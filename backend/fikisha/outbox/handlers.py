"""Foundation-level outbox handlers.

Only a demonstrative handler exists in Phase 2A. Real domain handlers
(Notification / Metrics / Trust / Ledger / ...) arrive with their modules.
"""

from __future__ import annotations

from django.core.cache import cache

from fikisha.common.logging_setup import get_logger
from fikisha.outbox.registry import OutboxEventContext, register

log = get_logger("fikisha.outbox.handlers")

DEMO_EVENT_TYPE = "demo.atomic_demo"
DEMO_PROCESSED_KEY_PREFIX = "outbox:demo:processed:"
DEMO_COUNT_KEY = "outbox:demo:count"


@register(DEMO_EVENT_TYPE)
def handle_demo_event(ctx: OutboxEventContext) -> None:
    """Idempotent demo handler: records that it processed ``ctx.event_id`` once."""
    processed_key = f"{DEMO_PROCESSED_KEY_PREFIX}{ctx.event_id}"
    if cache.get(processed_key):
        log.info("outbox.demo.already_processed", event_id=ctx.event_id)
        return
    cache.set(processed_key, True, timeout=3600)
    try:
        cache.incr(DEMO_COUNT_KEY)
    except ValueError:
        cache.set(DEMO_COUNT_KEY, 1, timeout=3600)
    log.info("outbox.demo.processed", event_id=ctx.event_id, note=ctx.payload.get("note"))
