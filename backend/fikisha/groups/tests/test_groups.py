"""Operator Groups — creation, membership, roles, admin ops (Phase 2B §34)."""

from __future__ import annotations

from typing import Any

import pytest

from fikisha.audit.models import AuditLogEntry
from fikisha.groups.models import GroupMemberRole, GroupMembership
from fikisha.outbox.models import OutboxEvent

pytestmark = pytest.mark.django_db


def _operator(client: Any, name: str = "Op") -> str:
    r = client.post("/api/v1/operators", {"full_name": name}, format="json")
    assert r.status_code == 201, r.content
    return r.data["id"]


def _group(client: Any, **over: Any) -> dict:
    body = {"name": "Kitengela Movers", "type": "SACCO", **over}
    r = client.post("/api/v1/groups", body, format="json")
    assert r.status_code == 201, r.content
    return r.data


class TestGroupCrud:
    def test_creator_becomes_owner(self, user: Any, client_for: Any) -> None:
        client = client_for(user)
        _operator(client, "Founder")
        data = _group(client)
        assert data["my_role"] == "OWNER"
        assert data["assignment_mode"] == "MANAGER_ASSIGNS"
        assert GroupMembership.objects.filter(
            group_id=data["id"], role="OWNER", status="ACTIVE"
        ).exists()
        assert AuditLogEntry.objects.filter(action="group.created").exists()

    def test_a_non_operator_cannot_create_a_group(self, user: Any, client_for: Any) -> None:
        r = client_for(user).post("/api/v1/groups", {"name": "X", "type": "FLEET"}, format="json")
        assert r.status_code == 403

    def test_list_returns_only_my_groups(self, user: Any, other_user: Any, client_for: Any) -> None:
        a = client_for(user)
        _operator(a)
        mine = _group(a)["id"]
        b = client_for(other_user)
        _operator(b, "Other")
        _group(b, name="Rival SACCO")
        ids = [g["id"] for g in a.get("/api/v1/groups").data["data"]]
        assert ids == [mine]

    def test_owner_updates_group_but_not_standing(self, user: Any, client_for: Any) -> None:
        client = client_for(user)
        _operator(client)
        gid = _group(client)["id"]
        assert (
            client.patch(
                f"/api/v1/groups/{gid}", {"assignment_mode": "DRIVER_ACCEPTS"}, format="json"
            ).status_code
            == 200
        )
        r = client.patch(f"/api/v1/groups/{gid}", {"standing": "SUSPENDED"}, format="json")
        assert r.status_code == 403

    def test_admin_can_suspend_a_group(self, user: Any, client_for: Any, admin_client: Any) -> None:
        client = client_for(user)
        _operator(client)
        gid = _group(client)["id"]
        r = admin_client.patch(f"/api/v1/groups/{gid}", {"standing": "SUSPENDED"}, format="json")
        assert r.status_code == 200 and r.data["standing"] == "SUSPENDED"


class TestGroupMembership:
    def test_manager_adds_a_driver(self, user: Any, other_user: Any, client_for: Any) -> None:
        owner = client_for(user)
        _operator(owner, "Owner")
        gid = _group(owner)["id"]

        driver = client_for(other_user)
        driver_pid = _operator(driver, "Driver Dan")

        r = owner.post(
            f"/api/v1/groups/{gid}/members",
            {"operator_id": driver_pid, "role": "DRIVER"},
            format="json",
        )
        assert r.status_code == 201, r.content
        assert OutboxEvent.objects.filter(event_type="group.member.added").exists()

        # The driver can now read the group...
        assert driver.get(f"/api/v1/groups/{gid}").status_code == 200
        # ...but cannot add members (manage is OWNER/MANAGER only).
        third = client_for  # noqa: F841 - not needed; assert on the driver instead
        assert (
            driver.post(
                f"/api/v1/groups/{gid}/members",
                {"operator_id": driver_pid, "role": "MANAGER"},
                format="json",
            ).status_code
            == 403
        )

    def test_operator_cannot_be_active_in_two_groups(
        self, user: Any, other_user: Any, make_user: Any, client_for: Any
    ) -> None:
        a_owner = client_for(user)
        _operator(a_owner, "A owner")
        gid_a = _group(a_owner, name="Group A")["id"]

        b_owner = client_for(other_user)
        _operator(b_owner, "B owner")
        gid_b = _group(b_owner, name="Group B")["id"]

        shared_user = make_user("+254733111222")
        shared_client = client_for(shared_user)
        shared_pid = _operator(shared_client, "Shared")

        assert (
            a_owner.post(
                f"/api/v1/groups/{gid_a}/members",
                {"operator_id": shared_pid, "role": "DRIVER"},
                format="json",
            ).status_code
            == 201
        )
        r = b_owner.post(
            f"/api/v1/groups/{gid_b}/members",
            {"operator_id": shared_pid, "role": "DRIVER"},
            format="json",
        )
        assert r.status_code == 409
        assert r.data["code"] == "already_in_group"

    def test_cannot_remove_last_owner(self, user: Any, client_for: Any) -> None:
        client = client_for(user)
        pid = _operator(client)
        gid = _group(client)["id"]
        membership_id = GroupMembership.objects.get(group_id=gid, operator_id=pid).id
        r = client.delete(f"/api/v1/groups/{gid}/members/{membership_id}")
        assert r.status_code == 409 and r.data["code"] == "last_owner"

    def test_remove_member_is_soft(self, user: Any, other_user: Any, client_for: Any) -> None:
        owner = client_for(user)
        _operator(owner, "Owner")
        gid = _group(owner)["id"]
        driver = client_for(other_user)
        driver_pid = _operator(driver, "Driver")
        mid = owner.post(
            f"/api/v1/groups/{gid}/members",
            {"operator_id": driver_pid, "role": "DRIVER"},
            format="json",
        ).data["id"]
        assert owner.delete(f"/api/v1/groups/{gid}/members/{mid}").status_code == 204
        assert GroupMembership.objects.get(id=mid).status == "INACTIVE"  # row kept


def test_group_member_roles() -> None:
    assert set(GroupMemberRole.values) == {"OWNER", "MANAGER", "DRIVER"}
