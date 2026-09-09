"""Operators module — profile CRUD, operating locations, association (Phase 2B §34)."""

from __future__ import annotations

from typing import Any

import pytest

from fikisha.audit.models import AuditLogEntry
from fikisha.operators.models import BaseMembership, OperatingBase, OperatorProfile, OperatorStatus

pytestmark = pytest.mark.django_db


def _create_profile(client: Any, **over: Any) -> dict:
    body = {"full_name": "John Kamau", **over}
    r = client.post("/api/v1/operators", body, format="json")
    assert r.status_code == 201, r.content
    return r.data


class TestOperatorProfile:
    def test_create_and_me(self, user: Any, client_for: Any) -> None:
        client = client_for(user)
        data = _create_profile(client)
        assert data["full_name"] == "John Kamau"
        assert data["status"] == "PENDING"
        assert OperatorProfile.objects.filter(user=user).count() == 1
        assert AuditLogEntry.objects.filter(action="operator.created").exists()

        me = client.get("/api/v1/operators/me")
        assert me.status_code == 200
        assert me.data["id"] == data["id"]

    def test_me_is_404_without_a_profile(self, user: Any, client_for: Any) -> None:
        r = client_for(user).get("/api/v1/operators/me")
        assert r.status_code == 404

    def test_one_profile_per_user(self, user: Any, client_for: Any) -> None:
        client = client_for(user)
        _create_profile(client)
        r = client.post("/api/v1/operators", {"full_name": "Twin"}, format="json")
        assert r.status_code == 409

    def test_owner_updates_own_profile(self, user: Any, client_for: Any) -> None:
        client = client_for(user)
        pid = _create_profile(client)["id"]
        r = client.patch(
            f"/api/v1/operators/{pid}", {"display_name": "Kamau Transporters"}, format="json"
        )
        assert r.status_code == 200
        assert r.data["display_name"] == "Kamau Transporters"

    def test_owner_cannot_change_status(self, user: Any, client_for: Any) -> None:
        client = client_for(user)
        pid = _create_profile(client)["id"]
        r = client.patch(f"/api/v1/operators/{pid}", {"status": "ACTIVE"}, format="json")
        assert r.status_code == 403

    def test_admin_can_change_status(self, user: Any, client_for: Any, admin_client: Any) -> None:
        pid = _create_profile(client_for(user))["id"]
        r = admin_client.patch(f"/api/v1/operators/{pid}", {"status": "SUSPENDED"}, format="json")
        assert r.status_code == 200
        assert r.data["status"] == "SUSPENDED"


class TestOperatingLocations:
    def test_operator_creates_a_base_and_lists_it(self, user: Any, client_for: Any) -> None:
        client = client_for(user)
        _create_profile(client)
        r = client.post(
            "/api/v1/operating-locations",
            {"name": "Kitengela Stage", "type": "STAGE", "zone_code": "KITENGELA"},
            format="json",
        )
        assert r.status_code == 201, r.content
        assert r.data["zone_code"] == "KITENGELA"
        assert AuditLogEntry.objects.filter(action="operating_location.created").exists()

        listing = client.get("/api/v1/operating-locations").data["data"]
        assert any(b["name"] == "Kitengela Stage" for b in listing)

    def test_a_non_operator_cannot_create_a_base(self, user: Any, client_for: Any) -> None:
        r = client_for(user).post(
            "/api/v1/operating-locations", {"name": "X", "type": "YARD"}, format="json"
        )
        assert r.status_code == 403

    def test_only_the_creator_can_edit_a_base(
        self, user: Any, other_user: Any, client_for: Any
    ) -> None:
        creator = client_for(user)
        _create_profile(creator)
        base_id = creator.post(
            "/api/v1/operating-locations", {"name": "Yard A", "type": "YARD"}, format="json"
        ).data["id"]

        intruder = client_for(other_user)
        _create_profile(intruder)
        r = intruder.patch(
            f"/api/v1/operating-locations/{base_id}", {"name": "Yard Hijack"}, format="json"
        )
        assert r.status_code == 403
        # ...but any authenticated user may read it (a stage is a public place).
        assert intruder.get(f"/api/v1/operating-locations/{base_id}").status_code == 200

    def test_associate_and_end_association(self, user: Any, client_for: Any) -> None:
        client = client_for(user)
        pid = _create_profile(client)["id"]
        base_id = client.post(
            "/api/v1/operating-locations", {"name": "Base 1", "type": "BASE"}, format="json"
        ).data["id"]

        assoc = client.post(
            f"/api/v1/operators/{pid}/bases", {"base_id": base_id, "role": "owner"}, format="json"
        )
        assert assoc.status_code == 201
        membership_id = assoc.data["id"]
        assert BaseMembership.objects.get(id=membership_id).status == "ACTIVE"

        bases = client.get(f"/api/v1/operators/{pid}/bases").data["data"]
        assert len(bases) == 1 and bases[0]["base_name"] == "Base 1"

        assert client.delete(f"/api/v1/operators/{pid}/bases/{membership_id}").status_code == 204
        assert BaseMembership.objects.get(id=membership_id).status == "INACTIVE"

    def test_cannot_associate_another_operators_profile(
        self, user: Any, other_user: Any, client_for: Any
    ) -> None:
        owner = client_for(user)
        pid = _create_profile(owner)["id"]
        base_id = owner.post(
            "/api/v1/operating-locations", {"name": "B", "type": "BASE"}, format="json"
        ).data["id"]

        intruder = client_for(other_user)
        _create_profile(intruder)
        r = intruder.post(f"/api/v1/operators/{pid}/bases", {"base_id": base_id}, format="json")
        assert r.status_code == 403


def test_operator_status_values() -> None:
    assert set(OperatorStatus.values) == {
        "PENDING",
        "ACTIVE",
        "RESTRICTED",
        "SUSPENDED",
        "OFFBOARDED",
    }


def test_base_membership_needs_exactly_one_party(db: Any) -> None:
    from django.db import IntegrityError

    base = OperatingBase.objects.create(name="X", type="STAGE")
    with pytest.raises(IntegrityError):
        BaseMembership.objects.create(base=base)  # neither operator nor group
