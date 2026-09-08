"""Test settings — fast, hermetic, no external services required.

Uses a locmem cache and the Celery eager executor so the outbox/worker path can
be exercised without Redis. Postgres is still required (the audit hash chain and
``select_for_update(skip_locked=True)`` semantics are Postgres-specific and must
be tested against the real engine).
"""

from __future__ import annotations

from config.settings.base import *  # noqa: F403
from config.settings.base import AUTH_CONFIG

DEBUG = False
SECRET_KEY = "test-only-secret-not-used-anywhere-real"  # noqa: S105
ALLOWED_HOSTS = ["testserver", "localhost"]
FIKISHA_ALLOW_DEMO_ENDPOINTS = True  # exercise the atomicity-demo endpoint in tests

# In-memory cache — rate-limit + OTP-attempt tests control it directly.
CACHES = {"default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"}}

# Run Celery tasks inline; no broker.
CELERY_TASK_ALWAYS_EAGER = True
CELERY_TASK_EAGER_PROPAGATES = True
CELERY_BROKER_URL = "memory://"
CELERY_RESULT_BACKEND = "cache+memory://"

# Deterministic auth for tests.
AUTH_CONFIG["OTP_DEV_EXPOSE"] = True
AUTH_CONFIG["OTP_DEV_FIXED_CODE"] = "000000"
AUTH_CONFIG["OTP_TTL_SECONDS"] = 300

PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]  # fast tests only

LOGGING["root"]["level"] = "WARNING"  # noqa: F405
