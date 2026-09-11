"""The commission subsystem must never become a second Job-status writer
(Step 9 brief §16/§28) — completion still goes through exactly one path,
``JobLifecycleService.transition()``."""

from __future__ import annotations

import ast
import inspect
from collections.abc import Callable
from typing import Any

import pytest

from fikisha.jobs import commission as commission_module

pytestmark = pytest.mark.django_db


def test_commission_module_never_assigns_job_status() -> None:
    """Static check: no ``... .status = ...`` assignment targets a ``job``-named
    variable anywhere in ``jobs.commission`` — the only legitimate
    ``job.status`` writer is ``fikisha.jobs.service.transition``."""
    source = inspect.getsource(commission_module)
    tree = ast.parse(source)
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if (
                    isinstance(target, ast.Attribute)
                    and target.attr == "status"
                    and isinstance(target.value, ast.Name)
                    and target.value.id == "job"
                ):
                    pytest.fail(
                        f"jobs.commission assigns job.status directly at line {node.lineno}"
                    )


def test_commission_module_never_imports_the_transition_function() -> None:
    """``jobs.commission`` never calls ``JobLifecycleService.transition()``
    itself — it is a pure apply-fn helper, called *from inside* an already
    running transition; it has no business driving one."""
    source = inspect.getsource(commission_module)
    assert "import transition" not in source
    assert "job_transition" not in source


def test_completion_still_only_reachable_through_the_lifecycle_service(
    delivered_job: Callable, admin_actor: Any
) -> None:
    """No parallel "complete this job" entry point exists — the only way a
    test (or any caller) can reach COMPLETED is the same
    ``JobLifecycleService.transition()`` every other Step used."""
    from fikisha.jobs.constants import JobStatus
    from fikisha.jobs.service import TransitionContext
    from fikisha.jobs.service import transition as job_transition

    job = delivered_job()
    view = job_transition(
        job_id=job.id,
        to=JobStatus.COMPLETED,
        actor=admin_actor,
        context=TransitionContext(data={"initiator_tokens": []}),
    )
    assert view["status"] == JobStatus.COMPLETED


def test_a_non_admin_participant_cannot_bypass_the_transition_guard_chain(
    delivered_job: Callable, driver_actor: Any
) -> None:
    """``(DELIVERED, COMPLETED)`` initiators are
    ``BUSINESS_PARTY/RECIPIENT/SCHEDULER/ADMIN`` — the assigned driver, though
    a job participant, is not one of them; commission creation must not have
    quietly widened who can complete a job."""
    from fikisha.jobs.constants import JobStatus
    from fikisha.jobs.errors import NotAuthorisedToInitiate
    from fikisha.jobs.service import TransitionContext
    from fikisha.jobs.service import transition as job_transition

    job = delivered_job()
    with pytest.raises(NotAuthorisedToInitiate):
        job_transition(
            job_id=job.id,
            to=JobStatus.COMPLETED,
            actor=driver_actor,
            context=TransitionContext(data={"initiator_tokens": []}),
        )
