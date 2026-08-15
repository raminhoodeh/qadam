"""Evidence-native contracts for Qadam next-generation flow Phase 2.

This module normalizes Qadam's current runtime fragments into typed evidence
contracts. It is a read-only boundary layer: contracts can support research,
dashboard visibility, Akber calibration, shadow review, and router dry mapping,
but they cannot create trade candidates, risk approvals, execution approvals,
orders, broker writes, proof credit, or live-capital authority.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
from typing import Any, Iterable

from orchestrator.config import Settings
from orchestrator.qadam_qualitative_common import (
    CONTRIBUTION_SCHEMA_VERSION,
    LANE_REGISTRY_PATH,
    public_authority,
    read_json as read_policy_json,
    repo_root,
    stable_id,
)

SCHEMA_VERSION = "qadam_evidence_contracts.v1"
PHASE_ID = "qadam_next_generation_phase_2_evidence_native_data_contracts"

PRIMARY_ARTIFACT = "qadam_evidence_contracts.json"
SUMMARY_ARTIFACT = "qadam_evidence_contracts_summary.json"
DASHBOARD_SUMMARY_ARTIFACT = "qadam_evidence_contracts_dashboard_summary.json"
EVENTS_ARTIFACT = "qadam_evidence_contracts_events.jsonl"

SOURCE_EVIDENCE_ARTIFACT = "qadam_source_evidence_contracts.jsonl"
PRICE_EVIDENCE_ARTIFACT = "qadam_price_evidence_contracts.jsonl"
SOURCE_PRICE_RELATIONSHIP_EVIDENCE_ARTIFACT = "qadam_source_price_relationship_evidence_contracts.jsonl"
HYPOTHESIS_EVIDENCE_ARTIFACT = "qadam_hypothesis_evidence_contracts.jsonl"
STRATEGY_EVIDENCE_ARTIFACT = "qadam_strategy_evidence_contracts.jsonl"
AKBER_EVIDENCE_ARTIFACT = "qadam_akber_evidence_contracts.jsonl"
SHADOW_EVIDENCE_ARTIFACT = "qadam_shadow_evidence_contracts.jsonl"
ROUTER_EVIDENCE_ARTIFACT = "qadam_router_evidence_contracts.jsonl"

SOURCE_UNIVERSE_ARTIFACT = "qsase_source_universe.json"
TRADING_UNIVERSE_ARTIFACT = "qsase_trading_universe.json"
SOURCE_PRICE_EDGES_ARTIFACT = "qsase_source_price_edges.jsonl"
HISTORICAL_MEMORY_ARTIFACT = "qsase_historical_source_price_memory.jsonl"
BASELINE_RESULTS_ARTIFACT = "qsase_baseline_backtest_results.jsonl"
BASELINE_REJECTIONS_ARTIFACT = "qsase_baseline_backtest_rejections.jsonl"
STRATEGY_HYPOTHESES_ARTIFACT = "qsase_strategy_hypotheses.jsonl"
STRATEGY_EVIDENCE_MAP_ARTIFACT = "qsase_baseline_strategy_evidence_map.json"
AKBER_RESULTS_ARTIFACT = "qsase_akber_filter_results.jsonl"
AKBER_CALIBRATION_ARTIFACT = "qsase_akber_backtest_calibration.json"
SHADOW_RESULTS_ARTIFACT = "qsase_shadow_strategy_results.jsonl"
SHADOW_ROUTER_MAP_ARTIFACT = "qsase_baseline_shadow_router_map.json"
ROUTER_DECISIONS_ARTIFACT = "qsase_strategy_router_decisions.jsonl"

CONTRACT_ARTIFACTS = {
    "source_evidence": SOURCE_EVIDENCE_ARTIFACT,
    "price_evidence": PRICE_EVIDENCE_ARTIFACT,
    "source_price_relationship_evidence": SOURCE_PRICE_RELATIONSHIP_EVIDENCE_ARTIFACT,
    "hypothesis_evidence": HYPOTHESIS_EVIDENCE_ARTIFACT,
    "strategy_evidence": STRATEGY_EVIDENCE_ARTIFACT,
    "akber_evidence": AKBER_EVIDENCE_ARTIFACT,
    "shadow_evidence": SHADOW_EVIDENCE_ARTIFACT,
    "router_evidence": ROUTER_EVIDENCE_ARTIFACT,
}

AUTHORITY_FLAGS = {
    "read_only": True,
    "paper_only": True,
    "proposal_first": True,
    "evidence_contract_only": True,
    "source_quorum_credit_granted": False,
    "trade_candidate_creation_allowed": False,
    "trade_candidate_created": False,
    "qualified_setup_created": False,
    "risk_handoff_allowed": False,
    "risk_approval_allowed": False,
    "risk_approval_created": False,
    "execution_allowed": False,
    "execution_approval_allowed": False,
    "execution_approval_created": False,
    "paper_order_allowed": False,
    "paper_order_created": False,
    "broker_write_allowed": False,
    "broker_write_count": 0,
    "live_broker_endpoint_allowed": False,
    "live_capital_enabled": False,
    "proof_credit_allowed": False,
    "paper_proof_ledger_credit_allowed": False,
    "paper_growth_trial_calendar_advance_allowed": False,
    "simulated_elapsed_time_allowed": False,
    "strategy_mutation_allowed": False,
    "filter_threshold_update_allowed": False,
    "telegram_command_path_enabled": False,
    "telegram_trade_command_enabled": False,
}

FORBIDDEN_TRUE_FIELDS = tuple(
    key for key, value in AUTHORITY_FLAGS.items() if value is False
)
FORBIDDEN_NONZERO_FIELDS = tuple(
    key for key, value in AUTHORITY_FLAGS.items() if isinstance(value, int) and value == 0
)

REQUIRED_CONTRACT_TYPES = tuple(CONTRACT_ARTIFACTS)

MISSING_TYPE_DEFAULT_SEVERITY = {
    "missing_source_history": "medium",
    "missing_source_freshness": "medium",
    "missing_source_quorum": "high",
    "missing_price_history": "high",
    "missing_current_price": "medium",
    "missing_forward_window": "high",
    "missing_outcome_window": "high",
    "missing_volatility_context": "medium",
    "missing_volume_or_flow": "high",
    "missing_technical_confirmation": "high",
    "missing_pricing_gap_evidence": "medium",
    "missing_fresh_catalyst": "high",
    "missing_risk_reward": "high",
    "missing_invalidation": "high",
    "missing_shadow_replay": "medium",
    "missing_router_decision": "high",
    "missing_hypothesis_lineage": "medium",
    "missing_paperops_guarded_route": "high",
    "provider_history_required": "high",
}


@dataclass(frozen=True)
class ContractBundle:
    primary: dict[str, Any]
    summary: dict[str, Any]
    dashboard_summary: dict[str, Any]
    records_by_type: dict[str, list[dict[str, Any]]]


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def _runtime_dir(settings: Settings | None = None) -> Path:
    active_settings = settings or Settings.from_env()
    path = Path(active_settings.runtime_dir)
    if not path.is_absolute():
        path = _repo_root() / path
    return path


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _iso(dt: datetime | None = None) -> str:
    return (dt or _now()).astimezone(timezone.utc).isoformat()


def _json_dump(payload: dict[str, Any]) -> str:
    return json.dumps(payload, indent=2, sort_keys=True) + "\n"


def _jsonl_line(payload: dict[str, Any]) -> str:
    return json.dumps(payload, sort_keys=True) + "\n"


def _read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return payload if isinstance(payload, dict) else {}


def _read_jsonl(path: Path, limit: int | None = None) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError:
        return []
    if limit is not None:
        lines = lines[-limit:]
    records: list[dict[str, Any]] = []
    for line in lines:
        if not line.strip():
            continue
        try:
            payload = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(payload, dict):
            records.append(payload)
    return records


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(_json_dump(payload), encoding="utf-8")


def _write_jsonl(path: Path, records: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(_jsonl_line(record) for record in records), encoding="utf-8")


def _append_jsonl(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(_jsonl_line(payload))


def _safe_list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def _safe_dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _int(value: Any, default: int = 0) -> int:
    if isinstance(value, bool):
        return default
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(value)
    if isinstance(value, str):
        try:
            return int(float(value))
        except ValueError:
            return default
    return default


def _float(value: Any, default: float | None = None) -> float | None:
    if isinstance(value, bool):
        return default
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        try:
            return float(value)
        except ValueError:
            return default
    return default


def _hash_id(prefix: str, parts: Iterable[Any]) -> str:
    raw = "|".join(str(part) for part in parts)
    return f"{prefix}:{hashlib.sha256(raw.encode('utf-8')).hexdigest()[:20]}"


def _artifact_ref(filename: str, fragment: str | None = None) -> str:
    base = f"data/runtime/{filename}"
    return f"{base}#{fragment}" if fragment else base


def _authority() -> dict[str, Any]:
    return dict(AUTHORITY_FLAGS)


def _missing(
    missing_type: str,
    *,
    field: str,
    reason: str,
    required_for: str,
    severity: str | None = None,
    source_artifact_ref: str | None = None,
) -> dict[str, Any]:
    return {
        "missing_evidence_type": missing_type,
        "severity": severity or MISSING_TYPE_DEFAULT_SEVERITY.get(missing_type, "medium"),
        "field": field,
        "reason": reason,
        "required_for": required_for,
        "source_artifact_ref": source_artifact_ref,
    }


def _score_from_missing(missing: list[dict[str, Any]], base: float = 1.0) -> float:
    penalties = {"low": 0.05, "medium": 0.12, "high": 0.2}
    score = base
    for item in missing:
        score -= penalties.get(str(item.get("severity")), 0.1)
    return round(max(0.0, min(1.0, score)), 6)


def _contract(
    *,
    contract_type: str,
    source_record_id: str,
    source_artifact: str,
    subject: dict[str, Any],
    lineage: dict[str, Any] | None = None,
    metrics: dict[str, Any] | None = None,
    missing_evidence: list[dict[str, Any]] | None = None,
    status: str | None = None,
    generated_at: str | None = None,
) -> dict[str, Any]:
    missing = missing_evidence or []
    resolved_status = status or ("evidence_complete" if not missing else "evidence_missing_typed")
    return {
        "schema_version": SCHEMA_VERSION,
        "phase_id": PHASE_ID,
        "contract_type": contract_type,
        "contract_id": _hash_id(f"qadam-{contract_type}", [source_record_id, source_artifact, subject]),
        "source_record_id": source_record_id,
        "source_artifact_ref": _artifact_ref(source_artifact),
        "generated_at": generated_at or _iso(),
        "status": resolved_status,
        "evidence_state": "complete" if not missing else "missing_typed",
        "missing_evidence_count": len(missing),
        "missing_evidence": missing,
        "completeness_score": _score_from_missing(missing),
        "subject": subject,
        "metrics": metrics or {},
        "lineage": lineage or {},
        "public_safe": True,
        "read_only": True,
        "paper_only": True,
        "authority": _authority(),
    }


def _load_context(settings: Settings | None = None) -> dict[str, Any]:
    runtime = _runtime_dir(settings)
    return {
        "runtime_dir": runtime,
        "source_universe": _read_json(runtime / SOURCE_UNIVERSE_ARTIFACT),
        "trading_universe": _read_json(runtime / TRADING_UNIVERSE_ARTIFACT),
        "source_price_edges": _read_jsonl(runtime / SOURCE_PRICE_EDGES_ARTIFACT, limit=500),
        "historical_memory": _read_jsonl(runtime / HISTORICAL_MEMORY_ARTIFACT, limit=500),
        "baseline_results": _read_jsonl(runtime / BASELINE_RESULTS_ARTIFACT, limit=500),
        "baseline_rejections": _read_jsonl(runtime / BASELINE_REJECTIONS_ARTIFACT, limit=500),
        "strategy_hypotheses": _read_jsonl(runtime / STRATEGY_HYPOTHESES_ARTIFACT, limit=500),
        "strategy_evidence_map": _read_json(runtime / STRATEGY_EVIDENCE_MAP_ARTIFACT),
        "akber_results": _read_jsonl(runtime / AKBER_RESULTS_ARTIFACT, limit=500),
        "akber_calibration": _read_json(runtime / AKBER_CALIBRATION_ARTIFACT),
        "shadow_results": _read_jsonl(runtime / SHADOW_RESULTS_ARTIFACT, limit=500),
        "shadow_router_map": _read_json(runtime / SHADOW_ROUTER_MAP_ARTIFACT),
        "router_decisions": _read_jsonl(runtime / ROUTER_DECISIONS_ARTIFACT, limit=500),
    }


def _build_source_contracts(context: dict[str, Any], generated_at: str) -> list[dict[str, Any]]:
    contracts: list[dict[str, Any]] = []
    for row in _safe_list(context["source_universe"].get("sources")):
        source_key = str(row.get("source_key") or "unknown_source")
        missing: list[dict[str, Any]] = []
        if row.get("freshness_status") not in {"fresh", "recent"}:
            missing.append(
                _missing(
                    "missing_source_freshness",
                    field="freshness_status",
                    reason=f"Source freshness is {row.get('freshness_status') or 'unknown'}.",
                    required_for="source evidence confidence",
                    source_artifact_ref=_artifact_ref(SOURCE_UNIVERSE_ARTIFACT),
                )
            )
        if row.get("source_quorum_contribution", {}).get("can_contribute") is not True:
            missing.append(
                _missing(
                    "missing_source_quorum",
                    field="source_quorum_contribution",
                    reason="Source cannot contribute candidate-level quorum by itself.",
                    required_for="candidate-level source quorum",
                    source_artifact_ref=_artifact_ref(SOURCE_UNIVERSE_ARTIFACT),
                )
            )
        contracts.append(
            _contract(
                contract_type="source_evidence",
                source_record_id=source_key,
                source_artifact=SOURCE_UNIVERSE_ARTIFACT,
                generated_at=generated_at,
                subject={
                    "source_key": source_key,
                    "source_name": row.get("source_name"),
                    "source_family": row.get("source_family"),
                    "state": row.get("state"),
                    "freshness_status": row.get("freshness_status"),
                    "trust_posture": row.get("trust_posture"),
                    "trust_score": row.get("trust_score"),
                    "credential_status": row.get("credential_status"),
                    "supplemental_context_only": row.get("supplemental_context_only") is True,
                },
                metrics={
                    "observed_age_seconds": row.get("observed_age_seconds"),
                    "source_quorum_can_contribute": row.get("source_quorum_contribution", {}).get("can_contribute") is True,
                },
                lineage={
                    "provenance": _safe_list(row.get("provenance")),
                },
                missing_evidence=missing,
            )
        )
    return contracts


def _build_price_contracts(context: dict[str, Any], generated_at: str) -> list[dict[str, Any]]:
    contracts: list[dict[str, Any]] = []
    for row in _safe_list(context["trading_universe"].get("instruments")):
        symbol = str(row.get("symbol") or "unknown_symbol")
        missing: list[dict[str, Any]] = []
        if row.get("price_or_odds_value") is None:
            missing.append(
                _missing(
                    "missing_current_price",
                    field="price_or_odds_value",
                    reason="Current price or odds is not present in the trading universe record.",
                    required_for="live setup confirmation",
                    source_artifact_ref=_artifact_ref(TRADING_UNIVERSE_ARTIFACT),
                )
            )
        if row.get("backtest_ready") is not True:
            missing.append(
                _missing(
                    "missing_price_history",
                    field="backtest_ready",
                    reason=row.get("backtest_gap_reason") or "Historical price windows are not complete.",
                    required_for="source-price backtest",
                    source_artifact_ref=_artifact_ref(TRADING_UNIVERSE_ARTIFACT),
                )
            )
        if row.get("volatility_context") in {None, "missing"}:
            missing.append(
                _missing(
                    "missing_volatility_context",
                    field="volatility_context",
                    reason="Volatility context is missing.",
                    required_for="Akber practical confirmation",
                    source_artifact_ref=_artifact_ref(TRADING_UNIVERSE_ARTIFACT),
                )
            )
        if row.get("volume_context") in {None, "missing"}:
            missing.append(
                _missing(
                    "missing_volume_or_flow",
                    field="volume_context",
                    reason="Volume or flow context is missing.",
                    required_for="Akber practical confirmation",
                    source_artifact_ref=_artifact_ref(TRADING_UNIVERSE_ARTIFACT),
                )
            )
        contracts.append(
            _contract(
                contract_type="price_evidence",
                source_record_id=symbol,
                source_artifact=TRADING_UNIVERSE_ARTIFACT,
                generated_at=generated_at,
                subject={
                    "symbol": symbol,
                    "instrument_id": row.get("instrument_id"),
                    "display_name": row.get("display_name"),
                    "market_family": row.get("market_family"),
                    "paperability_state": row.get("paperability_state"),
                    "paper_route_available": row.get("paper_route_available") is True,
                    "price_data_state": row.get("price_data_state"),
                    "qualified_setup_state": row.get("qualified_setup_state"),
                },
                metrics={
                    "price_or_odds_value": row.get("price_or_odds_value"),
                    "previous_price_or_odds_value": row.get("previous_price_or_odds_value"),
                    "rolling_volatility_20d": row.get("rolling_volatility_20d"),
                },
                lineage={
                    "provenance": _safe_list(row.get("provenance")),
                },
                missing_evidence=missing,
            )
        )
    return contracts


def _relationship_missing_from_result(row: dict[str, Any], source_artifact: str) -> list[dict[str, Any]]:
    missing: list[dict[str, Any]] = []
    if _int(row.get("sample_count")) < 3:
        missing.append(
            _missing(
                "missing_forward_window",
                field="sample_count",
                reason="Sample count is below the minimum for baseline relationship evidence.",
                required_for="source-price relationship confidence",
                source_artifact_ref=_artifact_ref(source_artifact),
            )
        )
    if row.get("average_forward_return") is None:
        missing.append(
            _missing(
                "missing_outcome_window",
                field="average_forward_return",
                reason="Forward return is missing.",
                required_for="backtest relationship metrics",
                source_artifact_ref=_artifact_ref(source_artifact),
            )
        )
    return missing


def _build_relationship_contracts(context: dict[str, Any], generated_at: str) -> list[dict[str, Any]]:
    contracts: list[dict[str, Any]] = []
    for row in context["baseline_results"]:
        record_id = str(row.get("baseline_result_id") or "unknown_baseline_result")
        contracts.append(
            _contract(
                contract_type="source_price_relationship_evidence",
                source_record_id=record_id,
                source_artifact=BASELINE_RESULTS_ARTIFACT,
                generated_at=generated_at,
                status="relationship_evidence_observed",
                subject={
                    "relationship_type": row.get("relationship_type"),
                    "source_or_family": row.get("source_or_family"),
                    "market_or_symbol": row.get("market_or_symbol"),
                    "time_window": row.get("time_window"),
                    "relationship_status": row.get("status"),
                },
                metrics={
                    "sample_count": row.get("sample_count"),
                    "hit_rate": row.get("hit_rate"),
                    "expectancy": row.get("expectancy"),
                    "average_forward_return": row.get("average_forward_return"),
                    "drawdown_proxy": row.get("drawdown_proxy"),
                    "false_positive_rate": row.get("false_positive_rate"),
                    "overfit_warning": row.get("overfit_warning"),
                },
                lineage={
                    "source_record_ids": _safe_list(row.get("source_record_ids")),
                },
                missing_evidence=_relationship_missing_from_result(row, BASELINE_RESULTS_ARTIFACT),
            )
        )
    for row in context["baseline_rejections"]:
        record_id = str(row.get("baseline_result_id") or row.get("rejected_relationship_id") or "unknown_rejected_relationship")
        missing = _relationship_missing_from_result(row, BASELINE_REJECTIONS_ARTIFACT)
        if not missing:
            missing.append(
                _missing(
                    "provider_history_required",
                    field="rejection_reason",
                    reason=row.get("rejection_reason") or "Relationship rejected by baseline process.",
                    required_for="relationship promotion",
                    source_artifact_ref=_artifact_ref(BASELINE_REJECTIONS_ARTIFACT),
                )
            )
        contracts.append(
            _contract(
                contract_type="source_price_relationship_evidence",
                source_record_id=record_id,
                source_artifact=BASELINE_REJECTIONS_ARTIFACT,
                generated_at=generated_at,
                status="relationship_evidence_rejected_missing_typed",
                subject={
                    "relationship_type": row.get("relationship_type"),
                    "source_or_family": row.get("source_or_family"),
                    "market_or_symbol": row.get("market_or_symbol"),
                    "time_window": row.get("time_window"),
                    "relationship_status": row.get("status"),
                    "rejection_reason": row.get("rejection_reason"),
                },
                metrics={
                    "sample_count": row.get("sample_count"),
                    "hit_rate": row.get("hit_rate"),
                    "expectancy": row.get("expectancy"),
                    "false_positive_rate": row.get("false_positive_rate"),
                },
                lineage={
                    "source_record_ids": _safe_list(row.get("source_record_ids")),
                },
                missing_evidence=missing,
            )
        )
    return contracts


def _build_hypothesis_contracts(context: dict[str, Any], generated_at: str) -> list[dict[str, Any]]:
    contracts: list[dict[str, Any]] = []
    for row in context["strategy_hypotheses"]:
        hypothesis_id = str(row.get("strategy_hypothesis_id") or "unknown_hypothesis")
        missing: list[dict[str, Any]] = []
        evidence = _safe_dict(row.get("evidence"))
        lineage = _safe_dict(row.get("lineage"))
        if evidence.get("source_price_lineage_present") is not True:
            missing.append(
                _missing(
                    "missing_hypothesis_lineage",
                    field="evidence.source_price_lineage_present",
                    reason="Hypothesis does not carry confirmed source-price lineage.",
                    required_for="hypothesis promotion",
                    source_artifact_ref=_artifact_ref(STRATEGY_HYPOTHESES_ARTIFACT),
                )
            )
        if row.get("akber_filter_passed") is not True:
            missing.append(
                _missing(
                    "missing_technical_confirmation",
                    field="akber_filter_passed",
                    reason="Akber has not passed this hypothesis.",
                    required_for="router/paper review",
                    source_artifact_ref=_artifact_ref(STRATEGY_HYPOTHESES_ARTIFACT),
                )
            )
        if row.get("shadow_replay_executed") is not True:
            missing.append(
                _missing(
                    "missing_shadow_replay",
                    field="shadow_replay_executed",
                    reason="Shadow replay has not executed for this hypothesis.",
                    required_for="router confidence",
                    source_artifact_ref=_artifact_ref(STRATEGY_HYPOTHESES_ARTIFACT),
                )
            )
        contracts.append(
            _contract(
                contract_type="hypothesis_evidence",
                source_record_id=hypothesis_id,
                source_artifact=STRATEGY_HYPOTHESES_ARTIFACT,
                generated_at=generated_at,
                subject={
                    "strategy_hypothesis_id": hypothesis_id,
                    "name": row.get("name"),
                    "status": row.get("status"),
                    "hypothesis_type": row.get("hypothesis_type"),
                    "primary_instrument": row.get("market_expression", {}).get("primary_instrument"),
                    "paperable_execution_expression": row.get("market_expression", {}).get("paperable_execution_expression"),
                },
                metrics={
                    "historical_sample_size": evidence.get("historical_sample_size"),
                    "linear_score": evidence.get("linear_score"),
                    "nonlinear_score": evidence.get("nonlinear_score"),
                    "quantum_ambiguity_score": evidence.get("quantum_ambiguity_score"),
                    "walk_forward_survival": evidence.get("walk_forward_survival"),
                },
                lineage={
                    "research_goal_id": row.get("research_goal_lineage", {}).get("research_goal_id"),
                    "source_price_evidence_artifacts": _safe_list(lineage.get("source_price_evidence_artifacts")),
                    "linear_pattern_ids": _safe_list(lineage.get("linear_pattern_ids")),
                    "nonlinear_pattern_ids": _safe_list(lineage.get("nonlinear_pattern_ids")),
                    "quantum_review_ids": _safe_list(lineage.get("quantum_review_ids")),
                },
                missing_evidence=missing,
            )
        )
    return contracts


def _build_strategy_contracts(context: dict[str, Any], generated_at: str) -> list[dict[str, Any]]:
    contracts: list[dict[str, Any]] = []
    for row in _safe_list(context["strategy_evidence_map"].get("records")):
        strategy_id = str(row.get("strategy_family_id") or "unknown_strategy")
        missing: list[dict[str, Any]] = []
        if _int(row.get("supporting_relationship_count")) < 1:
            missing.append(
                _missing(
                    "provider_history_required",
                    field="supporting_relationship_count",
                    reason="No baseline source-price relationship currently supports this strategy family.",
                    required_for="strategy evidence support",
                    source_artifact_ref=_artifact_ref(STRATEGY_EVIDENCE_MAP_ARTIFACT),
                )
            )
        if row.get("drawdown_proxy") is None:
            missing.append(
                _missing(
                    "missing_risk_reward",
                    field="drawdown_proxy",
                    reason="Drawdown/risk proxy is not available.",
                    required_for="strategy risk evidence",
                    source_artifact_ref=_artifact_ref(STRATEGY_EVIDENCE_MAP_ARTIFACT),
                )
            )
        contracts.append(
            _contract(
                contract_type="strategy_evidence",
                source_record_id=strategy_id,
                source_artifact=STRATEGY_EVIDENCE_MAP_ARTIFACT,
                generated_at=generated_at,
                subject={
                    "strategy_family_id": strategy_id,
                    "label": row.get("label"),
                    "current_state": row.get("current_state"),
                    "strategy_evidence_state": row.get("strategy_evidence_state"),
                    "recommended_research_state": row.get("recommended_research_state"),
                    "core_or_proxy_symbols": _safe_list(row.get("core_or_proxy_symbols")),
                },
                metrics={
                    "supporting_relationship_count": row.get("supporting_relationship_count"),
                    "backtest_sample_count": row.get("backtest_sample_count"),
                    "expectancy": row.get("expectancy"),
                    "drawdown_proxy": row.get("drawdown_proxy"),
                },
                lineage={
                    "supporting_result_ids": _safe_list(row.get("supporting_result_ids")),
                    "unsupported_assumptions": _safe_list(row.get("unsupported_assumptions")),
                },
                missing_evidence=missing,
            )
        )
    return contracts


def _build_akber_contracts(context: dict[str, Any], generated_at: str) -> list[dict[str, Any]]:
    contracts: list[dict[str, Any]] = []
    for row in context["akber_results"]:
        result_id = str(row.get("akber_filter_result_id") or "unknown_akber_result")
        decision = _safe_dict(row.get("decision"))
        scores = _safe_dict(row.get("scores"))
        missing = [
            _missing(
                "missing_volume_or_flow",
                field="decision.next_required_evidence",
                reason="Akber result requires volume or flow confirmation.",
                required_for="Akber pass",
                source_artifact_ref=_artifact_ref(AKBER_RESULTS_ARTIFACT),
            )
        ] if "volume_or_flow_confirmation" in _safe_list(decision.get("next_required_evidence")) else []
        if decision.get("filter_decision") != "pass":
            missing.append(
                _missing(
                    "missing_technical_confirmation",
                    field="decision.filter_decision",
                    reason=decision.get("reason") or "Akber filter has not passed.",
                    required_for="router/paper review",
                    source_artifact_ref=_artifact_ref(AKBER_RESULTS_ARTIFACT),
                )
            )
        contracts.append(
            _contract(
                contract_type="akber_evidence",
                source_record_id=result_id,
                source_artifact=AKBER_RESULTS_ARTIFACT,
                generated_at=generated_at,
                subject={
                    "akber_filter_result_id": result_id,
                    "strategy_hypothesis_id": row.get("strategy_hypothesis_id"),
                    "research_goal_id": row.get("research_goal_id"),
                    "status": row.get("status"),
                    "filter_decision": decision.get("filter_decision"),
                    "hold_reason": decision.get("hold_reason"),
                },
                metrics=scores,
                lineage={
                    "candidate_identity_key": row.get("candidate_identity_key"),
                    "threshold_proposal_refs": _safe_list(row.get("threshold_proposal_refs")),
                },
                missing_evidence=missing,
            )
        )
    for row in _safe_list(context["akber_calibration"].get("records")):
        strategy_id = str(row.get("strategy_family_id") or "unknown_akber_calibration")
        missing = [
            _missing(
                str(item).replace("fresh_current_catalyst", "missing_fresh_catalyst")
                if str(item).startswith("missing_")
                else {
                    "fresh_current_catalyst": "missing_fresh_catalyst",
                    "live_volatility_context": "missing_volatility_context",
                    "technical_confirmation": "missing_technical_confirmation",
                    "volume_or_flow_confirmation": "missing_volume_or_flow",
                    "pricing_gap_evidence": "missing_pricing_gap_evidence",
                    "risk_reward_and_invalidation": "missing_risk_reward",
                    "current_liquidity_and_spread": "missing_pricing_gap_evidence",
                }.get(str(item), "missing_technical_confirmation"),
                field="practical_input_gaps",
                reason=f"Akber calibration still requires {item}.",
                required_for="Akber practical pass",
                source_artifact_ref=_artifact_ref(AKBER_CALIBRATION_ARTIFACT),
            )
            for item in _safe_list(row.get("practical_input_gaps"))
        ]
        contracts.append(
            _contract(
                contract_type="akber_evidence",
                source_record_id=f"calibration:{strategy_id}",
                source_artifact=AKBER_CALIBRATION_ARTIFACT,
                generated_at=generated_at,
                subject={
                    "strategy_family_id": strategy_id,
                    "label": row.get("label"),
                    "calibration_state": row.get("calibration_state"),
                },
                metrics={
                    "backtest_sample_count": row.get("backtest_sample_count"),
                    "supporting_relationship_count": row.get("supporting_relationship_count"),
                    "expectancy": row.get("expectancy"),
                    "false_positive_rate_proxy": row.get("false_positive_rate_proxy"),
                    "pass_stage_count": row.get("pass_stage_count"),
                    "hold_stage_count": row.get("hold_stage_count"),
                },
                lineage={
                    "threshold_proposals": row.get("threshold_proposals"),
                    "akber_stage_records": _safe_list(row.get("akber_stage_records")),
                },
                missing_evidence=missing,
            )
        )
    return contracts


def _build_shadow_contracts(context: dict[str, Any], generated_at: str) -> list[dict[str, Any]]:
    contracts: list[dict[str, Any]] = []
    for row in context["shadow_results"]:
        replay_id = str(row.get("shadow_replay_id") or "unknown_shadow_replay")
        decision = _safe_dict(row.get("decision"))
        missing: list[dict[str, Any]] = []
        if decision.get("candidate_for_router") is not True:
            missing.append(
                _missing(
                    "missing_shadow_replay",
                    field="decision.candidate_for_router",
                    reason=decision.get("reason") or "Shadow replay is not router-ready.",
                    required_for="router confidence",
                    source_artifact_ref=_artifact_ref(SHADOW_RESULTS_ARTIFACT),
                )
            )
        contracts.append(
            _contract(
                contract_type="shadow_evidence",
                source_record_id=replay_id,
                source_artifact=SHADOW_RESULTS_ARTIFACT,
                generated_at=generated_at,
                subject={
                    "shadow_replay_id": replay_id,
                    "strategy_hypothesis_id": row.get("strategy_hypothesis_id"),
                    "akber_filter_result_id": row.get("akber_filter_result_id"),
                    "replay_state": row.get("replay_state"),
                    "shadow_status": decision.get("shadow_status"),
                },
                metrics=_safe_dict(row.get("scores")),
                lineage={
                    "source_refs": _safe_list(row.get("source_refs")),
                    "strategy_hypothesis_lineage": _safe_dict(row.get("strategy_hypothesis_lineage")),
                },
                missing_evidence=missing,
            )
        )
    for row in _safe_list(context["shadow_router_map"].get("records")):
        strategy_id = str(row.get("strategy_family_id") or "unknown_shadow_router")
        missing = [
            _missing(
                "missing_technical_confirmation",
                field="blocking_reasons",
                reason=str(reason),
                required_for="shadow-to-router promotion",
                source_artifact_ref=_artifact_ref(SHADOW_ROUTER_MAP_ARTIFACT),
            )
            for reason in _safe_list(row.get("blocking_reasons"))[:8]
        ]
        contracts.append(
            _contract(
                contract_type="shadow_evidence",
                source_record_id=f"baseline_shadow_router:{strategy_id}",
                source_artifact=SHADOW_ROUTER_MAP_ARTIFACT,
                generated_at=generated_at,
                subject={
                    "strategy_family_id": strategy_id,
                    "label": row.get("label"),
                    "dry_router_state": row.get("dry_router_state"),
                },
                metrics={
                    "supporting_relationship_count": row.get("supporting_relationship_count"),
                    "backtest_sample_count": row.get("backtest_sample_count"),
                },
                lineage={
                    "akber_calibration_state": row.get("akber_calibration_state"),
                    "counterfactuals": row.get("counterfactuals"),
                },
                missing_evidence=missing,
            )
        )
    return contracts


def _build_router_contracts(context: dict[str, Any], generated_at: str) -> list[dict[str, Any]]:
    contracts: list[dict[str, Any]] = []
    for row in context["router_decisions"]:
        router_id = str(row.get("router_decision_id") or "unknown_router_decision")
        decision = _safe_dict(row.get("decision"))
        missing: list[dict[str, Any]] = []
        if decision.get("paper_review_candidate") is not True:
            missing.append(
                _missing(
                    "missing_router_decision",
                    field="decision.paper_review_candidate",
                    reason=decision.get("why_not_trading_now") or decision.get("reason") or "Router did not produce a paper-review candidate.",
                    required_for="PaperOps handoff",
                    source_artifact_ref=_artifact_ref(ROUTER_DECISIONS_ARTIFACT),
                )
            )
        for blocker in _safe_list(row.get("soft_blockers"))[:8]:
            if "akber" in str(blocker):
                missing_type = "missing_technical_confirmation"
            elif "volume" in str(blocker) or "flow" in str(blocker):
                missing_type = "missing_volume_or_flow"
            elif "quantum" in str(blocker):
                missing_type = "missing_technical_confirmation"
            else:
                missing_type = "missing_router_decision"
            missing.append(
                _missing(
                    missing_type,
                    field="soft_blockers",
                    reason=str(blocker),
                    required_for="router promotion",
                    source_artifact_ref=_artifact_ref(ROUTER_DECISIONS_ARTIFACT),
                )
            )
        contracts.append(
            _contract(
                contract_type="router_evidence",
                source_record_id=router_id,
                source_artifact=ROUTER_DECISIONS_ARTIFACT,
                generated_at=generated_at,
                subject={
                    "router_decision_id": router_id,
                    "strategy_hypothesis_id": row.get("strategy_hypothesis_id"),
                    "router_output": decision.get("router_output"),
                    "paper_review_candidate": decision.get("paper_review_candidate") is True,
                    "why_not_trading_now": decision.get("why_not_trading_now"),
                },
                metrics=_safe_dict(row.get("scores")),
                lineage=_safe_dict(row.get("lineage")),
                missing_evidence=missing,
            )
        )
    for row in _safe_list(context["shadow_router_map"].get("records")):
        strategy_id = str(row.get("strategy_family_id") or "unknown_router_dry_map")
        missing = [
            _missing(
                "missing_router_decision",
                field="dry_router_state",
                reason=f"Dry router state is {row.get('dry_router_state')}.",
                required_for="paper-review candidate",
                source_artifact_ref=_artifact_ref(SHADOW_ROUTER_MAP_ARTIFACT),
            )
        ]
        contracts.append(
            _contract(
                contract_type="router_evidence",
                source_record_id=f"baseline_router_dry_map:{strategy_id}",
                source_artifact=SHADOW_ROUTER_MAP_ARTIFACT,
                generated_at=generated_at,
                subject={
                    "strategy_family_id": strategy_id,
                    "label": row.get("label"),
                    "dry_router_state": row.get("dry_router_state"),
                    "paper_review_candidate_created": row.get("paper_review_candidate_created") is True,
                },
                metrics={
                    "supporting_relationship_count": row.get("supporting_relationship_count"),
                    "backtest_sample_count": row.get("backtest_sample_count"),
                },
                lineage={
                    "akber_calibration_state": row.get("akber_calibration_state"),
                },
                missing_evidence=missing,
            )
        )
    return contracts


def build_evidence_contracts(settings: Settings | None = None) -> ContractBundle:
    context = _load_context(settings)
    generated_at = _iso()
    records_by_type = {
        "source_evidence": _build_source_contracts(context, generated_at),
        "price_evidence": _build_price_contracts(context, generated_at),
        "source_price_relationship_evidence": _build_relationship_contracts(context, generated_at),
        "hypothesis_evidence": _build_hypothesis_contracts(context, generated_at),
        "strategy_evidence": _build_strategy_contracts(context, generated_at),
        "akber_evidence": _build_akber_contracts(context, generated_at),
        "shadow_evidence": _build_shadow_contracts(context, generated_at),
        "router_evidence": _build_router_contracts(context, generated_at),
    }
    contract_counts = {key: len(value) for key, value in records_by_type.items()}
    all_records = [record for records in records_by_type.values() for record in records]
    missing_counter = Counter(
        item.get("missing_evidence_type")
        for record in all_records
        for item in _safe_list(record.get("missing_evidence"))
    )
    missing_by_type = {
        key: sum(record.get("missing_evidence_count", 0) for record in value)
        for key, value in records_by_type.items()
    }
    downstream_reader_contract = {
        "status": "evidence_contracts_available_for_safe_readers",
        "safe_refactor_scope": [
            "dashboard_next_generation_backtest_state",
            "dashboard_freshness_and_decision_records",
            "phase2_certification_checks",
        ],
        "not_refactored_yet": [
            "order-producing PaperOps route",
            "Akber production filter thresholds",
            "strategy router production decisions",
        ],
        "reason": "Phase 2 provides normalized evidence contracts first; later phases may consume them for stronger logic.",
    }
    summary_status = "evidence_contracts_ready" if all(contract_counts.values()) else "evidence_contracts_ready_with_empty_sections"
    summary = {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "qadam_evidence_contracts_summary",
        "phase_id": PHASE_ID,
        "generated_at": generated_at,
        "status": summary_status,
        "contract_type_count": len(records_by_type),
        "required_contract_types": list(REQUIRED_CONTRACT_TYPES),
        "contract_counts": contract_counts,
        "total_contract_count": len(all_records),
        "missing_evidence_count": sum(missing_by_type.values()),
        "missing_evidence_by_contract_type": missing_by_type,
        "missing_evidence_type_counts": dict(sorted(missing_counter.items())),
        "contracts_with_missing_evidence_count": sum(1 for record in all_records if record.get("missing_evidence_count", 0) > 0),
        "downstream_reader_contract": downstream_reader_contract,
        "paper_order_created_count": 0,
        "broker_write_count": 0,
        "live_capital_enabled": False,
        "proof_credit_allowed": False,
        "paper_growth_trial_calendar_advanced": False,
        "authority": _authority(),
        "artifact_refs": {
            "primary": _artifact_ref(PRIMARY_ARTIFACT),
            "dashboard_summary": _artifact_ref(DASHBOARD_SUMMARY_ARTIFACT),
            **{key: _artifact_ref(filename) for key, filename in CONTRACT_ARTIFACTS.items()},
        },
    }
    primary = {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "qadam_evidence_contracts",
        "phase_id": PHASE_ID,
        "generated_at": generated_at,
        "status": summary_status,
        "summary": summary,
        "contract_artifacts": CONTRACT_ARTIFACTS,
        "contract_samples": {
            key: value[:3] for key, value in records_by_type.items()
        },
        "authority": _authority(),
    }
    dashboard_summary = {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "qadam_evidence_contracts_dashboard_summary",
        "phase_id": PHASE_ID,
        "generated_at": generated_at,
        "status": summary_status,
        "public_safe": True,
        "read_only": True,
        "paper_only": True,
        "command_disabled": True,
        "total_contract_count": summary["total_contract_count"],
        "contract_counts": contract_counts,
        "missing_evidence_count": summary["missing_evidence_count"],
        "missing_evidence_type_counts": summary["missing_evidence_type_counts"],
        "contracts_with_missing_evidence_count": summary["contracts_with_missing_evidence_count"],
        "downstream_reader_state": downstream_reader_contract["status"],
        "message": (
            "Qadam has normalized evidence contracts for sources, prices, source-price "
            "relationships, hypotheses, strategies, Akber, shadow review, and router state. "
            "Missing evidence is typed and explicit."
        ),
        "paper_order_created_count": 0,
        "broker_write_count": 0,
        "live_capital_enabled": False,
        "proof_credit_allowed": False,
        "authority": _authority(),
        "artifact_refs": summary["artifact_refs"],
    }
    return ContractBundle(
        primary=primary,
        summary=summary,
        dashboard_summary=dashboard_summary,
        records_by_type=records_by_type,
    )


def _paths(settings: Settings | None = None) -> dict[str, Path]:
    runtime = _runtime_dir(settings)
    paths = {
        "primary": runtime / PRIMARY_ARTIFACT,
        "summary": runtime / SUMMARY_ARTIFACT,
        "dashboard_summary": runtime / DASHBOARD_SUMMARY_ARTIFACT,
        "events": runtime / EVENTS_ARTIFACT,
    }
    paths.update({key: runtime / filename for key, filename in CONTRACT_ARTIFACTS.items()})
    return paths


def write_evidence_contracts(
    bundle: ContractBundle,
    settings: Settings | None = None,
) -> dict[str, str]:
    paths = _paths(settings)
    written: dict[str, str] = {}
    _write_json(paths["primary"], bundle.primary)
    written["primary"] = str(paths["primary"])
    _write_json(paths["summary"], bundle.summary)
    written["summary"] = str(paths["summary"])
    _write_json(paths["dashboard_summary"], bundle.dashboard_summary)
    written["dashboard_summary"] = str(paths["dashboard_summary"])
    for contract_type, records in bundle.records_by_type.items():
        _write_jsonl(paths[contract_type], records)
        written[contract_type] = str(paths[contract_type])
    _append_jsonl(
        paths["events"],
        {
            "generated_at": bundle.summary["generated_at"],
            "event": "evidence_contracts_written",
            "status": bundle.summary["status"],
            "total_contract_count": bundle.summary["total_contract_count"],
            "missing_evidence_count": bundle.summary["missing_evidence_count"],
        },
    )
    written["events"] = str(paths["events"])
    return written


def build_and_write_evidence_contracts(settings: Settings | None = None) -> tuple[ContractBundle, dict[str, str], list[str]]:
    bundle = build_evidence_contracts(settings)
    written = write_evidence_contracts(bundle, settings)
    errors = validate_evidence_contract_bundle(load_evidence_contracts(settings))
    return bundle, written, errors


def load_evidence_contracts(settings: Settings | None = None) -> dict[str, Any]:
    paths = _paths(settings)
    return {
        "primary": _read_json(paths["primary"]),
        "summary": _read_json(paths["summary"]),
        "dashboard_summary": _read_json(paths["dashboard_summary"]),
        "records_by_type": {
            contract_type: _read_jsonl(paths[contract_type])
            for contract_type in REQUIRED_CONTRACT_TYPES
        },
    }


def _validate_authority(payload: dict[str, Any], prefix: str) -> list[str]:
    errors: list[str] = []
    authority = _safe_dict(payload.get("authority"))
    for field in FORBIDDEN_TRUE_FIELDS:
        if payload.get(field) is True:
            errors.append(f"{prefix}_forbidden_true:{field}")
        if authority.get(field) is True:
            errors.append(f"{prefix}_authority_forbidden_true:{field}")
    for field in FORBIDDEN_NONZERO_FIELDS:
        if _int(payload.get(field)) != 0 and field in payload:
            errors.append(f"{prefix}_forbidden_nonzero:{field}")
        if _int(authority.get(field)) != 0:
            errors.append(f"{prefix}_authority_forbidden_nonzero:{field}")
    return errors


def validate_evidence_contract_record(record: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    required = {
        "schema_version",
        "phase_id",
        "contract_type",
        "contract_id",
        "source_record_id",
        "source_artifact_ref",
        "generated_at",
        "status",
        "evidence_state",
        "missing_evidence_count",
        "missing_evidence",
        "completeness_score",
        "subject",
        "metrics",
        "lineage",
        "public_safe",
        "read_only",
        "paper_only",
        "authority",
    }
    missing_fields = required - set(record)
    errors.extend(f"missing_field:{field}" for field in sorted(missing_fields))
    if record.get("schema_version") != SCHEMA_VERSION:
        errors.append("schema_version_invalid")
    if record.get("contract_type") not in REQUIRED_CONTRACT_TYPES:
        errors.append("contract_type_invalid")
    if record.get("public_safe") is not True:
        errors.append("public_safe_not_true")
    if record.get("read_only") is not True:
        errors.append("read_only_not_true")
    if record.get("paper_only") is not True:
        errors.append("paper_only_not_true")
    missing_evidence = _safe_list(record.get("missing_evidence"))
    if _int(record.get("missing_evidence_count")) != len(missing_evidence):
        errors.append("missing_evidence_count_mismatch")
    if missing_evidence and record.get("evidence_state") != "missing_typed":
        errors.append("missing_evidence_not_typed")
    for index, item in enumerate(missing_evidence):
        for field in ("missing_evidence_type", "severity", "field", "reason", "required_for"):
            if not item.get(field):
                errors.append(f"missing_evidence_{index}_missing_field:{field}")
    errors.extend(_validate_authority(record, str(record.get("contract_id") or "contract")))
    return errors


def validate_evidence_contract_bundle(bundle: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    summary = _safe_dict(bundle.get("summary"))
    dashboard = _safe_dict(bundle.get("dashboard_summary"))
    records_by_type = _safe_dict(bundle.get("records_by_type"))
    if summary.get("schema_version") != SCHEMA_VERSION:
        errors.append("summary_schema_version_invalid")
    if dashboard.get("command_disabled") is not True:
        errors.append("dashboard_command_disabled_not_true")
    if dashboard.get("read_only") is not True:
        errors.append("dashboard_read_only_not_true")
    for contract_type in REQUIRED_CONTRACT_TYPES:
        records = _safe_list(records_by_type.get(contract_type))
        if not records:
            errors.append(f"{contract_type}_records_missing")
        if _safe_dict(summary.get("contract_counts")).get(contract_type) != len(records):
            errors.append(f"{contract_type}_summary_count_mismatch")
        for index, record in enumerate(records[:1000]):
            for error in validate_evidence_contract_record(record):
                errors.append(f"{contract_type}[{index}]:{error}")
    if _int(summary.get("total_contract_count")) != sum(len(_safe_list(records_by_type.get(item))) for item in REQUIRED_CONTRACT_TYPES):
        errors.append("total_contract_count_mismatch")
    if _int(summary.get("paper_order_created_count")) != 0:
        errors.append("summary_paper_order_created_count_nonzero")
    if _int(summary.get("broker_write_count")) != 0:
        errors.append("summary_broker_write_count_nonzero")
    for field in ("live_capital_enabled", "proof_credit_allowed", "paper_growth_trial_calendar_advanced"):
        if summary.get(field) is not False:
            errors.append(f"summary_forbidden_true:{field}")
    errors.extend(_validate_authority(summary, "summary"))
    errors.extend(_validate_authority(dashboard, "dashboard"))
    return sorted(set(errors))


def validate_negative_evidence_contract_probes(settings: Settings | None = None) -> list[str]:
    bundle = load_evidence_contracts(settings)
    errors: list[str] = []
    if not bundle.get("summary"):
        return ["negative_probe_skipped_missing_contracts"]
    order_probe = json.loads(json.dumps(bundle))
    order_probe["summary"]["paper_order_created_count"] = 1
    if not any("paper_order_created_count" in error for error in validate_evidence_contract_bundle(order_probe)):
        errors.append("negative_probe_failed_for_paper_order_count")
    authority_probe = json.loads(json.dumps(bundle))
    records = authority_probe.get("records_by_type", {}).get("router_evidence", [])
    if records:
        records[0]["authority"]["paper_order_allowed"] = True
        if not any("paper_order_allowed" in error for error in validate_evidence_contract_bundle(authority_probe)):
            errors.append("negative_probe_failed_for_record_authority")
    missing_probe = json.loads(json.dumps(bundle))
    source_records = missing_probe.get("records_by_type", {}).get("price_evidence", [])
    if source_records:
        source_records[0]["missing_evidence_count"] = 3 + len(_safe_list(source_records[0].get("missing_evidence")))
        if not any("missing_evidence_count_mismatch" in error for error in validate_evidence_contract_bundle(missing_probe)):
            errors.append("negative_probe_failed_for_missing_evidence_count")
    return errors


LANE_CONTRIBUTION_STATES = {
    "observed",
    "evidence_qualified",
    "pattern_nominated",
    "strategy_nominated",
    "paper_review_nominated",
    "held",
    "rejected",
    "expired",
}

LANE_AUTHORITY_ORDER = {f"A{index}": index for index in range(7)}


def lane_capability_index() -> dict[str, dict[str, Any]]:
    """Return the reviewed lane registry keyed by stable lane id."""

    registry = read_policy_json(repo_root() / LANE_REGISTRY_PATH)
    rows = registry.get("lanes") if isinstance(registry.get("lanes"), list) else []
    return {
        str(row.get("lane_id")): row
        for row in rows
        if isinstance(row, dict) and row.get("lane_id")
    }


def build_lane_contribution(
    *,
    lane_id: str,
    contribution_state: str,
    authority_tier: str,
    evidence_profile: str,
    subject: dict[str, Any],
    evidence_refs: list[str],
    generation_id: str,
    observed_at: str | None,
    expires_at: str | None,
    blockers: list[dict[str, Any]] | None = None,
    canonical_draft: dict[str, Any] | None = None,
    agent_contributions: list[dict[str, Any]] | None = None,
    critic_receipts: list[dict[str, Any]] | None = None,
    generated_at: str | None = None,
) -> dict[str, Any]:
    """Build one paper-only contribution for the canonical compiler boundary."""

    capabilities = lane_capability_index()
    capability = capabilities.get(lane_id, {})
    material = {
        "lane_id": lane_id,
        "state": contribution_state,
        "generation_id": generation_id,
        "subject": subject,
        "evidence_refs": sorted(set(evidence_refs)),
    }
    return {
        "schema_version": CONTRIBUTION_SCHEMA_VERSION,
        "artifact_type": "qadam_lane_contribution",
        "contribution_id": stable_id("lane-contribution", material),
        "generated_at": generated_at or _iso(),
        "lane_id": lane_id,
        "lane_owner": capability.get("owner"),
        "contribution_state": contribution_state,
        "authority_tier": authority_tier,
        "maximum_authority": capability.get("maximum_authority"),
        "evidence_profile": evidence_profile,
        "generation_id": generation_id,
        "observed_at": observed_at,
        "expires_at": expires_at,
        "subject": subject,
        "evidence_refs": sorted(set(str(value) for value in evidence_refs if value)),
        "blockers": blockers or [],
        "canonical_draft": canonical_draft,
        "agent_contributions": agent_contributions or [],
        "critic_receipts": critic_receipts or [],
        "next_stage": capability.get("downstream"),
        "public_safe": True,
        "paper_only": True,
        "authority": public_authority(),
    }


def validate_lane_contribution(record: dict[str, Any]) -> list[str]:
    """Fail closed on shape, lineage, authority or lane-capability drift."""

    errors: list[str] = []
    capabilities = lane_capability_index()
    lane_id = str(record.get("lane_id") or "")
    capability = capabilities.get(lane_id)
    if record.get("schema_version") != CONTRIBUTION_SCHEMA_VERSION:
        errors.append("lane_contribution_schema_invalid")
    if capability is None:
        errors.append("lane_contribution_lane_unregistered")
        return errors
    if record.get("lane_owner") != capability.get("owner"):
        errors.append("lane_contribution_owner_mismatch")
    if record.get("contribution_state") not in LANE_CONTRIBUTION_STATES:
        errors.append("lane_contribution_state_invalid")
    tier = str(record.get("authority_tier") or "")
    maximum = str(capability.get("maximum_authority") or "")
    if tier not in LANE_AUTHORITY_ORDER or maximum not in LANE_AUTHORITY_ORDER:
        errors.append("lane_contribution_authority_invalid")
    elif LANE_AUTHORITY_ORDER[tier] > LANE_AUTHORITY_ORDER[maximum]:
        errors.append("lane_contribution_authority_exceeds_capability")
    if not record.get("contribution_id"):
        errors.append("lane_contribution_id_missing")
    if not record.get("generation_id"):
        errors.append("lane_contribution_generation_missing")
    if not isinstance(record.get("subject"), dict):
        errors.append("lane_contribution_subject_invalid")
    if not isinstance(record.get("evidence_refs"), list):
        errors.append("lane_contribution_evidence_refs_invalid")
    if tier in {"A3", "A4"} and not isinstance(record.get("canonical_draft"), dict):
        errors.append("lane_contribution_canonical_draft_missing")
    if record.get("contribution_state") in {"strategy_nominated", "paper_review_nominated"} and not record.get("evidence_refs"):
        errors.append("lane_contribution_nomination_without_evidence")
    authority = record.get("authority") if isinstance(record.get("authority"), dict) else {}
    for field in (
        "trade_candidate_creation_allowed",
        "risk_approval_allowed",
        "execution_approval_allowed",
        "paper_order_allowed",
        "broker_write_allowed",
        "live_capital_enabled",
        "proof_credit_allowed",
    ):
        if authority.get(field) is not False:
            errors.append(f"lane_contribution_forbidden_authority:{field}")
    if record.get("public_safe") is not True or record.get("paper_only") is not True:
        errors.append("lane_contribution_boundary_invalid")
    return sorted(set(errors))
