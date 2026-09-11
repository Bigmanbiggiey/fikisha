"""Assignment HTTP API (Phase 2D Step 10): the server resolves eligibility;
the API only ever forwards ids (brief §6)."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

import pytest

pytestmark = pytest.mark.django_db


def test_the_confirmed_operator_assigns_their_own_driver_and_vehicle(
    client_for: Callable,
    make_confirmed_job: Callable,
    eligible_driver: Any,
    eligible_vehicle: Any,
    actor_for: Callable,
) -> None:
    job = make_confirmed_job(operator=eligible_driver)
    client = client_for(eligible_driver.user)
    r = client.post(
        f"/api/v1/jobs/{job.id}/assign",
        {"driver_profile_id": str(eligible_driver.id), "vehicle_id": str(eligible_vehicle.id)},
        format="json",
    )
    assert r.status_code == 200, r.content
    assert r.data["status"] == "ASSIGNED"


def test_an_unrelated_operator_cannot_assign_someone_elses_confirmed_job(
    client_for: Callable,
    make_confirmed_job: Callable,
    eligible_driver: Any,
    eligible_vehicle: Any,
    make_verified_operator: Callable,
) -> None:
    job = make_confirmed_job(operator=eligible_driver)
    stranger_operator = make_verified_operator("+254733999001", "Stranger Op")
    client = client_for(stranger_operator.user)
    r = client.post(
        f"/api/v1/jobs/{job.id}/assign",
        {"driver_profile_id": str(eligible_driver.id), "vehicle_id": str(eligible_vehicle.id)},
        format="json",
    )
    assert r.status_code == 403


def test_an_unknown_driver_id_is_404_not_500(
    client_for: Callable, make_confirmed_job: Callable, eligible_driver: Any, eligible_vehicle: Any
) -> None:
    job = make_confirmed_job(operator=eligible_driver)
    client = client_for(eligible_driver.user)
    r = client.post(
        f"/api/v1/jobs/{job.id}/assign",
        {
            "driver_profile_id": "00000000-0000-7000-8000-000000000000",
            "vehicle_id": str(eligible_vehicle.id),
        },
        format="json",
    )
    assert r.status_code == 404
