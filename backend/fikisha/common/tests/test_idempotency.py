"""Idempotency helper (Phase 2B §26)."""

from __future__ import annotations

from typing import Any

import pytest

from fikisha.business.models import BusinessAccount

pytestmark = pytest.mark.django_db


def test_repeated_create_with_same_key_creates_one_row(user: Any, client_for: Any) -> None:
    client = client_for(user)
    headers = {"HTTP_IDEMPOTENCY_KEY": "abc-123"}
    body = {"trading_name": "Retry Ltd"}

    r1 = client.post("/api/v1/businesses", body, format="json", **headers)
    r2 = client.post("/api/v1/businesses", body, format="json", **headers)

    assert r1.status_code == 201
    assert r2.status_code == 201
    assert r1.data["id"] == r2.data["id"]
    assert r2["Idempotency-Replayed"] == "true"
    assert BusinessAccount.objects.filter(trading_name="Retry Ltd").count() == 1


def test_different_keys_create_distinct_rows(user: Any, client_for: Any) -> None:
    client = client_for(user)
    body = {"trading_name": "Two Ltd"}
    client.post("/api/v1/businesses", body, format="json", HTTP_IDEMPOTENCY_KEY="k1")
    client.post("/api/v1/businesses", body, format="json", HTTP_IDEMPOTENCY_KEY="k2")
    assert BusinessAccount.objects.filter(trading_name="Two Ltd").count() == 2


def test_no_key_is_not_idempotent(user: Any, client_for: Any) -> None:
    client = client_for(user)
    body = {"trading_name": "NoKey Ltd"}
    client.post("/api/v1/businesses", body, format="json")
    client.post("/api/v1/businesses", body, format="json")
    assert BusinessAccount.objects.filter(trading_name="NoKey Ltd").count() == 2
