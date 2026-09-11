"""Custody / OTP HTTP API (Phase 2D Step 10): the pickup/delivery proof
matrix through the real HTTP boundary, plus the **mandatory** concurrent-HTTP
OTP single-use regression (brief §8/§22)."""

from __future__ import annotations

import threading
from collections.abc import Callable
from typing import Any

import pytest
from django.db import connection
from rest_framework.test import APIClient

pytestmark = pytest.mark.django_db


class TestArrivalAndCustodyFlow:
    def test_driver_drives_a_standard_job_through_pickup_to_delivery(
        self, client_for: Callable, driver_actor: Any, make_assigned_job: Callable
    ) -> None:
        job = make_assigned_job()
        client = client_for(driver_actor.user)

        r = client.post(f"/api/v1/jobs/{job.id}/custody/arrive-pickup", format="json")
        assert r.status_code == 200, r.content
        assert r.data["status"] == "AT_PICKUP"

        r = client.post(
            f"/api/v1/jobs/{job.id}/custody/confirm-pickup/otp", {"code": "000000"}, format="json"
        )
        assert r.status_code == 200, r.content
        assert r.data["status"] == "PICKED_UP"

        r = client.post(f"/api/v1/jobs/{job.id}/custody/start-transit", format="json")
        assert r.status_code == 200
        assert r.data["status"] == "IN_TRANSIT"

        r = client.post(f"/api/v1/jobs/{job.id}/custody/arrive-destination", format="json")
        assert r.status_code == 200
        assert r.data["status"] == "AT_DESTINATION"

        r = client.post(
            f"/api/v1/jobs/{job.id}/custody/confirm-delivery",
            {"party_name": "A. Recipient", "code": "000000"},
            format="json",
        )
        assert r.status_code == 200, r.content
        assert r.data["status"] == "DELIVERED"

    def test_an_unrelated_actor_cannot_confirm_pickup(
        self,
        client_for: Callable,
        driver_actor: Any,
        make_assigned_job: Callable,
        make_user: Callable,
    ) -> None:
        job = make_assigned_job()
        client_for(driver_actor.user).post(
            f"/api/v1/jobs/{job.id}/custody/arrive-pickup", format="json"
        )
        stranger = make_user("+254700888001")
        client = client_for(stranger)
        r = client.post(
            f"/api/v1/jobs/{job.id}/custody/confirm-pickup/otp", {"code": "000000"}, format="json"
        )
        assert r.status_code == 403

    def test_a_wrong_otp_is_rejected_not_a_500(
        self, client_for: Callable, driver_actor: Any, make_assigned_job: Callable
    ) -> None:
        job = make_assigned_job()
        client = client_for(driver_actor.user)
        client.post(f"/api/v1/jobs/{job.id}/custody/arrive-pickup", format="json")
        r = client.post(
            f"/api/v1/jobs/{job.id}/custody/confirm-pickup/otp", {"code": "999999"}, format="json"
        )
        assert r.status_code == 422
        assert r.data["code"] == "otp_invalid"

    def test_business_confirms_pickup_in_app(
        self,
        client_for: Callable,
        business_actor: Any,
        driver_actor: Any,
        make_assigned_job: Callable,
    ) -> None:
        job = make_assigned_job()
        client_for(driver_actor.user).post(
            f"/api/v1/jobs/{job.id}/custody/arrive-pickup", format="json"
        )
        client = client_for(business_actor.user)
        r = client.post(f"/api/v1/jobs/{job.id}/custody/confirm-pickup/business", {}, format="json")
        assert r.status_code == 200, r.content
        assert r.data["status"] == "PICKED_UP"

    def test_fail_at_pickup_requires_a_reason(
        self, client_for: Callable, admin_actor: Any, driver_actor: Any, make_assigned_job: Callable
    ) -> None:
        job = make_assigned_job()
        client_for(driver_actor.user).post(
            f"/api/v1/jobs/{job.id}/custody/arrive-pickup", format="json"
        )
        client = client_for(admin_actor.user)
        r = client.post(f"/api/v1/jobs/{job.id}/custody/fail-at-pickup", {}, format="json")
        assert r.status_code == 400  # reason_text is a required serializer field

        r = client.post(
            f"/api/v1/jobs/{job.id}/custody/fail-at-pickup",
            {"reason_text": "vehicle broke down"},
            format="json",
        )
        assert r.status_code == 200
        assert r.data["status"] == "FAILED"


@pytest.mark.django_db(transaction=True)
def test_concurrent_http_requests_cannot_both_consume_the_same_otp(
    make_assigned_job: Callable, driver_actor: Any, client_for: Callable
) -> None:
    """The mandatory Step 10 regression (brief §8): two simultaneous HTTP
    requests carrying the identical, still-valid OTP must not both succeed —
    the domain's OTP-challenge row is the atomic single-use boundary, not
    anything the HTTP layer adds; this proves it holds through the real HTTP
    stack, not just at the service-call layer."""
    job = make_assigned_job()
    client_for(driver_actor.user).post(
        f"/api/v1/jobs/{job.id}/custody/arrive-pickup", format="json"
    )

    results: list[int] = []
    lock = threading.Lock()

    def _confirm() -> None:
        try:
            client: APIClient = client_for(driver_actor.user)
            r = client.post(
                f"/api/v1/jobs/{job.id}/custody/confirm-pickup/otp",
                {"code": "000000"},
                format="json",
            )
            with lock:
                results.append(r.status_code)
        finally:
            connection.close()

    threads = [threading.Thread(target=_confirm) for _ in range(5)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    successes = [code for code in results if code == 200]
    assert len(successes) == 1, results

    from fikisha.jobs.models import Job

    job.refresh_from_db()
    assert Job.objects.get(id=job.id).status == "PICKED_UP"
