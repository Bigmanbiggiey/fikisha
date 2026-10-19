"""The verification queue by applicant (assessment 2026-10-19, part 5).

Reviewers work through *applicants* (an operator, a business, a group), not
loose records: each applicant's own records come together with the records of
what it owns (an operator's vehicles and the operating locations they
created; a group's vehicles). Read-only; every decision still goes through
the per-record endpoints and their rules (``reviewer_is_submitter``,
append-only decisions), and evidence bytes are still fetched and logged one
document at a time.
"""

from __future__ import annotations

from collections.abc import Iterable
from typing import Any

from django.db.models import Q

from fikisha.operators.models import OperatingBase, OperatorProfile, OperatorStatus
from fikisha.vehicles.models import Vehicle
from fikisha.verification import services
from fikisha.verification.models import State, VerificationRecord

OPEN_STATES = (State.SUBMITTED, State.IN_REVIEW, State.INFO_REQUESTED)
KINDS = ("OPERATOR", "BUSINESS", "GROUP")


def _records(q: Q) -> list[VerificationRecord]:
    return list(
        VerificationRecord.objects.filter(q)
        .prefetch_related("decisions", "evidence__evidence_object")
        .order_by("created_at")
    )


def _summary(records: Iterable[VerificationRecord]) -> dict[str, Any]:
    rows = list(records)
    open_rows = [r for r in rows if r.state in OPEN_STATES]
    return {
        "open_count": len(open_rows),
        "oldest_open_at": min((r.updated_at for r in open_rows), default=None),
    }


# ─── Operators ─────────────────────────────────────────────────────────
def _operator_scope(op: OperatorProfile) -> Q:
    vehicle_ids = Vehicle.objects.filter(owner_operator_id=op.id).values("id")
    base_ids = OperatingBase.objects.filter(created_by_id=op.user_id).values("id")
    return (
        Q(subject_operator_id=op.id)
        | Q(subject_vehicle_id__in=vehicle_ids)
        | Q(subject_base_id__in=base_ids)
    )


def _operator_row(op: OperatorProfile, records: list[VerificationRecord]) -> dict[str, Any]:
    required = [r for r in services.requirements_status(op) if r["mandatory"]]
    return {
        "kind": "OPERATOR",
        "id": str(op.id),
        "name": op.display_name or op.full_name,
        "status": op.status,
        "required_count": len(required),
        "verified_count": sum(1 for r in required if r["state"] == State.VERIFIED),
        "created_at": op.created_at,
        **_summary(records),
    }


def _operator_applicants() -> list[dict[str, Any]]:
    open_q = Q(state__in=OPEN_STATES)
    with_open = set(
        VerificationRecord.objects.filter(open_q, subject_operator__isnull=False).values_list(
            "subject_operator_id", flat=True
        )
    )
    with_open |= set(
        Vehicle.objects.filter(
            owner_operator__isnull=False,
            verification_records__state__in=OPEN_STATES,
        ).values_list("owner_operator_id", flat=True)
    )
    base_creators = OperatingBase.objects.filter(
        verification_records__state__in=OPEN_STATES
    ).values("created_by_id")
    ops = OperatorProfile.objects.filter(
        Q(id__in=with_open) | Q(user_id__in=base_creators) | Q(status=OperatorStatus.PENDING)
    )
    return [_operator_row(op, _records(_operator_scope(op))) for op in ops]


# ─── Businesses / groups ───────────────────────────────────────────────
def _business_applicants() -> list[dict[str, Any]]:
    from fikisha.business.models import BusinessAccount

    ids = VerificationRecord.objects.filter(
        state__in=OPEN_STATES, subject_business__isnull=False
    ).values("subject_business_id")
    rows = []
    for biz in BusinessAccount.objects.filter(id__in=ids):
        records = _records(Q(subject_business_id=biz.id))
        rows.append(
            {
                "kind": "BUSINESS",
                "id": str(biz.id),
                "name": biz.trading_name,
                "status": biz.verification_status,
                "created_at": biz.created_at,
                **_summary(records),
            }
        )
    return rows


def _group_scope(group_id: Any) -> Q:
    vehicle_ids = Vehicle.objects.filter(owner_group_id=group_id).values("id")
    return Q(subject_group_id=group_id) | Q(subject_vehicle_id__in=vehicle_ids)


def _group_applicants() -> list[dict[str, Any]]:
    from fikisha.groups.models import OperatorGroup

    ids = set(
        VerificationRecord.objects.filter(
            state__in=OPEN_STATES, subject_group__isnull=False
        ).values_list("subject_group_id", flat=True)
    )
    ids |= set(
        Vehicle.objects.filter(
            owner_group__isnull=False, verification_records__state__in=OPEN_STATES
        ).values_list("owner_group_id", flat=True)
    )
    rows = []
    for group in OperatorGroup.objects.filter(id__in=ids):
        records = _records(_group_scope(group.id))
        rows.append(
            {
                "kind": "GROUP",
                "id": str(group.id),
                "name": group.name,
                "status": group.verification_status,
                "created_at": group.created_at,
                **_summary(records),
            }
        )
    return rows


def applicants(kind: str) -> list[dict[str, Any]]:
    """Applicants a reviewer needs to look at: anyone with an open record
    (theirs or something they own), and every operator still awaiting
    approval. Oldest waiting first."""
    rows = {
        "OPERATOR": _operator_applicants,
        "BUSINESS": _business_applicants,
        "GROUP": _group_applicants,
    }[kind]()
    rows.sort(key=lambda r: r["oldest_open_at"] or r["created_at"])
    return rows


# ─── Applicant detail ──────────────────────────────────────────────────
def _vehicle_rows(vehicles: Iterable[Vehicle], by_vehicle: dict[Any, list[Any]]) -> list[Any]:
    return [
        {
            "id": str(v.id),
            "registration": v.registration,
            "vehicle_class": v.vehicle_class.code,
            "status": v.status,
            "records": by_vehicle.get(v.id, []),
        }
        for v in vehicles
    ]


def applicant_detail(kind: str, applicant_id: Any, serialize: Any) -> dict[str, Any] | None:
    """Everything a reviewer needs about one applicant: their details, and
    each record (with evidence and decision history) grouped by what it is
    about. ``serialize`` renders one record (the API's detail serializer)."""
    if kind == "OPERATOR":
        op = OperatorProfile.objects.filter(id=applicant_id).first()
        if op is None:
            return None
        records = _records(_operator_scope(op))
        by_vehicle: dict[Any, list[Any]] = {}
        by_base: dict[Any, list[Any]] = {}
        own = []
        for r in records:
            if r.subject_vehicle_id:
                by_vehicle.setdefault(r.subject_vehicle_id, []).append(serialize(r))
            elif r.subject_base_id:
                by_base.setdefault(r.subject_base_id, []).append(serialize(r))
            else:
                own.append(serialize(r))
        vehicles = Vehicle.objects.filter(owner_operator_id=op.id).select_related("vehicle_class")
        bases = OperatingBase.objects.filter(created_by_id=op.user_id)
        return {
            **_operator_row(op, records),
            "full_name": op.full_name,
            "requirements": services.requirements_status(op),
            "records": own,
            "vehicles": _vehicle_rows(vehicles, by_vehicle),
            "bases": [
                {"id": str(b.id), "name": b.name, "type": b.type, "records": by_base.get(b.id, [])}
                for b in bases
            ],
        }
    if kind == "BUSINESS":
        from fikisha.business import services as business_services
        from fikisha.business.models import BusinessAccount

        biz = BusinessAccount.objects.filter(id=applicant_id).first()
        if biz is None:
            return None
        records = _records(Q(subject_business_id=biz.id))
        return {
            "kind": "BUSINESS",
            "id": str(biz.id),
            "name": biz.trading_name,
            "status": biz.verification_status,
            "standing": biz.standing,
            "category": biz.category,
            "created_at": biz.created_at,
            **_summary(records),
            "records": [serialize(r) for r in records],
            "locations": [
                {
                    "id": str(loc.id),
                    "label": loc.label,
                    "type": loc.type,
                    "address_text": loc.address_text,
                }
                for loc in business_services.locations_for(biz)
            ],
        }
    if kind == "GROUP":
        from fikisha.groups.models import GroupMembership, GroupMembershipStatus, OperatorGroup

        group = OperatorGroup.objects.filter(id=applicant_id).first()
        if group is None:
            return None
        records = _records(_group_scope(group.id))
        by_vehicle = {}
        own = []
        for r in records:
            if r.subject_vehicle_id:
                by_vehicle.setdefault(r.subject_vehicle_id, []).append(serialize(r))
            else:
                own.append(serialize(r))
        vehicles = Vehicle.objects.filter(owner_group_id=group.id).select_related("vehicle_class")
        return {
            "kind": "GROUP",
            "id": str(group.id),
            "name": group.name,
            "status": group.verification_status,
            "standing": group.standing,
            "group_type": group.type,
            "member_count": GroupMembership.objects.filter(
                group=group, status=GroupMembershipStatus.ACTIVE
            ).count(),
            "created_at": group.created_at,
            **_summary(records),
            "records": own,
            "vehicles": _vehicle_rows(vehicles, by_vehicle),
        }
    return None
