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
"$PYTHON_BIN" scripts/check_cockpit_status.py

say "Checking dashboard acceptance gate"
node --check scripts/check_dashboard_acceptance.js
node scripts/check_dashboard_acceptance.js

say "Checking deployment readiness gate"
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
node scripts/check_dashboard_system_map.js
node scripts/check_dashboard_durable_spine.js
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
  docs/qadam-dashboard-overhaul-master-implementation-plan.md \
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
  scripts/preflight_dashboard_deployment.sh

say "Deployment preflight passed"
