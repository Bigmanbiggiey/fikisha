"""Operator + operating-location API (Phase 2B)."""

from __future__ import annotations

from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.exceptions import NotFound
from rest_framework.request import Request
from rest_framework.response import Response

from fikisha.common.api import OrgApiView, paginated
from fikisha.common.idempotency import idempotent
from fikisha.operators import services
from fikisha.operators.api.serializers import (
    BaseAssociateSerializer,
    BaseMembershipSerializer,
    OperatingLocationSerializer,
    OperatingLocationWriteSerializer,
    OperatorCreateSerializer,
    OperatorProfileSerializer,
    OperatorUpdateSerializer,
)
from fikisha.operators.models import BaseMembership, OperatingBase, OperatorProfile


class OperatorCollectionView(OrgApiView):
    action_post = "operator.create"

    def post(self, request: Request) -> Response:
        serializer = OperatorCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        def run() -> Response:
            profile = services.create_profile(
                actor=self.actor(request), **serializer.validated_data
            )
            return Response(OperatorProfileSerializer(profile).data, status=status.HTTP_201_CREATED)

        return idempotent(request, actor_id=str(request.user.id), run=run)


class OperatorMeView(OrgApiView):
    action_get = "operator.read.me"

    def get(self, request: Request) -> Response:
        profile = services.profile_for(self.user(request))
        if profile is None:
            raise NotFound(detail="No operator profile for this account.", code="not_found")
        return Response(OperatorProfileSerializer(profile).data)


class OperatorDetailView(OrgApiView):
    action_get = "operator.read"
    action_patch = "operator.update"

    def resolve_target(self) -> OperatorProfile:
        return get_object_or_404(OperatorProfile, pk=self.kwargs["operator_id"])

    def get(self, request: Request, operator_id: str) -> Response:
        return Response(OperatorProfileSerializer(self.get_authz_resource()).data)

    def patch(self, request: Request, operator_id: str) -> Response:
        profile = self.get_authz_resource()
        serializer = OperatorUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        profile = services.update_profile(
            actor=self.actor(request),
            profile=profile,
            patch=serializer.validated_data,
            is_platform_admin=self.is_platform_admin(request),
        )
        return Response(OperatorProfileSerializer(profile).data)


class OperatorBaseCollectionView(OrgApiView):
    action_get = "operator.read"
    action_post = "operator.update"

    def resolve_target(self) -> OperatorProfile:
        return get_object_or_404(OperatorProfile, pk=self.kwargs["operator_id"])

    def get(self, request: Request, operator_id: str) -> Response:
        profile = self.get_authz_resource()
        qs = profile.base_memberships.select_related("base").order_by("-created_at")
        return Response({"data": BaseMembershipSerializer(qs, many=True).data})

    def post(self, request: Request, operator_id: str) -> Response:
        profile = self.get_authz_resource()
        serializer = BaseAssociateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        base = get_object_or_404(OperatingBase, pk=serializer.validated_data["base_id"])
        membership = services.associate_operator(
            actor=self.actor(request),
            base=base,
            operator=profile,
            role=serializer.validated_data.get("role", ""),
        )
        return Response(BaseMembershipSerializer(membership).data, status=status.HTTP_201_CREATED)


class OperatorBaseDetailView(OrgApiView):
    action_delete = "operator.update"

    def resolve_target(self) -> OperatorProfile:
        return get_object_or_404(OperatorProfile, pk=self.kwargs["operator_id"])

    def delete(self, request: Request, operator_id: str, membership_id: str) -> Response:
        profile = self.get_authz_resource()
        membership = get_object_or_404(BaseMembership, pk=membership_id, operator=profile)
        services.end_association(actor=self.actor(request), membership=membership)
        return Response(status=status.HTTP_204_NO_CONTENT)


class OperatingLocationCollectionView(OrgApiView):
    action_get = "operating_location.read"
    action_post = "operating_location.create"

    def get(self, request: Request) -> Response:
        qs = services.bases(
            base_type=request.query_params.get("type"),
            zone_id=self._zone_id(request.query_params.get("zone")),
        )
        return paginated(request, qs, OperatingLocationSerializer)

    @staticmethod
    def _zone_id(code: str | None) -> object | None:
        if not code:
            return None
        from fikisha.platform_config.models import Zone

        return Zone.objects.filter(code=code).values_list("id", flat=True).first()

    def post(self, request: Request) -> Response:
        serializer = OperatingLocationWriteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        def run() -> Response:
            base = services.create_base(
                actor=self.actor(request), data=serializer.to_service_data()
            )
            return Response(OperatingLocationSerializer(base).data, status=status.HTTP_201_CREATED)

        return idempotent(request, actor_id=str(request.user.id), run=run)


class OperatingLocationDetailView(OrgApiView):
    action_get = "operating_location.read"
    action_patch = "operating_location.manage"

    def resolve_target(self) -> OperatingBase:
        return get_object_or_404(OperatingBase, pk=self.kwargs["base_id"])

    def get(self, request: Request, base_id: str) -> Response:
        return Response(OperatingLocationSerializer(self.get_authz_resource()).data)

    def patch(self, request: Request, base_id: str) -> Response:
        base = self.get_authz_resource()
        serializer = OperatingLocationWriteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        base = services.update_base(
            actor=self.actor(request), base=base, data=serializer.to_service_data()
        )
        return Response(OperatingLocationSerializer(base).data)
