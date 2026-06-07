#!/usr/bin/env python3
# ruff: noqa: E402
"""Validate the public-safe cockpit status contract."""

from __future__ import annotations

import json
import re
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
from orchestrator.release_contract import PAPER_ACCOUNT_BALANCE_GBP, PAPER_ACCOUNT_SCOPE  # noqa: E402
from orchestrator.paperops_active_paper_trading_automation import (  # noqa: E402
    PAPEROPS_ACTIVE_AUTOMATION_READY_STATUSES,
)
from orchestrator.paper_authority_reconciliation import (  # noqa: E402
    PAPER_AUTHORITY_RECONCILIATION_PUBLIC_FIELDS,
    validate_paper_authority_reconciliation,
)
from orchestrator.paper_lifecycle_portfolio_postmortem import (  # noqa: E402
    RS6_PUBLIC_STATUS_FIELDS,
)
from orchestrator.operator_inbox import (  # noqa: E402
    PUBLIC_STATUS_FIELDS as RS7_OPERATOR_INBOX_PUBLIC_FIELDS,
)
from orchestrator.paperops_cockpit_notification_upgrade import (  # noqa: E402
    PT9_PUBLIC_FIELDS as PAPEROPS_COCKPIT_NOTIFICATION_REQUIRED_FIELDS,
)
from orchestrator.paper_live_certification import (  # noqa: E402
    PT10_PUBLIC_FIELDS as PAPER_LIVE_CERTIFICATION_REQUIRED_FIELDS,
)
from orchestrator.phase6_cockpit_visibility import (
    PUBLIC_STATUS_FIELDS as PHASE6_LEARNING_LOOP_REQUIRED_FIELDS,
)  # noqa: E402
from orchestrator.phase6_certification import (
    PUBLIC_STATUS_FIELDS as PHASE6_CERTIFICATION_REQUIRED_FIELDS,
)  # noqa: E402
from orchestrator.rs9_learning_loop import (  # noqa: E402
    PUBLIC_STATUS_FIELDS as RS9_LEARNING_LOOP_REQUIRED_FIELDS,
)
from orchestrator.rs10_final_paper_autonomy_certification import (  # noqa: E402
    AUTHORITY_FIELDS as RS10_FINAL_PAPER_AUTONOMY_AUTHORITY_FIELDS,
    PUBLIC_STATUS_FIELDS as RS10_FINAL_PAPER_AUTONOMY_REQUIRED_FIELDS,
    UNSAFE_COUNT_FIELDS as RS10_FINAL_PAPER_AUTONOMY_UNSAFE_COUNT_FIELDS,
    validate_rs10_final_paper_autonomy_certification,
)
from orchestrator.telegram_comms import ensure_d8a_telegram_dry_run  # noqa: E402
from orchestrator.telegram_inbound_intake import ensure_sample_telegram_inbound_intake  # noqa: E402
from world_monitor.source_registry import EXPECTED_SOURCE_COUNT  # noqa: E402


WATCHING_REQUIRED_FIELDS = {
    "auth_class",
    "cadence",
    "can_authorize_orders",
    "can_influence_signals",
    "credential_status",
    "degraded_reason",
    "endpoint_count",
    "eligible_for_signal_review",
    "influence_boundary",
    "last_heartbeat",
    "last_payload_time",
    "latency_ms",
    "order_authority_boundary",
    "pipeline",
    "promoted_adapter",
    "raw_status",
    "readiness",
    "registry_status",
    "source_key",
    "source_name",
    "usable_for_research_context",
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

RESEARCH_GOAL_REQUIRED_FIELDS = {
    "akber_stage",
    "boundary",
    "broker_write_allowed",
    "candidate_ready_blockers",
    "close_reason",
    "contradiction_score",
    "execution_allowed",
    "expired",
    "expires_at",
    "goal_id",
    "hypothesis",
    "latency_freshness_score",
    "live_capital_enabled",
    "market_confirmation_score",
    "market_channel",
    "minimum_source_quorum",
    "missing_corroboration",
    "next_handoff",
    "origin",
    "owner_agent",
    "paper_order_allowed",
    "priority_label",
    "priority_score",
    "required_sources",
    "research_goal_hardening_version",
    "risk_handoff_allowed",
    "risk_readiness_score",
    "source_quorum_score",
    "stale",
    "status",
    "stored_status",
    "trade_candidate_creation_allowed",
    "updated_at",
    "watched_instruments",
    "worldview_relevance_score",
    "worldview_lens",
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
    "market_confirmation_policy",
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
    "technical_context_policy",
    "trade_candidate_created",
    "worldview_prior_status",
}

YAHOO_FINANCE_REQUIRED_FIELDS = {
    "boundary",
    "broker_echo_authority",
    "broker_write_authority",
    "cache_path_exposed",
    "canonical_source",
    "canonical_source_count",
    "classification",
    "cookies_exposed",
    "crumb_tokens_exposed",
    "degraded",
    "degraded_reason",
    "enabled",
    "fill_confirmation_authority",
    "last_check_at",
    "live_capital_authority",
    "live_read_deferred",
    "live_read_enabled",
    "market_confirmation_policy",
    "market_confirmation_role",
    "order_authority",
    "public_safe",
    "raw_archive_path_exposed",
    "raw_payload_exposed",
    "receipt_evidence_authority",
    "reconciliation_truth_authority",
    "risk_approval_authority",
    "sample_mode_available",
    "schema_version",
    "scraped_html_exposed",
    "signal_authority",
    "source",
    "status",
    "symbol_allowlist_count",
}

TRADINGVIEW_MCP_REQUIRED_FIELDS = {
    "active_required_challenges",
    "boundary",
    "broker_write_allowed",
    "canonical_source_count",
    "classification",
    "connected",
    "enabled",
    "execution_allowed",
    "fill_confirmation_authority",
    "live_calls_enabled",
    "live_capital_enabled",
    "local_checkout_exists",
    "local_path_exposed",
    "mcp_config_exists",
    "obvious_technical_context_count",
    "package_importable",
    "paper_order_allowed",
    "provider",
    "public_safe",
    "quantum_job_authority",
    "raw_payload_exposed",
    "receipt_evidence_authority",
    "reconciliation_truth_authority",
    "risk_approval_authority",
    "sample_mode_available",
    "schema_version",
    "service_importable",
    "signal_authority",
    "source",
    "source_key",
    "source_quorum_credit_allowed",
    "status",
    "technical_confirmation_role",
    "technical_context_count",
    "technical_context_status",
    "technical_contexts",
    "trade_candidate_creation_allowed",
}

PREFERENCE_MCP_REQUIRED_FIELDS = {
    "active_required_challenge_count",
    "approved_domain_pack_count",
    "approved_domain_packs",
    "authority_flags",
    "blocked_paid_tool_count",
    "boundary",
    "catalog_entry_count",
    "catalog_status",
    "classification",
    "daily_call_budget",
    "degraded",
    "degraded_reason",
    "domain_pack_count",
    "domain_pack_status",
    "domain_tool_calls_allowed",
    "enabled",
    "execution_allowed",
    "first_trading_universe_strategy_family_count",
    "identity_gate_status",
    "identity_status",
    "last_successful_catalog_check",
    "last_successful_domain_pack_check",
    "last_successful_provenance_check",
    "last_successful_shadow_context_check",
    "live_capital_enabled",
    "live_mcp_call_allowed",
    "paid_tool_calls_allowed",
    "paid_tools_allowed",
    "paper_order_allowed",
    "preference_only_confirmation_allowed",
    "private_source_payload_exposed",
    "provider_label",
    "provenance_context_status",
    "provenance_distinct_upstream_source_count",
    "provenance_status",
    "public_safe",
    "quota_degraded",
    "quota_metadata_present",
    "quota_status",
    "raw_key_exposed",
    "raw_payload_exposed",
    "raw_prompt_exposed",
    "risk_handoff_allowed",
    "run_call_budget",
    "schema_version",
    "search_tools_allowed",
    "shadow_context_role",
    "shadow_context_status",
    "shadow_observation_count",
    "source_key",
    "source_promotion_canonical_source_count_after",
    "source_promotion_decision_count",
    "source_promotion_promoted_decision_count",
    "source_promotion_status",
    "source_quorum_credit_allowed",
    "status",
    "trade_candidate_creation_allowed",
}

PHASE4_STRATEGY_REQUIRED_FIELDS = {
    "approved_shadow_ready",
    "approved_shadow_strategy_toggle_count",
    "approval_event",
    "approval_event_status",
    "audit_completion_state",
    "boundary",
    "broker_write_allowed",
    "broker_write_allowed_count",
    "certification",
    "certification_status",
    "execution_allowed",
    "execution_allowed_count",
    "live_capital_enabled",
    "live_capital_enabled_count",
    "market_confirmation_policy",
    "no_execution_boundary",
    "paper_order_allowed",
    "paper_order_allowed_count",
    "phase",
    "phase4_certification_allowed",
    "phase4_certified",
    "phase5_handoff_allowed",
    "public_safe",
    "schema_version",
    "stage",
    "stage_status",
    "strategy_document",
    "strategy_document_status",
    "strategy_toggles",
    "toggle_count",
    "trade_candidate_count",
}

PHASE5_LAYER_B_REQUIRED_FIELDS = {
    "approval_state",
    "approval_policy_router_enabled",
    "boundary",
    "broker_write_allowed",
    "execution_adapter_write_authority",
    "kill_switch_mutation_authority",
    "layer",
    "live_capital_enabled",
    "nonapproval_blocker_count",
    "only_explicit_approval_blocks_phase5_plan",
    "paper_execution_allowed",
    "paper_order_allowed",
    "phase",
    "phase4_certified",
    "phase5_handoff_allowed",
    "phase5_layer_b_implementation_allowed",
    "phase5_layer_b_implementation_plan_allowed",
    "phase5_layer_b_scope_count",
    "phase5_orchestration_start_allowed",
    "preference_source_promotion_status",
    "public_safe",
    "readiness_blocker_count",
    "readiness_blockers",
    "risk_agent_approval_authority",
    "schema_version",
    "stage",
    "status",
    "yahoo_finance_role",
}

PHASE5_KILL_SWITCH_REQUIRED_FIELDS = {
    "active_switch_count",
    "blocking_switch_count",
    "boundary",
    "broker_write_allowed",
    "clear_switch_count",
    "corrupt_state_fail_closed_default_count",
    "default_fail_closed_on_corrupt_state",
    "default_fail_closed_on_missing_state",
    "event_log_event_count",
    "event_log_written",
    "execution_allowed",
    "fail_closed_default_count",
    "kill_switch_mutation_authority",
    "ledger_recorded",
    "live_capital_enabled",
    "missing_state_fail_closed_default_count",
    "paper_order_allowed",
    "phase",
    "public_safe",
    "q5_3_paper_size_eligible_count",
    "q5_3_risk_review_count",
    "required_enforcement_point_count",
    "required_enforcement_points",
    "required_scope_type_count",
    "required_scope_types",
    "schema_version",
    "scope_counts",
    "stage",
    "state_counts",
    "status",
    "status_counts",
    "switch_count",
    "telegram_live_notifications_allowed",
    "validation_error_count",
}

PHASE5_EXECUTION_ADAPTER_REQUIRED_FIELDS = {
    "active_kill_switch_block_count",
    "adapter_status_count",
    "alpaca_account_mode",
    "alpaca_credentials_configured",
    "alpaca_current_balance_gbp",
    "alpaca_open_order_count",
    "alpaca_open_position_count",
    "alpaca_read_health",
    "alpaca_status",
    "alpaca_write_health",
    "boundary",
    "broker_write_allowed",
    "crypto_perps_write_allowed",
    "downstream_staging_allowed_count",
    "event_log_event_count",
    "event_log_written",
    "execution_adapter_write_authority",
    "first_release_allowed_count",
    "live_capital_enabled",
    "live_endpoint_allowed",
    "local_path_exposed_count",
    "paper_order_allowed",
    "paper_order_staging_allowed",
    "paper_order_submission_allowed",
    "phase",
    "prediction_market_write_allowed",
    "public_safe",
    "raw_payload_exposed_count",
    "read_allowed_count",
    "read_health_counts",
    "reconciliation_prerequisite_count",
    "recorded",
    "required_check_count",
    "schema_version",
    "secret_value_exposed_count",
    "stage",
    "status",
    "status_counts",
    "validation_error_count",
    "write_health_counts",
}

PHASE5_PAPER_ORDER_STAGING_REQUIRED_FIELDS = {
    "active_kill_switch_block_count",
    "blocked_count",
    "boundary",
    "broker_post_called",
    "broker_write_allowed",
    "cancellation_condition_count",
    "eligible_for_staging_count",
    "event_log_event_count",
    "event_log_prewrite_ready_count",
    "event_log_written",
    "execution_allowed",
    "global_error_count",
    "live_capital_enabled",
    "local_path_exposed_count",
    "order_state_counts",
    "paper_order_allowed",
    "paper_order_staging_allowed",
    "paper_order_submitted",
    "paper_order_submission_allowed",
    "paper_size_eligible_count",
    "phase",
    "public_safe",
    "raw_payload_exposed_count",
    "reconciliation_prerequisite_count",
    "recorded",
    "required_check_count",
    "risk_review_count",
    "schema_version",
    "secret_value_exposed_count",
    "stage",
    "staged_order_count",
    "staging_allowed",
    "staging_record_count",
    "status",
    "status_counts",
    "submission_allowed",
    "validation_error_count",
}

PHASE5_ALPACA_PAPER_DRY_RUN_REQUIRED_FIELDS = {
    "alpaca_post_called",
    "blocked_count",
    "boundary",
    "broker_post_called",
    "broker_write_allowed",
    "dry_run_receipt_count",
    "dry_run_record_count",
    "duplicate_guard_collision_count",
    "event_log_event_count",
    "event_log_written",
    "execution_allowed",
    "idempotency_collision_count",
    "live_capital_enabled",
    "live_endpoint_allowed",
    "local_path_exposed_count",
    "paper_order_allowed",
    "paper_order_submitted",
    "paper_order_submission_allowed",
    "phase",
    "public_safe",
    "raw_payload_exposed_count",
    "receipt_state_counts",
    "recorded",
    "request_preview_count",
    "required_check_count",
    "schema_version",
    "secret_value_exposed_count",
    "source_staged_order_count",
    "source_staging_record_count",
    "stage",
    "status",
    "status_counts",
    "validation_error_count",
}

PHASE5_PAPER_SUBMIT_ENABLEMENT_REQUIRED_FIELDS = {
    "alpaca_post_called",
    "authorization_header_exposed_count",
    "base_url_exposed_count",
    "blocked_count",
    "boundary",
    "broker_post_called",
    "broker_submit_receipt_created_count",
    "broker_write_allowed",
    "broker_write_allowed_count",
    "dry_run_bundle_validation_error_count",
    "duplicate_guard_collision_count",
    "event_log_event_count",
    "event_log_written",
    "execution_adapter_write_authority",
    "execution_adapter_write_authority_count",
    "idempotency_collision_count",
    "live_capital_enabled",
    "live_capital_enabled_count",
    "live_endpoint_allowed",
    "live_endpoint_allowed_count",
    "local_path_exposed_count",
    "paper_execution_allowed",
    "paper_execution_allowed_count",
    "paper_order_allowed",
    "paper_order_allowed_count",
    "paper_order_submission_allowed",
    "paper_order_submission_allowed_count",
    "paper_order_submitted",
    "paper_order_submitted_count",
    "paper_submit_approval_logged",
    "paper_submit_approval_present",
    "paper_submit_approval_state",
    "phase",
    "prediction_market_write_allowed",
    "prediction_market_write_allowed_count",
    "public_safe",
    "raw_payload_exposed_count",
    "receipt_state_counts",
    "recorded",
    "required_check_count",
    "schema_version",
    "secret_value_exposed_count",
    "source_dry_run_receipt_count",
    "source_dry_run_record_count",
    "source_request_preview_count",
    "stage",
    "status",
    "status_counts",
    "submit_enablement_record_count",
    "submit_path_available",
    "submit_path_available_count",
    "submit_path_key",
    "validation_error_count",
}

PHASE5_PREDICTION_MARKET_ADAPTER_REQUIRED_FIELDS = {
    "authorization_header_exposed_count",
    "base_url_exposed_count",
    "boundary",
    "broker_post_called_count",
    "broker_write_allowed",
    "broker_write_allowed_count",
    "crypto_perps_write_allowed",
    "crypto_perps_write_allowed_count",
    "event_log_event_count",
    "event_log_written",
    "guarded_placeholder_count",
    "live_blocked_count",
    "live_capital_enabled",
    "live_capital_enabled_count",
    "live_endpoint_allowed",
    "live_endpoint_allowed_count",
    "local_path_exposed_count",
    "paid_preference_tools_allowed",
    "paid_preference_tools_allowed_count",
    "paper_not_available_count",
    "paper_order_allowed",
    "paper_order_allowed_count",
    "paper_order_submitted",
    "paper_order_submitted_count",
    "phase",
    "placeholder_status_counts",
    "policy_risk_caution_context_count",
    "prediction_market_context_count",
    "prediction_market_live_order_allowed_count",
    "prediction_market_order_allowed_count",
    "prediction_market_route_count",
    "prediction_market_spend_allowed_count",
    "prediction_market_write_allowed",
    "prediction_market_write_allowed_count",
    "preference_context_status",
    "preference_counts_as_canonical_source",
    "preference_distinct_upstream_source_count",
    "preference_multi_source_context_allowed",
    "preference_only_source_quorum_allowed",
    "preference_provenance_status",
    "preference_source_quorum_credit_allowed",
    "public_safe",
    "raw_payload_exposed_count",
    "read_only_route_count",
    "recorded",
    "required_check_count",
    "route_count",
    "schema_version",
    "secret_value_exposed_count",
    "stage",
    "status",
    "status_counts",
    "strategy_source_quorum_credit_allowed",
    "validation_error_count",
}

PHASE5_TELEGRAM_NOTIFIER_REQUIRED_FIELDS = {
    "alert_type_count",
    "authorization_header_exposed_count",
    "bot_token_exposed_count",
    "boundary",
    "broker_post_called_count",
    "broker_write_allowed",
    "broker_write_allowed_count",
    "chat_id_exposed_count",
    "eligible_alert_count",
    "event_log_event_count",
    "event_log_written",
    "execution_allowed_count",
    "live_capital_enabled",
    "live_capital_enabled_count",
    "live_endpoint_allowed_count",
    "live_send_allowed_count",
    "local_path_exposed_count",
    "normal_live_notification_allowed",
    "notification_record_count",
    "notification_state_counts",
    "outbox_message_written_count",
    "paper_order_allowed",
    "paper_order_allowed_count",
    "paper_order_submitted",
    "paper_order_submitted_count",
    "phase",
    "prediction_market_write_allowed_count",
    "private_send_test_allowed",
    "public_safe",
    "queued_dry_run_alert_count",
    "raw_payload_exposed_count",
    "recorded",
    "required_check_count",
    "schema_version",
    "secret_value_exposed_count",
    "send_test_approval_logged",
    "send_test_approval_present",
    "send_test_gate_state",
    "source_degradation_count",
    "stage",
    "status",
    "status_counts",
    "suppressed_alert_count",
    "telegram_approve_trade_command_enabled_count",
    "telegram_bot_configured",
    "telegram_cancel_trade_command_enabled_count",
    "telegram_close_trade_command_enabled_count",
    "telegram_command_path_enabled",
    "telegram_command_path_enabled_count",
    "telegram_delivery_target_count",
    "telegram_live_notifications_allowed",
    "telegram_live_notifications_allowed_count",
    "telegram_mode",
    "telegram_modify_trade_command_enabled_count",
    "telegram_place_trade_command_enabled_count",
    "telegram_reject_trade_command_enabled_count",
    "telegram_resize_trade_command_enabled_count",
    "telegram_send_gate",
    "telegram_status",
    "telegram_trade_command_enabled_count",
    "validation_error_count",
}

PHASE5_POSITION_MONITOR_REQUIRED_FIELDS = {
    "account_equity_gbp",
    "account_identifier_exposed_count",
    "alpaca_post_called_count",
    "authorization_header_exposed_count",
    "boundary",
    "broker_order_identifier_exposed_count",
    "broker_post_called_count",
    "broker_write_allowed",
    "broker_write_allowed_count",
    "closed_trade_count",
    "closed_trade_summary_count",
    "contradictory_state_count",
    "current_balance_gbp",
    "drawdown_pct",
    "duplicate_state_count",
    "event_log_event_count",
    "event_log_written",
    "execution_allowed_count",
    "failed_reconciliation_count",
    "lifecycle_state_count",
    "lifecycle_state_counts",
    "live_capital_enabled",
    "live_capital_enabled_count",
    "local_path_exposed_count",
    "mirrored_order_count",
    "missing_state_count",
    "monitor_record_count",
    "new_actions_blocked_by_reconciliation_failure",
    "open_order_count",
    "open_position_count",
    "order_cancel_allowed_count",
    "paper_account_connection_status",
    "paper_account_snapshot_count",
    "paper_account_status",
    "paper_order_allowed",
    "paper_order_allowed_count",
    "paper_order_submitted",
    "paper_order_submitted_count",
    "paper_submit_gate_status",
    "phase",
    "position_close_allowed_count",
    "position_created_count",
    "position_monitor_write_authority",
    "position_monitor_write_authority_count",
    "position_record_count",
    "position_resize_allowed_count",
    "postmortem_complete_count",
    "postmortem_due_count",
    "public_safe",
    "raw_payload_exposed_count",
    "realized_pnl_gbp",
    "reconciliation_state_counts",
    "recorded",
    "required_check_count",
    "schema_version",
    "secret_value_exposed_count",
    "stage",
    "status",
    "status_counts",
    "stuck_state_count",
    "submitted_order_count",
    "telegram_live_notifications_allowed_count",
    "telegram_notifier_status",
    "unknown_state_count",
    "unrealized_pnl_gbp",
    "validation_error_count",
}

PHASE5_SIGNAL_REVIEW_REQUIRED_FIELDS = {
    "account_identifier_exposed_count",
    "alpaca_post_called_count",
    "authorization_header_exposed_count",
    "backend_truth_displayed_count",
    "backend_validation_error_count",
    "boundary",
    "broker_order_identifier_exposed_count",
    "broker_post_called_count",
    "broker_write_allowed",
    "broker_write_allowed_count",
    "chain_status_counts",
    "chain_step_count",
    "decision_chain_count",
    "event_log_event_count",
    "event_log_written",
    "funnel_flagged_missing_pricing_gap_producer_count",
    "funnel_review_count",
    "funnel_risk_reviews_blocked_only_by_pricing_gap_policy_count",
    "funnel_shadow_signal_count",
    "funnel_signals_blocked_only_by_missing_pricing_gap_count",
    "funnel_signals_passed_to_risk_count",
    "funnel_signals_with_market_confirmation_count",
    "funnel_signals_with_pricing_gap_evidence_count",
    "funnel_stage_b_candidate_signal_count",
    "governance_action_count",
    "governance_comment_count",
    "governance_comment_event_count",
    "kill_switch_action_available_count",
    "kill_switch_action_event_count",
    "kill_switch_action_mutates_state_count",
    "kill_switch_mutation_authority",
    "kill_switch_mutation_authority_count",
    "live_capital_enabled",
    "live_capital_enabled_count",
    "live_endpoint_allowed_count",
    "local_path_exposed_count",
    "order_cancel_control_enabled_count",
    "order_modify_control_enabled_count",
    "order_place_control_enabled_count",
    "paper_order_allowed",
    "paper_order_allowed_count",
    "paper_order_submitted",
    "paper_order_submitted_count",
    "phase",
    "position_close_control_enabled_count",
    "position_resize_control_enabled_count",
    "prediction_market_write_allowed",
    "prediction_market_write_allowed_count",
    "pricing_gap_rollout_relaxed_policy_enabled",
    "pricing_gap_rollout_stage",
    "public_safe",
    "raw_payload_exposed_count",
    "recorded",
    "records",
    "required_check_count",
    "required_chain_steps",
    "schema_version",
    "secret_value_exposed_count",
    "signal_review_record_count",
    "stage",
    "status",
    "status_counts",
    "telegram_command_path_enabled_count",
    "trade_approval_control_enabled_count",
    "trade_rejection_control_enabled_count",
    "ui_inferred_readiness_count",
    "validation_error_count",
}

PHASE5_SYSTEM_MAP_REQUIRED_FIELDS = {
    "artifact_id",
    "artifact_type",
    "backend_parity_check_count",
    "backend_parity_error_count",
    "boundary",
    "broker_write_allowed",
    "event_log_event_count",
    "event_log_required",
    "event_log_written",
    "generated_at",
    "guardrails",
    "kill_switch_mutation_authority",
    "lane_count",
    "lanes",
    "layer_b_node_count",
    "layer_b_node_keys",
    "live_capital_enabled",
    "node_count",
    "nodes",
    "order_place_control_enabled",
    "phase",
    "prediction_market_write_allowed",
    "public_safe",
    "recorded",
    "required_node_keys",
    "schema_version",
    "source_posture",
    "stage",
    "status",
    "trade_approval_control_enabled",
    "ui_inferred_node_count",
    "unsafe_control_count",
    "validation_error_count",
}

PHASE5_PAPER_TRADE_DRILL_REQUIRED_FIELDS = {
    "alpaca_post_called_count",
    "artifact_id",
    "artifact_type",
    "authorization_header_exposed_count",
    "backend_status_counts",
    "blocker_count",
    "blockers",
    "boundary",
    "broker_order_identifier_exposed_count",
    "broker_post_called_count",
    "broker_receipt_count",
    "broker_write_allowed_count",
    "canonical_source_count",
    "closed_trade_count",
    "dashboard_backend_parity_error_count",
    "dashboard_unsafe_control_count",
    "dry_run_receipt_count",
    "event_log_event_count",
    "event_log_required",
    "event_log_written",
    "generated_at",
    "live_capital_enabled_count",
    "live_endpoint_allowed_count",
    "local_path_exposed_count",
    "open_position_count",
    "order_cancel_allowed_count",
    "paper_size_eligible_count",
    "paper_submit_approval_present",
    "paper_submit_approval_state",
    "paper_submit_path_available_count",
    "paper_trade_drill_complete",
    "paper_trade_drill_state",
    "phase",
    "phase5_paper_trade_drill_exit_gate_passed",
    "phase5_paper_trade_drill_implementation_ready",
    "phase7_proof_credit_allowed",
    "phase7_proof_credit_allowed_count",
    "position_close_allowed_count",
    "position_open_lifecycle_satisfied",
    "position_monitor_write_authority_count",
    "position_resize_allowed_count",
    "prediction_market_write_allowed_count",
    "public_safe",
    "raw_payload_exposed_count",
    "recorded",
    "records",
    "required_step_count",
    "required_steps",
    "risk_review_count",
    "schema_version",
    "secret_value_exposed_count",
    "signal_review_record_count",
    "source_bundle_count",
    "source_bundles",
    "source_validation_error_count",
    "stage",
    "staged_order_count",
    "status",
    "status_counts",
    "step_count",
    "submitted_paper_order_count",
    "telegram_dashboard_sync_status",
    "telegram_live_notifications_allowed_count",
    "validation_error_count",
}

PHASE5_CERTIFICATION_REQUIRED_FIELDS = {
    "artifact_id",
    "artifact_type",
    "blocking_unsafe_count",
    "boundary",
    "broker_write_allowed_count",
    "canonical_source_count",
    "certification_blocker_count",
    "certification_blockers",
    "closed_trade_count",
    "crypto_perps_write_allowed_count",
    "event_log_event_count",
    "event_log_required",
    "event_log_written",
    "gate_records",
    "generated_at",
    "input_gate_blocked_count",
    "input_gate_count",
    "input_gate_passed_count",
    "live_capital_enabled_count",
    "live_endpoint_allowed_count",
    "open_position_count",
    "paper_trade_drill_complete",
    "paper_trade_drill_exit_gate_passed",
    "phase",
    "phase5_certification_schema_version",
    "phase5_certified",
    "phase5_complete",
    "phase5_exit_gate",
    "phase6_handoff_allowed",
    "phase7_planning_allowed",
    "phase7_proof_credit_allowed",
    "phase7_proof_credit_allowed_count",
    "postmortem_due_count",
    "prediction_market_write_allowed_count",
    "public_safe",
    "q5_stage_count",
    "recorded",
    "required_input_stage_count",
    "required_input_stages",
    "schema_version",
    "stage",
    "stage_status",
    "status",
    "submitted_paper_order_count",
    "telegram_live_notifications_allowed_count",
    "validation_error_count",
}

PHASE5_PHASE6_HANDOFF_REQUIRED_FIELDS = {
    "alpaca_post_called_count",
    "artifact_id",
    "artifact_type",
    "blocker_count",
    "blockers",
    "boundary",
    "broker_post_called_count",
    "broker_write_allowed_count",
    "canonical_source_count",
    "closed_trade_count",
    "crypto_perps_write_allowed_count",
    "downstream_staging_allowed_count",
    "event_log_event_count",
    "event_log_required",
    "event_log_written",
    "failed_reconciliation_count",
    "generated_at",
    "guarded_postmortem_due_ready",
    "guarded_postmortem_due_ref",
    "handoff_state",
    "live_capital_enabled_count",
    "live_endpoint_allowed_count",
    "mirrored_order_count",
    "open_position_count",
    "paper_trade_drill_blocker_count",
    "paper_trade_drill_complete",
    "paper_trade_drill_exit_gate_passed",
    "phase",
    "phase5_certified",
    "phase5_exit_gate",
    "phase5_phase6_handoff_schema_version",
    "phase5_test_trades_count_for_phase7",
    "phase6_architect_policy_mutation_allowed",
    "phase6_knowledge_graph_write_allowed",
    "phase6_knowledge_graph_write_allowed_count",
    "phase6_learning_loop_implementation_allowed",
    "phase6_learning_loop_plan_allowed",
    "phase6_learning_write_allowed",
    "phase6_learning_write_allowed_count",
    "phase6_model_weight_update_allowed",
    "phase6_model_weight_update_allowed_count",
    "phase6_policy_mutation_allowed_count",
    "phase6_postmortem_ingestion_allowed",
    "phase6_required_module_count",
    "phase6_required_modules",
    "phase6_shadow_strategy_runner_allowed",
    "phase6_trust_score_update_allowed",
    "phase6_trust_score_update_allowed_count",
    "phase6_handoff_allowed",
    "phase7_planning_allowed",
    "phase7_proof_credit_allowed",
    "phase7_proof_credit_allowed_count",
    "postmortem_due_count",
    "prediction_market_write_allowed_count",
    "public_safe",
    "recorded",
    "recommended_next_stage",
    "required_source_count",
    "schema_version",
    "source_recorded_count",
    "source_validation_error_count",
    "stage",
    "status",
    "submitted_order_count",
    "validation_error_count",
}

MARKET_CONFIRMATION_POLICY_REQUIRED_FIELDS = {
    "boundary",
    "broker_reconciliation_authority",
    "latest_observed_at",
    "market_price_confirmation",
    "max_age_seconds",
    "order_authority",
    "pricing_gap",
    "providers",
    "signal_authority",
    "single_source_hold",
    "stale",
    "status",
    "unavailable",
    "uses_yahoo_finance",
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

EXECUTION_POLICY_REQUIRED_FIELDS = {
    "authority",
    "boundary",
    "broker_write_allowed_count",
    "by_status",
    "execution_allowed_count",
    "kill_switch_block_count",
    "live_capital_enabled_count",
    "paper_order_created_count",
    "review_count",
    "reviews",
    "schema_version",
    "staged_paper_order_allowed_count",
    "status",
}

EXECUTION_POLICY_REVIEW_REQUIRED_FIELDS = {
    "blocked_reasons",
    "boundary",
    "broker_write_allowed",
    "checks",
    "execution_allowed",
    "instrument",
    "kill_switches",
    "live_capital_enabled",
    "paper_order_created",
    "policy_score",
    "required_next_steps",
    "review_id",
    "reviewed_at",
    "schema_version",
    "selected_venue",
    "source_risk_review_id",
    "staged_paper_order_allowed",
    "status",
    "venue_mode",
}

EXECUTION_POLICY_REQUIRED_CHECKS = {
    "broker_order_route",
    "closed_trade_maturity",
    "event_log",
    "execution_policy_registry",
    "global_kill_switch",
    "live_capital",
    "operating_mode",
    "paper_order_contract",
    "risk_agent",
    "risk_agent_authority",
    "strategy_kill_switch",
    "venue_kill_switch",
    "venue_registry",
}

EXECUTION_POLICY_REQUIRED_KILL_SWITCHES = {"data", "global", "model", "strategy", "venue"}

STAGED_PAPER_ORDER_REQUIRED_FIELDS = {
    "authority",
    "boundary",
    "broker_write_allowed_count",
    "by_status",
    "execution_allowed_count",
    "live_capital_enabled_count",
    "paper_order_submittable_count",
    "reconciliation_ready_count",
    "review_count",
    "reviews",
    "schema_version",
    "staged_paper_order_created_count",
    "status",
}

STAGED_PAPER_ORDER_REVIEW_REQUIRED_FIELDS = {
    "account_scope",
    "blocked_reasons",
    "boundary",
    "broker_write_allowed",
    "execution_allowed",
    "hypothetical_order",
    "instrument",
    "live_capital_enabled",
    "paper_order_submittable",
    "reconciliation_checks",
    "required_next_steps",
    "review_id",
    "reviewed_at",
    "schema_version",
    "selected_venue",
    "source_execution_policy_review_id",
    "staged_paper_order_created",
    "status",
    "venue_mode",
}

STAGED_PAPER_ORDER_HYPOTHETICAL_REQUIRED_FIELDS = {
    "direction",
    "event_log_ref",
    "idempotency_key",
    "instrument",
    "invalidation",
    "notional_gbp",
    "order_type",
    "quantity",
    "risk_gbp",
    "status",
    "venue",
}

STAGED_PAPER_ORDER_RECONCILIATION_REQUIRED_CHECKS = {
    "broker_route",
    "duplicate_order_guard",
    "event_log_prewrite",
    "execution_policy",
    "idempotency_key",
    "live_capital",
    "paper_account_mirror",
    "paper_account_write_authority",
    "post_submit_reconciliation",
    "postmortem_link",
    "pre_trade_snapshot",
    "staging_contract",
}

BROKER_RECONCILIATION_REQUIRED_FIELDS = {
    "authority",
    "boundary",
    "broker_echo_verified_count",
    "broker_write_allowed_count",
    "by_status",
    "duplicate_order_guard_ready_count",
    "event_log_prewrite_created_count",
    "idempotency_key_allocated_count",
    "live_capital_enabled_count",
    "paper_order_submit_allowed_count",
    "post_submit_reconciliation_ready_count",
    "postmortem_link_ready_count",
    "pre_trade_snapshot_created_count",
    "review_count",
    "reviews",
    "schema_version",
    "status",
}

BROKER_RECONCILIATION_REVIEW_REQUIRED_FIELDS = {
    "account_scope",
    "blocked_reasons",
    "boundary",
    "broker_echo",
    "broker_echo_verified",
    "broker_write_allowed",
    "duplicate_order_guard_ready",
    "event_log_prewrite_created",
    "hypothetical_order",
    "idempotency_key_allocated",
    "instrument",
    "live_capital_enabled",
    "paper_order_submit_allowed",
    "post_submit_reconciliation_ready",
    "postmortem_link_ready",
    "pre_trade_snapshot_created",
    "reconciliation_checks",
    "required_next_steps",
    "review_id",
    "reviewed_at",
    "schema_version",
    "selected_venue",
    "source_execution_policy_review_id",
    "source_staged_paper_order_review_id",
    "status",
    "venue_mode",
}

BROKER_RECONCILIATION_ECHO_REQUIRED_FIELDS = {
    "ack_status",
    "adapter",
    "client_order_id",
    "external_order_id",
    "fill_status",
    "raw_broker_payload_stored",
    "status",
    "submitted_at",
    "venue",
}

BROKER_RECONCILIATION_REQUIRED_CHECKS = {
    "broker_adapter_mode",
    "broker_echo",
    "broker_route",
    "duplicate_order_guard",
    "event_log_prewrite",
    "idempotency_key",
    "kill_switch",
    "live_capital",
    "paper_account_mirror",
    "paper_account_write_authority",
    "paper_order_submittable",
    "post_submit_reconciliation",
    "postmortem_link",
    "pre_trade_snapshot",
    "source_staged_status",
    "staged_order_contract",
    "staged_order_created",
    "venue_registry_write_health",
}

PAPER_SUBMIT_RECEIPT_REQUIRED_FIELDS = {
    "authority",
    "boundary",
    "broker_post_called_count",
    "broker_write_allowed_count",
    "by_status",
    "dry_run_receipt_created_count",
    "live_capital_enabled_count",
    "paper_order_submitted_count",
    "review_count",
    "reviews",
    "schema_version",
    "status",
}

PAPER_SUBMIT_RECEIPT_REVIEW_REQUIRED_FIELDS = {
    "account_scope",
    "blocked_reasons",
    "boundary",
    "broker_echo",
    "broker_post_called",
    "broker_write_allowed",
    "duplicate_order_guard",
    "dry_run_receipt_created",
    "event_log_prewrite_schema",
    "hypothetical_order",
    "idempotency_design",
    "instrument",
    "live_capital_enabled",
    "paper_order_submitted",
    "pre_trade_snapshot_schema",
    "receipt_checks",
    "required_next_steps",
    "review_id",
    "reviewed_at",
    "schema_version",
    "selected_venue",
    "simulated_receipt",
    "source_broker_reconciliation_review_id",
    "source_execution_policy_review_id",
    "source_staged_paper_order_review_id",
    "status",
    "submitted_at",
    "venue_mode",
}

PAPER_SUBMIT_RECEIPT_SIMULATED_REQUIRED_FIELDS = {
    "adapter",
    "broker_post_called",
    "client_order_id",
    "external_order_id",
    "idempotency_preview_key",
    "mode",
    "paper_order_submitted",
    "raw_broker_payload_stored",
    "status",
    "venue",
}

PAPER_SUBMIT_RECEIPT_REQUIRED_CHECKS = {
    "broker_echo",
    "broker_post",
    "broker_reconciliation_contract",
    "broker_reconciliation_status",
    "broker_write",
    "duplicate_order_guard",
    "duplicate_order_guard_schema",
    "dry_run_receipt",
    "event_log_prewrite",
    "event_log_prewrite_schema",
    "idempotency_design",
    "idempotency_key",
    "kill_switch",
    "live_capital",
    "paper_account_mirror",
    "paper_account_write_authority",
    "paper_order_submission",
    "paper_order_submit_permission",
    "post_submit_reconciliation",
    "postmortem_link",
    "pre_trade_snapshot",
    "pre_trade_snapshot_schema",
    "venue_registry_write_health",
}

PAPER_SUBMIT_RECEIPT_IDEMPOTENCY_REQUIRED_FIELDS = {
    "allocation_authority",
    "boundary",
    "broker_usable",
    "collision_policy",
    "material_fields",
    "preview_key",
    "status",
}

PAPER_SUBMIT_RECEIPT_PREWRITE_REQUIRED_FIELDS = {
    "boundary",
    "event_log_ref",
    "event_type",
    "idempotency_preview_key",
    "required_fields",
    "source_broker_reconciliation_review_id",
    "status",
    "write_performed",
}

PAPER_SUBMIT_RECEIPT_SNAPSHOT_REQUIRED_FIELDS = {
    "account_scope",
    "boundary",
    "capture_performed",
    "connection_status",
    "current_balance_gbp",
    "open_position_count",
    "order_count",
    "required_fields",
    "snapshot_ref",
    "status",
}

PAPER_SUBMIT_RECEIPT_DUPLICATE_GUARD_REQUIRED_FIELDS = {
    "block_policy",
    "boundary",
    "duplicate_detected",
    "duplicate_window_seconds",
    "guard_key",
    "guard_write_performed",
    "lookup_performed",
    "lookup_sources",
    "status",
}

MODEL_ACTIVITY_ROLES = {"Research Analyst", "Strategy Lead", "Head of Quant"}

QUANTUM_ORACLE_REQUIRED_FIELDS = {
    "boundary",
    "cadence",
    "cadence_days",
    "execution_allowed_count",
    "hardware_scheduler_enabled_count",
    "hardware_submission_allowed_count",
    "hardware_submitted_count",
    "latest_backend",
    "latest_backend_status",
    "latest_created_at",
    "latest_durable_evidence_status",
    "latest_input_contract_status",
    "latest_input_fingerprint",
    "latest_input_source_type",
    "latest_local_simulation_mode",
    "latest_market_confirmation_status",
    "latest_output_annotation_target",
    "latest_output_route_type",
    "latest_output_routing",
    "latest_output_routing_status",
    "latest_output_storage_type",
    "latest_recommendation",
    "latest_validation_checks",
    "latest_yahoo_finance_role",
    "latest_yahoo_only_market_confirmation",
    "local_simulator",
    "next_due_at",
    "paper_order_allowed_count",
    "qiskit_available",
    "qiskit_aer_available",
    "provider_readiness",
    "result_count",
    "scheduler_dry_run",
    "schema_version",
    "status",
    "trade_candidate_created_count",
}

QUANTUM_SCHEDULER_DRY_RUN_REQUIRED_FIELDS = {
    "autonomous_scheduler_enabled",
    "background_automation_created",
    "boundary",
    "bypass_broker_reconciliation_allowed",
    "bypass_execution_policy_allowed",
    "bypass_paper_submit_receipt_allowed",
    "bypass_risk_agent_allowed",
    "bypass_signal_integrity_allowed",
    "bypass_strategy_lead_allowed",
    "cadence",
    "cadence_days",
    "dry_run_only",
    "due",
    "due_reason",
    "execution_allowed",
    "hardware_jobs_submitted_count",
    "hardware_scheduler_enabled",
    "hardware_scheduler_enabled_count",
    "hardware_submission_allowed",
    "hardware_submission_allowed_count",
    "intended_job_count",
    "intended_jobs",
    "job_submission_allowed",
    "jobs_queued_count",
    "jobs_submitted_count",
    "last_run_at",
    "next_due_at",
    "paper_order_allowed",
    "provider_call_allowed",
    "public_safe",
    "queue_write_allowed",
    "recurring_job_created",
    "scheduler_enabled",
    "schema_version",
    "status",
    "trade_candidate_authority",
    "would_queue_job_count",
    "would_queue_jobs",
}

QUANTUM_SCHEDULER_JOB_REQUIRED_FIELDS = {
    "boundary",
    "dry_run_only",
    "execution_allowed",
    "hardware_submission_allowed",
    "job_submission_allowed",
    "job_type",
    "local_validation_required",
    "paper_order_allowed",
    "provider_call_allowed",
    "queue_write_allowed",
    "required_gates",
    "schema_version",
    "source",
    "trade_candidate_authority",
}

QUANTUM_OUTPUT_ROUTING_REQUIRED_FIELDS = {
    "ambiguity_score",
    "annotation_target",
    "blocked_routes",
    "boundary",
    "broker_reconciliation_authority",
    "broker_reconciliation_write_count",
    "broker_write_allowed",
    "confidence_delta",
    "execution_allowed",
    "execution_policy_approval_count",
    "execution_policy_authority",
    "hardware_submission_allowed",
    "job_id",
    "job_type",
    "paper_order_allowed",
    "paper_submit_receipt_authority",
    "paper_submit_receipt_created_count",
    "pattern_score",
    "provider_call_allowed",
    "public_safe",
    "recommendation",
    "recommendation_class",
    "risk_approval_authority",
    "risk_approval_count",
    "route_type",
    "schema_version",
    "signal_integrity_context",
    "source_ref",
    "staged_paper_order_authority",
    "staged_paper_order_created_count",
    "status",
    "storage_type",
    "strategy_lead_context",
    "trade_candidate_authority",
    "trade_candidate_created_count",
}

QUANTUM_LOCAL_SIMULATOR_REQUIRED_FIELDS = {
    "backend_selection_policy",
    "boundary",
    "classical_fallback_available",
    "dependency_guidance",
    "execution_allowed",
    "expected_job_types",
    "hardware_provider_selected",
    "hardware_scheduler_enabled",
    "hardware_submission_allowed",
    "local_only",
    "output_schema_version",
    "paper_order_allowed",
    "provider_call_allowed",
    "public_safe",
    "qiskit_aer_available",
    "qiskit_available",
    "qiskit_dependencies_available",
    "required_job_count",
    "runtime_failure_policy",
    "schema_consistent_across_backends",
    "schema_version",
    "selected_backend",
    "status",
    "trade_candidate_authority",
}

QUANTUM_PROVIDER_READINESS_REQUIRED_FIELDS = {
    "available_without_secret_count",
    "boundary",
    "by_status",
    "configured_count",
    "disabled_by_policy_count",
    "execution_allowed_count",
    "expected_provider_count",
    "hardware_provider_stubs",
    "hardware_scheduler_enabled_count",
    "hardware_submission_allowed_count",
    "missing_optional_package_count",
    "missing_secret_count",
    "paper_order_allowed_count",
    "provider_call_allowed_count",
    "provider_count",
    "providers",
    "public_safe",
    "qctrl_configured",
    "qctrl_readiness",
    "raw_response_exposed_count",
    "schema_version",
    "secret_value_exposed_count",
    "status",
    "trade_candidate_authority_count",
}

QUANTUM_HARDWARE_PROVIDER_STUB_LEDGER_REQUIRED_FIELDS = {
    "boundary",
    "configured_policy_blocked_count",
    "credential_configured_count",
    "disabled_by_policy_count",
    "execution_allowed_count",
    "expected_provider_count",
    "explicit_hardware_policy_approval_present",
    "hardware_backend_implemented_count",
    "hardware_scheduler_enabled_count",
    "hardware_submission_allowed_count",
    "hardware_submitted_count",
    "live_probe_allowed_count",
    "local_simulator_validation_passed",
    "missing_credentials_count",
    "missing_local_validation_count",
    "paper_order_allowed_count",
    "provider_call_allowed_count",
    "provider_count",
    "providers",
    "public_safe",
    "raw_response_exposed_count",
    "schema_version",
    "secret_value_exposed_count",
    "status",
    "submitting_backend_implemented_count",
    "trade_candidate_authority_count",
}

QUANTUM_HARDWARE_PROVIDER_STUB_PROVIDER_REQUIRED_FIELDS = {
    "boundary",
    "credential_configured",
    "credential_requirements",
    "execution_allowed",
    "explicit_hardware_policy_approval_present",
    "hardware_backend_implemented",
    "hardware_scheduler_enabled",
    "hardware_submission_allowed",
    "hardware_submitted",
    "key",
    "live_probe_allowed",
    "local_simulator_validation_passed",
    "missing_prerequisites",
    "name",
    "notes",
    "paper_order_allowed",
    "policy_block_reason",
    "provider_call_allowed",
    "provider_call_count",
    "provider_role",
    "public_safe",
    "raw_response_exposed",
    "schema_version",
    "sdk_module_candidates",
    "sdk_package_importable",
    "secret_value_exposed",
    "status",
    "submitting_backend_implemented",
    "trade_candidate_authority",
}

QUANTUM_QCTRL_READINESS_REQUIRED_FIELDS = {
    "boundary",
    "credential_configured",
    "credential_source",
    "default_mode",
    "execution_allowed",
    "hardware_backend_role",
    "hardware_job_submitted",
    "hardware_scheduler_enabled",
    "hardware_submission_allowed",
    "importable_modules",
    "live_probe_attempted",
    "live_probe_enabled",
    "live_probe_required_flag",
    "optimization_job_submission_allowed",
    "optimization_job_submitted",
    "paper_order_allowed",
    "provider_call_allowed",
    "provider_call_count",
    "provider_role",
    "public_safe",
    "raw_response_exposed",
    "recommendation_authority",
    "runtime_failure_policy",
    "schema_version",
    "sdk_module_candidates",
    "sdk_package_importable",
    "secret_value_exposed",
    "status",
    "trade_candidate_authority",
}

QUANTUM_PROVIDER_REQUIRED_FIELDS = {
    "boundary",
    "credential_configured",
    "execution_allowed",
    "hardware_scheduler_enabled",
    "hardware_submission_allowed",
    "key",
    "name",
    "notes",
    "paper_order_allowed",
    "provider_call_allowed",
    "public_safe",
    "raw_response_exposed",
    "role",
    "schema_version",
    "secret_value_exposed",
    "status",
    "trade_candidate_authority",
}

EXPECTED_QUANTUM_PROVIDERS = {"qiskit_aer", "qctrl", "ibm_quantum", "aws_braket"}
EXPECTED_QUANTUM_HARDWARE_PROVIDERS = {"ibm_quantum", "aws_braket"}
EXPECTED_QUANTUM_JOB_TYPES = {"pattern_recognition", "strategy_collapse"}
ALLOWED_QUANTUM_LOCAL_SIMULATOR_BACKENDS = {"classical_fallback", "qiskit_aer_local"}
ALLOWED_QUANTUM_HARDWARE_PROVIDER_STATUSES = {
    "missing_credentials",
    "missing_local_validation",
    "configured_policy_blocked",
    "disabled_by_policy",
}
ALLOWED_QUANTUM_PROVIDER_STATUSES = {
    "available_without_secret",
    "missing_optional_package",
    "configured",
    "missing_secret",
    "disabled_by_policy",
}

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
    "research_goal_id",
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
    "account_currency",
    "boundary",
    "broker",
    "broker_reconciliation_status",
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
    "mirror_freshness_label",
    "mirror_freshness_status",
    "observed_at",
    "open_order_count",
    "open_position_count",
    "open_positions",
    "order_count",
    "orders",
    "peak_equity_gbp",
    "portfolio_reconciliation",
    "portfolio_value_source",
    "postmortem_complete_count",
    "postmortem_due_count",
    "postmortems_complete",
    "postmortems_due",
    "realized_pnl_gbp",
    "starting_balance_gbp",
    "stale_after_seconds",
    "timeline_status",
    "unrealized_pnl_gbp",
    "write_authority",
    "display_currency",
    "fx_to_gbp_rate",
    "last_broker_sync_age_seconds",
    "last_broker_sync_at",
}

MISSION_CONTROL_REQUIRED_FIELDS = {
    "data_sources",
    "durable_spine",
    "headline",
    "mission_brief",
    "phase3_readiness",
    "phase5_layer_b",
    "phase6_learning_loop",
    "rs9_learning_loop",
    "rs10_final_paper_autonomy_certification",
    "portfolio",
    "safety",
    "schema_version",
    "source",
    "status",
    "strategy",
    "system_stack",
    "team",
    "thinking",
    "trades",
    "trade_intent",
    "trading_philosophy",
}

MISSION_CONTROL_TEAM_REQUIRED_FIELDS = {
    "authority",
    "current_process",
    "key",
    "label",
    "one_line",
    "owner",
    "status",
}

MISSION_CONTROL_SOURCE_REQUIRED_FIELDS = {
    "degraded",
    "ledger",
    "missing_credentials",
    "ok",
    "quorum",
}

MISSION_CONTROL_SOURCE_LEDGER_REQUIRED_FIELDS = {
    "credential_status",
    "eligible_for_signal_review",
    "pipeline",
    "readiness",
    "source_key",
    "source_name",
    "status",
    "trust_score",
    "usable_for_research_context",
}

MISSION_CONTROL_STRATEGY_REQUIRED_FIELDS = {
    "active_lens",
    "akber_lens",
    "boundary",
    "decision_chain",
    "posture",
    "universe",
    "why",
}

MISSION_CONTROL_PORTFOLIO_REQUIRED_FIELDS = {
    "balance_gbp",
    "delta_pct",
    "drawdown_pct",
    "equity_curve",
    "mirror_freshness",
    "realized_pnl_gbp",
    "total_pnl_gbp",
    "unrealized_pnl_gbp",
}

MISSION_CONTROL_TRADES_REQUIRED_FIELDS = {
    "board",
    "boundary",
    "lifecycle_counts",
    "open",
    "postmortems_due",
}

MISSION_CONTROL_THINKING_REQUIRED_FIELDS = {
    "hypotheses",
    "missing_corroboration",
    "research_goals",
    "worldview_prior",
}

MISSION_CONTROL_SAFETY_REQUIRED_FIELDS = {
    "broker_write_allowed",
    "broker_write_route",
    "live_capital_enabled",
    "mode",
    "read_only",
}

DIAGNOSTICS_REQUIRED_FIELDS = {
    "audit_sections",
    "boundary",
    "event_trail",
    "governance_forum",
    "kill_switch_ledger",
    "process_console",
    "prune_audit",
    "prune_candidates",
    "schema_version",
    "source_heartbeat_history",
    "status",
    "system_map",
    "telegram",
}

MISSION_BRIEF_REQUIRED_FIELDS = {
    "authority",
    "boundary",
    "navigation",
    "next_action",
    "question_count",
    "questions",
    "schema_version",
    "status",
    "summary",
}

MISSION_BRIEF_QUESTION_REQUIRED_FIELDS = {
    "answer",
    "href",
    "key",
    "metrics",
    "question",
    "summary",
    "tone",
}

MISSION_BRIEF_EXPECTED_QUESTION_KEYS = {
    "blocked",
    "considering",
    "forbidden",
    "portfolio",
    "thinking",
    "traded",
    "watching",
}

MISSION_BRIEF_AUTHORITY_REQUIRED_FIELDS = {
    "broker_write_allowed",
    "dashboard_write_authority",
    "live_capital_enabled",
    "llm_execution_authority",
    "quantum_execution_authority",
    "telegram_command_authority",
}

MISSION_DATA_SOURCES_REQUIRED_FIELDS = {
    "boundary",
    "connected_sources",
    "degraded_count",
    "durable_expected_source_count",
    "durable_replay_status",
    "durable_replayed_source_count",
    "logged_in_count",
    "logged_in_sources",
    "missing_credential_count",
    "online_count",
    "pending_count",
    "pipeline_count",
    "preference_mcp_catalog_status",
    "preference_mcp_degraded_reason",
    "preference_mcp_domain_pack_count",
    "preference_mcp_identity_status",
    "preference_mcp_provenance_status",
    "preference_mcp_quota_status",
    "preference_mcp_shadow_context_status",
    "preference_mcp_status",
    "total_count",
}

MISSION_PHILOSOPHY_REQUIRED_FIELDS = {
    "boundary",
    "current_self_directive",
    "decision_chain",
    "private_prior_count",
    "status",
    "summary",
}

MISSION_STACK_REQUIRED_FIELDS = {
    "boundary",
    "coo",
    "data_spine",
    "durable_spine",
    "frontier_llm",
    "local_llm",
    "paper_account",
    "paper_live_activation",
    "paper_live_activation_approved",
    "paper_live_activation_system_approval_logged",
    "paper_live_qctrl_product_access",
    "paper_live_qctrl_product_access_verified",
    "paper_live_qctrl_provider_call_count",
    "paper_operational_mode",
    "paper_operational_mode_effective",
    "paper_operational_mode_runtime_override",
    "paperops_alpaca_submit_enablement",
    "paperops_alpaca_submit_enablement_effective",
    "paperops_alpaca_submit_enablement_path_available",
    "paperops_alpaca_paper_post",
    "paperops_alpaca_paper_post_called_count",
    "paperops_paper_lifecycle_polling_enablement",
    "paperops_paper_lifecycle_polling_active",
    "paperops_paper_lifecycle_poller",
    "paperops_paper_lifecycle_poller_order_poll_called_count",
    "paperops_guarded_paper_exit_enablement",
    "paperops_guarded_paper_exit_effective",
    "paperops_guarded_paper_exit_close_called_count",
    "paperops_paper_exit_path",
    "paperops_paper_exit_path_close_called_count",
    "paperops_notification_review",
    "paperops_notification_review_live_send_allowed_count",
    "paperops_30_day_operations",
    "paperops_30_day_operations_scheduler_status",
    "paperops_30_day_operations_active_day_number",
    "paperops_cockpit_notification_upgrade",
    "paperops_cockpit_notification_ready",
    "paperops_cockpit_notification_readout_count",
    "paperops_cockpit_notification_qctrl_hold",
    "paperops_cockpit_notification_live_send_allowed_count",
    "paper_live_certification",
    "paper_live_control_plane_certified",
    "paper_live_certified",
    "paper_live_certification_blocker_count",
    "paper_live_operation_allowed",
    "paper_live_unattended_execution_delegation_enabled",
    "paper_live_unattended_execution_delegation_reason",
    "paperops_active_paper_trading_automation",
    "paperops_active_paper_trading_automation_enabled",
    "paperops_active_paper_trading_qctrl_hold",
    "paperops_active_paper_trading_submit_allowed",
    "paperops_active_paper_trading_unattended_delegation_enabled",
    "paperops_active_paper_trading_unattended_delegation_reason",
    "paperops_active_paper_trading_fresh_submit_count",
    "paperops_active_paper_trading_duplicate_submit_count",
    "paperops_active_paper_trading_idempotency_ledger_active",
    "paperops_active_paper_trading_rs5_available_distinct_setup_count",
    "paperops_active_paper_trading_rs5_can_submit_multiple_today",
    "paperops_active_paper_trading_rs5_daily_target_policy",
    "paperops_active_paper_trading_rs5_max_guarded_submit_attempts_per_run",
    "paperops_active_paper_trading_why_not_trading_now",
    "paperops_qualified_setup_production",
    "paperops_qualified_setup_production_qualified_count",
    "paperops_qualified_setup_production_ready_to_stage",
    "paperops_auto_approval_staged_order",
    "paperops_auto_approval_staged_order_staged_count",
    "paperops_auto_approval_staged_order_ready_for_submit",
    "rs6_lifecycle_portfolio_postmortem",
    "rs6_portfolio_value_source",
    "rs6_balance_ticker_broker_account_derived",
    "rs6_closed_trade_postmortem_coverage_count",
    "rs6_closed_trade_missing_postmortem_count",
    "rs6_paper_proof_ledger_verified_record_count",
    "rs6_mirror_trade_counted_for_proof_count",
    "operator_inbox",
    "operator_inbox_item_count",
    "operator_inbox_open_item_count",
    "operator_inbox_high_or_critical_item_count",
    "operator_inbox_postmortem_due_item_count",
    "operator_inbox_telegram_command_authority",
    "phase5_layer_b",
    "phase5_alpaca_paper_dry_run",
    "phase5_execution_adapter",
    "phase5_kill_switch",
    "phase5_paper_order_staging",
    "phase5_paper_submit_enablement",
    "phase5_prediction_market_adapter",
    "phase5_position_monitor",
    "phase5_paper_trade_drill",
    "phase5_certification",
    "phase5_phase6_handoff",
    "phase5_signal_review",
    "phase5_system_map",
    "phase6_learning_loop",
    "rs9_learning_loop",
    "rs9_learning_direction",
    "rs9_learning_proposal_count",
    "rs9_learning_blocked_proposal_count",
    "rs9_paperops_guarded_paper_trading_not_blocked",
    "rs10_final_paper_autonomy_certification",
    "rs10_final_paper_autonomy_certified",
    "rs10_guarded_paper_autonomy_allowed",
    "rs10_autonomy_currently_actionable",
    "rs10_current_blocker_count",
    "rs10_certification_blocker_count",
    "rs10_paper_submit_currently_allowed",
    "rs10_multiple_paper_trades_per_day_allowed_when_gates_pass",
    "phase5_telegram_notifier",
    "preference_mcp",
    "quant_oracle",
    "risk_gate",
    "telegram",
}

PAPER_LIVE_ACTIVATION_REQUIRED_FIELDS = {
    "approval_logged",
    "approval_scope",
    "approval_state",
    "alpaca_post_called_count",
    "boundary",
    "broker_post_called_count",
    "broker_scope",
    "daily_trade_cap",
    "event_log_event_count",
    "event_log_written",
    "forced_trades_allowed",
    "live_capital_enabled",
    "live_endpoint_allowed",
    "max_order_notional_gbp",
    "paper_live_activation_approved",
    "paper_live_mode",
    "paper_order_submission_allowed",
    "paper_trading_system_approval_logged",
    "phase7_proof_credit_allowed",
    "public_safe",
    "qctrl_consultation_required",
    "qctrl_direct_execution_allowed",
    "recorded",
    "schema_version",
    "stage",
    "status",
    "validation_error_count",
}

PAPER_LIVE_QCTRL_PRODUCT_ACCESS_REQUIRED_FIELDS = {
    "alpaca_post_allowed",
    "alpaca_post_called_count",
    "boundary",
    "broker_post_allowed",
    "broker_post_called_count",
    "event_log_event_count",
    "event_log_written",
    "execution_allowed",
    "forced_trades_allowed",
    "live_capital_enabled",
    "live_endpoint_allowed",
    "live_endpoint_called_count",
    "paper_consultation_ready",
    "paper_order_allowed",
    "phase7_proof_credit_allowed",
    "product_access_blocker",
    "product_access_state",
    "product_access_verified",
    "provider_call_attempted",
    "provider_call_count",
    "provider_call_succeeded",
    "public_safe",
    "qctrl_auth_status",
    "raw_provider_response_persisted",
    "raw_response_exposed",
    "recorded",
    "schema_version",
    "secret_value_exposed",
    "stage",
    "status",
    "validation_error_count",
}

PAPER_OPERATIONAL_MODE_REQUIRED_FIELDS = {
    "alpaca_post_called_count",
    "boundary",
    "broker_post_allowed",
    "broker_post_called_count",
    "env_file_edited",
    "event_log_event_count",
    "event_log_written",
    "execution_allowed",
    "forced_trades_allowed",
    "live_capital_enabled",
    "live_credentials_loaded",
    "live_endpoint_allowed",
    "live_endpoint_called_count",
    "paper_operational_flag_disabled",
    "paper_operational_mode_effective",
    "paper_operational_mode_enabled",
    "paper_order_allowed",
    "paper_order_submission_allowed",
    "phase7_proof_credit_allowed",
    "pt0_activation_approved",
    "pt1_product_access_checked",
    "public_safe",
    "qctrl_broker_post_allowed",
    "qctrl_direct_execution_allowed",
    "recorded",
    "runtime_artifact_override_enabled",
    "schema_version",
    "stage",
    "status",
    "validation_error_count",
}

PAPEROPS_30_DAY_OPERATIONS_REQUIRED_FIELDS = {
    "active_day_number",
    "automation_active",
    "automation_prompt_paperops_bound",
    "boundary",
    "calendar_days_remaining",
    "closed_proof_trade_count",
    "completed_calendar_day_count",
    "dashboard_mirror_public_safe",
    "dashboard_mirror_status",
    "event_log_event_count",
    "event_log_written",
    "live_capital_enabled",
    "paper_operational_cycle_command_count",
    "paper_operational_cycle_status",
    "phase7_proof_credit_allowed",
    "public_safe",
    "qualified_setup_count",
    "recorded",
    "run_id",
    "run_state",
    "scheduler_status",
    "schema_version",
    "stage",
    "status",
    "submitted_paper_order_count",
    "unsafe_write_counter_total",
    "validation_error_count",
}

PAPEROPS_QUALIFIED_SETUP_PRODUCTION_REQUIRED_FIELDS = {
    "boundary",
    "broker_post_called_count",
    "event_log_event_count",
    "event_log_written",
    "forced_trades_allowed",
    "live_capital_enabled",
    "paper_operational_mode_effective",
    "paper_order_submission_allowed",
    "phase7_demo_qualified_setup_count",
    "phase7_proof_credit_allowed",
    "production_candidate_count",
    "public_safe",
    "qctrl_paper_consultation_connected",
    "qctrl_paper_consultation_status",
    "qualified_setup_count",
    "qualified_setup_creation_forced",
    "qualified_setup_production_path_ready",
    "ready_to_stage_q7_order",
    "recorded",
    "schema_version",
    "source_qualified_setup_ledger_count",
    "stage",
    "status",
    "unsafe_write_counter_total",
    "validation_error_count",
}

PAPEROPS_AUTO_APPROVAL_STAGED_ORDER_REQUIRED_FIELDS = {
    "auto_approved_setup_count",
    "boundary",
    "broker_post_allowed",
    "broker_post_called_count",
    "event_log_event_count",
    "event_log_prewrite_written_count",
    "event_log_written",
    "forced_trades_allowed",
    "live_capital_enabled",
    "live_endpoint_allowed",
    "paper_order_submission_allowed",
    "phase7_proof_credit_allowed",
    "public_safe",
    "q7_auto_approval_artifact_mutation_performed",
    "q7_source_ledger_mutation_performed",
    "q7_staging_artifact_mutation_performed",
    "ready_for_paperops2_submit",
    "recorded",
    "schema_version",
    "source_pt3_path_ready",
    "source_pt3_status",
    "stage",
    "staged_order_count",
    "status",
    "unsafe_write_counter_total",
    "validation_error_count",
}

PAPEROPS_ALPACA_SUBMIT_ENABLEMENT_REQUIRED_FIELDS = {
    "alpaca_paper_submit_effective",
    "alpaca_paper_submit_enabled",
    "alpaca_post_called_count",
    "boundary",
    "broker_post_called_count",
    "env_file_edited",
    "event_log_event_count",
    "event_log_written",
    "explicit_submit_flag_required",
    "forced_trades_allowed",
    "live_capital_enabled",
    "live_endpoint_called_count",
    "paper_post_path_available",
    "paper_submit_runtime_enablement_enabled",
    "phase7_proof_credit_allowed",
    "pt4_ready_for_paperops2_submit",
    "pt4_staged_order_count",
    "public_safe",
    "recorded",
    "runtime_artifact_override_enabled",
    "schema_version",
    "settings_alpaca_paper_submit_enabled",
    "stage",
    "status",
    "unsafe_write_counter_total",
    "validation_error_count",
}

PAPEROPS_LIFECYCLE_POLLING_ENABLEMENT_REQUIRED_FIELDS = {
    "active_lifecycle_polling_enabled",
    "alpaca_paper_get_allowed",
    "boundary",
    "broker_get_called_count",
    "broker_post_allowed",
    "env_file_edited",
    "event_log_event_count",
    "event_log_written",
    "explicit_poll_flag_required",
    "forced_trades_allowed",
    "live_capital_enabled",
    "live_endpoint_called_count",
    "paper_broker_get_allowed",
    "paper_lifecycle_polling_effective",
    "paper_poll_path_available",
    "paperops_2_paper_post_path_available",
    "paperops_2_source_valid",
    "paperops_2_submitted_paper_order_count",
    "phase7_proof_credit_allowed",
    "public_safe",
    "recorded",
    "schema_version",
    "stage",
    "status",
    "unsafe_write_counter_total",
    "validation_error_count",
}

PAPEROPS_GUARDED_EXIT_ENABLEMENT_REQUIRED_FIELDS = {
    "alpaca_paper_exit_effective",
    "boundary",
    "broker_post_allowed",
    "env_file_edited",
    "event_log_event_count",
    "event_log_written",
    "explicit_exit_flag_required",
    "forced_trades_allowed",
    "guarded_paper_exit_enabled",
    "live_capital_enabled",
    "live_endpoint_called_count",
    "paper_exit_idle_until_open_position",
    "paper_exit_path_available",
    "paper_position_close_called_count",
    "paperops_3_open_position_count",
    "paperops_3_source_valid",
    "phase7_proof_credit_allowed",
    "position_close_allowed",
    "public_safe",
    "recorded",
    "runtime_artifact_override_enabled",
    "schema_version",
    "settings_alpaca_paper_exit_enabled",
    "stage",
    "status",
    "unsafe_write_counter_total",
    "validation_error_count",
}

PAPEROPS_ACTIVE_AUTOMATION_REQUIRED_FIELDS = {
    "active_paper_trading_automation_effective",
    "active_paper_trading_automation_enabled",
    "automation_active",
    "automation_prompt_active_trade_bound",
    "boundary",
    "direct_broker_shortcut_allowed",
    "event_log_event_count",
    "event_log_written",
    "forced_trades_allowed",
    "live_capital_enabled",
    "live_endpoint_called_count",
    "paper_endpoint_confirmed",
    "paper_exit_step_allowed",
    "paper_poll_step_allowed",
    "paper_submit_step_allowed",
    "phase7_proof_credit_allowed",
    "public_safe",
    "qctrl_consultation_hold_active",
    "qctrl_direct_execution_allowed",
    "recorded",
    "rs5_available_distinct_setup_count",
    "rs5_can_submit_multiple_today",
    "rs5_daily_target_blocks_additional_qualified_setups",
    "rs5_daily_target_is_minimum",
    "rs5_daily_target_policy",
    "rs5_guarded_submit_transport",
    "rs5_max_guarded_submit_attempts_per_run",
    "schema_version",
    "stage",
    "status",
    "unsafe_write_counter_total",
    "validation_error_count",
    "why_not_trading_now",
}

MISSION_PHASE5_LAYER_B_REQUIRED_FIELDS = {
    "boundary",
    "implementation_allowed",
    "implementation_plan_allowed",
    "layer",
    "nonapproval_blocker_count",
    "only_explicit_approval_blocks_plan",
    "orchestration_start_allowed",
    "phase",
    "readiness_blocker_count",
    "scope_count",
    "kill_switch_active_count",
    "kill_switch_blocking_count",
    "kill_switch_count",
    "kill_switch_event_log_written",
    "kill_switch_status",
    "execution_adapter_count",
    "execution_adapter_read_allowed_count",
    "execution_adapter_staging_allowed_count",
    "execution_adapter_status",
    "alpaca_paper_dry_run_blocked_count",
    "alpaca_paper_dry_run_broker_post_called",
    "alpaca_paper_dry_run_event_log_written",
    "alpaca_paper_dry_run_receipt_count",
    "alpaca_paper_dry_run_record_count",
    "alpaca_paper_dry_run_request_preview_count",
    "alpaca_paper_dry_run_status",
    "paper_order_staged_count",
    "paper_order_staging_blocked_count",
    "paper_order_staging_event_log_written",
    "paper_order_staging_record_count",
    "paper_order_staging_status",
    "paper_submit_approval_present",
    "paper_submit_approval_state",
    "paper_submit_broker_post_called",
    "paper_submit_enablement_record_count",
    "paper_submit_enablement_status",
    "paper_submit_event_log_written",
    "paper_submit_path_available_count",
    "prediction_market_adapter_status",
    "prediction_market_context_count",
    "prediction_market_event_log_written",
    "prediction_market_live_blocked_route_count",
    "prediction_market_preference_provenance_status",
    "prediction_market_preference_source_quorum_credit_allowed",
    "prediction_market_read_only_route_count",
    "prediction_market_route_count",
    "prediction_market_spend_allowed_count",
    "prediction_market_write_allowed_count",
    "telegram_notifier_alert_type_count",
    "telegram_notifier_command_path_enabled_count",
    "telegram_notifier_eligible_alert_count",
    "telegram_notifier_event_log_written",
    "telegram_notifier_live_send_allowed_count",
    "telegram_notifier_mode",
    "telegram_notifier_outbox_written_count",
    "telegram_notifier_queued_count",
    "telegram_notifier_send_gate",
    "telegram_notifier_status",
    "telegram_notifier_suppressed_count",
    "position_monitor_cancel_allowed_count",
    "position_monitor_closed_trade_count",
    "position_monitor_closed_trade_summary_count",
    "position_monitor_close_allowed_count",
    "position_monitor_event_log_written",
    "position_monitor_failed_reconciliation_count",
    "position_monitor_mirrored_order_count",
    "position_monitor_open_position_count",
    "position_monitor_position_record_count",
    "position_monitor_record_count",
    "position_monitor_resize_allowed_count",
    "position_monitor_status",
    "position_monitor_submitted_order_count",
    "position_monitor_write_authority_count",
    "signal_review_backend_truth_displayed_count",
    "signal_review_broker_write_allowed_count",
    "signal_review_decision_chain_count",
    "signal_review_event_log_written",
    "signal_review_governance_comment_event_count",
    "signal_review_kill_switch_action_event_count",
    "signal_review_live_capital_enabled_count",
    "signal_review_order_cancel_control_count",
    "signal_review_order_place_control_count",
    "signal_review_position_close_control_count",
    "signal_review_position_resize_control_count",
    "signal_review_prediction_market_write_allowed_count",
    "signal_review_record_count",
    "signal_review_status",
    "signal_review_trade_approval_control_count",
    "signal_review_ui_inferred_readiness_count",
    "paper_trade_drill_blocker_count",
    "paper_trade_drill_broker_post_called_count",
    "paper_trade_drill_closed_trade_count",
    "paper_trade_drill_complete",
    "paper_trade_drill_exit_gate_passed",
    "paper_trade_drill_implementation_ready",
    "paper_trade_drill_live_capital_enabled_count",
    "paper_trade_drill_open_position_count",
    "paper_trade_drill_postmortem_due_count",
    "paper_trade_drill_state",
    "paper_trade_drill_status",
    "paper_trade_drill_step_count",
    "paper_trade_drill_submit_approval_present",
    "paper_trade_drill_submit_path_available_count",
    "paper_trade_drill_submitted_order_count",
    "certification_blocker_count",
    "certification_closed_trade_count",
    "certification_input_gate_blocked_count",
    "certification_input_gate_count",
    "certification_input_gate_passed_count",
    "certification_live_capital_enabled_count",
    "certification_open_position_count",
    "certification_paper_trade_drill_complete",
    "certification_paper_trade_drill_exit_gate_passed",
    "certification_phase5_certified",
    "certification_phase5_exit_gate",
    "certification_phase6_handoff_allowed",
    "certification_phase7_planning_allowed",
    "certification_phase7_proof_credit_allowed",
    "certification_stage_status",
    "certification_status",
    "certification_submitted_paper_order_count",
    "phase6_handoff_blocker_count",
    "phase6_handoff_closed_trade_count",
    "phase6_handoff_event_log_written",
    "phase6_handoff_live_capital_enabled_count",
    "phase6_handoff_phase7_proof_credit_allowed",
    "phase6_handoff_postmortem_due_count",
    "phase6_handoff_recommended_next_stage",
    "phase6_handoff_state",
    "phase6_handoff_status",
    "phase6_knowledge_graph_write_allowed",
    "phase6_learning_loop_implementation_allowed",
    "phase6_learning_loop_plan_allowed",
    "phase6_learning_write_allowed",
    "phase6_required_module_count",
    "system_map_backend_parity_error_count",
    "system_map_dashboard_claims_trading_now",
    "system_map_event_log_written",
    "system_map_lane_count",
    "system_map_layer_b_node_count",
    "system_map_node_count",
    "system_map_status",
    "system_map_unsafe_control_count",
    "stage",
    "status",
}

MISSION_PHASE6_LEARNING_LOOP_REQUIRED_FIELDS = {
    "approval_state",
    "architect_blocked_recommendation_count",
    "architect_recommendation_count",
    "backend_derived",
    "backend_parity_error_count",
    "blocked_authority_count",
    "boundary",
    "broker_identifier_exposed_count",
    "display_derived_from_backend",
    "knowledge_graph_read_result_count",
    "learning_state",
    "live_capital_enabled",
    "local_path_exposed_count",
    "model_weight_proposal_count",
    "phase",
    "phase6_architect_policy_mutation_allowed",
    "phase6_knowledge_graph_write_allowed",
    "phase6_learning_write_allowed",
    "phase6_model_weight_update_allowed",
    "phase6_trust_score_update_allowed",
    "phase7_proof_credit_allowed",
    "postmortem_due_count",
    "postmortem_resolved_count",
    "raw_payload_exposed_count",
    "secret_ref_exposed_count",
    "shadow_replay_variant_count",
    "stage",
    "staged_graph_entry_count",
    "status",
    "trust_score_proposal_count",
    "ui_inferred_readiness_count",
    "unsafe_write_counter_total",
    "visibility_state",
}

MISSION_RS9_LEARNING_LOOP_REQUIRED_FIELDS = {
    "active_proposal_count",
    "blocked_authority_count",
    "blocked_proposal_count",
    "boundary",
    "broker_identifier_exposed_count",
    "broker_write_allowed",
    "dashboard_command_authority",
    "full_potential_state",
    "learning_direction",
    "learning_direction_reason",
    "live_capital_enabled",
    "local_path_exposed_count",
    "market_context_interpretation_mutation_allowed",
    "market_context_proposal_count",
    "next_action",
    "paperops_guarded_paper_trading_not_blocked",
    "phase",
    "phase7_proof_credit_allowed",
    "postmortem_due_count",
    "postmortem_resolved_count",
    "proposal_count",
    "raw_payload_exposed_count",
    "risk_sizing_mutation_allowed",
    "risk_sizing_proposal_count",
    "secret_ref_exposed_count",
    "source_trust_mutation_allowed",
    "source_trust_proposal_count",
    "stage",
    "status",
    "strategy_weight_mutation_allowed",
    "strategy_weight_proposal_count",
    "telegram_command_authority",
    "unsafe_write_counter_total",
    "worldview_lens_proposal_count",
    "worldview_lens_strength_mutation_allowed",
}

MISSION_RS10_FINAL_PAPER_AUTONOMY_REQUIRED_FIELDS = {
    "autonomy_currently_actionable",
    "boundary",
    "certification_blocker_count",
    "current_blocker_count",
    "current_blockers",
    "final_paper_autonomy_certified",
    "guarded_paper_autonomy_allowed",
    "multiple_paper_trades_per_day_allowed_when_gates_pass",
    "next_action",
    "paper_submit_currently_allowed",
    "phase",
    "safety_blocker_count",
    "stage",
    "status",
    "why_not_trading_now",
}

MISSION_PHASE3_READINESS_REQUIRED_FIELDS = {
    "autonomous_scheduler_enabled",
    "aws_braket_status",
    "boundary",
    "cloud_job_identifier_exposed_count",
    "configured_provider_count",
    "execution_allowed_count",
    "execution_readiness",
    "expected_provider_count",
    "hardware_scheduler_enabled_count",
    "hardware_submission_allowed_count",
    "hardware_submitted_count",
    "ibm_quantum_status",
    "latest_output_route_type",
    "latest_output_routing_status",
    "latest_output_storage_type",
    "latest_recommendation",
    "local_absolute_path_exposed_count",
    "local_simulator_backend",
    "local_simulator_mode",
    "local_simulator_status",
    "missing_optional_package_count",
    "missing_secret_count",
    "next_due_at",
    "paper_order_allowed_count",
    "phase",
    "provider_count",
    "provider_readiness_status",
    "public_safe",
    "qctrl_configured",
    "qctrl_live_probe_enabled",
    "qctrl_optimization_job_submitted",
    "qctrl_provider_call_count",
    "qctrl_status",
    "qiskit_aer_available",
    "qiskit_available",
    "raw_response_exposed_count",
    "readiness_scope",
    "scheduler_due",
    "scheduler_enabled",
    "scheduler_jobs_queued_count",
    "scheduler_jobs_submitted_count",
    "scheduler_status",
    "scheduler_would_queue_job_count",
    "schema_version",
    "secret_value_exposed_count",
    "status",
    "trade_candidate_created_count",
}

DURABLE_INGESTION_REQUIRED_FIELDS = {
    "boundary",
    "contract_status",
    "database_configured",
    "event_log_ingestion_event_count",
    "expected_source_count",
    "first_observed_at",
    "latest_observed_at",
    "missing_source_count",
    "missing_sources",
    "missing_tables",
    "next_step",
    "observation_count",
    "order_authority",
    "replay_status",
    "replayed_source_count",
    "schema_status",
    "schema_version",
    "service_status",
    "signal_authority",
    "status",
    "write_authority",
}

MISSION_DURABLE_REQUIRED_FIELDS = {
    "boundary",
    "contract_status",
    "expected_source_count",
    "latest_observed_at",
    "missing_source_count",
    "next_step",
    "observation_count",
    "order_authority",
    "replay_status",
    "replayed_source_count",
    "service_status",
    "signal_authority",
    "status",
    "write_authority",
}

MISSION_TRADE_REQUIRED_FIELDS = {
    "blocked_count",
    "blocked_trades",
    "boundary",
    "broker_post_called_count",
    "candidate_count",
    "execution_allowed_count",
    "observed_signal_count",
    "paper_order_submitted_count",
    "state",
    "summary",
    "top_candidates",
}

MISSION_PORTFOLIO_REQUIRED_FIELDS = {
    "account_scope",
    "boundary",
    "broker",
    "closed_trade_count",
    "connection_status",
    "current_balance_gbp",
    "drawdown_pct",
    "portfolio_value_source",
    "balance_ticker_broker_account_derived",
    "live_capital_enabled",
    "open_position_count",
    "open_positions",
    "order_count",
    "orders",
    "postmortem_due_count",
    "closed_trade_postmortem_coverage_count",
    "closed_trade_missing_postmortem_count",
    "paper_proof_ledger_verified_record_count",
    "mirror_trade_counted_for_proof_count",
    "total_pnl_gbp",
    "write_authority",
}

MISSION_SAFETY_REQUIRED_FIELDS = {
    "boundary",
    "broker_write_allowed",
    "forbidden_action_count",
    "hard_blocks",
    "live_capital_enabled",
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

COMMUNICATIONS_REQUIRED_FIELDS = {
    "boundary",
    "telegram",
    "telegram_codebase_upgrade",
    "telegram_daily_portfolio_digest",
    "telegram_intake",
}

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

TELEGRAM_DAILY_PORTFOLIO_DIGEST_REQUIRED_FIELDS = {
    "already_sent",
    "blocker_count",
    "blockers",
    "boundary",
    "broker_write_allowed",
    "daily_trade_count",
    "daily_trade_summaries",
    "delivery_after_local_time",
    "dry_run",
    "due_for_delivery",
    "enabled",
    "last_delivery_failure_category",
    "live_capital_enabled",
    "live_send_attempted",
    "live_send_succeeded",
    "local_date",
    "paper_order_allowed",
    "portfolio_balance_gbp",
    "portfolio_performance_pct",
    "portfolio_total_pnl_gbp",
    "schema_version",
    "status",
    "target",
    "telegram_command_path_enabled",
    "telegram_message_id_present",
    "timezone",
}

TELEGRAM_CODEBASE_UPGRADE_REQUIRED_FIELDS = {
    "aliases",
    "already_sent",
    "blocker_count",
    "blockers",
    "boundary",
    "broker_write_allowed",
    "dashboard_changed_file_count",
    "dashboard_commit_short",
    "dashboard_dirty",
    "benefits",
    "deploy_allowed",
    "details",
    "deployment_url",
    "dry_run",
    "enabled",
    "last_delivery_failure_category",
    "live_capital_enabled",
    "live_send_attempted",
    "live_send_succeeded",
    "paper_order_allowed",
    "repository_write_allowed",
    "root_changed_file_count",
    "root_commit_short",
    "root_dirty",
    "schema_version",
    "source",
    "status",
    "summary",
    "target",
    "telegram_command_path_enabled",
    "telegram_message_id_present",
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

TELEGRAM_INTAKE_REQUIRED_FIELDS = {
    "bot_configured",
    "boundary",
    "broker_write_allowed",
    "enabled",
    "execution_allowed",
    "ignored_message_count",
    "latest_intake_type",
    "latest_observed_at",
    "latest_status",
    "live_capital_enabled",
    "paper_order_allowed",
    "polling_mode",
    "recent_records",
    "recent_strategy_considerations",
    "recent_world_events",
    "record_count",
    "research_triage_packet_count",
    "risk_handoff_allowed",
    "schema_version",
    "status",
    "strategy_consideration_count",
    "telegram_command_authority",
    "trade_candidate_creation_allowed",
    "world_event_datapoint_count",
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
    ensure_sample_telegram_inbound_intake(settings)
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
    print(
        "cockpit_status_research_goal_status="
        f"{payload['cognition'].get('research_goals', {}).get('status')}"
    )
    print(
        "cockpit_status_research_goal_active_count="
        f"{payload['cognition'].get('research_goals', {}).get('active_goal_count', 0)}"
    )
    print(f"cockpit_status_research_goal_record_count={len(payload['cognition'].get('research_goal_records', []))}")
    print(
        "cockpit_status_market_context_status="
        f"{payload['cognition'].get('market_context', {}).get('status')}"
    )
    print(
        "cockpit_status_market_context_packet_count="
        f"{payload['cognition'].get('market_context', {}).get('packet_count', 0)}"
    )
    print(
        "cockpit_status_market_context_average_source_quality_score="
        f"{payload['cognition'].get('market_context', {}).get('average_source_quality_score', 0)}"
    )
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
    print(f"cockpit_status_execution_policy_status={payload.get('execution_policy', {}).get('status')}")
    print(f"cockpit_status_execution_policy_review_count={payload.get('execution_policy', {}).get('review_count')}")
    print(f"cockpit_status_staged_paper_order_status={payload.get('staged_paper_order', {}).get('status')}")
    print(f"cockpit_status_staged_paper_order_review_count={payload.get('staged_paper_order', {}).get('review_count')}")
    print(f"cockpit_status_broker_reconciliation_status={payload.get('broker_reconciliation', {}).get('status')}")
    print(f"cockpit_status_broker_reconciliation_review_count={payload.get('broker_reconciliation', {}).get('review_count')}")
    print(f"cockpit_status_paper_submit_receipt_status={payload.get('paper_submit_receipt', {}).get('status')}")
    print(f"cockpit_status_paper_submit_receipt_review_count={payload.get('paper_submit_receipt', {}).get('review_count')}")
    print(f"cockpit_status_quantum_oracle_status={payload.get('quantum_oracle', {}).get('status')}")
    print(f"cockpit_status_quantum_oracle_result_count={payload.get('quantum_oracle', {}).get('result_count')}")
    print(f"cockpit_status_quantum_oracle_backend={payload.get('quantum_oracle', {}).get('latest_backend')}")
    print(
        "cockpit_status_quantum_oracle_mode="
        f"{payload.get('quantum_oracle', {}).get('latest_local_simulation_mode')}"
    )
    fire_opal_ibm = payload.get("qctrl_fire_opal_ibm_readiness", {})
    print(f"cockpit_status_fire_opal_ibm_status={fire_opal_ibm.get('status')}")
    print(
        "cockpit_status_fire_opal_ibm_fire_opal_access="
        f"{fire_opal_ibm.get('fire_opal_product_access_verified')}"
    )
    print(
        "cockpit_status_fire_opal_ibm_qiskit_runtime="
        f"{fire_opal_ibm.get('qiskit_ibm_runtime_importable')}"
    )
    print(
        "cockpit_status_fire_opal_ibm_blocker="
        f"{fire_opal_ibm.get('blocker')}"
    )
    print(f"cockpit_status_mission_control_status={payload.get('mission_control', {}).get('status')}")
    print(f"cockpit_status_mission_control_headline={payload.get('mission_control', {}).get('headline')}")
    print(
        "cockpit_status_mission_logged_in_source_count="
        f"{payload.get('mission_control', {}).get('data_sources', {}).get('logged_in_count')}"
    )
    print(
        "cockpit_status_mission_candidate_count="
        f"{payload.get('mission_control', {}).get('trade_intent', {}).get('candidate_count')}"
    )
    print(f"cockpit_status_worldview_status={payload['decision_philosophy'].get('status')}")
    print(f"cockpit_status_worldview_claim_count={payload['decision_philosophy'].get('claim_count')}")
    print(
        "cockpit_status_worldview_foundational_prior_count="
        f"{payload['decision_philosophy'].get('foundational_prior_count')}"
    )
    print(f"cockpit_status_forbidden_action_count={len(payload['forbidden_actions'])}")
    print(f"cockpit_status_tradingview_mcp_status={payload['tradingview_mcp'].get('status')}")
    print(f"cockpit_status_tradingview_mcp_connected={payload['tradingview_mcp'].get('connected')}")
    print(
        "cockpit_status_tradingview_mcp_context_count="
        f"{payload['tradingview_mcp'].get('technical_context_count')}"
    )
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
    print(f"cockpit_status_telegram_inbound_status={payload['communications']['telegram_intake'].get('status')}")
    print(
        "cockpit_status_telegram_inbound_world_event_datapoint_count="
        f"{payload['communications']['telegram_intake'].get('world_event_datapoint_count')}"
    )
    print(
        "cockpit_status_telegram_inbound_strategy_consideration_count="
        f"{payload['communications']['telegram_intake'].get('strategy_consideration_count')}"
    )
    print(
        "cockpit_status_telegram_inbound_research_triage_packet_count="
        f"{payload['communications']['telegram_intake'].get('research_triage_packet_count')}"
    )
    print(f"cockpit_status_live_bridge_status={payload['live_bridge'].get('status')}")
    print(f"cockpit_status_live_bridge_endpoint={payload['live_bridge'].get('endpoint')}")
    print(f"cockpit_status_durable_ingestion_status={payload.get('durable_ingestion', {}).get('status')}")
    print(f"cockpit_status_durable_ingestion_contract_status={payload.get('durable_ingestion', {}).get('contract_status')}")
    print(f"cockpit_status_durable_ingestion_replay_status={payload.get('durable_ingestion', {}).get('replay_status')}")
    print(
        "cockpit_status_durable_ingestion_replayed_source_count="
        f"{payload.get('durable_ingestion', {}).get('replayed_source_count')}"
    )
    print(f"cockpit_status_yahoo_finance_status={payload.get('yahoo_finance', {}).get('status')}")
    print(f"cockpit_status_yahoo_finance_enabled={payload.get('yahoo_finance', {}).get('enabled')}")
    print(
        "cockpit_status_yahoo_finance_symbol_allowlist_count="
        f"{payload.get('yahoo_finance', {}).get('symbol_allowlist_count')}"
    )
    print(
        "cockpit_status_yahoo_finance_degraded_reason="
        f"{payload.get('yahoo_finance', {}).get('degraded_reason')}"
    )
    print(f"cockpit_status_preference_mcp_status={payload.get('preference_mcp', {}).get('status')}")
    print(f"cockpit_status_preference_mcp_enabled={payload.get('preference_mcp', {}).get('enabled')}")
    print(
        "cockpit_status_preference_mcp_identity_status="
        f"{payload.get('preference_mcp', {}).get('identity_status')}"
    )
    print(
        "cockpit_status_preference_mcp_quota_status="
        f"{payload.get('preference_mcp', {}).get('quota_status')}"
    )
    print(
        "cockpit_status_preference_mcp_catalog_status="
        f"{payload.get('preference_mcp', {}).get('catalog_status')}"
    )
    print(
        "cockpit_status_preference_mcp_domain_pack_count="
        f"{payload.get('preference_mcp', {}).get('approved_domain_pack_count')}"
    )
    print(
        "cockpit_status_preference_mcp_provenance_status="
        f"{payload.get('preference_mcp', {}).get('provenance_status')}"
    )
    print(
        "cockpit_status_preference_mcp_shadow_context_status="
        f"{payload.get('preference_mcp', {}).get('shadow_context_status')}"
    )
    print(
        "cockpit_status_preference_mcp_source_promotion_status="
        f"{payload.get('preference_mcp', {}).get('source_promotion_status')}"
    )
    print(
        "cockpit_status_preference_mcp_source_promotion_decision_count="
        f"{payload.get('preference_mcp', {}).get('source_promotion_decision_count')}"
    )
    print(
        "cockpit_status_preference_mcp_source_promotion_promoted_count="
        f"{payload.get('preference_mcp', {}).get('source_promotion_promoted_decision_count')}"
    )
    print(
        "cockpit_status_preference_mcp_degraded_reason="
        f"{payload.get('preference_mcp', {}).get('degraded_reason')}"
    )
    phase4_strategy = payload.get("phase4_strategy", {})
    phase5_readiness = payload.get("phase5_layer_b_readiness", {})
    phase5_kill_switch = payload.get("phase5_kill_switch_ledger", {})
    phase5_execution_adapter = payload.get("phase5_execution_adapter_status", {})
    phase5_paper_order_staging = payload.get("phase5_paper_order_staging_gate", {})
    phase5_alpaca_dry_run = payload.get("phase5_alpaca_paper_dry_run", {})
    phase5_paper_submit_enablement = payload.get("phase5_paper_submit_enablement_gate", {})
    phase5_prediction_market_adapter = payload.get("phase5_prediction_market_adapter", {})
    phase5_telegram_notifier = payload.get("phase5_telegram_notifier", {})
    phase5_position_monitor = payload.get("phase5_position_monitor", {})
    phase5_signal_review = payload.get("phase5_signal_review", {})
    phase5_paper_trade_drill = payload.get("phase5_paper_trade_drill", {})
    phase5_certification = payload.get("phase5_certification", {})
    phase5_phase6_handoff = payload.get("phase5_phase6_handoff", {})
    phase5_system_map = payload.get("phase5_system_map", {})
    phase6_learning_loop = payload.get("phase6_learning_loop", {})
    rs9_learning_loop = payload.get("rs9_learning_loop", {})
    rs10_final_paper_autonomy = payload.get(
        "rs10_final_paper_autonomy_certification",
        {},
    )
    phase6_certification = payload.get("phase6_certification", {})
    paper_live_activation = payload.get("paper_live_activation", {})
    paper_live_qctrl_product_access = payload.get("paper_live_qctrl_product_access", {})
    paper_operational_mode = payload.get("paper_operational_mode", {})
    paperops_alpaca_submit_enablement = payload.get(
        "paperops_alpaca_paper_submit_enablement",
        {},
    )
    paperops_alpaca_paper_post = payload.get("paperops_alpaca_paper_post", {})
    paperops_first_week_mandate = payload.get(
        "paperops_first_week_paper_trade_mandate",
        {},
    )
    paperops_lifecycle_polling_enablement = payload.get(
        "paperops_paper_lifecycle_polling_enablement",
        {},
    )
    paperops_paper_lifecycle_poller = payload.get("paperops_paper_lifecycle_poller", {})
    paperops_guarded_exit_enablement = payload.get(
        "paperops_guarded_paper_exit_enablement",
        {},
    )
    paperops_paper_exit_path = payload.get("paperops_paper_exit_path", {})
    paperops_notification_review = payload.get("paperops_notification_review", {})
    paperops_30_day_operations = payload.get("paperops_30_day_operations", {})
    paperops_cockpit_notification = payload.get(
        "paperops_cockpit_notification_upgrade",
        {},
    )
    paper_live_certification = payload.get("paper_live_certification", {})
    paperops_active_automation = payload.get(
        "paperops_active_paper_trading_automation",
        {},
    )
    paper_authority = payload.get("paper_authority_reconciliation", {})
    paper_lifecycle_postmortem = payload.get(
        "paper_lifecycle_portfolio_postmortem",
        {},
    )
    operator_inbox = payload.get("operator_inbox", {})
    paperops_qualified_setup_production = payload.get(
        "paperops_qualified_setup_production",
        {},
    )
    paperops_auto_approval_staged_order = payload.get(
        "paperops_auto_approval_staged_order",
        {},
    )
    phase4_approval = phase4_strategy.get("approval_event", {})
    phase4_toggles = phase4_strategy.get("strategy_toggles", {})
    phase4_certification = phase4_strategy.get("certification", {})
    phase4_preference_gate = phase4_certification.get(
        "preference_mcp_certification_gate",
        {},
    )
    print(f"cockpit_status_phase4_stage={phase4_strategy.get('stage')}")
    print(
        "cockpit_status_paper_live_activation_status="
        f"{paper_live_activation.get('status')}"
    )
    print(
        "cockpit_status_rs6_lifecycle_portfolio_postmortem_status="
        f"{paper_lifecycle_postmortem.get('status')}"
    )
    print(
        "cockpit_status_rs6_portfolio_value_source="
        f"{paper_lifecycle_postmortem.get('portfolio_value_source')}"
    )
    print(
        "cockpit_status_rs6_balance_ticker_broker_account_derived="
        f"{paper_lifecycle_postmortem.get('balance_ticker_broker_account_derived')}"
    )
    print(
        "cockpit_status_rs6_closed_trade_postmortem_coverage_count="
        f"{paper_lifecycle_postmortem.get('closed_trade_postmortem_coverage_count')}"
    )
    print(
        "cockpit_status_rs6_closed_trade_missing_postmortem_count="
        f"{paper_lifecycle_postmortem.get('closed_trade_missing_postmortem_count')}"
    )
    print(
        "cockpit_status_rs6_proof_verified_record_count="
        f"{paper_lifecycle_postmortem.get('paper_proof_ledger_verified_record_count')}"
    )
    print(
        "cockpit_status_rs7_operator_inbox_status="
        f"{operator_inbox.get('status')}"
    )
    print(
        "cockpit_status_rs7_operator_inbox_item_count="
        f"{operator_inbox.get('item_count')}"
    )
    print(
        "cockpit_status_rs7_operator_inbox_open_item_count="
        f"{operator_inbox.get('open_item_count')}"
    )
    print(
        "cockpit_status_rs7_operator_inbox_postmortem_due_item_count="
        f"{operator_inbox.get('postmortem_due_item_count')}"
    )
    print(
        "cockpit_status_paper_live_activation_approved="
        f"{paper_live_activation.get('paper_live_activation_approved')}"
    )
    print(
        "cockpit_status_paper_live_activation_system_approval_logged="
        f"{paper_live_activation.get('paper_trading_system_approval_logged')}"
    )
    print(
        "cockpit_status_paper_live_activation_submit_allowed="
        f"{paper_live_activation.get('paper_order_submission_allowed')}"
    )
    print(
        "cockpit_status_paper_live_qctrl_product_access_status="
        f"{paper_live_qctrl_product_access.get('status')}"
    )
    print(
        "cockpit_status_paper_live_qctrl_product_access_verified="
        f"{paper_live_qctrl_product_access.get('product_access_verified')}"
    )
    print(
        "cockpit_status_paper_live_qctrl_provider_call_count="
        f"{paper_live_qctrl_product_access.get('provider_call_count')}"
    )
    print(
        "cockpit_status_paper_live_qctrl_product_access_blocker="
        f"{paper_live_qctrl_product_access.get('product_access_blocker')}"
    )
    print(
        "cockpit_status_paper_operational_mode_status="
        f"{paper_operational_mode.get('status')}"
    )
    print(
        "cockpit_status_paper_operational_mode_effective="
        f"{paper_operational_mode.get('paper_operational_mode_effective')}"
    )
    print(
        "cockpit_status_paper_operational_mode_settings_flag="
        f"{paper_operational_mode.get('settings_paper_operational_enabled')}"
    )
    print(
        "cockpit_status_paper_operational_mode_runtime_override="
        f"{paper_operational_mode.get('runtime_artifact_override_enabled')}"
    )
    print(
        "cockpit_status_paper_operational_mode_submit_allowed="
        f"{paper_operational_mode.get('paper_order_submission_allowed')}"
    )
    print(
        "cockpit_status_paper_operational_mode_broker_post_called_count="
        f"{paper_operational_mode.get('broker_post_called_count')}"
    )
    print(
        "cockpit_status_paperops_alpaca_submit_enablement_status="
        f"{paperops_alpaca_submit_enablement.get('status')}"
    )
    print(
        "cockpit_status_paperops_alpaca_submit_enablement_effective="
        f"{paperops_alpaca_submit_enablement.get('alpaca_paper_submit_effective')}"
    )
    print(
        "cockpit_status_paperops_alpaca_submit_enablement_path_available="
        f"{paperops_alpaca_submit_enablement.get('paper_post_path_available')}"
    )
    print(
        "cockpit_status_paperops_alpaca_submit_enablement_pt4_staged_order_count="
        f"{paperops_alpaca_submit_enablement.get('pt4_staged_order_count')}"
    )
    print(
        "cockpit_status_paperops_alpaca_submit_enablement_broker_post_called_count="
        f"{paperops_alpaca_submit_enablement.get('broker_post_called_count')}"
    )
    print(
        "cockpit_status_paperops_alpaca_submit_enablement_alpaca_post_called_count="
        f"{paperops_alpaca_submit_enablement.get('alpaca_post_called_count')}"
    )
    print(
        "cockpit_status_paperops_lifecycle_polling_enablement_status="
        f"{paperops_lifecycle_polling_enablement.get('status')}"
    )
    print(
        "cockpit_status_paperops_lifecycle_polling_enablement_active="
        f"{paperops_lifecycle_polling_enablement.get('active_lifecycle_polling_enabled')}"
    )
    print(
        "cockpit_status_paperops_lifecycle_polling_enablement_path_available="
        f"{paperops_lifecycle_polling_enablement.get('paper_poll_path_available')}"
    )
    print(
        "cockpit_status_paperops_lifecycle_polling_enablement_submitted_order_count="
        f"{paperops_lifecycle_polling_enablement.get('paperops_2_submitted_paper_order_count')}"
    )
    print(
        "cockpit_status_paperops_lifecycle_polling_enablement_broker_get_called_count="
        f"{paperops_lifecycle_polling_enablement.get('broker_get_called_count')}"
    )
    print(
        "cockpit_status_paperops_guarded_exit_enablement_status="
        f"{paperops_guarded_exit_enablement.get('status')}"
    )
    print(
        "cockpit_status_paperops_guarded_exit_enablement_effective="
        f"{paperops_guarded_exit_enablement.get('alpaca_paper_exit_effective')}"
    )
    print(
        "cockpit_status_paperops_guarded_exit_enablement_path_available="
        f"{paperops_guarded_exit_enablement.get('paper_exit_path_available')}"
    )
    print(
        "cockpit_status_paperops_guarded_exit_enablement_open_position_count="
        f"{paperops_guarded_exit_enablement.get('paperops_3_open_position_count')}"
    )
    print(
        "cockpit_status_paperops_guarded_exit_enablement_close_called_count="
        f"{paperops_guarded_exit_enablement.get('paper_position_close_called_count')}"
    )
    print(
        "cockpit_status_paperops_lifecycle_poller_status="
        f"{paperops_paper_lifecycle_poller.get('status')}"
    )
    print(
        "cockpit_status_paperops_lifecycle_poller_source_submitted_order_count="
        f"{paperops_paper_lifecycle_poller.get('source_submitted_paper_order_count')}"
    )
    print(
        "cockpit_status_paperops_lifecycle_poller_order_poll_called_count="
        f"{paperops_paper_lifecycle_poller.get('paper_order_poll_called_count')}"
    )
    print(
        "cockpit_status_paperops_lifecycle_poller_live_endpoint_called_count="
        f"{paperops_paper_lifecycle_poller.get('live_endpoint_called_count')}"
    )
    print(
        "cockpit_status_paperops_exit_path_status="
        f"{paperops_paper_exit_path.get('status')}"
    )
    print(
        "cockpit_status_paperops_exit_path_open_position_readback_count="
        f"{paperops_paper_exit_path.get('open_position_readback_count')}"
    )
    print(
        "cockpit_status_paperops_exit_path_close_called_count="
        f"{paperops_paper_exit_path.get('paper_position_close_called_count')}"
    )
    print(
        "cockpit_status_paperops_exit_path_live_endpoint_called_count="
        f"{paperops_paper_exit_path.get('live_endpoint_called_count')}"
    )
    print(
        "cockpit_status_paperops_notification_review_status="
        f"{paperops_notification_review.get('status')}"
    )
    print(
        "cockpit_status_paperops_notification_review_record_count="
        f"{paperops_notification_review.get('notification_record_count')}"
    )
    print(
        "cockpit_status_paperops_notification_review_live_send_allowed_count="
        f"{paperops_notification_review.get('live_send_allowed_count')}"
    )
    print(
        "cockpit_status_paperops_notification_review_command_path_enabled_count="
        f"{paperops_notification_review.get('telegram_command_path_enabled_count')}"
    )
    print(
        "cockpit_status_paperops_30_day_operations_status="
        f"{paperops_30_day_operations.get('status')}"
    )
    print(
        "cockpit_status_paperops_30_day_operations_scheduler_status="
        f"{paperops_30_day_operations.get('scheduler_status')}"
    )
    print(
        "cockpit_status_paperops_30_day_operations_active_day_number="
        f"{paperops_30_day_operations.get('active_day_number')}"
    )
    print(
        "cockpit_status_paperops_30_day_operations_cycle_status="
        f"{paperops_30_day_operations.get('paper_operational_cycle_status')}"
    )
    print(
        "cockpit_status_paperops_30_day_operations_dashboard_public_safe="
        f"{paperops_30_day_operations.get('dashboard_mirror_public_safe')}"
    )
    print(
        "cockpit_status_paperops_30_day_operations_unsafe_write_counter_total="
        f"{paperops_30_day_operations.get('unsafe_write_counter_total')}"
    )
    print(
        "cockpit_status_paperops_cockpit_notification_status="
        f"{paperops_cockpit_notification.get('status')}"
    )
    print(
        "cockpit_status_paperops_cockpit_notification_ready="
        f"{paperops_cockpit_notification.get('cockpit_upgrade_ready')}"
    )
    print(
        "cockpit_status_paperops_cockpit_notification_notification_ready="
        f"{paperops_cockpit_notification.get('notification_upgrade_ready')}"
    )
    print(
        "cockpit_status_paperops_cockpit_notification_readout_count="
        f"{paperops_cockpit_notification.get('fund_manager_readout_count')}"
    )
    print(
        "cockpit_status_paperops_cockpit_notification_qctrl_hold="
        f"{paperops_cockpit_notification.get('qctrl_hold_visible')}"
    )
    print(
        "cockpit_status_paperops_cockpit_notification_submit_visible_as_held="
        f"{paperops_cockpit_notification.get('paper_submit_visible_as_held')}"
    )
    print(
        "cockpit_status_paperops_cockpit_notification_live_send_allowed_count="
        f"{paperops_cockpit_notification.get('notification_live_send_allowed_count')}"
    )
    print(
        "cockpit_status_paperops_cockpit_notification_unsafe_write_counter_total="
        f"{paperops_cockpit_notification.get('unsafe_write_counter_total')}"
    )
    print(
        "cockpit_status_paper_live_certification_status="
        f"{paper_live_certification.get('status')}"
    )
    print(
        "cockpit_status_paper_live_control_plane_certified="
        f"{paper_live_certification.get('paper_live_control_plane_certified')}"
    )
    print(
        "cockpit_status_paper_live_certified="
        f"{paper_live_certification.get('paper_live_certified')}"
    )
    print(
        "cockpit_status_paper_live_operation_allowed="
        f"{paper_live_certification.get('paper_live_operation_allowed')}"
    )
    print(
        "cockpit_status_paper_live_unattended_delegation_enabled="
        f"{paper_live_certification.get('paper_live_unattended_execution_delegation_enabled')}"
    )
    print(
        "cockpit_status_paper_live_unattended_delegation_reason="
        f"{paper_live_certification.get('paper_live_unattended_execution_delegation_reason')}"
    )
    print(
        "cockpit_status_paper_live_certification_blocker_count="
        f"{paper_live_certification.get('certification_blocker_count')}"
    )
    print(
        "cockpit_status_paper_live_qctrl_hold_active="
        f"{paper_live_certification.get('qctrl_hold_active')}"
    )
    print(
        "cockpit_status_paper_live_qctrl_hold_visible="
        f"{paper_live_certification.get('qctrl_hold_visible')}"
    )
    print(
        "cockpit_status_paper_live_submit_visible_as_held="
        f"{paper_live_certification.get('paper_submit_visible_as_held')}"
    )
    print(
        "cockpit_status_paper_live_phase7_30_day_run_complete="
        f"{paper_live_certification.get('phase7_30_day_run_complete')}"
    )
    print(
        "cockpit_status_paper_live_phase7_demo_proof_certified="
        f"{paper_live_certification.get('phase7_demo_proof_certified')}"
    )
    print(
        "cockpit_status_paper_live_unsafe_write_counter_total="
        f"{paper_live_certification.get('unsafe_write_counter_total')}"
    )
    print(
        "cockpit_status_paperops_active_automation_status="
        f"{paperops_active_automation.get('status')}"
    )
    print(
        "cockpit_status_paperops_active_automation_enabled="
        f"{paperops_active_automation.get('active_paper_trading_automation_enabled')}"
    )
    print(
        "cockpit_status_paperops_active_automation_prompt_bound="
        f"{paperops_active_automation.get('automation_prompt_active_trade_bound')}"
    )
    print(
        "cockpit_status_paperops_active_automation_qctrl_hold="
        f"{paperops_active_automation.get('qctrl_consultation_hold_active')}"
    )
    print(
        "cockpit_status_paperops_active_automation_submit_allowed="
        f"{paperops_active_automation.get('paper_submit_step_allowed')}"
    )
    print(
        "cockpit_status_paperops_active_automation_unattended_delegation_enabled="
        f"{paperops_active_automation.get('unattended_paper_execution_delegation_enabled')}"
    )
    print(
        "cockpit_status_paperops_active_automation_unattended_delegation_reason="
        f"{paperops_active_automation.get('unattended_paper_execution_delegation_reason')}"
    )
    print(
        "cockpit_status_paperops_active_automation_fresh_submit_count="
        f"{paperops_active_automation.get('paperops2_fresh_eligible_submit_record_count')}"
    )
    print(
        "cockpit_status_paperops_active_automation_duplicate_submit_count="
        f"{paperops_active_automation.get('paperops2_duplicate_submit_record_count')}"
    )
    print(
        "cockpit_status_paperops_active_automation_idempotency_ledger_active="
        f"{paperops_active_automation.get('paperops2_idempotency_ledger_active')}"
    )
    print(
        "cockpit_status_paperops_active_automation_rs5_daily_target_policy="
        f"{paperops_active_automation.get('rs5_daily_target_policy')}"
    )
    print(
        "cockpit_status_paperops_active_automation_rs5_max_guarded_submit_attempts_per_run="
        f"{paperops_active_automation.get('rs5_max_guarded_submit_attempts_per_run')}"
    )
    print(
        "cockpit_status_paperops_active_automation_rs5_available_distinct_setup_count="
        f"{paperops_active_automation.get('rs5_available_distinct_setup_count')}"
    )
    print(
        "cockpit_status_paperops_active_automation_rs5_can_submit_multiple_today="
        f"{paperops_active_automation.get('rs5_can_submit_multiple_today')}"
    )
    print(
        "cockpit_status_paperops_active_automation_why_not_trading_now="
        f"{paperops_active_automation.get('why_not_trading_now')}"
    )
    print(
        "cockpit_status_paper_authority_reconciliation_status="
        f"{paper_authority.get('status')}"
    )
    print(
        "cockpit_status_paper_authority_reconciliation_paper_authorized="
        f"{paper_authority.get('paper_authorized')}"
    )
    print(
        "cockpit_status_paper_authority_reconciliation_full_potential_state="
        f"{paper_authority.get('full_potential_state')}"
    )
    print(
        "cockpit_status_paper_authority_reconciliation_current_blockers="
        f"{','.join(paper_authority.get('current_blockers', []) or [])}"
    )
    print(
        "cockpit_status_paper_authority_reconciliation_safety_blockers="
        f"{','.join(paper_authority.get('safety_blockers', []) or [])}"
    )
    print(
        "cockpit_status_paperops_first_week_mandate_status="
        f"{paperops_first_week_mandate.get('status')}"
    )
    print(
        "cockpit_status_paperops_first_week_mandate_active="
        f"{paperops_first_week_mandate.get('active')}"
    )
    print(
        "cockpit_status_paperops_first_week_mandate_day_number="
        f"{paperops_first_week_mandate.get('day_number')}"
    )
    print(
        "cockpit_status_paperops_first_week_mandate_daily_target_trade_count="
        f"{paperops_first_week_mandate.get('daily_target_trade_count')}"
    )
    print(
        "cockpit_status_paperops_first_week_mandate_minimum_notional_usd="
        f"{paperops_first_week_mandate.get('minimum_notional_usd')}"
    )
    print(
        "cockpit_status_paperops_first_week_mandate_daily_ready_submit_count="
        f"{paperops_first_week_mandate.get('daily_ready_submit_count')}"
    )
    print(
        "cockpit_status_paperops_first_week_mandate_daily_submitted_count="
        f"{paperops_first_week_mandate.get('daily_submitted_count')}"
    )
    print(
        "cockpit_status_paperops_active_automation_poll_allowed="
        f"{paperops_active_automation.get('paper_poll_step_allowed')}"
    )
    print(
        "cockpit_status_paperops_active_automation_exit_allowed="
        f"{paperops_active_automation.get('paper_exit_step_allowed')}"
    )
    print(
        "cockpit_status_paperops_active_automation_live_endpoint_called_count="
        f"{paperops_active_automation.get('live_endpoint_called_count')}"
    )
    print(
        "cockpit_status_paperops_active_automation_unsafe_write_counter_total="
        f"{paperops_active_automation.get('unsafe_write_counter_total')}"
    )
    print(
        "cockpit_status_paperops_qualified_setup_production_status="
        f"{paperops_qualified_setup_production.get('status')}"
    )
    print(
        "cockpit_status_paperops_qualified_setup_production_candidate_count="
        f"{paperops_qualified_setup_production.get('production_candidate_count')}"
    )
    print(
        "cockpit_status_paperops_qualified_setup_production_qualified_count="
        f"{paperops_qualified_setup_production.get('qualified_setup_count')}"
    )
    print(
        "cockpit_status_paperops_qualified_setup_production_ready_to_stage="
        f"{paperops_qualified_setup_production.get('ready_to_stage_q7_order')}"
    )
    print(
        "cockpit_status_paperops_qualified_setup_production_qctrl_status="
        f"{paperops_qualified_setup_production.get('qctrl_paper_consultation_status')}"
    )
    print(
        "cockpit_status_paperops_qualified_setup_production_unsafe_write_counter_total="
        f"{paperops_qualified_setup_production.get('unsafe_write_counter_total')}"
    )
    print(
        "cockpit_status_paperops_auto_approval_staged_order_status="
        f"{paperops_auto_approval_staged_order.get('status')}"
    )
    print(
        "cockpit_status_paperops_auto_approval_staged_order_auto_approved_count="
        f"{paperops_auto_approval_staged_order.get('auto_approved_setup_count')}"
    )
    print(
        "cockpit_status_paperops_auto_approval_staged_order_staged_count="
        f"{paperops_auto_approval_staged_order.get('staged_order_count')}"
    )
    print(
        "cockpit_status_paperops_auto_approval_staged_order_ready_for_paperops2="
        f"{paperops_auto_approval_staged_order.get('ready_for_paperops2_submit')}"
    )
    print(
        "cockpit_status_paperops_auto_approval_staged_order_submit_allowed="
        f"{paperops_auto_approval_staged_order.get('paper_order_submission_allowed')}"
    )
    print(
        "cockpit_status_paperops_auto_approval_staged_order_unsafe_write_counter_total="
        f"{paperops_auto_approval_staged_order.get('unsafe_write_counter_total')}"
    )
    print(f"cockpit_status_phase4_stage_status={phase4_strategy.get('stage_status')}")
    print(
        "cockpit_status_phase4_strategy_document_status="
        f"{phase4_strategy.get('strategy_document_status')}"
    )
    print(f"cockpit_status_phase4_approval_state={phase4_strategy.get('approval_event_status')}")
    print(f"cockpit_status_phase4_approval_logged={phase4_approval.get('approval_logged')}")
    print(f"cockpit_status_phase4_required_amendment_count={phase4_approval.get('required_amendment_count')}")
    print(f"cockpit_status_phase4_toggle_count={phase4_strategy.get('toggle_count')}")
    print(
        "cockpit_status_phase4_approved_shadow_toggle_count="
        f"{phase4_strategy.get('approved_shadow_strategy_toggle_count')}"
    )
    print(f"cockpit_status_phase4_certification_allowed={phase4_strategy.get('phase4_certification_allowed')}")
    print(f"cockpit_status_phase4_certification_status={phase4_strategy.get('certification_status')}")
    print(f"cockpit_status_phase4_certified={phase4_strategy.get('phase4_certified')}")
    print(f"cockpit_status_phase4_phase5_handoff_allowed={phase4_strategy.get('phase5_handoff_allowed')}")
    print(f"cockpit_status_phase4_trade_candidate_count={phase4_strategy.get('trade_candidate_count')}")
    print(f"cockpit_status_phase4_execution_allowed_count={phase4_strategy.get('execution_allowed_count')}")
    print(f"cockpit_status_phase4_paper_order_allowed_count={phase4_strategy.get('paper_order_allowed_count')}")
    print(f"cockpit_status_phase4_broker_write_allowed_count={phase4_strategy.get('broker_write_allowed_count')}")
    print(f"cockpit_status_phase4_live_capital_enabled_count={phase4_strategy.get('live_capital_enabled_count')}")
    print(f"cockpit_status_phase4_toggle_validation_error_count={phase4_toggles.get('validation_error_count')}")
    print(
        "cockpit_status_phase4_preference_source_promotion_status="
        f"{phase4_preference_gate.get('source_promotion_status')}"
    )
    print(
        "cockpit_status_phase4_preference_source_promotion_promoted_count="
        f"{phase4_preference_gate.get('source_promotion_promoted_decision_count')}"
    )
    print(
        "cockpit_status_phase4_preference_source_promotion_source_count_after="
        f"{phase4_preference_gate.get('source_promotion_canonical_source_count_after')}"
    )
    print(f"cockpit_status_phase5_status={phase5_readiness.get('status')}")
    print(
        "cockpit_status_phase5_plan_allowed="
        f"{phase5_readiness.get('phase5_layer_b_implementation_plan_allowed')}"
    )
    print(
        "cockpit_status_phase5_implementation_allowed="
        f"{phase5_readiness.get('phase5_layer_b_implementation_allowed')}"
    )
    print(
        "cockpit_status_phase5_orchestration_start_allowed="
        f"{phase5_readiness.get('phase5_orchestration_start_allowed')}"
    )
    print(
        "cockpit_status_phase5_nonapproval_blocker_count="
        f"{phase5_readiness.get('nonapproval_blocker_count')}"
    )
    print(f"cockpit_status_phase5_kill_switch_status={phase5_kill_switch.get('status')}")
    print(
        "cockpit_status_phase5_kill_switch_count="
        f"{phase5_kill_switch.get('switch_count')}"
    )
    print(
        "cockpit_status_phase5_kill_switch_active_count="
        f"{phase5_kill_switch.get('active_switch_count')}"
    )
    print(
        "cockpit_status_phase5_kill_switch_blocking_count="
        f"{phase5_kill_switch.get('blocking_switch_count')}"
    )
    print(
        "cockpit_status_phase5_kill_switch_event_log_written="
        f"{phase5_kill_switch.get('event_log_written')}"
    )
    print(
        "cockpit_status_phase5_execution_adapter_status="
        f"{phase5_execution_adapter.get('status')}"
    )
    print(
        "cockpit_status_phase5_execution_adapter_count="
        f"{phase5_execution_adapter.get('adapter_status_count')}"
    )
    print(
        "cockpit_status_phase5_execution_adapter_read_allowed_count="
        f"{phase5_execution_adapter.get('read_allowed_count')}"
    )
    print(
        "cockpit_status_phase5_execution_adapter_staging_allowed_count="
        f"{phase5_execution_adapter.get('downstream_staging_allowed_count')}"
    )
    print(
        "cockpit_status_phase5_execution_adapter_alpaca_read_health="
        f"{phase5_execution_adapter.get('alpaca_read_health')}"
    )
    print(
        "cockpit_status_phase5_paper_order_staging_status="
        f"{phase5_paper_order_staging.get('status')}"
    )
    print(
        "cockpit_status_phase5_paper_order_staging_record_count="
        f"{phase5_paper_order_staging.get('staging_record_count')}"
    )
    print(
        "cockpit_status_phase5_paper_order_staged_count="
        f"{phase5_paper_order_staging.get('staged_order_count')}"
    )
    print(
        "cockpit_status_phase5_paper_order_staging_blocked_count="
        f"{phase5_paper_order_staging.get('blocked_count')}"
    )
    print(
        "cockpit_status_phase5_paper_order_staging_event_log_written="
        f"{phase5_paper_order_staging.get('event_log_written')}"
    )
    print(
        "cockpit_status_phase5_alpaca_paper_dry_run_status="
        f"{phase5_alpaca_dry_run.get('status')}"
    )
    print(
        "cockpit_status_phase5_alpaca_paper_dry_run_record_count="
        f"{phase5_alpaca_dry_run.get('dry_run_record_count')}"
    )
    print(
        "cockpit_status_phase5_alpaca_paper_dry_run_request_preview_count="
        f"{phase5_alpaca_dry_run.get('request_preview_count')}"
    )
    print(
        "cockpit_status_phase5_alpaca_paper_dry_run_receipt_count="
        f"{phase5_alpaca_dry_run.get('dry_run_receipt_count')}"
    )
    print(
        "cockpit_status_phase5_alpaca_paper_dry_run_blocked_count="
        f"{phase5_alpaca_dry_run.get('blocked_count')}"
    )
    print(
        "cockpit_status_phase5_alpaca_paper_dry_run_event_log_written="
        f"{phase5_alpaca_dry_run.get('event_log_written')}"
    )
    print(
        "cockpit_status_phase5_paper_submit_enablement_status="
        f"{phase5_paper_submit_enablement.get('status')}"
    )
    print(
        "cockpit_status_phase5_paper_submit_enablement_record_count="
        f"{phase5_paper_submit_enablement.get('submit_enablement_record_count')}"
    )
    print(
        "cockpit_status_phase5_paper_submit_path_available_count="
        f"{phase5_paper_submit_enablement.get('submit_path_available_count')}"
    )
    print(
        "cockpit_status_phase5_paper_submit_approval_state="
        f"{phase5_paper_submit_enablement.get('paper_submit_approval_state')}"
    )
    print(
        "cockpit_status_phase5_paper_submit_approval_present="
        f"{phase5_paper_submit_enablement.get('paper_submit_approval_present')}"
    )
    print(
        "cockpit_status_phase5_paper_submit_event_log_written="
        f"{phase5_paper_submit_enablement.get('event_log_written')}"
    )
    print(
        "cockpit_status_phase5_paper_submit_broker_post_called="
        f"{phase5_paper_submit_enablement.get('broker_post_called')}"
    )
    print(
        "cockpit_status_phase5_prediction_market_adapter_status="
        f"{phase5_prediction_market_adapter.get('status')}"
    )
    print(
        "cockpit_status_phase5_prediction_market_route_count="
        f"{phase5_prediction_market_adapter.get('prediction_market_route_count')}"
    )
    print(
        "cockpit_status_phase5_prediction_market_context_count="
        f"{phase5_prediction_market_adapter.get('prediction_market_context_count')}"
    )
    print(
        "cockpit_status_phase5_prediction_market_read_only_route_count="
        f"{phase5_prediction_market_adapter.get('read_only_route_count')}"
    )
    print(
        "cockpit_status_phase5_prediction_market_live_blocked_count="
        f"{phase5_prediction_market_adapter.get('live_blocked_count')}"
    )
    print(
        "cockpit_status_phase5_prediction_market_write_allowed_count="
        f"{phase5_prediction_market_adapter.get('prediction_market_write_allowed_count')}"
    )
    print(
        "cockpit_status_phase5_prediction_market_spend_allowed_count="
        f"{phase5_prediction_market_adapter.get('prediction_market_spend_allowed_count')}"
    )
    print(
        "cockpit_status_phase5_prediction_market_preference_provenance_status="
        f"{phase5_prediction_market_adapter.get('preference_provenance_status')}"
    )
    print(
        "cockpit_status_phase5_prediction_market_preference_context_status="
        f"{phase5_prediction_market_adapter.get('preference_context_status')}"
    )
    print(
        "cockpit_status_phase5_prediction_market_event_log_written="
        f"{phase5_prediction_market_adapter.get('event_log_written')}"
    )
    print(
        "cockpit_status_phase5_telegram_notifier_status="
        f"{phase5_telegram_notifier.get('status')}"
    )
    print(
        "cockpit_status_phase5_telegram_notifier_alert_type_count="
        f"{phase5_telegram_notifier.get('alert_type_count')}"
    )
    print(
        "cockpit_status_phase5_telegram_notifier_eligible_alert_count="
        f"{phase5_telegram_notifier.get('eligible_alert_count')}"
    )
    print(
        "cockpit_status_phase5_telegram_notifier_queued_count="
        f"{phase5_telegram_notifier.get('queued_dry_run_alert_count')}"
    )
    print(
        "cockpit_status_phase5_telegram_notifier_outbox_written_count="
        f"{phase5_telegram_notifier.get('outbox_message_written_count')}"
    )
    print(
        "cockpit_status_phase5_telegram_notifier_send_gate="
        f"{phase5_telegram_notifier.get('telegram_send_gate')}"
    )
    print(
        "cockpit_status_phase5_telegram_notifier_command_path_count="
        f"{phase5_telegram_notifier.get('telegram_command_path_enabled_count')}"
    )
    print(
        "cockpit_status_phase5_telegram_notifier_live_send_count="
        f"{phase5_telegram_notifier.get('live_send_allowed_count')}"
    )
    print(
        "cockpit_status_phase5_telegram_notifier_event_log_written="
        f"{phase5_telegram_notifier.get('event_log_written')}"
    )
    print(
        "cockpit_status_phase5_position_monitor_status="
        f"{phase5_position_monitor.get('status')}"
    )
    print(
        "cockpit_status_phase5_position_monitor_record_count="
        f"{phase5_position_monitor.get('monitor_record_count')}"
    )
    print(
        "cockpit_status_phase5_position_monitor_position_record_count="
        f"{phase5_position_monitor.get('position_record_count')}"
    )
    print(
        "cockpit_status_phase5_position_monitor_closed_trade_summary_count="
        f"{phase5_position_monitor.get('closed_trade_summary_count')}"
    )
    print(
        "cockpit_status_phase5_position_monitor_submitted_order_count="
        f"{phase5_position_monitor.get('submitted_order_count')}"
    )
    print(
        "cockpit_status_phase5_position_monitor_open_position_count="
        f"{phase5_position_monitor.get('open_position_count')}"
    )
    print(
        "cockpit_status_phase5_position_monitor_closed_trade_count="
        f"{phase5_position_monitor.get('closed_trade_count')}"
    )
    print(
        "cockpit_status_phase5_position_monitor_failed_reconciliation_count="
        f"{phase5_position_monitor.get('failed_reconciliation_count')}"
    )
    print(
        "cockpit_status_phase5_position_monitor_event_log_written="
        f"{phase5_position_monitor.get('event_log_written')}"
    )
    print(
        "cockpit_status_phase5_signal_review_status="
        f"{phase5_signal_review.get('status')}"
    )
    print(
        "cockpit_status_phase5_signal_review_record_count="
        f"{phase5_signal_review.get('signal_review_record_count')}"
    )
    print(
        "cockpit_status_phase5_signal_review_pricing_gap_rollout_stage="
        f"{phase5_signal_review.get('pricing_gap_rollout_stage')}"
    )
    print(
        "cockpit_status_phase5_signal_review_funnel_shadow_signal_count="
        f"{phase5_signal_review.get('funnel_shadow_signal_count')}"
    )
    print(
        "cockpit_status_phase5_signal_review_funnel_market_confirmation_count="
        f"{phase5_signal_review.get('funnel_signals_with_market_confirmation_count')}"
    )
    print(
        "cockpit_status_phase5_signal_review_funnel_pricing_gap_evidence_count="
        f"{phase5_signal_review.get('funnel_signals_with_pricing_gap_evidence_count')}"
    )
    print(
        "cockpit_status_phase5_signal_review_funnel_missing_pricing_gap_only_count="
        f"{phase5_signal_review.get('funnel_signals_blocked_only_by_missing_pricing_gap_count')}"
    )
    print(
        "cockpit_status_phase5_signal_review_funnel_passed_to_risk_count="
        f"{phase5_signal_review.get('funnel_signals_passed_to_risk_count')}"
    )
    print(
        "cockpit_status_phase5_signal_review_funnel_risk_pricing_gap_only_count="
        f"{phase5_signal_review.get('funnel_risk_reviews_blocked_only_by_pricing_gap_policy_count')}"
    )
    print(
        "cockpit_status_phase5_signal_review_funnel_stage_b_candidate_signal_count="
        f"{phase5_signal_review.get('funnel_stage_b_candidate_signal_count')}"
    )
    print(
        "cockpit_status_phase5_signal_review_decision_chain_count="
        f"{phase5_signal_review.get('decision_chain_count')}"
    )
    print(
        "cockpit_status_phase5_signal_review_governance_comment_event_count="
        f"{phase5_signal_review.get('governance_comment_event_count')}"
    )
    print(
        "cockpit_status_phase5_signal_review_kill_switch_action_event_count="
        f"{phase5_signal_review.get('kill_switch_action_event_count')}"
    )
    print(
        "cockpit_status_phase5_signal_review_backend_truth_displayed_count="
        f"{phase5_signal_review.get('backend_truth_displayed_count')}"
    )
    print(
        "cockpit_status_phase5_signal_review_ui_inferred_readiness_count="
        f"{phase5_signal_review.get('ui_inferred_readiness_count')}"
    )
    print(
        "cockpit_status_phase5_signal_review_event_log_written="
        f"{phase5_signal_review.get('event_log_written')}"
    )
    print(
        "cockpit_status_phase5_paper_trade_drill_status="
        f"{phase5_paper_trade_drill.get('status')}"
    )
    print(
        "cockpit_status_phase5_paper_trade_drill_state="
        f"{phase5_paper_trade_drill.get('paper_trade_drill_state')}"
    )
    print(
        "cockpit_status_phase5_paper_trade_drill_complete="
        f"{phase5_paper_trade_drill.get('paper_trade_drill_complete')}"
    )
    print(
        "cockpit_status_phase5_paper_trade_drill_exit_gate_passed="
        f"{phase5_paper_trade_drill.get('phase5_paper_trade_drill_exit_gate_passed')}"
    )
    print(
        "cockpit_status_phase5_paper_trade_drill_step_count="
        f"{phase5_paper_trade_drill.get('step_count')}"
    )
    print(
        "cockpit_status_phase5_paper_trade_drill_blocker_count="
        f"{phase5_paper_trade_drill.get('blocker_count')}"
    )
    print(
        "cockpit_status_phase5_paper_trade_drill_submit_approval_present="
        f"{phase5_paper_trade_drill.get('paper_submit_approval_present')}"
    )
    print(
        "cockpit_status_phase5_paper_trade_drill_submit_path_available_count="
        f"{phase5_paper_trade_drill.get('paper_submit_path_available_count')}"
    )
    print(
        "cockpit_status_phase5_paper_trade_drill_broker_post_called_count="
        f"{phase5_paper_trade_drill.get('broker_post_called_count')}"
    )
    print(
        "cockpit_status_phase5_paper_trade_drill_live_capital_enabled_count="
        f"{phase5_paper_trade_drill.get('live_capital_enabled_count')}"
    )
    print(
        "cockpit_status_phase5_paper_trade_drill_event_log_written="
        f"{phase5_paper_trade_drill.get('event_log_written')}"
    )
    print(
        "cockpit_status_phase5_certification_status="
        f"{phase5_certification.get('status')}"
    )
    print(
        "cockpit_status_phase5_certification_stage_status="
        f"{phase5_certification.get('stage_status')}"
    )
    print(
        "cockpit_status_phase5_certification_phase5_certified="
        f"{phase5_certification.get('phase5_certified')}"
    )
    print(
        "cockpit_status_phase5_certification_phase5_exit_gate="
        f"{phase5_certification.get('phase5_exit_gate')}"
    )
    print(
        "cockpit_status_phase5_certification_phase6_handoff_allowed="
        f"{phase5_certification.get('phase6_handoff_allowed')}"
    )
    print(
        "cockpit_status_phase5_certification_phase7_planning_allowed="
        f"{phase5_certification.get('phase7_planning_allowed')}"
    )
    print(
        "cockpit_status_phase5_certification_input_gate_passed_count="
        f"{phase5_certification.get('input_gate_passed_count')}"
    )
    print(
        "cockpit_status_phase5_certification_input_gate_blocked_count="
        f"{phase5_certification.get('input_gate_blocked_count')}"
    )
    print(
        "cockpit_status_phase5_certification_blocker_count="
        f"{phase5_certification.get('certification_blocker_count')}"
    )
    print(
        "cockpit_status_phase5_certification_event_log_written="
        f"{phase5_certification.get('event_log_written')}"
    )
    print(
        "cockpit_status_phase5_phase6_handoff_status="
        f"{phase5_phase6_handoff.get('status')}"
    )
    print(
        "cockpit_status_phase5_phase6_handoff_state="
        f"{phase5_phase6_handoff.get('handoff_state')}"
    )
    print(
        "cockpit_status_phase5_phase6_handoff_phase6_plan_allowed="
        f"{phase5_phase6_handoff.get('phase6_learning_loop_plan_allowed')}"
    )
    print(
        "cockpit_status_phase5_phase6_handoff_phase6_implementation_allowed="
        f"{phase5_phase6_handoff.get('phase6_learning_loop_implementation_allowed')}"
    )
    print(
        "cockpit_status_phase5_phase6_handoff_learning_write_allowed="
        f"{phase5_phase6_handoff.get('phase6_learning_write_allowed')}"
    )
    print(
        "cockpit_status_phase5_phase6_handoff_blocker_count="
        f"{phase5_phase6_handoff.get('blocker_count')}"
    )
    print(
        "cockpit_status_phase5_phase6_handoff_event_log_written="
        f"{phase5_phase6_handoff.get('event_log_written')}"
    )
    print(
        "cockpit_status_phase5_system_map_status="
        f"{phase5_system_map.get('status')}"
    )
    print(
        "cockpit_status_phase5_system_map_node_count="
        f"{phase5_system_map.get('node_count')}"
    )
    print(
        "cockpit_status_phase5_system_map_lane_count="
        f"{phase5_system_map.get('lane_count')}"
    )
    print(
        "cockpit_status_phase5_system_map_layer_b_node_count="
        f"{phase5_system_map.get('layer_b_node_count')}"
    )
    print(
        "cockpit_status_phase5_system_map_backend_parity_error_count="
        f"{phase5_system_map.get('backend_parity_error_count')}"
    )
    print(
        "cockpit_status_phase5_system_map_unsafe_control_count="
        f"{phase5_system_map.get('unsafe_control_count')}"
    )
    print(
        "cockpit_status_phase5_system_map_ui_inferred_node_count="
        f"{phase5_system_map.get('ui_inferred_node_count')}"
    )
    print(
        "cockpit_status_phase5_system_map_event_log_written="
        f"{phase5_system_map.get('event_log_written')}"
    )
    print(
        "cockpit_status_phase6_learning_loop_status="
        f"{phase6_learning_loop.get('status')}"
    )
    print(
        "cockpit_status_phase6_learning_loop_visibility_state="
        f"{phase6_learning_loop.get('visibility_state')}"
    )
    print(
        "cockpit_status_phase6_learning_loop_learning_state="
        f"{phase6_learning_loop.get('learning_state')}"
    )
    print(
        "cockpit_status_phase6_learning_loop_backend_derived="
        f"{phase6_learning_loop.get('backend_derived')}"
    )
    print(
        "cockpit_status_phase6_learning_loop_ui_inferred_readiness_count="
        f"{phase6_learning_loop.get('ui_inferred_readiness_count')}"
    )
    print(
        "cockpit_status_phase6_learning_loop_postmortem_due_count="
        f"{phase6_learning_loop.get('postmortem_due_count')}"
    )
    print(
        "cockpit_status_phase6_learning_loop_approval_state="
        f"{phase6_learning_loop.get('approval_state')}"
    )
    print(
        "cockpit_status_phase6_learning_loop_staged_graph_entry_count="
        f"{phase6_learning_loop.get('staged_graph_entry_count')}"
    )
    print(
        "cockpit_status_phase6_learning_loop_model_weight_proposal_count="
        f"{phase6_learning_loop.get('model_weight_proposal_count')}"
    )
    print(
        "cockpit_status_phase6_learning_loop_trust_score_proposal_count="
        f"{phase6_learning_loop.get('trust_score_proposal_count')}"
    )
    print(
        "cockpit_status_phase6_learning_loop_blocked_authority_count="
        f"{phase6_learning_loop.get('blocked_authority_count')}"
    )
    print(
        "cockpit_status_rs9_learning_loop_status="
        f"{rs9_learning_loop.get('status')}"
    )
    print(
        "cockpit_status_rs9_learning_direction="
        f"{rs9_learning_loop.get('learning_direction')}"
    )
    print(
        "cockpit_status_rs9_full_potential_state="
        f"{rs9_learning_loop.get('full_potential_state')}"
    )
    print(
        "cockpit_status_rs9_proposal_count="
        f"{rs9_learning_loop.get('proposal_count')}"
    )
    print(
        "cockpit_status_rs9_blocked_proposal_count="
        f"{rs9_learning_loop.get('blocked_proposal_count')}"
    )
    print(
        "cockpit_status_rs9_postmortem_due_count="
        f"{rs9_learning_loop.get('postmortem_due_count')}"
    )
    print(
        "cockpit_status_rs9_paperops_guarded_paper_trading_not_blocked="
        f"{rs9_learning_loop.get('paperops_guarded_paper_trading_not_blocked')}"
    )
    print(
        "cockpit_status_rs9_blocked_authority_count="
        f"{rs9_learning_loop.get('blocked_authority_count')}"
    )
    print(
        "cockpit_status_rs10_final_paper_autonomy_status="
        f"{rs10_final_paper_autonomy.get('status')}"
    )
    print(
        "cockpit_status_rs10_final_paper_autonomy_certified="
        f"{rs10_final_paper_autonomy.get('final_paper_autonomy_certified')}"
    )
    print(
        "cockpit_status_rs10_guarded_paper_autonomy_allowed="
        f"{rs10_final_paper_autonomy.get('guarded_paper_autonomy_allowed')}"
    )
    print(
        "cockpit_status_rs10_autonomy_currently_actionable="
        f"{rs10_final_paper_autonomy.get('autonomy_currently_actionable')}"
    )
    print(
        "cockpit_status_rs10_current_blocker_count="
        f"{rs10_final_paper_autonomy.get('current_blocker_count')}"
    )
    print(
        "cockpit_status_rs10_current_blockers="
        f"{','.join(rs10_final_paper_autonomy.get('current_blockers', []) or [])}"
    )
    print(
        "cockpit_status_rs10_certification_blocker_count="
        f"{rs10_final_paper_autonomy.get('certification_blocker_count')}"
    )
    print(
        "cockpit_status_rs10_multiple_paper_trades_per_day_allowed_when_gates_pass="
        f"{rs10_final_paper_autonomy.get('multiple_paper_trades_per_day_allowed_when_gates_pass')}"
    )
    print(
        "cockpit_status_phase6_certification_status="
        f"{phase6_certification.get('status')}"
    )
    print(
        "cockpit_status_phase6_certification_stage_status="
        f"{phase6_certification.get('stage_status')}"
    )
    print(
        "cockpit_status_phase6_certification_phase6_certified="
        f"{phase6_certification.get('phase6_certified')}"
    )
    print(
        "cockpit_status_phase6_certification_phase6_exit_gate="
        f"{phase6_certification.get('phase6_exit_gate')}"
    )
    print(
        "cockpit_status_phase6_certification_phase7_demo_proof_planning_allowed="
        f"{phase6_certification.get('phase7_demo_proof_planning_allowed')}"
    )
    print(
        "cockpit_status_phase6_certification_blocker_count="
        f"{phase6_certification.get('certification_blocker_count')}"
    )
    print(
        "cockpit_status_phase6_certification_input_gate_passed_count="
        f"{phase6_certification.get('input_gate_passed_count')}"
    )
    print(
        "cockpit_status_phase6_certification_approval_state="
        f"{phase6_certification.get('approval_state')}"
    )
    print(
        "cockpit_status_phase6_certification_unresolved_postmortem_count="
        f"{phase6_certification.get('unresolved_postmortem_count')}"
    )
    print(
        "cockpit_status_phase6_certification_pending_review_action_count="
        f"{phase6_certification.get('pending_review_action_count')}"
    )

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
    durable_ingestion = payload.get("durable_ingestion", {})
    missing_durable_fields = sorted(DURABLE_INGESTION_REQUIRED_FIELDS - set(durable_ingestion))
    if missing_durable_fields:
        print("cockpit_status_durable_ingestion_fields_missing=" + ",".join(missing_durable_fields))
        return 1
    if durable_ingestion.get("expected_source_count") != EXPECTED_SOURCE_COUNT:
        print("cockpit_status_durable_ingestion_expected_count_mismatch=true")
        return 1
    if durable_ingestion.get("write_authority") is not False:
        print("cockpit_status_durable_ingestion_write_authority_enabled=true")
        return 1
    if durable_ingestion.get("signal_authority") is not False or durable_ingestion.get("order_authority") is not False:
        print("cockpit_status_durable_ingestion_authority_enabled=true")
        return 1
    if "cannot create signals" not in durable_ingestion.get("boundary", ""):
        print("cockpit_status_durable_ingestion_boundary_weak=true")
        return 1
    if durable_ingestion.get("status") not in {"ok", "partial", "missing_tables", "degraded", "ready_waiting_for_local_service"}:
        print("cockpit_status_durable_ingestion_status_invalid=true")
        return 1
    yahoo_finance = payload.get("yahoo_finance", {})
    missing_yahoo_fields = sorted(YAHOO_FINANCE_REQUIRED_FIELDS - set(yahoo_finance))
    if missing_yahoo_fields:
        print("cockpit_status_yahoo_finance_fields_missing=" + ",".join(missing_yahoo_fields))
        return 1
    if yahoo_finance.get("source") != "market.yahoo_finance":
        print("cockpit_status_yahoo_finance_source_mismatch=true")
        return 1
    if yahoo_finance.get("classification") != "accepted_supplemental_pending_live_dependencies":
        print("cockpit_status_yahoo_finance_classification_mismatch=true")
        return 1
    if yahoo_finance.get("public_safe") is not True:
        print("cockpit_status_yahoo_finance_not_public_safe=true")
        return 1
    if yahoo_finance.get("canonical_source") is not False:
        print("cockpit_status_yahoo_finance_canonical_source=true")
        return 1
    if yahoo_finance.get("canonical_source_count") != EXPECTED_SOURCE_COUNT:
        print("cockpit_status_yahoo_finance_canonical_count_mismatch=true")
        return 1
    if yahoo_finance.get("market_confirmation_role") != "supplemental_market_confirmation":
        print("cockpit_status_yahoo_finance_role_mismatch=true")
        return 1
    if yahoo_finance.get("symbol_allowlist_count", 0) < 1:
        print("cockpit_status_yahoo_finance_symbols_missing=true")
        return 1
    if yahoo_finance.get("status") not in {"deferred", "degraded", "live_read_only_ready"}:
        print("cockpit_status_yahoo_finance_status_invalid=true")
        return 1
    for key in (
        "raw_payload_exposed",
        "raw_archive_path_exposed",
        "cache_path_exposed",
        "cookies_exposed",
        "crumb_tokens_exposed",
        "scraped_html_exposed",
        "signal_authority",
        "risk_approval_authority",
        "order_authority",
        "broker_write_authority",
        "broker_echo_authority",
        "fill_confirmation_authority",
        "receipt_evidence_authority",
        "reconciliation_truth_authority",
        "live_capital_authority",
    ):
        if yahoo_finance.get(key) is not False:
            print(f"cockpit_status_yahoo_finance_flag_not_false={key}")
            return 1
    if "supplemental market confirmation" not in yahoo_finance.get("boundary", ""):
        print("cockpit_status_yahoo_finance_boundary_weak=true")
        return 1
    preference_mcp = payload.get("preference_mcp", {})
    missing_preference_fields = sorted(PREFERENCE_MCP_REQUIRED_FIELDS - set(preference_mcp))
    if missing_preference_fields:
        print("cockpit_status_preference_mcp_fields_missing=" + ",".join(missing_preference_fields))
        return 1
    if preference_mcp.get("source_key") != "preference_mcp":
        print("cockpit_status_preference_mcp_source_key_mismatch=true")
        return 1
    if preference_mcp.get("provider_label") != "preference_labs_mcp":
        print("cockpit_status_preference_mcp_provider_mismatch=true")
        return 1
    if preference_mcp.get("classification") != "proposed_supplemental_multi_source_data_plane":
        print("cockpit_status_preference_mcp_classification_mismatch=true")
        return 1
    if preference_mcp.get("public_safe") is not True:
        print("cockpit_status_preference_mcp_not_public_safe=true")
        return 1
    if preference_mcp.get("status") not in {"challenge_only_ready", "catalog_only_ready", "disabled", "degraded"}:
        print("cockpit_status_preference_mcp_status_invalid=true")
        return 1
    if preference_mcp.get("quota_status") not in {
        "verified",
        "disabled_live_mode",
        "blocked_pending_verified_identity",
    }:
        print("cockpit_status_preference_mcp_quota_status_invalid=true")
        return 1
    if preference_mcp.get("approved_domain_pack_count") != len(preference_mcp.get("approved_domain_packs", [])):
        print("cockpit_status_preference_mcp_domain_pack_count_mismatch=true")
        return 1
    if preference_mcp.get("approved_domain_pack_count", 0) < 1:
        print("cockpit_status_preference_mcp_domain_pack_coverage_missing=true")
        return 1
    if preference_mcp.get("source_promotion_status") not in {"not_run", "validated"}:
        print("cockpit_status_preference_mcp_source_promotion_status_invalid=true")
        return 1
    if preference_mcp.get("source_promotion_promoted_decision_count", 0) != 0:
        print("cockpit_status_preference_mcp_source_promotion_promoted=true")
        return 1
    if preference_mcp.get("source_promotion_canonical_source_count_after") != EXPECTED_SOURCE_COUNT:
        print("cockpit_status_preference_mcp_source_promotion_source_count_mismatch=true")
        return 1
    for key in (
        "paid_tools_allowed",
        "live_mcp_call_allowed",
        "search_tools_allowed",
        "domain_tool_calls_allowed",
        "paid_tool_calls_allowed",
        "source_quorum_credit_allowed",
        "preference_only_confirmation_allowed",
        "trade_candidate_creation_allowed",
        "risk_handoff_allowed",
        "execution_allowed",
        "paper_order_allowed",
        "broker_write_allowed",
        "live_capital_enabled",
        "raw_key_exposed",
        "raw_prompt_exposed",
        "raw_payload_exposed",
        "private_source_payload_exposed",
    ):
        if preference_mcp.get(key) is not False:
            print(f"cockpit_status_preference_mcp_flag_not_false={key}")
            return 1
    preference_authority_flags = preference_mcp.get("authority_flags", {})
    if not isinstance(preference_authority_flags, dict) or not preference_authority_flags:
        print("cockpit_status_preference_mcp_authority_flags_missing=true")
        return 1
    for key, value in preference_authority_flags.items():
        if value is not False:
            print(f"cockpit_status_preference_mcp_authority_flag_enabled={key}")
            return 1
    preference_boundary = preference_mcp.get("boundary", "")
    for phrase in ("read-only", "without secrets", "cannot satisfy source quorum", "create trade candidates"):
        if phrase not in preference_boundary:
            print("cockpit_status_preference_mcp_boundary_weak=true")
            return 1
    phase4_strategy = payload.get("phase4_strategy", {})
    missing_phase4_fields = sorted(PHASE4_STRATEGY_REQUIRED_FIELDS - set(phase4_strategy))
    if missing_phase4_fields:
        print("cockpit_status_phase4_fields_missing=" + ",".join(missing_phase4_fields))
        return 1
    if phase4_strategy.get("phase") != "Q4" or phase4_strategy.get("stage") != "Q4-12":
        print("cockpit_status_phase4_stage_mismatch=true")
        return 1
    if phase4_strategy.get("public_safe") is not True:
        print("cockpit_status_phase4_not_public_safe=true")
        return 1
    if phase4_strategy.get("strategy_document_status") != "validated":
        print("cockpit_status_phase4_strategy_document_not_validated=true")
        return 1
    phase4_approval = phase4_strategy.get("approval_event", {})
    phase4_approved = phase4_strategy.get("approval_event_status") == "approved"
    if phase4_approval.get("approval_logged") is not True:
        print("cockpit_status_phase4_approval_not_logged=true")
        return 1
    if phase4_certification.get("validation_error_count") != 0:
        print("cockpit_status_phase4_certification_validation_errors=true")
        return 1
    if phase4_approved:
        if phase4_approval.get("required_amendment_count") != 0:
            print("cockpit_status_phase4_required_amendments_present=true")
            return 1
        if phase4_strategy.get("phase4_certification_allowed") is not True:
            print("cockpit_status_phase4_certification_not_allowed=true")
            return 1
        if phase4_strategy.get("phase4_certified") is not True:
            print("cockpit_status_phase4_not_certified=true")
            return 1
        if phase4_strategy.get("phase5_handoff_allowed") is not True:
            print("cockpit_status_phase4_phase5_handoff_not_allowed=true")
            return 1
        if phase4_strategy.get("certification_status") != "certified":
            print("cockpit_status_phase4_certification_status_not_certified=true")
            return 1
        if phase4_certification.get("certification_blocker_count", 0) != 0:
            print("cockpit_status_phase4_certification_blockers_present=true")
            return 1
    else:
        if phase4_strategy.get("approval_event_status") != "amendments_required":
            print("cockpit_status_phase4_approval_state_mismatch=true")
            return 1
        if phase4_approval.get("required_amendment_count") < 1:
            print("cockpit_status_phase4_required_amendments_missing=true")
            return 1
        if phase4_strategy.get("phase4_certification_allowed") is not False:
            print("cockpit_status_phase4_certification_allowed=true")
            return 1
        if phase4_strategy.get("phase4_certified") is not False:
            print("cockpit_status_phase4_certified=true")
            return 1
        if phase4_strategy.get("phase5_handoff_allowed") is not False:
            print("cockpit_status_phase4_phase5_handoff_allowed=true")
            return 1
        if phase4_strategy.get("certification_status") != "blocked":
            print("cockpit_status_phase4_certification_status_not_blocked=true")
            return 1
        if phase4_certification.get("certification_blocker_count", 0) < 1:
            print("cockpit_status_phase4_certification_blocker_missing=true")
            return 1
        if "explicit_fund_manager_approval_required" not in phase4_certification.get(
            "certification_blockers",
            [],
        ):
            print("cockpit_status_phase4_explicit_approval_blocker_missing=true")
            return 1
    if phase4_preference_gate.get("source_promotion_status") != "validated":
        print("cockpit_status_phase4_preference_source_promotion_not_validated=true")
        return 1
    if phase4_preference_gate.get("source_promotion_promoted_decision_count", 0) != 0:
        print("cockpit_status_phase4_preference_source_promotion_promoted=true")
        return 1
    if (
        phase4_preference_gate.get("source_promotion_canonical_source_count_after")
        != EXPECTED_SOURCE_COUNT
    ):
        print("cockpit_status_phase4_preference_source_promotion_count_mismatch=true")
        return 1
    if phase4_preference_gate.get("preference_mcp_source_36") is not False:
        print("cockpit_status_phase4_preference_source36=true")
        return 1
    phase4_toggles = phase4_strategy.get("strategy_toggles", {})
    if phase4_toggles.get("toggle_count") != 5:
        print("cockpit_status_phase4_toggle_count_mismatch=true")
        return 1
    if phase4_approved:
        if phase4_strategy.get("approved_shadow_strategy_toggle_count") != 5:
            print("cockpit_status_phase4_approved_shadow_toggle_count_mismatch=true")
            return 1
        if phase4_toggles.get("draft_toggle_count") != 0:
            print("cockpit_status_phase4_draft_toggle_count_mismatch=true")
            return 1
    else:
        if phase4_strategy.get("approved_shadow_strategy_toggle_count") != 0:
            print("cockpit_status_phase4_approved_shadow_toggle_enabled=true")
            return 1
        if phase4_toggles.get("draft_toggle_count") != 5:
            print("cockpit_status_phase4_draft_toggle_count_mismatch=true")
            return 1
    if phase4_toggles.get("validation_error_count") != 0:
        print("cockpit_status_phase4_toggle_validation_errors=true")
        return 1
    for key in (
        "trade_candidate_count",
        "execution_allowed_count",
        "paper_order_allowed_count",
        "broker_write_allowed_count",
        "live_capital_enabled_count",
    ):
        if phase4_strategy.get(key) != 0:
            print(f"cockpit_status_phase4_count_not_zero={key}")
            return 1
    for key in ("execution_allowed", "paper_order_allowed", "broker_write_allowed", "live_capital_enabled"):
        if phase4_strategy.get(key) is not False:
            print(f"cockpit_status_phase4_flag_not_false={key}")
            return 1
    if "cannot create trade candidates" not in phase4_strategy.get("no_execution_boundary", ""):
        print("cockpit_status_phase4_boundary_weak=true")
        return 1
    phase5_readiness = payload.get("phase5_layer_b_readiness", {})
    missing_phase5_fields = sorted(PHASE5_LAYER_B_REQUIRED_FIELDS - set(phase5_readiness))
    if missing_phase5_fields:
        print("cockpit_status_phase5_fields_missing=" + ",".join(missing_phase5_fields))
        return 1
    if phase5_readiness.get("phase") != "Q5" or phase5_readiness.get("layer") != "Layer B":
        print("cockpit_status_phase5_phase_or_layer_mismatch=true")
        return 1
    if phase5_readiness.get("stage") != "P5-PRE":
        print("cockpit_status_phase5_stage_mismatch=true")
        return 1
    if phase5_readiness.get("public_safe") is not True:
        print("cockpit_status_phase5_not_public_safe=true")
        return 1
    if phase5_readiness.get("phase5_layer_b_implementation_plan_allowed") is not True:
        print("cockpit_status_phase5_plan_not_allowed=true")
        return 1
    if phase5_readiness.get("phase5_orchestration_start_allowed") is not False:
        print("cockpit_status_phase5_orchestration_start_allowed=true")
        return 1
    phase5_implementation_allowed = (
        phase5_readiness.get("phase5_layer_b_implementation_allowed") is True
    )
    if phase5_implementation_allowed:
        if phase5_readiness.get("status") != "ready_for_phase5_layer_b_implementation":
            print("cockpit_status_phase5_not_ready=true")
            return 1
        if phase5_readiness.get("phase4_certified") is not True:
            print("cockpit_status_phase5_phase4_not_certified=true")
            return 1
        if phase5_readiness.get("phase5_handoff_allowed") is not True:
            print("cockpit_status_phase5_handoff_not_allowed=true")
            return 1
        if phase5_readiness.get("readiness_blocker_count") != 0:
            print("cockpit_status_phase5_blockers_present=true")
            return 1
    else:
        if phase5_readiness.get("status") != "blocked_pending_phase4_certification":
            print("cockpit_status_phase5_not_blocked=true")
            return 1
        if phase5_readiness.get("phase4_certified") is not False:
            print("cockpit_status_phase5_phase4_certified=true")
            return 1
        if phase5_readiness.get("phase5_handoff_allowed") is not False:
            print("cockpit_status_phase5_handoff_allowed=true")
            return 1
        if "explicit_fund_manager_approval_required" not in phase5_readiness.get(
            "readiness_blockers",
            [],
        ):
            print("cockpit_status_phase5_explicit_approval_blocker_missing=true")
            return 1
    if phase5_readiness.get("nonapproval_blocker_count") != 0:
        print("cockpit_status_phase5_nonapproval_blockers_present=true")
        return 1
    if phase5_readiness.get("preference_source_promotion_status") != "validated":
        print("cockpit_status_phase5_preference_source_promotion_not_validated=true")
        return 1
    if phase5_readiness.get("yahoo_finance_role") != "supplemental_market_confirmation_only":
        print("cockpit_status_phase5_yahoo_role_not_supplemental=true")
        return 1
    for key in (
        "approval_policy_router_enabled",
        "risk_agent_approval_authority",
        "kill_switch_mutation_authority",
        "execution_adapter_write_authority",
        "paper_execution_allowed",
        "paper_order_allowed",
        "broker_write_allowed",
        "prediction_market_write_allowed",
        "telegram_live_notifications_allowed",
        "position_monitor_write_authority",
        "live_capital_enabled",
    ):
        if phase5_readiness.get(key) is not False:
            print(f"cockpit_status_phase5_authority_enabled={key}")
            return 1
    missing_phase5_kill_switch_fields = sorted(
        PHASE5_KILL_SWITCH_REQUIRED_FIELDS - set(phase5_kill_switch)
    )
    if missing_phase5_kill_switch_fields:
        print(
            "cockpit_status_phase5_kill_switch_fields_missing="
            + ",".join(missing_phase5_kill_switch_fields)
        )
        return 1
    if phase5_kill_switch.get("phase") != "Q5" or phase5_kill_switch.get("stage") != "Q5-4":
        print("cockpit_status_phase5_kill_switch_phase_or_stage_mismatch=true")
        return 1
    if phase5_kill_switch.get("public_safe") is not True:
        print("cockpit_status_phase5_kill_switch_not_public_safe=true")
        return 1
    if phase5_kill_switch.get("ledger_recorded") is not True:
        print("cockpit_status_phase5_kill_switch_not_recorded=true")
        return 1
    if phase5_kill_switch.get("status") != "ok":
        print("cockpit_status_phase5_kill_switch_not_ok=true")
        return 1
    if phase5_kill_switch.get("validation_error_count") != 0:
        print("cockpit_status_phase5_kill_switch_validation_errors=true")
        return 1
    if phase5_kill_switch.get("event_log_written") is not True:
        print("cockpit_status_phase5_kill_switch_event_log_not_written=true")
        return 1
    if phase5_kill_switch.get("event_log_event_count") != phase5_kill_switch.get("switch_count"):
        print("cockpit_status_phase5_kill_switch_event_log_count_mismatch=true")
        return 1
    if phase5_kill_switch.get("switch_count", 0) < phase5_kill_switch.get(
        "required_scope_type_count",
        0,
    ):
        print("cockpit_status_phase5_kill_switch_count_below_scope_count=true")
        return 1
    if phase5_kill_switch.get("fail_closed_default_count") != phase5_kill_switch.get("switch_count"):
        print("cockpit_status_phase5_kill_switch_fail_closed_count_mismatch=true")
        return 1
    if phase5_kill_switch.get("active_switch_count") != phase5_kill_switch.get("blocking_switch_count"):
        print("cockpit_status_phase5_kill_switch_active_blocking_mismatch=true")
        return 1
    if phase5_kill_switch.get("default_fail_closed_on_missing_state") is not True:
        print("cockpit_status_phase5_kill_switch_missing_state_not_fail_closed=true")
        return 1
    if phase5_kill_switch.get("default_fail_closed_on_corrupt_state") is not True:
        print("cockpit_status_phase5_kill_switch_corrupt_state_not_fail_closed=true")
        return 1
    for scope_type in phase5_kill_switch.get("required_scope_types", []):
        if int(phase5_kill_switch.get("scope_counts", {}).get(scope_type, 0) or 0) < 1:
            print(f"cockpit_status_phase5_kill_switch_scope_missing={scope_type}")
            return 1
    for key in (
        "execution_allowed",
        "paper_order_allowed",
        "broker_write_allowed",
        "telegram_live_notifications_allowed",
        "kill_switch_mutation_authority",
        "live_capital_enabled",
    ):
        if phase5_kill_switch.get(key) is not False:
            print(f"cockpit_status_phase5_kill_switch_authority_enabled={key}")
            return 1
    if "live capital" not in phase5_kill_switch.get("boundary", ""):
        print("cockpit_status_phase5_kill_switch_boundary_weak=true")
        return 1
    missing_phase5_execution_adapter_fields = sorted(
        PHASE5_EXECUTION_ADAPTER_REQUIRED_FIELDS - set(phase5_execution_adapter)
    )
    if missing_phase5_execution_adapter_fields:
        print(
            "cockpit_status_phase5_execution_adapter_fields_missing="
            + ",".join(missing_phase5_execution_adapter_fields)
        )
        return 1
    if (
        phase5_execution_adapter.get("phase") != "Q5"
        or phase5_execution_adapter.get("stage") != "Q5-5"
    ):
        print("cockpit_status_phase5_execution_adapter_phase_or_stage_mismatch=true")
        return 1
    if phase5_execution_adapter.get("public_safe") is not True:
        print("cockpit_status_phase5_execution_adapter_not_public_safe=true")
        return 1
    if phase5_execution_adapter.get("recorded") is not True:
        print("cockpit_status_phase5_execution_adapter_not_recorded=true")
        return 1
    if phase5_execution_adapter.get("status") != "ok":
        print("cockpit_status_phase5_execution_adapter_not_ok=true")
        return 1
    if phase5_execution_adapter.get("validation_error_count") != 0:
        print("cockpit_status_phase5_execution_adapter_validation_errors=true")
        return 1
    if phase5_execution_adapter.get("event_log_written") is not True:
        print("cockpit_status_phase5_execution_adapter_event_log_not_written=true")
        return 1
    if phase5_execution_adapter.get("event_log_event_count") != phase5_execution_adapter.get(
        "adapter_status_count"
    ):
        print("cockpit_status_phase5_execution_adapter_event_log_count_mismatch=true")
        return 1
    if phase5_execution_adapter.get("downstream_staging_allowed_count", 0) > 1:
        print("cockpit_status_phase5_execution_adapter_staging_count_invalid=true")
        return 1
    if phase5_execution_adapter.get("alpaca_credentials_configured") is True:
        if phase5_execution_adapter.get("alpaca_read_health") != "read_only_available":
            print("cockpit_status_phase5_execution_adapter_alpaca_read_unavailable=true")
            return 1
        if phase5_execution_adapter.get("alpaca_account_mode") != "paper":
            print("cockpit_status_phase5_execution_adapter_alpaca_mode_not_paper=true")
            return 1
    if phase5_execution_adapter.get("alpaca_write_health") != "blocked_q5_5_status_contract":
        print("cockpit_status_phase5_execution_adapter_alpaca_write_unblocked=true")
        return 1
    for key in (
        "execution_adapter_write_authority",
        "paper_order_staging_allowed",
        "paper_order_submission_allowed",
        "paper_order_allowed",
        "broker_write_allowed",
        "prediction_market_write_allowed",
        "crypto_perps_write_allowed",
        "live_endpoint_allowed",
        "live_capital_enabled",
    ):
        if phase5_execution_adapter.get(key) is not False:
            print(f"cockpit_status_phase5_execution_adapter_authority_enabled={key}")
            return 1
    for key in (
        "secret_value_exposed_count",
        "raw_payload_exposed_count",
        "local_path_exposed_count",
    ):
        if phase5_execution_adapter.get(key) != 0:
            print(f"cockpit_status_phase5_execution_adapter_exposure_count_nonzero={key}")
            return 1
    if "live capital" not in phase5_execution_adapter.get("boundary", ""):
        print("cockpit_status_phase5_execution_adapter_boundary_weak=true")
        return 1
    missing_phase5_paper_order_staging_fields = sorted(
        PHASE5_PAPER_ORDER_STAGING_REQUIRED_FIELDS - set(phase5_paper_order_staging)
    )
    if missing_phase5_paper_order_staging_fields:
        print(
            "cockpit_status_phase5_paper_order_staging_fields_missing="
            + ",".join(missing_phase5_paper_order_staging_fields)
        )
        return 1
    if (
        phase5_paper_order_staging.get("phase") != "Q5"
        or phase5_paper_order_staging.get("stage") != "Q5-6"
    ):
        print("cockpit_status_phase5_paper_order_staging_phase_or_stage_mismatch=true")
        return 1
    if phase5_paper_order_staging.get("public_safe") is not True:
        print("cockpit_status_phase5_paper_order_staging_not_public_safe=true")
        return 1
    if phase5_paper_order_staging.get("recorded") is not True:
        print("cockpit_status_phase5_paper_order_staging_not_recorded=true")
        return 1
    if phase5_paper_order_staging.get("status") != "ok":
        print("cockpit_status_phase5_paper_order_staging_not_ok=true")
        return 1
    if phase5_paper_order_staging.get("validation_error_count") != 0:
        print("cockpit_status_phase5_paper_order_staging_validation_errors=true")
        return 1
    if phase5_paper_order_staging.get("event_log_written") is not True:
        print("cockpit_status_phase5_paper_order_staging_event_log_not_written=true")
        return 1
    if phase5_paper_order_staging.get("event_log_event_count") != phase5_paper_order_staging.get(
        "staging_record_count"
    ):
        print("cockpit_status_phase5_paper_order_staging_event_log_count_mismatch=true")
        return 1
    if phase5_paper_order_staging.get("staging_record_count") != phase5_paper_order_staging.get(
        "risk_review_count"
    ):
        print("cockpit_status_phase5_paper_order_staging_record_count_mismatch=true")
        return 1
    if phase5_paper_order_staging.get("paper_size_eligible_count") == 0:
        if phase5_paper_order_staging.get("staged_order_count") != 0:
            print("cockpit_status_phase5_paper_order_staging_created_order_without_risk=true")
            return 1
        if phase5_paper_order_staging.get("blocked_count") != phase5_paper_order_staging.get(
            "staging_record_count"
        ):
            print("cockpit_status_phase5_paper_order_staging_blocked_count_mismatch=true")
            return 1
    for key in (
        "staging_allowed",
        "submission_allowed",
        "paper_order_staging_allowed",
        "paper_order_submission_allowed",
        "paper_order_allowed",
        "paper_order_submitted",
        "broker_write_allowed",
        "broker_post_called",
        "execution_allowed",
        "live_capital_enabled",
    ):
        if phase5_paper_order_staging.get(key) is not False:
            print(f"cockpit_status_phase5_paper_order_staging_authority_enabled={key}")
            return 1
    for key in (
        "secret_value_exposed_count",
        "raw_payload_exposed_count",
        "local_path_exposed_count",
    ):
        if phase5_paper_order_staging.get(key) != 0:
            print(f"cockpit_status_phase5_paper_order_staging_exposure_count_nonzero={key}")
            return 1
    if "cannot submit paper orders" not in phase5_paper_order_staging.get("boundary", ""):
        print("cockpit_status_phase5_paper_order_staging_boundary_weak=true")
        return 1
    missing_phase5_alpaca_dry_run_fields = sorted(
        PHASE5_ALPACA_PAPER_DRY_RUN_REQUIRED_FIELDS - set(phase5_alpaca_dry_run)
    )
    if missing_phase5_alpaca_dry_run_fields:
        print(
            "cockpit_status_phase5_alpaca_paper_dry_run_fields_missing="
            + ",".join(missing_phase5_alpaca_dry_run_fields)
        )
        return 1
    if (
        phase5_alpaca_dry_run.get("phase") != "Q5"
        or phase5_alpaca_dry_run.get("stage") != "Q5-7"
    ):
        print("cockpit_status_phase5_alpaca_paper_dry_run_phase_or_stage_mismatch=true")
        return 1
    if phase5_alpaca_dry_run.get("public_safe") is not True:
        print("cockpit_status_phase5_alpaca_paper_dry_run_not_public_safe=true")
        return 1
    if phase5_alpaca_dry_run.get("recorded") is not True:
        print("cockpit_status_phase5_alpaca_paper_dry_run_not_recorded=true")
        return 1
    if phase5_alpaca_dry_run.get("status") != "ok":
        print("cockpit_status_phase5_alpaca_paper_dry_run_not_ok=true")
        return 1
    if phase5_alpaca_dry_run.get("validation_error_count") != 0:
        print("cockpit_status_phase5_alpaca_paper_dry_run_validation_errors=true")
        return 1
    if phase5_alpaca_dry_run.get("event_log_written") is not True:
        print("cockpit_status_phase5_alpaca_paper_dry_run_event_log_not_written=true")
        return 1
    if phase5_alpaca_dry_run.get("event_log_event_count") != phase5_alpaca_dry_run.get(
        "dry_run_record_count"
    ):
        print("cockpit_status_phase5_alpaca_paper_dry_run_event_log_count_mismatch=true")
        return 1
    if phase5_alpaca_dry_run.get("dry_run_record_count") != phase5_alpaca_dry_run.get(
        "source_staging_record_count"
    ):
        print("cockpit_status_phase5_alpaca_paper_dry_run_record_count_mismatch=true")
        return 1
    if phase5_alpaca_dry_run.get("source_staged_order_count") == 0:
        if phase5_alpaca_dry_run.get("request_preview_count") != 0:
            print("cockpit_status_phase5_alpaca_paper_dry_run_preview_without_staged=true")
            return 1
        if phase5_alpaca_dry_run.get("dry_run_receipt_count") != 0:
            print("cockpit_status_phase5_alpaca_paper_dry_run_receipt_without_staged=true")
            return 1
        if phase5_alpaca_dry_run.get("blocked_count") != phase5_alpaca_dry_run.get(
            "dry_run_record_count"
        ):
            print("cockpit_status_phase5_alpaca_paper_dry_run_blocked_count_mismatch=true")
            return 1
    for key in (
        "paper_order_submission_allowed",
        "paper_order_allowed",
        "paper_order_submitted",
        "broker_write_allowed",
        "broker_post_called",
        "alpaca_post_called",
        "execution_allowed",
        "live_endpoint_allowed",
        "live_capital_enabled",
    ):
        if phase5_alpaca_dry_run.get(key) is not False:
            print(f"cockpit_status_phase5_alpaca_paper_dry_run_authority_enabled={key}")
            return 1
    for key in (
        "secret_value_exposed_count",
        "raw_payload_exposed_count",
        "local_path_exposed_count",
        "idempotency_collision_count",
        "duplicate_guard_collision_count",
    ):
        if phase5_alpaca_dry_run.get(key) != 0:
            print(f"cockpit_status_phase5_alpaca_paper_dry_run_count_nonzero={key}")
            return 1
    if "cannot call Alpaca POST routes" not in phase5_alpaca_dry_run.get("boundary", ""):
        print("cockpit_status_phase5_alpaca_paper_dry_run_boundary_weak=true")
        return 1
    missing_phase5_paper_submit_enablement_fields = sorted(
        PHASE5_PAPER_SUBMIT_ENABLEMENT_REQUIRED_FIELDS - set(phase5_paper_submit_enablement)
    )
    if missing_phase5_paper_submit_enablement_fields:
        print(
            "cockpit_status_phase5_paper_submit_enablement_fields_missing="
            + ",".join(missing_phase5_paper_submit_enablement_fields)
        )
        return 1
    if (
        phase5_paper_submit_enablement.get("phase") != "Q5"
        or phase5_paper_submit_enablement.get("stage") != "Q5-8"
    ):
        print("cockpit_status_phase5_paper_submit_enablement_phase_or_stage_mismatch=true")
        return 1
    if phase5_paper_submit_enablement.get("public_safe") is not True:
        print("cockpit_status_phase5_paper_submit_enablement_not_public_safe=true")
        return 1
    if phase5_paper_submit_enablement.get("recorded") is not True:
        print("cockpit_status_phase5_paper_submit_enablement_not_recorded=true")
        return 1
    if phase5_paper_submit_enablement.get("status") != "ok":
        print("cockpit_status_phase5_paper_submit_enablement_not_ok=true")
        return 1
    if phase5_paper_submit_enablement.get("validation_error_count") != 0:
        print("cockpit_status_phase5_paper_submit_enablement_validation_errors=true")
        return 1
    if phase5_paper_submit_enablement.get("event_log_written") is not True:
        print("cockpit_status_phase5_paper_submit_enablement_event_log_not_written=true")
        return 1
    if phase5_paper_submit_enablement.get(
        "event_log_event_count"
    ) != phase5_paper_submit_enablement.get("submit_enablement_record_count"):
        print("cockpit_status_phase5_paper_submit_enablement_event_log_count_mismatch=true")
        return 1
    if phase5_paper_submit_enablement.get(
        "submit_enablement_record_count"
    ) != phase5_paper_submit_enablement.get("source_dry_run_record_count"):
        print("cockpit_status_phase5_paper_submit_enablement_record_count_mismatch=true")
        return 1
    if phase5_paper_submit_enablement.get("paper_submit_approval_present") is False:
        if phase5_paper_submit_enablement.get("submit_path_available_count") != 0:
            print("cockpit_status_phase5_paper_submit_enablement_path_without_approval=true")
            return 1
        if phase5_paper_submit_enablement.get("submit_path_available") is not False:
            print("cockpit_status_phase5_paper_submit_enablement_path_flag_without_approval=true")
            return 1
        if phase5_paper_submit_enablement.get("blocked_count") != phase5_paper_submit_enablement.get(
            "submit_enablement_record_count"
        ):
            print("cockpit_status_phase5_paper_submit_enablement_blocked_count_mismatch=true")
            return 1
    if phase5_paper_submit_enablement.get("broker_submit_receipt_created_count") != (
        phase5_paper_submit_enablement.get("paper_order_submitted_count")
    ):
        print("cockpit_status_phase5_paper_submit_enablement_receipt_count_mismatch=true")
        return 1
    for key in (
        "execution_adapter_write_authority",
        "paper_execution_allowed",
        "paper_order_submission_allowed",
        "paper_order_allowed",
        "paper_order_submitted",
        "broker_write_allowed",
        "broker_post_called",
        "alpaca_post_called",
        "prediction_market_write_allowed",
        "live_endpoint_allowed",
        "live_capital_enabled",
    ):
        if phase5_paper_submit_enablement.get("paper_submit_approval_present") is False:
            if phase5_paper_submit_enablement.get(key) is not False:
                print(f"cockpit_status_phase5_paper_submit_enablement_authority_enabled={key}")
                return 1
    for key in (
        "broker_post_called_count",
        "alpaca_post_called_count",
        "live_capital_enabled_count",
        "live_endpoint_allowed_count",
        "prediction_market_write_allowed_count",
        "secret_value_exposed_count",
        "raw_payload_exposed_count",
        "local_path_exposed_count",
        "authorization_header_exposed_count",
        "base_url_exposed_count",
        "idempotency_collision_count",
        "duplicate_guard_collision_count",
    ):
        if phase5_paper_submit_enablement.get(key) != 0:
            print(f"cockpit_status_phase5_paper_submit_enablement_count_nonzero={key}")
            return 1
    if "single guarded Alpaca paper POST path" not in phase5_paper_submit_enablement.get(
        "boundary",
        "",
    ):
        print("cockpit_status_phase5_paper_submit_enablement_boundary_weak=true")
        return 1
    missing_phase5_prediction_market_adapter_fields = sorted(
        PHASE5_PREDICTION_MARKET_ADAPTER_REQUIRED_FIELDS - set(phase5_prediction_market_adapter)
    )
    if missing_phase5_prediction_market_adapter_fields:
        print(
            "cockpit_status_phase5_prediction_market_adapter_fields_missing="
            + ",".join(missing_phase5_prediction_market_adapter_fields)
        )
        return 1
    if (
        phase5_prediction_market_adapter.get("phase") != "Q5"
        or phase5_prediction_market_adapter.get("stage") != "Q5-9"
    ):
        print("cockpit_status_phase5_prediction_market_adapter_phase_or_stage_mismatch=true")
        return 1
    if phase5_prediction_market_adapter.get("public_safe") is not True:
        print("cockpit_status_phase5_prediction_market_adapter_not_public_safe=true")
        return 1
    if phase5_prediction_market_adapter.get("recorded") is not True:
        print("cockpit_status_phase5_prediction_market_adapter_not_recorded=true")
        return 1
    if phase5_prediction_market_adapter.get("status") != "ok":
        print("cockpit_status_phase5_prediction_market_adapter_not_ok=true")
        return 1
    if phase5_prediction_market_adapter.get("validation_error_count") != 0:
        print("cockpit_status_phase5_prediction_market_adapter_validation_errors=true")
        return 1
    if phase5_prediction_market_adapter.get("event_log_written") is not True:
        print("cockpit_status_phase5_prediction_market_adapter_event_log_not_written=true")
        return 1
    if phase5_prediction_market_adapter.get(
        "event_log_event_count"
    ) != phase5_prediction_market_adapter.get("route_count"):
        print("cockpit_status_phase5_prediction_market_adapter_event_log_count_mismatch=true")
        return 1
    if phase5_prediction_market_adapter.get("prediction_market_route_count") != 2:
        print("cockpit_status_phase5_prediction_market_adapter_route_count_mismatch=true")
        return 1
    if phase5_prediction_market_adapter.get("read_only_route_count") != 2:
        print("cockpit_status_phase5_prediction_market_adapter_read_only_count_mismatch=true")
        return 1
    if phase5_prediction_market_adapter.get("prediction_market_context_count") != 2:
        print("cockpit_status_phase5_prediction_market_adapter_context_count_mismatch=true")
        return 1
    if phase5_prediction_market_adapter.get("policy_risk_caution_context_count") != 2:
        print("cockpit_status_phase5_prediction_market_adapter_policy_context_count_mismatch=true")
        return 1
    if phase5_prediction_market_adapter.get("guarded_placeholder_count") != (
        phase5_prediction_market_adapter.get("route_count")
    ):
        print("cockpit_status_phase5_prediction_market_adapter_placeholder_count_mismatch=true")
        return 1
    if phase5_prediction_market_adapter.get("paper_not_available_count") != 2:
        print("cockpit_status_phase5_prediction_market_adapter_paper_not_available_count_mismatch=true")
        return 1
    if phase5_prediction_market_adapter.get("live_blocked_count") != 4:
        print("cockpit_status_phase5_prediction_market_adapter_live_blocked_count_mismatch=true")
        return 1
    if phase5_prediction_market_adapter.get("preference_provenance_status") != "validated":
        print("cockpit_status_phase5_prediction_market_adapter_preference_not_validated=true")
        return 1
    if phase5_prediction_market_adapter.get(
        "preference_context_status"
    ) != "explicit_multi_upstream_context":
        print("cockpit_status_phase5_prediction_market_adapter_preference_context_mismatch=true")
        return 1
    for key in (
        "preference_counts_as_canonical_source",
        "preference_only_source_quorum_allowed",
        "preference_source_quorum_credit_allowed",
        "strategy_source_quorum_credit_allowed",
        "prediction_market_write_allowed",
        "paper_order_allowed",
        "paper_order_submitted",
        "broker_write_allowed",
        "crypto_perps_write_allowed",
        "paid_preference_tools_allowed",
        "live_endpoint_allowed",
        "live_capital_enabled",
    ):
        if phase5_prediction_market_adapter.get(key) is not False:
            print(f"cockpit_status_phase5_prediction_market_adapter_authority_enabled={key}")
            return 1
    for key in (
        "prediction_market_write_allowed_count",
        "prediction_market_order_allowed_count",
        "prediction_market_spend_allowed_count",
        "prediction_market_live_order_allowed_count",
        "crypto_perps_write_allowed_count",
        "paid_preference_tools_allowed_count",
        "paper_order_allowed_count",
        "paper_order_submitted_count",
        "broker_write_allowed_count",
        "broker_post_called_count",
        "live_endpoint_allowed_count",
        "live_capital_enabled_count",
        "secret_value_exposed_count",
        "raw_payload_exposed_count",
        "local_path_exposed_count",
        "authorization_header_exposed_count",
        "base_url_exposed_count",
    ):
        if phase5_prediction_market_adapter.get(key) != 0:
            print(f"cockpit_status_phase5_prediction_market_adapter_count_nonzero={key}")
            return 1
    if "Polymarket and Kalshi context" not in phase5_prediction_market_adapter.get(
        "boundary",
        "",
    ):
        print("cockpit_status_phase5_prediction_market_adapter_boundary_weak=true")
        return 1
    missing_phase5_telegram_notifier_fields = sorted(
        PHASE5_TELEGRAM_NOTIFIER_REQUIRED_FIELDS - set(phase5_telegram_notifier)
    )
    if missing_phase5_telegram_notifier_fields:
        print(
            "cockpit_status_phase5_telegram_notifier_fields_missing="
            + ",".join(missing_phase5_telegram_notifier_fields)
        )
        return 1
    if (
        phase5_telegram_notifier.get("phase") != "Q5"
        or phase5_telegram_notifier.get("stage") != "Q5-10"
    ):
        print("cockpit_status_phase5_telegram_notifier_phase_or_stage_mismatch=true")
        return 1
    if phase5_telegram_notifier.get("public_safe") is not True:
        print("cockpit_status_phase5_telegram_notifier_not_public_safe=true")
        return 1
    if phase5_telegram_notifier.get("recorded") is not True:
        print("cockpit_status_phase5_telegram_notifier_not_recorded=true")
        return 1
    if phase5_telegram_notifier.get("status") != "ok":
        print("cockpit_status_phase5_telegram_notifier_not_ok=true")
        return 1
    if phase5_telegram_notifier.get("validation_error_count") != 0:
        print("cockpit_status_phase5_telegram_notifier_validation_errors=true")
        return 1
    if phase5_telegram_notifier.get("event_log_written") is not True:
        print("cockpit_status_phase5_telegram_notifier_event_log_not_written=true")
        return 1
    if phase5_telegram_notifier.get("event_log_event_count") != phase5_telegram_notifier.get(
        "notification_record_count"
    ):
        print("cockpit_status_phase5_telegram_notifier_event_log_count_mismatch=true")
        return 1
    if phase5_telegram_notifier.get("alert_type_count") != 9:
        print("cockpit_status_phase5_telegram_notifier_alert_type_count_mismatch=true")
        return 1
    if phase5_telegram_notifier.get("notification_record_count") != 9:
        print("cockpit_status_phase5_telegram_notifier_record_count_mismatch=true")
        return 1
    if phase5_telegram_notifier.get("eligible_alert_count", 0) < 3:
        print("cockpit_status_phase5_telegram_notifier_eligible_alerts_missing=true")
        return 1
    if phase5_telegram_notifier.get("queued_dry_run_alert_count") != phase5_telegram_notifier.get(
        "eligible_alert_count"
    ):
        print("cockpit_status_phase5_telegram_notifier_queued_count_mismatch=true")
        return 1
    if phase5_telegram_notifier.get("outbox_message_written_count") != phase5_telegram_notifier.get(
        "eligible_alert_count"
    ):
        print("cockpit_status_phase5_telegram_notifier_outbox_count_mismatch=true")
        return 1
    if phase5_telegram_notifier.get("telegram_mode") != "dry_run":
        print("cockpit_status_phase5_telegram_notifier_mode_not_dry_run=true")
        return 1
    if phase5_telegram_notifier.get("telegram_send_gate") != "disabled":
        print("cockpit_status_phase5_telegram_notifier_send_gate_enabled=true")
        return 1
    if phase5_telegram_notifier.get("private_send_test_allowed") is not False:
        print("cockpit_status_phase5_telegram_notifier_private_send_test_allowed=true")
        return 1
    for key in (
        "telegram_command_path_enabled",
        "telegram_live_notifications_allowed",
        "paper_order_allowed",
        "paper_order_submitted",
        "broker_write_allowed",
        "live_capital_enabled",
        "normal_live_notification_allowed",
    ):
        if phase5_telegram_notifier.get(key) is not False:
            print(f"cockpit_status_phase5_telegram_notifier_authority_enabled={key}")
            return 1
    for key in (
        "telegram_command_path_enabled_count",
        "telegram_trade_command_enabled_count",
        "telegram_place_trade_command_enabled_count",
        "telegram_approve_trade_command_enabled_count",
        "telegram_reject_trade_command_enabled_count",
        "telegram_modify_trade_command_enabled_count",
        "telegram_resize_trade_command_enabled_count",
        "telegram_close_trade_command_enabled_count",
        "telegram_cancel_trade_command_enabled_count",
        "telegram_live_notifications_allowed_count",
        "live_send_allowed_count",
        "broker_write_allowed_count",
        "broker_post_called_count",
        "paper_order_allowed_count",
        "paper_order_submitted_count",
        "execution_allowed_count",
        "prediction_market_write_allowed_count",
        "live_endpoint_allowed_count",
        "live_capital_enabled_count",
        "secret_value_exposed_count",
        "raw_payload_exposed_count",
        "local_path_exposed_count",
        "authorization_header_exposed_count",
        "chat_id_exposed_count",
        "bot_token_exposed_count",
    ):
        if phase5_telegram_notifier.get(key) != 0:
            print(f"cockpit_status_phase5_telegram_notifier_count_nonzero={key}")
            return 1
    if (
        "cannot place, approve, reject, modify, resize, close, or cancel trades"
        not in phase5_telegram_notifier.get("boundary", "")
    ):
        print("cockpit_status_phase5_telegram_notifier_boundary_weak=true")
        return 1
    missing_phase5_position_monitor_fields = sorted(
        PHASE5_POSITION_MONITOR_REQUIRED_FIELDS - set(phase5_position_monitor)
    )
    if missing_phase5_position_monitor_fields:
        print(
            "cockpit_status_phase5_position_monitor_fields_missing="
            + ",".join(missing_phase5_position_monitor_fields)
        )
        return 1
    if (
        phase5_position_monitor.get("phase") != "Q5"
        or phase5_position_monitor.get("stage") != "Q5-11"
    ):
        print("cockpit_status_phase5_position_monitor_phase_or_stage_mismatch=true")
        return 1
    if phase5_position_monitor.get("public_safe") is not True:
        print("cockpit_status_phase5_position_monitor_not_public_safe=true")
        return 1
    if phase5_position_monitor.get("recorded") is not True:
        print("cockpit_status_phase5_position_monitor_not_recorded=true")
        return 1
    if phase5_position_monitor.get("status") != "ok":
        print("cockpit_status_phase5_position_monitor_not_ok=true")
        return 1
    if phase5_position_monitor.get("validation_error_count") != 0:
        print("cockpit_status_phase5_position_monitor_validation_errors=true")
        return 1
    if phase5_position_monitor.get("event_log_written") is not True:
        print("cockpit_status_phase5_position_monitor_event_log_not_written=true")
        return 1
    if phase5_position_monitor.get("event_log_event_count") != phase5_position_monitor.get(
        "monitor_record_count"
    ):
        print("cockpit_status_phase5_position_monitor_event_log_count_mismatch=true")
        return 1
    if phase5_position_monitor.get("monitor_record_count") != (
        phase5_position_monitor.get("position_record_count")
        + phase5_position_monitor.get("closed_trade_summary_count")
    ):
        print("cockpit_status_phase5_position_monitor_record_count_mismatch=true")
        return 1
    if phase5_position_monitor.get("lifecycle_state_count") != 9:
        print("cockpit_status_phase5_position_monitor_lifecycle_state_count_mismatch=true")
        return 1
    if phase5_position_monitor.get("failed_reconciliation_count") != 0:
        print("cockpit_status_phase5_position_monitor_reconciliation_failures_present=true")
        return 1
    if phase5_position_monitor.get("postmortem_due_count", 0) > phase5_position_monitor.get(
        "closed_trade_count",
        0,
    ):
        print("cockpit_status_phase5_position_monitor_postmortem_due_exceeds_closed=true")
        return 1
    for key in (
        "position_monitor_write_authority",
        "paper_order_allowed",
        "paper_order_submitted",
        "broker_write_allowed",
        "live_capital_enabled",
    ):
        if phase5_position_monitor.get(key) is not False:
            print(f"cockpit_status_phase5_position_monitor_authority_enabled={key}")
            return 1
    for key in (
        "execution_allowed_count",
        "paper_order_allowed_count",
        "paper_order_submitted_count",
        "broker_write_allowed_count",
        "broker_post_called_count",
        "alpaca_post_called_count",
        "telegram_live_notifications_allowed_count",
        "position_created_count",
        "position_monitor_write_authority_count",
        "position_close_allowed_count",
        "position_resize_allowed_count",
        "order_cancel_allowed_count",
        "live_capital_enabled_count",
        "secret_value_exposed_count",
        "raw_payload_exposed_count",
        "local_path_exposed_count",
        "authorization_header_exposed_count",
        "account_identifier_exposed_count",
        "broker_order_identifier_exposed_count",
    ):
        if phase5_position_monitor.get(key) != 0:
            print(f"cockpit_status_phase5_position_monitor_count_nonzero={key}")
            return 1
    if "cannot submit, close, resize, cancel" not in phase5_position_monitor.get(
        "boundary",
        "",
    ):
        print("cockpit_status_phase5_position_monitor_boundary_weak=true")
        return 1
    missing_phase5_signal_review_fields = sorted(
        PHASE5_SIGNAL_REVIEW_REQUIRED_FIELDS - set(phase5_signal_review)
    )
    if missing_phase5_signal_review_fields:
        print(
            "cockpit_status_phase5_signal_review_fields_missing="
            + ",".join(missing_phase5_signal_review_fields)
        )
        return 1
    if (
        phase5_signal_review.get("phase") != "Q5"
        or phase5_signal_review.get("stage") != "Q5-12"
    ):
        print("cockpit_status_phase5_signal_review_phase_or_stage_mismatch=true")
        return 1
    if phase5_signal_review.get("public_safe") is not True:
        print("cockpit_status_phase5_signal_review_not_public_safe=true")
        return 1
    if phase5_signal_review.get("recorded") is not True:
        print("cockpit_status_phase5_signal_review_not_recorded=true")
        return 1
    if phase5_signal_review.get("status") != "ok":
        print("cockpit_status_phase5_signal_review_not_ok=true")
        return 1
    if phase5_signal_review.get("validation_error_count") != 0:
        print("cockpit_status_phase5_signal_review_validation_errors=true")
        return 1
    if phase5_signal_review.get("backend_validation_error_count") != 0:
        print("cockpit_status_phase5_signal_review_backend_validation_errors=true")
        return 1
    if phase5_signal_review.get("pricing_gap_rollout_stage") not in {"stage_a", "stage_b"}:
        print("cockpit_status_phase5_signal_review_rollout_stage_invalid=true")
        return 1
    for key in (
        "funnel_shadow_signal_count",
        "funnel_review_count",
        "funnel_signals_with_market_confirmation_count",
        "funnel_signals_with_pricing_gap_evidence_count",
        "funnel_signals_blocked_only_by_missing_pricing_gap_count",
        "funnel_signals_passed_to_risk_count",
        "funnel_risk_reviews_blocked_only_by_pricing_gap_policy_count",
        "funnel_stage_b_candidate_signal_count",
        "funnel_flagged_missing_pricing_gap_producer_count",
    ):
        if int(phase5_signal_review.get(key, 0) or 0) < 0:
            print(f"cockpit_status_phase5_signal_review_negative_count={key}")
            return 1
    if phase5_signal_review.get("event_log_written") is not True:
        print("cockpit_status_phase5_signal_review_event_log_not_written=true")
        return 1
    expected_signal_review_events = (
        phase5_signal_review.get("signal_review_record_count")
        + phase5_signal_review.get("governance_comment_event_count")
        + phase5_signal_review.get("kill_switch_action_event_count")
    )
    if phase5_signal_review.get("event_log_event_count") != expected_signal_review_events:
        print("cockpit_status_phase5_signal_review_event_log_count_mismatch=true")
        return 1
    if phase5_signal_review.get("chain_step_count") != 9:
        print("cockpit_status_phase5_signal_review_chain_step_count_mismatch=true")
        return 1
    if phase5_signal_review.get("decision_chain_count") != (
        phase5_signal_review.get("signal_review_record_count") * 9
    ):
        print("cockpit_status_phase5_signal_review_decision_chain_count_mismatch=true")
        return 1
    if phase5_signal_review.get("backend_truth_displayed_count") != phase5_signal_review.get(
        "signal_review_record_count"
    ):
        print("cockpit_status_phase5_signal_review_backend_truth_count_mismatch=true")
        return 1
    if phase5_signal_review.get("ui_inferred_readiness_count") != 0:
        print("cockpit_status_phase5_signal_review_inferred_readiness_present=true")
        return 1
    if phase5_signal_review.get("governance_comment_event_count") != phase5_signal_review.get(
        "signal_review_record_count"
    ):
        print("cockpit_status_phase5_signal_review_comment_event_count_mismatch=true")
        return 1
    if phase5_signal_review.get("kill_switch_action_event_count") != phase5_signal_review.get(
        "signal_review_record_count"
    ):
        print("cockpit_status_phase5_signal_review_kill_action_event_count_mismatch=true")
        return 1
    if phase5_signal_review.get("kill_switch_action_available_count") != phase5_signal_review.get(
        "signal_review_record_count"
    ):
        print("cockpit_status_phase5_signal_review_kill_action_available_count_mismatch=true")
        return 1
    for key in (
        "paper_order_allowed",
        "paper_order_submitted",
        "broker_write_allowed",
        "prediction_market_write_allowed",
        "kill_switch_mutation_authority",
        "live_capital_enabled",
    ):
        if phase5_signal_review.get(key) is not False:
            print(f"cockpit_status_phase5_signal_review_authority_enabled={key}")
            return 1
    for key in (
        "trade_approval_control_enabled_count",
        "trade_rejection_control_enabled_count",
        "order_place_control_enabled_count",
        "order_modify_control_enabled_count",
        "position_resize_control_enabled_count",
        "position_close_control_enabled_count",
        "order_cancel_control_enabled_count",
        "kill_switch_mutation_authority_count",
        "kill_switch_action_mutates_state_count",
        "broker_write_allowed_count",
        "broker_post_called_count",
        "alpaca_post_called_count",
        "prediction_market_write_allowed_count",
        "paper_order_allowed_count",
        "paper_order_submitted_count",
        "telegram_command_path_enabled_count",
        "live_endpoint_allowed_count",
        "live_capital_enabled_count",
        "secret_value_exposed_count",
        "raw_payload_exposed_count",
        "local_path_exposed_count",
        "authorization_header_exposed_count",
        "account_identifier_exposed_count",
        "broker_order_identifier_exposed_count",
    ):
        if phase5_signal_review.get(key) != 0:
            print(f"cockpit_status_phase5_signal_review_count_nonzero={key}")
            return 1
    for record in phase5_signal_review.get("records", []):
        if record.get("backend_truth_displayed") is not True:
            print("cockpit_status_phase5_signal_review_record_not_backend_truth=true")
            return 1
        if record.get("ui_inferred_readiness") is not False:
            print("cockpit_status_phase5_signal_review_record_inferred_readiness=true")
            return 1
        action = record.get("governance_action", {})
        if not action.get("target_artifact_id"):
            print("cockpit_status_phase5_signal_review_governance_action_target_missing=true")
            return 1
        if action.get("comment_event_log_written") is not True:
            print("cockpit_status_phase5_signal_review_comment_event_not_written=true")
            return 1
        if action.get("kill_switch_action_event_log_written") is not True:
            print("cockpit_status_phase5_signal_review_kill_action_event_not_written=true")
            return 1
        if action.get("kill_switch_mutation_authority") is not False:
            print("cockpit_status_phase5_signal_review_kill_mutation_authority=true")
            return 1
    signal_review_boundary = phase5_signal_review.get("boundary", "")
    if (
        "cannot approve, reject, place, modify, resize, close, or cancel" not in signal_review_boundary
        or "cannot call brokers or venues" not in signal_review_boundary
    ):
        print("cockpit_status_phase5_signal_review_boundary_weak=true")
        return 1
    missing_phase5_paper_trade_drill_fields = sorted(
        PHASE5_PAPER_TRADE_DRILL_REQUIRED_FIELDS - set(phase5_paper_trade_drill)
    )
    if missing_phase5_paper_trade_drill_fields:
        print(
            "cockpit_status_phase5_paper_trade_drill_fields_missing="
            + ",".join(missing_phase5_paper_trade_drill_fields)
        )
        return 1
    if (
        phase5_paper_trade_drill.get("phase") != "Q5"
        or phase5_paper_trade_drill.get("stage") != "Q5-14"
    ):
        print("cockpit_status_phase5_paper_trade_drill_phase_or_stage_mismatch=true")
        return 1
    if phase5_paper_trade_drill.get("public_safe") is not True:
        print("cockpit_status_phase5_paper_trade_drill_not_public_safe=true")
        return 1
    if phase5_paper_trade_drill.get("recorded") is not True:
        print("cockpit_status_phase5_paper_trade_drill_not_recorded=true")
        return 1
    if phase5_paper_trade_drill.get("status") != "ok":
        print("cockpit_status_phase5_paper_trade_drill_not_ok=true")
        return 1
    if phase5_paper_trade_drill.get("validation_error_count") != 0:
        print("cockpit_status_phase5_paper_trade_drill_validation_errors=true")
        return 1
    if phase5_paper_trade_drill.get("event_log_written") is not True:
        print("cockpit_status_phase5_paper_trade_drill_event_log_not_written=true")
        return 1
    if phase5_paper_trade_drill.get("event_log_event_count") != phase5_paper_trade_drill.get(
        "required_step_count"
    ):
        print("cockpit_status_phase5_paper_trade_drill_event_log_count_mismatch=true")
        return 1
    if phase5_paper_trade_drill.get("required_step_count") != 13:
        print("cockpit_status_phase5_paper_trade_drill_required_step_count_mismatch=true")
        return 1
    if phase5_paper_trade_drill.get("step_count") != phase5_paper_trade_drill.get(
        "required_step_count"
    ):
        print("cockpit_status_phase5_paper_trade_drill_step_count_mismatch=true")
        return 1
    if (
        phase5_paper_trade_drill.get("phase5_paper_trade_drill_implementation_ready")
        is not True
    ):
        print("cockpit_status_phase5_paper_trade_drill_not_implementation_ready=true")
        return 1
    if phase5_paper_trade_drill.get("phase7_proof_credit_allowed") is not False:
        print("cockpit_status_phase5_paper_trade_drill_phase7_credit_allowed=true")
        return 1
    if (
        phase5_paper_trade_drill.get("paper_trade_drill_complete") is True
        and phase5_paper_trade_drill.get("phase5_paper_trade_drill_exit_gate_passed") is not True
    ):
        print("cockpit_status_phase5_paper_trade_drill_complete_without_exit_gate=true")
        return 1
    if (
        phase5_paper_trade_drill.get("phase5_paper_trade_drill_exit_gate_passed") is True
        and phase5_paper_trade_drill.get("paper_submit_approval_present") is not True
    ):
        print("cockpit_status_phase5_paper_trade_drill_exit_without_approval=true")
        return 1
    if (
        phase5_paper_trade_drill.get("paper_submit_approval_present") is not True
        and "paper_submit_approval_missing" not in phase5_paper_trade_drill.get("blockers", [])
    ):
        print("cockpit_status_phase5_paper_trade_drill_missing_approval_blocker=true")
        return 1
    if (
        phase5_paper_trade_drill.get("paper_submit_path_available_count") == 0
        and "paper_submit_path_unavailable" not in phase5_paper_trade_drill.get("blockers", [])
    ):
        print("cockpit_status_phase5_paper_trade_drill_missing_submit_path_blocker=true")
        return 1
    if phase5_paper_trade_drill.get("paper_trade_drill_complete") is True:
        for key in (
            "submitted_paper_order_count",
            "closed_trade_count",
            "postmortem_due_count",
        ):
            if phase5_paper_trade_drill.get(key, 0) <= 0:
                print(f"cockpit_status_phase5_paper_trade_drill_complete_missing={key}")
                return 1
        if phase5_paper_trade_drill.get("position_open_lifecycle_satisfied") is not True:
            print("cockpit_status_phase5_paper_trade_drill_complete_missing_position_open_lifecycle=true")
            return 1
    for key in (
        "broker_write_allowed_count",
        "broker_post_called_count",
        "alpaca_post_called_count",
        "prediction_market_write_allowed_count",
        "telegram_live_notifications_allowed_count",
        "position_monitor_write_authority_count",
        "position_close_allowed_count",
        "position_resize_allowed_count",
        "order_cancel_allowed_count",
        "live_capital_enabled_count",
        "live_endpoint_allowed_count",
        "phase7_proof_credit_allowed_count",
        "secret_value_exposed_count",
        "raw_payload_exposed_count",
        "local_path_exposed_count",
        "authorization_header_exposed_count",
        "broker_order_identifier_exposed_count",
    ):
        if phase5_paper_trade_drill.get(key) != 0:
            print(f"cockpit_status_phase5_paper_trade_drill_count_nonzero={key}")
            return 1
    if (
        phase5_paper_trade_drill.get("broker_post_called_count") != 0
        and phase5_paper_trade_drill.get("phase5_paper_trade_drill_exit_gate_passed")
        is not True
    ):
        print("cockpit_status_phase5_paper_trade_drill_broker_post_before_exit=true")
        return 1
    if (
        phase5_paper_trade_drill.get("alpaca_post_called_count") != 0
        and phase5_paper_trade_drill.get("phase5_paper_trade_drill_exit_gate_passed")
        is not True
    ):
        print("cockpit_status_phase5_paper_trade_drill_alpaca_post_before_exit=true")
        return 1
    for record in phase5_paper_trade_drill.get("records", []):
        if record.get("display_status") != record.get("backend_status"):
            print("cockpit_status_phase5_paper_trade_drill_record_status_mismatch=true")
            return 1
        if record.get("display_derived_from_backend") is not True:
            print("cockpit_status_phase5_paper_trade_drill_record_not_backend_derived=true")
            return 1
        if record.get("ui_inferred_readiness") is not False:
            print("cockpit_status_phase5_paper_trade_drill_record_inferred_readiness=true")
            return 1
        for key in (
            "broker_post_called",
            "broker_write_allowed",
            "live_capital_enabled",
            "phase7_proof_credit_allowed",
        ):
            if record.get(key) is not False:
                print(f"cockpit_status_phase5_paper_trade_drill_record_flag_enabled={key}")
                return 1
    paper_trade_drill_boundary = phase5_paper_trade_drill.get("boundary", "")
    if (
        "cannot bypass explicit paper-submit approval" not in paper_trade_drill_boundary
        or "cannot call brokers or venues" not in paper_trade_drill_boundary
        or "cannot enable live capital" not in paper_trade_drill_boundary
        or "cannot count toward Phase 7 proof" not in paper_trade_drill_boundary
    ):
        print("cockpit_status_phase5_paper_trade_drill_boundary_weak=true")
        return 1
    missing_phase5_certification_fields = sorted(
        PHASE5_CERTIFICATION_REQUIRED_FIELDS - set(phase5_certification)
    )
    if missing_phase5_certification_fields:
        print(
            "cockpit_status_phase5_certification_fields_missing="
            + ",".join(missing_phase5_certification_fields)
        )
        return 1
    if (
        phase5_certification.get("phase") != "Q5"
        or phase5_certification.get("stage") != "Q5-15"
    ):
        print("cockpit_status_phase5_certification_phase_or_stage_mismatch=true")
        return 1
    if phase5_certification.get("public_safe") is not True:
        print("cockpit_status_phase5_certification_not_public_safe=true")
        return 1
    if phase5_certification.get("recorded") is not True:
        print("cockpit_status_phase5_certification_not_recorded=true")
        return 1
    if phase5_certification.get("status") not in {"blocked", "eligible"}:
        print("cockpit_status_phase5_certification_status_invalid=true")
        return 1
    if phase5_certification.get("validation_error_count") != 0:
        print("cockpit_status_phase5_certification_validation_errors=true")
        return 1
    if phase5_certification.get("event_log_written") is not True:
        print("cockpit_status_phase5_certification_event_log_not_written=true")
        return 1
    if phase5_certification.get("event_log_event_count") != 1:
        print("cockpit_status_phase5_certification_event_log_count_mismatch=true")
        return 1
    if phase5_certification.get("q5_stage_count") != 16:
        print("cockpit_status_phase5_certification_stage_count_mismatch=true")
        return 1
    if phase5_certification.get("required_input_stage_count") != 15:
        print("cockpit_status_phase5_certification_input_stage_count_mismatch=true")
        return 1
    if phase5_certification.get("input_gate_count") != 15:
        print("cockpit_status_phase5_certification_gate_count_mismatch=true")
        return 1
    if phase5_certification.get("input_gate_blocked_count") != (
        phase5_certification.get("input_gate_count", 0)
        - phase5_certification.get("input_gate_passed_count", 0)
    ):
        print("cockpit_status_phase5_certification_blocked_gate_count_mismatch=true")
        return 1
    if phase5_certification.get("phase7_proof_credit_allowed") is not False:
        print("cockpit_status_phase5_certification_phase7_credit_allowed=true")
        return 1
    if phase5_certification.get("phase7_proof_credit_allowed_count") != 0:
        print("cockpit_status_phase5_certification_phase7_credit_count_nonzero=true")
        return 1
    if phase5_certification.get("blocking_unsafe_count") != 0:
        print("cockpit_status_phase5_certification_blocking_unsafe_count_nonzero=true")
        return 1
    for key in (
        "broker_write_allowed_count",
        "prediction_market_write_allowed_count",
        "crypto_perps_write_allowed_count",
        "telegram_live_notifications_allowed_count",
        "live_endpoint_allowed_count",
        "live_capital_enabled_count",
    ):
        if phase5_certification.get(key) != 0:
            print(f"cockpit_status_phase5_certification_count_nonzero={key}")
            return 1
    if phase5_certification.get("phase5_certified") is True:
        if phase5_certification.get("status") != "eligible":
            print("cockpit_status_phase5_certification_certified_not_eligible=true")
            return 1
        for key in (
            "phase5_complete",
            "phase5_exit_gate",
            "phase6_handoff_allowed",
            "phase7_planning_allowed",
            "paper_trade_drill_complete",
            "paper_trade_drill_exit_gate_passed",
        ):
            if phase5_certification.get(key) is not True:
                print(f"cockpit_status_phase5_certification_missing_true={key}")
                return 1
        for key in (
            "submitted_paper_order_count",
            "open_position_count",
            "closed_trade_count",
            "postmortem_due_count",
        ):
            if phase5_certification.get(key, 0) <= 0:
                print(f"cockpit_status_phase5_certification_missing_count={key}")
                return 1
    else:
        if phase5_certification.get("status") != "blocked":
            print("cockpit_status_phase5_certification_blocked_status_mismatch=true")
            return 1
        if phase5_certification.get("phase5_exit_gate") is not False:
            print("cockpit_status_phase5_certification_exit_gate_open=true")
            return 1
        if phase5_certification.get("phase6_handoff_allowed") is not False:
            print("cockpit_status_phase5_certification_phase6_handoff_open=true")
            return 1
        if phase5_certification.get("phase7_planning_allowed") is not False:
            print("cockpit_status_phase5_certification_phase7_planning_open=true")
            return 1
        if phase5_certification.get("certification_blocker_count", 0) < 1:
            print("cockpit_status_phase5_certification_blocker_missing=true")
            return 1
        if (
            phase5_certification.get("paper_trade_drill_exit_gate_passed") is not True
            and "q5_14_exit_gate_not_passed"
            not in phase5_certification.get("certification_blockers", [])
        ):
            print("cockpit_status_phase5_certification_q5_14_blocker_missing=true")
            return 1
    for record in phase5_certification.get("gate_records", []):
        if record.get("display_status") != record.get("backend_status"):
            print("cockpit_status_phase5_certification_gate_status_mismatch=true")
            return 1
        if record.get("display_derived_from_backend") is not True:
            print("cockpit_status_phase5_certification_gate_not_backend_derived=true")
            return 1
        if record.get("ui_inferred_readiness") is not False:
            print("cockpit_status_phase5_certification_gate_inferred_readiness=true")
            return 1
        if record.get("phase7_proof_credit_allowed") is not False:
            print("cockpit_status_phase5_certification_gate_phase7_credit=true")
            return 1
    certification_boundary = phase5_certification.get("boundary", "")
    if (
        "cannot bypass Q5-14" not in certification_boundary
        or "cannot call live endpoints" not in certification_boundary
        or "cannot enable live capital" not in certification_boundary
        or "cannot let Phase 5 test trades count toward Phase 7 proof"
        not in certification_boundary
    ):
        print("cockpit_status_phase5_certification_boundary_weak=true")
        return 1
    missing_phase5_phase6_handoff_fields = sorted(
        PHASE5_PHASE6_HANDOFF_REQUIRED_FIELDS - set(phase5_phase6_handoff)
    )
    if missing_phase5_phase6_handoff_fields:
        print(
            "cockpit_status_phase5_phase6_handoff_fields_missing="
            + ",".join(missing_phase5_phase6_handoff_fields)
        )
        return 1
    if (
        phase5_phase6_handoff.get("phase") != "Q5"
        or phase5_phase6_handoff.get("stage") != "Q5E-10"
    ):
        print("cockpit_status_phase5_phase6_handoff_phase_or_stage_mismatch=true")
        return 1
    if phase5_phase6_handoff.get("public_safe") is not True:
        print("cockpit_status_phase5_phase6_handoff_not_public_safe=true")
        return 1
    if phase5_phase6_handoff.get("recorded") is not True:
        print("cockpit_status_phase5_phase6_handoff_not_recorded=true")
        return 1
    if phase5_phase6_handoff.get("status") not in {"eligible", "blocked"}:
        print("cockpit_status_phase5_phase6_handoff_status_invalid=true")
        return 1
    if phase5_phase6_handoff.get("validation_error_count") != 0:
        print("cockpit_status_phase5_phase6_handoff_validation_errors=true")
        return 1
    if phase5_phase6_handoff.get("event_log_written") is not True:
        print("cockpit_status_phase5_phase6_handoff_event_log_not_written=true")
        return 1
    if phase5_phase6_handoff.get("event_log_event_count") != 1:
        print("cockpit_status_phase5_phase6_handoff_event_log_count_mismatch=true")
        return 1
    if phase5_phase6_handoff.get("phase7_proof_credit_allowed") is not False:
        print("cockpit_status_phase5_phase6_handoff_phase7_credit_allowed=true")
        return 1
    if phase5_phase6_handoff.get("phase5_test_trades_count_for_phase7") is not False:
        print("cockpit_status_phase5_phase6_handoff_phase5_trade_credit=true")
        return 1
    for key in (
        "broker_post_called_count",
        "alpaca_post_called_count",
        "broker_write_allowed_count",
        "prediction_market_write_allowed_count",
        "crypto_perps_write_allowed_count",
        "live_endpoint_allowed_count",
        "live_capital_enabled_count",
        "phase7_proof_credit_allowed_count",
        "phase6_learning_write_allowed_count",
        "phase6_knowledge_graph_write_allowed_count",
        "phase6_model_weight_update_allowed_count",
        "phase6_trust_score_update_allowed_count",
        "phase6_policy_mutation_allowed_count",
    ):
        if phase5_phase6_handoff.get(key) != 0:
            print(f"cockpit_status_phase5_phase6_handoff_count_nonzero={key}")
            return 1
    for key in (
        "phase6_learning_loop_implementation_allowed",
        "phase6_postmortem_ingestion_allowed",
        "phase6_learning_write_allowed",
        "phase6_knowledge_graph_write_allowed",
        "phase6_model_weight_update_allowed",
        "phase6_trust_score_update_allowed",
        "phase6_shadow_strategy_runner_allowed",
        "phase6_architect_policy_mutation_allowed",
    ):
        if phase5_phase6_handoff.get(key) is not False:
            print(f"cockpit_status_phase5_phase6_handoff_phase6_authority={key}")
            return 1
    if phase5_phase6_handoff.get("phase6_learning_loop_plan_allowed") is True:
        if phase5_phase6_handoff.get("status") != "eligible":
            print("cockpit_status_phase5_phase6_handoff_plan_not_eligible=true")
            return 1
        if phase5_phase6_handoff.get("handoff_state") != "phase6_learning_loop_plan_ready":
            print("cockpit_status_phase5_phase6_handoff_state_mismatch=true")
            return 1
        if phase5_phase6_handoff.get("blocker_count") != 0:
            print("cockpit_status_phase5_phase6_handoff_blockers_present=true")
            return 1
        for key in (
            "phase5_certified",
            "phase5_exit_gate",
            "phase6_handoff_allowed",
            "phase7_planning_allowed",
            "paper_trade_drill_complete",
            "paper_trade_drill_exit_gate_passed",
            "guarded_postmortem_due_ready",
        ):
            if phase5_phase6_handoff.get(key) is not True:
                print(f"cockpit_status_phase5_phase6_handoff_missing_true={key}")
                return 1
        if phase5_phase6_handoff.get("paper_trade_drill_blocker_count") != 0:
            print("cockpit_status_phase5_phase6_handoff_drill_blockers=true")
            return 1
        for key in (
            "downstream_staging_allowed_count",
            "submitted_order_count",
            "mirrored_order_count",
            "closed_trade_count",
            "postmortem_due_count",
        ):
            if phase5_phase6_handoff.get(key, 0) <= 0:
                print(f"cockpit_status_phase5_phase6_handoff_missing_count={key}")
                return 1
        if phase5_phase6_handoff.get("failed_reconciliation_count") != 0:
            print("cockpit_status_phase5_phase6_handoff_failed_reconciliation=true")
            return 1
        if phase5_phase6_handoff.get("source_validation_error_count") != 0:
            print("cockpit_status_phase5_phase6_handoff_source_errors=true")
            return 1
        if phase5_phase6_handoff.get("source_recorded_count") != phase5_phase6_handoff.get(
            "required_source_count"
        ):
            print("cockpit_status_phase5_phase6_handoff_source_count_mismatch=true")
            return 1
    else:
        if phase5_phase6_handoff.get("status") != "blocked":
            print("cockpit_status_phase5_phase6_handoff_blocked_status_mismatch=true")
            return 1
        if phase5_phase6_handoff.get("blocker_count", 0) < 1:
            print("cockpit_status_phase5_phase6_handoff_blocker_missing=true")
            return 1
    if phase5_phase6_handoff.get("phase6_required_module_count") != len(
        phase5_phase6_handoff.get("phase6_required_modules", [])
    ):
        print("cockpit_status_phase5_phase6_handoff_module_count_mismatch=true")
        return 1
    handoff_boundary = phase5_phase6_handoff.get("boundary", "")
    if (
        "cannot implement Phase 6" not in handoff_boundary
        or "cannot write learning data" not in handoff_boundary
        or "cannot call broker POST routes" not in handoff_boundary
        or "cannot enable live capital" not in handoff_boundary
        or "cannot count Phase 5 test trades toward Phase 7 proof"
        not in handoff_boundary
    ):
        print("cockpit_status_phase5_phase6_handoff_boundary_weak=true")
        return 1
    missing_phase6_learning_loop_fields = sorted(
        set(PHASE6_LEARNING_LOOP_REQUIRED_FIELDS) - set(phase6_learning_loop)
    )
    if missing_phase6_learning_loop_fields:
        print(
            "cockpit_status_phase6_learning_loop_fields_missing="
            + ",".join(missing_phase6_learning_loop_fields)
        )
        return 1
    if phase6_learning_loop.get("phase") != "Q6" or phase6_learning_loop.get("stage") != "Q6-16":
        print("cockpit_status_phase6_learning_loop_phase_or_stage_mismatch=true")
        return 1
    if phase6_learning_loop.get("public_safe") is not True:
        print("cockpit_status_phase6_learning_loop_not_public_safe=true")
        return 1
    if phase6_learning_loop.get("recorded") is not True:
        print("cockpit_status_phase6_learning_loop_not_recorded=true")
        return 1
    if phase6_learning_loop.get("status") != "visible":
        print("cockpit_status_phase6_learning_loop_not_visible=true")
        return 1
    if phase6_learning_loop.get("visibility_state") != "backend_derived_deferred_learning_visible":
        print("cockpit_status_phase6_learning_loop_visibility_state_mismatch=true")
        return 1
    if phase6_learning_loop.get("learning_state") != "deferred_learning_visible":
        print("cockpit_status_phase6_learning_loop_learning_state_mismatch=true")
        return 1
    if phase6_learning_loop.get("backend_derived") is not True:
        print("cockpit_status_phase6_learning_loop_not_backend_derived=true")
        return 1
    if phase6_learning_loop.get("display_derived_from_backend") is not True:
        print("cockpit_status_phase6_learning_loop_display_not_backend_derived=true")
        return 1
    if phase6_learning_loop.get("dashboard_uses_backend_status") is not True:
        print("cockpit_status_phase6_learning_loop_dashboard_not_backend_derived=true")
        return 1
    if phase6_learning_loop.get("ui_inferred_readiness_count") != 0:
        print("cockpit_status_phase6_learning_loop_ui_inferred=true")
        return 1
    if phase6_learning_loop.get("backend_parity_error_count") != 0:
        print("cockpit_status_phase6_learning_loop_parity_errors=true")
        return 1
    if phase6_learning_loop.get("validation_error_count") != 0:
        print("cockpit_status_phase6_learning_loop_validation_errors=true")
        return 1
    if phase6_learning_loop.get("event_log_written") is not True:
        print("cockpit_status_phase6_learning_loop_event_log_missing=true")
        return 1
    if phase6_learning_loop.get("event_log_event_count") != 1:
        print("cockpit_status_phase6_learning_loop_event_log_count_mismatch=true")
        return 1
    if phase6_learning_loop.get("source_missing_count") != 0:
        print("cockpit_status_phase6_learning_loop_source_missing=true")
        return 1
    if phase6_learning_loop.get("source_validation_error_count") != 0:
        print("cockpit_status_phase6_learning_loop_source_validation_errors=true")
        return 1
    if phase6_learning_loop.get("source_artifact_count") != len(
        phase6_learning_loop.get("source_status_records", [])
    ):
        print("cockpit_status_phase6_learning_loop_source_count_mismatch=true")
        return 1
    for record in phase6_learning_loop.get("source_status_records", []):
        if record.get("display_status") != record.get("backend_status"):
            print("cockpit_status_phase6_learning_loop_source_display_mismatch=true")
            return 1
        if record.get("display_derived_from_backend") is not True:
            print("cockpit_status_phase6_learning_loop_source_not_backend_derived=true")
            return 1
        if record.get("ui_inferred_readiness") is not False:
            print("cockpit_status_phase6_learning_loop_source_ui_inferred=true")
            return 1
        if not str(record.get("source_ref", "")).startswith("data/runtime/"):
            print("cockpit_status_phase6_learning_loop_source_ref_invalid=true")
            return 1
    if phase6_learning_loop.get("postmortem_due_count", 0) < 1:
        print("cockpit_status_phase6_learning_loop_postmortem_due_missing=true")
        return 1
    if phase6_learning_loop.get("postmortem_resolved_count") != 0:
        print("cockpit_status_phase6_learning_loop_resolved_unexpected=true")
        return 1
    if phase6_learning_loop.get("approval_state") != "deferred":
        print("cockpit_status_phase6_learning_loop_approval_state_mismatch=true")
        return 1
    if phase6_learning_loop.get("staged_graph_entry_count") != 0:
        print("cockpit_status_phase6_learning_loop_staged_graph_unexpected=true")
        return 1
    for key in (
        "knowledge_graph_read_result_count",
        "model_weight_proposal_count",
        "trust_score_proposal_count",
        "shadow_replay_variant_count",
        "architect_recommendation_count",
        "architect_blocked_recommendation_count",
    ):
        if phase6_learning_loop.get(key, 0) < 1:
            print(f"cockpit_status_phase6_learning_loop_missing_count={key}")
            return 1
    if phase6_learning_loop.get("blocked_authority_count") != len(
        phase6_learning_loop.get("blocked_authorities", [])
    ):
        print("cockpit_status_phase6_learning_loop_blocked_authority_count_mismatch=true")
        return 1
    for key in (
        "phase6_learning_write_allowed",
        "phase6_knowledge_graph_write_allowed",
        "phase6_model_weight_update_allowed",
        "phase6_trust_score_update_allowed",
        "phase6_architect_policy_mutation_allowed",
        "phase7_proof_credit_allowed",
        "live_capital_enabled",
    ):
        if phase6_learning_loop.get(key) is not False:
            print(f"cockpit_status_phase6_learning_loop_authority_enabled={key}")
            return 1
    for key in (
        "unsafe_write_counter_total",
        "raw_payload_exposed_count",
        "private_payload_exposed_count",
        "local_path_exposed_count",
        "secret_ref_exposed_count",
        "broker_identifier_exposed_count",
    ):
        if phase6_learning_loop.get(key) != 0:
            print(f"cockpit_status_phase6_learning_loop_exposure_nonzero={key}")
            return 1
    missing_rs9_learning_loop_fields = sorted(
        set(RS9_LEARNING_LOOP_REQUIRED_FIELDS) - set(rs9_learning_loop)
    )
    if missing_rs9_learning_loop_fields:
        print(
            "cockpit_status_rs9_learning_loop_fields_missing="
            + ",".join(missing_rs9_learning_loop_fields)
        )
        return 1
    if rs9_learning_loop.get("phase") != "RS" or rs9_learning_loop.get("stage") != "RS-9":
        print("cockpit_status_rs9_learning_loop_phase_or_stage_mismatch=true")
        return 1
    if rs9_learning_loop.get("public_safe") is not True:
        print("cockpit_status_rs9_learning_loop_not_public_safe=true")
        return 1
    if rs9_learning_loop.get("recorded") is not True:
        print("cockpit_status_rs9_learning_loop_not_recorded=true")
        return 1
    if rs9_learning_loop.get("status") not in {"review_ready", "blocked"}:
        print("cockpit_status_rs9_learning_loop_status_invalid=true")
        return 1
    if rs9_learning_loop.get("validation_error_count") != 0:
        print("cockpit_status_rs9_learning_loop_validation_errors=true")
        return 1
    if rs9_learning_loop.get("event_log_written") is not True:
        print("cockpit_status_rs9_learning_loop_event_log_missing=true")
        return 1
    if rs9_learning_loop.get("event_log_event_count") != 1:
        print("cockpit_status_rs9_learning_loop_event_log_count_mismatch=true")
        return 1
    if rs9_learning_loop.get("learning_direction") not in {"improving", "degrading", "uncertain"}:
        print("cockpit_status_rs9_learning_loop_direction_invalid=true")
        return 1
    if rs9_learning_loop.get("full_potential_state") != "learning_visible_but_mutation_locked":
        print("cockpit_status_rs9_learning_loop_full_potential_state_mismatch=true")
        return 1
    if rs9_learning_loop.get("paperops_guarded_paper_trading_not_blocked") is not True:
        print("cockpit_status_rs9_learning_loop_blocks_guarded_paperops=true")
        return 1
    if rs9_learning_loop.get("source_missing_count") != 0:
        print("cockpit_status_rs9_learning_loop_source_missing=true")
        return 1
    if rs9_learning_loop.get("source_validation_error_count") != 0:
        print("cockpit_status_rs9_learning_loop_source_validation_errors=true")
        return 1
    if rs9_learning_loop.get("source_artifact_count") != len(
        rs9_learning_loop.get("source_status_records", [])
    ):
        print("cockpit_status_rs9_learning_loop_source_count_mismatch=true")
        return 1
    for record in rs9_learning_loop.get("source_status_records", []):
        source_ref = str(record.get("source_ref", ""))
        if not source_ref.startswith("data/runtime/"):
            print("cockpit_status_rs9_learning_loop_source_ref_invalid=true")
            return 1
        if (
            source_ref.startswith("/")
            or source_ref.startswith("~")
            or (len(source_ref) > 2 and source_ref[1:3] == ":\\")
        ):
            print("cockpit_status_rs9_learning_loop_source_ref_local=true")
            return 1
    if rs9_learning_loop.get("proposal_count") != len(
        rs9_learning_loop.get("learning_proposals", [])
    ):
        print("cockpit_status_rs9_learning_loop_proposal_count_mismatch=true")
        return 1
    if rs9_learning_loop.get("proposal_count") < 5:
        print("cockpit_status_rs9_learning_loop_proposal_count_low=true")
        return 1
    if rs9_learning_loop.get("active_proposal_count") != 0:
        print("cockpit_status_rs9_learning_loop_active_proposals=true")
        return 1
    if rs9_learning_loop.get("blocked_proposal_count") != rs9_learning_loop.get(
        "proposal_count"
    ):
        print("cockpit_status_rs9_learning_loop_blocked_proposal_count_mismatch=true")
        return 1
    rs9_surfaces = {
        str(proposal.get("proposal_surface"))
        for proposal in rs9_learning_loop.get("learning_proposals", [])
    }
    if rs9_surfaces != {
        "strategy_weights",
        "source_trust",
        "risk_sizing",
        "market_context_interpretation",
        "worldview_lens_strength",
    }:
        print("cockpit_status_rs9_learning_loop_proposal_surfaces_mismatch=true")
        return 1
    for proposal in rs9_learning_loop.get("learning_proposals", []):
        if proposal.get("approval_required") is not True:
            print("cockpit_status_rs9_learning_loop_proposal_approval_missing=true")
            return 1
        if proposal.get("apply_allowed") is not False:
            print("cockpit_status_rs9_learning_loop_proposal_apply_allowed=true")
            return 1
        if proposal.get("mutation_allowed") is not False:
            print("cockpit_status_rs9_learning_loop_proposal_mutation_allowed=true")
            return 1
        for ref in proposal.get("source_refs", []):
            if not isinstance(ref, str) or not ref.startswith("data/runtime/"):
                print("cockpit_status_rs9_learning_loop_proposal_source_ref_invalid=true")
                return 1
            if (
                ref.startswith("/")
                or ref.startswith("~")
                or (len(ref) > 2 and ref[1:3] == ":\\")
            ):
                print("cockpit_status_rs9_learning_loop_proposal_source_ref_local=true")
                return 1
    for key in (
        "strategy_weight_proposal_count",
        "source_trust_proposal_count",
        "risk_sizing_proposal_count",
        "market_context_proposal_count",
        "worldview_lens_proposal_count",
    ):
        if rs9_learning_loop.get(key) != 1:
            print(f"cockpit_status_rs9_learning_loop_surface_count_invalid={key}")
            return 1
    for key in (
        "strategy_weight_mutation_allowed",
        "source_trust_mutation_allowed",
        "risk_sizing_mutation_allowed",
        "market_context_interpretation_mutation_allowed",
        "worldview_lens_strength_mutation_allowed",
        "knowledge_graph_write_allowed",
        "model_weight_update_allowed",
        "trust_score_update_allowed",
        "policy_mutation_allowed",
        "strategy_mutation_allowed",
        "learning_write_allowed",
        "dashboard_command_authority",
        "telegram_command_authority",
        "broker_write_allowed",
        "broker_post_allowed",
        "alpaca_post_allowed",
        "live_capital_enabled",
        "phase7_proof_credit_allowed",
    ):
        if rs9_learning_loop.get(key) is not False:
            print(f"cockpit_status_rs9_learning_loop_authority_enabled={key}")
            return 1
    for key in (
        "broker_post_called_count",
        "alpaca_post_called_count",
        "broker_write_allowed_count",
        "live_endpoint_called_count",
        "live_capital_enabled_count",
        "phase7_proof_credit_allowed_count",
        "unsafe_write_counter_total",
        "raw_payload_exposed_count",
        "private_payload_exposed_count",
        "local_path_exposed_count",
        "secret_ref_exposed_count",
        "broker_identifier_exposed_count",
    ):
        if rs9_learning_loop.get(key) != 0:
            print(f"cockpit_status_rs9_learning_loop_exposure_nonzero={key}")
            return 1
    rs9_boundary = rs9_learning_loop.get("boundary", "")
    if (
        "cannot silently rewrite strategy" not in rs9_boundary
        or "cannot apply source trust" not in rs9_boundary
        or "cannot change risk sizing" not in rs9_boundary
        or "cannot mutate worldview lens strength" not in rs9_boundary
        or "cannot create orders" not in rs9_boundary
        or "cannot enable live capital" not in rs9_boundary
        or "cannot give dashboard or Telegram command authority" not in rs9_boundary
    ):
        print("cockpit_status_rs9_learning_loop_boundary_weak=true")
        return 1
    missing_rs10_final_paper_autonomy_fields = sorted(
        set(RS10_FINAL_PAPER_AUTONOMY_REQUIRED_FIELDS)
        - set(rs10_final_paper_autonomy)
    )
    if missing_rs10_final_paper_autonomy_fields:
        print(
            "cockpit_status_rs10_final_paper_autonomy_fields_missing="
            + ",".join(missing_rs10_final_paper_autonomy_fields)
        )
        return 1
    if (
        rs10_final_paper_autonomy.get("phase") != "RS"
        or rs10_final_paper_autonomy.get("stage") != "RS-10"
    ):
        print("cockpit_status_rs10_final_paper_autonomy_phase_or_stage_mismatch=true")
        return 1
    if rs10_final_paper_autonomy.get("public_safe") is not True:
        print("cockpit_status_rs10_final_paper_autonomy_not_public_safe=true")
        return 1
    if rs10_final_paper_autonomy.get("recorded") is not True:
        print("cockpit_status_rs10_final_paper_autonomy_not_recorded=true")
        return 1
    if rs10_final_paper_autonomy.get("event_log_written") is not True:
        print("cockpit_status_rs10_final_paper_autonomy_event_log_missing=true")
        return 1
    if rs10_final_paper_autonomy.get("event_log_event_count") != 1:
        print("cockpit_status_rs10_final_paper_autonomy_event_log_count_mismatch=true")
        return 1
    if validate_rs10_final_paper_autonomy_certification(rs10_final_paper_autonomy):
        print("cockpit_status_rs10_final_paper_autonomy_validation_errors=true")
        return 1
    if rs10_final_paper_autonomy.get("status") not in {
        "certified_actionable",
        "certified_waiting_for_qualified_setup",
        "certified_idle",
    }:
        print("cockpit_status_rs10_final_paper_autonomy_status_invalid=true")
        return 1
    if rs10_final_paper_autonomy.get("final_paper_autonomy_certified") is not True:
        print("cockpit_status_rs10_final_paper_autonomy_not_certified=true")
        return 1
    if rs10_final_paper_autonomy.get("guarded_paper_autonomy_allowed") is not True:
        print("cockpit_status_rs10_guarded_paper_autonomy_not_allowed=true")
        return 1
    if (
        rs10_final_paper_autonomy.get(
            "multiple_paper_trades_per_day_allowed_when_gates_pass"
        )
        is not True
    ):
        print("cockpit_status_rs10_multiple_paper_trades_policy_disabled=true")
        return 1
    if rs10_final_paper_autonomy.get("certification_blocker_count") != 0:
        print("cockpit_status_rs10_final_paper_autonomy_certification_blockers=true")
        return 1
    if rs10_final_paper_autonomy.get("safety_blocker_count") != 0:
        print("cockpit_status_rs10_final_paper_autonomy_safety_blockers=true")
        return 1
    if rs10_final_paper_autonomy.get("stale_blocker_in_current_count") != 0:
        print("cockpit_status_rs10_stale_blocker_in_current=true")
        return 1
    for key in RS10_FINAL_PAPER_AUTONOMY_AUTHORITY_FIELDS:
        if rs10_final_paper_autonomy.get(key) is not False:
            print(f"cockpit_status_rs10_authority_enabled={key}")
            return 1
    for key in RS10_FINAL_PAPER_AUTONOMY_UNSAFE_COUNT_FIELDS:
        if rs10_final_paper_autonomy.get(key) != 0:
            print(f"cockpit_status_rs10_unsafe_or_exposure_nonzero={key}")
            return 1
    if (
        rs10_final_paper_autonomy.get("paper_submit_currently_allowed") is True
        and paper_authority.get("paper_submit_currently_allowed") is not True
    ):
        print("cockpit_status_rs10_invented_paper_submit_authority=true")
        return 1
    if (
        rs10_final_paper_autonomy.get("autonomy_currently_actionable") is True
        and not any(
            rs10_final_paper_autonomy.get(key) is True
            for key in (
                "paper_submit_currently_allowed",
                "paper_poll_currently_allowed",
                "paper_exit_currently_allowed",
            )
        )
    ):
        print("cockpit_status_rs10_actionable_without_action=true")
        return 1
    missing_phase6_certification_fields = sorted(
        set(PHASE6_CERTIFICATION_REQUIRED_FIELDS) - set(phase6_certification)
    )
    if missing_phase6_certification_fields:
        print(
            "cockpit_status_phase6_certification_fields_missing="
            + ",".join(missing_phase6_certification_fields)
        )
        return 1
    if phase6_certification.get("phase") != "Q6" or phase6_certification.get("stage") != "Q6-17":
        print("cockpit_status_phase6_certification_phase_or_stage_mismatch=true")
        return 1
    if phase6_certification.get("public_safe") is not True:
        print("cockpit_status_phase6_certification_not_public_safe=true")
        return 1
    if phase6_certification.get("recorded") is not True:
        print("cockpit_status_phase6_certification_not_recorded=true")
        return 1
    if phase6_certification.get("status") != "certified":
        print("cockpit_status_phase6_certification_not_certified=true")
        return 1
    if phase6_certification.get("stage_status") != "phase6_certified":
        print("cockpit_status_phase6_certification_stage_status_mismatch=true")
        return 1
    if phase6_certification.get("phase6_certified") is not True:
        print("cockpit_status_phase6_certification_not_certified_true=true")
        return 1
    if phase6_certification.get("phase6_exit_gate") is not True:
        print("cockpit_status_phase6_certification_exit_gate_not_open=true")
        return 1
    if phase6_certification.get("phase7_demo_proof_planning_allowed") is not True:
        print("cockpit_status_phase6_certification_phase7_demo_not_allowed=true")
        return 1
    if phase6_certification.get("phase7_proof_credit_allowed") is not False:
        print("cockpit_status_phase6_certification_phase7_credit_allowed=true")
        return 1
    if phase6_certification.get("phase5_test_trades_count_for_phase7") is not False:
        print("cockpit_status_phase6_certification_phase5_trade_counted=true")
        return 1
    if phase6_certification.get("input_gate_count") != 17:
        print("cockpit_status_phase6_certification_input_gate_count_mismatch=true")
        return 1
    if phase6_certification.get("input_gate_passed_count") != 17:
        print("cockpit_status_phase6_certification_input_gate_passed_mismatch=true")
        return 1
    if phase6_certification.get("input_gate_blocked_count") != 0:
        print("cockpit_status_phase6_certification_input_gate_blocked=true")
        return 1
    if phase6_certification.get("certification_blocker_count") != 0:
        print("cockpit_status_phase6_certification_blockers_present=true")
        return 1
    if phase6_certification.get("unresolved_postmortem_count") != 0:
        print("cockpit_status_phase6_certification_unresolved_postmortem_nonzero=true")
        return 1
    if phase6_certification.get("pending_review_action_count") != 0:
        print("cockpit_status_phase6_certification_pending_actions_nonzero=true")
        return 1
    if phase6_certification.get("reviewed_postmortem_coverage_satisfied") is not True:
        print("cockpit_status_phase6_certification_postmortem_coverage_missing=true")
        return 1
    if phase6_certification.get("learning_actions_review_satisfied") is not True:
        print("cockpit_status_phase6_certification_learning_review_missing=true")
        return 1
    if phase6_certification.get("knowledge_graph_requirement_satisfied") is not True:
        print("cockpit_status_phase6_certification_kg_requirement_missing=true")
        return 1
    for key in (
        "knowledge_graph_read_result_count",
        "model_weight_proposal_count",
        "trust_score_proposal_count",
        "shadow_replay_variant_count",
        "architect_recommendation_count",
    ):
        if phase6_certification.get(key, 0) < 1:
            print(f"cockpit_status_phase6_certification_missing_count={key}")
            return 1
    if phase6_certification.get("cockpit_visibility_status") != "visible":
        print("cockpit_status_phase6_certification_cockpit_not_visible=true")
        return 1
    if phase6_certification.get("cockpit_backend_derived") is not True:
        print("cockpit_status_phase6_certification_cockpit_not_backend=true")
        return 1
    for key in (
        "unsafe_write_counter_total",
        "blocking_unsafe_count",
        "phase7_proof_credit_allowed_count",
        "live_capital_enabled_count",
        "broker_write_allowed_count",
    ):
        if phase6_certification.get(key) != 0:
            print(f"cockpit_status_phase6_certification_unsafe_nonzero={key}")
            return 1
    missing_phase5_system_map_fields = sorted(
        PHASE5_SYSTEM_MAP_REQUIRED_FIELDS - set(phase5_system_map)
    )
    if missing_phase5_system_map_fields:
        print(
            "cockpit_status_phase5_system_map_fields_missing="
            + ",".join(missing_phase5_system_map_fields)
        )
        return 1
    if phase5_system_map.get("phase") != "Q5" or phase5_system_map.get("stage") != "Q5-13":
        print("cockpit_status_phase5_system_map_phase_or_stage_mismatch=true")
        return 1
    if phase5_system_map.get("public_safe") is not True:
        print("cockpit_status_phase5_system_map_not_public_safe=true")
        return 1
    if phase5_system_map.get("recorded") is not True:
        print("cockpit_status_phase5_system_map_not_recorded=true")
        return 1
    if phase5_system_map.get("status") != "ok":
        print("cockpit_status_phase5_system_map_not_ok=true")
        return 1
    if phase5_system_map.get("validation_error_count") != 0:
        print("cockpit_status_phase5_system_map_validation_errors=true")
        return 1
    if phase5_system_map.get("event_log_written") is not True:
        print("cockpit_status_phase5_system_map_event_log_not_written=true")
        return 1
    if phase5_system_map.get("event_log_event_count") != 1:
        print("cockpit_status_phase5_system_map_event_log_count_mismatch=true")
        return 1
    if phase5_system_map.get("node_count") != len(phase5_system_map.get("nodes", [])):
        print("cockpit_status_phase5_system_map_node_count_mismatch=true")
        return 1
    if phase5_system_map.get("lane_count") != len(phase5_system_map.get("lanes", [])):
        print("cockpit_status_phase5_system_map_lane_count_mismatch=true")
        return 1
    if phase5_system_map.get("backend_parity_error_count") != 0:
        print("cockpit_status_phase5_system_map_backend_parity_errors=true")
        return 1
    if phase5_system_map.get("unsafe_control_count") != 0:
        print("cockpit_status_phase5_system_map_unsafe_controls=true")
        return 1
    if phase5_system_map.get("ui_inferred_node_count") != 0:
        print("cockpit_status_phase5_system_map_ui_inferred_nodes=true")
        return 1
    for node in phase5_system_map.get("nodes", []):
        if node.get("backend_status") != node.get("display_status"):
            print("cockpit_status_phase5_system_map_node_status_mismatch=true")
            return 1
        if node.get("ui_inferred") is not False:
            print("cockpit_status_phase5_system_map_node_inferred=true")
            return 1
        for key in (
            "trade_approval_control_enabled",
            "order_place_control_enabled",
            "broker_write_allowed",
            "prediction_market_write_allowed",
            "kill_switch_mutation_authority",
            "live_capital_enabled",
        ):
            if node.get(key) is not False:
                print(f"cockpit_status_phase5_system_map_node_authority_enabled={key}")
                return 1
    system_map_posture = phase5_system_map.get("source_posture", {})
    if system_map_posture.get("canonical", {}).get("expected_source_count") != EXPECTED_SOURCE_COUNT:
        print("cockpit_status_phase5_system_map_canonical_source_count_mismatch=true")
        return 1
    if (
        system_map_posture.get("yahoo_finance", {}).get("role")
        != "supplemental_market_confirmation_only"
    ):
        print("cockpit_status_phase5_system_map_yahoo_role_mismatch=true")
        return 1
    if system_map_posture.get("preference_mcp", {}).get("source_36") is not False:
        print("cockpit_status_phase5_system_map_preference_source_36=true")
        return 1
    if system_map_posture.get("preference_mcp", {}).get("source_quorum_credit_allowed") is not False:
        print("cockpit_status_phase5_system_map_preference_source_quorum=true")
        return 1
    system_map_guardrails = phase5_system_map.get("guardrails", {})
    if system_map_guardrails.get("live_capital_enabled") is not False:
        print("cockpit_status_phase5_system_map_live_capital_enabled=true")
        return 1
    if system_map_guardrails.get("phase5_orchestration_start_allowed") is not False:
        print("cockpit_status_phase5_system_map_orchestration_start_allowed=true")
        return 1
    if (
        system_map_guardrails.get("dashboard_claims_trading_now") is True
        and not system_map_guardrails.get("trading_state_present")
    ):
        print("cockpit_status_phase5_system_map_claims_trading_without_state=true")
        return 1
    system_map_boundary = phase5_system_map.get("boundary", "")
    if "cannot approve trades" not in system_map_boundary or "cannot enable live capital" not in system_map_boundary:
        print("cockpit_status_phase5_system_map_boundary_weak=true")
        return 1
    quantum_oracle = payload.get("quantum_oracle", {})
    missing_quantum_fields = sorted(QUANTUM_ORACLE_REQUIRED_FIELDS - set(quantum_oracle))
    if missing_quantum_fields:
        print("cockpit_status_quantum_oracle_fields_missing=" + ",".join(missing_quantum_fields))
        return 1
    if quantum_oracle.get("hardware_submitted_count") != 0:
        print("cockpit_status_quantum_oracle_hardware_submitted=true")
        return 1
    if quantum_oracle.get("hardware_submission_allowed_count") != 0:
        print("cockpit_status_quantum_oracle_hardware_allowed=true")
        return 1
    if quantum_oracle.get("hardware_scheduler_enabled_count") != 0:
        print("cockpit_status_quantum_oracle_hardware_scheduler_enabled=true")
        return 1
    if quantum_oracle.get("execution_allowed_count") != 0:
        print("cockpit_status_quantum_oracle_execution_allowed=true")
        return 1
    if quantum_oracle.get("paper_order_allowed_count") != 0:
        print("cockpit_status_quantum_oracle_paper_order_allowed=true")
        return 1
    if quantum_oracle.get("trade_candidate_created_count") != 0:
        print("cockpit_status_quantum_oracle_trade_candidate_created=true")
        return 1
    if "non-executable" not in quantum_oracle.get("boundary", ""):
        print("cockpit_status_quantum_oracle_boundary_weak=true")
        return 1
    if quantum_oracle.get("result_count", 0) and len(str(quantum_oracle.get("latest_input_fingerprint"))) != 64:
        print("cockpit_status_quantum_oracle_fingerprint_invalid=true")
        return 1
    if quantum_oracle.get("result_count", 0) and not quantum_oracle.get("latest_validation_checks"):
        print("cockpit_status_quantum_oracle_validation_checks_missing=true")
        return 1
    if quantum_oracle.get("result_count", 0):
        if quantum_oracle.get("latest_input_contract_status") != "accepted":
            print("cockpit_status_quantum_oracle_input_contract_not_accepted=true")
            return 1
        if quantum_oracle.get("latest_input_source_type") not in {
            "signal_integrity_review",
            "certified_shadow_review_packet",
        }:
            print("cockpit_status_quantum_oracle_input_source_invalid=true")
            return 1
        if quantum_oracle.get("latest_market_confirmation_status") != "market_confirmation_corroboration_available":
            print("cockpit_status_quantum_oracle_market_confirmation_invalid=true")
            return 1
        if quantum_oracle.get("latest_yahoo_finance_role") not in {"supplemental_market_confirmation", "not_used"}:
            print("cockpit_status_quantum_oracle_yahoo_role_invalid=true")
            return 1
        if quantum_oracle.get("latest_yahoo_only_market_confirmation") is not False:
            print("cockpit_status_quantum_oracle_yahoo_only_market_confirmation=true")
            return 1
        output_routing = quantum_oracle.get("latest_output_routing", {})
        if not isinstance(output_routing, dict):
            print("cockpit_status_quantum_oracle_output_routing_invalid=true")
            return 1
        missing_output_fields = sorted(QUANTUM_OUTPUT_ROUTING_REQUIRED_FIELDS - set(output_routing))
        if missing_output_fields:
            print("cockpit_status_quantum_oracle_output_routing_fields_missing=" + ",".join(missing_output_fields))
            return 1
        if quantum_oracle.get("latest_output_route_type") != "shadow_annotation":
            print("cockpit_status_quantum_oracle_output_route_type_invalid=true")
            return 1
        if quantum_oracle.get("latest_output_storage_type") != "oracle_review_result":
            print("cockpit_status_quantum_oracle_output_storage_type_invalid=true")
            return 1
        if quantum_oracle.get("latest_output_routing_status") != "shadow_annotation_ready":
            print("cockpit_status_quantum_oracle_output_routing_status_invalid=true")
            return 1
        if output_routing.get("route_type") != "shadow_annotation":
            print("cockpit_status_quantum_oracle_output_route_invalid=true")
            return 1
        if output_routing.get("storage_type") != "oracle_review_result":
            print("cockpit_status_quantum_oracle_output_storage_invalid=true")
            return 1
        if output_routing.get("recommendation_class") != quantum_oracle.get("latest_recommendation"):
            print("cockpit_status_quantum_oracle_output_recommendation_mismatch=true")
            return 1
        blocked_routes = output_routing.get("blocked_routes", {})
        if not isinstance(blocked_routes, dict) or any(value is not False for value in blocked_routes.values()):
            print("cockpit_status_quantum_oracle_output_route_unblocked=true")
            return 1
        for key in (
            "trade_candidate_created_count",
            "risk_approval_count",
            "execution_policy_approval_count",
            "staged_paper_order_created_count",
            "broker_reconciliation_write_count",
            "paper_submit_receipt_created_count",
        ):
            if output_routing.get(key) != 0:
                print(f"cockpit_status_quantum_oracle_output_count_nonzero={key}")
                return 1
        for key in (
            "execution_allowed",
            "paper_order_allowed",
            "trade_candidate_authority",
            "risk_approval_authority",
            "execution_policy_authority",
            "staged_paper_order_authority",
            "broker_reconciliation_authority",
            "paper_submit_receipt_authority",
            "broker_write_allowed",
        ):
            if output_routing.get(key) is not False:
                print(f"cockpit_status_quantum_oracle_output_flag_not_false={key}")
                return 1
    scheduler_dry_run = quantum_oracle.get("scheduler_dry_run", {})
    missing_scheduler_fields = sorted(QUANTUM_SCHEDULER_DRY_RUN_REQUIRED_FIELDS - set(scheduler_dry_run))
    if missing_scheduler_fields:
        print("cockpit_status_quantum_scheduler_fields_missing=" + ",".join(missing_scheduler_fields))
        return 1
    if scheduler_dry_run.get("public_safe") is not True:
        print("cockpit_status_quantum_scheduler_not_public_safe=true")
        return 1
    if scheduler_dry_run.get("dry_run_only") is not True:
        print("cockpit_status_quantum_scheduler_not_dry_run=true")
        return 1
    if scheduler_dry_run.get("cadence") != "weekly_shadow_oracle":
        print("cockpit_status_quantum_scheduler_cadence_mismatch=true")
        return 1
    if scheduler_dry_run.get("cadence_days") != 7:
        print("cockpit_status_quantum_scheduler_cadence_days_mismatch=true")
        return 1
    if scheduler_dry_run.get("status") not in {"due", "not_due"}:
        print("cockpit_status_quantum_scheduler_status_invalid=true")
        return 1
    if scheduler_dry_run.get("due") is not (scheduler_dry_run.get("status") == "due"):
        print("cockpit_status_quantum_scheduler_due_status_mismatch=true")
        return 1
    if scheduler_dry_run.get("intended_job_count") != len(EXPECTED_QUANTUM_JOB_TYPES):
        print("cockpit_status_quantum_scheduler_intended_job_count_mismatch=true")
        return 1
    intended_jobs = scheduler_dry_run.get("intended_jobs", [])
    if not isinstance(intended_jobs, list):
        print("cockpit_status_quantum_scheduler_intended_jobs_invalid=true")
        return 1
    intended_job_types = {str(job.get("job_type")) for job in intended_jobs if isinstance(job, dict)}
    if intended_job_types != EXPECTED_QUANTUM_JOB_TYPES:
        print("cockpit_status_quantum_scheduler_intended_job_types_mismatch=true")
        return 1
    would_queue_jobs = scheduler_dry_run.get("would_queue_jobs", [])
    if not isinstance(would_queue_jobs, list):
        print("cockpit_status_quantum_scheduler_would_queue_jobs_invalid=true")
        return 1
    if scheduler_dry_run.get("due") is True and scheduler_dry_run.get("would_queue_job_count") != len(
        EXPECTED_QUANTUM_JOB_TYPES
    ):
        print("cockpit_status_quantum_scheduler_due_queue_count_mismatch=true")
        return 1
    if scheduler_dry_run.get("due") is False and scheduler_dry_run.get("would_queue_job_count") != 0:
        print("cockpit_status_quantum_scheduler_not_due_queue_count_nonzero=true")
        return 1
    if scheduler_dry_run.get("jobs_queued_count") != 0 or scheduler_dry_run.get("jobs_submitted_count") != 0:
        print("cockpit_status_quantum_scheduler_queued_or_submitted=true")
        return 1
    if scheduler_dry_run.get("hardware_jobs_submitted_count") != 0:
        print("cockpit_status_quantum_scheduler_hardware_jobs_submitted=true")
        return 1
    if scheduler_dry_run.get("hardware_scheduler_enabled_count") != 0:
        print("cockpit_status_quantum_scheduler_hardware_scheduler_enabled_count=true")
        return 1
    if scheduler_dry_run.get("hardware_submission_allowed_count") != 0:
        print("cockpit_status_quantum_scheduler_hardware_submission_allowed_count=true")
        return 1
    for key in (
        "scheduler_enabled",
        "autonomous_scheduler_enabled",
        "background_automation_created",
        "recurring_job_created",
        "queue_write_allowed",
        "job_submission_allowed",
        "hardware_scheduler_enabled",
        "hardware_submission_allowed",
        "provider_call_allowed",
        "execution_allowed",
        "paper_order_allowed",
        "trade_candidate_authority",
        "bypass_signal_integrity_allowed",
        "bypass_strategy_lead_allowed",
        "bypass_risk_agent_allowed",
        "bypass_execution_policy_allowed",
        "bypass_broker_reconciliation_allowed",
        "bypass_paper_submit_receipt_allowed",
    ):
        if scheduler_dry_run.get(key) is not False:
            print(f"cockpit_status_quantum_scheduler_flag_not_false={key}")
            return 1
    for job in intended_jobs + would_queue_jobs:
        if not isinstance(job, dict):
            print("cockpit_status_quantum_scheduler_job_invalid=true")
            return 1
        missing_scheduler_job_fields = sorted(QUANTUM_SCHEDULER_JOB_REQUIRED_FIELDS - set(job))
        if missing_scheduler_job_fields:
            print(
                "cockpit_status_quantum_scheduler_job_fields_missing="
                f"{job.get('job_type', 'unknown')}:{','.join(missing_scheduler_job_fields)}"
            )
            return 1
        for key in (
            "queue_write_allowed",
            "job_submission_allowed",
            "hardware_submission_allowed",
            "provider_call_allowed",
            "execution_allowed",
            "paper_order_allowed",
            "trade_candidate_authority",
        ):
            if job.get(key) is not False:
                print(f"cockpit_status_quantum_scheduler_job_flag_not_false={job.get('job_type')}:{key}")
                return 1
    if "metadata only" not in scheduler_dry_run.get("boundary", ""):
        print("cockpit_status_quantum_scheduler_boundary_weak=true")
        return 1
    local_simulator = quantum_oracle.get("local_simulator", {})
    missing_local_simulator_fields = sorted(
        QUANTUM_LOCAL_SIMULATOR_REQUIRED_FIELDS - set(local_simulator)
    )
    if missing_local_simulator_fields:
        print("cockpit_status_quantum_local_simulator_fields_missing=" + ",".join(missing_local_simulator_fields))
        return 1
    if local_simulator.get("public_safe") is not True:
        print("cockpit_status_quantum_local_simulator_not_public_safe=true")
        return 1
    if local_simulator.get("local_only") is not True:
        print("cockpit_status_quantum_local_simulator_not_local_only=true")
        return 1
    if local_simulator.get("classical_fallback_available") is not True:
        print("cockpit_status_quantum_local_simulator_fallback_unavailable=true")
        return 1
    if local_simulator.get("selected_backend") not in ALLOWED_QUANTUM_LOCAL_SIMULATOR_BACKENDS:
        print("cockpit_status_quantum_local_simulator_backend_invalid=true")
        return 1
    if set(local_simulator.get("expected_job_types", [])) != EXPECTED_QUANTUM_JOB_TYPES:
        print("cockpit_status_quantum_local_simulator_job_types_mismatch=true")
        return 1
    if local_simulator.get("required_job_count") != len(EXPECTED_QUANTUM_JOB_TYPES):
        print("cockpit_status_quantum_local_simulator_job_count_mismatch=true")
        return 1
    dependencies_available = (
        local_simulator.get("qiskit_available") is True
        and local_simulator.get("qiskit_aer_available") is True
    )
    if local_simulator.get("qiskit_dependencies_available") is not dependencies_available:
        print("cockpit_status_quantum_local_simulator_dependency_mismatch=true")
        return 1
    expected_backend = "qiskit_aer_local" if dependencies_available else "classical_fallback"
    if local_simulator.get("selected_backend") != expected_backend:
        print("cockpit_status_quantum_local_simulator_selected_backend_mismatch=true")
        return 1
    if local_simulator.get("schema_consistent_across_backends") is not True:
        print("cockpit_status_quantum_local_simulator_schema_not_consistent=true")
        return 1
    if "local-only" not in local_simulator.get("boundary", ""):
        print("cockpit_status_quantum_local_simulator_boundary_weak=true")
        return 1
    for key in (
        "provider_call_allowed",
        "hardware_provider_selected",
        "hardware_submission_allowed",
        "hardware_scheduler_enabled",
        "execution_allowed",
        "paper_order_allowed",
        "trade_candidate_authority",
    ):
        if local_simulator.get(key) is not False:
            print(f"cockpit_status_quantum_local_simulator_flag_not_false={key}")
            return 1
    provider_readiness = quantum_oracle.get("provider_readiness", {})
    missing_provider_readiness_fields = sorted(
        QUANTUM_PROVIDER_READINESS_REQUIRED_FIELDS - set(provider_readiness)
    )
    if missing_provider_readiness_fields:
        print("cockpit_status_quantum_provider_readiness_fields_missing=" + ",".join(missing_provider_readiness_fields))
        return 1
    if provider_readiness.get("public_safe") is not True:
        print("cockpit_status_quantum_provider_readiness_not_public_safe=true")
        return 1
    if provider_readiness.get("provider_count") != len(EXPECTED_QUANTUM_PROVIDERS):
        print("cockpit_status_quantum_provider_count_mismatch=true")
        return 1
    if provider_readiness.get("expected_provider_count") != len(EXPECTED_QUANTUM_PROVIDERS):
        print("cockpit_status_quantum_expected_provider_count_mismatch=true")
        return 1
    hardware_stubs = provider_readiness.get("hardware_provider_stubs", {})
    if not isinstance(hardware_stubs, dict):
        print("cockpit_status_quantum_hardware_provider_stubs_invalid=true")
        return 1
    missing_hardware_stub_fields = sorted(
        QUANTUM_HARDWARE_PROVIDER_STUB_LEDGER_REQUIRED_FIELDS - set(hardware_stubs)
    )
    if missing_hardware_stub_fields:
        print("cockpit_status_quantum_hardware_provider_stubs_fields_missing=" + ",".join(missing_hardware_stub_fields))
        return 1
    if hardware_stubs.get("public_safe") is not True:
        print("cockpit_status_quantum_hardware_provider_stubs_not_public_safe=true")
        return 1
    if hardware_stubs.get("provider_count") != len(EXPECTED_QUANTUM_HARDWARE_PROVIDERS):
        print("cockpit_status_quantum_hardware_provider_count_mismatch=true")
        return 1
    if hardware_stubs.get("expected_provider_count") != len(EXPECTED_QUANTUM_HARDWARE_PROVIDERS):
        print("cockpit_status_quantum_hardware_provider_expected_count_mismatch=true")
        return 1
    if hardware_stubs.get("explicit_hardware_policy_approval_present") is not False:
        print("cockpit_status_quantum_hardware_policy_approval_present=true")
        return 1
    if hardware_stubs.get("local_simulator_validation_passed") is not True:
        print("cockpit_status_quantum_hardware_local_validation_missing=true")
        return 1
    for key in (
        "provider_call_allowed_count",
        "live_probe_allowed_count",
        "hardware_backend_implemented_count",
        "submitting_backend_implemented_count",
        "hardware_submission_allowed_count",
        "hardware_submitted_count",
        "hardware_scheduler_enabled_count",
        "execution_allowed_count",
        "paper_order_allowed_count",
        "trade_candidate_authority_count",
        "secret_value_exposed_count",
        "raw_response_exposed_count",
    ):
        if hardware_stubs.get(key) != 0:
            print(f"cockpit_status_quantum_hardware_provider_stubs_nonzero={key}")
            return 1
    hardware_provider_rows = hardware_stubs.get("providers", [])
    if not isinstance(hardware_provider_rows, list):
        print("cockpit_status_quantum_hardware_provider_list_invalid=true")
        return 1
    hardware_provider_keys = {
        str(provider.get("key")) for provider in hardware_provider_rows if isinstance(provider, dict)
    }
    if hardware_provider_keys != EXPECTED_QUANTUM_HARDWARE_PROVIDERS:
        print("cockpit_status_quantum_hardware_provider_keys_mismatch=true")
        return 1
    for hardware_provider in hardware_provider_rows:
        if not isinstance(hardware_provider, dict):
            print("cockpit_status_quantum_hardware_provider_row_invalid=true")
            return 1
        missing_hardware_provider_fields = sorted(
            QUANTUM_HARDWARE_PROVIDER_STUB_PROVIDER_REQUIRED_FIELDS - set(hardware_provider)
        )
        if missing_hardware_provider_fields:
            print(
                "cockpit_status_quantum_hardware_provider_fields_missing="
                f"{hardware_provider.get('key', 'unknown')}:{','.join(missing_hardware_provider_fields)}"
            )
            return 1
        if hardware_provider.get("status") not in ALLOWED_QUANTUM_HARDWARE_PROVIDER_STATUSES:
            print(f"cockpit_status_quantum_hardware_provider_status_invalid={hardware_provider.get('key')}")
            return 1
        if hardware_provider.get("policy_block_reason") != "explicit_hardware_policy_approval_missing":
            print(f"cockpit_status_quantum_hardware_provider_policy_block_invalid={hardware_provider.get('key')}")
            return 1
        if "credential_key" in hardware_provider:
            print("cockpit_status_quantum_hardware_provider_exposes_credential_key=true")
            return 1
        for key in (
            "provider_call_allowed",
            "live_probe_allowed",
            "hardware_backend_implemented",
            "submitting_backend_implemented",
            "hardware_submission_allowed",
            "hardware_submitted",
            "hardware_scheduler_enabled",
            "execution_allowed",
            "paper_order_allowed",
            "trade_candidate_authority",
            "secret_value_exposed",
            "raw_response_exposed",
        ):
            if hardware_provider.get(key) is not False:
                print(f"cockpit_status_quantum_hardware_provider_flag_not_false={hardware_provider.get('key')}:{key}")
                return 1
    qctrl_readiness = provider_readiness.get("qctrl_readiness", {})
    if not isinstance(qctrl_readiness, dict):
        print("cockpit_status_qctrl_readiness_invalid=true")
        return 1
    missing_qctrl_readiness_fields = sorted(
        QUANTUM_QCTRL_READINESS_REQUIRED_FIELDS - set(qctrl_readiness)
    )
    if missing_qctrl_readiness_fields:
        print("cockpit_status_qctrl_readiness_fields_missing=" + ",".join(missing_qctrl_readiness_fields))
        return 1
    if qctrl_readiness.get("public_safe") is not True:
        print("cockpit_status_qctrl_readiness_not_public_safe=true")
        return 1
    if qctrl_readiness.get("credential_configured") is not True:
        print("cockpit_status_qctrl_credential_missing=true")
        return 1
    if qctrl_readiness.get("hardware_backend_role") != "not_hardware_backend":
        print("cockpit_status_qctrl_hardware_backend_role_invalid=true")
        return 1
    if qctrl_readiness.get("default_mode") != "metadata_only_no_provider_call":
        print("cockpit_status_qctrl_default_mode_invalid=true")
        return 1
    if qctrl_readiness.get("live_probe_required_flag") != "--live-qctrl-readiness":
        print("cockpit_status_qctrl_live_probe_flag_missing=true")
        return 1
    if qctrl_readiness.get("provider_call_count") != 0:
        print("cockpit_status_qctrl_provider_call_count_nonzero=true")
        return 1
    if "metadata-only" not in qctrl_readiness.get("boundary", ""):
        print("cockpit_status_qctrl_readiness_boundary_weak=true")
        return 1
    for key in (
        "live_probe_enabled",
        "live_probe_attempted",
        "provider_call_allowed",
        "optimization_job_submission_allowed",
        "optimization_job_submitted",
        "hardware_submission_allowed",
        "hardware_job_submitted",
        "hardware_scheduler_enabled",
        "recommendation_authority",
        "execution_allowed",
        "paper_order_allowed",
        "trade_candidate_authority",
        "secret_value_exposed",
        "raw_response_exposed",
    ):
        if qctrl_readiness.get(key) is not False:
            print(f"cockpit_status_qctrl_readiness_flag_not_false={key}")
            return 1
    for key in (
        "provider_call_allowed_count",
        "hardware_submission_allowed_count",
        "hardware_scheduler_enabled_count",
        "execution_allowed_count",
        "paper_order_allowed_count",
        "trade_candidate_authority_count",
        "secret_value_exposed_count",
        "raw_response_exposed_count",
    ):
        if provider_readiness.get(key) != 0:
            print(f"cockpit_status_quantum_provider_readiness_nonzero={key}")
            return 1
    providers = provider_readiness.get("providers", [])
    if not isinstance(providers, list):
        print("cockpit_status_quantum_provider_list_invalid=true")
        return 1
    provider_keys = {str(provider.get("key")) for provider in providers if isinstance(provider, dict)}
    if provider_keys != EXPECTED_QUANTUM_PROVIDERS:
        print("cockpit_status_quantum_provider_keys_mismatch=true")
        return 1
    for provider in providers:
        if not isinstance(provider, dict):
            print("cockpit_status_quantum_provider_row_invalid=true")
            return 1
        missing_provider_fields = sorted(QUANTUM_PROVIDER_REQUIRED_FIELDS - set(provider))
        if missing_provider_fields:
            print(
                "cockpit_status_quantum_provider_fields_missing="
                f"{provider.get('key', 'unknown')}:{','.join(missing_provider_fields)}"
            )
            return 1
        if "credential_key" in provider:
            print("cockpit_status_quantum_provider_exposes_credential_key=true")
            return 1
        if provider.get("status") not in ALLOWED_QUANTUM_PROVIDER_STATUSES:
            print(f"cockpit_status_quantum_provider_status_invalid={provider.get('key')}")
            return 1
        if provider.get("public_safe") is not True:
            print(f"cockpit_status_quantum_provider_not_public_safe={provider.get('key')}")
            return 1
        for key in (
            "provider_call_allowed",
            "hardware_submission_allowed",
            "hardware_scheduler_enabled",
            "execution_allowed",
            "paper_order_allowed",
            "trade_candidate_authority",
            "secret_value_exposed",
            "raw_response_exposed",
        ):
            if provider.get(key) is not False:
                print(f"cockpit_status_quantum_provider_flag_not_false={provider.get('key')}:{key}")
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
    telegram_intake = communications["telegram_intake"]
    missing_telegram_intake_fields = sorted(TELEGRAM_INTAKE_REQUIRED_FIELDS - set(telegram_intake))
    if missing_telegram_intake_fields:
        print("cockpit_status_telegram_intake_fields_missing=" + ",".join(missing_telegram_intake_fields))
        return 1
    if telegram_intake.get("status") not in {"ready", "ready_no_messages"}:
        print("cockpit_status_telegram_intake_not_ready=true")
        return 1
    if telegram_intake.get("world_event_datapoint_count", 0) < 1:
        print("cockpit_status_telegram_world_event_datapoint_missing=true")
        return 1
    if telegram_intake.get("strategy_consideration_count", 0) < 1:
        print("cockpit_status_telegram_strategy_consideration_missing=true")
        return 1
    if telegram_intake.get("research_triage_packet_count", 0) < 1:
        print("cockpit_status_telegram_research_triage_missing=true")
        return 1
    if "read-only member research intake" not in telegram_intake.get("boundary", ""):
        print("cockpit_status_telegram_intake_boundary_weak=true")
        return 1
    for field in (
        "trade_candidate_creation_allowed",
        "risk_handoff_allowed",
        "execution_allowed",
        "paper_order_allowed",
        "broker_write_allowed",
        "telegram_command_authority",
        "live_capital_enabled",
    ):
        if telegram_intake.get(field) is not False:
            print(f"cockpit_status_telegram_intake_authority_enabled={field}")
            return 1
    telegram_intake_encoded = json.dumps(telegram_intake, sort_keys=True)
    if (
        "chat_id" in telegram_intake_encoded
        or "username" in telegram_intake_encoded
        or "first_name" in telegram_intake_encoded
        or "last_name" in telegram_intake_encoded
        or "/Users/" in telegram_intake_encoded
        or "@" in telegram_intake_encoded
    ):
        print("cockpit_status_telegram_intake_identifier_leaked=true")
        return 1
    telegram_daily_digest = communications["telegram_daily_portfolio_digest"]
    missing_telegram_daily_digest_fields = sorted(
        TELEGRAM_DAILY_PORTFOLIO_DIGEST_REQUIRED_FIELDS - set(telegram_daily_digest)
    )
    if missing_telegram_daily_digest_fields:
        print(
            "cockpit_status_telegram_daily_digest_fields_missing="
            + ",".join(missing_telegram_daily_digest_fields)
        )
        return 1
    if telegram_daily_digest.get("status") not in {
        "already_sent",
        "blocked_pending_enablement",
        "degraded",
        "dry_run_ready",
        "failed",
        "not_due",
        "not_run",
        "ready_to_send",
        "sent",
    }:
        print("cockpit_status_telegram_daily_digest_status_invalid=true")
        return 1
    if telegram_daily_digest.get("target") != "group":
        print("cockpit_status_telegram_daily_digest_target_not_group=true")
        return 1
    if "Daily Telegram portfolio digests" not in telegram_daily_digest.get("boundary", ""):
        print("cockpit_status_telegram_daily_digest_boundary_weak=true")
        return 1
    for field in (
        "telegram_command_path_enabled",
        "broker_write_allowed",
        "paper_order_allowed",
        "live_capital_enabled",
    ):
        if telegram_daily_digest.get(field) is not False:
            print(f"cockpit_status_telegram_daily_digest_authority_enabled={field}")
            return 1
    telegram_daily_digest_encoded = json.dumps(telegram_daily_digest, sort_keys=True)
    if (
        "chat_id" in telegram_daily_digest_encoded
        or "bot_token" in telegram_daily_digest_encoded
        or "/Users/" in telegram_daily_digest_encoded
        or "@" in telegram_daily_digest_encoded
        or re.search(r"\d{6,}:[A-Za-z0-9_-]{20,}", telegram_daily_digest_encoded)
    ):
        print("cockpit_status_telegram_daily_digest_secret_or_identifier_leaked=true")
        return 1
    telegram_codebase_upgrade = communications["telegram_codebase_upgrade"]
    missing_telegram_codebase_upgrade_fields = sorted(
        TELEGRAM_CODEBASE_UPGRADE_REQUIRED_FIELDS - set(telegram_codebase_upgrade)
    )
    if missing_telegram_codebase_upgrade_fields:
        print(
            "cockpit_status_telegram_codebase_upgrade_fields_missing="
            + ",".join(missing_telegram_codebase_upgrade_fields)
        )
        return 1
    if telegram_codebase_upgrade.get("status") not in {
        "already_sent",
        "blocked_pending_enablement",
        "degraded",
        "dry_run_ready",
        "failed",
        "not_run",
        "ready_to_send",
        "sent",
        "suppressed_not_safe",
    }:
        print("cockpit_status_telegram_codebase_upgrade_status_invalid=true")
        return 1
    if telegram_codebase_upgrade.get("target") != "group":
        print("cockpit_status_telegram_codebase_upgrade_target_not_group=true")
        return 1
    if "codebase upgrade notifications" not in telegram_codebase_upgrade.get("boundary", ""):
        print("cockpit_status_telegram_codebase_upgrade_boundary_weak=true")
        return 1
    for phrase in ("cannot", "create commits", "push code", "deploy assets", "enable live capital"):
        if phrase not in telegram_codebase_upgrade.get("boundary", ""):
            print(f"cockpit_status_telegram_codebase_upgrade_boundary_missing={phrase}")
            return 1
    for field in (
        "telegram_command_path_enabled",
        "broker_write_allowed",
        "paper_order_allowed",
        "repository_write_allowed",
        "deploy_allowed",
        "live_capital_enabled",
    ):
        if telegram_codebase_upgrade.get(field) is not False:
            print(f"cockpit_status_telegram_codebase_upgrade_authority_enabled={field}")
            return 1
    telegram_codebase_upgrade_encoded = json.dumps(telegram_codebase_upgrade, sort_keys=True)
    if (
        "chat_id" in telegram_codebase_upgrade_encoded
        or "bot_token" in telegram_codebase_upgrade_encoded
        or "/Users/" in telegram_codebase_upgrade_encoded
        or "@" in telegram_codebase_upgrade_encoded
        or re.search(r"\d{6,}:[A-Za-z0-9_-]{20,}", telegram_codebase_upgrade_encoded)
    ):
        print("cockpit_status_telegram_codebase_upgrade_secret_or_identifier_leaked=true")
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
    if capital.get("account_scope") != PAPER_ACCOUNT_SCOPE:
        print("cockpit_status_paper_account_scope_mismatch=true")
        return 1
    if not capital.get("account_currency") or not capital.get("display_currency"):
        print("cockpit_status_paper_currency_missing=true")
        return 1
    if capital.get("mirror_freshness_status") not in {"fresh", "stale", "unknown", "not_connected"}:
        print("cockpit_status_paper_freshness_status_invalid=true")
        return 1
    if int(capital.get("stale_after_seconds") or 0) <= 0:
        print("cockpit_status_paper_stale_after_missing=true")
        return 1
    reconciliation = capital.get("portfolio_reconciliation", {})
    if not isinstance(reconciliation, dict) or not reconciliation.get("status"):
        print("cockpit_status_paper_reconciliation_missing=true")
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
    if capital.get("starting_balance_gbp") != PAPER_ACCOUNT_BALANCE_GBP:
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
        if trade.get("postmortem_status") not in {
            "postmortem_pending_marker",
            "postmortem_due",
            "postmortem_complete",
        }:
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
    missing_rs6_fields = sorted(RS6_PUBLIC_STATUS_FIELDS - set(paper_lifecycle_postmortem))
    if missing_rs6_fields:
        print("cockpit_status_rs6_fields_missing=" + ",".join(missing_rs6_fields))
        return 1
    if paper_lifecycle_postmortem.get("status") != "ok":
        print("cockpit_status_rs6_not_ok=true")
        return 1
    if paper_lifecycle_postmortem.get("public_safe") is not True:
        print("cockpit_status_rs6_not_public_safe=true")
        return 1
    if int(paper_lifecycle_postmortem.get("validation_error_count") or 0) != 0:
        print("cockpit_status_rs6_validation_errors=true")
        return 1
    for field in (
        "live_capital_enabled",
        "write_authority",
        "broker_write_allowed",
        "paper_order_allowed",
    ):
        if paper_lifecycle_postmortem.get(field) is not False:
            print(f"cockpit_status_rs6_authority_enabled={field}")
            return 1
    if paper_lifecycle_postmortem.get("closed_trade_count") != capital.get("closed_trade_count"):
        print("cockpit_status_rs6_closed_trade_count_mismatch=true")
        return 1
    if paper_lifecycle_postmortem.get("order_count") != capital.get("order_count"):
        print("cockpit_status_rs6_order_count_mismatch=true")
        return 1
    if paper_lifecycle_postmortem.get("open_position_count") != capital.get("open_position_count"):
        print("cockpit_status_rs6_position_count_mismatch=true")
        return 1
    if paper_lifecycle_postmortem.get("current_balance_gbp") != capital.get("current_balance_gbp"):
        print("cockpit_status_rs6_balance_mismatch=true")
        return 1
    if capital.get("connection_status") == "alpaca_paper_readonly_connected":
        if paper_lifecycle_postmortem.get("portfolio_value_source") != "alpaca_paper_account_mirror":
            print("cockpit_status_rs6_portfolio_value_source_not_alpaca_mirror=true")
            return 1
        if paper_lifecycle_postmortem.get("balance_ticker_broker_account_derived") is not True:
            print("cockpit_status_rs6_balance_ticker_not_broker_account_derived=true")
            return 1
    coverage_count = int(
        paper_lifecycle_postmortem.get("closed_trade_postmortem_coverage_count") or 0
    )
    missing_count = int(
        paper_lifecycle_postmortem.get("closed_trade_missing_postmortem_count") or 0
    )
    if coverage_count + missing_count != int(capital.get("closed_trade_count") or 0):
        print("cockpit_status_rs6_postmortem_coverage_count_mismatch=true")
        return 1
    if missing_count != 0:
        print("cockpit_status_rs6_missing_postmortem=true")
        return 1
    if paper_lifecycle_postmortem.get("paper_proof_ledger_uses_verified_lifecycle_only") is not True:
        print("cockpit_status_rs6_proof_ledger_policy_invalid=true")
        return 1
    if int(paper_lifecycle_postmortem.get("mirror_trade_counted_for_proof_count") or 0) != 0:
        print("cockpit_status_rs6_mirror_trade_counted_for_proof=true")
        return 1
    if "read-only" not in paper_lifecycle_postmortem.get("boundary", ""):
        print("cockpit_status_rs6_boundary_weak=true")
        return 1
    missing_rs7_fields = sorted(RS7_OPERATOR_INBOX_PUBLIC_FIELDS - set(operator_inbox))
    if missing_rs7_fields:
        print("cockpit_status_rs7_fields_missing=" + ",".join(missing_rs7_fields))
        return 1
    if operator_inbox.get("status") != "ok":
        print("cockpit_status_rs7_not_ok=true")
        return 1
    if operator_inbox.get("public_safe") is not True:
        print("cockpit_status_rs7_not_public_safe=true")
        return 1
    if int(operator_inbox.get("validation_error_count") or 0) != 0:
        print("cockpit_status_rs7_validation_errors=true")
        return 1
    if int(operator_inbox.get("item_count") or 0) < 5:
        print("cockpit_status_rs7_item_count_too_low=true")
        return 1
    for command in (
        "/status",
        "/sources",
        "/research-goals",
        "/trades",
        "/blocked",
        "/portfolio",
        "/worldview",
        "/postmortems",
    ):
        if command not in operator_inbox.get("allowed_read_commands", []):
            print(f"cockpit_status_rs7_read_command_missing={command}")
            return 1
    for field in (
        "telegram_command_authority",
        "comment_can_approve_trades",
        "ack_can_approve_trades",
        "signal_authority",
        "trade_candidate_creation_allowed",
        "risk_handoff_allowed",
        "risk_approval_allowed",
        "execution_allowed",
        "execution_approval_allowed",
        "paper_order_allowed",
        "broker_write_allowed",
        "qctrl_provider_call_allowed",
        "live_capital_enabled",
    ):
        if operator_inbox.get(field) is not False:
            print(f"cockpit_status_rs7_authority_enabled={field}")
            return 1
    if "cannot create signals" not in operator_inbox.get("boundary", ""):
        print("cockpit_status_rs7_boundary_weak=true")
        return 1
    mission = payload.get("mission_control", {})
    missing_mission_fields = sorted(MISSION_CONTROL_REQUIRED_FIELDS - set(mission))
    if missing_mission_fields:
        print("cockpit_status_mission_control_fields_missing=" + ",".join(missing_mission_fields))
        return 1
    if mission.get("status") != "read_only_mission_control":
        print("cockpit_status_mission_control_status_mismatch=true")
        return 1
    if int(mission.get("schema_version", 0) or 0) < 2:
        print("cockpit_status_mission_control_schema_too_old=true")
        return 1
    mission_team = mission.get("team", [])
    if not isinstance(mission_team, list) or len(mission_team) < 6:
        print("cockpit_status_mission_team_invalid=true")
        return 1
    mission_team_keys = {str(node.get("key")) for node in mission_team if isinstance(node, dict)}
    for expected_key in {
        "intelligence_pipelines",
        "coo",
        "research_analyst",
        "strategy_lead",
        "head_of_quant",
        "safety_policy",
        "paper_demo_state",
    }:
        if expected_key not in mission_team_keys:
            print(f"cockpit_status_mission_team_node_missing={expected_key}")
            return 1
    for node in mission_team:
        missing_node_fields = sorted(MISSION_CONTROL_TEAM_REQUIRED_FIELDS - set(node))
        if missing_node_fields:
            print(
                "cockpit_status_mission_team_fields_missing="
                + f"{node.get('key', 'unknown')}:{','.join(missing_node_fields)}"
            )
            return 1
    mission_sources = mission.get("data_sources", {})
    missing_source_fields = sorted(MISSION_CONTROL_SOURCE_REQUIRED_FIELDS - set(mission_sources))
    if missing_source_fields:
        print("cockpit_status_mission_sources_fields_missing=" + ",".join(missing_source_fields))
        return 1
    if mission_sources.get("ok") != mission_sources.get("online_count"):
        print("cockpit_status_mission_sources_ok_mismatch=true")
        return 1
    if mission_sources.get("missing_credentials") != mission_sources.get("missing_credential_count"):
        print("cockpit_status_mission_sources_missing_credential_mismatch=true")
        return 1
    source_ledger = mission_sources.get("ledger", [])
    if not isinstance(source_ledger, list) or len(source_ledger) != len(payload.get("watching", [])):
        print("cockpit_status_mission_source_ledger_invalid=true")
        return 1
    for row in source_ledger[:5]:
        missing_row_fields = sorted(MISSION_CONTROL_SOURCE_LEDGER_REQUIRED_FIELDS - set(row))
        if missing_row_fields:
            print(
                "cockpit_status_mission_source_ledger_fields_missing="
                + f"{row.get('source_key', 'unknown')}:{','.join(missing_row_fields)}"
            )
            return 1
    mission_strategy = mission.get("strategy", {})
    missing_strategy_fields = sorted(MISSION_CONTROL_STRATEGY_REQUIRED_FIELDS - set(mission_strategy))
    if missing_strategy_fields:
        print("cockpit_status_mission_strategy_fields_missing=" + ",".join(missing_strategy_fields))
        return 1
    if "Akber" not in mission_strategy.get("akber_lens", {}).get("summary", ""):
        print("cockpit_status_mission_strategy_akber_lens_missing=true")
        return 1
    if not isinstance(mission_strategy.get("universe"), list):
        print("cockpit_status_mission_strategy_universe_invalid=true")
        return 1
    mission_portfolio = mission.get("portfolio", {})
    missing_portfolio_fields = sorted(MISSION_CONTROL_PORTFOLIO_REQUIRED_FIELDS - set(mission_portfolio))
    if missing_portfolio_fields:
        print("cockpit_status_mission_portfolio_fields_missing=" + ",".join(missing_portfolio_fields))
        return 1
    if mission_portfolio.get("balance_gbp") != mission_portfolio.get("current_balance_gbp"):
        print("cockpit_status_mission_portfolio_balance_mismatch=true")
        return 1
    if not isinstance(mission_portfolio.get("equity_curve"), list):
        print("cockpit_status_mission_portfolio_equity_curve_invalid=true")
        return 1
    mission_trades = mission.get("trades", {})
    missing_trades_fields = sorted(MISSION_CONTROL_TRADES_REQUIRED_FIELDS - set(mission_trades))
    if missing_trades_fields:
        print("cockpit_status_mission_trades_fields_missing=" + ",".join(missing_trades_fields))
        return 1
    lifecycle_counts = mission_trades.get("lifecycle_counts", {})
    for count_key in ("observed", "candidate", "blocked", "open", "closed", "postmortem_due"):
        if count_key not in lifecycle_counts:
            print(f"cockpit_status_mission_trades_lifecycle_missing={count_key}")
            return 1
    if not isinstance(mission_trades.get("board"), list):
        print("cockpit_status_mission_trades_board_invalid=true")
        return 1
    mission_thinking = mission.get("thinking", {})
    missing_thinking_fields = sorted(MISSION_CONTROL_THINKING_REQUIRED_FIELDS - set(mission_thinking))
    if missing_thinking_fields:
        print("cockpit_status_mission_thinking_fields_missing=" + ",".join(missing_thinking_fields))
        return 1
    if mission_thinking.get("worldview_prior", {}).get("role") != "private_worldview_prior":
        print("cockpit_status_mission_worldview_prior_role_mismatch=true")
        return 1
    mission_safety = mission.get("safety", {})
    missing_safety_fields = sorted(MISSION_CONTROL_SAFETY_REQUIRED_FIELDS - set(mission_safety))
    if missing_safety_fields:
        print("cockpit_status_mission_safety_fields_missing=" + ",".join(missing_safety_fields))
        return 1
    if mission_safety.get("read_only") is not True:
        print("cockpit_status_mission_safety_not_read_only=true")
        return 1
    if mission_safety.get("live_capital_enabled") is not False:
        print("cockpit_status_mission_safety_live_capital_enabled=true")
        return 1
    if mission_safety.get("broker_write_allowed") is not False:
        print("cockpit_status_mission_safety_broker_write_allowed=true")
        return 1
    diagnostics = payload.get("diagnostics", {})
    missing_diagnostics_fields = sorted(DIAGNOSTICS_REQUIRED_FIELDS - set(diagnostics))
    if missing_diagnostics_fields:
        print("cockpit_status_diagnostics_fields_missing=" + ",".join(missing_diagnostics_fields))
        return 1
    if diagnostics.get("status") != "diagnostics_available":
        print("cockpit_status_diagnostics_status_mismatch=true")
        return 1
    if not isinstance(diagnostics.get("audit_sections"), dict) or not diagnostics.get("audit_sections"):
        print("cockpit_status_diagnostics_audit_sections_invalid=true")
        return 1
    for expected_diagnostic in (
        "phase5_kill_switch_ledger",
        "paper_authority_reconciliation",
        "rs10_final_paper_autonomy_certification",
        "paperops_active_paper_trading_automation",
    ):
        if expected_diagnostic not in diagnostics.get("audit_sections", {}):
            print(f"cockpit_status_diagnostics_section_missing={expected_diagnostic}")
            return 1
    prune_candidates = diagnostics.get("prune_candidates", [])
    prune_audit = diagnostics.get("prune_audit", {})
    if not isinstance(prune_candidates, list) or not prune_candidates:
        print("cockpit_status_diagnostics_prune_candidates_invalid=true")
        return 1
    if not isinstance(prune_audit, dict) or not prune_audit:
        print("cockpit_status_diagnostics_prune_audit_invalid=true")
        return 1
    if prune_audit.get("status") != "retained_due_to_active_dependencies":
        print("cockpit_status_diagnostics_prune_audit_status_mismatch=true")
        return 1
    retained_entries = prune_audit.get("retained_top_level_keys", [])
    if not isinstance(retained_entries, list) or not retained_entries:
        print("cockpit_status_diagnostics_prune_audit_retained_invalid=true")
        return 1
    retained_keys = [entry.get("key") for entry in retained_entries if isinstance(entry, dict)]
    if retained_keys != prune_candidates:
        print("cockpit_status_diagnostics_prune_audit_retained_mismatch=true")
        return 1
    if prune_audit.get("candidate_count") != len(prune_candidates):
        print("cockpit_status_diagnostics_prune_audit_candidate_count_mismatch=true")
        return 1
    if prune_audit.get("retained_count") != len(retained_entries):
        print("cockpit_status_diagnostics_prune_audit_retained_count_mismatch=true")
        return 1
    if prune_audit.get("safe_to_remove_count") != 0 or prune_audit.get("safe_to_remove_keys") != []:
        print("cockpit_status_diagnostics_prune_audit_safe_remove_without_proof=true")
        return 1
    for entry in retained_entries:
        if not isinstance(entry, dict):
            print("cockpit_status_diagnostics_prune_audit_entry_invalid=true")
            return 1
        for required_field in (
            "key",
            "migration_status",
            "retention_reason",
            "dependent_surfaces",
            "namespace_shadow",
        ):
            if required_field not in entry:
                print(f"cockpit_status_diagnostics_prune_audit_entry_field_missing={required_field}")
                return 1
        if not entry.get("dependent_surfaces"):
            print(f"cockpit_status_diagnostics_prune_audit_dependency_missing={entry.get('key')}")
            return 1
    mission_brief = mission.get("mission_brief", {})
    missing_mission_brief_fields = sorted(MISSION_BRIEF_REQUIRED_FIELDS - set(mission_brief))
    if missing_mission_brief_fields:
        print("cockpit_status_mission_brief_fields_missing=" + ",".join(missing_mission_brief_fields))
        return 1
    if mission_brief.get("status") != "ok":
        print("cockpit_status_mission_brief_status_mismatch=true")
        return 1
    mission_brief_questions = mission_brief.get("questions", [])
    if mission_brief.get("question_count") != 7 or len(mission_brief_questions) != 7:
        print("cockpit_status_mission_brief_question_count_mismatch=true")
        return 1
    mission_brief_question_keys = {question.get("key") for question in mission_brief_questions}
    if mission_brief_question_keys != MISSION_BRIEF_EXPECTED_QUESTION_KEYS:
        print("cockpit_status_mission_brief_question_keys_mismatch=true")
        return 1
    for question in mission_brief_questions:
        missing_question_fields = sorted(
            MISSION_BRIEF_QUESTION_REQUIRED_FIELDS - set(question)
        )
        if missing_question_fields:
            print(
                "cockpit_status_mission_brief_question_fields_missing="
                + f"{question.get('key')}:{','.join(missing_question_fields)}"
            )
            return 1
        if not isinstance(question.get("metrics"), list) or len(question.get("metrics", [])) < 2:
            print("cockpit_status_mission_brief_question_metrics_invalid=true")
            return 1
        if not str(question.get("href", "")).startswith("#"):
            print("cockpit_status_mission_brief_question_href_invalid=true")
            return 1
    if not any(question.get("question") == "What is Qadam watching?" for question in mission_brief_questions):
        print("cockpit_status_mission_brief_watching_question_missing=true")
        return 1
    if not any(question.get("question") == "What is Qadam thinking about next?" for question in mission_brief_questions):
        print("cockpit_status_mission_brief_thinking_question_missing=true")
        return 1
    if not any(question.get("question") == "What is Qadam forbidden from doing?" for question in mission_brief_questions):
        print("cockpit_status_mission_brief_forbidden_question_missing=true")
        return 1
    if not any(question.get("question") == "Which trades are candidates or blocked?" for question in mission_brief_questions):
        print("cockpit_status_mission_brief_trade_question_missing=true")
        return 1
    if not any(question.get("question") == "What is the portfolio worth?" for question in mission_brief_questions):
        print("cockpit_status_mission_brief_portfolio_question_missing=true")
        return 1
    mission_brief_nav = mission_brief.get("navigation", [])
    if len(mission_brief_nav) < 9:
        print("cockpit_status_mission_brief_navigation_short=true")
        return 1
    mission_brief_nav_labels = {item.get("label") for item in mission_brief_nav}
    for label in {"Mission", "Map", "Sources", "Reasoning", "Trades", "Portfolio", "Safety", "Inbox", "Runtime"}:
        if label not in mission_brief_nav_labels:
            print(f"cockpit_status_mission_brief_navigation_missing={label}")
            return 1
    mission_brief_authority = mission_brief.get("authority", {})
    missing_mission_brief_authority_fields = sorted(
        MISSION_BRIEF_AUTHORITY_REQUIRED_FIELDS - set(mission_brief_authority)
    )
    if missing_mission_brief_authority_fields:
        print("cockpit_status_mission_brief_authority_fields_missing=" + ",".join(missing_mission_brief_authority_fields))
        return 1
    for field in MISSION_BRIEF_AUTHORITY_REQUIRED_FIELDS:
        if mission_brief_authority.get(field) is not False:
            print(f"cockpit_status_mission_brief_authority_enabled={field}")
            return 1
    if "read-only" not in mission_brief.get("boundary", ""):
        print("cockpit_status_mission_brief_boundary_weak=true")
        return 1
    if "cannot approve" not in mission_brief.get("boundary", ""):
        print("cockpit_status_mission_brief_boundary_missing_authority=true")
        return 1
    if not mission_brief.get("next_action", {}).get("label"):
        print("cockpit_status_mission_brief_next_action_missing=true")
        return 1
    mission_data = mission.get("data_sources", {})
    missing_mission_data_fields = sorted(MISSION_DATA_SOURCES_REQUIRED_FIELDS - set(mission_data))
    if missing_mission_data_fields:
        print("cockpit_status_mission_data_fields_missing=" + ",".join(missing_mission_data_fields))
        return 1
    if mission_data.get("total_count") != len(payload["watching"]):
        print("cockpit_status_mission_source_total_mismatch=true")
        return 1
    if mission_data.get("pipeline_count") != len(payload.get("source_pipeline_summary", [])):
        print("cockpit_status_mission_pipeline_count_mismatch=true")
        return 1
    if not isinstance(mission_data.get("logged_in_sources"), list) or not isinstance(mission_data.get("connected_sources"), list):
        print("cockpit_status_mission_source_lists_invalid=true")
        return 1
    if "observation inputs only" not in mission_data.get("boundary", ""):
        print("cockpit_status_mission_source_boundary_weak=true")
        return 1
    if mission_data.get("durable_expected_source_count") != durable_ingestion.get("expected_source_count"):
        print("cockpit_status_mission_durable_expected_count_mismatch=true")
        return 1
    if mission_data.get("durable_replayed_source_count") != durable_ingestion.get("replayed_source_count"):
        print("cockpit_status_mission_durable_replay_count_mismatch=true")
        return 1
    if mission_data.get("preference_mcp_status") != preference_mcp.get("status"):
        print("cockpit_status_mission_preference_mcp_status_mismatch=true")
        return 1
    if mission_data.get("preference_mcp_identity_status") != preference_mcp.get("identity_status"):
        print("cockpit_status_mission_preference_mcp_identity_mismatch=true")
        return 1
    if mission_data.get("preference_mcp_quota_status") != preference_mcp.get("quota_status"):
        print("cockpit_status_mission_preference_mcp_quota_mismatch=true")
        return 1
    if mission_data.get("preference_mcp_catalog_status") != preference_mcp.get("catalog_status"):
        print("cockpit_status_mission_preference_mcp_catalog_mismatch=true")
        return 1
    if mission_data.get("preference_mcp_domain_pack_count") != preference_mcp.get("approved_domain_pack_count"):
        print("cockpit_status_mission_preference_mcp_domain_pack_mismatch=true")
        return 1
    if mission_data.get("preference_mcp_provenance_status") != preference_mcp.get("provenance_status"):
        print("cockpit_status_mission_preference_mcp_provenance_mismatch=true")
        return 1
    if mission_data.get("preference_mcp_shadow_context_status") != preference_mcp.get("shadow_context_status"):
        print("cockpit_status_mission_preference_mcp_shadow_context_mismatch=true")
        return 1
    if "Supplemental data planes are observation inputs only" not in mission_data.get("boundary", ""):
        print("cockpit_status_mission_preference_mcp_boundary_missing=true")
        return 1
    mission_durable = mission.get("durable_spine", {})
    missing_mission_durable_fields = sorted(MISSION_DURABLE_REQUIRED_FIELDS - set(mission_durable))
    if missing_mission_durable_fields:
        print("cockpit_status_mission_durable_fields_missing=" + ",".join(missing_mission_durable_fields))
        return 1
    if mission_durable.get("write_authority") is not False:
        print("cockpit_status_mission_durable_write_authority_enabled=true")
        return 1
    if mission_durable.get("signal_authority") is not False or mission_durable.get("order_authority") is not False:
        print("cockpit_status_mission_durable_authority_enabled=true")
        return 1
    if mission_durable.get("replayed_source_count") != durable_ingestion.get("replayed_source_count"):
        print("cockpit_status_mission_durable_count_mismatch=true")
        return 1
    if "cannot create signals" not in mission_durable.get("boundary", ""):
        print("cockpit_status_mission_durable_boundary_weak=true")
        return 1
    mission_philosophy = mission.get("trading_philosophy", {})
    missing_mission_philosophy_fields = sorted(MISSION_PHILOSOPHY_REQUIRED_FIELDS - set(mission_philosophy))
    if missing_mission_philosophy_fields:
        print("cockpit_status_mission_philosophy_fields_missing=" + ",".join(missing_mission_philosophy_fields))
        return 1
    if "private prior" not in mission_philosophy.get("boundary", "").lower():
        print("cockpit_status_mission_philosophy_boundary_weak=true")
        return 1
    if len(mission_philosophy.get("current_self_directive", [])) < 4:
        print("cockpit_status_mission_self_directive_missing=true")
        return 1
    mission_stack = mission.get("system_stack", {})
    missing_mission_stack_fields = sorted(MISSION_STACK_REQUIRED_FIELDS - set(mission_stack))
    if missing_mission_stack_fields:
        print("cockpit_status_mission_stack_fields_missing=" + ",".join(missing_mission_stack_fields))
        return 1
    if mission_stack.get("preference_mcp") != preference_mcp.get("status"):
        print("cockpit_status_mission_stack_preference_mcp_mismatch=true")
        return 1
    if mission_stack.get("paper_live_activation") != paper_live_activation.get("status"):
        print("cockpit_status_mission_stack_paper_live_activation_mismatch=true")
        return 1
    if mission_stack.get("paper_live_activation_approved") != (
        paper_live_activation.get("paper_live_activation_approved")
    ):
        print("cockpit_status_mission_stack_paper_live_activation_approval_mismatch=true")
        return 1
    if mission_stack.get("paper_live_activation_system_approval_logged") != (
        paper_live_activation.get("paper_trading_system_approval_logged")
    ):
        print("cockpit_status_mission_stack_paper_live_activation_logged_mismatch=true")
        return 1
    if mission_stack.get("paper_live_qctrl_product_access") != (
        paper_live_qctrl_product_access.get("status")
    ):
        print("cockpit_status_mission_stack_paper_live_qctrl_status_mismatch=true")
        return 1
    if mission_stack.get("paper_live_qctrl_product_access_verified") != (
        paper_live_qctrl_product_access.get("product_access_verified")
    ):
        print("cockpit_status_mission_stack_paper_live_qctrl_verified_mismatch=true")
        return 1
    if mission_stack.get("paper_live_qctrl_provider_call_count") != (
        paper_live_qctrl_product_access.get("provider_call_count")
    ):
        print("cockpit_status_mission_stack_paper_live_qctrl_call_count_mismatch=true")
        return 1
    if mission_stack.get("paper_operational_mode") != paper_operational_mode.get("status"):
        print("cockpit_status_mission_stack_paper_operational_mode_mismatch=true")
        return 1
    if mission_stack.get("paper_operational_mode_effective") != (
        paper_operational_mode.get("paper_operational_mode_effective")
    ):
        print("cockpit_status_mission_stack_paper_operational_mode_effective_mismatch=true")
        return 1
    if mission_stack.get("paper_operational_mode_runtime_override") != (
        paper_operational_mode.get("runtime_artifact_override_enabled")
    ):
        print("cockpit_status_mission_stack_paper_operational_mode_override_mismatch=true")
        return 1
    if mission_stack.get("paperops_alpaca_submit_enablement") != (
        paperops_alpaca_submit_enablement.get("status")
    ):
        print("cockpit_status_mission_stack_paperops_submit_enablement_mismatch=true")
        return 1
    if mission_stack.get("paperops_alpaca_submit_enablement_effective") != (
        paperops_alpaca_submit_enablement.get("alpaca_paper_submit_effective")
    ):
        print("cockpit_status_mission_stack_paperops_submit_enablement_effective_mismatch=true")
        return 1
    if mission_stack.get("paperops_alpaca_submit_enablement_path_available") != (
        paperops_alpaca_submit_enablement.get("paper_post_path_available")
    ):
        print("cockpit_status_mission_stack_paperops_submit_enablement_path_mismatch=true")
        return 1
    if mission_stack.get("paperops_alpaca_paper_post") != paperops_alpaca_paper_post.get("status"):
        print("cockpit_status_mission_stack_paperops_alpaca_post_mismatch=true")
        return 1
    if mission_stack.get("paperops_alpaca_paper_post_called_count") != (
        paperops_alpaca_paper_post.get("alpaca_paper_post_called_count")
    ):
        print("cockpit_status_mission_stack_paperops_alpaca_post_count_mismatch=true")
        return 1
    if mission_stack.get("rs6_lifecycle_portfolio_postmortem") != (
        paper_lifecycle_postmortem.get("status")
    ):
        print("cockpit_status_mission_stack_rs6_status_mismatch=true")
        return 1
    if mission_stack.get("rs6_portfolio_value_source") != (
        paper_lifecycle_postmortem.get("portfolio_value_source")
    ):
        print("cockpit_status_mission_stack_rs6_source_mismatch=true")
        return 1
    if mission_stack.get("rs6_balance_ticker_broker_account_derived") != (
        paper_lifecycle_postmortem.get("balance_ticker_broker_account_derived")
    ):
        print("cockpit_status_mission_stack_rs6_balance_source_mismatch=true")
        return 1
    if mission_stack.get("rs6_closed_trade_postmortem_coverage_count") != (
        paper_lifecycle_postmortem.get("closed_trade_postmortem_coverage_count")
    ):
        print("cockpit_status_mission_stack_rs6_postmortem_coverage_mismatch=true")
        return 1
    if mission_stack.get("rs6_closed_trade_missing_postmortem_count") != (
        paper_lifecycle_postmortem.get("closed_trade_missing_postmortem_count")
    ):
        print("cockpit_status_mission_stack_rs6_missing_postmortem_mismatch=true")
        return 1
    if mission_stack.get("rs6_paper_proof_ledger_verified_record_count") != (
        paper_lifecycle_postmortem.get("paper_proof_ledger_verified_record_count")
    ):
        print("cockpit_status_mission_stack_rs6_proof_record_mismatch=true")
        return 1
    if mission_stack.get("rs6_mirror_trade_counted_for_proof_count") != (
        paper_lifecycle_postmortem.get("mirror_trade_counted_for_proof_count")
    ):
        print("cockpit_status_mission_stack_rs6_mirror_proof_mismatch=true")
        return 1
    if mission_stack.get("operator_inbox") != operator_inbox.get("status"):
        print("cockpit_status_mission_stack_rs7_status_mismatch=true")
        return 1
    if mission_stack.get("operator_inbox_item_count") != operator_inbox.get("item_count"):
        print("cockpit_status_mission_stack_rs7_item_count_mismatch=true")
        return 1
    if mission_stack.get("operator_inbox_open_item_count") != operator_inbox.get("open_item_count"):
        print("cockpit_status_mission_stack_rs7_open_count_mismatch=true")
        return 1
    if mission_stack.get("operator_inbox_high_or_critical_item_count") != (
        operator_inbox.get("high_or_critical_item_count")
    ):
        print("cockpit_status_mission_stack_rs7_high_count_mismatch=true")
        return 1
    if mission_stack.get("operator_inbox_postmortem_due_item_count") != (
        operator_inbox.get("postmortem_due_item_count")
    ):
        print("cockpit_status_mission_stack_rs7_postmortem_count_mismatch=true")
        return 1
    if mission_stack.get("operator_inbox_telegram_command_authority") is not False:
        print("cockpit_status_mission_stack_rs7_telegram_command_authority_enabled=true")
        return 1
    if mission_stack.get("paperops_paper_lifecycle_polling_enablement") != (
        paperops_lifecycle_polling_enablement.get("status")
    ):
        print("cockpit_status_mission_stack_paperops_lifecycle_polling_mismatch=true")
        return 1
    if mission_stack.get("paperops_paper_lifecycle_polling_active") != (
        paperops_lifecycle_polling_enablement.get("active_lifecycle_polling_enabled")
    ):
        print("cockpit_status_mission_stack_paperops_lifecycle_polling_active_mismatch=true")
        return 1
    if (
        mission_stack.get("paperops_paper_lifecycle_poller")
        != paperops_paper_lifecycle_poller.get("status")
    ):
        print("cockpit_status_mission_stack_paperops_lifecycle_poller_mismatch=true")
        return 1
    if mission_stack.get("paperops_paper_lifecycle_poller_order_poll_called_count") != (
        paperops_paper_lifecycle_poller.get("paper_order_poll_called_count")
    ):
        print("cockpit_status_mission_stack_paperops_lifecycle_poller_count_mismatch=true")
        return 1
    if mission_stack.get("paperops_guarded_paper_exit_enablement") != (
        paperops_guarded_exit_enablement.get("status")
    ):
        print("cockpit_status_mission_stack_guarded_exit_enablement_mismatch=true")
        return 1
    if mission_stack.get("paperops_guarded_paper_exit_effective") != (
        paperops_guarded_exit_enablement.get("alpaca_paper_exit_effective")
    ):
        print("cockpit_status_mission_stack_guarded_exit_effective_mismatch=true")
        return 1
    if mission_stack.get("paperops_guarded_paper_exit_close_called_count") != (
        paperops_guarded_exit_enablement.get("paper_position_close_called_count")
    ):
        print("cockpit_status_mission_stack_guarded_exit_close_count_mismatch=true")
        return 1
    if mission_stack.get("paperops_paper_exit_path") != paperops_paper_exit_path.get("status"):
        print("cockpit_status_mission_stack_paperops_exit_path_mismatch=true")
        return 1
    if mission_stack.get("paperops_paper_exit_path_close_called_count") != (
        paperops_paper_exit_path.get("paper_position_close_called_count")
    ):
        print("cockpit_status_mission_stack_paperops_exit_path_count_mismatch=true")
        return 1
    if mission_stack.get("paperops_notification_review") != paperops_notification_review.get(
        "status"
    ):
        print("cockpit_status_mission_stack_paperops_notification_review_mismatch=true")
        return 1
    if mission_stack.get("paperops_notification_review_live_send_allowed_count") != (
        paperops_notification_review.get("live_send_allowed_count")
    ):
        print("cockpit_status_mission_stack_paperops_notification_review_count_mismatch=true")
        return 1
    if mission_stack.get("paperops_30_day_operations") != paperops_30_day_operations.get(
        "status"
    ):
        print("cockpit_status_mission_stack_paperops_30_day_status_mismatch=true")
        return 1
    if mission_stack.get("paperops_30_day_operations_scheduler_status") != (
        paperops_30_day_operations.get("scheduler_status")
    ):
        print("cockpit_status_mission_stack_paperops_30_day_scheduler_mismatch=true")
        return 1
    if mission_stack.get("paperops_30_day_operations_active_day_number") != (
        paperops_30_day_operations.get("active_day_number")
    ):
        print("cockpit_status_mission_stack_paperops_30_day_day_mismatch=true")
        return 1
    if mission_stack.get("paperops_cockpit_notification_upgrade") != (
        paperops_cockpit_notification.get("status")
    ):
        print("cockpit_status_mission_stack_pt9_status_mismatch=true")
        return 1
    if mission_stack.get("paperops_cockpit_notification_ready") != (
        paperops_cockpit_notification.get("cockpit_upgrade_ready")
    ):
        print("cockpit_status_mission_stack_pt9_ready_mismatch=true")
        return 1
    if mission_stack.get("paperops_cockpit_notification_readout_count") != (
        paperops_cockpit_notification.get("fund_manager_readout_count")
    ):
        print("cockpit_status_mission_stack_pt9_readout_count_mismatch=true")
        return 1
    if mission_stack.get("paperops_cockpit_notification_qctrl_hold") != (
        paperops_cockpit_notification.get("qctrl_hold_visible")
    ):
        print("cockpit_status_mission_stack_pt9_qctrl_hold_mismatch=true")
        return 1
    if mission_stack.get("paperops_cockpit_notification_live_send_allowed_count") != (
        paperops_cockpit_notification.get("notification_live_send_allowed_count")
    ):
        print("cockpit_status_mission_stack_pt9_live_send_mismatch=true")
        return 1
    if mission_stack.get("paper_live_certification") != (
        paper_live_certification.get("status")
    ):
        print("cockpit_status_mission_stack_pt10_status_mismatch=true")
        return 1
    if mission_stack.get("paper_live_control_plane_certified") != (
        paper_live_certification.get("paper_live_control_plane_certified")
    ):
        print("cockpit_status_mission_stack_pt10_control_plane_mismatch=true")
        return 1
    if mission_stack.get("paper_live_certified") != (
        paper_live_certification.get("paper_live_certified")
    ):
        print("cockpit_status_mission_stack_pt10_certified_mismatch=true")
        return 1
    if mission_stack.get("paper_live_certification_blocker_count") != (
        paper_live_certification.get("certification_blocker_count")
    ):
        print("cockpit_status_mission_stack_pt10_blocker_count_mismatch=true")
        return 1
    if mission_stack.get("paper_live_operation_allowed") != (
        paper_live_certification.get("paper_live_operation_allowed")
    ):
        print("cockpit_status_mission_stack_pt10_operation_allowed_mismatch=true")
        return 1
    if mission_stack.get("paper_live_unattended_execution_delegation_enabled") != (
        paper_live_certification.get(
            "paper_live_unattended_execution_delegation_enabled"
        )
    ):
        print("cockpit_status_mission_stack_pt10_unattended_delegation_mismatch=true")
        return 1
    if mission_stack.get("paper_live_unattended_execution_delegation_reason") != (
        paper_live_certification.get(
            "paper_live_unattended_execution_delegation_reason"
        )
    ):
        print("cockpit_status_mission_stack_pt10_unattended_reason_mismatch=true")
        return 1
    if mission_stack.get("paperops_active_paper_trading_automation") != (
        paperops_active_automation.get("status")
    ):
        print("cockpit_status_mission_stack_active_paper_automation_mismatch=true")
        return 1
    if mission_stack.get("paperops_active_paper_trading_automation_enabled") != (
        paperops_active_automation.get("active_paper_trading_automation_enabled")
    ):
        print("cockpit_status_mission_stack_active_paper_automation_enabled_mismatch=true")
        return 1
    if mission_stack.get("paperops_active_paper_trading_qctrl_hold") != (
        paperops_active_automation.get("qctrl_consultation_hold_active")
    ):
        print("cockpit_status_mission_stack_active_paper_automation_qctrl_mismatch=true")
        return 1
    if mission_stack.get("paperops_active_paper_trading_submit_allowed") != (
        paperops_active_automation.get("paper_submit_step_allowed")
    ):
        print("cockpit_status_mission_stack_active_paper_automation_submit_mismatch=true")
        return 1
    if mission_stack.get("paperops_active_paper_trading_unattended_delegation_enabled") != (
        paperops_active_automation.get(
            "unattended_paper_execution_delegation_enabled"
        )
    ):
        print("cockpit_status_mission_stack_active_paper_automation_unattended_mismatch=true")
        return 1
    if mission_stack.get("paperops_active_paper_trading_unattended_delegation_reason") != (
        paperops_active_automation.get(
            "unattended_paper_execution_delegation_reason"
        )
    ):
        print("cockpit_status_mission_stack_active_paper_automation_reason_mismatch=true")
        return 1
    if mission_stack.get("paperops_active_paper_trading_fresh_submit_count") != (
        paperops_active_automation.get("paperops2_fresh_eligible_submit_record_count")
    ):
        print("cockpit_status_mission_stack_active_paper_automation_fresh_count_mismatch=true")
        return 1
    if mission_stack.get("paperops_active_paper_trading_duplicate_submit_count") != (
        paperops_active_automation.get("paperops2_duplicate_submit_record_count")
    ):
        print("cockpit_status_mission_stack_active_paper_automation_duplicate_count_mismatch=true")
        return 1
    if mission_stack.get("paperops_active_paper_trading_idempotency_ledger_active") != (
        paperops_active_automation.get("paperops2_idempotency_ledger_active")
    ):
        print("cockpit_status_mission_stack_active_paper_automation_ledger_mismatch=true")
        return 1
    if mission_stack.get("paperops_active_paper_trading_rs5_daily_target_policy") != (
        paperops_active_automation.get("rs5_daily_target_policy")
    ):
        print("cockpit_status_mission_stack_active_paper_automation_rs5_policy_mismatch=true")
        return 1
    if mission_stack.get(
        "paperops_active_paper_trading_rs5_max_guarded_submit_attempts_per_run"
    ) != paperops_active_automation.get("rs5_max_guarded_submit_attempts_per_run"):
        print("cockpit_status_mission_stack_active_paper_automation_rs5_attempts_mismatch=true")
        return 1
    if mission_stack.get(
        "paperops_active_paper_trading_rs5_available_distinct_setup_count"
    ) != paperops_active_automation.get("rs5_available_distinct_setup_count"):
        print("cockpit_status_mission_stack_active_paper_automation_rs5_setup_count_mismatch=true")
        return 1
    if mission_stack.get("paperops_active_paper_trading_rs5_can_submit_multiple_today") != (
        paperops_active_automation.get("rs5_can_submit_multiple_today")
    ):
        print("cockpit_status_mission_stack_active_paper_automation_rs5_multi_submit_mismatch=true")
        return 1
    if mission_stack.get("paperops_active_paper_trading_why_not_trading_now") != (
        paperops_active_automation.get("why_not_trading_now")
    ):
        print("cockpit_status_mission_stack_active_paper_automation_why_not_mismatch=true")
        return 1
    if mission_stack.get("paperops_qualified_setup_production") != (
        paperops_qualified_setup_production.get("status")
    ):
        print("cockpit_status_mission_stack_paperops_qualified_setup_mismatch=true")
        return 1
    if mission_stack.get("paperops_qualified_setup_production_qualified_count") != (
        paperops_qualified_setup_production.get("qualified_setup_count")
    ):
        print("cockpit_status_mission_stack_paperops_qualified_setup_count_mismatch=true")
        return 1
    if mission_stack.get("paperops_qualified_setup_production_ready_to_stage") != (
        paperops_qualified_setup_production.get("ready_to_stage_q7_order")
    ):
        print("cockpit_status_mission_stack_paperops_qualified_setup_ready_mismatch=true")
        return 1
    if mission_stack.get("paperops_auto_approval_staged_order") != (
        paperops_auto_approval_staged_order.get("status")
    ):
        print("cockpit_status_mission_stack_paperops_pt4_status_mismatch=true")
        return 1
    if mission_stack.get("paperops_auto_approval_staged_order_staged_count") != (
        paperops_auto_approval_staged_order.get("staged_order_count")
    ):
        print("cockpit_status_mission_stack_paperops_pt4_staged_count_mismatch=true")
        return 1
    if mission_stack.get("paperops_auto_approval_staged_order_ready_for_submit") != (
        paperops_auto_approval_staged_order.get("ready_for_paperops2_submit")
    ):
        print("cockpit_status_mission_stack_paperops_pt4_ready_mismatch=true")
        return 1
    missing_paper_live_fields = sorted(
        PAPER_LIVE_ACTIVATION_REQUIRED_FIELDS - set(paper_live_activation)
    )
    if missing_paper_live_fields:
        print(
            "cockpit_status_paper_live_activation_fields_missing="
            + ",".join(missing_paper_live_fields)
        )
        return 1
    if paper_live_activation.get("status") != "approved_pending_later_enablement":
        print("cockpit_status_paper_live_activation_not_approved=true")
        return 1
    if paper_live_activation.get("public_safe") is not True:
        print("cockpit_status_paper_live_activation_not_public_safe=true")
        return 1
    if paper_live_activation.get("approval_state") != "approved":
        print("cockpit_status_paper_live_activation_approval_state_invalid=true")
        return 1
    if paper_live_activation.get("approval_logged") is not True:
        print("cockpit_status_paper_live_activation_approval_not_logged=true")
        return 1
    if paper_live_activation.get("paper_live_activation_approved") is not True:
        print("cockpit_status_paper_live_activation_approved_false=true")
        return 1
    if paper_live_activation.get("paper_trading_system_approval_logged") is not True:
        print("cockpit_status_paper_live_activation_system_approval_missing=true")
        return 1
    if paper_live_activation.get("paper_order_submission_allowed") is not False:
        print("cockpit_status_paper_live_activation_submit_authority=true")
        return 1
    if paper_live_activation.get("live_capital_enabled") is not False:
        print("cockpit_status_paper_live_activation_live_capital_enabled=true")
        return 1
    if paper_live_activation.get("forced_trades_allowed") is not False:
        print("cockpit_status_paper_live_activation_forced_trades_allowed=true")
        return 1
    if paper_live_activation.get("qctrl_direct_execution_allowed") is not False:
        print("cockpit_status_paper_live_activation_qctrl_execution_authority=true")
        return 1
    for key in (
        "broker_post_called_count",
        "alpaca_post_called_count",
        "live_endpoint_called_count",
    ):
        if int(paper_live_activation.get(key, 0) or 0) != 0:
            print(f"cockpit_status_paper_live_activation_unsafe_counter={key}")
            return 1
    missing_paper_live_qctrl_fields = sorted(
        PAPER_LIVE_QCTRL_PRODUCT_ACCESS_REQUIRED_FIELDS
        - set(paper_live_qctrl_product_access)
    )
    if missing_paper_live_qctrl_fields:
        print(
            "cockpit_status_paper_live_qctrl_product_access_fields_missing="
            + ",".join(missing_paper_live_qctrl_fields)
        )
        return 1
    if paper_live_qctrl_product_access.get("status") not in {
        "blocked_qctrl_product_access_or_subscription",
        "blocked_missing_qctrl_sdk",
        "qctrl_paper_consultation_ready",
    }:
        print("cockpit_status_paper_live_qctrl_product_access_not_checked=true")
        return 1
    if paper_live_qctrl_product_access.get("public_safe") is not True:
        print("cockpit_status_paper_live_qctrl_product_access_not_public_safe=true")
        return 1
    if paper_live_qctrl_product_access.get("provider_call_attempted") is not True:
        print("cockpit_status_paper_live_qctrl_provider_call_not_attempted=true")
        return 1
    if int(paper_live_qctrl_product_access.get("provider_call_count", 0) or 0) < 1:
        print("cockpit_status_paper_live_qctrl_provider_call_count_missing=true")
        return 1
    if paper_live_qctrl_product_access.get("validation_error_count") != 0:
        print("cockpit_status_paper_live_qctrl_validation_errors=true")
        return 1
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
        if paper_live_qctrl_product_access.get(key) is not False:
            print(f"cockpit_status_paper_live_qctrl_unsafe_flag={key}")
            return 1
    for key in (
        "broker_post_called_count",
        "alpaca_post_called_count",
        "live_endpoint_called_count",
    ):
        if int(paper_live_qctrl_product_access.get(key, 0) or 0) != 0:
            print(f"cockpit_status_paper_live_qctrl_unsafe_counter={key}")
            return 1
    missing_paper_operational_mode_fields = sorted(
        PAPER_OPERATIONAL_MODE_REQUIRED_FIELDS - set(paper_operational_mode)
    )
    if missing_paper_operational_mode_fields:
        print(
            "cockpit_status_paper_operational_mode_fields_missing="
            + ",".join(missing_paper_operational_mode_fields)
        )
        return 1
    if paper_operational_mode.get("status") != "enabled_pending_downstream_gates":
        print("cockpit_status_paper_operational_mode_not_enabled=true")
        return 1
    if paper_operational_mode.get("public_safe") is not True:
        print("cockpit_status_paper_operational_mode_not_public_safe=true")
        return 1
    if paper_operational_mode.get("paper_operational_mode_effective") is not True:
        print("cockpit_status_paper_operational_mode_not_effective=true")
        return 1
    if paper_operational_mode.get("paper_operational_flag_disabled") is not False:
        print("cockpit_status_paper_operational_mode_flag_disabled=true")
        return 1
    if paper_operational_mode.get("validation_error_count") != 0:
        print("cockpit_status_paper_operational_mode_validation_errors=true")
        return 1
    for key in (
        "env_file_edited",
        "env_mutation_allowed",
        "execution_allowed",
        "paper_order_allowed",
        "paper_order_submission_allowed",
        "broker_post_allowed",
        "alpaca_post_allowed",
        "live_endpoint_allowed",
        "live_capital_enabled",
        "live_credentials_loaded",
        "qctrl_direct_execution_allowed",
        "qctrl_paper_order_allowed",
        "qctrl_broker_post_allowed",
        "hardware_submission_allowed",
        "phase7_proof_credit_allowed",
        "forced_trades_allowed",
        "secret_value_exposed",
        "raw_response_exposed",
    ):
        if paper_operational_mode.get(key) is not False:
            print(f"cockpit_status_paper_operational_mode_unsafe_flag={key}")
            return 1
    for key in (
        "broker_post_called_count",
        "alpaca_post_called_count",
        "live_endpoint_called_count",
        "qctrl_broker_post_called_count",
        "qctrl_alpaca_post_called_count",
        "qctrl_live_endpoint_called_count",
    ):
        if int(paper_operational_mode.get(key, 0) or 0) != 0:
            print(f"cockpit_status_paper_operational_mode_unsafe_counter={key}")
            return 1
    rs10_waiting_for_qualified_setup = (
        rs10_final_paper_autonomy.get("final_paper_autonomy_certified") is True
        and rs10_final_paper_autonomy.get("guarded_paper_autonomy_allowed") is True
        and rs10_final_paper_autonomy.get("autonomy_currently_actionable") is False
        and (
            "no_fresh_eligible_candidate"
            in (rs10_final_paper_autonomy.get("idle_reasons") or [])
            or "no_fresh_eligible_candidate"
            in (rs10_final_paper_autonomy.get("current_blockers") or [])
        )
        and rs10_final_paper_autonomy.get("certification_blocker_count") == 0
        and rs10_final_paper_autonomy.get("safety_blocker_count") == 0
    )
    no_current_paperops_setup = (
        paperops_qualified_setup_production.get("status")
        == "production_path_ready_no_current_qualified_setup"
        and int(
            paperops_qualified_setup_production.get("qualified_setup_count", 0) or 0
        )
        == 0
        and paperops_auto_approval_staged_order.get("status")
        == "ready_no_current_auto_approved_setup"
        and int(paperops_auto_approval_staged_order.get("staged_order_count", 0) or 0)
        == 0
        and paperops_alpaca_submit_enablement.get("status")
        == "blocked_pending_prerequisites"
        and paperops_lifecycle_polling_enablement.get("status")
        == "blocked_pending_prerequisites"
        and paperops_guarded_exit_enablement.get("status")
        == "blocked_lifecycle_polling_enablement_not_ready"
        and (
            paper_live_certification.get("status") == "blocked_paper_live_control_plane"
            or (
                paper_live_certification.get("status") == "paper_live_certified"
                and paper_live_certification.get("paper_live_certified") is True
                and paper_live_certification.get("paper_live_operation_allowed") is True
                and paper_live_certification.get(
                    "paper_live_unattended_execution_delegation_enabled"
                )
                is True
                and int(
                    paper_live_certification.get("certification_blocker_count", 0)
                    or 0
                )
                == 0
                and rs10_waiting_for_qualified_setup
            )
        )
        and paperops_30_day_operations.get("paper_operational_cycle_safe_to_continue")
        is True
        and paperops_30_day_operations.get("no_forced_trades") is True
        and paperops_30_day_operations.get("live_capital_enabled") is False
        and paperops_30_day_operations.get("phase7_proof_credit_allowed") is False
        and int(paperops_30_day_operations.get("unsafe_write_counter_total", 0) or 0)
        == 0
        and int(paper_live_certification.get("unsafe_write_counter_total", 0) or 0)
        == 0
        and int(
            paperops_alpaca_submit_enablement.get(
                "unsafe_write_counter_total",
                0,
            )
            or 0
        )
        == 0
        and int(
            paperops_lifecycle_polling_enablement.get(
                "unsafe_write_counter_total",
                0,
            )
            or 0
        )
        == 0
        and int(
            paperops_guarded_exit_enablement.get("unsafe_write_counter_total", 0) or 0
        )
        == 0
    )
    missing_paperops_30_day_fields = sorted(
        PAPEROPS_30_DAY_OPERATIONS_REQUIRED_FIELDS - set(paperops_30_day_operations)
    )
    if missing_paperops_30_day_fields:
        print(
            "cockpit_status_paperops_30_day_operations_fields_missing="
            + ",".join(missing_paperops_30_day_fields)
        )
        return 1
    if (
        paperops_30_day_operations.get("status") != "operations_active"
        and not no_current_paperops_setup
    ):
        print("cockpit_status_paperops_30_day_operations_not_active=true")
        return 1
    if paperops_30_day_operations.get("public_safe") is not True:
        print("cockpit_status_paperops_30_day_operations_not_public_safe=true")
        return 1
    if paperops_30_day_operations.get("recorded") is not True:
        print("cockpit_status_paperops_30_day_operations_not_recorded=true")
        return 1
    if paperops_30_day_operations.get("event_log_written") is not True:
        print("cockpit_status_paperops_30_day_operations_event_log_not_written=true")
        return 1
    if paperops_30_day_operations.get("event_log_event_count") != 1:
        print("cockpit_status_paperops_30_day_operations_event_count_mismatch=true")
        return 1
    if (
        paperops_30_day_operations.get("validation_error_count") != 0
        and not no_current_paperops_setup
    ):
        print("cockpit_status_paperops_30_day_operations_validation_errors=true")
        return 1
    if paperops_30_day_operations.get("automation_active") is not True:
        print("cockpit_status_paperops_30_day_operations_automation_inactive=true")
        return 1
    if paperops_30_day_operations.get("automation_prompt_paperops_bound") is not True:
        print("cockpit_status_paperops_30_day_operations_prompt_not_bound=true")
        return 1
    if paperops_30_day_operations.get("dashboard_mirror_public_safe") is not True:
        print("cockpit_status_paperops_30_day_operations_dashboard_not_safe=true")
        return 1
    if paperops_30_day_operations.get("live_capital_enabled") is not False:
        print("cockpit_status_paperops_30_day_operations_live_capital_enabled=true")
        return 1
    if paperops_30_day_operations.get("phase7_proof_credit_allowed") is not False:
        print("cockpit_status_paperops_30_day_operations_proof_credit_allowed=true")
        return 1
    if int(paperops_30_day_operations.get("unsafe_write_counter_total", 0) or 0) != 0:
        print("cockpit_status_paperops_30_day_operations_unsafe_counter_nonzero=true")
        return 1
    if "cannot force trades" not in paperops_30_day_operations.get("boundary", ""):
        print("cockpit_status_paperops_30_day_operations_boundary_weak=true")
        return 1
    missing_pt9_fields = sorted(
        set(PAPEROPS_COCKPIT_NOTIFICATION_REQUIRED_FIELDS)
        - set(paperops_cockpit_notification)
    )
    if missing_pt9_fields:
        print(
            "cockpit_status_paperops_cockpit_notification_fields_missing="
            + ",".join(missing_pt9_fields)
        )
        return 1
    if paperops_cockpit_notification.get("status") != (
        "cockpit_notification_upgrade_ready"
    ):
        print("cockpit_status_paperops_cockpit_notification_not_ready=true")
        return 1
    if paperops_cockpit_notification.get("public_safe") is not True:
        print("cockpit_status_paperops_cockpit_notification_not_public_safe=true")
        return 1
    if paperops_cockpit_notification.get("recorded") is not True:
        print("cockpit_status_paperops_cockpit_notification_not_recorded=true")
        return 1
    if paperops_cockpit_notification.get("event_log_written") is not True:
        print("cockpit_status_paperops_cockpit_notification_event_log_not_written=true")
        return 1
    if paperops_cockpit_notification.get("event_log_event_count") != 1:
        print("cockpit_status_paperops_cockpit_notification_event_count_mismatch=true")
        return 1
    if paperops_cockpit_notification.get("validation_error_count") != 0:
        print("cockpit_status_paperops_cockpit_notification_validation_errors=true")
        return 1
    if paperops_cockpit_notification.get("cockpit_upgrade_ready") is not True:
        print("cockpit_status_paperops_cockpit_notification_flag_false=true")
        return 1
    if paperops_cockpit_notification.get("notification_upgrade_ready") is not True:
        print("cockpit_status_paperops_cockpit_notification_notification_false=true")
        return 1
    if int(paperops_cockpit_notification.get("fund_manager_readout_count", 0) or 0) < 5:
        print("cockpit_status_paperops_cockpit_notification_readouts_missing=true")
        return 1
    if (
        paperops_cockpit_notification.get("qctrl_hold_visible") is True
        and paperops_cockpit_notification.get("paper_submit_visible_as_held")
        is not True
    ):
        print("cockpit_status_paperops_cockpit_notification_qctrl_hold_hidden=true")
        return 1
    for key in (
        "notification_live_send_allowed_count",
        "notification_command_path_enabled_count",
        "notification_broker_write_allowed_count",
        "notification_paper_order_allowed_count",
        "live_endpoint_called_count",
        "broker_post_called_count",
        "alpaca_post_called_count",
        "outbox_message_written_count",
        "unsafe_write_counter_total",
    ):
        if int(paperops_cockpit_notification.get(key, 0) or 0) != 0:
            print(f"cockpit_status_paperops_cockpit_notification_unsafe_{key}=true")
            return 1
    if paperops_cockpit_notification.get("phase7_proof_credit_allowed") is not False:
        print("cockpit_status_paperops_cockpit_notification_proof_credit_allowed=true")
        return 1
    if (
        "review-only notification previews"
        not in paperops_cockpit_notification.get("boundary", "")
    ):
        print("cockpit_status_paperops_cockpit_notification_boundary_weak=true")
        return 1
    missing_paper_live_certification_fields = sorted(
        set(PAPER_LIVE_CERTIFICATION_REQUIRED_FIELDS) - set(paper_live_certification)
    )
    if missing_paper_live_certification_fields:
        print(
            "cockpit_status_paper_live_certification_fields_missing="
            + ",".join(missing_paper_live_certification_fields)
        )
        return 1
    if paper_live_certification.get("status") not in {
        "blocked_pending_qctrl_and_phase7_proof",
        "blocked_pending_qctrl",
        "blocked_pending_phase7_proof",
        "blocked_pending_certification_gates",
        "blocked_paper_live_control_plane",
        "paper_live_certified",
    }:
        print("cockpit_status_paper_live_certification_not_evaluated=true")
        return 1
    if paper_live_certification.get("public_safe") is not True:
        print("cockpit_status_paper_live_certification_not_public_safe=true")
        return 1
    if paper_live_certification.get("recorded") is not True:
        print("cockpit_status_paper_live_certification_not_recorded=true")
        return 1
    if paper_live_certification.get("event_log_written") is not True:
        print("cockpit_status_paper_live_certification_event_log_not_written=true")
        return 1
    if paper_live_certification.get("event_log_event_count") != 1:
        print("cockpit_status_paper_live_certification_event_count_mismatch=true")
        return 1
    if paper_live_certification.get("validation_error_count") != 0:
        print("cockpit_status_paper_live_certification_validation_errors=true")
        return 1
    if (
        paper_live_certification.get("paper_live_control_plane_certified") is not True
        and not no_current_paperops_setup
    ):
        print("cockpit_status_paper_live_control_plane_not_certified=true")
        return 1
    if (
        paper_live_certification.get("paper_live_certified") is not True
        and not no_current_paperops_setup
    ):
        print("cockpit_status_paper_live_not_certified=true")
        return 1
    if (
        paper_live_certification.get("paper_live_operation_allowed") is not True
        and not no_current_paperops_setup
    ):
        print("cockpit_status_paper_live_operation_not_allowed=true")
        return 1
    if (
        paper_live_certification.get(
            "paper_live_unattended_execution_delegation_enabled"
        )
        is not True
        and not no_current_paperops_setup
    ):
        print("cockpit_status_paper_live_unattended_delegation_not_enabled=true")
        return 1
    if (
        int(paper_live_certification.get("certification_blocker_count", 0) or 0) != 0
        and not no_current_paperops_setup
    ):
        print("cockpit_status_paper_live_certification_blockers_present=true")
        return 1
    if (
        paper_live_certification.get("qctrl_hold_active") is True
        and paper_live_certification.get("paper_submit_visible_as_held") is not True
    ):
        print("cockpit_status_paper_live_submit_hold_hidden=true")
        return 1
    if paper_live_certification.get("live_capital_enabled") is not False:
        print("cockpit_status_paper_live_certification_live_capital_enabled=true")
        return 1
    if paper_live_certification.get("phase7_proof_credit_allowed") is not False:
        print("cockpit_status_paper_live_certification_proof_credit_allowed=true")
        return 1
    for key in (
        "live_endpoint_called_count",
        "broker_post_called_count",
        "alpaca_post_called_count",
        "broker_write_allowed_count",
        "notification_live_send_allowed_count",
        "telegram_command_path_enabled_count",
        "outbox_message_written_count",
        "unsafe_write_counter_total",
    ):
        if int(paper_live_certification.get(key, 0) or 0) != 0:
            print(f"cockpit_status_paper_live_certification_unsafe_{key}=true")
            return 1
    if (
        "cannot mark paper performance as mature without verified records"
        not in paper_live_certification.get("boundary", "")
    ):
        print("cockpit_status_paper_live_certification_boundary_weak=true")
        return 1
    missing_active_automation_fields = sorted(
        PAPEROPS_ACTIVE_AUTOMATION_REQUIRED_FIELDS - set(paperops_active_automation)
    )
    if missing_active_automation_fields:
        print(
            "cockpit_status_paperops_active_automation_fields_missing="
            + ",".join(missing_active_automation_fields)
        )
        return 1
    paper_authority_allows_paused_active_runner = (
        paper_authority.get("status") == "paper_authorized_blocked_operational"
        and paper_authority.get("paper_authorized") is True
        and paper_authority.get("live_capital_enabled") is False
        and paper_authority.get("live_capital_blocked") is True
        and "automation_not_active"
        in (paper_authority.get("operational_blockers") or [])
        and not (paper_authority.get("safety_blockers") or [])
        and paperops_active_automation.get("status")
        == "blocked_active_automation_safety_or_binding"
    )
    if (
        paperops_active_automation.get("status")
        not in PAPEROPS_ACTIVE_AUTOMATION_READY_STATUSES
        and not paper_authority_allows_paused_active_runner
    ):
        print("cockpit_status_paperops_active_automation_not_ready=true")
        return 1
    if paperops_active_automation.get("public_safe") is not True:
        print("cockpit_status_paperops_active_automation_not_public_safe=true")
        return 1
    if paperops_active_automation.get("recorded") is not True:
        print("cockpit_status_paperops_active_automation_not_recorded=true")
        return 1
    if paperops_active_automation.get("event_log_written") is not True:
        print("cockpit_status_paperops_active_automation_event_log_not_written=true")
        return 1
    if paperops_active_automation.get("event_log_event_count") != 1:
        print("cockpit_status_paperops_active_automation_event_count_mismatch=true")
        return 1
    if paperops_active_automation.get("validation_error_count") != 0:
        print("cockpit_status_paperops_active_automation_validation_errors=true")
        return 1
    if (
        paperops_active_automation.get("active_paper_trading_automation_enabled")
        is not True
        and not paper_authority_allows_paused_active_runner
    ):
        print("cockpit_status_paperops_active_automation_enabled_false=true")
        return 1
    if (
        paperops_active_automation.get("active_paper_trading_automation_effective")
        is not True
        and not paper_authority_allows_paused_active_runner
    ):
        print("cockpit_status_paperops_active_automation_effective_false=true")
        return 1
    if (
        paperops_active_automation.get("automation_active") is not True
        and not paper_authority_allows_paused_active_runner
    ):
        print("cockpit_status_paperops_active_automation_scheduler_inactive=true")
        return 1
    if paperops_active_automation.get("automation_prompt_active_trade_bound") is not True:
        print("cockpit_status_paperops_active_automation_prompt_not_bound=true")
        return 1
    if paperops_active_automation.get("paper_endpoint_confirmed") is not True:
        print("cockpit_status_paperops_active_automation_paper_endpoint_missing=true")
        return 1
    if (
        paperops_active_automation.get(
            "unattended_paper_execution_delegation_enabled"
        )
        is not True
        and not paper_authority_allows_paused_active_runner
    ):
        print("cockpit_status_paperops_active_automation_unattended_not_enabled=true")
        return 1
    if paperops_active_automation.get("paperops2_idempotency_ledger_active") is not True:
        print("cockpit_status_paperops_active_automation_ledger_inactive=true")
        return 1
    if (
        paperops_active_automation.get("qctrl_consultation_hold_active") is True
        and paperops_active_automation.get("paper_submit_step_allowed") is True
    ):
        print("cockpit_status_paperops_active_automation_qctrl_bypass=true")
        return 1
    for key in (
        "direct_broker_shortcut_allowed",
        "qctrl_direct_execution_allowed",
        "forced_trades_allowed",
        "phase7_proof_credit_allowed",
        "live_capital_enabled",
    ):
        if paperops_active_automation.get(key) is not False:
            print(f"cockpit_status_paperops_active_automation_forbidden={key}")
            return 1
    if paperops_active_automation.get("rs5_daily_target_policy") != "minimum_not_ceiling":
        print("cockpit_status_paperops_active_automation_rs5_policy_invalid=true")
        return 1
    if paperops_active_automation.get("rs5_daily_target_is_minimum") is not True:
        print("cockpit_status_paperops_active_automation_rs5_target_not_minimum=true")
        return 1
    if (
        paperops_active_automation.get(
            "rs5_daily_target_blocks_additional_qualified_setups"
        )
        is not False
    ):
        print("cockpit_status_paperops_active_automation_rs5_target_ceiling=true")
        return 1
    if paperops_active_automation.get("rs5_guarded_submit_transport") != "paperops2_only":
        print("cockpit_status_paperops_active_automation_rs5_transport_invalid=true")
        return 1
    if int(
        paperops_active_automation.get("rs5_max_guarded_submit_attempts_per_run", 0)
        or 0
    ) > 3:
        print("cockpit_status_paperops_active_automation_rs5_attempts_exceed_cap=true")
        return 1
    if (
        paperops_active_automation.get("rs5_daily_target_met") is True
        and int(
            paperops_active_automation.get("rs5_available_distinct_setup_count", 0)
            or 0
        )
        > 0
        and paperops_active_automation.get("idle_reason")
        == "daily_paper_trade_target_met"
    ):
        print("cockpit_status_paperops_active_automation_rs5_target_ceiling_detected=true")
        return 1
    if not str(paperops_active_automation.get("why_not_trading_now") or "").strip():
        print("cockpit_status_paperops_active_automation_why_not_missing=true")
        return 1
    for key in ("live_endpoint_called_count", "unsafe_write_counter_total"):
        if int(paperops_active_automation.get(key, 0) or 0) != 0:
            print(f"cockpit_status_paperops_active_automation_unsafe_counter={key}")
            return 1
    active_automation_boundary = paperops_active_automation.get("boundary", "")
    if (
        "PT-8 binds the hourly PaperOps automation" not in active_automation_boundary
        or "PaperOps-2, PaperOps-3, and PaperOps-4"
        not in active_automation_boundary
        or "Q-CTRL paper consultation hold" not in active_automation_boundary
        or "only submit to Alpaca paper" not in active_automation_boundary
        or "cannot enable live capital" not in active_automation_boundary
    ):
        print("cockpit_status_paperops_active_automation_boundary_weak=true")
        return 1
    missing_paper_authority_fields = sorted(
        set(PAPER_AUTHORITY_RECONCILIATION_PUBLIC_FIELDS) - set(paper_authority)
    )
    if missing_paper_authority_fields:
        print(
            "cockpit_status_paper_authority_reconciliation_fields_missing="
            + ",".join(missing_paper_authority_fields)
        )
        return 1
    if paper_authority.get("validation_error_count") != 0:
        print("cockpit_status_paper_authority_reconciliation_validation_errors=true")
        return 1
    if validate_paper_authority_reconciliation(paper_authority):
        print("cockpit_status_paper_authority_reconciliation_invalid=true")
        return 1
    if paper_authority.get("public_safe") is not True:
        print("cockpit_status_paper_authority_reconciliation_not_public_safe=true")
        return 1
    if paper_authority.get("paper_submission_transport") != "paperops_guarded_alpaca_paper":
        print("cockpit_status_paper_authority_reconciliation_transport_invalid=true")
        return 1
    if paper_authority.get("live_capital_enabled") is not False:
        print("cockpit_status_paper_authority_reconciliation_live_capital_enabled=true")
        return 1
    if paper_authority.get("live_capital_blocked") is not True:
        print("cockpit_status_paper_authority_reconciliation_live_capital_not_blocked=true")
        return 1
    if paper_authority.get("status") not in {
        "blocked_by_safety",
        "paper_authorized_blocked_operational",
        "paper_authorized_waiting_for_setup",
        "paper_authorized_ready_to_submit",
        "paper_authorized_ready_to_poll",
        "paper_authorized_ready_to_exit",
        "paper_authorized_idle",
    }:
        print("cockpit_status_paper_authority_reconciliation_status_invalid=true")
        return 1
    if paper_authority.get("paper_submit_currently_allowed") is True and (
        paperops_active_automation.get("paper_submit_step_allowed") is not True
    ):
        print("cockpit_status_paper_authority_reconciliation_submit_invented=true")
        return 1
    if paper_authority.get("status") == "paper_authorized_blocked_operational" and (
        "automation_not_active" not in (paper_authority.get("operational_blockers") or [])
    ):
        print("cockpit_status_paper_authority_reconciliation_automation_hidden=true")
        return 1
    missing_qualified_setup_fields = sorted(
        PAPEROPS_QUALIFIED_SETUP_PRODUCTION_REQUIRED_FIELDS
        - set(paperops_qualified_setup_production)
    )
    if missing_qualified_setup_fields:
        print(
            "cockpit_status_paperops_qualified_setup_production_fields_missing="
            + ",".join(missing_qualified_setup_fields)
        )
        return 1
    if paperops_qualified_setup_production.get("status") not in {
        "production_path_ready_with_qualified_setup",
        "production_path_ready_no_current_qualified_setup",
    }:
        print("cockpit_status_paperops_qualified_setup_production_not_ready=true")
        return 1
    if paperops_qualified_setup_production.get("public_safe") is not True:
        print("cockpit_status_paperops_qualified_setup_production_not_public_safe=true")
        return 1
    if paperops_qualified_setup_production.get("recorded") is not True:
        print("cockpit_status_paperops_qualified_setup_production_not_recorded=true")
        return 1
    if paperops_qualified_setup_production.get("event_log_written") is not True:
        print("cockpit_status_paperops_qualified_setup_production_event_log_not_written=true")
        return 1
    if paperops_qualified_setup_production.get("event_log_event_count") != 1:
        print("cockpit_status_paperops_qualified_setup_production_event_count_mismatch=true")
        return 1
    if paperops_qualified_setup_production.get("validation_error_count") != 0:
        print("cockpit_status_paperops_qualified_setup_production_validation_errors=true")
        return 1
    if paperops_qualified_setup_production.get("qualified_setup_production_path_ready") is not True:
        print("cockpit_status_paperops_qualified_setup_production_path_not_ready=true")
        return 1
    if int(paperops_qualified_setup_production.get("production_candidate_count", 0) or 0) < 1:
        print("cockpit_status_paperops_qualified_setup_production_candidates_missing=true")
        return 1
    if paperops_qualified_setup_production.get("live_capital_enabled") is not False:
        print("cockpit_status_paperops_qualified_setup_production_live_capital_enabled=true")
        return 1
    if paperops_qualified_setup_production.get("paper_order_submission_allowed") is not False:
        print("cockpit_status_paperops_qualified_setup_production_submit_authority=true")
        return 1
    if paperops_qualified_setup_production.get("phase7_proof_credit_allowed") is not False:
        print("cockpit_status_paperops_qualified_setup_production_proof_credit_allowed=true")
        return 1
    if paperops_qualified_setup_production.get("forced_trades_allowed") is not False:
        print("cockpit_status_paperops_qualified_setup_production_forced_trades_allowed=true")
        return 1
    if paperops_qualified_setup_production.get("qualified_setup_creation_forced") is not False:
        print("cockpit_status_paperops_qualified_setup_production_forced_setup=true")
        return 1
    if int(paperops_qualified_setup_production.get("unsafe_write_counter_total", 0) or 0) != 0:
        print("cockpit_status_paperops_qualified_setup_production_unsafe_counter_nonzero=true")
        return 1
    pt3_qualified_count = int(
        paperops_qualified_setup_production.get("qualified_setup_count", 0) or 0
    )
    phase7_demo_qualified_count = int(
        paperops_qualified_setup_production.get("phase7_demo_qualified_setup_count", 0)
        or 0
    )
    q7_ledger_qualified_count = int(
        paperops_qualified_setup_production.get("source_qualified_setup_ledger_count", 0)
        or 0
    )
    if phase7_demo_qualified_count > pt3_qualified_count:
        print("cockpit_status_paperops_qualified_setup_production_demo_count_exceeds_pt3=true")
        return 1
    if q7_ledger_qualified_count > pt3_qualified_count:
        print("cockpit_status_paperops_qualified_setup_production_q7_count_exceeds_pt3=true")
        return 1
    qualified_setup_boundary = paperops_qualified_setup_production.get("boundary", "")
    if (
        "guarded qualified setup production path" not in qualified_setup_boundary
        or "cannot mutate the Q7 ledger" not in qualified_setup_boundary
        or "cannot force trades" not in qualified_setup_boundary
    ):
        print("cockpit_status_paperops_qualified_setup_production_boundary_weak=true")
        return 1
    missing_pt4_fields = sorted(
        PAPEROPS_AUTO_APPROVAL_STAGED_ORDER_REQUIRED_FIELDS
        - set(paperops_auto_approval_staged_order)
    )
    if missing_pt4_fields:
        print(
            "cockpit_status_paperops_auto_approval_staged_order_fields_missing="
            + ",".join(missing_pt4_fields)
        )
        return 1
    if paperops_auto_approval_staged_order.get("status") not in {
        "staged_paper_order_ready",
        "ready_no_current_auto_approved_setup",
    }:
        print("cockpit_status_paperops_auto_approval_staged_order_not_ready=true")
        return 1
    if paperops_auto_approval_staged_order.get("public_safe") is not True:
        print("cockpit_status_paperops_auto_approval_staged_order_not_public_safe=true")
        return 1
    if paperops_auto_approval_staged_order.get("recorded") is not True:
        print("cockpit_status_paperops_auto_approval_staged_order_not_recorded=true")
        return 1
    if paperops_auto_approval_staged_order.get("event_log_written") is not True:
        print("cockpit_status_paperops_auto_approval_staged_order_event_log_not_written=true")
        return 1
    if paperops_auto_approval_staged_order.get("event_log_event_count") != 1:
        print("cockpit_status_paperops_auto_approval_staged_order_event_count_mismatch=true")
        return 1
    if paperops_auto_approval_staged_order.get("validation_error_count") != 0:
        print("cockpit_status_paperops_auto_approval_staged_order_validation_errors=true")
        return 1
    if paperops_auto_approval_staged_order.get("source_pt3_path_ready") is not True:
        print("cockpit_status_paperops_auto_approval_staged_order_source_not_ready=true")
        return 1
    if (
        int(paperops_auto_approval_staged_order.get("staged_order_count", 0) or 0)
        < 1
        and not no_current_paperops_setup
    ):
        print("cockpit_status_paperops_auto_approval_staged_order_staged_missing=true")
        return 1
    if (
        paperops_auto_approval_staged_order.get("ready_for_paperops2_submit")
        is not True
        and not no_current_paperops_setup
    ):
        print("cockpit_status_paperops_auto_approval_staged_order_not_ready_for_paperops2=true")
        return 1
    for key in (
        "paper_order_submission_allowed",
        "broker_post_allowed",
        "live_endpoint_allowed",
        "live_capital_enabled",
        "phase7_proof_credit_allowed",
        "forced_trades_allowed",
        "q7_source_ledger_mutation_performed",
        "q7_auto_approval_artifact_mutation_performed",
        "q7_staging_artifact_mutation_performed",
    ):
        if paperops_auto_approval_staged_order.get(key) is not False:
            print(f"cockpit_status_paperops_auto_approval_staged_order_forbidden={key}")
            return 1
    for key in (
        "broker_post_called_count",
        "unsafe_write_counter_total",
    ):
        if int(paperops_auto_approval_staged_order.get(key, 0) or 0) != 0:
            print(f"cockpit_status_paperops_auto_approval_staged_order_unsafe_counter={key}")
            return 1
    pt4_boundary = paperops_auto_approval_staged_order.get("boundary", "")
    if (
        "guarded paper-only auto-approval" not in pt4_boundary
        or "cannot mutate the Q7 source ledger" not in pt4_boundary
        or "cannot force trades" not in pt4_boundary
    ):
        print("cockpit_status_paperops_auto_approval_staged_order_boundary_weak=true")
        return 1
    missing_submit_enablement_fields = sorted(
        PAPEROPS_ALPACA_SUBMIT_ENABLEMENT_REQUIRED_FIELDS
        - set(paperops_alpaca_submit_enablement)
    )
    if missing_submit_enablement_fields:
        print(
            "cockpit_status_paperops_alpaca_submit_enablement_fields_missing="
            + ",".join(missing_submit_enablement_fields)
        )
        return 1
    if (
        paperops_alpaca_submit_enablement.get("status")
        != "enabled_pending_explicit_submit"
        and not no_current_paperops_setup
    ):
        print("cockpit_status_paperops_alpaca_submit_enablement_not_enabled=true")
        return 1
    if paperops_alpaca_submit_enablement.get("public_safe") is not True:
        print("cockpit_status_paperops_alpaca_submit_enablement_not_public_safe=true")
        return 1
    if paperops_alpaca_submit_enablement.get("recorded") is not True:
        print("cockpit_status_paperops_alpaca_submit_enablement_not_recorded=true")
        return 1
    if paperops_alpaca_submit_enablement.get("event_log_written") is not True:
        print("cockpit_status_paperops_alpaca_submit_enablement_event_log_not_written=true")
        return 1
    if paperops_alpaca_submit_enablement.get("event_log_event_count") != 1:
        print("cockpit_status_paperops_alpaca_submit_enablement_event_count_mismatch=true")
        return 1
    if (
        paperops_alpaca_submit_enablement.get("validation_error_count") != 0
        and not no_current_paperops_setup
    ):
        print("cockpit_status_paperops_alpaca_submit_enablement_validation_errors=true")
        return 1
    if (
        paperops_alpaca_submit_enablement.get("alpaca_paper_submit_effective")
        is not True
        and not no_current_paperops_setup
    ):
        print("cockpit_status_paperops_alpaca_submit_enablement_effective_false=true")
        return 1
    if (
        paperops_alpaca_submit_enablement.get("paper_post_path_available") is not True
        and not no_current_paperops_setup
    ):
        print("cockpit_status_paperops_alpaca_submit_enablement_path_unavailable=true")
        return 1
    if (
        int(paperops_alpaca_submit_enablement.get("pt4_staged_order_count", 0) or 0)
        < 1
        and not no_current_paperops_setup
    ):
        print("cockpit_status_paperops_alpaca_submit_enablement_pt4_order_missing=true")
        return 1
    for key in (
        "env_file_edited",
        "live_capital_enabled",
        "phase7_proof_credit_allowed",
        "forced_trades_allowed",
    ):
        if paperops_alpaca_submit_enablement.get(key) is not False:
            print(f"cockpit_status_paperops_alpaca_submit_enablement_forbidden={key}")
            return 1
    for key in (
        "broker_post_called_count",
        "alpaca_post_called_count",
        "live_endpoint_called_count",
        "unsafe_write_counter_total",
    ):
        if int(paperops_alpaca_submit_enablement.get(key, 0) or 0) != 0:
            print(f"cockpit_status_paperops_alpaca_submit_enablement_unsafe_counter={key}")
            return 1
    submit_enablement_boundary = paperops_alpaca_submit_enablement.get("boundary", "")
    if (
        "PT-5 records runtime Alpaca paper-submit enablement"
        not in submit_enablement_boundary
        or "explicit submit flag" not in submit_enablement_boundary
        or "cannot call Alpaca" not in submit_enablement_boundary
        or "cannot enable live capital" not in submit_enablement_boundary
    ):
        print("cockpit_status_paperops_alpaca_submit_enablement_boundary_weak=true")
        return 1
    missing_lifecycle_polling_enablement_fields = sorted(
        PAPEROPS_LIFECYCLE_POLLING_ENABLEMENT_REQUIRED_FIELDS
        - set(paperops_lifecycle_polling_enablement)
    )
    if missing_lifecycle_polling_enablement_fields:
        print(
            "cockpit_status_paperops_lifecycle_polling_enablement_fields_missing="
            + ",".join(missing_lifecycle_polling_enablement_fields)
        )
        return 1
    if (
        paperops_lifecycle_polling_enablement.get("status")
        not in {
            "enabled_pending_submitted_paper_orders",
            "enabled_pending_explicit_poll",
        }
        and not no_current_paperops_setup
    ):
        print("cockpit_status_paperops_lifecycle_polling_enablement_not_enabled=true")
        return 1
    if paperops_lifecycle_polling_enablement.get("public_safe") is not True:
        print("cockpit_status_paperops_lifecycle_polling_enablement_not_public_safe=true")
        return 1
    if paperops_lifecycle_polling_enablement.get("recorded") is not True:
        print("cockpit_status_paperops_lifecycle_polling_enablement_not_recorded=true")
        return 1
    if paperops_lifecycle_polling_enablement.get("event_log_written") is not True:
        print("cockpit_status_paperops_lifecycle_polling_enablement_event_log_not_written=true")
        return 1
    if paperops_lifecycle_polling_enablement.get("event_log_event_count") != 1:
        print("cockpit_status_paperops_lifecycle_polling_enablement_event_count_mismatch=true")
        return 1
    if (
        paperops_lifecycle_polling_enablement.get("validation_error_count") != 0
        and not no_current_paperops_setup
    ):
        print("cockpit_status_paperops_lifecycle_polling_enablement_validation_errors=true")
        return 1
    if (
        paperops_lifecycle_polling_enablement.get("active_lifecycle_polling_enabled")
        is not True
        and not no_current_paperops_setup
    ):
        print("cockpit_status_paperops_lifecycle_polling_enablement_active_false=true")
        return 1
    if (
        paperops_lifecycle_polling_enablement.get("paper_lifecycle_polling_effective")
        is not True
        and not no_current_paperops_setup
    ):
        print("cockpit_status_paperops_lifecycle_polling_enablement_effective_false=true")
        return 1
    if (
        paperops_lifecycle_polling_enablement.get("paper_broker_get_allowed")
        is not True
        and not no_current_paperops_setup
    ):
        print("cockpit_status_paperops_lifecycle_polling_enablement_get_not_allowed=true")
        return 1
    if (
        int(
            paperops_lifecycle_polling_enablement.get(
                "paperops_2_submitted_paper_order_count",
                0,
            )
            or 0
        )
        == 0
        and paperops_lifecycle_polling_enablement.get("paper_poll_path_available")
        is True
    ):
        print("cockpit_status_paperops_lifecycle_polling_path_without_source=true")
        return 1
    for key in (
        "env_file_edited",
        "live_capital_enabled",
        "phase7_proof_credit_allowed",
        "forced_trades_allowed",
        "broker_post_allowed",
    ):
        if paperops_lifecycle_polling_enablement.get(key) is not False:
            print(f"cockpit_status_paperops_lifecycle_polling_enablement_forbidden={key}")
            return 1
    for key in (
        "broker_get_called_count",
        "live_endpoint_called_count",
        "unsafe_write_counter_total",
    ):
        if int(paperops_lifecycle_polling_enablement.get(key, 0) or 0) != 0:
            print(f"cockpit_status_paperops_lifecycle_polling_enablement_unsafe_counter={key}")
            return 1
    lifecycle_polling_boundary = paperops_lifecycle_polling_enablement.get(
        "boundary",
        "",
    )
    if (
        "PT-6 records runtime active Alpaca paper lifecycle polling enablement"
        not in lifecycle_polling_boundary
        or "read-only Alpaca paper GET" not in lifecycle_polling_boundary
        or "cannot submit orders" not in lifecycle_polling_boundary
        or "cannot enable live capital" not in lifecycle_polling_boundary
    ):
        print("cockpit_status_paperops_lifecycle_polling_enablement_boundary_weak=true")
        return 1
    missing_guarded_exit_enablement_fields = sorted(
        PAPEROPS_GUARDED_EXIT_ENABLEMENT_REQUIRED_FIELDS
        - set(paperops_guarded_exit_enablement)
    )
    if missing_guarded_exit_enablement_fields:
        print(
            "cockpit_status_paperops_guarded_exit_enablement_fields_missing="
            + ",".join(missing_guarded_exit_enablement_fields)
        )
        return 1
    if (
        paperops_guarded_exit_enablement.get("status")
        not in {
            "enabled_pending_open_position_readback",
            "enabled_pending_explicit_exit",
        }
        and not no_current_paperops_setup
    ):
        print("cockpit_status_paperops_guarded_exit_enablement_not_enabled=true")
        return 1
    if paperops_guarded_exit_enablement.get("public_safe") is not True:
        print("cockpit_status_paperops_guarded_exit_enablement_not_public_safe=true")
        return 1
    if paperops_guarded_exit_enablement.get("recorded") is not True:
        print("cockpit_status_paperops_guarded_exit_enablement_not_recorded=true")
        return 1
    if paperops_guarded_exit_enablement.get("event_log_written") is not True:
        print("cockpit_status_paperops_guarded_exit_enablement_event_log_not_written=true")
        return 1
    if paperops_guarded_exit_enablement.get("event_log_event_count") != 1:
        print("cockpit_status_paperops_guarded_exit_enablement_event_count_mismatch=true")
        return 1
    if (
        paperops_guarded_exit_enablement.get("validation_error_count") != 0
        and not no_current_paperops_setup
    ):
        print("cockpit_status_paperops_guarded_exit_enablement_validation_errors=true")
        return 1
    if (
        paperops_guarded_exit_enablement.get("guarded_paper_exit_enabled") is not True
        and not no_current_paperops_setup
    ):
        print("cockpit_status_paperops_guarded_exit_enablement_flag_false=true")
        return 1
    if (
        paperops_guarded_exit_enablement.get("alpaca_paper_exit_effective")
        is not True
        and not no_current_paperops_setup
    ):
        print("cockpit_status_paperops_guarded_exit_enablement_effective_false=true")
        return 1
    if (
        int(paperops_guarded_exit_enablement.get("paperops_3_open_position_count", 0) or 0)
        == 0
        and paperops_guarded_exit_enablement.get("paper_exit_path_available") is True
    ):
        print("cockpit_status_paperops_guarded_exit_path_without_open_position=true")
        return 1
    for key in (
        "env_file_edited",
        "live_capital_enabled",
        "phase7_proof_credit_allowed",
        "forced_trades_allowed",
        "broker_post_allowed",
        "position_close_allowed",
    ):
        if paperops_guarded_exit_enablement.get(key) is not False:
            print(f"cockpit_status_paperops_guarded_exit_enablement_forbidden={key}")
            return 1
    for key in (
        "paper_position_close_called_count",
        "live_endpoint_called_count",
        "unsafe_write_counter_total",
    ):
        if int(paperops_guarded_exit_enablement.get(key, 0) or 0) != 0:
            print(f"cockpit_status_paperops_guarded_exit_enablement_unsafe_counter={key}")
            return 1
    guarded_exit_boundary = paperops_guarded_exit_enablement.get("boundary", "")
    if (
        "PT-7 records runtime guarded Alpaca paper-exit enablement"
        not in guarded_exit_boundary
        or "explicit paper-exit flag" not in guarded_exit_boundary
        or "cannot call Alpaca" not in guarded_exit_boundary
        or "cannot enable live capital" not in guarded_exit_boundary
    ):
        print("cockpit_status_paperops_guarded_exit_enablement_boundary_weak=true")
        return 1
    if mission_stack.get("phase5_layer_b") != phase5_readiness.get("status"):
        print("cockpit_status_mission_stack_phase5_mismatch=true")
        return 1
    if mission_stack.get("phase5_kill_switch") != phase5_kill_switch.get("status"):
        print("cockpit_status_mission_stack_phase5_kill_switch_mismatch=true")
        return 1
    if mission_stack.get("phase5_execution_adapter") != phase5_execution_adapter.get("status"):
        print("cockpit_status_mission_stack_phase5_execution_adapter_mismatch=true")
        return 1
    if mission_stack.get("phase5_paper_order_staging") != phase5_paper_order_staging.get("status"):
        print("cockpit_status_mission_stack_phase5_paper_order_staging_mismatch=true")
        return 1
    if mission_stack.get("phase5_alpaca_paper_dry_run") != phase5_alpaca_dry_run.get("status"):
        print("cockpit_status_mission_stack_phase5_alpaca_paper_dry_run_mismatch=true")
        return 1
    if mission_stack.get("phase5_paper_submit_enablement") != phase5_paper_submit_enablement.get("status"):
        print("cockpit_status_mission_stack_phase5_paper_submit_enablement_mismatch=true")
        return 1
    if mission_stack.get("phase5_prediction_market_adapter") != phase5_prediction_market_adapter.get("status"):
        print("cockpit_status_mission_stack_phase5_prediction_market_adapter_mismatch=true")
        return 1
    if mission_stack.get("phase5_telegram_notifier") != phase5_telegram_notifier.get("status"):
        print("cockpit_status_mission_stack_phase5_telegram_notifier_mismatch=true")
        return 1
    if mission_stack.get("phase5_position_monitor") != phase5_position_monitor.get("status"):
        print("cockpit_status_mission_stack_phase5_position_monitor_mismatch=true")
        return 1
    if mission_stack.get("phase5_signal_review") != phase5_signal_review.get("status"):
        print("cockpit_status_mission_stack_phase5_signal_review_mismatch=true")
        return 1
    if mission_stack.get("phase5_paper_trade_drill") != phase5_paper_trade_drill.get("status"):
        print("cockpit_status_mission_stack_phase5_paper_trade_drill_mismatch=true")
        return 1
    if mission_stack.get("phase5_certification") != phase5_certification.get("status"):
        print("cockpit_status_mission_stack_phase5_certification_mismatch=true")
        return 1
    if mission_stack.get("phase5_phase6_handoff") != phase5_phase6_handoff.get("status"):
        print("cockpit_status_mission_stack_phase5_phase6_handoff_mismatch=true")
        return 1
    if mission_stack.get("phase5_system_map") != phase5_system_map.get("status"):
        print("cockpit_status_mission_stack_phase5_system_map_mismatch=true")
        return 1
    if mission_stack.get("phase6_learning_loop") != phase6_learning_loop.get("status"):
        print("cockpit_status_mission_stack_phase6_learning_loop_mismatch=true")
        return 1
    if mission_stack.get("rs9_learning_loop") != rs9_learning_loop.get("status"):
        print("cockpit_status_mission_stack_rs9_learning_loop_mismatch=true")
        return 1
    if mission_stack.get("rs9_learning_direction") != rs9_learning_loop.get("learning_direction"):
        print("cockpit_status_mission_stack_rs9_direction_mismatch=true")
        return 1
    if mission_stack.get("rs9_learning_proposal_count") != rs9_learning_loop.get("proposal_count"):
        print("cockpit_status_mission_stack_rs9_proposal_count_mismatch=true")
        return 1
    if mission_stack.get("rs9_learning_blocked_proposal_count") != rs9_learning_loop.get(
        "blocked_proposal_count"
    ):
        print("cockpit_status_mission_stack_rs9_blocked_proposal_count_mismatch=true")
        return 1
    if (
        mission_stack.get("rs9_paperops_guarded_paper_trading_not_blocked")
        != rs9_learning_loop.get("paperops_guarded_paper_trading_not_blocked")
    ):
        print("cockpit_status_mission_stack_rs9_guarded_paperops_mismatch=true")
        return 1
    if (
        mission_stack.get("rs10_final_paper_autonomy_certification")
        != rs10_final_paper_autonomy.get("status")
    ):
        print("cockpit_status_mission_stack_rs10_status_mismatch=true")
        return 1
    if (
        mission_stack.get("rs10_final_paper_autonomy_certified")
        != rs10_final_paper_autonomy.get("final_paper_autonomy_certified")
    ):
        print("cockpit_status_mission_stack_rs10_certification_mismatch=true")
        return 1
    if (
        mission_stack.get("rs10_guarded_paper_autonomy_allowed")
        != rs10_final_paper_autonomy.get("guarded_paper_autonomy_allowed")
    ):
        print("cockpit_status_mission_stack_rs10_guarded_autonomy_mismatch=true")
        return 1
    if (
        mission_stack.get("rs10_autonomy_currently_actionable")
        != rs10_final_paper_autonomy.get("autonomy_currently_actionable")
    ):
        print("cockpit_status_mission_stack_rs10_actionable_mismatch=true")
        return 1
    if (
        mission_stack.get("rs10_current_blocker_count")
        != rs10_final_paper_autonomy.get("current_blocker_count")
    ):
        print("cockpit_status_mission_stack_rs10_current_blocker_mismatch=true")
        return 1
    if (
        mission_stack.get("rs10_certification_blocker_count")
        != rs10_final_paper_autonomy.get("certification_blocker_count")
    ):
        print("cockpit_status_mission_stack_rs10_certification_blocker_mismatch=true")
        return 1
    if (
        mission_stack.get("rs10_paper_submit_currently_allowed")
        != rs10_final_paper_autonomy.get("paper_submit_currently_allowed")
    ):
        print("cockpit_status_mission_stack_rs10_submit_allowed_mismatch=true")
        return 1
    if (
        mission_stack.get("rs10_multiple_paper_trades_per_day_allowed_when_gates_pass")
        != rs10_final_paper_autonomy.get(
            "multiple_paper_trades_per_day_allowed_when_gates_pass"
        )
    ):
        print("cockpit_status_mission_stack_rs10_multiple_trade_policy_mismatch=true")
        return 1
    mission_phase6 = mission.get("phase6_learning_loop", {})
    missing_mission_phase6_fields = sorted(
        MISSION_PHASE6_LEARNING_LOOP_REQUIRED_FIELDS - set(mission_phase6)
    )
    if missing_mission_phase6_fields:
        print("cockpit_status_mission_phase6_fields_missing=" + ",".join(missing_mission_phase6_fields))
        return 1
    if mission_phase6.get("phase") != "Q6" or mission_phase6.get("stage") != "Q6-16":
        print("cockpit_status_mission_phase6_phase_or_stage_mismatch=true")
        return 1
    if mission_phase6.get("status") != phase6_learning_loop.get("status"):
        print("cockpit_status_mission_phase6_status_mismatch=true")
        return 1
    if mission_phase6.get("learning_state") != phase6_learning_loop.get("learning_state"):
        print("cockpit_status_mission_phase6_learning_state_mismatch=true")
        return 1
    if mission_phase6.get("backend_derived") is not True:
        print("cockpit_status_mission_phase6_not_backend_derived=true")
        return 1
    if mission_phase6.get("ui_inferred_readiness_count") != 0:
        print("cockpit_status_mission_phase6_ui_inferred=true")
        return 1
    if mission_phase6.get("backend_parity_error_count") != 0:
        print("cockpit_status_mission_phase6_parity_errors=true")
        return 1
    if mission_phase6.get("postmortem_due_count") != phase6_learning_loop.get("postmortem_due_count"):
        print("cockpit_status_mission_phase6_postmortem_mismatch=true")
        return 1
    if mission_phase6.get("approval_state") != phase6_learning_loop.get("approval_state"):
        print("cockpit_status_mission_phase6_approval_mismatch=true")
        return 1
    if mission_phase6.get("model_weight_proposal_count") != phase6_learning_loop.get("model_weight_proposal_count"):
        print("cockpit_status_mission_phase6_model_proposal_mismatch=true")
        return 1
    if mission_phase6.get("trust_score_proposal_count") != phase6_learning_loop.get("trust_score_proposal_count"):
        print("cockpit_status_mission_phase6_trust_proposal_mismatch=true")
        return 1
    if mission_phase6.get("blocked_authority_count") != phase6_learning_loop.get("blocked_authority_count"):
        print("cockpit_status_mission_phase6_blocked_authority_mismatch=true")
        return 1
    for key in (
        "phase6_learning_write_allowed",
        "phase6_knowledge_graph_write_allowed",
        "phase6_model_weight_update_allowed",
        "phase6_trust_score_update_allowed",
        "phase6_architect_policy_mutation_allowed",
        "phase7_proof_credit_allowed",
        "live_capital_enabled",
    ):
        if mission_phase6.get(key) is not False:
            print(f"cockpit_status_mission_phase6_authority_enabled={key}")
            return 1
    if mission_phase6.get("unsafe_write_counter_total") != 0:
        print("cockpit_status_mission_phase6_unsafe_writes=true")
        return 1
    mission_rs9 = mission.get("rs9_learning_loop", {})
    missing_mission_rs9_fields = sorted(
        MISSION_RS9_LEARNING_LOOP_REQUIRED_FIELDS - set(mission_rs9)
    )
    if missing_mission_rs9_fields:
        print("cockpit_status_mission_rs9_fields_missing=" + ",".join(missing_mission_rs9_fields))
        return 1
    if mission_rs9.get("phase") != "RS" or mission_rs9.get("stage") != "RS-9":
        print("cockpit_status_mission_rs9_phase_or_stage_mismatch=true")
        return 1
    if mission_rs9.get("status") != rs9_learning_loop.get("status"):
        print("cockpit_status_mission_rs9_status_mismatch=true")
        return 1
    if mission_rs9.get("learning_direction") != rs9_learning_loop.get("learning_direction"):
        print("cockpit_status_mission_rs9_direction_mismatch=true")
        return 1
    if mission_rs9.get("full_potential_state") != rs9_learning_loop.get("full_potential_state"):
        print("cockpit_status_mission_rs9_full_potential_mismatch=true")
        return 1
    if mission_rs9.get("proposal_count") != rs9_learning_loop.get("proposal_count"):
        print("cockpit_status_mission_rs9_proposal_count_mismatch=true")
        return 1
    if mission_rs9.get("blocked_proposal_count") != rs9_learning_loop.get("blocked_proposal_count"):
        print("cockpit_status_mission_rs9_blocked_proposal_count_mismatch=true")
        return 1
    if (
        mission_rs9.get("paperops_guarded_paper_trading_not_blocked")
        is not True
    ):
        print("cockpit_status_mission_rs9_blocks_guarded_paperops=true")
        return 1
    for key in (
        "strategy_weight_proposal_count",
        "source_trust_proposal_count",
        "risk_sizing_proposal_count",
        "market_context_proposal_count",
        "worldview_lens_proposal_count",
    ):
        if mission_rs9.get(key) != rs9_learning_loop.get(key):
            print(f"cockpit_status_mission_rs9_surface_count_mismatch={key}")
            return 1
    for key in (
        "strategy_weight_mutation_allowed",
        "source_trust_mutation_allowed",
        "risk_sizing_mutation_allowed",
        "market_context_interpretation_mutation_allowed",
        "worldview_lens_strength_mutation_allowed",
        "dashboard_command_authority",
        "telegram_command_authority",
        "broker_write_allowed",
        "live_capital_enabled",
        "phase7_proof_credit_allowed",
    ):
        if mission_rs9.get(key) is not False:
            print(f"cockpit_status_mission_rs9_authority_enabled={key}")
            return 1
    for key in (
        "unsafe_write_counter_total",
        "raw_payload_exposed_count",
        "local_path_exposed_count",
        "secret_ref_exposed_count",
        "broker_identifier_exposed_count",
    ):
        if mission_rs9.get(key) != 0:
            print(f"cockpit_status_mission_rs9_exposure_nonzero={key}")
            return 1
    mission_rs9_boundary = mission_rs9.get("boundary", "")
    if (
        "cannot silently rewrite strategy" not in mission_rs9_boundary
        or "cannot apply source trust" not in mission_rs9_boundary
        or "cannot change risk sizing" not in mission_rs9_boundary
        or "cannot mutate worldview lens strength" not in mission_rs9_boundary
        or "cannot create orders" not in mission_rs9_boundary
        or "cannot enable live capital" not in mission_rs9_boundary
        or "cannot give dashboard or Telegram command authority" not in mission_rs9_boundary
    ):
        print("cockpit_status_mission_rs9_boundary_weak=true")
        return 1
    mission_rs10 = mission.get("rs10_final_paper_autonomy_certification", {})
    missing_mission_rs10_fields = sorted(
        MISSION_RS10_FINAL_PAPER_AUTONOMY_REQUIRED_FIELDS - set(mission_rs10)
    )
    if missing_mission_rs10_fields:
        print("cockpit_status_mission_rs10_fields_missing=" + ",".join(missing_mission_rs10_fields))
        return 1
    if mission_rs10.get("phase") != "RS" or mission_rs10.get("stage") != "RS-10":
        print("cockpit_status_mission_rs10_phase_or_stage_mismatch=true")
        return 1
    for key in (
        "status",
        "final_paper_autonomy_certified",
        "guarded_paper_autonomy_allowed",
        "autonomy_currently_actionable",
        "multiple_paper_trades_per_day_allowed_when_gates_pass",
        "paper_submit_currently_allowed",
        "current_blocker_count",
        "certification_blocker_count",
        "safety_blocker_count",
        "why_not_trading_now",
        "next_action",
    ):
        if mission_rs10.get(key) != rs10_final_paper_autonomy.get(key):
            print(f"cockpit_status_mission_rs10_mismatch={key}")
            return 1
    if mission_rs10.get("current_blockers") != rs10_final_paper_autonomy.get(
        "current_blockers"
    ):
        print("cockpit_status_mission_rs10_current_blockers_mismatch=true")
        return 1
    mission_rs10_boundary = mission_rs10.get("boundary", "")
    if (
        "guarded paper autonomy only" not in mission_rs10_boundary
        or "cannot submit without PaperOps gates" not in mission_rs10_boundary
        or "cannot enable live capital" not in mission_rs10_boundary
    ):
        print("cockpit_status_mission_rs10_boundary_weak=true")
        return 1
    mission_phase5 = mission.get("phase5_layer_b", {})
    missing_mission_phase5_fields = sorted(
        MISSION_PHASE5_LAYER_B_REQUIRED_FIELDS - set(mission_phase5)
    )
    if missing_mission_phase5_fields:
        print("cockpit_status_mission_phase5_fields_missing=" + ",".join(missing_mission_phase5_fields))
        return 1
    if mission_phase5.get("phase") != "Q5" or mission_phase5.get("layer") != "Layer B":
        print("cockpit_status_mission_phase5_phase_or_layer_mismatch=true")
        return 1
    if mission_phase5.get("status") != phase5_readiness.get("status"):
        print("cockpit_status_mission_phase5_status_mismatch=true")
        return 1
    if mission_phase5.get("implementation_plan_allowed") is not True:
        print("cockpit_status_mission_phase5_plan_not_allowed=true")
        return 1
    if mission_phase5.get("implementation_allowed") is not phase5_implementation_allowed:
        print("cockpit_status_mission_phase5_implementation_allowed_mismatch=true")
        return 1
    if mission_phase5.get("kill_switch_status") != phase5_kill_switch.get("status"):
        print("cockpit_status_mission_phase5_kill_switch_status_mismatch=true")
        return 1
    if mission_phase5.get("kill_switch_count") != phase5_kill_switch.get("switch_count"):
        print("cockpit_status_mission_phase5_kill_switch_count_mismatch=true")
        return 1
    if mission_phase5.get("kill_switch_active_count") != phase5_kill_switch.get(
        "active_switch_count"
    ):
        print("cockpit_status_mission_phase5_kill_switch_active_count_mismatch=true")
        return 1
    if mission_phase5.get("kill_switch_blocking_count") != phase5_kill_switch.get(
        "blocking_switch_count"
    ):
        print("cockpit_status_mission_phase5_kill_switch_blocking_count_mismatch=true")
        return 1
    if mission_phase5.get("kill_switch_event_log_written") is not True:
        print("cockpit_status_mission_phase5_kill_switch_event_log_not_written=true")
        return 1
    if mission_phase5.get("execution_adapter_status") != phase5_execution_adapter.get("status"):
        print("cockpit_status_mission_phase5_execution_adapter_status_mismatch=true")
        return 1
    if mission_phase5.get("execution_adapter_count") != phase5_execution_adapter.get(
        "adapter_status_count"
    ):
        print("cockpit_status_mission_phase5_execution_adapter_count_mismatch=true")
        return 1
    if mission_phase5.get("execution_adapter_read_allowed_count") != phase5_execution_adapter.get(
        "read_allowed_count"
    ):
        print("cockpit_status_mission_phase5_execution_adapter_read_count_mismatch=true")
        return 1
    if mission_phase5.get("execution_adapter_staging_allowed_count") != phase5_execution_adapter.get(
        "downstream_staging_allowed_count"
    ):
        print("cockpit_status_mission_phase5_execution_adapter_staging_count_mismatch=true")
        return 1
    if mission_phase5.get("paper_order_staging_status") != phase5_paper_order_staging.get("status"):
        print("cockpit_status_mission_phase5_paper_order_staging_status_mismatch=true")
        return 1
    if mission_phase5.get("paper_order_staging_record_count") != phase5_paper_order_staging.get(
        "staging_record_count"
    ):
        print("cockpit_status_mission_phase5_paper_order_staging_record_count_mismatch=true")
        return 1
    if mission_phase5.get("paper_order_staged_count") != phase5_paper_order_staging.get(
        "staged_order_count"
    ):
        print("cockpit_status_mission_phase5_paper_order_staged_count_mismatch=true")
        return 1
    if mission_phase5.get("paper_order_staging_blocked_count") != phase5_paper_order_staging.get(
        "blocked_count"
    ):
        print("cockpit_status_mission_phase5_paper_order_staging_blocked_count_mismatch=true")
        return 1
    if mission_phase5.get("paper_order_staging_event_log_written") is not True:
        print("cockpit_status_mission_phase5_paper_order_staging_event_log_not_written=true")
        return 1
    if mission_phase5.get("alpaca_paper_dry_run_status") != phase5_alpaca_dry_run.get("status"):
        print("cockpit_status_mission_phase5_alpaca_dry_run_status_mismatch=true")
        return 1
    if mission_phase5.get("alpaca_paper_dry_run_record_count") != phase5_alpaca_dry_run.get(
        "dry_run_record_count"
    ):
        print("cockpit_status_mission_phase5_alpaca_dry_run_record_count_mismatch=true")
        return 1
    if mission_phase5.get("alpaca_paper_dry_run_request_preview_count") != phase5_alpaca_dry_run.get(
        "request_preview_count"
    ):
        print("cockpit_status_mission_phase5_alpaca_dry_run_preview_count_mismatch=true")
        return 1
    if mission_phase5.get("alpaca_paper_dry_run_receipt_count") != phase5_alpaca_dry_run.get(
        "dry_run_receipt_count"
    ):
        print("cockpit_status_mission_phase5_alpaca_dry_run_receipt_count_mismatch=true")
        return 1
    if mission_phase5.get("alpaca_paper_dry_run_blocked_count") != phase5_alpaca_dry_run.get(
        "blocked_count"
    ):
        print("cockpit_status_mission_phase5_alpaca_dry_run_blocked_count_mismatch=true")
        return 1
    if mission_phase5.get("alpaca_paper_dry_run_event_log_written") is not True:
        print("cockpit_status_mission_phase5_alpaca_dry_run_event_log_not_written=true")
        return 1
    if mission_phase5.get("alpaca_paper_dry_run_broker_post_called") is not False:
        print("cockpit_status_mission_phase5_alpaca_dry_run_broker_post_called=true")
        return 1
    if mission_phase5.get("paper_submit_enablement_status") != phase5_paper_submit_enablement.get("status"):
        print("cockpit_status_mission_phase5_paper_submit_enablement_status_mismatch=true")
        return 1
    if mission_phase5.get("paper_submit_enablement_record_count") != phase5_paper_submit_enablement.get(
        "submit_enablement_record_count"
    ):
        print("cockpit_status_mission_phase5_paper_submit_enablement_record_count_mismatch=true")
        return 1
    if mission_phase5.get("paper_submit_path_available_count") != phase5_paper_submit_enablement.get(
        "submit_path_available_count"
    ):
        print("cockpit_status_mission_phase5_paper_submit_path_count_mismatch=true")
        return 1
    if mission_phase5.get("paper_submit_approval_state") != phase5_paper_submit_enablement.get(
        "paper_submit_approval_state"
    ):
        print("cockpit_status_mission_phase5_paper_submit_approval_state_mismatch=true")
        return 1
    if mission_phase5.get("paper_submit_approval_present") != (
        phase5_paper_submit_enablement.get("paper_submit_approval_present") is True
    ):
        print("cockpit_status_mission_phase5_paper_submit_approval_present_mismatch=true")
        return 1
    if mission_phase5.get("paper_submit_event_log_written") is not True:
        print("cockpit_status_mission_phase5_paper_submit_event_log_not_written=true")
        return 1
    if mission_phase5.get("paper_submit_broker_post_called") is not False:
        print("cockpit_status_mission_phase5_paper_submit_broker_post_called=true")
        return 1
    if mission_phase5.get("prediction_market_adapter_status") != phase5_prediction_market_adapter.get("status"):
        print("cockpit_status_mission_phase5_prediction_market_adapter_status_mismatch=true")
        return 1
    if mission_phase5.get("prediction_market_route_count") != phase5_prediction_market_adapter.get(
        "prediction_market_route_count"
    ):
        print("cockpit_status_mission_phase5_prediction_market_route_count_mismatch=true")
        return 1
    if mission_phase5.get("prediction_market_context_count") != phase5_prediction_market_adapter.get(
        "prediction_market_context_count"
    ):
        print("cockpit_status_mission_phase5_prediction_market_context_count_mismatch=true")
        return 1
    if mission_phase5.get("prediction_market_read_only_route_count") != phase5_prediction_market_adapter.get(
        "read_only_route_count"
    ):
        print("cockpit_status_mission_phase5_prediction_market_read_only_count_mismatch=true")
        return 1
    if mission_phase5.get("prediction_market_live_blocked_route_count") != phase5_prediction_market_adapter.get(
        "live_blocked_count"
    ):
        print("cockpit_status_mission_phase5_prediction_market_live_blocked_count_mismatch=true")
        return 1
    if mission_phase5.get("prediction_market_write_allowed_count") != 0:
        print("cockpit_status_mission_phase5_prediction_market_write_allowed=true")
        return 1
    if mission_phase5.get("prediction_market_spend_allowed_count") != 0:
        print("cockpit_status_mission_phase5_prediction_market_spend_allowed=true")
        return 1
    if mission_phase5.get(
        "prediction_market_preference_provenance_status"
    ) != phase5_prediction_market_adapter.get("preference_provenance_status"):
        print("cockpit_status_mission_phase5_prediction_market_provenance_mismatch=true")
        return 1
    if mission_phase5.get("prediction_market_preference_source_quorum_credit_allowed") is not False:
        print("cockpit_status_mission_phase5_prediction_market_source_quorum_credit=true")
        return 1
    if mission_phase5.get("prediction_market_event_log_written") is not True:
        print("cockpit_status_mission_phase5_prediction_market_event_log_not_written=true")
        return 1
    if mission_phase5.get("telegram_notifier_status") != phase5_telegram_notifier.get("status"):
        print("cockpit_status_mission_phase5_telegram_notifier_status_mismatch=true")
        return 1
    if mission_phase5.get("telegram_notifier_alert_type_count") != phase5_telegram_notifier.get(
        "alert_type_count"
    ):
        print("cockpit_status_mission_phase5_telegram_notifier_alert_count_mismatch=true")
        return 1
    if mission_phase5.get("telegram_notifier_eligible_alert_count") != phase5_telegram_notifier.get(
        "eligible_alert_count"
    ):
        print("cockpit_status_mission_phase5_telegram_notifier_eligible_count_mismatch=true")
        return 1
    if mission_phase5.get("telegram_notifier_queued_count") != phase5_telegram_notifier.get(
        "queued_dry_run_alert_count"
    ):
        print("cockpit_status_mission_phase5_telegram_notifier_queued_count_mismatch=true")
        return 1
    if mission_phase5.get("telegram_notifier_outbox_written_count") != phase5_telegram_notifier.get(
        "outbox_message_written_count"
    ):
        print("cockpit_status_mission_phase5_telegram_notifier_outbox_count_mismatch=true")
        return 1
    if mission_phase5.get("telegram_notifier_suppressed_count") != phase5_telegram_notifier.get(
        "suppressed_alert_count"
    ):
        print("cockpit_status_mission_phase5_telegram_notifier_suppressed_count_mismatch=true")
        return 1
    if mission_phase5.get("telegram_notifier_send_gate") != "disabled":
        print("cockpit_status_mission_phase5_telegram_notifier_send_gate_enabled=true")
        return 1
    if mission_phase5.get("telegram_notifier_mode") != "dry_run":
        print("cockpit_status_mission_phase5_telegram_notifier_not_dry_run=true")
        return 1
    if mission_phase5.get("telegram_notifier_command_path_enabled_count") != 0:
        print("cockpit_status_mission_phase5_telegram_notifier_command_path_enabled=true")
        return 1
    if mission_phase5.get("telegram_notifier_live_send_allowed_count") != 0:
        print("cockpit_status_mission_phase5_telegram_notifier_live_send_allowed=true")
        return 1
    if mission_phase5.get("telegram_notifier_event_log_written") is not True:
        print("cockpit_status_mission_phase5_telegram_notifier_event_log_not_written=true")
        return 1
    if mission_phase5.get("position_monitor_status") != phase5_position_monitor.get("status"):
        print("cockpit_status_mission_phase5_position_monitor_status_mismatch=true")
        return 1
    if mission_phase5.get("position_monitor_record_count") != phase5_position_monitor.get(
        "monitor_record_count"
    ):
        print("cockpit_status_mission_phase5_position_monitor_record_count_mismatch=true")
        return 1
    if mission_phase5.get(
        "position_monitor_position_record_count"
    ) != phase5_position_monitor.get("position_record_count"):
        print("cockpit_status_mission_phase5_position_record_count_mismatch=true")
        return 1
    if mission_phase5.get(
        "position_monitor_closed_trade_summary_count"
    ) != phase5_position_monitor.get("closed_trade_summary_count"):
        print("cockpit_status_mission_phase5_closed_trade_summary_count_mismatch=true")
        return 1
    if mission_phase5.get("position_monitor_open_position_count") != phase5_position_monitor.get(
        "open_position_count"
    ):
        print("cockpit_status_mission_phase5_position_monitor_open_position_mismatch=true")
        return 1
    if mission_phase5.get("position_monitor_closed_trade_count") != phase5_position_monitor.get(
        "closed_trade_count"
    ):
        print("cockpit_status_mission_phase5_position_monitor_closed_trade_mismatch=true")
        return 1
    if mission_phase5.get("position_monitor_failed_reconciliation_count") != 0:
        print("cockpit_status_mission_phase5_position_monitor_reconciliation_failures=true")
        return 1
    if mission_phase5.get("position_monitor_event_log_written") is not True:
        print("cockpit_status_mission_phase5_position_monitor_event_log_not_written=true")
        return 1
    if mission_phase5.get("position_monitor_write_authority_count") != 0:
        print("cockpit_status_mission_phase5_position_monitor_write_authority=true")
        return 1
    if mission_phase5.get("position_monitor_close_allowed_count") != 0:
        print("cockpit_status_mission_phase5_position_monitor_close_allowed=true")
        return 1
    if mission_phase5.get("position_monitor_resize_allowed_count") != 0:
        print("cockpit_status_mission_phase5_position_monitor_resize_allowed=true")
        return 1
    if mission_phase5.get("position_monitor_cancel_allowed_count") != 0:
        print("cockpit_status_mission_phase5_position_monitor_cancel_allowed=true")
        return 1
    if mission_phase5.get("signal_review_status") != phase5_signal_review.get("status"):
        print("cockpit_status_mission_phase5_signal_review_status_mismatch=true")
        return 1
    if mission_phase5.get("signal_review_record_count") != phase5_signal_review.get(
        "signal_review_record_count"
    ):
        print("cockpit_status_mission_phase5_signal_review_record_count_mismatch=true")
        return 1
    if mission_phase5.get("signal_review_decision_chain_count") != phase5_signal_review.get(
        "decision_chain_count"
    ):
        print("cockpit_status_mission_phase5_signal_review_chain_count_mismatch=true")
        return 1
    if mission_phase5.get(
        "signal_review_governance_comment_event_count"
    ) != phase5_signal_review.get("governance_comment_event_count"):
        print("cockpit_status_mission_phase5_signal_review_comment_count_mismatch=true")
        return 1
    if mission_phase5.get(
        "signal_review_kill_switch_action_event_count"
    ) != phase5_signal_review.get("kill_switch_action_event_count"):
        print("cockpit_status_mission_phase5_signal_review_kill_action_count_mismatch=true")
        return 1
    if mission_phase5.get(
        "signal_review_backend_truth_displayed_count"
    ) != phase5_signal_review.get("backend_truth_displayed_count"):
        print("cockpit_status_mission_phase5_signal_review_truth_count_mismatch=true")
        return 1
    if mission_phase5.get("signal_review_ui_inferred_readiness_count") != 0:
        print("cockpit_status_mission_phase5_signal_review_inferred_readiness=true")
        return 1
    if mission_phase5.get("signal_review_event_log_written") is not True:
        print("cockpit_status_mission_phase5_signal_review_event_log_not_written=true")
        return 1
    for key in (
        "signal_review_trade_approval_control_count",
        "signal_review_order_place_control_count",
        "signal_review_position_close_control_count",
        "signal_review_position_resize_control_count",
        "signal_review_order_cancel_control_count",
        "signal_review_broker_write_allowed_count",
        "signal_review_prediction_market_write_allowed_count",
        "signal_review_live_capital_enabled_count",
    ):
        if mission_phase5.get(key) != 0:
            print(f"cockpit_status_mission_phase5_{key}_nonzero=true")
            return 1
    if mission_phase5.get("paper_trade_drill_status") != phase5_paper_trade_drill.get("status"):
        print("cockpit_status_mission_phase5_paper_trade_drill_status_mismatch=true")
        return 1
    if mission_phase5.get("paper_trade_drill_state") != phase5_paper_trade_drill.get(
        "paper_trade_drill_state"
    ):
        print("cockpit_status_mission_phase5_paper_trade_drill_state_mismatch=true")
        return 1
    if mission_phase5.get("paper_trade_drill_step_count") != phase5_paper_trade_drill.get(
        "step_count"
    ):
        print("cockpit_status_mission_phase5_paper_trade_drill_step_count_mismatch=true")
        return 1
    if mission_phase5.get("paper_trade_drill_blocker_count") != phase5_paper_trade_drill.get(
        "blocker_count"
    ):
        print("cockpit_status_mission_phase5_paper_trade_drill_blocker_count_mismatch=true")
        return 1
    if mission_phase5.get("paper_trade_drill_complete") != phase5_paper_trade_drill.get(
        "paper_trade_drill_complete"
    ):
        print("cockpit_status_mission_phase5_paper_trade_drill_complete_mismatch=true")
        return 1
    if mission_phase5.get("paper_trade_drill_exit_gate_passed") != phase5_paper_trade_drill.get(
        "phase5_paper_trade_drill_exit_gate_passed"
    ):
        print("cockpit_status_mission_phase5_paper_trade_drill_exit_gate_mismatch=true")
        return 1
    if mission_phase5.get("paper_trade_drill_implementation_ready") is not True:
        print("cockpit_status_mission_phase5_paper_trade_drill_not_ready=true")
        return 1
    if (
        mission_phase5.get("paper_trade_drill_submit_approval_present")
        != phase5_paper_trade_drill.get("paper_submit_approval_present")
    ):
        print("cockpit_status_mission_phase5_paper_trade_drill_approval_mismatch=true")
        return 1
    if mission_phase5.get("paper_trade_drill_open_position_count") != phase5_paper_trade_drill.get(
        "open_position_count"
    ):
        print("cockpit_status_mission_phase5_paper_trade_drill_open_position_mismatch=true")
        return 1
    if mission_phase5.get("paper_trade_drill_closed_trade_count") != phase5_paper_trade_drill.get(
        "closed_trade_count"
    ):
        print("cockpit_status_mission_phase5_paper_trade_drill_closed_trade_mismatch=true")
        return 1
    if mission_phase5.get("paper_trade_drill_postmortem_due_count") != phase5_paper_trade_drill.get(
        "postmortem_due_count"
    ):
        print("cockpit_status_mission_phase5_paper_trade_drill_postmortem_due_mismatch=true")
        return 1
    if mission_phase5.get("paper_trade_drill_broker_post_called_count") != 0:
        print("cockpit_status_mission_phase5_paper_trade_drill_broker_post_called=true")
        return 1
    if mission_phase5.get("paper_trade_drill_live_capital_enabled_count") != 0:
        print("cockpit_status_mission_phase5_paper_trade_drill_live_capital_enabled=true")
        return 1
    if mission_phase5.get("certification_status") != phase5_certification.get("status"):
        print("cockpit_status_mission_phase5_certification_status_mismatch=true")
        return 1
    if mission_phase5.get("certification_stage_status") != phase5_certification.get(
        "stage_status"
    ):
        print("cockpit_status_mission_phase5_certification_stage_status_mismatch=true")
        return 1
    if mission_phase5.get("certification_phase5_certified") != phase5_certification.get(
        "phase5_certified"
    ):
        print("cockpit_status_mission_phase5_certification_certified_mismatch=true")
        return 1
    if mission_phase5.get("certification_phase5_exit_gate") != phase5_certification.get(
        "phase5_exit_gate"
    ):
        print("cockpit_status_mission_phase5_certification_exit_gate_mismatch=true")
        return 1
    if mission_phase5.get("certification_phase6_handoff_allowed") != phase5_certification.get(
        "phase6_handoff_allowed"
    ):
        print("cockpit_status_mission_phase5_certification_phase6_handoff_mismatch=true")
        return 1
    if mission_phase5.get("certification_phase7_planning_allowed") != phase5_certification.get(
        "phase7_planning_allowed"
    ):
        print("cockpit_status_mission_phase5_certification_phase7_planning_mismatch=true")
        return 1
    if mission_phase5.get("certification_phase7_proof_credit_allowed") is not False:
        print("cockpit_status_mission_phase5_certification_phase7_credit=true")
        return 1
    if mission_phase5.get("certification_input_gate_count") != phase5_certification.get(
        "input_gate_count"
    ):
        print("cockpit_status_mission_phase5_certification_gate_count_mismatch=true")
        return 1
    if mission_phase5.get("certification_input_gate_passed_count") != phase5_certification.get(
        "input_gate_passed_count"
    ):
        print("cockpit_status_mission_phase5_certification_passed_count_mismatch=true")
        return 1
    if mission_phase5.get("certification_input_gate_blocked_count") != phase5_certification.get(
        "input_gate_blocked_count"
    ):
        print("cockpit_status_mission_phase5_certification_blocked_count_mismatch=true")
        return 1
    if mission_phase5.get("certification_blocker_count") != phase5_certification.get(
        "certification_blocker_count"
    ):
        print("cockpit_status_mission_phase5_certification_blocker_count_mismatch=true")
        return 1
    if mission_phase5.get("certification_paper_trade_drill_complete") != phase5_certification.get(
        "paper_trade_drill_complete"
    ):
        print("cockpit_status_mission_phase5_certification_drill_complete_mismatch=true")
        return 1
    if mission_phase5.get(
        "certification_paper_trade_drill_exit_gate_passed"
    ) != phase5_certification.get("paper_trade_drill_exit_gate_passed"):
        print("cockpit_status_mission_phase5_certification_drill_exit_gate_mismatch=true")
        return 1
    if mission_phase5.get("certification_submitted_paper_order_count") != phase5_certification.get(
        "submitted_paper_order_count"
    ):
        print("cockpit_status_mission_phase5_certification_submitted_order_mismatch=true")
        return 1
    if mission_phase5.get("certification_open_position_count") != phase5_certification.get(
        "open_position_count"
    ):
        print("cockpit_status_mission_phase5_certification_open_position_mismatch=true")
        return 1
    if mission_phase5.get("certification_closed_trade_count") != phase5_certification.get(
        "closed_trade_count"
    ):
        print("cockpit_status_mission_phase5_certification_closed_trade_mismatch=true")
        return 1
    if mission_phase5.get("certification_live_capital_enabled_count") != 0:
        print("cockpit_status_mission_phase5_certification_live_capital=true")
        return 1
    if mission_phase5.get("phase6_handoff_status") != phase5_phase6_handoff.get("status"):
        print("cockpit_status_mission_phase5_phase6_handoff_status_mismatch=true")
        return 1
    if mission_phase5.get("phase6_handoff_state") != phase5_phase6_handoff.get(
        "handoff_state"
    ):
        print("cockpit_status_mission_phase5_phase6_handoff_state_mismatch=true")
        return 1
    if mission_phase5.get("phase6_handoff_blocker_count") != phase5_phase6_handoff.get(
        "blocker_count"
    ):
        print("cockpit_status_mission_phase5_phase6_handoff_blocker_mismatch=true")
        return 1
    if mission_phase5.get("phase6_handoff_event_log_written") != (
        phase5_phase6_handoff.get("event_log_written") is True
    ):
        print("cockpit_status_mission_phase5_phase6_handoff_event_log_mismatch=true")
        return 1
    if mission_phase5.get("phase6_learning_loop_plan_allowed") != (
        phase5_phase6_handoff.get("phase6_learning_loop_plan_allowed") is True
    ):
        print("cockpit_status_mission_phase5_phase6_plan_mismatch=true")
        return 1
    if mission_phase5.get("phase6_learning_loop_implementation_allowed") is not False:
        print("cockpit_status_mission_phase5_phase6_implementation_allowed=true")
        return 1
    if mission_phase5.get("phase6_learning_write_allowed") is not False:
        print("cockpit_status_mission_phase5_phase6_learning_write_allowed=true")
        return 1
    if mission_phase5.get("phase6_knowledge_graph_write_allowed") is not False:
        print("cockpit_status_mission_phase5_phase6_knowledge_graph_write_allowed=true")
        return 1
    if mission_phase5.get("phase6_required_module_count") != phase5_phase6_handoff.get(
        "phase6_required_module_count"
    ):
        print("cockpit_status_mission_phase5_phase6_module_count_mismatch=true")
        return 1
    if mission_phase5.get("phase6_handoff_closed_trade_count") != phase5_phase6_handoff.get(
        "closed_trade_count"
    ):
        print("cockpit_status_mission_phase5_phase6_closed_trade_mismatch=true")
        return 1
    if mission_phase5.get("phase6_handoff_postmortem_due_count") != phase5_phase6_handoff.get(
        "postmortem_due_count"
    ):
        print("cockpit_status_mission_phase5_phase6_postmortem_due_mismatch=true")
        return 1
    if mission_phase5.get("phase6_handoff_phase7_proof_credit_allowed") is not False:
        print("cockpit_status_mission_phase5_phase6_phase7_credit=true")
        return 1
    if mission_phase5.get("phase6_handoff_live_capital_enabled_count") != 0:
        print("cockpit_status_mission_phase5_phase6_live_capital=true")
        return 1
    if mission_phase5.get("system_map_status") != phase5_system_map.get("status"):
        print("cockpit_status_mission_phase5_system_map_status_mismatch=true")
        return 1
    if mission_phase5.get("system_map_node_count") != phase5_system_map.get("node_count"):
        print("cockpit_status_mission_phase5_system_map_node_count_mismatch=true")
        return 1
    if mission_phase5.get("system_map_lane_count") != phase5_system_map.get("lane_count"):
        print("cockpit_status_mission_phase5_system_map_lane_count_mismatch=true")
        return 1
    if mission_phase5.get("system_map_layer_b_node_count") != phase5_system_map.get(
        "layer_b_node_count"
    ):
        print("cockpit_status_mission_phase5_system_map_layer_b_count_mismatch=true")
        return 1
    if mission_phase5.get("system_map_backend_parity_error_count") != 0:
        print("cockpit_status_mission_phase5_system_map_parity_errors=true")
        return 1
    if mission_phase5.get("system_map_unsafe_control_count") != 0:
        print("cockpit_status_mission_phase5_system_map_unsafe_controls=true")
        return 1
    if mission_phase5.get("system_map_event_log_written") is not True:
        print("cockpit_status_mission_phase5_system_map_event_log_not_written=true")
        return 1
    if mission_phase5.get("system_map_dashboard_claims_trading_now") is not False:
        print("cockpit_status_mission_phase5_system_map_claims_trading=true")
        return 1
    if mission_phase5.get("orchestration_start_allowed") is not False:
        print("cockpit_status_mission_phase5_orchestration_start_allowed=true")
        return 1
    if mission_phase5.get("nonapproval_blocker_count") != 0:
        print("cockpit_status_mission_phase5_nonapproval_blockers_present=true")
        return 1
    if "cannot start Layer B orchestration" not in mission_phase5.get("boundary", ""):
        print("cockpit_status_mission_phase5_boundary_weak=true")
        return 1
    mission_phase3 = mission.get("phase3_readiness", {})
    missing_mission_phase3_fields = sorted(MISSION_PHASE3_READINESS_REQUIRED_FIELDS - set(mission_phase3))
    if missing_mission_phase3_fields:
        print("cockpit_status_mission_phase3_fields_missing=" + ",".join(missing_mission_phase3_fields))
        return 1
    if mission_phase3.get("phase") != "Q3":
        print("cockpit_status_mission_phase3_phase_mismatch=true")
        return 1
    if mission_phase3.get("status") != "provider_scheduler_readiness":
        print("cockpit_status_mission_phase3_status_mismatch=true")
        return 1
    if mission_phase3.get("readiness_scope") != "provider_scheduler_readiness":
        print("cockpit_status_mission_phase3_scope_mismatch=true")
        return 1
    if mission_phase3.get("execution_readiness") != "not_execution_ready":
        print("cockpit_status_mission_phase3_execution_readiness_enabled=true")
        return 1
    if mission_phase3.get("public_safe") is not True:
        print("cockpit_status_mission_phase3_not_public_safe=true")
        return 1
    if mission_phase3.get("provider_count") != quantum_oracle.get("provider_readiness", {}).get("provider_count"):
        print("cockpit_status_mission_phase3_provider_count_mismatch=true")
        return 1
    if mission_phase3.get("expected_provider_count") != quantum_oracle.get("provider_readiness", {}).get(
        "expected_provider_count"
    ):
        print("cockpit_status_mission_phase3_expected_provider_count_mismatch=true")
        return 1
    if mission_phase3.get("configured_provider_count") != quantum_oracle.get("provider_readiness", {}).get(
        "configured_count"
    ):
        print("cockpit_status_mission_phase3_configured_provider_count_mismatch=true")
        return 1
    if mission_phase3.get("qctrl_configured") is not True:
        print("cockpit_status_mission_phase3_qctrl_not_configured=true")
        return 1
    if mission_phase3.get("qctrl_status") != quantum_oracle.get("provider_readiness", {}).get(
        "qctrl_readiness", {}
    ).get("status"):
        print("cockpit_status_mission_phase3_qctrl_status_mismatch=true")
        return 1
    if mission_phase3.get("qctrl_live_probe_enabled") is not False:
        print("cockpit_status_mission_phase3_qctrl_live_probe_enabled=true")
        return 1
    if mission_phase3.get("qctrl_optimization_job_submitted") is not False:
        print("cockpit_status_mission_phase3_qctrl_optimization_submitted=true")
        return 1
    if not isinstance(mission_phase3.get("qiskit_available"), bool) or not isinstance(
        mission_phase3.get("qiskit_aer_available"), bool
    ):
        print("cockpit_status_mission_phase3_qiskit_availability_invalid=true")
        return 1
    if mission_phase3.get("local_simulator_backend") != quantum_oracle.get("local_simulator", {}).get(
        "selected_backend"
    ):
        print("cockpit_status_mission_phase3_local_backend_mismatch=true")
        return 1
    if mission_phase3.get("ibm_quantum_status") not in {
        "missing_secret",
        "configured",
        "configured_policy_blocked",
    }:
        print("cockpit_status_mission_phase3_ibm_status_mismatch=true")
        return 1
    if mission_phase3.get("aws_braket_status") != "missing_secret":
        print("cockpit_status_mission_phase3_aws_status_mismatch=true")
        return 1
    if mission_phase3.get("scheduler_status") != quantum_oracle.get("scheduler_dry_run", {}).get("status"):
        print("cockpit_status_mission_phase3_scheduler_status_mismatch=true")
        return 1
    if mission_phase3.get("scheduler_enabled") is not False:
        print("cockpit_status_mission_phase3_scheduler_enabled=true")
        return 1
    if mission_phase3.get("autonomous_scheduler_enabled") is not False:
        print("cockpit_status_mission_phase3_autonomous_scheduler_enabled=true")
        return 1
    if mission_phase3.get("latest_recommendation") != quantum_oracle.get("latest_recommendation"):
        print("cockpit_status_mission_phase3_recommendation_mismatch=true")
        return 1
    if mission_phase3.get("latest_output_route_type") != quantum_oracle.get("latest_output_route_type"):
        print("cockpit_status_mission_phase3_output_route_mismatch=true")
        return 1
    for key in (
        "qctrl_provider_call_count",
        "scheduler_jobs_queued_count",
        "scheduler_jobs_submitted_count",
        "hardware_submission_allowed_count",
        "hardware_submitted_count",
        "hardware_scheduler_enabled_count",
        "execution_allowed_count",
        "paper_order_allowed_count",
        "trade_candidate_created_count",
        "secret_value_exposed_count",
        "raw_response_exposed_count",
        "local_absolute_path_exposed_count",
        "cloud_job_identifier_exposed_count",
    ):
        if mission_phase3.get(key) != 0:
            print(f"cockpit_status_mission_phase3_nonzero={key}")
            return 1
    if "provider/scheduler readiness only" not in mission_phase3.get("boundary", ""):
        print("cockpit_status_mission_phase3_boundary_scope_weak=true")
        return 1
    if "not execution readiness" not in mission_phase3.get("boundary", ""):
        print("cockpit_status_mission_phase3_boundary_execution_weak=true")
        return 1
    mission_trade = mission.get("trade_intent", {})
    missing_mission_trade_fields = sorted(MISSION_TRADE_REQUIRED_FIELDS - set(mission_trade))
    if missing_mission_trade_fields:
        print("cockpit_status_mission_trade_fields_missing=" + ",".join(missing_mission_trade_fields))
        return 1
    if mission_trade.get("candidate_count") != len(payload["trade_layer"].get("candidates", [])):
        print("cockpit_status_mission_candidate_count_mismatch=true")
        return 1
    if mission_trade.get("observed_signal_count") != len(payload["trade_layer"].get("watching", [])):
        print("cockpit_status_mission_observed_signal_count_mismatch=true")
        return 1
    if mission_trade.get("execution_allowed_count") != 0:
        print("cockpit_status_mission_execution_allowed=true")
        return 1
    if mission_trade.get("paper_order_submitted_count") != 0 or mission_trade.get("broker_post_called_count") != 0:
        print("cockpit_status_mission_broker_submit_enabled=true")
        return 1
    mission_portfolio = mission.get("portfolio", {})
    missing_mission_portfolio_fields = sorted(MISSION_PORTFOLIO_REQUIRED_FIELDS - set(mission_portfolio))
    if missing_mission_portfolio_fields:
        print("cockpit_status_mission_portfolio_fields_missing=" + ",".join(missing_mission_portfolio_fields))
        return 1
    if mission_portfolio.get("open_position_count") != len(capital.get("open_positions", [])):
        print("cockpit_status_mission_open_position_count_mismatch=true")
        return 1
    if mission_portfolio.get("portfolio_value_source") != (
        paper_lifecycle_postmortem.get("portfolio_value_source")
    ):
        print("cockpit_status_mission_portfolio_rs6_source_mismatch=true")
        return 1
    if mission_portfolio.get("balance_ticker_broker_account_derived") != (
        paper_lifecycle_postmortem.get("balance_ticker_broker_account_derived")
    ):
        print("cockpit_status_mission_portfolio_rs6_balance_source_mismatch=true")
        return 1
    if mission_portfolio.get("postmortem_due_count") != (
        paper_lifecycle_postmortem.get("postmortem_due_count")
    ):
        print("cockpit_status_mission_portfolio_rs6_postmortem_due_mismatch=true")
        return 1
    if mission_portfolio.get("closed_trade_postmortem_coverage_count") != (
        paper_lifecycle_postmortem.get("closed_trade_postmortem_coverage_count")
    ):
        print("cockpit_status_mission_portfolio_rs6_postmortem_coverage_mismatch=true")
        return 1
    if mission_portfolio.get("closed_trade_missing_postmortem_count") != (
        paper_lifecycle_postmortem.get("closed_trade_missing_postmortem_count")
    ):
        print("cockpit_status_mission_portfolio_rs6_missing_postmortem_mismatch=true")
        return 1
    if mission_portfolio.get("paper_proof_ledger_verified_record_count") != (
        paper_lifecycle_postmortem.get("paper_proof_ledger_verified_record_count")
    ):
        print("cockpit_status_mission_portfolio_rs6_proof_record_mismatch=true")
        return 1
    if mission_portfolio.get("mirror_trade_counted_for_proof_count") != (
        paper_lifecycle_postmortem.get("mirror_trade_counted_for_proof_count")
    ):
        print("cockpit_status_mission_portfolio_rs6_mirror_proof_mismatch=true")
        return 1
    if mission_portfolio.get("live_capital_enabled") is not False or mission_portfolio.get("write_authority") is not False:
        print("cockpit_status_mission_portfolio_authority_enabled=true")
        return 1
    mission_safety = mission.get("safety", {})
    missing_mission_safety_fields = sorted(MISSION_SAFETY_REQUIRED_FIELDS - set(mission_safety))
    if missing_mission_safety_fields:
        print("cockpit_status_mission_safety_fields_missing=" + ",".join(missing_mission_safety_fields))
        return 1
    if mission_safety.get("live_capital_enabled") is not False or mission_safety.get("broker_write_allowed") is not False:
        print("cockpit_status_mission_safety_authority_enabled=true")
        return 1
    if "read-only" not in mission_safety.get("boundary", ""):
        print("cockpit_status_mission_safety_boundary_weak=true")
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
    if not any(source.get("source_key") == "tradingview_mcp" for source in payload["watching"]):
        print("cockpit_status_watching_tradingview_mcp_missing=true")
        return 1
    signal_review_eligible_count = sum(1 for source in payload["watching"] if source.get("eligible_for_signal_review") is True)
    if signal_review_eligible_count < 1:
        print("cockpit_status_no_signal_review_eligible_sources=true")
        return 1
    if not any(source.get("usable_for_research_context") is True for source in payload["watching"]):
        print("cockpit_status_no_research_context_sources=true")
        return 1
    if any(source.get("can_authorize_orders") is not False for source in payload["watching"]):
        print("cockpit_status_source_order_authority_unblocked=true")
        return 1
    if any(source.get("can_influence_signals") != source.get("eligible_for_signal_review") for source in payload["watching"]):
        print("cockpit_status_source_signal_review_alias_mismatch=true")
        return 1
    if any("no_source_can_authorize_orders" not in source.get("order_authority_boundary", "") for source in payload["watching"]):
        print("cockpit_status_source_order_boundary_weak=true")
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
        market_policy = review.get("market_confirmation_policy", {})
        if not isinstance(market_policy, dict):
            print("cockpit_status_signal_integrity_market_policy_invalid=true")
            return 1
        missing_market_policy_fields = sorted(MARKET_CONFIRMATION_POLICY_REQUIRED_FIELDS - set(market_policy))
        if missing_market_policy_fields:
            print(
                "cockpit_status_signal_integrity_market_policy_fields_missing="
                f"{review.get('review_id', 'unknown')}:{','.join(missing_market_policy_fields)}"
            )
            return 1
        if market_policy.get("signal_authority") is not False:
            print("cockpit_status_signal_integrity_market_policy_signal_authority=true")
            return 1
        if market_policy.get("order_authority") is not False:
            print("cockpit_status_signal_integrity_market_policy_order_authority=true")
            return 1
        if market_policy.get("broker_reconciliation_authority") is not False:
            print("cockpit_status_signal_integrity_market_policy_reconciliation_authority=true")
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
    research_goals = cognition.get("research_goals", {})
    if not isinstance(research_goals, dict):
        print("cockpit_status_research_goals_missing=true")
        return 1
    if research_goals.get("status") not in {"ok", "not_run", "degraded"}:
        print("cockpit_status_research_goals_status_invalid=true")
        return 1
    for authority_field in (
        "execution_allowed",
        "paper_order_allowed",
        "trade_candidate_creation_allowed",
        "risk_handoff_allowed",
        "broker_write_allowed",
        "live_capital_enabled",
    ):
        if int(research_goals.get("authority_counts", {}).get(authority_field, 0) or 0) != 0:
            print(f"cockpit_status_research_goal_authority_enabled={authority_field}")
            return 1
    if "pre-signal research state" not in research_goals.get("boundary", ""):
        print("cockpit_status_research_goals_boundary_weak=true")
        return 1
    if research_goals.get("hardening_version") != "rs2_2026_06_03":
        print("cockpit_status_research_goal_hardening_version_missing=true")
        return 1
    for count_field in (
        "candidate_ready_goal_count",
        "closed_no_trade_goal_count",
        "stale_goal_count",
        "expired_goal_count",
    ):
        if int(research_goals.get(count_field, 0) or 0) < 0:
            print(f"cockpit_status_research_goal_count_invalid={count_field}")
            return 1
    if not isinstance(cognition.get("research_goal_records"), list):
        print("cockpit_status_research_goal_records_missing=true")
        return 1
    for goal in cognition.get("research_goal_records", []):
        missing_fields = sorted(RESEARCH_GOAL_REQUIRED_FIELDS - set(goal))
        if missing_fields:
            print(
                "cockpit_status_research_goal_fields_missing="
                f"{goal.get('goal_id', 'unknown')}:{','.join(missing_fields)}"
            )
            return 1
        if goal.get("minimum_source_quorum", 0) < 2:
            print("cockpit_status_research_goal_source_quorum_weak=true")
            return 1
        if goal.get("research_goal_hardening_version") != "rs2_2026_06_03":
            print("cockpit_status_research_goal_record_hardening_version_missing=true")
            return 1
        for score_field in (
            "source_quorum_score",
            "market_confirmation_score",
            "worldview_relevance_score",
            "akber_stage_score",
            "contradiction_score",
            "latency_freshness_score",
            "risk_readiness_score",
            "priority_score",
        ):
            try:
                score = float(goal.get(score_field))
            except (TypeError, ValueError):
                print(f"cockpit_status_research_goal_score_invalid={score_field}")
                return 1
            if not 0 <= score <= 1:
                print(f"cockpit_status_research_goal_score_out_of_range={score_field}")
                return 1
        if goal.get("status") == "candidate_ready" and goal.get("candidate_ready_blockers"):
            print("cockpit_status_research_goal_candidate_ready_has_blockers=true")
            return 1
        if goal.get("status") == "closed_no_trade" and not goal.get("close_reason"):
            print("cockpit_status_research_goal_closed_no_trade_reason_missing=true")
            return 1
        for authority_field in (
            "execution_allowed",
            "paper_order_allowed",
            "trade_candidate_creation_allowed",
            "risk_handoff_allowed",
            "broker_write_allowed",
            "live_capital_enabled",
        ):
            if goal.get(authority_field) is not False:
                print(f"cockpit_status_research_goal_record_authority_enabled={authority_field}")
                return 1
        if "pre-signal research state" not in goal.get("boundary", ""):
            print("cockpit_status_research_goal_record_boundary_weak=true")
            return 1
    market_context = cognition.get("market_context", {})
    if not isinstance(market_context, dict):
        print("cockpit_status_market_context_missing=true")
        return 1
    if market_context.get("status") not in {"ok", "degraded"}:
        print("cockpit_status_market_context_status_invalid=true")
        return 1
    if market_context.get("packet_version") != "rs3_2026_06_03":
        print("cockpit_status_market_context_packet_version_missing=true")
        return 1
    if int(market_context.get("packet_count", 0) or 0) < 1:
        print("cockpit_status_market_context_packet_count_missing=true")
        return 1
    if float(market_context.get("average_source_quality_score", 0) or 0) <= 0:
        print("cockpit_status_market_context_quality_missing=true")
        return 1
    for authority_field in (
        "execution_allowed",
        "paper_order_allowed",
        "trade_candidate_creation_allowed",
        "risk_handoff_allowed",
        "broker_write_allowed",
        "live_capital_enabled",
        "source_quorum_credit_allowed",
    ):
        if int(market_context.get("authority_counts", {}).get(authority_field, 0) or 0) != 0:
            print(f"cockpit_status_market_context_authority_enabled={authority_field}")
            return 1
    if "read-only context" not in market_context.get("boundary", ""):
        print("cockpit_status_market_context_boundary_weak=true")
        return 1
    packets = cognition.get("market_context_packets", [])
    if not isinstance(packets, list) or not packets:
        print("cockpit_status_market_context_packets_missing=true")
        return 1
    for packet in packets:
        if packet.get("packet_version") != "rs3_2026_06_03":
            print("cockpit_status_market_context_packet_version_invalid=true")
            return 1
        for authority_field in (
            "execution_allowed",
            "paper_order_allowed",
            "trade_candidate_creation_allowed",
            "risk_handoff_allowed",
            "broker_write_allowed",
            "live_capital_enabled",
            "source_quorum_credit_allowed",
        ):
            if packet.get(authority_field) is not False:
                print(f"cockpit_status_market_context_packet_authority_enabled={authority_field}")
                return 1
        if packet.get("price_volume_context", {}).get("role") != "supplemental_market_confirmation_only":
            print("cockpit_status_market_context_yahoo_role_invalid=true")
            return 1
        if packet.get("technical_context", {}).get("role") != "supplemental_technical_confirmation_only":
            print("cockpit_status_market_context_tradingview_role_invalid=true")
            return 1
        if packet.get("paper_account_context", {}).get("authority") != "read_only_paper_account_context_only":
            print("cockpit_status_market_context_paper_context_role_invalid=true")
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
    if "research goal intake" not in cognition.get("analysis_timeline", []):
        print("cockpit_status_analysis_timeline_research_goal_missing=true")
        return 1
    if "market context packet" not in cognition.get("analysis_timeline", []):
        print("cockpit_status_analysis_timeline_market_context_missing=true")
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
    if "research_goal_requires_corroboration" not in cognition.get("blocked_reasons", []):
        print("cockpit_status_research_goal_block_missing=true")
        return 1
    if "market_context_cannot_create_trade_candidate" not in cognition.get("blocked_reasons", []):
        print("cockpit_status_market_context_block_missing=true")
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

    execution_policy = payload.get("execution_policy", {})
    missing_execution_fields = sorted(EXECUTION_POLICY_REQUIRED_FIELDS - set(execution_policy))
    if missing_execution_fields:
        print("cockpit_status_execution_policy_fields_missing=" + ",".join(missing_execution_fields))
        return 1
    if execution_policy.get("status") != "ok":
        print("cockpit_status_execution_policy_not_ok=true")
        return 1
    if execution_policy.get("authority") != "read_only_execution_policy":
        print("cockpit_status_execution_policy_authority_mismatch=true")
        return 1
    if execution_policy.get("execution_allowed_count") != 0:
        print("cockpit_status_execution_policy_execution_allowed_not_zero=true")
        return 1
    if execution_policy.get("staged_paper_order_allowed_count") != 0:
        print("cockpit_status_execution_policy_staged_order_allowed_not_zero=true")
        return 1
    if execution_policy.get("paper_order_created_count") != 0:
        print("cockpit_status_execution_policy_order_created_not_zero=true")
        return 1
    if execution_policy.get("broker_write_allowed_count") != 0:
        print("cockpit_status_execution_policy_broker_write_allowed_not_zero=true")
        return 1
    if execution_policy.get("live_capital_enabled_count") != 0:
        print("cockpit_status_execution_policy_live_capital_enabled_not_zero=true")
        return 1
    if "cannot stage paper orders" not in execution_policy.get("boundary", ""):
        print("cockpit_status_execution_policy_boundary_weak=true")
        return 1
    if not isinstance(execution_policy.get("reviews"), list) or not execution_policy["reviews"]:
        print("cockpit_status_execution_policy_reviews_missing=true")
        return 1
    for review in execution_policy.get("reviews", []):
        missing_fields = sorted(EXECUTION_POLICY_REVIEW_REQUIRED_FIELDS - set(review))
        if missing_fields:
            print(
                "cockpit_status_execution_policy_review_fields_missing="
                f"{review.get('review_id', 'unknown')}:{','.join(missing_fields)}"
            )
            return 1
        if review.get("execution_allowed") is not False:
            print("cockpit_status_execution_policy_review_execution_allowed=true")
            return 1
        if review.get("staged_paper_order_allowed") is not False:
            print("cockpit_status_execution_policy_review_staged_order_allowed=true")
            return 1
        if review.get("paper_order_created") is not False:
            print("cockpit_status_execution_policy_review_order_created=true")
            return 1
        if review.get("broker_write_allowed") is not False:
            print("cockpit_status_execution_policy_review_broker_write_allowed=true")
            return 1
        if review.get("live_capital_enabled") is not False:
            print("cockpit_status_execution_policy_review_live_capital_enabled=true")
            return 1
        if not 0 <= float(review.get("policy_score", -1)) <= 1:
            print("cockpit_status_execution_policy_score_bad=true")
            return 1
        missing_checks = sorted(EXECUTION_POLICY_REQUIRED_CHECKS - set(review.get("checks", {})))
        if missing_checks:
            print(
                "cockpit_status_execution_policy_checks_missing="
                f"{review.get('review_id', 'unknown')}:{','.join(missing_checks)}"
            )
            return 1
        missing_switches = sorted(EXECUTION_POLICY_REQUIRED_KILL_SWITCHES - set(review.get("kill_switches", {})))
        if missing_switches:
            print(
                "cockpit_status_execution_policy_kill_switches_missing="
                f"{review.get('review_id', 'unknown')}:{','.join(missing_switches)}"
            )
            return 1
        if "cannot stage orders" not in review.get("boundary", ""):
            print("cockpit_status_execution_policy_review_boundary_weak=true")
            return 1

    staged_order = payload.get("staged_paper_order", {})
    missing_staged_order_fields = sorted(STAGED_PAPER_ORDER_REQUIRED_FIELDS - set(staged_order))
    if missing_staged_order_fields:
        print("cockpit_status_staged_paper_order_fields_missing=" + ",".join(missing_staged_order_fields))
        return 1
    if staged_order.get("status") != "ok":
        print("cockpit_status_staged_paper_order_not_ok=true")
        return 1
    if staged_order.get("authority") != "disabled_staged_order_contract":
        print("cockpit_status_staged_paper_order_authority_mismatch=true")
        return 1
    if staged_order.get("execution_allowed_count") != 0:
        print("cockpit_status_staged_paper_order_execution_allowed=true")
        return 1
    if staged_order.get("staged_paper_order_created_count") != 0:
        print("cockpit_status_staged_paper_order_created=true")
        return 1
    if staged_order.get("paper_order_submittable_count") != 0:
        print("cockpit_status_staged_paper_order_submittable=true")
        return 1
    if staged_order.get("broker_write_allowed_count") != 0:
        print("cockpit_status_staged_paper_order_broker_write_allowed=true")
        return 1
    if staged_order.get("live_capital_enabled_count") != 0:
        print("cockpit_status_staged_paper_order_live_capital_enabled=true")
        return 1
    if "cannot create staged orders" not in staged_order.get("boundary", ""):
        print("cockpit_status_staged_paper_order_boundary_weak=true")
        return 1
    if not isinstance(staged_order.get("reviews"), list) or not staged_order["reviews"]:
        print("cockpit_status_staged_paper_order_reviews_missing=true")
        return 1
    for review in staged_order.get("reviews", []):
        missing_fields = sorted(STAGED_PAPER_ORDER_REVIEW_REQUIRED_FIELDS - set(review))
        if missing_fields:
            print(
                "cockpit_status_staged_paper_order_review_fields_missing="
                f"{review.get('review_id', 'unknown')}:{','.join(missing_fields)}"
            )
            return 1
        if review.get("execution_allowed") is not False:
            print("cockpit_status_staged_paper_order_review_execution_allowed=true")
            return 1
        if review.get("staged_paper_order_created") is not False:
            print("cockpit_status_staged_paper_order_review_created=true")
            return 1
        if review.get("paper_order_submittable") is not False:
            print("cockpit_status_staged_paper_order_review_submittable=true")
            return 1
        if review.get("broker_write_allowed") is not False:
            print("cockpit_status_staged_paper_order_review_broker_write_allowed=true")
            return 1
        if review.get("live_capital_enabled") is not False:
            print("cockpit_status_staged_paper_order_review_live_capital_enabled=true")
            return 1
        missing_hypothetical = sorted(
            STAGED_PAPER_ORDER_HYPOTHETICAL_REQUIRED_FIELDS - set(review.get("hypothetical_order", {}))
        )
        if missing_hypothetical:
            print(
                "cockpit_status_staged_paper_order_hypothetical_fields_missing="
                f"{review.get('review_id', 'unknown')}:{','.join(missing_hypothetical)}"
            )
            return 1
        if review.get("hypothetical_order", {}).get("status") != "not_created":
            print("cockpit_status_staged_paper_order_hypothetical_created=true")
            return 1
        missing_checks = sorted(
            STAGED_PAPER_ORDER_RECONCILIATION_REQUIRED_CHECKS - set(review.get("reconciliation_checks", {}))
        )
        if missing_checks:
            print(
                "cockpit_status_staged_paper_order_checks_missing="
                f"{review.get('review_id', 'unknown')}:{','.join(missing_checks)}"
            )
            return 1
        if "cannot create a staged order" not in review.get("boundary", ""):
            print("cockpit_status_staged_paper_order_review_boundary_weak=true")
            return 1

    broker_reconciliation = payload.get("broker_reconciliation", {})
    missing_broker_reconciliation_fields = sorted(
        BROKER_RECONCILIATION_REQUIRED_FIELDS - set(broker_reconciliation)
    )
    if missing_broker_reconciliation_fields:
        print(
            "cockpit_status_broker_reconciliation_fields_missing="
            + ",".join(missing_broker_reconciliation_fields)
        )
        return 1
    if broker_reconciliation.get("status") != "ok":
        print("cockpit_status_broker_reconciliation_not_ok=true")
        return 1
    if broker_reconciliation.get("authority") != "read_only_broker_reconciliation":
        print("cockpit_status_broker_reconciliation_authority_mismatch=true")
        return 1
    zero_authority_counts = {
        "idempotency_key_allocated_count": "cockpit_status_broker_reconciliation_idempotency_allocated=true",
        "event_log_prewrite_created_count": "cockpit_status_broker_reconciliation_event_log_prewrite_created=true",
        "pre_trade_snapshot_created_count": "cockpit_status_broker_reconciliation_pre_trade_snapshot_created=true",
        "duplicate_order_guard_ready_count": "cockpit_status_broker_reconciliation_duplicate_guard_ready=true",
        "broker_echo_verified_count": "cockpit_status_broker_reconciliation_broker_echo_verified=true",
        "post_submit_reconciliation_ready_count": "cockpit_status_broker_reconciliation_post_submit_ready=true",
        "postmortem_link_ready_count": "cockpit_status_broker_reconciliation_postmortem_link_ready=true",
        "paper_order_submit_allowed_count": "cockpit_status_broker_reconciliation_paper_submit_allowed=true",
        "broker_write_allowed_count": "cockpit_status_broker_reconciliation_broker_write_allowed=true",
        "live_capital_enabled_count": "cockpit_status_broker_reconciliation_live_capital_enabled=true",
    }
    for count_key, error_key in zero_authority_counts.items():
        if broker_reconciliation.get(count_key) != 0:
            print(error_key)
            return 1
    if "cannot submit paper orders" not in broker_reconciliation.get("boundary", ""):
        print("cockpit_status_broker_reconciliation_boundary_weak=true")
        return 1
    if not isinstance(broker_reconciliation.get("reviews"), list) or not broker_reconciliation["reviews"]:
        print("cockpit_status_broker_reconciliation_reviews_missing=true")
        return 1
    for review in broker_reconciliation.get("reviews", []):
        missing_fields = sorted(BROKER_RECONCILIATION_REVIEW_REQUIRED_FIELDS - set(review))
        if missing_fields:
            print(
                "cockpit_status_broker_reconciliation_review_fields_missing="
                f"{review.get('review_id', 'unknown')}:{','.join(missing_fields)}"
            )
            return 1
        for flag_key in (
            "idempotency_key_allocated",
            "event_log_prewrite_created",
            "pre_trade_snapshot_created",
            "duplicate_order_guard_ready",
            "broker_echo_verified",
            "post_submit_reconciliation_ready",
            "postmortem_link_ready",
            "paper_order_submit_allowed",
            "broker_write_allowed",
            "live_capital_enabled",
        ):
            if review.get(flag_key) is not False:
                print(
                    "cockpit_status_broker_reconciliation_review_flag_not_false="
                    f"{review.get('review_id', 'unknown')}:{flag_key}"
                )
                return 1
        missing_broker_echo = sorted(
            BROKER_RECONCILIATION_ECHO_REQUIRED_FIELDS - set(review.get("broker_echo", {}))
        )
        if missing_broker_echo:
            print(
                "cockpit_status_broker_reconciliation_echo_fields_missing="
                f"{review.get('review_id', 'unknown')}:{','.join(missing_broker_echo)}"
            )
            return 1
        if review.get("broker_echo", {}).get("status") != "not_requested":
            print("cockpit_status_broker_reconciliation_echo_requested=true")
            return 1
        missing_checks = sorted(
            BROKER_RECONCILIATION_REQUIRED_CHECKS - set(review.get("reconciliation_checks", {}))
        )
        if missing_checks:
            print(
                "cockpit_status_broker_reconciliation_checks_missing="
                f"{review.get('review_id', 'unknown')}:{','.join(missing_checks)}"
            )
            return 1
        if review.get("reconciliation_checks", {}).get("broker_route") != "fail_closed_no_broker_submit_route":
            print("cockpit_status_broker_reconciliation_route_not_closed=true")
            return 1
        if review.get("reconciliation_checks", {}).get("idempotency_key") != "fail_not_allocated":
            print("cockpit_status_broker_reconciliation_idempotency_allocated=true")
            return 1
        if review.get("reconciliation_checks", {}).get("event_log_prewrite") != "fail_not_written":
            print("cockpit_status_broker_reconciliation_event_log_written=true")
            return 1
    if "cannot submit paper orders" not in review.get("boundary", ""):
        print("cockpit_status_broker_reconciliation_review_boundary_weak=true")
        return 1

    paper_submit_receipt = payload.get("paper_submit_receipt", {})
    missing_paper_submit_receipt_fields = sorted(
        PAPER_SUBMIT_RECEIPT_REQUIRED_FIELDS - set(paper_submit_receipt)
    )
    if missing_paper_submit_receipt_fields:
        print("cockpit_status_paper_submit_receipt_fields_missing=" + ",".join(missing_paper_submit_receipt_fields))
        return 1
    if paper_submit_receipt.get("status") != "ok":
        print("cockpit_status_paper_submit_receipt_not_ok=true")
        return 1
    if paper_submit_receipt.get("authority") != "dry_run_receipt_only":
        print("cockpit_status_paper_submit_receipt_authority_mismatch=true")
        return 1
    zero_receipt_counts = {
        "paper_order_submitted_count": "cockpit_status_paper_submit_receipt_order_submitted=true",
        "broker_post_called_count": "cockpit_status_paper_submit_receipt_broker_post_called=true",
        "broker_write_allowed_count": "cockpit_status_paper_submit_receipt_broker_write_allowed=true",
        "live_capital_enabled_count": "cockpit_status_paper_submit_receipt_live_capital_enabled=true",
    }
    for count_key, error_key in zero_receipt_counts.items():
        if paper_submit_receipt.get(count_key) != 0:
            print(error_key)
            return 1
    if "cannot call broker POST routes" not in paper_submit_receipt.get("boundary", ""):
        print("cockpit_status_paper_submit_receipt_boundary_weak=true")
        return 1
    if not isinstance(paper_submit_receipt.get("reviews"), list) or not paper_submit_receipt["reviews"]:
        print("cockpit_status_paper_submit_receipt_reviews_missing=true")
        return 1
    for review in paper_submit_receipt.get("reviews", []):
        missing_fields = sorted(PAPER_SUBMIT_RECEIPT_REVIEW_REQUIRED_FIELDS - set(review))
        if missing_fields:
            print(
                "cockpit_status_paper_submit_receipt_review_fields_missing="
                f"{review.get('review_id', 'unknown')}:{','.join(missing_fields)}"
            )
            return 1
        for flag_key in (
            "paper_order_submitted",
            "broker_post_called",
            "broker_write_allowed",
            "live_capital_enabled",
        ):
            if review.get(flag_key) is not False:
                print(
                    "cockpit_status_paper_submit_receipt_review_flag_not_false="
                    f"{review.get('review_id', 'unknown')}:{flag_key}"
                )
                return 1
        if review.get("submitted_at") != "not_submitted":
            print("cockpit_status_paper_submit_receipt_submitted_at_not_blocked=true")
            return 1
        missing_receipt = sorted(
            PAPER_SUBMIT_RECEIPT_SIMULATED_REQUIRED_FIELDS - set(review.get("simulated_receipt", {}))
        )
        if missing_receipt:
            print(
                "cockpit_status_paper_submit_receipt_simulated_fields_missing="
                f"{review.get('review_id', 'unknown')}:{','.join(missing_receipt)}"
            )
            return 1
        simulated = review.get("simulated_receipt", {})
        if simulated.get("mode") != "dry_run_only":
            print("cockpit_status_paper_submit_receipt_simulated_not_dry_run=true")
            return 1
        if simulated.get("broker_post_called") is not False:
            print("cockpit_status_paper_submit_receipt_simulated_broker_post_called=true")
            return 1
        if simulated.get("paper_order_submitted") is not False:
            print("cockpit_status_paper_submit_receipt_simulated_order_submitted=true")
            return 1
        idempotency = review.get("idempotency_design", {})
        missing_idempotency = sorted(PAPER_SUBMIT_RECEIPT_IDEMPOTENCY_REQUIRED_FIELDS - set(idempotency))
        if missing_idempotency:
            print(
                "cockpit_status_paper_submit_receipt_idempotency_fields_missing="
                f"{review.get('review_id', 'unknown')}:{','.join(missing_idempotency)}"
            )
            return 1
        if idempotency.get("broker_usable") is not False or idempotency.get("allocation_authority") is not False:
            print("cockpit_status_paper_submit_receipt_idempotency_has_authority=true")
            return 1
        if not str(idempotency.get("preview_key") or "").startswith("dryrun-"):
            print("cockpit_status_paper_submit_receipt_idempotency_preview_not_dryrun=true")
            return 1
        if simulated.get("idempotency_preview_key") != idempotency.get("preview_key"):
            print("cockpit_status_paper_submit_receipt_idempotency_preview_mismatch=true")
            return 1
        prewrite = review.get("event_log_prewrite_schema", {})
        missing_prewrite = sorted(PAPER_SUBMIT_RECEIPT_PREWRITE_REQUIRED_FIELDS - set(prewrite))
        if missing_prewrite:
            print(
                "cockpit_status_paper_submit_receipt_prewrite_fields_missing="
                f"{review.get('review_id', 'unknown')}:{','.join(missing_prewrite)}"
            )
            return 1
        if prewrite.get("write_performed") is not False or prewrite.get("event_log_ref") != "not_written":
            print("cockpit_status_paper_submit_receipt_prewrite_wrote=true")
            return 1
        snapshot = review.get("pre_trade_snapshot_schema", {})
        missing_snapshot = sorted(PAPER_SUBMIT_RECEIPT_SNAPSHOT_REQUIRED_FIELDS - set(snapshot))
        if missing_snapshot:
            print(
                "cockpit_status_paper_submit_receipt_snapshot_fields_missing="
                f"{review.get('review_id', 'unknown')}:{','.join(missing_snapshot)}"
            )
            return 1
        if snapshot.get("capture_performed") is not False or snapshot.get("snapshot_ref") != "not_captured":
            print("cockpit_status_paper_submit_receipt_snapshot_captured=true")
            return 1
        duplicate_guard = review.get("duplicate_order_guard", {})
        missing_guard = sorted(PAPER_SUBMIT_RECEIPT_DUPLICATE_GUARD_REQUIRED_FIELDS - set(duplicate_guard))
        if missing_guard:
            print(
                "cockpit_status_paper_submit_receipt_duplicate_guard_fields_missing="
                f"{review.get('review_id', 'unknown')}:{','.join(missing_guard)}"
            )
            return 1
        if duplicate_guard.get("lookup_performed") is not False or duplicate_guard.get("guard_write_performed") is not False:
            print("cockpit_status_paper_submit_receipt_duplicate_guard_has_authority=true")
            return 1
        if duplicate_guard.get("guard_key") != idempotency.get("preview_key"):
            print("cockpit_status_paper_submit_receipt_duplicate_guard_key_mismatch=true")
            return 1
        missing_checks = sorted(PAPER_SUBMIT_RECEIPT_REQUIRED_CHECKS - set(review.get("receipt_checks", {})))
        if missing_checks:
            print(
                "cockpit_status_paper_submit_receipt_checks_missing="
                f"{review.get('review_id', 'unknown')}:{','.join(missing_checks)}"
            )
            return 1
        if review.get("receipt_checks", {}).get("broker_post") != "pass_not_called":
            print("cockpit_status_paper_submit_receipt_broker_post_not_closed=true")
            return 1
        if review.get("receipt_checks", {}).get("paper_order_submission") != "pass_not_submitted":
            print("cockpit_status_paper_submit_receipt_order_submission_not_closed=true")
            return 1
        if review.get("receipt_checks", {}).get("idempotency_design") != "pass_preview_only":
            print("cockpit_status_paper_submit_receipt_idempotency_design_not_closed=true")
            return 1
        if review.get("receipt_checks", {}).get("event_log_prewrite_schema") != "pass_schema_not_written":
            print("cockpit_status_paper_submit_receipt_prewrite_schema_not_closed=true")
            return 1
        if review.get("receipt_checks", {}).get("pre_trade_snapshot_schema") != "pass_schema_not_captured":
            print("cockpit_status_paper_submit_receipt_snapshot_schema_not_closed=true")
            return 1
        if review.get("receipt_checks", {}).get("duplicate_order_guard_schema") != "pass_guard_not_executed":
            print("cockpit_status_paper_submit_receipt_duplicate_guard_schema_not_closed=true")
            return 1
        if "cannot call Alpaca POST routes" not in review.get("boundary", ""):
            print("cockpit_status_paper_submit_receipt_review_boundary_weak=true")
            return 1

    tradingview_mcp = payload["tradingview_mcp"]
    missing_tradingview_mcp_fields = sorted(TRADINGVIEW_MCP_REQUIRED_FIELDS - set(tradingview_mcp))
    if missing_tradingview_mcp_fields:
        print("cockpit_status_tradingview_mcp_fields_missing=" + ",".join(missing_tradingview_mcp_fields))
        return 1
    if tradingview_mcp.get("status") not in {"connected", "degraded"}:
        print("cockpit_status_tradingview_mcp_status_invalid=true")
        return 1
    if tradingview_mcp.get("public_safe") is not True:
        print("cockpit_status_tradingview_mcp_not_public_safe=true")
        return 1
    if tradingview_mcp.get("source_key") != "tradingview_mcp":
        print("cockpit_status_tradingview_mcp_source_key_mismatch=true")
        return 1
    if tradingview_mcp.get("technical_confirmation_role") != "supplemental_technical_confirmation_only":
        print("cockpit_status_tradingview_mcp_role_mismatch=true")
        return 1
    for key in (
        "source_quorum_credit_allowed",
        "signal_authority",
        "risk_approval_authority",
        "trade_candidate_creation_allowed",
        "execution_allowed",
        "paper_order_allowed",
        "broker_write_allowed",
        "fill_confirmation_authority",
        "receipt_evidence_authority",
        "reconciliation_truth_authority",
        "quantum_job_authority",
        "live_capital_enabled",
        "raw_payload_exposed",
        "local_path_exposed",
    ):
        if tradingview_mcp.get(key) is not False:
            print(f"cockpit_status_tradingview_mcp_authority_enabled={key}")
            return 1
    if "read-only supplemental technical analysis" not in tradingview_mcp.get("boundary", ""):
        print("cockpit_status_tradingview_mcp_boundary_weak=true")
        return 1
    for row in tradingview_mcp.get("technical_contexts", []):
        if row.get("execution_allowed") is not False:
            print("cockpit_status_tradingview_mcp_row_execution_allowed=true")
            return 1
        if row.get("paper_order_allowed") is not False:
            print("cockpit_status_tradingview_mcp_row_paper_order_allowed=true")
            return 1
        if row.get("trade_candidate_created") is not False:
            print("cockpit_status_tradingview_mcp_row_trade_candidate_created=true")
            return 1
        if row.get("broker_write_allowed") is not False:
            print("cockpit_status_tradingview_mcp_row_broker_write_allowed=true")
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
        if not str(intent.get("research_goal_id") or "").strip():
            print("cockpit_status_trade_intent_research_goal_id_missing=true")
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
