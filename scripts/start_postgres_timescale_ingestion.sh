#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."

PYTHON_BIN="${QADAM_PYTHON:-python3}"
if [[ -x ".venv/bin/python" ]]; then
  PYTHON_BIN="${QADAM_PYTHON:-.venv/bin/python}"
fi

if command -v docker >/dev/null 2>&1; then
  RUNTIME=(docker compose)
elif command -v podman >/dev/null 2>&1; then
  RUNTIME=(podman compose)
else
  echo "postgres_timescale_runtime_status=missing"
  echo "postgres_timescale_runtime_required=docker_or_podman_compatible_cli"
  echo "postgres_timescale_next_step=Install Docker Desktop, OrbStack, Podman, or Colima, then rerun scripts/start_postgres_timescale_ingestion.sh."
  exit 1
fi

echo "postgres_timescale_runtime_status=found"
"${RUNTIME[@]}" up -d postgres

"$PYTHON_BIN" scripts/wait_for_postgres.py --timeout="${QADAM_POSTGRES_WAIT_SECONDS:-90}"
"$PYTHON_BIN" scripts/apply_migrations.py
"$PYTHON_BIN" scripts/seed_durable_foundation.py
"$PYTHON_BIN" scripts/run_test_ingestion_durable.py --all
"$PYTHON_BIN" scripts/check_postgres_timescale_ingestion.py --require-live
"$PYTHON_BIN" scripts/check_postgres_timescale_replay.py --require-full-source-coverage

echo "postgres_timescale_durable_ingestion=ok"
echo "postgres_timescale_boundary=Durable replayable observations are local-only and cannot create signals or orders."
