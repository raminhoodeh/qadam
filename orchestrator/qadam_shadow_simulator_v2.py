"""Shadow Simulator V2 for Qadam next-generation flow Phase 8.

The simulator gives every Strategy Foundry V2 hypothesis shadow evidence after
Akber V2 review. Shadow evidence can support later Router confidence, but only
as research input: shadow success cannot create paper orders, broker writes,
proof credit, live-capital authority, or simulated 30-day paper-trial progress.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
from typing import Any

from orchestrator.config import Settings

SCHEMA_VERSION = "qadam_shadow_simulator_v2.v1"
PHASE_ID = "qadam_next_generation_phase_8_shadow_simulator_v2"

PRIMARY_ARTIFACT = "qadam_shadow_simulator_v2.json"
HISTORICAL_REPLAY_ARTIFACT = "qadam_shadow_simulator_v2_historical_replay.jsonl"
FORWARD_TRACKING_ARTIFACT = "qadam_shadow_simulator_v2_forward_tracking.jsonl"
COUNTERFACTUAL_NO_ORDER_ARTIFACT = "qadam_shadow_simulator_v2_counterfactual_no_order.jsonl"
ALTERNATE_THRESHOLD_OUTCOMES_ARTIFACT = "qadam_shadow_simulator_v2_alternate_threshold_outcomes.jsonl"
MISSED_OPPORTUNITIES_ARTIFACT = "qadam_shadow_simulator_v2_missed_opportunities.jsonl"
DASHBOARD_SUMMARY_ARTIFACT = "qadam_shadow_simulator_v2_dashboard_summary.json"
EVENTS_ARTIFACT = "qadam_shadow_simulator_v2_events.jsonl"

STRATEGY_FOUNDRY_V2_ARTIFACT = "qadam_strategy_foundry_v2.json"
STRATEGY_FOUNDRY_V2_HYPOTHESES_ARTIFACT = "qadam_strategy_foundry_v2_hypotheses.jsonl"
AKBER_FILTER_V2_ARTIFACT = "qadam_akber_filter_v2.json"
AKBER_FILTER_V2_INPUTS_ARTIFACT = "qadam_akber_filter_v2_inputs.jsonl"
AKBER_FILTER_V2_RESULTS_ARTIFACT = "qadam_akber_filter_v2_results.jsonl"
AKBER_FILTER_V2_THRESHOLD_PROPOSALS_ARTIFACT = "qadam_akber_filter_v2_threshold_proposals.jsonl"

AUTHORITY_FLAGS = {
    "read_only": True,
    "paper_only": True,
    "proposal_first": True,
    "research_only": True,
    "shadow_only": True,
    "shadow_success_is_not_order_authority": True,
    "shadow_success_is_not_proof_credit": True,
    "router_confidence_increase_created": False,
    "router_promotion_authority": False,
    "trade_candidate_creation_allowed": False,
    "trade_candidate_created": False,
    "qualified_setup_created": False,
    "risk_handoff_allowed": False,
    "risk_approval_allowed": False,
    "risk_approval_created": False,
    "execution_allowed": False,
    "execution_approval_allowed": False,
    "execution_approval_created": False,
    "paperops_direct_handoff_allowed": False,
    "paper_order_allowed": False,
    "paper_order_created": False,
    "broker_write_allowed": False,
    "broker_write_count": 0,
    "live_broker_endpoint_allowed": False,
    "live_capital_enabled": False,
    "proof_credit_allowed": False,
    "paper_proof_ledger_credit_allowed": False,
    "paper_growth_trial_calendar_advance_allowed": False,
    "paper_growth_trial_calendar_advanced": False,
    "simulated_elapsed_time_allowed": False,
    "threshold_change_applied": False,
    "strategy_mutation_allowed": False,
    "strategy_mutation_created": False,
    "telegram_command_path_enabled": False,
    "telegram_trade_command_enabled": False,
}

FORBIDDEN_TRUE_FIELDS = tuple(
    key for key, value in AUTHORITY_FLAGS.items() if value is False
)
FORBIDDEN_NONZERO_FIELDS = tuple(
    key for key, value in AUTHORITY_FLAGS.items() if isinstance(value, int) and value == 0
)


@dataclass(frozen=True)
class ShadowSimulatorBundle:
    primary: dict[str, Any]
    historical_replay: list[dict[str, Any]]
    forward_tracking: list[dict[str, Any]]
    counterfactual_no_order: list[dict[str, Any]]
    alternate_threshold_outcomes: list[dict[str, Any]]
    missed_opportunities: list[dict[str, Any]]
    dashboard_summary: dict[str, Any]


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


def _safe_dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _safe_list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def _safe_float(value: Any, default: float = 0.0) -> float:
    if isinstance(value, bool):
        return default
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _safe_int(value: Any, default: int = 0) -> int:
    if isinstance(value, bool):
        return default
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _hash_id(prefix: str, parts: list[Any]) -> str:
    payload = json.dumps(parts, sort_keys=True, default=str)
    digest = hashlib.sha256(payload.encode("utf-8")).hexdigest()[:20]
    return f"{prefix}:{digest}"


def _authority() -> dict[str, Any]:
    return dict(AUTHORITY_FLAGS)


def _load_context(settings: Settings | None = None) -> dict[str, Any]:
    runtime = _runtime_dir(settings)
    return {
        "runtime_dir": runtime,
        "foundry": _read_json(runtime / STRATEGY_FOUNDRY_V2_ARTIFACT),
        "hypotheses": _read_jsonl(runtime / STRATEGY_FOUNDRY_V2_HYPOTHESES_ARTIFACT),
        "akber": _read_json(runtime / AKBER_FILTER_V2_ARTIFACT),
        "akber_inputs": _read_jsonl(runtime / AKBER_FILTER_V2_INPUTS_ARTIFACT),
        "akber_results": _read_jsonl(runtime / AKBER_FILTER_V2_RESULTS_ARTIFACT),
        "threshold_proposals": _read_jsonl(runtime / AKBER_FILTER_V2_THRESHOLD_PROPOSALS_ARTIFACT),
    }


def _index_by(records: list[dict[str, Any]], key: str) -> dict[str, dict[str, Any]]:
    indexed = {}
    for record in records:
        value = record.get(key)
        if value:
            indexed[str(value)] = record
    return indexed


def _thresholds_by_result(
    thresholds: list[dict[str, Any]],
) -> dict[str, list[dict[str, Any]]]:
    grouped: dict[str, list[dict[str, Any]]] = {}
    for threshold in thresholds:
        hypothesis_id = str(threshold.get("strategy_hypothesis_id") or "")
        if hypothesis_id:
            grouped.setdefault(hypothesis_id, []).append(threshold)
    return grouped


def _historical_shadow_replay(
    hypothesis: dict[str, Any],
    akber_input: dict[str, Any],
    akber_result: dict[str, Any],
    generated_at: str,
) -> dict[str, Any]:
    evidence = _safe_dict(hypothesis.get("evidence_summary"))
    scores = _safe_dict(akber_result.get("scores"))
    sample_count = _safe_int(evidence.get("sample_count"))
    expectancy = _safe_float(evidence.get("expectancy"))
    hit_rate = _safe_float(evidence.get("hit_rate"), 0.5)
    missing_count = _safe_int(akber_result.get("critical_missing_context_count"))
    if missing_count:
        replay_state = "shadow_hold_missing_akber_context"
        shadow_outcome = "no_shadow_promotion"
    elif scores.get("akber_filter_score", 0) >= 0.72:
        replay_state = "shadow_passed_research_threshold"
        shadow_outcome = "shadow_success_research_only"
    else:
        replay_state = "shadow_hold_evidence_quality"
        shadow_outcome = "no_shadow_promotion"
    shadow_score = max(0.0, min(1.0, 0.35 * hit_rate + 0.25 * min(sample_count / 50, 1) + 10 * expectancy - 0.08 * missing_count))
    return {
        "schema_version": SCHEMA_VERSION,
        "phase_id": PHASE_ID,
        "shadow_replay_id": _hash_id("qadam-shadow-historical-v2", [hypothesis.get("strategy_hypothesis_id"), akber_result.get("akber_filter_result_id")]),
        "strategy_hypothesis_id": hypothesis.get("strategy_hypothesis_id"),
        "akber_filter_result_id": akber_result.get("akber_filter_result_id"),
        "akber_input_id": akber_input.get("akber_input_id"),
        "replay_mode": "historical_shadow_replay",
        "replay_state": replay_state,
        "shadow_outcome": shadow_outcome,
        "sample_count": sample_count,
        "expectancy": expectancy,
        "hit_rate": hit_rate,
        "akber_filter_decision": akber_result.get("decision", {}).get("filter_decision"),
        "akber_filter_score": scores.get("akber_filter_score"),
        "critical_missing_context_count": missing_count,
        "shadow_score": round(shadow_score, 4),
        "shadow_evidence_present": True,
        "router_confidence_increase_allowed": False,
        "router_confidence_increase_blocker": "Phase 9 Router V2 required; shadow evidence alone cannot increase Router confidence.",
        "paper_order_allowed": False,
        "paper_order_created": False,
        "proof_credit_allowed": False,
        "paper_proof_ledger_credit_allowed": False,
        "authority": _authority(),
        "generated_at": generated_at,
    }


def _forward_tracking(
    hypothesis: dict[str, Any],
    historical_record: dict[str, Any],
    generated_at: str,
) -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "phase_id": PHASE_ID,
        "forward_tracking_id": _hash_id("qadam-shadow-forward-v2", [historical_record.get("shadow_replay_id")]),
        "strategy_hypothesis_id": hypothesis.get("strategy_hypothesis_id"),
        "shadow_replay_id": historical_record.get("shadow_replay_id"),
        "tracking_mode": "forward_shadow_tracking",
        "tracking_state": "watch_only_no_elapsed_time_simulation",
        "observed_market_expression": hypothesis.get("instrument_proxy_mapping", {}).get("observed_market_expression"),
        "primary_proxy": hypothesis.get("instrument_proxy_mapping", {}).get("primary_proxy"),
        "start_observed_at": generated_at,
        "forward_window_status": "not_started_until_real_time_observation",
        "simulated_elapsed_time_allowed": False,
        "paper_growth_trial_calendar_advance_allowed": False,
        "shadow_evidence_present": True,
        "router_confidence_increase_allowed": False,
        "paper_order_created": False,
        "proof_credit_allowed": False,
        "authority": _authority(),
        "generated_at": generated_at,
    }


def _counterfactual_no_order(
    hypothesis: dict[str, Any],
    akber_result: dict[str, Any],
    historical_record: dict[str, Any],
    generated_at: str,
) -> dict[str, Any]:
    decision = akber_result.get("decision", {}).get("filter_decision")
    no_order_reason = (
        "Akber missing-context hold protected the system from routing an incomplete setup."
        if decision == "hold_missing_context"
        else "No-order outcome recorded for research comparison only."
    )
    return {
        "schema_version": SCHEMA_VERSION,
        "phase_id": PHASE_ID,
        "counterfactual_id": _hash_id("qadam-shadow-no-order-v2", [historical_record.get("shadow_replay_id")]),
        "strategy_hypothesis_id": hypothesis.get("strategy_hypothesis_id"),
        "shadow_replay_id": historical_record.get("shadow_replay_id"),
        "actual_decision": "no_order",
        "hypothetical_decision": "paper_order_if_all_later_gates_passed",
        "actual_outcome_state": "safety_preserved_no_order",
        "hypothetical_outcome_state": "not_executed_counterfactual_only",
        "no_order_reason": no_order_reason,
        "counterfactual_pnl": None,
        "counterfactual_is_not_proof": True,
        "paper_order_created": False,
        "paper_proof_ledger_credit_allowed": False,
        "proof_credit_allowed": False,
        "authority": _authority(),
        "generated_at": generated_at,
    }


def _alternate_threshold_outcome(
    hypothesis: dict[str, Any],
    akber_result: dict[str, Any],
    thresholds: list[dict[str, Any]],
    historical_record: dict[str, Any],
    generated_at: str,
) -> dict[str, Any]:
    score = _safe_float(akber_result.get("scores", {}).get("akber_filter_score"))
    missing_count = _safe_int(akber_result.get("critical_missing_context_count"))
    variants = []
    for threshold in thresholds:
        name = str(threshold.get("threshold_name") or "")
        proposed_value = threshold.get("proposed_value")
        if name == "minimum_akber_filter_score_for_pass":
            would_pass = score >= _safe_float(proposed_value) and missing_count == 0
        elif name == "requires_no_critical_missing_context":
            would_pass = missing_count == 0 and proposed_value is True
        elif name == "akber_pass_is_not_execution_approval":
            would_pass = False
        else:
            would_pass = False if missing_count else score >= 0.5
        variants.append(
            {
                "threshold_proposal_id": threshold.get("threshold_proposal_id"),
                "threshold_name": name,
                "proposed_value": proposed_value,
                "would_change_decision": False,
                "variant_decision": "hold_missing_context" if missing_count else "shadow_threshold_research_only",
                "would_pass": bool(would_pass),
                "threshold_change_applied": False,
            }
        )
    return {
        "schema_version": SCHEMA_VERSION,
        "phase_id": PHASE_ID,
        "alternate_threshold_outcome_id": _hash_id("qadam-shadow-threshold-v2", [historical_record.get("shadow_replay_id"), score]),
        "strategy_hypothesis_id": hypothesis.get("strategy_hypothesis_id"),
        "akber_filter_result_id": akber_result.get("akber_filter_result_id"),
        "shadow_replay_id": historical_record.get("shadow_replay_id"),
        "variant_count": len(variants),
        "variants": variants,
        "threshold_outcome_state": "no_threshold_variant_can_bypass_missing_context" if missing_count else "threshold_research_only",
        "threshold_change_applied": False,
        "router_confidence_increase_allowed": False,
        "paper_order_created": False,
        "proof_credit_allowed": False,
        "authority": _authority(),
        "generated_at": generated_at,
    }


def _missed_opportunity(
    hypothesis: dict[str, Any],
    akber_result: dict[str, Any],
    historical_record: dict[str, Any],
    generated_at: str,
) -> dict[str, Any]:
    evidence = _safe_dict(hypothesis.get("evidence_summary"))
    positive_expectancy = _safe_float(evidence.get("expectancy")) > 0
    missing_count = _safe_int(akber_result.get("critical_missing_context_count"))
    if positive_expectancy and missing_count:
        state = "possible_missed_opportunity_due_missing_context"
        learning_question = "Would live confirmation have converted this research edge into a safer later setup?"
    elif positive_expectancy:
        state = "possible_missed_opportunity_under_shadow_observation"
        learning_question = "Would later Router review have improved timing without increasing risk?"
    else:
        state = "no_missed_opportunity_signal"
        learning_question = "No positive expectancy signal is available for this hypothesis."
    return {
        "schema_version": SCHEMA_VERSION,
        "phase_id": PHASE_ID,
        "missed_opportunity_id": _hash_id("qadam-shadow-missed-v2", [historical_record.get("shadow_replay_id"), state]),
        "strategy_hypothesis_id": hypothesis.get("strategy_hypothesis_id"),
        "shadow_replay_id": historical_record.get("shadow_replay_id"),
        "missed_opportunity_state": state,
        "positive_expectancy": positive_expectancy,
        "critical_missing_context_count": missing_count,
        "learning_question": learning_question,
        "missed_opportunity_is_not_proof": True,
        "paper_proof_ledger_credit_allowed": False,
        "paper_order_created": False,
        "proof_credit_allowed": False,
        "authority": _authority(),
        "generated_at": generated_at,
    }


def build_shadow_simulator_v2(settings: Settings | None = None) -> ShadowSimulatorBundle:
    generated_at = _iso()
    context = _load_context(settings)
    akber_inputs = _index_by(context["akber_inputs"], "strategy_hypothesis_id")
    akber_results = _index_by(context["akber_results"], "strategy_hypothesis_id")
    thresholds_by_hypothesis = _thresholds_by_result(context["threshold_proposals"])

    historical: list[dict[str, Any]] = []
    forward: list[dict[str, Any]] = []
    counterfactual: list[dict[str, Any]] = []
    thresholds: list[dict[str, Any]] = []
    missed: list[dict[str, Any]] = []

    for hypothesis in context["hypotheses"]:
        hypothesis_id = str(hypothesis.get("strategy_hypothesis_id") or "")
        akber_input = akber_inputs.get(hypothesis_id, {})
        akber_result = akber_results.get(hypothesis_id, {})
        historical_record = _historical_shadow_replay(hypothesis, akber_input, akber_result, generated_at)
        historical.append(historical_record)
        forward.append(_forward_tracking(hypothesis, historical_record, generated_at))
        counterfactual.append(_counterfactual_no_order(hypothesis, akber_result, historical_record, generated_at))
        thresholds.append(
            _alternate_threshold_outcome(
                hypothesis,
                akber_result,
                thresholds_by_hypothesis.get(hypothesis_id, []),
                historical_record,
                generated_at,
            )
        )
        missed.append(_missed_opportunity(hypothesis, akber_result, historical_record, generated_at))

    hypothesis_ids = {str(h.get("strategy_hypothesis_id")) for h in context["hypotheses"] if h.get("strategy_hypothesis_id")}
    shadow_ids = {str(record.get("strategy_hypothesis_id")) for record in historical if record.get("strategy_hypothesis_id")}
    missing_shadow_ids = sorted(hypothesis_ids - shadow_ids)
    state_counts = Counter(str(record.get("replay_state") or "unknown") for record in historical)
    missed_counts = Counter(str(record.get("missed_opportunity_state") or "unknown") for record in missed)
    status = "shadow_simulator_v2_ready" if not missing_shadow_ids and historical else "shadow_simulator_v2_blocked_missing_hypothesis_shadow_evidence"
    primary = {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "qadam_shadow_simulator_v2",
        "phase_id": PHASE_ID,
        "generated_at": generated_at,
        "status": status,
        "public_safe": True,
        "read_only": True,
        "paper_only": True,
        "proposal_first": True,
        "research_only": True,
        "input_artifacts": {
            "strategy_foundry_v2": STRATEGY_FOUNDRY_V2_ARTIFACT,
            "strategy_foundry_v2_hypotheses": STRATEGY_FOUNDRY_V2_HYPOTHESES_ARTIFACT,
            "akber_filter_v2": AKBER_FILTER_V2_ARTIFACT,
            "akber_filter_v2_inputs": AKBER_FILTER_V2_INPUTS_ARTIFACT,
            "akber_filter_v2_results": AKBER_FILTER_V2_RESULTS_ARTIFACT,
        },
        "hypothesis_count": len(context["hypotheses"]),
        "hypothesis_with_shadow_evidence_count": len(shadow_ids),
        "missing_shadow_evidence_count": len(missing_shadow_ids),
        "missing_shadow_evidence_hypothesis_ids": missing_shadow_ids,
        "historical_shadow_replay_count": len(historical),
        "forward_tracking_count": len(forward),
        "counterfactual_no_order_count": len(counterfactual),
        "alternate_threshold_outcome_count": len(thresholds),
        "missed_opportunity_count": len(missed),
        "shadow_replay_state_counts": dict(state_counts),
        "missed_opportunity_state_counts": dict(missed_counts),
        "every_hypothesis_has_shadow_evidence": len(missing_shadow_ids) == 0,
        "router_confidence_increase_without_shadow_evidence_count": 0,
        "router_confidence_increase_created": False,
        "shadow_success_cannot_create_paper_order": True,
        "shadow_success_cannot_create_proof_credit": True,
        "paper_order_created": False,
        "paper_order_created_count": 0,
        "proof_credit_allowed": False,
        "paper_proof_ledger_credit_allowed": False,
        "broker_write_allowed": False,
        "broker_write_count": 0,
        "live_capital_enabled": False,
        "paper_growth_trial_calendar_advanced": False,
        "simulated_elapsed_time_allowed": False,
        "authority": _authority(),
        "artifact_refs": {
            "historical_replay": HISTORICAL_REPLAY_ARTIFACT,
            "forward_tracking": FORWARD_TRACKING_ARTIFACT,
            "counterfactual_no_order": COUNTERFACTUAL_NO_ORDER_ARTIFACT,
            "alternate_threshold_outcomes": ALTERNATE_THRESHOLD_OUTCOMES_ARTIFACT,
            "missed_opportunities": MISSED_OPPORTUNITIES_ARTIFACT,
            "dashboard_summary": DASHBOARD_SUMMARY_ARTIFACT,
        },
    }
    return ShadowSimulatorBundle(
        primary=primary,
        historical_replay=historical,
        forward_tracking=forward,
        counterfactual_no_order=counterfactual,
        alternate_threshold_outcomes=thresholds,
        missed_opportunities=missed,
        dashboard_summary=_dashboard_summary(primary, historical, missed, generated_at),
    )


def _dashboard_summary(
    primary: dict[str, Any],
    historical: list[dict[str, Any]],
    missed: list[dict[str, Any]],
    generated_at: str,
) -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "qadam_shadow_simulator_v2_dashboard_summary",
        "phase_id": PHASE_ID,
        "generated_at": generated_at,
        "status": primary.get("status"),
        "public_safe": True,
        "read_only": True,
        "paper_only": True,
        "proposal_first": True,
        "research_only": True,
        "hypothesis_count": primary.get("hypothesis_count"),
        "hypothesis_with_shadow_evidence_count": primary.get("hypothesis_with_shadow_evidence_count"),
        "missing_shadow_evidence_count": primary.get("missing_shadow_evidence_count"),
        "historical_shadow_replay_count": primary.get("historical_shadow_replay_count"),
        "forward_tracking_count": primary.get("forward_tracking_count"),
        "counterfactual_no_order_count": primary.get("counterfactual_no_order_count"),
        "alternate_threshold_outcome_count": primary.get("alternate_threshold_outcome_count"),
        "missed_opportunity_count": primary.get("missed_opportunity_count"),
        "every_hypothesis_has_shadow_evidence": primary.get("every_hypothesis_has_shadow_evidence"),
        "router_confidence_increase_without_shadow_evidence_count": primary.get("router_confidence_increase_without_shadow_evidence_count"),
        "router_confidence_increase_created": False,
        "shadow_success_cannot_create_paper_order": True,
        "shadow_success_cannot_create_proof_credit": True,
        "paper_order_created": False,
        "proof_credit_allowed": False,
        "cards": [
            {
                "strategy_hypothesis_id": record.get("strategy_hypothesis_id"),
                "replay_state": record.get("replay_state"),
                "shadow_score": record.get("shadow_score"),
                "akber_filter_decision": record.get("akber_filter_decision"),
                "router_confidence_increase_allowed": record.get("router_confidence_increase_allowed"),
                "missed_opportunity_state": next(
                    (
                        item.get("missed_opportunity_state")
                        for item in missed
                        if item.get("shadow_replay_id") == record.get("shadow_replay_id")
                    ),
                    None,
                ),
            }
            for record in historical
        ],
        "message": (
            "Shadow Simulator V2 gives every research hypothesis shadow evidence. "
            "Shadow success cannot create paper orders, proof credit, or Router confidence increases by itself."
        ),
        "next_allowed_action": "Phase 9 Router V2 may read shadow evidence, but must enforce its own single-state routing gates.",
        "authority": _authority(),
    }


def write_shadow_simulator_v2(bundle: ShadowSimulatorBundle, settings: Settings | None = None) -> dict[str, str]:
    runtime = _runtime_dir(settings)
    paths = {
        "primary": runtime / PRIMARY_ARTIFACT,
        "historical_replay": runtime / HISTORICAL_REPLAY_ARTIFACT,
        "forward_tracking": runtime / FORWARD_TRACKING_ARTIFACT,
        "counterfactual_no_order": runtime / COUNTERFACTUAL_NO_ORDER_ARTIFACT,
        "alternate_threshold_outcomes": runtime / ALTERNATE_THRESHOLD_OUTCOMES_ARTIFACT,
        "missed_opportunities": runtime / MISSED_OPPORTUNITIES_ARTIFACT,
        "dashboard_summary": runtime / DASHBOARD_SUMMARY_ARTIFACT,
        "events": runtime / EVENTS_ARTIFACT,
    }
    _write_json(paths["primary"], bundle.primary)
    _write_jsonl(paths["historical_replay"], bundle.historical_replay)
    _write_jsonl(paths["forward_tracking"], bundle.forward_tracking)
    _write_jsonl(paths["counterfactual_no_order"], bundle.counterfactual_no_order)
    _write_jsonl(paths["alternate_threshold_outcomes"], bundle.alternate_threshold_outcomes)
    _write_jsonl(paths["missed_opportunities"], bundle.missed_opportunities)
    _write_json(paths["dashboard_summary"], bundle.dashboard_summary)
    _append_jsonl(
        paths["events"],
        {
            "schema_version": SCHEMA_VERSION,
            "phase_id": PHASE_ID,
            "event_type": "shadow_simulator_v2_written",
            "generated_at": bundle.primary.get("generated_at"),
            "status": bundle.primary.get("status"),
            "hypothesis_count": bundle.primary.get("hypothesis_count"),
            "every_hypothesis_has_shadow_evidence": bundle.primary.get("every_hypothesis_has_shadow_evidence"),
            "router_confidence_increase_created": False,
            "paper_order_created": False,
            "proof_credit_allowed": False,
            "broker_write_count": 0,
            "live_capital_enabled": False,
            "authority": _authority(),
        },
    )
    return {key: str(path) for key, path in paths.items()}


def build_and_write_shadow_simulator_v2(settings: Settings | None = None) -> tuple[ShadowSimulatorBundle, dict[str, str]]:
    bundle = build_shadow_simulator_v2(settings)
    written = write_shadow_simulator_v2(bundle, settings)
    return bundle, written


def _validate_authority(payload: dict[str, Any], prefix: str) -> list[str]:
    errors: list[str] = []
    authority = _safe_dict(payload.get("authority"))
    for key, expected in AUTHORITY_FLAGS.items():
        if authority.get(key) != expected:
            errors.append(f"{prefix}_{key}_authority_invalid")
    for field in FORBIDDEN_TRUE_FIELDS:
        if payload.get(field) is True:
            errors.append(f"{prefix}_{field}_must_not_be_true")
    for field in FORBIDDEN_NONZERO_FIELDS:
        if _safe_int(payload.get(field), 0) != 0:
            errors.append(f"{prefix}_{field}_must_be_zero")
    return errors


def validate_shadow_record(record: dict[str, Any], prefix: str) -> list[str]:
    errors: list[str] = []
    if record.get("schema_version") != SCHEMA_VERSION:
        errors.append(f"{prefix}_schema_version_invalid")
    if record.get("phase_id") != PHASE_ID:
        errors.append(f"{prefix}_phase_id_invalid")
    if record.get("paper_order_created") is not False:
        errors.append(f"{prefix}_paper_order_created_must_be_false")
    if record.get("proof_credit_allowed") is not False:
        errors.append(f"{prefix}_proof_credit_allowed_must_be_false")
    if record.get("router_confidence_increase_allowed") is True:
        errors.append(f"{prefix}_router_confidence_increase_allowed_must_not_be_true")
    errors.extend(_validate_authority(record, prefix))
    return errors


def validate_shadow_simulator_v2_bundle(bundle: ShadowSimulatorBundle | dict[str, Any]) -> list[str]:
    if isinstance(bundle, ShadowSimulatorBundle):
        primary = bundle.primary
        historical = bundle.historical_replay
        forward = bundle.forward_tracking
        counterfactual = bundle.counterfactual_no_order
        thresholds = bundle.alternate_threshold_outcomes
        missed = bundle.missed_opportunities
        dashboard = bundle.dashboard_summary
    else:
        primary = _safe_dict(bundle.get("primary"))
        historical = _safe_list(bundle.get("historical_replay"))
        forward = _safe_list(bundle.get("forward_tracking"))
        counterfactual = _safe_list(bundle.get("counterfactual_no_order"))
        thresholds = _safe_list(bundle.get("alternate_threshold_outcomes"))
        missed = _safe_list(bundle.get("missed_opportunities"))
        dashboard = _safe_dict(bundle.get("dashboard_summary"))
    errors: list[str] = []
    if primary.get("schema_version") != SCHEMA_VERSION:
        errors.append("primary_schema_version_invalid")
    if primary.get("phase_id") != PHASE_ID:
        errors.append("primary_phase_id_invalid")
    if primary.get("artifact_type") != "qadam_shadow_simulator_v2":
        errors.append("primary_artifact_type_invalid")
    if primary.get("status") != "shadow_simulator_v2_ready":
        errors.append("primary_status_not_ready")
    for key in ("public_safe", "read_only", "paper_only", "proposal_first", "research_only"):
        if primary.get(key) is not True:
            errors.append(f"primary_{key}_must_be_true")
    if primary.get("every_hypothesis_has_shadow_evidence") is not True:
        errors.append("not_every_hypothesis_has_shadow_evidence")
    if _safe_int(primary.get("missing_shadow_evidence_count")) != 0:
        errors.append("missing_shadow_evidence_count_nonzero")
    if _safe_int(primary.get("router_confidence_increase_without_shadow_evidence_count")) != 0:
        errors.append("router_confidence_increase_without_shadow_evidence_nonzero")
    if primary.get("router_confidence_increase_created") is not False:
        errors.append("router_confidence_increase_created_must_be_false")
    if primary.get("shadow_success_cannot_create_paper_order") is not True:
        errors.append("shadow_success_order_boundary_missing")
    if primary.get("shadow_success_cannot_create_proof_credit") is not True:
        errors.append("shadow_success_proof_boundary_missing")
    if not historical:
        errors.append("historical_shadow_replay_missing")
    if len(historical) != _safe_int(primary.get("hypothesis_count")):
        errors.append("historical_shadow_count_mismatch")
    for index, record in enumerate(historical, start=1):
        if record.get("shadow_evidence_present") is not True:
            errors.append(f"historical_{index}_shadow_evidence_present_missing")
        for error in validate_shadow_record(record, "historical"):
            errors.append(f"historical_{index}_{error}")
    for index, record in enumerate(forward, start=1):
        for error in validate_shadow_record(record, "forward"):
            errors.append(f"forward_{index}_{error}")
        if record.get("simulated_elapsed_time_allowed") is not False:
            errors.append(f"forward_{index}_simulated_elapsed_time_allowed_must_be_false")
    for index, record in enumerate(counterfactual, start=1):
        for error in validate_shadow_record(record, "counterfactual"):
            errors.append(f"counterfactual_{index}_{error}")
        if record.get("counterfactual_is_not_proof") is not True:
            errors.append(f"counterfactual_{index}_not_proof_boundary_missing")
    for index, record in enumerate(thresholds, start=1):
        for error in validate_shadow_record(record, "threshold"):
            errors.append(f"threshold_{index}_{error}")
        if record.get("threshold_change_applied") is not False:
            errors.append(f"threshold_{index}_threshold_change_applied_must_be_false")
    for index, record in enumerate(missed, start=1):
        for error in validate_shadow_record(record, "missed"):
            errors.append(f"missed_{index}_{error}")
        if record.get("missed_opportunity_is_not_proof") is not True:
            errors.append(f"missed_{index}_not_proof_boundary_missing")
    if dashboard.get("artifact_type") != "qadam_shadow_simulator_v2_dashboard_summary":
        errors.append("dashboard_summary_artifact_type_invalid")
    if dashboard.get("shadow_success_cannot_create_paper_order") is not True:
        errors.append("dashboard_shadow_order_boundary_missing")
    if dashboard.get("shadow_success_cannot_create_proof_credit") is not True:
        errors.append("dashboard_shadow_proof_boundary_missing")
    errors.extend(_validate_authority(primary, "primary"))
    return errors


def validate_negative_shadow_simulator_v2_probes(settings: Settings | None = None) -> list[str]:
    bundle = build_shadow_simulator_v2(settings)
    if not bundle.historical_replay:
        return ["negative_probe_skipped_missing_shadow_records"]
    errors: list[str] = []
    unsafe_order = json.loads(json.dumps(bundle.historical_replay[0]))
    unsafe_order["paper_order_created"] = True
    unsafe_order["authority"]["paper_order_created"] = True
    if not validate_shadow_record(unsafe_order, "historical"):
        errors.append("negative_probe_failed_for_paper_order_boundary")

    unsafe_proof = json.loads(json.dumps(bundle.missed_opportunities[0]))
    unsafe_proof["proof_credit_allowed"] = True
    unsafe_proof["authority"]["proof_credit_allowed"] = True
    if not validate_shadow_record(unsafe_proof, "missed"):
        errors.append("negative_probe_failed_for_proof_boundary")

    unsafe_router = json.loads(json.dumps(bundle.historical_replay[0]))
    unsafe_router["router_confidence_increase_allowed"] = True
    if not validate_shadow_record(unsafe_router, "historical"):
        errors.append("negative_probe_failed_for_router_confidence_boundary")

    missing_shadow_payload = {
        "primary": {**bundle.primary, "missing_shadow_evidence_count": 1, "every_hypothesis_has_shadow_evidence": False},
        "historical_replay": bundle.historical_replay[:-1],
        "forward_tracking": bundle.forward_tracking,
        "counterfactual_no_order": bundle.counterfactual_no_order,
        "alternate_threshold_outcomes": bundle.alternate_threshold_outcomes,
        "missed_opportunities": bundle.missed_opportunities,
        "dashboard_summary": bundle.dashboard_summary,
    }
    if not validate_shadow_simulator_v2_bundle(missing_shadow_payload):
        errors.append("negative_probe_failed_for_missing_shadow_evidence")
    return errors


def load_shadow_simulator_v2(settings: Settings | None = None) -> dict[str, Any]:
    runtime = _runtime_dir(settings)
    return {
        "primary": _read_json(runtime / PRIMARY_ARTIFACT),
        "historical_replay": _read_jsonl(runtime / HISTORICAL_REPLAY_ARTIFACT),
        "forward_tracking": _read_jsonl(runtime / FORWARD_TRACKING_ARTIFACT),
        "counterfactual_no_order": _read_jsonl(runtime / COUNTERFACTUAL_NO_ORDER_ARTIFACT),
        "alternate_threshold_outcomes": _read_jsonl(runtime / ALTERNATE_THRESHOLD_OUTCOMES_ARTIFACT),
        "missed_opportunities": _read_jsonl(runtime / MISSED_OPPORTUNITIES_ARTIFACT),
        "dashboard_summary": _read_json(runtime / DASHBOARD_SUMMARY_ARTIFACT),
    }
