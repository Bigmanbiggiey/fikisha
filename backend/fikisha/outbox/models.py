"""Outbox data model.

``id`` is a ``BigAutoField`` (monotonic, cheap to order/lock) — not a UUID —
because the publisher orders and locks by it. Rows are never deleted; a poison
event ends in ``DEAD`` status and stays for inspection.
"""

from __future__ import annotations

from django.db import models
from django.utils import timezone


class OutboxStatus(models.TextChoices):
    PENDING = "PENDING", "Pending"
    PUBLISHED = "PUBLISHED", "Published"
    DEAD = "DEAD", "Dead-lettered"


class OutboxEvent(models.Model):
    id = models.BigAutoField(primary_key=True)

    event_type = models.CharField(max_length=128, db_index=True)
    aggregate_type = models.CharField(max_length=64)
    aggregate_id = models.UUIDField(null=True, blank=True)
    payload = models.JSONField(default=dict, blank=True)

    status = models.CharField(
        max_length=16, choices=OutboxStatus.choices, default=OutboxStatus.PENDING
    )
    attempts = models.PositiveSmallIntegerField(default=0)
    available_at = models.DateTimeField(default=timezone.now, help_text="Next attempt time")
    last_error = models.TextField(blank=True, default="")

    created_at = models.DateTimeField(auto_now_add=True)
    published_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "outbox_event"
        indexes = [
            models.Index(
                fields=["status", "available_at", "id"],
                name="outbox_pending_idx",
                condition=models.Q(status="PENDING"),
            ),
            models.Index(fields=["aggregate_type", "aggregate_id"]),
        ]
        ordering = ["id"]

    def __str__(self) -> str:
        return f"OutboxEvent(#{self.id} {self.event_type} {self.status})"
