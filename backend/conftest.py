"""Pytest fixtures shared across the backend test suite."""

from __future__ import annotations

from collections.abc import Iterator
from typing import Any

import pytest
from django.core.cache import cache
from rest_framework.test import APIClient


@pytest.fixture(autouse=True)
def _clear_cache() -> Iterator[None]:
    cache.clear()
    yield
    cache.clear()


@pytest.fixture
def api() -> APIClient:
    return APIClient()


@pytest.fixture
def user(db: Any) -> Any:
    from fikisha.identity.models import User

    return User.objects.create_user(phone="+254700000001")


@pytest.fixture
def other_user(db: Any) -> Any:
    from fikisha.identity.models import User

    return User.objects.create_user(phone="+254700000002")


@pytest.fixture
def platform_admin(db: Any) -> Any:
    from fikisha.identity.models import AdminProfile, AdminRole, RoleAssignment, User

    admin_user = User.objects.create_user(phone="+254700000009", is_staff=True)
    AdminProfile.objects.create(user=admin_user, active=True)
    RoleAssignment.objects.create(user=admin_user, role=AdminRole.PLATFORM_ADMIN)
    return admin_user


@pytest.fixture
def ops_officer(db: Any) -> Any:
    from fikisha.identity.models import AdminProfile, AdminRole, RoleAssignment, User

    ops_user = User.objects.create_user(phone="+254700000008", is_staff=True)
    AdminProfile.objects.create(user=ops_user, active=True)
    RoleAssignment.objects.create(user=ops_user, role=AdminRole.OPERATIONS_OFFICER)
    return ops_user


@pytest.fixture
def auth_client(api: APIClient, user: Any) -> APIClient:
    """An APIClient carrying a valid Bearer access token for ``user``."""
    from fikisha.identity.services import auth as auth_service

    issued = auth_service.start_session(user=user, device_label="pytest")
    api.credentials(HTTP_AUTHORIZATION=f"Bearer {issued.access_token}")
    api._issued_session = issued  # type: ignore[attr-defined]
    return api


@pytest.fixture
def admin_client(api: APIClient, platform_admin: Any) -> APIClient:
    from fikisha.identity.services import auth as auth_service

    issued = auth_service.start_session(user=platform_admin, device_label="pytest-admin")
    api.credentials(HTTP_AUTHORIZATION=f"Bearer {issued.access_token}")
    return api
