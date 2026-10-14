"""Fixtures for the Platform Admin console tests (Design Phase 6 Increment
9). Re-exports the jobs fixtures (a verified business, verified operators,
confirmed and delivered jobs); see inbox/tests/conftest.py for the pattern."""

from __future__ import annotations

import dataclasses
from collections.abc import Callable
from typing import Any

import pytest

from fikisha.jobs.tests.conftest import (  # noqa: F401 - re-exported fixtures
    actor_for,
    admin_actor,
    business_actor,
    complete_job,
    delivered_job,
    do_transition,
    draft_job,
    driver_actor,
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
def stepped_up_admin(admin_actor: Any) -> Any:  # noqa: F811
    """The Platform Admin as if a fresh MFA step-up had just succeeded. No
    request can produce this yet (admin MFA is D-1, deferred); it lets the
    services behind the step-up gate be tested now."""
    return dataclasses.replace(admin_actor, is_step_up_fresh=True)


@pytest.fixture
def make_group(make_verified_operator: Callable) -> Callable[..., Any]:  # noqa: F811
    from fikisha.groups.models import (
        GroupMemberRole,
        GroupMembership,
        GroupMembershipStatus,
        GroupType,
        OperatorGroup,
    )

    def _make(phone: str = "+254733999003", name: str = "Kitengela Fleet") -> Any:
        manager = make_verified_operator(phone, "Group Manager")
        group = OperatorGroup.objects.create(
            name=name, type=GroupType.FLEET, primary_contact=manager.user
        )
        GroupMembership.objects.create(
            group=group,
            operator=manager,
            role=GroupMemberRole.OWNER,
            status=GroupMembershipStatus.ACTIVE,
        )
        return group

    return _make
