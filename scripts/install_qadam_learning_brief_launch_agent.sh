#!/bin/sh
set -eu

ROOT=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
TEMPLATE="$ROOT/ops/launchd/com.qadam.learning-brief.plist.template"
TARGET="$HOME/Library/LaunchAgents/com.qadam.learning-brief.plist"
DOMAIN="gui/$(id -u)"

mkdir -p "$HOME/Library/LaunchAgents"
sed "s|__QADAM_ROOT__|$ROOT|g" "$TEMPLATE" > "$TARGET"
plutil -lint "$TARGET" >/dev/null

echo "Prepared: $TARGET"
echo "Schedule: 08:02 and 20:02, with a timezone-aware five-minute fallback"
echo "Command: $ROOT/.venv/bin/python $ROOT/scripts/run_scheduled_daily_learning_brief.py"
echo "Safety: outbound public-safe summary only; no Telegram commands or trading authority"

if [ "${1:-}" = "--load" ]; then
  launchctl bootout "$DOMAIN" "$TARGET" >/dev/null 2>&1 || true
  launchctl bootstrap "$DOMAIN" "$TARGET"
  launchctl enable "$DOMAIN/com.qadam.learning-brief"
  echo "Loaded: com.qadam.learning-brief"
else
  echo "Load after review: launchctl bootstrap $DOMAIN $TARGET"
fi
