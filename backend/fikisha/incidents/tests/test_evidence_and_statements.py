"""Incident evidence + statements: authorized/unauthorized attach, cross-job
rejection, append-only enforcement, actor attribution."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

import pytest

from fikisha.incidents.errors import (
    IncidentAlreadyResolved,
    NotIncidentParty,
    StatementTextRequired,
)
from fikisha.incidents.models import IncidentStatement
from fikisha.incidents.services import add_statement, attach_evidence, report_incident

pytestmark = pytest.mark.django_db


@pytest.fixture
def an_incident(make_assigned_job: Callable, business_owner_actor: Any) -> Any:
    from fikisha.incidents.constants import IncidentType

    job = make_assigned_job()
    return report_incident(actor=business_owner_actor, job_id=job.id, type=IncidentType.DAMAGE)


# ─── evidence ────────────────────────────────────────────────────────
def test_a_job_party_may_attach_evidence(an_incident: Any, driver_actor: Any) -> None:
    row = attach_evidence(
        actor=driver_actor,
        incident_id=an_incident.id,
        data=b"\xff\xd8\xff fake jpeg bytes",
        content_type="image/jpeg",
        caption="goods on arrival",
    )
    assert row.incident_id == an_incident.id
    assert row.caption == "goods on arrival"
    assert row.uploaded_by_kind == "OPERATOR"


def test_an_unrelated_actor_may_not_attach_evidence(
    an_incident: Any, other_business_actor: Any
) -> None:
    with pytest.raises(NotIncidentParty):
        attach_evidence(
            actor=other_business_actor,
            incident_id=an_incident.id,
            data=b"bytes",
            content_type="image/jpeg",
        )


def test_evidence_cannot_be_attached_to_a_resolved_incident(
    an_incident: Any, business_owner_actor: Any
) -> None:
    an_incident.status = "RESOLVED"
    an_incident.save(update_fields=["status"])
    with pytest.raises(IncidentAlreadyResolved):
        attach_evidence(
            actor=business_owner_actor,
            incident_id=an_incident.id,
            data=b"bytes",
            content_type="image/jpeg",
        )


def test_evidence_is_append_only_at_the_database(
    an_incident: Any, business_owner_actor: Any
) -> None:
    from django.db import DatabaseError, connection, transaction

    row = attach_evidence(
        actor=business_owner_actor,
        incident_id=an_incident.id,
        data=b"bytes",
        content_type="image/jpeg",
    )
    with pytest.raises(DatabaseError):
        with transaction.atomic():
            with connection.cursor() as cur:
                cur.execute(
                    "UPDATE incident_evidence SET caption = 'x' WHERE id = %s", [str(row.id)]
                )
    with pytest.raises(DatabaseError):
        with transaction.atomic():
            with connection.cursor() as cur:
                cur.execute("DELETE FROM incident_evidence WHERE id = %s", [str(row.id)])


def test_evidence_uses_the_shared_evidence_architecture_not_a_parallel_store(
    an_incident: Any, business_owner_actor: Any
) -> None:
    from fikisha.evidence.models import EvidenceObject

    row = attach_evidence(
        actor=business_owner_actor,
        incident_id=an_incident.id,
        data=b"bytes",
        content_type="image/jpeg",
    )
    obj = EvidenceObject.objects.get(id=row.evidence_object_id)
    assert obj.purpose == "INCIDENT_EVIDENCE"
    assert obj.linked_entity_type == "incident"
    assert obj.linked_entity_id == an_incident.id


# ─── statements ──────────────────────────────────────────────────────
def test_a_job_party_may_add_a_statement(an_incident: Any, business_owner_actor: Any) -> None:
    statement = add_statement(
        actor=business_owner_actor, incident_id=an_incident.id, text="Here is what happened."
    )
    assert statement.incident_id == an_incident.id
    assert statement.party_kind == "BUSINESS"
    assert statement.party_user_id == business_owner_actor.user.id


def test_an_unrelated_actor_may_not_add_a_statement(
    an_incident: Any, other_business_actor: Any
) -> None:
    with pytest.raises(NotIncidentParty):
        add_statement(actor=other_business_actor, incident_id=an_incident.id, text="butting in")


def test_empty_statement_text_is_rejected(an_incident: Any, business_owner_actor: Any) -> None:
    with pytest.raises(StatementTextRequired):
        add_statement(actor=business_owner_actor, incident_id=an_incident.id, text="   ")


def test_statement_history_is_immutable(an_incident: Any, business_owner_actor: Any) -> None:
    from django.db import DatabaseError, connection, transaction

    statement = add_statement(
        actor=business_owner_actor, incident_id=an_incident.id, text="original account"
    )
    with pytest.raises(DatabaseError):
        with transaction.atomic():
            with connection.cursor() as cur:
                cur.execute(
                    "UPDATE incident_statement SET text = 'edited' WHERE id = %s",
                    [str(statement.id)],
                )


def test_multiple_statements_preserve_full_append_only_history(
    an_incident: Any, business_owner_actor: Any, driver_actor: Any
) -> None:
    add_statement(actor=business_owner_actor, incident_id=an_incident.id, text="business side")
    add_statement(actor=driver_actor, incident_id=an_incident.id, text="operator side")
    statements = list(IncidentStatement.objects.filter(incident=an_incident).order_by("created_at"))
    assert [s.party_kind for s in statements] == ["BUSINESS", "OPERATOR"]


def test_statement_addition_is_audited(an_incident: Any, business_owner_actor: Any) -> None:
    from fikisha.audit.models import AuditLogEntry

    statement = add_statement(
        actor=business_owner_actor, incident_id=an_incident.id, text="on the record"
    )
    assert AuditLogEntry.objects.filter(
        action="incident.statement.added", entity_id=statement.id
    ).exists()


def test_evidence_row_attribution_matches_the_actual_uploader(
    an_incident: Any, driver_actor: Any
) -> None:
    row = attach_evidence(
        actor=driver_actor, incident_id=an_incident.id, data=b"bytes", content_type="image/jpeg"
    )
    assert row.uploaded_by_user_id == driver_actor.user.id


def test_every_incident_party_kind_maps_to_a_valid_evidence_uploader_kind() -> None:
    """Regression: ``PartyKind`` (incidents-local, includes ``GROUP``) and
    ``evidence.UploaderKind`` (predates Incidents, no ``GROUP`` member) are
    different enums. A ``GROUP``-party actor's evidence upload must still
    write a value ``evidence.models.EvidenceObject.uploaded_by_kind`` actually
    recognises — Django ``choices=`` is not DB-enforced, so a missing mapping
    entry would silently persist an out-of-choices string instead of raising."""
    from fikisha.evidence.models import UploaderKind
    from fikisha.incidents.constants import PartyKind
    from fikisha.incidents.services import _EVIDENCE_UPLOADER_KIND

    for party_kind in PartyKind.values:
        assert party_kind in _EVIDENCE_UPLOADER_KIND, party_kind
        assert _EVIDENCE_UPLOADER_KIND[party_kind] in UploaderKind.values
