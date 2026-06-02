#!/usr/bin/env python3
"""Validate the first-week paper-only trade mandate."""

from __future__ import annotations

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from orchestrator.config import Settings  # noqa: E402
from orchestrator.paperops_first_week_paper_trade_mandate import (  # noqa: E402
    build_first_week_paper_trade_mandate,
    validate_first_week_paper_trade_mandate,
    write_first_week_paper_trade_mandate,
)


def main() -> int:
    settings = Settings.from_env()
    artifact = build_first_week_paper_trade_mandate(settings)
    output_path, history_path, event_path, written = write_first_week_paper_trade_mandate(
        artifact,
        settings=settings,
        record_event=True,
    )
    validation_errors = validate_first_week_paper_trade_mandate(written)

    print(f"paperops_first_week_trade_mandate_status={written['status']}")
    print(f"paperops_first_week_trade_mandate_artifact_path={output_path}")
    print(f"paperops_first_week_trade_mandate_history_path={history_path}")
    print(f"paperops_first_week_trade_mandate_event_log_path={event_path}")
    print(f"paperops_first_week_trade_mandate_active={written['active']}")
    print(f"paperops_first_week_trade_mandate_start_date={written['start_date']}")
    print(f"paperops_first_week_trade_mandate_end_date={written['end_date']}")
    print(f"paperops_first_week_trade_mandate_local_date={written['local_date']}")
    print(f"paperops_first_week_trade_mandate_day_number={written['day_number']}")
    print(
        "paperops_first_week_trade_mandate_daily_target_trade_count="
        f"{written['daily_target_trade_count']}"
    )
    print(
        "paperops_first_week_trade_mandate_minimum_notional_usd="
        f"{written['minimum_notional_usd']}"
    )
    print(
        "paperops_first_week_trade_mandate_daily_decision_count="
        f"{written['daily_decision_count']}"
    )
    print(
        "paperops_first_week_trade_mandate_daily_ready_submit_count="
        f"{written['daily_ready_submit_count']}"
    )
    print(
        "paperops_first_week_trade_mandate_daily_submitted_count="
        f"{written['daily_submitted_count']}"
    )
    print(
        "paperops_first_week_trade_mandate_daily_remaining_submit_count="
        f"{written['daily_remaining_submit_count']}"
    )
    print(f"paperops_first_week_trade_mandate_paper_only={written['paper_only']}")
    print(
        "paperops_first_week_trade_mandate_live_capital_enabled="
        f"{written['live_capital_enabled']}"
    )
    print(
        "paperops_first_week_trade_mandate_proof_credit_allowed="
        f"{written['proof_credit_allowed']}"
    )
    print(
        "paperops_first_week_trade_mandate_validation_errors="
        f"{validation_errors}"
    )

    if validation_errors:
        print("paperops_first_week_trade_mandate_check=failed")
        return 1
    print("paperops_first_week_trade_mandate_check=ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
