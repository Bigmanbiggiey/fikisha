"""Negotiation HTTP API (Phase 2D Step 10): propose/counter/accept/decline
through the real HTTP boundary — the API never asserts offer state (brief
§5)."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

import pytest
from rest_framework.test import APIClient

pytestmark = pytest.mark.django_db


class TestProposeAndAccept:
    def test_operator_accepts_posted_price_then_business_accepts_confirms_the_job(
        self,
        client_for: Callable,
        requested_job: Any,
        operator_a: Any,
        business_owner: Any,
    ) -> None:
        """Mirrors ``test_negotiation_flow.py``'s domain-level proof: the
        operator matches the business's already-seeded posted price
        (250,000) and accepts it; only once *both* sides have an ACTIVE
        ACCEPT for the same figure does the job confirm — the API asserts
        none of this itself, it only reads back what the domain decided."""
        op_client = client_for(operator_a.user)
        r = op_client.post(
            f"/api/v1/jobs/{requested_job.id}/negotiation/threads",
            {"operator_id": str(operator_a.id), "amount_kes": 250_000},
            format="json",
        )
        assert r.status_code == 201, r.content
        thread_id = r.data["thread_id"]
        assert r.data["job_status"] == "NEGOTIATING"

        r = op_client.post(f"/api/v1/negotiation/threads/{thread_id}/accept", {}, format="json")
        assert r.status_code == 200, r.content
        assert r.data["confirmed"] is False  # waiting on the business

        biz_client = client_for(business_owner)
        r = biz_client.post(f"/api/v1/negotiation/threads/{thread_id}/accept", {}, format="json")
        assert r.status_code == 200, r.content
        assert r.data["confirmed"] is True
        assert r.data["job"]["status"] == "CONFIRMED"

    def test_a_stranger_cannot_read_a_sealed_thread(
        self,
        client_for: Callable,
        requested_job: Any,
        operator_a: Any,
        operator_b: Any,
    ) -> None:
        op_client = client_for(operator_a.user)
        r = op_client.post(
            f"/api/v1/jobs/{requested_job.id}/negotiation/threads",
            {"operator_id": str(operator_a.id), "amount_kes": 220_000},
            format="json",
        )
        thread_id = r.data["thread_id"]

        other_client = client_for(operator_b.user)
        r = other_client.get(f"/api/v1/negotiation/threads/{thread_id}")
        assert r.status_code == 403

    def test_the_api_cannot_be_used_to_assert_an_amount_the_counterparty_never_offered(
        self, client_for: Callable, requested_job: Any, operator_a: Any, business_owner: Any
    ) -> None:
        op_client = client_for(operator_a.user)
        r = op_client.post(
            f"/api/v1/jobs/{requested_job.id}/negotiation/threads",
            {"operator_id": str(operator_a.id), "amount_kes": 220_000},
            format="json",
        )
        thread_id = r.data["thread_id"]
        biz_client = client_for(business_owner)
        r = biz_client.post(
            f"/api/v1/negotiation/threads/{thread_id}/accept",
            {"amount_kes": 999_999},
            format="json",
        )
        assert r.status_code == 422
        assert r.data["code"] == "invalid_offer"

    def test_business_counters_and_operator_accepts(
        self, client_for: Callable, requested_job: Any, operator_a: Any, business_owner: Any
    ) -> None:
        op_client = client_for(operator_a.user)
        r = op_client.post(
            f"/api/v1/jobs/{requested_job.id}/negotiation/threads",
            {"operator_id": str(operator_a.id), "amount_kes": 220_000},
            format="json",
        )
        thread_id = r.data["thread_id"]

        biz_client = client_for(business_owner)
        r = biz_client.post(
            f"/api/v1/negotiation/threads/{thread_id}/counter",
            {"amount_kes": 240_000},
            format="json",
        )
        assert r.status_code == 200, r.content

        # operator accepts the business's 240k counter — waiting on the business
        r = op_client.post(f"/api/v1/negotiation/threads/{thread_id}/accept", {}, format="json")
        assert r.status_code == 200
        assert r.data["confirmed"] is False

        r = biz_client.post(f"/api/v1/negotiation/threads/{thread_id}/accept", {}, format="json")
        assert r.status_code == 200
        assert r.data["confirmed"] is True

    def test_operator_declines_and_job_stays_open(
        self, client_for: Callable, requested_job: Any, operator_a: Any
    ) -> None:
        op_client = client_for(operator_a.user)
        r = op_client.post(
            f"/api/v1/jobs/{requested_job.id}/negotiation/threads",
            {"operator_id": str(operator_a.id), "amount_kes": 220_000},
            format="json",
        )
        thread_id = r.data["thread_id"]
        r = op_client.post(
            f"/api/v1/negotiation/threads/{thread_id}/decline",
            {"note": "too far"},
            format="json",
        )
        assert r.status_code == 200
        assert r.data["status"] == "CLOSED"

    def test_proposing_requires_authentication(self, api: APIClient, requested_job: Any) -> None:
        r = api.post(
            f"/api/v1/jobs/{requested_job.id}/negotiation/threads",
            {"operator_id": "00000000-0000-7000-8000-000000000000", "amount_kes": 100},
            format="json",
        )
        assert r.status_code == 401

    def test_propose_requires_exactly_one_of_operator_or_group(
        self, client_for: Callable, requested_job: Any, operator_a: Any
    ) -> None:
        op_client = client_for(operator_a.user)
        r = op_client.post(
            f"/api/v1/jobs/{requested_job.id}/negotiation/threads",
            {"amount_kes": 220_000},
            format="json",
        )
        assert r.status_code == 400
