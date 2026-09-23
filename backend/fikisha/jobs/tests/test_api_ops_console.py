"""Design Phase 6 Increment 8 — Operations Officer console (P3 §18).

Covers: the staff-cancel band guard (founder decision 2026-09-23 — Ops ≤
STANDARD, above → Platform Admin; a business party is never affected), the
operational note (visible to the job's parties, never changes status), the
audited contact reveal (no phone in the audit row), the job monitor filters
+ job-reference quick jump, the staff event log, the high-value queue +
decision endpoint, and config-driven permission denials (IDOR/BOLA).
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

import pytest

from fikisha.audit.models import AuditLogEntry
from fikisha.common.models import AppendOnlyModelError
from fikisha.jobs.constants import JobStatus
from fikisha.jobs.models import Job, JobEvent

pytestmark = pytest.mark.django_db

ELEVATED = 10_000_000  # KES 100,000.00
HIGH = 50_000_000  # KES 500,000.00
VERY_HIGH = 200_000_000  # KES 2,000,000.00


def _cancel(client: Any, job: Job, reason_text: str = "") -> Any:
    body: dict[str, Any] = {"reason_code": "ADMIN_ACTION"}
    if reason_text:
        body["reason_text"] = reason_text
    return client.post(f"/api/v1/jobs/{job.id}/cancel", body, format="json")


# ─── Staff cancel band guard ──────────────────────────────────────────
def test_ops_can_cancel_standard_job_with_reason(
    client_for: Callable, ops_officer: Any, make_confirmed_job: Callable, eligible_driver: Any
) -> None:
    job = make_confirmed_job(operator=eligible_driver, declared_value_kes=1_000_000)
    assert job.value_band == "STANDARD"
    resp = _cancel(client_for(ops_officer), job, "Business asked us to stop it by phone")
    assert resp.status_code == 200, resp.content
    job.refresh_from_db()
    assert job.status == JobStatus.CANCELLED


@pytest.mark.parametrize("declared", [ELEVATED, HIGH, VERY_HIGH])
def test_ops_cannot_cancel_above_standard(
    declared: int,
    client_for: Callable,
    ops_officer: Any,
    make_confirmed_job: Callable,
    eligible_driver: Any,
) -> None:
    job = make_confirmed_job(operator=eligible_driver, declared_value_kes=declared)
    resp = _cancel(client_for(ops_officer), job, "reason")
    assert resp.status_code == 422, resp.content
    assert resp.json()["code"] == "platform_admin_required"
    job.refresh_from_db()
    assert job.status == JobStatus.CONFIRMED


@pytest.mark.parametrize("declared", [ELEVATED, HIGH, VERY_HIGH])
def test_platform_admin_can_cancel_any_band(
    declared: int,
    client_for: Callable,
    platform_admin: Any,
    make_confirmed_job: Callable,
    eligible_driver: Any,
) -> None:
    job = make_confirmed_job(operator=eligible_driver, declared_value_kes=declared)
    resp = _cancel(client_for(platform_admin), job, "Fraud concern")
    assert resp.status_code == 200, resp.content


def test_staff_cancel_requires_a_reason(
    client_for: Callable, ops_officer: Any, make_confirmed_job: Callable, eligible_driver: Any
) -> None:
    job = make_confirmed_job(operator=eligible_driver, declared_value_kes=1_000_000)
    resp = _cancel(client_for(ops_officer), job)
    assert resp.status_code == 422
    assert resp.json()["code"] == "admin_reason_required"


@pytest.mark.parametrize("declared", [1_000_000, ELEVATED, VERY_HIGH])
def test_business_party_cancel_is_unaffected_by_band(
    declared: int,
    client_for: Callable,
    user: Any,
    make_confirmed_job: Callable,
    eligible_driver: Any,
) -> None:
    """The business owner cancels as BUSINESS_PARTY — no reason, any band."""
    job = make_confirmed_job(operator=eligible_driver, declared_value_kes=declared)
    resp = client_for(user).post(
        f"/api/v1/jobs/{job.id}/cancel", {"reason_code": "OTHER"}, format="json"
    )
    assert resp.status_code == 200, resp.content


# ─── Operational notes ────────────────────────────────────────────────
def test_ops_note_is_visible_to_the_business_party_and_never_moves_status(
    client_for: Callable,
    ops_officer: Any,
    user: Any,
    make_confirmed_job: Callable,
    eligible_driver: Any,
) -> None:
    job = make_confirmed_job(operator=eligible_driver, declared_value_kes=1_000_000)
    before_status, before_version = job.status, job.version

    resp = client_for(ops_officer).post(
        f"/api/v1/jobs/{job.id}/notes", {"text": "Called the driver — running late"}, format="json"
    )
    assert resp.status_code == 201, resp.content
    job.refresh_from_db()
    assert (job.status, job.version) == (before_status, before_version)
    assert AuditLogEntry.objects.filter(action="job.note.added", entity_id=job.id).count() == 1

    party_view = client_for(user).get(f"/api/v1/jobs/{job.id}/notes").json()["data"]
    assert [n["text"] for n in party_view] == ["Called the driver — running late"]
    assert party_view[0]["author_label"] == "Fikisha Operations"
    assert "author_user_id" not in party_view[0]  # staff identity not disclosed to parties


def test_notes_are_append_only(
    client_for: Callable, ops_officer: Any, make_confirmed_job: Callable, eligible_driver: Any
) -> None:
    job = make_confirmed_job(operator=eligible_driver, declared_value_kes=1_000_000)
    client_for(ops_officer).post(f"/api/v1/jobs/{job.id}/notes", {"text": "x"}, format="json")
    note = JobEvent.objects.get(job=job, type="NOTE", category="ADMIN_ACTION")
    with pytest.raises(AppendOnlyModelError):
        JobEvent.objects.filter(pk=note.pk).update(note="edited")


def test_a_party_cannot_add_a_note(
    client_for: Callable, user: Any, make_confirmed_job: Callable, eligible_driver: Any
) -> None:
    job = make_confirmed_job(operator=eligible_driver, declared_value_kes=1_000_000)
    resp = client_for(user).post(f"/api/v1/jobs/{job.id}/notes", {"text": "x"}, format="json")
    assert resp.status_code == 403


def test_a_non_party_cannot_read_notes(
    client_for: Callable,
    other_user: Any,
    make_confirmed_job: Callable,
    eligible_driver: Any,
) -> None:
    job = make_confirmed_job(operator=eligible_driver, declared_value_kes=1_000_000)
    resp = client_for(other_user).get(f"/api/v1/jobs/{job.id}/notes")
    assert resp.status_code == 403


def test_empty_note_rejected(
    client_for: Callable, ops_officer: Any, make_confirmed_job: Callable, eligible_driver: Any
) -> None:
    job = make_confirmed_job(operator=eligible_driver, declared_value_kes=1_000_000)
    resp = client_for(ops_officer).post(
        f"/api/v1/jobs/{job.id}/notes", {"text": "   "}, format="json"
    )
    assert resp.status_code in (400, 422)


# ─── Contact reveal ───────────────────────────────────────────────────
def test_contact_reveal_returns_phones_and_audits_without_them(
    client_for: Callable, ops_officer: Any, make_assigned_job: Callable
) -> None:
    job = make_assigned_job(declared_value_kes=1_000_000)
    resp = client_for(ops_officer).post(f"/api/v1/jobs/{job.id}/contacts/reveal")
    assert resp.status_code == 200, resp.content
    contacts = resp.json()["contacts"]
    assert contacts["pickup"]["phone"] == "+254700900001"
    assert contacts["recipient"]["phone"] == "+254700900002"
    assert contacts["driver"]["phone"]

    rows = AuditLogEntry.objects.filter(action="job.contacts.revealed", entity_id=job.id)
    assert rows.count() == 1
    serialized = str(rows.get().after)
    assert "+2547" not in serialized
    assert "pickup" in rows.get().after["parties"]


def test_a_party_cannot_reveal_contacts(
    client_for: Callable, user: Any, make_assigned_job: Callable
) -> None:
    job = make_assigned_job(declared_value_kes=1_000_000)
    resp = client_for(user).post(f"/api/v1/jobs/{job.id}/contacts/reveal")
    assert resp.status_code == 403
    assert not AuditLogEntry.objects.filter(action="job.contacts.revealed").exists()


# ─── Job monitor + quick jump ─────────────────────────────────────────
def test_monitor_lists_all_jobs_without_contacts(
    client_for: Callable, ops_officer: Any, make_assigned_job: Callable
) -> None:
    job = make_assigned_job(declared_value_kes=1_000_000)
    body = client_for(ops_officer).get("/api/v1/ops/jobs").json()
    row = next(r for r in body["data"] if r["id"] == str(job.id))
    assert row["reference"] == str(job.id)[-6:].upper()
    assert "+2547" not in str(body)  # no phones on monitor rows


def test_monitor_filters_by_status_and_band(
    client_for: Callable, ops_officer: Any, make_confirmed_job: Callable, eligible_driver: Any
) -> None:
    std = make_confirmed_job(operator=eligible_driver, declared_value_kes=1_000_000)
    elev = make_confirmed_job(operator=eligible_driver, declared_value_kes=ELEVATED)
    client = client_for(ops_officer)
    ids = {r["id"] for r in client.get("/api/v1/ops/jobs?value_band=ELEVATED").json()["data"]}
    assert str(elev.id) in ids and str(std.id) not in ids
    ids = {r["id"] for r in client.get("/api/v1/ops/jobs?status=CANCELLED").json()["data"]}
    assert not ids & {str(std.id), str(elev.id)}


@pytest.mark.parametrize("length", [6, 8])
def test_reference_quick_jump_matches_ui_and_recipient_references(
    length: int,
    client_for: Callable,
    ops_officer: Any,
    make_confirmed_job: Callable,
    eligible_driver: Any,
) -> None:
    job = make_confirmed_job(operator=eligible_driver, declared_value_kes=1_000_000)
    make_confirmed_job(operator=eligible_driver, declared_value_kes=1_000_000)
    ref = job.id.hex[-length:].upper()
    data = client_for(ops_officer).get(f"/api/v1/ops/jobs?ref={ref}").json()["data"]
    assert [r["id"] for r in data] == [str(job.id)]


def test_monitor_rejects_unknown_filters(client_for: Callable, ops_officer: Any) -> None:
    client = client_for(ops_officer)
    assert client.get("/api/v1/ops/jobs?status=NOPE").status_code == 422
    assert client.get("/api/v1/ops/jobs?ref=ab").status_code == 422
    assert client.get("/api/v1/ops/jobs?stale_hours=x").status_code == 422


@pytest.mark.parametrize(
    "path",
    ["/api/v1/ops/jobs", "/api/v1/ops/high-value"],
)
def test_monitor_endpoints_are_staff_only(
    path: str, client_for: Callable, user: Any, other_user: Any
) -> None:
    assert client_for(user).get(path).status_code == 403
    assert client_for(other_user).get(path).status_code == 403


def test_admin_flag_without_a_role_grants_nothing(
    client_for: Callable, make_user: Callable
) -> None:
    """Config-driven: an active AdminProfile with no RoleAssignment has no
    ``job.monitor.view`` (no ``is_admin`` shortcut)."""
    from fikisha.identity.models import AdminProfile

    bare = make_user("+254700000077")
    AdminProfile.objects.create(user=bare, active=True)
    assert client_for(bare).get("/api/v1/ops/jobs").status_code == 403


# ─── Staff event log ──────────────────────────────────────────────────
def test_event_log_is_staff_only_and_ordered(
    client_for: Callable,
    ops_officer: Any,
    user: Any,
    make_confirmed_job: Callable,
    eligible_driver: Any,
) -> None:
    job = make_confirmed_job(operator=eligible_driver, declared_value_kes=1_000_000)
    assert client_for(user).get(f"/api/v1/jobs/{job.id}/events").status_code == 403
    data = client_for(ops_officer).get(f"/api/v1/jobs/{job.id}/events").json()["data"]
    seqs = [e["seq"] for e in data]
    assert seqs == sorted(seqs) and len(seqs) >= 2
    assert all("source_meta" not in e for e in data)


# ─── High-value queue + decision ──────────────────────────────────────
def test_high_value_queue_and_ops_decides_high(
    client_for: Callable, ops_officer: Any, make_confirmed_job: Callable, eligible_driver: Any
) -> None:
    high = make_confirmed_job(operator=eligible_driver, declared_value_kes=HIGH)
    very = make_confirmed_job(operator=eligible_driver, declared_value_kes=VERY_HIGH)
    client = client_for(ops_officer)

    rows = {r["id"]: r for r in client.get("/api/v1/ops/high-value").json()["data"]}
    assert rows[str(high.id)]["needs_platform_admin"] is False
    assert rows[str(very.id)]["needs_platform_admin"] is True

    resp = client.post(
        f"/api/v1/jobs/{high.id}/high-value-decision",
        {"decision": "APPROVED", "rationale": "Driver history checked"},
        format="json",
    )
    assert resp.status_code == 201, resp.content
    rows = {r["id"] for r in client.get("/api/v1/ops/high-value").json()["data"]}
    assert str(high.id) not in rows

    again = client.post(
        f"/api/v1/jobs/{high.id}/high-value-decision",
        {"decision": "REJECTED", "rationale": "second"},
        format="json",
    )
    assert again.status_code == 409


def test_ops_cannot_decide_very_high(
    client_for: Callable, ops_officer: Any, make_confirmed_job: Callable, eligible_driver: Any
) -> None:
    very = make_confirmed_job(operator=eligible_driver, declared_value_kes=VERY_HIGH)
    resp = client_for(ops_officer).post(
        f"/api/v1/jobs/{very.id}/high-value-decision",
        {"decision": "APPROVED", "rationale": "x"},
        format="json",
    )
    assert resp.status_code == 403


def test_high_value_decision_requires_rationale(
    client_for: Callable, ops_officer: Any, make_confirmed_job: Callable, eligible_driver: Any
) -> None:
    high = make_confirmed_job(operator=eligible_driver, declared_value_kes=HIGH)
    resp = client_for(ops_officer).post(
        f"/api/v1/jobs/{high.id}/high-value-decision", {"decision": "APPROVED"}, format="json"
    )
    assert resp.status_code in (400, 422)


def test_a_party_cannot_decide_high_value(
    client_for: Callable, user: Any, make_confirmed_job: Callable, eligible_driver: Any
) -> None:
    high = make_confirmed_job(operator=eligible_driver, declared_value_kes=HIGH)
    resp = client_for(user).post(
        f"/api/v1/jobs/{high.id}/high-value-decision",
        {"decision": "APPROVED", "rationale": "x"},
        format="json",
    )
    assert resp.status_code == 403
