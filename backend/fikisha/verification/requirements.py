"""Which verification domains are mandatory for a subject — read from
``platform_config`` (``verification_requirements``), never hard-coded.

Heavy-vehicle requirements are keyed off ``VehicleClass.heavy`` (config data),
so there is no ``if vehicle.class == "LORRY"`` anywhere in application code.
"""

from __future__ import annotations

from typing import Any

from fikisha.platform_config import services as config
from fikisha.platform_config.defaults import DEFAULT_CONFIG
from fikisha.verification.models import SubjectType


def _rules() -> list[dict[str, Any]]:
    # Fall back to the shipped default if a pre-2C config snapshot lacks the key
    # (an already-deployed config picks it up via ConfigService.apply_change).
    rules = list(config.get("verification_requirements", None) or [])
    if not rules:
        return list(DEFAULT_CONFIG["verification_requirements"])
    # A subject type the live config predates (BUSINESS / GROUP, assessment
    # 2026-10-19) takes the shipped default rules until an admin applies a
    # config that names it.
    configured = {r.get("subject_type") for r in rules}
    rules += [
        r
        for r in DEFAULT_CONFIG["verification_requirements"]
        if r.get("subject_type") not in configured
    ]
    return rules


def required_domains(subject_type: str, *, vehicle_is_heavy: bool = False) -> list[str]:
    out: list[str] = []
    for rule in _rules():
        if rule.get("subject_type") != subject_type or not rule.get("mandatory", False):
            continue
        if rule.get("heavy_only") and not vehicle_is_heavy:
            continue
        out.append(rule["domain"])
    return out


def required_domains_for_subject(subject: Any) -> list[str]:
    from fikisha.operators.models import OperatingBase, OperatorProfile
    from fikisha.vehicles.models import Vehicle

    if isinstance(subject, OperatorProfile):
        return required_domains(SubjectType.OPERATOR)
    if isinstance(subject, Vehicle):
        return required_domains(
            SubjectType.VEHICLE, vehicle_is_heavy=bool(subject.vehicle_class.heavy)
        )
    if isinstance(subject, OperatingBase):
        return required_domains(SubjectType.BASE)
    from fikisha.business.models import BusinessAccount
    from fikisha.groups.models import OperatorGroup

    if isinstance(subject, BusinessAccount):
        return required_domains(SubjectType.BUSINESS)
    if isinstance(subject, OperatorGroup):
        return required_domains(SubjectType.GROUP)
    raise TypeError(f"unsupported verification subject: {type(subject).__name__}")
