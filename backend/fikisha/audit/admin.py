from __future__ import annotations

from typing import Any

from django.contrib import admin

from fikisha.audit.models import AuditChainHead, AuditLogEntry


class _ReadOnly(admin.ModelAdmin):
    def has_add_permission(self, request: Any) -> bool:
        return False

    def has_change_permission(self, request: Any, obj: Any = None) -> bool:
        return False

    def has_delete_permission(self, request: Any, obj: Any = None) -> bool:
        return False


@admin.register(AuditLogEntry)
class AuditLogEntryAdmin(_ReadOnly):
    list_display = (
        "seq",
        "server_time",
        "actor_role",
        "action",
        "entity_type",
        "entity_id",
        "request_id",
    )
    list_filter = ("actor_role", "source_channel", "action")
    search_fields = ("action", "entity_type", "request_id", "row_hash")
    ordering = ("-seq",)


@admin.register(AuditChainHead)
class AuditChainHeadAdmin(_ReadOnly):
    list_display = ("id", "last_seq", "updated_at")
