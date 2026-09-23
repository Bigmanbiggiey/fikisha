"""Design Phase 6 Increment 8 — audit read (P3 §18.5). ``audit.view.scoped``
= the Ops remit allowlist (founder decision 2026-09-23); Platform Admin sees
everything; everyone else is denied."""

from __future__ import annotations

import uuid
from collections.abc import Callable
from typing import Any

import pytest
from django.db import transaction

from fikisha.audit import services as audit

pytestmark = pytest.mark.django_db


def _record(actor: Any, action: str, entity_type: str, entity_id: Any = None) -> None:
    with transaction.atomic():
        audit.record(actor=actor, action=action, entity_type=entity_type, entity_id=entity_id)


@pytest.fixture
def entries(platform_admin: Any) -> dict[str, uuid.UUID]:
    ids = {"job": uuid.uuid4(), "commission": uuid.uuid4(), "config": uuid.uuid4()}
    _record(platform_admin, "job.note.added", "job", ids["job"])
    _record(platform_admin, "commission.adjusted", "commission_record", ids["commission"])
    _record(platform_admin, "config.changed", "platform_config", ids["config"])
    return ids


def test_ops_sees_only_the_ops_remit(
    client_for: Callable, ops_officer: Any, entries: dict[str, uuid.UUID]
) -> None:
    data = client_for(ops_officer).get("/api/v1/audit/entries").json()["data"]
    types = {row["entity_type"] for row in data}
    assert "job" in types
    assert not types & {"commission_record", "platform_config"}
    assert all("source_ip" not in row for row in data)


def test_ops_cannot_widen_scope_with_a_filter(
    client_for: Callable, ops_officer: Any, entries: dict[str, uuid.UUID]
) -> None:
    resp = client_for(ops_officer).get("/api/v1/audit/entries?entity_type=commission_record")
    assert resp.status_code == 200
    assert resp.json()["data"] == []


def test_platform_admin_sees_everything(
    client_for: Callable, platform_admin: Any, entries: dict[str, uuid.UUID]
) -> None:
    data = client_for(platform_admin).get("/api/v1/audit/entries").json()["data"]
    assert {"job", "commission_record", "platform_config"} <= {r["entity_type"] for r in data}


def test_filters_and_newest_first(
    client_for: Callable, platform_admin: Any, entries: dict[str, uuid.UUID]
) -> None:
    client = client_for(platform_admin)
    rows = client.get(f"/api/v1/audit/entries?entity_id={entries['job']}").json()["data"]
    assert [r["action"] for r in rows] == ["job.note.added"]
    rows = client.get("/api/v1/audit/entries?action=config.").json()["data"]
    assert [r["action"] for r in rows] == ["config.changed"]
    seqs = [r["seq"] for r in client.get("/api/v1/audit/entries").json()["data"]]
    assert seqs == sorted(seqs, reverse=True)
    assert client.get("/api/v1/audit/entries?entity_id=nope").status_code == 422


def test_ordinary_users_are_denied(client_for: Callable, user: Any) -> None:
    assert client_for(user).get("/api/v1/audit/entries").status_code == 403
