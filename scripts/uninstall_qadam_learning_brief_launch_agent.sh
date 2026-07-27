#!/bin/sh
set -eu

TARGET="$HOME/Library/LaunchAgents/com.qadam.learning-brief.plist"
DOMAIN="gui/$(id -u)"

launchctl bootout "$DOMAIN" "$TARGET" >/dev/null 2>&1 || true
rm -f "$TARGET"
echo "Removed: com.qadam.learning-brief"
