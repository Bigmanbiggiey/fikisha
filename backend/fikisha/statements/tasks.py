"""Scheduled statement work (plan §3.4, `commission-ledger.md` §7).

- ``run_weekly_statements``: Monday 06:00 EAT, bills last week. Safe to run
  again: a payee who already has that week's statement is skipped.
- ``reconcile_statements``: nightly; logs CRITICAL for any statement whose
  totals, lines or payments disagree.
"""

from __future__ import annotations

from typing import Any

from celery import shared_task

from fikisha.common.logging_setup import get_logger
from fikisha.identity.authz.actors import SystemActor

log = get_logger("fikisha.statements.tasks")


@shared_task(name="fikisha.statements.tasks.run_weekly_statements")
def run_weekly_statements(period_start: str | None = None) -> dict[str, Any]:
    from datetime import date

    from fikisha.statements import services

    start = date.fromisoformat(period_start) if period_start else None
    result = services.run_statements(
        period_start=start or services.last_completed_period_start(),
        actor=SystemActor("statements.weekly"),
    )
    log.info(
        "statements.run",
        period_start=result["period_start"],
        created=result["statements_created"],
        skipped=result["payees_skipped_existing"],
    )
    return result


@shared_task(name="fikisha.statements.tasks.reconcile_statements")
def reconcile_statements() -> dict[str, int]:
    from fikisha.statements import services

    problems = services.reconcile()
    for problem in problems:
        log.critical("statements.reconciliation_mismatch", **problem)
    return {"mismatches": len(problems)}
