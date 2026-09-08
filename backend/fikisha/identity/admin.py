from __future__ import annotations

from typing import Any

from django.contrib import admin

from fikisha.identity.models import (
    AdminProfile,
    AuthSession,
    OtpChallenge,
    RefreshToken,
    RoleAssignment,
    TotpDevice,
    User,
)


@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = ("phone", "display_name", "status", "locale", "is_staff", "created_at")
    list_filter = ("status", "locale", "is_staff")
    search_fields = ("phone", "display_name", "email")
    readonly_fields = ("id", "created_at", "updated_at", "last_login", "password")
    ordering = ("-created_at",)


@admin.register(RoleAssignment)
class RoleAssignmentAdmin(admin.ModelAdmin):
    list_display = ("user", "role", "assigned_by", "assigned_at", "revoked_at")
    list_filter = ("role",)
    autocomplete_fields = ("user", "assigned_by")


@admin.register(AdminProfile)
class AdminProfileAdmin(admin.ModelAdmin):
    list_display = ("user", "active", "created_at")
    autocomplete_fields = ("user",)


class _ReadOnlyAdmin(admin.ModelAdmin):
    def has_add_permission(self, request: Any) -> bool:
        return False

    def has_change_permission(self, request: Any, obj: Any = None) -> bool:
        return False

    def has_delete_permission(self, request: Any, obj: Any = None) -> bool:
        return False


@admin.register(AuthSession)
class AuthSessionAdmin(_ReadOnlyAdmin):
    list_display = (
        "id",
        "user",
        "is_admin_session",
        "created_at",
        "last_seen_at",
        "expires_at",
        "revoked_at",
    )
    list_filter = ("is_admin_session",)
    search_fields = ("user__phone",)


@admin.register(RefreshToken)
class RefreshTokenAdmin(_ReadOnlyAdmin):
    list_display = ("id", "session", "used_at", "expires_at", "created_at")


@admin.register(OtpChallenge)
class OtpChallengeAdmin(_ReadOnlyAdmin):
    list_display = ("id", "phone", "purpose", "attempts", "expires_at", "consumed_at", "created_at")
    list_filter = ("purpose",)


@admin.register(TotpDevice)
class TotpDeviceAdmin(_ReadOnlyAdmin):
    list_display = ("user", "confirmed_at", "created_at")
