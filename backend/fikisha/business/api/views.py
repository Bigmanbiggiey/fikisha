"""Business API (Phase 2B). Authorization runs before every handler via the
engine (``OrgApiView.required_action`` + ``get_authz_resource``); the service
layer enforces the domain invariants.
"""

from __future__ import annotations

from typing import Any

from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.request import Request
from rest_framework.response import Response

from fikisha.business import services
from fikisha.business.api.serializers import (
    BusinessCreateSerializer,
    BusinessSerializer,
    BusinessUpdateSerializer,
    LocationSerializer,
    LocationWriteSerializer,
    MemberAddSerializer,
    MembershipSerializer,
    MemberUpdateSerializer,
)
from fikisha.business.models import BusinessAccount, BusinessLocation, BusinessMembership
from fikisha.common.api import OrgApiView, paginated
from fikisha.common.idempotency import idempotent


def _business_ctx(request: Request, business: BusinessAccount) -> dict[str, Any]:
    from fikisha.identity.authz.actors import actor_from_request

    actor = actor_from_request(request)
    membership = services.membership_for(actor.user, business.id) if actor.user else None
    return {"my_role": membership.role if membership else None, "request": request}


class BusinessCollectionView(OrgApiView):
    action_get = "business.list"
    action_post = "business.create"

    def get(self, request: Request) -> Response:
        return paginated(request, services.businesses_for(self.user(request)), BusinessSerializer)

    def post(self, request: Request) -> Response:
        serializer = BusinessCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        def run() -> Response:
            business = services.create_business(
                actor=self.actor(request), **serializer.validated_data
            )
            return Response(
                BusinessSerializer(business, context=_business_ctx(request, business)).data,
                status=status.HTTP_201_CREATED,
            )

        return idempotent(request, actor_id=str(request.user.id), run=run)


class BusinessDetailView(OrgApiView):
    action_get = "business.read"
    action_patch = "business.update"

    def resolve_target(self) -> BusinessAccount:
        return get_object_or_404(BusinessAccount, pk=self.kwargs["business_id"])

    def get(self, request: Request, business_id: str) -> Response:
        business = self.get_authz_resource()
        return Response(BusinessSerializer(business, context=_business_ctx(request, business)).data)

    def patch(self, request: Request, business_id: str) -> Response:
        business = self.get_authz_resource()
        serializer = BusinessUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        business = services.update_business(
            actor=self.actor(request),
            business=business,
            patch=serializer.validated_data,
            is_platform_admin=self.is_platform_admin(request),
        )
        return Response(BusinessSerializer(business, context=_business_ctx(request, business)).data)


class BusinessMemberCollectionView(OrgApiView):
    action_get = "business.member.list"
    action_post = "business.member.manage"

    def resolve_target(self) -> BusinessAccount:
        return get_object_or_404(BusinessAccount, pk=self.kwargs["business_id"])

    def get(self, request: Request, business_id: str) -> Response:
        business = self.get_authz_resource()
        qs = business.memberships.select_related("user").order_by("created_at")
        return Response({"data": MembershipSerializer(qs, many=True).data})

    def post(self, request: Request, business_id: str) -> Response:
        business = self.get_authz_resource()
        serializer = MemberAddSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        def run() -> Response:
            membership = services.add_member(
                actor=self.actor(request),
                business=business,
                phone=serializer.validated_data["phone"],
                role=serializer.validated_data["role"],
            )
            return Response(MembershipSerializer(membership).data, status=status.HTTP_201_CREATED)

        return idempotent(request, actor_id=str(request.user.id), run=run)


class BusinessMemberDetailView(OrgApiView):
    action_patch = "business.member.manage"
    action_delete = "business.member.manage"

    def resolve_target(self) -> BusinessAccount:
        return get_object_or_404(BusinessAccount, pk=self.kwargs["business_id"])

    def _membership(self, business: BusinessAccount) -> BusinessMembership:
        return get_object_or_404(BusinessMembership, pk=self.kwargs["member_id"], business=business)

    def patch(self, request: Request, business_id: str, member_id: str) -> Response:
        business = self.get_authz_resource()
        serializer = MemberUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        membership = services.update_membership(
            actor=self.actor(request),
            business=business,
            membership=self._membership(business),
            role=serializer.validated_data.get("role"),
            status=serializer.validated_data.get("status"),
        )
        return Response(MembershipSerializer(membership).data)

    def delete(self, request: Request, business_id: str, member_id: str) -> Response:
        business = self.get_authz_resource()
        services.remove_member(
            actor=self.actor(request),
            business=business,
            membership=self._membership(business),
        )
        return Response(status=status.HTTP_204_NO_CONTENT)


class BusinessLocationCollectionView(OrgApiView):
    action_get = "business.location.read"
    action_post = "business.location.manage"

    def resolve_target(self) -> BusinessAccount:
        return get_object_or_404(BusinessAccount, pk=self.kwargs["business_id"])

    def get(self, request: Request, business_id: str) -> Response:
        business = self.get_authz_resource()
        return Response(
            {"data": LocationSerializer(services.locations_for(business), many=True).data}
        )

    def post(self, request: Request, business_id: str) -> Response:
        business = self.get_authz_resource()
        serializer = LocationWriteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        def run() -> Response:
            location = services.create_location(
                actor=self.actor(request),
                business=business,
                data=serializer.to_service_data(),
            )
            return Response(LocationSerializer(location).data, status=status.HTTP_201_CREATED)

        return idempotent(request, actor_id=str(request.user.id), run=run)


class BusinessLocationDetailView(OrgApiView):
    action_get = "business.location.read"
    action_patch = "business.location.manage"
    action_delete = "business.location.manage"

    def resolve_target(self) -> BusinessAccount:
        return get_object_or_404(BusinessAccount, pk=self.kwargs["business_id"])

    def _location(self, business: BusinessAccount) -> BusinessLocation:
        return get_object_or_404(BusinessLocation, pk=self.kwargs["location_id"], business=business)

    def get(self, request: Request, business_id: str, location_id: str) -> Response:
        business = self.get_authz_resource()
        return Response(LocationSerializer(self._location(business)).data)

    def patch(self, request: Request, business_id: str, location_id: str) -> Response:
        business = self.get_authz_resource()
        serializer = LocationWriteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        location = services.update_location(
            actor=self.actor(request),
            business=business,
            location=self._location(business),
            data=serializer.to_service_data(),
        )
        return Response(LocationSerializer(location).data)

    def delete(self, request: Request, business_id: str, location_id: str) -> Response:
        business = self.get_authz_resource()
        services.deactivate_location(
            actor=self.actor(request), business=business, location=self._location(business)
        )
        return Response(status=status.HTTP_204_NO_CONTENT)
