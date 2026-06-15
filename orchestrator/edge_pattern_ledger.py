"""Public-safe edge pattern ledger for Qadam.

This ledger documents how Qadam decides whether source/price pattern
recognition has become a real edge. It is research visibility only: it records
candidate edges, quantum review state, and Telegram-ready summaries, but it
cannot create trades, approve risk, submit orders, or grant performance credit.
"""

from __future__ import annotations

import json
from datetime import date, datetime, timedelta, timezone
from hashlib import sha256
from pathlib import Path
from typing import Any

from orchestrator.config import Settings


EDGE_PATTERN_LEDGER_SCHEMA_VERSION = 1
EDGE_PATTERN_LEDGER_RUNTIME_ARTIFACT = "edge_pattern_ledger.json"
EDGE_PATTERN_LEDGER_HISTORY = "edge_pattern_ledger_history.jsonl"
EDGE_PATTERN_LEDGER_EVENT_LOG = "edge_pattern_ledger_events.jsonl"
EDGE_PATTERN_LEDGER_EVENT_TYPE = "edge_pattern_ledger_recorded"
EDGE_PATTERN_LEDGER_COMPONENT = "edge_pattern_ledger"

EDGE_PATTERN_SPRINT_START_DATE = date(2026, 6, 15)
EDGE_PATTERN_SPRINT_LENGTH_DAYS = 30

EDGE_PATTERN_AUTHORITY_FALSE_FIELDS: tuple[str, ...] = (
    "source_quorum_credit_allowed",
    "trade_candidate_creation_allowed",
    "risk_approval_allowed",
    "execution_allowed",
    "paper_order_allowed",
    "broker_write_allowed",
    "prediction_market_write_allowed",
    "telegram_command_path_enabled",
    "telegram_trade_command_enabled",
    "telegram_live_send_allowed",
    "quantum_job_authority",
    "live_capital_enabled",
    "proof_credit_allowed",
)

EDGE_PATTERN_BOUNDARY = (
    "Edge Pattern Ledger is read-only research documentation. It can document "
    "candidate source/price patterns, edge criteria, quantum non-linear review, "
    "and Telegram-ready summaries, but it cannot create source quorum, trade "
    "candidates, risk approval, paper orders, broker writes, Telegram commands, "
    "prediction-market writes, quantum jobs, live capital, or proof credit."
)

EDGE_CRITERIA = (
    {
        "key": "all_source_price_cross_scan",
        "label": "All sources cross-scanned against all watched prices",
        "explanation": (
            "Every exported Qadam source must be evaluated against each watched "
            "oil, silver, semiconductor, prediction-market, and defence sleeve."
        ),
    },
    {
        "key": "lead_lag_or_divergence",
        "label": "Lead-lag or divergence hypothesis documented",
        "explanation": (
            "Qadam must record what moved first, what price or probability moved "
            "afterward, and what would falsify the relationship."
        ),
    },
    {
        "key": "multi_source_corroboration",
        "label": "Multiple independent source families corroborate it",
        "explanation": (
            "The pattern cannot rely on one feed. It needs independent evidence "
            "from the shared source universe."
        ),
    },
    {
        "key": "llm_adversarial_review",
        "label": "LLM review compresses and challenges the explanation",
        "explanation": (
            "Local and frontier model review must explain why this could be "
            "causal, why it could be noise, and what to watch next."
        ),
    },
    {
        "key": "quantum_nonlinear_review",
        "label": "Quantum non-linear review is complete",
        "explanation": (
            "The quantum layer is a core gate. It must challenge non-linear "
            "scenario sensitivity before a candidate can be treated as an edge."
        ),
    },
    {
        "key": "market_confirmation",
        "label": "Market confirmation or mispricing evidence exists",
        "explanation": (
            "The watched instrument or probability market must show a tradeable "
            "dislocation, momentum shift, or underpriced event probability."
        ),
    },
    {
        "key": "paper_safety_route",
        "label": "Paper route remains guarded",
        "explanation": (
            "Finding an edge only changes research conviction. Paper execution "
            "still needs Qadam risk, sizing, idempotency, and Alpaca Paper gates."
        ),
    },
    {
        "key": "thirty_day_persistence",
        "label": "Observed across the 30-day edge hunt",
        "explanation": (
            "Qadam must track whether the relationship persists, decays, or "
            "inverts during the 30-day pattern-recognition sprint."
        ),
    },
)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _runtime_dir(settings: Settings | None = None) -> Path:
    return Path((settings or Settings.from_env()).runtime_dir)


def edge_pattern_ledger_paths(
    settings: Settings | None = None,
) -> tuple[Path, Path, Path]:
    runtime = _runtime_dir(settings)
    return (
        runtime / EDGE_PATTERN_LEDGER_RUNTIME_ARTIFACT,
        runtime / EDGE_PATTERN_LEDGER_HISTORY,
        runtime / EDGE_PATTERN_LEDGER_EVENT_LOG,
    )


def _parse_datetime(value: Any) -> datetime:
    if not value:
        return datetime.now(timezone.utc)
    text = str(value).replace("Z", "+00:00")
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError:
        return datetime.now(timezone.utc)
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _as_list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def _int(value: Any) -> int:
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0


def _bool(value: Any) -> bool:
    return value is True or str(value).strip().lower() in {"1", "true", "yes", "on"}


def _sprint(generated_at: str) -> dict[str, Any]:
    generated = _parse_datetime(generated_at).date()
    end_date = EDGE_PATTERN_SPRINT_START_DATE + timedelta(days=EDGE_PATTERN_SPRINT_LENGTH_DAYS)
    elapsed = max(0, min(EDGE_PATTERN_SPRINT_LENGTH_DAYS, (generated - EDGE_PATTERN_SPRINT_START_DATE).days + 1))
    remaining = max(0, EDGE_PATTERN_SPRINT_LENGTH_DAYS - elapsed)
    return {
        "status": "active" if generated < end_date else "complete",
        "start_date": EDGE_PATTERN_SPRINT_START_DATE.isoformat(),
        "end_date": end_date.isoformat(),
        "length_days": EDGE_PATTERN_SPRINT_LENGTH_DAYS,
        "day_number": elapsed,
        "days_remaining": remaining,
        "actual_calendar_run": True,
        "backfill_used": False,
        "simulated_time_used": False,
        "purpose": (
            "Spend 30 actual calendar days looking for durable relationships "
            "between all Qadam source activity and the watched prices."
        ),
    }


def _criterion_statuses(
    *,
    edge_tracker: dict[str, Any],
    cognition: dict[str, Any],
    trade_layer: dict[str, Any],
    quantum_oracle: dict[str, Any],
    qctrl_fire_opal_ibm: dict[str, Any],
    sprint: dict[str, Any],
) -> list[dict[str, Any]]:
    source_scan = edge_tracker.get("source_scan", {})
    source_universe = edge_tracker.get("source_universe", {})
    quantum_status = str(quantum_oracle.get("status") or edge_tracker.get("quantum_pattern_review", {}).get("status") or "")
    quantum_mode = str(
        edge_tracker.get("quantum_pattern_review", {}).get("mode")
        or quantum_oracle.get("latest_local_simulation_mode")
        or ""
    )
    fire_opal_status = str(
        qctrl_fire_opal_ibm.get("status")
        or edge_tracker.get("quantum_pattern_review", {}).get("fire_opal_ibm_status")
        or ""
    )
    evidence_count = len(_as_list(cognition.get("evidence_packets")))
    hypothesis_count = len(_as_list(cognition.get("hypotheses")))
    strategy_count = len(_as_list(cognition.get("strategy_lead_packets")))
    market_context_count = _int(cognition.get("market_context", {}).get("packet_count"))
    candidate_count = len(_as_list(trade_layer.get("candidates")))
    blocked_count = len(_as_list(trade_layer.get("blocked")))
    watched_count = _int(edge_tracker.get("watched_instrument_count"))
    statuses = {
        "all_source_price_cross_scan": (
            source_scan.get("mode") == "all_sources_every_sleeve"
            and _int(source_universe.get("source_count")) >= 30
            and _int(source_scan.get("total_source_count")) == _int(source_universe.get("source_count"))
            and watched_count >= 20
        ),
        "lead_lag_or_divergence": hypothesis_count > 0 and evidence_count > 0,
        "multi_source_corroboration": _int(source_scan.get("signal_review_eligible_source_count")) >= 3,
        "llm_adversarial_review": strategy_count > 0 and str(cognition.get("signal_integrity", {}).get("status") or "") == "ok",
        "quantum_nonlinear_review": (
            quantum_status == "ok"
            and bool(quantum_mode)
            and _int(quantum_oracle.get("result_count") or quantum_oracle.get("oracle_result_count")) >= 1
            and fire_opal_status not in {"blocked", "provider_network_error", "not_exported"}
        ),
        "market_confirmation": market_context_count > 0 and (candidate_count > 0 or blocked_count > 0),
        "paper_safety_route": (
            edge_tracker.get("paper_order_allowed") is False
            and edge_tracker.get("broker_write_allowed") is False
            and edge_tracker.get("live_capital_enabled") is False
        ),
        "thirty_day_persistence": _int(sprint.get("day_number")) >= EDGE_PATTERN_SPRINT_LENGTH_DAYS,
    }
    detail_by_key = {
        "all_source_price_cross_scan": f"{source_universe.get('source_count', 0)} sources and {watched_count} watched prices.",
        "lead_lag_or_divergence": f"{hypothesis_count} hypotheses and {evidence_count} evidence packets.",
        "multi_source_corroboration": f"{source_scan.get('signal_review_eligible_source_count', 0)} signal-review eligible sources.",
        "llm_adversarial_review": f"{strategy_count} Strategy Lead packets; Signal Integrity is {cognition.get('signal_integrity', {}).get('status', 'unknown')}.",
        "quantum_nonlinear_review": f"Quantum mode {quantum_mode or 'not exported'}; Fire Opal/IBM status {fire_opal_status or 'not exported'}.",
        "market_confirmation": f"{market_context_count} market context packets; {candidate_count} candidates and {blocked_count} blocked ideas.",
        "paper_safety_route": "Research has no direct paper-order, broker-write, or live-capital authority.",
        "thirty_day_persistence": f"Day {sprint.get('day_number')} of {sprint.get('length_days')}.",
    }
    results: list[dict[str, Any]] = []
    for criterion in EDGE_CRITERIA:
        key = criterion["key"]
        passed = bool(statuses.get(key))
        results.append(
            {
                **criterion,
                "status": "passed" if passed else "observing",
                "passed": passed,
                "detail": detail_by_key.get(key, "not exported"),
            }
        )
    return results


def _pattern_records(
    *,
    edge_tracker: dict[str, Any],
    criteria: list[dict[str, Any]],
    generated_at: str,
) -> list[dict[str, Any]]:
    passed_without_persistence = {
        criterion["key"]
        for criterion in criteria
        if criterion.get("passed") and criterion.get("key") != "thirty_day_persistence"
    }
    source_count = _int(edge_tracker.get("source_universe", {}).get("source_count"))
    records: list[dict[str, Any]] = []
    for sleeve in _as_list(edge_tracker.get("sleeves")):
        if not isinstance(sleeve, dict):
            continue
        instruments = [
            str(instrument.get("symbol"))
            for instrument in _as_list(sleeve.get("watched_instruments"))
            if isinstance(instrument, dict) and instrument.get("symbol")
        ]
        raw = {
            "key": sleeve.get("key"),
            "generated_at": generated_at,
            "source_count": source_count,
            "instruments": instruments,
        }
        record_id = "edge-pattern:" + sha256(json.dumps(raw, sort_keys=True).encode("utf-8")).hexdigest()[:18]
        records.append(
            {
                "pattern_id": record_id,
                "sleeve_key": str(sleeve.get("key") or "unknown"),
                "label": str(sleeve.get("label") or sleeve.get("key") or "Watched sleeve"),
                "status": "candidate_under_observation",
                "edge_stage": "candidate_edge_not_validated",
                "source_application": "all_qadam_sources_cross_scanned_for_this_pattern",
                "source_count": source_count,
                "instrument_symbols": instruments,
                "pattern_question": str(sleeve.get("pattern_question") or ""),
                "current_observation": (
                    "Qadam is looking for whether changes across the full source "
                    "universe repeatedly lead, lag, or diverge from this sleeve's prices."
                ),
                "passed_criteria": sorted(passed_without_persistence),
                "missing_criteria": [
                    criterion["key"]
                    for criterion in criteria
                    if not criterion.get("passed")
                ],
                "quantum_required": True,
                "quantum_role": str(sleeve.get("quantum_role") or "core non-linear review"),
                "llm_role": str(sleeve.get("llm_role") or "explanation and adversarial review"),
                "telegram_notification_allowed": True,
                "trade_candidate_creation_allowed": False,
                "risk_approval_allowed": False,
                "execution_allowed": False,
                "paper_order_allowed": False,
                "broker_write_allowed": False,
                "live_capital_enabled": False,
            }
        )
    return records


def _telegram_summary(
    *,
    sprint: dict[str, Any],
    criteria: list[dict[str, Any]],
    patterns: list[dict[str, Any]],
    edge_state: str,
    quantum_review: dict[str, Any],
) -> dict[str, Any]:
    passed_count = sum(1 for criterion in criteria if criterion.get("passed"))
    body = (
        f"Qadam is on day {sprint['day_number']} of a 30-day edge hunt. It is comparing all "
        f"available source activity with the watched prices for oil, silver, semiconductors, "
        f"prediction markets, and defence stocks. Right now it has {len(patterns)} candidate "
        f"patterns under observation and {passed_count}/{len(criteria)} edge criteria passing, "
        f"but the current state is {edge_state.replace('_', ' ')} rather than a confirmed edge."
        "\n\n"
        f"The quantum layer is part of the core test, not a side note: its current mode is "
        f"{quantum_review.get('mode', 'not exported')} and it is used to challenge whether the "
        "relationship is non-linear, fragile, or just noise. Telegram can summarize the thesis "
        "in plain English, but it cannot approve trades or give Qadam execution authority."
    )
    return {
        "status": "ready_for_review",
        "message_class": "edge_pattern_progress",
        "cadence": "weekly_or_candidate_threshold_crossing",
        "title": "Qadam edge hunt update",
        "body": body,
        "telegram_notification_allowed": True,
        "telegram_live_send_allowed": False,
        "telegram_command_path_enabled": False,
        "boundary": (
            "Telegram edge summaries are outbound explanation only. They cannot "
            "approve, reject, modify, close, or submit trades."
        ),
    }


def build_edge_pattern_ledger(
    *,
    edge_tracker: dict[str, Any],
    cognition: dict[str, Any],
    trade_layer: dict[str, Any],
    quantum_oracle: dict[str, Any],
    qctrl_fire_opal_ibm: dict[str, Any],
    paperops_30_day_operations: dict[str, Any] | None = None,
    generated_at: str | None = None,
) -> dict[str, Any]:
    generated_at = generated_at or _now()
    sprint = _sprint(generated_at)
    criteria = _criterion_statuses(
        edge_tracker=edge_tracker,
        cognition=cognition,
        trade_layer=trade_layer,
        quantum_oracle=quantum_oracle,
        qctrl_fire_opal_ibm=qctrl_fire_opal_ibm,
        sprint=sprint,
    )
    patterns = _pattern_records(
        edge_tracker=edge_tracker,
        criteria=criteria,
        generated_at=generated_at,
    )
    passed_count = sum(1 for criterion in criteria if criterion.get("passed"))
    persistence_passed = any(
        criterion.get("key") == "thirty_day_persistence" and criterion.get("passed")
        for criterion in criteria
    )
    core_passed = all(
        criterion.get("passed")
        for criterion in criteria
        if criterion.get("key")
        in {
            "all_source_price_cross_scan",
            "lead_lag_or_divergence",
            "multi_source_corroboration",
            "llm_adversarial_review",
            "quantum_nonlinear_review",
            "market_confirmation",
            "paper_safety_route",
        }
    )
    edge_state = "validated_edge" if core_passed and persistence_passed else (
        "candidate_edges_under_observation" if core_passed else "edge_hunt_active"
    )
    quantum_review = {
        "status": edge_tracker.get("quantum_pattern_review", {}).get("status") or quantum_oracle.get("status") or "not_run",
        "mode": edge_tracker.get("quantum_pattern_review", {}).get("mode") or quantum_oracle.get("latest_local_simulation_mode") or "not_run",
        "backend": edge_tracker.get("quantum_pattern_review", {}).get("backend") or quantum_oracle.get("latest_backend") or "classical_fallback",
        "fire_opal_ibm_status": qctrl_fire_opal_ibm.get("status") or edge_tracker.get("quantum_pattern_review", {}).get("fire_opal_ibm_status") or "not_exported",
        "core_gate": True,
        "required_before_validated_edge": True,
        "role": (
            "Quantum review challenges non-linear sensitivity for every candidate "
            "pattern before Qadam may call it an edge."
        ),
    }
    ledger = {
        "schema_version": EDGE_PATTERN_LEDGER_SCHEMA_VERSION,
        "artifact_type": "edge_pattern_ledger",
        "artifact_id": "edge-pattern-ledger:latest",
        "generated_at": generated_at,
        "status": edge_state,
        "public_safe": True,
        "sprint": sprint,
        "purpose": (
            "Document whether Qadam has found an edge by tracking relationships "
            "between all data-source activity and the watched market prices."
        ),
        "edge_definition": (
            "Qadam has found an edge only when a source/price relationship is "
            "documented, corroborated, challenged by LLMs, reviewed by the "
            "quantum non-linear gate, confirmed by market evidence, and observed "
            "through the 30-day sprint without breaking paper-safety rules."
        ),
        "criteria": criteria,
        "criterion_count": len(criteria),
        "passed_criterion_count": passed_count,
        "candidate_pattern_count": len(patterns),
        "validated_edge_count": 1 if edge_state == "validated_edge" else 0,
        "patterns": patterns,
        "quantum_review": quantum_review,
        "llm_review": {
            "status": "active" if _as_list(cognition.get("hypotheses")) else "waiting",
            "hypothesis_count": len(_as_list(cognition.get("hypotheses"))),
            "evidence_packet_count": len(_as_list(cognition.get("evidence_packets"))),
            "strategy_lead_packet_count": len(_as_list(cognition.get("strategy_lead_packets"))),
            "signal_integrity_status": str(cognition.get("signal_integrity", {}).get("status") or "pending"),
            "role": "LLMs explain, compress, rank, and attack the pattern thesis before risk review.",
        },
        "source_price_scope": {
            "source_count": _int(edge_tracker.get("source_universe", {}).get("source_count")),
            "source_mode": edge_tracker.get("source_scan", {}).get("mode"),
            "watched_instrument_count": _int(edge_tracker.get("watched_instrument_count")),
            "symbols": edge_tracker.get("market_price_watch", {}).get("symbols", []),
        },
        "paperops_context": {
            "status": (paperops_30_day_operations or {}).get("status", "not_exported"),
            "cycle_status": (paperops_30_day_operations or {}).get("paper_operational_cycle_status")
            or (paperops_30_day_operations or {}).get("cycle_status")
            or "not_exported",
            "active_day_number": (paperops_30_day_operations or {}).get("active_day_number"),
            "live_capital_enabled": False,
        },
        "telegram_summary": _telegram_summary(
            sprint=sprint,
            criteria=criteria,
            patterns=patterns,
            edge_state=edge_state,
            quantum_review=quantum_review,
        ),
        "documentation_routes": {
            "runtime_artifact": f"data/runtime/{EDGE_PATTERN_LEDGER_RUNTIME_ARTIFACT}",
            "history": f"data/runtime/{EDGE_PATTERN_LEDGER_HISTORY}",
            "event_log": f"data/runtime/{EDGE_PATTERN_LEDGER_EVENT_LOG}",
            "dashboard_surface": "Overview Edge Tracker",
            "telegram_surface": "outbound review-only edge summary",
        },
        "boundary": EDGE_PATTERN_BOUNDARY,
    }
    for field in EDGE_PATTERN_AUTHORITY_FALSE_FIELDS:
        ledger[field] = False
    return ledger


def validate_edge_pattern_ledger(payload: dict[str, Any]) -> None:
    required = {
        "schema_version",
        "artifact_type",
        "artifact_id",
        "generated_at",
        "status",
        "public_safe",
        "sprint",
        "edge_definition",
        "criteria",
        "criterion_count",
        "passed_criterion_count",
        "candidate_pattern_count",
        "validated_edge_count",
        "patterns",
        "quantum_review",
        "llm_review",
        "source_price_scope",
        "telegram_summary",
        "documentation_routes",
        "boundary",
        *EDGE_PATTERN_AUTHORITY_FALSE_FIELDS,
    }
    missing = sorted(required - set(payload))
    if missing:
        raise ValueError(f"edge pattern ledger missing fields: {missing}")
    if payload.get("schema_version") != EDGE_PATTERN_LEDGER_SCHEMA_VERSION:
        raise ValueError("edge pattern ledger schema mismatch")
    if payload.get("artifact_type") != "edge_pattern_ledger":
        raise ValueError("edge pattern ledger artifact type mismatch")
    if payload.get("public_safe") is not True:
        raise ValueError("edge pattern ledger must be public-safe")
    if payload.get("status") not in {
        "edge_hunt_active",
        "candidate_edges_under_observation",
        "validated_edge",
    }:
        raise ValueError("edge pattern ledger status invalid")
    for field in EDGE_PATTERN_AUTHORITY_FALSE_FIELDS:
        if payload.get(field) is not False:
            raise ValueError(f"edge pattern ledger must keep {field}=False")
    sprint = payload.get("sprint")
    if not isinstance(sprint, dict) or sprint.get("length_days") != EDGE_PATTERN_SPRINT_LENGTH_DAYS:
        raise ValueError("edge pattern ledger sprint invalid")
    if sprint.get("actual_calendar_run") is not True:
        raise ValueError("edge pattern ledger must use actual calendar time")
    if sprint.get("backfill_used") is not False or sprint.get("simulated_time_used") is not False:
        raise ValueError("edge pattern ledger cannot backfill or simulate time")
    criteria = payload.get("criteria")
    if not isinstance(criteria, list) or len(criteria) != len(EDGE_CRITERIA):
        raise ValueError("edge pattern ledger criteria mismatch")
    criterion_keys = {str(criterion.get("key")) for criterion in criteria if isinstance(criterion, dict)}
    expected_keys = {criterion["key"] for criterion in EDGE_CRITERIA}
    if criterion_keys != expected_keys:
        raise ValueError("edge pattern ledger criterion keys mismatch")
    if not any(
        criterion.get("key") == "quantum_nonlinear_review"
        and criterion.get("label") == "Quantum non-linear review is complete"
        for criterion in criteria
        if isinstance(criterion, dict)
    ):
        raise ValueError("edge pattern ledger quantum criterion missing")
    quantum_review = payload.get("quantum_review")
    if not isinstance(quantum_review, dict) or quantum_review.get("core_gate") is not True:
        raise ValueError("edge pattern ledger quantum review must be core gate")
    patterns = payload.get("patterns")
    if not isinstance(patterns, list) or len(patterns) != 5:
        raise ValueError("edge pattern ledger must expose five candidate pattern sleeves")
    for pattern in patterns:
        if not isinstance(pattern, dict):
            raise ValueError("edge pattern record must be a dict")
        if pattern.get("source_application") != "all_qadam_sources_cross_scanned_for_this_pattern":
            raise ValueError("edge pattern record must use all sources")
        if pattern.get("quantum_required") is not True:
            raise ValueError("edge pattern record must require quantum review")
        for field in (
            "trade_candidate_creation_allowed",
            "risk_approval_allowed",
            "execution_allowed",
            "paper_order_allowed",
            "broker_write_allowed",
            "live_capital_enabled",
        ):
            if pattern.get(field) is not False:
                raise ValueError(f"edge pattern record authority leak: {field}")
    telegram = payload.get("telegram_summary")
    if not isinstance(telegram, dict):
        raise ValueError("edge pattern ledger telegram summary missing")
    if telegram.get("telegram_command_path_enabled") is not False:
        raise ValueError("edge pattern telegram summary command path enabled")
    if telegram.get("telegram_live_send_allowed") is not False:
        raise ValueError("edge pattern telegram summary live send allowed")
    if "quantum" not in str(telegram.get("body", "")).lower():
        raise ValueError("edge pattern telegram summary must mention quantum")
    if "read-only research documentation" not in str(payload.get("boundary", "")):
        raise ValueError("edge pattern ledger boundary weak")


def write_edge_pattern_ledger(
    payload: dict[str, Any],
    settings: Settings | None = None,
) -> dict[str, Any]:
    validate_edge_pattern_ledger(payload)
    output_path, history_path, event_path = edge_pattern_ledger_paths(settings)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    with history_path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(payload, sort_keys=True) + "\n")
    event = {
        "schema_version": EDGE_PATTERN_LEDGER_SCHEMA_VERSION,
        "event_type": EDGE_PATTERN_LEDGER_EVENT_TYPE,
        "component": EDGE_PATTERN_LEDGER_COMPONENT,
        "created_at": payload.get("generated_at") or _now(),
        "status": payload.get("status"),
        "sprint_day_number": payload.get("sprint", {}).get("day_number"),
        "candidate_pattern_count": payload.get("candidate_pattern_count"),
        "validated_edge_count": payload.get("validated_edge_count"),
        "quantum_core_gate": payload.get("quantum_review", {}).get("core_gate") is True,
        "telegram_summary_status": payload.get("telegram_summary", {}).get("status"),
        "authority_leak_count": sum(
            1 for field in EDGE_PATTERN_AUTHORITY_FALSE_FIELDS if payload.get(field) is not False
        ),
        "public_safe": True,
        "boundary": EDGE_PATTERN_BOUNDARY,
    }
    with event_path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(event, sort_keys=True) + "\n")
    return {
        "output_path": str(output_path),
        "history_path": str(history_path),
        "event_log_path": str(event_path),
    }
