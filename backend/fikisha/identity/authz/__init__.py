"""Server-side authorization (Phase 1 authentication-authorization.md §2).

One engine — ``authorize(actor, action, resource) -> Decision`` — default deny,
RBAC + ABAC. Admin permissions are resolved from
``platform_config.role_permissions`` so the pilot's 2-role setup switches to the
4-role split by configuration, not a deploy (D-ADM-1 / FR-ADM-8).

Import the engine directly (``from fikisha.identity.authz.engine import ...``);
this package ``__init__`` is kept import-light to avoid circular imports during
app startup.
"""
