"""Audit authorization policies (registered on app ``ready()``)."""

from __future__ import annotations

from typing import Any

from fikisha.identity.authz.engine import ALLOW, Decision, deny, policy


@policy("audit.view.scoped")
def _audit_view_scoped(actor: Any, action: str, _resource: Any) -> Decision:
    """Config-driven (``platform_config.role_permissions``): Operations
    Officer holds ``audit.view.scoped``; Platform Admin holds ``"*"``. The
    *scope* itself is applied to the queryset in the view
    (:mod:`fikisha.audit.scopes`)."""
    if not getattr(actor, "is_authenticated", False):
        return deny("authz.unauthenticated")
    from fikisha.identity.authz.policies import actor_has_permission

    if actor_has_permission(actor, action):
        return ALLOW
    return deny("authz.forbidden", f"missing permission {action!r}")
