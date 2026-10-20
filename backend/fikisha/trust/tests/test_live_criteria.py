"""Ratings and at-fault findings counting toward tiers once switched on
(trust-and-disputes plan A5; TE-4, TE-11, T-5)."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

import pytest

from fikisha.incidents.models import Incident, IncidentFinding, IncidentFindingParty
from fikisha.platform_config import services as config_service
from fikisha.ratings.models import Rating
from fikisha.trust import services
from fikisha.trust.models import TrustLevelChange

pytestmark = pytest.mark.django_db


def _criteria(view: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {c["key"]: c for c in view["criteria"]}


@pytest.fixture
def driver(make_verified_operator: Callable) -> Any:
    return make_verified_operator("+254711500002", "L. Dereva")


@pytest.fixture
def live(platform_admin: Any) -> None:
    config_service.apply_change(
        patch={"trust_tiers": {"live_criteria": True}},
        changed_by=platform_admin,
        rationale="Ratings have built up; count them.",
    )


@pytest.fixture
def rate(user: Any, verified_business: Any) -> Callable[..., None]:
    """``rate(job, score)``: both sides rate, so the rating is published."""

    def _rate(job: Any, score: int) -> None:
        Rating.objects.create(
            job=job,
            side="BUSINESS_RATES_OPERATOR",
            score=score,
            rater=user,
            rater_party="BUSINESS",
            driver_profile_id=job.assignment.assigned_driver_profile_id,
        )
        Rating.objects.create(
            job=job,
            side="OPERATOR_RATES_BUSINESS",
            score=5,
            rater=job.assignment.assigned_driver_profile.user,
            rater_party="OPERATOR",
            business=verified_business,
        )

    return _rate


def _fault(
    job: Any, driver: Any, decided_by: Any, *, kind: str = "DRIVER", type_: str = "DELAY"
) -> Any:
    incident = Incident.objects.create(
        job=job,
        type=type_,
        severity="LOW",
        reported_by_kind="USER",
        reporter_party="BUSINESS",
        status="RESOLVED",
    )
    finding = IncidentFinding.objects.create(
        incident=incident, outcome="AT_FAULT", reason="Late twice.", decided_by=decided_by
    )
    subject = driver.id if kind == "DRIVER" else job.assignment.vehicle_id
    IncidentFindingParty.objects.create(finding=finding, kind=kind, subject_id=subject)
    return finding


def test_switched_off_ratings_and_findings_are_not_measured(
    driver: Any, give_jobs: Callable
) -> None:
    give_jobs(driver, 8, days_ago=20)
    rows = _criteria(services.tier_view(driver))
    assert rows["avg_rating"]["status"] == "NOT_MEASURED"
    assert rows["at_fault_findings"]["status"] == "NOT_MEASURED"
    assert services.tier_view(driver)["ready_for_review"] is True


def test_fewer_than_three_ratings_blocks(
    driver: Any, give_jobs: Callable, rate: Callable, live: None
) -> None:
    jobs = give_jobs(driver, 8, days_ago=20)
    rate(jobs[0], 5)
    rate(jobs[1], 5)
    view = services.tier_view(driver)
    row = _criteria(view)["avg_rating"]
    assert row["status"] == "INSUFFICIENT_DATA"
    assert row["current"] == 2
    assert view["ready_for_review"] is False
    assert services.evaluate(driver) is None


def test_enough_good_ratings_meet_and_the_proposal_keeps_the_evidence(
    driver: Any, give_jobs: Callable, rate: Callable, live: None
) -> None:
    jobs = give_jobs(driver, 8, days_ago=20)
    for job, score in zip(jobs, (5, 4, 5), strict=False):
        rate(job, score)
    row = _criteria(services.tier_view(driver))["avg_rating"]
    assert row["status"] == "MET"
    assert row["current"] == pytest.approx(4.67, abs=0.01)
    change = services.evaluate(driver)
    assert isinstance(change, TrustLevelChange)
    evidence = change.criteria_snapshot["evidence"]
    assert len(evidence["rating_ids"]) == 3
    assert evidence["rating_concentration"] == {"top": 3, "of": 3}
    assert change.criteria_snapshot["live_criteria"] is True


def test_a_low_average_is_not_met(
    driver: Any, give_jobs: Callable, rate: Callable, live: None
) -> None:
    jobs = give_jobs(driver, 8, days_ago=20)
    for job in jobs[:3]:
        rate(job, 3)
    assert _criteria(services.tier_view(driver))["avg_rating"]["status"] == "NOT_MET"


def test_at_fault_findings_against_the_driver_count_only_while_current(
    driver: Any, give_jobs: Callable, rate: Callable, live: None, platform_admin: Any
) -> None:
    jobs = give_jobs(driver, 8, days_ago=20)
    for job in jobs[:3]:
        rate(job, 5)
    _fault(jobs[3], driver, platform_admin)
    assert _criteria(services.tier_view(driver))["at_fault_findings"]["status"] == "MET"  # ≤ 1
    second = _fault(jobs[4], driver, platform_admin)
    row = _criteria(services.tier_view(driver))["at_fault_findings"]
    assert row["status"] == "NOT_MET"
    assert row["current"] == 2
    # corrected to no fault: the superseded finding stops counting
    IncidentFinding.objects.create(
        incident=second.incident,
        outcome="NO_FAULT",
        reason="Road closure, not the driver.",
        decided_by=platform_admin,
        supersedes=second,
    )
    assert _criteria(services.tier_view(driver))["at_fault_findings"]["current"] == 1


def test_a_finding_naming_only_the_group_never_counts_against_the_driver(
    driver: Any, give_jobs: Callable, live: None, platform_admin: Any
) -> None:
    jobs = give_jobs(driver, 8, days_ago=20)
    _fault(jobs[0], driver, platform_admin, kind="GROUP")
    _fault(jobs[1], driver, platform_admin, kind="GROUP")
    assert _criteria(services.tier_view(driver))["at_fault_findings"]["current"] == 0


def test_staff_see_how_concentrated_the_ratings_are(
    driver: Any, give_jobs: Callable, rate: Callable, live: None
) -> None:
    jobs = give_jobs(driver, 8, days_ago=20)
    for job in jobs[:4]:
        rate(job, 5)
    assert services.tier_view(driver, staff=True)["rating_concentration"] == {"top": 4, "of": 4}
    assert "rating_concentration" not in services.tier_view(driver)
