"""Messages inbox authorization policies (registered on app ``ready()``).

Coarse gate only: any signed-in person may read their own inbox and mark
their own conversations read. What each person sees is decided per source
by that module's own party checks (``jobs.job_authz.jobs_visible_to``,
``negotiation.services.inbox_threads``, ``incidents.services.
inbox_items_for_job``), never by a client-supplied id.
"""

from __future__ import annotations

from typing import Any

from fikisha.identity.authz.engine import ALLOW, Decision, deny, policy


def _authed(actor: Any) -> Decision:
    return ALLOW if getattr(actor, "is_authenticated", False) else deny("authz.unauthenticated")


@policy("inbox.read")
def _read(actor: Any, _action: str, _resource: Any) -> Decision:
    return _authed(actor)


@policy("inbox.mark_read")
def _mark_read(actor: Any, _action: str, _resource: Any) -> Decision:
    return _authed(actor)
