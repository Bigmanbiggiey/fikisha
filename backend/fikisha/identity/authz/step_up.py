"""Step-up re-authentication gate (Phase 1 `authentication-authorization.md`
§1.2, `security-architecture.md` item 17).

A fresh TOTP step-up is required for platform-config change, account
suspension/offboarding, dispute resolution, high-value approval and HIGH-PII
views. Admin TOTP has not been built yet (Increment 9 decision D-1, deferred
by the founder 2026-10-13), so ``Actor.is_step_up_fresh`` is always ``False``
and every action behind this gate is refused with ``step_up_required``. That
is deliberate: the actions are built and tested, but none of them can run
until step-up exists. When it does, this function needs no change; the
actor's flag starts coming back ``True`` after a successful step-up.
"""

from __future__ import annotations

from typing import Any

from rest_framework import status

from fikisha.common.exceptions import DomainError


class StepUpRequired(DomainError):
    status_code = status.HTTP_403_FORBIDDEN
    default_code = "step_up_required"
    default_detail = "This action needs a fresh MFA check, which is not available yet."


def require_step_up(actor: Any) -> None:
    if not getattr(actor, "is_step_up_fresh", False):
        raise StepUpRequired()
