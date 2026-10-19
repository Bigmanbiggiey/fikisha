"""Cargo categories (assessment 2026-10-19 part 6, D-5).

The categories are platform rules (FR-ADM-6, ``cargo_categories`` in config)
and they matter: a category in ``latent_risk_categories`` gives a job the
longer post-completion dispute window (D-JOB-5). So:

- a category the business picks must be one of the configured ones;
- when it picks none, the description suggests one by **deterministic keyword
  matching** (English and Swahili keywords in ``cargo_category_keywords``);
  no match → ``OTHER``, marked as chosen automatically so a Platform Admin
  sees it in the "uncategorised" list;
- the system never creates a category on its own. A Platform Admin adds a
  keyword or a category through an audited, step-up config change, and every
  later description benefits ("learns" from admin decisions only).

No AI classifier and no external service.
"""

from __future__ import annotations

import re
from collections import Counter
from typing import Any

from fikisha.common.exceptions import DomainError
from fikisha.platform_config import services as config
from fikisha.platform_config.defaults import DEFAULT_CONFIG

OTHER = "OTHER"
_WORD = re.compile(r"[^\w']+", re.UNICODE)


class UnknownCargoCategory(DomainError):
    default_code = "unknown_cargo_category"
    default_detail = "That is not one of the cargo categories."


def categories() -> list[str]:
    return list(config.get("cargo_categories", None) or DEFAULT_CONFIG["cargo_categories"])


def latent_risk_categories() -> set[str]:
    return set(
        config.get("latent_risk_categories", None) or DEFAULT_CONFIG["latent_risk_categories"]
    )


def keywords() -> dict[str, list[str]]:
    """Keywords per configured category. A live config that predates the
    keywords key uses the shipped defaults until an admin changes them."""
    live = config.get("cargo_category_keywords", None)
    source = live if isinstance(live, dict) else DEFAULT_CONFIG["cargo_category_keywords"]
    return {code: [str(k) for k in source.get(code, [])] for code in categories()}


def _normalise(text: str) -> str:
    return " " + " ".join(_WORD.sub(" ", (text or "").lower()).split()) + " "


def _matches(text: str, keyword: str) -> bool:
    kw = _normalise(keyword).strip()
    if not kw:
        return False
    # Whole words or phrases, singular or with a plural "s"/"es".
    return any(f" {form} " in text for form in (kw, f"{kw}s", f"{kw}es"))


def suggest(description: str) -> str | None:
    """The configured category whose keywords best match the description, or
    ``None``. A longer phrase outweighs a single word ("cooking oil" beats
    "oil"); a tie goes to the category listed first in config."""
    text = _normalise(description)
    best: tuple[int, str] | None = None
    for code, words in keywords().items():
        score = sum(len(k.split()) for k in words if _matches(text, k))
        if score and (best is None or score > best[0]):
            best = (score, code)
    return best[1] if best else None


def resolve(*, category_code: str, description: str) -> tuple[str, bool]:
    """``(category, chosen_automatically)`` for a new job's cargo."""
    code = (category_code or "").strip().upper()
    if code:
        if code not in categories():
            raise UnknownCargoCategory()
        return code, False
    return suggest(description) or OTHER, True


def is_latent_risk(code: str) -> bool:
    return code in latent_risk_categories()


def catalogue() -> list[dict[str, Any]]:
    risky = latent_risk_categories()
    return [{"code": c, "latent_risk": c in risky} for c in categories()]


def uncategorised(*, limit: int = 50) -> list[dict[str, Any]]:
    """Descriptions that were filed under ``OTHER`` automatically and that the
    current keywords still don't place, most frequent first: what a Platform
    Admin should teach the matcher next."""
    from fikisha.jobs.models import CargoDetails

    counts: Counter[str] = Counter()
    shown: dict[str, str] = {}
    last_seen: dict[str, Any] = {}
    rows = CargoDetails.objects.filter(category_code=OTHER, category_auto=True).values_list(
        "description", "created_at"
    )
    for description, created_at in rows.iterator():
        if suggest(description):
            continue  # a keyword added since now places it
        key = _normalise(description).strip()
        if not key:
            continue
        counts[key] += 1
        shown.setdefault(key, description.strip())
        if key not in last_seen or created_at > last_seen[key]:
            last_seen[key] = created_at
    return [
        {"description": shown[key], "count": n, "last_seen": last_seen[key]}
        for key, n in counts.most_common(limit)
    ]
