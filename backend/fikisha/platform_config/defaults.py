"""The default platform configuration + a light validator.

This is the coherent baseline seeded on first run. It mirrors the *shape* in
Phase 1 database-design §4.15; business tuning happens via
``ConfigService.apply_change`` (no deploy). Money is integer KES minor units.

Confirmed founder values already baked in (Phase 0 decisions):
  * commission: flat 10%, KES 40 minimum, KES 5,000 cap (Phase 2A brief §3 / D-BIZ-5 clarified)
  * value bands: 50k / 250k / 1M ; high-value review threshold KES 250,000 (D-TRU-5)
  * UI languages English + Swahili (D-PIL-4)
  * pilot admin roles: PLATFORM_ADMIN + OPERATIONS_OFFICER (D-ADM-1)
  * Kitengela zones: deferred — empty list (D-PIL-5)
"""

from __future__ import annotations

from typing import Any

SCHEMA_VERSION = 1

DEFAULT_CONFIG: dict[str, Any] = {
    "schema_version": SCHEMA_VERSION,
    "brand": {"name": "Fikisha"},
    "locales": {"supported": ["en", "sw"], "operator_default": "sw", "default": "en"},
    "pilot": {"area": "Kitengela, Kajiado County + environs"},
    # ─── Commission (Phase 2A brief §3) ───────────────────────────────
    "commission": {
        "model": "FLAT_WITH_MIN_CAP",  # the only implemented model
        "rate": 0.10,
        "min_fee_kes": 4000,  # KES 40.00
        "cap_kes": 500000,  # KES 5,000.00
        "party_liable": "OPERATOR",
    },
    # ─── Value bands / trust gating (Phase 0 D-TRU-5) ────────────────
    "high_value_threshold_kes": 25000000,  # KES 250,000.00
    "value_bands": [
        {"band": "STANDARD", "max_declared_value_kes": 5000000, "min_trust_level": "L1"},
        {"band": "ELEVATED", "max_declared_value_kes": 25000000, "min_trust_level": "L2"},
        {"band": "HIGH", "max_declared_value_kes": 100000000, "min_trust_level": "L3"},
        {"band": "VERY_HIGH", "max_declared_value_kes": None, "min_trust_level": "L3"},
    ],
    # ─── Enumerations (admin-extensible later) ──────────────────────
    "vehicle_types": [
        "MOTORCYCLE",
        "PICKUP",
        "CANTER",
        "TIPPER",
        "LORRY",
        "SEMI_TRUCK",
        "TRAILER",
        "OTHER",
    ],
    "heavy_class_tare_kg": 3048,
    "cargo_categories": [
        "GENERAL",
        "CONSTRUCTION_MATERIALS",
        "AGRICULTURE_PRODUCE",
        "FOOD_BEVERAGE",
        "FURNITURE_APPLIANCES",
        "ELECTRONICS",
        "DOCUMENTS_PARCELS",
        "LIVESTOCK",
        "LIQUIDS_BULK",
        "OTHER",
    ],
    "latent_risk_categories": ["ELECTRONICS", "FOOD_BEVERAGE", "FURNITURE_APPLIANCES"],
    # ─── Zones — deferred (D-PIL-5); pilot area is one implicit zone ─
    "zones": [],
    # ─── Timeouts (Phase 0 D-JOB-5; ranges tuned in pilot) ─────────
    "timeouts": {
        "request_expiry_hours": 24,
        "offer_expiry_hours": 4,
        "delivery_acceptance": {"standard_hours": 24, "high_hours": 48},
        "post_completion_window": {"default_hours": 72, "high_and_latent_days": 7},
        "stale_assignment_alert_minutes": 45,
    },
    # ─── Cancellation policy (Phase 0 D-DIS-3) ─────────────────────
    "cancellation_policy": {
        "rolling_window_days": 30,
        "flag_threshold": 3,
        "courtesy_fee_enabled": False,
        "courtesy_fee_kes": 0,
    },
    # ─── Admin roles → permissions (Phase 0 D-ADM-1 / FR-ADM-8) ────
    # Pilot ships 2 roles. The 4-role split is enabled here later without a deploy.
    "role_permissions": {
        "PLATFORM_ADMIN": ["*"],
        "OPERATIONS_OFFICER": [
            "verification.queue.view",
            "verification.decide",
            "job.monitor.view",
            "job.intervene",
            "incident.intake",
            "incident.amicable.facilitate",
            "trust.change.propose",
            "audit.view.scoped",
            "export.request",
        ],
    },
    # ─── Retention windows (proposed; REQUIRES VALIDATION — legal-scope §7) ─
    "retention_windows": {
        "job_records_years": 7,
        "audit_years": 7,
        "verification_doc_months": 12,
        "raw_geo_months": 12,
        "comms_logs_years": 3,
    },
    "sla_targets": {
        "CRITICAL": {"ack_hours": 1, "action_hours": 2},
        "HIGH": {"ack_hours": 4, "action_hours": 8, "resolution_days": 3},
        "MEDIUM": {"ack_hours": 12, "action_hours": 24, "resolution_days": 5},
        "LOW": {"ack_hours": 24, "action_hours": 48, "resolution_days": 7},
    },
    # ─── Feature flags ────────────────────────────────────────────
    "feature_flags": {
        "demo_endpoints": True,  # dev-only demo routes (also gated by DEBUG)
    },
}

_ALLOWED_COMMISSION_MODELS = {"FLAT_WITH_MIN_CAP", "BANDED_TAPER", "RAMPED"}
_REQUIRED_TOP_LEVEL = {
    "schema_version",
    "commission",
    "value_bands",
    "high_value_threshold_kes",
    "vehicle_types",
    "role_permissions",
    "timeouts",
    "retention_windows",
}


class ConfigValidationError(ValueError):
    """Raised when a proposed configuration fails validation."""


def validate(data: dict[str, Any]) -> None:
    """Light structural validation. A full JSON-Schema is a Phase 2B item."""
    missing = _REQUIRED_TOP_LEVEL - set(data)
    if missing:
        raise ConfigValidationError(f"config missing required keys: {sorted(missing)}")

    commission = data["commission"]
    if commission.get("model") not in _ALLOWED_COMMISSION_MODELS:
        raise ConfigValidationError(f"commission.model must be one of {_ALLOWED_COMMISSION_MODELS}")
    for money_key in ("min_fee_kes", "cap_kes"):
        value = commission.get(money_key)
        if not isinstance(value, int) or isinstance(value, bool) or value < 0:
            raise ConfigValidationError(
                f"commission.{money_key} must be a non-negative int (minor units)"
            )
    rate = commission.get("rate")
    if not isinstance(rate, int | float) or not (0 <= rate <= 1):
        raise ConfigValidationError("commission.rate must be a number between 0 and 1")

    hv = data["high_value_threshold_kes"]
    if not isinstance(hv, int) or isinstance(hv, bool) or hv < 0:
        raise ConfigValidationError(
            "high_value_threshold_kes must be a non-negative int (minor units)"
        )

    rp = data["role_permissions"]
    if not isinstance(rp, dict) or "PLATFORM_ADMIN" not in rp:
        raise ConfigValidationError("role_permissions must be a dict including PLATFORM_ADMIN")
