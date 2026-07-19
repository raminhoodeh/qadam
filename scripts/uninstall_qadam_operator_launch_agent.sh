#!/bin/sh
set -eu

TARGET="$HOME/Library/LaunchAgents/com.qadam.operator.plist"
echo "If loaded, stop explicitly first: launchctl bootout gui/$(id -u)/com.qadam.operator"
if [ -f "$TARGET" ]; then
  rm "$TARGET"
fi
echo "Removed $TARGET. Runtime evidence and the paper-trial calendar were not changed."
