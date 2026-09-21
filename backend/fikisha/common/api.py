"""Small shared helpers for the organisation APIs (Phase 2B).

``OrgApiView`` wires the authorization engine to a view whose HTTP methods map to
different authz actions, and lets a detail view expose its target object to the
policy for an object-level check before the handler runs.
"""

from __future__ import annotations

from typing import Any, ClassVar

from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from fikisha.identity.authz.actors import actor_from_request
from fikisha.identity.authz.permissions import ActionPermission


class OrgApiView(APIView):
    """Base view for the Phase 2B organisation endpoints.

    Set the per-method action names. A detail view additionally implements
    ``resolve_target(self) -> object`` (cached) — its return value is handed to
    the authorization policy so the object-level check happens before the body
    of the handler.
    """

    permission_classes = [ActionPermission]

    action_get: ClassVar[str | None] = None
    action_post: ClassVar[str | None] = None
    action_patch: ClassVar[str | None] = None
    action_put: ClassVar[str | None] = None
    action_delete: ClassVar[str | None] = None

    @property
    def required_action(self) -> str:
        method = (self.request.method or "GET").lower()
        action = getattr(self, f"action_{method}", None)
        if action is None:  # pragma: no cover - misconfiguration
            raise RuntimeError(f"{type(self).__name__} has no authz action for {method.upper()}")
        return action

    def get_authz_resource(self) -> Any:
        resolver = getattr(self, "resolve_target", None)
        if not callable(resolver):
            return None
        if not hasattr(self, "_authz_target"):
            self._authz_target = resolver()
        return self._authz_target

    # convenience
    def actor(self, request: Request) -> Any:
        return actor_from_request(request)

    def user(self, request: Request) -> Any:
        """The authenticated ``User`` (views here always run behind ActionPermission).

        Returned as ``Any`` so callers can pass it to service functions typed for
        the concrete ``identity.User`` without a cast at every call site.
        """
        return request.user

    def is_platform_admin(self, request: Request) -> bool:
        from fikisha.identity.authz.policies import actor_has_permission

        return actor_has_permission(self.actor(request), "*")


def paginated(
    request: Request,
    queryset: Any,
    serializer_cls: Any,
    *,
    context: dict[str, Any] | None = None,
) -> Response:
    """Standard cursor-paginated list response (``{data, page}``). ``context``
    merges into the serializer context alongside ``request`` — e.g. the
    acting operator for a per-row eligibility computation
    (``jobs.discovery.opportunity_view``)."""
    from fikisha.common.pagination import CursorPagination

    paginator = CursorPagination()
    page = paginator.paginate_queryset(queryset, request)
    ctx: dict[str, Any] = {"request": request}
    if context:
        ctx.update(context)
    data = serializer_cls(page, many=True, context=ctx).data
    return paginator.get_paginated_response(data)
