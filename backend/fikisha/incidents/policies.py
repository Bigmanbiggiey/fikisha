"""Incidents & Disputes authorization policies (registered on app ``ready()``).

Coarse gate only — "may this actor touch incidents/disputes at all". The
authoritative resource-aware checks (is this actor a party to *this* job; is a
binding resolution above STANDARD band restricted to a Platform Admin) run in
:mod:`fikisha.incidents.services` / :mod:`fikisha.incidents.authz`, and — for
the Job-status-changing operations — inside
``JobLifecycleService.transition()`` itself (``AdminBandAuthorised`` etc.),
exactly like the assignment and high-value policies.
"""

from __future__ import annotations

from typing import Any

from fikisha.identity.authz.engine import ALLOW, Decision, deny, policy


def _authed(actor: Any) -> Decision:
    return ALLOW if getattr(actor, "is_authenticated", False) else deny("authz.unauthenticated")


def _is_admin(actor: Any) -> bool:
    roles = {str(r) for r in (getattr(actor, "roles", None) or [])}
    return bool(roles & {"PLATFORM_ADMIN", "OPERATIONS_OFFICER"}) or bool(
        getattr(actor, "is_admin", False)
    )


@policy("incident.create")
def _incident_create(actor: Any, _action: str, _resource: Any) -> Decision:
    """Any party or admin may report an incident; a recipient reports via its
    own principal-scoped path (``fikisha.jobs.recipient`` /
    ``incidents.intake_recipient_report``), not this policy."""
    return _authed(actor)


@policy("incident.evidence.attach")
def _incident_evidence_attach(actor: Any, _action: str, _resource: Any) -> Decision:
    return _authed(actor)


@policy("incident.statement.add")
def _incident_statement_add(actor: Any, _action: str, _resource: Any) -> Decision:
    return _authed(actor)


@policy("incident.review")
def _incident_review(actor: Any, _action: str, _resource: Any) -> Decision:
    """Acknowledge / start review / open the amicable window — admin or an
    Operations Officer with ``incident.amicable.facilitate`` (config-driven,
    already present in ``role_permissions`` — ADR-2A pattern)."""
    if not getattr(actor, "is_authenticated", False):
        return deny("authz.unauthenticated")
    if _is_admin(actor):
        return ALLOW
    return deny("authz.forbidden", "Incident review requires an admin role.")


@policy("incident.escalate")
def _incident_escalate(actor: Any, _action: str, _resource: Any) -> Decision:
    if not getattr(actor, "is_authenticated", False):
        return deny("authz.unauthenticated")
    return ALLOW if _is_admin(actor) else deny("authz.forbidden")


@policy("dispute.open")
def _dispute_open(actor: Any, _action: str, _resource: Any) -> Decision:
    """Coarse gate — the allowed-initiator match for the freeze transition runs
    inside ``JobLifecycleService.transition()``."""
    return _authed(actor)


@policy("dispute.resolve")
def _dispute_resolve(actor: Any, _action: str, _resource: Any) -> Decision:
    """Coarse gate — must be *some* admin tier; the STANDARD-vs-above-STANDARD
    Platform-Admin-only split is the ``AdminBandAuthorised`` guard inside the
    transition (D-ADM-1), not this policy."""
    if not getattr(actor, "is_authenticated", False):
        return deny("authz.unauthenticated")
    return ALLOW if _is_admin(actor) else deny("authz.forbidden")
