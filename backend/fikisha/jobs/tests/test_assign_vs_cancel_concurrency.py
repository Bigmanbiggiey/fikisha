"""Real concurrency for a lock-family pair the Phase 2D final-verification
report flagged (N-4) as covered only by architectural inference — the single
Job-row ``select_for_update()`` inside ``JobLifecycleService.transition()`` —
not by a dedicated real-thread test, unlike 8 other pairs already proven that
way (negotiation-accept, OTP-consume, sweep-vs-sweep, sweep-vs-confirm, three
commission races, dispute-open).

Unlike those pairs, ``assign_job()`` (``CONFIRMED -> ASSIGNED``) and
``cancel_job()`` (``* -> CANCELLED``, valid from both ``CONFIRMED`` and
``ASSIGNED``) are **not symmetric** — cancellation reaches its target from
either starting state, so this is not a "whoever gets there first wins, the
loser is rejected" race. Racing them the naive way was tried first and
correctly failed: both threads reported success (assign won the lock,
landed the job on ASSIGNED, and cancel then validly walked ASSIGNED ->
CANCELLED right after) — not a bug, just this test's original premise being
wrong. The real, deterministic property under this row lock is that
cancellation always eventually reaches the terminal state regardless of
interleaving, assignment either transiently wins or is cleanly rejected
once the job is already terminal, and no interleaving ever produces a raw
IntegrityError, a corrupted job, or a duplicate ``Assignment`` row."""

from __future__ import annotations

import threading
from collections.abc import Callable
from typing import Any

import pytest
from django.db import connection

from fikisha.jobs.assignment import assign_job
from fikisha.jobs.constants import CancellationReason, JobStatus
from fikisha.jobs.creation import cancel_job
from fikisha.jobs.errors import TransitionNotAllowed
from fikisha.jobs.models import Assignment

pytestmark = pytest.mark.django_db(transaction=True)


def test_two_threads_racing_assign_and_cancel_on_the_same_confirmed_job(
    make_confirmed_job: Callable,
    eligible_driver: Any,
    eligible_vehicle: Any,
    actor_for: Callable,
    business_actor: Any,
) -> None:
    job = make_confirmed_job(operator=eligible_driver)

    results: list[str] = []
    errors: list[BaseException] = []
    lock = threading.Lock()

    def _assign() -> None:
        try:
            assign_job(
                actor=actor_for(eligible_driver.user),
                job_id=job.id,
                driver_profile_id=eligible_driver.id,
                vehicle_id=eligible_vehicle.id,
            )
            with lock:
                results.append("assigned")
        except BaseException as exc:
            with lock:
                errors.append(exc)
        finally:
            connection.close()

    def _cancel() -> None:
        try:
            cancel_job(
                actor=business_actor,
                job_id=job.id,
                reason_code=CancellationReason.BUSINESS_CHANGED_MIND,
            )
            with lock:
                results.append("cancelled")
        except BaseException as exc:
            with lock:
                errors.append(exc)
        finally:
            connection.close()

    threads = [threading.Thread(target=_assign), threading.Thread(target=_cancel)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    # Cancellation always succeeds, whichever order the row lock serialises
    # the two calls in (from CONFIRMED directly, or from ASSIGNED right
    # after assignment wins the lock first).
    assert "cancelled" in results, (results, errors)
    assert len(results) + len(errors) == 2  # no silently-lost thread

    job.refresh_from_db()
    assert job.status == JobStatus.CANCELLED

    if "assigned" in results:
        # assign won the lock first, transiently succeeded, then cancel
        # validly walked ASSIGNED -> CANCELLED right after — no error at all.
        assert not errors, errors
        assert Assignment.objects.filter(job=job).count() == 1
    else:
        # cancel won the lock first; assign's attempt found the job already
        # CANCELLED (terminal — no such rule), rejected cleanly, not a crash.
        assert len(errors) == 1
        assert isinstance(errors[0], TransitionNotAllowed), errors[0]
        assert Assignment.objects.filter(job=job).count() == 0
