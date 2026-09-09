"""Operator services — mutation paths not covered by the API happy-path tests."""

from __future__ import annotations

from typing import Any

import pytest

from fikisha.common.exceptions import AuthorizationError, ConflictError, DomainError
from fikisha.identity.authz.actors import actor_from_user
from fikisha.operators import services

pytestmark = pytest.mark.django_db


def _actor(u: Any) -> Any:
    return actor_from_user(u)


@pytest.fixture
def profile(user: Any) -> Any:
    return services.create_profile(actor=_actor(user), full_name="Op One", phones=["0700 111 222"])


def test_phones_are_trimmed_on_create(profile: Any) -> None:
    assert profile.phones == ["0700 111 222"]


def test_second_profile_conflicts(user: Any, profile: Any) -> None:
    with pytest.raises(ConflictError):
        services.create_profile(actor=_actor(user), full_name="Op Two")


def test_update_profile_fields_and_noop(user: Any, profile: Any) -> None:
    updated = services.update_profile(
        actor=_actor(user),
        profile=profile,
        patch={"display_name": "Op Transporters", "phones": ["0722", ""]},
    )
    assert updated.display_name == "Op Transporters"
    assert updated.phones == ["0722"]
    same = services.update_profile(actor=_actor(user), profile=profile, patch={})
    assert same.pk == profile.pk


def test_non_admin_cannot_set_status(user: Any, profile: Any) -> None:
    with pytest.raises(AuthorizationError):
        services.update_profile(actor=_actor(user), profile=profile, patch={"status": "ACTIVE"})


def test_admin_sets_status(user: Any, platform_admin: Any, profile: Any) -> None:
    updated = services.update_profile(
        actor=_actor(platform_admin),
        profile=profile,
        patch={"status": "SUSPENDED"},
        is_platform_admin=True,
    )
    assert updated.status == "SUSPENDED"


def test_bad_status_rejected(user: Any, platform_admin: Any, profile: Any) -> None:
    with pytest.raises(DomainError):
        services.update_profile(
            actor=_actor(platform_admin),
            profile=profile,
            patch={"status": "VANISHED"},
            is_platform_admin=True,
        )


def test_create_and_update_base(user: Any, profile: Any) -> None:
    base = services.create_base(
        actor=_actor(user), data={"name": "Stage A", "type": "STAGE", "landmark": "By the church"}
    )
    updated = services.update_base(
        actor=_actor(user),
        base=base,
        data={"name": "Stage Alpha", "type": "BASE", "lat": "-1.4700"},
    )
    assert updated.name == "Stage Alpha"
    assert updated.type == "BASE"
    updated.refresh_from_db()
    assert float(updated.lat) == pytest.approx(-1.47)
    # a no-op update
    same = services.update_base(actor=_actor(user), base=base, data={})
    assert same.pk == base.pk


def test_bad_base_type_rejected(user: Any, profile: Any) -> None:
    with pytest.raises(DomainError):
        services.create_base(actor=_actor(user), data={"name": "X", "type": "PLANET"})


def test_operator_base_reassociate_after_inactive(user: Any, profile: Any) -> None:
    base = services.create_base(actor=_actor(user), data={"name": "B", "type": "BASE"})
    m = services.associate_operator(actor=_actor(user), base=base, operator=profile)
    services.end_association(actor=_actor(user), membership=m)
    m2 = services.associate_operator(actor=_actor(user), base=base, operator=profile, role="member")
    assert m2.pk == m.pk and m2.status == "ACTIVE"
