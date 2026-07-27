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
drain_attempt=1
while launchctl print "$DOMAIN/$LABEL" >/dev/null 2>&1; do
  if [ "$drain_attempt" -ge 20 ]; then
    echo "Operator service did not drain within 20 seconds." >&2
    exit 1
  fi
  sleep 1
  drain_attempt=$((drain_attempt + 1))
done
"$ROOT/scripts/install_qadam_operator_launch_agent.sh"
bootstrap_attempt=1
bootstrap_status=1
while [ "$bootstrap_attempt" -le 5 ]; do
  if launchctl bootstrap "$DOMAIN" "$TARGET"; then
    bootstrap_status=0
    break
  fi
  if launchctl print "$DOMAIN/$LABEL" >/dev/null 2>&1; then
    bootstrap_status=0
    break
  fi
  sleep "$bootstrap_attempt"
  bootstrap_attempt=$((bootstrap_attempt + 1))
done
if [ "$bootstrap_status" -ne 0 ]; then
  echo "Operator service could not be bootstrapped after five bounded retries." >&2
  exit 1
fi
sleep 2
if ! launchctl print "$DOMAIN/$LABEL" >/dev/null 2>&1; then
  echo "Operator service was not loaded after bootstrap." >&2
  exit 1
fi
"$ROOT/scripts/status_qadam_operator_launch_agent.sh"
