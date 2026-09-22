"""Recipient scoped HTTP API (Phase 2D Step 10): the bearer-token-in-URL
boundary — minimal disclosure, brute-force throttling, and concurrent
confirmation (brief §9-§13/§22)."""

from __future__ import annotations

import threading
from collections.abc import Callable
from typing import Any

import pytest
from django.core.cache import cache
from django.db import connection
from rest_framework.test import APIClient

pytestmark = pytest.mark.django_db


@pytest.fixture(autouse=True)
def _clear_ratelimit_cache() -> None:
    cache.clear()


@pytest.fixture
def at_destination(
    client_for: Callable, driver_actor: Any, make_assigned_job: Callable
) -> Callable[..., tuple[Any, str]]:
    def _make() -> tuple[Any, str]:
        job = make_assigned_job()
        client = client_for(driver_actor.user)
        client.post(f"/api/v1/jobs/{job.id}/custody/arrive-pickup", format="json")
        client.post(
            f"/api/v1/jobs/{job.id}/custody/confirm-pickup/otp", {"code": "000000"}, format="json"
        )
        client.post(f"/api/v1/jobs/{job.id}/custody/start-transit", format="json")
        r = client.post(f"/api/v1/jobs/{job.id}/custody/arrive-destination", format="json")
        token = r.data["recipient_link_token"]
        assert token
        return job, token

    return _make


class TestRecipientView:
    def test_the_link_exposes_the_minimal_disclosure_field_set(
        self, api: APIClient, at_destination: Callable
    ) -> None:
        _job, token = at_destination()
        r = api.get(f"/api/v1/r/{token}")
        assert r.status_code == 200, r.content
        expected_keys = {
            "delivery_reference",
            "recipient_display_name",
            "cargo_summary",
            "status",
            "status_label",
            "driver_first_name",
            "vehicle_class",
            "vehicle_plate",
            "operator_identity_verified",
            "allowed_actions",
        }
        assert set(r.data.keys()) == expected_keys
        dump = str(r.data).lower()
        for forbidden in ("phone", "+2547", "declared_value", "value_band", "trust"):
            assert forbidden not in dump, forbidden

    def test_an_unknown_token_is_404(self, api: APIClient) -> None:
        r = api.get("/api/v1/r/not-a-real-token")
        assert r.status_code == 404

    def test_token_resolution_needs_no_session_auth(
        self, api: APIClient, at_destination: Callable
    ) -> None:
        """``api`` never calls ``.credentials()`` — no ``Authorization`` header
        is ever sent; the link itself is the only credential this needs."""
        _job, token = at_destination()
        r = api.get(f"/api/v1/r/{token}")
        assert r.status_code == 200


class TestRecipientTokenBruteForce:
    def test_repeated_bad_tokens_from_one_ip_are_eventually_rate_limited(
        self, api: APIClient
    ) -> None:
        statuses = [api.get("/api/v1/r/guess-a-token").status_code for _ in range(25)]
        assert 404 in statuses
        assert 429 in statuses, statuses


class TestRecipientConfirm:
    def test_recipient_confirms_receipt_with_the_real_otp(
        self, api: APIClient, at_destination: Callable
    ) -> None:
        job, token = at_destination()
        r = api.post(
            f"/api/v1/r/{token}/confirm",
            {"code": "000000", "party_name": "A. Recipient"},
            format="json",
        )
        assert r.status_code == 200, r.content
        assert r.data["status"] == "DELIVERED"

    def test_a_wrong_otp_is_rejected(self, api: APIClient, at_destination: Callable) -> None:
        _job, token = at_destination()
        r = api.post(
            f"/api/v1/r/{token}/confirm",
            {"code": "999999", "party_name": "A. Recipient"},
            format="json",
        )
        assert r.status_code == 422

    def test_a_used_link_cannot_confirm_again(
        self, api: APIClient, at_destination: Callable
    ) -> None:
        _job, token = at_destination()
        api.post(
            f"/api/v1/r/{token}/confirm",
            {"code": "000000", "party_name": "A. Recipient"},
            format="json",
        )
        r = api.post(
            f"/api/v1/r/{token}/confirm",
            {"code": "000000", "party_name": "A. Recipient"},
            format="json",
        )
        assert r.status_code == 403

    def test_a_revoked_link_is_gone(self, api: APIClient, at_destination: Callable) -> None:
        from fikisha.jobs import recipient as recipient_service

        job, token = at_destination()
        recipient_service.reissue_link(job_id=job.id)
        r = api.get(f"/api/v1/r/{token}")
        assert r.status_code == 404


class TestRecipientReportIssue:
    def test_recipient_reports_an_issue_with_a_curated_category(
        self, api: APIClient, at_destination: Callable
    ) -> None:
        _job, token = at_destination()
        r = api.post(
            f"/api/v1/r/{token}/report-issue",
            {"category": "DAMAGE", "description": "box was crushed"},
            format="json",
        )
        assert r.status_code == 201, r.content

    def test_an_uncurated_category_is_rejected(
        self, api: APIClient, at_destination: Callable
    ) -> None:
        _job, token = at_destination()
        r = api.post(f"/api/v1/r/{token}/report-issue", {"category": "MADE_UP"}, format="json")
        assert r.status_code == 400

    def test_a_photo_attached_to_a_report_is_stored_as_incident_evidence(
        self, api: APIClient, at_destination: Callable
    ) -> None:
        from django.core.files.uploadedfile import SimpleUploadedFile

        from fikisha.evidence.models import EvidenceObject, EvidencePurpose, UploaderKind
        from fikisha.jobs.models import RecipientReportedIssue

        _job, token = at_destination()
        upload = SimpleUploadedFile("damage.jpg", b"\xff\xd8\xff fake", content_type="image/jpeg")
        r = api.post(
            f"/api/v1/r/{token}/report-issue",
            {"category": "DAMAGE", "description": "box was crushed", "photos": [upload]},
            format="multipart",
        )
        assert r.status_code == 201, r.content

        report = RecipientReportedIssue.objects.get(id=r.data["report_id"])
        assert len(report.photo_evidence_ids) == 1
        evidence = EvidenceObject.objects.get(id=report.photo_evidence_ids[0])
        assert evidence.purpose == EvidencePurpose.INCIDENT_EVIDENCE
        assert evidence.uploaded_by_kind == UploaderKind.RECIPIENT


@pytest.mark.django_db(transaction=True)
def test_concurrent_recipient_confirmations_produce_exactly_one_delivery(
    client_for: Callable, driver_actor: Any, make_assigned_job: Callable
) -> None:
    """The mandatory-style Step 10 concurrency regression, recipient side:
    the scoped link's ``used_at`` + the OTP challenge's single-use consumption
    together must serialise concurrent HTTP confirmations to exactly one
    success — through the real HTTP stack."""
    job = make_assigned_job()
    client = client_for(driver_actor.user)
    client.post(f"/api/v1/jobs/{job.id}/custody/arrive-pickup", format="json")
    client.post(
        f"/api/v1/jobs/{job.id}/custody/confirm-pickup/otp", {"code": "000000"}, format="json"
    )
    client.post(f"/api/v1/jobs/{job.id}/custody/start-transit", format="json")
    r = client.post(f"/api/v1/jobs/{job.id}/custody/arrive-destination", format="json")
    token = r.data["recipient_link_token"]

    results: list[int] = []
    lock = threading.Lock()

    def _confirm() -> None:
        try:
            api: APIClient = APIClient()
            resp = api.post(
                f"/api/v1/r/{token}/confirm",
                {"code": "000000", "party_name": "A. Recipient"},
                format="json",
            )
            with lock:
                results.append(resp.status_code)
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

    assert Job.objects.get(id=job.id).status == "DELIVERED"
