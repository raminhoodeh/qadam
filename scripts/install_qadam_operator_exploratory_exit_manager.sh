#!/bin/sh
set -eu

ROOT=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
LABEL="com.qadam.operator-exploratory-exit-manager"
DOMAIN="gui/$(id -u)"
TEMPLATE="$ROOT/ops/launchd/$LABEL.plist.template"
TARGET="$HOME/Library/LaunchAgents/$LABEL.plist"

mkdir -p "$HOME/Library/LaunchAgents"
sed "s|__QADAM_ROOT__|$ROOT|g" "$TEMPLATE" > "$TARGET"
chmod 600 "$TARGET"
plutil -lint "$TARGET"

launchctl bootout "$DOMAIN/$LABEL" >/dev/null 2>&1 || true
launchctl bootstrap "$DOMAIN" "$TARGET"
launchctl enable "$DOMAIN/$LABEL"

echo "installed=$TARGET"
echo "label=$LABEL"
echo "safety=exact approved sleeve, paper-only, risk-reducing exits only"
echo "cadence_seconds=60"
