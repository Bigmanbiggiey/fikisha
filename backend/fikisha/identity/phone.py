"""Phone-number normalisation + validation.

Phase 2A keeps this permissive-but-strict: accept common local forms, store
E.164. Kenya (+254) is the default country for a bare ``07…`` / ``01…`` number
since the pilot is Kitengela.
"""

from __future__ import annotations

import re

from django.core.exceptions import ValidationError

_E164 = re.compile(r"^\+[1-9]\d{7,14}$")
_DEFAULT_CC = "254"


def normalize_phone(raw: str) -> str:
    if not raw:
        raise ValidationError("Phone number is required.", code="phone.required")
    cleaned = re.sub(r"[\s\-().]", "", raw.strip())

    if cleaned.startswith("+"):
        candidate = cleaned
    elif cleaned.startswith("00"):
        candidate = "+" + cleaned[2:]
    elif cleaned.startswith("0") and len(cleaned) >= 9:
        candidate = "+" + _DEFAULT_CC + cleaned[1:]
    elif cleaned.startswith(_DEFAULT_CC):
        candidate = "+" + cleaned
    elif cleaned.isdigit() and 9 <= len(cleaned) <= 10:
        candidate = "+" + _DEFAULT_CC + cleaned.lstrip("0")
    else:
        candidate = "+" + cleaned if cleaned.isdigit() else cleaned

    if not _E164.match(candidate):
        raise ValidationError(
            "Enter a valid phone number in international format.", code="phone.invalid"
        )
    return candidate


def mask_phone(phone: str) -> str:
    """For logs: ``+254712345678`` -> ``+2547****5678``."""
    if len(phone) < 8:
        return "****"
    return phone[:5] + "****" + phone[-4:]
