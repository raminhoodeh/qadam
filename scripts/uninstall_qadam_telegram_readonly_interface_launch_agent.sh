#!/bin/sh
set -eu

LABEL="com.qadam.telegram-readonly-interface"
TARGET="$HOME/Library/LaunchAgents/$LABEL.plist"

launchctl bootout "gui/$(id -u)/$LABEL" >/dev/null 2>&1 || true
rm -f "$TARGET"
echo "Removed: $LABEL"
