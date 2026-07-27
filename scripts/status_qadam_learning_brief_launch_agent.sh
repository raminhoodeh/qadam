#!/bin/sh
set -eu

LABEL="com.qadam.learning-brief"
DOMAIN="gui/$(id -u)"
ROOT=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
STATE="$ROOT/data/runtime/daily_learning_scheduler.json"

if launchctl print "$DOMAIN/$LABEL" >/dev/null 2>&1; then
  echo "status=loaded"
  launchctl print "$DOMAIN/$LABEL" | sed -n '1,80p'
  if [ -f "$STATE" ]; then
    echo "scheduler_state=$STATE"
    jq '{generated_at,local_date,local_time,brief_slot,reason,last_attempt_at,last_exit_code,automation_status,live_send_attempted,live_send_succeeded}' "$STATE"
  fi
else
  echo "status=not_loaded"
  exit 1
fi
