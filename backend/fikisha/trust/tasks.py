"""Nightly tier evaluation (trust-architecture.md §3: "+ nightly beat").
Days active pass without any event, so a proposal can become due overnight.
Writes proposals only; never applies a tier."""

from __future__ import annotations

from typing import Any

from celery import shared_task

from fikisha.common.logging_setup import get_logger

log = get_logger("fikisha.trust.evaluate")


@shared_task(name="fikisha.trust.tasks.evaluate_tiers")
def evaluate_tiers() -> dict[str, Any]:
    from fikisha.operators import services as operators
    from fikisha.trust import services

    proposed = 0
    for operator_id in operators.active_operator_ids():
        try:
            if services.evaluate_operator_id(operator_id) is not None:
                proposed += 1
        except Exception:  # one bad row must not stop the run
            log.exception("trust.evaluate_failed", operator_id=str(operator_id))
    return {"proposed": proposed}
