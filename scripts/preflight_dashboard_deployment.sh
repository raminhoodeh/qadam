#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

say() {
  printf '[qadam-preflight] %s\n' "$*"
}

cd "$ROOT"

PYTHON_BIN="${QADAM_PYTHON:-python3}"
if [[ -x ".venv/bin/python" ]]; then
  PYTHON_BIN="${QADAM_PYTHON:-.venv/bin/python}"
fi

say "Refreshing dry-run receipt contract"
"$PYTHON_BIN" scripts/check_paper_submit_receipt_contract.py
"$PYTHON_BIN" scripts/check_paperops_paper_lifecycle_poller.py --poll-paper-orders
"$PYTHON_BIN" scripts/check_alpaca_paper_mirror.py --live
"$PYTHON_BIN" scripts/check_paperops_paper_exit_path.py
"$PYTHON_BIN" scripts/check_paper_operational_cycle.py
"$PYTHON_BIN" scripts/check_paperops_30_day_operations.py
"$PYTHON_BIN" scripts/check_evidence_packet_runtime.py
"$PYTHON_BIN" scripts/check_cockpit_status.py

say "Checking dashboard acceptance gate"
node --check scripts/check_dashboard_acceptance.js
node scripts/check_dashboard_acceptance.js

say "Checking deployment readiness gate"
"$PYTHON_BIN" scripts/check_codebase_upgrade_telegram_notification.py
"$PYTHON_BIN" scripts/check_telegram_message_specificity.py
node --check scripts/check_dashboard_deployment_readiness.js
node scripts/check_dashboard_deployment_readiness.js

say "Checking dashboard phase contracts"
node scripts/check_dashboard_density_toggle.js
node scripts/check_dashboard_navigation_ux.js
node scripts/check_dashboard_panel_redesign.js
node scripts/check_dashboard_section_explainers.js
node scripts/check_dashboard_visual_system.js
node scripts/check_dashboard_page_architecture.js
node scripts/check_dashboard_information_hierarchy.js
node scripts/check_dashboard_overhaul_ia_contract.js
node scripts/check_dashboard_overhaul_copy_system.js
node scripts/check_dashboard_overhaul_view_models.js
node scripts/check_dashboard_overhaul_shell.js
node scripts/check_dashboard_overhaul_overview.js
node scripts/check_dashboard_overhaul_trades.js
node scripts/check_dashboard_overhaul_sources.js
node scripts/check_dashboard_overhaul_reasoning.js
node scripts/check_dashboard_overhaul_performance.js
node scripts/check_dashboard_overhaul_operations.js
node scripts/check_dashboard_overhaul_governance.js
node scripts/check_dashboard_overhaul_responsive.js
node scripts/check_dashboard_d11a_information_diet_audit.js
node scripts/check_dashboard_d11b_new_navigation_contract.js
node scripts/check_dashboard_d11c_canonical_status_language.js
node scripts/check_dashboard_d11d_single_safety_strip.js
node scripts/check_dashboard_d11e_rebuild_overview.js
node scripts/check_dashboard_d11f_trades_view_consolidation.js
node scripts/check_dashboard_d11g_evidence_view_consolidation.js
node scripts/check_dashboard_d11h_reasoning_view_consolidation.js
node scripts/check_dashboard_d11i_operations_view.js
node scripts/check_dashboard_d11j_tooltip_simplification.js
node scripts/check_dashboard_d11k_view_model_refactor.js
node scripts/check_dashboard_d11l_visual_simplification.js
node scripts/check_dashboard_d11m_regression_acceptance.js
node scripts/check_dashboard_d11n_documentation_guide_alignment.js
node scripts/check_dashboard_d11o_deployment_discipline.js
node scripts/check_dashboard_d12_language_cleanup.js
node scripts/check_dashboard_d13_health_language.js
node scripts/check_dashboard_rs8_mission_control.js
node scripts/check_dashboard_phase6_learning_loop.js
node scripts/check_dashboard_rs9_learning_loop.js
node scripts/check_dashboard_rs10_final_paper_autonomy.js
node scripts/check_dashboard_system_map.js
node scripts/check_dashboard_durable_spine.js
node scripts/check_dashboard_cc6_real_portfolio_timeline.js
node scripts/check_dashboard_cc7_visual_a11y.js
node scripts/check_dashboard_cc8_prune_docs_deploy.js
node scripts/check_dashboard_cc9_slop_repetition.js
node scripts/check_dashboard_renderer.js
node scripts/check_dashboard_live_bridge.js
node scripts/check_dashboard_watching_view.js
node scripts/check_dashboard_cognition_view.js
node scripts/check_dashboard_trade_board.js
node scripts/check_dashboard_money_panel.js
node scripts/check_dashboard_tradingview_source.js
node scripts/check_dashboard_communications.js
node scripts/check_dashboard_forum.js
node scripts/check_protected_user_guide.js

say "Checking status exporters"
"$PYTHON_BIN" scripts/check_cockpit_status.py
"$PYTHON_BIN" scripts/check_live_bridge.py

say "Checking dashboard syntax and whitespace"
node --check landing-page-repo/dashboard.js
git diff --check -- \
  landing-page-repo/auth.css \
  landing-page-repo/auth.js \
  landing-page-repo/dashboard/index.html \
  landing-page-repo/dashboard.js \
  landing-page-repo/guide/index.html \
  landing-page-repo/scripts/deploy-vercel-production.sh \
  orchestrator/cockpit_status.py \
  orchestrator/telegram_codebase_upgrade_notifications.py \
  orchestrator/telegram_comms.py \
  orchestrator/telegram_daily_portfolio_digest.py \
  orchestrator/telegram_message_quality.py \
  orchestrator/telegram_trade_notifications.py \
  scripts/check_codebase_upgrade_telegram_notification.py \
  scripts/check_daily_telegram_portfolio_digest.py \
  scripts/check_dashboard_communications.js \
  scripts/check_telegram_message_specificity.py \
  scripts/check_telegram_trade_notifications.py \
  scripts/send_codebase_upgrade_telegram_notification.py \
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
  scripts/check_dashboard_d13_health_language.js \
  scripts/check_dashboard_phase6_learning_loop.js \
  scripts/check_dashboard_rs9_learning_loop.js \
  scripts/check_dashboard_rs10_final_paper_autonomy.js \
  scripts/check_dashboard_cc6_real_portfolio_timeline.js \
  scripts/check_dashboard_cc7_visual_a11y.js \
  scripts/check_dashboard_cc8_prune_docs_deploy.js \
  scripts/check_dashboard_cc9_slop_repetition.js \
  docs/qadam-dashboard-consolidation-cut-implementation-plan-2026-06-05.md \
  docs/qadam-dashboard-overhaul-master-implementation-plan.md \
  docs/qadam-user-guide.md \
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
  scripts/check_dashboard_d12_language_cleanup.js \
  scripts/check_protected_user_guide.js \
  scripts/preflight_dashboard_deployment.sh

say "Deployment preflight passed"
