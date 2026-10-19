"""When the assigned side sees each contact phone (founder assessment
2026-10-20 item 4, LD-3).

The business and staff always see both. The assigned operator / driver sees
the sender's (pickup) number from assignment, the recipient's only once pickup
is confirmed, and neither once the job is completed, cancelled, failed or
disputed.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

import pytest

from fikisha.jobs import job_authz

pytestmark = pytest.mark.django_db

API = "/api/v1"
PICKUP = "+254700900001"
RECIPIENT = "+254700900002"


@pytest.mark.parametrize(
    ("status", "pickup", "recipient"),
    [
        ("ASSIGNED", None, "until_pickup"),
        ("AT_PICKUP", None, "until_pickup"),
        ("PICKED_UP", None, None),
        ("IN_TRANSIT", None, None),
        ("AT_DESTINATION", None, None),
        ("DELIVERED", None, None),
        ("COMPLETED", "job_closed", "job_closed"),
        ("CANCELLED", "job_closed", "job_closed"),
        ("FAILED", "job_closed", "job_closed"),
        ("DISPUTED", "job_closed", "job_closed"),
    ],
)
def test_the_assigned_driver_sees_contacts_by_stage(
    make_assigned_job: Callable,
    driver_actor: Any,
    status: str,
    pickup: str | None,
    recipient: str | None,
) -> None:
    job = make_assigned_job()
    job.status = status  # in memory only: the rule reads the status it is given
    assert job_authz.hidden_contacts(driver_actor, job) == {
        "pickup": pickup,
        "recipient": recipient,
    }


def test_the_business_and_staff_always_see_both(
    make_assigned_job: Callable, business_actor: Any, admin_actor: Any
) -> None:
    job = make_assigned_job()
    for status in ("ASSIGNED", "COMPLETED", "DISPUTED"):
        job.status = status
        for actor in (business_actor, admin_actor):
            assert job_authz.hidden_contacts(actor, job) == {"pickup": None, "recipient": None}


def test_through_the_api_at_assignment(
    client_for: Callable, make_assigned_job: Callable, eligible_driver: Any
) -> None:
    assigned = make_assigned_job(recipient_phone=RECIPIENT, pickup_contact_phone=PICKUP)
    r = client_for(eligible_driver.user).get(f"{API}/jobs/{assigned.id}")
    assert r.data["pickup_location"]["contact_phone"] == PICKUP
    assert r.data["recipient_phone"] == ""
    assert r.data["hidden_contacts"]["recipient"] == "until_pickup"


def test_after_completion_the_driver_sees_no_contact(
    client_for: Callable,
    delivered_job: Callable,
    complete_job: Callable,
    eligible_driver: Any,
) -> None:
    job = delivered_job()
    r = client_for(eligible_driver.user).get(f"{API}/jobs/{job.id}")
    assert r.data["hidden_contacts"] == {"pickup": None, "recipient": None}
    complete_job(job)
    r = client_for(eligible_driver.user).get(f"{API}/jobs/{job.id}")
    assert r.data["hidden_contacts"] == {"pickup": "job_closed", "recipient": "job_closed"}
    assert r.data["recipient_phone"] == ""
    assert r.data["pickup_location"]["contact_phone"] == ""
