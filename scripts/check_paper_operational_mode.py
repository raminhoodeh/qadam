#!/usr/bin/env python3
"""Validate PT-2 global PaperOps runtime mode."""

from __future__ import annotations

from copy import deepcopy
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from orchestrator.config import Settings  # noqa: E402
from orchestrator.event_log import EventLog  # noqa: E402
from orchestrator.paper_operational_mode import (  # noqa: E402
    PAPER_OPERATIONAL_MODE_SCHEMA_VERSION,
    build_paper_operational_mode,
    paper_operational_mode_paths,
    validate_paper_operational_mode,
    write_paper_operational_mode,
)


def main() -> int:
    errors: list[str] = []
    settings = Settings.from_env()
    output_path, history_path, event_log_path = paper_operational_mode_paths(settings)
    if event_log_path.exists():
        event_log_path.unlink()

    artifact = build_paper_operational_mode(settings)
    output_path, history_path, event_log_path, written = write_paper_operational_mode(
        artifact,
        settings=settings,
        record_event=True,
        event_log_path=event_log_path,
    )
    validation_errors = validate_paper_operational_mode(written)
    replay = EventLog(event_log_path, echo=False).replay()

    live_capital_probe = deepcopy(written)
    live_capital_probe["live_capital_enabled"] = True
    live_capital_errors = validate_paper_operational_mode(live_capital_probe)

    env_probe = deepcopy(written)
    env_probe["env_file_edited"] = True
    env_errors = validate_paper_operational_mode(env_probe)

    submission_probe = deepcopy(written)
    submission_probe["paper_order_submission_allowed"] = True
    submission_errors = validate_paper_operational_mode(submission_probe)

    broker_probe = deepcopy(written)
    broker_probe["broker_post_allowed"] = True
    broker_probe["broker_post_called_count"] = 1
    broker_errors = validate_paper_operational_mode(broker_probe)

    qctrl_probe = deepcopy(written)
    qctrl_probe["qctrl_direct_execution_allowed"] = True
    qctrl_probe["qctrl_broker_post_allowed"] = True
    qctrl_errors = validate_paper_operational_mode(qctrl_probe)

    proof_probe = deepcopy(written)
    proof_probe["phase7_proof_credit_allowed"] = True
    proof_errors = validate_paper_operational_mode(proof_probe)

    forced_trade_probe = deepcopy(written)
    forced_trade_probe["forced_trades_allowed"] = True
    forced_trade_errors = validate_paper_operational_mode(forced_trade_probe)

    secret_probe = deepcopy(written)
    secret_probe["secret_value_exposed"] = True
    secret_errors = validate_paper_operational_mode(secret_probe)

    event_probe = deepcopy(written)
    event_probe["event_log_written"] = False
    event_probe["event_log_event_count"] = 0
    event_errors = validate_paper_operational_mode(event_probe)

    print(f"paper_operational_mode_status={written['status']}")
    print(
        "paper_operational_mode_schema_version="
        f"{PAPER_OPERATIONAL_MODE_SCHEMA_VERSION}"
    )
    print(f"paper_operational_mode_artifact_path={output_path}")
    print(f"paper_operational_mode_history_path={history_path}")
    print(f"paper_operational_mode_event_log_path={event_log_path}")
    print(f"paper_operational_mode_mode={written['mode']}")
    print(
        "paper_operational_mode_enabled="
        f"{written['paper_operational_mode_enabled']}"
    )
    print(
        "paper_operational_mode_effective="
        f"{written['paper_operational_mode_effective']}"
    )
    print(
        "paper_operational_mode_settings_flag="
        f"{written['settings_paper_operational_enabled']}"
    )
    print(
        "paper_operational_mode_runtime_artifact_override_enabled="
        f"{written['runtime_artifact_override_enabled']}"
    )
    print(
        "paper_operational_mode_flag_disabled="
        f"{written['paper_operational_flag_disabled']}"
    )
    print(f"paper_operational_mode_env_file_edited={written['env_file_edited']}")
    print(
        "paper_operational_mode_pt0_activation_status="
        f"{written['pt0_activation_status']}"
    )
    print(
        "paper_operational_mode_pt0_activation_approved="
        f"{written['pt0_activation_approved']}"
    )
    print(
        "paper_operational_mode_pt0_system_approval_logged="
        f"{written['pt0_system_approval_logged']}"
    )
    print(
        "paper_operational_mode_pt1_product_access_status="
        f"{written['pt1_product_access_status']}"
    )
    print(
        "paper_operational_mode_pt1_product_access_checked="
        f"{written['pt1_product_access_checked']}"
    )
    print(
        "paper_operational_mode_pt1_provider_call_attempted="
        f"{written['pt1_provider_call_attempted']}"
    )
    print(
        "paper_operational_mode_pt1_provider_call_count="
        f"{written['pt1_provider_call_count']}"
    )
    print(
        "paper_operational_mode_qctrl_product_access_required="
        f"{written['qctrl_product_access_required_for_full_parity']}"
    )
    print(
        "paper_operational_mode_qctrl_product_access_verified="
        f"{written['qctrl_product_access_verified']}"
    )
    print(
        "paper_operational_mode_qctrl_product_access_blocker="
        f"{written['qctrl_product_access_blocker']}"
    )
    print(
        "paper_operational_mode_paper_order_submission_allowed="
        f"{written['paper_order_submission_allowed']}"
    )
    print(
        "paper_operational_mode_broker_post_called_count="
        f"{written['broker_post_called_count']}"
    )
    print(
        "paper_operational_mode_alpaca_post_called_count="
        f"{written['alpaca_post_called_count']}"
    )
    print(
        "paper_operational_mode_live_endpoint_called_count="
        f"{written['live_endpoint_called_count']}"
    )
    print(
        "paper_operational_mode_live_capital_enabled="
        f"{written['live_capital_enabled']}"
    )
    print(
        "paper_operational_mode_qctrl_direct_execution_allowed="
        f"{written['qctrl_direct_execution_allowed']}"
    )
    print(
        "paper_operational_mode_qctrl_broker_post_allowed="
        f"{written['qctrl_broker_post_allowed']}"
    )
    print(
        "paper_operational_mode_phase7_proof_credit_allowed="
        f"{written['phase7_proof_credit_allowed']}"
    )
    print(
        "paper_operational_mode_forced_trades_allowed="
        f"{written['forced_trades_allowed']}"
    )
    print(
        "paper_operational_mode_event_log_events="
        f"{replay['total_events']}"
    )
    print(f"paper_operational_mode_validation_errors={validation_errors}")

    if validation_errors:
        errors.append(f"PT-2 validation failed: {validation_errors}")
    if replay["total_events"] != 1:
        errors.append("PT-2 event log did not record exactly one event")
    if written["status"] != "enabled_pending_downstream_gates":
        errors.append("PT-2 did not enable global paper operational mode")
    if written["paper_operational_mode_effective"] is not True:
        errors.append("PT-2 paper operational mode is not effective")
    if written["paper_operational_flag_disabled"] is not False:
        errors.append("PT-2 paper operational flag remains disabled at runtime")
    if written["env_file_edited"] is not False:
        errors.append("PT-2 edited the environment file")
    if written["paper_order_submission_allowed"] is not False:
        errors.append("PT-2 opened paper order submission")
    if written["broker_post_called_count"] or written["alpaca_post_called_count"]:
        errors.append("PT-2 recorded broker/Alpaca POST calls")
    if written["live_capital_enabled"] is not False:
        errors.append("PT-2 enabled live capital")
    if written["qctrl_direct_execution_allowed"] is not False:
        errors.append("PT-2 gave Q-CTRL execution authority")
    if written["phase7_proof_credit_allowed"] is not False:
        errors.append("PT-2 granted Phase 7 proof credit")
    if "paper_operational_mode_forbidden:live_capital_enabled" not in live_capital_errors:
        errors.append("live-capital probe was not rejected")
    if "paper_operational_mode_forbidden:env_file_edited" not in env_errors:
        errors.append("env-file probe was not rejected")
    if (
        "paper_operational_mode_forbidden:paper_order_submission_allowed"
        not in submission_errors
    ):
        errors.append("paper-order-submission probe was not rejected")
    if "paper_operational_mode_forbidden:broker_post_allowed" not in broker_errors:
        errors.append("broker authority probe was not rejected")
    if (
        "paper_operational_mode_unsafe_counter_nonzero:broker_post_called_count"
        not in broker_errors
    ):
        errors.append("broker counter probe was not rejected")
    if (
        "paper_operational_mode_forbidden:qctrl_direct_execution_allowed"
        not in qctrl_errors
    ):
        errors.append("Q-CTRL execution probe was not rejected")
    if (
        "paper_operational_mode_forbidden:phase7_proof_credit_allowed"
        not in proof_errors
    ):
        errors.append("Phase 7 proof-credit probe was not rejected")
    if "paper_operational_mode_forbidden:forced_trades_allowed" not in forced_trade_errors:
        errors.append("forced-trade probe was not rejected")
    if "paper_operational_mode_forbidden:secret_value_exposed" not in secret_errors:
        errors.append("secret-exposure probe was not rejected")
    if "paper_operational_mode_event_log_missing" not in event_errors:
        errors.append("missing-event probe was not rejected")

    if errors:
        print("paper_operational_mode_check=failed")
        for error in errors:
            print(f"error={error}")
        return 1
    print("paper_operational_mode_check=ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
