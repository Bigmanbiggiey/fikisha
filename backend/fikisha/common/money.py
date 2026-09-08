"""Money value type — integer KES minor units.

Phase 1 NFR-INT-3 / database-design §1: money is *always* an integer number of
minor units (cents), never a float. No money-bearing models exist in Phase 2A;
this type is provided so later modules use it consistently from day one.
"""

from __future__ import annotations

from dataclasses import dataclass

CURRENCY = "KES"
MINOR_UNITS_PER_MAJOR = 100


@dataclass(frozen=True, slots=True)
class Money:
    """An amount in KES minor units (e.g. ``Money(400000)`` == KSh 4,000.00)."""

    minor_units: int
    currency: str = CURRENCY

    def __post_init__(self) -> None:
        if not isinstance(self.minor_units, int) or isinstance(self.minor_units, bool):
            raise TypeError("Money.minor_units must be an int (KES minor units)")
        if self.currency != CURRENCY:
            raise ValueError(f"Only {CURRENCY} is supported in the MVP")

    @classmethod
    def from_major(cls, shillings: int) -> Money:
        return cls(int(shillings) * MINOR_UNITS_PER_MAJOR)

    @property
    def major(self) -> float:
        return self.minor_units / MINOR_UNITS_PER_MAJOR

    def __str__(self) -> str:
        return f"KSh {self.major:,.2f}"

    def __add__(self, other: Money) -> Money:
        return Money(self.minor_units + other.minor_units)

    def __sub__(self, other: Money) -> Money:
        return Money(self.minor_units - other.minor_units)
