#!/usr/bin/env python3
"""Validate RS-0 paper authority reconciliation.

This check answers whether Qadam is authorized for guarded paper trading and
what currently blocks action. It does not require the recurring scheduler to be
armed; that remains the job of the stricter PT-8 active automation check.
"""

from __future__ import annotations

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from orchestrator.config import Settings  # noqa: E402
from orchestrator.paper_authority_reconciliation import (  # noqa: E402
    PAPER_AUTHORITY_RECONCILIATION_SCHEMA_VERSION,
    build_paper_authority_reconciliation,
    validate_paper_authority_reconciliation,
)
from orchestrator.paperops_active_paper_trading_automation import (  # noqa: E402
    build_paperops_active_paper_trading_automation,
    write_paperops_active_paper_trading_automation,
)


def main() -> int:
    errors: list[str] = []
    settings = Settings.from_env()
    active_artifact = build_paperops_active_paper_trading_automation(settings=settings)
    _, _, _, active_written = write_paperops_active_paper_trading_automation(
        active_artifact,
        settings=settings,
        record_event=True,
    )
    contract = build_paper_authority_reconciliation(
        {
            "paperops_active_paper_trading_automation": active_written,
        },
        settings=settings,
        generated_at=active_written.get("generated_at"),
    )
    validation_errors = validate_paper_authority_reconciliation(contract)

    print(f"paper_authority_reconciliation_status={contract['status']}")
    print(
        "paper_authority_reconciliation_schema_version="
        f"{PAPER_AUTHORITY_RECONCILIATION_SCHEMA_VERSION}"
    )
    print(
        "paper_authority_reconciliation_paper_authorized="
        f"{contract['paper_authorized']}"
    )
    print(
        "paper_authority_reconciliation_paper_submit_currently_allowed="
        f"{contract['paper_submit_currently_allowed']}"
    )
    print(
        "paper_authority_reconciliation_paper_poll_currently_allowed="
        f"{contract['paper_poll_currently_allowed']}"
    )
    print(
        "paper_authority_reconciliation_paper_exit_currently_allowed="
        f"{contract['paper_exit_currently_allowed']}"
    )
    print(
        "paper_authority_reconciliation_live_capital_enabled="
        f"{contract['live_capital_enabled']}"
    )
    print(
        "paper_authority_reconciliation_full_potential_state="
        f"{contract['full_potential_state']}"
    )
    print(
        "paper_authority_reconciliation_current_blockers="
        f"{','.join(contract['current_blockers'])}"
    )
    print(
        "paper_authority_reconciliation_idle_reasons="
        f"{','.join(contract['idle_reasons'])}"
    )
    print(
        "paper_authority_reconciliation_downstream_waiting_reasons="
        f"{','.join(contract['downstream_waiting_reasons'])}"
    )
    print(
        "paper_authority_reconciliation_trade_path_unblocked="
        f"{contract['trade_path_unblocked']}"
    )
    print(
        "paper_authority_reconciliation_safety_blockers="
        f"{','.join(contract['safety_blockers'])}"
    )
    print(
        "paper_authority_reconciliation_operational_blockers="
        f"{','.join(contract['operational_blockers'])}"
    )
    print(
        "paper_authority_reconciliation_opportunity_or_risk_blockers="
        f"{','.join(contract['opportunity_or_risk_blockers'])}"
    )
    print(
        "paper_authority_reconciliation_stale_historical_blocker_count="
        f"{contract['stale_historical_blocker_count']}"
    )
    print(
        "paper_authority_reconciliation_why_not_trading_now="
        f"{contract['why_not_trading_now']}"
    )
    print(
        "paper_authority_reconciliation_next_required_action="
        f"{contract['next_required_action']}"
    )
    print(
        "paper_authority_reconciliation_active_automation_status="
        f"{active_written['status']}"
    )
    print(
        "paper_authority_reconciliation_active_automation_validation_error_count="
        f"{active_written['validation_error_count']}"
    )
    print(
        "paper_authority_reconciliation_validation_errors="
        f"{validation_errors}"
    )

    if validation_errors:
        errors.append(f"RS-0 validation failed: {validation_errors}")
    if contract["public_safe"] is not True:
        errors.append("RS-0 contract is not public-safe")
    if contract["live_capital_enabled"] is not False:
        errors.append("RS-0 contract enabled live capital")
    if contract["live_capital_blocked"] is not True:
        errors.append("RS-0 contract did not block live capital")
    if contract["paper_submission_transport"] != "paperops_guarded_alpaca_paper":
        errors.append("RS-0 transport is not guarded Alpaca paper")
    if contract["status"] == "paper_authorized_blocked_operational" and (
        "automation_not_active" not in contract["operational_blockers"]
    ):
        errors.append("RS-0 operational blocker classification hid paused automation")
    if contract["paper_submit_currently_allowed"] is True and (
        active_written.get("paper_submit_step_allowed") is not True
    ):
        errors.append("RS-0 invented paper submit authority")
    if contract["safety_blockers"]:
        errors.append("RS-0 has safety blockers: " + ",".join(contract["safety_blockers"]))
    if "no_fresh_eligible_candidate" in contract["current_blockers"]:
        errors.append("RS-0 misclassified idle no-fresh-candidate as a current blocker")
    if "no_fresh_eligible_candidate" in contract["opportunity_or_risk_blockers"]:
        errors.append("RS-0 misclassified idle no-fresh-candidate as a risk blocker")
    if contract["trade_path_unblocked"] is not (
        not contract["safety_blockers"] and not contract["operational_blockers"]
    ):
        errors.append("RS-0 trade_path_unblocked does not match safety/ops state")

    if errors:
        print("paper_authority_reconciliation_check=failed")
        for error in errors:
            print(f"error={error}")
        return 1
    print("paper_authority_reconciliation_check=ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
