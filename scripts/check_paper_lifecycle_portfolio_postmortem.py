#!/usr/bin/env python3
"""Validate RS-6 paper lifecycle, portfolio, and postmortem hardening."""

from __future__ import annotations

from copy import deepcopy
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from orchestrator.config import Settings  # noqa: E402
from orchestrator.paper_lifecycle_portfolio_postmortem import (  # noqa: E402
    build_paper_lifecycle_portfolio_postmortem,
    validate_paper_lifecycle_portfolio_postmortem,
    write_paper_lifecycle_portfolio_postmortem,
)


def _expect_rejected(payload: dict, expected_error: str) -> str | None:
    errors = validate_paper_lifecycle_portfolio_postmortem(payload)
    if expected_error not in errors:
        return f"expected_probe_error_missing:{expected_error}"
    return None


def _run_negative_probes(artifact: dict) -> list[str]:
    probe_errors: list[str] = []

    display_inferred = deepcopy(artifact)
    display_inferred["portfolio_value_source"] = "display_inferred"
    if error := _expect_rejected(
        display_inferred,
        "portfolio_value_display_inferred",
    ):
        probe_errors.append(error)

    missing_postmortem = deepcopy(artifact)
    if missing_postmortem.get("closed_trade_postmortem_records"):
        missing_postmortem["closed_trade_postmortem_records"][0][
            "postmortem_record_present"
        ] = False
        missing_postmortem["closed_trade_missing_postmortem_count"] = 1
        missing_postmortem["closed_trade_postmortem_coverage_satisfied"] = False
        missing_postmortem["acceptance"][
            "closed_paper_trades_have_postmortem_markers"
        ] = False
        if error := _expect_rejected(
            missing_postmortem,
            "closed_trade_postmortem_coverage_not_satisfied",
        ):
            probe_errors.append(error)

    mirror_proof = deepcopy(artifact)
    mirror_proof["mirror_trade_counted_for_proof_count"] = 1
    if error := _expect_rejected(mirror_proof, "mirror_trade_counted_for_proof"):
        probe_errors.append(error)

    authority_enabled = deepcopy(artifact)
    authority_enabled["write_authority"] = True
    if error := _expect_rejected(authority_enabled, "write_authority_enabled"):
        probe_errors.append(error)

    return probe_errors


def main() -> int:
    settings = Settings.from_env()
    artifact = write_paper_lifecycle_portfolio_postmortem(settings=settings)
    validation_errors = validate_paper_lifecycle_portfolio_postmortem(artifact)
    probe_errors = _run_negative_probes(build_paper_lifecycle_portfolio_postmortem(settings=settings))

    print("paper_lifecycle_portfolio_postmortem_status=" + artifact["status"])
    print(
        "paper_lifecycle_portfolio_postmortem_portfolio_value_source="
        + str(artifact["portfolio_value_source"])
    )
    print(
        "paper_lifecycle_portfolio_postmortem_balance_ticker_broker_account_derived="
        + str(artifact["balance_ticker_broker_account_derived"])
    )
    print(
        "paper_lifecycle_portfolio_postmortem_current_balance_gbp="
        + str(artifact["current_balance_gbp"])
    )
    print(
        "paper_lifecycle_portfolio_postmortem_open_position_count="
        + str(artifact["open_position_count"])
    )
    print(
        "paper_lifecycle_portfolio_postmortem_order_count="
        + str(artifact["order_count"])
    )
    print(
        "paper_lifecycle_portfolio_postmortem_closed_trade_count="
        + str(artifact["closed_trade_count"])
    )
    print(
        "paper_lifecycle_portfolio_postmortem_coverage_count="
        + str(artifact["closed_trade_postmortem_coverage_count"])
    )
    print(
        "paper_lifecycle_portfolio_postmortem_missing_postmortem_count="
        + str(artifact["closed_trade_missing_postmortem_count"])
    )
    print(
        "paper_lifecycle_portfolio_postmortem_postmortem_due_count="
        + str(artifact["postmortem_due_count"])
    )
    print(
        "paper_lifecycle_portfolio_postmortem_proof_verified_count="
        + str(artifact["paper_proof_ledger_verified_record_count"])
    )
    print(
        "paper_lifecycle_portfolio_postmortem_close_to_ledger_status="
        + str(artifact["paperops_close_to_ledger_status"])
    )
    print(
        "paper_lifecycle_portfolio_postmortem_close_to_ledger_blocker_count="
        + str(artifact["paperops_close_to_ledger_blocker_count"])
    )
    print(
        "paper_lifecycle_portfolio_postmortem_close_to_ledger_postmortem_due_marker_created_count="
        + str(artifact["paperops_close_to_ledger_postmortem_due_marker_created_count"])
    )
    print(
        "paper_lifecycle_portfolio_postmortem_mirror_trade_counted_for_proof_count="
        + str(artifact["mirror_trade_counted_for_proof_count"])
    )
    print(
        "paper_lifecycle_portfolio_postmortem_validation_error_count="
        + str(len(validation_errors))
    )
    print(
        "paper_lifecycle_portfolio_postmortem_probe_error_count="
        + str(len(probe_errors))
    )
    print(
        "paper_lifecycle_portfolio_postmortem_report=data/runtime/"
        "paper_lifecycle_portfolio_postmortem.json"
    )
    print("paper_lifecycle_portfolio_postmortem_boundary=" + artifact["boundary"])

    if validation_errors:
        print("paper_lifecycle_portfolio_postmortem_validation_errors=" + ",".join(validation_errors))
        return 1
    if probe_errors:
        print("paper_lifecycle_portfolio_postmortem_probe_errors=" + ",".join(probe_errors))
        return 1
    if artifact.get("live_capital_enabled") is not False:
        print("paper_lifecycle_portfolio_postmortem_live_capital_enabled=true")
        return 1
    if artifact.get("write_authority") is not False:
        print("paper_lifecycle_portfolio_postmortem_write_authority_enabled=true")
        return 1
    if artifact.get("paper_proof_ledger_uses_verified_lifecycle_only") is not True:
        print("paper_lifecycle_portfolio_postmortem_proof_policy_invalid=true")
        return 1
    print("paper_lifecycle_portfolio_postmortem_check=ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
