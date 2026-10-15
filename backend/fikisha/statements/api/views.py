"""Commission statements API (plan S-1, ADR-2D-42): a thin adapter over
``fikisha.statements.services``.

Payee: ``GET /statements``, ``GET /statements/<id>``,
``GET /jobs/<id>/earnings``.
Staff: ``GET /admin/statements``, ``POST /admin/statements/run``,
``POST /admin/statements/<id>/payments``,
``POST /admin/statements/<id>/payments/<payment_id>/reverse``.
"""

from __future__ import annotations

import uuid
from typing import Any

from django.utils.dateparse import parse_date
from rest_framework import serializers
from rest_framework.exceptions import NotFound
from rest_framework.request import Request
from rest_framework.response import Response

from fikisha.common.api import OrgApiView
from fikisha.common.pagination import CursorPagination
from fikisha.statements import services
from fikisha.statements.models import CommissionStatement, PayeeKind, SettlementMethod


class _SummaryRow(serializers.BaseSerializer):
    def to_representation(self, instance: Any) -> dict[str, Any]:
        return services.statement_summary(instance)


class _StatementPagination(CursorPagination):
    ordering = ("-period_start", "-created_at")  # type: ignore[assignment]  # DRF accepts a tuple


class MyStatementsView(OrgApiView):
    """``GET /statements`` — the caller's own statements as a payee. Each row
    says whether they have opened it (``seen``); ``unseen_count`` drives the
    Home "New statement" card (D-6)."""

    action_get = "statements.read.own"

    def get(self, request: Request) -> Response:
        actor = self.actor(request)
        paginator = _StatementPagination()
        page = paginator.paginate_queryset(services.statements_for(actor), request) or []
        seen = services.seen_statement_ids(actor=actor, statement_ids=[s.id for s in page])
        rows = _SummaryRow(page, many=True).data
        for row in rows:
            row["seen"] = row["id"] in seen
        response = paginator.get_paginated_response(rows)
        response.data["unseen_count"] = services.unseen_count(actor)
        return response


class StatementSeenView(OrgApiView):
    """``POST /statements/<id>/seen`` — the payee opened it. 204; staff
    opening a statement records nothing."""

    action_post = "statements.read.one"

    def resolve_target(self) -> CommissionStatement:
        statement = CommissionStatement.objects.filter(id=self.kwargs["statement_id"]).first()
        if statement is None:
            raise NotFound("No such statement.")
        return statement

    def post(self, request: Request, statement_id: uuid.UUID) -> Response:
        services.mark_seen(actor=self.actor(request), statement=self.resolve_target())
        return Response(status=204)


class StatementDetailView(OrgApiView):
    """``GET /statements/<id>`` — lines, payments and where to pay."""

    action_get = "statements.read.one"

    def resolve_target(self) -> CommissionStatement:
        statement = CommissionStatement.objects.filter(id=self.kwargs["statement_id"]).first()
        if statement is None:
            raise NotFound("No such statement.")
        return statement

    def get(self, request: Request, statement_id: uuid.UUID) -> Response:
        return Response(services.statement_detail(self.resolve_target()))


class JobEarningsView(OrgApiView):
    """``GET /jobs/<id>/earnings`` — "Earnings for this Job" (P3 §7.4)."""

    action_get = "statements.job_earnings"

    def get(self, request: Request, job_id: uuid.UUID) -> Response:
        return Response(services.job_earnings(actor=self.actor(request), job_id=job_id))


def _date_param(request: Request, name: str) -> Any:
    raw = (request.query_params.get(name) or "").strip()
    if not raw:
        return None
    value = parse_date(raw)
    if value is None:
        raise services.InvalidPeriod(f"{name} must be a date (YYYY-MM-DD).")
    return value


class AdminStatementsView(OrgApiView):
    """``GET /admin/statements?period_start=&payee_kind=&payee_id=`` — every
    statement, newest first, with invoiced-vs-settled totals for the filter."""

    action_get = "statements.read.all"

    def get(self, request: Request) -> Response:
        payee_kind = (request.query_params.get("payee_kind") or "").strip().upper() or None
        if payee_kind and payee_kind not in PayeeKind.values:
            raise services.InvalidPeriod("payee_kind must be OPERATOR or GROUP.")
        payee_id = (request.query_params.get("payee_id") or "").strip() or None
        if payee_id:
            try:
                uuid.UUID(payee_id)
            except ValueError as exc:
                raise services.InvalidPeriod("payee_id must be a UUID.") from exc
        qs = services.admin_queryset(
            period_start=_date_param(request, "period_start"),
            payee_kind=payee_kind,
            payee_id=payee_id,
        )
        paginator = _StatementPagination()
        page = paginator.paginate_queryset(qs, request)
        response = paginator.get_paginated_response(_SummaryRow(page, many=True).data)
        response.data["totals"] = services.admin_totals(qs)
        return response


class AdminStatementDetailView(StatementDetailView):
    """``GET /admin/statements/<id>`` — the same detail, for staff."""

    action_get = "statements.read.all"


class _RunSerializer(serializers.Serializer):
    period_start = serializers.DateField(required=False)


class AdminRunView(OrgApiView):
    """``POST /admin/statements/run {period_start?}`` — bill a finished week
    (default: last week). Idempotent."""

    action_post = "statements.run"

    def post(self, request: Request) -> Response:
        s = _RunSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        period_start = (
            s.validated_data.get("period_start") or services.last_completed_period_start()
        )
        result = services.run_statements(period_start=period_start, actor=self.actor(request))
        return Response(result, status=201 if result["statements_created"] else 200)


class _PaymentSerializer(serializers.Serializer):
    amount_kes = serializers.IntegerField()
    payment_ref = serializers.CharField(max_length=64)
    paid_on = serializers.DateField()
    method = serializers.ChoiceField(
        choices=SettlementMethod.values, default=SettlementMethod.MPESA_PAYBILL
    )
    note = serializers.CharField(max_length=500, required=False, allow_blank=True, default="")


class AdminPaymentsView(OrgApiView):
    """``POST /admin/statements/<id>/payments`` — record a payment (step-up)."""

    action_post = "statements.settle"

    def post(self, request: Request, statement_id: uuid.UUID) -> Response:
        s = _PaymentSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        v = s.validated_data
        result = services.record_payment(
            actor=self.actor(request),
            statement_id=statement_id,
            amount_kes=v["amount_kes"],
            payment_ref=v["payment_ref"],
            paid_on=v["paid_on"],
            method=v["method"],
            note=v["note"],
        )
        return Response(result, status=201)


class _ReverseSerializer(serializers.Serializer):
    reason = serializers.CharField(max_length=2000)


class AdminReversePaymentView(OrgApiView):
    """``POST /admin/statements/<id>/payments/<payment_id>/reverse`` (step-up)."""

    action_post = "statements.settle"

    def post(self, request: Request, statement_id: uuid.UUID, payment_id: uuid.UUID) -> Response:
        s = _ReverseSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        result = services.reverse_payment(
            actor=self.actor(request),
            statement_id=statement_id,
            settlement_id=payment_id,
            reason=s.validated_data["reason"],
        )
        return Response(result, status=201)
