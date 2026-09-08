"""Audit data model.

``AuditLogEntry`` is append-only (``AppendOnlyModel``) and hash-chained. The
chain head (last seq + last hash) lives in a tiny singleton ``AuditChainHead``
row that is ``SELECT ... FOR UPDATE``-locked while a new entry is written, giving
a gapless ``seq`` and the previous hash without a race.
"""

from __future__ import annotations

from django.conf import settings
from django.db import models
from django.utils import timezone

from fikisha.common.models import AppendOnlyModel, AppendOnlyQuerySet


class ActorRole(models.TextChoices):
    ANONYMOUS = "ANONYMOUS", "Anonymous"
    USER = "USER", "Authenticated user"
    BUSINESS = "BUSINESS", "Business"
    OPERATOR = "OPERATOR", "Operator"
    GROUP_MANAGER = "GROUP_MANAGER", "Group manager"
    GROUP_DRIVER = "GROUP_DRIVER", "Group driver"
    RECIPIENT = "RECIPIENT", "Recipient"
    OPERATIONS_OFFICER = "OPERATIONS_OFFICER", "Operations Officer"
    PLATFORM_ADMIN = "PLATFORM_ADMIN", "Platform Admin"
    SYSTEM = "SYSTEM", "System"


class SourceChannel(models.TextChoices):
    API = "API", "API"
    ADMIN_UI = "ADMIN_UI", "Admin UI"
    WEBHOOK = "WEBHOOK", "Webhook"
    SCHEDULER = "SCHEDULER", "Scheduler"
    CLI = "CLI", "CLI / management command"


class AuditChainHead(models.Model):
    """Singleton pointer to the tail of the hash chain (pk is fixed at 1)."""

    id = models.PositiveSmallIntegerField(primary_key=True, default=1, editable=False)
    last_seq = models.BigIntegerField(default=0)
    last_hash = models.CharField(max_length=64, default="", blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "audit_chain_head"
        constraints = [
            models.CheckConstraint(condition=models.Q(id=1), name="audit_chain_head_singleton")
        ]


class AuditLogEntry(AppendOnlyModel):
    seq = models.BigIntegerField(unique=True, editable=False)

    actor_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.PROTECT,  # audit must outlive account changes; users are soft-deleted
        related_name="audit_entries",
    )
    actor_role = models.CharField(max_length=32, choices=ActorRole.choices)

    action = models.CharField(max_length=128)
    entity_type = models.CharField(max_length=64)
    entity_id = models.UUIDField(null=True, blank=True)

    before = models.JSONField(null=True, blank=True)
    after = models.JSONField(null=True, blank=True)

    server_time = models.DateTimeField(default=timezone.now, db_index=True, editable=False)
    request_id = models.CharField(max_length=128, default="-", blank=True)
    source_channel = models.CharField(
        max_length=16, choices=SourceChannel.choices, default=SourceChannel.API
    )
    source_ip = models.GenericIPAddressField(null=True, blank=True)
    source_device = models.CharField(max_length=256, null=True, blank=True)

    prev_hash = models.CharField(max_length=64, blank=True, default="")
    row_hash = models.CharField(max_length=64, unique=True, editable=False)

    objects = AppendOnlyQuerySet.as_manager()

    class Meta:
        db_table = "audit_log_entry"
        ordering = ["seq"]
        indexes = [
            models.Index(fields=["entity_type", "entity_id", "server_time"]),
            models.Index(fields=["actor_user", "server_time"]),
            models.Index(fields=["action", "server_time"]),
        ]

    def __str__(self) -> str:
        return f"#{self.seq} {self.actor_role} {self.action} {self.entity_type}:{self.entity_id}"
