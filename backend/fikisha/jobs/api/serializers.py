"""Job/custody/recipient API serializers — shape/type validation only. Every
business rule (band, proof matrix, eligibility, price) stays in the domain
services these feed (Step 10 brief §27)."""

from __future__ import annotations

from typing import Any

from rest_framework import serializers

from fikisha.jobs.constants import CancellationReason, RecipientIssueCategory


class LocationWriteSerializer(serializers.Serializer[dict[str, Any]]):
    address_text = serializers.CharField(max_length=2000, required=False, allow_blank=True)
    lat = serializers.DecimalField(max_digits=9, decimal_places=6, required=False, allow_null=True)
    lng = serializers.DecimalField(max_digits=9, decimal_places=6, required=False, allow_null=True)
    contact_name = serializers.CharField(max_length=120, required=False, allow_blank=True)
    contact_phone = serializers.CharField(max_length=32, required=False, allow_blank=True)
    notes = serializers.CharField(max_length=2000, required=False, allow_blank=True)


class CargoWriteSerializer(serializers.Serializer[dict[str, Any]]):
    description = serializers.CharField(max_length=4000)
    category_code = serializers.CharField(max_length=64, required=False, allow_blank=True)
    est_weight_kg = serializers.IntegerField(required=False, allow_null=True, min_value=0)
    dims_l_cm = serializers.IntegerField(required=False, allow_null=True, min_value=0)
    dims_w_cm = serializers.IntegerField(required=False, allow_null=True, min_value=0)
    dims_h_cm = serializers.IntegerField(required=False, allow_null=True, min_value=0)
    declared_value_kes = serializers.IntegerField(min_value=1)
    handling_flags = serializers.ListField(child=serializers.CharField(), required=False)


class VehicleRequirementWriteSerializer(serializers.Serializer[dict[str, Any]]):
    required_vehicle_class_codes = serializers.ListField(
        child=serializers.CharField(), required=False
    )
    min_payload_kg = serializers.IntegerField(required=False, min_value=0, default=0)
    min_volume_m3 = serializers.DecimalField(
        max_digits=7, decimal_places=2, required=False, allow_null=True
    )
    required_features = serializers.ListField(child=serializers.CharField(), required=False)
    notes = serializers.CharField(max_length=2000, required=False, allow_blank=True)


class JobCreateSerializer(serializers.Serializer[dict[str, Any]]):
    pickup_location = LocationWriteSerializer()
    destination_location = LocationWriteSerializer()
    cargo = CargoWriteSerializer()
    vehicle_requirement = VehicleRequirementWriteSerializer(required=False)
    recipient_name = serializers.CharField(max_length=120, required=False, allow_blank=True)
    recipient_phone = serializers.CharField(max_length=32, required=False, allow_blank=True)
    delivery_requirements = serializers.CharField(max_length=4000, required=False, allow_blank=True)
    delivery_flags = serializers.ListField(child=serializers.CharField(), required=False)
    proposed_price_kes = serializers.IntegerField(required=False, allow_null=True, min_value=1)
    latent_risk_cargo = serializers.BooleanField(required=False, default=False)


class CancelJobSerializer(serializers.Serializer[dict[str, Any]]):
    reason_code = serializers.ChoiceField(
        choices=CancellationReason.choices, default=CancellationReason.OTHER
    )
    reason_text = serializers.CharField(max_length=2000, required=False, allow_blank=True)


class GeoSerializer(serializers.Serializer[dict[str, Any]]):
    lat = serializers.FloatField(required=False, allow_null=True)
    lng = serializers.FloatField(required=False, allow_null=True)
    accuracy_m = serializers.FloatField(required=False, allow_null=True)


class ArriveSerializer(serializers.Serializer[dict[str, Any]]):
    geo = GeoSerializer(required=False)


class ConfirmPickupOtpSerializer(serializers.Serializer[dict[str, Any]]):
    code = serializers.CharField(max_length=12)
    condition_note = serializers.CharField(max_length=2000, required=False, allow_blank=True)


class ConfirmPickupBusinessSerializer(serializers.Serializer[dict[str, Any]]):
    condition_note = serializers.CharField(max_length=2000, required=False, allow_blank=True)


class ConfirmPickupAttestedSerializer(serializers.Serializer[dict[str, Any]]):
    pickup_contact_name = serializers.CharField(max_length=120)
    condition_note = serializers.CharField(max_length=2000, required=False, allow_blank=True)


class FailAtPickupSerializer(serializers.Serializer[dict[str, Any]]):
    reason_text = serializers.CharField(max_length=2000)


class ConfirmDeliverySerializer(serializers.Serializer[dict[str, Any]]):
    party_name = serializers.CharField(max_length=120)
    code = serializers.CharField(max_length=12, required=False, allow_blank=True)
    condition_note = serializers.CharField(max_length=2000, required=False, allow_blank=True)
    geo = GeoSerializer(required=False)


class AssignSerializer(serializers.Serializer[dict[str, Any]]):
    driver_profile_id = serializers.UUIDField()
    vehicle_id = serializers.UUIDField()
    admin_override_reason = serializers.CharField(max_length=2000, required=False, allow_blank=True)


class RecipientConfirmSerializer(serializers.Serializer[dict[str, Any]]):
    code = serializers.CharField(max_length=12)
    party_name = serializers.CharField(max_length=120)


class RecipientReportIssueSerializer(serializers.Serializer[dict[str, Any]]):
    category = serializers.ChoiceField(choices=RecipientIssueCategory.choices)
    description = serializers.CharField(max_length=2000, required=False, allow_blank=True)
    other_label = serializers.CharField(max_length=80, required=False, allow_blank=True)
