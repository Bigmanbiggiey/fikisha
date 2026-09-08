"""Audit foundation tests: hash chaining, tamper detection, append-only at both
the ORM layer and the DB layer, and the transaction requirement.
"""

from __future__ import annotations

import pytest
from django.db import DatabaseError, transaction

from fikisha.audit import services as audit
from fikisha.audit.models import AuditChainHead, AuditLogEntry
from fikisha.common.models import AppendOnlyModelError

pytestmark = pytest.mark.django_db


def _record(action: str = "test.action") -> AuditLogEntry:
    with transaction.atomic():
        return audit.record(actor=None, action=action, entity_type="thing", entity_id=None)


class TestHashChain:
    def test_first_entry_has_empty_prev_hash(self) -> None:
        entry = _record()
        assert entry.seq == 1
        assert entry.prev_hash == ""
        assert len(entry.row_hash) == 64

    def test_chain_links_and_verifies(self) -> None:
        e1 = _record("a")
        e2 = _record("b")
        e3 = _record("c")
        assert (e1.seq, e2.seq, e3.seq) == (1, 2, 3)
        assert e2.prev_hash == e1.row_hash
        assert e3.prev_hash == e2.row_hash
        assert audit.verify_chain() == []

    def test_head_tracks_tail(self) -> None:
        _record()
        e = _record()
        head = AuditChainHead.objects.get(pk=1)
        assert head.last_seq == e.seq
        assert head.last_hash == e.row_hash

    def test_verify_chain_detects_a_bad_row_hash(self) -> None:
        _record("a")
        _record("b")
        # UPDATE/DELETE are blocked (trigger + guards); simulate tampering by
        # INSERTing an entry whose stored row_hash does not match its content.
        head = AuditChainHead.objects.get(pk=1)
        forged = AuditLogEntry(
            seq=head.last_seq + 1,
            actor_role="SYSTEM",
            action="content-says-one-thing",
            entity_type="x",
            entity_id=None,
            prev_hash=head.last_hash,
            row_hash="0" * 64,  # deliberately wrong
        )
        forged.save()  # an INSERT is permitted; only mutation is blocked
        breaks = audit.verify_chain()
        assert any(b["seq"] == forged.seq and b["issue"] == "row_hash_mismatch" for b in breaks)

    def test_verify_chain_detects_a_seq_gap(self) -> None:
        _record("a")
        head = AuditChainHead.objects.get(pk=1)
        forged = AuditLogEntry(
            seq=head.last_seq + 5,  # skips 4 sequence numbers
            actor_role="SYSTEM",
            action="x",
            entity_type="x",
            prev_hash=head.last_hash,
            row_hash="deadbeef",
        )
        forged.save()
        breaks = audit.verify_chain()
        assert any(b["issue"] == "gap_or_reorder" for b in breaks)


class TestAppendOnly:
    def test_orm_instance_update_raises(self) -> None:
        entry = _record()
        entry.action = "changed"
        with pytest.raises(AppendOnlyModelError):
            entry.save()

    def test_orm_instance_delete_raises(self) -> None:
        entry = _record()
        with pytest.raises(AppendOnlyModelError):
            entry.delete()

    def test_queryset_update_raises(self) -> None:
        _record()
        with pytest.raises(AppendOnlyModelError):
            AuditLogEntry.objects.all().update(action="x")

    def test_queryset_delete_raises(self) -> None:
        _record()
        with pytest.raises(AppendOnlyModelError):
            AuditLogEntry.objects.all().delete()

    def test_db_trigger_blocks_raw_update(self) -> None:
        _record()
        from django.db import connection

        with pytest.raises(DatabaseError):
            with connection.cursor() as cur:
                cur.execute("UPDATE audit_log_entry SET action = 'x'")

    def test_db_trigger_blocks_raw_delete(self) -> None:
        _record()
        from django.db import connection

        with pytest.raises(DatabaseError):
            with connection.cursor() as cur:
                cur.execute("DELETE FROM audit_log_entry")


class TestTransactionRequirement:
    def test_record_outside_transaction_raises(self) -> None:
        # pytest-django wraps each test in a transaction, so simulate "no atomic
        # block" by checking the guard directly is hard; instead assert the
        # public contract via a non-atomic connection flag.
        from unittest.mock import patch

        with patch("fikisha.audit.services.transaction.get_connection") as gc:
            gc.return_value.in_atomic_block = False
            with pytest.raises(RuntimeError):
                audit.record(actor=None, action="x", entity_type="y")
