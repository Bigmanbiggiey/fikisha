"""Design Phase 6 Increment 9 — Platform Admin console (P3 §19, ADR-2D-38).

Covers: Platform-Admin-only access on every endpoint (an Ops Officer, an
ordinary user and an anonymous caller are refused: IDOR/BOLA), the directory
with masked phones and the audited reveal, the step-up gate on
interventions and config changes (refused until admin MFA exists), the
interventions themselves behind the gate, the append-only intervention
record, suspension actually blocking new work (D-2), the config view /
preview / allowlist, and the commission ledger.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

import pytest
from django.db import connection, transaction
from django.db.utils import IntegrityError

from fikisha.admin_console import services
from fikisha.admin_console.models import AdminIntervention
from fikisha.audit.models import AuditLogEntry
from fikisha.common.models import AppendOnlyModelError
from fikisha.identity.authz.step_up import StepUpRequired

pytestmark = pytest.mark.django_db

API = "/api/v1"

ADMIN_GETS = [
    "/admin/directory/businesses",
    "/admin/directory/operators",
    "/admin/directory/groups",
    "/admin/config",
    "/admin/commission",
]


# ─── Access: Platform Admin only ───────────────────────────────────────
@pytest.mark.parametrize("path", ADMIN_GETS)
def test_platform_admin_can_read(path: str, client_for: Callable, platform_admin: Any) -> None:
    r = client_for(platform_admin).get(API + path)
    assert r.status_code == 200, r.content


@pytest.mark.parametrize("path", ADMIN_GETS)
@pytest.mark.parametrize("who", ["ops_officer", "user"])
def test_others_are_refused_reads(path: str, who: str, request: Any, client_for: Callable) -> None:
    r = client_for(request.getfixturevalue(who)).get(API + path)
    assert r.status_code == 403, r.content


@pytest.mark.parametrize("path", ADMIN_GETS)
def test_anonymous_is_refused(path: str, api: Any) -> None:
    assert api.get(API + path).status_code == 401


@pytest.mark.parametrize("who", ["ops_officer", "user"])
def test_others_are_refused_writes(
    who: str,
    request: Any,
    client_for: Callable,
    eligible_driver: Any,
    verified_business: Any,
) -> None:
    client = client_for(request.getfixturevalue(who))
    posts = [
        (f"/admin/directory/businesses/{verified_business.id}/contact", {}),
        (
            "/admin/interventions",
            {
                "account_type": "OPERATOR",
                "account_id": str(eligible_driver.id),
                "action": "SUSPEND",
                "reason": "Repeated no-shows at pickup",
            },
        ),
        ("/admin/config", {"changes": {"commission.rate": 0.08}, "rationale": "Pilot test rate"}),
        ("/admin/config/preview", {"changes": {"commission.rate": 0.08}}),
    ]
    for path, body in posts:
        r = client.post(API + path, body, format="json")
        assert r.status_code == 403, (path, r.content)
    eligible_driver.refresh_from_db()
    assert eligible_driver.status == "ACTIVE"


# ─── Directory ─────────────────────────────────────────────────────────
def test_directory_masks_phones_and_filters(
    client_for: Callable, platform_admin: Any, verified_business: Any, eligible_driver: Any
) -> None:
    client = client_for(platform_admin)
    r = client.get(f"{API}/admin/directory/operators")
    row = next(x for x in r.data["data"] if x["id"] == str(eligible_driver.id))
    assert eligible_driver.user.phone not in str(r.content)
    assert row["phone"].startswith(eligible_driver.user.phone[:5])
    assert "•" in row["phone"]

    r = client.get(f"{API}/admin/directory/businesses?q=kitengela")
    assert [x["id"] for x in r.data["data"]] == [str(verified_business.id)]
    r = client.get(f"{API}/admin/directory/businesses?state=SUSPENDED")
    assert r.data["data"] == []
    assert client.get(f"{API}/admin/directory/businesses?state=NOPE").status_code == 422
    assert client.get(f"{API}/admin/directory/vehicles").status_code == 404


def test_directory_detail_shows_in_flight_jobs(
    client_for: Callable,
    platform_admin: Any,
    make_confirmed_job: Callable,
    eligible_driver: Any,
) -> None:
    job = make_confirmed_job(operator=eligible_driver)
    client = client_for(platform_admin)
    for kind, account_id in (("businesses", job.business_id), ("operators", eligible_driver.id)):
        r = client.get(f"{API}/admin/directory/{kind}/{account_id}")
        assert r.status_code == 200, r.content
        assert [j["id"] for j in r.data["in_flight_jobs"]] == [str(job.id)]
        assert r.data["interventions"] == []
    import uuid

    assert client.get(f"{API}/admin/directory/operators/{uuid.uuid4()}").status_code == 404


def test_contact_reveal_is_audited_without_the_phone(
    client_for: Callable, platform_admin: Any, eligible_driver: Any
) -> None:
    r = client_for(platform_admin).post(
        f"{API}/admin/directory/operators/{eligible_driver.id}/contact"
    )
    assert r.status_code == 200, r.content
    assert r.data["phone"] == eligible_driver.user.phone
    entry = AuditLogEntry.objects.get(action="admin.directory.contact_revealed")
    assert str(entry.entity_id) == str(eligible_driver.id)
    assert eligible_driver.user.phone not in str(entry.after)


# ─── Step-up gate (D-1 deferred: everything behind it is refused) ───────
def _stale_step_up(client: Any) -> Any:
    """Make the client's session MFA-verified but with an old step-up."""
    from datetime import timedelta

    from django.utils import timezone

    from fikisha.identity.models import AuthSession

    AuthSession.objects.filter(revoked_at__isnull=True, step_up_at__isnull=False).update(
        step_up_at=timezone.now() - timedelta(hours=1)
    )
    return client


SUSPEND = {"account_type": "OPERATOR", "action": "SUSPEND", "reason": "Repeated no-shows at pickup"}


def test_intervention_api_needs_a_fresh_step_up(
    client_for: Callable, platform_admin: Any, eligible_driver: Any
) -> None:
    body = {**SUSPEND, "account_id": str(eligible_driver.id)}
    stale = _stale_step_up(client_for(platform_admin))
    r = stale.post(f"{API}/admin/interventions", body, format="json")
    assert r.status_code == 403, r.content
    assert r.json()["code"] == "step_up_required"
    eligible_driver.refresh_from_db()
    assert eligible_driver.status == "ACTIVE"
    assert not AdminIntervention.objects.exists()

    # with admin MFA built (9a), a fresh step-up lets it through
    r = client_for(platform_admin).post(f"{API}/admin/interventions", body, format="json")
    assert r.status_code == 201, r.content
    eligible_driver.refresh_from_db()
    assert eligible_driver.status == "SUSPENDED"


def test_config_change_api_needs_a_fresh_step_up(client_for: Callable, platform_admin: Any) -> None:
    from fikisha.platform_config import services as config_services

    before = config_services.current_version()
    body = {
        "changes": {"commission.business_rate": 0.04},
        "rationale": "Pilot test of a lower rate",
    }
    stale = _stale_step_up(client_for(platform_admin))
    r = stale.post(f"{API}/admin/config", body, format="json")
    assert r.status_code == 403, r.content
    assert r.json()["code"] == "step_up_required"
    assert config_services.current_version() == before

    r = client_for(platform_admin).post(f"{API}/admin/config", body, format="json")
    assert r.status_code == 201, r.content
    assert config_services.current_version() == before + 1


def test_high_value_decision_and_dispute_resolution_need_a_fresh_step_up(
    client_for: Callable, platform_admin: Any, make_confirmed_job: Callable, eligible_driver: Any
) -> None:
    job = make_confirmed_job(operator=eligible_driver, declared_value_kes=50_000_000)
    stale = _stale_step_up(client_for(platform_admin))
    r = stale.post(
        f"{API}/jobs/{job.id}/high-value-decision",
        {"decision": "APPROVED", "rationale": "Known business, insured cargo"},
        format="json",
    )
    assert r.status_code == 403, r.content
    assert r.json()["code"] == "step_up_required"
    r = stale.post(
        f"{API}/disputes/00000000-0000-7000-8000-000000000000/resolve",
        {
            "outcome_code": "ADMIN_DETERMINATION",
            "rationale": "Agreed by phone",
            "routed_job_status": "COMPLETED",
        },
        format="json",
    )
    assert r.status_code == 403, r.content
    assert r.json()["code"] == "step_up_required"


def test_input_errors_come_before_the_step_up(
    client_for: Callable, platform_admin: Any, eligible_driver: Any
) -> None:
    r = client_for(platform_admin).post(
        f"{API}/admin/interventions",
        {
            "account_type": "OPERATOR",
            "account_id": str(eligible_driver.id),
            "action": "SUSPEND",
            "reason": "short",
        },
        format="json",
    )
    assert r.status_code == 422
    assert r.json()["code"] == "invalid_intervention"


# ─── Interventions, behind the gate ────────────────────────────────────
def _intervene(actor: Any, account_type: str, account_id: Any, action: str, **kw: Any) -> Any:
    return services.intervene(
        actor=actor,
        account_type=account_type,
        account_id=account_id,
        action=action,
        reason=kw.pop("reason", "Repeated no-shows at pickup"),
        **kw,
    )


def test_suspend_and_reinstate_operator(stepped_up_admin: Any, eligible_driver: Any) -> None:
    result = _intervene(
        stepped_up_admin, "OPERATOR", eligible_driver.id, "SUSPEND", duration_days=14
    )
    assert (result["before_state"], result["after_state"]) == ("ACTIVE", "SUSPENDED")
    eligible_driver.refresh_from_db()
    assert eligible_driver.status == "SUSPENDED"

    row = AdminIntervention.objects.get()
    assert (row.action, row.duration_days, row.before_state) == ("SUSPEND", 14, "ACTIVE")
    entry = AuditLogEntry.objects.get(action="admin.account.suspend")
    assert entry.after["reason"] == "Repeated no-shows at pickup"
    assert entry.after["intervention_id"] == str(row.id)

    _intervene(stepped_up_admin, "OPERATOR", eligible_driver.id, "REINSTATE")
    eligible_driver.refresh_from_db()
    assert eligible_driver.status == "ACTIVE"


def test_reinstate_restores_the_state_before_suspension(
    stepped_up_admin: Any, make_verified_operator: Callable
) -> None:
    pending = make_verified_operator("+254733111222", "New Operator")
    pending.status = "PENDING"
    pending.save(update_fields=["status"])
    _intervene(stepped_up_admin, "OPERATOR", pending.id, "SUSPEND")
    _intervene(stepped_up_admin, "OPERATOR", pending.id, "REINSTATE")
    pending.refresh_from_db()
    assert pending.status == "PENDING"


def test_offboard_rules(
    stepped_up_admin: Any, eligible_driver: Any, verified_business: Any, make_group: Callable
) -> None:
    _intervene(stepped_up_admin, "OPERATOR", eligible_driver.id, "OFFBOARD")
    eligible_driver.refresh_from_db()
    assert eligible_driver.status == "OFFBOARDED"
    with pytest.raises(services.InterventionNotAllowed):
        _intervene(stepped_up_admin, "OPERATOR", eligible_driver.id, "OFFBOARD")
    with pytest.raises(services.InterventionNotAllowed):
        _intervene(stepped_up_admin, "OPERATOR", eligible_driver.id, "SUSPEND")
    with pytest.raises(services.InterventionNotAllowed):
        _intervene(stepped_up_admin, "BUSINESS", verified_business.id, "OFFBOARD")
    with pytest.raises(services.InterventionNotAllowed):
        _intervene(stepped_up_admin, "GROUP", make_group().id, "OFFBOARD")


def test_suspend_business_group_and_user(
    stepped_up_admin: Any, verified_business: Any, make_group: Callable, user: Any
) -> None:
    group = make_group()
    _intervene(stepped_up_admin, "BUSINESS", verified_business.id, "SUSPEND")
    _intervene(stepped_up_admin, "GROUP", group.id, "SUSPEND")
    _intervene(stepped_up_admin, "USER", user.id, "SUSPEND")
    verified_business.refresh_from_db()
    group.refresh_from_db()
    user.refresh_from_db()
    assert (verified_business.standing, group.standing, user.status) == (
        "SUSPENDED",
        "SUSPENDED",
        "SUSPENDED",
    )
    _intervene(stepped_up_admin, "BUSINESS", verified_business.id, "REINSTATE")
    verified_business.refresh_from_db()
    assert verified_business.standing == "GOOD"


def test_a_suspended_user_is_signed_out(
    stepped_up_admin: Any, user: Any, client_for: Callable
) -> None:
    client = client_for(user)
    assert client.get(f"{API}/me").status_code == 200
    _intervene(stepped_up_admin, "USER", user.id, "SUSPEND")
    assert client.get(f"{API}/me").status_code == 401


def test_intervention_input_rules(
    stepped_up_admin: Any, eligible_driver: Any, platform_admin: Any
) -> None:
    with pytest.raises(services.InvalidIntervention):
        _intervene(stepped_up_admin, "OPERATOR", eligible_driver.id, "SUSPEND", reason="short")
    with pytest.raises(services.InvalidIntervention):
        _intervene(stepped_up_admin, "OPERATOR", eligible_driver.id, "RESTRICT")
    with pytest.raises(services.InvalidIntervention):
        _intervene(stepped_up_admin, "VEHICLE", eligible_driver.id, "SUSPEND")
    with pytest.raises(services.InvalidIntervention):
        _intervene(stepped_up_admin, "OPERATOR", eligible_driver.id, "SUSPEND", duration_days=0)
    with pytest.raises(services.InvalidIntervention):
        _intervene(stepped_up_admin, "OPERATOR", eligible_driver.id, "OFFBOARD", duration_days=7)
    with pytest.raises(services.InterventionNotAllowed):
        _intervene(stepped_up_admin, "OPERATOR", eligible_driver.id, "REINSTATE")
    with pytest.raises(services.InterventionNotAllowed):
        _intervene(stepped_up_admin, "USER", platform_admin.id, "SUSPEND")
    assert not AdminIntervention.objects.exists()


def test_without_step_up_the_service_refuses_too(admin_actor: Any, eligible_driver: Any) -> None:
    with pytest.raises(StepUpRequired):
        _intervene(admin_actor, "OPERATOR", eligible_driver.id, "SUSPEND")


def test_intervention_rows_are_append_only(stepped_up_admin: Any, eligible_driver: Any) -> None:
    _intervene(stepped_up_admin, "OPERATOR", eligible_driver.id, "SUSPEND")
    row = AdminIntervention.objects.get()
    with pytest.raises(AppendOnlyModelError):
        row.save()
    with pytest.raises(AppendOnlyModelError):
        AdminIntervention.objects.filter(id=row.id).update(reason="edited")
    with pytest.raises(IntegrityError), transaction.atomic(), connection.cursor() as cur:
        cur.execute("UPDATE admin_intervention SET reason = 'edited' WHERE id = %s", [row.id])


# ─── Suspension blocks new work (D-2) ──────────────────────────────────
def test_suspended_business_cannot_create_or_publish(
    stepped_up_admin: Any,
    verified_business: Any,
    draft_job: Any,
    business_actor: Any,
    admin_actor: Any,
    do_transition: Callable,
) -> None:
    from fikisha.jobs import creation
    from fikisha.jobs.errors import GuardFailed

    _intervene(stepped_up_admin, "BUSINESS", verified_business.id, "SUSPEND")
    with pytest.raises(creation.BusinessSuspended):
        creation.create_draft(actor=business_actor, business_id=verified_business.id, data={})
    with pytest.raises(GuardFailed) as exc:
        do_transition(draft_job, "REQUESTED", admin_actor)
    assert exc.value.code == "business_suspended"


def test_suspended_operator_sees_no_work(
    stepped_up_admin: Any,
    eligible_driver: Any,
    eligible_vehicle: Any,
    draft_job: Any,
    admin_actor: Any,
    do_transition: Callable,
    actor_for: Callable,
) -> None:
    from fikisha.jobs import discovery

    do_transition(draft_job, "REQUESTED", admin_actor)
    driver = actor_for(eligible_driver.user)
    assert list(discovery.open_jobs_for(driver)) != []
    _intervene(stepped_up_admin, "OPERATOR", eligible_driver.id, "SUSPEND")
    assert list(discovery.open_jobs_for(driver)) == []


@pytest.mark.parametrize("status", ["SUSPENDED", "OFFBOARDED"])
def test_operator_eligibility_refuses_suspended_and_offboarded(
    status: str, eligible_driver: Any, draft_job: Any
) -> None:
    from fikisha.jobs import guards
    from fikisha.jobs.errors import DriverNotEligible

    eligible_driver.status = status
    with pytest.raises(DriverNotEligible):
        guards.operator_eligible_for_job(draft_job, None, {"operator_profile": eligible_driver})


def test_suspended_group_cannot_negotiate(
    stepped_up_admin: Any, make_group: Callable, draft_job: Any
) -> None:
    from fikisha.jobs import guards
    from fikisha.jobs.errors import DriverNotEligible

    group = make_group()
    ctx = {"operator_profile": None, "group_id": str(group.id)}
    guards.operator_eligible_for_job(draft_job, None, ctx)
    _intervene(stepped_up_admin, "GROUP", group.id, "SUSPEND")
    with pytest.raises(DriverNotEligible):
        guards.operator_eligible_for_job(draft_job, None, ctx)


# ─── Configuration ─────────────────────────────────────────────────────
def test_config_view(client_for: Callable, platform_admin: Any) -> None:
    r = client_for(platform_admin).get(f"{API}/admin/config")
    assert r.data["config"]["commission"] == {
        "model": "SPLIT_FLAT",
        "business_rate": 0.05,
        "operator_rate": 0.05,
    }
    assert "commission.business_rate" in r.data["editable_paths"]
    assert "commission.operator_rate" in r.data["editable_paths"]
    assert "commission.min_fee_kes" not in r.data["editable_paths"]
    assert "role_permissions" not in " ".join(r.data["editable_paths"])
    assert r.data["versions"][0]["version"] == r.data["version"]


def test_config_preview_shows_diff_and_effect(client_for: Callable, platform_admin: Any) -> None:
    from fikisha.platform_config import services as config_services

    before = config_services.current_version()
    r = client_for(platform_admin).post(
        f"{API}/admin/config/preview",
        {"changes": {"commission.business_rate": 0.03, "timeouts.offer_expiry_hours": 6}},
        format="json",
    )
    assert r.status_code == 200, r.content
    assert {c["path"]: (c["before"], c["after"]) for c in r.data["changes"]} == {
        "commission.business_rate": (0.05, 0.03),
        "timeouts.offer_expiry_hours": (4, 6),
    }
    # each side on a KES 3,000 job: 5% + 5% today, 3% + 5% after
    sample = next(s for s in r.data["commission_samples"] if s["agreed_price_kes"] == 300_000)
    assert sample["before"] == {"business_kes": 15_000, "operator_kes": 15_000}
    assert sample["after"] == {"business_kes": 9_000, "operator_kes": 15_000}
    assert (sample["before_kes"], sample["after_kes"]) == (30_000, 24_000)
    assert config_services.current_version() == before


@pytest.mark.parametrize(
    ("changes", "code"),
    [
        ({"role_permissions.OPERATIONS_OFFICER": ["*"]}, "config_key_not_editable"),
        ({"high_value_threshold_kes": 1}, "config_key_not_editable"),
        ({"commission.business_rate": 2}, "invalid_config_change"),
        ({"commission.operator_rate": -0.01}, "invalid_config_change"),
        ({"commission.business_rate": "0.1"}, "invalid_config_change"),
        ({"commission.cap_kes": 500000}, "config_key_not_editable"),
        ({"commission.rate": 0.10}, "config_key_not_editable"),
        ({"commission.operator_rate": 0.05}, "invalid_config_change"),
        ({}, "invalid_config_change"),
    ],
)
def test_config_preview_refuses(
    changes: dict[str, Any], code: str, client_for: Callable, platform_admin: Any
) -> None:
    r = client_for(platform_admin).post(
        f"{API}/admin/config/preview", {"changes": changes}, format="json"
    )
    assert r.status_code in (400, 422), r.content
    assert r.json()["code"] == code


def test_config_apply_behind_the_gate(stepped_up_admin: Any) -> None:
    from fikisha.platform_config import services as config_services

    before = config_services.current_version()
    result = services.apply_config_change(
        actor=stepped_up_admin,
        changes={"commission.operator_rate": 0.04},
        rationale="Pilot test of a lower rate",
    )
    assert result["version"] == before + 1
    assert config_services.get("commission.operator_rate") == 0.04
    assert AuditLogEntry.objects.filter(action="platform_config.changed").exists()
    with pytest.raises(services.InvalidConfigChange):
        services.apply_config_change(
            actor=stepped_up_admin, changes={"commission.operator_rate": 0.07}, rationale="short"
        )


def test_the_live_criteria_switch_is_a_yes_no_value(stepped_up_admin: Any) -> None:
    """trust-and-disputes plan A5: a Platform Admin turns ratings and
    findings on for the tiers."""
    from fikisha.platform_config import services as config_services

    for bad in (1, "true", None):
        with pytest.raises(services.InvalidConfigChange):
            services.apply_config_change(
                actor=stepped_up_admin,
                changes={"trust_tiers.live_criteria": bad},
                rationale="Turn ratings on for the tiers",
            )
    services.apply_config_change(
        actor=stepped_up_admin,
        changes={"trust_tiers.live_criteria": True},
        rationale="Turn ratings on for the tiers",
    )
    assert config_services.get("trust_tiers.live_criteria") is True


# ─── Commission ledger ─────────────────────────────────────────────────
def test_commission_ledger(
    client_for: Callable,
    platform_admin: Any,
    delivered_job: Callable,
    complete_job: Callable,
    eligible_driver: Any,
) -> None:
    job = delivered_job()
    complete_job(job)
    r = client_for(platform_admin).get(f"{API}/admin/commission")
    assert r.status_code == 200, r.content
    assert r.data["statements_available"] is True
    rows = {row["party"]: row for row in r.data["data"]}
    assert set(rows) == {"BUSINESS", "OPERATOR"}  # one per paying side (ADR-2D-55)
    for row in rows.values():
        assert row["job_id"] == str(job.id)
        assert row["effective_kes"] == row["commission_kes"] > 0
        assert row["min_fee_kes"] is None and row["cap_kes"] is None
    assert rows["OPERATOR"]["payee"]["id"] == str(eligible_driver.id)
    assert rows["BUSINESS"]["payee"] == {
        "kind": "BUSINESS",
        "id": str(job.business_id),
        "name": "Kitengela Traders",
    }
    assert r.data["totals"]["records"] == 2
    assert r.data["totals"]["effective_kes"] == sum(x["effective_kes"] for x in rows.values())

    # filters: a side; an operator owes only the operator side; a business its own
    by_party = client_for(platform_admin).get(f"{API}/admin/commission?party=BUSINESS")
    assert [x["party"] for x in by_party.data["data"]] == ["BUSINESS"]
    by_op = client_for(platform_admin).get(
        f"{API}/admin/commission?operator_id={eligible_driver.id}"
    )
    assert [x["party"] for x in by_op.data["data"]] == ["OPERATOR"]
    by_biz = client_for(platform_admin).get(f"{API}/admin/commission?business_id={job.business_id}")
    assert [x["party"] for x in by_biz.data["data"]] == ["BUSINESS"]
    assert client_for(platform_admin).get(f"{API}/admin/commission?party=X").status_code == 422

    r = client_for(platform_admin).get(f"{API}/admin/commission?since=2999-01-01T00:00:00Z")
    assert r.data["data"] == []
    assert r.data["totals"]["records"] == 0
    bad = client_for(platform_admin).get(f"{API}/admin/commission?operator_id=nope")
    assert bad.status_code == 422


def test_group_directory_detail_and_reveal(
    client_for: Callable, platform_admin: Any, make_group: Callable, make_confirmed_job: Callable
) -> None:
    group = make_group()
    job = make_confirmed_job(group=group)
    client = client_for(platform_admin)

    r = client.get(f"{API}/admin/directory/groups?q=kitengela&state=GOOD")
    assert [x["id"] for x in r.data["data"]] == [str(group.id)]
    assert r.data["data"][0]["member_count"] == 1

    r = client.get(f"{API}/admin/directory/groups/{group.id}")
    assert r.status_code == 200, r.content
    assert [m["role"] for m in r.data["members"]] == ["OWNER"]
    assert [j["id"] for j in r.data["in_flight_jobs"]] == [str(job.id)]
    assert r.data["user_interventions"] == []

    r = client.post(f"{API}/admin/directory/groups/{group.id}/contact")
    assert r.status_code == 200, r.content
    assert r.data["phone"] == group.primary_contact.phone
