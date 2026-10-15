"""Statements API: who sees what (plan §3.5, IDOR/BOLA) and the admin
actions over HTTP."""

from __future__ import annotations

from collections.abc import Callable
from datetime import timedelta
from typing import Any

import pytest
from django.utils import timezone

from fikisha.statements import services
from fikisha.statements.models import CommissionStatement, StatementSettlement
from fikisha.statements.tests.conftest import LAST_WEEK

pytestmark = pytest.mark.django_db

API = "/api/v1"


@pytest.fixture
def billed(
    completed_solo_job: Callable,
    completed_group_job: Callable,
    group_setup: dict[str, Any],
    eligible_driver: Any,
    admin_actor: Any,
) -> dict[str, Any]:
    solo_job = completed_solo_job()
    group_job = completed_group_job()
    services.run_statements(period_start=LAST_WEEK, actor=admin_actor)
    return {
        "solo_job": solo_job,
        "group_job": group_job,
        "solo_statement": CommissionStatement.objects.get(payee_kind="OPERATOR"),
        "group_statement": CommissionStatement.objects.get(payee_kind="GROUP"),
        "operator": eligible_driver,
        **group_setup,
    }


def _ids(response: Any) -> set[str]:
    assert response.status_code == 200, response.content
    return {row["id"] for row in response.json()["data"]}


def test_each_payee_lists_only_their_own(
    billed: dict[str, Any], client_for: Callable, user: Any
) -> None:
    solo, group = str(billed["solo_statement"].id), str(billed["group_statement"].id)
    assert _ids(client_for(billed["operator"].user).get(f"{API}/statements")) == {solo}
    assert _ids(client_for(billed["manager"].user).get(f"{API}/statements")) == {group}
    # a group DRIVER member is not a payee (FR-O-8); a business never is (D-7)
    assert _ids(client_for(billed["member"].user).get(f"{API}/statements")) == set()
    assert _ids(client_for(user).get(f"{API}/statements")) == set()


def test_statement_detail_is_payee_or_staff_only(
    billed: dict[str, Any], client_for: Callable, user: Any, ops_officer: Any, platform_admin: Any
) -> None:
    url = f"{API}/statements/{billed['solo_statement'].id}"
    r = client_for(billed["operator"].user).get(url)
    assert r.status_code == 200, r.content
    data = r.json()
    assert data["reference"] == billed["solo_statement"].reference
    assert data["lines"][0]["job_reference"] == str(billed["solo_job"].id)[-6:].upper()
    assert data["payment"] == {"paybill_number": None, "account_reference": data["reference"]}
    assert data["state"] == "UNPAID" and data["overdue"] is False

    for outsider in (billed["manager"].user, billed["member"].user, user):
        assert client_for(outsider).get(url).status_code == 403
    assert client_for(ops_officer).get(url).status_code == 200
    assert client_for(platform_admin).get(url).status_code == 200
    assert (
        client_for(billed["operator"].user).get(f"{API}/statements/{'0' * 32}").status_code == 404
    )


def test_job_earnings_for_the_payee_and_staff_only(
    billed: dict[str, Any], client_for: Callable, platform_admin: Any
) -> None:
    url = f"{API}/jobs/{billed['solo_job'].id}/earnings"
    r = client_for(billed["operator"].user).get(url)
    assert r.status_code == 200, r.content
    data = r.json()
    assert (
        data["agreed_price_kes"],
        data["effective_commission_kes"],
        data["net_to_operator_kes"],
    ) == (
        250_000,
        25_000,
        225_000,
    )
    assert data["statement"]["reference"] == billed["solo_statement"].reference
    assert client_for(billed["manager"].user).get(url).status_code == 404
    assert client_for(platform_admin).get(url).status_code == 200
    group_url = f"{API}/jobs/{billed['group_job'].id}/earnings"
    assert client_for(billed["manager"].user).get(group_url).status_code == 200
    assert client_for(billed["member"].user).get(group_url).status_code == 404


def test_admin_list_has_totals_and_ops_can_read_but_not_act(
    billed: dict[str, Any], client_for: Callable, ops_officer: Any, platform_admin: Any
) -> None:
    r = client_for(ops_officer).get(f"{API}/admin/statements?period_start=2026-10-05")
    assert r.status_code == 200, r.content
    body = r.json()
    assert len(body["data"]) == 2
    assert body["totals"] == {
        "statements": 2,
        "invoiced_kes": 50_000,
        "settled_kes": 0,
        "outstanding_kes": 50_000,
    }
    ops = client_for(ops_officer)
    assert ops.post(f"{API}/admin/statements/run", {}, format="json").status_code == 403
    pay = {"amount_kes": 1_000, "payment_ref": "SJK1", "paid_on": "2026-10-13"}
    url = f"{API}/admin/statements/{billed['solo_statement'].id}/payments"
    assert ops.post(url, pay, format="json").status_code == 403
    assert client_for(billed["operator"].user).get(f"{API}/admin/statements").status_code == 403
    r = client_for(platform_admin).get(f"{API}/admin/statements?payee_kind=GROUP")
    assert _ids(r) == {str(billed["group_statement"].id)}


def test_admin_runs_a_week_over_http(
    completed_solo_job: Callable, client_for: Callable, platform_admin: Any
) -> None:
    completed_solo_job()
    admin = client_for(platform_admin)
    r = admin.post(f"{API}/admin/statements/run", {}, format="json")
    assert r.status_code == 201, r.content
    assert r.json()["period_start"] == "2026-10-05"
    r = admin.post(f"{API}/admin/statements/run", {"period_start": "2026-10-05"}, format="json")
    assert r.status_code == 200 and r.json()["statements_created"] == 0
    r = admin.post(f"{API}/admin/statements/run", {"period_start": "2026-10-07"}, format="json")
    assert r.status_code == 422 and r.json()["code"] == "invalid_statement_period"


def test_payment_and_reversal_over_http_need_a_fresh_step_up(
    billed: dict[str, Any], client_for: Callable, platform_admin: Any
) -> None:
    from fikisha.identity.models import AuthSession

    url = f"{API}/admin/statements/{billed['solo_statement'].id}/payments"
    pay = {"amount_kes": 25_000, "payment_ref": "SJK4ABC123", "paid_on": "2026-10-13"}

    stale = client_for(platform_admin)
    AuthSession.objects.filter(user=platform_admin).update(
        step_up_at=timezone.now() - timedelta(hours=1)
    )
    r = stale.post(url, pay, format="json")
    assert r.status_code == 403 and r.json()["code"] == "step_up_required"

    admin = client_for(platform_admin)
    r = admin.post(url, pay, format="json")
    assert r.status_code == 201, r.content
    assert r.json()["state"] == "PAID"
    r = admin.post(url, {**pay, "payment_ref": "SJK4ABC999", "amount_kes": 1}, format="json")
    assert r.status_code == 409 and r.json()["code"] == "settlement_exceeds_due"

    payment = StatementSettlement.objects.get()
    r = admin.post(
        f"{url}/{payment.id}/reverse", {"reason": "Recorded against the wrong week"}, format="json"
    )
    assert r.status_code == 201, r.content
    assert r.json()["state"] == "UNPAID"

    # the operator now sees the reversal on their own statement
    mine = (
        client_for(billed["operator"].user)
        .get(f"{API}/statements/{billed['solo_statement'].id}")
        .json()
    )
    assert [s["kind"] for s in mine["settlements"]] == ["PAYMENT", "REVERSAL"]


def test_new_statements_are_unseen_until_the_payee_opens_them(
    billed: dict[str, Any], client_for: Callable, platform_admin: Any
) -> None:
    from fikisha.statements.models import StatementSeen

    operator = client_for(billed["operator"].user)
    body = operator.get(f"{API}/statements").json()
    assert body["unseen_count"] == 1 and body["data"][0]["seen"] is False

    seen_url = f"{API}/statements/{billed['solo_statement'].id}/seen"
    # staff opening it doesn't count; an outsider is refused
    assert client_for(platform_admin).post(seen_url).status_code == 204
    assert client_for(billed["manager"].user).post(seen_url).status_code == 403
    assert not StatementSeen.objects.exists()

    assert operator.post(seen_url).status_code == 204
    assert operator.post(seen_url).status_code == 204  # idempotent
    body = operator.get(f"{API}/statements").json()
    assert body["unseen_count"] == 0 and body["data"][0]["seen"] is True
    # the group's statement is still new for its manager
    assert client_for(billed["manager"].user).get(f"{API}/statements").json()["unseen_count"] == 1
