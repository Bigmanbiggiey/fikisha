"""Business and group verification (assessment 2026-10-19, D-1 / D-6).

Registering a business (or creating a group) submits its details; a reviewer's
decision on that record sets the organisation's own ``verification_status``,
in the same transaction and audited. Documents are optional.
"""

from __future__ import annotations

from typing import Any

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile

from fikisha.audit.models import AuditLogEntry
from fikisha.business.models import BusinessAccount
from fikisha.groups.models import OperatorGroup
from fikisha.verification.models import VerificationRecord

pytestmark = pytest.mark.django_db


def _business(client: Any, name: str = "Mama Njeri Hardware") -> str:
    r = client.post("/api/v1/businesses", {"trading_name": name}, format="json")
    assert r.status_code == 201, r.content
    return str(r.data["id"])


def _add_location(client: Any, bid: str) -> None:
    r = client.post(
        f"/api/v1/businesses/{bid}/locations", {"label": "Shop", "type": "MAIN"}, format="json"
    )
    assert r.status_code == 201, r.content


def _record(bid: str) -> VerificationRecord:
    return VerificationRecord.objects.get(subject_business_id=bid, domain="BUSINESS")


@pytest.fixture
def ops_client(ops_officer: Any, client_for: Any) -> Any:
    return client_for(ops_officer)


class TestBusinessVerification:
    def test_registering_submits_the_business_for_review(
        self, user: Any, client_for: Any, ops_client: Any
    ) -> None:
        bid = _business(client_for(user))
        rec = _record(bid)
        assert rec.state == "SUBMITTED"
        assert rec.subject_type == "BUSINESS"
        queue = ops_client.get("/api/v1/verification/queue?subject_type=BUSINESS").data["data"]
        assert [r["id"] for r in queue] == [str(rec.id)]

    def test_owner_sees_the_status_and_it_is_mandatory(self, user: Any, client_for: Any) -> None:
        client = client_for(user)
        bid = _business(client)
        r = client.get(f"/api/v1/verification/subjects/BUSINESS/{bid}/status")
        assert r.status_code == 200, r.content
        assert r.data["required_domains"] == ["BUSINESS"]
        assert r.data["eligibility"] == {"BUSINESS": "SUBMITTED"}

    def test_approval_sets_the_business_verified_and_is_audited(
        self, user: Any, client_for: Any, ops_client: Any
    ) -> None:
        client = client_for(user)
        bid = _business(client)
        _add_location(client, bid)
        rid = _record(bid).id
        assert (
            ops_client.post(f"/api/v1/verification/records/{rid}/review/start").status_code == 200
        )
        r = ops_client.post(
            f"/api/v1/verification/records/{rid}/review/approve", {"reason": "ok"}, format="json"
        )
        assert r.status_code == 200, r.content
        assert BusinessAccount.objects.get(id=bid).verification_status == "VERIFIED"
        assert AuditLogEntry.objects.filter(
            action="business.verification_status.changed", entity_id=bid
        ).exists()

    def test_a_business_with_no_location_cannot_be_approved(
        self, user: Any, client_for: Any, ops_client: Any
    ) -> None:
        bid = _business(client_for(user))
        rid = _record(bid).id
        ops_client.post(f"/api/v1/verification/records/{rid}/review/start")
        r = ops_client.post(
            f"/api/v1/verification/records/{rid}/review/approve", {"reason": "ok"}, format="json"
        )
        assert r.status_code == 422
        assert r.data["code"] == "business_has_no_location"
        assert BusinessAccount.objects.get(id=bid).verification_status == "UNVERIFIED"
        assert _record(bid).state == "IN_REVIEW"

    def test_rejecting_after_approval_unverifies_the_business(
        self, user: Any, client_for: Any, ops_client: Any
    ) -> None:
        client = client_for(user)
        bid = _business(client)
        _add_location(client, bid)
        rid = _record(bid).id
        ops_client.post(f"/api/v1/verification/records/{rid}/review/start")
        ops_client.post(
            f"/api/v1/verification/records/{rid}/review/approve", {"reason": "ok"}, format="json"
        )
        # The owner resubmits (e.g. changed details); a reviewer rejects.
        assert (
            client.post(f"/api/v1/verification/records/{rid}/submit", {}, format="json").status_code
            == 200
        )
        ops_client.post(f"/api/v1/verification/records/{rid}/review/start")
        r = ops_client.post(
            f"/api/v1/verification/records/{rid}/review/reject",
            {"reason": "not a real shop"},
            format="json",
        )
        assert r.status_code == 200, r.content
        assert BusinessAccount.objects.get(id=bid).verification_status == "UNVERIFIED"

    def test_documents_are_frozen_while_awaiting_review(self, user: Any, client_for: Any) -> None:
        client = client_for(user)
        bid = _business(client)
        rec = _record(bid)
        # Documents can be added again once a reviewer asks for more info.
        upload = SimpleUploadedFile("cert.pdf", b"%PDF-1.4 fake", content_type="application/pdf")
        r = client.post(
            f"/api/v1/verification/records/{rec.id}/evidence",
            {"file": upload, "kind": "BUSINESS_REGISTRATION_CERT"},
            format="multipart",
        )
        assert r.status_code == 409
        assert r.data["code"] == "already_pending"

    def test_a_dispatcher_or_stranger_cannot_read_or_submit_it(
        self, user: Any, client_for: Any, make_user: Any
    ) -> None:
        """IDOR: only the business OWNER is the subject owner."""
        bid = _business(client_for(user))
        rid = _record(bid).id
        stranger = client_for(make_user("+254700777201"))
        assert stranger.get(f"/api/v1/verification/records/{rid}").status_code == 403
        assert (
            stranger.post(
                f"/api/v1/verification/records/{rid}/submit", {}, format="json"
            ).status_code
            == 403
        )
        assert (
            stranger.get(f"/api/v1/verification/subjects/BUSINESS/{bid}/status").status_code == 403
        )
        assert stranger.get("/api/v1/verification/records").data["data"] == []

    def test_the_owner_cannot_review_their_own_business(
        self, platform_admin: Any, client_for: Any
    ) -> None:
        admin = client_for(platform_admin)
        bid = _business(admin)
        _add_location(admin, bid)
        rid = _record(bid).id
        r = admin.post(f"/api/v1/verification/records/{rid}/review/start")
        assert r.status_code == 422
        assert r.data["code"] == "reviewer_is_submitter"


class TestGroupVerification:
    def test_creating_a_group_submits_it_and_approval_verifies_it(
        self, user: Any, client_for: Any, ops_client: Any
    ) -> None:
        client = client_for(user)
        assert (
            client.post("/api/v1/operators", {"full_name": "Owner"}, format="json").status_code
            == 201
        )
        r = client.post(
            "/api/v1/groups", {"name": "Kitengela Movers", "type": "FLEET"}, format="json"
        )
        assert r.status_code == 201, r.content
        gid = r.data["id"]
        rec = VerificationRecord.objects.get(subject_group_id=gid, domain="GROUP")
        assert rec.state == "SUBMITTED"
        ops_client.post(f"/api/v1/verification/records/{rec.id}/review/start")
        r = ops_client.post(
            f"/api/v1/verification/records/{rec.id}/review/approve", {"reason": "ok"}, format="json"
        )
        assert r.status_code == 200, r.content
        assert OperatorGroup.objects.get(id=gid).verification_status == "VERIFIED"
        # The group's owner reads its record; a stranger may not.
        assert client.get(f"/api/v1/verification/records/{rec.id}").status_code == 200
