from __future__ import annotations

from typing import Any

from django.contrib import admin

from fikisha.outbox.models import OutboxEvent


@admin.register(OutboxEvent)
class OutboxEventAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "event_type",
        "status",
        "attempts",
        "created_at",
        "published_at",
        "available_at",
    )
    list_filter = ("status", "event_type")
    search_fields = ("event_type", "aggregate_type")
    ordering = ("-id",)
    readonly_fields = ("id", "created_at", "published_at")

    def has_add_permission(self, request: Any) -> bool:
        return False

    def has_delete_permission(self, request: Any, obj: Any = None) -> bool:
        return False
