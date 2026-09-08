"""Identity data model — foundation set.

Deliberately *not* on this model: Business / Operator / Vehicle / Trust / Job
data. Those are separate bounded modules introduced later. ``User`` stays lean
and extensible (Phase 2A brief §10).
"""

from __future__ import annotations

from typing import Any, ClassVar

from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin
from django.db import models
from django.utils import timezone

from fikisha.common.uuid7 import uuid7
from fikisha.identity.phone import normalize_phone


class UserStatus(models.TextChoices):
    ACTIVE = "ACTIVE", "Active"
    SUSPENDED = "SUSPENDED", "Suspended"
    OFFBOARDED = "OFFBOARDED", "Offboarded"


class UserManager(models.Manager["User"]):
    use_in_migrations = True

    def _create(self, phone: str, password: str | None, **extra: Any) -> User:
        if not phone:
            raise ValueError("phone is required")
        user = self.model(phone=normalize_phone(phone), **extra)
        if password:
            user.set_password(password)
        else:
            user.set_unusable_password()  # normal users authenticate by OTP
        user.full_clean(exclude=["password", "last_login"])
        user.save(using=self._db)
        return user

    def create_user(self, phone: str, password: str | None = None, **extra: Any) -> User:
        extra.setdefault("is_staff", False)
        extra.setdefault("is_superuser", False)
        return self._create(phone, password, **extra)

    def create_superuser(self, phone: str, password: str, **extra: Any) -> User:
        extra.update(is_staff=True, is_superuser=True, status=UserStatus.ACTIVE)
        return self._create(phone, password, **extra)

    def get_or_create_by_phone(self, phone: str) -> tuple[User, bool]:
        norm = normalize_phone(phone)
        try:
            return self.get(phone=norm), False
        except self.model.DoesNotExist:
            return self.create_user(norm), True


class User(AbstractBaseUser, PermissionsMixin):
    id = models.UUIDField(primary_key=True, default=uuid7, editable=False)
    phone = models.CharField(max_length=20, unique=True)
    email = models.EmailField(blank=True, default="")
    display_name = models.CharField(max_length=120, blank=True, default="")
    locale = models.CharField(
        max_length=5, choices=[("en", "English"), ("sw", "Kiswahili")], default="en"
    )
    status = models.CharField(max_length=16, choices=UserStatus.choices, default=UserStatus.ACTIVE)

    # ``is_staff`` here only gates the (dev-only) Django admin site. Real
    # administrative capability comes from AdminProfile + RoleAssignment +
    # the authorization engine.
    is_staff = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    USERNAME_FIELD = "phone"
    REQUIRED_FIELDS: ClassVar[list[str]] = []

    objects = UserManager()

    class Meta:
        db_table = "identity_user"
        indexes = [models.Index(fields=["status"])]

    def __str__(self) -> str:
        return self.phone

    def clean(self) -> None:
        super().clean()
        self.phone = normalize_phone(self.phone)

    # django-stubs types ``AbstractBaseUser.is_active`` as ``bool | BooleanField``;
    # Fikisha has no ``is_active`` column — it is derived from ``status``.
    @property  # type: ignore[override]
    def is_active(self) -> bool:
        return self.status == UserStatus.ACTIVE

    @is_active.setter
    def is_active(self, value: bool) -> None:  # pragma: no cover - compat shim
        self.status = UserStatus.ACTIVE if value else UserStatus.SUSPENDED


class OtpPurpose(models.TextChoices):
    LOGIN = "LOGIN", "Login"
    STEP_UP = "STEP_UP", "Admin step-up"
    # PICKUP_HANDOVER / RECIPIENT_VERIFY arrive with the custody / recipient modules.


class OtpChallenge(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid7, editable=False)
    phone = models.CharField(max_length=20, db_index=True)
    purpose = models.CharField(max_length=24, choices=OtpPurpose.choices, default=OtpPurpose.LOGIN)
    code_hash = models.CharField(max_length=256)
    attempts = models.PositiveSmallIntegerField(default=0)
    max_attempts = models.PositiveSmallIntegerField(default=5)
    expires_at = models.DateTimeField()
    consumed_at = models.DateTimeField(null=True, blank=True)
    request_ip = models.GenericIPAddressField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        db_table = "identity_otp_challenge"
        indexes = [models.Index(fields=["phone", "purpose", "created_at"])]

    @property
    def is_expired(self) -> bool:
        return timezone.now() >= self.expires_at

    @property
    def is_consumed(self) -> bool:
        return self.consumed_at is not None

    @property
    def is_locked(self) -> bool:
        return self.attempts >= self.max_attempts


class AuthSession(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid7, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="sessions")
    device_label = models.CharField(max_length=120, blank=True, default="")
    user_agent = models.CharField(max_length=400, blank=True, default="")
    ip = models.GenericIPAddressField(null=True, blank=True)
    is_admin_session = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    last_seen_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    revoked_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "identity_auth_session"
        indexes = [models.Index(fields=["user", "revoked_at"])]

    @property
    def is_active(self) -> bool:
        return self.revoked_at is None and timezone.now() < self.expires_at


class RefreshToken(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid7, editable=False)
    session = models.ForeignKey(
        AuthSession, on_delete=models.CASCADE, related_name="refresh_tokens"
    )
    token_hash = models.CharField(max_length=64, unique=True)
    rotated_from = models.ForeignKey(
        "self", null=True, blank=True, on_delete=models.SET_NULL, related_name="rotations"
    )
    used_at = models.DateTimeField(null=True, blank=True)
    expires_at = models.DateTimeField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "identity_refresh_token"

    @property
    def is_spent(self) -> bool:
        return self.used_at is not None

    @property
    def is_expired(self) -> bool:
        return timezone.now() >= self.expires_at


class AdminRole(models.TextChoices):
    PLATFORM_ADMIN = "PLATFORM_ADMIN", "Platform Admin"
    OPERATIONS_OFFICER = "OPERATIONS_OFFICER", "Operations Officer"
    # 4-role split — defined now, enabled by config later (Phase 0 D-ADM-1).
    VERIFIER = "VERIFIER", "Verifier"
    OPERATIONS = "OPERATIONS", "Operations"
    DISPUTE_OFFICER = "DISPUTE_OFFICER", "Dispute Officer"


class AdminProfile(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid7, editable=False)
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="admin_profile")
    active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "identity_admin_profile"


class RoleAssignment(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid7, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="role_assignments")
    role = models.CharField(max_length=32, choices=AdminRole.choices)
    assigned_by = models.ForeignKey(
        User, null=True, blank=True, on_delete=models.SET_NULL, related_name="+"
    )
    assigned_at = models.DateTimeField(auto_now_add=True)
    revoked_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "identity_role_assignment"
        constraints = [
            models.UniqueConstraint(
                fields=["user", "role"],
                condition=models.Q(revoked_at__isnull=True),
                name="uniq_active_role_per_user",
            )
        ]

    @property
    def is_active(self) -> bool:
        return self.revoked_at is None


class TotpDevice(models.Model):
    """Foundation stub for admin TOTP MFA.

    Phase 2A creates the table + the ``confirmed_at`` gate the authorization
    engine reads. Actual TOTP secret generation / code verification is a
    Phase 2B item (see docs/phase-2/phase-2a-decisions.md ADR-2A-07).
    """

    id = models.UUIDField(primary_key=True, default=uuid7, editable=False)
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="totp_device")
    secret_encrypted = models.BinaryField(null=True, blank=True)
    confirmed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "identity_totp_device"

    @property
    def is_confirmed(self) -> bool:
        return self.confirmed_at is not None
