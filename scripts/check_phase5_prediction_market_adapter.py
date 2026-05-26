#!/usr/bin/env python3
"""Validate the Q5-9 prediction-market read-only adapter placeholder."""

from __future__ import annotations

from copy import deepcopy
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from orchestrator.config import Settings  # noqa: E402
from orchestrator.event_log import EventLog  # noqa: E402
from orchestrator.phase5_prediction_market_adapter import (  # noqa: E402
    PHASE5_PREDICTION_MARKET_ADAPTER_SCHEMA_VERSION,
    PREDICTION_MARKET_REQUIRED_CHECKS,
    PREDICTION_MARKET_ROUTE_KEYS,
    build_phase5_prediction_market_adapter,
    prediction_market_adapter_paths,
    validate_phase5_prediction_market_adapter_bundle,
    validate_phase5_prediction_market_route,
    write_phase5_prediction_market_adapter,
)


def _route(bundle: dict, route_key: str) -> dict:
    for record in bundle.get("records", []):
        if isinstance(record, dict) and record.get("route_key") == route_key:
            return record
    raise RuntimeError(f"missing route {route_key}")


def _route_errors(record: dict, **updates: object) -> list[str]:
    probe = deepcopy(record)
    for key, value in updates.items():
        probe[key] = value
    return validate_phase5_prediction_market_route(probe)


def _placeholder_probe_errors(record: dict, field: str, value: object) -> list[str]:
    probe = deepcopy(record)
    placeholder = dict(probe.get("guarded_execution_placeholder", {}))
    placeholder[field] = value
    probe["guarded_execution_placeholder"] = placeholder
    return validate_phase5_prediction_market_route(probe)


def main() -> int:
    errors: list[str] = []
    settings = Settings.from_env()
    output_path, history_path, event_log_path = prediction_market_adapter_paths(settings)
    if event_log_path.exists():
        event_log_path.unlink()

    bundle = build_phase5_prediction_market_adapter(settings=settings)
    output_path, history_path, event_log_path, written_bundle = (
        write_phase5_prediction_market_adapter(
            bundle,
            settings=settings,
            record_event=True,
            event_log_path=event_log_path,
        )
    )
    validation_errors = validate_phase5_prediction_market_adapter_bundle(written_bundle)
    event_replay = EventLog(event_log_path, echo=False).replay()
    polymarket = _route(written_bundle, "polymarket_context")
    kalshi = _route(written_bundle, "kalshi_context")
    hyperliquid = _route(written_bundle, "hyperliquid_context")
    privex_base = _route(written_bundle, "privex_base_perps")

    write_probe_errors = _route_errors(polymarket, prediction_market_write_allowed=True)
    spend_probe_errors = _placeholder_probe_errors(polymarket, "spend_allowed", True)
    order_probe_errors = _placeholder_probe_errors(polymarket, "order_placement_allowed", True)
    source_quorum_probe_errors = _route_errors(polymarket, preference_source_quorum_credit_allowed=True)
    canonical_probe_errors = _route_errors(polymarket, preference_counts_as_canonical_source=True)
    missing_provenance_probe = deepcopy(polymarket)
    missing_provenance_probe["preference_provenance"] = dict(
        missing_provenance_probe.get("preference_provenance", {})
    )
    missing_provenance_probe["preference_provenance"]["provenance_valid"] = False
    missing_provenance_errors = validate_phase5_prediction_market_route(missing_provenance_probe)
    live_endpoint_errors = _route_errors(polymarket, endpoint_classification="live_endpoint")
    paid_tool_errors = _route_errors(polymarket, paid_tool_call_performed=True)
    domain_tool_errors = _route_errors(polymarket, domain_tool_call_performed=True)
    search_tools_errors = _route_errors(polymarket, search_tools_call_performed=True)
    perps_write_errors = _route_errors(privex_base, crypto_perps_write_allowed=True)
    raw_payload_errors = _route_errors(polymarket, raw_payload_exposed=True)
    auth_header_errors = _route_errors(polymarket, authorization_header_exposed=True)
    broker_write_errors = _route_errors(polymarket, broker_write_allowed=True)
    paper_order_errors = _route_errors(polymarket, paper_order_allowed=True)
    submitted_order_errors = _route_errors(polymarket, paper_order_submitted=True)

    print("phase5_prediction_market_adapter_status=" + written_bundle["status"])
    print(
        "phase5_prediction_market_adapter_schema_version="
        f"{PHASE5_PREDICTION_MARKET_ADAPTER_SCHEMA_VERSION}"
    )
    print(f"phase5_prediction_market_adapter_artifact_path={output_path}")
    print(f"phase5_prediction_market_adapter_history_path={history_path}")
    print(f"phase5_prediction_market_adapter_event_log_path={event_log_path}")
    print(f"phase5_prediction_market_adapter_route_count={written_bundle['route_count']}")
    print(
        "phase5_prediction_market_adapter_prediction_route_count="
        f"{written_bundle['prediction_market_route_count']}"
    )
    print(
        "phase5_prediction_market_adapter_read_only_route_count="
        f"{written_bundle['read_only_route_count']}"
    )
    print(
        "phase5_prediction_market_adapter_context_count="
        f"{written_bundle['preference_prediction_market_context_count']}"
    )
    print(
        "phase5_prediction_market_adapter_policy_risk_caution_context_count="
        f"{written_bundle['policy_risk_caution_context_count']}"
    )
    print(
        "phase5_prediction_market_adapter_guarded_placeholder_count="
        f"{written_bundle['guarded_placeholder_count']}"
    )
    print(
        "phase5_prediction_market_adapter_paper_not_available_count="
        f"{written_bundle['paper_not_available_count']}"
    )
    print(
        "phase5_prediction_market_adapter_live_blocked_count="
        f"{written_bundle['live_blocked_count']}"
    )
    print(
        "phase5_prediction_market_adapter_preference_provenance_status="
        f"{written_bundle['preference_provenance_status']}"
    )
    print(
        "phase5_prediction_market_adapter_preference_context_status="
        f"{written_bundle['preference_context_status']}"
    )
    print(
        "phase5_prediction_market_adapter_preference_distinct_upstream_source_count="
        f"{written_bundle['preference_distinct_upstream_source_count']}"
    )
    print(
        "phase5_prediction_market_adapter_event_log_written="
        f"{written_bundle['event_log_written']}"
    )
    print(
        "phase5_prediction_market_adapter_event_log_total_events="
        f"{event_replay['total_events']}"
    )
    print(
        "phase5_prediction_market_adapter_validation_error_count="
        f"{len(validation_errors)}"
    )
    print(
        "phase5_prediction_market_adapter_polymarket_status="
        f"{polymarket['status']}"
    )
    print(
        "phase5_prediction_market_adapter_kalshi_status="
        f"{kalshi['status']}"
    )
    print(
        "phase5_prediction_market_adapter_hyperliquid_status="
        f"{hyperliquid['status']}"
    )
    for key in (
        "prediction_market_write_allowed_count",
        "prediction_market_order_allowed_count",
        "prediction_market_spend_allowed_count",
        "prediction_market_live_order_allowed_count",
        "polymarket_write_allowed_count",
        "kalshi_write_allowed_count",
        "hyperliquid_write_allowed_count",
        "dflow_write_allowed_count",
        "privex_write_allowed_count",
        "crypto_perps_write_allowed_count",
        "paid_preference_tools_allowed_count",
        "broker_write_allowed_count",
        "broker_post_called_count",
        "paper_order_allowed_count",
        "paper_order_submitted_count",
        "live_capital_enabled_count",
        "live_endpoint_allowed_count",
        "secret_value_exposed_count",
        "raw_payload_exposed_count",
        "local_path_exposed_count",
        "authorization_header_exposed_count",
        "base_url_exposed_count",
    ):
        print(f"phase5_prediction_market_adapter_{key}={written_bundle[key]}")
    print(
        "phase5_prediction_market_adapter_write_probe_error_count="
        f"{len(write_probe_errors)}"
    )
    print(
        "phase5_prediction_market_adapter_spend_probe_error_count="
        f"{len(spend_probe_errors)}"
    )
    print(
        "phase5_prediction_market_adapter_order_probe_error_count="
        f"{len(order_probe_errors)}"
    )
    print(
        "phase5_prediction_market_adapter_source_quorum_probe_error_count="
        f"{len(source_quorum_probe_errors)}"
    )
    print(
        "phase5_prediction_market_adapter_canonical_probe_error_count="
        f"{len(canonical_probe_errors)}"
    )
    print(
        "phase5_prediction_market_adapter_missing_provenance_probe_error_count="
        f"{len(missing_provenance_errors)}"
    )
    print(
        "phase5_prediction_market_adapter_live_endpoint_probe_error_count="
        f"{len(live_endpoint_errors)}"
    )
    print(
        "phase5_prediction_market_adapter_paid_tool_probe_error_count="
        f"{len(paid_tool_errors)}"
    )
    print(
        "phase5_prediction_market_adapter_domain_tool_probe_error_count="
        f"{len(domain_tool_errors)}"
    )
    print(
        "phase5_prediction_market_adapter_search_tools_probe_error_count="
        f"{len(search_tools_errors)}"
    )
    print(
        "phase5_prediction_market_adapter_perps_write_probe_error_count="
        f"{len(perps_write_errors)}"
    )
    print(
        "phase5_prediction_market_adapter_raw_payload_probe_error_count="
        f"{len(raw_payload_errors)}"
    )
    print(
        "phase5_prediction_market_adapter_auth_header_probe_error_count="
        f"{len(auth_header_errors)}"
    )
    print(
        "phase5_prediction_market_adapter_broker_write_probe_error_count="
        f"{len(broker_write_errors)}"
    )
    print(
        "phase5_prediction_market_adapter_paper_order_probe_error_count="
        f"{len(paper_order_errors)}"
    )
    print(
        "phase5_prediction_market_adapter_submitted_order_probe_error_count="
        f"{len(submitted_order_errors)}"
    )
    print("phase5_prediction_market_adapter_boundary=" + written_bundle["boundary"])

    if validation_errors:
        errors.extend(validation_errors)
    if written_bundle["status"] != "ok":
        errors.append("prediction_market_adapter_bundle_not_ok")
    if written_bundle["route_count"] != len(PREDICTION_MARKET_ROUTE_KEYS):
        errors.append("prediction_market_adapter_route_count_mismatch")
    if written_bundle["prediction_market_route_count"] != 2:
        errors.append("prediction_market_adapter_prediction_route_count_not_two")
    if written_bundle["read_only_route_count"] != 2:
        errors.append("prediction_market_adapter_read_only_route_count_not_two")
    if written_bundle["preference_prediction_market_context_count"] != 2:
        errors.append("prediction_market_adapter_context_count_not_two")
    if written_bundle["policy_risk_caution_context_count"] != 2:
        errors.append("prediction_market_adapter_policy_risk_caution_count_not_two")
    if written_bundle["guarded_placeholder_count"] != written_bundle["route_count"]:
        errors.append("prediction_market_adapter_placeholder_count_mismatch")
    if written_bundle["paper_not_available_count"] != 2:
        errors.append("prediction_market_adapter_paper_not_available_count_not_two")
    if written_bundle["live_blocked_count"] != 4:
        errors.append("prediction_market_adapter_live_blocked_count_not_four")
    if written_bundle["required_check_count"] != len(PREDICTION_MARKET_REQUIRED_CHECKS):
        errors.append("prediction_market_adapter_required_check_count_mismatch")
    if written_bundle["event_log_written"] is not True:
        errors.append("prediction_market_adapter_event_log_not_written")
    if event_replay["total_events"] != written_bundle["route_count"]:
        errors.append("prediction_market_adapter_event_log_count_mismatch")
    if written_bundle["preference_provenance_status"] != "validated":
        errors.append("prediction_market_adapter_preference_provenance_not_validated")
    if written_bundle["preference_context_status"] != "explicit_multi_upstream_context":
        errors.append("prediction_market_adapter_preference_context_not_multi_upstream")
    for key in (
        "preference_counts_as_canonical_source",
        "preference_only_source_quorum_allowed",
        "preference_source_quorum_credit_allowed",
        "strategy_source_quorum_credit_allowed",
    ):
        if written_bundle.get(key) is not False:
            errors.append(f"prediction_market_adapter_preference_overclaim:{key}")
    for key in (
        "prediction_market_write_allowed_count",
        "prediction_market_order_allowed_count",
        "prediction_market_spend_allowed_count",
        "prediction_market_live_order_allowed_count",
        "polymarket_write_allowed_count",
        "kalshi_write_allowed_count",
        "hyperliquid_write_allowed_count",
        "dflow_write_allowed_count",
        "privex_write_allowed_count",
        "crypto_perps_write_allowed_count",
        "paid_preference_tools_allowed_count",
        "broker_write_allowed_count",
        "broker_post_called_count",
        "paper_order_allowed_count",
        "paper_order_submitted_count",
        "live_capital_enabled_count",
        "live_endpoint_allowed_count",
        "secret_value_exposed_count",
        "raw_payload_exposed_count",
        "local_path_exposed_count",
        "authorization_header_exposed_count",
        "base_url_exposed_count",
    ):
        if written_bundle.get(key) != 0:
            errors.append(f"prediction_market_adapter_boundary_count_not_zero:{key}")
    for route in (polymarket, kalshi):
        if route.get("status") != "hold":
            errors.append(f"prediction_market_adapter_context_route_not_hold:{route.get('route_key')}")
        if route.get("read_only_route") is not True:
            errors.append(f"prediction_market_adapter_context_route_not_read_only:{route.get('route_key')}")
        if route.get("context_informs_policy_risk_caution") is not True:
            errors.append(f"prediction_market_adapter_context_not_policy_caution:{route.get('route_key')}")
        if route.get("preference_provenance_valid") is not True:
            errors.append(f"prediction_market_adapter_context_provenance_invalid:{route.get('route_key')}")
    for route_key in ("hyperliquid_context", "dflow_context", "privex_base_perps", "privex_coti_perps"):
        route = _route(written_bundle, route_key)
        if route.get("status") != "live_blocked":
            errors.append(f"prediction_market_adapter_disabled_route_not_live_blocked:{route_key}")
        if route.get("crypto_perps_write_allowed") is not False:
            errors.append(f"prediction_market_adapter_disabled_route_perps_write:{route_key}")
    if "prediction_market_boundary_enabled:prediction_market_write_allowed" not in write_probe_errors:
        errors.append("prediction_market_adapter_write_probe_not_rejected")
    if "guarded_placeholder_authority_enabled:spend_allowed" not in spend_probe_errors:
        errors.append("prediction_market_adapter_spend_probe_not_rejected")
    if "guarded_placeholder_authority_enabled:order_placement_allowed" not in order_probe_errors:
        errors.append("prediction_market_adapter_order_probe_not_rejected")
    if "preference_source_quorum_credit_allowed" not in source_quorum_probe_errors:
        errors.append("prediction_market_adapter_source_quorum_probe_not_rejected")
    if "preference_counts_as_canonical_source" not in canonical_probe_errors:
        errors.append("prediction_market_adapter_canonical_probe_not_rejected")
    if "required_preference_provenance_invalid" not in missing_provenance_errors:
        errors.append("prediction_market_adapter_missing_provenance_probe_not_rejected")
    if "live_endpoint_classification" not in live_endpoint_errors:
        errors.append("prediction_market_adapter_live_endpoint_probe_not_rejected")
    if "paid_tool_call_performed" not in paid_tool_errors:
        errors.append("prediction_market_adapter_paid_tool_probe_not_rejected")
    if "domain_tool_call_performed" not in domain_tool_errors:
        errors.append("prediction_market_adapter_domain_tool_probe_not_rejected")
    if "search_tools_call_performed" not in search_tools_errors:
        errors.append("prediction_market_adapter_search_tools_probe_not_rejected")
    if "phase5_authority_enabled:crypto_perps_write_allowed" not in perps_write_errors:
        errors.append("prediction_market_adapter_perps_write_probe_not_rejected")
    if "prediction_market_exposure_enabled:raw_payload_exposed" not in raw_payload_errors:
        errors.append("prediction_market_adapter_raw_payload_probe_not_rejected")
    if "prediction_market_exposure_enabled:authorization_header_exposed" not in auth_header_errors:
        errors.append("prediction_market_adapter_auth_header_probe_not_rejected")
    if "phase5_authority_enabled:broker_write_allowed" not in broker_write_errors:
        errors.append("prediction_market_adapter_broker_write_probe_not_rejected")
    if "phase5_authority_enabled:paper_order_allowed" not in paper_order_errors:
        errors.append("prediction_market_adapter_paper_order_probe_not_rejected")
    if "prediction_market_boundary_enabled:paper_order_submitted" not in submitted_order_errors:
        errors.append("prediction_market_adapter_submitted_order_probe_not_rejected")
    if "Polymarket and Kalshi context" not in written_bundle["boundary"]:
        errors.append("prediction_market_adapter_boundary_weak")

    if errors:
        for error in errors:
            print(f"phase5_prediction_market_adapter_error={error}")
        print("phase5_prediction_market_adapter_check=failed")
        return 1

    print("phase5_prediction_market_adapter_check=ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
