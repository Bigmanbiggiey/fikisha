"""Business services — the mutation paths not covered by the API happy-path tests."""

from __future__ import annotations

from typing import Any

import pytest

from fikisha.business import services
from fikisha.business.models import BusinessRole, MembershipStatus
from fikisha.common.exceptions import ConflictError, DomainError
from fikisha.identity.authz.actors import actor_from_user

pytestmark = pytest.mark.django_db


@pytest.fixture
def business(user: Any) -> Any:
    return services.create_business(actor=actor_from_user(user), trading_name="Svc Co")


def _actor(u: Any) -> Any:
    return actor_from_user(u)


class TestMembershipService:
    def test_promote_member_to_owner_then_demote_first_owner(
        self, user: Any, other_user: Any, business: Any
    ) -> None:
        m2 = services.add_member(
            actor=_actor(user), business=business, phone=other_user.phone, role=BusinessRole.VIEWER
        )
        # promote #2 to OWNER
        services.update_membership(
            actor=_actor(user), business=business, membership=m2, role=BusinessRole.OWNER
        )
        # now the original owner can be demoted (a second owner exists)
        m1 = business.memberships.get(user=user)
        services.update_membership(
            actor=_actor(user), business=business, membership=m1, role=BusinessRole.VIEWER
        )
        assert business.memberships.get(user=user).role == BusinessRole.VIEWER

    def test_demoting_the_only_owner_is_rejected(self, user: Any, business: Any) -> None:
        m1 = business.memberships.get(user=user)
        with pytest.raises(ConflictError):
            services.update_membership(
                actor=_actor(user),
                business=business,
                membership=m1,
                role=BusinessRole.DISPATCHER,
            )

    def test_reactivate_a_removed_member(self, user: Any, other_user: Any, business: Any) -> None:
        m = services.add_member(
            actor=_actor(user), business=business, phone=other_user.phone, role=BusinessRole.VIEWER
        )
        services.remove_member(actor=_actor(user), business=business, membership=m)
        assert business.memberships.get(pk=m.pk).status == MembershipStatus.REMOVED
        again = services.add_member(
            actor=_actor(user),
            business=business,
            phone=other_user.phone,
            role=BusinessRole.DISPATCHER,
        )
        assert again.pk == m.pk
        assert again.status == MembershipStatus.ACTIVE
        assert again.role == BusinessRole.DISPATCHER

    def test_add_existing_active_member_conflicts(
        self, user: Any, other_user: Any, business: Any
    ) -> None:
        services.add_member(
            actor=_actor(user), business=business, phone=other_user.phone, role=BusinessRole.VIEWER
        )
        with pytest.raises(ConflictError):
            services.add_member(
                actor=_actor(user),
                business=business,
                phone=other_user.phone,
                role=BusinessRole.VIEWER,
            )

    def test_unknown_role_rejected(self, user: Any, other_user: Any, business: Any) -> None:
        with pytest.raises(DomainError):
            services.add_member(
                actor=_actor(user), business=business, phone=other_user.phone, role="BOSS"
            )


class TestLocationService:
    def test_update_location_fields_and_promote_to_main(self, user: Any, business: Any) -> None:
        loc = services.create_location(
            actor=_actor(user),
            business=business,
            data={"label": "Store", "type": "STORE"},
        )
        updated = services.update_location(
            actor=_actor(user),
            business=business,
            location=loc,
            data={"label": "Main Store", "type": "MAIN", "address_text": "Namanga Rd"},
        )
        assert updated.label == "Main Store"
        assert updated.type == "MAIN"
        assert updated.address_text == "Namanga Rd"

    def test_update_noop_returns_unchanged(self, user: Any, business: Any) -> None:
        loc = services.create_location(
            actor=_actor(user), business=business, data={"label": "X", "type": "BRANCH"}
        )
        same = services.update_location(
            actor=_actor(user), business=business, location=loc, data={}
        )
        assert same.pk == loc.pk

    def test_deactivate_is_idempotent(self, user: Any, business: Any) -> None:
        loc = services.create_location(
            actor=_actor(user), business=business, data={"label": "X", "type": "BRANCH"}
        )
        services.deactivate_location(actor=_actor(user), business=business, location=loc)
        services.deactivate_location(
            actor=_actor(user), business=business, location=loc
        )  # no error

    def test_bad_location_type_rejected(self, user: Any, business: Any) -> None:
        with pytest.raises(DomainError):
            services.create_location(
                actor=_actor(user), business=business, data={"label": "X", "type": "ROOFTOP"}
            )
