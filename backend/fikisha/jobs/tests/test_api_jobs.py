"""Jobs HTTP API (Phase 2D Step 10): creation, read, list, submit, cancel —
the domain-boundary + authorization + error-contract tests for the thin
adapter over ``fikisha.jobs`` services."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

import pytest
from rest_framework.test import APIClient

pytestmark = pytest.mark.django_db


def _create_payload(business_id: str, **overrides: Any) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "business_id": business_id,
        "pickup_location": {"address_text": "Depot, Kitengela", "contact_phone": "+254700900001"},
        "destination_location": {"address_text": "Shop 4, Kitengela"},
        "cargo": {"description": "20 cartons bottled water", "declared_value_kes": 1_200_000},
        "proposed_price_kes": 250_000,
    }
    payload.update(overrides)
    return payload


class TestJobCreation:
    def test_business_owner_creates_a_draft_job(
        self, client_for: Callable, business_actor: Any, verified_business: Any
    ) -> None:
        client = client_for(business_actor.user)
        r = client.post("/api/v1/jobs", _create_payload(str(verified_business.id)), format="json")
        assert r.status_code == 201, r.content
        assert r.data["status"] == "DRAFT"
        assert r.data["cargo"]["declared_value_kes"] == 1_200_000

    def test_creation_requires_authentication(self, api: APIClient, verified_business: Any) -> None:
        r = api.post("/api/v1/jobs", _create_payload(str(verified_business.id)), format="json")
        assert r.status_code == 401
        assert r["content-type"] == "application/problem+json"

    def test_a_stranger_may_not_create_a_job_for_someone_elses_business(
        self, client_for: Callable, other_user: Any, verified_business: Any
    ) -> None:
        client = client_for(other_user)
        r = client.post("/api/v1/jobs", _create_payload(str(verified_business.id)), format="json")
        assert r.status_code == 403
        assert r.data["code"] == "not_authorised_to_create_job"

    def test_missing_cargo_is_a_validation_error_not_a_500(
        self, client_for: Callable, business_actor: Any, verified_business: Any
    ) -> None:
        client = client_for(business_actor.user)
        payload = _create_payload(str(verified_business.id))
        del payload["cargo"]
        r = client.post("/api/v1/jobs", payload, format="json")
        assert r.status_code == 400
        assert r["content-type"] == "application/problem+json"

    def test_creation_is_idempotent_on_retry(
        self, client_for: Callable, business_actor: Any, verified_business: Any
    ) -> None:
        from fikisha.jobs.models import Job

        client = client_for(business_actor.user)
        payload = _create_payload(str(verified_business.id))
        r1 = client.post("/api/v1/jobs", payload, format="json", HTTP_IDEMPOTENCY_KEY="create-1")
        r2 = client.post("/api/v1/jobs", payload, format="json", HTTP_IDEMPOTENCY_KEY="create-1")
        assert r1.status_code == r2.status_code == 201
        assert r1.data["id"] == r2.data["id"]
        assert Job.objects.filter(business=verified_business).count() == 1


class TestJobReadAndList:
    def test_the_owning_business_can_read_its_job(
        self, client_for: Callable, business_actor: Any, draft_job: Any
    ) -> None:
        client = client_for(business_actor.user)
        r = client.get(f"/api/v1/jobs/{draft_job.id}")
        assert r.status_code == 200
        assert r.data["id"] == str(draft_job.id)

    def test_an_unrelated_business_cannot_read_the_job(
        self, client_for: Callable, make_user: Callable, draft_job: Any
    ) -> None:
        stranger = make_user("+254700777001")
        client = client_for(stranger)
        r = client.get(f"/api/v1/jobs/{draft_job.id}")
        assert r.status_code == 403
        assert r["content-type"] == "application/problem+json"

    def test_an_unknown_job_id_is_404(self, client_for: Callable, business_actor: Any) -> None:
        client = client_for(business_actor.user)
        r = client.get("/api/v1/jobs/00000000-0000-7000-8000-000000000000")
        assert r.status_code == 404

    def test_the_assigned_operator_can_read_the_job(
        self, client_for: Callable, driver_actor: Any, make_assigned_job: Callable
    ) -> None:
        job = make_assigned_job()
        client = client_for(driver_actor.user)
        r = client.get(f"/api/v1/jobs/{job.id}")
        assert r.status_code == 200

    def test_platform_admin_can_read_any_job(
        self, client_for: Callable, admin_actor: Any, draft_job: Any
    ) -> None:
        client = client_for(admin_actor.user)
        r = client.get(f"/api/v1/jobs/{draft_job.id}")
        assert r.status_code == 200

    def test_business_lists_only_its_own_jobs(
        self, client_for: Callable, business_actor: Any, draft_job: Any, make_user: Callable
    ) -> None:
        from fikisha.jobs.constants import JobStatus
        from fikisha.jobs.models import CargoDetails, Job, JobLocation, VehicleRequirement

        # a second, unrelated job that must never appear in this listing
        other_user = make_user("+254700777002")
        cargo = CargoDetails.objects.create(description="x", declared_value_kes=1000)
        pickup = JobLocation.objects.create(type="PICKUP", source_kind="AD_HOC")
        dest = JobLocation.objects.create(type="DESTINATION", source_kind="AD_HOC")
        vreq = VehicleRequirement.objects.create()
        from fikisha.business.models import BusinessAccount

        other_biz = BusinessAccount.objects.create(owner_user=other_user, trading_name="Other Co")
        other_job = Job.objects.create(
            business=other_biz,
            created_by=other_user,
            status=JobStatus.DRAFT,
            pickup_location=pickup,
            destination_location=dest,
            cargo=cargo,
            vehicle_requirement=vreq,
        )

        client = client_for(business_actor.user)
        r = client.get("/api/v1/jobs")
        assert r.status_code == 200
        ids = {row["id"] for row in r.data["data"]}
        assert str(draft_job.id) in ids
        assert str(other_job.id) not in ids

    def test_list_requires_authentication(self, api: APIClient) -> None:
        r = api.get("/api/v1/jobs")
        assert r.status_code == 401


class TestJobSubmitAndCancel:
    def test_business_owner_submits_a_complete_draft(
        self, client_for: Callable, business_actor: Any, draft_job: Any
    ) -> None:
        client = client_for(business_actor.user)
        r = client.post(f"/api/v1/jobs/{draft_job.id}/submit", format="json")
        assert r.status_code == 200, r.content
        assert r.data["status"] == "REQUESTED"

    def test_an_unrelated_actor_cannot_submit(
        self, client_for: Callable, make_user: Callable, draft_job: Any
    ) -> None:
        stranger = make_user("+254700777003")
        client = client_for(stranger)
        r = client.post(f"/api/v1/jobs/{draft_job.id}/submit", format="json")
        assert r.status_code == 403
        assert r.data["code"] == "not_authorised_to_initiate"

    def test_business_owner_cancels_a_draft_job(
        self, client_for: Callable, business_actor: Any, draft_job: Any
    ) -> None:
        client = client_for(business_actor.user)
        r = client.post(
            f"/api/v1/jobs/{draft_job.id}/cancel",
            {"reason_code": "BUSINESS_CHANGED_MIND", "reason_text": "no longer needed"},
            format="json",
        )
        assert r.status_code == 200
        assert r.data["status"] == "CANCELLED"

    @pytest.mark.django_db(transaction=True)
    def test_submit_and_cancel_work_outside_an_implicit_test_transaction(
        self, business_actor: Any, draft_job: Any
    ) -> None:
        """Self-caught bug (Step 11 concurrency testing surfaced it):
        ``creation.submit_job``/``cancel_job`` called ``job_for_update()``
        (``select_for_update()``) with no ``@transaction.atomic`` of their
        own — invisible under every prior test because pytest-django's
        default ``django_db`` fixture already wraps each test in an implicit
        atomic block, and Django has no ``ATOMIC_REQUESTS`` either, so the
        same crash was latent in real HTTP use. Fixed by switching both
        functions to the unlocked ``get_job()`` (they only resolve the
        initiator token; ``transition()`` re-locks the row itself, the
        actual authoritative check) — this test only passes under
        ``transaction=True``, which removes that implicit wrapper."""
        from fikisha.jobs.creation import cancel_job, submit_job

        result = submit_job(actor=business_actor, job_id=draft_job.id)
        assert result["status"] == "REQUESTED"
        result = cancel_job(
            actor=business_actor,
            job_id=draft_job.id,
            reason_code="BUSINESS_CHANGED_MIND",
        )
        assert result["status"] == "CANCELLED"

    def test_the_http_layer_does_not_bypass_the_transition_guard_chain(
        self, client_for: Callable, business_actor: Any, verified_business: Any
    ) -> None:
        """An incomplete DRAFT (no cargo/locations) fails ``RequiredFieldsComplete``
        — the same guard the domain always enforced; the API adds nothing."""
        from fikisha.jobs.constants import JobStatus
        from fikisha.jobs.models import Job

        incomplete = Job.objects.create(
            business=verified_business,
            created_by=business_actor.user,
            status=JobStatus.DRAFT,
        )
        client = client_for(business_actor.user)
        r = client.post(f"/api/v1/jobs/{incomplete.id}/submit", format="json")
        assert r.status_code == 422
        assert r.data["code"] == "required_fields_incomplete"
