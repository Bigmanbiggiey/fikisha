#!/usr/bin/env sh
# Fikisha backend container entrypoint.
#   api    -> wait for db, migrate, serve (runserver in DEBUG, gunicorn otherwise)
#   worker -> celery worker
#   beat   -> celery beat (drives the outbox drain schedule)
set -eu

ROLE="${1:-api}"

wait_for_db() {
  echo "waiting for database at ${POSTGRES_HOST:-db}:${POSTGRES_PORT:-5432} ..."
  python - <<'PY'
import os, time, sys
import psycopg
dsn = (
    f"host={os.environ.get('POSTGRES_HOST','db')} "
    f"port={os.environ.get('POSTGRES_PORT','5432')} "
    f"dbname={os.environ.get('POSTGRES_DB','fikisha')} "
    f"user={os.environ.get('POSTGRES_USER','fikisha')} "
    f"password={os.environ.get('POSTGRES_PASSWORD','fikisha')}"
)
for attempt in range(60):
    try:
        with psycopg.connect(dsn, connect_timeout=3):
            print("database is up")
            sys.exit(0)
    except Exception as exc:
        print(f"  ...not yet ({exc})")
        time.sleep(2)
print("database did not become available", file=sys.stderr)
sys.exit(1)
PY
}

case "$ROLE" in
  api)
    wait_for_db
    python manage.py migrate --noinput
    python manage.py collectstatic --noinput || true
    if [ "${DJANGO_DEBUG:-false}" = "true" ]; then
      exec python manage.py runserver 0.0.0.0:8000
    else
      exec gunicorn config.wsgi:application --bind 0.0.0.0:8000 --workers "${GUNICORN_WORKERS:-3}" --access-logfile - --error-logfile -
    fi
    ;;
  worker)
    wait_for_db
    exec celery -A config worker -l "${LOG_LEVEL:-info}" -Q default
    ;;
  beat)
    wait_for_db
    exec celery -A config beat -l "${LOG_LEVEL:-info}"
    ;;
  *)
    exec "$@"
    ;;
esac
