"""Public-safe Qadam edge tracker.

The edge tracker states Qadam's core research loop in machine-readable form:
scan source activity, compare it with watched market prices, ask LLMs and the
quant layer to challenge the pattern, then use the weekly thesis to refine
strategy priors. It is an observability and research contract only.
"""

from __future__ import annotations

from collections import Counter
from datetime import datetime, timedelta, timezone
from typing import Any

EDGE_TRACKER_SCHEMA_VERSION = 1

EDGE_TRACKER_AUTHORITY_FALSE_FIELDS: tuple[str, ...] = (
    "source_quorum_credit_allowed",
    "trade_candidate_creation_allowed",
    "risk_approval_allowed",
    "execution_allowed",
    "paper_order_allowed",
    "broker_write_allowed",
    "prediction_market_write_allowed",
    "quantum_job_authority",
    "live_capital_enabled",
)

EDGE_TRACKER_BOUNDARY = (
    "Edge Tracker is read-only research visibility. It can shape hypotheses, "
    "watchlist weights, and weekly thesis review, but it cannot create source "
    "quorum, trade candidates, risk approval, paper orders, broker writes, "
    "prediction-market writes, quantum jobs, or live capital."
)

WATCHED_SLEEVES: tuple[dict[str, Any], ...] = (
    {
        "key": "oil",
        "label": "Oil",
        "pattern_question": (
            "Do conflict, maritime, aviation, fire, macro, and technical signals "
            "imply a repricing of energy-security risk?"
        ),
        "primary_lens_source_keys": (
            "acled",
            "gdelt",
            "nasa_firms",
            "ais_maritime",
            "aviationstack",
            "gps_jamming",
            "fred",
            "un_comtrade",
            "tradingview_mcp",
            "tradingview_paid_alerts",
            "alpaca",
        ),
        "instruments": (
            {
                "symbol": "CL=F",
                "label": "WTI crude futures",
                "instrument_type": "futures price proxy",
                "paper_route": "market confirmation only",
            },
            {
                "symbol": "BZ=F",
                "label": "Brent crude futures",
                "instrument_type": "futures price proxy",
                "paper_route": "market confirmation only",
            },
            {
                "symbol": "USO",
                "label": "United States Oil Fund",
                "instrument_type": "ETF",
                "paper_route": "Alpaca Paper eligible proxy",
            },
            {
                "symbol": "XLE",
                "label": "Energy Select Sector SPDR",
                "instrument_type": "ETF",
                "paper_route": "Alpaca Paper eligible proxy",
            },
        ),
        "strategy_use": "Energy disruption setup, supply shock confirmation, and risk-sizing context.",
    },
    {
        "key": "silver",
        "label": "Silver",
        "pattern_question": (
            "Do macro liquidity, commodity trade, industrial demand, social flow, "
            "and technical structure imply convex metals exposure?"
        ),
        "primary_lens_source_keys": (
            "fred",
            "bis",
            "ecb",
            "un_comtrade",
            "usgs",
            "rss",
            "twitter_x",
            "reddit",
            "bookmap",
            "tradingview_mcp",
            "alpaca",
        ),
        "instruments": (
            {
                "symbol": "SI=F",
                "label": "Silver futures",
                "instrument_type": "futures price proxy",
                "paper_route": "market confirmation only",
            },
            {
                "symbol": "SLV",
                "label": "iShares Silver Trust",
                "instrument_type": "ETF",
                "paper_route": "Alpaca Paper eligible proxy",
            },
            {
                "symbol": "SIL",
                "label": "Global X Silver Miners",
                "instrument_type": "ETF",
                "paper_route": "Alpaca Paper eligible proxy",
            },
            {
                "symbol": "PAAS",
                "label": "Pan American Silver",
                "instrument_type": "equity",
                "paper_route": "Alpaca Paper eligible proxy",
            },
        ),
        "strategy_use": "Precious-metals stress, liquidity repricing, and breakout confirmation.",
    },
    {
        "key": "semiconductors",
        "label": "Semiconductors",
        "pattern_question": (
            "Do sanctions, export controls, supply-chain pressure, software signals, "
            "earnings context, and technical strength imply semiconductor repricing?"
        ),
        "primary_lens_source_keys": (
            "gdelt",
            "rss",
            "sec_edgar",
            "patents",
            "github",
            "un_comtrade",
            "aviationstack",
            "tradingview_mcp",
            "tradingview_paid_alerts",
            "alpaca",
        ),
        "instruments": (
            {
                "symbol": "SMH",
                "label": "VanEck Semiconductor ETF",
                "instrument_type": "ETF",
                "paper_route": "Alpaca Paper eligible proxy",
            },
            {
                "symbol": "SOXX",
                "label": "iShares Semiconductor ETF",
                "instrument_type": "ETF",
                "paper_route": "Alpaca Paper eligible proxy",
            },
            {
                "symbol": "NVDA",
                "label": "Nvidia",
                "instrument_type": "equity",
                "paper_route": "Alpaca Paper eligible proxy",
            },
            {
                "symbol": "AMD",
                "label": "AMD",
                "instrument_type": "equity",
                "paper_route": "Alpaca Paper eligible proxy",
            },
            {
                "symbol": "TSM",
                "label": "TSMC",
                "instrument_type": "ADR equity",
                "paper_route": "Alpaca Paper eligible proxy",
            },
            {
                "symbol": "ASML",
                "label": "ASML",
                "instrument_type": "ADR equity",
                "paper_route": "Alpaca Paper eligible proxy",
            },
        ),
        "strategy_use": "AI infrastructure, export-control, and supply-chain asymmetry.",
    },
    {
        "key": "prediction_markets",
        "label": "Prediction markets",
        "pattern_question": (
            "Do event-probability curves disagree with source evidence, market "
            "prices, and Qadam's scenario model?"
        ),
        "primary_lens_source_keys": (
            "polymarket",
            "kalshi",
            "rss",
            "twitter_x",
            "reddit",
            "acled",
            "gdelt",
            "telegram",
        ),
        "instruments": (
            {
                "symbol": "Polymarket CLOB",
                "label": "Polymarket event probability",
                "instrument_type": "prediction-market probability",
                "paper_route": "research context; no write route",
            },
            {
                "symbol": "Kalshi events",
                "label": "Kalshi event probability",
                "instrument_type": "prediction-market probability",
                "paper_route": "credential-dependent research context",
            },
        ),
        "strategy_use": "Probability-mispricing research against source evidence and market proxies.",
    },
    {
        "key": "defence",
        "label": "Defence stocks",
        "pattern_question": (
            "Do conflict intensity, procurement pressure, congressional flows, "
            "shipping disruption, and aviation activity imply defence repricing?"
        ),
        "primary_lens_source_keys": (
            "acled",
            "ucdp",
            "gdelt",
            "ais_maritime",
            "aviationstack",
            "gps_jamming",
            "sec_edgar",
            "stock_act",
            "tradingview_mcp",
            "alpaca",
        ),
        "instruments": (
            {
                "symbol": "ITA",
                "label": "iShares Aerospace and Defense ETF",
                "instrument_type": "ETF",
                "paper_route": "Alpaca Paper eligible proxy",
            },
            {
                "symbol": "XAR",
                "label": "SPDR Aerospace and Defense ETF",
                "instrument_type": "ETF",
                "paper_route": "Alpaca Paper eligible proxy",
            },
            {
                "symbol": "LMT",
                "label": "Lockheed Martin",
                "instrument_type": "equity",
                "paper_route": "Alpaca Paper eligible proxy",
            },
            {
                "symbol": "RTX",
                "label": "RTX",
                "instrument_type": "equity",
                "paper_route": "Alpaca Paper eligible proxy",
            },
            {
                "symbol": "NOC",
                "label": "Northrop Grumman",
                "instrument_type": "equity",
                "paper_route": "Alpaca Paper eligible proxy",
            },
        ),
        "strategy_use": "Geopolitical escalation, procurement, and second-order defence exposure.",
    },
)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _parse_generated_at(generated_at: str | None) -> datetime:
    if not generated_at:
        return datetime.now(timezone.utc)
    try:
        parsed = datetime.fromisoformat(str(generated_at).replace("Z", "+00:00"))
    except ValueError:
        return datetime.now(timezone.utc)
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _source_record(source: dict[str, Any]) -> dict[str, Any]:
    status = str(source.get("status") or "pending")
    return {
        "source_key": str(source.get("source_key") or "unknown"),
        "source_name": str(source.get("source_name") or source.get("source_key") or "Unknown source"),
        "pipeline": str(source.get("pipeline") or "unknown"),
        "status": status,
        "readiness": str(source.get("readiness") or "not exported"),
        "credential_status": str(source.get("credential_status") or "not exported"),
        "usable_for_research_context": bool(source.get("usable_for_research_context")),
        "eligible_for_signal_review": bool(source.get("eligible_for_signal_review")),
        "can_authorize_orders": bool(source.get("can_authorize_orders")),
    }


def _source_universe(watching: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return sorted(
        [_source_record(source) for source in watching if isinstance(source, dict)],
        key=lambda source: source["source_key"],
    )


def _sleeve_status(source_records: list[dict[str, Any]]) -> str:
    if not source_records:
        return "pending"
    if any(record["can_authorize_orders"] for record in source_records):
        return "blocked"
    if any(record["status"] == "degraded" for record in source_records):
        return "degraded"
    if any(record["status"] == "online" for record in source_records):
        return "tracking"
    return "pending"


def _build_sleeves(watching: list[dict[str, Any]]) -> list[dict[str, Any]]:
    source_records = _source_universe(watching)
    source_keys = [record["source_key"] for record in source_records]
    sleeves: list[dict[str, Any]] = []
    for sleeve in WATCHED_SLEEVES:
        counts = Counter(record["status"] for record in source_records)
        research_usable_count = sum(
            1 for record in source_records if record["usable_for_research_context"]
        )
        signal_review_eligible_count = sum(
            1 for record in source_records if record["eligible_for_signal_review"]
        )
        order_authority_count = sum(
            1 for record in source_records if record["can_authorize_orders"]
        )
        status = _sleeve_status(source_records)
        sleeves.append(
            {
                "key": sleeve["key"],
                "label": sleeve["label"],
                "status": status,
                "pattern_question": sleeve["pattern_question"],
                "strategy_use": sleeve["strategy_use"],
                "watched_instruments": list(sleeve["instruments"]),
                "watched_instrument_count": len(sleeve["instruments"]),
                "source_application": "all_qadam_sources_cross_scanned_for_this_sleeve",
                "source_keys": source_keys,
                "source_activity": source_records,
                "source_count": len(source_records),
                "online_source_count": int(counts.get("online", 0)),
                "degraded_source_count": int(counts.get("degraded", 0)),
                "research_usable_source_count": research_usable_count,
                "signal_review_eligible_source_count": signal_review_eligible_count,
                "order_authority_source_count": order_authority_count,
                "missing_source_keys": [],
                "primary_lens_source_keys": list(sleeve["primary_lens_source_keys"]),
                "primary_lens_note": (
                    "These lenses help explain relevance, but they do not limit "
                    "the scan. Every exported Qadam source is evaluated for this sleeve."
                ),
                "llm_role": (
                    "Local LLM compresses raw source activity; frontier LLM "
                    "challenges the weekly thesis and competing explanations."
                ),
                "quantum_role": (
                    "Head of Quant checks non-linear scenario sensitivity after "
                    "the evidence packet is accepted; it remains annotation only."
                ),
                "paper_route": (
                    "Only Qadam risk and guarded Alpaca Paper execution can route "
                    "paper orders after all gates pass."
                ),
            }
        )
    return sleeves


def _weekly_thesis(generated_at: str | None) -> dict[str, Any]:
    current = _parse_generated_at(generated_at)
    iso_year, iso_week, _ = current.isocalendar()
    week_start = current - timedelta(days=current.weekday())
    week_start = week_start.replace(hour=0, minute=0, second=0, microsecond=0)
    next_due = week_start + timedelta(days=7)
    return {
        "status": "weekly_thesis_active",
        "cadence": "weekly",
        "iso_week": f"{iso_year}-W{iso_week:02d}",
        "current_thesis_label": f"{iso_year}-W{iso_week:02d} source-price pattern thesis",
        "next_thesis_due_at": next_due.isoformat(),
        "working_thesis": (
            "Cross-scan every Qadam data source against every watched oil, "
            "silver, semiconductor, prediction-market, and defence price to "
            "find non-obvious repricing pressure."
        ),
        "strategy_refinement": (
            "Weekly review updates hypothesis priors, watchlist weights, and "
            "pattern thresholds before any future Strategy Lead or Signal "
            "Integrity pass can treat the evidence as meaningful."
        ),
        "non_linear_review": (
            "Quantum and classical-shadow analysis is used as a non-linear "
            "scenario challenge, not as a standalone signal."
        ),
    }


def _llm_status(cognition: dict[str, Any]) -> dict[str, Any]:
    hypotheses = cognition.get("hypotheses", [])
    evidence_packets = cognition.get("evidence_packets", [])
    local_assessments = cognition.get("local_research_assessments", [])
    strategy_packets = cognition.get("strategy_lead_packets", [])
    signal_integrity = cognition.get("signal_integrity", {})
    return {
        "status": "active" if hypotheses or evidence_packets or local_assessments or strategy_packets else "waiting",
        "local_research_assessment_count": len(local_assessments) if isinstance(local_assessments, list) else 0,
        "strategy_lead_packet_count": len(strategy_packets) if isinstance(strategy_packets, list) else 0,
        "hypothesis_count": len(hypotheses) if isinstance(hypotheses, list) else 0,
        "evidence_packet_count": len(evidence_packets) if isinstance(evidence_packets, list) else 0,
        "signal_integrity_status": str(signal_integrity.get("status") or "pending")
        if isinstance(signal_integrity, dict)
        else "pending",
        "role": (
            "LLMs explain, compress, challenge, and rank evidence. They cannot "
            "approve risk, submit paper orders, or enable live capital."
        ),
    }


def _quant_status(
    quantum_oracle: dict[str, Any],
    qctrl_fire_opal_ibm: dict[str, Any],
) -> dict[str, Any]:
    return {
        "status": str(quantum_oracle.get("status") or "not_run"),
        "backend": str(quantum_oracle.get("latest_backend") or "classical_fallback"),
        "mode": str(quantum_oracle.get("latest_local_simulation_mode") or "not_run"),
        "latest_recommendation": str(quantum_oracle.get("latest_recommendation") or "not_run"),
        "next_due_at": quantum_oracle.get("next_due_at"),
        "provider_status": str(
            quantum_oracle.get("provider_readiness", {}).get("status")
            if isinstance(quantum_oracle.get("provider_readiness"), dict)
            else "not_exported"
        ),
        "fire_opal_ibm_status": str(qctrl_fire_opal_ibm.get("status") or "not_exported"),
        "hardware_submission_allowed_count": int(
            quantum_oracle.get("hardware_submission_allowed_count", 0) or 0
        ),
        "paper_order_allowed_count": int(quantum_oracle.get("paper_order_allowed_count", 0) or 0),
        "role": (
            "Quantum consultation is a bounded non-linear scenario review. It "
            "annotates accepted evidence and cannot create trades or orders."
        ),
    }


def build_edge_tracker_status(
    *,
    watching: list[dict[str, Any]],
    quantum_oracle: dict[str, Any],
    qctrl_fire_opal_ibm: dict[str, Any],
    cognition: dict[str, Any],
    generated_at: str | None = None,
    yahoo_finance: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build the public-safe edge tracker projection."""

    generated_at = generated_at or _now()
    sleeves = _build_sleeves(watching)
    source_universe = _source_universe(watching)
    source_keys = [source["source_key"] for source in source_universe]
    source_counts = Counter(source["status"] for source in source_universe)
    instrument_symbols = [
        instrument["symbol"]
        for sleeve in sleeves
        for instrument in sleeve.get("watched_instruments", [])
    ]
    tracker = {
        "schema_version": EDGE_TRACKER_SCHEMA_VERSION,
        "status": "tracking",
        "generated_at": generated_at,
        "purpose": (
            "Cross-scan every Qadam data source against the watched prices of "
            "oil, silver, semiconductors, prediction markets, and defence stocks."
        ),
        "source_scan": {
            "status": "active" if watching else "waiting",
            "mode": "all_sources_every_sleeve",
            "total_source_count": len(source_universe),
            "all_source_keys": source_keys,
            "online_source_count": int(source_counts.get("online", 0)),
            "degraded_source_count": int(source_counts.get("degraded", 0)),
            "research_usable_source_count": sum(
                1 for source in source_universe if source["usable_for_research_context"] is True
            ),
            "signal_review_eligible_source_count": sum(
                1 for source in source_universe if source["eligible_for_signal_review"] is True
            ),
            "order_authority_source_count": sum(
                1 for source in source_universe if source["can_authorize_orders"] is True
            ),
            "scan_contract": (
                "Every watched sleeve receives the same full source universe. "
                "Sleeve labels only describe market focus, not source exclusion."
            ),
        },
        "source_universe": {
            "status": "active" if source_universe else "waiting",
            "mode": "all_sources_every_sleeve",
            "source_count": len(source_universe),
            "sources": source_universe,
            "boundary": (
                "The full source universe is read-only evidence context. It can "
                "support pattern recognition but cannot authorize trades."
            ),
        },
        "market_price_watch": {
            "status": "listed",
            "instrument_count": len(instrument_symbols),
            "symbols": instrument_symbols,
            "supplemental_market_confirmation_status": (
                yahoo_finance or {}
            ).get("status", "not_exported"),
            "live_price_boundary": (
                "Dashboard lists the watched price instruments. Live price reads "
                "depend on the market-data adapter status and remain confirmation "
                "only, not broker truth."
            ),
        },
        "llm_pattern_review": _llm_status(cognition),
        "quantum_pattern_review": _quant_status(quantum_oracle, qctrl_fire_opal_ibm),
        "weekly_thesis": _weekly_thesis(generated_at),
        "sleeves": sleeves,
        "sleeve_count": len(sleeves),
        "watched_instrument_count": len(instrument_symbols),
        "strategy_refinement_route": (
            "Source observations become evidence packets, evidence packets feed "
            "Research Analyst and Strategy Lead review, Signal Integrity checks "
            "corroboration, the quantum layer challenges non-linear sensitivity, "
            "and only then can guarded PaperOps consider an Alpaca Paper route."
        ),
        "public_safe": True,
        "boundary": EDGE_TRACKER_BOUNDARY,
    }
    for field in EDGE_TRACKER_AUTHORITY_FALSE_FIELDS:
        tracker[field] = False
    return tracker


def validate_edge_tracker_status(payload: dict[str, Any]) -> None:
    required = {
        "schema_version",
        "status",
        "purpose",
        "source_scan",
        "source_universe",
        "market_price_watch",
        "llm_pattern_review",
        "quantum_pattern_review",
        "weekly_thesis",
        "sleeves",
        "sleeve_count",
        "watched_instrument_count",
        "strategy_refinement_route",
        "public_safe",
        "boundary",
        *EDGE_TRACKER_AUTHORITY_FALSE_FIELDS,
    }
    missing = sorted(required - set(payload))
    if missing:
        raise ValueError(f"edge tracker missing fields: {missing}")
    if payload.get("schema_version") != EDGE_TRACKER_SCHEMA_VERSION:
        raise ValueError("edge tracker schema version mismatch")
    if payload.get("status") != "tracking":
        raise ValueError("edge tracker must report tracking")
    if payload.get("public_safe") is not True:
        raise ValueError("edge tracker must remain public-safe")
    if "read-only research visibility" not in str(payload.get("boundary", "")):
        raise ValueError("edge tracker boundary is weak")
    for field in EDGE_TRACKER_AUTHORITY_FALSE_FIELDS:
        if payload.get(field) is not False:
            raise ValueError(f"edge tracker must keep {field}=False")
    source_scan = payload.get("source_scan")
    if not isinstance(source_scan, dict):
        raise ValueError("edge tracker source_scan must be a dict")
    if source_scan.get("mode") != "all_sources_every_sleeve":
        raise ValueError("edge tracker must use all sources for every sleeve")
    source_universe = payload.get("source_universe")
    if not isinstance(source_universe, dict):
        raise ValueError("edge tracker source_universe must be a dict")
    universe_sources = source_universe.get("sources")
    if not isinstance(universe_sources, list):
        raise ValueError("edge tracker source universe must expose sources")
    universe_keys = {str(source.get("source_key")) for source in universe_sources if isinstance(source, dict)}
    scan_keys = {str(key) for key in source_scan.get("all_source_keys", [])}
    if universe_keys != scan_keys:
        raise ValueError("edge tracker source_scan keys must match source_universe")
    if int(source_universe.get("source_count", 0) or 0) != len(universe_keys):
        raise ValueError("edge tracker source universe count mismatch")
    sleeves = payload.get("sleeves")
    if not isinstance(sleeves, list) or len(sleeves) != 5:
        raise ValueError("edge tracker must expose five watched sleeves")
    required_sleeves = {"oil", "silver", "semiconductors", "prediction_markets", "defence"}
    found_sleeves = {str(sleeve.get("key")) for sleeve in sleeves if isinstance(sleeve, dict)}
    if found_sleeves != required_sleeves:
        raise ValueError(f"edge tracker sleeve mismatch: {sorted(found_sleeves)}")
    if int(payload.get("watched_instrument_count", 0) or 0) < 20:
        raise ValueError("edge tracker watched instrument list is too small")
    for sleeve in sleeves:
        if not isinstance(sleeve, dict):
            raise ValueError("edge tracker sleeve must be a dict")
        if sleeve.get("order_authority_source_count", 0) != 0:
            raise ValueError(f"edge tracker sleeve has order authority: {sleeve.get('key')}")
        if sleeve.get("source_application") != "all_qadam_sources_cross_scanned_for_this_sleeve":
            raise ValueError(f"edge tracker sleeve has weak source application: {sleeve.get('key')}")
        sleeve_keys = {str(key) for key in sleeve.get("source_keys", [])}
        if sleeve_keys != universe_keys:
            raise ValueError(f"edge tracker sleeve source subset detected: {sleeve.get('key')}")
        if int(sleeve.get("source_count", 0) or 0) != len(universe_keys):
            raise ValueError(f"edge tracker sleeve source count mismatch: {sleeve.get('key')}")
        if sleeve.get("missing_source_keys"):
            raise ValueError(f"edge tracker sleeve reports missing source keys: {sleeve.get('key')}")
        if not sleeve.get("watched_instruments"):
            raise ValueError(f"edge tracker sleeve missing instruments: {sleeve.get('key')}")
        if not sleeve.get("pattern_question"):
            raise ValueError(f"edge tracker sleeve missing pattern question: {sleeve.get('key')}")
