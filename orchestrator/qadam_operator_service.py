"""OR-18 unattended operator-service contract and safety probes.

The service coordinates existing research and status components. It never owns
broker credentials or bypasses guarded PaperOps, and installation remains an
explicit operator action.
"""

from __future__ import annotations

from contextlib import contextmanager
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta, timezone
import fcntl
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import threading
import time
from typing import Any, Callable
from zoneinfo import ZoneInfo

from orchestrator.config import Settings
from orchestrator.qadam_canonical_contracts import AtomicArtifactStore
from orchestrator.qadam_control_plane_store import ControlPlaneStore
from orchestrator.qadam_artifact_generations import (
    ArtifactGenerationStore,
    GenerationError,
)
from orchestrator.qadam_operator_ready_common import (
    ROOT,
    append_jsonl_durable,
    authority_flags,
    file_sha256,
    now_iso,
    read_json,
    read_jsonl,
    runtime_dir,
    sha256_json,
    unique_errors,
    validate_authority,
)
from orchestrator.qadam_resource_locks import (
    ResourceClaims,
    ResourceLease,
    ResourceLockBusy,
    claims_are_compatible,
)
from orchestrator.qadam_runtime_domains import (
    max_jobs_per_cycle as configured_max_jobs_per_cycle,
    order_by_domain_reservations,
    service_domain,
    validate_domain_coverage,
)
from orchestrator.qadam_state_root import resolve_state_root
from orchestrator.qadam_storage_retention import (
    MAINTENANCE_LEDGER_ARTIFACT as STORAGE_MAINTENANCE_LEDGER_ARTIFACT,
    live_storage_health,
    provider_budget_available,
    prune_research_generations,
    run_storage_maintenance,
)

SCHEMA_VERSION = "qadam_operator_service.v2"
PHASE_ID = "OR-18"

STATUS_ARTIFACT = "qadam_operator_service_status.json"
HEARTBEATS_ARTIFACT = "qadam_operator_service_heartbeats.json"
REPAIR_QUEUE_ARTIFACT = "qadam_operator_repair_queue.json"
RETRY_LEDGER_ARTIFACT = "qadam_operator_retry_ledger.jsonl"
SOAK_ARTIFACT = "qadam_operator_soak_test.json"
WHY_NOT_RUNNING_ARTIFACT = "qadam_operator_why_not_running.json"
LEASE_ARTIFACT = "qadam_operator_service_lease.json"
CHECK_ARTIFACT = "qadam_operator_service_checks.json"
RECEIPTS_ARTIFACT = "qadam_operator_service_receipts.jsonl"
RECEIPT_INDEX_ARTIFACT = "qadam_operator_service_receipt_index.json"
RECEIPT_INDEX_LOCK_FILENAME = ".qadam_operator_service_receipt_index.lock"
CONTROL_STATE_LOCK_FILENAME = ".qadam_operator_control_state.lock"
WORKER_STATE_LOCK_FILENAME = ".qadam_operator_worker_state.lock"
INTEGRATION_PROBE_ARTIFACT = "qadam_operator_integration_probe.json"
CIRCUIT_BREAKERS_ARTIFACT = "qadam_operator_circuit_breakers.json"
CIRCUIT_REVALIDATION_ARTIFACT = "qadam_operator_circuit_revalidation_evidence.jsonl"
WORKERS_ARTIFACT = "qadam_operator_workers.json"
SESSION_LEDGER_ARTIFACT = "qadam_operator_session_ledger.jsonl"
MAINTENANCE_ARTIFACT = "qadam_operator_maintenance_window.json"
DISPATCH_CURSOR_ARTIFACT = "qadam_operator_dispatch_cursor.json"
FULL_HEAL_REQUEST_ARTIFACT = "qadam_operator_full_heal_request.json"
FULL_HEAL_RECEIPT_ARTIFACT = "qadam_operator_full_heal_receipt.json"
RECOVERY_COVERAGE_ARTIFACT = "qadam_self_healing_recovery_coverage.json"
MAINTENANCE_LOCK_FILENAME = ".qadam_runtime_maintenance.lock"
MAINTENANCE_REQUEST_MAX_AGE_SECONDS = 900
# A request must survive laptop sleep or a temporary network interruption. It is
# still safe because the singleton rejects requests from another code commit or
# operator contract before executing any service.
FULL_HEAL_REQUEST_MAX_AGE_SECONDS = 24 * 60 * 60
FULL_HEAL_SAFE_CIRCUIT_FAILURE_CLASSES = {
    "database_io_unavailable",
    "storage_maintenance_due",
    "concurrent_artifact_access",
    "transient_provider_network",
    "rate_limit",
    "stale_artifact",
    "interrupted_resumable_job",
    "optional_transport_unconfigured",
}
REPEATED_SKIP_AUDIT_INTERVAL_SECONDS = 21600

LOCK_ARTIFACT = "qadam_long_backtest_lock.json"
RELEASE_ARTIFACT = "qadam_research_lock_release_readiness.json"
EXPERIMENTAL_RELEASE_ARTIFACT = "qadam_experimental_paper_release_readiness.json"
RESEARCH_STATUS_ARTIFACT = "qadam_research_supervisor_status.json"
RESEARCH_HEARTBEAT_ARTIFACT = "qadam_research_supervisor_heartbeat.json"
DASHBOARD_FRESHNESS_ARTIFACT = "qadam_operator_dashboard_freshness.json"
SELF_HEALING_STATUS_ARTIFACT = "qadam_self_healing_status.json"
LEGACY_SOAK_ARTIFACT = "qadam_operational_soak_run.json"
PERMANENT_RELIABILITY_ARTIFACT = "qadam_permanent_operator_reliability_certification.json"
PAPER_ORDERS_ARTIFACT = "paper_orders.jsonl"
ORDER_EXPOSURE_INTEGRITY_ARTIFACT = "qadam_operator_order_exposure_integrity.json"
OPEN_BROKER_ORDER_STATES = frozenset(
    {"accepted", "new", "open", "pending", "pending_new", "partially_filled", "submitted"}
)
OPENING_POSITION_INTENTS = frozenset({"buy_to_open", "sell_to_open"})
MAX_PENDING_MARKET_ORDER_AGE_SECONDS = 15 * 60
NON_BLOCKING_DERIVED_PROJECTION_ARTIFACTS = frozenset(
    {
        # Liveness is checked directly from the active lease and process. The
        # service status is this builder's own projection, so treating an old
        # copy as a repair request creates a self-referential deadlock after a
        # legitimately long worker cycle.
        STATUS_ARTIFACT,
        "qadam_operator_ready_edge_engine_certification.json",
        "qadam_permanent_operator_reliability_status.json",
        # The consolidated operator service replaced the legacy research
        # supervisor. Its compatibility heartbeat can be older than the old
        # five-minute cadence without indicating a missed active service.
        RESEARCH_HEARTBEAT_ARTIFACT,
    }
)

LAUNCHD_LABEL = "com.qadam.operator"
LAUNCHD_TEMPLATE = ROOT / "ops" / "launchd" / f"{LAUNCHD_LABEL}.plist.template"
LAUNCHD_TARGET = Path.home() / "Library" / "LaunchAgents" / f"{LAUNCHD_LABEL}.plist"
INSTALLER = ROOT / "scripts" / "install_qadam_operator_launch_agent.sh"
RUNNER = ROOT / "scripts" / "run_qadam_operator_service.py"
WORKER_RUNNER = ROOT / "scripts" / "run_qadam_operator_worker.py"

FAILURE_CLASSES = (
    "database_io_unavailable",
    "storage_maintenance_due",
    "concurrent_artifact_access",
    "transient_provider_network",
    "rate_limit",
    "credential_operator_action",
    "parser_schema_drift",
    "stale_artifact",
    "disk_resource_pressure",
    "interrupted_resumable_job",
    "research_integrity_hold",
    "optional_transport_unconfigured",
    "code_defect",
    "safety_violation",
)
SAME_FINGERPRINT_REVALIDATION_CLASSES = frozenset({
    "concurrent_artifact_access", "database_io_unavailable", "storage_maintenance_due"
})
MAX_AUTOMATIC_STABILITY_REVALIDATIONS = 3

# A guarded synchronous cycle can legitimately include current-market
# conversion plus the canonical PaperOps wrapper. Service liveness therefore
# needs a wider clock than the evidence used by an individual trade decision.
# Quote, spread, source, and setup expiry remain enforced by their own gates.
MIN_SERVICE_HEALTH_FRESHNESS_SECONDS = 30 * 60

RECOVERY_MODES = frozenset(
    {
        "safe_revalidate",
        "bounded_resume",
        "terminal_aware_bounded_resume",
        "guarded_market_conversion",
        "guarded_paperops",
    }
)


@dataclass(frozen=True, kw_only=True)
class ServiceDefinition:
    service_id: str
    purpose: str
    cadence_seconds: int
    trigger: str
    ownership: str
    safe_retry_class: str
    recovery_mode: str
    command_sequence: tuple[tuple[str, ...], ...]
    timeout_seconds: int
    dependencies: tuple[str, ...]
    concurrency_group: str
    lock_requirement: str
    safety_mode: str
    prerequisite_artifacts: tuple[str, ...] = ()
    prerequisite_max_age_seconds: int = 21600
    long_running: bool = False
    market_session_only: bool = False
    provider_budget_required: bool = False
    integration_probe_command_sequence: tuple[tuple[str, ...], ...] = ()
    paperops_dependency: bool = False
    latency_sensitive: bool = False
    freshness_deadline_seconds: int | None = None
    read_resources: tuple[str, ...] = ()
    write_resources: tuple[str, ...] = ()
    append_resources: tuple[str, ...] = ()
    generation_artifacts: tuple[str, ...] = ()
    resource_lock_timeout_seconds: int = 30
    wake_on_dependency_advance: bool = True

    def resource_claims(self) -> ResourceClaims:
        return ResourceClaims(
            reads=self.read_resources,
            writes=self.write_resources,
            appends=self.append_resources,
        )

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


SERVICE_DEFINITIONS = (
    ServiceDefinition(
        service_id="source_ingestion",
        purpose="Refresh configured source evidence on provider-safe schedules.",
        cadence_seconds=300,
        trigger="provider_schedule_and_freshness",
        ownership="source_heartbeat_runner",
        safe_retry_class="idempotent_read",
        recovery_mode="safe_revalidate",
        command_sequence=(
            ("scripts/run_source_heartbeat.py", "--once"),
            ("scripts/run_qadam_live_source_refresh.py", "--max-sources", "10"),
            ("scripts/check_qsase_universal_source_price_matrix.py",),
            ("scripts/check_qsase_source_reliability.py",),
            ("scripts/check_qadam_source_provider_capabilities.py",),
            ("scripts/check_qadam_point_in_time_evidence.py",),
            ("scripts/check_qadam_source_capability_registry.py",),
        ),
        timeout_seconds=900,
        dependencies=(),
        concurrency_group="provider_read",
        lock_requirement="research_read_allowed",
        safety_mode="read_only_provider_refresh",
        read_resources=("price_lake",),
        write_resources=("source_lake", "point_in_time_evidence"),
        generation_artifacts=(
            "qadam_source_research_goal_ingestion.json",
            "qadam_source_provider_capabilities_checks.json",
            "qadam_point_in_time_evidence_checks.json",
            "qadam_source_capability_registry.json",
            "qadam_source_capability_registry_checks.json",
        ),
    ),
    ServiceDefinition(
        service_id="historical_source_worker",
        purpose="Resume bounded source-history acquisition from reviewed providers.",
        cadence_seconds=900,
        trigger="incomplete_source_partitions_and_budget",
        ownership="or3_source_history_runner",
        safe_retry_class="interrupted_resumable_job",
        recovery_mode="terminal_aware_bounded_resume",
        command_sequence=(
            (
                "scripts/run_qadam_source_history_acquisition.py",
                "--allow-network",
                "--provider-terms-reviewed",
                "--max-jobs",
                "10",
                "--classify-deferred",
            ),
        ),
        integration_probe_command_sequence=(
            (
                "scripts/run_qadam_source_history_acquisition.py",
                "--provider-terms-reviewed",
                "--max-jobs",
                "1",
                "--classify-deferred",
            ),
        ),
        timeout_seconds=1800,
        dependencies=(),
        concurrency_group="historical_research",
        lock_requirement="research_read_allowed",
        safety_mode="resumable_provider_acquisition",
        long_running=True,
        provider_budget_required=True,
        write_resources=("source_lake",),
        generation_artifacts=("qadam_source_backfill_manifest.json",),
    ),
    ServiceDefinition(
        service_id="market_price_refresh",
        purpose="Refresh paper-market prices during relevant sessions.",
        cadence_seconds=60,
        trigger="market_session_and_instrument_schedule",
        ownership="existing_market_data_adapters",
        safe_retry_class="idempotent_read",
        recovery_mode="safe_revalidate",
        command_sequence=(("scripts/check_alpaca_paper_mirror.py", "--live"),),
        integration_probe_command_sequence=(("scripts/check_alpaca_paper_mirror.py",),),
        timeout_seconds=120,
        dependencies=(),
        concurrency_group="provider_read",
        lock_requirement="paper_read_only_allowed",
        safety_mode="alpaca_paper_get_only",
        market_session_only=True,
        latency_sensitive=True,
        write_resources=("price_lake", "paper_state"),
        generation_artifacts=(
            "qadam_price_backfill_manifest.json",
            "alpaca_paper_mirror.json",
        ),
    ),
    ServiceDefinition(
        service_id="execution_context",
        purpose=(
            "Compile current session, quote, spread, liquidity, volatility, and "
            "provider state for qualified paper setups."
        ),
        cadence_seconds=60,
        trigger="qualified_trigger_or_open_position",
        ownership="canonical_execution_context_service",
        safe_retry_class="idempotent_read",
        recovery_mode="safe_revalidate",
        command_sequence=(("scripts/check_qadam_execution_context.py",),),
        integration_probe_command_sequence=(("scripts/check_qadam_execution_context.py",),),
        timeout_seconds=120,
        # This read-only compiler consumes market_context_packet, not the
        # account mirror. It must publish missing/expired context even when
        # the market-hours mirror job has never run (for example on restart).
        dependencies=(),
        concurrency_group="provider_read",
        lock_requirement="paper_read_only_allowed",
        safety_mode="current_market_context_read_only",
        market_session_only=False,
        latency_sensitive=True,
        read_resources=("price_lake", "paper_state"),
        write_resources=("learning_plane",),
        generation_artifacts=(
            "qadam_execution_contexts.jsonl",
            "qadam_execution_context_summary.json",
            "qadam_execution_context_checks.json",
        ),
    ),
    ServiceDefinition(
        service_id="open_market_conversion",
        purpose=(
            "Run the fresh-clock, same-generation Akber, shadow, risk, Router, "
            "and canonical PaperOps conversion path for current paper setups."
        ),
        cadence_seconds=300,
        trigger="regular_session_or_new_current_trigger",
        ownership="ef11_open_market_conversion_coordinator",
        safe_retry_class="no_automatic_broker_write_retry",
        recovery_mode="guarded_market_conversion",
        command_sequence=(
            (
                "scripts/run_qadam_open_market_conversion.py",
                "--allow-network",
                "--no-paperops",
            ),
        ),
        integration_probe_command_sequence=(
            (
                "scripts/run_qadam_open_market_conversion.py",
                "--broker-disabled-canary",
                "--no-paperops",
            ),
        ),
        timeout_seconds=1800,
        dependencies=("market_price_refresh", "execution_context"),
        concurrency_group="market_conversion_critical",
        lock_requirement="explicit_research_lock_release_required",
        safety_mode="paper_only_same_generation_canonical_paperops",
        market_session_only=True,
        paperops_dependency=True,
        latency_sensitive=True,
        read_resources=(
            "source_lake",
            "score_plane",
            "edge_registry",
        ),
        write_resources=(
            "price_lake",
            "learning_plane",
            "paper_state",
            "dashboard_projection",
        ),
        generation_artifacts=(
            "qadam_market_clock_truth.json",
            "qadam_prestaged_setup_status.json",
            "qadam_open_market_conversion_generation.json",
            "qadam_open_market_conversion_status.json",
            "qadam_ef11_open_market_conversion_certification.json",
        ),
    ),
    ServiceDefinition(
        service_id="pattern_scoring",
        purpose="Score only after point-in-time evidence refresh completes.",
        cadence_seconds=300,
        trigger="new_evidence_cutoff",
        ownership="pattern_score_v3",
        safe_retry_class="deterministic_calculation",
        recovery_mode="safe_revalidate",
        command_sequence=(
            ("scripts/check_qadam_pattern_score_v3.py",),
            ("scripts/run_qadam_pattern_score_tape.py", "--resume"),
        ),
        timeout_seconds=600,
        dependencies=("source_ingestion",),
        concurrency_group="research_cpu",
        lock_requirement="research_read_allowed",
        safety_mode="deterministic_research_only",
        freshness_deadline_seconds=15 * 60,
        prerequisite_artifacts=("qadam_point_in_time_evidence_checks.json",),
        read_resources=("point_in_time_evidence",),
        write_resources=("score_plane",),
        generation_artifacts=(
            "qadam_feature_registry.json",
            "qadam_pattern_score_v3.json",
            "qadam_pattern_score_v3_records.jsonl",
            "qadam_pattern_score_v3_rejections.jsonl",
            "qadam_pattern_score_v3_dashboard_summary.json",
            "qadam_pattern_score_v3_checks.json",
            "qadam_pattern_score_tape_manifest.json",
            "qadam_pattern_score_tape_progress.json",
            "qadam_pattern_score_tape_quality.json",
            "qadam_pattern_score_tape_checks.json",
        ),
    ),
    ServiceDefinition(
        service_id="research_evidence_validation",
        purpose=(
            "Rebuild forward labels, statistical tests, nonlinear review, and the "
            "edge registry in strict dependency order after pattern scoring."
        ),
        cadence_seconds=300,
        trigger="new_pattern_score_or_validation_deadline",
        ownership="research_evidence_validation",
        safe_retry_class="deterministic_calculation",
        recovery_mode="safe_revalidate",
        command_sequence=(
            ("scripts/check_qadam_forward_labels.py",),
            ("scripts/check_qadam_statistical_backtest.py",),
            ("scripts/check_qadam_nonlinear_quantum_value.py",),
            ("scripts/check_qadam_edge_registry.py",),
        ),
        timeout_seconds=1800,
        dependencies=("pattern_scoring",),
        concurrency_group="research_cpu",
        lock_requirement="research_read_allowed",
        safety_mode="ordered_research_validation_only",
        freshness_deadline_seconds=15 * 60,
        prerequisite_artifacts=("qadam_pattern_score_v3_checks.json",),
        read_resources=("source_lake", "price_lake", "score_plane"),
        write_resources=("label_plane", "edge_registry"),
        generation_artifacts=(
            "qadam_forward_labels_checks.json",
            "qadam_statistical_backtest_checks.json",
            "qadam_nonlinear_quantum_value_checks.json",
            "qadam_edge_registry_checks.json",
        ),
    ),
    ServiceDefinition(
        service_id="akber_review",
        purpose=(
            "Refresh exact read-only decision context and form V3 strategy drafts. "
            "The canonical compiler performs the later Akber review."
        ),
        cadence_seconds=300,
        trigger="new_score_and_context",
        ownership="akber_filter_v3",
        safe_retry_class="deterministic_calculation",
        recovery_mode="safe_revalidate",
        command_sequence=(
            ("scripts/check_market_context_packet.py",),
            ("scripts/check_qadam_strategy_translation.py",),
            ("scripts/check_qadam_akber_evidence_fit.py",),
        ),
        timeout_seconds=300,
        dependencies=("research_evidence_validation",),
        concurrency_group="research_cpu",
        lock_requirement="research_read_allowed",
        safety_mode="research_eligibility_only",
        freshness_deadline_seconds=15 * 60,
        prerequisite_artifacts=("qadam_edge_registry_checks.json",),
        read_resources=("edge_registry",),
        write_resources=("price_lake", "learning_plane"),
        generation_artifacts=(
            "market_context_packet.json",
            "qadam_current_event_triggers.jsonl",
            "qadam_current_regime_observations.jsonl",
            "qadam_current_market_dislocations.jsonl",
            "qadam_trigger_factory_summary.json",
            "qadam_trigger_factory_rejections.jsonl",
            "qadam_direction_resolutions.jsonl",
            "qadam_direction_resolution_rejections.jsonl",
            "qadam_direction_retry_queue.jsonl",
            "qadam_emerging_strategy_formations.jsonl",
            "qadam_strategy_translation_summary.json",
            "qadam_strategy_foundry_v3_checks.json",
            "qadam_strategy_drafts_v3.jsonl",
            "qadam_akber_evidence_fit_checks.json",
            "qadam_akber_evidence_profile_policy.json",
        ),
    ),
    ServiceDefinition(
        service_id="qeg_evidence_cycle",
        purpose=(
            "Connect current evidence, experiment memory, graph patterns, strategy "
            "admission, and Akber inputs before forward observation."
        ),
        cadence_seconds=300,
        trigger="new_akber_context_or_graph_freshness_deadline",
        ownership="qadam_temporal_evidence_graph",
        safe_retry_class="deterministic_calculation",
        recovery_mode="safe_revalidate",
        command_sequence=(("scripts/run_qadam_qeg_cycle.py", "--operational"),),
        integration_probe_command_sequence=(("scripts/run_qadam_qeg_cycle.py", "--operational"),),
        timeout_seconds=3600,
        dependencies=("akber_review",),
        concurrency_group="research_cpu",
        lock_requirement="ordered_temporal_graph_write",
        safety_mode="research_only_graph_and_akber_input_projection",
        freshness_deadline_seconds=15 * 60,
        prerequisite_artifacts=("qadam_strategy_foundry_v3_checks.json",),
        read_resources=(
            "source_lake",
            "price_lake",
            "point_in_time_evidence",
            "score_plane",
            "label_plane",
            "edge_registry",
            "paper_state",
        ),
        write_resources=("temporal_graph", "learning_plane"),
        generation_artifacts=(
            "qadam_temporal_graph_manifest.json",
            "qadam_temporal_graph_health.json",
            "qadam_experiment_memory_summary.json",
            "qadam_graph_pattern_candidates.json",
            "qadam_actionability_queue.json",
            "qadam_graph_experiment_bridge.json",
            "qadam_graph_quantum_challenger.json",
            "qadam_current_expectancy_v2.jsonl",
            "qadam_graph_strategy_versions.json",
            "qadam_paper_strategy_admission.json",
            "qadam_qeg_strategy_hypotheses.jsonl",
            "qadam_qeg_decision_evidence_packets.jsonl",
            "qadam_qeg_akber_inputs.jsonl",
            "qadam_qeg_akber_results.jsonl",
            "qadam_graph_active_discovery_funnel.json",
            "qadam_qeg_cycle_summary.json",
        ),
    ),
    ServiceDefinition(
        service_id="qualitative_evidence_cycle",
        purpose=(
            "Acquire bounded approved qualitative evidence, preserve point-in-time "
            "provenance, test source-price relationships, and compile typed lane "
            "contributions without invoking the downstream tradeability compiler."
        ),
        cadence_seconds=900,
        trigger="approved_origin_refresh_or_forward_window_maturity",
        ownership="qualitative_evidence_operator",
        safe_retry_class="interrupted_resumable_job",
        recovery_mode="safe_revalidate",
        command_sequence=(
            (
                "scripts/run_qadam_agent_reach_operator.py",
                "--allow-network",
                "--no-fast-path",
            ),
        ),
        integration_probe_command_sequence=(
            ("scripts/run_qadam_agent_reach_operator.py", "--no-fast-path"),
        ),
        timeout_seconds=1800,
        dependencies=("source_ingestion",),
        concurrency_group="provider_read",
        lock_requirement="bounded_qualitative_evidence_write",
        safety_mode="sandboxed_read_only_research_no_trade_authority",
        freshness_deadline_seconds=30 * 60,
        prerequisite_artifacts=("qadam_point_in_time_evidence_checks.json",),
        read_resources=("price_lake", "paper_state"),
        write_resources=(
            "source_lake",
            "label_plane",
            "edge_registry",
            "temporal_graph",
            "learning_plane",
            "dashboard_projection",
        ),
        generation_artifacts=(
            "qadam_agent_reach_baseline.json",
            "qadam_source_count_contract.json",
            "qadam_qualitative_evidence_gap_map.json",
            "qadam_agent_reach_supply_chain_audit.json",
            "qadam_agent_reach_sandbox_status.json",
            "qadam_external_origin_terms_matrix.json",
            "qadam_external_origin_promotion_ledger.jsonl",
            "qadam_external_document_manifest.jsonl",
            "qadam_external_documents.jsonl",
            "qadam_external_acquisition_status.json",
            "qadam_external_channel_health.json",
            "qadam_external_evidence_security_audit.json",
            "qadam_external_evidence_provenance_audit.json",
            "qadam_qualitative_claims.jsonl",
            "qadam_qualitative_claim_rejections.jsonl",
            "qadam_qualitative_claim_challenges.jsonl",
            "qadam_qualitative_claim_summary.json",
            "qadam_qualitative_graph_summary.json",
            "qadam_qualitative_entity_mappings.jsonl",
            "qadam_qualitative_instrument_mappings.jsonl",
            "qadam_qualitative_history_coverage.json",
            "qadam_qualitative_forward_window_status.json",
            "qadam_qualitative_label_manifest.jsonl",
            "qadam_qualitative_pattern_candidates.jsonl",
            "qadam_qualitative_pattern_rejections.jsonl",
            "qadam_qualitative_backtest_summary.json",
            "qadam_qualitative_quantum_review.json",
            "qadam_qualitative_pattern_score_bridge.json",
            "qadam_qualitative_direction_resolutions.jsonl",
            "qadam_qualitative_strategy_impacts.jsonl",
            "qadam_qualitative_akber_inputs.jsonl",
            "qadam_qualitative_akber_explanations.jsonl",
            "qadam_qualitative_paper_eligibility.json",
            "qadam_prediction_contract_registry.jsonl",
            "qadam_prediction_contracts.jsonl",
            "qadam_prediction_contract_graph.json",
            "qadam_prediction_belief_states.jsonl",
            "qadam_prediction_market_research.json",
            "qadam_prediction_market_paper_registry.json",
            "qadam_prediction_market_quality.json",
            "qadam_prediction_market_consistency_records.jsonl",
            "qadam_prediction_market_cross_asset_signals.jsonl",
            "qadam_prediction_market_intelligence_summary.json",
            "qadam_lane_contributions.jsonl",
            "qadam_lane_authority_inventory.json",
            "qadam_lane_conversion_funnel.json",
            "qadam_lane_blocker_ownership.json",
            "qadam_qualitative_dashboard_summary.json",
            "qadam_qualitative_communications_summary.json",
            "qadam_qualitative_notification_dedupe.jsonl",
            "qadam_agent_reach_operator_status.json",
            "qadam_agent_reach_repair_queue.jsonl",
            "qadam_agent_reach_resource_state.json",
            "qadam_agent_reach_soak_status.json",
        ),
    ),
    ServiceDefinition(
        service_id="power_market_research",
        purpose=(
            "Refresh CAISO power fundamentals and Alpaca proxy evidence, resume a "
            "bounded historical backfill, and test the emerging power strategy."
        ),
        cadence_seconds=1800,
        trigger="power_market_refresh_or_incomplete_partition",
        ownership="power_market_edge_engine",
        safe_retry_class="interrupted_resumable_job",
        recovery_mode="bounded_resume",
        command_sequence=(
            (
                "scripts/run_qadam_power_market_edge_engine.py",
                "--once",
                "--allow-network",
                "--max-partitions",
                "8",
            ),
            ("scripts/check_qadam_power_market_edge_engine.py",),
        ),
        integration_probe_command_sequence=(
            ("scripts/run_qadam_power_market_edge_engine.py", "--once"),
        ),
        timeout_seconds=1200,
        dependencies=(),
        concurrency_group="historical_research",
        lock_requirement="research_read_allowed",
        safety_mode="provider_read_only_emerging_strategy_research",
        long_running=True,
        read_resources=("paper_state",),
        write_resources=("power_market_research",),
        generation_artifacts=(
            "qadam_power_market_edge_engine.json",
            "qadam_power_market_acquisition_manifest.json",
            "qadam_power_market_backtest.json",
            "qadam_power_market_strategy_registry.json",
            "qadam_power_market_pattern_scores.jsonl",
            "qadam_power_market_context.json",
            "qadam_power_market_dashboard_summary.json",
            "qadam_power_market_edge_engine_checks.json",
        ),
    ),
    ServiceDefinition(
        service_id="canonical_tradeability",
        purpose=(
            "Compile V3 and QEG research drafts into one strict same-generation "
            "tradeability envelope and the sole Akber/downstream projection."
        ),
        cadence_seconds=300,
        trigger="new_foundry_or_qeg_draft",
        ownership="canonical_tradeability_compiler",
        safe_retry_class="deterministic_calculation",
        recovery_mode="safe_revalidate",
        command_sequence=(
            ("scripts/check_qadam_tradeability_pipeline.py",),
            ("scripts/check_qadam_akber_filter_v3.py",),
            ("scripts/check_qadam_tradeability_migration.py",),
            ("scripts/check_qadam_tradeability_reachability.py",),
            ("scripts/check_qadam_contract_defect_handling.py",),
        ),
        integration_probe_command_sequence=(
            ("scripts/check_qadam_tradeability_pipeline.py",),
            ("scripts/check_qadam_akber_filter_v3.py",),
            ("scripts/check_qadam_tradeability_reachability.py",),
            ("scripts/check_qadam_contract_defect_handling.py",),
        ),
        timeout_seconds=900,
        dependencies=("qeg_evidence_cycle", "qualitative_evidence_cycle"),
        concurrency_group="research_cpu",
        lock_requirement="ordered_tradeability_compile",
        safety_mode="paper_only_research_compilation_no_authority",
        freshness_deadline_seconds=15 * 60,
        prerequisite_artifacts=("qadam_qeg_cycle_summary.json",),
        read_resources=("temporal_graph", "edge_registry", "price_lake"),
        write_resources=("learning_plane",),
        generation_artifacts=(
            "qadam_tradeability_envelopes.jsonl",
            "qadam_tradeability_envelope_registry.json",
            "qadam_tradeability_envelope_rejections.jsonl",
            "qadam_tradeability_pipeline_checks.json",
            "qadam_tradeability_envelope_checks.json",
            "qadam_tradeability_pipeline_summary.json",
            "qadam_canonical_tradeability_foundry_summary.json",
            "qadam_decision_evidence_packets.jsonl",
            "qadam_decision_evidence_packet_summary.json",
            "qadam_decision_evidence_packet_rejections.jsonl",
            "qadam_generation_integrity_checks.json",
            "qadam_akber_filter_v3_inputs.jsonl",
            "qadam_akber_filter_v3_results.jsonl",
            "qadam_akber_filter_v3_checks.json",
            "qadam_tradeability_contract_defects.jsonl",
            "qadam_contract_defects.jsonl",
            "qadam_contract_repair_requests.jsonl",
            "qadam_contract_defect_summary.json",
            "qadam_tradeability_migration_status.json",
            "qadam_legacy_contract_parity.json",
            "qadam_consumer_migration_audit.json",
            "qadam_deprecation_registry.json",
            "qadam_tradeability_migration_checks.json",
            "qadam_tradeability_reachability_canary.json",
            "qadam_tradeability_reachability_history.jsonl",
            "qadam_tradeability_reachability_checks.json",
            "qadam_contract_self_healing_checks.json",
        ),
    ),
    ServiceDefinition(
        service_id="forward_shadow",
        purpose="Observe eligible hypotheses without orders or proof credit.",
        cadence_seconds=300,
        trigger="new_akber_result_or_due_observation",
        ownership="forward_shadow_runner",
        safe_retry_class="idempotent_read",
        recovery_mode="safe_revalidate",
        command_sequence=(("scripts/run_qadam_forward_shadow.py", "--once", "--allow-network"),),
        timeout_seconds=300,
        dependencies=("canonical_tradeability",),
        concurrency_group="research_cpu",
        lock_requirement="research_read_allowed",
        safety_mode="counterfactual_no_order",
        freshness_deadline_seconds=15 * 60,
        prerequisite_artifacts=("qadam_akber_filter_v3_checks.json",),
        read_resources=("price_lake", "edge_registry"),
        write_resources=("learning_plane",),
        generation_artifacts=("qadam_forward_shadow_checks.json",),
    ),
    ServiceDefinition(
        service_id="portfolio_router_review",
        purpose="Refresh portfolio risk and assign exactly one final Router state.",
        cadence_seconds=300,
        trigger="new_shadow_or_market_context",
        ownership="portfolio_risk_and_router_v3",
        safe_retry_class="deterministic_calculation",
        recovery_mode="safe_revalidate",
        command_sequence=(
            ("scripts/check_qadam_portfolio_risk_engine.py",),
            ("scripts/check_qadam_router_v3_paperops.py",),
            ("scripts/check_qadam_experimental_paper_eligibility.py",),
            ("scripts/check_qadam_multi_setup_paperops.py",),
            ("scripts/check_qadam_decision_generation.py",),
            ("scripts/check_qadam_tradeability_consumers.py",),
            ("scripts/check_qadam_layered_market_judgment.py",),
            ("scripts/check_qadam_risk_router_alignment.py",),
        ),
        timeout_seconds=900,
        dependencies=("forward_shadow",),
        concurrency_group="research_cpu",
        lock_requirement="research_read_allowed",
        safety_mode="single_state_router_no_order",
        freshness_deadline_seconds=15 * 60,
        read_resources=("price_lake", "edge_registry", "paper_state"),
        write_resources=("learning_plane",),
        generation_artifacts=(
            "qadam_router_v3_paperops_checks.json",
            "qadam_router_v3_why_not_trading_now.json",
            "qadam_risk_router_alignment_checks.json",
            "qadam_router_root_cause_summary.json",
            "qadam_multi_setup_paperops.json",
            "qadam_decision_dag_checks.json",
            "qadam_downstream_consumer_checks.json",
            "qadam_decision_generation_manifest.json",
            "qadam_decision_generation_receipts.jsonl",
            "qadam_decision_generation_failures.jsonl",
            "qadam_envelope_akber_decisions.jsonl",
            "qadam_envelope_shadow_decisions.jsonl",
            "qadam_envelope_risk_decisions.jsonl",
            "qadam_envelope_router_decisions.jsonl",
            "qadam_layered_market_judgment_checks.json",
            "qadam_layered_market_judgment_certification.json",
            "qadam_delayed_entry_queue.json",
            "qadam_activity_quality_health.json",
        ),
    ),
    ServiceDefinition(
        service_id="active_discovery_trial",
        purpose=(
            "Record the frozen five-market-session discovery trial after each "
            "generation-consistent Router review."
        ),
        cadence_seconds=300,
        trigger="new_router_generation_or_market_session_progress",
        ownership="active_discovery_trial_observer",
        safe_retry_class="deterministic_calculation",
        recovery_mode="safe_revalidate",
        command_sequence=(
            ("scripts/check_qadam_active_discovery_trial.py",),
            ("scripts/check_qadam_discovery_micro_conversion.py",),
        ),
        timeout_seconds=600,
        dependencies=("portfolio_router_review",),
        concurrency_group="projection",
        lock_requirement="research_read_allowed",
        safety_mode="read_only_trial_observation_no_trade_authority",
        read_resources=(
            "score_plane",
            "edge_registry",
            "learning_plane",
            "paper_state",
        ),
        write_resources=("dashboard_projection",),
        generation_artifacts=(
            "qadam_active_discovery_trial_status.json",
            "qadam_active_discovery_trial_evaluations.jsonl",
            "qadam_active_discovery_trial_sessions.jsonl",
            "qadam_active_discovery_trial_dashboard_summary.json",
            "qadam_active_discovery_conversion_funnel.jsonl",
            "qadam_active_discovery_eligible_days.jsonl",
            "qadam_active_discovery_root_causes.jsonl",
            "qadam_active_discovery_trial_certification.json",
            "qadam_active_discovery_trial_checks.json",
            "qadam_discovery_micro_calibration.json",
            "qadam_discovery_micro_conversion_certification.json",
        ),
    ),
    ServiceDefinition(
        service_id="guarded_paperops",
        purpose="Delegate clean handoffs to the existing guarded Alpaca Paper wrapper.",
        cadence_seconds=1200,
        trigger="explicit_release_and_clean_handoff",
        ownership="canonical_paperops_wrapper_only",
        safe_retry_class="no_automatic_retry",
        recovery_mode="guarded_paperops",
        command_sequence=(("scripts/run_paperops_autonomous_pass.py",),),
        timeout_seconds=1200,
        dependencies=("portfolio_router_review",),
        concurrency_group="paperops",
        lock_requirement="explicit_research_lock_release_required",
        safety_mode="guarded_alpaca_paper_wrapper_only",
        paperops_dependency=True,
        latency_sensitive=True,
        read_resources=("edge_registry", "learning_plane"),
        write_resources=("paper_state", "dashboard_projection"),
        generation_artifacts=("paperops_autonomous_pass_summary.json",),
    ),
    ServiceDefinition(
        service_id="paper_lifecycle_poll",
        purpose="Poll mirrored paper orders and positions without creating new orders.",
        cadence_seconds=300,
        trigger="open_or_pending_paper_lifecycle",
        ownership="paper_lifecycle_poller",
        safe_retry_class="idempotent_read",
        recovery_mode="safe_revalidate",
        command_sequence=(
            ("scripts/check_paperops_paper_lifecycle_poller.py", "--poll-paper-orders"),
            ("scripts/check_qadam_paper_lineage_and_proof.py",),
            ("scripts/check_qadam_lifecycle_control_plane.py",),
        ),
        integration_probe_command_sequence=(
            ("scripts/check_paperops_paper_lifecycle_poller.py",),
            ("scripts/check_qadam_paper_lineage_and_proof.py",),
            ("scripts/check_qadam_lifecycle_control_plane.py",),
        ),
        timeout_seconds=300,
        dependencies=(),
        concurrency_group="paper_read",
        lock_requirement="paper_read_only_allowed",
        safety_mode="alpaca_paper_get_only_no_mutation",
        latency_sensitive=True,
        write_resources=("paper_state",),
        generation_artifacts=(
            "paperops_paper_lifecycle_poller.json",
            "qadam_paper_lineage_and_proof_checks.json",
            "qadam_lifecycle_control_plane_checks.json",
        ),
    ),
    ServiceDefinition(
        service_id="learning_attribution",
        purpose="Refresh outcome attribution and learning records without applying proposals.",
        cadence_seconds=86400,
        trigger="new_outcome_or_daily_deadline",
        ownership="paper_lineage_and_learning_cycle",
        safe_retry_class="deterministic_calculation",
        recovery_mode="safe_revalidate",
        command_sequence=(
            ("scripts/check_qadam_paper_lineage_and_proof.py",),
            ("scripts/check_qadam_experimental_paper_trial.py",),
            ("scripts/check_qadam_outcome_learning_promotion.py",),
            ("scripts/check_qadam_graph_outcome_learning.py",),
            ("scripts/check_qadam_strategy_challenger_tournament.py",),
            ("scripts/check_qadam_learning_cycle_view_model.py",),
            ("scripts/check_qadam_improvement_pipeline_view_model.py",),
        ),
        timeout_seconds=600,
        dependencies=(),
        concurrency_group="research_cpu",
        lock_requirement="research_read_allowed",
        safety_mode="proposal_only_learning",
        read_resources=("edge_registry", "paper_state"),
        write_resources=("temporal_graph", "learning_plane"),
        generation_artifacts=(
            "qadam_temporal_graph_manifest.json",
            "qadam_temporal_graph_health.json",
            "qadam_learning_cycle_dashboard.json",
            "qadam_improvement_pipeline_dashboard.json",
            "qadam_active_discovery_outcomes.jsonl",
            "qadam_gate_attribution_ledger.jsonl",
            "qadam_strategy_promotion_proposals.jsonl",
            "qadam_strategy_admission_decisions.jsonl",
            "qadam_strategy_version_registry.json",
            "qadam_forward_strategy_tournament.json",
            "qadam_forward_research_freeze_registry.json",
            "qadam_outcome_learning_promotion_checks.json",
            "qadam_graph_outcome_learning_summary.json",
            "qadam_strategy_challenger_tournament.json",
        ),
    ),
    ServiceDefinition(
        service_id="dashboard_refresh",
        purpose="Refresh local operator and dashboard-safe projections.",
        cadence_seconds=240,
        trigger="freshness_deadline_or_upstream_receipt",
        ownership="operator_dashboard_projection",
        safe_retry_class="deterministic_calculation",
        recovery_mode="safe_revalidate",
        command_sequence=(
            ("scripts/check_qadam_dashboard_vnext.py",),
            ("scripts/check_qadam_evidence_fit_visibility.py",),
            ("scripts/check_qsase_dashboard_view_model.py",),
            ("scripts/check_qadam_research_progression_health.py",),
            ("scripts/check_qadam_state_root.py",),
            ("scripts/check_qadam_artifact_ownership.py",),
            ("scripts/check_qadam_resource_locks.py",),
            ("scripts/check_qadam_storage_retention.py",),
            ("scripts/check_qadam_operator_dashboard.py",),
            ("scripts/check_qadam_dashboard_epoch_isolation.py",),
            ("scripts/check_qadam_clean_broker_account_preflight.py", "--report-only"),
            ("scripts/check_qadam_quantum_edge_page_view_model.py",),
            ("scripts/check_qadam_tradeability_public_safety.py",),
            ("scripts/check_qadam_catc_real_market_soak.py",),
            ("scripts/check_qadam_catc_dashboard_projection.py",),
            ("scripts/check_qadam_operator_service.py", "--report-only"),
            ("scripts/export_cockpit_status.py", "--no-landing-copy"),
        ),
        integration_probe_command_sequence=(
            ("scripts/check_qadam_dashboard_vnext.py",),
            ("scripts/check_qadam_evidence_fit_visibility.py",),
            ("scripts/check_qadam_research_progression_health.py",),
            ("scripts/check_qadam_operator_dashboard.py",),
            ("scripts/export_cockpit_status.py", "--no-landing-copy"),
        ),
        timeout_seconds=600,
        dependencies=(),
        concurrency_group="projection",
        lock_requirement="research_read_allowed",
        safety_mode="read_only_local_projection",
        freshness_deadline_seconds=360,
        read_resources=(
            "source_lake",
            "price_lake",
            "point_in_time_evidence",
            "score_plane",
            "label_plane",
            "edge_registry",
            "temporal_graph",
            "learning_plane",
            "paper_state",
        ),
        write_resources=("dashboard_projection",),
        generation_artifacts=(
            "qadam_research_progression_health.json",
            "qadam_research_progression_health_history.jsonl",
            "qadam_research_progression_health_checks.json",
            "qadam_operator_dashboard_view_model.json",
            "qadam_evidence_fit_dashboard_summary.json",
            "qadam_strategy_conversion_funnel.json",
            "qadam_material_research_changes.jsonl",
            "qadam_evidence_fit_notification_candidates.jsonl",
            "qadam_evidence_fit_visibility_checks.json",
            "qadam_active_edge_research_certification.json",
            "qadam_active_edge_research_checks.json",
            "qadam_quantum_edge_wave_f_public_view.json",
            "qadam_quantum_edge_wave_g_hybrid_loop.json",
            "qadam_quantum_edge_wave_h_crude_oil_certification.json",
            "qadam_quantum_edge_page.json",
            "qadam_qeg_dashboard_projection.json",
            "qadam_qeg_telegram_projection.json",
            "qadam_qeg_curated_resource_registry.json",
            "qadam_qeg_operator_reliability.json",
            "qadam_qeg_active_discovery_trial.json",
            "qadam_tradeability_compiler_dashboard_summary.json",
            "qadam_agent_gauntlet_dashboard_summary.json",
            "qadam_tradeability_funnel.json",
            "qadam_tradeability_public_safety_audit.json",
            "qadam_canonical_tradeability_compiler_certification.json",
            "qadam_tradeability_soak_status.json",
            "qadam_tradeability_release_manifest.json",
            "qadam_legacy_removal_audit.json",
            "qadam_ctc_implementation_status.json",
            "qadam_canonical_autonomous_tradeability_dashboard_summary.json",
            "qadam_canonical_autonomous_tradeability_telegram_summary.json",
            "qadam_catc_dashboard_projection_checks.json",
            "qadam_catc_real_market_soak.json",
            "cockpit-status.json",
        ),
    ),
    ServiceDefinition(
        service_id="public_status_publication",
        purpose=(
            "Publish the latest completed dashboard projection through the "
            "optional signed public-status bridge."
        ),
        cadence_seconds=240,
        trigger="new_local_dashboard_generation_or_transport_retry",
        ownership="public_status_bridge",
        safe_retry_class="idempotent_read",
        recovery_mode="safe_revalidate",
        command_sequence=(
            ("scripts/publish_qadam_public_status.py",),
            ("scripts/check_qadam_public_status_bridge.py", "--report-only"),
        ),
        timeout_seconds=180,
        dependencies=("dashboard_refresh",),
        concurrency_group="publication",
        lock_requirement="public_safe_transport_only",
        safety_mode="signed_public_status_transport_no_authority",
        freshness_deadline_seconds=480,
        latency_sensitive=True,
        read_resources=("dashboard_projection",),
        write_resources=("public_status_transport",),
        generation_artifacts=("qadam_public_status_bridge_checks.json",),
    ),
    ServiceDefinition(
        service_id="challenger_research",
        purpose=(
            "Run the frozen challenger family weekly; a reviewed material evidence-version "
            "change may request an explicit supervised run."
        ),
        cadence_seconds=604800,
        trigger="weekly_or_explicit_material_dataset_version_change",
        ownership="research_supervisor",
        safe_retry_class="interrupted_resumable_job",
        recovery_mode="bounded_resume",
        command_sequence=(
            ("scripts/check_qadam_forward_labels.py",),
            ("scripts/check_qadam_statistical_backtest.py",),
            ("scripts/check_qadam_nonlinear_quantum_value.py",),
            ("scripts/check_qadam_edge_registry.py",),
            ("scripts/run_qadam_backtest_completion.py",),
            ("scripts/check_qadam_backtest_completion.py",),
        ),
        timeout_seconds=7200,
        dependencies=("pattern_scoring",),
        # The challenger reads and revalidates the score/label plane. Keep it in
        # the same exclusion group as score generation so that plane cannot
        # change underneath a running validation.
        concurrency_group="research_cpu",
        lock_requirement="research_read_allowed",
        safety_mode="resumable_challenger_research",
        prerequisite_artifacts=("qadam_pattern_score_v3_checks.json",),
        long_running=True,
        read_resources=(
            "source_lake",
            "price_lake",
            "point_in_time_evidence",
            "score_plane",
        ),
        write_resources=("label_plane", "edge_registry", "learning_plane"),
        generation_artifacts=(
            "qadam_forward_labels_checks.json",
            "qadam_statistical_backtest_checks.json",
            "qadam_nonlinear_quantum_value_checks.json",
            "qadam_backtest_completion_checks.json",
            "qadam_edge_registry_checks.json",
        ),
        # Pattern scoring refreshes every five minutes even when its evidence
        # population is unchanged. Keep the dependency for ordering and input
        # readiness, but do not turn every routine score receipt into a full
        # challenger backtest. The weekly cadence or an explicit supervised
        # force-due request owns that expensive wake-up.
        wake_on_dependency_advance=False,
    ),
)


def service_recovery_contract_errors(definition: ServiceDefinition) -> list[str]:
    """Validate that one service has a bounded, fail-closed recovery path."""

    errors: list[str] = []
    mode = definition.recovery_mode
    commands = definition.command_sequence
    flattened = [part for command in commands for part in command]
    if mode not in RECOVERY_MODES:
        errors.append("unknown_recovery_mode")
    if not commands or any(not command for command in commands):
        errors.append("recovery_command_missing")
    if any("live" in part.lower() and "capital" in part.lower() for part in flattened):
        errors.append("live_capital_command_forbidden")

    if mode == "safe_revalidate":
        if definition.long_running:
            errors.append("safe_revalidate_cannot_be_long_running")
        if definition.provider_budget_required:
            errors.append("safe_revalidate_cannot_require_provider_budget")
        if definition.paperops_dependency:
            errors.append("safe_revalidate_cannot_depend_on_paperops")
        if definition.safe_retry_class not in {
            "idempotent_read",
            "deterministic_calculation",
            "interrupted_resumable_job",
        }:
            errors.append("safe_revalidate_retry_class_not_safe")
    elif mode == "bounded_resume":
        if not definition.long_running:
            errors.append("bounded_resume_must_be_long_running")
        if definition.provider_budget_required:
            errors.append("bounded_resume_cannot_require_provider_budget")
        if definition.paperops_dependency:
            errors.append("bounded_resume_cannot_depend_on_paperops")
        if definition.safe_retry_class != "interrupted_resumable_job":
            errors.append("bounded_resume_retry_class_mismatch")
        if definition.timeout_seconds <= 0 or definition.timeout_seconds > 2 * 60 * 60:
            errors.append("bounded_resume_timeout_out_of_range")
    elif mode == "terminal_aware_bounded_resume":
        if not definition.long_running:
            errors.append("terminal_resume_must_be_long_running")
        if not definition.provider_budget_required:
            errors.append("terminal_resume_must_require_provider_budget")
        if definition.paperops_dependency:
            errors.append("terminal_resume_cannot_depend_on_paperops")
        if definition.safe_retry_class != "interrupted_resumable_job":
            errors.append("terminal_resume_retry_class_mismatch")
        if definition.service_id != "historical_source_worker":
            errors.append("terminal_resume_handler_missing")
        if "--max-jobs" not in flattened:
            errors.append("terminal_resume_job_bound_missing")
    elif mode == "guarded_market_conversion":
        if definition.service_id != "open_market_conversion":
            errors.append("guarded_market_conversion_owner_mismatch")
        if not definition.paperops_dependency:
            errors.append("guarded_market_conversion_dependency_missing")
        if not commands or any("--no-paperops" not in command for command in commands):
            errors.append("guarded_market_conversion_no_paperops_flag_missing")
    elif mode == "guarded_paperops":
        if definition.service_id != "guarded_paperops":
            errors.append("guarded_paperops_owner_mismatch")
        if commands != (("scripts/run_paperops_autonomous_pass.py",),):
            errors.append("guarded_paperops_wrapper_mismatch")
        if not definition.paperops_dependency:
            errors.append("guarded_paperops_dependency_missing")

    if mode != "guarded_paperops" and (
        "scripts/run_paperops_autonomous_pass.py" in flattened
    ):
        errors.append("unguarded_paperops_command_forbidden")
    return sorted(set(errors))


def build_recovery_coverage(
    definitions: tuple[ServiceDefinition, ...] = SERVICE_DEFINITIONS,
) -> dict[str, Any]:
    """Prove that detection and bounded recovery cover the same registry."""

    generated_at = now_iso()
    ids = [definition.service_id for definition in definitions]
    duplicate_ids = sorted({service_id for service_id in ids if ids.count(service_id) > 1})
    services: list[dict[str, Any]] = []
    errors: list[str] = []
    for definition in definitions:
        service_errors = service_recovery_contract_errors(definition)
        errors.extend(
            f"service_recovery_contract:{definition.service_id}:{error}"
            for error in service_errors
        )
        services.append(
            {
                "service_id": definition.service_id,
                "recovery_mode": definition.recovery_mode,
                "safe_retry_class": definition.safe_retry_class,
                "long_running": definition.long_running,
                "provider_budget_required": definition.provider_budget_required,
                "paperops_dependency": definition.paperops_dependency,
                "timeout_seconds": definition.timeout_seconds,
                "full_heal_eligible": not service_errors,
                "validation_errors": service_errors,
            }
        )
    errors.extend(f"duplicate_service_id:{service_id}" for service_id in duplicate_ids)
    return {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "qadam_self_healing_recovery_coverage",
        "generated_at": generated_at,
        "status": "passed" if not errors and len(services) == len(definitions) else "blocked",
        "registered_service_count": len(definitions),
        "covered_service_count": sum(row["full_heal_eligible"] for row in services),
        "uncovered_service_count": sum(not row["full_heal_eligible"] for row in services),
        "services": services,
        "validation_errors": sorted(set(errors)),
        "paper_order_created_count": 0,
        "broker_write_count": 0,
        "live_capital_enabled": False,
        "authority": authority_flags(),
    }


def build_and_write_recovery_coverage(
    settings: Settings | None = None,
) -> dict[str, Any]:
    payload = build_recovery_coverage()
    AtomicArtifactStore(runtime_dir(settings)).write_json(
        RECOVERY_COVERAGE_ARTIFACT,
        payload,
    )
    return payload


def operator_service_contract_hash() -> str:
    """Bind reliability evidence to the exact scheduled service contract."""

    return sha256_json([definition.to_dict() for definition in SERVICE_DEFINITIONS])


def _git_output(*arguments: str) -> str:
    try:
        completed = subprocess.run(
            ["git", *arguments],
            cwd=ROOT,
            capture_output=True,
            text=True,
            timeout=15,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        return ""
    return completed.stdout.strip()


OPERATOR_BUILD_PATHS = (
    ".env.example",
    "agents",
    "config",
    "ops",
    "orchestrator",
    "scripts",
    "schemas",
    "pyproject.toml",
    "requirements.txt",
    "requirements-dev.txt",
)


def _operator_build_dirty_records() -> list[dict[str, Any]]:
    """Fingerprint only files that can change the installed operator runtime."""

    lines = _git_output(
        "-c",
        "core.quotePath=false",
        "status",
        "--porcelain=v1",
        "--untracked-files=all",
        "--",
        *OPERATOR_BUILD_PATHS,
    ).splitlines()
    records: list[dict[str, Any]] = []
    for line in sorted(item for item in lines if item):
        path_text = line[3:]
        if " -> " in path_text:
            path_text = path_text.rsplit(" -> ", 1)[-1]
        path = ROOT / path_text
        records.append(
            {
                "state": line[:2],
                "path": path_text,
                "content_sha256": file_sha256(path) if path.is_file() else None,
            }
        )
    return records


def operator_build_dirty_records() -> list[dict[str, Any]]:
    """Return build-relevant changes without including mutable research state."""

    return _operator_build_dirty_records()


def operator_build_identity(settings: Settings | None = None) -> dict[str, Any]:
    dirty_records = _operator_build_dirty_records()
    dependency_paths = [
        path
        for name in ("pyproject.toml", "requirements.txt", "requirements-dev.txt")
        if (path := ROOT / name).is_file()
    ]
    return {
        "git_commit": _git_output("rev-parse", "HEAD") or None,
        "git_branch": _git_output("rev-parse", "--abbrev-ref", "HEAD") or None,
        "dirty_worktree": bool(dirty_records),
        "dirty_path_count": len(dirty_records),
        "dirty_worktree_digest": sha256_json(dirty_records),
        "build_scope": list(OPERATOR_BUILD_PATHS),
        "python_executable": str(Path(sys.executable).resolve()),
        "python_version": sys.version.split()[0],
        "dependency_lock_digest": sha256_json(
            {str(path.relative_to(ROOT)): file_sha256(path) for path in dependency_paths}
        ),
        "service_contract_hash": operator_service_contract_hash(),
        "state_root": str(resolve_state_root(settings)),
        "working_directory": str(ROOT),
        "launchd_template_sha256": file_sha256(LAUNCHD_TEMPLATE),
        "launchd_target_sha256": file_sha256(LAUNCHD_TARGET),
    }


def operator_public_build_identity(identity: dict[str, Any]) -> dict[str, Any]:
    """Project build evidence without exposing local filesystem paths."""

    return {
        key: identity.get(key)
        for key in (
            "git_commit",
            "git_branch",
            "dirty_worktree",
            "dirty_path_count",
            "dirty_worktree_digest",
            "python_version",
            "dependency_lock_digest",
            "service_contract_hash",
            "launchd_template_sha256",
            "launchd_target_sha256",
        )
    } | {
        "python_executable_digest": sha256_json(identity.get("python_executable")),
        "state_root_digest": sha256_json(identity.get("state_root")),
        "working_directory_digest": sha256_json(identity.get("working_directory")),
    }


def _installed_launchd_matches_template() -> bool:
    try:
        expected = LAUNCHD_TEMPLATE.read_text(encoding="utf-8").replace(
            "__QADAM_ROOT__",
            str(ROOT),
        )
        actual = LAUNCHD_TARGET.read_text(encoding="utf-8")
    except OSError:
        return False
    return actual == expected


INTEGRATION_PROBE_SERVICES = (
    "historical_source_worker",
    "source_ingestion",
    "market_price_refresh",
    "execution_context",
    "pattern_scoring",
    "research_evidence_validation",
    "akber_review",
    "qeg_evidence_cycle",
    "qualitative_evidence_cycle",
    "canonical_tradeability",
    "forward_shadow",
    "portfolio_router_review",
    "open_market_conversion",
    "active_discovery_trial",
    "paper_lifecycle_poll",
    "learning_attribution",
    "dashboard_refresh",
)


SOAK_SCENARIOS = (
    ("network_loss", "provider network timeout", "transient_provider_network"),
    ("laptop_sleep", "interrupted after laptop sleep", "interrupted_resumable_job"),
    ("sigterm", "SIGTERM interrupted resumable job", "interrupted_resumable_job"),
    ("provider_429", "HTTP 429 rate limit", "rate_limit"),
    ("malformed_response", "malformed JSON schema response", "parser_schema_drift"),
    ("stale_lock", "stale lock interrupted job", "interrupted_resumable_job"),
    ("disk_threshold", "disk free space below threshold", "disk_resource_pressure"),
    ("local_llm_down", "local LLM provider unavailable", "transient_provider_network"),
    ("frontier_down", "frontier provider unavailable", "transient_provider_network"),
    ("quantum_fallback", "quantum provider unavailable fallback", "transient_provider_network"),
    ("unsafe_route", "live broker endpoint requested", "safety_violation"),
)


def _parse_timestamp(value: Any) -> datetime | None:
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _pid_alive(pid: int) -> bool:
    if pid <= 0:
        return False
    try:
        completed_pid, _status = os.waitpid(pid, os.WNOHANG)
    except ChildProcessError:
        completed_pid = 0
    if completed_pid == pid:
        return False
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    try:
        state = subprocess.run(
            ("ps", "-o", "state=", "-p", str(pid)),
            check=False,
            capture_output=True,
            text=True,
            timeout=2,
        ).stdout.strip()
    except (OSError, subprocess.SubprocessError):
        return True
    if state.startswith("Z"):
        return False
    return True


class OperatorServiceLease:
    """Process-scoped non-blocking file lock with a public-safe lease mirror."""

    def __init__(self, runtime: Path, *, lease_ttl_seconds: int = 180):
        self.runtime = runtime.resolve()
        self.lease_ttl_seconds = lease_ttl_seconds
        self.store = AtomicArtifactStore(self.runtime)
        self._handle: Any = None

    def acquire(self, *, owner_pid: int | None = None) -> tuple[bool, str]:
        pid = owner_pid or os.getpid()
        lock_path = self.runtime / ".qadam_operator_service.lock"
        lock_path.parent.mkdir(parents=True, exist_ok=True)
        handle = lock_path.open("a+", encoding="utf-8")
        try:
            fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            handle.close()
            return False, "active_operator_service_lease_exists"
        self._handle = handle
        generated_at = now_iso()
        existing = read_json(self.runtime / LEASE_ARTIFACT)
        lease = {
            "schema_version": SCHEMA_VERSION,
            "artifact_type": "qadam_operator_service_lease",
            "generated_at": generated_at,
            "status": "active",
            "owner_pid": pid,
            "acquired_at": generated_at,
            "expires_at": (
                datetime.now(timezone.utc) + timedelta(seconds=self.lease_ttl_seconds)
            ).isoformat(),
            "stale_lease_recovered": bool(existing)
            and existing.get("status") == "active"
            and not _pid_alive(int(existing.get("owner_pid") or 0)),
            "build_identity": operator_build_identity(),
            "authority": authority_flags(),
        }
        self.store.write_json(LEASE_ARTIFACT, lease)
        return True, "operator_service_lease_acquired"

    def renew(self, *, owner_pid: int | None = None) -> bool:
        if self._handle is None:
            return False
        pid = owner_pid or os.getpid()
        lease = read_json(self.runtime / LEASE_ARTIFACT)
        if lease.get("status") != "active" or int(lease.get("owner_pid") or 0) != pid:
            return False
        lease["generated_at"] = now_iso()
        lease["expires_at"] = (
            datetime.now(timezone.utc) + timedelta(seconds=self.lease_ttl_seconds)
        ).isoformat()
        self.store.write_json(LEASE_ARTIFACT, lease)
        return True

    def release(self, *, owner_pid: int | None = None, reason: str = "clean_exit") -> bool:
        if self._handle is None:
            return False
        pid = owner_pid or os.getpid()
        lease = read_json(self.runtime / LEASE_ARTIFACT)
        released = int(lease.get("owner_pid") or 0) == pid
        if released:
            lease.update(
                {
                    "generated_at": now_iso(),
                    "status": "released",
                    "release_reason": reason,
                }
            )
            self.store.write_json(LEASE_ARTIFACT, lease)
        fcntl.flock(self._handle.fileno(), fcntl.LOCK_UN)
        self._handle.close()
        self._handle = None
        return released


class OperatorServiceLeaseHeartbeat:
    """Renew the public lease while a long operator job is still running."""

    def __init__(self, lease: OperatorServiceLease, *, interval_seconds: float = 30.0):
        self.lease = lease
        self.interval_seconds = max(0.01, interval_seconds)
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None

    def start(self) -> None:
        if self._thread is not None:
            return
        self._thread = threading.Thread(
            target=self._run,
            name="qadam-operator-lease-heartbeat",
            daemon=True,
        )
        self._thread.start()

    def _run(self) -> None:
        while not self._stop.wait(self.interval_seconds):
            self.lease.renew()

    def stop(self) -> None:
        self._stop.set()
        if self._thread is not None:
            self._thread.join(timeout=max(1.0, self.interval_seconds * 2))
            self._thread = None


class OperatorMaintenanceLock:
    """Mutual exclusion between autonomous cycles and maintenance checks."""

    def __init__(self, runtime: Path):
        self.runtime = runtime.resolve()
        self._handle: Any = None

    def acquire(self, *, blocking: bool) -> tuple[bool, str]:
        lock_path = self.runtime / MAINTENANCE_LOCK_FILENAME
        lock_path.parent.mkdir(parents=True, exist_ok=True)
        handle = lock_path.open("a+", encoding="utf-8")
        flags = fcntl.LOCK_EX if blocking else fcntl.LOCK_EX | fcntl.LOCK_NB
        try:
            fcntl.flock(handle.fileno(), flags)
        except BlockingIOError:
            handle.close()
            return False, "runtime_maintenance_window_active"
        self._handle = handle
        return True, "runtime_maintenance_lock_acquired"

    def release(self) -> bool:
        if self._handle is None:
            return False
        fcntl.flock(self._handle.fileno(), fcntl.LOCK_UN)
        self._handle.close()
        self._handle = None
        return True


def maintenance_request_active(
    runtime: Path,
    *,
    now: datetime | None = None,
    max_age_seconds: int = MAINTENANCE_REQUEST_MAX_AGE_SECONDS,
) -> bool:
    """Return true only for a fresh request owned by a live local process."""

    artifact = read_json(runtime.resolve() / MAINTENANCE_ARTIFACT)
    if artifact.get("status") not in {"requested", "active"}:
        return False
    try:
        generated_at = datetime.fromisoformat(
            str(artifact.get("generated_at") or "").replace("Z", "+00:00")
        )
    except ValueError:
        return False
    if generated_at.tzinfo is None:
        generated_at = generated_at.replace(tzinfo=timezone.utc)
    reference = now or datetime.now(timezone.utc)
    age_seconds = (reference.astimezone(timezone.utc) - generated_at).total_seconds()
    if age_seconds < 0 or age_seconds > max_age_seconds:
        return False
    try:
        owner_pid = int(artifact.get("owner_pid") or 0)
    except (TypeError, ValueError):
        return False
    if owner_pid <= 0:
        return False
    try:
        os.kill(owner_pid, 0)
    except (OSError, ValueError):
        return False
    return True


def classify_failure(message: str, *, status_code: int | None = None) -> str:
    text = str(message or "").lower()
    if any(
        token in text
        for token in (
            "resource_lock_busy:",
            "score_tape_input_snapshot_unstable:",
            "resource deadlock avoided",
            "errno 11",
            "errno 35",
            "errno 45",
            "temporarily unavailable",
            "stale file handle",
        )
    ):
        return "concurrent_artifact_access"
    if any(
        token in text
        for token in ("live broker", "live capital", "unauthorized write", "safety violation")
    ):
        return "safety_violation"
    if any(
        token in text
        for token in (
            "research_integrity_hold",
            "negative_control_calibration_hold",
            "backtest_negative_control_promotion_gate_breach",
            "completed_score_tape_partition_immutable_mismatch",
            "score_tape_input_snapshot_integrity_hold",
        )
    ):
        return "research_integrity_hold"
    if any(
        token in text
        for token in (
            "receiver_not_configured",
            "public_status_receiver_not_configured",
        )
    ):
        return "optional_transport_unconfigured"
    if status_code == 429 or "429" in text or "rate limit" in text:
        return "rate_limit"
    if re.search(
        r"\b(?:credential(?:s)?|unauthorized|forbidden|token expired|401|403)\b",
        text,
    ):
        return "credential_operator_action"
    if any(
        token in text for token in ("malformed", "schema", "parse", "invalid json", "jsondecode")
    ):
        return "parser_schema_drift"
    if any(token in text for token in (
        "sqlite3.operationalerror: disk i/o error", "unable to open database file",
        "database is locked", "database table is locked",
    )):
        return "database_io_unavailable"
    if "storage_generation_retention_exceeded:" in text:
        return "storage_maintenance_due"
    if any(token in text for token in ("disk", "no space", "resource pressure", "memory pressure")):
        return "disk_resource_pressure"
    if any(token in text for token in ("stale artifact", "freshness deadline", "artifact missing")):
        return "stale_artifact"
    if any(
        token in text
        for token in ("sigterm", "sleep", "interrupted", "stale lock", "resume cursor")
    ):
        return "interrupted_resumable_job"
    if any(
        token in text
        for token in (
            "network",
            "timeout",
            "connection",
            "provider unavailable",
            "market_clock_refresh_failed",
            "alpaca_paper_mirror_refresh_failed",
            "paper_mirror_refresh_failed",
            "dns",
            "transport_error",
            "urlerror",
            "httperror",
        )
    ):
        return "transient_provider_network"
    return "code_defect"


def retry_policy(failure_class: str, *, attempt_count: int = 0) -> dict[str, Any]:
    policies: dict[str, dict[str, Any]] = {
        "database_io_unavailable": {
            "automatic_retry_allowed": attempt_count < 3,
            "maximum_attempts": 3,
            "backoff_seconds": min(30 * (2**attempt_count), 300),
            "circuit_breaker_after_attempts": 3,
            "next_action": "reopen_authoritative_database_without_replaying_broker_writes",
        },
        "storage_maintenance_due": {
            "automatic_retry_allowed": attempt_count < 3,
            "maximum_attempts": 3,
            "backoff_seconds": 60,
            "circuit_breaker_after_attempts": 3,
            "next_action": "run_bounded_generation_retention_then_revalidate",
        },
        "concurrent_artifact_access": {
            "automatic_retry_allowed": attempt_count < 5,
            "maximum_attempts": 5,
            "backoff_seconds": min(5 * (2**attempt_count), 60),
            "circuit_breaker_after_attempts": 5,
            "next_action": "wait_for_resource_lease_then_retry_same_generation",
        },
        "transient_provider_network": {
            "automatic_retry_allowed": attempt_count < 3,
            "maximum_attempts": 3,
            "backoff_seconds": min(30 * (2**attempt_count), 300),
            "circuit_breaker_after_attempts": 3,
            "next_action": "retry_idempotent_read_then_open_circuit",
        },
        "rate_limit": {
            "automatic_retry_allowed": attempt_count < 5,
            "maximum_attempts": 5,
            "backoff_seconds": min(60 * (2**attempt_count), 3600),
            "circuit_breaker_after_attempts": 5,
            "next_action": "respect_provider_retry_after",
        },
        "stale_artifact": {
            "automatic_retry_allowed": attempt_count < 1,
            "maximum_attempts": 1,
            "backoff_seconds": 0,
            "circuit_breaker_after_attempts": 1,
            "next_action": "run_known_safe_refresh_then_validate",
        },
        "interrupted_resumable_job": {
            "automatic_retry_allowed": attempt_count < 1,
            "maximum_attempts": 1,
            "backoff_seconds": 0,
            "circuit_breaker_after_attempts": 1,
            "next_action": "resume_incomplete_idempotent_job_from_checkpoint",
        },
        "research_integrity_hold": {
            "automatic_retry_allowed": False,
            "maximum_attempts": 0,
            "backoff_seconds": None,
            "circuit_breaker_after_attempts": 0,
            "next_action": (
                "quarantine_promotion_continue_observation_and_revalidate_after_evidence_change"
            ),
        },
        "optional_transport_unconfigured": {
            "automatic_retry_allowed": False,
            "maximum_attempts": 0,
            "backoff_seconds": None,
            "circuit_breaker_after_attempts": 0,
            "next_action": "retain_local_projection_and_report_transport_hold",
        },
    }
    policy = policies.get(
        failure_class,
        {
            "automatic_retry_allowed": False,
            "maximum_attempts": 0,
            "backoff_seconds": None,
            "circuit_breaker_after_attempts": 0,
            "next_action": (
                "stop_affected_work_and_require_safety_review"
                if failure_class == "safety_violation"
                else "write_specific_repair_request"
            ),
        },
    )
    return {
        "failure_class": failure_class,
        "attempt_count": attempt_count,
        "safe_idempotent_operations_only": True,
        "paperops_retry_allowed": False,
        "broker_write_retry_allowed": False,
        "code_edit_allowed": False,
        "secret_change_allowed": False,
        "authority_change_allowed": False,
        **policy,
    }


CommandExecutor = Callable[[tuple[str, ...], int], dict[str, Any]]


def _service_definition(service_id: str) -> ServiceDefinition:
    for definition in SERVICE_DEFINITIONS:
        if definition.service_id == service_id:
            return definition
    raise ValueError(f"unknown_operator_service:{service_id}")


def _full_heal_service_ids(service_ids: tuple[str, ...] | list[str]) -> tuple[str, ...]:
    """Return the bounded services the singleton owner may revalidate."""

    requested = {str(service_id) for service_id in service_ids if str(service_id)}
    ordered: list[str] = []
    for definition in SERVICE_DEFINITIONS:
        if definition.service_id not in requested:
            continue
        recovery_errors = service_recovery_contract_errors(definition)
        if recovery_errors:
            raise ValueError(
                "operator_full_heal_service_not_permitted:"
                f"{definition.service_id}:" + ",".join(recovery_errors)
            )
        ordered.append(definition.service_id)
    unknown = requested.difference(ordered)
    if unknown:
        raise ValueError("operator_full_heal_unknown_service:" + ",".join(sorted(unknown)))
    if not ordered:
        raise ValueError("operator_full_heal_service_list_empty")
    return tuple(ordered)


def request_operator_full_heal(
    service_ids: tuple[str, ...] | list[str],
    settings: Settings | None = None,
    *,
    trigger_codes: tuple[str, ...] | list[str] = (),
    requested_by: str = "qadam_reliability_critic",
) -> dict[str, Any]:
    """Ask the active singleton owner to perform one bounded full-heal cycle."""

    runtime = runtime_dir(settings)
    selected = _full_heal_service_ids(service_ids)
    generated_at = now_iso()
    request_id = "operator-full-heal:" + sha256_json(
        {
            "generated_at": generated_at,
            "service_ids": selected,
            "trigger_codes": sorted(str(code) for code in trigger_codes),
            "requested_by": requested_by,
        }
    )[:24]
    payload = {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "qadam_operator_full_heal_request",
        "generated_at": generated_at,
        "request_id": request_id,
        "status": "requested",
        "requested_by": requested_by,
        "operator_service_contract_hash": operator_service_contract_hash(),
        "git_commit": _git_output("rev-parse", "HEAD") or None,
        "service_ids": list(selected),
        "trigger_codes": sorted({str(code) for code in trigger_codes if str(code)}),
        "force_due": True,
        "single_operator_owner_required": True,
        "guarded_paperops_wrapper_only": True,
        "paper_only": True,
        "live_capital_enabled": False,
        "autonomous_code_edit_allowed": False,
        "policy_mutation_allowed": False,
        "forced_trade_allowed": False,
        "authority": authority_flags(),
    }
    AtomicArtifactStore(runtime).write_json(FULL_HEAL_REQUEST_ARTIFACT, payload)
    return payload


def _update_full_heal_request_state(
    runtime: Path,
    request_id: str,
    **updates: Any,
) -> dict[str, Any]:
    """Advance request state without allowing an older owner to overwrite a newer request."""

    with _operator_state_transaction(runtime, CONTROL_STATE_LOCK_FILENAME):
        current = read_json(runtime / FULL_HEAL_REQUEST_ARTIFACT)
        if current.get("request_id") != request_id:
            return {}
        updated = {
            **current,
            **updates,
            "progress_at": now_iso(),
        }
        AtomicArtifactStore(runtime).write_json(FULL_HEAL_REQUEST_ARTIFACT, updated)
    return updated


def pending_operator_full_heal_request(
    settings: Settings | None = None,
    *,
    reference: datetime | None = None,
) -> dict[str, Any]:
    runtime = runtime_dir(settings)
    request = read_json(runtime / FULL_HEAL_REQUEST_ARTIFACT)
    if request.get("status") not in {"requested", "in_progress"} or not request.get(
        "request_id"
    ):
        return {}
    generated_at = _parse_timestamp(request.get("generated_at"))
    now = reference or datetime.now(timezone.utc)
    if generated_at is None:
        return {}
    age_seconds = (now.astimezone(timezone.utc) - generated_at).total_seconds()
    if age_seconds < 0 or age_seconds > FULL_HEAL_REQUEST_MAX_AGE_SECONDS:
        return {}
    if request.get("operator_service_contract_hash") != operator_service_contract_hash():
        return {}
    if request.get("git_commit") != (_git_output("rev-parse", "HEAD") or None):
        return {}
    try:
        _full_heal_service_ids(list(request.get("service_ids") or []))
    except ValueError:
        return {}
    return request


def _command_sequence(
    definition: ServiceDefinition,
    *,
    integration_probe: bool,
) -> tuple[tuple[str, ...], ...]:
    if integration_probe and definition.integration_probe_command_sequence:
        return definition.integration_probe_command_sequence
    return definition.command_sequence


def _display_command(command: tuple[str, ...]) -> list[str]:
    return [".venv/bin/python", *command]


def _sanitize_process_output(value: str, *, limit: int = 2400) -> str:
    text = str(value or "")[-limit:]
    patterns = (
        (r"(?i)(authorization\s*[:=]\s*bearer\s+)[^\s]+", r"\1[REDACTED]"),
        (r"(?i)((?:api[_-]?key|api[_-]?secret|token)\s*[:=]\s*)[^\s]+", r"\1[REDACTED]"),
        (r"\b(?:db-[A-Za-z0-9]{12,}|ghp_[A-Za-z0-9]{20,})\b", "[REDACTED]"),
    )
    for pattern, replacement in patterns:
        text = re.sub(pattern, replacement, text)
    return text


def _default_command_executor(command: tuple[str, ...], timeout_seconds: int) -> dict[str, Any]:
    started = time.monotonic()
    environment = os.environ.copy()
    environment.update(
        {
            "QADAM_OPERATOR_DISPATCH": "1",
            "QADAM_OPERATOR_SAFETY_MODE": "paper_only",
            "QADAM_LIVE_CAPITAL_ENABLED": "false",
        }
    )
    try:
        completed = subprocess.run(
            [sys.executable, *command],
            cwd=ROOT,
            env=environment,
            capture_output=True,
            text=True,
            timeout=timeout_seconds,
            check=False,
        )
        return {
            "returncode": completed.returncode,
            "stdout": _sanitize_process_output(completed.stdout),
            "stderr": _sanitize_process_output(completed.stderr),
            "duration_seconds": round(time.monotonic() - started, 6),
            "timed_out": False,
        }
    except subprocess.TimeoutExpired as exc:
        return {
            "returncode": 124,
            "stdout": _sanitize_process_output(str(exc.stdout or "")),
            "stderr": _sanitize_process_output(f"timeout after {timeout_seconds}s"),
            "duration_seconds": round(time.monotonic() - started, 6),
            "timed_out": True,
        }


def _result_is_evidence_hold(result: dict[str, Any]) -> bool:
    output = f"{result.get('stdout', '')}\n{result.get('stderr', '')}".lower()
    hold_states = (
        "status=evidence_maturing",
        "status=hold",
        "status=blocked_evidence_maturing",
        "status=complete_for_supported_sources",
        "status=running_idle_no_eligible_hypothesis",
    )
    return (
        int(result.get("returncode") or 0) != 0
        and "validation_error_count=0" in output
        and any(state in output for state in hold_states)
    )


def _result_is_optional_publication_transport_hold(
    command: tuple[str, ...], result: dict[str, Any]
) -> bool:
    if not command or command[0] != "scripts/publish_qadam_public_status.py":
        return False
    output = f"{result.get('stdout', '')}\n{result.get('stderr', '')}".lower()
    credential_status = re.search(r"http_status_(?:401|403)\b", output)
    return (
        int(result.get("returncode") or 0) != 0
        and "public_status_publish_status=degraded" in output
        and (
            "public_status_reason=transport_error:" in output
            or "receiver_not_configured" in output
            or "public_status_receiver_not_configured" in output
        )
        and credential_status is None
    )


def _publish_service_generations(
    runtime: Path,
    definition: ServiceDefinition,
    command_results: list[dict[str, Any]],
) -> dict[str, str]:
    registry_path = ROOT / "config" / "qadam_runtime_artifact_ownership.json"
    try:
        registry = json.loads(registry_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise GenerationError("artifact_ownership_registry_unreadable") from exc
    ownership_records = {
        str(record.get("artifact") or ""): record
        for record in registry.get("artifacts") or []
        if isinstance(record, dict)
    }
    changed_by_resource: dict[str, list[str]] = {}
    for name in definition.generation_artifacts:
        path = runtime / name
        if not path.is_file():
            conflict_pattern = f"{path.stem} [0-9]*{path.suffix}"
            if any(runtime.glob(conflict_pattern)):
                raise GenerationError(f"generation_artifact_canonical_name_conflict:{name}")
            continue
        ownership = ownership_records.get(name)
        if ownership is None:
            raise GenerationError(f"generation_artifact_ownership_missing:{name}")
        authorized = set(ownership.get("authorized_invokers") or ())
        if definition.service_id not in authorized:
            raise GenerationError(f"generation_artifact_invoker_not_authorized:{name}")
        resource = str(ownership.get("logical_resource") or "")
        producer = str(ownership.get("producer") or "")
        if resource not in (*definition.write_resources, *definition.append_resources):
            raise GenerationError(f"generation_artifact_resource_not_claimed:{name}")
        if not producer:
            raise GenerationError(f"generation_artifact_producer_missing:{name}")
        changed_by_resource.setdefault(resource, []).append(name)
    if not changed_by_resource:
        return {}
    generations: dict[str, str] = {}
    removed_generations: dict[str, list[str]] = {}
    for resource in sorted(changed_by_resource):
        resource_records = {
            name: record
            for name, record in ownership_records.items()
            if record.get("logical_resource") == resource
        }
        files = {
            Path(name).name: runtime / name
            for name in resource_records
            if (runtime / name).is_file()
        }
        if not files:
            raise GenerationError(f"generation_resource_has_no_files:{resource}")
        generation_store = ArtifactGenerationStore(runtime, resource)
        reference = generation_store.publish_files(
            files,
            producer=definition.service_id,
            provenance={
                "authorized_invoker": definition.service_id,
                "changed_artifacts": sorted(changed_by_resource[resource]),
                "artifact_owners": {
                    name: resource_records[name].get("producer") for name in sorted(files)
                },
                "service_contract_hash": operator_service_contract_hash(),
                "commands": [record.get("command") for record in command_results],
            },
            # Published generations must remain immutable even if a legacy
            # producer still rewrites its runtime file in place.
            copy_mode="copy",
        )
        generations[resource] = reference.generation_id
        removed = generation_store.collect(retain=3)
        if removed:
            removed_generations[resource] = removed
    research_retention: dict[str, Any] | None = None
    if {"score_plane", "label_plane"}.intersection(generations):
        research_retention = prune_research_generations(runtime, apply=True)
    if removed_generations or (
        research_retention
        and (
            int(research_retention.get("obsolete_score_file_count") or 0)
            or int(research_retention.get("obsolete_label_root_count") or 0)
        )
    ):
        append_jsonl_durable(
            runtime / STORAGE_MAINTENANCE_LEDGER_ARTIFACT,
            {
                "schema_version": SCHEMA_VERSION,
                "artifact_type": "qadam_storage_generation_collection_event",
                "generated_at": now_iso(),
                "service_id": definition.service_id,
                "removed_generations": removed_generations,
                "research_retention": research_retention,
                "paper_order_created_count": 0,
                "broker_write_count": 0,
                "authority": authority_flags(),
            },
        )
    return generations


def _resolve_input_generation_ids(
    runtime: Path,
    definition: ServiceDefinition,
) -> dict[str, str | None]:
    resolved: dict[str, str | None] = {}
    for resource in definition.read_resources:
        try:
            resolved[resource] = (
                ArtifactGenerationStore(
                    runtime,
                    resource,
                )
                .resolve_current()
                .generation_id
            )
        except GenerationError:
            resolved[resource] = None
    return resolved


def _execute_service_synchronously(
    definition: ServiceDefinition,
    *,
    runtime: Path | None = None,
    executor: CommandExecutor | None = None,
    integration_probe: bool = False,
) -> dict[str, Any]:
    runtime = (runtime or runtime_dir()).resolve()
    execute = executor or _default_command_executor
    command_results: list[dict[str, Any]] = []
    state = "completed"
    generations: dict[str, str] = {}
    input_generations: dict[str, str | None] = {}
    mixed_generation_join_count = 0
    try:
        with ResourceLease(
            runtime,
            service_id=definition.service_id,
            claims=definition.resource_claims(),
            timeout_seconds=definition.resource_lock_timeout_seconds,
        ):
            input_generations = _resolve_input_generation_ids(runtime, definition)
            for command in _command_sequence(
                definition,
                integration_probe=integration_probe,
            ):
                if not command or not (ROOT / command[0]).is_file():
                    result = {
                        "returncode": 127,
                        "stdout": "",
                        "stderr": (
                            f"approved runner missing: {command[0] if command else 'empty'}"
                        ),
                        "duration_seconds": 0.0,
                        "timed_out": False,
                    }
                else:
                    result = execute(command, definition.timeout_seconds)
                evidence_hold = _result_is_evidence_hold(result)
                transport_hold = _result_is_optional_publication_transport_hold(command, result)
                accepted_hold = evidence_hold or transport_hold
                command_results.append(
                    {
                        "command": _display_command(command),
                        "returncode": int(result.get("returncode") or 0),
                        "duration_seconds": float(result.get("duration_seconds") or 0.0),
                        "timed_out": result.get("timed_out") is True,
                        "stdout_tail": _sanitize_process_output(str(result.get("stdout") or "")),
                        "stderr_tail": _sanitize_process_output(str(result.get("stderr") or "")),
                        "evidence_hold_accepted": evidence_hold,
                        "optional_transport_hold_accepted": transport_hold,
                    }
                )
                if int(result.get("returncode") or 0) != 0 and not accepted_hold:
                    state = "failed"
                    break
                if accepted_hold:
                    state = (
                        "completed_with_transport_hold"
                        if transport_hold
                        else "completed_with_evidence_hold"
                    )
            final_input_generations = _resolve_input_generation_ids(runtime, definition)
            mixed_generation_join_count = sum(
                final_input_generations.get(resource) != generation_id
                for resource, generation_id in input_generations.items()
            )
            if mixed_generation_join_count:
                raise GenerationError(
                    f"input_generation_changed_during_execution:{definition.service_id}"
                )
            if state != "failed":
                generations = _publish_service_generations(
                    runtime,
                    definition,
                    command_results,
                )
    except ResourceLockBusy as exc:
        state = "deferred_resource_busy"
        command_results.append(
            {
                "command": ["resource-lease", definition.service_id],
                "returncode": 75,
                "duration_seconds": 0.0,
                "timed_out": False,
                "stdout_tail": "",
                "stderr_tail": str(exc),
                "evidence_hold_accepted": True,
                "optional_transport_hold_accepted": False,
            }
        )
    except (GenerationError, OSError, ValueError) as exc:
        state = "failed"
        command_results.append(
            {
                "command": ["artifact-generation-publish", definition.service_id],
                "returncode": 74,
                "duration_seconds": 0.0,
                "timed_out": False,
                "stdout_tail": "",
                "stderr_tail": f"{exc.__class__.__name__}: {exc}",
                "evidence_hold_accepted": False,
                "optional_transport_hold_accepted": False,
            }
        )
    return {
        "state": state,
        "command_results": command_results,
        "generation_ids": generations,
        "input_generation_ids": input_generations,
        "input_generation_binding_complete": all(
            generation_id is not None for generation_id in input_generations.values()
        ),
        "mixed_generation_join_count": mixed_generation_join_count,
        "duration_seconds": round(
            sum(float(record.get("duration_seconds") or 0.0) for record in command_results),
            6,
        ),
    }


_SUCCESSFUL_RECEIPT_STATES = {
    "completed",
    "completed_with_evidence_hold",
    "completed_with_transport_hold",
    "worker_completed",
}

_HISTORICAL_SOURCE_TERMINAL_JOB_STATES = frozenset(
    {
        "complete",
        "unavailable_classified",
    }
)


def _empty_receipt_index() -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "qadam_operator_service_receipt_index",
        "generated_at": now_iso(),
        "indexed_size_bytes": 0,
        "receipt_count": 0,
        "suppressed_repeat_count": 0,
        "latest_receipts": {},
        "latest_successful_receipts": {},
        "last_persisted_at": {},
    }


def _apply_receipt_to_index(
    index: dict[str, Any], receipt: dict[str, Any], *, persisted: bool
) -> None:
    service_id = str(receipt.get("service_id") or "")
    if not service_id:
        return
    latest = index.setdefault("latest_receipts", {})
    successful = index.setdefault("latest_successful_receipts", {})
    latest[service_id] = receipt
    if receipt.get("state") in _SUCCESSFUL_RECEIPT_STATES:
        successful[service_id] = receipt
    if persisted:
        persisted_at = receipt.get("completed_at") or receipt.get("generated_at")
        if persisted_at:
            index.setdefault("last_persisted_at", {})[service_id] = persisted_at


def _refresh_receipt_index_unlocked(runtime: Path) -> dict[str, Any]:
    ledger_path = runtime / RECEIPTS_ARTIFACT
    index_path = runtime / RECEIPT_INDEX_ARTIFACT
    index = read_json(index_path)
    if index.get("artifact_type") != "qadam_operator_service_receipt_index":
        index = _empty_receipt_index()
    try:
        ledger_size = ledger_path.stat().st_size
    except OSError:
        ledger_size = 0
    indexed_size = int(index.get("indexed_size_bytes") or 0)
    if indexed_size < 0 or indexed_size > ledger_size:
        index = _empty_receipt_index()
        indexed_size = 0
    if ledger_size > indexed_size:
        with ledger_path.open("rb") as handle:
            handle.seek(indexed_size)
            for encoded in handle:
                try:
                    payload = json.loads(encoded.decode("utf-8"))
                except (UnicodeDecodeError, json.JSONDecodeError):
                    continue
                if not isinstance(payload, dict):
                    continue
                _apply_receipt_to_index(index, payload, persisted=True)
                index["receipt_count"] = int(index.get("receipt_count") or 0) + 1
            index["indexed_size_bytes"] = handle.tell()
    index["generated_at"] = now_iso()
    AtomicArtifactStore(runtime).write_json(RECEIPT_INDEX_ARTIFACT, index)
    return index


def _receipt_index(runtime: Path) -> dict[str, Any]:
    lock_path = runtime / RECEIPT_INDEX_LOCK_FILENAME
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    with lock_path.open("a+", encoding="utf-8") as lock_handle:
        fcntl.flock(lock_handle.fileno(), fcntl.LOCK_EX)
        try:
            return _refresh_receipt_index_unlocked(runtime)
        finally:
            fcntl.flock(lock_handle.fileno(), fcntl.LOCK_UN)


def _last_receipts(runtime: Path) -> dict[str, dict[str, Any]]:
    return dict(_receipt_index(runtime).get("latest_receipts") or {})


def _last_successful_receipts(runtime: Path) -> dict[str, dict[str, Any]]:
    return dict(_receipt_index(runtime).get("latest_successful_receipts") or {})


def _same_skip_state(previous: dict[str, Any], receipt: dict[str, Any]) -> bool:
    return (
        previous.get("state") == receipt.get("state") == "skipped"
        and previous.get("skip_reason") == receipt.get("skip_reason")
        and previous.get("detail") == receipt.get("detail")
        and previous.get("integration_probe") == receipt.get("integration_probe")
    )


def _append_receipt(runtime: Path, receipt: dict[str, Any]) -> None:
    # Bind work to the running lease, not whatever checkout is present later.
    lease = read_json(runtime / LEASE_ARTIFACT)
    receipt["operator_build_identity"] = (
        lease.get("build_identity") or {} if lease.get("owner_pid") == os.getpid() else {}
    )
    lock_path = runtime / RECEIPT_INDEX_LOCK_FILENAME
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    with lock_path.open("a+", encoding="utf-8") as lock_handle:
        fcntl.flock(lock_handle.fileno(), fcntl.LOCK_EX)
        try:
            index = _refresh_receipt_index_unlocked(runtime)
            service_id = str(receipt.get("service_id") or "")
            previous = (index.get("latest_receipts") or {}).get(service_id, {})
            last_persisted = _parse_timestamp(
                (index.get("last_persisted_at") or {}).get(service_id)
            )
            generated_at = _parse_timestamp(receipt.get("generated_at"))
            suppress_repeat = bool(
                service_id
                and _same_skip_state(previous, receipt)
                and last_persisted is not None
                and generated_at is not None
                and (generated_at - last_persisted).total_seconds()
                < REPEATED_SKIP_AUDIT_INTERVAL_SECONDS
            )
            if suppress_repeat:
                _apply_receipt_to_index(index, receipt, persisted=False)
                index["suppressed_repeat_count"] = (
                    int(index.get("suppressed_repeat_count") or 0) + 1
                )
                index["generated_at"] = now_iso()
                AtomicArtifactStore(runtime).write_json(RECEIPT_INDEX_ARTIFACT, index)
                return
            append_jsonl_durable(runtime / RECEIPTS_ARTIFACT, receipt)
            _apply_receipt_to_index(index, receipt, persisted=True)
            index["receipt_count"] = int(index.get("receipt_count") or 0) + 1
            try:
                index["indexed_size_bytes"] = (runtime / RECEIPTS_ARTIFACT).stat().st_size
            except OSError:
                index["indexed_size_bytes"] = int(index.get("indexed_size_bytes") or 0)
            index["generated_at"] = now_iso()
            AtomicArtifactStore(runtime).write_json(RECEIPT_INDEX_ARTIFACT, index)
        finally:
            fcntl.flock(lock_handle.fileno(), fcntl.LOCK_UN)
    service_id = str(receipt.get("service_id") or "unknown")
    try:
        domain = service_domain(service_id)
    except ValueError:
        domain = "unregistered"
    ControlPlaneStore(runtime / "qadam-control-plane.sqlite3").record_service_run(
        run_id=str(receipt.get("receipt_id") or sha256_json(receipt)),
        service_id=service_id,
        domain=domain,
        status=str(receipt.get("state") or "unknown"),
        payload=receipt,
        started_at=str(receipt.get("started_at") or receipt.get("generated_at") or now_iso()),
        completed_at=(
            str(receipt.get("completed_at")) if receipt.get("completed_at") else None
        ),
    )


def _next_due_at(definition: ServiceDefinition, receipt: dict[str, Any] | None) -> str:
    completed = _parse_timestamp((receipt or {}).get("completed_at"))
    if completed is None:
        return now_iso()
    return (completed + timedelta(seconds=definition.cadence_seconds)).isoformat()


def _is_due(
    definition: ServiceDefinition,
    receipt: dict[str, Any] | None,
    *,
    timestamp: datetime,
) -> bool:
    if not receipt:
        return True
    due_at = _parse_timestamp(_next_due_at(definition, receipt))
    return due_at is None or due_at <= timestamp


def _dependency_advanced(
    definition: ServiceDefinition,
    successful: dict[str, dict[str, Any]],
    cycle_successes: set[str],
) -> bool:
    """Run a dependent service whenever an upstream result is newer."""

    if not definition.wake_on_dependency_advance:
        return False
    if any(dependency in cycle_successes for dependency in definition.dependencies):
        return True
    own_completed = _parse_timestamp(
        (successful.get(definition.service_id) or {}).get("completed_at")
    )
    if own_completed is None:
        return False
    for dependency in definition.dependencies:
        dependency_completed = _parse_timestamp(
            (successful.get(dependency) or {}).get("completed_at")
        )
        if dependency_completed is not None and dependency_completed > own_completed:
            return True
    return False


def _cycle_material_change_state(
    receipts: list[dict[str, Any]], service_id: str
) -> bool | None:
    for receipt in reversed(receipts):
        if receipt.get("service_id") != service_id:
            continue
        output = "\n".join(
            f"{row.get('stdout_tail', '')}\n{row.get('stderr_tail', '')}"
            for row in receipt.get("command_results", [])
            if isinstance(row, dict)
        ).lower()
        if "material_change_detected=false" in output:
            return False
        if "material_change_detected=true" in output:
            return True
        return None
    return None


def _market_is_open(timestamp: datetime) -> bool:
    local = timestamp.astimezone(ZoneInfo("America/New_York"))
    if local.weekday() >= 5:
        return False
    minute = local.hour * 60 + local.minute
    return (9 * 60 + 30) <= minute < 16 * 60


def _provider_budget_available(runtime: Path) -> bool:
    available, _detail = provider_budget_available(runtime)
    return available


def _prerequisites_fresh(
    runtime: Path,
    definition: ServiceDefinition,
    *,
    timestamp: datetime,
) -> tuple[bool, list[str]]:
    stale: list[str] = []
    for filename in definition.prerequisite_artifacts:
        path = runtime / filename
        payload = read_json(path)
        generated = _parse_timestamp(payload.get("generated_at")) if payload else None
        if not path.is_file() or generated is None:
            stale.append(filename)
            continue
        if (timestamp - generated).total_seconds() > definition.prerequisite_max_age_seconds:
            stale.append(filename)
    return not stale, stale


def _paper_release_state(runtime: Path) -> tuple[dict[str, Any], bool]:
    validated = read_json(runtime / RELEASE_ARTIFACT)
    experimental = read_json(runtime / EXPERIMENTAL_RELEASE_ARTIFACT)
    effective = bool(
        validated.get("release_effective") is True
        or experimental.get("experimental_paper_release_effective") is True
    )
    return (
        experimental
        if experimental.get("experimental_paper_release_effective") is True
        else validated,
        effective,
    )


def _service_terminal_idle_state(
    runtime: Path,
    definition: ServiceDefinition,
) -> dict[str, Any]:
    """Return immutable no-work evidence for a completed bounded service.

    Historical acquisition is resumable while jobs remain, but once every
    reviewed partition is complete or honestly unavailable it is no longer a
    continuously expiring live worker. A changed manifest automatically removes
    this terminal state and makes the worker schedulable again.
    """

    if definition.service_id != "historical_source_worker":
        return {"active": False}
    acquisition = read_json(runtime / "qadam_source_history_acquisition.json")
    manifest = read_json(runtime / "qadam_source_backfill_manifest.json")
    jobs = [row for row in list(manifest.get("jobs") or []) if isinstance(row, dict)]
    terminal_job_count = sum(
        str(row.get("status") or "") in _HISTORICAL_SOURCE_TERMINAL_JOB_STATES
        for row in jobs
    )
    active = bool(
        acquisition.get("status") == "complete_for_supported_sources"
        and not list(acquisition.get("errors") or [])
        and jobs
        and terminal_job_count == len(jobs)
    )
    return {
        "active": active,
        "reason": "historical_coverage_complete_for_supported_sources" if active else None,
        "evidence_generated_at": acquisition.get("generated_at"),
        "job_count": len(jobs),
        "terminal_job_count": terminal_job_count,
        "manifest_digest": sha256_json(
            [
                {
                    "job_id": row.get("job_id"),
                    "status": row.get("status"),
                    "checksum": row.get("checksum"),
                }
                for row in jobs
            ]
        )
        if jobs
        else None,
    }


@contextmanager
def _operator_state_transaction(runtime: Path, lock_filename: str):
    lock_path = runtime / lock_filename
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    with lock_path.open("a+", encoding="utf-8") as lock_handle:
        fcntl.flock(lock_handle.fileno(), fcntl.LOCK_EX)
        try:
            yield
        finally:
            fcntl.flock(lock_handle.fileno(), fcntl.LOCK_UN)


def _worker_state_payload(records: dict[str, Any]) -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "qadam_operator_workers",
        "generated_at": now_iso(),
        "workers": records,
        "authority": authority_flags(),
    }


_TERMINAL_WORKER_RECEIPT_STATES = frozenset(
    {
        "worker_completed",
        "worker_completed_pending_circuit_confirmation",
        "worker_deferred_resource_busy",
        "failed",
    }
)


def _reap_finished_children() -> None:
    while True:
        try:
            completed_pid, _status = os.waitpid(-1, os.WNOHANG)
        except ChildProcessError:
            return
        if completed_pid == 0:
            return


def _terminal_worker_receipt(
    runtime: Path,
    *,
    service_id: str,
    receipt_id: str,
) -> dict[str, Any] | None:
    latest = (_receipt_index(runtime).get("latest_receipts") or {}).get(service_id, {})
    if (
        latest.get("receipt_id") == receipt_id
        and latest.get("state") in _TERMINAL_WORKER_RECEIPT_STATES
    ):
        return latest
    for receipt in reversed(read_jsonl(runtime / RECEIPTS_ARTIFACT)):
        if (
            receipt.get("receipt_id") == receipt_id
            and receipt.get("state") in _TERMINAL_WORKER_RECEIPT_STATES
        ):
            return receipt
    return None


def _read_workers_unlocked(runtime: Path) -> tuple[dict[str, Any], bool]:
    payload = read_json(runtime / WORKERS_ARTIFACT)
    records = payload.get("workers") if isinstance(payload.get("workers"), dict) else {}
    changed = False
    for service_id, record in records.items():
        if record.get("state") != "running":
            continue
        if not _pid_alive(int(record.get("pid") or 0)):
            receipt = _terminal_worker_receipt(
                runtime,
                service_id=service_id,
                receipt_id=str(record.get("receipt_id") or ""),
            )
            if receipt is not None:
                record.update(
                    {
                        "state": receipt["state"],
                        "completed_at": receipt.get("completed_at")
                        or receipt.get("generated_at")
                        or now_iso(),
                        "exit_code": 1 if receipt.get("state") == "failed" else 0,
                        "why": "terminal_receipt_reconciled_after_worker_exit",
                    }
                )
            else:
                record.update(
                    {
                        "state": "interrupted",
                        "completed_at": now_iso(),
                        "failure_class": "interrupted_resumable_job",
                        "why": "worker_pid_no_longer_active_before_terminal_receipt",
                    }
                )
            changed = True
    return records, changed


def _workers(runtime: Path) -> dict[str, Any]:
    _reap_finished_children()
    with _operator_state_transaction(runtime, WORKER_STATE_LOCK_FILENAME):
        records, changed = _read_workers_unlocked(runtime)
        if changed:
            AtomicArtifactStore(runtime).write_json(
                WORKERS_ARTIFACT,
                _worker_state_payload(records),
            )
        return records


def _write_workers(runtime: Path, records: dict[str, Any]) -> None:
    with _operator_state_transaction(runtime, WORKER_STATE_LOCK_FILENAME):
        AtomicArtifactStore(runtime).write_json(
            WORKERS_ARTIFACT,
            _worker_state_payload(records),
        )


def _set_worker_record(
    runtime: Path,
    service_id: str,
    record: dict[str, Any],
    *,
    expected_receipt_id: str | None = None,
) -> dict[str, Any]:
    with _operator_state_transaction(runtime, WORKER_STATE_LOCK_FILENAME):
        records, _changed = _read_workers_unlocked(runtime)
        current = records.get(service_id, {})
        if expected_receipt_id and current.get("receipt_id") != expected_receipt_id:
            return current
        records[service_id] = record
        AtomicArtifactStore(runtime).write_json(
            WORKERS_ARTIFACT,
            _worker_state_payload(records),
        )
        return record


def _active_concurrency_groups(runtime: Path) -> set[str]:
    return {
        str(record.get("concurrency_group"))
        for record in _workers(runtime).values()
        if record.get("state") == "running" and _pid_alive(int(record.get("pid") or 0))
    }


def _active_worker_service_ids(runtime: Path) -> set[str]:
    return {
        str(record.get("service_id"))
        for record in _workers(runtime).values()
        if record.get("state") == "running" and _pid_alive(int(record.get("pid") or 0))
    }


def _resource_conflicts_with_active_workers(
    definition: ServiceDefinition,
    active_worker_service_ids: set[str],
) -> list[str]:
    conflicts: list[str] = []
    for service_id in sorted(active_worker_service_ids):
        active = _service_definition(service_id)
        if not claims_are_compatible(
            definition.resource_claims(),
            active.resource_claims(),
        ):
            conflicts.append(service_id)
    return conflicts


def _launch_resumable_worker(
    runtime: Path,
    definition: ServiceDefinition,
    *,
    receipt_id: str,
) -> dict[str, Any]:
    log_path = runtime / f"qadam-operator-worker-{definition.service_id}.log"
    log_path.parent.mkdir(parents=True, exist_ok=True)
    started_at = now_iso()
    launching_record = {
        "service_id": definition.service_id,
        "receipt_id": receipt_id,
        "pid": None,
        "state": "launching",
        "started_at": started_at,
        "concurrency_group": definition.concurrency_group,
        "resume_required": True,
        "command": [
            ".venv/bin/python",
            "scripts/run_qadam_operator_worker.py",
            "--service-id",
            definition.service_id,
        ],
        "log_path": str(log_path.relative_to(ROOT)),
        "paper_order_created_count": 0,
        "broker_write_count": 0,
    }
    _set_worker_record(runtime, definition.service_id, launching_record)
    with log_path.open("a", encoding="utf-8") as log:
        process = subprocess.Popen(
            [
                sys.executable,
                str(WORKER_RUNNER),
                "--service-id",
                definition.service_id,
                "--receipt-id",
                receipt_id,
            ],
            cwd=ROOT,
            env={
                **os.environ,
                "QADAM_OPERATOR_DISPATCH": "1",
                "QADAM_OPERATOR_SAFETY_MODE": "paper_only",
                "QADAM_LIVE_CAPITAL_ENABLED": "false",
            },
            stdin=subprocess.DEVNULL,
            stdout=log,
            stderr=log,
            start_new_session=True,
        )
    current = _workers(runtime).get(definition.service_id, {})
    if current.get("receipt_id") == receipt_id and current.get("state") not in {
        "worker_completed",
        "failed",
    }:
        current = {**current, "pid": process.pid, "state": "running"}
        current = _set_worker_record(
            runtime,
            definition.service_id,
            current,
            expected_receipt_id=receipt_id,
        )
    return current


def _circuit_breaker_state(runtime: Path) -> dict[str, Any]:
    payload = read_json(runtime / CIRCUIT_BREAKERS_ARTIFACT)
    return payload.get("services") if isinstance(payload.get("services"), dict) else {}


def _service_code_state(definition: ServiceDefinition) -> list[dict[str, Any]]:
    code_paths = sorted((ROOT / "orchestrator").glob("*.py"))
    code_paths.extend(
        ROOT / command[0]
        for command in definition.command_sequence
        if command and (ROOT / command[0]).is_file()
    )
    code_state = []
    for path in sorted(set(code_paths)):
        try:
            stat = path.stat()
        except OSError:
            continue
        code_state.append(
            {
                "path": str(path.relative_to(ROOT)),
                "size": stat.st_size,
                "sha256": file_sha256(path),
            }
        )
    return code_state


def _service_revalidation_identity(definition: ServiceDefinition) -> str:
    """Identify the executable repair campaign without mutable research inputs."""

    return sha256_json(
        {
            "service": definition.to_dict(),
            "code_state": _service_code_state(definition),
            "environment": {
                "python_executable": str(Path(sys.executable).resolve()),
                "python_version": sys.version.split()[0],
                "service_contract_hash": operator_service_contract_hash(),
            },
        }
    )


def operator_service_revalidation_identity(service_id: str) -> str:
    """Return the committed executable identity used to verify circuit repairs."""

    return _service_revalidation_identity(_service_definition(service_id))


def code_defect_revalidation_available(
    service_id: str,
    circuit: dict[str, Any],
) -> bool:
    """Allow corrected code to be tested without silently clearing the circuit."""

    return bool(
        circuit.get("state") in {"open", "half_open"}
        and circuit.get("failure_class") == "code_defect"
        and circuit.get("failure_revalidation_identity")
        and circuit.get("failure_revalidation_identity")
        != operator_service_revalidation_identity(service_id)
    )


def _service_revalidation_fingerprint(runtime: Path, definition: ServiceDefinition) -> str:
    """Identify a material repair trigger, including the current evidence snapshot."""

    evidence_state = []
    for name in definition.prerequisite_artifacts:
        path = runtime / name
        if not path.exists():
            evidence_state.append({"artifact": name, "exists": False})
            continue
        try:
            stat = path.stat()
        except OSError:
            evidence_state.append({"artifact": name, "exists": False})
            continue
        evidence_state.append(
            {
                "artifact": name,
                "exists": True,
                "size": stat.st_size,
                "mtime_ns": stat.st_mtime_ns,
            }
        )
    generation_state = []
    for resource in definition.read_resources:
        pointer = read_json(runtime / ".qadam_generations" / resource / "current.json")
        generation_state.append(
            {
                "resource": resource,
                "generation_id": pointer.get("generation_id"),
                "manifest_sha256": pointer.get("manifest_sha256"),
            }
        )
    return sha256_json(
        {
            "revalidation_identity": _service_revalidation_identity(definition),
            "evidence_state": evidence_state,
            "generation_state": generation_state,
        }
    )


def _circuit_revalidation_allowed(
    runtime: Path,
    definition: ServiceDefinition,
    circuit: dict[str, Any],
) -> tuple[bool, str]:
    trigger_fingerprint = _service_revalidation_fingerprint(runtime, definition)
    confirmation_identity = _service_revalidation_identity(definition)
    retry_at = _parse_timestamp(circuit.get("next_retry_at"))
    same_fingerprint_revalidation_ready = (
        circuit.get("failure_class") in SAME_FINGERPRINT_REVALIDATION_CLASSES
        and int(circuit.get("automatic_revalidation_attempt_count") or 0)
        < MAX_AUTOMATIC_STABILITY_REVALIDATIONS
        and retry_at is not None
        and datetime.now(timezone.utc) >= retry_at
    )
    allowed = (
        circuit.get("state") in {"open", "half_open"}
        and not definition.paperops_dependency
        and definition.safe_retry_class
        in {"idempotent_read", "deterministic_calculation", "interrupted_resumable_job"}
        and circuit.get("failure_class")
        not in {"safety_violation", "credential_operator_action", "disk_resource_pressure"}
        and (
            circuit.get("state") == "half_open"
            or same_fingerprint_revalidation_ready
            or trigger_fingerprint
            not in {
                circuit.get("failure_fingerprint"),
                circuit.get("last_failed_revalidation_fingerprint"),
            }
        )
    )
    return allowed, confirmation_identity


def _write_circuit_breakers_unlocked(runtime: Path, services: dict[str, Any]) -> None:
    registered_service_ids = {definition.service_id for definition in SERVICE_DEFINITIONS}
    services = {
        service_id: record
        for service_id, record in services.items()
        if service_id in registered_service_ids
    }
    AtomicArtifactStore(runtime).write_json(
        CIRCUIT_BREAKERS_ARTIFACT,
        {
            "schema_version": SCHEMA_VERSION,
            "artifact_type": "qadam_operator_circuit_breakers",
            "generated_at": now_iso(),
            "services": services,
            "open_circuit_count": sum(
                record.get("state") in {"open", "half_open"} for record in services.values()
            ),
            "authority": authority_flags(),
        },
    )


def _write_circuit_breakers(runtime: Path, services: dict[str, Any]) -> None:
    with _operator_state_transaction(runtime, CONTROL_STATE_LOCK_FILENAME):
        _write_circuit_breakers_unlocked(runtime, services)


def _record_failure(
    runtime: Path,
    definition: ServiceDefinition,
    receipt: dict[str, Any],
) -> tuple[str, dict[str, Any]]:
    command_results = receipt.get("command_results") or []
    failed_results = [
        record
        for record in command_results
        if int(record.get("returncode") or 0) != 0
        and record.get("evidence_hold_accepted") is not True
    ]
    diagnostic_results = failed_results or command_results[-1:]
    output = "\n".join(
        f"{record.get('stdout_tail', '')}\n{record.get('stderr_tail', '')}"
        for record in diagnostic_results
    )
    failure_class = classify_failure(output)
    with _operator_state_transaction(runtime, CONTROL_STATE_LOCK_FILENAME):
        circuits = _circuit_breaker_state(runtime)
        prior = circuits.get(definition.service_id, {})
        attempt_count = (
            int(prior.get("consecutive_failure_count") or 0) + 1
            if prior.get("failure_class") == failure_class
            else 1
        )
        policy = retry_policy(failure_class, attempt_count=attempt_count - 1)
        automatic_retry = (
            policy.get("automatic_retry_allowed") is True
            and definition.safe_retry_class
            in {
                "idempotent_read",
                "deterministic_calculation",
                "interrupted_resumable_job",
            }
            and definition.paperops_dependency is False
        )
        threshold = int(policy.get("circuit_breaker_after_attempts") or 0)
        circuit_open = (
            failure_class == "safety_violation"
            or (threshold > 0 and attempt_count >= threshold)
            or not automatic_retry
        )
        automatic_revalidation_attempt_count = (
            int(prior.get("automatic_revalidation_attempt_count") or 0) + 1
            if receipt.get("circuit_revalidation") is True
            and failure_class in SAME_FINGERPRINT_REVALIDATION_CLASSES
            else int(prior.get("automatic_revalidation_attempt_count") or 0)
            if prior.get("failure_class") == failure_class
            else 0
        )
        stability_revalidation_scheduled = (
            circuit_open
            and failure_class in SAME_FINGERPRINT_REVALIDATION_CLASSES
            and automatic_revalidation_attempt_count
            < MAX_AUTOMATIC_STABILITY_REVALIDATIONS
        )
        retry_scheduled = (automatic_retry and not circuit_open) or (
            stability_revalidation_scheduled
        )
        circuits[definition.service_id] = {
            "state": "open" if circuit_open else "closed_retry_scheduled",
            "failure_class": failure_class,
            "consecutive_failure_count": attempt_count,
            "automatic_retry_allowed": automatic_retry and not circuit_open,
            "backoff_seconds": policy.get("backoff_seconds"),
            "last_failure_at": receipt.get("completed_at"),
            "failure_fingerprint": _service_revalidation_fingerprint(runtime, definition),
            "failure_revalidation_identity": _service_revalidation_identity(definition),
            "last_failed_revalidation_fingerprint": (
                receipt.get("revalidation_fingerprint")
                if receipt.get("circuit_revalidation") is True
                else None
            ),
            "revalidation_success_count": 0,
            "automatic_revalidation_attempt_count": (
                automatic_revalidation_attempt_count
            ),
            "next_retry_at": (
                datetime.now(timezone.utc)
                + timedelta(seconds=int(policy.get("backoff_seconds") or 0))
            ).isoformat()
            if retry_scheduled
            else None,
        }
        _write_circuit_breakers_unlocked(runtime, circuits)
    retry_record = {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "qadam_operator_retry_event",
        "retry_event_id": "retry:"
        + sha256_json({"receipt_id": receipt["receipt_id"], "failure_class": failure_class})[:24],
        "generated_at": now_iso(),
        "service_id": definition.service_id,
        "failure_class": failure_class,
        "policy": {
            **policy,
            "automatic_retry_allowed": automatic_retry and not circuit_open,
            "automatic_stability_revalidation_allowed": (
                stability_revalidation_scheduled
            ),
            "maximum_stability_revalidations": (
                MAX_AUTOMATIC_STABILITY_REVALIDATIONS
            ),
        },
        "retry_attempted": False,
        "retry_scheduled": retry_scheduled,
        "automatic_stability_revalidation_scheduled": (
            stability_revalidation_scheduled
        ),
        "paper_order_created": False,
        "broker_write_count": 0,
        "authority": authority_flags(),
    }
    append_jsonl_durable(runtime / RETRY_LEDGER_ARTIFACT, retry_record)
    return failure_class, retry_record


def _clear_circuit_after_success(
    runtime: Path,
    service_id: str,
    *,
    revalidation_fingerprint: str | None = None,
) -> str:
    with _operator_state_transaction(runtime, CONTROL_STATE_LOCK_FILENAME):
        circuits = _circuit_breaker_state(runtime)
        if service_id not in circuits:
            return "closed"
        prior = circuits[service_id]
        if prior.get("state") in {"open", "half_open"}:
            fingerprint = revalidation_fingerprint or str(
                prior.get("failure_fingerprint") or ""
            )
            prior_fingerprint = str(prior.get("revalidation_fingerprint") or "")
            success_count = (
                int(prior.get("revalidation_success_count") or 0) + 1
                if prior.get("state") == "half_open" and prior_fingerprint == fingerprint
                else 1
            )
            append_jsonl_durable(
                runtime / CIRCUIT_REVALIDATION_ARTIFACT,
                {
                    "schema_version": SCHEMA_VERSION,
                    "artifact_type": "qadam_operator_circuit_revalidation_evidence",
                    "generated_at": now_iso(),
                    "service_id": service_id,
                    "revalidation_fingerprint": fingerprint,
                    "verification_pass": success_count,
                    "required_verification_passes": 3,
                    "result": "passed",
                    "next_circuit_state": (
                        "closed" if success_count >= 3 else "half_open"
                    ),
                    "paper_order_created_count": 0,
                    "broker_write_count": 0,
                    "authority": authority_flags(),
                },
            )
            if success_count < 3:
                circuits[service_id] = {
                    **prior,
                    "state": "half_open",
                    "automatic_retry_allowed": True,
                    "last_revalidation_success_at": now_iso(),
                    "revalidation_fingerprint": fingerprint,
                    "revalidation_success_count": success_count,
                    "next_retry_at": now_iso(),
                }
                _write_circuit_breakers_unlocked(runtime, circuits)
                return "half_open"
        circuits[service_id] = {
            "state": "closed",
            "failure_class": None,
            "consecutive_failure_count": 0,
            "automatic_revalidation_attempt_count": 0,
            "automatic_retry_allowed": False,
            "backoff_seconds": None,
            "last_success_at": now_iso(),
            "revalidation_fingerprint": revalidation_fingerprint,
            "revalidation_success_count": 3,
            "next_retry_at": None,
        }
        _write_circuit_breakers_unlocked(runtime, circuits)
        return "closed"


def _skip_receipt(
    definition: ServiceDefinition,
    *,
    reason: str,
    generated_at: str,
    integration_probe: bool,
    detail: dict[str, Any] | None = None,
) -> dict[str, Any]:
    material = {
        "service_id": definition.service_id,
        "reason": reason,
        "generated_at": generated_at,
        "integration_probe": integration_probe,
    }
    return {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "qadam_operator_service_receipt",
        "receipt_id": "operator-receipt:" + sha256_json(material)[:24],
        "generated_at": generated_at,
        "service_id": definition.service_id,
        "state": "skipped",
        "skip_reason": reason,
        "detail": detail or {},
        "integration_probe": integration_probe,
        "paper_order_created_count": 0,
        "broker_write_count": 0,
        "proof_credit_created_count": 0,
        "live_capital_enabled": False,
        "authority": authority_flags(),
    }


def _fair_dispatch_order(
    runtime: Path,
    *,
    integration_probe: bool,
    explicit_service_selection: bool,
    max_jobs: int,
) -> tuple[tuple[ServiceDefinition, ...], int | None]:
    """Rotate bounded full-service cycles so later pipeline stages cannot starve."""

    if integration_probe or explicit_service_selection or max_jobs <= 0:
        return SERVICE_DEFINITIONS, None
    cursor = read_json(runtime / DISPATCH_CURSOR_ARTIFACT)
    try:
        start_index = int(cursor.get("next_index", 0)) % len(SERVICE_DEFINITIONS)
    except (TypeError, ValueError):
        start_index = 0
    return (
        SERVICE_DEFINITIONS[start_index:] + SERVICE_DEFINITIONS[:start_index],
        start_index,
    )


def _freshness_deadline_priority(
    definition: ServiceDefinition,
    successful: dict[str, dict[str, Any]],
    *,
    timestamp: datetime,
) -> int:
    """Elevate a service before its declared output freshness deadline expires."""

    if definition.latency_sensitive:
        return 0
    deadline = definition.freshness_deadline_seconds or max(
        definition.cadence_seconds * 3,
        900,
    )
    completed = _parse_timestamp(
        (successful.get(definition.service_id) or {}).get("completed_at")
    )
    if completed is None:
        return 1
    age_seconds = max(0.0, (timestamp - completed).total_seconds())
    if age_seconds >= deadline:
        return 0
    guard_seconds = min(5 * 60, max(60, deadline // 3))
    return 2 if age_seconds >= max(0, deadline - guard_seconds) else 3


def _service_health_freshness_deadline(definition: ServiceDefinition) -> int:
    """Return the liveness SLA without weakening decision-evidence clocks."""

    declared = definition.freshness_deadline_seconds or max(
        definition.cadence_seconds * 3,
        900,
    )
    return max(declared, MIN_SERVICE_HEALTH_FRESHNESS_SECONDS)


def _bounded_dispatch_order(
    definitions: tuple[ServiceDefinition, ...],
    successful: dict[str, dict[str, Any]],
    *,
    timestamp: datetime,
    max_jobs: int | None = None,
    circuits: dict[str, dict[str, Any]] | None = None,
) -> tuple[ServiceDefinition, ...]:
    """Reserve capacity while guaranteeing circuit revalidation can progress."""

    circuit_states = circuits or {}

    def secondary_priority(definition: ServiceDefinition) -> int:
        # A repaired half-open service must win its domain's reserved slot.
        # Otherwise an equally stale healthy projection can consume that slot
        # every cycle and leave the repaired circuit half-open indefinitely.
        if (circuit_states.get(definition.service_id) or {}).get("state") in {
            "open",
            "half_open",
        }:
            return -1
        return _freshness_deadline_priority(
            definition,
            successful,
            timestamp=timestamp,
        )

    return order_by_domain_reservations(
        definitions,
        service_id_getter=lambda definition: definition.service_id,
        secondary_priority_getter=secondary_priority,
        max_jobs=max_jobs or configured_max_jobs_per_cycle(),
    )


def dispatch_due_jobs(
    settings: Settings | None = None,
    *,
    force_due: bool = False,
    integration_probe: bool = False,
    service_ids: tuple[str, ...] | None = None,
    executor: CommandExecutor | None = None,
    max_jobs: int = 0,
) -> dict[str, Any]:
    """Run only allowlisted due jobs and record every execution or skip."""

    runtime = runtime_dir(settings)
    domain_errors = validate_domain_coverage(
        definition.service_id for definition in SERVICE_DEFINITIONS
    )
    if domain_errors:
        raise RuntimeError("scheduler_domain_contract_failed:" + ",".join(domain_errors))
    try:
        storage_maintenance = run_storage_maintenance(runtime, force=False, apply=True)
        storage_health = storage_maintenance.get("disk") or live_storage_health(runtime)
    except Exception as exc:  # noqa: BLE001 - live disk health remains authoritative
        storage_health = {
            **live_storage_health(runtime),
            "reason": "storage_maintenance_failed",
            "maintenance_degraded": True,
        }
        storage_maintenance = {
            "status": "maintenance_failed",
            "maintenance_error": {
                "error_type": type(exc).__name__,
                "error": str(exc)[:500],
            },
            "disk": storage_health,
        }
    generated_at = now_iso()
    cycle_generated_at = generated_at
    timestamp = _parse_timestamp(generated_at) or datetime.now(timezone.utc)
    order_exposure_integrity = _order_exposure_integrity(
        runtime,
        generated_at=generated_at,
    )
    AtomicArtifactStore(runtime).write_json(
        ORDER_EXPOSURE_INTEGRITY_ARTIFACT,
        order_exposure_integrity,
    )
    selected = set(service_ids or (definition.service_id for definition in SERVICE_DEFINITIONS))
    lock = read_json(runtime / LOCK_ARTIFACT)
    release, release_effective = _paper_release_state(runtime)
    research_lock_active = lock.get("status") == "active"
    successful = _last_successful_receipts(runtime)
    circuits = _circuit_breaker_state(runtime)
    active_worker_services = _active_worker_service_ids(runtime)
    cycle_successes: set[str] = set()
    receipts: list[dict[str, Any]] = []
    executed_count = 0
    definitions, dispatch_start_index = _fair_dispatch_order(
        runtime,
        integration_probe=integration_probe,
        explicit_service_selection=service_ids is not None,
        max_jobs=max_jobs,
    )
    if not integration_probe and service_ids is None and max_jobs > 0:
        # Reserve bounded capacity for provider clock, conversion, PaperOps,
        # and lifecycle work before CPU-heavy research jobs. Market-only jobs
        # still skip outside their session, while lifecycle polling remains
        # available for unresolved paper exposure at any hour. Rotation still
        # applies within each priority class.
        definitions = _bounded_dispatch_order(
            definitions,
            successful,
            timestamp=timestamp,
            max_jobs=max_jobs,
            circuits=circuits,
        )
    definition_indexes = {
        definition.service_id: index for index, definition in enumerate(SERVICE_DEFINITIONS)
    }
    last_executed_index: int | None = None

    for definition in definitions:
        if definition.service_id not in selected:
            continue
        # Earlier work may cross a due date, evidence expiry or market close.
        generated_at = now_iso()
        timestamp = _parse_timestamp(generated_at) or datetime.now(timezone.utc)
        circuit = circuits.get(definition.service_id, {})
        terminal_idle = _service_terminal_idle_state(runtime, definition)
        resource_conflicts = _resource_conflicts_with_active_workers(
            definition,
            active_worker_services,
        )
        circuit_revalidation, revalidation_fingerprint = (
            _circuit_revalidation_allowed(runtime, definition, circuit)
            if circuit.get("state") in {"open", "half_open"}
            else (False, "")
        )
        if (
            (definition.write_resources or definition.append_resources)
            and storage_health.get("write_services_allowed") is not True
        ):
            receipt = _skip_receipt(
                definition,
                reason="disk_resource_pressure",
                generated_at=generated_at,
                integration_probe=integration_probe,
                detail={
                    "measurement_source": storage_health.get("measurement_source"),
                    "free_bytes": storage_health.get("free_bytes"),
                    "minimum_free_bytes": storage_health.get("minimum_free_bytes"),
                    "used_ratio": storage_health.get("used_ratio"),
                    "maximum_used_ratio": storage_health.get("maximum_used_ratio"),
                },
            )
        elif (
            definition.paperops_dependency
            and (research_lock_active or not release_effective)
            and not (integration_probe and definition.integration_probe_command_sequence)
        ):
            receipt = _skip_receipt(
                definition,
                reason="research_lock",
                generated_at=generated_at,
                integration_probe=integration_probe,
                detail={"release_effective": release_effective},
            )
        elif (
            definition.service_id == "guarded_paperops"
            and order_exposure_integrity.get("guarded_paperops_allowed") is not True
        ):
            receipt = _skip_receipt(
                definition,
                reason="order_exposure_integrity_blocked",
                generated_at=generated_at,
                integration_probe=integration_probe,
                detail={
                    "duplicate_opening_symbols": order_exposure_integrity.get(
                        "duplicate_opening_symbols", {}
                    ),
                    "stale_market_order_count": order_exposure_integrity.get(
                        "stale_market_order_count", 0
                    ),
                },
            )
        elif (
            definition.service_id == "research_evidence_validation"
            and not force_due
            and _cycle_material_change_state(receipts, "pattern_scoring") is False
        ):
            receipt = _skip_receipt(
                definition,
                reason="no_material_evidence_change",
                generated_at=generated_at,
                integration_probe=integration_probe,
                detail={
                    "pattern_generation_preserved": True,
                    "forward_outcomes_remain_owned_by": "forward_shadow",
                },
            )
        elif terminal_idle.get("active") is True and not integration_probe:
            receipt = _skip_receipt(
                definition,
                reason="terminal_no_work",
                generated_at=generated_at,
                integration_probe=integration_probe,
                detail={
                    "terminal_reason": terminal_idle.get("reason"),
                    "evidence_generated_at": terminal_idle.get("evidence_generated_at"),
                    "job_count": terminal_idle.get("job_count"),
                    "terminal_job_count": terminal_idle.get("terminal_job_count"),
                    "manifest_digest": terminal_idle.get("manifest_digest"),
                },
            )
        elif (
            definition.market_session_only
            and not _market_is_open(timestamp)
            and not integration_probe
        ):
            receipt = _skip_receipt(
                definition,
                reason="market_closed",
                generated_at=generated_at,
                integration_probe=integration_probe,
            )
        elif definition.provider_budget_required and not _provider_budget_available(runtime):
            receipt = _skip_receipt(
                definition,
                reason="cost_budget_exhausted",
                generated_at=generated_at,
                integration_probe=integration_probe,
            )
        elif definition.service_id in active_worker_services:
            receipt = _skip_receipt(
                definition,
                reason="service_already_active",
                generated_at=generated_at,
                integration_probe=integration_probe,
                detail={"active_service_id": definition.service_id},
            )
        elif resource_conflicts:
            receipt = _skip_receipt(
                definition,
                reason="resource_claim_busy",
                generated_at=generated_at,
                integration_probe=integration_probe,
                detail={
                    "conflicting_services": resource_conflicts,
                    "resource_claims": definition.resource_claims().to_dict(),
                },
            )
        elif (
            circuit.get("state") in {"open", "half_open"}
            and not circuit_revalidation
            and not integration_probe
        ):
            receipt = _skip_receipt(
                definition,
                reason="circuit_breaker_open",
                generated_at=generated_at,
                integration_probe=integration_probe,
                detail={
                    "failure_class": circuit.get("failure_class"),
                    "revalidation_waiting_for_change": circuit.get("state") == "open",
                },
            )
        elif (
            circuits.get(definition.service_id, {}).get("state") == "closed_retry_scheduled"
            and (
                _parse_timestamp(circuits[definition.service_id].get("next_retry_at")) or timestamp
            )
            > timestamp
            and not force_due
        ):
            receipt = _skip_receipt(
                definition,
                reason="retry_backoff",
                generated_at=generated_at,
                integration_probe=integration_probe,
                detail={"next_retry_at": circuits[definition.service_id].get("next_retry_at")},
            )
        elif (
            not force_due
            and not circuit_revalidation
            and not _is_due(definition, successful.get(definition.service_id), timestamp=timestamp)
            and not _dependency_advanced(definition, successful, cycle_successes)
        ):
            receipt = _skip_receipt(
                definition,
                reason="not_due",
                generated_at=generated_at,
                integration_probe=integration_probe,
                detail={
                    "next_due_at": _next_due_at(definition, successful.get(definition.service_id))
                },
            )
        else:
            missing_dependencies = [
                dependency
                for dependency in definition.dependencies
                if dependency not in cycle_successes and dependency not in successful
            ]
            prerequisites_ok, stale_prerequisites = _prerequisites_fresh(
                runtime, definition, timestamp=timestamp
            )
            if missing_dependencies:
                receipt = _skip_receipt(
                    definition,
                    reason="dependency_not_ready",
                    generated_at=generated_at,
                    integration_probe=integration_probe,
                    detail={"dependencies": missing_dependencies},
                )
            elif not prerequisites_ok:
                receipt = _skip_receipt(
                    definition,
                    reason="stale_prerequisite",
                    generated_at=generated_at,
                    integration_probe=integration_probe,
                    detail={"artifacts": stale_prerequisites},
                )
            elif max_jobs and executed_count >= max_jobs:
                receipt = _skip_receipt(
                    definition,
                    reason="cycle_job_budget_exhausted",
                    generated_at=generated_at,
                    integration_probe=integration_probe,
                )
            else:
                receipt_id = (
                    "operator-receipt:"
                    + sha256_json(
                        {
                            "service_id": definition.service_id,
                            "generated_at": generated_at,
                            "integration_probe": integration_probe,
                        }
                    )[:24]
                )
                if definition.long_running and not integration_probe and executor is None:
                    count_execution = True
                    worker = _launch_resumable_worker(runtime, definition, receipt_id=receipt_id)
                    receipt = {
                        "schema_version": SCHEMA_VERSION,
                        "artifact_type": "qadam_operator_service_receipt",
                        "receipt_id": receipt_id,
                        "generated_at": generated_at,
                        "service_id": definition.service_id,
                        "state": (
                            "worker_started"
                            if worker.get("state") in {"launching", "running"}
                            else worker.get("state")
                        ),
                        "started_at": worker["started_at"],
                        "worker_pid": worker.get("pid"),
                        "integration_probe": False,
                        "paper_order_created_count": 0,
                        "broker_write_count": 0,
                        "proof_credit_created_count": 0,
                        "live_capital_enabled": False,
                        "authority": authority_flags(),
                    }
                    active_worker_services.add(definition.service_id)
                else:
                    result = _execute_service_synchronously(
                        definition,
                        runtime=runtime,
                        executor=executor,
                        integration_probe=integration_probe,
                    )
                    completed_at = now_iso()
                    receipt = {
                        "schema_version": SCHEMA_VERSION,
                        "artifact_type": "qadam_operator_service_receipt",
                        "receipt_id": receipt_id,
                        "generated_at": generated_at,
                        "service_id": definition.service_id,
                        "state": result["state"],
                        "started_at": generated_at,
                        "completed_at": completed_at,
                        "duration_seconds": result["duration_seconds"],
                        "command_results": result["command_results"],
                        "generation_ids": result["generation_ids"],
                        "input_generation_ids": result["input_generation_ids"],
                        "input_generation_binding_complete": result[
                            "input_generation_binding_complete"
                        ],
                        "mixed_generation_join_count": result["mixed_generation_join_count"],
                        "integration_probe": integration_probe,
                        "circuit_revalidation": circuit_revalidation,
                        "revalidation_fingerprint": (
                            revalidation_fingerprint if circuit_revalidation else None
                        ),
                        "paper_order_created_count": 0,
                        "broker_write_count": 0,
                        "proof_credit_created_count": 0,
                        "live_capital_enabled": False,
                        "authority": authority_flags(),
                    }
                    count_execution = result["state"] != "deferred_resource_busy"
                    if result["state"] == "deferred_resource_busy":
                        receipt = _skip_receipt(
                            definition,
                            reason="resource_claim_busy",
                            generated_at=generated_at,
                            integration_probe=integration_probe,
                            detail={
                                "resource_claims": definition.resource_claims().to_dict(),
                                "deferred_before_command_execution": True,
                            },
                        )
                    elif result["state"] == "failed":
                        failure_class, retry = _record_failure(runtime, definition, receipt)
                        receipt["failure_class"] = failure_class
                        receipt["retry_scheduled"] = retry["retry_scheduled"]
                    else:
                        circuit_state = _clear_circuit_after_success(
                            runtime,
                            definition.service_id,
                            revalidation_fingerprint=(
                                revalidation_fingerprint if circuit_revalidation else None
                            ),
                        )
                        if circuit_state == "closed":
                            cycle_successes.add(definition.service_id)
                        else:
                            receipt["state"] = "completed_pending_circuit_confirmation"
                if count_execution:
                    executed_count += 1
                    last_executed_index = definition_indexes[definition.service_id]
        _append_receipt(runtime, receipt)
        receipts.append(receipt)

    if dispatch_start_index is not None:
        next_index = (
            (last_executed_index + 1) % len(SERVICE_DEFINITIONS)
            if last_executed_index is not None
            else (dispatch_start_index + 1) % len(SERVICE_DEFINITIONS)
        )
        AtomicArtifactStore(runtime).write_json(
            DISPATCH_CURSOR_ARTIFACT,
            {
                "schema_version": SCHEMA_VERSION,
                "artifact_type": "qadam_operator_dispatch_cursor",
                "generated_at": now_iso(),
                "start_index": dispatch_start_index,
                "last_executed_service_id": (
                    SERVICE_DEFINITIONS[last_executed_index].service_id
                    if last_executed_index is not None
                    else None
                ),
                "next_index": next_index,
                "next_service_id": SERVICE_DEFINITIONS[next_index].service_id,
                "max_jobs": max_jobs,
                "authority": authority_flags(),
            },
        )

    completed_states = {
        "completed",
        "completed_with_evidence_hold",
        "completed_with_transport_hold",
        "completed_pending_circuit_confirmation",
        "worker_started",
        "worker_completed",
        "worker_completed_pending_circuit_confirmation",
    }
    return {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "qadam_operator_dispatch_cycle",
        "generated_at": cycle_generated_at,
        "status": "passed"
        if all(
            receipt.get("state") in completed_states or receipt.get("state") == "skipped"
            for receipt in receipts
        )
        else "completed_with_failures",
        "integration_probe": integration_probe,
        "selected_service_count": len(selected),
        "receipt_count": len(receipts),
        "executed_count": executed_count,
        "completed_count": sum(receipt.get("state") in completed_states for receipt in receipts),
        "failed_count": sum(receipt.get("state") == "failed" for receipt in receipts),
        "skipped_count": sum(receipt.get("state") == "skipped" for receipt in receipts),
        "skip_reasons": sorted(
            {str(receipt.get("skip_reason")) for receipt in receipts if receipt.get("skip_reason")}
        ),
        "receipts": receipts,
        "runtime_domains": {
            domain: sum(
                1
                for receipt in receipts
                if service_domain(str(receipt.get("service_id") or "")) == domain
            )
            for domain in ("execution", "research", "projection")
        },
        "storage_status": storage_maintenance.get("status"),
        "storage_write_services_allowed": storage_health.get("write_services_allowed")
        is True,
        "storage_free_bytes": storage_health.get("free_bytes"),
        "paperops_invoked": any(
            receipt.get("service_id") == "guarded_paperops"
            and receipt.get("state") in completed_states
            for receipt in receipts
        ),
        "paper_order_created_count": 0,
        "broker_write_count": 0,
        "proof_credit_created_count": 0,
        "live_capital_enabled": False,
        "authority": authority_flags(),
    }


def run_operator_integration_probe(
    settings: Settings | None = None,
    *,
    executor: CommandExecutor | None = None,
) -> dict[str, Any]:
    runtime = runtime_dir(settings)
    cycle = dispatch_due_jobs(
        settings,
        force_due=True,
        integration_probe=True,
        service_ids=INTEGRATION_PROBE_SERVICES,
        executor=executor,
    )
    terminal = {
        "completed",
        "completed_with_evidence_hold",
        "completed_with_transport_hold",
    }
    states = {
        receipt["service_id"]: receipt.get("state")
        for receipt in cycle["receipts"]
        if receipt.get("service_id") in INTEGRATION_PROBE_SERVICES
    }
    all_executed = all(
        states.get(service_id) in terminal for service_id in INTEGRATION_PROBE_SERVICES
    )
    probe = {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "qadam_operator_integration_probe",
        "phase_id": PHASE_ID,
        "generated_at": now_iso(),
        "status": "passed" if all_executed and cycle["failed_count"] == 0 else "blocked",
        "required_services": list(INTEGRATION_PROBE_SERVICES),
        "required_service_count": len(INTEGRATION_PROBE_SERVICES),
        "executed_service_count": sum(state in terminal for state in states.values()),
        "executed_count": cycle["executed_count"],
        "completed_count": cycle["completed_count"],
        "failed_count": cycle["failed_count"],
        "skipped_count": cycle["skipped_count"],
        "skip_reasons": cycle["skip_reasons"],
        "service_states": states,
        "all_required_jobs_executed": all_executed,
        "projection_only_cycle": False,
        "paperops_invoked": cycle["paperops_invoked"],
        "research_lock_bypassed": False,
        "paper_order_created_count": 0,
        "broker_write_count": 0,
        "proof_credit_created_count": 0,
        "live_capital_enabled": False,
        "cycle_receipt_ids": [receipt["receipt_id"] for receipt in cycle["receipts"]],
        "authority": authority_flags(),
    }
    AtomicArtifactStore(runtime).write_json(INTEGRATION_PROBE_ARTIFACT, probe)
    return probe


def execute_registered_worker(
    service_id: str,
    receipt_id: str,
    settings: Settings | None = None,
) -> int:
    runtime = runtime_dir(settings)
    definition = _service_definition(service_id)
    if not definition.long_running or definition.paperops_dependency:
        raise ValueError("operator_worker_service_not_permitted")
    result = _execute_service_synchronously(definition, runtime=runtime)
    completed_at = now_iso()
    receipt = {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "qadam_operator_service_receipt",
        "receipt_id": receipt_id,
        "generated_at": completed_at,
        "service_id": service_id,
        "state": "worker_completed" if result["state"] != "failed" else "failed",
        "completed_at": completed_at,
        "duration_seconds": result["duration_seconds"],
        "command_results": result["command_results"],
        "generation_ids": result["generation_ids"],
        "input_generation_ids": result["input_generation_ids"],
        "input_generation_binding_complete": result["input_generation_binding_complete"],
        "mixed_generation_join_count": result["mixed_generation_join_count"],
        "worker_pid": os.getpid(),
        "paper_order_created_count": 0,
        "broker_write_count": 0,
        "proof_credit_created_count": 0,
        "live_capital_enabled": False,
        "authority": authority_flags(),
    }
    if result["state"] == "failed":
        failure_class, retry = _record_failure(runtime, definition, receipt)
        receipt["failure_class"] = failure_class
        receipt["retry_scheduled"] = retry["retry_scheduled"]
    elif result["state"] == "deferred_resource_busy":
        receipt["state"] = "worker_deferred_resource_busy"
        receipt["retry_scheduled"] = True
    else:
        circuit_state = _clear_circuit_after_success(runtime, service_id)
        if circuit_state != "closed":
            receipt["state"] = "worker_completed_pending_circuit_confirmation"
    _append_receipt(runtime, receipt)
    current = _workers(runtime).get(service_id, {})
    _set_worker_record(
        runtime,
        service_id,
        {
        **current,
        "state": receipt["state"],
        "completed_at": completed_at,
        "exit_code": 0 if result["state"] != "failed" else 1,
        },
        expected_receipt_id=receipt_id,
    )
    return 0 if result["state"] != "failed" else 1


def repair_operator_service_circuit(
    service_id: str,
    settings: Settings | None = None,
    *,
    executor: CommandExecutor | None = None,
    explicit_guarded_paperops_confirmation: bool = False,
    explicit_open_market_conversion_confirmation: bool = False,
) -> dict[str, Any]:
    """Re-run one safe service and close its circuit only after success."""
    runtime = runtime_dir(settings)
    definition = _service_definition(service_id)
    guarded_paperops_revalidation = (
        definition.service_id == "guarded_paperops"
        and explicit_guarded_paperops_confirmation
    )
    open_market_conversion_revalidation = (
        definition.service_id == "open_market_conversion"
        and explicit_open_market_conversion_confirmation
    )
    explicit_paper_service_revalidation = (
        guarded_paperops_revalidation or open_market_conversion_revalidation
    )
    if (
        definition.paperops_dependency
        and not explicit_paper_service_revalidation
    ) or (
        not explicit_paper_service_revalidation
        and definition.safe_retry_class not in {
        "idempotent_read",
        "deterministic_calculation",
        "interrupted_resumable_job",
        }
    ):
        raise ValueError("operator_circuit_repair_service_not_permitted")
    if open_market_conversion_revalidation and not all(
        "--no-paperops" in command for command in definition.command_sequence
    ):
        raise ValueError("open_market_conversion_revalidation_requires_no_paperops")
    if explicit_paper_service_revalidation:
        lock = read_json(runtime / LOCK_ARTIFACT)
        _release, release_effective = _paper_release_state(runtime)
        if lock.get("status") == "active" or not release_effective:
            raise ValueError("guarded_paperops_revalidation_requires_effective_paper_release")
    prior = _circuit_breaker_state(runtime).get(service_id, {})
    if prior.get("state") not in {"open", "half_open"}:
        return {
            "status": "not_required",
            "service_id": service_id,
            "prior_circuit_state": prior.get("state", "closed"),
            "paper_order_created_count": 0,
            "broker_write_count": 0,
            "live_capital_enabled": False,
            "authority": authority_flags(),
        }

    revalidation_fingerprint = _service_revalidation_identity(definition)
    verification_pass_count = 0
    prior_state = str(prior.get("state"))
    for pass_index in range(1, 4):
        result = _execute_service_synchronously(
            definition,
            runtime=runtime,
            executor=executor,
        )
        completed_at = now_iso()
        receipt = {
            "schema_version": SCHEMA_VERSION,
            "artifact_type": "qadam_operator_service_receipt",
            "receipt_id": "operator-receipt:"
            + sha256_json(
                {
                    "service_id": service_id,
                    "completed_at": completed_at,
                    "repair_attempt": True,
                    "verification_pass": pass_index,
                }
            )[:24],
            "generated_at": completed_at,
            "completed_at": completed_at,
            "service_id": service_id,
            "state": result["state"],
            "repair_attempt": True,
            "explicit_guarded_paperops_confirmation": guarded_paperops_revalidation,
            "explicit_open_market_conversion_confirmation": (
                open_market_conversion_revalidation
            ),
            "circuit_revalidation": True,
            "revalidation_fingerprint": revalidation_fingerprint,
            "verification_pass": pass_index,
            "prior_circuit_state": prior_state,
            "duration_seconds": result["duration_seconds"],
            "command_results": result["command_results"],
            "generation_ids": result["generation_ids"],
            "input_generation_ids": result["input_generation_ids"],
            "input_generation_binding_complete": result["input_generation_binding_complete"],
            "mixed_generation_join_count": result["mixed_generation_join_count"],
            "paper_order_created_count": 0,
            "broker_write_count": 0,
            "proof_credit_created_count": 0,
            "live_capital_enabled": False,
            "authority": authority_flags(),
        }
        if result["state"] == "failed":
            failure_class, retry = _record_failure(runtime, definition, receipt)
            receipt["failure_class"] = failure_class
            receipt["retry_scheduled"] = retry["retry_scheduled"]
            receipt["status"] = "failed"
            receipt["verification_pass_count"] = verification_pass_count
            _append_receipt(runtime, receipt)
            return receipt
        if result["state"] == "deferred_resource_busy":
            receipt["state"] = "skipped"
            receipt["skip_reason"] = "resource_claim_busy"
            receipt["status"] = "deferred_resource_busy"
            receipt["verification_pass_count"] = verification_pass_count
            _append_receipt(runtime, receipt)
            return receipt
        verification_pass_count += 1
        circuit_state = _clear_circuit_after_success(
            runtime,
            service_id,
            revalidation_fingerprint=revalidation_fingerprint,
        )
        receipt["state"] = (
            "completed" if circuit_state == "closed" else "completed_pending_circuit_confirmation"
        )
        receipt["status"] = "repaired" if circuit_state == "closed" else "confirming_repair"
        receipt["verification_pass_count"] = verification_pass_count
        _append_receipt(runtime, receipt)
        if circuit_state == "closed":
            return receipt
        prior_state = circuit_state
    return receipt


def _record_real_operator_session(
    runtime: Path,
    cycle: dict[str, Any],
    *,
    operator_status: dict[str, Any],
) -> None:
    generated_at = str(cycle.get("generated_at") or now_iso())
    parsed = _parse_timestamp(generated_at) or datetime.now(timezone.utc)
    release, release_effective = _paper_release_state(runtime)
    epoch = read_json(runtime / "current_paper_epoch.json")
    record = {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "qadam_operator_real_session_observation",
        "session_id": "operator-session:"
        + sha256_json({"generated_at": generated_at, "pid": os.getpid()})[:24],
        "generated_at": generated_at,
        "real_calendar_date": parsed.date().isoformat(),
        "real_elapsed_time": True,
        "simulated_elapsed_time_used": False,
        "dispatch_executed_count": int(cycle.get("executed_count") or 0),
        "dispatch_failed_count": int(cycle.get("failed_count") or 0),
        "paperops_invoked": cycle.get("paperops_invoked") is True,
        "paper_epoch_id": epoch.get("paper_epoch_id"),
        "paper_epoch_kind": epoch.get("paper_epoch_kind") or "legacy_test",
        "experimental_paper_release_effective": bool(
            release_effective and release.get("experimental_paper_release_effective") is True
        ),
        "release_binding_digest": release.get("binding_digest"),
        "policy_version": release.get("policy_version"),
        "risk_policy_version": release.get("risk_policy_version"),
        "operator_service_contract_hash": operator_service_contract_hash(),
        "operator_observation_ready": operator_status.get("observation_ready") is True,
        "operator_operational_ready": operator_status.get("operational_ready") is True,
        "operator_build_identity_matches": operator_status.get("build_identity", {}).get(
            "running_build_matches_current"
        )
        is True,
        "launchd_template_matches": operator_status.get("launchd", {}).get(
            "installed_template_matches"
        )
        is True,
        "open_circuit_count": int(operator_status.get("open_circuit_count") or 0),
        "repair_request_count": int(
            operator_status.get("repair_queue", {}).get("open_request_count") or 0
        ),
        "paper_growth_trial_calendar_advanced": False,
        "paper_order_created_count": 0,
        "broker_write_count": 0,
        "authority": authority_flags(),
    }
    append_jsonl_durable(runtime / SESSION_LEDGER_ARTIFACT, record)


def _real_soak_evidence(runtime: Path) -> dict[str, Any]:
    sessions = [
        record
        for record in read_jsonl(runtime / SESSION_LEDGER_ARTIFACT)
        if record.get("real_elapsed_time") is True
        and record.get("simulated_elapsed_time_used") is False
    ]
    observed_dates = sorted(
        {
            str(record.get("real_calendar_date"))
            for record in sessions
            if record.get("real_calendar_date")
        }
    )
    legacy = read_json(runtime / LEGACY_SOAK_ARTIFACT)
    legacy_count = (
        int(legacy.get("observed_soak_day_count") or 0)
        if legacy.get("simulated_elapsed_time_used") is not True
        else 0
    )
    observed_count = max(len(observed_dates), legacy_count)
    return {
        "observed_session_count": observed_count,
        "observed_calendar_dates": observed_dates,
        "required_session_count": 7,
        "complete": observed_count >= 7
        and (len(observed_dates) >= 7 or legacy.get("soak_complete") is True),
        "session_ledger_record_count": len(sessions),
        "simulated_elapsed_time_used": False,
    }


def _service_runtime_record(
    definition: ServiceDefinition,
    *,
    generated_at: str,
    research_lock_active: bool,
    release_effective: bool,
    process_running: bool,
    last_receipt: dict[str, Any] | None = None,
    last_successful_receipt: dict[str, Any] | None = None,
    circuit: dict[str, Any] | None = None,
    worker: dict[str, Any] | None = None,
    terminal_idle: dict[str, Any] | None = None,
) -> dict[str, Any]:
    paperops_blocked = definition.paperops_dependency and (
        research_lock_active or not release_effective
    )
    definition_record = definition.to_dict()
    definition_record["resource_claims"] = definition.resource_claims().to_dict()
    definition_record["command_sequence"] = [
        _display_command(command) for command in definition.command_sequence
    ]
    definition_record["integration_probe_command_sequence"] = [
        _display_command(command) for command in definition.integration_probe_command_sequence
    ]
    receipt = last_receipt or {}
    successful_receipt = last_successful_receipt or {}
    worker_state = worker or {}
    terminal_state = terminal_idle or {"active": False}
    terminal_active = terminal_state.get("active") is True
    generated_dt = _parse_timestamp(generated_at) or datetime.now(timezone.utc)
    idle_reason = "terminal_no_work" if terminal_active else receipt.get("skip_reason")
    idle_current = idle_reason in {
        "no_eligible_work",
        "market_closed",
        "terminal_no_work",
    }
    receipt_dt = _parse_timestamp(
        (
            terminal_state.get("evidence_generated_at")
            if terminal_active
            else receipt.get("completed_at") or receipt.get("generated_at")
            if idle_current
            else successful_receipt.get("completed_at") or successful_receipt.get("generated_at")
        )
    )
    receipt_age_seconds = (
        max(0.0, (generated_dt - receipt_dt).total_seconds()) if receipt_dt else None
    )
    health_freshness_deadline = _service_health_freshness_deadline(definition)
    freshness_state = (
        "fresh"
        if terminal_active
        else "not_run"
        if receipt_dt is None
        else "fresh"
        if receipt_age_seconds <= health_freshness_deadline
        else "stale"
    )
    return {
        **definition_record,
        "generated_at": generated_at,
        "service_process_running": process_running,
        "current_state": (
            "watch_only_research_lock"
            if paperops_blocked
            else "idle_no_eligible_work"
            if idle_reason == "no_eligible_work"
            else "idle_market_closed"
            if idle_reason == "market_closed"
            else "idle_terminal_complete"
            if idle_reason == "terminal_no_work"
            else "worker_running"
            if worker_state.get("state") == "running"
            else "monitor_ready"
            if not process_running
            else "supervised"
        ),
        "current_execution_allowed": process_running and not paperops_blocked,
        "paperops_watch_only": paperops_blocked,
        "last_receipt": {
            "receipt_id": receipt.get("receipt_id"),
            "state": receipt.get("state") or "not_run",
            "completed_at": receipt.get("completed_at"),
            "skip_reason": idle_reason,
            "failure_class": receipt.get("failure_class"),
        },
        "next_due_at": None
        if terminal_active
        else _next_due_at(definition, receipt if idle_current else last_successful_receipt),
        "freshness": {
            "state": freshness_state,
            "age_seconds": receipt_age_seconds,
            "stale_after_seconds": None if terminal_active else health_freshness_deadline,
            "terminal_idle": terminal_active,
            "terminal_reason": terminal_state.get("reason") if terminal_active else None,
            "scheduler_priority_deadline_seconds": (
                definition.freshness_deadline_seconds
                or max(definition.cadence_seconds * 3, 900)
            ),
            "decision_evidence_freshness_enforced_separately": True,
        },
        "circuit_breaker": circuit or {"state": "closed"},
        "terminal_idle": terminal_state,
        "worker": {
            "state": worker_state.get("state") or "not_running",
            "pid": worker_state.get("pid") if worker_state.get("state") == "running" else None,
            "resume_required": worker_state.get("resume_required") is True,
        },
        "live_capital_enabled": False,
        "broker_write_count": 0,
    }


def _lease_runtime_state(runtime: Path) -> dict[str, Any]:
    lease = read_json(runtime / LEASE_ARTIFACT)
    pid = int(lease.get("owner_pid") or 0)
    expires_at = _parse_timestamp(lease.get("expires_at"))
    active = (
        lease.get("status") == "active"
        and _pid_alive(pid)
        and (expires_at is None or expires_at > datetime.now(timezone.utc))
    )
    return {
        "lease_present": bool(lease),
        "lease_status": lease.get("status") or "not_acquired",
        "owner_pid": pid if active else None,
        "owner_process_alive": active,
        "single_instance_active": active,
        "duplicate_instance_prevention": "non_blocking_flock",
        # The lease is a local diagnostic and may contain absolute paths. Only
        # its digested public projection may enter dashboard/cockpit state.
        "build_identity": operator_public_build_identity(lease.get("build_identity") or {}),
    }


def _repair_entry(
    *,
    category: str,
    summary: str,
    action: str,
    severity: str,
    evidence: dict[str, Any],
) -> dict[str, Any]:
    material = {"category": category, "summary": summary, "evidence": evidence}
    return {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "qadam_operator_repair_request",
        "repair_request_id": f"operator-repair:{sha256_json(material)[:24]}",
        "category": category,
        "severity": severity,
        "summary": summary,
        "required_action": action,
        "evidence": evidence,
        "state": "operator_action_required"
        if category == "operator_action"
        else "repair_requested",
        "automatic_retry_allowed": False,
        "autonomous_code_edit_allowed": False,
        "secret_change_allowed": False,
        "authority_change_allowed": False,
        "paper_order_allowed": False,
        "broker_write_allowed": False,
        "proof_credit_allowed": False,
        "live_capital_enabled": False,
    }


def _order_exposure_integrity(
    runtime: Path,
    *,
    generated_at: str,
) -> dict[str, Any]:
    observed_at = _parse_timestamp(generated_at) or datetime.now(timezone.utc)
    open_orders = [
        order
        for order in read_jsonl(runtime / PAPER_ORDERS_ARTIFACT)
        if str(order.get("status") or "").lower() in OPEN_BROKER_ORDER_STATES
    ]
    opening_counts: dict[str, int] = {}
    stale_market_orders: list[dict[str, Any]] = []
    for order in open_orders:
        symbol = str(order.get("instrument") or order.get("symbol") or "").upper()
        intent = str(order.get("position_intent") or "").lower()
        if symbol and intent in OPENING_POSITION_INTENTS:
            opening_counts[symbol] = opening_counts.get(symbol, 0) + 1
        submitted_at = _parse_timestamp(order.get("submitted_at"))
        age_seconds = (
            max(0.0, (observed_at - submitted_at).total_seconds())
            if submitted_at is not None
            else None
        )
        if (
            str(order.get("order_type") or "").lower() == "market"
            and age_seconds is not None
            and age_seconds > MAX_PENDING_MARKET_ORDER_AGE_SECONDS
        ):
            stale_market_orders.append(
                {
                    "symbol": symbol,
                    "position_intent": intent or "unknown",
                    "age_seconds": round(age_seconds, 3),
                }
            )
    duplicate_opening_symbols = {
        symbol: count for symbol, count in opening_counts.items() if count > 1
    }
    blocked = bool(duplicate_opening_symbols or stale_market_orders)
    return {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "qadam_operator_order_exposure_integrity",
        "generated_at": generated_at,
        "status": "blocked" if blocked else "passed",
        "open_order_count": len(open_orders),
        "duplicate_opening_symbol_count": len(duplicate_opening_symbols),
        "duplicate_opening_order_count": sum(
            count - 1 for count in duplicate_opening_symbols.values()
        ),
        "duplicate_opening_symbols": duplicate_opening_symbols,
        "stale_market_order_count": len(stale_market_orders),
        "stale_market_orders": stale_market_orders[:20],
        "guarded_paperops_allowed": not blocked,
        "paper_only": True,
        "live_capital_enabled": False,
        "authority": authority_flags(),
    }


def _build_repair_queue(
    runtime: Path,
    *,
    service_installed: bool,
    process_running: bool,
    generated_at: str,
) -> dict[str, Any]:
    entries: list[dict[str, Any]] = []
    order_integrity = _order_exposure_integrity(
        runtime,
        generated_at=generated_at,
    )
    if order_integrity["status"] != "passed":
        entries.append(
            _repair_entry(
                category="safety_violation",
                severity="critical",
                summary="Pending paper orders violate aggregate exposure integrity.",
                action="Keep guarded PaperOps stopped, reconcile the Alpaca Paper mirror, and cancel or resolve duplicate and stale pending orders before revalidation.",
                evidence={
                    "open_order_count": order_integrity["open_order_count"],
                    "duplicate_opening_symbols": order_integrity[
                        "duplicate_opening_symbols"
                    ],
                    "stale_market_order_count": order_integrity[
                        "stale_market_order_count"
                    ],
                },
            )
        )
    if not service_installed:
        entries.append(
            _repair_entry(
                category="operator_action",
                severity="medium",
                summary="Operator service is prepared but not installed.",
                action="Review and run scripts/install_qadam_operator_launch_agent.sh, then bootstrap explicitly.",
                evidence={"launchd_label": LAUNCHD_LABEL, "target_exists": False},
            )
        )
    elif not process_running:
        entries.append(
            _repair_entry(
                category="operator_action",
                severity="high",
                summary="Operator service is installed but no active lease is visible.",
                action="Inspect launchctl status and logs before an explicit restart.",
                evidence={"launchd_label": LAUNCHD_LABEL, "target_exists": True},
            )
        )
    freshness = read_json(runtime / DASHBOARD_FRESHNESS_ARTIFACT)
    records = freshness.get("records") if isinstance(freshness.get("records"), list) else []
    stale = [
        record
        for record in records
        if record.get("freshness_state") in {"stale", "missing"}
        and Path(str(record.get("artifact") or "")).name
        not in NON_BLOCKING_DERIVED_PROJECTION_ARTIFACTS
    ]
    if stale:
        entries.append(
            _repair_entry(
                category="stale_artifact",
                severity="medium",
                summary=f"{len(stale)} monitored operator artifacts need refresh or evidence repair.",
                action="Retry only known safe refreshes; keep affected decisions fail-closed until revalidated.",
                evidence={
                    "artifact_count": len(stale),
                    "artifacts": [record.get("artifact") for record in stale[:20]],
                },
            )
        )
    circuits = _circuit_breaker_state(runtime)
    for service_id, circuit in circuits.items():
        if circuit.get("state") not in {"open", "half_open"}:
            continue
        failure_class = str(circuit.get("failure_class") or "code_defect")
        entries.append(
            _repair_entry(
                category=(
                    "operator_action"
                    if failure_class in {"credential_operator_action", "disk_resource_pressure"}
                    else failure_class
                ),
                severity=(
                    "critical"
                    if failure_class == "safety_violation"
                    else "medium"
                    if failure_class == "research_integrity_hold"
                    else "high"
                ),
                summary=f"{service_id} stopped after a {failure_class.replace('_', ' ')} failure.",
                action=(
                    "Review the safety violation before resetting this circuit."
                    if failure_class == "safety_violation"
                    else "Keep promotion quarantined, inspect the research diagnostic, and revalidate after evidence changes."
                    if failure_class == "research_integrity_hold"
                    else "Inspect the latest receipt, correct the stated cause, and explicitly reset the service circuit."
                ),
                evidence={
                    "service_id": service_id,
                    "failure_class": failure_class,
                    "last_failure_at": circuit.get("last_failure_at"),
                    "consecutive_failure_count": circuit.get("consecutive_failure_count"),
                },
            )
        )
    for service_id, worker in _workers(runtime).items():
        if worker.get("state") != "interrupted":
            continue
        entries.append(
            _repair_entry(
                category="interrupted_resumable_job",
                severity="medium",
                summary=f"{service_id} was interrupted before writing a terminal receipt.",
                action="Resume from the durable checkpoint through the operator dispatcher; do not restart completed partitions.",
                evidence={
                    "service_id": service_id,
                    "receipt_id": worker.get("receipt_id"),
                    "failure_class": worker.get("failure_class"),
                },
            )
        )
    return {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "qadam_operator_repair_queue",
        "phase_id": PHASE_ID,
        "generated_at": generated_at,
        "status": "repair_queue_open" if entries else "repair_queue_clear",
        "open_request_count": len(entries),
        "critical_request_count": sum(entry["severity"] == "critical" for entry in entries),
        "requests": entries,
        "autonomous_code_edit_allowed": False,
        "public_safe": True,
        "read_only": True,
        "command_disabled": True,
        "authority": authority_flags(),
        "order_exposure_integrity": order_integrity,
    }


def _build_interruption_probes(generated_at: str) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    records: list[dict[str, Any]] = []
    retry_records: list[dict[str, Any]] = []
    for scenario, message, expected in SOAK_SCENARIOS:
        observed = classify_failure(
            message, status_code=429 if scenario == "provider_429" else None
        )
        policy = retry_policy(observed)
        safe = observed == expected and policy["paperops_retry_allowed"] is False
        record = {
            "scenario": scenario,
            "expected_failure_class": expected,
            "observed_failure_class": observed,
            "classification_passed": observed == expected,
            "safe_response_passed": safe,
            "retry_policy": policy,
            "checkpoint_required": scenario in {"laptop_sleep", "sigterm", "stale_lock"},
            "semantic_hypotheses_blocked": scenario == "local_llm_down",
            "frontier_review_deferred": scenario == "frontier_down",
            "classical_fallback_must_be_labelled": scenario == "quantum_fallback",
            "affected_work_stopped": scenario == "unsafe_route",
            "probe_only": True,
            "external_call_performed": False,
            "paper_order_created": False,
            "broker_write_count": 0,
        }
        records.append(record)
        retry_records.append(
            {
                "schema_version": SCHEMA_VERSION,
                "artifact_type": "qadam_operator_retry_probe",
                "retry_event_id": f"retry-probe:{sha256_json({'scenario': scenario, 'class': observed})[:24]}",
                "generated_at": generated_at,
                "service_id": "probe_suite",
                "scenario": scenario,
                "failure_class": observed,
                "probe_only": True,
                "retry_attempted": False,
                "policy": policy,
                "paper_order_created": False,
                "broker_write_count": 0,
                "authority": authority_flags(),
            }
        )
    passed = all(record["safe_response_passed"] for record in records)
    return (
        {
            "schema_version": SCHEMA_VERSION,
            "artifact_type": "qadam_operator_soak_test",
            "phase_id": PHASE_ID,
            "generated_at": generated_at,
            "status": "interruption_probes_passed" if passed else "interruption_probes_failed",
            "interruption_probe_count": len(records),
            "interruption_probe_pass_count": sum(
                record["safe_response_passed"] for record in records
            ),
            "all_interruption_probes_passed": passed,
            "scenarios": records,
            "multi_session_soak_complete": False,
            "real_elapsed_session_count": 0,
            "simulated_elapsed_time_used": False,
            "paper_growth_trial_calendar_advanced": False,
            "boundary": "Deterministic interruption probes validate response policy only. They do not simulate or satisfy the required real multi-session soak.",
            "public_safe": True,
            "read_only": True,
            "command_disabled": True,
            "authority": authority_flags(),
        },
        retry_records,
    )


def _why_not_running_summary(
    *, process_running: bool, blockers: list[dict[str, Any]]
) -> tuple[str, str]:
    if not process_running:
        return "not_running", "Operator service is ready to install, but is not running."
    if blockers:
        return (
            "running_with_blocks",
            "Operator service is running with evidence or safety holds.",
        )
    return (
        "running_ready",
        "Operator service is running with no current evidence or safety holds.",
    )


def build_operator_service_state(
    settings: Settings | None = None,
    *,
    generated_at: str | None = None,
) -> dict[str, Any]:
    runtime = runtime_dir(settings)
    timestamp = generated_at or now_iso()
    recovery_coverage = build_recovery_coverage()
    lock = read_json(runtime / LOCK_ARTIFACT)
    release, release_effective = _paper_release_state(runtime)
    research = read_json(runtime / RESEARCH_STATUS_ARTIFACT)
    research_heartbeat = read_json(runtime / RESEARCH_HEARTBEAT_ARTIFACT)
    raw_lease = read_json(runtime / LEASE_ARTIFACT)
    lease = _lease_runtime_state(runtime)
    current_build_identity = operator_build_identity(settings)
    running_build_identity = raw_lease.get("build_identity") or {}
    build_binding_keys = (
        "git_commit",
        "dirty_worktree_digest",
        "python_executable",
        "dependency_lock_digest",
        "service_contract_hash",
        "state_root",
        "working_directory",
        "launchd_template_sha256",
        "launchd_target_sha256",
    )
    running_build_matches = bool(running_build_identity) and all(
        running_build_identity.get(key) == current_build_identity.get(key)
        for key in build_binding_keys
    )
    launchd_template_matches = _installed_launchd_matches_template()
    process_running = lease["single_instance_active"]
    service_installed = LAUNCHD_TARGET.exists()
    research_lock_active = lock.get("status") == "active"
    receipt_index = _receipt_index(runtime)
    latest_receipts = dict(receipt_index.get("latest_receipts") or {})
    successful_receipts = dict(receipt_index.get("latest_successful_receipts") or {})
    circuits = _circuit_breaker_state(runtime)
    worker_records = _workers(runtime)
    integration_probe = read_json(runtime / INTEGRATION_PROBE_ARTIFACT)
    permanent_reliability = read_json(runtime / PERMANENT_RELIABILITY_ARTIFACT)
    service_records = [
        _service_runtime_record(
            definition,
            generated_at=timestamp,
            research_lock_active=research_lock_active,
            release_effective=release_effective,
            process_running=process_running,
            last_receipt=latest_receipts.get(definition.service_id),
            last_successful_receipt=successful_receipts.get(definition.service_id),
            circuit=circuits.get(definition.service_id),
            worker=worker_records.get(definition.service_id),
            terminal_idle=_service_terminal_idle_state(runtime, definition),
        )
        for definition in SERVICE_DEFINITIONS
    ]
    validation_blocking = circuits.get("research_evidence_validation", {}).get("state") in {
        "open",
        "half_open",
    }
    for record in service_records:
        service_id = record.get("service_id")
        if service_id == "pattern_scoring":
            record["observation_continues_during_validation_hold"] = True
            record["promotion_quarantined"] = validation_blocking
            record["promotion_quarantine_reason"] = (
                "research_evidence_validation_circuit_not_closed" if validation_blocking else None
            )
        if service_id == "dashboard_refresh":
            circuit_blocking = record.get("circuit_breaker", {}).get("state") in {
                "open",
                "half_open",
            }
            record["last_known_good_projection_available"] = bool(
                successful_receipts.get("dashboard_refresh")
            )
            record["projection_degradation_state"] = (
                "last_known_good_stale_label_required" if circuit_blocking else "current_projection"
            )
    heartbeats = {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "qadam_operator_service_heartbeats",
        "phase_id": PHASE_ID,
        "generated_at": timestamp,
        "status": "running" if process_running else "ready_not_running",
        "operator_service": {
            "running": process_running,
            "lease": lease,
        },
        "research_supervisor": {
            "status": research.get("status") or "not_reported",
            "heartbeat_status": research_heartbeat.get("status") or "not_reported",
            "heartbeat_generated_at": research_heartbeat.get("generated_at"),
        },
        "services": service_records,
        "public_safe": True,
        "read_only": True,
        "command_disabled": True,
        "authority": authority_flags(),
    }
    repair_queue = _build_repair_queue(
        runtime,
        service_installed=service_installed,
        process_running=process_running,
        generated_at=timestamp,
    )
    order_exposure_integrity = repair_queue["order_exposure_integrity"]
    soak, retry_records = _build_interruption_probes(timestamp)
    real_soak = _real_soak_evidence(runtime)
    soak["real_elapsed_session_count"] = real_soak["observed_session_count"]
    soak["real_elapsed_calendar_dates"] = real_soak["observed_calendar_dates"]
    soak["real_session_ledger_record_count"] = real_soak["session_ledger_record_count"]
    soak["multi_session_soak_complete"] = process_running and real_soak["complete"]
    soak["integration_probe_passed"] = integration_probe.get("status") == "passed"
    blockers: list[dict[str, Any]] = []
    if not service_installed:
        blockers.append(
            {
                "code": "operator_service_not_installed",
                "plain_english": "The unattended operator service has not been installed by the operator.",
                "next_action": "Review the generated launchd configuration, then install and bootstrap it explicitly.",
            }
        )
    if not process_running:
        blockers.append(
            {
                "code": "operator_service_not_running",
                "plain_english": "No active single-instance operator service lease is visible.",
                "next_action": "Install or inspect the service; do not infer operation from files alone.",
            }
        )
    if research_lock_active:
        blockers.append(
            {
                "code": "research_lock_active",
                "plain_english": "Research remains in watch-only mode while empirical evidence matures.",
                "next_action": "Complete the evidence and shadow gates before explicit lock release review.",
            }
        )
    if not soak["multi_session_soak_complete"]:
        blockers.append(
            {
                "code": "real_multi_session_soak_incomplete",
                "plain_english": "Interruption probes pass, but the real multi-session unattended soak is incomplete.",
                "next_action": "Run the installed service across real sessions without simulating elapsed time.",
            }
        )
    if integration_probe.get("status") != "passed":
        blockers.append(
            {
                "code": "real_due_job_integration_probe_incomplete",
                "plain_english": "The dispatcher has not yet proved the required research jobs execute through their approved runners.",
                "next_action": "Run scripts/run_qadam_operator_service.py --integration-probe and inspect the structured receipts.",
            }
        )
    if order_exposure_integrity.get("status") != "passed":
        blockers.append(
            {
                "code": "paper_order_exposure_integrity_blocked",
                "plain_english": "The paper broker mirror contains duplicate opening exposure or a stale pending market order.",
                "next_action": "Keep guarded PaperOps stopped and reconcile the pending paper orders before revalidation.",
            }
        )
    if recovery_coverage.get("status") != "passed":
        blockers.append(
            {
                "code": "self_healing_recovery_coverage_incomplete",
                "plain_english": "At least one operator service has no validated recovery path.",
                "next_action": "Keep the operator fail closed until every registered service declares and passes a bounded recovery contract.",
            }
        )
    why_not_status, why_not_headline = _why_not_running_summary(
        process_running=process_running,
        blockers=blockers,
    )
    why_not = {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "qadam_operator_why_not_running",
        "phase_id": PHASE_ID,
        "generated_at": timestamp,
        "status": why_not_status,
        "headline": why_not_headline,
        "blocker_count": len(blockers),
        "blockers": blockers,
        "paperops_watch_only": research_lock_active or not release_effective,
        "public_safe": True,
        "read_only": True,
        "command_disabled": True,
        "authority": authority_flags(),
    }
    open_circuit_count = sum(
        record.get("state") in {"open", "half_open"} for record in circuits.values()
    )
    stale_service_count = sum(
        record.get("freshness", {}).get("state") == "stale" for record in service_records
    )
    not_run_service_count = sum(
        record.get("freshness", {}).get("state") == "not_run"
        for record in service_records
    )
    observation_ready = bool(
        process_running
        and service_installed
        and release_effective
        and not research_lock_active
        and integration_probe.get("status") == "passed"
        and repair_queue["open_request_count"] == 0
        and open_circuit_count == 0
        and stale_service_count == 0
        and not_run_service_count == 0
        and running_build_matches
        and launchd_template_matches
        and recovery_coverage.get("status") == "passed"
    )
    status = {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "qadam_operator_service_status",
        "phase_id": PHASE_ID,
        "generated_at": timestamp,
        "status": (
            "operator_service_running_guarded_paper"
            if process_running and release_effective and not research_lock_active
            else "operator_service_running_research_only"
            if process_running
            else "ready_installed_not_running_guarded_paper"
            if service_installed and release_effective and not research_lock_active
            else "ready_installed_not_running_research_only"
            if service_installed
            else "ready_not_installed_research_only"
        ),
        "implementation_ready": recovery_coverage.get("status") == "passed",
        "operational_ready": process_running
        and service_installed
        and soak["multi_session_soak_complete"]
        and integration_probe.get("status") == "passed"
        and not repair_queue["critical_request_count"]
        and recovery_coverage.get("status") == "passed",
        "observation_ready": observation_ready,
        "service_installed": service_installed,
        "service_running": process_running,
        "installation_is_explicit_operator_action": True,
        "automatic_install_or_bootstrap_allowed": False,
        "launchd": {
            "label": LAUNCHD_LABEL,
            "template": str(LAUNCHD_TEMPLATE.relative_to(ROOT)),
            "target": f"~/Library/LaunchAgents/{LAUNCHD_LABEL}.plist",
            "runner": str(RUNNER.relative_to(ROOT)),
            "worker_runner": str(WORKER_RUNNER.relative_to(ROOT)),
            "installed_template_matches": launchd_template_matches,
        },
        "build_identity": {
            "current": operator_public_build_identity(current_build_identity),
            "running": operator_public_build_identity(running_build_identity),
            "running_build_matches_current": running_build_matches,
            "committed_release": current_build_identity.get("dirty_worktree") is False,
        },
        "single_instance": {
            **lease,
            "build_identity": operator_public_build_identity(lease.get("build_identity") or {}),
        },
        "cadence_separation_enabled": True,
        "due_job_dispatcher_enabled": True,
        "projection_only_control_cycle": False,
        "approved_subprocess_entrypoints_only": True,
        "direct_broker_client_import_allowed": False,
        "service_count": len(service_records),
        "services": service_records,
        "recovery_coverage": {
            "status": recovery_coverage.get("status"),
            "registered_service_count": recovery_coverage.get("registered_service_count"),
            "covered_service_count": recovery_coverage.get("covered_service_count"),
            "uncovered_service_count": recovery_coverage.get("uncovered_service_count"),
        },
        "receipt_ledger": {
            "receipt_count": int(receipt_index.get("receipt_count") or 0),
            "suppressed_repeat_count": int(receipt_index.get("suppressed_repeat_count") or 0),
            "indexed_size_bytes": int(receipt_index.get("indexed_size_bytes") or 0),
            "index_current": int(receipt_index.get("indexed_size_bytes") or 0)
            == (runtime / RECEIPTS_ARTIFACT).stat().st_size
            if (runtime / RECEIPTS_ARTIFACT).exists()
            else True,
        },
        "liveness": {
            "process_running": process_running,
            "lease_active": lease["single_instance_active"],
        },
        "readiness": {
            "implementation_ready": recovery_coverage.get("status") == "passed",
            "research_supervisor_contract_present": bool(research),
            "operator_installation_complete": service_installed,
            "legacy_seven_session_soak_complete": soak["multi_session_soak_complete"],
            "permanent_reliability_status": permanent_reliability.get("status")
            or "not_run",
            "permanent_reliability_certified": permanent_reliability.get(
                "permanent_reliability_certified"
            )
            is True,
            "integration_probe_passed": integration_probe.get("status") == "passed",
            "observation_ready": observation_ready,
            "running_build_matches_current": running_build_matches,
            "launchd_template_matches": launchd_template_matches,
            "committed_release": current_build_identity.get("dirty_worktree") is False,
        },
        "freshness": {
            "fresh_service_count": sum(
                record.get("freshness", {}).get("state") == "fresh" for record in service_records
            ),
            "stale_service_count": stale_service_count,
            "not_run_service_count": not_run_service_count,
        },
        "research_lock_active": research_lock_active,
        "release_effective": release_effective,
        "paperops_watch_only": research_lock_active or not release_effective,
        "safe_retry_classes": [
            "concurrent_artifact_access",
            "transient_provider_network",
            "rate_limit",
            "stale_artifact",
            "interrupted_resumable_job",
        ],
        "failure_classes": list(FAILURE_CLASSES),
        "repair_queue": {
            "open_request_count": repair_queue["open_request_count"],
            "critical_request_count": repair_queue["critical_request_count"],
        },
        "order_exposure_integrity": order_exposure_integrity,
        "interruption_probes_passed": soak["all_interruption_probes_passed"],
        "integration_probe": {
            "status": integration_probe.get("status") or "not_run",
            "all_required_jobs_executed": integration_probe.get("all_required_jobs_executed")
            is True,
            "executed_service_count": int(integration_probe.get("executed_service_count") or 0),
            "required_service_count": len(INTEGRATION_PROBE_SERVICES),
            "paperops_invoked": integration_probe.get("paperops_invoked") is True,
        },
        "paperops_delegation_probe": {
            "status": (
                "deferred_research_lock"
                if research_lock_active or not release_effective
                else "active_canonical_wrapper_owner"
                if process_running
                else "operator_service_not_running"
            ),
            "canonical_wrapper": "scripts/run_paperops_autonomous_pass.py",
            "direct_broker_call_allowed": False,
            "automatic_retry_allowed": False,
        },
        "worker_count": len(worker_records),
        "active_worker_count": sum(
            record.get("state") == "running" for record in worker_records.values()
        ),
        "open_circuit_count": open_circuit_count,
        "multi_session_soak_complete": soak["multi_session_soak_complete"],
        "permanent_reliability": {
            "status": permanent_reliability.get("status") or "not_run",
            "certified": permanent_reliability.get("permanent_reliability_certified")
            is True,
            "blockers": list(permanent_reliability.get("blockers") or []),
        },
        "paper_order_created_count": 0,
        "broker_write_count": 0,
        "public_safe": True,
        "read_only": True,
        "command_disabled": True,
        "authority": authority_flags(),
    }
    return {
        "status": status,
        "heartbeats": heartbeats,
        "repair_queue": repair_queue,
        "retry_records": retry_records,
        "soak": soak,
        "why_not_running": why_not,
        "recovery_coverage": recovery_coverage,
    }


def validate_operator_service_state(state: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    status = state["status"]
    heartbeats = state["heartbeats"]
    repair_queue = state["repair_queue"]
    retry_records = state["retry_records"]
    soak = state["soak"]
    why_not = state["why_not_running"]
    recovery_coverage = state["recovery_coverage"]
    if set(status.get("failure_classes", [])) != set(FAILURE_CLASSES):
        errors.append("operator_service_failure_taxonomy_incomplete")
    if status.get("service_count") != len(SERVICE_DEFINITIONS):
        errors.append("operator_service_registry_incomplete")
    if status.get("receipt_ledger", {}).get("index_current") is not True:
        errors.append("operator_service_receipt_index_stale")
    if status.get("cadence_separation_enabled") is not True:
        errors.append("operator_service_cadence_separation_missing")
    if status.get("due_job_dispatcher_enabled") is not True:
        errors.append("operator_service_due_job_dispatcher_missing")
    if status.get("projection_only_control_cycle") is not False:
        errors.append("operator_service_still_projection_only")
    if status.get("direct_broker_client_import_allowed") is not False:
        errors.append("operator_service_direct_broker_client_allowed")
    required_registry_fields = {
        "command_sequence",
        "cadence_seconds",
        "timeout_seconds",
        "dependencies",
        "concurrency_group",
        "lock_requirement",
        "safety_mode",
        "last_receipt",
        "next_due_at",
        "freshness",
        "safe_retry_class",
        "recovery_mode",
        "resource_claims",
    }
    for service in status.get("services", []):
        if not required_registry_fields.issubset(service):
            errors.append(f"operator_service_registry_fields_missing:{service.get('service_id')}")
        for command in service.get("command_sequence", []):
            if not isinstance(command, list) or len(command) < 2:
                errors.append(f"operator_service_command_invalid:{service.get('service_id')}")
                continue
            script_path = ROOT / str(command[1])
            if not script_path.is_file():
                errors.append(f"operator_service_runner_missing:{service.get('service_id')}")
    if recovery_coverage.get("status") != "passed":
        errors.extend(list(recovery_coverage.get("validation_errors") or []))
        errors.append("operator_service_recovery_coverage_incomplete")
    if status.get("recovery_coverage", {}).get("covered_service_count") != len(
        SERVICE_DEFINITIONS
    ):
        errors.append("operator_service_recovery_coverage_count_mismatch")
    paperops = next(
        (
            record
            for record in status.get("services", [])
            if record.get("service_id") == "guarded_paperops"
        ),
        {},
    )
    if (
        status.get("research_lock_active") is True
        and paperops.get("current_execution_allowed") is not False
    ):
        errors.append("operator_service_paperops_not_fail_closed")
    if paperops.get("command_sequence") != [
        [".venv/bin/python", "scripts/run_paperops_autonomous_pass.py"]
    ]:
        errors.append("operator_service_paperops_not_exact_guarded_wrapper")
    paperops_probe = status.get("paperops_delegation_probe", {})
    if paperops_probe.get("direct_broker_call_allowed") is not False:
        errors.append("operator_service_paperops_probe_direct_broker_allowed")
    if paperops_probe.get("automatic_retry_allowed") is not False:
        errors.append("operator_service_paperops_probe_retry_allowed")
    lifecycle = next(
        (
            record
            for record in status.get("services", [])
            if record.get("service_id") == "paper_lifecycle_poll"
        ),
        {},
    )
    if lifecycle.get("paperops_dependency") is not False:
        errors.append("operator_service_readonly_lifecycle_blocked_by_research_lock")
    if (
        status.get("single_instance", {}).get("duplicate_instance_prevention")
        != "non_blocking_flock"
    ):
        errors.append("operator_service_duplicate_prevention_missing")
    if (
        not LAUNCHD_TEMPLATE.is_file()
        or not INSTALLER.is_file()
        or not RUNNER.is_file()
        or not WORKER_RUNNER.is_file()
    ):
        errors.append("operator_service_installation_assets_missing")
    if soak.get("all_interruption_probes_passed") is not True:
        errors.append("operator_service_interruption_probe_failed")
    if soak.get("simulated_elapsed_time_used") is not False:
        errors.append("operator_service_simulated_elapsed_time_used")
    if (
        soak.get("multi_session_soak_complete") is True
        and soak.get("real_elapsed_session_count", 0) < 7
    ):
        errors.append("operator_service_soak_completed_without_real_sessions")
    integration = status.get("integration_probe", {})
    if integration.get("status") != "passed":
        errors.append("operator_service_integration_probe_not_passed")
    else:
        if integration.get("all_required_jobs_executed") is not True:
            errors.append("operator_service_integration_probe_false_pass")
        if integration.get("executed_service_count") != len(INTEGRATION_PROBE_SERVICES):
            errors.append("operator_service_integration_probe_service_count_mismatch")
        if integration.get("paperops_invoked") is not False:
            errors.append("operator_service_integration_probe_invoked_paperops")
    for record in retry_records:
        policy = record.get("policy", {})
        if policy.get("paperops_retry_allowed") is not False:
            errors.append("operator_service_retry_can_repeat_paperops")
        if policy.get("broker_write_retry_allowed") is not False:
            errors.append("operator_service_retry_can_write_broker")
        if record.get("retry_attempted") is not False or record.get("probe_only") is not True:
            errors.append("operator_service_probe_executed_external_retry")
    for request in repair_queue.get("requests", []):
        if request.get("autonomous_code_edit_allowed") is not False:
            errors.append("operator_service_repair_can_edit_code")
        if not request.get("summary") or not request.get("required_action"):
            errors.append("operator_service_repair_not_specific")
    for payload, prefix in (
        (status, "operator_service"),
        (heartbeats, "operator_heartbeats"),
        (repair_queue, "operator_repair_queue"),
        (soak, "operator_soak"),
        (why_not, "operator_why_not_running"),
        (recovery_coverage, "operator_recovery_coverage"),
    ):
        errors.extend(validate_authority(payload.get("authority", {}), prefix=prefix))
    if status.get("paper_order_created_count") != 0 or status.get("broker_write_count") != 0:
        errors.append("operator_service_unauthorized_execution_side_effect")
    if status.get("observation_ready") is True and (
        status.get("research_lock_active") is True
        or status.get("release_effective") is not True
        or status.get("open_circuit_count") != 0
        or status.get("order_exposure_integrity", {}).get("status") != "passed"
    ):
        errors.append("operator_service_observation_ready_false_pass")
    return unique_errors(errors)


def build_and_write_operator_service(
    settings: Settings | None = None,
) -> tuple[dict[str, Any], dict[str, Any], list[str]]:
    runtime = runtime_dir(settings)
    state = build_operator_service_state(settings)
    errors = validate_operator_service_state(state)
    store = AtomicArtifactStore(runtime)
    store.write_json(STATUS_ARTIFACT, state["status"])
    store.write_json(HEARTBEATS_ARTIFACT, state["heartbeats"])
    store.write_json(REPAIR_QUEUE_ARTIFACT, state["repair_queue"])
    store.write_json(
        ORDER_EXPOSURE_INTEGRITY_ARTIFACT,
        state["repair_queue"]["order_exposure_integrity"],
    )
    existing_retry_records = read_jsonl(runtime / RETRY_LEDGER_ARTIFACT)
    retry_ids = {record.get("retry_event_id") for record in existing_retry_records}
    merged_retry_records = [*existing_retry_records]
    merged_retry_records.extend(
        record for record in state["retry_records"] if record.get("retry_event_id") not in retry_ids
    )
    store.write_jsonl(RETRY_LEDGER_ARTIFACT, merged_retry_records)
    store.write_json(SOAK_ARTIFACT, state["soak"])
    store.write_json(WHY_NOT_RUNNING_ARTIFACT, state["why_not_running"])
    store.write_json(RECOVERY_COVERAGE_ARTIFACT, state["recovery_coverage"])
    if not (runtime / RECEIPTS_ARTIFACT).exists():
        store.write_jsonl(RECEIPTS_ARTIFACT, [])
    if not (runtime / SESSION_LEDGER_ARTIFACT).exists():
        store.write_jsonl(SESSION_LEDGER_ARTIFACT, [])
    if not (runtime / CIRCUIT_BREAKERS_ARTIFACT).exists():
        _write_circuit_breakers(runtime, {})
    if not (runtime / WORKERS_ARTIFACT).exists():
        _write_workers(runtime, {})
    checks = {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "qadam_operator_service_checks",
        "phase_id": PHASE_ID,
        "generated_at": now_iso(),
        "status": "passed" if not errors else "blocked",
        "implementation_ready": not errors,
        "operational_ready": state["status"]["operational_ready"],
        "observation_ready": state["status"]["observation_ready"],
        "service_installed": state["status"]["service_installed"],
        "service_running": state["status"]["service_running"],
        "service_count": state["status"]["service_count"],
        "due_job_dispatcher_enabled": state["status"]["due_job_dispatcher_enabled"],
        "projection_only_control_cycle": state["status"]["projection_only_control_cycle"],
        "integration_probe_passed": state["status"]["integration_probe"]["status"] == "passed",
        "integration_probe_executed_service_count": state["status"]["integration_probe"][
            "executed_service_count"
        ],
        "integration_probe_required_service_count": len(INTEGRATION_PROBE_SERVICES),
        "service_receipt_count": state["status"]["receipt_ledger"]["receipt_count"],
        "suppressed_repeat_receipt_count": state["status"]["receipt_ledger"][
            "suppressed_repeat_count"
        ],
        "receipt_index_current": state["status"]["receipt_ledger"]["index_current"],
        "active_worker_count": state["status"]["active_worker_count"],
        "open_circuit_count": state["status"]["open_circuit_count"],
        "fresh_service_count": state["status"]["freshness"]["fresh_service_count"],
        "stale_service_count": state["status"]["freshness"]["stale_service_count"],
        "not_run_service_count": state["status"]["freshness"]["not_run_service_count"],
        "paperops_delegation_probe_status": state["status"]["paperops_delegation_probe"]["status"],
        "failure_class_count": len(state["status"]["failure_classes"]),
        "interruption_probe_count": state["soak"]["interruption_probe_count"],
        "interruption_probe_pass_count": state["soak"]["interruption_probe_pass_count"],
        "multi_session_soak_complete": state["soak"]["multi_session_soak_complete"],
        "repair_request_count": state["repair_queue"]["open_request_count"],
        "critical_repair_request_count": state["repair_queue"]["critical_request_count"],
        "paperops_watch_only": state["status"]["paperops_watch_only"],
        "paper_order_created_count": 0,
        "broker_write_count": 0,
        "validation_error_count": len(errors),
        "validation_errors": errors,
        "authority": authority_flags(),
    }
    store.write_json(CHECK_ARTIFACT, checks)
    return state, checks, errors


def run_safe_operator_control_cycle(
    settings: Settings | None = None,
    *,
    integration_probe: bool = False,
    force_due: bool = False,
    service_ids: tuple[str, ...] | None = None,
    executor: CommandExecutor | None = None,
    max_jobs: int | None = None,
) -> dict[str, Any]:
    """Dispatch approved due jobs, then refresh read-only status projections."""

    from orchestrator.qadam_operator_dashboard import build_and_write_operator_dashboard
    from orchestrator.qadam_permanent_operator_reliability import (
        build_permanent_reliability_certification,
    )
    from orchestrator.qadam_research_supervisor import build_and_write_research_supervisor
    from orchestrator.qadam_self_healing_supervisor import build_and_write_self_healing_state

    # Publish the active lease and guarded PaperOps ownership before any due job
    # can inspect scheduler state. This prevents a fresh service start from being
    # mistaken for the retired legacy automation during its first dispatch.
    startup_state, startup_checks, startup_errors = build_and_write_operator_service(
        settings
    )
    effective_max_jobs = (
        configured_max_jobs_per_cycle() if max_jobs is None else max_jobs
    )
    dispatch = (
        run_operator_integration_probe(settings, executor=executor)
        if integration_probe
        else dispatch_due_jobs(
            settings,
            force_due=force_due,
            service_ids=service_ids,
            executor=executor,
            max_jobs=effective_max_jobs,
        )
    )
    research = build_and_write_research_supervisor(settings)
    self_healing = build_and_write_self_healing_state(settings, perform_refresh=False)
    dashboard = build_and_write_operator_dashboard(settings)
    state, checks, errors = build_and_write_operator_service(settings)
    dispatch_failed_count = int(dispatch.get("failed_count") or 0)
    if integration_probe and dispatch.get("status") != "passed":
        dispatch_failed_count += 1
    error_count = (
        len(research[2])
        + len(self_healing[2])
        + len(dashboard[2])
        + len(errors)
        + dispatch_failed_count
    )
    if not integration_probe:
        _record_real_operator_session(
            runtime_dir(settings),
            dispatch,
            operator_status=state["status"],
        )
    certification_error_count = 0
    certification_status = "not_run_integration_probe"
    if not integration_probe:
        try:
            certification = build_permanent_reliability_certification(runtime_dir(settings))
            certification_status = str(certification.get("status") or "blocked")
        except (OSError, RuntimeError, ValueError):
            certification_error_count = 1
            certification_status = "projection_error"
    error_count += certification_error_count
    return {
        "generated_at": now_iso(),
        "status": "passed" if error_count == 0 else "blocked",
        "dispatch_status": dispatch.get("status"),
        "dispatch_executed_count": int(dispatch.get("executed_count") or 0),
        "dispatch_completed_count": int(dispatch.get("completed_count") or 0),
        "dispatch_failed_count": dispatch_failed_count,
        "dispatch_skipped_count": int(dispatch.get("skipped_count") or 0),
        "dispatch_skip_reasons": dispatch.get("skip_reasons") or [],
        "dispatch_receipts": dispatch.get("receipts") or [],
        "integration_probe": integration_probe,
        "projection_only_cycle": False,
        "validation_error_count": error_count,
        "research_validation_error_count": len(research[2]),
        "self_healing_validation_error_count": len(self_healing[2]),
        "dashboard_validation_error_count": len(dashboard[2]),
        "operator_service_validation_error_count": len(errors),
        "startup_projection_service_running": startup_state["status"]["service_running"],
        "startup_projection_validation_error_count": len(startup_errors),
        "startup_projection_status": startup_checks["status"],
        "permanent_reliability_status": certification_status,
        "permanent_reliability_projection_error_count": certification_error_count,
        "service_running": state["status"]["service_running"],
        "integration_probe_passed": checks["integration_probe_passed"],
        "paper_order_created_count": checks["paper_order_created_count"],
        "broker_write_count": checks["broker_write_count"],
        "authority": authority_flags(),
    }


def run_requested_operator_full_heal(
    request: dict[str, Any],
    settings: Settings | None = None,
    *,
    executor: CommandExecutor | None = None,
) -> dict[str, Any]:
    """Consume one full-heal request inside the active singleton owner process."""

    runtime = runtime_dir(settings)
    selected = _full_heal_service_ids(list(request.get("service_ids") or []))
    request_id = str(request.get("request_id") or "")
    current = pending_operator_full_heal_request(settings)
    if not request_id or current.get("request_id") != request_id:
        raise ValueError("operator_full_heal_request_not_current")
    accepted_at = str(current.get("accepted_at") or now_iso())
    _update_full_heal_request_state(
        runtime,
        request_id,
        status="in_progress",
        accepted_at=accepted_at,
        owner_pid=os.getpid(),
        phase="circuit_revalidation",
        current_service_ids=[],
        completed_service_ids=list(current.get("completed_service_ids") or []),
    )

    circuit_repairs: list[dict[str, Any]] = []
    dispatch_services: list[str] = []
    circuits = _circuit_breaker_state(runtime)
    for service_id in selected:
        circuit = circuits.get(service_id, {})
        if circuit.get("state") not in {"open", "half_open"}:
            dispatch_services.append(service_id)
            continue
        definition = _service_definition(service_id)
        _update_full_heal_request_state(
            runtime,
            request_id,
            phase="circuit_revalidation",
            current_service_ids=[service_id],
            current_step_timeout_seconds=(
                definition.timeout_seconds
                * max(1, len(definition.command_sequence))
                * MAX_AUTOMATIC_STABILITY_REVALIDATIONS
            ),
            circuit_revalidation_count=len(circuit_repairs),
        )
        corrected_code_revalidation = code_defect_revalidation_available(
            service_id,
            circuit,
        )
        if (
            circuit.get("failure_class") not in FULL_HEAL_SAFE_CIRCUIT_FAILURE_CLASSES
            and not corrected_code_revalidation
        ):
            circuit_repairs.append(
                {
                    "status": "blocked_unsafe_failure_class",
                    "service_id": service_id,
                    "failure_class": circuit.get("failure_class"),
                    "error": "operator_full_heal_requires_operator_review",
                }
            )
            continue
        try:
            result = repair_operator_service_circuit(
                service_id,
                settings,
                executor=executor,
                explicit_guarded_paperops_confirmation=(service_id == "guarded_paperops"),
                explicit_open_market_conversion_confirmation=(
                    service_id == "open_market_conversion"
                ),
            )
            if corrected_code_revalidation:
                result = {
                    **result,
                    "corrected_code_revalidation": True,
                }
        except (RuntimeError, ValueError) as error:
            result = {
                "status": "failed",
                "service_id": service_id,
                "error": f"{error.__class__.__name__}:{error}",
            }
        circuit_repairs.append(result)
        completed = list(
            read_json(runtime / FULL_HEAL_REQUEST_ARTIFACT).get(
                "completed_service_ids"
            )
            or []
        )
        if result.get("status") in {"repaired", "not_required"}:
            if service_id not in completed:
                completed.append(service_id)
        _update_full_heal_request_state(
            runtime,
            request_id,
            phase="circuit_revalidation",
            current_service_ids=[],
            current_step_timeout_seconds=0,
            completed_service_ids=completed,
            circuit_revalidation_count=len(circuit_repairs),
        )

    dispatch_chunks: list[tuple[tuple[str, ...], bool]] = []
    regular_chunk: list[str] = []
    for service_id in dispatch_services:
        definition = _service_definition(service_id)
        if definition.long_running:
            if regular_chunk:
                dispatch_chunks.append((tuple(regular_chunk), False))
                regular_chunk = []
            dispatch_chunks.append(((service_id,), True))
        else:
            regular_chunk.append(service_id)
    if regular_chunk:
        dispatch_chunks.append((tuple(regular_chunk), False))

    dispatch_cycles: list[dict[str, Any]] = []
    completed_service_ids = list(
        read_json(runtime / FULL_HEAL_REQUEST_ARTIFACT).get("completed_service_ids")
        or []
    )
    for chunk_index, (service_ids, force_synchronous) in enumerate(dispatch_chunks, start=1):
        chunk_definitions = [_service_definition(service_id) for service_id in service_ids]
        _update_full_heal_request_state(
            runtime,
            request_id,
            phase="service_revalidation",
            current_service_ids=list(service_ids),
            current_chunk_index=chunk_index,
            dispatch_chunk_count=len(dispatch_chunks),
            completed_service_ids=completed_service_ids,
            current_step_timeout_seconds=sum(
                definition.timeout_seconds
                * max(1, len(definition.command_sequence))
                for definition in chunk_definitions
            ),
        )
        dispatch_cycle = run_safe_operator_control_cycle(
            settings,
            force_due=True,
            service_ids=service_ids,
            executor=(
                executor or _default_command_executor
                if force_synchronous
                else executor
            ),
            max_jobs=max(1, len(service_ids)),
        )
        dispatch_cycles.append(dispatch_cycle)
        chunk_receipts = {
            str(receipt.get("service_id")): receipt
            for receipt in list(dispatch_cycle.get("dispatch_receipts") or [])
            if isinstance(receipt, dict) and receipt.get("service_id")
        }
        for service_id in service_ids:
            receipt = chunk_receipts.get(service_id, {})
            verified = bool(
                receipt.get("state")
                in {
                    "completed",
                    "completed_with_evidence_hold",
                    "completed_with_transport_hold",
                }
                or (
                    receipt.get("state") == "skipped"
                    and receipt.get("skip_reason")
                    in {"market_closed", "terminal_no_work"}
                )
            )
            if verified and service_id not in completed_service_ids:
                completed_service_ids.append(service_id)
        failed_service_ids = sorted(set(service_ids).difference(completed_service_ids))
        _update_full_heal_request_state(
            runtime,
            request_id,
            phase="service_revalidation",
            current_service_ids=[],
            current_chunk_index=chunk_index,
            dispatch_chunk_count=len(dispatch_chunks),
            completed_service_ids=completed_service_ids,
            failed_service_ids=failed_service_ids,
            current_step_timeout_seconds=0,
        )
    if dispatch_cycles:
        cycle = {
            **dispatch_cycles[-1],
            "generated_at": now_iso(),
            "status": (
                "passed"
                if all(item.get("status") == "passed" for item in dispatch_cycles)
                else "completed_with_failures"
            ),
            "dispatch_status": (
                "passed"
                if all(item.get("dispatch_status") == "passed" for item in dispatch_cycles)
                else "completed_with_failures"
            ),
            "dispatch_executed_count": sum(
                int(item.get("dispatch_executed_count") or 0)
                for item in dispatch_cycles
            ),
            "dispatch_completed_count": sum(
                int(item.get("dispatch_completed_count") or 0)
                for item in dispatch_cycles
            ),
            "dispatch_failed_count": sum(
                int(item.get("dispatch_failed_count") or 0)
                for item in dispatch_cycles
            ),
            "dispatch_skipped_count": sum(
                int(item.get("dispatch_skipped_count") or 0)
                for item in dispatch_cycles
            ),
            "dispatch_skip_reasons": sorted(
                {
                    str(reason)
                    for item in dispatch_cycles
                    for reason in list(item.get("dispatch_skip_reasons") or [])
                    if reason
                }
            ),
            "dispatch_receipts": [
                receipt
                for item in dispatch_cycles
                for receipt in list(item.get("dispatch_receipts") or [])
                if isinstance(receipt, dict)
            ],
            "paper_order_created_count": sum(
                int(item.get("paper_order_created_count") or 0)
                for item in dispatch_cycles
            ),
            "broker_write_count": 0,
            "full_heal_subcycle_count": len(dispatch_cycles),
        }
    else:
        cycle = {
            "generated_at": now_iso(),
            "status": "passed",
            "dispatch_status": "not_required",
            "dispatch_executed_count": 0,
            "dispatch_completed_count": 0,
            "dispatch_failed_count": 0,
            "dispatch_skipped_count": 0,
            "dispatch_skip_reasons": [],
            "paper_order_created_count": 0,
            "broker_write_count": 0,
        }
    repair_failed = any(
        result.get("status") not in {"repaired", "not_required"}
        for result in circuit_repairs
    )
    dispatch_receipts = {
        str(receipt.get("service_id")): receipt
        for receipt in list(cycle.get("dispatch_receipts") or [])
        if isinstance(receipt, dict) and receipt.get("service_id")
    }
    verified_dispatch_states = {
        "completed",
        "completed_with_evidence_hold",
        "completed_with_transport_hold",
    }
    dispatch_service_checks = {
        service_id: {
            "state": dispatch_receipts.get(service_id, {}).get("state"),
            "skip_reason": dispatch_receipts.get(service_id, {}).get("skip_reason"),
            "verified": bool(
                dispatch_receipts.get(service_id, {}).get("state")
                in verified_dispatch_states
                or (
                    dispatch_receipts.get(service_id, {}).get("state") == "skipped"
                    and dispatch_receipts.get(service_id, {}).get("skip_reason")
                    in {"market_closed", "terminal_no_work"}
                )
            ),
        }
        for service_id in dispatch_services
    }
    dispatch_failed = bool(
        cycle.get("status") != "passed"
        or int(cycle.get("dispatch_failed_count") or 0) > 0
        or any(not check["verified"] for check in dispatch_service_checks.values())
    )
    failed_service_ids = sorted(
        service_id
        for service_id in dispatch_services
        if not dispatch_service_checks.get(service_id, {}).get("verified")
    )
    paperops_summary = read_json(runtime / "paperops_autonomous_pass_summary.json")
    paper_runtime = paperops_summary.get("paper_runtime") or {}
    _update_full_heal_request_state(
        runtime,
        request_id,
        phase="final_verification",
        current_service_ids=[],
        completed_service_ids=completed_service_ids,
        failed_service_ids=failed_service_ids,
        current_step_timeout_seconds=0,
    )
    completed_at = now_iso()
    receipt = {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "qadam_operator_full_heal_receipt",
        "generated_at": completed_at,
        "request_id": request_id,
        "operator_service_contract_hash": request.get(
            "operator_service_contract_hash"
        ),
        "git_commit": request.get("git_commit"),
        "status": "completed" if not repair_failed and not dispatch_failed else "blocked",
        "service_ids": list(selected),
        "circuit_repairs": circuit_repairs,
        "operator_cycle": cycle,
        "dispatch_service_checks": dispatch_service_checks,
        "completed_service_ids": completed_service_ids,
        "failed_service_ids": failed_service_ids,
        "all_requested_services_revalidated": not repair_failed and not dispatch_failed,
        "single_operator_owner_used": True,
        "guarded_paperops_wrapper_only": True,
        "paper_only": True,
        "live_capital_enabled": False,
        "autonomous_code_edit_allowed": False,
        "policy_mutation_allowed": False,
        "forced_trade_allowed": False,
        "canonical_paperops_status": paperops_summary.get("status"),
        "canonical_paperops_submitted_order_count": int(
            paper_runtime.get("submitted_paper_order_count") or 0
        ),
        "authority": authority_flags(),
    }
    store = AtomicArtifactStore(runtime)
    store.write_json(FULL_HEAL_RECEIPT_ARTIFACT, receipt)
    latest_request = read_json(runtime / FULL_HEAL_REQUEST_ARTIFACT)
    if latest_request.get("request_id") == request_id:
        store.write_json(
            FULL_HEAL_REQUEST_ARTIFACT,
            {
                **latest_request,
                "status": "completed" if receipt["status"] == "completed" else "blocked",
                "completed_at": completed_at,
                "progress_at": completed_at,
                "current_service_ids": [],
                "current_step_timeout_seconds": 0,
                "receipt_artifact": FULL_HEAL_RECEIPT_ARTIFACT,
            },
        )
    return receipt
