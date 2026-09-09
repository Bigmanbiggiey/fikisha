"""Group services — mutation paths not covered by the API happy-path tests."""

from __future__ import annotations

from typing import Any

import pytest

from fikisha.common.exceptions import ConflictError, DomainError
from fikisha.groups import services
from fikisha.groups.models import GroupMemberRole, GroupMembershipStatus, GroupType
from fikisha.identity.authz.actors import actor_from_user
from fikisha.operators import services as operator_services
from fikisha.operators.models import OperatingBase

pytestmark = pytest.mark.django_db


def _actor(u: Any) -> Any:
    return actor_from_user(u)


@pytest.fixture
def group(user: Any) -> Any:
    operator_services.create_profile(actor=_actor(user), full_name="Owner")
    return services.create_group(actor=_actor(user), name="G", type=GroupType.SACCO)


def test_create_group_requires_operator_profile(other_user: Any) -> None:
    with pytest.raises(DomainError):
        services.create_group(actor=_actor(other_user), name="X", type=GroupType.FLEET)


def test_owner_already_in_a_group_cannot_create_another(user: Any, group: Any) -> None:
    with pytest.raises(ConflictError):
        services.create_group(actor=_actor(user), name="Second", type=GroupType.FLEET)


def test_update_member_role_and_status(user: Any, other_user: Any, group: Any) -> None:
    driver_profile = operator_services.create_profile(actor=_actor(other_user), full_name="Driver")
    m = services.add_member(
        actor=_actor(user), group=group, operator=driver_profile, role=GroupMemberRole.DRIVER
    )
    services.update_member(
        actor=_actor(user), group=group, membership=m, role=GroupMemberRole.MANAGER
    )
    assert group.memberships.get(pk=m.pk).role == GroupMemberRole.MANAGER

    services.update_member(
        actor=_actor(user), group=group, membership=m, status=GroupMembershipStatus.INACTIVE
    )
    assert group.memberships.get(pk=m.pk).status == GroupMembershipStatus.INACTIVE


def test_reactivating_a_member_who_joined_elsewhere_conflicts(
    user: Any, other_user: Any, make_user: Any, group: Any
) -> None:
    shared = operator_services.create_profile(actor=_actor(other_user), full_name="Shared")
    m = services.add_member(
        actor=_actor(user), group=group, operator=shared, role=GroupMemberRole.DRIVER
    )
    services.update_member(
        actor=_actor(user), group=group, membership=m, status=GroupMembershipStatus.INACTIVE
    )
    # shared joins a different group
    other_owner = make_user("+254720999888")
    operator_services.create_profile(actor=_actor(other_owner), full_name="O2")
    g2 = services.create_group(actor=_actor(other_owner), name="G2", type=GroupType.FLEET)
    services.add_member(
        actor=_actor(other_owner), group=g2, operator=shared, role=GroupMemberRole.DRIVER
    )
    # re-activating the old membership now clashes
    with pytest.raises(ConflictError):
        services.update_member(
            actor=_actor(user),
            group=group,
            membership=m,
            status=GroupMembershipStatus.ACTIVE,
        )


def test_group_base_association_and_end(user: Any, group: Any) -> None:
    base = OperatingBase.objects.create(name="Yard", type="YARD")
    m = operator_services.associate_group(actor=_actor(user), base=base, group=group, role="owner")
    assert m.status == "ACTIVE"
    # duplicate association conflicts
    with pytest.raises(ConflictError):
        operator_services.associate_group(actor=_actor(user), base=base, group=group)
    operator_services.end_association(actor=_actor(user), membership=m)
    m.refresh_from_db()
    assert m.status == "INACTIVE"
    # can re-associate after ending
    m2 = operator_services.associate_group(actor=_actor(user), base=base, group=group)
    assert m2.pk == m.pk and m2.status == "ACTIVE"
