"""Phone-number normalisation + validation.

One rule for every phone Fikisha takes (founder assessment 2026-10-20 L-3,
LD-2): a Kenyan mobile or landline-style number written as ``07…`` or ``01…``,
or as ``+254…``, where ``+254`` stands for the leading ``0``. After that
conversion it must be exactly 10 digits (``0`` + 9). Anything else is refused,
including a bare ``254…`` and foreign numbers.

    0712345678     -> +254712345678   (stored)  /  0712345678  (shown)
    +254100350768  -> +254100350768             /  0100350768
    +25472345689   -> refused: 072345689 is 9 digits

Stored in E.164 (``+254…``): logins and SMS providers need it. Shown in the
national form (``national()``).
"""

from __future__ import annotations

import re

from django.core.exceptions import ValidationError

_NATIONAL = re.compile(r"^0[17]\d{8}$")
_SEPARATORS = re.compile(r"[\s\-().]")

INVALID_MESSAGE = (
    "Enter a Kenyan number: 07… or 01… (10 digits), or +254 followed by the same "
    "number without its first 0."
)


def _national(raw: str) -> str | None:
    cleaned = _SEPARATORS.sub("", (raw or "").strip())
    if cleaned.startswith("+254"):
        cleaned = "0" + cleaned[4:]
    return cleaned if _NATIONAL.match(cleaned) else None


def normalize_phone(raw: str) -> str:
    """The stored (E.164) form of a valid Kenyan number, or ``ValidationError``."""
    if not (raw or "").strip():
        raise ValidationError("Phone number is required.", code="phone.required")
    national = _national(raw)
    if national is None:
        raise ValidationError(INVALID_MESSAGE, code="phone.invalid")
    return "+254" + national[1:]


def national(phone: str) -> str:
    """``+254712345678`` -> ``0712345678``; anything else returned unchanged."""
    return "0" + phone[4:] if phone.startswith("+254") and len(phone) == 13 else phone


def is_valid_phone(raw: str) -> bool:
    return _national(raw) is not None


def mask_phone(phone: str) -> str:
    """For logs: ``+254712345678`` -> ``+2547****5678``."""
    if len(phone) < 8:
        return "****"
    return phone[:5] + "****" + phone[-4:]
