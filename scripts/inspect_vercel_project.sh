#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
COCKPIT_DIR="$ROOT/cockpit"
LOCAL_VERCEL_ENV="$ROOT/data/runtime/vercel.env"
export npm_config_cache="${npm_config_cache:-$ROOT/data/runtime/npm-cache}"
export QADAM_VERCEL_HOME="${QADAM_VERCEL_HOME:-$ROOT/data/runtime/vercel-home}"
export HOME="$QADAM_VERCEL_HOME"
export XDG_CACHE_HOME="${XDG_CACHE_HOME:-$ROOT/data/runtime/xdg-cache}"
export XDG_CONFIG_HOME="${XDG_CONFIG_HOME:-$ROOT/data/runtime/xdg-config}"
export VERCEL_TELEMETRY_DISABLED="${VERCEL_TELEMETRY_DISABLED:-1}"
mkdir -p "$npm_config_cache" "$HOME" "$XDG_CACHE_HOME" "$XDG_CONFIG_HOME"

if [[ -f "$LOCAL_VERCEL_ENV" ]]; then
  # shellcheck disable=SC1090
  source "$LOCAL_VERCEL_ENV"
fi

if [[ -z "${VERCEL_TOKEN:-}" ]]; then
  echo "VERCEL_TOKEN is not set. Export it in your shell or load it from your local secret store." >&2
  exit 1
fi

cd "$COCKPIT_DIR"

npx vercel project inspect --token "$VERCEL_TOKEN"
