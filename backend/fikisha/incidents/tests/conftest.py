"""Fixtures for the Phase 2D Step 8 (Incidents & Disputes) tests.

Re-exports the Jobs-app test fixtures (verified business, driver/vehicle,
assignment, custody helpers) — pytest discovers fixtures by scanning a
conftest module's own namespace, so a plain import re-registers them here
without duplicating their (fairly involved) setup logic.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

import pytest

from fikisha.jobs.tests.conftest import (  # noqa: F401 - re-exported fixtures
    actor_for,
    admin_actor,
    business_actor,
    do_transition,
    driver_actor,
    driver_and_vehicle,
    eligible_driver,
    eligible_vehicle,
    make_assigned_job,
    make_confirmed_job,
    make_vehicle,
    make_verified_operator,
    verified_business,
    verify_subject,
)


@pytest.fixture
def ops_actor(ops_officer: Any, actor_for: Callable) -> Any:  # noqa: F811 - fixture param shadow
    return actor_for(ops_officer)


@pytest.fixture
def business_owner_actor(verified_business: Any, business_actor: Any) -> Any:  # noqa: F811
    """``business_actor`` (root conftest's ``user``) already owns
    ``verified_business`` (jobs conftest's ``verified_business`` fixture uses
    ``user`` as the owner)."""
    return business_actor


@pytest.fixture
def other_business_actor(make_user: Callable, actor_for: Callable) -> Any:  # noqa: F811
    """A user with **no** relationship to the test job at all — for
    cross-business / cross-job isolation tests."""
    stranger = make_user("+254799000123")
    return actor_for(stranger)
