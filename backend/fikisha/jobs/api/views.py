"""Jobs API (Phase 2D Step 10) — a thin HTTP adapter over the existing
``jobs`` domain services. No lifecycle/negotiation/assignment/proof rule is
implemented here; every state-changing view calls the domain function that
was already the authoritative entry point in Increments 1-9 (brief §1)."""

from __future__ import annotations

from typing import Any

from rest_framework import serializers, status
from rest_framework.exceptions import ValidationError
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.permissions import AllowAny
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from fikisha.common import if_match
from fikisha.common.api import OrgApiView, paginated
from fikisha.common.exceptions import ConflictError
from fikisha.common.idempotency import idempotent
from fikisha.common.ratelimit import RateLimiter
from fikisha.evidence import services as evidence_services
from fikisha.evidence.models import EvidencePurpose, PiiClass, UploaderKind
from fikisha.identity.authz.step_up import require_step_up
from fikisha.jobs import assignment_candidates as assignment_candidates_service
from fikisha.jobs import cargo_categories, creation, custody, discovery, high_value, job_authz, ops
from fikisha.jobs import commission as commission_service
from fikisha.jobs import recipient as recipient_service
from fikisha.jobs.api.serializers import (
    AddNoteSerializer,
    ArriveSerializer,
    AssignSerializer,
    CancelJobSerializer,
    CloseJobSerializer,
    ConfirmDeliverySerializer,
    ConfirmPickupSerializer,
    FailAtPickupSerializer,
    HighValueDecisionSerializer,
    JobCreateSerializer,
    RecipientConfirmSerializer,
    RecipientReportIssueSerializer,
    SenderConfirmPickupSerializer,
)
from fikisha.jobs.assignment import assign_job
from fikisha.jobs.constants import JobStatus
from fikisha.jobs.errors import CommissionRecordNotFound
from fikisha.jobs.high_value import decide_high_value
from fikisha.jobs.models import CommissionAdjustment, CommissionRecord, Job
from fikisha.jobs.selectors import get_job


def _idempotency_key(request: Request) -> str:
    return request.META.get("HTTP_IDEMPOTENCY_KEY", "").strip()


def _uploader_kind(actor: Any, job: Job) -> str:
    if job_authz.is_admin(actor):
        return UploaderKind.ADMIN
    if job_authz.operator_is_party(actor, job):
        return UploaderKind.OPERATOR
    return UploaderKind.BUSINESS


def _store_photos(request: Request, actor: Any, job: Job) -> list[str]:
    files = request.FILES.getlist("photos")
    ids: list[str] = []
    for upload in files:
        obj = evidence_services.store(
            data=upload.read(),
            content_type=upload.content_type or "application/octet-stream",
            purpose=EvidencePurpose.CUSTODY_PROOF,
            pii_class=PiiClass.MEDIUM,
            linked_entity_type="job",
            linked_entity_id=job.id,
            uploaded_by=getattr(actor, "user", None),
            uploaded_by_kind=_uploader_kind(actor, job),
        )
        ids.append(str(obj.id))
    return ids


def _store_single(request: Request, field: str, actor: Any, job: Job) -> str | None:
    upload = request.FILES.get(field)
    if upload is None:
        return None
    obj = evidence_services.store(
        data=upload.read(),
        content_type=upload.content_type or "application/octet-stream",
        purpose=EvidencePurpose.CUSTODY_PROOF,
        pii_class=PiiClass.MEDIUM,
        linked_entity_type="job",
        linked_entity_id=job.id,
        uploaded_by=getattr(actor, "user", None),
        uploaded_by_kind=_uploader_kind(actor, job),
    )
    return str(obj.id)


# ─── Job collection / detail ───────────────────────────────────────────
class JobCollectionView(OrgApiView):
    action_get = "job.read"
    action_post = "job.create"

    def get(self, request: Request) -> Response:
        """``GET /jobs?status=A,B&assigned=me``. Both filters only narrow what
        the actor may already see: ``status`` to those states, ``assigned=me``
        to jobs whose assigned driver is the caller's own operator profile
        (the driver's "Current job", PR #5 follow-up 2)."""
        actor = self.actor(request)
        qs = (
            job_authz.jobs_visible_to(actor)
            .select_related("business", "agreement", "assignment")
            .order_by("-created_at")
        )
        statuses = [s for s in (request.query_params.get("status") or "").split(",") if s]
        if statuses:
            unknown = sorted(set(statuses) - set(JobStatus.values))
            if unknown:
                raise ValidationError({"status": [f"Unknown status: {', '.join(unknown)}."]})
            qs = qs.filter(status__in=statuses)
        assigned = request.query_params.get("assigned")
        if assigned is not None:
            if assigned != "me":
                raise ValidationError({"assigned": ["Only 'me' is supported."]})
            from fikisha.operators import services as operators_services

            profile = operators_services.profile_for(self.user(request))
            qs = (
                qs.filter(assignment__assigned_driver_profile_id=profile.id)
                if profile
                else qs.none()
            )
        return paginated(request, qs, _JobListSerializer, context={"viewer": actor})

    def post(self, request: Request) -> Response:
        serializer = JobCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        business_id = request.data.get("business_id")
        if not business_id:
            raise ConflictError("business_id is required.", code="business_id_required")

        def run() -> Response:
            job = creation.create_draft(
                actor=self.actor(request),
                business_id=business_id,
                data=serializer.validated_data,
            )
            return Response(creation.job_detail(job), status=status.HTTP_201_CREATED)

        return idempotent(request, actor_id=str(request.user.id), run=run)


class JobDetailView(OrgApiView):
    action_get = "job.read"

    def resolve_target(self) -> Job:
        return get_job(self.kwargs["job_id"])

    def get(self, request: Request, job_id: str) -> Response:
        job = self.get_authz_resource()
        # ETag = the version a client sends back as If-Match (ADR-2D-44)
        return Response(
            creation.job_detail(job, viewer=self.actor(request)),
            headers={"ETag": if_match.etag(job.version)},
        )


class JobSubmitView(OrgApiView):
    action_post = "job.transition"

    def post(self, request: Request, job_id: str) -> Response:
        view = creation.submit_job(
            actor=self.actor(request), job_id=job_id, idempotency_key=_idempotency_key(request)
        )
        return Response(view)


class JobCancelView(OrgApiView):
    action_post = "job.transition"

    def post(self, request: Request, job_id: str) -> Response:
        serializer = CancelJobSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        view = creation.cancel_job(
            actor=self.actor(request),
            job_id=job_id,
            reason_code=serializer.validated_data["reason_code"],
            reason_text=serializer.validated_data.get("reason_text", ""),
            idempotency_key=_idempotency_key(request),
        )
        return Response(view)


# ─── Operations Officer console (Design Phase 6 Increment 8, P3 §18) ────
def _int_param(request: Request, name: str) -> int | None:
    raw = request.query_params.get(name)
    if raw in (None, ""):
        return None
    try:
        return int(str(raw))
    except (TypeError, ValueError) as exc:
        raise ops.InvalidFilter(f"{name} must be a whole number.") from exc


def _paginate_rows(request: Request, qs: Any, render: Any) -> Response:
    """Cursor-paginate ``qs`` and render the page in one bulk call (the row
    renderers resolve business/operator names for the whole page at once)."""
    from fikisha.common.pagination import CursorPagination

    paginator = CursorPagination()
    page = paginator.paginate_queryset(qs, request) or []
    return paginator.get_paginated_response(render(list(page)))


class OpsJobMonitorView(OrgApiView):
    action_get = "job.monitor.view"

    def get(self, request: Request) -> Response:
        params = request.query_params
        statuses = [s for s in (params.get("status") or "").split(",") if s]
        qs = ops.monitored_jobs(
            statuses=statuses or None,
            value_band=params.get("value_band") or None,
            ref=params.get("ref") or None,
            attention=params.get("attention") or None,
            stale_hours=_int_param(request, "stale_hours"),
        )
        return _paginate_rows(request, qs, ops.ops_rows)


class OpsHighValueQueueView(OrgApiView):
    action_get = "job.monitor.view"

    def get(self, request: Request) -> Response:
        qs = ops.high_value_pending().select_related(
            "pickup_location", "destination_location", "agreement"
        )
        return _paginate_rows(request, qs, ops.high_value_rows)


class JobHighValueReversalView(OrgApiView):
    """``POST /jobs/<id>/high-value-decision/reverse {reason}`` — a Platform
    Admin reverses a rejection (founder decision 2026-10-14). Needs a fresh
    step-up."""

    action_post = "highvalue.approve"

    def post(self, request: Request, job_id: str) -> Response:
        reason = str(request.data.get("reason") or "")
        require_step_up(self.actor(request))
        return Response(
            high_value.reverse_rejection(actor=self.actor(request), job_id=job_id, reason=reason),
            status=status.HTTP_201_CREATED,
        )


class JobHighValueDecisionView(OrgApiView):
    action_post = "highvalue.approve"

    def post(self, request: Request, job_id: str) -> Response:
        serializer = HighValueDecisionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        # high-value approval needs a fresh MFA step-up (Phase 1 §1.2, ADR-2D-39)
        require_step_up(self.actor(request))
        view = decide_high_value(
            actor=self.actor(request),
            job_id=job_id,
            decision=serializer.validated_data["decision"],
            rationale=serializer.validated_data["rationale"],
        )
        return Response(view, status=status.HTTP_201_CREATED)


class JobNotesView(OrgApiView):
    """GET: any party to the job (founder decision 2026-09-23 — notes are
    visible to the job's parties). POST: staff with ``job.intervene``."""

    action_get = "job.read"
    action_post = "job.intervene"

    def resolve_target(self) -> Job:
        return get_job(self.kwargs["job_id"])

    def get(self, request: Request, job_id: str) -> Response:
        job = self.get_authz_resource()
        staff = job_authz.is_admin(self.actor(request))
        return Response({"data": ops.notes_for(job, staff=staff)})

    def post(self, request: Request, job_id: str) -> Response:
        serializer = AddNoteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        view = ops.add_note(
            actor=self.actor(request), job_id=job_id, text=serializer.validated_data["text"]
        )
        return Response(view, status=status.HTTP_201_CREATED)


class JobEventsView(OrgApiView):
    action_get = "job.monitor.view"

    def get(self, request: Request, job_id: str) -> Response:
        return Response({"data": ops.events_for(get_job(job_id))})


class JobContactsRevealView(OrgApiView):
    action_post = "job.intervene"

    def post(self, request: Request, job_id: str) -> Response:
        return Response(ops.reveal_contacts(actor=self.actor(request), job_id=job_id))


# ─── Work discovery (Design Phase 6 Increment 4, individual-operator-only —
# see jobs.assignment_candidates module docstring) ──────────────────────
class JobOpportunitiesView(OrgApiView):
    action_get = "job.discover"

    def get(self, request: Request) -> Response:
        actor = self.actor(request)
        value_band = request.query_params.get("value_band") or None
        qs = discovery.open_jobs_for(actor, value_band=value_band)
        return paginated(request, qs, _JobOpportunitySerializer, context={"discovery_actor": actor})


class JobOpportunityDetailView(OrgApiView):
    action_get = "job.discover"

    def get(self, request: Request, job_id: str) -> Response:
        return Response(discovery.opportunity_detail(self.actor(request), job_id))


# ─── Cargo categories (assessment 2026-10-19 D-5) ───────────────────────
class CargoCategoriesView(OrgApiView):
    """``GET /jobs/cargo-categories`` — the configured categories, each with
    whether it is latent-risk (longer dispute window)."""

    action_get = "job.cargo_categories.read"

    def get(self, request: Request) -> Response:
        return Response({"data": cargo_categories.catalogue()})


class CargoCategorySuggestView(OrgApiView):
    """``GET /jobs/cargo-categories/suggest?description=`` — the category the
    description's keywords point to, or ``null``."""

    action_get = "job.cargo_categories.read"

    def get(self, request: Request) -> Response:
        description = (request.query_params.get("description") or "")[:4000]
        return Response({"code": cargo_categories.suggest(description)})


# ─── Assignment ─────────────────────────────────────────────────────────
class JobAssignmentCandidatesView(OrgApiView):
    action_get = "job.assign.candidates"

    def get(self, request: Request, job_id: str) -> Response:
        view = assignment_candidates_service.candidates(actor=self.actor(request), job_id=job_id)
        return Response(view)


class JobAssignView(OrgApiView):
    action_post = "job.assign"

    def post(self, request: Request, job_id: str) -> Response:
        serializer = AssignSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        view = assign_job(
            actor=self.actor(request),
            job_id=job_id,
            driver_profile_id=serializer.validated_data["driver_profile_id"],
            vehicle_id=serializer.validated_data["vehicle_id"],
            admin_override_reason=serializer.validated_data.get("admin_override_reason", ""),
            idempotency_key=_idempotency_key(request),
        )
        return Response(view)


# ─── Custody ─────────────────────────────────────────────────────────────
class ArriveAtPickupView(OrgApiView):
    action_post = "job.proof.pickup"

    def post(self, request: Request, job_id: str) -> Response:
        serializer = ArriveSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        view = custody.arrive_at_pickup(
            actor=self.actor(request),
            job_id=job_id,
            geo=serializer.validated_data.get("geo"),
            idempotency_key=_idempotency_key(request),
        )
        return Response(view)


class StartTransitView(OrgApiView):
    action_post = "job.transition"

    def post(self, request: Request, job_id: str) -> Response:
        view = custody.start_transit(
            actor=self.actor(request), job_id=job_id, idempotency_key=_idempotency_key(request)
        )
        return Response(view)


class ArriveAtDestinationView(OrgApiView):
    action_post = "job.proof.delivery"

    def post(self, request: Request, job_id: str) -> Response:
        serializer = ArriveSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        view = custody.arrive_at_destination(
            actor=self.actor(request),
            job_id=job_id,
            geo=serializer.validated_data.get("geo"),
            idempotency_key=_idempotency_key(request),
        )
        return Response(view)


class FailAtPickupView(OrgApiView):
    action_post = "job.transition"

    def post(self, request: Request, job_id: str) -> Response:
        serializer = FailAtPickupSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        view = custody.fail_at_pickup(
            actor=self.actor(request),
            job_id=job_id,
            reason_text=serializer.validated_data["reason_text"],
            idempotency_key=_idempotency_key(request),
        )
        return Response(view)


class ConfirmPickupView(OrgApiView):
    """``POST /jobs/<id>/custody/confirm-pickup`` (also the older
    ``.../confirm-pickup/otp``): the driver completes pickup. Multipart:
    ``code``, ``party_name``, ``signature`` file, ``photos`` files."""

    action_post = "job.proof.pickup"
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    def post(self, request: Request, job_id: str) -> Response:
        serializer = ConfirmPickupSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        job = get_job(job_id)
        actor = self.actor(request)
        photo_ids = _store_photos(request, actor, job)
        signature_id = _store_single(request, "signature", actor, job)
        view = custody.confirm_pickup(
            actor=actor,
            job_id=job_id,
            code=serializer.validated_data.get("code") or None,
            signature_evidence_id=signature_id,
            photo_evidence_ids=photo_ids,
            party_name=serializer.validated_data.get("party_name", ""),
            condition_note=serializer.validated_data.get("condition_note", ""),
            idempotency_key=_idempotency_key(request),
        )
        return Response(view)


class SenderConfirmPickupView(OrgApiView):
    """``POST /jobs/<id>/custody/confirm-pickup/business``: the sender
    confirms the handover in their own app. Recorded; the driver's call then
    completes pickup (assessment 2026-10-20 L-5)."""

    action_post = "job.proof.pickup"

    def post(self, request: Request, job_id: str) -> Response:
        serializer = SenderConfirmPickupSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        view = custody.sender_confirm_pickup(
            actor=self.actor(request),
            job_id=job_id,
            party_name=serializer.validated_data.get("party_name", ""),
        )
        return Response(view)


class CloseJobView(OrgApiView):
    """``POST /jobs/<id>/close``: the sender confirms the goods arrived and
    that they paid the operator; the job completes (PD-3 / PD-4)."""

    action_post = "job.transition"

    def post(self, request: Request, job_id: str) -> Response:
        serializer = CloseJobSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        view = custody.sender_close_job(
            actor=self.actor(request),
            job_id=job_id,
            method=serializer.validated_data["payment_method"],
            mpesa_reference=serializer.validated_data.get("mpesa_reference", ""),
            idempotency_key=_idempotency_key(request),
        )
        return Response(view)


class ConfirmPickupAttestedView(OrgApiView):
    """Retired (LD-4): ``410 pickup_fallback_retired``."""

    action_post = "job.proof.pickup"

    def post(self, request: Request, job_id: str) -> Response:
        custody.confirm_pickup_attested()
        raise AssertionError("unreachable")  # pragma: no cover


class ConfirmDeliveryView(OrgApiView):
    action_post = "job.proof.delivery"
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    def post(self, request: Request, job_id: str) -> Response:
        serializer = ConfirmDeliverySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        job = get_job(job_id)
        actor = self.actor(request)
        photo_ids = _store_photos(request, actor, job)
        signature_id = _store_single(request, "signature", actor, job)
        view = custody.confirm_delivery(
            actor=actor,
            job_id=job_id,
            party_name=serializer.validated_data["party_name"],
            code=serializer.validated_data.get("code") or None,
            signature_evidence_id=signature_id,
            photo_evidence_ids=photo_ids,
            condition_note=serializer.validated_data.get("condition_note", ""),
            geo=serializer.validated_data.get("geo"),
            idempotency_key=_idempotency_key(request),
        )
        return Response(view)


# ─── Recipient scoped API (bearer token in the URL, not a session) ─────
# No ActionPermission / BearerSessionAuthentication here — a recipient link
# is not a User (Increment 5 ADR-2D-06). Every view resolves the token
# itself and authenticates the scoped RecipientPrincipal by hand, exactly as
# ``fikisha.jobs.recipient`` was designed to be called.
_recipient_ip_limiter = RateLimiter(scope="recipient.token", limit=20, window_seconds=300)


def _client_ip(request: Request) -> str | None:
    xff = request.META.get("HTTP_X_FORWARDED_FOR")
    if xff:
        return xff.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR")


def _resolve_recipient(request: Request, token: str) -> Any:
    """IP-rate-limited token resolution — brief §11: a brute-force boundary
    around token resolution, shared by every recipient-facing view (the
    view, the confirm action, and the report-issue action all resolve the
    token first). ``resolve_recipient`` itself already returns an identical
    404 for "never existed" and "wrong" tokens (Increment 5) — this adds
    the IP throttle, nothing about response shape."""
    ip = _client_ip(request) or "unknown"
    _recipient_ip_limiter.check(ip)
    return recipient_service.resolve_recipient(token)


class RecipientDetailView(APIView):
    permission_classes = [AllowAny]
    authentication_classes: list[type] = []

    def get(self, request: Request, token: str) -> Response:
        principal = _resolve_recipient(request, token)
        return Response(recipient_service.view(principal=principal))


class RecipientConfirmView(APIView):
    permission_classes = [AllowAny]
    authentication_classes: list[type] = []
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    def post(self, request: Request, token: str) -> Response:
        principal = _resolve_recipient(request, token)
        serializer = RecipientConfirmSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        # No Job row is resolvable pre-authentication here without trusting a
        # client-supplied id — evidence is linked by the *link*, the scope
        # itself, not a caller-asserted job id.
        signature_id = None
        photo_ids: list[str] = []
        upload = request.FILES.get("signature")
        if upload is not None:
            obj = evidence_services.store(
                data=upload.read(),
                content_type=upload.content_type or "application/octet-stream",
                purpose=EvidencePurpose.CUSTODY_PROOF,
                pii_class=PiiClass.MEDIUM,
                linked_entity_type="job",
                linked_entity_id=principal.job_id,
                uploaded_by_kind=UploaderKind.RECIPIENT,
            )
            signature_id = str(obj.id)
        for upload in request.FILES.getlist("photos"):
            obj = evidence_services.store(
                data=upload.read(),
                content_type=upload.content_type or "application/octet-stream",
                purpose=EvidencePurpose.CUSTODY_PROOF,
                pii_class=PiiClass.MEDIUM,
                linked_entity_type="job",
                linked_entity_id=principal.job_id,
                uploaded_by_kind=UploaderKind.RECIPIENT,
            )
            photo_ids.append(str(obj.id))
        view = recipient_service.confirm_receipt(
            principal=principal,
            code=serializer.validated_data["code"],
            party_name=serializer.validated_data["party_name"],
            signature_evidence_id=signature_id,
            photo_evidence_ids=photo_ids,
            idempotency_key=_idempotency_key(request),
        )
        return Response(view)


class RecipientReportIssueView(APIView):
    permission_classes = [AllowAny]
    authentication_classes: list[type] = []
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    def post(self, request: Request, token: str) -> Response:
        principal = _resolve_recipient(request, token)
        serializer = RecipientReportIssueSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        # Same evidence-linked-by-link pattern as RecipientConfirmView — no
        # Job row is resolvable pre-authentication without trusting a
        # client-supplied id, so photos are linked via principal.job_id.
        photo_ids: list[str] = []
        for upload in request.FILES.getlist("photos"):
            obj = evidence_services.store(
                data=upload.read(),
                content_type=upload.content_type or "application/octet-stream",
                purpose=EvidencePurpose.INCIDENT_EVIDENCE,
                pii_class=PiiClass.MEDIUM,
                linked_entity_type="job",
                linked_entity_id=principal.job_id,
                uploaded_by_kind=UploaderKind.RECIPIENT,
            )
            photo_ids.append(str(obj.id))
        result = recipient_service.report_issue(
            principal=principal,
            category=serializer.validated_data["category"],
            description=serializer.validated_data.get("description", ""),
            other_label=serializer.validated_data.get("other_label", ""),
            photo_evidence_ids=photo_ids,
        )
        return Response(result, status=status.HTTP_201_CREATED)


# ─── Commission (read-only; Platform-Admin-only, ADR-2D — Step 10) ──────
class JobCommissionView(OrgApiView):
    action_get = "commission.read"

    def resolve_target(self) -> Job:
        return get_job(self.kwargs["job_id"])

    def get(self, request: Request, job_id: str) -> Response:
        job = self.get_authz_resource()
        record = CommissionRecord.objects.filter(job=job).first()
        if record is None:
            raise CommissionRecordNotFound()
        adjustments = CommissionAdjustment.objects.filter(commission_record=record).order_by(
            "created_at"
        )
        return Response(
            {
                "job_id": str(job.id),
                "commission_kes": record.commission_kes,
                "rate": str(record.rate),
                "min_fee_kes": record.min_fee_kes,
                "cap_kes": record.cap_kes,
                "agreed_price_kes": record.agreed_price_kes,
                "currency": record.currency,
                "effective_commission_kes": commission_service.effective_commission_kes(record),
                "adjustments": [
                    {
                        "id": str(a.id),
                        "kind": a.kind,
                        "amount_kes": a.amount_kes,
                        "reason": a.reason,
                        "created_at": a.created_at.isoformat(),
                    }
                    for a in adjustments
                ],
            }
        )


class _JobListSerializer(serializers.BaseSerializer):
    """Keeps the list endpoint on the exact same ``job_detail()`` projection
    the detail endpoint uses (no second representation to keep in sync)."""

    def to_representation(self, instance: Job) -> dict[str, Any]:
        return creation.job_detail(instance, viewer=self.context.get("viewer"))


class _JobOpportunitySerializer(serializers.BaseSerializer):
    def to_representation(self, instance: Job) -> dict[str, Any]:
        return discovery.opportunity_view(instance, self.context["discovery_actor"])
