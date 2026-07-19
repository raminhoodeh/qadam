#!/bin/sh
set -eu

TARGET="$HOME/Library/LaunchAgents/com.qadam.research-supervisor.plist"
if [ -f "$TARGET" ]; then
  rm "$TARGET"
fi
echo "Removed $TARGET. This script does not alter research artifacts."
