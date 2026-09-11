from __future__ import annotations

from typing import Any

from rest_framework import serializers


class ProposeSerializer(serializers.Serializer[dict[str, Any]]):
    operator_id = serializers.UUIDField(required=False, allow_null=True)
    group_id = serializers.UUIDField(required=False, allow_null=True)
    amount_kes = serializers.IntegerField(min_value=1)
    note = serializers.CharField(max_length=2000, required=False, allow_blank=True)

    def validate(self, attrs: dict[str, Any]) -> dict[str, Any]:
        if bool(attrs.get("operator_id")) == bool(attrs.get("group_id")):
            raise serializers.ValidationError("Exactly one of operator_id or group_id is required.")
        return attrs


class CounterSerializer(serializers.Serializer[dict[str, Any]]):
    amount_kes = serializers.IntegerField(min_value=1)
    note = serializers.CharField(max_length=2000, required=False, allow_blank=True)


class AcceptSerializer(serializers.Serializer[dict[str, Any]]):
    amount_kes = serializers.IntegerField(min_value=1, required=False, allow_null=True)


class DeclineSerializer(serializers.Serializer[dict[str, Any]]):
    note = serializers.CharField(max_length=2000, required=False, allow_blank=True)
