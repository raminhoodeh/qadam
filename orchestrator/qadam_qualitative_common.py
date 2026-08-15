"""Shared contracts for Qadam's qualitative and all-lane evidence plane."""

from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
from typing import Any, Iterable

from orchestrator.config import Settings
from orchestrator.qadam_operator_ready_common import authority_flags


SCHEMA_VERSION = "qadam_qualitative_evidence.v1"
LANE_SCHEMA_VERSION = "qadam_lane_capability.v1"
CONTRIBUTION_SCHEMA_VERSION = "qadam_lane_contribution.v1"

LANE_REGISTRY_PATH = "config/qadam_lane_capability_registry.json"
ORIGIN_REGISTRY_PATH = "config/qadam_external_origin_registry.json"
TRUST_POLICY_PATH = "config/qadam_external_evidence_trust_policy.json"
AGENT_REACH_LOCK_PATH = "config/qadam_agent_reach_lock.json"
COMMAND_POLICY_PATH = "config/qadam_agent_reach_command_policy.json"

LANE_CONTRIBUTIONS_ARTIFACT = "qadam_lane_contributions.jsonl"
LANE_AUTHORITY_ARTIFACT = "qadam_lane_authority_inventory.json"
LANE_FUNNEL_ARTIFACT = "qadam_lane_conversion_funnel.json"
LANE_BLOCKERS_ARTIFACT = "qadam_lane_blocker_ownership.json"
LANE_FAST_PATH_ARTIFACT = "qadam_lane_fast_path_status.json"
LANE_REACHABILITY_ARTIFACT = "qadam_lane_reachability_canary.json"
ALL_LANE_CERTIFICATION_ARTIFACT = "qadam_all_lane_conversion_certification.json"

EXTERNAL_MANIFEST_ARTIFACT = "qadam_external_document_manifest.jsonl"
EXTERNAL_DOCUMENTS_ARTIFACT = "qadam_external_documents.jsonl"
EXTERNAL_ACQUISITION_ARTIFACT = "qadam_external_acquisition_status.json"
EXTERNAL_CHANNEL_HEALTH_ARTIFACT = "qadam_external_channel_health.json"
EXTERNAL_SECURITY_ARTIFACT = "qadam_external_evidence_security_audit.json"
EXTERNAL_PROVENANCE_ARTIFACT = "qadam_external_evidence_provenance_audit.json"
QUALITATIVE_CLAIMS_ARTIFACT = "qadam_qualitative_claims.jsonl"
QUALITATIVE_REJECTIONS_ARTIFACT = "qadam_qualitative_claim_rejections.jsonl"
QUALITATIVE_CHALLENGES_ARTIFACT = "qadam_qualitative_claim_challenges.jsonl"
QUALITATIVE_CLAIM_SUMMARY_ARTIFACT = "qadam_qualitative_claim_summary.json"
QUALITATIVE_GRAPH_SUMMARY_ARTIFACT = "qadam_qualitative_graph_summary.json"
QUALITATIVE_ENTITY_MAPPINGS_ARTIFACT = "qadam_qualitative_entity_mappings.jsonl"
QUALITATIVE_INSTRUMENT_MAPPINGS_ARTIFACT = "qadam_qualitative_instrument_mappings.jsonl"
QUALITATIVE_HISTORY_ARTIFACT = "qadam_qualitative_history_coverage.json"
QUALITATIVE_FORWARD_WINDOWS_ARTIFACT = "qadam_qualitative_forward_window_status.json"
QUALITATIVE_LABELS_ARTIFACT = "qadam_qualitative_label_manifest.jsonl"
QUALITATIVE_PATTERNS_ARTIFACT = "qadam_qualitative_pattern_candidates.jsonl"
QUALITATIVE_PATTERN_REJECTIONS_ARTIFACT = "qadam_qualitative_pattern_rejections.jsonl"
QUALITATIVE_BACKTEST_ARTIFACT = "qadam_qualitative_backtest_summary.json"
QUALITATIVE_QUANTUM_ARTIFACT = "qadam_qualitative_quantum_review.json"
QUALITATIVE_PATTERN_BRIDGE_ARTIFACT = "qadam_qualitative_pattern_score_bridge.json"
QUALITATIVE_DIRECTIONS_ARTIFACT = "qadam_qualitative_direction_resolutions.jsonl"
QUALITATIVE_STRATEGY_IMPACTS_ARTIFACT = "qadam_qualitative_strategy_impacts.jsonl"
QUALITATIVE_AKBER_INPUTS_ARTIFACT = "qadam_qualitative_akber_inputs.jsonl"
QUALITATIVE_AKBER_EXPLANATIONS_ARTIFACT = "qadam_qualitative_akber_explanations.jsonl"
QUALITATIVE_PAPER_ELIGIBILITY_ARTIFACT = "qadam_qualitative_paper_eligibility.json"
QUALITATIVE_DASHBOARD_ARTIFACT = "qadam_qualitative_dashboard_summary.json"
QUALITATIVE_COMMUNICATIONS_ARTIFACT = "qadam_qualitative_communications_summary.json"
QUALITATIVE_NOTIFICATION_DEDUPE_ARTIFACT = "qadam_qualitative_notification_dedupe.jsonl"

PREDICTION_CONTRACTS_ARTIFACT = "qadam_prediction_contract_registry.jsonl"
PREDICTION_CONTRACTS_PUBLIC_ARTIFACT = "qadam_prediction_contracts.jsonl"
PREDICTION_GRAPH_ARTIFACT = "qadam_prediction_contract_graph.json"
PREDICTION_BELIEFS_ARTIFACT = "qadam_prediction_belief_states.jsonl"
PREDICTION_RESEARCH_ARTIFACT = "qadam_prediction_market_research.json"
PREDICTION_PAPER_REGISTRY_ARTIFACT = "qadam_prediction_market_paper_registry.json"
PREDICTION_QUALITY_ARTIFACT = "qadam_prediction_market_quality.json"
PREDICTION_CONSISTENCY_ARTIFACT = "qadam_prediction_market_consistency_records.jsonl"
PREDICTION_CROSS_ASSET_ARTIFACT = "qadam_prediction_market_cross_asset_signals.jsonl"
PREDICTION_INTELLIGENCE_ARTIFACT = "qadam_prediction_market_intelligence_summary.json"

AGENT_REACH_BASELINE_ARTIFACT = "qadam_agent_reach_baseline.json"
SOURCE_COUNT_CONTRACT_ARTIFACT = "qadam_source_count_contract.json"
QUALITATIVE_GAP_MAP_ARTIFACT = "qadam_qualitative_evidence_gap_map.json"
AGENT_REACH_SUPPLY_CHAIN_ARTIFACT = "qadam_agent_reach_supply_chain_audit.json"
AGENT_REACH_SANDBOX_ARTIFACT = "qadam_agent_reach_sandbox_status.json"
EXTERNAL_TERMS_ARTIFACT = "qadam_external_origin_terms_matrix.json"
EXTERNAL_PROMOTION_ARTIFACT = "qadam_external_origin_promotion_ledger.jsonl"
AGENT_REACH_OPERATOR_ARTIFACT = "qadam_agent_reach_operator_status.json"
AGENT_REACH_REPAIR_ARTIFACT = "qadam_agent_reach_repair_queue.jsonl"
AGENT_REACH_RESOURCE_ARTIFACT = "qadam_agent_reach_resource_state.json"
AGENT_REACH_SOAK_ARTIFACT = "qadam_agent_reach_soak_status.json"
AGENT_REACH_CERTIFICATION_ARTIFACT = "qadam_agent_reach_enrichment_certification.json"
AGENT_REACH_ACTIVATION_ARTIFACT = "qadam_agent_reach_activation_receipt.json"
QUALITATIVE_IMPACT_ARTIFACT = "qadam_qualitative_evidence_impact_report.json"


def repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def runtime_dir(settings: Settings | None = None) -> Path:
    value = Path((settings or Settings.from_env()).runtime_dir)
    return value if value.is_absolute() else repo_root() / value


def research_root() -> Path:
    return repo_root() / "data" / "research" / "qadam_external_evidence"


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def stable_id(prefix: str, *parts: Any) -> str:
    raw = json.dumps(parts, sort_keys=True, separators=(",", ":"), default=str)
    return f"{prefix}:{hashlib.sha256(raw.encode('utf-8')).hexdigest()[:24]}"


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha256_json(value: Any) -> str:
    raw = json.dumps(value, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def read_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return value if isinstance(value, dict) else {}


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.is_file():
        return []
    rows: list[dict[str, Any]] = []
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError:
        return []
    for line in lines:
        if not line.strip():
            continue
        try:
            value = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(value, dict):
            rows.append(value)
    return rows


def public_authority(**overrides: Any) -> dict[str, Any]:
    value = authority_flags()
    value.update(
        {
            "read_only": True,
            "paper_only": True,
            "proposal_first": True,
            "trade_candidate_creation_allowed": False,
            "trade_candidate_created": False,
            "risk_approval_allowed": False,
            "risk_approval_created": False,
            "execution_approval_allowed": False,
            "execution_approval_created": False,
            "paper_order_allowed": False,
            "paper_order_created": False,
            "broker_write_allowed": False,
            "broker_write_count": 0,
            "live_capital_enabled": False,
            "proof_credit_allowed": False,
            "paper_proof_ledger_credit_allowed": False,
            "paper_growth_trial_calendar_advance_allowed": False,
            "strategy_mutation_allowed": False,
            "policy_mutation_allowed": False,
        }
    )
    value.update(overrides)
    return value


def unique(values: Iterable[str]) -> list[str]:
    return sorted({str(value) for value in values if str(value)})


def parse_iso(value: Any) -> datetime | None:
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        return None
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)


def age_seconds(value: Any) -> float | None:
    parsed = parse_iso(value)
    if parsed is None:
        return None
    return max(0.0, (datetime.now(timezone.utc) - parsed.astimezone(timezone.utc)).total_seconds())
