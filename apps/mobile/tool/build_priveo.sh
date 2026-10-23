#!/usr/bin/env bash
# Builds and runs the dev app on an Android emulator/phone or the iOS Simulator.
# The macOS counterpart of push_apk.ps1.
#
# From any folder:
#   apps/mobile/tool/build_priveo.sh android
#   apps/mobile/tool/build_priveo.sh ios
#   apps/mobile/tool/build_priveo.sh android --build-only   (writes the APK)
#   apps/mobile/tool/build_priveo.sh ios --replay --api http://192.168.1.5:8000
#
# Flags: --build-only  --clean  --api <url>  --local  --replay  --debug|--release  --device <id>
# --local uses the API from tools/dev/run-local.sh on this Mac (Android emulator: 10.0.2.2,
# iOS Simulator: localhost). It needs a debug build, so it cannot be used with --release.
# --clean runs `flutter clean` first, for a full rebuild (slow).
#
# Analytics (PostHog EU): the key comes from $POSTHOG_KEY, else from the GitHub
# variable POSTHOG_KEY (needs `gh auth login`). Without a key the app sends
# nothing. Session replay is off unless you add --replay, and it records every
# screen unmasked, so use test data only.
#
# Every step is logged with a time. The full Flutter output also goes to
# apps/mobile/build/logs/ (git-ignored).
set -euo pipefail

MOBILE="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
REPO="jazgitt/priveo"
POSTHOG_HOST="https://eu.i.posthog.com"

usage() {
  sed -n '2,19p' "${BASH_SOURCE[0]}" | sed 's/^# \{0,1\}//'
  exit "${1:-2}"
}

START=$SECONDS
STEP="starting"
# To stderr, so log lines never mix into a value a function returns on stdout.
log() { printf '[%s] %s\n' "$(date +%H:%M:%S)" "$*" >&2; }
step() { STEP="$1"; log "step: $1 (+$((SECONDS - START))s)"; }

TARGET="${1:-}"
case "$TARGET" in
  ios | android) shift ;;
  -h | --help) usage 0 ;;
  *) echo "Target must be ios or android." >&2; usage ;;
esac

API_URL="https://priveo-api.vercel.app"
REPLAY=false
BUILD_ONLY=false
CLEAN=false
LOCAL=false
MODE=""
DEVICE=""
while [ $# -gt 0 ]; do
  case "$1" in
    --build-only) BUILD_ONLY=true ;;
    --clean) CLEAN=true ;;
    --replay) REPLAY=true ;;
    --debug) MODE=debug ;;
    --release) MODE=release ;;
    --api) API_URL="${2:?--api needs a URL}"; shift ;;
    --local) LOCAL=true ;;
    --device) DEVICE="${2:?--device needs an id}"; shift ;;
    -h | --help) usage 0 ;;
    *) echo "Unknown option: $1" >&2; usage ;;
  esac
  shift
done
if $LOCAL; then
  if [ "$TARGET" = android ]; then API_URL="http://10.0.2.2:8000"; else API_URL="http://localhost:8000"; fi
  [ "$MODE" != release ] || { echo "--local needs a debug build (plain http is blocked in release)." >&2; exit 2; }
  MODE=debug
fi
if [ -z "$MODE" ]; then
  if $BUILD_ONLY; then MODE=release; else MODE=debug; fi
fi

STAMP="$(date +%y%m%d-%H%M%S)"
LOG_DIR="$MOBILE/build/logs"
LOG_FILE="$LOG_DIR/build_priveo-$TARGET-$STAMP.log"
mkdir -p "$LOG_DIR"
: > "$LOG_FILE"

on_error() {
  local code=$?
  log "FAILED at step '$STEP' (exit $code, after $((SECONDS - START))s)"
  log "Full log: $LOG_FILE"
  if [ -s "$LOG_FILE" ]; then
    log "Last 30 lines:"
    tail -n 30 "$LOG_FILE" | sed 's/^/    /'
  fi
  exit "$code"
}
trap on_error ERR

# adb lives in the Android SDK, which Android Studio does not put on PATH.
SDK_DIR="${ANDROID_HOME:-${ANDROID_SDK_ROOT:-$HOME/Library/Android/sdk}}"
if [ -d "$SDK_DIR/platform-tools" ]; then
  export PATH="$SDK_DIR/platform-tools:$SDK_DIR/emulator:$PATH"
fi

cd "$MOBILE"
log "Target $TARGET, mode $MODE, $($BUILD_ONLY && echo build-only || echo build and run), API $API_URL"
log "Log file: $LOG_FILE"

step "checking tools"
command -v flutter > /dev/null || { echo "flutter is not on PATH." >&2; false; }
log "flutter: $(flutter --version 2> /dev/null | head -n 1)"

# PostHog key: environment first, then the GitHub variable. Never printed.
step "finding the PostHog key"
POSTHOG_KEY="${POSTHOG_KEY:-}"
KEY_SOURCE="env"
if [ -z "$POSTHOG_KEY" ] && command -v gh > /dev/null; then
  POSTHOG_KEY="$(gh variable get POSTHOG_KEY --repo "$REPO" 2> /dev/null || true)"
  KEY_SOURCE="GitHub variable"
fi
DEFINES=("--dart-define=API_BASE_URL=$API_URL" "--dart-define=BUILD_STAMP=$STAMP")
if [ -n "$POSTHOG_KEY" ]; then
  DEFINES+=("--dart-define=POSTHOG_KEY=$POSTHOG_KEY"
    "--dart-define=POSTHOG_HOST=$POSTHOG_HOST"
    "--dart-define=POSTHOG_REPLAY=$REPLAY")
  log "Analytics: PostHog EU, key from $KEY_SOURCE, replay $($REPLAY && echo ON || echo off)"
else
  log "Analytics: off (no POSTHOG_KEY in the environment or on GitHub)"
fi

# Pick a device unless one was given. Boots an emulator/simulator when none runs.
pick_android_device() {
  command -v adb > /dev/null || { echo "adb not found. Install the Android SDK platform tools." >&2; false; }
  local id
  id="$(adb devices | awk 'NR>1 && $2=="device" {print $1; exit}')"
  if [ -z "$id" ]; then
    local avd
    avd="$(flutter emulators 2> /dev/null | awk -F'•' '/android/ {gsub(/ /,"",$1); print $1; exit}')"
    [ -n "$avd" ] || { echo "No Android device and no emulator found. Create one in Android Studio." >&2; false; }
    log "No device running. Starting emulator $avd ..."
    flutter emulators --launch "$avd" >> "$LOG_FILE" 2>&1
    adb wait-for-device
    until [ "$(adb shell getprop sys.boot_completed 2> /dev/null | tr -d '\r')" = "1" ]; do sleep 2; done
    id="$(adb devices | awk 'NR>1 && $2=="device" {print $1; exit}')"
  fi
  echo "$id"
}

pick_ios_device() {
  command -v xcrun > /dev/null || { echo "xcrun not found. Install Xcode." >&2; false; }
  xcrun simctl help > /dev/null 2>&1 || { echo "Xcode is not set up. Run: sudo xcode-select --switch /Applications/Xcode.app/Contents/Developer" >&2; false; }
  command -v pod > /dev/null || { echo "CocoaPods is missing. Run: brew install cocoapods" >&2; false; }
  local id
  id="$(xcrun simctl list devices booted | grep -Eo '[0-9A-F]{8}-([0-9A-F]{4}-){3}[0-9A-F]{12}' | head -n 1 || true)"
  if [ -z "$id" ]; then
    id="$(xcrun simctl list devices available | grep -E 'iPhone' | grep -Eo '[0-9A-F]{8}-([0-9A-F]{4}-){3}[0-9A-F]{12}' | tail -n 1 || true)"
    [ -n "$id" ] || { echo "No iOS Simulator found. Add one in Xcode > Settings > Platforms." >&2; false; }
    log "No simulator running. Booting $id ..."
    xcrun simctl boot "$id" >> "$LOG_FILE" 2>&1 || true
    open -a Simulator
  fi
  echo "$id"
}

if ! $BUILD_ONLY && [ -z "$DEVICE" ]; then
  step "choosing a device ($TARGET)"
  if [ "$TARGET" = android ]; then DEVICE="$(pick_android_device)"; else DEVICE="$(pick_ios_device)"; fi
  log "Device: $DEVICE"
elif [ "$TARGET" = ios ] && $BUILD_ONLY; then
  command -v pod > /dev/null || { echo "CocoaPods is missing. Run: brew install cocoapods" >&2; false; }
fi

if $CLEAN; then
  step "flutter clean (full rebuild)"
  # This deletes build/, including the log folder, so keep the output aside
  # and write it into a fresh log afterwards.
  CLEAN_OUT="$(flutter clean 2>&1)"
  mkdir -p "$LOG_DIR"
  printf '%s\n' "$CLEAN_OUT" | tee -a "$LOG_FILE"
fi

step "flutter pub get"
flutter pub get 2>&1 | tee -a "$LOG_FILE"

# Only Android has the dev/prod flavors. iOS has a single Runner scheme.
FLAVOR=()
if [ "$TARGET" = android ]; then
  FLAVOR=(--flavor dev)
  if $BUILD_ONLY; then
    # Gradle once packed an old copy of the app's code into every APK.
    step "clearing stale Android build folders"
    for d in merged_jni_libs merged_native_libs stripped_native_libs; do
      rm -rf "$MOBILE/build/app/intermediates/$d"
    done
  fi
fi

if $BUILD_ONLY; then
  if [ "$TARGET" = android ]; then
    step "flutter build apk --$MODE"
    flutter build apk "--$MODE" "${FLAVOR[@]}" -t lib/main_dev.dart "${DEFINES[@]}" 2>&1 | tee -a "$LOG_FILE"
    log "APK: $MOBILE/build/app/outputs/flutter-apk/app-dev-$MODE.apk"
  else
    step "flutter build ios --simulator --$MODE"
    flutter build ios --simulator "--$MODE" -t lib/main_dev.dart "${DEFINES[@]}" 2>&1 | tee -a "$LOG_FILE"
    log "App: $MOBILE/build/ios/iphonesimulator/Runner.app"
  fi
else
  step "flutter run --$MODE on $DEVICE (press q to quit, r to hot reload)"
  flutter run "--$MODE" -d "$DEVICE" "${FLAVOR[@]}" -t lib/main_dev.dart "${DEFINES[@]}" 2>&1 | tee -a "$LOG_FILE"
fi

log "Done in $((SECONDS - START))s. Build $STAMP. Log: $LOG_FILE"
