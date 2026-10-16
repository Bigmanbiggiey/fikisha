"""``GET /jobs?status=&assigned=me`` (PR #5 follow-up 2: the driver's
Current job must not depend on the active job being on page 1)."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

import pytest

pytestmark = pytest.mark.django_db

API = "/api/v1/jobs"


def _ids(r: Any) -> set[str]:
    assert r.status_code == 200, r.content
    return {row["id"] for row in r.data["data"]}


def test_assigned_me_and_status_narrow_to_the_drivers_active_jobs(
    make_assigned_job: Callable,
    draft_job: Any,
    eligible_driver: Any,
    client_for: Callable,
    user: Any,
) -> None:
    active = make_assigned_job()
    driver = client_for(eligible_driver.user)

    assert str(active.id) in _ids(driver.get(f"{API}?assigned=me"))
    assert _ids(driver.get(f"{API}?assigned=me&status=ASSIGNED,AT_PICKUP")) == {str(active.id)}
    assert _ids(driver.get(f"{API}?assigned=me&status=DELIVERED")) == set()

    # the business owner sees the job, but isn't its assigned driver
    owner = client_for(user)
    assert str(active.id) in _ids(owner.get(f"{API}?status=ASSIGNED"))
    assert _ids(owner.get(f"{API}?assigned=me")) == set()
    assert str(draft_job.id) in _ids(owner.get(f"{API}?status=DRAFT"))


def test_bad_filters_are_rejected(client_for: Callable, user: Any) -> None:
    client = client_for(user)
    assert client.get(f"{API}?status=FLYING").status_code == 400
    assert client.get(f"{API}?assigned=someone").status_code == 400
