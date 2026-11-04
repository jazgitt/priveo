#!/usr/bin/env bash
# One-time setup of the nightly clone (default ~/priveo-nightly). Safe to run again.
# Creates the clone, its Python virtualenv, the web and mobile installs and the browser for the
# Playwright tests, and a nightly.env with NIGHTLY_ENABLED=false (edit it to switch the night on).
set -euo pipefail
HOME_DIR="${NIGHTLY_HOME:-$HOME/priveo-nightly}"
REMOTE="${NIGHTLY_REMOTE:-https://github.com/jazgitt/priveo.git}"
if [ ! -d "$HOME_DIR/.git" ]; then
  git clone "$REMOTE" "$HOME_DIR"
fi
cd "$HOME_DIR"
git config user.name "Priveo Nightly"
git config user.email "nightly@priveo.invalid"
for f in logs/ KILL nightly.lock nightly.env; do
  grep -qxF "$f" .git/info/exclude 2> /dev/null || echo "$f" >> .git/info/exclude
done
git fetch -q origin main && git checkout -q -B main origin/main && git reset -q --hard origin/main
mkdir -p logs
[ -f nightly.env ] || printf '# Read as data by the pipeline. NIGHTLY_ENABLED must be true for a real run.\nNIGHTLY_ENABLED=false\n' > nightly.env
if [ ! -x services/api/.venv/bin/python ]; then
  "${NIGHTLY_PYTHON:-python3.12}" -m venv services/api/.venv
  services/api/.venv/bin/pip install -q -e "services/api[dev]"
fi
(cd apps/web && npm ci --silent && npx playwright install chromium)
(cd apps/mobile && flutter pub get > /dev/null)
echo "Nightly clone ready at $HOME_DIR. Switch the night on with NIGHTLY_ENABLED=true in $HOME_DIR/nightly.env."
