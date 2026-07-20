#!/bin/sh
set -eu

ROOT=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
TEMPLATE="$ROOT/ops/launchd/com.qadam.operator.plist.template"
TARGET="$HOME/Library/LaunchAgents/com.qadam.operator.plist"

mkdir -p "$HOME/Library/LaunchAgents"
sed "s|__QADAM_ROOT__|$ROOT|g" "$TEMPLATE" > "$TARGET"

echo "Prepared: $TARGET"
echo "Program: /usr/bin/caffeinate -s $ROOT/.venv/bin/python $ROOT/scripts/run_qadam_operator_service.py --serve --poll-seconds 60 --max-jobs-per-cycle 4"
echo "Working directory: $ROOT"
echo "Safety mode: paper-only, research-lock aware, no direct broker path"
echo "Power mode: prevent system sleep while connected to AC power; display sleep remains allowed"
echo "Cadence: dispatcher checks every 60 seconds; each registered job retains its own due time"
echo "Long jobs: resumable workers; duplicate concurrency groups are skipped"
echo "Logs: $ROOT/data/runtime/qadam-operator-service.stdout.log and qadam-operator-service.stderr.log"
echo "The service was not loaded automatically. After review, load explicitly with:"
echo "launchctl bootstrap gui/$(id -u) $TARGET"
