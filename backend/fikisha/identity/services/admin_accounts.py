"""The admin status change for user accounts (Design Phase 6 Increment 9,
ADR-2D-38). A user who is not ``ACTIVE`` can't refresh or use a session
(``identity.services.auth``), so suspending or offboarding a user signs them
out on their next request.

A plain write: authorisation, step-up, the reason, the ``admin_intervention``
row and the audit entry all belong to the caller, inside the caller's
transaction.
"""

from __future__ import annotations

from typing import Any

from rest_framework.exceptions import NotFound

from fikisha.identity.models import User, UserStatus

STATUSES = tuple(UserStatus.values)


def status_of(user_id: Any) -> str | None:
    return User.objects.filter(id=user_id).values_list("status", flat=True).first()


def set_state(user_id: Any, status: str) -> tuple[str, str]:
    """Set the status; returns ``(before, after)``. Call inside a
    transaction (the row is locked)."""
    user = User.objects.select_for_update().filter(id=user_id).first()
    if user is None:
        raise NotFound("No such user.")
    before = user.status
    user.status = status
    user.save(update_fields=["status", "updated_at"])
    return before, status
