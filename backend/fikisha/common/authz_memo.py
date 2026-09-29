"""Opt-in memo for authorization lookups during one bulk read.

A read that checks many jobs for one actor (the Messages inbox, ADR-2D-37)
asks the same membership questions over and over: "is this user an active
member of business X / group Y", "does this user own operator profile Z".
Inside :func:`authz_memo` the membership primitives answer each distinct
question once; outside it (every other call path, including all writes)
nothing is cached and they behave exactly as before.

Only use it around read-only work: a memoized answer would not see a
membership change made later in the same block.
"""

from __future__ import annotations

from collections.abc import Callable, Hashable, Iterator
from contextlib import contextmanager
from contextvars import ContextVar
from typing import Any, TypeVar

T = TypeVar("T")

_memo: ContextVar[dict[Hashable, Any] | None] = ContextVar("authz_memo", default=None)


@contextmanager
def authz_memo() -> Iterator[None]:
    token = _memo.set({})
    try:
        yield
    finally:
        _memo.reset(token)


def memoized(key: Hashable, compute: Callable[[], T]) -> T:
    """``compute()``, cached under ``key`` while an :func:`authz_memo` block
    is active; called every time otherwise. Keys must include everything the
    answer depends on (at least the user id and the resource id)."""
    memo = _memo.get()
    if memo is None:
        return compute()
    if key not in memo:
        memo[key] = compute()
    return memo[key]
