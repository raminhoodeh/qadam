#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."

PYTHON_BIN="${QADAM_PYTHON:-python3}"
if [[ -x ".venv/bin/python" ]]; then
  PYTHON_BIN="${QADAM_PYTHON:-.venv/bin/python}"
fi

STAGE="all"
DRY_RUN=0

usage() {
  cat <<'EOF'
Usage: scripts/run_pre_phase3_operational_routine.sh [--stage STAGE] [--dry-run]

Stages:
  all                  Run the full pre-Phase-3 local routine.
  local-startup        Verify foundation, stores, registries, Agent OS, and data spine.
  source-refresh       Refresh source heartbeat and read-only adapter posture.
  durable-replay       Start/check local Postgres/Timescale durable replay.
  shadow-intelligence  Run durable Phase 2 shadow intelligence checks.
  safety-chain         Verify Signal Integrity through dry-run paper receipt.
  cockpit-export       Export and validate the public-safe cockpit snapshot.
  dashboard            Verify static dashboard render contracts.
  secret-scan          Scan committed surfaces for obvious secret values.
  phase3-provider-ledger
                       Verify Phase 3 provider readiness ledger.
  phase3-local-simulator
                       Verify Phase 3 local simulator track.
  phase3-qctrl         Verify Phase 3 Q-CTRL metadata-only readiness.
  phase3-hardware-stubs
                       Verify Phase 3 IBM/AWS hardware provider stubs.
  phase3-scheduler     Verify Phase 3 scheduler dry-run contract.
  phase3-oracle        Verify Phase 3 oracle input/output contracts.
  phase3-quantum       Run all Phase 3 quantum readiness checks.
  phase3-readiness     Run the full pre-Phase-3 routine plus Phase 3 readiness.

Safety defaults:
  Telegram remains dry-run/notify-only.
  TradingView remains observed-only.
  Yahoo Finance remains read-only supplemental market confirmation.
  Preference/PREF MCP remains status/catalog/sample/provenance-only unless explicit later stages enable live checks.
  Quantum remains local/classical scaffold only; no hardware jobs are submitted.
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --stage)
      STAGE="${2:-}"
      shift 2
      ;;
    --dry-run)
      DRY_RUN=1
      shift
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "pre_phase3_routine_error=unknown_argument:$1" >&2
      usage >&2
      exit 2
      ;;
  esac
done

run_cmd() {
  if [[ "${DRY_RUN}" == "1" ]]; then
    printf 'pre_phase3_dry_run_command='
    printf '%q ' "$@"
    printf '\n'
    return 0
  fi
  printf 'pre_phase3_command='
  printf '%q ' "$@"
  printf '\n'
  "$@"
}

run_secret_scan() {
  local secret_pattern
  secret_pattern='(ghp_[A-Za-z0-9_]{20,}|vcp_[A-Za-z0-9_]{20,}|pref_agent_[A-Za-z0-9_-]{12,}|AIza[0-9A-Za-z_-]{20,}|sb_secret_[0-9A-Za-z_-]{12,}|sk-[A-Za-z0-9_-]{20,}|[0-9]{6,}:[A-Za-z0-9_-]{20,}|(QCTRL_API_KEY|NASA_FIRMS_API_KEY|ALPACA_API_SECRET|KALSHI_API_SECRET|TELEGRAM_BOT_TOKEN|X_BEARER_TOKEN|PREFERENCE_API_KEY)=[A-Za-z0-9_-]{8,})'
  if [[ "${DRY_RUN}" == "1" ]]; then
    echo "pre_phase3_dry_run_command=rg -n <secret-pattern> docs orchestrator scripts README.md .env.example landing-page-repo"
    return 0
  fi
  set +e
  rg -n "${secret_pattern}" docs orchestrator scripts README.md .env.example landing-page-repo
  local status=$?
  set -e
  if [[ "${status}" == "0" ]]; then
    echo "pre_phase3_secret_scan=failed"
    return 1
  fi
  if [[ "${status}" == "1" ]]; then
    echo "pre_phase3_secret_scan=ok"
    return 0
  fi
  echo "pre_phase3_secret_scan=error:${status}"
  return "${status}"
}

stage_local_startup() {
  echo "pre_phase3_stage=local-startup"
  run_cmd "${PYTHON_BIN}" scripts/check_foundation.py
  run_cmd "${PYTHON_BIN}" scripts/check_event_log.py
  run_cmd "${PYTHON_BIN}" scripts/check_local_stores.py
  run_cmd "${PYTHON_BIN}" scripts/check_registries.py
  run_cmd "${PYTHON_BIN}" scripts/check_phase1_agent_os.py
  run_cmd "${PYTHON_BIN}" scripts/check_phase1_data_spine.py
  run_cmd "${PYTHON_BIN}" scripts/check_yahoo_finance_adapter.py
  run_cmd "${PYTHON_BIN}" scripts/check_preference_mcp_identity.py
  run_cmd "${PYTHON_BIN}" scripts/check_preference_tool_catalog.py
  run_cmd "${PYTHON_BIN}" scripts/check_preference_mcp_adapter.py
  run_cmd "${PYTHON_BIN}" scripts/check_preference_provenance.py
  run_cmd "${PYTHON_BIN}" scripts/check_preference_domain_packs.py
  run_cmd "${PYTHON_BIN}" scripts/check_preference_shadow_context.py
}

stage_source_refresh() {
  echo "pre_phase3_stage=source-refresh"
  run_cmd "${PYTHON_BIN}" scripts/run_source_heartbeat.py
  run_cmd "${PYTHON_BIN}" scripts/check_phase1_live_adapters.py
  run_cmd "${PYTHON_BIN}" scripts/check_phase1_live_source_hardening.py
  run_cmd "${PYTHON_BIN}" scripts/check_trust_score_seed.py
  run_cmd "${PYTHON_BIN}" scripts/check_tradingview_alerts.py
  run_cmd "${PYTHON_BIN}" scripts/check_yahoo_finance_adapter.py
}

stage_durable_replay() {
  echo "pre_phase3_stage=durable-replay"
  run_cmd ./scripts/start_postgres_timescale_ingestion.sh
  run_cmd "${PYTHON_BIN}" scripts/check_postgres_timescale_ingestion.py --require-live
  run_cmd "${PYTHON_BIN}" scripts/check_postgres_timescale_replay.py --require-full-source-coverage
  run_cmd "${PYTHON_BIN}" scripts/check_phase2_durable_replay_cycle.py
  run_cmd "${PYTHON_BIN}" scripts/check_strategy_lead_durable_context.py
}

stage_shadow_intelligence() {
  echo "pre_phase3_stage=shadow-intelligence"
  run_cmd "${PYTHON_BIN}" scripts/check_shadow_intelligence.py
  run_cmd "${PYTHON_BIN}" scripts/check_local_research_analyst.py
  run_cmd "${PYTHON_BIN}" scripts/run_phase2_shadow_cycle.py --durable-replay
}

stage_safety_chain() {
  echo "pre_phase3_stage=safety-chain"
  run_cmd "${PYTHON_BIN}" scripts/check_signal_integrity_gate.py
  run_cmd "${PYTHON_BIN}" scripts/check_risk_agent_policy_router.py
  run_cmd "${PYTHON_BIN}" scripts/check_execution_policy_router.py
  run_cmd "${PYTHON_BIN}" scripts/check_staged_paper_order_contract.py
  run_cmd "${PYTHON_BIN}" scripts/check_broker_reconciliation_contract.py
  run_cmd "${PYTHON_BIN}" scripts/check_paper_submit_receipt_contract.py
}

stage_cockpit_export() {
  echo "pre_phase3_stage=cockpit-export"
  run_cmd "${PYTHON_BIN}" scripts/export_cockpit_status.py
  run_cmd "${PYTHON_BIN}" scripts/check_cockpit_status.py
  run_cmd git -C landing-page-repo status --short
}

stage_dashboard() {
  echo "pre_phase3_stage=dashboard"
  run_cmd node --check landing-page-repo/dashboard.js
  run_cmd node scripts/check_dashboard_renderer.js
  run_cmd node scripts/check_dashboard_watching_view.js
  run_cmd node scripts/check_dashboard_cognition_view.js
  run_cmd node scripts/check_dashboard_mission_control.js
  run_cmd node scripts/check_dashboard_system_map.js
  run_cmd node scripts/check_dashboard_durable_spine.js
  run_cmd node scripts/check_dashboard_acceptance.js
}

stage_secret_scan() {
  echo "pre_phase3_stage=secret-scan"
  run_secret_scan
}

stage_phase3_provider_ledger() {
  echo "pre_phase3_stage=phase3-provider-ledger"
  run_cmd "${PYTHON_BIN}" scripts/check_quantum_provider_readiness.py
}

stage_phase3_local_simulator() {
  echo "pre_phase3_stage=phase3-local-simulator"
  run_cmd "${PYTHON_BIN}" scripts/check_quantum_local_simulator.py
}

stage_phase3_qctrl() {
  echo "pre_phase3_stage=phase3-qctrl"
  run_cmd "${PYTHON_BIN}" scripts/check_qctrl_readiness.py
}

stage_phase3_hardware_stubs() {
  echo "pre_phase3_stage=phase3-hardware-stubs"
  run_cmd "${PYTHON_BIN}" scripts/check_quantum_hardware_provider_stubs.py
}

stage_phase3_scheduler() {
  echo "pre_phase3_stage=phase3-scheduler"
  run_cmd "${PYTHON_BIN}" scripts/check_quantum_scheduler_dry_run.py
}

stage_phase3_oracle() {
  echo "pre_phase3_stage=phase3-oracle"
  run_cmd "${PYTHON_BIN}" scripts/check_quantum_oracle_input_contract.py
  run_cmd "${PYTHON_BIN}" scripts/check_quantum_oracle.py
  run_cmd "${PYTHON_BIN}" scripts/check_quantum_oracle_output_routing.py
}

stage_phase3_quantum() {
  echo "pre_phase3_stage=phase3-quantum"
  stage_phase3_provider_ledger
  stage_phase3_local_simulator
  stage_phase3_qctrl
  stage_phase3_hardware_stubs
  stage_phase3_scheduler
  stage_phase3_oracle
}

stage_all_pre_phase3() {
  stage_local_startup
  stage_source_refresh
  stage_durable_replay
  stage_shadow_intelligence
  stage_safety_chain
  stage_cockpit_export
  stage_dashboard
  stage_secret_scan
}

stage_phase3_readiness() {
  echo "pre_phase3_stage=phase3-readiness"
  stage_all_pre_phase3
  stage_phase3_quantum
  stage_cockpit_export
  stage_dashboard
  stage_secret_scan
}

run_stage() {
  case "$1" in
    local-startup) stage_local_startup ;;
    source-refresh) stage_source_refresh ;;
    durable-replay) stage_durable_replay ;;
    shadow-intelligence) stage_shadow_intelligence ;;
    safety-chain) stage_safety_chain ;;
    cockpit-export) stage_cockpit_export ;;
    dashboard) stage_dashboard ;;
    secret-scan) stage_secret_scan ;;
    phase3-provider-ledger) stage_phase3_provider_ledger ;;
    phase3-provider-readiness) stage_phase3_provider_ledger ;;
    phase3-local-simulator) stage_phase3_local_simulator ;;
    phase3-qctrl) stage_phase3_qctrl ;;
    phase3-hardware-stubs) stage_phase3_hardware_stubs ;;
    phase3-scheduler) stage_phase3_scheduler ;;
    phase3-oracle) stage_phase3_oracle ;;
    phase3-quantum) stage_phase3_quantum ;;
    phase3-readiness) stage_phase3_readiness ;;
    all) stage_all_pre_phase3 ;;
    *)
      echo "pre_phase3_routine_error=unknown_stage:$1" >&2
      usage >&2
      exit 2
      ;;
  esac
}

run_stage "${STAGE}"
echo "pre_phase3_routine=ok"
