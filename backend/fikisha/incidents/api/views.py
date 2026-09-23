"""Incidents & Disputes API (Phase 2D Step 10) — a thin adapter over
``fikisha.incidents.services``. No incident/dispute/resolution rule is
implemented here; the API never submits a resolution actor, admin identity,
or trust/rating/suspension effect — all resolved server-side (brief §16)."""

from __future__ import annotations

from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from rest_framework import serializers, status
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.request import Request
from rest_framework.response import Response

from fikisha.common.api import OrgApiView, paginated
from fikisha.common.idempotency import idempotent
from fikisha.evidence import services as evidence_services
from fikisha.identity.authz.actors import actor_from_request
from fikisha.incidents import services
from fikisha.incidents.api.serializers import (
    AddStatementSerializer,
    AttachEvidenceSerializer,
    EscalateSerializer,
    OpenDisputeSerializer,
    ReportIncidentSerializer,
    ResolveDisputeSerializer,
)
from fikisha.incidents.models import Dispute, Incident, IncidentEvidence


def _incident_view(incident: Incident) -> dict[str, object]:
    return {
        "id": str(incident.id),
        "job_id": str(incident.job_id),
        "type": incident.type,
        "other_label": incident.other_label,
        "severity": incident.severity,
        "status": incident.status,
        "description": incident.description,
        "reported_by_kind": incident.reported_by_kind,
        "created_at": incident.created_at.isoformat(),
        "sla_ack_due_at": incident.sla_ack_due_at.isoformat() if incident.sla_ack_due_at else None,
        "sla_action_due_at": (
            incident.sla_action_due_at.isoformat() if incident.sla_action_due_at else None
        ),
        "sla_resolution_due_at": (
            incident.sla_resolution_due_at.isoformat() if incident.sla_resolution_due_at else None
        ),
        # Design Phase 6 Increment 7 — the Ops Officer review workspace
        # (P3 §17.2 "review evidence" / "communication log") has no other
        # way to read these back; both were previously POST-only.
        "evidence": [
            {
                "id": str(e.id),
                "evidence_object_id": str(e.evidence_object_id),
                "caption": e.caption,
                "uploaded_by_kind": e.uploaded_by_kind,
                "created_at": e.created_at.isoformat(),
            }
            for e in incident.evidence.all()
        ],
        "statements": [
            {
                "id": str(s.id),
                "party_kind": s.party_kind,
                "text": s.text,
                "created_at": s.created_at.isoformat(),
            }
            for s in incident.statements.all()
        ],
    }


def _dispute_view(dispute: Dispute) -> dict[str, object]:
    resolution = getattr(dispute, "resolution", None)
    return {
        "id": str(dispute.id),
        "job_id": str(dispute.job_id),
        "incident_ids": dispute.incident_ids,
        "status": dispute.status,
        "pre_dispute_status": dispute.pre_dispute_status,
        "created_at": dispute.created_at.isoformat(),
        "resolution": (
            {
                "id": str(resolution.id),
                "outcome_code": resolution.outcome_code,
                "rationale": resolution.rationale,
                "routed_job_status": resolution.routed_job_status,
                "commission_treatment": resolution.commission_treatment,
                "created_at": resolution.created_at.isoformat(),
            }
            if resolution is not None
            else None
        ),
    }


def _idempotency_key(request: Request) -> str:
    return request.META.get("HTTP_IDEMPOTENCY_KEY", "").strip()


# ─── Incidents ───────────────────────────────────────────────────────
class IncidentCollectionView(OrgApiView):
    action_get = "incident.read"
    action_post = "incident.create"

    def get(self, request: Request, job_id: str) -> Response:
        from fikisha.common.exceptions import AuthorizationError
        from fikisha.incidents import authz as incidents_authz
        from fikisha.jobs.selectors import get_job

        # No `resolve_target` on a collection view (`get_authz_resource()`
        # returns None, so `incident.read` only ran its coarse check) — the
        # real cross-job isolation for *this* list is this explicit check,
        # exactly like `JobCollectionView`/`jobs.job_authz.jobs_visible_to`.
        job = get_job(job_id)
        if not incidents_authz.is_job_party(self.actor(request), job):
            raise AuthorizationError("You are not a party to this job.", code="authz.forbidden")
        incidents = (
            Incident.objects.filter(job=job)
            .prefetch_related("evidence", "statements")
            .order_by("-created_at")
        )
        return Response({"data": [_incident_view(i) for i in incidents]})

    def post(self, request: Request, job_id: str) -> Response:
        serializer = ReportIncidentSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        def run() -> Response:
            incident = services.report_incident(
                actor=self.actor(request),
                job_id=job_id,
                type=serializer.validated_data["type"],
                severity=serializer.validated_data.get("severity", ""),
                description=serializer.validated_data.get("description", ""),
                other_label=serializer.validated_data.get("other_label", ""),
            )
            return Response(_incident_view(incident), status=status.HTTP_201_CREATED)

        return idempotent(request, actor_id=str(request.user.id), run=run)


class IncidentDetailView(OrgApiView):
    action_get = "incident.read"

    def resolve_target(self) -> Incident:
        return get_object_or_404(
            Incident.objects.select_related("job").prefetch_related("evidence", "statements"),
            pk=self.kwargs["incident_id"],
        )

    def get(self, request: Request, incident_id: str) -> Response:
        incident = self.get_authz_resource()
        return Response(_incident_view(incident))


class IncidentEvidenceContentView(OrgApiView):
    """Streams a previously-attached evidence file's bytes — mirrors
    ``verification.api.views.EvidenceContentView`` exactly (Design Phase 6
    Increment 7): without this there was no way to actually *view* an
    incident photo, only its metadata (id/caption)."""

    action_get = "incident.read"

    def resolve_target(self) -> Incident:
        ev = get_object_or_404(
            IncidentEvidence.objects.select_related("incident", "evidence_object"),
            pk=self.kwargs["evidence_id"],
        )
        self._evidence = ev
        return ev.incident

    def get(self, request: Request, evidence_id: str) -> HttpResponse:
        self.get_authz_resource()  # runs the authz check
        ev = self._evidence
        actor = actor_from_request(request)
        payload, content_type = evidence_services.open_stream(
            ev.evidence_object,
            actor_user=request.user,
            actor_role=str(getattr(actor, "audit_role", "")),
            reason=f"incident {ev.incident_id} review",
        )
        response = HttpResponse(payload, content_type=content_type)
        response["Content-Disposition"] = 'inline; filename="evidence"'
        response["Cache-Control"] = "no-store"
        return response


class IncidentEvidenceView(OrgApiView):
    action_post = "incident.evidence.attach"
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    def post(self, request: Request, incident_id: str) -> Response:
        serializer = AttachEvidenceSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        upload = serializer.validated_data["file"]
        row = services.attach_evidence(
            actor=self.actor(request),
            incident_id=incident_id,
            data=upload.read(),
            content_type=upload.content_type or "application/octet-stream",
            caption=serializer.validated_data.get("caption", ""),
        )
        return Response(
            {"id": str(row.id), "evidence_object_id": str(row.evidence_object_id)},
            status=status.HTTP_201_CREATED,
        )


class IncidentStatementView(OrgApiView):
    action_post = "incident.statement.add"

    def post(self, request: Request, incident_id: str) -> Response:
        serializer = AddStatementSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        statement = services.add_statement(
            actor=self.actor(request),
            incident_id=incident_id,
            text=serializer.validated_data["text"],
        )
        return Response(
            {
                "id": str(statement.id),
                "party_kind": statement.party_kind,
                "text": statement.text,
                "created_at": statement.created_at.isoformat(),
            },
            status=status.HTTP_201_CREATED,
        )


class IncidentReviewView(OrgApiView):
    action_post = "incident.review"

    def post(self, request: Request, incident_id: str) -> Response:
        incident = services.start_review(actor=self.actor(request), incident_id=incident_id)
        return Response(_incident_view(incident))


class IncidentAmicableView(OrgApiView):
    action_post = "incident.review"

    def post(self, request: Request, incident_id: str) -> Response:
        incident = services.start_amicable_window(
            actor=self.actor(request), incident_id=incident_id
        )
        return Response(_incident_view(incident))


class IncidentEscalateView(OrgApiView):
    action_post = "incident.escalate"

    def post(self, request: Request, incident_id: str) -> Response:
        serializer = EscalateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        escalation = services.escalate(
            actor=self.actor(request),
            incident_id=incident_id,
            reason=serializer.validated_data["reason"],
            escalated_to=serializer.validated_data.get("escalated_to", "FOUNDER"),
            advised_external_options=serializer.validated_data.get(
                "advised_external_options", False
            ),
        )
        return Response(
            {
                "id": str(escalation.id),
                "incident_id": str(escalation.incident_id),
                "dispute_id": str(escalation.dispute_id) if escalation.dispute_id else None,
                "escalated_to": escalation.escalated_to,
            },
            status=status.HTTP_201_CREATED,
        )


# ─── Disputes ────────────────────────────────────────────────────────
class DisputeCollectionView(OrgApiView):
    action_get = "incident.read"
    action_post = "dispute.open"

    def get(self, request: Request, job_id: str) -> Response:
        from fikisha.common.exceptions import AuthorizationError
        from fikisha.incidents import authz as incidents_authz
        from fikisha.jobs.selectors import get_job

        job = get_job(job_id)
        if not incidents_authz.is_job_party(self.actor(request), job):
            raise AuthorizationError("You are not a party to this job.", code="authz.forbidden")
        disputes = (
            Dispute.objects.filter(job=job).select_related("resolution").order_by("-created_at")
        )
        return Response({"data": [_dispute_view(d) for d in disputes]})

    def post(self, request: Request, job_id: str) -> Response:
        serializer = OpenDisputeSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        def run() -> Response:
            dispute, view = services.open_dispute(
                actor=self.actor(request),
                job_id=job_id,
                incident_ids=serializer.validated_data["incident_ids"],
            )
            return Response(
                {"dispute": _dispute_view(dispute), "job": view}, status=status.HTTP_201_CREATED
            )

        return idempotent(request, actor_id=str(request.user.id), run=run)


class DisputeDetailView(OrgApiView):
    action_get = "incident.read"

    def resolve_target(self) -> Dispute:
        return get_object_or_404(
            Dispute.objects.select_related("job", "resolution"),
            pk=self.kwargs["dispute_id"],
        )

    def get(self, request: Request, dispute_id: str) -> Response:
        dispute = self.get_authz_resource()
        return Response(_dispute_view(dispute))


class DisputeResolveView(OrgApiView):
    action_post = "dispute.resolve"

    def post(self, request: Request, dispute_id: str) -> Response:
        serializer = ResolveDisputeSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        resolution, view = services.resolve_dispute(
            actor=self.actor(request),
            dispute_id=dispute_id,
            outcome_code=serializer.validated_data["outcome_code"],
            rationale=serializer.validated_data["rationale"],
            routed_job_status=serializer.validated_data["routed_job_status"],
            commission_treatment=serializer.validated_data.get("commission_treatment", "APPLY"),
            reduced_amount_kes=serializer.validated_data.get("reduced_amount_kes"),
            agreed_compensation_kes=serializer.validated_data.get("agreed_compensation_kes"),
            actions=serializer.validated_data.get("actions"),
            idempotency_key=_idempotency_key(request),
        )
        return Response({"resolution_id": str(resolution.id), "job": view})


# ─── Ops console queues (Design Phase 6 Increment 8, P3 §18.1) ─────────
_OPEN_STATUSES = ("OPEN", "UNDER_REVIEW", "AMICABLE_PENDING", "ESCALATED")


def _job_ref(job_id: object) -> str:
    return str(job_id)[-6:].upper()


class _IncidentQueueRow(serializers.BaseSerializer):
    def to_representation(self, incident: Incident) -> dict[str, object]:
        return {
            "id": str(incident.id),
            "job_id": str(incident.job_id),
            "job_reference": _job_ref(incident.job_id),
            "type": incident.type,
            "other_label": incident.other_label,
            "severity": incident.severity,
            "status": incident.status,
            "created_at": incident.created_at.isoformat(),
            "sla_ack_due_at": (
                incident.sla_ack_due_at.isoformat() if incident.sla_ack_due_at else None
            ),
        }


class _DisputeQueueRow(serializers.BaseSerializer):
    def to_representation(self, dispute: Dispute) -> dict[str, object]:
        band = dispute.job.value_band or "STANDARD"
        return {
            "id": str(dispute.id),
            "job_id": str(dispute.job_id),
            "job_reference": _job_ref(dispute.job_id),
            "status": dispute.status,
            "value_band": band,
            # Binding resolution above STANDARD is Platform-Admin-only (D-ADM-1).
            "needs_platform_admin": band != "STANDARD",
            "created_at": dispute.created_at.isoformat(),
        }


class OpsIncidentQueueView(OrgApiView):
    action_get = "incident.queue.view"

    def get(self, request: Request) -> Response:
        qs = Incident.objects.filter(status__in=_OPEN_STATUSES)
        return paginated(request, qs, _IncidentQueueRow)


class OpsDisputeQueueView(OrgApiView):
    action_get = "incident.queue.view"

    def get(self, request: Request) -> Response:
        qs = Dispute.objects.filter(status__in=_OPEN_STATUSES).select_related("job")
        return paginated(request, qs, _DisputeQueueRow)
