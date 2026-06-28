#!/usr/bin/env python3
"""Run QSASE-13 dashboard anti-slop checks."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from orchestrator.config import Settings
from orchestrator.qsase_dashboard_view_model import (
    build_and_write_dashboard_view_model,
    load_dashboard_view_model,
    run_dashboard_anti_slop_checks,
    validate_negative_dashboard_view_model_probes,
)


def main() -> int:
    settings = Settings.from_env()
    payload = load_dashboard_view_model(settings)
    if not payload:
        payload, _, build_errors = build_and_write_dashboard_view_model(settings)
    else:
        build_errors = []
    audit = run_dashboard_anti_slop_checks(payload)
    errors = list(build_errors) + list(audit.get("errors", [])) + validate_negative_dashboard_view_model_probes()

    print(f"status={audit.get('status')}")
    print(f"error_count={audit.get('error_count')}")
    print(f"warning_count={audit.get('warning_count')}")
    print(f"duplicate_headlines_rejected={audit.get('checks', {}).get('duplicate_headlines_rejected')}")
    print(f"generic_ai_prose_rejected={audit.get('checks', {}).get('generic_ai_prose_rejected')}")
    print(f"trade_intents_not_orders={audit.get('checks', {}).get('trade_intents_not_orders')}")
    print(f"overview_detail_ledgers_excluded={audit.get('checks', {}).get('overview_detail_ledgers_excluded')}")
    print(f"stale_state_labeled={audit.get('checks', {}).get('stale_state_labeled')}")
    print(f"authority_drift_rejected={audit.get('checks', {}).get('authority_drift_rejected')}")
    for warning in audit.get("warnings", []):
        print(f"warning={warning}")
    if errors:
        for error in errors:
            print(f"error={error}")
        return 1
    print("qsase_dashboard_anti_slop_check=ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
