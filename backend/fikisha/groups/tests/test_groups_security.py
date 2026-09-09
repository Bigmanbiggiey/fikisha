"""Operator Groups — cross-group isolation & privilege escalation (Phase 2B §16 / §35)."""

from __future__ import annotations

from typing import Any

import pytest

pytestmark = pytest.mark.django_db


def _op(client: Any, name: str) -> str:
    return client.post("/api/v1/operators", {"full_name": name}, format="json").data["id"]


@pytest.fixture
def two_groups(user: Any, other_user: Any, make_user: Any, client_for: Any) -> Any:
    a_client = client_for(user)
    _op(a_client, "A owner")
    a = a_client.post("/api/v1/groups", {"name": "Group A", "type": "SACCO"}, format="json").data

    b_client = client_for(other_user)
    _op(b_client, "B owner")
    b = b_client.post("/api/v1/groups", {"name": "Group B", "type": "FLEET"}, format="json").data

    spare = client_for(make_user("+254701020304"))
    spare_pid = _op(spare, "Spare")
    return {"a_client": a_client, "b_client": b_client, "a": a, "b": b, "spare_pid": spare_pid}


class TestCrossGroup:
    def test_a_member_cannot_read_group_b(self, two_groups: Any) -> None:
        r = two_groups["a_client"].get(f"/api/v1/groups/{two_groups['b']['id']}")
        assert r.status_code == 403

    def test_a_member_cannot_manage_group_b(self, two_groups: Any) -> None:
        r = two_groups["a_client"].patch(
            f"/api/v1/groups/{two_groups['b']['id']}", {"name": "Owned"}, format="json"
        )
        assert r.status_code == 403

    def test_a_member_cannot_list_group_b_members(self, two_groups: Any) -> None:
        r = two_groups["a_client"].get(f"/api/v1/groups/{two_groups['b']['id']}/members")
        assert r.status_code == 403

    def test_a_member_cannot_add_a_member_to_group_b(self, two_groups: Any) -> None:
        r = two_groups["a_client"].post(
            f"/api/v1/groups/{two_groups['b']['id']}/members",
            {"operator_id": two_groups["spare_pid"], "role": "DRIVER"},
            format="json",
        )
        assert r.status_code == 403


class TestUnauthenticated:
    def test_list_requires_auth(self, api: Any) -> None:
        assert api.get("/api/v1/groups").status_code == 401

    def test_create_requires_auth(self, api: Any) -> None:
        assert (
            api.post("/api/v1/groups", {"name": "X", "type": "FLEET"}, format="json").status_code
            == 401
        )
