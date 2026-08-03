#!/bin/sh
set -eu

LABEL="com.qadam.operator-exploratory-exit-manager"
DOMAIN="gui/$(id -u)"
launchctl print "$DOMAIN/$LABEL"
