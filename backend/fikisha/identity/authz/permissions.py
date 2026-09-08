"""DRF permission classes backed by the authorization engine.

A view sets ``required_action = "some.action"`` and (optionally) implements
``get_authz_resource(self)`` for object-level checks. On denial the class raises
so the problem+json handler renders a stable ``code``.
"""

from __future__ import annotations

from typing import Any

from rest_framework.exceptions import NotAuthenticated
from rest_framework.permissions import BasePermission
from rest_framework.request import Request
from rest_framework.views import APIView

from fikisha.common.exceptions import AuthorizationError
from fikisha.identity.authz.actors import actor_from_request
from fikisha.identity.authz.engine import Decision, authorize

# Denial codes that mean "you're not signed in" -> 401, not 403.
_UNAUTHENTICATED_CODES = {"authz.unauthenticated", "authz.no_policy"}


def _raise_for_denial(decision: Decision, *, authenticated: bool) -> None:
    if decision.code == "authz.unauthenticated" or (
        decision.code == "authz.no_policy" and not authenticated
    ):
        raise NotAuthenticated(detail="Authentication required.", code="authz.unauthenticated")
    raise AuthorizationError(decision.reason or "Forbidden.", code=decision.code)


class ActionPermission(BasePermission):
    """Enforce ``view.required_action`` through the authorization engine.

    Distinguishes 401 (not authenticated) from 403 (authenticated but not
    permitted) — Phase 1 authentication-authorization.md.
    """

    def has_permission(self, request: Request, view: APIView) -> bool:
        action = getattr(view, "required_action", None)
        if action is None:  # pragma: no cover - misconfiguration
            raise AuthorizationError("View is missing required_action.", code="authz.misconfigured")
        actor = actor_from_request(request)
        resource = None
        getter = getattr(view, "get_authz_resource", None)
        if callable(getter):
            resource = getter()
        decision = authorize(actor, action, resource)
        if not decision.allowed:
            _raise_for_denial(decision, authenticated=actor.is_authenticated)
        return True

    def has_object_permission(self, request: Request, view: APIView, obj: Any) -> bool:
        action = getattr(view, "required_action", None)
        if action is None:  # pragma: no cover - misconfiguration
            raise AuthorizationError("View is missing required_action.", code="authz.misconfigured")
        actor = actor_from_request(request)
        decision = authorize(actor, action, obj)
        if not decision.allowed:
            _raise_for_denial(decision, authenticated=actor.is_authenticated)
        return True
