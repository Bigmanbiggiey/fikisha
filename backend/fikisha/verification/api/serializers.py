from __future__ import annotations

from typing import Any

from rest_framework import serializers

from fikisha.verification.models import (
    Domain,
    EvidenceKind,
    State,
    SubjectType,
    VerificationDecision,
    VerificationEvidence,
    VerificationRecord,
)


class DecisionSerializer(serializers.ModelSerializer[VerificationDecision]):
    class Meta:
        model = VerificationDecision
        fields = (
            "id",
            "action",
            "actor_id",
            "actor_role",
            "reason",
            "note",
            "set_expires_at",
            "created_at",
        )
        read_only_fields = fields


class EvidenceItemSerializer(serializers.ModelSerializer[VerificationEvidence]):
    evidence_id = serializers.CharField(source="evidence_object_id", read_only=True)
    content_type = serializers.CharField(source="evidence_object.content_type", read_only=True)
    pii_class = serializers.CharField(source="evidence_object.pii_class", read_only=True)

    class Meta:
        model = VerificationEvidence
        fields = (
            "id",
            "evidence_id",
            "kind",
            "content_type",
            "pii_class",
            "issued_at",
            "expires_at",
            "submitted_by_id",
            "submitted_at",
            "superseded_at",
        )
        read_only_fields = fields


class RecordSerializer(serializers.ModelSerializer[VerificationRecord]):
    effective_state = serializers.SerializerMethodField()
    subject_id = serializers.CharField(read_only=True)

    class Meta:
        model = VerificationRecord
        fields = (
            "id",
            "subject_type",
            "subject_id",
            "domain",
            "state",
            "effective_state",
            "issuing_authority",
            "reviewer_id",
            "owner_admin_id",
            "verified_at",
            "expires_at",
            "created_at",
            "updated_at",
        )
        read_only_fields = fields

    def get_effective_state(self, obj: VerificationRecord) -> str:
        return obj.effective_state()


class RecordDetailSerializer(RecordSerializer):
    evidence = serializers.SerializerMethodField()
    decisions = DecisionSerializer(many=True, read_only=True)

    class Meta(RecordSerializer.Meta):
        fields = (  # type: ignore[assignment]
            *RecordSerializer.Meta.fields,
            "evidence",
            "decisions",
        )

    def get_evidence(self, obj: VerificationRecord) -> Any:
        return EvidenceItemSerializer(
            obj.evidence.select_related("evidence_object").all(), many=True
        ).data


class RecordCreateSerializer(serializers.Serializer[dict[str, Any]]):
    subject_type = serializers.ChoiceField(choices=SubjectType.choices)
    subject_id = serializers.UUIDField()
    domain = serializers.ChoiceField(choices=Domain.choices)


class EvidenceUploadSerializer(serializers.Serializer[dict[str, Any]]):
    file = serializers.FileField()
    kind = serializers.ChoiceField(choices=EvidenceKind.choices)
    issued_at = serializers.DateField(required=False, allow_null=True)
    expires_at = serializers.DateField(required=False, allow_null=True)


class SubmitSerializer(serializers.Serializer[dict[str, Any]]):
    issuing_authority = serializers.CharField(
        max_length=120, required=False, allow_blank=True, default=""
    )


class RequestInfoSerializer(serializers.Serializer[dict[str, Any]]):
    note = serializers.CharField(max_length=1000)


class ApproveSerializer(serializers.Serializer[dict[str, Any]]):
    expires_at = serializers.DateTimeField(required=False, allow_null=True)
    reason = serializers.CharField(max_length=1000, required=False, allow_blank=True, default="")


class RejectSerializer(serializers.Serializer[dict[str, Any]]):
    reason = serializers.CharField(max_length=1000)


_STATE_VALUES = set(State.values)
