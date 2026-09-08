"""Access-token encode/decode.

Phase 1 ADR-011: opaque server-side sessions. The access token is a short-lived
*signed* value that carries only the ``session_id`` (+ ``user_id`` for a cheap
sanity check). Every request still loads the ``AuthSession`` row, so revocation
is instant.
"""

from __future__ import annotations

import hashlib
import secrets
from typing import Any

from django.conf import settings
from django.core import signing

_ACCESS_SALT = "fikisha.access.v1"


def make_access_token(*, session_id: str, user_id: str) -> str:
    # ``n`` is a per-token nonce so two tokens minted for the same session in the
    # same second are still distinct (and greppable in logs).
    return signing.dumps(
        {"sid": str(session_id), "uid": str(user_id), "n": secrets.token_hex(8)},
        salt=_ACCESS_SALT,
    )


def read_access_token(token: str) -> dict[str, Any]:
    """Return ``{"sid", "uid"}`` or raise ``signing.BadSignature`` / ``SignatureExpired``."""
    max_age = settings.AUTH_CONFIG["ACCESS_TOKEN_TTL_SECONDS"]
    return signing.loads(token, salt=_ACCESS_SALT, max_age=max_age)


def new_refresh_token() -> str:
    return secrets.token_urlsafe(48)


def hash_refresh_token(raw: str) -> str:
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()
