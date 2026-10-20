"""What completes a pickup and a delivery (founder assessment 2026-10-20 L-5,
LD-4 / LD-5). Read from config ``custody_proof_rules``; a live config that
predates it uses the shipped defaults.

A band's rule is a list of groups. Every group must be met; a group is met by
any one of its methods (``OTP``, ``SIGNATURE``, ``PHOTO``, ``IN_APP``).
"""

from __future__ import annotations

from typing import Any

from fikisha.jobs.constants import ValueBand
from fikisha.platform_config import services as config
from fikisha.platform_config.defaults import DEFAULT_CONFIG

PICKUP = "pickup"
DELIVERY = "delivery"
METHODS = ("OTP", "SIGNATURE", "PHOTO", "IN_APP")


def rules(stage: str, band: str | None) -> list[list[str]]:
    live = config.get("custody_proof_rules", None)
    source = (
        live if isinstance(live, dict) and stage in live else DEFAULT_CONFIG["custody_proof_rules"]
    )
    by_band = source[stage]
    return [list(g) for g in by_band.get(band or ValueBand.STANDARD, by_band[ValueBand.STANDARD])]


def unmet(stage: str, band: str | None, present: set[str]) -> list[list[str]]:
    """The groups the present methods don't satisfy (empty = complete)."""
    return [group for group in rules(stage, band) if not present.intersection(group)]


def requirements_view(job: Any) -> dict[str, list[list[str]]]:
    """For the job payload: what each step needs for this job's band."""
    band = job.value_band or ValueBand.STANDARD
    return {PICKUP: rules(PICKUP, band), DELIVERY: rules(DELIVERY, band)}
