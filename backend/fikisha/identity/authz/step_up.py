"""Step-up re-authentication gate (Phase 1 `authentication-authorization.md`
§1.2, `security-architecture.md` item 17).

A fresh MFA code is required for platform-config change, account
suspension/offboarding, dispute resolution, high-value approval and HIGH-PII
document views. The admin enters it through ``POST /auth/step-up``
(``identity.services.mfa``, Increment 9a, ADR-2D-39); it stays fresh for
``AUTH_CONFIG["STEP_UP_TTL_SECONDS"]``. Until then the action is refused
with ``step_up_required``, and the client asks for a code and retries.
"""

from __future__ import annotations

from typing import Any

from rest_framework import status

from fikisha.common.exceptions import DomainError


class StepUpRequired(DomainError):
    status_code = status.HTTP_403_FORBIDDEN
    default_code = "step_up_required"
    default_detail = "Enter a fresh authenticator code to do this."


def require_step_up(actor: Any) -> None:
    if not getattr(actor, "is_step_up_fresh", False):
        raise StepUpRequired()
