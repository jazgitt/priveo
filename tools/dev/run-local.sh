#!/usr/bin/env bash
# Runs the Priveo API on this Mac, against the remote (Neon) database, so the
# admin portal, the Android emulator and the iOS Simulator can all talk to it.
# The macOS counterpart of portal-local.ps1.
#
#   tools/dev/run-local.sh                # API on http://127.0.0.1:8000
#   tools/dev/run-local.sh --portal       # also the admin portal on http://localhost:5173/portal/
#   tools/dev/run-local.sh --migrate      # apply pending migrations to the database first (asks)
#   tools/dev/run-local.sh --lan          # listen on the network, for a phone on the same Wi-Fi
#   tools/dev/run-local.sh --pull         # pull the dev env from Vercel into services/api/.env.neon first
#   tools/dev/run-local.sh --port 8001
#
# Then run the app against it (in another terminal):
#   apps/mobile/tool/build_priveo.sh android --local     # emulator reaches this Mac as 10.0.2.2
#   apps/mobile/tool/build_priveo.sh ios --local         # simulator uses localhost
#
# Settings come from services/api/.env, then services/api/.env.neon (pulled
# from Vercel) on top. DATABASE_URL and TOKEN_SECRET must be set in one of them.
#
# The database is the REAL shared dev database: what you save here is saved
# there. Nothing else leaves this Mac: email, push and cloud storage are
# switched off, and media goes to a folder on disk.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
API="$ROOT/services/api"
WEB="$ROOT/apps/web"
PORT=8000
HOST=127.0.0.1
PORTAL=false
MIGRATE=false
PULL=false

usage() { sed -n '2,23p' "${BASH_SOURCE[0]}" | sed 's/^# \{0,1\}//'; exit "${1:-2}"; }
while [ $# -gt 0 ]; do
  case "$1" in
    --portal) PORTAL=true ;;
    --migrate) MIGRATE=true ;;
    --pull) PULL=true ;;
    --lan) HOST=0.0.0.0 ;;
    --port) PORT="${2:?--port needs a number}"; shift ;;
    -h | --help) usage 0 ;;
    *) echo "Unknown option: $1" >&2; usage ;;
  esac
  shift
done

log() { printf '[%s] %s\n' "$(date +%H:%M:%S)" "$*" >&2; }
die() { echo "error: $*" >&2; exit 1; }

PYTHON="$API/.venv/bin/python"
[ -x "$PYTHON" ] || die "no virtualenv at services/api/.venv. Create it: cd services/api && python3 -m venv .venv && .venv/bin/pip install -e '.[dev]'"

if $PULL || [ ! -f "$API/.env" -a ! -f "$API/.env.neon" ]; then
  command -v npx > /dev/null || die "npx is needed to pull from Vercel (install Node)."
  log "Pulling the dev environment from Vercel into services/api/.env.neon ..."
  (cd "$API" && npx vercel env pull .env.neon --environment production --yes > /dev/null)
fi

# Load the env files into this shell with python-dotenv (the same reader the
# API uses), so values with spaces or <> are fine. Values are never printed.
eval "$("$PYTHON" -I - "$API/.env" "$API/.env.neon" << 'PY'
import shlex, sys
from dotenv import dotenv_values
for path in sys.argv[1:]:
    for key, value in dotenv_values(path).items():
        if value is not None:
            print(f"export {key}={shlex.quote(value)}")
PY
)"

[ -n "${DATABASE_URL:-}" ] || die "DATABASE_URL is empty. Put it in services/api/.env, or run with --pull."
[ -n "${TOKEN_SECRET:-}" ] || die "TOKEN_SECRET is empty. Put a 32+ character value in services/api/.env, or run with --pull."

# Plain http on this Mac, and nothing that reaches real people.
export ENVIRONMENT=dev
export PUBLIC_BASE_URL="http://localhost:5173"
export RESEND_API_KEY=""
export EMAIL_REDIRECT_TO=""
export FCM_ENABLED=false
export MEDIA_STORE=local
export BLOB_READ_WRITE_TOKEN=""
export AWS_ACCESS_KEY_ID="" AWS_SECRET_ACCESS_KEY="" S3_BUCKET=""

DB_HOST="$(printf '%s' "$DATABASE_URL" | sed -E 's#^[a-z+]+://([^@/]*@)?([^/:?]+).*#\2#')"
log "Database host: $DB_HOST (shared; saves here are real dev data)"
log "Email, push and S3 are off. Verification codes appear in the API log."

cd "$API"
CURRENT="$("$PYTHON" -m alembic current 2> /dev/null | grep -Eo '^[0-9]+' | head -n1 || true)"
HEAD="$("$PYTHON" -m alembic heads 2> /dev/null | grep -Eo '^[0-9]+' | head -n1 || true)"
log "Migrations: database at ${CURRENT:-unknown}, code at ${HEAD:-unknown}"
if [ -n "$CURRENT" ] && [ "$CURRENT" != "$HEAD" ]; then
  if $MIGRATE; then
    read -r -p "Apply migrations $CURRENT -> $HEAD to the shared database at $DB_HOST? [y/N] " yn
    [ "$yn" = y ] || [ "$yn" = Y ] || die "not applied."
    "$PYTHON" -m alembic upgrade head
  else
    log "The database is behind the code. New features that need the new tables will fail"
    log "until you run:  tools/dev/run-local.sh --migrate"
  fi
fi

PIDS=()
cleanup() { for p in "${PIDS[@]:-}"; do [ -n "$p" ] && kill "$p" 2> /dev/null || true; done; }
trap cleanup EXIT INT TERM

if $PORTAL; then
  [ -d "$WEB/node_modules" ] || (cd "$WEB" && npm install)
  log "Portal: http://localhost:5173/portal/  (proxies /v1 to the API)"
  (cd "$WEB" && VITE_API_TARGET="http://127.0.0.1:$PORT" exec npm run dev) &
  PIDS+=($!)
fi

log "API: http://$HOST:$PORT   emulator: http://10.0.2.2:$PORT   simulator: http://localhost:$PORT"
if [ "$HOST" = 0.0.0.0 ]; then
  log "On the network: http://$(ipconfig getifaddr en0 2> /dev/null || echo '<this-mac-ip>'):$PORT"
fi
"$PYTHON" -m uvicorn app.main:app --reload --host "$HOST" --port "$PORT"
