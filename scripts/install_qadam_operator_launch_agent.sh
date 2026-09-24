#!/bin/sh
set -eu

ROOT=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
TEMPLATE="$ROOT/ops/launchd/com.qadam.operator.plist.template"
TARGET="$HOME/Library/LaunchAgents/com.qadam.operator.plist"

LOG_DIR="$HOME/Library/Logs/Qadam"
mkdir -p "$HOME/Library/LaunchAgents" "$LOG_DIR"
sed -e "s|__QADAM_ROOT__|$ROOT|g" -e "s|__QADAM_LOG_DIR__|$LOG_DIR|g" "$TEMPLATE" > "$TARGET"

echo "Prepared: $TARGET"
echo "Program: /usr/bin/caffeinate -s $ROOT/.venv/bin/python $ROOT/scripts/run_qadam_operator_service.py --serve --poll-seconds 60"
echo "Working directory: $ROOT"
echo "Safety mode: paper-only, research-lock aware, no direct broker path"
echo "State root: $ROOT/data (local, Git-ignored, state-root preflight required)"
echo "Power mode: prevent system sleep while connected to AC power; display sleep remains allowed"
echo "Cadence: dispatcher checks every 60 seconds; each registered job retains its own due time"
echo "Scheduler budget: loaded from $ROOT/config/qadam_scheduler_domains.json"
echo "Long jobs: resumable workers; incompatible resource claims are serialized"
echo "Logs: $LOG_DIR/qadam-operator-service.stdout.log and qadam-operator-service.stderr.log"
echo "The service was not loaded automatically. After review, load explicitly with:"
echo "launchctl bootstrap gui/$(id -u) $TARGET"
