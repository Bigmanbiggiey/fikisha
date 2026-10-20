"""Operator tier API and its authorization (IDOR / BOLA)."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

import pytest

from fikisha.trust import services

pytestmark = pytest.mark.django_db

REASON = "Reviewed their record with the stage chair."


@pytest.fixture
def driver(make_verified_operator: Callable) -> Any:
    return make_verified_operator("+254711600001", "A. Dereva")


@pytest.fixture
def other_driver(make_verified_operator: Callable) -> Any:
    return make_verified_operator("+254711600002", "B. Dereva")


def test_an_operator_reads_their_own_tier(driver: Any, client_for: Callable) -> None:
    res = client_for(driver.user).get("/api/v1/operators/me/tier")
    assert res.status_code == 200
    body = res.json()
    assert body["level"] == "L1"
    assert body["next_level"] == "L2"
    assert body["criteria"]
    res = client_for(driver.user).get(f"/api/v1/operators/{driver.id}/tier")
    assert res.status_code == 200


def test_another_operator_cannot_read_a_tier(
    driver: Any, other_driver: Any, client_for: Callable, user: Any
) -> None:
    assert (
        client_for(other_driver.user).get(f"/api/v1/operators/{driver.id}/tier").status_code == 403
    )
    assert client_for(user).get(f"/api/v1/operators/{driver.id}/tier").status_code == 403
    assert client_for(user).get("/api/v1/operators/me/tier").status_code == 404


def test_ops_reads_with_staff_detail_but_cannot_change(
    driver: Any, client_for: Callable, ops_officer: Any, stepped_admin: Any
) -> None:
    services.set_level(actor=stepped_admin, operator_id=driver.id, level="L2", reason=REASON)
    ops = client_for(ops_officer)
    res = ops.get(f"/api/v1/operators/{driver.id}/tier")
    assert res.status_code == 200
    assert "by" in res.json()["history"][0]
    assert ops.get("/api/v1/admin/tier-proposals").status_code == 200
    res = ops.post(
        f"/api/v1/admin/operators/{driver.id}/tier",
        {"level": "L3", "reason": REASON},
        format="json",
    )
    assert res.status_code == 403
    assert services.stored_level(driver.id) == "L2"


def test_an_operator_cannot_promote_themselves(driver: Any, client_for: Callable) -> None:
    res = client_for(driver.user).post(
        f"/api/v1/admin/operators/{driver.id}/tier",
        {"level": "L3", "reason": REASON},
        format="json",
    )
    assert res.status_code == 403
    assert client_for(driver.user).get("/api/v1/admin/tier-proposals").status_code == 403


def test_the_platform_admin_promotes_and_demotes(driver: Any, admin_client: Any) -> None:
    res = admin_client.post(
        f"/api/v1/admin/operators/{driver.id}/tier",
        {"level": "L2", "reason": REASON},
        format="json",
    )
    assert res.status_code == 200, res.content
    assert res.json()["level"] == "L2"
    assert res.json()["bands"] == ["STANDARD", "ELEVATED"]
    res = admin_client.post(
        f"/api/v1/admin/operators/{driver.id}/tier",
        {"level": "RESTRICTED", "reason": REASON},
        format="json",
    )
    assert res.json()["level"] == "RESTRICTED"
    bad = admin_client.post(
        f"/api/v1/admin/operators/{driver.id}/tier",
        {"level": "L0", "reason": REASON},
        format="json",
    )
    assert bad.status_code == 400


def test_the_platform_admin_decides_a_proposal(
    driver: Any, give_jobs: Callable, admin_client: Any
) -> None:
    give_jobs(driver, 8, days_ago=20)
    proposal = services.evaluate(driver)
    assert proposal is not None
    queue = admin_client.get("/api/v1/admin/tier-proposals").json()["data"]
    assert [p["id"] for p in queue] == [str(proposal.id)]
    assert queue[0]["operator_name"] == "A. Dereva"
    res = admin_client.post(
        f"/api/v1/admin/tier-proposals/{proposal.id}/decision",
        {"decision": "CONFIRM", "reason": REASON},
        format="json",
    )
    assert res.status_code == 200, res.content
    assert res.json()["level"] == "L2"
    again = admin_client.post(
        f"/api/v1/admin/tier-proposals/{proposal.id}/decision",
        {"decision": "REJECT", "reason": REASON},
        format="json",
    )
    assert again.status_code == 409
    assert again.json()["code"] == "tier_proposal_not_open"
