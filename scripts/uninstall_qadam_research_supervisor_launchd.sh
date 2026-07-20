#!/bin/sh
set -eu

TARGET="$HOME/Library/LaunchAgents/com.qadam.research-supervisor.plist"
launchctl bootout "gui/$(id -u)/com.qadam.research-supervisor" >/dev/null 2>&1 || true
if [ -f "$TARGET" ]; then
  rm "$TARGET"
fi
echo "Retired $TARGET. The consolidated Qadam operator service owns scheduling."
echo "Research artifacts were not altered."
