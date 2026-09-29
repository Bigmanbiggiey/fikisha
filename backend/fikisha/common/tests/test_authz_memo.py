"""``common.authz_memo`` (ADR-2D-37): caches only inside the block."""

from __future__ import annotations

from collections.abc import Callable

from fikisha.common.authz_memo import authz_memo, memoized


def _counter() -> tuple[list[int], Callable[[], int]]:
    calls: list[int] = []

    def compute() -> int:
        calls.append(1)
        return len(calls)

    return calls, compute


def test_outside_a_block_nothing_is_cached() -> None:
    calls, compute = _counter()
    memoized("k", compute)
    memoized("k", compute)
    assert len(calls) == 2


def test_inside_a_block_each_key_is_computed_once() -> None:
    calls, compute = _counter()
    with authz_memo():
        assert memoized("k", compute) == 1
        assert memoized("k", compute) == 1
        assert memoized("other", compute) == 2
    assert len(calls) == 2


def test_the_memo_ends_with_the_block() -> None:
    calls, compute = _counter()
    with authz_memo():
        memoized("k", compute)
    memoized("k", compute)
    with authz_memo():
        memoized("k", compute)
    assert len(calls) == 3
