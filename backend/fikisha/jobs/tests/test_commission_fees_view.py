"""Who sees Fikisha's fee on a job (commission split, ADR-2D-55): the business
its own side, the confirmed operator its own side, staff both, and nobody
else (IDOR/BOLA)."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

import pytest

from fikisha.jobs.creation import job_detail

pytestmark = pytest.mark.django_db


def _parties(job: Any, actor: Any) -> list[str]:
    return [f["party"] for f in job_detail(job, viewer=actor)["fees"]]


def test_each_side_sees_its_own_fee_at_the_agreed_rates(
    delivered_job: Callable,
    business_actor: Any,
    actor_for: Callable,
    eligible_driver: Any,
    admin_actor: Any,
) -> None:
    job = delivered_job()  # agreed KES 2,500
    [business_fee] = job_detail(job, viewer=business_actor)["fees"]
    assert business_fee == {
        "party": "BUSINESS",
        "rate": "0.0500",
        "fee_kes": 12_500,
        "total_cost_kes": 262_500,
    }
    [operator_fee] = job_detail(job, viewer=actor_for(eligible_driver.user))["fees"]
    assert operator_fee == {
        "party": "OPERATOR",
        "rate": "0.0500",
        "fee_kes": 12_500,
        "operator_keeps_kes": 237_500,
    }
    assert _parties(job, admin_actor) == ["BUSINESS", "OPERATOR"]


def test_outsiders_see_no_fee(
    delivered_job: Callable,
    actor_for: Callable,
    make_verified_operator: Callable,
    make_user: Callable,
) -> None:
    job = delivered_job()
    stranger_operator = make_verified_operator("+254745100031", "S. Stranger")
    assert _parties(job, actor_for(stranger_operator.user)) == []
    assert _parties(job, actor_for(make_user("+254700000033"))) == []


def test_no_fee_before_a_price_is_agreed(draft_job: Any, business_actor: Any) -> None:
    assert job_detail(draft_job, viewer=business_actor)["fees"] == []


def test_the_fee_stays_at_the_rates_fixed_on_the_agreement(
    delivered_job: Callable, business_actor: Any, admin_actor: Any
) -> None:
    from fikisha.platform_config import services as config

    job = delivered_job()
    config.apply_change(
        patch={"commission": {"business_rate": 0.10}},
        changed_by=admin_actor.user,
        rationale="test: a later rate change",
    )
    [fee] = job_detail(job, viewer=business_actor)["fees"]
    assert fee["fee_kes"] == 12_500


def test_a_completed_job_shows_what_was_recorded(
    delivered_job: Callable, complete_job: Callable, business_actor: Any, admin_actor: Any
) -> None:
    """After completion the fee is the recorded one, after any adjustment."""
    from fikisha.jobs.commission import create_adjustment
    from fikisha.jobs.constants import CommissionAdjustmentKind
    from fikisha.jobs.models import CommissionRecord

    job = delivered_job()
    complete_job(job)
    business = CommissionRecord.objects.get(job=job, party="BUSINESS")
    create_adjustment(
        commission_record=business,
        actor=admin_actor,
        kind=CommissionAdjustmentKind.REDUCTION,
        amount_kes=-2_500,
        reason="test: a dispute reduced the business fee",
    )
    [fee] = job_detail(job, viewer=business_actor)["fees"]
    assert (fee["fee_kes"], fee["total_cost_kes"]) == (10_000, 260_000)


def test_a_job_completed_before_the_split_shows_its_old_operator_only_fee(
    delivered_job: Callable,
    business_actor: Any,
    actor_for: Callable,
    eligible_driver: Any,
) -> None:
    """A record written under the old rule (10%, operator only): the
    business sees no fee, the operator its 10%, not today's 5%."""
    from decimal import Decimal

    from fikisha.jobs.constants import JobStatus
    from fikisha.jobs.models import CommissionRecord, Job

    job = delivered_job()
    Job.objects.filter(id=job.id).update(status=JobStatus.COMPLETED)
    CommissionRecord.objects.create(
        job=job,
        party="OPERATOR",
        agreement=job.agreement,
        agreed_price_kes=250_000,
        rate=Decimal("0.1000"),
        min_fee_kes=4_000,
        cap_kes=500_000,
        commission_kes=25_000,
    )
    job.refresh_from_db()
    assert job_detail(job, viewer=business_actor)["fees"] == []
    [fee] = job_detail(job, viewer=actor_for(eligible_driver.user))["fees"]
    assert (fee["rate"], fee["fee_kes"], fee["operator_keeps_kes"]) == ("0.1000", 25_000, 225_000)
