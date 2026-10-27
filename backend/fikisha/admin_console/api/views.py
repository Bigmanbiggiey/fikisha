"""Platform Admin console API (Design Phase 6 Increment 9, P3 §19,
ADR-2D-38) — a thin adapter over ``fikisha.admin_console.services``. Every
endpoint is a config-driven Platform Admin permission (``policies.py``);
interventions and config changes additionally need a step-up (refused with
``step_up_required`` until admin MFA exists)."""

from __future__ import annotations

import uuid
from typing import Any

from django.utils.dateparse import parse_datetime
from rest_framework import serializers
from rest_framework.exceptions import NotFound
from rest_framework.request import Request
from rest_framework.response import Response

from fikisha.admin_console import services
from fikisha.admin_console.models import AccountType
from fikisha.common.api import OrgApiView
from fikisha.common.exceptions import DomainError
from fikisha.common.pagination import CursorPagination
from fikisha.jobs import admin_ledger
from fikisha.jobs import ops as jobs_ops

_KIND_TO_ACCOUNT = {
    "businesses": AccountType.BUSINESS,
    "operators": AccountType.OPERATOR,
    "groups": AccountType.GROUP,
}
_KIND_TO_JOBS_KEY = {"businesses": "business_id", "operators": "operator_id", "groups": "group_id"}


class InvalidAdminFilter(DomainError):
    default_code = "invalid_filter"


def _directory(kind: str) -> Any:
    directory = services.DIRECTORIES.get(kind)
    if directory is None:
        raise NotFound("No such directory.")
    return directory


class _MaskedRow(serializers.BaseSerializer):
    def to_representation(self, instance: Any) -> dict[str, Any]:
        return services.masked(self.context["directory"].row(instance))


class DirectoryListView(OrgApiView):
    """``GET /admin/directory/<kind>?q=&state=`` — newest first, phones
    masked."""

    action_get = "admin.directory.read"

    def get(self, request: Request, kind: str) -> Response:
        directory = _directory(kind)
        q = (request.query_params.get("q") or "").strip()[:80]
        state = (request.query_params.get("state") or "").strip().upper()
        states = getattr(directory, "STANDINGS", None) or directory.STATUSES
        if state and state not in states:
            raise InvalidAdminFilter(f"state must be one of {', '.join(states)}.")
        if kind == "operators":
            qs = directory.queryset(q=q, status=state)
        else:
            qs = directory.queryset(q=q, standing=state)
        paginator = CursorPagination()
        page = paginator.paginate_queryset(qs, request)
        data = _MaskedRow(page, many=True, context={"directory": directory}).data
        return paginator.get_paginated_response(data)


class DirectoryDetailView(OrgApiView):
    """``GET /admin/directory/<kind>/<id>`` — the account, its members, its
    in-flight jobs and its intervention history (and its user's, for an
    operator or a business owner)."""

    action_get = "admin.directory.read"

    def get(self, request: Request, kind: str, account_id: uuid.UUID) -> Response:
        directory = _directory(kind)
        data = services.masked(directory.detail(account_id))
        data["in_flight_jobs"] = jobs_ops.in_flight_jobs_for(
            **{_KIND_TO_JOBS_KEY[kind]: account_id}
        )
        data["interventions"] = services.interventions_for(_KIND_TO_ACCOUNT[kind], account_id)
        user_id = data.get("user_id") or data.get("owner_user_id")
        data["user_interventions"] = (
            services.interventions_for(AccountType.USER, user_id) if user_id else []
        )
        return Response(data)


class BusinessRecordView(OrgApiView):
    """``GET /admin/directory/businesses/<id>/record`` — the business's track
    record for staff (trust-and-disputes plan A8): open reports, closed
    incidents and how, current findings against it (superseded ones in
    history), reports found unfounded, its rating from operators and its
    cancellation flags. Staff only; nothing here changes standing."""

    action_get = "admin.directory.read"

    def get(self, request: Request, account_id: uuid.UUID) -> Response:
        from fikisha.incidents.business_record import business_record
        from fikisha.jobs import cancellation_flags
        from fikisha.ratings import services as ratings

        _directory("businesses").detail(account_id)  # 404 for an unknown business
        avg = ratings.average("BUSINESS", account_id)
        return Response(
            {
                **business_record(account_id),
                "rating": {"average": avg["average"], "count": avg["count"]},
                "cancellation_flags": cancellation_flags.flags_for_business(account_id),
            }
        )


class DirectoryContactView(OrgApiView):
    """``POST /admin/directory/<kind>/<id>/contact`` — the full phone,
    audited."""

    action_post = "admin.directory.contact_reveal"

    def post(self, request: Request, kind: str, account_id: uuid.UUID) -> Response:
        _directory(kind)
        return Response(
            services.reveal_contact(
                actor=self.actor(request),
                account_type=_KIND_TO_ACCOUNT[kind],
                account_id=account_id,
            )
        )


class _InterventionSerializer(serializers.Serializer):
    account_type = serializers.ChoiceField(choices=AccountType.values)
    account_id = serializers.UUIDField()
    action = serializers.CharField(max_length=12)
    reason = serializers.CharField(max_length=2000, allow_blank=True)
    duration_days = serializers.IntegerField(required=False, allow_null=True)


class InterventionsView(OrgApiView):
    """``POST /admin/interventions`` — suspend / reinstate / offboard."""

    action_post = "admin.account.intervene"

    def post(self, request: Request) -> Response:
        s = _InterventionSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        v = s.validated_data
        result = services.intervene(
            actor=self.actor(request),
            account_type=v["account_type"],
            account_id=v["account_id"],
            action=v["action"],
            reason=v["reason"],
            duration_days=v.get("duration_days"),
        )
        return Response(result, status=201)


class _ApproveOperatorSerializer(serializers.Serializer):
    note = serializers.CharField(max_length=2000, allow_blank=True, required=False)


class ApproveOperatorView(OrgApiView):
    """``POST /admin/operators/<id>/approve`` — a verification reviewer
    approves a new operator, ``PENDING → ACTIVE`` (assessment 2026-10-19 D-2)."""

    action_post = "verification.decide"

    def post(self, request: Request, operator_id: uuid.UUID) -> Response:
        s = _ApproveOperatorSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        result = services.approve_operator(
            actor=self.actor(request),
            operator_id=operator_id,
            note=s.validated_data.get("note", ""),
        )
        return Response(result, status=201)


class CargoUncategorisedView(OrgApiView):
    """``GET /admin/cargo-categories/uncategorised`` (assessment 2026-10-19 D-5)."""

    action_get = "admin.config.read"

    def get(self, request: Request) -> Response:
        return Response({"data": services.uncategorised_cargo(actor=self.actor(request))})


class _CargoKeywordSerializer(serializers.Serializer):
    category_code = serializers.CharField(max_length=40)
    keyword = serializers.CharField(max_length=60)
    rationale = serializers.CharField(max_length=2000, allow_blank=True, required=False)


class CargoKeywordView(OrgApiView):
    """``POST /admin/cargo-categories/keywords`` — add a keyword (step-up)."""

    action_post = "admin.config.change"

    def post(self, request: Request) -> Response:
        s = _CargoKeywordSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        v = s.validated_data
        result = services.add_cargo_keyword(
            actor=self.actor(request),
            category_code=v["category_code"],
            keyword=v["keyword"],
            rationale=v.get("rationale", ""),
        )
        return Response(result, status=201)


class _CargoCategorySerializer(serializers.Serializer):
    code = serializers.CharField(max_length=40)
    keywords = serializers.ListField(child=serializers.CharField(max_length=60), required=False)
    rationale = serializers.CharField(max_length=2000, allow_blank=True, required=False)


class CargoCategoryView(OrgApiView):
    """``POST /admin/cargo-categories`` — add a category (step-up)."""

    action_post = "admin.config.change"

    def post(self, request: Request) -> Response:
        s = _CargoCategorySerializer(data=request.data)
        s.is_valid(raise_exception=True)
        v = s.validated_data
        result = services.add_cargo_category(
            actor=self.actor(request),
            code=v["code"],
            keywords=v.get("keywords", []),
            rationale=v.get("rationale", ""),
        )
        return Response(result, status=201)


class _ConfigChangeSerializer(serializers.Serializer):
    changes = serializers.DictField()
    rationale = serializers.CharField(max_length=2000, allow_blank=True, required=False)


class ConfigView(OrgApiView):
    """``GET /admin/config`` (live config, version, history, editable keys)
    and ``POST /admin/config {changes, rationale}`` (apply; step-up)."""

    action_get = "admin.config.read"
    action_post = "admin.config.change"

    def get(self, request: Request) -> Response:
        return Response(services.config_view(actor=self.actor(request)))

    def post(self, request: Request) -> Response:
        s = _ConfigChangeSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        result = services.apply_config_change(
            actor=self.actor(request),
            changes=s.validated_data["changes"],
            rationale=s.validated_data.get("rationale", ""),
        )
        return Response(result, status=201)


class ConfigPreviewView(OrgApiView):
    """``POST /admin/config/preview {changes}`` — the diff and its effect;
    changes nothing."""

    action_post = "admin.config.read"

    def post(self, request: Request) -> Response:
        s = _ConfigChangeSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        return Response(
            services.preview_config_change(
                actor=self.actor(request), changes=s.validated_data["changes"]
            )
        )


class _LedgerRow(serializers.BaseSerializer):
    def to_representation(self, instance: Any) -> dict[str, Any]:
        return admin_ledger.row(instance)


def _uuid_param(request: Request, name: str) -> uuid.UUID | None:
    raw = request.query_params.get(name)
    if not raw:
        return None
    try:
        return uuid.UUID(raw)
    except ValueError as exc:
        raise InvalidAdminFilter(f"{name} must be a UUID.") from exc


def _time_param(request: Request, name: str) -> Any:
    raw = request.query_params.get(name)
    if not raw:
        return None
    parsed = parse_datetime(raw)
    if parsed is None:
        raise InvalidAdminFilter(f"{name} must be an ISO-8601 date-time.")
    return parsed


class CommissionLedgerView(OrgApiView):
    """``GET /admin/commission?since=&until=&operator_id=&group_id=&business_id=&party=`` —
    ``{data, page, totals, statements_available}``. ``totals`` covers the
    whole filtered ledger. Weekly statements exist since Commission & Statements
    S-1 (`GET /admin/statements`, ADR-2D-42)."""

    action_get = "admin.commission.read"

    def get(self, request: Request) -> Response:
        qs = admin_ledger.queryset(
            since=_time_param(request, "since"),
            until=_time_param(request, "until"),
            operator_id=_uuid_param(request, "operator_id"),
            group_id=_uuid_param(request, "group_id"),
            business_id=_uuid_param(request, "business_id"),
            party=request.query_params.get("party") or None,
        )
        paginator = CursorPagination()
        page = paginator.paginate_queryset(qs, request)
        response = paginator.get_paginated_response(_LedgerRow(page, many=True).data)
        response.data["totals"] = admin_ledger.totals(qs)
        response.data["statements_available"] = True
        return response
