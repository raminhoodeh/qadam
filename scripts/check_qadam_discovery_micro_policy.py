#!/usr/bin/env python3
"""Validate the active discovery-micro amendment and paper-only boundaries."""

from __future__ import annotations

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from orchestrator.qadam_canonical_contracts import AtomicArtifactStore  # noqa: E402
from orchestrator.qadam_experimental_paper_policy import (  # noqa: E402
    POLICY_ARTIFACT,
    validate_policy,
)
from orchestrator.qadam_experimental_policy_amendment import (  # noqa: E402
    AMENDMENT_ARTIFACT,
    validate_policy_amendment,
)
from orchestrator.qadam_operator_ready_common import (  # noqa: E402
    authority_flags,
    file_sha256,
    now_iso,
    read_json,
    runtime_dir,
    unique_errors,
)

CHECK_ARTIFACT = "qadam_discovery_micro_policy_checks.json"


def main() -> int:
    runtime = runtime_dir()
    policy = read_json(runtime / POLICY_ARTIFACT)
    amendment = read_json(runtime / AMENDMENT_ARTIFACT)
    approval_path = runtime / "qadam_experimental_paper_release_approval.json"
    approval = read_json(approval_path)
    epoch = read_json(runtime / "current_paper_epoch.json")
    calendar = read_json(runtime / "qadam_paper_trial_calendar.json")
    errors = unique_errors(
        [
            *validate_policy(policy),
            *validate_policy_amendment(
                amendment,
                policy=policy,
                release_approval=approval,
                paper_epoch=epoch,
                trial_calendar=calendar,
                previous_approval_sha256=file_sha256(approval_path),
            ),
        ]
    )
    checks = {
        "schema_version": "qadam_discovery_micro_policy_checks.v1",
        "artifact_type": "qadam_discovery_micro_policy_checks",
        "generated_at": now_iso(),
        "status": "passed" if not errors else "blocked",
        "policy_version": policy.get("policy_version"),
        "amendment_id": amendment.get("amendment_id"),
        "paper_epoch_id": epoch.get("paper_epoch_id"),
        "trial_started_at": calendar.get("trial_started_at"),
        "discovery_micro_trade_ceiling_usd": policy.get("risk", {}).get(
            "discovery_micro_trade_ceiling_usd"
        ),
        "maximum_concurrent_discovery_micro_positions": policy.get("risk", {}).get(
            "maximum_concurrent_discovery_micro_positions"
        ),
        "paper_trial_calendar_reset": amendment.get("paper_trial_calendar_reset"),
        "paper_order_created_count": 0,
        "broker_write_count": 0,
        "proof_credit_granted_count": 0,
        "live_capital_enabled": False,
        "validation_error_count": len(errors),
        "validation_errors": errors,
        "authority": authority_flags(),
    }
    AtomicArtifactStore(runtime).write_json(CHECK_ARTIFACT, checks)
    print(f"discovery_micro_policy_check_status={checks['status']}")
    print(
        "discovery_micro_trade_ceiling_usd="
        f"{checks['discovery_micro_trade_ceiling_usd']}"
    )
    print(f"paper_trial_calendar_reset={str(checks['paper_trial_calendar_reset']).lower()}")
    for error in errors:
        print(f"discovery_micro_policy_error={error}")
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
