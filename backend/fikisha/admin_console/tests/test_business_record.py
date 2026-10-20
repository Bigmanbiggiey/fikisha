"""The staff business record (trust-and-disputes plan A8)."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

import pytest

from fikisha.incidents.models import Incident, IncidentFinding, IncidentFindingParty

pytestmark = pytest.mark.django_db

API = "/api/v1"


def test_the_record_keeps_reports_closures_and_findings_apart(
    client_for: Callable,
    platform_admin: Any,
    make_assigned_job: Callable,
    verified_business: Any,
) -> None:
    job = make_assigned_job()
    open_report = Incident.objects.create(
        job=job,
        type="NON_PAYMENT",
        severity="MEDIUM",
        reported_by_kind="USER",
        reporter_party="OPERATOR",
    )
    closed = Incident.objects.create(
        job=job, type="DELAY", severity="LOW", reported_by_kind="USER", status="RESOLVED"
    )
    old = IncidentFinding.objects.create(
        incident=closed,
        outcome="AT_FAULT",
        reason="Kept the driver waiting.",
        decided_by=platform_admin,
    )
    IncidentFindingParty.objects.create(
        finding=old, kind="BUSINESS", subject_id=verified_business.id
    )
    IncidentFinding.objects.create(
        incident=closed,
        outcome="NO_FAULT",
        reason="Gate was locked by the landlord.",
        decided_by=platform_admin,
        supersedes=old,
    )
    r = client_for(platform_admin).get(
        f"{API}/admin/directory/businesses/{verified_business.id}/record"
    )
    assert r.status_code == 200, r.content
    body = r.json()
    assert [i["id"] for i in body["open_reports"]] == [str(open_report.id)]
    assert [i["id"] for i in body["closed_incidents"]] == [str(closed.id)]
    [finding] = body["findings_against"]
    assert finding["current"] is False  # superseded, shown as history
    assert body["unfounded_reports"] == []
    assert body["rating"] == {"average": None, "count": 0}
    assert body["cancellation_flags"] == []


def test_a_business_user_cannot_read_it(
    client_for: Callable, user: Any, verified_business: Any
) -> None:
    r = client_for(user).get(f"{API}/admin/directory/businesses/{verified_business.id}/record")
    assert r.status_code == 403
