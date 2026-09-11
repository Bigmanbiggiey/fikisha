"""Celery wrapper around the existing Phase 2C expiry command (Phase 2D Step
11, plan §19 / ADR-2D-08). ``services.expire_due()`` already is the
authoritative, tested, idempotent operation (``@transaction.atomic``,
``SELECT ... FOR UPDATE``, append-only ``VerificationDecision`` history,
audit + outbox) — this module adds nothing but the Celery Beat seam so it
runs on a schedule instead of only ad hoc. ``manage.py verification_expire``
is unchanged and keeps working for manual/operational runs."""

from __future__ import annotations

from celery import shared_task

from fikisha.common.logging_setup import get_logger
from fikisha.verification import services

log = get_logger("fikisha.verification.sweeps")


@shared_task(name="fikisha.verification.tasks.expire_due")
def expire_due() -> dict[str, int]:
    count = services.expire_due()
    if count:
        log.info("verification.sweep.completed", expired=count)
    return {"expired": count}
