"""Handler registry for outbox events.

A handler is ``Callable[[OutboxEventContext], None]`` registered against an
``event_type``. Handlers MUST be idempotent — the publisher is at-least-once and
``event_id`` is passed so a handler can dedupe.
"""

from __future__ import annotations

import uuid
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

_HANDLERS: dict[str, list[Callable[[OutboxEventContext], None]]] = {}


@dataclass(frozen=True, slots=True)
class OutboxEventContext:
    event_id: int
    event_type: str
    aggregate_type: str
    aggregate_id: uuid.UUID | None
    payload: dict[str, Any]
    attempt: int


def register(
    event_type: str,
) -> Callable[[Callable[[OutboxEventContext], None]], Callable[[OutboxEventContext], None]]:
    def _decorator(
        func: Callable[[OutboxEventContext], None],
    ) -> Callable[[OutboxEventContext], None]:
        _HANDLERS.setdefault(event_type, []).append(func)
        return func

    return _decorator


def handlers_for(event_type: str) -> list[Callable[[OutboxEventContext], None]]:
    return list(_HANDLERS.get(event_type, []))


def registered_event_types() -> list[str]:
    return sorted(_HANDLERS)
