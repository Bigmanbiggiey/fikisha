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
    # ─── Commission statements (Commission & Statements plan, ADR-2D-42) ─
    "statements": {
        "overdue_days": 14,  # D-8: an admin "overdue" marker only
        "paybill_number": None,  # D-3: set by the founder; null shows "details to follow"
    },
    # ─── Value bands / trust gating (Phase 0 D-TRU-5) ────────────────
    "high_value_threshold_kes": 25000000,  # KES 250,000.00
    "value_bands": [
        {"band": "STANDARD", "max_declared_value_kes": 5000000, "min_trust_level": "L1"},
        {"band": "ELEVATED", "max_declared_value_kes": 25000000, "min_trust_level": "L2"},
        {"band": "HIGH", "max_declared_value_kes": 100000000, "min_trust_level": "L3"},
        {"band": "VERY_HIGH", "max_declared_value_kes": None, "min_trust_level": "L3"},
    ],
    # ─── Operator tiers (trust-architecture §1 pilot values; operator-tiers
    # plan). Ratings and at-fault findings aren't measured yet (TD-3), so
    # the rating values are recorded for when they are, and block nothing.
    "trust_tiers": {
        # Ratings and at-fault findings count toward tiers only once a
        # Platform Admin turns this on (trust-and-disputes plan A5), so
        # ratings can build up first; until then those rows are "not
        # measured yet" and block nothing (TD-3).
        "live_criteria": False,
        "L2": {
            "min_completed_jobs": 8,
            "min_days_active": 14,
            "min_avg_rating": 4.2,
            "max_at_fault_findings": 1,
            "at_fault_window_jobs": 20,
        },
        "L3": {
            "min_completed_jobs": 30,
            "min_days_active": 60,
            "min_avg_rating": 4.5,
            "min_clean_elevated_jobs": 3,
        },
        "late_cancellation_flag": {"count": 3, "window_days": 30},
        "reproposal_cooldown_days": 30,
        # TE-6: a demotion is proposed when the mean of the newest
        # `over_last` counted ratings falls below `below`.
        "rating_drop": {"below": 3.5, "over_last": 10},
    },
    # Ratings (trust-and-disputes plan TE-1, TE-4): each side may rate until
    # the job has spent `window_days` in COMPLETED in total (time DISPUTED
    # doesn't count); an average needs `min_counted` counted ratings and
    # uses the newest `average_of`.
    "ratings": {"window_days": 7, "min_counted": 3, "average_of": 10},
    # Resuming a disputed job (trust-and-disputes plan DR-4): only within
    # this many days of the dispute opening; after that it stays DISPUTED.
    "disputes": {"resume_window_days": 7},
    # ─── Enumerations (admin-extensible later) ──────────────────────
    # Vehicle classes moved to the `config_vehicle_class` lookup table in
    # Phase 2C (ADR-2C-01); `ConfigService`/`ConfigPublicView` expose the codes.
    "heavy_class_tare_kg": 3048,  # informational; the heavy flag lives on VehicleClass
    # ─── Verification (Phase 1 verification-architecture) ───────────
    "verification": {
        "good_conduct_recheck_months": 12,
        "expiry_lead_days": 30,  # "expiring soon" window (notifications are a later phase)
    },
    # Which verification domains are mandatory per subject type. `heavy_only`
    # domains apply only when the vehicle's class is `heavy` (config-driven —
    # no vehicle-class literals in application code).
    "verification_requirements": [
        {"subject_type": "OPERATOR", "domain": "IDENTITY", "mandatory": True},
        {"subject_type": "OPERATOR", "domain": "LICENCE", "mandatory": True},
        {"subject_type": "OPERATOR", "domain": "GOOD_CONDUCT", "mandatory": True},
        {"subject_type": "VEHICLE", "domain": "VEHICLE", "mandatory": True},
        {"subject_type": "VEHICLE", "domain": "ASSOCIATION", "mandatory": True},
        {
            "subject_type": "VEHICLE",
            "domain": "HEAVY_CLASS_COMPLIANCE",
            "mandatory": True,
            "heavy_only": True,
        },
        {"subject_type": "BASE", "domain": "BASE", "mandatory": True},
        {"subject_type": "BUSINESS", "domain": "BUSINESS", "mandatory": True},
        {"subject_type": "GROUP", "domain": "GROUP", "mandatory": True},
    ],
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
    # What completes a pickup and a delivery, per value band (founder
    # assessment 2026-10-20, LD-4, amended PD-1 / PD-2). Each band lists
    # groups; every group must be met, and a group is met by any one of its
    # methods. OTP = the code, given to the driver or through the recipient
    # link; SIGNATURE = signed on the driver's phone; PHOTO = taken by the
    # driver, as proof only (it never stands in for the other party);
    # IN_APP = the sender confirmed in their own app. The driver makes the
    # final call, so both parties take part.
    "custody_proof_rules": {
        "pickup": {
            "STANDARD": [["OTP", "SIGNATURE", "IN_APP"]],
            "ELEVATED": [["OTP", "IN_APP"], ["PHOTO"]],
            "HIGH": [["OTP"], ["SIGNATURE"], ["PHOTO"]],
            "VERY_HIGH": [["OTP"], ["SIGNATURE"], ["PHOTO"]],
        },
        "delivery": {
            "STANDARD": [["OTP", "SIGNATURE"], ["PHOTO"]],
            "ELEVATED": [["OTP"], ["PHOTO"]],
            "HIGH": [["OTP"], ["SIGNATURE"], ["PHOTO"]],
            "VERY_HIGH": [["OTP"], ["SIGNATURE"], ["PHOTO"]],
        },
    },
    # Keywords (English + Swahili) that suggest a cargo category from the
    # description when the business picks none (assessment 2026-10-19 D-5).
    # A Platform Admin adds to them from the "uncategorised" list.
    "cargo_category_keywords": {
        "GENERAL": ["goods", "items", "general goods", "bidhaa", "vitu"],
        "CONSTRUCTION_MATERIALS": [
            "cement",
            "sand",
            "ballast",
            "bricks",
            "blocks",
            "timber",
            "iron sheets",
            "steel",
            "rebar",
            "nails",
            "tiles",
            "paint",
            "gravel",
            "stones",
            "mabati",
            "saruji",
            "mchanga",
            "kokoto",
            "matofali",
            "mbao",
            "chuma",
            "misumari",
            "rangi",
            "mawe",
        ],
        "AGRICULTURE_PRODUCE": [
            "maize",
            "beans",
            "potatoes",
            "tomatoes",
            "onions",
            "cabbages",
            "sukuma",
            "vegetables",
            "fruits",
            "bananas",
            "mangoes",
            "avocados",
            "fertilizer",
            "seeds",
            "hay",
            "animal feed",
            "mahindi",
            "maharagwe",
            "viazi",
            "nyanya",
            "vitunguu",
            "kabichi",
            "mboga",
            "matunda",
            "ndizi",
            "maembe",
            "mbolea",
            "mbegu",
            "nyasi",
            "chakula cha mifugo",
        ],
        "FOOD_BEVERAGE": [
            "bottled water",
            "drinking water",
            "soda",
            "juice",
            "milk",
            "bread",
            "flour",
            "sugar",
            "rice",
            "cooking oil",
            "drinks",
            "beer",
            "unga",
            "sukari",
            "mchele",
            "mafuta ya kupikia",
            "maziwa",
            "mkate",
            "maji ya kunywa",
            "vinywaji",
        ],
        "FURNITURE_APPLIANCES": [
            "sofa",
            "bed",
            "mattress",
            "table",
            "chairs",
            "wardrobe",
            "cupboard",
            "fridge",
            "refrigerator",
            "cooker",
            "washing machine",
            "furniture",
            "kitanda",
            "godoro",
            "meza",
            "viti",
            "kabati",
            "friji",
            "jiko",
            "samani",
        ],
        "ELECTRONICS": [
            "tv",
            "television",
            "laptop",
            "computer",
            "phones",
            "speaker",
            "electronics",
            "solar panel",
            "inverter",
            "battery",
            "printer",
            "simu",
            "kompyuta",
            "runinga",
            "televisheni",
            "betri",
        ],
        "DOCUMENTS_PARCELS": [
            "documents",
            "envelope",
            "parcel",
            "package",
            "letter",
            "files",
            "nyaraka",
            "bahasha",
            "kifurushi",
            "barua",
        ],
        "LIVESTOCK": [
            "goats",
            "sheep",
            "cows",
            "cattle",
            "chickens",
            "poultry",
            "pigs",
            "livestock",
            "mbuzi",
            "kondoo",
            "ng'ombe",
            "kuku",
            "nguruwe",
            "mifugo",
        ],
        "LIQUIDS_BULK": [
            "fuel",
            "diesel",
            "petrol",
            "oil drums",
            "water tank",
            "jerrycans",
            "chemicals",
            "dizeli",
            "petroli",
            "tangi la maji",
        ],
        "OTHER": [],
    },
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
            # Review (read-only) access to organisations + vehicles — FR-ADM-1.
            "business.read",
            "operator.read",
            "group.read",
            "vehicle.read",
            # Commission statements, read-only (Commission & Statements D-4).
            "statements.read.all",
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
    "role_permissions",
    "timeouts",
    "retention_windows",
    "verification_requirements",
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
