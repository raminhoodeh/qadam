#!/usr/bin/env python3
"""Run Qadam's safe self-healing supervisor."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from orchestrator.config import Settings
from orchestrator.qadam_self_healing_supervisor import build_and_write_self_healing_state


def main() -> int:
    payload, written, errors = build_and_write_self_healing_state(Settings.from_env(), perform_refresh=True)
    print(f"artifact={written.get('primary')}")
    print(f"status_artifact={written.get('status')}")
    print(f"quarantine={written.get('quarantine')}")
    print(f"repair_requests={written.get('repair_requests')}")
    print(f"repair_queue={written.get('repair_queue')}")
    print(f"refresh_retry_policy={written.get('refresh_retry_policy')}")
    print(f"provider_outages={written.get('provider_outages')}")
    print(f"stale_artifact_recovery={written.get('stale_artifact_recovery')}")
    print(f"backfill_resume={written.get('backfill_resume')}")
    print(f"code_defect_repair_requests={written.get('code_defect_repair_requests')}")
    print(f"why_not_working={written.get('why_not_working')}")
    print(f"status={payload.get('status')}")
    print(f"self_healing_passed={payload.get('self_healing_passed')}")
    print(f"safe_refresh_only={payload.get('safe_refresh_only')}")
    print(f"refresh_success_count={payload.get('refresh_tier', {}).get('refresh_success_count')}")
    print(f"refresh_failure_count={payload.get('refresh_tier', {}).get('refresh_failure_count')}")
    print(f"quarantine_record_count={payload.get('quarantine_tier', {}).get('quarantine_record_count')}")
    print(f"source_quorum_protected={payload.get('quarantine_tier', {}).get('source_quorum_protected')}")
    print(f"repair_request_count={payload.get('repair_request_tier', {}).get('repair_request_count')}")
    print(f"repair_queue_count={payload.get('repair_queue_tier', {}).get('repair_queue_count')}")
    print(f"provider_outage_count={payload.get('provider_outage_classification', {}).get('provider_outage_count')}")
    print(f"stale_or_missing_artifact_count={payload.get('stale_artifact_recovery', {}).get('stale_or_missing_artifact_count')}")
    print(f"backfill_resume_status={payload.get('backfill_resume', {}).get('status')}")
    print(f"code_defect_repair_request_count={payload.get('code_defect_repair_request_count')}")
    print(f"paper_order_created_count={payload.get('paper_order_created_count')}")
    print(f"broker_write_count={payload.get('broker_write_count')}")
    print(f"proof_credit_allowed={payload.get('proof_credit_allowed')}")
    print(f"live_capital_enabled={payload.get('live_capital_enabled')}")
    if errors:
        for error in errors:
            print(f"error={error}")
        return 1
    print("qadam_self_healing_supervisor_run=ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
