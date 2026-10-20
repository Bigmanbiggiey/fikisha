"""Map pins on jobs (docs/maps-plan.md M-3 / M-4, MD-2).

A pinned location is ``CAPTURED``. The exact pin goes to the business, staff
and, once the job is assigned, the assigned operator/group and driver; anyone
else (an operator still looking or negotiating) gets the ~1 km area,
``COARSENED``, the same people who don't get contact phones.
"""

from __future__ import annotations

from collections.abc import Callable
from decimal import Decimal
from typing import Any

import pytest

from fikisha.jobs.tests.test_discovery import _make_requested_job

pytestmark = pytest.mark.django_db

EXACT = (Decimal("-1.477512"), Decimal("36.960148"))


def _pin(location: Any) -> None:
    location.lat, location.lng = EXACT
    location.geo_state = "CAPTURED"
    location.save(update_fields=["lat", "lng", "geo_state"])


def test_a_pinned_destination_is_captured(
    client_for: Callable, business_actor: Any, verified_business: Any
) -> None:
    from fikisha.jobs.models import Job

    payload = {
        "business_id": str(verified_business.id),
        "pickup_location": {"address_text": "Depot"},
        "destination_location": {"address_text": "Shop", "lat": "-1.477512", "lng": "36.960148"},
        "cargo": {"description": "cement", "declared_value_kes": 1_000_000},
    }
    r = client_for(business_actor.user).post("/api/v1/jobs", payload, format="json")
    assert r.status_code == 201, r.content
    job = Job.objects.select_related("pickup_location", "destination_location").get(id=r.data["id"])
    assert job.destination_location.geo_state == "CAPTURED"
    assert job.pickup_location.geo_state == "NOT_CAPTURED"


def test_a_saved_location_pin_is_copied_as_captured(
    client_for: Callable, business_actor: Any, verified_business: Any
) -> None:
    from fikisha.business.models import BusinessLocation
    from fikisha.jobs.models import Job

    loc = BusinessLocation.objects.create(
        business=verified_business, label="Yard", type="WAREHOUSE", lat=EXACT[0], lng=EXACT[1]
    )
    payload = {
        "business_id": str(verified_business.id),
        "pickup_location": {"business_location_id": str(loc.id)},
        "destination_location": {"address_text": "Shop"},
        "cargo": {"description": "cement", "declared_value_kes": 1_000_000},
    }
    r = client_for(business_actor.user).post("/api/v1/jobs", payload, format="json")
    assert r.status_code == 201, r.content
    pickup = Job.objects.get(id=r.data["id"]).pickup_location
    assert (pickup.lat, pickup.lng, pickup.geo_state) == (*EXACT, "CAPTURED")


def test_an_operator_looking_at_work_sees_only_the_area(
    client_for: Callable,
    verified_business: Any,
    user: Any,
    admin_actor: Any,
    eligible_driver: Any,
    make_vehicle: Callable,
) -> None:
    make_vehicle(owner_operator=eligible_driver, registration="KDA 600M")
    job = _make_requested_job(business=verified_business, user=user, admin_actor=admin_actor)
    _pin(job.destination_location)

    client = client_for(eligible_driver.user)
    for url in (f"/api/v1/jobs/{job.id}/opportunity", "/api/v1/jobs/opportunities"):
        r = client.get(url)
        assert r.status_code == 200, r.content
        view = (
            r.data if "id" in r.data else next(j for j in r.data["data"] if j["id"] == str(job.id))
        )
        dest = view["destination_location"]
        assert dest["geo_state"] == "COARSENED"
        assert (Decimal(str(dest["lat"])), Decimal(str(dest["lng"]))) == (
            Decimal("-1.48"),
            Decimal("36.96"),
        )

    # The business still sees the exact pin.
    business_view = client_for(user).get(f"/api/v1/jobs/{job.id}").data
    assert business_view["destination_location"]["geo_state"] == "CAPTURED"
    assert Decimal(str(business_view["destination_location"]["lat"])) == EXACT[0]


def test_the_assigned_driver_sees_the_exact_pin(
    client_for: Callable, make_assigned_job: Callable, eligible_driver: Any
) -> None:
    job = make_assigned_job()
    _pin(job.destination_location)
    r = client_for(eligible_driver.user).get(f"/api/v1/jobs/{job.id}")
    assert r.status_code == 200, r.content
    dest = r.data["destination_location"]
    assert dest["geo_state"] == "CAPTURED"
    assert (Decimal(str(dest["lat"])), Decimal(str(dest["lng"]))) == EXACT
