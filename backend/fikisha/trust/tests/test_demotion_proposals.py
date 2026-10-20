"""Restriction and rating-drop proposals, confirm-time re-checks, and
lifting a restriction (trust-and-disputes plan A6; TE-5, TE-6, Q3, TD-4)."""

from __future__ import annotations

import dataclasses
from collections.abc import Callable
from typing import Any

import pytest
from django.db import IntegrityError, transaction

from fikisha.incidents import findings
from fikisha.incidents.models import Incident
from fikisha.platform_config import services as config_service
from fikisha.ratings.models import Rating
from fikisha.trust import services
from fikisha.trust.constants import ChangeStatus, ChangeTrigger, Tier
from fikisha.trust.models import TrustLevelChange

pytestmark = pytest.mark.django_db

REASON = "Reviewed the photos and both statements."


@pytest.fixture
def driver(make_verified_operator: Callable) -> Any:
    return make_verified_operator("+254711500003", "R. Dereva")


@pytest.fixture
def ops(ops_officer: Any, actor_for: Callable) -> Any:
    return actor_for(ops_officer)


@pytest.fixture
def stepped_admin(admin_actor: Any) -> Any:
    return dataclasses.replace(admin_actor, is_step_up_fresh=True)


@pytest.fixture
def live(platform_admin: Any) -> None:
    config_service.apply_change(
        patch={"trust_tiers": {"live_criteria": True}},
        changed_by=platform_admin,
        rationale="Count ratings and findings.",
    )


def _incident(job: Any, type_: str = "DAMAGE") -> Any:
    return Incident.objects.create(
        job=job, type=type_, severity="HIGH", reported_by_kind="USER", reporter_party="BUSINESS"
    )


def _restriction_proposals(driver: Any) -> Any:
    return TrustLevelChange.objects.filter(
        operator=driver, trigger=ChangeTrigger.INCIDENT, status=ChangeStatus.PROPOSED
    )


# ─── TE-5: a serious at-fault finding proposes Restricted ─────────────
def test_a_serious_finding_naming_the_driver_proposes_restricted(
    driver: Any, give_jobs: Callable, ops: Any
) -> None:
    job = give_jobs(driver, 1)[0]
    incident = _incident(job)
    finding = findings.record_finding(
        actor=ops, incident_id=incident.id, outcome="AT_FAULT", parties=["DRIVER"], reason=REASON
    )
    proposal = _restriction_proposals(driver).get()
    assert proposal.to_level == Tier.RESTRICTED
    assert proposal.evidence_key == str(finding.id)
    assert services.stored_level(driver.id) == Tier.L1  # nothing applied yet (FR-T-4)


@pytest.mark.parametrize(
    ("type_", "parties"),
    [
        ("DELAY", ["DRIVER"]),  # not a serious type
        ("DAMAGE", ["BUSINESS", "DRIVER"]),  # shared: no proposal (Q3)
        ("DAMAGE", ["BUSINESS"]),
    ],
)
def test_findings_that_do_not_propose(
    driver: Any, give_jobs: Callable, ops: Any, type_: str, parties: list[str]
) -> None:
    job = give_jobs(driver, 1)[0]
    findings.record_finding(
        actor=ops,
        incident_id=_incident(job, type_).id,
        outcome="AT_FAULT",
        parties=parties,
        reason=REASON,
    )
    assert not _restriction_proposals(driver).exists()


def test_a_platform_admin_confirms_the_restriction(
    driver: Any, give_jobs: Callable, ops: Any, stepped_admin: Any
) -> None:
    job = give_jobs(driver, 1)[0]
    findings.record_finding(
        actor=ops,
        incident_id=_incident(job).id,
        outcome="AT_FAULT",
        parties=["DRIVER"],
        reason=REASON,
    )
    proposal = _restriction_proposals(driver).get()
    services.decide_proposal(
        actor=stepped_admin, change_id=proposal.id, confirm=True, reason=REASON
    )
    assert services.stored_level(driver.id) == Tier.RESTRICTED


def test_a_corrected_finding_makes_the_proposal_out_of_date(
    driver: Any, give_jobs: Callable, ops: Any, stepped_admin: Any
) -> None:
    job = give_jobs(driver, 1)[0]
    incident = _incident(job)
    findings.record_finding(
        actor=ops, incident_id=incident.id, outcome="AT_FAULT", parties=["DRIVER"], reason=REASON
    )
    proposal = _restriction_proposals(driver).get()
    findings.record_finding(
        actor=ops,
        incident_id=incident.id,
        outcome="NO_FAULT",
        parties=[],
        reason="The packaging was already damaged at pickup.",
    )
    with pytest.raises(services.ProposalNotOpen):
        services.decide_proposal(
            actor=stepped_admin, change_id=proposal.id, confirm=True, reason=REASON
        )
    assert services.stored_level(driver.id) == Tier.L1


def test_an_applied_restriction_is_never_undone_by_a_correction(
    driver: Any, give_jobs: Callable, ops: Any, stepped_admin: Any
) -> None:
    job = give_jobs(driver, 1)[0]
    incident = _incident(job)
    findings.record_finding(
        actor=ops, incident_id=incident.id, outcome="AT_FAULT", parties=["DRIVER"], reason=REASON
    )
    services.decide_proposal(
        actor=stepped_admin,
        change_id=_restriction_proposals(driver).get().id,
        confirm=True,
        reason=REASON,
    )
    findings.record_finding(
        actor=ops, incident_id=incident.id, outcome="NO_FAULT", parties=[], reason=REASON
    )
    assert services.stored_level(driver.id) == Tier.RESTRICTED


def test_one_restriction_proposal_per_finding(driver: Any, give_jobs: Callable, ops: Any) -> None:
    job = give_jobs(driver, 1)[0]
    finding = findings.record_finding(
        actor=ops,
        incident_id=_incident(job).id,
        outcome="AT_FAULT",
        parties=["DRIVER"],
        reason=REASON,
    )
    assert (
        services.propose_restriction(
            actor=ops, operator_id=driver.id, finding_id=finding.id, incident_id=finding.incident_id
        )
        is None
    )
    with pytest.raises(IntegrityError), transaction.atomic():
        TrustLevelChange.objects.create(
            operator=driver,
            from_level="L1",
            to_level="RESTRICTED",
            trigger="INCIDENT",
            status="PROPOSED",
            proposed_by="SYSTEM",
            evidence_key=str(finding.id),
        )


def test_the_operator_does_not_see_a_pending_demotion(
    driver: Any, give_jobs: Callable, ops: Any
) -> None:
    job = give_jobs(driver, 1)[0]
    findings.record_finding(
        actor=ops,
        incident_id=_incident(job).id,
        outcome="AT_FAULT",
        parties=["DRIVER"],
        reason=REASON,
    )
    assert services.tier_view(driver)["open_proposal"] is None
    assert services.tier_view(driver, staff=True)["open_proposal"]["trigger"] == "INCIDENT"


# ─── TE-6: a rating drop proposes one tier down ────────────────────────
@pytest.fixture
def rate_all(user: Any, verified_business: Any) -> Callable[..., None]:
    def _rate(jobs: list[Any], score: int) -> None:
        for job in jobs:
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


def test_a_rating_drop_proposes_one_tier_down_once_per_evidence(
    driver: Any, give_jobs: Callable, rate_all: Callable, live: None, stepped_admin: Any
) -> None:
    services.set_level(actor=stepped_admin, operator_id=driver.id, level="L2", reason=REASON)
    rate_all(give_jobs(driver, 10), 3)
    change = services.evaluate(driver)
    assert change is not None
    assert (change.trigger, change.from_level, change.to_level) == ("RATING_DROP", "L2", "L1")
    assert len(change.criteria_snapshot["rating_drop"]["rating_ids"]) == 10
    assert services.evaluate(driver) is None  # already open
    services.decide_proposal(actor=stepped_admin, change_id=change.id, confirm=False, reason=REASON)
    assert services.evaluate(driver) is None  # same evidence, and the cooldown


def test_fewer_than_ten_ratings_never_drop(
    driver: Any, give_jobs: Callable, rate_all: Callable, live: None
) -> None:
    rate_all(give_jobs(driver, 9), 1)
    assert services.evaluate(driver) is None


def test_switched_off_ratings_never_drop(
    driver: Any, give_jobs: Callable, rate_all: Callable
) -> None:
    rate_all(give_jobs(driver, 10), 1)
    services.evaluate(driver)
    assert not TrustLevelChange.objects.filter(operator=driver, trigger="RATING_DROP").exists()


def test_no_promotion_while_a_demotion_is_open(driver: Any, give_jobs: Callable, ops: Any) -> None:
    jobs = give_jobs(driver, 8, days_ago=20)
    findings.record_finding(
        actor=ops,
        incident_id=_incident(jobs[0]).id,
        outcome="AT_FAULT",
        parties=["DRIVER"],
        reason=REASON,
    )
    assert services.evaluate(driver) is None
    assert not TrustLevelChange.objects.filter(operator=driver, trigger="AUTO_PROPOSED").exists()


# ─── TD-4: lifting a restriction ───────────────────────────────────────
def test_lifting_a_restriction_is_a_remediation_exit_to_l1(driver: Any, stepped_admin: Any) -> None:
    services.set_level(
        actor=stepped_admin, operator_id=driver.id, level="RESTRICTED", reason=REASON
    )
    change = services.set_level(
        actor=stepped_admin,
        operator_id=driver.id,
        level="L1",
        reason="Retrained; stage chair vouches.",
    )
    assert change.trigger == ChangeTrigger.REMEDIATION_EXIT
