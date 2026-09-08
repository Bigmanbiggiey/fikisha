from __future__ import annotations

from typing import Any

from rest_framework import serializers

from fikisha.identity.models import AuthSession, OtpPurpose, RoleAssignment, User
from fikisha.identity.phone import normalize_phone


class OtpRequestSerializer(serializers.Serializer):
    phone = serializers.CharField(max_length=32)
    purpose = serializers.ChoiceField(
        choices=[OtpPurpose.LOGIN, OtpPurpose.STEP_UP], default=OtpPurpose.LOGIN
    )

    def validate_phone(self, value: str) -> str:
        from django.core.exceptions import ValidationError as DjangoValidationError

        try:
            return normalize_phone(value)
        except DjangoValidationError as exc:
            raise serializers.ValidationError(
                exc.messages, code=getattr(exc, "code", "invalid")
            ) from exc


class OtpVerifySerializer(serializers.Serializer):
    challenge_id = serializers.UUIDField()
    code = serializers.CharField(max_length=12, trim_whitespace=True)


class MeSerializer(serializers.ModelSerializer):
    roles = serializers.SerializerMethodField()
    is_admin = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ("id", "phone", "display_name", "locale", "status", "roles", "is_admin")
        read_only_fields = fields

    def get_roles(self, obj: User) -> list[str]:
        return sorted(
            RoleAssignment.objects.filter(user=obj, revoked_at__isnull=True).values_list(
                "role", flat=True
            )
        )

    def get_is_admin(self, obj: User) -> bool:
        return getattr(getattr(obj, "admin_profile", None), "active", False) is True


class MeUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ("display_name", "locale")


class SessionSerializer(serializers.ModelSerializer):
    current = serializers.SerializerMethodField()

    class Meta:
        model = AuthSession
        fields = (
            "id",
            "device_label",
            "user_agent",
            "ip",
            "is_admin_session",
            "created_at",
            "last_seen_at",
            "expires_at",
            "current",
        )
        read_only_fields = fields

    def get_current(self, obj: AuthSession) -> bool:
        current = self.context.get("current_session_id")
        return current is not None and str(current) == str(obj.id)


class AccessTokenSerializer(serializers.Serializer):
    """Documents the shape of the auth success payload for the schema."""

    access_token = serializers.CharField()
    access_expires_in = serializers.IntegerField()
    user = MeSerializer(required=False)

    def to_representation(self, instance: Any) -> dict[str, Any]:  # pragma: no cover - schema only
        return instance
