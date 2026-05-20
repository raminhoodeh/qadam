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
"$PYTHON_BIN" scripts/check_agent_manifests.py
"$PYTHON_BIN" scripts/check_agent_runtime.py
"$PYTHON_BIN" scripts/check_phase1_agent_os.py
"$PYTHON_BIN" scripts/check_shadow_intelligence.py
"$PYTHON_BIN" scripts/check_signal_integrity_gate.py
"$PYTHON_BIN" scripts/check_risk_agent_policy_router.py
"$PYTHON_BIN" scripts/check_execution_policy_router.py
"$PYTHON_BIN" scripts/check_staged_paper_order_contract.py
"$PYTHON_BIN" scripts/check_llm_provider_probes.py
"$PYTHON_BIN" scripts/check_local_research_analyst.py
"$PYTHON_BIN" scripts/check_trade_intent.py
"$PYTHON_BIN" scripts/check_paper_account.py
"$PYTHON_BIN" scripts/check_tradingview_alerts.py
"$PYTHON_BIN" scripts/check_chroma_store.py
"$PYTHON_BIN" scripts/check_source_heartbeat.py
"$PYTHON_BIN" scripts/check_phase1_data_spine.py
"$PYTHON_BIN" scripts/check_phase1_live_adapters.py
"$PYTHON_BIN" scripts/check_phase1_live_source_hardening.py
"$PYTHON_BIN" scripts/check_historical_backfills.py
"$PYTHON_BIN" scripts/check_trust_score_seed.py
"$PYTHON_BIN" scripts/check_postgres_timescale_ingestion.py
"$PYTHON_BIN" scripts/check_gdelt_adapter.py
"$PYTHON_BIN" scripts/check_oref_adapter.py
"$PYTHON_BIN" scripts/check_nasa_firms_adapter.py
"$PYTHON_BIN" scripts/check_fred_adapter.py
"$PYTHON_BIN" scripts/check_rss_adapter.py
"$PYTHON_BIN" scripts/check_cockpit_status.py

if [[ "${QADAM_START_ORCHESTRATOR:-0}" == "1" ]]; then
  "$PYTHON_BIN" -m orchestrator.main
else
  echo "Foundation check passed. Set QADAM_START_ORCHESTRATOR=1 to start the health endpoint."
fi
