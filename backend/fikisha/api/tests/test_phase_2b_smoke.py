"""Phase 2B required end-to-end smoke flow (brief §43).

User -> authenticate -> create Business -> become owner -> add staff ->
staff authenticates -> staff has scoped access but not admin-only actions ->
create Operator profile -> create Operator Group -> add group member ->
member has scoped access but not group-admin actions -> create Operating
Location -> associate context -> every important mutation is audited.
Plus: Business A user X Business B data; Group A member X Group B data.
"""

from __future__ import annotations

from typing import Any

import pytest

from fikisha.audit.models import AuditLogEntry

pytestmark = pytest.mark.django_db

_AUDITED_ACTIONS = {
    "business.created",
    "business.member.added",
    "business.location.added",
    "operator.created",
    "group.created",
    "group.member.added",
    "operating_location.created",
    "operating_location.operator_associated",
}


def test_phase_2b_smoke(make_user: Any, client_for: Any) -> None:
    owner_user = make_user("+254700100001")
    staff_user = make_user("+254700100002")
    driver_user = make_user("+254700100003")

    owner = client_for(owner_user)

    # ── Business ──────────────────────────────────────────────────────
    biz = owner.post(
        "/api/v1/businesses",
        {"trading_name": "Kitengela Hardware", "contact_phone": "+254700100001"},
        format="json",
    )
    assert biz.status_code == 201, biz.content
    business_id = biz.data["id"]
    assert biz.data["my_role"] == "OWNER"

    add_staff = owner.post(
        f"/api/v1/businesses/{business_id}/members",
        {"phone": staff_user.phone, "role": "DISPATCHER"},
        format="json",
    )
    assert add_staff.status_code == 201

    staff = client_for(staff_user)
    assert staff.get(f"/api/v1/businesses/{business_id}").status_code == 200
    # staff CANNOT do owner-only member administration
    assert (
        staff.post(
            f"/api/v1/businesses/{business_id}/members",
            {"phone": "+254700199999", "role": "VIEWER"},
            format="json",
        ).status_code
        == 403
    )
    # staff (DISPATCHER) CAN manage locations
    loc = staff.post(
        f"/api/v1/businesses/{business_id}/locations",
        {"label": "Yard", "type": "MAIN", "zone_code": "KITENGELA"},
        format="json",
    )
    assert loc.status_code == 201

    # ── Operator + Group ─────────────────────────────────────────────
    op_owner = owner.post("/api/v1/operators", {"full_name": "Peter Owner"}, format="json")
    assert op_owner.status_code == 201

    grp = owner.post("/api/v1/groups", {"name": "Kitengela Movers", "type": "SACCO"}, format="json")
    assert grp.status_code == 201
    group_id = grp.data["id"]
    assert grp.data["my_role"] == "OWNER"

    driver = client_for(driver_user)
    driver_pid = driver.post("/api/v1/operators", {"full_name": "Dan Driver"}, format="json").data[
        "id"
    ]

    add_member = owner.post(
        f"/api/v1/groups/{group_id}/members",
        {"operator_id": driver_pid, "role": "DRIVER"},
        format="json",
    )
    assert add_member.status_code == 201

    assert driver.get(f"/api/v1/groups/{group_id}").status_code == 200
    assert (
        driver.post(
            f"/api/v1/groups/{group_id}/members",
            {"operator_id": driver_pid, "role": "MANAGER"},
            format="json",
        ).status_code
        == 403
    )

    # ── Operating location + association ─────────────────────────────
    base = owner.post(
        "/api/v1/operating-locations",
        {"name": "Kitengela Main Stage", "type": "STAGE", "zone_code": "KITENGELA"},
        format="json",
    )
    assert base.status_code == 201
    base_id = base.data["id"]
    op_owner_pid = op_owner.data["id"]
    assoc = owner.post(
        f"/api/v1/operators/{op_owner_pid}/bases", {"base_id": base_id}, format="json"
    )
    assert assoc.status_code == 201

    # ── Every important mutation produced an audit record ────────────
    seen = set(AuditLogEntry.objects.values_list("action", flat=True))
    missing = _AUDITED_ACTIONS - seen
    assert not missing, f"missing audit records: {sorted(missing)}"

    # ── Cross-organisation isolation ────────────────────────────────
    other = client_for(make_user("+254700100009"))
    other_biz = other.post("/api/v1/businesses", {"trading_name": "Rival Ltd"}, format="json").data[
        "id"
    ]
    other.post("/api/v1/operators", {"full_name": "Rival Op"}, format="json")
    other_group = other.post(
        "/api/v1/groups", {"name": "Rival SACCO", "type": "FLEET"}, format="json"
    ).data["id"]

    assert owner.get(f"/api/v1/businesses/{other_biz}").status_code == 403
    assert other.get(f"/api/v1/businesses/{business_id}").status_code == 403
    assert owner.get(f"/api/v1/groups/{other_group}").status_code == 403
    assert other.get(f"/api/v1/groups/{group_id}").status_code == 403
