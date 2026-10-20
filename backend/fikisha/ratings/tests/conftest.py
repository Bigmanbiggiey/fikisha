"""The jobs and incidents fixtures, plus a completed job ready to rate."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

import pytest

from fikisha.incidents.tests.conftest import *  # noqa: F403  (re-export fixtures)


@pytest.fixture
def completed_job(delivered_job: Callable, complete_job: Callable) -> Any:
    job = delivered_job()
    complete_job(job)
    job.refresh_from_db()
    return job
