"""Job contact phones follow the Kenyan rule (assessment 2026-10-20 L-3)."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

import pytest

pytestmark = pytest.mark.django_db


def test_job_contacts(client_for: Callable, business_actor: Any, verified_business: Any) -> None:
    payload = {
        "business_id": str(verified_business.id),
        "pickup_location": {"address_text": "Depot", "contact_phone": "+254100350768"},
        "destination_location": {"address_text": "Shop"},
        "cargo": {"description": "cement", "declared_value_kes": 1_000_000},
        "recipient_phone": "+25472345689",
    }
    client = client_for(business_actor.user)
    assert client.post("/api/v1/jobs", payload, format="json").status_code == 400
    payload["recipient_phone"] = "0712345678"
    r = client.post("/api/v1/jobs", payload, format="json")
    assert r.status_code == 201, r.content
    assert r.data["recipient_phone"] == "+254712345678"
    assert r.data["pickup_location"]["contact_phone"] == "+254100350768"
