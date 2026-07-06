#!/usr/bin/env python3
"""Validate and write QSASE Phase 13 dashboard completion V2 artifacts."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from orchestrator.config import Settings
from orchestrator.qsase_phase11_to14_completion import (
    DASHBOARD_COMPLETION_V2_ARTIFACT,
    DASHBOARD_ORDER_AUDIT_V2_ARTIFACT,
    _runtime_dir,
    build_and_write_phase11_to14_completion,
    validate_payload,
)


def _load_json(path: Path) -> dict:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> int:
    settings = Settings.from_env()
    summary, written, errors = build_and_write_phase11_to14_completion(settings)
    runtime = _runtime_dir(settings)
    payload = _load_json(runtime / DASHBOARD_COMPLETION_V2_ARTIFACT)
    order_audit = _load_json(runtime / DASHBOARD_ORDER_AUDIT_V2_ARTIFACT)
    validation_errors = list(errors)

    for filename in (DASHBOARD_COMPLETION_V2_ARTIFACT, DASHBOARD_ORDER_AUDIT_V2_ARTIFACT):
        if not (runtime / filename).exists():
            validation_errors.append(f"{filename}_missing")

    validation_errors.extend(validate_payload(payload, "qsase_dashboard_completion_v2"))
    if payload.get("dashboard_order_passed") is not True:
        validation_errors.append("dashboard_order_not_passed")
    if order_audit.get("order_passed") is not True:
        validation_errors.append("dashboard_order_audit_not_passed")
    if payload.get("portfolio_consistency_status") != "ok":
        validation_errors.append("portfolio_consistency_not_ok")
    if payload.get("anti_slop_error_count", 0):
        validation_errors.append("anti_slop_errors_present")

    print(f"artifact={written.get(DASHBOARD_COMPLETION_V2_ARTIFACT)}")
    print(f"order_audit={written.get(DASHBOARD_ORDER_AUDIT_V2_ARTIFACT)}")
    print(f"status={payload.get('status')}")
    print(f"dashboard_order_passed={payload.get('dashboard_order_passed')}")
    print(f"missing_section_count={payload.get('missing_section_count')}")
    print(f"portfolio_consistency_status={payload.get('portfolio_consistency_status')}")
    print(f"portfolio_value_latest={payload.get('portfolio_value_latest')}")
    print(f"chart_latest_value={payload.get('chart_latest_value')}")
    print(f"source_category_count={payload.get('source_category_count')}")
    print(f"source_row_count={payload.get('source_row_count')}")
    print(f"trading_universe_row_count={payload.get('trading_universe_row_count')}")
    print(f"pattern_finding_count={payload.get('pattern_finding_count')}")
    print(f"anti_slop_error_count={payload.get('anti_slop_error_count')}")
    print(f"stale_labeled_count={payload.get('stale_labeled_count')}")
    print(f"paper_order_created_count={payload.get('paper_order_created_count')}")
    print(f"broker_write_count={payload.get('broker_write_count')}")

    if validation_errors:
        for error in sorted(set(validation_errors)):
            print(f"error={error}")
        return 1
    if summary.get("dashboard", {}).get("dashboard_order_passed") != payload.get("dashboard_order_passed"):
        print("error=summary_dashboard_order_mismatch")
        return 1
    print("qsase_dashboard_completion_v2_check=ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
