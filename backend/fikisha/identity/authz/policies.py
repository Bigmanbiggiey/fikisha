"""Foundation authorization policies.

Only cross-cutting / foundation actions are registered in Phase 2A. Business
actions (job.*, negotiation.*, verification.*, ...) register their own policies
with their modules later. Nothing here grants access by default.
"""

from __future__ import annotations

from typing import Any

from django.conf import settings

from fikisha.identity.authz.engine import ALLOW, Decision, deny, policy
from fikisha.platform_config import services as config


def actor_has_permission(actor: Any, permission: str) -> bool:
    """Resolve an admin permission from ``platform_config.role_permissions``.

    ``"*"`` in a role's list grants everything (PLATFORM_ADMIN).
    """
    if not getattr(actor, "is_authenticated", False):
        return False
    role_perms: dict[str, list[str]] = config.get("role_permissions", {}) or {}
    granted: set[str] = set()
    for role in getattr(actor, "roles", frozenset()):
        granted.update(role_perms.get(role, []))
    return "*" in granted or permission in granted


# ─── Authenticated-user foundation actions ─────────────────────────────
@policy("auth.me.read")
def _me_read(actor: Any, _action: str, _resource: Any) -> Decision:
    return ALLOW if getattr(actor, "is_authenticated", False) else deny("authz.unauthenticated")


@policy("auth.session.list")
def _session_list(actor: Any, _action: str, _resource: Any) -> Decision:
    return ALLOW if getattr(actor, "is_authenticated", False) else deny("authz.unauthenticated")


@policy("auth.session.revoke")
def _session_revoke(actor: Any, _action: str, resource: Any) -> Decision:
    if not getattr(actor, "is_authenticated", False):
        return deny("authz.unauthenticated")
    if resource is None:
        return ALLOW  # object-level check happens with the resource
    owner_id = getattr(resource, "user_id", None)
    if owner_id is not None and str(owner_id) == str(getattr(actor.user, "id", None)):
        return ALLOW
    return deny("authz.forbidden", "You may only manage your own sessions.")


@policy("config.read.public")
def _config_read_public(actor: Any, _action: str, _resource: Any) -> Decision:
    return ALLOW if getattr(actor, "is_authenticated", False) else deny("authz.unauthenticated")


# ─── Admin-namespaced actions (config-driven RBAC) ────────────────────
@policy("admin.*")
def _admin_actions(actor: Any, action: str, _resource: Any) -> Decision:
    if not getattr(actor, "is_authenticated", False):
        return deny("authz.unauthenticated")
    return (
        ALLOW
        if actor_has_permission(actor, action)
        else deny("authz.forbidden", f"missing permission {action!r}")
    )


@policy("config.change")
def _config_change(actor: Any, _action: str, _resource: Any) -> Decision:
    if not getattr(actor, "is_authenticated", False):
        return deny("authz.unauthenticated")
    return ALLOW if actor_has_permission(actor, "config.change") else deny("authz.forbidden")


# ─── Dev/test-only demo actions (feature flag + settings gate + admin) ─
@policy("demo.atomic.invoke")
def _demo_atomic(actor: Any, _action: str, _resource: Any) -> Decision:
    allowed_by_env = getattr(settings, "FIKISHA_ALLOW_DEMO_ENDPOINTS", False)
    if not allowed_by_env or not config.get("feature_flags.demo_endpoints", False):
        return deny("authz.disabled", "demo endpoints are disabled")
    if not getattr(actor, "is_authenticated", False):
        return deny("authz.unauthenticated")
    # Platform-admin only (same gate as a config change).
    return (
        ALLOW
        if actor_has_permission(actor, "config.change")
        else deny("authz.forbidden", "demo endpoints require a platform admin")
    )
