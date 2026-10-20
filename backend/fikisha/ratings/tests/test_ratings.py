"""Ratings (trust-and-disputes plan A4; TE-1..TE-4, TE-8..TE-10)."""

from __future__ import annotations

from collections.abc import Callable
from datetime import timedelta
from typing import Any

import pytest
from django.utils import timezone

from fikisha.audit.models import AuditLogEntry
from fikisha.common.models import AppendOnlyModelError
from fikisha.incidents.services import open_dispute, report_incident, resolve_dispute
from fikisha.jobs import rating_facts
from fikisha.ratings import services
from fikisha.ratings.models import Rating

pytestmark = pytest.mark.django_db

LATER = timedelta(days=8)


def test_the_business_rates_the_driver(completed_job: Any, business_owner_actor: Any) -> None:
    rating = services.submit(
        actor=business_owner_actor, job_id=completed_job.id, score=5, comment="On time."
    )
    assert rating.side == "BUSINESS_RATES_OPERATOR"
    assert rating.driver_profile_id == completed_job.assignment.assigned_driver_profile_id
    assert rating.group_id is None
    assert rating.business_id is None
    assert AuditLogEntry.objects.filter(action="rating.submitted").exists()


def test_the_driver_rates_the_business(completed_job: Any, driver_actor: Any) -> None:
    rating = services.submit(actor=driver_actor, job_id=completed_job.id, score=4)
    assert rating.side == "OPERATOR_RATES_BUSINESS"
    assert rating.business_id == completed_job.business_id
    assert rating.rater_party == "OPERATOR"


def test_one_rating_per_side(completed_job: Any, business_owner_actor: Any) -> None:
    services.submit(actor=business_owner_actor, job_id=completed_job.id, score=5)
    with pytest.raises(services.AlreadyRated):
        services.submit(actor=business_owner_actor, job_id=completed_job.id, score=1)


@pytest.mark.parametrize("score", [0, 6, -1])
def test_scores_are_1_to_5(completed_job: Any, business_owner_actor: Any, score: int) -> None:
    with pytest.raises(services.InvalidRating):
        services.submit(actor=business_owner_actor, job_id=completed_job.id, score=score)


def test_staff_and_strangers_cannot_rate(
    completed_job: Any, admin_actor: Any, other_business_actor: Any
) -> None:
    for actor in (admin_actor, other_business_actor):
        with pytest.raises(services.NotRatingParty):
            services.submit(actor=actor, job_id=completed_job.id, score=3)


def test_only_a_completed_job_can_be_rated(
    delivered_job: Callable, business_owner_actor: Any
) -> None:
    job = delivered_job()
    with pytest.raises(services.RatingNotOpen):
        services.submit(actor=business_owner_actor, job_id=job.id, score=5)


def test_the_window_closes_after_7_days_in_completed(
    completed_job: Any, business_owner_actor: Any
) -> None:
    with pytest.raises(services.RatingNotOpen):
        services.submit(
            actor=business_owner_actor,
            job_id=completed_job.id,
            score=5,
            now=timezone.now() + LATER,
        )


def test_publication_both_sides_or_window(
    completed_job: Any, business_owner_actor: Any, driver_actor: Any
) -> None:
    services.submit(actor=business_owner_actor, job_id=completed_job.id, score=2, comment="Late.")
    driver_view = services.job_ratings_view(driver_actor, completed_job)
    assert driver_view["about_me"] is None  # not published yet
    later = services.job_ratings_view(driver_actor, completed_job, now=timezone.now() + LATER)
    assert later["about_me"]["score"] == 2
    assert "comment" not in later["about_me"]  # TE-3
    services.submit(actor=driver_actor, job_id=completed_job.id, score=5)
    both = services.job_ratings_view(business_owner_actor, completed_job)
    assert both["about_me"]["score"] == 5


def test_staff_see_every_rating_with_comments(
    completed_job: Any, business_owner_actor: Any, admin_actor: Any
) -> None:
    services.submit(actor=business_owner_actor, job_id=completed_job.id, score=3, comment="Ok.")
    view = services.job_ratings_view(admin_actor, completed_job)
    assert view["ratings"][0]["comment"] == "Ok."
    assert view["ratings"][0]["published"] is False


def test_time_disputed_does_not_count_and_a_failed_job_stops_counting(
    completed_job: Any, business_owner_actor: Any, admin_actor: Any
) -> None:
    services.submit(actor=business_owner_actor, job_id=completed_job.id, score=1)
    incident = report_incident(
        actor=business_owner_actor, job_id=completed_job.id, type="MISSING_GOODS"
    )
    dispute, _ = open_dispute(
        actor=business_owner_actor, job_id=completed_job.id, incident_ids=[incident.id]
    )
    far = timezone.now() + timedelta(days=30)
    spent = rating_facts.time_in_completed([completed_job.id], now=far)[str(completed_job.id)]
    assert spent < timedelta(minutes=5)  # the clock paused while DISPUTED
    driver_id = completed_job.assignment.assigned_driver_profile_id
    assert services.counted("DRIVER", driver_id, now=far) == []
    resolve_dispute(
        actor=admin_actor,
        dispute_id=dispute.id,
        outcome_code="ADMIN_DETERMINATION",
        rationale="Goods never arrived; the job failed.",
        routed_job_status="FAILED",
    )
    assert services.counted("DRIVER", driver_id, now=far) == []
    assert Rating.objects.count() == 1  # kept, just not counted


def test_counted_ratings_and_the_average(completed_job: Any, business_owner_actor: Any) -> None:
    services.submit(actor=business_owner_actor, job_id=completed_job.id, score=4)
    driver_id = completed_job.assignment.assigned_driver_profile_id
    avg = services.average("DRIVER", driver_id, now=timezone.now() + LATER)
    assert avg["count"] == 1
    assert avg["enough"] is False  # TE-4: fewer than 3
    assert avg["average"] is None


def test_ratings_are_append_only(completed_job: Any, business_owner_actor: Any) -> None:
    rating = services.submit(actor=business_owner_actor, job_id=completed_job.id, score=4)
    rating.score = 5
    with pytest.raises(AppendOnlyModelError):
        rating.save()


class TestApi:
    def test_rate_and_read_back(
        self, client_for: Callable, completed_job: Any, business_owner_actor: Any
    ) -> None:
        client = client_for(business_owner_actor.user)
        before = client.get(f"/api/v1/jobs/{completed_job.id}/ratings")
        assert before.status_code == 200
        assert before.json()["can_rate"] is True
        r = client.post(
            f"/api/v1/jobs/{completed_job.id}/ratings",
            {"score": 5, "comment": "Great"},
            format="json",
        )
        assert r.status_code == 201, r.content
        assert r.json()["can_rate"] is False
        assert r.json()["mine"]["score"] == 5

    def test_a_stranger_gets_403(
        self, client_for: Callable, completed_job: Any, other_business_actor: Any
    ) -> None:
        client = client_for(other_business_actor.user)
        assert client.get(f"/api/v1/jobs/{completed_job.id}/ratings").status_code == 403
        r = client.post(f"/api/v1/jobs/{completed_job.id}/ratings", {"score": 5}, format="json")
        assert r.status_code == 403
