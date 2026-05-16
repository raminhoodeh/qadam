#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")"

PYTHON_BIN="${QADAM_PYTHON:-python3}"
if [[ -x ".venv/bin/python" ]]; then
  PYTHON_BIN="${QADAM_PYTHON:-.venv/bin/python}"
fi

"$PYTHON_BIN" scripts/check_foundation.py
"$PYTHON_BIN" scripts/check_event_log.py
"$PYTHON_BIN" scripts/check_local_stores.py
"$PYTHON_BIN" scripts/check_registries.py
"$PYTHON_BIN" scripts/check_chroma_store.py
"$PYTHON_BIN" scripts/check_source_heartbeat.py
"$PYTHON_BIN" scripts/check_gdelt_adapter.py
"$PYTHON_BIN" scripts/check_oref_adapter.py
"$PYTHON_BIN" scripts/check_fred_adapter.py
"$PYTHON_BIN" scripts/check_rss_adapter.py

if [[ "${QADAM_START_ORCHESTRATOR:-0}" == "1" ]]; then
  "$PYTHON_BIN" -m orchestrator.main
else
  echo "Foundation check passed. Set QADAM_START_ORCHESTRATOR=1 to start the health endpoint."
fi
