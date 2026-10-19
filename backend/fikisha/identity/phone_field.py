"""A DRF field for any phone a person types (assessment 2026-10-20 L-3).

Validates with :func:`fikisha.identity.phone.normalize_phone` and hands the
service the stored E.164 form. Optional fields may be left blank (``""``).
"""

from __future__ import annotations

from typing import Any

from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import serializers

from fikisha.identity.phone import normalize_phone


class KenyanPhoneField(serializers.CharField):
    default_error_messages = {"phone_invalid": "Enter a valid Kenyan phone number."}

    def __init__(self, **kwargs: Any) -> None:
        kwargs.setdefault("max_length", 32)
        super().__init__(**kwargs)

    def to_internal_value(self, data: Any) -> str:
        value = super().to_internal_value(data)
        if value == "":
            return value
        try:
            return normalize_phone(value)
        except DjangoValidationError as exc:
            raise serializers.ValidationError(exc.messages, code="phone_invalid") from exc
