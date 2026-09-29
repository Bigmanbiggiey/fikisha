"""Messages inbox (Design Phase 7 10g, ADR-2D-37): aggregation per source,
party scoping (IDOR/BOLA), read markers, the API contract and paging."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

import pytest

from fikisha.inbox import services as inbox

pytestmark = pytest.mark.django_db


def _by_kind(items: list[dict[str, Any]], kind: str) -> list[dict[str, Any]]:
    return [i for i in items if i["kind"] == kind]


def _unread(actor: Any) -> dict[str, bool]:
    return {i["conversation_key"]: i["unread"] for i in inbox.conversations_for(actor)}


# ─── aggregation + scoping ───────────────────────────────────────────
def test_business_sees_every_operator_thread_on_its_job_as_unread(
    offers: dict[str, Any], owner_actor: Any
) -> None:
    items = _by_kind(inbox.conversations_for(owner_actor), "OFFER")
    assert {i["conversation_key"] for i in items} == {
        f"offer:{offers['a']}",
        f"offer:{offers['b']}",
    }
    assert {i["counterparty_name"] for i in items} == {"A. Otieno", "B. Wanjiru"}
    assert all(i["unread"] and not i["from_viewer"] for i in items)
    assert all(i["link"].endswith("/negotiation") for i in items)


def test_an_operator_sees_only_its_own_sealed_thread(
    offers: dict[str, Any], operator_a: Any, _actor: Callable
) -> None:
    items = _by_kind(inbox.conversations_for(_actor(operator_a.user)), "OFFER")
    assert [i["conversation_key"] for i in items] == [f"offer:{offers['a']}"]
    assert items[0]["counterparty_name"] == "Kitengela Traders"
    # The latest entry is the operator's own offer: not unread for them.
    assert items[0]["from_viewer"] is True
    assert items[0]["unread"] is False
    assert items[0]["amount_kes"] == 240_000


def test_another_business_sees_nothing_of_this_job(
    offers: dict[str, Any], stranger_business: Any, _actor: Callable
) -> None:
    assert inbox.conversations_for(_actor(stranger_business)) == []


def test_staff_get_an_empty_inbox_despite_seeing_every_job(
    offers: dict[str, Any], platform_admin: Any, ops_officer: Any, _actor: Callable
) -> None:
    assert inbox.conversations_for(_actor(platform_admin)) == []
    assert inbox.conversations_for(_actor(ops_officer)) == []


def test_fikisha_notes_reach_the_job_parties_as_one_conversation(
    offers: dict[str, Any],
    requested_job: Any,
    owner_actor: Any,
    operator_a: Any,
    ops_officer: Any,
    stranger_business: Any,
    _actor: Callable,
) -> None:
    from fikisha.jobs import ops

    ops.add_note(actor=_actor(ops_officer), job_id=requested_job.id, text="Driver running late")
    ops.add_note(actor=_actor(ops_officer), job_id=requested_job.id, text="Now 10 minutes away")

    notes = _by_kind(inbox.conversations_for(owner_actor), "FIKISHA_UPDATE")
    assert len(notes) == 1  # one conversation per job, not one per note
    assert notes[0]["conversation_key"] == f"notes:{requested_job.id}"
    assert notes[0]["preview"] == "Now 10 minutes away"
    assert notes[0]["count"] == 2
    assert notes[0]["unread"] is True
    # A negotiating operator is a job party for notes (the job.read rule) ...
    assert _by_kind(inbox.conversations_for(_actor(operator_a.user)), "FIKISHA_UPDATE")
    # ... a stranger is not.
    assert inbox.conversations_for(_actor(stranger_business)) == []


def test_a_business_viewer_does_not_get_notes_the_notes_endpoint_refuses_them(
    offers: dict[str, Any],
    requested_job: Any,
    verified_business: Any,
    owner_actor: Any,
    ops_officer: Any,
    make_user: Callable,
    _actor: Callable,
) -> None:
    """``jobs_visible_to`` lists a VIEWER's business jobs, but ``job.read``
    (the notes endpoint) only admits OWNER/DISPATCHER: the inbox must follow
    the endpoint, not the wider list."""
    from fikisha.business.models import BusinessRole
    from fikisha.business.services import add_member
    from fikisha.jobs import job_authz, ops

    viewer = make_user("+254720000077")
    add_member(
        actor=owner_actor, business=verified_business, phone=viewer.phone, role=BusinessRole.VIEWER
    )
    ops.add_note(actor=_actor(ops_officer), job_id=requested_job.id, text="Driver running late")

    assert job_authz.jobs_visible_to(_actor(viewer)).filter(id=requested_job.id).exists()
    assert not job_authz.is_job_party(_actor(viewer), requested_job)
    assert _by_kind(inbox.conversations_for(_actor(viewer)), "FIKISHA_UPDATE") == []
    assert _by_kind(inbox.conversations_for(owner_actor), "FIKISHA_UPDATE")


def test_an_offer_posted_by_staff_is_credited_to_fikisha_not_the_counterparty(
    offers: dict[str, Any],
    requested_job: Any,
    operator_a: Any,
    owner_actor: Any,
    platform_admin: Any,
    _actor: Callable,
) -> None:
    from fikisha.negotiation import services as negotiation

    negotiation.propose(
        actor=_actor(platform_admin),
        job_id=requested_job.id,
        operator_id=operator_a.id,
        amount_kes=250_000,
    )
    [item] = [
        i
        for i in inbox.conversations_for(owner_actor)
        if i["conversation_key"] == f"offer:{offers['a']}"
    ]
    assert item["from_fikisha"] is True
    assert item["from_viewer"] is False
    assert item["unread"] is True
    assert item["amount_kes"] == 250_000


def test_incident_activity_is_unread_only_when_someone_else_wrote_it(
    offers: dict[str, Any],
    requested_job: Any,
    owner_actor: Any,
    operator_a: Any,
    ops_officer: Any,
    _actor: Callable,
) -> None:
    from fikisha.incidents import services as incidents

    incident = incidents.report_incident(
        actor=owner_actor, job_id=requested_job.id, type="DELAY", description="Goods not ready"
    )
    [item] = _by_kind(inbox.conversations_for(owner_actor), "INCIDENT")
    assert item["conversation_key"] == f"incident:{incident.id}"
    assert item["link"] == f"/incidents/{incident.id}"
    assert item["unread"] is False  # the business reported it itself

    incidents.add_statement(actor=_actor(ops_officer), incident_id=incident.id, text="We are on it")
    [item] = _by_kind(inbox.conversations_for(owner_actor), "INCIDENT")
    assert item["unread"] is True
    assert item["preview"] == "We are on it"

    # An operator that has only negotiated is not an incident party.
    assert _by_kind(inbox.conversations_for(_actor(operator_a.user)), "INCIDENT") == []


# ─── read markers ─────────────────────────────────────────────────────
def test_marking_read_clears_unread_until_the_other_side_writes_again(
    offers: dict[str, Any], owner_actor: Any, operator_a: Any, _actor: Callable
) -> None:
    from fikisha.negotiation import services as negotiation

    key = f"offer:{offers['a']}"
    assert _unread(owner_actor)[key] is True

    inbox.mark_read(actor=owner_actor, conversation_key=key)
    unread = _unread(owner_actor)
    assert unread[key] is False
    assert unread[f"offer:{offers['b']}"] is True  # other threads untouched

    negotiation.counter(actor=_actor(operator_a.user), thread_id=offers["a"], amount_kes=235_000)
    assert _unread(owner_actor)[key] is True


def test_read_markers_are_per_person(
    offers: dict[str, Any],
    owner_actor: Any,
    verified_business: Any,
    make_user: Callable,
    _actor: Callable,
) -> None:
    from fikisha.business.models import BusinessMembership, BusinessRole, MembershipStatus

    dispatcher = make_user("+254720000055")
    BusinessMembership.objects.create(
        business=verified_business,
        user=dispatcher,
        role=BusinessRole.DISPATCHER,
        status=MembershipStatus.ACTIVE,
    )
    key = f"offer:{offers['a']}"
    inbox.mark_read(actor=owner_actor, conversation_key=key)
    assert _unread(_actor(dispatcher))[key] is True


@pytest.mark.parametrize(
    "key",
    ["", "offer:", "offer:not-a-uuid", "job:01a0c3e0-cf3f-7b8a-9ab8-f8b3701fe0c4", "x" * 200],
)
def test_mark_read_rejects_anything_but_a_conversation_key(owner_actor: Any, key: str) -> None:
    with pytest.raises(inbox.InvalidConversationKey):
        inbox.mark_read(actor=owner_actor, conversation_key=key)


# ─── API ──────────────────────────────────────────────────────────────
def test_api_lists_with_unread_count_and_marks_read(
    offers: dict[str, Any], business_owner: Any, client_for: Callable
) -> None:
    client = client_for(business_owner)
    res = client.get("/api/v1/messages")
    assert res.status_code == 200
    body = res.json()
    assert set(body) == {"data", "page", "unread_count"}
    assert body["unread_count"] == 2
    assert {"conversation_key", "kind", "job_id", "job_reference", "at", "unread", "link"} <= set(
        body["data"][0]
    )

    res = client.post(
        "/api/v1/messages/read", {"conversation_key": f"offer:{offers['a']}"}, format="json"
    )
    assert res.status_code == 204
    assert client.get("/api/v1/messages").json()["unread_count"] == 1

    res = client.post("/api/v1/messages/read", {"conversation_key": "nope"}, format="json")
    assert res.status_code == 400
    assert res.json()["code"] == "inbox_invalid_conversation_key"


def test_api_requires_sign_in(api: Any) -> None:
    assert api.get("/api/v1/messages").status_code == 401
    res = api.post("/api/v1/messages/read", {"conversation_key": "x"}, format="json")
    assert res.status_code == 401


def test_api_pages_forward_without_overlap(
    offers: dict[str, Any], business_owner: Any, client_for: Callable
) -> None:
    client = client_for(business_owner)
    first = client.get("/api/v1/messages?limit=1").json()
    assert len(first["data"]) == 1
    assert first["page"]["next_cursor"]
    second = client.get(f"/api/v1/messages?limit=1&cursor={first['page']['next_cursor']}").json()
    assert len(second["data"]) == 1
    assert second["data"][0]["conversation_key"] != first["data"][0]["conversation_key"]
    assert second["page"]["next_cursor"] is None
    assert second["unread_count"] == 2  # the whole inbox, not the page

    assert client.get("/api/v1/messages?cursor=garbage!!").status_code == 400


# ─── cost ────────────────────────────────────────────────────────────
def _another_requested_job(business: Any, owner: Any, actor: Any) -> Any:
    """A second published job on the same business, built like
    negotiation's ``requested_job`` fixture."""
    from fikisha.jobs.constants import JobStatus
    from fikisha.jobs.models import CargoDetails, Job, JobLocation, VehicleRequirement
    from fikisha.jobs.service import TransitionContext, transition

    job = Job.objects.create(
        business=business,
        created_by=owner,
        status=JobStatus.DRAFT,
        pickup_location=JobLocation.objects.create(
            type="PICKUP", source_kind="AD_HOC", address_text="Depot"
        ),
        destination_location=JobLocation.objects.create(
            type="DESTINATION", source_kind="AD_HOC", address_text="Shop"
        ),
        cargo=CargoDetails.objects.create(
            description="10 cartons", declared_value_kes=1_200_000, handling_flags=[]
        ),
        vehicle_requirement=VehicleRequirement.objects.create(
            min_payload_kg=500, required_vehicle_class_codes=[]
        ),
        proposed_price_kes=250_000,
        declared_value_kes=1_200_000,
    )
    transition(
        job_id=job.id,
        to=JobStatus.REQUESTED,
        actor=actor,
        context=TransitionContext(data={"initiator_tokens": ["BUSINESS_OWNER_OR_DISPATCHER"]}),
    )
    return job


def test_the_query_count_does_not_grow_with_the_number_of_jobs(
    offers: dict[str, Any],
    verified_business: Any,
    business_owner: Any,
    owner_actor: Any,
    operator_a: Any,
    ops_officer: Any,
    _actor: Callable,
) -> None:
    """ADR-2D-37: one batch read per source, membership lookups memoized, so
    the inbox costs the same for 1 job as for 4 (for both sides)."""
    from django.db import connection
    from django.test.utils import CaptureQueriesContext

    from fikisha.jobs import ops
    from fikisha.negotiation import services as negotiation

    def cost(actor: Any) -> tuple[int, int]:
        with CaptureQueriesContext(connection) as ctx:
            items = inbox.conversations_for(actor)
        return len(ctx.captured_queries), len(items)

    operator_actor = _actor(operator_a.user)
    before = {"business": cost(owner_actor), "operator": cost(operator_actor)}

    for _ in range(3):
        job = _another_requested_job(verified_business, business_owner, owner_actor)
        negotiation.propose(
            actor=operator_actor, job_id=job.id, operator_id=operator_a.id, amount_kes=240_000
        )
        ops.add_note(actor=_actor(ops_officer), job_id=job.id, text="Checked in")

    after = {"business": cost(owner_actor), "operator": cost(operator_actor)}
    for side in ("business", "operator"):
        assert after[side][1] > before[side][1]  # more conversations ...
        assert after[side][0] == before[side][0]  # ... for the same number of queries
