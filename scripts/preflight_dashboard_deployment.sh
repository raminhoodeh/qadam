#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
PYTHON_BIN="${QADAM_PYTHON:-${ROOT}/.venv/bin/python}"
SITE="${QADAM_DASHBOARD_SITE_ROOT:-${ROOT}/landing-page-repo}"
RUNTIME="${QADAM_RUNTIME_DIR:-${ROOT}/data/runtime}"
export QADAM_DASHBOARD_SITE_ROOT="$SITE"
export QADAM_RUNTIME_DIR="$RUNTIME"

# Deployment validates existing projections. It never refreshes the account,
# invokes a research producer, migrates SQLite or pauses position care.
"$PYTHON_BIN" scripts/verify_dashboard_release_readonly.py --site-root "$SITE" --runtime-dir "$RUNTIME"
"$PYTHON_BIN" scripts/run_paperops_autonomous_pass.py --report-only
for asset in dashboard.js auth.js api/cockpit-status.js api/cockpit-status-publish.js lib/status-storage.js; do
  node --check "${SITE}/${asset}"
done
node --test "${SITE}/scripts/test-status-storage.js" "${SITE}/scripts/test-vercel-deployment-guard.js"
node scripts/check_dashboard_renderer.js
node scripts/check_dashboard_ten_stage_lifecycle.js
node scripts/check_dashboard_portfolio_accounting.js
node scripts/check_qadam_strategy_decision_ui.js
node scripts/check_dashboard_passive_refresh_scroll.js
git -C "$SITE" diff --check
printf '[qadam-preflight] Read-only release checks passed; no account or runtime producer was invoked.\n'
