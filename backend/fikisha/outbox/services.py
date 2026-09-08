"""Outbox write side — :func:`emit`."""

from __future__ import annotations

import uuid
from typing import Any

from django.db import transaction

from fikisha.outbox.models import OutboxEvent


def emit(
    *,
    event_type: str,
    aggregate_type: str,
    aggregate_id: uuid.UUID | str | None = None,
    payload: dict[str, Any] | None = None,
) -> OutboxEvent:
    """Append a domain event to the outbox.

    MUST be called inside a database transaction so the event is atomic with the
    state change that produced it (Phase 1 events-and-background-jobs §2). If no
    transaction is open this raises rather than silently emitting a
    non-transactional event.
    """
    if not transaction.get_connection().in_atomic_block:
        raise RuntimeError(
            "outbox.emit() must be called inside a database transaction "
            "(wrap the state change + emit in transaction.atomic())."
        )
    return OutboxEvent.objects.create(
        event_type=event_type,
        aggregate_type=aggregate_type,
        aggregate_id=aggregate_id,
        payload=payload or {},
    )
