"""Phase 2C required end-to-end smoke flow (brief §38).

operator + individual vehicle -> group + group vehicle -> group owner manages /
driver cannot -> submit operator verification -> PENDING -> self-approval fails
-> Operations Officer approves -> history intact -> submit + approve vehicle
verification -> evidence access restricted -> audit chain verifies -> cross-org
access fails -> expiry + replacement/history.
"""

from __future__ import annotations

from datetime import timedelta
from typing import Any

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.utils import timezone

from fikisha.audit.services import verify_chain

pytestmark = pytest.mark.django_db


def _png() -> SimpleUploadedFile:
    return SimpleUploadedFile("d.png", b"\x89PNG\r\n\x1a\nx", content_type="image/png")


def _submit(client: Any, subject_type: str, subject_id: str, domain: str, kind: str) -> str:
    rid = client.post(
        "/api/v1/verification/records",
        {"subject_type": subject_type, "subject_id": subject_id, "domain": domain},
        format="json",
    ).data["id"]
    assert (
        client.post(
            f"/api/v1/verification/records/{rid}/evidence",
            {"file": _png(), "kind": kind},
            format="multipart",
        ).status_code
        == 201
    )
    assert (
        client.post(f"/api/v1/verification/records/{rid}/submit", {}, format="json").data["state"]
        == "SUBMITTED"
    )
    return rid


def _approve(reviewer: Any, rid: str, **body: Any) -> Any:
    assert (
        reviewer.post(
            f"/api/v1/verification/records/{rid}/review/start", {}, format="json"
        ).status_code
        == 200
    )
    return reviewer.post(f"/api/v1/verification/records/{rid}/review/approve", body, format="json")


def test_phase_2c_smoke(make_user: Any, client_for: Any, ops_officer: Any) -> None:
    op_user = make_user("+254700300001")
    driver_user = make_user("+254700300002")
    other_user = make_user("+254700300009")
    op = client_for(op_user)
    reviewer = client_for(ops_officer)

    # 1-3. operator + individual vehicle
    op_pid = op.post("/api/v1/operators", {"full_name": "Sam Operator"}, format="json").data["id"]
    v1 = op.post(
        "/api/v1/vehicles",
        {
            "owner_operator_id": op_pid,
            "vehicle_class": "PICKUP",
            "registration": "KDA 100A",
            "capacity_value": "900",
        },
        format="json",
    )
    assert v1.status_code == 201
    assert any(row["id"] == v1.data["id"] for row in op.get("/api/v1/vehicles").data["data"])

    # 4-7. group + group vehicle; owner manages, driver cannot
    gid = op.post(
        "/api/v1/groups", {"name": "Kitengela Fleet", "type": "FLEET"}, format="json"
    ).data["id"]
    gv = op.post(
        "/api/v1/vehicles",
        {
            "owner_group_id": gid,
            "vehicle_class": "LORRY",
            "registration": "KDB 200B",
            "capacity_value": "8",
            "capacity_unit": "TONNES",
        },
        format="json",
    )
    assert gv.status_code == 201 and gv.data["vehicle_class_heavy"] is True
    driver = client_for(driver_user)
    d_pid = driver.post("/api/v1/operators", {"full_name": "Dan Driver"}, format="json").data["id"]
    op.post(
        f"/api/v1/groups/{gid}/members", {"operator_id": d_pid, "role": "DRIVER"}, format="json"
    )
    assert (
        op.patch(f"/api/v1/vehicles/{gv.data['id']}", {"make": "Isuzu"}, format="json").status_code
        == 200
    )
    assert driver.get(f"/api/v1/vehicles/{gv.data['id']}").status_code == 200
    assert (
        driver.patch(
            f"/api/v1/vehicles/{gv.data['id']}", {"make": "Hijack"}, format="json"
        ).status_code
        == 403
    )

    # 8-13. operator IDENTITY verification: submit -> pending -> self-approve fails -> approve
    id_rid = _submit(op, "OPERATOR", op_pid, "IDENTITY", "NATIONAL_ID")
    assert (
        op.post(
            f"/api/v1/verification/records/{id_rid}/review/start", {}, format="json"
        ).status_code
        == 403
    )
    assert _approve(reviewer, id_rid, reason="clear").data["state"] == "VERIFIED"
    detail = reviewer.get(f"/api/v1/verification/records/{id_rid}").data
    assert [d["action"] for d in detail["decisions"]] == ["SUBMIT", "START_REVIEW", "APPROVE"]

    # 14-16. vehicle VEHICLE verification + restricted evidence access
    veh_rid = _submit(op, "VEHICLE", v1.data["id"], "VEHICLE", "LOGBOOK")
    _approve(reviewer, veh_rid, expires_at=(timezone.now() + timedelta(days=365)).isoformat())
    ev_id = op.get(f"/api/v1/verification/records/{veh_rid}").data["evidence"][0]["id"]
    stranger = client_for(other_user)
    stranger.post("/api/v1/operators", {"full_name": "Nosy"}, format="json")
    assert op.get(f"/api/v1/verification/evidence/{ev_id}/content").status_code == 200
    assert reviewer.get(f"/api/v1/verification/evidence/{ev_id}/content").status_code == 200
    assert stranger.get(f"/api/v1/verification/evidence/{ev_id}/content").status_code == 403

    # 17. audit chain verifies
    assert verify_chain() == []

    # 18. cross-organisation access fails
    other_pid = stranger.get("/api/v1/operators/me").data["id"]
    assert op.get(f"/api/v1/operators/{other_pid}").status_code == 403
    assert stranger.get(f"/api/v1/vehicles/{v1.data['id']}").status_code == 403

    # 19-20. expiry + replacement/history
    exp_rid = _submit(op, "OPERATOR", op_pid, "LICENCE", "DRIVING_LICENCE")
    _approve(reviewer, exp_rid, expires_at=(timezone.now() - timedelta(days=1)).isoformat())
    lic = op.get(f"/api/v1/verification/records/{exp_rid}").data
    assert lic["state"] == "VERIFIED" and lic["effective_state"] == "EXPIRED"
    # replace: resubmit LICENCE with a fresh doc
    again = _submit(op, "OPERATOR", op_pid, "LICENCE", "DRIVING_LICENCE")
    assert again == exp_rid  # same record
    hist = op.get(f"/api/v1/verification/records/{exp_rid}").data
    assert len([e for e in hist["evidence"] if e["superseded_at"]]) >= 1
    assert hist["state"] == "SUBMITTED"
