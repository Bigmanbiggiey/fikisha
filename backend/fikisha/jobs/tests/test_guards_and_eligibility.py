"""Direct unit tests for the guards and eligibility helpers that Phase 2D
increment 1 owns. The assignment / custody-proof / dispute guards get their
comprehensive suites with their own increments (plan §19 Steps 5-8)."""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any

import pytest

from fikisha.jobs import eligibility, guards
from fikisha.jobs.constants import PenaltyClass, TrustLevel, ValueBand, compute_penalty_class
from fikisha.jobs.errors import GuardFailed, JobNoLongerAvailable

pytestmark = pytest.mark.django_db


# ─── eligibility (ADR-2D-05 Option b — interim, config-driven) ───────
@pytest.mark.parametrize(
    ("declared_minor", "expected"),
    [
        (0, ValueBand.STANDARD),
        (5_000_000, ValueBand.STANDARD),
        (5_000_001, ValueBand.ELEVATED),
        (25_000_000, ValueBand.ELEVATED),
        (25_000_001, ValueBand.HIGH),
        (100_000_000, ValueBand.HIGH),
        (100_000_001, ValueBand.VERY_HIGH),
    ],
)
def test_band_for_declared_value(declared_minor: int, expected: str) -> None:
    assert eligibility.band_for_declared_value(declared_minor) == expected


def test_band_min_trust_level_from_config() -> None:
    assert eligibility.band_min_trust_level(ValueBand.STANDARD) == "L1"
    assert eligibility.band_min_trust_level(ValueBand.ELEVATED) == "L2"
    assert eligibility.band_min_trust_level(ValueBand.HIGH) == "L3"


def test_level_covers_band() -> None:
    assert eligibility.level_covers_band(TrustLevel.L1, ValueBand.STANDARD)
    assert not eligibility.level_covers_band(TrustLevel.L1, ValueBand.ELEVATED)
    assert not eligibility.level_covers_band("", ValueBand.STANDARD)
    assert eligibility.level_covers_band(TrustLevel.L3, ValueBand.HIGH)


def test_interim_driver_trust_level_needs_all_three_domains(make_user: Any) -> None:
    from fikisha.operators.models import OperatorProfile, OperatorStatus
    from fikisha.verification.models import Domain, State, VerificationRecord

    driver = OperatorProfile.objects.create(
        user=make_user("+254799000001"), full_name="T. Driver", status=OperatorStatus.ACTIVE
    )
    assert eligibility.interim_driver_trust_level(driver) == ""  # nothing verified

    for dom in (Domain.IDENTITY, Domain.LICENCE, Domain.GOOD_CONDUCT):
        VerificationRecord.objects.create(
            subject_type="OPERATOR", subject_operator=driver, domain=dom, state=State.VERIFIED
        )
    assert eligibility.interim_driver_trust_level(driver) == TrustLevel.L1


# ─── penalty class (D-DIS-3) ───────────────────────────────────────
@pytest.mark.parametrize(
    ("at_status", "expected"),
    [
        ("DRAFT", PenaltyClass.NONE),
        ("REQUESTED", PenaltyClass.NONE),
        ("CONFIRMED", PenaltyClass.NONE),
        ("ASSIGNED", PenaltyClass.LATE_CANCELLATION),
        ("AT_PICKUP", PenaltyClass.WASTED_TRIP),
        ("IN_TRANSIT", PenaltyClass.WASTED_TRIP),
    ],
)
def test_compute_penalty_class(at_status: str, expected: str) -> None:
    assert compute_penalty_class(at_status) == expected


# ─── publish guards ────────────────────────────────────────────────
def test_required_fields_complete(draft_job: Any) -> None:
    guards.GUARDS["RequiredFieldsComplete"](draft_job, None, {})  # complete → no raise
    draft_job.cargo = None
    draft_job.declared_value_kes = 0
    with pytest.raises(GuardFailed) as exc:
        guards.GUARDS["RequiredFieldsComplete"](draft_job, None, {})
    assert "cargo" in str(exc.value) and "declared_value_kes" in str(exc.value)


def test_business_verified_with_location(draft_job: Any) -> None:
    guards.GUARDS["BusinessVerifiedWithLocation"](draft_job, None, {})
    draft_job.business.verification_status = "UNVERIFIED"
    draft_job.business.save(update_fields=["verification_status"])
    with pytest.raises(GuardFailed):
        guards.GUARDS["BusinessVerifiedWithLocation"](draft_job, None, {})


def test_cargo_not_prohibited(draft_job: Any) -> None:
    guards.GUARDS["CargoNotProhibited"](draft_job, None, {})
    draft_job.cargo.handling_flags = ["FRAGILE", "HAZARDOUS"]
    with pytest.raises(GuardFailed):
        guards.GUARDS["CargoNotProhibited"](draft_job, None, {})


# ─── negotiate / confirm guards ───────────────────────────────────
def test_no_racing_confirm() -> None:
    guards.GUARDS["NoRacingConfirm"](SimpleNamespace(status="REQUESTED"), None, {})
    with pytest.raises(JobNoLongerAvailable):
        guards.GUARDS["NoRacingConfirm"](SimpleNamespace(status="CONFIRMED"), None, {})


def test_mutual_acceptance_exists() -> None:
    guards.GUARDS["MutualAcceptanceExists"](
        None, None, {"agreed_price_kes": 100, "operator_party": "OPERATOR"}
    )
    with pytest.raises(GuardFailed):
        guards.GUARDS["MutualAcceptanceExists"](None, None, {"agreed_price_kes": 100})


def test_requester_is_not_provider() -> None:
    # solo-operator agreement; the requester (u1) is a different person to the operator (u9)
    job = SimpleNamespace(
        created_by_id="u1",
        agreement=SimpleNamespace(
            operator_party="OPERATOR",
            operator_id="op1",
            group_id=None,
            operator=SimpleNamespace(user_id="u9"),
        ),
    )
    guards.GUARDS["RequesterIsNotProvider"](
        job, None, {"driver_profile": SimpleNamespace(user_id="u2")}
    )
    with pytest.raises(GuardFailed):
        guards.GUARDS["RequesterIsNotProvider"](
            job, None, {"driver_profile": SimpleNamespace(user_id="u1")}
        )


# ─── terminal-reason / dispute guards ─────────────────────────────
def test_failure_reason_provided() -> None:
    guards.GUARDS["FailureReasonProvided"](None, None, {"reason_text": "goods not ready"})
    with pytest.raises(GuardFailed):
        guards.GUARDS["FailureReasonProvided"](None, None, {"reason_text": "   "})


def test_resolution_recorded() -> None:
    guards.GUARDS["ResolutionRecorded"](
        None, None, {"resolution_id": "r1", "routed_job_status": "COMPLETED"}
    )
    with pytest.raises(GuardFailed):
        guards.GUARDS["ResolutionRecorded"](None, None, {"resolution_id": "r1"})


def test_admin_band_authorised() -> None:
    standard = SimpleNamespace(value_band=ValueBand.STANDARD)
    guards.GUARDS["AdminBandAuthorised"](
        standard, SimpleNamespace(roles=set()), {}
    )  # standard: any admin

    high = SimpleNamespace(value_band=ValueBand.HIGH)
    guards.GUARDS["AdminBandAuthorised"](high, SimpleNamespace(roles={"PLATFORM_ADMIN"}), {})
    with pytest.raises(GuardFailed):
        guards.GUARDS["AdminBandAuthorised"](
            high, SimpleNamespace(roles={"OPERATIONS_OFFICER"}), {}
        )


def test_no_open_blocking_dispute_is_noop_without_incidents_app(draft_job: Any) -> None:
    # The incidents app is a later increment; the guard degrades to "no dispute".
    guards.GUARDS["NoOpenBlockingDispute"](draft_job, None, {})
