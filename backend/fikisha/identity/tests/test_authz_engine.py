"""Authorization engine tests — default deny, vertical + horizontal escalation."""

from __future__ import annotations

import pytest

from fikisha.common.exceptions import AuthorizationError
from fikisha.identity.authz.actors import AnonymousActor, actor_from_user
from fikisha.identity.authz.engine import authorize, require

pytestmark = pytest.mark.django_db


class TestDefaultDeny:
    def test_unregistered_action_is_denied(self) -> None:
        decision = authorize(AnonymousActor(), "totally.unknown.action")
        assert decision.allowed is False
        assert decision.code == "authz.no_policy"

    def test_require_raises_on_deny(self) -> None:
        with pytest.raises(AuthorizationError):
            require(AnonymousActor(), "totally.unknown.action")


class TestAuthenticatedActions:
    def test_me_read_requires_auth(self, user: object) -> None:
        assert authorize(AnonymousActor(), "auth.me.read").allowed is False
        assert authorize(actor_from_user(user), "auth.me.read").allowed is True


class TestVerticalEscalation:
    def test_plain_user_denied_admin_action(self, user: object) -> None:
        decision = authorize(actor_from_user(user), "admin.ping")
        assert decision.allowed is False
        assert decision.code == "authz.forbidden"

    def test_platform_admin_allowed_admin_action(self, platform_admin: object) -> None:
        assert authorize(actor_from_user(platform_admin), "admin.ping").allowed is True

    def test_ops_officer_denied_config_change(self, ops_officer: object) -> None:
        # OPERATIONS_OFFICER's config-driven permission set excludes "config.change".
        assert authorize(actor_from_user(ops_officer), "config.change").allowed is False

    def test_platform_admin_allowed_config_change(self, platform_admin: object) -> None:
        assert authorize(actor_from_user(platform_admin), "config.change").allowed is True


class TestHorizontalEscalation:
    def test_session_revoke_denied_for_other_users_resource(
        self, user: object, other_user: object
    ) -> None:
        from datetime import timedelta

        from django.utils import timezone

        from fikisha.identity.models import AuthSession

        victim_session = AuthSession.objects.create(
            user=other_user, expires_at=timezone.now() + timedelta(days=1)
        )
        decision = authorize(actor_from_user(user), "auth.session.revoke", victim_session)
        assert decision.allowed is False
        assert decision.code == "authz.forbidden"

    def test_session_revoke_allowed_for_own_resource(self, user: object) -> None:
        from datetime import timedelta

        from django.utils import timezone

        from fikisha.identity.models import AuthSession

        own = AuthSession.objects.create(user=user, expires_at=timezone.now() + timedelta(days=1))
        assert authorize(actor_from_user(user), "auth.session.revoke", own).allowed is True
