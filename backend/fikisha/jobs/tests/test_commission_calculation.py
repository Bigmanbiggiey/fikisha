"""Commission calculation: deterministic, integer-in/integer-out, boundary
cases (Step 9 brief §6). ``rate``/``min_fee_kes``/``cap_kes`` are passed
explicitly here — the config-driven resolution path is covered in
``test_commission_completion.py``."""

from __future__ import annotations

import pytest

from fikisha.jobs.commission import calculate_commission_kes

RATE = 0.10
MIN_FEE = 4000  # KES 40.00
CAP = 500000  # KES 5,000.00


def _calc(price: int) -> int:
    return calculate_commission_kes(price, rate=RATE, min_fee_kes=MIN_FEE, cap_kes=CAP)


def test_below_minimum_is_floored_to_the_minimum() -> None:
    # 10% of 30,000 minor units (KES 300) = 3,000 minor units < 4,000 floor.
    assert _calc(30_000) == MIN_FEE


def test_exactly_the_minimum_boundary() -> None:
    # 10% of 40,000 minor units (KES 400) = exactly 4,000.
    assert _calc(40_000) == MIN_FEE


def test_normal_price_uses_the_flat_rate() -> None:
    # 10% of 1,200,000 (KES 12,000) = 120,000 (KES 1,200) — under the cap.
    assert _calc(1_200_000) == 120_000


def test_exactly_the_cap_boundary() -> None:
    # 10% of 5,000,000 (KES 50,000) = exactly 500,000 (KES 5,000).
    assert _calc(5_000_000) == CAP


def test_above_the_cap_is_capped() -> None:
    # 10% of 50,000,000 (KES 500,000) = 5,000,000 — well above the cap.
    assert _calc(50_000_000) == CAP


def test_a_very_high_value_job_is_still_capped_at_5000_kes() -> None:
    assert _calc(1_000_000_000) == CAP


def test_zero_price_still_floors_to_the_minimum() -> None:
    assert _calc(0) == MIN_FEE


def test_result_is_always_a_plain_int() -> None:
    result = _calc(1_200_000)
    assert isinstance(result, int)
    assert not isinstance(result, bool)


def test_calculation_is_deterministic_across_repeated_calls() -> None:
    results = {_calc(3_330_003) for _ in range(50)}
    assert len(results) == 1


def test_negative_price_is_rejected() -> None:
    with pytest.raises(ValueError):
        _calc(-1)


def test_non_int_price_is_rejected() -> None:
    with pytest.raises(TypeError):
        calculate_commission_kes(1_200_000.0, rate=RATE, min_fee_kes=MIN_FEE, cap_kes=CAP)  # type: ignore[arg-type]


def test_a_price_producing_a_fractional_minor_unit_rounds_half_up() -> None:
    # 10% of 3,330,003 = 333,000.3 -> rounds to 333,000 (below the cap).
    assert _calc(3_330_003) == 333_000
    # 10% of 3,330,005 = 333,000.5 -> rounds half-up to 333,001.
    assert _calc(3_330_005) == 333_001


def test_the_approved_rate_of_010_is_exact_not_a_binary_float_artefact() -> None:
    """``Decimal(str(0.10))`` must be exactly ``0.1`` — guards against
    ``Decimal(0.10)`` picking up the binary float's rounding error, which
    would silently corrupt every commission figure by a fraction of a cent."""
    from decimal import Decimal

    assert Decimal(str(RATE)) == Decimal("0.1")
    # 10% of 999,999 = 99,999.9 -> rounds half-up to 100,000, computed via the
    # exact decimal path (a naive binary-float multiply can drift by ulps
    # around a value this close to a round number).
    assert _calc(999_999) == 100_000
