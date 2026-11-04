#!/usr/bin/env bash
# Start the nightly pipeline from the dedicated clone (~/priveo-nightly). See docs/nightly-pipeline.md.
#   run-nightly.sh [--dry-run] [--skip-checks] [--ignore-recent-deploy]
# Updates the clone to origin/main first, so the scripts that run are the merged ones. The clone is
# private to the pipeline: never run this in a working checkout.
set -uo pipefail
HOME_DIR="${NIGHTLY_HOME:-$HOME/priveo-nightly}"
cd "$HOME_DIR" || { echo "No nightly clone at $HOME_DIR. Run tools/nightly/setup-clone.sh." >&2; exit 2; }
git fetch -q origin main && git checkout -q -B main origin/main && git reset -q --hard origin/main \
  || echo "Warning: could not update the clone; running what is there." >&2
# -i no idle sleep, -m no disk sleep, -s no system sleep on AC power. The dry run of 04-Nov-26 was
# frozen by 'Maintenance Sleep' every 15 minutes and ran for 3 hours.
exec caffeinate -ims python3 tools/nightly/nightly.py "$@"
