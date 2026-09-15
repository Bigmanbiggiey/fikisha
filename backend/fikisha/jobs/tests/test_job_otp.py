"""Job-scoped OTP generation + verification (chain-of-custody.md §4)."""

from __future__ import annotations

from collections.abc import Callable
from datetime import timedelta
from typing import Any

import pytest
from django.utils import timezone

from fikisha.jobs import otp as otp_service
from fikisha.jobs.errors import OtpExpired, OtpInvalid, OtpLocked, OtpNotIssued
from fikisha.jobs.models import PickupOtpChallenge

pytestmark = pytest.mark.django_db


def test_issue_returns_dev_code_and_hashes_at_rest(
    make_assigned_job: Callable, admin_actor: Any
) -> None:
    job = make_assigned_job()
    issued = otp_service.issue_otp(
        job=job, purpose="PICKUP_HANDOVER", phone="+254700111222", actor=admin_actor
    )
    assert issued.dev_code == "000000"
    challenge = PickupOtpChallenge.objects.get(id=issued.challenge_id)
    assert challenge.code_hash != "000000" and challenge.sent_to_phone == "+254700111222"
    assert (challenge.expires_at - timezone.now()) <= timedelta(seconds=301)


def test_issue_without_a_phone_raises(make_assigned_job: Callable) -> None:
    job = make_assigned_job()
    with pytest.raises(OtpNotIssued):
        otp_service.issue_otp(job=job, purpose="PICKUP_HANDOVER", phone="")


def test_verify_happy_path_consumes_single_use(make_assigned_job: Callable) -> None:
    job = make_assigned_job()
    otp_service.issue_otp(job=job, purpose="PICKUP_HANDOVER", phone="+254700111222")
    otp_service.verify_otp(job=job, purpose="PICKUP_HANDOVER", code="000000")
    assert otp_service.has_consumed_otp(job=job, purpose="PICKUP_HANDOVER")
    # replay: the consumed challenge is gone, and nothing else is issued
    with pytest.raises(OtpNotIssued):
        otp_service.verify_otp(job=job, purpose="PICKUP_HANDOVER", code="000000")


def test_wrong_code_then_lock(make_assigned_job: Callable) -> None:
    job = make_assigned_job()
    otp_service.issue_otp(job=job, purpose="PICKUP_HANDOVER", phone="+254700111222")
    for _ in range(4):
        with pytest.raises(OtpInvalid):
            otp_service.verify_otp(job=job, purpose="PICKUP_HANDOVER", code="111111")
    with pytest.raises(OtpLocked):
        otp_service.verify_otp(job=job, purpose="PICKUP_HANDOVER", code="111111")
    challenge = PickupOtpChallenge.objects.filter(job=job).latest("seq")
    assert challenge.attempts == 5


def test_expired_code_is_rejected(make_assigned_job: Callable, monkeypatch: Any) -> None:
    job = make_assigned_job()
    otp_service.issue_otp(job=job, purpose="PICKUP_HANDOVER", phone="+254700111222")
    future = timezone.now() + timedelta(hours=1)
    monkeypatch.setattr("django.utils.timezone.now", lambda: future)
    with pytest.raises(OtpExpired):
        otp_service.verify_otp(job=job, purpose="PICKUP_HANDOVER", code="000000")


def test_reissue_is_rate_limited_per_job(make_assigned_job: Callable) -> None:
    from fikisha.common.exceptions import RateLimitedError

    job = make_assigned_job()
    for _ in range(5):
        otp_service.issue_otp(job=job, purpose="PICKUP_HANDOVER", phone="+254700111222")
    with pytest.raises(RateLimitedError):
        otp_service.issue_otp(job=job, purpose="PICKUP_HANDOVER", phone="+254700111222")


def test_reissue_supersedes_the_previous_code(make_assigned_job: Callable) -> None:
    job = make_assigned_job()
    otp_service.issue_otp(job=job, purpose="PICKUP_HANDOVER", phone="+254700111222")
    otp_service.issue_otp(job=job, purpose="PICKUP_HANDOVER", phone="+254700111222")
    # verify consumes the newest un-consumed challenge; both share the fixed dev code
    otp_service.verify_otp(job=job, purpose="PICKUP_HANDOVER", code="000000")
    newest = PickupOtpChallenge.objects.filter(job=job).latest("seq")
    assert newest.consumed_at is not None


def test_reissue_still_supersedes_when_created_at_ties(
    make_assigned_job: Callable, monkeypatch: Any
) -> None:
    """Regression for the tiebreak defect found in the Phase 2D final
    verification (2026-09-11): verify_otp() previously picked the newest
    challenge via `order_by("-created_at")`, but two challenges issued in
    immediate succession can receive an identical `auto_now_add` timestamp
    (measured ~3% under real reissue timing) — on a tie, Postgres's row order
    is unspecified, so the superseded challenge could be validated instead.
    `seq` is a strictly-monotonic tiebreaker that never ties."""
    job = make_assigned_job()
    frozen = timezone.now()
    monkeypatch.setattr("django.utils.timezone.now", lambda: frozen)
    otp_service.issue_otp(job=job, purpose="PICKUP_HANDOVER", phone="+254700111222")
    otp_service.issue_otp(job=job, purpose="PICKUP_HANDOVER", phone="+254700111222")
    challenges = list(PickupOtpChallenge.objects.filter(job=job).order_by("seq"))
    assert len(challenges) == 2
    assert challenges[0].created_at == challenges[1].created_at  # the tie was actually forced
    assert challenges[0].seq < challenges[1].seq

    otp_service.verify_otp(job=job, purpose="PICKUP_HANDOVER", code="000000")
    challenges[0].refresh_from_db()
    challenges[1].refresh_from_db()
    assert challenges[1].consumed_at is not None  # the newer (higher-seq) challenge won
    assert challenges[0].consumed_at is None
