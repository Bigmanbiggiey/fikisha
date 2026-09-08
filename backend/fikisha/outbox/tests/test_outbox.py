"""Transactional outbox foundation tests.

Proves the core Phase 1 guarantee: an outbox row is written **atomically** with
the state change that emits it (rollback leaves neither), and the publisher is
at-least-once + idempotent, with retry -> dead-letter on a poison event.
"""

from __future__ import annotations

import pytest
from django.core.cache import cache
from django.db import transaction
from django.utils import timezone

from fikisha.audit import services as audit
from fikisha.audit.models import AuditLogEntry
from fikisha.outbox import handlers as demo_handlers
from fikisha.outbox.models import OutboxEvent, OutboxStatus
from fikisha.outbox.registry import register
from fikisha.outbox.services import emit
from fikisha.outbox.tasks import drain_outbox

pytestmark = pytest.mark.django_db


def _always_fails(_ctx: object) -> None:
    raise ValueError("always fails")


register("demo.poison")(_always_fails)  # module-load registration (test-only event type)


class TestEmitRequiresTransaction:
    def test_emit_outside_transaction_raises(self) -> None:
        from unittest.mock import patch

        with patch("fikisha.outbox.services.transaction.get_connection") as gc:
            gc.return_value.in_atomic_block = False
            with pytest.raises(RuntimeError):
                emit(event_type="x", aggregate_type="y")


class TestAtomicity:
    def test_state_change_and_outbox_commit_together(self) -> None:
        with transaction.atomic():
            entry = audit.record(actor=None, action="demo.atomic", entity_type="demo")
            event = emit(
                event_type="demo.atomic_demo",
                aggregate_type="demo",
                payload={"audit_seq": entry.seq},
            )
        assert AuditLogEntry.objects.filter(seq=entry.seq).exists()
        assert OutboxEvent.objects.filter(pk=event.pk, status=OutboxStatus.PENDING).exists()

    def test_rollback_leaves_neither_row(self) -> None:
        before_audit = AuditLogEntry.objects.count()
        before_outbox = OutboxEvent.objects.count()
        with pytest.raises(RuntimeError):
            with transaction.atomic():
                audit.record(actor=None, action="demo.atomic", entity_type="demo")
                emit(event_type="demo.atomic_demo", aggregate_type="demo")
                raise RuntimeError("boom — abort the whole unit")
        assert AuditLogEntry.objects.count() == before_audit
        assert OutboxEvent.objects.count() == before_outbox


class TestPublisher:
    def test_drain_publishes_and_runs_handler_once(self) -> None:
        cache.delete(demo_handlers.DEMO_COUNT_KEY)
        with transaction.atomic():
            event = emit(
                event_type=demo_handlers.DEMO_EVENT_TYPE,
                aggregate_type="demo",
                payload={"note": "hello"},
            )

        stats = drain_outbox()
        assert stats["published"] == 1
        event.refresh_from_db()
        assert event.status == OutboxStatus.PUBLISHED
        assert event.published_at is not None
        assert cache.get(demo_handlers.DEMO_COUNT_KEY) == 1

        assert drain_outbox()["published"] == 0
        assert cache.get(demo_handlers.DEMO_COUNT_KEY) == 1

    def test_handler_idempotent_on_reprocess(self) -> None:
        cache.delete(demo_handlers.DEMO_COUNT_KEY)
        with transaction.atomic():
            event = emit(event_type=demo_handlers.DEMO_EVENT_TYPE, aggregate_type="demo")
        drain_outbox()
        OutboxEvent.objects.filter(pk=event.pk).update(
            status=OutboxStatus.PENDING, published_at=None
        )
        drain_outbox()
        assert cache.get(demo_handlers.DEMO_COUNT_KEY) == 1

    def test_poison_event_retries_then_dead_letters(self) -> None:
        with transaction.atomic():
            event = emit(event_type="demo.poison", aggregate_type="demo")

        for _ in range(5):
            OutboxEvent.objects.filter(pk=event.pk).update(available_at=timezone.now())
            drain_outbox()

        event.refresh_from_db()
        assert event.status == OutboxStatus.DEAD
        assert event.attempts >= 5
        assert "ValueError" in event.last_error
