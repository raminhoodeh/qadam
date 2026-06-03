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
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from orchestrator.config import Settings
from orchestrator.event_log import EventLog

RESEARCH_GOAL_SCHEMA_VERSION = 1
RESEARCH_GOAL_RUNTIME_ARTIFACT = "research_goals.jsonl"

RESEARCH_GOAL_STATUSES = {
    "watching",
    "needs_evidence",
    "researching",
    "strategy_review",
    "blocked",
    "candidate_ready",
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
        ):
            payload[key] = list(payload[key])
        return payload


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


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
        "macro_liquidity": ("SPY", "QQQ", "TLT", "DXY"),
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
    status = "needs_evidence" if refs else "watching"
    return ResearchGoal(
        schema_version=RESEARCH_GOAL_SCHEMA_VERSION,
        goal_id=goal_id,
        status=status,
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
        execution_allowed=False,
        paper_order_allowed=False,
        trade_candidate_creation_allowed=False,
        risk_handoff_allowed=False,
        broker_write_allowed=False,
        live_capital_enabled=False,
        created_at=created_at,
        updated_at=_now(),
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
        return {
            "status": "ok",
            "schema_version": RESEARCH_GOAL_SCHEMA_VERSION,
            "goal_record_count": len(rows),
            "active_goal_count": len(latest),
            "by_status": dict(sorted(by_status.items())),
            "by_market_channel": dict(sorted(by_channel.items())),
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
    after = store.health()
    return {
        "status": "ok" if after["status"] == "ok" else "degraded",
        "created_or_updated_count": len(samples),
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
        recent.append(
            {
                "goal_id": row.get("goal_id"),
                "status": row.get("status"),
                "origin": row.get("origin"),
                "hypothesis": row.get("hypothesis"),
                "market_channel": row.get("market_channel"),
                "watched_instruments": row.get("watched_instruments", [])[:6],
                "required_sources": row.get("required_sources", [])[:8],
                "minimum_source_quorum": row.get("minimum_source_quorum"),
                "worldview_lens": row.get("worldview_lens"),
                "akber_stage": row.get("akber_stage"),
                "missing_corroboration": row.get("missing_corroboration", [])[:8],
                "owner_agent": row.get("owner_agent"),
                "next_handoff": row.get("next_handoff"),
                "execution_allowed": False,
                "paper_order_allowed": False,
                "trade_candidate_creation_allowed": False,
                "risk_handoff_allowed": False,
                "broker_write_allowed": False,
                "live_capital_enabled": False,
                "updated_at": row.get("updated_at"),
                "boundary": row.get("boundary"),
            }
        )
    return health | {"recent_goals": recent}

