"""Public-safe cockpit status contract.

The live qadam.trade cockpit starts as a static site, so this module exports a
sanitized snapshot that can be served without exposing the local MacBook, raw
credentials, shell access, or broker authority.
"""

from __future__ import annotations

import json
import re
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from orchestrator.bookmap_local_bridge import (
    bookmap_local_bridge_context,
    bookmap_local_bridge_packet_context,
    bookmap_local_bridge_status,
)
from orchestrator.agent_reach_bridge import (
    agent_reach_bridge_evidence_items,
    agent_reach_bridge_public_status,
)
from orchestrator.config import Settings
from orchestrator.broker_reconciliation import BrokerReconciliationReviewStore, broker_reconciliation_summary
from orchestrator.event_log import EventLog
from orchestrator.execution import execution_registry
from orchestrator.execution_policy import ExecutionPolicyReviewStore, execution_policy_summary
from orchestrator.evidence_packet_normalization import (
    evidence_packet_normalization_summary,
    normalize_adapter_evidence_packet,
    normalize_signal_evidence_packet,
)
from orchestrator.evidence_packet_runtime import (
    evidence_packet_runtime_public_status,
    write_evidence_packet_runtime,
)
from orchestrator.edge_tracker import (
    build_edge_tracker_status,
    validate_edge_tracker_status,
)
from orchestrator.edge_pattern_ledger import (
    build_edge_pattern_ledger,
    validate_edge_pattern_ledger,
)
from orchestrator.pattern_recognition_engine import (
    build_pattern_recognition_engine,
    validate_pattern_recognition_engine,
)
from orchestrator.quantum_mandatory_review_gate import build_quantum_mandatory_review_gate
from orchestrator.governance import GovernanceStore
from orchestrator.intelligence import (
    LocalResearchAssessmentStore,
    ShadowSignalStore,
    read_research_shadow_triage_queue,
    shadow_intelligence_summary,
)
from orchestrator.live_bridge import live_bridge_contract, write_status_signature
from orchestrator.market_context import MARKET_CONTEXT_PACKET_VERSION, market_context_summary
from orchestrator.operator_inbox import (
    public_operator_inbox_status,
    write_operator_inbox,
)
from orchestrator.paper_account import (
    OPEN_ORDER_STATUSES,
    PaperAccountMirrorStore,
    paper_account_shadow_context,
    paper_account_summary,
)
from orchestrator.paper_lifecycle_portfolio_postmortem import (
    paper_lifecycle_portfolio_postmortem_public_status,
)
from orchestrator.release_contract import PAPER_ACCOUNT_SCOPE
from orchestrator.research_goal import research_goal_summary
from orchestrator.paper_submit_receipt import PaperSubmitReceiptReviewStore, paper_submit_receipt_summary
from orchestrator.paper_live_activation import paper_live_activation_public_status
from orchestrator.paper_live_qctrl_product_access import (
    paper_live_qctrl_product_access_public_status,
)
from orchestrator.paper_operational_mode import paper_operational_mode_public_status
from orchestrator.paperops_alpaca_paper_submit_enablement import (
    paperops_alpaca_paper_submit_enablement_public_status,
)
from orchestrator.paperops_alpaca_paper_post import paperops_alpaca_paper_post_public_status
from orchestrator.paperops_first_week_paper_trade_mandate import (
    first_week_paper_trade_mandate_public_status,
)
from orchestrator.paperops_paper_lifecycle_poller import (
    paperops_paper_lifecycle_poller_public_status,
)
from orchestrator.paperops_paper_lifecycle_polling_enablement import (
    paperops_paper_lifecycle_polling_enablement_public_status,
)
from orchestrator.paperops_guarded_paper_exit_enablement import (
    paperops_guarded_paper_exit_enablement_public_status,
)
from orchestrator.paperops_active_paper_trading_automation import (
    PAPEROPS_ACTIVE_AUTOMATION_READY_STATUSES,
    paperops_active_paper_trading_automation_public_status,
)
from orchestrator.paper_authority_reconciliation import (
    PAPER_AUTHORITY_RECONCILIATION_PUBLIC_FIELDS,
    build_paper_authority_reconciliation,
    validate_paper_authority_reconciliation,
)
from orchestrator.paperops_paper_exit_path import paperops_paper_exit_path_public_status
from orchestrator.paperops_closed_trade_funnel import (
    build_paperops_closed_trade_funnel,
    validate_paperops_closed_trade_funnel,
)
from orchestrator.paperops_close_to_ledger import (
    build_paperops_close_to_ledger,
    validate_paperops_close_to_ledger,
)
from orchestrator.paperops_submit_regression_guard import (
    paperops_submit_regression_guard_public_status,
)
from orchestrator.paperops_source_gap_visibility import (
    paperops_source_gap_visibility_public_status,
)
from orchestrator.paperops_lifecycle_mirror_freshness import (
    build_paperops_lifecycle_mirror_freshness,
)
from orchestrator.paperops_notification_review import (
    paperops_notification_review_public_status,
)
from orchestrator.paperops_30_day_operations import (
    paperops_30_day_operations_public_status,
)
from orchestrator.paperops_opportunity_scan_cadence import (
    PAPEROPS_OPPORTUNITY_SCAN_CADENCE_PUBLIC_FIELDS,
    paperops_opportunity_scan_cadence_public_status,
)
from orchestrator.paperops_cockpit_notification_upgrade import (
    PT9_PUBLIC_FIELDS as PAPEROPS_COCKPIT_NOTIFICATION_UPGRADE_PUBLIC_FIELDS,
    paperops_cockpit_notification_upgrade_public_status,
)
from orchestrator.paper_live_certification import (
    PT10_PUBLIC_FIELDS as PAPER_LIVE_CERTIFICATION_PUBLIC_FIELDS,
    paper_live_certification_public_status,
)
from orchestrator.paperops_qualified_setup_production import (
    paperops_qualified_setup_production_public_status,
)
from orchestrator.paperops_auto_approval_staged_order import (
    paperops_auto_approval_staged_order_public_status,
)
from orchestrator.paperops_qctrl_consultation import paperops_qctrl_public_status
from orchestrator.phase4_approval_record import (
    build_fund_manager_approval_event,
    validate_fund_manager_approval_event,
)
from orchestrator.phase4_certification import validate_phase4_certification
from orchestrator.phase4_manifested_strategy import (
    build_manifested_strategy_metadata,
    validate_manifested_strategy_metadata,
)
from orchestrator.phase4_strategy_toggles import (
    build_strategy_toggle_snapshot,
    validate_strategy_toggle_snapshot,
)
from orchestrator.phase5_readiness import (
    build_phase5_layer_b_readiness,
    validate_phase5_layer_b_readiness,
)
from orchestrator.phase5_kill_switch import (
    KILL_SWITCH_RUNTIME_ARTIFACT,
    build_phase5_kill_switch_ledger,
    validate_phase5_kill_switch_ledger,
)
from orchestrator.phase5_execution_adapter_status import (
    EXECUTION_ADAPTER_RUNTIME_ARTIFACT,
    build_phase5_execution_adapter_status,
    validate_phase5_execution_adapter_status_bundle,
)
from orchestrator.phase5_paper_order_staging import (
    PAPER_ORDER_STAGING_RUNTIME_ARTIFACT,
    build_phase5_paper_order_staging_gate,
    validate_phase5_paper_order_staging_bundle,
)
from orchestrator.phase5_alpaca_paper_dry_run import (
    ALPACA_PAPER_DRY_RUN_RUNTIME_ARTIFACT,
    build_phase5_alpaca_paper_dry_run,
    validate_phase5_alpaca_paper_dry_run_bundle,
)
from orchestrator.phase5_paper_submit_enablement import (
    PAPER_SUBMIT_ENABLEMENT_RUNTIME_ARTIFACT,
    build_phase5_paper_submit_enablement_gate,
    validate_phase5_paper_submit_enablement_bundle,
)
from orchestrator.phase5_prediction_market_adapter import (
    PREDICTION_MARKET_ADAPTER_RUNTIME_ARTIFACT,
    build_phase5_prediction_market_adapter,
    validate_phase5_prediction_market_adapter_bundle,
)
from orchestrator.phase5_telegram_notifier import (
    TELEGRAM_NOTIFIER_RUNTIME_ARTIFACT,
    build_phase5_telegram_notifier,
    validate_phase5_telegram_notifier_bundle,
)
from orchestrator.phase5_position_monitor import (
    POSITION_MONITOR_RUNTIME_ARTIFACT,
    build_phase5_position_monitor,
    validate_phase5_position_monitor_bundle,
)
from orchestrator.phase5_signal_review import (
    SIGNAL_REVIEW_RUNTIME_ARTIFACT,
    build_phase5_signal_review,
    validate_phase5_signal_review_bundle,
)
from orchestrator.phase5_system_map import (
    phase5_system_map_public_status,
    validate_phase5_system_map_bundle,
)
from orchestrator.phase5_paper_trade_drill import (
    PAPER_TRADE_DRILL_RUNTIME_ARTIFACT,
    build_phase5_paper_trade_drill,
    validate_phase5_paper_trade_drill_bundle,
)
from orchestrator.phase5_certification import (
    PHASE5_CERTIFICATION_RUNTIME_ARTIFACT,
    build_phase5_certification,
    validate_phase5_certification,
)
from orchestrator.phase5_phase6_handoff import (
    PHASE5_PHASE6_HANDOFF_RUNTIME_ARTIFACT,
    build_phase5_phase6_handoff,
    validate_phase5_phase6_handoff,
)
from orchestrator.phase6_cockpit_visibility import (
    PUBLIC_STATUS_FIELDS as PHASE6_LEARNING_LOOP_PUBLIC_FIELDS,
    phase6_cockpit_visibility_public_status,
)
from orchestrator.phase6_certification import (
    PUBLIC_STATUS_FIELDS as PHASE6_CERTIFICATION_PUBLIC_FIELDS,
    phase6_certification_public_status,
)
from orchestrator.phase7_cockpit_visibility import (
    PUBLIC_STATUS_FIELDS as PHASE7_DEMO_PROOF_PUBLIC_FIELDS,
    phase7_cockpit_visibility_public_status,
)
from orchestrator.rs9_learning_loop import (
    PUBLIC_STATUS_FIELDS as RS9_LEARNING_LOOP_PUBLIC_FIELDS,
    rs9_learning_loop_public_status,
)
from orchestrator.rs10_final_paper_autonomy_certification import (
    PUBLIC_STATUS_FIELDS as RS10_FINAL_PAPER_AUTONOMY_PUBLIC_FIELDS,
    rs10_final_paper_autonomy_public_status,
    validate_rs10_final_paper_autonomy_certification,
)
from orchestrator.postgres_store import durable_ingestion_status
from orchestrator.preference_mcp_catalog import build_preference_tool_catalog, preference_tool_catalog_paths
from orchestrator.preference_mcp_domain_packs import (
    build_preference_domain_pack_mapping,
    preference_domain_pack_paths,
)
from orchestrator.preference_mcp_identity import (
    PREFERENCE_CLASSIFICATION,
    PREFERENCE_PROVIDER_LABEL,
    PREFERENCE_SOURCE_KEY,
    build_preference_mcp_identity_status,
)
from orchestrator.preference_mcp_provenance import preference_provenance_paths
from orchestrator.preference_mcp_shadow_context import preference_shadow_context_paths
from orchestrator.preference_mcp_source_promotion import preference_source_promotion_paths
from orchestrator.quantum import (
    qctrl_fire_opal_ibm_readiness,
    quantum_local_simulator_status,
    quantum_oracle_summary,
    quantum_provider_readiness,
    validate_qctrl_fire_opal_ibm_readiness,
    validate_quantum_local_simulator_status,
    validate_quantum_oracle_output_routing,
    validate_quantum_provider_readiness,
    validate_quantum_scheduler_dry_run,
)
from orchestrator.risk_agent import RiskPolicyReviewStore, risk_agent_summary
from orchestrator.signal_integrity import SignalIntegrityReviewStore, signal_integrity_summary
from orchestrator.source_health import (
    PROMOTED_ADAPTER_STATUS,
    SourceHeartbeatStore,
    build_data_environment_map,
)
from orchestrator.staged_paper_order import StagedPaperOrderReviewStore, staged_paper_order_summary
from orchestrator.strategy_lead import StrategyLeadShadowStore
from orchestrator.system_state import build_system_health
from orchestrator.telegram_comms import telegram_status
from orchestrator.telegram_codebase_upgrade_notifications import (
    TELEGRAM_CODEBASE_UPGRADE_BOUNDARY,
    TELEGRAM_CODEBASE_UPGRADE_SCHEMA_VERSION,
    telegram_codebase_upgrade_public_status,
)
from orchestrator.telegram_daily_portfolio_digest import (
    TELEGRAM_DAILY_PORTFOLIO_DIGEST_BOUNDARY,
    TELEGRAM_DAILY_PORTFOLIO_DIGEST_SCHEMA_VERSION,
    telegram_daily_portfolio_digest_public_status,
)
from orchestrator.telegram_inbound_intake import telegram_inbound_intake_public_status
from orchestrator.trade_intent import TradeIntentStore, trade_intent_summary
from orchestrator.tradingview_alerts import (
    TradingViewAlertStore,
    tradingview_alert_summary,
)
from orchestrator.tradingview_mcp_adapter import (
    tradingview_mcp_adapter_status,
    tradingview_mcp_context,
    tradingview_mcp_packet_context,
)
from orchestrator.world_model import world_model_claims, world_model_summary
from orchestrator.yahoo_finance_adapter import yahoo_finance_adapter_status
from world_monitor.source_registry import EXPECTED_SOURCE_COUNT

COCKPIT_STATUS_SCHEMA_VERSION = 1
COCKPIT_STATUS_FILENAME = "cockpit-status.json"
PAPER_ACCOUNT_MIRROR_STALE_AFTER_SECONDS = 45 * 60

PROHIBITED_KEYS = {
    "access_token",
    "allowlist_emails",
    "api_key",
    "authorization",
    "bearer",
    "bot_token",
    "bot_username",
    "chat_id",
    "chat_ids",
    "configured_secrets",
    "cache_dir",
    "cache_path",
    "cookie",
    "cookies",
    "crumb",
    "crumb_token",
    "email",
    "handle",
    "member_handles",
    "missing_secrets",
    "password",
    "path",
    "private_key",
    "raw_archive_path",
    "raw_ref",
    "raw_payload",
    "refresh_token",
    "secret_file",
    "secrets_file",
    "telegram_bot_token",
    "telegram_default_chat_id",
    "telegram_payload",
    "token",
    "webhook_secret",
}

YAHOO_FINANCE_PUBLIC_REQUIRED_FIELDS = {
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

TRADINGVIEW_MCP_PUBLIC_REQUIRED_FIELDS = {
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

BOOKMAP_LOCAL_BRIDGE_PUBLIC_REQUIRED_FIELDS = {
    "active_required_challenges",
    "bookmap_order_injection_allowed",
    "bookmap_trading_mode_allowed",
    "boundary",
    "bridge_host_class",
    "bridge_scheme",
    "bridge_url_configured",
    "bridge_url_local",
    "broker_write_allowed",
    "canonical_source_count",
    "classification",
    "connected",
    "degraded_reason",
    "enabled",
    "execution_allowed",
    "fill_confirmation_authority",
    "live_capital_enabled",
    "live_probe_enabled",
    "local_path_exposed",
    "obvious_orderflow_context_count",
    "orderflow_confirmation_role",
    "orderflow_context_count",
    "orderflow_context_status",
    "orderflow_contexts",
    "paper_order_allowed",
    "provider",
    "public_safe",
    "quantum_job_authority",
    "raw_payload_exposed",
    "receipt_evidence_authority",
    "reconciliation_truth_authority",
    "risk_approval_authority",
    "sample_mode_available",
    "sanitized_endpoint",
    "schema_version",
    "signal_authority",
    "source",
    "source_key",
    "source_quorum_credit_allowed",
    "status",
    "trade_candidate_creation_allowed",
}

PREFERENCE_MCP_PUBLIC_REQUIRED_FIELDS = {
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

PHASE4_STRATEGY_PUBLIC_REQUIRED_FIELDS = {
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
    "live_endpoint_allowed_count",
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

PHASE5_LAYER_B_PUBLIC_REQUIRED_FIELDS = {
    "approval_state",
    "boundary",
    "broker_write_allowed",
    "execution_adapter_write_authority",
    "kill_switch_mutation_authority",
    "layer",
    "live_capital_enabled",
    "nonapproval_blocker_count",
    "only_explicit_approval_blocks_phase5_plan",
    "paper_execution_allowed",
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

PHASE5_KILL_SWITCH_PUBLIC_REQUIRED_FIELDS = {
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

PHASE5_EXECUTION_ADAPTER_PUBLIC_REQUIRED_FIELDS = {
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

PHASE5_PAPER_ORDER_STAGING_PUBLIC_REQUIRED_FIELDS = {
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

PHASE5_ALPACA_PAPER_DRY_RUN_PUBLIC_REQUIRED_FIELDS = {
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

PHASE5_PAPER_SUBMIT_ENABLEMENT_PUBLIC_REQUIRED_FIELDS = {
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

PHASE5_PREDICTION_MARKET_ADAPTER_PUBLIC_REQUIRED_FIELDS = {
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

PHASE5_TELEGRAM_NOTIFIER_PUBLIC_REQUIRED_FIELDS = {
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

PHASE5_POSITION_MONITOR_PUBLIC_REQUIRED_FIELDS = {
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

PHASE5_SIGNAL_REVIEW_PUBLIC_REQUIRED_FIELDS = {
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

PHASE5_SYSTEM_MAP_PUBLIC_REQUIRED_FIELDS = {
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

PHASE5_PAPER_TRADE_DRILL_PUBLIC_REQUIRED_FIELDS = {
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

PHASE5_CERTIFICATION_PUBLIC_REQUIRED_FIELDS = {
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

PHASE5_PHASE6_HANDOFF_PUBLIC_REQUIRED_FIELDS = {
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

PHASE6_LEARNING_LOOP_PUBLIC_REQUIRED_FIELDS = set(PHASE6_LEARNING_LOOP_PUBLIC_FIELDS)
PHASE6_CERTIFICATION_PUBLIC_REQUIRED_FIELDS = set(PHASE6_CERTIFICATION_PUBLIC_FIELDS)
PHASE7_DEMO_PROOF_PUBLIC_REQUIRED_FIELDS = set(PHASE7_DEMO_PROOF_PUBLIC_FIELDS)

PAPEROPS_30_DAY_OPERATIONS_PUBLIC_REQUIRED_FIELDS = {
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
    "paperops_submit_regression_guard_blocker_count",
    "paperops_submit_regression_guard_duplicate_misclassified_as_fresh_count",
    "paperops_submit_regression_guard_duplicate_submit_record_count",
    "paperops_submit_regression_guard_fresh_eligible_submit_record_count",
    "paperops_submit_regression_guard_fresh_submitted_ledger_collision_count",
    "paperops_submit_regression_guard_source_stale_after_post_count",
    "paperops_submit_regression_guard_status",
    "paperops_submit_regression_guard_validation_error_count",
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

PAPEROPS_COCKPIT_NOTIFICATION_UPGRADE_PUBLIC_REQUIRED_FIELDS = set(
    PAPEROPS_COCKPIT_NOTIFICATION_UPGRADE_PUBLIC_FIELDS
)
PAPER_LIVE_CERTIFICATION_PUBLIC_REQUIRED_FIELDS = set(
    PAPER_LIVE_CERTIFICATION_PUBLIC_FIELDS
)

PAPEROPS_QUALIFIED_SETUP_PRODUCTION_PUBLIC_REQUIRED_FIELDS = {
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

PAPEROPS_AUTO_APPROVAL_STAGED_ORDER_PUBLIC_REQUIRED_FIELDS = {
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

PAPEROPS_ALPACA_SUBMIT_ENABLEMENT_PUBLIC_REQUIRED_FIELDS = {
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

PAPEROPS_LIFECYCLE_POLLING_ENABLEMENT_PUBLIC_REQUIRED_FIELDS = {
    "active_lifecycle_polling_enabled",
    "alpaca_api_key_configured",
    "alpaca_api_secret_configured",
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

PAPEROPS_GUARDED_EXIT_ENABLEMENT_PUBLIC_REQUIRED_FIELDS = {
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

PAPEROPS_ACTIVE_AUTOMATION_PUBLIC_REQUIRED_FIELDS = {
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

PROHIBITED_VALUE_PATTERNS = (
    re.compile(r"[A-Z0-9._%+\-]+@[A-Z0-9.\-]+\.[A-Z]{2,}", re.IGNORECASE),
    re.compile(r"sk-[A-Za-z0-9_\-]{20,}"),
    re.compile(r"ghp_[A-Za-z0-9_]{20,}"),
    re.compile(r"vcp_[A-Za-z0-9_]{20,}"),
    re.compile(r"AIza[0-9A-Za-z_\-]{20,}"),
    re.compile(r"sb_secret_[0-9A-Za-z_\-]{12,}"),
    re.compile(r"PVZ[0-9A-Za-z_\-]{20,}"),
    re.compile(r"\d{6,}:[A-Za-z0-9_\-]{20,}"),
    re.compile(r"@[A-Za-z0-9_]{5,}"),
)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _iso_age_seconds(value: str | None) -> int | None:
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return max(0, int((datetime.now(timezone.utc) - parsed.astimezone(timezone.utc)).total_seconds()))


def _read_runtime_json(settings: Settings, filename: str) -> dict[str, Any] | None:
    path = Path(settings.runtime_dir) / filename
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def _dashboard_status(raw_status: str) -> str:
    if raw_status in {
        "registered",
        "manifest_ready",
        "enforced",
        "shadow_ready",
        "test_data_ready",
        "sample_ready",
        "live_optional",
        "read_only_ready",
        "ready_classical_fallback",
        "local_bridge_connected",
        "local_bridge_sample_ready",
        "sample_ready",
        "oracle_ready",
        "ok",
        "dry_run",
        "shell",
    }:
        return "online"
    if raw_status in {"pending", "not_started"}:
        return "pending"
    if raw_status in {"disabled", "live_blocked", "blocked_foundation_phase", "blocked_first_release"}:
        return "blocked"
    if raw_status in {
        "jsonl_fallback",
        "local",
        "local_bridge_required",
        "local_bridge_configured_pending_probe",
        "configured_pending_probe",
        "foundational_prior",
    }:
        return "local_only"
    if raw_status in {
        "credential_gated",
        "unavailable_missing_credentials",
        "unavailable_provider_endpoint_unconfirmed",
        "not_running",
        "degraded",
    }:
        return "degraded"
    if raw_status in {
        "deferred",
        "ready_to_build",
        "ready_to_port",
        "fallback_only",
        "derived",
        "intentionally_disabled",
        "needs_adapter",
        "provider_decision_required",
    }:
        return "pending"
    return "pending"


def _module_authority(module_key: str, raw_status: str) -> str:
    if module_key in {
        "execution_registry",
        "risk_agent",
        "execution_policy",
        "staged_order_contract",
        "broker_reconciliation",
        "paper_submit_receipt",
        "quantum_oracle",
        "trade_layer",
    }:
        return "write_blocked"
    if module_key == "telegram_bot":
        return "notify_only"
    if module_key == "live_bridge":
        return "read_only"
    if module_key in {
        "research_analyst",
        "strategy_lead",
        "head_of_quant",
        "shadow_intelligence",
        "signal_integrity_gate",
        "yahoo_finance_adapter",
    }:
        return "non_executable"
    if raw_status in {"disabled", "live_blocked"}:
        return "blocked"
    return "read_only"


def _module_process(module_key: str, raw_status: str) -> str:
    if module_key == "research_analyst" and raw_status == "shadow_ready":
        return "local shadow assessments available"
    if module_key == "strategy_lead" and raw_status == "shadow_ready":
        return "frontier challenge packets queued"

    processes = {
        "coo": "supervising local modules",
        "event_log": "recording local audit trail",
        "knowledge_graph": "holding local memory shell",
        "research_analyst": "waiting for local LLM readiness",
        "strategy_lead": "waiting for frontier model probe",
        "head_of_quant": "weekly quantum/classical oracle check",
        "execution_registry": "execution disabled in foundation mode",
        "agent_os": "manifest permissions available",
        "agent_runtime": "broker-write tools blocked",
        "shadow_intelligence": "shadow-only review packets available",
        "signal_integrity_gate": "auditing shadow signals without trade authority",
        "risk_agent": "reviewing policy without order authority",
        "execution_policy": "checking kill switches without order authority",
        "staged_order_contract": "describing disabled paper-order staging",
        "broker_reconciliation": "checking broker echo and reconciliation prerequisites",
        "paper_submit_receipt": "checking dry-run paper-submit receipt prerequisites",
        "telegram_bot": "outbound dry-run member communications",
        "live_bridge": "serving authenticated public-safe status snapshots",
        "yahoo_finance_adapter": "supplemental market confirmation; live reads deferred until dependency gate is green",
        "cockpit": "static live shell frozen",
    }
    return processes.get(module_key, raw_status.replace("_", " "))


def _build_modules(health: dict[str, Any], generated_at: str) -> list[dict[str, Any]]:
    modules: list[dict[str, Any]] = []
    for module in health.get("modules", []):
        raw_status = str(module.get("status", "pending"))
        module_key = str(module.get("key", "unknown"))
        dashboard_status = _dashboard_status(raw_status)
        modules.append(
            {
                "key": module_key,
                "label": str(module.get("label", module_key)),
                "owner": str(module.get("owner", "unknown")),
                "status": dashboard_status,
                "raw_status": raw_status,
                "last_heartbeat": generated_at,
                "current_process": _module_process(module_key, raw_status),
                "authority": _module_authority(module_key, raw_status),
                "local_only": module_key
                in {
                    "event_log",
                    "knowledge_graph",
                    "governance_forum",
                    "world_model",
                    "ingestion_spine",
                    "telegram_bot",
                    "live_bridge",
                },
            }
        )
    return modules


def _d1_snapshot_contract(generated_at: str) -> dict[str, Any]:
    return {
        "phase": "D1",
        "status": "public_safe_snapshot_ready",
        "generated_at": generated_at,
        "read_only": True,
        "public_safe": True,
        "source_of_truth": "local_qadam_runtime_export",
        "browser_authority": "read_only",
        "local_orchestrator_exposed": False,
        "landing_copy": "landing-page-repo/status/cockpit-status.json",
        "runtime_copy": "data/runtime/cockpit-status.json",
        "sanitizer_rules": [
            "no_tokens",
            "no_secret_names",
            "no_allowlist_emails",
            "no_local_absolute_paths",
            "no_raw_payloads",
            "no_browser_to_broker_authority",
        ],
    }


def _credential_status(source: dict[str, Any]) -> str:
    if source.get("selection_status") in {"optional_disabled", "not_selected"}:
        return "not_required"
    if source.get("action_category") in {
        "intentionally_disabled",
        "needs_adapter",
        "provider_decision_required",
    }:
        return "not_required"
    if source.get("auth") in {"none", "public"}:
        return "not_required"
    if source.get("missing_secrets"):
        return "missing"
    if source.get("configured_secrets"):
        return "configured"
    return "unknown"


def _public_auth_class(source: dict[str, Any]) -> str:
    auth = str(source.get("auth") or "").lower()
    if auth in {"none", "public"}:
        return "public_or_none"
    if any(term in auth for term in ("api key", "bearer", "token", "session", "oauth", "password")):
        return "credential_required"
    if any(term in auth for term in ("browser", "account", "login")):
        return "account_required"
    if "local" in auth:
        return "local_bridge"
    return "review_required"


def _readiness_label(source: dict[str, Any], runtime_status: str) -> str:
    provider_decision_status = str(source.get("provider_decision_status") or "")
    if source.get("promoted_adapter") and runtime_status == "live_optional":
        return "adapter ready"
    if runtime_status == "local_bridge_connected":
        return "local bridge connected"
    if runtime_status == "local_bridge_sample_ready":
        return "sample context available"
    if runtime_status == "local_bridge_configured_pending_probe":
        return "local bridge configured"
    if runtime_status == "unavailable_missing_credentials":
        return "credential required"
    if runtime_status == "unavailable_provider_endpoint_unconfirmed":
        return "provider endpoint required"
    if runtime_status == "deferred":
        return "deferred"
    if runtime_status == "local_bridge_required":
        return "local bridge required"
    if runtime_status == "fallback_only":
        return "fallback only"
    if runtime_status == "intentionally_disabled":
        if provider_decision_status == "marketplace_disabled_no_provider":
            return "marketplace disabled"
        return "optional disabled"
    if runtime_status == "needs_adapter":
        if provider_decision_status.startswith("provider_selected"):
            return "provider selected, adapter not built"
        return "adapter not built"
    if runtime_status == "provider_decision_required":
        return "provider decision required"
    if runtime_status == "derived":
        return "derived signal"
    if runtime_status in {"ready_to_build", "ready_to_port"}:
        return runtime_status.replace("_", " ")
    return runtime_status.replace("_", " ")


def _float_or_none(value: Any) -> float | None:
    try:
        if value is None or value == "":
            return None
        return float(value)
    except (TypeError, ValueError):
        return None


def _source_influence_profile(source: dict[str, Any], runtime_status: str) -> dict[str, Any]:
    status = _dashboard_status(runtime_status)
    credential_status = _credential_status(source)
    promoted_adapter = bool(source.get("promoted_adapter"))
    trust_score = _float_or_none(source.get("trust_score"))
    credential_ready = credential_status != "missing"
    action_category = str(source.get("action_category") or "")
    provider_decision_status = str(source.get("provider_decision_status") or "")
    selected = source.get("selection_status") not in {"optional_disabled", "not_selected"}
    usable_for_research = (
        selected
        and
        promoted_adapter
        and credential_ready
        and status in {"online", "local_only"}
    )
    eligible_for_signal_review = (
        usable_for_research
        and status == "online"
        and trust_score is not None
        and trust_score >= 0.5
    )
    if eligible_for_signal_review:
        influence_boundary = "research_context_and_signal_review_only_no_order_authority"
    elif usable_for_research:
        influence_boundary = "research_context_only_until_signal_integrity_quality_threshold"
    elif action_category == "intentionally_disabled":
        if provider_decision_status == "marketplace_disabled_no_provider":
            influence_boundary = "marketplace_disabled_no_source_quorum_role"
        else:
            influence_boundary = "optional_source_intentionally_disabled_not_used_for_research"
    elif provider_decision_status.startswith("provider_selected"):
        influence_boundary = "provider_selected_pending_readonly_adapter"
    elif provider_decision_status.startswith("local_bridge"):
        influence_boundary = "local_bridge_orderflow_context_only_no_order_authority"
    elif action_category in {"needs_adapter", "provider_decision_required"}:
        influence_boundary = "source_not_selected_until_adapter_or_provider_decision"
    elif runtime_status == "unavailable_provider_endpoint_unconfirmed":
        influence_boundary = "blocked_until_provider_endpoint_confirmed"
    elif not credential_ready:
        influence_boundary = "blocked_missing_credentials"
    elif not promoted_adapter:
        influence_boundary = "observation_only_until_adapter_promotion"
    else:
        influence_boundary = "observation_only_until_freshness_or_quality_threshold"
    return {
        "usable_for_research_context": usable_for_research,
        "eligible_for_signal_review": eligible_for_signal_review,
        "can_influence_signals": eligible_for_signal_review,
        "can_authorize_orders": False,
        "order_authority_boundary": "no_source_can_authorize_orders_or_broker_writes",
        "influence_boundary": influence_boundary,
    }


def _tradingview_watching_row(settings: Settings) -> dict[str, Any]:
    summary = tradingview_alert_summary(settings)
    alert_count = int(summary.get("alert_count", 0) or 0)
    status = "online" if alert_count else "pending"
    return {
        "source_key": "tradingview_paid_alerts",
        "source_name": "TradingView Paid Alerts",
        "pipeline": "market",
        "tier": 2,
        "status": status,
        "raw_status": summary.get("status", "not_initialized"),
        "registry_status": "d7_local_contract",
        "readiness": "observed alert source" if alert_count else "secure receiver pending",
        "promoted_adapter": bool(alert_count),
        "auth_class": "account_required",
        "cadence": "event-driven from paid TradingView alerts",
        "endpoint_count": 0,
        "degraded_reason": None if alert_count else "no alert snapshot yet",
        "trust_score": None,
        "last_heartbeat": summary.get("latest_observed_at"),
        "last_payload_time": summary.get("latest_observed_at"),
        "credential_status": "receiver_pending",
        "latency_ms": None,
        "selection_status": "selected",
        "operator_action": "connect_paid_tradingview_alert_snapshot",
        "action_category": "needs_credentials",
        "usable_for_research_context": bool(alert_count),
        "eligible_for_signal_review": False,
        "can_influence_signals": False,
        "can_authorize_orders": False,
        "order_authority_boundary": "no_source_can_authorize_orders_or_broker_writes",
        "influence_boundary": "observed_signal_only_no_execution_path",
    }


def _tradingview_mcp_watching_row(settings: Settings) -> dict[str, Any]:
    summary = tradingview_mcp_adapter_status(settings)
    connected = bool(summary.get("connected"))
    context_count = int(summary.get("technical_context_count", 0) or 0)
    return {
        "source_key": "tradingview_mcp",
        "source_name": "TradingView MCP Technical Analysis",
        "pipeline": "market",
        "tier": 2,
        "status": "online" if connected else "degraded",
        "raw_status": summary.get("status", "degraded"),
        "registry_status": "read_only_mcp_adapter",
        "readiness": "technical analysis connected"
        if connected
        else "local MCP server not connected",
        "promoted_adapter": connected,
        "auth_class": "public_or_none",
        "cadence": "read-only technical scan when called by Qadam",
        "endpoint_count": 0,
        "degraded_reason": None if connected else "local TradingView MCP checkout unavailable",
        "trust_score": None,
        "last_heartbeat": None,
        "last_payload_time": None,
        "credential_status": "not_required",
        "latency_ms": None,
        "selection_status": "selected",
        "operator_action": "none",
        "action_category": "no_user_action",
        "usable_for_research_context": connected,
        "eligible_for_signal_review": False,
        "can_influence_signals": False,
        "can_authorize_orders": False,
        "order_authority_boundary": "no_source_can_authorize_orders_or_broker_writes",
        "influence_boundary": (
            "supplemental_technical_confirmation_no_source_quorum_or_order_authority"
        ),
        "technical_context_count": context_count,
    }


def _build_watching(data_map: dict[str, Any], settings: Settings) -> list[dict[str, Any]]:
    watching: list[dict[str, Any]] = []
    for source in data_map.get("sources", []):
        runtime_status = str(source.get("runtime_status", "registered"))
        bookmap_summary = (
            bookmap_local_bridge_status(settings)
            if source.get("source_key") == "bookmap"
            else {}
        )
        influence_profile = _source_influence_profile(source, runtime_status)
        row = {
                "source_key": source.get("source_key"),
                "source_name": source.get("source_name"),
                "pipeline": source.get("pipeline"),
                "tier": source.get("tier"),
                "status": _dashboard_status(runtime_status),
                "raw_status": runtime_status,
                "registry_status": source.get("registry_status"),
                "readiness": _readiness_label(source, runtime_status),
                "promoted_adapter": bool(source.get("promoted_adapter")),
                "auth_class": _public_auth_class(source),
                "cadence": source.get("cadence"),
                "endpoint_count": source.get("endpoint_count"),
                "degraded_reason": source.get("degraded_reason"),
                "trust_score": source.get("trust_score"),
                "last_heartbeat": source.get("checked_at"),
                "last_payload_time": None,
                "credential_status": _credential_status(source),
                "credential_bound": bool(source.get("credential_bound")),
                "credential_activation_state": source.get("credential_activation_state"),
                "credential_activation_ready": bool(source.get("credential_activation_ready")),
                "provider_decision_status": source.get("provider_decision_status"),
                "provider_selected_provider": source.get("provider_selected_provider"),
                "provider_activation_state": source.get("provider_activation_state"),
                "provider_decision_boundary": source.get("provider_decision_boundary"),
                "latency_ms": None,
                "selection_status": source.get("selection_status", "selected"),
                "operator_action": source.get("operator_action", "none"),
                "action_category": source.get("action_category", "no_user_action"),
                **influence_profile,
            }
        if source.get("source_key") == "bookmap":
            row.update(
                {
                    "status": _dashboard_status(str(bookmap_summary.get("runtime_status") or runtime_status)),
                    "raw_status": bookmap_summary.get("runtime_status") or runtime_status,
                    "readiness": (
                        "Bookmap local bridge connected"
                        if bookmap_summary.get("connected")
                        else (
                            "Bookmap sample context available"
                            if bookmap_summary.get("status") == "sample_ready"
                            else "Bookmap local bridge required"
                        )
                    ),
                    "credential_status": "not_required",
                    "degraded_reason": bookmap_summary.get("degraded_reason"),
                    "bookmap_local_bridge_status": bookmap_summary.get("status"),
                    "bookmap_local_bridge_connected": bool(bookmap_summary.get("connected")),
                    "bookmap_live_probe_enabled": bool(bookmap_summary.get("live_probe_enabled")),
                    "bookmap_orderflow_context_count": int(
                        bookmap_summary.get("orderflow_context_count", 0) or 0
                    ),
                    "bookmap_orderflow_confirmation_role": (
                        "supplemental_orderflow_confirmation_only"
                    ),
                    "bookmap_order_injection_allowed": False,
                    "bookmap_trading_mode_allowed": False,
                    "can_influence_signals": False,
                    "eligible_for_signal_review": False,
                    "influence_boundary": (
                        "supplemental_orderflow_confirmation_no_source_quorum_or_order_authority"
                    ),
                }
            )
        watching.append(row)
    watching.append(_tradingview_mcp_watching_row(settings))
    watching.append(_tradingview_watching_row(settings))
    return watching


def _safe_yahoo_finance_status(settings: Settings, generated_at: str) -> dict[str, Any]:
    status = yahoo_finance_adapter_status(settings)
    enabled = bool(status.get("enabled"))
    dependency_importable = bool(status.get("dependency_importable"))
    if enabled and dependency_importable:
        public_status = "live_read_only_ready"
        degraded = False
        degraded_reason = None
    elif not enabled:
        public_status = "deferred"
        degraded = True
        degraded_reason = "disabled:YFINANCE_ENABLED_false"
    else:
        public_status = "degraded"
        degraded = True
        degraded_reason = f"missing_dependency:{status.get('missing_dependency') or 'yfinance'}"
    return {
        "schema_version": 1,
        "source": status.get("source", "market.yahoo_finance"),
        "classification": status.get("classification", "accepted_supplemental_pending_live_dependencies"),
        "status": public_status,
        "enabled": enabled,
        "live_read_enabled": enabled and dependency_importable,
        "live_read_deferred": not (enabled and dependency_importable),
        "sample_mode_available": True,
        "last_check_at": generated_at,
        "symbol_allowlist_count": int(status.get("symbol_allowlist_count", 0) or 0),
        "canonical_source_count": int(status.get("canonical_source_count", 0) or 0),
        "canonical_source": False,
        "market_confirmation_role": "supplemental_market_confirmation",
        "market_confirmation_policy": "corroboration_only_hold_when_stale_unavailable_or_single_source",
        "degraded": degraded,
        "degraded_reason": degraded_reason,
        "public_safe": True,
        "raw_payload_exposed": False,
        "raw_archive_path_exposed": False,
        "cache_path_exposed": False,
        "cookies_exposed": False,
        "crumb_tokens_exposed": False,
        "scraped_html_exposed": False,
        "signal_authority": False,
        "risk_approval_authority": False,
        "order_authority": False,
        "broker_write_authority": False,
        "broker_echo_authority": False,
        "fill_confirmation_authority": False,
        "receipt_evidence_authority": False,
        "reconciliation_truth_authority": False,
        "live_capital_authority": False,
        "boundary": (
            "Yahoo Finance is read-only supplemental market confirmation. It cannot create "
            "signals, approve risk, create orders, provide broker echo, confirm fills, create "
            "receipt evidence, provide reconciliation truth, enable live capital, or expose raw provider internals."
        ),
    }


def _read_public_runtime_artifact(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return payload if isinstance(payload, dict) else {}


def _preference_last_successful_at(artifact: dict[str, Any], allowed_statuses: set[str]) -> str | None:
    if artifact.get("public_safe") is not True:
        return None
    if artifact.get("validation_errors"):
        return None
    if str(artifact.get("status") or "") not in allowed_statuses:
        return None
    generated_at = artifact.get("generated_at")
    return str(generated_at) if isinstance(generated_at, str) and generated_at.strip() else None


def _safe_preference_mcp_status(settings: Settings, generated_at: str) -> dict[str, Any]:
    identity = _read_public_runtime_artifact(Path(settings.runtime_dir) / "preference_mcp_identity_status.json")
    if not identity:
        identity = build_preference_mcp_identity_status(
            settings=settings,
            live_status_check=False,
            record_event=False,
        )

    catalog_path, _ = preference_tool_catalog_paths(settings)
    catalog = _read_public_runtime_artifact(catalog_path)
    if not catalog:
        catalog = build_preference_tool_catalog(
            settings=settings,
            identity_status=identity,
            record_event=False,
        )

    domain_path, _ = preference_domain_pack_paths(settings)
    domain_packs = _read_public_runtime_artifact(domain_path)
    if not domain_packs:
        domain_packs = build_preference_domain_pack_mapping(settings=settings)

    provenance_path, _ = preference_provenance_paths(settings)
    provenance = _read_public_runtime_artifact(provenance_path)

    shadow_path, _ = preference_shadow_context_paths(settings)
    shadow_context = _read_public_runtime_artifact(shadow_path)

    source_promotion_path, _ = preference_source_promotion_paths(settings)
    source_promotion = _read_public_runtime_artifact(source_promotion_path)

    approved_domain_packs = [
        str(domain_pack)
        for domain_pack in domain_packs.get("unique_domain_packs", [])
        if str(domain_pack).strip()
    ]
    quota_degraded = (
        identity.get("status") != "verified_non_anonymous"
        or identity.get("quota_metadata_present") is not True
    )
    quota_status = (
        "verified"
        if not quota_degraded
        else "disabled_live_mode"
        if not settings.preference_mcp_enabled
        else "blocked_pending_verified_identity"
    )
    shadow_status = str(shadow_context.get("status") or "not_run")
    catalog_status = str(catalog.get("status") or "not_run")
    domain_status = str(domain_packs.get("status") or "not_run")
    provenance_status = str(provenance.get("status") or "not_run")

    if shadow_status == "challenge_only_ready":
        public_status = "challenge_only_ready"
    elif domain_status == "validated" or catalog_status != "not_run":
        public_status = "catalog_only_ready"
    elif not settings.preference_mcp_enabled:
        public_status = "disabled"
    else:
        public_status = "degraded"

    degraded_reasons: list[str] = []
    if not settings.preference_mcp_enabled:
        degraded_reasons.append("live_mcp_disabled")
    if identity.get("status") != "verified_non_anonymous":
        degraded_reasons.append("identity_not_verified")
    if identity.get("quota_metadata_present") is not True:
        degraded_reasons.append("quota_metadata_missing")
    if catalog_status == "not_run":
        degraded_reasons.append("catalog_not_run")
    if domain_status != "validated":
        degraded_reasons.append("domain_packs_not_validated")
    if provenance_status != "validated":
        degraded_reasons.append("provenance_not_validated")
    if shadow_status != "challenge_only_ready":
        degraded_reasons.append("shadow_context_not_ready")

    authority_flags = {
        "live_mcp_call_allowed": False,
        "search_tools_allowed": False,
        "domain_tool_calls_allowed": False,
        "paid_tool_calls_allowed": False,
        "source_quorum_credit_allowed": False,
        "preference_only_confirmation_allowed": False,
        "trade_candidate_creation_allowed": False,
        "risk_handoff_allowed": False,
        "execution_allowed": False,
        "paper_order_allowed": False,
        "broker_write_allowed": False,
        "live_capital_enabled": False,
    }
    return {
        "schema_version": 1,
        "source_key": PREFERENCE_SOURCE_KEY,
        "provider_label": PREFERENCE_PROVIDER_LABEL,
        "classification": PREFERENCE_CLASSIFICATION,
        "status": public_status,
        "enabled": bool(settings.preference_mcp_enabled),
        "public_safe": True,
        "identity_status": str(identity.get("identity_status") or "not_verified"),
        "identity_gate_status": str(identity.get("status") or "blocked"),
        "quota_status": quota_status,
        "quota_degraded": quota_degraded,
        "quota_metadata_present": bool(identity.get("quota_metadata_present")),
        "daily_call_budget": int(identity.get("daily_call_budget") or settings.preference_mcp_daily_call_budget),
        "run_call_budget": int(identity.get("run_call_budget") or settings.preference_mcp_run_call_budget),
        "catalog_status": catalog_status,
        "catalog_entry_count": int(catalog.get("catalog_entry_count", 0) or 0),
        "blocked_paid_tool_count": int(catalog.get("blocked_paid_tool_count", 0) or 0),
        "domain_pack_status": domain_status,
        "domain_pack_count": int(domain_packs.get("unique_domain_pack_count", len(approved_domain_packs)) or 0),
        "approved_domain_pack_count": len(approved_domain_packs),
        "approved_domain_packs": approved_domain_packs,
        "first_trading_universe_strategy_family_count": int(
            domain_packs.get("strategy_family_count", 0) or 0
        ),
        "provenance_status": provenance_status,
        "provenance_context_status": str(provenance.get("preference_context_status") or "not_run"),
        "provenance_distinct_upstream_source_count": int(
            provenance.get("preference_distinct_upstream_source_count", 0) or 0
        ),
        "shadow_context_status": shadow_status,
        "shadow_context_role": str(shadow_context.get("context_role") or "not_run"),
        "shadow_observation_count": int(shadow_context.get("shadow_observation_count", 0) or 0),
        "active_required_challenge_count": int(
            shadow_context.get("active_required_challenge_count", 0) or 0
        ),
        "source_promotion_status": str(source_promotion.get("status") or "not_run"),
        "source_promotion_decision_count": int(
            source_promotion.get("decision_count", 0) or 0
        ),
        "source_promotion_promoted_decision_count": int(
            source_promotion.get("promoted_decision_count", 0) or 0
        ),
        "source_promotion_canonical_source_count_after": int(
            source_promotion.get("canonical_source_count_after", EXPECTED_SOURCE_COUNT)
            or EXPECTED_SOURCE_COUNT
        ),
        "last_successful_catalog_check": _preference_last_successful_at(
            catalog,
            {"blocked_pending_verified_identity", "catalog_schema_ready_pending_live_discovery"},
        ),
        "last_successful_domain_pack_check": _preference_last_successful_at(domain_packs, {"validated"}),
        "last_successful_provenance_check": _preference_last_successful_at(provenance, {"validated"}),
        "last_successful_shadow_context_check": _preference_last_successful_at(
            shadow_context,
            {"challenge_only_ready"},
        ),
        "degraded": bool(degraded_reasons),
        "degraded_reason": ",".join(degraded_reasons) if degraded_reasons else None,
        "paid_tools_allowed": False,
        **authority_flags,
        "authority_flags": authority_flags,
        "raw_key_exposed": False,
        "raw_prompt_exposed": False,
        "raw_payload_exposed": False,
        "private_source_payload_exposed": False,
        "boundary": (
            "Preference/PREF MCP is a public-safe read-only supplemental data plane. "
            "It can show identity, quota, catalog, domain-pack, provenance, and shadow-context "
            "posture without secrets, raw prompts, raw payloads, or private source payloads. "
            "It cannot satisfy source quorum, create trade candidates, approve risk, submit "
            "paper orders, write brokers, confirm fills, provide reconciliation truth, call "
            "quantum providers, enable schedulers, or enable live capital."
        ),
        "last_check_at": generated_at,
    }


def _build_source_pipeline_summary(watching: list[dict[str, Any]]) -> list[dict[str, Any]]:
    pipelines: dict[str, dict[str, Any]] = {}
    for source in watching:
        pipeline = str(source.get("pipeline") or "unknown")
        current = pipelines.setdefault(
            pipeline,
            {
                "pipeline": pipeline,
                "source_count": 0,
                "online_count": 0,
                "degraded_count": 0,
                "pending_count": 0,
                "local_only_count": 0,
                "missing_credential_count": 0,
                "adapter_ready_count": 0,
                "intentionally_disabled_count": 0,
                "needs_adapter_count": 0,
                "provider_decision_required_count": 0,
                "local_bridge_required_count": 0,
                "provider_decision_count": 0,
                "provider_selected_pending_adapter_count": 0,
                "provider_decision_marketplace_disabled_count": 0,
                "provider_decision_local_bridge_count": 0,
            },
        )
        current["source_count"] += 1
        if source.get("status") == "online":
            current["online_count"] += 1
        elif source.get("status") == "degraded":
            current["degraded_count"] += 1
        elif source.get("status") == "pending":
            current["pending_count"] += 1
        elif source.get("status") == "local_only":
            current["local_only_count"] += 1
        if source.get("credential_status") == "missing":
            current["missing_credential_count"] += 1
        if source.get("promoted_adapter"):
            current["adapter_ready_count"] += 1
        action_category = source.get("action_category")
        if action_category == "intentionally_disabled":
            current["intentionally_disabled_count"] += 1
        elif action_category == "needs_adapter":
            current["needs_adapter_count"] += 1
        elif action_category == "provider_decision_required":
            current["provider_decision_required_count"] += 1
        elif action_category == "local_bridge_required":
            current["local_bridge_required_count"] += 1
        provider_decision_status = str(source.get("provider_decision_status") or "")
        if provider_decision_status:
            current["provider_decision_count"] += 1
        if provider_decision_status.startswith("provider_selected"):
            current["provider_selected_pending_adapter_count"] += 1
        elif provider_decision_status == "marketplace_disabled_no_provider":
            current["provider_decision_marketplace_disabled_count"] += 1
        elif provider_decision_status.startswith("local_bridge"):
            current["provider_decision_local_bridge_count"] += 1
    return [pipelines[key] for key in sorted(pipelines)]


def _build_source_heartbeat_history(settings: Settings) -> list[dict[str, Any]]:
    store = SourceHeartbeatStore(settings=settings)
    try:
        runs = store.read_runs()[-5:]
    except Exception:
        return []
    history: list[dict[str, Any]] = []
    for run in runs:
        summary = run.get("summary", {})
        history.append(
            {
                "checked_at": run.get("checked_at"),
                "source_count": summary.get("source_count"),
                "promoted_adapter_count": summary.get("promoted_adapter_count"),
                "deferred_count": summary.get("deferred_count"),
                "missing_credential_source_count": summary.get("missing_credential_source_count"),
                "by_runtime_status": summary.get("by_runtime_status", {}),
                "by_pipeline": summary.get("by_pipeline", {}),
            }
        )
    return history


def _decision_philosophy() -> dict[str, Any]:
    summary = world_model_summary()
    claims = world_model_claims()
    ai_infrastructure_lens = {
        "status": "active_strategy_lens",
        "name": "Second-order AI infrastructure beneficiary lens",
        "thesis": (
            "Qadam treats obvious AI leaders as reference assets and asks where the AI buildout "
            "creates harder-to-price physical bottlenecks: electricity, grid equipment, data-centre "
            "electrical systems, fabrication capacity, memory, connectivity, and networking."
        ),
        "reference_assets": [
            "Nvidia and other obvious AI leaders",
            "mega-cap AI platform winners",
            "AI-linked benchmark baskets",
        ],
        "target_bottlenecks": [
            "power generation",
            "grid hardware",
            "data-centre electrical infrastructure",
            "semiconductor fabrication capacity",
            "memory bandwidth and storage",
            "connectivity and networking",
        ],
        "decision_questions": [
            "Is the visible AI winner already priced more efficiently than the supplier constraint?",
            "Which bottleneck is binding first: power, fab capacity, memory, networking, or policy?",
            "Is the beneficiary directly exposed to the constraint or only narratively adjacent?",
            "Does live evidence show orders, capex, pricing power, policy support, or supply scarcity?",
            "Does Akber's 6-stage filter still confirm timing, risk, and execution quality?",
        ],
        "strategy_role": "worldview_prior_and_strategy_emphasis",
        "gating_role": (
            "This lens can shape research goals, evidence packets, Strategy Lead challenges, and candidate "
            "comparison. It cannot create a trade, approve risk, stage an order, submit to Alpaca, or enable live capital."
        ),
        "risk_controls": [
            "reject narrative-only AI exposure",
            "compare against obvious AI leader reference performance",
            "require source-quality and durable replay support",
            "require Signal Integrity, Risk Agent, Execution Policy, and paper-account checks",
        ],
        "boundary": (
            "The AI infrastructure lens is a private strategy prior and comparison tool. It is not a standalone "
            "buy signal and does not override Qadam's existing strategy, Akber filter, or safety gates."
        ),
    }
    active_lenses = [
        {
            "key": claim.get("key"),
            "claim_type": claim.get("claim_type"),
            "claim": claim.get("claim"),
            "mechanism": claim.get("mechanism"),
            "actors": claim.get("actors", []),
            "observable_signatures": claim.get("observable_signatures", []),
            "live_sources_to_check": claim.get("live_sources_to_check", []),
            "market_channels": claim.get("market_channels", []),
            "corroboration_status": claim.get("corroboration_status"),
            "evidence_boundary": claim.get("evidence_boundary"),
        }
        for claim in claims
    ]
    return {
        "status": summary.get("status", "ok"),
        "corpus": "how-the-world-works",
        "corpus_file_count": summary.get("corpus_file_count", 0),
        "claim_count": summary.get("claim_count", 0),
        "foundational_prior_count": summary.get("foundational_prior_count", 0),
        "role": "private_worldview_prior",
        "trading_philosophy": (
            "Qadam starts from a power-map worldview: energy, security, money, institutional "
            "incentives, narrative control, and hidden coordination shape what markets price late. "
            "Inside the AI infrastructure buildout, it now treats obvious AI leaders as reference "
            "assets and looks for second-order infrastructure beneficiaries in power generation, "
            "grid hardware, data-centre electrical systems, fabrication capacity, memory, connectivity, "
            "and networking. "
            "The worldview powers questions and scenario generation, but live evidence, the Akber "
            "filter, Signal Integrity Gate, and Risk Agent decide whether anything can move toward a trade."
        ),
        "decision_chain": [
            "private worldview prior",
            "observable signatures",
            "second-order beneficiary check",
            "live-source corroboration",
            "Akber 6-stage filter",
            "Signal Integrity Gate",
            "Risk Agent",
            "paper trade or postmortem",
        ],
        "ai_infrastructure_lens": ai_infrastructure_lens,
        "active_lenses": active_lenses,
        "default_decision_context": [
            "power hierarchy",
            "narrative asymmetry",
            "institutional incentive",
            "US-China grand-bargain scenario",
            "hidden coordination risk",
            "AI infrastructure capacity constraints",
        ],
        "boundary": summary.get(
            "evidence_boundary",
            "World-model claims are private priors, not factual evidence or trade triggers.",
        ),
    }


def _event_summary(entry: Any) -> str:
    event_type = getattr(entry, "event_type", "event")
    component = getattr(entry, "component", "system")
    severity = getattr(entry, "severity", "info")
    return f"{component}: {event_type} ({severity})"


def _build_process_console(settings: Settings, generated_at: str) -> list[dict[str, str]]:
    event_log = EventLog(echo=False)
    try:
        entries = event_log.read_entries()[-8:]
    except Exception:
        entries = ()
    if entries:
        return [
            {
                "timestamp": entry.created_at,
                "component": entry.component,
                "severity": entry.severity,
                "message": _event_summary(entry),
            }
            for entry in entries
        ]
    return [
        {
            "timestamp": generated_at,
            "component": "cockpit",
            "severity": "info",
            "message": "cockpit: static shell frozen; waiting for local status snapshots",
        },
        {
            "timestamp": generated_at,
            "component": "execution",
            "severity": "warning",
            "message": f"execution: paper mode only; live capital disabled for GBP {settings.trial_balance_gbp} trial",
        },
    ]


def _safe_evidence_packet(signal: dict[str, Any]) -> dict[str, Any]:
    return normalize_signal_evidence_packet(signal)


def _safe_shadow_packets(settings: Settings) -> list[dict[str, Any]]:
    try:
        packets = list(read_research_shadow_triage_queue(settings))[-5:]
    except Exception:
        packets = []
    return [
        {
            "packet_id": packet.get("packet_id"),
            "agent_key": packet.get("agent_key"),
            "status": packet.get("status"),
            "summary": packet.get("summary"),
            "uncertainty": packet.get("uncertainty"),
            "source_event_refs": packet.get("source_event_refs", []),
            "created_at": packet.get("created_at"),
            "boundary": packet.get("boundary"),
        }
        for packet in packets
    ]


def _safe_phase2_shadow_cycle(settings: Settings) -> dict[str, Any]:
    report_path = Path(settings.runtime_dir) / "phase2_shadow_cycle.json"
    fallback = {
        "status": "not_run",
        "mode": "not_run",
        "source_count": 0,
        "source_degraded_count": 0,
        "queued_packet_count": 0,
        "shadow_signal_count": 0,
        "durable_replay_requested": False,
        "durable_replay_status": "not_requested",
        "durable_replay_contract_status": "not_requested",
        "durable_replay_observation_count": 0,
        "durable_replay_replayed_source_count": 0,
        "durable_replay_missing_source_count": 0,
        "write_authority": False,
        "signal_authority": False,
        "order_authority": False,
        "execution_allowed": False,
        "paper_order_allowed": False,
        "strategy_lead_source_mode": "not_run",
        "strategy_lead_source_posture": "not_run",
        "strategy_lead_review_mode": "not_run",
        "strategy_lead_evidence_pressure": "not_run",
        "strategy_lead_required_challenge_count": 0,
        "strategy_lead_risk_handoff_allowed": False,
        "strategy_lead_trade_candidate_allowed": False,
        "research_goal_status": "not_run",
        "research_goal_hardening_version": "not_run",
        "research_goal_record_count": 0,
        "research_goal_active_count": 0,
        "research_goal_created_or_updated_count": 0,
        "research_goal_candidate_ready_count": 0,
        "research_goal_closed_no_trade_count": 0,
        "research_goal_stale_goal_count": 0,
        "research_goal_expired_goal_count": 0,
        "research_goal_average_priority_score": 0.0,
        "research_goal_by_priority_label": {},
        "research_goal_by_status": {},
        "research_goal_by_market_channel": {},
        "research_goal_recent_goals": [],
        "research_goal_execution_allowed_count": 0,
        "research_goal_paper_order_allowed_count": 0,
        "research_goal_trade_candidate_creation_allowed_count": 0,
        "research_goal_risk_handoff_allowed_count": 0,
        "research_goal_broker_write_allowed_count": 0,
        "research_goal_live_capital_enabled_count": 0,
        "boundary": "Phase 2 shadow cycle has not run in the current local snapshot.",
    }
    try:
        report = json.loads(report_path.read_text())
    except Exception:
        return fallback
    if not isinstance(report, dict):
        return fallback
    return {
        "status": report.get("status", "unknown"),
        "mode": report.get("mode", "unknown"),
        "source_count": int(report.get("source_count", 0) or 0),
        "source_degraded_count": int(report.get("source_degraded_count", 0) or 0),
        "queued_packet_count": int(report.get("queued_packet_count", 0) or 0),
        "shadow_signal_count": int(report.get("shadow_signal_count", 0) or 0),
        "strategy_lead_status": report.get("strategy_lead_status", "unknown"),
        "local_research_status": report.get("local_research_status", "unknown"),
        "signal_integrity_status": report.get("signal_integrity_status", "unknown"),
        "risk_agent_status": report.get("risk_agent_status", "unknown"),
        "execution_policy_status": report.get("execution_policy_status", "unknown"),
        "durable_replay_requested": bool(report.get("durable_replay_requested")),
        "durable_replay_status": report.get("durable_replay_status", "unknown"),
        "durable_replay_contract_status": report.get("durable_replay_contract_status", "unknown"),
        "durable_replay_observation_count": int(report.get("durable_replay_observation_count", 0) or 0),
        "durable_replay_replayed_source_count": int(report.get("durable_replay_replayed_source_count", 0) or 0),
        "durable_replay_missing_source_count": int(report.get("durable_replay_missing_source_count", 0) or 0),
        "write_authority": bool(report.get("durable_replay_write_authority")),
        "signal_authority": bool(report.get("durable_replay_signal_authority")),
        "order_authority": bool(report.get("durable_replay_order_authority")),
        "execution_allowed": bool(report.get("strategy_lead_execution_allowed")),
        "paper_order_allowed": bool(report.get("strategy_lead_paper_order_allowed")),
        "strategy_lead_source_mode": report.get("strategy_lead_source_mode", "unknown"),
        "strategy_lead_source_posture": report.get("strategy_lead_source_posture", "unknown"),
        "strategy_lead_review_mode": report.get("strategy_lead_review_mode", "unknown"),
        "strategy_lead_evidence_pressure": report.get("strategy_lead_evidence_pressure", "unknown"),
        "strategy_lead_required_challenge_count": int(
            report.get("strategy_lead_required_challenge_count", 0) or 0
        ),
        "strategy_lead_risk_handoff_allowed": bool(report.get("strategy_lead_risk_handoff_allowed")),
        "strategy_lead_trade_candidate_allowed": bool(report.get("strategy_lead_trade_candidate_allowed")),
        "research_goal_status": report.get("research_goal_status", "unknown"),
        "research_goal_hardening_version": report.get("research_goal_hardening_version", "unknown"),
        "research_goal_record_count": int(report.get("research_goal_record_count", 0) or 0),
        "research_goal_active_count": int(report.get("research_goal_active_count", 0) or 0),
        "research_goal_created_or_updated_count": int(
            report.get("research_goal_created_or_updated_count", 0) or 0
        ),
        "research_goal_candidate_ready_count": int(
            report.get("research_goal_candidate_ready_count", 0) or 0
        ),
        "research_goal_closed_no_trade_count": int(
            report.get("research_goal_closed_no_trade_count", 0) or 0
        ),
        "research_goal_stale_goal_count": int(report.get("research_goal_stale_goal_count", 0) or 0),
        "research_goal_expired_goal_count": int(report.get("research_goal_expired_goal_count", 0) or 0),
        "research_goal_average_priority_score": float(
            report.get("research_goal_average_priority_score", 0.0) or 0.0
        ),
        "research_goal_by_priority_label": report.get("research_goal_by_priority_label", {}),
        "research_goal_by_status": report.get("research_goal_by_status", {}),
        "research_goal_by_market_channel": report.get("research_goal_by_market_channel", {}),
        "research_goal_recent_goals": report.get("research_goal_recent_goals", []),
        "research_goal_execution_allowed_count": int(
            report.get("research_goal_execution_allowed_count", 0) or 0
        ),
        "research_goal_paper_order_allowed_count": int(
            report.get("research_goal_paper_order_allowed_count", 0) or 0
        ),
        "research_goal_trade_candidate_creation_allowed_count": int(
            report.get("research_goal_trade_candidate_creation_allowed_count", 0) or 0
        ),
        "research_goal_risk_handoff_allowed_count": int(
            report.get("research_goal_risk_handoff_allowed_count", 0) or 0
        ),
        "research_goal_broker_write_allowed_count": int(
            report.get("research_goal_broker_write_allowed_count", 0) or 0
        ),
        "research_goal_live_capital_enabled_count": int(
            report.get("research_goal_live_capital_enabled_count", 0) or 0
        ),
        "created_at": report.get("created_at"),
        "boundary": report.get(
            "boundary",
            "Phase 2 shadow cycle is read-only context and cannot create orders.",
        ),
    }


def _safe_signal_integrity_reviews(settings: Settings) -> list[dict[str, Any]]:
    try:
        reviews = list(SignalIntegrityReviewStore(settings=settings).read(limit=5))
    except Exception:
        reviews = []
    return [
        {
            "review_id": review.get("review_id"),
            "source_signal_id": review.get("source_signal_id"),
            "status": review.get("status"),
            "instrument_focus": review.get("instrument_focus"),
            "integrity_score": review.get("integrity_score"),
            "source_count": review.get("source_count"),
            "evidence_item_count": review.get("evidence_item_count"),
            "average_trust_score": review.get("average_trust_score"),
            "min_trust_score": review.get("min_trust_score"),
            "signal_confidence": review.get("signal_confidence"),
            "missing_correlations": review.get("missing_correlations", []),
            "akber_filter": review.get("akber_filter", {}),
            "market_confirmation_policy": review.get("market_confirmation_policy", {}),
            "technical_context_policy": review.get("technical_context_policy", {}),
            "failure_reasons": review.get("failure_reasons", []),
            "required_next_steps": review.get("required_next_steps", []),
            "worldview_prior_status": review.get("worldview_prior_status"),
            "execution_allowed": bool(review.get("execution_allowed")),
            "paper_order_allowed": bool(review.get("paper_order_allowed")),
            "trade_candidate_created": bool(review.get("trade_candidate_created")),
            "reviewed_at": review.get("reviewed_at"),
            "boundary": review.get("boundary"),
        }
        for review in reviews
    ]


def _safe_risk_policy_reviews(settings: Settings) -> list[dict[str, Any]]:
    try:
        reviews = list(RiskPolicyReviewStore(settings=settings).read(limit=5))
    except Exception:
        reviews = []
    return [
        {
            "review_id": review.get("review_id"),
            "source_type": review.get("source_type"),
            "source_ref": review.get("source_ref"),
            "status": review.get("status"),
            "instrument": review.get("instrument"),
            "policy_score": review.get("policy_score"),
            "proposed_risk_gbp": review.get("proposed_risk_gbp"),
            "proposed_risk_pct": review.get("proposed_risk_pct"),
            "max_risk_gbp": review.get("max_risk_gbp"),
            "max_risk_pct": review.get("max_risk_pct"),
            "checks": review.get("checks", {}),
            "blocked_reasons": review.get("blocked_reasons", []),
            "required_next_steps": review.get("required_next_steps", []),
            "paper_account_status": review.get("paper_account_status"),
            "signal_integrity_status": review.get("signal_integrity_status"),
            "execution_allowed": bool(review.get("execution_allowed")),
            "paper_order_allowed": bool(review.get("paper_order_allowed")),
            "order_created": bool(review.get("order_created")),
            "broker_write_allowed": bool(review.get("broker_write_allowed")),
            "reviewed_at": review.get("reviewed_at"),
            "boundary": review.get("boundary"),
        }
        for review in reviews
    ]


def _safe_execution_policy_reviews(settings: Settings) -> list[dict[str, Any]]:
    try:
        reviews = list(ExecutionPolicyReviewStore(settings=settings).read(limit=5))
    except Exception:
        reviews = []
    return [
        {
            "schema_version": review.get("schema_version"),
            "review_id": review.get("review_id"),
            "source_risk_review_id": review.get("source_risk_review_id"),
            "status": review.get("status"),
            "instrument": review.get("instrument"),
            "selected_venue": review.get("selected_venue"),
            "venue_mode": review.get("venue_mode"),
            "policy_score": review.get("policy_score"),
            "checks": review.get("checks", {}),
            "kill_switches": review.get("kill_switches", {}),
            "blocked_reasons": review.get("blocked_reasons", []),
            "required_next_steps": review.get("required_next_steps", []),
            "execution_allowed": bool(review.get("execution_allowed")),
            "staged_paper_order_allowed": bool(review.get("staged_paper_order_allowed")),
            "paper_order_created": bool(review.get("paper_order_created")),
            "broker_write_allowed": bool(review.get("broker_write_allowed")),
            "live_capital_enabled": bool(review.get("live_capital_enabled")),
            "reviewed_at": review.get("reviewed_at"),
            "boundary": review.get("boundary"),
        }
        for review in reviews
    ]


def _safe_staged_paper_order_reviews(settings: Settings) -> list[dict[str, Any]]:
    try:
        reviews = list(StagedPaperOrderReviewStore(settings=settings).read(limit=5))
    except Exception:
        reviews = []
    return [
        {
            "schema_version": review.get("schema_version"),
            "review_id": review.get("review_id"),
            "source_execution_policy_review_id": review.get("source_execution_policy_review_id"),
            "status": review.get("status"),
            "instrument": review.get("instrument"),
            "selected_venue": review.get("selected_venue"),
            "venue_mode": review.get("venue_mode"),
            "account_scope": review.get("account_scope"),
            "hypothetical_order": review.get("hypothetical_order", {}),
            "reconciliation_checks": review.get("reconciliation_checks", {}),
            "blocked_reasons": review.get("blocked_reasons", []),
            "required_next_steps": review.get("required_next_steps", []),
            "execution_allowed": bool(review.get("execution_allowed")),
            "staged_paper_order_created": bool(review.get("staged_paper_order_created")),
            "paper_order_submittable": bool(review.get("paper_order_submittable")),
            "broker_write_allowed": bool(review.get("broker_write_allowed")),
            "live_capital_enabled": bool(review.get("live_capital_enabled")),
            "reviewed_at": review.get("reviewed_at"),
            "boundary": review.get("boundary"),
        }
        for review in reviews
    ]


def _safe_broker_reconciliation_reviews(settings: Settings) -> list[dict[str, Any]]:
    try:
        reviews = list(BrokerReconciliationReviewStore(settings=settings).read(limit=5))
    except Exception:
        reviews = []
    return [
        {
            "schema_version": review.get("schema_version"),
            "review_id": review.get("review_id"),
            "source_staged_paper_order_review_id": review.get("source_staged_paper_order_review_id"),
            "source_execution_policy_review_id": review.get("source_execution_policy_review_id"),
            "status": review.get("status"),
            "instrument": review.get("instrument"),
            "selected_venue": review.get("selected_venue"),
            "venue_mode": review.get("venue_mode"),
            "account_scope": review.get("account_scope"),
            "hypothetical_order": review.get("hypothetical_order", {}),
            "broker_echo": review.get("broker_echo", {}),
            "reconciliation_checks": review.get("reconciliation_checks", {}),
            "blocked_reasons": review.get("blocked_reasons", []),
            "required_next_steps": review.get("required_next_steps", []),
            "idempotency_key_allocated": bool(review.get("idempotency_key_allocated")),
            "event_log_prewrite_created": bool(review.get("event_log_prewrite_created")),
            "pre_trade_snapshot_created": bool(review.get("pre_trade_snapshot_created")),
            "duplicate_order_guard_ready": bool(review.get("duplicate_order_guard_ready")),
            "broker_echo_verified": bool(review.get("broker_echo_verified")),
            "post_submit_reconciliation_ready": bool(review.get("post_submit_reconciliation_ready")),
            "postmortem_link_ready": bool(review.get("postmortem_link_ready")),
            "paper_order_submit_allowed": bool(review.get("paper_order_submit_allowed")),
            "broker_write_allowed": bool(review.get("broker_write_allowed")),
            "live_capital_enabled": bool(review.get("live_capital_enabled")),
            "reviewed_at": review.get("reviewed_at"),
            "boundary": review.get("boundary"),
        }
        for review in reviews
    ]


def _safe_paper_submit_receipt_reviews(settings: Settings) -> list[dict[str, Any]]:
    try:
        reviews = list(PaperSubmitReceiptReviewStore(settings=settings).read(limit=5))
    except Exception:
        reviews = []
    return [
        {
            "schema_version": review.get("schema_version"),
            "review_id": review.get("review_id"),
            "source_broker_reconciliation_review_id": review.get("source_broker_reconciliation_review_id"),
            "source_staged_paper_order_review_id": review.get("source_staged_paper_order_review_id"),
            "source_execution_policy_review_id": review.get("source_execution_policy_review_id"),
            "status": review.get("status"),
            "instrument": review.get("instrument"),
            "selected_venue": review.get("selected_venue"),
            "venue_mode": review.get("venue_mode"),
            "account_scope": review.get("account_scope"),
            "hypothetical_order": review.get("hypothetical_order", {}),
            "broker_echo": review.get("broker_echo", {}),
            "idempotency_design": review.get("idempotency_design", {}),
            "event_log_prewrite_schema": review.get("event_log_prewrite_schema", {}),
            "pre_trade_snapshot_schema": review.get("pre_trade_snapshot_schema", {}),
            "duplicate_order_guard": review.get("duplicate_order_guard", {}),
            "simulated_receipt": review.get("simulated_receipt", {}),
            "receipt_checks": review.get("receipt_checks", {}),
            "blocked_reasons": review.get("blocked_reasons", []),
            "required_next_steps": review.get("required_next_steps", []),
            "dry_run_receipt_created": bool(review.get("dry_run_receipt_created")),
            "paper_order_submitted": bool(review.get("paper_order_submitted")),
            "broker_post_called": bool(review.get("broker_post_called")),
            "broker_write_allowed": bool(review.get("broker_write_allowed")),
            "live_capital_enabled": bool(review.get("live_capital_enabled")),
            "submitted_at": review.get("submitted_at"),
            "reviewed_at": review.get("reviewed_at"),
            "boundary": review.get("boundary"),
        }
        for review in reviews
    ]


def _build_cognition(settings: Settings) -> dict[str, Any]:
    summary = shadow_intelligence_summary(settings)
    store = ShadowSignalStore(settings=settings)
    local_research_store = LocalResearchAssessmentStore(settings=settings)
    strategy_lead_store = StrategyLeadShadowStore(settings=settings)
    paper_context = paper_account_shadow_context(settings)
    signal_integrity = signal_integrity_summary(settings)
    quantum_oracle = quantum_oracle_summary(settings)
    quantum_readiness = quantum_provider_readiness(settings)
    phase2_cycle = _safe_phase2_shadow_cycle(settings)
    research_goals = research_goal_summary(settings=settings, limit=8)
    market_context = market_context_summary(settings=settings, limit=6)
    signal_reviews = _safe_signal_integrity_reviews(settings)
    try:
        signals = list(store.read())[-5:]
    except Exception:
        signals = []
    try:
        local_assessments = list(local_research_store.read())[-3:]
    except Exception:
        local_assessments = []
    try:
        strategy_packets = list(strategy_lead_store.read())[-3:]
    except Exception:
        strategy_packets = []

    evidence_packets = [_safe_evidence_packet(signal) for signal in signals]
    agent_reach_bridge = agent_reach_bridge_public_status(settings)
    agent_reach_items = agent_reach_bridge_evidence_items(agent_reach_bridge)
    if agent_reach_items:
        evidence_packets.append(
            normalize_adapter_evidence_packet(
                source_key="agent_reach",
                evidence_items=agent_reach_items,
                packet_type="social_news_discovery_packet",
                context_role="supplemental_social_news_discovery_only",
                summary="Agent Reach social/news/web capability evidence normalized for cockpit replay.",
            )
        )
    evidence_normalization = evidence_packet_normalization_summary(evidence_packets)
    try:
        evidence_runtime = evidence_packet_runtime_public_status(
            write_evidence_packet_runtime(evidence_packets, settings=settings)
        )
    except Exception as exc:  # noqa: BLE001 - cockpit must degrade safely.
        evidence_runtime = {
            "schema_version": 1,
            "runtime_version": "epr_2026_06_14",
            "normalization_version": evidence_normalization.get("normalization_version"),
            "status": "degraded",
            "replay_status": "local_jsonl_replay_failed",
            "contract_status": "durable_evidence_packet_runtime_failed",
            "storage_backend": "local_jsonl",
            "packet_count": len(evidence_packets),
            "item_count": sum(len(packet.get("items", [])) for packet in evidence_packets),
            "source_count": len({source for packet in evidence_packets for source in packet.get("sources", [])}),
            "validation_error_count": 1,
            "authority_leak_count": 0,
            "raw_ref_leak_count": 0,
            "snapshot_written": False,
            "history_appended": False,
            "history_record_count": 0,
            "event_log_written": False,
            "event_log_event_count": 0,
            "write_authority": False,
            "signal_authority": False,
            "risk_handoff_allowed": False,
            "trade_candidate_creation_allowed": False,
            "execution_allowed": False,
            "paper_order_allowed": False,
            "broker_write_allowed": False,
            "quantum_job_authority": False,
            "performance_credit_allowed": False,
            "live_capital_enabled": False,
            "public_safe": True,
            "boundary": (
                "Durable evidence packet runtime degraded closed. It cannot create source quorum, "
                "trade ideas, risk approval, orders, broker writes, quantum jobs, performance credit, "
                "or live capital."
            ),
            "error_type": exc.__class__.__name__,
        }
    latest_review_by_signal = {
        str(review.get("source_signal_id")): review
        for review in signal_reviews
        if review.get("source_signal_id")
    }

    def _hypothesis_blocked_reason(signal_id: Any) -> str:
        review = latest_review_by_signal.get(str(signal_id))
        if not review:
            return "shadow_only_pending_signal_integrity_gate"
        if review.get("status") == "passed_to_risk_shadow":
            return "signal_integrity_gate_requires_risk_agent"
        return "signal_integrity_gate_hold_or_block"

    hypotheses = [
        {
            "signal_id": signal.get("signal_id"),
            "title": signal.get("title"),
            "instrument_focus": signal.get("instrument_focus"),
            "thesis": signal.get("thesis"),
            "confidence": signal.get("confidence"),
            "status": signal.get("status", "shadow_only"),
            "execution_allowed": bool(signal.get("execution_allowed")),
            "blocked_reason": _hypothesis_blocked_reason(signal.get("signal_id")),
            "invalidation": signal.get("invalidation"),
            "generated_by": signal.get("generated_by"),
            "evidence_packet_id": signal.get("signal_id"),
            "evidence_source_count": evidence_packets[index].get("source_count", 0)
            if index < len(evidence_packets)
            else 0,
            "missing_correlations": evidence_packets[index].get("missing_correlations", [])
            if index < len(evidence_packets)
            else [],
            "integrity_review_status": next(
                (
                    review.get("status")
                    for review in reversed(signal_reviews)
                    if review.get("source_signal_id") == signal.get("signal_id")
                ),
                "not_reviewed",
            ),
            "integrity_score": next(
                (
                    review.get("integrity_score")
                    for review in reversed(signal_reviews)
                    if review.get("source_signal_id") == signal.get("signal_id")
                ),
                None,
            ),
            "created_at": signal.get("created_at"),
        }
        for index, signal in enumerate(signals)
    ]

    current_focus = []
    if hypotheses:
        current_focus.append("reviewing shadow-only hypotheses")
    if int(research_goals.get("active_goal_count", 0) or 0):
        current_focus.append(
            f"{research_goals.get('active_goal_count', 0)} active Research Goals before candidate state"
        )
    if int(market_context.get("packet_count", 0) or 0):
        current_focus.append(
            "RS-3 market context: "
            f"{market_context.get('packet_count', 0)} packets, "
            f"average source quality {market_context.get('average_source_quality_score', 0)}"
        )
    if phase2_cycle.get("mode") == "durable_replay":
        current_focus.append(
            "Phase 2 durable replay: "
            f"{phase2_cycle.get('durable_replay_replayed_source_count', 0)}/"
            f"{phase2_cycle.get('source_count', 0)} sources replayed into shadow review"
        )
    if agent_reach_bridge.get("status") == "reference_ready":
        current_focus.append(
            "Agent Reach bridge: "
            f"{agent_reach_bridge.get('selected_runtime_evidence_channel_count', 0)} "
            "social/news/web channels available for supplemental evidence"
        )
    if local_assessments:
        current_focus.append(
            f"local Research Analyst focus: {local_assessments[-1].get('watch_focus', 'shadow review')}"
        )
    if paper_context.get("status") in {"ok", "not_initialized"}:
        current_focus.append(
            "checking paper account context without order authority: "
            f"{paper_context.get('connection_status', 'unknown')}"
        )
    if signal_reviews:
        current_focus.append(
            f"Signal Integrity Gate: {len(signal_reviews)} recent reviews, "
            f"{signal_integrity.get('by_status', {}).get('hold_for_corroboration', 0)} held"
        )
    if quantum_oracle.get("result_count", 0):
        current_focus.append(
            "Head of Quant latest oracle: "
            f"{quantum_oracle.get('latest_recommendation', 'hold')}"
        )
    if not current_focus:
        current_focus.append("waiting for source heartbeat and shadow triage inputs")

    provider_status = summary.get("provider_status", {})
    latest_local_assessment = local_assessments[-1] if local_assessments else {}
    local_llm_status = provider_status.get("local_llm", {})
    research_provider = latest_local_assessment.get("provider") or local_llm_status.get("provider", "lm_studio")
    research_model = latest_local_assessment.get("model") or local_llm_status.get("model")
    research_status = local_llm_status.get("probe_status", "not_called")
    if latest_local_assessment:
        research_status = "ok" if latest_local_assessment.get("raw_response_status") == "ok" else "shadow_only"
    model_activity = [
        {
            "role": "Research Analyst",
            "provider": research_provider,
            "status": research_status,
            "model": research_model,
            "authority": "non_executable",
            "current_task": "local shadow assessment" if local_assessments else "shadow triage and local compression",
        },
        {
            "role": "Strategy Lead",
            "provider": "gemini",
            "status": "queued_shadow_review"
            if strategy_packets
            else provider_status.get("frontier_llm", {}).get("probe_status", "not_called"),
            "model": "configured_frontier_model",
            "authority": "non_executable",
            "current_task": "shadow handoff queued"
            if strategy_packets
            else "scenario challenge after local triage",
        },
        {
            "role": "Head of Quant",
            "provider": "quantum_or_classical",
            "status": quantum_oracle.get("status", "ready_classical_fallback"),
            "model": "weekly_oracle",
            "authority": "non_executable",
            "current_task": (
                "latest bounded oracle result available"
                if quantum_oracle.get("result_count", 0)
                else "classical fallback oracle ready"
            ),
        },
    ]
    return {
        "status": summary.get("status", "shadow_ready"),
        "current_focus": current_focus,
        "phase2_shadow_cycle": phase2_cycle,
        "research_goals": research_goals,
        "research_goal_records": research_goals.get("recent_goals", []),
        "market_context": market_context,
        "market_context_packets": market_context.get("recent_packets", []),
        "agent_reach_bridge": agent_reach_bridge,
        "paper_account_context": paper_context,
        "signal_integrity": {
            "status": signal_integrity.get("status", "ok"),
            "schema_version": signal_integrity.get("schema_version"),
            "review_count": signal_integrity.get("review_count", 0),
            "by_status": signal_integrity.get("by_status", {}),
            "execution_allowed_count": signal_integrity.get("execution_allowed_count", 0),
            "paper_order_allowed_count": signal_integrity.get("paper_order_allowed_count", 0),
            "trade_candidate_created_count": signal_integrity.get("trade_candidate_created_count", 0),
            "boundary": signal_integrity.get("boundary"),
        },
        "signal_integrity_reviews": signal_reviews,
        "quantum_oracle": {
            "status": quantum_oracle.get("status", "ready_classical_fallback"),
            "schema_version": quantum_oracle.get("schema_version"),
            "result_count": quantum_oracle.get("result_count", 0),
            "latest_backend": quantum_oracle.get("latest_backend", "classical_fallback"),
            "latest_backend_status": quantum_oracle.get("latest_backend_status", "not_run"),
            "latest_local_simulation_mode": quantum_oracle.get("latest_local_simulation_mode", "not_run"),
            "latest_recommendation": quantum_oracle.get("latest_recommendation", "not_run"),
            "latest_input_fingerprint": quantum_oracle.get("latest_input_fingerprint"),
            "latest_output_route_type": quantum_oracle.get("latest_output_route_type", "not_run"),
            "latest_output_storage_type": quantum_oracle.get("latest_output_storage_type", "not_run"),
            "latest_output_routing_status": quantum_oracle.get("latest_output_routing_status", "not_run"),
            "latest_output_annotation_target": quantum_oracle.get("latest_output_annotation_target", "not_run"),
            "latest_output_routing": quantum_oracle.get("latest_output_routing", {}),
            "latest_input_contract_status": quantum_oracle.get("latest_input_contract_status", "not_run"),
            "latest_input_source_type": quantum_oracle.get("latest_input_source_type", "not_run"),
            "latest_market_confirmation_status": quantum_oracle.get("latest_market_confirmation_status", "not_run"),
            "latest_yahoo_finance_role": quantum_oracle.get("latest_yahoo_finance_role", "not_run"),
            "latest_yahoo_only_market_confirmation": bool(
                quantum_oracle.get("latest_yahoo_only_market_confirmation", False)
            ),
            "latest_durable_evidence_status": quantum_oracle.get("latest_durable_evidence_status", "not_run"),
            "latest_validation_checks": quantum_oracle.get("latest_validation_checks", {}),
            "latest_created_at": quantum_oracle.get("latest_created_at"),
            "cadence": quantum_oracle.get("cadence", "weekly_shadow_oracle"),
            "cadence_days": quantum_oracle.get("cadence_days", 7),
            "next_due_at": quantum_oracle.get("next_due_at"),
            "hardware_submitted_count": quantum_oracle.get("hardware_submitted_count", 0),
            "hardware_submission_allowed_count": quantum_oracle.get("hardware_submission_allowed_count", 0),
            "hardware_scheduler_enabled_count": quantum_oracle.get("hardware_scheduler_enabled_count", 0),
            "execution_allowed_count": quantum_oracle.get("execution_allowed_count", 0),
            "paper_order_allowed_count": quantum_oracle.get("paper_order_allowed_count", 0),
            "trade_candidate_created_count": quantum_oracle.get("trade_candidate_created_count", 0),
            "qiskit_aer_available": bool(quantum_oracle.get("qiskit_aer_available")),
            "qiskit_available": bool(quantum_oracle.get("qiskit_available")),
            "local_simulator": quantum_oracle.get("local_simulator", quantum_local_simulator_status()),
            "scheduler_dry_run": quantum_oracle.get("scheduler_dry_run", {}),
            "provider_readiness": quantum_readiness,
            "boundary": quantum_oracle.get("boundary"),
        },
        "shadow_packets": _safe_shadow_packets(settings),
        "local_research_assessments": [
            {
                "assessment_id": assessment.get("assessment_id"),
                "status": assessment.get("status", "shadow_only"),
                "mode": assessment.get("mode"),
                "provider": assessment.get("provider"),
                "model": assessment.get("model"),
                "summary": assessment.get("summary"),
                "watch_focus": assessment.get("watch_focus"),
                "anomalies": assessment.get("anomalies", []),
                "missing_correlations": assessment.get("missing_correlations", []),
                "next_questions": assessment.get("next_questions", []),
                "escalation_recommendation": assessment.get("escalation_recommendation"),
                "confidence": assessment.get("confidence"),
                "execution_allowed": bool(assessment.get("execution_allowed")),
                "paper_order_allowed": bool(assessment.get("paper_order_allowed")),
                "created_at": assessment.get("created_at"),
            }
            for assessment in local_assessments
        ],
        "strategy_lead_packets": [
            {
                "packet_id": packet.get("packet_id"),
                "status": packet.get("status", "queued_shadow_only"),
                "source_assessment_id": packet.get("source_assessment_id"),
                "watch_focus": packet.get("watch_focus"),
                "missing_correlations": packet.get("missing_correlations", []),
                "blocked_by": packet.get("blocked_by", []),
                "worldview_lens_status": packet.get("worldview_lens_status"),
                "source_context": packet.get("source_context", {}),
                "strategy_review": packet.get("strategy_review", {}),
                "paper_account_context": paper_context,
                "execution_allowed": bool(packet.get("execution_allowed")),
                "paper_order_allowed": bool(packet.get("paper_order_allowed")),
                "created_at": packet.get("created_at"),
            }
            for packet in strategy_packets
        ],
        "hypotheses": hypotheses,
        "evidence_packets": evidence_packets,
        "evidence_packet_normalization": evidence_normalization,
        "evidence_packet_runtime": evidence_runtime,
        "model_activity": model_activity,
        "analysis_timeline": [
            "source observation",
            "research goal intake",
            "market context packet",
            "research analyst shadow packet",
            "local research assessment",
            "paper account mirror context",
            "deterministic triage",
            "signal integrity review",
            "staged paper-order contract hold",
            "broker reconciliation contract hold",
            "paper-submit receipt dry-run hold",
            "quantum/classical oracle check",
            "strategy review pending",
            "signal integrity gate blocked",
            "trade layer not reached",
        ],
        "blocked_reasons": [
            "shadow_only_pending_signal_integrity_gate",
            "research_goal_requires_corroboration",
            "market_context_cannot_create_trade_candidate",
            "signal_integrity_gate_hold_or_block",
            "no_risk_agent_approval",
            "no_trade_candidate_store",
            "no_broker_write_authority",
            "paper_account_context_read_only",
            "signal_integrity_gate_requires_risk_agent",
            "execution_policy_read_only",
            "staged_paper_order_contract_disabled",
            "broker_reconciliation_contract_read_only",
            "paper_submit_receipt_dry_run_only",
            "quantum_oracle_non_executable",
        ],
        "boundary": (
            "Cognition is shadow-only. Signal Integrity Gate can block or hold signals, "
            "Risk Agent can only review policy, Execution Policy kill-switch checks are read-only, "
            "staged paper-order checks cannot create orders, and broker reconciliation checks "
            "cannot submit paper orders. Paper-submit receipt checks cannot call brokers."
            " Research Goals are pre-signal research state only: they cannot create "
            "trade candidates, approve risk, stage orders, or call brokers."
            " Market Context Packets are read-only source-quality context and cannot "
            "create trade candidates, approve risk, or write orders."
        ),
    }


def _safe_paper_position(position: Any) -> dict[str, Any]:
    return {
        "position_id": position.position_id,
        "status": position.status,
        "instrument": position.instrument,
        "direction": position.direction,
        "quantity": position.quantity,
        "entry_price": position.entry_price,
        "current_price": position.current_price,
        "unrealized_pnl_gbp": position.unrealized_pnl_gbp,
        "risk_size_gbp": position.risk_size_gbp,
        "opened_at": position.opened_at,
        "invalidation": position.invalidation,
        "source_intent_id": position.source_intent_id,
        "boundary": position.boundary,
    }


def _safe_closed_trade(trade: Any) -> dict[str, Any]:
    return {
        "trade_id": trade.trade_id,
        "instrument": trade.instrument,
        "direction": trade.direction,
        "entry_price": trade.entry_price,
        "exit_price": trade.exit_price,
        "realized_pnl_gbp": trade.realized_pnl_gbp,
        "r_multiple": trade.r_multiple,
        "close_reason": trade.close_reason,
        "opened_at": trade.opened_at,
        "closed_at": trade.closed_at,
        "postmortem_status": trade.postmortem_status,
        "source_intent_id": trade.source_intent_id,
        "boundary": trade.boundary,
    }


def _safe_paper_order(order: Any) -> dict[str, Any]:
    return {
        "order_id": order.order_id,
        "status": order.status,
        "instrument": order.instrument,
        "direction": order.direction,
        "quantity": order.quantity,
        "notional_gbp": order.notional_gbp,
        "order_type": order.order_type,
        "limit_price": order.limit_price,
        "submitted_at": order.submitted_at,
        "filled_at": order.filled_at,
        "filled_quantity": order.filled_quantity,
        "filled_avg_price": order.filled_avg_price,
        "execution_allowed": order.execution_allowed,
        "paper_order_allowed": order.paper_order_allowed,
        "boundary": order.boundary,
    }


def _safe_tradingview_alert(alert: Any) -> dict[str, Any]:
    return {
        "alert_id": alert.alert_id,
        "status": alert.status,
        "source": "tradingview_alerts",
        "source_type": "tradingview_paid_alert",
        "instrument": alert.symbol,
        "symbol": alert.symbol,
        "timeframe": alert.timeframe,
        "setup_type": alert.setup_type,
        "direction": alert.direction,
        "trigger": alert.trigger,
        "price": alert.price,
        "indicator_state": alert.indicator_state,
        "chart_context": alert.chart_context,
        "received_at": alert.received_at,
        "observed_at": alert.observed_at,
        "execution_allowed": alert.execution_allowed,
        "paper_order_allowed": alert.paper_order_allowed,
        "trade_candidate_created": alert.trade_candidate_created,
        "boundary": alert.boundary,
    }


def _tradingview_alerts(settings: Settings) -> dict[str, Any]:
    summary = tradingview_alert_summary(settings)
    try:
        alerts = TradingViewAlertStore(settings=settings).read_alerts(limit=10)
        store_status = summary.get("status", "ok")
    except Exception as exc:  # noqa: BLE001 - public status should degrade safely
        alerts = ()
        store_status = "degraded"
        summary = {
            "status": "degraded",
            "alert_count": 0,
            "error": str(exc),
            "receiver_status": "local_contract_only",
            "duplicate_protection": "dedupe_key_sha256",
            "boundary": "TradingView alert store could not be read.",
        }
    return {
        "status": store_status,
        "receiver_status": summary.get("receiver_status", "local_contract_only"),
        "duplicate_protection": summary.get("duplicate_protection", "dedupe_key_sha256"),
        "alert_count": summary.get("alert_count", 0),
        "latest_observed_at": summary.get("latest_observed_at"),
        "execution_allowed_count": summary.get("execution_allowed_count", 0),
        "paper_order_allowed_count": summary.get("paper_order_allowed_count", 0),
        "trade_candidate_created_count": summary.get("trade_candidate_created_count", 0),
        "observed_signals": [_safe_tradingview_alert(alert) for alert in alerts],
        "boundary": summary.get(
            "boundary",
            "TradingView alerts are observed signals only. D7 has no execution route.",
        ),
    }


def _safe_tradingview_mcp_context_row(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "event_id": str(row.get("event_id") or "")[:160],
        "symbol": str(row.get("symbol") or "unknown")[:40],
        "instrument_name": str(row.get("instrument_name") or "unknown")[:120],
        "timeframe": str(row.get("timeframe") or "unknown")[:20],
        "tool_name": str(row.get("tool_name") or "technical_context")[:80],
        "setup_type": str(row.get("setup_type") or "technical_context")[:100],
        "direction": str(row.get("direction") or "watch")[:80],
        "technical_score": row.get("technical_score"),
        "volatility_state": str(row.get("volatility_state") or "unknown")[:120],
        "indicator_state": row.get("indicator_state") if isinstance(row.get("indicator_state"), dict) else {},
        "support_resistance": row.get("support_resistance")
        if isinstance(row.get("support_resistance"), dict)
        else {},
        "candidate_watchlist_context": str(row.get("candidate_watchlist_context") or "")[:260],
        "obvious_technical_context_flag": bool(row.get("obvious_technical_context_flag")),
        "observed_at": row.get("observed_at"),
        "trade_candidate_created": False,
        "paper_order_allowed": False,
        "execution_allowed": False,
        "broker_write_allowed": False,
        "live_capital_enabled": False,
        "boundary": str(row.get("boundary") or "TradingView MCP is technical context only.")[:700],
    }


def _tradingview_mcp_status(settings: Settings) -> dict[str, Any]:
    status = tradingview_mcp_adapter_status(settings)
    context = tradingview_mcp_context(settings)
    packet_context = tradingview_mcp_packet_context(settings)
    rows = context.get("technical_contexts", [])
    if not isinstance(rows, list):
        rows = []
    return {
        "schema_version": status.get("schema_version", 1),
        "status": status.get("status", "degraded"),
        "source": status.get("source", "market.tradingview_mcp"),
        "source_key": status.get("source_key", "tradingview_mcp"),
        "provider": status.get("provider", "local_tradingview_mcp_server"),
        "classification": status.get("classification", "supplemental_technical_analysis_context"),
        "canonical_source_count": int(status.get("canonical_source_count", 0) or 0),
        "enabled": bool(status.get("enabled")),
        "connected": bool(status.get("connected")),
        "local_checkout_exists": bool(status.get("local_checkout_exists")),
        "mcp_config_exists": bool(status.get("mcp_config_exists")),
        "package_importable": bool(status.get("package_importable")),
        "service_importable": bool(status.get("service_importable")),
        "live_calls_enabled": bool(status.get("live_calls_enabled")),
        "sample_mode_available": bool(status.get("sample_mode_available", True)),
        "technical_context_status": status.get("technical_context_status", "not_initialized"),
        "technical_context_count": int(status.get("technical_context_count", 0) or 0),
        "obvious_technical_context_count": int(
            status.get("obvious_technical_context_count", 0) or 0
        ),
        "technical_contexts": [_safe_tradingview_mcp_context_row(row) for row in rows[:8]],
        "active_required_challenges": packet_context.get("active_required_challenges", []),
        "source_quorum_credit_allowed": False,
        "technical_confirmation_role": "supplemental_technical_confirmation_only",
        "signal_authority": False,
        "risk_approval_authority": False,
        "trade_candidate_creation_allowed": False,
        "execution_allowed": False,
        "paper_order_allowed": False,
        "broker_write_allowed": False,
        "fill_confirmation_authority": False,
        "receipt_evidence_authority": False,
        "reconciliation_truth_authority": False,
        "quantum_job_authority": False,
        "live_capital_enabled": False,
        "raw_payload_exposed": False,
        "local_path_exposed": False,
        "public_safe": True,
        "boundary": status.get(
            "boundary",
            "TradingView MCP is read-only supplemental technical analysis.",
        ),
    }


def _safe_bookmap_orderflow_context_row(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "event_id": str(row.get("event_id") or "")[:160],
        "symbol": str(row.get("symbol") or "unknown")[:40],
        "instrument_name": str(row.get("instrument_name") or "unknown")[:120],
        "venue": str(row.get("venue") or "local_bookmap")[:80],
        "timeframe": str(row.get("timeframe") or "unknown")[:40],
        "bridge_channel": str(row.get("bridge_channel") or "snapshot")[:80],
        "setup_type": str(row.get("setup_type") or "orderflow_context")[:100],
        "direction": str(row.get("direction") or "watch")[:80],
        "orderflow_score": row.get("orderflow_score"),
        "liquidity_state": str(row.get("liquidity_state") or "unknown")[:120],
        "absorption_state": str(row.get("absorption_state") or "unknown")[:120],
        "imbalance_state": str(row.get("imbalance_state") or "unknown")[:120],
        "support_resistance": row.get("support_resistance")
        if isinstance(row.get("support_resistance"), dict)
        else {},
        "candidate_watchlist_context": str(row.get("candidate_watchlist_context") or "")[:260],
        "obvious_orderflow_context_flag": bool(row.get("obvious_orderflow_context_flag")),
        "observed_at": row.get("observed_at"),
        "trade_candidate_created": False,
        "paper_order_allowed": False,
        "execution_allowed": False,
        "broker_write_allowed": False,
        "bookmap_order_injection_allowed": False,
        "bookmap_trading_mode_allowed": False,
        "live_capital_enabled": False,
        "boundary": str(row.get("boundary") or "Bookmap is orderflow context only.")[:700],
    }


def _bookmap_local_bridge_status(settings: Settings) -> dict[str, Any]:
    status = bookmap_local_bridge_status(settings)
    context = bookmap_local_bridge_context(settings)
    packet_context = bookmap_local_bridge_packet_context(settings)
    rows = context.get("orderflow_contexts", [])
    if not isinstance(rows, list):
        rows = []
    return {
        "schema_version": status.get("schema_version", 1),
        "status": status.get("status", "local_bridge_required"),
        "source": status.get("source", "market.bookmap"),
        "source_key": status.get("source_key", "bookmap"),
        "provider": status.get("provider", "bookmap_local_readonly_bridge"),
        "classification": status.get("classification", "local_orderflow_confirmation_context"),
        "canonical_source_count": int(status.get("canonical_source_count", 0) or 0),
        "enabled": bool(status.get("enabled")),
        "connected": bool(status.get("connected")),
        "bridge_url_configured": bool(status.get("bridge_url_configured")),
        "bridge_url_local": bool(status.get("bridge_url_local")),
        "bridge_scheme": status.get("bridge_scheme", "missing"),
        "bridge_host_class": status.get("bridge_host_class", "missing"),
        "sanitized_endpoint": status.get("sanitized_endpoint"),
        "live_probe_enabled": bool(status.get("live_probe_enabled")),
        "sample_mode_available": bool(status.get("sample_mode_available", True)),
        "orderflow_context_status": status.get("orderflow_context_status", "not_initialized"),
        "orderflow_context_count": int(status.get("orderflow_context_count", 0) or 0),
        "obvious_orderflow_context_count": int(
            status.get("obvious_orderflow_context_count", 0) or 0
        ),
        "degraded_reason": status.get("degraded_reason"),
        "orderflow_contexts": [_safe_bookmap_orderflow_context_row(row) for row in rows[:8]],
        "active_required_challenges": packet_context.get("active_required_challenges", []),
        "source_quorum_credit_allowed": False,
        "orderflow_confirmation_role": "supplemental_orderflow_confirmation_only",
        "signal_authority": False,
        "risk_approval_authority": False,
        "trade_candidate_creation_allowed": False,
        "execution_allowed": False,
        "paper_order_allowed": False,
        "broker_write_allowed": False,
        "fill_confirmation_authority": False,
        "receipt_evidence_authority": False,
        "reconciliation_truth_authority": False,
        "quantum_job_authority": False,
        "bookmap_order_injection_allowed": False,
        "bookmap_trading_mode_allowed": False,
        "live_capital_enabled": False,
        "raw_payload_exposed": False,
        "local_path_exposed": False,
        "public_safe": True,
        "boundary": status.get(
            "boundary",
            "Bookmap local bridge is read-only supplemental order-flow context.",
        ),
    }


def _fund_manager_notes(settings: Settings) -> dict[str, Any]:
    store = GovernanceStore(settings=settings)
    try:
        comments = tuple(reversed(store.read_comments(limit=10)))
        health = store.health()
        status = health.get("status", "ok")
    except Exception as exc:  # noqa: BLE001 - public status should degrade safely
        comments = ()
        health = {
            "status": "degraded",
            "schema_version": 1,
            "comment_count": 0,
            "suggestion_count": 0,
            "accepted_count": 0,
            "rejected_count": 0,
            "implemented_count": 0,
            "event_log_export_count": 0,
            "allowed_target_types": [],
            "allowed_statuses": [],
            "visibility": "founding_fund_managers",
            "error": str(exc),
        }
        status = "degraded"
    return {
        "status": status,
        "schema_version": health.get("schema_version", 1),
        "comment_count": health.get("comment_count", 0),
        "suggestion_count": health.get("suggestion_count", 0),
        "accepted_count": health.get("accepted_count", 0),
        "rejected_count": health.get("rejected_count", 0),
        "implemented_count": health.get("implemented_count", 0),
        "event_log_export_count": health.get("event_log_export_count", 0),
        "allowed_target_types": health.get("allowed_target_types", []),
        "allowed_statuses": health.get("allowed_statuses", ["suggestion", "accepted", "rejected", "implemented"]),
        "visibility": "founding_fund_managers",
        "supabase_table": "fund_manager_comments",
        "browser_write_scope": "comments_only",
        "local_event_log_export": "accepted_or_implemented_only",
        "recent_comments": [
            {
                "comment_id": comment.comment_id,
                "author_label": "founding_fund_manager",
                "target_type": comment.target_type,
                "target_key": comment.target_key,
                "body": comment.body,
                "tags": list(comment.tags),
                "status": "suggestion" if comment.status == "open" else comment.status,
                "visibility": comment.visibility,
                "created_at": comment.created_at,
            }
            for comment in comments
        ],
        "boundary": (
            "Fund Manager comments are governance notes only. They cannot approve trades, "
            "place orders, or expose local secrets."
        ),
    }


def _communications(settings: Settings) -> dict[str, Any]:
    try:
        telegram = telegram_status(settings)
    except Exception:  # noqa: BLE001 - public status should degrade safely
        telegram = {
            "status": "degraded",
            "schema_version": 1,
            "mode": "dry_run",
            "send_gate": "disabled",
            "bot_configured": False,
            "bot_username_configured": False,
            "default_chat_configured": False,
            "member_count": 0,
            "verified_member_count": 0,
            "pending_member_count": 0,
            "failed_member_count": 0,
            "pending_queue_count": 0,
            "sent_count": 0,
            "failed_count": 0,
            "retried_count": 0,
            "suppressed_count": 0,
            "last_sent_time": None,
            "last_failure_reason": "telegram communications status unavailable",
            "last_digest_title": "",
            "active_message_classes": [],
            "dry_run_message_count": 0,
            "recent_messages": [],
            "boundary": (
                "Telegram is outbound-only member communication. It cannot place, approve, "
                "reject, modify, close, or resize trades."
            ),
        }
    try:
        telegram_intake = telegram_inbound_intake_public_status(settings)
    except Exception:  # noqa: BLE001 - public status should degrade safely
        telegram_intake = {
            "status": "degraded",
            "schema_version": 1,
            "enabled": False,
            "bot_configured": False,
            "polling_mode": "getUpdates_explicit_poll",
            "record_count": 0,
            "world_event_datapoint_count": 0,
            "strategy_consideration_count": 0,
            "ignored_message_count": 0,
            "research_triage_packet_count": 0,
            "latest_intake_type": None,
            "latest_status": None,
            "latest_observed_at": None,
            "recent_records": [],
            "recent_strategy_considerations": [],
            "recent_world_events": [],
            "trade_candidate_creation_allowed": False,
            "risk_handoff_allowed": False,
            "execution_allowed": False,
            "paper_order_allowed": False,
            "broker_write_allowed": False,
            "telegram_command_authority": False,
            "live_capital_enabled": False,
            "boundary": (
                "Telegram inbound intake is read-only member research intake. It cannot "
                "create signals, trade candidates, orders, broker writes, commands, or live capital."
            ),
        }
    try:
        telegram_daily_digest = telegram_daily_portfolio_digest_public_status(settings)
    except Exception:  # noqa: BLE001 - public status should degrade safely
        telegram_daily_digest = {
            "schema_version": TELEGRAM_DAILY_PORTFOLIO_DIGEST_SCHEMA_VERSION,
            "status": "degraded",
            "enabled": False,
            "dry_run": True,
            "target": "group",
            "local_date": None,
            "timezone": settings.telegram_daily_portfolio_digest_timezone,
            "delivery_after_local_time": settings.telegram_daily_portfolio_digest_after_local_time,
            "due_for_delivery": False,
            "already_sent": False,
            "portfolio_balance_gbp": None,
            "portfolio_total_pnl_gbp": None,
            "portfolio_performance_pct": None,
            "daily_trade_count": 0,
            "daily_trade_summaries": [],
            "paperops_idle_reason": None,
            "paperops_qualified_setup_count": 0,
            "paperops_submitted_paper_order_count": 0,
            "message_specificity_status": "degraded",
            "message_specificity_score": 0,
            "message_fingerprint": None,
            "live_send_attempted": False,
            "live_send_succeeded": False,
            "telegram_message_id_present": False,
            "last_delivery_failure_category": "daily portfolio digest status unavailable",
            "blocker_count": 1,
            "blockers": ["daily_portfolio_digest_status_unavailable"],
            "telegram_command_path_enabled": False,
            "broker_write_allowed": False,
            "paper_order_allowed": False,
            "live_capital_enabled": False,
            "boundary": TELEGRAM_DAILY_PORTFOLIO_DIGEST_BOUNDARY,
        }
    try:
        telegram_codebase_upgrade = telegram_codebase_upgrade_public_status(settings)
    except Exception:  # noqa: BLE001 - public status should degrade safely
        telegram_codebase_upgrade = {
            "schema_version": TELEGRAM_CODEBASE_UPGRADE_SCHEMA_VERSION,
            "status": "degraded",
            "enabled": False,
            "dry_run": True,
            "target": "group",
            "source": None,
            "summary": None,
            "details": [],
            "benefits": [],
            "change_area_lines": [],
            "root_commit_short": None,
            "root_last_commit_subject": None,
            "root_change_areas": [],
            "root_dirty": False,
            "root_changed_file_count": 0,
            "dashboard_commit_short": None,
            "dashboard_last_commit_subject": None,
            "dashboard_change_areas": [],
            "dashboard_dirty": False,
            "dashboard_changed_file_count": 0,
            "message_specificity_status": "degraded",
            "message_specificity_score": 0,
            "message_fingerprint": None,
            "deployment_url": None,
            "aliases": ["qadam.trade", "www.qadam.trade"],
            "already_sent": False,
            "live_send_attempted": False,
            "live_send_succeeded": False,
            "telegram_message_id_present": False,
            "last_delivery_failure_category": "codebase upgrade notification status unavailable",
            "blocker_count": 1,
            "blockers": ["codebase_upgrade_notification_status_unavailable"],
            "telegram_command_path_enabled": False,
            "broker_write_allowed": False,
            "paper_order_allowed": False,
            "repository_write_allowed": False,
            "deploy_allowed": False,
            "live_capital_enabled": False,
            "boundary": TELEGRAM_CODEBASE_UPGRADE_BOUNDARY,
        }
    return {
        "telegram": telegram,
        "telegram_intake": telegram_intake,
        "telegram_daily_portfolio_digest": telegram_daily_digest,
        "telegram_codebase_upgrade": telegram_codebase_upgrade,
        "boundary": (
            "Communications are notify-only and intake-only. The browser and Telegram "
            "rail cannot create broker actions, commands, or hidden approvals."
        ),
    }


def _capital(settings: Settings) -> dict[str, Any]:
    store = PaperAccountMirrorStore(settings=settings)
    summary = paper_account_summary(settings)
    alpaca_report = _read_runtime_json(settings, "alpaca_paper_mirror.json") or {}
    market_clock = alpaca_report.get("market_clock", {})
    if not isinstance(market_clock, dict):
        market_clock = {}
    latest = store.latest_snapshot()
    positions = [_safe_paper_position(position) for position in store.read_positions()]
    closed_trades = [_safe_closed_trade(trade) for trade in store.read_closed_trades()]
    orders = [_safe_paper_order(order) for order in store.read_orders()]
    postmortems_due = [
        trade for trade in closed_trades if trade.get("postmortem_status") == "postmortem_due"
    ]
    postmortems_complete = [
        trade for trade in closed_trades if trade.get("postmortem_status") == "postmortem_complete"
    ]
    equity_curve = [
        {
            "observed_at": snapshot.observed_at,
            "equity_gbp": snapshot.equity_gbp,
            "drawdown_pct": snapshot.drawdown_pct,
            "display_currency": snapshot.display_currency,
            "account_currency": snapshot.account_currency,
        }
        for snapshot in store.read_snapshots(limit=20)
    ]
    if latest is None:
        return {
            "mirror_status": summary["status"],
            "account_scope": PAPER_ACCOUNT_SCOPE,
            "broker": "local_mirror_pending_alpaca_readonly",
            "portfolio_value_source": "local_placeholder",
            "account_currency": "GBP",
            "display_currency": "GBP",
            "fx_to_gbp_rate": 1.0,
            "starting_balance_gbp": settings.trial_balance_gbp,
            "current_balance_gbp": settings.trial_balance_gbp,
            "cash_gbp": settings.trial_balance_gbp,
            "equity_gbp": settings.trial_balance_gbp,
            "peak_equity_gbp": settings.trial_balance_gbp,
            "realized_pnl_gbp": 0,
            "unrealized_pnl_gbp": 0,
            "drawdown_pct": 0,
            "max_drawdown_pct": 0,
            "live_capital_enabled": False,
            "write_authority": False,
            "connection_status": "not_initialized",
            "timeline_status": "not_initialized",
            "observed_at": None,
            "last_broker_sync_at": None,
            "last_broker_sync_age_seconds": None,
            "stale_after_seconds": PAPER_ACCOUNT_MIRROR_STALE_AFTER_SECONDS,
            "mirror_freshness_status": "not_connected",
            "mirror_freshness_label": "No broker mirror snapshot yet",
            "portfolio_reconciliation": {
                "status": "not_available",
                "delta": None,
                "tolerance": None,
                "detail": "No broker snapshot exists yet.",
                "history_latest_equity_gbp": None,
                "history_latest_profit_loss_gbp": None,
            },
            "broker_reconciliation_status": "not_available",
            "maturity_closed_trade_target": 100,
            "maturity_closed_trade_count": 0,
            "order_count": 0,
            "open_order_count": 0,
            "open_positions": [],
            "closed_trades": [],
            "orders": [],
            "postmortems_due": [],
            "postmortems_complete": [],
            "equity_curve": [],
            "market_clock": {
                "status": "unavailable",
                "is_open": None,
                "next_open": None,
                "next_close": None,
            },
            "boundary": summary["boundary"],
        }
    sync_age_seconds = _iso_age_seconds(latest.observed_at)
    if sync_age_seconds is None:
        freshness_status = "unknown"
        freshness_label = "Broker mirror timestamp unavailable"
    elif sync_age_seconds <= PAPER_ACCOUNT_MIRROR_STALE_AFTER_SECONDS:
        freshness_status = "fresh"
        freshness_label = "Broker mirror fresh"
    else:
        freshness_status = "stale"
        freshness_label = "Broker mirror stale"
    return {
        "mirror_status": summary["status"],
        "account_scope": latest.account_scope,
        "broker": latest.broker,
        "portfolio_value_source": (
            "alpaca_paper_account_mirror"
            if str(latest.broker).startswith("alpaca")
            else "local_paper_account_snapshot"
        ),
        "account_currency": latest.account_currency,
        "display_currency": latest.display_currency,
        "fx_to_gbp_rate": latest.fx_to_gbp_rate,
        "source_current_balance": latest.source_current_balance,
        "source_cash": latest.source_cash,
        "source_equity": latest.source_equity,
        "starting_balance_gbp": latest.starting_balance_gbp,
        "current_balance_gbp": latest.current_balance_gbp,
        "cash_gbp": latest.cash_gbp,
        "equity_gbp": latest.equity_gbp,
        "peak_equity_gbp": latest.peak_equity_gbp,
        "realized_pnl_gbp": latest.realized_pnl_gbp,
        "unrealized_pnl_gbp": latest.unrealized_pnl_gbp,
        "drawdown_pct": latest.drawdown_pct,
        "max_drawdown_pct": latest.max_drawdown_pct,
        "live_capital_enabled": latest.live_capital_enabled,
        "write_authority": latest.write_authority,
        "connection_status": latest.connection_status,
        "timeline_status": latest.timeline_status,
        "observed_at": latest.observed_at,
        "last_broker_sync_at": latest.observed_at,
        "last_broker_sync_age_seconds": sync_age_seconds,
        "stale_after_seconds": PAPER_ACCOUNT_MIRROR_STALE_AFTER_SECONDS,
        "mirror_freshness_status": freshness_status,
        "mirror_freshness_label": freshness_label,
        "portfolio_reconciliation": {
            "status": latest.broker_reconciliation_status,
            "delta": latest.broker_reconciliation_delta,
            "tolerance": latest.broker_reconciliation_tolerance,
            "detail": latest.broker_reconciliation_detail,
            "history_latest_equity_gbp": latest.broker_portfolio_history_latest_equity,
            "history_latest_profit_loss_gbp": latest.broker_portfolio_history_latest_profit_loss,
        },
        "broker_reconciliation_status": latest.broker_reconciliation_status,
        "maturity_closed_trade_target": latest.maturity_closed_trade_target,
        "maturity_closed_trade_count": latest.maturity_closed_trade_count,
        "open_position_count": len(positions),
        "closed_trade_count": len(closed_trades),
        "order_count": len(orders),
        "open_order_count": sum(
            1
            for order in orders
            if str(order.get("status") or "").lower() in OPEN_ORDER_STATUSES
        ),
        "market_clock": {
            "status": market_clock.get("status", "unavailable"),
            "is_open": market_clock.get("is_open"),
            "next_open": market_clock.get("next_open"),
            "next_close": market_clock.get("next_close"),
            "timestamp": market_clock.get("timestamp"),
        },
        "postmortem_due_count": len(postmortems_due),
        "postmortem_complete_count": len(postmortems_complete),
        "open_positions": positions,
        "closed_trades": closed_trades,
        "orders": orders,
        "postmortems_due": postmortems_due,
        "postmortems_complete": postmortems_complete,
        "equity_curve": equity_curve,
        "boundary": latest.boundary,
    }


def _safe_trade_item(intent: Any) -> dict[str, Any]:
    return {
        "intent_id": intent.intent_id,
        "status": intent.status,
        "instrument": intent.instrument,
        "direction": intent.direction,
        "venue": intent.venue,
        "strategy": intent.strategy,
        "catalyst": intent.catalyst,
        "evidence_summary": intent.evidence_summary,
        "probability_estimate": intent.probability_estimate,
        "market_implied_probability": intent.market_implied_probability,
        "price_gap": intent.price_gap,
        "proposed_entry": intent.proposed_entry,
        "invalidation": intent.invalidation,
        "holding_window": intent.holding_window,
        "risk_size_gbp": intent.risk_size_gbp,
        "risk_size_pct": intent.risk_size_pct,
        "risk_state": intent.risk_state,
        "blocked_reason": intent.blocked_reason,
        "execution_allowed": intent.execution_allowed,
        "paper_order_allowed": intent.paper_order_allowed,
        "source_signal_id": intent.source_signal_id,
        "source_type": intent.source_type,
        "research_goal_id": intent.research_goal_id,
        "akber_filter": intent.akber_filter,
        "risk_checks": intent.risk_checks,
        "tags": list(intent.tags),
        "created_at": intent.created_at,
        "updated_at": intent.updated_at,
        "boundary": intent.boundary,
    }


def _trade_layer(settings: Settings) -> dict[str, Any]:
    try:
        intents = TradeIntentStore(settings=settings).read_intents()
        store_status = "ok"
    except Exception:
        intents = ()
        store_status = "degraded"
    try:
        paper_store = PaperAccountMirrorStore(settings=settings)
        paper_positions = paper_store.read_positions()
        paper_closed_trades = paper_store.read_closed_trades()
        paper_orders = paper_store.read_orders()
    except Exception:
        paper_positions = ()
        paper_closed_trades = ()
        paper_orders = ()
    try:
        tradingview_alerts = TradingViewAlertStore(settings=settings).read_alerts(limit=10)
    except Exception:
        tradingview_alerts = ()
    tradingview_mcp_rows = _tradingview_mcp_status(settings).get("technical_contexts", [])
    if not isinstance(tradingview_mcp_rows, list):
        tradingview_mcp_rows = []

    trade_layer: dict[str, Any] = {
        "summary": trade_intent_summary(settings) if store_status == "ok" else {"status": store_status},
        "risk_agent": _risk_agent_status(settings),
        "execution_policy": _execution_policy_status(settings),
        "staged_paper_order": _staged_paper_order_status(settings),
        "broker_reconciliation": _broker_reconciliation_status(settings),
        "paper_submit_receipt": _paper_submit_receipt_status(settings),
        "store_status": store_status,
        "watching": [],
        "candidates": [],
        "blocked": [],
        "staged_orders": [],
        "submitted_orders": [],
        "mirrored_orders": [],
        "open_positions": [],
        "closed_trades": [],
        "postmortems_due": [],
        "postmortems_complete": [],
        "boundary": "D5 trade intent is local and non-executing. No broker order path exists.",
    }
    trade_layer["watching"].extend(_safe_tradingview_alert(alert) for alert in tradingview_alerts)
    trade_layer["watching"].extend(
        {
            "alert_id": row.get("event_id"),
            "status": "observed_signal",
            "source": "tradingview_mcp",
            "source_type": "tradingview_mcp_technical_context",
            "instrument": row.get("symbol"),
            "symbol": row.get("symbol"),
            "timeframe": row.get("timeframe"),
            "setup_type": row.get("setup_type"),
            "direction": row.get("direction"),
            "trigger": row.get("candidate_watchlist_context"),
            "price": None,
            "indicator_state": row.get("indicator_state", {}),
            "chart_context": row.get("volatility_state"),
            "received_at": row.get("observed_at"),
            "observed_at": row.get("observed_at"),
            "execution_allowed": False,
            "paper_order_allowed": False,
            "trade_candidate_created": False,
            "boundary": row.get("boundary"),
        }
        for row in tradingview_mcp_rows[:8]
    )
    for intent in intents:
        item = _safe_trade_item(intent)
        if intent.status in {"candidate", "risk_review"}:
            trade_layer["candidates"].append(item)
        elif intent.status == "blocked":
            trade_layer["blocked"].append(item)
        elif intent.status == "staged_paper_order":
            trade_layer["staged_orders"].append(item)
        elif intent.status == "submitted_paper_order":
            trade_layer["submitted_orders"].append(item)
        elif intent.status in {"open_position", "exit_planned"}:
            trade_layer["open_positions"].append(item)
        elif intent.status == "closed_trade":
            trade_layer["closed_trades"].append(item)
        elif intent.status == "postmortem_due":
            trade_layer["postmortems_due"].append(item)
        elif intent.status == "postmortem_complete":
            trade_layer["postmortems_complete"].append(item)
        else:
            trade_layer["watching"].append(item)
    trade_layer["open_positions"].extend(
        _safe_paper_position(position) | {"source": "paper_account_mirror"}
        for position in paper_positions
    )
    trade_layer["closed_trades"].extend(
        _safe_closed_trade(trade) | {"source": "paper_account_mirror"}
        for trade in paper_closed_trades
    )
    trade_layer["mirrored_orders"].extend(
        _safe_paper_order(order) | {"source": "paper_account_mirror"}
        for order in paper_orders
    )
    trade_layer["postmortems_due"].extend(
        _safe_closed_trade(trade) | {"source": "paper_account_mirror"}
        for trade in paper_closed_trades
        if trade.postmortem_status == "postmortem_due"
    )
    trade_layer["postmortems_complete"].extend(
        _safe_closed_trade(trade) | {"source": "paper_account_mirror"}
        for trade in paper_closed_trades
        if trade.postmortem_status == "postmortem_complete"
    )
    if isinstance(trade_layer["summary"], dict):
        trade_layer["summary"]["observed_signal_count"] = len(trade_layer["watching"])
    return trade_layer


def _module_status(payload: dict[str, Any], key: str) -> str:
    for module in payload.get("modules", []):
        if module.get("key") == key:
            return str(module.get("status") or "pending")
    return "pending"


def _provider_status(providers: Any, provider_key: str) -> dict[str, Any]:
    if not isinstance(providers, list):
        return {}
    for provider in providers:
        if isinstance(provider, dict) and provider.get("key") == provider_key:
            return provider
    return {}


def _phase3_readiness(quantum_oracle: dict[str, Any]) -> dict[str, Any]:
    provider_readiness = quantum_oracle.get("provider_readiness", {})
    if not isinstance(provider_readiness, dict):
        provider_readiness = {}
    local_simulator = quantum_oracle.get("local_simulator", {})
    if not isinstance(local_simulator, dict):
        local_simulator = {}
    scheduler = quantum_oracle.get("scheduler_dry_run", {})
    if not isinstance(scheduler, dict):
        scheduler = {}
    qctrl = provider_readiness.get("qctrl_readiness", {})
    if not isinstance(qctrl, dict):
        qctrl = {}

    ibm_quantum = _provider_status(provider_readiness.get("providers", []), "ibm_quantum")
    aws_braket = _provider_status(provider_readiness.get("providers", []), "aws_braket")

    return {
        "schema_version": 1,
        "phase": "Q3",
        "status": "provider_scheduler_readiness",
        "readiness_scope": "provider_scheduler_readiness",
        "execution_readiness": "not_execution_ready",
        "public_safe": True,
        "provider_readiness_status": provider_readiness.get("status", "unknown"),
        "provider_count": provider_readiness.get("provider_count", 0),
        "expected_provider_count": provider_readiness.get("expected_provider_count", 0),
        "configured_provider_count": provider_readiness.get("configured_count", 0),
        "missing_secret_count": provider_readiness.get("missing_secret_count", 0),
        "missing_optional_package_count": provider_readiness.get("missing_optional_package_count", 0),
        "qctrl_configured": bool(provider_readiness.get("qctrl_configured")),
        "qctrl_status": qctrl.get("status", "unknown"),
        "qctrl_live_probe_enabled": bool(qctrl.get("live_probe_enabled", False)),
        "qctrl_provider_call_count": qctrl.get("provider_call_count", 0),
        "qctrl_optimization_job_submitted": bool(qctrl.get("optimization_job_submitted", False)),
        "qiskit_available": bool(quantum_oracle.get("qiskit_available") or local_simulator.get("qiskit_available")),
        "qiskit_aer_available": bool(
            quantum_oracle.get("qiskit_aer_available") or local_simulator.get("qiskit_aer_available")
        ),
        "local_simulator_status": local_simulator.get("status", "unknown"),
        "local_simulator_backend": local_simulator.get("selected_backend", quantum_oracle.get("latest_backend")),
        "local_simulator_mode": quantum_oracle.get("latest_local_simulation_mode", "not_run"),
        "ibm_quantum_status": ibm_quantum.get("status", "unknown"),
        "aws_braket_status": aws_braket.get("status", "unknown"),
        "scheduler_status": scheduler.get("status", "unknown"),
        "scheduler_due": bool(scheduler.get("due", False)),
        "scheduler_enabled": bool(scheduler.get("scheduler_enabled", False)),
        "autonomous_scheduler_enabled": bool(scheduler.get("autonomous_scheduler_enabled", False)),
        "scheduler_would_queue_job_count": scheduler.get("would_queue_job_count", 0),
        "scheduler_jobs_queued_count": scheduler.get("jobs_queued_count", 0),
        "scheduler_jobs_submitted_count": scheduler.get("jobs_submitted_count", 0),
        "latest_recommendation": quantum_oracle.get("latest_recommendation", "not_run"),
        "latest_output_route_type": quantum_oracle.get("latest_output_route_type", "not_run"),
        "latest_output_storage_type": quantum_oracle.get("latest_output_storage_type", "not_run"),
        "latest_output_routing_status": quantum_oracle.get("latest_output_routing_status", "not_run"),
        "latest_oracle_created_at": quantum_oracle.get("latest_created_at"),
        "next_due_at": quantum_oracle.get("next_due_at") or scheduler.get("next_due_at"),
        "hardware_submission_allowed_count": quantum_oracle.get("hardware_submission_allowed_count", 0),
        "hardware_submitted_count": quantum_oracle.get("hardware_submitted_count", 0),
        "hardware_scheduler_enabled_count": quantum_oracle.get("hardware_scheduler_enabled_count", 0),
        "execution_allowed_count": quantum_oracle.get("execution_allowed_count", 0),
        "paper_order_allowed_count": quantum_oracle.get("paper_order_allowed_count", 0),
        "trade_candidate_created_count": quantum_oracle.get("trade_candidate_created_count", 0),
        "secret_value_exposed_count": provider_readiness.get("secret_value_exposed_count", 0),
        "raw_response_exposed_count": provider_readiness.get("raw_response_exposed_count", 0),
        "local_absolute_path_exposed_count": 0,
        "cloud_job_identifier_exposed_count": 0,
        "boundary": (
            "Phase 3 cockpit visibility is provider/scheduler readiness only, not execution readiness. "
            "It exposes sanitized status and counters only; no secret values, raw provider responses, "
            "local absolute paths, provider payloads, or unsanitized cloud job identifiers."
        ),
    }


def _phase4_strategy_status(settings: Settings) -> dict[str, Any]:
    manifested_strategy = (
        _read_runtime_json(settings, "phase4_manifested_strategy_metadata.json")
        or build_manifested_strategy_metadata(settings=settings)
    )
    approval_event = (
        _read_runtime_json(settings, "phase4_fund_manager_approval_event.json")
        or build_fund_manager_approval_event(settings=settings)
    )
    toggle_snapshot = build_strategy_toggle_snapshot(
        settings=settings,
        approval_event=approval_event,
    )
    document_errors = validate_manifested_strategy_metadata(manifested_strategy)
    approval_errors = validate_fund_manager_approval_event(
        approval_event,
        manifested_strategy=manifested_strategy,
    )
    toggle_errors = validate_strategy_toggle_snapshot(toggle_snapshot)
    certification = _read_runtime_json(settings, "phase4_certification.json") or {}
    certification_errors = (
        validate_phase4_certification(certification) if certification else []
    )
    certification_present = bool(certification)

    toggles = [
        {
            "strategy_key": str(toggle.get("strategy_key") or "unknown_strategy"),
            "label": str(toggle.get("label") or toggle.get("strategy_key") or "Unknown Strategy"),
            "toggle_state": str(toggle.get("toggle_state") or "inactive"),
            "visible_in_cockpit": bool(toggle.get("visible_in_cockpit")),
            "approval_state": str(toggle.get("approval_state") or approval_event.get("approval_state")),
            "event_log_required": bool(toggle.get("event_log_required")),
            "execution_allowed": False,
            "paper_order_allowed": False,
            "broker_write_allowed": False,
            "live_capital_enabled": False,
            "boundary": "Strategy toggle visibility only; it cannot route execution.",
        }
        for toggle in toggle_snapshot.get("toggles", [])
        if isinstance(toggle, dict)
    ]

    approval_state = str(approval_event.get("approval_state") or "not_requested")
    approval_logged = approval_event.get("approval_logged") is True
    strategy_document_ready = bool(str(manifested_strategy.get("document_fingerprint") or "").strip())
    phase4_certification_allowed = (
        approval_state == "approved"
        and approval_logged
        and strategy_document_ready
        and not document_errors
        and not approval_errors
        and not toggle_errors
    )
    if certification_present:
        phase4_certification_allowed = (
            certification.get("phase4_certification_allowed") is True
            and not certification_errors
        )
    stage = str(certification.get("stage") or "Q4-11")
    stage_status = str(
        certification.get("stage_status")
        or (
            "phase4_certification_pending"
            if certification_present
            else "cockpit_strategy_visibility"
        )
    )
    no_execution_boundary = (
        "Phase 4 cockpit visibility is strategy-governance state only. It cannot create "
        "trade candidates, approve risk, stage or submit paper orders, write to brokers, "
        "call quantum providers, schedule hardware, or enable live capital."
    )
    return {
        "schema_version": 1,
        "phase": "Q4",
        "stage": stage,
        "stage_status": stage_status,
        "status": (
            "phase4_certification_visible"
            if certification_present
            else "phase4_strategy_visible"
        ),
        "public_safe": True,
        "audit_completion_state": {
            "latest_completed_stage": "Q4-12" if certification_present else "Q4-10",
            "current_stage": stage,
            "completed_stage_count": 13 if certification_present else 11,
            "completed_audits": [
                "Q4-0",
                "Q4-1",
                "Q4-2",
                "Q4-3",
                "Q4-4",
                "Q4-5",
                "Q4-6",
                "Q4-7",
                "Q4-8",
                "Q4-9",
                "Q4-10",
                *(
                    ["Q4-11", "Q4-12"]
                    if certification_present
                    else []
                ),
            ],
            "phase4_exit_gate": (
                certification.get("phase4_exit_gate")
                or (
                    "ready_for_certification_probe"
                    if phase4_certification_allowed
                    else "blocked_pending_explicit_approval"
                )
            ),
        },
        "strategy_document_status": manifested_strategy.get("status", "unknown"),
        "strategy_document": {
            "artifact_id": manifested_strategy.get("artifact_id"),
            "document_fingerprint": manifested_strategy.get("document_fingerprint"),
            "document_ready": strategy_document_ready,
            "active_instrument_count": manifested_strategy.get("active_instrument_count", 0),
            "catalyst_class_count": manifested_strategy.get("catalyst_class_count", 0),
            "strategy_family_candidate_count": manifested_strategy.get(
                "strategy_family_candidate_count",
                0,
            ),
            "approval_required": manifested_strategy.get("approval_required") is True,
            "approval_state": manifested_strategy.get("approval_state", "not_requested"),
            "validation_error_count": len(document_errors),
            "trade_candidate_count": 0,
            "boundary": "Manifested strategy metadata is review-only and cannot enable execution.",
        },
        "approval_event_status": approval_state,
        "approval_event": {
            "artifact_id": approval_event.get("artifact_id"),
            "status": approval_event.get("status"),
            "approval_state": approval_state,
            "approval_logged": approval_logged,
            "approver_label": approval_event.get("approver_label"),
            "event_log_required": approval_event.get("event_log_required") is True,
            "event_log_correlation_present": bool(
                str(approval_event.get("event_log_correlation_id") or "").strip()
            ),
            "strategy_artifact_fingerprint_verified": approval_event.get(
                "strategy_artifact_fingerprint_verified"
            )
            is True,
            "approved_strategy_family_count": len(
                approval_event.get("approved_strategy_families", [])
            ),
            "rejected_strategy_family_count": len(
                approval_event.get("rejected_strategy_families", [])
            ),
            "required_amendment_count": len(approval_event.get("required_amendments", [])),
            "required_amendments": list(approval_event.get("required_amendments", []))[:3],
            "validation_error_count": len(approval_errors),
            "phase4_certification_allowed": phase4_certification_allowed,
            "boundary": approval_event.get("boundary") or no_execution_boundary,
        },
        "strategy_toggles": {
            "toggle_count": len(toggles),
            "visible_toggle_count": sum(1 for toggle in toggles if toggle["visible_in_cockpit"]),
            "draft_toggle_count": toggle_snapshot.get("draft_toggle_count", 0),
            "approved_shadow_toggle_count": toggle_snapshot.get("approved_shadow_toggle_count", 0),
            "inactive_toggle_count": toggle_snapshot.get("inactive_toggle_count", 0),
            "event_log_required": toggle_snapshot.get("event_log_required") is True,
            "validation_error_count": len(toggle_errors),
            "toggles": toggles,
            "boundary": "Strategy toggles are cockpit-visible governance states, not order routes.",
        },
        "toggle_count": len(toggles),
        "approved_shadow_strategy_toggle_count": toggle_snapshot.get(
            "approved_shadow_toggle_count",
            0,
        ),
        "approved_shadow_ready": toggle_snapshot.get("approved_shadow_ready") is True,
        "phase4_certification_allowed": phase4_certification_allowed,
        "phase4_certified": certification.get("phase4_certified") is True,
        "phase5_handoff_allowed": certification.get("phase5_handoff_allowed") is True,
        "certification_status": certification.get("status", "not_run"),
        "certification": {
            "artifact_id": certification.get("artifact_id"),
            "status": certification.get("status", "not_run"),
            "stage_status": stage_status,
            "certification_logged": certification.get("certification_logged") is True,
            "event_log_required": certification.get("event_log_required") is True,
            "event_log_correlation_present": bool(
                str(certification.get("event_log_correlation_id") or "").strip()
            ),
            "phase4_certified": certification.get("phase4_certified") is True,
            "phase4_complete": certification.get("phase4_complete") is True,
            "phase5_handoff_allowed": certification.get("phase5_handoff_allowed") is True,
            "certification_blocker_count": len(
                certification.get("certification_blockers", [])
            ),
            "certification_blockers": list(
                certification.get("certification_blockers", [])
            )[:5],
            "preference_mcp_certification_gate": {
                "status": certification.get(
                    "preference_mcp_certification_gate",
                    {},
                ).get("status", "not_run"),
                "identity_status": certification.get(
                    "preference_mcp_certification_gate",
                    {},
                ).get("identity_status", "not_verified"),
                "provenance_status": certification.get(
                    "preference_mcp_certification_gate",
                    {},
                ).get("provenance_status", "not_run"),
                "approved_domain_pack_count": certification.get(
                    "preference_mcp_certification_gate",
                    {},
                ).get("approved_domain_pack_count", 0),
                "source_promotion_status": certification.get(
                    "preference_mcp_certification_gate",
                    {},
                ).get("source_promotion_status", "not_run"),
                "source_promotion_decision_count": certification.get(
                    "preference_mcp_certification_gate",
                    {},
                ).get("source_promotion_decision_count", 0),
                "source_promotion_promoted_decision_count": certification.get(
                    "preference_mcp_certification_gate",
                    {},
                ).get("source_promotion_promoted_decision_count", 0),
                "source_promotion_canonical_source_count_after": certification.get(
                    "preference_mcp_certification_gate",
                    {},
                ).get("source_promotion_canonical_source_count_after", 0),
                "preference_mcp_source_36": certification.get(
                    "preference_mcp_certification_gate",
                    {},
                ).get("preference_mcp_source_36", False),
                "certification_blocker_count": certification.get(
                    "preference_mcp_certification_gate",
                    {},
                ).get("certification_blocker_count", 0),
            },
            "validation_error_count": len(certification_errors),
            "required_next_steps": list(
                certification.get("required_next_steps", [])
            )[:3],
            "boundary": certification.get("boundary") or no_execution_boundary,
        },
        "trade_candidate_count": 0,
        "execution_allowed_count": 0,
        "paper_order_allowed_count": 0,
        "broker_write_allowed_count": 0,
        "live_endpoint_allowed_count": 0,
        "live_capital_enabled_count": 0,
        "execution_allowed": False,
        "paper_order_allowed": False,
        "broker_write_allowed": False,
        "live_endpoint_allowed": False,
        "live_capital_enabled": False,
        "market_confirmation_policy": {
            "yahoo_finance_role": "supplemental_market_confirmation_only",
            "yahoo_only_confirmation_allowed": False,
            "canonical_source_promotion_allowed": False,
        },
        "no_execution_boundary": no_execution_boundary,
        "boundary": no_execution_boundary,
    }


def _phase5_layer_b_readiness_status(settings: Settings) -> dict[str, Any]:
    readiness = build_phase5_layer_b_readiness(settings=settings)
    validation_errors = validate_phase5_layer_b_readiness(readiness)
    return {
        "schema_version": readiness.get("schema_version", 1),
        "phase": readiness.get("phase", "Q5"),
        "layer": readiness.get("layer", "Layer B"),
        "stage": readiness.get("stage", "P5-PRE"),
        "status": readiness.get("status", "not_run"),
        "public_safe": readiness.get("public_safe") is True,
        "phase5_layer_b_scope_count": readiness.get("phase5_layer_b_scope_count", 0),
        "phase5_layer_b_scope": list(readiness.get("phase5_layer_b_scope", [])),
        "phase5_layer_b_implementation_plan_allowed": (
            readiness.get("phase5_layer_b_implementation_plan_allowed") is True
        ),
        "phase5_layer_b_implementation_allowed": (
            readiness.get("phase5_layer_b_implementation_allowed") is True
        ),
        "phase5_orchestration_start_allowed": (
            readiness.get("phase5_orchestration_start_allowed") is True
        ),
        "phase5_handoff_allowed": readiness.get("phase5_handoff_allowed") is True,
        "phase4_certified": readiness.get("phase4_certified") is True,
        "phase4_certification_status": readiness.get(
            "phase4_certification_status",
            "not_run",
        ),
        "phase4_stage_status": readiness.get("phase4_stage_status", "not_run"),
        "approval_state": readiness.get("approval_state", "missing"),
        "approval_logged": readiness.get("approval_logged") is True,
        "preference_gate_status": readiness.get("preference_gate_status", "not_run"),
        "preference_source_promotion_status": readiness.get(
            "preference_source_promotion_status",
            "not_run",
        ),
        "preference_source_promotion_promoted_decision_count": readiness.get(
            "preference_source_promotion_promoted_decision_count",
            0,
        ),
        "preference_source_promotion_canonical_source_count_after": readiness.get(
            "preference_source_promotion_canonical_source_count_after",
            0,
        ),
        "preference_mcp_source_36": readiness.get("preference_mcp_source_36") is True,
        "yahoo_finance_role": readiness.get("yahoo_finance_role", "missing"),
        "readiness_blockers": list(readiness.get("readiness_blockers", [])),
        "readiness_blocker_count": readiness.get("readiness_blocker_count", 0),
        "nonapproval_blocker_count": readiness.get("nonapproval_blocker_count", 0),
        "only_explicit_approval_blocks_phase5_plan": (
            readiness.get("only_explicit_approval_blocks_phase5_plan") is True
        ),
        "validation_error_count": len(validation_errors),
        "approval_policy_router_enabled": False,
        "risk_agent_approval_authority": False,
        "kill_switch_mutation_authority": False,
        "execution_adapter_write_authority": False,
        "paper_execution_allowed": False,
        "paper_order_allowed": False,
        "broker_write_allowed": False,
        "prediction_market_write_allowed": False,
        "telegram_live_notifications_allowed": False,
        "position_monitor_write_authority": False,
        "live_capital_enabled": False,
        "boundary": readiness.get("boundary") or (
            "Phase 5 readiness is a planning gate only and cannot start Layer B."
        ),
    }


def _phase5_kill_switch_public_status(settings: Settings) -> dict[str, Any]:
    runtime_ledger = _read_runtime_json(settings, KILL_SWITCH_RUNTIME_ARTIFACT)
    ledger_recorded = runtime_ledger is not None
    ledger = runtime_ledger or build_phase5_kill_switch_ledger(settings=settings)
    validation_errors = validate_phase5_kill_switch_ledger(ledger)
    return {
        "schema_version": ledger.get("schema_version", 1),
        "phase": ledger.get("phase", "Q5"),
        "stage": ledger.get("stage", "Q5-4"),
        "status": ledger.get("status", "not_run") if ledger_recorded else "missing_fail_closed",
        "public_safe": ledger.get("public_safe") is True,
        "ledger_recorded": ledger_recorded,
        "event_log_written": ledger.get("event_log_written") is True,
        "event_log_event_count": int(ledger.get("event_log_event_count", 0) or 0),
        "validation_error_count": len(validation_errors),
        "switch_count": int(ledger.get("switch_count", 0) or 0),
        "active_switch_count": int(ledger.get("active_switch_count", 0) or 0),
        "blocking_switch_count": int(ledger.get("blocking_switch_count", 0) or 0),
        "clear_switch_count": int(ledger.get("clear_switch_count", 0) or 0),
        "fail_closed_default_count": int(ledger.get("fail_closed_default_count", 0) or 0),
        "missing_state_fail_closed_default_count": int(
            ledger.get("missing_state_fail_closed_default_count", 0) or 0
        ),
        "corrupt_state_fail_closed_default_count": int(
            ledger.get("corrupt_state_fail_closed_default_count", 0) or 0
        ),
        "default_fail_closed_on_missing_state": (
            ledger.get("default_fail_closed_on_missing_state") is True
        ),
        "default_fail_closed_on_corrupt_state": (
            ledger.get("default_fail_closed_on_corrupt_state") is True
        ),
        "required_scope_types": list(ledger.get("required_scope_types", [])),
        "required_scope_type_count": int(ledger.get("required_scope_type_count", 0) or 0),
        "required_enforcement_points": list(ledger.get("required_enforcement_points", [])),
        "required_enforcement_point_count": int(
            ledger.get("required_enforcement_point_count", 0) or 0
        ),
        "scope_counts": dict(ledger.get("scope_counts", {}) or {}),
        "state_counts": dict(ledger.get("state_counts", {}) or {}),
        "status_counts": dict(ledger.get("status_counts", {}) or {}),
        "q5_3_risk_review_count": int(ledger.get("q5_3_risk_review_count", 0) or 0),
        "q5_3_paper_size_eligible_count": int(
            ledger.get("q5_3_paper_size_eligible_count", 0) or 0
        ),
        "execution_allowed": False,
        "paper_order_allowed": False,
        "broker_write_allowed": False,
        "telegram_live_notifications_allowed": False,
        "kill_switch_mutation_authority": False,
        "live_capital_enabled": False,
        "boundary": ledger.get("boundary")
        or "Q5-4 kill-switch status is fail-closed and cannot enable live capital.",
    }


def _phase5_execution_adapter_public_status(settings: Settings) -> dict[str, Any]:
    runtime_bundle = _read_runtime_json(settings, EXECUTION_ADAPTER_RUNTIME_ARTIFACT)
    recorded = runtime_bundle is not None
    bundle = runtime_bundle or build_phase5_execution_adapter_status(settings=settings)
    validation_errors = validate_phase5_execution_adapter_status_bundle(bundle)
    statuses = [
        status
        for status in bundle.get("statuses", [])
        if isinstance(status, dict)
    ]
    alpaca = next(
        (status for status in statuses if status.get("venue_key") == "alpaca_paper"),
        {},
    )
    return {
        "schema_version": bundle.get("schema_version", 1),
        "phase": bundle.get("phase", "Q5"),
        "stage": bundle.get("stage", "Q5-5"),
        "status": bundle.get("status", "not_run") if recorded else "missing_fail_closed",
        "public_safe": bundle.get("public_safe") is True,
        "recorded": recorded,
        "event_log_written": bundle.get("event_log_written") is True,
        "event_log_event_count": int(bundle.get("event_log_event_count", 0) or 0),
        "validation_error_count": len(validation_errors),
        "adapter_status_count": int(bundle.get("adapter_status_count", 0) or 0),
        "first_release_allowed_count": int(bundle.get("first_release_allowed_count", 0) or 0),
        "read_allowed_count": int(bundle.get("read_allowed_count", 0) or 0),
        "downstream_staging_allowed_count": int(
            bundle.get("downstream_staging_allowed_count", 0) or 0
        ),
        "active_kill_switch_block_count": int(
            bundle.get("active_kill_switch_block_count", 0) or 0
        ),
        "required_check_count": int(bundle.get("required_check_count", 0) or 0),
        "reconciliation_prerequisite_count": int(
            bundle.get("reconciliation_prerequisite_count", 0) or 0
        ),
        "status_counts": dict(bundle.get("status_counts", {}) or {}),
        "read_health_counts": dict(bundle.get("read_health_counts", {}) or {}),
        "write_health_counts": dict(bundle.get("write_health_counts", {}) or {}),
        "alpaca_status": alpaca.get("status", "missing"),
        "alpaca_read_health": alpaca.get("read_health", "missing"),
        "alpaca_write_health": alpaca.get("write_health", "missing"),
        "alpaca_credentials_configured": alpaca.get("credentials_configured") is True,
        "alpaca_account_mode": alpaca.get("account_mode", "missing"),
        "alpaca_current_balance_gbp": float(alpaca.get("current_balance_gbp", 0.0) or 0.0),
        "alpaca_open_order_count": int(alpaca.get("open_order_count", 0) or 0),
        "alpaca_open_position_count": int(alpaca.get("open_position_count", 0) or 0),
        "execution_adapter_write_authority": False,
        "paper_order_staging_allowed": False,
        "paper_order_submission_allowed": False,
        "paper_order_allowed": False,
        "broker_write_allowed": False,
        "prediction_market_write_allowed": False,
        "crypto_perps_write_allowed": False,
        "live_endpoint_allowed": False,
        "live_capital_enabled": False,
        "secret_value_exposed_count": int(bundle.get("secret_value_exposed_count", 0) or 0),
        "raw_payload_exposed_count": int(bundle.get("raw_payload_exposed_count", 0) or 0),
        "local_path_exposed_count": int(bundle.get("local_path_exposed_count", 0) or 0),
        "boundary": bundle.get("boundary")
        or "Q5-5 adapter status is read-only and cannot write brokers or enable live capital.",
    }


def _phase5_paper_order_staging_public_status(settings: Settings) -> dict[str, Any]:
    runtime_bundle = _read_runtime_json(settings, PAPER_ORDER_STAGING_RUNTIME_ARTIFACT)
    recorded = runtime_bundle is not None
    bundle = runtime_bundle or build_phase5_paper_order_staging_gate(settings=settings)
    validation_errors = validate_phase5_paper_order_staging_bundle(bundle)
    records = [
        record
        for record in bundle.get("records", [])
        if isinstance(record, dict)
    ]
    return {
        "schema_version": bundle.get("schema_version", 1),
        "phase": bundle.get("phase", "Q5"),
        "stage": bundle.get("stage", "Q5-6"),
        "status": bundle.get("status", "not_run") if recorded else "missing_fail_closed",
        "public_safe": bundle.get("public_safe") is True,
        "recorded": recorded,
        "event_log_written": bundle.get("event_log_written") is True,
        "event_log_event_count": int(bundle.get("event_log_event_count", 0) or 0),
        "validation_error_count": len(validation_errors),
        "risk_review_count": int(bundle.get("risk_review_count", 0) or 0),
        "paper_size_eligible_count": int(bundle.get("paper_size_eligible_count", 0) or 0),
        "staging_record_count": int(bundle.get("staging_record_count", 0) or 0),
        "staged_order_count": int(bundle.get("staged_order_count", 0) or 0),
        "blocked_count": int(bundle.get("blocked_count", 0) or 0),
        "eligible_for_staging_count": int(bundle.get("staged_order_count", 0) or 0),
        "event_log_prewrite_ready_count": sum(
            1 for record in records if record.get("event_log_prewrite_ready") is True
        ),
        "active_kill_switch_block_count": sum(
            1 for record in records if record.get("kill_switch_clear") is not True
        ),
        "global_error_count": int(bundle.get("global_error_count", 0) or 0),
        "required_check_count": int(bundle.get("required_check_count", 0) or 0),
        "reconciliation_prerequisite_count": int(
            bundle.get("reconciliation_prerequisite_count", 0) or 0
        ),
        "cancellation_condition_count": int(
            bundle.get("cancellation_condition_count", 0) or 0
        ),
        "status_counts": dict(bundle.get("status_counts", {}) or {}),
        "order_state_counts": dict(bundle.get("order_state_counts", {}) or {}),
        "staging_allowed": False,
        "submission_allowed": False,
        "paper_order_staging_allowed": False,
        "paper_order_submission_allowed": False,
        "paper_order_allowed": False,
        "paper_order_submitted": False,
        "broker_write_allowed": False,
        "broker_post_called": False,
        "execution_allowed": False,
        "live_capital_enabled": False,
        "secret_value_exposed_count": sum(
            1 for record in records if record.get("secret_value_exposed") is not False
        ),
        "raw_payload_exposed_count": sum(
            1 for record in records if record.get("raw_payload_exposed") is not False
        ),
        "local_path_exposed_count": sum(
            1 for record in records if record.get("local_path_exposed") is not False
        ),
        "boundary": bundle.get("boundary")
        or "Q5-6 staging status is blocked and cannot submit paper orders or enable live capital.",
    }


def _phase5_alpaca_paper_dry_run_public_status(settings: Settings) -> dict[str, Any]:
    runtime_bundle = _read_runtime_json(settings, ALPACA_PAPER_DRY_RUN_RUNTIME_ARTIFACT)
    recorded = runtime_bundle is not None
    bundle = runtime_bundle or build_phase5_alpaca_paper_dry_run(settings=settings)
    validation_errors = validate_phase5_alpaca_paper_dry_run_bundle(bundle)
    return {
        "schema_version": bundle.get("schema_version", 1),
        "phase": bundle.get("phase", "Q5"),
        "stage": bundle.get("stage", "Q5-7"),
        "status": bundle.get("status", "not_run") if recorded else "missing_fail_closed",
        "public_safe": bundle.get("public_safe") is True,
        "recorded": recorded,
        "event_log_written": bundle.get("event_log_written") is True,
        "event_log_event_count": int(bundle.get("event_log_event_count", 0) or 0),
        "validation_error_count": len(validation_errors),
        "source_staging_record_count": int(bundle.get("source_staging_record_count", 0) or 0),
        "source_staged_order_count": int(bundle.get("source_staged_order_count", 0) or 0),
        "dry_run_record_count": int(bundle.get("dry_run_record_count", 0) or 0),
        "request_preview_count": int(bundle.get("request_preview_count", 0) or 0),
        "dry_run_receipt_count": int(bundle.get("dry_run_receipt_count", 0) or 0),
        "blocked_count": int(bundle.get("blocked_count", 0) or 0),
        "required_check_count": int(bundle.get("required_check_count", 0) or 0),
        "idempotency_collision_count": int(bundle.get("idempotency_collision_count", 0) or 0),
        "duplicate_guard_collision_count": int(
            bundle.get("duplicate_guard_collision_count", 0) or 0
        ),
        "status_counts": dict(bundle.get("status_counts", {}) or {}),
        "receipt_state_counts": dict(bundle.get("receipt_state_counts", {}) or {}),
        "paper_order_submission_allowed": False,
        "paper_order_allowed": False,
        "paper_order_submitted": False,
        "broker_write_allowed": False,
        "broker_post_called": False,
        "alpaca_post_called": False,
        "execution_allowed": False,
        "live_endpoint_allowed": False,
        "live_capital_enabled": False,
        "secret_value_exposed_count": int(bundle.get("secret_value_exposed_count", 0) or 0),
        "raw_payload_exposed_count": int(bundle.get("raw_payload_exposed_count", 0) or 0),
        "local_path_exposed_count": int(bundle.get("local_path_exposed_count", 0) or 0),
        "boundary": bundle.get("boundary")
        or "Q5-7 Alpaca paper dry-run cannot call POST routes or enable live capital.",
    }


def _phase5_paper_submit_enablement_public_status(settings: Settings) -> dict[str, Any]:
    runtime_bundle = _read_runtime_json(settings, PAPER_SUBMIT_ENABLEMENT_RUNTIME_ARTIFACT)
    recorded = runtime_bundle is not None
    bundle = runtime_bundle or build_phase5_paper_submit_enablement_gate(settings=settings)
    validation_errors = validate_phase5_paper_submit_enablement_bundle(bundle)
    submit_path_available_count = int(bundle.get("submit_path_available_count", 0) or 0)
    return {
        "schema_version": bundle.get("schema_version", 1),
        "phase": bundle.get("phase", "Q5"),
        "stage": bundle.get("stage", "Q5-8"),
        "status": bundle.get("status", "not_run") if recorded else "missing_fail_closed",
        "public_safe": bundle.get("public_safe") is True,
        "recorded": recorded,
        "event_log_written": bundle.get("event_log_written") is True,
        "event_log_event_count": int(bundle.get("event_log_event_count", 0) or 0),
        "validation_error_count": len(validation_errors),
        "source_dry_run_record_count": int(bundle.get("source_dry_run_record_count", 0) or 0),
        "source_request_preview_count": int(bundle.get("source_request_preview_count", 0) or 0),
        "source_dry_run_receipt_count": int(bundle.get("source_dry_run_receipt_count", 0) or 0),
        "submit_enablement_record_count": int(bundle.get("submit_enablement_record_count", 0) or 0),
        "submit_path_available_count": submit_path_available_count,
        "blocked_count": int(bundle.get("blocked_count", 0) or 0),
        "required_check_count": int(bundle.get("required_check_count", 0) or 0),
        "idempotency_collision_count": int(bundle.get("idempotency_collision_count", 0) or 0),
        "duplicate_guard_collision_count": int(
            bundle.get("duplicate_guard_collision_count", 0) or 0
        ),
        "dry_run_bundle_validation_error_count": int(
            bundle.get("dry_run_bundle_validation_error_count", 0) or 0
        ),
        "status_counts": dict(bundle.get("status_counts", {}) or {}),
        "receipt_state_counts": dict(bundle.get("receipt_state_counts", {}) or {}),
        "paper_submit_approval_state": bundle.get("paper_submit_approval_state", "missing"),
        "paper_submit_approval_present": bundle.get("paper_submit_approval_present") is True,
        "paper_submit_approval_logged": bundle.get("paper_submit_approval_logged") is True,
        "submit_path_key": "alpaca_paper_post_order",
        "submit_path_available": submit_path_available_count > 0,
        "paper_execution_allowed": False,
        "paper_order_submission_allowed": False,
        "paper_order_allowed": False,
        "paper_order_submitted": False,
        "execution_adapter_write_authority": False,
        "broker_write_allowed": False,
        "broker_post_called": False,
        "alpaca_post_called": False,
        "prediction_market_write_allowed": False,
        "live_endpoint_allowed": False,
        "live_capital_enabled": False,
        "execution_adapter_write_authority_count": int(
            bundle.get("execution_adapter_write_authority_count", 0) or 0
        ),
        "paper_execution_allowed_count": int(bundle.get("paper_execution_allowed_count", 0) or 0),
        "paper_order_allowed_count": int(bundle.get("paper_order_allowed_count", 0) or 0),
        "paper_order_submission_allowed_count": int(
            bundle.get("paper_order_submission_allowed_count", 0) or 0
        ),
        "paper_order_submitted_count": int(bundle.get("paper_order_submitted_count", 0) or 0),
        "broker_submit_receipt_created_count": int(
            bundle.get("broker_submit_receipt_created_count", 0) or 0
        ),
        "broker_write_allowed_count": int(bundle.get("broker_write_allowed_count", 0) or 0),
        "broker_post_called_count": int(bundle.get("broker_post_called_count", 0) or 0),
        "alpaca_post_called_count": int(bundle.get("alpaca_post_called_count", 0) or 0),
        "prediction_market_write_allowed_count": int(
            bundle.get("prediction_market_write_allowed_count", 0) or 0
        ),
        "live_endpoint_allowed_count": int(bundle.get("live_endpoint_allowed_count", 0) or 0),
        "live_capital_enabled_count": int(bundle.get("live_capital_enabled_count", 0) or 0),
        "secret_value_exposed_count": int(bundle.get("secret_value_exposed_count", 0) or 0),
        "raw_payload_exposed_count": int(bundle.get("raw_payload_exposed_count", 0) or 0),
        "local_path_exposed_count": int(bundle.get("local_path_exposed_count", 0) or 0),
        "authorization_header_exposed_count": int(
            bundle.get("authorization_header_exposed_count", 0) or 0
        ),
        "base_url_exposed_count": int(bundle.get("base_url_exposed_count", 0) or 0),
        "boundary": bundle.get("boundary")
        or "Q5-8 paper-submit enablement is approval-gated and cannot enable live capital.",
    }


def _phase5_prediction_market_adapter_public_status(settings: Settings) -> dict[str, Any]:
    runtime_bundle = _read_runtime_json(settings, PREDICTION_MARKET_ADAPTER_RUNTIME_ARTIFACT)
    recorded = runtime_bundle is not None
    bundle = runtime_bundle or build_phase5_prediction_market_adapter(settings=settings)
    validation_errors = validate_phase5_prediction_market_adapter_bundle(bundle)
    return {
        "schema_version": bundle.get("schema_version", 1),
        "phase": bundle.get("phase", "Q5"),
        "stage": bundle.get("stage", "Q5-9"),
        "status": bundle.get("status", "not_run") if recorded else "missing_fail_closed",
        "public_safe": bundle.get("public_safe") is True,
        "recorded": recorded,
        "event_log_written": bundle.get("event_log_written") is True,
        "event_log_event_count": int(bundle.get("event_log_event_count", 0) or 0),
        "validation_error_count": len(validation_errors),
        "route_count": int(bundle.get("route_count", 0) or 0),
        "prediction_market_route_count": int(
            bundle.get("prediction_market_route_count", 0) or 0
        ),
        "read_only_route_count": int(bundle.get("read_only_route_count", 0) or 0),
        "prediction_market_context_count": int(
            bundle.get("preference_prediction_market_context_count", 0) or 0
        ),
        "policy_risk_caution_context_count": int(
            bundle.get("policy_risk_caution_context_count", 0) or 0
        ),
        "guarded_placeholder_count": int(bundle.get("guarded_placeholder_count", 0) or 0),
        "paper_not_available_count": int(bundle.get("paper_not_available_count", 0) or 0),
        "live_blocked_count": int(bundle.get("live_blocked_count", 0) or 0),
        "required_check_count": int(bundle.get("required_check_count", 0) or 0),
        "status_counts": dict(bundle.get("status_counts", {}) or {}),
        "placeholder_status_counts": dict(bundle.get("placeholder_status_counts", {}) or {}),
        "preference_provenance_status": bundle.get("preference_provenance_status", "not_run"),
        "preference_context_status": bundle.get("preference_context_status", "not_run"),
        "preference_distinct_upstream_source_count": int(
            bundle.get("preference_distinct_upstream_source_count", 0) or 0
        ),
        "preference_multi_source_context_allowed": (
            bundle.get("preference_multi_source_context_allowed") is True
        ),
        "preference_counts_as_canonical_source": False,
        "preference_only_source_quorum_allowed": False,
        "preference_source_quorum_credit_allowed": False,
        "strategy_source_quorum_credit_allowed": False,
        "prediction_market_write_allowed": False,
        "paper_order_allowed": False,
        "paper_order_submitted": False,
        "broker_write_allowed": False,
        "crypto_perps_write_allowed": False,
        "paid_preference_tools_allowed": False,
        "live_endpoint_allowed": False,
        "live_capital_enabled": False,
        "prediction_market_write_allowed_count": int(
            bundle.get("prediction_market_write_allowed_count", 0) or 0
        ),
        "prediction_market_order_allowed_count": int(
            bundle.get("prediction_market_order_allowed_count", 0) or 0
        ),
        "prediction_market_spend_allowed_count": int(
            bundle.get("prediction_market_spend_allowed_count", 0) or 0
        ),
        "prediction_market_live_order_allowed_count": int(
            bundle.get("prediction_market_live_order_allowed_count", 0) or 0
        ),
        "crypto_perps_write_allowed_count": int(
            bundle.get("crypto_perps_write_allowed_count", 0) or 0
        ),
        "paid_preference_tools_allowed_count": int(
            bundle.get("paid_preference_tools_allowed_count", 0) or 0
        ),
        "paper_order_allowed_count": int(bundle.get("paper_order_allowed_count", 0) or 0),
        "paper_order_submitted_count": int(
            bundle.get("paper_order_submitted_count", 0) or 0
        ),
        "broker_write_allowed_count": int(bundle.get("broker_write_allowed_count", 0) or 0),
        "broker_post_called_count": int(bundle.get("broker_post_called_count", 0) or 0),
        "live_endpoint_allowed_count": int(bundle.get("live_endpoint_allowed_count", 0) or 0),
        "live_capital_enabled_count": int(bundle.get("live_capital_enabled_count", 0) or 0),
        "secret_value_exposed_count": int(bundle.get("secret_value_exposed_count", 0) or 0),
        "raw_payload_exposed_count": int(bundle.get("raw_payload_exposed_count", 0) or 0),
        "local_path_exposed_count": int(bundle.get("local_path_exposed_count", 0) or 0),
        "authorization_header_exposed_count": int(
            bundle.get("authorization_header_exposed_count", 0) or 0
        ),
        "base_url_exposed_count": int(bundle.get("base_url_exposed_count", 0) or 0),
        "boundary": bundle.get("boundary")
        or "Q5-9 prediction-market context is read-only and cannot enable live capital.",
    }


def _phase5_telegram_notifier_public_status(settings: Settings) -> dict[str, Any]:
    runtime_bundle = _read_runtime_json(settings, TELEGRAM_NOTIFIER_RUNTIME_ARTIFACT)
    recorded = runtime_bundle is not None
    bundle = runtime_bundle or build_phase5_telegram_notifier(settings=settings)
    validation_errors = validate_phase5_telegram_notifier_bundle(bundle)
    return {
        "schema_version": bundle.get("schema_version", 1),
        "phase": bundle.get("phase", "Q5"),
        "stage": bundle.get("stage", "Q5-10"),
        "status": bundle.get("status", "not_run") if recorded else "missing_fail_closed",
        "public_safe": bundle.get("public_safe") is True,
        "recorded": recorded,
        "event_log_written": bundle.get("event_log_written") is True,
        "event_log_event_count": int(bundle.get("event_log_event_count", 0) or 0),
        "validation_error_count": len(validation_errors),
        "alert_type_count": int(bundle.get("alert_type_count", 0) or 0),
        "notification_record_count": int(bundle.get("notification_record_count", 0) or 0),
        "eligible_alert_count": int(bundle.get("eligible_alert_count", 0) or 0),
        "suppressed_alert_count": int(bundle.get("suppressed_alert_count", 0) or 0),
        "queued_dry_run_alert_count": int(bundle.get("queued_dry_run_alert_count", 0) or 0),
        "outbox_message_written_count": int(bundle.get("outbox_message_written_count", 0) or 0),
        "required_check_count": int(bundle.get("required_check_count", 0) or 0),
        "status_counts": dict(bundle.get("status_counts", {}) or {}),
        "notification_state_counts": dict(bundle.get("notification_state_counts", {}) or {}),
        "telegram_status": bundle.get("telegram_status", "not_run"),
        "telegram_mode": bundle.get("telegram_mode", "not_run"),
        "telegram_send_gate": bundle.get("telegram_send_gate", "not_run"),
        "telegram_bot_configured": bundle.get("telegram_bot_configured") is True,
        "telegram_delivery_target_count": int(
            bundle.get("telegram_delivery_target_count", 0) or 0
        ),
        "send_test_gate_state": bundle.get("send_test_gate_state", "missing"),
        "send_test_approval_present": bundle.get("send_test_approval_present") is True,
        "send_test_approval_logged": bundle.get("send_test_approval_logged") is True,
        "private_send_test_allowed": bundle.get("private_send_test_allowed") is True,
        "normal_live_notification_allowed": False,
        "source_degradation_count": int(bundle.get("source_degradation_count", 0) or 0),
        "telegram_command_path_enabled": False,
        "telegram_live_notifications_allowed": False,
        "paper_order_allowed": False,
        "paper_order_submitted": False,
        "broker_write_allowed": False,
        "live_capital_enabled": False,
        "telegram_command_path_enabled_count": int(
            bundle.get("telegram_command_path_enabled_count", 0) or 0
        ),
        "telegram_trade_command_enabled_count": int(
            bundle.get("telegram_trade_command_enabled_count", 0) or 0
        ),
        "telegram_place_trade_command_enabled_count": int(
            bundle.get("telegram_place_trade_command_enabled_count", 0) or 0
        ),
        "telegram_approve_trade_command_enabled_count": int(
            bundle.get("telegram_approve_trade_command_enabled_count", 0) or 0
        ),
        "telegram_reject_trade_command_enabled_count": int(
            bundle.get("telegram_reject_trade_command_enabled_count", 0) or 0
        ),
        "telegram_modify_trade_command_enabled_count": int(
            bundle.get("telegram_modify_trade_command_enabled_count", 0) or 0
        ),
        "telegram_resize_trade_command_enabled_count": int(
            bundle.get("telegram_resize_trade_command_enabled_count", 0) or 0
        ),
        "telegram_close_trade_command_enabled_count": int(
            bundle.get("telegram_close_trade_command_enabled_count", 0) or 0
        ),
        "telegram_cancel_trade_command_enabled_count": int(
            bundle.get("telegram_cancel_trade_command_enabled_count", 0) or 0
        ),
        "telegram_live_notifications_allowed_count": int(
            bundle.get("telegram_live_notifications_allowed_count", 0) or 0
        ),
        "live_send_allowed_count": int(bundle.get("live_send_allowed_count", 0) or 0),
        "broker_write_allowed_count": int(bundle.get("broker_write_allowed_count", 0) or 0),
        "broker_post_called_count": int(bundle.get("broker_post_called_count", 0) or 0),
        "paper_order_allowed_count": int(bundle.get("paper_order_allowed_count", 0) or 0),
        "paper_order_submitted_count": int(
            bundle.get("paper_order_submitted_count", 0) or 0
        ),
        "execution_allowed_count": int(bundle.get("execution_allowed_count", 0) or 0),
        "prediction_market_write_allowed_count": int(
            bundle.get("prediction_market_write_allowed_count", 0) or 0
        ),
        "live_endpoint_allowed_count": int(bundle.get("live_endpoint_allowed_count", 0) or 0),
        "live_capital_enabled_count": int(bundle.get("live_capital_enabled_count", 0) or 0),
        "secret_value_exposed_count": int(bundle.get("secret_value_exposed_count", 0) or 0),
        "raw_payload_exposed_count": int(bundle.get("raw_payload_exposed_count", 0) or 0),
        "local_path_exposed_count": int(bundle.get("local_path_exposed_count", 0) or 0),
        "authorization_header_exposed_count": int(
            bundle.get("authorization_header_exposed_count", 0) or 0
        ),
        "chat_id_exposed_count": int(bundle.get("chat_id_exposed_count", 0) or 0),
        "bot_token_exposed_count": int(bundle.get("bot_token_exposed_count", 0) or 0),
        "boundary": bundle.get("boundary")
        or "Q5-10 Telegram notifications are dry-run and command-disabled.",
    }


def _phase5_position_monitor_public_status(settings: Settings) -> dict[str, Any]:
    runtime_bundle = _read_runtime_json(settings, POSITION_MONITOR_RUNTIME_ARTIFACT)
    recorded = runtime_bundle is not None
    bundle = runtime_bundle or build_phase5_position_monitor(settings=settings)
    validation_errors = validate_phase5_position_monitor_bundle(bundle)
    return {
        "schema_version": bundle.get("schema_version", 1),
        "phase": bundle.get("phase", "Q5"),
        "stage": bundle.get("stage", "Q5-11"),
        "status": bundle.get("status", "not_run") if recorded else "missing_fail_closed",
        "public_safe": bundle.get("public_safe") is True,
        "recorded": recorded,
        "event_log_written": bundle.get("event_log_written") is True,
        "event_log_event_count": int(bundle.get("event_log_event_count", 0) or 0),
        "validation_error_count": len(validation_errors),
        "position_record_count": int(bundle.get("position_record_count", 0) or 0),
        "closed_trade_summary_count": int(bundle.get("closed_trade_summary_count", 0) or 0),
        "monitor_record_count": int(bundle.get("monitor_record_count", 0) or 0),
        "lifecycle_state_count": int(bundle.get("lifecycle_state_count", 0) or 0),
        "status_counts": dict(bundle.get("status_counts", {}) or {}),
        "lifecycle_state_counts": dict(bundle.get("lifecycle_state_counts", {}) or {}),
        "reconciliation_state_counts": dict(bundle.get("reconciliation_state_counts", {}) or {}),
        "paper_account_status": bundle.get("paper_account_status", "unknown"),
        "paper_account_snapshot_count": int(bundle.get("paper_account_snapshot_count", 0) or 0),
        "paper_account_connection_status": bundle.get(
            "paper_account_connection_status",
            "unknown",
        ),
        "account_equity_gbp": float(bundle.get("account_equity_gbp", 0.0) or 0.0),
        "current_balance_gbp": float(bundle.get("current_balance_gbp", 0.0) or 0.0),
        "realized_pnl_gbp": float(bundle.get("realized_pnl_gbp", 0.0) or 0.0),
        "unrealized_pnl_gbp": float(bundle.get("unrealized_pnl_gbp", 0.0) or 0.0),
        "drawdown_pct": float(bundle.get("drawdown_pct", 0.0) or 0.0),
        "submitted_order_count": int(bundle.get("submitted_order_count", 0) or 0),
        "mirrored_order_count": int(bundle.get("mirrored_order_count", 0) or 0),
        "open_order_count": int(bundle.get("open_order_count", 0) or 0),
        "open_position_count": int(bundle.get("open_position_count", 0) or 0),
        "closed_trade_count": int(bundle.get("closed_trade_count", 0) or 0),
        "postmortem_due_count": int(bundle.get("postmortem_due_count", 0) or 0),
        "postmortem_complete_count": int(bundle.get("postmortem_complete_count", 0) or 0),
        "duplicate_state_count": int(bundle.get("duplicate_state_count", 0) or 0),
        "missing_state_count": int(bundle.get("missing_state_count", 0) or 0),
        "contradictory_state_count": int(bundle.get("contradictory_state_count", 0) or 0),
        "unknown_state_count": int(bundle.get("unknown_state_count", 0) or 0),
        "stuck_state_count": int(bundle.get("stuck_state_count", 0) or 0),
        "failed_reconciliation_count": int(bundle.get("failed_reconciliation_count", 0) or 0),
        "new_actions_blocked_by_reconciliation_failure": (
            bundle.get("new_actions_blocked_by_reconciliation_failure") is True
        ),
        "paper_submit_gate_status": bundle.get("paper_submit_gate_status", "unknown"),
        "telegram_notifier_status": bundle.get("telegram_notifier_status", "unknown"),
        "required_check_count": int(bundle.get("required_check_count", 0) or 0),
        "position_monitor_write_authority": False,
        "paper_order_allowed": False,
        "paper_order_submitted": False,
        "broker_write_allowed": False,
        "live_capital_enabled": False,
        "execution_allowed_count": int(bundle.get("execution_allowed_count", 0) or 0),
        "paper_order_allowed_count": int(bundle.get("paper_order_allowed_count", 0) or 0),
        "paper_order_submitted_count": int(bundle.get("paper_order_submitted_count", 0) or 0),
        "broker_write_allowed_count": int(bundle.get("broker_write_allowed_count", 0) or 0),
        "broker_post_called_count": int(bundle.get("broker_post_called_count", 0) or 0),
        "alpaca_post_called_count": int(bundle.get("alpaca_post_called_count", 0) or 0),
        "telegram_live_notifications_allowed_count": int(
            bundle.get("telegram_live_notifications_allowed_count", 0) or 0
        ),
        "position_created_count": int(bundle.get("position_created_count", 0) or 0),
        "position_monitor_write_authority_count": int(
            bundle.get("position_monitor_write_authority_count", 0) or 0
        ),
        "position_close_allowed_count": int(bundle.get("position_close_allowed_count", 0) or 0),
        "position_resize_allowed_count": int(bundle.get("position_resize_allowed_count", 0) or 0),
        "order_cancel_allowed_count": int(bundle.get("order_cancel_allowed_count", 0) or 0),
        "live_capital_enabled_count": int(bundle.get("live_capital_enabled_count", 0) or 0),
        "secret_value_exposed_count": int(bundle.get("secret_value_exposed_count", 0) or 0),
        "raw_payload_exposed_count": int(bundle.get("raw_payload_exposed_count", 0) or 0),
        "local_path_exposed_count": int(bundle.get("local_path_exposed_count", 0) or 0),
        "authorization_header_exposed_count": int(
            bundle.get("authorization_header_exposed_count", 0) or 0
        ),
        "account_identifier_exposed_count": int(
            bundle.get("account_identifier_exposed_count", 0) or 0
        ),
        "broker_order_identifier_exposed_count": int(
            bundle.get("broker_order_identifier_exposed_count", 0) or 0
        ),
        "boundary": bundle.get("boundary")
        or "Q5-11 position monitoring is read-only and cannot mutate positions.",
    }


def _phase5_signal_review_public_status(settings: Settings) -> dict[str, Any]:
    runtime_bundle = _read_runtime_json(settings, SIGNAL_REVIEW_RUNTIME_ARTIFACT)
    recorded = runtime_bundle is not None
    bundle = runtime_bundle or build_phase5_signal_review(settings=settings)
    signal_integrity = signal_integrity_summary(settings)
    validation_errors = validate_phase5_signal_review_bundle(bundle)
    records = [
        record
        for record in bundle.get("records", [])
        if isinstance(record, dict)
    ]
    public_records = [
        {
            "artifact_id": record.get("artifact_id"),
            "strategy_family_key": record.get("strategy_family_key"),
            "primary_instrument": record.get("primary_instrument"),
            "selected_venue": record.get("selected_venue"),
            "status": record.get("status"),
            "decision_chain": record.get("decision_chain", {}),
            "governance_action": record.get("governance_action", {}),
            "backend_truth_displayed": record.get("backend_truth_displayed") is True,
            "ui_inferred_readiness": record.get("ui_inferred_readiness") is True,
            "trade_approval_control_enabled": record.get("trade_approval_control_enabled") is True,
            "order_place_control_enabled": record.get("order_place_control_enabled") is True,
            "broker_write_allowed": record.get("broker_write_allowed") is True,
            "prediction_market_write_allowed": record.get("prediction_market_write_allowed") is True,
            "live_capital_enabled": record.get("live_capital_enabled") is True,
            "boundary": record.get("boundary"),
        }
        for record in records[:10]
    ]
    return {
        "schema_version": bundle.get("schema_version", 1),
        "phase": bundle.get("phase", "Q5"),
        "stage": bundle.get("stage", "Q5-12"),
        "status": bundle.get("status", "not_run") if recorded else "missing_fail_closed",
        "public_safe": bundle.get("public_safe") is True,
        "recorded": recorded,
        "event_log_written": bundle.get("event_log_written") is True,
        "event_log_event_count": int(bundle.get("event_log_event_count", 0) or 0),
        "validation_error_count": len(validation_errors),
        "pricing_gap_rollout_stage": str(
            signal_integrity.get("pricing_gap_rollout_stage") or "stage_a"
        ),
        "pricing_gap_rollout_relaxed_policy_enabled": (
            signal_integrity.get("pricing_gap_rollout_relaxed_policy_enabled") is True
        ),
        "funnel_shadow_signal_count": int(signal_integrity.get("shadow_signal_count", 0) or 0),
        "funnel_review_count": int(signal_integrity.get("review_count", 0) or 0),
        "funnel_signals_with_market_confirmation_count": int(
            signal_integrity.get("signals_with_market_confirmation_count", 0) or 0
        ),
        "funnel_signals_with_pricing_gap_evidence_count": int(
            signal_integrity.get("signals_with_pricing_gap_evidence_count", 0) or 0
        ),
        "funnel_signals_blocked_only_by_missing_pricing_gap_count": int(
            signal_integrity.get(
                "signals_blocked_only_by_missing_pricing_gap_count",
                0,
            )
            or 0
        ),
        "funnel_signals_passed_to_risk_count": int(
            signal_integrity.get("signals_passed_to_risk_count", 0) or 0
        ),
        "funnel_risk_reviews_blocked_only_by_pricing_gap_policy_count": int(
            signal_integrity.get(
                "risk_reviews_blocked_only_by_pricing_gap_policy_count",
                0,
            )
            or 0
        ),
        "funnel_stage_b_candidate_signal_count": int(
            signal_integrity.get("stage_b_candidate_signal_count", 0) or 0
        ),
        "funnel_flagged_missing_pricing_gap_producer_count": int(
            signal_integrity.get("flagged_missing_pricing_gap_producer_count", 0) or 0
        ),
        "signal_review_record_count": int(bundle.get("signal_review_record_count", 0) or 0),
        "chain_step_count": int(bundle.get("chain_step_count", 0) or 0),
        "decision_chain_count": int(bundle.get("decision_chain_count", 0) or 0),
        "required_chain_steps": list(bundle.get("required_chain_steps", [])),
        "required_check_count": int(bundle.get("required_check_count", 0) or 0),
        "governance_action_count": int(bundle.get("governance_action_count", 0) or 0),
        "governance_comment_count": int(bundle.get("governance_comment_count", 0) or 0),
        "governance_comment_event_count": int(
            bundle.get("governance_comment_event_count", 0) or 0
        ),
        "kill_switch_action_available_count": int(
            bundle.get("kill_switch_action_available_count", 0) or 0
        ),
        "kill_switch_action_event_count": int(
            bundle.get("kill_switch_action_event_count", 0) or 0
        ),
        "backend_truth_displayed_count": int(
            bundle.get("backend_truth_displayed_count", 0) or 0
        ),
        "ui_inferred_readiness_count": int(bundle.get("ui_inferred_readiness_count", 0) or 0),
        "backend_validation_error_count": int(bundle.get("backend_validation_error_count", 0) or 0),
        "status_counts": dict(bundle.get("status_counts", {}) or {}),
        "chain_status_counts": dict(bundle.get("chain_status_counts", {}) or {}),
        "records": public_records,
        "paper_order_allowed": False,
        "paper_order_submitted": False,
        "broker_write_allowed": False,
        "prediction_market_write_allowed": False,
        "kill_switch_mutation_authority": False,
        "live_capital_enabled": False,
        "trade_approval_control_enabled_count": int(
            bundle.get("trade_approval_control_enabled_count", 0) or 0
        ),
        "trade_rejection_control_enabled_count": int(
            bundle.get("trade_rejection_control_enabled_count", 0) or 0
        ),
        "order_place_control_enabled_count": int(
            bundle.get("order_place_control_enabled_count", 0) or 0
        ),
        "order_modify_control_enabled_count": int(
            bundle.get("order_modify_control_enabled_count", 0) or 0
        ),
        "position_resize_control_enabled_count": int(
            bundle.get("position_resize_control_enabled_count", 0) or 0
        ),
        "position_close_control_enabled_count": int(
            bundle.get("position_close_control_enabled_count", 0) or 0
        ),
        "order_cancel_control_enabled_count": int(
            bundle.get("order_cancel_control_enabled_count", 0) or 0
        ),
        "kill_switch_mutation_authority_count": int(
            bundle.get("kill_switch_mutation_authority_count", 0) or 0
        ),
        "kill_switch_action_mutates_state_count": int(
            bundle.get("kill_switch_action_mutates_state_count", 0) or 0
        ),
        "broker_write_allowed_count": int(bundle.get("broker_write_allowed_count", 0) or 0),
        "broker_post_called_count": int(bundle.get("broker_post_called_count", 0) or 0),
        "alpaca_post_called_count": int(bundle.get("alpaca_post_called_count", 0) or 0),
        "prediction_market_write_allowed_count": int(
            bundle.get("prediction_market_write_allowed_count", 0) or 0
        ),
        "paper_order_allowed_count": int(bundle.get("paper_order_allowed_count", 0) or 0),
        "paper_order_submitted_count": int(
            bundle.get("paper_order_submitted_count", 0) or 0
        ),
        "telegram_command_path_enabled_count": int(
            bundle.get("telegram_command_path_enabled_count", 0) or 0
        ),
        "live_endpoint_allowed_count": int(bundle.get("live_endpoint_allowed_count", 0) or 0),
        "live_capital_enabled_count": int(bundle.get("live_capital_enabled_count", 0) or 0),
        "secret_value_exposed_count": int(bundle.get("secret_value_exposed_count", 0) or 0),
        "raw_payload_exposed_count": int(bundle.get("raw_payload_exposed_count", 0) or 0),
        "local_path_exposed_count": int(bundle.get("local_path_exposed_count", 0) or 0),
        "authorization_header_exposed_count": int(
            bundle.get("authorization_header_exposed_count", 0) or 0
        ),
        "account_identifier_exposed_count": int(
            bundle.get("account_identifier_exposed_count", 0) or 0
        ),
        "broker_order_identifier_exposed_count": int(
            bundle.get("broker_order_identifier_exposed_count", 0) or 0
        ),
        "boundary": bundle.get("boundary")
        or "Q5-12 Signal Review is read-only and cannot call brokers or venues.",
    }


def _phase5_paper_trade_drill_public_status(settings: Settings) -> dict[str, Any]:
    runtime_bundle = _read_runtime_json(settings, PAPER_TRADE_DRILL_RUNTIME_ARTIFACT)
    recorded = runtime_bundle is not None
    bundle = runtime_bundle or build_phase5_paper_trade_drill(settings=settings)
    validation_errors = validate_phase5_paper_trade_drill_bundle(bundle)
    records = [
        record
        for record in bundle.get("records", [])
        if isinstance(record, dict)
    ]
    public_records = [
        {
            "artifact_id": record.get("artifact_id"),
            "step_key": record.get("step_key"),
            "step_label": record.get("step_label"),
            "step_order": int(record.get("step_order", 0) or 0),
            "source_key": record.get("source_key"),
            "backend_metric_name": record.get("backend_metric_name"),
            "backend_metric_value": record.get("backend_metric_value"),
            "backend_status": record.get("backend_status"),
            "display_status": record.get("display_status"),
            "display_derived_from_backend": record.get("display_derived_from_backend") is True,
            "ui_inferred_readiness": record.get("ui_inferred_readiness") is True,
            "step_passed": record.get("step_passed") is True,
            "blocked_reason": record.get("blocked_reason"),
            "broker_post_called": record.get("broker_post_called") is True,
            "broker_write_allowed": record.get("broker_write_allowed") is True,
            "live_capital_enabled": record.get("live_capital_enabled") is True,
            "phase7_proof_credit_allowed": record.get("phase7_proof_credit_allowed") is True,
        }
        for record in records
    ]
    return {
        "schema_version": bundle.get("schema_version", 1),
        "artifact_type": bundle.get("artifact_type", "phase5_paper_trade_drill_bundle"),
        "artifact_id": bundle.get("artifact_id", "phase5:q5-14:paper-trade-drill"),
        "phase": bundle.get("phase", "Q5"),
        "stage": bundle.get("stage", "Q5-14"),
        "status": bundle.get("status", "not_run") if recorded else "missing_fail_closed",
        "generated_at": bundle.get("generated_at"),
        "public_safe": bundle.get("public_safe") is True,
        "recorded": recorded,
        "event_log_required": bundle.get("event_log_required") is True,
        "event_log_written": bundle.get("event_log_written") is True,
        "event_log_event_count": int(bundle.get("event_log_event_count", 0) or 0),
        "validation_error_count": len(validation_errors),
        "canonical_source_count": int(bundle.get("canonical_source_count", 0) or 0),
        "paper_trade_drill_state": bundle.get("paper_trade_drill_state", "not_run"),
        "paper_trade_drill_complete": bundle.get("paper_trade_drill_complete") is True,
        "phase5_paper_trade_drill_implementation_ready": (
            bundle.get("phase5_paper_trade_drill_implementation_ready") is True
        ),
        "phase5_paper_trade_drill_exit_gate_passed": (
            bundle.get("phase5_paper_trade_drill_exit_gate_passed") is True
        ),
        "phase7_proof_credit_allowed": bundle.get("phase7_proof_credit_allowed") is True,
        "blockers": list(bundle.get("blockers", [])),
        "blocker_count": int(bundle.get("blocker_count", 0) or 0),
        "step_count": int(bundle.get("step_count", 0) or 0),
        "required_step_count": int(bundle.get("required_step_count", 0) or 0),
        "required_steps": list(bundle.get("required_steps", [])),
        "status_counts": dict(bundle.get("status_counts", {}) or {}),
        "backend_status_counts": dict(bundle.get("backend_status_counts", {}) or {}),
        "source_validation_error_count": int(
            bundle.get("source_validation_error_count", 0) or 0
        ),
        "source_bundle_count": int(bundle.get("source_bundle_count", 0) or 0),
        "source_bundles": dict(bundle.get("source_bundles", {}) or {}),
        "records": public_records,
        "paper_submit_approval_state": bundle.get("paper_submit_approval_state", "missing"),
        "paper_submit_approval_present": bundle.get("paper_submit_approval_present") is True,
        "paper_submit_path_available_count": int(
            bundle.get("paper_submit_path_available_count", 0) or 0
        ),
        "signal_review_record_count": int(bundle.get("signal_review_record_count", 0) or 0),
        "risk_review_count": int(bundle.get("risk_review_count", 0) or 0),
        "paper_size_eligible_count": int(bundle.get("paper_size_eligible_count", 0) or 0),
        "staged_order_count": int(bundle.get("staged_order_count", 0) or 0),
        "dry_run_receipt_count": int(bundle.get("dry_run_receipt_count", 0) or 0),
        "submitted_paper_order_count": int(
            bundle.get("submitted_paper_order_count", 0) or 0
        ),
        "broker_receipt_count": int(bundle.get("broker_receipt_count", 0) or 0),
        "open_position_count": int(bundle.get("open_position_count", 0) or 0),
        "position_open_lifecycle_satisfied": (
            bundle.get("position_open_lifecycle_satisfied") is True
        ),
        "closed_trade_count": int(bundle.get("closed_trade_count", 0) or 0),
        "postmortem_due_count": int(bundle.get("postmortem_due_count", 0) or 0),
        "telegram_dashboard_sync_status": bundle.get(
            "telegram_dashboard_sync_status",
            "not_run",
        ),
        "dashboard_backend_parity_error_count": int(
            bundle.get("dashboard_backend_parity_error_count", 0) or 0
        ),
        "dashboard_unsafe_control_count": int(
            bundle.get("dashboard_unsafe_control_count", 0) or 0
        ),
        "broker_post_called_count": int(bundle.get("broker_post_called_count", 0) or 0),
        "alpaca_post_called_count": int(bundle.get("alpaca_post_called_count", 0) or 0),
        "broker_write_allowed_count": int(bundle.get("broker_write_allowed_count", 0) or 0),
        "prediction_market_write_allowed_count": int(
            bundle.get("prediction_market_write_allowed_count", 0) or 0
        ),
        "telegram_live_notifications_allowed_count": int(
            bundle.get("telegram_live_notifications_allowed_count", 0) or 0
        ),
        "position_monitor_write_authority_count": int(
            bundle.get("position_monitor_write_authority_count", 0) or 0
        ),
        "position_close_allowed_count": int(bundle.get("position_close_allowed_count", 0) or 0),
        "position_resize_allowed_count": int(bundle.get("position_resize_allowed_count", 0) or 0),
        "order_cancel_allowed_count": int(bundle.get("order_cancel_allowed_count", 0) or 0),
        "live_capital_enabled_count": int(bundle.get("live_capital_enabled_count", 0) or 0),
        "live_endpoint_allowed_count": int(bundle.get("live_endpoint_allowed_count", 0) or 0),
        "phase7_proof_credit_allowed_count": int(
            bundle.get("phase7_proof_credit_allowed_count", 0) or 0
        ),
        "secret_value_exposed_count": int(bundle.get("secret_value_exposed_count", 0) or 0),
        "raw_payload_exposed_count": int(bundle.get("raw_payload_exposed_count", 0) or 0),
        "local_path_exposed_count": int(bundle.get("local_path_exposed_count", 0) or 0),
        "authorization_header_exposed_count": int(
            bundle.get("authorization_header_exposed_count", 0) or 0
        ),
        "broker_order_identifier_exposed_count": int(
            bundle.get("broker_order_identifier_exposed_count", 0) or 0
        ),
        "boundary": bundle.get("boundary")
        or "Q5-14 paper trade drill is approval-gated and cannot enable live capital.",
    }


def _phase5_certification_public_status(settings: Settings) -> dict[str, Any]:
    runtime_artifact = _read_runtime_json(settings, PHASE5_CERTIFICATION_RUNTIME_ARTIFACT)
    recorded = runtime_artifact is not None
    artifact = runtime_artifact or build_phase5_certification(settings=settings)
    validation_errors = validate_phase5_certification(artifact)
    gate_records = [
        record
        for record in artifact.get("gate_records", [])
        if isinstance(record, dict)
    ]
    public_gate_records = [
        {
            "source_stage": record.get("source_stage"),
            "label": record.get("label"),
            "artifact_key": record.get("artifact_key"),
            "source_status": record.get("source_status"),
            "backend_status": record.get("backend_status"),
            "display_status": record.get("display_status"),
            "display_derived_from_backend": (
                record.get("display_derived_from_backend") is True
            ),
            "ui_inferred_readiness": record.get("ui_inferred_readiness") is True,
            "gate_passed": record.get("gate_passed") is True,
            "recorded": record.get("recorded") is True,
            "validation_error_count": int(record.get("validation_error_count", 0) or 0),
            "failed_conditions": list(record.get("failed_conditions", [])),
            "blocking_unsafe_counts": dict(record.get("blocking_unsafe_counts", {}) or {}),
            "phase7_proof_credit_allowed": (
                record.get("phase7_proof_credit_allowed") is True
            ),
        }
        for record in gate_records
    ]
    return {
        "schema_version": artifact.get("schema_version", 1),
        "phase5_certification_schema_version": artifact.get(
            "phase5_certification_schema_version",
            1,
        ),
        "artifact_type": artifact.get("artifact_type", "phase5_certification"),
        "artifact_id": artifact.get("artifact_id", "phase5:q5-15:certification"),
        "phase": artifact.get("phase", "Q5"),
        "stage": artifact.get("stage", "Q5-15"),
        "status": artifact.get("status", "not_run") if recorded else "missing_fail_closed",
        "stage_status": artifact.get("stage_status", "not_run"),
        "generated_at": artifact.get("generated_at"),
        "public_safe": artifact.get("public_safe") is True,
        "recorded": recorded,
        "event_log_required": artifact.get("event_log_required") is True,
        "event_log_written": artifact.get("event_log_written") is True,
        "event_log_event_count": int(artifact.get("event_log_event_count", 0) or 0),
        "validation_error_count": len(validation_errors),
        "canonical_source_count": int(artifact.get("canonical_source_count", 0) or 0),
        "phase5_certified": artifact.get("phase5_certified") is True,
        "phase5_complete": artifact.get("phase5_complete") is True,
        "phase5_exit_gate": artifact.get("phase5_exit_gate") is True,
        "phase6_handoff_allowed": artifact.get("phase6_handoff_allowed") is True,
        "phase7_planning_allowed": artifact.get("phase7_planning_allowed") is True,
        "phase7_proof_credit_allowed": (
            artifact.get("phase7_proof_credit_allowed") is True
        ),
        "q5_stage_count": int(artifact.get("q5_stage_count", 0) or 0),
        "required_input_stage_count": int(
            artifact.get("required_input_stage_count", 0) or 0
        ),
        "required_input_stages": list(artifact.get("required_input_stages", [])),
        "input_gate_count": int(artifact.get("input_gate_count", 0) or 0),
        "input_gate_passed_count": int(
            artifact.get("input_gate_passed_count", 0) or 0
        ),
        "input_gate_blocked_count": int(
            artifact.get("input_gate_blocked_count", 0) or 0
        ),
        "gate_records": public_gate_records,
        "certification_blockers": list(artifact.get("certification_blockers", [])),
        "certification_blocker_count": int(
            artifact.get("certification_blocker_count", 0) or 0
        ),
        "paper_trade_drill_complete": artifact.get("paper_trade_drill_complete") is True,
        "paper_trade_drill_exit_gate_passed": (
            artifact.get("paper_trade_drill_exit_gate_passed") is True
        ),
        "submitted_paper_order_count": int(
            artifact.get("submitted_paper_order_count", 0) or 0
        ),
        "open_position_count": int(artifact.get("open_position_count", 0) or 0),
        "closed_trade_count": int(artifact.get("closed_trade_count", 0) or 0),
        "postmortem_due_count": int(artifact.get("postmortem_due_count", 0) or 0),
        "blocking_unsafe_count": int(artifact.get("blocking_unsafe_count", 0) or 0),
        "broker_write_allowed_count": int(
            artifact.get("broker_write_allowed_count", 0) or 0
        ),
        "prediction_market_write_allowed_count": int(
            artifact.get("prediction_market_write_allowed_count", 0) or 0
        ),
        "crypto_perps_write_allowed_count": int(
            artifact.get("crypto_perps_write_allowed_count", 0) or 0
        ),
        "telegram_live_notifications_allowed_count": int(
            artifact.get("telegram_live_notifications_allowed_count", 0) or 0
        ),
        "live_endpoint_allowed_count": int(
            artifact.get("live_endpoint_allowed_count", 0) or 0
        ),
        "live_capital_enabled_count": int(
            artifact.get("live_capital_enabled_count", 0) or 0
        ),
        "phase7_proof_credit_allowed_count": int(
            artifact.get("phase7_proof_credit_allowed_count", 0) or 0
        ),
        "boundary": artifact.get("boundary")
        or "Q5-15 certification is blocked until Q5-14 completes a paper lifecycle.",
    }


def _phase5_phase6_handoff_public_status(settings: Settings) -> dict[str, Any]:
    runtime_artifact = _read_runtime_json(settings, PHASE5_PHASE6_HANDOFF_RUNTIME_ARTIFACT)
    recorded = runtime_artifact is not None
    artifact = runtime_artifact or build_phase5_phase6_handoff(settings=settings)
    validation_errors = validate_phase5_phase6_handoff(artifact)
    return {
        "schema_version": artifact.get("schema_version", 1),
        "phase5_phase6_handoff_schema_version": artifact.get(
            "phase5_phase6_handoff_schema_version",
            1,
        ),
        "artifact_type": artifact.get("artifact_type", "phase5_phase6_handoff"),
        "artifact_id": artifact.get("artifact_id", "phase5:q5e-10:phase6-handoff"),
        "phase": artifact.get("phase", "Q5"),
        "stage": artifact.get("stage", "Q5E-10"),
        "status": artifact.get("status", "not_run") if recorded else "missing_fail_closed",
        "handoff_state": artifact.get("handoff_state", "not_run"),
        "generated_at": artifact.get("generated_at"),
        "public_safe": artifact.get("public_safe") is True,
        "recorded": recorded,
        "event_log_required": artifact.get("event_log_required") is True,
        "event_log_written": artifact.get("event_log_written") is True,
        "event_log_event_count": int(artifact.get("event_log_event_count", 0) or 0),
        "validation_error_count": len(validation_errors),
        "canonical_source_count": int(artifact.get("canonical_source_count", 0) or 0),
        "phase5_certified": artifact.get("phase5_certified") is True,
        "phase5_exit_gate": artifact.get("phase5_exit_gate") is True,
        "phase6_handoff_allowed": artifact.get("phase6_handoff_allowed") is True,
        "phase7_planning_allowed": artifact.get("phase7_planning_allowed") is True,
        "phase7_proof_credit_allowed": artifact.get("phase7_proof_credit_allowed") is True,
        "phase5_test_trades_count_for_phase7": (
            artifact.get("phase5_test_trades_count_for_phase7") is True
        ),
        "paper_trade_drill_complete": artifact.get("paper_trade_drill_complete") is True,
        "paper_trade_drill_exit_gate_passed": (
            artifact.get("paper_trade_drill_exit_gate_passed") is True
        ),
        "paper_trade_drill_blocker_count": int(
            artifact.get("paper_trade_drill_blocker_count", 0) or 0
        ),
        "downstream_staging_allowed_count": int(
            artifact.get("downstream_staging_allowed_count", 0) or 0
        ),
        "submitted_order_count": int(artifact.get("submitted_order_count", 0) or 0),
        "mirrored_order_count": int(artifact.get("mirrored_order_count", 0) or 0),
        "open_position_count": int(artifact.get("open_position_count", 0) or 0),
        "closed_trade_count": int(artifact.get("closed_trade_count", 0) or 0),
        "postmortem_due_count": int(artifact.get("postmortem_due_count", 0) or 0),
        "failed_reconciliation_count": int(
            artifact.get("failed_reconciliation_count", 0) or 0
        ),
        "guarded_postmortem_due_ready": (
            artifact.get("guarded_postmortem_due_ready") is True
        ),
        "guarded_postmortem_due_ref": artifact.get("guarded_postmortem_due_ref"),
        "source_validation_error_count": int(
            artifact.get("source_validation_error_count", 0) or 0
        ),
        "source_recorded_count": int(artifact.get("source_recorded_count", 0) or 0),
        "required_source_count": int(artifact.get("required_source_count", 0) or 0),
        "blockers": list(artifact.get("blockers", [])),
        "blocker_count": int(artifact.get("blocker_count", 0) or 0),
        "phase6_learning_loop_plan_allowed": (
            artifact.get("phase6_learning_loop_plan_allowed") is True
        ),
        "phase6_learning_loop_implementation_allowed": (
            artifact.get("phase6_learning_loop_implementation_allowed") is True
        ),
        "phase6_postmortem_ingestion_allowed": (
            artifact.get("phase6_postmortem_ingestion_allowed") is True
        ),
        "phase6_learning_write_allowed": (
            artifact.get("phase6_learning_write_allowed") is True
        ),
        "phase6_knowledge_graph_write_allowed": (
            artifact.get("phase6_knowledge_graph_write_allowed") is True
        ),
        "phase6_model_weight_update_allowed": (
            artifact.get("phase6_model_weight_update_allowed") is True
        ),
        "phase6_trust_score_update_allowed": (
            artifact.get("phase6_trust_score_update_allowed") is True
        ),
        "phase6_shadow_strategy_runner_allowed": (
            artifact.get("phase6_shadow_strategy_runner_allowed") is True
        ),
        "phase6_architect_policy_mutation_allowed": (
            artifact.get("phase6_architect_policy_mutation_allowed") is True
        ),
        "phase6_required_modules": list(artifact.get("phase6_required_modules", [])),
        "phase6_required_module_count": int(
            artifact.get("phase6_required_module_count", 0) or 0
        ),
        "recommended_next_stage": artifact.get(
            "recommended_next_stage",
            "Q6-0 Phase 6 re-entry and learning-loop implementation plan",
        ),
        "broker_post_called_count": int(artifact.get("broker_post_called_count", 0) or 0),
        "alpaca_post_called_count": int(artifact.get("alpaca_post_called_count", 0) or 0),
        "broker_write_allowed_count": int(
            artifact.get("broker_write_allowed_count", 0) or 0
        ),
        "prediction_market_write_allowed_count": int(
            artifact.get("prediction_market_write_allowed_count", 0) or 0
        ),
        "crypto_perps_write_allowed_count": int(
            artifact.get("crypto_perps_write_allowed_count", 0) or 0
        ),
        "live_endpoint_allowed_count": int(
            artifact.get("live_endpoint_allowed_count", 0) or 0
        ),
        "live_capital_enabled_count": int(
            artifact.get("live_capital_enabled_count", 0) or 0
        ),
        "phase7_proof_credit_allowed_count": int(
            artifact.get("phase7_proof_credit_allowed_count", 0) or 0
        ),
        "phase6_learning_write_allowed_count": int(
            artifact.get("phase6_learning_write_allowed_count", 0) or 0
        ),
        "phase6_knowledge_graph_write_allowed_count": int(
            artifact.get("phase6_knowledge_graph_write_allowed_count", 0) or 0
        ),
        "phase6_model_weight_update_allowed_count": int(
            artifact.get("phase6_model_weight_update_allowed_count", 0) or 0
        ),
        "phase6_trust_score_update_allowed_count": int(
            artifact.get("phase6_trust_score_update_allowed_count", 0) or 0
        ),
        "phase6_policy_mutation_allowed_count": int(
            artifact.get("phase6_policy_mutation_allowed_count", 0) or 0
        ),
        "boundary": artifact.get("boundary")
        or "Q5E-10 can plan Phase 6 only; it cannot implement learning writes.",
    }


def _phase6_learning_loop_public_status(settings: Settings) -> dict[str, Any]:
    return phase6_cockpit_visibility_public_status(settings=settings)


def _phase6_certification_public_status(settings: Settings) -> dict[str, Any]:
    return phase6_certification_public_status(settings=settings)


def _phase7_demo_proof_public_status(settings: Settings) -> dict[str, Any]:
    return phase7_cockpit_visibility_public_status(settings=settings)


def _rs9_learning_loop_public_status(settings: Settings) -> dict[str, Any]:
    return rs9_learning_loop_public_status(settings=settings)


def _rs10_final_paper_autonomy_public_status(
    payload: dict[str, Any],
    settings: Settings,
) -> dict[str, Any]:
    return rs10_final_paper_autonomy_public_status(
        settings=settings,
        payload=payload,
    )


def _team_lookup(payload: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {
        str(module.get("key", "")): module
        for module in payload.get("modules", [])
        if module.get("key")
    }


def _mission_team(payload: dict[str, Any]) -> list[dict[str, Any]]:
    modules = _team_lookup(payload)
    data_sources = payload.get("source_pipeline_summary", [])
    watching = payload.get("watching", [])
    online_sources = sum(1 for source in watching if source.get("status") == "online")
    paper_authority = payload.get("paper_authority_reconciliation", {})
    rs10 = payload.get("rs10_final_paper_autonomy_certification", {})
    learning = payload.get("rs9_learning_loop", {})

    def module_node(
        key: str,
        label: str,
        owner: str,
        one_line: str,
        source_key: str | None = None,
        status: str | None = None,
    ) -> dict[str, Any]:
        module = modules.get(source_key or key, {})
        node_status = status or str(module.get("status") or "pending")
        return {
            "key": key,
            "label": label,
            "owner": owner,
            "status": node_status,
            "one_line": one_line,
            "current_process": str(module.get("current_process") or one_line),
            "authority": str(module.get("authority") or "read_only"),
        }

    return [
        {
            "key": "intelligence_pipelines",
            "label": "Intelligence Pipelines",
            "owner": "Live data feeds",
            "status": "online" if online_sources else "pending",
            "one_line": f"{online_sources}/{len(watching)} sources online across {len(data_sources)} pipelines.",
            "current_process": "Collecting source observations for research context.",
            "authority": "observation_only",
        },
        module_node(
            "coo",
            "Chief Operating Officer",
            "Python Orchestrator",
            "Coordinates local modules, health checks, logs, and paper-mode boundaries.",
            source_key="coo",
        ),
        module_node(
            "research_analyst",
            "Research Analyst",
            "Local LLM",
            "Compresses noisy source observations into shadow research packets.",
            source_key="research_analyst",
        ),
        module_node(
            "strategy_lead",
            "Strategy Lead",
            "Frontier LLM",
            "Challenges research packets and prepares higher-level strategy reviews.",
            source_key="strategy_lead",
        ),
        module_node(
            "head_of_quant",
            "Head of Quant",
            "Quantum Compute",
            "Runs bounded oracle checks and classical fallback comparisons.",
            source_key="head_of_quant",
        ),
        module_node(
            "safety_policy",
            "Safety Policy",
            "Risk and execution gates",
            "Keeps paper autonomy gated by signal integrity, risk, policy, reconciliation, and receipts.",
            source_key="risk_agent",
            status="online" if paper_authority.get("current_blocker_count", 0) == 0 else "blocked",
        ),
        {
            "key": "paper_demo_state",
            "label": "Paper/Demo State",
            "owner": "PaperOps",
            "status": (
                "online"
                if rs10.get("final_paper_autonomy_certified") is True
                else str(rs10.get("status") or "pending")
            ),
            "one_line": "Tracks paper account lifecycle, positions, receipts, and postmortems.",
            "current_process": str(rs10.get("why_not_trading_now") or "Waiting for fresh eligible setups."),
            "authority": "guarded_paper_only",
        },
        {
            "key": "learning_review",
            "label": "Learning Review",
            "owner": "RS-9",
            "status": str(learning.get("status") or "waiting"),
            "one_line": "Turns postmortems into proposed learning updates without silent mutation.",
            "current_process": str(learning.get("learning_direction_reason") or "Waiting for closed-trade evidence."),
            "authority": "review_only",
        },
    ]


def _mission_source_ledger(watching: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        {
            "source_key": source.get("source_key"),
            "source_name": source.get("source_name"),
            "pipeline": source.get("pipeline"),
            "status": source.get("status"),
            "readiness": source.get("readiness"),
            "credential_status": source.get("credential_status"),
            "trust_score": source.get("trust_score"),
            "latency_ms": source.get("latency_ms"),
            "usable_for_research_context": source.get("usable_for_research_context"),
            "eligible_for_signal_review": source.get("eligible_for_signal_review"),
            "selection_status": source.get("selection_status"),
            "operator_action": source.get("operator_action"),
            "action_category": source.get("action_category"),
        }
        for source in watching
    ]


QADAM_NATIVE_STRATEGY_FAMILIES: dict[str, dict[str, Any]] = {
    "semiconductor_policy_options_asymmetry": {
        "rank": 1,
        "fit": "high",
        "fit_score": 0.94,
        "instrument": "semiconductors",
        "label": "Semiconductor Policy Options Asymmetry",
        "catalyst_focus": "export-control shifts, AI-chip supply constraints, and policy bargains",
        "qadam_fit_reason": (
            "Best match for Qadam's policy, filings, patents, macro, technical context, "
            "and liquid paper-proxy strengths."
        ),
        "route_fit": "strong_alpaca_paper_proxy_fit",
    },
    "defence_repricing_geopolitical_watch": {
        "rank": 2,
        "fit": "high",
        "fit_score": 0.9,
        "instrument": "defence",
        "label": "Defence Repricing Geopolitical Watch",
        "catalyst_focus": "defence posture shifts, conflict escalation, and procurement or policy signals",
        "qadam_fit_reason": (
            "Strong fit for conflict, news, filings, procurement, Strategy Lead challenge, "
            "and paper-tradable proxy expression."
        ),
        "route_fit": "strong_alpaca_paper_proxy_fit",
    },
    "silver_macro_liquidity_stress": {
        "rank": 3,
        "fit": "medium-high",
        "fit_score": 0.82,
        "instrument": "silver",
        "label": "Silver Macro Liquidity Stress",
        "catalyst_focus": "liquidity stress, rates shocks, and currency-confidence shifts",
        "qadam_fit_reason": (
            "Good fit for macro/liquidity evidence with simple, liquid paper-market expression."
        ),
        "route_fit": "clean_alpaca_paper_proxy_fit",
    },
    "crude_oil_energy_security_disruption": {
        "rank": 4,
        "fit": "medium",
        "fit_score": 0.72,
        "instrument": "crude_oil",
        "label": "Crude Oil Energy Security Disruption",
        "catalyst_focus": "energy security, shipping chokepoints, and conflict-fire disruption",
        "qadam_fit_reason": (
            "Conceptually strong for Qadam's physical and geopolitical feeds, but it depends "
            "on cleaner physical confirmation and risk-stage evidence."
        ),
        "route_fit": "conditional_paper_proxy_fit",
    },
    "prediction_market_geopolitical_dislocation": {
        "rank": 5,
        "fit": "conceptual-high execution-low",
        "fit_score": 0.64,
        "instrument": "prediction_markets",
        "label": "Prediction Market Geopolitical Dislocation",
        "catalyst_focus": "conflict escalation, narrative coordination, and policy shocks",
        "qadam_fit_reason": (
            "Intellectually aligned with Qadam's event reasoning, but current venue, adapter, "
            "and credential constraints make it weaker for guarded paper execution."
        ),
        "route_fit": "blocked_until_prediction_market_route_is_ready",
    },
}

STRATEGY_SETUP_BLOCKER_LABELS = {
    "signal_integrity_passed": "source corroboration",
    "risk_agent_paper_sizing": "paper risk sizing",
    "paper_order_staged_not_submitted": "paper staging readiness",
    "notional_within_paperops_cap": "positive paper notional inside cap",
    "execution_adapter_read_ready": "paper execution route readiness",
    "venue_read_available": "paper venue route readiness",
}


def _strategy_setup_record_by_key(
    paperops_qualified_setup_production: dict[str, Any],
) -> dict[str, dict[str, Any]]:
    return {
        str(record.get("strategy_family_key")): record
        for record in paperops_qualified_setup_production.get("candidate_setup_records", [])
        if isinstance(record, dict) and record.get("strategy_family_key")
    }


def _mission_strategy_families(
    phase4_strategy: dict[str, Any],
    paperops_qualified_setup_production: dict[str, Any],
) -> list[dict[str, Any]]:
    toggles = phase4_strategy.get("strategy_toggles", {}).get("toggles", [])
    toggle_by_key = {
        str(toggle.get("strategy_key")): toggle
        for toggle in toggles
        if isinstance(toggle, dict) and toggle.get("strategy_key")
    }
    setup_by_key = _strategy_setup_record_by_key(paperops_qualified_setup_production)
    keys = list(dict.fromkeys([*QADAM_NATIVE_STRATEGY_FAMILIES.keys(), *toggle_by_key.keys()]))
    families: list[dict[str, Any]] = []
    for key in keys:
        definition = QADAM_NATIVE_STRATEGY_FAMILIES.get(key, {})
        toggle = toggle_by_key.get(key, {})
        setup = setup_by_key.get(key, {})
        qualified_setup = setup.get("qualified_setup") is True
        setup_state = str(setup.get("setup_state") or "not_currently_qualified")
        rejection_reasons = [
            str(reason)
            for reason in setup.get("rejection_reasons", [])
            if str(reason).strip()
        ]
        if qualified_setup:
            current_state = "qualified_for_guarded_paper_review"
            current_reason = "Current guarded paper checks show a production-qualified paper setup."
        elif rejection_reasons:
            current_state = "waiting_on_required_gates"
            current_reason = "Waiting on " + ", ".join(
                STRATEGY_SETUP_BLOCKER_LABELS.get(reason, reason.replace("_", " "))
                for reason in rejection_reasons[:3]
            )
        else:
            current_state = "watching_for_evidence"
            current_reason = "No current production-qualified paper setup is exported for this family."
        label = str(
            toggle.get("label")
            or definition.get("label")
            or key.replace("_", " ").title()
        )
        families.append(
            {
                "key": key,
                "rank": int(definition.get("rank") or 99),
                "label": label,
                "instrument": str(setup.get("instrument") or definition.get("instrument") or "strategy_family"),
                "fit": str(definition.get("fit") or "review"),
                "fit_score": float(definition.get("fit_score") or 0),
                "catalyst_focus": str(definition.get("catalyst_focus") or "strategy-family catalyst"),
                "qadam_fit_reason": str(definition.get("qadam_fit_reason") or "Strategy family is visible in Qadam governance."),
                "route_fit": str(definition.get("route_fit") or "route_under_review"),
                "approval_state": str(toggle.get("approval_state") or "approved"),
                "toggle_state": str(toggle.get("toggle_state") or "visible"),
                "visible_in_cockpit": bool(toggle.get("visible_in_cockpit", True)),
                "current_state": current_state,
                "setup_state": setup_state,
                "qualified_setup": qualified_setup,
                "side": str(setup.get("side") or "not_determined"),
                "notional_gbp": float(setup.get("notional_gbp") or 0),
                "rejection_reasons": rejection_reasons,
                "current_reason": current_reason,
                "paper_order_submission_allowed": False,
                "broker_write_allowed": False,
                "live_capital_enabled": False,
            }
        )
    return sorted(families, key=lambda family: (family["rank"], family["label"]))


def _mission_strategy(
    decision_philosophy: dict[str, Any],
    *,
    phase4_strategy: dict[str, Any] | None = None,
    paperops_qualified_setup_production: dict[str, Any] | None = None,
) -> dict[str, Any]:
    ai_lens = decision_philosophy.get("ai_infrastructure_lens", {})
    strategy_families = _mission_strategy_families(
        phase4_strategy or {},
        paperops_qualified_setup_production or {},
    )
    qualified_family_count = sum(1 for family in strategy_families if family["qualified_setup"])
    return {
        "posture": "shadow_paper_strategy_with_second_order_ai_infrastructure_lens",
        "native_edge": {
            "name": "Asymmetric Catalyst Proxy Trading",
            "status": "active_qadam_native_strategy",
            "thesis": (
                "Qadam detects catalyst setups, challenges them with model review, verifies "
                "source quorum, sizes risk deterministically, and expresses only approved "
                "setups through guarded paper-tradable proxies."
            ),
            "why_this_fits_qadam": [
                "Python scripts provide deterministic gates, ledgers, sizing, idempotency, and audit trails.",
                "The local LLM is useful for low-cost triage, extraction, and recurring analyst packets.",
                "The frontier LLM is useful for contradiction checks, narrative synthesis, and Strategy Lead challenges.",
                "Q-CTRL is an uncertainty and optimization consultation layer, not execution authority.",
                "Canonical and supplemental data sources make source-quorum discipline more valuable than discretionary prediction.",
            ],
            "decision_spine": [
                "catalyst detected",
                "source quorum",
                "LLM challenge",
                "market proxy",
                "risk sizing",
                "guarded Alpaca Paper",
                "paper proof ledger",
            ],
            "summary": (
                "Every setup must survive evidence, reasoning, risk, duplicate-exposure, "
                "idempotency, and guarded Alpaca Paper route checks."
            ),
        },
        "why": decision_philosophy.get(
            "trading_philosophy",
            "Qadam uses private priors to ask sharper questions, then waits for live evidence and gates.",
        ),
        "akber_lens": {
            "status": "active_filter",
            "summary": (
                "Akber's 6-stage method remains the practical filter: context, catalyst, "
                "confirmation, risk, execution, and postmortem learning."
            ),
            "stages": [
                "context",
                "catalyst",
                "confirmation",
                "risk",
                "execution",
                "postmortem learning",
            ],
        },
        "strategy_family_count": len(strategy_families),
        "qualified_strategy_family_count": qualified_family_count,
        "strategy_families": strategy_families,
        "fit_matrix": strategy_families,
        "universe": [
            "prediction markets",
            "crude oil",
            "defence",
            "silver",
            "semiconductors",
        ],
        "ai_infrastructure_universe": ai_lens.get("target_bottlenecks", []),
        "reference_assets": ai_lens.get("reference_assets", []),
        "active_lens": {
            "name": ai_lens.get("name", "Second-order AI infrastructure beneficiary lens"),
            "status": ai_lens.get("status", "active_strategy_lens"),
            "thesis": ai_lens.get("thesis"),
            "decision_questions": ai_lens.get("decision_questions", []),
            "gating_role": ai_lens.get("gating_role"),
        },
        "decision_chain": decision_philosophy.get("decision_chain", []),
        "boundary": (
            "Strategy fit is public-safe context. It cannot create trade candidates, approve risk, "
            "stage or submit paper orders, write brokers, call live endpoints, or enable live capital."
        ),
    }


def _mission_trade_board(
    observed_signals: list[dict[str, Any]],
    candidates: list[dict[str, Any]],
    blocked_trades: list[dict[str, Any]],
    open_positions: list[dict[str, Any]],
    closed_trades: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    board: list[dict[str, Any]] = []
    for item in observed_signals[:4]:
        board.append(
            {
                "state": "observed",
                "instrument": item.get("instrument") or item.get("symbol"),
                "summary": item.get("summary") or item.get("catalyst") or "Observed signal under review.",
                "status": item.get("status", "watching"),
            }
        )
    for item in candidates[:4]:
        board.append(
            {
                "state": "candidate",
                "instrument": item.get("instrument"),
                "summary": item.get("catalyst") or item.get("thesis") or "Candidate under gated review.",
                "status": item.get("status", "candidate"),
            }
        )
    for item in blocked_trades[:4]:
        board.append(
            {
                "state": "blocked",
                "instrument": item.get("instrument"),
                "summary": item.get("blocked_reason") or "Blocked before execution.",
                "status": item.get("status", "blocked"),
            }
        )
    for item in open_positions[:4]:
        board.append(
            {
                "state": "open",
                "instrument": item.get("symbol") or item.get("instrument"),
                "summary": item.get("side") or "Open paper position.",
                "status": item.get("status", "open"),
            }
        )
    for item in closed_trades[:4]:
        board.append(
            {
                "state": "closed",
                "instrument": item.get("symbol") or item.get("instrument"),
                "summary": item.get("postmortem_status") or "Closed paper trade.",
                "status": item.get("status", "closed"),
            }
        )
    return board[:12]


def _mission_hypotheses(hypotheses: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        {
            "signal_id": item.get("signal_id"),
            "title": item.get("title"),
            "thesis": item.get("thesis"),
            "status": item.get("status"),
            "confidence": item.get("confidence"),
            "instrument_focus": item.get("instrument_focus"),
            "missing_corroboration": item.get("missing_correlations", []),
            "invalidation": item.get("invalidation"),
        }
        for item in hypotheses[:6]
    ]


def _diagnostic_dependent_surfaces(key: str) -> list[str]:
    surfaces = [
        "diagnostics.audit_sections",
        "scripts/check_cockpit_status.py",
        "dashboard diagnostics drawer",
    ]
    if key == "phase5_system_map":
        surfaces.extend(["dashboard overview operating flow", "dashboard operations system map"])
    if key.startswith("phase5_"):
        surfaces.extend(["Phase 5 dashboard checkers", "paper-trade readiness mirrors"])
    if key.startswith("phase6_"):
        surfaces.extend(["Phase 6 learning-loop checkers", "mission_control learning mirror"])
    if key.startswith("phase7_"):
        surfaces.extend(["Phase 7 proof-runner checks", "demo-proof continuity artifacts"])
    if key.startswith("rs9_"):
        surfaces.extend(["RS-9 learning-loop checks", "mission_control learning mirror"])
    if key.startswith("rs10_"):
        surfaces.extend(["RS-10 autonomy certification checks", "paper-autonomy safety strip"])
    if key.startswith("paperops_") or key.startswith("paper_"):
        surfaces.extend(["PaperOps automation checks", "dashboard trades and operations views"])
    return list(dict.fromkeys(surfaces))


def _diagnostics(payload: dict[str, Any]) -> dict[str, Any]:
    diagnostic_keys = [
        "phase3_readiness",
        "phase4_strategy",
        "phase5_layer_b_readiness",
        "phase5_kill_switch_ledger",
        "phase5_execution_adapter_status",
        "phase5_paper_order_staging_gate",
        "phase5_alpaca_paper_dry_run",
        "phase5_paper_submit_enablement_gate",
        "phase5_prediction_market_adapter",
        "phase5_telegram_notifier",
        "phase5_position_monitor",
        "phase5_signal_review",
        "phase5_paper_trade_drill",
        "phase5_certification",
        "phase5_phase6_handoff",
        "phase5_system_map",
        "phase6_learning_loop",
        "phase6_certification",
        "phase7_demo_proof",
        "rs9_learning_loop",
        "rs10_final_paper_autonomy_certification",
        "paper_live_activation",
        "paper_live_qctrl_product_access",
        "paper_operational_mode",
        "paperops_alpaca_paper_submit_enablement",
        "paperops_alpaca_paper_post",
        "paperops_first_week_paper_trade_mandate",
        "paperops_paper_lifecycle_polling_enablement",
        "paperops_paper_lifecycle_poller",
        "paperops_guarded_paper_exit_enablement",
        "paperops_paper_exit_path",
        "paperops_notification_review",
        "paperops_submit_regression_guard",
        "paperops_source_gap_visibility",
        "paperops_30_day_operations",
        "paperops_opportunity_scan_cadence",
        "paperops_cockpit_notification_upgrade",
        "paper_live_certification",
        "paperops_active_paper_trading_automation",
        "paper_authority_reconciliation",
        "paperops_qualified_setup_production",
        "paperops_auto_approval_staged_order",
        "paperops_qctrl_consultation",
        "paper_lifecycle_portfolio_postmortem",
    ]
    process_console = payload.get("process_console", [])
    event_trail = (
        process_console
        if isinstance(process_console, list)
        else process_console.get("events", [])
    )
    retained_keys = [
        {
            "key": key,
            "migration_status": "retained_for_checker_and_diagnostics_compatibility",
            "retention_reason": (
                "Still referenced by dashboard diagnostics, checkers, automations, "
                "or status mirrors."
            ),
            "dependent_surfaces": _diagnostic_dependent_surfaces(key),
            "namespace_shadow": f"diagnostics.audit_sections.{key}",
        }
        for key in diagnostic_keys
    ]
    return {
        "schema_version": 1,
        "status": "diagnostics_available",
        "system_map": payload.get("phase5_system_map", {}),
        "event_trail": event_trail,
        "process_console": process_console,
        "source_heartbeat_history": payload.get("source_heartbeat_history", []),
        "governance_forum": payload.get("fund_manager_notes", {}),
        "telegram": payload.get("communications", {}),
        "kill_switch_ledger": payload.get("phase5_kill_switch_ledger", {}),
        "audit_sections": {
            key: payload.get(key, {})
            for key in diagnostic_keys
        },
        "prune_candidates": diagnostic_keys,
        "prune_audit": {
            "schema_version": 1,
            "status": "retained_due_to_active_dependencies",
            "top_level_key_count": len(payload),
            "candidate_count": len(diagnostic_keys),
            "retained_count": len(retained_keys),
            "safe_to_remove_count": 0,
            "retained_top_level_keys": retained_keys,
            "safe_to_remove_keys": [],
            "boundary": (
                "No raw top-level diagnostic key is removed until all referencing "
                "checkers, automations, mirrors, and diagnostics have migrated."
            ),
        },
        "boundary": (
            "Diagnostics are read-only audit surfaces for the drawer. They preserve "
            "current checker dependencies and cannot change trading authority."
        ),
    }


def _mission_control(payload: dict[str, Any], source_label: str = "status_contract") -> dict[str, Any]:
    watching = payload.get("watching", [])
    source_counts = Counter(source.get("status", "unknown") for source in watching)
    pipeline_summary = payload.get("source_pipeline_summary", [])
    missing_credentials = sum(int(pipeline.get("missing_credential_count", 0)) for pipeline in pipeline_summary)
    configured_sources = [
        str(source.get("source_name") or source.get("source_key"))
        for source in watching
        if source.get("credential_status") == "configured"
    ]
    live_sources = [
        str(source.get("source_name") or source.get("source_key"))
        for source in watching
        if source.get("status") == "online"
    ]
    connected_sources = list(dict.fromkeys(configured_sources + live_sources))

    cognition = payload.get("cognition", {})
    trade_layer = payload.get("trade_layer", {})
    capital = payload.get("capital", {})
    decision_philosophy = payload.get("decision_philosophy", {})
    communications = payload.get("communications", {}).get("telegram", {})
    forbidden_actions = payload.get("forbidden_actions", [])
    risk_agent = payload.get("risk_agent", {})
    execution_policy = payload.get("execution_policy", {})
    paper_submit_receipt = payload.get("paper_submit_receipt", {})
    quantum_oracle = payload.get("quantum_oracle", {})
    durable_ingestion = payload.get("durable_ingestion", {})
    yahoo_finance = payload.get("yahoo_finance", {})
    preference_mcp = payload.get("preference_mcp", {})
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
    phase7_demo_proof = payload.get("phase7_demo_proof", {})
    rs9_learning_loop = payload.get("rs9_learning_loop", {})
    rs10_final_paper_autonomy = payload.get(
        "rs10_final_paper_autonomy_certification",
        {},
    )
    paper_live_activation = payload.get("paper_live_activation", {})
    paper_live_qctrl_product_access = payload.get("paper_live_qctrl_product_access", {})
    paper_operational_mode = payload.get("paper_operational_mode", {})
    paperops_submit_enablement = payload.get(
        "paperops_alpaca_paper_submit_enablement",
        {},
    )
    paperops_alpaca_post = payload.get("paperops_alpaca_paper_post", {})
    paperops_first_week_mandate = payload.get(
        "paperops_first_week_paper_trade_mandate",
        {},
    )
    paperops_lifecycle_polling_enablement = payload.get(
        "paperops_paper_lifecycle_polling_enablement",
        {},
    )
    paperops_lifecycle_poller = payload.get("paperops_paper_lifecycle_poller", {})
    paperops_guarded_exit_enablement = payload.get(
        "paperops_guarded_paper_exit_enablement",
        {},
    )
    paperops_exit_path = payload.get("paperops_paper_exit_path", {})
    paperops_closed_trade_funnel = payload.get("paperops_closed_trade_funnel", {})
    paperops_lifecycle_mirror_freshness = payload.get(
        "paperops_lifecycle_mirror_freshness",
        {},
    )
    paperops_close_to_ledger = payload.get("paperops_close_to_ledger", {})
    paperops_notification_review = payload.get("paperops_notification_review", {})
    paperops_submit_regression_guard = payload.get(
        "paperops_submit_regression_guard",
        {},
    )
    paperops_source_gap_visibility = payload.get(
        "paperops_source_gap_visibility",
        {},
    )
    paperops_30_day_operations = payload.get("paperops_30_day_operations", {})
    paperops_opportunity_scan = payload.get("paperops_opportunity_scan_cadence", {})
    paperops_cockpit_notification_upgrade = payload.get(
        "paperops_cockpit_notification_upgrade",
        {},
    )
    paper_live_certification = payload.get("paper_live_certification", {})
    paperops_active_automation = payload.get(
        "paperops_active_paper_trading_automation",
        {},
    )
    paperops_qualified_setup_production = payload.get(
        "paperops_qualified_setup_production",
        {},
    )
    paperops_auto_approval_staged_order = payload.get(
        "paperops_auto_approval_staged_order",
        {},
    )
    paperops_qctrl = payload.get("paperops_qctrl_consultation", {})
    paper_lifecycle_postmortem = payload.get(
        "paper_lifecycle_portfolio_postmortem",
        {},
    )
    phase1_data_spine = payload.get("phase1_data_spine", {})
    operator_inbox = payload.get("operator_inbox", {})

    hypotheses = cognition.get("hypotheses", [])
    evidence_packets = cognition.get("evidence_packets", [])
    research_goal_records = cognition.get("research_goal_records", [])
    research_goal_status = cognition.get("research_goals", {})
    strategy_packets = cognition.get("strategy_lead_packets", [])
    local_assessments = cognition.get("local_research_assessments", [])
    phase2_cycle = cognition.get("phase2_shadow_cycle", {})
    observed_signals = trade_layer.get("watching", [])
    candidates = trade_layer.get("candidates", [])
    blocked_trades = trade_layer.get("blocked", [])
    open_positions = capital.get("open_positions", [])
    orders = capital.get("orders", [])
    closed_trades = capital.get("closed_trades", [])

    live_capital_enabled = bool(capital.get("live_capital_enabled"))
    broker_write_allowed = any(
        bool(section.get("broker_write_allowed_count"))
        for section in (
            risk_agent,
            execution_policy,
            payload.get("staged_paper_order", {}),
            payload.get("broker_reconciliation", {}),
            paper_submit_receipt,
        )
    )
    current_balance = float(capital.get("current_balance_gbp") or capital.get("starting_balance_gbp") or 0)
    pnl_total = float(capital.get("realized_pnl_gbp") or 0) + float(capital.get("unrealized_pnl_gbp") or 0)
    phase1_data_spine_ok = phase1_data_spine.get("status") == "ok"
    phase1_operational_status = (
        "operational_with_optional_missing_credentials"
        if phase1_data_spine_ok
        else "not_ready"
    )

    if candidates:
        next_trade_state = "candidate_review"
        next_trade_summary = f"{len(candidates)} candidate ideas are waiting behind risk and execution gates."
    elif observed_signals:
        next_trade_state = "observed_signal_review"
        next_trade_summary = f"{len(observed_signals)} observed signals are being watched, but none are orders."
    elif blocked_trades:
        next_trade_state = "blocked_review"
        next_trade_summary = f"{len(blocked_trades)} trade ideas are blocked before execution."
    else:
        next_trade_state = "no_trade_candidate"
        next_trade_summary = "No executable trade candidate exists in the current public-safe snapshot."

    paper_order_submitted_count = int(
        paper_submit_receipt.get("paper_order_submitted_count")
        or len(
            [
                order
                for order in orders
                if str(order.get("status", "")).lower()
                in {"submitted", "accepted", "filled", "open", "partially_filled"}
            ]
        )
        or 0
    )
    postmortem_due_count = int(
        paper_lifecycle_postmortem.get(
            "postmortem_due_count",
            capital.get("postmortem_due_count", 0),
        )
        or 0
    )
    operator_high_count = int(operator_inbox.get("high_or_critical_item_count", 0) or 0)
    operator_open_count = int(operator_inbox.get("open_item_count", 0) or 0)
    telegram_command_authority = bool(operator_inbox.get("telegram_command_authority"))
    source_tone = (
        "degraded"
        if missing_credentials or source_counts.get("degraded", 0)
        else "online"
    )
    thinking_tone = (
        "online"
        if local_assessments or strategy_packets or phase2_cycle.get("status") == "ok"
        else "pending"
    )
    trade_tone = "pending" if candidates or observed_signals else "online"
    blocked_tone = (
        "blocked"
        if operator_high_count or postmortem_due_count
        else ("pending" if blocked_trades or missing_credentials else "online")
    )
    closed_trade_funnel_blocker = (
        paperops_closed_trade_funnel.get("next_required_action")
        if paperops_closed_trade_funnel.get("blocked_stage")
        else None
    )
    paperops_blocker = (
        closed_trade_funnel_blocker
        or paperops_active_automation.get("why_not_trading_now")
        or paper_live_certification.get(
            "paper_live_unattended_execution_delegation_reason"
        )
        or paperops_active_automation.get("idle_reason")
        or next_trade_summary
    )
    if operator_high_count:
        next_action = {
            "label": "Review Chief Operating Officer inbox",
            "href": "#operations",
            "tone": "blocked",
            "summary": f"{operator_high_count} high-priority Chief Operating Officer items need review before Qadam advances.",
        }
    elif postmortem_due_count:
        next_action = {
            "label": "Review paper postmortems",
            "href": "#trades",
            "tone": "blocked",
            "summary": f"{postmortem_due_count} closed paper trade postmortems are due before learning can update.",
        }
    elif candidates:
        next_action = {
            "label": "Review trade candidates",
            "href": "#trades",
            "tone": "pending",
            "summary": f"{len(candidates)} candidates are visible, but risk and execution gates still decide.",
        }
    elif blocked_trades:
        next_action = {
            "label": "Review blocked ideas",
            "href": "#trades",
            "tone": "pending",
            "summary": f"{len(blocked_trades)} trade ideas are blocked before execution.",
        }
    elif missing_credentials or source_counts.get("degraded", 0):
        next_action = {
            "label": "Review source health",
            "href": "#evidence",
            "tone": "degraded",
            "summary": f"{missing_credentials} missing credentials and {int(source_counts.get('degraded', 0))} degraded sources are visible.",
        }
    else:
        next_action = {
            "label": "Continue monitoring",
            "href": "#mission-control",
            "tone": "online",
            "summary": "No urgent Fund Manager intervention is visible in the public-safe snapshot.",
        }

    mission_brief = {
        "schema_version": 1,
        "status": "ok",
        "question_count": 7,
        "summary": (
            "Seven-question Fund Manager brief for sources, reasoning, authority, "
            "trade intent, paper activity, portfolio value, and blockers."
        ),
        "questions": [
            {
                "key": "watching",
                "question": "What is Qadam watching?",
                "answer": f"{int(source_counts.get('online', 0))}/{len(watching)} sources online across {len(pipeline_summary)} pipelines.",
                "tone": source_tone,
                "href": "#evidence",
                "summary": (
                    f"{len(connected_sources)} configured or connected sources are visible; "
                    f"{missing_credentials} credentials are missing; durable replay is "
                    f"{durable_ingestion.get('replay_status', 'unknown')}."
                ),
                "metrics": [
                    {"label": "Online sources", "value": int(source_counts.get("online", 0))},
                    {"label": "Total sources", "value": len(watching)},
                    {"label": "Missing credentials", "value": missing_credentials},
                ],
            },
            {
                "key": "thinking",
                "question": "What is Qadam thinking about next?",
                "answer": (
                    f"{int(research_goal_status.get('active_goal_count', len(research_goal_records)) or 0)} "
                    f"research goals, {len(hypotheses)} hypotheses, {len(evidence_packets)} evidence packets."
                ),
                "tone": thinking_tone,
                "href": "#reasoning",
                "summary": (
                    f"Local Research Analyst assessments: {len(local_assessments)}; "
                    f"Strategy Lead packets: {len(strategy_packets)}; "
                    f"Signal Integrity: {cognition.get('signal_integrity', {}).get('status', 'pending')}."
                ),
                "metrics": [
                    {"label": "Research goals", "value": int(research_goal_status.get("active_goal_count", len(research_goal_records)) or 0)},
                    {"label": "Hypotheses", "value": len(hypotheses)},
                    {"label": "Strategy packets", "value": len(strategy_packets)},
                ],
            },
            {
                "key": "forbidden",
                "question": "What is Qadam forbidden from doing?",
                "answer": f"{len(forbidden_actions)} hard safety stops; live capital and broker-write authority are off.",
                "tone": "online" if not live_capital_enabled and not broker_write_allowed and not telegram_command_authority else "blocked",
                "href": "#operations",
                "summary": (
                    "The dashboard, Telegram intake, LLMs, data sources, and quantum oracle cannot approve, "
                    "place, modify, close, fund, or bypass risk checks for trades."
                ),
                "metrics": [
                    {"label": "Live capital", "value": "off" if not live_capital_enabled else "enabled"},
                    {"label": "Broker write", "value": "off" if not broker_write_allowed else "enabled"},
                    {"label": "Telegram commands", "value": "off" if not telegram_command_authority else "enabled"},
                ],
            },
            {
                "key": "considering",
                "question": "Which trades are candidates or blocked?",
                "answer": (
                    f"{len(candidates)} candidates, {len(blocked_trades)} blocked ideas, "
                    f"{len(observed_signals)} observed signals."
                ),
                "tone": trade_tone if not blocked_trades else "pending",
                "href": "#trades",
                "summary": next_trade_summary,
                "metrics": [
                    {"label": "Observed", "value": len(observed_signals)},
                    {"label": "Candidates", "value": len(candidates)},
                    {"label": "Blocked", "value": len(blocked_trades)},
                ],
            },
            {
                "key": "traded",
                "question": "What has Qadam traded on paper?",
                "answer": (
                    f"{paper_order_submitted_count} submitted paper orders, "
                    f"{len(open_positions)} open positions, {len(closed_trades)} closed trades."
                ),
                "tone": "online" if paper_order_submitted_count or open_positions or closed_trades else "pending",
                "href": "#trades",
                "summary": (
                    "Paper activity is mirrored from the local account and ledgers. "
                    "It is evidence for review, not live-capital authority."
                ),
                "metrics": [
                    {"label": "Paper orders", "value": paper_order_submitted_count},
                    {"label": "Open positions", "value": len(open_positions)},
                    {"label": "Closed trades", "value": len(closed_trades)},
                ],
            },
            {
                "key": "portfolio",
                "question": "What is the portfolio worth?",
                "answer": f"GBP {current_balance:,.2f}; total paper P&L GBP {pnl_total:,.2f}.",
                "tone": "online" if capital.get("connection_status") in {"ok", "live", "mirrored"} else "pending",
                "href": "#trades",
                "summary": (
                    f"Portfolio value source is {paper_lifecycle_postmortem.get('portfolio_value_source', capital.get('portfolio_value_source', 'unknown'))}; "
                    f"{postmortem_due_count} postmortems due."
                ),
                "metrics": [
                    {"label": "Balance GBP", "value": round(current_balance, 2)},
                    {"label": "Total P&L GBP", "value": round(pnl_total, 2)},
                    {"label": "Postmortems due", "value": postmortem_due_count},
                ],
            },
            {
                "key": "blocked",
                "question": "Why is Qadam blocked or waiting?",
                "answer": next_action["label"],
                "tone": blocked_tone,
                "href": next_action["href"],
                "summary": paperops_blocker,
                "metrics": [
                    {"label": "COO open", "value": operator_open_count},
                    {"label": "High priority", "value": operator_high_count},
                    {"label": "Postmortems due", "value": postmortem_due_count},
                ],
            },
        ],
        "navigation": [
            {"key": "mission", "label": "Mission", "href": "#mission-control"},
            {"key": "map", "label": "Map", "href": "#system-map"},
            {"key": "sources", "label": "Sources", "href": "#evidence"},
            {"key": "reasoning", "label": "Reasoning", "href": "#reasoning"},
            {"key": "trades", "label": "Trades", "href": "#trades"},
            {"key": "portfolio", "label": "Portfolio", "href": "#trades"},
            {"key": "safety", "label": "Safety", "href": "#operations"},
            {"key": "inbox", "label": "Inbox", "href": "#operations"},
            {"key": "runtime", "label": "Runtime", "href": "#operations"},
        ],
        "next_action": next_action,
        "authority": {
            "live_capital_enabled": live_capital_enabled,
            "broker_write_allowed": broker_write_allowed,
            "dashboard_write_authority": False,
            "telegram_command_authority": telegram_command_authority,
            "llm_execution_authority": False,
            "quantum_execution_authority": False,
        },
        "boundary": (
            "RS-8 Mission Brief is read-only. It cannot approve, place, modify, "
            "resize, close, fund, or verify performance credit for trades."
        ),
    }

    return {
        "schema_version": 2,
        "status": "read_only_mission_control",
        "source": source_label,
        "headline": (
            f"{int(source_counts.get('online', 0))}/{len(watching)} sources online; "
            f"{int(research_goal_status.get('active_goal_count', len(research_goal_records)) or 0)} research goals; "
            f"{len(hypotheses)} hypotheses; {len(candidates)} candidates; "
            f"{len(open_positions)} open positions; live capital "
            f"{'enabled' if live_capital_enabled else 'disabled'}."
        ),
        "team": _mission_team(payload),
        "data_sources": {
            "ok": int(source_counts.get("online", 0)),
            "degraded": int(source_counts.get("degraded", 0)),
            "missing_credentials": missing_credentials,
            "quorum": {
                "status": phase1_operational_status,
                "online_count": int(source_counts.get("online", 0)),
                "total_count": len(watching),
                "pipeline_count": len(pipeline_summary),
                "canonical_source_count": phase1_data_spine.get(
                    "canonical_source_count",
                    EXPECTED_SOURCE_COUNT,
                ),
                "expected_canonical_source_count": EXPECTED_SOURCE_COUNT,
            },
            "ledger": _mission_source_ledger(watching),
            "total_count": len(watching),
            "online_count": int(source_counts.get("online", 0)),
            "degraded_count": int(source_counts.get("degraded", 0)),
            "pending_count": int(source_counts.get("pending", 0)),
            "local_only_count": int(source_counts.get("local_only", 0) + source_counts.get("local-only", 0)),
            "missing_credential_count": missing_credentials,
            "pipeline_count": len(pipeline_summary),
            "logged_in_count": len(configured_sources),
            "logged_in_sources": configured_sources[:12],
            "connected_sources": connected_sources[:12],
            "phase1_data_spine_status": phase1_data_spine.get("status", "missing"),
            "phase1_data_spine_operational_status": phase1_operational_status,
            "canonical_source_count": phase1_data_spine.get(
                "canonical_source_count",
                EXPECTED_SOURCE_COUNT,
            ),
            "expected_canonical_source_count": EXPECTED_SOURCE_COUNT,
            "promoted_adapter_count": phase1_data_spine.get(
                "promoted_adapter_count",
                len(PROMOTED_ADAPTER_STATUS),
            ),
            "expected_promoted_adapter_count": len(PROMOTED_ADAPTER_STATUS),
            "provider_decision_source_count": phase1_data_spine.get(
                "provider_decision_source_count",
                0,
            ),
            "provider_selected_pending_adapter_count": phase1_data_spine.get(
                "provider_selected_pending_adapter_count",
                0,
            ),
            "provider_decision_marketplace_disabled_count": phase1_data_spine.get(
                "provider_decision_marketplace_disabled_count",
                0,
            ),
            "provider_decision_local_bridge_count": phase1_data_spine.get(
                "provider_decision_local_bridge_count",
                0,
            ),
            "provider_decision_credential_required_now_count": phase1_data_spine.get(
                "provider_decision_credential_required_now_count",
                0,
            ),
            "optional_missing_credential_source_count": phase1_data_spine.get(
                "optional_missing_credential_source_count",
                missing_credentials,
            ),
            "source_gap_visibility_status": paperops_source_gap_visibility.get(
                "status",
                "not_run",
            ),
            "source_gap_policy_status": paperops_source_gap_visibility.get(
                "source_gap_policy_status",
                "not_run",
            ),
            "optional_source_gap_count": paperops_source_gap_visibility.get(
                "optional_gap_count",
                0,
            ),
            "optional_source_gap_keys": paperops_source_gap_visibility.get(
                "optional_gap_keys",
                [],
            ),
            "optional_source_gap_records": paperops_source_gap_visibility.get(
                "optional_gap_records",
                [],
            ),
            "required_source_gap_count": paperops_source_gap_visibility.get(
                "required_gap_count",
                0,
            ),
            "trade_blocking_source_gap_count": paperops_source_gap_visibility.get(
                "trade_blocking_source_gap_count",
                0,
            ),
            "source_gap_silent_blocker_count": paperops_source_gap_visibility.get(
                "silent_blocker_count",
                0,
            ),
            "source_gap_blocker_count": paperops_source_gap_visibility.get(
                "blocker_count",
                0,
            ),
            "durable_replay_status": durable_ingestion.get("replay_status", "unknown"),
            "durable_replayed_source_count": durable_ingestion.get("replayed_source_count", 0),
            "durable_expected_source_count": durable_ingestion.get("expected_source_count", 0),
            "supplemental_market_confirmation_status": yahoo_finance.get("status", "not_configured"),
            "yahoo_finance_degraded_reason": yahoo_finance.get("degraded_reason"),
            "preference_mcp_status": preference_mcp.get("status", "not_exported"),
            "preference_mcp_identity_status": preference_mcp.get("identity_status", "not_verified"),
            "preference_mcp_quota_status": preference_mcp.get("quota_status", "unknown"),
            "preference_mcp_catalog_status": preference_mcp.get("catalog_status", "not_run"),
            "preference_mcp_domain_pack_count": preference_mcp.get("approved_domain_pack_count", 0),
            "preference_mcp_provenance_status": preference_mcp.get("provenance_status", "not_run"),
            "preference_mcp_shadow_context_status": preference_mcp.get("shadow_context_status", "not_run"),
            "preference_mcp_degraded_reason": preference_mcp.get("degraded_reason"),
            "boundary": (
                "Configured and connected sources are observation inputs only; they cannot create orders. "
                "Supplemental data planes are observation inputs only."
            ),
        },
        "durable_spine": {
            "status": durable_ingestion.get("status", "unknown"),
            "service_status": durable_ingestion.get("service_status", "unknown"),
            "contract_status": durable_ingestion.get("contract_status", "unknown"),
            "replay_status": durable_ingestion.get("replay_status", "unknown"),
            "observation_count": durable_ingestion.get("observation_count", 0),
            "replayed_source_count": durable_ingestion.get("replayed_source_count", 0),
            "expected_source_count": durable_ingestion.get("expected_source_count", 0),
            "missing_source_count": durable_ingestion.get("missing_source_count", 0),
            "source_spine_ready": phase1_data_spine_ok,
            "operational_status": phase1_operational_status,
            "canonical_source_count": phase1_data_spine.get(
                "canonical_source_count",
                EXPECTED_SOURCE_COUNT,
            ),
            "promoted_adapter_count": phase1_data_spine.get(
                "promoted_adapter_count",
                len(PROMOTED_ADAPTER_STATUS),
            ),
            "optional_missing_credential_source_count": phase1_data_spine.get(
                "optional_missing_credential_source_count",
                missing_credentials,
            ),
            "latest_observed_at": durable_ingestion.get("latest_observed_at"),
            "next_step": durable_ingestion.get("next_step", "Verify durable replay readiness."),
            "write_authority": False,
            "signal_authority": False,
            "order_authority": False,
            "boundary": durable_ingestion.get(
                "boundary",
                "Read-only durable ingestion readiness. It cannot create signals, candidates, orders, or broker writes.",
            ),
        },
        "trading_philosophy": {
            "status": decision_philosophy.get("status", "pending"),
            "summary": decision_philosophy.get(
                "trading_philosophy",
                "Qadam generates hypotheses from private priors, but live evidence and gates decide what can advance.",
            ),
            "decision_chain": decision_philosophy.get("decision_chain", []),
            "ai_infrastructure_lens": decision_philosophy.get("ai_infrastructure_lens", {}),
            "private_prior_count": decision_philosophy.get("foundational_prior_count", 0),
            "current_self_directive": [
                "Use the worldview to ask sharper questions, not as evidence.",
                "Require live-source corroboration before signal confidence improves.",
                "Let the local Research Analyst compress noisy observations.",
                "Let the Strategy Lead challenge packets before risk review.",
                "Use the Head of Quant as a bounded oracle only after a testable scenario exists.",
                "Keep paper orders blocked until Signal Integrity, Risk, Execution Policy, reconciliation, and receipt gates pass.",
            ],
            "boundary": decision_philosophy.get(
                "boundary",
                "Worldview is a private prior only, not a trade trigger.",
            ),
        },
        "strategy": _mission_strategy(
            decision_philosophy,
            phase4_strategy=phase4_strategy,
            paperops_qualified_setup_production=paperops_qualified_setup_production,
        ),
        "system_stack": {
            "coo": _module_status(payload, "event_log"),
            "data_spine": phase1_data_spine.get("status", _module_status(payload, "watching")),
            "data_spine_operational_status": phase1_operational_status,
            "durable_spine": durable_ingestion.get("contract_status", "unknown"),
            "local_llm": _module_status(payload, "research_analyst"),
            "frontier_llm": _module_status(payload, "strategy_lead"),
            "quant_oracle": _module_status(payload, "head_of_quant"),
            "quant_oracle_backend": quantum_oracle.get("latest_backend", "classical_fallback"),
            "quant_oracle_mode": quantum_oracle.get("latest_local_simulation_mode", "not_run"),
            "quant_oracle_recommendation": quantum_oracle.get("latest_recommendation", "not_run"),
            "paper_live_activation": paper_live_activation.get("status", "not_run"),
            "paper_live_activation_approved": paper_live_activation.get(
                "paper_live_activation_approved",
                False,
            ),
            "paper_live_activation_system_approval_logged": paper_live_activation.get(
                "paper_trading_system_approval_logged",
                False,
            ),
            "paper_live_qctrl_product_access": paper_live_qctrl_product_access.get(
                "status",
                "not_run",
            ),
            "paper_live_qctrl_product_access_verified": (
                paper_live_qctrl_product_access.get("product_access_verified", False)
            ),
            "paper_live_qctrl_provider_call_count": (
                paper_live_qctrl_product_access.get("provider_call_count", 0)
            ),
            "paper_operational_mode": paper_operational_mode.get("status", "not_run"),
            "paper_operational_mode_effective": paper_operational_mode.get(
                "paper_operational_mode_effective",
                False,
            ),
            "paper_operational_mode_runtime_override": paper_operational_mode.get(
                "runtime_artifact_override_enabled",
                False,
            ),
            "qctrl_paper_consultation": paperops_qctrl.get("status", "not_run"),
            "qctrl_paper_provider_call_count": paperops_qctrl.get("provider_call_count", 0),
            "paperops_alpaca_paper_post": paperops_alpaca_post.get("status", "not_run"),
            "paperops_alpaca_paper_post_called_count": paperops_alpaca_post.get(
                "alpaca_paper_post_called_count",
                0,
            ),
            "paperops_first_week_paper_trade_mandate": (
                paperops_first_week_mandate.get("status", "not_run")
            ),
            "paperops_first_week_paper_trade_mandate_active": (
                paperops_first_week_mandate.get("active", False)
            ),
            "paperops_first_week_paper_trade_mandate_day_number": (
                paperops_first_week_mandate.get("day_number", 0)
            ),
            "paperops_first_week_paper_trade_mandate_daily_target": (
                paperops_first_week_mandate.get("daily_target_trade_count", 0)
            ),
            "paperops_first_week_paper_trade_mandate_min_notional_usd": (
                paperops_first_week_mandate.get("minimum_notional_usd", 0)
            ),
            "paperops_first_week_paper_trade_mandate_daily_ready_submit_count": (
                paperops_first_week_mandate.get("daily_ready_submit_count", 0)
            ),
            "paperops_first_week_paper_trade_mandate_daily_submitted_count": (
                paperops_first_week_mandate.get("daily_submitted_count", 0)
            ),
            "paperops_first_week_paper_trade_mandate_paper_only": (
                paperops_first_week_mandate.get("paper_only", False)
            ),
            "paperops_paper_lifecycle_polling_enablement": (
                paperops_lifecycle_polling_enablement.get("status", "not_run")
            ),
            "paperops_paper_lifecycle_polling_active": (
                paperops_lifecycle_polling_enablement.get(
                    "active_lifecycle_polling_enabled",
                    False,
                )
            ),
            "paperops_paper_lifecycle_poller": paperops_lifecycle_poller.get(
                "status",
                "not_run",
            ),
            "paperops_paper_lifecycle_poller_order_poll_called_count": (
                paperops_lifecycle_poller.get("paper_order_poll_called_count", 0)
            ),
            "paperops_guarded_paper_exit_enablement": (
                paperops_guarded_exit_enablement.get("status", "not_run")
            ),
            "paperops_guarded_paper_exit_effective": (
                paperops_guarded_exit_enablement.get(
                    "alpaca_paper_exit_effective",
                    False,
                )
            ),
            "paperops_guarded_paper_exit_close_called_count": (
                paperops_guarded_exit_enablement.get(
                    "paper_position_close_called_count",
                    0,
                )
            ),
            "paperops_paper_exit_path": paperops_exit_path.get("status", "not_run"),
            "paperops_paper_exit_path_close_called_count": paperops_exit_path.get(
                "paper_position_close_called_count",
                0,
            ),
            "paperops_paper_exit_path_suppressed_stale_not_found_count": (
                paperops_exit_path.get(
                    "suppressed_stale_not_found_exit_candidate_count",
                    0,
                )
            ),
            "paperops_paper_exit_path_suppressed_pending_close_request_count": (
                paperops_exit_path.get(
                    "suppressed_pending_close_request_exit_candidate_count",
                    0,
                )
            ),
            "paperops_lifecycle_mirror_freshness": (
                paperops_lifecycle_mirror_freshness.get("status", "not_run")
            ),
            "paperops_lifecycle_mirror_fresh_after_latest_close": (
                paperops_lifecycle_mirror_freshness.get(
                    "fresh_after_latest_close",
                    True,
                )
            ),
            "paperops_close_to_ledger": paperops_close_to_ledger.get(
                "status",
                "not_run",
            ),
            "paperops_close_to_ledger_closed_proof_trade_count": (
                paperops_close_to_ledger.get("closed_proof_trade_count", 0)
            ),
            "paperops_close_to_ledger_postmortem_due_marker_created_count": (
                paperops_close_to_ledger.get("postmortem_due_marker_created_count", 0)
            ),
            "paperops_closed_trade_funnel": paperops_closed_trade_funnel.get(
                "status",
                "not_run",
            ),
            "paperops_closed_trade_funnel_blocked_stage": (
                paperops_closed_trade_funnel.get("blocked_stage")
            ),
            "paperops_closed_trade_funnel_close_receipt_count": (
                paperops_closed_trade_funnel.get("counts", {}).get(
                    "paper_close_receipt_count",
                    0,
                )
            ),
            "paperops_closed_trade_funnel_closed_proof_trade_count": (
                paperops_closed_trade_funnel.get("counts", {}).get(
                    "closed_proof_trade_count",
                    0,
                )
            ),
            "paperops_notification_review": paperops_notification_review.get(
                "status",
                "not_run",
            ),
            "paperops_notification_review_live_send_allowed_count": (
                paperops_notification_review.get("live_send_allowed_count", 0)
            ),
            "paperops_submit_regression_guard": (
                paperops_submit_regression_guard.get("status", "not_run")
            ),
            "paperops_submit_regression_guard_source_paperops2": (
                paperops_submit_regression_guard.get(
                    "source_paperops2_status",
                    "not_run",
                )
            ),
            "paperops_submit_regression_guard_fresh_submit_count": (
                paperops_submit_regression_guard.get(
                    "fresh_eligible_submit_record_count",
                    0,
                )
            ),
            "paperops_submit_regression_guard_duplicate_submit_count": (
                paperops_submit_regression_guard.get(
                    "duplicate_submit_record_count",
                    0,
                )
            ),
            "paperops_submit_regression_guard_blocker_count": (
                paperops_submit_regression_guard.get("blocker_count", 0)
            ),
            "paperops_submit_regression_guard_fresh_ledger_collision_count": (
                paperops_submit_regression_guard.get(
                    "fresh_submitted_ledger_collision_count",
                    0,
                )
            ),
            "paperops_submit_regression_guard_duplicate_misclassified_count": (
                paperops_submit_regression_guard.get(
                    "duplicate_misclassified_as_fresh_count",
                    0,
                )
            ),
            "paperops_submit_regression_guard_source_stale_after_post_count": (
                paperops_submit_regression_guard.get(
                    "source_stale_after_post_tolerance_count",
                    0,
                )
            ),
            "paperops_30_day_operations": paperops_30_day_operations.get(
                "status",
                "not_run",
            ),
            "paperops_30_day_operations_scheduler_status": (
                paperops_30_day_operations.get("scheduler_status", "not_run")
            ),
            "paperops_30_day_operations_active_day_number": (
                paperops_30_day_operations.get("active_day_number")
            ),
            "paperops_opportunity_scan_cadence": (
                paperops_opportunity_scan.get("status", "not_run")
            ),
            "paperops_opportunity_scan_interval_minutes": (
                paperops_opportunity_scan.get("opportunity_scan_interval_minutes", 20)
            ),
            "paperops_opportunity_scan_ready": (
                paperops_opportunity_scan.get("twenty_minute_scan_ready", False)
            ),
            "paperops_opportunity_scan_recurring_active": (
                paperops_opportunity_scan.get(
                    "twenty_minute_recurring_scheduler_active",
                    False,
                )
            ),
            "paperops_opportunity_scan_scheduler_status": (
                paperops_opportunity_scan.get(
                    "recurring_scheduler_status",
                    "not_run",
                )
            ),
            "paperops_opportunity_scan_submission_allowed": (
                paperops_opportunity_scan.get(
                    "trade_submission_allowed_by_scan",
                    False,
                )
            ),
            "paperops_opportunity_scan_fresh_submit_count": (
                paperops_opportunity_scan.get("fresh_eligible_submit_count", 0)
            ),
            "paperops_cockpit_notification_upgrade": (
                paperops_cockpit_notification_upgrade.get("status", "not_run")
            ),
            "paperops_cockpit_notification_ready": (
                paperops_cockpit_notification_upgrade.get("cockpit_upgrade_ready", False)
            ),
            "paperops_cockpit_notification_readout_count": (
                paperops_cockpit_notification_upgrade.get(
                    "fund_manager_readout_count",
                    0,
                )
            ),
            "paperops_cockpit_notification_qctrl_hold": (
                paperops_cockpit_notification_upgrade.get("qctrl_hold_visible", False)
            ),
            "paperops_cockpit_notification_live_send_allowed_count": (
                paperops_cockpit_notification_upgrade.get(
                    "notification_live_send_allowed_count",
                    0,
                )
            ),
            "paper_live_certification": paper_live_certification.get(
                "status",
                "not_run",
            ),
            "paper_live_control_plane_certified": paper_live_certification.get(
                "paper_live_control_plane_certified",
                False,
            ),
            "paper_live_certified": paper_live_certification.get(
                "paper_live_certified",
                False,
            ),
            "paper_live_certification_blocker_count": (
                paper_live_certification.get("certification_blocker_count", 0)
            ),
            "paper_live_operation_allowed": paper_live_certification.get(
                "paper_live_operation_allowed",
                False,
            ),
            "paper_live_unattended_execution_delegation_enabled": (
                paper_live_certification.get(
                    "paper_live_unattended_execution_delegation_enabled",
                    False,
                )
            ),
            "paper_live_unattended_execution_delegation_reason": (
                paper_live_certification.get(
                    "paper_live_unattended_execution_delegation_reason",
                    "not_armed",
                )
            ),
            "paperops_active_paper_trading_automation": (
                paperops_active_automation.get("status", "not_run")
            ),
            "paperops_active_paper_trading_automation_enabled": (
                paperops_active_automation.get(
                    "active_paper_trading_automation_enabled",
                    False,
                )
            ),
            "paperops_active_paper_trading_qctrl_hold": (
                paperops_active_automation.get("qctrl_consultation_hold_active", False)
            ),
            "paperops_active_paper_trading_submit_allowed": (
                paperops_active_automation.get("paper_submit_step_allowed", False)
            ),
            "paperops_active_paper_trading_unattended_delegation_enabled": (
                paperops_active_automation.get(
                    "unattended_paper_execution_delegation_enabled",
                    False,
                )
            ),
            "paperops_active_paper_trading_unattended_delegation_reason": (
                paperops_active_automation.get(
                    "unattended_paper_execution_delegation_reason",
                    "not_armed",
                )
            ),
            "paperops_active_paper_trading_idle_reason": (
                paperops_active_automation.get("idle_reason", "")
            ),
            "paperops_active_paper_trading_idempotency_guard_message": (
                paperops_active_automation.get("idempotency_guard_message", "")
            ),
            "paperops_active_paper_trading_fresh_submit_count": (
                paperops_active_automation.get(
                    "paperops2_fresh_eligible_submit_record_count",
                    0,
                )
            ),
            "paperops_active_paper_trading_duplicate_submit_count": (
                paperops_active_automation.get(
                    "paperops2_duplicate_submit_record_count",
                    0,
                )
            ),
            "paperops_active_paper_trading_idempotency_ledger_active": (
                paperops_active_automation.get(
                    "paperops2_idempotency_ledger_active",
                    False,
                )
            ),
            "paperops_active_paper_trading_rs5_daily_target_policy": (
                paperops_active_automation.get("rs5_daily_target_policy", "unknown")
            ),
            "paperops_active_paper_trading_rs5_max_guarded_submit_attempts_per_run": (
                paperops_active_automation.get(
                    "rs5_max_guarded_submit_attempts_per_run",
                    0,
                )
            ),
            "paperops_active_paper_trading_rs5_available_distinct_setup_count": (
                paperops_active_automation.get("rs5_available_distinct_setup_count", 0)
            ),
            "paperops_active_paper_trading_rs5_can_submit_multiple_today": (
                paperops_active_automation.get("rs5_can_submit_multiple_today", False)
            ),
            "paperops_active_paper_trading_why_not_trading_now": (
                paperops_active_automation.get("why_not_trading_now", "")
            ),
            "paperops_qualified_setup_production": (
                paperops_qualified_setup_production.get("status", "not_run")
            ),
            "paperops_qualified_setup_production_qualified_count": (
                paperops_qualified_setup_production.get("qualified_setup_count", 0)
            ),
            "paperops_qualified_setup_production_ready_to_stage": (
                paperops_qualified_setup_production.get("ready_to_stage_q7_order", False)
            ),
            "paperops_auto_approval_staged_order": (
                paperops_auto_approval_staged_order.get("status", "not_run")
            ),
            "paperops_auto_approval_staged_order_staged_count": (
                paperops_auto_approval_staged_order.get("staged_order_count", 0)
            ),
            "paperops_auto_approval_staged_order_ready_for_submit": (
                paperops_auto_approval_staged_order.get(
                    "ready_for_paperops2_submit",
                    False,
                )
            ),
            "paperops_alpaca_submit_enablement": (
                paperops_submit_enablement.get("status", "not_run")
            ),
            "paperops_alpaca_submit_enablement_effective": (
                paperops_submit_enablement.get("alpaca_paper_submit_effective", False)
            ),
            "paperops_alpaca_submit_enablement_path_available": (
                paperops_submit_enablement.get("paper_post_path_available", False)
            ),
            "risk_gate": _module_status(payload, "risk_agent"),
            "market_confirmation": yahoo_finance.get("status", "not_configured"),
            "preference_mcp": preference_mcp.get("status", "not_configured"),
            "phase5_layer_b": phase5_readiness.get("status", "not_run"),
            "phase5_kill_switch": phase5_kill_switch.get("status", "not_run"),
            "phase5_execution_adapter": phase5_execution_adapter.get("status", "not_run"),
            "phase5_paper_order_staging": phase5_paper_order_staging.get("status", "not_run"),
            "phase5_alpaca_paper_dry_run": phase5_alpaca_dry_run.get("status", "not_run"),
            "phase5_paper_submit_enablement": phase5_paper_submit_enablement.get("status", "not_run"),
            "phase5_prediction_market_adapter": phase5_prediction_market_adapter.get(
                "status",
                "not_run",
            ),
            "phase5_telegram_notifier": phase5_telegram_notifier.get("status", "not_run"),
            "phase5_position_monitor": phase5_position_monitor.get("status", "not_run"),
            "phase5_signal_review": phase5_signal_review.get("status", "not_run"),
            "phase5_paper_trade_drill": phase5_paper_trade_drill.get("status", "not_run"),
            "phase5_certification": phase5_certification.get("status", "not_run"),
            "phase5_phase6_handoff": phase5_phase6_handoff.get("status", "not_run"),
            "phase5_system_map": phase5_system_map.get("status", "not_run"),
            "phase6_learning_loop": phase6_learning_loop.get("status", "not_run"),
            "rs9_learning_loop": rs9_learning_loop.get("status", "not_run"),
            "rs9_learning_direction": rs9_learning_loop.get("learning_direction", "uncertain"),
            "rs9_learning_proposal_count": rs9_learning_loop.get("proposal_count", 0),
            "rs9_learning_blocked_proposal_count": rs9_learning_loop.get(
                "blocked_proposal_count",
                0,
            ),
            "rs9_paperops_guarded_paper_trading_not_blocked": (
                rs9_learning_loop.get("paperops_guarded_paper_trading_not_blocked") is True
            ),
            "rs10_final_paper_autonomy_certification": rs10_final_paper_autonomy.get(
                "status",
                "not_run",
            ),
            "rs10_final_paper_autonomy_certified": (
                rs10_final_paper_autonomy.get("final_paper_autonomy_certified")
                is True
            ),
            "rs10_guarded_paper_autonomy_allowed": (
                rs10_final_paper_autonomy.get("guarded_paper_autonomy_allowed")
                is True
            ),
            "rs10_autonomy_currently_actionable": (
                rs10_final_paper_autonomy.get("autonomy_currently_actionable")
                is True
            ),
            "rs10_current_blocker_count": rs10_final_paper_autonomy.get(
                "current_blocker_count",
                0,
            ),
            "rs10_certification_blocker_count": rs10_final_paper_autonomy.get(
                "certification_blocker_count",
                0,
            ),
            "rs10_paper_submit_currently_allowed": (
                rs10_final_paper_autonomy.get("paper_submit_currently_allowed")
                is True
            ),
            "rs10_multiple_paper_trades_per_day_allowed_when_gates_pass": (
                rs10_final_paper_autonomy.get(
                    "multiple_paper_trades_per_day_allowed_when_gates_pass"
                )
                is True
            ),
            "phase7_demo_proof": phase7_demo_proof.get("status", "not_run"),
            "paper_account": capital.get("mirror_status", "pending"),
            "rs6_lifecycle_portfolio_postmortem": paper_lifecycle_postmortem.get(
                "status",
                "not_run",
            ),
            "rs6_portfolio_value_source": paper_lifecycle_postmortem.get(
                "portfolio_value_source",
                capital.get("portfolio_value_source", "unknown"),
            ),
            "rs6_balance_ticker_broker_account_derived": (
                paper_lifecycle_postmortem.get(
                    "balance_ticker_broker_account_derived",
                    False,
                )
            ),
            "rs6_closed_trade_postmortem_coverage_count": (
                paper_lifecycle_postmortem.get(
                    "closed_trade_postmortem_coverage_count",
                    0,
                )
            ),
            "rs6_closed_trade_missing_postmortem_count": (
                paper_lifecycle_postmortem.get(
                    "closed_trade_missing_postmortem_count",
                    0,
                )
            ),
            "rs6_paper_proof_ledger_verified_record_count": (
                paper_lifecycle_postmortem.get(
                    "paper_proof_ledger_verified_record_count",
                    0,
                )
            ),
            "rs6_mirror_trade_counted_for_proof_count": (
                paper_lifecycle_postmortem.get(
                    "mirror_trade_counted_for_proof_count",
                    0,
                )
            ),
            "telegram": communications.get("status", "pending"),
            "operator_inbox": operator_inbox.get("status", "not_run"),
            "operator_inbox_item_count": operator_inbox.get("item_count", 0),
            "operator_inbox_open_item_count": operator_inbox.get("open_item_count", 0),
            "operator_inbox_high_or_critical_item_count": operator_inbox.get(
                "high_or_critical_item_count",
                0,
            ),
            "operator_inbox_postmortem_due_item_count": operator_inbox.get(
                "postmortem_due_item_count",
                0,
            ),
            "operator_inbox_telegram_command_authority": operator_inbox.get(
                "telegram_command_authority",
                False,
            ),
            "boundary": "APIs, models, and quantum checks can inform the chain; only gates can advance state.",
        },
        "phase3_readiness": _phase3_readiness(quantum_oracle),
        "phase4_strategy": {
            "phase": phase4_strategy.get("phase", "Q4"),
            "stage": phase4_strategy.get("stage", "Q4-11"),
            "stage_status": phase4_strategy.get("stage_status", "not_exported"),
            "audit_completion_state": phase4_strategy.get("audit_completion_state", {}),
            "strategy_document_status": phase4_strategy.get("strategy_document_status", "unknown"),
            "approval_event_status": phase4_strategy.get("approval_event_status", "missing"),
            "approval_logged": phase4_strategy.get("approval_event", {}).get("approval_logged") is True,
            "toggle_count": phase4_strategy.get("toggle_count", 0),
            "approved_shadow_strategy_toggle_count": phase4_strategy.get(
                "approved_shadow_strategy_toggle_count",
                0,
            ),
            "phase4_certification_allowed": phase4_strategy.get(
                "phase4_certification_allowed"
            )
            is True,
            "phase4_certified": phase4_strategy.get("phase4_certified") is True,
            "phase5_handoff_allowed": phase4_strategy.get("phase5_handoff_allowed")
            is True,
            "certification_status": phase4_strategy.get(
                "certification_status",
                "not_run",
            ),
            "certification_blocker_count": phase4_strategy.get(
                "certification",
                {},
            ).get("certification_blocker_count", 0),
            "trade_candidate_count": phase4_strategy.get("trade_candidate_count", 0),
            "execution_allowed_count": phase4_strategy.get("execution_allowed_count", 0),
            "paper_order_allowed_count": phase4_strategy.get("paper_order_allowed_count", 0),
            "broker_write_allowed_count": phase4_strategy.get("broker_write_allowed_count", 0),
            "live_capital_enabled_count": phase4_strategy.get("live_capital_enabled_count", 0),
            "boundary": phase4_strategy.get(
                "no_execution_boundary",
                "Phase 4 strategy visibility is review-only and cannot route execution.",
            ),
        },
        "phase5_layer_b": {
            "phase": phase5_readiness.get("phase", "Q5"),
            "layer": phase5_readiness.get("layer", "Layer B"),
            "stage": phase5_readiness.get("stage", "P5-PRE"),
            "status": phase5_readiness.get("status", "not_run"),
            "implementation_plan_allowed": phase5_readiness.get(
                "phase5_layer_b_implementation_plan_allowed"
            )
            is True,
            "implementation_allowed": phase5_readiness.get(
                "phase5_layer_b_implementation_allowed"
            )
            is True,
            "orchestration_start_allowed": phase5_readiness.get(
                "phase5_orchestration_start_allowed"
            )
            is True,
            "readiness_blocker_count": phase5_readiness.get(
                "readiness_blocker_count",
                0,
            ),
            "nonapproval_blocker_count": phase5_readiness.get(
                "nonapproval_blocker_count",
                0,
            ),
            "only_explicit_approval_blocks_plan": phase5_readiness.get(
                "only_explicit_approval_blocks_phase5_plan"
            )
            is True,
            "scope_count": phase5_readiness.get("phase5_layer_b_scope_count", 0),
            "kill_switch_status": phase5_kill_switch.get("status", "not_run"),
            "kill_switch_count": phase5_kill_switch.get("switch_count", 0),
            "kill_switch_active_count": phase5_kill_switch.get("active_switch_count", 0),
            "kill_switch_blocking_count": phase5_kill_switch.get("blocking_switch_count", 0),
            "kill_switch_event_log_written": phase5_kill_switch.get("event_log_written") is True,
            "execution_adapter_status": phase5_execution_adapter.get("status", "not_run"),
            "execution_adapter_count": phase5_execution_adapter.get("adapter_status_count", 0),
            "execution_adapter_read_allowed_count": phase5_execution_adapter.get("read_allowed_count", 0),
            "execution_adapter_staging_allowed_count": phase5_execution_adapter.get(
                "downstream_staging_allowed_count",
                0,
            ),
            "paper_order_staging_status": phase5_paper_order_staging.get("status", "not_run"),
            "paper_order_staging_record_count": phase5_paper_order_staging.get(
                "staging_record_count",
                0,
            ),
            "paper_order_staged_count": phase5_paper_order_staging.get("staged_order_count", 0),
            "paper_order_staging_blocked_count": phase5_paper_order_staging.get("blocked_count", 0),
            "paper_order_staging_event_log_written": (
                phase5_paper_order_staging.get("event_log_written") is True
            ),
            "alpaca_paper_dry_run_status": phase5_alpaca_dry_run.get("status", "not_run"),
            "alpaca_paper_dry_run_record_count": phase5_alpaca_dry_run.get(
                "dry_run_record_count",
                0,
            ),
            "alpaca_paper_dry_run_request_preview_count": phase5_alpaca_dry_run.get(
                "request_preview_count",
                0,
            ),
            "alpaca_paper_dry_run_receipt_count": phase5_alpaca_dry_run.get(
                "dry_run_receipt_count",
                0,
            ),
            "alpaca_paper_dry_run_blocked_count": phase5_alpaca_dry_run.get(
                "blocked_count",
                0,
            ),
            "alpaca_paper_dry_run_event_log_written": (
                phase5_alpaca_dry_run.get("event_log_written") is True
            ),
            "alpaca_paper_dry_run_broker_post_called": (
                phase5_alpaca_dry_run.get("broker_post_called") is True
            ),
            "paper_submit_enablement_status": phase5_paper_submit_enablement.get("status", "not_run"),
            "paper_submit_enablement_record_count": phase5_paper_submit_enablement.get(
                "submit_enablement_record_count",
                0,
            ),
            "paper_submit_path_available_count": phase5_paper_submit_enablement.get(
                "submit_path_available_count",
                0,
            ),
            "paper_submit_approval_state": phase5_paper_submit_enablement.get(
                "paper_submit_approval_state",
                "missing",
            ),
            "paper_submit_approval_present": (
                phase5_paper_submit_enablement.get("paper_submit_approval_present") is True
            ),
            "paper_submit_event_log_written": (
                phase5_paper_submit_enablement.get("event_log_written") is True
            ),
            "paper_submit_broker_post_called": (
                phase5_paper_submit_enablement.get("broker_post_called") is True
            ),
            "prediction_market_adapter_status": phase5_prediction_market_adapter.get(
                "status",
                "not_run",
            ),
            "prediction_market_route_count": phase5_prediction_market_adapter.get(
                "prediction_market_route_count",
                0,
            ),
            "prediction_market_context_count": phase5_prediction_market_adapter.get(
                "prediction_market_context_count",
                0,
            ),
            "prediction_market_read_only_route_count": phase5_prediction_market_adapter.get(
                "read_only_route_count",
                0,
            ),
            "prediction_market_live_blocked_route_count": phase5_prediction_market_adapter.get(
                "live_blocked_count",
                0,
            ),
            "prediction_market_write_allowed_count": phase5_prediction_market_adapter.get(
                "prediction_market_write_allowed_count",
                0,
            ),
            "prediction_market_spend_allowed_count": phase5_prediction_market_adapter.get(
                "prediction_market_spend_allowed_count",
                0,
            ),
            "prediction_market_preference_provenance_status": (
                phase5_prediction_market_adapter.get("preference_provenance_status", "not_run")
            ),
            "prediction_market_preference_source_quorum_credit_allowed": (
                phase5_prediction_market_adapter.get("preference_source_quorum_credit_allowed")
                is True
            ),
            "prediction_market_event_log_written": (
                phase5_prediction_market_adapter.get("event_log_written") is True
            ),
            "telegram_notifier_status": phase5_telegram_notifier.get("status", "not_run"),
            "telegram_notifier_alert_type_count": phase5_telegram_notifier.get(
                "alert_type_count",
                0,
            ),
            "telegram_notifier_eligible_alert_count": phase5_telegram_notifier.get(
                "eligible_alert_count",
                0,
            ),
            "telegram_notifier_queued_count": phase5_telegram_notifier.get(
                "queued_dry_run_alert_count",
                0,
            ),
            "telegram_notifier_outbox_written_count": phase5_telegram_notifier.get(
                "outbox_message_written_count",
                0,
            ),
            "telegram_notifier_suppressed_count": phase5_telegram_notifier.get(
                "suppressed_alert_count",
                0,
            ),
            "telegram_notifier_send_gate": phase5_telegram_notifier.get(
                "telegram_send_gate",
                "not_run",
            ),
            "telegram_notifier_mode": phase5_telegram_notifier.get("telegram_mode", "not_run"),
            "telegram_notifier_command_path_enabled_count": phase5_telegram_notifier.get(
                "telegram_command_path_enabled_count",
                0,
            ),
            "telegram_notifier_live_send_allowed_count": phase5_telegram_notifier.get(
                "live_send_allowed_count",
                0,
            ),
            "telegram_notifier_event_log_written": (
                phase5_telegram_notifier.get("event_log_written") is True
            ),
            "position_monitor_status": phase5_position_monitor.get("status", "not_run"),
            "position_monitor_record_count": phase5_position_monitor.get(
                "monitor_record_count",
                0,
            ),
            "position_monitor_position_record_count": phase5_position_monitor.get(
                "position_record_count",
                0,
            ),
            "position_monitor_closed_trade_summary_count": phase5_position_monitor.get(
                "closed_trade_summary_count",
                0,
            ),
            "position_monitor_submitted_order_count": phase5_position_monitor.get(
                "submitted_order_count",
                0,
            ),
            "position_monitor_mirrored_order_count": phase5_position_monitor.get(
                "mirrored_order_count",
                0,
            ),
            "position_monitor_open_position_count": phase5_position_monitor.get(
                "open_position_count",
                0,
            ),
            "position_monitor_closed_trade_count": phase5_position_monitor.get(
                "closed_trade_count",
                0,
            ),
            "position_monitor_failed_reconciliation_count": phase5_position_monitor.get(
                "failed_reconciliation_count",
                0,
            ),
            "position_monitor_event_log_written": (
                phase5_position_monitor.get("event_log_written") is True
            ),
            "position_monitor_write_authority_count": phase5_position_monitor.get(
                "position_monitor_write_authority_count",
                0,
            ),
            "position_monitor_close_allowed_count": phase5_position_monitor.get(
                "position_close_allowed_count",
                0,
            ),
            "position_monitor_resize_allowed_count": phase5_position_monitor.get(
                "position_resize_allowed_count",
                0,
            ),
            "position_monitor_cancel_allowed_count": phase5_position_monitor.get(
                "order_cancel_allowed_count",
                0,
            ),
            "signal_review_status": phase5_signal_review.get("status", "not_run"),
            "signal_review_record_count": phase5_signal_review.get(
                "signal_review_record_count",
                0,
            ),
            "signal_review_decision_chain_count": phase5_signal_review.get(
                "decision_chain_count",
                0,
            ),
            "signal_review_governance_comment_event_count": phase5_signal_review.get(
                "governance_comment_event_count",
                0,
            ),
            "signal_review_kill_switch_action_event_count": phase5_signal_review.get(
                "kill_switch_action_event_count",
                0,
            ),
            "signal_review_backend_truth_displayed_count": phase5_signal_review.get(
                "backend_truth_displayed_count",
                0,
            ),
            "signal_review_ui_inferred_readiness_count": phase5_signal_review.get(
                "ui_inferred_readiness_count",
                0,
            ),
            "signal_review_event_log_written": (
                phase5_signal_review.get("event_log_written") is True
            ),
            "signal_review_trade_approval_control_count": phase5_signal_review.get(
                "trade_approval_control_enabled_count",
                0,
            ),
            "signal_review_order_place_control_count": phase5_signal_review.get(
                "order_place_control_enabled_count",
                0,
            ),
            "signal_review_position_close_control_count": phase5_signal_review.get(
                "position_close_control_enabled_count",
                0,
            ),
            "signal_review_position_resize_control_count": phase5_signal_review.get(
                "position_resize_control_enabled_count",
                0,
            ),
            "signal_review_order_cancel_control_count": phase5_signal_review.get(
                "order_cancel_control_enabled_count",
                0,
            ),
            "signal_review_broker_write_allowed_count": phase5_signal_review.get(
                "broker_write_allowed_count",
                0,
            ),
            "signal_review_prediction_market_write_allowed_count": phase5_signal_review.get(
                "prediction_market_write_allowed_count",
                0,
            ),
            "signal_review_live_capital_enabled_count": phase5_signal_review.get(
                "live_capital_enabled_count",
                0,
            ),
            "paper_trade_drill_status": phase5_paper_trade_drill.get("status", "not_run"),
            "paper_trade_drill_state": phase5_paper_trade_drill.get(
                "paper_trade_drill_state",
                "not_run",
            ),
            "paper_trade_drill_step_count": phase5_paper_trade_drill.get("step_count", 0),
            "paper_trade_drill_blocker_count": phase5_paper_trade_drill.get("blocker_count", 0),
            "paper_trade_drill_complete": (
                phase5_paper_trade_drill.get("paper_trade_drill_complete") is True
            ),
            "paper_trade_drill_exit_gate_passed": (
                phase5_paper_trade_drill.get("phase5_paper_trade_drill_exit_gate_passed")
                is True
            ),
            "paper_trade_drill_implementation_ready": (
                phase5_paper_trade_drill.get("phase5_paper_trade_drill_implementation_ready")
                is True
            ),
            "paper_trade_drill_submit_approval_present": (
                phase5_paper_trade_drill.get("paper_submit_approval_present") is True
            ),
            "paper_trade_drill_submit_path_available_count": phase5_paper_trade_drill.get(
                "paper_submit_path_available_count",
                0,
            ),
            "paper_trade_drill_submitted_order_count": phase5_paper_trade_drill.get(
                "submitted_paper_order_count",
                0,
            ),
            "paper_trade_drill_open_position_count": phase5_paper_trade_drill.get(
                "open_position_count",
                0,
            ),
            "paper_trade_drill_closed_trade_count": phase5_paper_trade_drill.get(
                "closed_trade_count",
                0,
            ),
            "paper_trade_drill_postmortem_due_count": phase5_paper_trade_drill.get(
                "postmortem_due_count",
                0,
            ),
            "paper_trade_drill_broker_post_called_count": phase5_paper_trade_drill.get(
                "broker_post_called_count",
                0,
            ),
            "paper_trade_drill_live_capital_enabled_count": phase5_paper_trade_drill.get(
                "live_capital_enabled_count",
                0,
            ),
            "certification_status": phase5_certification.get("status", "not_run"),
            "certification_stage_status": phase5_certification.get(
                "stage_status",
                "not_run",
            ),
            "certification_phase5_certified": (
                phase5_certification.get("phase5_certified") is True
            ),
            "certification_phase5_exit_gate": (
                phase5_certification.get("phase5_exit_gate") is True
            ),
            "certification_phase6_handoff_allowed": (
                phase5_certification.get("phase6_handoff_allowed") is True
            ),
            "certification_phase7_planning_allowed": (
                phase5_certification.get("phase7_planning_allowed") is True
            ),
            "certification_phase7_proof_credit_allowed": (
                phase5_certification.get("phase7_proof_credit_allowed") is True
            ),
            "certification_input_gate_count": phase5_certification.get(
                "input_gate_count",
                0,
            ),
            "certification_input_gate_passed_count": phase5_certification.get(
                "input_gate_passed_count",
                0,
            ),
            "certification_input_gate_blocked_count": phase5_certification.get(
                "input_gate_blocked_count",
                0,
            ),
            "certification_blocker_count": phase5_certification.get(
                "certification_blocker_count",
                0,
            ),
            "certification_paper_trade_drill_complete": (
                phase5_certification.get("paper_trade_drill_complete") is True
            ),
            "certification_paper_trade_drill_exit_gate_passed": (
                phase5_certification.get("paper_trade_drill_exit_gate_passed") is True
            ),
            "certification_submitted_paper_order_count": phase5_certification.get(
                "submitted_paper_order_count",
                0,
            ),
            "certification_open_position_count": phase5_certification.get(
                "open_position_count",
                0,
            ),
            "certification_closed_trade_count": phase5_certification.get(
                "closed_trade_count",
                0,
            ),
            "certification_live_capital_enabled_count": phase5_certification.get(
                "live_capital_enabled_count",
                0,
            ),
            "phase6_handoff_status": phase5_phase6_handoff.get("status", "not_run"),
            "phase6_handoff_state": phase5_phase6_handoff.get(
                "handoff_state",
                "not_run",
            ),
            "phase6_handoff_blocker_count": phase5_phase6_handoff.get(
                "blocker_count",
                0,
            ),
            "phase6_handoff_event_log_written": (
                phase5_phase6_handoff.get("event_log_written") is True
            ),
            "phase6_learning_loop_plan_allowed": (
                phase5_phase6_handoff.get("phase6_learning_loop_plan_allowed") is True
            ),
            "phase6_learning_loop_implementation_allowed": (
                phase5_phase6_handoff.get(
                    "phase6_learning_loop_implementation_allowed"
                )
                is True
            ),
            "phase6_learning_write_allowed": (
                phase5_phase6_handoff.get("phase6_learning_write_allowed") is True
            ),
            "phase6_knowledge_graph_write_allowed": (
                phase5_phase6_handoff.get("phase6_knowledge_graph_write_allowed")
                is True
            ),
            "phase6_required_module_count": phase5_phase6_handoff.get(
                "phase6_required_module_count",
                0,
            ),
            "phase6_handoff_closed_trade_count": phase5_phase6_handoff.get(
                "closed_trade_count",
                0,
            ),
            "phase6_handoff_postmortem_due_count": phase5_phase6_handoff.get(
                "postmortem_due_count",
                0,
            ),
            "phase6_handoff_phase7_proof_credit_allowed": (
                phase5_phase6_handoff.get("phase7_proof_credit_allowed") is True
            ),
            "phase6_handoff_live_capital_enabled_count": phase5_phase6_handoff.get(
                "live_capital_enabled_count",
                0,
            ),
            "phase6_handoff_recommended_next_stage": phase5_phase6_handoff.get(
                "recommended_next_stage",
                "Q6-0 Phase 6 re-entry and learning-loop implementation plan",
            ),
            "system_map_status": phase5_system_map.get("status", "not_run"),
            "system_map_node_count": phase5_system_map.get("node_count", 0),
            "system_map_lane_count": phase5_system_map.get("lane_count", 0),
            "system_map_layer_b_node_count": phase5_system_map.get("layer_b_node_count", 0),
            "system_map_backend_parity_error_count": phase5_system_map.get(
                "backend_parity_error_count",
                0,
            ),
            "system_map_unsafe_control_count": phase5_system_map.get(
                "unsafe_control_count",
                0,
            ),
            "system_map_event_log_written": (
                phase5_system_map.get("event_log_written") is True
            ),
            "system_map_dashboard_claims_trading_now": (
                phase5_system_map.get("guardrails", {}).get("dashboard_claims_trading_now")
                is True
            ),
            "boundary": phase5_readiness.get(
                "boundary",
                "Phase 5 readiness is planning-only until Q4-12 certifies.",
            ),
        },
        "phase6_learning_loop": {
            "phase": phase6_learning_loop.get("phase", "Q6"),
            "stage": phase6_learning_loop.get("stage", "Q6-16"),
            "status": phase6_learning_loop.get("status", "not_run"),
            "visibility_state": phase6_learning_loop.get("visibility_state", "not_visible"),
            "learning_state": phase6_learning_loop.get("learning_state", "not_run"),
            "backend_derived": phase6_learning_loop.get("backend_derived") is True,
            "display_derived_from_backend": (
                phase6_learning_loop.get("display_derived_from_backend") is True
            ),
            "ui_inferred_readiness_count": phase6_learning_loop.get(
                "ui_inferred_readiness_count",
                0,
            ),
            "backend_parity_error_count": phase6_learning_loop.get(
                "backend_parity_error_count",
                0,
            ),
            "postmortem_due_count": phase6_learning_loop.get("postmortem_due_count", 0),
            "postmortem_resolved_count": phase6_learning_loop.get(
                "postmortem_resolved_count",
                0,
            ),
            "approval_state": phase6_learning_loop.get("approval_state", "not_requested"),
            "staged_graph_entry_count": phase6_learning_loop.get(
                "staged_graph_entry_count",
                0,
            ),
            "knowledge_graph_read_result_count": phase6_learning_loop.get(
                "knowledge_graph_read_result_count",
                0,
            ),
            "model_weight_proposal_count": phase6_learning_loop.get(
                "model_weight_proposal_count",
                0,
            ),
            "trust_score_proposal_count": phase6_learning_loop.get(
                "trust_score_proposal_count",
                0,
            ),
            "shadow_replay_variant_count": phase6_learning_loop.get(
                "shadow_replay_variant_count",
                0,
            ),
            "architect_recommendation_count": phase6_learning_loop.get(
                "architect_recommendation_count",
                0,
            ),
            "architect_blocked_recommendation_count": phase6_learning_loop.get(
                "architect_blocked_recommendation_count",
                0,
            ),
            "blocked_authority_count": phase6_learning_loop.get(
                "blocked_authority_count",
                0,
            ),
            "phase6_learning_write_allowed": (
                phase6_learning_loop.get("phase6_learning_write_allowed") is True
            ),
            "phase6_knowledge_graph_write_allowed": (
                phase6_learning_loop.get("phase6_knowledge_graph_write_allowed") is True
            ),
            "phase6_model_weight_update_allowed": (
                phase6_learning_loop.get("phase6_model_weight_update_allowed") is True
            ),
            "phase6_trust_score_update_allowed": (
                phase6_learning_loop.get("phase6_trust_score_update_allowed") is True
            ),
            "phase6_architect_policy_mutation_allowed": (
                phase6_learning_loop.get("phase6_architect_policy_mutation_allowed") is True
            ),
            "phase7_proof_credit_allowed": (
                phase6_learning_loop.get("phase7_proof_credit_allowed") is True
            ),
            "live_capital_enabled": phase6_learning_loop.get("live_capital_enabled") is True,
            "unsafe_write_counter_total": phase6_learning_loop.get(
                "unsafe_write_counter_total",
                0,
            ),
            "raw_payload_exposed_count": phase6_learning_loop.get(
                "raw_payload_exposed_count",
                0,
            ),
            "local_path_exposed_count": phase6_learning_loop.get(
                "local_path_exposed_count",
                0,
            ),
            "secret_ref_exposed_count": phase6_learning_loop.get(
                "secret_ref_exposed_count",
                0,
            ),
            "broker_identifier_exposed_count": phase6_learning_loop.get(
                "broker_identifier_exposed_count",
                0,
            ),
            "boundary": phase6_learning_loop.get(
                "boundary",
                "Phase 6 Learning Loop visibility is backend-derived and non-executable.",
            ),
        },
        "rs9_learning_loop": {
            "phase": rs9_learning_loop.get("phase", "RS"),
            "stage": rs9_learning_loop.get("stage", "RS-9"),
            "status": rs9_learning_loop.get("status", "not_run"),
            "learning_direction": rs9_learning_loop.get("learning_direction", "uncertain"),
            "learning_direction_reason": rs9_learning_loop.get(
                "learning_direction_reason",
                "RS-9 has not exported a learning direction yet.",
            ),
            "full_potential_state": rs9_learning_loop.get(
                "full_potential_state",
                "not_run",
            ),
            "paperops_guarded_paper_trading_not_blocked": (
                rs9_learning_loop.get("paperops_guarded_paper_trading_not_blocked")
                is True
            ),
            "proposal_count": rs9_learning_loop.get("proposal_count", 0),
            "active_proposal_count": rs9_learning_loop.get("active_proposal_count", 0),
            "blocked_proposal_count": rs9_learning_loop.get("blocked_proposal_count", 0),
            "strategy_weight_proposal_count": rs9_learning_loop.get(
                "strategy_weight_proposal_count",
                0,
            ),
            "source_trust_proposal_count": rs9_learning_loop.get(
                "source_trust_proposal_count",
                0,
            ),
            "risk_sizing_proposal_count": rs9_learning_loop.get(
                "risk_sizing_proposal_count",
                0,
            ),
            "market_context_proposal_count": rs9_learning_loop.get(
                "market_context_proposal_count",
                0,
            ),
            "worldview_lens_proposal_count": rs9_learning_loop.get(
                "worldview_lens_proposal_count",
                0,
            ),
            "postmortem_due_count": rs9_learning_loop.get("postmortem_due_count", 0),
            "postmortem_resolved_count": rs9_learning_loop.get(
                "postmortem_resolved_count",
                0,
            ),
            "blocked_authority_count": rs9_learning_loop.get("blocked_authority_count", 0),
            "strategy_weight_mutation_allowed": (
                rs9_learning_loop.get("strategy_weight_mutation_allowed") is True
            ),
            "source_trust_mutation_allowed": (
                rs9_learning_loop.get("source_trust_mutation_allowed") is True
            ),
            "risk_sizing_mutation_allowed": (
                rs9_learning_loop.get("risk_sizing_mutation_allowed") is True
            ),
            "market_context_interpretation_mutation_allowed": (
                rs9_learning_loop.get("market_context_interpretation_mutation_allowed")
                is True
            ),
            "worldview_lens_strength_mutation_allowed": (
                rs9_learning_loop.get("worldview_lens_strength_mutation_allowed")
                is True
            ),
            "dashboard_command_authority": (
                rs9_learning_loop.get("dashboard_command_authority") is True
            ),
            "telegram_command_authority": (
                rs9_learning_loop.get("telegram_command_authority") is True
            ),
            "broker_write_allowed": rs9_learning_loop.get("broker_write_allowed") is True,
            "live_capital_enabled": rs9_learning_loop.get("live_capital_enabled") is True,
            "phase7_proof_credit_allowed": (
                rs9_learning_loop.get("phase7_proof_credit_allowed") is True
            ),
            "unsafe_write_counter_total": rs9_learning_loop.get(
                "unsafe_write_counter_total",
                0,
            ),
            "raw_payload_exposed_count": rs9_learning_loop.get(
                "raw_payload_exposed_count",
                0,
            ),
            "local_path_exposed_count": rs9_learning_loop.get(
                "local_path_exposed_count",
                0,
            ),
            "secret_ref_exposed_count": rs9_learning_loop.get(
                "secret_ref_exposed_count",
                0,
            ),
            "broker_identifier_exposed_count": rs9_learning_loop.get(
                "broker_identifier_exposed_count",
                0,
            ),
            "boundary": rs9_learning_loop.get(
                "boundary",
                "RS-9 is learning review only and cannot apply mutations or create orders.",
            ),
            "next_action": rs9_learning_loop.get(
                "next_action",
                "Review RS-9 learning proposals before allowing any mutation.",
            ),
        },
        "rs10_final_paper_autonomy_certification": {
            "phase": rs10_final_paper_autonomy.get("phase", "RS"),
            "stage": rs10_final_paper_autonomy.get("stage", "RS-10"),
            "status": rs10_final_paper_autonomy.get("status", "not_run"),
            "certification_state": rs10_final_paper_autonomy.get(
                "certification_state",
                "not_run",
            ),
            "final_paper_autonomy_certified": (
                rs10_final_paper_autonomy.get("final_paper_autonomy_certified")
                is True
            ),
            "guarded_paper_autonomy_allowed": (
                rs10_final_paper_autonomy.get("guarded_paper_autonomy_allowed")
                is True
            ),
            "autonomy_currently_actionable": (
                rs10_final_paper_autonomy.get("autonomy_currently_actionable")
                is True
            ),
            "multiple_paper_trades_per_day_allowed_when_gates_pass": (
                rs10_final_paper_autonomy.get(
                    "multiple_paper_trades_per_day_allowed_when_gates_pass"
                )
                is True
            ),
            "paper_submit_currently_allowed": (
                rs10_final_paper_autonomy.get("paper_submit_currently_allowed")
                is True
            ),
            "paper_poll_currently_allowed": (
                rs10_final_paper_autonomy.get("paper_poll_currently_allowed")
                is True
            ),
            "paper_exit_currently_allowed": (
                rs10_final_paper_autonomy.get("paper_exit_currently_allowed")
                is True
            ),
            "daily_target_policy": rs10_final_paper_autonomy.get(
                "daily_target_policy",
                "minimum_not_ceiling",
            ),
            "opportunity_scan_interval_minutes": rs10_final_paper_autonomy.get(
                "opportunity_scan_interval_minutes",
                20,
            ),
            "max_guarded_submit_attempts_per_run": rs10_final_paper_autonomy.get(
                "max_guarded_submit_attempts_per_run",
                3,
            ),
            "available_distinct_setup_count": rs10_final_paper_autonomy.get(
                "available_distinct_setup_count",
                0,
            ),
            "current_blocker_count": rs10_final_paper_autonomy.get(
                "current_blocker_count",
                0,
            ),
            "current_blockers": rs10_final_paper_autonomy.get(
                "current_blockers",
                [],
            ),
            "certification_blocker_count": rs10_final_paper_autonomy.get(
                "certification_blocker_count",
                0,
            ),
            "safety_blocker_count": rs10_final_paper_autonomy.get(
                "safety_blocker_count",
                0,
            ),
            "safety_blockers": rs10_final_paper_autonomy.get(
                "safety_blockers",
                [],
            ),
            "paper_live_certification_status": rs10_final_paper_autonomy.get(
                "paper_live_certification_status",
                "unknown",
            ),
            "paper_live_certification_blocker_count": rs10_final_paper_autonomy.get(
                "paper_live_certification_blocker_count",
                0,
            ),
            "why_not_trading_now": rs10_final_paper_autonomy.get(
                "why_not_trading_now",
                "No current why-not-trading reason exported.",
            ),
            "next_action": rs10_final_paper_autonomy.get(
                "next_action",
                "Continue 20-minute opportunity scans.",
            ),
            "boundary": rs10_final_paper_autonomy.get(
                "boundary",
                "RS-10 certifies guarded paper autonomy only.",
            ),
        },
        "phase7_demo_proof": {
            "phase": phase7_demo_proof.get("phase", "Q7"),
            "stage": phase7_demo_proof.get("stage", "Q7-15"),
            "status": phase7_demo_proof.get("status", "not_run"),
            "stage_status": phase7_demo_proof.get("stage_status", "not_run"),
            "visibility_state": phase7_demo_proof.get("visibility_state", "not_visible"),
            "proof_state": phase7_demo_proof.get("proof_state", "not_run"),
            "backend_derived": phase7_demo_proof.get("backend_derived") is True,
            "display_derived_from_backend": (
                phase7_demo_proof.get("display_derived_from_backend") is True
            ),
            "dashboard_uses_backend_status": (
                phase7_demo_proof.get("dashboard_uses_backend_status") is True
            ),
            "ui_inferred_readiness_count": phase7_demo_proof.get(
                "ui_inferred_readiness_count",
                0,
            ),
            "source_artifact_count": phase7_demo_proof.get("source_artifact_count", 0),
            "source_missing_count": phase7_demo_proof.get("source_missing_count", 0),
            "source_validation_error_count": phase7_demo_proof.get(
                "source_validation_error_count",
                0,
            ),
            "phase7_harness_day_count": phase7_demo_proof.get(
                "phase7_harness_day_count",
                30,
            ),
            "completed_calendar_day_count": phase7_demo_proof.get(
                "completed_calendar_day_count",
                0,
            ),
            "phase7_30_day_run_complete": (
                phase7_demo_proof.get("phase7_30_day_run_complete") is True
            ),
            "proof_week_count": phase7_demo_proof.get("proof_week_count", 0),
            "current_proof_week_number": phase7_demo_proof.get(
                "current_proof_week_number",
                0,
            ),
            "weekly_proof_trade_target": phase7_demo_proof.get(
                "weekly_proof_trade_target",
                3,
            ),
            "qualified_setup_count": phase7_demo_proof.get("qualified_setup_count", 0),
            "eligible_setup_count": phase7_demo_proof.get("eligible_setup_count", 0),
            "missed_qualified_setup_count": phase7_demo_proof.get(
                "missed_qualified_setup_count",
                0,
            ),
            "staged_proof_order_count": phase7_demo_proof.get(
                "staged_proof_order_count",
                0,
            ),
            "submitted_paper_order_count": phase7_demo_proof.get(
                "submitted_paper_order_count",
                0,
            ),
            "broker_receipt_count": phase7_demo_proof.get("broker_receipt_count", 0),
            "mirrored_submitted_order_count": phase7_demo_proof.get(
                "mirrored_submitted_order_count",
                0,
            ),
            "open_position_count": phase7_demo_proof.get("open_position_count", 0),
            "closed_proof_trade_count": phase7_demo_proof.get(
                "closed_proof_trade_count",
                0,
            ),
            "postmortem_due_count": phase7_demo_proof.get("postmortem_due_count", 0),
            "expectancy_after_costs_gbp": phase7_demo_proof.get(
                "expectancy_after_costs_gbp"
            ),
            "expectancy_after_costs_positive": (
                phase7_demo_proof.get("expectancy_after_costs_positive") is True
            ),
            "drawdown_state": phase7_demo_proof.get("drawdown_state", "unknown"),
            "drawdown_within_cap": phase7_demo_proof.get("drawdown_within_cap") is True,
            "max_drawdown_fraction_observed": phase7_demo_proof.get(
                "max_drawdown_fraction_observed"
            ),
            "new_proof_trades_frozen": (
                phase7_demo_proof.get("new_proof_trades_frozen") is True
            ),
            "override_count": phase7_demo_proof.get("override_count", 0),
            "sample_contaminated": phase7_demo_proof.get("sample_contaminated") is True,
            "complete_decision_chain_count": phase7_demo_proof.get(
                "complete_decision_chain_count",
                0,
            ),
            "missing_decision_chain_count": phase7_demo_proof.get(
                "missing_decision_chain_count",
                0,
            ),
            "maturity_state": phase7_demo_proof.get("maturity_state", "no_sample"),
            "mature_benchmark": phase7_demo_proof.get("mature_benchmark", 100),
            "maturity_progress_fraction": phase7_demo_proof.get(
                "maturity_progress_fraction",
                0,
            ),
            "closed_trades_remaining_to_mature": phase7_demo_proof.get(
                "closed_trades_remaining_to_mature",
                100,
            ),
            "phase7_mature_benchmark_met": (
                phase7_demo_proof.get("phase7_mature_benchmark_met") is True
            ),
            "phase7_mature_status_blocked": (
                phase7_demo_proof.get("phase7_mature_status_blocked") is True
            ),
            "phase7_statistical_immaturity_hidden": (
                phase7_demo_proof.get("phase7_statistical_immaturity_hidden") is True
            ),
            "phase5_test_trades_count_for_phase7": (
                phase7_demo_proof.get("phase5_test_trades_count_for_phase7") is True
            ),
            "phase7_proof_credit_allowed": (
                phase7_demo_proof.get("phase7_proof_credit_allowed") is True
            ),
            "live_capital_enabled": phase7_demo_proof.get("live_capital_enabled") is True,
            "broker_post_called_count": phase7_demo_proof.get(
                "broker_post_called_count",
                0,
            ),
            "alpaca_post_called_count": phase7_demo_proof.get(
                "alpaca_post_called_count",
                0,
            ),
            "unsafe_write_counter_total": phase7_demo_proof.get(
                "unsafe_write_counter_total",
                0,
            ),
            "q7_16_weekly_review_pack_stage_allowed": (
                phase7_demo_proof.get("q7_16_weekly_review_pack_stage_allowed") is True
            ),
            "boundary": phase7_demo_proof.get(
                "boundary",
                "Phase 7 demo-proof visibility is backend-derived and non-executable.",
            ),
        },
        "thinking": {
            "status": cognition.get("status", "pending"),
            "phase2_status": phase2_cycle.get("status", "not_run"),
            "phase2_mode": phase2_cycle.get("mode", "not_run"),
            "phase2_queued_packet_count": phase2_cycle.get("queued_packet_count", 0),
            "phase2_shadow_signal_count": phase2_cycle.get("shadow_signal_count", 0),
            "phase2_durable_replay_status": phase2_cycle.get("durable_replay_status", "not_requested"),
            "phase2_durable_replayed_source_count": phase2_cycle.get("durable_replay_replayed_source_count", 0),
            "phase2_durable_missing_source_count": phase2_cycle.get("durable_replay_missing_source_count", 0),
            "strategy_lead_source_posture": phase2_cycle.get("strategy_lead_source_posture", "not_run"),
            "strategy_lead_review_mode": phase2_cycle.get("strategy_lead_review_mode", "not_run"),
            "strategy_lead_evidence_pressure": phase2_cycle.get("strategy_lead_evidence_pressure", "not_run"),
            "strategy_lead_required_challenge_count": phase2_cycle.get("strategy_lead_required_challenge_count", 0),
            "current_focus": cognition.get("current_focus", [])[:5],
            "research_goal_status": research_goal_status.get("status", "not_run"),
            "research_goal_active_count": int(
                research_goal_status.get("active_goal_count", len(research_goal_records)) or 0
            ),
            "research_goal_record_count": int(
                research_goal_status.get("goal_record_count", len(research_goal_records)) or 0
            ),
            "hypothesis_count": len(hypotheses),
            "evidence_packet_count": len(evidence_packets),
            "local_assessment_count": len(local_assessments),
            "strategy_packet_count": len(strategy_packets),
            "signal_integrity_status": cognition.get("signal_integrity", {}).get("status", "pending"),
            "blocked_reasons": cognition.get("blocked_reasons", [])[:8],
            "hypotheses": _mission_hypotheses(hypotheses),
            "research_goals": [
                {
                    "goal_id": goal.get("goal_id"),
                    "status": goal.get("status"),
                    "hypothesis": goal.get("hypothesis"),
                    "market_channel": goal.get("market_channel"),
                    "priority_label": goal.get("priority_label"),
                    "missing_corroboration": goal.get("missing_corroboration", []),
                    "worldview_lens": goal.get("worldview_lens"),
                    "akber_stage": goal.get("akber_stage"),
                }
                for goal in research_goal_records[:6]
            ],
            "missing_corroboration": list(
                dict.fromkeys(
                    str(item)
                    for hypothesis in hypotheses[:6]
                    for item in hypothesis.get("missing_correlations", [])
                    if item
                )
            )[:8],
            "worldview_prior": {
                "status": decision_philosophy.get("status", "pending"),
                "role": decision_philosophy.get("role", "private_worldview_prior"),
                "corpus": decision_philosophy.get("corpus", "how-the-world-works"),
                "claim_count": decision_philosophy.get("claim_count", 0),
                "summary": decision_philosophy.get("trading_philosophy"),
                "boundary": decision_philosophy.get(
                    "boundary",
                    "World-model claims are private priors, not factual evidence or trade triggers.",
                ),
            },
            "boundary": cognition.get("boundary", "Cognition is shadow-only and cannot execute trades."),
        },
        "trade_intent": {
            "state": next_trade_state,
            "summary": next_trade_summary,
            "observed_signal_count": len(observed_signals),
            "candidate_count": len(candidates),
            "blocked_count": len(blocked_trades),
            "risk_review_count": risk_agent.get("review_count", 0),
            "execution_policy_review_count": execution_policy.get("review_count", 0),
            "paper_submit_receipt_review_count": paper_submit_receipt.get("review_count", 0),
            "top_candidates": [
                {
                    "instrument": item.get("instrument"),
                    "direction": item.get("direction"),
                    "status": item.get("status"),
                    "venue": item.get("venue"),
                    "catalyst": item.get("catalyst"),
                }
                for item in candidates[:5]
            ],
            "blocked_trades": [
                {
                    "instrument": item.get("instrument"),
                    "status": item.get("status"),
                    "blocked_reason": item.get("blocked_reason"),
                }
                for item in blocked_trades[:5]
            ],
            "execution_allowed_count": 0,
            "paper_order_submitted_count": paper_submit_receipt.get("paper_order_submitted_count", 0),
            "broker_post_called_count": paper_submit_receipt.get("broker_post_called_count", 0),
            "boundary": trade_layer.get("boundary", "Candidate is not order; no broker route exists."),
        },
        "trades": {
            "lifecycle_counts": {
                "observed": len(observed_signals),
                "candidate": len(candidates),
                "blocked": len(blocked_trades),
                "paper_order_submitted": paper_order_submitted_count,
                "open": len(open_positions),
                "closed": len(closed_trades),
                "postmortem_due": postmortem_due_count,
            },
            "board": _mission_trade_board(
                observed_signals,
                candidates,
                blocked_trades,
                open_positions,
                closed_trades,
            ),
            "open": open_positions[:8],
            "postmortems_due": capital.get("postmortems_due", [])[:8],
            "boundary": trade_layer.get("boundary", "Candidate is not order; no broker route exists."),
        },
        "portfolio": {
            "account_scope": capital.get("account_scope", PAPER_ACCOUNT_SCOPE),
            "broker": capital.get("broker", "paper_broker"),
            "connection_status": capital.get("connection_status", "pending"),
            "balance_gbp": current_balance,
            "delta_pct": (
                round(((current_balance - float(capital.get("starting_balance_gbp") or current_balance)) / float(capital.get("starting_balance_gbp") or current_balance)) * 100, 4)
                if float(capital.get("starting_balance_gbp") or current_balance)
                else 0
            ),
            "equity_curve": capital.get("equity_curve", []),
            "current_balance_gbp": current_balance,
            "realized_pnl_gbp": capital.get("realized_pnl_gbp", 0),
            "unrealized_pnl_gbp": capital.get("unrealized_pnl_gbp", 0),
            "total_pnl_gbp": pnl_total,
            "drawdown_pct": capital.get("drawdown_pct", 0),
            "mirror_freshness": capital.get("mirror_freshness_status", "unknown"),
            "portfolio_value_source": paper_lifecycle_postmortem.get(
                "portfolio_value_source",
                capital.get("portfolio_value_source", "unknown"),
            ),
            "balance_ticker_broker_account_derived": (
                paper_lifecycle_postmortem.get(
                    "balance_ticker_broker_account_derived",
                    False,
                )
            ),
            "open_position_count": len(open_positions),
            "order_count": len(orders),
            "closed_trade_count": len(closed_trades),
            "postmortem_due_count": paper_lifecycle_postmortem.get(
                "postmortem_due_count",
                capital.get("postmortem_due_count", 0),
            ),
            "closed_trade_postmortem_coverage_count": (
                paper_lifecycle_postmortem.get(
                    "closed_trade_postmortem_coverage_count",
                    0,
                )
            ),
            "closed_trade_missing_postmortem_count": (
                paper_lifecycle_postmortem.get(
                    "closed_trade_missing_postmortem_count",
                    0,
                )
            ),
            "paper_proof_ledger_verified_record_count": (
                paper_lifecycle_postmortem.get(
                    "paper_proof_ledger_verified_record_count",
                    0,
                )
            ),
            "mirror_trade_counted_for_proof_count": (
                paper_lifecycle_postmortem.get(
                    "mirror_trade_counted_for_proof_count",
                    0,
                )
            ),
            "maturity_closed_trade_target": capital.get("maturity_closed_trade_target", 100),
            "live_capital_enabled": live_capital_enabled,
            "write_authority": bool(capital.get("write_authority")),
            "open_positions": open_positions[:5],
            "orders": orders[:5],
            "boundary": capital.get("boundary", "Read-only paper account mirror."),
        },
        "safety": {
            "mode": payload.get("mode", "paper"),
            "read_only": True,
            "broker_write_route": "closed" if not broker_write_allowed else "enabled",
            "live_capital_enabled": live_capital_enabled,
            "broker_write_allowed": broker_write_allowed,
            "forbidden_action_count": len(forbidden_actions),
            "hard_blocks": [
                action.get("action") or action.get("key") or "blocked_action"
                for action in forbidden_actions[:8]
            ],
            "boundary": "This is read-only mission control: it cannot approve trades, broker writes, position changes, funding, or live capital changes.",
        },
        "mission_brief": mission_brief,
    }


def _risk_agent_status(settings: Settings) -> dict[str, Any]:
    summary = risk_agent_summary(settings)
    reviews = _safe_risk_policy_reviews(settings)
    return {
        "status": summary.get("status", "ok"),
        "schema_version": summary.get("schema_version"),
        "review_count": summary.get("review_count", 0),
        "by_status": summary.get("by_status", {}),
        "execution_allowed_count": summary.get("execution_allowed_count", 0),
        "paper_order_allowed_count": summary.get("paper_order_allowed_count", 0),
        "order_created_count": summary.get("order_created_count", 0),
        "broker_write_allowed_count": summary.get("broker_write_allowed_count", 0),
        "max_risk_pct_per_idea": 1.0,
        "authority": "read_only_policy_router",
        "reviews": reviews,
        "boundary": summary.get(
            "boundary",
            "Risk Agent policy reviews are read-only and cannot approve risk or create orders.",
        ),
    }


def _execution_policy_status(settings: Settings) -> dict[str, Any]:
    summary = execution_policy_summary(settings)
    reviews = _safe_execution_policy_reviews(settings)
    return {
        "status": summary.get("status", "ok"),
        "schema_version": summary.get("schema_version"),
        "review_count": summary.get("review_count", 0),
        "by_status": summary.get("by_status", {}),
        "execution_allowed_count": summary.get("execution_allowed_count", 0),
        "staged_paper_order_allowed_count": summary.get("staged_paper_order_allowed_count", 0),
        "paper_order_created_count": summary.get("paper_order_created_count", 0),
        "broker_write_allowed_count": summary.get("broker_write_allowed_count", 0),
        "live_capital_enabled_count": summary.get("live_capital_enabled_count", 0),
        "kill_switch_block_count": summary.get("kill_switch_block_count", 0),
        "authority": "read_only_execution_policy",
        "reviews": reviews,
        "boundary": summary.get(
            "boundary",
            "Execution policy reviews are read-only and cannot stage paper orders or write to brokers.",
        ),
    }


def _staged_paper_order_status(settings: Settings) -> dict[str, Any]:
    summary = staged_paper_order_summary(settings)
    reviews = _safe_staged_paper_order_reviews(settings)
    return {
        "status": summary.get("status", "ok"),
        "schema_version": summary.get("schema_version"),
        "review_count": summary.get("review_count", 0),
        "by_status": summary.get("by_status", {}),
        "execution_allowed_count": summary.get("execution_allowed_count", 0),
        "staged_paper_order_created_count": summary.get("staged_paper_order_created_count", 0),
        "paper_order_submittable_count": summary.get("paper_order_submittable_count", 0),
        "broker_write_allowed_count": summary.get("broker_write_allowed_count", 0),
        "live_capital_enabled_count": summary.get("live_capital_enabled_count", 0),
        "reconciliation_ready_count": summary.get("reconciliation_ready_count", 0),
        "authority": "disabled_staged_order_contract",
        "reviews": reviews,
        "boundary": summary.get(
            "boundary",
            "Staged paper-order reviews are disabled and read-only; they cannot create staged orders.",
        ),
    }


def _broker_reconciliation_status(settings: Settings) -> dict[str, Any]:
    summary = broker_reconciliation_summary(settings)
    reviews = _safe_broker_reconciliation_reviews(settings)
    return {
        "status": summary.get("status", "ok"),
        "schema_version": summary.get("schema_version"),
        "review_count": summary.get("review_count", 0),
        "by_status": summary.get("by_status", {}),
        "idempotency_key_allocated_count": summary.get("idempotency_key_allocated_count", 0),
        "event_log_prewrite_created_count": summary.get("event_log_prewrite_created_count", 0),
        "pre_trade_snapshot_created_count": summary.get("pre_trade_snapshot_created_count", 0),
        "duplicate_order_guard_ready_count": summary.get("duplicate_order_guard_ready_count", 0),
        "broker_echo_verified_count": summary.get("broker_echo_verified_count", 0),
        "post_submit_reconciliation_ready_count": summary.get("post_submit_reconciliation_ready_count", 0),
        "postmortem_link_ready_count": summary.get("postmortem_link_ready_count", 0),
        "paper_order_submit_allowed_count": summary.get("paper_order_submit_allowed_count", 0),
        "broker_write_allowed_count": summary.get("broker_write_allowed_count", 0),
        "live_capital_enabled_count": summary.get("live_capital_enabled_count", 0),
        "authority": "read_only_broker_reconciliation",
        "reviews": reviews,
        "boundary": summary.get(
            "boundary",
            "Broker reconciliation reviews are read-only and cannot submit paper orders or write to brokers.",
        ),
    }


def _paper_submit_receipt_status(settings: Settings) -> dict[str, Any]:
    summary = paper_submit_receipt_summary(settings)
    reviews = _safe_paper_submit_receipt_reviews(settings)
    return {
        "status": summary.get("status", "ok"),
        "schema_version": summary.get("schema_version"),
        "review_count": summary.get("review_count", 0),
        "by_status": summary.get("by_status", {}),
        "dry_run_receipt_created_count": summary.get("dry_run_receipt_created_count", 0),
        "paper_order_submitted_count": summary.get("paper_order_submitted_count", 0),
        "broker_post_called_count": summary.get("broker_post_called_count", 0),
        "broker_write_allowed_count": summary.get("broker_write_allowed_count", 0),
        "live_capital_enabled_count": summary.get("live_capital_enabled_count", 0),
        "authority": "dry_run_receipt_only",
        "reviews": reviews,
        "boundary": summary.get(
            "boundary",
            "Paper-submit receipt reviews are dry-run only and cannot call brokers or submit paper orders.",
        ),
    }


def _forbidden_actions() -> list[dict[str, str]]:
    return [
        {
            "key": "live_capital",
            "status": "blocked",
            "reason": "first_release_paper_mode_only",
        },
        {
            "key": "browser_to_broker",
            "status": "blocked",
            "reason": "no_direct_ui_to_broker_path",
        },
        {
            "key": "llm_to_broker",
            "status": "blocked",
            "reason": "no_llm_to_broker_path",
        },
        {
            "key": "broker_write",
            "status": "blocked",
            "reason": "execution_venues_disabled_until_phase_5_gates",
        },
        {
            "key": "staged_paper_order_creation",
            "status": "blocked",
            "reason": "staged_order_contract_is_disabled_read_only",
        },
        {
            "key": "paper_order_submission",
            "status": "blocked",
            "reason": "broker_reconciliation_contract_is_read_only",
        },
        {
            "key": "broker_post_call",
            "status": "blocked",
            "reason": "paper_submit_receipt_is_dry_run_only",
        },
        {
            "key": "tradingview_alert_execution",
            "status": "blocked",
            "reason": "future_alerts_can_only_write_observed_signal_events",
        },
        {
            "key": "quantum_realtime_trading",
            "status": "blocked",
            "reason": "quantum_is_weekly_oracle_not_execution_engine",
        },
    ]


def build_cockpit_status(settings: Settings | None = None) -> dict[str, Any]:
    settings = settings or Settings.from_env()
    generated_at = _now()
    data_map = build_data_environment_map(settings)
    data_summary = data_map.get("summary", {})
    phase1_data_spine = {
        "status": (
            "ok"
            if data_summary.get("status") == "ok"
            and int(data_summary.get("source_count", 0) or 0) == EXPECTED_SOURCE_COUNT
            and int(data_summary.get("promoted_adapter_count", 0) or 0)
            == len(PROMOTED_ADAPTER_STATUS)
            else str(data_summary.get("status") or "missing")
        ),
        "operational_status": (
            "operational_with_optional_missing_credentials"
            if data_summary.get("status") == "ok"
            and int(data_summary.get("source_count", 0) or 0) == EXPECTED_SOURCE_COUNT
            and int(data_summary.get("promoted_adapter_count", 0) or 0)
            == len(PROMOTED_ADAPTER_STATUS)
            else "not_ready"
        ),
        "canonical_source_count": int(data_summary.get("source_count", 0) or 0),
        "expected_canonical_source_count": EXPECTED_SOURCE_COUNT,
        "promoted_adapter_count": int(
            data_summary.get("promoted_adapter_count", 0) or 0
        ),
        "expected_promoted_adapter_count": len(PROMOTED_ADAPTER_STATUS),
        "optional_missing_credential_source_count": int(
            data_summary.get("missing_credential_source_count", 0) or 0
        ),
        "provider_decision_source_count": int(
            data_summary.get("provider_decision_source_count", 0) or 0
        ),
        "provider_selected_pending_adapter_count": int(
            data_summary.get("provider_selected_pending_adapter_count", 0) or 0
        ),
        "provider_decision_marketplace_disabled_count": int(
            data_summary.get("provider_decision_marketplace_disabled_count", 0) or 0
        ),
        "provider_decision_local_bridge_count": int(
            data_summary.get("provider_decision_local_bridge_count", 0) or 0
        ),
        "provider_decision_credential_required_now_count": int(
            data_summary.get("provider_decision_credential_required_now_count", 0) or 0
        ),
        "public_safe": True,
        "boundary": (
            "Phase 1 data spine readiness is source coverage only. Missing "
            "coverage credentials are optional unless a strategy explicitly "
            "requires that source."
        ),
    }
    health = build_system_health(settings, event_log_health=EventLog(echo=False).health())
    quantum_oracle = dict(health["quantum_oracle"])
    quantum_oracle["provider_readiness"] = quantum_provider_readiness(settings)
    fire_opal_ibm_readiness = qctrl_fire_opal_ibm_readiness(settings)
    validate_qctrl_fire_opal_ibm_readiness(fire_opal_ibm_readiness)
    quantum_oracle["fire_opal_ibm_readiness"] = fire_opal_ibm_readiness
    watching = _build_watching(data_map, settings)
    payload = {
        "schema_version": COCKPIT_STATUS_SCHEMA_VERSION,
        "generated_at": generated_at,
        "mode": settings.mode,
        "d1_snapshot": _d1_snapshot_contract(generated_at),
        "d0_shell": {
            "status": "frozen",
            "surface": "qadam.trade static Supabase-authenticated shell",
            "routing": ["/login/", "/sign-up/", "/dashboard/"],
            "live_orchestrator_exposed": False,
        },
        "capital": _capital(settings),
        "paper_lifecycle_portfolio_postmortem": (
            paper_lifecycle_portfolio_postmortem_public_status(settings=settings)
        ),
        "watching": watching,
        "phase1_data_spine": phase1_data_spine,
        "source_pipeline_summary": _build_source_pipeline_summary(watching),
        "source_heartbeat_history": _build_source_heartbeat_history(settings),
        "yahoo_finance": _safe_yahoo_finance_status(settings, generated_at),
        "preference_mcp": _safe_preference_mcp_status(settings, generated_at),
        "tradingview_mcp": _tradingview_mcp_status(settings),
        "bookmap_local_bridge": _bookmap_local_bridge_status(settings),
        "modules": _build_modules(health, generated_at),
        "process_console": _build_process_console(settings, generated_at),
        "decision_philosophy": _decision_philosophy(),
        "cognition": _build_cognition(settings),
        "tradingview_alerts": _tradingview_alerts(settings),
        "risk_agent": _risk_agent_status(settings),
        "execution_policy": _execution_policy_status(settings),
        "staged_paper_order": _staged_paper_order_status(settings),
        "broker_reconciliation": _broker_reconciliation_status(settings),
        "paper_submit_receipt": _paper_submit_receipt_status(settings),
        "quantum_oracle": quantum_oracle,
        "qctrl_fire_opal_ibm_readiness": fire_opal_ibm_readiness,
        "paper_live_activation": paper_live_activation_public_status(settings),
        "paper_live_qctrl_product_access": paper_live_qctrl_product_access_public_status(
            settings
        ),
        "paper_operational_mode": paper_operational_mode_public_status(settings),
        "paperops_alpaca_paper_submit_enablement": (
            paperops_alpaca_paper_submit_enablement_public_status(settings)
        ),
        "paperops_alpaca_paper_post": paperops_alpaca_paper_post_public_status(settings),
        "paperops_first_week_paper_trade_mandate": (
            first_week_paper_trade_mandate_public_status(settings)
        ),
        "paperops_paper_lifecycle_polling_enablement": (
            paperops_paper_lifecycle_polling_enablement_public_status(settings)
        ),
        "paperops_paper_lifecycle_poller": (
            paperops_paper_lifecycle_poller_public_status(settings)
        ),
        "paperops_guarded_paper_exit_enablement": (
            paperops_guarded_paper_exit_enablement_public_status(settings)
        ),
        "paperops_paper_exit_path": paperops_paper_exit_path_public_status(settings),
        "paperops_lifecycle_mirror_freshness": (
            build_paperops_lifecycle_mirror_freshness(
                settings=settings,
                generated_at=generated_at,
            )
        ),
        "paperops_close_to_ledger": build_paperops_close_to_ledger(
            settings=settings,
            generated_at=generated_at,
        ),
        "paperops_closed_trade_funnel": build_paperops_closed_trade_funnel(
            settings,
            generated_at=generated_at,
        ),
        "paperops_notification_review": paperops_notification_review_public_status(settings),
        "paperops_submit_regression_guard": (
            paperops_submit_regression_guard_public_status(settings)
        ),
        "paperops_source_gap_visibility": (
            paperops_source_gap_visibility_public_status(settings)
        ),
        "paperops_30_day_operations": paperops_30_day_operations_public_status(settings),
        "paperops_opportunity_scan_cadence": (
            paperops_opportunity_scan_cadence_public_status(settings)
        ),
        "paperops_cockpit_notification_upgrade": (
            paperops_cockpit_notification_upgrade_public_status(settings)
        ),
        "paper_live_certification": paper_live_certification_public_status(settings),
        "paperops_active_paper_trading_automation": (
            paperops_active_paper_trading_automation_public_status(settings)
        ),
        "paperops_qualified_setup_production": (
            paperops_qualified_setup_production_public_status(settings)
        ),
        "paperops_auto_approval_staged_order": (
            paperops_auto_approval_staged_order_public_status(settings)
        ),
        "paperops_qctrl_consultation": paperops_qctrl_public_status(settings),
        "trade_layer": _trade_layer(settings),
        "communications": _communications(settings),
        "live_bridge": live_bridge_contract(settings, generated_at),
        "durable_ingestion": durable_ingestion_status(settings),
        "phase4_strategy": _phase4_strategy_status(settings),
        "phase5_layer_b_readiness": _phase5_layer_b_readiness_status(settings),
        "phase5_kill_switch_ledger": _phase5_kill_switch_public_status(settings),
        "phase5_execution_adapter_status": _phase5_execution_adapter_public_status(settings),
        "phase5_paper_order_staging_gate": _phase5_paper_order_staging_public_status(settings),
        "phase5_alpaca_paper_dry_run": _phase5_alpaca_paper_dry_run_public_status(settings),
        "phase5_paper_submit_enablement_gate": _phase5_paper_submit_enablement_public_status(settings),
        "phase5_prediction_market_adapter": _phase5_prediction_market_adapter_public_status(settings),
        "phase5_telegram_notifier": _phase5_telegram_notifier_public_status(settings),
        "phase5_position_monitor": _phase5_position_monitor_public_status(settings),
        "phase5_signal_review": _phase5_signal_review_public_status(settings),
        "phase5_paper_trade_drill": _phase5_paper_trade_drill_public_status(settings),
        "phase5_certification": _phase5_certification_public_status(settings),
        "phase5_phase6_handoff": _phase5_phase6_handoff_public_status(settings),
        "phase6_learning_loop": _phase6_learning_loop_public_status(settings),
        "phase6_certification": _phase6_certification_public_status(settings),
        "phase7_demo_proof": _phase7_demo_proof_public_status(settings),
        "rs9_learning_loop": _rs9_learning_loop_public_status(settings),
        "forbidden_actions": _forbidden_actions(),
        "fund_manager_notes": _fund_manager_notes(settings),
        "execution_venues": [
            {
                "key": venue["key"],
                "name": venue["name"],
                "mode": venue["mode"],
                "account_scope": venue["account_scope"],
                "read_health": venue["read_health"],
                "write_health": venue["write_health"],
                "kill_switch_status": venue["kill_switch_status"],
                "first_release_allowed": venue["first_release_allowed"],
            }
            for venue in execution_registry()
        ],
        "boundary": "Public-safe read-only snapshot. It cannot trigger trading and contains no secrets.",
    }
    payload["edge_tracker"] = build_edge_tracker_status(
        watching=watching,
        quantum_oracle=quantum_oracle,
        qctrl_fire_opal_ibm=fire_opal_ibm_readiness,
        cognition=payload["cognition"],
        generated_at=generated_at,
        yahoo_finance=payload["yahoo_finance"],
    )
    payload["edge_pattern_ledger"] = build_edge_pattern_ledger(
        edge_tracker=payload["edge_tracker"],
        cognition=payload["cognition"],
        trade_layer=payload["trade_layer"],
        quantum_oracle=quantum_oracle,
        qctrl_fire_opal_ibm=fire_opal_ibm_readiness,
        paperops_30_day_operations=payload["paperops_30_day_operations"],
        generated_at=generated_at,
    )
    quantum_mandatory_review_gate = build_quantum_mandatory_review_gate(
        edge_ledger=payload["edge_pattern_ledger"],
        generated_at=generated_at,
    )
    payload["pattern_recognition_engine"] = build_pattern_recognition_engine(
        edge_tracker=payload["edge_tracker"],
        edge_pattern_ledger=payload["edge_pattern_ledger"],
        quantum_gate=quantum_mandatory_review_gate,
        generated_at=generated_at,
    )
    payload["paper_authority_reconciliation"] = build_paper_authority_reconciliation(
        payload,
        settings=settings,
        generated_at=generated_at,
    )
    payload["rs10_final_paper_autonomy_certification"] = (
        _rs10_final_paper_autonomy_public_status(payload, settings)
    )
    payload["phase5_system_map"] = phase5_system_map_public_status(
        payload,
        settings=settings,
        generated_at=generated_at,
    )
    operator_inbox_artifact = write_operator_inbox(payload, settings=settings)
    payload["operator_inbox"] = public_operator_inbox_status(operator_inbox_artifact)
    payload["mission_control"] = _mission_control(payload)
    payload["diagnostics"] = _diagnostics(payload)
    validate_cockpit_status(payload)
    return payload


def _walk_payload(payload: Any, path: str = "$") -> list[str]:
    problems: list[str] = []
    if isinstance(payload, dict):
        for key, value in payload.items():
            if key in PROHIBITED_KEYS:
                problems.append(f"prohibited key at {path}.{key}")
            problems.extend(_walk_payload(value, f"{path}.{key}"))
    elif isinstance(payload, list):
        for index, value in enumerate(payload):
            problems.extend(_walk_payload(value, f"{path}[{index}]"))
    elif isinstance(payload, str):
        for pattern in PROHIBITED_VALUE_PATTERNS:
            if pattern.search(payload):
                problems.append(f"token-like value at {path}")
        if (
            "/Users/" in payload
            or "\\Users\\" in payload
            or "/private/" in payload
            or "/var/folders/" in payload
            or payload.startswith("/tmp/")
        ):
            problems.append(f"local absolute path at {path}")
    return problems


def validate_cockpit_status(payload: dict[str, Any]) -> None:
    required = {
        "schema_version",
        "generated_at",
        "mode",
        "d1_snapshot",
        "d0_shell",
        "durable_ingestion",
        "diagnostics",
        "phase4_strategy",
        "phase5_layer_b_readiness",
        "phase5_kill_switch_ledger",
        "phase5_execution_adapter_status",
        "phase5_paper_order_staging_gate",
        "phase5_alpaca_paper_dry_run",
        "phase5_paper_submit_enablement_gate",
        "phase5_prediction_market_adapter",
        "phase5_telegram_notifier",
        "phase5_position_monitor",
        "phase5_signal_review",
        "phase5_paper_trade_drill",
        "phase5_certification",
        "phase5_phase6_handoff",
        "phase6_learning_loop",
        "phase6_certification",
        "phase7_demo_proof",
        "rs9_learning_loop",
        "rs10_final_paper_autonomy_certification",
        "phase5_system_map",
        "paper_live_activation",
        "paper_live_qctrl_product_access",
        "paper_operational_mode",
        "paperops_alpaca_paper_submit_enablement",
        "paperops_alpaca_paper_post",
        "paperops_first_week_paper_trade_mandate",
        "paperops_paper_lifecycle_polling_enablement",
        "paperops_paper_lifecycle_poller",
        "paperops_guarded_paper_exit_enablement",
        "paperops_paper_exit_path",
        "paperops_notification_review",
        "paperops_submit_regression_guard",
        "paperops_source_gap_visibility",
        "paperops_30_day_operations",
        "paperops_opportunity_scan_cadence",
        "paperops_cockpit_notification_upgrade",
        "paper_live_certification",
        "paperops_active_paper_trading_automation",
        "paper_authority_reconciliation",
        "paperops_qualified_setup_production",
        "paperops_auto_approval_staged_order",
        "paper_lifecycle_portfolio_postmortem",
        "operator_inbox",
        "yahoo_finance",
        "preference_mcp",
        "tradingview_mcp",
        "bookmap_local_bridge",
        "edge_tracker",
        "edge_pattern_ledger",
        "pattern_recognition_engine",
        "capital",
        "mission_control",
        "watching",
        "modules",
        "process_console",
        "decision_philosophy",
        "cognition",
        "tradingview_alerts",
        "risk_agent",
        "execution_policy",
        "staged_paper_order",
        "broker_reconciliation",
        "paper_submit_receipt",
        "trade_layer",
        "communications",
        "forbidden_actions",
        "fund_manager_notes",
        "live_bridge",
    }
    missing = sorted(required - set(payload))
    if missing:
        raise ValueError(f"cockpit status missing required keys: {missing}")
    if payload["schema_version"] != COCKPIT_STATUS_SCHEMA_VERSION:
        raise ValueError("cockpit status schema version mismatch")
    if payload["mode"] != "paper":
        raise ValueError("cockpit status can only be exported in paper mode")
    d1_snapshot = payload["d1_snapshot"]
    if d1_snapshot.get("phase") != "D1":
        raise ValueError("cockpit status D1 snapshot phase mismatch")
    if d1_snapshot.get("read_only") is not True:
        raise ValueError("cockpit status D1 snapshot must be read-only")
    if d1_snapshot.get("public_safe") is not True:
        raise ValueError("cockpit status D1 snapshot must be public-safe")
    if d1_snapshot.get("browser_authority") != "read_only":
        raise ValueError("browser authority must remain read-only")
    if d1_snapshot.get("local_orchestrator_exposed") is not False:
        raise ValueError("local orchestrator must not be exposed in D1")
    if payload["capital"].get("live_capital_enabled") is not False:
        raise ValueError("cockpit status must keep live capital disabled")
    mission_control = payload["mission_control"]
    for key in (
        "team",
        "data_sources",
        "strategy",
        "portfolio",
        "trades",
        "thinking",
        "safety",
    ):
        if key not in mission_control:
            raise ValueError(f"Mission Control CC1 projection missing: {key}")
    if not isinstance(mission_control.get("team"), list) or not mission_control["team"]:
        raise ValueError("Mission Control team projection must be a non-empty list")
    if mission_control["safety"].get("read_only") is not True:
        raise ValueError("Mission Control safety projection must remain read-only")
    if mission_control["safety"].get("live_capital_enabled") is not False:
        raise ValueError("Mission Control safety projection must keep live capital disabled")
    mission_strategy = mission_control["strategy"]
    if mission_strategy.get("native_edge", {}).get("name") != "Asymmetric Catalyst Proxy Trading":
        raise ValueError("Mission Control strategy native edge missing")
    if int(mission_strategy.get("strategy_family_count", 0) or 0) < 5:
        raise ValueError("Mission Control strategy universe must expose at least five families")
    if len(mission_strategy.get("strategy_families", [])) < 5:
        raise ValueError("Mission Control strategy family list missing")
    if not any(
        family.get("qualified_setup") is True
        for family in mission_strategy.get("strategy_families", [])
        if isinstance(family, dict)
    ):
        raise ValueError("Mission Control strategy universe must expose current setup state")
    diagnostics = payload["diagnostics"]
    if diagnostics.get("status") != "diagnostics_available":
        raise ValueError("cockpit diagnostics status mismatch")
    if not isinstance(diagnostics.get("audit_sections"), dict):
        raise ValueError("cockpit diagnostics audit sections missing")
    durable_ingestion = payload["durable_ingestion"]
    if durable_ingestion.get("write_authority") is not False:
        raise ValueError("durable ingestion must not have write authority in the cockpit")
    if durable_ingestion.get("signal_authority") is not False:
        raise ValueError("durable ingestion must not have signal authority in the cockpit")
    if durable_ingestion.get("order_authority") is not False:
        raise ValueError("durable ingestion must not have order authority in the cockpit")
    validate_edge_tracker_status(payload["edge_tracker"])
    validate_edge_pattern_ledger(payload["edge_pattern_ledger"])
    validate_pattern_recognition_engine(payload["pattern_recognition_engine"])
    yahoo_finance = payload["yahoo_finance"]
    missing_yahoo = sorted(YAHOO_FINANCE_PUBLIC_REQUIRED_FIELDS - set(yahoo_finance))
    if missing_yahoo:
        raise ValueError(f"Yahoo Finance public status missing fields: {missing_yahoo}")
    if yahoo_finance.get("public_safe") is not True:
        raise ValueError("Yahoo Finance public status must be public-safe")
    if yahoo_finance.get("canonical_source") is not False:
        raise ValueError("Yahoo Finance must not be exported as a canonical source")
    if yahoo_finance.get("market_confirmation_role") != "supplemental_market_confirmation":
        raise ValueError("Yahoo Finance must remain supplemental market confirmation")
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
            raise ValueError(f"Yahoo Finance public status must keep {key}=False")
    if yahoo_finance.get("status") not in {"deferred", "degraded", "live_read_only_ready"}:
        raise ValueError("Yahoo Finance public status is invalid")
    if yahoo_finance.get("symbol_allowlist_count", 0) < 1:
        raise ValueError("Yahoo Finance public status must include a symbol count")
    if "supplemental market confirmation" not in yahoo_finance.get("boundary", ""):
        raise ValueError("Yahoo Finance public boundary is weak")
    preference_mcp = payload["preference_mcp"]
    missing_preference = sorted(PREFERENCE_MCP_PUBLIC_REQUIRED_FIELDS - set(preference_mcp))
    if missing_preference:
        raise ValueError(f"Preference MCP public status missing fields: {missing_preference}")
    if preference_mcp.get("public_safe") is not True:
        raise ValueError("Preference MCP public status must be public-safe")
    if preference_mcp.get("source_key") != PREFERENCE_SOURCE_KEY:
        raise ValueError("Preference MCP source key mismatch")
    if preference_mcp.get("provider_label") != PREFERENCE_PROVIDER_LABEL:
        raise ValueError("Preference MCP provider label mismatch")
    if preference_mcp.get("classification") != PREFERENCE_CLASSIFICATION:
        raise ValueError("Preference MCP classification mismatch")
    if preference_mcp.get("status") not in {"challenge_only_ready", "catalog_only_ready", "disabled", "degraded"}:
        raise ValueError("Preference MCP public status is invalid")
    if preference_mcp.get("quota_status") not in {
        "verified",
        "disabled_live_mode",
        "blocked_pending_verified_identity",
    }:
        raise ValueError("Preference MCP quota status is invalid")
    if preference_mcp.get("approved_domain_pack_count") != len(preference_mcp.get("approved_domain_packs", [])):
        raise ValueError("Preference MCP approved domain pack count mismatch")
    if preference_mcp.get("approved_domain_pack_count", 0) < 1:
        raise ValueError("Preference MCP must expose approved domain-pack coverage")
    if preference_mcp.get("source_promotion_status") not in {"not_run", "validated"}:
        raise ValueError("Preference MCP source-promotion status is invalid")
    if preference_mcp.get("source_promotion_promoted_decision_count", 0) != 0:
        raise ValueError("Preference MCP source promotion must not promote sources locally")
    if (
        preference_mcp.get("source_promotion_canonical_source_count_after")
        != EXPECTED_SOURCE_COUNT
    ):
        raise ValueError("Preference MCP source promotion must preserve canonical source count")
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
            raise ValueError(f"Preference MCP public status must keep {key}=False")
    authority_flags = preference_mcp.get("authority_flags", {})
    if not isinstance(authority_flags, dict) or not authority_flags:
        raise ValueError("Preference MCP authority flags must be populated")
    for key, value in authority_flags.items():
        if value is not False:
            raise ValueError(f"Preference MCP authority flag enabled: {key}")
    preference_boundary = str(preference_mcp.get("boundary") or "")
    for phrase in ("read-only", "without secrets", "cannot satisfy source quorum", "create trade candidates"):
        if phrase not in preference_boundary:
            raise ValueError(f"Preference MCP public boundary missing: {phrase}")
    tradingview_mcp = payload["tradingview_mcp"]
    missing_tradingview_mcp = sorted(
        TRADINGVIEW_MCP_PUBLIC_REQUIRED_FIELDS - set(tradingview_mcp)
    )
    if missing_tradingview_mcp:
        raise ValueError(f"TradingView MCP public status missing fields: {missing_tradingview_mcp}")
    if tradingview_mcp.get("public_safe") is not True:
        raise ValueError("TradingView MCP public status must be public-safe")
    if tradingview_mcp.get("source_key") != "tradingview_mcp":
        raise ValueError("TradingView MCP source key mismatch")
    if tradingview_mcp.get("status") not in {"connected", "degraded"}:
        raise ValueError("TradingView MCP public status is invalid")
    if tradingview_mcp.get("technical_confirmation_role") != "supplemental_technical_confirmation_only":
        raise ValueError("TradingView MCP role must remain supplemental technical confirmation")
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
            raise ValueError(f"TradingView MCP public status must keep {key}=False")
    tradingview_mcp_boundary = str(tradingview_mcp.get("boundary") or "")
    for phrase in (
        "read-only supplemental technical analysis",
        "cannot create source quorum",
        "trade candidates",
        "paper orders",
        "broker writes",
    ):
        if phrase not in tradingview_mcp_boundary:
            raise ValueError(f"TradingView MCP public boundary missing: {phrase}")
    bookmap_local_bridge = payload["bookmap_local_bridge"]
    missing_bookmap = sorted(
        BOOKMAP_LOCAL_BRIDGE_PUBLIC_REQUIRED_FIELDS - set(bookmap_local_bridge)
    )
    if missing_bookmap:
        raise ValueError(f"Bookmap local bridge public status missing fields: {missing_bookmap}")
    if bookmap_local_bridge.get("public_safe") is not True:
        raise ValueError("Bookmap local bridge public status must be public-safe")
    if bookmap_local_bridge.get("source_key") != "bookmap":
        raise ValueError("Bookmap local bridge source key mismatch")
    if bookmap_local_bridge.get("status") not in {
        "connected",
        "sample_ready",
        "configured_pending_probe",
        "local_bridge_required",
        "disabled",
        "degraded",
    }:
        raise ValueError("Bookmap local bridge public status is invalid")
    if bookmap_local_bridge.get("orderflow_confirmation_role") != (
        "supplemental_orderflow_confirmation_only"
    ):
        raise ValueError("Bookmap role must remain supplemental orderflow confirmation")
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
        "bookmap_order_injection_allowed",
        "bookmap_trading_mode_allowed",
        "live_capital_enabled",
        "raw_payload_exposed",
        "local_path_exposed",
    ):
        if bookmap_local_bridge.get(key) is not False:
            raise ValueError(f"Bookmap local bridge public status must keep {key}=False")
    bookmap_boundary = str(bookmap_local_bridge.get("boundary") or "")
    for phrase in (
        "read-only supplemental order-flow context",
        "cannot create source quorum",
        "trade candidates",
        "paper orders",
        "broker writes",
    ):
        if phrase not in bookmap_boundary:
            raise ValueError(f"Bookmap local bridge public boundary missing: {phrase}")
    cognition_status = payload["cognition"]
    market_context = cognition_status.get("market_context", {})
    if not isinstance(market_context, dict):
        raise ValueError("market context public status missing")
    if market_context.get("packet_version") != MARKET_CONTEXT_PACKET_VERSION:
        raise ValueError("market context packet version mismatch")
    if market_context.get("status") not in {"ok", "degraded"}:
        raise ValueError("market context public status invalid")
    if int(market_context.get("packet_count", 0) or 0) < 1:
        raise ValueError("market context must expose at least one packet")
    for key in (
        "execution_allowed",
        "paper_order_allowed",
        "trade_candidate_creation_allowed",
        "risk_handoff_allowed",
        "broker_write_allowed",
        "live_capital_enabled",
        "source_quorum_credit_allowed",
    ):
        if int(market_context.get("authority_counts", {}).get(key, 0) or 0) != 0:
            raise ValueError(f"market context authority enabled: {key}")
    if "read-only context" not in str(market_context.get("boundary") or ""):
        raise ValueError("market context boundary is weak")
    market_context_packets = cognition_status.get("market_context_packets", [])
    if not isinstance(market_context_packets, list) or not market_context_packets:
        raise ValueError("market context packets missing from cognition")
    for packet in market_context_packets:
        if not isinstance(packet, dict):
            raise ValueError("market context packet must be an object")
        if packet.get("packet_version") != MARKET_CONTEXT_PACKET_VERSION:
            raise ValueError("market context packet version mismatch")
        if packet.get("trade_candidate_creation_allowed") is not False:
            raise ValueError("market context packet must not create trade candidates")
        if packet.get("paper_order_allowed") is not False:
            raise ValueError("market context packet must not allow paper orders")
        if packet.get("broker_write_allowed") is not False:
            raise ValueError("market context packet must not allow broker writes")
    paper_live_activation = payload["paper_live_activation"]
    if paper_live_activation.get("status") not in {
        "not_run",
        "approved_pending_later_enablement",
        "invalid",
    }:
        raise ValueError("Paper-live activation public status is invalid")
    if paper_live_activation.get("public_safe") is not True:
        raise ValueError("Paper-live activation status must be public-safe")
    if paper_live_activation.get("live_capital_enabled") is not False:
        raise ValueError("Paper-live activation must keep live capital disabled")
    if paper_live_activation.get("live_endpoint_allowed") is not False:
        raise ValueError("Paper-live activation must block live endpoints")
    if paper_live_activation.get("paper_order_submission_allowed") is not False:
        raise ValueError("Paper-live activation must not open paper submit authority")
    if paper_live_activation.get("forced_trades_allowed") is not False:
        raise ValueError("Paper-live activation must not allow forced trades")
    if paper_live_activation.get("qctrl_direct_execution_allowed") is not False:
        raise ValueError("Paper-live activation must keep Q-CTRL non-executing")
    for key in (
        "broker_post_called_count",
        "alpaca_post_called_count",
        "live_endpoint_called_count",
    ):
        if int(paper_live_activation.get(key, 0) or 0) != 0:
            raise ValueError(f"Paper-live activation unsafe count nonzero: {key}")
    if paper_live_activation.get("status") == "approved_pending_later_enablement":
        if paper_live_activation.get("approval_state") != "approved":
            raise ValueError("Paper-live activation approval state mismatch")
        if paper_live_activation.get("approval_logged") is not True:
            raise ValueError("Paper-live activation approval must be logged")
        if paper_live_activation.get("paper_live_activation_approved") is not True:
            raise ValueError("Paper-live activation approval flag missing")
        if paper_live_activation.get("paper_trading_system_approval_logged") is not True:
            raise ValueError("Paper-live system approval must be logged")
    paper_live_boundary = str(paper_live_activation.get("boundary") or "")
    for phrase in (
        "Alpaca paper-only",
        "cannot submit paper orders by itself",
        "cannot enable live capital",
    ):
        if phrase not in paper_live_boundary:
            raise ValueError("Paper-live activation boundary is weak")
    paper_live_qctrl = payload["paper_live_qctrl_product_access"]
    if paper_live_qctrl.get("status") not in {
        "not_run",
        "ready_for_explicit_qctrl_product_access_probe",
        "blocked_qctrl_product_access_or_subscription",
        "blocked_missing_qctrl_sdk",
        "qctrl_paper_consultation_ready",
        "invalid",
    }:
        raise ValueError("PT-1 Q-CTRL product access status is invalid")
    if paper_live_qctrl.get("public_safe") is not True:
        raise ValueError("PT-1 Q-CTRL product access must be public-safe")
    for key in (
        "execution_allowed",
        "paper_order_allowed",
        "broker_post_allowed",
        "alpaca_post_allowed",
        "live_endpoint_allowed",
        "live_capital_enabled",
        "hardware_submission_allowed",
        "phase7_proof_credit_allowed",
        "forced_trades_allowed",
        "secret_value_exposed",
        "raw_response_exposed",
        "raw_provider_response_persisted",
        "provider_failure_message_persisted",
    ):
        if paper_live_qctrl.get(key) is not False:
            raise ValueError(f"PT-1 Q-CTRL product access unsafe flag set: {key}")
    for key in (
        "broker_post_called_count",
        "alpaca_post_called_count",
        "live_endpoint_called_count",
    ):
        if int(paper_live_qctrl.get(key, 0) or 0) != 0:
            raise ValueError(f"PT-1 Q-CTRL product access unsafe count nonzero: {key}")
    if paper_live_qctrl.get("status") in {
        "blocked_qctrl_product_access_or_subscription",
        "blocked_missing_qctrl_sdk",
        "qctrl_paper_consultation_ready",
    }:
        if paper_live_qctrl.get("provider_call_attempted") is not True:
            raise ValueError("PT-1 Q-CTRL product access provider call missing")
        if int(paper_live_qctrl.get("provider_call_count", 0) or 0) < 1:
            raise ValueError("PT-1 Q-CTRL product access provider call count missing")
    qctrl_product_boundary = str(paper_live_qctrl.get("boundary") or "")
    for phrase in (
        "guarded PaperOps-Q",
        "cannot call brokers",
        "cannot grant Phase 7 proof credit",
    ):
        if phrase not in qctrl_product_boundary:
            raise ValueError("PT-1 Q-CTRL product access boundary is weak")
    paper_operational_mode = payload["paper_operational_mode"]
    if paper_operational_mode.get("status") not in {
        "not_run",
        "enabled_pending_downstream_gates",
        "invalid",
    }:
        raise ValueError("PT-2 paper operational mode status is invalid")
    if paper_operational_mode.get("public_safe") is not True:
        raise ValueError("PT-2 paper operational mode must be public-safe")
    if paper_operational_mode.get("paper_operational_mode_effective") is not True:
        raise ValueError("PT-2 paper operational mode must be effective")
    if paper_operational_mode.get("paper_operational_flag_disabled") is not False:
        raise ValueError("PT-2 paper operational mode flag must be effective")
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
            raise ValueError(f"PT-2 paper operational mode unsafe flag set: {key}")
    for key in (
        "broker_post_called_count",
        "alpaca_post_called_count",
        "live_endpoint_called_count",
        "qctrl_broker_post_called_count",
        "qctrl_alpaca_post_called_count",
        "qctrl_live_endpoint_called_count",
    ):
        if int(paper_operational_mode.get(key, 0) or 0) != 0:
            raise ValueError(f"PT-2 paper operational mode unsafe count nonzero: {key}")
    mode_boundary = str(paper_operational_mode.get("boundary") or "")
    for phrase in (
        "runtime PaperOps mode",
        "does not edit .env",
        "does not submit paper orders",
        "does not grant Phase 7 proof credit",
    ):
        if phrase not in mode_boundary:
            raise ValueError("PT-2 paper operational mode boundary is weak")
    paperops_alpaca = payload["paperops_alpaca_paper_post"]
    if paperops_alpaca.get("status") not in {
        "not_run",
        "disabled_pending_enablement",
        "ready_no_eligible_order",
        "ready_no_fresh_eligible_order",
        "ready_pending_explicit_execute",
        "submitted_to_alpaca_paper",
        "broker_post_failed_sanitized",
        "blocked_not_paper_mode",
        "blocked_live_capital_enabled",
        "blocked_non_paper_endpoint",
        "blocked_missing_alpaca_paper_credentials",
        "invalid",
    }:
        raise ValueError("PaperOps Alpaca paper POST public status is invalid")
    if paperops_alpaca.get("live_capital_enabled") is not False:
        raise ValueError("PaperOps Alpaca paper POST must keep live capital disabled")
    if int(paperops_alpaca.get("live_endpoint_called_count", 0) or 0) != 0:
        raise ValueError("PaperOps Alpaca paper POST must not call live endpoints")
    for key in (
        "secret_value_exposed",
        "raw_broker_payload_exposed",
        "broker_order_identifier_exposed",
    ):
        if paperops_alpaca.get(key) is not False:
            raise ValueError(f"PaperOps Alpaca paper POST public status must keep {key}=False")
    if "paper-only POST gate" not in paperops_alpaca.get("boundary", ""):
        raise ValueError("PaperOps Alpaca paper POST public boundary is weak")
    paperops_lifecycle = payload["paperops_paper_lifecycle_poller"]
    if paperops_lifecycle.get("status") not in {
        "not_run",
        "ready_no_submitted_paper_orders",
        "ready_pending_explicit_poll",
        "paper_lifecycle_poll_recorded",
        "paper_lifecycle_poll_failed_sanitized",
        "blocked_not_paper_mode",
        "blocked_live_capital_enabled",
        "blocked_non_paper_endpoint",
        "blocked_missing_alpaca_paper_credentials",
        "blocked_missing_paperops_alpaca_post_source",
        "blocked_invalid_paperops_alpaca_post_source",
        "blocked_lifecycle_polling_not_enabled",
        "invalid",
    }:
        raise ValueError("PaperOps lifecycle poller public status is invalid")
    if paperops_lifecycle.get("live_capital_enabled") is not False:
        raise ValueError("PaperOps lifecycle poller must keep live capital disabled")
    if int(paperops_lifecycle.get("live_endpoint_called_count", 0) or 0) != 0:
        raise ValueError("PaperOps lifecycle poller must not call live endpoints")
    if int(paperops_lifecycle.get("broker_post_called_count", 0) or 0) != 0:
        raise ValueError("PaperOps lifecycle poller must not call broker POST routes")
    if paperops_lifecycle.get("phase7_proof_credit_allowed") is not False:
        raise ValueError("PaperOps lifecycle poller must not grant Phase 7 proof credit")
    for key in (
        "secret_value_exposed",
        "raw_broker_payload_exposed",
        "broker_order_identifier_exposed",
    ):
        if paperops_lifecycle.get(key) is not False:
            raise ValueError(f"PaperOps lifecycle poller public status must keep {key}=False")
    lifecycle_boundary = paperops_lifecycle.get("boundary", "")
    if "read-only Alpaca paper lifecycle poller" not in lifecycle_boundary:
        raise ValueError("PaperOps lifecycle poller public boundary is weak")
    paperops_exit = payload["paperops_paper_exit_path"]
    if paperops_exit.get("status") not in {
        "not_run",
        "disabled_pending_enablement",
        "ready_no_exit_candidate",
        "ready_pending_lifecycle_mirror_refresh",
        "ready_pending_explicit_execute",
        "paper_exit_close_recorded",
        "paper_exit_close_failed_sanitized",
        "blocked_paper_position_preflight_readback_failed",
        "blocked_not_paper_mode",
        "blocked_live_capital_enabled",
        "blocked_non_paper_endpoint",
        "blocked_missing_alpaca_paper_credentials",
        "blocked_missing_paper_lifecycle_source",
        "blocked_invalid_paper_lifecycle_source",
        "invalid",
    }:
        raise ValueError("PaperOps exit path public status is invalid")
    if paperops_exit.get("live_capital_enabled") is not False:
        raise ValueError("PaperOps exit path must keep live capital disabled")
    if int(paperops_exit.get("live_endpoint_called_count", 0) or 0) != 0:
        raise ValueError("PaperOps exit path must not call live endpoints")
    if int(paperops_exit.get("broker_post_called_count", 0) or 0) != 0:
        raise ValueError("PaperOps exit path must not call broker POST routes")
    if int(paperops_exit.get("order_cancel_called_count", 0) or 0) != 0:
        raise ValueError("PaperOps exit path must not cancel orders")
    if int(paperops_exit.get("position_resize_called_count", 0) or 0) != 0:
        raise ValueError("PaperOps exit path must not resize positions")
    if paperops_exit.get("phase7_proof_credit_allowed") is not False:
        raise ValueError("PaperOps exit path must not grant Phase 7 proof credit")
    for key in (
        "secret_value_exposed",
        "raw_broker_payload_exposed",
        "broker_order_identifier_exposed",
    ):
        if paperops_exit.get(key) is not False:
            raise ValueError(f"PaperOps exit path public status must keep {key}=False")
    exit_boundary = paperops_exit.get("boundary", "")
    if "guarded Alpaca paper-only exit path" not in exit_boundary:
        raise ValueError("PaperOps exit path public boundary is weak")
    lifecycle_mirror_freshness = payload["paperops_lifecycle_mirror_freshness"]
    if lifecycle_mirror_freshness.get("public_safe") is not True:
        raise ValueError("PaperOps lifecycle/mirror freshness must be public-safe")
    if lifecycle_mirror_freshness.get("live_capital_enabled") is not False:
        raise ValueError("PaperOps lifecycle/mirror freshness must keep live capital disabled")
    if int(lifecycle_mirror_freshness.get("live_endpoint_called_count", 0) or 0) != 0:
        raise ValueError("PaperOps lifecycle/mirror freshness must not call live endpoints")
    if int(lifecycle_mirror_freshness.get("broker_post_called_count", 0) or 0) != 0:
        raise ValueError("PaperOps lifecycle/mirror freshness must not call broker POST routes")
    if lifecycle_mirror_freshness.get("phase7_proof_credit_allowed") is not False:
        raise ValueError("PaperOps lifecycle/mirror freshness must not grant proof credit")
    close_to_ledger = payload["paperops_close_to_ledger"]
    close_to_ledger_errors = validate_paperops_close_to_ledger(close_to_ledger)
    if close_to_ledger_errors:
        raise ValueError(
            "PaperOps close-to-ledger invalid: " + ",".join(close_to_ledger_errors)
        )
    if close_to_ledger.get("public_safe") is not True:
        raise ValueError("PaperOps close-to-ledger must be public-safe")
    if close_to_ledger.get("live_capital_enabled") is not False:
        raise ValueError("PaperOps close-to-ledger must keep live capital disabled")
    if int(close_to_ledger.get("live_endpoint_called_count", 0) or 0) != 0:
        raise ValueError("PaperOps close-to-ledger must not call live endpoints")
    if int(close_to_ledger.get("broker_post_called_count", 0) or 0) != 0:
        raise ValueError("PaperOps close-to-ledger must not call broker POST routes")
    if close_to_ledger.get("phase7_proof_credit_allowed") is not False:
        raise ValueError("PaperOps close-to-ledger must not grant Phase 7 proof credit")
    closed_trade_funnel = payload["paperops_closed_trade_funnel"]
    funnel_errors = validate_paperops_closed_trade_funnel(closed_trade_funnel)
    if funnel_errors:
        raise ValueError("PaperOps closed trade funnel invalid: " + ",".join(funnel_errors))
    if closed_trade_funnel.get("boundary") != (
        "Read-only closed paper trade funnel diagnostic. It cannot submit, close, "
        "cancel, resize, approve, or grant paper proof ledger credit."
    ):
        raise ValueError("PaperOps closed trade funnel public boundary is weak")
    paperops_notification = payload["paperops_notification_review"]
    if paperops_notification.get("status") not in {
        "not_run",
        "review_ready",
        "invalid",
    }:
        raise ValueError("PaperOps notification review public status is invalid")
    if paperops_notification.get("public_safe") is not True:
        raise ValueError("PaperOps notification review must be public-safe")
    if paperops_notification.get("live_capital_enabled") is not False:
        raise ValueError("PaperOps notification review must keep live capital disabled")
    for key in (
        "live_send_allowed_count",
        "telegram_command_path_enabled_count",
        "telegram_trade_command_enabled_count",
        "telegram_approve_trade_command_enabled_count",
        "telegram_reject_trade_command_enabled_count",
        "telegram_modify_trade_command_enabled_count",
        "telegram_resize_trade_command_enabled_count",
        "telegram_close_trade_command_enabled_count",
        "telegram_cancel_trade_command_enabled_count",
        "broker_write_allowed_count",
        "broker_post_allowed_count",
        "paper_order_allowed_count",
        "paper_order_submission_allowed_count",
        "position_close_allowed_count",
        "position_resize_allowed_count",
        "prediction_market_write_allowed_count",
        "crypto_perps_write_allowed_count",
        "live_endpoint_allowed_count",
        "live_capital_enabled_count",
    ):
        if int(paperops_notification.get(key, 0) or 0) != 0:
            raise ValueError(f"PaperOps notification review unsafe count nonzero: {key}")
    if paperops_notification.get("phase7_proof_credit_allowed") is not False:
        raise ValueError("PaperOps notification review must not grant Phase 7 proof credit")
    for key in (
        "secret_value_exposed",
        "raw_payload_exposed",
        "authorization_header_exposed",
        "chat_id_exposed",
        "bot_token_exposed",
    ):
        if paperops_notification.get(key) is not False:
            raise ValueError(f"PaperOps notification review must keep {key}=False")
    notification_boundary = paperops_notification.get("boundary", "")
    if (
        "Telegram remains notify-only" not in notification_boundary
        or "separate explicit send-test approval" not in notification_boundary
    ):
        raise ValueError("PaperOps notification review boundary is weak")
    submit_regression_guard = payload["paperops_submit_regression_guard"]
    if submit_regression_guard.get("status") not in {
        "not_run",
        "healthy_idle_idempotency_guarded",
        "healthy_idle_no_fresh_submit",
        "healthy_submitted_idempotency_recorded",
        "ready_fresh_submit_consistent",
        "blocked_submit_regression",
        "invalid",
    }:
        raise ValueError("PaperOps submit regression guard public status is invalid")
    if submit_regression_guard.get("public_safe") is not True:
        raise ValueError("PaperOps submit regression guard must be public-safe")
    if submit_regression_guard.get("live_capital_enabled") is not False:
        raise ValueError("PaperOps submit regression guard must keep live capital disabled")
    if submit_regression_guard.get("phase7_proof_credit_allowed") is not False:
        raise ValueError("PaperOps submit regression guard must not grant proof credit")
    for key in (
        "live_endpoint_called_count",
        "broker_post_called_count",
        "broker_write_allowed_count",
        "source_stale_after_post_tolerance_count",
        "fresh_submitted_ledger_collision_count",
        "duplicate_misclassified_as_fresh_count",
    ):
        if int(submit_regression_guard.get(key, 0) or 0) != 0:
            raise ValueError(f"PaperOps submit regression guard count nonzero: {key}")
    if int(submit_regression_guard.get("blocker_count", 0) or 0) != 0:
        raise ValueError("PaperOps submit regression guard has blockers")
    for key in (
        "secret_value_exposed",
        "raw_payload_exposed",
        "raw_broker_payload_exposed",
        "broker_order_identifier_exposed",
    ):
        if submit_regression_guard.get(key) is not False:
            raise ValueError(f"PaperOps submit regression guard must keep {key}=False")
    guard_boundary = str(submit_regression_guard.get("boundary") or "")
    for phrase in (
        "submit-side regression guard",
        "cannot submit",
        "cannot call live endpoints",
        "cannot enable live capital",
        "cannot grant proof credit",
    ):
        if phrase not in guard_boundary:
            raise ValueError("PaperOps submit regression guard boundary is weak")
    source_gap_visibility = payload["paperops_source_gap_visibility"]
    if source_gap_visibility.get("status") not in {
        "explicit_optional_source_gaps",
        "all_optional_sources_configured",
    }:
        raise ValueError("PaperOps source-gap visibility status is invalid")
    if int(source_gap_visibility.get("validation_error_count", 0) or 0) != 0:
        raise ValueError("PaperOps source-gap visibility has validation errors")
    if source_gap_visibility.get("public_safe") is not True:
        raise ValueError("PaperOps source-gap visibility must be public-safe")
    if source_gap_visibility.get("source_gap_policy_status") != (
        "optional_gaps_explicit_non_blocking"
    ):
        raise ValueError("PaperOps source-gap policy status is invalid")
    if int(source_gap_visibility.get("required_gap_count", 0) or 0) != 0:
        raise ValueError("PaperOps source-gap visibility has required source gaps")
    if int(source_gap_visibility.get("trade_blocking_source_gap_count", 0) or 0) != 0:
        raise ValueError("PaperOps source-gap visibility has trade-blocking gaps")
    if int(source_gap_visibility.get("source_quorum_blocking_gap_count", 0) or 0) != 0:
        raise ValueError("PaperOps source-gap visibility has source-quorum blockers")
    if int(source_gap_visibility.get("silent_blocker_count", 0) or 0) != 0:
        raise ValueError("PaperOps source-gap visibility has silent blockers")
    if int(source_gap_visibility.get("blocker_count", 0) or 0) != 0:
        raise ValueError("PaperOps source-gap visibility has blockers")
    if source_gap_visibility.get("live_capital_enabled") is not False:
        raise ValueError("PaperOps source-gap visibility must keep live capital disabled")
    if source_gap_visibility.get("phase7_proof_credit_allowed") is not False:
        raise ValueError("PaperOps source-gap visibility must not grant proof credit")
    for key in (
        "broker_post_called_count",
        "broker_write_allowed_count",
        "live_endpoint_called_count",
    ):
        if int(source_gap_visibility.get(key, 0) or 0) != 0:
            raise ValueError(f"PaperOps source-gap visibility unsafe count nonzero: {key}")
    paperops_30_day = payload["paperops_30_day_operations"]
    missing_paperops_30_day = sorted(
        PAPEROPS_30_DAY_OPERATIONS_PUBLIC_REQUIRED_FIELDS - set(paperops_30_day)
    )
    if missing_paperops_30_day:
        raise ValueError(
            "PaperOps 30-day operations public status missing fields: "
            f"{missing_paperops_30_day}"
        )
    if paperops_30_day.get("status") not in {
        "not_run",
        "operations_active",
        "operations_complete_pending_certification",
        "blocked_pending_operations_enablement",
        "invalid",
    }:
        raise ValueError("PaperOps 30-day operations public status is invalid")
    if paperops_30_day.get("public_safe") is not True:
        raise ValueError("PaperOps 30-day operations status must be public-safe")
    if paperops_30_day.get("live_capital_enabled") is not False:
        raise ValueError("PaperOps 30-day operations must keep live capital disabled")
    if paperops_30_day.get("phase7_proof_credit_allowed") is not False:
        raise ValueError("PaperOps 30-day operations must not grant Phase 7 proof credit")
    if int(paperops_30_day.get("unsafe_write_counter_total", 0) or 0) != 0:
        raise ValueError("PaperOps 30-day operations unsafe counter must stay zero")
    if paperops_30_day.get("status") != "not_run":
        if paperops_30_day.get("recorded") is not True:
            raise ValueError("PaperOps 30-day operations must be recorded after running")
        if paperops_30_day.get("event_log_written") is not True:
            raise ValueError("PaperOps 30-day operations event log must be written")
        if paperops_30_day.get("event_log_event_count") != 1:
            raise ValueError("PaperOps 30-day operations event count mismatch")
        safe_historical_paperops_block = (
            paperops_30_day.get("status") == "invalid"
            and paperops_30_day.get("paper_operational_cycle_safe_to_continue") is True
            and paperops_30_day.get("no_forced_trades") is True
            and paperops_30_day.get("live_capital_enabled") is False
            and paperops_30_day.get("phase7_proof_credit_allowed") is False
            and int(paperops_30_day.get("unsafe_write_counter_total", 0) or 0) == 0
        )
        if (
            paperops_30_day.get("validation_error_count") != 0
            and not safe_historical_paperops_block
        ):
            raise ValueError("PaperOps 30-day operations validation errors present")
    if paperops_30_day.get("status") == "operations_active":
        if paperops_30_day.get("automation_active") is not True:
            raise ValueError("PaperOps 30-day operations automation is inactive")
        if paperops_30_day.get("automation_prompt_paperops_bound") is not True:
            raise ValueError("PaperOps 30-day operations prompt is not PaperOps-bound")
        if paperops_30_day.get("dashboard_mirror_public_safe") is not True:
            raise ValueError("PaperOps 30-day operations dashboard mirror is not public-safe")
    operations_boundary = str(paperops_30_day.get("boundary") or "")
    for phrase in (
        "active paper growth trial",
        "cannot backfill days",
        "cannot force trades",
        "cannot enable live capital",
    ):
        if phrase not in operations_boundary:
            raise ValueError("PaperOps 30-day operations boundary is weak")
    paperops_opportunity_scan = payload["paperops_opportunity_scan_cadence"]
    missing_opportunity_scan = sorted(
        set(PAPEROPS_OPPORTUNITY_SCAN_CADENCE_PUBLIC_FIELDS)
        - set(paperops_opportunity_scan)
    )
    if missing_opportunity_scan:
        raise ValueError(
            "PaperOps opportunity scan cadence public status missing fields: "
            f"{missing_opportunity_scan}"
        )
    if paperops_opportunity_scan.get("status") not in {
        "not_run",
        "scan_ready_no_candidate",
        "scan_ready_candidate_monitoring",
        "scan_ready_fresh_submit_pending_hourly_runner",
        "invalid",
    }:
        raise ValueError("PaperOps opportunity scan cadence status is invalid")
    if paperops_opportunity_scan.get("public_safe") is not True:
        raise ValueError("PaperOps opportunity scan cadence must be public-safe")
    if paperops_opportunity_scan.get("opportunity_scan_interval_minutes") != 20:
        raise ValueError("PaperOps opportunity scan cadence must remain 20 minutes")
    if paperops_opportunity_scan.get("opportunity_scan_frequency_per_hour") != 3:
        raise ValueError("PaperOps opportunity scan frequency must remain three per hour")
    if paperops_opportunity_scan.get("trade_submission_allowed_by_scan") is not False:
        raise ValueError("PaperOps opportunity scan must not allow submission")
    for key in (
        "forced_trades_allowed",
        "live_capital_enabled",
        "phase7_proof_credit_allowed",
    ):
        if paperops_opportunity_scan.get(key) is not False:
            raise ValueError(f"PaperOps opportunity scan forbidden: {key}")
    for key in (
        "broker_post_called_count",
        "alpaca_post_called_count",
        "live_endpoint_called_count",
        "broker_write_allowed_count",
        "unsafe_write_counter_total",
    ):
        if int(paperops_opportunity_scan.get(key, 0) or 0) != 0:
            raise ValueError(f"PaperOps opportunity scan unsafe count nonzero: {key}")
    if paperops_opportunity_scan.get("status") != "not_run":
        if paperops_opportunity_scan.get("recorded") is not True:
            raise ValueError("PaperOps opportunity scan cadence must be recorded")
        if paperops_opportunity_scan.get("event_log_written") is not True:
            raise ValueError("PaperOps opportunity scan event log missing")
        if paperops_opportunity_scan.get("event_log_event_count") != 1:
            raise ValueError("PaperOps opportunity scan event count mismatch")
        if paperops_opportunity_scan.get("validation_error_count") != 0:
            raise ValueError("PaperOps opportunity scan validation errors present")
    opportunity_boundary = str(paperops_opportunity_scan.get("boundary") or "")
    for phrase in (
        "read-only candidate refresh cadence",
        "every 20 minutes",
        "cannot submit broker orders",
        "hourly PaperOps runner remains the guarded submission transport",
    ):
        if phrase not in opportunity_boundary:
            raise ValueError("PaperOps opportunity scan cadence boundary is weak")
    paperops_cockpit_notification = payload["paperops_cockpit_notification_upgrade"]
    missing_pt9 = sorted(
        PAPEROPS_COCKPIT_NOTIFICATION_UPGRADE_PUBLIC_REQUIRED_FIELDS
        - set(paperops_cockpit_notification)
    )
    if missing_pt9:
        raise ValueError(
            "PaperOps cockpit notification public status missing fields: "
            f"{missing_pt9}"
        )
    if paperops_cockpit_notification.get("status") not in {
        "not_run",
        "cockpit_notification_upgrade_ready",
        "blocked_cockpit_notification_upgrade",
        "invalid",
    }:
        raise ValueError("PaperOps cockpit notification upgrade status is invalid")
    if paperops_cockpit_notification.get("public_safe") is not True:
        raise ValueError("PaperOps cockpit notification upgrade must be public-safe")
    if paperops_cockpit_notification.get("live_capital_enabled") is not False:
        raise ValueError("PaperOps cockpit notification upgrade enabled live capital")
    if paperops_cockpit_notification.get("phase7_proof_credit_allowed") is not False:
        raise ValueError("PaperOps cockpit notification upgrade granted proof credit")
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
            raise ValueError(
                "PaperOps cockpit notification unsafe count nonzero: "
                f"{key}"
            )
    if (
        paperops_cockpit_notification.get("qctrl_hold_visible") is True
        and paperops_cockpit_notification.get("paper_submit_visible_as_held")
        is not True
    ):
        raise ValueError("PaperOps cockpit notification hid the Q-CTRL submit hold")
    if paperops_cockpit_notification.get("status") == (
        "cockpit_notification_upgrade_ready"
    ):
        if paperops_cockpit_notification.get("recorded") is not True:
            raise ValueError("PaperOps cockpit notification upgrade must be recorded")
        if paperops_cockpit_notification.get("event_log_written") is not True:
            raise ValueError("PaperOps cockpit notification event log missing")
        if paperops_cockpit_notification.get("event_log_event_count") != 1:
            raise ValueError("PaperOps cockpit notification event count mismatch")
        if paperops_cockpit_notification.get("validation_error_count") != 0:
            raise ValueError("PaperOps cockpit notification validation errors present")
        if paperops_cockpit_notification.get("cockpit_upgrade_ready") is not True:
            raise ValueError("PaperOps cockpit notification ready flag is false")
        if paperops_cockpit_notification.get("notification_upgrade_ready") is not True:
            raise ValueError("PaperOps notification upgrade ready flag is false")
        if int(paperops_cockpit_notification.get("fund_manager_readout_count", 0) or 0) < 5:
            raise ValueError("PaperOps cockpit notification readouts missing")
    pt9_boundary = str(paperops_cockpit_notification.get("boundary") or "")
    for phrase in (
        "PT-9 upgrades the cockpit and notification review surface",
        "review-only notification previews",
        "cannot send Telegram messages",
        "cannot enable Telegram commands",
        "cannot call brokers",
        "cannot enable live capital",
    ):
        if phrase not in pt9_boundary:
            raise ValueError("PaperOps cockpit notification boundary is weak")
    paper_live_certification = payload["paper_live_certification"]
    missing_pt10 = sorted(
        PAPER_LIVE_CERTIFICATION_PUBLIC_REQUIRED_FIELDS
        - set(paper_live_certification)
    )
    if missing_pt10:
        raise ValueError(
            "Paper-live certification public status missing fields: "
            f"{missing_pt10}"
        )
    if paper_live_certification.get("status") not in {
        "not_run",
        "blocked_pending_qctrl_and_phase7_proof",
        "blocked_pending_qctrl",
        "blocked_pending_phase7_proof",
        "blocked_pending_certification_gates",
        "blocked_paper_live_control_plane",
        "paper_live_certified",
        "invalid",
    }:
        raise ValueError("Paper-live certification status is invalid")
    if paper_live_certification.get("public_safe") is not True:
        raise ValueError("Paper-live certification must be public-safe")
    if paper_live_certification.get("live_capital_enabled") is not False:
        raise ValueError("Paper-live certification enabled live capital")
    if paper_live_certification.get("phase7_proof_credit_allowed") is not False:
        raise ValueError("Paper-live certification granted Phase 7 proof credit")
    if (
        paper_live_certification.get("qctrl_hold_active") is True
        and paper_live_certification.get("paper_submit_step_allowed") is True
    ):
        raise ValueError("Paper-live certification bypassed the Q-CTRL hold")
    if (
        paper_live_certification.get("qctrl_hold_active") is True
        and paper_live_certification.get("paper_submit_visible_as_held") is not True
    ):
        raise ValueError("Paper-live certification hid the Q-CTRL submit hold")
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
            raise ValueError(
                "Paper-live certification unsafe count nonzero: "
                f"{key}"
            )
    if paper_live_certification.get("status") in {
        "blocked_pending_qctrl_and_phase7_proof",
        "paper_live_certified",
    }:
        if paper_live_certification.get("recorded") is not True:
            raise ValueError("Paper-live certification must be recorded")
        if paper_live_certification.get("event_log_written") is not True:
            raise ValueError("Paper-live certification event log missing")
        if paper_live_certification.get("event_log_event_count") != 1:
            raise ValueError("Paper-live certification event count mismatch")
        if paper_live_certification.get("validation_error_count") != 0:
            raise ValueError("Paper-live certification validation errors present")
        if paper_live_certification.get("paper_live_certification_gate_evaluated") is not True:
            raise ValueError("Paper-live certification gate not evaluated")
        if paper_live_certification.get("paper_live_control_plane_certified") is not True:
            raise ValueError("Paper-live control plane not certified")
    if paper_live_certification.get("status") == "blocked_pending_qctrl_and_phase7_proof":
        if paper_live_certification.get("paper_live_certified") is not False:
            raise ValueError("Blocked paper-live certification reports certified")
        if paper_live_certification.get("paper_live_operation_allowed") is not False:
            raise ValueError("Blocked paper-live certification allows operation")
        if int(paper_live_certification.get("certification_blocker_count", 0) or 0) < 1:
            raise ValueError("Blocked paper-live certification has no blockers")
    pt10_boundary = str(paper_live_certification.get("boundary") or "")
    for phrase in (
        "PT-10 is a paper-live certification gate only",
        "cannot bypass Q-CTRL product access",
        "cannot submit paper orders",
        "cannot call brokers",
        "cannot mark paper performance as mature without verified records",
        "cannot enable live capital",
    ):
        if phrase not in pt10_boundary:
            raise ValueError("Paper-live certification boundary is weak")
    paperops_active_automation = payload["paperops_active_paper_trading_automation"]
    missing_paperops_active = sorted(
        PAPEROPS_ACTIVE_AUTOMATION_PUBLIC_REQUIRED_FIELDS
        - set(paperops_active_automation)
    )
    if missing_paperops_active:
        raise ValueError(
            "PaperOps active paper automation public status missing fields: "
            f"{missing_paperops_active}"
        )
    if paperops_active_automation.get("status") not in {
        "not_run",
        "blocked_active_automation_safety_or_binding",
        "invalid",
        *PAPEROPS_ACTIVE_AUTOMATION_READY_STATUSES,
    }:
        raise ValueError("PaperOps active paper automation status is invalid")
    if paperops_active_automation.get("public_safe") is not True:
        raise ValueError("PaperOps active paper automation must be public-safe")
    if paperops_active_automation.get("status") != "not_run":
        if paperops_active_automation.get("recorded") is not True:
            raise ValueError("PaperOps active paper automation must be recorded")
        if paperops_active_automation.get("event_log_written") is not True:
            raise ValueError("PaperOps active paper automation event log missing")
        if paperops_active_automation.get("event_log_event_count") != 1:
            raise ValueError("PaperOps active paper automation event count mismatch")
        if paperops_active_automation.get("validation_error_count") != 0:
            raise ValueError("PaperOps active paper automation validation errors present")
    if paperops_active_automation.get("status") in PAPEROPS_ACTIVE_AUTOMATION_READY_STATUSES:
        if (
            paperops_active_automation.get(
                "active_paper_trading_automation_enabled"
            )
            is not True
        ):
            raise ValueError("PaperOps active paper automation enabled flag is false")
        if (
            paperops_active_automation.get(
                "active_paper_trading_automation_effective"
            )
            is not True
        ):
            raise ValueError("PaperOps active paper automation effective flag is false")
        if paperops_active_automation.get("automation_active") is not True:
            raise ValueError("PaperOps active paper automation scheduler inactive")
        if (
            paperops_active_automation.get("automation_prompt_active_trade_bound")
            is not True
        ):
            raise ValueError("PaperOps active paper automation prompt is not bound")
        if paperops_active_automation.get("paper_endpoint_confirmed") is not True:
            raise ValueError("PaperOps active paper automation missing paper endpoint")
    if (
        paperops_active_automation.get("qctrl_consultation_hold_active") is True
        and paperops_active_automation.get("paper_submit_step_allowed") is True
    ):
        raise ValueError("PaperOps active paper automation bypassed Q-CTRL hold")
    for key in (
        "direct_broker_shortcut_allowed",
        "qctrl_direct_execution_allowed",
        "forced_trades_allowed",
        "phase7_proof_credit_allowed",
        "live_capital_enabled",
    ):
        if paperops_active_automation.get(key) is not False:
            raise ValueError(f"PaperOps active paper automation forbidden: {key}")
    for key in ("live_endpoint_called_count", "unsafe_write_counter_total"):
        if int(paperops_active_automation.get(key, 0) or 0) != 0:
            raise ValueError(
                f"PaperOps active paper automation unsafe count nonzero: {key}"
            )
    if paperops_active_automation.get("rs5_daily_target_policy") != "minimum_not_ceiling":
        raise ValueError("PaperOps active paper automation RS-5 target policy is invalid")
    if paperops_active_automation.get("rs5_daily_target_is_minimum") is not True:
        raise ValueError("PaperOps active paper automation RS-5 target is not minimum")
    if (
        paperops_active_automation.get(
            "rs5_daily_target_blocks_additional_qualified_setups"
        )
        is not False
    ):
        raise ValueError("PaperOps active paper automation RS-5 target is a ceiling")
    if paperops_active_automation.get("rs5_guarded_submit_transport") != "paperops2_only":
        raise ValueError("PaperOps active paper automation RS-5 transport is invalid")
    if (
        int(
            paperops_active_automation.get(
                "rs5_max_guarded_submit_attempts_per_run",
                0,
            )
            or 0
        )
        > 3
    ):
        raise ValueError("PaperOps active paper automation RS-5 attempts exceed cap")
    if (
        paperops_active_automation.get("rs5_daily_target_met") is True
        and int(
            paperops_active_automation.get(
                "rs5_available_distinct_setup_count",
                0,
            )
            or 0
        )
        > 0
        and paperops_active_automation.get("idle_reason")
        == "daily_paper_trade_target_met"
    ):
        raise ValueError("PaperOps active paper automation treated target as ceiling")
    if not str(paperops_active_automation.get("why_not_trading_now") or "").strip():
        raise ValueError("PaperOps active paper automation why-not-trading is missing")
    active_boundary = str(paperops_active_automation.get("boundary") or "")
    for phrase in (
        "PT-8 binds the hourly PaperOps automation",
        "PaperOps-2, PaperOps-3, and PaperOps-4",
        "Q-CTRL paper consultation hold",
        "only submit to Alpaca paper",
        "cannot enable live capital",
    ):
        if phrase not in active_boundary:
            raise ValueError("PaperOps active paper automation boundary is weak")
    paper_authority = payload["paper_authority_reconciliation"]
    missing_paper_authority = sorted(
        set(PAPER_AUTHORITY_RECONCILIATION_PUBLIC_FIELDS) - set(paper_authority)
    )
    if missing_paper_authority:
        raise ValueError(
            "Paper authority reconciliation missing public fields: "
            f"{missing_paper_authority}"
        )
    if paper_authority.get("validation_error_count") != 0:
        raise ValueError("Paper authority reconciliation validation errors present")
    if validate_paper_authority_reconciliation(paper_authority):
        raise ValueError("Paper authority reconciliation validation failed")
    if paper_authority.get("public_safe") is not True:
        raise ValueError("Paper authority reconciliation must be public-safe")
    if paper_authority.get("paper_submission_transport") != "paperops_guarded_alpaca_paper":
        raise ValueError("Paper authority reconciliation transport is invalid")
    if paper_authority.get("live_capital_enabled") is not False:
        raise ValueError("Paper authority reconciliation enabled live capital")
    if paper_authority.get("live_capital_blocked") is not True:
        raise ValueError("Paper authority reconciliation did not block live capital")
    if paper_authority.get("status") not in {
        "blocked_by_safety",
        "paper_authorized_blocked_operational",
        "paper_authorized_waiting_for_setup",
        "paper_authorized_ready_to_submit",
        "paper_authorized_ready_to_poll",
        "paper_authorized_ready_to_exit",
        "paper_authorized_idle",
    }:
        raise ValueError("Paper authority reconciliation status is invalid")
    if (
        paper_authority.get("status") == "paper_authorized_blocked_operational"
        and "automation_not_active"
        not in paper_authority.get("operational_blockers", [])
    ):
        raise ValueError("Paper authority reconciliation hid inactive automation")
    if paper_authority.get("paper_submit_currently_allowed") is True and (
        paperops_active_automation.get("paper_submit_step_allowed") is not True
    ):
        raise ValueError("Paper authority reconciliation invented paper submit authority")
    paperops_qualified_setup = payload["paperops_qualified_setup_production"]
    missing_qualified_setup = sorted(
        PAPEROPS_QUALIFIED_SETUP_PRODUCTION_PUBLIC_REQUIRED_FIELDS
        - set(paperops_qualified_setup)
    )
    if missing_qualified_setup:
        raise ValueError(
            "PaperOps qualified setup production public status missing fields: "
            f"{missing_qualified_setup}"
        )
    if paperops_qualified_setup.get("status") not in {
        "not_run",
        "production_path_ready_with_qualified_setup",
        "production_path_ready_no_current_qualified_setup",
        "blocked_pending_paperops_prerequisite",
        "invalid",
    }:
        raise ValueError("PaperOps qualified setup production status is invalid")
    if paperops_qualified_setup.get("public_safe") is not True:
        raise ValueError("PaperOps qualified setup production must be public-safe")
    if paperops_qualified_setup.get("status") != "not_run":
        if paperops_qualified_setup.get("recorded") is not True:
            raise ValueError("PaperOps qualified setup production must be recorded")
        if paperops_qualified_setup.get("event_log_written") is not True:
            raise ValueError("PaperOps qualified setup production event log missing")
        if paperops_qualified_setup.get("event_log_event_count") != 1:
            raise ValueError("PaperOps qualified setup production event count mismatch")
        if paperops_qualified_setup.get("validation_error_count") != 0:
            raise ValueError("PaperOps qualified setup production validation errors present")
    if paperops_qualified_setup.get("live_capital_enabled") is not False:
        raise ValueError("PaperOps qualified setup production enabled live capital")
    if paperops_qualified_setup.get("paper_order_submission_allowed") is not False:
        raise ValueError("PaperOps qualified setup production opened submit authority")
    if paperops_qualified_setup.get("phase7_proof_credit_allowed") is not False:
        raise ValueError("PaperOps qualified setup production granted proof credit")
    if paperops_qualified_setup.get("forced_trades_allowed") is not False:
        raise ValueError("PaperOps qualified setup production allowed forced trades")
    if paperops_qualified_setup.get("qualified_setup_creation_forced") is not False:
        raise ValueError("PaperOps qualified setup production forced a setup")
    if int(paperops_qualified_setup.get("unsafe_write_counter_total", 0) or 0) != 0:
        raise ValueError("PaperOps qualified setup production unsafe counter nonzero")
    if paperops_qualified_setup.get("status") == "production_path_ready_with_qualified_setup":
        if int(paperops_qualified_setup.get("qualified_setup_count", 0) or 0) < 1:
            raise ValueError("PaperOps qualified setup production ready without setup")
        if paperops_qualified_setup.get("ready_to_stage_q7_order") is not True:
            raise ValueError("PaperOps qualified setup production missing stage handoff")
    pt3_qualified_count = int(paperops_qualified_setup.get("qualified_setup_count", 0) or 0)
    phase7_demo_qualified_count = int(
        paperops_qualified_setup.get("phase7_demo_qualified_setup_count", 0) or 0
    )
    q7_ledger_qualified_count = int(
        paperops_qualified_setup.get("source_qualified_setup_ledger_count", 0) or 0
    )
    phase7_demo_scope = str(
        paperops_qualified_setup.get("phase7_demo_qualified_setup_count_scope") or ""
    )
    q7_ledger_scope = str(
        paperops_qualified_setup.get("source_qualified_setup_ledger_count_scope") or ""
    )
    if (
        phase7_demo_qualified_count > pt3_qualified_count
        and phase7_demo_scope != "cumulative_demo_run"
    ):
        raise ValueError(
            "PaperOps qualified setup production observed more Phase 7 demo setups "
            "than PT-3 qualified"
        )
    if (
        q7_ledger_qualified_count > pt3_qualified_count
        and q7_ledger_scope != "cumulative_runtime_ledger"
    ):
        raise ValueError(
            "PaperOps qualified setup production observed more Q7 ledger setups "
            "than PT-3 qualified"
        )
    setup_boundary = str(paperops_qualified_setup.get("boundary") or "")
    for phrase in (
        "guarded qualified setup production path",
        "cannot mutate the Q7 ledger",
        "cannot call brokers",
        "cannot grant Phase 7 proof credit",
        "cannot force trades",
        "cannot enable live capital",
    ):
        if phrase not in setup_boundary:
            raise ValueError("PaperOps qualified setup production boundary is weak")
    paperops_pt4 = payload["paperops_auto_approval_staged_order"]
    missing_pt4 = sorted(
        PAPEROPS_AUTO_APPROVAL_STAGED_ORDER_PUBLIC_REQUIRED_FIELDS
        - set(paperops_pt4)
    )
    if missing_pt4:
        raise ValueError(
            "PaperOps auto-approval staged order public status missing fields: "
            f"{missing_pt4}"
        )
    if paperops_pt4.get("status") not in {
        "not_run",
        "staged_paper_order_ready",
        "ready_no_current_auto_approved_setup",
        "blocked_pending_pt3_prerequisite",
        "invalid",
    }:
        raise ValueError("PaperOps auto-approval staged order status is invalid")
    if paperops_pt4.get("public_safe") is not True:
        raise ValueError("PaperOps auto-approval staged order must be public-safe")
    if paperops_pt4.get("status") != "not_run":
        if paperops_pt4.get("recorded") is not True:
            raise ValueError("PaperOps auto-approval staged order must be recorded")
        if paperops_pt4.get("event_log_written") is not True:
            raise ValueError("PaperOps auto-approval staged order event log missing")
        if paperops_pt4.get("event_log_event_count") != 1:
            raise ValueError("PaperOps auto-approval staged order event count mismatch")
        if paperops_pt4.get("validation_error_count") != 0:
            raise ValueError("PaperOps auto-approval staged order validation errors present")
    if paperops_pt4.get("status") == "staged_paper_order_ready":
        if int(paperops_pt4.get("staged_order_count", 0) or 0) < 1:
            raise ValueError("PaperOps auto-approval staged order ready without order")
        if paperops_pt4.get("ready_for_paperops2_submit") is not True:
            raise ValueError("PaperOps auto-approval staged order missing submit handoff")
    if paperops_pt4.get("live_capital_enabled") is not False:
        raise ValueError("PaperOps auto-approval staged order enabled live capital")
    if paperops_pt4.get("paper_order_submission_allowed") is not False:
        raise ValueError("PaperOps auto-approval staged order opened submit authority")
    if paperops_pt4.get("broker_post_allowed") is not False:
        raise ValueError("PaperOps auto-approval staged order opened broker POST authority")
    if paperops_pt4.get("live_endpoint_allowed") is not False:
        raise ValueError("PaperOps auto-approval staged order opened live endpoints")
    if paperops_pt4.get("phase7_proof_credit_allowed") is not False:
        raise ValueError("PaperOps auto-approval staged order granted proof credit")
    if paperops_pt4.get("forced_trades_allowed") is not False:
        raise ValueError("PaperOps auto-approval staged order allowed forced trades")
    for key in (
        "q7_source_ledger_mutation_performed",
        "q7_auto_approval_artifact_mutation_performed",
        "q7_staging_artifact_mutation_performed",
    ):
        if paperops_pt4.get(key) is not False:
            raise ValueError(f"PaperOps auto-approval staged order mutated Q7: {key}")
    for key in (
        "broker_post_called_count",
        "unsafe_write_counter_total",
    ):
        if int(paperops_pt4.get(key, 0) or 0) != 0:
            raise ValueError(
                f"PaperOps auto-approval staged order unsafe count nonzero: {key}"
            )
    pt4_boundary = str(paperops_pt4.get("boundary") or "")
    for phrase in (
        "guarded paper-only auto-approval",
        "cannot mutate the Q7 source ledger",
        "cannot submit paper orders",
        "cannot call brokers",
        "cannot grant Phase 7 proof credit",
        "cannot force trades",
        "cannot enable live capital",
    ):
        if phrase not in pt4_boundary:
            raise ValueError("PaperOps auto-approval staged order boundary is weak")
    paperops_submit_enablement = payload["paperops_alpaca_paper_submit_enablement"]
    missing_submit_enablement = sorted(
        PAPEROPS_ALPACA_SUBMIT_ENABLEMENT_PUBLIC_REQUIRED_FIELDS
        - set(paperops_submit_enablement)
    )
    if missing_submit_enablement:
        raise ValueError(
            "PaperOps Alpaca submit enablement public status missing fields: "
            f"{missing_submit_enablement}"
        )
    if paperops_submit_enablement.get("status") not in {
        "not_run",
        "enabled_pending_explicit_submit",
        "blocked_pending_prerequisites",
        "blocked_alpaca_paper_endpoint_or_credentials",
        "blocked_not_paper_mode",
        "blocked_live_capital_enabled",
        "invalid",
    }:
        raise ValueError("PaperOps Alpaca submit enablement status is invalid")
    if paperops_submit_enablement.get("public_safe") is not True:
        raise ValueError("PaperOps Alpaca submit enablement must be public-safe")
    if paperops_submit_enablement.get("status") != "not_run":
        if paperops_submit_enablement.get("recorded") is not True:
            raise ValueError("PaperOps Alpaca submit enablement must be recorded")
        if paperops_submit_enablement.get("event_log_written") is not True:
            raise ValueError("PaperOps Alpaca submit enablement event log missing")
        if paperops_submit_enablement.get("event_log_event_count") != 1:
            raise ValueError("PaperOps Alpaca submit enablement event count mismatch")
        if paperops_submit_enablement.get("validation_error_count") != 0:
            raise ValueError("PaperOps Alpaca submit enablement validation errors present")
    if paperops_submit_enablement.get("status") == "enabled_pending_explicit_submit":
        if paperops_submit_enablement.get("paper_submit_runtime_enablement_enabled") is not True:
            raise ValueError("PaperOps Alpaca submit enablement flag is false")
        if paperops_submit_enablement.get("alpaca_paper_submit_effective") is not True:
            raise ValueError("PaperOps Alpaca submit effective flag is false")
        if paperops_submit_enablement.get("paper_post_path_available") is not True:
            raise ValueError("PaperOps Alpaca submit path is unavailable")
        if int(paperops_submit_enablement.get("pt4_staged_order_count", 0) or 0) < 1:
            raise ValueError("PaperOps Alpaca submit enablement has no PT-4 order")
    for key in (
        "env_file_edited",
        "live_capital_enabled",
        "phase7_proof_credit_allowed",
        "forced_trades_allowed",
    ):
        if paperops_submit_enablement.get(key) is not False:
            raise ValueError(f"PaperOps Alpaca submit enablement forbidden: {key}")
    for key in (
        "broker_post_called_count",
        "alpaca_post_called_count",
        "live_endpoint_called_count",
        "unsafe_write_counter_total",
    ):
        if int(paperops_submit_enablement.get(key, 0) or 0) != 0:
            raise ValueError(
                f"PaperOps Alpaca submit enablement unsafe count nonzero: {key}"
            )
    submit_enablement_boundary = str(paperops_submit_enablement.get("boundary") or "")
    for phrase in (
        "PT-5 records runtime Alpaca paper-submit enablement",
        "explicit submit flag",
        "cannot edit .env",
        "cannot call Alpaca",
        "cannot grant Phase 7 proof credit",
        "cannot enable live capital",
    ):
        if phrase not in submit_enablement_boundary:
            raise ValueError("PaperOps Alpaca submit enablement boundary is weak")
    paperops_lifecycle_polling_enablement = payload[
        "paperops_paper_lifecycle_polling_enablement"
    ]
    missing_lifecycle_polling_enablement = sorted(
        PAPEROPS_LIFECYCLE_POLLING_ENABLEMENT_PUBLIC_REQUIRED_FIELDS
        - set(paperops_lifecycle_polling_enablement)
    )
    if missing_lifecycle_polling_enablement:
        raise ValueError(
            "PaperOps lifecycle polling enablement public status missing fields: "
            f"{missing_lifecycle_polling_enablement}"
        )
    if paperops_lifecycle_polling_enablement.get("status") not in {
        "not_run",
        "enabled_pending_submitted_paper_orders",
        "enabled_pending_explicit_poll",
        "blocked_pending_prerequisites",
        "blocked_alpaca_paper_endpoint_or_credentials",
        "blocked_not_paper_mode",
        "blocked_live_capital_enabled",
        "blocked_missing_paperops_alpaca_post_source",
        "blocked_invalid_paperops_alpaca_post_source",
        "invalid",
    }:
        raise ValueError("PaperOps lifecycle polling enablement status is invalid")
    if paperops_lifecycle_polling_enablement.get("public_safe") is not True:
        raise ValueError("PaperOps lifecycle polling enablement must be public-safe")
    if paperops_lifecycle_polling_enablement.get("status") != "not_run":
        if paperops_lifecycle_polling_enablement.get("recorded") is not True:
            raise ValueError("PaperOps lifecycle polling enablement must be recorded")
        if paperops_lifecycle_polling_enablement.get("event_log_written") is not True:
            raise ValueError("PaperOps lifecycle polling enablement event log missing")
        if paperops_lifecycle_polling_enablement.get("event_log_event_count") != 1:
            raise ValueError("PaperOps lifecycle polling enablement event count mismatch")
        if paperops_lifecycle_polling_enablement.get("validation_error_count") != 0:
            raise ValueError(
                "PaperOps lifecycle polling enablement validation errors present"
            )
    if paperops_lifecycle_polling_enablement.get("status") in {
        "enabled_pending_submitted_paper_orders",
        "enabled_pending_explicit_poll",
    }:
        if (
            paperops_lifecycle_polling_enablement.get(
                "active_lifecycle_polling_enabled"
            )
            is not True
        ):
            raise ValueError("PaperOps lifecycle polling enablement flag is false")
        if (
            paperops_lifecycle_polling_enablement.get(
                "paper_lifecycle_polling_effective"
            )
            is not True
        ):
            raise ValueError("PaperOps lifecycle polling effective flag is false")
        if paperops_lifecycle_polling_enablement.get("paper_broker_get_allowed") is not True:
            raise ValueError("PaperOps lifecycle polling GET path is not allowed")
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
            raise ValueError(
                "PaperOps lifecycle polling path is available without submitted order"
            )
    for key in (
        "env_file_edited",
        "live_capital_enabled",
        "phase7_proof_credit_allowed",
        "forced_trades_allowed",
        "broker_post_allowed",
    ):
        if paperops_lifecycle_polling_enablement.get(key) is not False:
            raise ValueError(f"PaperOps lifecycle polling enablement forbidden: {key}")
    for key in (
        "broker_get_called_count",
        "live_endpoint_called_count",
        "unsafe_write_counter_total",
    ):
        if int(paperops_lifecycle_polling_enablement.get(key, 0) or 0) != 0:
            raise ValueError(
                f"PaperOps lifecycle polling enablement unsafe count nonzero: {key}"
            )
    lifecycle_polling_boundary = str(
        paperops_lifecycle_polling_enablement.get("boundary") or ""
    )
    for phrase in (
        "PT-6 records runtime active Alpaca paper lifecycle polling enablement",
        "read-only Alpaca paper GET",
        "cannot submit orders",
        "cannot call live endpoints",
        "cannot grant Phase 7 proof credit",
        "cannot enable live capital",
    ):
        if phrase not in lifecycle_polling_boundary:
            raise ValueError("PaperOps lifecycle polling enablement boundary is weak")
    guarded_exit_enablement = payload["paperops_guarded_paper_exit_enablement"]
    missing_guarded_exit_enablement = sorted(
        PAPEROPS_GUARDED_EXIT_ENABLEMENT_PUBLIC_REQUIRED_FIELDS
        - set(guarded_exit_enablement)
    )
    if missing_guarded_exit_enablement:
        raise ValueError(
            "PaperOps guarded paper-exit enablement public status missing fields: "
            f"{missing_guarded_exit_enablement}"
        )
    if guarded_exit_enablement.get("status") not in {
        "not_run",
        "enabled_pending_open_position_readback",
        "enabled_pending_explicit_exit",
        "blocked_pending_prerequisites",
        "blocked_lifecycle_polling_enablement_not_ready",
        "blocked_alpaca_paper_endpoint_or_credentials",
        "blocked_not_paper_mode",
        "blocked_live_capital_enabled",
        "blocked_missing_paper_lifecycle_source",
        "blocked_invalid_paper_lifecycle_source",
        "invalid",
    }:
        raise ValueError("PaperOps guarded exit enablement status is invalid")
    if guarded_exit_enablement.get("public_safe") is not True:
        raise ValueError("PaperOps guarded exit enablement must be public-safe")
    if guarded_exit_enablement.get("status") != "not_run":
        if guarded_exit_enablement.get("recorded") is not True:
            raise ValueError("PaperOps guarded exit enablement must be recorded")
        if guarded_exit_enablement.get("event_log_written") is not True:
            raise ValueError("PaperOps guarded exit enablement event log missing")
        if guarded_exit_enablement.get("event_log_event_count") != 1:
            raise ValueError("PaperOps guarded exit enablement event count mismatch")
        if guarded_exit_enablement.get("validation_error_count") != 0:
            raise ValueError("PaperOps guarded exit enablement validation errors present")
    if guarded_exit_enablement.get("status") in {
        "enabled_pending_open_position_readback",
        "enabled_pending_explicit_exit",
    }:
        if guarded_exit_enablement.get("guarded_paper_exit_enabled") is not True:
            raise ValueError("PaperOps guarded exit enablement flag is false")
        if guarded_exit_enablement.get("alpaca_paper_exit_effective") is not True:
            raise ValueError("PaperOps guarded exit effective flag is false")
        if guarded_exit_enablement.get("runtime_artifact_override_enabled") is not True:
            raise ValueError("PaperOps guarded exit runtime override is false")
        if (
            int(guarded_exit_enablement.get("paperops_3_open_position_count", 0) or 0)
            == 0
            and guarded_exit_enablement.get("paper_exit_path_available") is True
        ):
            raise ValueError("PaperOps guarded exit path is available without open position")
    for key in (
        "env_file_edited",
        "live_capital_enabled",
        "phase7_proof_credit_allowed",
        "forced_trades_allowed",
        "broker_post_allowed",
        "position_close_allowed",
    ):
        if guarded_exit_enablement.get(key) is not False:
            raise ValueError(f"PaperOps guarded exit enablement forbidden: {key}")
    for key in (
        "paper_position_close_called_count",
        "live_endpoint_called_count",
        "unsafe_write_counter_total",
    ):
        if int(guarded_exit_enablement.get(key, 0) or 0) != 0:
            raise ValueError(
                f"PaperOps guarded exit enablement unsafe count nonzero: {key}"
            )
    guarded_exit_boundary = str(guarded_exit_enablement.get("boundary") or "")
    for phrase in (
        "PT-7 records runtime guarded Alpaca paper-exit enablement",
        "explicit paper-exit flag",
        "cannot call Alpaca",
        "cannot call live endpoints",
        "cannot grant Phase 7 proof credit",
        "cannot enable live capital",
    ):
        if phrase not in guarded_exit_boundary:
            raise ValueError("PaperOps guarded exit enablement boundary is weak")
    phase4_strategy = payload["phase4_strategy"]
    missing_phase4 = sorted(PHASE4_STRATEGY_PUBLIC_REQUIRED_FIELDS - set(phase4_strategy))
    if missing_phase4:
        raise ValueError(f"Phase 4 strategy public status missing fields: {missing_phase4}")
    if phase4_strategy.get("phase") != "Q4":
        raise ValueError("Phase 4 strategy status phase must be Q4")
    if phase4_strategy.get("stage") not in {"Q4-11", "Q4-12"}:
        raise ValueError("Phase 4 strategy status stage must be Q4-11 or Q4-12")
    if phase4_strategy.get("public_safe") is not True:
        raise ValueError("Phase 4 strategy status must be public-safe")
    if phase4_strategy.get("trade_candidate_count") != 0:
        raise ValueError("Phase 4 strategy status must not create trade candidates")
    if phase4_strategy.get("phase4_certification_allowed") is not False:
        approval_state = phase4_strategy.get("approval_event", {}).get("approval_state")
        approval_logged = phase4_strategy.get("approval_event", {}).get("approval_logged")
        if approval_state != "approved" or approval_logged is not True:
            raise ValueError("Phase 4 certification cannot be allowed without logged approval")
    if phase4_strategy.get("approval_event_status") != "approved":
        if phase4_strategy.get("phase4_certification_allowed") is not False:
            raise ValueError("Phase 4 certification must remain blocked before approval")
        if phase4_strategy.get("approved_shadow_strategy_toggle_count") != 0:
            raise ValueError("Phase 4 approved-shadow toggles require approval")
    strategy_toggles = phase4_strategy.get("strategy_toggles", {})
    if strategy_toggles.get("toggle_count") != phase4_strategy.get("toggle_count"):
        raise ValueError("Phase 4 strategy toggle count mismatch")
    if strategy_toggles.get("validation_error_count") != 0:
        raise ValueError("Phase 4 strategy toggles must validate")
    if phase4_strategy.get("strategy_document", {}).get("validation_error_count") != 0:
        raise ValueError("Phase 4 strategy document must validate")
    if phase4_strategy.get("approval_event", {}).get("validation_error_count") != 0:
        raise ValueError("Phase 4 approval event must validate")
    certification = phase4_strategy.get("certification", {})
    if phase4_strategy.get("stage") == "Q4-12":
        if certification.get("validation_error_count") != 0:
            raise ValueError("Phase 4 certification artifact must validate")
        if phase4_strategy.get("phase4_certified") is True:
            if phase4_strategy.get("certification_status") != "certified":
                raise ValueError("Phase 4 certification status must be certified after approval")
            if phase4_strategy.get("phase5_handoff_allowed") is not True:
                raise ValueError("Phase 5 handoff must be allowed after certification")
            if certification.get("certification_blocker_count", 0) != 0:
                raise ValueError("Phase 4 certification must not expose blockers after approval")
            if phase4_strategy.get("approved_shadow_strategy_toggle_count") != phase4_strategy.get("toggle_count"):
                raise ValueError("Phase 4 approved strategy must expose approved-shadow toggles")
        else:
            if phase4_strategy.get("certification_status") != "blocked":
                raise ValueError("Phase 4 certification status must be blocked without approval")
            if phase4_strategy.get("phase5_handoff_allowed") is not False:
                raise ValueError("Phase 5 handoff must remain blocked without approval")
            if certification.get("certification_blocker_count", 0) < 1:
                raise ValueError("Phase 4 certification must expose blockers")
            if "explicit_fund_manager_approval_required" not in certification.get(
                "certification_blockers",
                [],
            ):
                raise ValueError("Phase 4 certification must expose explicit approval blocker")
        preference_gate = certification.get("preference_mcp_certification_gate", {})
        if preference_gate.get("status") != "validated":
            raise ValueError("Phase 4 certification Preference gate must validate")
        if preference_gate.get("approved_domain_pack_count", 0) < 1:
            raise ValueError("Phase 4 certification Preference gate must expose domain packs")
        if preference_gate.get("certification_blocker_count", 0) != 0:
            raise ValueError("Phase 4 certification Preference gate must not have blockers locally")
    for key in (
        "execution_allowed_count",
        "paper_order_allowed_count",
        "broker_write_allowed_count",
        "live_capital_enabled_count",
        "live_endpoint_allowed_count",
    ):
        if phase4_strategy.get(key) != 0:
            raise ValueError(f"Phase 4 strategy status must keep {key}=0")
    for key in (
        "execution_allowed",
        "paper_order_allowed",
        "broker_write_allowed",
        "live_capital_enabled",
    ):
        if phase4_strategy.get(key) is not False:
            raise ValueError(f"Phase 4 strategy status must keep {key}=False")
    for toggle in strategy_toggles.get("toggles", []):
        if toggle.get("visible_in_cockpit") is not True:
            raise ValueError("Phase 4 strategy toggle must be visible in cockpit")
        for key in ("execution_allowed", "paper_order_allowed", "broker_write_allowed", "live_capital_enabled"):
            if toggle.get(key) is not False:
                raise ValueError(f"Phase 4 strategy toggle must keep {key}=False")
    if phase4_strategy.get("market_confirmation_policy", {}).get("yahoo_finance_role") != (
        "supplemental_market_confirmation_only"
    ):
        raise ValueError("Phase 4 Yahoo Finance policy must remain supplemental")
    if "cannot create trade candidates" not in phase4_strategy.get("no_execution_boundary", ""):
        raise ValueError("Phase 4 strategy no-execution boundary is weak")
    phase5_readiness = payload["phase5_layer_b_readiness"]
    missing_phase5 = sorted(PHASE5_LAYER_B_PUBLIC_REQUIRED_FIELDS - set(phase5_readiness))
    if missing_phase5:
        raise ValueError(f"Phase 5 readiness public status missing fields: {missing_phase5}")
    if phase5_readiness.get("phase") != "Q5" or phase5_readiness.get("layer") != "Layer B":
        raise ValueError("Phase 5 readiness phase/layer mismatch")
    if phase5_readiness.get("stage") != "P5-PRE":
        raise ValueError("Phase 5 readiness stage mismatch")
    if phase5_readiness.get("public_safe") is not True:
        raise ValueError("Phase 5 readiness must be public-safe")
    if phase5_readiness.get("phase5_layer_b_implementation_plan_allowed") is not True:
        raise ValueError("Phase 5 implementation planning should be allowed after closeout")
    phase5_implementation_allowed = (
        phase5_readiness.get("phase5_layer_b_implementation_allowed") is True
    )
    if phase5_implementation_allowed:
        if phase5_readiness.get("status") != "ready_for_phase5_layer_b_implementation":
            raise ValueError("Phase 5 readiness must be ready after Q4-12 approval")
        if phase5_readiness.get("phase4_certified") is not True:
            raise ValueError("Phase 5 readiness must see certified Phase 4")
        if phase5_readiness.get("phase5_handoff_allowed") is not True:
            raise ValueError("Phase 5 readiness must allow handoff after certification")
        if phase5_readiness.get("approval_state") != "approved":
            raise ValueError("Phase 5 readiness approval state must be approved")
        if phase5_readiness.get("readiness_blocker_count") != 0:
            raise ValueError("Phase 5 readiness must not expose blockers after approval")
    else:
        if phase5_readiness.get("status") != "blocked_pending_phase4_certification":
            raise ValueError("Phase 5 readiness must remain blocked before Q4-12 approval")
        if phase5_readiness.get("phase4_certified") is not False:
            raise ValueError("Phase 5 readiness must not see Phase 4 certified yet")
        if phase5_readiness.get("phase5_handoff_allowed") is not False:
            raise ValueError("Phase 5 readiness must not allow handoff yet")
        if "explicit_fund_manager_approval_required" not in phase5_readiness.get(
            "readiness_blockers",
            [],
        ):
            raise ValueError("Phase 5 readiness must expose explicit approval blocker")
    for key in (
        "phase5_orchestration_start_allowed",
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
            raise ValueError(f"Phase 5 readiness must keep {key}=False")
    if phase5_readiness.get("nonapproval_blocker_count") != 0:
        raise ValueError("Phase 5 readiness has non-approval blockers")
    if phase5_readiness.get("preference_source_promotion_status") != "validated":
        raise ValueError("Phase 5 readiness Preference source-promotion status invalid")
    if phase5_readiness.get("preference_source_promotion_promoted_decision_count", 0) != 0:
        raise ValueError("Phase 5 readiness cannot have promoted Preference sources")
    if phase5_readiness.get("preference_mcp_source_36") is not False:
        raise ValueError("Phase 5 readiness cannot treat Preference as source 36")
    if phase5_readiness.get("yahoo_finance_role") != "supplemental_market_confirmation_only":
        raise ValueError("Phase 5 readiness Yahoo Finance role must be supplemental")
    if "cannot start Layer B orchestration" not in phase5_readiness.get("boundary", ""):
        raise ValueError("Phase 5 readiness boundary is weak")
    phase5_kill_switch = payload["phase5_kill_switch_ledger"]
    missing_phase5_kill_switch = sorted(
        PHASE5_KILL_SWITCH_PUBLIC_REQUIRED_FIELDS - set(phase5_kill_switch)
    )
    if missing_phase5_kill_switch:
        raise ValueError(
            "Phase 5 kill-switch public status missing fields: "
            f"{missing_phase5_kill_switch}"
        )
    if phase5_kill_switch.get("phase") != "Q5" or phase5_kill_switch.get("stage") != "Q5-4":
        raise ValueError("Phase 5 kill-switch phase/stage mismatch")
    if phase5_kill_switch.get("public_safe") is not True:
        raise ValueError("Phase 5 kill-switch status must be public-safe")
    if phase5_kill_switch.get("ledger_recorded") is not True:
        raise ValueError("Phase 5 kill-switch ledger must be recorded after Q5-4")
    if phase5_kill_switch.get("status") != "ok":
        raise ValueError("Phase 5 kill-switch ledger must be ok")
    if phase5_kill_switch.get("validation_error_count") != 0:
        raise ValueError("Phase 5 kill-switch validation errors present")
    if phase5_kill_switch.get("event_log_written") is not True:
        raise ValueError("Phase 5 kill-switch ledger must write Event Log")
    if phase5_kill_switch.get("event_log_event_count") != phase5_kill_switch.get("switch_count"):
        raise ValueError("Phase 5 kill-switch Event Log count mismatch")
    if phase5_kill_switch.get("fail_closed_default_count") != phase5_kill_switch.get("switch_count"):
        raise ValueError("Phase 5 kill-switch fail-closed count mismatch")
    if phase5_kill_switch.get("active_switch_count") != phase5_kill_switch.get("blocking_switch_count"):
        raise ValueError("Phase 5 kill-switch active/blocking count mismatch")
    for key in (
        "default_fail_closed_on_missing_state",
        "default_fail_closed_on_corrupt_state",
    ):
        if phase5_kill_switch.get(key) is not True:
            raise ValueError(f"Phase 5 kill-switch {key} must be true")
    for scope_type in phase5_kill_switch.get("required_scope_types", []):
        if int(phase5_kill_switch.get("scope_counts", {}).get(scope_type, 0) or 0) < 1:
            raise ValueError(f"Phase 5 kill-switch missing scope type {scope_type}")
    for key in (
        "execution_allowed",
        "paper_order_allowed",
        "broker_write_allowed",
        "telegram_live_notifications_allowed",
        "kill_switch_mutation_authority",
        "live_capital_enabled",
    ):
        if phase5_kill_switch.get(key) is not False:
            raise ValueError(f"Phase 5 kill-switch must keep {key}=False")
    kill_switch_boundary = phase5_kill_switch.get("boundary", "")
    if "cannot" not in kill_switch_boundary or "live capital" not in kill_switch_boundary:
        raise ValueError("Phase 5 kill-switch boundary is weak")
    phase5_execution_adapter = payload["phase5_execution_adapter_status"]
    missing_phase5_execution_adapter = sorted(
        PHASE5_EXECUTION_ADAPTER_PUBLIC_REQUIRED_FIELDS - set(phase5_execution_adapter)
    )
    if missing_phase5_execution_adapter:
        raise ValueError(
            "Phase 5 execution-adapter public status missing fields: "
            f"{missing_phase5_execution_adapter}"
        )
    if (
        phase5_execution_adapter.get("phase") != "Q5"
        or phase5_execution_adapter.get("stage") != "Q5-5"
    ):
        raise ValueError("Phase 5 execution-adapter phase/stage mismatch")
    if phase5_execution_adapter.get("public_safe") is not True:
        raise ValueError("Phase 5 execution-adapter status must be public-safe")
    if phase5_execution_adapter.get("recorded") is not True:
        raise ValueError("Phase 5 execution-adapter status must be recorded after Q5-5")
    if phase5_execution_adapter.get("status") != "ok":
        raise ValueError("Phase 5 execution-adapter status must be ok")
    if phase5_execution_adapter.get("validation_error_count") != 0:
        raise ValueError("Phase 5 execution-adapter validation errors present")
    if phase5_execution_adapter.get("event_log_written") is not True:
        raise ValueError("Phase 5 execution-adapter status must write Event Log")
    if phase5_execution_adapter.get("event_log_event_count") != phase5_execution_adapter.get(
        "adapter_status_count"
    ):
        raise ValueError("Phase 5 execution-adapter Event Log count mismatch")
    if phase5_execution_adapter.get("downstream_staging_allowed_count", 0) > 1:
        raise ValueError("Phase 5 execution-adapter downstream staging count is invalid")
    if phase5_execution_adapter.get("alpaca_credentials_configured") is True:
        if phase5_execution_adapter.get("alpaca_read_health") != "read_only_available":
            raise ValueError("Phase 5 Alpaca adapter should be read-only available when configured")
        if phase5_execution_adapter.get("alpaca_account_mode") != "paper":
            raise ValueError("Phase 5 Alpaca adapter must use paper account mode")
    if phase5_execution_adapter.get("alpaca_write_health") != "blocked_q5_5_status_contract":
        raise ValueError("Phase 5 Alpaca adapter write health must be blocked")
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
            raise ValueError(f"Phase 5 execution-adapter must keep {key}=False")
    for key in (
        "secret_value_exposed_count",
        "raw_payload_exposed_count",
        "local_path_exposed_count",
    ):
        if phase5_execution_adapter.get(key) != 0:
            raise ValueError(f"Phase 5 execution-adapter exposure count nonzero: {key}")
    execution_adapter_boundary = phase5_execution_adapter.get("boundary", "")
    if "cannot" not in execution_adapter_boundary or "live capital" not in execution_adapter_boundary:
        raise ValueError("Phase 5 execution-adapter boundary is weak")
    phase5_paper_order_staging = payload["phase5_paper_order_staging_gate"]
    missing_phase5_paper_order_staging = sorted(
        PHASE5_PAPER_ORDER_STAGING_PUBLIC_REQUIRED_FIELDS - set(phase5_paper_order_staging)
    )
    if missing_phase5_paper_order_staging:
        raise ValueError(
            "Phase 5 paper-order staging public status missing fields: "
            f"{missing_phase5_paper_order_staging}"
        )
    if (
        phase5_paper_order_staging.get("phase") != "Q5"
        or phase5_paper_order_staging.get("stage") != "Q5-6"
    ):
        raise ValueError("Phase 5 paper-order staging phase/stage mismatch")
    if phase5_paper_order_staging.get("public_safe") is not True:
        raise ValueError("Phase 5 paper-order staging status must be public-safe")
    if phase5_paper_order_staging.get("recorded") is not True:
        raise ValueError("Phase 5 paper-order staging must be recorded after Q5-6")
    if phase5_paper_order_staging.get("status") != "ok":
        raise ValueError("Phase 5 paper-order staging status must be ok")
    if phase5_paper_order_staging.get("validation_error_count") != 0:
        raise ValueError("Phase 5 paper-order staging validation errors present")
    if phase5_paper_order_staging.get("event_log_written") is not True:
        raise ValueError("Phase 5 paper-order staging must write Event Log")
    if phase5_paper_order_staging.get("event_log_event_count") != phase5_paper_order_staging.get(
        "staging_record_count"
    ):
        raise ValueError("Phase 5 paper-order staging Event Log count mismatch")
    if phase5_paper_order_staging.get("staging_record_count") != phase5_paper_order_staging.get(
        "risk_review_count"
    ):
        raise ValueError("Phase 5 paper-order staging record count mismatch")
    if phase5_paper_order_staging.get("paper_size_eligible_count") == 0:
        if phase5_paper_order_staging.get("staged_order_count") != 0:
            raise ValueError("Phase 5 paper-order staging created order without eligible risk")
        if phase5_paper_order_staging.get("blocked_count") != phase5_paper_order_staging.get(
            "staging_record_count"
        ):
            raise ValueError("Phase 5 paper-order staging blocked count mismatch")
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
            raise ValueError(f"Phase 5 paper-order staging must keep {key}=False")
    for key in (
        "secret_value_exposed_count",
        "raw_payload_exposed_count",
        "local_path_exposed_count",
    ):
        if phase5_paper_order_staging.get(key) != 0:
            raise ValueError(f"Phase 5 paper-order staging exposure count nonzero: {key}")
    paper_order_staging_boundary = phase5_paper_order_staging.get("boundary", "")
    if (
        "cannot submit paper orders" not in paper_order_staging_boundary
        or "live capital" not in paper_order_staging_boundary
    ):
        raise ValueError("Phase 5 paper-order staging boundary is weak")
    phase5_alpaca_dry_run = payload["phase5_alpaca_paper_dry_run"]
    missing_phase5_alpaca_dry_run = sorted(
        PHASE5_ALPACA_PAPER_DRY_RUN_PUBLIC_REQUIRED_FIELDS - set(phase5_alpaca_dry_run)
    )
    if missing_phase5_alpaca_dry_run:
        raise ValueError(
            "Phase 5 Alpaca paper dry-run public status missing fields: "
            f"{missing_phase5_alpaca_dry_run}"
        )
    if (
        phase5_alpaca_dry_run.get("phase") != "Q5"
        or phase5_alpaca_dry_run.get("stage") != "Q5-7"
    ):
        raise ValueError("Phase 5 Alpaca paper dry-run phase/stage mismatch")
    if phase5_alpaca_dry_run.get("public_safe") is not True:
        raise ValueError("Phase 5 Alpaca paper dry-run status must be public-safe")
    if phase5_alpaca_dry_run.get("recorded") is not True:
        raise ValueError("Phase 5 Alpaca paper dry-run must be recorded after Q5-7")
    if phase5_alpaca_dry_run.get("status") != "ok":
        raise ValueError("Phase 5 Alpaca paper dry-run status must be ok")
    if phase5_alpaca_dry_run.get("validation_error_count") != 0:
        raise ValueError("Phase 5 Alpaca paper dry-run validation errors present")
    if phase5_alpaca_dry_run.get("event_log_written") is not True:
        raise ValueError("Phase 5 Alpaca paper dry-run must write Event Log")
    if phase5_alpaca_dry_run.get("event_log_event_count") != phase5_alpaca_dry_run.get(
        "dry_run_record_count"
    ):
        raise ValueError("Phase 5 Alpaca paper dry-run Event Log count mismatch")
    if phase5_alpaca_dry_run.get("dry_run_record_count") != phase5_alpaca_dry_run.get(
        "source_staging_record_count"
    ):
        raise ValueError("Phase 5 Alpaca dry-run record count mismatch")
    if phase5_alpaca_dry_run.get("source_staged_order_count") == 0:
        if phase5_alpaca_dry_run.get("request_preview_count") != 0:
            raise ValueError("Phase 5 Alpaca dry-run created request preview without staged source")
        if phase5_alpaca_dry_run.get("dry_run_receipt_count") != 0:
            raise ValueError("Phase 5 Alpaca dry-run created receipt without staged source")
        if phase5_alpaca_dry_run.get("blocked_count") != phase5_alpaca_dry_run.get(
            "dry_run_record_count"
        ):
            raise ValueError("Phase 5 Alpaca dry-run blocked count mismatch")
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
            raise ValueError(f"Phase 5 Alpaca dry-run must keep {key}=False")
    for key in (
        "secret_value_exposed_count",
        "raw_payload_exposed_count",
        "local_path_exposed_count",
        "idempotency_collision_count",
        "duplicate_guard_collision_count",
    ):
        if phase5_alpaca_dry_run.get(key) != 0:
            raise ValueError(f"Phase 5 Alpaca dry-run unsafe count nonzero: {key}")
    alpaca_dry_run_boundary = phase5_alpaca_dry_run.get("boundary", "")
    if (
        "cannot call Alpaca POST routes" not in alpaca_dry_run_boundary
        or "live capital" not in alpaca_dry_run_boundary
    ):
        raise ValueError("Phase 5 Alpaca paper dry-run boundary is weak")
    phase5_paper_submit_enablement = payload["phase5_paper_submit_enablement_gate"]
    missing_phase5_paper_submit_enablement = sorted(
        PHASE5_PAPER_SUBMIT_ENABLEMENT_PUBLIC_REQUIRED_FIELDS
        - set(phase5_paper_submit_enablement)
    )
    if missing_phase5_paper_submit_enablement:
        raise ValueError(
            "Phase 5 paper-submit enablement public status missing fields: "
            f"{missing_phase5_paper_submit_enablement}"
        )
    if (
        phase5_paper_submit_enablement.get("phase") != "Q5"
        or phase5_paper_submit_enablement.get("stage") != "Q5-8"
    ):
        raise ValueError("Phase 5 paper-submit enablement phase/stage mismatch")
    if phase5_paper_submit_enablement.get("public_safe") is not True:
        raise ValueError("Phase 5 paper-submit enablement status must be public-safe")
    if phase5_paper_submit_enablement.get("recorded") is not True:
        raise ValueError("Phase 5 paper-submit enablement must be recorded after Q5-8")
    if phase5_paper_submit_enablement.get("status") != "ok":
        raise ValueError("Phase 5 paper-submit enablement status must be ok")
    if phase5_paper_submit_enablement.get("validation_error_count") != 0:
        raise ValueError("Phase 5 paper-submit enablement validation errors present")
    if phase5_paper_submit_enablement.get("event_log_written") is not True:
        raise ValueError("Phase 5 paper-submit enablement must write Event Log")
    if phase5_paper_submit_enablement.get(
        "event_log_event_count"
    ) != phase5_paper_submit_enablement.get("submit_enablement_record_count"):
        raise ValueError("Phase 5 paper-submit enablement Event Log count mismatch")
    if phase5_paper_submit_enablement.get(
        "submit_enablement_record_count"
    ) != phase5_paper_submit_enablement.get("source_dry_run_record_count"):
        raise ValueError("Phase 5 paper-submit enablement record count mismatch")
    if phase5_paper_submit_enablement.get("paper_submit_approval_present") is False:
        if phase5_paper_submit_enablement.get("submit_path_available_count") != 0:
            raise ValueError("Phase 5 paper-submit path available without approval")
        if phase5_paper_submit_enablement.get("submit_path_available") is not False:
            raise ValueError("Phase 5 paper-submit public path flag available without approval")
        if phase5_paper_submit_enablement.get("blocked_count") != phase5_paper_submit_enablement.get(
            "submit_enablement_record_count"
        ):
            raise ValueError("Phase 5 paper-submit enablement blocked count mismatch")
    if phase5_paper_submit_enablement.get("broker_submit_receipt_created_count") != (
        phase5_paper_submit_enablement.get("paper_order_submitted_count")
    ):
        raise ValueError("Phase 5 paper-submit receipt/submitted count mismatch")
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
                raise ValueError(f"Phase 5 paper-submit enablement must keep {key}=False")
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
            raise ValueError(f"Phase 5 paper-submit enablement unsafe count nonzero: {key}")
    paper_submit_enablement_boundary = phase5_paper_submit_enablement.get("boundary", "")
    if (
        "single guarded Alpaca paper POST path" not in paper_submit_enablement_boundary
        or "cannot enable live capital" not in paper_submit_enablement_boundary
    ):
        raise ValueError("Phase 5 paper-submit enablement boundary is weak")
    phase5_prediction_market_adapter = payload["phase5_prediction_market_adapter"]
    missing_phase5_prediction_market_adapter = sorted(
        PHASE5_PREDICTION_MARKET_ADAPTER_PUBLIC_REQUIRED_FIELDS
        - set(phase5_prediction_market_adapter)
    )
    if missing_phase5_prediction_market_adapter:
        raise ValueError(
            "Phase 5 prediction-market adapter public status missing fields: "
            f"{missing_phase5_prediction_market_adapter}"
        )
    if (
        phase5_prediction_market_adapter.get("phase") != "Q5"
        or phase5_prediction_market_adapter.get("stage") != "Q5-9"
    ):
        raise ValueError("Phase 5 prediction-market adapter phase/stage mismatch")
    if phase5_prediction_market_adapter.get("public_safe") is not True:
        raise ValueError("Phase 5 prediction-market adapter status must be public-safe")
    if phase5_prediction_market_adapter.get("recorded") is not True:
        raise ValueError("Phase 5 prediction-market adapter must be recorded after Q5-9")
    if phase5_prediction_market_adapter.get("status") != "ok":
        raise ValueError("Phase 5 prediction-market adapter status must be ok")
    if phase5_prediction_market_adapter.get("validation_error_count") != 0:
        raise ValueError("Phase 5 prediction-market adapter validation errors present")
    if phase5_prediction_market_adapter.get("event_log_written") is not True:
        raise ValueError("Phase 5 prediction-market adapter must write Event Log")
    if phase5_prediction_market_adapter.get(
        "event_log_event_count"
    ) != phase5_prediction_market_adapter.get("route_count"):
        raise ValueError("Phase 5 prediction-market adapter Event Log count mismatch")
    if phase5_prediction_market_adapter.get("prediction_market_route_count") != 2:
        raise ValueError("Phase 5 prediction-market route count mismatch")
    if phase5_prediction_market_adapter.get("read_only_route_count") != 2:
        raise ValueError("Phase 5 prediction-market read-only route count mismatch")
    if phase5_prediction_market_adapter.get("prediction_market_context_count") != 2:
        raise ValueError("Phase 5 prediction-market context count mismatch")
    if phase5_prediction_market_adapter.get("policy_risk_caution_context_count") != 2:
        raise ValueError("Phase 5 prediction-market policy context count mismatch")
    if phase5_prediction_market_adapter.get("guarded_placeholder_count") != (
        phase5_prediction_market_adapter.get("route_count")
    ):
        raise ValueError("Phase 5 prediction-market placeholder count mismatch")
    if phase5_prediction_market_adapter.get("paper_not_available_count") != 2:
        raise ValueError("Phase 5 prediction-market paper-not-available count mismatch")
    if phase5_prediction_market_adapter.get("live_blocked_count") != 4:
        raise ValueError("Phase 5 prediction-market live-blocked count mismatch")
    if phase5_prediction_market_adapter.get("preference_provenance_status") != "validated":
        raise ValueError("Phase 5 prediction-market Preference provenance not validated")
    if phase5_prediction_market_adapter.get(
        "preference_context_status"
    ) != "explicit_multi_upstream_context":
        raise ValueError("Phase 5 prediction-market Preference context not multi-upstream")
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
            raise ValueError(f"Phase 5 prediction-market adapter must keep {key}=False")
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
            raise ValueError(f"Phase 5 prediction-market adapter unsafe count nonzero: {key}")
    prediction_market_boundary = phase5_prediction_market_adapter.get("boundary", "")
    if (
        "Polymarket and Kalshi context" not in prediction_market_boundary
        or "enable live capital" not in prediction_market_boundary
    ):
        raise ValueError("Phase 5 prediction-market adapter boundary is weak")

    phase5_telegram_notifier = payload["phase5_telegram_notifier"]
    missing_phase5_telegram_notifier = sorted(
        PHASE5_TELEGRAM_NOTIFIER_PUBLIC_REQUIRED_FIELDS - set(phase5_telegram_notifier)
    )
    if missing_phase5_telegram_notifier:
        raise ValueError(
            "Phase 5 Telegram notifier public status missing fields: "
            f"{missing_phase5_telegram_notifier}"
        )
    if (
        phase5_telegram_notifier.get("phase") != "Q5"
        or phase5_telegram_notifier.get("stage") != "Q5-10"
    ):
        raise ValueError("Phase 5 Telegram notifier phase/stage mismatch")
    if phase5_telegram_notifier.get("public_safe") is not True:
        raise ValueError("Phase 5 Telegram notifier status must be public-safe")
    if phase5_telegram_notifier.get("recorded") is not True:
        raise ValueError("Phase 5 Telegram notifier must be recorded after Q5-10")
    if phase5_telegram_notifier.get("status") != "ok":
        raise ValueError("Phase 5 Telegram notifier status must be ok")
    if phase5_telegram_notifier.get("validation_error_count") != 0:
        raise ValueError("Phase 5 Telegram notifier validation errors present")
    if phase5_telegram_notifier.get("event_log_written") is not True:
        raise ValueError("Phase 5 Telegram notifier must write Event Log")
    if phase5_telegram_notifier.get(
        "event_log_event_count"
    ) != phase5_telegram_notifier.get("notification_record_count"):
        raise ValueError("Phase 5 Telegram notifier Event Log count mismatch")
    if phase5_telegram_notifier.get("alert_type_count") != 9:
        raise ValueError("Phase 5 Telegram notifier alert type count mismatch")
    if phase5_telegram_notifier.get("notification_record_count") != 9:
        raise ValueError("Phase 5 Telegram notifier record count mismatch")
    if phase5_telegram_notifier.get("eligible_alert_count", 0) < 3:
        raise ValueError("Phase 5 Telegram notifier expected eligible alerts missing")
    if phase5_telegram_notifier.get("queued_dry_run_alert_count") != phase5_telegram_notifier.get(
        "eligible_alert_count"
    ):
        raise ValueError("Phase 5 Telegram notifier queued dry-run count mismatch")
    if phase5_telegram_notifier.get("outbox_message_written_count") != phase5_telegram_notifier.get(
        "eligible_alert_count"
    ):
        raise ValueError("Phase 5 Telegram notifier outbox written count mismatch")
    if phase5_telegram_notifier.get("telegram_mode") != "dry_run":
        raise ValueError("Phase 5 Telegram notifier must use dry-run mode")
    if phase5_telegram_notifier.get("telegram_send_gate") != "disabled":
        raise ValueError("Phase 5 Telegram notifier send gate must remain disabled")
    if phase5_telegram_notifier.get("private_send_test_allowed") is not False:
        raise ValueError("Phase 5 Telegram notifier private send-test gate unexpectedly allowed")
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
            raise ValueError(f"Phase 5 Telegram notifier must keep {key}=False")
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
            raise ValueError(f"Phase 5 Telegram notifier unsafe count nonzero: {key}")
    telegram_notifier_boundary = phase5_telegram_notifier.get("boundary", "")
    if (
        "cannot place, approve, reject, modify, resize, close, or cancel trades"
        not in telegram_notifier_boundary
        or "enable live capital" not in telegram_notifier_boundary
    ):
        raise ValueError("Phase 5 Telegram notifier boundary is weak")
    phase5_position_monitor = payload["phase5_position_monitor"]
    missing_phase5_position_monitor = sorted(
        PHASE5_POSITION_MONITOR_PUBLIC_REQUIRED_FIELDS - set(phase5_position_monitor)
    )
    if missing_phase5_position_monitor:
        raise ValueError(
            "Phase 5 position monitor public status missing fields: "
            f"{missing_phase5_position_monitor}"
        )
    if (
        phase5_position_monitor.get("phase") != "Q5"
        or phase5_position_monitor.get("stage") != "Q5-11"
    ):
        raise ValueError("Phase 5 position monitor phase/stage mismatch")
    if phase5_position_monitor.get("public_safe") is not True:
        raise ValueError("Phase 5 position monitor status must be public-safe")
    if phase5_position_monitor.get("recorded") is not True:
        raise ValueError("Phase 5 position monitor must be recorded after Q5-11")
    if phase5_position_monitor.get("status") != "ok":
        raise ValueError("Phase 5 position monitor status must be ok")
    if phase5_position_monitor.get("validation_error_count") != 0:
        raise ValueError("Phase 5 position monitor validation errors present")
    if phase5_position_monitor.get("event_log_written") is not True:
        raise ValueError("Phase 5 position monitor must write Event Log")
    if phase5_position_monitor.get("event_log_event_count") != phase5_position_monitor.get(
        "monitor_record_count"
    ):
        raise ValueError("Phase 5 position monitor Event Log count mismatch")
    if phase5_position_monitor.get("monitor_record_count") != (
        phase5_position_monitor.get("position_record_count")
        + phase5_position_monitor.get("closed_trade_summary_count")
    ):
        raise ValueError("Phase 5 position monitor record count mismatch")
    if phase5_position_monitor.get("lifecycle_state_count") != 9:
        raise ValueError("Phase 5 position monitor lifecycle state count mismatch")
    if phase5_position_monitor.get("failed_reconciliation_count") != 0:
        raise ValueError("Phase 5 position monitor reconciliation failures unexpectedly present")
    if phase5_position_monitor.get("postmortem_due_count", 0) > phase5_position_monitor.get(
        "closed_trade_count",
        0,
    ):
        raise ValueError("Phase 5 position monitor postmortem-due count exceeds closed trades")
    for key in (
        "position_monitor_write_authority",
        "paper_order_allowed",
        "paper_order_submitted",
        "broker_write_allowed",
        "live_capital_enabled",
    ):
        if phase5_position_monitor.get(key) is not False:
            raise ValueError(f"Phase 5 position monitor must keep {key}=False")
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
            raise ValueError(f"Phase 5 position monitor unsafe count nonzero: {key}")
    position_monitor_boundary = phase5_position_monitor.get("boundary", "")
    if (
        "cannot submit, close, resize, cancel" not in position_monitor_boundary
        or "cannot enable live capital" not in position_monitor_boundary
    ):
        raise ValueError("Phase 5 position monitor boundary is weak")
    phase5_signal_review = payload["phase5_signal_review"]
    missing_phase5_signal_review = sorted(
        PHASE5_SIGNAL_REVIEW_PUBLIC_REQUIRED_FIELDS - set(phase5_signal_review)
    )
    if missing_phase5_signal_review:
        raise ValueError(
            "Phase 5 signal review public status missing fields: "
            f"{missing_phase5_signal_review}"
        )
    if (
        phase5_signal_review.get("phase") != "Q5"
        or phase5_signal_review.get("stage") != "Q5-12"
    ):
        raise ValueError("Phase 5 signal review phase/stage mismatch")
    if phase5_signal_review.get("public_safe") is not True:
        raise ValueError("Phase 5 signal review status must be public-safe")
    if phase5_signal_review.get("recorded") is not True:
        raise ValueError("Phase 5 signal review must be recorded after Q5-12")
    if phase5_signal_review.get("status") != "ok":
        raise ValueError("Phase 5 signal review status must be ok")
    if phase5_signal_review.get("validation_error_count") != 0:
        raise ValueError("Phase 5 signal review validation errors present")
    if phase5_signal_review.get("backend_validation_error_count") != 0:
        raise ValueError("Phase 5 signal review backend validation errors present")
    if phase5_signal_review.get("pricing_gap_rollout_stage") not in {"stage_a", "stage_b"}:
        raise ValueError("Phase 5 signal review pricing-gap rollout stage invalid")
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
            raise ValueError(f"Phase 5 signal review funnel count negative: {key}")
    if phase5_signal_review.get("event_log_written") is not True:
        raise ValueError("Phase 5 signal review must write Event Log")
    expected_signal_events = (
        phase5_signal_review.get("signal_review_record_count")
        + phase5_signal_review.get("governance_comment_event_count")
        + phase5_signal_review.get("kill_switch_action_event_count")
    )
    if phase5_signal_review.get("event_log_event_count") != expected_signal_events:
        raise ValueError("Phase 5 signal review Event Log count mismatch")
    if phase5_signal_review.get("chain_step_count") != 9:
        raise ValueError("Phase 5 signal review chain step count mismatch")
    if phase5_signal_review.get("decision_chain_count") != (
        phase5_signal_review.get("signal_review_record_count") * 9
    ):
        raise ValueError("Phase 5 signal review decision-chain count mismatch")
    if phase5_signal_review.get("backend_truth_displayed_count") != phase5_signal_review.get(
        "signal_review_record_count"
    ):
        raise ValueError("Phase 5 signal review backend truth count mismatch")
    if phase5_signal_review.get("ui_inferred_readiness_count") != 0:
        raise ValueError("Phase 5 signal review inferred readiness present")
    if phase5_signal_review.get("governance_comment_event_count") != phase5_signal_review.get(
        "signal_review_record_count"
    ):
        raise ValueError("Phase 5 signal review governance comment count mismatch")
    if phase5_signal_review.get("kill_switch_action_available_count") != phase5_signal_review.get(
        "signal_review_record_count"
    ):
        raise ValueError("Phase 5 signal review kill-switch action availability mismatch")
    if phase5_signal_review.get("kill_switch_action_event_count") != phase5_signal_review.get(
        "signal_review_record_count"
    ):
        raise ValueError("Phase 5 signal review kill-switch action event count mismatch")
    for key in (
        "paper_order_allowed",
        "paper_order_submitted",
        "broker_write_allowed",
        "prediction_market_write_allowed",
        "kill_switch_mutation_authority",
        "live_capital_enabled",
    ):
        if phase5_signal_review.get(key) is not False:
            raise ValueError(f"Phase 5 signal review must keep {key}=False")
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
            raise ValueError(f"Phase 5 signal review unsafe count nonzero: {key}")
    for record in phase5_signal_review.get("records", []):
        if record.get("backend_truth_displayed") is not True:
            raise ValueError("Phase 5 signal review record is not backend truth")
        if record.get("ui_inferred_readiness") is not False:
            raise ValueError("Phase 5 signal review record inferred readiness")
        action = record.get("governance_action", {})
        if not action.get("target_artifact_id"):
            raise ValueError("Phase 5 signal review governance action missing target")
        if action.get("comment_event_log_written") is not True:
            raise ValueError("Phase 5 signal review governance comment not logged")
        if action.get("kill_switch_action_event_log_written") is not True:
            raise ValueError("Phase 5 signal review kill-switch action not logged")
        if action.get("kill_switch_mutation_authority") is not False:
            raise ValueError("Phase 5 signal review kill-switch mutation authority enabled")
    signal_review_boundary = phase5_signal_review.get("boundary", "")
    if (
        "cannot approve, reject, place, modify, resize, close, or cancel" not in signal_review_boundary
        or "cannot call brokers or venues" not in signal_review_boundary
        or "cannot enable live capital" not in signal_review_boundary
    ):
        raise ValueError("Phase 5 signal review boundary is weak")
    phase5_paper_trade_drill = payload["phase5_paper_trade_drill"]
    missing_phase5_paper_trade_drill = sorted(
        PHASE5_PAPER_TRADE_DRILL_PUBLIC_REQUIRED_FIELDS - set(phase5_paper_trade_drill)
    )
    if missing_phase5_paper_trade_drill:
        raise ValueError(
            "Phase 5 paper trade drill public status missing fields: "
            f"{missing_phase5_paper_trade_drill}"
        )
    if (
        phase5_paper_trade_drill.get("phase") != "Q5"
        or phase5_paper_trade_drill.get("stage") != "Q5-14"
    ):
        raise ValueError("Phase 5 paper trade drill phase/stage mismatch")
    if phase5_paper_trade_drill.get("public_safe") is not True:
        raise ValueError("Phase 5 paper trade drill status must be public-safe")
    if phase5_paper_trade_drill.get("recorded") is not True:
        raise ValueError("Phase 5 paper trade drill must be recorded after Q5-14")
    if phase5_paper_trade_drill.get("status") != "ok":
        raise ValueError("Phase 5 paper trade drill status must be ok")
    if phase5_paper_trade_drill.get("validation_error_count") != 0:
        raise ValueError("Phase 5 paper trade drill validation errors present")
    if phase5_paper_trade_drill.get("event_log_written") is not True:
        raise ValueError("Phase 5 paper trade drill must write Event Log")
    if phase5_paper_trade_drill.get("event_log_event_count") != phase5_paper_trade_drill.get(
        "required_step_count"
    ):
        raise ValueError("Phase 5 paper trade drill Event Log count mismatch")
    if phase5_paper_trade_drill.get("step_count") != phase5_paper_trade_drill.get(
        "required_step_count"
    ):
        raise ValueError("Phase 5 paper trade drill step count mismatch")
    if phase5_paper_trade_drill.get("required_step_count") != 13:
        raise ValueError("Phase 5 paper trade drill required step count mismatch")
    if (
        phase5_paper_trade_drill.get("phase5_paper_trade_drill_implementation_ready")
        is not True
    ):
        raise ValueError("Phase 5 paper trade drill implementation is not ready")
    if phase5_paper_trade_drill.get("phase7_proof_credit_allowed") is not False:
        raise ValueError("Phase 5 paper trade drill must not allow Phase 7 proof credit")
    if (
        phase5_paper_trade_drill.get("paper_trade_drill_complete") is True
        and phase5_paper_trade_drill.get("phase5_paper_trade_drill_exit_gate_passed") is not True
    ):
        raise ValueError("Phase 5 paper trade drill complete without exit gate")
    if (
        phase5_paper_trade_drill.get("phase5_paper_trade_drill_exit_gate_passed") is True
        and phase5_paper_trade_drill.get("paper_submit_approval_present") is not True
    ):
        raise ValueError("Phase 5 paper trade drill exit gate open without approval")
    if (
        phase5_paper_trade_drill.get("paper_submit_approval_present") is not True
        and "paper_submit_approval_missing" not in phase5_paper_trade_drill.get("blockers", [])
    ):
        raise ValueError("Phase 5 paper trade drill missing approval blocker")
    if (
        phase5_paper_trade_drill.get("paper_submit_path_available_count") == 0
        and "paper_submit_path_unavailable" not in phase5_paper_trade_drill.get("blockers", [])
    ):
        raise ValueError("Phase 5 paper trade drill missing submit-path blocker")
    if phase5_paper_trade_drill.get("paper_trade_drill_complete") is True:
        for key in (
            "submitted_paper_order_count",
            "closed_trade_count",
            "postmortem_due_count",
        ):
            if phase5_paper_trade_drill.get(key, 0) <= 0:
                raise ValueError(f"Phase 5 paper trade drill complete without {key}")
        if phase5_paper_trade_drill.get("position_open_lifecycle_satisfied") is not True:
            raise ValueError("Phase 5 paper trade drill complete without open-position lifecycle")
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
        "phase7_proof_credit_allowed_count",
        "secret_value_exposed_count",
        "raw_payload_exposed_count",
        "local_path_exposed_count",
        "authorization_header_exposed_count",
        "broker_order_identifier_exposed_count",
    ):
        if phase5_paper_trade_drill.get(key) != 0:
            raise ValueError(f"Phase 5 paper trade drill unsafe count nonzero: {key}")
    if (
        phase5_paper_trade_drill.get("broker_post_called_count") != 0
        and phase5_paper_trade_drill.get("phase5_paper_trade_drill_exit_gate_passed")
        is not True
    ):
        raise ValueError("Phase 5 paper trade drill broker POST before exit gate")
    if (
        phase5_paper_trade_drill.get("alpaca_post_called_count") != 0
        and phase5_paper_trade_drill.get("phase5_paper_trade_drill_exit_gate_passed")
        is not True
    ):
        raise ValueError("Phase 5 paper trade drill Alpaca POST before exit gate")
    for record in phase5_paper_trade_drill.get("records", []):
        if record.get("display_status") != record.get("backend_status"):
            raise ValueError("Phase 5 paper trade drill record display/backend mismatch")
        if record.get("display_derived_from_backend") is not True:
            raise ValueError("Phase 5 paper trade drill record not backend-derived")
        if record.get("ui_inferred_readiness") is not False:
            raise ValueError("Phase 5 paper trade drill record inferred readiness")
        for key in (
            "broker_post_called",
            "broker_write_allowed",
            "live_capital_enabled",
            "phase7_proof_credit_allowed",
        ):
            if record.get(key) is not False:
                raise ValueError(f"Phase 5 paper trade drill record unsafe flag: {key}")
    paper_trade_drill_boundary = phase5_paper_trade_drill.get("boundary", "")
    if (
        "cannot bypass explicit paper-submit approval" not in paper_trade_drill_boundary
        or "cannot call brokers or venues" not in paper_trade_drill_boundary
        or "cannot enable live capital" not in paper_trade_drill_boundary
        or "cannot count toward Phase 7 proof" not in paper_trade_drill_boundary
    ):
        raise ValueError("Phase 5 paper trade drill boundary is weak")
    phase5_certification = payload["phase5_certification"]
    missing_phase5_certification = sorted(
        PHASE5_CERTIFICATION_PUBLIC_REQUIRED_FIELDS - set(phase5_certification)
    )
    if missing_phase5_certification:
        raise ValueError(
            "Phase 5 certification public status missing fields: "
            f"{missing_phase5_certification}"
        )
    if (
        phase5_certification.get("phase") != "Q5"
        or phase5_certification.get("stage") != "Q5-15"
    ):
        raise ValueError("Phase 5 certification phase/stage mismatch")
    if phase5_certification.get("public_safe") is not True:
        raise ValueError("Phase 5 certification status must be public-safe")
    if phase5_certification.get("recorded") is not True:
        raise ValueError("Phase 5 certification must be recorded after Q5-15")
    if phase5_certification.get("status") not in {"blocked", "eligible"}:
        raise ValueError("Phase 5 certification status must be blocked or eligible")
    if phase5_certification.get("validation_error_count") != 0:
        raise ValueError("Phase 5 certification validation errors present")
    if phase5_certification.get("event_log_written") is not True:
        raise ValueError("Phase 5 certification must write Event Log")
    if phase5_certification.get("event_log_event_count") != 1:
        raise ValueError("Phase 5 certification Event Log count mismatch")
    if phase5_certification.get("q5_stage_count") != 16:
        raise ValueError("Phase 5 certification Q5 stage count mismatch")
    if phase5_certification.get("required_input_stage_count") != 15:
        raise ValueError("Phase 5 certification input stage count mismatch")
    if phase5_certification.get("input_gate_count") != 15:
        raise ValueError("Phase 5 certification gate count mismatch")
    if phase5_certification.get("input_gate_blocked_count") != (
        phase5_certification.get("input_gate_count", 0)
        - phase5_certification.get("input_gate_passed_count", 0)
    ):
        raise ValueError("Phase 5 certification blocked gate count mismatch")
    if phase5_certification.get("phase7_proof_credit_allowed") is not False:
        raise ValueError("Phase 5 certification must not grant Phase 7 proof credit")
    if phase5_certification.get("phase7_proof_credit_allowed_count") != 0:
        raise ValueError("Phase 5 certification proof credit count must be zero")
    if phase5_certification.get("blocking_unsafe_count") != 0:
        raise ValueError("Phase 5 certification unsafe blocking count nonzero")
    for key in (
        "broker_write_allowed_count",
        "prediction_market_write_allowed_count",
        "crypto_perps_write_allowed_count",
        "telegram_live_notifications_allowed_count",
        "live_endpoint_allowed_count",
        "live_capital_enabled_count",
    ):
        if phase5_certification.get(key) != 0:
            raise ValueError(f"Phase 5 certification unsafe count nonzero: {key}")
    if phase5_certification.get("phase5_certified") is True:
        if phase5_certification.get("status") != "eligible":
            raise ValueError("Phase 5 certification certified with non-eligible status")
        for key in (
            "phase5_complete",
            "phase5_exit_gate",
            "phase6_handoff_allowed",
            "phase7_planning_allowed",
            "paper_trade_drill_complete",
            "paper_trade_drill_exit_gate_passed",
        ):
            if phase5_certification.get(key) is not True:
                raise ValueError(f"Phase 5 certification missing true flag: {key}")
        for key in (
            "submitted_paper_order_count",
            "open_position_count",
            "closed_trade_count",
            "postmortem_due_count",
        ):
            if phase5_certification.get(key, 0) <= 0:
                raise ValueError(f"Phase 5 certification missing count: {key}")
    else:
        if phase5_certification.get("status") != "blocked":
            raise ValueError("Phase 5 certification blocked state has wrong status")
        if phase5_certification.get("phase5_exit_gate") is not False:
            raise ValueError("Phase 5 certification exit gate opened while blocked")
        if phase5_certification.get("phase6_handoff_allowed") is not False:
            raise ValueError("Phase 5 certification Phase 6 handoff opened while blocked")
        if phase5_certification.get("phase7_planning_allowed") is not False:
            raise ValueError("Phase 5 certification Phase 7 planning opened while blocked")
        if phase5_certification.get("certification_blocker_count", 0) < 1:
            raise ValueError("Phase 5 certification blocked without blockers")
        if (
            phase5_certification.get("paper_trade_drill_exit_gate_passed") is not True
            and "q5_14_exit_gate_not_passed"
            not in phase5_certification.get("certification_blockers", [])
        ):
            raise ValueError("Phase 5 certification missing Q5-14 exit blocker")
    for record in phase5_certification.get("gate_records", []):
        if record.get("display_status") != record.get("backend_status"):
            raise ValueError("Phase 5 certification gate display/backend mismatch")
        if record.get("display_derived_from_backend") is not True:
            raise ValueError("Phase 5 certification gate not backend-derived")
        if record.get("ui_inferred_readiness") is not False:
            raise ValueError("Phase 5 certification gate inferred readiness")
        if record.get("phase7_proof_credit_allowed") is not False:
            raise ValueError("Phase 5 certification gate grants proof credit")
    certification_boundary = phase5_certification.get("boundary", "")
    if (
        "cannot bypass Q5-14" not in certification_boundary
        or "cannot call live endpoints" not in certification_boundary
        or "cannot enable live capital" not in certification_boundary
        or "cannot let Phase 5 test trades count toward Phase 7 proof"
        not in certification_boundary
    ):
        raise ValueError("Phase 5 certification boundary is weak")
    phase5_phase6_handoff = payload["phase5_phase6_handoff"]
    missing_phase5_phase6_handoff = sorted(
        PHASE5_PHASE6_HANDOFF_PUBLIC_REQUIRED_FIELDS - set(phase5_phase6_handoff)
    )
    if missing_phase5_phase6_handoff:
        raise ValueError(
            "Phase 5 to Phase 6 handoff public status missing fields: "
            f"{missing_phase5_phase6_handoff}"
        )
    if (
        phase5_phase6_handoff.get("phase") != "Q5"
        or phase5_phase6_handoff.get("stage") != "Q5E-10"
    ):
        raise ValueError("Phase 5 to Phase 6 handoff phase/stage mismatch")
    if phase5_phase6_handoff.get("public_safe") is not True:
        raise ValueError("Phase 5 to Phase 6 handoff must be public-safe")
    if phase5_phase6_handoff.get("recorded") is not True:
        raise ValueError("Phase 5 to Phase 6 handoff must be recorded after Q5E-10")
    if phase5_phase6_handoff.get("status") not in {"eligible", "blocked"}:
        raise ValueError("Phase 5 to Phase 6 handoff status is invalid")
    if phase5_phase6_handoff.get("validation_error_count") != 0:
        raise ValueError("Phase 5 to Phase 6 handoff validation errors present")
    if phase5_phase6_handoff.get("event_log_written") is not True:
        raise ValueError("Phase 5 to Phase 6 handoff must write Event Log")
    if phase5_phase6_handoff.get("event_log_event_count") != 1:
        raise ValueError("Phase 5 to Phase 6 handoff Event Log count mismatch")
    if phase5_phase6_handoff.get("phase7_proof_credit_allowed") is not False:
        raise ValueError("Phase 5 to Phase 6 handoff must not grant Phase 7 proof credit")
    if phase5_phase6_handoff.get("phase5_test_trades_count_for_phase7") is not False:
        raise ValueError("Phase 5 to Phase 6 handoff must not count test trades for Phase 7")
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
            raise ValueError(f"Phase 5 to Phase 6 handoff unsafe count nonzero: {key}")
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
            raise ValueError(f"Phase 6 authority enabled before Q6-0: {key}")
    if phase5_phase6_handoff.get("phase6_learning_loop_plan_allowed") is True:
        if phase5_phase6_handoff.get("status") != "eligible":
            raise ValueError("Phase 6 plan is allowed without eligible handoff")
        if phase5_phase6_handoff.get("handoff_state") != "phase6_learning_loop_plan_ready":
            raise ValueError("Phase 6 handoff state mismatch")
        if phase5_phase6_handoff.get("blocker_count") != 0:
            raise ValueError("Phase 6 handoff has blockers")
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
                raise ValueError(f"Phase 6 handoff missing true flag: {key}")
        if phase5_phase6_handoff.get("paper_trade_drill_blocker_count") != 0:
            raise ValueError("Phase 6 handoff has paper trade drill blockers")
        for key in (
            "downstream_staging_allowed_count",
            "submitted_order_count",
            "mirrored_order_count",
            "closed_trade_count",
            "postmortem_due_count",
        ):
            if phase5_phase6_handoff.get(key, 0) <= 0:
                raise ValueError(f"Phase 6 handoff missing count: {key}")
        if phase5_phase6_handoff.get("failed_reconciliation_count") != 0:
            raise ValueError("Phase 6 handoff has reconciliation failures")
        if phase5_phase6_handoff.get("source_validation_error_count") != 0:
            raise ValueError("Phase 6 handoff source validation errors present")
        if phase5_phase6_handoff.get("source_recorded_count") != phase5_phase6_handoff.get(
            "required_source_count"
        ):
            raise ValueError("Phase 6 handoff source coverage mismatch")
    else:
        if phase5_phase6_handoff.get("status") != "blocked":
            raise ValueError("Phase 6 handoff blocked state has wrong status")
        if phase5_phase6_handoff.get("blocker_count", 0) < 1:
            raise ValueError("Phase 6 handoff blocked without blockers")
    if phase5_phase6_handoff.get("phase6_required_module_count") != len(
        phase5_phase6_handoff.get("phase6_required_modules", [])
    ):
        raise ValueError("Phase 6 required module count mismatch")
    handoff_boundary = phase5_phase6_handoff.get("boundary", "")
    if (
        "cannot implement Phase 6" not in handoff_boundary
        or "cannot write learning data" not in handoff_boundary
        or "cannot call broker POST routes" not in handoff_boundary
        or "cannot enable live capital" not in handoff_boundary
        or "cannot count Phase 5 test trades toward Phase 7 proof"
        not in handoff_boundary
    ):
        raise ValueError("Phase 5 to Phase 6 handoff boundary is weak")
    phase6_learning_loop = payload["phase6_learning_loop"]
    missing_phase6_learning_loop = sorted(
        PHASE6_LEARNING_LOOP_PUBLIC_REQUIRED_FIELDS - set(phase6_learning_loop)
    )
    if missing_phase6_learning_loop:
        raise ValueError(
            "Phase 6 Learning Loop public status missing fields: "
            f"{missing_phase6_learning_loop}"
        )
    if (
        phase6_learning_loop.get("phase") != "Q6"
        or phase6_learning_loop.get("stage") != "Q6-16"
    ):
        raise ValueError("Phase 6 Learning Loop phase/stage mismatch")
    if phase6_learning_loop.get("public_safe") is not True:
        raise ValueError("Phase 6 Learning Loop status must be public-safe")
    if phase6_learning_loop.get("recorded") is not True:
        raise ValueError("Phase 6 Learning Loop visibility must be recorded after Q6-16")
    if phase6_learning_loop.get("status") not in {"visible", "blocked"}:
        raise ValueError("Phase 6 Learning Loop status is invalid")
    if phase6_learning_loop.get("validation_error_count") != 0:
        raise ValueError("Phase 6 Learning Loop validation errors present")
    if phase6_learning_loop.get("event_log_written") is not True:
        raise ValueError("Phase 6 Learning Loop must write Event Log")
    if phase6_learning_loop.get("event_log_event_count") != 1:
        raise ValueError("Phase 6 Learning Loop Event Log count mismatch")
    if phase6_learning_loop.get("backend_derived") is not True:
        raise ValueError("Phase 6 Learning Loop visibility is not backend-derived")
    if phase6_learning_loop.get("display_derived_from_backend") is not True:
        raise ValueError("Phase 6 Learning Loop display is not backend-derived")
    if phase6_learning_loop.get("dashboard_uses_backend_status") is not True:
        raise ValueError("Phase 6 Learning Loop dashboard is not backend-derived")
    if phase6_learning_loop.get("ui_inferred_readiness_count") != 0:
        raise ValueError("Phase 6 Learning Loop UI inferred readiness present")
    if phase6_learning_loop.get("backend_parity_error_count") != 0:
        raise ValueError("Phase 6 Learning Loop backend parity errors present")
    if not str(phase6_learning_loop.get("visibility_state", "")).startswith(
        "backend_derived_"
    ):
        raise ValueError("Phase 6 Learning Loop visibility state is not backend-derived")
    if phase6_learning_loop.get("learning_state") not in {
        "blocked_pending_learning_approval",
        "approved_learning_visible",
        "deferred_learning_visible",
        "rejected_learning_visible",
    }:
        raise ValueError("Phase 6 Learning Loop learning state is invalid")
    if phase6_learning_loop.get("source_missing_count") != 0:
        raise ValueError("Phase 6 Learning Loop source artifacts missing")
    if phase6_learning_loop.get("source_validation_error_count") != 0:
        raise ValueError("Phase 6 Learning Loop source validation errors present")
    if phase6_learning_loop.get("source_artifact_count") != len(
        phase6_learning_loop.get("source_status_records", [])
    ):
        raise ValueError("Phase 6 Learning Loop source status count mismatch")
    for record in phase6_learning_loop.get("source_status_records", []):
        if record.get("display_status") != record.get("backend_status"):
            raise ValueError("Phase 6 Learning Loop source display/backend mismatch")
        if record.get("display_derived_from_backend") is not True:
            raise ValueError("Phase 6 Learning Loop source display is not backend-derived")
        if record.get("ui_inferred_readiness") is not False:
            raise ValueError("Phase 6 Learning Loop source UI inferred readiness present")
        source_ref = str(record.get("source_ref", ""))
        if not source_ref.startswith("data/runtime/"):
            raise ValueError("Phase 6 Learning Loop source ref must be public-safe relative")
        if (
            source_ref.startswith("/")
            or source_ref.startswith("~")
            or (len(source_ref) > 2 and source_ref[1:3] == ":\\")
        ):
            raise ValueError("Phase 6 Learning Loop source ref exposes local path")
    if phase6_learning_loop.get("postmortem_due_count", 0) < 1:
        raise ValueError("Phase 6 Learning Loop missing postmortem due count")
    if phase6_learning_loop.get("postmortem_resolved_count", 0) > phase6_learning_loop.get(
        "postmortem_due_count",
        0,
    ):
        raise ValueError("Phase 6 Learning Loop postmortem count mismatch")
    if (
        phase6_learning_loop.get("approval_state") != "approved"
        and phase6_learning_loop.get("postmortem_resolved_count") != 0
    ):
        raise ValueError("Phase 6 Learning Loop resolved postmortem without approval")
    if phase6_learning_loop.get("staged_graph_entry_count") != 0:
        raise ValueError("Phase 6 Learning Loop staged graph entries present before approval")
    for key in (
        "knowledge_graph_read_result_count",
        "model_weight_proposal_count",
        "trust_score_proposal_count",
        "shadow_replay_variant_count",
        "architect_recommendation_count",
    ):
        if phase6_learning_loop.get(key, 0) < 1:
            raise ValueError(f"Phase 6 Learning Loop missing count: {key}")
    for key in (
        "phase6_learning_write_allowed",
        "phase6_knowledge_graph_write_allowed",
        "phase6_model_weight_update_allowed",
        "phase6_trust_score_update_allowed",
        "phase6_shadow_strategy_runner_allowed",
        "phase6_architect_policy_mutation_allowed",
        "phase6_policy_mutation_allowed",
        "phase7_proof_credit_allowed",
        "broker_write_allowed",
        "prediction_market_write_allowed",
        "live_capital_enabled",
    ):
        if phase6_learning_loop.get(key) is not False:
            raise ValueError(f"Phase 6 Learning Loop authority enabled: {key}")
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
        "unsafe_write_counter_total",
        "raw_payload_exposed_count",
        "private_payload_exposed_count",
        "local_path_exposed_count",
        "secret_ref_exposed_count",
        "broker_identifier_exposed_count",
    ):
        if phase6_learning_loop.get(key) != 0:
            raise ValueError(f"Phase 6 Learning Loop unsafe or exposure count nonzero: {key}")
    phase6_boundary = phase6_learning_loop.get("boundary", "")
    if (
        "cannot infer readiness from the UI" not in phase6_boundary
        or "cannot expose raw payloads" not in phase6_boundary
        or "cannot write learning data" not in phase6_boundary
        or "cannot apply model weights" not in phase6_boundary
        or "cannot apply trust scores" not in phase6_boundary
        or "cannot mutate policy" not in phase6_boundary
        or "cannot call broker POST routes" not in phase6_boundary
        or "cannot enable live capital" not in phase6_boundary
        or "cannot grant Phase 7 proof credit" not in phase6_boundary
    ):
        raise ValueError("Phase 6 Learning Loop boundary is weak")
    rs9_learning_loop = payload["rs9_learning_loop"]
    missing_rs9_learning_loop = sorted(
        set(RS9_LEARNING_LOOP_PUBLIC_FIELDS) - set(rs9_learning_loop)
    )
    if missing_rs9_learning_loop:
        raise ValueError(
            "RS-9 Learning Loop public status missing fields: "
            f"{missing_rs9_learning_loop}"
        )
    if (
        rs9_learning_loop.get("phase") != "RS"
        or rs9_learning_loop.get("stage") != "RS-9"
    ):
        raise ValueError("RS-9 Learning Loop phase/stage mismatch")
    if rs9_learning_loop.get("public_safe") is not True:
        raise ValueError("RS-9 Learning Loop must be public-safe")
    if rs9_learning_loop.get("recorded") is not True:
        raise ValueError("RS-9 Learning Loop must be recorded")
    if rs9_learning_loop.get("status") not in {"review_ready", "blocked"}:
        raise ValueError("RS-9 Learning Loop status is invalid")
    if rs9_learning_loop.get("validation_error_count") != 0:
        raise ValueError("RS-9 Learning Loop validation errors present")
    if rs9_learning_loop.get("event_log_written") is not True:
        raise ValueError("RS-9 Learning Loop Event Log missing")
    if rs9_learning_loop.get("event_log_event_count") != 1:
        raise ValueError("RS-9 Learning Loop Event Log count mismatch")
    if rs9_learning_loop.get("learning_direction") not in {
        "improving",
        "degrading",
        "uncertain",
    }:
        raise ValueError("RS-9 Learning Loop direction invalid")
    if (
        rs9_learning_loop.get("full_potential_state")
        != "learning_visible_but_mutation_locked"
    ):
        raise ValueError("RS-9 Learning Loop full-potential state invalid")
    if rs9_learning_loop.get("paperops_guarded_paper_trading_not_blocked") is not True:
        raise ValueError("RS-9 Learning Loop must not block guarded PaperOps trading")
    if rs9_learning_loop.get("source_missing_count") != 0:
        raise ValueError("RS-9 Learning Loop source artifacts missing")
    if rs9_learning_loop.get("source_validation_error_count") != 0:
        raise ValueError("RS-9 Learning Loop source validation errors present")
    if rs9_learning_loop.get("source_artifact_count") != len(
        rs9_learning_loop.get("source_status_records", [])
    ):
        raise ValueError("RS-9 Learning Loop source count mismatch")
    for record in rs9_learning_loop.get("source_status_records", []):
        source_ref = str(record.get("source_ref", ""))
        if not source_ref.startswith("data/runtime/"):
            raise ValueError("RS-9 Learning Loop source ref must be relative")
        if (
            source_ref.startswith("/")
            or source_ref.startswith("~")
            or (len(source_ref) > 2 and source_ref[1:3] == ":\\")
        ):
            raise ValueError("RS-9 Learning Loop source ref exposes local path")
    if rs9_learning_loop.get("proposal_count") != len(
        rs9_learning_loop.get("learning_proposals", [])
    ):
        raise ValueError("RS-9 Learning Loop proposal count mismatch")
    if rs9_learning_loop.get("proposal_count") < 5:
        raise ValueError("RS-9 Learning Loop must expose five proposal surfaces")
    if rs9_learning_loop.get("active_proposal_count") != 0:
        raise ValueError("RS-9 Learning Loop must not expose active proposals")
    if rs9_learning_loop.get("blocked_proposal_count") != rs9_learning_loop.get(
        "proposal_count"
    ):
        raise ValueError("RS-9 Learning Loop proposals must remain blocked pending review")
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
        raise ValueError("RS-9 Learning Loop proposal surfaces mismatch")
    for proposal in rs9_learning_loop.get("learning_proposals", []):
        if proposal.get("approval_required") is not True:
            raise ValueError("RS-9 Learning Loop proposal missing approval gate")
        if proposal.get("apply_allowed") is not False:
            raise ValueError("RS-9 Learning Loop proposal can apply")
        if proposal.get("mutation_allowed") is not False:
            raise ValueError("RS-9 Learning Loop proposal can mutate")
        for ref in proposal.get("source_refs", []):
            if not isinstance(ref, str) or not ref.startswith("data/runtime/"):
                raise ValueError("RS-9 Learning Loop proposal source ref invalid")
            if (
                ref.startswith("/")
                or ref.startswith("~")
                or (len(ref) > 2 and ref[1:3] == ":\\")
            ):
                raise ValueError("RS-9 Learning Loop proposal source ref exposes local path")
    for key in (
        "strategy_weight_proposal_count",
        "source_trust_proposal_count",
        "risk_sizing_proposal_count",
        "market_context_proposal_count",
        "worldview_lens_proposal_count",
    ):
        if rs9_learning_loop.get(key) != 1:
            raise ValueError(f"RS-9 Learning Loop surface count invalid: {key}")
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
            raise ValueError(f"RS-9 Learning Loop authority enabled: {key}")
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
            raise ValueError(f"RS-9 Learning Loop unsafe or exposure count nonzero: {key}")
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
        raise ValueError("RS-9 Learning Loop boundary is weak")
    mission_rs9 = payload["mission_control"].get("rs9_learning_loop", {})
    if mission_rs9.get("status") != rs9_learning_loop.get("status"):
        raise ValueError("Mission Control RS-9 status mismatch")
    if mission_rs9.get("learning_direction") != rs9_learning_loop.get("learning_direction"):
        raise ValueError("Mission Control RS-9 direction mismatch")
    if mission_rs9.get("proposal_count") != rs9_learning_loop.get("proposal_count"):
        raise ValueError("Mission Control RS-9 proposal count mismatch")
    rs10_final_paper_autonomy = payload["rs10_final_paper_autonomy_certification"]
    missing_rs10_final_paper_autonomy = sorted(
        set(RS10_FINAL_PAPER_AUTONOMY_PUBLIC_FIELDS)
        - set(rs10_final_paper_autonomy)
    )
    if missing_rs10_final_paper_autonomy:
        raise ValueError(
            "RS-10 Final Paper Autonomy public status missing fields: "
            f"{missing_rs10_final_paper_autonomy}"
        )
    if (
        rs10_final_paper_autonomy.get("phase") != "RS"
        or rs10_final_paper_autonomy.get("stage") != "RS-10"
    ):
        raise ValueError("RS-10 Final Paper Autonomy phase/stage mismatch")
    if rs10_final_paper_autonomy.get("public_safe") is not True:
        raise ValueError("RS-10 Final Paper Autonomy must be public-safe")
    if rs10_final_paper_autonomy.get("recorded") is not True:
        raise ValueError("RS-10 Final Paper Autonomy must be recorded")
    if rs10_final_paper_autonomy.get("event_log_written") is not True:
        raise ValueError("RS-10 Final Paper Autonomy Event Log missing")
    if rs10_final_paper_autonomy.get("event_log_event_count") != 1:
        raise ValueError("RS-10 Final Paper Autonomy Event Log count mismatch")
    if validate_rs10_final_paper_autonomy_certification(
        rs10_final_paper_autonomy
    ):
        raise ValueError("RS-10 Final Paper Autonomy validation failed")
    if rs10_final_paper_autonomy.get("final_paper_autonomy_certified") is not True:
        raise ValueError("RS-10 Final Paper Autonomy is not certified")
    if rs10_final_paper_autonomy.get("guarded_paper_autonomy_allowed") is not True:
        raise ValueError("RS-10 guarded paper autonomy is not allowed")
    if (
        rs10_final_paper_autonomy.get(
            "multiple_paper_trades_per_day_allowed_when_gates_pass"
        )
        is not True
    ):
        raise ValueError("RS-10 multiple paper trades policy is not enabled")
    if rs10_final_paper_autonomy.get("certification_blocker_count") != 0:
        raise ValueError("RS-10 certification blockers present")
    if rs10_final_paper_autonomy.get("safety_blocker_count") != 0:
        raise ValueError("RS-10 safety blockers present")
    if rs10_final_paper_autonomy.get("stale_blocker_in_current_count") != 0:
        raise ValueError("RS-10 stale blocker is shown as current")
    for key in (
        "dashboard_command_authority",
        "telegram_command_authority",
        "local_llm_execution_authority",
        "frontier_llm_execution_authority",
        "quantum_execution_authority",
        "unmanaged_broker_write_allowed",
        "broker_post_allowed",
        "alpaca_post_allowed",
        "live_capital_enabled",
        "phase7_proof_credit_allowed",
    ):
        if rs10_final_paper_autonomy.get(key) is not False:
            raise ValueError(f"RS-10 authority enabled: {key}")
    for key in (
        "live_endpoint_called_count",
        "broker_post_called_count",
        "alpaca_post_called_count",
        "broker_write_allowed_count",
        "telegram_command_path_enabled_count",
        "unsafe_write_counter_total",
        "raw_payload_exposed_count",
        "private_payload_exposed_count",
        "local_path_exposed_count",
        "secret_ref_exposed_count",
        "broker_identifier_exposed_count",
    ):
        if rs10_final_paper_autonomy.get(key) != 0:
            raise ValueError(f"RS-10 unsafe or exposure count nonzero: {key}")
    if (
        rs10_final_paper_autonomy.get("paper_submit_currently_allowed") is True
        and paper_authority.get("paper_submit_currently_allowed") is not True
    ):
        raise ValueError("RS-10 invented paper submit authority")
    mission_rs10 = payload["mission_control"].get(
        "rs10_final_paper_autonomy_certification",
        {},
    )
    if mission_rs10.get("status") != rs10_final_paper_autonomy.get("status"):
        raise ValueError("Mission Control RS-10 status mismatch")
    if mission_rs10.get("final_paper_autonomy_certified") != (
        rs10_final_paper_autonomy.get("final_paper_autonomy_certified")
    ):
        raise ValueError("Mission Control RS-10 certification mismatch")
    phase6_certification = payload["phase6_certification"]
    missing_phase6_certification = sorted(
        PHASE6_CERTIFICATION_PUBLIC_REQUIRED_FIELDS - set(phase6_certification)
    )
    if missing_phase6_certification:
        raise ValueError(
            "Phase 6 certification public status missing fields: "
            f"{missing_phase6_certification}"
        )
    if (
        phase6_certification.get("phase") != "Q6"
        or phase6_certification.get("stage") != "Q6-17"
    ):
        raise ValueError("Phase 6 certification phase/stage mismatch")
    if phase6_certification.get("public_safe") is not True:
        raise ValueError("Phase 6 certification status must be public-safe")
    if phase6_certification.get("recorded") is not True:
        raise ValueError("Phase 6 certification must be recorded after Q6-17")
    if phase6_certification.get("validation_error_count") != 0:
        raise ValueError("Phase 6 certification validation errors present")
    if phase6_certification.get("event_log_written") is not True:
        raise ValueError("Phase 6 certification must write Event Log")
    if phase6_certification.get("event_log_event_count") != 1:
        raise ValueError("Phase 6 certification Event Log count mismatch")
    if phase6_certification.get("input_gate_count") != 17:
        raise ValueError("Phase 6 certification input gate count mismatch")
    if phase6_certification.get("input_gate_passed_count") != 17:
        raise ValueError("Phase 6 certification input gates are not all implemented")
    if phase6_certification.get("input_gate_blocked_count") != 0:
        raise ValueError("Phase 6 certification input gates are blocked")
    if phase6_certification.get("phase6_certified") is True:
        if phase6_certification.get("status") != "certified":
            raise ValueError("Phase 6 certification status mismatch")
        if phase6_certification.get("phase6_exit_gate") is not True:
            raise ValueError("Phase 6 exit gate not open after certification")
        if phase6_certification.get("phase7_demo_proof_planning_allowed") is not True:
            raise ValueError("Phase 7 demo-proof planning not allowed after certification")
        if phase6_certification.get("certification_blocker_count") != 0:
            raise ValueError("Phase 6 certified with blockers")
    else:
        if phase6_certification.get("status") != "blocked":
            raise ValueError("Phase 6 uncertified status must be blocked")
        if phase6_certification.get("phase6_exit_gate") is not False:
            raise ValueError("Phase 6 exit gate opened while uncertified")
        if phase6_certification.get("phase7_demo_proof_planning_allowed") is not False:
            raise ValueError("Phase 7 demo-proof planning allowed while Phase 6 blocked")
        if phase6_certification.get("certification_blocker_count", 0) < 1:
            raise ValueError("Phase 6 blocked certification lacks blockers")
    if phase6_certification.get("approval_state") == "pending_review":
        for blocker in (
            "learning_approval_pending_review",
            "postmortem_review_coverage_incomplete",
            "learning_actions_not_approved_or_deferred",
            "knowledge_graph_entries_or_proposals_not_certifiable",
        ):
            if blocker not in phase6_certification.get("certification_blockers", []):
                raise ValueError(f"Phase 6 certification missing blocker: {blocker}")
    if phase6_certification.get("phase7_proof_credit_allowed") is not False:
        raise ValueError("Phase 6 certification grants Phase 7 proof credit")
    if phase6_certification.get("phase5_test_trades_count_for_phase7") is not False:
        raise ValueError("Phase 6 certification counts Phase 5 test trades for Phase 7")
    if phase6_certification.get("live_capital_enabled") is not False:
        raise ValueError("Phase 6 certification enables live capital")
    if phase6_certification.get("broker_write_allowed") is not False:
        raise ValueError("Phase 6 certification enables broker writes")
    if phase6_certification.get("reviewed_postmortem_coverage_satisfied") is True:
        if phase6_certification.get("unresolved_postmortem_count") != 0:
            raise ValueError("Phase 6 certification has false postmortem coverage")
    if phase6_certification.get("learning_actions_review_satisfied") is True:
        if phase6_certification.get("pending_review_action_count") != 0:
            raise ValueError("Phase 6 certification has false learning-action review")
    for key in (
        "knowledge_graph_read_result_count",
        "model_weight_proposal_count",
        "trust_score_proposal_count",
        "shadow_replay_variant_count",
        "architect_recommendation_count",
    ):
        if phase6_certification.get(key, 0) < 1:
            raise ValueError(f"Phase 6 certification missing count: {key}")
    if phase6_certification.get("cockpit_visibility_status") != "visible":
        raise ValueError("Phase 6 certification does not see cockpit visibility")
    if phase6_certification.get("cockpit_backend_derived") is not True:
        raise ValueError("Phase 6 certification cockpit input is not backend-derived")
    if phase6_certification.get("cockpit_ui_inferred_readiness_count") != 0:
        raise ValueError("Phase 6 certification cockpit input has UI inference")
    for record in phase6_certification.get("gate_records", []):
        if record.get("display_status") != record.get("backend_status"):
            raise ValueError("Phase 6 certification gate display/backend mismatch")
        if record.get("display_derived_from_backend") is not True:
            raise ValueError("Phase 6 certification gate display is not backend-derived")
        if record.get("ui_inferred_readiness") is not False:
            raise ValueError("Phase 6 certification gate UI inferred readiness present")
        source_ref = str(record.get("source_ref", ""))
        if source_ref.startswith("/") or source_ref.startswith("~"):
            raise ValueError("Phase 6 certification source ref exposes local path")
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
        "unsafe_write_counter_total",
        "blocking_unsafe_count",
    ):
        if phase6_certification.get(key) != 0:
            raise ValueError(f"Phase 6 certification unsafe count nonzero: {key}")
    phase6_certification_boundary = phase6_certification.get("boundary", "")
    if (
        "all scoped postmortems are reviewed" not in phase6_certification_boundary
        or "learning actions are approved or explicitly deferred"
        not in phase6_certification_boundary
        or "cannot approve learning" not in phase6_certification_boundary
        or "cannot write learning data" not in phase6_certification_boundary
        or "cannot enable live capital" not in phase6_certification_boundary
        or "cannot grant Phase 7 proof credit" not in phase6_certification_boundary
    ):
        raise ValueError("Phase 6 certification boundary is weak")

    phase7_demo_proof = payload["phase7_demo_proof"]
    missing_phase7_demo_proof = sorted(
        PHASE7_DEMO_PROOF_PUBLIC_REQUIRED_FIELDS - set(phase7_demo_proof)
    )
    if missing_phase7_demo_proof:
        raise ValueError(
            "Phase 7 demo proof public status missing fields: "
            f"{missing_phase7_demo_proof}"
        )
    if phase7_demo_proof.get("phase") != "Q7" or phase7_demo_proof.get("stage") != "Q7-15":
        raise ValueError("Phase 7 demo proof phase/stage mismatch")
    if phase7_demo_proof.get("public_safe") is not True:
        raise ValueError("Phase 7 demo proof status must be public-safe")
    if phase7_demo_proof.get("recorded") is not True:
        raise ValueError("Phase 7 demo proof visibility must be recorded after Q7-15")
    phase7_demo_proof_status = phase7_demo_proof.get("status")
    if phase7_demo_proof_status not in {"visible", "blocked"}:
        raise ValueError("Phase 7 demo proof visibility status is invalid")
    expected_phase7_demo_stage_status = (
        "phase7_demo_proof_visible"
        if phase7_demo_proof_status == "visible"
        else "phase7_demo_proof_visibility_blocked"
    )
    if phase7_demo_proof.get("stage_status") != expected_phase7_demo_stage_status:
        raise ValueError("Phase 7 demo proof stage status mismatch")
    if phase7_demo_proof.get("validation_error_count") != 0:
        raise ValueError("Phase 7 demo proof validation errors present")
    if phase7_demo_proof.get("event_log_written") is not True:
        raise ValueError("Phase 7 demo proof must write Event Log")
    if phase7_demo_proof.get("event_log_event_count") != 1:
        raise ValueError("Phase 7 demo proof Event Log count mismatch")
    if phase7_demo_proof.get("backend_derived") is not True:
        raise ValueError("Phase 7 demo proof visibility is not backend-derived")
    if phase7_demo_proof.get("display_derived_from_backend") is not True:
        raise ValueError("Phase 7 demo proof display is not backend-derived")
    if phase7_demo_proof.get("dashboard_uses_backend_status") is not True:
        raise ValueError("Phase 7 demo proof dashboard is not backend-derived")
    if phase7_demo_proof.get("ui_inferred_readiness_count") != 0:
        raise ValueError("Phase 7 demo proof UI inferred readiness present")
    if not str(phase7_demo_proof.get("visibility_state", "")).startswith(
        "backend_derived_"
    ):
        raise ValueError("Phase 7 demo proof visibility state is not backend-derived")
    if phase7_demo_proof.get("source_missing_count") != 0:
        raise ValueError("Phase 7 demo proof source artifacts missing")
    if (
        phase7_demo_proof_status == "visible"
        and phase7_demo_proof.get("source_validation_error_count") != 0
    ):
        raise ValueError("Phase 7 demo proof source validation errors present")
    if phase7_demo_proof.get("source_artifact_count") != len(
        phase7_demo_proof.get("source_status_records", [])
    ):
        raise ValueError("Phase 7 demo proof source status count mismatch")
    for record in phase7_demo_proof.get("source_status_records", []):
        if record.get("display_status") != record.get("backend_status"):
            raise ValueError("Phase 7 demo proof source display/backend mismatch")
        if record.get("display_derived_from_backend") is not True:
            raise ValueError("Phase 7 demo proof source display is not backend-derived")
        if record.get("ui_inferred_readiness") is not False:
            raise ValueError("Phase 7 demo proof source UI inferred readiness present")
        source_ref = str(record.get("source_ref", ""))
        if not source_ref.startswith("data/runtime/"):
            raise ValueError("Phase 7 demo proof source ref must be public-safe relative")
        if (
            source_ref.startswith("/")
            or source_ref.startswith("~")
            or (len(source_ref) > 2 and source_ref[1:3] == ":\\")
        ):
            raise ValueError("Phase 7 demo proof source ref exposes local path")
    if phase7_demo_proof.get("phase7_harness_day_count") != 30:
        raise ValueError("Phase 7 demo proof harness day count mismatch")
    if phase7_demo_proof.get("weekly_proof_trade_target") != 3:
        raise ValueError("Phase 7 demo proof weekly target mismatch")
    if phase7_demo_proof.get("mature_benchmark") != 100:
        raise ValueError("Phase 7 demo proof mature benchmark mismatch")
    if phase7_demo_proof.get("phase7_statistical_immaturity_hidden") is not False:
        raise ValueError("Phase 7 demo proof hides statistical immaturity")
    if phase7_demo_proof.get("phase7_mature_benchmark_met") is False:
        if phase7_demo_proof.get("phase7_mature_status_blocked") is not True:
            raise ValueError("Phase 7 demo proof immature sample is not blocked")
    if phase7_demo_proof.get("sample_contaminated") is True:
        raise ValueError("Phase 7 demo proof sample is contaminated")
    if phase7_demo_proof.get("drawdown_cap_breached") is True:
        if phase7_demo_proof.get("new_proof_trades_frozen") is not True:
            raise ValueError("Phase 7 demo proof drawdown breach did not freeze trades")
    if phase7_demo_proof_status == "visible":
        if phase7_demo_proof.get("q7_16_weekly_review_pack_stage_allowed") is not True:
            raise ValueError("Phase 7 demo proof does not allow Q7-16 weekly review pack")
    elif phase7_demo_proof.get("q7_16_weekly_review_pack_stage_allowed") is not False:
        raise ValueError("Phase 7 blocked demo proof unexpectedly allows Q7-16")
    for key in (
        "phase5_test_trades_count_for_phase7",
        "q6_deferred_learning_counts_as_proof",
        "phase7_proof_credit_allowed",
        "live_capital_enabled",
    ):
        if phase7_demo_proof.get(key) is not False:
            raise ValueError(f"Phase 7 demo proof forbidden flag enabled: {key}")
    for key in (
        "broker_write_allowed_count",
        "prediction_market_write_allowed_count",
        "crypto_perps_write_allowed_count",
        "live_endpoint_allowed_count",
        "live_capital_enabled_count",
        "proof_trade_credit_count",
        "phase7_proof_credit_allowed_count",
        "phase5_test_trade_reuse_count",
        "ui_inferred_readiness_count",
        "manual_trade_level_override_count",
        "unsafe_write_counter_total",
        "raw_payload_exposed_count",
        "private_payload_exposed_count",
        "local_path_exposed_count",
        "secret_ref_exposed_count",
        "broker_identifier_exposed_count",
    ):
        if phase7_demo_proof.get(key) != 0:
            raise ValueError(f"Phase 7 demo proof unsafe/exposure count nonzero: {key}")
    if phase7_demo_proof.get("submitted_paper_order_count", 0) < phase7_demo_proof.get(
        "closed_proof_trade_count",
        0,
    ):
        raise ValueError("Phase 7 demo proof closed trades exceed submitted orders")
    if phase7_demo_proof.get("broker_receipt_count", 0) not in {
        0,
        phase7_demo_proof.get("submitted_paper_order_count", 0),
    }:
        if phase7_demo_proof.get("broker_receipt_count", 0) < phase7_demo_proof.get(
            "closed_proof_trade_count",
            0,
        ):
            raise ValueError("Phase 7 demo proof broker receipts under closed trades")
    phase7_boundary = phase7_demo_proof.get("boundary", "")
    if (
        "from backend artifacts only" not in phase7_boundary
        or "cannot infer readiness from the UI" not in phase7_boundary
        or "cannot expose raw payloads" not in phase7_boundary
        or "cannot count Phase 5 test trades toward Phase 7 proof" not in phase7_boundary
        or "cannot hide statistical immaturity" not in phase7_boundary
        or "cannot grant Phase 7 proof credit" not in phase7_boundary
        or "cannot enable live capital" not in phase7_boundary
    ):
        raise ValueError("Phase 7 demo proof boundary is weak")
    phase5_system_map = payload["phase5_system_map"]
    missing_phase5_system_map = sorted(
        PHASE5_SYSTEM_MAP_PUBLIC_REQUIRED_FIELDS - set(phase5_system_map)
    )
    if missing_phase5_system_map:
        raise ValueError(
            "Phase 5 system map public status missing fields: "
            f"{missing_phase5_system_map}"
        )
    if (
        phase5_system_map.get("phase") != "Q5"
        or phase5_system_map.get("stage") != "Q5-13"
    ):
        raise ValueError("Phase 5 system map phase/stage mismatch")
    if phase5_system_map.get("public_safe") is not True:
        raise ValueError("Phase 5 system map status must be public-safe")
    if phase5_system_map.get("status") != "ok":
        raise ValueError("Phase 5 system map status must be ok")
    if phase5_system_map.get("validation_error_count") != 0:
        raise ValueError("Phase 5 system map validation errors present")
    if validate_phase5_system_map_bundle(phase5_system_map):
        raise ValueError("Phase 5 system map backend validation errors present")
    if phase5_system_map.get("node_count") != len(phase5_system_map.get("nodes", [])):
        raise ValueError("Phase 5 system map node count mismatch")
    if phase5_system_map.get("lane_count") != len(phase5_system_map.get("lanes", [])):
        raise ValueError("Phase 5 system map lane count mismatch")
    if phase5_system_map.get("backend_parity_error_count") != 0:
        raise ValueError("Phase 5 system map backend parity errors present")
    if phase5_system_map.get("ui_inferred_node_count") != 0:
        raise ValueError("Phase 5 system map UI inferred nodes present")
    if phase5_system_map.get("unsafe_control_count") != 0:
        raise ValueError("Phase 5 system map unsafe controls present")
    for node in phase5_system_map.get("nodes", []):
        if node.get("backend_status") != node.get("display_status"):
            raise ValueError("Phase 5 system map node display/backend mismatch")
        if node.get("ui_inferred") is not False:
            raise ValueError("Phase 5 system map node inferred state")
        for key in (
            "trade_approval_control_enabled",
            "order_place_control_enabled",
            "broker_write_allowed",
            "prediction_market_write_allowed",
            "kill_switch_mutation_authority",
            "live_capital_enabled",
        ):
            if node.get(key) is not False:
                raise ValueError(f"Phase 5 system map node authority enabled: {key}")
    system_map_posture = phase5_system_map.get("source_posture", {})
    if system_map_posture.get("canonical", {}).get("expected_source_count") != EXPECTED_SOURCE_COUNT:
        raise ValueError("Phase 5 system map canonical source count mismatch")
    if (
        system_map_posture.get("yahoo_finance", {}).get("role")
        != "supplemental_market_confirmation_only"
    ):
        raise ValueError("Phase 5 system map Yahoo Finance role mismatch")
    if system_map_posture.get("preference_mcp", {}).get("source_36") is not False:
        raise ValueError("Phase 5 system map Preference MCP source 36 enabled")
    if (
        system_map_posture.get("preference_mcp", {}).get("source_quorum_credit_allowed")
        is not False
    ):
        raise ValueError("Phase 5 system map Preference MCP source quorum enabled")
    system_map_guardrails = phase5_system_map.get("guardrails", {})
    if system_map_guardrails.get("live_capital_enabled") is not False:
        raise ValueError("Phase 5 system map live capital enabled")
    if system_map_guardrails.get("phase5_orchestration_start_allowed") is not False:
        raise ValueError("Phase 5 system map orchestration start allowed")
    if (
        system_map_guardrails.get("dashboard_claims_trading_now") is True
        and not system_map_guardrails.get("trading_state_present")
    ):
        raise ValueError("Phase 5 system map claims trading without backend state")
    system_map_boundary = phase5_system_map.get("boundary", "")
    if (
        "cannot approve trades" not in system_map_boundary
        or "cannot enable live capital" not in system_map_boundary
    ):
        raise ValueError("Phase 5 system map boundary is weak")
    quantum_oracle = payload["quantum_oracle"]
    if quantum_oracle.get("hardware_submitted_count", 0) != 0:
        raise ValueError("quantum oracle must not submit hardware jobs")
    if quantum_oracle.get("hardware_scheduler_enabled_count", 0) != 0:
        raise ValueError("quantum oracle hardware scheduler must stay disabled")
    if quantum_oracle.get("execution_allowed_count", 0) != 0:
        raise ValueError("quantum oracle must not allow execution")
    if quantum_oracle.get("paper_order_allowed_count", 0) != 0:
        raise ValueError("quantum oracle must not allow paper orders")
    if quantum_oracle.get("trade_candidate_created_count", 0) != 0:
        raise ValueError("quantum oracle must not create trade candidates")
    if quantum_oracle.get("result_count", 0):
        if quantum_oracle.get("latest_input_contract_status") != "accepted":
            raise ValueError("quantum oracle latest input contract must be accepted")
        if quantum_oracle.get("latest_market_confirmation_status") != "market_confirmation_corroboration_available":
            raise ValueError("quantum oracle latest input requires market confirmation")
        if quantum_oracle.get("latest_yahoo_only_market_confirmation") is not False:
            raise ValueError("quantum oracle latest input cannot be Yahoo-only market confirmation")
        if quantum_oracle.get("latest_input_source_type") not in {
            "signal_integrity_review",
            "certified_shadow_review_packet",
        }:
            raise ValueError("quantum oracle latest input source type is invalid")
        validate_quantum_oracle_output_routing(quantum_oracle.get("latest_output_routing", {}))
        if quantum_oracle.get("latest_output_route_type") != "shadow_annotation":
            raise ValueError("quantum oracle latest output route must be shadow annotation")
        if quantum_oracle.get("latest_output_storage_type") != "oracle_review_result":
            raise ValueError("quantum oracle latest output storage type is invalid")
    validate_quantum_local_simulator_status(quantum_oracle.get("local_simulator", {}))
    validate_quantum_scheduler_dry_run(quantum_oracle.get("scheduler_dry_run", {}))
    provider_readiness = quantum_oracle.get("provider_readiness", {})
    validate_quantum_provider_readiness(provider_readiness)
    if provider_readiness.get("provider_call_allowed_count", 0) != 0:
        raise ValueError("quantum provider readiness must not allow provider calls")
    if provider_readiness.get("hardware_submission_allowed_count", 0) != 0:
        raise ValueError("quantum provider readiness must not allow hardware submissions")
    if provider_readiness.get("hardware_scheduler_enabled_count", 0) != 0:
        raise ValueError("quantum provider readiness must not enable hardware schedulers")
    if provider_readiness.get("execution_allowed_count", 0) != 0:
        raise ValueError("quantum provider readiness must not allow execution")
    if provider_readiness.get("paper_order_allowed_count", 0) != 0:
        raise ValueError("quantum provider readiness must not allow paper orders")
    if provider_readiness.get("trade_candidate_authority_count", 0) != 0:
        raise ValueError("quantum provider readiness must not create trade candidates")
    if provider_readiness.get("secret_value_exposed_count", 0) != 0:
        raise ValueError("quantum provider readiness must not expose secret values")
    if provider_readiness.get("raw_response_exposed_count", 0) != 0:
        raise ValueError("quantum provider readiness must not expose raw provider responses")
    fire_opal_ibm = payload.get("qctrl_fire_opal_ibm_readiness", {})
    validate_qctrl_fire_opal_ibm_readiness(fire_opal_ibm)
    if quantum_oracle.get("fire_opal_ibm_readiness") != fire_opal_ibm:
        raise ValueError("Fire Opal IBM readiness mismatch between cockpit surfaces")
    phase3_readiness = payload["mission_control"].get("phase3_readiness", {})
    phase3_required = {
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
    missing_phase3_fields = sorted(phase3_required - set(phase3_readiness))
    if missing_phase3_fields:
        raise ValueError(f"Phase 3 readiness missing fields: {missing_phase3_fields}")
    if phase3_readiness.get("phase") != "Q3":
        raise ValueError("Phase 3 readiness phase must be Q3")
    if phase3_readiness.get("status") != "provider_scheduler_readiness":
        raise ValueError("Phase 3 readiness status must be provider/scheduler readiness")
    if phase3_readiness.get("execution_readiness") != "not_execution_ready":
        raise ValueError("Phase 3 readiness must not imply execution readiness")
    if phase3_readiness.get("public_safe") is not True:
        raise ValueError("Phase 3 readiness must be public-safe")
    if phase3_readiness.get("qctrl_configured") != bool(provider_readiness.get("qctrl_configured")):
        raise ValueError("Phase 3 readiness Q-CTRL status must mirror provider readiness")
    if phase3_readiness.get("local_simulator_backend") != quantum_oracle.get("local_simulator", {}).get("selected_backend"):
        raise ValueError("Phase 3 readiness local simulator backend mismatch")
    if phase3_readiness.get("scheduler_enabled") is not False:
        raise ValueError("Phase 3 readiness must keep scheduler disabled")
    if phase3_readiness.get("autonomous_scheduler_enabled") is not False:
        raise ValueError("Phase 3 readiness must keep autonomous scheduler disabled")
    for key in (
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
        "qctrl_provider_call_count",
        "scheduler_jobs_queued_count",
        "scheduler_jobs_submitted_count",
    ):
        if phase3_readiness.get(key) != 0:
            raise ValueError(f"Phase 3 readiness must keep {key}=0")
    if "provider/scheduler readiness only" not in phase3_readiness.get("boundary", ""):
        raise ValueError("Phase 3 readiness boundary must describe provider/scheduler scope")
    if "not execution readiness" not in phase3_readiness.get("boundary", ""):
        raise ValueError("Phase 3 readiness boundary must block execution readiness")
    if payload["d0_shell"].get("status") != "frozen":
        raise ValueError("D0 shell must be frozen before D1 export")
    live_bridge = payload["live_bridge"]
    if live_bridge.get("phase") != "D9":
        raise ValueError("live bridge phase must be D9")
    if live_bridge.get("read_only") is not True:
        raise ValueError("live bridge must be read-only")
    if live_bridge.get("browser_authority") != "read_only":
        raise ValueError("live bridge browser authority must remain read-only")
    if live_bridge.get("write_authority") is not False:
        raise ValueError("live bridge must not have write authority")
    if live_bridge.get("broker_write_route") is not False:
        raise ValueError("live bridge must not expose a broker write route")
    if live_bridge.get("local_orchestrator_exposed") is not False:
        raise ValueError("live bridge must not expose the local orchestrator")

    problems = _walk_payload(payload)
    if problems:
        raise ValueError("cockpit status is not public-safe: " + "; ".join(problems))


def write_cockpit_status(payload: dict[str, Any], path: str | Path | None = None) -> Path:
    validate_cockpit_status(payload)
    settings = Settings.from_env()
    output_path = Path(path or Path(settings.runtime_dir) / COCKPIT_STATUS_FILENAME)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    write_status_signature(payload, output_path)
    return output_path


def export_cockpit_status(
    *,
    settings: Settings | None = None,
    output_path: str | Path | None = None,
    landing_repo_path: str | Path | None = "landing-page-repo",
    copy_to_landing: bool = True,
) -> dict[str, Any]:
    settings = settings or Settings.from_env()
    payload = build_cockpit_status(settings)
    runtime_path = write_cockpit_status(payload, output_path)
    landing_path: Path | None = None
    if copy_to_landing and landing_repo_path:
        repo_path = Path(landing_repo_path)
        if repo_path.exists():
            landing_path = repo_path / "status" / COCKPIT_STATUS_FILENAME
            write_cockpit_status(payload, landing_path)
    return {
        "status": "ok",
        "runtime_path": str(runtime_path),
        "landing_path": str(landing_path) if landing_path else None,
        "runtime_signature_path": str(runtime_path.with_name("cockpit-status.signature.json")),
        "landing_signature_path": str(landing_path.with_name("cockpit-status.signature.json")) if landing_path else None,
        "schema_version": payload["schema_version"],
        "generated_at": payload["generated_at"],
        "module_count": len(payload["modules"]),
        "watching_count": len(payload["watching"]),
        "research_goal_count": len(payload["cognition"].get("research_goal_records", [])),
        "market_context_packet_count": payload["cognition"].get("market_context", {}).get("packet_count", 0),
        "hypothesis_count": len(payload["cognition"]["hypotheses"]),
        "trade_candidate_count": len(payload["trade_layer"]["candidates"]),
        "forbidden_action_count": len(payload["forbidden_actions"]),
        "yahoo_finance_status": payload["yahoo_finance"]["status"],
        "phase7_demo_proof_status": payload["phase7_demo_proof"]["status"],
        "rs9_learning_loop_status": payload["rs9_learning_loop"]["status"],
        "rs9_learning_direction": payload["rs9_learning_loop"]["learning_direction"],
    }
