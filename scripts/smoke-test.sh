#!/usr/bin/env bash
# Fikisha Phase 2A end-to-end smoke test (brief §40).
#
# Proves the whole foundation path with the stack from docker-compose:
#   Postgres + Redis + backend + worker + beat + frontend  →
#   PWA served → API health → auth foundation (OTP request/verify) →
#   authenticated request → authorization enforced (403) → DB write +
#   audit row + outbox row in one transaction → Celery worker drains it →
#   frontend shows the authenticated state.
#
# Usage:
#   cp .env.example .env
#   ./scripts/smoke-test.sh
#
# Requires: docker compose, curl, python3 (for JSON parsing), the stack built.
set -euo pipefail

API="http://localhost:8000"
WEB="http://localhost:5173"
ADMIN_PHONE="+254700000009"
USER_PHONE="+254700000123"

say()  { printf '\n\033[1;36m== %s\033[0m\n' "$*"; }
ok()   { printf '   \033[1;32mOK\033[0m  %s\n' "$*"; }
fail() { printf '   \033[1;31mFAIL\033[0m %s\n' "$*"; exit 1; }
json() { python3 -c "import sys,json; d=json.load(sys.stdin); print(d$1)"; }

say "1. Bring the stack up"
docker compose up -d --build
docker compose ps

say "2. Wait for the backend to become healthy"
for i in $(seq 1 60); do
  if curl -fsS "$API/healthz" >/dev/null 2>&1; then ok "backend /healthz is up"; break; fi
  sleep 2
  [ "$i" = 60 ] && fail "backend did not become healthy"
done
curl -fsS "$API/readyz" | json "['checks']" | grep -q "True" && ok "/readyz: database + cache reachable"

say "3. PWA is served"
curl -fsS "$WEB" | grep -qi "<div id=\"root\">" && ok "frontend HTML served at $WEB"

say "4. API health via the versioned API"
curl -fsS "$API/api/v1/health/" | json "['status']" | grep -q "ok" && ok "/api/v1/health/ ok"

say "5. Auth foundation — request a one-time code"
REQ=$(curl -fsS -X POST "$API/api/v1/auth/otp/request" \
  -H 'Content-Type: application/json' -d "{\"phone\":\"$USER_PHONE\"}")
CHALLENGE=$(echo "$REQ" | json "['challenge_id']")
CODE=$(echo "$REQ" | json "['dev_code']")
[ -n "$CHALLENGE" ] && [ -n "$CODE" ] && ok "challenge $CHALLENGE issued, dev_code present"

say "6. Auth foundation — verify the code, receive an access token"
VERIFY=$(curl -fsS -X POST "$API/api/v1/auth/otp/verify" \
  -H 'Content-Type: application/json' \
  -d "{\"challenge_id\":\"$CHALLENGE\",\"code\":\"$CODE\"}")
TOKEN=$(echo "$VERIFY" | json "['access_token']")
[ -n "$TOKEN" ] && ok "access token issued for $(echo "$VERIFY" | json "['user']['phone']")"

say "7. Authenticated request reaches the API"
ME=$(curl -fsS "$API/api/v1/me" -H "Authorization: Bearer $TOKEN")
echo "$ME" | json "['phone']" | grep -q "$USER_PHONE" && ok "/me returns the signed-in user"

say "8. Authorization is enforced — ordinary user hits an admin route"
CODE_403=$(curl -s -o /dev/null -w '%{http_code}' \
  "$API/api/v1/admin/ping" -H "Authorization: Bearer $TOKEN")
[ "$CODE_403" = "403" ] && ok "GET /api/v1/admin/ping -> 403 for a non-admin" \
  || fail "expected 403, got $CODE_403"

say "9. Create a platform admin and mint its token"
ADMIN_TOKEN=$(docker compose exec -T backend \
  python manage.py create_admin "$ADMIN_PHONE" --print-token \
  | grep '^ACCESS_TOKEN=' | cut -d= -f2-)
[ -n "$ADMIN_TOKEN" ] && ok "admin $ADMIN_PHONE created, token minted"

say "10. One transaction writes a DB row + an audit row + an outbox row"
DEMO=$(curl -fsS -X POST "$API/api/v1/_demo/atomic-outbox" \
  -H "Authorization: Bearer $ADMIN_TOKEN" -H 'Content-Type: application/json' \
  -d '{"note":"phase-2a smoke test"}')
OUTBOX_ID=$(echo "$DEMO" | json "['outbox_event_id']")
AUDIT_SEQ=$(echo "$DEMO" | json "['audit_seq']")
[ -n "$OUTBOX_ID" ] && ok "demo wrote audit seq=$AUDIT_SEQ + outbox id=$OUTBOX_ID in one transaction"

say "11. The Celery worker drains the outbox event"
for i in $(seq 1 20); do
  STATUS=$(docker compose exec -T backend python manage.py shell -c \
    "from fikisha.outbox.models import OutboxEvent; print(OutboxEvent.objects.get(pk=$OUTBOX_ID).status)" \
    2>/dev/null | tr -d '\r')
  [ "$STATUS" = "PUBLISHED" ] && { ok "outbox event $OUTBOX_ID -> PUBLISHED by the worker"; break; }
  sleep 2
  [ "$i" = 20 ] && fail "outbox event never reached PUBLISHED (last: $STATUS)"
done

say "12. Audit chain still verifies"
docker compose exec -T backend python manage.py shell -c \
  "from fikisha.audit.services import verify_chain; b=verify_chain(); print('BREAKS', b); assert b==[]" \
  && ok "verify_chain() reports no breaks"

printf '\n\033[1;32mSMOKE TEST PASSED\033[0m\n'
