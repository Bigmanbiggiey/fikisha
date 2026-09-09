from __future__ import annotations

from typing import Any

from rest_framework import serializers

from fikisha.operators.models import (
    BaseMembership,
    BaseType,
    OperatingBase,
    OperatorProfile,
    OperatorStatus,
)
from fikisha.platform_config.models import Zone


class OperatorProfileSerializer(serializers.ModelSerializer[OperatorProfile]):
    user_phone = serializers.CharField(source="user.phone", read_only=True)

    class Meta:
        model = OperatorProfile
        fields = (
            "id",
            "user_id",
            "user_phone",
            "full_name",
            "display_name",
            "phones",
            "status",
            "created_at",
            "updated_at",
        )
        read_only_fields = fields


class OperatorCreateSerializer(serializers.Serializer[dict[str, Any]]):
    full_name = serializers.CharField(max_length=160)
    display_name = serializers.CharField(
        max_length=120, required=False, allow_blank=True, default=""
    )
    phones = serializers.ListField(
        child=serializers.CharField(max_length=20), required=False, default=list
    )


class OperatorUpdateSerializer(serializers.Serializer[dict[str, Any]]):
    full_name = serializers.CharField(max_length=160, required=False)
    display_name = serializers.CharField(max_length=120, required=False, allow_blank=True)
    phones = serializers.ListField(child=serializers.CharField(max_length=20), required=False)
    status = serializers.ChoiceField(choices=OperatorStatus.choices, required=False)


class OperatingLocationSerializer(serializers.ModelSerializer[OperatingBase]):
    zone_code = serializers.CharField(source="zone.code", read_only=True, default=None)

    class Meta:
        model = OperatingBase
        fields = (
            "id",
            "name",
            "type",
            "lat",
            "lng",
            "zone_code",
            "landmark",
            "created_by_id",
            "created_at",
            "updated_at",
        )
        read_only_fields = fields


class OperatingLocationWriteSerializer(serializers.Serializer[dict[str, Any]]):
    name = serializers.CharField(max_length=160, required=False)
    type = serializers.ChoiceField(choices=BaseType.choices, required=False)
    lat = serializers.DecimalField(max_digits=9, decimal_places=6, required=False, allow_null=True)
    lng = serializers.DecimalField(max_digits=9, decimal_places=6, required=False, allow_null=True)
    zone_code = serializers.CharField(max_length=40, required=False, allow_blank=True)
    landmark = serializers.CharField(max_length=200, required=False, allow_blank=True)

    def validate_zone_code(self, value: str) -> str:
        if value and not Zone.objects.filter(code=value, active=True).exists():
            raise serializers.ValidationError(f"Unknown zone {value!r}.")
        return value

    def to_service_data(self) -> dict[str, Any]:
        data = dict(self.validated_data)
        zone_code = data.pop("zone_code", None)
        if zone_code:
            data["zone_id"] = (
                Zone.objects.filter(code=zone_code, active=True)
                .values_list("id", flat=True)
                .first()
            )
        elif zone_code == "":
            data["zone_id"] = None
        return data


class BaseMembershipSerializer(serializers.ModelSerializer[BaseMembership]):
    base_name = serializers.CharField(source="base.name", read_only=True)
    base_type = serializers.CharField(source="base.type", read_only=True)

    class Meta:
        model = BaseMembership
        fields = (
            "id",
            "base_id",
            "base_name",
            "base_type",
            "operator_id",
            "group_id",
            "role",
            "status",
            "created_at",
        )
        read_only_fields = fields


class BaseAssociateSerializer(serializers.Serializer[dict[str, Any]]):
    base_id = serializers.UUIDField()
    role = serializers.CharField(max_length=40, required=False, allow_blank=True, default="")
