#!/bin/sh
set -eu

launchctl print "gui/$(id -u)/com.qadam.research-supervisor"
