"""Business module — creation, membership, roles, locations (Phase 2B §34)."""

from __future__ import annotations

from typing import Any

import pytest

from fikisha.audit.models import AuditLogEntry
from fikisha.business.models import BusinessMembership, MembershipStatus
from fikisha.outbox.models import OutboxEvent

pytestmark = pytest.mark.django_db


def _create_business(client: Any, **over: Any) -> dict:
    body = {"trading_name": "Mama Njeri Hardware", **over}
    r = client.post("/api/v1/businesses", body, format="json")
    assert r.status_code == 201, r.content
    return r.data


class TestBusinessCrud:
    def test_owner_is_created_with_the_business(self, user: Any, client_for: Any) -> None:
        client = client_for(user)
        data = _create_business(client)
        assert data["trading_name"] == "Mama Njeri Hardware"
        assert data["my_role"] == "OWNER"
        assert data["standing"] == "GOOD"
        assert BusinessMembership.objects.filter(
            business_id=data["id"], user=user, role="OWNER", status="ACTIVE"
        ).exists()
        assert AuditLogEntry.objects.filter(action="business.created").exists()

    def test_list_returns_only_my_businesses(
        self, user: Any, other_user: Any, client_for: Any
    ) -> None:
        mine = _create_business(client_for(user))["id"]
        _create_business(client_for(other_user), trading_name="Someone Else Ltd")
        r = client_for(user).get("/api/v1/businesses")
        ids = [b["id"] for b in r.data["data"]]
        assert ids == [mine]

    def test_owner_can_update_profile(self, user: Any, client_for: Any) -> None:
        client = client_for(user)
        bid = _create_business(client)["id"]
        r = client.patch(
            f"/api/v1/businesses/{bid}", {"contact_phone": "+254720000000"}, format="json"
        )
        assert r.status_code == 200
        assert r.data["contact_phone"] == "+254720000000"
        assert AuditLogEntry.objects.filter(action="business.updated").exists()

    def test_owner_cannot_set_standing(self, user: Any, client_for: Any) -> None:
        client = client_for(user)
        bid = _create_business(client)["id"]
        r = client.patch(f"/api/v1/businesses/{bid}", {"standing": "SUSPENDED"}, format="json")
        assert r.status_code == 403

    def test_platform_admin_can_suspend(
        self, user: Any, client_for: Any, admin_client: Any
    ) -> None:
        bid = _create_business(client_for(user))["id"]
        r = admin_client.patch(
            f"/api/v1/businesses/{bid}", {"standing": "SUSPENDED"}, format="json"
        )
        assert r.status_code == 200
        assert r.data["standing"] == "SUSPENDED"


class TestBusinessMembership:
    def test_add_staff_and_staff_gets_scoped_access(
        self, user: Any, make_user: Any, client_for: Any
    ) -> None:
        owner = client_for(user)
        bid = _create_business(owner)["id"]

        r = owner.post(
            f"/api/v1/businesses/{bid}/members",
            {"phone": "+254712345678", "role": "DISPATCHER"},
            format="json",
        )
        assert r.status_code == 201, r.content
        staff_user_id = r.data["user_id"]

        from fikisha.identity.models import User

        staff = client_for(User.objects.get(id=staff_user_id))
        # Staff can read the business...
        assert staff.get(f"/api/v1/businesses/{bid}").status_code == 200
        # ...but cannot manage members (owner-only).
        assert (
            staff.post(
                f"/api/v1/businesses/{bid}/members",
                {"phone": "+254799999999", "role": "VIEWER"},
                format="json",
            ).status_code
            == 403
        )
        # ...and cannot update the business profile.
        assert (
            staff.patch(
                f"/api/v1/businesses/{bid}", {"trading_name": "Hijack Ltd"}, format="json"
            ).status_code
            == 403
        )

    def test_add_member_emits_outbox_event(self, user: Any, client_for: Any) -> None:
        owner = client_for(user)
        bid = _create_business(owner)["id"]
        owner.post(
            f"/api/v1/businesses/{bid}/members",
            {"phone": "+254712345678", "role": "VIEWER"},
            format="json",
        )
        assert OutboxEvent.objects.filter(event_type="business.member.added").exists()

    def test_cannot_remove_the_last_owner(self, user: Any, client_for: Any) -> None:
        owner = client_for(user)
        bid = _create_business(owner)["id"]
        member_id = BusinessMembership.objects.get(business_id=bid, user=user).id
        r = owner.delete(f"/api/v1/businesses/{bid}/members/{member_id}")
        assert r.status_code == 409
        assert r.data["code"] == "last_owner"

    def test_suspended_member_loses_access(
        self, user: Any, make_user: Any, client_for: Any
    ) -> None:
        owner = client_for(user)
        bid = _create_business(owner)["id"]
        add = owner.post(
            f"/api/v1/businesses/{bid}/members",
            {"phone": "+254712345678", "role": "VIEWER"},
            format="json",
        )
        from fikisha.identity.models import User

        staff = client_for(User.objects.get(id=add.data["user_id"]))
        assert staff.get(f"/api/v1/businesses/{bid}").status_code == 200

        member_id = add.data["id"]
        owner.patch(
            f"/api/v1/businesses/{bid}/members/{member_id}",
            {"status": "SUSPENDED"},
            format="json",
        )
        assert staff.get(f"/api/v1/businesses/{bid}").status_code == 403


class TestBusinessLocations:
    def test_main_location_is_unique_and_demotes_the_previous(
        self, user: Any, client_for: Any
    ) -> None:
        client = client_for(user)
        bid = _create_business(client)["id"]
        r1 = client.post(
            f"/api/v1/businesses/{bid}/locations",
            {"label": "Shop", "type": "MAIN", "zone_code": "KITENGELA"},
            format="json",
        )
        assert r1.status_code == 201, r1.content
        assert r1.data["zone_code"] == "KITENGELA"

        r2 = client.post(
            f"/api/v1/businesses/{bid}/locations",
            {"label": "Depot", "type": "MAIN"},
            format="json",
        )
        assert r2.status_code == 201
        # Exactly one active MAIN.
        listing = client.get(f"/api/v1/businesses/{bid}/locations").data["data"]
        mains = [loc for loc in listing if loc["type"] == "MAIN"]
        assert len(mains) == 1 and mains[0]["label"] == "Depot"

    def test_deactivate_is_soft(self, user: Any, client_for: Any) -> None:
        client = client_for(user)
        bid = _create_business(client)["id"]
        loc_id = client.post(
            f"/api/v1/businesses/{bid}/locations",
            {"label": "Branch", "type": "BRANCH"},
            format="json",
        ).data["id"]
        assert client.delete(f"/api/v1/businesses/{bid}/locations/{loc_id}").status_code == 204
        assert client.get(f"/api/v1/businesses/{bid}/locations").data["data"] == []

        from fikisha.business.models import BusinessLocation

        assert BusinessLocation.objects.filter(id=loc_id).exists()  # row kept (history)

    def test_unknown_zone_is_rejected(self, user: Any, client_for: Any) -> None:
        client = client_for(user)
        bid = _create_business(client)["id"]
        r = client.post(
            f"/api/v1/businesses/{bid}/locations",
            {"label": "X", "type": "STORE", "zone_code": "NAIROBI_CBD"},
            format="json",
        )
        assert r.status_code == 400


def test_membership_status_values() -> None:
    assert set(MembershipStatus.values) == {"ACTIVE", "SUSPENDED", "REMOVED"}
