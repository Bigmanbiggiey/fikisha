"""``If-Match`` at the HTTP layer (ADR-2D-44): job detail sends the version
as an ETag, and a job action carrying a stale If-Match is refused with 412
and changes nothing."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

import pytest

from fikisha.jobs.constants import JobStatus
from fikisha.jobs.models import Job

pytestmark = pytest.mark.django_db


def _submit(client: Any, job: Any, if_match: str | None) -> Any:
    headers = {"HTTP_IF_MATCH": if_match} if if_match is not None else {}
    return client.post(f"/api/v1/jobs/{job.id}/submit", format="json", **headers)


def test_job_detail_carries_the_version_as_an_etag(
    draft_job: Any, client_for: Callable, user: Any
) -> None:
    r = client_for(user).get(f"/api/v1/jobs/{draft_job.id}")
    assert r.status_code == 200
    assert r["ETag"] == f'"{draft_job.version}"'
    assert r.data["version"] == draft_job.version


def test_a_stale_if_match_is_refused_and_changes_nothing(
    draft_job: Any, client_for: Callable, user: Any
) -> None:
    stale = f'"{draft_job.version + 1}"'
    r = _submit(client_for(user), draft_job, stale)
    assert r.status_code == 412, r.content
    assert r.json()["code"] == "stale_job"
    draft_job.refresh_from_db()
    assert draft_job.status == JobStatus.DRAFT


@pytest.mark.parametrize("header", ["current", "weak", "bare", "any", None])
def test_a_current_any_or_missing_if_match_goes_through(
    draft_job: Any, client_for: Callable, user: Any, header: str | None
) -> None:
    v = draft_job.version
    value = {"current": f'"{v}"', "weak": f'W/"{v}"', "bare": str(v), "any": "*", None: None}[
        header
    ]
    r = _submit(client_for(user), draft_job, value)
    assert r.status_code == 200, r.content
    assert Job.objects.get(id=draft_job.id).status == JobStatus.REQUESTED


def test_a_malformed_if_match_is_a_400(draft_job: Any, client_for: Callable, user: Any) -> None:
    r = _submit(client_for(user), draft_job, '"seven"')
    assert r.status_code == 400
    assert r.json()["code"] == "invalid_if_match"
    draft_job.refresh_from_db()
    assert draft_job.status == JobStatus.DRAFT


def test_if_match_is_allowed_by_cors() -> None:
    from django.conf import settings

    assert "if-match" in [h.lower() for h in settings.CORS_ALLOW_HEADERS]
