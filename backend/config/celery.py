"""Celery application wiring."""

from __future__ import annotations

import os
from typing import Any

from celery import Celery

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.dev")

app = Celery("fikisha")
app.config_from_object("django.conf:settings", namespace="CELERY")
app.autodiscover_tasks()


@app.task(bind=True, name="fikisha.debug.ping")
def debug_ping(self: Any) -> str:  # pragma: no cover - trivial connectivity probe
    """A trivial task used by the smoke test to prove worker connectivity."""
    return "pong"
