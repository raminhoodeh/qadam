#!/usr/bin/env python3
"""Validate the PT-0 paper-live activation charter."""

from __future__ import annotations

from copy import deepcopy
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from orchestrator.config import Settings  # noqa: E402
from orchestrator.event_log import EventLog  # noqa: E402
from orchestrator.paper_live_activation import (  # noqa: E402
    PAPER_LIVE_ACTIVATION_SCHEMA_VERSION,
    build_paper_live_activation,
    paper_live_activation_paths,
    validate_paper_live_activation,
    write_paper_live_activation,
)


def main() -> int:
    errors: list[str] = []
    settings = Settings.from_env()
    output_path, history_path, event_log_path = paper_live_activation_paths(settings)
    if event_log_path.exists():
        event_log_path.unlink()

    artifact = build_paper_live_activation(settings=settings)
    output_path, history_path, event_log_path, written = write_paper_live_activation(
        artifact,
        settings=settings,
        record_event=True,
        event_log_path=event_log_path,
    )
    validation_errors = validate_paper_live_activation(written)
    replay = EventLog(event_log_path, echo=False).replay()

    live_capital_probe = deepcopy(written)
    live_capital_probe["live_capital_enabled"] = True
    live_capital_errors = validate_paper_live_activation(live_capital_probe)

    env_probe = deepcopy(written)
    env_probe["env_file_edited"] = True
    env_errors = validate_paper_live_activation(env_probe)

    submission_probe = deepcopy(written)
    submission_probe["paper_order_submission_allowed"] = True
    submission_errors = validate_paper_live_activation(submission_probe)

    broker_probe = deepcopy(written)
    broker_probe["broker_post_called_count"] = 1
    broker_probe["alpaca_post_called_count"] = 1
    broker_errors = validate_paper_live_activation(broker_probe)

    proof_probe = deepcopy(written)
    proof_probe["phase7_proof_credit_allowed"] = True
    proof_errors = validate_paper_live_activation(proof_probe)

    forced_trade_probe = deepcopy(written)
    forced_trade_probe["forced_trades_allowed"] = True
    forced_trade_errors = validate_paper_live_activation(forced_trade_probe)

    qctrl_execution_probe = deepcopy(written)
    qctrl_execution_probe["qctrl_direct_execution_allowed"] = True
    qctrl_execution_errors = validate_paper_live_activation(qctrl_execution_probe)

    qctrl_broker_probe = deepcopy(written)
    qctrl_broker_probe["qctrl_broker_post_allowed"] = True
    qctrl_broker_errors = validate_paper_live_activation(qctrl_broker_probe)

    manual_approval_probe = deepcopy(written)
    manual_approval_probe["per_trade_manual_approval_required"] = True
    manual_approval_errors = validate_paper_live_activation(manual_approval_probe)

    event_probe = deepcopy(written)
    event_probe["event_log_written"] = False
    event_probe["event_log_event_count"] = 0
    event_errors = validate_paper_live_activation(event_probe)

    print(f"paper_live_activation_status={written['status']}")
    print(f"paper_live_activation_schema_version={PAPER_LIVE_ACTIVATION_SCHEMA_VERSION}")
    print(f"paper_live_activation_artifact_path={output_path}")
    print(f"paper_live_activation_history_path={history_path}")
    print(f"paper_live_activation_event_log_path={event_log_path}")
    print(f"paper_live_activation_mode={written['mode']}")
    print(f"paper_live_activation_approval_state={written['approval_state']}")
    print(f"paper_live_activation_approval_scope={written['approval_scope']}")
    print(f"paper_live_activation_approval_logged={written['approval_logged']}")
    print(
        "paper_live_activation_approved="
        f"{written['paper_live_activation_approved']}"
    )
    print(
        "paper_live_activation_system_approval_logged="
        f"{written['paper_trading_system_approval_logged']}"
    )
    print(f"paper_live_activation_mode_defined={written['paper_live_mode_defined']}")
    print(f"paper_live_activation_paper_live_mode={written['paper_live_mode']}")
    print(f"paper_live_activation_broker_scope={written['broker_scope']}")
    print(f"paper_live_activation_live_capital_enabled={written['live_capital_enabled']}")
    print(f"paper_live_activation_live_endpoint_allowed={written['live_endpoint_allowed']}")
    print(f"paper_live_activation_env_file_edited={written['env_file_edited']}")
    print(
        "paper_live_activation_per_trade_manual_approval_required="
        f"{written['per_trade_manual_approval_required']}"
    )
    print(
        "paper_live_activation_paper_order_submission_allowed="
        f"{written['paper_order_submission_allowed']}"
    )
    print(
        "paper_live_activation_broker_post_called_count="
        f"{written['broker_post_called_count']}"
    )
    print(
        "paper_live_activation_alpaca_post_called_count="
        f"{written['alpaca_post_called_count']}"
    )
    print(
        "paper_live_activation_live_endpoint_called_count="
        f"{written['live_endpoint_called_count']}"
    )
    print(
        "paper_live_activation_phase7_proof_credit_allowed="
        f"{written['phase7_proof_credit_allowed']}"
    )
    print(
        "paper_live_activation_phase7_proof_rules_separate="
        f"{written['phase7_proof_rules_separate']}"
    )
    print(f"paper_live_activation_forced_trades_allowed={written['forced_trades_allowed']}")
    print(
        "paper_live_activation_qctrl_consultation_required="
        f"{written['qctrl_consultation_required']}"
    )
    print(
        "paper_live_activation_qctrl_direct_execution_allowed="
        f"{written['qctrl_direct_execution_allowed']}"
    )
    print(
        "paper_live_activation_qctrl_broker_post_allowed="
        f"{written['qctrl_broker_post_allowed']}"
    )
    print(f"paper_live_activation_max_order_notional_gbp={written['max_order_notional_gbp']}")
    print(f"paper_live_activation_daily_trade_cap={written['daily_trade_cap']}")
    print(
        "paper_live_activation_max_concurrent_positions="
        f"{written['max_concurrent_positions']}"
    )
    print(
        "paper_live_activation_max_daily_loss_fraction="
        f"{written['max_daily_loss_fraction']}"
    )
    print(f"paper_live_activation_max_drawdown_fraction={written['max_drawdown_fraction']}")
    print(
        "paper_live_activation_emergency_kill_switch_required="
        f"{written['emergency_kill_switch_required']}"
    )
    print(f"paper_live_activation_event_log_events={replay['total_events']}")
    print(f"paper_live_activation_validation_errors={validation_errors}")

    if validation_errors:
        errors.append(f"paper-live validation failed: {validation_errors}")
    if replay["total_events"] != 1:
        errors.append("paper-live event log did not record exactly one event")
    if written["approval_state"] != "approved":
        errors.append("paper-live approval state is not approved")
    if written["approval_logged"] is not True:
        errors.append("paper-live approval was not logged")
    if written["paper_live_activation_approved"] is not True:
        errors.append("paper-live activation approval is false")
    if written["paper_trading_system_approval_logged"] is not True:
        errors.append("paper trading system approval was not logged")
    if written["per_trade_manual_approval_required"] is not False:
        errors.append("PT-0 should not require per-trade manual approval")
    if written["paper_order_submission_allowed"] is not False:
        errors.append("PT-0 opened paper order submission")
    if written["live_capital_enabled"] is not False:
        errors.append("PT-0 enabled live capital")
    if written["broker_post_called_count"] or written["alpaca_post_called_count"]:
        errors.append("PT-0 called broker/Alpaca POST")
    if "paper_live_activation_forbidden:live_capital_enabled" not in live_capital_errors:
        errors.append("live-capital probe was not rejected")
    if "paper_live_activation_forbidden:env_file_edited" not in env_errors:
        errors.append("env-file probe was not rejected")
    if "paper_live_activation_forbidden:paper_order_submission_allowed" not in submission_errors:
        errors.append("paper-order-submission probe was not rejected")
    if (
        "paper_live_activation_unsafe_counter_nonzero:broker_post_called_count"
        not in broker_errors
    ):
        errors.append("broker POST probe was not rejected")
    if "paper_live_activation_forbidden:phase7_proof_credit_allowed" not in proof_errors:
        errors.append("Phase 7 proof-credit probe was not rejected")
    if "paper_live_activation_forbidden:forced_trades_allowed" not in forced_trade_errors:
        errors.append("forced-trade probe was not rejected")
    if (
        "paper_live_activation_forbidden:qctrl_direct_execution_allowed"
        not in qctrl_execution_errors
    ):
        errors.append("Q-CTRL execution probe was not rejected")
    if "paper_live_activation_forbidden:qctrl_broker_post_allowed" not in qctrl_broker_errors:
        errors.append("Q-CTRL broker-post probe was not rejected")
    if (
        "paper_live_activation_forbidden:per_trade_manual_approval_required"
        not in manual_approval_errors
    ):
        errors.append("manual trade-level approval probe was not rejected")
    if "paper_live_activation_event_log_missing" not in event_errors:
        errors.append("missing-event probe was not rejected")

    if errors:
        print("paper_live_activation_check=failed")
        for error in errors:
            print(f"error={error}")
        return 1
    print("paper_live_activation_check=ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
