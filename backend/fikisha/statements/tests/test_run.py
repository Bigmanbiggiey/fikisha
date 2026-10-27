"""The weekly statement run (Commission & Statements S-1, plan §3.3-3.4)."""

from __future__ import annotations

from collections.abc import Callable
from datetime import date
from typing import Any

import pytest

from fikisha.audit.models import AuditLogEntry
from fikisha.jobs.models import CommissionRecord
from fikisha.outbox.models import OutboxEvent
from fikisha.statements import services
from fikisha.statements.models import CommissionStatement, StatementLine
from fikisha.statements.tests.conftest import LAST_WEEK, WEEK_BEFORE, age_completion

pytestmark = pytest.mark.django_db

#: The operator's 5% of the fixture's agreed KES 2,500, in minor units (the
#: business side is 0 here; see conftest ``operator_side_only``).
COMMISSION = 12_500


def _run(admin: Any, start: date = LAST_WEEK) -> dict[str, Any]:
    return services.run_statements(period_start=start, actor=admin)


def test_a_closed_window_job_is_billed_once(completed_solo_job: Callable, admin_actor: Any) -> None:
    job = completed_solo_job()
    result = _run(admin_actor)
    assert result["statements_created"] == 1
    statement = CommissionStatement.objects.get()
    assert statement.payee_kind == "OPERATOR"
    assert str(statement.payee_id) == str(job.agreement.operator_id)
    assert (statement.period_start, statement.period_end) == (date(2026, 10, 5), date(2026, 10, 11))
    assert statement.gross_commission_kes == COMMISSION
    assert statement.net_due_kes == COMMISSION
    assert statement.reference == services.reference_for(statement.id)
    assert statement.reference.startswith("ST-") and len(statement.reference) == 9
    line = statement.lines.get()
    assert line.kind == "COMMISSION"
    assert line.commission_record_id == CommissionRecord.objects.get(job=job).id
    assert line.agreed_price_kes == 250_000
    assert AuditLogEntry.objects.filter(action="statement.generated").count() == 1
    assert OutboxEvent.objects.filter(event_type="StatementGenerated").count() == 1

    again = _run(admin_actor)
    assert again["statements_created"] == 0
    assert StatementLine.objects.count() == 1


def test_a_job_inside_its_dispute_window_waits(
    completed_solo_job: Callable, admin_actor: Any
) -> None:
    waiting = completed_solo_job(days=1)  # window closes after the week ends
    assert _run(admin_actor)["statements_created"] == 0

    # Its window closes; the payee has no statement for that week yet, so it
    # is billed now.
    age_completion(waiting, before=LAST_WEEK, days=4)
    assert _run(admin_actor)["statements_created"] == 1


def test_a_payee_with_a_statement_for_the_week_is_skipped_and_the_rest_rolls_forward(
    completed_solo_job: Callable, admin_actor: Any
) -> None:
    completed_solo_job()
    late = completed_solo_job(days=1)
    assert _run(admin_actor)["statements_created"] == 1
    age_completion(late, before=LAST_WEEK, days=4)

    result = _run(admin_actor)
    assert result["statements_created"] == 0
    assert result["payees_skipped_existing"] == 1
    assert not StatementLine.objects.filter(commission_record__job=late).exists()


def test_a_disputed_job_is_held_until_it_is_resolved(
    delivered_job: Callable, complete_job: Callable, admin_actor: Any, business_actor: Any
) -> None:
    from fikisha.incidents.constants import IncidentType
    from fikisha.incidents.services import open_dispute, report_incident, resolve_dispute

    job = delivered_job()
    complete_job(job)
    incident = report_incident(actor=business_actor, job_id=job.id, type=IncidentType.DAMAGE)
    open_dispute(actor=business_actor, job_id=job.id, incident_ids=[incident.id])
    age_completion(job, before=LAST_WEEK)
    assert _run(admin_actor)["statements_created"] == 0  # DISPUTED: held (D-2)

    resolve_dispute(
        actor=admin_actor,
        dispute_id=job.disputes.first().id,
        outcome_code="ADMIN_DETERMINATION",
        rationale="goods were damaged in transit; commission waived",
        routed_job_status="COMPLETED",
        commission_treatment="WAIVE",
    )
    age_completion(job, before=LAST_WEEK)
    # resolved back to COMPLETED: billed. The waiver was made after the week
    # ended, so it waits for next week's statement.
    assert _run(admin_actor)["statements_created"] == 1
    statement = CommissionStatement.objects.get()
    assert statement.net_due_kes == COMMISSION
    assert list(statement.lines.values_list("kind", flat=True)) == ["COMMISSION"]


def test_a_waiver_made_before_the_week_ended_nets_on_the_same_statement(
    completed_solo_job: Callable, admin_actor: Any, frozen: Any
) -> None:
    from fikisha.jobs.commission import create_adjustment

    job = completed_solo_job()
    frozen.move_to("2026-10-10T07:00:00+00:00")  # inside last week
    create_adjustment(
        commission_record=CommissionRecord.objects.get(job=job),
        actor=admin_actor,
        kind="WAIVER",
        amount_kes=-COMMISSION,
        reason="test: waived by dispute resolution",
    )
    frozen.move_to("2026-10-14T07:00:00+00:00")
    _run(admin_actor)
    statement = CommissionStatement.objects.get()
    assert (statement.gross_commission_kes, statement.adjustments_kes, statement.net_due_kes) == (
        COMMISSION,
        -COMMISSION,
        0,
    )
    assert sorted(statement.lines.values_list("kind", flat=True)) == ["ADJUSTMENT", "COMMISSION"]
    assert services.statement_summary(statement)["state"] == "PAID"


def test_an_adjustment_after_billing_is_a_credit_on_a_later_statement(
    completed_solo_job: Callable, admin_actor: Any, frozen: Any
) -> None:
    from fikisha.jobs.commission import create_adjustment

    job = completed_solo_job(before=WEEK_BEFORE)
    frozen.move_to("2026-10-06T07:00:00+00:00")  # Tuesday of last week
    _run(admin_actor, WEEK_BEFORE)
    create_adjustment(
        commission_record=CommissionRecord.objects.get(job=job),
        actor=admin_actor,
        kind="REDUCTION",
        amount_kes=-5_000,
        reason="test: reduced by dispute resolution",
    )
    frozen.move_to("2026-10-14T07:00:00+00:00")
    _run(admin_actor)

    first, second = CommissionStatement.objects.order_by("period_start")
    assert first.net_due_kes == COMMISSION
    assert (second.gross_commission_kes, second.adjustments_kes, second.net_due_kes) == (
        0,
        -5_000,
        -5_000,
    )
    assert services.statement_summary(second)["outstanding_kes"] == 0


def test_solo_and_group_jobs_go_to_their_own_payees(
    completed_solo_job: Callable, completed_group_job: Callable, admin_actor: Any
) -> None:
    completed_solo_job()
    group_job = completed_group_job()
    assert _run(admin_actor)["statements_created"] == 2
    group_statement = CommissionStatement.objects.get(payee_kind="GROUP")
    assert str(group_statement.payee_id) == str(group_job.agreement.group_id)


def test_only_finished_mondays_are_valid_periods(admin_actor: Any) -> None:
    with pytest.raises(services.InvalidPeriod):
        _run(admin_actor, date(2026, 10, 6))  # a Tuesday
    with pytest.raises(services.InvalidPeriod):
        _run(admin_actor, date(2026, 10, 12))  # this week, not finished


def test_the_weekly_task_bills_last_week_as_the_system(completed_solo_job: Callable) -> None:
    from fikisha.statements.tasks import run_weekly_statements

    completed_solo_job()
    result = run_weekly_statements()
    assert result["period_start"] == "2026-10-05"
    statement = CommissionStatement.objects.get()
    assert statement.generated_by is None
    entry = AuditLogEntry.objects.get(action="statement.generated")
    assert entry.source_channel == "SCHEDULER"


def test_reconciliation_is_clean_for_generated_statements(
    completed_solo_job: Callable, admin_actor: Any
) -> None:
    from fikisha.statements.tasks import reconcile_statements

    completed_solo_job()
    _run(admin_actor)
    assert services.reconcile() == []
    assert reconcile_statements() == {"mismatches": 0}
