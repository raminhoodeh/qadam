#!/bin/sh
set -eu

ROOT=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
TEMPLATE="$ROOT/ops/launchd/com.qadam.research-supervisor.plist.template"
TARGET="$HOME/Library/LaunchAgents/com.qadam.research-supervisor.plist"

mkdir -p "$HOME/Library/LaunchAgents"
sed "s|__QADAM_ROOT__|$ROOT|g" "$TEMPLATE" > "$TARGET"
echo "Installed template at $TARGET. It is not loaded; use launchctl bootstrap explicitly."
