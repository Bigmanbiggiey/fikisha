"""The Kenyan phone rule (founder assessment 2026-10-20 L-3, LD-2)."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

import pytest
from django.core.exceptions import ValidationError

from fikisha.identity.phone import mask_phone, national, normalize_phone


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("0712345678", "+254712345678"),
        ("0100350768", "+254100350768"),
        ("+254712345678", "+254712345678"),
        ("+254100350768", "+254100350768"),  # the founder's example: 0100350768
        ("0712 345 678", "+254712345678"),
        ("+254 (712) 345-678", "+254712345678"),
    ],
)
def test_valid_kenyan_numbers_are_stored_in_e164(raw: str, expected: str) -> None:
    assert normalize_phone(raw) == expected


@pytest.mark.parametrize(
    "raw",
    [
        "+25472345689",  # the founder's example: 072345689 is 9 digits
        "071234567",  # 9 digits
        "07123456789",  # 11 digits
        "254712345678",  # no +
        "00254712345678",
        "0812345678",  # not 07 / 01
        "712345678",
        "+447911123456",  # not Kenyan
        "",
        "abc",
    ],
)
def test_anything_else_is_refused(raw: str) -> None:
    with pytest.raises(ValidationError):
        normalize_phone(raw)


def test_shown_in_the_national_form() -> None:
    assert national("+254712345678") == "0712345678"
    assert national("+254100350768") == "0100350768"


def test_mask() -> None:
    assert mask_phone("+254712345678") == "+2547****5678"


@pytest.mark.django_db
class TestEveryEntryPoint:
    def test_sign_in_refuses_a_bad_number(self, api: Any) -> None:
        r = api.post("/api/v1/auth/otp/request", {"phone": "+25472345689"}, format="json")
        assert r.status_code == 400
        assert r["content-type"] == "application/problem+json"

    def test_business_and_location_contacts(self, user: Any, client_for: Callable) -> None:
        client = client_for(user)
        bad = client.post(
            "/api/v1/businesses",
            {"trading_name": "Duka", "contact_phone": "0812345678"},
            format="json",
        )
        assert bad.status_code == 400
        ok = client.post(
            "/api/v1/businesses",
            {"trading_name": "Duka", "contact_phone": "0712 345 678"},
            format="json",
        )
        assert ok.status_code == 201, ok.content
        assert ok.data["contact_phone"] == "+254712345678"
        bid = ok.data["id"]
        loc = client.post(
            f"/api/v1/businesses/{bid}/locations",
            {"label": "Shop", "type": "MAIN", "contact_phone": "071234567"},
            format="json",
        )
        assert loc.status_code == 400
        member = client.post(
            f"/api/v1/businesses/{bid}/members",
            {"phone": "254712345678", "role": "VIEWER"},
            format="json",
        )
        assert member.status_code == 400

    def test_operator_phones(self, user: Any, client_for: Callable) -> None:
        r = client_for(user).post(
            "/api/v1/operators", {"full_name": "Op", "phones": ["0712345678", "07"]}, format="json"
        )
        assert r.status_code == 400
