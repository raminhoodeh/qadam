"""QSASE phases 5-10 completion layers.

These V2 layers convert the current QSASE research stack into explicit
graduation, foundry, Akber, shadow, router, and PaperOps handoff decisions.
They are paper-only, read-only until guarded PaperOps receives a valid handoff,
and they create no orders, broker writes, proof credit, or live-capital
authority.
"""

from __future__ import annotations

import hashlib
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from orchestrator.config import Settings
from orchestrator.qsase_governance_safety_contract import universal_authority_flags

SCHEMA_VERSION = "qsase_phase5_to10_completion.v1"

VALIDATED_EDGE_ARTIFACT = "qsase_validated_edge_graduation.json"
VALIDATED_EDGE_RECORDS_ARTIFACT = "qsase_validated_edges.jsonl"
EDGE_REJECTIONS_ARTIFACT = "qsase_edge_rejections.jsonl"
VALIDATED_EDGE_DASHBOARD_ARTIFACT = "qsase_validated_edge_graduation_dashboard_summary.json"

PATTERN_SEARCH_V2_ARTIFACT = "qsase_full_universe_pattern_search_v2.json"
PATTERN_SEARCH_V2_RECORDS_ARTIFACT = "qsase_full_universe_patterns_v2.jsonl"
PATTERN_SEARCH_V2_REJECTIONS_ARTIFACT = "qsase_full_universe_pattern_rejections_v2.jsonl"
PATTERN_SEARCH_V2_DASHBOARD_ARTIFACT = "qsase_full_universe_pattern_search_v2_dashboard_summary.json"

STRATEGY_FOUNDRY_V2_ARTIFACT = "qsase_strategy_foundry_v2.json"
STRATEGY_HYPOTHESES_V2_ARTIFACT = "qsase_strategy_hypotheses_v2.jsonl"
REJECTED_STRATEGY_HYPOTHESES_V2_ARTIFACT = "qsase_rejected_strategy_hypotheses_v2.jsonl"
STRATEGY_FOUNDRY_V2_DASHBOARD_ARTIFACT = "qsase_strategy_foundry_v2_dashboard_summary.json"

AKBER_V2_ARTIFACT = "qsase_akber_filter_v2.json"
AKBER_STAGE_RECORDS_V2_ARTIFACT = "qsase_akber_stage_records_v2.jsonl"
AKBER_V2_DASHBOARD_ARTIFACT = "qsase_akber_filter_v2_dashboard_summary.json"

SHADOW_V2_ARTIFACT = "qsase_shadow_simulator_v2.json"
SHADOW_RESULTS_V2_ARTIFACT = "qsase_shadow_results_v2.jsonl"
SHADOW_COUNTERFACTUALS_V2_ARTIFACT = "qsase_shadow_counterfactuals_v2.jsonl"
SHADOW_REJECTIONS_V2_ARTIFACT = "qsase_shadow_rejections_v2.jsonl"
SHADOW_V2_DASHBOARD_ARTIFACT = "qsase_shadow_simulator_v2_dashboard_summary.json"

ROUTER_V2_ARTIFACT = "qsase_strategy_router_v2.json"
ROUTER_DECISIONS_V2_ARTIFACT = "qsase_strategy_router_decisions_v2.jsonl"
ROUTER_SCOREBOARD_V2_ARTIFACT = "qsase_strategy_router_scoreboard_v2.json"
WHY_NOT_V2_ARTIFACT = "qsase_why_not_trading_now_v2.json"
PAPEROPS_HANDOFF_V2_ARTIFACT = "qsase_paperops_handoff_v2.json"
PAPEROPS_HANDOFF_RECORDS_V2_ARTIFACT = "qsase_paperops_handoffs_v2.jsonl"
PAPEROPS_REJECTED_HANDOFFS_V2_ARTIFACT = "qsase_paperops_rejected_handoffs_v2.jsonl"
ROUTER_V2_DASHBOARD_ARTIFACT = "qsase_strategy_router_v2_dashboard_summary.json"

HISTORY_ARTIFACT = "qsase_phase5_to10_completion_history.jsonl"
EVENTS_ARTIFACT = "qsase_phase5_to10_completion_events.jsonl"
PHASE_STATUS_ARTIFACT = "qsase_phase_implementation_status.json"

CANDIDATE_PATTERNS_ARTIFACT = "qsase_candidate_patterns.jsonl"
LINEAR_RESULTS_ARTIFACT = "qsase_linear_backtest_results.jsonl"
NONLINEAR_RESULTS_ARTIFACT = "qsase_nonlinear_pattern_results.jsonl"
QUANTUM_REVIEWS_ARTIFACT = "qsase_quantum_pattern_reviews.jsonl"
HISTORICAL_COMPLETION_ARTIFACT = "qsase_historical_memory_completion.json"
SOURCE_RELIABILITY_ARTIFACT = "qsase_source_reliability.json"
MARKET_CONFIRMATION_ARTIFACT = "qsase_market_confirmation.json"
MARKET_CONFIRMATION_PACKETS_ARTIFACT = "qsase_market_confirmation_packets.jsonl"
AKBER_INPUT_COMPLETENESS_ARTIFACT = "qsase_akber_input_completeness.json"
STRATEGY_HYPOTHESES_ARTIFACT = "qsase_strategy_hypotheses.jsonl"
AKBER_RESULTS_ARTIFACT = "qsase_akber_filter_results.jsonl"
SHADOW_RESULTS_ARTIFACT = "qsase_shadow_strategy_results.jsonl"
ROUTER_DECISIONS_ARTIFACT = "qsase_strategy_router_decisions.jsonl"
PAPEROPS_GATE_ARTIFACT = "qsase_paperops_gate_interface.json"
PAPEROPS_SUMMARY_ARTIFACT = "paperops_autonomous_pass_summary.json"

EDGE_GRADUATION_TARGETS = {
    "min_sample_size": 50,
    "min_hit_rate": 0.52,
    "min_expectancy": 0.0,
    "max_false_positive_risk": 0.35,
    "min_regime_stability": 0.60,
    "min_out_of_sample_survival": 0.60,
    "min_complete_forward_window_ratio": 0.80,
    "min_required_source_freshness_ratio": 0.95,
}

AUTHORITY_FLAGS = {
    "review_only": True,
    "trade_candidate_created": False,
    "trade_candidate_creation_allowed": False,
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
    "live_broker_endpoint_allowed": False,
    "paperops_direct_call_allowed": False,
    "paperops_bypass_allowed": False,
    "qctrl_bypass_allowed": False,
    "proof_credit_allowed": False,
    "paper_proof_ledger_credit_allowed": False,
    "paper_growth_trial_calendar_advance_allowed": False,
    "simulated_elapsed_time_allowed": False,
    "strategy_mutation_allowed": False,
    "strategy_mutation_created": False,
    "source_trust_update_allowed": False,
    "source_trust_update_created": False,
    "model_weight_update_allowed": False,
    "model_weight_update_created": False,
    "filter_threshold_update_allowed": False,
    "filter_threshold_update_created": False,
    "telegram_command_path_enabled": False,
    "telegram_trade_command_enabled": False,
    "live_capital_enabled": False,
}

FALSE_AUTHORITY_FIELDS = {key for key, value in AUTHORITY_FLAGS.items() if value is False}


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


def _iso(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).isoformat()


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


def _artifact_ref(filename: str) -> str:
    return f"data/runtime/{filename}"


def _hash_id(parts: list[Any], prefix: str) -> str:
    raw = "|".join(str(part) for part in parts)
    return f"{prefix}:{hashlib.sha256(raw.encode('utf-8')).hexdigest()[:20]}"


def _safe_list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def _safe_dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _float(value: Any, default: float = 0.0) -> float:
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


def _int(value: Any, default: int = 0) -> int:
    if isinstance(value, bool):
        return int(value)
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


def _slug(value: Any) -> str:
    return str(value or "").strip().lower().replace(" ", "_").replace("-", "_")


def _load_context(settings: Settings | None = None) -> dict[str, Any]:
    runtime = _runtime_dir(settings)
    return {
        "runtime": runtime,
        "candidate_patterns": _read_jsonl(runtime / CANDIDATE_PATTERNS_ARTIFACT, limit=1000),
        "linear_results": _read_jsonl(runtime / LINEAR_RESULTS_ARTIFACT, limit=1000),
        "nonlinear_results": _read_jsonl(runtime / NONLINEAR_RESULTS_ARTIFACT, limit=1000),
        "quantum_reviews": _read_jsonl(runtime / QUANTUM_REVIEWS_ARTIFACT, limit=1000),
        "historical_completion": _read_json(runtime / HISTORICAL_COMPLETION_ARTIFACT),
        "source_reliability": _read_json(runtime / SOURCE_RELIABILITY_ARTIFACT),
        "market_confirmation": _read_json(runtime / MARKET_CONFIRMATION_ARTIFACT),
        "market_packets": _read_jsonl(runtime / MARKET_CONFIRMATION_PACKETS_ARTIFACT, limit=1000),
        "akber_input_completeness": _read_json(runtime / AKBER_INPUT_COMPLETENESS_ARTIFACT),
        "v1_strategy_hypotheses": _read_jsonl(runtime / STRATEGY_HYPOTHESES_ARTIFACT, limit=1000),
        "v1_akber_results": _read_jsonl(runtime / AKBER_RESULTS_ARTIFACT, limit=1000),
        "v1_shadow_results": _read_jsonl(runtime / SHADOW_RESULTS_ARTIFACT, limit=1000),
        "v1_router_decisions": _read_jsonl(runtime / ROUTER_DECISIONS_ARTIFACT, limit=1000),
        "paperops_gate": _read_json(runtime / PAPEROPS_GATE_ARTIFACT),
        "paperops_summary": _read_json(runtime / PAPEROPS_SUMMARY_ARTIFACT),
    }


def _by_key(rows: list[dict[str, Any]], *keys: str) -> dict[str, dict[str, Any]]:
    lookup: dict[str, dict[str, Any]] = {}
    for row in rows:
        for key in keys:
            value = row.get(key)
            if isinstance(value, str) and value:
                lookup.setdefault(value, row)
    return lookup


def _market_family(row: dict[str, Any]) -> str:
    market = _safe_dict(row.get("market_expression"))
    candidate = _safe_dict(row.get("candidate_identity"))
    families = _safe_list(row.get("market_families"))
    return str(market.get("asset_class") or candidate.get("asset_class") or (families[0] if families else "unknown"))


def _instrument(row: dict[str, Any]) -> str:
    market = _safe_dict(row.get("market_expression"))
    candidate = _safe_dict(row.get("candidate_identity"))
    symbols = _safe_list(row.get("market_symbols"))
    return str(candidate.get("instrument") or market.get("instrument") or market.get("observed_market_expression") or (symbols[0] if symbols else "unknown"))


def _strategy_family(row: dict[str, Any]) -> str:
    family = _safe_dict(row.get("family_mapping"))
    labels = _safe_list(row.get("initial_strategy_labels"))
    strategy_family = row.get("strategy_family")
    return str(
        strategy_family
        or family.get("mapped_existing_family")
        or family.get("primary_family")
        or (labels[0] if labels else "unmapped_strategy_family")
    )


def _lineage_id(row: dict[str, Any]) -> str:
    return str(row.get("source_pattern_id") or row.get("pattern_id") or row.get("strategy_hypothesis_id") or "")


def _match_source(rows: list[dict[str, Any]], source_pattern_id: str) -> dict[str, Any]:
    for row in rows:
        if row.get("source_pattern_id") == source_pattern_id or row.get("pattern_id") == source_pattern_id:
            return row
    return {}


def _score_bool(condition: bool) -> float:
    return 1.0 if condition else 0.0


def _edge_metrics(linear: dict[str, Any], nonlinear: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
    risk = _safe_dict(linear.get("risk"))
    sample = _safe_dict(linear.get("sample"))
    linear_components = _safe_dict(linear.get("linear_score_components"))
    nonlinear_tests = _safe_dict(nonlinear.get("nonlinear_tests"))
    decision = _safe_dict(nonlinear.get("decision"))
    historical = _safe_dict(context.get("historical_completion"))
    source_rel = _safe_dict(context.get("source_reliability"))
    return {
        "sample_size": _int(sample.get("complete_forward_outcome_count"), _int(linear.get("sample_size"), 0)),
        "hit_rate": _float(risk.get("hit_rate"), 0.0),
        "expectancy": _float(risk.get("expectancy"), 0.0),
        "max_drawdown": abs(_float(risk.get("tail_loss_95"), 0.0)),
        "false_positive_risk": _float(_safe_dict(_safe_dict(linear.get("tests")).get("false_positive_control")).get("false_positive_risk"), 1.0),
        "regime_stability": _float(linear_components.get("regime_durability"), _float(nonlinear_tests.get("regime_dependence_score"), 0.0)),
        "out_of_sample_survival": _float(linear_components.get("out_of_sample_survival"), _float(nonlinear_tests.get("walk_forward_survival"), 0.0)),
        "complete_forward_window_ratio": _float(historical.get("complete_forward_window_ratio"), 0.0),
        "required_source_freshness_ratio": _float(source_rel.get("required_source_freshness_ratio"), 0.0),
        "linear_score": _float(linear.get("linear_score"), 0.0),
        "nonlinear_score": _float(nonlinear_tests.get("nonlinear_score"), _float(nonlinear.get("nonlinear_score"), 0.0)),
        "nonlinear_baseline_beaten": bool(nonlinear_tests.get("linear_baseline_beaten")),
        "quantum_recommendation": str(decision.get("quantum_review_recommendation") or nonlinear.get("quantum_review_state") or "not_recorded"),
        "point_in_time_safe": bool(sample.get("point_in_time_safe")),
    }


def _graduation_criteria(metrics: dict[str, Any]) -> dict[str, dict[str, Any]]:
    targets = EDGE_GRADUATION_TARGETS
    return {
        "sample_size": {
            "passed": metrics["sample_size"] >= targets["min_sample_size"],
            "value": metrics["sample_size"],
            "target": targets["min_sample_size"],
        },
        "hit_rate": {
            "passed": metrics["hit_rate"] >= targets["min_hit_rate"],
            "value": metrics["hit_rate"],
            "target": targets["min_hit_rate"],
        },
        "expectancy": {
            "passed": metrics["expectancy"] > targets["min_expectancy"],
            "value": metrics["expectancy"],
            "target": targets["min_expectancy"],
        },
        "false_positive_risk": {
            "passed": metrics["false_positive_risk"] <= targets["max_false_positive_risk"],
            "value": metrics["false_positive_risk"],
            "target": targets["max_false_positive_risk"],
        },
        "regime_stability": {
            "passed": metrics["regime_stability"] >= targets["min_regime_stability"],
            "value": metrics["regime_stability"],
            "target": targets["min_regime_stability"],
        },
        "out_of_sample_survival": {
            "passed": metrics["out_of_sample_survival"] >= targets["min_out_of_sample_survival"],
            "value": metrics["out_of_sample_survival"],
            "target": targets["min_out_of_sample_survival"],
        },
        "complete_forward_window_ratio": {
            "passed": metrics["complete_forward_window_ratio"] >= targets["min_complete_forward_window_ratio"],
            "value": metrics["complete_forward_window_ratio"],
            "target": targets["min_complete_forward_window_ratio"],
        },
        "required_source_freshness_ratio": {
            "passed": metrics["required_source_freshness_ratio"] >= targets["min_required_source_freshness_ratio"],
            "value": metrics["required_source_freshness_ratio"],
            "target": targets["min_required_source_freshness_ratio"],
        },
        "nonlinear_incremental_value": {
            "passed": metrics["nonlinear_baseline_beaten"] is True,
            "value": metrics["nonlinear_baseline_beaten"],
            "target": True,
        },
        "quantum_not_downgrade_or_hold": {
            "passed": "downgrade_or_hold" not in metrics["quantum_recommendation"],
            "value": metrics["quantum_recommendation"],
            "target": "not downgrade_or_hold",
        },
    }


def build_validated_edge_graduation(context: dict[str, Any], generated_at: str) -> tuple[dict[str, Any], list[dict[str, Any]], list[dict[str, Any]]]:
    nonlinear_by_source = _by_key(context["nonlinear_results"], "source_pattern_id")
    records: list[dict[str, Any]] = []
    rejections: list[dict[str, Any]] = []
    for linear in context["linear_results"]:
        source_pattern_id = str(linear.get("source_pattern_id") or "")
        if not source_pattern_id:
            continue
        nonlinear = nonlinear_by_source.get(source_pattern_id, {})
        metrics = _edge_metrics(linear, nonlinear, context)
        criteria = _graduation_criteria(metrics)
        failed = [name for name, item in criteria.items() if not item["passed"]]
        accepted = not failed
        record = {
            "schema_version": SCHEMA_VERSION,
            "artifact_type": "qsase_validated_edge_record",
            "validated_edge_id": _hash_id([SCHEMA_VERSION, source_pattern_id, "validated-edge"], "qsase-edge-v2"),
            "generated_at": generated_at,
            "source_pattern_id": source_pattern_id,
            "linear_pattern_id": linear.get("linear_pattern_id"),
            "nonlinear_pattern_id": nonlinear.get("nonlinear_pattern_id"),
            "strategy_family": _strategy_family(linear),
            "instrument": _instrument(linear),
            "market_family": _market_family(linear),
            "graduation_state": "validated_edge" if accepted else "edge_under_observation",
            "accepted_as_validated_edge": accepted,
            "criteria": criteria,
            "failed_criteria": failed,
            "metrics": metrics,
            "source_price_lineage": {
                "linear_result_ref": _artifact_ref(LINEAR_RESULTS_ARTIFACT),
                "nonlinear_result_ref": _artifact_ref(NONLINEAR_RESULTS_ARTIFACT),
                "historical_completion_ref": _artifact_ref(HISTORICAL_COMPLETION_ARTIFACT),
                "source_reliability_ref": _artifact_ref(SOURCE_RELIABILITY_ARTIFACT),
            },
            "next_action": "eligible_for_strategy_foundry_v2" if accepted else "repair_failed_criteria_before_strategy_foundry",
            "authority": AUTHORITY_FLAGS,
            "execution_allowed": False,
            "paper_order_created": False,
            "broker_write_allowed": False,
            "proof_credit_allowed": False,
            "live_capital_enabled": False,
        }
        if accepted:
            records.append(record)
        else:
            rejection = {
                **record,
                "artifact_type": "qsase_edge_rejection_record",
                "edge_rejection_id": _hash_id([record["validated_edge_id"], "rejection"], "qsase-edge-reject-v2"),
                "rejection_reasons": failed,
                "retest_condition": "complete the failed criteria and rerun edge graduation",
            }
            rejections.append(rejection)
            records.append(record)

    accepted_count = sum(1 for row in records if row.get("accepted_as_validated_edge") is True)
    payload = {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "qsase_validated_edge_graduation",
        "generated_at": generated_at,
        "status": "qsase_validated_edge_graduation_ready" if accepted_count else "qsase_validated_edge_graduation_ready_no_validated_edges",
        "public_safe": True,
        "read_only": True,
        "command_disabled": True,
        "paper_only": True,
        "research_only": True,
        "proposal_first": True,
        "authority": universal_authority_flags(),
        "authority_flags": AUTHORITY_FLAGS,
        "input_linear_result_count": len(context["linear_results"]),
        "graduation_record_count": len(records),
        "validated_edge_count": accepted_count,
        "edge_rejection_count": len(rejections),
        "targets": EDGE_GRADUATION_TARGETS,
        "records_path": _artifact_ref(VALIDATED_EDGE_RECORDS_ARTIFACT),
        "rejections_path": _artifact_ref(EDGE_REJECTIONS_ARTIFACT),
        "top_failed_criteria": dict(Counter(reason for row in rejections for reason in row.get("rejection_reasons", [])).most_common(8)),
        "paper_order_created_count": 0,
        "broker_write_count": 0,
        "proof_credit_allowed": False,
        "live_capital_enabled": False,
    }
    return payload, records, rejections


def build_pattern_search_v2(context: dict[str, Any], edge_records: list[dict[str, Any]], generated_at: str) -> tuple[dict[str, Any], list[dict[str, Any]], list[dict[str, Any]]]:
    edge_by_source = _by_key(edge_records, "source_pattern_id")
    linear_by_source = _by_key(context["linear_results"], "source_pattern_id")
    nonlinear_by_source = _by_key(context["nonlinear_results"], "source_pattern_id")
    records: list[dict[str, Any]] = []
    rejections: list[dict[str, Any]] = []
    for index, pattern in enumerate(context["candidate_patterns"]):
        source_pattern_id = str(pattern.get("pattern_id") or "")
        edge = edge_by_source.get(source_pattern_id, {})
        linear = linear_by_source.get(source_pattern_id, {})
        nonlinear = nonlinear_by_source.get(source_pattern_id, {})
        score = round(
            _float(pattern.get("pattern_scan_score"), 0.0) * 0.35
            + _float(linear.get("linear_score"), 0.0) * 0.25
            + _float(_safe_dict(nonlinear.get("nonlinear_tests")).get("nonlinear_score"), 0.0) * 0.20
            + _score_bool(edge.get("accepted_as_validated_edge") is True) * 0.20,
            4,
        )
        blockers = []
        if edge and edge.get("accepted_as_validated_edge") is not True:
            blockers.extend(edge.get("failed_criteria", [])[:6])
        if not linear:
            blockers.append("linear_review_missing")
        if not nonlinear:
            blockers.append("nonlinear_review_missing")
        record = {
            "schema_version": SCHEMA_VERSION,
            "artifact_type": "qsase_full_universe_pattern_v2_record",
            "pattern_v2_id": _hash_id([SCHEMA_VERSION, source_pattern_id, "pattern-v2"], "qsase-pattern-v2"),
            "generated_at": generated_at,
            "source_pattern_id": source_pattern_id,
            "rank": index + 1,
            "pattern_state": "validated_for_foundry" if edge.get("accepted_as_validated_edge") is True else "research_pattern_needs_evidence",
            "relationship_summary": pattern.get("relationship_summary"),
            "source_keys": _safe_list(pattern.get("source_keys")),
            "market_symbols": _safe_list(pattern.get("market_symbols")),
            "time_windows": _safe_list(pattern.get("time_windows")),
            "strategy_family": _strategy_family(pattern),
            "linear_state": _safe_dict(linear.get("decision")).get("linear_status"),
            "nonlinear_state": _safe_dict(nonlinear.get("decision")).get("nonlinear_status"),
            "edge_graduation_state": edge.get("graduation_state", "not_evaluated"),
            "pattern_rank_score": score,
            "blockers": blockers,
            "next_action": "send_to_strategy_foundry_v2" if edge.get("accepted_as_validated_edge") is True else "continue evidence repair and shadow research",
            "authority": AUTHORITY_FLAGS,
            "execution_allowed": False,
            "paper_order_created": False,
            "broker_write_allowed": False,
            "proof_credit_allowed": False,
            "live_capital_enabled": False,
        }
        records.append(record)
        if blockers:
            rejections.append({
                **record,
                "artifact_type": "qsase_full_universe_pattern_v2_rejection",
                "rejection_id": _hash_id([record["pattern_v2_id"], "rejected"], "qsase-pattern-v2-reject"),
                "rejection_reasons": blockers,
            })
    records.sort(key=lambda row: row.get("pattern_rank_score", 0), reverse=True)
    for rank, record in enumerate(records, start=1):
        record["rank"] = rank
    payload = {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "qsase_full_universe_pattern_search_v2",
        "generated_at": generated_at,
        "status": "qsase_pattern_search_v2_ready" if records else "qsase_pattern_search_v2_missing_inputs",
        "public_safe": True,
        "read_only": True,
        "command_disabled": True,
        "paper_only": True,
        "research_only": True,
        "proposal_first": True,
        "authority": universal_authority_flags(),
        "authority_flags": AUTHORITY_FLAGS,
        "pattern_record_count": len(records),
        "validated_for_foundry_count": sum(1 for row in records if row["pattern_state"] == "validated_for_foundry"),
        "research_pattern_count": sum(1 for row in records if row["pattern_state"] != "validated_for_foundry"),
        "rejection_count": len(rejections),
        "top_pattern": records[0] if records else {},
        "records_path": _artifact_ref(PATTERN_SEARCH_V2_RECORDS_ARTIFACT),
        "rejections_path": _artifact_ref(PATTERN_SEARCH_V2_REJECTIONS_ARTIFACT),
        "paper_order_created_count": 0,
        "broker_write_count": 0,
        "proof_credit_allowed": False,
        "live_capital_enabled": False,
    }
    return payload, records, rejections


def _paper_proxy(instrument: str) -> dict[str, Any]:
    if instrument in {"CL=F", "USO", "BNO"}:
        return {"primary_proxy": "USO", "alternate_proxies": ["XLE"], "proxy_set": ["USO", "XLE"]}
    if instrument in {"SI=F", "SLV", "SIL"}:
        return {"primary_proxy": "SLV", "alternate_proxies": ["SIL"], "proxy_set": ["SLV", "SIL"]}
    if instrument in {"SMH", "SOXX", "NVDA"}:
        return {"primary_proxy": "SMH", "alternate_proxies": ["SOXX"], "proxy_set": ["SMH", "SOXX"]}
    if instrument in {"ITA", "PPA", "XAR", "LMT"}:
        return {"primary_proxy": "ITA", "alternate_proxies": ["PPA", "XAR"], "proxy_set": ["ITA", "PPA", "XAR"]}
    return {"primary_proxy": instrument, "alternate_proxies": [], "proxy_set": [instrument]}


def build_strategy_foundry_v2(edge_records: list[dict[str, Any]], pattern_records: list[dict[str, Any]], generated_at: str) -> tuple[dict[str, Any], list[dict[str, Any]], list[dict[str, Any]]]:
    pattern_by_source = _by_key(pattern_records, "source_pattern_id")
    hypotheses: list[dict[str, Any]] = []
    rejected: list[dict[str, Any]] = []
    for edge in edge_records:
        source_pattern_id = str(edge.get("source_pattern_id") or "")
        pattern = pattern_by_source.get(source_pattern_id, {})
        if edge.get("accepted_as_validated_edge") is not True:
            rejected.append({
                "schema_version": SCHEMA_VERSION,
                "artifact_type": "qsase_rejected_strategy_hypothesis_v2",
                "rejected_hypothesis_id": _hash_id([SCHEMA_VERSION, source_pattern_id, "foundry-v2-reject"], "qsase-foundry-reject-v2"),
                "generated_at": generated_at,
                "source_pattern_id": source_pattern_id,
                "strategy_family": edge.get("strategy_family"),
                "rejection_reasons": edge.get("failed_criteria", ["validated_edge_missing"]),
                "retest_condition": "validated edge graduation must pass first",
                "authority": AUTHORITY_FLAGS,
                "execution_allowed": False,
                "paper_order_created": False,
                "broker_write_allowed": False,
                "proof_credit_allowed": False,
                "live_capital_enabled": False,
            })
            continue
        instrument = str(edge.get("instrument") or "unknown")
        proxy = _paper_proxy(instrument)
        hypotheses.append({
            "schema_version": SCHEMA_VERSION,
            "artifact_type": "qsase_strategy_hypothesis_v2",
            "strategy_hypothesis_id": _hash_id([SCHEMA_VERSION, source_pattern_id, "strategy-v2"], "qsase-strategy-v2"),
            "generated_at": generated_at,
            "status": "strategy_hypothesis_v2_ready_for_akber",
            "source_pattern_id": source_pattern_id,
            "validated_edge_id": edge.get("validated_edge_id"),
            "strategy_family": edge.get("strategy_family") or pattern.get("strategy_family"),
            "instrument": instrument,
            "paperable_execution_expression": proxy["primary_proxy"],
            "thesis": f"{edge.get('strategy_family')} has a validated source-price edge in {instrument}.",
            "source_price_lineage": edge.get("source_price_lineage", {}),
            "research_goal_lineage": {
                "origin": "validated_edge_graduation_v2",
                "source_pattern_id": source_pattern_id,
                "validated_edge_id": edge.get("validated_edge_id"),
            },
            "invalidation": {
                "summary": "Invalidate if source quorum fails, market confirmation reverses, Akber vetoes, or PaperOps guard blocks route.",
                "hard_invalidators": ["source_quorum_missing", "akber_veto", "risk_budget_block", "paperops_guard_block"],
            },
            "risk_concept": {
                "risk_budget_required": True,
                "sizing_authority": "downstream_risk_agent_only",
                "max_loss_concept": "no sizing created in foundry",
            },
            "paperability": {
                "paper_review_candidate": False,
                "paperable_proxy_expression": proxy,
                "paper_order_allowed": False,
            },
            "authority": AUTHORITY_FLAGS,
            "execution_allowed": False,
            "risk_approval_created": False,
            "paper_order_created": False,
            "broker_write_allowed": False,
            "proof_credit_allowed": False,
            "live_capital_enabled": False,
        })
    payload = {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "qsase_strategy_foundry_v2",
        "generated_at": generated_at,
        "status": "qsase_strategy_foundry_v2_ready" if hypotheses else "qsase_strategy_foundry_v2_waiting_for_validated_edges",
        "public_safe": True,
        "read_only": True,
        "command_disabled": True,
        "paper_only": True,
        "research_only": True,
        "proposal_first": True,
        "authority": universal_authority_flags(),
        "authority_flags": AUTHORITY_FLAGS,
        "validated_edge_input_count": len(edge_records),
        "strategy_hypothesis_count": len(hypotheses),
        "rejected_hypothesis_count": len(rejected),
        "hypotheses_path": _artifact_ref(STRATEGY_HYPOTHESES_V2_ARTIFACT),
        "rejected_hypotheses_path": _artifact_ref(REJECTED_STRATEGY_HYPOTHESES_V2_ARTIFACT),
        "paper_order_created_count": 0,
        "broker_write_count": 0,
        "proof_credit_allowed": False,
        "live_capital_enabled": False,
    }
    return payload, hypotheses, rejected


def _packet_by_hypothesis(packets: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    return _by_key(packets, "strategy_hypothesis_id")


def build_akber_v2(context: dict[str, Any], hypotheses_v2: list[dict[str, Any]], generated_at: str) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    market_packets = context["market_packets"]
    packet_lookup = _packet_by_hypothesis(market_packets)
    source_rows = hypotheses_v2 if hypotheses_v2 else context["v1_strategy_hypotheses"]
    records: list[dict[str, Any]] = []
    for row in source_rows:
        hypothesis_id = str(row.get("strategy_hypothesis_id") or "")
        packet = packet_lookup.get(hypothesis_id, {})
        if not packet and market_packets:
            packet = market_packets[min(len(records), len(market_packets) - 1)]
        missing = _safe_list(packet.get("missing_inputs"))
        is_v2 = row.get("artifact_type") == "qsase_strategy_hypothesis_v2"
        passed = is_v2 and packet.get("akber_input_complete") is True
        decision = "pass" if passed else "hold_missing_context"
        records.append({
            "schema_version": SCHEMA_VERSION,
            "artifact_type": "qsase_akber_filter_v2_record",
            "akber_filter_v2_id": _hash_id([SCHEMA_VERSION, hypothesis_id, packet.get("market_confirmation_packet_id"), "akber-v2"], "qsase-akber-v2"),
            "generated_at": generated_at,
            "strategy_hypothesis_id": hypothesis_id,
            "source_hypothesis_version": "v2" if is_v2 else "v1_probationary",
            "strategy_family": _strategy_family(row),
            "instrument": _instrument(row),
            "stage_state": {
                "context": "present" if row else "missing",
                "catalyst": "present" if row.get("source_recipe") or row.get("source_price_lineage") else "missing",
                "confirmation": "present" if packet.get("akber_input_complete") else "missing:" + ",".join(missing or ["market_confirmation"]),
                "risk": "downstream_risk_agent_only" if passed else "not_reached",
                "execution": "not_execution_authority",
                "postmortem_learning": "proposal_only",
            },
            "decision": {
                "filter_decision": decision,
                "candidate_for_router": passed,
                "candidate_for_paper_review": False,
                "reason": "Akber V2 practical inputs complete." if passed else "Akber V2 needs practical confirmation inputs.",
                "next_required_evidence": missing,
            },
            "scores": {
                "akber_filter_score": _float(packet.get("completeness_score"), 0.0),
                "input_completeness_score": _float(packet.get("completeness_score"), 0.0),
            },
            "market_confirmation_packet_ref": _artifact_ref(MARKET_CONFIRMATION_PACKETS_ARTIFACT),
            "authority": AUTHORITY_FLAGS,
            "execution_allowed": False,
            "risk_approval_created": False,
            "paper_order_created": False,
            "broker_write_allowed": False,
            "proof_credit_allowed": False,
            "live_capital_enabled": False,
        })
    pass_count = sum(1 for row in records if row["decision"]["filter_decision"] == "pass")
    hold_count = sum(1 for row in records if row["decision"]["filter_decision"].startswith("hold"))
    payload = {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "qsase_akber_filter_v2",
        "generated_at": generated_at,
        "status": "qsase_akber_filter_v2_ready" if pass_count else "qsase_akber_filter_v2_ready_with_holds",
        "public_safe": True,
        "read_only": True,
        "command_disabled": True,
        "paper_only": True,
        "research_only": True,
        "proposal_first": True,
        "authority": universal_authority_flags(),
        "authority_flags": AUTHORITY_FLAGS,
        "stage_record_count": len(records),
        "pass_count": pass_count,
        "hold_count": hold_count,
        "missing_context_count": sum(len(_safe_list(row["decision"].get("next_required_evidence"))) for row in records),
        "records_path": _artifact_ref(AKBER_STAGE_RECORDS_V2_ARTIFACT),
        "paper_order_created_count": 0,
        "broker_write_count": 0,
        "proof_credit_allowed": False,
        "live_capital_enabled": False,
    }
    return payload, records


def build_shadow_v2(context: dict[str, Any], hypotheses_v2: list[dict[str, Any]], akber_records: list[dict[str, Any]], generated_at: str) -> tuple[dict[str, Any], list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    source_rows = hypotheses_v2 if hypotheses_v2 else akber_records
    akber_by_hypothesis = _by_key(akber_records, "strategy_hypothesis_id")
    results: list[dict[str, Any]] = []
    counterfactuals: list[dict[str, Any]] = []
    rejections: list[dict[str, Any]] = []
    variants = ["trade_now", "wait_for_confirmation", "veto", "no_order"]
    for row in source_rows:
        hypothesis_id = str(row.get("strategy_hypothesis_id") or "")
        akber = akber_by_hypothesis.get(hypothesis_id, row)
        akber_passed = _safe_dict(akber.get("decision")).get("filter_decision") == "pass"
        support = akber_passed and bool(hypotheses_v2)
        result = {
            "schema_version": SCHEMA_VERSION,
            "artifact_type": "qsase_shadow_result_v2",
            "shadow_result_v2_id": _hash_id([SCHEMA_VERSION, hypothesis_id, "shadow-v2"], "qsase-shadow-v2"),
            "generated_at": generated_at,
            "strategy_hypothesis_id": hypothesis_id,
            "replay_state": "candidate_for_router_review" if support else "hold_for_more_shadow_data",
            "evidence_class": "forward_shadow_watch" if support else "blocked_route_shadow_research",
            "shadow_supports_router": support,
            "metrics": {
                "expectancy": 0.0,
                "hit_rate": 0.0,
                "max_drawdown": 0.0,
                "missed_opportunity_score": 0.0,
                "false_positive_score": 1.0 if not support else 0.4,
            },
            "reason": "Shadow V2 can support router only after validated-edge and Akber V2 pass." if not support else "Shadow V2 supports router review.",
            "authority": AUTHORITY_FLAGS,
            "execution_allowed": False,
            "paper_order_created": False,
            "broker_write_allowed": False,
            "proof_credit_allowed": False,
            "live_capital_enabled": False,
        }
        results.append(result)
        for variant in variants:
            counterfactuals.append({
                "schema_version": SCHEMA_VERSION,
                "artifact_type": "qsase_shadow_counterfactual_v2",
                "counterfactual_id": _hash_id([result["shadow_result_v2_id"], variant], "qsase-shadow-cf-v2"),
                "generated_at": generated_at,
                "strategy_hypothesis_id": hypothesis_id,
                "variant": variant,
                "outcome_class": "not_executed_research_only",
                "paper_order_created": False,
                "proof_credit_allowed": False,
                "live_capital_enabled": False,
            })
        if not support:
            rejections.append({
                **result,
                "artifact_type": "qsase_shadow_rejection_v2",
                "shadow_rejection_id": _hash_id([result["shadow_result_v2_id"], "reject"], "qsase-shadow-reject-v2"),
                "rejection_reasons": ["validated_edge_or_akber_v2_pass_missing"],
            })
    support_count = sum(1 for row in results if row["shadow_supports_router"])
    payload = {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "qsase_shadow_simulator_v2",
        "generated_at": generated_at,
        "status": "qsase_shadow_simulator_v2_ready" if support_count else "qsase_shadow_simulator_v2_ready_with_holds",
        "public_safe": True,
        "read_only": True,
        "command_disabled": True,
        "paper_only": True,
        "research_only": True,
        "proposal_first": True,
        "authority": universal_authority_flags(),
        "authority_flags": AUTHORITY_FLAGS,
        "shadow_result_count": len(results),
        "counterfactual_count": len(counterfactuals),
        "shadow_support_count": support_count,
        "shadow_rejection_count": len(rejections),
        "results_path": _artifact_ref(SHADOW_RESULTS_V2_ARTIFACT),
        "counterfactuals_path": _artifact_ref(SHADOW_COUNTERFACTUALS_V2_ARTIFACT),
        "paper_order_created_count": 0,
        "broker_write_count": 0,
        "proof_credit_allowed": False,
        "live_capital_enabled": False,
    }
    return payload, results, counterfactuals, rejections


def build_router_and_handoff_v2(
    context: dict[str, Any],
    hypotheses_v2: list[dict[str, Any]],
    akber_records: list[dict[str, Any]],
    shadow_results: list[dict[str, Any]],
    generated_at: str,
) -> tuple[dict[str, Any], list[dict[str, Any]], dict[str, Any], dict[str, Any], list[dict[str, Any]], list[dict[str, Any]]]:
    shadow_by_hypothesis = _by_key(shadow_results, "strategy_hypothesis_id")
    source_rows = hypotheses_v2 if hypotheses_v2 else akber_records
    decisions: list[dict[str, Any]] = []
    handoffs: list[dict[str, Any]] = []
    rejected_handoffs: list[dict[str, Any]] = []
    for row in source_rows:
        hypothesis_id = str(row.get("strategy_hypothesis_id") or "")
        akber = next((item for item in akber_records if item.get("strategy_hypothesis_id") == hypothesis_id), {})
        shadow = shadow_by_hypothesis.get(hypothesis_id, {})
        hard_vetoes: list[str] = []
        soft_blockers: list[str] = []
        if not hypotheses_v2:
            soft_blockers.append("validated_edge_graduation_missing")
        if _safe_dict(akber.get("decision")).get("filter_decision") != "pass":
            soft_blockers.append("akber_v2_not_passed")
        if shadow.get("shadow_supports_router") is not True:
            soft_blockers.append("shadow_v2_not_supporting_router")
        if hard_vetoes:
            router_output = "blocked_safety_boundary"
        elif soft_blockers:
            router_output = "hold_missing_evidence"
        else:
            router_output = "paper_review_candidate"
        decision = {
            "schema_version": SCHEMA_VERSION,
            "artifact_type": "qsase_strategy_router_decision_v2",
            "router_decision_v2_id": _hash_id([SCHEMA_VERSION, hypothesis_id, "router-v2"], "qsase-router-v2"),
            "generated_at": generated_at,
            "strategy_hypothesis_id": hypothesis_id,
            "strategy_family": row.get("strategy_family") or akber.get("strategy_family"),
            "instrument": row.get("instrument") or akber.get("instrument"),
            "scores": {
                "akber_score": _float(_safe_dict(akber.get("scores")).get("akber_filter_score"), 0.0),
                "shadow_support": 1.0 if shadow.get("shadow_supports_router") is True else 0.0,
                "route_readiness": 1.0 if router_output == "paper_review_candidate" else 0.0,
            },
            "gates": {
                "validated_edge": "pass" if hypotheses_v2 else "hold",
                "akber_v2": _safe_dict(akber.get("decision")).get("filter_decision", "missing"),
                "shadow_v2": shadow.get("replay_state", "missing"),
                "paperops_guarded_route": "required_downstream",
            },
            "hard_vetoes": hard_vetoes,
            "soft_blockers": soft_blockers,
            "decision": {
                "router_output": router_output,
                "paper_review_candidate": router_output == "paper_review_candidate",
                "why_not_trading_now": "ready_for_paperops_handoff" if router_output == "paper_review_candidate" else ", ".join(soft_blockers or hard_vetoes),
                "next_required_action": "build_paperops_handoff" if router_output == "paper_review_candidate" else "repair_router_blockers",
            },
            "paper_review_candidate_handoff": None,
            "authority": AUTHORITY_FLAGS,
            "execution_allowed": False,
            "paper_order_created": False,
            "broker_write_allowed": False,
            "proof_credit_allowed": False,
            "live_capital_enabled": False,
        }
        decisions.append(decision)
        if router_output == "paper_review_candidate":
            handoffs.append({
                "schema_version": SCHEMA_VERSION,
                "artifact_type": "qsase_paperops_handoff_v2_record",
                "paperops_handoff_v2_id": _hash_id([decision["router_decision_v2_id"], "handoff"], "qsase-paperops-handoff-v2"),
                "generated_at": generated_at,
                "router_decision_v2_id": decision["router_decision_v2_id"],
                "strategy_hypothesis_id": hypothesis_id,
                "handoff_state": "upstream_paperops_review_record_only",
                "guarded_alpaca_paper_route_required": True,
                "paper_order_created": False,
                "broker_write_allowed": False,
                "proof_credit_allowed": False,
                "live_capital_enabled": False,
                "authority": AUTHORITY_FLAGS,
            })
        else:
            rejected_handoffs.append({
                "schema_version": SCHEMA_VERSION,
                "artifact_type": "qsase_paperops_rejected_handoff_v2",
                "rejected_handoff_v2_id": _hash_id([decision["router_decision_v2_id"], "rejected-handoff"], "qsase-paperops-reject-v2"),
                "generated_at": generated_at,
                "router_decision_v2_id": decision["router_decision_v2_id"],
                "strategy_hypothesis_id": hypothesis_id,
                "rejection_reasons": soft_blockers or hard_vetoes,
                "paper_order_created": False,
                "broker_write_allowed": False,
                "live_capital_enabled": False,
            })
    paper_candidate_count = sum(1 for row in decisions if row["decision"]["router_output"] == "paper_review_candidate")
    scoreboard = {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "qsase_strategy_router_scoreboard_v2",
        "generated_at": generated_at,
        "decision_count": len(decisions),
        "paper_review_candidate_count": paper_candidate_count,
        "hold_count": sum(1 for row in decisions if row["decision"]["router_output"].startswith("hold")),
        "blocked_safety_boundary_count": sum(1 for row in decisions if row["decision"]["router_output"] == "blocked_safety_boundary"),
        "public_safe": True,
        "read_only": True,
        "command_disabled": True,
    }
    why_not = {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "qsase_why_not_trading_now_v2",
        "generated_at": generated_at,
        "status": "paper_review_candidate_available" if paper_candidate_count else "no_paper_review_candidate",
        "reason": "paper_review_candidate_available" if paper_candidate_count else "validated edge, Akber V2, or shadow V2 support is missing",
        "top_blockers": dict(Counter(blocker for row in decisions for blocker in row.get("soft_blockers", [])).most_common(8)),
        "public_safe": True,
        "read_only": True,
        "command_disabled": True,
        "paper_order_created": False,
        "broker_write_allowed": False,
        "live_capital_enabled": False,
    }
    router_payload = {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "qsase_strategy_router_v2",
        "generated_at": generated_at,
        "status": "qsase_strategy_router_v2_ready_with_paper_candidates" if paper_candidate_count else "qsase_strategy_router_v2_ready_no_paper_candidate",
        "public_safe": True,
        "read_only": True,
        "command_disabled": True,
        "paper_only": True,
        "research_only": True,
        "proposal_first": True,
        "authority": universal_authority_flags(),
        "authority_flags": AUTHORITY_FLAGS,
        "decision_count": len(decisions),
        "paper_review_candidate_count": paper_candidate_count,
        "handoff_count": len(handoffs),
        "rejected_handoff_count": len(rejected_handoffs),
        "decisions_path": _artifact_ref(ROUTER_DECISIONS_V2_ARTIFACT),
        "paper_order_created_count": 0,
        "broker_write_count": 0,
        "proof_credit_allowed": False,
        "live_capital_enabled": False,
    }
    handoff_payload = {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "qsase_paperops_handoff_v2",
        "generated_at": generated_at,
        "status": "qsase_paperops_handoff_v2_ready" if handoffs else "qsase_paperops_handoff_v2_no_handoffs",
        "public_safe": True,
        "read_only": True,
        "command_disabled": True,
        "paper_only": True,
        "authority": universal_authority_flags(),
        "authority_flags": AUTHORITY_FLAGS,
        "handoff_count": len(handoffs),
        "rejected_handoff_count": len(rejected_handoffs),
        "records_path": _artifact_ref(PAPEROPS_HANDOFF_RECORDS_V2_ARTIFACT),
        "rejected_handoffs_path": _artifact_ref(PAPEROPS_REJECTED_HANDOFFS_V2_ARTIFACT),
        "paper_order_created_count": 0,
        "broker_write_count": 0,
        "proof_credit_allowed": False,
        "live_capital_enabled": False,
    }
    return router_payload, decisions, scoreboard, why_not, handoffs, rejected_handoffs, handoff_payload


def _dashboard_summary(payload: dict[str, Any], label: str) -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": f"{label}_dashboard_summary",
        "generated_at": payload.get("generated_at"),
        "status": payload.get("status"),
        "public_safe": True,
        "read_only": True,
        "command_disabled": True,
        "paper_order_created_count": payload.get("paper_order_created_count", 0),
        "broker_write_count": payload.get("broker_write_count", 0),
        "proof_credit_allowed": False,
        "live_capital_enabled": False,
        "summary_counts": {
            key: value
            for key, value in payload.items()
            if key.endswith("_count") and isinstance(value, int)
        },
    }


def build_phase5_to10_completion(settings: Settings | None = None) -> dict[str, Any]:
    context = _load_context(settings)
    generated_at = _iso(_now())
    edge_payload, edge_records, edge_rejections = build_validated_edge_graduation(context, generated_at)
    pattern_payload, pattern_records, pattern_rejections = build_pattern_search_v2(context, edge_records, generated_at)
    foundry_payload, hypotheses_v2, rejected_hypotheses_v2 = build_strategy_foundry_v2(edge_records, pattern_records, generated_at)
    akber_payload, akber_records = build_akber_v2(context, hypotheses_v2, generated_at)
    shadow_payload, shadow_results, shadow_counterfactuals, shadow_rejections = build_shadow_v2(
        context,
        hypotheses_v2,
        akber_records,
        generated_at,
    )
    (
        router_payload,
        router_decisions,
        router_scoreboard,
        why_not,
        handoffs,
        rejected_handoffs,
        handoff_payload,
    ) = build_router_and_handoff_v2(context, hypotheses_v2, akber_records, shadow_results, generated_at)
    return {
        "generated_at": generated_at,
        "edge": (edge_payload, edge_records, edge_rejections),
        "pattern": (pattern_payload, pattern_records, pattern_rejections),
        "foundry": (foundry_payload, hypotheses_v2, rejected_hypotheses_v2),
        "akber": (akber_payload, akber_records),
        "shadow": (shadow_payload, shadow_results, shadow_counterfactuals, shadow_rejections),
        "router": (router_payload, router_decisions, router_scoreboard, why_not, handoffs, rejected_handoffs, handoff_payload),
    }


def validate_payload(payload: dict[str, Any], expected_type: str) -> list[str]:
    errors: list[str] = []
    if payload.get("schema_version") != SCHEMA_VERSION:
        errors.append("schema_version_mismatch")
    if payload.get("artifact_type") != expected_type:
        errors.append("artifact_type_mismatch")
    if payload.get("public_safe") is not True:
        errors.append("public_safe_must_be_true")
    if payload.get("read_only") is not True:
        errors.append("read_only_must_be_true")
    for field in FALSE_AUTHORITY_FIELDS:
        if payload.get(field) is True:
            errors.append(f"{field}_must_not_be_true")
    if payload.get("paper_order_created_count", 0) not in (0, None):
        errors.append("paper_order_created_count_must_be_zero")
    if payload.get("broker_write_count", 0) not in (0, None):
        errors.append("broker_write_count_must_be_zero")
    if payload.get("proof_credit_allowed") is not False:
        errors.append("proof_credit_allowed_must_be_false")
    if payload.get("live_capital_enabled") is not False:
        errors.append("live_capital_enabled_must_be_false")
    return errors


def _write_phase_outputs(bundle: dict[str, Any], settings: Settings | None = None) -> dict[str, str]:
    runtime = _runtime_dir(settings)
    written: dict[str, str] = {}

    edge_payload, edge_records, edge_rejections = bundle["edge"]
    pattern_payload, pattern_records, pattern_rejections = bundle["pattern"]
    foundry_payload, hypotheses_v2, rejected_hypotheses_v2 = bundle["foundry"]
    akber_payload, akber_records = bundle["akber"]
    shadow_payload, shadow_results, shadow_counterfactuals, shadow_rejections = bundle["shadow"]
    (
        router_payload,
        router_decisions,
        router_scoreboard,
        why_not,
        handoffs,
        rejected_handoffs,
        handoff_payload,
    ) = bundle["router"]

    json_outputs = {
        VALIDATED_EDGE_ARTIFACT: edge_payload,
        VALIDATED_EDGE_DASHBOARD_ARTIFACT: _dashboard_summary(edge_payload, "qsase_validated_edge_graduation"),
        PATTERN_SEARCH_V2_ARTIFACT: pattern_payload,
        PATTERN_SEARCH_V2_DASHBOARD_ARTIFACT: _dashboard_summary(pattern_payload, "qsase_full_universe_pattern_search_v2"),
        STRATEGY_FOUNDRY_V2_ARTIFACT: foundry_payload,
        STRATEGY_FOUNDRY_V2_DASHBOARD_ARTIFACT: _dashboard_summary(foundry_payload, "qsase_strategy_foundry_v2"),
        AKBER_V2_ARTIFACT: akber_payload,
        AKBER_V2_DASHBOARD_ARTIFACT: _dashboard_summary(akber_payload, "qsase_akber_filter_v2"),
        SHADOW_V2_ARTIFACT: shadow_payload,
        SHADOW_V2_DASHBOARD_ARTIFACT: _dashboard_summary(shadow_payload, "qsase_shadow_simulator_v2"),
        ROUTER_V2_ARTIFACT: router_payload,
        ROUTER_SCOREBOARD_V2_ARTIFACT: router_scoreboard,
        WHY_NOT_V2_ARTIFACT: why_not,
        PAPEROPS_HANDOFF_V2_ARTIFACT: handoff_payload,
        ROUTER_V2_DASHBOARD_ARTIFACT: _dashboard_summary(router_payload, "qsase_strategy_router_v2"),
    }
    jsonl_outputs = {
        VALIDATED_EDGE_RECORDS_ARTIFACT: edge_records,
        EDGE_REJECTIONS_ARTIFACT: edge_rejections,
        PATTERN_SEARCH_V2_RECORDS_ARTIFACT: pattern_records,
        PATTERN_SEARCH_V2_REJECTIONS_ARTIFACT: pattern_rejections,
        STRATEGY_HYPOTHESES_V2_ARTIFACT: hypotheses_v2,
        REJECTED_STRATEGY_HYPOTHESES_V2_ARTIFACT: rejected_hypotheses_v2,
        AKBER_STAGE_RECORDS_V2_ARTIFACT: akber_records,
        SHADOW_RESULTS_V2_ARTIFACT: shadow_results,
        SHADOW_COUNTERFACTUALS_V2_ARTIFACT: shadow_counterfactuals,
        SHADOW_REJECTIONS_V2_ARTIFACT: shadow_rejections,
        ROUTER_DECISIONS_V2_ARTIFACT: router_decisions,
        PAPEROPS_HANDOFF_RECORDS_V2_ARTIFACT: handoffs,
        PAPEROPS_REJECTED_HANDOFFS_V2_ARTIFACT: rejected_handoffs,
    }
    for filename, payload in json_outputs.items():
        path = runtime / filename
        _write_json(path, payload)
        written[filename] = str(path)
    for filename, records in jsonl_outputs.items():
        path = runtime / filename
        _write_jsonl(path, records)
        written[filename] = str(path)
    event = {
        "schema_version": SCHEMA_VERSION,
        "generated_at": bundle["generated_at"],
        "event": "qsase_phase5_to10_completion_written",
        "validated_edge_count": edge_payload.get("validated_edge_count"),
        "strategy_hypothesis_count": foundry_payload.get("strategy_hypothesis_count"),
        "akber_pass_count": akber_payload.get("pass_count"),
        "shadow_support_count": shadow_payload.get("shadow_support_count"),
        "router_paper_review_candidate_count": router_payload.get("paper_review_candidate_count"),
        "paperops_handoff_count": handoff_payload.get("handoff_count"),
    }
    _append_jsonl(runtime / HISTORY_ARTIFACT, event)
    _append_jsonl(runtime / EVENTS_ARTIFACT, event)
    written[HISTORY_ARTIFACT] = str(runtime / HISTORY_ARTIFACT)
    written[EVENTS_ARTIFACT] = str(runtime / EVENTS_ARTIFACT)
    phase_status_path = runtime / PHASE_STATUS_ARTIFACT
    _update_phase_status(phase_status_path, bundle)
    written[PHASE_STATUS_ARTIFACT] = str(phase_status_path)
    return written


def _phase_record(
    *,
    name: str,
    status: str,
    artifact_path: str,
    counts: dict[str, Any],
) -> dict[str, Any]:
    return {
        "name": name,
        "status": status,
        "artifact_path": artifact_path,
        "paper_only": True,
        "public_safe": True,
        "read_only": True,
        "research_only": True,
        "proposal_first": True,
        "no_trade_candidates_created": True,
        "no_paper_orders_created": True,
        "no_broker_writes": True,
        "no_proof_credit_granted": True,
        "live_capital_enabled": False,
        **counts,
    }


def _update_phase_status(path: Path, bundle: dict[str, Any]) -> None:
    current = _read_json(path)
    phases = _safe_dict(current.get("phases"))
    edge_payload = bundle["edge"][0]
    pattern_payload = bundle["pattern"][0]
    foundry_payload = bundle["foundry"][0]
    akber_payload = bundle["akber"][0]
    shadow_payload = bundle["shadow"][0]
    router_payload = bundle["router"][0]
    handoff_payload = bundle["router"][6]

    phases.update(
        {
            "perfect_operation_phase_5_validated_edge_graduation_v2": _phase_record(
                name="Perfect Operation Phase 5: Validated Edge Graduation V2",
                status=str(edge_payload.get("status")),
                artifact_path=_artifact_ref(VALIDATED_EDGE_ARTIFACT),
                counts={
                    "input_linear_result_count": edge_payload.get("input_linear_result_count"),
                    "graduation_record_count": edge_payload.get("graduation_record_count"),
                    "validated_edge_count": edge_payload.get("validated_edge_count"),
                    "edge_rejection_count": edge_payload.get("edge_rejection_count"),
                },
            ),
            "perfect_operation_phase_6_pattern_search_v2": _phase_record(
                name="Perfect Operation Phase 6: Full-Universe Pattern Search V2",
                status=str(pattern_payload.get("status")),
                artifact_path=_artifact_ref(PATTERN_SEARCH_V2_ARTIFACT),
                counts={
                    "pattern_record_count": pattern_payload.get("pattern_record_count"),
                    "validated_for_foundry_count": pattern_payload.get("validated_for_foundry_count"),
                    "research_pattern_count": pattern_payload.get("research_pattern_count"),
                    "rejection_count": pattern_payload.get("rejection_count"),
                },
            ),
            "perfect_operation_phase_7_strategy_foundry_v2": _phase_record(
                name="Perfect Operation Phase 7: Strategy Foundry V2",
                status=str(foundry_payload.get("status")),
                artifact_path=_artifact_ref(STRATEGY_FOUNDRY_V2_ARTIFACT),
                counts={
                    "validated_edge_input_count": foundry_payload.get("validated_edge_input_count"),
                    "strategy_hypothesis_count": foundry_payload.get("strategy_hypothesis_count"),
                    "rejected_hypothesis_count": foundry_payload.get("rejected_hypothesis_count"),
                },
            ),
            "perfect_operation_phase_8_akber_filter_v2": _phase_record(
                name="Perfect Operation Phase 8: Akber Filter V2",
                status=str(akber_payload.get("status")),
                artifact_path=_artifact_ref(AKBER_V2_ARTIFACT),
                counts={
                    "stage_record_count": akber_payload.get("stage_record_count"),
                    "pass_count": akber_payload.get("pass_count"),
                    "hold_count": akber_payload.get("hold_count"),
                    "missing_context_count": akber_payload.get("missing_context_count"),
                },
            ),
            "perfect_operation_phase_9_shadow_simulator_v2": _phase_record(
                name="Perfect Operation Phase 9: Shadow Simulator V2",
                status=str(shadow_payload.get("status")),
                artifact_path=_artifact_ref(SHADOW_V2_ARTIFACT),
                counts={
                    "shadow_result_count": shadow_payload.get("shadow_result_count"),
                    "counterfactual_count": shadow_payload.get("counterfactual_count"),
                    "shadow_support_count": shadow_payload.get("shadow_support_count"),
                    "shadow_rejection_count": shadow_payload.get("shadow_rejection_count"),
                },
            ),
            "perfect_operation_phase_10_router_paperops_handoff_v2": _phase_record(
                name="Perfect Operation Phase 10: Router V2 And PaperOps Handoff V2",
                status=str(router_payload.get("status")),
                artifact_path=_artifact_ref(ROUTER_V2_ARTIFACT),
                counts={
                    "decision_count": router_payload.get("decision_count"),
                    "paper_review_candidate_count": router_payload.get("paper_review_candidate_count"),
                    "router_handoff_count": router_payload.get("handoff_count"),
                    "paperops_handoff_status": handoff_payload.get("status"),
                    "paperops_handoff_count": handoff_payload.get("handoff_count"),
                    "rejected_handoff_count": handoff_payload.get("rejected_handoff_count"),
                },
            ),
        }
    )
    payload = {
        **current,
        "schema_version": current.get("schema_version", 1),
        "generated_at": bundle["generated_at"],
        "active_phase": "perfect_operation_phase_10_router_paperops_handoff_v2",
        "phases": phases,
        "safety": {
            **_safe_dict(current.get("safety")),
            "paper_only": True,
            "live_capital_enabled": False,
            "paper_order_created_count": 0,
            "broker_write_count": 0,
            "proof_credit_allowed": False,
            "phase5_to10_v2_outputs_are_review_only": True,
        },
    }
    _write_json(path, payload)


def build_and_write_phase5_to10_completion(settings: Settings | None = None) -> tuple[dict[str, Any], dict[str, str], list[str]]:
    bundle = build_phase5_to10_completion(settings)
    errors: list[str] = []
    expected = {
        "edge": "qsase_validated_edge_graduation",
        "pattern": "qsase_full_universe_pattern_search_v2",
        "foundry": "qsase_strategy_foundry_v2",
        "akber": "qsase_akber_filter_v2",
        "shadow": "qsase_shadow_simulator_v2",
    }
    for key, expected_type in expected.items():
        payload = bundle[key][0]
        errors.extend(f"{key}:{error}" for error in validate_payload(payload, expected_type))
    router_payload = bundle["router"][0]
    handoff_payload = bundle["router"][6]
    errors.extend(f"router:{error}" for error in validate_payload(router_payload, "qsase_strategy_router_v2"))
    errors.extend(f"handoff:{error}" for error in validate_payload(handoff_payload, "qsase_paperops_handoff_v2"))
    written = _write_phase_outputs(bundle, settings)
    summary = {
        "generated_at": bundle["generated_at"],
        "edge": bundle["edge"][0],
        "pattern": bundle["pattern"][0],
        "foundry": bundle["foundry"][0],
        "akber": bundle["akber"][0],
        "shadow": bundle["shadow"][0],
        "router": bundle["router"][0],
        "handoff": bundle["router"][6],
    }
    return summary, written, sorted(set(errors))
