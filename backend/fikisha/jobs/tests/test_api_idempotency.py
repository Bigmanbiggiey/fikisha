"""HTTP ``Idempotency-Key`` boundary (Phase 2D Step 10 brief §21/§22): the
existing cache-based ``fikisha.common.idempotency.idempotent()`` for plain
creates, and the existing DB-row-based ``JobTransitionIdempotency`` (already
built in Increment 1) for lifecycle actions — no second idempotency store."""

from __future__ import annotations

import threading
from collections.abc import Callable
from typing import Any

import pytest
from django.core.cache import cache
from django.db import connection

pytestmark = pytest.mark.django_db


@pytest.fixture(autouse=True)
def _clear_idempotency_cache() -> None:
    cache.clear()


def _create_payload(business_id: str) -> dict[str, Any]:
    return {
        "business_id": business_id,
        "pickup_location": {"address_text": "Depot"},
        "destination_location": {"address_text": "Shop"},
        "cargo": {"description": "cartons", "declared_value_kes": 1_200_000},
    }


def test_same_key_same_request_returns_the_identical_cached_response(
    client_for: Callable, business_actor: Any, verified_business: Any
) -> None:
    from fikisha.jobs.models import Job

    client = client_for(business_actor.user)
    payload = _create_payload(str(verified_business.id))
    r1 = client.post("/api/v1/jobs", payload, format="json", HTTP_IDEMPOTENCY_KEY="k-1")
    r2 = client.post("/api/v1/jobs", payload, format="json", HTTP_IDEMPOTENCY_KEY="k-1")
    assert r1.status_code == r2.status_code == 201
    assert r1.data == r2.data
    assert r2.get("Idempotency-Replayed") == "true"
    assert Job.objects.filter(business=verified_business).count() == 1


def test_a_retry_after_success_does_not_duplicate_the_side_effect(
    client_for: Callable, business_actor: Any, verified_business: Any
) -> None:
    from fikisha.jobs.models import Job

    client = client_for(business_actor.user)
    payload = _create_payload(str(verified_business.id))
    for _ in range(3):
        client.post("/api/v1/jobs", payload, format="json", HTTP_IDEMPOTENCY_KEY="k-retry")
    assert Job.objects.filter(business=verified_business).count() == 1


def test_idempotency_does_not_bypass_authorization(
    client_for: Callable, other_user: Any, verified_business: Any
) -> None:
    client = client_for(other_user)
    payload = _create_payload(str(verified_business.id))
    r = client.post("/api/v1/jobs", payload, format="json", HTTP_IDEMPOTENCY_KEY="k-authz")
    assert r.status_code == 403  # not cached as a success; the check still ran


@pytest.mark.django_db(transaction=True)
def test_concurrent_requests_with_the_same_key_produce_exactly_one_job(
    client_for: Callable, business_actor: Any, verified_business: Any
) -> None:
    from fikisha.jobs.models import Job

    payload = _create_payload(str(verified_business.id))
    statuses: list[int] = []
    lock = threading.Lock()

    def _create() -> None:
        try:
            client = client_for(business_actor.user)
            r = client.post(
                "/api/v1/jobs", payload, format="json", HTTP_IDEMPOTENCY_KEY="k-concurrent"
            )
            with lock:
                statuses.append(r.status_code)
        finally:
            connection.close()

    threads = [threading.Thread(target=_create) for _ in range(5)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    # Every request either creates-or-replays (201) or finds the lock still
    # held by a sibling request (409 idempotency_in_progress) — never a raw
    # duplicate-row error, and never more than one row created either way.
    assert all(code in (201, 409) for code in statuses), statuses
    assert Job.objects.filter(business=verified_business).count() == 1


def test_job_transition_idempotency_reuses_the_existing_db_backed_store(
    client_for: Callable, business_actor: Any, draft_job: Any
) -> None:
    """``submit`` forwards ``Idempotency-Key`` straight to
    ``JobLifecycleService.transition()``'s own ``JobTransitionIdempotency``
    table (built in Increment 1) — no second store."""
    from fikisha.jobs.models import JobTransitionIdempotency

    client = client_for(business_actor.user)
    r1 = client.post(
        f"/api/v1/jobs/{draft_job.id}/submit", format="json", HTTP_IDEMPOTENCY_KEY="submit-1"
    )
    r2 = client.post(
        f"/api/v1/jobs/{draft_job.id}/submit", format="json", HTTP_IDEMPOTENCY_KEY="submit-1"
    )
    assert r1.status_code == r2.status_code == 200
    assert r1.data == r2.data
    assert JobTransitionIdempotency.objects.filter(job=draft_job).count() == 1
