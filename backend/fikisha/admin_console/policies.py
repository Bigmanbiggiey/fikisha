"""Platform Admin console authorization policies (registered on app
``ready()``). Each is a config-driven permission from
``platform_config.role_permissions``: the Platform Admin holds ``"*"``; no
other role holds any of these today (Increment 9 D-6). Granting one to the
Operations Officer later is a config change, not a code change, with the
step-up gate still applying to the actions.
"""

from __future__ import annotations

from typing import Any

from fikisha.identity.authz.engine import ALLOW, Decision, deny, policy
from fikisha.identity.authz.policies import actor_has_permission

PERMISSIONS = (
    "admin.directory.read",
    "admin.directory.contact_reveal",
    "admin.account.intervene",
    "admin.config.read",
    "admin.config.change",
    "admin.commission.read",
)


def _by_permission(actor: Any, action: str, _resource: Any) -> Decision:
    if not getattr(actor, "is_authenticated", False):
        return deny("authz.unauthenticated")
    return ALLOW if actor_has_permission(actor, action) else deny("authz.missing_permission")


for _permission in PERMISSIONS:
    policy(_permission)(_by_permission)
