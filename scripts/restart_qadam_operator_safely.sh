#!/bin/sh
set -eu

ROOT=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
LABEL="com.qadam.operator"
TARGET="$HOME/Library/LaunchAgents/$LABEL.plist"
DOMAIN="gui/$(id -u)"

cd "$ROOT"
"$ROOT/.venv/bin/python" "$ROOT/scripts/check_qadam_state_root.py"
"$ROOT/.venv/bin/python" "$ROOT/scripts/check_qadam_artifact_ownership.py"
"$ROOT/.venv/bin/python" "$ROOT/scripts/check_qadam_resource_locks.py"
"$ROOT/.venv/bin/python" "$ROOT/scripts/check_qadam_artifact_generations.py"

launchctl bootout "$DOMAIN/$LABEL" >/dev/null 2>&1 || true
"$ROOT/scripts/install_qadam_operator_launch_agent.sh"
launchctl bootstrap "$DOMAIN" "$TARGET"
sleep 2
"$ROOT/scripts/status_qadam_operator_launch_agent.sh"
