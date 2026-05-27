#!/usr/bin/env python3
"""Validate PT-6 active PaperOps paper lifecycle polling enablement."""

from __future__ import annotations

from copy import deepcopy
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from orchestrator.config import Settings  # noqa: E402
from orchestrator.event_log import EventLog  # noqa: E402
from orchestrator.paperops_paper_lifecycle_poller import (  # noqa: E402
    build_paperops_paper_lifecycle_poller,
    read_latest_paperops_paper_lifecycle_poller,
    write_paperops_paper_lifecycle_poller,
)
from orchestrator.paperops_paper_lifecycle_polling_enablement import (  # noqa: E402
    PAPEROPS_LIFECYCLE_POLLING_ENABLEMENT_SCHEMA_VERSION,
    build_paperops_paper_lifecycle_polling_enablement,
    paperops_paper_lifecycle_polling_enablement_paths,
    validate_paperops_paper_lifecycle_polling_enablement,
    write_paperops_paper_lifecycle_polling_enablement,
)


def main() -> int:
    errors: list[str] = []
    settings = Settings.from_env()
    output_path, history_path, event_path = (
        paperops_paper_lifecycle_polling_enablement_paths(settings)
    )
    if event_path.exists():
        event_path.unlink()

    artifact = build_paperops_paper_lifecycle_polling_enablement(settings=settings)
    output_path, history_path, event_path, written = (
        write_paperops_paper_lifecycle_polling_enablement(
            artifact,
            settings=settings,
            record_event=True,
            event_log_path=event_path,
        )
    )
    validation_errors = validate_paperops_paper_lifecycle_polling_enablement(written)
    replay = EventLog(event_path, echo=False).replay()

    poll_now = False
    existing_poller = read_latest_paperops_paper_lifecycle_poller(settings)
    preserve_lifecycle_readback = (
        existing_poller.get("status") == "paper_lifecycle_poll_recorded"
        and "phase7_proof_credit_allowed" in existing_poller
    )
    poller = (
        existing_poller
        if preserve_lifecycle_readback
        else build_paperops_paper_lifecycle_poller(
            settings=settings,
            poll_paper_orders=False,
        )
    )
    _, _, _, poller_written = write_paperops_paper_lifecycle_poller(
        poller,
        settings=settings,
        record_event=True,
    )

    env_probe = deepcopy(written)
    env_probe["env_file_edited"] = True
    env_errors = validate_paperops_paper_lifecycle_polling_enablement(env_probe)

    poll_request_probe = deepcopy(written)
    poll_request_probe["poll_now_requested"] = True
    poll_request_errors = validate_paperops_paper_lifecycle_polling_enablement(
        poll_request_probe
    )

    live_capital_probe = deepcopy(written)
    live_capital_probe["live_capital_enabled"] = True
    live_capital_errors = validate_paperops_paper_lifecycle_polling_enablement(
        live_capital_probe
    )

    broker_post_probe = deepcopy(written)
    broker_post_probe["broker_post_allowed"] = True
    broker_post_probe["unsafe_write_counter_total"] = 1
    broker_post_errors = validate_paperops_paper_lifecycle_polling_enablement(
        broker_post_probe
    )

    live_endpoint_probe = deepcopy(written)
    live_endpoint_probe["live_endpoint_allowed"] = True
    live_endpoint_probe["live_endpoint_called_count"] = 1
    live_endpoint_errors = validate_paperops_paper_lifecycle_polling_enablement(
        live_endpoint_probe
    )

    proof_probe = deepcopy(written)
    proof_probe["phase7_proof_credit_allowed"] = True
    proof_errors = validate_paperops_paper_lifecycle_polling_enablement(proof_probe)

    forced_probe = deepcopy(written)
    forced_probe["forced_trades_allowed"] = True
    forced_errors = validate_paperops_paper_lifecycle_polling_enablement(forced_probe)

    secret_probe = deepcopy(written)
    secret_probe["secret_value_exposed"] = True
    secret_errors = validate_paperops_paper_lifecycle_polling_enablement(secret_probe)

    get_counter_probe = deepcopy(written)
    get_counter_probe["broker_get_called_count"] = 1
    get_counter_errors = validate_paperops_paper_lifecycle_polling_enablement(
        get_counter_probe
    )

    path_without_source_probe = deepcopy(written)
    path_without_source_probe["paper_poll_path_available"] = True
    path_without_source_probe["paperops_2_submitted_paper_order_count"] = 0
    path_without_source_errors = validate_paperops_paper_lifecycle_polling_enablement(
        path_without_source_probe
    )

    print(f"paperops_lifecycle_polling_enablement_status={written['status']}")
    print(
        "paperops_lifecycle_polling_enablement_schema_version="
        f"{PAPEROPS_LIFECYCLE_POLLING_ENABLEMENT_SCHEMA_VERSION}"
    )
    print(f"paperops_lifecycle_polling_enablement_artifact_path={output_path}")
    print(f"paperops_lifecycle_polling_enablement_history_path={history_path}")
    print(f"paperops_lifecycle_polling_enablement_event_log_path={event_path}")
    print(f"paperops_lifecycle_polling_enablement_mode={written['mode']}")
    print(
        "paperops_lifecycle_polling_enablement_active="
        f"{written['active_lifecycle_polling_enabled']}"
    )
    print(
        "paperops_lifecycle_polling_enablement_effective="
        f"{written['paper_lifecycle_polling_effective']}"
    )
    print(
        "paperops_lifecycle_polling_enablement_path_available="
        f"{written['paper_poll_path_available']}"
    )
    print(
        "paperops_lifecycle_polling_enablement_idle_until_submitted_order="
        f"{written['paper_poll_idle_until_submitted_order']}"
    )
    print(
        "paperops_lifecycle_polling_enablement_explicit_poll_flag_required="
        f"{written['explicit_poll_flag_required']}"
    )
    print(
        "paperops_lifecycle_polling_enablement_poll_now_requested="
        f"{written['poll_now_requested']}"
    )
    print(
        "paperops_lifecycle_polling_enablement_paperops2_status="
        f"{written['paperops_2_status']}"
    )
    print(
        "paperops_lifecycle_polling_enablement_paperops2_source_valid="
        f"{written['paperops_2_source_valid']}"
    )
    print(
        "paperops_lifecycle_polling_enablement_paperops2_path_available="
        f"{written['paperops_2_paper_post_path_available']}"
    )
    print(
        "paperops_lifecycle_polling_enablement_paperops2_submitted_order_count="
        f"{written['paperops_2_submitted_paper_order_count']}"
    )
    print(
        "paperops_lifecycle_polling_enablement_endpoint_classification="
        f"{written['endpoint_classification']}"
    )
    print(
        "paperops_lifecycle_polling_enablement_paper_endpoint_confirmed="
        f"{written['paper_endpoint_confirmed']}"
    )
    print(
        "paperops_lifecycle_polling_enablement_key_configured="
        f"{written['alpaca_api_key_configured']}"
    )
    print(
        "paperops_lifecycle_polling_enablement_secret_configured="
        f"{written['alpaca_api_secret_configured']}"
    )
    print(
        "paperops_lifecycle_polling_enablement_broker_get_allowed="
        f"{written['paper_broker_get_allowed']}"
    )
    print(
        "paperops_lifecycle_polling_enablement_broker_get_called_count="
        f"{written['broker_get_called_count']}"
    )
    print(
        "paperops_lifecycle_polling_enablement_live_endpoint_called_count="
        f"{written['live_endpoint_called_count']}"
    )
    print(
        "paperops_lifecycle_polling_enablement_live_capital_enabled="
        f"{written['live_capital_enabled']}"
    )
    print(
        "paperops_lifecycle_polling_enablement_phase7_proof_credit_allowed="
        f"{written['phase7_proof_credit_allowed']}"
    )
    print(
        "paperops_lifecycle_polling_enablement_forced_trades_allowed="
        f"{written['forced_trades_allowed']}"
    )
    print(
        "paperops_lifecycle_polling_enablement_unsafe_write_counter_total="
        f"{written['unsafe_write_counter_total']}"
    )
    print(f"paperops_lifecycle_polling_enablement_event_log_events={replay['total_events']}")
    print(
        "paperops_lifecycle_polling_enablement_blockers="
        f"{','.join(written['blockers'])}"
    )
    print(f"paperops_lifecycle_polling_enablement_validation_errors={validation_errors}")
    print(f"paperops_lifecycle_polling_enablement_active_poll_now={poll_now}")
    print(
        "paperops_lifecycle_polling_enablement_preserved_lifecycle_readback="
        f"{preserve_lifecycle_readback}"
    )
    print(f"paperops_lifecycle_polling_enablement_poller_status={poller_written['status']}")
    print(
        "paperops_lifecycle_polling_enablement_poller_order_poll_called_count="
        f"{poller_written['paper_order_poll_called_count']}"
    )
    print(
        "paperops_lifecycle_polling_enablement_poller_broker_get_called_count="
        f"{poller_written['broker_get_called_count']}"
    )
    print(
        "paperops_lifecycle_polling_enablement_poller_live_endpoint_called_count="
        f"{poller_written['live_endpoint_called_count']}"
    )

    if validation_errors:
        errors.append(f"PT-6 validation failed: {validation_errors}")
    if replay["total_events"] != 1:
        errors.append("PT-6 event log did not record exactly one event")
    if written["status"] not in {
        "enabled_pending_submitted_paper_orders",
        "enabled_pending_explicit_poll",
    }:
        errors.append("PT-6 did not enable active lifecycle polling")
    if written["active_lifecycle_polling_enabled"] is not True:
        errors.append("PT-6 active polling flag is not true")
    if written["paper_lifecycle_polling_effective"] is not True:
        errors.append("PT-6 effective polling flag is not true")
    if written["paperops_2_source_valid"] is not True:
        errors.append("PT-6 did not see a valid PaperOps-2 source")
    if written["paperops_2_paper_post_path_available"] is not True:
        errors.append("PT-6 did not see the PaperOps-2 paper POST path")
    if written["explicit_poll_flag_required"] is not True:
        errors.append("PT-6 did not require explicit poll handoff")
    if written["poll_now_requested"] is not False:
        errors.append("PT-6 enablement requested a poll directly")
    if written["broker_get_called_count"] or written["alpaca_paper_get_called_count"]:
        errors.append("PT-6 enablement called a broker GET directly")
    if written["live_endpoint_called_count"]:
        errors.append("PT-6 called a live endpoint")
    if written["live_capital_enabled"] is not False:
        errors.append("PT-6 enabled live capital")
    if written["phase7_proof_credit_allowed"] is not False:
        errors.append("PT-6 granted Phase 7 proof credit")
    if written["forced_trades_allowed"] is not False:
        errors.append("PT-6 allowed forced trades")
    if written["paperops_2_submitted_paper_order_count"] == 0:
        if written["paper_poll_path_available"] is not False:
            errors.append("PT-6 made poll path available without submitted orders")
        if poll_now:
            errors.append("PT-6 attempted an active poll without submitted orders")
        if poller_written["paper_order_poll_called_count"] != 0:
            errors.append("PT-6 poller called Alpaca without submitted orders")
    if "paperops_lifecycle_polling_enablement_forbidden:env_file_edited" not in env_errors:
        errors.append("env-file probe was not rejected")
    if (
        "paperops_lifecycle_polling_enablement_forbidden:poll_now_requested"
        not in poll_request_errors
    ):
        errors.append("poll-request probe was not rejected")
    if (
        "paperops_lifecycle_polling_enablement_forbidden:live_capital_enabled"
        not in live_capital_errors
    ):
        errors.append("live-capital probe was not rejected")
    if (
        "paperops_lifecycle_polling_enablement_forbidden:broker_post_allowed"
        not in broker_post_errors
    ):
        errors.append("broker-post probe was not rejected")
    if (
        "paperops_lifecycle_polling_enablement_forbidden:live_endpoint_allowed"
        not in live_endpoint_errors
    ):
        errors.append("live-endpoint authority probe was not rejected")
    if (
        "paperops_lifecycle_polling_enablement_unsafe_counter_nonzero:live_endpoint_called_count"
        not in live_endpoint_errors
    ):
        errors.append("live-endpoint counter probe was not rejected")
    if (
        "paperops_lifecycle_polling_enablement_forbidden:phase7_proof_credit_allowed"
        not in proof_errors
    ):
        errors.append("proof-credit probe was not rejected")
    if "paperops_lifecycle_polling_enablement_forbidden:forced_trades_allowed" not in forced_errors:
        errors.append("forced-trade probe was not rejected")
    if "paperops_lifecycle_polling_enablement_forbidden:secret_value_exposed" not in secret_errors:
        errors.append("secret-exposure probe was not rejected")
    if (
        "paperops_lifecycle_polling_enablement_unsafe_counter_nonzero:broker_get_called_count"
        not in get_counter_errors
    ):
        errors.append("direct-get counter probe was not rejected")
    if (
        "paperops_lifecycle_polling_enablement_path_without_submitted_order"
        not in path_without_source_errors
    ):
        errors.append("path-without-submitted-order probe was not rejected")

    if errors:
        print("paperops_paper_lifecycle_polling_enablement_check=failed")
        for error in errors:
            print(f"error={error}")
        return 1
    print("paperops_paper_lifecycle_polling_enablement_check=ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
