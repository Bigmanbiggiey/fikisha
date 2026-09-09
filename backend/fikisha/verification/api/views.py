"""Verification API (Phase 2C).

Submission is incremental: create a record, attach evidence items, then submit.
Review actions require the ``verification.decide`` permission; the service layer
also blocks a reviewer who was the submitter (brief §17). Evidence bytes are
streamed through the API after an explicit authorization check, and every
HIGH-PII fetch is logged.
"""

from __future__ import annotations

from typing import Any

from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.request import Request
from rest_framework.response import Response

from fikisha.common.api import OrgApiView, paginated
from fikisha.common.exceptions import AuthorizationError
from fikisha.identity.authz.actors import actor_from_request
from fikisha.operators.models import OperatingBase, OperatorProfile
from fikisha.vehicles.models import Vehicle
from fikisha.verification import authz, services
from fikisha.verification.api.serializers import (
    ApproveSerializer,
    EvidenceUploadSerializer,
    RecordCreateSerializer,
    RecordDetailSerializer,
    RecordSerializer,
    RejectSerializer,
    RequestInfoSerializer,
    SubmitSerializer,
)
from fikisha.verification.models import (
    State,
    SubjectType,
    VerificationEvidence,
    VerificationRecord,
)
from fikisha.verification.requirements import required_domains_for_subject

_SUBJECT_MODEL: dict[str, Any] = {
    str(SubjectType.OPERATOR): OperatorProfile,
    str(SubjectType.VEHICLE): Vehicle,
    str(SubjectType.BASE): OperatingBase,
}


def _resolve_subject(subject_type: str, subject_id: Any) -> Any:
    model = _SUBJECT_MODEL.get(subject_type)
    if model is None:
        raise AuthorizationError("Unknown subject type.", code="validation_error")
    return get_object_or_404(model, pk=subject_id)


def _owned_records_qs(request: Request) -> Any:
    user: Any = request.user
    profile_ids = list(OperatorProfile.objects.filter(user=user).values_list("id", flat=True))
    from fikisha.groups.models import GroupMembership, GroupMembershipStatus

    group_ids = list(
        GroupMembership.objects.filter(
            operator__user=user, status=GroupMembershipStatus.ACTIVE
        ).values_list("group_id", flat=True)
    )
    vehicle_ids = list(
        Vehicle.objects.filter(owner_operator_id__in=profile_ids).values_list("id", flat=True)
    ) + list(Vehicle.objects.filter(owner_group_id__in=group_ids).values_list("id", flat=True))
    base_ids = list(OperatingBase.objects.filter(created_by=user).values_list("id", flat=True))

    from django.db.models import Q

    return VerificationRecord.objects.filter(
        Q(subject_operator_id__in=profile_ids)
        | Q(subject_vehicle_id__in=vehicle_ids)
        | Q(subject_base_id__in=base_ids)
    ).order_by("-created_at")


class RecordCollectionView(OrgApiView):
    action_get = "verification.record.list"
    action_post = "verification.submit"

    def get(self, request: Request) -> Response:
        qs = _owned_records_qs(request)
        if request.query_params.get("domain"):
            qs = qs.filter(domain=request.query_params["domain"])
        if request.query_params.get("state"):
            qs = qs.filter(state=request.query_params["state"])
        return paginated(request, qs, RecordSerializer)

    def post(self, request: Request) -> Response:
        serializer = RecordCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        actor = actor_from_request(request)
        subject = _resolve_subject(
            serializer.validated_data["subject_type"], serializer.validated_data["subject_id"]
        )
        if not authz.can_submit_for(actor, subject) and not self.is_platform_admin(request):
            raise AuthorizationError("Not your verification subject.", code="authz.forbidden")
        record = services.get_or_create_record(
            subject=subject, domain=serializer.validated_data["domain"]
        )
        return Response(RecordDetailSerializer(record).data, status=status.HTTP_201_CREATED)


class RecordDetailView(OrgApiView):
    action_get = "verification.record.read"

    def resolve_target(self) -> VerificationRecord:
        return get_object_or_404(
            VerificationRecord.objects.prefetch_related("decisions", "evidence"),
            pk=self.kwargs["record_id"],
        )

    def get(self, request: Request, record_id: str) -> Response:
        return Response(RecordDetailSerializer(self.get_authz_resource()).data)


class RecordEvidenceView(OrgApiView):
    action_post = "verification.submit"
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    def resolve_target(self) -> VerificationRecord:
        return get_object_or_404(VerificationRecord, pk=self.kwargs["record_id"])

    def post(self, request: Request, record_id: str) -> Response:
        record = self.get_authz_resource()
        actor = actor_from_request(request)
        subject = _record_subject(record)
        if not authz.can_submit_for(actor, subject) and not self.is_platform_admin(request):
            raise AuthorizationError("Not your verification subject.", code="authz.forbidden")

        serializer = EvidenceUploadSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        upload = serializer.validated_data["file"]
        ev = services.add_evidence(
            actor=actor,
            record=record,
            item={
                "data": upload.read(),
                "content_type": upload.content_type or "application/octet-stream",
                "kind": serializer.validated_data["kind"],
                "issued_at": serializer.validated_data.get("issued_at"),
                "expires_at": serializer.validated_data.get("expires_at"),
            },
        )
        return Response(
            RecordDetailSerializer(record).data | {"attached_evidence_id": str(ev.id)},
            status=status.HTTP_201_CREATED,
        )


class RecordSubmitView(OrgApiView):
    action_post = "verification.submit"

    def resolve_target(self) -> VerificationRecord:
        return get_object_or_404(VerificationRecord, pk=self.kwargs["record_id"])

    def post(self, request: Request, record_id: str) -> Response:
        record = self.get_authz_resource()
        actor = actor_from_request(request)
        if not authz.can_submit_for(actor, _record_subject(record)) and not self.is_platform_admin(
            request
        ):
            raise AuthorizationError("Not your verification subject.", code="authz.forbidden")
        serializer = SubmitSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        record = services.mark_submitted(
            actor=actor,
            record=record,
            issuing_authority=serializer.validated_data["issuing_authority"],
        )
        return Response(RecordDetailSerializer(record).data)


class _ReviewView(OrgApiView):
    action_post = "verification.decide"

    def resolve_target(self) -> VerificationRecord:
        return get_object_or_404(VerificationRecord, pk=self.kwargs["record_id"])


class ReviewStartView(_ReviewView):
    def post(self, request: Request, record_id: str) -> Response:
        record = services.start_review(
            reviewer=actor_from_request(request), record=self.get_authz_resource()
        )
        return Response(RecordDetailSerializer(record).data)


class ReviewRequestInfoView(_ReviewView):
    def post(self, request: Request, record_id: str) -> Response:
        serializer = RequestInfoSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        record = services.request_info(
            reviewer=actor_from_request(request),
            record=self.get_authz_resource(),
            note=serializer.validated_data["note"],
        )
        return Response(RecordDetailSerializer(record).data)


class ReviewApproveView(_ReviewView):
    def post(self, request: Request, record_id: str) -> Response:
        serializer = ApproveSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        record = services.approve(
            reviewer=actor_from_request(request),
            record=self.get_authz_resource(),
            expires_at=serializer.validated_data.get("expires_at"),
            reason=serializer.validated_data["reason"],
        )
        return Response(RecordDetailSerializer(record).data)


class ReviewRejectView(_ReviewView):
    def post(self, request: Request, record_id: str) -> Response:
        serializer = RejectSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        record = services.reject(
            reviewer=actor_from_request(request),
            record=self.get_authz_resource(),
            reason=serializer.validated_data["reason"],
        )
        return Response(RecordDetailSerializer(record).data)


class QueueView(OrgApiView):
    action_get = "verification.queue"

    def get(self, request: Request) -> Response:
        qs = VerificationRecord.objects.filter(
            state__in=[State.SUBMITTED, State.IN_REVIEW, State.INFO_REQUESTED]
        ).order_by("created_at")
        if request.query_params.get("subject_type"):
            qs = qs.filter(subject_type=request.query_params["subject_type"])
        if request.query_params.get("domain"):
            qs = qs.filter(domain=request.query_params["domain"])
        return paginated(request, qs, RecordSerializer)


class SubjectStatusView(OrgApiView):
    action_get = "verification.record.list"

    def get(self, request: Request, subject_type: str, subject_id: str) -> Response:
        subject = _resolve_subject(subject_type, subject_id)
        actor = actor_from_request(request)
        from fikisha.identity.authz.policies import actor_has_permission

        is_reviewer = actor_has_permission(actor, "verification.decide") or actor_has_permission(
            actor, "verification.queue.view"
        )
        if not (authz.can_submit_for(actor, subject) or is_reviewer):
            raise AuthorizationError("Not your verification subject.", code="authz.forbidden")
        return Response(
            {
                "subject_type": subject_type,
                "subject_id": str(subject_id),
                "eligibility": services.eligibility(subject),
                "requirements": services.requirements_status(subject),
                "required_domains": required_domains_for_subject(subject),
            }
        )


class EvidenceContentView(OrgApiView):
    action_get = "verification.evidence.read"

    def resolve_target(self) -> VerificationRecord:
        ev = get_object_or_404(
            VerificationEvidence.objects.select_related("record", "evidence_object"),
            pk=self.kwargs["evidence_id"],
        )
        self._evidence = ev
        return ev.record

    def get(self, request: Request, evidence_id: str) -> HttpResponse:
        self.get_authz_resource()  # runs the authz check
        ev: VerificationEvidence = self._evidence
        actor = actor_from_request(request)
        from fikisha.evidence import services as evidence_services

        payload, content_type = evidence_services.open_stream(
            ev.evidence_object,
            actor_user=request.user,
            actor_role=str(getattr(actor, "audit_role", "")),
            reason=f"verification {ev.record.domain} review",
        )
        response = HttpResponse(payload, content_type=content_type)
        response["Content-Disposition"] = f'inline; filename="{ev.kind.lower()}"'
        response["Cache-Control"] = "no-store"
        return response


# ─── helpers ────────────────────────────────────────────────────────
def _record_subject(record: VerificationRecord) -> Any:
    if record.subject_operator_id:
        return OperatorProfile.objects.get(pk=record.subject_operator_id)
    if record.subject_vehicle_id:
        return Vehicle.objects.select_related("vehicle_class").get(pk=record.subject_vehicle_id)
    return OperatingBase.objects.get(pk=record.subject_base_id)  # type: ignore[misc]
