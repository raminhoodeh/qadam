#!/usr/bin/env python3
"""Validate the PaperOps-4 guarded Alpaca paper exit path."""

from __future__ import annotations

import argparse
from copy import deepcopy
from dataclasses import replace
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from orchestrator.config import Settings  # noqa: E402
from orchestrator.event_log import EventLog  # noqa: E402
from orchestrator.paperops_paper_exit_path import (  # noqa: E402
    PAPEROPS_EXIT_PATH_SCHEMA_VERSION,
    build_paperops_paper_exit_path,
    paperops_paper_exit_path_paths,
    validate_paperops_paper_exit_path,
    write_paperops_paper_exit_path,
)


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--execute-paper-exit",
        action="store_true",
        help=(
            "Actually DELETE the first eligible PaperOps-3 open position on Alpaca paper. "
            "All PaperOps-4 gates must pass first."
        ),
    )
    return parser.parse_args()


def main() -> int:
    args = _parse_args()
    errors: list[str] = []
    settings = Settings.from_env()
    output_path, history_path, event_path = paperops_paper_exit_path_paths(settings)
    if event_path.exists():
        event_path.unlink()

    artifact = build_paperops_paper_exit_path(
        settings=settings,
        execute_exit=args.execute_paper_exit,
        event_log_path=event_path,
    )
    output_path, history_path, event_path, written = write_paperops_paper_exit_path(
        artifact,
        settings=settings,
        record_event=True,
        event_log_path=event_path,
    )
    validation_errors = validate_paperops_paper_exit_path(written)
    replay = EventLog(event_path, echo=False).replay()

    live_mode_probe = deepcopy(written)
    live_mode_probe["mode"] = "live"
    live_mode_errors = validate_paperops_paper_exit_path(live_mode_probe)

    live_capital_probe = deepcopy(written)
    live_capital_probe["live_capital_enabled"] = True
    live_capital_probe["live_capital_enabled_count"] = 1
    live_capital_errors = validate_paperops_paper_exit_path(live_capital_probe)

    no_flag_probe = deepcopy(written)
    no_flag_probe["alpaca_paper_exit_enabled"] = False
    no_flag_probe["paper_position_close_called_count"] = 1
    no_flag_errors = validate_paperops_paper_exit_path(no_flag_probe)

    no_execute_probe = deepcopy(written)
    no_execute_probe["execute_exit_requested"] = False
    no_execute_probe["paper_position_close_called_count"] = 1
    no_execute_errors = validate_paperops_paper_exit_path(no_execute_probe)

    no_candidate_probe = deepcopy(written)
    no_candidate_probe["eligible_exit_record_count"] = 0
    no_candidate_probe["paper_position_close_called_count"] = 1
    no_candidate_errors = validate_paperops_paper_exit_path(no_candidate_probe)

    live_endpoint_probe = deepcopy(written)
    live_endpoint_probe["endpoint_classification"] = "alpaca_live_endpoint"
    live_endpoint_probe["paper_endpoint_confirmed"] = False
    live_endpoint_probe["paper_position_close_called_count"] = 1
    live_endpoint_errors = validate_paperops_paper_exit_path(live_endpoint_probe)

    missing_prewrite_probe = deepcopy(written)
    missing_prewrite_probe["paper_position_close_called_count"] = 1
    missing_prewrite_probe["execute_exit_requested"] = True
    missing_prewrite_probe["alpaca_paper_exit_enabled"] = True
    missing_prewrite_probe["paper_endpoint_confirmed"] = True
    missing_prewrite_probe["paperops_exit_event_log_prewrite_written"] = False
    missing_prewrite_errors = validate_paperops_paper_exit_path(missing_prewrite_probe)

    broker_post_probe = deepcopy(written)
    broker_post_probe["broker_post_called_count"] = 1
    broker_post_probe["alpaca_post_called_count"] = 1
    broker_post_errors = validate_paperops_paper_exit_path(broker_post_probe)

    order_mutation_probe = deepcopy(written)
    order_mutation_probe["order_cancel_called_count"] = 1
    order_mutation_probe["position_resize_called_count"] = 1
    order_mutation_errors = validate_paperops_paper_exit_path(order_mutation_probe)

    raw_payload_probe = deepcopy(written)
    raw_payload_probe["raw_broker_payload_exposed"] = True
    raw_payload_probe["raw_broker_payload_exposed_count"] = 1
    raw_payload_errors = validate_paperops_paper_exit_path(raw_payload_probe)

    broker_id_probe = deepcopy(written)
    broker_id_probe["broker_order_identifier_exposed"] = True
    broker_id_probe["broker_order_identifier_exposed_count"] = 1
    broker_id_errors = validate_paperops_paper_exit_path(broker_id_probe)

    secret_probe = deepcopy(written)
    secret_probe["broker_failure_class"] = "ALPACA_API_SECRET=thisShouldNeverAppear123"
    secret_errors = validate_paperops_paper_exit_path(secret_probe)

    proof_credit_probe = deepcopy(written)
    proof_credit_probe["phase7_proof_credit_allowed"] = True
    proof_credit_probe["phase7_proof_credit_allowed_count"] = 1
    proof_credit_errors = validate_paperops_paper_exit_path(proof_credit_probe)

    enabled_preview_settings = replace(settings, alpaca_paper_exit_enabled=True)
    enabled_preview = build_paperops_paper_exit_path(
        settings=enabled_preview_settings,
        execute_exit=False,
    )

    print(f"paperops_exit_status={written['status']}")
    print(f"paperops_exit_schema_version={PAPEROPS_EXIT_PATH_SCHEMA_VERSION}")
    print(f"paperops_exit_artifact_path={output_path}")
    print(f"paperops_exit_history_path={history_path}")
    print(f"paperops_exit_event_log_path={event_path}")
    print(f"paperops_exit_mode={written['mode']}")
    print(f"paperops_exit_enabled={written['alpaca_paper_exit_enabled']}")
    print(f"paperops_exit_execute_requested={written['execute_exit_requested']}")
    print(f"paperops_exit_path_available={written['paper_exit_path_available']}")
    print(f"paperops_exit_endpoint_classification={written['endpoint_classification']}")
    print(f"paperops_exit_paper_endpoint_confirmed={written['paper_endpoint_confirmed']}")
    print(f"paperops_exit_key_configured={written['alpaca_api_key_configured']}")
    print(f"paperops_exit_secret_configured={written['alpaca_api_secret_configured']}")
    print(f"paperops_exit_source_status={written['source_paperops_3_status']}")
    print(
        "paperops_exit_source_validation_error_count="
        f"{written['source_paperops_3_validation_error_count']}"
    )
    print(f"paperops_exit_open_position_readback_count={written['open_position_readback_count']}")
    print(f"paperops_exit_eligible_record_count={written['eligible_exit_record_count']}")
    print(
        "paperops_exit_prewrite_written="
        f"{written['paperops_exit_event_log_prewrite_written']}"
    )
    print(f"paperops_exit_close_called_count={written['paper_position_close_called_count']}")
    print(
        "paperops_exit_close_succeeded_count="
        f"{written['paper_position_close_succeeded_count']}"
    )
    print(f"paperops_exit_broker_write_called_count={written['broker_write_called_count']}")
    print(f"paperops_exit_broker_post_called_count={written['broker_post_called_count']}")
    print(f"paperops_exit_order_cancel_called_count={written['order_cancel_called_count']}")
    print(f"paperops_exit_position_resize_called_count={written['position_resize_called_count']}")
    print(f"paperops_exit_live_endpoint_called_count={written['live_endpoint_called_count']}")
    print(f"paperops_exit_live_capital_enabled={written['live_capital_enabled']}")
    print(
        "paperops_exit_q7_lifecycle_mutation_performed="
        f"{written['q7_lifecycle_mutation_performed']}"
    )
    print(f"paperops_exit_secret_value_exposed={written['secret_value_exposed']}")
    print(f"paperops_exit_raw_broker_payload_exposed={written['raw_broker_payload_exposed']}")
    print(
        "paperops_exit_broker_order_identifier_exposed="
        f"{written['broker_order_identifier_exposed']}"
    )
    print(f"paperops_exit_event_log_events={replay['total_events']}")
    print(f"paperops_exit_enabled_preview_status={enabled_preview['status']}")
    print(
        "paperops_exit_enabled_preview_execute_requested="
        f"{enabled_preview['execute_exit_requested']}"
    )
    print(
        "paperops_exit_enabled_preview_close_called_count="
        f"{enabled_preview['paper_position_close_called_count']}"
    )
    print(f"paperops_exit_validation_errors={validation_errors}")

    if validation_errors:
        errors.append(f"PaperOps-4 validation failed: {validation_errors}")
    expected_event_count = 2 if written["paperops_exit_event_log_prewrite_written"] else 1
    if replay["total_events"] != expected_event_count:
        errors.append("PaperOps-4 event log did not record the expected event count")
    if written["mode"] != "paper":
        errors.append("PaperOps-4 current mode is not paper")
    if written["live_capital_enabled"] is not False:
        errors.append("PaperOps-4 enables live capital")
    if not args.execute_paper_exit and written["paper_position_close_called_count"] != 0:
        errors.append("PaperOps-4 closed a position without --execute-paper-exit")
    if written["alpaca_paper_exit_enabled"] is False:
        if written["status"] != "disabled_pending_enablement":
            errors.append("PaperOps-4 should stay disabled pending explicit enablement")
        if written["paper_position_close_called_count"] != 0:
            errors.append("PaperOps-4 called Alpaca while disabled")
    if enabled_preview["execute_exit_requested"] is not False:
        errors.append("PaperOps-4 enabled preview should not request execution")
    if enabled_preview["paper_position_close_called_count"] != 0:
        errors.append("PaperOps-4 enabled preview called Alpaca")
    for key in (
        "broker_post_called_count",
        "alpaca_post_called_count",
        "order_cancel_called_count",
        "position_resize_called_count",
        "live_endpoint_called_count",
        "live_capital_enabled_count",
        "manual_trade_level_override_count",
        "prediction_market_write_allowed_count",
        "crypto_perps_write_allowed_count",
        "phase7_proof_credit_allowed_count",
        "secret_value_exposed_count",
        "raw_broker_payload_exposed_count",
        "raw_broker_payload_stored_count",
        "authorization_header_exposed_count",
        "base_url_exposed_count",
        "broker_order_identifier_exposed_count",
        "postmortem_due_marker_created_count",
    ):
        if written[key] != 0:
            errors.append(f"PaperOps-4 unsafe counter nonzero: {key}")
    if written["q7_lifecycle_mutation_performed"] is not False:
        errors.append("PaperOps-4 directly mutated Q7 lifecycle")
    if "paperops_exit_mode_not_paper" not in live_mode_errors:
        errors.append("live-mode probe was not rejected")
    if "paperops_exit_forbidden:live_capital_enabled" not in live_capital_errors:
        errors.append("live-capital probe was not rejected")
    if "paperops_exit_called_without_flag" not in no_flag_errors:
        errors.append("close-without-flag probe was not rejected")
    if "paperops_exit_called_without_explicit_execute" not in no_execute_errors:
        errors.append("close-without-explicit-execute probe was not rejected")
    if "paperops_exit_close_called_without_candidate" not in no_candidate_errors:
        errors.append("close-without-candidate probe was not rejected")
    if "paperops_exit_close_called_without_paper_endpoint" not in live_endpoint_errors:
        errors.append("live-endpoint close probe was not rejected")
    if "paperops_exit_close_called_without_prewrite" not in missing_prewrite_errors:
        errors.append("missing-prewrite probe was not rejected")
    if "paperops_exit_unsafe_counter_nonzero:broker_post_called_count" not in broker_post_errors:
        errors.append("broker POST probe was not rejected")
    if (
        "paperops_exit_unsafe_counter_nonzero:order_cancel_called_count"
        not in order_mutation_errors
    ):
        errors.append("order-cancel probe was not rejected")
    if "paperops_exit_forbidden:raw_broker_payload_exposed" not in raw_payload_errors:
        errors.append("raw-broker-payload probe was not rejected")
    if "paperops_exit_forbidden:broker_order_identifier_exposed" not in broker_id_errors:
        errors.append("broker-identifier probe was not rejected")
    if "paperops_exit_secret_shape_exposed" not in secret_errors:
        errors.append("secret-shape probe was not rejected")
    if "paperops_exit_forbidden:phase7_proof_credit_allowed" not in proof_credit_errors:
        errors.append("proof-credit probe was not rejected")

    if errors:
        print("paperops_paper_exit_path_check=failed")
        for error in errors:
            print(f"error={error}")
        return 1
    print("paperops_paper_exit_path_check=ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
