"""Phase 2D Step 11 — scheduled sweeps (plan §19 / ADR-2D-08 / Q-5).

A sweep is a maintenance trigger over the already-approved
``JobLifecycleService.transition()`` — every test here proves candidate
selection + the drive loop, never a duplicated guard/business rule (the
guards themselves are exercised by the existing lifecycle-engine suite)."""

from __future__ import annotations

import threading
from collections.abc import Callable
from datetime import timedelta
from typing import Any

import pytest
from django.db import connection
from django.utils import timezone

from fikisha.common.exceptions import DomainError
from fikisha.jobs import tasks
from fikisha.jobs.constants import JobStatus
from fikisha.jobs.errors import NotAuthorisedToInitiate
from fikisha.jobs.models import CommissionRecord, FailureRecord, Job
from fikisha.jobs.service import TransitionContext, transition

pytestmark = pytest.mark.django_db


def _backdate(job: Job, field: str, hours: float) -> None:
    setattr(job, field, timezone.now() - timedelta(hours=hours))
    job.save(update_fields=[field])


@pytest.fixture
def requested_job(draft_job: Job, business_actor: Any) -> Job:
    from fikisha.jobs.creation import submit_job

    submit_job(actor=business_actor, job_id=draft_job.id)
    draft_job.refresh_from_db()
    return draft_job


# ── expire_requests ───────────────────────────────────────────────────
class TestExpireRequests:
    def test_a_stale_request_is_failed(self, requested_job: Job) -> None:
        _backdate(requested_job, "published_at", 25)
        stats = tasks.expire_requests()
        assert stats == {"candidates": 1, "changed": 1, "skipped": 0, "failed": 0}
        requested_job.refresh_from_db()
        assert requested_job.status == JobStatus.FAILED
        record = FailureRecord.objects.get(job=requested_job)
        assert record.reason_text == "EXPIRED_NO_OFFER"
        assert record.recorded_by_admin is None  # SystemActor, not a human admin

    def test_a_fresh_request_is_not_a_candidate(self, requested_job: Job) -> None:
        stats = tasks.expire_requests()
        assert stats == {"candidates": 0, "changed": 0, "skipped": 0, "failed": 0}
        requested_job.refresh_from_db()
        assert requested_job.status == JobStatus.REQUESTED

    def test_empty_dataset(self) -> None:
        assert tasks.expire_requests() == {
            "candidates": 0,
            "changed": 0,
            "skipped": 0,
            "failed": 0,
        }

    def test_repeated_execution_is_idempotent(self, requested_job: Job) -> None:
        _backdate(requested_job, "published_at", 25)
        first = tasks.expire_requests()
        second = tasks.expire_requests()
        assert first["changed"] == 1
        assert second == {"candidates": 0, "changed": 0, "skipped": 0, "failed": 0}
        assert FailureRecord.objects.filter(job=requested_job).count() == 1

    def test_bounded_batching(
        self,
        draft_job: Job,
        verified_business: Any,
        user: Any,
        business_actor: Any,
        requested_job: Job,
    ) -> None:
        from fikisha.jobs.creation import submit_job
        from fikisha.jobs.models import CargoDetails, JobLocation, VehicleRequirement

        def _extra_requested() -> Job:
            cargo = CargoDetails.objects.create(description="x", declared_value_kes=100_000)
            pickup = JobLocation.objects.create(
                type="PICKUP", source_kind="AD_HOC", address_text="A"
            )
            dest = JobLocation.objects.create(
                type="DESTINATION", source_kind="AD_HOC", address_text="B"
            )
            vreq = VehicleRequirement.objects.create(min_payload_kg=100)
            job = Job.objects.create(
                business=verified_business,
                created_by=user,
                status=JobStatus.DRAFT,
                pickup_location=pickup,
                destination_location=dest,
                cargo=cargo,
                vehicle_requirement=vreq,
                proposed_price_kes=50_000,
                declared_value_kes=100_000,
            )
            submit_job(actor=business_actor, job_id=job.id)
            job.refresh_from_db()
            return job

        jobs = [requested_job, _extra_requested(), _extra_requested()]
        for j in jobs:
            _backdate(j, "published_at", 25)

        stats = tasks.expire_requests(batch_size=2)
        assert stats["candidates"] == 2
        assert stats["changed"] == 2
        remaining = Job.objects.filter(status=JobStatus.REQUESTED).count()
        assert remaining == 1

    def test_an_invalid_candidate_is_skipped_not_failed(self, requested_job: Job) -> None:
        """Robustness against a stale/incorrect candidate list: a job that is
        no longer actually eligible (already FAILED) is skipped cleanly, and
        does not stop a genuine candidate in the same batch from changing."""
        from fikisha.jobs.constants import TrustLevel, ValueBand

        _backdate(requested_job, "published_at", 25)
        already_gone = Job.objects.create(
            business=requested_job.business,
            created_by=requested_job.created_by,
            status=JobStatus.FAILED,
            declared_value_kes=1,
            value_band=ValueBand.STANDARD,  # ck_job_band_set_once_published
            required_trust_level=TrustLevel.L1,
        )
        stats = tasks._run_sweep(
            name="expire_requests",
            job_ids=[already_gone.id, requested_job.id],
            to=JobStatus.FAILED,
            ctx=TransitionContext(data={"expiry_reached": True}),
        )
        assert stats == {"candidates": 2, "changed": 1, "skipped": 1, "failed": 0}

    def test_a_single_unexpected_exception_does_not_abort_the_batch(
        self, requested_job: Job, monkeypatch: Any
    ) -> None:
        _backdate(requested_job, "published_at", 25)
        real_transition = tasks.transition

        def _flaky(*, job_id: Any, **kwargs: Any) -> Any:
            if str(job_id) == str(requested_job.id):
                raise RuntimeError("simulated worker crash mid-candidate")
            return real_transition(job_id=job_id, **kwargs)

        monkeypatch.setattr(tasks, "transition", _flaky)
        stats = tasks.expire_requests()
        assert stats == {"candidates": 1, "changed": 0, "skipped": 0, "failed": 1}
        requested_job.refresh_from_db()
        assert requested_job.status == JobStatus.REQUESTED  # untouched, not half-applied


# ── autocomplete_delivered: retired (founder 2026-10-20, PD-3) ────────
class TestAutocompleteDeliveredIsRetired:
    def test_it_never_completes_a_job_and_counts_those_waiting(
        self, delivered_job: Callable
    ) -> None:
        job = delivered_job()
        _backdate(job, "delivered_at", 25)  # past the old 24 h window
        assert tasks.autocomplete_delivered() == {"retired": 1, "awaiting_sender": 1}
        job.refresh_from_db()
        assert job.status == JobStatus.DELIVERED
        assert not CommissionRecord.objects.filter(job=job).exists()

    def test_within_the_window_a_job_is_not_yet_awaiting(self, delivered_job: Callable) -> None:
        delivered_job()
        assert tasks.awaiting_sender_job_ids() == []

    def test_high_value_uses_the_longer_window(self, delivered_job: Callable) -> None:
        job = delivered_job()
        Job.objects.filter(id=job.id).update(is_high_value=True)
        _backdate(job, "delivered_at", 30)
        assert tasks.awaiting_sender_job_ids() == []
        _backdate(job, "delivered_at", 50)
        assert tasks.awaiting_sender_job_ids() == [job.id]


# ── Celery registration ────────────────────────────────────────────────
class TestCeleryTaskRegistration:
    def test_jobs_tasks_are_registered_under_the_documented_names(self) -> None:
        assert tasks.expire_requests.name == "fikisha.jobs.tasks.expire_requests"
        assert tasks.autocomplete_delivered.name == "fikisha.jobs.tasks.autocomplete_delivered"

    def test_verification_task_is_registered_but_not_beat_scheduled(self) -> None:
        from django.conf import settings

        from fikisha.verification.tasks import expire_due as verification_expire_due

        assert verification_expire_due.name == "fikisha.verification.tasks.expire_due"
        # ADR-2D-08: deliberately command-only, unlike the two jobs sweeps.
        assert "fikisha.verification.tasks.expire_due" not in {
            entry["task"] for entry in settings.CELERY_BEAT_SCHEDULE.values()
        }

    def test_jobs_sweeps_are_beat_scheduled(self) -> None:
        from django.conf import settings

        scheduled = {entry["task"] for entry in settings.CELERY_BEAT_SCHEDULE.values()}
        assert "fikisha.jobs.tasks.expire_requests" in scheduled
        # retired: jobs no longer complete on a timer (PD-3)
        assert "fikisha.jobs.tasks.autocomplete_delivered" not in scheduled


# ── Concurrency (real threads need real cross-connection visibility, hence
#    transaction=True -- the same pattern Step 10's concurrent HTTP tests use)
class TestConcurrency:
    @pytest.mark.django_db(transaction=True)
    def test_two_sweep_workers_racing_the_same_stale_request(self, requested_job: Job) -> None:
        _backdate(requested_job, "published_at", 25)
        results: list[dict[str, int]] = []
        lock = threading.Lock()

        def _run() -> None:
            try:
                stats = tasks.expire_requests()
                with lock:
                    results.append(stats)
            finally:
                connection.close()

        threads = [threading.Thread(target=_run) for _ in range(3)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        total_changed = sum(r["changed"] for r in results)
        assert total_changed == 1  # exactly one worker's transition() wins the row lock
        assert FailureRecord.objects.filter(job=requested_job).count() == 1
        requested_job.refresh_from_db()
        assert requested_job.status == JobStatus.FAILED

    @pytest.mark.django_db(transaction=True)
    def test_sweep_races_an_ordinary_confirm_of_the_same_request(
        self, requested_job: Job, admin_actor: Any, make_verified_operator: Callable
    ) -> None:
        """A REQUESTED job an admin confirms (-> CONFIRMED, the same
        negotiation-bypass shape ``make_confirmed_job`` uses) at the same
        moment the sweep tries to expire it: whichever transition wins the
        row lock first determines the outcome; the loser gets a clean domain
        rejection, never a corrupted/partial state."""
        from fikisha.jobs.constants import OperatorParty

        _backdate(requested_job, "published_at", 25)
        operator = make_verified_operator("+254700900555", "Racer Transport")
        start = threading.Barrier(2)
        errors: list[BaseException] = []

        def _confirm() -> None:
            start.wait()
            try:
                transition(
                    job_id=requested_job.id,
                    to=JobStatus.CONFIRMED,
                    actor=admin_actor,
                    context=TransitionContext(
                        data={
                            "initiator_tokens": ["ADMIN"],
                            "operator_party": OperatorParty.OPERATOR,
                            "operator_id": str(operator.id),
                            "agreed_price_kes": requested_job.proposed_price_kes,
                            "accepting_entry_ids": [],
                        }
                    ),
                )
            except Exception as exc:  # recorded, not swallowed
                errors.append(exc)
            finally:
                connection.close()

        def _sweep() -> None:
            start.wait()
            try:
                tasks.expire_requests()
            finally:
                connection.close()

        t1 = threading.Thread(target=_confirm)
        t2 = threading.Thread(target=_sweep)
        t1.start()
        t2.start()
        t1.join()
        t2.join()

        requested_job.refresh_from_db()
        # Whichever path actually won the row lock, the job lands in exactly
        # one clean terminal-or-progressed state -- never half-applied, and
        # the loser's exception (if any) is an ordinary domain rejection.
        assert requested_job.status in {JobStatus.CONFIRMED, JobStatus.FAILED}
        for exc in errors:
            assert isinstance(exc, DomainError)


# ── Privilege boundary ──────────────────────────────────────────────────
class TestPrivilegeBoundary:
    def test_an_ordinary_business_actor_cannot_force_expire_their_own_request(
        self, requested_job: Job, business_actor: Any
    ) -> None:
        with pytest.raises(NotAuthorisedToInitiate):
            transition(
                job_id=requested_job.id,
                to=JobStatus.FAILED,
                actor=business_actor,
                context=TransitionContext(data={"expiry_reached": True}),
            )

    def test_no_http_endpoint_exposes_a_raw_scheduler_transition(self) -> None:
        """No route lets a client trigger ``expire_requests``/
        ``autocomplete_delivered`` directly, or set an arbitrary target
        status — ``fail-at-pickup`` is the one pre-existing, already-reviewed
        Step 10 custody endpoint that legitimately contains "fail"."""
        from fikisha.jobs.api import urls as jobs_urls

        patterns = [str(p.pattern) for p in jobs_urls.urlpatterns]
        forbidden = ("expire", "autocomplete", "sweep", "scheduler")
        assert not any(any(term in p for term in forbidden) for p in patterns)
        assert [p for p in patterns if "fail" in p] == ["jobs/<uuid:job_id>/custody/fail-at-pickup"]
