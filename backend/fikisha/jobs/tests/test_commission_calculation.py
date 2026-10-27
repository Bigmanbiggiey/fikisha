"""Commission calculation: deterministic, integer-in/integer-out, boundary
cases (Step 9 brief §6), one side at a time since the commission split
(ADR-2D-55: 5% each side, no minimum, no cap, each side rounded on its own,
D-2). The config-driven path is covered in ``test_commission_completion.py``."""

from __future__ import annotations

import pytest

from fikisha.jobs.commission import calculate_fee_kes, fee_view

RATE = 0.05


def _calc(price: int) -> int:
    return calculate_fee_kes(price, rate=RATE)


def test_small_jobs_have_no_minimum() -> None:
    # 5% of KES 300 = KES 15 (the old KES 40 minimum is gone).
    assert _calc(30_000) == 1_500


def test_normal_price() -> None:
    # 5% of KES 2,500 = KES 125.
    assert _calc(250_000) == 12_500


def test_large_jobs_have_no_cap() -> None:
    # 5% of KES 80,000 = KES 4,000; 5% of KES 1,200,000 = KES 60,000.
    assert _calc(8_000_000) == 400_000
    assert _calc(120_000_000) == 6_000_000


def test_zero_price_is_zero() -> None:
    assert _calc(0) == 0


def test_zero_rate_is_zero() -> None:
    assert calculate_fee_kes(1_000_000, rate=0) == 0


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
        calculate_fee_kes(1_200_000.0, rate=RATE)  # type: ignore[arg-type]


def test_a_fractional_minor_unit_rounds_half_up() -> None:
    # 5% of 30 = 1.5 -> 2; 5% of 29 = 1.45 -> 1.
    assert _calc(30) == 2
    assert _calc(29) == 1


def test_each_side_rounds_on_its_own() -> None:
    """D-2: on an odd price the two sides together can differ from exactly
    10% by a cent: 5% of 30 cents is 1.5 -> 2 each, 4 together, while 10%
    would be 3."""
    assert _calc(30) + _calc(30) == 4


def test_the_rate_is_exact_not_a_binary_float_artefact() -> None:
    from decimal import Decimal

    assert Decimal(str(RATE)) == Decimal("0.05")
    # 5% of 1,999,999 = 99,999.95 -> 100,000 via the exact decimal path.
    assert _calc(1_999_999) == 100_000


def test_fee_view_business_pays_on_top_operator_keeps_the_rest() -> None:
    from decimal import Decimal

    business = fee_view(250_000, "BUSINESS", Decimal("0.05"))
    operator = fee_view(250_000, "OPERATOR", Decimal("0.05"))
    assert business == {
        "party": "BUSINESS",
        "rate": "0.05",
        "fee_kes": 12_500,
        "total_cost_kes": 262_500,
    }
    assert operator == {
        "party": "OPERATOR",
        "rate": "0.05",
        "fee_kes": 12_500,
        "operator_keeps_kes": 237_500,
    }
