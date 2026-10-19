"""Driver trust level for value-band gating (operator tiers, ADR-2D-52;
replaces the interim rule of ADR-2D-05 Option b).

A driver's level is their stored tier (``fikisha.trust``: L1 / L2 / L3 /
RESTRICTED, L1 when none was ever recorded), with verification as the
floor: without current IDENTITY + LICENCE + GOOD_CONDUCT (config) they have
no level and can take no banded job. The job's ``required_trust_level`` /
``value_band`` come from ``platform_config`` (``value_bands[].min_trust_level``).

**No ratings, stars, ranking, recommendation, or opaque scoring.** HIGH /
VERY_HIGH jobs additionally require ``HighValueApproval`` regardless of level.
"""

from __future__ import annotations

from typing import Any

from fikisha.jobs.constants import TrustLevel, ValueBand
from fikisha.platform_config import services as config_service

#: RESTRICTED covers what L1 covers: STANDARD only (TD-4).
_LEVEL_ORDER: dict[str, int] = {
    TrustLevel.RESTRICTED: 1,
    TrustLevel.L1: 1,
    TrustLevel.L2: 2,
    TrustLevel.L3: 3,
}
_BAND_ORDER: dict[str, int] = {
    ValueBand.STANDARD: 1,
    ValueBand.ELEVATED: 2,
    ValueBand.HIGH: 3,
    ValueBand.VERY_HIGH: 4,
}


def driver_trust_level(driver: Any) -> str:
    """``L1`` / ``L2`` / ``L3`` / ``RESTRICTED``, or ``""`` (the
    verification floor isn't met: no banded job). Tiers change only through
    ``fikisha.trust`` (a confirmed proposal or a Platform Admin's manual
    change); an ``L2``/``L3`` job for a lower driver still needs a recorded
    ``admin_override_reason`` at assignment."""
    from fikisha.trust import services as trust

    level = trust.effective_level(driver)
    return "" if level == "L0" else level


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
