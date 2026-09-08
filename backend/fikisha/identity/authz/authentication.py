"""DRF authentication: ``Authorization: Bearer <access-token>``.

Resolves the token to an ``AuthSession`` (opaque server-side session, ADR-011).
An absent header -> anonymous (returns ``None``). A present-but-bad token -> 401
via the problem+json handler.
"""

from __future__ import annotations

from rest_framework.authentication import BaseAuthentication, get_authorization_header
from rest_framework.request import Request

from fikisha.identity.models import AuthSession, User
from fikisha.identity.services import auth as auth_service


class BearerSessionAuthentication(BaseAuthentication):
    keyword = b"bearer"

    def authenticate(self, request: Request) -> tuple[User, AuthSession] | None:
        header = get_authorization_header(request).split()
        if not header or header[0].lower() != self.keyword:
            return None
        if len(header) != 2:
            from rest_framework.exceptions import AuthenticationFailed

            raise AuthenticationFailed(
                "Malformed Authorization header.", code="auth.header_invalid"
            )
        token = header[1].decode("latin-1")
        user, session = auth_service.resolve_session(token)
        return user, session

    def authenticate_header(self, request: Request) -> str:
        return 'Bearer realm="fikisha"'
