"""Verification API — submit / review / evidence access (Phase 2C §24, §26, §28)."""

from __future__ import annotations

from typing import Any

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile

pytestmark = pytest.mark.django_db


def _png(name: str = "doc.png") -> SimpleUploadedFile:
    return SimpleUploadedFile(name, b"\x89PNG\r\n\x1a\n" + b"fakebytes", content_type="image/png")


def _operator(client: Any, name: str = "Op") -> str:
    return client.post("/api/v1/operators", {"full_name": name}, format="json").data["id"]


def _submit_identity(client: Any, operator_id: str) -> str:
    r = client.post(
        "/api/v1/verification/records",
        {"subject_type": "OPERATOR", "subject_id": operator_id, "domain": "IDENTITY"},
        format="json",
    )
    assert r.status_code == 201, r.content
    rid = r.data["id"]
    up = client.post(
        f"/api/v1/verification/records/{rid}/evidence",
        {"file": _png(), "kind": "NATIONAL_ID"},
        format="multipart",
    )
    assert up.status_code == 201, up.content
    sub = client.post(f"/api/v1/verification/records/{rid}/submit", {}, format="json")
    assert sub.status_code == 200, sub.content
    assert sub.data["state"] == "SUBMITTED"
    return rid


@pytest.fixture
def ops_client(ops_officer: Any, client_for: Any) -> Any:
    return client_for(ops_officer)


class TestSubmitAndReview:
    def test_operator_submits_and_ops_officer_approves(
        self, user: Any, client_for: Any, ops_client: Any
    ) -> None:
        op_client = client_for(user)
        pid = _operator(op_client)
        rid = _submit_identity(op_client, pid)

        # it appears in the reviewer's queue
        queue = ops_client.get("/api/v1/verification/queue")
        assert any(r["id"] == rid for r in queue.data["data"])

        assert (
            ops_client.post(
                f"/api/v1/verification/records/{rid}/review/start", {}, format="json"
            ).status_code
            == 200
        )
        appr = ops_client.post(
            f"/api/v1/verification/records/{rid}/review/approve",
            {"reason": "clear"},
            format="json",
        )
        assert appr.status_code == 200
        assert appr.data["state"] == "VERIFIED"

    def test_operator_cannot_approve_their_own(self, user: Any, client_for: Any) -> None:
        op_client = client_for(user)
        pid = _operator(op_client)
        rid = _submit_identity(op_client, pid)
        # the operator has no verification.decide permission -> 403
        assert (
            op_client.post(
                f"/api/v1/verification/records/{rid}/review/start", {}, format="json"
            ).status_code
            == 403
        )

    def test_business_user_cannot_review(self, user: Any, other_user: Any, client_for: Any) -> None:
        op_client = client_for(user)
        pid = _operator(op_client)
        rid = _submit_identity(op_client, pid)
        biz_client = client_for(other_user)
        biz_client.post("/api/v1/businesses", {"trading_name": "Biz"}, format="json")
        assert (
            biz_client.post(
                f"/api/v1/verification/records/{rid}/review/approve", {}, format="json"
            ).status_code
            == 403
        )

    def test_subject_status_endpoint(self, user: Any, client_for: Any, ops_client: Any) -> None:
        op_client = client_for(user)
        pid = _operator(op_client)
        rid = _submit_identity(op_client, pid)
        ops_client.post(f"/api/v1/verification/records/{rid}/review/start", {}, format="json")
        ops_client.post(f"/api/v1/verification/records/{rid}/review/approve", {}, format="json")
        r = op_client.get(f"/api/v1/verification/subjects/OPERATOR/{pid}/status")
        assert r.status_code == 200
        assert r.data["eligibility"]["IDENTITY"] == "VERIFIED"
        assert "IDENTITY" in r.data["required_domains"]


class TestEvidenceAccess:
    def test_owner_and_reviewer_can_fetch_evidence_others_cannot(
        self, user: Any, other_user: Any, client_for: Any, ops_client: Any
    ) -> None:
        op_client = client_for(user)
        pid = _operator(op_client)
        rid = _submit_identity(op_client, pid)
        detail = op_client.get(f"/api/v1/verification/records/{rid}")
        ev_id = detail.data["evidence"][0]["id"]
        url = f"/api/v1/verification/evidence/{ev_id}/content"

        assert op_client.get(url).status_code == 200  # the owner
        assert ops_client.get(url).status_code == 200  # a reviewer

        stranger = client_for(other_user)
        _operator(stranger, "Stranger")
        assert stranger.get(url).status_code == 403  # someone else

    def test_high_pii_fetch_is_access_logged(
        self, user: Any, client_for: Any, ops_client: Any
    ) -> None:
        from fikisha.evidence.models import EvidenceAccessLog

        op_client = client_for(user)
        pid = _operator(op_client)
        rid = _submit_identity(op_client, pid)
        ev_id = op_client.get(f"/api/v1/verification/records/{rid}").data["evidence"][0]["id"]
        ops_client.get(f"/api/v1/verification/evidence/{ev_id}/content")
        assert EvidenceAccessLog.objects.filter(evidence_object__isnull=False).exists()


class TestUnauthenticated:
    def test_records_list_requires_auth(self, api: Any) -> None:
        assert api.get("/api/v1/verification/records").status_code == 401

    def test_queue_requires_permission(self, user: Any, client_for: Any) -> None:
        # an authenticated ordinary operator is not a reviewer
        assert client_for(user).get("/api/v1/verification/queue").status_code == 403
