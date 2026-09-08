# Fikisha backend — Phase 2A foundation image.
# Python 3.12 (LTS-friendly for Django 5.2). See docs/phase-2/phase-2a-decisions.md ADR-2A-01.
FROM python:3.12-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1 \
    DJANGO_SETTINGS_MODULE=config.settings.dev

WORKDIR /app

# System deps: libpq for psycopg[binary] is bundled, but keep curl for healthchecks.
RUN apt-get update \
    && apt-get install -y --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/*

# ─── dependencies (cached layer) ──────────────────────────────────────
COPY requirements/ requirements/
ARG REQUIREMENTS=requirements/dev.txt
RUN pip install -r ${REQUIREMENTS}

# ─── application ─────────────────────────────────────────────────────
COPY . .

# Non-root runtime user.
RUN addgroup --system app && adduser --system --ingroup app app \
    && mkdir -p /app/private_media /app/staticfiles /app/logs \
    && chown -R app:app /app
USER app

EXPOSE 8000
ENTRYPOINT ["/app/scripts/entrypoint.sh"]
CMD ["api"]
