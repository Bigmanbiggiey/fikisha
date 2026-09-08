"""The authorization engine.

``authorize(actor, action, resource=None)`` looks up a registered **policy** for
``action`` (exact match, then longest wildcard prefix) and returns a
:class:`Decision`. **Default deny**: an action with no policy is denied.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from fikisha.common.exceptions import AuthorizationError

PolicyFn = Callable[["Any", str, "Any"], "Decision"]

_POLICIES: dict[str, PolicyFn] = {}


@dataclass(frozen=True, slots=True)
class Decision:
    allowed: bool
    code: str = "authz.forbidden"
    reason: str = ""

    def __bool__(self) -> bool:
        return self.allowed


ALLOW = Decision(True, code="ok")


def deny(code: str = "authz.forbidden", reason: str = "") -> Decision:
    return Decision(False, code=code, reason=reason)


def policy(action: str) -> Callable[[PolicyFn], PolicyFn]:
    def _register(func: PolicyFn) -> PolicyFn:
        if action in _POLICIES:  # pragma: no cover - programming error
            raise RuntimeError(f"policy for action {action!r} already registered")
        _POLICIES[action] = func
        return func

    return _register


def _resolve(action: str) -> PolicyFn | None:
    if action in _POLICIES:
        return _POLICIES[action]
    # longest wildcard prefix, e.g. "admin.*" matches "admin.ping"
    best: tuple[int, PolicyFn] | None = None
    for key, fn in _POLICIES.items():
        if key.endswith(".*") and action.startswith(key[:-1]):
            depth = key.count(".")
            if best is None or depth > best[0]:
                best = (depth, fn)
    return best[1] if best else None


def authorize(actor: Any, action: str, resource: Any = None) -> Decision:
    fn = _resolve(action)
    if fn is None:
        return deny("authz.no_policy", f"no policy registered for action {action!r}")
    try:
        return fn(actor, action, resource)
    except AuthorizationError as exc:  # a policy may raise instead of returning
        return deny(exc.code, str(exc))


def require(actor: Any, action: str, resource: Any = None) -> None:
    """Raise :class:`AuthorizationError` if not allowed (for use inside services)."""
    decision = authorize(actor, action, resource)
    if not decision.allowed:
        raise AuthorizationError(decision.reason or "Forbidden.", code=decision.code)


def registered_actions() -> list[str]:
    return sorted(_POLICIES)
