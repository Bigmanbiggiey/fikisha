"""Operator tiers (operator-tiers plan, ADR-2D-52; TD-1 to TD-6)."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

import pytest

from fikisha.audit.models import AuditLogEntry
from fikisha.common.exceptions import AuthorizationError
from fikisha.common.models import AppendOnlyModelError
from fikisha.identity.authz.step_up import StepUpRequired
from fikisha.jobs import eligibility
from fikisha.trust import services
from fikisha.trust.constants import ChangeStatus, ChangeTrigger, Tier
from fikisha.trust.models import TrustLevelChange, TrustLevelState

pytestmark = pytest.mark.django_db

REASON = "Reviewed their record with the stage chair."


def _criteria(view: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {c["key"]: c for c in view["criteria"]}


@pytest.fixture
def driver(make_verified_operator: Callable) -> Any:
    return make_verified_operator("+254711500001", "T. Dereva")


def _ready_for_l2(driver: Any, give_jobs: Callable) -> None:
    give_jobs(driver, 8, days_ago=20)


# ─── the tier and its floor ───────────────────────────────────────────
def test_a_verified_operator_with_no_record_is_l1(driver: Any) -> None:
    view = services.tier_view(driver)
    assert view["level"] == Tier.L1
    assert view["bands"] == ["STANDARD"]
    assert view["max_value_kes"] == 5_000_000
    assert view["next_level"] == Tier.L2
    assert not TrustLevelState.objects.exists()  # nobody's access changed on day one
    assert eligibility.driver_trust_level(driver) == "L1"


def test_unverified_operator_is_l0_with_the_verification_checklist(
    make_verified_operator: Callable,
) -> None:
    pending = make_verified_operator("+254711500002", "P. Pending", verified=False)
    view = services.tier_view(pending)
    assert view["level"] == Tier.L0
    assert view["bands"] == []
    assert view["next_level"] == Tier.L1
    assert {c["key"] for c in view["criteria"]} == {
        "verified_identity",
        "verified_licence",
        "verified_good_conduct",
    }
    assert eligibility.driver_trust_level(pending) == ""


def test_lapsed_verification_drops_any_tier_to_l0(driver: Any, stepped_admin: Any) -> None:
    from fikisha.verification.models import State, VerificationRecord

    services.set_level(actor=stepped_admin, operator_id=driver.id, level="L3", reason=REASON)
    assert eligibility.driver_trust_level(driver) == "L3"
    VerificationRecord.objects.filter(subject_operator=driver, domain="LICENCE").update(
        state=State.EXPIRED
    )
    assert eligibility.driver_trust_level(driver) == ""
    assert services.tier_view(driver)["level"] == Tier.L0
    assert services.stored_level(driver.id) == "L3"  # restored once renewed


# ─── progress ────────────────────────────────────────────────────────
def test_progress_counts_completed_jobs_and_days_active(driver: Any, give_jobs: Callable) -> None:
    give_jobs(driver, 5, days_ago=10)
    give_jobs(driver, 2, status="CANCELLED")
    rows = _criteria(services.tier_view(driver))
    assert rows["completed_jobs"] == {
        "key": "completed_jobs",
        "status": "NOT_MET",
        "current": 5,
        "target": 8,
    }
    assert rows["days_active"]["current"] == 10
    assert rows["days_active"]["status"] == "NOT_MET"
    assert rows["avg_rating"]["status"] == "NOT_MEASURED"  # TD-3
    assert rows["at_fault_findings"]["status"] == "NOT_MEASURED"
    assert rows["good_conduct"]["status"] == "MET"


def test_every_measured_l2_criterion_met_means_ready(driver: Any, give_jobs: Callable) -> None:
    _ready_for_l2(driver, give_jobs)
    view = services.tier_view(driver)
    assert view["ready_for_review"] is True


def test_an_unresolved_incident_blocks_but_not_paid_does_not(
    driver: Any, give_jobs: Callable
) -> None:
    from fikisha.incidents.models import Incident

    jobs = give_jobs(driver, 8, days_ago=20)
    Incident.objects.create(
        job=jobs[0], type="NON_PAYMENT", severity="MEDIUM", reported_by_kind="USER"
    )
    assert services.tier_view(driver)["ready_for_review"] is True
    Incident.objects.create(job=jobs[1], type="DELAY", severity="LOW", reported_by_kind="USER")
    view = services.tier_view(driver)
    assert _criteria(view)["unresolved_incidents"]["current"] == 1
    assert view["ready_for_review"] is False


def test_operator_cancellations_are_not_measured(driver: Any, give_jobs: Callable) -> None:
    """Operators can't cancel and no-shows aren't recorded (CF-1): a business
    user's cancellations never count against an operator who shares the user."""
    from fikisha.jobs.models import CancellationRecord

    jobs = give_jobs(driver, 8, days_ago=20)
    for job in jobs[:3]:
        CancellationRecord.objects.create(
            job=job,
            cancelled_by_role="USER",
            cancelled_by_user=driver.user,
            at_status="ASSIGNED",
            penalty_class="LATE_CANCELLATION",
        )
    view = services.tier_view(driver)
    assert _criteria(view)["no_cancellation_flag"]["status"] == "NOT_MEASURED"
    assert view["ready_for_review"] is True


def test_the_operators_own_reports_never_count_against_them(
    driver: Any, give_jobs: Callable
) -> None:
    from fikisha.incidents.models import Incident

    jobs = give_jobs(driver, 8, days_ago=20)
    Incident.objects.create(
        job=jobs[0],
        type="WRONG_PICKUP",
        severity="LOW",
        reported_by_kind="USER",
        reporter_party="OPERATOR",
    )
    Incident.objects.create(
        job=jobs[1],
        type="DELAY",
        severity="LOW",
        reported_by_kind="USER",
        reporter_party="GROUP",
    )
    # reported before the reporter's side was stored, by the driver themself
    Incident.objects.create(
        job=jobs[2],
        type="DELAY",
        severity="LOW",
        reported_by_kind="USER",
        reported_by_user=driver.user,
    )
    view = services.tier_view(driver)
    assert _criteria(view)["unresolved_incidents"]["current"] == 0
    assert view["ready_for_review"] is True
    Incident.objects.create(
        job=jobs[3],
        type="DELAY",
        severity="LOW",
        reported_by_kind="USER",
        reporter_party="BUSINESS",
    )
    assert _criteria(services.tier_view(driver))["unresolved_incidents"]["current"] == 1


def test_restricted_exits_to_l1_only(driver: Any, stepped_admin: Any) -> None:
    from fikisha.trust.services import TierChangeNotAllowed

    services.set_level(
        actor=stepped_admin, operator_id=driver.id, level="RESTRICTED", reason=REASON
    )
    for level in ("L2", "L3"):
        with pytest.raises(TierChangeNotAllowed):
            services.set_level(
                actor=stepped_admin, operator_id=driver.id, level=level, reason=REASON
            )
    services.set_level(actor=stepped_admin, operator_id=driver.id, level="L1", reason=REASON)
    assert services.stored_level(driver.id) == "L1"


def test_l3_needs_clean_elevated_jobs(driver: Any, give_jobs: Callable, stepped_admin: Any) -> None:
    from fikisha.incidents.models import Incident

    services.set_level(actor=stepped_admin, operator_id=driver.id, level="L2", reason=REASON)
    give_jobs(driver, 28, days_ago=70)
    elevated = give_jobs(driver, 3, days_ago=65, band="ELEVATED")
    Incident.objects.create(
        job=elevated[0], type="DAMAGE", severity="LOW", reported_by_kind="USER", status="RESOLVED"
    )
    rows = _criteria(services.tier_view(driver))
    assert rows["completed_jobs"]["status"] == "MET"
    assert rows["clean_elevated_jobs"]["current"] == 2  # the one with an incident isn't clean
    assert rows["clean_elevated_jobs"]["status"] == "NOT_MET"
    assert rows["serious_unresolved_incidents"]["status"] == "MET"


# ─── proposals (TD-1: proposed by Fikisha, confirmed by an admin) ────
def test_evaluate_proposes_once_and_applies_nothing(driver: Any, give_jobs: Callable) -> None:
    assert services.evaluate(driver) is None  # nothing due yet
    _ready_for_l2(driver, give_jobs)
    change = services.evaluate(driver)
    assert change is not None
    assert (change.from_level, change.to_level, change.status) == ("L1", "L2", "PROPOSED")
    assert change.trigger == ChangeTrigger.AUTO_PROPOSED
    assert change.criteria_snapshot["criteria"]
    assert services.evaluate(driver) is None  # already open
    assert services.stored_level(driver.id) == "L1"
    assert services.tier_view(driver)["open_proposal"]["id"] == str(change.id)
    assert AuditLogEntry.objects.filter(action="trust.change.proposed").count() == 1


def test_confirming_a_proposal_promotes(
    driver: Any, give_jobs: Callable, stepped_admin: Any
) -> None:
    _ready_for_l2(driver, give_jobs)
    proposal = services.evaluate(driver)
    assert proposal is not None
    services.decide_proposal(
        actor=stepped_admin, change_id=proposal.id, confirm=True, reason=REASON
    )
    assert services.stored_level(driver.id) == "L2"
    assert eligibility.level_covers_band(eligibility.driver_trust_level(driver), "ELEVATED")
    view = services.tier_view(driver, staff=True)
    assert view["open_proposal"] is None
    assert view["history"][0]["trigger"] == "ADMIN_CONFIRMED"
    assert view["history"][0]["by"]
    assert AuditLogEntry.objects.filter(action="trust.change.confirmed").exists()
    with pytest.raises(services.ProposalNotOpen):
        services.decide_proposal(
            actor=stepped_admin, change_id=proposal.id, confirm=True, reason=REASON
        )


def test_a_rejected_proposal_is_not_remade_within_the_cooldown(
    driver: Any, give_jobs: Callable, stepped_admin: Any
) -> None:
    _ready_for_l2(driver, give_jobs)
    proposal = services.evaluate(driver)
    assert proposal is not None
    services.decide_proposal(
        actor=stepped_admin, change_id=proposal.id, confirm=False, reason=REASON
    )
    assert services.stored_level(driver.id) == "L1"
    assert TrustLevelChange.objects.filter(status=ChangeStatus.REJECTED).count() == 1
    assert services.evaluate(driver) is None


def test_a_manual_change_makes_an_open_proposal_stale(
    driver: Any, give_jobs: Callable, stepped_admin: Any
) -> None:
    _ready_for_l2(driver, give_jobs)
    proposal = services.evaluate(driver)
    assert proposal is not None
    services.set_level(
        actor=stepped_admin, operator_id=driver.id, level="RESTRICTED", reason=REASON
    )
    assert services.open_proposals() == []
    with pytest.raises(services.ProposalNotOpen):
        services.decide_proposal(
            actor=stepped_admin, change_id=proposal.id, confirm=True, reason=REASON
        )


# ─── manual promote / demote (TD-1, TD-4) ────────────────────────────
def test_manual_demotion_to_restricted_and_back(driver: Any, stepped_admin: Any) -> None:
    services.set_level(
        actor=stepped_admin, operator_id=driver.id, level="RESTRICTED", reason=REASON
    )
    level = eligibility.driver_trust_level(driver)
    assert level == "RESTRICTED"
    assert eligibility.level_covers_band(level, "STANDARD")
    assert not eligibility.level_covers_band(level, "ELEVATED")
    view = services.tier_view(driver)
    assert view["bands"] == ["STANDARD"]
    assert view["next_level"] is None  # Restricted doesn't progress
    services.set_level(actor=stepped_admin, operator_id=driver.id, level="L1", reason=REASON)
    history = services.tier_view(driver)["history"]
    assert [h["to_level"] for h in history] == ["L1", "RESTRICTED"]
    assert all(h["trigger"] == "ADMIN_OVERRIDE" for h in history)
    assert "by" not in history[0]  # the operator doesn't see staff names


def test_manual_change_refusals(
    driver: Any, admin_actor: Any, stepped_admin: Any, ops_officer: Any
) -> None:
    from fikisha.identity.authz.actors import actor_from_user

    with pytest.raises(StepUpRequired):
        services.set_level(actor=admin_actor, operator_id=driver.id, level="L2", reason=REASON)
    with pytest.raises(services.InvalidTierChange):
        services.set_level(actor=stepped_admin, operator_id=driver.id, level="L2", reason="short")
    with pytest.raises(services.TierChangeNotAllowed):
        services.set_level(actor=stepped_admin, operator_id=driver.id, level="L1", reason=REASON)
    with pytest.raises(AuthorizationError):
        services.set_level(
            actor=actor_from_user(ops_officer), operator_id=driver.id, level="L2", reason=REASON
        )
    assert not TrustLevelChange.objects.exists()


def test_an_admin_cannot_change_their_own_tier(
    platform_admin: Any, stepped_admin: Any, verify_subject: Callable
) -> None:
    from fikisha.operators.models import OperatorProfile

    own = OperatorProfile.objects.create(user=platform_admin, full_name="Admin Dereva")
    verify_subject(own, "IDENTITY", "LICENCE", "GOOD_CONDUCT")
    with pytest.raises(services.TierChangeNotAllowed):
        services.set_level(actor=stepped_admin, operator_id=own.id, level="L3", reason=REASON)


def test_changes_are_append_only(driver: Any, stepped_admin: Any) -> None:
    change = services.set_level(
        actor=stepped_admin, operator_id=driver.id, level="L2", reason=REASON
    )
    change.reason = "edited"
    with pytest.raises(AppendOnlyModelError):
        change.save()
    with pytest.raises(AppendOnlyModelError):
        change.delete()


# ─── assignment follows the tier ─────────────────────────────────────
def test_an_l2_driver_can_take_an_elevated_job_without_override(
    eligible_driver: Any,
    eligible_vehicle: Any,
    make_confirmed_job: Callable,
    actor_for: Callable,
    stepped_admin: Any,
) -> None:
    from fikisha.jobs.assignment import assign_job
    from fikisha.jobs.errors import DriverNotEligible

    job = make_confirmed_job(operator=eligible_driver, declared_value_kes=10_000_000)
    assert job.value_band == "ELEVATED"
    with pytest.raises(DriverNotEligible):
        assign_job(
            actor=actor_for(eligible_driver.user),
            job_id=job.id,
            driver_profile_id=eligible_driver.id,
            vehicle_id=eligible_vehicle.id,
        )
    services.set_level(
        actor=stepped_admin, operator_id=eligible_driver.id, level="L2", reason=REASON
    )
    assign_job(
        actor=actor_for(eligible_driver.user),
        job_id=job.id,
        driver_profile_id=eligible_driver.id,
        vehicle_id=eligible_vehicle.id,
    )
    job.refresh_from_db()
    assert job.status == "ASSIGNED"
    assert job.assignment.driver_trust_level == "L2"


def test_completing_a_job_proposes_a_due_tier(
    delivered_job: Callable,
    complete_job: Callable,
    eligible_driver: Any,
    give_jobs: Callable,
    django_capture_on_commit_callbacks: Any,
) -> None:
    job = delivered_job()
    give_jobs(eligible_driver, 7, days_ago=20)
    with django_capture_on_commit_callbacks(execute=True):
        complete_job(job)
    proposal = TrustLevelChange.objects.get(operator=eligible_driver)
    assert (proposal.status, proposal.to_level) == ("PROPOSED", "L2")


def test_nightly_task_proposes(driver: Any, give_jobs: Callable) -> None:
    from fikisha.trust.tasks import evaluate_tiers

    _ready_for_l2(driver, give_jobs)
    assert evaluate_tiers() == {"proposed": 1}
    assert evaluate_tiers() == {"proposed": 0}
