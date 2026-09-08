from __future__ import annotations

import pytest
from django.core.exceptions import ValidationError

from fikisha.identity.phone import mask_phone, normalize_phone


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("+254712345678", "+254712345678"),
        ("0712345678", "+254712345678"),
        ("0712 345 678", "+254712345678"),
        ("254712345678", "+254712345678"),
        ("00254712345678", "+254712345678"),
        ("+254 (712) 345-678", "+254712345678"),
    ],
)
def test_normalize_ok(raw: str, expected: str) -> None:
    assert normalize_phone(raw) == expected


@pytest.mark.parametrize("raw", ["", "abc", "12", "+0123", "not a phone"])
def test_normalize_rejects(raw: str) -> None:
    with pytest.raises(ValidationError):
        normalize_phone(raw)


def test_mask() -> None:
    assert mask_phone("+254712345678") == "+2547****5678"
