#!/bin/sh
set -eu

ROOT=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
LABEL="com.qadam.telegram-readonly-interface"
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
echo "Cadence: every 30 seconds on the shared locked Telegram update rail"
echo "Authority: read-only group queries; no trade, repair, broker, proof, or capital commands"

if [ "$LOAD" = true ]; then
  launchctl bootout "gui/$(id -u)/$LABEL" >/dev/null 2>&1 || true
  launchctl bootstrap "gui/$(id -u)" "$TARGET"
  "$ROOT/.venv/bin/python" "$ROOT/scripts/run_qadam_telegram_readonly_interface.py" \
    --register-commands --announce
  echo "Loaded: $LABEL"
else
  echo "Not loaded. After review: $0 --load"
fi
