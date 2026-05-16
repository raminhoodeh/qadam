#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."

if command -v docker >/dev/null 2>&1; then
  docker compose up -d postgres chroma
elif command -v podman >/dev/null 2>&1; then
  podman compose up -d postgres chroma
else
  echo "No Docker-compatible runtime found. Install Docker Desktop, OrbStack, Podman, or Colima, then rerun." >&2
  exit 1
fi

python3 scripts/check_local_stores.py --require-running

if [[ -x ".venv/bin/python" ]]; then
  .venv/bin/python scripts/apply_migrations.py
  .venv/bin/python scripts/seed_durable_foundation.py
else
  python3 scripts/apply_migrations.py
  python3 scripts/seed_durable_foundation.py
fi

echo "local_stores_started=ok"
