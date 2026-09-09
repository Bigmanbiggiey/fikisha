"""Vehicles — cross-organisation isolation & privilege escalation (Phase 2C §23/§28)."""

from __future__ import annotations

from typing import Any

import pytest

pytestmark = pytest.mark.django_db


def _op(client: Any, name: str) -> str:
    return client.post("/api/v1/operators", {"full_name": name}, format="json").data["id"]


def _vehicle(client: Any, **body: Any) -> str:
    payload = {"vehicle_class": "PICKUP", "capacity_value": "1", **body}
    r = client.post("/api/v1/vehicles", payload, format="json")
    assert r.status_code == 201, r.content
    return r.data["id"]


@pytest.fixture
def scene(user: Any, other_user: Any, make_user: Any, client_for: Any) -> Any:
    a = client_for(user)
    a_pid = _op(a, "A")
    a_vid = _vehicle(a, owner_operator_id=a_pid, registration="KAA 1")

    b = client_for(other_user)
    b_pid = _op(b, "B")
    _vehicle(b, owner_operator_id=b_pid, registration="KBB 2")

    # a group with an owner and a driver
    owner_user = make_user("+254701700001")
    owner = client_for(owner_user)
    _op(owner, "GOwner")
    gid = owner.post("/api/v1/groups", {"name": "G", "type": "FLEET"}, format="json").data["id"]
    g_vid = _vehicle(owner, owner_group_id=gid, registration="KGG 3")

    driver_user = make_user("+254701700002")
    driver = client_for(driver_user)
    d_pid = _op(driver, "GDriver")
    owner.post(
        f"/api/v1/groups/{gid}/members", {"operator_id": d_pid, "role": "DRIVER"}, format="json"
    )
    return {"a": a, "b": b, "owner": owner, "driver": driver, "a_vid": a_vid, "g_vid": g_vid}


class TestCrossOrg:
    def test_operator_cannot_read_anothers_vehicle(self, scene: Any) -> None:
        assert scene["b"].get(f"/api/v1/vehicles/{scene['a_vid']}").status_code == 403

    def test_operator_cannot_update_anothers_vehicle(self, scene: Any) -> None:
        r = scene["b"].patch(
            f"/api/v1/vehicles/{scene['a_vid']}", {"make": "Hijack"}, format="json"
        )
        assert r.status_code == 403

    def test_operator_cannot_register_to_another_operator(
        self, user: Any, other_user: Any, client_for: Any
    ) -> None:
        a = client_for(user)
        a_pid = _op(a, "A")
        b = client_for(other_user)
        _op(b, "B")
        r = b.post(
            "/api/v1/vehicles",
            {
                "owner_operator_id": a_pid,
                "vehicle_class": "PICKUP",
                "registration": "K",
                "capacity_value": "1",
            },
            format="json",
        )
        assert r.status_code == 403

    def test_group_driver_can_read_but_not_manage_group_vehicle(self, scene: Any) -> None:
        assert scene["driver"].get(f"/api/v1/vehicles/{scene['g_vid']}").status_code == 200
        r = scene["driver"].patch(
            f"/api/v1/vehicles/{scene['g_vid']}", {"make": "X"}, format="json"
        )
        assert r.status_code == 403
        assert (
            scene["driver"]
            .post(f"/api/v1/vehicles/{scene['g_vid']}/status", {"status": "ACTIVE"}, format="json")
            .status_code
            == 403
        )

    def test_group_owner_manages_group_vehicle(self, scene: Any) -> None:
        assert (
            scene["owner"]
            .patch(f"/api/v1/vehicles/{scene['g_vid']}", {"make": "Isuzu"}, format="json")
            .status_code
            == 200
        )


class TestUnauthenticated:
    def test_list_requires_auth(self, api: Any) -> None:
        assert api.get("/api/v1/vehicles").status_code == 401

    def test_create_requires_auth(self, api: Any) -> None:
        assert api.post("/api/v1/vehicles", {}, format="json").status_code == 401

    def test_unknown_vehicle_is_problem_json(self, user: Any, client_for: Any) -> None:
        r = client_for(user).get("/api/v1/vehicles/00000000-0000-0000-0000-000000000000")
        assert r.status_code in {403, 404}
        assert r["content-type"] == "application/problem+json"
