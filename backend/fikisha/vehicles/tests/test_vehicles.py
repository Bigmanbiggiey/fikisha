"""Vehicles — registration, ownership, status, capacity (Phase 2C §28)."""

from __future__ import annotations

from typing import Any

import pytest

from fikisha.audit.models import AuditLogEntry
from fikisha.vehicles.models import Vehicle, VehicleStatus

pytestmark = pytest.mark.django_db


def _operator(client: Any, name: str = "Op") -> str:
    r = client.post("/api/v1/operators", {"full_name": name}, format="json")
    assert r.status_code == 201, r.content
    return r.data["id"]


def _register(client: Any, **over: Any) -> dict:
    body = {
        "vehicle_class": "PICKUP",
        "registration": "KAA 001A",
        "capacity_value": "800.00",
        "capacity_unit": "KG",
        **over,
    }
    r = client.post("/api/v1/vehicles", body, format="json")
    assert r.status_code == 201, r.content
    return r.data


class TestRegistration:
    def test_individual_operator_registers_a_vehicle(self, user: Any, client_for: Any) -> None:
        client = client_for(user)
        pid = _operator(client)
        data = _register(client, owner_operator_id=pid)
        assert data["controller_kind"] == "OPERATOR"
        assert data["vehicle_class"] == "PICKUP"
        assert data["status"] == "INACTIVE"
        assert Vehicle.objects.get(id=data["id"]).registration_normalized == "KAA001A"
        assert AuditLogEntry.objects.filter(action="vehicle.registered").exists()

    def test_group_manager_registers_a_group_vehicle(
        self, user: Any, other_user: Any, client_for: Any
    ) -> None:
        owner = client_for(user)
        _operator(owner, "Group owner")
        gid = owner.post("/api/v1/groups", {"name": "Movers", "type": "FLEET"}, format="json").data[
            "id"
        ]
        data = _register(owner, owner_group_id=gid, registration="KBB 002B")
        assert data["controller_kind"] == "GROUP"
        assert str(data["owner_group_id"]) == gid

    def test_ambiguous_ownership_is_rejected(self, user: Any, client_for: Any) -> None:
        client = client_for(user)
        pid = _operator(client)
        gid = "00000000-0000-0000-0000-000000000000"
        r = client.post(
            "/api/v1/vehicles",
            {
                "owner_operator_id": pid,
                "owner_group_id": gid,
                "vehicle_class": "PICKUP",
                "registration": "KAA 9",
                "capacity_value": "1",
            },
            format="json",
        )
        assert r.status_code == 400

    def test_no_owner_is_rejected(self, user: Any, client_for: Any) -> None:
        client = client_for(user)
        _operator(client)
        r = client.post(
            "/api/v1/vehicles",
            {"vehicle_class": "PICKUP", "registration": "KAA 9", "capacity_value": "1"},
            format="json",
        )
        assert r.status_code == 400

    def test_unknown_vehicle_class_is_rejected(self, user: Any, client_for: Any) -> None:
        client = client_for(user)
        pid = _operator(client)
        r = client.post(
            "/api/v1/vehicles",
            {
                "owner_operator_id": pid,
                "vehicle_class": "SPACESHIP",
                "registration": "KAA 5",
                "capacity_value": "1",
            },
            format="json",
        )
        assert r.status_code == 422
        assert r.data["code"] == "validation_error"

    def test_duplicate_active_registration_conflicts(self, user: Any, client_for: Any) -> None:
        client = client_for(user)
        pid = _operator(client)
        _register(client, owner_operator_id=pid, registration="KCC 3C")
        r = client.post(
            "/api/v1/vehicles",
            {
                "owner_operator_id": pid,
                "vehicle_class": "PICKUP",
                "registration": "kcc-3c",  # normalises to the same
                "capacity_value": "1",
            },
            format="json",
        )
        assert r.status_code == 409

    def test_can_reuse_registration_after_deactivation(self, user: Any, client_for: Any) -> None:
        client = client_for(user)
        pid = _operator(client)
        vid = _register(client, owner_operator_id=pid, registration="KDD 4D")["id"]
        assert client.delete(f"/api/v1/vehicles/{vid}").status_code == 204
        r = client.post(
            "/api/v1/vehicles",
            {
                "owner_operator_id": pid,
                "vehicle_class": "PICKUP",
                "registration": "KDD 4D",
                "capacity_value": "1",
            },
            format="json",
        )
        assert r.status_code == 201


class TestStatus:
    def test_operator_sets_operational_statuses_but_not_suspended(
        self, user: Any, client_for: Any
    ) -> None:
        client = client_for(user)
        pid = _operator(client)
        vid = _register(client, owner_operator_id=pid)["id"]

        assert (
            client.post(
                f"/api/v1/vehicles/{vid}/status", {"status": "ACTIVE"}, format="json"
            ).status_code
            == 200
        )
        assert Vehicle.objects.get(id=vid).status == "ACTIVE"
        assert (
            client.post(
                f"/api/v1/vehicles/{vid}/status", {"status": "UNDER_REPAIR"}, format="json"
            ).status_code
            == 200
        )
        r = client.post(f"/api/v1/vehicles/{vid}/status", {"status": "SUSPENDED"}, format="json")
        assert r.status_code == 403
        assert AuditLogEntry.objects.filter(action="vehicle.status_changed").count() == 2

    def test_admin_suspends_and_lifts(self, user: Any, client_for: Any, admin_client: Any) -> None:
        client = client_for(user)
        pid = _operator(client)
        vid = _register(client, owner_operator_id=pid)["id"]
        client.post(f"/api/v1/vehicles/{vid}/status", {"status": "ACTIVE"}, format="json")

        assert (
            admin_client.post(
                f"/api/v1/vehicles/{vid}/status",
                {"status": "SUSPENDED", "reason": "unsafe"},
                format="json",
            ).status_code
            == 200
        )
        assert Vehicle.objects.get(id=vid).is_active is False
        # the operator cannot un-suspend
        assert (
            client.post(
                f"/api/v1/vehicles/{vid}/status", {"status": "ACTIVE"}, format="json"
            ).status_code
            == 403
        )
        # the admin can
        assert (
            admin_client.post(
                f"/api/v1/vehicles/{vid}/status", {"status": "ACTIVE"}, format="json"
            ).status_code
            == 200
        )


def test_vehicle_statuses() -> None:
    assert set(VehicleStatus.values) == {"ACTIVE", "INACTIVE", "UNDER_REPAIR", "SUSPENDED"}


def test_seeded_vehicle_classes(db: Any) -> None:
    from fikisha.platform_config.models import VehicleClass

    codes = set(VehicleClass.objects.filter(active=True).values_list("code", flat=True))
    assert codes == {
        "MOTORCYCLE",
        "PICKUP",
        "CANTER",
        "TIPPER",
        "LORRY",
        "SEMI_TRUCK",
        "TRAILER",
        "OTHER",
    }
    heavy = set(VehicleClass.objects.filter(heavy=True).values_list("code", flat=True))
    assert heavy == {"CANTER", "TIPPER", "LORRY", "SEMI_TRUCK", "TRAILER"}


def test_check_constraint_blocks_two_controllers(db: Any) -> None:
    from django.db import IntegrityError

    from fikisha.platform_config.models import VehicleClass

    klass = VehicleClass.objects.get(code="PICKUP")
    with pytest.raises(IntegrityError):
        Vehicle.objects.create(
            vehicle_class=klass, registration="X", capacity_value=1
        )  # no controller
