"""Business — cross-organisation isolation & privilege escalation (Phase 2B §16 / §35)."""

from __future__ import annotations

from typing import Any

import pytest

pytestmark = pytest.mark.django_db


@pytest.fixture
def two_businesses(user: Any, other_user: Any, client_for: Any) -> Any:
    a_client = client_for(user)
    b_client = client_for(other_user)
    a = a_client.post("/api/v1/businesses", {"trading_name": "Alpha"}, format="json").data
    b = b_client.post("/api/v1/businesses", {"trading_name": "Bravo"}, format="json").data
    return {"a_client": a_client, "b_client": b_client, "a": a, "b": b}


class TestCrossBusiness:
    def test_a_cannot_read_b(self, two_businesses: Any) -> None:
        r = two_businesses["a_client"].get(f"/api/v1/businesses/{two_businesses['b']['id']}")
        assert r.status_code == 403
        assert r.data["code"] == "authz.forbidden"

    def test_a_cannot_update_b(self, two_businesses: Any) -> None:
        r = two_businesses["a_client"].patch(
            f"/api/v1/businesses/{two_businesses['b']['id']}",
            {"trading_name": "Owned"},
            format="json",
        )
        assert r.status_code == 403
        # B is untouched.
        assert (
            two_businesses["b_client"]
            .get(f"/api/v1/businesses/{two_businesses['b']['id']}")
            .data["trading_name"]
            == "Bravo"
        )

    def test_a_cannot_list_b_members(self, two_businesses: Any) -> None:
        r = two_businesses["a_client"].get(
            f"/api/v1/businesses/{two_businesses['b']['id']}/members"
        )
        assert r.status_code == 403

    def test_a_cannot_add_a_member_to_b(self, two_businesses: Any) -> None:
        r = two_businesses["a_client"].post(
            f"/api/v1/businesses/{two_businesses['b']['id']}/members",
            {"phone": "+254712345678", "role": "VIEWER"},
            format="json",
        )
        assert r.status_code == 403

    def test_a_cannot_read_b_locations(self, two_businesses: Any) -> None:
        r = two_businesses["a_client"].get(
            f"/api/v1/businesses/{two_businesses['b']['id']}/locations"
        )
        assert r.status_code == 403


class TestUnauthenticated:
    def test_list_requires_auth(self, api: Any) -> None:
        assert api.get("/api/v1/businesses").status_code == 401

    def test_create_requires_auth(self, api: Any) -> None:
        assert (
            api.post("/api/v1/businesses", {"trading_name": "X"}, format="json").status_code == 401
        )

    def test_detail_requires_auth(self, api: Any, user: Any, client_for: Any) -> None:
        bid = (
            client_for(user)
            .post("/api/v1/businesses", {"trading_name": "X"}, format="json")
            .data["id"]
        )
        assert api.get(f"/api/v1/businesses/{bid}").status_code == 401


class TestInvalidIds:
    def test_unknown_business_is_403_or_404_not_500(self, user: Any, client_for: Any) -> None:
        r = client_for(user).get("/api/v1/businesses/00000000-0000-0000-0000-000000000000")
        assert r.status_code in {403, 404}
        assert r["content-type"] == "application/problem+json"

    def test_malformed_uuid_is_problem_json(self, user: Any, client_for: Any) -> None:
        r = client_for(user).get("/api/v1/businesses/not-a-uuid")
        assert r.status_code in {401, 404}
        assert r["content-type"] == "application/problem+json"
