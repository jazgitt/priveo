#!/usr/bin/env bash
# Install the launchd jobs for the nightly pipeline (user agents, no sudo).
#   install-launchd.sh            install and load
#   install-launchd.sh --remove   unload and delete
# Jobs: in.priveo.nightly at 02:00 local time (IST on the owner's Mac); in.priveo.nightly-watchdog at 06:30
# . The wake at 01:55 needs sudo and is NOT done here:
#   sudo pmset repeat wakeorpoweron MTWRFSU 01:55:00
set -euo pipefail
HOME_DIR="${NIGHTLY_HOME:-$HOME/priveo-nightly}"
AGENTS="$HOME/Library/LaunchAgents"
UIDN="$(id -u)"
# launchd has a bare PATH. Keep the one this shell has, plus Homebrew and the Flutter/Dart locations.
RUN_PATH="/opt/homebrew/bin:/opt/homebrew/opt/postgresql@17/bin:/usr/local/bin:$PATH"

plist() { # label hour minute script args...
  local label="$1" hour="$2" minute="$3" script="$4"; shift 4
  cat << EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0"><dict>
  <key>Label</key><string>$label</string>
  <key>ProgramArguments</key><array><string>$script</string>$(for a in "$@"; do printf '<string>%s</string>' "$a"; done)</array>
  <key>StartCalendarInterval</key><dict><key>Hour</key><integer>$hour</integer><key>Minute</key><integer>$minute</integer></dict>
  <key>WorkingDirectory</key><string>$HOME_DIR</string>
  <key>EnvironmentVariables</key><dict><key>PATH</key><string>$RUN_PATH</string><key>NIGHTLY_HOME</key><string>$HOME_DIR</string></dict>
  <key>StandardOutPath</key><string>$HOME_DIR/logs/launchd-$label.out</string>
  <key>StandardErrorPath</key><string>$HOME_DIR/logs/launchd-$label.err</string>
</dict></plist>
EOF
}

install_one() { # label hour minute script args...
  local label="$1"
  plist "$@" > "$AGENTS/$label.plist"
  launchctl bootout "gui/$UIDN/$label" 2> /dev/null || true
  launchctl bootstrap "gui/$UIDN" "$AGENTS/$label.plist"
  echo "Loaded $label"
}

if [ "${1:-}" = "--remove" ]; then
  for label in in.priveo.nightly in.priveo.nightly-watchdog; do
    launchctl bootout "gui/$UIDN/$label" 2> /dev/null || true
    rm -f "$AGENTS/$label.plist"
    echo "Removed $label"
  done
  exit 0
fi

mkdir -p "$AGENTS" "$HOME_DIR/logs"
install_one in.priveo.nightly 2 0 "$HOME_DIR/tools/nightly/run-nightly.sh"
install_one in.priveo.nightly-watchdog 6 30 /usr/bin/env python3 "$HOME_DIR/tools/nightly/watchdog.py"
