"""Incidents / Disputes / Commission HTTP API (Phase 2D Step 10): the thin
adapter over ``fikisha.incidents.services`` — no resolution actor, admin
identity, or commission authority is ever accepted from the client
(brief §15-§17)."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

import pytest

pytestmark = pytest.mark.django_db


class TestIncidentReportAndRead:
    def test_a_job_party_reports_an_incident(
        self, client_for: Callable, business_owner_actor: Any, make_assigned_job: Callable
    ) -> None:
        job = make_assigned_job()
        client = client_for(business_owner_actor.user)
        r = client.post(
            f"/api/v1/jobs/{job.id}/incidents",
            {"type": "DAMAGE", "description": "carton crushed in transit"},
            format="json",
        )
        assert r.status_code == 201, r.content
        assert r.data["type"] == "DAMAGE"
        assert r.data["status"] == "OPEN"

    def test_an_unrelated_actor_cannot_report(
        self, client_for: Callable, other_business_actor: Any, make_assigned_job: Callable
    ) -> None:
        job = make_assigned_job()
        client = client_for(other_business_actor.user)
        r = client.post(f"/api/v1/jobs/{job.id}/incidents", {"type": "DAMAGE"}, format="json")
        assert r.status_code == 403

    def test_an_unrecognised_type_is_a_validation_error(
        self, client_for: Callable, business_owner_actor: Any, make_assigned_job: Callable
    ) -> None:
        job = make_assigned_job()
        client = client_for(business_owner_actor.user)
        r = client.post(
            f"/api/v1/jobs/{job.id}/incidents", {"type": "PICKUP_PROBLEM"}, format="json"
        )
        assert r.status_code == 400

    def test_the_reporter_can_read_the_incident_back(
        self, client_for: Callable, business_owner_actor: Any, make_assigned_job: Callable
    ) -> None:
        job = make_assigned_job()
        client = client_for(business_owner_actor.user)
        created = client.post(
            f"/api/v1/jobs/{job.id}/incidents", {"type": "LOSS"}, format="json"
        ).data
        r = client.get(f"/api/v1/incidents/{created['id']}")
        assert r.status_code == 200
        assert r.data["id"] == created["id"]

    def test_a_stranger_cannot_read_the_incident(
        self,
        client_for: Callable,
        business_owner_actor: Any,
        other_business_actor: Any,
        make_assigned_job: Callable,
    ) -> None:
        job = make_assigned_job()
        created = (
            client_for(business_owner_actor.user)
            .post(f"/api/v1/jobs/{job.id}/incidents", {"type": "LOSS"}, format="json")
            .data
        )
        r = client_for(other_business_actor.user).get(f"/api/v1/incidents/{created['id']}")
        assert r.status_code == 403

    def test_listing_incidents_is_scoped_to_the_job(
        self, client_for: Callable, business_owner_actor: Any, make_assigned_job: Callable
    ) -> None:
        job = make_assigned_job()
        client = client_for(business_owner_actor.user)
        client.post(f"/api/v1/jobs/{job.id}/incidents", {"type": "LOSS"}, format="json")
        r = client.get(f"/api/v1/jobs/{job.id}/incidents")
        assert r.status_code == 200
        assert len(r.data["data"]) == 1


class TestIncidentEvidenceAndStatements:
    def test_a_job_party_attaches_evidence(
        self, client_for: Callable, business_owner_actor: Any, make_assigned_job: Callable
    ) -> None:
        from django.core.files.uploadedfile import SimpleUploadedFile

        job = make_assigned_job()
        client = client_for(business_owner_actor.user)
        incident_id = client.post(
            f"/api/v1/jobs/{job.id}/incidents", {"type": "DAMAGE"}, format="json"
        ).data["id"]
        upload = SimpleUploadedFile("proof.jpg", b"\xff\xd8\xff fake", content_type="image/jpeg")
        r = client.post(
            f"/api/v1/incidents/{incident_id}/evidence",
            {"file": upload, "caption": "damaged goods"},
            format="multipart",
        )
        assert r.status_code == 201, r.content

    def test_a_disallowed_content_type_is_a_clean_422_not_a_500(
        self, client_for: Callable, business_owner_actor: Any, make_assigned_job: Callable
    ) -> None:
        """``evidence.services.store()`` raises ``EvidenceValidationError`` for
        an upload outside the per-purpose type allowlist — this must surface
        as RFC 9457 problem+json, not an unhandled 500 (brief §23)."""
        from django.core.files.uploadedfile import SimpleUploadedFile

        job = make_assigned_job()
        client = client_for(business_owner_actor.user)
        incident_id = client.post(
            f"/api/v1/jobs/{job.id}/incidents", {"type": "DAMAGE"}, format="json"
        ).data["id"]
        upload = SimpleUploadedFile(
            "malware.exe", b"MZ fake", content_type="application/x-msdownload"
        )
        r = client.post(
            f"/api/v1/incidents/{incident_id}/evidence",
            {"file": upload},
            format="multipart",
        )
        assert r.status_code == 422, r.content
        assert r["content-type"] == "application/problem+json"
        assert r.data["code"] == "evidence_validation_error"

    def test_a_job_party_adds_a_statement(
        self, client_for: Callable, business_owner_actor: Any, make_assigned_job: Callable
    ) -> None:
        job = make_assigned_job()
        client = client_for(business_owner_actor.user)
        incident_id = client.post(
            f"/api/v1/jobs/{job.id}/incidents", {"type": "DAMAGE"}, format="json"
        ).data["id"]
        r = client.post(
            f"/api/v1/incidents/{incident_id}/statements",
            {"text": "here is what happened"},
            format="json",
        )
        assert r.status_code == 201, r.content

    def test_attached_evidence_and_statements_are_readable_back_on_the_incident(
        self, client_for: Callable, business_owner_actor: Any, make_assigned_job: Callable
    ) -> None:
        """Design Phase 6 Increment 7: the Ops Officer review workspace needs
        to read back what was attached/said — previously ``evidence``/
        ``statements`` were POST-only, invisible on the incident detail."""
        from django.core.files.uploadedfile import SimpleUploadedFile

        job = make_assigned_job()
        client = client_for(business_owner_actor.user)
        incident_id = client.post(
            f"/api/v1/jobs/{job.id}/incidents", {"type": "DAMAGE"}, format="json"
        ).data["id"]
        upload = SimpleUploadedFile("proof.jpg", b"\xff\xd8\xff fake", content_type="image/jpeg")
        client.post(
            f"/api/v1/incidents/{incident_id}/evidence",
            {"file": upload, "caption": "damaged goods"},
            format="multipart",
        )
        client.post(
            f"/api/v1/incidents/{incident_id}/statements",
            {"text": "here is what happened"},
            format="json",
        )

        r = client.get(f"/api/v1/incidents/{incident_id}")
        assert r.status_code == 200, r.content
        assert len(r.data["evidence"]) == 1
        assert r.data["evidence"][0]["caption"] == "damaged goods"
        assert len(r.data["statements"]) == 1
        assert r.data["statements"][0]["text"] == "here is what happened"

    def test_attached_evidence_content_is_downloadable_by_a_party_and_refused_to_a_stranger(
        self,
        client_for: Callable,
        business_owner_actor: Any,
        other_business_actor: Any,
        make_assigned_job: Callable,
    ) -> None:
        from django.core.files.uploadedfile import SimpleUploadedFile

        job = make_assigned_job()
        client = client_for(business_owner_actor.user)
        incident_id = client.post(
            f"/api/v1/jobs/{job.id}/incidents", {"type": "DAMAGE"}, format="json"
        ).data["id"]
        upload = SimpleUploadedFile("proof.jpg", b"\xff\xd8\xff fake", content_type="image/jpeg")
        client.post(
            f"/api/v1/incidents/{incident_id}/evidence",
            {"file": upload},
            format="multipart",
        )
        # The content route is keyed by the IncidentEvidence row id, not the
        # underlying EvidenceObject id — re-fetch the incident to get it.
        evidence_row_id = client.get(f"/api/v1/incidents/{incident_id}").data["evidence"][0]["id"]

        r = client.get(f"/api/v1/incidents/evidence/{evidence_row_id}/content")
        assert r.status_code == 200, r.content
        assert r["content-type"] == "image/jpeg"

        stranger = client_for(other_business_actor.user)
        r = stranger.get(f"/api/v1/incidents/evidence/{evidence_row_id}/content")
        assert r.status_code == 403


class TestIncidentReviewAndEscalate:
    def test_ops_officer_starts_review(
        self,
        client_for: Callable,
        business_owner_actor: Any,
        ops_actor: Any,
        make_assigned_job: Callable,
    ) -> None:
        job = make_assigned_job()
        incident_id = (
            client_for(business_owner_actor.user)
            .post(f"/api/v1/jobs/{job.id}/incidents", {"type": "DAMAGE"}, format="json")
            .data["id"]
        )
        r = client_for(ops_actor.user).post(
            f"/api/v1/incidents/{incident_id}/review", {}, format="json"
        )
        assert r.status_code == 200
        assert r.data["status"] == "UNDER_REVIEW"

    def test_a_business_party_may_not_start_review(
        self, client_for: Callable, business_owner_actor: Any, make_assigned_job: Callable
    ) -> None:
        job = make_assigned_job()
        client = client_for(business_owner_actor.user)
        incident_id = client.post(
            f"/api/v1/jobs/{job.id}/incidents", {"type": "DAMAGE"}, format="json"
        ).data["id"]
        r = client.post(f"/api/v1/incidents/{incident_id}/review", {}, format="json")
        assert r.status_code == 403

    def test_only_platform_admin_may_escalate(
        self,
        client_for: Callable,
        business_owner_actor: Any,
        ops_actor: Any,
        admin_actor: Any,
        make_assigned_job: Callable,
    ) -> None:
        job = make_assigned_job()
        incident_id = (
            client_for(business_owner_actor.user)
            .post(f"/api/v1/jobs/{job.id}/incidents", {"type": "DAMAGE"}, format="json")
            .data["id"]
        )

        r = client_for(ops_actor.user).post(
            f"/api/v1/incidents/{incident_id}/escalate", {"reason": "trying anyway"}, format="json"
        )
        assert r.status_code == 403

        r = client_for(admin_actor.user).post(
            f"/api/v1/incidents/{incident_id}/escalate",
            {"reason": "critical — advising the founder"},
            format="json",
        )
        assert r.status_code == 201, r.content


class TestDisputeOpenAndResolve:
    def test_business_opens_a_dispute_and_admin_resolves_it(
        self,
        client_for: Callable,
        business_owner_actor: Any,
        admin_actor: Any,
        make_assigned_job: Callable,
    ) -> None:
        job = make_assigned_job()
        biz_client = client_for(business_owner_actor.user)
        incident_id = biz_client.post(
            f"/api/v1/jobs/{job.id}/incidents", {"type": "BREAKDOWN"}, format="json"
        ).data["id"]

        r = biz_client.post(
            f"/api/v1/jobs/{job.id}/disputes", {"incident_ids": [incident_id]}, format="json"
        )
        assert r.status_code == 201, r.content
        dispute_id = r.data["dispute"]["id"]
        assert r.data["job"]["status"] == "DISPUTED"

        admin_client = client_for(admin_actor.user)
        r = admin_client.post(
            f"/api/v1/disputes/{dispute_id}/resolve",
            {
                "outcome_code": "AMICABLE_AGREEMENT",
                "rationale": "resolved amicably between the parties",
                "routed_job_status": "CANCELLED",
                "commission_treatment": "APPLY",
            },
            format="json",
        )
        assert r.status_code == 200, r.content
        assert r.data["job"]["status"] == "CANCELLED"

    def test_a_non_admin_cannot_resolve(
        self, client_for: Callable, business_owner_actor: Any, make_assigned_job: Callable
    ) -> None:
        job = make_assigned_job()
        biz_client = client_for(business_owner_actor.user)
        incident_id = biz_client.post(
            f"/api/v1/jobs/{job.id}/incidents", {"type": "BREAKDOWN"}, format="json"
        ).data["id"]
        dispute_id = biz_client.post(
            f"/api/v1/jobs/{job.id}/disputes", {"incident_ids": [incident_id]}, format="json"
        ).data["dispute"]["id"]

        r = biz_client.post(
            f"/api/v1/disputes/{dispute_id}/resolve",
            {
                "outcome_code": "AMICABLE_AGREEMENT",
                "rationale": "trying to self-resolve",
                "routed_job_status": "CANCELLED",
            },
            format="json",
        )
        assert r.status_code == 403

    def test_only_platform_admin_may_reduce_commission_on_resolution(
        self,
        client_for: Callable,
        business_owner_actor: Any,
        ops_actor: Any,
        delivered_job: Callable,
        complete_job: Callable,
    ) -> None:
        job = delivered_job()
        complete_job(job)
        biz_client = client_for(business_owner_actor.user)
        incident_id = biz_client.post(
            f"/api/v1/jobs/{job.id}/incidents", {"type": "DAMAGE"}, format="json"
        ).data["id"]
        dispute_id = biz_client.post(
            f"/api/v1/jobs/{job.id}/disputes", {"incident_ids": [incident_id]}, format="json"
        ).data["dispute"]["id"]

        r = client_for(ops_actor.user).post(
            f"/api/v1/disputes/{dispute_id}/resolve",
            {
                "outcome_code": "ADMIN_DETERMINATION",
                "rationale": "Ops Officer attempting to waive commission",
                "routed_job_status": "COMPLETED",
                "commission_treatment": "WAIVE",
            },
            format="json",
        )
        assert r.status_code == 403
        assert r.data["code"] == "not_authorised_for_commission_adjustment"


class TestCommissionRead:
    def test_platform_admin_reads_the_commission_record(
        self,
        client_for: Callable,
        admin_actor: Any,
        delivered_job: Callable,
        complete_job: Callable,
    ) -> None:
        job = delivered_job()
        complete_job(job)
        client = client_for(admin_actor.user)
        r = client.get(f"/api/v1/jobs/{job.id}/commission")
        assert r.status_code == 200, r.content
        assert r.data["commission_kes"] > 0

    def test_a_business_cannot_read_the_commission_record(
        self,
        client_for: Callable,
        business_owner_actor: Any,
        delivered_job: Callable,
        complete_job: Callable,
    ) -> None:
        job = delivered_job()
        complete_job(job)
        client = client_for(business_owner_actor.user)
        r = client.get(f"/api/v1/jobs/{job.id}/commission")
        assert r.status_code == 403

    def test_no_commission_exists_before_completion(
        self, client_for: Callable, admin_actor: Any, make_assigned_job: Callable
    ) -> None:
        job = make_assigned_job()
        client = client_for(admin_actor.user)
        r = client.get(f"/api/v1/jobs/{job.id}/commission")
        assert r.status_code == 404
