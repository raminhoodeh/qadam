"""Policy and migration contract for Qadam's experimental paper lane.

The experimental lane permits bounded Alpaca Paper observations before an edge
is statistically validated. It never upgrades evidence, grants live authority,
or weakens the validated-strategy contract.
"""

from __future__ import annotations

from collections import Counter
from pathlib import Path
from typing import Any, Iterable, Mapping

from orchestrator.config import Settings
from orchestrator.qadam_canonical_contracts import AtomicArtifactStore
from orchestrator.qadam_operator_ready_common import (
    authority_flags,
    file_sha256,
    now_iso,
    read_json,
    read_jsonl,
    runtime_dir,
    unique_errors,
    validate_authority,
)
from orchestrator.qadam_wave_b_common import stable_id

SCHEMA_VERSION = "qadam_experimental_paper_policy.v3"
POLICY_VERSION = "qadam-experimental-paper.3-frozen-discovery-5k"

POLICY_ARTIFACT = "qadam_experimental_paper_policy.json"
EXECUTION_MODE_ARTIFACT = "qadam_execution_mode.json"
MIGRATION_ARTIFACT = "qadam_experimental_contract_migration.json"
STATUS_ARTIFACT = "qadam_autonomous_experimental_epoch_status.json"

LEGACY_TEST = "legacy_test"
RESEARCH_ONLY = "research_only"
EXPERIMENTAL_UNVALIDATED = "experimental_unvalidated"
VALIDATED_PAPER_STRATEGY = "validated_paper_strategy"
BOUNDED_EXPERIMENTAL_TIER = "bounded_experimental"
DISCOVERY_MICRO_TIER = "discovery_micro"
EXPERIMENTAL_TIERS = {
    BOUNDED_EXPERIMENTAL_TIER,
    DISCOVERY_MICRO_TIER,
}
EVIDENCE_CLASSES = {
    LEGACY_TEST,
    RESEARCH_ONLY,
    EXPERIMENTAL_UNVALIDATED,
    VALIDATED_PAPER_STRATEGY,
}

EXPERIMENTAL_ROUTER_STATE = "experimental_paper_review_candidate"
VALIDATED_ROUTER_STATE = "validated_paper_review_candidate"

COMMON_LINEAGE_FIELDS = (
    "research_goal_id",
    "score_id",
    "hypothesis_id",
    "akber_result_id",
    "shadow_evidence_id",
    "risk_proposal_id",
)
LINEAGE_FIELDS_BY_CLASS = {
    EXPERIMENTAL_UNVALIDATED: (*COMMON_LINEAGE_FIELDS, "pattern_relationship_id"),
    VALIDATED_PAPER_STRATEGY: (*COMMON_LINEAGE_FIELDS, "edge_id"),
}

MIGRATED_JSONL_ARTIFACTS = (
    "qadam_strategy_hypotheses_v3.jsonl",
    "qadam_akber_filter_v3_inputs.jsonl",
    "qadam_akber_filter_v3_results.jsonl",
    "qadam_position_size_proposals.jsonl",
    "qadam_router_v3_decisions.jsonl",
    "qadam_paperops_handoff_v3.jsonl",
    "qadam_paper_trade_lineage.jsonl",
    "qadam_paper_postmortems_v3.jsonl",
    "qadam_learning_attribution_v3.jsonl",
)


def evidence_class(record: Mapping[str, Any] | None) -> str:
    """Return a safe class without upgrading an old record."""

    if not record:
        return LEGACY_TEST
    value = str(record.get("evidence_class") or "").strip()
    return value if value in EVIDENCE_CLASSES else LEGACY_TEST


def experimental_tier(record: Mapping[str, Any] | None) -> str:
    """Default old experimental records to the original bounded tier."""

    if not record or evidence_class(record) != EXPERIMENTAL_UNVALIDATED:
        return BOUNDED_EXPERIMENTAL_TIER
    value = str(record.get("experimental_tier") or "").strip()
    return value if value in EXPERIMENTAL_TIERS else BOUNDED_EXPERIMENTAL_TIER


def required_lineage_fields(value: str) -> tuple[str, ...]:
    return LINEAGE_FIELDS_BY_CLASS.get(value, ())


def validate_class_lineage(
    value: str,
    lineage: Mapping[str, Any] | None,
) -> list[str]:
    errors: list[str] = []
    lineage = lineage if isinstance(lineage, Mapping) else {}
    if value not in {EXPERIMENTAL_UNVALIDATED, VALIDATED_PAPER_STRATEGY}:
        return [f"unsupported_execution_evidence_class:{value or 'missing'}"]
    for field in required_lineage_fields(value):
        if not lineage.get(field):
            errors.append(f"missing_lineage:{field}")
    if value == EXPERIMENTAL_UNVALIDATED and lineage.get("edge_id"):
        errors.append("experimental_lineage_must_not_claim_edge_id")
    if value == VALIDATED_PAPER_STRATEGY and lineage.get("pattern_relationship_id") and not lineage.get(
        "edge_id"
    ):
        errors.append("validated_lineage_requires_edge_id")
    return unique_errors(errors)


def default_policy(generated_at: str | None = None) -> dict[str, Any]:
    generated = generated_at or now_iso()
    return {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "qadam_experimental_paper_policy",
        "generated_at": generated,
        "status": "frozen_operator_reviewed_policy",
        "policy_version": POLICY_VERSION,
        "purpose": "Collect real forward evidence through bounded Alpaca Paper trades without claiming a validated edge.",
        "evidence_classes": {
            LEGACY_TEST: "Archived testing records; never current and never proof eligible.",
            RESEARCH_ONLY: "Research observations that cannot enter PaperOps.",
            EXPERIMENTAL_UNVALIDATED: "Current paper experiment with complete tradeability evidence but no validated edge.",
            VALIDATED_PAPER_STRATEGY: "A strategy backed by a promoted edge and completed forward-shadow evidence.",
        },
        "lineage_fields_by_class": {
            key: list(value) for key, value in LINEAGE_FIELDS_BY_CLASS.items()
        },
        "experimental_admission": {
            "tier": BOUNDED_EXPERIMENTAL_TIER,
            "minimum_research_score": 0.50,
            "minimum_independent_source_families": 2,
            "fresh_provider_backed_evidence_required": True,
            "current_price_required": True,
            "volatility_required": True,
            "volume_or_flow_required": True,
            "positive_provisional_expectancy_after_costs_required": True,
            "decision_time_shadow_snapshot_required": True,
            "completed_forward_shadow_outcome_required": False,
            "validated_edge_required": False,
        },
        "discovery_micro_admission": {
            "tier": DISCOVERY_MICRO_TIER,
            "enabled": True,
            "purpose": (
                "Collect small real paper outcomes for complete directional signals that "
                "are under-observed historically, without calling them validated edges."
            ),
            "minimum_research_score": 0.45,
            "minimum_fresh_catalyst_sources": 1,
            "minimum_catalyst_source_trust": 0.70,
            "causal_source_mapping_required": True,
            "independent_live_market_confirmation_required": True,
            "current_price_required": True,
            "volatility_required": True,
            "volume_or_flow_required": True,
            "confirmation_alternatives": [
                "technical_confirmation",
                "pricing_gap_evidence",
                "nonlinear_quantum_review",
            ],
            "minimum_confirmation_alternatives": 1,
            "positive_historical_expectancy_required": False,
            "positive_current_expectancy_after_costs_required": True,
            "minimum_current_reward_to_risk": 1.25,
            "decision_time_shadow_snapshot_required": True,
            "completed_forward_shadow_outcome_required": False,
            "validated_edge_required": False,
        },
        "risk": {
            "portfolio_policy_version": "qadam-paper-portfolio-risk.3-frozen-discovery-5k",
            "starting_equity_usd": 100000.0,
            "absolute_trade_ceiling_usd": 5000.0,
            "discovery_micro_trade_ceiling_usd": 5000.0,
            "maximum_concurrent_discovery_micro_positions": 1,
            "experimental_risk_multiplier": 0.50,
            "discovery_micro_risk_multiplier": 0.10,
            "validated_risk_multiplier": 1.0,
            "risk_or_authority_mutation_allowed": False,
        },
        "route": {
            "required": "guarded_alpaca_paper_via_paperops",
            "canonical_wrapper": ".venv/bin/python scripts/run_paperops_autonomous_pass.py",
            "alpaca_paper_endpoint": "https://paper-api.alpaca.markets",
            "direct_broker_call_allowed": False,
            "automatic_ambiguous_write_retry_allowed": False,
        },
        "proof": {
            "experimental_trade_fact_allowed_after_real_close": True,
            "experimental_outcome_allowed_after_real_close": True,
            "validated_edge_credit_allowed": False,
            "automatic_edge_promotion_allowed": False,
            "discovery_micro_validated_edge_credit_allowed": False,
        },
        "calendar": {
            "real_release_timestamp_only": True,
            "backfill_allowed": False,
            "simulated_elapsed_time_allowed": False,
        },
        "operator_approval": {
            "one_time_bounded_experimental_mandate_required": True,
            "individual_trade_human_approval_required_after_mandate": False,
            "policy_transition_must_be_version_bound": True,
        },
        "live_capital_enabled": False,
        "authority": authority_flags(),
    }


def validate_policy(policy: Mapping[str, Any]) -> list[str]:
    errors: list[str] = []
    if policy.get("policy_version") != POLICY_VERSION:
        errors.append("experimental_policy_version_unknown")
    if policy.get("live_capital_enabled") is not False:
        errors.append("experimental_policy_live_capital_enabled")
    if policy.get("route", {}).get("required") != "guarded_alpaca_paper_via_paperops":
        errors.append("experimental_policy_route_not_guarded")
    if policy.get("route", {}).get("direct_broker_call_allowed") is not False:
        errors.append("experimental_policy_direct_broker_call_allowed")
    if float(policy.get("risk", {}).get("absolute_trade_ceiling_usd") or 0) != 5000.0:
        errors.append("experimental_policy_trade_ceiling_changed")
    micro = policy.get("discovery_micro_admission", {})
    if micro.get("enabled") is not True:
        errors.append("experimental_policy_discovery_micro_disabled")
    if float(policy.get("risk", {}).get("discovery_micro_trade_ceiling_usd") or 0) != 5000.0:
        errors.append("experimental_policy_discovery_micro_ceiling_changed")
    if policy.get("risk", {}).get("portfolio_policy_version") != (
        "qadam-paper-portfolio-risk.3-frozen-discovery-5k"
    ):
        errors.append("experimental_policy_portfolio_policy_version_changed")
    if int(
        policy.get("risk", {}).get("maximum_concurrent_discovery_micro_positions") or 0
    ) != 1:
        errors.append("experimental_policy_discovery_micro_concurrency_changed")
    if float(micro.get("minimum_research_score") or 0) < 0.45:
        errors.append("experimental_policy_discovery_micro_score_too_low")
    if int(micro.get("minimum_fresh_catalyst_sources") or 0) < 1:
        errors.append("experimental_policy_discovery_micro_catalyst_missing")
    if micro.get("independent_live_market_confirmation_required") is not True:
        errors.append("experimental_policy_discovery_micro_market_confirmation_not_required")
    if micro.get("positive_current_expectancy_after_costs_required") is not True:
        errors.append("experimental_policy_discovery_micro_positive_expectancy_not_required")
    if policy.get("experimental_admission", {}).get("validated_edge_required") is not False:
        errors.append("experimental_policy_incorrectly_requires_validated_edge")
    if policy.get("proof", {}).get("validated_edge_credit_allowed") is not False:
        errors.append("experimental_policy_grants_edge_credit")
    if policy.get("calendar", {}).get("backfill_allowed") is not False:
        errors.append("experimental_policy_allows_calendar_backfill")
    errors.extend(validate_authority(policy.get("authority", {}), prefix="experimental_policy"))
    return unique_errors(errors)


def _execution_mode(runtime: Path, policy: Mapping[str, Any], generated_at: str) -> dict[str, Any]:
    epoch = read_json(runtime / "current_paper_epoch.json")
    release = read_json(runtime / "qadam_experimental_paper_release_readiness.json")
    lock = read_json(runtime / "qadam_long_backtest_lock.json")
    experimental_active = bool(
        epoch.get("paper_epoch_kind") == "clean_experimental_operator_epoch"
        and release.get("experimental_paper_release_effective") is True
        and lock.get("status") == "released"
        and lock.get("paperops_watch_only_mode") is False
    )
    return {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "qadam_execution_mode",
        "generated_at": generated_at,
        "policy_version": policy.get("policy_version"),
        "status": "experimental_paper_active" if experimental_active else "research_watch_only",
        "research_enabled": True,
        "experimental_paper_enabled": experimental_active,
        "validated_paper_enabled": False,
        "live_capital_enabled": False,
        "active_evidence_class": EXPERIMENTAL_UNVALIDATED if experimental_active else RESEARCH_ONLY,
        "active_paper_epoch_id": epoch.get("paper_epoch_id"),
        "paperops_watch_only": not experimental_active,
        "unknown_mode_fails_closed": True,
        "authority": authority_flags(),
    }


def _migration_rows(runtime: Path) -> tuple[list[dict[str, Any]], Counter[str]]:
    rows: list[dict[str, Any]] = []
    counts: Counter[str] = Counter()
    for name in MIGRATED_JSONL_ARTIFACTS:
        path = runtime / name
        records = read_jsonl(path)
        explicit = sum(
            1 for record in records if str(record.get("evidence_class") or "") in EVIDENCE_CLASSES
        )
        legacy = len(records) - explicit
        counts["record_count"] += len(records)
        counts["explicit_class_count"] += explicit
        counts["legacy_default_count"] += legacy
        rows.append(
            {
                "artifact": f"data/runtime/{name}",
                "exists": path.is_file(),
                "record_count": len(records),
                "explicit_class_count": explicit,
                "legacy_default_count": legacy,
                "legacy_rows_rewritten": 0,
                "sha256": file_sha256(path),
            }
        )
    return rows, counts


def build_contract_migration(runtime: Path, generated_at: str) -> dict[str, Any]:
    rows, counts = _migration_rows(runtime)
    return {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "qadam_experimental_contract_migration",
        "generated_at": generated_at,
        "status": "passed_legacy_defaults_fail_closed",
        "migration_id": stable_id("experimental-contract-migration", rows),
        "artifact_count": len(rows),
        "record_count": counts["record_count"],
        "explicit_class_count": counts["explicit_class_count"],
        "legacy_default_count": counts["legacy_default_count"],
        "legacy_rows_rewritten": 0,
        "legacy_rows_upgraded_to_experimental": 0,
        "legacy_rows_upgraded_to_validated": 0,
        "default_for_missing_or_unknown_class": LEGACY_TEST,
        "artifacts": rows,
        "authority": authority_flags(),
    }


def validate_contract_migration(migration: Mapping[str, Any]) -> list[str]:
    errors: list[str] = []
    for field in (
        "legacy_rows_rewritten",
        "legacy_rows_upgraded_to_experimental",
        "legacy_rows_upgraded_to_validated",
    ):
        if int(migration.get(field) or 0) != 0:
            errors.append(f"experimental_migration_forbidden_count:{field}")
    if migration.get("default_for_missing_or_unknown_class") != LEGACY_TEST:
        errors.append("experimental_migration_unsafe_legacy_default")
    errors.extend(validate_authority(migration.get("authority", {}), prefix="experimental_migration"))
    return unique_errors(errors)


def build_status(
    runtime: Path,
    policy: Mapping[str, Any],
    mode: Mapping[str, Any],
    migration: Mapping[str, Any],
    errors: Iterable[str],
    generated_at: str,
) -> dict[str, Any]:
    errors = unique_errors(errors)
    epoch = read_json(runtime / "current_paper_epoch.json")
    certification = read_json(
        runtime / "qadam_autonomous_experimental_paper_epoch_certification.json"
    )
    implementation_complete = bool(
        not errors and certification.get("implementation_complete") is True
    )
    operation_running = certification.get(
        "autonomous_experimental_paper_operation_running"
    ) is True
    return {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "qadam_autonomous_experimental_epoch_status",
        "generated_at": generated_at,
        "status": (
            "autonomous_experimental_paper_operation_running"
            if operation_running
            else "implementation_complete_waiting_for_operational_cutover"
            if implementation_complete
            else "implementation_foundation_ready"
            if not errors
            else "blocked"
        ),
        "implementation_foundation_ready": not errors,
        "implementation_complete": implementation_complete,
        "autonomous_experimental_paper_operation_running": operation_running,
        "unattended_reliability_certified": certification.get(
            "unattended_reliability_certified"
        )
        is True,
        "final_certification_ref": (
            "data/runtime/qadam_autonomous_experimental_paper_epoch_certification.json"
        ),
        "policy_version": policy.get("policy_version"),
        "execution_mode": mode.get("status"),
        "paper_epoch_id": epoch.get("paper_epoch_id"),
        "paper_epoch_kind": epoch.get("paper_epoch_kind") or LEGACY_TEST,
        "experimental_paper_enabled": mode.get("experimental_paper_enabled") is True,
        "validated_paper_enabled": mode.get("validated_paper_enabled") is True,
        "live_capital_enabled": False,
        "legacy_default_count": migration.get("legacy_default_count", 0),
        "blocker_count": len(errors),
        "blockers": list(errors),
        "authority": authority_flags(),
    }


def build_and_write_experimental_policy(
    settings: Settings | None = None,
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any], dict[str, Any], list[str]]:
    runtime = runtime_dir(settings)
    generated = now_iso()
    policy = default_policy(generated)
    migration = build_contract_migration(runtime, generated)
    mode = _execution_mode(runtime, policy, generated)
    errors = unique_errors(
        [*validate_policy(policy), *validate_contract_migration(migration)]
    )
    if mode.get("live_capital_enabled") is not False:
        errors.append("experimental_execution_mode_live_capital_enabled")
    if mode.get("experimental_paper_enabled") is True and mode.get(
        "active_evidence_class"
    ) != EXPERIMENTAL_UNVALIDATED:
        errors.append("experimental_execution_mode_class_mismatch")
    errors = unique_errors(errors)
    status = build_status(runtime, policy, mode, migration, errors, generated)
    store = AtomicArtifactStore(runtime)
    store.write_json(POLICY_ARTIFACT, policy)
    store.write_json(EXECUTION_MODE_ARTIFACT, mode)
    store.write_json(MIGRATION_ARTIFACT, migration)
    store.write_json(STATUS_ARTIFACT, status)
    return policy, mode, migration, status, errors


__all__ = [
    "COMMON_LINEAGE_FIELDS",
    "BOUNDED_EXPERIMENTAL_TIER",
    "DISCOVERY_MICRO_TIER",
    "EVIDENCE_CLASSES",
    "EXPERIMENTAL_TIERS",
    "EXECUTION_MODE_ARTIFACT",
    "EXPERIMENTAL_ROUTER_STATE",
    "EXPERIMENTAL_UNVALIDATED",
    "LEGACY_TEST",
    "LINEAGE_FIELDS_BY_CLASS",
    "MIGRATION_ARTIFACT",
    "POLICY_ARTIFACT",
    "POLICY_VERSION",
    "RESEARCH_ONLY",
    "STATUS_ARTIFACT",
    "VALIDATED_PAPER_STRATEGY",
    "VALIDATED_ROUTER_STATE",
    "build_and_write_experimental_policy",
    "build_contract_migration",
    "default_policy",
    "evidence_class",
    "experimental_tier",
    "required_lineage_fields",
    "validate_class_lineage",
    "validate_contract_migration",
    "validate_policy",
]
