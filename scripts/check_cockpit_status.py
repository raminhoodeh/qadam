#!/usr/bin/env python3
# ruff: noqa: E402
"""Validate the public-safe cockpit status contract."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from orchestrator.cockpit_status import (
    COCKPIT_STATUS_SCHEMA_VERSION,
    export_cockpit_status,
    validate_cockpit_status,
)  # noqa: E402
from orchestrator.config import Settings  # noqa: E402
from orchestrator.paper_account import MATURITY_CLOSED_TRADE_TARGET  # noqa: E402
from orchestrator.telegram_comms import ensure_d8a_telegram_dry_run  # noqa: E402
from world_monitor.source_registry import EXPECTED_SOURCE_COUNT  # noqa: E402


WATCHING_REQUIRED_FIELDS = {
    "auth_class",
    "cadence",
    "can_influence_signals",
    "credential_status",
    "degraded_reason",
    "endpoint_count",
    "influence_boundary",
    "last_heartbeat",
    "last_payload_time",
    "latency_ms",
    "pipeline",
    "promoted_adapter",
    "raw_status",
    "readiness",
    "registry_status",
    "source_key",
    "source_name",
    "status",
    "tier",
    "trust_score",
}

SHADOW_PACKET_REQUIRED_FIELDS = {
    "agent_key",
    "boundary",
    "created_at",
    "packet_id",
    "source_event_refs",
    "status",
    "summary",
    "uncertainty",
}

LOCAL_RESEARCH_REQUIRED_FIELDS = {
    "anomalies",
    "assessment_id",
    "confidence",
    "created_at",
    "escalation_recommendation",
    "execution_allowed",
    "missing_correlations",
    "mode",
    "model",
    "next_questions",
    "paper_order_allowed",
    "provider",
    "status",
    "summary",
    "watch_focus",
}

HYPOTHESIS_REQUIRED_FIELDS = {
    "blocked_reason",
    "confidence",
    "created_at",
    "evidence_packet_id",
    "evidence_source_count",
    "execution_allowed",
    "generated_by",
    "integrity_review_status",
    "integrity_score",
    "instrument_focus",
    "invalidation",
    "missing_correlations",
    "signal_id",
    "status",
    "thesis",
    "title",
}

EVIDENCE_PACKET_REQUIRED_FIELDS = {
    "average_trust_score",
    "created_at",
    "items",
    "min_trust_score",
    "missing_correlations",
    "signal_id",
    "source_count",
    "sources",
    "trail_id",
}

SIGNAL_INTEGRITY_REQUIRED_FIELDS = {
    "boundary",
    "by_status",
    "execution_allowed_count",
    "paper_order_allowed_count",
    "review_count",
    "schema_version",
    "status",
    "trade_candidate_created_count",
}

SIGNAL_INTEGRITY_REVIEW_REQUIRED_FIELDS = {
    "akber_filter",
    "average_trust_score",
    "boundary",
    "evidence_item_count",
    "execution_allowed",
    "failure_reasons",
    "instrument_focus",
    "integrity_score",
    "min_trust_score",
    "missing_correlations",
    "paper_order_allowed",
    "required_next_steps",
    "review_id",
    "reviewed_at",
    "signal_confidence",
    "source_count",
    "source_signal_id",
    "status",
    "trade_candidate_created",
    "worldview_prior_status",
}

RISK_AGENT_REQUIRED_FIELDS = {
    "authority",
    "boundary",
    "broker_write_allowed_count",
    "by_status",
    "execution_allowed_count",
    "max_risk_pct_per_idea",
    "order_created_count",
    "paper_order_allowed_count",
    "review_count",
    "reviews",
    "schema_version",
    "status",
}

RISK_POLICY_REVIEW_REQUIRED_FIELDS = {
    "blocked_reasons",
    "boundary",
    "broker_write_allowed",
    "checks",
    "execution_allowed",
    "instrument",
    "max_risk_gbp",
    "max_risk_pct",
    "order_created",
    "paper_account_status",
    "paper_order_allowed",
    "policy_score",
    "proposed_risk_gbp",
    "proposed_risk_pct",
    "required_next_steps",
    "review_id",
    "reviewed_at",
    "signal_integrity_status",
    "source_ref",
    "source_type",
    "status",
}

RISK_POLICY_REQUIRED_CHECKS = {
    "broker_order_route",
    "broker_write",
    "drawdown",
    "execution_policy",
    "kill_switch",
    "live_capital",
    "mode",
    "paper_order_authority",
}

MODEL_ACTIVITY_ROLES = {"Research Analyst", "Strategy Lead", "Head of Quant"}

TRADE_INTENT_REQUIRED_FIELDS = {
    "akber_filter",
    "blocked_reason",
    "boundary",
    "catalyst",
    "created_at",
    "direction",
    "evidence_summary",
    "execution_allowed",
    "holding_window",
    "instrument",
    "intent_id",
    "invalidation",
    "market_implied_probability",
    "paper_order_allowed",
    "price_gap",
    "probability_estimate",
    "proposed_entry",
    "risk_checks",
    "risk_size_gbp",
    "risk_size_pct",
    "risk_state",
    "source_signal_id",
    "source_type",
    "status",
    "strategy",
    "tags",
    "updated_at",
    "venue",
}

OBSERVED_SIGNAL_REQUIRED_FIELDS = {
    "alert_id",
    "boundary",
    "chart_context",
    "direction",
    "execution_allowed",
    "indicator_state",
    "instrument",
    "observed_at",
    "paper_order_allowed",
    "price",
    "received_at",
    "setup_type",
    "source",
    "source_type",
    "status",
    "symbol",
    "timeframe",
    "trade_candidate_created",
    "trigger",
}

TRADINGVIEW_SUMMARY_REQUIRED_FIELDS = {
    "alert_count",
    "boundary",
    "duplicate_protection",
    "execution_allowed_count",
    "latest_observed_at",
    "observed_signals",
    "paper_order_allowed_count",
    "receiver_status",
    "status",
    "trade_candidate_created_count",
}

CAPITAL_REQUIRED_FIELDS = {
    "account_scope",
    "boundary",
    "broker",
    "cash_gbp",
    "closed_trade_count",
    "closed_trades",
    "connection_status",
    "current_balance_gbp",
    "drawdown_pct",
    "equity_curve",
    "equity_gbp",
    "live_capital_enabled",
    "maturity_closed_trade_count",
    "maturity_closed_trade_target",
    "max_drawdown_pct",
    "mirror_status",
    "observed_at",
    "open_order_count",
    "open_position_count",
    "open_positions",
    "order_count",
    "orders",
    "peak_equity_gbp",
    "postmortem_complete_count",
    "postmortem_due_count",
    "postmortems_complete",
    "postmortems_due",
    "realized_pnl_gbp",
    "starting_balance_gbp",
    "timeline_status",
    "unrealized_pnl_gbp",
    "write_authority",
}

EQUITY_POINT_REQUIRED_FIELDS = {"drawdown_pct", "equity_gbp", "observed_at"}

PAPER_POSITION_REQUIRED_FIELDS = {
    "boundary",
    "current_price",
    "direction",
    "entry_price",
    "instrument",
    "invalidation",
    "opened_at",
    "position_id",
    "quantity",
    "risk_size_gbp",
    "source_intent_id",
    "status",
    "unrealized_pnl_gbp",
}

CLOSED_PAPER_TRADE_REQUIRED_FIELDS = {
    "boundary",
    "close_reason",
    "closed_at",
    "direction",
    "entry_price",
    "exit_price",
    "instrument",
    "opened_at",
    "postmortem_status",
    "r_multiple",
    "realized_pnl_gbp",
    "source_intent_id",
    "trade_id",
}

PAPER_ORDER_REQUIRED_FIELDS = {
    "boundary",
    "direction",
    "execution_allowed",
    "filled_at",
    "filled_avg_price",
    "filled_quantity",
    "instrument",
    "limit_price",
    "notional_gbp",
    "order_id",
    "order_type",
    "paper_order_allowed",
    "quantity",
    "status",
    "submitted_at",
}

PAPER_ACCOUNT_CONTEXT_REQUIRED_FIELDS = {
    "account_scope",
    "boundary",
    "broker",
    "capital_policy",
    "closed_trade_count",
    "connection_status",
    "current_balance_gbp",
    "drawdown_pct",
    "execution_allowed",
    "live_capital_enabled",
    "maturity_closed_trade_count",
    "maturity_closed_trade_target",
    "mode",
    "open_order_count",
    "open_position_count",
    "order_count",
    "paper_order_allowed",
    "realized_pnl_gbp",
    "status",
    "timeline_status",
    "trial_allocation_gbp",
    "unrealized_pnl_gbp",
    "write_authority",
}

FUND_MANAGER_NOTES_REQUIRED_FIELDS = {
    "allowed_statuses",
    "allowed_target_types",
    "boundary",
    "browser_write_scope",
    "comment_count",
    "event_log_export_count",
    "local_event_log_export",
    "recent_comments",
    "schema_version",
    "status",
    "supabase_table",
    "visibility",
}

FUND_MANAGER_COMMENT_REQUIRED_FIELDS = {
    "author_label",
    "body",
    "comment_id",
    "created_at",
    "status",
    "tags",
    "target_key",
    "target_type",
    "visibility",
}

COMMUNICATIONS_REQUIRED_FIELDS = {"boundary", "telegram"}

TELEGRAM_COMMUNICATIONS_REQUIRED_FIELDS = {
    "active_message_classes",
    "bot_configured",
    "bot_username_configured",
    "boundary",
    "default_chat_configured",
    "delivery_target_count",
    "delivery_target_modes",
    "dry_run_message_count",
    "failed_count",
    "failed_member_count",
    "group_chat_configured",
    "last_digest_title",
    "last_failure_reason",
    "last_sent_time",
    "member_count",
    "mode",
    "pending_member_count",
    "pending_queue_count",
    "recent_messages",
    "retried_count",
    "schema_version",
    "send_gate",
    "sent_count",
    "status",
    "suppressed_count",
    "verified_member_count",
}

TELEGRAM_MESSAGE_REQUIRED_FIELDS = {
    "created_at",
    "message_class",
    "message_id",
    "mode",
    "send_allowed",
    "status",
    "target_ref",
    "title",
}

LIVE_BRIDGE_REQUIRED_FIELDS = {
    "allowed_methods",
    "authentication",
    "boundary",
    "broker_write_route",
    "browser_authority",
    "cache_policy",
    "endpoint",
    "forbidden_methods",
    "generated_at",
    "health_checks",
    "local_orchestrator_exposed",
    "phase",
    "publisher",
    "rate_limit_per_minute",
    "read_only",
    "schema_version",
    "static_fallback",
    "status",
    "write_authority",
}

LIVE_BRIDGE_PUBLISHER_REQUIRED_FIELDS = {
    "payload_source",
    "signature_algorithm",
    "signature_configured",
    "signature_file",
    "status",
}

LIVE_BRIDGE_SIGNATURE_REQUIRED_FIELDS = {
    "algorithm",
    "boundary",
    "broker_write_route",
    "browser_authority",
    "payload_file",
    "payload_generated_at",
    "payload_schema_version",
    "read_only",
    "schema_version",
    "signature",
    "signature_configured",
    "signed_at",
    "status",
}


def main() -> int:
    settings = Settings.from_env()
    ensure_d8a_telegram_dry_run(settings)
    result = export_cockpit_status(settings=settings, landing_repo_path=ROOT / "landing-page-repo")
    runtime_path = Path(result["runtime_path"])
    landing_path = Path(result["landing_path"]) if result.get("landing_path") else None
    if not runtime_path.exists():
        print("cockpit_status_runtime_missing=true")
        return 1
    if landing_path is None or not landing_path.exists():
        print("cockpit_status_landing_missing=true")
        return 1
    runtime_signature_path = runtime_path.with_name("cockpit-status.signature.json")
    landing_signature_path = landing_path.with_name("cockpit-status.signature.json")
    if not runtime_signature_path.exists():
        print("cockpit_status_runtime_signature_missing=true")
        return 1
    if not landing_signature_path.exists():
        print("cockpit_status_landing_signature_missing=true")
        return 1

    payload = json.loads(runtime_path.read_text(encoding="utf-8"))
    validate_cockpit_status(payload)
    landing_payload = json.loads(landing_path.read_text(encoding="utf-8"))
    validate_cockpit_status(landing_payload)
    if landing_payload != payload:
        print("cockpit_status_landing_mismatch=true")
        return 1
    runtime_signature = json.loads(runtime_signature_path.read_text(encoding="utf-8"))
    landing_signature = json.loads(landing_signature_path.read_text(encoding="utf-8"))
    if landing_signature != runtime_signature:
        print("cockpit_status_signature_landing_mismatch=true")
        return 1

    print("cockpit_status_check=ok")
    print(f"cockpit_status_schema_version={payload['schema_version']}")
    print(f"cockpit_status_generated_at={payload['generated_at']}")
    print(f"cockpit_status_mode={payload['mode']}")
    print(f"cockpit_status_d1_phase={payload['d1_snapshot']['phase']}")
    print(f"cockpit_status_d1_read_only={payload['d1_snapshot']['read_only']}")
    print(f"cockpit_status_d1_public_safe={payload['d1_snapshot']['public_safe']}")
    print(f"cockpit_status_d1_browser_authority={payload['d1_snapshot']['browser_authority']}")
    print(f"cockpit_status_d0_shell_status={payload['d0_shell']['status']}")
    print(f"cockpit_status_runtime_path={runtime_path}")
    print(f"cockpit_status_landing_path={landing_path}")
    print(f"cockpit_status_runtime_signature_path={runtime_signature_path}")
    print(f"cockpit_status_landing_signature_path={landing_signature_path}")
    print(f"cockpit_status_module_count={len(payload['modules'])}")
    print(f"cockpit_status_watching_count={len(payload['watching'])}")
    print(f"cockpit_status_pipeline_count={len(payload.get('source_pipeline_summary', []))}")
    print(f"cockpit_status_heartbeat_history_count={len(payload.get('source_heartbeat_history', []))}")
    print(f"cockpit_status_shadow_packet_count={len(payload['cognition'].get('shadow_packets', []))}")
    print(f"cockpit_status_hypothesis_count={len(payload['cognition'].get('hypotheses', []))}")
    print(f"cockpit_status_evidence_packet_count={len(payload['cognition'].get('evidence_packets', []))}")
    print(f"cockpit_status_paper_context_status={payload['cognition'].get('paper_account_context', {}).get('status')}")
    print(
        "cockpit_status_paper_context_connection_status="
        f"{payload['cognition'].get('paper_account_context', {}).get('connection_status')}"
    )
    print(f"cockpit_status_signal_integrity_status={payload['cognition'].get('signal_integrity', {}).get('status')}")
    print(f"cockpit_status_signal_integrity_review_count={len(payload['cognition'].get('signal_integrity_reviews', []))}")
    print(f"cockpit_status_risk_agent_status={payload.get('risk_agent', {}).get('status')}")
    print(f"cockpit_status_risk_agent_review_count={payload.get('risk_agent', {}).get('review_count')}")
    print(f"cockpit_status_worldview_status={payload['decision_philosophy'].get('status')}")
    print(f"cockpit_status_worldview_claim_count={payload['decision_philosophy'].get('claim_count')}")
    print(
        "cockpit_status_worldview_foundational_prior_count="
        f"{payload['decision_philosophy'].get('foundational_prior_count')}"
    )
    print(f"cockpit_status_forbidden_action_count={len(payload['forbidden_actions'])}")
    print(f"cockpit_status_tradingview_alert_status={payload['tradingview_alerts'].get('status')}")
    print(f"cockpit_status_tradingview_alert_count={payload['tradingview_alerts'].get('alert_count')}")
    print(
        "cockpit_status_tradingview_observed_signal_count="
        f"{len(payload['tradingview_alerts'].get('observed_signals', []))}"
    )
    print(f"cockpit_status_trade_candidate_count={len(payload['trade_layer']['candidates'])}")
    print(f"cockpit_status_blocked_trade_count={len(payload['trade_layer'].get('blocked', []))}")
    print(f"cockpit_status_trade_observed_signal_count={len(payload['trade_layer'].get('watching', []))}")
    print(f"cockpit_status_trade_store_status={payload['trade_layer'].get('store_status')}")
    print(f"cockpit_status_paper_mirror_status={payload['capital'].get('mirror_status')}")
    print(f"cockpit_status_paper_current_balance_gbp={payload['capital'].get('current_balance_gbp')}")
    print(f"cockpit_status_paper_open_position_count={len(payload['capital'].get('open_positions', []))}")
    print(f"cockpit_status_paper_closed_trade_count={len(payload['capital'].get('closed_trades', []))}")
    print(f"cockpit_status_paper_order_count={len(payload['capital'].get('orders', []))}")
    print(f"cockpit_status_paper_maturity_count={payload['capital'].get('maturity_closed_trade_count')}")
    print(f"cockpit_status_live_capital_enabled={payload['capital']['live_capital_enabled']}")
    print(f"cockpit_status_fund_manager_forum_status={payload['fund_manager_notes'].get('status')}")
    print(f"cockpit_status_fund_manager_comment_count={payload['fund_manager_notes'].get('comment_count')}")
    print(f"cockpit_status_fund_manager_recent_count={len(payload['fund_manager_notes'].get('recent_comments', []))}")
    print(f"cockpit_status_telegram_status={payload['communications']['telegram'].get('status')}")
    print(f"cockpit_status_telegram_pending_queue_count={payload['communications']['telegram'].get('pending_queue_count')}")
    print(f"cockpit_status_telegram_dry_run_message_count={payload['communications']['telegram'].get('dry_run_message_count')}")
    print(f"cockpit_status_live_bridge_status={payload['live_bridge'].get('status')}")
    print(f"cockpit_status_live_bridge_endpoint={payload['live_bridge'].get('endpoint')}")

    if payload["schema_version"] != COCKPIT_STATUS_SCHEMA_VERSION:
        print("cockpit_status_schema_mismatch=true")
        return 1
    if payload["d1_snapshot"].get("phase") != "D1":
        print("cockpit_status_d1_phase_mismatch=true")
        return 1
    if payload["d1_snapshot"].get("read_only") is not True:
        print("cockpit_status_d1_not_read_only=true")
        return 1
    if payload["d1_snapshot"].get("public_safe") is not True:
        print("cockpit_status_d1_not_public_safe=true")
        return 1
    if payload["d1_snapshot"].get("browser_authority") != "read_only":
        print("cockpit_status_d1_browser_authority_not_read_only=true")
        return 1
    if payload["d1_snapshot"].get("local_orchestrator_exposed") is not False:
        print("cockpit_status_d1_orchestrator_exposed=true")
        return 1
    if payload["d0_shell"]["status"] != "frozen":
        print("cockpit_status_d0_not_frozen=true")
        return 1
    live_bridge = payload["live_bridge"]
    missing_live_bridge_fields = sorted(LIVE_BRIDGE_REQUIRED_FIELDS - set(live_bridge))
    if missing_live_bridge_fields:
        print("cockpit_status_live_bridge_fields_missing=" + ",".join(missing_live_bridge_fields))
        return 1
    missing_publisher_fields = sorted(LIVE_BRIDGE_PUBLISHER_REQUIRED_FIELDS - set(live_bridge.get("publisher", {})))
    if missing_publisher_fields:
        print("cockpit_status_live_bridge_publisher_fields_missing=" + ",".join(missing_publisher_fields))
        return 1
    if live_bridge.get("phase") != "D9":
        print("cockpit_status_live_bridge_phase_mismatch=true")
        return 1
    if live_bridge.get("status") != "read_only_ready":
        print("cockpit_status_live_bridge_not_ready=true")
        return 1
    if live_bridge.get("endpoint") != "/api/cockpit-status":
        print("cockpit_status_live_bridge_endpoint_mismatch=true")
        return 1
    if live_bridge.get("static_fallback") != "/status/cockpit-status.json":
        print("cockpit_status_live_bridge_fallback_mismatch=true")
        return 1
    if live_bridge.get("allowed_methods") != ["GET", "HEAD"]:
        print("cockpit_status_live_bridge_allowed_methods_mismatch=true")
        return 1
    for method in {"POST", "PUT", "PATCH", "DELETE"}:
        if method not in live_bridge.get("forbidden_methods", []):
            print(f"cockpit_status_live_bridge_forbidden_method_missing={method}")
            return 1
    if live_bridge.get("read_only") is not True:
        print("cockpit_status_live_bridge_not_read_only=true")
        return 1
    if live_bridge.get("browser_authority") != "read_only":
        print("cockpit_status_live_bridge_browser_authority_mismatch=true")
        return 1
    if live_bridge.get("write_authority") is not False:
        print("cockpit_status_live_bridge_write_authority_enabled=true")
        return 1
    if live_bridge.get("broker_write_route") is not False:
        print("cockpit_status_live_bridge_broker_write_route_enabled=true")
        return 1
    if live_bridge.get("local_orchestrator_exposed") is not False:
        print("cockpit_status_live_bridge_orchestrator_exposed=true")
        return 1
    if "supabase" not in live_bridge.get("authentication", ""):
        print("cockpit_status_live_bridge_auth_missing=true")
        return 1
    if live_bridge.get("rate_limit_per_minute", 0) <= 0:
        print("cockpit_status_live_bridge_rate_limit_missing=true")
        return 1
    for check in {"auth_required", "rate_limit_enforced", "method_block_enforced", "snapshot_fallback_available", "broker_write_route_absent"}:
        if check not in live_bridge.get("health_checks", []):
            print(f"cockpit_status_live_bridge_health_check_missing={check}")
            return 1
    if "public-safe cockpit status snapshot only" not in live_bridge.get("boundary", ""):
        print("cockpit_status_live_bridge_boundary_weak=true")
        return 1
    if live_bridge.get("publisher", {}).get("signature_file") != "status/cockpit-status.signature.json":
        print("cockpit_status_live_bridge_signature_file_mismatch=true")
        return 1
    missing_signature_fields = sorted(LIVE_BRIDGE_SIGNATURE_REQUIRED_FIELDS - set(runtime_signature))
    if missing_signature_fields:
        print("cockpit_status_signature_fields_missing=" + ",".join(missing_signature_fields))
        return 1
    if runtime_signature.get("payload_file") != "cockpit-status.json":
        print("cockpit_status_signature_payload_file_mismatch=true")
        return 1
    if runtime_signature.get("payload_schema_version") != payload["schema_version"]:
        print("cockpit_status_signature_schema_mismatch=true")
        return 1
    if runtime_signature.get("payload_generated_at") != payload["generated_at"]:
        print("cockpit_status_signature_generated_at_mismatch=true")
        return 1
    if runtime_signature.get("read_only") is not True or runtime_signature.get("broker_write_route") is not False:
        print("cockpit_status_signature_boundary_mismatch=true")
        return 1
    if len(runtime_signature.get("signature", "")) != 64:
        print("cockpit_status_signature_length_mismatch=true")
        return 1
    communications = payload["communications"]
    missing_communications_fields = sorted(COMMUNICATIONS_REQUIRED_FIELDS - set(communications))
    if missing_communications_fields:
        print("cockpit_status_communications_fields_missing=" + ",".join(missing_communications_fields))
        return 1
    telegram = communications["telegram"]
    missing_telegram_fields = sorted(TELEGRAM_COMMUNICATIONS_REQUIRED_FIELDS - set(telegram))
    if missing_telegram_fields:
        print("cockpit_status_telegram_fields_missing=" + ",".join(missing_telegram_fields))
        return 1
    if telegram.get("status") != "dry_run":
        print("cockpit_status_telegram_not_dry_run=true")
        return 1
    if telegram.get("mode") != "dry_run":
        print("cockpit_status_telegram_mode_not_dry_run=true")
        return 1
    if telegram.get("send_gate") != "disabled":
        print("cockpit_status_telegram_send_gate_enabled=true")
        return 1
    if telegram.get("member_count", 0) < 5:
        print("cockpit_status_telegram_members_missing=true")
        return 1
    if telegram.get("pending_queue_count", 0) < 4:
        print("cockpit_status_telegram_queue_missing=true")
        return 1
    if telegram.get("dry_run_message_count", 0) < 4:
        print("cockpit_status_telegram_dry_run_messages_missing=true")
        return 1
    for message_class in {"trade_candidate", "blocked_trade", "insight_digest", "source_degraded"}:
        if message_class not in telegram.get("active_message_classes", []):
            print(f"cockpit_status_telegram_message_class_missing={message_class}")
            return 1
    if "outbound-only" not in telegram.get("boundary", ""):
        print("cockpit_status_telegram_boundary_weak=true")
        return 1
    for phrase in ("place", "approve", "reject", "modify", "close", "resize"):
        if phrase not in telegram.get("boundary", ""):
            print(f"cockpit_status_telegram_boundary_missing={phrase}")
            return 1
    for message in telegram.get("recent_messages", []):
        missing_message_fields = sorted(TELEGRAM_MESSAGE_REQUIRED_FIELDS - set(message))
        if missing_message_fields:
            print(
                "cockpit_status_telegram_message_fields_missing="
                f"{message.get('message_id', 'unknown')}:{','.join(missing_message_fields)}"
            )
            return 1
        if message.get("send_allowed") is not False:
            print("cockpit_status_telegram_message_send_allowed=true")
            return 1
        if "body" in message:
            print("cockpit_status_telegram_public_body_leaked=true")
            return 1
        if "chat_id" in message or "handle" in message:
            print("cockpit_status_telegram_identifier_leaked=true")
            return 1
    fund_manager_notes = payload["fund_manager_notes"]
    missing_fund_manager_fields = sorted(FUND_MANAGER_NOTES_REQUIRED_FIELDS - set(fund_manager_notes))
    if missing_fund_manager_fields:
        print("cockpit_status_fund_manager_notes_fields_missing=" + ",".join(missing_fund_manager_fields))
        return 1
    if fund_manager_notes.get("status") != "ok":
        print("cockpit_status_fund_manager_notes_not_ok=true")
        return 1
    if fund_manager_notes.get("supabase_table") != "fund_manager_comments":
        print("cockpit_status_fund_manager_supabase_table_mismatch=true")
        return 1
    if fund_manager_notes.get("browser_write_scope") != "comments_only":
        print("cockpit_status_fund_manager_browser_write_scope_mismatch=true")
        return 1
    if fund_manager_notes.get("local_event_log_export") != "accepted_or_implemented_only":
        print("cockpit_status_fund_manager_event_log_export_mismatch=true")
        return 1
    if fund_manager_notes.get("visibility") != "founding_fund_managers":
        print("cockpit_status_fund_manager_visibility_mismatch=true")
        return 1
    if "governance notes only" not in fund_manager_notes.get("boundary", ""):
        print("cockpit_status_fund_manager_boundary_weak=true")
        return 1
    if "cannot approve trades" not in fund_manager_notes.get("boundary", ""):
        print("cockpit_status_fund_manager_trade_approval_unblocked=true")
        return 1
    for target_type in {"module", "source", "signal", "trade_candidate", "postmortem"}:
        if target_type not in fund_manager_notes.get("allowed_target_types", []):
            print(f"cockpit_status_fund_manager_target_type_missing={target_type}")
            return 1
    for status in {"suggestion", "accepted", "rejected", "implemented"}:
        if status not in fund_manager_notes.get("allowed_statuses", []):
            print(f"cockpit_status_fund_manager_status_missing={status}")
            return 1
    if fund_manager_notes.get("comment_count", 0) < 1:
        print("cockpit_status_fund_manager_comment_missing=true")
        return 1
    if not fund_manager_notes.get("recent_comments"):
        print("cockpit_status_fund_manager_recent_missing=true")
        return 1
    for comment in fund_manager_notes.get("recent_comments", []):
        missing_comment_fields = sorted(FUND_MANAGER_COMMENT_REQUIRED_FIELDS - set(comment))
        if missing_comment_fields:
            print(
                "cockpit_status_fund_manager_comment_fields_missing="
                f"{comment.get('comment_id', 'unknown')}:{','.join(missing_comment_fields)}"
            )
            return 1
        if "author_email" in comment:
            print("cockpit_status_fund_manager_author_email_leaked=true")
            return 1
        if comment.get("visibility") != "founding_fund_managers":
            print("cockpit_status_fund_manager_comment_visibility_mismatch=true")
            return 1
    if not any(
        comment.get("target_type") == "module" and comment.get("target_key") == "trade_layer"
        for comment in fund_manager_notes.get("recent_comments", [])
    ):
        print("cockpit_status_fund_manager_trade_layer_comment_missing=true")
        return 1
    capital = payload["capital"]
    missing_capital_fields = sorted(CAPITAL_REQUIRED_FIELDS - set(capital))
    if missing_capital_fields:
        print("cockpit_status_capital_fields_missing=" + ",".join(missing_capital_fields))
        return 1
    if capital["live_capital_enabled"] is not False:
        print("cockpit_status_live_capital_not_blocked=true")
        return 1
    if capital.get("write_authority") is not False:
        print("cockpit_status_paper_write_authority_enabled=true")
        return 1
    if capital.get("mirror_status") != "ok":
        print("cockpit_status_paper_mirror_not_ok=true")
        return 1
    if capital.get("account_scope") != "first_release_gbp_1000_trial":
        print("cockpit_status_paper_account_scope_mismatch=true")
        return 1
    if capital.get("connection_status") not in {"local_mirror_not_broker_connected", "alpaca_paper_readonly_connected"}:
        print("cockpit_status_paper_connection_status_mismatch=true")
        return 1
    if not any(
        phrase in capital.get("boundary", "")
        for phrase in ("No broker connection", "read-only", "No broker write path")
    ):
        print("cockpit_status_paper_boundary_weak=true")
        return 1
    if capital.get("starting_balance_gbp") != 1000:
        print("cockpit_status_paper_starting_balance_mismatch=true")
        return 1
    if capital.get("connection_status") == "local_mirror_not_broker_connected":
        if capital.get("current_balance_gbp") != capital.get("starting_balance_gbp"):
            print("cockpit_status_paper_current_balance_mismatch=true")
            return 1
        if capital.get("cash_gbp") != capital.get("current_balance_gbp"):
            print("cockpit_status_paper_cash_mismatch=true")
            return 1
        if capital.get("equity_gbp") != capital.get("current_balance_gbp"):
            print("cockpit_status_paper_equity_mismatch=true")
            return 1
        if capital.get("realized_pnl_gbp") != 0 or capital.get("unrealized_pnl_gbp") != 0:
            print("cockpit_status_paper_pnl_not_zero=true")
            return 1
        if capital.get("drawdown_pct") != 0 or capital.get("max_drawdown_pct") != 0:
            print("cockpit_status_paper_drawdown_not_zero=true")
            return 1
    if capital.get("maturity_closed_trade_target") != MATURITY_CLOSED_TRADE_TARGET:
        print("cockpit_status_paper_maturity_target_mismatch=true")
        return 1
    if capital.get("open_position_count") != len(capital.get("open_positions", [])):
        print("cockpit_status_paper_open_position_count_mismatch=true")
        return 1
    if capital.get("closed_trade_count") != len(capital.get("closed_trades", [])):
        print("cockpit_status_paper_closed_trade_count_mismatch=true")
        return 1
    if capital.get("order_count") != len(capital.get("orders", [])):
        print("cockpit_status_paper_order_count_mismatch=true")
        return 1
    if capital.get("open_order_count") != sum(
        1 for order in capital.get("orders", []) if order.get("status") in {"new", "accepted", "partially_filled"}
    ):
        print("cockpit_status_paper_open_order_count_mismatch=true")
        return 1
    if capital.get("postmortem_due_count") != len(capital.get("postmortems_due", [])):
        print("cockpit_status_paper_postmortem_due_count_mismatch=true")
        return 1
    if capital.get("postmortem_complete_count") != len(capital.get("postmortems_complete", [])):
        print("cockpit_status_paper_postmortem_complete_count_mismatch=true")
        return 1
    if capital.get("maturity_closed_trade_count") != len(capital.get("closed_trades", [])):
        print("cockpit_status_paper_maturity_count_mismatch=true")
        return 1
    if not capital.get("equity_curve"):
        print("cockpit_status_paper_equity_curve_missing=true")
        return 1
    for point in capital.get("equity_curve", []):
        missing_fields = sorted(EQUITY_POINT_REQUIRED_FIELDS - set(point))
        if missing_fields:
            print("cockpit_status_equity_point_fields_missing=" + ",".join(missing_fields))
            return 1
    for position in capital.get("open_positions", []):
        missing_fields = sorted(PAPER_POSITION_REQUIRED_FIELDS - set(position))
        if missing_fields:
            print(f"cockpit_status_paper_position_fields_missing={position.get('position_id', 'unknown')}:{','.join(missing_fields)}")
            return 1
        if position.get("status") not in {"open_position", "exit_planned"}:
            print("cockpit_status_paper_position_status_invalid=true")
            return 1
    for trade in capital.get("closed_trades", []):
        missing_fields = sorted(CLOSED_PAPER_TRADE_REQUIRED_FIELDS - set(trade))
        if missing_fields:
            print(f"cockpit_status_closed_paper_trade_fields_missing={trade.get('trade_id', 'unknown')}:{','.join(missing_fields)}")
            return 1
        if trade.get("postmortem_status") not in {"postmortem_due", "postmortem_complete"}:
            print("cockpit_status_closed_paper_trade_postmortem_invalid=true")
            return 1
    for order in capital.get("orders", []):
        missing_fields = sorted(PAPER_ORDER_REQUIRED_FIELDS - set(order))
        if missing_fields:
            print(f"cockpit_status_paper_order_fields_missing={order.get('order_id', 'unknown')}:{','.join(missing_fields)}")
            return 1
        if order.get("execution_allowed") is not False or order.get("paper_order_allowed") is not False:
            print("cockpit_status_paper_order_authority_enabled=true")
            return 1
    if len(payload["watching"]) < 1:
        print("cockpit_status_no_sources=true")
        return 1
    if len(payload["watching"]) < EXPECTED_SOURCE_COUNT + 1:
        print("cockpit_status_source_count_below_expected=true")
        return 1
    for source in payload["watching"]:
        missing_fields = sorted(WATCHING_REQUIRED_FIELDS - set(source))
        if missing_fields:
            print(f"cockpit_status_source_fields_missing={source.get('source_key', 'unknown')}:{','.join(missing_fields)}")
            return 1
    if not any(source.get("source_key") == "tradingview_paid_alerts" for source in payload["watching"]):
        print("cockpit_status_watching_tradingview_missing=true")
        return 1
    if not all(source.get("can_influence_signals") is False for source in payload["watching"]):
        print("cockpit_status_source_signal_influence_unblocked=true")
        return 1
    if len(payload.get("source_pipeline_summary", [])) < 1:
        print("cockpit_status_no_pipeline_summary=true")
        return 1
    if len(payload.get("source_pipeline_summary", [])) != 5:
        print("cockpit_status_pipeline_count_mismatch=true")
        return 1
    if sum(item.get("source_count", 0) for item in payload["source_pipeline_summary"]) != len(payload["watching"]):
        print("cockpit_status_pipeline_source_total_mismatch=true")
        return 1
    if len(payload["modules"]) < 1:
        print("cockpit_status_no_modules=true")
        return 1
    philosophy = payload["decision_philosophy"]
    if philosophy.get("status") != "ok":
        print("cockpit_status_worldview_not_ok=true")
        return 1
    if philosophy.get("corpus") != "how-the-world-works":
        print("cockpit_status_worldview_corpus_mismatch=true")
        return 1
    if philosophy.get("claim_count", 0) < 1:
        print("cockpit_status_worldview_claims_missing=true")
        return 1
    if philosophy.get("foundational_prior_count", 0) < 1:
        print("cockpit_status_worldview_priors_missing=true")
        return 1
    if not philosophy.get("decision_chain"):
        print("cockpit_status_worldview_decision_chain_missing=true")
        return 1
    if not philosophy.get("active_lenses"):
        print("cockpit_status_worldview_lenses_missing=true")
        return 1
    if "not factual evidence" not in philosophy.get("boundary", ""):
        print("cockpit_status_worldview_boundary_weak=true")
        return 1

    cognition = payload["cognition"]
    if cognition.get("status") not in {"shadow_ready", "ok", "degraded"}:
        print("cockpit_status_cognition_status_invalid=true")
        return 1
    if not cognition.get("current_focus"):
        print("cockpit_status_current_focus_missing=true")
        return 1
    paper_context = cognition.get("paper_account_context", {})
    missing_paper_context_fields = sorted(PAPER_ACCOUNT_CONTEXT_REQUIRED_FIELDS - set(paper_context))
    if missing_paper_context_fields:
        print("cockpit_status_paper_context_fields_missing=" + ",".join(missing_paper_context_fields))
        return 1
    if paper_context.get("execution_allowed") is not False:
        print("cockpit_status_paper_context_execution_allowed=true")
        return 1
    if paper_context.get("paper_order_allowed") is not False:
        print("cockpit_status_paper_context_paper_order_allowed=true")
        return 1
    if paper_context.get("write_authority") is not False:
        print("cockpit_status_paper_context_write_authority_enabled=true")
        return 1
    if paper_context.get("live_capital_enabled") is not False:
        print("cockpit_status_paper_context_live_capital_enabled=true")
        return 1
    if "read-only" not in paper_context.get("boundary", ""):
        print("cockpit_status_paper_context_boundary_weak=true")
        return 1
    signal_integrity = cognition.get("signal_integrity", {})
    missing_signal_integrity_fields = sorted(SIGNAL_INTEGRITY_REQUIRED_FIELDS - set(signal_integrity))
    if missing_signal_integrity_fields:
        print("cockpit_status_signal_integrity_fields_missing=" + ",".join(missing_signal_integrity_fields))
        return 1
    if signal_integrity.get("status") != "ok":
        print("cockpit_status_signal_integrity_not_ok=true")
        return 1
    if signal_integrity.get("execution_allowed_count") != 0:
        print("cockpit_status_signal_integrity_execution_allowed=true")
        return 1
    if signal_integrity.get("paper_order_allowed_count") != 0:
        print("cockpit_status_signal_integrity_paper_order_allowed=true")
        return 1
    if signal_integrity.get("trade_candidate_created_count") != 0:
        print("cockpit_status_signal_integrity_created_trade_candidate=true")
        return 1
    if "cannot create candidates or orders" not in signal_integrity.get("boundary", ""):
        print("cockpit_status_signal_integrity_boundary_weak=true")
        return 1
    if not isinstance(cognition.get("signal_integrity_reviews"), list):
        print("cockpit_status_signal_integrity_reviews_missing=true")
        return 1
    if not cognition.get("signal_integrity_reviews"):
        print("cockpit_status_signal_integrity_reviews_empty=true")
        return 1
    for review in cognition.get("signal_integrity_reviews", []):
        missing_fields = sorted(SIGNAL_INTEGRITY_REVIEW_REQUIRED_FIELDS - set(review))
        if missing_fields:
            print(
                "cockpit_status_signal_integrity_review_fields_missing="
                f"{review.get('review_id', 'unknown')}:{','.join(missing_fields)}"
            )
            return 1
        if review.get("execution_allowed") is not False:
            print("cockpit_status_signal_integrity_review_execution_allowed=true")
            return 1
        if review.get("paper_order_allowed") is not False:
            print("cockpit_status_signal_integrity_review_paper_order_allowed=true")
            return 1
        if review.get("trade_candidate_created") is not False:
            print("cockpit_status_signal_integrity_review_created_trade_candidate=true")
            return 1
        if "cannot approve" not in review.get("boundary", ""):
            print("cockpit_status_signal_integrity_review_boundary_weak=true")
            return 1
    if not isinstance(cognition.get("shadow_packets"), list):
        print("cockpit_status_shadow_packets_missing=true")
        return 1
    if not cognition.get("shadow_packets"):
        print("cockpit_status_shadow_packets_empty=true")
        return 1
    for packet in cognition.get("shadow_packets", []):
        missing_fields = sorted(SHADOW_PACKET_REQUIRED_FIELDS - set(packet))
        if missing_fields:
            print(f"cockpit_status_shadow_packet_fields_missing={packet.get('packet_id', 'unknown')}:{','.join(missing_fields)}")
            return 1
        if "No signal, risk decision, or execution authority" not in packet.get("boundary", ""):
            print("cockpit_status_shadow_packet_boundary_weak=true")
            return 1
    if not isinstance(cognition.get("local_research_assessments"), list):
        print("cockpit_status_local_research_missing=true")
        return 1
    if not cognition.get("local_research_assessments"):
        print("cockpit_status_local_research_empty=true")
        return 1
    for assessment in cognition.get("local_research_assessments", []):
        missing_fields = sorted(LOCAL_RESEARCH_REQUIRED_FIELDS - set(assessment))
        if missing_fields:
            print(
                "cockpit_status_local_research_fields_missing="
                f"{assessment.get('assessment_id', 'unknown')}:{','.join(missing_fields)}"
            )
            return 1
        if assessment.get("execution_allowed") is not False:
            print("cockpit_status_local_research_execution_allowed=true")
            return 1
        if assessment.get("paper_order_allowed") is not False:
            print("cockpit_status_local_research_paper_order_allowed=true")
            return 1
    if not isinstance(cognition.get("hypotheses"), list) or not cognition["hypotheses"]:
        print("cockpit_status_hypotheses_missing=true")
        return 1
    if not isinstance(cognition.get("evidence_packets"), list) or not cognition["evidence_packets"]:
        print("cockpit_status_evidence_packets_missing=true")
        return 1
    if not cognition.get("analysis_timeline"):
        print("cockpit_status_analysis_timeline_missing=true")
        return 1
    if "trade layer not reached" not in cognition.get("analysis_timeline", []):
        print("cockpit_status_analysis_timeline_trade_boundary_missing=true")
        return 1
    if "paper account mirror context" not in cognition.get("analysis_timeline", []):
        print("cockpit_status_analysis_timeline_paper_context_missing=true")
        return 1
    if "signal integrity review" not in cognition.get("analysis_timeline", []):
        print("cockpit_status_analysis_timeline_signal_integrity_missing=true")
        return 1
    if not cognition.get("blocked_reasons"):
        print("cockpit_status_blocked_reasons_missing=true")
        return 1
    if "shadow_only_pending_signal_integrity_gate" not in cognition.get("blocked_reasons", []):
        print("cockpit_status_signal_integrity_pending_block_missing=true")
        return 1
    if "signal_integrity_gate_hold_or_block" not in cognition.get("blocked_reasons", []):
        print("cockpit_status_signal_integrity_hold_block_missing=true")
        return 1
    if "paper_account_context_read_only" not in cognition.get("blocked_reasons", []):
        print("cockpit_status_paper_context_block_missing=true")
        return 1
    if "signal_integrity_gate_requires_risk_agent" not in cognition.get("blocked_reasons", []):
        print("cockpit_status_signal_integrity_risk_block_missing=true")
        return 1
    for packet in cognition.get("strategy_lead_packets", []):
        strategy_context = packet.get("paper_account_context", {})
        missing_strategy_context_fields = sorted(PAPER_ACCOUNT_CONTEXT_REQUIRED_FIELDS - set(strategy_context))
        if missing_strategy_context_fields:
            print(
                "cockpit_status_strategy_paper_context_fields_missing="
                f"{packet.get('packet_id', 'unknown')}:{','.join(missing_strategy_context_fields)}"
            )
            return 1
        if strategy_context.get("execution_allowed") is not False or strategy_context.get("paper_order_allowed") is not False:
            print("cockpit_status_strategy_paper_context_authority_enabled=true")
            return 1
    if not isinstance(cognition.get("model_activity"), list) or not cognition["model_activity"]:
        print("cockpit_status_model_activity_missing=true")
        return 1
    model_roles = {model.get("role") for model in cognition.get("model_activity", [])}
    if not MODEL_ACTIVITY_ROLES.issubset(model_roles):
        print("cockpit_status_model_activity_roles_missing=true")
        return 1
    if any(model.get("authority") != "non_executable" for model in cognition.get("model_activity", [])):
        print("cockpit_status_model_activity_executable=true")
        return 1

    risk_agent = payload.get("risk_agent", {})
    missing_risk_agent_fields = sorted(RISK_AGENT_REQUIRED_FIELDS - set(risk_agent))
    if missing_risk_agent_fields:
        print("cockpit_status_risk_agent_fields_missing=" + ",".join(missing_risk_agent_fields))
        return 1
    if risk_agent.get("status") != "ok":
        print("cockpit_status_risk_agent_not_ok=true")
        return 1
    if risk_agent.get("authority") != "read_only_policy_router":
        print("cockpit_status_risk_agent_authority_mismatch=true")
        return 1
    if risk_agent.get("execution_allowed_count") != 0:
        print("cockpit_status_risk_agent_execution_allowed_not_zero=true")
        return 1
    if risk_agent.get("paper_order_allowed_count") != 0:
        print("cockpit_status_risk_agent_paper_order_allowed_not_zero=true")
        return 1
    if risk_agent.get("order_created_count") != 0:
        print("cockpit_status_risk_agent_order_created_not_zero=true")
        return 1
    if risk_agent.get("broker_write_allowed_count") != 0:
        print("cockpit_status_risk_agent_broker_write_allowed_not_zero=true")
        return 1
    if "cannot approve risk" not in risk_agent.get("boundary", ""):
        print("cockpit_status_risk_agent_boundary_weak=true")
        return 1
    if not isinstance(risk_agent.get("reviews"), list) or not risk_agent["reviews"]:
        print("cockpit_status_risk_agent_reviews_missing=true")
        return 1
    for review in risk_agent.get("reviews", []):
        missing_fields = sorted(RISK_POLICY_REVIEW_REQUIRED_FIELDS - set(review))
        if missing_fields:
            print(
                "cockpit_status_risk_policy_review_fields_missing="
                f"{review.get('review_id', 'unknown')}:{','.join(missing_fields)}"
            )
            return 1
        if review.get("execution_allowed") is not False:
            print("cockpit_status_risk_policy_execution_allowed=true")
            return 1
        if review.get("paper_order_allowed") is not False:
            print("cockpit_status_risk_policy_paper_order_allowed=true")
            return 1
        if review.get("order_created") is not False:
            print("cockpit_status_risk_policy_order_created=true")
            return 1
        if review.get("broker_write_allowed") is not False:
            print("cockpit_status_risk_policy_broker_write_allowed=true")
            return 1
        if not 0 <= float(review.get("policy_score", -1)) <= 1:
            print("cockpit_status_risk_policy_score_bad=true")
            return 1
        missing_checks = sorted(RISK_POLICY_REQUIRED_CHECKS - set(review.get("checks", {})))
        if missing_checks:
            print(
                "cockpit_status_risk_policy_checks_missing="
                f"{review.get('review_id', 'unknown')}:{','.join(missing_checks)}"
            )
            return 1
        if "cannot approve risk" not in review.get("boundary", ""):
            print("cockpit_status_risk_policy_boundary_weak=true")
            return 1

    tradingview = payload["tradingview_alerts"]
    missing_tradingview_fields = sorted(TRADINGVIEW_SUMMARY_REQUIRED_FIELDS - set(tradingview))
    if missing_tradingview_fields:
        print("cockpit_status_tradingview_fields_missing=" + ",".join(missing_tradingview_fields))
        return 1
    if tradingview.get("status") != "ok":
        print("cockpit_status_tradingview_alerts_not_ok=true")
        return 1
    if tradingview.get("receiver_status") != "local_contract_only":
        print("cockpit_status_tradingview_receiver_status_mismatch=true")
        return 1
    if tradingview.get("duplicate_protection") != "dedupe_key_sha256":
        print("cockpit_status_tradingview_duplicate_protection_mismatch=true")
        return 1
    if "observed signals only" not in tradingview.get("boundary", ""):
        print("cockpit_status_tradingview_boundary_weak=true")
        return 1
    if tradingview.get("alert_count") != len(tradingview.get("observed_signals", [])):
        print("cockpit_status_tradingview_alert_count_mismatch=true")
        return 1
    if len(tradingview.get("observed_signals", [])) < 1:
        print("cockpit_status_tradingview_observed_signal_missing=true")
        return 1
    if tradingview.get("execution_allowed_count") != 0:
        print("cockpit_status_tradingview_execution_allowed_not_zero=true")
        return 1
    if tradingview.get("paper_order_allowed_count") != 0:
        print("cockpit_status_tradingview_paper_order_allowed_not_zero=true")
        return 1
    if tradingview.get("trade_candidate_created_count") != 0:
        print("cockpit_status_tradingview_trade_candidate_created=true")
        return 1
    for observed in tradingview.get("observed_signals", []):
        missing_fields = sorted(OBSERVED_SIGNAL_REQUIRED_FIELDS - set(observed))
        if missing_fields:
            print(
                "cockpit_status_tradingview_observed_fields_missing="
                f"{observed.get('alert_id', 'unknown')}:{','.join(missing_fields)}"
            )
            return 1
        if observed.get("status") != "observed_signal":
            print("cockpit_status_tradingview_observed_wrong_status=true")
            return 1
        if observed.get("execution_allowed") is not False:
            print("cockpit_status_tradingview_observed_execution_allowed=true")
            return 1
        if observed.get("paper_order_allowed") is not False:
            print("cockpit_status_tradingview_observed_paper_order_allowed=true")
            return 1
        if observed.get("trade_candidate_created") is not False:
            print("cockpit_status_tradingview_observed_created_candidate=true")
            return 1
        if "cannot create a trade candidate, paper order, or broker action" not in observed.get("boundary", ""):
            print("cockpit_status_tradingview_observed_boundary_weak=true")
            return 1

    for packet in cognition.get("evidence_packets", []):
        missing_fields = sorted(EVIDENCE_PACKET_REQUIRED_FIELDS - set(packet))
        if missing_fields:
            print(f"cockpit_status_evidence_packet_fields_missing={packet.get('trail_id', 'unknown')}:{','.join(missing_fields)}")
            return 1
        if "items" not in packet:
            print("cockpit_status_evidence_items_missing=true")
            return 1
        if not packet.get("items"):
            print("cockpit_status_evidence_items_empty=true")
            return 1
        for item in packet.get("items", []):
            if "raw_ref" in item:
                print("cockpit_status_evidence_raw_ref_leaked=true")
                return 1

    for hypothesis in cognition.get("hypotheses", []):
        missing_fields = sorted(HYPOTHESIS_REQUIRED_FIELDS - set(hypothesis))
        if missing_fields:
            print(f"cockpit_status_hypothesis_fields_missing={hypothesis.get('signal_id', 'unknown')}:{','.join(missing_fields)}")
            return 1
        if hypothesis.get("execution_allowed") is not False:
            print("cockpit_status_shadow_hypothesis_execution_allowed=true")
            return 1
        if not hypothesis.get("blocked_reason"):
            print("cockpit_status_shadow_hypothesis_block_missing=true")
            return 1
        if hypothesis.get("blocked_reason") not in {
            "shadow_only_pending_signal_integrity_gate",
            "signal_integrity_gate_hold_or_block",
            "signal_integrity_gate_requires_risk_agent",
        }:
            print("cockpit_status_shadow_hypothesis_wrong_block=true")
            return 1
        if hypothesis.get("evidence_packet_id") != hypothesis.get("signal_id"):
            print("cockpit_status_hypothesis_evidence_link_mismatch=true")
            return 1

    trade_layer = payload["trade_layer"]
    if trade_layer.get("store_status") not in {"ok", "degraded"}:
        print("cockpit_status_trade_store_status_missing=true")
        return 1
    trade_summary = trade_layer.get("summary", {})
    if trade_summary.get("status") != "ok":
        print("cockpit_status_trade_summary_not_ok=true")
        return 1
    if "No broker order path exists" not in trade_layer.get("boundary", ""):
        print("cockpit_status_trade_layer_boundary_weak=true")
        return 1
    if "No broker order path exists" not in trade_summary.get("boundary", ""):
        print("cockpit_status_trade_summary_boundary_weak=true")
        return 1
    if trade_summary.get("candidate_count", 0) < 1:
        print("cockpit_status_trade_candidate_missing=true")
        return 1
    if trade_summary.get("blocked_count", 0) < 1:
        print("cockpit_status_trade_blocked_missing=true")
        return 1
    if trade_summary.get("execution_allowed_count") != 0:
        print("cockpit_status_trade_execution_allowed_not_zero=true")
        return 1
    if trade_summary.get("paper_order_allowed_count") != 0:
        print("cockpit_status_trade_paper_order_allowed_not_zero=true")
        return 1
    if trade_summary.get("candidate_count") != len(trade_layer.get("candidates", [])):
        print("cockpit_status_trade_candidate_count_mismatch=true")
        return 1
    if trade_summary.get("blocked_count") != len(trade_layer.get("blocked", [])):
        print("cockpit_status_trade_blocked_count_mismatch=true")
        return 1
    if trade_summary.get("observed_signal_count") != len(trade_layer.get("watching", [])):
        print("cockpit_status_trade_observed_count_mismatch=true")
        return 1
    public_intents = (
        trade_layer.get("watching", [])
        + trade_layer.get("candidates", [])
        + trade_layer.get("blocked", [])
        + trade_layer.get("staged_orders", [])
        + trade_layer.get("submitted_orders", [])
        + trade_layer.get("open_positions", [])
        + trade_layer.get("closed_trades", [])
        + trade_layer.get("postmortems_due", [])
        + trade_layer.get("postmortems_complete", [])
    )
    if not any(intent.get("source_type") == "tradingview_paid_alert" for intent in trade_layer.get("watching", [])):
        print("cockpit_status_tradingview_not_in_trade_watching=true")
        return 1
    for observed in trade_layer.get("watching", []):
        if observed.get("source_type") == "tradingview_paid_alert":
            missing_fields = sorted(OBSERVED_SIGNAL_REQUIRED_FIELDS - set(observed))
            if missing_fields:
                print(
                    "cockpit_status_observed_signal_fields_missing="
                    f"{observed.get('alert_id', 'unknown')}:{','.join(missing_fields)}"
                )
                return 1
            if observed.get("trade_candidate_created") is not False:
                print("cockpit_status_observed_signal_created_candidate=true")
                return 1
    for intent in trade_layer.get("candidates", []) + trade_layer.get("blocked", []):
        missing_fields = sorted(TRADE_INTENT_REQUIRED_FIELDS - set(intent))
        if missing_fields:
            print(f"cockpit_status_trade_intent_fields_missing={intent.get('intent_id', 'unknown')}:{','.join(missing_fields)}")
            return 1
        if "no broker route exists" not in intent.get("boundary", "").lower():
            print("cockpit_status_trade_intent_boundary_weak=true")
            return 1
        if not intent.get("akber_filter"):
            print("cockpit_status_trade_intent_akber_filter_missing=true")
            return 1
        if not intent.get("risk_checks"):
            print("cockpit_status_trade_intent_risk_checks_missing=true")
            return 1
        if intent.get("risk_size_gbp") != 0 or intent.get("risk_size_pct") != 0:
            print("cockpit_status_trade_intent_risk_nonzero=true")
            return 1
        if intent.get("status") == "candidate" and intent.get("blocked_reason") not in {"", None}:
            print("cockpit_status_candidate_has_blocked_reason=true")
            return 1
        if intent.get("status") == "blocked" and not intent.get("blocked_reason"):
            print("cockpit_status_blocked_trade_reason_missing=true")
            return 1
    for intent in public_intents:
        if intent.get("source_type") == "tradingview_paid_alert":
            if intent.get("status") != "observed_signal":
                print("cockpit_status_tradingview_wrong_state=true")
                return 1
            if intent.get("execution_allowed") is not False:
                print("cockpit_status_tradingview_execution_allowed=true")
                return 1
            if intent.get("paper_order_allowed") is not False:
                print("cockpit_status_tradingview_paper_order_allowed=true")
                return 1
        if intent.get("status") in {"candidate", "blocked"} and intent.get("execution_allowed") is not False:
            print("cockpit_status_trade_intent_execution_allowed=true")
            return 1
        if intent.get("status") in {"candidate", "blocked"} and intent.get("paper_order_allowed") is not False:
            print("cockpit_status_trade_intent_paper_order_allowed=true")
            return 1

    print("cockpit_status_boundary=" + payload["boundary"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
