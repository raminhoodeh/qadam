#!/usr/bin/env python3
"""Write the Q5-14 guarded end-to-end paper trade drill artifact."""

from __future__ import annotations

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from orchestrator.config import Settings  # noqa: E402
from orchestrator.phase5_paper_trade_drill import (  # noqa: E402
    build_phase5_paper_trade_drill,
    paper_trade_drill_paths,
    write_phase5_paper_trade_drill,
)


def main() -> int:
    settings = Settings.from_env()
    _output_path, _history_path, event_log_path = paper_trade_drill_paths(settings)
    if event_log_path.exists():
        event_log_path.unlink()

    bundle = build_phase5_paper_trade_drill(settings=settings)
    output_path, history_path, event_path, written = write_phase5_paper_trade_drill(
        bundle,
        settings=settings,
        record_event=True,
        event_log_path=event_log_path,
    )
    print(f"phase5_paper_trade_drill_status={written['status']}")
    print(f"phase5_paper_trade_drill_state={written['paper_trade_drill_state']}")
    print(
        "phase5_paper_trade_drill_complete="
        f"{written['paper_trade_drill_complete']}"
    )
    print(
        "phase5_paper_trade_drill_exit_gate_passed="
        f"{written['phase5_paper_trade_drill_exit_gate_passed']}"
    )
    print(f"phase5_paper_trade_drill_blocker_count={written['blocker_count']}")
    print(
        "phase5_paper_trade_drill_paper_submit_approval_state="
        f"{written['paper_submit_approval_state']}"
    )
    print(
        "phase5_paper_trade_drill_paper_submit_approval_present="
        f"{written['paper_submit_approval_present']}"
    )
    print(
        "phase5_paper_trade_drill_paper_submit_path_available_count="
        f"{written['paper_submit_path_available_count']}"
    )
    print(
        "phase5_paper_trade_drill_submitted_paper_order_count="
        f"{written['submitted_paper_order_count']}"
    )
    print(
        "phase5_paper_trade_drill_open_position_count="
        f"{written['open_position_count']}"
    )
    print(
        "phase5_paper_trade_drill_closed_trade_count="
        f"{written['closed_trade_count']}"
    )
    print(
        "phase5_paper_trade_drill_postmortem_due_count="
        f"{written['postmortem_due_count']}"
    )
    print(
        "phase5_paper_trade_drill_event_log_written="
        f"{written['event_log_written']}"
    )
    print(
        "phase5_paper_trade_drill_event_log_event_count="
        f"{written['event_log_event_count']}"
    )
    print(f"phase5_paper_trade_drill_artifact_path={output_path}")
    print(f"phase5_paper_trade_drill_history_path={history_path}")
    print(f"phase5_paper_trade_drill_event_log_path={event_path}")
    if written.get("validation_errors"):
        print("phase5_paper_trade_drill_validation_errors=" + ",".join(written["validation_errors"]))
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
