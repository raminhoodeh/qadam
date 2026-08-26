#!/bin/sh
set -eu

LABEL="com.qadam.reliability-critic"
TARGET="$HOME/Library/LaunchAgents/$LABEL.plist"

launchctl bootout "gui/$(id -u)/$LABEL" >/dev/null 2>&1 || true
rm -f "$TARGET"
echo "Removed: $LABEL"
