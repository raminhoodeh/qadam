"""Phase 7 Demo Proof artifact contracts.

Q7-1 defines the shared schema, proof authority ledger, event names, source
posture, and provenance rules for the 30-day Demo Proof harness. It is
schema-only: it does not start the proof harness, create qualified setups,
auto-approve trades, stage or submit proof orders, grant proof credit, or
enable live capital.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from typing import Any

from orchestrator.phase7_readiness import (
    PHASE7_AUTHORITY_FLAGS,
    PHASE7_HARNESS_DAY_COUNT,
    PHASE7_MATURE_CLOSED_TRADE_BENCHMARK,
    PHASE7_MAX_DRAWDOWN_FRACTION,
    PHASE7_PAPER_ACCOUNT_STARTING_GBP,
    PHASE7_UNSAFE_COUNT_FIELDS,
    PHASE7_WEEKLY_PROOF_TRADE_TARGET,
)
from world_monitor.source_registry import EXPECTED_SOURCE_COUNT


PHASE7_ARTIFACT_SCHEMA_VERSION = 1

PHASE7_STATUS_ENUMS: tuple[str, ...] = (
    "blocked",
    "schema_only",
    "read_only",
    "planned",
    "eligible",
    "qualified",
    "auto_approved",
    "staged",
    "submitted",
    "open",
    "closed",
    "postmortem_due",
    "postmortem_complete",
    "evaluated",
    "halted",
    "contaminated",
    "visible",
    "certified",
    "statistically_immature",
)

PHASE7_ARTIFACT_TYPES: tuple[str, ...] = (
    "proof_authority_ledger",
    "proof_calendar_day",
    "proof_week",
    "qualified_setup",
    "proof_candidate",
    "auto_approval_decision",
    "staged_proof_order",
    "proof_broker_receipt",
    "proof_lifecycle_event",
    "proof_postmortem_packet",
    "performance_evaluation",
    "drawdown_risk_sentinel",
    "override_detection",
    "source_signal_funnel_evidence",
    "maturity_snapshot",
    "cockpit_proof_visibility",
    "weekly_review_pack",
    "phase7_certification",
    "live_promotion_review",
)

PHASE7_COMMON_REQUIRED_FIELDS: tuple[str, ...] = (
    "schema_version",
    "artifact_type",
    "artifact_id",
    "phase",
    "stage",
    "status",
    "generated_at",
    "public_safe",
    "event_log_required",
    "event_log_written",
    "event_log_correlation_id",
    "event_contract",
    "authority_ledger",
    "proof_contract",
    "source_posture",
    "provenance",
    "boundary",
)

PHASE7_SOURCE_POSTURE_REQUIRED_FIELDS: tuple[str, ...] = (
    "canonical_source_required",
    "canonical_source_count",
    "supplemental_source_bypass_allowed",
    "yahoo_finance_role",
    "preference_mcp_role",
    "preference_mcp_source_quorum_credit_allowed",
    "qctrl_role",
    "private_world_model_role",
    "phase5_test_lifecycle_role",
    "phase6_deferred_learning_role",
    "source_quorum_bypass_allowed",
)

PHASE7_PROVENANCE_REQUIRED_FIELDS: tuple[str, ...] = (
    "source_refs",
    "event_log_required",
    "raw_secret_exposed",
    "raw_payload_exposed",
    "local_path_exposed",
    "broker_identifier_exposed",
    "decision_chain_refs",
    "execution_evidence_refs",
    "market_context_refs",
    "governance_refs",
    "proof_lifecycle_refs",
)

PHASE7_EVENT_TYPES: dict[str, str] = {
    "artifact_schema": "phase7_artifact_schema_recorded",
    "proof_calendar": "phase7_proof_calendar_recorded",
    "qualified_setup": "phase7_qualified_setup_recorded",
    "weekly_cadence": "phase7_weekly_cadence_recorded",
    "auto_approval": "phase7_auto_approval_recorded",
    "staged_order": "phase7_staged_proof_order_recorded",
    "broker_receipt": "phase7_broker_receipt_recorded",
    "proof_lifecycle": "phase7_proof_lifecycle_recorded",
    "postmortem": "phase7_postmortem_recorded",
    "performance": "phase7_performance_recorded",
    "risk_halt": "phase7_risk_halt_recorded",
    "override": "phase7_override_recorded",
    "signal_evidence": "phase7_signal_evidence_recorded",
    "maturity": "phase7_maturity_recorded",
    "visibility": "phase7_visibility_recorded",
    "weekly_review": "phase7_weekly_review_recorded",
    "certification": "phase7_certification_recorded",
    "live_promotion": "phase7_live_promotion_review_recorded",
}

PHASE7_REQUIRED_EVENT_CATEGORIES: tuple[str, ...] = tuple(PHASE7_EVENT_TYPES)


@dataclass(frozen=True)
class Phase7ArtifactContract:
    artifact_type: str
    description: str
    required_fields: tuple[str, ...]
    allowed_statuses: tuple[str, ...]
    default_status: str
    event_category: str
    boundary: str

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["required_fields"] = list(self.required_fields)
        payload["allowed_statuses"] = list(self.allowed_statuses)
        return payload


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def phase7_authority_defaults() -> dict[str, bool]:
    return {field: False for field in PHASE7_AUTHORITY_FLAGS}


def phase7_unsafe_counter_defaults() -> dict[str, int]:
    return {field: 0 for field in PHASE7_UNSAFE_COUNT_FIELDS}


def phase7_authority_ledger() -> dict[str, Any]:
    return {
        "authority_schema_version": PHASE7_ARTIFACT_SCHEMA_VERSION,
        "stage": "Q7-1",
        "authority_field_count": len(PHASE7_AUTHORITY_FLAGS),
        "explicit_authority_grant_count": 0,
        **phase7_authority_defaults(),
        "boundary": (
            "Q7-1 defines Phase 7 artifact shapes only. Every proof, broker, "
            "override, live-capital, and proof-credit authority flag defaults "
            "false until a later Q7 gate explicitly grants and validates a "
            "narrower permission."
        ),
    }


def phase7_proof_contract() -> dict[str, Any]:
    return {
        "contract_schema_version": PHASE7_ARTIFACT_SCHEMA_VERSION,
        "harness_day_count": PHASE7_HARNESS_DAY_COUNT,
        "consecutive_calendar_days_required": True,
        "weekly_proof_trade_target": PHASE7_WEEKLY_PROOF_TRADE_TARGET,
        "weekly_target_applies_only_where_qualified_setups_exist": True,
        "weekly_target_formula": "min(3, qualified_setup_count)",
        "no_forced_trades": True,
        "qualified_setup_ledger_required": True,
        "paper_account_starting_gbp": PHASE7_PAPER_ACCOUNT_STARTING_GBP,
        "max_drawdown_fraction": PHASE7_MAX_DRAWDOWN_FRACTION,
        "mature_closed_trade_benchmark": PHASE7_MATURE_CLOSED_TRADE_BENCHMARK,
        "statistical_immaturity_allowed": True,
        "phase5_test_trade_reuse_allowed": False,
        "q6_deferred_learning_counts_as_proof": False,
        "manual_trade_level_override_allowed": False,
        "local_first_proof_storage_required": True,
    }


def phase7_source_posture() -> dict[str, Any]:
    return {
        "canonical_source_required": True,
        "canonical_source_count": EXPECTED_SOURCE_COUNT,
        "supplemental_source_bypass_allowed": False,
        "yahoo_finance_role": "supplemental_market_confirmation_only",
        "preference_mcp_role": "supplemental_multi_source_data_plane",
        "preference_mcp_source_quorum_credit_allowed": False,
        "qctrl_role": "shadow_annotation_only",
        "private_world_model_role": "context_not_proof",
        "phase5_test_lifecycle_role": "excluded_from_phase7_proof",
        "phase6_deferred_learning_role": "context_not_proof",
        "source_quorum_bypass_allowed": False,
        "boundary": (
            "Phase 7 proof artifacts must keep source quorum, supplemental "
            "market context, private priors, Q6 deferred learning context, and "
            "broker/paper lifecycle evidence separate. Yahoo Finance and "
            "Preference/PREF MCP remain supplemental by default."
        ),
    }


def phase7_provenance(source_refs: tuple[str, ...] | None = None) -> dict[str, Any]:
    return {
        "source_refs": list(
            source_refs
            or (
                "data/runtime/phase7_readiness.json",
                "data/runtime/phase6_certification.json",
                "docs/qadam-phase-7-demo-proof-implementation-plan.md",
            )
        ),
        "event_log_required": True,
        "raw_secret_exposed": False,
        "raw_payload_exposed": False,
        "local_path_exposed": False,
        "broker_identifier_exposed": False,
        "decision_chain_refs": [],
        "execution_evidence_refs": [],
        "market_context_refs": [],
        "governance_refs": [],
        "proof_lifecycle_refs": [],
        "boundary": (
            "Phase 7 artifacts must cite public-safe relative source refs and "
            "must not expose secrets, raw private payloads, broker identifiers, "
            "or local-only absolute paths."
        ),
    }


def phase7_event_contract(event_category: str) -> dict[str, Any]:
    event_type = PHASE7_EVENT_TYPES[event_category]
    return {
        "event_schema_version": PHASE7_ARTIFACT_SCHEMA_VERSION,
        "event_category": event_category,
        "event_type": event_type,
        "event_log_required": True,
        "append_only": True,
        "supersession_required_for_change": True,
        "raw_secret_exposed": False,
        "raw_payload_exposed": False,
        "broker_identifier_exposed": False,
        "boundary": (
            "Phase 7 events are append-only proof audit records. They cannot "
            "hide forced trades, manual trade-level overrides, Phase 5 proof "
            "reuse, live capital, or false proof credit."
        ),
    }


def phase7_event_contracts() -> dict[str, dict[str, Any]]:
    return {
        category: phase7_event_contract(category)
        for category in PHASE7_REQUIRED_EVENT_CATEGORIES
    }


def phase7_artifact_contracts() -> tuple[Phase7ArtifactContract, ...]:
    common = PHASE7_COMMON_REQUIRED_FIELDS
    return (
        Phase7ArtifactContract(
            artifact_type="proof_authority_ledger",
            description="Shared proof authority ledger for every Phase 7 artifact.",
            required_fields=common
            + ("authority_field_count", "explicit_authority_grant_count"),
            allowed_statuses=("schema_only", "blocked"),
            default_status="schema_only",
            event_category="artifact_schema",
            boundary="The authority ledger can describe permissions but cannot grant them in Q7-1.",
        ),
        Phase7ArtifactContract(
            artifact_type="proof_calendar_day",
            description="30-day consecutive calendar harness day contract.",
            required_fields=common
            + ("proof_day_number", "calendar_date", "harness_start_allowed"),
            allowed_statuses=("schema_only", "blocked", "planned"),
            default_status="schema_only",
            event_category="proof_calendar",
            boundary=(
                "Calendar day records can define shape only and cannot create "
                "or start the proof harness."
            ),
        ),
        Phase7ArtifactContract(
            artifact_type="proof_week",
            description="Proof-week cadence accounting contract.",
            required_fields=common
            + ("proof_week_number", "weekly_target", "forced_trade_allowed"),
            allowed_statuses=("schema_only", "blocked", "planned"),
            default_status="schema_only",
            event_category="weekly_cadence",
            boundary="Proof-week records cannot force trades or bypass qualified setup evidence.",
        ),
        Phase7ArtifactContract(
            artifact_type="qualified_setup",
            description="Qualified setup ledger contract.",
            required_fields=common
            + ("setup_state", "source_quorum_required", "qualified_setup_creation_allowed"),
            allowed_statuses=("schema_only", "blocked", "eligible", "qualified"),
            default_status="schema_only",
            event_category="qualified_setup",
            boundary="Qualified setup records cannot be created in Q7-1 and cannot rely on supplemental-only evidence.",
        ),
        Phase7ArtifactContract(
            artifact_type="proof_candidate",
            description="Candidate proof-trade decision contract.",
            required_fields=common
            + ("candidate_state", "phase5_reuse_allowed", "proof_candidate_creation_allowed"),
            allowed_statuses=("schema_only", "blocked", "eligible"),
            default_status="schema_only",
            event_category="qualified_setup",
            boundary=(
                "Proof candidates cannot create proof trades or reuse Phase 5 "
                "lifecycle records in Q7-1."
            ),
        ),
        Phase7ArtifactContract(
            artifact_type="auto_approval_decision",
            description="Test-mode auto-approval decision contract.",
            required_fields=common
            + ("approval_state", "manual_trade_level_approval_allowed", "auto_approval_allowed"),
            allowed_statuses=("schema_only", "blocked", "auto_approved"),
            default_status="schema_only",
            event_category="auto_approval",
            boundary="Auto-approval decisions cannot be created before later Q7 policy gates pass.",
        ),
        Phase7ArtifactContract(
            artifact_type="staged_proof_order",
            description="Phase 7 proof order staging contract.",
            required_fields=common
            + ("order_state", "idempotency_required", "proof_order_staging_allowed"),
            allowed_statuses=("schema_only", "blocked", "staged"),
            default_status="schema_only",
            event_category="staged_order",
            boundary="Staged proof orders cannot be created before later auto-approval and staging gates pass.",
        ),
        Phase7ArtifactContract(
            artifact_type="proof_broker_receipt",
            description="Alpaca paper broker receipt contract for proof orders.",
            required_fields=common + ("receipt_state", "broker_post_allowed", "live_endpoint_allowed"),
            allowed_statuses=("schema_only", "blocked", "submitted"),
            default_status="schema_only",
            event_category="broker_receipt",
            boundary=(
                "Broker receipts cannot submit broker POST routes or enable "
                "live endpoints in Q7-1."
            ),
        ),
        Phase7ArtifactContract(
            artifact_type="proof_lifecycle_event",
            description="Proof trade lifecycle event contract.",
            required_fields=common
            + ("lifecycle_state", "proof_lifecycle_write_allowed", "reconciliation_required"),
            allowed_statuses=("schema_only", "blocked", "submitted", "open", "closed"),
            default_status="schema_only",
            event_category="proof_lifecycle",
            boundary="Proof lifecycle records cannot write proof state before later paper lifecycle gates pass.",
        ),
        Phase7ArtifactContract(
            artifact_type="proof_postmortem_packet",
            description="Postmortem packet contract for closed proof trades.",
            required_fields=common
            + (
                "postmortem_state",
                "postmortem_write_allowed",
                "all_closed_trades_require_postmortem",
            ),
            allowed_statuses=("schema_only", "blocked", "postmortem_due", "postmortem_complete"),
            default_status="schema_only",
            event_category="postmortem",
            boundary=(
                "Postmortem packet contracts cannot create postmortems and can "
                "define proof requirements only in Q7-1."
            ),
        ),
        Phase7ArtifactContract(
            artifact_type="performance_evaluation",
            description="Proof performance and expectancy evaluation contract.",
            required_fields=common
            + ("evaluation_state", "expectancy_after_costs", "performance_evaluation_write_allowed"),
            allowed_statuses=("schema_only", "blocked", "evaluated"),
            default_status="schema_only",
            event_category="performance",
            boundary=(
                "Performance evaluations cannot enable proof certification or "
                "hide immature sample size."
            ),
        ),
        Phase7ArtifactContract(
            artifact_type="drawdown_risk_sentinel",
            description="20 percent max drawdown sentinel contract.",
            required_fields=common + ("drawdown_state", "max_drawdown_fraction", "risk_halt_allowed"),
            allowed_statuses=("schema_only", "blocked", "halted"),
            default_status="schema_only",
            event_category="risk_halt",
            boundary="Risk sentinels can define halt conditions only and cannot enable new proof trades.",
        ),
        Phase7ArtifactContract(
            artifact_type="override_detection",
            description="Manual trade-level override detector contract.",
            required_fields=common
            + ("override_state", "manual_trade_level_override_allowed", "override_count"),
            allowed_statuses=("schema_only", "blocked", "contaminated"),
            default_status="schema_only",
            event_category="override",
            boundary=(
                "Override detection cannot approve or permit manual "
                "trade-level intervention."
            ),
        ),
        Phase7ArtifactContract(
            artifact_type="source_signal_funnel_evidence",
            description="Source quorum and signal-chain evidence contract.",
            required_fields=common
            + ("evidence_state", "decision_chain_required", "private_prior_counts_as_proof"),
            allowed_statuses=("schema_only", "blocked", "read_only"),
            default_status="schema_only",
            event_category="signal_evidence",
            boundary=(
                "Signal evidence cannot infer proof from private priors or "
                "supplemental-only sources."
            ),
        ),
        Phase7ArtifactContract(
            artifact_type="maturity_snapshot",
            description="100 closed proof-trade maturity benchmark contract.",
            required_fields=common
            + ("maturity_state", "closed_proof_trade_count", "mature_benchmark"),
            allowed_statuses=("schema_only", "blocked", "statistically_immature", "certified"),
            default_status="schema_only",
            event_category="maturity",
            boundary="Maturity snapshots cannot hide immature sample size or force trades.",
        ),
        Phase7ArtifactContract(
            artifact_type="cockpit_proof_visibility",
            description="Public-safe Phase 7 cockpit visibility contract.",
            required_fields=common
            + ("visibility_state", "backend_derived", "ui_inferred_readiness_count"),
            allowed_statuses=("schema_only", "blocked", "visible"),
            default_status="schema_only",
            event_category="visibility",
            boundary="Visibility records must be backend-derived and cannot infer proof readiness from the UI.",
        ),
        Phase7ArtifactContract(
            artifact_type="weekly_review_pack",
            description="Weekly Fund Manager proof review packet contract.",
            required_fields=common
            + ("review_state", "trade_level_intervention_allowed", "weekly_review_packet_created"),
            allowed_statuses=("schema_only", "blocked", "read_only"),
            default_status="schema_only",
            event_category="weekly_review",
            boundary="Weekly review packs cannot mutate individual proof trades.",
        ),
        Phase7ArtifactContract(
            artifact_type="phase7_certification",
            description="30-day Demo Proof certification contract.",
            required_fields=common
            + ("phase7_demo_proof_certified", "phase7_mature_benchmark_met", "live_capital_enabled"),
            allowed_statuses=("schema_only", "blocked", "certified", "statistically_immature"),
            default_status="schema_only",
            event_category="certification",
            boundary="Certification can summarize Phase 7 only and cannot enable live capital in Q7-1.",
        ),
        Phase7ArtifactContract(
            artifact_type="live_promotion_review",
            description="Structured live-promotion review contract.",
            required_fields=common
            + ("live_promotion_review_state", "live_credentials_enabled", "cooling_off_required"),
            allowed_statuses=("schema_only", "blocked", "read_only"),
            default_status="schema_only",
            event_category="live_promotion",
            boundary="Live promotion reviews cannot load live credentials or enable live capital in Q7-1.",
        ),
    )


def phase7_contract_by_type() -> dict[str, Phase7ArtifactContract]:
    return {contract.artifact_type: contract for contract in phase7_artifact_contracts()}


def _base_artifact(artifact_type: str, *, status: str | None = None) -> dict[str, Any]:
    contract = phase7_contract_by_type()[artifact_type]
    return {
        "schema_version": PHASE7_ARTIFACT_SCHEMA_VERSION,
        "artifact_type": artifact_type,
        "artifact_id": f"sample:q7-1:{artifact_type}",
        "phase": "Q7",
        "stage": "Q7-1",
        "status": status or contract.default_status,
        "generated_at": _now(),
        "public_safe": True,
        "event_log_required": True,
        "event_log_written": False,
        "event_log_correlation_id": None,
        "event_contract": phase7_event_contract(contract.event_category),
        "authority_ledger": phase7_authority_ledger(),
        "proof_contract": phase7_proof_contract(),
        "source_posture": phase7_source_posture(),
        "provenance": phase7_provenance(),
        "boundary": contract.boundary,
        **phase7_authority_defaults(),
        **phase7_unsafe_counter_defaults(),
    }


def build_phase7_sample_artifacts() -> list[dict[str, Any]]:
    return [
        {
            **_base_artifact("proof_authority_ledger"),
            "authority_field_count": len(PHASE7_AUTHORITY_FLAGS),
            "explicit_authority_grant_count": 0,
        },
        {
            **_base_artifact("proof_calendar_day"),
            "proof_day_number": 0,
            "calendar_date": None,
            "harness_start_allowed": False,
        },
        {
            **_base_artifact("proof_week"),
            "proof_week_number": 0,
            "weekly_target": PHASE7_WEEKLY_PROOF_TRADE_TARGET,
            "forced_trade_allowed": False,
        },
        {
            **_base_artifact("qualified_setup"),
            "setup_state": "schema_only_not_created",
            "source_quorum_required": True,
            "qualified_setup_creation_allowed": False,
        },
        {
            **_base_artifact("proof_candidate"),
            "candidate_state": "schema_only_not_created",
            "phase5_reuse_allowed": False,
            "proof_candidate_creation_allowed": False,
        },
        {
            **_base_artifact("auto_approval_decision"),
            "approval_state": "schema_only_not_requested",
            "manual_trade_level_approval_allowed": False,
            "auto_approval_allowed": False,
        },
        {
            **_base_artifact("staged_proof_order"),
            "order_state": "schema_only_not_staged",
            "idempotency_required": True,
            "proof_order_staging_allowed": False,
        },
        {
            **_base_artifact("proof_broker_receipt"),
            "receipt_state": "schema_only_not_submitted",
            "broker_post_allowed": False,
            "live_endpoint_allowed": False,
        },
        {
            **_base_artifact("proof_lifecycle_event"),
            "lifecycle_state": "schema_only_not_created",
            "proof_lifecycle_write_allowed": False,
            "reconciliation_required": True,
        },
        {
            **_base_artifact("proof_postmortem_packet"),
            "postmortem_state": "schema_only_not_due",
            "postmortem_write_allowed": False,
            "all_closed_trades_require_postmortem": True,
        },
        {
            **_base_artifact("performance_evaluation"),
            "evaluation_state": "schema_only_not_evaluated",
            "expectancy_after_costs": None,
            "performance_evaluation_write_allowed": False,
        },
        {
            **_base_artifact("drawdown_risk_sentinel"),
            "drawdown_state": "schema_only_not_active",
            "max_drawdown_fraction": PHASE7_MAX_DRAWDOWN_FRACTION,
            "risk_halt_allowed": False,
        },
        {
            **_base_artifact("override_detection"),
            "override_state": "schema_only_not_checked",
            "manual_trade_level_override_allowed": False,
            "override_count": 0,
        },
        {
            **_base_artifact("source_signal_funnel_evidence"),
            "evidence_state": "schema_only_not_checked",
            "decision_chain_required": True,
            "private_prior_counts_as_proof": False,
        },
        {
            **_base_artifact("maturity_snapshot"),
            "maturity_state": "schema_only_not_started",
            "closed_proof_trade_count": 0,
            "mature_benchmark": PHASE7_MATURE_CLOSED_TRADE_BENCHMARK,
        },
        {
            **_base_artifact("cockpit_proof_visibility"),
            "visibility_state": "schema_only_not_visible",
            "backend_derived": True,
            "ui_inferred_readiness_count": 0,
        },
        {
            **_base_artifact("weekly_review_pack"),
            "review_state": "schema_only_not_created",
            "trade_level_intervention_allowed": False,
            "weekly_review_packet_created": False,
        },
        {
            **_base_artifact("phase7_certification"),
            "phase7_demo_proof_certified": False,
            "phase7_mature_benchmark_met": False,
            "live_capital_enabled": False,
        },
        {
            **_base_artifact("live_promotion_review"),
            "live_promotion_review_state": "schema_only_not_created",
            "live_credentials_enabled": False,
            "cooling_off_required": True,
        },
    ]


def _authority_errors(artifact: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    ledger = artifact.get("authority_ledger")
    if not isinstance(ledger, dict):
        return ["authority_ledger_missing_or_invalid"]
    if ledger.get("authority_field_count") != len(PHASE7_AUTHORITY_FLAGS):
        errors.append("authority_field_count_mismatch")
    if ledger.get("explicit_authority_grant_count", 0) != 0:
        errors.append("explicit_authority_grant_count_nonzero")
    for field in PHASE7_AUTHORITY_FLAGS:
        if field not in ledger:
            errors.append(f"authority_ledger_field_missing:{field}")
        elif ledger.get(field) is not False:
            errors.append(f"authority_ledger_enabled:{field}")
        if field not in artifact:
            errors.append(f"authority_field_missing:{field}")
        elif artifact.get(field) is not False:
            errors.append(f"authority_enabled:{field}")
        if field in ledger and field in artifact and ledger.get(field) != artifact.get(field):
            errors.append(f"authority_field_mismatch:{field}")
    return errors


def _unsafe_counter_errors(artifact: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    for field in PHASE7_UNSAFE_COUNT_FIELDS:
        if field not in artifact:
            errors.append(f"unsafe_counter_missing:{field}")
        elif int(artifact.get(field, 0) or 0) != 0:
            errors.append(f"unsafe_counter_nonzero:{field}")
    return errors


def _proof_contract_errors(artifact: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    contract = artifact.get("proof_contract")
    if not isinstance(contract, dict):
        return ["proof_contract_missing_or_invalid"]
    expected_values = {
        "harness_day_count": PHASE7_HARNESS_DAY_COUNT,
        "weekly_proof_trade_target": PHASE7_WEEKLY_PROOF_TRADE_TARGET,
        "mature_closed_trade_benchmark": PHASE7_MATURE_CLOSED_TRADE_BENCHMARK,
    }
    for field, expected in expected_values.items():
        if contract.get(field) != expected:
            errors.append(f"proof_contract_mismatch:{field}")
    if float(contract.get("paper_account_starting_gbp", 0.0) or 0.0) != (
        PHASE7_PAPER_ACCOUNT_STARTING_GBP
    ):
        errors.append("proof_contract_paper_account_start_invalid")
    if float(contract.get("max_drawdown_fraction", 0.0) or 0.0) != (
        PHASE7_MAX_DRAWDOWN_FRACTION
    ):
        errors.append("proof_contract_drawdown_cap_invalid")
    for field in (
        "consecutive_calendar_days_required",
        "weekly_target_applies_only_where_qualified_setups_exist",
        "no_forced_trades",
        "qualified_setup_ledger_required",
        "statistical_immaturity_allowed",
        "local_first_proof_storage_required",
    ):
        if contract.get(field) is not True:
            errors.append(f"proof_contract_missing_true:{field}")
    for field in (
        "phase5_test_trade_reuse_allowed",
        "q6_deferred_learning_counts_as_proof",
        "manual_trade_level_override_allowed",
    ):
        if contract.get(field) is not False:
            errors.append(f"proof_contract_forbidden:{field}")
    if contract.get("weekly_target_formula") != "min(3, qualified_setup_count)":
        errors.append("proof_contract_weekly_target_formula_invalid")
    return errors


def _source_posture_errors(artifact: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    posture = artifact.get("source_posture")
    if not isinstance(posture, dict):
        return ["source_posture_missing_or_invalid"]
    for field in PHASE7_SOURCE_POSTURE_REQUIRED_FIELDS:
        if field not in posture:
            errors.append(f"source_posture_field_missing:{field}")
    if posture.get("canonical_source_required") is not True:
        errors.append("canonical_source_not_required")
    if posture.get("canonical_source_count") != EXPECTED_SOURCE_COUNT:
        errors.append("canonical_source_count_mismatch")
    if posture.get("supplemental_source_bypass_allowed") is not False:
        errors.append("supplemental_source_bypass_allowed")
    if posture.get("yahoo_finance_role") != "supplemental_market_confirmation_only":
        errors.append("yahoo_finance_role_invalid")
    if posture.get("preference_mcp_role") != "supplemental_multi_source_data_plane":
        errors.append("preference_mcp_role_invalid")
    if posture.get("preference_mcp_source_quorum_credit_allowed") is not False:
        errors.append("preference_mcp_source_quorum_credit_allowed")
    if posture.get("qctrl_role") != "shadow_annotation_only":
        errors.append("qctrl_role_invalid")
    if posture.get("private_world_model_role") != "context_not_proof":
        errors.append("private_world_model_role_invalid")
    if posture.get("phase5_test_lifecycle_role") != "excluded_from_phase7_proof":
        errors.append("phase5_test_lifecycle_role_invalid")
    if posture.get("phase6_deferred_learning_role") != "context_not_proof":
        errors.append("phase6_deferred_learning_role_invalid")
    if posture.get("source_quorum_bypass_allowed") is not False:
        errors.append("source_quorum_bypass_allowed")
    return errors


def _has_local_path(ref: str) -> bool:
    if ref.startswith("/") or ref.startswith("~"):
        return True
    return len(ref) > 2 and ref[1:3] == "\\"


def _provenance_errors(artifact: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    provenance = artifact.get("provenance")
    if not isinstance(provenance, dict):
        return ["provenance_missing_or_invalid"]
    for field in PHASE7_PROVENANCE_REQUIRED_FIELDS:
        if field not in provenance:
            errors.append(f"provenance_field_missing:{field}")
    refs = provenance.get("source_refs")
    if not isinstance(refs, list) or not refs:
        errors.append("provenance_source_refs_missing")
        refs = []
    for ref in refs:
        if not isinstance(ref, str) or not ref.strip():
            errors.append("provenance_source_ref_invalid")
            continue
        lowered = ref.lower()
        if _has_local_path(ref):
            errors.append("provenance_local_path_leak")
        if "api_key" in lowered or "secret" in lowered or "token" in lowered:
            errors.append("provenance_secret_ref_leak")
        if "broker_order_id" in lowered or "external_order_id" in lowered or "fill_id" in lowered:
            errors.append("provenance_broker_identifier_leak")
    if provenance.get("event_log_required") is not True:
        errors.append("provenance_event_log_not_required")
    for field in (
        "raw_secret_exposed",
        "raw_payload_exposed",
        "local_path_exposed",
        "broker_identifier_exposed",
    ):
        if provenance.get(field) is not False:
            errors.append(f"provenance_exposure_enabled:{field}")
    for field in (
        "decision_chain_refs",
        "execution_evidence_refs",
        "market_context_refs",
        "governance_refs",
        "proof_lifecycle_refs",
    ):
        if not isinstance(provenance.get(field), list):
            errors.append(f"provenance_ref_bucket_invalid:{field}")
    return errors


def _event_contract_errors(artifact: dict[str, Any], contract: Phase7ArtifactContract) -> list[str]:
    errors: list[str] = []
    event_contract = artifact.get("event_contract")
    if not isinstance(event_contract, dict):
        return ["event_contract_missing_or_invalid"]
    if event_contract.get("event_category") != contract.event_category:
        errors.append("event_contract_category_mismatch")
    expected_type = PHASE7_EVENT_TYPES.get(contract.event_category)
    if event_contract.get("event_type") != expected_type:
        errors.append("event_contract_type_mismatch")
    if event_contract.get("event_log_required") is not True:
        errors.append("event_contract_log_not_required")
    if event_contract.get("append_only") is not True:
        errors.append("event_contract_not_append_only")
    if event_contract.get("supersession_required_for_change") is not True:
        errors.append("event_contract_supersession_not_required")
    for field in ("raw_secret_exposed", "raw_payload_exposed", "broker_identifier_exposed"):
        if event_contract.get(field) is not False:
            errors.append(f"event_contract_exposure_enabled:{field}")
    return errors


def _boundary_errors(artifact: dict[str, Any]) -> list[str]:
    boundary = str(artifact.get("boundary") or "")
    lowered = boundary.lower()
    if len(boundary.strip()) < 40:
        return ["boundary_weak_or_missing"]
    if "cannot" not in lowered:
        return ["boundary_weak_or_missing"]
    if not any(
        term in lowered
        for term in (
            "write",
            "mutate",
            "enable",
            "approve",
            "create",
            "submit",
            "grant",
            "infer",
            "force",
        )
    ):
        return ["boundary_weak_or_missing"]
    return []


def _specific_errors(artifact: dict[str, Any], *, expected_stage: str) -> list[str]:
    artifact_type = str(artifact.get("artifact_type") or "")
    errors: list[str] = []
    if expected_stage != "Q7-1":
        return errors
    if artifact_type == "proof_authority_ledger":
        if artifact.get("explicit_authority_grant_count") != 0:
            errors.append("proof_authority_grant_count_nonzero")
    if artifact_type == "proof_calendar_day":
        if artifact.get("harness_start_allowed") is not False:
            errors.append("calendar_harness_start_allowed_in_q7_1")
    if artifact_type == "proof_week":
        if artifact.get("weekly_target") != PHASE7_WEEKLY_PROOF_TRADE_TARGET:
            errors.append("proof_week_target_not_three")
        if artifact.get("forced_trade_allowed") is not False:
            errors.append("forced_trade_allowed_in_q7_1")
    if artifact_type == "qualified_setup":
        if artifact.get("source_quorum_required") is not True:
            errors.append("qualified_setup_source_quorum_not_required")
        if artifact.get("qualified_setup_creation_allowed") is not False:
            errors.append("qualified_setup_creation_allowed_in_q7_1")
    if artifact_type == "proof_candidate":
        if artifact.get("phase5_reuse_allowed") is not False:
            errors.append("phase5_reuse_allowed_in_q7_1")
        if artifact.get("proof_candidate_creation_allowed") is not False:
            errors.append("proof_candidate_creation_allowed_in_q7_1")
    if artifact_type == "auto_approval_decision":
        if artifact.get("manual_trade_level_approval_allowed") is not False:
            errors.append("manual_trade_level_approval_allowed_in_q7_1")
        if artifact.get("auto_approval_allowed") is not False:
            errors.append("auto_approval_allowed_in_q7_1")
    if artifact_type == "staged_proof_order":
        if artifact.get("idempotency_required") is not True:
            errors.append("staged_proof_order_idempotency_not_required")
        if artifact.get("proof_order_staging_allowed") is not False:
            errors.append("proof_order_staging_allowed_in_q7_1")
    if artifact_type == "proof_broker_receipt":
        if artifact.get("broker_post_allowed") is not False:
            errors.append("broker_post_allowed_in_q7_1")
        if artifact.get("live_endpoint_allowed") is not False:
            errors.append("live_endpoint_allowed_in_q7_1")
    if artifact_type == "proof_lifecycle_event":
        if artifact.get("proof_lifecycle_write_allowed") is not False:
            errors.append("proof_lifecycle_write_allowed_in_q7_1")
        if artifact.get("reconciliation_required") is not True:
            errors.append("proof_lifecycle_reconciliation_not_required")
    if artifact_type == "proof_postmortem_packet":
        if artifact.get("postmortem_write_allowed") is not False:
            errors.append("postmortem_write_allowed_in_q7_1")
        if artifact.get("all_closed_trades_require_postmortem") is not True:
            errors.append("all_closed_trades_require_postmortem_missing")
    if artifact_type == "performance_evaluation":
        if artifact.get("performance_evaluation_write_allowed") is not False:
            errors.append("performance_evaluation_write_allowed_in_q7_1")
    if artifact_type == "drawdown_risk_sentinel":
        if float(artifact.get("max_drawdown_fraction", 0.0) or 0.0) != (
            PHASE7_MAX_DRAWDOWN_FRACTION
        ):
            errors.append("drawdown_cap_mismatch")
        if artifact.get("risk_halt_allowed") is not False:
            errors.append("risk_halt_allowed_in_q7_1")
    if artifact_type == "override_detection":
        if artifact.get("manual_trade_level_override_allowed") is not False:
            errors.append("manual_override_allowed_in_q7_1")
        if int(artifact.get("override_count", 0) or 0) != 0:
            errors.append("override_count_nonzero_in_q7_1")
    if artifact_type == "source_signal_funnel_evidence":
        if artifact.get("decision_chain_required") is not True:
            errors.append("decision_chain_not_required")
        if artifact.get("private_prior_counts_as_proof") is not False:
            errors.append("private_prior_counts_as_proof")
    if artifact_type == "maturity_snapshot":
        if int(artifact.get("closed_proof_trade_count", 0) or 0) != 0:
            errors.append("closed_proof_trade_count_nonzero_in_q7_1")
        if artifact.get("mature_benchmark") != PHASE7_MATURE_CLOSED_TRADE_BENCHMARK:
            errors.append("mature_benchmark_mismatch")
    if artifact_type == "cockpit_proof_visibility":
        if artifact.get("backend_derived") is not True:
            errors.append("cockpit_proof_visibility_not_backend_derived")
        if int(artifact.get("ui_inferred_readiness_count", 0) or 0) != 0:
            errors.append("cockpit_proof_ui_inferred_readiness")
    if artifact_type == "weekly_review_pack":
        if artifact.get("trade_level_intervention_allowed") is not False:
            errors.append("weekly_review_trade_level_intervention_allowed")
        if artifact.get("weekly_review_packet_created") is not False:
            errors.append("weekly_review_packet_created_in_q7_1")
    if artifact_type == "phase7_certification":
        if artifact.get("phase7_demo_proof_certified") is not False:
            errors.append("phase7_demo_proof_certified_in_q7_1")
        if artifact.get("phase7_mature_benchmark_met") is not False:
            errors.append("phase7_mature_benchmark_met_in_q7_1")
        if artifact.get("live_capital_enabled") is not False:
            errors.append("live_capital_enabled_in_q7_1")
    if artifact_type == "live_promotion_review":
        if artifact.get("live_credentials_enabled") is not False:
            errors.append("live_credentials_enabled_in_q7_1")
        if artifact.get("cooling_off_required") is not True:
            errors.append("cooling_off_not_required")
    return errors


def validate_phase7_event_contracts(contracts: dict[str, dict[str, Any]]) -> list[str]:
    errors: list[str] = []
    for category in PHASE7_REQUIRED_EVENT_CATEGORIES:
        contract = contracts.get(category)
        if not isinstance(contract, dict):
            errors.append(f"event_contract_missing:{category}")
            continue
        if contract.get("event_type") != PHASE7_EVENT_TYPES[category]:
            errors.append(f"event_contract_type_mismatch:{category}")
        if contract.get("event_log_required") is not True:
            errors.append(f"event_contract_log_not_required:{category}")
        if contract.get("append_only") is not True:
            errors.append(f"event_contract_not_append_only:{category}")
        if contract.get("supersession_required_for_change") is not True:
            errors.append(f"event_contract_supersession_not_required:{category}")
    return errors


def validate_phase7_artifact(
    artifact: dict[str, Any],
    *,
    expected_stage: str = "Q7-1",
) -> list[str]:
    errors: list[str] = []
    artifact_type = str(artifact.get("artifact_type"))
    contract = phase7_contract_by_type().get(artifact_type)
    if contract is None:
        return [f"unknown_artifact_type:{artifact.get('artifact_type')}"]
    for field in contract.required_fields:
        if field not in artifact:
            errors.append(f"missing_field:{artifact_type}:{field}")
    if artifact.get("schema_version") != PHASE7_ARTIFACT_SCHEMA_VERSION:
        errors.append(f"schema_version_mismatch:{artifact_type}")
    if artifact.get("phase") != "Q7":
        errors.append(f"phase_mismatch:{artifact_type}")
    if artifact.get("stage") != expected_stage:
        errors.append(f"stage_mismatch:{artifact_type}")
    if artifact.get("status") not in contract.allowed_statuses:
        errors.append(f"status_invalid:{artifact_type}:{artifact.get('status')}")
    if artifact.get("public_safe") is not True:
        errors.append(f"public_safe_not_true:{artifact_type}")
    if artifact.get("event_log_required") is not True:
        errors.append(f"event_log_required_not_true:{artifact_type}")
    if not isinstance(artifact.get("event_log_written"), bool):
        errors.append(f"event_log_written_not_bool:{artifact_type}")
    errors.extend(_boundary_errors(artifact))
    errors.extend(_authority_errors(artifact))
    errors.extend(_unsafe_counter_errors(artifact))
    errors.extend(_proof_contract_errors(artifact))
    errors.extend(_source_posture_errors(artifact))
    errors.extend(_provenance_errors(artifact))
    errors.extend(_event_contract_errors(artifact, contract))
    errors.extend(_specific_errors(artifact, expected_stage=expected_stage))
    return sorted(set(errors))


def phase7_artifact_bundle_summary(artifacts: list[dict[str, Any]]) -> dict[str, Any]:
    errors: list[str] = []
    seen = Counter(str(artifact.get("artifact_type")) for artifact in artifacts)
    missing_types = [
        artifact_type
        for artifact_type in PHASE7_ARTIFACT_TYPES
        if seen.get(artifact_type, 0) == 0
    ]
    duplicate_types = [
        artifact_type
        for artifact_type, count in seen.items()
        if artifact_type in PHASE7_ARTIFACT_TYPES and count > 1
    ]
    for artifact in artifacts:
        errors.extend(validate_phase7_artifact(artifact))
    for artifact_type in missing_types:
        errors.append(f"missing_artifact_type:{artifact_type}")
    for artifact_type in duplicate_types:
        errors.append(f"duplicate_artifact_type:{artifact_type}")
    event_contract_errors = validate_phase7_event_contracts(phase7_event_contracts())
    errors.extend(event_contract_errors)
    authority_enabled_count = sum(
        1
        for artifact in artifacts
        for field in PHASE7_AUTHORITY_FLAGS
        if artifact.get(field) is not False
    )
    unsafe_counter_total = sum(
        int(artifact.get(field, 0) or 0)
        for artifact in artifacts
        for field in PHASE7_UNSAFE_COUNT_FIELDS
    )
    return {
        "status": "ok" if not errors else "error",
        "schema_version": PHASE7_ARTIFACT_SCHEMA_VERSION,
        "artifact_count": len(artifacts),
        "artifact_type_count": len(PHASE7_ARTIFACT_TYPES),
        "status_enum_count": len(PHASE7_STATUS_ENUMS),
        "authority_field_count": len(PHASE7_AUTHORITY_FLAGS),
        "unsafe_counter_field_count": len(PHASE7_UNSAFE_COUNT_FIELDS),
        "event_contract_count": len(PHASE7_REQUIRED_EVENT_CATEGORIES),
        "missing_artifact_types": missing_types,
        "duplicate_artifact_types": duplicate_types,
        "error_count": len(errors),
        "errors": errors,
        "authority_enabled_count": authority_enabled_count,
        "unsafe_counter_total": unsafe_counter_total,
        "proof_contract_status": "validated" if not errors else "error",
        "source_posture_status": "validated" if not errors else "error",
        "provenance_status": "validated" if not errors else "error",
        "event_contract_status": "validated" if not event_contract_errors else "error",
        "boundary": (
            "Q7-1 validates Demo Proof artifact shapes only. Later Q7 stages "
            "must explicitly grant and verify any non-default proof authority."
        ),
    }
