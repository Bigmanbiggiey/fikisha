"""Incident review workflow (Ops-Officer / Admin, config-driven permissions)
and escalation (admin-only, FR-D-8)."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

import pytest

from fikisha.incidents.constants import DisputeStatus, IncidentStatus, IncidentType
from fikisha.incidents.errors import NotAuthorisedForIncidentReview, RationaleRequired
from fikisha.incidents.services import (
    escalate,
    open_dispute,
    report_incident,
    start_amicable_window,
    start_review,
)

pytestmark = pytest.mark.django_db


@pytest.fixture
def an_incident(make_assigned_job: Callable, business_owner_actor: Any) -> Any:
    job = make_assigned_job()
    return report_incident(actor=business_owner_actor, job_id=job.id, type=IncidentType.MISCONDUCT)


def test_ops_officer_may_start_review_via_the_approved_permission_string(
    an_incident: Any, ops_actor: Any
) -> None:
    """``role_permissions.OPERATIONS_OFFICER`` already carries
    ``incident.intake`` (pre-approved platform config) — Step 8 consumes it,
    does not invent it."""
    incident = start_review(actor=ops_actor, incident_id=an_incident.id)
    assert incident.status == IncidentStatus.UNDER_REVIEW
    assert incident.owner_admin_id == ops_actor.user.id


def test_a_business_party_may_not_start_review(an_incident: Any, business_owner_actor: Any) -> None:
    with pytest.raises(NotAuthorisedForIncidentReview):
        start_review(actor=business_owner_actor, incident_id=an_incident.id)


def test_an_ordinary_authenticated_user_with_no_admin_standing_may_not_start_review(
    an_incident: Any, make_user: Callable, actor_for: Callable
) -> None:
    """STRIDE regression: an authenticated actor with no ``AdminProfile`` and no
    ``RoleAssignment`` at all — not even a job party — is refused. Permission
    is config-driven (``role_permissions``) via ``actor_has_permission``, never
    a blanket "any authenticated caller" fallback."""
    stranger = make_user("+254700000778")
    stranger_actor = actor_for(stranger)
    assert stranger_actor.is_admin is False
    assert stranger_actor.roles == frozenset()

    with pytest.raises(NotAuthorisedForIncidentReview):
        start_review(actor=stranger_actor, incident_id=an_incident.id)


def test_platform_admin_may_always_start_review(an_incident: Any, admin_actor: Any) -> None:
    incident = start_review(actor=admin_actor, incident_id=an_incident.id)
    assert incident.status == IncidentStatus.UNDER_REVIEW


def test_ops_officer_may_open_the_amicable_window(an_incident: Any, ops_actor: Any) -> None:
    incident = start_amicable_window(actor=ops_actor, incident_id=an_incident.id)
    assert incident.status == IncidentStatus.AMICABLE_PENDING


def test_admin_review_is_not_mandatory_before_amicable_resolution(
    an_incident: Any, ops_actor: Any
) -> None:
    """dispute-and-liability.md §4: amicable-first, admin review is not
    mandatory for every incident — an Ops Officer may go straight from OPEN to
    AMICABLE_PENDING without a prior ``start_review`` call."""
    assert an_incident.status == IncidentStatus.OPEN
    incident = start_amicable_window(actor=ops_actor, incident_id=an_incident.id)
    assert incident.status == IncidentStatus.AMICABLE_PENDING


def test_review_actions_are_audited(an_incident: Any, ops_actor: Any) -> None:
    from fikisha.audit.models import AuditLogEntry

    start_review(actor=ops_actor, incident_id=an_incident.id)
    assert AuditLogEntry.objects.filter(
        action="incident.review.started", entity_id=an_incident.id
    ).exists()


# ─── escalation (admin-only; FR-D-8) ────────────────────────────────
def test_admin_may_escalate_a_critical_incident(an_incident: Any, admin_actor: Any) -> None:
    escalation = escalate(
        actor=admin_actor,
        incident_id=an_incident.id,
        reason="Repeated misconduct allegations; advising the founder.",
        advised_external_options=True,
    )
    assert escalation.incident_id == an_incident.id
    assert escalation.advised_external_options is True
    an_incident.refresh_from_db()
    assert an_incident.status == IncidentStatus.ESCALATED


def test_escalation_links_the_jobs_open_dispute_when_one_exists(
    an_incident: Any, business_owner_actor: Any, admin_actor: Any
) -> None:
    dispute, _view = open_dispute(
        actor=business_owner_actor, job_id=an_incident.job_id, incident_ids=[an_incident.id]
    )
    escalation = escalate(
        actor=admin_actor, incident_id=an_incident.id, reason="Escalating the live dispute too."
    )
    assert escalation.dispute_id == dispute.id
    dispute.refresh_from_db()
    assert dispute.status == DisputeStatus.ESCALATED


def test_a_non_admin_may_not_escalate(an_incident: Any, business_owner_actor: Any) -> None:
    with pytest.raises(NotAuthorisedForIncidentReview):
        escalate(actor=business_owner_actor, incident_id=an_incident.id, reason="trying anyway")


def test_an_ops_officer_may_not_escalate_only_a_platform_admin_can(
    an_incident: Any, ops_actor: Any
) -> None:
    """STRIDE regression: escalation to the founder is not among the specific
    actions ``role_permissions.OPERATIONS_OFFICER`` grants — an Ops Officer
    (who *is* "an admin" in the general ``is_admin()`` sense) must still be
    refused here."""
    with pytest.raises(NotAuthorisedForIncidentReview):
        escalate(actor=ops_actor, incident_id=an_incident.id, reason="Ops Officer escalating")


def test_escalation_requires_a_reason(an_incident: Any, admin_actor: Any) -> None:
    with pytest.raises(RationaleRequired):
        escalate(actor=admin_actor, incident_id=an_incident.id, reason="  ")


def test_escalation_is_audited(an_incident: Any, admin_actor: Any) -> None:
    from fikisha.audit.models import AuditLogEntry

    escalation = escalate(actor=admin_actor, incident_id=an_incident.id, reason="on the record")
    assert AuditLogEntry.objects.filter(
        action="incident.escalated", entity_id=escalation.id
    ).exists()


def test_escalation_is_append_only_at_the_database(an_incident: Any, admin_actor: Any) -> None:
    from django.db import DatabaseError, connection, transaction

    escalation = escalate(actor=admin_actor, incident_id=an_incident.id, reason="original reason")
    with pytest.raises(DatabaseError):
        with transaction.atomic():
            with connection.cursor() as cur:
                cur.execute(
                    "UPDATE escalation SET reason = 'changed' WHERE id = %s", [str(escalation.id)]
                )
