#!/bin/sh
set -eu

LABEL="com.qadam.operator-exploratory-exit-manager"
DOMAIN="gui/$(id -u)"
TARGET="$HOME/Library/LaunchAgents/$LABEL.plist"
launchctl bootout "$DOMAIN/$LABEL" >/dev/null 2>&1 || true
rm -f "$TARGET"
echo "uninstalled=$LABEL"
