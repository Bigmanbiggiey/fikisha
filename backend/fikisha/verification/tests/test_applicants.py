"""Verification queue by applicant (assessment 2026-10-19, part 5)."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile

pytestmark = pytest.mark.django_db


def _png() -> SimpleUploadedFile:
    return SimpleUploadedFile("doc.png", b"\x89PNG\r\n\x1a\nfake", content_type="image/png")


def _submit(client: Any, subject_type: str, subject_id: str, domain: str, kind: str) -> str:
    r = client.post(
        "/api/v1/verification/records",
        {"subject_type": subject_type, "subject_id": subject_id, "domain": domain},
        format="json",
    )
    assert r.status_code == 201, r.content
    rid = str(r.data["id"])
    up = client.post(
        f"/api/v1/verification/records/{rid}/evidence",
        {"file": _png(), "kind": kind},
        format="multipart",
    )
    assert up.status_code == 201, up.content
    assert (
        client.post(f"/api/v1/verification/records/{rid}/submit", {}, format="json").status_code
        == 200
    )
    return rid


@pytest.fixture
def ops_client(ops_officer: Any, client_for: Callable) -> Any:
    return client_for(ops_officer)


@pytest.fixture
def operator_with_vehicle(user: Any, client_for: Callable) -> dict[str, Any]:
    """A new (PENDING) operator who submitted their ID and a vehicle logbook."""
    client = client_for(user)
    op_id = str(
        client.post("/api/v1/operators", {"full_name": "Wanjiku"}, format="json").data["id"]
    )
    v = client.post(
        "/api/v1/vehicles",
        {
            "owner_operator_id": op_id,
            "vehicle_class": "PICKUP",
            "registration": "kda 500x",
            "capacity_value": "500.00",
            "capacity_unit": "KG",
        },
        format="json",
    )
    assert v.status_code == 201, v.content
    return {
        "client": client,
        "operator_id": op_id,
        "vehicle_id": str(v.data["id"]),
        "id_record": _submit(client, "OPERATOR", op_id, "IDENTITY", "NATIONAL_ID"),
        "logbook_record": _submit(client, "VEHICLE", str(v.data["id"]), "VEHICLE", "LOGBOOK"),
    }


class TestApplicantList:
    def test_one_row_per_operator_with_their_vehicle_records_counted(
        self, ops_client: Any, operator_with_vehicle: dict[str, Any]
    ) -> None:
        r = ops_client.get("/api/v1/verification/applicants?kind=OPERATOR")
        assert r.status_code == 200, r.content
        rows = [row for row in r.data["data"] if row["id"] == operator_with_vehicle["operator_id"]]
        assert len(rows) == 1
        row = rows[0]
        assert row["status"] == "PENDING"
        assert row["open_count"] == 2  # their ID + their vehicle's logbook
        assert row["required_count"] == 3
        assert row["verified_count"] == 0

    def test_businesses_and_groups_have_their_own_tab(
        self, ops_client: Any, user: Any, client_for: Callable
    ) -> None:
        client = client_for(user)
        bid = str(
            client.post("/api/v1/businesses", {"trading_name": "Duka"}, format="json").data["id"]
        )
        businesses = ops_client.get("/api/v1/verification/applicants?kind=BUSINESS").data["data"]
        assert [b["id"] for b in businesses] == [bid]
        assert ops_client.get("/api/v1/verification/applicants?kind=GROUP").data["data"] == []
        assert ops_client.get("/api/v1/verification/applicants?kind=NOPE").status_code == 400

    def test_a_pending_operator_with_nothing_submitted_still_appears(
        self, ops_client: Any, user: Any, client_for: Callable
    ) -> None:
        op_id = str(
            client_for(user)
            .post("/api/v1/operators", {"full_name": "New"}, format="json")
            .data["id"]
        )
        rows = ops_client.get("/api/v1/verification/applicants?kind=OPERATOR").data["data"]
        row = next(r for r in rows if r["id"] == op_id)
        assert row["open_count"] == 0

    def test_only_reviewers_see_the_queue(
        self, client_for: Callable, make_user: Callable, operator_with_vehicle: dict[str, Any]
    ) -> None:
        stranger = client_for(make_user("+254700777301"))
        assert stranger.get("/api/v1/verification/applicants?kind=OPERATOR").status_code == 403
        # Not even the applicant: the grouped view is a reviewer screen.
        own = operator_with_vehicle["client"]
        op_id = operator_with_vehicle["operator_id"]
        assert own.get(f"/api/v1/verification/applicants/OPERATOR/{op_id}").status_code == 403


class TestApplicantDetail:
    def test_records_are_grouped_under_the_operator_and_their_vehicle(
        self, ops_client: Any, operator_with_vehicle: dict[str, Any]
    ) -> None:
        op_id = operator_with_vehicle["operator_id"]
        r = ops_client.get(f"/api/v1/verification/applicants/OPERATOR/{op_id}")
        assert r.status_code == 200, r.content
        assert [rec["id"] for rec in r.data["records"]] == [operator_with_vehicle["id_record"]]
        assert r.data["records"][0]["evidence"][0]["kind"] == "NATIONAL_ID"
        assert r.data["records"][0]["decisions"][0]["action"] == "SUBMIT"
        (vehicle,) = r.data["vehicles"]
        assert vehicle["registration"] == "KDA 500X"
        assert [rec["id"] for rec in vehicle["records"]] == [
            operator_with_vehicle["logbook_record"]
        ]
        assert {req["domain"] for req in r.data["requirements"] if req["mandatory"]} == {
            "IDENTITY",
            "LICENCE",
            "GOOD_CONDUCT",
        }

    def test_business_detail_carries_its_locations(
        self, ops_client: Any, user: Any, client_for: Callable
    ) -> None:
        client = client_for(user)
        bid = str(
            client.post("/api/v1/businesses", {"trading_name": "Duka"}, format="json").data["id"]
        )
        client.post(
            f"/api/v1/businesses/{bid}/locations",
            {"label": "Shop", "type": "MAIN", "address_text": "Namanga Rd"},
            format="json",
        )
        r = ops_client.get(f"/api/v1/verification/applicants/BUSINESS/{bid}")
        assert r.status_code == 200, r.content
        assert r.data["status"] == "UNVERIFIED"
        assert [loc["label"] for loc in r.data["locations"]] == ["Shop"]
        assert [rec["domain"] for rec in r.data["records"]] == ["BUSINESS"]

    def test_unknown_applicant_is_404(self, ops_client: Any) -> None:
        r = ops_client.get(
            "/api/v1/verification/applicants/OPERATOR/0190f2a0-0000-7000-8000-000000000000"
        )
        assert r.status_code == 404
