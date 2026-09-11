"""Database-level integrity for the commission history tables (Step 9 brief
§9/§20): exactly one CommissionRecord per job, append-only enforcement, and
the CHECK constraints backing the domain invariants."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

import pytest
from django.db import DatabaseError, IntegrityError, connection, transaction

from fikisha.jobs.constants import CommissionAdjustmentKind
from fikisha.jobs.models import CommissionAdjustment, CommissionRecord

pytestmark = pytest.mark.django_db


@pytest.fixture
def a_commission_record(delivered_job: Callable, complete_job: Callable) -> CommissionRecord:
    job = delivered_job()
    complete_job(job)
    return CommissionRecord.objects.get(job=job)


# ─── exactly one per job ─────────────────────────────────────────────
def test_a_second_commission_record_for_the_same_job_is_rejected(
    a_commission_record: CommissionRecord,
) -> None:
    with pytest.raises(IntegrityError):
        with transaction.atomic():
            CommissionRecord.objects.create(
                job=a_commission_record.job,
                agreement=a_commission_record.agreement,
                agreed_price_kes=a_commission_record.agreed_price_kes,
                rate=a_commission_record.rate,
                min_fee_kes=a_commission_record.min_fee_kes,
                cap_kes=a_commission_record.cap_kes,
                commission_kes=a_commission_record.commission_kes,
            )


# ─── append-only ─────────────────────────────────────────────────────
def test_commission_record_update_is_rejected_at_the_database(
    a_commission_record: CommissionRecord,
) -> None:
    with pytest.raises(DatabaseError):
        with transaction.atomic():
            with connection.cursor() as cur:
                cur.execute(
                    "UPDATE commission_record SET commission_kes = 1 WHERE id = %s",
                    [str(a_commission_record.id)],
                )


def test_commission_record_delete_is_rejected_at_the_database(
    a_commission_record: CommissionRecord,
) -> None:
    with pytest.raises(DatabaseError):
        with transaction.atomic():
            with connection.cursor() as cur:
                cur.execute(
                    "DELETE FROM commission_record WHERE id = %s", [str(a_commission_record.id)]
                )


def test_commission_record_update_is_rejected_at_the_orm(
    a_commission_record: CommissionRecord,
) -> None:
    from fikisha.common.models import AppendOnlyModelError

    a_commission_record.commission_kes = 1
    with pytest.raises(AppendOnlyModelError):
        a_commission_record.save()


def test_commission_adjustment_update_is_rejected_at_the_database(
    a_commission_record: CommissionRecord, admin_actor: Any
) -> None:
    from fikisha.jobs.commission import create_adjustment

    adjustment = create_adjustment(
        commission_record=a_commission_record,
        actor=admin_actor,
        kind=CommissionAdjustmentKind.REDUCTION,
        amount_kes=-1000,
        reason="test",
    )
    with pytest.raises(DatabaseError):
        with transaction.atomic():
            with connection.cursor() as cur:
                cur.execute(
                    "UPDATE commission_adjustment SET reason = 'changed' WHERE id = %s",
                    [str(adjustment.id)],
                )


def test_commission_adjustment_delete_is_rejected_at_the_database(
    a_commission_record: CommissionRecord, admin_actor: Any
) -> None:
    from fikisha.jobs.commission import create_adjustment

    adjustment = create_adjustment(
        commission_record=a_commission_record,
        actor=admin_actor,
        kind=CommissionAdjustmentKind.REDUCTION,
        amount_kes=-1000,
        reason="test",
    )
    with pytest.raises(DatabaseError):
        with transaction.atomic():
            with connection.cursor() as cur:
                cur.execute("DELETE FROM commission_adjustment WHERE id = %s", [str(adjustment.id)])


# ─── CHECK constraints ────────────────────────────────────────────────
def test_negative_agreed_price_is_rejected(delivered_job: Callable) -> None:
    job = delivered_job()
    with pytest.raises(IntegrityError):
        with transaction.atomic():
            CommissionRecord.objects.create(
                job=job,
                agreement=job.agreement,
                agreed_price_kes=-1,
                rate="0.1000",
                min_fee_kes=4000,
                cap_kes=500000,
                commission_kes=1000,
            )


def test_negative_commission_amount_is_rejected(delivered_job: Callable) -> None:
    job = delivered_job()
    with pytest.raises(IntegrityError):
        with transaction.atomic():
            CommissionRecord.objects.create(
                job=job,
                agreement=job.agreement,
                agreed_price_kes=job.agreement.agreed_price_kes,
                rate="0.1000",
                min_fee_kes=4000,
                cap_kes=500000,
                commission_kes=-1,
            )


def test_a_positive_adjustment_amount_is_rejected_at_the_database(
    a_commission_record: CommissionRecord, admin_actor: Any
) -> None:
    with pytest.raises(IntegrityError):
        with transaction.atomic():
            CommissionAdjustment.objects.create(
                commission_record=a_commission_record,
                kind=CommissionAdjustmentKind.REDUCTION,
                amount_kes=1000,  # positive — an increase, never allowed
                reason="test",
                authorized_by=admin_actor.user,
            )


def test_a_zero_adjustment_amount_is_rejected_at_the_database(
    a_commission_record: CommissionRecord, admin_actor: Any
) -> None:
    with pytest.raises(IntegrityError):
        with transaction.atomic():
            CommissionAdjustment.objects.create(
                commission_record=a_commission_record,
                kind=CommissionAdjustmentKind.REDUCTION,
                amount_kes=0,
                reason="test",
                authorized_by=admin_actor.user,
            )
