#!/usr/bin/env python3
"""Apply the operator-approved discovery-micro policy without resetting time."""

from __future__ import annotations

import argparse
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from orchestrator.qadam_canonical_contracts import AtomicArtifactStore  # noqa: E402
from orchestrator.qadam_experimental_paper_policy import (  # noqa: E402
    POLICY_ARTIFACT,
    POLICY_VERSION,
    build_and_write_experimental_policy,
    default_policy,
)
from orchestrator.qadam_experimental_policy_amendment import (  # noqa: E402
    AMENDMENT_ARTIFACT,
    AMENDMENT_HISTORY_ARTIFACT,
    POLICY_HISTORY_ARTIFACT,
    build_policy_amendment,
    validate_policy_amendment,
)
from orchestrator.qadam_operator_ready_common import (  # noqa: E402
    append_jsonl_durable,
    file_sha256,
    read_json,
    read_jsonl,
    runtime_dir,
    sha256_json,
)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--approve-discovery-micro", action="store_true")
    args = parser.parse_args()
    if not args.approve_discovery_micro:
        print("discovery_micro_policy_status=blocked_explicit_operator_approval_required")
        return 1

    runtime = runtime_dir()
    maintenance = read_json(runtime / "qadam_operator_maintenance_window.json")
    if maintenance.get("status") != "active":
        print("discovery_micro_policy_status=blocked_maintenance_window_required")
        return 1

    previous_policy = read_json(runtime / POLICY_ARTIFACT)
    release_approval_path = runtime / "qadam_experimental_paper_release_approval.json"
    release_approval = read_json(release_approval_path)
    paper_epoch = read_json(runtime / "current_paper_epoch.json")
    trial_calendar = read_json(runtime / "qadam_paper_trial_calendar.json")
    release_receipt = read_json(runtime / "qadam_guarded_paper_launch_receipt.json")
    lock = read_json(runtime / "qadam_long_backtest_lock.json")
    amended_policy = default_policy()
    previous_amendment = read_json(runtime / AMENDMENT_ARTIFACT)
    policy_history = read_jsonl(runtime / POLICY_HISTORY_ARTIFACT)
    if previous_policy.get("policy_version") == POLICY_VERSION:
        existing_errors = validate_policy_amendment(
            previous_amendment,
            policy=previous_policy,
            release_approval=release_approval,
            paper_epoch=paper_epoch,
            trial_calendar=trial_calendar,
            previous_approval_sha256=file_sha256(release_approval_path),
            policy_history=policy_history,
        )
        if not existing_errors:
            print("discovery_micro_policy_status=already_applied")
            print(
                "discovery_micro_policy_amendment_id="
                f"{previous_amendment.get('amendment_id')}"
            )
            print("paper_trial_calendar_reset=false")
            return 0
        print("discovery_micro_policy_status=blocked_existing_amendment_invalid")
        for error in existing_errors:
            print(f"discovery_micro_policy_error={error}")
        return 1
    amendment = build_policy_amendment(
        previous_policy=previous_policy,
        amended_policy=amended_policy,
        release_approval=release_approval,
        paper_epoch=paper_epoch,
        trial_calendar=trial_calendar,
        previous_approval_sha256=file_sha256(release_approval_path),
        explicit_operator_approval=True,
        previous_amendment=previous_amendment,
    )
    preconditions: list[str] = []
    if release_receipt.get("launch_executed") is not True:
        preconditions.append("experimental_paper_launch_not_executed")
    if release_receipt.get("direct_broker_call_count", 0) != 0:
        preconditions.append("direct_broker_call_detected")
    if lock.get("status") != "released" or lock.get("paperops_watch_only_mode") is not False:
        preconditions.append("experimental_paper_lock_not_released")
    if amendment.get("operator_approved") is not True:
        preconditions.append("policy_amendment_binding_not_approved")
    if preconditions:
        print("discovery_micro_policy_status=blocked")
        for blocker in preconditions:
            print(f"discovery_micro_policy_blocker={blocker}")
        return 1

    errors = validate_policy_amendment(
        amendment,
        policy=amended_policy,
        release_approval=release_approval,
        paper_epoch=paper_epoch,
        trial_calendar=trial_calendar,
        previous_approval_sha256=file_sha256(release_approval_path),
        policy_history=[*policy_history, previous_policy],
    )
    if errors:
        print("discovery_micro_policy_status=blocked")
        for error in errors:
            print(f"discovery_micro_policy_error={error}")
        return 1

    store = AtomicArtifactStore(runtime)
    if previous_policy and not any(
        record.get("policy_version") == previous_policy.get("policy_version")
        and sha256_json(record) == sha256_json(previous_policy)
        for record in policy_history
    ):
        append_jsonl_durable(runtime / POLICY_HISTORY_ARTIFACT, previous_policy)
    store.write_json(AMENDMENT_ARTIFACT, amendment)
    append_jsonl_durable(runtime / AMENDMENT_HISTORY_ARTIFACT, amendment)
    build_and_write_experimental_policy()
    print("discovery_micro_policy_status=applied")
    print(f"discovery_micro_policy_amendment_id={amendment['amendment_id']}")
    print(f"discovery_micro_policy_from={amendment['from_policy_version']}")
    print(f"discovery_micro_policy_to={amendment['to_policy_version']}")
    print("discovery_micro_trade_ceiling_usd=5000")
    print("paper_trial_calendar_reset=false")
    print("paper_order_created_count=0")
    print("broker_write_count=0")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
