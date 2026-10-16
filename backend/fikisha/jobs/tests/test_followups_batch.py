"""Founder decisions 2026-10-14, follow-ups batch:

- phones hidden from operators until the job is assigned to them (closes
  ADR-2D-36);
- a Platform Admin can reverse a high-value rejection, with a reason;
- the recipient page uses the same 6-character reference as the app.
"""

from __future__ import annotations

from collections.abc import Callable
from datetime import timedelta
from typing import Any

import pytest
from django.db import connection, transaction
from django.db.utils import IntegrityError
from django.utils import timezone

from fikisha.audit.models import AuditLogEntry
from fikisha.common.models import AppendOnlyModelError
from fikisha.jobs import high_value
from fikisha.jobs.constants import JobStatus
from fikisha.jobs.errors import HighValueAlreadyDecided, NotAuthorisedToAssign
from fikisha.jobs.models import HighValueReversal
from fikisha.jobs.service import TransitionContext, transition

pytestmark = pytest.mark.django_db

API = "/api/v1"
PICKUP_PHONE = "+254711222333"
RECIPIENT_PHONE = "+254711444555"


# ─── phones before assignment ───────────────────────────────────────────
@pytest.fixture
def negotiated_job(
    draft_job: Any, admin_actor: Any, make_verified_operator: Callable, actor_for: Callable
) -> tuple[Any, Any]:
    from fikisha.negotiation import services as negotiation

    draft_job.pickup_location.contact_phone = PICKUP_PHONE
    draft_job.pickup_location.save(update_fields=["contact_phone"])
    draft_job.recipient_phone = RECIPIENT_PHONE
    draft_job.recipient_name = "John Kariuki"
    draft_job.save(update_fields=["recipient_phone", "recipient_name"])
    transition(
        job_id=draft_job.id,
        to=JobStatus.REQUESTED,
        actor=admin_actor,
        context=TransitionContext(data={"initiator_tokens": ["ADMIN"]}),
    )
    bidder = make_verified_operator("+254733500001", "Bidding Operator")
    negotiation.propose(
        actor=actor_for(bidder.user), job_id=draft_job.id, operator_id=bidder.id, amount_kes=260_000
    )
    draft_job.refresh_from_db()
    return draft_job, bidder


def _phones(payload: dict[str, Any]) -> tuple[str, str, bool]:
    return (
        payload["pickup_location"]["contact_phone"],
        payload["recipient_phone"],
        payload["contacts_hidden"],
    )


def test_a_negotiating_operator_sees_names_not_numbers(
    client_for: Callable, negotiated_job: tuple[Any, Any]
) -> None:
    job, bidder = negotiated_job
    r = client_for(bidder.user).get(f"{API}/jobs/{job.id}")
    assert r.status_code == 200, r.content
    assert _phones(r.data) == ("", "", True)
    assert r.data["recipient_name"] == "John Kariuki"
    assert PICKUP_PHONE not in str(r.content) and RECIPIENT_PHONE not in str(r.content)

    rows = client_for(bidder.user).get(f"{API}/jobs").data["data"]
    row = next(x for x in rows if x["id"] == str(job.id))
    assert _phones(row) == ("", "", True)


def test_the_business_and_staff_see_the_numbers(
    client_for: Callable, negotiated_job: tuple[Any, Any], user: Any, ops_officer: Any
) -> None:
    job, _ = negotiated_job
    for who in (user, ops_officer):
        r = client_for(who).get(f"{API}/jobs/{job.id}")
        assert r.status_code == 200, r.content
        assert _phones(r.data) == (PICKUP_PHONE, RECIPIENT_PHONE, False)


def test_open_work_hides_the_numbers(
    client_for: Callable,
    draft_job: Any,
    admin_actor: Any,
    eligible_driver: Any,
    eligible_vehicle: Any,
) -> None:
    draft_job.recipient_phone = RECIPIENT_PHONE
    draft_job.save(update_fields=["recipient_phone"])
    transition(
        job_id=draft_job.id,
        to=JobStatus.REQUESTED,
        actor=admin_actor,
        context=TransitionContext(data={"initiator_tokens": ["ADMIN"]}),
    )
    rows = client_for(eligible_driver.user).get(f"{API}/jobs/opportunities").data["data"]
    row = next(x for x in rows if x["id"] == str(draft_job.id))
    assert row["recipient_phone"] == "" and row["contacts_hidden"] is True


def test_confirmed_but_not_assigned_still_hides_then_assignment_reveals(
    client_for: Callable,
    make_confirmed_job: Callable,
    make_assigned_job: Callable,
    eligible_driver: Any,
) -> None:
    confirmed = make_confirmed_job(operator=eligible_driver)
    confirmed.recipient_phone = RECIPIENT_PHONE
    confirmed.save(update_fields=["recipient_phone"])
    r = client_for(eligible_driver.user).get(f"{API}/jobs/{confirmed.id}")
    assert r.data["contacts_hidden"] is True and r.data["recipient_phone"] == ""

    assigned = make_assigned_job(recipient_phone=RECIPIENT_PHONE, pickup_contact_phone=PICKUP_PHONE)
    r = client_for(eligible_driver.user).get(f"{API}/jobs/{assigned.id}")
    assert _phones(r.data) == (PICKUP_PHONE, RECIPIENT_PHONE, False)


# ─── reversible high-value rejection ────────────────────────────────────
HIGH = 50_000_000  # KES 500,000


@pytest.fixture
def rejected_job(make_confirmed_job: Callable, eligible_driver: Any, admin_actor: Any) -> Any:
    job = make_confirmed_job(operator=eligible_driver, declared_value_kes=HIGH)
    high_value.decide_high_value(
        actor=admin_actor, job_id=job.id, decision="REJECTED", rationale="Unverified cargo"
    )
    return job


def test_platform_admin_reverses_a_rejection_and_the_job_can_be_assigned(
    rejected_job: Any,
    admin_actor: Any,
    eligible_driver: Any,
    eligible_vehicle: Any,
    actor_for: Callable,
) -> None:
    from fikisha.jobs.assignment_candidates import candidates

    assert high_value.effective_decision(rejected_job) == ("REJECTED", True)
    assert candidates(actor=admin_actor, job_id=rejected_job.id)["blocked"] is not None

    result = high_value.reverse_rejection(
        actor=admin_actor, job_id=rejected_job.id, reason="Cargo documents verified by phone"
    )
    assert result["decision"] == "APPROVED"
    assert high_value.effective_decision(rejected_job) == ("APPROVED", True)
    assert candidates(actor=admin_actor, job_id=rejected_job.id)["blocked"] is None
    entry = AuditLogEntry.objects.get(action="job.highvalue.rejection_reversed")
    assert entry.after["reason"] == "Cargo documents verified by phone"

    with pytest.raises(HighValueAlreadyDecided):
        high_value.reverse_rejection(
            actor=admin_actor, job_id=rejected_job.id, reason="Second attempt here"
        )


def test_reversal_rules(
    rejected_job: Any,
    make_confirmed_job: Callable,
    eligible_driver: Any,
    admin_actor: Any,
    ops_officer: Any,
    actor_for: Callable,
) -> None:
    with pytest.raises(NotAuthorisedToAssign):
        high_value.reverse_rejection(
            actor=actor_for(ops_officer), job_id=rejected_job.id, reason="Ops tries to reverse it"
        )
    with pytest.raises(high_value.NotReversible):
        high_value.reverse_rejection(actor=admin_actor, job_id=rejected_job.id, reason="short")
    approved = make_confirmed_job(operator=eligible_driver, declared_value_kes=HIGH)
    high_value.decide_high_value(actor=admin_actor, job_id=approved.id, decision="APPROVED")
    with pytest.raises(high_value.NotReversible):
        high_value.reverse_rejection(
            actor=admin_actor, job_id=approved.id, reason="Nothing to reverse here"
        )
    assert not HighValueReversal.objects.exists()


def test_reversal_rows_are_append_only(rejected_job: Any, admin_actor: Any) -> None:
    high_value.reverse_rejection(
        actor=admin_actor, job_id=rejected_job.id, reason="Cargo documents verified"
    )
    row = HighValueReversal.objects.get()
    with pytest.raises(AppendOnlyModelError):
        row.save()
    with pytest.raises(IntegrityError), transaction.atomic(), connection.cursor() as cur:
        cur.execute("UPDATE high_value_reversal SET reason = 'edited' WHERE id = %s", [row.id])


def test_reversal_api_needs_platform_admin_and_a_fresh_step_up(
    client_for: Callable, rejected_job: Any, platform_admin: Any, ops_officer: Any
) -> None:
    from fikisha.identity.models import AuthSession

    url = f"{API}/jobs/{rejected_job.id}/high-value-decision/reverse"
    body = {"reason": "Cargo documents verified by phone"}

    stale = client_for(platform_admin)
    AuthSession.objects.filter(user=platform_admin).update(
        step_up_at=timezone.now() - timedelta(hours=1)
    )
    r = stale.post(url, body, format="json")
    assert r.status_code == 403 and r.json()["code"] == "step_up_required"

    r = client_for(ops_officer).post(url, body, format="json")
    assert r.status_code in (403, 422), r.content
    assert not HighValueReversal.objects.exists()

    r = client_for(platform_admin).post(url, body, format="json")
    assert r.status_code == 201, r.content

    detail = client_for(platform_admin).get(f"{API}/jobs/{rejected_job.id}").data
    assert detail["high_value_decision"] == "APPROVED"


# ─── 6-character references ─────────────────────────────────────────────
def test_recipient_page_uses_the_app_reference(make_assigned_job: Callable) -> None:
    from fikisha.jobs.ops import job_reference
    from fikisha.jobs.recipient import reissue_link

    job = make_assigned_job()
    _, token = reissue_link(job_id=job.id)
    from rest_framework.test import APIClient

    r = APIClient().get(f"{API}/r/{token}")
    assert r.status_code == 200, r.content
    assert r.data["delivery_reference"] == job_reference(job.id)
    assert len(r.data["delivery_reference"]) == 6
