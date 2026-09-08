"""Tests for the shared/common layer: UUIDv7, Money, request-id, rate limiting."""

from __future__ import annotations

import time

import pytest
from django.test import RequestFactory

from fikisha.common.exceptions import RateLimitedError
from fikisha.common.money import Money
from fikisha.common.ratelimit import RateLimiter
from fikisha.common.request_id import HEADER, RequestIDMiddleware, get_request_id
from fikisha.common.uuid7 import uuid7


class TestUUID7:
    def test_version_and_variant_bits(self) -> None:
        u = uuid7()
        assert u.version == 7
        assert (u.int >> 62) & 0b11 == 0b10  # RFC 4122 variant

    def test_monotonic_ordering(self) -> None:
        a = uuid7()
        time.sleep(0.002)
        b = uuid7()
        assert str(a) < str(b)

    def test_uniqueness(self) -> None:
        assert len({uuid7() for _ in range(2000)}) == 2000


class TestMoney:
    def test_minor_units_only(self) -> None:
        assert Money(400000).major == 4000.0
        assert str(Money(400000)) == "KSh 4,000.00"

    def test_from_major(self) -> None:
        assert Money.from_major(5000).minor_units == 500000

    def test_rejects_float(self) -> None:
        with pytest.raises(TypeError):
            Money(1.5)  # type: ignore[arg-type]

    def test_rejects_bool(self) -> None:
        with pytest.raises(TypeError):
            Money(True)

    def test_arithmetic(self) -> None:
        assert (Money(100) + Money(50)).minor_units == 150
        assert (Money(100) - Money(50)).minor_units == 50


class TestRequestIDMiddleware:
    def test_generates_when_absent(self) -> None:
        rf = RequestFactory()
        seen: dict[str, str] = {}

        def view(request: object) -> object:
            seen["rid"] = get_request_id()
            from django.http import HttpResponse

            return HttpResponse("ok")

        mw = RequestIDMiddleware(view)
        response = mw(rf.get("/"))
        assert response[HEADER]
        assert seen["rid"] == response[HEADER]
        assert seen["rid"] != "-"

    def test_honours_valid_incoming(self) -> None:
        rf = RequestFactory()
        from django.http import HttpResponse

        mw = RequestIDMiddleware(lambda r: HttpResponse("ok"))
        response = mw(rf.get("/", HTTP_X_REQUEST_ID="abc12345-req"))
        assert response[HEADER] == "abc12345-req"

    def test_rejects_malformed_incoming(self) -> None:
        rf = RequestFactory()
        from django.http import HttpResponse

        mw = RequestIDMiddleware(lambda r: HttpResponse("ok"))
        response = mw(rf.get("/", HTTP_X_REQUEST_ID="bad id with spaces!"))
        assert response[HEADER] != "bad id with spaces!"


class TestRateLimiter:
    def test_allows_up_to_limit_then_blocks(self) -> None:
        rl = RateLimiter(scope="t", limit=3, window_seconds=60)
        for _ in range(3):
            rl.check("actor-1")
        with pytest.raises(RateLimitedError):
            rl.check("actor-1")

    def test_isolated_per_identifier(self) -> None:
        rl = RateLimiter(scope="t2", limit=1, window_seconds=60)
        rl.check("a")
        rl.check("b")  # different identifier — not blocked

    def test_fail_closed_when_cache_unavailable(self, monkeypatch: pytest.MonkeyPatch) -> None:
        rl = RateLimiter(scope="t3", limit=5, window_seconds=60, fail_closed=True)

        def boom(*_a: object, **_k: object) -> None:
            raise RuntimeError("cache down")

        monkeypatch.setattr("fikisha.common.ratelimit.cache.add", boom)
        with pytest.raises(RateLimitedError):
            rl.check("a")
