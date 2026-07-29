"""Twice-daily Telegram learning brief for Qadam's edge loop.

Stage 6A turns current edge findings into a plain-language Telegram-ready
learning note. It is outbound-only and never gains command, trading, broker,
strategy-mutation, quantum-provider, or live-capital authority.
"""

from __future__ import annotations

from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
import fcntl
from hashlib import sha256
import json
from pathlib import Path
from typing import Any
import urllib.error
import urllib.parse
import urllib.request

from orchestrator.config import Settings
from orchestrator.daily_edge_findings import validate_daily_edge_findings_brief
from orchestrator.event_log import EventLog
from orchestrator.promotion_gates import validate_promotion_gates
from orchestrator.qadam_research_programme_state import (
    build_research_programme_state,
    validate_research_programme_state,
)
from orchestrator.secrets import secret_status, secret_value
from orchestrator.telegram_comms import FORBIDDEN_TELEGRAM_TEXT
from orchestrator.telegram_human_brief import TELEGRAM_HUMAN_BRIEF_FALSE_FIELDS
from orchestrator.telegram_message_quality import (
    telegram_human_message_style,
    telegram_message_fingerprint,
    telegram_message_specificity,
)


DAILY_TELEGRAM_LEARNING_BRIEF_SCHEMA_VERSION = 3
DAILY_TELEGRAM_LEARNING_BRIEF_RUNTIME_ARTIFACT = "daily_telegram_learning_brief.json"
DAILY_TELEGRAM_LEARNING_BRIEF_HISTORY = "daily_telegram_learning_brief_history.jsonl"
DAILY_TELEGRAM_LEARNING_BRIEF_EVENT_LOG = "daily_telegram_learning_brief_events.jsonl"
DAILY_TELEGRAM_LEARNING_BRIEF_EVENT_TYPE = "daily_telegram_learning_brief_recorded"
DAILY_TELEGRAM_LEARNING_BRIEF_COMPONENT = "daily_telegram_learning_brief"
DAILY_TELEGRAM_CONTENT_POLICY_VERSION = "stateful_sections.v1"
DAILY_TELEGRAM_SECTION_DEDUPE_DAYS = 7

DAILY_TELEGRAM_LEARNING_BRIEF_STATUSES = {
    "daily_telegram_learning_brief_blocked",
    "daily_telegram_learning_brief_quiet_no_material_change",
    "daily_telegram_learning_brief_dry_run_ready",
    "daily_telegram_learning_brief_ready_to_send",
    "daily_telegram_learning_brief_sent",
    "daily_telegram_learning_brief_failed",
    "daily_telegram_learning_brief_already_sent",
}

DAILY_TELEGRAM_LEARNING_BRIEF_BOUNDARY = (
    "Daily Telegram Learning Brief is an outbound plain-language learning note "
    "for Qadam's twice-daily edge loop. It can explain source/price patterns, quantum "
    "review, and proposed learning implications, but it cannot create trade "
    "candidates, approve risk, approve execution, submit or close broker orders, "
    "handle Telegram commands, call quantum providers, mutate strategy, expose "
    "secrets or chat ids, grant proof credit, deploy code, or enable live capital."
)

PATTERN_QUALITATIVE_FOCUS = {
    "oil": "shipping/GPS/fire/flight vs CL=F, BZ=F, USO and XLE",
    "silver": "rates, trade and mining flow vs SI=F, SLV, SIL and PAAS",
    "semiconductors": (
        "export/news, filings, patents, GitHub and transport vs SMH, SOXX, NVDA, AMD, TSM and ASML"
    ),
    "prediction_markets": "Polymarket/Kalshi odds vs news/social/conflict",
    "defence": "conflict, maritime/flight, GPS and filings vs ITA, XAR, LMT, RTX and NOC",
}

PATTERN_TELEGRAM_LABELS = {
    "Physical disruption pressure across crude-oil proxies": (
        "physical-disruption signals versus CL=F, USO and XLE"
    ),
    "Policy and innovation pressure across semiconductor assets": (
        "policy and innovation signals versus SMH, SOXX and NVDA"
    ),
    "Macro liquidity pressure across silver proxies": (
        "macro-liquidity signals versus SI=F, SLV and SIL"
    ),
    "Geopolitical repricing pressure across defence assets": (
        "geopolitical evidence versus ITA, XAR and LMT"
    ),
    "Event-market odds diverging from geopolitical evidence": (
        "Kalshi and Polymarket odds versus geopolitical evidence"
    ),
}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _runtime_dir(settings: Settings | None = None) -> Path:
    return Path((settings or Settings.from_env()).runtime_dir)


def daily_telegram_learning_brief_paths(
    settings: Settings | None = None,
) -> tuple[Path, Path, Path]:
    runtime = _runtime_dir(settings)
    return (
        runtime / DAILY_TELEGRAM_LEARNING_BRIEF_RUNTIME_ARTIFACT,
        runtime / DAILY_TELEGRAM_LEARNING_BRIEF_HISTORY,
        runtime / DAILY_TELEGRAM_LEARNING_BRIEF_EVENT_LOG,
    )


def _delivery_path(settings: Settings) -> Path:
    path = _runtime_dir(settings) / "telegram-deliveries.jsonl"
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


@contextmanager
def _delivery_lock(settings: Settings):
    path = _runtime_dir(settings) / ".daily_telegram_learning_brief.lock"
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a+", encoding="utf-8") as handle:
        fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
        try:
            yield
        finally:
            fcntl.flock(handle.fileno(), fcntl.LOCK_UN)


def _sent_delivery_keys(settings: Settings) -> set[str]:
    path = _delivery_path(settings)
    if not path.exists():
        return set()
    keys: set[str] = set()
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            stripped = line.strip()
            if not stripped:
                continue
            try:
                payload = json.loads(stripped)
            except json.JSONDecodeError:
                continue
            if (
                isinstance(payload, dict)
                and payload.get("message_class") == "daily_telegram_learning_brief"
                and payload.get("target") == "group"
                and payload.get("status") == "sent"
            ):
                key = str(payload.get("delivery_key") or "")
                if key:
                    keys.add(key)
    return keys


def _archive_delivery(settings: Settings, payload: dict[str, Any]) -> None:
    safe_payload = {
        "schema_version": DAILY_TELEGRAM_LEARNING_BRIEF_SCHEMA_VERSION,
        "created_at": payload.get("created_at") or _now(),
        "target": "group",
        "status": payload.get("status", "unknown"),
        "message_class": "daily_telegram_learning_brief",
        "delivery_key": payload.get("delivery_key"),
        "brief_slot": payload.get("brief_slot"),
        "telegram_message_id": payload.get("telegram_message_id"),
        "failure_category": payload.get("failure_category"),
        "send_requested": payload.get("send_requested") is True,
        "live_send_attempted": payload.get("live_send_attempted") is True,
        "bot_token_exposed": False,
        "chat_id_exposed": False,
        "raw_provider_response_persisted": False,
        "boundary": DAILY_TELEGRAM_LEARNING_BRIEF_BOUNDARY,
    }
    with _delivery_path(settings).open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(safe_payload, sort_keys=True) + "\n")


def _telegram_send(token: str, chat_id: str, text: str) -> dict[str, Any]:
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    data = urllib.parse.urlencode(
        {
            "chat_id": chat_id,
            "text": text,
            "disable_web_page_preview": "true",
        }
    ).encode("utf-8")
    request = urllib.request.Request(url, data=data, method="POST")
    with urllib.request.urlopen(request, timeout=20) as response:
        payload = json.loads(response.read().decode("utf-8"))
    return payload if isinstance(payload, dict) else {}


def _int(value: Any) -> int:
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0


def _float(value: Any, default: float = 0.0) -> float:
    try:
        if value is None or value == "":
            return default
        return float(value)
    except (TypeError, ValueError):
        return default


def _safe_text(title: str, body: str) -> bool:
    text = f"{title}\n{body}"
    return all(not pattern.search(text) for pattern in FORBIDDEN_TELEGRAM_TEXT)


def daily_telegram_learning_delivery_key(brief_date: str, brief_slot: str) -> str:
    raw = f"qadam:daily_telegram_learning_brief:{brief_date}:{brief_slot}:group"
    return sha256(raw.encode("utf-8")).hexdigest()


def _read_runtime_json(settings: Settings, filename: str) -> dict[str, Any]:
    path = _runtime_dir(settings) / filename
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return payload if isinstance(payload, dict) else {}


def _parse_datetime(value: Any) -> datetime | None:
    text = str(value or "").strip()
    if not text:
        return None
    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _recent_sent_briefs(
    settings: Settings,
    *,
    generated_at: str,
    days: int = DAILY_TELEGRAM_SECTION_DEDUPE_DAYS,
) -> list[dict[str, Any]]:
    history_path = _runtime_dir(settings) / DAILY_TELEGRAM_LEARNING_BRIEF_HISTORY
    if not history_path.is_file():
        return []
    reference = _parse_datetime(generated_at) or datetime.now(timezone.utc)
    cutoff = reference - timedelta(days=days)
    records: list[dict[str, Any]] = []
    try:
        lines = history_path.read_text(encoding="utf-8").splitlines()[-500:]
    except OSError:
        return []
    for line in lines:
        try:
            payload = json.loads(line)
        except json.JSONDecodeError:
            continue
        if not isinstance(payload, dict):
            continue
        if payload.get("live_send_succeeded") is not True:
            continue
        created_at = _parse_datetime(payload.get("generated_at"))
        if created_at is None or created_at < cutoff or created_at > reference:
            continue
        records.append(payload)
    return records


def _content_fingerprint(section_id: str, evidence: Any) -> str:
    encoded = json.dumps(
        {"section_id": section_id, "evidence": evidence},
        sort_keys=True,
        separators=(",", ":"),
        default=str,
    ).encode("utf-8")
    return sha256(encoded).hexdigest()


def _section_was_recently_sent(
    *,
    section_id: str,
    fingerprint: str,
    text: str,
    recent_sent_briefs: list[dict[str, Any]],
) -> bool:
    for brief in recent_sent_briefs:
        sections = brief.get("content_sections")
        sections = sections if isinstance(sections, list) else []
        if any(
            isinstance(section, dict)
            and section.get("included") is True
            and section.get("section_id") == section_id
            and section.get("fingerprint") == fingerprint
            for section in sections
        ):
            return True
        legacy_body = str(brief.get("body") or "")
        if text and text in legacy_body:
            return True
    return False


def _build_quantum_hardware_learning(
    *,
    hardware_result: dict[str, Any],
    candidate_validation: dict[str, Any],
) -> dict[str, Any]:
    """Translate verified hardware evidence into a public-safe learning record."""

    base = {
        "evidence_mode": "no_verified_hardware_result",
        "hardware_run_completed": False,
        "hardware_provider": None,
        "hardware_result_generated_at": None,
        "candidate_validation_generated_at": None,
        "represented_score_label_row_count": 0,
        "backend_qubit_count": 0,
        "hardware_candidate_count": 0,
        "feature_pair": [],
        "conditioning_feature": None,
        "opportunity_count": 0,
        "interaction_beats_classical_baseline": False,
        "incremental_net_return_per_opportunity": 0.0,
        "multiple_testing_adjusted_p_value": None,
        "strategy_changed": False,
        "paper_order_created": False,
        "validated_edge_created": False,
        "learning_summary": (
            "No verified IBM hardware learning is available. Quantum evidence must be "
            "described as simulator or classical review until a hardware receipt exists."
        ),
        "public_safe": True,
    }
    if not (
        hardware_result.get("hardware_experiment_completed") is True
        and str(hardware_result.get("provider_status") or "").upper() == "SUCCESS"
    ):
        return base

    input_envelope = (
        hardware_result.get("input_envelope")
        if isinstance(hardware_result.get("input_envelope"), dict)
        else {}
    )
    backend_selection = (
        hardware_result.get("backend_selection")
        if isinstance(hardware_result.get("backend_selection"), dict)
        else {}
    )
    candidates = [
        item for item in hardware_result.get("research_candidates", []) if isinstance(item, dict)
    ]
    candidate = candidates[0] if candidates else {}
    methods = [
        item
        for item in hardware_result.get("hardware_method_results", [])
        if isinstance(item, dict)
    ]
    interaction_method = next(
        (item for item in methods if isinstance(item.get("feature_pair"), list)),
        {},
    )
    feature_pair = candidate.get("feature_pair") or interaction_method.get("feature_pair") or []
    feature_pair = [str(item) for item in feature_pair if str(item).strip()][:2]

    base.update(
        {
            "evidence_mode": "ibm_hardware_candidate_awaiting_validation",
            "hardware_run_completed": True,
            "hardware_provider": "IBM Quantum via Q-CTRL Fire Opal",
            "hardware_result_generated_at": hardware_result.get("generated_at"),
            "represented_score_label_row_count": _int(
                input_envelope.get("paired_score_label_row_count")
            ),
            "backend_qubit_count": _int(backend_selection.get("backend_qubit_count")),
            "hardware_candidate_count": _int(
                hardware_result.get("hardware_research_candidate_count")
            ),
            "feature_pair": feature_pair,
            "conditioning_feature": interaction_method.get("state_feature"),
            "learning_summary": (
                "A verified IBM hardware run surfaced a nonlinear research candidate, but "
                "that candidate has not yet completed a separate predictive test against a "
                "matched classical baseline. It is not a trading edge."
            ),
        }
    )

    comparison = (
        candidate_validation.get("comparison")
        if isinstance(candidate_validation.get("comparison"), dict)
        else {}
    )
    verdict = (
        candidate_validation.get("verdict")
        if isinstance(candidate_validation.get("verdict"), dict)
        else {}
    )
    validation_status = str(candidate_validation.get("status") or "")
    if not validation_status.startswith("tested_"):
        return base

    rejected = validation_status == "tested_rejected_no_predictive_value"
    supported = (
        comparison.get("interaction_beats_additive_baseline") is True
        and comparison.get("multiple_testing_significant") is True
        and verdict.get("historical_survivor") is True
    )
    base.update(
        {
            "evidence_mode": (
                "ibm_hardware_candidate_supported"
                if supported
                else "ibm_hardware_candidate_rejected"
                if rejected
                else "ibm_hardware_candidate_tested_inconclusive"
            ),
            "candidate_validation_generated_at": candidate_validation.get("generated_at"),
            "opportunity_count": _int(comparison.get("opportunity_count")),
            "interaction_beats_classical_baseline": (
                comparison.get("interaction_beats_additive_baseline") is True
            ),
            "incremental_net_return_per_opportunity": _float(
                comparison.get("interaction_minus_baseline_mean_net_return_per_opportunity")
            ),
            "multiple_testing_adjusted_p_value": comparison.get(
                "multiple_testing_adjusted_p_value"
            ),
            "strategy_changed": verdict.get("strategy_change_created") is True,
            "paper_order_created": verdict.get("paper_order_created") is True,
            "validated_edge_created": verdict.get("validated_edge_created") is True,
            "learning_summary": str(verdict.get("plain_english") or "").strip(),
        }
    )
    return base


def build_learning_research_snapshot(settings: Settings | None = None) -> dict[str, Any]:
    """Build a public-safe summary from canonical research and decision artifacts."""

    settings = settings or Settings.from_env()
    backtest = _read_runtime_json(settings, "qadam_backtest_results_summary.json")
    patterns = _read_runtime_json(settings, "qadam_pattern_discovery_dashboard.json")
    quantum = _read_runtime_json(settings, "qadam_quantum_review_dashboard.json")
    foundry = _read_runtime_json(settings, "qadam_strategy_foundry_v3_dashboard_summary.json")
    router = _read_runtime_json(settings, "qadam_router_v3_scoreboard.json")
    post_backtest = _read_runtime_json(settings, "qadam_post_backtest_decision.json")
    value_queue = _read_runtime_json(settings, "qadam_value_of_information_queue.json")
    hardware_result = _read_runtime_json(
        settings,
        "qadam_ibm_full_history_experiment_result.json",
    )
    candidate_validation = _read_runtime_json(
        settings,
        "qadam_ibm_hardware_candidate_validation.json",
    )
    quantum_hardware_learning = _build_quantum_hardware_learning(
        hardware_result=hardware_result,
        candidate_validation=candidate_validation,
    )

    qualitative = patterns.get("qualitative_analysis")
    bullets = qualitative.get("bullets", []) if isinstance(qualitative, dict) else []
    ranked_patterns = [row for row in bullets if isinstance(row, dict)]
    ranked_patterns.sort(key=lambda row: _float(row.get("raw_pattern_score")), reverse=True)
    strongest = ranked_patterns[0] if ranked_patterns else {}
    universe = patterns.get("universe") if isinstance(patterns.get("universe"), dict) else {}
    interesting_patterns = [
        {
            "title": row.get("title"),
            "research_score": _float(row.get("raw_pattern_score")),
            "fresh_source_count": _int(row.get("fresh_source_count")),
            "contributing_source_count": _int(row.get("contributing_source_count")),
            "stage": row.get("stage"),
        }
        for row in ranked_patterns[:5]
    ]
    snapshot_generated_at = max(
        str(backtest.get("generated_at") or ""),
        str(patterns.get("generated_at") or ""),
        str(quantum.get("generated_at") or ""),
        str(hardware_result.get("generated_at") or ""),
        str(candidate_validation.get("generated_at") or ""),
        str(value_queue.get("generated_at") or ""),
    )
    programme_state = build_research_programme_state(
        _runtime_dir(settings),
        value_queue,
        generated_at=snapshot_generated_at or _now(),
    )
    validate_research_programme_state(programme_state)
    selected_programme = programme_state.get("selected_programme")
    selected_programme = selected_programme if isinstance(selected_programme, dict) else None
    queue_present = isinstance(value_queue.get("queue"), list) and bool(value_queue.get("queue"))
    next_research_focus = (
        str(selected_programme.get("question") or "").strip() if selected_programme else None
    )

    return {
        "generated_at": snapshot_generated_at,
        "source_count": _int(universe.get("source_count")),
        "instrument_count": _int(universe.get("instrument_count")),
        "candidate_relationship_count": _int(patterns.get("relationship_count")),
        "backtest": {
            "attempted_hypothesis_count": _int(backtest.get("attempted_hypothesis_count")),
            "completed_method_count": _int(backtest.get("completed_method_count")),
            "eligible_group_count": _int(
                backtest.get("eligible_strategy_instrument_horizon_group_count")
            ),
            "raw_significant_result_count": _int(backtest.get("raw_significant_result_count")),
            "adjusted_significant_result_count": _int(
                backtest.get("adjusted_significant_result_count")
            ),
            "validated_edge_count": _int(backtest.get("validated_edge_count")),
            "rejected_result_count": _int(backtest.get("rejected_result_count")),
            "status": backtest.get("status"),
            "why_no_result": backtest.get("why_no_result"),
        },
        "strongest_pattern": {
            "title": strongest.get("title"),
            "research_score": _float(strongest.get("raw_pattern_score")),
            "fresh_source_count": _int(strongest.get("fresh_source_count")),
            "contributing_source_count": _int(strongest.get("contributing_source_count")),
            "stage": strongest.get("stage"),
        },
        "interesting_patterns": interesting_patterns,
        "quantum": {
            "headline": quantum.get("headline"),
            "classical_preferred_count": _int(quantum.get("classical_preferred_count")),
            "strengthened_count": _int(quantum.get("strengthened_count")),
            "quantum_usefulness_score": _float(quantum.get("quantum_usefulness_score")),
        },
        "quantum_hardware_learning": quantum_hardware_learning,
        "strategy_hypothesis_count": _int(foundry.get("hypothesis_count")),
        "paper_order_count": _int(router.get("paper_order_created_count")),
        "research_programme_state": programme_state,
        "next_research_focus": next_research_focus,
        "next_test": (
            next_research_focus
            if next_research_focus
            else None
            if queue_present
            else post_backtest.get("next_test")
        ),
        "public_safe": True,
    }


def _pattern_names(daily_edge_findings: dict[str, Any]) -> str:
    names: list[str] = []
    for pattern in daily_edge_findings.get("patterns_observed", []):
        if not isinstance(pattern, dict):
            continue
        name = str(pattern.get("market_sleeve") or pattern.get("sleeve_key") or "").strip()
        if name and name not in names:
            names.append(name)
        if len(names) >= 4:
            break
    return ", ".join(names) or "the watched markets"


def _pattern_quality_sentence(daily_edge_findings: dict[str, Any]) -> str:
    clauses: list[str] = []
    for pattern in daily_edge_findings.get("patterns_observed", []):
        if not isinstance(pattern, dict):
            continue
        name = str(pattern.get("market_sleeve") or pattern.get("sleeve_key") or "").strip()
        if not name:
            continue
        sleeve_key = str(pattern.get("sleeve_key") or "").strip()
        focus = PATTERN_QUALITATIVE_FOCUS.get(
            sleeve_key,
            "source signals leading market movement",
        )
        clauses.append(f"{name.lower()} {focus}")
        if len(clauses) >= 5:
            break
    if not clauses:
        return f"The pattern work stayed broad across {_pattern_names(daily_edge_findings)}."
    if len(clauses) == 1:
        return f"The recognised candidate was {clauses[0]}."
    return f"The reads: {'; '.join(clauses)}."


def _portfolio_goal(daily_edge_findings: dict[str, Any]) -> dict[str, Any]:
    goal = daily_edge_findings.get("portfolio_goal_alignment")
    return goal if isinstance(goal, dict) else {}


def _quantum_learning_sentence(research_snapshot: dict[str, Any]) -> str:
    learning = research_snapshot.get("quantum_hardware_learning")
    learning = learning if isinstance(learning, dict) else {}
    mode = str(learning.get("evidence_mode") or "no_verified_hardware_result")
    if mode == "ibm_hardware_candidate_rejected":
        opportunity_count = _int(learning.get("opportunity_count"))
        relative_return = abs(_float(learning.get("incremental_net_return_per_opportunity")) * 100)
        return (
            "IBM Quantum testing found a possible interaction between market flow and "
            f"evidence freshness. Across {opportunity_count:,} cost-adjusted opportunities, "
            f"it underperformed the matched classical benchmark by {relative_return:.3f}% "
            "per opportunity and remains excluded from strategy decisions."
        )
    if mode == "ibm_hardware_candidate_supported":
        opportunity_count = _int(learning.get("opportunity_count"))
        relative_return = _float(learning.get("incremental_net_return_per_opportunity")) * 100
        return (
            "IBM Quantum testing identified a nonlinear relationship that outperformed "
            f"the matched classical benchmark across "
            f"{opportunity_count:,} cost-adjusted opportunities by {relative_return:.3f}% "
            "per opportunity. It remains research evidence pending the rest of Qadam's "
            "validation process."
        )
    if mode == "ibm_hardware_candidate_awaiting_validation":
        return (
            "IBM Quantum testing identified one nonlinear relationship. Its predictive "
            "value has not yet been established against a matched classical benchmark."
        )
    if mode == "ibm_hardware_candidate_tested_inconclusive":
        return (
            "IBM Quantum testing produced an inconclusive result against the matched "
            "classical benchmark, so it has no effect on strategy decisions."
        )
    return (
        "Current quantum evidence is limited to classical and simulated analysis, with no "
        "verified IBM Quantum result available for strategy evaluation."
    )


def _compact_answer(value: Any, *, limit: int = 145) -> str:
    text = " ".join(str(value or "").split()).strip()
    if not text:
        return ""
    if len(text) > limit:
        text = text[: limit - 3].rstrip(" ,;:-") + "..."
    if text[-1] not in ".?!":
        text += "."
    return text


def _quantum_result_changed_today(
    research_snapshot: dict[str, Any],
    brief_date: str,
) -> bool:
    learning = research_snapshot.get("quantum_hardware_learning")
    learning = learning if isinstance(learning, dict) else {}
    timestamps = (
        learning.get("hardware_result_generated_at"),
        learning.get("candidate_validation_generated_at"),
    )
    return any(str(value or "").startswith(brief_date) for value in timestamps)


def _pattern_digest_sentence(
    research_snapshot: dict[str, Any],
    candidate_count: int,
) -> str:
    patterns = research_snapshot.get("interesting_patterns")
    patterns = (
        [row for row in patterns if isinstance(row, dict)] if isinstance(patterns, list) else []
    )
    if not patterns:
        return (
            f"Qadam is monitoring {candidate_count} candidate relationships, but no ranked "
            "pattern detail is available for this brief."
        )

    highest_score = patterns[0]
    alternatives = patterns[1:]
    strongest_alternative = max(
        alternatives,
        key=lambda row: (
            _int(row.get("fresh_source_count"))
            / max(1, _int(row.get("contributing_source_count"))),
            _float(row.get("research_score")),
        ),
        default=None,
    )
    selected = [highest_score]
    if strongest_alternative is not None:
        selected.append(strongest_alternative)

    descriptions: list[str] = []
    for row in selected:
        title = str(row.get("title") or "candidate relationship").strip()
        label = PATTERN_TELEGRAM_LABELS.get(title, title[:1].lower() + title[1:])
        descriptions.append(
            f"{label} (research score {_float(row.get('research_score')):.3f}; "
            f"{_int(row.get('fresh_source_count'))}/"
            f"{_int(row.get('contributing_source_count'))} sources fresh)"
        )

    if len(descriptions) == 1:
        return f"The most interesting candidate relationship is {descriptions[0]}."
    return (
        f"The most interesting candidate relationships are {descriptions[0]} and {descriptions[1]}."
    )


def _material_update_sentence(answers: dict[str, Any]) -> str:
    parts = [
        _compact_answer(answers.get("new_evidence_arrived"), limit=120),
        _compact_answer(answers.get("hypothesis_strengthened_or_weakened"), limit=120),
        _compact_answer(answers.get("outcome_matured"), limit=120),
        _compact_answer(answers.get("what_was_rejected"), limit=120),
    ]
    return " ".join(part for part in parts if part)


def _question_as_focus(question: Any) -> str:
    text = " ".join(str(question or "").split()).strip()
    if not text:
        return ""
    if text[-1] not in ".?!":
        text += "?"
    return f'Qadam\'s active research focus is the question, "{text}"'


def _content_section(
    *,
    section_id: str,
    text: str,
    evidence: Any,
    eligible_for_slot: bool,
    recent_sent_briefs: list[dict[str, Any]],
) -> dict[str, Any]:
    fingerprint = _content_fingerprint(section_id, evidence)
    recently_sent = _section_was_recently_sent(
        section_id=section_id,
        fingerprint=fingerprint,
        text=text,
        recent_sent_briefs=recent_sent_briefs,
    )
    included = bool(text) and eligible_for_slot and not recently_sent
    suppression_reason = None
    if not text:
        suppression_reason = "no_current_content"
    elif not eligible_for_slot:
        suppression_reason = "slot_policy"
    elif recently_sent:
        suppression_reason = "unchanged_within_rolling_window"
    return {
        "section_id": section_id,
        "fingerprint": fingerprint,
        "text": text,
        "eligible_for_slot": eligible_for_slot,
        "included": included,
        "suppression_reason": suppression_reason,
    }


def _render_learning_message(
    *,
    daily_edge_findings: dict[str, Any],
    promotion_gates: dict[str, Any],
    material_learning_delta: dict[str, Any] | None = None,
    research_snapshot: dict[str, Any] | None = None,
    brief_slot_label: str = "Current",
    recent_sent_briefs: list[dict[str, Any]] | None = None,
) -> tuple[str, str, dict[str, Any]]:
    del promotion_gates
    research_snapshot = research_snapshot or {}
    recent_sent_briefs = recent_sent_briefs or []
    answers = (material_learning_delta or {}).get("five_part_answer")
    answers = answers if isinstance(answers, dict) else {}

    candidate_count = _int(daily_edge_findings.get("candidate_pattern_count"))
    source_count = _int(daily_edge_findings.get("source_count"))
    instrument_count = _int(daily_edge_findings.get("watched_instrument_count"))
    strategy_count = _int(research_snapshot.get("strategy_hypothesis_count"))
    paper_order_count = _int(research_snapshot.get("paper_order_count"))
    edition = brief_slot_label.lower()
    title = f"Qadam {edition} research brief"
    brief_date = str(daily_edge_findings.get("brief_date") or "")
    material_change = (material_learning_delta or {}).get("material_change") is True

    material_text = _material_update_sentence(answers) if material_change else ""
    material_section = _content_section(
        section_id="material_research_update",
        text=material_text,
        evidence={
            "semantic_hash": (material_learning_delta or {}).get("current_semantic_hash"),
            "answers": answers,
        },
        eligible_for_slot=material_change,
        recent_sent_briefs=recent_sent_briefs,
    )

    pattern_text = _pattern_digest_sentence(research_snapshot, candidate_count)
    pattern_section = _content_section(
        section_id="ranked_pattern_digest",
        text=pattern_text,
        evidence=research_snapshot.get("interesting_patterns"),
        eligible_for_slot=(edition != "evening" or material_change),
        recent_sent_briefs=recent_sent_briefs,
    )

    quantum_learning = research_snapshot.get("quantum_hardware_learning")
    quantum_learning = quantum_learning if isinstance(quantum_learning, dict) else {}
    quantum_section = _content_section(
        section_id="quantum_result",
        text=_quantum_learning_sentence(research_snapshot),
        evidence={
            "evidence_mode": quantum_learning.get("evidence_mode"),
            "hardware_result_generated_at": quantum_learning.get("hardware_result_generated_at"),
            "candidate_validation_generated_at": quantum_learning.get(
                "candidate_validation_generated_at"
            ),
            "opportunity_count": quantum_learning.get("opportunity_count"),
            "incremental_net_return_per_opportunity": quantum_learning.get(
                "incremental_net_return_per_opportunity"
            ),
            "multiple_testing_adjusted_p_value": quantum_learning.get(
                "multiple_testing_adjusted_p_value"
            ),
        },
        eligible_for_slot=(
            edition != "evening" or _quantum_result_changed_today(research_snapshot, brief_date)
        ),
        recent_sent_briefs=recent_sent_briefs,
    )

    programme_state = research_snapshot.get("research_programme_state")
    programme_state = programme_state if isinstance(programme_state, dict) else {}
    selected_programme = programme_state.get("selected_programme")
    selected_programme = selected_programme if isinstance(selected_programme, dict) else None
    focus_text = _question_as_focus(
        selected_programme.get("question") if selected_programme else None
    )
    focus_section = _content_section(
        section_id="active_research_focus",
        text=focus_text,
        evidence={
            "programme_id": (
                selected_programme.get("programme_id") if selected_programme else None
            ),
            "progress_fingerprint": (
                selected_programme.get("progress_fingerprint") if selected_programme else None
            ),
        },
        eligible_for_slot=selected_programme is not None,
        recent_sent_briefs=recent_sent_briefs,
    )

    sections = [material_section, pattern_section, quantum_section, focus_section]
    included_sections = [section for section in sections if section["included"]]
    if edition == "evening":
        change_sentence = (
            "New provider-backed evidence changed the research state today."
            if material_section["included"]
            else "No new provider-backed outcome matured today."
        )
    else:
        change_sentence = (
            "New evidence changed the research state since the previous brief."
            if material_section["included"]
            else "No material research result changed overnight."
        )
    state_sentence = (
        f"Across {source_count} sources and {instrument_count} watched instruments, "
        f"Qadam is tracking {candidate_count} candidate relationships, "
        f"{strategy_count} strategies and {paper_order_count} paper orders."
    )
    first_paragraph = f"{brief_slot_label} research brief. {change_sentence} {state_sentence}"
    included_text = " ".join(section["text"] for section in included_sections)
    body = f"{first_paragraph}\n\n{included_text}" if included_text else first_paragraph
    return (
        title,
        body,
        {
            "content_sections": sections,
            "suppressed_repeated_section_ids": [
                section["section_id"]
                for section in sections
                if section["suppression_reason"] == "unchanged_within_rolling_window"
            ],
            "repeated_section_count": sum(
                section["suppression_reason"] == "unchanged_within_rolling_window"
                for section in sections
            ),
            "quiet_status_only": not included_sections,
            "material_update_included": material_section["included"],
            "pattern_update_included": pattern_section["included"],
            "quantum_update_included": quantum_section["included"],
            "research_focus_included": focus_section["included"],
            "selected_research_programme_id": (
                selected_programme.get("programme_id") if selected_programme else None
            ),
            "selected_research_programme_state": (
                selected_programme.get("state") if selected_programme else None
            ),
        },
    )


def build_daily_telegram_learning_brief(
    *,
    daily_edge_findings: dict[str, Any],
    promotion_gates: dict[str, Any],
    material_learning_delta: dict[str, Any] | None = None,
    settings: Settings | None = None,
    send_requested: bool = False,
    force_delivery_window: bool = False,
    generated_at: str | None = None,
    brief_slot: str = "manual",
    brief_slot_label: str = "Current",
    research_snapshot: dict[str, Any] | None = None,
) -> dict[str, Any]:
    settings = settings or Settings.from_env()
    generated_at = generated_at or _now()
    validate_daily_edge_findings_brief(daily_edge_findings)
    validate_promotion_gates(promotion_gates)
    brief_date = str(daily_edge_findings.get("brief_date") or generated_at[:10])
    material_learning_delta = (
        material_learning_delta
        if isinstance(material_learning_delta, dict)
        and material_learning_delta.get("artifact_type") == "qadam_material_learning_delta"
        else None
    )
    material_hash = str((material_learning_delta or {}).get("current_semantic_hash") or "")
    material_mode = material_learning_delta is not None
    material_change = not material_mode or material_learning_delta.get("material_change") is True
    research_snapshot = research_snapshot or build_learning_research_snapshot(settings)
    delivery_key = daily_telegram_learning_delivery_key(brief_date, brief_slot)
    recent_sent_briefs = _recent_sent_briefs(
        settings,
        generated_at=generated_at,
    )
    title, body, content_metadata = _render_learning_message(
        daily_edge_findings=daily_edge_findings,
        promotion_gates=promotion_gates,
        material_learning_delta=material_learning_delta,
        research_snapshot=research_snapshot,
        brief_slot_label=brief_slot_label,
        recent_sent_briefs=recent_sent_briefs,
    )
    programme_state = research_snapshot.get("research_programme_state")
    programme_state = programme_state if isinstance(programme_state, dict) else {}
    blocked_questions = [
        str(programme.get("question") or "").strip()
        for programme in programme_state.get("programmes", [])
        if isinstance(programme, dict)
        and programme.get("state") == "blocked_external_data"
        and str(programme.get("question") or "").strip()
    ]
    blocked_question_repeated = any(question in body for question in blocked_questions)
    specificity = telegram_message_specificity(title, body)
    style = telegram_human_message_style(title, body)
    fingerprint = telegram_message_fingerprint(title, body)
    message_safe = _safe_text(title, body)
    bot_configured = secret_status("TELEGRAM_BOT_TOKEN", settings).configured
    group_chat_configured = secret_status("TELEGRAM_GROUP_CHAT_ID", settings).configured
    token = secret_value("TELEGRAM_BOT_TOKEN", settings)
    chat_id = secret_value("TELEGRAM_GROUP_CHAT_ID", settings)
    enabled = settings.telegram_daily_learning_brief_enabled
    dry_run = settings.telegram_daily_learning_brief_dry_run
    already_sent = delivery_key in _sent_delivery_keys(settings)
    eligible = (
        settings.mode == "paper"
        and settings.live_capital_enabled is False
        and daily_edge_findings.get("status") == "daily_edge_findings_ready_for_review"
        and promotion_gates.get("status") == "promotion_gates_ready"
        and daily_edge_findings.get("quantum_mandatory_review_gate_passed") is True
        and specificity["status"] == "specific"
        and style["status"] == "human"
        and message_safe
    )
    live_send_allowed = (
        eligible
        and enabled
        and not dry_run
        and bot_configured
        and group_chat_configured
        and not already_sent
    )

    blockers: list[str] = []
    if not eligible:
        blockers.append("daily_learning_brief_not_eligible")
    if daily_edge_findings.get("status") != "daily_edge_findings_ready_for_review":
        blockers.append("daily_edge_findings_not_ready")
    if promotion_gates.get("status") != "promotion_gates_ready":
        blockers.append("promotion_gates_not_ready")
    if daily_edge_findings.get("quantum_mandatory_review_gate_passed") is not True:
        blockers.append("quantum_gate_not_passed")
    if specificity["status"] != "specific":
        blockers.append("telegram_message_not_specific")
    if style["status"] != "human":
        blockers.append("telegram_message_not_human")
    if not message_safe:
        blockers.append("telegram_message_not_safe")
    if not enabled:
        blockers.append("daily_learning_brief_disabled")
    if dry_run:
        blockers.append("daily_learning_brief_dry_run")
    if not bot_configured:
        blockers.append("telegram_bot_token_missing")
    if not group_chat_configured:
        blockers.append("telegram_group_chat_missing")
    status = "daily_telegram_learning_brief_blocked"
    if eligible:
        status = (
            "daily_telegram_learning_brief_dry_run_ready"
            if dry_run
            else "daily_telegram_learning_brief_ready_to_send"
        )
    if already_sent:
        status = "daily_telegram_learning_brief_already_sent"

    live_send_attempted = False
    live_send_succeeded = False
    telegram_message_id: int | None = None
    failure_category: str | None = None
    delivery_retry_status: str | None = None

    if send_requested and live_send_allowed:
        with _delivery_lock(settings):
            if delivery_key in _sent_delivery_keys(settings):
                already_sent = True
                live_send_allowed = False
                status = "daily_telegram_learning_brief_already_sent"
            else:
                live_send_attempted = True
                try:
                    assert token is not None
                    assert chat_id is not None
                    response = _telegram_send(token, chat_id, body)
                    if response.get("ok") is True:
                        live_send_succeeded = True
                        result = response.get("result", {})
                        if isinstance(result, dict) and result.get("message_id") is not None:
                            telegram_message_id = int(result["message_id"])
                        status = "daily_telegram_learning_brief_sent"
                    else:
                        status = "daily_telegram_learning_brief_failed"
                        failure_category = "telegram_api_rejected"
                except Exception as exc:  # noqa: BLE001 - persist sanitized failure only.
                    failure_category = type(exc).__name__
                    if isinstance(exc, (urllib.error.URLError, TimeoutError, OSError)):
                        status = "daily_telegram_learning_brief_ready_to_send"
                        delivery_retry_status = "queued_after_transport_failure"
                    else:
                        status = "daily_telegram_learning_brief_failed"

                _archive_delivery(
                    settings,
                    {
                        "created_at": generated_at,
                        "status": "sent" if live_send_succeeded else "failed",
                        "delivery_key": delivery_key,
                        "brief_slot": brief_slot,
                        "telegram_message_id": telegram_message_id,
                        "failure_category": failure_category,
                        "send_requested": send_requested,
                        "live_send_attempted": live_send_attempted,
                    },
                )

    artifact = {
        "schema_version": DAILY_TELEGRAM_LEARNING_BRIEF_SCHEMA_VERSION,
        "artifact_type": "daily_telegram_learning_brief",
        "artifact_id": f"daily-telegram-learning-brief:{brief_date}:{brief_slot}",
        "stage": "Stage 6A - Twice-Daily Telegram Learning Brief",
        "generated_at": generated_at,
        "brief_date": brief_date,
        "brief_slot": brief_slot,
        "brief_slot_label": brief_slot_label,
        "scheduled_summary": True,
        "status": status,
        "public_safe": True,
        "target": "group",
        "message_class": "daily_telegram_learning_brief",
        "title": title,
        "body": body,
        "paragraph_count": style["paragraph_count"],
        "line_count": style["line_count"],
        "sentence_count": style["sentence_count"],
        "message_fingerprint": fingerprint,
        "message_specificity_status": specificity["status"],
        "message_specificity_score": specificity["score"],
        "message_specificity_reasons": specificity["reasons"],
        "message_human_style_status": style["status"],
        "message_human_style_errors": style["errors"],
        "message_technical_noise_count": style["technical_noise_count"],
        "message_section_header_count": style["section_header_count"],
        "message_safe": message_safe,
        "content_policy_version": DAILY_TELEGRAM_CONTENT_POLICY_VERSION,
        "rolling_section_dedupe_days": DAILY_TELEGRAM_SECTION_DEDUPE_DAYS,
        "recent_sent_brief_count": len(recent_sent_briefs),
        "blocked_question_repeated_without_change": blocked_question_repeated,
        **content_metadata,
        "material_delta_mode": material_mode,
        "material_change": material_change,
        "material_delta_status": (material_learning_delta or {}).get("status"),
        "material_semantic_hash": material_hash or None,
        "notification_candidate_created": eligible and not already_sent,
        "enabled": enabled,
        "dry_run": dry_run,
        "send_requested": send_requested,
        "force_delivery_window": force_delivery_window,
        "already_sent": already_sent,
        "telegram_live_send_allowed": live_send_allowed,
        "live_send_attempted": live_send_attempted,
        "live_send_succeeded": live_send_succeeded,
        "telegram_message_id_present": telegram_message_id is not None,
        "last_delivery_failure_category": failure_category,
        "delivery_retry_status": delivery_retry_status,
        "bot_configured": bot_configured,
        "group_chat_configured": group_chat_configured,
        "delivery_key": delivery_key,
        "research_snapshot": research_snapshot,
        "blockers": sorted(set(blockers)),
        "blocker_count": len(set(blockers)),
        "source_daily_edge_findings_status": daily_edge_findings.get("status"),
        "source_promotion_gates_status": promotion_gates.get("status"),
        "source_count": _int(daily_edge_findings.get("source_count")),
        "watched_instrument_count": _int(daily_edge_findings.get("watched_instrument_count")),
        "candidate_pattern_count": _int(daily_edge_findings.get("candidate_pattern_count")),
        "validated_edge_count": _int(daily_edge_findings.get("validated_edge_count")),
        "quantum_required": True,
        "quantum_review_status": daily_edge_findings.get("quantum_review_status"),
        "quantum_backend": daily_edge_findings.get("quantum_backend"),
        "quantum_gate_status": daily_edge_findings.get("quantum_mandatory_review_gate_status"),
        "quantum_gate_passed": (
            daily_edge_findings.get("quantum_mandatory_review_gate_passed") is True
        ),
        "promotion_gate_decision_count": _int(promotion_gates.get("promotion_gate_decision_count")),
        "promotion_review_ready_count": _int(promotion_gates.get("promotion_review_ready_count")),
        "promotion_gate_passed_count": _int(promotion_gates.get("promotion_gate_passed_count")),
        "promotion_gate_held_count": _int(promotion_gates.get("promotion_gate_held_count")),
        "human_approval_missing_count": _int(promotion_gates.get("human_approval_missing_count")),
        "strategy_learning_applied_count": 0,
        "portfolio_goal_alignment": _portfolio_goal(daily_edge_findings),
        "documentation_routes": {
            "runtime_artifact": f"data/runtime/{DAILY_TELEGRAM_LEARNING_BRIEF_RUNTIME_ARTIFACT}",
            "history": f"data/runtime/{DAILY_TELEGRAM_LEARNING_BRIEF_HISTORY}",
            "event_log": f"data/runtime/{DAILY_TELEGRAM_LEARNING_BRIEF_EVENT_LOG}",
            "source_daily_edge_findings": "data/runtime/daily_edge_findings_brief.json",
            "source_promotion_gates": "data/runtime/promotion_gates.json",
            "source_material_learning_delta": "data/runtime/qadam_material_learning_delta.json",
            "dashboard_surface": "Communications",
        },
        "boundary": DAILY_TELEGRAM_LEARNING_BRIEF_BOUNDARY,
    }
    for field in TELEGRAM_HUMAN_BRIEF_FALSE_FIELDS:
        artifact[field] = False
    return artifact


def validate_daily_telegram_learning_brief(payload: dict[str, Any]) -> None:
    required = {
        "schema_version",
        "artifact_type",
        "artifact_id",
        "stage",
        "generated_at",
        "brief_date",
        "brief_slot",
        "brief_slot_label",
        "scheduled_summary",
        "status",
        "public_safe",
        "target",
        "message_class",
        "title",
        "body",
        "paragraph_count",
        "line_count",
        "sentence_count",
        "message_fingerprint",
        "message_specificity_status",
        "message_specificity_score",
        "message_specificity_reasons",
        "message_human_style_status",
        "message_human_style_errors",
        "message_technical_noise_count",
        "message_section_header_count",
        "message_safe",
        "content_policy_version",
        "rolling_section_dedupe_days",
        "recent_sent_brief_count",
        "blocked_question_repeated_without_change",
        "content_sections",
        "suppressed_repeated_section_ids",
        "repeated_section_count",
        "quiet_status_only",
        "material_update_included",
        "pattern_update_included",
        "quantum_update_included",
        "research_focus_included",
        "selected_research_programme_id",
        "selected_research_programme_state",
        "material_delta_mode",
        "material_change",
        "material_delta_status",
        "material_semantic_hash",
        "notification_candidate_created",
        "enabled",
        "dry_run",
        "send_requested",
        "force_delivery_window",
        "already_sent",
        "telegram_live_send_allowed",
        "live_send_attempted",
        "live_send_succeeded",
        "telegram_message_id_present",
        "last_delivery_failure_category",
        "bot_configured",
        "group_chat_configured",
        "delivery_key",
        "research_snapshot",
        "blockers",
        "blocker_count",
        "source_daily_edge_findings_status",
        "source_promotion_gates_status",
        "source_count",
        "watched_instrument_count",
        "candidate_pattern_count",
        "validated_edge_count",
        "quantum_required",
        "quantum_review_status",
        "quantum_backend",
        "quantum_gate_status",
        "quantum_gate_passed",
        "promotion_gate_decision_count",
        "promotion_review_ready_count",
        "promotion_gate_passed_count",
        "promotion_gate_held_count",
        "human_approval_missing_count",
        "strategy_learning_applied_count",
        "portfolio_goal_alignment",
        "documentation_routes",
        "boundary",
        *TELEGRAM_HUMAN_BRIEF_FALSE_FIELDS,
    }
    missing = sorted(required - set(payload))
    if missing:
        raise ValueError(f"Daily Telegram learning brief missing fields: {missing}")
    if payload.get("schema_version") != DAILY_TELEGRAM_LEARNING_BRIEF_SCHEMA_VERSION:
        raise ValueError("Daily Telegram learning brief schema mismatch")
    if payload.get("artifact_type") != "daily_telegram_learning_brief":
        raise ValueError("Daily Telegram learning brief artifact type mismatch")
    if payload.get("status") not in DAILY_TELEGRAM_LEARNING_BRIEF_STATUSES:
        raise ValueError("Daily Telegram learning brief status invalid")
    if payload.get("public_safe") is not True:
        raise ValueError("Daily Telegram learning brief must be public-safe")
    if payload.get("target") != "group":
        raise ValueError("Daily Telegram learning brief target must be group")
    if payload.get("message_class") != "daily_telegram_learning_brief":
        raise ValueError("Daily Telegram learning brief message class mismatch")
    if payload.get("brief_slot") not in {"morning", "evening", "manual"}:
        raise ValueError("Daily Telegram learning brief slot invalid")
    if payload.get("scheduled_summary") is not True:
        raise ValueError("Daily Telegram learning brief scheduled-summary flag missing")
    research_snapshot = payload.get("research_snapshot")
    if not isinstance(research_snapshot, dict) or research_snapshot.get("public_safe") is not True:
        raise ValueError("Daily Telegram learning brief research snapshot is not public-safe")
    quantum_learning = research_snapshot.get("quantum_hardware_learning")
    if not isinstance(quantum_learning, dict) or quantum_learning.get("public_safe") is not True:
        raise ValueError("Daily Telegram learning brief quantum learning is not public-safe")
    quantum_mode = str(quantum_learning.get("evidence_mode") or "")
    allowed_quantum_modes = {
        "no_verified_hardware_result",
        "ibm_hardware_candidate_awaiting_validation",
        "ibm_hardware_candidate_tested_inconclusive",
        "ibm_hardware_candidate_rejected",
        "ibm_hardware_candidate_supported",
    }
    if quantum_mode not in allowed_quantum_modes:
        raise ValueError("Daily Telegram learning brief quantum evidence mode invalid")
    if quantum_mode.startswith("ibm_hardware_"):
        if quantum_learning.get("hardware_run_completed") is not True:
            raise ValueError("Daily Telegram learning brief hardware claim is unverified")
        if str(quantum_learning.get("hardware_provider") or "") != (
            "IBM Quantum via Q-CTRL Fire Opal"
        ):
            raise ValueError("Daily Telegram learning brief hardware provider mismatch")
    if quantum_mode == "ibm_hardware_candidate_rejected":
        if quantum_learning.get("interaction_beats_classical_baseline") is not False:
            raise ValueError("Rejected quantum candidate reports classical outperformance")
        for field in ("strategy_changed", "paper_order_created", "validated_edge_created"):
            if quantum_learning.get(field) is not False:
                raise ValueError(f"Rejected quantum candidate leaked authority: {field}")
    if "outbound plain-language learning note" not in str(payload.get("boundary", "")):
        raise ValueError("Daily Telegram learning brief boundary weak")
    for field in TELEGRAM_HUMAN_BRIEF_FALSE_FIELDS:
        if payload.get(field) is not False:
            raise ValueError(f"Daily Telegram learning brief authority leak: {field}")
    title = str(payload.get("title") or "")
    body = str(payload.get("body") or "")
    if not body.strip():
        raise ValueError("Daily Telegram learning brief body missing")
    if payload.get("message_safe") is not True or not _safe_text(title, body):
        raise ValueError("Daily Telegram learning brief unsafe text")
    if payload.get("content_policy_version") != DAILY_TELEGRAM_CONTENT_POLICY_VERSION:
        raise ValueError("Daily Telegram learning brief content policy mismatch")
    if _int(payload.get("rolling_section_dedupe_days")) != (DAILY_TELEGRAM_SECTION_DEDUPE_DAYS):
        raise ValueError("Daily Telegram learning brief dedupe window mismatch")
    if payload.get("blocked_question_repeated_without_change") is not False:
        raise ValueError("Daily Telegram learning brief repeated a blocked research question")
    sections = payload.get("content_sections")
    if not isinstance(sections, list) or len(sections) != 4:
        raise ValueError("Daily Telegram learning brief content sections invalid")
    section_ids = [
        str(section.get("section_id") or "") for section in sections if isinstance(section, dict)
    ]
    expected_section_ids = {
        "material_research_update",
        "ranked_pattern_digest",
        "quantum_result",
        "active_research_focus",
    }
    if set(section_ids) != expected_section_ids:
        raise ValueError("Daily Telegram learning brief content section ids invalid")
    for section in sections:
        if not isinstance(section, dict) or not section.get("fingerprint"):
            raise ValueError("Daily Telegram learning brief content section malformed")
        if section.get("included") is True and section.get("suppression_reason") is not None:
            raise ValueError("Included Daily Telegram section reports suppression")
        if section.get("included") is False and not section.get("suppression_reason"):
            raise ValueError("Suppressed Daily Telegram section has no reason")
    suppressed_ids = payload.get("suppressed_repeated_section_ids")
    if not isinstance(suppressed_ids, list):
        raise ValueError("Daily Telegram learning brief suppressed ids invalid")
    if _int(payload.get("repeated_section_count")) != len(suppressed_ids):
        raise ValueError("Daily Telegram learning brief repeated section count mismatch")
    if payload.get("selected_research_programme_id") is not None:
        if payload.get("selected_research_programme_state") != "active":
            raise ValueError("Daily Telegram learning brief selected blocked research work")
    programme_state = research_snapshot.get("research_programme_state")
    if isinstance(programme_state, dict):
        validate_research_programme_state(programme_state)
    lower_body = body.lower()
    quiet = payload.get("status") == "daily_telegram_learning_brief_quiet_no_material_change"
    if quiet:
        if payload.get("material_delta_mode") is not True:
            raise ValueError("Quiet Daily Telegram brief missing material-delta mode")
        if payload.get("material_change") is not False:
            raise ValueError("Quiet Daily Telegram brief reports material change")
        if payload.get("notification_candidate_created") is not False:
            raise ValueError("Quiet Daily Telegram brief created a notification candidate")
        if payload.get("telegram_live_send_allowed") is not False:
            raise ValueError("Quiet Daily Telegram brief allowed live send")
        if payload.get("live_send_attempted") is not False:
            raise ValueError("Quiet Daily Telegram brief attempted a send")
    else:
        for word in ("candidate", "paper order"):
            if word not in lower_body:
                raise ValueError(f"Daily Telegram learning brief missing {word}")
        if payload.get("brief_slot") in {"morning", "manual"}:
            quantum_included = payload.get("quantum_update_included") is True
            quantum_suppressed = "quantum_result" in suppressed_ids
            if not quantum_included and not quantum_suppressed:
                raise ValueError(
                    "Daily Telegram learning brief neither included nor deduplicated quantum"
                )
        prohibited_copy = (
            "force a trade",
            "forcing a trade",
            "real ibm hardware",
            "not a simulator",
            "honest research cycle",
            "qadam rejected it",
        )
        if any(phrase in lower_body for phrase in prohibited_copy):
            raise ValueError("Daily Telegram learning brief contains promotional boilerplate")
    style = telegram_human_message_style(title, body)
    if style["status"] != "human":
        raise ValueError(f"Daily Telegram learning brief not human: {style['errors']}")
    if style["paragraph_count"] != _int(payload.get("paragraph_count")):
        raise ValueError("Daily Telegram learning brief paragraph count mismatch")
    if not 1 <= _int(payload.get("paragraph_count")) <= 2:
        raise ValueError("Daily Telegram learning brief must be one or two paragraphs")
    if _int(payload.get("message_technical_noise_count")) != 0:
        raise ValueError("Daily Telegram learning brief has technical noise")
    if _int(payload.get("message_section_header_count")) != 0:
        raise ValueError("Daily Telegram learning brief has section headers")
    specificity = telegram_message_specificity(title, body)
    if specificity["status"] != "specific" and not quiet:
        raise ValueError(f"Daily Telegram learning brief not specific: {specificity['reasons']}")
    if _int(payload.get("message_specificity_score")) < 70 and not quiet:
        raise ValueError("Daily Telegram learning brief specificity score too low")
    if payload.get("message_specificity_status") != specificity["status"]:
        raise ValueError("Daily Telegram learning brief specificity status mismatch")
    if payload.get("message_human_style_status") != style["status"]:
        raise ValueError("Daily Telegram learning brief style status mismatch")
    if _int(payload.get("source_count")) < 30:
        raise ValueError("Daily Telegram learning brief source count below contract")
    if _int(payload.get("watched_instrument_count")) < 19:
        raise ValueError("Daily Telegram learning brief watched instrument count below contract")
    if _int(payload.get("candidate_pattern_count")) < 5:
        raise ValueError("Daily Telegram learning brief candidate pattern count below contract")
    if payload.get("quantum_required") is not True:
        raise ValueError("Daily Telegram learning brief must require quantum")
    if payload.get("quantum_gate_passed") is not True:
        raise ValueError("Daily Telegram learning brief quantum gate not passed")
    if payload.get("source_daily_edge_findings_status") != "daily_edge_findings_ready_for_review":
        raise ValueError("Daily Telegram learning brief daily findings not ready")
    if payload.get("source_promotion_gates_status") != "promotion_gates_ready":
        raise ValueError("Daily Telegram learning brief promotion gates not ready")
    if _int(payload.get("promotion_gate_decision_count")) != 5:
        raise ValueError("Daily Telegram learning brief promotion decision count mismatch")
    if _int(payload.get("human_approval_missing_count")) < 1:
        raise ValueError("Daily Telegram learning brief must expose missing human approval")
    if _int(payload.get("strategy_learning_applied_count")) != 0:
        raise ValueError("Daily Telegram learning brief cannot apply learning")
    live_send_allowed = payload.get("telegram_live_send_allowed") is True
    if live_send_allowed:
        if payload.get("enabled") is not True:
            raise ValueError("Daily Telegram learning brief live send allowed while disabled")
        if payload.get("dry_run") is not False:
            raise ValueError("Daily Telegram learning brief live send allowed in dry run")
        if payload.get("bot_configured") is not True:
            raise ValueError("Daily Telegram learning brief live send allowed without bot")
        if payload.get("group_chat_configured") is not True:
            raise ValueError("Daily Telegram learning brief live send allowed without group")
        if payload.get("already_sent") is True:
            raise ValueError("Daily Telegram learning brief live send allowed after already sent")
    if (
        payload.get("live_send_succeeded") is True
        and payload.get("live_send_attempted") is not True
    ):
        raise ValueError("Daily Telegram learning brief sent without attempt")
    if (
        payload.get("telegram_message_id_present") is True
        and payload.get("live_send_succeeded") is not True
    ):
        raise ValueError("Daily Telegram learning brief message id present without success")
    if "/Users/" in body or "/private/" in body or "qadam.trade/" in body:
        raise ValueError("Daily Telegram learning brief body leaked path or URL")


def write_daily_telegram_learning_brief(
    payload: dict[str, Any],
    settings: Settings | None = None,
) -> dict[str, Any]:
    validate_daily_telegram_learning_brief(payload)
    output_path, history_path, event_path = daily_telegram_learning_brief_paths(settings)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    with history_path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(payload, sort_keys=True) + "\n")
    event = {
        "schema_version": DAILY_TELEGRAM_LEARNING_BRIEF_SCHEMA_VERSION,
        "event_type": DAILY_TELEGRAM_LEARNING_BRIEF_EVENT_TYPE,
        "component": DAILY_TELEGRAM_LEARNING_BRIEF_COMPONENT,
        "created_at": payload.get("generated_at") or _now(),
        "brief_date": payload.get("brief_date"),
        "brief_slot": payload.get("brief_slot"),
        "brief_slot_label": payload.get("brief_slot_label"),
        "status": payload.get("status"),
        "message_specificity_score": payload.get("message_specificity_score"),
        "message_human_style_status": payload.get("message_human_style_status"),
        "telegram_live_send_allowed": payload.get("telegram_live_send_allowed") is True,
        "live_send_attempted": payload.get("live_send_attempted") is True,
        "live_send_succeeded": payload.get("live_send_succeeded") is True,
        "paper_order_allowed": False,
        "broker_write_allowed": False,
        "strategy_learning_applied_count": 0,
        "live_capital_enabled": False,
        "boundary": DAILY_TELEGRAM_LEARNING_BRIEF_BOUNDARY,
    }
    with event_path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(event, sort_keys=True) + "\n")
    EventLog(echo=False).write(
        event_type=DAILY_TELEGRAM_LEARNING_BRIEF_EVENT_TYPE,
        component=DAILY_TELEGRAM_LEARNING_BRIEF_COMPONENT,
        payload=event,
    )
    return {
        "output_path": str(output_path),
        "history_path": str(history_path),
        "event_path": str(event_path),
    }
