"""Recording and reversing payments (D-4, D-5) and append-only enforcement."""

from __future__ import annotations

from collections.abc import Callable
from datetime import date
from typing import Any

import pytest
from django.db import IntegrityError, connection, transaction

from fikisha.common.models import AppendOnlyModelError
from fikisha.identity.authz.step_up import StepUpRequired
from fikisha.statements import services
from fikisha.statements.models import CommissionStatement, StatementLine, StatementSettlement
from fikisha.statements.tests.conftest import LAST_WEEK

pytestmark = pytest.mark.django_db

PAID_ON = date(2026, 10, 13)


@pytest.fixture
def statement(completed_solo_job: Callable, admin_actor: Any) -> CommissionStatement:
    completed_solo_job()
    services.run_statements(period_start=LAST_WEEK, actor=admin_actor)
    return CommissionStatement.objects.get()  # net due 12_500: the operator's 5% of KES 2,500


def _pay(actor: Any, statement: Any, amount: int, ref: str = "SJK4ABC123") -> dict[str, Any]:
    return services.record_payment(
        actor=actor, statement_id=statement.id, amount_kes=amount, payment_ref=ref, paid_on=PAID_ON
    )


def test_part_then_full_payment(statement: Any, stepped_up_admin: Any) -> None:
    data = _pay(stepped_up_admin, statement, 10_000)
    assert (data["state"], data["settled_kes"], data["outstanding_kes"]) == (
        "PART_PAID",
        10_000,
        2_500,
    )
    data = _pay(stepped_up_admin, statement, 2_500, ref="sjk4abc124")
    assert (data["state"], data["outstanding_kes"]) == ("PAID", 0)
    assert data["settlements"][1]["payment_ref"] == "SJK4ABC124"  # stored upper-case


def test_more_than_owed_and_a_reused_reference_are_refused(
    statement: Any, stepped_up_admin: Any
) -> None:
    with pytest.raises(services.SettlementExceedsDue):
        _pay(stepped_up_admin, statement, 12_501)
    _pay(stepped_up_admin, statement, 5_000)
    with pytest.raises(services.DuplicatePaymentRef):
        _pay(stepped_up_admin, statement, 5_000)
    with pytest.raises(services.InvalidSettlement):
        _pay(stepped_up_admin, statement, 0, ref="OTHER")
    with pytest.raises(services.InvalidSettlement):
        services.record_payment(
            actor=stepped_up_admin,
            statement_id=statement.id,
            amount_kes=100,
            payment_ref="FUTURE1",
            paid_on=date(2026, 10, 20),
        )


def test_a_reversal_cancels_a_payment_once_and_frees_its_reference(
    statement: Any, stepped_up_admin: Any
) -> None:
    _pay(stepped_up_admin, statement, 12_500)
    payment = StatementSettlement.objects.get()
    with pytest.raises(services.InvalidSettlement):
        services.reverse_payment(
            actor=stepped_up_admin,
            statement_id=statement.id,
            settlement_id=payment.id,
            reason="typo",
        )
    data = services.reverse_payment(
        actor=stepped_up_admin,
        statement_id=statement.id,
        settlement_id=payment.id,
        reason="Wrong statement; belongs to another operator",
    )
    assert (data["state"], data["settled_kes"]) == ("UNPAID", 0)
    assert data["settlements"][0]["reversed"] is True
    with pytest.raises(services.SettlementNotReversible):
        services.reverse_payment(
            actor=stepped_up_admin,
            statement_id=statement.id,
            settlement_id=payment.id,
            reason="Second attempt at the same reversal",
        )
    reversal = StatementSettlement.objects.get(kind="REVERSAL")
    with pytest.raises(services.SettlementNotReversible):
        services.reverse_payment(
            actor=stepped_up_admin,
            statement_id=statement.id,
            settlement_id=reversal.id,
            reason="Reversing a reversal is not allowed",
        )
    assert _pay(stepped_up_admin, statement, 12_500)["state"] == "PAID"  # same ref again


def test_settling_needs_a_fresh_step_up_and_a_platform_admin(
    statement: Any, admin_actor: Any, ops_officer: Any, actor_for: Callable
) -> None:
    with pytest.raises(StepUpRequired):
        _pay(admin_actor, statement, 1_000)
    import dataclasses

    from fikisha.common.exceptions import AuthorizationError

    ops = dataclasses.replace(actor_for(ops_officer), is_step_up_fresh=True)
    with pytest.raises(AuthorizationError):
        _pay(ops, statement, 1_000)
    assert not StatementSettlement.objects.exists()


@pytest.mark.parametrize(
    "table", ["commission_statement", "statement_line", "statement_settlement"]
)
def test_statement_tables_are_append_only(
    statement: Any, stepped_up_admin: Any, table: str
) -> None:
    _pay(stepped_up_admin, statement, 1_000)
    row = {
        "commission_statement": statement,
        "statement_line": StatementLine.objects.first(),
        "statement_settlement": StatementSettlement.objects.first(),
    }[table]
    with pytest.raises(AppendOnlyModelError):
        row.save()
    with pytest.raises(AppendOnlyModelError):
        type(row).objects.filter(id=row.id).delete()
    with pytest.raises(IntegrityError), transaction.atomic(), connection.cursor() as cur:
        cur.execute(f"DELETE FROM {table} WHERE id = %s", [row.id])  # noqa: S608


def test_an_unpaid_statement_is_overdue_after_14_days_and_paid_clears_it(
    statement: Any, stepped_up_admin: Any, frozen: Any
) -> None:
    assert services.statement_summary(statement)["overdue"] is False
    frozen.move_to("2026-10-29T07:00:00+00:00")  # 15 days after it was generated
    assert services.statement_summary(statement)["overdue"] is True
    _pay(stepped_up_admin, statement, 12_500)
    assert services.statement_summary(statement)["overdue"] is False
