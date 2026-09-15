"""Phase 2D Step 12 (invariant/property tests): audit/outbox atomicity, swept
across the ``jobs`` app's self-atomic (``@transaction.atomic``) entry points
that were not already covered by a dedicated rollback test.

The BLOCKER-1 corrective pass (Phase 2D final-verification report) found and
fixed 7 ``incidents.services`` functions that wrote a domain row and called
``audit.record()`` with **no** enclosing transaction — invisible under
``pytest.mark.django_db``'s own implicit atomic wrapper, real over HTTP. A
module-by-module sweep for this same class of gap (every ``audit.record()``
call site in ``jobs``/``negotiation``, checked against whether it is itself
``@transaction.atomic`` or is only ever called from one) found no further
unwrapped instance — but "wrapped" was previously true only by inspection,
not by a direct forced-failure test proving the wrapper actually rolls
everything back. This file adds that direct proof for the functions that
didn't already have one (``transition()`` and ``jobs.recipient.confirm_receipt``
already do, from the BLOCKER-1/N-6 passes)."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

import pytest

from fikisha.audit.models import AuditLogEntry
from fikisha.outbox.models import OutboxEvent

pytestmark = pytest.mark.django_db(transaction=True)


def _boom(*_a: Any, **_kw: Any) -> Any:
    raise RuntimeError("simulated downstream failure")


class TestTransitionRollback:
    """``JobLifecycleService.transition()`` itself — the single writer of
    ``job.status`` and the most heavily-relied-on atomic boundary in the
    domain. Proven here directly rather than only inferred from the many
    concurrency tests that already depend on its lock."""

    def test_a_downstream_audit_failure_rolls_back_the_whole_transition(
        self, draft_job: Any, business_actor: Any, monkeypatch: Any
    ) -> None:
        from fikisha.jobs import service as jobs_service
        from fikisha.jobs.constants import JobStatus
        from fikisha.jobs.models import JobEvent

        monkeypatch.setattr(jobs_service.audit, "record", _boom)
        job = draft_job
        with pytest.raises(RuntimeError):
            jobs_service.transition(
                job_id=job.id,
                to=JobStatus.REQUESTED,
                actor=business_actor,
                context=jobs_service.TransitionContext(
                    data={"initiator_tokens": ["BUSINESS_OWNER_OR_DISPATCHER"]}
                ),
            )
        job.refresh_from_db()
        assert job.status == JobStatus.DRAFT  # unchanged
        assert JobEvent.objects.filter(job=job).count() == 0
        assert AuditLogEntry.objects.filter(entity_type="job", entity_id=job.id).count() == 0


class TestCreateDraftRollback:
    def _payload(self) -> dict[str, Any]:
        return {
            "pickup_location": {"address_text": "Depot, Kitengela"},
            "destination_location": {"address_text": "Shop 4, Kitengela"},
            "cargo": {"description": "20 cartons", "declared_value_kes": 1_200_000},
        }

    def test_success_is_fully_atomic(self, business_actor: Any, verified_business: Any) -> None:
        from fikisha.jobs.creation import create_draft
        from fikisha.jobs.models import Job

        job = create_draft(
            actor=business_actor, business_id=verified_business.id, data=self._payload()
        )
        assert Job.objects.filter(id=job.id).exists()
        assert AuditLogEntry.objects.filter(entity_type="job", entity_id=job.id).exists()
        assert OutboxEvent.objects.filter(aggregate_type="job", aggregate_id=str(job.id)).exists()

    def test_a_downstream_audit_failure_rolls_back_the_draft_job(
        self, business_actor: Any, verified_business: Any, monkeypatch: Any
    ) -> None:
        from fikisha.jobs import creation
        from fikisha.jobs.models import Job

        before = Job.objects.count()
        monkeypatch.setattr(creation.audit, "record", _boom)
        with pytest.raises(RuntimeError):
            creation.create_draft(
                actor=business_actor, business_id=verified_business.id, data=self._payload()
            )
        assert Job.objects.count() == before
        assert OutboxEvent.objects.filter(aggregate_type="job").count() == 0


class TestDecideHighValueRollback:
    HIGH = 30_000_000  # KES 300,000 -> HIGH band

    def test_a_downstream_audit_failure_rolls_back_the_approval(
        self, make_confirmed_job: Callable, eligible_driver: Any, admin_actor: Any, monkeypatch: Any
    ) -> None:
        from fikisha.jobs import high_value
        from fikisha.jobs.models import HighValueApproval

        job = make_confirmed_job(operator=eligible_driver, declared_value_kes=self.HIGH)
        # baseline, not zero: make_confirmed_job's own REQUESTED/CONFIRMED
        # transitions already emitted job-aggregate outbox events.
        outbox_before = OutboxEvent.objects.filter(
            aggregate_type="job", aggregate_id=str(job.id)
        ).count()
        monkeypatch.setattr(high_value.audit, "record", _boom)
        with pytest.raises(RuntimeError):
            high_value.decide_high_value(
                actor=admin_actor, job_id=job.id, decision="APPROVED", rationale="x"
            )
        assert HighValueApproval.objects.filter(job=job).count() == 0
        assert (
            OutboxEvent.objects.filter(aggregate_type="job", aggregate_id=str(job.id)).count()
            == outbox_before
        )
