"""Operator approval and the pending lock-out (assessment 2026-10-19 D-2/D-3).

A new operator is ``PENDING`` until a verification reviewer approves them.
Until then the server gives them no work, refuses their offers and refuses to
assign them as a group's driver.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

import pytest

from fikisha.admin_console.models import AdminIntervention
from fikisha.audit.models import AuditLogEntry
from fikisha.jobs import guards
from fikisha.jobs.errors import OperatorNotApproved
from fikisha.jobs.tests.test_discovery import _make_requested_job

pytestmark = pytest.mark.django_db


def _pending(make_verified_operator: Callable, phone: str = "+254733400001") -> Any:
    op = make_verified_operator(phone, "New Operator")
    op.status = "PENDING"
    op.save(update_fields=["status"])
    return op


def _approve(client: Any, operator_id: Any, **body: Any) -> Any:
    return client.post(f"/api/v1/admin/operators/{operator_id}/approve", body, format="json")


class TestApprove:
    def test_an_ops_officer_approves_a_pending_operator(
        self, ops_officer: Any, client_for: Callable, make_verified_operator: Callable
    ) -> None:
        op = _pending(make_verified_operator)
        r = _approve(client_for(ops_officer), op.id, note="ID and licence checked")
        assert r.status_code == 201, r.content
        assert (r.data["before_state"], r.data["after_state"]) == ("PENDING", "ACTIVE")
        op.refresh_from_db()
        assert op.status == "ACTIVE"
        row = AdminIntervention.objects.get(account_id=op.id, action="APPROVE")
        assert row.reason == "ID and licence checked"
        assert row.admin_id == ops_officer.id
        assert AuditLogEntry.objects.filter(
            action="admin.account.approve", entity_id=op.id
        ).exists()

    def test_only_a_pending_operator_can_be_approved(
        self, platform_admin: Any, client_for: Callable, eligible_driver: Any
    ) -> None:
        r = _approve(client_for(platform_admin), eligible_driver.id)
        assert r.status_code == 409
        assert r.data["code"] == "intervention_not_allowed"

    def test_a_non_reviewer_cannot_approve(
        self, client_for: Callable, make_verified_operator: Callable, make_user: Callable
    ) -> None:
        op = _pending(make_verified_operator)
        r = _approve(client_for(make_user("+254733400099")), op.id)
        assert r.status_code == 403
        op.refresh_from_db()
        assert op.status == "PENDING"

    def test_a_reviewer_cannot_approve_their_own_operator_profile(
        self, ops_officer: Any, client_for: Callable
    ) -> None:
        from fikisha.operators.models import OperatorProfile

        own = OperatorProfile.objects.create(user=ops_officer, full_name="Me", status="PENDING")
        r = _approve(client_for(ops_officer), own.id)
        assert r.status_code == 409
        own.refresh_from_db()
        assert own.status == "PENDING"

    def test_approve_is_not_an_ordinary_intervention(
        self, platform_admin: Any, client_for: Callable, make_verified_operator: Callable
    ) -> None:
        op = _pending(make_verified_operator)
        r = client_for(platform_admin).post(
            "/api/v1/admin/interventions",
            {
                "account_type": "OPERATOR",
                "account_id": str(op.id),
                "action": "APPROVE",
                "reason": "trying the back door",
            },
            format="json",
        )
        assert r.status_code == 422
        op.refresh_from_db()
        assert op.status == "PENDING"


class TestPendingLockOut:
    def test_a_pending_operator_sees_no_work(
        self,
        client_for: Callable,
        verified_business: Any,
        user: Any,
        admin_actor: Any,
        make_verified_operator: Callable,
        make_vehicle: Callable,
    ) -> None:
        op = _pending(make_verified_operator)
        make_vehicle(owner_operator=op, registration="KDA 401P")
        job = _make_requested_job(business=verified_business, user=user, admin_actor=admin_actor)
        r = client_for(op.user).get("/api/v1/jobs/opportunities")
        assert r.status_code == 200, r.content
        assert str(job.id) not in {row["id"] for row in r.data["data"]}

        # Once approved, the same job shows.
        op.status = "ACTIVE"
        op.save(update_fields=["status"])
        r = client_for(op.user).get("/api/v1/jobs/opportunities")
        assert str(job.id) in {row["id"] for row in r.data["data"]}

    def test_a_pending_operator_cannot_negotiate(self, make_verified_operator: Callable) -> None:
        op = _pending(make_verified_operator)
        with pytest.raises(OperatorNotApproved):
            guards.operator_eligible_for_job(None, None, {"operator_profile": op})

    def test_a_pending_member_cannot_be_assigned_as_driver(
        self, make_verified_operator: Callable
    ) -> None:
        op = _pending(make_verified_operator)
        with pytest.raises(OperatorNotApproved):
            guards.driver_assignment_allowed(None, None, {"driver_profile": op})
