"""Late-cancellation review flags for businesses (D-DIS-3, trust-and-disputes
plan A7; CF-1, CF-2)."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

import pytest

from fikisha.audit.models import AuditLogEntry
from fikisha.common.models import AppendOnlyModelError
from fikisha.jobs import cancellation_flags
from fikisha.jobs.creation import cancel_job
from fikisha.jobs.models import CancellationFlag, CancellationFlagReview, CancellationRecord

pytestmark = pytest.mark.django_db


@pytest.fixture
def ops(ops_officer: Any, actor_for: Callable) -> Any:
    return actor_for(ops_officer)


def _cancel(job: Any, actor: Any) -> None:
    cancel_job(actor=actor, job_id=job.id, reason_code="BUSINESS_CHANGED_MIND")


def test_three_late_cancellations_by_the_business_open_one_flag(
    make_assigned_job: Callable, business_actor: Any, verified_business: Any
) -> None:
    for _ in range(2):
        _cancel(make_assigned_job(), business_actor)
    assert not CancellationFlag.objects.exists()
    _cancel(make_assigned_job(), business_actor)
    flag = CancellationFlag.objects.get()
    assert flag.business_id == verified_business.id
    assert len(flag.record_ids) == 3
    assert AuditLogEntry.objects.filter(action="cancellation_flag.opened").exists()
    _cancel(make_assigned_job(), business_actor)
    assert CancellationFlag.objects.count() == 1  # one open flag per business


def test_the_cancelling_side_and_business_are_recorded(
    make_assigned_job: Callable, business_actor: Any, admin_actor: Any
) -> None:
    _cancel(make_assigned_job(), business_actor)
    cancel_job(
        actor=admin_actor,
        job_id=make_assigned_job().id,
        reason_code="ADMIN_ACTION",
        reason_text="Asked by the stage chair.",
    )
    sides = sorted(CancellationRecord.objects.values_list("cancelling_side", flat=True))
    assert sides == ["BUSINESS", "STAFF"]
    assert all(r.business_id for r in CancellationRecord.objects.all())


def test_staff_cancellations_count_against_no_one(
    make_assigned_job: Callable, admin_actor: Any
) -> None:
    for _ in range(3):
        cancel_job(
            actor=admin_actor,
            job_id=make_assigned_job().id,
            reason_code="ADMIN_ACTION",
            reason_text="Operator unreachable.",
        )
    assert not CancellationFlag.objects.exists()


def test_older_rows_are_attributed_from_the_stored_role(
    make_confirmed_job: Callable, verified_business: Any, user: Any, eligible_driver: Any
) -> None:
    for role in ("USER", "USER", "OPERATIONS_OFFICER"):
        CancellationRecord.objects.create(
            job=make_confirmed_job(operator=eligible_driver),
            cancelled_by_role=role,
            cancelled_by_user=user,
            at_status="ASSIGNED",
            penalty_class="LATE_CANCELLATION",
        )
    assert cancellation_flags.qualifying_records(verified_business.id).count() == 2


def test_staff_clear_or_close_as_mistaken_with_a_note(
    make_assigned_job: Callable, business_actor: Any, ops: Any
) -> None:
    for _ in range(3):
        _cancel(make_assigned_job(), business_actor)
    flag = CancellationFlag.objects.get()
    with pytest.raises(cancellation_flags.FlagNoteRequired):
        cancellation_flags.review_flag(actor=ops, flag_id=flag.id, mistaken=False, note="ok")
    cancellation_flags.review_flag(
        actor=ops, flag_id=flag.id, mistaken=True, note="Two were the same job reposted."
    )
    flag.refresh_from_db()
    assert flag.status == "MISTAKEN"
    with pytest.raises(cancellation_flags.FlagNotOpen):
        cancellation_flags.review_flag(
            actor=ops, flag_id=flag.id, mistaken=False, note="Reviewed again later."
        )
    review = CancellationFlagReview.objects.get()
    review.note = "edited"
    with pytest.raises(AppendOnlyModelError):
        review.save()


def test_a_business_party_cannot_review(make_assigned_job: Callable, business_actor: Any) -> None:
    for _ in range(3):
        _cancel(make_assigned_job(), business_actor)
    from fikisha.common.exceptions import AuthorizationError

    with pytest.raises(AuthorizationError):
        cancellation_flags.review_flag(
            actor=business_actor,
            flag_id=CancellationFlag.objects.get().id,
            mistaken=True,
            note="Not our fault at all.",
        )


class TestApi:
    def test_ops_list_and_review(
        self,
        client_for: Callable,
        make_assigned_job: Callable,
        business_actor: Any,
        ops_officer: Any,
    ) -> None:
        for _ in range(3):
            _cancel(make_assigned_job(), business_actor)
        client = client_for(ops_officer)
        listed = client.get("/api/v1/ops/cancellation-flags")
        assert listed.status_code == 200
        [row] = listed.json()["data"]
        assert row["count"] == 3
        r = client.post(
            f"/api/v1/ops/cancellation-flags/{row['id']}/review",
            {"outcome": "CLEARED", "note": "Spoke to the owner; seasonal stock."},
            format="json",
        )
        assert r.status_code == 200, r.content
        assert r.json()["status"] == "CLEARED"
        assert client.get("/api/v1/ops/cancellation-flags").json()["data"] == []

    def test_a_business_user_gets_403(self, client_for: Callable, user: Any) -> None:
        assert client_for(user).get("/api/v1/ops/cancellation-flags").status_code == 403
