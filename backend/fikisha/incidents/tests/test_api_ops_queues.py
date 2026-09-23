"""Design Phase 6 Increment 8 — cross-job incident/dispute queues for the
Ops console overview (P3 §18.1): config-driven ``incident.intake`` gate, the
"needs Platform Admin" marker above STANDARD, resolved items excluded."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

import pytest

pytestmark = pytest.mark.django_db


def _open_dispute(client: Any, job: Any) -> tuple[str, str]:
    incident_id = client.post(
        f"/api/v1/jobs/{job.id}/incidents", {"type": "DAMAGE"}, format="json"
    ).data["id"]
    dispute_id = client.post(
        f"/api/v1/jobs/{job.id}/disputes", {"incident_ids": [incident_id]}, format="json"
    ).data["dispute"]["id"]
    return incident_id, dispute_id


def test_ops_sees_open_incidents_and_disputes_with_band_marker(
    client_for: Callable,
    ops_officer: Any,
    business_owner_actor: Any,
    make_assigned_job: Callable,
) -> None:
    job = make_assigned_job(declared_value_kes=10_000_000)  # ELEVATED
    incident_id, dispute_id = _open_dispute(client_for(business_owner_actor.user), job)
    ops = client_for(ops_officer)

    incidents = ops.get("/api/v1/ops/incidents").json()["data"]
    assert incident_id in {i["id"] for i in incidents}
    row = next(i for i in incidents if i["id"] == incident_id)
    assert row["job_reference"] == str(job.id)[-6:].upper()

    disputes = ops.get("/api/v1/ops/disputes").json()["data"]
    d = next(x for x in disputes if x["id"] == dispute_id)
    assert d["value_band"] == "ELEVATED"
    assert d["needs_platform_admin"] is True


def test_standard_dispute_does_not_need_platform_admin(
    client_for: Callable,
    ops_officer: Any,
    business_owner_actor: Any,
    make_assigned_job: Callable,
) -> None:
    job = make_assigned_job(declared_value_kes=1_000_000)
    _, dispute_id = _open_dispute(client_for(business_owner_actor.user), job)
    disputes = client_for(ops_officer).get("/api/v1/ops/disputes").json()["data"]
    assert next(x for x in disputes if x["id"] == dispute_id)["needs_platform_admin"] is False


@pytest.mark.parametrize("path", ["/api/v1/ops/incidents", "/api/v1/ops/disputes"])
def test_queues_are_staff_only(
    path: str, client_for: Callable, business_owner_actor: Any, other_business_actor: Any
) -> None:
    assert client_for(business_owner_actor.user).get(path).status_code == 403
    assert client_for(other_business_actor.user).get(path).status_code == 403
