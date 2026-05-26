#!/usr/bin/env python3
"""Write the Q5-15 Phase 5 certification artifact."""

from __future__ import annotations

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from orchestrator.config import Settings  # noqa: E402
from orchestrator.phase5_certification import (  # noqa: E402
    build_phase5_certification,
    write_phase5_certification,
)


def main() -> int:
    settings = Settings.from_env()
    artifact = build_phase5_certification(settings=settings)
    output_path, history_path, event_path, written = write_phase5_certification(
        artifact,
        settings=settings,
        record_event=True,
    )
    print(f"phase5_certification_status={written['status']}")
    print(f"phase5_certification_stage_status={written['stage_status']}")
    print(f"phase5_certification_phase5_certified={written['phase5_certified']}")
    print(f"phase5_certification_phase5_exit_gate={written['phase5_exit_gate']}")
    print(f"phase5_certification_phase6_handoff_allowed={written['phase6_handoff_allowed']}")
    print(f"phase5_certification_phase7_planning_allowed={written['phase7_planning_allowed']}")
    print(
        "phase5_certification_phase7_proof_credit_allowed="
        f"{written['phase7_proof_credit_allowed']}"
    )
    print(f"phase5_certification_input_gate_count={written['input_gate_count']}")
    print(f"phase5_certification_input_gate_passed_count={written['input_gate_passed_count']}")
    print(f"phase5_certification_input_gate_blocked_count={written['input_gate_blocked_count']}")
    print(f"phase5_certification_blocker_count={written['certification_blocker_count']}")
    print(
        "phase5_certification_paper_trade_drill_complete="
        f"{written['paper_trade_drill_complete']}"
    )
    print(
        "phase5_certification_paper_trade_drill_exit_gate_passed="
        f"{written['paper_trade_drill_exit_gate_passed']}"
    )
    print(
        "phase5_certification_submitted_paper_order_count="
        f"{written['submitted_paper_order_count']}"
    )
    print(f"phase5_certification_open_position_count={written['open_position_count']}")
    print(f"phase5_certification_closed_trade_count={written['closed_trade_count']}")
    print(f"phase5_certification_postmortem_due_count={written['postmortem_due_count']}")
    print(f"phase5_certification_live_capital_enabled_count={written['live_capital_enabled_count']}")
    print(f"phase5_certification_event_log_written={written['event_log_written']}")
    print(f"phase5_certification_event_log_event_count={written['event_log_event_count']}")
    print(f"phase5_certification_artifact_path={output_path}")
    print(f"phase5_certification_history_path={history_path}")
    print(f"phase5_certification_event_log_path={event_path}")
    if written.get("validation_errors"):
        print(
            "phase5_certification_validation_errors="
            + ",".join(written["validation_errors"])
        )
    return 0 if not written.get("validation_errors") else 1


if __name__ == "__main__":
    raise SystemExit(main())
