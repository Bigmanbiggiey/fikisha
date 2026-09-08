"""UUIDv7 generator (RFC 9562).

Phase 1 (ADR-004 / database-design §1) mandates time-ordered, non-guessable
identifiers. ``uuid.uuid7`` only exists in the CPython 3.14 stdlib; the project
targets 3.12, so this ~20-line implementation is used instead. Layout:

    unix_ts_ms (48 bits) | ver=0b0111 (4) | rand_a (12) | var=0b10 (2) | rand_b (62)
"""

from __future__ import annotations

import os
import time
import uuid


def uuid7() -> uuid.UUID:
    """Return a fresh UUIDv7."""
    ts_ms = int(time.time() * 1000) & 0xFFFFFFFFFFFF  # 48 bits
    rand = int.from_bytes(os.urandom(10), "big")  # 80 bits of randomness
    rand_a = (rand >> 68) & 0xFFF  # top 12 bits
    rand_b = rand & 0x3FFFFFFFFFFFFFFF  # low 62 bits

    value = ts_ms << 80
    value |= 0x7 << 76  # version 7
    value |= rand_a << 64
    value |= 0b10 << 62  # RFC 4122 variant
    value |= rand_b
    return uuid.UUID(int=value)


def uuid7_str() -> str:
    return str(uuid7())
