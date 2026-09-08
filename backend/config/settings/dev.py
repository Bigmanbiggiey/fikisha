"""Local development settings."""

from __future__ import annotations

from config.settings.base import *  # noqa: F403
from config.settings.base import AUTH_CONFIG, INSTALLED_APPS

DEBUG = True
INSTALLED_APPS = [*INSTALLED_APPS, "django.contrib.humanize"]
FIKISHA_ALLOW_DEMO_ENDPOINTS = True

# Dev convenience: allow the OTP code to be surfaced so a developer can log in
# without an SMS provider. NEVER true in prod (prod.py forces it off).
AUTH_CONFIG["OTP_DEV_EXPOSE"] = True

# Relaxed cookie flags for http://localhost.
AUTH_CONFIG["COOKIE_SECURE"] = False
SESSION_COOKIE_SECURE = False
CSRF_COOKIE_SECURE = False

# Show emails/SMS to the console-style logger only.
EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"
