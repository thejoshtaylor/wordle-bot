#!/bin/bash
# Wrapper for launchd: run the daily Wordle job from the repo with its venv.
set -euo pipefail
REPO="/Users/josh/code/wordle-bot"
cd "$REPO"
mkdir -p scripts/daily/logs
exec "$REPO/venv/bin/python" scripts/daily/run_daily.py >> scripts/daily/logs/daily.log 2>&1
