"""Fixtures for the Messages inbox tests (Design Phase 7 10g). Re-exports the
negotiation fixtures (a verified business, a REQUESTED job with a posted
price, two operators); see incidents/tests/conftest.py for the pattern."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

import pytest

from fikisha.negotiation.tests.conftest import (  # noqa: F401 - re-exported fixtures
    _actor,
    business_owner,
    make_operator,
    operator_a,
    operator_b,
    owner_actor,
    requested_job,
    verified_business,
)


@pytest.fixture
def offers(
    requested_job: Any,  # noqa: F811
    operator_a: Any,  # noqa: F811
    operator_b: Any,  # noqa: F811
    _actor: Callable,  # noqa: F811
) -> dict[str, Any]:
    """Both operators have made an offer on the job: one thread each."""
    from fikisha.negotiation import services

    a = services.propose(
        actor=_actor(operator_a.user),
        job_id=requested_job.id,
        operator_id=operator_a.id,
        amount_kes=240_000,
    )
    b = services.propose(
        actor=_actor(operator_b.user),
        job_id=requested_job.id,
        operator_id=operator_b.id,
        amount_kes=260_000,
    )
    return {"a": a["thread_id"], "b": b["thread_id"]}


@pytest.fixture
def stranger_business(make_user: Callable, _actor: Callable) -> Any:  # noqa: F811
    """Another business owner, with no relation to ``requested_job``."""
    from fikisha.business.services import create_business

    owner = make_user("+254720000099")
    create_business(actor=_actor(owner), trading_name="Other Co")
    return owner
