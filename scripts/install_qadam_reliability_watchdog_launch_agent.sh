#!/bin/sh
set -eu

ROOT=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
LABEL="com.qadam.reliability-watchdog"
TEMPLATE="$ROOT/ops/launchd/$LABEL.plist.template"
TARGET="$HOME/Library/LaunchAgents/$LABEL.plist"
LOAD=false

if [ "${1:-}" = "--load" ]; then
  LOAD=true
elif [ "$#" -gt 0 ]; then
  echo "Usage: $0 [--load]" >&2
  exit 2
fi

LOG_DIR="$HOME/Library/Logs/Qadam"
mkdir -p "$HOME/Library/LaunchAgents" "$LOG_DIR"
sed -e "s|__QADAM_ROOT__|$ROOT|g" -e "s|__QADAM_LOG_DIR__|$LOG_DIR|g" "$TEMPLATE" > "$TARGET"
plutil -lint "$TARGET" >/dev/null

echo "Prepared: $TARGET"
echo "Cadence: every 60 seconds, plus one bounded pass at load"
echo "Authority: runtime wake-up only; no research, PaperOps, broker, or policy authority"

if [ "$LOAD" = true ]; then
  launchctl bootout "gui/$(id -u)/$LABEL" >/dev/null 2>&1 || true
  launchctl bootstrap "gui/$(id -u)" "$TARGET"
  echo "Loaded: $LABEL"
else
  echo "Not loaded. After review: $0 --load"
fi
