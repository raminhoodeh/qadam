#!/usr/bin/env python3
"""Run one guarded PaperOps autonomous pass and emit one canonical summary."""

from __future__ import annotations

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from orchestrator.config import Settings  # noqa: E402
from orchestrator.paperops_autonomous_pass import (  # noqa: E402
    build_research_lock_watch_only_summary,
    build_paperops_autonomous_pass_summary,
    read_latest_paperops_autonomous_pass_summary,
    run_command_sequence,
    write_paperops_autonomous_pass_summary,
)
from orchestrator.qadam_next_generation_safety_lock import (  # noqa: E402
    is_long_backtest_lock_active,
    read_long_backtest_lock,
)


def main() -> int:
    settings = Settings.from_env()
    lock = read_long_backtest_lock(settings)
    if is_long_backtest_lock_active(lock):
        summary = build_research_lock_watch_only_summary(
            lock=lock,
            previous_summary=read_latest_paperops_autonomous_pass_summary(settings),
        )
    else:
        command_results = run_command_sequence(
            repo_root=ROOT,
            python_executable=sys.executable,
        )
        summary = build_paperops_autonomous_pass_summary(command_results)
    output_path = write_paperops_autonomous_pass_summary(summary, settings=settings)

    print(f"paperops_autonomous_pass_summary_path={output_path}")
    print(f"paperops_autonomous_pass_status={summary['status']}")
    print(
        "paperops_autonomous_pass_run_day="
        f"{summary['paper_growth_trial']['run_day']}"
    )
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
    print(
        "paperops_autonomous_pass_idle_reason="
        f"{summary['paper_runtime']['idle_reason'] or ''}"
    )
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
    print(
        "paperops_autonomous_pass_closeout_status="
        f"{summary['states']['closeout_status']}"
    )
    print(
        "paperops_autonomous_pass_cockpit_mirror_state="
        f"{summary['states']['cockpit_mirror_state']}"
    )
    print(f"paperops_autonomous_pass_blocker_count={summary['blocker_count']}")
    print("paperops_autonomous_pass_blockers=" + ",".join(summary["blockers"]))
    print(f"paperops_autonomous_pass_optional_gap_count={summary['optional_gap_count']}")
    print(
        "paperops_autonomous_pass_optional_gaps="
        + ",".join(summary["optional_gaps"])
    )
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
    print(
        "paperops_autonomous_pass_validation_error_count="
        f"{summary['validation_error_count']}"
    )
    print(
        "paperops_autonomous_pass_validation_errors="
        + ",".join(summary["validation_errors"])
    )
    print(
        "paperops_autonomous_pass_self_heal_enabled="
        f"{summary['self_healing']['enabled']}"
    )
    print(
        "paperops_autonomous_pass_self_heal_needed="
        f"{summary['self_healing']['needs_repair']}"
    )
    print(
        "paperops_autonomous_pass_self_heal_status="
        f"{summary['self_healing']['status']}"
    )
    print(
        "paperops_autonomous_pass_self_heal_trigger_reasons="
        + ",".join(summary["self_healing"]["trigger_reasons"])
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
