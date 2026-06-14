"""RS-3 market context packets and source-quality scoring.

Market context packets sit between Research Goals and later strategy/risk
workflows. They aggregate price/volume context, technical context, paper-account
state, source taxonomy, trust, freshness, and contradictions without granting
any execution authority.
"""

from __future__ import annotations

import hashlib
import json
import re
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from orchestrator.bookmap_local_bridge import (
    BOOKMAP_LOCAL_BRIDGE_TRUST_SCORE,
    bookmap_local_bridge_packet_context,
    bookmap_local_bridge_status,
)
from orchestrator.config import Settings
from orchestrator.event_log import EventLog
from orchestrator.paper_account import paper_account_shadow_context
from orchestrator.research_goal import research_goal_summary
from orchestrator.tradingview_mcp_adapter import (
    TRADINGVIEW_MCP_TRUST_SCORE,
    tradingview_mcp_adapter_status,
    tradingview_mcp_packet_context,
)
from orchestrator.yahoo_finance_adapter import (
    YAHOO_FINANCE_TRUST_SCORE,
    fetch_yahoo_finance_sample,
    yahoo_finance_adapter_status,
)

MARKET_CONTEXT_SCHEMA_VERSION = 1
MARKET_CONTEXT_PACKET_VERSION = "rs3_2026_06_03"
MARKET_CONTEXT_RUNTIME_ARTIFACT = "market_context_packet.json"
MARKET_CONTEXT_HISTORY_ARTIFACT = "market_context_packets.jsonl"
MARKET_CONTEXT_BOUNDARY = (
    "Market Context Packet is read-only context for Research Analyst, Strategy "
    "Lead, Signal Integrity, Risk Agent, and Head of Quant review. It can score "
    "source quality, freshness, corroboration, Yahoo Finance supplemental market "
    "confirmation, TradingView MCP supplemental technical confirmation, "
    "Bookmap local supplemental order-flow confirmation, and paper-account "
    "state, but it cannot create trade candidates, approve risk, "
    "stage or submit paper orders, write to brokers, submit quantum hardware "
    "jobs, or enable live capital."
)

SECRET_LIKE_PATTERNS = (
    re.compile(r"\d{6,}:[A-Za-z0-9_-]{20,}"),
    re.compile(r"\bghp_[A-Za-z0-9]{20,}\b"),
    re.compile(r"\bvcp_[A-Za-z0-9]{20,}\b"),
    re.compile(r"\bAIza[0-9A-Za-z_-]{20,}\b"),
    re.compile(r"\bsb_secret_[0-9A-Za-z_-]{12,}\b"),
    re.compile(r"\b[A-Za-z0-9_-]{40,}\.[A-Za-z0-9_-]{20,}\.[A-Za-z0-9_-]{20,}\b"),
)

AUTHORITY_FIELDS = (
    "execution_allowed",
    "paper_order_allowed",
    "trade_candidate_creation_allowed",
    "risk_handoff_allowed",
    "broker_write_allowed",
    "live_capital_enabled",
    "source_quorum_credit_allowed",
)

DEFAULT_SOURCE_TRUST: dict[str, float] = {
    "acled": 0.78,
    "ais_or_shipping": 0.66,
    "alpaca": 0.76,
    "bls": 0.82,
    "bookmap": BOOKMAP_LOCAL_BRIDGE_TRUST_SCORE,
    "ecb": 0.84,
    "fred": 0.83,
    "gdelt": 0.62,
    "kalshi": 0.58,
    "nasa_firms": 0.74,
    "polymarket": 0.56,
    "reddit": 0.42,
    "rss": 0.55,
    "sec": 0.82,
    "telegram": 0.45,
    "tradingview_mcp": TRADINGVIEW_MCP_TRUST_SCORE,
    "unusual_whales": 0.57,
    "x": 0.4,
    "yahoo_finance": YAHOO_FINANCE_TRUST_SCORE,
    "yahoo_finance_or_tradingview": max(YAHOO_FINANCE_TRUST_SCORE, TRADINGVIEW_MCP_TRUST_SCORE),
}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _runtime_path(settings: Settings) -> Path:
    return Path(settings.runtime_dir) / MARKET_CONTEXT_RUNTIME_ARTIFACT


def _history_path(settings: Settings) -> Path:
    return Path(settings.runtime_dir) / MARKET_CONTEXT_HISTORY_ARTIFACT


def _clamp_score(value: Any, default: float = 0.0) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError):
        number = default
    return round(max(0.0, min(1.0, number)), 3)


def _safe_text(value: Any, *, limit: int = 400, fallback: str = "") -> str:
    text = str(value or "").strip()
    if not text:
        text = fallback
    return " ".join(text.split())[:limit]


def _safe_list(value: Any, *, limit: int = 8) -> list[Any]:
    if isinstance(value, list):
        return value[:limit]
    if isinstance(value, tuple):
        return list(value[:limit])
    if isinstance(value, str) and value.strip():
        return [value.strip()]
    return []


def _contains_secret_like_value(payload: Any) -> bool:
    encoded = json.dumps(payload, sort_keys=True, default=str)
    return any(pattern.search(encoded) for pattern in SECRET_LIKE_PATTERNS)


def _source_key_from_ref(ref: Any) -> str:
    source = str(ref or "").split(":", 1)[0].replace("durable.", "").replace("market.", "").strip()
    if source == "sample":
        return "sample_source"
    return source or "unknown_source"


def _normalise_source_key(source: Any) -> str:
    return str(source or "").replace("market.", "").replace("durable.", "").strip() or "unknown_source"


def _packet_id(goal: dict[str, Any], generated_at: str) -> str:
    seed = json.dumps(
        {
            "goal_id": goal.get("goal_id"),
            "updated_at": goal.get("updated_at"),
            "generated_at": generated_at,
            "packet_version": MARKET_CONTEXT_PACKET_VERSION,
        },
        sort_keys=True,
        default=str,
    )
    return "mcp-" + hashlib.sha256(seed.encode("utf-8")).hexdigest()[:16]


def _status_by_source(source_results: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    statuses: dict[str, dict[str, Any]] = {}
    for result in source_results:
        if not isinstance(result, dict):
            continue
        key = _normalise_source_key(result.get("source_key"))
        statuses[key] = {
            "status": _safe_text(result.get("status"), limit=80, fallback="unknown"),
            "degraded": bool(result.get("degraded")),
            "degraded_reason": _safe_text(result.get("degraded_reason"), limit=160),
            "event_count": int(result.get("event_count", 0) or 0),
            "context_role": _safe_text(result.get("context_role"), limit=100, fallback="unknown"),
        }
    return statuses


def _source_role(source_key: str) -> str:
    if source_key == "yahoo_finance" or source_key == "yahoo_finance_or_tradingview":
        return "supplemental_market_confirmation"
    if source_key == "tradingview_mcp":
        return "supplemental_technical_confirmation"
    if source_key == "bookmap":
        return "supplemental_orderflow_confirmation"
    if source_key == "alpaca":
        return "paper_account_context"
    if source_key == "kalshi":
        return "credential_gated_deferred"
    if source_key in {"unusual_whales", "acled"}:
        return "credential_gated_or_degraded"
    if source_key == "sample_source":
        return "sample_research_goal_context"
    return "canonical_or_registered_source"


def _source_status(source_key: str, source_statuses: dict[str, dict[str, Any]]) -> str:
    if source_key in source_statuses:
        return source_statuses[source_key].get("status", "unknown")
    if source_key == "kalshi":
        return "deferred_due_to_current_location"
    if source_key == "unusual_whales":
        return "missing_credentials"
    if source_key == "yahoo_finance_or_tradingview":
        return "resolved_by_supplemental_context_if_available"
    if source_key == "sample_source":
        return "sample_context"
    return "not_seen_in_current_cycle"


def _source_taxonomy(goal: dict[str, Any], source_results: list[dict[str, Any]]) -> list[dict[str, Any]]:
    statuses = _status_by_source(source_results)
    required_sources = [_normalise_source_key(source) for source in _safe_list(goal.get("required_sources"), limit=16)]
    observed_sources = [_source_key_from_ref(ref) for ref in _safe_list(goal.get("source_event_refs"), limit=16)]
    source_keys = list(
        dict.fromkeys(
            [*observed_sources, *required_sources, "yahoo_finance", "tradingview_mcp", "bookmap", "alpaca"]
        )
    )
    rows: list[dict[str, Any]] = []
    for source_key in source_keys:
        role = _source_role(source_key)
        status = _source_status(source_key, statuses)
        trust = DEFAULT_SOURCE_TRUST.get(source_key, 0.5)
        if source_key in statuses and statuses[source_key].get("degraded"):
            trust = min(trust, 0.45)
        rows.append(
            {
                "source_key": source_key,
                "role": role,
                "status": status,
                "trust_score": round(trust, 3),
                "observed_in_goal": source_key in observed_sources,
                "required_for_goal": source_key in required_sources,
                "event_count": int(statuses.get(source_key, {}).get("event_count", 0) or 0),
                "source_quorum_credit_allowed": False
                if role.startswith("supplemental") or role.startswith("paper") or role.startswith("credential")
                else True,
            }
        )
    return rows


def _symbols_from_goal(goal: dict[str, Any]) -> set[str]:
    symbols = set()
    for symbol in _safe_list(goal.get("watched_instruments"), limit=12):
        text = str(symbol or "").upper().strip()
        if text:
            symbols.add(text)
            if text == "USO":
                symbols.add("CL=F")
            if text == "CL=F":
                symbols.add("TVC:USOIL")
            if text == "SMH":
                symbols.add("NASDAQ:SMH")
    return symbols


def _yahoo_records(yahoo_envelope: dict[str, Any], goal: dict[str, Any]) -> list[dict[str, Any]]:
    symbols = _symbols_from_goal(goal)
    rows: list[dict[str, Any]] = []
    for event in _safe_list(yahoo_envelope.get("events"), limit=12):
        if not isinstance(event, dict):
            continue
        raw = event.get("raw_payload") if isinstance(event.get("raw_payload"), dict) else {}
        symbol = _safe_text(raw.get("symbol"), limit=24, fallback="UNKNOWN").upper()
        if symbols and symbol not in symbols:
            continue
        rows.append(
            {
                "source": "yahoo_finance",
                "symbol": symbol,
                "instrument_name": _safe_text(raw.get("instrument_name"), limit=100, fallback=symbol),
                "last_close": raw.get("last_close"),
                "previous_close": raw.get("previous_close"),
                "percent_move": raw.get("percent_move"),
                "volume_ratio": raw.get("volume_ratio"),
                "rolling_volatility_20d": raw.get("rolling_volatility_20d"),
                "market_state": _safe_text(raw.get("market_state"), limit=80, fallback="unknown"),
                "trust_score": YAHOO_FINANCE_TRUST_SCORE,
                "authority": "supplemental_market_confirmation_only",
            }
        )
    if not rows:
        for event in _safe_list(yahoo_envelope.get("events"), limit=2):
            if not isinstance(event, dict):
                continue
            raw = event.get("raw_payload") if isinstance(event.get("raw_payload"), dict) else {}
            rows.append(
                {
                    "source": "yahoo_finance",
                    "symbol": _safe_text(raw.get("symbol"), limit=24, fallback="UNKNOWN").upper(),
                    "instrument_name": _safe_text(raw.get("instrument_name"), limit=100, fallback="market proxy"),
                    "last_close": raw.get("last_close"),
                    "percent_move": raw.get("percent_move"),
                    "volume_ratio": raw.get("volume_ratio"),
                    "market_state": _safe_text(raw.get("market_state"), limit=80, fallback="unknown"),
                    "trust_score": YAHOO_FINANCE_TRUST_SCORE,
                    "authority": "supplemental_market_confirmation_only",
                }
            )
    return rows[:4]


def _tradingview_records(context: dict[str, Any], goal: dict[str, Any]) -> list[dict[str, Any]]:
    symbols = _symbols_from_goal(goal)
    refs = context.get("technical_context_refs")
    if not isinstance(refs, list):
        refs = []
    rows: list[dict[str, Any]] = []
    for ref in refs:
        if not isinstance(ref, dict):
            continue
        symbol = _safe_text(ref.get("symbol"), limit=40, fallback="UNKNOWN").upper()
        if symbols and symbol not in symbols and symbol.replace("TVC:", "") not in symbols:
            continue
        rows.append(
            {
                "source": "tradingview_mcp",
                "symbol": symbol,
                "setup_type": _safe_text(ref.get("setup_type"), limit=100, fallback="technical_context"),
                "technical_score": _clamp_score(ref.get("technical_score")),
                "obvious_technical_context_flag": bool(ref.get("obvious_technical_context_flag")),
                "authority": "supplemental_technical_confirmation_only",
            }
        )
    if not rows:
        for ref in refs[:2]:
            if isinstance(ref, dict):
                rows.append(
                    {
                        "source": "tradingview_mcp",
                        "symbol": _safe_text(ref.get("symbol"), limit=40, fallback="UNKNOWN").upper(),
                        "setup_type": _safe_text(ref.get("setup_type"), limit=100, fallback="technical_context"),
                        "technical_score": _clamp_score(ref.get("technical_score")),
                        "obvious_technical_context_flag": bool(ref.get("obvious_technical_context_flag")),
                        "authority": "supplemental_technical_confirmation_only",
                    }
                )
    return rows[:4]


def _bookmap_records(context: dict[str, Any], goal: dict[str, Any]) -> list[dict[str, Any]]:
    symbols = _symbols_from_goal(goal)
    refs = context.get("orderflow_context_refs")
    if not isinstance(refs, list):
        refs = []
    rows: list[dict[str, Any]] = []
    for ref in refs:
        if not isinstance(ref, dict):
            continue
        symbol = _safe_text(ref.get("symbol"), limit=40, fallback="UNKNOWN").upper()
        if symbols and symbol not in symbols:
            continue
        rows.append(
            {
                "source": "bookmap",
                "symbol": symbol,
                "setup_type": _safe_text(ref.get("setup_type"), limit=100, fallback="orderflow_context"),
                "orderflow_score": _clamp_score(ref.get("orderflow_score")),
                "obvious_orderflow_context_flag": bool(ref.get("obvious_orderflow_context_flag")),
                "authority": "supplemental_orderflow_confirmation_only",
            }
        )
    if not rows:
        for ref in refs[:2]:
            if isinstance(ref, dict):
                rows.append(
                    {
                        "source": "bookmap",
                        "symbol": _safe_text(ref.get("symbol"), limit=40, fallback="UNKNOWN").upper(),
                        "setup_type": _safe_text(ref.get("setup_type"), limit=100, fallback="orderflow_context"),
                        "orderflow_score": _clamp_score(ref.get("orderflow_score")),
                        "obvious_orderflow_context_flag": bool(ref.get("obvious_orderflow_context_flag")),
                        "authority": "supplemental_orderflow_confirmation_only",
                    }
                )
    return rows[:4]


def _paper_account_context(paper_context: dict[str, Any]) -> dict[str, Any]:
    return {
        "status": _safe_text(paper_context.get("status"), limit=80, fallback="not_initialized"),
        "connection_status": _safe_text(paper_context.get("connection_status"), limit=120, fallback="unknown"),
        "mode": _safe_text(paper_context.get("mode"), limit=40, fallback="paper"),
        "broker": _safe_text(paper_context.get("broker"), limit=80, fallback="paper_mirror"),
        "current_balance_gbp": paper_context.get("current_balance_gbp"),
        "cash_gbp": paper_context.get("cash_gbp"),
        "equity_gbp": paper_context.get("equity_gbp"),
        "open_position_count": int(paper_context.get("open_position_count", 0) or 0),
        "order_count": int(paper_context.get("order_count", 0) or 0),
        "open_order_count": int(paper_context.get("open_order_count", 0) or 0),
        "closed_trade_count": int(paper_context.get("closed_trade_count", 0) or 0),
        "write_authority": False,
        "execution_allowed": False,
        "paper_order_allowed": False,
        "live_capital_enabled": False,
        "authority": "read_only_paper_account_context_only",
    }


def _source_quality(
    goal: dict[str, Any],
    taxonomy: list[dict[str, Any]],
    yahoo_rows: list[dict[str, Any]],
    tradingview_rows: list[dict[str, Any]],
    bookmap_rows: list[dict[str, Any]],
    paper_context: dict[str, Any],
) -> dict[str, Any]:
    source_quorum_score = _clamp_score(goal.get("source_quorum_score"))
    latency_freshness_score = _clamp_score(goal.get("latency_freshness_score"))
    market_confirmation_score = _clamp_score(goal.get("market_confirmation_score"))
    technical_confirmation_score = (
        round(sum(_clamp_score(row.get("technical_score")) for row in tradingview_rows) / len(tradingview_rows), 3)
        if tradingview_rows
        else 0.0
    )
    orderflow_confirmation_score = (
        round(sum(_clamp_score(row.get("orderflow_score")) for row in bookmap_rows) / len(bookmap_rows), 3)
        if bookmap_rows
        else 0.0
    )
    trust_scores = [
        float(row.get("trust_score", 0) or 0)
        for row in taxonomy
        if row.get("status") not in {"missing_credentials", "deferred_due_to_current_location"}
    ]
    trust_average = round(sum(trust_scores) / len(trust_scores), 3) if trust_scores else 0.0
    paper_context_score = 1.0 if paper_context.get("status") in {"ok", "paper_mirror_synced"} else 0.45
    quality_score = _clamp_score(
        (source_quorum_score * 0.23)
        + (trust_average * 0.18)
        + (latency_freshness_score * 0.18)
        + ((1.0 if yahoo_rows else market_confirmation_score) * 0.15)
        + (technical_confirmation_score * 0.1)
        + (orderflow_confirmation_score * 0.06)
        + (paper_context_score * 0.1)
    )
    return {
        "source_quorum_score": source_quorum_score,
        "latency_freshness_score": latency_freshness_score,
        "market_confirmation_score": market_confirmation_score,
        "technical_confirmation_score": technical_confirmation_score,
        "orderflow_confirmation_score": orderflow_confirmation_score,
        "trust_score_average": trust_average,
        "source_quality_score": quality_score,
        "observed_source_count": sum(1 for row in taxonomy if row.get("observed_in_goal")),
        "required_source_count": sum(1 for row in taxonomy if row.get("required_for_goal")),
        "supplemental_context_count": sum(1 for row in taxonomy if str(row.get("role", "")).startswith("supplemental")),
        "missing_or_degraded_source_count": sum(
            1
            for row in taxonomy
            if row.get("status") in {"missing_credentials", "deferred_due_to_current_location", "not_seen_in_current_cycle"}
            or str(row.get("status", "")).startswith("degraded")
        ),
    }


def build_market_context_packet(
    goal: dict[str, Any],
    *,
    source_results: list[dict[str, Any]] | None = None,
    yahoo_envelope: dict[str, Any] | None = None,
    yahoo_status: dict[str, Any] | None = None,
    tradingview_context: dict[str, Any] | None = None,
    tradingview_status: dict[str, Any] | None = None,
    bookmap_context: dict[str, Any] | None = None,
    bookmap_status: dict[str, Any] | None = None,
    paper_context: dict[str, Any] | None = None,
    durable_replay_summary: dict[str, Any] | None = None,
    generated_at: str | None = None,
) -> dict[str, Any]:
    generated_at = generated_at or _now()
    source_results = source_results or []
    yahoo_envelope = yahoo_envelope or fetch_yahoo_finance_sample()
    yahoo_status = yahoo_status or yahoo_finance_adapter_status()
    tradingview_context = tradingview_context or tradingview_mcp_packet_context()
    tradingview_status = tradingview_status or tradingview_mcp_adapter_status()
    bookmap_context = bookmap_context or bookmap_local_bridge_packet_context()
    bookmap_status = bookmap_status or bookmap_local_bridge_status()
    paper_context = paper_context or paper_account_shadow_context()
    durable_replay_summary = durable_replay_summary or {}

    taxonomy = _source_taxonomy(goal, source_results)
    yahoo_rows = _yahoo_records(yahoo_envelope, goal)
    tradingview_rows = _tradingview_records(tradingview_context, goal)
    bookmap_rows = _bookmap_records(bookmap_context, goal)
    paper_safe = _paper_account_context(paper_context)
    source_quality = _source_quality(
        goal,
        taxonomy,
        yahoo_rows,
        tradingview_rows,
        bookmap_rows,
        paper_safe,
    )
    missing_context = list(
        dict.fromkeys(
            [
                *_safe_list(goal.get("missing_corroboration"), limit=10),
                *[
                    f"missing_or_degraded:{row['source_key']}"
                    for row in taxonomy
                    if row.get("status") in {"missing_credentials", "deferred_due_to_current_location", "not_seen_in_current_cycle"}
                    and row.get("required_for_goal")
                ],
            ]
        )
    )[:12]
    contradictory = _safe_list(goal.get("contradictory_evidence"), limit=8)
    source_quorum_passed = _clamp_score(goal.get("source_quorum_score")) >= 1.0
    market_context_ready = (
        source_quorum_passed
        and bool(yahoo_rows or tradingview_rows)
        and source_quality["source_quality_score"] >= 0.55
        and not contradictory
    )
    packet = {
        "schema_version": MARKET_CONTEXT_SCHEMA_VERSION,
        "packet_version": MARKET_CONTEXT_PACKET_VERSION,
        "packet_id": _packet_id(goal, generated_at),
        "generated_at": generated_at,
        "research_goal_id": _safe_text(goal.get("goal_id"), limit=80, fallback="unknown_research_goal"),
        "research_goal_status": _safe_text(goal.get("status"), limit=80, fallback="needs_evidence"),
        "market_channel": _safe_text(goal.get("market_channel"), limit=100, fallback="macro_watchlist"),
        "hypothesis": _safe_text(goal.get("hypothesis"), limit=500, fallback="Research goal requires context."),
        "watched_instruments": [str(item)[:40] for item in _safe_list(goal.get("watched_instruments"), limit=10)],
        "worldview_lens": _safe_text(goal.get("worldview_lens"), limit=120, fallback="private_world_model_prior_only"),
        "akber_stage": _safe_text(goal.get("akber_stage"), limit=100, fallback="stage_1_catalyst_identification"),
        "source_taxonomy": taxonomy,
        "source_quality": source_quality,
        "price_volume_context": {
            "provider": "yahoo_finance",
            "status": _safe_text(yahoo_status.get("status"), limit=80, fallback="sample_mode_available"),
            "role": "supplemental_market_confirmation_only",
            "record_count": len(yahoo_rows),
            "records": yahoo_rows,
            "canonical_source": False,
            "source_quorum_credit_allowed": False,
        },
        "technical_context": {
            "provider": "tradingview_mcp",
            "status": _safe_text(tradingview_status.get("status"), limit=80, fallback="degraded"),
            "role": "supplemental_technical_confirmation_only",
            "record_count": len(tradingview_rows),
            "records": tradingview_rows,
            "canonical_source": False,
            "source_quorum_credit_allowed": False,
        },
        "orderflow_context": {
            "provider": "bookmap_local_bridge",
            "status": _safe_text(bookmap_status.get("status"), limit=80, fallback="local_bridge_required"),
            "role": "supplemental_orderflow_confirmation_only",
            "record_count": len(bookmap_rows),
            "records": bookmap_rows,
            "canonical_source": False,
            "source_quorum_credit_allowed": False,
            "trade_candidate_creation_allowed": False,
            "execution_allowed": False,
            "paper_order_allowed": False,
            "broker_write_allowed": False,
        },
        "paper_account_context": paper_safe,
        "contradictory_evidence": [str(item)[:220] for item in contradictory],
        "missing_context": [str(item)[:180] for item in missing_context],
        "durable_replay_context": {
            "requested": bool(durable_replay_summary.get("replay_status") not in {None, "not_requested"}),
            "status": _safe_text(durable_replay_summary.get("status"), limit=80, fallback="not_requested"),
            "replay_status": _safe_text(durable_replay_summary.get("replay_status"), limit=80, fallback="not_requested"),
            "observation_count": int(durable_replay_summary.get("observation_count", 0) or 0),
            "write_authority": False,
            "signal_authority": False,
            "order_authority": False,
        },
        "source_quorum_result": {
            "status": "passed" if source_quorum_passed else "hold",
            "score": _clamp_score(goal.get("source_quorum_score")),
            "minimum_source_quorum": int(goal.get("minimum_source_quorum", 2) or 2),
            "reason": "source_quorum_met" if source_quorum_passed else "source_quorum_incomplete",
        },
        "market_context_status": "context_ready_for_strategy_review" if market_context_ready else "hold_for_context",
        "context_readiness": {
            "strategy_review_context_ready": bool(market_context_ready),
            "risk_handoff_allowed": False,
            "trade_candidate_creation_allowed": False,
            "paper_order_allowed": False,
            "reason": "read_only_context_ready" if market_context_ready else "missing_or_degraded_context",
        },
        "execution_allowed": False,
        "paper_order_allowed": False,
        "trade_candidate_creation_allowed": False,
        "risk_handoff_allowed": False,
        "broker_write_allowed": False,
        "live_capital_enabled": False,
        "source_quorum_credit_allowed": False,
        "boundary": MARKET_CONTEXT_BOUNDARY,
    }
    validate_market_context_packet(packet)
    return packet


def validate_market_context_packet(packet: dict[str, Any]) -> None:
    required = {
        "schema_version",
        "packet_version",
        "packet_id",
        "research_goal_id",
        "market_channel",
        "source_taxonomy",
        "source_quality",
        "price_volume_context",
        "technical_context",
        "orderflow_context",
        "paper_account_context",
        "source_quorum_result",
        "market_context_status",
        "context_readiness",
        "boundary",
    }
    missing = sorted(required - set(packet))
    if missing:
        raise ValueError(f"market context packet missing fields: {missing}")
    if packet.get("schema_version") != MARKET_CONTEXT_SCHEMA_VERSION:
        raise ValueError("market context packet schema version mismatch")
    if packet.get("packet_version") != MARKET_CONTEXT_PACKET_VERSION:
        raise ValueError("market context packet version mismatch")
    for field in AUTHORITY_FIELDS:
        if packet.get(field) is not False:
            raise ValueError(f"market context packet authority must remain false: {field}")
    for score_field in (
        "source_quorum_score",
        "latency_freshness_score",
        "market_confirmation_score",
        "technical_confirmation_score",
        "orderflow_confirmation_score",
        "trust_score_average",
        "source_quality_score",
    ):
        if score_field not in packet["source_quality"]:
            raise ValueError(f"market context source quality missing {score_field}")
        if not 0 <= float(packet["source_quality"][score_field]) <= 1:
            raise ValueError(f"market context source quality score out of range: {score_field}")
    if packet["price_volume_context"].get("role") != "supplemental_market_confirmation_only":
        raise ValueError("Yahoo Finance role must remain supplemental market confirmation only")
    if packet["price_volume_context"].get("source_quorum_credit_allowed") is not False:
        raise ValueError("Yahoo Finance cannot grant source quorum credit from market context")
    if packet["technical_context"].get("role") != "supplemental_technical_confirmation_only":
        raise ValueError("TradingView MCP role must remain supplemental technical confirmation only")
    if packet["technical_context"].get("source_quorum_credit_allowed") is not False:
        raise ValueError("TradingView MCP cannot grant source quorum credit from market context")
    if packet["orderflow_context"].get("role") != "supplemental_orderflow_confirmation_only":
        raise ValueError("Bookmap role must remain supplemental orderflow confirmation only")
    for field in (
        "source_quorum_credit_allowed",
        "trade_candidate_creation_allowed",
        "execution_allowed",
        "paper_order_allowed",
        "broker_write_allowed",
    ):
        if packet["orderflow_context"].get(field) is not False:
            raise ValueError(f"Bookmap orderflow context authority must remain false: {field}")
    for field in ("write_authority", "execution_allowed", "paper_order_allowed", "live_capital_enabled"):
        if packet["paper_account_context"].get(field) is not False:
            raise ValueError(f"paper account context authority must remain false: {field}")
    if "read-only context" not in str(packet.get("boundary", "")):
        raise ValueError("market context packet boundary is too weak")
    if _contains_secret_like_value(packet):
        raise ValueError("market context packet contains secret-like value")


def run_market_context_packet_cycle(
    *,
    settings: Settings | None = None,
    limit: int = 8,
    source_results: list[dict[str, Any]] | None = None,
    durable_replay_summary: dict[str, Any] | None = None,
    event_log: EventLog | None = None,
) -> dict[str, Any]:
    settings = settings or Settings.from_env()
    event_log = event_log or EventLog(echo=False)
    generated_at = _now()
    research_goals = research_goal_summary(settings=settings, limit=limit)
    recent_goals = research_goals.get("recent_goals", [])
    if not isinstance(recent_goals, list):
        recent_goals = []
    yahoo_envelope = fetch_yahoo_finance_sample()
    yahoo_status = yahoo_finance_adapter_status(settings)
    tradingview_context = tradingview_mcp_packet_context(settings)
    tradingview_status = tradingview_mcp_adapter_status(settings)
    bookmap_context = bookmap_local_bridge_packet_context(settings)
    bookmap_status = bookmap_local_bridge_status(settings)
    paper_context = paper_account_shadow_context(settings)
    packets = [
        build_market_context_packet(
            goal,
            source_results=source_results,
            yahoo_envelope=yahoo_envelope,
            yahoo_status=yahoo_status,
            tradingview_context=tradingview_context,
            tradingview_status=tradingview_status,
            bookmap_context=bookmap_context,
            bookmap_status=bookmap_status,
            paper_context=paper_context,
            durable_replay_summary=durable_replay_summary,
            generated_at=generated_at,
        )
        for goal in recent_goals[:limit]
        if isinstance(goal, dict)
    ]
    authority_counts = {
        field: sum(1 for packet in packets if packet.get(field) is True)
        for field in AUTHORITY_FIELDS
    }
    statuses = Counter(packet.get("market_context_status", "unknown") for packet in packets)
    average_quality = (
        round(sum(packet["source_quality"]["source_quality_score"] for packet in packets) / len(packets), 3)
        if packets
        else 0.0
    )
    summary = {
        "schema_version": MARKET_CONTEXT_SCHEMA_VERSION,
        "packet_version": MARKET_CONTEXT_PACKET_VERSION,
        "status": "ok" if packets else "degraded",
        "generated_at": generated_at,
        "packet_count": len(packets),
        "context_ready_count": statuses.get("context_ready_for_strategy_review", 0),
        "hold_for_context_count": statuses.get("hold_for_context", 0),
        "by_market_context_status": dict(sorted(statuses.items())),
        "average_source_quality_score": average_quality,
        "average_trust_score": (
            round(sum(packet["source_quality"]["trust_score_average"] for packet in packets) / len(packets), 3)
            if packets
            else 0.0
        ),
        "yahoo_finance_status": yahoo_status.get("status"),
        "tradingview_mcp_status": tradingview_status.get("status"),
        "bookmap_local_bridge_status": bookmap_status.get("status"),
        "paper_account_context_status": paper_context.get("status"),
        "authority_counts": authority_counts,
        "recent_packets": packets[:limit],
        "boundary": MARKET_CONTEXT_BOUNDARY,
    }
    if _contains_secret_like_value(summary):
        raise ValueError("market context summary contains secret-like value")
    path = _runtime_path(settings)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(summary, indent=2, sort_keys=True), encoding="utf-8")
    with _history_path(settings).open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(summary, sort_keys=True) + "\n")
    event_log.write(
        "market_context_packet_cycle_completed",
        "market_context",
        {
            "status": summary["status"],
            "packet_count": summary["packet_count"],
            "context_ready_count": summary["context_ready_count"],
            "hold_for_context_count": summary["hold_for_context_count"],
            "average_source_quality_score": summary["average_source_quality_score"],
            "execution_allowed": False,
            "paper_order_allowed": False,
            "broker_write_allowed": False,
        },
    )
    return summary


def market_context_summary(settings: Settings | None = None, *, limit: int = 6) -> dict[str, Any]:
    settings = settings or Settings.from_env()
    path = _runtime_path(settings)
    if not path.exists():
        return run_market_context_packet_cycle(settings=settings, limit=limit)
    try:
        loaded = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return run_market_context_packet_cycle(settings=settings, limit=limit)
    if not isinstance(loaded, dict):
        return run_market_context_packet_cycle(settings=settings, limit=limit)
    loaded["recent_packets"] = _safe_list(loaded.get("recent_packets"), limit=limit)
    return loaded
