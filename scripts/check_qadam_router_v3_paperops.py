#!/usr/bin/env python3
"""Build and validate OR-15 Router V3 and PaperOps handoff state."""

from __future__ import annotations

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from orchestrator.config import Settings  # noqa: E402
from orchestrator.qadam_operator_ready_common import (  # noqa: E402
    runtime_dir,
    write_json_atomic,
)
from orchestrator.qadam_router_v3_paperops import (  # noqa: E402
    CHECK_ARTIFACT,
    DECISIONS_ARTIFACT,
    HANDOFF_ACCEPTED_ARTIFACT,
    HANDOFF_ARTIFACT,
    HANDOFF_CONSUMER_CHECK_ARTIFACT,
    HANDOFF_CONSUMER_STATE_ARTIFACT,
    HANDOFF_RECEIPTS_ARTIFACT,
    HANDOFF_REJECTIONS_ARTIFACT,
    RELEASE_READINESS_ARTIFACT,
    SCOREBOARD_ARTIFACT,
    WHY_NOT_ARTIFACT,
    build_and_write_handoff_consumption,
    build_and_write_router_v3,
    validate_handoff_consumer_negative_probes,
)


def main() -> int:
    settings = Settings.from_env()
    runtime = runtime_dir(settings)
    state, checks, errors = build_and_write_router_v3(settings)
    consumer, consumer_checks, consumer_errors = build_and_write_handoff_consumption(
        settings,
        router_state=state,
    )
    negative_probe_errors = validate_handoff_consumer_negative_probes()
    errors = [*errors, *consumer_errors, *negative_probe_errors]
    checks.update(
        {
            "status": "passed" if not errors else "blocked",
            "implementation_ready": not errors,
            "canonical_wrapper_consumer_implemented": True,
            "handoff_consumer_status": consumer["status"],
            "handoff_consumer_enforcement_active": consumer["enforcement_active"],
            "handoff_consumption_receipt_count": consumer["receipt_count"],
            "accepted_handoff_count": consumer["accepted_handoff_count"],
            "rejected_handoff_count": consumer["rejected_handoff_count"],
            "guarded_paperops_command_sequence_allowed": consumer[
                "guarded_paperops_command_sequence_allowed"
            ],
            "negative_safety_probe_error_count": len(negative_probe_errors),
            "validation_error_count": len(errors),
            "validation_errors": errors,
        }
    )
    write_json_atomic(runtime / CHECK_ARTIFACT, checks)
    for name in (
        DECISIONS_ARTIFACT,
        SCOREBOARD_ARTIFACT,
        WHY_NOT_ARTIFACT,
        HANDOFF_ARTIFACT,
        HANDOFF_ACCEPTED_ARTIFACT,
        HANDOFF_REJECTIONS_ARTIFACT,
        HANDOFF_RECEIPTS_ARTIFACT,
        HANDOFF_CONSUMER_STATE_ARTIFACT,
        HANDOFF_CONSUMER_CHECK_ARTIFACT,
        RELEASE_READINESS_ARTIFACT,
        CHECK_ARTIFACT,
    ):
        print(f"artifact={runtime / name}")
    for key in (
        "status",
        "implementation_ready",
        "release_state",
        "release_recommended",
        "release_performed",
        "setup_count",
        "decision_count",
        "paper_review_candidate_count",
        "handoff_count",
        "qualified_setup_created_count",
        "paper_order_created_count",
        "broker_write_count",
        "live_capital_enabled",
    ):
        print(f"{key}={checks[key]}")
    print(f"handoff_consumer_status={consumer['status']}")
    print(f"handoff_consumer_enforcement_active={consumer['enforcement_active']}")
    print(f"handoff_consumption_receipt_count={consumer['receipt_count']}")
    print(f"handoff_accepted_count={consumer['accepted_handoff_count']}")
    print(f"handoff_rejected_count={consumer['rejected_handoff_count']}")
    print(
        "guarded_paperops_command_sequence_allowed="
        f"{consumer['guarded_paperops_command_sequence_allowed']}"
    )
    print(f"handoff_consumer_check_status={consumer_checks['status']}")
    print(f"handoff_consumer_negative_probe_error_count={len(negative_probe_errors)}")
    print(f"validation_error_count={len(errors)}")
    for error in errors:
        print(f"error={error}")
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
