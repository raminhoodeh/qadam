#!/usr/bin/env python3
"""Poll Telegram for member-submitted read-only research intake."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from orchestrator.config import Settings  # noqa: E402
from orchestrator.strategy_research_intake import (  # noqa: E402
    build_strategy_research_intake,
    validate_strategy_research_intake,
    write_strategy_research_intake,
)
from orchestrator.telegram_inbound_intake import (  # noqa: E402
    poll_telegram_inbound_updates,
    telegram_inbound_intake_public_status,
)


def main() -> int:
    settings = Settings.from_env()
    errors: list[str] = []
    poll_result = poll_telegram_inbound_updates(settings=settings)
    public_status = telegram_inbound_intake_public_status(settings)

    strategy_artifact = build_strategy_research_intake(settings)
    _, _, _, written_strategy = write_strategy_research_intake(
        strategy_artifact,
        settings,
        record_event=True,
    )
    strategy_errors = validate_strategy_research_intake(written_strategy)

    print(f"telegram_inbound_poll_status={poll_result.get('status')}")
    print(f"telegram_inbound_poll_fetched_update_count={poll_result.get('fetched_update_count', 0)}")
    print(f"telegram_inbound_poll_created_count={poll_result.get('created_count', 0)}")
    print(f"telegram_inbound_poll_duplicate_count={poll_result.get('duplicate_count', 0)}")
    print(f"telegram_inbound_poll_ignored_count={poll_result.get('ignored_count', 0)}")
    print(f"telegram_inbound_poll_record_count={public_status.get('record_count', 0)}")
    print(
        "telegram_inbound_poll_world_event_datapoint_count="
        f"{public_status.get('world_event_datapoint_count', 0)}"
    )
    print(
        "telegram_inbound_poll_strategy_consideration_count="
        f"{public_status.get('strategy_consideration_count', 0)}"
    )
    print(
        "telegram_inbound_poll_strategy_research_consideration_count="
        f"{written_strategy.get('user_strategy_consideration_count', 0)}"
    )
    print(f"telegram_inbound_poll_strategy_validation_error_count={len(strategy_errors)}")

    if poll_result.get("status") != "ok":
        errors.append(f"telegram_inbound_poll_not_ok:{poll_result.get('status')}")
    if strategy_errors:
        errors.extend(strategy_errors)
    for field in (
        "trade_candidate_creation_allowed",
        "risk_handoff_allowed",
        "execution_allowed",
        "paper_order_allowed",
        "broker_write_allowed",
        "telegram_command_authority",
        "live_capital_enabled",
    ):
        if public_status.get(field) is not False:
            errors.append(f"telegram_inbound_poll_authority_enabled:{field}")

    if errors:
        for error in errors:
            print(f"telegram_inbound_poll_error={error}")
        print("telegram_inbound_poll_check=failed")
        return 1

    print("telegram_inbound_poll_check=ok")
    print("telegram_inbound_poll_boundary=read-only member research intake; no trade authority")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
