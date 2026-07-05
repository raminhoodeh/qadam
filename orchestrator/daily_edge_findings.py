"""Daily Edge Findings artifact for Qadam.

This artifact turns the current edge ledger into a daily, public-safe research
brief. It documents observed source/price pattern recognition, quantum review,
and possible strategy implications without creating trades, approving risk,
submitting orders, or sending Telegram messages live.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from hashlib import sha256
from pathlib import Path
from typing import Any

from orchestrator.config import Settings
from orchestrator.edge_pattern_ledger import (
    EDGE_PATTERN_AUTHORITY_FALSE_FIELDS,
    validate_edge_pattern_ledger,
)
from orchestrator.quantum_mandatory_review_gate import (
    build_quantum_mandatory_review_gate,
    validate_quantum_mandatory_review_gate,
)


DAILY_EDGE_FINDINGS_SCHEMA_VERSION = 2
DAILY_EDGE_FINDINGS_RUNTIME_ARTIFACT = "daily_edge_findings_brief.json"
DAILY_EDGE_FINDINGS_HISTORY = "daily_edge_findings_brief_history.jsonl"
DAILY_EDGE_FINDINGS_EVENT_LOG = "daily_edge_findings_brief_events.jsonl"
DAILY_EDGE_FINDINGS_EVENT_TYPE = "daily_edge_findings_brief_recorded"
DAILY_EDGE_FINDINGS_COMPONENT = "daily_edge_findings_brief"

DAILY_EDGE_FINDINGS_REQUIRED_MIN_SOURCE_COUNT = 30
DAILY_EDGE_FINDINGS_REQUIRED_MIN_WATCHED_INSTRUMENT_COUNT = 20
DAILY_EDGE_FINDINGS_REQUIRED_MIN_PATTERN_COUNT = 5

DAILY_EDGE_FINDINGS_BOUNDARY = (
    "Daily Edge Findings Brief is read-only research documentation. It can "
    "summarize source/price pattern observations, quantum non-linear review, "
    "LLM review, and proposed strategy updates, but it cannot create source "
    "quorum, trade candidates, risk approval, paper orders, broker writes, "
    "Telegram commands, Telegram live sends, prediction-market writes, quantum "
    "jobs, live capital, or proof credit."
)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


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


def _runtime_dir(settings: Settings | None = None) -> Path:
    return Path((settings or Settings.from_env()).runtime_dir)


def daily_edge_findings_paths(
    settings: Settings | None = None,
) -> tuple[Path, Path, Path]:
    runtime = _runtime_dir(settings)
    return (
        runtime / DAILY_EDGE_FINDINGS_RUNTIME_ARTIFACT,
        runtime / DAILY_EDGE_FINDINGS_HISTORY,
        runtime / DAILY_EDGE_FINDINGS_EVENT_LOG,
    )


def _as_list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def _as_dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _int(value: Any) -> int:
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0


def _float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _slug(value: Any) -> str:
    return str(value or "").strip().replace(" ", "_").lower() or "unknown"


def _sleeve_by_key(edge_tracker: dict[str, Any]) -> dict[str, dict[str, Any]]:
    sleeves: dict[str, dict[str, Any]] = {}
    for sleeve in _as_list(edge_tracker.get("sleeves")):
        if isinstance(sleeve, dict):
            key = _slug(sleeve.get("key"))
            sleeves[key] = sleeve
    return sleeves


def _symbols_for_sleeve(sleeve: dict[str, Any], pattern: dict[str, Any]) -> list[str]:
    if pattern.get("instrument_symbols"):
        return [str(symbol) for symbol in _as_list(pattern.get("instrument_symbols")) if symbol]
    symbols: list[str] = []
    for instrument in _as_list(sleeve.get("watched_instruments")):
        if isinstance(instrument, dict) and instrument.get("symbol"):
            symbols.append(str(instrument["symbol"]))
    return symbols


def _source_families_for_sleeve(sleeve: dict[str, Any]) -> list[str]:
    keys = [str(key) for key in _as_list(sleeve.get("primary_lens_source_keys")) if key]
    return keys or ["all_qadam_sources"]


def _confidence(
    *,
    pattern: dict[str, Any],
    quantum_review: dict[str, Any],
    include_quantum: bool,
) -> float:
    passed = set(str(item) for item in _as_list(pattern.get("passed_criteria")))
    if not include_quantum:
        passed.discard("quantum_nonlinear_review")
    score = 0.35 + (0.045 * len(passed))
    if include_quantum and quantum_review.get("status") == "ok" and quantum_review.get("core_gate") is True:
        score += 0.04
    if include_quantum and quantum_review.get("status") != "ok":
        score -= 0.2
    return round(max(0.0, min(0.95, score)), 3)


def _pattern_observation_text(pattern: dict[str, Any]) -> str:
    label = str(pattern.get("label") or pattern.get("sleeve_key") or "This sleeve")
    return (
        f"{label} is being tested for repeated lead-lag, divergence, and "
        "confirmation relationships between the full source universe and the "
        "watched prices or probabilities."
    )


def _pattern_hypothesis_text(pattern: dict[str, Any]) -> str:
    label = str(pattern.get("label") or pattern.get("sleeve_key") or "This sleeve")
    return (
        f"If the same named source families repeatedly appear before {label} "
        "prices or probabilities move, Qadam treats the timing gap as a "
        "candidate edge; if the relationship does not persist, it is treated "
        "as noise."
    )


def _strategy_implication_text(pattern: dict[str, Any]) -> str:
    label = str(pattern.get("label") or pattern.get("sleeve_key") or "this sleeve")
    return (
        f"Keep {label} in the high-priority watchlist for paper-only ranking. "
        "This can influence research conviction only after the guarded "
        "strategy and risk route accepts the evidence."
    )


def _pattern_records(
    *,
    edge_ledger: dict[str, Any],
    edge_tracker: dict[str, Any],
) -> list[dict[str, Any]]:
    sleeves = _sleeve_by_key(edge_tracker)
    quantum_review = _as_dict(edge_ledger.get("quantum_review"))
    source_scope = _as_dict(edge_ledger.get("source_price_scope"))
    source_count = _int(source_scope.get("source_count"))
    records: list[dict[str, Any]] = []
    for pattern in _as_list(edge_ledger.get("patterns")):
        if not isinstance(pattern, dict):
            continue
        sleeve_key = _slug(pattern.get("sleeve_key"))
        sleeve = sleeves.get(sleeve_key, {})
        confidence_before = _confidence(
            pattern=pattern,
            quantum_review=quantum_review,
            include_quantum=False,
        )
        confidence_after = _confidence(
            pattern=pattern,
            quantum_review=quantum_review,
            include_quantum=True,
        )
        record = {
            "pattern_id": pattern.get("pattern_id") or f"daily-edge:{sleeve_key}",
            "sleeve_key": sleeve_key,
            "market_sleeve": str(pattern.get("label") or sleeve.get("label") or sleeve_key),
            "status": "observed_candidate_not_approved",
            "source_families_involved": _source_families_for_sleeve(sleeve),
            "source_application": "all_qadam_sources_scanned_against_this_market_sleeve",
            "source_count": source_count,
            "watched_market_symbols": _symbols_for_sleeve(sleeve, pattern),
            "observed_relationship": _pattern_observation_text(pattern),
            "lead_lag_or_divergence_hypothesis": _pattern_hypothesis_text(pattern),
            "passed_criteria": _as_list(pattern.get("passed_criteria")),
            "missing_criteria": _as_list(pattern.get("missing_criteria")),
            "confidence_before_quantum_review": confidence_before,
            "quantum_non_linear_review_result": {
                "required": True,
                "status": quantum_review.get("status", "not_run"),
                "mode": quantum_review.get("mode", "not_run"),
                "backend": quantum_review.get("backend", "not_exported"),
                "fire_opal_ibm_status": quantum_review.get(
                    "fire_opal_ibm_status",
                    "not_exported",
                ),
                "core_gate": quantum_review.get("core_gate") is True,
                "finding": (
                    "The quantum layer is a mandatory non-linear challenge. "
                    "It has not converted this observation into approval or "
                    "execution authority."
                ),
            },
            "confidence_after_quantum_review": confidence_after,
            "trading_strategy_implication": _strategy_implication_text(pattern),
            "affects_paper_trade_candidate_ranking": (
                quantum_review.get("status") == "ok"
                and quantum_review.get("core_gate") is True
                and "thirty_day_persistence" in _as_list(pattern.get("missing_criteria"))
            ),
            "telegram_notification_allowed": True,
        }
        for field in EDGE_PATTERN_AUTHORITY_FALSE_FIELDS:
            record[field] = False
        records.append(record)
    return records


def _strategy_updates(
    patterns: list[dict[str, Any]],
    quantum_gate: dict[str, Any],
) -> list[dict[str, Any]]:
    updates: list[dict[str, Any]] = []
    gate_passed = quantum_gate.get("status") == "quantum_review_gate_passed"
    for pattern in patterns:
        raw = {
            "sleeve_key": pattern.get("sleeve_key"),
            "pattern_id": pattern.get("pattern_id"),
            "kind": "daily_edge_strategy_update",
        }
        update_id = "daily-edge-update:" + sha256(
            json.dumps(raw, sort_keys=True).encode("utf-8")
        ).hexdigest()[:18]
        update = {
            "update_id": update_id,
            "status": "proposal_only",
            "sleeve_key": pattern.get("sleeve_key"),
            "market_sleeve": pattern.get("market_sleeve"),
            "quantum_mandatory_review_gate_required": True,
            "quantum_mandatory_review_gate_status": quantum_gate.get("status"),
            "quantum_mandatory_review_gate_passed": gate_passed,
            "quantum_dependency_satisfied": (
                gate_passed
                and pattern.get("quantum_review_dependency_satisfied") is True
            ),
            "proposed_adjustment": "raise_watch_priority_if_persistence_confirms",
            "reason": (
                "The pattern has enough cross-source and quantum-reviewed "
                "evidence to keep it visible, but it still lacks durable "
                "persistence and downstream guarded paper acceptance."
            ),
            "quantum_dependency": (
                "Quantum non-linear review remains mandatory before the "
                "relationship can be treated as validated edge evidence."
            ),
            "expected_portfolio_goal_effect": (
                "Better ranking of larger paper-only opportunities tied to the "
                "GBP 100,000 to GBP 200,000 60-day paper growth target."
            ),
            "rollback_condition": (
                "Demote if the source/price relationship decays, inverts, or "
                "fails the next quantum or LLM adversarial review."
            ),
        }
        for field in EDGE_PATTERN_AUTHORITY_FALSE_FIELDS:
            update[field] = False
        updates.append(update)
    return updates


def _portfolio_goal_alignment(capital: dict[str, Any]) -> dict[str, Any]:
    starting_value = _float(
        capital.get("starting_balance_gbp")
        or capital.get("starting_value_gbp")
        or 100000.0,
        100000.0,
    )
    current_value = _float(
        capital.get("current_balance_gbp")
        or capital.get("source_current_balance")
        or capital.get("source_equity")
        or starting_value,
        starting_value,
    )
    target_value = 200000.0
    progress = 0.0
    if target_value > starting_value:
        progress = (current_value - starting_value) / (target_value - starting_value)
    return {
        "goal": "double paper portfolio value over 60 days",
        "paper_only": True,
        "starting_value_gbp": round(starting_value, 2),
        "current_value_gbp": round(current_value, 2),
        "target_value_gbp": round(target_value, 2),
        "progress_to_double_pct": round(progress * 100, 4),
        "strategy_alignment": (
            "Daily findings may alter watch priority and research conviction, "
            "but paper order creation still requires Qadam strategy, risk, "
            "idempotency, and Alpaca Paper execution gates."
        ),
    }


def _telegram_message(
    *,
    brief_date: str,
    patterns: list[dict[str, Any]],
    quantum_review: dict[str, Any],
    portfolio_goal_alignment: dict[str, Any],
) -> dict[str, Any]:
    pattern_names = ", ".join(str(pattern["market_sleeve"]) for pattern in patterns)
    body = (
        f"Today Qadam reviewed all connected source activity against the markets "
        f"it is watching: {pattern_names}. It has {len(patterns)} candidate "
        "patterns under observation, but none of them is being treated as a "
        "finished edge yet. The useful part is the daily discipline: Qadam is "
        "checking whether named source families repeatedly appear before price "
        "or probability moves, instead of reacting to one-off headlines.\n\n"
        f"The quantum review is a core part of that process. For {brief_date}, "
        f"the quantum layer is recorded as {quantum_review.get('status', 'unknown')} "
        f"using {quantum_review.get('mode', 'not exported')} on "
        f"{quantum_review.get('backend', 'not exported')}. These findings can "
        "refine the paper strategy toward the 60-day portfolio growth goal, but "
        "they cannot approve or place trades by themselves."
    )
    return {
        "status": "ready_for_review",
        "message_class": "daily_edge_findings",
        "cadence": "daily",
        "body": body,
        "portfolio_goal": portfolio_goal_alignment.get("goal"),
        "telegram_notification_allowed": True,
        "telegram_live_send_allowed": False,
        "telegram_command_path_enabled": False,
        "boundary": (
            "This message is outbound review text only. It cannot approve, "
            "reject, modify, close, or submit trades."
        ),
    }


def build_daily_edge_findings_brief(
    *,
    cockpit_status: dict[str, Any],
    generated_at: str | None = None,
) -> dict[str, Any]:
    generated_at = generated_at or _now()
    generated = _parse_datetime(generated_at)
    edge_ledger = _as_dict(cockpit_status.get("edge_pattern_ledger"))
    validate_edge_pattern_ledger(edge_ledger)
    edge_tracker = _as_dict(cockpit_status.get("edge_tracker"))
    quantum_review = _as_dict(edge_ledger.get("quantum_review"))
    quantum_gate = build_quantum_mandatory_review_gate(
        edge_ledger=edge_ledger,
        generated_at=generated_at,
    )
    validate_quantum_mandatory_review_gate(quantum_gate)
    source_scope = _as_dict(edge_ledger.get("source_price_scope"))
    patterns = _pattern_records(edge_ledger=edge_ledger, edge_tracker=edge_tracker)
    decisions_by_pattern = {
        str(decision.get("pattern_id")): decision
        for decision in _as_list(quantum_gate.get("pattern_gate_decisions"))
        if isinstance(decision, dict)
    }
    for pattern in patterns:
        decision = decisions_by_pattern.get(str(pattern.get("pattern_id")), {})
        pattern["quantum_mandatory_review_gate_status"] = quantum_gate.get("status")
        pattern["quantum_review_dependency_satisfied"] = (
            decision.get("dependency_satisfied") is True
        )
        pattern["quantum_review_gate_decision"] = decision.get(
            "status",
            "blocked_pending_quantum_review",
        )
        if decision.get("dependency_satisfied") is not True:
            pattern["affects_paper_trade_candidate_ranking"] = False
    strategy_updates = _strategy_updates(patterns, quantum_gate)
    portfolio_goal_alignment = _portfolio_goal_alignment(_as_dict(cockpit_status.get("capital")))
    source_count = _int(source_scope.get("source_count"))
    watched_count = _int(source_scope.get("watched_instrument_count"))
    candidate_count = _int(edge_ledger.get("candidate_pattern_count"))
    validated_count = _int(edge_ledger.get("validated_edge_count"))
    if source_count < DAILY_EDGE_FINDINGS_REQUIRED_MIN_SOURCE_COUNT or watched_count < DAILY_EDGE_FINDINGS_REQUIRED_MIN_WATCHED_INSTRUMENT_COUNT:
        status = "daily_edge_findings_waiting_for_sources"
    elif quantum_gate.get("status") != "quantum_review_gate_passed":
        status = "daily_edge_findings_quantum_degraded"
    else:
        status = "daily_edge_findings_ready_for_review"
    brief = {
        "schema_version": DAILY_EDGE_FINDINGS_SCHEMA_VERSION,
        "artifact_type": "daily_edge_findings_brief",
        "artifact_id": "daily-edge-findings:latest",
        "generated_at": generated_at,
        "brief_date": generated.date().isoformat(),
        "status": status,
        "public_safe": True,
        "source_count": source_count,
        "watched_instrument_count": watched_count,
        "candidate_pattern_count": candidate_count,
        "validated_edge_count": validated_count,
        "quantum_review_status": quantum_review.get("status", "not_run"),
        "quantum_backend": quantum_review.get("backend", "not_exported"),
        "quantum_review": quantum_review,
        "quantum_mandatory_review_gate": quantum_gate,
        "quantum_mandatory_review_gate_status": quantum_gate.get("status"),
        "quantum_mandatory_review_gate_passed": (
            quantum_gate.get("status") == "quantum_review_gate_passed"
        ),
        "edge_ledger_status": edge_ledger.get("status"),
        "criteria": edge_ledger.get("criteria", []),
        "source_price_scope": source_scope,
        "non_linear_pattern_summary": (
            "Quantum review is mandatory for every observed pattern. Today's "
            f"review is {quantum_review.get('status', 'unknown')} using "
            f"{quantum_review.get('mode', 'not exported')} on "
            f"{quantum_review.get('backend', 'not exported')}; patterns remain "
            "candidates until persistence and downstream paper gates pass."
        ),
        "patterns_observed": patterns,
        "patterns_rejected": [],
        "strategy_updates": strategy_updates,
        "portfolio_goal_alignment": portfolio_goal_alignment,
        "telegram_message": _telegram_message(
            brief_date=generated.date().isoformat(),
            patterns=patterns,
            quantum_review=quantum_review,
            portfolio_goal_alignment=portfolio_goal_alignment,
        ),
        "documentation_routes": {
            "runtime_artifact": f"data/runtime/{DAILY_EDGE_FINDINGS_RUNTIME_ARTIFACT}",
            "history": f"data/runtime/{DAILY_EDGE_FINDINGS_HISTORY}",
            "event_log": f"data/runtime/{DAILY_EDGE_FINDINGS_EVENT_LOG}",
            "source_artifact": "data/runtime/edge_pattern_ledger.json",
            "dashboard_surface": "not wired in this stage",
            "telegram_surface": "review-only body, no live send in this stage",
        },
        "boundary": DAILY_EDGE_FINDINGS_BOUNDARY,
    }
    for field in EDGE_PATTERN_AUTHORITY_FALSE_FIELDS:
        brief[field] = False
    return brief


def validate_daily_edge_findings_brief(payload: dict[str, Any]) -> None:
    required = {
        "schema_version",
        "artifact_type",
        "artifact_id",
        "generated_at",
        "brief_date",
        "status",
        "public_safe",
        "source_count",
        "watched_instrument_count",
        "candidate_pattern_count",
        "validated_edge_count",
        "quantum_review_status",
        "quantum_backend",
        "quantum_review",
        "quantum_mandatory_review_gate",
        "quantum_mandatory_review_gate_status",
        "quantum_mandatory_review_gate_passed",
        "edge_ledger_status",
        "criteria",
        "source_price_scope",
        "non_linear_pattern_summary",
        "patterns_observed",
        "patterns_rejected",
        "strategy_updates",
        "portfolio_goal_alignment",
        "telegram_message",
        "documentation_routes",
        "boundary",
        *EDGE_PATTERN_AUTHORITY_FALSE_FIELDS,
    }
    missing = sorted(required - set(payload))
    if missing:
        raise ValueError(f"daily edge findings brief missing fields: {missing}")
    if payload.get("schema_version") != DAILY_EDGE_FINDINGS_SCHEMA_VERSION:
        raise ValueError("daily edge findings brief schema mismatch")
    if payload.get("artifact_type") != "daily_edge_findings_brief":
        raise ValueError("daily edge findings brief artifact type mismatch")
    if payload.get("public_safe") is not True:
        raise ValueError("daily edge findings brief must be public-safe")
    if payload.get("status") not in {
        "daily_edge_findings_ready_for_review",
        "daily_edge_findings_quantum_degraded",
        "daily_edge_findings_waiting_for_sources",
    }:
        raise ValueError("daily edge findings brief status invalid")
    for field in EDGE_PATTERN_AUTHORITY_FALSE_FIELDS:
        if payload.get(field) is not False:
            raise ValueError(f"daily edge findings brief authority leak: {field}")
    source_count = _int(payload.get("source_count"))
    watched_count = _int(payload.get("watched_instrument_count"))
    candidate_count = _int(payload.get("candidate_pattern_count"))
    if source_count < DAILY_EDGE_FINDINGS_REQUIRED_MIN_SOURCE_COUNT:
        raise ValueError("daily edge findings brief source count below contract")
    if watched_count < DAILY_EDGE_FINDINGS_REQUIRED_MIN_WATCHED_INSTRUMENT_COUNT:
        raise ValueError("daily edge findings brief watched instrument count below contract")
    patterns = payload.get("patterns_observed")
    if not isinstance(patterns, list):
        raise ValueError("daily edge findings brief patterns must be a list")
    if len(patterns) != candidate_count:
        raise ValueError("daily edge findings brief pattern count mismatch")
    if len(patterns) < DAILY_EDGE_FINDINGS_REQUIRED_MIN_PATTERN_COUNT:
        raise ValueError("daily edge findings brief needs at least five patterns")
    quantum_review = _as_dict(payload.get("quantum_review"))
    quantum_gate = _as_dict(payload.get("quantum_mandatory_review_gate"))
    validate_quantum_mandatory_review_gate(quantum_gate)
    if payload.get("quantum_mandatory_review_gate_status") != quantum_gate.get("status"):
        raise ValueError("daily edge findings quantum gate status mismatch")
    if payload.get("quantum_mandatory_review_gate_passed") is not (
        quantum_gate.get("status") == "quantum_review_gate_passed"
    ):
        raise ValueError("daily edge findings quantum gate pass flag mismatch")
    if quantum_review.get("core_gate") is not True:
        raise ValueError("daily edge findings brief quantum review must be core gate")
    if quantum_review.get("status") != "ok" and _int(payload.get("validated_edge_count")) > 0:
        raise ValueError("daily edge findings brief validated edge count cannot pass without quantum")
    for pattern in patterns:
        if not isinstance(pattern, dict):
            raise ValueError("daily edge findings pattern must be a dict")
        if pattern.get("source_application") != "all_qadam_sources_scanned_against_this_market_sleeve":
            raise ValueError("daily edge findings pattern must use all sources")
        if pattern.get("quantum_non_linear_review_result", {}).get("required") is not True:
            raise ValueError("daily edge findings pattern must require quantum review")
        if pattern.get("quantum_mandatory_review_gate_status") != quantum_gate.get("status"):
            raise ValueError("daily edge findings pattern quantum gate status mismatch")
        if (
            pattern.get("affects_paper_trade_candidate_ranking") is True
            and pattern.get("quantum_review_dependency_satisfied") is not True
        ):
            raise ValueError("daily edge findings pattern ranking bypasses quantum gate")
        for field in EDGE_PATTERN_AUTHORITY_FALSE_FIELDS:
            if pattern.get(field) is not False:
                raise ValueError(f"daily edge findings pattern authority leak: {field}")
    strategy_updates = payload.get("strategy_updates")
    if not isinstance(strategy_updates, list) or len(strategy_updates) != len(patterns):
        raise ValueError("daily edge findings strategy update count mismatch")
    for update in strategy_updates:
        if not isinstance(update, dict):
            raise ValueError("daily edge findings strategy update must be a dict")
        if update.get("status") != "proposal_only":
            raise ValueError("daily edge findings strategy update must be proposal only")
        if update.get("quantum_mandatory_review_gate_required") is not True:
            raise ValueError("daily edge findings strategy update must require quantum gate")
        if update.get("quantum_mandatory_review_gate_status") != quantum_gate.get("status"):
            raise ValueError("daily edge findings strategy update quantum gate status mismatch")
        if (
            quantum_gate.get("status") == "quantum_review_gate_passed"
            and update.get("quantum_dependency_satisfied") is not True
        ):
            raise ValueError("daily edge findings strategy update lacks quantum dependency")
        if (
            quantum_gate.get("status") != "quantum_review_gate_passed"
            and update.get("quantum_dependency_satisfied") is True
        ):
            raise ValueError("daily edge findings strategy update bypasses blocked quantum gate")
        for field in EDGE_PATTERN_AUTHORITY_FALSE_FIELDS:
            if update.get(field) is not False:
                raise ValueError(f"daily edge findings strategy update authority leak: {field}")
    telegram = payload.get("telegram_message")
    if not isinstance(telegram, dict):
        raise ValueError("daily edge findings telegram message missing")
    if telegram.get("telegram_command_path_enabled") is not False:
        raise ValueError("daily edge findings telegram command path enabled")
    if telegram.get("telegram_live_send_allowed") is not False:
        raise ValueError("daily edge findings telegram live send allowed")
    if "quantum" not in str(telegram.get("body", "")).lower():
        raise ValueError("daily edge findings telegram message must mention quantum")
    if "read-only research documentation" not in str(payload.get("boundary", "")):
        raise ValueError("daily edge findings boundary weak")


def write_daily_edge_findings_brief(
    payload: dict[str, Any],
    settings: Settings | None = None,
) -> dict[str, Any]:
    validate_daily_edge_findings_brief(payload)
    output_path, history_path, event_path = daily_edge_findings_paths(settings)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    with history_path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(payload, sort_keys=True) + "\n")
    event = {
        "schema_version": DAILY_EDGE_FINDINGS_SCHEMA_VERSION,
        "event_type": DAILY_EDGE_FINDINGS_EVENT_TYPE,
        "component": DAILY_EDGE_FINDINGS_COMPONENT,
        "created_at": payload.get("generated_at") or _now(),
        "brief_date": payload.get("brief_date"),
        "status": payload.get("status"),
        "source_count": payload.get("source_count"),
        "watched_instrument_count": payload.get("watched_instrument_count"),
        "candidate_pattern_count": payload.get("candidate_pattern_count"),
        "validated_edge_count": payload.get("validated_edge_count"),
        "quantum_review_status": payload.get("quantum_review_status"),
        "quantum_backend": payload.get("quantum_backend"),
        "quantum_mandatory_review_gate_status": payload.get(
            "quantum_mandatory_review_gate_status"
        ),
        "quantum_mandatory_review_gate_passed": payload.get(
            "quantum_mandatory_review_gate_passed"
        )
        is True,
        "telegram_message_status": payload.get("telegram_message", {}).get("status"),
        "authority_leak_count": sum(
            1 for field in EDGE_PATTERN_AUTHORITY_FALSE_FIELDS if payload.get(field) is not False
        ),
        "public_safe": True,
        "boundary": DAILY_EDGE_FINDINGS_BOUNDARY,
    }
    with event_path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(event, sort_keys=True) + "\n")
    return {
        "output_path": str(output_path),
        "history_path": str(history_path),
        "event_log_path": str(event_path),
    }
