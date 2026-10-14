"""Actor shapes consumed by the authorization engine + the audit subsystem."""

from __future__ import annotations

from dataclasses import dataclass, field

from django.http import HttpRequest

from fikisha.audit.models import ActorRole
from fikisha.identity.models import AuthSession, RoleAssignment, User


@dataclass(frozen=True)
class Actor:
    is_authenticated: bool = False
    user: User | None = None
    roles: frozenset[str] = field(default_factory=frozenset)
    is_admin: bool = False
    session: AuthSession | None = None
    #: a fresh MFA step-up on this session (Increment 9a, ADR-2D-39)
    is_step_up_fresh: bool = False

    @property
    def audit_role(self) -> str:
        if not self.is_authenticated:
            return ActorRole.ANONYMOUS
        if "PLATFORM_ADMIN" in self.roles:
            return ActorRole.PLATFORM_ADMIN
        if "OPERATIONS_OFFICER" in self.roles or self.is_admin:
            return ActorRole.OPERATIONS_OFFICER
        # No Business/Operator profile concept exists yet in Phase 2A.
        return ActorRole.USER


class AnonymousActor(Actor):
    def __init__(self) -> None:
        super().__init__(is_authenticated=False)


class SystemActor(Actor):
    """A scheduler / event-handler identity (for audit attribution)."""

    def __init__(self, name: str = "system") -> None:
        super().__init__(is_authenticated=False)
        object.__setattr__(self, "name", name)

    @property
    def audit_role(self) -> str:
        return ActorRole.SYSTEM


def actor_from_user(user: User | None, session: AuthSession | None = None) -> Actor:
    if user is None:
        return AnonymousActor()
    from fikisha.identity.services import mfa

    roles = set(
        RoleAssignment.objects.filter(user=user, revoked_at__isnull=True).values_list(
            "role", flat=True
        )
    )
    is_admin = getattr(getattr(user, "admin_profile", None), "active", False) is True
    # An admin's powers apply only on a session that passed MFA (Phase 1
    # authentication-authorization.md §1.2, ADR-2D-39). Until then they act
    # as an ordinary user and can only enrol or verify. Internal callers with
    # no session (services, tests) are unaffected.
    if is_admin and session is not None and session.mfa_verified_at is None:
        roles = set()
        is_admin = False
    return Actor(
        is_authenticated=True,
        user=user,
        roles=frozenset(roles),
        is_admin=is_admin,
        session=session,
        is_step_up_fresh=mfa.step_up_fresh(session),
    )


def actor_from_request(request: HttpRequest) -> Actor:
    user = getattr(request, "user", None)
    if user is None or not getattr(user, "is_authenticated", False):
        return AnonymousActor()
    session = getattr(request, "auth", None)
    return actor_from_user(user, session if isinstance(session, AuthSession) else None)
