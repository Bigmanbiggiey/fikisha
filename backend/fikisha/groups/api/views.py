"""Operator Group API (Phase 2B)."""

from __future__ import annotations

from typing import Any

from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.request import Request
from rest_framework.response import Response

from fikisha.common.api import OrgApiView, paginated
from fikisha.common.idempotency import idempotent
from fikisha.groups import services
from fikisha.groups.api.serializers import (
    GroupCreateSerializer,
    GroupMemberAddSerializer,
    GroupMembershipSerializer,
    GroupMemberUpdateSerializer,
    GroupSerializer,
    GroupUpdateSerializer,
)
from fikisha.groups.authz import active_membership
from fikisha.groups.models import GroupMembership, OperatorGroup
from fikisha.identity.authz.actors import actor_from_request
from fikisha.operators import services as operator_services
from fikisha.operators.api.serializers import BaseAssociateSerializer, BaseMembershipSerializer
from fikisha.operators.models import BaseMembership, OperatingBase, OperatorProfile


def _group_ctx(request: Request, group: OperatorGroup) -> dict[str, Any]:
    membership = active_membership(actor_from_request(request), group)
    return {"my_role": membership.role if membership else None, "request": request}


class GroupCollectionView(OrgApiView):
    action_get = "group.list"
    action_post = "group.create"

    def get(self, request: Request) -> Response:
        return paginated(request, services.groups_for(self.user(request)), GroupSerializer)

    def post(self, request: Request) -> Response:
        serializer = GroupCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        def run() -> Response:
            group = services.create_group(actor=self.actor(request), **serializer.validated_data)
            return Response(
                GroupSerializer(group, context=_group_ctx(request, group)).data,
                status=status.HTTP_201_CREATED,
            )

        return idempotent(request, actor_id=str(request.user.id), run=run)


class GroupDetailView(OrgApiView):
    action_get = "group.read"
    action_patch = "group.update"

    def resolve_target(self) -> OperatorGroup:
        return get_object_or_404(OperatorGroup, pk=self.kwargs["group_id"])

    def get(self, request: Request, group_id: str) -> Response:
        group = self.get_authz_resource()
        return Response(GroupSerializer(group, context=_group_ctx(request, group)).data)

    def patch(self, request: Request, group_id: str) -> Response:
        group = self.get_authz_resource()
        serializer = GroupUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        group = services.update_group(
            actor=self.actor(request),
            group=group,
            patch=serializer.validated_data,
            is_platform_admin=self.is_platform_admin(request),
        )
        return Response(GroupSerializer(group, context=_group_ctx(request, group)).data)


class GroupMemberCollectionView(OrgApiView):
    action_get = "group.member.list"
    action_post = "group.member.manage"

    def resolve_target(self) -> OperatorGroup:
        return get_object_or_404(OperatorGroup, pk=self.kwargs["group_id"])

    def get(self, request: Request, group_id: str) -> Response:
        group = self.get_authz_resource()
        qs = group.memberships.select_related("operator").order_by("since")
        return Response({"data": GroupMembershipSerializer(qs, many=True).data})

    def post(self, request: Request, group_id: str) -> Response:
        group = self.get_authz_resource()
        serializer = GroupMemberAddSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        operator = get_object_or_404(OperatorProfile, pk=serializer.validated_data["operator_id"])

        def run() -> Response:
            membership = services.add_member(
                actor=self.actor(request),
                group=group,
                operator=operator,
                role=serializer.validated_data["role"],
            )
            return Response(
                GroupMembershipSerializer(membership).data, status=status.HTTP_201_CREATED
            )

        return idempotent(request, actor_id=str(request.user.id), run=run)


class GroupMemberDetailView(OrgApiView):
    action_patch = "group.member.manage"
    action_delete = "group.member.manage"

    def resolve_target(self) -> OperatorGroup:
        return get_object_or_404(OperatorGroup, pk=self.kwargs["group_id"])

    def _membership(self, group: OperatorGroup) -> GroupMembership:
        return get_object_or_404(GroupMembership, pk=self.kwargs["member_id"], group=group)

    def patch(self, request: Request, group_id: str, member_id: str) -> Response:
        group = self.get_authz_resource()
        serializer = GroupMemberUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        membership = services.update_member(
            actor=self.actor(request),
            group=group,
            membership=self._membership(group),
            role=serializer.validated_data.get("role"),
            status=serializer.validated_data.get("status"),
        )
        return Response(GroupMembershipSerializer(membership).data)

    def delete(self, request: Request, group_id: str, member_id: str) -> Response:
        group = self.get_authz_resource()
        services.remove_member(
            actor=self.actor(request), group=group, membership=self._membership(group)
        )
        return Response(status=status.HTTP_204_NO_CONTENT)


class GroupBaseCollectionView(OrgApiView):
    action_get = "group.read"
    action_post = "group.update"

    def resolve_target(self) -> OperatorGroup:
        return get_object_or_404(OperatorGroup, pk=self.kwargs["group_id"])

    def get(self, request: Request, group_id: str) -> Response:
        group = self.get_authz_resource()
        qs = group.base_memberships.select_related("base").order_by("-created_at")
        return Response({"data": BaseMembershipSerializer(qs, many=True).data})

    def post(self, request: Request, group_id: str) -> Response:
        group = self.get_authz_resource()
        serializer = BaseAssociateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        base = get_object_or_404(OperatingBase, pk=serializer.validated_data["base_id"])
        membership = operator_services.associate_group(
            actor=self.actor(request),
            base=base,
            group=group,
            role=serializer.validated_data.get("role", ""),
        )
        return Response(BaseMembershipSerializer(membership).data, status=status.HTTP_201_CREATED)


class GroupBaseDetailView(OrgApiView):
    action_delete = "group.update"

    def resolve_target(self) -> OperatorGroup:
        return get_object_or_404(OperatorGroup, pk=self.kwargs["group_id"])

    def delete(self, request: Request, group_id: str, membership_id: str) -> Response:
        group = self.get_authz_resource()
        membership = get_object_or_404(BaseMembership, pk=membership_id, group=group)
        operator_services.end_association(actor=self.actor(request), membership=membership)
        return Response(status=status.HTTP_204_NO_CONTENT)
