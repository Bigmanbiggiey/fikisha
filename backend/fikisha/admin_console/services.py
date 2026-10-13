"""Platform Admin console services (Design Phase 6 Increment 9, P3 §19,
ADR-2D-38).

Every source is read or changed through its own module's public surface
(module boundary rule): ``business`` / ``operators`` / ``groups``
``admin_directory``, ``identity.services.admin_accounts``,
``platform_config.services``, ``jobs.admin_ledger``.

What needs a fresh MFA step-up (Phase 1 ``authentication-authorization.md``
§1.2) goes through ``identity.authz.step_up.require_step_up``: account
interventions and configuration changes. Until admin MFA exists (D-1,
deferred) those are refused with ``step_up_required``; everything else here
is a read and works now.
"""

from __future__ import annotations

from typing import Any

from django.db import transaction
from rest_framework import status

from fikisha.admin_console.models import AccountType, AdminIntervention, InterventionAction
from fikisha.audit import services as audit
from fikisha.business import admin_directory as business_directory
from fikisha.common.exceptions import AuthorizationError, DomainError
from fikisha.groups import admin_directory as groups_directory
from fikisha.identity.authz.policies import actor_has_permission
from fikisha.identity.authz.step_up import require_step_up
from fikisha.identity.services import admin_accounts
from fikisha.operators import admin_directory as operators_directory


class InvalidIntervention(DomainError):
    default_code = "invalid_intervention"


class InterventionNotAllowed(DomainError):
    status_code = status.HTTP_409_CONFLICT
    default_code = "intervention_not_allowed"


class ConfigKeyNotEditable(DomainError):
    default_code = "config_key_not_editable"


class InvalidConfigChange(DomainError):
    default_code = "invalid_config_change"


def _require(actor: Any, permission: str) -> None:
    if not actor_has_permission(actor, permission):
        raise AuthorizationError(f"missing permission {permission!r}")


def _user(actor: Any) -> Any:
    return getattr(actor, "user", None)


# ─── Directory (§19.5, D-6) ─────────────────────────────────────────────
DIRECTORIES: dict[str, Any] = {
    "businesses": business_directory,
    "operators": operators_directory,
    "groups": groups_directory,
}
_KIND_TO_DIRECTORY = {
    AccountType.BUSINESS: business_directory,
    AccountType.OPERATOR: operators_directory,
    AccountType.GROUP: groups_directory,
}


def mask_phone(phone: str | None) -> str | None:
    """``+254712345678`` → ``+2547•••••678``: enough to tell two numbers
    apart, not enough to call. The full number needs an audited reveal."""
    if not phone:
        return None
    if len(phone) <= 7:
        return "•" * len(phone)
    return phone[:5] + "•" * (len(phone) - 8) + phone[-3:]


def masked(row: dict[str, Any]) -> dict[str, Any]:
    return {**row, "phone": mask_phone(row.get("phone"))}


@transaction.atomic
def reveal_contact(*, actor: Any, account_type: str, account_id: Any) -> dict[str, Any]:
    """The account's contact name and full phone. One audit row per reveal,
    never containing the phone itself (the Increment 8 contact-reveal
    pattern)."""
    _require(actor, "admin.directory.contact_reveal")
    directory = _KIND_TO_DIRECTORY.get(account_type)  # type: ignore[call-overload]
    if directory is None:
        raise InvalidIntervention("Unknown account type.")
    contact = directory.contact(account_id)
    if contact is None:
        from rest_framework.exceptions import NotFound

        raise NotFound("No such account.")
    audit.record(
        actor=actor,
        action="admin.directory.contact_revealed",
        entity_type=account_type.lower(),
        entity_id=account_id,
        after={"revealed": bool(contact.get("phone"))},
    )
    return contact


def interventions_for(account_type: str, account_id: Any) -> list[dict[str, Any]]:
    rows = AdminIntervention.objects.filter(
        account_type=account_type, account_id=account_id
    ).select_related("admin")
    return [
        {
            "id": str(r.id),
            "action": r.action,
            "reason": r.reason,
            "duration_days": r.duration_days,
            "before_state": r.before_state,
            "after_state": r.after_state,
            "admin_name": r.admin.display_name or "",
            "created_at": r.created_at.isoformat(),
        }
        for r in rows.order_by("-created_at")
    ]


# ─── Account interventions (§19.2, §19.5, D-2) ──────────────────────────
#: (account type, action) → (states it may start from, the state it sets).
#: REINSTATE's target is the state before the latest SUSPEND (falling back
#: to the default), so a PENDING operator goes back to PENDING, not ACTIVE.
#: Businesses and groups have no offboarded state; RESTRICTED is never set
#: here (D-2: left out until defined).
_SUSPENDABLE = {
    AccountType.USER: ({"ACTIVE"}, "SUSPENDED", "ACTIVE"),
    AccountType.OPERATOR: ({"PENDING", "ACTIVE", "RESTRICTED"}, "SUSPENDED", "ACTIVE"),
    AccountType.BUSINESS: ({"GOOD", "RESTRICTED"}, "SUSPENDED", "GOOD"),
    AccountType.GROUP: ({"GOOD", "RESTRICTED"}, "SUSPENDED", "GOOD"),
}
_OFFBOARDABLE = {AccountType.USER, AccountType.OPERATOR}

REASON_MIN_LENGTH = 10
MAX_DURATION_DAYS = 365


def _current_state(account_type: str, account_id: Any) -> str | None:
    if account_type == AccountType.USER:
        return admin_accounts.status_of(account_id)
    directory = _KIND_TO_DIRECTORY[account_type]  # type: ignore[index]
    row = directory.queryset().filter(id=account_id).first()
    return directory.row(row)["state"] if row is not None else None


def _set_state(account_type: str, account_id: Any, state: str) -> tuple[str, str]:
    if account_type == AccountType.USER:
        return admin_accounts.set_state(account_id, state)
    return _KIND_TO_DIRECTORY[account_type].set_state(account_id, state)  # type: ignore[index]


def _target_state(account_type: str, account_id: Any, action: str, current: str) -> str:
    starts, suspended, default = _SUSPENDABLE[account_type]  # type: ignore[index]
    if action == InterventionAction.SUSPEND:
        if current not in starts:
            raise InterventionNotAllowed(f"An account that is {current} can't be suspended.")
        return suspended
    if action == InterventionAction.REINSTATE:
        if current != suspended:
            raise InterventionNotAllowed("Only a suspended account can be reinstated.")
        last = (
            AdminIntervention.objects.filter(
                account_type=account_type,
                account_id=account_id,
                action=InterventionAction.SUSPEND,
            )
            .order_by("-created_at")
            .values_list("before_state", flat=True)
            .first()
        )
        return last if last in starts else default
    # OFFBOARD
    if account_type not in _OFFBOARDABLE:
        raise InterventionNotAllowed(
            "This kind of account can't be offboarded; suspend it instead."
        )
    if current == "OFFBOARDED":
        raise InterventionNotAllowed("This account is already offboarded.")
    return "OFFBOARDED"


def intervene(
    *,
    actor: Any,
    account_type: str,
    account_id: Any,
    action: str,
    reason: str,
    duration_days: int | None = None,
) -> dict[str, Any]:
    """Suspend, reinstate or offboard an account (FR-ADM-4). Permission,
    then input checks, then the step-up gate, then one transaction: the
    state change, the ``admin_intervention`` row and the audit entry."""
    _require(actor, "admin.account.intervene")
    if account_type not in _SUSPENDABLE:
        raise InvalidIntervention("Unknown account type.")
    if action not in InterventionAction.values:
        raise InvalidIntervention("Unknown action.")
    reason = (reason or "").strip()
    if len(reason) < REASON_MIN_LENGTH:
        raise InvalidIntervention(f"Give a reason of at least {REASON_MIN_LENGTH} characters.")
    if duration_days is not None and (
        action != InterventionAction.SUSPEND or not 1 <= duration_days <= MAX_DURATION_DAYS
    ):
        raise InvalidIntervention(
            f"A duration is 1 to {MAX_DURATION_DAYS} days, on a suspension only."
        )
    user = _user(actor)
    if account_type == AccountType.USER and str(account_id) == str(getattr(user, "id", "")):
        raise InterventionNotAllowed("You can't act on your own account.")

    require_step_up(actor)

    with transaction.atomic():
        current = _current_state(account_type, account_id)
        if current is None:
            from rest_framework.exceptions import NotFound

            raise NotFound("No such account.")
        target = _target_state(account_type, account_id, action, current)
        before, after = _set_state(account_type, account_id, target)
        row = AdminIntervention.objects.create(
            account_type=account_type,
            account_id=account_id,
            action=action,
            admin=user,
            reason=reason,
            duration_days=duration_days,
            before_state=before,
            after_state=after,
        )
        audit.record(
            actor=actor,
            action=f"admin.account.{action.lower()}",
            entity_type=account_type.lower(),
            entity_id=account_id,
            before={"state": before},
            after={
                "state": after,
                "reason": reason,
                "duration_days": duration_days,
                "intervention_id": str(row.id),
            },
            source_channel="ADMIN_UI",
        )
    return {"id": str(row.id), "before_state": before, "after_state": after}


# ─── Configuration (§19.3, D-3) ─────────────────────────────────────────
#: The keys a Platform Admin may change from the console in Increment 9
#: (D-3). Value bands, role_permissions, vehicle classes and verification
#: requirements stay read-only: they underpin approved invariants and
#: privilege boundaries.
EDITABLE_CONFIG_PATHS = (
    "commission.rate",
    "commission.min_fee_kes",
    "commission.cap_kes",
    "timeouts.request_expiry_hours",
    "timeouts.offer_expiry_hours",
    "timeouts.delivery_acceptance.standard_hours",
    "timeouts.delivery_acceptance.high_hours",
    "timeouts.post_completion_window.default_hours",
    "timeouts.post_completion_window.high_and_latent_days",
    "timeouts.stale_assignment_alert_minutes",
)


def _patch_from(changes: dict[str, Any]) -> dict[str, Any]:
    """``{"commission.rate": 0.08}`` → ``{"commission": {"rate": 0.08}}``,
    refusing any path outside the allowlist and any non-number value."""
    if not isinstance(changes, dict) or not changes:
        raise InvalidConfigChange("Nothing to change.")
    patch: dict[str, Any] = {}
    for path, value in changes.items():
        if path not in EDITABLE_CONFIG_PATHS:
            raise ConfigKeyNotEditable(f"{path} can't be changed from the console.")
        if isinstance(value, bool) or not isinstance(value, int | float):
            raise InvalidConfigChange(f"{path} must be a number.")
        if path != "commission.rate" and (not isinstance(value, int) or value < 0):
            raise InvalidConfigChange(f"{path} must be a whole number, 0 or more.")
        node = patch
        *parents, leaf = path.split(".")
        for part in parents:
            node = node.setdefault(part, {})
        node[leaf] = value
    return patch


def config_view(*, actor: Any) -> dict[str, Any]:
    from fikisha.platform_config import services as config_services

    _require(actor, "admin.config.read")
    return {
        "version": config_services.current_version(),
        "config": config_services.current(),
        "editable_paths": list(EDITABLE_CONFIG_PATHS),
        "versions": config_services.versions(),
    }


def _validated_changes(changes: dict[str, Any]) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    from fikisha.platform_config import services as config_services
    from fikisha.platform_config.defaults import ConfigValidationError

    patch = _patch_from(changes)
    try:
        diff = config_services.preview_change(patch)
    except ConfigValidationError as exc:
        raise InvalidConfigChange(str(exc)) from exc
    if not diff:
        raise InvalidConfigChange("Those are already the live values.")
    return patch, diff


def preview_config_change(*, actor: Any, changes: dict[str, Any]) -> dict[str, Any]:
    """What would change, and the commission on a few sample prices before
    and after. Changes nothing."""
    from fikisha.jobs.commission import calculate_commission_kes
    from fikisha.platform_config import services as config_services

    _require(actor, "admin.config.read")
    _patch, diff = _validated_changes(changes)

    live = config_services.current()["commission"]
    proposed = dict(live)
    for change in diff:
        if change["path"].startswith("commission."):
            proposed[change["path"].split(".", 1)[1]] = change["after"]

    def fee(price: int, cfg: dict[str, Any]) -> int:
        return calculate_commission_kes(
            price, rate=cfg["rate"], min_fee_kes=cfg["min_fee_kes"], cap_kes=cfg["cap_kes"]
        )

    samples = [
        {
            "agreed_price_kes": price,
            "before_kes": fee(price, live),
            "after_kes": fee(price, proposed),
        }
        # KES 300 / 3,000 / 10,000 / 100,000
        for price in (30_000, 300_000, 1_000_000, 10_000_000)
    ]
    return {
        "version": config_services.current_version(),
        "changes": diff,
        "commission_samples": samples,
    }


def apply_config_change(*, actor: Any, changes: dict[str, Any], rationale: str) -> dict[str, Any]:
    """Apply through ``platform_config.services.apply_change`` (versioned,
    validated, audited, emits ``platform_config.changed``). Single-admin
    draft → diff → apply (D-3); needs a step-up."""
    from fikisha.platform_config import services as config_services

    _require(actor, "admin.config.change")
    rationale = (rationale or "").strip()
    if len(rationale) < REASON_MIN_LENGTH:
        raise InvalidConfigChange(f"Give a reason of at least {REASON_MIN_LENGTH} characters.")
    patch, diff = _validated_changes(changes)

    require_step_up(actor)

    version = config_services.apply_change(
        patch=patch, changed_by=_user(actor), rationale=rationale
    )
    return {"version": version.version, "changes": diff}
