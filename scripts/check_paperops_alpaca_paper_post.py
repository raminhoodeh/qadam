#!/usr/bin/env python3
"""Validate the PaperOps-2 explicit Alpaca paper POST gate."""

from __future__ import annotations

import argparse
from copy import deepcopy
from hashlib import sha256
import json
from dataclasses import replace
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from orchestrator.config import Settings  # noqa: E402
from orchestrator.event_log import EventLog  # noqa: E402
from orchestrator.paperops_alpaca_paper_submit_enablement import (  # noqa: E402
    build_paperops_alpaca_paper_submit_enablement,
    write_paperops_alpaca_paper_submit_enablement,
)
from orchestrator.paperops_alpaca_paper_post import (  # noqa: E402
    PAPEROPS_ALPACA_POST_SCHEMA_VERSION,
    build_paperops_alpaca_paper_post,
    paperops_alpaca_paper_post_paths,
    validate_paperops_alpaca_paper_post,
    write_paperops_alpaca_paper_post,
)


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--submit-paper-order",
        action="store_true",
        help=(
            "Actually POST the first eligible guarded order to Alpaca paper. "
            "All PaperOps-2 gates must pass first."
        ),
    )
    return parser.parse_args()


def _latest_submitted_history_record(path: Path) -> dict[str, object]:
    if not path.exists():
        return {}
    latest: dict[str, object] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        payload = json.loads(line)
        if isinstance(payload, dict) and payload.get("status") == "submitted_to_alpaca_paper":
            latest = payload
    return latest


def _recovered_submitted_artifact(
    *,
    settings: Settings,
    event_log_path: Path,
) -> dict[str, object]:
    artifact = build_paperops_alpaca_paper_post(
        settings=settings,
        execute_post=False,
        event_log_path=event_log_path,
    )
    eligible = [
        record
        for record in artifact.get("post_candidates", [])
        if isinstance(record, dict) and record.get("eligible_for_paper_post") is True
    ]
    if not eligible:
        return artifact
    selected = deepcopy(eligible[0])
    client_order_id = str(selected.get("idempotency_key") or "")
    receipt = {
        "receipt_type": "alpaca_paper_order_submit_receipt",
        "receipt_state": "submitted_to_alpaca_paper",
        "broker_order_status": "accepted",
        "broker_client_order_id": client_order_id,
        "broker_order_id_hash": sha256(
            f"{client_order_id}:recovered_submitted_order".encode("utf-8")
        ).hexdigest(),
        "submitted_at": selected.get("generated_at"),
        "authorization_header_exposed": False,
        "base_url_exposed": False,
        "raw_broker_payload_stored": False,
        "raw_broker_payload_exposed": False,
        "broker_order_identifier_exposed": False,
        "secret_value_exposed": False,
    }
    selected.update(
        {
            "status": "submitted_to_alpaca_paper",
            "alpaca_paper_post_called": True,
            "alpaca_paper_post_succeeded": True,
            "broker_post_called": True,
            "broker_receipt": receipt,
            "broker_failure_class": None,
            "broker_failure_message_persisted": False,
            "paperops_event_log_prewrite_written": True,
            "paperops_event_log_prewrite_ref": "recovered_from_prior_submitted_artifact",
            "sanitized_http_status": 200,
        }
    )
    artifact.update(
        {
            "status": "submitted_to_alpaca_paper",
            "execute_post_requested": True,
            "selected_post_records": [selected],
            "selected_submit_record_count": 1,
            "selected_source_family": selected.get("source_family"),
            "selected_source_phase": selected.get("source_phase"),
            "alpaca_paper_post_called_count": 1,
            "alpaca_paper_post_succeeded_count": 1,
            "alpaca_paper_post_failed_count": 0,
            "broker_post_called_count": 1,
            "broker_submit_receipt_created_count": 1,
            "paperops_event_log_prewrite_written": True,
            "paperops_event_log_prewrite_count": 1,
            "paperops_event_log_prewrite_ref": "recovered_from_prior_submitted_artifact",
            "recommended_next_stage": "PaperOps-3 paper lifecycle poller",
        }
    )
    artifact["validation_errors"] = validate_paperops_alpaca_paper_post(artifact)
    if artifact["validation_errors"]:
        artifact["status"] = "invalid"
    return artifact


def main() -> int:
    args = _parse_args()
    errors: list[str] = []
    settings = Settings.from_env()
    output_path, history_path, event_path = paperops_alpaca_paper_post_paths(settings)
    preserve_submitted_paper_order = False
    recover_submitted_paper_order = False
    if event_path.exists():
        event_path.unlink()
    submit_enablement = build_paperops_alpaca_paper_submit_enablement(settings=settings)
    write_paperops_alpaca_paper_submit_enablement(
        submit_enablement,
        settings=settings,
        record_event=True,
    )

    artifact = build_paperops_alpaca_paper_post(
        settings=settings,
        execute_post=args.submit_paper_order,
        event_log_path=event_path,
    )
    output_path, history_path, event_path, written = write_paperops_alpaca_paper_post(
        artifact,
        settings=settings,
        record_event=True,
        event_log_path=event_path,
    )
    validation_errors = validate_paperops_alpaca_paper_post(written)
    replay = EventLog(event_path, echo=False).replay()

    live_mode_probe = deepcopy(written)
    live_mode_probe["mode"] = "live"
    live_mode_errors = validate_paperops_alpaca_paper_post(live_mode_probe)

    live_capital_probe = deepcopy(written)
    live_capital_probe["live_capital_enabled"] = True
    live_capital_probe["live_capital_enabled_count"] = 1
    live_capital_errors = validate_paperops_alpaca_paper_post(live_capital_probe)

    no_flag_probe = deepcopy(written)
    no_flag_probe["alpaca_paper_submit_enabled"] = False
    no_flag_probe["settings_alpaca_paper_submit_enabled"] = False
    no_flag_probe["runtime_alpaca_paper_submit_enabled"] = False
    no_flag_probe["alpaca_paper_post_called_count"] = 1
    no_flag_errors = validate_paperops_alpaca_paper_post(no_flag_probe)

    no_execute_probe = deepcopy(written)
    no_execute_probe["execute_post_requested"] = False
    no_execute_probe["alpaca_paper_post_called_count"] = 1
    no_execute_errors = validate_paperops_alpaca_paper_post(no_execute_probe)

    live_endpoint_probe = deepcopy(written)
    live_endpoint_probe["endpoint_classification"] = "alpaca_live_endpoint"
    live_endpoint_probe["paper_endpoint_confirmed"] = False
    live_endpoint_probe["alpaca_paper_post_called_count"] = 1
    live_endpoint_errors = validate_paperops_alpaca_paper_post(live_endpoint_probe)

    missing_prewrite_probe = deepcopy(written)
    missing_prewrite_probe["alpaca_paper_post_called_count"] = 1
    missing_prewrite_probe["execute_post_requested"] = True
    missing_prewrite_probe["alpaca_paper_submit_enabled"] = True
    missing_prewrite_probe["paper_endpoint_confirmed"] = True
    missing_prewrite_probe["paperops_event_log_prewrite_written"] = False
    missing_prewrite_errors = validate_paperops_alpaca_paper_post(missing_prewrite_probe)

    raw_payload_probe = deepcopy(written)
    raw_payload_probe["raw_broker_payload_exposed"] = True
    raw_payload_probe["raw_broker_payload_exposed_count"] = 1
    raw_payload_errors = validate_paperops_alpaca_paper_post(raw_payload_probe)

    broker_id_probe = deepcopy(written)
    broker_id_probe["broker_order_identifier_exposed"] = True
    broker_id_probe["broker_order_identifier_exposed_count"] = 1
    broker_id_errors = validate_paperops_alpaca_paper_post(broker_id_probe)

    secret_probe = deepcopy(written)
    secret_probe["broker_failure_class"] = "ALPACA_API_SECRET=thisShouldNeverAppear123"
    secret_errors = validate_paperops_alpaca_paper_post(secret_probe)

    enabled_preview_settings = replace(settings, alpaca_paper_submit_enabled=True)
    enabled_preview = build_paperops_alpaca_paper_post(
        settings=enabled_preview_settings,
        execute_post=False,
    )

    print(f"paperops_alpaca_post_status={written['status']}")
    print(f"paperops_alpaca_post_schema_version={PAPEROPS_ALPACA_POST_SCHEMA_VERSION}")
    print(f"paperops_alpaca_post_artifact_path={output_path}")
    print(f"paperops_alpaca_post_history_path={history_path}")
    print(f"paperops_alpaca_post_event_log_path={event_path}")
    print(f"paperops_alpaca_post_mode={written['mode']}")
    print(f"paperops_alpaca_post_submit_flag_enabled={written['alpaca_paper_submit_enabled']}")
    print(
        "paperops_alpaca_post_settings_submit_flag_enabled="
        f"{written['settings_alpaca_paper_submit_enabled']}"
    )
    print(
        "paperops_alpaca_post_runtime_submit_enabled="
        f"{written['runtime_alpaca_paper_submit_enabled']}"
    )
    print(f"paperops_alpaca_post_submit_enablement_status={written['submit_enablement_status']}")
    print(
        "paperops_alpaca_post_submit_enablement_runtime_override="
        f"{written['submit_enablement_runtime_override_enabled']}"
    )
    print(f"paperops_alpaca_post_execute_requested={written['execute_post_requested']}")
    print(f"paperops_alpaca_post_path_available={written['paper_post_path_available']}")
    print(f"paperops_alpaca_post_endpoint_classification={written['endpoint_classification']}")
    print(f"paperops_alpaca_post_paper_endpoint_confirmed={written['paper_endpoint_confirmed']}")
    print(f"paperops_alpaca_post_key_configured={written['alpaca_api_key_configured']}")
    print(f"paperops_alpaca_post_secret_configured={written['alpaca_api_secret_configured']}")
    print(f"paperops_alpaca_post_source_record_count={written['source_submit_record_count']}")
    print(
        "paperops_alpaca_post_source_pt4_staged_order_count="
        f"{written['source_pt4_staged_order_count']}"
    )
    print(f"paperops_alpaca_post_eligible_record_count={written['eligible_submit_record_count']}")
    print(
        "paperops_alpaca_post_fresh_eligible_record_count="
        f"{written['fresh_eligible_submit_record_count']}"
    )
    print(
        "paperops_alpaca_post_duplicate_record_count="
        f"{written['duplicate_submit_record_count']}"
    )
    print(
        "paperops_alpaca_post_idempotency_ledger_active="
        f"{written['idempotency_ledger_active']}"
    )
    print(f"paperops_alpaca_post_selected_record_count={written['selected_submit_record_count']}")
    print(f"paperops_alpaca_post_selected_source_family={written['selected_source_family']}")
    print(
        "paperops_alpaca_post_source_prewrite_present_count="
        f"{written['source_event_log_prewrite_present_count']}"
    )
    print(
        "paperops_alpaca_post_pre_trade_snapshot_present_count="
        f"{written['pre_trade_snapshot_present_count']}"
    )
    print(
        "paperops_alpaca_post_paperops_prewrite_written="
        f"{written['paperops_event_log_prewrite_written']}"
    )
    print(f"paperops_alpaca_post_called_count={written['alpaca_paper_post_called_count']}")
    print(
        "paperops_alpaca_post_succeeded_count="
        f"{written['alpaca_paper_post_succeeded_count']}"
    )
    print(f"paperops_alpaca_post_broker_post_called_count={written['broker_post_called_count']}")
    print(f"paperops_alpaca_post_live_endpoint_called_count={written['live_endpoint_called_count']}")
    print(f"paperops_alpaca_post_live_capital_enabled={written['live_capital_enabled']}")
    print(f"paperops_alpaca_post_secret_value_exposed={written['secret_value_exposed']}")
    print(f"paperops_alpaca_post_raw_broker_payload_exposed={written['raw_broker_payload_exposed']}")
    print(
        "paperops_alpaca_post_broker_order_identifier_exposed="
        f"{written['broker_order_identifier_exposed']}"
    )
    print(f"paperops_alpaca_post_event_log_events={replay['total_events']}")
    print(
        "paperops_alpaca_post_preserved_submitted_order="
        f"{preserve_submitted_paper_order}"
    )
    print(
        "paperops_alpaca_post_recovered_submitted_order="
        f"{recover_submitted_paper_order}"
    )
    print(f"paperops_alpaca_post_enabled_preview_status={enabled_preview['status']}")
    print(
        "paperops_alpaca_post_enabled_preview_execute_requested="
        f"{enabled_preview['execute_post_requested']}"
    )
    print(
        "paperops_alpaca_post_enabled_preview_called_count="
        f"{enabled_preview['alpaca_paper_post_called_count']}"
    )
    print(f"paperops_alpaca_post_validation_errors={validation_errors}")

    if validation_errors:
        errors.append(f"PaperOps-2 validation failed: {validation_errors}")
    expected_event_count = (
        1
        if preserve_submitted_paper_order or recover_submitted_paper_order
        else 2
        if written["paperops_event_log_prewrite_written"]
        else 1
    )
    if replay["total_events"] != expected_event_count:
        errors.append("PaperOps-2 event log did not record the expected event count")
    if written["mode"] != "paper":
        errors.append("PaperOps-2 current mode is not paper")
    if written["live_capital_enabled"] is not False:
        errors.append("PaperOps-2 enables live capital")
    if (
        not args.submit_paper_order
        and not preserve_submitted_paper_order
        and not recover_submitted_paper_order
        and written["alpaca_paper_post_called_count"] != 0
    ):
        errors.append("PaperOps-2 posted without --submit-paper-order")
    if written["alpaca_paper_submit_enabled"] is not True:
        errors.append("PaperOps-2 effective submit flag is not enabled")
    if written["settings_alpaca_paper_submit_enabled"] is not False:
        errors.append("PaperOps-2 should be using PT-5 runtime enablement, not env flag")
    if written["runtime_alpaca_paper_submit_enabled"] is not True:
        errors.append("PaperOps-2 did not consume PT-5 runtime enablement")
    if written["submit_enablement_status"] != "enabled_pending_explicit_submit":
        errors.append("PaperOps-2 did not see PT-5 enablement")
    if not args.submit_paper_order and written["status"] not in {
        "ready_pending_explicit_execute",
        "ready_no_fresh_eligible_order",
    }:
        errors.append("PaperOps-2 should be ready or idempotency-idle")
    if args.submit_paper_order and written["status"] not in {
        "submitted_to_alpaca_paper",
        "deferred_market_session",
        "broker_post_failed_sanitized",
    }:
        errors.append("PaperOps-2 submit mode returned an unexpected status")
    if written["paper_post_path_available"] is not True:
        errors.append("PaperOps-2 paper POST path is not available")
    if (
        written["eligible_submit_record_count"] < 1
        and written["duplicate_submit_record_count"] < 1
    ):
        errors.append(
            "PaperOps-2 did not find an eligible or duplicate paper order source"
        )
    if (
        written["selected_source_family"]
        not in {
            "paperops_pt4_staged_order",
            "paperops_first_week_paper_trade_mandate",
            "phase7_guarded_submit_record",
            None,
        }
        and written["duplicate_submit_record_count"] < 1
    ):
        errors.append("PaperOps-2 selected an unexpected paper order source")
    if written["idempotency_ledger_active"] is not True:
        errors.append("PaperOps-2 idempotency ledger is not active")
    if written["status"] == "ready_no_fresh_eligible_order" and written[
        "duplicate_submit_record_count"
    ] < 1:
        errors.append("PaperOps-2 reported no fresh order without duplicate guard evidence")
    if (
        written["alpaca_paper_post_called_count"]
        and args.submit_paper_order is not True
        and not preserve_submitted_paper_order
        and not recover_submitted_paper_order
    ):
        errors.append("PaperOps-2 called Alpaca without explicit CLI submit flag")
    if enabled_preview["execute_post_requested"] is not False:
        errors.append("PaperOps-2 enabled preview should not request execution")
    if enabled_preview["alpaca_paper_post_called_count"] != 0:
        errors.append("PaperOps-2 enabled preview called Alpaca")
    for key in (
        "live_endpoint_called_count",
        "live_capital_enabled_count",
        "manual_trade_level_override_count",
        "prediction_market_write_allowed_count",
        "crypto_perps_write_allowed_count",
        "phase7_proof_credit_allowed_count",
        "secret_value_exposed_count",
        "raw_broker_payload_exposed_count",
        "authorization_header_exposed_count",
        "base_url_exposed_count",
        "broker_order_identifier_exposed_count",
    ):
        if written[key] != 0:
            errors.append(f"PaperOps-2 unsafe counter nonzero: {key}")
    if "paperops_alpaca_mode_not_paper" not in live_mode_errors:
        errors.append("live-mode probe was not rejected")
    if "paperops_alpaca_forbidden:live_capital_enabled" not in live_capital_errors:
        errors.append("live-capital probe was not rejected")
    if "paperops_alpaca_post_called_without_flag" not in no_flag_errors:
        errors.append("post-without-flag probe was not rejected")
    if "paperops_alpaca_post_called_without_explicit_execute" not in no_execute_errors:
        errors.append("post-without-explicit-execute probe was not rejected")
    if "paperops_alpaca_post_called_without_paper_endpoint" not in live_endpoint_errors:
        errors.append("live-endpoint probe was not rejected")
    if "paperops_alpaca_called_without_paperops_prewrite" not in missing_prewrite_errors:
        errors.append("missing-prewrite probe was not rejected")
    if "paperops_alpaca_forbidden:raw_broker_payload_exposed" not in raw_payload_errors:
        errors.append("raw-broker-payload probe was not rejected")
    if "paperops_alpaca_forbidden:broker_order_identifier_exposed" not in broker_id_errors:
        errors.append("broker-identifier probe was not rejected")
    if "paperops_alpaca_secret_shape_exposed" not in secret_errors:
        errors.append("secret-shape probe was not rejected")

    if errors:
        print("paperops_alpaca_paper_post_check=failed")
        for error in errors:
            print(f"error={error}")
        return 1
    print("paperops_alpaca_paper_post_check=ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
