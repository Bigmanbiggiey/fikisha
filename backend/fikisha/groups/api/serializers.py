from __future__ import annotations

from typing import Any

from rest_framework import serializers

from fikisha.groups.models import (
    AssignmentMode,
    GroupMemberRole,
    GroupMembership,
    GroupMembershipStatus,
    GroupStanding,
    GroupType,
    OperatorGroup,
)


class GroupSerializer(serializers.ModelSerializer[OperatorGroup]):
    my_role = serializers.SerializerMethodField()

    class Meta:
        model = OperatorGroup
        fields = (
            "id",
            "name",
            "type",
            "primary_contact_id",
            "standing",
            "assignment_mode",
            "verification_status",
            "my_role",
            "created_at",
            "updated_at",
        )
        read_only_fields = fields

    def get_my_role(self, obj: OperatorGroup) -> str | None:
        # List views (`services.groups_for`) annotate `my_role` per-row via a
        # subquery — a flat `context["my_role"]` can't vary across a list.
        # Single-object create/detail views still set it in context.
        annotated = getattr(obj, "my_role", None)
        if annotated is not None:
            return annotated
        return self.context.get("my_role")


class GroupCreateSerializer(serializers.Serializer[dict[str, Any]]):
    name = serializers.CharField(max_length=160)
    type = serializers.ChoiceField(choices=GroupType.choices)
    assignment_mode = serializers.ChoiceField(
        choices=AssignmentMode.choices, required=False, default=AssignmentMode.MANAGER_ASSIGNS
    )


class GroupUpdateSerializer(serializers.Serializer[dict[str, Any]]):
    name = serializers.CharField(max_length=160, required=False)
    assignment_mode = serializers.ChoiceField(choices=AssignmentMode.choices, required=False)
    standing = serializers.ChoiceField(choices=GroupStanding.choices, required=False)


class GroupMembershipSerializer(serializers.ModelSerializer[GroupMembership]):
    operator_name = serializers.CharField(source="operator.full_name", read_only=True)
    operator_user_id = serializers.CharField(source="operator.user_id", read_only=True)

    class Meta:
        model = GroupMembership
        fields = (
            "id",
            "group_id",
            "operator_id",
            "operator_name",
            "operator_user_id",
            "role",
            "status",
            "since",
            "created_at",
        )
        read_only_fields = fields


class GroupMemberAddSerializer(serializers.Serializer[dict[str, Any]]):
    operator_id = serializers.UUIDField()
    role = serializers.ChoiceField(choices=GroupMemberRole.choices)


class GroupMemberUpdateSerializer(serializers.Serializer[dict[str, Any]]):
    role = serializers.ChoiceField(choices=GroupMemberRole.choices, required=False)
    status = serializers.ChoiceField(choices=GroupMembershipStatus.choices, required=False)

    def validate(self, attrs: dict[str, Any]) -> dict[str, Any]:
        if not attrs:
            raise serializers.ValidationError("Provide role and/or status.")
        return attrs
