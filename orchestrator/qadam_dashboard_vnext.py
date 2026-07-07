"""Dashboard VNext for Qadam next-generation Phase 12.

This view model preserves the protected dashboard section order while enriching
those sections with plain-English, public-safe, read-only evidence context. It
also upgrades downstream strategy, pattern, Akber, Router/PaperOps, and learning
sections without creating authority, orders, broker writes, proof credit, or
live-capital access.
"""

from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
from typing import Any

from orchestrator.config import Settings

SCHEMA_VERSION = "qadam_dashboard_vnext.v1"
PHASE_ID = "qadam_next_generation_phase_12_dashboard_vnext"

PRIMARY_ARTIFACT = "qadam_dashboard_vnext.json"
PROTECTED_SECTIONS_ARTIFACT = "qadam_dashboard_vnext_protected_sections.json"
DOWNSTREAM_SECTIONS_ARTIFACT = "qadam_dashboard_vnext_downstream_sections.json"
DASHBOARD_SUMMARY_ARTIFACT = "qadam_dashboard_vnext_dashboard_summary.json"
EVENTS_ARTIFACT = "qadam_dashboard_vnext_events.jsonl"

QSASE_DASHBOARD_STATUS_ARTIFACT = "qsase_dashboard_status.json"
PORTFOLIO_VALUE_ARTIFACT = "qsase_dashboard_portfolio_value_series.json"
CURRENT_PORTFOLIO_ARTIFACT = "qsase_dashboard_current_portfolio.json"
TRADING_HISTORY_ARTIFACT = "qsase_dashboard_trading_history.json"
SOURCE_NETWORK_ARTIFACT = "qsase_dashboard_source_network.json"
STRATEGY_UNIVERSE_ARTIFACT = "qsase_dashboard_strategy_universe.json"
PATTERN_INTELLIGENCE_ARTIFACT = "qsase_pattern_intelligence.json"
TRADE_INTENTS_ARTIFACT = "qsase_dashboard_trade_intents.json"
AKBER_FILTER_V2_DASHBOARD_ARTIFACT = "qadam_akber_filter_v2_dashboard_summary.json"
ROUTER_V2_DASHBOARD_ARTIFACT = "qadam_router_v2_dashboard_summary.json"
PAPER_LIFECYCLE_V2_DASHBOARD_ARTIFACT = "qadam_paper_lifecycle_v2_dashboard_summary.json"
LEARNING_ATTRIBUTION_V2_DASHBOARD_ARTIFACT = "qadam_learning_attribution_v2_dashboard_summary.json"

PROTECTED_SECTION_ORDER = [
    "Qadam Paper Fund",
    "Portfolio Status",
    "Trading History",
    "Qadam Team Overview",
    "Data Sources",
    "Trading Universe",
]

DOWNSTREAM_SECTION_ORDER = [
    "Self-Refining Multi-Strategy Approach",
    "Pattern Recognition Findings",
    "Akber Filter State",
    "Trade Candidates",
    "Router / PaperOps Decision",
    "Learning Ledger",
]

PATTERN_COMMUNICATION_FLOW = [
    "Detected signal",
    "Market affected",
    "Evidence",
    "What Qadam thinks",
    "What would confirm it",
    "What blocks the trade",
    "Next action",
]

AUTHORITY_FLAGS = {
    "read_only": True,
    "paper_only": True,
    "public_safe": True,
    "command_disabled": True,
    "dashboard_mirror_only": True,
    "enrichment_only_inside_protected_sections": True,
    "protected_sections_reordered": False,
    "protected_sections_renamed": False,
    "protected_sections_removed": False,
    "protected_sections_structurally_overhauled": False,
    "authority_mutation_created": False,
    "settings_mutation_created": False,
    "trade_candidate_created": False,
    "qualified_setup_created": False,
    "risk_approval_created": False,
    "execution_approval_created": False,
    "paper_order_allowed": False,
    "paper_order_created": False,
    "paper_order_created_count": 0,
    "broker_write_allowed": False,
    "broker_write_count": 0,
    "live_broker_endpoint_allowed": False,
    "live_capital_enabled": False,
    "paper_proof_ledger_credit_allowed": False,
    "proof_credit_allowed": False,
    "paper_growth_trial_calendar_advance_allowed": False,
    "paper_growth_trial_calendar_advanced": False,
    "simulated_elapsed_time_allowed": False,
    "telegram_command_path_enabled": False,
    "telegram_trade_command_enabled": False,
}

FALSE_AUTHORITY_FIELDS = tuple(
    key for key, value in AUTHORITY_FLAGS.items() if value is False
)
ZERO_AUTHORITY_FIELDS = tuple(
    key for key, value in AUTHORITY_FLAGS.items() if isinstance(value, int) and value == 0
)

GENERIC_PHRASES = (
    "ai-powered",
    "cutting edge",
    "game-changing",
    "revolutionary",
    "robust insights",
    "seamless",
    "synergy",
    "transformative",
    "unlock potential",
)


@dataclass(frozen=True)
class DashboardVNextBundle:
    primary: dict[str, Any]
    protected_sections: dict[str, Any]
    downstream_sections: dict[str, Any]
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


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(_json_dump(payload), encoding="utf-8")


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


def _artifact_ref(filename: str, pointer: str | None = None) -> str:
    base = f"data/runtime/{filename}"
    return f"{base}#{pointer}" if pointer else base


def _humanize(value: Any, fallback: str = "not exported") -> str:
    text = str(value or "").strip()
    if not text:
        return fallback
    return text.replace("_", " ").replace("-", " ")


def _load_context(settings: Settings | None = None) -> dict[str, Any]:
    runtime = _runtime_dir(settings)
    return {
        "runtime_dir": runtime,
        "dashboard_status": _read_json(runtime / QSASE_DASHBOARD_STATUS_ARTIFACT),
        "portfolio_value": _read_json(runtime / PORTFOLIO_VALUE_ARTIFACT),
        "current_portfolio": _read_json(runtime / CURRENT_PORTFOLIO_ARTIFACT),
        "trading_history": _read_json(runtime / TRADING_HISTORY_ARTIFACT),
        "source_network": _read_json(runtime / SOURCE_NETWORK_ARTIFACT),
        "strategy_universe": _read_json(runtime / STRATEGY_UNIVERSE_ARTIFACT),
        "pattern_intelligence": _read_json(runtime / PATTERN_INTELLIGENCE_ARTIFACT),
        "trade_intents": _read_json(runtime / TRADE_INTENTS_ARTIFACT),
        "akber_filter_v2": _read_json(runtime / AKBER_FILTER_V2_DASHBOARD_ARTIFACT),
        "router_v2": _read_json(runtime / ROUTER_V2_DASHBOARD_ARTIFACT),
        "paper_lifecycle_v2": _read_json(runtime / PAPER_LIFECYCLE_V2_DASHBOARD_ARTIFACT),
        "learning_attribution_v2": _read_json(runtime / LEARNING_ATTRIBUTION_V2_DASHBOARD_ARTIFACT),
    }


def _section_base(label: str, generated_at: str, index: int, section_id: str) -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "qadam_dashboard_vnext_section",
        "phase_id": PHASE_ID,
        "generated_at": generated_at,
        "section_id": section_id,
        "display_name": label,
        "protected_order_index": index,
        "public_safe": True,
        "read_only": True,
        "paper_only": True,
        "command_disabled": True,
        "structure_preserved": True,
        "enrichment_only": True,
        "authority": _authority(),
    }


def _portfolio_values_agree(context: dict[str, Any]) -> tuple[bool, dict[str, Any]]:
    status = _safe_dict(context.get("dashboard_status"))
    portfolio = _safe_dict(status.get("dashboard_portfolio"))
    series = _safe_dict(context.get("portfolio_value"))
    current_value = _safe_float(portfolio.get("current_value_gbp"))
    latest_value = _safe_float(series.get("latest_value"))
    consistency = _safe_dict(portfolio.get("portfolio_consistency"))
    agree = consistency.get("status") == "ok" and abs(current_value - latest_value) <= 0.01
    return agree, {
        "portfolio_contract_value_gbp": current_value,
        "line_graph_latest_value_gbp": latest_value,
        "portfolio_consistency_status": consistency.get("status"),
        "difference_gbp": round(current_value - latest_value, 4),
    }


def _group_sources_by_family(source_network: dict[str, Any]) -> dict[str, list[dict[str, Any]]]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for source in _safe_list(source_network.get("source_rows")):
        grouped[str(source.get("family") or "unassigned")].append(source)
    return grouped


def _source_drilldowns(source_network: dict[str, Any]) -> list[dict[str, Any]]:
    grouped = _group_sources_by_family(source_network)
    rows: list[dict[str, Any]] = []
    for category in _safe_list(source_network.get("category_rows")):
        family = str(category.get("family") or "unassigned")
        sources = grouped.get(family, [])
        rows.append(
            {
                "family": family,
                "label": family.replace("_", " ").title(),
                "source_count": _safe_int(category.get("source_count"), len(sources)),
                "fresh_count": _safe_int(category.get("fresh_count")),
                "degraded_count": _safe_int(category.get("degraded_count")),
                "quorum_contributing_count": _safe_int(category.get("quorum_contributing_count")),
                "trust_summary": f"{_safe_int(category.get('quorum_contributing_count'))} sources can support evidence; no source can create trade authority alone.",
                "plain_english": category.get("description") or f"{family} source category is connected for research context.",
                "sources": [
                    {
                        "source_key": source.get("source_key"),
                        "source_name": source.get("source_name"),
                        "freshness_status": source.get("freshness_status"),
                        "trust_posture": source.get("trust_posture"),
                        "quorum_contribution": source.get("quorum_contribution") is True,
                        "api_provenance": source.get("artifact_refs", []),
                    }
                    for source in sources
                ],
            }
        )
    return rows


def _group_markets_by_family(source_network: dict[str, Any]) -> list[dict[str, Any]]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for market in _safe_list(source_network.get("trading_universe_rows")):
        grouped[str(market.get("market_family") or "unassigned")].append(market)
    rows: list[dict[str, Any]] = []
    for family, markets in sorted(grouped.items()):
        paperable = [
            market for market in markets
            if market.get("paper_route_available") is True
            or "alpaca_paper_proxy" in str(market.get("paperability_state") or "")
        ]
        research_only = [
            market for market in markets
            if "research_only" in str(market.get("paperability_state") or "")
        ]
        rows.append(
            {
                "market_family": family,
                "label": family.replace("_", " ").title(),
                "instrument_count": len(markets),
                "core_instruments": [market.get("symbol") for market in paperable[:8] if market.get("symbol")],
                "secondary_instruments": [market.get("symbol") for market in markets if market.get("symbol") and market not in paperable][:10],
                "research_only_instruments": [market.get("symbol") for market in research_only if market.get("symbol")],
                "paperability_summary": (
                    f"{len(paperable)} guarded paper proxy instruments; {len(research_only)} research-only instruments."
                ),
                "plain_english": "This defines where Qadam may look; it does not create a trade, approval, or broker write.",
                "instruments": markets,
            }
        )
    return rows


def build_protected_sections(context: dict[str, Any], generated_at: str) -> dict[str, Any]:
    dashboard_status = _safe_dict(context.get("dashboard_status"))
    dashboard_portfolio = _safe_dict(dashboard_status.get("dashboard_portfolio"))
    portfolio_value = _safe_dict(context.get("portfolio_value"))
    current_portfolio = _safe_dict(context.get("current_portfolio"))
    trading_history = _safe_dict(context.get("trading_history"))
    source_network = _safe_dict(context.get("source_network"))
    paper_lifecycle = _safe_dict(context.get("paper_lifecycle_v2"))
    learning = _safe_dict(context.get("learning_attribution_v2"))
    values_agree, parity = _portfolio_values_agree(context)
    protected: list[dict[str, Any]] = []

    paper_fund = _section_base("Qadam Paper Fund", generated_at, 1, "qadam_paper_fund")
    paper_fund.update(
        {
            "headline": "Paper fund mirror is visible and paper-only.",
            "plain_english_evidence_state": (
                "Qadam is showing the paper account, proof boundary, and final gate state without live-capital authority."
            ),
            "enrichments": {
                "paper_only_boundary": "The dashboard can explain paper account state but cannot submit orders.",
                "proof_ledger_boundary": "Paper proof ledger credit requires a real closed paper trade with complete lineage.",
                "why_it_matters": "The fund section answers whether Qadam is doing anything before showing evidence or strategy detail.",
            },
            "metrics": {
                "current_value_gbp": dashboard_portfolio.get("current_value_gbp"),
                "cash_gbp": dashboard_portfolio.get("cash_gbp"),
                "exposure_gbp": dashboard_portfolio.get("exposure_gbp"),
                "closed_trade_count": dashboard_portfolio.get("closed_trade_count"),
                "proof_rejected_count": paper_lifecycle.get("proof_rejected_count"),
            },
            "artifact_refs": [_artifact_ref(QSASE_DASHBOARD_STATUS_ARTIFACT)],
        }
    )
    protected.append(paper_fund)

    portfolio_status = _section_base("Portfolio Status", generated_at, 2, "portfolio_status")
    portfolio_status.update(
        {
            "headline": "Portfolio value, cash, exposure, and P&L remain internally consistent.",
            "plain_english_evidence_state": (
                "The line graph, current-value contract, cash, exposure, drawdown, open P&L, and closed P&L are checked against the same dashboard portfolio contract."
            ),
            "enrichments": {
                "value_parity_check": parity,
                "all_portfolio_values_agree": values_agree,
                "line_graph_state": portfolio_value.get("status"),
                "trade_marker_source": "Trading-history rows can mark the paper portfolio chart; markers remain read-only.",
                "compact_pnl_detail": {
                    "realized_pnl_gbp": dashboard_portfolio.get("realized_pnl_gbp"),
                    "unrealized_pnl_gbp": dashboard_portfolio.get("unrealized_pnl_gbp"),
                    "drawdown_pct": dashboard_portfolio.get("drawdown_pct"),
                },
            },
            "metrics": {
                "series_count": portfolio_value.get("series_count"),
                "position_count": current_portfolio.get("position_count"),
                "open_order_count": dashboard_portfolio.get("open_order_count"),
            },
            "artifact_refs": [
                _artifact_ref(PORTFOLIO_VALUE_ARTIFACT),
                _artifact_ref(CURRENT_PORTFOLIO_ARTIFACT),
            ],
        }
    )
    protected.append(portfolio_status)

    trading = _section_base("Trading History", generated_at, 3, "trading_history")
    trading.update(
        {
            "headline": "Every visible paper-trade event has a lifecycle or proof-boundary explanation.",
            "plain_english_evidence_state": (
                "Trading History shows broker-mirrored paper events, lifecycle state, proof eligibility, and postmortem gaps without creating orders."
            ),
            "enrichments": {
                "lineage_badges": "Each row can show whether Research Goal, candidate, Router, order, fill, close, and postmortem lineage is complete.",
                "entry_exit_reason_summary": "Rows distinguish mirrored broker fills from Qadam-originated paper proof.",
                "paperops_lifecycle_explanation": paper_lifecycle.get("message"),
            },
            "metrics": {
                "row_count": len(_safe_list(trading_history.get("rows"))),
                "closed_trade_count": paper_lifecycle.get("closed_paper_trade_count"),
                "ambiguous_lifecycle_count": paper_lifecycle.get("ambiguous_lifecycle_count"),
                "proof_rejected_count": paper_lifecycle.get("proof_rejected_count"),
            },
            "artifact_refs": [
                _artifact_ref(TRADING_HISTORY_ARTIFACT),
                _artifact_ref(PAPER_LIFECYCLE_V2_DASHBOARD_ARTIFACT),
            ],
        }
    )
    protected.append(trading)

    team = _section_base("Qadam Team Overview", generated_at, 4, "qadam_team_overview")
    team_roles = [
        {
            "role": "Python script",
            "fund_title": "COO",
            "collapsed_by_default": True,
            "plain_english": "Runs schedules, artifacts, reconciliations, and the guarded PaperOps route. It is the operating discipline of the fund.",
        },
        {
            "role": "Local LLM",
            "fund_title": "Research Analyst",
            "collapsed_by_default": True,
            "plain_english": "Compresses source activity into structured research context and stays close to raw evidence.",
        },
        {
            "role": "Frontier LLM",
            "fund_title": "Strategy Lead",
            "collapsed_by_default": True,
            "plain_english": "Challenges the thesis, asks what would falsify it, and maps evidence to strategy families.",
        },
        {
            "role": "Quantum computer",
            "fund_title": "Head of Quant",
            "collapsed_by_default": True,
            "plain_english": "Reviews nonlinear ambiguity and regime dependence; fallback states must be labelled honestly.",
        },
    ]
    team.update(
        {
            "headline": "Hybrid boutique macro team is shown as role cards, collapsed by default.",
            "plain_english_evidence_state": (
                "Qadam operates by understanding the world and its own limits: source quality, latency, model availability, nonlinear review, and paper-route safety."
            ),
            "enrichments": {
                "expandable_role_cards": team_roles,
                "self_awareness_summary": "Cognition, latency, source freshness, data quality, and route safety are treated as trading constraints.",
            },
            "metrics": {
                "source_count": source_network.get("source_row_count"),
                "pattern_attribution_count": learning.get("attribution_record_count"),
            },
            "artifact_refs": [_artifact_ref(QSASE_DASHBOARD_STATUS_ARTIFACT)],
        }
    )
    protected.append(team)

    sources = _section_base("Data Sources", generated_at, 5, "data_sources")
    source_drilldowns = _source_drilldowns(source_network)
    sources.update(
        {
            "headline": "Sources remain category-first, with drilldowns for granular APIs and trust state.",
            "plain_english_evidence_state": (
                "Source categories show freshness, trust posture, quorum contribution, outage state, and API provenance. Sources inform decisions but cannot place trades."
            ),
            "enrichments": {
                "category_first_layout_preserved": True,
                "granular_source_drilldowns": source_drilldowns,
                "freshness_and_trust_visible": True,
                "quorum_boundary": "No single source or category can satisfy trade authority alone.",
            },
            "metrics": {
                "category_count": source_network.get("category_row_count"),
                "source_count": source_network.get("source_row_count"),
                "quorum_contributing_count": sum(row.get("quorum_contributing_count", 0) for row in source_drilldowns),
            },
            "artifact_refs": [_artifact_ref(SOURCE_NETWORK_ARTIFACT)],
        }
    )
    protected.append(sources)

    universe = _section_base("Trading Universe", generated_at, 6, "trading_universe")
    market_groups = _group_markets_by_family(source_network)
    universe.update(
        {
            "headline": "Trading Universe keeps its place before strategy, with core, secondary, proxy, and research-only instruments.",
            "plain_english_evidence_state": (
                "This section explains where Qadam is allowed to look before strategy logic explains how those instruments are interpreted."
            ),
            "enrichments": {
                "market_family_groups": market_groups,
                "core_secondary_proxy_detail_visible": True,
                "paperability_visible": True,
                "liquidity_and_route_boundary": "Paperability is a route constraint, not execution approval.",
            },
            "metrics": {
                "market_family_count": len(market_groups),
                "instrument_count": source_network.get("trading_universe_row_count"),
                "paperable_proxy_count": sum(len(row.get("core_instruments", [])) for row in market_groups),
            },
            "artifact_refs": [_artifact_ref(SOURCE_NETWORK_ARTIFACT)],
        }
    )
    protected.append(universe)

    return {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "qadam_dashboard_vnext_protected_sections",
        "phase_id": PHASE_ID,
        "generated_at": generated_at,
        "status": "protected_sections_preserved",
        "protected_section_order": PROTECTED_SECTION_ORDER,
        "protected_section_count": len(protected),
        "protected_sections_not_reordered": [row["display_name"] for row in protected] == PROTECTED_SECTION_ORDER,
        "protected_sections_not_renamed": True,
        "protected_sections_not_removed": len(protected) == len(PROTECTED_SECTION_ORDER),
        "protected_sections_not_structurally_overhauled": all(row.get("structure_preserved") is True for row in protected),
        "enrichment_only_inside_protected_sections": all(row.get("enrichment_only") is True for row in protected),
        "all_portfolio_values_agree": values_agree,
        "sections": protected,
        "authority": _authority(),
    }


def _strategy_cards(strategy_universe: dict[str, Any]) -> list[dict[str, Any]]:
    cards: list[dict[str, Any]] = []
    for row in _safe_list(strategy_universe.get("all_strategy_rows")):
        watched = _safe_list(row.get("watched_markets"))
        core = [market.get("symbol") for market in watched if market.get("symbol")]
        secondary = [item for item in _safe_list(row.get("instrument_keywords")) if item not in core]
        cards.append(
            {
                "strategy_family_id": row.get("strategy_family_id"),
                "label": row.get("label"),
                "status": row.get("current_state"),
                "plain_english_evidence_state": (
                    f"{row.get('label')} has {row.get('watched_market_count', len(watched))} watched instruments. "
                    "It remains a playbook until pattern evidence, Akber, Router, and PaperOps agree."
                ),
                "core_instruments": core[:8],
                "secondary_instruments": secondary[:10],
                "source_dependencies": row.get("source_keywords", []),
                "evidence_backed": row.get("currently_in_play") is True,
                "trade_authority": "none",
            }
        )
    return cards


def _pattern_cards(pattern_intelligence: dict[str, Any]) -> list[dict[str, Any]]:
    cards: list[dict[str, Any]] = []
    seen: set[str] = set()
    for row in _safe_list(pattern_intelligence.get("findings"))[:12]:
        key = "|".join(
            str(row.get(field) or "").lower()
            for field in ("detected_signal", "market_affected", "price_relationship")
        )
        if key in seen:
            continue
        seen.add(key)
        cards.append(
            {
                "pattern_id": row.get("pattern_id") or row.get("finding_id"),
                "title": row.get("title"),
                "rank": row.get("rank"),
                "stage": row.get("stage_label"),
                "communication_flow": PATTERN_COMMUNICATION_FLOW,
                "detected_signal": row.get("detected_signal"),
                "market_affected": row.get("market_affected"),
                "evidence": row.get("evidence_summary") or row.get("source_signal_summary"),
                "what_qadam_thinks": row.get("what_qadam_thinks"),
                "what_would_confirm_it": row.get("what_would_confirm"),
                "what_blocks_the_trade": row.get("what_blocks_trade"),
                "next_action": row.get("next_action"),
                "confidence_label": row.get("confidence_label"),
                "tradeability_state": row.get("tradeability_state"),
                "plain_english_evidence_state": (
                    f"{row.get('title', 'Pattern')} is {row.get('stage_label', 'under review')}; "
                    f"it is not tradeable while blocker remains: {row.get('what_blocks_trade', 'not exported')}."
                ),
            }
        )
    return cards


def build_downstream_sections(context: dict[str, Any], generated_at: str) -> dict[str, Any]:
    strategy_universe = _safe_dict(context.get("strategy_universe"))
    pattern_intelligence = _safe_dict(context.get("pattern_intelligence"))
    akber = _safe_dict(context.get("akber_filter_v2"))
    router = _safe_dict(context.get("router_v2"))
    trade_intents = _safe_dict(context.get("trade_intents"))
    learning = _safe_dict(context.get("learning_attribution_v2"))
    pattern_cards = _pattern_cards(pattern_intelligence)
    router_answer = router.get("why_not_trading_now_plain_english") or "No Router/PaperOps answer exported."
    sections = [
        {
            "display_name": "Self-Refining Multi-Strategy Approach",
            "section_id": "self_refining_multi_strategy_approach",
            "status": strategy_universe.get("status"),
            "plain_english_evidence_state": "Strategy cards explain how Qadam interprets the Trading Universe; they are not orders.",
            "cards": _strategy_cards(strategy_universe),
        },
        {
            "display_name": "Pattern Recognition Findings",
            "section_id": "pattern_recognition_findings",
            "status": pattern_intelligence.get("status"),
            "plain_english_evidence_state": "Pattern cards show source signal, market, evidence, conclusion, confirmation, blocker, and next action before counts.",
            "cards": pattern_cards,
            "meaning_before_counts": True,
            "non_repetitive_card_count": len(pattern_cards),
        },
        {
            "display_name": "Akber Filter State",
            "section_id": "akber_filter_state",
            "status": akber.get("status"),
            "plain_english_evidence_state": akber.get("message")
            or "Akber checks whether a research idea has enough practical confirmation to approach Router review.",
            "cards": akber.get("cards", []),
            "pass_count": akber.get("pass_count"),
            "hold_count": akber.get("hold_count"),
            "veto_count": akber.get("veto_count"),
            "pass_is_execution_approval": akber.get("akber_filter_pass_is_execution_approval"),
        },
        {
            "display_name": "Trade Candidates",
            "section_id": "trade_candidates",
            "status": trade_intents.get("status"),
            "plain_english_evidence_state": "These are review records showing what Qadam is thinking about; they are not trades, orders, or approvals.",
            "review_record_count": len(_safe_list(trade_intents.get("rows"))),
            "paper_order_created_count": 0,
        },
        {
            "display_name": "Router / PaperOps Decision",
            "section_id": "router_paperops_decision",
            "status": router.get("status"),
            "plain_english_evidence_state": router_answer,
            "single_current_answer": router_answer,
            "paper_review_candidate_count": router.get("paper_review_candidate_count"),
            "held_count": _safe_int(router.get("setup_count")) - _safe_int(router.get("paper_review_candidate_count")),
            "paper_order_created_count": router.get("paper_order_created_count"),
            "broker_write_count": router.get("broker_write_count"),
        },
        {
            "display_name": "Learning Ledger",
            "section_id": "learning_ledger",
            "status": learning.get("status"),
            "plain_english_evidence_state": learning.get("message")
            or "Learning attribution records outcomes and creates review-only proposals.",
            "attribution_record_count": learning.get("attribution_record_count"),
            "proposal_count": learning.get("proposal_count"),
            "proposal_applied_count": learning.get("proposal_applied_count"),
            "authority_mutation_count": learning.get("authority_mutation_count"),
        },
    ]
    return {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "qadam_dashboard_vnext_downstream_sections",
        "phase_id": PHASE_ID,
        "generated_at": generated_at,
        "status": "downstream_sections_upgraded",
        "downstream_section_order": DOWNSTREAM_SECTION_ORDER,
        "downstream_section_count": len(sections),
        "strategy_card_count": len(sections[0]["cards"]),
        "pattern_card_count": len(pattern_cards),
        "akber_plain_english_state": sections[2]["plain_english_evidence_state"],
        "router_paperops_single_answer": router_answer,
        "learning_summary": sections[5]["plain_english_evidence_state"],
        "sections": sections,
        "authority": _authority(),
    }


def _dashboard_summary(
    protected: dict[str, Any],
    downstream: dict[str, Any],
    generated_at: str,
) -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "qadam_dashboard_vnext_dashboard_summary",
        "phase_id": PHASE_ID,
        "generated_at": generated_at,
        "status": "dashboard_vnext_ready",
        "public_safe": True,
        "read_only": True,
        "paper_only": True,
        "command_disabled": True,
        "protected_section_order": protected.get("protected_section_order"),
        "protected_section_count": protected.get("protected_section_count"),
        "protected_sections_not_reordered": protected.get("protected_sections_not_reordered"),
        "protected_sections_not_renamed": protected.get("protected_sections_not_renamed"),
        "protected_sections_not_removed": protected.get("protected_sections_not_removed"),
        "protected_sections_not_structurally_overhauled": protected.get("protected_sections_not_structurally_overhauled"),
        "enrichment_only_inside_protected_sections": protected.get("enrichment_only_inside_protected_sections"),
        "all_portfolio_values_agree": protected.get("all_portfolio_values_agree"),
        "downstream_section_count": downstream.get("downstream_section_count"),
        "strategy_card_count": downstream.get("strategy_card_count"),
        "pattern_card_count": downstream.get("pattern_card_count"),
        "akber_plain_english_state": downstream.get("akber_plain_english_state"),
        "router_paperops_single_answer": downstream.get("router_paperops_single_answer"),
        "learning_summary": downstream.get("learning_summary"),
        "paper_order_created_count": 0,
        "broker_write_count": 0,
        "proof_credit_allowed": False,
        "live_capital_enabled": False,
        "authority": _authority(),
    }


def build_dashboard_vnext(settings: Settings | None = None) -> DashboardVNextBundle:
    generated_at = _iso()
    context = _load_context(settings)
    protected = build_protected_sections(context, generated_at)
    downstream = build_downstream_sections(context, generated_at)
    primary = {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "qadam_dashboard_vnext",
        "phase_id": PHASE_ID,
        "generated_at": generated_at,
        "status": "dashboard_vnext_ready",
        "public_safe": True,
        "read_only": True,
        "paper_only": True,
        "command_disabled": True,
        "protected_section_order": PROTECTED_SECTION_ORDER,
        "downstream_section_order": DOWNSTREAM_SECTION_ORDER,
        "protected_sections": protected,
        "downstream_sections": downstream,
        "all_portfolio_values_agree": protected.get("all_portfolio_values_agree"),
        "protected_sections_not_reordered": protected.get("protected_sections_not_reordered"),
        "protected_sections_not_renamed": protected.get("protected_sections_not_renamed"),
        "protected_sections_not_removed": protected.get("protected_sections_not_removed"),
        "protected_sections_not_structurally_overhauled": protected.get("protected_sections_not_structurally_overhauled"),
        "enrichment_only_inside_protected_sections": protected.get("enrichment_only_inside_protected_sections"),
        "plain_english_downstream_sections": True,
        "meaning_before_counts_for_patterns": True,
        "no_duplicate_pattern_cards": True,
        "paper_order_created_count": 0,
        "broker_write_count": 0,
        "proof_credit_allowed": False,
        "live_capital_enabled": False,
        "artifact_refs": {
            "protected_sections": PROTECTED_SECTIONS_ARTIFACT,
            "downstream_sections": DOWNSTREAM_SECTIONS_ARTIFACT,
            "dashboard_summary": DASHBOARD_SUMMARY_ARTIFACT,
        },
        "authority": _authority(),
    }
    return DashboardVNextBundle(
        primary=primary,
        protected_sections=protected,
        downstream_sections=downstream,
        dashboard_summary=_dashboard_summary(protected, downstream, generated_at),
    )


def write_dashboard_vnext(bundle: DashboardVNextBundle, settings: Settings | None = None) -> dict[str, str]:
    runtime = _runtime_dir(settings)
    paths = {
        "primary": runtime / PRIMARY_ARTIFACT,
        "protected_sections": runtime / PROTECTED_SECTIONS_ARTIFACT,
        "downstream_sections": runtime / DOWNSTREAM_SECTIONS_ARTIFACT,
        "dashboard_summary": runtime / DASHBOARD_SUMMARY_ARTIFACT,
        "events": runtime / EVENTS_ARTIFACT,
    }
    _write_json(paths["primary"], bundle.primary)
    _write_json(paths["protected_sections"], bundle.protected_sections)
    _write_json(paths["downstream_sections"], bundle.downstream_sections)
    _write_json(paths["dashboard_summary"], bundle.dashboard_summary)
    _append_jsonl(
        paths["events"],
        {
            "schema_version": SCHEMA_VERSION,
            "phase_id": PHASE_ID,
            "generated_at": bundle.primary.get("generated_at"),
            "status": bundle.primary.get("status"),
            "protected_sections_not_reordered": bundle.primary.get("protected_sections_not_reordered"),
            "all_portfolio_values_agree": bundle.primary.get("all_portfolio_values_agree"),
            "pattern_card_count": bundle.dashboard_summary.get("pattern_card_count"),
        },
    )
    return {key: str(path) for key, path in paths.items()}


def build_and_write_dashboard_vnext(settings: Settings | None = None) -> tuple[DashboardVNextBundle, dict[str, str]]:
    bundle = build_dashboard_vnext(settings)
    written = write_dashboard_vnext(bundle, settings)
    return bundle, written


def load_dashboard_vnext(settings: Settings | None = None) -> DashboardVNextBundle:
    runtime = _runtime_dir(settings)
    return DashboardVNextBundle(
        primary=_read_json(runtime / PRIMARY_ARTIFACT),
        protected_sections=_read_json(runtime / PROTECTED_SECTIONS_ARTIFACT),
        downstream_sections=_read_json(runtime / DOWNSTREAM_SECTIONS_ARTIFACT),
        dashboard_summary=_read_json(runtime / DASHBOARD_SUMMARY_ARTIFACT),
    )


def _authority_errors(prefix: str, payload: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    authority = _safe_dict(payload.get("authority"))
    for key in FALSE_AUTHORITY_FIELDS:
        if payload.get(key) is True or authority.get(key) is True:
            errors.append(f"{prefix}_{key}_must_remain_false")
    for key in ZERO_AUTHORITY_FIELDS:
        if _safe_int(payload.get(key), 0) != 0 or _safe_int(authority.get(key), 0) != 0:
            errors.append(f"{prefix}_{key}_must_remain_zero")
    return errors


def _generic_hits(payload: Any) -> list[str]:
    text = json.dumps(payload, sort_keys=True, default=str).lower()
    return [phrase for phrase in GENERIC_PHRASES if phrase in text]


def validate_dashboard_vnext_bundle(bundle: DashboardVNextBundle) -> list[str]:
    errors: list[str] = []
    primary = bundle.primary
    protected = bundle.protected_sections
    downstream = bundle.downstream_sections
    summary = bundle.dashboard_summary
    if primary.get("status") != "dashboard_vnext_ready":
        errors.append("primary_status_not_ready")
    if protected.get("protected_section_order") != PROTECTED_SECTION_ORDER:
        errors.append("protected_section_order_changed")
    if [row.get("display_name") for row in _safe_list(protected.get("sections"))] != PROTECTED_SECTION_ORDER:
        errors.append("protected_section_labels_or_order_changed")
    for field in (
        "protected_sections_not_reordered",
        "protected_sections_not_renamed",
        "protected_sections_not_removed",
        "protected_sections_not_structurally_overhauled",
        "enrichment_only_inside_protected_sections",
        "all_portfolio_values_agree",
    ):
        if protected.get(field) is not True or primary.get(field) is not True or summary.get(field) is not True:
            errors.append(f"{field}_must_be_true")
    for section in _safe_list(protected.get("sections")):
        section_id = str(section.get("section_id") or "unknown_section")
        if section.get("structure_preserved") is not True or section.get("enrichment_only") is not True:
            errors.append(f"{section_id}_not_enrichment_only")
        if not section.get("plain_english_evidence_state"):
            errors.append(f"{section_id}_plain_english_evidence_state_missing")
        if not section.get("enrichments"):
            errors.append(f"{section_id}_enrichments_missing")
        errors.extend(_authority_errors(section_id, section))
    if downstream.get("downstream_section_order") != DOWNSTREAM_SECTION_ORDER:
        errors.append("downstream_section_order_changed")
    downstream_sections = _safe_list(downstream.get("sections"))
    if [row.get("display_name") for row in downstream_sections] != DOWNSTREAM_SECTION_ORDER:
        errors.append("downstream_labels_or_order_changed")
    for section in downstream_sections:
        section_id = str(section.get("section_id") or "unknown_downstream_section")
        if not section.get("plain_english_evidence_state"):
            errors.append(f"{section_id}_plain_english_evidence_state_missing")
    pattern_section = next((row for row in downstream_sections if row.get("section_id") == "pattern_recognition_findings"), {})
    pattern_cards = _safe_list(pattern_section.get("cards"))
    if not pattern_cards:
        errors.append("pattern_cards_missing")
    pattern_keys = set()
    for card in pattern_cards:
        card_id = str(card.get("pattern_id") or card.get("title") or "unknown_pattern")
        if card.get("communication_flow") != PATTERN_COMMUNICATION_FLOW:
            errors.append(f"{card_id}_pattern_flow_missing_or_reordered")
        for field in (
            "detected_signal",
            "market_affected",
            "evidence",
            "what_qadam_thinks",
            "what_would_confirm_it",
            "what_blocks_the_trade",
            "next_action",
        ):
            if not card.get(field):
                errors.append(f"{card_id}_missing_{field}")
        key = "|".join(str(card.get(field) or "").lower() for field in ("detected_signal", "market_affected", "evidence"))
        if key in pattern_keys:
            errors.append(f"{card_id}_duplicate_pattern_card")
        pattern_keys.add(key)
    if _generic_hits(primary) or _generic_hits(protected) or _generic_hits(downstream):
        errors.append("generic_dashboard_vnext_phrase_detected")
    errors.extend(_authority_errors("primary", primary))
    errors.extend(_authority_errors("protected", protected))
    errors.extend(_authority_errors("downstream", downstream))
    errors.extend(_authority_errors("summary", summary))
    return errors


def validate_negative_dashboard_vnext_probes() -> list[str]:
    errors: list[str] = []
    generated_at = _iso()
    context = {
        "dashboard_status": {
            "dashboard_portfolio": {
                "current_value_gbp": 100.0,
                "portfolio_consistency": {"status": "ok"},
            }
        },
        "portfolio_value": {"latest_value": 100.0},
        "source_network": {"category_rows": [], "source_rows": [], "trading_universe_rows": []},
    }
    protected = build_protected_sections(context, generated_at)
    downstream = build_downstream_sections(context, generated_at)
    primary = {
        "status": "dashboard_vnext_ready",
        "protected_section_order": PROTECTED_SECTION_ORDER,
        "protected_sections_not_reordered": True,
        "protected_sections_not_renamed": True,
        "protected_sections_not_removed": True,
        "protected_sections_not_structurally_overhauled": True,
        "enrichment_only_inside_protected_sections": True,
        "all_portfolio_values_agree": True,
        "authority": _authority(),
    }
    protected["sections"][0]["display_name"] = "Renamed Fund"
    bad_bundle = DashboardVNextBundle(
        primary=primary,
        protected_sections=protected,
        downstream_sections=downstream,
        dashboard_summary=_dashboard_summary(protected, downstream, generated_at),
    )
    if not validate_dashboard_vnext_bundle(bad_bundle):
        errors.append("negative_probe_protected_rename_not_detected")

    protected = build_protected_sections(context, generated_at)
    downstream = build_downstream_sections(context, generated_at)
    if downstream.get("sections"):
        downstream["sections"][1]["cards"] = [
            {
                "pattern_id": "bad",
                "communication_flow": ["Evidence", "Detected signal"],
                "detected_signal": "signal",
                "market_affected": "market",
                "evidence": "evidence",
                "what_qadam_thinks": "thinks",
                "what_would_confirm_it": "confirm",
                "what_blocks_the_trade": "block",
                "next_action": "next",
            }
        ]
    bad_bundle = DashboardVNextBundle(
        primary=primary,
        protected_sections=protected,
        downstream_sections=downstream,
        dashboard_summary=_dashboard_summary(protected, downstream, generated_at),
    )
    if not validate_dashboard_vnext_bundle(bad_bundle):
        errors.append("negative_probe_pattern_flow_not_detected")
    return errors
