#!/usr/bin/env python3
"""Validate Qadam's safe self-healing supervisor artifacts."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from orchestrator.config import Settings
from orchestrator.qadam_self_healing_supervisor import (
    BACKFILL_RESUME_ARTIFACT,
    CODE_DEFECT_REPAIR_REQUESTS_ARTIFACT,
    PRIMARY_ARTIFACT,
    PROVIDER_OUTAGES_ARTIFACT,
    QUARANTINE_ARTIFACT,
    REFRESH_RETRY_POLICY_ARTIFACT,
    REPAIR_REQUESTS_ARTIFACT,
    REPAIR_QUEUE_ARTIFACT,
    STALE_ARTIFACT_RECOVERY_ARTIFACT,
    STATUS_ARTIFACT,
    WHY_NOT_WORKING_ARTIFACT,
    _runtime_dir,
    build_and_write_self_healing_state,
    validate_self_healing,
)


def _load_json(path: Path) -> dict:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def _read_jsonl(path: Path) -> list[dict]:
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def main() -> int:
    settings = Settings.from_env()
    payload, written, errors = build_and_write_self_healing_state(settings, perform_refresh=True)
    runtime = _runtime_dir(settings)
    loaded = _load_json(runtime / PRIMARY_ARTIFACT)
    status = _load_json(runtime / STATUS_ARTIFACT)
    quarantine = _load_json(runtime / QUARANTINE_ARTIFACT)
    repair_requests = _read_jsonl(runtime / REPAIR_REQUESTS_ARTIFACT)
    repair_queue = _load_json(runtime / REPAIR_QUEUE_ARTIFACT)
    retry_policy = _load_json(runtime / REFRESH_RETRY_POLICY_ARTIFACT)
    provider_outages = _load_json(runtime / PROVIDER_OUTAGES_ARTIFACT)
    stale_recovery = _load_json(runtime / STALE_ARTIFACT_RECOVERY_ARTIFACT)
    backfill_resume = _load_json(runtime / BACKFILL_RESUME_ARTIFACT)
    code_defects = _read_jsonl(runtime / CODE_DEFECT_REPAIR_REQUESTS_ARTIFACT)
    why_not_working = _load_json(runtime / WHY_NOT_WORKING_ARTIFACT)
    validation_errors = list(errors)

    for filename in (
        PRIMARY_ARTIFACT,
        STATUS_ARTIFACT,
        QUARANTINE_ARTIFACT,
        REPAIR_REQUESTS_ARTIFACT,
        REPAIR_QUEUE_ARTIFACT,
        REFRESH_RETRY_POLICY_ARTIFACT,
        PROVIDER_OUTAGES_ARTIFACT,
        STALE_ARTIFACT_RECOVERY_ARTIFACT,
        BACKFILL_RESUME_ARTIFACT,
        CODE_DEFECT_REPAIR_REQUESTS_ARTIFACT,
        WHY_NOT_WORKING_ARTIFACT,
    ):
        if not (runtime / filename).exists():
            validation_errors.append(f"{filename}_missing")

    validation_errors.extend(validate_self_healing(loaded, repair_requests))
    if status.get("artifact_type") != "qadam_self_healing_status":
        validation_errors.append("status_artifact_type_mismatch")
    if status.get("generated_at") != loaded.get("generated_at"):
        validation_errors.append("status_generated_at_mismatch")
    if len(repair_requests) != loaded.get("repair_request_tier", {}).get("repair_request_count"):
        validation_errors.append("repair_request_count_mismatch")
    if repair_queue.get("repair_queue_count") != loaded.get("repair_queue_tier", {}).get("repair_queue_count"):
        validation_errors.append("repair_queue_count_mismatch")
    if len(quarantine.get("records", [])) != loaded.get("quarantine_tier", {}).get("quarantine_record_count"):
        validation_errors.append("quarantine_record_count_mismatch")
    if retry_policy.get("safe_refresh_only") is not True:
        validation_errors.append("retry_policy_not_safe_refresh_only")
    if provider_outages.get("provider_outage_count") != len(provider_outages.get("records", [])):
        validation_errors.append("provider_outage_count_mismatch")
    if stale_recovery.get("stale_or_missing_artifact_count") != len(stale_recovery.get("records", [])):
        validation_errors.append("stale_recovery_count_mismatch")
    if backfill_resume.get("resume_executed") is not False:
        validation_errors.append("backfill_resume_executed")
    if len(code_defects) != loaded.get("code_defect_repair_request_count"):
        validation_errors.append("code_defect_repair_request_count_mismatch")
    if why_not_working.get("self_healing_may_edit_code") is not False:
        validation_errors.append("why_not_working_may_edit_code")
    if loaded.get("self_healing_passed") is not True:
        validation_errors.append("self_healing_not_passed")

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
    print(f"status={loaded.get('status')}")
    print(f"self_healing_passed={loaded.get('self_healing_passed')}")
    print(f"safe_refresh_only={loaded.get('safe_refresh_only')}")
    print(f"refresh_success_count={loaded.get('refresh_tier', {}).get('refresh_success_count')}")
    print(f"refresh_failure_count={loaded.get('refresh_tier', {}).get('refresh_failure_count')}")
    print(f"quarantine_record_count={loaded.get('quarantine_tier', {}).get('quarantine_record_count')}")
    print(f"source_quorum_protected={loaded.get('quarantine_tier', {}).get('source_quorum_protected')}")
    print(f"repair_request_count={loaded.get('repair_request_tier', {}).get('repair_request_count')}")
    print(f"critical_repair_request_count={loaded.get('repair_request_tier', {}).get('critical_repair_request_count')}")
    print(f"repair_queue_count={loaded.get('repair_queue_tier', {}).get('repair_queue_count')}")
    print(f"critical_repair_queue_count={loaded.get('repair_queue_tier', {}).get('critical_repair_queue_count')}")
    print(f"provider_outage_count={loaded.get('provider_outage_classification', {}).get('provider_outage_count')}")
    print(f"stale_or_missing_artifact_count={loaded.get('stale_artifact_recovery', {}).get('stale_or_missing_artifact_count')}")
    print(f"safe_retry_attempted_count={loaded.get('stale_artifact_recovery', {}).get('safe_retry_attempted_count')}")
    print(f"backfill_resume_status={loaded.get('backfill_resume', {}).get('status')}")
    print(f"code_defect_repair_request_count={loaded.get('code_defect_repair_request_count')}")
    print(f"why_not_working_status={loaded.get('why_not_working', {}).get('status')}")
    print(f"code_edit_allowed={loaded.get('code_edit_allowed')}")
    print(f"secret_change_allowed={loaded.get('secret_change_allowed')}")
    print(f"test_bypass_allowed={loaded.get('test_bypass_allowed')}")
    print(f"authority_change_allowed={loaded.get('authority_change_allowed')}")
    print(f"paper_order_created_count={loaded.get('paper_order_created_count')}")
    print(f"broker_write_count={loaded.get('broker_write_count')}")
    print(f"proof_credit_allowed={loaded.get('proof_credit_allowed')}")
    print(f"live_capital_enabled={loaded.get('live_capital_enabled')}")

    if validation_errors:
        for error in sorted(set(validation_errors)):
            print(f"error={error}")
        return 1
    if payload.get("generated_at") != loaded.get("generated_at"):
        print("error=written_generated_at_mismatch")
        return 1
    print("qadam_self_healing_supervisor_check=ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
