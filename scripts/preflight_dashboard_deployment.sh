#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

say() {
  printf '[qadam-preflight] %s\n' "$*"
}

run_with_retry() {
  local attempts="$1"
  shift
  local attempt=1
  until "$@"; do
    if (( attempt >= attempts )); then
      return 1
    fi
    say "Retrying failed command (${attempt}/${attempts}): $*"
    sleep 10
    attempt=$((attempt + 1))
  done
}

long_backtest_lock_active() {
  "$PYTHON_BIN" -c '
import json
import os
from pathlib import Path

runtime_dir = Path(os.environ.get("QADAM_RUNTIME_DIR", "data/runtime"))
path = runtime_dir / "qadam_long_backtest_lock.json"
try:
    payload = json.loads(path.read_text(encoding="utf-8"))
except (OSError, json.JSONDecodeError):
    raise SystemExit(1)

active = (
    payload.get("lock_type") == "qadam_next_generation_whole_universe_backfill_backtest"
    and payload.get("status") == "active"
    and payload.get("paperops_autonomous_runner_paused") is True
    and payload.get("paperops_watch_only_mode") is True
)
raise SystemExit(0 if active else 1)
'
}

cd "$ROOT"

PYTHON_BIN="${QADAM_PYTHON:-python3}"
if [[ -x ".venv/bin/python" ]]; then
  PYTHON_BIN="${QADAM_PYTHON:-.venv/bin/python}"
fi
DASHBOARD_SITE_ROOT="${QADAM_DASHBOARD_SITE_ROOT:-${ROOT}/landing-page-repo}"
if [[ "${DASHBOARD_SITE_ROOT}" != /* ]]; then
  DASHBOARD_SITE_ROOT="${ROOT}/${DASHBOARD_SITE_ROOT}"
fi
DASHBOARD_SITE_ROOT="$(cd "${DASHBOARD_SITE_ROOT}" && pwd)"

# Older dashboard acceptance checks resolve the site through the historical
# repo-local `landing-page-repo` path. When deployment supplies an isolated,
# committed dashboard worktree, bridge that path to the exact release tree so
# every checker inspects the same immutable candidate. Never replace an
# existing checkout, and remove only the bridge created by this preflight.
LEGACY_DASHBOARD_SITE_ROOT="${ROOT}/landing-page-repo"
DASHBOARD_SITE_BRIDGE_CREATED=0
DASHBOARD_SITE_BRIDGE_TARGET=""
cleanup_dashboard_site_bridge() {
  if [[ "${DASHBOARD_SITE_BRIDGE_CREATED}" != "1" ]]; then
    return 0
  fi
  if [[ ! -L "${LEGACY_DASHBOARD_SITE_ROOT}" ]]; then
    say "Dashboard compatibility bridge disappeared before cleanup."
    return 1
  fi
  if [[ "$(readlink "${LEGACY_DASHBOARD_SITE_ROOT}")" != "${DASHBOARD_SITE_BRIDGE_TARGET}" ]]; then
    say "Dashboard compatibility bridge target changed; refusing to remove it."
    return 1
  fi
  unlink "${LEGACY_DASHBOARD_SITE_ROOT}"
  DASHBOARD_SITE_BRIDGE_CREATED=0
}
trap cleanup_dashboard_site_bridge EXIT
trap 'exit 129' HUP
trap 'exit 130' INT
trap 'exit 143' TERM

if [[ "${DASHBOARD_SITE_ROOT}" != "${LEGACY_DASHBOARD_SITE_ROOT}" ]]; then
  if [[ -e "${LEGACY_DASHBOARD_SITE_ROOT}" || -L "${LEGACY_DASHBOARD_SITE_ROOT}" ]]; then
    # Production deploys start from the normal dashboard checkout and validate
    # an isolated worktree of the same release. Older checks still resolve the
    # normal path, so accept it only when both clean trees are byte-identical.
    if ! git -C "${LEGACY_DASHBOARD_SITE_ROOT}" rev-parse --is-inside-work-tree >/dev/null 2>&1; then
      say "Historical dashboard path exists but is not a Git worktree."
      exit 1
    fi
    release_commit="$(git -C "${DASHBOARD_SITE_ROOT}" rev-parse HEAD)"
    legacy_commit="$(git -C "${LEGACY_DASHBOARD_SITE_ROOT}" rev-parse HEAD)"
    release_tree="$(git -C "${DASHBOARD_SITE_ROOT}" rev-parse 'HEAD^{tree}')"
    legacy_tree="$(git -C "${LEGACY_DASHBOARD_SITE_ROOT}" rev-parse 'HEAD^{tree}')"
    if [[ "${legacy_commit}" != "${release_commit}" || "${legacy_tree}" != "${release_tree}" ]]; then
      say "Historical dashboard checkout does not match the isolated release tree."
      exit 1
    fi
    if [[ -n "$(git -C "${LEGACY_DASHBOARD_SITE_ROOT}" status --porcelain --untracked-files=all)" ]]; then
      say "Historical dashboard checkout is dirty and cannot stand in for the isolated release tree."
      exit 1
    fi
    say "Historical dashboard checkout matches the isolated release tree."
  else
    ln -s "${DASHBOARD_SITE_ROOT}" "${LEGACY_DASHBOARD_SITE_ROOT}"
    DASHBOARD_SITE_BRIDGE_TARGET="${DASHBOARD_SITE_ROOT}"
    DASHBOARD_SITE_BRIDGE_CREATED=1
  fi
fi
say "Validating dashboard release tree ${DASHBOARD_SITE_ROOT}"

say "Refreshing dry-run receipt contract"
"$PYTHON_BIN" scripts/check_paper_submit_receipt_contract.py
run_with_retry 5 "$PYTHON_BIN" scripts/check_alpaca_paper_mirror.py --live
say "Validating the latest PaperOps summary without producing orders"
"$PYTHON_BIN" scripts/run_paperops_autonomous_pass.py --report-only
"$PYTHON_BIN" scripts/check_paperops_completion_gaps.py
"$PYTHON_BIN" scripts/check_evidence_packet_runtime.py
"$PYTHON_BIN" scripts/check_qsase_evidence_quality_engine.py
"$PYTHON_BIN" scripts/check_qsase_dashboard_view_model.py
"$PYTHON_BIN" scripts/check_qsase_pattern_to_paper_workflow.py
"$PYTHON_BIN" scripts/check_qadam_end_to_end_lifecycle.py
"$PYTHON_BIN" scripts/check_qadam_operator_dashboard.py
node scripts/check_dashboard_ten_stage_lifecycle.js
"$PYTHON_BIN" scripts/check_source_evidence_acceptance.py
"$PYTHON_BIN" scripts/check_reddit_narrative_proxy.py --live
"$PYTHON_BIN" scripts/check_edge_tracker.py
"$PYTHON_BIN" scripts/check_edge_pattern_ledger.py
"$PYTHON_BIN" scripts/check_quantum_mandatory_review_gate.py
"$PYTHON_BIN" scripts/check_pattern_recognition_engine.py
"$PYTHON_BIN" scripts/check_edge_memory_ledger.py
"$PYTHON_BIN" scripts/check_strategy_update_record.py
"$PYTHON_BIN" scripts/check_hypothesis_lifecycle.py
"$PYTHON_BIN" scripts/check_strategy_weight_updates.py
"$PYTHON_BIN" scripts/check_quantum_meta_review.py
"$PYTHON_BIN" scripts/check_self_improvement_proposals.py
"$PYTHON_BIN" scripts/check_promotion_gates.py
"$PYTHON_BIN" scripts/check_daily_edge_findings_brief.py
"$PYTHON_BIN" scripts/check_telegram_human_brief.py
"$PYTHON_BIN" scripts/check_daily_learning_automation.py
"$PYTHON_BIN" scripts/check_daily_edge_learning_acceptance.py
"$PYTHON_BIN" scripts/check_daily_edge_learning_safety_boundary.py
"$PYTHON_BIN" scripts/check_qsase_evidence_quality_engine.py
"$PYTHON_BIN" scripts/check_qsase_dashboard_view_model.py
"$PYTHON_BIN" scripts/check_qsase_pattern_to_paper_workflow.py
"$PYTHON_BIN" scripts/check_cockpit_status.py
"$PYTHON_BIN" scripts/check_dashboard_portfolio_consistency.py
"$PYTHON_BIN" scripts/check_source_evidence_deployment_discipline.py
# Commit-time projections are intentionally immutable while runtime research
# continues to advance. Their schema, internal hashes, release binding, and
# frontend behavior are validated by the site-only Wave F/G/H, three-layer,
# interaction, and release-manifest gates below. Re-comparing them here against
# mutable runtime inputs would make a reproducible release fail whenever a
# normal research refresh completed during preflight.

say "Checking dashboard acceptance gate"
node --check scripts/check_dashboard_acceptance.js
node scripts/check_dashboard_acceptance.js

say "Checking deployment readiness gate"
"$PYTHON_BIN" scripts/check_codebase_upgrade_telegram_notification.py
"$PYTHON_BIN" scripts/check_telegram_message_specificity.py
node --check scripts/check_dashboard_deployment_readiness.js
node scripts/check_dashboard_deployment_readiness.js
node --check scripts/check_dashboard_d11o_deployment_discipline.js
node scripts/check_dashboard_d11o_deployment_discipline.js
"$PYTHON_BIN" scripts/sync_qadam_documentation_metadata.py --check
node --check scripts/check_protected_user_guide.js
node scripts/check_protected_user_guide.js
node --check scripts/check_non_homepage_regression_suite.js
node scripts/check_non_homepage_regression_suite.js
node --check scripts/check_non_homepage_deploy_discipline.js
node scripts/check_non_homepage_deploy_discipline.js

say "Checking dashboard current product contracts"
node "${DASHBOARD_SITE_ROOT}/scripts/check-active-discovery-trial.js"
node scripts/check_dashboard_quantum_edge_wave_f.js "${DASHBOARD_SITE_ROOT}"
node scripts/check_dashboard_quantum_edge_wave_g.js "${DASHBOARD_SITE_ROOT}"
node scripts/check_dashboard_quantum_edge_wave_h.js "${DASHBOARD_SITE_ROOT}"
node scripts/check_dashboard_quantum_edge_three_layer.js "${DASHBOARD_SITE_ROOT}"
node --check scripts/check_dashboard_quantum_edge_interactions.js
run_with_retry 3 node scripts/check_dashboard_quantum_edge_interactions.js --site-root "${DASHBOARD_SITE_ROOT}"
node scripts/check_dashboard_information_hierarchy.js
node scripts/check_dashboard_overhaul_overview.js
node scripts/check_dashboard_stage7_visibility.js
node scripts/check_dashboard_cc6_real_portfolio_timeline.js
node scripts/check_dashboard_edge_tracker.js
node scripts/check_dashboard_cc8_prune_docs_deploy.js
node scripts/check_dashboard_cc9_slop_repetition.js
node scripts/check_dashboard_pattern_discovery_quantum_review.js
node scripts/check_dashboard_decision_room_governance.js
node scripts/check_dashboard_qsase_public_frontend.js
node scripts/check_dashboard_passive_refresh_scroll.js
node scripts/check_dashboard_system_overview.js
node scripts/check_dashboard_order_monitor.js
node scripts/check_dashboard_renderer.js
node scripts/check_dashboard_live_bridge.js
node scripts/check_dashboard_watching_view.js
node scripts/check_dashboard_cognition_view.js
node scripts/check_dashboard_trade_board.js
node scripts/check_dashboard_money_panel.js
node scripts/check_dashboard_tradingview_source.js
node scripts/check_dashboard_communications.js
node scripts/check_dashboard_forum.js
node scripts/check_dashboard_d11l_visual_simplification.js
node scripts/check_dashboard_d11m_regression_acceptance.js
node scripts/check_dashboard_d11n_documentation_guide_alignment.js

say "Checking status exporters"
"$PYTHON_BIN" scripts/check_qsase_evidence_quality_engine.py
"$PYTHON_BIN" scripts/check_qsase_dashboard_view_model.py
"$PYTHON_BIN" scripts/check_qsase_pattern_to_paper_workflow.py
"$PYTHON_BIN" scripts/check_cockpit_status.py
"$PYTHON_BIN" scripts/check_dashboard_portfolio_consistency.py
"$PYTHON_BIN" scripts/check_live_bridge.py

say "Checking dashboard syntax and whitespace"
node --check "${DASHBOARD_SITE_ROOT}/api/cockpit-status.js"
node --check "${DASHBOARD_SITE_ROOT}/auth.js"
node --check "${DASHBOARD_SITE_ROOT}/dashboard.js"
node --check "${DASHBOARD_SITE_ROOT}/dashboard-release.js"
node --check "${DASHBOARD_SITE_ROOT}/quantum-edge-page.js"
node --check "${DASHBOARD_SITE_ROOT}/quantum-edge-wave-f.js"
node --check "${DASHBOARD_SITE_ROOT}/scripts/build-dashboard-release-manifest.js"
node --check "${DASHBOARD_SITE_ROOT}/scripts/check-active-discovery-trial.js"
node --check "${DASHBOARD_SITE_ROOT}/scripts/verify-dashboard-production-release.js"
git -C "${DASHBOARD_SITE_ROOT}" diff --check
git diff --check -- \
  README.md \
  landing-page-repo/api/cockpit-status.js \
  landing-page-repo/auth.css \
  landing-page-repo/auth.js \
  landing-page-repo/dashboard/index.html \
  landing-page-repo/dashboard.js \
  landing-page-repo/guide/index.html \
  landing-page-repo/login/index.html \
  landing-page-repo/non-homepage-layout.css \
  landing-page-repo/non-homepage-tokens.css \
  landing-page-repo/quantum-edge-page.css \
  landing-page-repo/quantum-edge-page.js \
  landing-page-repo/status/quantum-edge-page.json \
  landing-page-repo/scripts/deploy-vercel-production.sh \
  landing-page-repo/sign-up/index.html \
  landing-page-repo/whitepaper.css \
  landing-page-repo/whitepaper/index.html \
  orchestrator/cockpit_status.py \
  orchestrator/daily_edge_findings.py \
  orchestrator/daily_learning_automation.py \
  orchestrator/daily_telegram_learning_brief.py \
  orchestrator/edge_pattern_ledger.py \
  orchestrator/edge_tracker.py \
  orchestrator/edge_memory_ledger.py \
  orchestrator/hypothesis_lifecycle.py \
  orchestrator/paperops_completion_gaps.py \
  orchestrator/paperops_source_gap_visibility.py \
  orchestrator/pattern_recognition_engine.py \
  orchestrator/qadam_quantum_edge_page_view_model.py \
  orchestrator/qadam_wave_h_crude_oil_certification.py \
  orchestrator/quantum_mandatory_review_gate.py \
  orchestrator/quantum_meta_review.py \
  orchestrator/promotion_gates.py \
  orchestrator/self_improvement_proposals.py \
  orchestrator/strategy_weight_updates.py \
  orchestrator/strategy_update_record.py \
  orchestrator/telegram_codebase_upgrade_notifications.py \
  orchestrator/telegram_comms.py \
  orchestrator/telegram_daily_portfolio_digest.py \
  orchestrator/telegram_human_brief.py \
  orchestrator/telegram_message_quality.py \
  orchestrator/telegram_trade_notifications.py \
  orchestrator/reddit_narrative_proxy.py \
  scripts/check_codebase_upgrade_telegram_notification.py \
  scripts/check_daily_telegram_portfolio_digest.py \
  scripts/check_dashboard_communications.js \
  scripts/check_dashboard_quantum_edge_interactions.js \
  scripts/check_dashboard_quantum_edge_three_layer.js \
  scripts/check_dashboard_decision_room_governance.js \
  scripts/check_qadam_quantum_edge_page_view_model.py \
  scripts/check_qadam_wave_h_crude_oil_certification.py \
  scripts/check_dashboard_stage7_visibility.js \
  scripts/check_paperops_completion_gaps.py \
  scripts/check_daily_learning_automation.py \
  scripts/check_reddit_narrative_proxy.py \
  scripts/check_telegram_message_specificity.py \
  scripts/check_telegram_human_brief.py \
  scripts/run_daily_learning_automation.py \
  scripts/check_telegram_trade_notifications.py \
  scripts/send_codebase_upgrade_telegram_notification.py \
  tests/test_qadam_quantum_edge_page_view_model.py \
  tests/test_qadam_wave_h_crude_oil_certification.py \
  docs/qadam-dashboard-implementation-plan.md \
  docs/qadam-dashboard-navigation-ux-plan.md \
  docs/qadam-dashboard-overhaul-dx-1-ia-contract.json \
  docs/qadam-dashboard-overhaul-dx-1-ia-contract-audit-2026-05-25.md \
  docs/qadam-dashboard-overhaul-dx-2-copy-system.json \
  docs/qadam-dashboard-overhaul-dx-2-copy-system-audit-2026-05-25.md \
  docs/qadam-dashboard-overhaul-dx-3-view-model-audit-2026-05-25.md \
  docs/qadam-dashboard-overhaul-dx-4-segmented-shell-audit-2026-05-25.md \
  docs/qadam-dashboard-overhaul-dx-5-overview-audit-2026-05-25.md \
  docs/qadam-dashboard-overhaul-dx-6-trades-audit-2026-05-25.md \
  docs/qadam-dashboard-overhaul-dx-7-sources-audit-2026-05-25.md \
  docs/qadam-dashboard-overhaul-dx-8-reasoning-audit-2026-05-25.md \
  docs/qadam-dashboard-overhaul-dx-9-performance-audit-2026-05-25.md \
  docs/qadam-dashboard-overhaul-dx-10-operations-audit-2026-05-25.md \
  docs/qadam-dashboard-overhaul-dx-11-governance-audit-2026-05-25.md \
  docs/qadam-dashboard-overhaul-dx-12-responsive-audit-2026-05-25.md \
  docs/qadam-dashboard-d11a-information-diet-audit-2026-05-26.md \
  docs/qadam-dashboard-d11b-new-navigation-contract-2026-05-26.md \
  docs/qadam-dashboard-d11c-canonical-status-language-2026-05-26.md \
  docs/qadam-dashboard-d11d-single-safety-strip-2026-05-26.md \
  docs/qadam-dashboard-d11e-rebuild-overview-2026-05-26.md \
  docs/qadam-dashboard-d11f-trades-view-consolidation-2026-05-26.md \
  docs/qadam-dashboard-d11g-evidence-view-consolidation-2026-05-26.md \
  docs/qadam-dashboard-d11h-reasoning-view-consolidation-2026-05-26.md \
  docs/qadam-dashboard-d11i-operations-view-2026-05-26.md \
  docs/qadam-dashboard-d11j-tooltip-simplification-2026-05-26.md \
  docs/qadam-dashboard-d11k-view-model-refactor-2026-05-26.md \
  docs/qadam-dashboard-d11l-visual-simplification-2026-05-26.md \
  docs/qadam-dashboard-d11m-regression-and-acceptance-tests-2026-05-26.md \
  docs/qadam-dashboard-d11n-documentation-guide-alignment-2026-05-26.md \
  docs/qadam-dashboard-d11o-deployment-discipline-2026-05-26.md \
  docs/qadam-dashboard-d12-language-cleanup-2026-05-26.md \
  docs/qadam-dashboard-d13-health-language-and-ibm-readiness-2026-05-26.md \
  docs/qadam-paperops-completion-gaps-2026-06-20.md \
  scripts/check_dashboard_d13_health_language.js \
  scripts/check_dashboard_phase6_learning_loop.js \
  scripts/check_dashboard_rs9_learning_loop.js \
  scripts/check_dashboard_rs10_final_paper_autonomy.js \
  scripts/check_dashboard_cc6_real_portfolio_timeline.js \
  scripts/check_dashboard_edge_tracker.js \
  scripts/check_dashboard_live_bridge.js \
  scripts/check_dashboard_cc7_visual_a11y.js \
  scripts/check_dashboard_cc8_prune_docs_deploy.js \
  scripts/check_dashboard_cc9_slop_repetition.js \
  docs/qadam-dashboard-consolidation-cut-implementation-plan-2026-06-05.md \
  docs/qadam-dashboard-overhaul-master-implementation-plan.md \
  docs/README.md \
  docs/qadam-documentation-contract.json \
  docs/qadam-for-fund-managers.md \
  docs/qadam-user-guide.md \
  docs/qadam-whitepaper.md \
  cockpit/public/non-homepage-layout.css \
  cockpit/public/non-homepage-tokens.css \
  cockpit/public/whitepaper.css \
  cockpit/public/whitepaper/index.html \
  scripts/check_dashboard_acceptance.js \
  scripts/check_dashboard_deployment_readiness.js \
  scripts/check_dashboard_density_toggle.js \
  scripts/check_dashboard_navigation_ux.js \
  scripts/check_dashboard_panel_redesign.js \
  scripts/check_dashboard_section_explainers.js \
  scripts/check_dashboard_visual_system.js \
  scripts/check_dashboard_overhaul_ia_contract.js \
  scripts/check_dashboard_overhaul_copy_system.js \
  scripts/check_dashboard_overhaul_view_models.js \
  scripts/check_dashboard_overhaul_shell.js \
  scripts/check_dashboard_overhaul_overview.js \
  scripts/check_dashboard_overhaul_trades.js \
  scripts/check_dashboard_overhaul_sources.js \
  scripts/check_dashboard_overhaul_reasoning.js \
  scripts/check_dashboard_overhaul_performance.js \
  scripts/check_dashboard_overhaul_operations.js \
  scripts/check_dashboard_overhaul_governance.js \
  scripts/check_dashboard_decision_room_governance.js \
  scripts/check_dashboard_overhaul_responsive.js \
  scripts/check_dashboard_d11a_information_diet_audit.js \
  scripts/check_dashboard_d11b_new_navigation_contract.js \
  scripts/check_dashboard_d11c_canonical_status_language.js \
  scripts/check_dashboard_d11d_single_safety_strip.js \
  scripts/check_dashboard_d11e_rebuild_overview.js \
  scripts/check_dashboard_d11f_trades_view_consolidation.js \
  scripts/check_dashboard_d11g_evidence_view_consolidation.js \
  scripts/check_dashboard_d11h_reasoning_view_consolidation.js \
  scripts/check_dashboard_d11i_operations_view.js \
  scripts/check_dashboard_d11j_tooltip_simplification.js \
  scripts/check_dashboard_d11k_view_model_refactor.js \
  scripts/check_dashboard_d11l_visual_simplification.js \
  scripts/check_dashboard_d11m_regression_acceptance.js \
  scripts/check_dashboard_d11n_documentation_guide_alignment.js \
  scripts/check_dashboard_d11o_deployment_discipline.js \
  scripts/check_non_homepage_accessibility.js \
  scripts/check_non_homepage_auth_pages.js \
  scripts/check_non_homepage_dashboard_redesign.js \
  scripts/check_non_homepage_deploy_discipline.js \
  scripts/check_non_homepage_design_tokens.js \
  scripts/check_non_homepage_guide_redesign.js \
  scripts/check_non_homepage_layout_components.js \
  scripts/check_non_homepage_navigation_contract.js \
  scripts/check_non_homepage_regression_suite.js \
  scripts/check_non_homepage_whitepaper_redesign.js \
  scripts/check_qadam_documentation_parity.js \
  scripts/check_dashboard_d12_language_cleanup.js \
  scripts/check_protected_user_guide.js \
  scripts/sync_qadam_documentation_metadata.py \
  scripts/check_daily_edge_findings_brief.py \
  scripts/check_telegram_human_brief.py \
  scripts/check_daily_learning_automation.py \
  scripts/check_daily_edge_learning_acceptance.py \
  scripts/check_daily_edge_learning_safety_boundary.py \
  scripts/check_dashboard_portfolio_consistency.py \
  scripts/check_live_bridge.py \
  scripts/check_edge_tracker.py \
  scripts/check_edge_pattern_ledger.py \
  scripts/check_edge_memory_ledger.py \
  scripts/check_hypothesis_lifecycle.py \
  scripts/check_strategy_weight_updates.py \
  scripts/check_quantum_meta_review.py \
  scripts/check_self_improvement_proposals.py \
  scripts/check_promotion_gates.py \
  scripts/check_quantum_mandatory_review_gate.py \
  scripts/check_pattern_recognition_engine.py \
  scripts/check_strategy_update_record.py \
  scripts/preflight_dashboard_deployment.sh

cleanup_dashboard_site_bridge
trap - EXIT HUP INT TERM
say "Deployment preflight passed"
