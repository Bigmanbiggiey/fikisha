"""OTP request + verification service tests (Phase 2A brief §30 — authentication)."""

from __future__ import annotations

from datetime import timedelta

import pytest
from django.utils import timezone
from rest_framework.exceptions import AuthenticationFailed

from fikisha.audit.models import AuditLogEntry
from fikisha.common.exceptions import RateLimitedError
from fikisha.identity.models import OtpChallenge, User
from fikisha.identity.services import otp as otp_service

pytestmark = pytest.mark.django_db

PHONE = "+254733000111"


class TestRequest:
    def test_request_creates_challenge_and_returns_dev_code(self) -> None:
        result = otp_service.request_otp(phone=PHONE)
        assert result.dev_code == "000000"  # OTP_DEV_FIXED_CODE in test settings
        challenge = OtpChallenge.objects.get(pk=result.challenge_id)
        assert challenge.phone == PHONE
        assert challenge.code_hash and challenge.code_hash != "000000"  # stored hashed
        assert AuditLogEntry.objects.filter(action="auth.otp.requested").exists()

    def test_request_rate_limited_per_minute(self) -> None:
        # OTP_REQUEST_RATE_PER_MINUTE defaults to 1 in base settings.
        otp_service.request_otp(phone=PHONE)
        with pytest.raises(RateLimitedError):
            otp_service.request_otp(phone=PHONE)


class TestVerify:
    def _request(self) -> str:
        return otp_service.request_otp(phone=PHONE).challenge_id

    def test_verify_success_creates_user(self) -> None:
        cid = self._request()
        assert not User.objects.filter(phone=PHONE).exists()
        user = otp_service.verify_otp(challenge_id=cid, code="000000")
        assert user.phone == PHONE
        assert User.objects.filter(phone=PHONE).count() == 1
        OtpChallenge.objects.get(pk=cid).refresh_from_db()
        assert OtpChallenge.objects.get(pk=cid).is_consumed
        assert AuditLogEntry.objects.filter(action="auth.otp.verified").exists()

    def test_verify_wrong_code(self) -> None:
        cid = self._request()
        with pytest.raises(AuthenticationFailed) as exc:
            otp_service.verify_otp(challenge_id=cid, code="999999")
        assert exc.value.detail.code == "otp.invalid"
        assert OtpChallenge.objects.get(pk=cid).attempts == 1

    def test_verify_expired(self) -> None:
        cid = self._request()
        OtpChallenge.objects.filter(pk=cid).update(expires_at=timezone.now() - timedelta(seconds=1))
        with pytest.raises(AuthenticationFailed) as exc:
            otp_service.verify_otp(challenge_id=cid, code="000000")
        assert exc.value.detail.code == "otp.expired"

    def test_verify_already_used(self) -> None:
        cid = self._request()
        otp_service.verify_otp(challenge_id=cid, code="000000")
        with pytest.raises(AuthenticationFailed) as exc:
            otp_service.verify_otp(challenge_id=cid, code="000000")
        assert exc.value.detail.code == "otp.already_used"

    def test_verify_too_many_attempts_locks(self) -> None:
        cid = self._request()
        for _ in range(5):
            with pytest.raises(AuthenticationFailed):
                otp_service.verify_otp(challenge_id=cid, code="111111")
        # Even the correct code is now rejected.
        with pytest.raises(AuthenticationFailed) as exc:
            otp_service.verify_otp(challenge_id=cid, code="000000")
        assert exc.value.detail.code == "otp.too_many_attempts"

    def test_verify_unknown_challenge(self) -> None:
        with pytest.raises(AuthenticationFailed) as exc:
            otp_service.verify_otp(
                challenge_id="00000000-0000-0000-0000-000000000000", code="000000"
            )
        assert exc.value.detail.code == "otp.invalid"
