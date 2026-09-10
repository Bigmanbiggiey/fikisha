"""Interim driver trust ceiling (ADR-2D-05 Option b — Founder-approved).

There is no Trust engine in the codebase yet. Until the dedicated Trust phase,
a driver's trust level is derived **conservatively and deterministically** from
approved verification facts only, and the job's ``required_trust_level`` /
``value_band`` come from ``platform_config`` (``value_bands[].min_trust_level``).

**No ratings, stars, ranking, recommendation, or opaque scoring.** HIGH /
VERY_HIGH jobs additionally require ``HighValueApproval`` regardless of level.
"""

from __future__ import annotations

from typing import Any

from fikisha.jobs.constants import TrustLevel, ValueBand
from fikisha.platform_config import services as config_service

_LEVEL_ORDER: dict[str, int] = {TrustLevel.L1: 1, TrustLevel.L2: 2, TrustLevel.L3: 3}
_BAND_ORDER: dict[str, int] = {
    ValueBand.STANDARD: 1,
    ValueBand.ELEVATED: 2,
    ValueBand.HIGH: 3,
    ValueBand.VERY_HIGH: 4,
}


def interim_driver_trust_level(driver: Any) -> str:
    """Conservative: a driver with current IDENTITY + LICENCE + GOOD_CONDUCT
    verification is ``L1``. ``L2``/``L3`` require the (not-yet-built) Trust
    engine's job-history / rating / admin-confirmation criteria, so they are
    **unreachable in 2D** — an ``L2``/``L3`` job needs a recorded
    ``admin_override_reason`` at assignment until the Trust phase ships.
    """
    from fikisha.verification.models import Domain
    from fikisha.verification.services import subject_meets

    required = {Domain.IDENTITY, Domain.LICENCE, Domain.GOOD_CONDUCT}
    if subject_meets(driver, list(required)):
        return TrustLevel.L1
    return ""  # not even L1 — cannot take any banded job


def band_min_trust_level(band: str) -> str:
    """The configured ``min_trust_level`` for a value band (L1/L2/L3)."""
    for entry in config_service.get("value_bands", default=[]) or []:
        if entry.get("band") == band:
            return str(entry.get("min_trust_level", "L1"))
    return TrustLevel.L1


def level_covers_band(level: str, band: str) -> bool:
    """True iff ``level`` ≥ the band's configured ``min_trust_level``."""
    if not level:
        return False
    need = band_min_trust_level(band)
    return _LEVEL_ORDER.get(level, 0) >= _LEVEL_ORDER.get(need, 99)


def band_for_declared_value(declared_value_kes: int) -> str:
    """Map a declared value (KES minor units) to a value band via config."""
    entries = config_service.get("value_bands", default=[]) or []
    for entry in sorted(entries, key=lambda e: _BAND_ORDER.get(e.get("band", ""), 99)):
        cap = entry.get("max_declared_value_kes")
        if cap is None or declared_value_kes <= cap:
            return str(entry["band"])
    return ValueBand.VERY_HIGH
