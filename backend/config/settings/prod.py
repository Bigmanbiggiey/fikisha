"""Production settings.

Phase 2A ships the *shape* of production configuration. It is not exercised in
2A (no deployment target). Anything that would weaken security is forced to a
safe value here regardless of the environment.
"""

from __future__ import annotations

from config import env
from config.settings.base import *  # noqa: F403
from config.settings.base import AUTH_CONFIG

DEBUG = False

# Fail loud if the real secret is missing.
SECRET_KEY = env.str_("DJANGO_SECRET_KEY", required=True)
ALLOWED_HOSTS = env.list_("DJANGO_ALLOWED_HOSTS", required=False)
if not ALLOWED_HOSTS:  # pragma: no cover - config guard
    raise env.ImproperlyConfigured("DJANGO_ALLOWED_HOSTS must be set in production")

# ─── Hard security floor — not overridable by env ────────────────────
AUTH_CONFIG["OTP_DEV_EXPOSE"] = False
AUTH_CONFIG["OTP_DEV_FIXED_CODE"] = ""
AUTH_CONFIG["COOKIE_SECURE"] = True
AUTH_CONFIG["COOKIE_SAMESITE"] = "Strict"
FIKISHA_ALLOW_DEMO_ENDPOINTS = False

SECURE_SSL_REDIRECT = True
SECURE_HSTS_SECONDS = 60 * 60 * 24 * 365
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")

SPECTACULAR_SETTINGS["SERVE_INCLUDE_SCHEMA"] = False  # noqa: F405

# Error tracking (wired, off unless a DSN is provided).
_SENTRY_DSN = env.str_("SENTRY_DSN", "")
if _SENTRY_DSN:  # pragma: no cover - not exercised in 2A
    import sentry_sdk

    sentry_sdk.init(dsn=_SENTRY_DSN, traces_sample_rate=0.0, send_default_pii=False)
