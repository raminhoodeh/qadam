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
  landing-page-repo/dashboard/index.html \
  landing-page-repo/dashboard.js \
  landing-page-repo/guide/index.html \
  landing-page-repo/scripts/deploy-vercel-production.sh \
  docs/qadam-dashboard-implementation-plan.md \
  docs/qadam-dashboard-navigation-ux-plan.md \
  scripts/check_dashboard_acceptance.js \
  scripts/check_dashboard_deployment_readiness.js \
  scripts/check_dashboard_navigation_ux.js \
  scripts/preflight_dashboard_deployment.sh

say "Deployment preflight passed"
