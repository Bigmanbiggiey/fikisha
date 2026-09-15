from __future__ import annotations

from typing import Any

from rest_framework import serializers

from fikisha.business.models import (
    BusinessAccount,
    BusinessLocation,
    BusinessMembership,
    BusinessRole,
    BusinessStanding,
    LocationType,
    MembershipStatus,
)
from fikisha.platform_config.models import Zone


class BusinessSerializer(serializers.ModelSerializer[BusinessAccount]):
    my_role = serializers.SerializerMethodField()

    class Meta:
        model = BusinessAccount
        fields = (
            "id",
            "trading_name",
            "category",
            "contact_name",
            "contact_phone",
            "contact_email",
            "standing",
            "verification_status",
            "my_role",
            "created_at",
            "updated_at",
        )
        read_only_fields = fields

    def get_my_role(self, obj: BusinessAccount) -> str | None:
        # List views (`services.businesses_for`) annotate `my_role` per-row via
        # a subquery — a flat `context["my_role"]` can't vary across a list.
        # Single-object create/detail views still set it in context.
        annotated = getattr(obj, "my_role", None)
        if annotated is not None:
            return annotated
        return self.context.get("my_role")


class BusinessCreateSerializer(serializers.Serializer[dict[str, Any]]):
    trading_name = serializers.CharField(max_length=200)
    category = serializers.CharField(max_length=80, required=False, allow_blank=True, default="")
    contact_name = serializers.CharField(
        max_length=120, required=False, allow_blank=True, default=""
    )
    contact_phone = serializers.CharField(
        max_length=20, required=False, allow_blank=True, default=""
    )
    contact_email = serializers.EmailField(required=False, allow_blank=True, default="")


class BusinessUpdateSerializer(serializers.Serializer[dict[str, Any]]):
    trading_name = serializers.CharField(max_length=200, required=False)
    category = serializers.CharField(max_length=80, required=False, allow_blank=True)
    contact_name = serializers.CharField(max_length=120, required=False, allow_blank=True)
    contact_phone = serializers.CharField(max_length=20, required=False, allow_blank=True)
    contact_email = serializers.EmailField(required=False, allow_blank=True)
    standing = serializers.ChoiceField(choices=BusinessStanding.choices, required=False)


class MembershipSerializer(serializers.ModelSerializer[BusinessMembership]):
    user_phone = serializers.CharField(source="user.phone", read_only=True)
    user_display_name = serializers.CharField(source="user.display_name", read_only=True)

    class Meta:
        model = BusinessMembership
        fields = (
            "id",
            "user_id",
            "user_phone",
            "user_display_name",
            "role",
            "status",
            "created_at",
            "updated_at",
        )
        read_only_fields = fields


class MemberAddSerializer(serializers.Serializer[dict[str, Any]]):
    phone = serializers.CharField(max_length=32)
    role = serializers.ChoiceField(choices=BusinessRole.choices)


class MemberUpdateSerializer(serializers.Serializer[dict[str, Any]]):
    role = serializers.ChoiceField(choices=BusinessRole.choices, required=False)
    status = serializers.ChoiceField(choices=MembershipStatus.choices, required=False)

    def validate(self, attrs: dict[str, Any]) -> dict[str, Any]:
        if not attrs:
            raise serializers.ValidationError("Provide role and/or status.")
        return attrs


class LocationSerializer(serializers.ModelSerializer[BusinessLocation]):
    zone_code = serializers.CharField(source="zone.code", read_only=True, default=None)

    class Meta:
        model = BusinessLocation
        fields = (
            "id",
            "label",
            "type",
            "address_text",
            "lat",
            "lng",
            "zone_code",
            "contact_name",
            "contact_phone",
            "hours",
            "access_notes",
            "created_at",
            "updated_at",
        )
        read_only_fields = fields


class LocationWriteSerializer(serializers.Serializer[dict[str, Any]]):
    # ``label`` shadows ``Field.label`` (fine at runtime — DRF collects declared
    # fields via the metaclass); silence the drf-stubs assignment complaint.
    label = serializers.CharField(max_length=120, required=False)  # type: ignore[assignment]
    type = serializers.ChoiceField(choices=LocationType.choices, required=False)
    address_text = serializers.CharField(required=False, allow_blank=True)
    lat = serializers.DecimalField(max_digits=9, decimal_places=6, required=False, allow_null=True)
    lng = serializers.DecimalField(max_digits=9, decimal_places=6, required=False, allow_null=True)
    zone_code = serializers.CharField(max_length=40, required=False, allow_blank=True)
    contact_name = serializers.CharField(max_length=120, required=False, allow_blank=True)
    contact_phone = serializers.CharField(max_length=20, required=False, allow_blank=True)
    hours = serializers.JSONField(required=False)
    access_notes = serializers.CharField(required=False, allow_blank=True)

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
