#!/usr/bin/env bash
# Builds an installable app that points at the Test or the Production API, and
# names the file after the environment and the version in pubspec.yaml.
#
#   apps/mobile/tool/build_release.sh android test    # dist/priveo-test-<version>.apk
#   apps/mobile/tool/build_release.sh android prod    # dist/priveo-release-<version>.apk
#   apps/mobile/tool/build_release.sh ios test        # dist/priveo-test-<version>-ios-sim.zip
#   apps/mobile/tool/build_release.sh ios prod        # dist/priveo-release-<version>-ios-sim.zip
#   apps/mobile/tool/build_release.sh ios test --ipa  # dist/priveo-test-<version>.ipa (needs Apple signing)
#   apps/mobile/tool/build_release.sh android test --api https://example.com   # another API
#
# <version> is pubspec.yaml's `0.2.7+207` written as 0.2.7-207 (name, then build number).
# Files go to apps/mobile/dist/ (git-ignored). The app shows the same details under
# Settings > Version (customer), Profile > Version (crew) and Home > Version (admin).
#
# Test uses --flavor test (package in.priveo.app.test, label "Priveo Test") and
# prod uses --flavor prod (in.priveo.app, label "Priveo"), so both install side by
# side on Android. On iOS both share one bundle id: install one at a time.
#
# The API addresses can be overridden with API_TEST_URL and API_PROD_URL. Change the
# defaults below when the custom domains exist (api.priveo.in).
#
# iOS: a simulator build needs only Xcode. An .ipa for a phone needs an Apple
# Developer account and a signing identity, which are not set up yet: --ipa stops
# with a clear message until then. The simulator build is a debug build, because
# Flutter does not make release builds for the simulator.
#
# Android is signed with android/key.properties when it exists (CI writes it from
# secrets), otherwise with the debug key, which installs fine for testing.
set -euo pipefail

MOBILE="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
REPO="jazgitt/priveo"
POSTHOG_HOST="https://eu.i.posthog.com"
TEST_URL="${API_TEST_URL:-https://priveo-api-test.vercel.app}"
PROD_URL="${API_PROD_URL:-https://priveo-api-prod.vercel.app}"

usage() { sed -n '2,25p' "${BASH_SOURCE[0]}" | sed 's/^# \{0,1\}//'; exit "${1:-2}"; }
log() { printf '[%s] %s\n' "$(date +%H:%M:%S)" "$*" >&2; }
die() { echo "error: $*" >&2; exit 1; }

PLATFORM="${1:-}"; ENV_NAME="${2:-}"
case "$PLATFORM" in android | ios) ;; -h | --help) usage 0 ;; *) echo "First argument must be android or ios." >&2; usage ;; esac
case "$ENV_NAME" in test | prod) ;; *) echo "Second argument must be test or prod." >&2; usage ;; esac
shift 2

API_URL=""
IPA=false
while [ $# -gt 0 ]; do
  case "$1" in
    --api) API_URL="${2:?--api needs a URL}"; shift ;;
    --ipa) IPA=true ;;
    -h | --help) usage 0 ;;
    *) echo "Unknown option: $1" >&2; usage ;;
  esac
  shift
done
if $IPA && [ "$PLATFORM" != ios ]; then die "--ipa is for ios only."; fi

if [ "$ENV_NAME" = test ]; then
  PREFIX="priveo-test"; ENTRY="lib/main_test.dart"; FLAVOR="test"; DEFAULT_URL="$TEST_URL"
else
  PREFIX="priveo-release"; ENTRY="lib/main_prod.dart"; FLAVOR="prod"; DEFAULT_URL="$PROD_URL"
fi
[ -n "$API_URL" ] || API_URL="$DEFAULT_URL"

# pubspec.yaml: version: 0.2.7+207
RAW="$(sed -nE 's/^version:[[:space:]]*([^[:space:]]+).*/\1/p' "$MOBILE/pubspec.yaml" | head -n1)"
[ -n "$RAW" ] || die "no version in pubspec.yaml."
VERSION="${RAW/+/-}"
STAMP="$(date +%y%m%d-%H%M%S)"
NAME="$PREFIX-$VERSION"
DIST="$MOBILE/dist"
mkdir -p "$DIST"

cd "$MOBILE"
command -v flutter > /dev/null || die "flutter is not on PATH."
log "Building $PLATFORM $ENV_NAME: version $RAW, API $API_URL"

# PostHog key: environment first, then the GitHub variable. Never printed.
POSTHOG_KEY="${POSTHOG_KEY:-}"
if [ -z "$POSTHOG_KEY" ] && command -v gh > /dev/null; then
  POSTHOG_KEY="$(gh variable get POSTHOG_KEY --repo "$REPO" 2> /dev/null || true)"
fi
DEFINES=("--dart-define=API_BASE_URL=$API_URL" "--dart-define=BUILD_STAMP=$STAMP")
if [ -n "$POSTHOG_KEY" ]; then
  DEFINES+=("--dart-define=POSTHOG_KEY=$POSTHOG_KEY" "--dart-define=POSTHOG_HOST=$POSTHOG_HOST" "--dart-define=POSTHOG_REPLAY=false")
fi

flutter pub get > /dev/null

if [ "$PLATFORM" = android ]; then
  # Gradle once packed an old copy of the app's code into every APK.
  for d in merged_jni_libs merged_native_libs stripped_native_libs; do
    rm -rf "$MOBILE/build/app/intermediates/$d"
  done
  flutter build apk --release --flavor "$FLAVOR" -t "$ENTRY" "${DEFINES[@]}"
  OUT="$DIST/$NAME.apk"
  cp "$MOBILE/build/app/outputs/flutter-apk/app-$FLAVOR-release.apk" "$OUT"
elif $IPA; then
  security find-identity -v -p codesigning 2> /dev/null | grep -Eq '^[[:space:]]*[1-9][0-9]* valid identit' \
    || die "no Apple signing identity on this Mac. An .ipa needs an Apple Developer account (not set up yet). Use the simulator build for now."
  flutter build ipa --release -t "$ENTRY" "${DEFINES[@]}" --export-method ad-hoc
  IPA_FILE="$(ls -t "$MOBILE"/build/ios/ipa/*.ipa 2> /dev/null | head -n1)"
  [ -n "$IPA_FILE" ] || die "flutter did not produce an .ipa."
  OUT="$DIST/$NAME.ipa"
  cp "$IPA_FILE" "$OUT"
else
  flutter build ios --simulator --debug -t "$ENTRY" "${DEFINES[@]}"
  APP="$MOBILE/build/ios/iphonesimulator/Runner.app"
  [ -d "$APP" ] || die "no Runner.app at $APP."
  OUT="$DIST/$NAME-ios-sim.zip"
  rm -f "$OUT"
  ditto -c -k --keepParent "$APP" "$OUT"
fi

log "Done: $OUT"
log "  environment: $ENV_NAME  version: $RAW  API: $API_URL  built: $STAMP"
log "  The app shows this under its Version page."
