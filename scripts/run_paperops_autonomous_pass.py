#!/usr/bin/env python3
"""Run one guarded PaperOps autonomous pass and emit one canonical summary."""

from __future__ import annotations

import argparse
import atexit
import fcntl
import os
from pathlib import Path
import subprocess
import sys
from uuid import uuid4

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from orchestrator.config import Settings  # noqa: E402
from orchestrator.paperops_autonomous_pass import (  # noqa: E402
    build_research_lock_watch_only_summary,
    build_paperops_autonomous_pass_summary,
    read_latest_paperops_autonomous_pass_summary,
    run_command_sequence,
    validate_paperops_autonomous_pass_summary,
    write_paperops_autonomous_pass_summary,
)
from orchestrator.qadam_next_generation_safety_lock import (  # noqa: E402
    is_long_backtest_lock_active,
    read_long_backtest_lock,
)
from orchestrator.qadam_paper_lineage_and_proof import (  # noqa: E402
    build_and_write_paper_lineage_and_proof,
)
from orchestrator.qadam_router_v3_paperops import (  # noqa: E402
    build_and_write_handoff_consumption,
    build_and_write_router_v3,
)
from orchestrator.qadam_control_plane_bridge import (  # noqa: E402
    persist_handoff_consumption,
)
from orchestrator.qadam_operating_ledger import (  # noqa: E402
    EXECUTION_OWNER_ID_ENV,
    EXECUTION_OWNER_TOKEN_ENV,
    ExecutionOwnerError,
    OperatingLedger,
)


def _acquire_pass_lock(settings: Settings):
    runtime = Path(settings.runtime_dir)
    if not runtime.is_absolute():
        runtime = ROOT / runtime
    runtime.mkdir(parents=True, exist_ok=True)
    handle = (runtime / ".paperops_autonomous_pass.lock").open(
        "a+", encoding="utf-8"
    )
    try:
        fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        handle.close()
        return None
    return handle


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--report-only",
        action="store_true",
        help="Validate the latest canonical summary without running any producer or broker-write path.",
    )
    args = parser.parse_args()
    settings = Settings.from_env()
    if args.report_only:
        latest = read_latest_paperops_autonomous_pass_summary(settings)
        errors = (
            validate_paperops_autonomous_pass_summary(latest)
            if latest
            else ["paperops_autonomous_pass_summary_missing"]
        )
        print("paperops_autonomous_pass_report_only=true")
        print(f"paperops_autonomous_pass_status={latest.get('status', 'missing')}")
        print(f"paperops_autonomous_pass_validation_error_count={len(errors)}")
        print("paperops_autonomous_pass_broker_write_count=0")
        return 1 if errors else 0
    pass_lock = _acquire_pass_lock(settings)
    if pass_lock is None:
        latest = read_latest_paperops_autonomous_pass_summary(settings)
        print("paperops_autonomous_pass_concurrent_pass_skipped=true")
        print("paperops_autonomous_pass_reason=canonical_pass_already_running")
        print(
            "paperops_autonomous_pass_summary_path="
            "data/runtime/paperops_autonomous_pass_summary.json"
        )
        print(
            "paperops_autonomous_pass_status="
            f"{latest.get('status', 'concurrent_pass_already_running')}"
        )
        return 0
    ledger = OperatingLedger(settings)
    owner_id = f"paperops-autonomous-pass:{os.getpid()}:{uuid4().hex[:12]}"
    try:
        execution_lease = ledger.acquire_execution_owner(owner_id, ttl_seconds=7_200)
    except ExecutionOwnerError as exc:
        pass_lock.close()
        print("paperops_autonomous_pass_status=degraded_execution_owner_unavailable")
        print(f"paperops_autonomous_pass_reason={str(exc).split(':', 1)[0]}")
        return 1

    previous_owner_id = os.environ.get(EXECUTION_OWNER_ID_ENV)
    previous_owner_token = os.environ.get(EXECUTION_OWNER_TOKEN_ENV)
    os.environ.update(execution_lease.environment())
    cleaned_up = False

    def _cleanup_execution_owner() -> None:
        nonlocal cleaned_up
        if cleaned_up:
            return
        cleaned_up = True
        try:
            ledger.release_execution_owner(execution_lease)
        finally:
            if previous_owner_id is None:
                os.environ.pop(EXECUTION_OWNER_ID_ENV, None)
            else:
                os.environ[EXECUTION_OWNER_ID_ENV] = previous_owner_id
            if previous_owner_token is None:
                os.environ.pop(EXECUTION_OWNER_TOKEN_ENV, None)
            else:
                os.environ[EXECUTION_OWNER_TOKEN_ENV] = previous_owner_token
            pass_lock.close()

    atexit.register(_cleanup_execution_owner)

    mirror_refresh = subprocess.run(
        [sys.executable, "scripts/check_alpaca_paper_mirror.py", "--live"],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
        timeout=90,
        env=os.environ.copy(),
    )
    ledger_bootstrap = not ledger.store.read_table("canonical_orders")
    try:
        pre_execution_reconciliation = ledger.sync_paper_mirror(
            phase="pre_paperops_submission",
            bootstrap=ledger_bootstrap,
        )
    except Exception as exc:  # noqa: BLE001 - publish class, never provider text.
        ledger.set_execution_frozen(
            reason=f"pre_execution_reconciliation_failed:{type(exc).__name__}"
        )
        pre_execution_reconciliation = {
            "status": "blocked",
            "blockers": [f"pre_execution_reconciliation_failed:{type(exc).__name__}"],
        }
    lock = read_long_backtest_lock(settings)
    router_state, router_checks, router_errors = build_and_write_router_v3(settings)
    try:
        research_generation = ledger.record_research_generation(router_state)
    except Exception as exc:  # noqa: BLE001 - publish class, never record contents.
        ledger.set_execution_frozen(
            reason=f"research_generation_ledger_failed:{type(exc).__name__}"
        )
        research_generation = {
            "hypothesis_count": 0,
            "risk_decision_inserted_count": 0,
            "error": f"research_generation_ledger_failed:{type(exc).__name__}",
        }
        router_errors = [
            *router_errors,
            research_generation["error"],
        ]
    handoff_consumer, consumer_checks, consumer_errors = build_and_write_handoff_consumption(
        settings, router_state=router_state
    )
    new_submission_allowed = bool(
        not router_errors
        and not consumer_errors
        and handoff_consumer.get("guarded_paperops_command_sequence_allowed") is True
        and mirror_refresh.returncode == 0
        and pre_execution_reconciliation.get("status") == "passed"
        and int(ledger.execution_state().get("frozen") or 0) == 0
    )
    if is_long_backtest_lock_active(lock):
        summary = build_research_lock_watch_only_summary(
            lock=lock,
            previous_summary=read_latest_paperops_autonomous_pass_summary(settings),
        )
    else:
        command_results = run_command_sequence(
            repo_root=ROOT,
            python_executable=sys.executable,
            allow_new_paper_submission=new_submission_allowed,
            execution_owner_env=execution_lease.environment(),
        )
        summary = build_paperops_autonomous_pass_summary(command_results)
    try:
        post_execution_reconciliation = ledger.sync_paper_mirror(
            phase="post_paperops_submission",
            bootstrap=False,
        )
    except Exception as exc:  # noqa: BLE001 - publish class, never provider text.
        ledger.set_execution_frozen(
            reason=f"post_execution_reconciliation_failed:{type(exc).__name__}"
        )
        post_execution_reconciliation = {
            "status": "blocked",
            "blockers": [f"post_execution_reconciliation_failed:{type(exc).__name__}"],
        }
    post_wrapper_reconciliation = persist_handoff_consumption(
        handoff_consumer,
        settings,
    )
    rejection_reasons = sorted(
        {
            str(reason)
            for record in handoff_consumer.get("rejections", [])
            if isinstance(record, dict)
            for reason in record.get("rejection_reasons", [])
            if str(reason)
        }
    )
    summary["router_v3_handoff_boundary"] = {
        "status": handoff_consumer.get("status"),
        "enforcement_active": handoff_consumer.get("enforcement_active") is True,
        "canonical_wrapper_only": handoff_consumer.get("canonical_wrapper_only") is True,
        "handoff_count": handoff_consumer.get("handoff_count", 0),
        "consumption_receipt_count": handoff_consumer.get("receipt_count", 0),
        "accepted_handoff_count": handoff_consumer.get("accepted_handoff_count", 0),
        "rejected_handoff_count": handoff_consumer.get("rejected_handoff_count", 0),
        "rejection_reasons": rejection_reasons,
        "new_paper_submission_allowed": new_submission_allowed,
        "router_check_status": router_checks.get("status"),
        "consumer_check_status": consumer_checks.get("status"),
        "post_wrapper_reconciliation_status": post_wrapper_reconciliation.get(
            "status"
        ),
        "reconciled_submitted_handoff_count": post_wrapper_reconciliation.get(
            "reconciled_submitted_handoff_count", 0
        ),
        "paper_order_created_count": 0,
        "broker_write_count": 0,
        "live_capital_enabled": False,
    }
    lifecycle_state, lifecycle_checks, lifecycle_errors = build_and_write_paper_lineage_and_proof(
        settings
    )
    summary["paper_lifecycle_v3_boundary"] = {
        "status": lifecycle_checks.get("status"),
        "implementation_ready": lifecycle_checks.get("implementation_ready") is True,
        "broker_record_count": lifecycle_checks.get("broker_record_count", 0),
        "ambiguous_order_count": lifecycle_checks.get("ambiguous_order_count", 0),
        "reconciliation_required_count": lifecycle_checks.get("reconciliation_required_count", 0),
        "every_record_has_origin_class": lifecycle_checks.get("every_record_has_origin_class")
        is True,
        "qadam_origin_complete_lineage_count": lifecycle_checks.get(
            "qadam_origin_complete_lineage_count", 0
        ),
        "qadam_origin_verified_closed_trade_count": lifecycle_checks.get(
            "qadam_origin_verified_closed_trade_count", 0
        ),
        "mirror_only_historical_record_count": lifecycle_checks.get(
            "mirror_only_historical_record_count", 0
        ),
        "proof_eligible_count": lifecycle_checks.get("proof_eligible_count", 0),
        "proof_credit_created_count": lifecycle_checks.get("proof_credit_created_count", 0),
        "mirror_record_backfill_proof_credit_count": lifecycle_checks.get(
            "mirror_record_backfill_proof_credit_count", 0
        ),
        "validation_error_count": len(lifecycle_errors),
        "paper_order_created_count": lifecycle_checks.get("paper_order_created_count", 0),
        "broker_write_count": lifecycle_checks.get("broker_write_count", 0),
        "live_capital_enabled": False,
        "lifecycle_state": lifecycle_state.get("lifecycle", {}).get("status"),
    }
    submitted_count = int(
        summary.get("paper_runtime", {}).get("submitted_paper_order_count") or 0
    )
    liveness = ledger.record_liveness_cycle(
        generation_id=str(
            router_state.get("generated_at")
            or router_state.get("generation_id")
            or summary.get("generated_at")
        ),
        decisions=[
            record
            for record in router_state.get("decisions", [])
            if isinstance(record, dict)
        ],
        submitted_order_count=submitted_count,
    )
    cohorts = ledger.rebuild_cohorts()
    operating_ledger_summary = ledger.summary()
    ledger.write_summary()
    summary["simplified_operating_architecture"] = {
        "status": operating_ledger_summary.get("status"),
        "authoritative_store": "qadam-control-plane.sqlite3",
        "single_execution_owner": True,
        "execution_owner_id": owner_id,
        "research_generation": research_generation,
        "pre_execution_reconciliation": pre_execution_reconciliation,
        "post_execution_reconciliation": post_execution_reconciliation,
        "validated_lane_order_count": operating_ledger_summary.get(
            "trading_lanes", {}
        ).get("validated", 0),
        "discovery_lane_order_count": operating_ledger_summary.get(
            "trading_lanes", {}
        ).get("discovery", 0),
        "exit_plan_count": operating_ledger_summary.get("counts", {}).get(
            "exit_plans", 0
        ),
        "cohort_count": len(cohorts),
        "liveness": liveness,
        "paper_only": True,
        "live_capital_enabled": False,
    }
    summary["validation_errors"] = validate_paperops_autonomous_pass_summary(summary)
    summary["validation_error_count"] = len(summary["validation_errors"])
    if summary["validation_errors"] and summary.get("status") == "ready_idle":
        summary["status"] = "degraded"
    output_path = write_paperops_autonomous_pass_summary(summary, settings=settings)

    print(f"paperops_autonomous_pass_summary_path={output_path}")
    print(f"paperops_autonomous_pass_status={summary['status']}")
    print(f"paperops_autonomous_pass_run_day={summary['paper_growth_trial']['run_day']}")
    print(
        "paperops_autonomous_pass_qualified_setup_count="
        f"{summary['paper_proof_ledger']['qualified_setup_count']}"
    )
    print(
        "paperops_autonomous_pass_fresh_eligible_submit_count="
        f"{summary['paper_runtime']['fresh_eligible_submit_count']}"
    )
    print(
        "paperops_autonomous_pass_duplicate_submit_count="
        f"{summary['paper_runtime']['duplicate_submit_count']}"
    )
    print(
        "paperops_autonomous_pass_submit_regression_guard_status="
        f"{summary['submit_regression_guard']['status']}"
    )
    print(
        "paperops_autonomous_pass_submit_regression_guard_blocker_count="
        f"{summary['submit_regression_guard']['blocker_count']}"
    )
    print(
        "paperops_autonomous_pass_submit_regression_guard_fresh_ledger_collision_count="
        f"{summary['submit_regression_guard']['fresh_submitted_ledger_collision_count']}"
    )
    print(
        "paperops_autonomous_pass_submit_regression_guard_duplicate_misclassified_count="
        f"{summary['submit_regression_guard']['duplicate_misclassified_as_fresh_count']}"
    )
    print(
        "paperops_autonomous_pass_submit_regression_guard_source_stale_after_post_count="
        f"{summary['submit_regression_guard']['source_stale_after_post_tolerance_count']}"
    )
    print(
        "paperops_autonomous_pass_submitted_paper_order_count="
        f"{summary['paper_runtime']['submitted_paper_order_count']}"
    )
    print(
        "paperops_autonomous_pass_first_week_mandate_status="
        f"{summary['first_week_paper_trade_mandate']['status']}"
    )
    print(
        "paperops_autonomous_pass_first_week_mandate_active="
        f"{summary['first_week_paper_trade_mandate']['active']}"
    )
    print(
        "paperops_autonomous_pass_first_week_mandate_day_number="
        f"{summary['first_week_paper_trade_mandate']['day_number']}"
    )
    print(
        "paperops_autonomous_pass_first_week_mandate_daily_target_trade_count="
        f"{summary['first_week_paper_trade_mandate']['daily_target_trade_count']}"
    )
    print(
        "paperops_autonomous_pass_first_week_mandate_minimum_notional_usd="
        f"{summary['first_week_paper_trade_mandate']['minimum_notional_usd']}"
    )
    print(
        "paperops_autonomous_pass_first_week_mandate_daily_ready_submit_count="
        f"{summary['first_week_paper_trade_mandate']['daily_ready_submit_count']}"
    )
    print(
        "paperops_autonomous_pass_first_week_mandate_daily_submitted_count="
        f"{summary['first_week_paper_trade_mandate']['daily_submitted_count']}"
    )
    print(f"paperops_autonomous_pass_idle_reason={summary['paper_runtime']['idle_reason'] or ''}")
    print(
        "paperops_autonomous_pass_paper_ops_cycle_state="
        f"{summary['states']['paper_ops_cycle_state']}"
    )
    print(
        "paperops_autonomous_pass_active_automation_state="
        f"{summary['states']['active_automation_state']}"
    )
    print(
        "paperops_autonomous_pass_paper_live_certification_state="
        f"{summary['states']['paper_live_certification_state']}"
    )
    print(f"paperops_autonomous_pass_closeout_status={summary['states']['closeout_status']}")
    print(
        f"paperops_autonomous_pass_cockpit_mirror_state={summary['states']['cockpit_mirror_state']}"
    )
    print(f"paperops_autonomous_pass_blocker_count={summary['blocker_count']}")
    print("paperops_autonomous_pass_blockers=" + ",".join(summary["blockers"]))
    print(f"paperops_autonomous_pass_optional_gap_count={summary['optional_gap_count']}")
    print("paperops_autonomous_pass_optional_gaps=" + ",".join(summary["optional_gaps"]))
    print(
        "paperops_autonomous_pass_source_gap_visibility_status="
        f"{summary['source_gap_visibility']['status']}"
    )
    print(
        "paperops_autonomous_pass_source_gap_optional_count="
        f"{summary['source_gap_visibility']['optional_gap_count']}"
    )
    print(
        "paperops_autonomous_pass_source_gap_optional_keys="
        + ",".join(summary["source_gap_visibility"]["optional_gap_keys"])
    )
    print(
        "paperops_autonomous_pass_source_gap_trade_blocking_count="
        f"{summary['source_gap_visibility']['trade_blocking_source_gap_count']}"
    )
    print(
        "paperops_autonomous_pass_source_gap_silent_blocker_count="
        f"{summary['source_gap_visibility']['silent_blocker_count']}"
    )
    print(
        "paperops_autonomous_pass_edge_pattern_ledger_status="
        f"{summary['edge_pattern_ledger']['status']}"
    )
    print(
        "paperops_autonomous_pass_edge_pattern_ledger_sprint_day="
        f"{summary['edge_pattern_ledger']['sprint_day']}"
    )
    print(
        "paperops_autonomous_pass_edge_pattern_ledger_sprint_days_remaining="
        f"{summary['edge_pattern_ledger']['sprint_days_remaining']}"
    )
    print(
        "paperops_autonomous_pass_edge_pattern_ledger_candidate_pattern_count="
        f"{summary['edge_pattern_ledger']['candidate_pattern_count']}"
    )
    print(
        "paperops_autonomous_pass_edge_pattern_ledger_validated_edge_count="
        f"{summary['edge_pattern_ledger']['validated_edge_count']}"
    )
    print(
        "paperops_autonomous_pass_edge_pattern_ledger_criteria="
        f"{summary['edge_pattern_ledger']['criteria']}"
    )
    print(
        "paperops_autonomous_pass_edge_pattern_ledger_quantum_mode="
        f"{summary['edge_pattern_ledger']['quantum_mode']}"
    )
    print(
        "paperops_autonomous_pass_edge_pattern_ledger_quantum_core_gate="
        f"{summary['edge_pattern_ledger']['quantum_core_gate']}"
    )
    print(
        "paperops_autonomous_pass_edge_pattern_ledger_telegram_summary_status="
        f"{summary['edge_pattern_ledger']['telegram_summary_status']}"
    )
    print(f"paperops_autonomous_pass_validation_error_count={summary['validation_error_count']}")
    print("paperops_autonomous_pass_validation_errors=" + ",".join(summary["validation_errors"]))
    print(f"paperops_autonomous_pass_self_heal_enabled={summary['self_healing']['enabled']}")
    print(f"paperops_autonomous_pass_self_heal_needed={summary['self_healing']['needs_repair']}")
    print(f"paperops_autonomous_pass_self_heal_status={summary['self_healing']['status']}")
    print(
        "paperops_autonomous_pass_self_heal_trigger_reasons="
        + ",".join(summary["self_healing"]["trigger_reasons"])
    )
    return_code = 1 if summary["failed_commands"] or summary["validation_errors"] else 0
    _cleanup_execution_owner()
    atexit.unregister(_cleanup_execution_owner)
    return return_code


if __name__ == "__main__":
    raise SystemExit(main())
