"""Create or promote an administrative user by phone number.

Ops / local tooling, analogous to Django's ``createsuperuser`` — it grants an
existing (or new) ``identity.User`` an ``AdminProfile`` and an active
``RoleAssignment``. It does **not** implement any business-domain workflow.

    python manage.py create_admin +254700000009
    python manage.py create_admin +254700000009 --role OPERATIONS_OFFICER
    python manage.py create_admin +254700000009 --print-token   # smoke tests
"""

from __future__ import annotations

from typing import Any

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from fikisha.audit import services as audit
from fikisha.identity.models import AdminProfile, AdminRole, RoleAssignment, User
from fikisha.identity.phone import normalize_phone


class Command(BaseCommand):
    help = "Create or promote an administrative user by phone number."

    def add_arguments(self, parser: Any) -> None:
        parser.add_argument("phone", help="Phone number, e.g. +254700000009 or 0700000009")
        parser.add_argument(
            "--role",
            default=AdminRole.PLATFORM_ADMIN,
            choices=[r.value for r in AdminRole],
            help="Admin role to assign (default: PLATFORM_ADMIN).",
        )
        parser.add_argument(
            "--print-token",
            action="store_true",
            help="Also start a session and print a Bearer access token (local use only).",
        )

    def handle(self, *args: Any, **options: Any) -> None:
        try:
            phone = normalize_phone(options["phone"])
        except Exception as exc:
            raise CommandError(f"Invalid phone number: {exc}") from exc

        role = options["role"]

        with transaction.atomic():
            user, created = User.objects.get_or_create_by_phone(phone)
            profile, _ = AdminProfile.objects.get_or_create(user=user, defaults={"active": True})
            if not profile.active:
                profile.active = True
                profile.save(update_fields=["active"])

            assignment, role_created = RoleAssignment.objects.get_or_create(
                user=user, role=role, revoked_at=None
            )
            audit.record(
                actor=user,
                action="admin.role.granted",
                entity_type="user",
                entity_id=user.id,
                after={"role": role, "via": "manage.py create_admin"},
                source_channel="CLI",
            )

        self.stdout.write(
            self.style.SUCCESS(
                f"{'Created' if created else 'Updated'} admin {phone} "
                f"({'granted' if role_created else 'already had'} {role})"
            )
        )

        if options["print_token"]:
            from fikisha.identity.services import auth as auth_service

            issued = auth_service.start_session(
                user=user, device_label="create_admin --print-token"
            )
            self.stdout.write("")
            self.stdout.write(f"ACCESS_TOKEN={issued.access_token}")
