"""Outbox publisher + a demonstrative task.

``drain_outbox`` is the Celery task that Celery beat runs every
``OUTBOX_POLL_SECONDS``. It claims a batch of ``PENDING`` rows with
``select_for_update(skip_locked=True)`` (so multiple workers never double-claim),
runs the registered handlers for each, and marks the row ``PUBLISHED`` or —
after ``OUTBOX_MAX_ATTEMPTS`` failures — ``DEAD``.
"""

from __future__ import annotations

from datetime import timedelta

from celery import shared_task
from django.conf import settings
from django.db import transaction
from django.utils import timezone

from fikisha.common.logging_setup import get_logger
from fikisha.outbox.models import OutboxEvent, OutboxStatus
from fikisha.outbox.registry import OutboxEventContext, handlers_for

log = get_logger("fikisha.outbox")

MAX_ATTEMPTS = getattr(settings, "OUTBOX_MAX_ATTEMPTS", 5)
BACKOFF_BASE_SECONDS = getattr(settings, "OUTBOX_BACKOFF_BASE_SECONDS", 5)
BACKOFF_CAP_SECONDS = getattr(settings, "OUTBOX_BACKOFF_CAP_SECONDS", 300)


def _backoff(attempts: int) -> timedelta:
    return timedelta(seconds=min(BACKOFF_BASE_SECONDS * (2**attempts), BACKOFF_CAP_SECONDS))


@shared_task(name="fikisha.outbox.tasks.drain_outbox")
def drain_outbox(batch_size: int = 100) -> dict[str, int]:
    """Publish a batch of pending outbox rows. Returns a small stats dict."""
    now = timezone.now()
    published = failed = dead = 0

    with transaction.atomic():
        rows = list(
            OutboxEvent.objects.select_for_update(skip_locked=True)
            .filter(status=OutboxStatus.PENDING, available_at__lte=now)
            .order_by("id")[:batch_size]
        )
        for row in rows:
            ctx = OutboxEventContext(
                event_id=row.id,
                event_type=row.event_type,
                aggregate_type=row.aggregate_type,
                aggregate_id=row.aggregate_id,
                payload=row.payload,
                attempt=row.attempts + 1,
            )
            try:
                for handler in handlers_for(row.event_type):
                    handler(ctx)
            except Exception as exc:
                row.attempts += 1
                row.last_error = f"{type(exc).__name__}: {exc}"[:2000]
                if row.attempts >= MAX_ATTEMPTS:
                    row.status = OutboxStatus.DEAD
                    dead += 1
                    log.error(
                        "outbox.dead_letter",
                        event_id=row.id,
                        event_type=row.event_type,
                        attempts=row.attempts,
                    )
                else:
                    row.available_at = now + _backoff(row.attempts)
                    failed += 1
                row.save(update_fields=["attempts", "last_error", "status", "available_at"])
            else:
                row.status = OutboxStatus.PUBLISHED
                row.published_at = now
                row.save(update_fields=["status", "published_at"])
                published += 1

    if published or failed or dead:
        log.info("outbox.drained", published=published, failed=failed, dead=dead)
    return {"published": published, "failed": failed, "dead": dead}


@shared_task(name="fikisha.outbox.tasks.demo_task")
def demo_task(value: str = "ok") -> str:
    """A trivial task used by the foundation tests / smoke test."""
    log.info("outbox.demo_task", value=value)
    return value
