from __future__ import annotations

from typing import Any

from rest_framework import serializers

from fikisha.incidents.constants import (
    ROUTABLE_JOB_STATUSES,
    CommissionTreatment,
    IncidentSeverity,
    IncidentType,
    ResolutionAction,
    ResolutionOutcome,
)


class ReportIncidentSerializer(serializers.Serializer[dict[str, Any]]):
    type = serializers.ChoiceField(choices=IncidentType.choices)
    severity = serializers.ChoiceField(choices=IncidentSeverity.choices, required=False)
    description = serializers.CharField(max_length=4000, required=False, allow_blank=True)
    other_label = serializers.CharField(max_length=120, required=False, allow_blank=True)


class AttachEvidenceSerializer(serializers.Serializer[dict[str, Any]]):
    file = serializers.FileField()
    caption = serializers.CharField(max_length=200, required=False, allow_blank=True)


class AddStatementSerializer(serializers.Serializer[dict[str, Any]]):
    text = serializers.CharField(max_length=8000)


class EscalateSerializer(serializers.Serializer[dict[str, Any]]):
    reason = serializers.CharField(max_length=4000)
    escalated_to = serializers.CharField(max_length=120, required=False, default="FOUNDER")
    advised_external_options = serializers.BooleanField(required=False, default=False)


class CloseIncidentSerializer(serializers.Serializer[dict[str, Any]]):
    reason_code = serializers.CharField(max_length=32, allow_blank=True)
    note = serializers.CharField(max_length=4000, allow_blank=True)


class RecordFindingSerializer(serializers.Serializer[dict[str, Any]]):
    outcome = serializers.CharField(max_length=16)
    parties = serializers.ListField(
        child=serializers.CharField(max_length=10), required=False, default=list
    )
    reason = serializers.CharField(max_length=4000, allow_blank=True)


class UnfoundedSerializer(serializers.Serializer[dict[str, Any]]):
    reason = serializers.CharField(max_length=4000, allow_blank=True)


class ResumeDisputeSerializer(serializers.Serializer[dict[str, Any]]):
    sender_method = serializers.CharField(max_length=16, allow_blank=True)
    operator_method = serializers.CharField(max_length=16, allow_blank=True)
    sender_confirmed_at = serializers.DateTimeField(required=False, allow_null=True)
    operator_confirmed_at = serializers.DateTimeField(required=False, allow_null=True)
    reason = serializers.CharField(max_length=4000, allow_blank=True)


class OpenDisputeSerializer(serializers.Serializer[dict[str, Any]]):
    incident_ids = serializers.ListField(child=serializers.UUIDField(), min_length=1)


class ResolveDisputeSerializer(serializers.Serializer[dict[str, Any]]):
    outcome_code = serializers.ChoiceField(choices=ResolutionOutcome.choices)
    rationale = serializers.CharField(max_length=8000)
    routed_job_status = serializers.ChoiceField(choices=sorted(ROUTABLE_JOB_STATUSES))
    commission_treatment = serializers.ChoiceField(
        choices=CommissionTreatment.choices, required=False, default=CommissionTreatment.APPLY
    )
    reduced_amount_kes = serializers.IntegerField(required=False, allow_null=True, min_value=1)
    # The business side (commission split D-5). Left out: the same as the
    # operator side's treatment and amount.
    business_commission_treatment = serializers.ChoiceField(
        choices=CommissionTreatment.choices, required=False, allow_null=True
    )
    business_reduced_amount_kes = serializers.IntegerField(
        required=False, allow_null=True, min_value=1
    )
    agreed_compensation_kes = serializers.IntegerField(required=False, allow_null=True, min_value=1)
    actions = serializers.ListField(
        child=serializers.ChoiceField(choices=ResolutionAction.choices), required=False
    )
