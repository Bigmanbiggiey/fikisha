"""ConfigService — read the current config, resolve dotted paths, and apply a
versioned change (deep-merge + validate + audit + outbox event), all atomic.
"""

from __future__ import annotations

import copy
from typing import Any

from django.db import transaction

from fikisha.audit import services as audit
from fikisha.outbox.services import emit
from fikisha.platform_config.defaults import DEFAULT_CONFIG, validate
from fikisha.platform_config.models import PlatformConfig, PlatformConfigVersion

_MISSING = object()

CONFIG_CHANGED_EVENT = "platform_config.changed"


def _deep_merge(base: dict[str, Any], patch: dict[str, Any]) -> dict[str, Any]:
    out = copy.deepcopy(base)
    for key, value in patch.items():
        if isinstance(value, dict) and isinstance(out.get(key), dict):
            out[key] = _deep_merge(out[key], value)
        else:
            out[key] = copy.deepcopy(value)
    return out


@transaction.atomic
def _bootstrap() -> PlatformConfig:
    cfg = PlatformConfig.objects.select_for_update().filter(pk=1).first()
    if cfg is not None:
        return cfg
    snapshot = copy.deepcopy(DEFAULT_CONFIG)
    validate(snapshot)
    version = PlatformConfigVersion.objects.create(
        version=1,
        changed_by=None,
        rationale="Initial default configuration (bootstrap).",
        snapshot=snapshot,
    )
    return PlatformConfig.objects.create(pk=1, data=snapshot, current_version=version)


def current() -> dict[str, Any]:
    """Return the live config dict (bootstrapping the singleton on first use)."""
    cfg = PlatformConfig.objects.filter(pk=1).first() or _bootstrap()
    return cfg.data


def get(path: str, default: Any = None) -> Any:
    """Resolve a dotted path, e.g. ``get("commission.rate")``."""
    node: Any = current()
    for part in path.split("."):
        if isinstance(node, dict) and part in node:
            node = node[part]
        else:
            return default
    return node


def current_version() -> int:
    cfg = (
        PlatformConfig.objects.select_related("current_version").filter(pk=1).first()
        or _bootstrap()
    )
    version_obj = cfg.current_version if cfg.current_version_id else None
    return version_obj.version if version_obj is not None else 1


@transaction.atomic
def apply_change(
    *, patch: dict[str, Any], changed_by: Any, rationale: str
) -> PlatformConfigVersion:
    """Apply a deep-merge patch, validate, append a version, audit, emit an event."""
    if not rationale or not rationale.strip():
        raise ValueError("A non-empty rationale is required for a configuration change.")

    cfg = PlatformConfig.objects.select_for_update().filter(pk=1).first() or _bootstrap()
    cfg = PlatformConfig.objects.select_for_update().get(pk=1)

    before = copy.deepcopy(cfg.data)
    after = _deep_merge(before, patch)
    validate(after)

    next_version = (
        PlatformConfigVersion.objects.order_by("-version").values_list("version", flat=True).first()
        or 0
    ) + 1
    version = PlatformConfigVersion.objects.create(
        version=next_version,
        changed_by=changed_by if getattr(changed_by, "pk", None) else None,
        rationale=rationale.strip(),
        snapshot=after,
    )
    cfg.data = after
    cfg.current_version = version
    cfg.save(update_fields=["data", "current_version", "updated_at"])

    audit.record(
        actor=changed_by,
        action="platform_config.changed",
        entity_type="platform_config",
        entity_id=None,
        before={"version": next_version - 1, "keys": sorted(patch)},
        after={"version": next_version},
        source_channel="ADMIN_UI",
    )
    emit(
        event_type=CONFIG_CHANGED_EVENT,
        aggregate_type="platform_config",
        aggregate_id=None,
        payload={"version": next_version, "changed_keys": sorted(patch)},
    )
    return version
