from __future__ import annotations

from typing import Any

from rest_framework import serializers

from fikisha.vehicles.models import CapacityUnit, Vehicle, VehicleOwnership, VehicleStatus


class VehicleSerializer(serializers.ModelSerializer[Vehicle]):
    vehicle_class = serializers.CharField(source="vehicle_class.code", read_only=True)
    vehicle_class_heavy = serializers.BooleanField(source="vehicle_class.heavy", read_only=True)
    controller_kind = serializers.CharField(read_only=True)

    class Meta:
        model = Vehicle
        fields = (
            "id",
            "owner_operator_id",
            "owner_group_id",
            "controller_kind",
            "vehicle_class",
            "vehicle_class_heavy",
            "sub_descriptor",
            "registration",
            "make",
            "model",
            "year",
            "capacity_value",
            "capacity_unit",
            "volume_m3",
            "tare_kg",
            "feature_tags",
            "ownership",
            "speed_limiter_fitted",
            "telematics_installed",
            "status",
            "created_at",
            "updated_at",
        )
        read_only_fields = fields


class VehicleCreateSerializer(serializers.Serializer[dict[str, Any]]):
    owner_operator_id = serializers.UUIDField(required=False, allow_null=True)
    owner_group_id = serializers.UUIDField(required=False, allow_null=True)
    vehicle_class = serializers.CharField(max_length=40)
    registration = serializers.CharField(max_length=32)
    sub_descriptor = serializers.CharField(max_length=80, required=False, allow_blank=True)
    make = serializers.CharField(max_length=60, required=False, allow_blank=True)
    model = serializers.CharField(max_length=60, required=False, allow_blank=True)
    year = serializers.IntegerField(required=False, allow_null=True, min_value=1950, max_value=2100)
    capacity_value = serializers.DecimalField(max_digits=10, decimal_places=2, min_value=0)
    capacity_unit = serializers.ChoiceField(
        choices=CapacityUnit.choices, required=False, default=CapacityUnit.KG
    )
    volume_m3 = serializers.DecimalField(
        max_digits=8, decimal_places=2, required=False, allow_null=True, min_value=0
    )
    tare_kg = serializers.IntegerField(required=False, allow_null=True, min_value=0)
    feature_tags = serializers.ListField(
        child=serializers.CharField(max_length=40), required=False, default=list
    )
    ownership = serializers.ChoiceField(choices=VehicleOwnership.choices, required=False)
    speed_limiter_fitted = serializers.BooleanField(required=False, allow_null=True)
    telematics_installed = serializers.BooleanField(required=False, allow_null=True)

    def validate(self, attrs: dict[str, Any]) -> dict[str, Any]:
        if bool(attrs.get("owner_operator_id")) == bool(attrs.get("owner_group_id")):
            raise serializers.ValidationError(
                "Provide exactly one of owner_operator_id or owner_group_id."
            )
        return attrs


class VehicleUpdateSerializer(serializers.Serializer[dict[str, Any]]):
    vehicle_class = serializers.CharField(max_length=40, required=False)
    registration = serializers.CharField(max_length=32, required=False)
    sub_descriptor = serializers.CharField(max_length=80, required=False, allow_blank=True)
    make = serializers.CharField(max_length=60, required=False, allow_blank=True)
    model = serializers.CharField(max_length=60, required=False, allow_blank=True)
    year = serializers.IntegerField(required=False, allow_null=True, min_value=1950, max_value=2100)
    capacity_value = serializers.DecimalField(
        max_digits=10, decimal_places=2, required=False, min_value=0
    )
    capacity_unit = serializers.ChoiceField(choices=CapacityUnit.choices, required=False)
    volume_m3 = serializers.DecimalField(
        max_digits=8, decimal_places=2, required=False, allow_null=True, min_value=0
    )
    tare_kg = serializers.IntegerField(required=False, allow_null=True, min_value=0)
    feature_tags = serializers.ListField(child=serializers.CharField(max_length=40), required=False)
    ownership = serializers.ChoiceField(choices=VehicleOwnership.choices, required=False)
    speed_limiter_fitted = serializers.BooleanField(required=False, allow_null=True)
    telematics_installed = serializers.BooleanField(required=False, allow_null=True)


class VehicleStatusSerializer(serializers.Serializer[dict[str, Any]]):
    status = serializers.ChoiceField(choices=VehicleStatus.choices)
    reason = serializers.CharField(max_length=200, required=False, allow_blank=True, default="")


class VehicleDeactivateSerializer(serializers.Serializer[dict[str, Any]]):
    reason = serializers.CharField(max_length=200, required=False, allow_blank=True, default="")
