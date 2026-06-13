#!/usr/bin/env python3
"""Validate the PaperOps submit-side regression guard."""

from __future__ import annotations

from copy import deepcopy
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from orchestrator.config import Settings  # noqa: E402
from orchestrator.event_log import EventLog  # noqa: E402
from orchestrator.paperops_submit_regression_guard import (  # noqa: E402
    PAPEROPS_SUBMIT_REGRESSION_SCHEMA_VERSION,
    build_paperops_submit_regression_guard,
    paperops_submit_regression_guard_paths,
    validate_paperops_submit_regression_guard,
    write_paperops_submit_regression_guard,
)


def main() -> int:
    errors: list[str] = []
    settings = Settings.from_env()
    output_path, history_path, event_path = paperops_submit_regression_guard_paths(
        settings
    )
    if event_path.exists():
        event_path.unlink()

    artifact = build_paperops_submit_regression_guard(settings=settings)
    output_path, history_path, event_path, written = write_paperops_submit_regression_guard(
        artifact,
        settings=settings,
        record_event=True,
        event_log_path=event_path,
    )
    validation_errors = validate_paperops_submit_regression_guard(written)
    replay = EventLog(event_path, echo=False).replay()

    stale_probe = deepcopy(written)
    stale_probe["source_stale_after_post_tolerance_count"] = 1
    stale_probe["blockers"] = []
    stale_probe["blocker_count"] = 0
    stale_probe["status"] = "healthy_idle_idempotency_guarded"
    stale_errors = validate_paperops_submit_regression_guard(stale_probe)

    ledger_collision_probe = deepcopy(written)
    ledger_collision_probe["fresh_submitted_ledger_collision_count"] = 1
    ledger_collision_probe["blockers"] = []
    ledger_collision_probe["blocker_count"] = 0
    ledger_collision_probe["status"] = "ready_fresh_submit_consistent"
    ledger_collision_errors = validate_paperops_submit_regression_guard(
        ledger_collision_probe
    )

    duplicate_probe = deepcopy(written)
    duplicate_probe["duplicate_misclassified_as_fresh_count"] = 1
    duplicate_probe["blockers"] = []
    duplicate_probe["blocker_count"] = 0
    duplicate_probe["status"] = "ready_fresh_submit_consistent"
    duplicate_errors = validate_paperops_submit_regression_guard(duplicate_probe)

    lineage_probe = deepcopy(written)
    lineage_probe["fresh_research_goal_lineage_missing_count"] = 1
    lineage_probe["blockers"] = []
    lineage_probe["blocker_count"] = 0
    lineage_probe["status"] = "ready_fresh_submit_consistent"
    lineage_errors = validate_paperops_submit_regression_guard(lineage_probe)

    live_endpoint_probe = deepcopy(written)
    live_endpoint_probe["live_endpoint_called_count"] = 1
    live_endpoint_errors = validate_paperops_submit_regression_guard(
        live_endpoint_probe
    )

    proof_probe = deepcopy(written)
    proof_probe["phase7_proof_credit_allowed"] = True
    proof_errors = validate_paperops_submit_regression_guard(proof_probe)

    print(f"paperops_submit_regression_guard_status={written['status']}")
    print(
        "paperops_submit_regression_guard_schema_version="
        f"{PAPEROPS_SUBMIT_REGRESSION_SCHEMA_VERSION}"
    )
    print(f"paperops_submit_regression_guard_artifact_path={output_path}")
    print(f"paperops_submit_regression_guard_history_path={history_path}")
    print(f"paperops_submit_regression_guard_event_log_path={event_path}")
    print(
        "paperops_submit_regression_guard_source_paperops2_status="
        f"{written['source_paperops2_status']}"
    )
    print(
        "paperops_submit_regression_guard_source_paperops2_generated_at="
        f"{written['source_paperops2_generated_at'] or ''}"
    )
    print(
        "paperops_submit_regression_guard_source_artifact_count="
        f"{written['source_artifact_count']}"
    )
    print(
        "paperops_submit_regression_guard_source_stale_after_post_count="
        f"{written['source_stale_after_post_tolerance_count']}"
    )
    print(
        "paperops_submit_regression_guard_source_submit_record_count="
        f"{written['source_submit_record_count']}"
    )
    print(
        "paperops_submit_regression_guard_source_eligible_submit_record_count="
        f"{written['source_eligible_submit_record_count']}"
    )
    print(
        "paperops_submit_regression_guard_fresh_eligible_submit_record_count="
        f"{written['fresh_eligible_submit_record_count']}"
    )
    print(
        "paperops_submit_regression_guard_duplicate_submit_record_count="
        f"{written['duplicate_submit_record_count']}"
    )
    print(
        "paperops_submit_regression_guard_submitted_client_order_id_count="
        f"{written['submitted_client_order_id_count']}"
    )
    print(
        "paperops_submit_regression_guard_submitted_source_idempotency_key_count="
        f"{written['submitted_source_idempotency_key_count']}"
    )
    print(
        "paperops_submit_regression_guard_idempotency_ledger_active="
        f"{written['idempotency_ledger_active']}"
    )
    print(
        "paperops_submit_regression_guard_fresh_submitted_ledger_collision_count="
        f"{written['fresh_submitted_ledger_collision_count']}"
    )
    print(
        "paperops_submit_regression_guard_fresh_submitted_idempotency_recorded_count="
        f"{written['fresh_submitted_idempotency_recorded_count']}"
    )
    print(
        "paperops_submit_regression_guard_fresh_submitted_idempotency_missing_count="
        f"{written['fresh_submitted_idempotency_missing_count']}"
    )
    print(
        "paperops_submit_regression_guard_duplicate_misclassified_as_fresh_count="
        f"{written['duplicate_misclassified_as_fresh_count']}"
    )
    print(
        "paperops_submit_regression_guard_fresh_candidate_identity_missing_count="
        f"{written['fresh_candidate_identity_missing_count']}"
    )
    print(
        "paperops_submit_regression_guard_fresh_research_goal_lineage_missing_count="
        f"{written['fresh_research_goal_lineage_missing_count']}"
    )
    print(
        "paperops_submit_regression_guard_fresh_idempotency_key_missing_count="
        f"{written['fresh_idempotency_key_missing_count']}"
    )
    print(
        "paperops_submit_regression_guard_fresh_candidate_identity_collision_count="
        f"{written['fresh_candidate_identity_collision_count']}"
    )
    print(
        "paperops_submit_regression_guard_fresh_research_goal_lineage_collision_count="
        f"{written['fresh_research_goal_lineage_collision_count']}"
    )
    print(
        "paperops_submit_regression_guard_fresh_idempotency_key_collision_count="
        f"{written['fresh_idempotency_key_collision_count']}"
    )
    print(
        "paperops_submit_regression_guard_live_endpoint_called_count="
        f"{written['live_endpoint_called_count']}"
    )
    print(
        "paperops_submit_regression_guard_broker_post_called_count="
        f"{written['broker_post_called_count']}"
    )
    print(
        "paperops_submit_regression_guard_live_capital_enabled="
        f"{written['live_capital_enabled']}"
    )
    print(
        "paperops_submit_regression_guard_phase7_proof_credit_allowed="
        f"{written['phase7_proof_credit_allowed']}"
    )
    print(
        "paperops_submit_regression_guard_blockers="
        f"{','.join(written['blockers'])}"
    )
    print(
        "paperops_submit_regression_guard_blocker_count="
        f"{written['blocker_count']}"
    )
    print(
        "paperops_submit_regression_guard_next_required_action="
        f"{written['next_required_action']}"
    )
    print(
        "paperops_submit_regression_guard_event_log_events="
        f"{replay['total_events']}"
    )
    print(
        "paperops_submit_regression_guard_validation_errors="
        f"{validation_errors}"
    )

    if validation_errors:
        errors.append(f"submit regression guard validation failed: {validation_errors}")
    if replay["total_events"] != 1:
        errors.append("submit regression guard event log did not record exactly one event")
    if written["public_safe"] is not True:
        errors.append("submit regression guard is not public-safe")
    if written["live_endpoint_called_count"] != 0:
        errors.append("submit regression guard called a live endpoint")
    if written["broker_post_called_count"] != 0:
        errors.append("submit regression guard called broker POST")
    if written["live_capital_enabled"] is not False:
        errors.append("submit regression guard enabled live capital")
    if written["phase7_proof_credit_allowed"] is not False:
        errors.append("submit regression guard allowed proof credit")
    if written["idempotency_ledger_active"] is not True:
        errors.append("submit regression guard did not see active idempotency ledger")
    if written["fresh_submitted_ledger_collision_count"] != 0:
        errors.append("fresh submit candidate is already in idempotency ledger")
    if written["fresh_submitted_idempotency_missing_count"] != 0:
        errors.append("submitted fresh candidate is missing from idempotency ledger")
    if written["duplicate_misclassified_as_fresh_count"] != 0:
        errors.append("duplicate candidate is misclassified as fresh")
    if "paperops_submit_regression_unblocked:source_stale_after_post_tolerance_count" not in stale_errors:
        errors.append("stale-source probe was not rejected")
    if "paperops_submit_regression_unblocked:fresh_submitted_ledger_collision_count" not in ledger_collision_errors:
        errors.append("fresh ledger-collision probe was not rejected")
    if "paperops_submit_regression_unblocked:duplicate_misclassified_as_fresh_count" not in duplicate_errors:
        errors.append("duplicate misclassification probe was not rejected")
    if "paperops_submit_regression_unblocked:fresh_research_goal_lineage_missing_count" not in lineage_errors:
        errors.append("missing Research Goal lineage probe was not rejected")
    if "paperops_submit_regression_unsafe_counter_nonzero:live_endpoint_called_count" not in live_endpoint_errors:
        errors.append("live-endpoint probe was not rejected")
    if "paperops_submit_regression_forbidden:phase7_proof_credit_allowed" not in proof_errors:
        errors.append("proof-credit probe was not rejected")

    if errors:
        print("paperops_submit_regression_guard_check=failed")
        for error in errors:
            print(f"error={error}")
        return 1
    print("paperops_submit_regression_guard_check=ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
