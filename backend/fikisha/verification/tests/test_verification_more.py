"""Verification — service paths and subject-ownership authz not covered elsewhere."""

from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal
from typing import Any

import pytest
from django.utils import timezone

from fikisha.common.exceptions import DomainError
from fikisha.identity.authz.actors import actor_from_user
from fikisha.operators import services as op_services
from fikisha.vehicles import services as veh_services
from fikisha.verification import authz, services
from fikisha.verification.models import Domain, State

pytestmark = pytest.mark.django_db


def _actor(u: Any) -> Any:
    return actor_from_user(u)


@pytest.fixture
def profile(user: Any) -> Any:
    return op_services.create_profile(actor=_actor(user), full_name="Op")


def test_request_info_requires_a_note(user: Any, ops_officer: Any, profile: Any) -> None:
    rec = services.submit(
        actor=_actor(user),
        subject=profile,
        domain=Domain.IDENTITY,
        evidence_items=[{"data": b"x", "content_type": "image/jpeg", "kind": "NATIONAL_ID"}],
    )
    services.start_review(reviewer=_actor(ops_officer), record=rec)
    with pytest.raises(DomainError):
        services.request_info(reviewer=_actor(ops_officer), record=rec, note="   ")


def test_good_conduct_gets_a_recheck_expiry_when_no_doc_date(
    user: Any, ops_officer: Any, profile: Any
) -> None:
    rec = services.submit(
        actor=_actor(user),
        subject=profile,
        domain=Domain.GOOD_CONDUCT,
        evidence_items=[
            {"data": b"cert", "content_type": "application/pdf", "kind": "GOOD_CONDUCT_CERT"}
        ],
    )
    services.start_review(reviewer=_actor(ops_officer), record=rec)
    rec = services.approve(reviewer=_actor(ops_officer), record=rec)  # no explicit expiry
    assert rec.expires_at is not None
    assert rec.expires_at > timezone.now() + timedelta(days=300)


def test_suggested_expiry_from_earliest_evidence_date(
    user: Any, ops_officer: Any, profile: Any
) -> None:
    soon = date.today() + timedelta(days=40)
    rec = services.submit(
        actor=_actor(user),
        subject=profile,
        domain=Domain.LICENCE,
        evidence_items=[
            {
                "data": b"lic",
                "content_type": "image/jpeg",
                "kind": "DRIVING_LICENCE",
                "expires_at": soon,
            }
        ],
    )
    services.start_review(reviewer=_actor(ops_officer), record=rec)
    rec = services.approve(reviewer=_actor(ops_officer), record=rec)
    assert rec.expires_at is not None and rec.expires_at.date() == soon


def test_invalidate_association_resets_the_record(
    user: Any, ops_officer: Any, profile: Any
) -> None:
    vehicle = veh_services.register_vehicle(
        actor=_actor(user),
        owner_operator=profile,
        vehicle_class_code="PICKUP",
        registration="KAA 7",
        capacity_value=Decimal("1"),
    )
    rec = services.submit(
        actor=_actor(user),
        subject=vehicle,
        domain=Domain.ASSOCIATION,
        evidence_items=[
            {"data": b"consent", "content_type": "application/pdf", "kind": "OWNER_CONSENT"}
        ],
    )
    services.start_review(reviewer=_actor(ops_officer), record=rec)
    services.approve(reviewer=_actor(ops_officer), record=rec)

    services.invalidate_association(
        actor=_actor(ops_officer), vehicle=vehicle, reason="control changed"
    )
    rec.refresh_from_db()
    assert rec.state == State.NOT_SUBMITTED
    assert rec.decisions.filter(action="REJECT").exists()


class TestSubjectOwnershipAuthz:
    def test_owns_vehicle_subject(self, user: Any, profile: Any) -> None:
        vehicle = veh_services.register_vehicle(
            actor=_actor(user),
            owner_operator=profile,
            vehicle_class_code="PICKUP",
            registration="KAA 8",
            capacity_value=Decimal("1"),
        )
        rec = services.get_or_create_record(subject=vehicle, domain=Domain.VEHICLE)
        assert authz.owns_subject(_actor(user), rec) is True

    def test_owns_base_subject(self, user: Any) -> None:
        prof = op_services.create_profile(actor=_actor(user), full_name="Op2")
        assert prof
        base = op_services.create_base(actor=_actor(user), data={"name": "Stage", "type": "STAGE"})
        rec = services.get_or_create_record(subject=base, domain=Domain.BASE)
        assert authz.owns_subject(_actor(user), rec) is True

    def test_stranger_does_not_own_subject(self, user: Any, other_user: Any, profile: Any) -> None:
        rec = services.get_or_create_record(subject=profile, domain=Domain.IDENTITY)
        op_services.create_profile(actor=_actor(other_user), full_name="Stranger")
        assert authz.owns_subject(_actor(other_user), rec) is False


def test_requirements_status_lists_required_and_extra(
    user: Any, ops_officer: Any, profile: Any
) -> None:
    rec = services.submit(
        actor=_actor(user),
        subject=profile,
        domain=Domain.DOCUMENT,
        evidence_items=[{"data": b"d", "content_type": "application/pdf", "kind": "OTHER"}],
    )
    services.start_review(reviewer=_actor(ops_officer), record=rec)
    services.approve(reviewer=_actor(ops_officer), record=rec)

    rows = services.requirements_status(profile)
    by_domain = {r["domain"]: r for r in rows}
    assert by_domain["IDENTITY"]["mandatory"] is True
    assert by_domain["IDENTITY"]["state"] == "NOT_SUBMITTED"
    assert by_domain["DOCUMENT"]["mandatory"] is False
    assert by_domain["DOCUMENT"]["state"] == "VERIFIED"
