"""Vehicle API (Phase 2C). Authorization runs before every handler via the
engine; the service layer enforces domain invariants.
"""

from __future__ import annotations

from typing import Any

from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.request import Request
from rest_framework.response import Response

from fikisha.common.api import OrgApiView, paginated
from fikisha.common.exceptions import AuthorizationError
from fikisha.common.idempotency import idempotent
from fikisha.groups.authz import can_manage as group_can_manage
from fikisha.groups.models import GroupMembership, GroupMembershipStatus
from fikisha.identity.authz.actors import actor_from_request
from fikisha.operators.models import OperatorProfile
from fikisha.vehicles import services
from fikisha.vehicles.api.serializers import (
    VehicleCreateSerializer,
    VehicleDeactivateSerializer,
    VehicleSerializer,
    VehicleStatusSerializer,
    VehicleUpdateSerializer,
)
from fikisha.vehicles.models import Vehicle


def _caller_scope(request: Request) -> tuple[list[Any], list[Any]]:
    """(operator_profile_ids, group_ids) the caller is an active member of."""
    user: Any = request.user
    profile_ids = list(OperatorProfile.objects.filter(user=user).values_list("id", flat=True))
    group_ids = list(
        GroupMembership.objects.filter(
            operator__user=user, status=GroupMembershipStatus.ACTIVE
        ).values_list("group_id", flat=True)
    )
    return profile_ids, group_ids


class VehicleCollectionView(OrgApiView):
    action_get = "vehicle.list"
    action_post = "vehicle.create"

    def get(self, request: Request) -> Response:
        profile_ids, group_ids = _caller_scope(request)
        qs = (
            Vehicle.objects.filter(deactivated_at__isnull=True)
            .filter(services.controlled_by_query(profile_ids, group_ids))
            .select_related("vehicle_class")
            .order_by("-created_at")
        )
        return paginated(request, qs, VehicleSerializer)

    def post(self, request: Request) -> Response:
        serializer = VehicleCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        actor = actor_from_request(request)

        owner_operator = owner_group = None
        if data.get("owner_operator_id"):
            owner_operator = get_object_or_404(OperatorProfile, pk=data["owner_operator_id"])
            if str(owner_operator.user_id) != str(request.user.id):
                raise AuthorizationError(
                    "You can only register a vehicle to your own operator profile.",
                    code="authz.forbidden",
                )
        else:
            from fikisha.groups.models import OperatorGroup

            owner_group = get_object_or_404(OperatorGroup, pk=data["owner_group_id"])
            if not group_can_manage(actor, {"group_id": owner_group.id}):
                raise AuthorizationError(
                    "You must be an owner or manager of that group.", code="authz.forbidden"
                )

        def run() -> Response:
            vehicle = services.register_vehicle(
                actor=actor,
                owner_operator=owner_operator,
                owner_group=owner_group,
                vehicle_class_code=data["vehicle_class"],
                registration=data["registration"],
                capacity_value=data["capacity_value"],
                capacity_unit=data.get("capacity_unit", "KG"),
                **{
                    k: v
                    for k, v in data.items()
                    if k
                    not in {
                        "owner_operator_id",
                        "owner_group_id",
                        "vehicle_class",
                        "registration",
                        "capacity_value",
                        "capacity_unit",
                    }
                },
            )
            return Response(VehicleSerializer(vehicle).data, status=status.HTTP_201_CREATED)

        return idempotent(request, actor_id=str(request.user.id), run=run)


class VehicleDetailView(OrgApiView):
    action_get = "vehicle.read"
    action_patch = "vehicle.manage"
    action_delete = "vehicle.manage"

    def resolve_target(self) -> Vehicle:
        return get_object_or_404(
            Vehicle.objects.select_related("vehicle_class"), pk=self.kwargs["vehicle_id"]
        )

    def get(self, request: Request, vehicle_id: str) -> Response:
        return Response(VehicleSerializer(self.get_authz_resource()).data)

    def patch(self, request: Request, vehicle_id: str) -> Response:
        vehicle = self.get_authz_resource()
        serializer = VehicleUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        patch = dict(serializer.validated_data)
        if "vehicle_class" in patch:
            patch["vehicle_class_code"] = patch.pop("vehicle_class")
        vehicle = services.update_vehicle(
            actor=actor_from_request(request), vehicle=vehicle, patch=patch
        )
        return Response(VehicleSerializer(vehicle).data)

    def delete(self, request: Request, vehicle_id: str) -> Response:
        vehicle = self.get_authz_resource()
        serializer = VehicleDeactivateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        services.deactivate_vehicle(
            actor=actor_from_request(request),
            vehicle=vehicle,
            reason=serializer.validated_data["reason"],
        )
        return Response(status=status.HTTP_204_NO_CONTENT)


class VehicleStatusView(OrgApiView):
    action_post = "vehicle.manage"

    def resolve_target(self) -> Vehicle:
        return get_object_or_404(Vehicle, pk=self.kwargs["vehicle_id"])

    def post(self, request: Request, vehicle_id: str) -> Response:
        vehicle = self.get_authz_resource()
        serializer = VehicleStatusSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        vehicle = services.set_status(
            actor=actor_from_request(request),
            vehicle=vehicle,
            status=serializer.validated_data["status"],
            reason=serializer.validated_data["reason"],
            is_platform_admin=self.is_platform_admin(request),
        )
        return Response(VehicleSerializer(vehicle).data)
