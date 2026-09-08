from __future__ import annotations

from typing import Any

from django.contrib import admin

from fikisha.platform_config.models import PlatformConfig, PlatformConfigVersion


@admin.register(PlatformConfigVersion)
class PlatformConfigVersionAdmin(admin.ModelAdmin):
    list_display = ("version", "changed_by", "created_at", "rationale")
    ordering = ("-version",)
    readonly_fields = ("version", "changed_by", "created_at", "rationale", "snapshot")

    def has_add_permission(self, request: Any) -> bool:
        return False

    def has_change_permission(self, request: Any, obj: Any = None) -> bool:
        return False

    def has_delete_permission(self, request: Any, obj: Any = None) -> bool:
        return False


@admin.register(PlatformConfig)
class PlatformConfigAdmin(admin.ModelAdmin):
    list_display = ("id", "current_version", "updated_at")
    readonly_fields = ("id", "data", "current_version", "updated_at")

    def has_add_permission(self, request: Any) -> bool:
        return False

    def has_change_permission(self, request: Any, obj: Any = None) -> bool:
        # Changes go through ConfigService.apply_change (audited + versioned),
        # never raw admin editing.
        return False

    def has_delete_permission(self, request: Any, obj: Any = None) -> bool:
        return False
