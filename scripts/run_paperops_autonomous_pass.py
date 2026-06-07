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
    build_paperops_autonomous_pass_summary,
    run_command_sequence,
    write_paperops_autonomous_pass_summary,
)


def main() -> int:
    settings = Settings.from_env()
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
