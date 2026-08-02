"""Research Goal lifecycle contracts for Phase 2.

Research goals sit between raw observations and trade candidates. They make
Qadam's reasoning explicit without granting signal, risk, order, broker-write,
or live-capital authority.
"""

from __future__ import annotations

import hashlib
import json
import re
from collections import Counter
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from orchestrator.config import Settings
from orchestrator.event_log import EventLog

RESEARCH_GOAL_SCHEMA_VERSION = 1
RESEARCH_GOAL_HARDENING_VERSION = "rs2_2026_06_03"
RESEARCH_GOAL_RUNTIME_ARTIFACT = "research_goals.jsonl"
RESEARCH_GOAL_STALE_AFTER_HOURS = 72
RESEARCH_GOAL_EXPIRE_AFTER_HOURS = 168

RESEARCH_GOAL_STATUSES = {
    "watching",
    "needs_evidence",
    "researching",
    "strategy_review",
    "blocked",
    "candidate_ready",
    "closed_no_trade",
    "closed",
}

RESEARCH_GOAL_ORIGINS = {
    "live_source",
    "durable_replay",
    "worldview_lens",
    "fund_manager_note",
    "telegram_intake",
    "postmortem",
    "scheduled_scan",
    "sample_source",
}

SECRET_LIKE_PATTERNS = (
    re.compile(r"\d{6,}:[A-Za-z0-9_-]{20,}"),
    re.compile(r"\bghp_[A-Za-z0-9]{20,}\b"),
    re.compile(r"\bvcp_[A-Za-z0-9]{20,}\b"),
    re.compile(r"\bAIza[0-9A-Za-z_-]{20,}\b"),
    re.compile(r"\bsb_secret_[0-9A-Za-z_-]{12,}\b"),
    re.compile(r"\b[A-Za-z0-9_-]{40,}\.[A-Za-z0-9_-]{20,}\.[A-Za-z0-9_-]{20,}\b"),
)

RESEARCH_GOAL_BOUNDARY = (
    "Research Goal is pre-signal research state. It can organize evidence, "
    "contradictions, worldview priors, and handoffs, but it cannot create trade "
    "candidates, approve risk, stage paper orders, write to brokers, submit "
    "quantum hardware jobs, or enable live capital."
)


@dataclass(frozen=True)
class ResearchGoal:
    schema_version: int
    goal_id: str
    status: str
    origin: str
    hypothesis: str
    market_channel: str
    watched_instruments: tuple[str, ...]
    required_sources: tuple[str, ...]
    minimum_source_quorum: int
    source_event_refs: tuple[str, ...]
    worldview_lens: str
    akber_stage: str
    evidence_packets: tuple[str, ...]
    contradictory_evidence: tuple[str, ...]
    missing_corroboration: tuple[str, ...]
    invalidation_conditions: tuple[str, ...]
    owner_agent: str
    next_handoff: str
    research_goal_hardening_version: str
    source_quorum_score: float
    market_confirmation_score: float
    worldview_relevance_score: float
    akber_stage_score: float
    contradiction_score: float
    latency_freshness_score: float
    risk_readiness_score: float
    priority_score: float
    priority_label: str
    candidate_ready_blockers: tuple[str, ...]
    expires_at: str
    stale: bool
    expired: bool
    close_reason: str
    execution_allowed: bool
    paper_order_allowed: bool
    trade_candidate_creation_allowed: bool
    risk_handoff_allowed: bool
    broker_write_allowed: bool
    live_capital_enabled: bool
    created_at: str
    updated_at: str
    boundary: str

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        for key in (
            "watched_instruments",
            "required_sources",
            "source_event_refs",
            "evidence_packets",
            "contradictory_evidence",
            "missing_corroboration",
            "invalidation_conditions",
            "candidate_ready_blockers",
        ):
            payload[key] = list(payload[key])
        return payload


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _parse_datetime(value: Any) -> datetime | None:
    text = str(value or "").strip()
    if not text:
        return None
    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _clamp_score(value: float) -> float:
    return round(max(0.0, min(1.0, float(value))), 3)


def _clean_text(value: Any, *, limit: int = 600, fallback: str = "") -> str:
    text = str(value or "").strip()
    if not text:
        text = fallback
    return " ".join(text.split())[:limit]


def _clean_tuple(value: Any, *, limit: int = 8, item_limit: int = 160) -> tuple[str, ...]:
    if isinstance(value, str):
        rows = [value]
    elif isinstance(value, tuple | list):
        rows = list(value)
    else:
        rows = []
    cleaned = []
    for item in rows:
        text = _clean_text(item, limit=item_limit)
        if text and text not in cleaned:
            cleaned.append(text)
    return tuple(cleaned[:limit])


def _contains_secret_like_value(payload: Any) -> bool:
    encoded = json.dumps(payload, sort_keys=True, default=str)
    return any(pattern.search(encoded) for pattern in SECRET_LIKE_PATTERNS)


def _goal_id(*, source_event_refs: tuple[str, ...], hypothesis: str) -> str:
    seed = json.dumps(
        {"source_event_refs": sorted(source_event_refs), "hypothesis": hypothesis},
        sort_keys=True,
    )
    return "rg-" + hashlib.sha256(seed.encode("utf-8")).hexdigest()[:16]


def _source_names(source_event_refs: tuple[str, ...]) -> tuple[str, ...]:
    names = []
    for ref in source_event_refs:
        source = str(ref).split(":", 1)[0].replace("durable.", "").strip()
        if source and source not in names:
            names.append(source)
    return tuple(names)


def _market_channel(summary: str) -> str:
    lowered = summary.lower()
    if any(term in lowered for term in ("oil", "crude", "hormuz", "suez", "red sea", "shipping")):
        return "energy_transport"
    if any(term in lowered for term in ("semiconductor", "chip", "taiwan", "export control")):
        return "semiconductors"
    if any(term in lowered for term in ("defence", "defense", "missile", "conflict", "war")):
        return "defence_geopolitics"
    if "silver" in lowered:
        return "precious_metals"
    if any(term in lowered for term in ("polymarket", "kalshi", "prediction")):
        return "prediction_markets"
    if any(term in lowered for term in ("yield", "rate", "inflation", "fred", "ecb", "macro")):
        return "macro_liquidity"
    return "macro_watchlist"


def _watched_instruments(channel: str) -> tuple[str, ...]:
    mapping = {
        "energy_transport": ("USO", "XLE", "CL=F", "BNO"),
        "semiconductors": ("SMH", "SOXX", "NVDA", "TSM"),
        "defence_geopolitics": ("ITA", "XAR", "LMT", "RTX"),
        "precious_metals": ("SLV", "SIL", "XME"),
        "prediction_markets": ("Polymarket", "Kalshi"),
        "macro_liquidity": ("SPY", "QQQ", "TLT", "DXY", "SLV", "SIL", "GLD"),
        "macro_watchlist": ("SPY", "QQQ", "GLD", "USO"),
    }
    return mapping.get(channel, mapping["macro_watchlist"])


def _required_sources(channel: str, source_refs: tuple[str, ...]) -> tuple[str, ...]:
    source_names = {ref.split(":", 1)[0].replace("durable.", "") for ref in source_refs}
    requirements = set(source_names)
    if channel == "energy_transport":
        requirements.update({"nasa_firms", "ais_or_shipping", "fred", "yahoo_finance_or_tradingview"})
    elif channel == "semiconductors":
        requirements.update({"gdelt", "sec", "yahoo_finance_or_tradingview", "rss"})
    elif channel == "defence_geopolitics":
        requirements.update({"acled", "gdelt", "rss", "yahoo_finance_or_tradingview"})
    elif channel == "precious_metals":
        requirements.update({"fred", "yahoo_finance_or_tradingview", "rss"})
    elif channel == "prediction_markets":
        requirements.update({"polymarket", "kalshi_or_deferred_reason", "rss"})
    else:
        requirements.update({"fred", "rss", "yahoo_finance_or_tradingview"})
    return tuple(sorted(item for item in requirements if item))


def _worldview_lens(channel: str, summary: str) -> str:
    lowered = summary.lower()
    if channel == "energy_transport" or any(term in lowered for term in ("hormuz", "iran", "red sea")):
        return "energy_security_and_chokepoint_power_prior"
    if channel == "semiconductors" or any(term in lowered for term in ("china", "taiwan", "chips")):
        return "us_china_grand_bargain_and_ai_supply_chain_prior"
    if channel == "defence_geopolitics":
        return "hierarchical_power_and_conflict_incentive_prior"
    if channel == "prediction_markets":
        return "public_odds_vs_institutional_narrative_gap_prior"
    return "private_world_model_prior_only"


def _akber_stage_score(stage: str) -> float:
    lowered = str(stage or "").lower()
    if "stage_6" in lowered or "approval" in lowered:
        return 0.9
    if "stage_5" in lowered or "volume" in lowered:
        return 0.75
    if "stage_4" in lowered or "technical" in lowered:
        return 0.65
    if "stage_3" in lowered or "distribution" in lowered:
        return 0.55
    if "stage_2" in lowered or "volatility" in lowered:
        return 0.45
    if "stage_1" in lowered or "catalyst" in lowered:
        return 0.35
    return 0.25


def _latency_freshness_score(updated_at: Any, *, now: datetime | None = None) -> tuple[float, bool, bool, str]:
    now_dt = now or datetime.now(timezone.utc)
    updated = _parse_datetime(updated_at) or now_dt
    age_hours = max(0.0, (now_dt - updated).total_seconds() / 3600)
    stale = age_hours >= RESEARCH_GOAL_STALE_AFTER_HOURS
    expired = age_hours >= RESEARCH_GOAL_EXPIRE_AFTER_HOURS
    if age_hours <= 6:
        score = 1.0
    elif age_hours <= 24:
        score = 0.75
    elif age_hours <= RESEARCH_GOAL_STALE_AFTER_HOURS:
        score = 0.45
    elif age_hours <= RESEARCH_GOAL_EXPIRE_AFTER_HOURS:
        score = 0.15
    else:
        score = 0.0
    expires_at = (updated + timedelta(hours=RESEARCH_GOAL_EXPIRE_AFTER_HOURS)).isoformat()
    return _clamp_score(score), stale, expired, expires_at


def research_goal_hardening_fields(payload: dict[str, Any], *, now: datetime | None = None) -> dict[str, Any]:
    """Derive RS-2 scoring, priority, and aging fields for a public-safe goal."""

    refs = _clean_tuple(payload.get("source_event_refs"), limit=8, item_limit=180)
    source_names = _source_names(refs)
    minimum_source_quorum = max(2, int(payload.get("minimum_source_quorum", 2) or 2))
    source_quorum_score = _clamp_score(len(source_names) / minimum_source_quorum)
    market_confirmation_sources = {
        "yahoo_finance",
        "tradingview_mcp",
        "alpaca",
        "fred",
    }
    source_set = set(source_names)
    market_confirmation_score = _clamp_score(
        1.0
        if source_set.intersection(market_confirmation_sources)
        else (0.35 if "market_price_confirmation" not in payload.get("missing_corroboration", []) else 0.0)
    )
    worldview_lens = str(payload.get("worldview_lens") or "")
    worldview_relevance_score = _clamp_score(
        0.8 if worldview_lens and worldview_lens != "private_world_model_prior_only" else 0.45
    )
    akber_score = _clamp_score(_akber_stage_score(str(payload.get("akber_stage") or "")))
    contradiction_count = len(_clean_tuple(payload.get("contradictory_evidence"), limit=12, item_limit=180))
    contradiction_score = _clamp_score(1.0 - (0.25 * contradiction_count))
    freshness_score, stale, expired, expires_at = _latency_freshness_score(
        payload.get("updated_at") or payload.get("created_at"),
        now=now,
    )
    missing = set(_clean_tuple(payload.get("missing_corroboration"), limit=16, item_limit=120))
    risk_readiness_score = _clamp_score(
        0.65
        if "risk_agent_review" not in missing and source_quorum_score >= 1.0 and contradiction_score >= 0.75
        else 0.0
    )
    candidate_ready_blockers = []
    if source_quorum_score < 1.0:
        candidate_ready_blockers.append("source_quorum_incomplete")
    if market_confirmation_score < 0.6:
        candidate_ready_blockers.append("market_confirmation_missing")
    if contradiction_score < 0.75:
        candidate_ready_blockers.append("contradictory_evidence_pressure")
    if freshness_score <= 0.15:
        candidate_ready_blockers.append("research_goal_stale_or_expired")
    if risk_readiness_score < 0.6:
        candidate_ready_blockers.append("risk_readiness_missing")
    priority_score = _clamp_score(
        (source_quorum_score * 0.25)
        + (market_confirmation_score * 0.2)
        + (worldview_relevance_score * 0.15)
        + (akber_score * 0.1)
        + (contradiction_score * 0.15)
        + (freshness_score * 0.1)
        + (risk_readiness_score * 0.05)
    )
    close_reason = ""
    effective_status = str(payload.get("status") or "needs_evidence")
    if expired:
        close_reason = "expired_without_candidate_ready_evidence"
        effective_status = "closed_no_trade"
    elif contradiction_score <= 0.25:
        close_reason = "closed_no_trade_due_to_contradictory_evidence"
        effective_status = "closed_no_trade"
    elif not candidate_ready_blockers:
        effective_status = "candidate_ready"
    if effective_status == "closed_no_trade":
        priority_label = "closed_no_trade"
    elif effective_status == "candidate_ready":
        priority_label = "candidate_ready"
    elif priority_score >= 0.7:
        priority_label = "high"
    elif priority_score >= 0.45:
        priority_label = "medium"
    else:
        priority_label = "low"
    return {
        "research_goal_hardening_version": RESEARCH_GOAL_HARDENING_VERSION,
        "source_quorum_score": source_quorum_score,
        "market_confirmation_score": market_confirmation_score,
        "worldview_relevance_score": worldview_relevance_score,
        "akber_stage_score": akber_score,
        "contradiction_score": contradiction_score,
        "latency_freshness_score": freshness_score,
        "risk_readiness_score": risk_readiness_score,
        "priority_score": priority_score,
        "priority_label": priority_label,
        "candidate_ready_blockers": list(dict.fromkeys(candidate_ready_blockers)),
        "expires_at": expires_at,
        "stale": stale,
        "expired": expired,
        "close_reason": close_reason,
        "effective_status": effective_status,
    }


def build_research_goal_from_observation(
    *,
    summary: str,
    source_event_refs: tuple[str, ...],
    origin: str,
    observed_at: str | None = None,
    existing_goal: dict[str, Any] | None = None,
) -> ResearchGoal:
    safe_summary = _clean_text(
        summary,
        limit=700,
        fallback="Read-only source observation requires research review.",
    )
    refs = _clean_tuple(source_event_refs, limit=8, item_limit=180)
    channel = _market_channel(safe_summary + " " + " ".join(refs))
    missing = (
        "second_independent_source",
        "market_price_confirmation",
        "signal_integrity_gate",
        "risk_agent_review",
    )
    if channel == "energy_transport":
        missing += ("shipping_or_ais_confirmation",)
    if channel == "prediction_markets":
        missing += ("counterparty_liquidity_and_orderbook_check",)
    hypothesis = (
        f"{channel.replace('_', ' ')} observation may become relevant if independent "
        f"sources corroborate it: {safe_summary[:240]}"
    )
    goal_id = _goal_id(source_event_refs=refs, hypothesis=hypothesis)
    created_at = str((existing_goal or {}).get("created_at") or observed_at or _now())
    # A repeatedly fetched provider record must not become fresh again merely
    # because Qadam observed the same historical event in a later cycle.
    updated_at = str((existing_goal or {}).get("updated_at") or observed_at or _now())
    status = "needs_evidence" if refs else "watching"
    hardening = research_goal_hardening_fields(
        {
            "status": status,
            "minimum_source_quorum": 2,
            "source_event_refs": refs,
            "missing_corroboration": missing,
            "contradictory_evidence": _clean_tuple(
                (existing_goal or {}).get("contradictory_evidence"),
                limit=8,
                item_limit=180,
            ),
            "worldview_lens": _worldview_lens(channel, safe_summary),
            "akber_stage": "stage_1_catalyst_identification",
            "created_at": created_at,
            "updated_at": updated_at,
        }
    )
    return ResearchGoal(
        schema_version=RESEARCH_GOAL_SCHEMA_VERSION,
        goal_id=goal_id,
        status=hardening["effective_status"],
        origin=origin if origin in RESEARCH_GOAL_ORIGINS else "sample_source",
        hypothesis=hypothesis,
        market_channel=channel,
        watched_instruments=_watched_instruments(channel),
        required_sources=_required_sources(channel, refs),
        minimum_source_quorum=2,
        source_event_refs=refs,
        worldview_lens=_worldview_lens(channel, safe_summary),
        akber_stage="stage_1_catalyst_identification",
        evidence_packets=_clean_tuple((existing_goal or {}).get("evidence_packets"), limit=8),
        contradictory_evidence=_clean_tuple(
            (existing_goal or {}).get("contradictory_evidence"),
            limit=8,
            item_limit=180,
        ),
        missing_corroboration=tuple(dict.fromkeys(missing)),
        invalidation_conditions=(
            "No second independent source confirms the observation.",
            "Market/price confirmation contradicts the implied channel.",
            "Signal Integrity Gate blocks the thesis.",
            "Risk Agent cannot map the thesis to a bounded paper risk state.",
        ),
        owner_agent="research_analyst",
        next_handoff="local_research_analyst_compression",
        research_goal_hardening_version=hardening["research_goal_hardening_version"],
        source_quorum_score=hardening["source_quorum_score"],
        market_confirmation_score=hardening["market_confirmation_score"],
        worldview_relevance_score=hardening["worldview_relevance_score"],
        akber_stage_score=hardening["akber_stage_score"],
        contradiction_score=hardening["contradiction_score"],
        latency_freshness_score=hardening["latency_freshness_score"],
        risk_readiness_score=hardening["risk_readiness_score"],
        priority_score=hardening["priority_score"],
        priority_label=hardening["priority_label"],
        candidate_ready_blockers=hardening["candidate_ready_blockers"],
        expires_at=hardening["expires_at"],
        stale=hardening["stale"],
        expired=hardening["expired"],
        close_reason=hardening["close_reason"],
        execution_allowed=False,
        paper_order_allowed=False,
        trade_candidate_creation_allowed=False,
        risk_handoff_allowed=False,
        broker_write_allowed=False,
        live_capital_enabled=False,
        created_at=created_at,
        updated_at=updated_at,
        boundary=RESEARCH_GOAL_BOUNDARY,
    )


def validate_research_goal(goal: ResearchGoal | dict[str, Any]) -> None:
    payload = goal.to_dict() if isinstance(goal, ResearchGoal) else goal
    if payload.get("schema_version") != RESEARCH_GOAL_SCHEMA_VERSION:
        raise ValueError("research goal schema version mismatch")
    if payload.get("status") not in RESEARCH_GOAL_STATUSES:
        raise ValueError(f"invalid research goal status: {payload.get('status')}")
    if payload.get("origin") not in RESEARCH_GOAL_ORIGINS:
        raise ValueError(f"invalid research goal origin: {payload.get('origin')}")
    for field_name in (
        "goal_id",
        "hypothesis",
        "market_channel",
        "worldview_lens",
        "akber_stage",
        "owner_agent",
        "next_handoff",
        "boundary",
    ):
        if not str(payload.get(field_name) or "").strip():
            raise ValueError(f"research goal missing required field: {field_name}")
    for authority_field in (
        "execution_allowed",
        "paper_order_allowed",
        "trade_candidate_creation_allowed",
        "risk_handoff_allowed",
        "broker_write_allowed",
        "live_capital_enabled",
    ):
        if payload.get(authority_field) is not False:
            raise ValueError(f"research goal authority must remain false: {authority_field}")
    if int(payload.get("minimum_source_quorum", 0) or 0) < 2:
        raise ValueError("research goal minimum source quorum must be at least 2")
    if not isinstance(payload.get("watched_instruments"), list) or not payload["watched_instruments"]:
        raise ValueError("research goal requires watched instruments")
    if not isinstance(payload.get("required_sources"), list) or not payload["required_sources"]:
        raise ValueError("research goal requires source requirements")
    if not isinstance(payload.get("missing_corroboration"), list) or not payload["missing_corroboration"]:
        raise ValueError("research goal requires missing corroboration")
    if "pre-signal research state" not in str(payload.get("boundary", "")):
        raise ValueError("research goal boundary is too weak")
    for score_field in (
        "source_quorum_score",
        "market_confirmation_score",
        "worldview_relevance_score",
        "akber_stage_score",
        "contradiction_score",
        "latency_freshness_score",
        "risk_readiness_score",
        "priority_score",
    ):
        if score_field in payload and not 0 <= float(payload.get(score_field, 0) or 0) <= 1:
            raise ValueError(f"research goal score out of range: {score_field}")
    if payload.get("research_goal_hardening_version") and payload.get(
        "research_goal_hardening_version"
    ) != RESEARCH_GOAL_HARDENING_VERSION:
        raise ValueError("research goal hardening version mismatch")
    if payload.get("status") == "candidate_ready":
        if payload.get("candidate_ready_blockers") not in ([], (), None):
            raise ValueError("candidate_ready research goal cannot retain candidate blockers")
        if payload.get("trade_candidate_creation_allowed") is not False:
            raise ValueError("candidate_ready research goal still cannot create trade candidates")
    if payload.get("status") == "closed_no_trade" and not str(payload.get("close_reason") or "").strip():
        raise ValueError("closed_no_trade research goal requires close_reason")
    if _contains_secret_like_value(payload):
        raise ValueError("research goal contains secret-like value")


class ResearchGoalStore:
    def __init__(self, path: str | Path | None = None, settings: Settings | None = None) -> None:
        self.settings = settings or Settings.from_env()
        self.path = Path(path or Path(self.settings.runtime_dir) / RESEARCH_GOAL_RUNTIME_ARTIFACT)
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def read(self) -> tuple[dict[str, Any], ...]:
        if not self.path.exists():
            return ()
        rows: list[dict[str, Any]] = []
        with self.path.open("r", encoding="utf-8") as handle:
            for line_number, line in enumerate(handle, start=1):
                stripped = line.strip()
                if not stripped:
                    continue
                try:
                    loaded = json.loads(stripped)
                except json.JSONDecodeError as exc:
                    raise ValueError(f"invalid research goal line {line_number} in {self.path}") from exc
                if isinstance(loaded, dict):
                    validate_research_goal(loaded)
                    rows.append(loaded)
        return tuple(rows)

    def latest_by_goal_id(self) -> dict[str, dict[str, Any]]:
        latest: dict[str, dict[str, Any]] = {}
        for row in self.read():
            latest[str(row.get("goal_id"))] = row
        return latest

    def add_record(self, payload: dict[str, Any], *, event_log: EventLog | None = None) -> dict[str, Any]:
        validate_research_goal(payload)
        with self.path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(payload, sort_keys=True) + "\n")
        (event_log or EventLog(echo=False)).write(
            "research_goal_hardened",
            "research_goal",
            {
                "goal_id": payload.get("goal_id"),
                "status": payload.get("status"),
                "priority_score": payload.get("priority_score"),
                "priority_label": payload.get("priority_label"),
                "stale": payload.get("stale"),
                "expired": payload.get("expired"),
                "close_reason": payload.get("close_reason"),
                "execution_allowed": payload.get("execution_allowed"),
                "paper_order_allowed": payload.get("paper_order_allowed"),
            },
        )
        return payload

    def harden_lifecycle(self, *, event_log: EventLog | None = None) -> dict[str, Any]:
        latest = self.latest_by_goal_id()
        appended_count = 0
        closed_no_trade_count = 0
        candidate_ready_count = 0
        stale_count = 0
        expired_count = 0
        for row in latest.values():
            hardening = research_goal_hardening_fields(row)
            hardened = dict(row)
            effective_status = str(hardening.pop("effective_status"))
            hardened.update(hardening)
            if effective_status in RESEARCH_GOAL_STATUSES:
                hardened["status"] = effective_status
            if hardened.get("status") == "closed_no_trade":
                closed_no_trade_count += 1
            if hardened.get("status") == "candidate_ready":
                candidate_ready_count += 1
            if hardened.get("stale") is True:
                stale_count += 1
            if hardened.get("expired") is True:
                expired_count += 1
            needs_append = any(
                row.get(key) != hardened.get(key)
                for key in (
                    "research_goal_hardening_version",
                    "status",
                    "source_quorum_score",
                    "market_confirmation_score",
                    "worldview_relevance_score",
                    "akber_stage_score",
                    "contradiction_score",
                    "latency_freshness_score",
                    "risk_readiness_score",
                    "priority_score",
                    "priority_label",
                    "candidate_ready_blockers",
                    "expires_at",
                    "stale",
                    "expired",
                    "close_reason",
                )
            )
            if needs_append:
                self.add_record(hardened, event_log=event_log)
                appended_count += 1
        return {
            "status": "ok",
            "schema_version": RESEARCH_GOAL_SCHEMA_VERSION,
            "hardening_version": RESEARCH_GOAL_HARDENING_VERSION,
            "inspected_goal_count": len(latest),
            "appended_hardened_snapshot_count": appended_count,
            "closed_no_trade_count": closed_no_trade_count,
            "candidate_ready_count": candidate_ready_count,
            "stale_goal_count": stale_count,
            "expired_goal_count": expired_count,
            "boundary": RESEARCH_GOAL_BOUNDARY,
        }

    def add(self, goal: ResearchGoal, *, event_log: EventLog | None = None) -> ResearchGoal:
        validate_research_goal(goal)
        with self.path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(goal.to_dict(), sort_keys=True) + "\n")
        (event_log or EventLog(echo=False)).write(
            "research_goal_recorded",
            "research_goal",
            {
                "goal_id": goal.goal_id,
                "status": goal.status,
                "origin": goal.origin,
                "market_channel": goal.market_channel,
                "owner_agent": goal.owner_agent,
                "next_handoff": goal.next_handoff,
                "execution_allowed": goal.execution_allowed,
                "paper_order_allowed": goal.paper_order_allowed,
            },
        )
        return goal

    def add_from_observation(
        self,
        *,
        summary: str,
        source_event_refs: tuple[str, ...],
        origin: str,
        observed_at: str | None = None,
        event_log: EventLog | None = None,
    ) -> ResearchGoal:
        refs = _clean_tuple(source_event_refs, limit=8, item_limit=180)
        preview_hypothesis = (
            f"{_market_channel(summary + ' ' + ' '.join(refs)).replace('_', ' ')} observation may become relevant "
            f"if independent sources corroborate it: {_clean_text(summary, limit=240)}"
        )
        preview_id = _goal_id(source_event_refs=refs, hypothesis=preview_hypothesis)
        existing = self.latest_by_goal_id().get(preview_id)
        goal = build_research_goal_from_observation(
            summary=summary,
            source_event_refs=refs,
            origin=origin,
            observed_at=observed_at,
            existing_goal=existing,
        )
        return self.add(goal, event_log=event_log)

    def health(self) -> dict[str, Any]:
        try:
            rows = self.read()
        except Exception as exc:  # noqa: BLE001 - health should report failure
            return {"status": "degraded", "schema_version": RESEARCH_GOAL_SCHEMA_VERSION, "error": str(exc)}
        latest = self.latest_by_goal_id()
        authority_counts = {
            field: sum(1 for row in latest.values() if row.get(field) is True)
            for field in (
                "execution_allowed",
                "paper_order_allowed",
                "trade_candidate_creation_allowed",
                "risk_handoff_allowed",
                "broker_write_allowed",
                "live_capital_enabled",
            )
        }
        by_status = Counter(str(row.get("status") or "unknown") for row in latest.values())
        by_channel = Counter(str(row.get("market_channel") or "unknown") for row in latest.values())
        hardened_latest = []
        for row in latest.values():
            hardening = research_goal_hardening_fields(row)
            hardened = dict(row)
            effective_status = hardening.pop("effective_status")
            hardened.update(hardening)
            hardened["effective_status"] = effective_status
            hardened_latest.append(hardened)
        by_priority = Counter(str(row.get("priority_label") or "unknown") for row in hardened_latest)
        by_effective_status = Counter(str(row.get("effective_status") or "unknown") for row in hardened_latest)
        average_priority_score = (
            round(
                sum(float(row.get("priority_score", 0) or 0) for row in hardened_latest)
                / len(hardened_latest),
                3,
            )
            if hardened_latest
            else 0.0
        )
        return {
            "status": "ok",
            "schema_version": RESEARCH_GOAL_SCHEMA_VERSION,
            "hardening_version": RESEARCH_GOAL_HARDENING_VERSION,
            "goal_record_count": len(rows),
            "active_goal_count": len(latest),
            "by_status": dict(sorted(by_status.items())),
            "by_effective_status": dict(sorted(by_effective_status.items())),
            "by_market_channel": dict(sorted(by_channel.items())),
            "by_priority_label": dict(sorted(by_priority.items())),
            "average_priority_score": average_priority_score,
            "candidate_ready_goal_count": sum(
                1 for row in hardened_latest if row.get("effective_status") == "candidate_ready"
            ),
            "closed_no_trade_goal_count": sum(
                1 for row in hardened_latest if row.get("effective_status") == "closed_no_trade"
            ),
            "stale_goal_count": sum(1 for row in hardened_latest if row.get("stale") is True),
            "expired_goal_count": sum(1 for row in hardened_latest if row.get("expired") is True),
            "authority_counts": authority_counts,
            "last_goal_id": rows[-1].get("goal_id") if rows else None,
            "boundary": RESEARCH_GOAL_BOUNDARY,
        }


def ensure_sample_research_goals(settings: Settings | None = None) -> dict[str, Any]:
    settings = settings or Settings.from_env()
    store = ResearchGoalStore(settings=settings)
    samples = (
        {
            "summary": "High-confidence thermal anomaly near the Strait of Hormuz energy corridor.",
            "source_event_refs": ("sample:nasa_firms:hormuz_thermal",),
            "origin": "sample_source",
        },
        {
            "summary": "Chip export controls become focus of renewed US China negotiations.",
            "source_event_refs": ("sample:gdelt:chip_controls",),
            "origin": "sample_source",
        },
    )
    before = store.health()
    for sample in samples:
        store.add_from_observation(**sample, event_log=EventLog(echo=False))
    hardening = store.harden_lifecycle(event_log=EventLog(echo=False))
    after = store.health()
    return {
        "status": "ok" if after["status"] == "ok" else "degraded",
        "created_or_updated_count": len(samples),
        "hardened_snapshot_count": hardening.get("appended_hardened_snapshot_count", 0),
        "before_active_goal_count": before.get("active_goal_count", 0),
        "after_active_goal_count": after.get("active_goal_count", 0),
        "health": after,
        "boundary": RESEARCH_GOAL_BOUNDARY,
    }


def research_goal_summary(settings: Settings | None = None, *, limit: int = 6) -> dict[str, Any]:
    store = ResearchGoalStore(settings=settings)
    health = store.health()
    if health["status"] != "ok":
        return health | {"recent_goals": []}
    latest = list(store.latest_by_goal_id().values())
    latest.sort(key=lambda row: str(row.get("updated_at") or row.get("created_at") or ""))
    recent = []
    for row in latest[-limit:]:
        hardening = research_goal_hardening_fields(row)
        effective_status = str(hardening.pop("effective_status"))
        market_channel = str(row.get("market_channel") or "macro_watchlist")
        watched_instruments = list(
            dict.fromkeys(
                [
                    *_clean_tuple(
                        row.get("watched_instruments"), limit=12, item_limit=40
                    ),
                    *_watched_instruments(market_channel),
                ]
            )
        )
        recent.append(
            {
                "goal_id": row.get("goal_id"),
                "status": effective_status,
                "stored_status": row.get("status"),
                "origin": row.get("origin"),
                "hypothesis": row.get("hypothesis"),
                "market_channel": market_channel,
                "watched_instruments": watched_instruments[:12],
                "required_sources": row.get("required_sources", [])[:8],
                "source_event_refs": row.get("source_event_refs", [])[:16],
                "minimum_source_quorum": row.get("minimum_source_quorum"),
                "worldview_lens": row.get("worldview_lens"),
                "akber_stage": row.get("akber_stage"),
                "missing_corroboration": row.get("missing_corroboration", [])[:8],
                "research_goal_hardening_version": hardening.get("research_goal_hardening_version"),
                "source_quorum_score": hardening.get("source_quorum_score"),
                "market_confirmation_score": hardening.get("market_confirmation_score"),
                "worldview_relevance_score": hardening.get("worldview_relevance_score"),
                "akber_stage_score": hardening.get("akber_stage_score"),
                "contradiction_score": hardening.get("contradiction_score"),
                "latency_freshness_score": hardening.get("latency_freshness_score"),
                "risk_readiness_score": hardening.get("risk_readiness_score"),
                "priority_score": hardening.get("priority_score"),
                "priority_label": hardening.get("priority_label"),
                "candidate_ready_blockers": list(hardening.get("candidate_ready_blockers", []))[:8],
                "created_at": row.get("created_at"),
                "updated_at": row.get("updated_at"),
                "expires_at": hardening.get("expires_at"),
                "stale": hardening.get("stale"),
                "expired": hardening.get("expired"),
                "close_reason": hardening.get("close_reason"),
                "owner_agent": row.get("owner_agent"),
                "next_handoff": row.get("next_handoff"),
                "execution_allowed": False,
                "paper_order_allowed": False,
                "trade_candidate_creation_allowed": False,
                "risk_handoff_allowed": False,
                "broker_write_allowed": False,
                "live_capital_enabled": False,
                "boundary": row.get("boundary"),
            }
        )
    return health | {"recent_goals": recent}
