"""Transactional outbox — Phase 1 ADR-015 / events-and-background-jobs §2.

A domain module calls :func:`fikisha.outbox.services.emit` **inside the same DB
transaction** as its state change. A Celery task (:func:`drain_outbox`) polls
unpublished rows with ``SELECT ... FOR UPDATE SKIP LOCKED`` and dispatches to
registered handlers. Exactly-once capture, at-least-once delivery, no message
broker.
"""
