"""Negotiation API (Phase 2D Step 10) — a thin adapter over
``fikisha.negotiation.services``. The API never asserts an offer is active,
accepted, or superseded — every state here is read back from the domain
(brief §5)."""

from __future__ import annotations

from django.shortcuts import get_object_or_404
from rest_framework.request import Request
from rest_framework.response import Response

from fikisha.common.api import OrgApiView
from fikisha.common.idempotency import idempotent
from fikisha.negotiation import services
from fikisha.negotiation.api.serializers import (
    AcceptSerializer,
    CounterSerializer,
    DeclineSerializer,
    ProposeSerializer,
)
from fikisha.negotiation.models import NegotiationThread


def _thread_or_404(thread_id: str) -> NegotiationThread:
    return get_object_or_404(NegotiationThread.objects.select_related("job"), pk=thread_id)


def _idempotency_key(request: Request) -> str:
    return request.META.get("HTTP_IDEMPOTENCY_KEY", "").strip()


class NegotiationThreadCollectionView(OrgApiView):
    action_get = "negotiation.read"
    action_post = "negotiation.propose"

    def get(self, request: Request, job_id: str) -> Response:
        threads = services.list_threads(actor=self.actor(request), job_id=job_id)
        return Response({"data": threads})

    def post(self, request: Request, job_id: str) -> Response:
        serializer = ProposeSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        def run() -> Response:
            payload = services.propose(
                actor=self.actor(request),
                job_id=job_id,
                operator_id=serializer.validated_data.get("operator_id"),
                group_id=serializer.validated_data.get("group_id"),
                amount_kes=serializer.validated_data["amount_kes"],
                note=serializer.validated_data.get("note", ""),
            )
            return Response(payload, status=201)

        return idempotent(request, actor_id=str(request.user.id), run=run)


class NegotiationThreadDetailView(OrgApiView):
    action_get = "negotiation.read"

    def resolve_target(self) -> NegotiationThread:
        return _thread_or_404(self.kwargs["thread_id"])

    def get(self, request: Request, thread_id: str) -> Response:
        payload = services.view_thread(actor=self.actor(request), thread_id=thread_id)
        return Response(payload)


class NegotiationCounterView(OrgApiView):
    action_post = "negotiation.counter"

    def resolve_target(self) -> NegotiationThread:
        return _thread_or_404(self.kwargs["thread_id"])

    def post(self, request: Request, thread_id: str) -> Response:
        self.get_authz_resource()
        serializer = CounterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        payload = services.counter(
            actor=self.actor(request),
            thread_id=thread_id,
            amount_kes=serializer.validated_data["amount_kes"],
            note=serializer.validated_data.get("note", ""),
        )
        return Response(payload)


class NegotiationAcceptView(OrgApiView):
    action_post = "negotiation.accept"

    def resolve_target(self) -> NegotiationThread:
        return _thread_or_404(self.kwargs["thread_id"])

    def post(self, request: Request, thread_id: str) -> Response:
        self.get_authz_resource()
        serializer = AcceptSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        payload = services.accept(
            actor=self.actor(request),
            thread_id=thread_id,
            amount_kes=serializer.validated_data.get("amount_kes"),
            idempotency_key=_idempotency_key(request),
        )
        return Response(payload)


class NegotiationDeclineView(OrgApiView):
    action_post = "negotiation.decline"

    def resolve_target(self) -> NegotiationThread:
        return _thread_or_404(self.kwargs["thread_id"])

    def post(self, request: Request, thread_id: str) -> Response:
        self.get_authz_resource()
        serializer = DeclineSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        payload = services.decline(
            actor=self.actor(request),
            thread_id=thread_id,
            note=serializer.validated_data.get("note", ""),
        )
        return Response(payload)
