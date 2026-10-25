#!/usr/bin/env bash
# Runs the same checks as the GitHub CI workflows on this machine, so a push
# does not wait 15 to 25 minutes to find out it is red.
#
#   tools/dev/check-local.sh                 # api, pg, mobile, web
#   tools/dev/check-local.sh --changed       # only the stages the diff against origin/main touches
#   tools/dev/check-local.sh --only api      # api | pg | mobile | web | e2e
#   tools/dev/check-local.sh --no-pg         # skip the PostgreSQL run (the slowest)
#   tools/dev/check-local.sh --e2e           # also the Playwright browser tests (needs: cd apps/web && npx playwright install chromium)
#   tools/dev/check-local.sh --fail-fast     # stop at the first failing stage
#
# Works from any checkout or git worktree: it checks the code of the folder
# you run it in. The API runs on SQLite, and on a disposable local PostgreSQL
# cluster (scripts/test_postgres.py), never on a hosted database. No .env is read.
#
# Cannot run here: the golden-image tests (Linux only, skipped on macOS) and
# the mobile-goldens workflow. Those stay in CI.
set -uo pipefail

ROOT="$(git rev-parse --show-toplevel 2> /dev/null)" || { echo "Run this inside the repo." >&2; exit 2; }
API="$ROOT/services/api"
MOBILE="$ROOT/apps/mobile"
WEB="$ROOT/apps/web"

ONLY=""
CHANGED=false
PG=true
E2E=false
FAIL_FAST=false
usage() { sed -n '2,19p' "${BASH_SOURCE[0]}" | sed 's/^# \{0,1\}//'; exit "${1:-2}"; }
while [ $# -gt 0 ]; do
  case "$1" in
    --only) ONLY="${2:?--only needs api, pg, mobile, web or e2e}"; shift ;;
    --changed) CHANGED=true ;;
    --no-pg) PG=false ;;
    --e2e) E2E=true ;;
    --fail-fast) FAIL_FAST=true ;;
    -h | --help) usage 0 ;;
    *) echo "Unknown option: $1" >&2; usage ;;
  esac
  shift
done
case "$ONLY" in "" | api | pg | mobile | web | e2e) ;; *) echo "Unknown stage: $ONLY" >&2; usage ;; esac

log() { printf '[%s] %s\n' "$(date +%H:%M:%S)" "$*" >&2; }

# ---- which stages to run ------------------------------------------------------
want_api=false; want_pg=false; want_mobile=false; want_web=false; want_e2e=false
if [ -n "$ONLY" ]; then
  eval "want_$ONLY=true"
elif $CHANGED; then
  base="$(git merge-base HEAD origin/main 2> /dev/null || echo HEAD)"
  files="$( { git diff --name-only "$base"...HEAD; git diff --name-only; git ls-files --others --exclude-standard; } 2> /dev/null | sort -u)"
  has() { printf '%s\n' "$files" | grep -Eq "$1"; }
  if has '^(services/api/|packages/api-contract/)'; then want_api=true; want_pg=true; fi
  if has '^(apps/mobile/|docs/brand/tokens.json|packages/api-contract/openapi.json)'; then want_mobile=true; fi
  if has '^(apps/web/|docs/brand/tokens.json)'; then want_web=true; fi
  if has '^(apps/web/|services/api/|tools/test-data/)'; then want_e2e=true; fi
  if [ -z "$files" ]; then log "No changes against origin/main: nothing to run."; fi
else
  want_api=true; want_pg=true; want_mobile=true; want_web=true; want_e2e=true
fi
$PG || want_pg=false
# The browser tests are slow and need a browser, so they only run when asked.
if ! $E2E && [ "$ONLY" != e2e ]; then want_e2e=false; fi

# ---- Python: this checkout's code, with a virtualenv from this or the main checkout ----
find_python() {
  local main_checkout
  main_checkout="$(cd "$(git rev-parse --git-common-dir)/.." 2> /dev/null && pwd)"
  for py in "$API/.venv/bin/python" "$main_checkout/services/api/.venv/bin/python"; do
    [ -x "$py" ] && { echo "$py"; return; }
  done
  return 1
}
PY=""
if $want_api || $want_pg || $want_e2e; then
  PY="$(find_python)" || { echo "No virtualenv found. Create one: cd services/api && python3 -m venv .venv && .venv/bin/pip install -e '.[dev]'" >&2; exit 2; }
  # An editable install points at the checkout that made it. Put THIS checkout's code first.
  export PYTHONPATH="$API${PYTHONPATH:+:$PYTHONPATH}"
  log "Python: $PY (code from $API)"
fi

# Flutter rewrites a few tracked files and makes a Podfile. Put back only what was clean at the start.
noise="apps/mobile/analysis_options.yaml apps/mobile/ios/Flutter/Debug.xcconfig apps/mobile/ios/Flutter/Release.xcconfig apps/mobile/pubspec.lock"
clean_before=""
for f in $noise; do
  [ -z "$(git -C "$ROOT" status --porcelain -- "$f")" ] && clean_before="$clean_before $f"
done
podfile_before=false; [ -e "$MOBILE/ios/Podfile" ] && podfile_before=true
restore_noise() {
  for f in $clean_before; do git -C "$ROOT" checkout -q -- "$f" 2> /dev/null || true; done
  $podfile_before || rm -f "$MOBILE/ios/Podfile"
}
trap restore_noise EXIT

# ---- helpers --------------------------------------------------------------------
RESULTS=""
FAILED=0
# stage <name> <function>: runs it, times it, records PASS or FAIL.
stage() {
  local name="$1" fn="$2" start=$SECONDS
  log "---- $name ----"
  if "$fn"; then
    RESULTS="$RESULTS\n  PASS  $name  ($((SECONDS - start))s)"
  else
    RESULTS="$RESULTS\n  FAIL  $name  ($((SECONDS - start))s)"
    FAILED=1
    if $FAIL_FAST; then summary; exit 1; fi
  fi
}
summary() { printf '\nSummary:%b\n' "$RESULTS" >&2; }

# fingerprint <path>: a hash of a file, or of every file in a folder.
fingerprint() {
  if [ -d "$1" ]; then
    find "$1" -type f -print0 | sort -z | xargs -0 shasum | shasum | cut -d' ' -f1
  else
    shasum < "$1" | cut -d' ' -f1
  fi
}

# gen_stale <path> <command...>: runs a generator and says whether it changed the
# file or folder. It compares before and after (not against git), so uncommitted
# work does not count as stale.
gen_stale() {
  local target="$1"; shift
  local before after
  before="$(fingerprint "$target")"
  "$@" > /dev/null 2>&1 || { echo "  could not run: $*" >&2; return 1; }
  after="$(fingerprint "$target")"
  if [ "$before" != "$after" ]; then
    echo "  $target was stale and has been regenerated. Commit it." >&2
    return 1
  fi
}

# ---- stages ---------------------------------------------------------------------
api_stage() {
  cd "$API" || return 1
  "$PY" -m ruff check . || return 1
  "$PY" -m pytest -q || return 1
  # The OpenAPI contract must match the code (the api-ci "Contract check").
  gen_stale "$ROOT/packages/api-contract/openapi.json" "$PY" scripts/export_openapi.py
}

pg_stage() {
  cd "$API" || return 1
  "$PY" scripts/test_postgres.py
}

mobile_stage() {
  cd "$MOBILE" || return 1
  command -v flutter > /dev/null || { echo "flutter is not on PATH." >&2; return 1; }
  flutter pub get > /dev/null || return 1
  gen_stale lib/core/ui/tokens.g.dart dart run tool/gen_theme.dart || return 1
  gen_stale lib/l10n flutter gen-l10n || return 1
  gen_stale lib/core/api/api.g.dart dart run tool/gen_api.dart || return 1
  # The wire-contract cases are generated from the OpenAPI contract.
  gen_stale test/contract "$PY" "$ROOT/tools/coverage/generate_contract_cases.py" || return 1
  flutter analyze || return 1
  flutter test || return 1
  echo "  Note: the golden-image tests are skipped on macOS. CI runs them on Linux." >&2
}

web_stage() {
  cd "$WEB" || return 1
  if [ ! -d node_modules ] || [ package-lock.json -nt node_modules/.package-lock.json ]; then
    npm ci || return 1
  fi
  npm run lint || return 1
  npm run test || return 1
  npm run build || return 1
}

e2e_stage() {
  cd "$WEB" || return 1
  [ -d node_modules ] || npm ci || return 1
  E2E_PYTHON="$PY" npm run e2e
}

$want_api && stage "api: ruff, pytest (SQLite), contract" api_stage
$want_pg && stage "api: pytest on PostgreSQL (disposable local cluster)" pg_stage
$want_mobile && stage "mobile: generated files, analyze, test" mobile_stage
$want_web && stage "web: lint, test, build" web_stage
$want_e2e && stage "web: Playwright browser tests" e2e_stage

summary
if [ -z "$RESULTS" ]; then exit 0; fi
if [ "$FAILED" -ne 0 ]; then log "FAILED. Fix the stages above before you push."; exit 1; fi
log "All local checks passed. CI is the final gate (it also runs the goldens on Linux)."
