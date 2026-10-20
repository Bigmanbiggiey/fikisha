"""Ratings authorization. Coarse gates only: the service checks that the
actor is the job's business or operator side (``ratings.services``), and
the read view checks job party or staff."""

from __future__ import annotations

from typing import Any

from fikisha.identity.authz.engine import ALLOW, Decision, deny, policy


@policy("rating.read")
def _rating_read(actor: Any, _action: str, _resource: Any) -> Decision:
    return ALLOW if getattr(actor, "is_authenticated", False) else deny("authz.unauthenticated")


@policy("rating.submit")
def _rating_submit(actor: Any, _action: str, _resource: Any) -> Decision:
    return ALLOW if getattr(actor, "is_authenticated", False) else deny("authz.unauthenticated")
