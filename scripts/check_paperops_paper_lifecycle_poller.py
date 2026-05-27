#!/usr/bin/env python3
"""Validate the PaperOps-3 read-only paper lifecycle poller."""

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
from orchestrator.paperops_paper_lifecycle_poller import (  # noqa: E402
    PAPEROPS_LIFECYCLE_POLLER_SCHEMA_VERSION,
    build_paperops_paper_lifecycle_poller,
    paperops_paper_lifecycle_poller_paths,
    read_latest_paperops_paper_lifecycle_poller,
    validate_paperops_paper_lifecycle_poller,
    write_paperops_paper_lifecycle_poller,
)


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--poll-paper-orders",
        action="store_true",
        help=(
            "GET read-only Alpaca paper order/position state for PaperOps-2 submitted "
            "paper orders. The current default check never polls."
        ),
    )
    return parser.parse_args()


def main() -> int:
    args = _parse_args()
    errors: list[str] = []
    settings = Settings.from_env()
    output_path, history_path, event_path = paperops_paper_lifecycle_poller_paths(settings)
    existing = read_latest_paperops_paper_lifecycle_poller(settings)
    preserve_lifecycle_poll = (
        args.poll_paper_orders is False
        and existing.get("status") == "paper_lifecycle_poll_recorded"
        and "phase7_proof_credit_allowed" in existing
    )
    if event_path.exists():
        event_path.unlink()

    artifact = (
        existing
        if preserve_lifecycle_poll
        else build_paperops_paper_lifecycle_poller(
            settings=settings,
            poll_paper_orders=args.poll_paper_orders,
        )
    )
    output_path, history_path, event_path, written = write_paperops_paper_lifecycle_poller(
        artifact,
        settings=settings,
        record_event=True,
        event_log_path=event_path,
    )
    validation_errors = validate_paperops_paper_lifecycle_poller(written)
    replay = EventLog(event_path, echo=False).replay()

    live_mode_probe = deepcopy(written)
    live_mode_probe["mode"] = "live"
    live_mode_errors = validate_paperops_paper_lifecycle_poller(live_mode_probe)

    live_capital_probe = deepcopy(written)
    live_capital_probe["live_capital_enabled"] = True
    live_capital_probe["live_capital_enabled_count"] = 1
    live_capital_errors = validate_paperops_paper_lifecycle_poller(live_capital_probe)

    no_flag_probe = deepcopy(written)
    no_flag_probe["poll_paper_orders_requested"] = False
    no_flag_probe["paper_order_poll_called_count"] = 1
    no_flag_errors = validate_paperops_paper_lifecycle_poller(no_flag_probe)

    no_source_probe = deepcopy(written)
    no_source_probe["source_submitted_paper_order_count"] = 0
    no_source_probe["paper_order_poll_called_count"] = 1
    no_source_errors = validate_paperops_paper_lifecycle_poller(no_source_probe)

    no_pt6_probe = deepcopy(written)
    no_pt6_probe["source_submitted_paper_order_count"] = 1
    no_pt6_probe["poll_candidate_records"] = [
        {
            "eligible_for_lifecycle_poll": True,
            "idempotency_namespace": "phase7_demo_proof",
            "client_order_id": "q7-6-stage-test",
            "broker_order_id_hash": "hash",
            "base_url_exposed": False,
            "authorization_header_included": False,
            "authorization_header_exposed": False,
            "raw_broker_payload_stored": False,
            "raw_broker_payload_exposed": False,
            "broker_order_identifier_exposed": False,
            "secret_value_exposed": False,
            "live_endpoint_allowed": False,
            "live_capital_enabled": False,
        }
    ]
    no_pt6_probe["poll_candidate_count"] = 1
    no_pt6_probe["active_lifecycle_polling_enabled"] = False
    no_pt6_probe["status"] = "ready_pending_explicit_poll"
    no_pt6_errors = validate_paperops_paper_lifecycle_poller(no_pt6_probe)

    live_endpoint_probe = deepcopy(written)
    live_endpoint_probe["endpoint_classification"] = "alpaca_live_endpoint"
    live_endpoint_probe["paper_endpoint_confirmed"] = False
    live_endpoint_probe["paper_order_poll_called_count"] = 1
    live_endpoint_errors = validate_paperops_paper_lifecycle_poller(live_endpoint_probe)

    broker_post_probe = deepcopy(written)
    broker_post_probe["broker_post_called_count"] = 1
    broker_post_probe["alpaca_post_called_count"] = 1
    broker_post_errors = validate_paperops_paper_lifecycle_poller(broker_post_probe)

    order_mutation_probe = deepcopy(written)
    order_mutation_probe["order_cancel_called_count"] = 1
    order_mutation_probe["position_close_called_count"] = 1
    order_mutation_errors = validate_paperops_paper_lifecycle_poller(order_mutation_probe)

    raw_payload_probe = deepcopy(written)
    raw_payload_probe["raw_broker_payload_exposed"] = True
    raw_payload_probe["raw_broker_payload_exposed_count"] = 1
    raw_payload_errors = validate_paperops_paper_lifecycle_poller(raw_payload_probe)

    broker_id_probe = deepcopy(written)
    broker_id_probe["broker_order_identifier_exposed"] = True
    broker_id_probe["broker_order_identifier_exposed_count"] = 1
    broker_id_errors = validate_paperops_paper_lifecycle_poller(broker_id_probe)

    secret_probe = deepcopy(written)
    secret_probe["failure_class"] = "ALPACA_API_SECRET=thisShouldNeverAppear123"
    secret_errors = validate_paperops_paper_lifecycle_poller(secret_probe)

    proof_credit_probe = deepcopy(written)
    proof_credit_probe["phase7_proof_credit_allowed"] = True
    proof_credit_probe["phase7_proof_credit_allowed_count"] = 1
    proof_credit_errors = validate_paperops_paper_lifecycle_poller(proof_credit_probe)

    print(f"paperops_lifecycle_poller_status={written['status']}")
    print(f"paperops_lifecycle_poller_schema_version={PAPEROPS_LIFECYCLE_POLLER_SCHEMA_VERSION}")
    print(f"paperops_lifecycle_poller_artifact_path={output_path}")
    print(f"paperops_lifecycle_poller_history_path={history_path}")
    print(f"paperops_lifecycle_poller_event_log_path={event_path}")
    print(f"paperops_lifecycle_poller_mode={written['mode']}")
    print(f"paperops_lifecycle_poller_poll_requested={written['poll_paper_orders_requested']}")
    print(
        "paperops_lifecycle_poller_active_polling_enabled="
        f"{written['active_lifecycle_polling_enabled']}"
    )
    print(
        "paperops_lifecycle_poller_enablement_status="
        f"{written['lifecycle_polling_enablement_status']}"
    )
    print(f"paperops_lifecycle_poller_path_available={written['paper_poll_path_available']}")
    print(f"paperops_lifecycle_poller_endpoint_classification={written['endpoint_classification']}")
    print(f"paperops_lifecycle_poller_paper_endpoint_confirmed={written['paper_endpoint_confirmed']}")
    print(f"paperops_lifecycle_poller_key_configured={written['alpaca_api_key_configured']}")
    print(f"paperops_lifecycle_poller_secret_configured={written['alpaca_api_secret_configured']}")
    print(f"paperops_lifecycle_poller_source_status={written['source_paperops_2_status']}")
    print(
        "paperops_lifecycle_poller_source_validation_error_count="
        f"{written['source_paperops_2_validation_error_count']}"
    )
    print(
        "paperops_lifecycle_poller_source_submitted_order_count="
        f"{written['source_submitted_paper_order_count']}"
    )
    print(f"paperops_lifecycle_poller_poll_candidate_count={written['poll_candidate_count']}")
    print(
        "paperops_lifecycle_poller_order_poll_called_count="
        f"{written['paper_order_poll_called_count']}"
    )
    print(
        "paperops_lifecycle_poller_order_poll_succeeded_count="
        f"{written['paper_order_poll_succeeded_count']}"
    )
    print(
        "paperops_lifecycle_poller_position_poll_called_count="
        f"{written['paper_position_poll_called_count']}"
    )
    print(f"paperops_lifecycle_poller_broker_get_called_count={written['broker_get_called_count']}")
    print(f"paperops_lifecycle_poller_broker_post_called_count={written['broker_post_called_count']}")
    print(f"paperops_lifecycle_poller_live_endpoint_called_count={written['live_endpoint_called_count']}")
    print(f"paperops_lifecycle_poller_live_capital_enabled={written['live_capital_enabled']}")
    print(f"paperops_lifecycle_poller_open_position_count={written['open_position_count']}")
    print(f"paperops_lifecycle_poller_closed_trade_count={written['closed_trade_count']}")
    print(
        "paperops_lifecycle_poller_postmortem_due_marker_created_count="
        f"{written['postmortem_due_marker_created_count']}"
    )
    print(
        "paperops_lifecycle_poller_q7_lifecycle_mutation_performed="
        f"{written['q7_lifecycle_mutation_performed']}"
    )
    print(f"paperops_lifecycle_poller_secret_value_exposed={written['secret_value_exposed']}")
    print(
        "paperops_lifecycle_poller_raw_broker_payload_exposed="
        f"{written['raw_broker_payload_exposed']}"
    )
    print(
        "paperops_lifecycle_poller_broker_order_identifier_exposed="
        f"{written['broker_order_identifier_exposed']}"
    )
    print(f"paperops_lifecycle_poller_event_log_events={replay['total_events']}")
    print(
        "paperops_lifecycle_poller_preserved_lifecycle_poll="
        f"{preserve_lifecycle_poll}"
    )
    print(f"paperops_lifecycle_poller_validation_errors={validation_errors}")

    if validation_errors:
        errors.append(f"PaperOps-3 validation failed: {validation_errors}")
    if replay["total_events"] < 1:
        errors.append("PaperOps-3 event log did not record the current event")
    if written["mode"] != "paper":
        errors.append("PaperOps-3 current mode is not paper")
    if written["live_capital_enabled"] is not False:
        errors.append("PaperOps-3 enables live capital")
    if (
        not args.poll_paper_orders
        and not preserve_lifecycle_poll
        and written["paper_order_poll_called_count"] != 0
    ):
        errors.append("PaperOps-3 polled without --poll-paper-orders")
    if written["source_submitted_paper_order_count"] == 0:
        if written["status"] != "ready_no_submitted_paper_orders":
            errors.append("PaperOps-3 should be ready but idle with no submitted source orders")
        if written["paper_order_poll_called_count"] != 0:
            errors.append("PaperOps-3 called Alpaca with no submitted PaperOps-2 orders")
    for key in (
        "broker_post_called_count",
        "alpaca_post_called_count",
        "order_cancel_called_count",
        "position_close_called_count",
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
    ):
        if written[key] != 0:
            errors.append(f"PaperOps-3 unsafe counter nonzero: {key}")
    if written["q7_lifecycle_mutation_performed"] is not False:
        errors.append("PaperOps-3 directly mutated Q7 lifecycle")
    if "paperops_lifecycle_mode_not_paper" not in live_mode_errors:
        errors.append("live-mode probe was not rejected")
    if "paperops_lifecycle_forbidden:live_capital_enabled" not in live_capital_errors:
        errors.append("live-capital probe was not rejected")
    if "paperops_lifecycle_poll_called_without_explicit_flag" not in no_flag_errors:
        errors.append("poll-without-explicit-flag probe was not rejected")
    if "paperops_lifecycle_poll_called_without_submitted_source_order" not in no_source_errors:
        errors.append("poll-without-source-order probe was not rejected")
    if (
        "paperops_lifecycle_submitted_source_without_pt6_enablement"
        not in no_pt6_errors
    ):
        errors.append("submitted-source-without-PT-6 probe was not rejected")
    if "paperops_lifecycle_poll_called_without_paper_endpoint" not in live_endpoint_errors:
        errors.append("live-endpoint poll probe was not rejected")
    if "paperops_lifecycle_unsafe_counter_nonzero:broker_post_called_count" not in broker_post_errors:
        errors.append("broker POST probe was not rejected")
    if (
        "paperops_lifecycle_unsafe_counter_nonzero:order_cancel_called_count"
        not in order_mutation_errors
    ):
        errors.append("order mutation probe was not rejected")
    if "paperops_lifecycle_forbidden:raw_broker_payload_exposed" not in raw_payload_errors:
        errors.append("raw-broker-payload probe was not rejected")
    if (
        "paperops_lifecycle_forbidden:broker_order_identifier_exposed"
        not in broker_id_errors
    ):
        errors.append("broker-identifier probe was not rejected")
    if "paperops_lifecycle_secret_shape_exposed" not in secret_errors:
        errors.append("secret-shape probe was not rejected")
    if "paperops_lifecycle_forbidden:phase7_proof_credit_allowed" not in proof_credit_errors:
        errors.append("proof-credit probe was not rejected")

    if errors:
        print("paperops_paper_lifecycle_poller_check=failed")
        for error in errors:
            print(f"error={error}")
        return 1
    print("paperops_paper_lifecycle_poller_check=ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
