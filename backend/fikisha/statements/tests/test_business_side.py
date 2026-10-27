"""The business side of the commission split (ADR-2D-55): a business is billed
its own 5% on a statement of its own (D-1), only its Owner sees that statement
(D-3), and its Owner and Dispatchers see the fee on each job they send. Each
test here keeps the real split (``both_sides``)."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

import pytest

from fikisha.statements import services
from fikisha.statements.models import CommissionStatement
from fikisha.statements.tests.conftest import LAST_WEEK

pytestmark = pytest.mark.django_db

API = "/api/v1"
FEE = 12_500  # 5% of the fixture's agreed KES 2,500


@pytest.fixture
def billed(
    both_sides: None,
    completed_solo_job: Callable,
    eligible_driver: Any,
    verified_business: Any,
    admin_actor: Any,
    make_user: Callable,
) -> dict[str, Any]:
    from fikisha.business.models import BusinessMembership, BusinessRole, MembershipStatus

    job = completed_solo_job()
    services.run_statements(period_start=LAST_WEEK, actor=admin_actor)
    dispatcher = make_user("+254700000031")
    BusinessMembership.objects.create(
        business=verified_business,
        user=dispatcher,
        role=BusinessRole.DISPATCHER,
        status=MembershipStatus.ACTIVE,
    )
    viewer = make_user("+254700000032")
    BusinessMembership.objects.create(
        business=verified_business,
        user=viewer,
        role=BusinessRole.VIEWER,
        status=MembershipStatus.ACTIVE,
    )
    return {
        "job": job,
        "business": verified_business,
        "operator": eligible_driver,
        "dispatcher": dispatcher,
        "viewer": viewer,
        "business_statement": CommissionStatement.objects.get(payee_kind="BUSINESS"),
        "operator_statement": CommissionStatement.objects.get(payee_kind="OPERATOR"),
    }


def test_one_job_bills_each_side_on_its_own_statement(billed: dict[str, Any]) -> None:
    biz, op = billed["business_statement"], billed["operator_statement"]
    assert str(biz.payee_id) == str(billed["business"].id)
    assert str(op.payee_id) == str(billed["job"].agreement.operator_id)
    assert biz.net_due_kes == op.net_due_kes == FEE
    assert biz.reference != op.reference
    biz_line = biz.lines.get()
    assert biz_line.job_id == billed["job"].id and biz_line.amount_kes == FEE


def test_only_the_business_owner_lists_and_opens_the_business_statement(
    billed: dict[str, Any], client_for: Callable, user: Any
) -> None:
    owner = client_for(user)  # ``user`` owns ``verified_business``
    statement_id = str(billed["business_statement"].id)
    r = owner.get(f"{API}/statements")
    assert r.status_code == 200, r.content
    assert {row["id"] for row in r.json()["data"]} == {statement_id}
    detail = owner.get(f"{API}/statements/{statement_id}")
    assert detail.status_code == 200
    assert detail.json()["payee"]["kind"] == "BUSINESS"
    assert detail.json()["payee"]["name"] == "Kitengela Traders"

    for other in (billed["dispatcher"], billed["viewer"], billed["operator"].user):
        c = client_for(other)
        listed = {row["id"] for row in c.get(f"{API}/statements").json()["data"]}
        assert statement_id not in listed
        assert c.get(f"{API}/statements/{statement_id}").status_code == 403


def test_the_operator_cannot_open_the_business_statement_and_vice_versa(
    billed: dict[str, Any], client_for: Callable, user: Any
) -> None:
    op_id = billed["operator_statement"].id
    assert client_for(user).get(f"{API}/statements/{op_id}").status_code == 403


def test_cost_for_this_job_for_the_business_side(
    billed: dict[str, Any], client_for: Callable, user: Any
) -> None:
    url = f"{API}/jobs/{billed['job'].id}/earnings"
    data = client_for(user).get(url).json()
    assert data["party"] == "BUSINESS"
    assert (data["agreed_price_kes"], data["effective_commission_kes"], data["total_cost_kes"]) == (
        250_000,
        FEE,
        262_500,
    )
    assert data["statement"]["reference"] == billed["business_statement"].reference

    # a Dispatcher sees the fee on a job they could send, not the statement
    r = client_for(billed["dispatcher"]).get(url)
    assert r.status_code == 200
    assert r.json()["party"] == "BUSINESS" and r.json()["statement"] is None
    # a Viewer sees neither
    assert client_for(billed["viewer"]).get(url).status_code == 404


def test_each_side_sees_only_its_own_side(
    billed: dict[str, Any], client_for: Callable, user: Any, platform_admin: Any
) -> None:
    url = f"{API}/jobs/{billed['job'].id}/earnings"
    op = client_for(billed["operator"].user)
    data = op.get(url).json()
    assert data["party"] == "OPERATOR" and data["net_to_operator_kes"] == 237_500
    assert data["sides"] == ["OPERATOR"]
    assert op.get(f"{url}?party=BUSINESS").status_code == 404
    assert client_for(user).get(f"{url}?party=OPERATOR").status_code == 404

    staff = client_for(platform_admin)
    assert staff.get(f"{url}?party=BUSINESS").json()["party"] == "BUSINESS"
    assert staff.get(f"{url}?party=OPERATOR").json()["party"] == "OPERATOR"
    assert staff.get(f"{url}?party=NOPE").status_code == 422


def test_admin_filters_business_statements(
    billed: dict[str, Any], client_for: Callable, platform_admin: Any
) -> None:
    r = client_for(platform_admin).get(f"{API}/admin/statements?payee_kind=BUSINESS")
    assert r.status_code == 200, r.content
    assert [row["id"] for row in r.json()["data"]] == [str(billed["business_statement"].id)]
    assert r.json()["totals"]["invoiced_kes"] == FEE


def test_a_business_statement_is_settled_like_any_other(
    billed: dict[str, Any], stepped_up_admin: Any
) -> None:
    from datetime import date

    data = services.record_payment(
        actor=stepped_up_admin,
        statement_id=billed["business_statement"].id,
        amount_kes=FEE,
        payment_ref="SJK9BIZ001",
        paid_on=date(2026, 10, 13),
    )
    assert data["state"] == "PAID"
    assert services.statement_summary(billed["operator_statement"])["state"] == "UNPAID"
