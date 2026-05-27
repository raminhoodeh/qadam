#!/usr/bin/env python3
"""Validate PT-1 Q-CTRL product access and paper consultation state."""

from __future__ import annotations

import argparse
from copy import deepcopy
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from orchestrator.config import Settings  # noqa: E402
from orchestrator.event_log import EventLog  # noqa: E402
from orchestrator.paper_live_qctrl_product_access import (  # noqa: E402
    PAPER_LIVE_QCTRL_PRODUCT_ACCESS_SCHEMA_VERSION,
    build_paper_live_qctrl_product_access,
    validate_paper_live_qctrl_product_access,
    write_paper_live_qctrl_product_access,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--attempt-provider-consultation",
        action="store_true",
        help=(
            "Attempt exactly one guarded Q-CTRL paper provider auth/consultation "
            "probe through PaperOps-Q. This does not call brokers or live capital."
        ),
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    errors: list[str] = []
    settings = Settings.from_env()
    artifact = build_paper_live_qctrl_product_access(
        settings,
        attempt_provider_consultation=args.attempt_provider_consultation,
    )
    output_path, history_path, event_path, written = write_paper_live_qctrl_product_access(
        artifact,
        settings=settings,
    )
    validation_errors = validate_paper_live_qctrl_product_access(written)
    replay = EventLog(event_path, echo=False).replay()

    authority_probe = deepcopy(written)
    authority_probe["execution_allowed"] = True
    authority_probe["paper_order_allowed"] = True
    authority_probe["broker_post_allowed"] = True
    authority_errors = validate_paper_live_qctrl_product_access(authority_probe)

    proof_probe = deepcopy(written)
    proof_probe["phase7_proof_credit_allowed"] = True
    proof_errors = validate_paper_live_qctrl_product_access(proof_probe)

    secret_probe = deepcopy(written)
    secret_probe["secret_value_exposed"] = True
    secret_errors = validate_paper_live_qctrl_product_access(secret_probe)

    counter_probe = deepcopy(written)
    counter_probe["broker_post_called_count"] = 1
    counter_errors = validate_paper_live_qctrl_product_access(counter_probe)

    attempt_without_flag_probe = deepcopy(written)
    attempt_without_flag_probe["provider_call_attempted"] = True
    attempt_without_flag_probe["provider_call_count"] = 1
    attempt_without_flag_probe["qctrl_paper_consultation_enabled_for_probe"] = False
    attempt_without_flag_errors = validate_paper_live_qctrl_product_access(
        attempt_without_flag_probe
    )

    success_without_count_probe = deepcopy(written)
    success_without_count_probe["provider_call_succeeded"] = True
    success_without_count_probe["product_access_verified"] = True
    success_without_count_probe["paper_consultation_ready"] = True
    success_without_count_probe["provider_call_count"] = 0
    success_without_count_errors = validate_paper_live_qctrl_product_access(
        success_without_count_probe
    )

    event_probe = deepcopy(written)
    event_probe["event_log_written"] = False
    event_probe["event_log_event_count"] = 0
    event_errors = validate_paper_live_qctrl_product_access(event_probe)

    print(f"paper_live_qctrl_product_access_status={written['status']}")
    print(
        "paper_live_qctrl_product_access_schema_version="
        f"{PAPER_LIVE_QCTRL_PRODUCT_ACCESS_SCHEMA_VERSION}"
    )
    print(f"paper_live_qctrl_product_access_artifact_path={output_path}")
    print(f"paper_live_qctrl_product_access_history_path={history_path}")
    print(f"paper_live_qctrl_product_access_event_log_path={event_path}")
    print(
        "paper_live_qctrl_product_access_attempt_provider_consultation="
        f"{args.attempt_provider_consultation}"
    )
    print(
        "paper_live_qctrl_product_access_pt0_approved="
        f"{written['pt0_activation_approved']}"
    )
    print(
        "paper_live_qctrl_product_access_pt0_system_logged="
        f"{written['pt0_system_approval_logged']}"
    )
    print(
        "paper_live_qctrl_product_access_product_access_state="
        f"{written['product_access_state']}"
    )
    print(
        "paper_live_qctrl_product_access_verified="
        f"{written['product_access_verified']}"
    )
    print(
        "paper_live_qctrl_product_access_paper_consultation_ready="
        f"{written['paper_consultation_ready']}"
    )
    print(
        "paper_live_qctrl_product_access_paper_consultation_recorded="
        f"{written['paper_consultation_recorded']}"
    )
    print(
        "paper_live_qctrl_product_access_probe_flag="
        f"{written['qctrl_paper_consultation_enabled_for_probe']}"
    )
    print(
        "paper_live_qctrl_product_access_readiness_status="
        f"{written['qctrl_readiness_status']}"
    )
    print(
        "paper_live_qctrl_product_access_credential_configured="
        f"{written['qctrl_credential_configured']}"
    )
    print(
        "paper_live_qctrl_product_access_fire_opal_product_required="
        f"{written['qctrl_fire_opal_product_required']}"
    )
    print(
        "paper_live_qctrl_product_access_organization_slug_configured="
        f"{written['qctrl_organization_slug_configured']}"
    )
    print(
        "paper_live_qctrl_product_access_organization_config_applied="
        f"{written['qctrl_organization_config_applied']}"
    )
    print(
        "paper_live_qctrl_product_access_sdk_importable="
        f"{written['qctrl_sdk_package_importable']}"
    )
    print(
        "paper_live_qctrl_product_access_sdk_module_selected="
        f"{written['qctrl_sdk_module_selected']}"
    )
    print(
        "paper_live_qctrl_product_access_provider_call_allowed="
        f"{written['provider_call_allowed']}"
    )
    print(
        "paper_live_qctrl_product_access_provider_call_attempted="
        f"{written['provider_call_attempted']}"
    )
    print(
        "paper_live_qctrl_product_access_provider_call_succeeded="
        f"{written['provider_call_succeeded']}"
    )
    print(
        "paper_live_qctrl_product_access_provider_call_count="
        f"{written['provider_call_count']}"
    )
    print(
        "paper_live_qctrl_product_access_auth_status="
        f"{written['qctrl_auth_status']}"
    )
    print(
        "paper_live_qctrl_product_access_provider_failure_category="
        f"{written['provider_failure_category']}"
    )
    print(
        "paper_live_qctrl_product_access_blocker="
        f"{written['product_access_blocker']}"
    )
    print(
        "paper_live_qctrl_product_access_paperops_qctrl_status="
        f"{written['paperops_qctrl_status']}"
    )
    print(
        "paper_live_qctrl_product_access_head_note_status="
        f"{written['head_of_quant_note_status']}"
    )
    print(
        "paper_live_qctrl_product_access_execution_allowed="
        f"{written['execution_allowed']}"
    )
    print(
        "paper_live_qctrl_product_access_paper_order_allowed="
        f"{written['paper_order_allowed']}"
    )
    print(
        "paper_live_qctrl_product_access_broker_post_allowed="
        f"{written['broker_post_allowed']}"
    )
    print(
        "paper_live_qctrl_product_access_live_capital_enabled="
        f"{written['live_capital_enabled']}"
    )
    print(
        "paper_live_qctrl_product_access_phase7_proof_credit_allowed="
        f"{written['phase7_proof_credit_allowed']}"
    )
    print(
        "paper_live_qctrl_product_access_secret_value_exposed="
        f"{written['secret_value_exposed']}"
    )
    print(
        "paper_live_qctrl_product_access_raw_response_exposed="
        f"{written['raw_response_exposed']}"
    )
    print(
        "paper_live_qctrl_product_access_event_log_events="
        f"{replay['total_events']}"
    )
    print(
        "paper_live_qctrl_product_access_validation_errors="
        f"{validation_errors}"
    )

    if validation_errors:
        errors.append(f"PT-1 validation failed: {validation_errors}")
    if replay["total_events"] < 1 or written["event_log_event_count"] != 1:
        errors.append("PT-1 event log did not record the current event")
    if args.attempt_provider_consultation and written["provider_call_attempted"] is not True:
        errors.append("PT-1 did not attempt the requested provider consultation")
    if args.attempt_provider_consultation and written["provider_call_count"] < 1:
        errors.append("PT-1 did not record the requested provider-call attempt")
    if written["pt0_activation_approved"] is not True:
        errors.append("PT-1 is missing PT-0 approval")
    if written["pt0_system_approval_logged"] is not True:
        errors.append("PT-1 is missing PT-0 system approval log")
    if written["qctrl_credential_configured"] is not True:
        errors.append("PT-1 does not see configured Q-CTRL credential")
    if written["qctrl_fire_opal_product_required"] is not True:
        errors.append("PT-1 does not require Fire Opal for mandatory quantum parity")
    if (
        written["qctrl_sdk_package_importable"] is not True
        and written["status"] != "blocked_missing_qctrl_sdk"
    ):
        errors.append("PT-1 does not see importable Q-CTRL SDK")
    for key in (
        "execution_allowed",
        "paper_order_allowed",
        "broker_post_allowed",
        "alpaca_post_allowed",
        "live_endpoint_allowed",
        "live_capital_enabled",
        "phase7_proof_credit_allowed",
        "forced_trades_allowed",
        "secret_value_exposed",
        "raw_response_exposed",
        "raw_provider_response_persisted",
    ):
        if written[key] is not False:
            errors.append(f"PT-1 unsafe flag is enabled: {key}")
    if written["broker_post_called_count"] or written["alpaca_post_called_count"]:
        errors.append("PT-1 recorded broker/Alpaca POST calls")
    if "paper_live_qctrl_product_access_forbidden:execution_allowed" not in authority_errors:
        errors.append("PT-1 execution-authority probe was not rejected")
    if (
        "paper_live_qctrl_product_access_forbidden:phase7_proof_credit_allowed"
        not in proof_errors
    ):
        errors.append("PT-1 proof-credit probe was not rejected")
    if "paper_live_qctrl_product_access_forbidden:secret_value_exposed" not in secret_errors:
        errors.append("PT-1 secret-exposure probe was not rejected")
    if (
        "paper_live_qctrl_product_access_unsafe_counter_nonzero:"
        "broker_post_called_count"
        not in counter_errors
    ):
        errors.append("PT-1 broker-counter probe was not rejected")
    if (
        "paper_live_qctrl_product_access_attempt_without_probe_flag"
        not in attempt_without_flag_errors
    ):
        errors.append("PT-1 provider-attempt-without-flag probe was not rejected")
    if (
        "paper_live_qctrl_product_access_success_without_call_count"
        not in success_without_count_errors
    ):
        errors.append("PT-1 success-without-call-count probe was not rejected")
    if "paper_live_qctrl_product_access_event_log_missing" not in event_errors:
        errors.append("PT-1 missing-event probe was not rejected")

    if errors:
        print("paper_live_qctrl_product_access_check=failed")
        for error in errors:
            print(f"error={error}")
        return 1
    print("paper_live_qctrl_product_access_check=ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
