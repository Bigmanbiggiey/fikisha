"""Operator tier API (operator-tiers plan T-3 / T-4)."""

from __future__ import annotations

from typing import Any

from rest_framework.exceptions import NotFound
from rest_framework.request import Request
from rest_framework.response import Response

from fikisha.common.api import OrgApiView
from fikisha.identity.authz.policies import actor_has_permission
from fikisha.operators import services as operators
from fikisha.trust import services
from fikisha.trust.api.serializers import DecideProposalSerializer, SetTierSerializer


def _is_staff(view: OrgApiView, request: Request) -> bool:
    return actor_has_permission(view.actor(request), "operator.read")


class MyTierView(OrgApiView):
    action_get = "operator.read.me"

    def get(self, request: Request) -> Response:
        profile = operators.profile_for(self.user(request))
        if profile is None:
            raise NotFound(detail="No operator profile for this account.", code="not_found")
        return Response(services.tier_view(profile, staff=False))


class OperatorTierView(OrgApiView):
    action_get = "trust.read"

    def resolve_target(self) -> Any:
        profile = operators.profile_by_id(self.kwargs["operator_id"])
        if profile is None:
            raise NotFound("No such operator.")
        return profile

    def get(self, request: Request, operator_id: str) -> Response:
        profile = self.get_authz_resource()
        return Response(services.tier_view(profile, staff=_is_staff(self, request)))


class SetTierView(OrgApiView):
    """A Platform Admin's direct promote / demote (TD-1)."""

    action_post = "trust.change.apply"

    def post(self, request: Request, operator_id: str) -> Response:
        body = SetTierSerializer(data=request.data)
        body.is_valid(raise_exception=True)
        services.set_level(
            actor=self.actor(request),
            operator_id=operator_id,
            level=body.validated_data["level"],
            reason=body.validated_data["reason"],
        )
        profile = operators.profile_by_id(operator_id)
        return Response(services.tier_view(profile, staff=True))


class TierProposalsView(OrgApiView):
    action_get = "trust.queue.read"

    def get(self, request: Request) -> Response:
        return Response({"data": services.open_proposals()})


class DecideProposalView(OrgApiView):
    action_post = "trust.change.apply"

    def post(self, request: Request, change_id: str) -> Response:
        body = DecideProposalSerializer(data=request.data)
        body.is_valid(raise_exception=True)
        change = services.decide_proposal(
            actor=self.actor(request),
            change_id=change_id,
            confirm=body.validated_data["decision"] == "CONFIRM",
            reason=body.validated_data["reason"],
        )
        profile = operators.profile_by_id(change.operator_id)
        return Response(services.tier_view(profile, staff=True))
