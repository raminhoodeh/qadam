#!/usr/bin/env python3
"""Validate the receipt-bound IBM hardware candidate research result."""

from __future__ import annotations

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from orchestrator.qadam_ibm_hardware_candidate_validation import (  # noqa: E402
    CHECK_ARTIFACT,
    VALIDATION_ARTIFACT,
    validate_hardware_candidate_validation,
)
from orchestrator.qadam_ibm_hardware_utilization import (  # noqa: E402
    FOLLOWUP_ARTIFACT,
)
from orchestrator.qadam_operator_ready_common import read_json  # noqa: E402


def main() -> int:
    runtime = ROOT / "data" / "runtime"
    payload = read_json(runtime / VALIDATION_ARTIFACT)
    checks = read_json(runtime / CHECK_ARTIFACT)
    followup = read_json(runtime / FOLLOWUP_ARTIFACT)
    errors = validate_hardware_candidate_validation(payload)
    if checks.get("status") != "passed" or checks.get("acceptance_passed") is not True:
        errors.append("candidate_validation_checks_not_passed")
    if payload.get("hardware_receipt_hash") != followup.get("hardware_receipt_hash"):
        errors.append("candidate_followup_receipt_mismatch")
    candidate = (followup.get("candidates") or [{}])[0]
    historical = candidate.get("historical_validation") or {}
    if historical.get("content_hash") != payload.get("content_hash"):
        errors.append("candidate_followup_content_hash_mismatch")
    if any(
        int(checks.get(key) or 0) != 0
        for key in (
            "validated_edge_count",
            "strategy_change_count",
            "trade_candidate_count",
            "paper_order_count",
            "proof_credit_count",
        )
    ):
        errors.append("candidate_validation_crossed_authority_boundary")
    errors = sorted(set(errors))
    print(f"ibm_hardware_candidate_validation_check={'ok' if not errors else 'blocked'}")
    print(f"ibm_hardware_candidate_validation_status={payload.get('status')}")
    print(
        "ibm_hardware_candidate_historical_survivor="
        f"{(payload.get('verdict') or {}).get('historical_survivor')}"
    )
    print(f"ibm_hardware_candidate_validation_errors={errors}")
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
