"""The Platform Admin commission ledger read (Design Phase 6 Increment 9,
P3 §19.4, ADR-2D-38). Every ``commission_record`` with its adjustments and
the effective amount. Read-only: records and adjustments are append-only,
and nothing here moves money. Fikisha records commission; the fare moves
party-to-party.

Since the commission split (ADR-2D-55) a completed job has a record per
paying side (``party``): the business's and the operator's.

Weekly statements and manual settlement live in ``fikisha.statements``
(ADR-2D-42); eTIMS is not built. This ledger stays the per-job record.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from django.db.models import QuerySet, Sum
from django.db.models.functions import Coalesce

from fikisha.business import services as business_services
from fikisha.common.exceptions import DomainError
from fikisha.groups import services as groups_services
from fikisha.jobs.constants import CommissionParty
from fikisha.jobs.models import CommissionRecord
from fikisha.jobs.ops import job_reference
from fikisha.operators import services as operators_services


class InvalidLedgerFilter(DomainError):
    default_code = "invalid_filter"


def queryset(
    *,
    since: datetime | None = None,
    until: datetime | None = None,
    operator_id: Any = None,
    group_id: Any = None,
    business_id: Any = None,
    party: str | None = None,
) -> QuerySet[CommissionRecord]:
    qs = CommissionRecord.objects.select_related(
        "job", "agreement", "config_version"
    ).prefetch_related("adjustments")
    if since is not None:
        qs = qs.filter(created_at__gte=since)
    if until is not None:
        qs = qs.filter(created_at__lt=until)
    if party is not None:
        if party not in CommissionParty.values:
            raise InvalidLedgerFilter("party must be BUSINESS or OPERATOR.")
        qs = qs.filter(party=party)
    # an operator or group owes only the operator side; a business only its own
    if operator_id is not None:
        qs = qs.filter(party=CommissionParty.OPERATOR, agreement__operator_id=operator_id)
    if group_id is not None:
        qs = qs.filter(party=CommissionParty.OPERATOR, agreement__group_id=group_id)
    if business_id is not None:
        qs = qs.filter(party=CommissionParty.BUSINESS, job__business_id=business_id)
    return qs


def _payee(record: CommissionRecord) -> dict[str, Any]:
    """Who owes this record."""
    if record.party == CommissionParty.BUSINESS:
        return {
            "kind": "BUSINESS",
            "id": str(record.job.business_id),
            "name": business_services.display_name_for(record.job.business_id),
        }
    agreement = record.agreement
    if agreement.operator_id is not None:
        return {
            "kind": "OPERATOR",
            "id": str(agreement.operator_id),
            "name": operators_services.display_name_for(agreement.operator_id),
        }
    return {
        "kind": "GROUP",
        "id": str(agreement.group_id),
        "name": groups_services.display_name_for(agreement.group_id),
    }


def row(record: CommissionRecord) -> dict[str, Any]:
    adjustments = [
        {
            "id": str(a.id),
            "kind": a.kind,
            "amount_kes": a.amount_kes,
            "reason": a.reason,
            "by_platform_admin": a.authorized_by_is_platform_admin,
            "source_dispute_id": str(a.source_dispute_id) if a.source_dispute_id else None,
            "created_at": a.created_at.isoformat(),
        }
        for a in sorted(record.adjustments.all(), key=lambda a: a.created_at)
    ]
    adjustments_kes = sum(a["amount_kes"] for a in adjustments)
    return {
        "id": str(record.id),
        "job_id": str(record.job_id),
        "job_reference": job_reference(record.job_id),
        "business_name": business_services.display_name_for(record.job.business_id),
        "party": record.party,
        "payee": _payee(record),
        "agreed_price_kes": record.agreed_price_kes,
        "rate": str(record.rate),
        "min_fee_kes": record.min_fee_kes,
        "cap_kes": record.cap_kes,
        "commission_kes": record.commission_kes,
        "adjustments_kes": adjustments_kes,
        "effective_kes": record.commission_kes + adjustments_kes,
        "config_version": record.config_version.version if record.config_version else None,
        "adjustments": adjustments,
        "created_at": record.created_at.isoformat(),
    }


def totals(qs: QuerySet[CommissionRecord]) -> dict[str, int]:
    """Sums over the whole filtered ledger (not just one page)."""
    from fikisha.jobs.models import CommissionAdjustment

    commission = qs.aggregate(total=Coalesce(Sum("commission_kes"), 0))["total"]
    adjustments = CommissionAdjustment.objects.filter(
        commission_record__in=qs.values("id")
    ).aggregate(total=Coalesce(Sum("amount_kes"), 0))["total"]
    return {
        "records": qs.count(),
        "commission_kes": commission,
        "adjustments_kes": adjustments,
        "effective_kes": commission + adjustments,
    }
