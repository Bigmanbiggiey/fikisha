"""The allowed-transition table is *data* — these tests pin it against
job-state-machine.md §3 and prove the DB seed is the same single source."""

from __future__ import annotations

import pytest

from fikisha.jobs.constants import TERMINAL_STATES, JobStatus
from fikisha.jobs.transitions import ALLOWED_PAIRS, ALLOWED_TRANSITIONS, rule_for

# Exactly the rows in job-state-machine.md §3.1-3.4 (RESUME excluded — ADR-2D-07).
EXPECTED_PAIRS = {
    ("DRAFT", "REQUESTED"),
    ("DRAFT", "CANCELLED"),
    ("REQUESTED", "NEGOTIATING"),
    ("REQUESTED", "CONFIRMED"),
    ("REQUESTED", "CANCELLED"),
    ("REQUESTED", "FAILED"),
    ("NEGOTIATING", "NEGOTIATING"),
    ("NEGOTIATING", "CONFIRMED"),
    ("NEGOTIATING", "CANCELLED"),
    ("NEGOTIATING", "FAILED"),
    ("CONFIRMED", "ASSIGNED"),
    ("CONFIRMED", "CANCELLED"),
    ("ASSIGNED", "AT_PICKUP"),
    ("ASSIGNED", "CANCELLED"),
    ("ASSIGNED", "FAILED"),
    ("ASSIGNED", "DISPUTED"),
    ("AT_PICKUP", "PICKED_UP"),
    ("AT_PICKUP", "CANCELLED"),
    ("AT_PICKUP", "FAILED"),
    ("AT_PICKUP", "DISPUTED"),
    ("PICKED_UP", "IN_TRANSIT"),
    ("PICKED_UP", "DISPUTED"),
    ("PICKED_UP", "FAILED"),
    ("IN_TRANSIT", "AT_DESTINATION"),
    ("IN_TRANSIT", "DISPUTED"),
    ("IN_TRANSIT", "FAILED"),
    ("AT_DESTINATION", "DELIVERED"),
    ("AT_DESTINATION", "DISPUTED"),
    ("AT_DESTINATION", "FAILED"),
    ("DELIVERED", "COMPLETED"),
    ("DELIVERED", "DISPUTED"),
    ("COMPLETED", "DISPUTED"),
    ("DISPUTED", "COMPLETED"),
    ("DISPUTED", "FAILED"),
    ("DISPUTED", "CANCELLED"),
}


def test_table_matches_state_machine_doc() -> None:
    assert set(ALLOWED_PAIRS) == EXPECTED_PAIRS


def test_resume_path_is_absent() -> None:
    # DISPUTED → <pre_dispute_status> (RESUME) is OPEN — not implemented in 2D.
    for _from, to in ALLOWED_PAIRS:
        if _from == "DISPUTED":
            assert to in TERMINAL_STATES


def test_no_transition_out_of_terminal_states_except_post_completion_dispute() -> None:
    # job-state-machine.md §1 + mermaid: the only edge leaving a terminal state
    # is COMPLETED → DISPUTED (post-completion dispute window, D-JOB-5).
    leaving_terminal = {p for p in ALLOWED_PAIRS if p[0] in TERMINAL_STATES}
    assert leaving_terminal == {("COMPLETED", "DISPUTED")}


def test_every_rule_has_a_registered_apply_and_guards() -> None:
    from fikisha.jobs.apply_fns import APPLY
    from fikisha.jobs.guards import GUARDS

    for (frm, to), rule in ALLOWED_TRANSITIONS.items():
        assert rule.apply in APPLY, f"{frm}->{to}: apply {rule.apply!r} not registered"
        for g in rule.guards:
            assert g in GUARDS, f"{frm}->{to}: guard {g!r} not registered"
        assert rule.initiators, f"{frm}->{to}: no initiators"


@pytest.mark.parametrize("frm", JobStatus.values)
@pytest.mark.parametrize("to", JobStatus.values)
def test_cross_product_lookup(frm: str, to: str) -> None:
    rule = rule_for(frm, to)
    if (frm, to) in EXPECTED_PAIRS:
        assert rule is not None
    else:
        assert rule is None


@pytest.mark.django_db
def test_db_seed_equals_the_python_table() -> None:
    from fikisha.jobs.models import AllowedJobTransition

    seeded = set(AllowedJobTransition.objects.values_list("from_status", "to_status"))
    assert seeded == set(ALLOWED_PAIRS)
