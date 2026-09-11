"""Real concurrency (Step 9 brief §25 "Concurrency"): the Job row lock
``JobLifecycleService.transition()`` already takes is the serialisation
boundary for completion + commission creation; ``CommissionRecord``'s own
``select_for_update()`` is the boundary for concurrent adjustments."""

from __future__ import annotations

import threading
from collections.abc import Callable
from typing import Any

import pytest
from django.db import connection

from fikisha.jobs.constants import CommissionAdjustmentKind, JobStatus
from fikisha.jobs.errors import InvalidCommissionAdjustmentAmount
from fikisha.jobs.models import CommissionRecord

pytestmark = pytest.mark.django_db(transaction=True)


def test_concurrent_completion_attempts_produce_exactly_one_commission_record(
    delivered_job: Callable, admin_actor: Any
) -> None:
    from fikisha.jobs.service import TransitionContext
    from fikisha.jobs.service import transition as job_transition

    job = delivered_job()

    results: list[dict[str, Any]] = []
    errors: list[BaseException] = []
    lock = threading.Lock()

    def _complete() -> None:
        try:
            view = job_transition(
                job_id=job.id,
                to=JobStatus.COMPLETED,
                actor=admin_actor,
                context=TransitionContext(data={"initiator_tokens": []}),
            )
            with lock:
                results.append(view)
        except BaseException as exc:
            with lock:
                errors.append(exc)
        finally:
            connection.close()  # each thread must not share the main connection

    threads = [threading.Thread(target=_complete) for _ in range(5)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    # Exactly one thread's transition succeeds (the job can only leave
    # DELIVERED once); the rest legitimately fail once the first commits —
    # never a raw IntegrityError, never a duplicate commission record.
    assert len(results) == 1, (results, errors)
    assert CommissionRecord.objects.filter(job=job).count() == 1
    job.refresh_from_db()
    assert job.status == JobStatus.COMPLETED


def test_concurrent_commission_creation_calls_are_idempotent_not_duplicating(
    delivered_job: Callable, complete_job: Callable
) -> None:
    """Calling the domain function directly (bypassing the transition/lock a
    caller would normally already hold) from several threads must still never
    produce two rows — the DB ``UNIQUE(job_id)`` is the true backstop even if
    application-level locking discipline is somehow bypassed."""
    from fikisha.jobs import commission

    job = delivered_job()
    complete_job(job)  # the record already exists — every thread should just find it

    found: list[Any] = []
    errors: list[BaseException] = []
    lock = threading.Lock()

    def _ensure() -> None:
        try:
            record = commission.create_commission_record_locked(job=job, actor=None)
            with lock:
                found.append(record.id)
        except BaseException as exc:
            with lock:
                errors.append(exc)
        finally:
            connection.close()

    threads = [threading.Thread(target=_ensure) for _ in range(5)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert not errors, errors
    assert len(set(found)) == 1
    assert CommissionRecord.objects.filter(job=job).count() == 1


def test_concurrent_adjustments_cannot_overdraw_the_effective_commission(
    delivered_job: Callable, complete_job: Callable, admin_actor: Any
) -> None:
    from fikisha.jobs.commission import create_adjustment

    job = delivered_job()
    complete_job(job)
    record = CommissionRecord.objects.get(job=job)
    # Whatever the fixture's default agreed price yields (the calculation
    # itself is covered exhaustively in test_commission_calculation.py) — the
    # point here is purely the concurrency behaviour against that amount.
    # ``reduction = commission_kes // 2`` guarantees any *two* concurrent
    # reductions fit (2 * reduction <= commission_kes, integer division) while
    # a *third* never can (3 * reduction > commission_kes) — deterministic
    # regardless of thread scheduling order.
    reduction = max(record.commission_kes // 2, 1)

    # Three concurrent reductions: exactly two succeed before the effective
    # commission would go negative on the third, whichever thread is last.
    succeeded: list[Any] = []
    failed: list[BaseException] = []
    lock = threading.Lock()

    def _reduce() -> None:
        try:
            create_adjustment(
                commission_record=record,
                actor=admin_actor,
                kind=CommissionAdjustmentKind.REDUCTION,
                amount_kes=-reduction,
                reason="concurrent reduction test",
            )
            with lock:
                succeeded.append(True)
        except InvalidCommissionAdjustmentAmount as exc:
            with lock:
                failed.append(exc)
        finally:
            connection.close()

    threads = [threading.Thread(target=_reduce) for _ in range(3)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert len(succeeded) == 2, (succeeded, failed)
    assert len(failed) == 1
    total_adjusted = sum(record.adjustments.values_list("amount_kes", flat=True))
    assert total_adjusted == -2 * reduction
    assert record.commission_kes + total_adjusted >= 0  # never negative
