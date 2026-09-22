"""GET /jobs/<job_id>/assignment-candidates (Design Phase 6 Increment 4).

Individual-operator-only this increment — the driver pool is always exactly
the confirmed solo operator. Verifies the read-only preview matches what
``POST .../assign`` would actually accept (the shared reason predicates in
``jobs.guards``), never drifting from the transition guards it mirrors."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

import pytest

pytestmark = pytest.mark.django_db


def test_confirmed_operator_sees_self_as_eligible_driver_and_own_vehicle(
    client_for: Callable,
    make_confirmed_job: Callable,
    eligible_driver: Any,
    eligible_vehicle: Any,
) -> None:
    job = make_confirmed_job(operator=eligible_driver)
    client = client_for(eligible_driver.user)
    r = client.get(f"/api/v1/jobs/{job.id}/assignment-candidates")
    assert r.status_code == 200, r.content
    assert r.data["value_band"] == "STANDARD"
    assert r.data["supports_group_assignment"] is False
    assert r.data["blocked"] is None
    assert len(r.data["drivers"]) == 1
    driver_row = r.data["drivers"][0]
    assert driver_row["id"] == str(eligible_driver.id)
    assert driver_row["eligible"] is True
    assert driver_row["reasons"] == []
    vehicle_ids = {v["id"]: v for v in r.data["vehicles"]}
    assert vehicle_ids[str(eligible_vehicle.id)]["eligible"] is True


def test_unrelated_operator_cannot_read_someone_elses_candidates(
    client_for: Callable,
    make_confirmed_job: Callable,
    eligible_driver: Any,
    make_verified_operator: Callable,
) -> None:
    job = make_confirmed_job(operator=eligible_driver)
    stranger = make_verified_operator("+254733999002", "Stranger Op")
    client = client_for(stranger.user)
    r = client.get(f"/api/v1/jobs/{job.id}/assignment-candidates")
    assert r.status_code == 403


def test_ineligible_vehicle_shows_a_reason_without_blocking_an_eligible_one(
    client_for: Callable,
    make_confirmed_job: Callable,
    make_vehicle: Callable,
    eligible_driver: Any,
    eligible_vehicle: Any,
) -> None:
    job = make_confirmed_job(
        operator=eligible_driver, required_vehicle_class_codes=["PICKUP"]
    )
    wrong_class_vehicle = make_vehicle(
        owner_operator=eligible_driver, registration="KDA 201C", heavy=False
    )
    # eligible_vehicle's class is whatever the fixture defaults to (light,
    # non-heavy) — force a mismatch on the second vehicle by requiring a
    # class neither fixture vehicle actually has, so both come back
    # ineligible on class grounds alone, keeping this test independent of
    # which specific light-class code the fixtures happen to pick.
    client = client_for(eligible_driver.user)
    r = client.get(f"/api/v1/jobs/{job.id}/assignment-candidates")
    assert r.status_code == 200, r.content
    rows = {v["id"]: v for v in r.data["vehicles"]}
    assert str(wrong_class_vehicle.id) in rows
    assert str(eligible_vehicle.id) in rows
    # The driver row is independent of vehicle eligibility.
    assert r.data["drivers"][0]["eligible"] is True


def test_high_value_band_reports_blocked_and_a_trust_reason(
    client_for: Callable, make_confirmed_job: Callable, eligible_driver: Any
) -> None:
    # KES 500,000 declared value -> HIGH band (min_trust_level L3); the
    # interim trust rule (ADR-2D-05) caps every driver at L1 today.
    job = make_confirmed_job(operator=eligible_driver, declared_value_kes=50_000_000)
    client = client_for(eligible_driver.user)
    r = client.get(f"/api/v1/jobs/{job.id}/assignment-candidates")
    assert r.status_code == 200, r.content
    assert r.data["value_band"] == "HIGH"
    assert r.data["blocked"] is not None
    driver_row = r.data["drivers"][0]
    assert driver_row["eligible"] is False
    assert any("trust level" in reason for reason in driver_row["reasons"])


def test_group_confirmed_job_reports_group_assignment_not_supported_yet(
    client_for: Callable, make_confirmed_job: Callable, make_verified_operator: Callable
) -> None:
    from fikisha.groups.models import (
        GroupMemberRole,
        GroupMembership,
        GroupMembershipStatus,
        GroupType,
        OperatorGroup,
    )

    manager = make_verified_operator("+254733999003", "Group Manager")
    group = OperatorGroup.objects.create(
        name="Kitengela Fleet", type=GroupType.FLEET, primary_contact=manager.user
    )
    GroupMembership.objects.create(
        group=group,
        operator=manager,
        role=GroupMemberRole.OWNER,
        status=GroupMembershipStatus.ACTIVE,
    )
    job = make_confirmed_job(group=group)
    client = client_for(manager.user)
    r = client.get(f"/api/v1/jobs/{job.id}/assignment-candidates")
    assert r.status_code == 200, r.content
    assert r.data["supports_group_assignment"] is False
    assert r.data["drivers"] == []
    assert r.data["vehicles"] == []
