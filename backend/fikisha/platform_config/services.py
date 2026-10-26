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


def vehicle_class_codes(*, active_only: bool = True) -> list[str]:
    """The vehicle-class machine identifiers (the `config_vehicle_class` table
    is authoritative — ADR-2C-01)."""
    from fikisha.platform_config.models import VehicleClass

    qs = VehicleClass.objects.all()
    if active_only:
        qs = qs.filter(active=True)
    return list(qs.order_by("sort_order", "code").values_list("code", flat=True))


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
    return _commit(
        cfg=cfg,
        after=_deep_merge(before, patch),
        changed_keys=sorted(patch),
        changed_by=changed_by,
        rationale=rationale,
    )


@transaction.atomic
def replace_section(
    *, key: str, value: Any, changed_by: Any, rationale: str, source_channel: str = "ADMIN_UI"
) -> PlatformConfigVersion | None:
    """Replace one top-level section whole, rather than merging into it, so
    keys the new shape drops really go (the commission split, ADR-2D-55,
    drops ``rate`` / ``min_fee_kes`` / ``cap_kes``). Versioned, validated,
    audited and announced exactly like :func:`apply_change`. Returns ``None``
    if no live config exists yet (the bootstrap will use the defaults) or the
    section already has this value."""
    if not rationale or not rationale.strip():
        raise ValueError("A non-empty rationale is required for a configuration change.")
    cfg = PlatformConfig.objects.select_for_update().filter(pk=1).first()
    if cfg is None or cfg.data.get(key) == value:
        return None
    after = copy.deepcopy(cfg.data)
    after[key] = copy.deepcopy(value)
    return _commit(
        cfg=cfg,
        after=after,
        changed_keys=[key],
        changed_by=changed_by,
        rationale=rationale,
        source_channel=source_channel,
    )


def _commit(
    *,
    cfg: PlatformConfig,
    after: dict[str, Any],
    changed_keys: list[str],
    changed_by: Any,
    rationale: str,
    source_channel: str = "ADMIN_UI",
) -> PlatformConfigVersion:
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
        before={"version": next_version - 1, "keys": changed_keys},
        after={"version": next_version},
        source_channel=source_channel,
    )
    emit(
        event_type=CONFIG_CHANGED_EVENT,
        aggregate_type="platform_config",
        aggregate_id=None,
        payload={"version": next_version, "changed_keys": changed_keys},
    )
    return version


# ─── Platform Admin console reads (Design Phase 6 Increment 9, ADR-2D-38) ─
def _flatten(node: Any, prefix: str = "") -> dict[str, Any]:
    if isinstance(node, dict):
        out: dict[str, Any] = {}
        for key, value in node.items():
            out.update(_flatten(value, f"{prefix}.{key}" if prefix else key))
        return out
    return {prefix: node}


def preview_change(patch: dict[str, Any]) -> list[dict[str, Any]]:
    """What ``apply_change(patch)`` would change, without changing anything:
    one ``{path, before, after}`` per leaf that differs. Raises
    ``ConfigValidationError`` exactly as ``apply_change`` would."""
    before = current()
    after = _deep_merge(before, patch)
    validate(after)
    flat_before, flat_after = _flatten(before), _flatten(after)
    return [
        {"path": path, "before": flat_before.get(path), "after": value}
        for path, value in sorted(flat_after.items())
        if flat_before.get(path, _MISSING) != value
    ]


def versions(limit: int = 50) -> list[dict[str, Any]]:
    """The newest config versions, newest first, with who changed what and
    why. The snapshot itself is left out (it's the whole config)."""
    rows = PlatformConfigVersion.objects.select_related("changed_by").order_by("-version")[:limit]
    return [
        {
            "version": v.version,
            "changed_by_user_id": str(v.changed_by_id) if v.changed_by_id else None,
            "changed_by_name": (v.changed_by.display_name or "") if v.changed_by else None,
            "rationale": v.rationale,
            "created_at": v.created_at.isoformat(),
        }
        for v in rows
    ]
