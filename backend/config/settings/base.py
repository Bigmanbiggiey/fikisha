"""Base settings shared by every environment.

Environment-specific overrides live in ``dev.py`` / ``test.py`` / ``prod.py``.
Nothing secret is hard-coded here; secrets come from the environment.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from config import env

# ─── Paths ──────────────────────────────────────────────────────────────
BASE_DIR = Path(__file__).resolve().parent.parent.parent  # .../backend
PROJECT_ROOT = BASE_DIR.parent  # repo root

# ─── Core ───────────────────────────────────────────────────────────────
SECRET_KEY = env.str_("DJANGO_SECRET_KEY", "insecure-base-default-override-me")
DEBUG = env.bool_("DJANGO_DEBUG", False)
ALLOWED_HOSTS = env.list_("DJANGO_ALLOWED_HOSTS", ["localhost", "127.0.0.1"])
CSRF_TRUSTED_ORIGINS = env.list_("DJANGO_CSRF_TRUSTED_ORIGINS", [])
ROOT_URLCONF = "config.urls"
WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
AUTH_USER_MODEL = "identity.User"

# ─── Applications ───────────────────────────────────────────────────────
DJANGO_APPS = [
    "django.contrib.contenttypes",
    "django.contrib.auth",
    "django.contrib.staticfiles",
    "django.contrib.messages",
    "django.contrib.admin",
    "django.contrib.sessions",
    "django.contrib.postgres",  # ArrayField lookups/validators (operators.OperatorProfile.phones)
]
THIRD_PARTY_APPS = [
    "rest_framework",
    "corsheaders",
    "drf_spectacular",
]
# Fikisha bounded modules.
#   Phase 2A foundation: common, audit, outbox, platform_config, identity, storage.
#   Phase 2B identity/organisation domain: business, operators, groups.
# (Jobs / Negotiation / Vehicles / Verification / Trust / etc. are NOT created yet.)
LOCAL_APPS = [
    "fikisha.common",
    "fikisha.audit",
    "fikisha.outbox",
    "fikisha.platform_config",
    "fikisha.identity",
    "fikisha.storage",
    "fikisha.business",
    "fikisha.operators",
    "fikisha.groups",
]
INSTALLED_APPS = DJANGO_APPS + THIRD_PARTY_APPS + LOCAL_APPS

# ─── Middleware ─────────────────────────────────────────────────────────
MIDDLEWARE = [
    "fikisha.common.request_id.RequestIDMiddleware",  # earliest: bind request id
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.locale.LocaleMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

# ─── Database ───────────────────────────────────────────────────────────
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": env.str_("POSTGRES_DB", "fikisha"),
        "USER": env.str_("POSTGRES_USER", "fikisha"),
        "PASSWORD": env.str_("POSTGRES_PASSWORD", "fikisha"),
        "HOST": env.str_("POSTGRES_HOST", "localhost"),
        "PORT": env.str_("POSTGRES_PORT", "5432"),
        "CONN_MAX_AGE": env.int_("DB_CONN_MAX_AGE", 60),
        "OPTIONS": {"connect_timeout": 10},
    }
}

# ─── Cache / Redis ─────────────────────────────────────────────────────
REDIS_URL = env.str_("REDIS_URL", "redis://localhost:6379/0")
CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.redis.RedisCache",
        "LOCATION": REDIS_URL,
    }
}

# ─── Celery ────────────────────────────────────────────────────────────
CELERY_BROKER_URL = env.str_("CELERY_BROKER_URL", "redis://localhost:6379/1")
CELERY_RESULT_BACKEND = env.str_("CELERY_RESULT_BACKEND", "redis://localhost:6379/2")
CELERY_TASK_ACKS_LATE = True
CELERY_TASK_REJECT_ON_WORKER_LOST = True
CELERY_WORKER_PREFETCH_MULTIPLIER = 1
CELERY_TASK_TIME_LIMIT = 120
CELERY_TASK_SOFT_TIME_LIMIT = 90
CELERY_TASK_DEFAULT_QUEUE = "default"
CELERY_TIMEZONE = env.str_("DJANGO_TIME_ZONE", "Africa/Nairobi")
OUTBOX_POLL_SECONDS = env.int_("OUTBOX_POLL_SECONDS", 3)
CELERY_BEAT_SCHEDULE = {
    "drain-outbox": {
        "task": "fikisha.outbox.tasks.drain_outbox",
        "schedule": float(OUTBOX_POLL_SECONDS),
        "options": {"expires": OUTBOX_POLL_SECONDS},
    },
}

# ─── Password hashing (Argon2 first) ──────────────────────────────────
PASSWORD_HASHERS = [
    "django.contrib.auth.hashers.Argon2PasswordHasher",
    "django.contrib.auth.hashers.PBKDF2PasswordHasher",
]
AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
]

# ─── i18n / tz ────────────────────────────────────────────────────────
LANGUAGE_CODE = env.str_("DJANGO_LANGUAGE_CODE", "en")
TIME_ZONE = env.str_("DJANGO_TIME_ZONE", "Africa/Nairobi")
USE_I18N = True
USE_TZ = True  # store UTC; render EAT on the client (Phase 1 api-architecture §1)
LANGUAGES = [("en", "English"), ("sw", "Kiswahili")]

# ─── Static / media ──────────────────────────────────────────────────
STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {"BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage"},
}

# ─── Object storage abstraction (Fikisha, not Django's) ──────────────
# Phase 2A: a private storage abstraction with a local FS backend. See
# fikisha/storage/. Production S3 credentials are NOT wired here.
FIKISHA_STORAGE: dict[str, Any] = {
    "BACKEND": env.str_("STORAGE_BACKEND", "local"),  # "local" | "s3"
    "LOCAL_ROOT": env.str_("STORAGE_LOCAL_ROOT", str(BASE_DIR / "private_media")),
    "SIGNED_URL_TTL_SECONDS": env.int_("STORAGE_SIGNED_URL_TTL_SECONDS", 120),
    "S3": {
        "ENDPOINT_URL": env.str_("S3_ENDPOINT_URL", ""),
        "REGION": env.str_("S3_REGION", ""),
        "BUCKET": env.str_("S3_BUCKET", ""),
        "ACCESS_KEY_ID": env.str_("S3_ACCESS_KEY_ID", ""),
        "SECRET_ACCESS_KEY": env.str_("S3_SECRET_ACCESS_KEY", ""),
    },
}

# ─── REST framework ──────────────────────────────────────────────────
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "fikisha.identity.authz.authentication.BearerSessionAuthentication",
    ],
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.IsAuthenticated",
    ],
    "DEFAULT_PAGINATION_CLASS": "fikisha.common.pagination.CursorPagination",
    "PAGE_SIZE": 25,
    "EXCEPTION_HANDLER": "fikisha.common.exceptions.problem_detail_exception_handler",
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
    "DEFAULT_RENDERER_CLASSES": ["rest_framework.renderers.JSONRenderer"],
    "DEFAULT_PARSER_CLASSES": [
        "rest_framework.parsers.JSONParser",
        "rest_framework.parsers.MultiPartParser",
    ],
    "UNAUTHENTICATED_USER": None,
}

SPECTACULAR_SETTINGS = {
    "TITLE": "Fikisha API",
    "DESCRIPTION": "Fikisha — local logistics marketplace. API v1 (foundation).",
    "VERSION": "0.0.1",
    "SERVE_INCLUDE_SCHEMA": False,
    "SCHEMA_PATH_PREFIX": "/api/v1",
}

# ─── Authentication / OTP config (read by fikisha.identity) ──────────
AUTH_CONFIG: dict[str, Any] = {
    "OTP_LENGTH": env.int_("OTP_LENGTH", 6),
    "OTP_TTL_SECONDS": env.int_("OTP_TTL_SECONDS", 300),
    "OTP_MAX_ATTEMPTS": env.int_("OTP_MAX_ATTEMPTS", 5),
    "OTP_REQUEST_RATE_PER_HOUR": env.int_("OTP_REQUEST_RATE_PER_HOUR", 5),
    "OTP_REQUEST_RATE_PER_MINUTE": env.int_("OTP_REQUEST_RATE_PER_MINUTE", 1),
    # DEV/TEST ONLY — prod.py forces these to safe values.
    "OTP_DEV_EXPOSE": env.bool_("OTP_DEV_EXPOSE", False),
    "OTP_DEV_FIXED_CODE": env.str_("OTP_DEV_FIXED_CODE", ""),
    "ACCESS_TOKEN_TTL_SECONDS": env.int_("ACCESS_TOKEN_TTL_SECONDS", 900),
    "REFRESH_TOKEN_TTL_SECONDS": env.int_("REFRESH_TOKEN_TTL_SECONDS", 2592000),
    "ADMIN_SESSION_TTL_SECONDS": env.int_("ADMIN_SESSION_TTL_SECONDS", 28800),
    "REFRESH_COOKIE_NAME": env.str_("AUTH_REFRESH_COOKIE_NAME", "fikisha_refresh"),
    "COOKIE_SECURE": env.bool_("AUTH_COOKIE_SECURE", False),
    "COOKIE_SAMESITE": env.str_("AUTH_COOKIE_SAMESITE", "Lax"),
}

# ─── CORS ────────────────────────────────────────────────────────────
CORS_ALLOWED_ORIGINS = env.list_("API_CORS_ALLOWED_ORIGINS", [])
CORS_ALLOW_CREDENTIALS = True  # refresh cookie

# ─── Dev-only demo endpoints (also gated by the `demo_endpoints` feature flag) ─
# Proves the audit + outbox atomicity path. Off by default; dev/test turn it on;
# prod.py forces it off.
FIKISHA_ALLOW_DEMO_ENDPOINTS = env.bool_("FIKISHA_ALLOW_DEMO_ENDPOINTS", False)

# ─── Security headers (tightened further in prod.py) ─────────────────
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_REFERRER_POLICY = "strict-origin-when-cross-origin"
X_FRAME_OPTIONS = "DENY"
SESSION_COOKIE_HTTPONLY = True
CSRF_COOKIE_HTTPONLY = False  # the SPA reads it for the (rare) session-auth paths

# ─── Logging ─────────────────────────────────────────────────────────
LOG_LEVEL = env.str_("LOG_LEVEL", "INFO")
LOG_JSON = env.bool_("LOG_JSON", True)
# Concrete dictConfig is built in fikisha.common.logging_setup and applied here.
from fikisha.common.logging_setup import build_logging_config  # noqa: E402

LOGGING = build_logging_config(level=LOG_LEVEL, json_output=LOG_JSON)
