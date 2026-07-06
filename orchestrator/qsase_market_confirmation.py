"""QSASE market confirmation and Akber input builder.

This module prepares practical market-confirmation packets for Akber's filter.
It is evidence preparation only: it cannot approve execution, create trade
candidates, route PaperOps, submit orders, or mutate strategy thresholds.
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

SCHEMA_VERSION = "qsase_market_confirmation.v1"
PRIMARY_ARTIFACT = "qsase_market_confirmation.json"
PACKETS_ARTIFACT = "qsase_market_confirmation_packets.jsonl"
AKBER_COMPLETENESS_ARTIFACT = "qsase_akber_input_completeness.json"
REPAIR_QUEUE_ARTIFACT = "qsase_market_confirmation_repair_queue.jsonl"
DASHBOARD_SUMMARY_ARTIFACT = "qsase_market_confirmation_dashboard_summary.json"
HISTORY_ARTIFACT = "qsase_market_confirmation_history.jsonl"
EVENTS_ARTIFACT = "qsase_market_confirmation_events.jsonl"

STRATEGY_HYPOTHESES_ARTIFACT = "qsase_strategy_hypotheses.jsonl"
AKBER_RESULTS_ARTIFACT = "qsase_akber_filter_results.jsonl"
MARKET_CONFIRMATION_ARTIFACT = "phase5_market_confirmation_refresh.json"
TECHNICAL_CONTEXT_ARTIFACT = "tradingview_mcp_technical_context.json"

REQUIRED_INPUTS = [
    "volatility_context",
    "technical_confirmation",
    "volume_or_flow_confirmation",
    "pricing_gap_evidence",
    "catalyst_strength",
    "liquidity_state",
    "invalidation",
    "paperability",
]

AUTHORITY_FLAGS = {
    "market_confirmation_read_only": True,
    "akber_input_preparation_only": True,
    "akber_pass_is_execution_approval": False,
    "trade_candidate_created": False,
    "qualified_setup_created": False,
    "risk_approval_created": False,
    "execution_approval_created": False,
    "paper_order_created": False,
    "broker_write_allowed": False,
    "paperops_handoff_created": False,
    "strategy_mutation_created": False,
    "threshold_change_applied": False,
    "proof_credit_allowed": False,
    "live_capital_enabled": False,
}


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
    lines = path.read_text(encoding="utf-8").splitlines()
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


def _hash_id(parts: list[Any], prefix: str) -> str:
    raw = "|".join(str(part) for part in parts)
    return f"{prefix}:{hashlib.sha256(raw.encode('utf-8')).hexdigest()[:20]}"


def _family(record: dict[str, Any]) -> str:
    family = record.get("family_mapping") if isinstance(record.get("family_mapping"), dict) else {}
    return str(family.get("mapped_existing_family") or family.get("primary_family") or "")


def _instrument(record: dict[str, Any]) -> str:
    candidate = record.get("candidate_identity") if isinstance(record.get("candidate_identity"), dict) else {}
    market = record.get("market_expression") if isinstance(record.get("market_expression"), dict) else {}
    return str(candidate.get("instrument") or market.get("observed_market_expression") or market.get("primary_instrument") or "")


def _match_market_confirmation(family: str, market_context: dict[str, Any]) -> dict[str, Any]:
    targets = market_context.get("targets") if isinstance(market_context.get("targets"), list) else []
    for target in targets:
        if isinstance(target, dict) and str(target.get("strategy_family_key")) == family:
            return target
    return {}


def _match_technical_context(instrument: str, technical_context: dict[str, Any]) -> dict[str, Any]:
    contexts = technical_context.get("technical_contexts") if isinstance(technical_context.get("technical_contexts"), list) else []
    candidates = {instrument.upper()}
    if instrument.upper() in {"CL=F", "USO", "BNO"}:
        candidates.update({"TVC:USOIL", "USO"})
    if instrument.upper() in {"SI=F", "SLV", "SIL"}:
        candidates.update({"SLV", "TVC:SILVER"})
    for context in contexts:
        if not isinstance(context, dict):
            continue
        symbol = str(context.get("symbol") or "").upper()
        if symbol in candidates:
            return context
    return {}


def _akber_by_hypothesis(results: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    lookup: dict[str, dict[str, Any]] = {}
    for result in results:
        hypothesis_id = str(result.get("strategy_hypothesis_id") or "")
        if hypothesis_id:
            lookup[hypothesis_id] = result
    return lookup


def _input_state(name: str, present: bool, score: float, reason: str, refs: list[str] | None = None) -> dict[str, Any]:
    return {
        "name": name,
        "present": bool(present),
        "score": round(score, 4),
        "state": "present" if present else "missing",
        "reason": reason,
        "refs": refs or [],
    }


def _build_packet(
    hypothesis: dict[str, Any],
    akber_result: dict[str, Any],
    market_target: dict[str, Any],
    technical: dict[str, Any],
    generated_at: str,
) -> dict[str, Any]:
    hypothesis_id = str(hypothesis.get("strategy_hypothesis_id") or "unknown")
    family = _family(hypothesis)
    instrument = _instrument(hypothesis)
    scores = akber_result.get("scores") if isinstance(akber_result.get("scores"), dict) else {}
    stage = akber_result.get("stage_state") if isinstance(akber_result.get("stage_state"), dict) else {}
    indicator_state = technical.get("indicator_state") if isinstance(technical.get("indicator_state"), dict) else {}
    invalidation = hypothesis.get("invalidation_concept") if isinstance(hypothesis.get("invalidation_concept"), dict) else {}
    paperability = hypothesis.get("paperability") if isinstance(hypothesis.get("paperability"), dict) else {}

    technical_score = _float(technical.get("technical_score"))
    volatility_score = max(_float(scores.get("volatility_setup_score")), 0.55 if technical.get("volatility_state") else 0.0)
    volume_score = _float(scores.get("volume_flow_score"))
    volume_evidence = (
        indicator_state.get("volume")
        or indicator_state.get("relative_volume")
        or indicator_state.get("obv")
        or stage.get("obv_volume")
    )
    volume_missing_text = "missing" in str(volume_evidence or stage.get("obv_volume", "")).lower()
    volume_present = bool(volume_evidence) and not volume_missing_text
    volume_input_score = max(volume_score, 0.2 if volume_present else 0.0)
    pricing_gap_present = (
        str(market_target.get("pricing_gap_status") or "").startswith("pass")
        or _float(scores.get("pricing_gap_score")) >= 0.35
    )
    catalyst_present = _float(scores.get("catalyst_quality_score")) >= 0.5 or bool(hypothesis.get("source_recipe"))
    liquidity_present = bool(hypothesis.get("market_expression", {}).get("paperable_execution_expression")) or bool(
        market_target.get("providers")
    )
    invalidation_present = bool(invalidation.get("summary") or invalidation.get("hard_invalidators"))
    paperability_present = bool(paperability.get("paper_review_candidate")) and not paperability.get("paperability_blockers")

    inputs = {
        "volatility_context": _input_state(
            "volatility_context",
            volatility_score >= 0.35,
            volatility_score,
            str(technical.get("volatility_state") or stage.get("low_volatility") or "volatility_context_missing"),
            ["data/runtime/tradingview_mcp_technical_context.json"] if technical else [],
        ),
        "technical_confirmation": _input_state(
            "technical_confirmation",
            technical_score >= 0.5 or _float(scores.get("technical_confirmation_score")) >= 0.35,
            max(technical_score, _float(scores.get("technical_confirmation_score"))),
            str(technical.get("setup_type") or stage.get("technical_setup") or "technical_confirmation_missing"),
            ["data/runtime/tradingview_mcp_technical_context.json"] if technical else [],
        ),
        "volume_or_flow_confirmation": _input_state(
            "volume_or_flow_confirmation",
            volume_present,
            volume_input_score,
            str(volume_evidence or "volume_or_flow_missing"),
            ["data/runtime/tradingview_mcp_technical_context.json"] if technical else [],
        ),
        "pricing_gap_evidence": _input_state(
            "pricing_gap_evidence",
            pricing_gap_present,
            max(_float(scores.get("pricing_gap_score")), 0.7 if pricing_gap_present else 0.0),
            str(market_target.get("pricing_gap_status") or stage.get("options_distribution_gap") or "pricing_gap_missing"),
            ["data/runtime/phase5_market_confirmation_refresh.json"] if market_target else [],
        ),
        "catalyst_strength": _input_state(
            "catalyst_strength",
            catalyst_present,
            _float(scores.get("catalyst_quality_score"), 0.5 if catalyst_present else 0.0),
            str(stage.get("catalyst_identification") or "source_recipe_present"),
            ["data/runtime/qsase_strategy_hypotheses.jsonl"],
        ),
        "liquidity_state": _input_state(
            "liquidity_state",
            liquidity_present,
            0.65 if liquidity_present else 0.0,
            "paperable proxy and provider context present" if liquidity_present else "liquidity_or_proxy_context_missing",
            ["data/runtime/qsase_strategy_hypotheses.jsonl", "data/runtime/phase5_market_confirmation_refresh.json"],
        ),
        "invalidation": _input_state(
            "invalidation",
            invalidation_present,
            _float(scores.get("invalidation_clarity_score"), 0.6 if invalidation_present else 0.0),
            str(invalidation.get("summary") or "invalidation_missing"),
            ["data/runtime/qsase_strategy_hypotheses.jsonl"],
        ),
        "paperability": _input_state(
            "paperability",
            paperability_present,
            0.8 if paperability_present else 0.0,
            str(paperability.get("paperability_state") or "paperability_missing"),
            ["data/runtime/qsase_strategy_hypotheses.jsonl"],
        ),
    }

    missing = [name for name in REQUIRED_INPUTS if not inputs[name]["present"]]
    completeness_score = round(sum(1 for name in REQUIRED_INPUTS if inputs[name]["present"]) / len(REQUIRED_INPUTS), 4)
    return {
        "schema_version": SCHEMA_VERSION,
        "market_confirmation_packet_id": _hash_id([SCHEMA_VERSION, hypothesis_id, "market-confirmation"], "qsase-market-confirmation"),
        "generated_at": generated_at,
        "strategy_hypothesis_id": hypothesis_id,
        "akber_filter_result_id": akber_result.get("akber_filter_result_id"),
        "strategy_family": family,
        "instrument": instrument,
        "paperable_execution_expression": hypothesis.get("market_expression", {}).get("paperable_execution_expression"),
        "inputs": inputs,
        "required_input_count": len(REQUIRED_INPUTS),
        "present_input_count": len(REQUIRED_INPUTS) - len(missing),
        "missing_inputs": missing,
        "completeness_score": completeness_score,
        "akber_input_complete": not missing,
        "packet_status": "market_confirmation_packet_complete" if not missing else "market_confirmation_packet_missing_inputs",
        "akber_ready_state": "ready_for_akber_pass_hold_veto" if not missing else "akber_must_hold_until_inputs_complete",
        "next_action": "send_to_akber_filter_review" if not missing else f"repair_missing_inputs:{','.join(missing)}",
        "refs": {
            "strategy_hypothesis": "data/runtime/qsase_strategy_hypotheses.jsonl",
            "akber_filter_result": "data/runtime/qsase_akber_filter_results.jsonl",
            "market_confirmation": "data/runtime/phase5_market_confirmation_refresh.json" if market_target else None,
            "technical_context": "data/runtime/tradingview_mcp_technical_context.json" if technical else None,
        },
        "authority": AUTHORITY_FLAGS,
        "execution_allowed": False,
        "risk_approval_created": False,
        "paper_order_created": False,
        "broker_write_allowed": False,
        "paperops_handoff_created": False,
        "proof_credit_allowed": False,
        "live_capital_enabled": False,
    }


def build_market_confirmation(settings: Settings | None = None) -> tuple[dict[str, Any], list[dict[str, Any]], list[dict[str, Any]], dict[str, Any]]:
    runtime = _runtime_dir(settings)
    now = _now()
    generated_at = _iso(now)
    hypotheses = _read_jsonl(runtime / STRATEGY_HYPOTHESES_ARTIFACT)
    akber_results = _read_jsonl(runtime / AKBER_RESULTS_ARTIFACT)
    market_context = _read_json(runtime / MARKET_CONFIRMATION_ARTIFACT)
    technical_context = _read_json(runtime / TECHNICAL_CONTEXT_ARTIFACT)
    akber_lookup = _akber_by_hypothesis(akber_results)

    packets: list[dict[str, Any]] = []
    for hypothesis in hypotheses:
        hypothesis_id = str(hypothesis.get("strategy_hypothesis_id") or "")
        family = _family(hypothesis)
        instrument = _instrument(hypothesis)
        packet = _build_packet(
            hypothesis,
            akber_lookup.get(hypothesis_id, {}),
            _match_market_confirmation(family, market_context),
            _match_technical_context(instrument, technical_context),
            generated_at,
        )
        packets.append(packet)

    repair_queue = []
    for packet in packets:
        for missing in packet.get("missing_inputs", []):
            repair_queue.append({
                "schema_version": SCHEMA_VERSION,
                "repair_request_id": _hash_id([packet["market_confirmation_packet_id"], missing], "qsase-market-confirmation-repair"),
                "generated_at": generated_at,
                "strategy_hypothesis_id": packet.get("strategy_hypothesis_id"),
                "strategy_family": packet.get("strategy_family"),
                "instrument": packet.get("instrument"),
                "missing_input": missing,
                "provider_action_required": f"supply_{missing}",
                "execution_allowed": False,
                "paper_order_created": False,
                "broker_write_allowed": False,
                "live_capital_enabled": False,
            })

    missing_counter = Counter(item["missing_input"] for item in repair_queue)
    complete_count = len([packet for packet in packets if packet["akber_input_complete"]])
    completeness = {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "qsase_akber_input_completeness",
        "generated_at": generated_at,
        "status": "akber_inputs_complete" if packets and complete_count == len(packets) else "akber_inputs_incomplete",
        "read_only": True,
        "research_only": True,
        "proposal_first": True,
        "public_safe": True,
        "command_disabled": True,
        "paper_only": True,
        "packet_count": len(packets),
        "complete_packet_count": complete_count,
        "incomplete_packet_count": len(packets) - complete_count,
        "missing_input_counts": dict(missing_counter),
        "akber_missing_context_count": len(repair_queue),
        "akber_missing_context_packet_count": len([packet for packet in packets if packet.get("missing_inputs")]),
        "router_eligible_missing_context_count": len([packet for packet in packets if packet.get("missing_inputs")]),
        "execution_allowed": False,
        "paper_order_created": False,
        "broker_write_allowed": False,
        "proof_credit_allowed": False,
        "live_capital_enabled": False,
    }

    blockers = []
    if not packets:
        blockers.append("strategy_hypotheses_missing")
    if repair_queue:
        blockers.append("akber_inputs_missing_practical_confirmation")

    payload = {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "qsase_market_confirmation",
        "generated_at": generated_at,
        "status": "qsase_market_confirmation_ready" if not blockers else "qsase_market_confirmation_ready_with_missing_inputs",
        "read_only": True,
        "research_only": True,
        "proposal_first": True,
        "public_safe": True,
        "command_disabled": True,
        "paper_only": True,
        "authority": universal_authority_flags(),
        "authority_flags": AUTHORITY_FLAGS,
        "strategy_hypotheses_ref": f"data/runtime/{STRATEGY_HYPOTHESES_ARTIFACT}",
        "akber_results_ref": f"data/runtime/{AKBER_RESULTS_ARTIFACT}",
        "market_confirmation_context_ref": f"data/runtime/{MARKET_CONFIRMATION_ARTIFACT}",
        "technical_context_ref": f"data/runtime/{TECHNICAL_CONTEXT_ARTIFACT}",
        "packets_path": f"data/runtime/{PACKETS_ARTIFACT}",
        "akber_input_completeness_path": f"data/runtime/{AKBER_COMPLETENESS_ARTIFACT}",
        "repair_queue_path": f"data/runtime/{REPAIR_QUEUE_ARTIFACT}",
        "packet_count": len(packets),
        "complete_packet_count": complete_count,
        "incomplete_packet_count": len(packets) - complete_count,
        "repair_request_count": len(repair_queue),
        "missing_input_counts": dict(missing_counter),
        "akber_missing_context_count": len(repair_queue),
        "blockers": blockers,
        "dashboard_summary": {
            "headline": "Akber inputs need practical confirmation" if repair_queue else "Akber inputs are complete",
            "packet_count": len(packets),
            "complete_packet_count": complete_count,
            "top_missing_inputs": dict(missing_counter.most_common(5)),
            "plain_english_state": "Qadam has strategy hypotheses, but Akber still needs practical market confirmation before anything can pass onward."
            if repair_queue
            else "Akber has the market confirmation fields needed to pass, hold, or veto on evidence.",
        },
        "execution_allowed": False,
        "risk_approval_created": False,
        "paper_order_created_count": 0,
        "broker_write_allowed": False,
        "paperops_handoff_created": False,
        "proof_credit_allowed": False,
        "live_capital_enabled": False,
    }
    return payload, packets, repair_queue, completeness


def validate_market_confirmation(payload: dict[str, Any], packets: list[dict[str, Any]]) -> list[str]:
    errors: list[str] = []
    if payload.get("schema_version") != SCHEMA_VERSION:
        errors.append("schema_version_mismatch")
    if payload.get("artifact_type") != "qsase_market_confirmation":
        errors.append("artifact_type_mismatch")
    if payload.get("packet_count") != len(packets):
        errors.append("packet_count_mismatch")
    if payload.get("read_only") is not True:
        errors.append("read_only_must_be_true")
    for key in ("execution_allowed", "risk_approval_created", "broker_write_allowed", "paperops_handoff_created", "proof_credit_allowed", "live_capital_enabled"):
        if payload.get(key) is not False:
            errors.append(f"{key}_must_be_false")
    if payload.get("paper_order_created_count") != 0:
        errors.append("paper_order_created_count_must_be_zero")
    for packet in packets:
        for field in ("market_confirmation_packet_id", "strategy_hypothesis_id", "inputs", "missing_inputs", "akber_input_complete"):
            if field not in packet:
                errors.append(f"packet_missing_{field}")
        if packet.get("execution_allowed") is not False:
            errors.append("packet_execution_allowed_must_be_false")
        inputs = packet.get("inputs") if isinstance(packet.get("inputs"), dict) else {}
        for required in REQUIRED_INPUTS:
            if required not in inputs:
                errors.append(f"packet_missing_required_input_{required}")
    return sorted(set(errors))


def write_market_confirmation(
    payload: dict[str, Any],
    packets: list[dict[str, Any]],
    repair_queue: list[dict[str, Any]],
    completeness: dict[str, Any],
    settings: Settings | None = None,
) -> dict[str, str]:
    runtime = _runtime_dir(settings)
    primary = runtime / PRIMARY_ARTIFACT
    packets_path = runtime / PACKETS_ARTIFACT
    completeness_path = runtime / AKBER_COMPLETENESS_ARTIFACT
    repair_path = runtime / REPAIR_QUEUE_ARTIFACT
    dashboard = runtime / DASHBOARD_SUMMARY_ARTIFACT
    history = runtime / HISTORY_ARTIFACT
    events = runtime / EVENTS_ARTIFACT

    _write_json(primary, payload)
    _write_jsonl(packets_path, packets)
    _write_json(completeness_path, completeness)
    _write_jsonl(repair_path, repair_queue)
    _write_json(dashboard, payload.get("dashboard_summary", {}))
    _append_jsonl(history, payload)
    _append_jsonl(events, {
        "schema_version": SCHEMA_VERSION,
        "generated_at": payload.get("generated_at"),
        "event": payload.get("status"),
        "packet_count": payload.get("packet_count"),
        "repair_request_count": payload.get("repair_request_count"),
    })
    return {
        "primary": str(primary),
        "packets": str(packets_path),
        "akber_input_completeness": str(completeness_path),
        "repair_queue": str(repair_path),
        "dashboard_summary": str(dashboard),
        "history": str(history),
        "events": str(events),
    }


def build_and_write_market_confirmation(settings: Settings | None = None) -> tuple[dict[str, Any], list[dict[str, Any]], dict[str, str], list[str]]:
    payload, packets, repair_queue, completeness = build_market_confirmation(settings)
    errors = validate_market_confirmation(payload, packets)
    written = write_market_confirmation(payload, packets, repair_queue, completeness, settings)
    return payload, packets, written, errors
