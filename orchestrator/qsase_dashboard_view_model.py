"""QSASE-13 Dashboard Visibility view model.

The dashboard view model mirrors QSASE and PaperOps runtime state as compact,
public-safe decision records. It is read-only: it cannot create trade intents,
qualified setups, approvals, paper orders, broker writes, proof credit, live
capital, or simulated 30-day paper growth trial progress.
"""

from __future__ import annotations

import copy
import hashlib
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from orchestrator.config import Settings
from orchestrator.qadam_paper_epoch import (
    canonical_money,
    filter_current_epoch_records,
    record_matches_epoch,
)
from orchestrator.qadam_next_generation_safety_lock import (
    DASHBOARD_SUMMARY_ARTIFACT as NEXT_GENERATION_BACKTEST_DASHBOARD_ARTIFACT,
    LOCK_ARTIFACT as NEXT_GENERATION_RESEARCH_LOCK_ARTIFACT,
    authority_flags as next_generation_lock_authority_flags,
)
from orchestrator.qsase_governance_safety_contract import (
    PHASE_STATUS_ARTIFACT,
    universal_authority_flags,
)

SCHEMA_VERSION = "qsase_dashboard_view_model.v1"
PHASE_ID = "qsase_13_dashboard_visibility"
PHASE_NAME = "QSASE-13: Dashboard Visibility"
IMPLEMENTATION_LOG = "docs/qsase-implementation-log.md"

STATUS_ARTIFACT = "qsase_dashboard_status.json"
DECISION_RECORDS_ARTIFACT = "qsase_dashboard_decision_records.json"
SYSTEM_MAP_ARTIFACT = "qsase_dashboard_system_map.json"
PORTFOLIO_SERIES_ARTIFACT = "qsase_dashboard_portfolio_value_series.json"
CURRENT_PORTFOLIO_ARTIFACT = "qsase_dashboard_current_portfolio.json"
TRADING_HISTORY_ARTIFACT = "qsase_dashboard_trading_history.json"
SOURCE_NETWORK_ARTIFACT = "qsase_dashboard_source_network.json"
STRATEGY_UNIVERSE_ARTIFACT = "qsase_dashboard_strategy_universe.json"
PATTERN_LAB_ARTIFACT = "qsase_dashboard_pattern_lab.json"
TRADE_INTENTS_ARTIFACT = "qsase_dashboard_trade_intents.json"
LEARNING_LEDGER_ARTIFACT = "qsase_dashboard_learning_ledger.json"
REPAIR_QUEUE_ARTIFACT = "qsase_dashboard_repair_queue.json"
PATTERN_TO_PAPER_WORKFLOW_ARTIFACT = "qsase_pattern_to_paper_workflow.json"
PATTERN_INTELLIGENCE_ARTIFACT = "qsase_pattern_intelligence.json"
EVIDENCE_QUALITY_ARTIFACT = "qsase_evidence_quality_engine.json"
ANTI_SLOP_ARTIFACT = "qsase_dashboard_anti_slop_audit.json"
HISTORY_ARTIFACT = "qsase_dashboard_view_model_history.jsonl"
EVENTS_ARTIFACT = "qsase_dashboard_view_model_events.jsonl"

ALPACA_PAPER_MIRROR_ARTIFACT = "alpaca_paper_mirror.json"
ALPACA_PAPER_MIRROR_HISTORY_ARTIFACT = "alpaca_paper_mirror.jsonl"
PAPER_POSITIONS_ARTIFACT = "paper_positions.jsonl"
PAPER_ORDERS_ARTIFACT = "paper_orders.jsonl"
PAPER_CLOSED_TRADES_ARTIFACT = "paper_closed_trades.jsonl"
COCKPIT_STATUS_ARTIFACT = "cockpit-status.json"
SELF_MODEL_ARTIFACT = "qsase_self_model.json"
UNIVERSAL_MATRIX_ARTIFACT = "qsase_universal_source_price_matrix.json"
PATTERN_ENGINE_ARTIFACT = "pattern_recognition_engine.json"
EDGE_PATTERN_LEDGER_ARTIFACT = "edge_pattern_ledger.json"
STRATEGY_FAMILY_MAP_ARTIFACT = "qsase_strategy_family_map.json"
STRATEGY_FOUNDRY_ARTIFACT = "qsase_strategy_hypotheses.json"
STRATEGY_HYPOTHESES_ARTIFACT = "qsase_strategy_hypotheses.jsonl"
REJECTED_STRATEGY_HYPOTHESES_ARTIFACT = "qsase_rejected_strategy_hypotheses.jsonl"
AKBER_FILTER_ARTIFACT = "qsase_akber_filter_integration.json"
AKBER_FILTER_RESULTS_ARTIFACT = "qsase_akber_filter_results.jsonl"
LINEAR_LAB_ARTIFACT = "qsase_linear_pattern_lab.json"
LINEAR_RESULTS_ARTIFACT = "qsase_linear_backtest_results.jsonl"
NONLINEAR_LAB_ARTIFACT = "qsase_nonlinear_quantum_pattern_lab.json"
NONLINEAR_RESULTS_ARTIFACT = "qsase_nonlinear_pattern_results.jsonl"
QUANTUM_REVIEWS_ARTIFACT = "qsase_quantum_pattern_reviews.jsonl"
ROUTER_ARTIFACT = "qsase_strategy_router_decisions.json"
ROUTER_DECISIONS_ARTIFACT = "qsase_strategy_router_decisions.jsonl"
PAPEROPS_GATE_ARTIFACT = "qsase_paperops_gate_interface.json"
PAPEROPS_GATE_RECORDS_ARTIFACT = "qsase_paperops_gate_interface.jsonl"
COMPONENT_ATTRIBUTION_LEDGER_ARTIFACT = "qsase_component_attribution_ledger.json"
LEARNING_LEDGER_RECORDS_ARTIFACT = "qsase_component_attribution_ledger.jsonl"
LEARNING_APPROVAL_QUEUE_ARTIFACT = "qsase_learning_approval_queue.json"
PAPEROPS_SUMMARY_ARTIFACT = "paperops_autonomous_pass_summary.json"
DAILY_TELEGRAM_LEARNING_BRIEF_ARTIFACT = "daily_telegram_learning_brief.json"
TELEGRAM_HUMAN_BRIEF_ARTIFACT = "telegram_human_brief.json"
WHOLE_UNIVERSE_BACKFILL_BACKTEST_DASHBOARD_ARTIFACT = "qsase_whole_universe_backfill_backtest_dashboard_summary.json"
EVIDENCE_CONTRACTS_DASHBOARD_ARTIFACT = "qadam_evidence_contracts_dashboard_summary.json"
WORLD_MODEL_DASHBOARD_ARTIFACT = "qadam_world_model_dashboard_summary.json"
PATTERN_ENGINE_V2_DASHBOARD_ARTIFACT = "qadam_pattern_engine_v2_dashboard_summary.json"
STRATEGY_EVIDENCE_MAP_DASHBOARD_ARTIFACT = "qadam_strategy_evidence_map_dashboard_summary.json"
STRATEGY_EVIDENCE_MAP_RECORDS_ARTIFACT = "qadam_strategy_evidence_map_records.jsonl"
STRATEGY_FOUNDRY_V2_DASHBOARD_ARTIFACT = "qadam_strategy_foundry_v2_dashboard_summary.json"
AKBER_FILTER_V2_DASHBOARD_ARTIFACT = "qadam_akber_filter_v2_dashboard_summary.json"
AKBER_FILTER_V2_RESULTS_ARTIFACT = "qadam_akber_filter_v2_results.jsonl"
SHADOW_SIMULATOR_V2_DASHBOARD_ARTIFACT = "qadam_shadow_simulator_v2_dashboard_summary.json"
ROUTER_V2_DASHBOARD_ARTIFACT = "qadam_router_v2_dashboard_summary.json"
ROUTER_V2_DECISIONS_ARTIFACT = "qadam_router_v2_decisions.jsonl"
PAPER_LIFECYCLE_V2_DASHBOARD_ARTIFACT = "qadam_paper_lifecycle_v2_dashboard_summary.json"
LEARNING_ATTRIBUTION_V2_DASHBOARD_ARTIFACT = "qadam_learning_attribution_v2_dashboard_summary.json"
DASHBOARD_VNEXT_DASHBOARD_ARTIFACT = "qadam_dashboard_vnext_dashboard_summary.json"
TELEGRAM_VNEXT_DASHBOARD_ARTIFACT = "qadam_telegram_vnext_dashboard_summary.json"
TELEGRAM_VNEXT_COMMUNICATIONS_MIRROR_ARTIFACT = "qadam_telegram_next_generation_dashboard_communications_mirror.json"
QADAM_SELF_HEALING_STATUS_ARTIFACT = "qadam_self_healing_status.json"
QADAM_SELF_HEALING_DASHBOARD_ARTIFACT = "qadam_self_healing_dashboard_summary.json"
QADAM_SELF_HEALING_REPAIR_QUEUE_ARTIFACT = "qadam_self_healing_repair_queue.json"
PATTERN_SCORE_V3_ARTIFACT = "qadam_pattern_score_v3.json"
PATTERN_SCORE_V3_RECORDS_ARTIFACT = "qadam_pattern_score_v3_records.jsonl"
BACKTEST_RESULTS_SUMMARY_ARTIFACT = "qadam_backtest_results_summary.json"
QUANTUM_USEFULNESS_SUMMARY_ARTIFACT = "qadam_quantum_usefulness_summary.json"
EDGE_REGISTRY_SUMMARY_ARTIFACT = "qadam_edge_registry_summary.json"
STRATEGY_EVIDENCE_MAP_V3_ARTIFACT = "qadam_strategy_evidence_map_v3.json"
NEW_STRATEGY_FAMILY_PROPOSALS_ARTIFACT = "qadam_new_strategy_family_proposals.jsonl"
STRATEGY_FOUNDRY_V3_ARTIFACT = "qadam_strategy_foundry_v3.json"
STRATEGY_HYPOTHESES_V3_ARTIFACT = "qadam_strategy_hypotheses_v3.jsonl"
STRATEGY_HYPOTHESIS_REJECTIONS_V3_ARTIFACT = "qadam_strategy_hypothesis_rejections_v3.jsonl"
UNUSUAL_WHALES_RESEARCH_STATUS_ARTIFACT = "unusual_whales_research_status.json"
UNUSUAL_WHALES_FEATURE_MANIFEST_ARTIFACT = "unusual_whales_backtest_feature_manifest.json"
POWER_MARKET_CHECK_ARTIFACT = "qadam_power_market_edge_engine_checks.json"
POWER_MARKET_STRATEGY_ARTIFACT = "qadam_power_market_strategy_registry.json"
POWER_MARKET_DASHBOARD_ARTIFACT = "qadam_power_market_dashboard_summary.json"
POWER_MARKET_SCORES_ARTIFACT = "qadam_power_market_pattern_scores.jsonl"
LAYERED_MARKET_JUDGMENT_DASHBOARD_ARTIFACT = (
    "qadam_layered_market_judgment_dashboard.json"
)

DASHBOARD_AUTHORITY_FLAGS = {
    "dashboard_read_only": True,
    "dashboard_mirror_only": True,
    "dashboard_command_disabled": True,
    "broker_write_allowed": False,
    "live_broker_endpoint_allowed": False,
    "paper_order_allowed": False,
    "paper_order_created": False,
    "qualified_setup_created": False,
    "trade_candidate_created": False,
    "trade_intent_created": False,
    "risk_approval_allowed": False,
    "risk_approval_created": False,
    "execution_approval_allowed": False,
    "execution_approval_created": False,
    "strategy_mutation_created": False,
    "source_trust_update_created": False,
    "model_weight_update_created": False,
    "filter_threshold_update_created": False,
    "proof_credit_allowed": False,
    "paper_proof_ledger_credit_allowed": False,
    "paper_growth_trial_calendar_advance_allowed": False,
    "simulated_elapsed_time_allowed": False,
    "telegram_command_path_enabled": False,
    "telegram_trade_command_enabled": False,
    "live_capital_enabled": False,
}

FALSE_AUTHORITY_FIELDS = {
    key for key, value in DASHBOARD_AUTHORITY_FLAGS.items() if value is False
}

REQUIRED_DECISION_RECORD_FIELDS = (
    "decision_record_id",
    "module",
    "state",
    "headline",
    "reason",
    "blocker",
    "next_allowed_action",
    "authority_boundary",
    "artifact_refs",
    "applied_change",
    "paper_order_created",
    "proof_credit_allowed",
    "live_capital_enabled",
)

GENERIC_AI_PHRASES = (
    "ai-powered",
    "cutting edge",
    "cutting-edge",
    "seamless",
    "holistic",
    "synergy",
    "synergise",
    "unlock potential",
    "revolutionary",
    "game-changing",
    "robust insights",
    "dynamic insights",
    "qadam learned",
    "transformative",
)

PROHIBITED_INTENT_LABELS = {"trade", "order", "approval", "qualified_setup", "paper_order"}

FRESHNESS_THRESHOLDS_SECONDS = {
    ALPACA_PAPER_MIRROR_ARTIFACT: 7200,
    PAPEROPS_SUMMARY_ARTIFACT: 7200,
    COCKPIT_STATUS_ARTIFACT: 7200,
    SELF_MODEL_ARTIFACT: 14400,
    PATTERN_ENGINE_ARTIFACT: 14400,
    EDGE_PATTERN_LEDGER_ARTIFACT: 14400,
    EVIDENCE_QUALITY_ARTIFACT: 14400,
    ROUTER_ARTIFACT: 14400,
    PAPEROPS_GATE_ARTIFACT: 14400,
    COMPONENT_ATTRIBUTION_LEDGER_ARTIFACT: 14400,
    NEXT_GENERATION_BACKTEST_DASHBOARD_ARTIFACT: 7200,
    WHOLE_UNIVERSE_BACKFILL_BACKTEST_DASHBOARD_ARTIFACT: 7200,
    EVIDENCE_CONTRACTS_DASHBOARD_ARTIFACT: 7200,
    WORLD_MODEL_DASHBOARD_ARTIFACT: 7200,
    PATTERN_ENGINE_V2_DASHBOARD_ARTIFACT: 7200,
    STRATEGY_EVIDENCE_MAP_DASHBOARD_ARTIFACT: 7200,
    STRATEGY_FOUNDRY_V2_DASHBOARD_ARTIFACT: 7200,
    AKBER_FILTER_V2_DASHBOARD_ARTIFACT: 7200,
    SHADOW_SIMULATOR_V2_DASHBOARD_ARTIFACT: 7200,
    ROUTER_V2_DASHBOARD_ARTIFACT: 7200,
    PAPER_LIFECYCLE_V2_DASHBOARD_ARTIFACT: 7200,
    LEARNING_ATTRIBUTION_V2_DASHBOARD_ARTIFACT: 7200,
    DASHBOARD_VNEXT_DASHBOARD_ARTIFACT: 7200,
    TELEGRAM_VNEXT_DASHBOARD_ARTIFACT: 7200,
    TELEGRAM_VNEXT_COMMUNICATIONS_MIRROR_ARTIFACT: 7200,
    QADAM_SELF_HEALING_STATUS_ARTIFACT: 7200,
    QADAM_SELF_HEALING_DASHBOARD_ARTIFACT: 7200,
    QADAM_SELF_HEALING_REPAIR_QUEUE_ARTIFACT: 7200,
    LAYERED_MARKET_JUDGMENT_DASHBOARD_ARTIFACT: 900,
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


def _append_jsonl(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(_jsonl_line(payload))


def _hash_id(parts: list[Any], prefix: str) -> str:
    raw = "|".join(str(part) for part in parts)
    return f"{prefix}:{hashlib.sha256(raw.encode('utf-8')).hexdigest()[:20]}"


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


def _int(value: Any, default: int = 0) -> int:
    if isinstance(value, bool):
        return default
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(value)
    if isinstance(value, str):
        try:
            return int(float(value))
        except ValueError:
            return default
    return default


def _first_text(*values: Any, default: str = "not_recorded") -> str:
    for value in values:
        if value is None:
            continue
        text = str(value).strip()
        if text:
            return text
    return default


def _safe_list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def _artifact_ref(filename: str, pointer: str | None = None) -> str:
    base = f"data/runtime/{filename}"
    return f"{base}#{pointer}" if pointer else base


SOURCE_FAMILY_DESCRIPTIONS = {
    "conflict": (
        "Conflict and geopolitics feeds track wars, sanctions, political violence, and government-risk events "
        "that can move oil, defence, shipping, currencies, and prediction markets."
    ),
    "macro": (
        "Macro and trade feeds give Qadam the economic backdrop: rates, inflation, trade flows, inventories, "
        "industrial activity, and country-level pressure that may change market regimes."
    ),
    "market": (
        "Market feeds provide the direct trading lens: prices, technical context, paper broker mirrors, prediction "
        "market order books, options context, and execution-safe market state."
    ),
    "market_context_taxonomy": (
        "Market-context taxonomy feeds map raw sources into the actual sleeves Qadam watches, so a shipping, "
        "energy, chip, defence, or prediction-market signal is routed to the right strategy family."
    ),
    "physical": (
        "Physical-world feeds watch real-world movement and constraints: ships, flights, weather, fires, ports, "
        "infrastructure, geospatial activity, and supply-chain pressure."
    ),
    "power_grid_constraints": (
        "Power and grid-constraint feeds track expected electricity demand, renewable supply, regional prices, "
        "and congestion so Qadam can test whether physical grid pressure appears before listed power assets move."
    ),
    "social": (
        "Social, news, filings, and web feeds watch public narrative, attention shifts, regulatory filings, "
        "developer/news activity, and human crowd signals that can strengthen or weaken a hypothesis."
    ),
}


STRATEGY_PLAYBOOK_DESCRIPTIONS = {
    "crude_oil_energy_security_disruption": {
        "plain_english_summary": "Qadam watches whether real-world disruption is making oil harder to move before oil markets fully react.",
        "how_strategy_works": "If conflict, sanctions, fires, port disruption, or shipping stress threaten the flow of energy, Qadam compares those events with oil prices and energy-company prices. The basic idea is simple: if the world is making oil supply riskier, oil-linked instruments may need to reprice.",
        "why_this_can_create_an_edge": "Oil markets can move before headlines are obvious, but they can also ignore early disruption. Qadam tries to find the moments where physical-world evidence appears before the price response is complete.",
        "example_scenario": "If conflict data and vessel movements show stress near a major energy route while USO or XLE have not moved much, Qadam treats that as a research question: is the market underpricing the disruption?",
        "what_qadam_watches": "Conflict events, shipping routes, satellite fire data, curated conflict trackers, crude oil futures, oil ETFs, and energy equities.",
        "core_instruments": [
            {"symbol": "USO", "role": "Paper-tradable oil ETF proxy", "explanation": "A practical way to express broad US crude-oil price exposure through the guarded Alpaca Paper route."},
            {"symbol": "XLE", "role": "Energy-company basket", "explanation": "Shows whether energy producers are being repriced alongside oil disruption."},
            {"symbol": "BNO", "role": "Brent oil proxy", "explanation": "Useful when the disruption is more global or seaborne than US-specific."},
            {"symbol": "CL=F", "role": "Crude futures reference", "explanation": "The direct oil-price reference Qadam studies, but not a direct Alpaca paper order target."},
        ],
        "secondary_instruments": [
            {"symbol": "XOP", "role": "Exploration and production context", "explanation": "Can show whether smaller producers are reacting differently from broad energy ETFs."},
            {"symbol": "OIH", "role": "Oil-services context", "explanation": "Can react when drilling, production, or service demand changes."},
            {"symbol": "XOM", "role": "Large producer context", "explanation": "A liquid single-name reference for major integrated oil-company repricing."},
            {"symbol": "CVX", "role": "Large producer context", "explanation": "A second large energy company for cross-checking producer repricing."},
            {"symbol": "BZ=F", "role": "Brent futures reference", "explanation": "Research-only global oil benchmark for seaborne supply stress."},
            {"symbol": "RB=F", "role": "Gasoline futures context", "explanation": "Helps check whether refined-product markets confirm crude disruption."},
        ],
    },
    "defence_repricing_geopolitical_watch": {
        "plain_english_summary": "Qadam watches whether rising geopolitical risk could make defence companies more valuable.",
        "how_strategy_works": "When the world becomes more dangerous, governments may spend more on security, weapons, aerospace, surveillance, and defence infrastructure. Qadam looks for evidence that conflict risk or policy attention is increasing before defence assets have fully repriced.",
        "why_this_can_create_an_edge": "Defence repricing can happen slowly because procurement cycles, filings, and policy signals are scattered. Qadam tries to connect those signals before they become obvious in market prices.",
        "example_scenario": "If conflict events rise, defence-related filings increase, and policy news becomes more intense while defence ETFs are still quiet, Qadam marks the strategy as evidence-building.",
        "what_qadam_watches": "Conflict data, GDELT news, SEC filings, patent activity, Capitol/Stock Act disclosures, defence ETFs, and major contractors.",
        "core_instruments": [
            {"symbol": "ITA", "role": "US aerospace and defence ETF", "explanation": "A broad paper-tradable basket for US defence-sector exposure."},
            {"symbol": "XAR", "role": "Equal-weight aerospace and defence ETF", "explanation": "Helps avoid relying only on the largest defence names."},
            {"symbol": "PPA", "role": "Defence and aerospace ETF", "explanation": "A second sector basket for checking whether the move is broad."},
            {"symbol": "LMT", "role": "Large defence contractor", "explanation": "A liquid single-name reference for major contractor repricing."},
        ],
        "secondary_instruments": [
            {"symbol": "NOC", "role": "Major contractor context", "explanation": "Useful for aerospace, missile, and defence-program confirmation."},
            {"symbol": "RTX", "role": "Major contractor context", "explanation": "Can confirm whether defence and aerospace exposure is broadening."},
            {"symbol": "GD", "role": "Contractor context", "explanation": "Adds land, marine, and defence-systems context."},
            {"symbol": "LHX", "role": "Defence technology context", "explanation": "Helps track electronics, sensors, communications, and space-defence themes."},
            {"symbol": "BA", "role": "Aerospace context", "explanation": "Useful but noisier because commercial aviation can dominate the signal."},
        ],
    },
    "prediction_market_geopolitical_dislocation": {
        "plain_english_summary": "Qadam watches when event-market odds disagree with the wider real-world evidence picture.",
        "how_strategy_works": "Prediction markets put prices on future events. Qadam compares those odds with news, conflict data, social narrative, and related market behavior. If the odds look too calm or too extreme compared with the evidence, Qadam studies the dislocation.",
        "why_this_can_create_an_edge": "Event markets can be thin, emotional, or slow to absorb outside evidence. Qadam looks for moments where probability prices and real-world evidence are out of sync.",
        "example_scenario": "If conflict evidence is escalating but an event contract still prices low risk, Qadam records the gap as a hypothesis rather than immediately treating it as a trade.",
        "what_qadam_watches": "Kalshi, Polymarket, GDELT, ACLED, Telegram intake, related ETFs, and macro/commodity proxies linked to the event.",
        "core_instruments": [
            {"symbol": "KALSHI:EVENTS", "role": "Regulated event-contract context", "explanation": "Shows how regulated event markets price a future outcome."},
            {"symbol": "POLYMARKET:EVENTS", "role": "Prediction-market context", "explanation": "Shows crowd-implied probabilities and liquidity around geopolitical or macro events."},
        ],
        "secondary_instruments": [
            {"symbol": "USO", "role": "Oil confirmation proxy", "explanation": "Useful when the event should affect energy prices."},
            {"symbol": "ITA", "role": "Defence confirmation proxy", "explanation": "Useful when the event should affect security or defence spending."},
            {"symbol": "SPY", "role": "Risk-market context", "explanation": "Helps check whether broad markets agree with the event risk."},
        ],
    },
    "semiconductor_policy_options_asymmetry": {
        "plain_english_summary": "Qadam watches whether chip companies are mispriced after policy, supply-chain, AI, or export-control signals.",
        "how_strategy_works": "Semiconductor assets react to policy, AI demand, export restrictions, supply-chain bottlenecks, filings, and innovation signals. Qadam compares those sources with chip ETFs and key chip names to see whether the sector has reacted enough.",
        "why_this_can_create_an_edge": "Chip-market signals are spread across government policy, patents, filings, news, and company-specific narratives. Qadam tries to combine them into one clearer view.",
        "example_scenario": "If export-control news and filings suggest pressure on chip supply while SMH or SOXX have not reflected it, Qadam treats that as a possible asymmetry to test.",
        "what_qadam_watches": "SEC filings, patents, RSS/news, GDELT, Capitol/Stock Act disclosures, semiconductor ETFs, and large chip companies.",
        "core_instruments": [
            {"symbol": "SMH", "role": "Semiconductor ETF", "explanation": "Broad paper-tradable chip-sector exposure."},
            {"symbol": "SOXX", "role": "Semiconductor ETF", "explanation": "A second chip-sector basket for confirmation."},
            {"symbol": "NVDA", "role": "AI-chip bellwether", "explanation": "A high-attention chip name that can dominate AI and semiconductor narratives."},
            {"symbol": "QQQ", "role": "Technology-market context", "explanation": "Shows whether the broader technology market confirms or rejects the chip signal."},
        ],
        "secondary_instruments": [
            {"symbol": "AMD", "role": "Chip single-name context", "explanation": "Useful for AI and CPU/GPU competition signals."},
            {"symbol": "TSM", "role": "Foundry context", "explanation": "Useful for manufacturing, Taiwan, and supply-chain risk."},
            {"symbol": "ASML", "role": "Semiconductor equipment context", "explanation": "Important for export controls and advanced-chip manufacturing constraints."},
            {"symbol": "AVGO", "role": "Chip infrastructure context", "explanation": "Adds networking, AI infrastructure, and diversified chip exposure."},
            {"symbol": "MU", "role": "Memory-cycle context", "explanation": "Useful when the signal is tied to memory supply or demand."},
        ],
    },
    "silver_macro_liquidity_stress": {
        "plain_english_summary": "Qadam watches whether silver is acting like a stress signal when money, rates, inflation, or the dollar become unstable.",
        "how_strategy_works": "Silver can behave like a precious metal, an industrial metal, or a liquidity-stress instrument. Qadam compares macro data, dollar/rate pressure, commodities, and silver-linked instruments to see which role silver is playing.",
        "why_this_can_create_an_edge": "Silver can move sharply when macro conditions shift, but the reason is often unclear. Qadam tries to identify which macro regime is actually driving the move before treating it as tradeable.",
        "example_scenario": "If real-yield or dollar pressure changes while silver begins outperforming related assets, Qadam asks whether this is a repeatable liquidity-stress pattern.",
        "what_qadam_watches": "FRED, ECB, BIS, USGS, UN Comtrade, silver ETFs, silver miners, gold, dollar/rate proxies, and broad equity risk.",
        "core_instruments": [
            {"symbol": "SLV", "role": "Silver ETF proxy", "explanation": "The practical paper-tradable proxy for silver exposure."},
            {"symbol": "SIL", "role": "Silver-miner ETF", "explanation": "Shows whether mining equities confirm the silver move."},
            {"symbol": "SI=F", "role": "Silver futures reference", "explanation": "The direct silver-price reference Qadam studies, but not a direct Alpaca paper order target."},
        ],
        "secondary_instruments": [
            {"symbol": "GLD", "role": "Gold comparison", "explanation": "Helps separate precious-metal demand from silver-specific behavior."},
            {"symbol": "GDX", "role": "Gold-miner context", "explanation": "Checks whether metal miners broadly confirm the stress signal."},
            {"symbol": "TLT", "role": "Rates context", "explanation": "Helps show whether bond/rate moves are driving the metal signal."},
            {"symbol": "UUP", "role": "Dollar context", "explanation": "A dollar proxy because silver often reacts to dollar strength or weakness."},
            {"symbol": "SPY", "role": "Risk-market context", "explanation": "Helps determine whether silver is moving with or against broad risk appetite."},
        ],
    },
}


def _source_family_description(family: Any) -> str:
    key = str(family or "").strip().lower()
    return SOURCE_FAMILY_DESCRIPTIONS.get(
        key,
        "This source category contributes read-only evidence to Qadam's hypothesis engine. It can inform a pattern, but it cannot create trades.",
    )


def _dashboard_authority() -> dict[str, Any]:
    return dict(DASHBOARD_AUTHORITY_FLAGS)


def _parse_timestamp(value: Any) -> datetime | None:
    if not isinstance(value, str) or not value.strip():
        return None
    text = value.strip()
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    try:
        return datetime.fromisoformat(text).astimezone(timezone.utc)
    except ValueError:
        return None


def _file_snapshot(runtime_dir: Path, filename: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
    path = runtime_dir / filename
    if not path.exists():
        return {
            "artifact": _artifact_ref(filename),
            "exists": False,
            "generated_at": None,
            "mtime": None,
            "age_seconds": None,
            "freshness_status": "missing",
            "staleness_label": "missing_input",
        }
    loaded = payload if payload is not None else _read_json(path)
    generated_at = loaded.get("generated_at") or loaded.get("snapshot", {}).get("observed_at") or loaded.get("observed_at")
    generated_dt = _parse_timestamp(generated_at)
    mtime = datetime.fromtimestamp(path.stat().st_mtime, tz=timezone.utc)
    reference_dt = generated_dt or mtime
    age_seconds = int((_now() - reference_dt).total_seconds())
    threshold = FRESHNESS_THRESHOLDS_SECONDS.get(filename, 21600)
    freshness_status = "fresh" if age_seconds <= threshold else "stale_labeled"
    return {
        "artifact": _artifact_ref(filename),
        "exists": True,
        "generated_at": generated_at,
        "mtime": _iso(mtime),
        "age_seconds": age_seconds,
        "freshness_threshold_seconds": threshold,
        "freshness_status": freshness_status,
        "staleness_label": "fresh" if freshness_status == "fresh" else f"stale_over_{threshold}_seconds",
    }


def _load_context(settings: Settings | None = None) -> dict[str, Any]:
    runtime = _runtime_dir(settings)
    json_files = {
        "alpaca_mirror": ALPACA_PAPER_MIRROR_ARTIFACT,
        "cockpit_status": COCKPIT_STATUS_ARTIFACT,
        "self_model": SELF_MODEL_ARTIFACT,
        "universal_matrix": UNIVERSAL_MATRIX_ARTIFACT,
        "pattern_engine": PATTERN_ENGINE_ARTIFACT,
        "edge_pattern_ledger": EDGE_PATTERN_LEDGER_ARTIFACT,
        "strategy_family_map": STRATEGY_FAMILY_MAP_ARTIFACT,
        "strategy_foundry": STRATEGY_FOUNDRY_ARTIFACT,
        "akber_filter": AKBER_FILTER_ARTIFACT,
        "linear_lab": LINEAR_LAB_ARTIFACT,
        "nonlinear_lab": NONLINEAR_LAB_ARTIFACT,
        "evidence_quality": EVIDENCE_QUALITY_ARTIFACT,
        "router": ROUTER_ARTIFACT,
        "paperops_gate": PAPEROPS_GATE_ARTIFACT,
        "learning_ledger": COMPONENT_ATTRIBUTION_LEDGER_ARTIFACT,
        "learning_approval_queue": LEARNING_APPROVAL_QUEUE_ARTIFACT,
        "paperops_summary": PAPEROPS_SUMMARY_ARTIFACT,
        "daily_telegram_learning_brief": DAILY_TELEGRAM_LEARNING_BRIEF_ARTIFACT,
        "telegram_human_brief": TELEGRAM_HUMAN_BRIEF_ARTIFACT,
        "next_generation_research_lock": NEXT_GENERATION_RESEARCH_LOCK_ARTIFACT,
        "next_generation_backtest_dashboard": NEXT_GENERATION_BACKTEST_DASHBOARD_ARTIFACT,
        "whole_universe_backfill_backtest_dashboard": WHOLE_UNIVERSE_BACKFILL_BACKTEST_DASHBOARD_ARTIFACT,
        "evidence_contracts_dashboard": EVIDENCE_CONTRACTS_DASHBOARD_ARTIFACT,
        "world_model_dashboard": WORLD_MODEL_DASHBOARD_ARTIFACT,
        "pattern_engine_v2_dashboard": PATTERN_ENGINE_V2_DASHBOARD_ARTIFACT,
        "strategy_evidence_map_dashboard": STRATEGY_EVIDENCE_MAP_DASHBOARD_ARTIFACT,
        "strategy_foundry_v2_dashboard": STRATEGY_FOUNDRY_V2_DASHBOARD_ARTIFACT,
        "akber_filter_v2_dashboard": AKBER_FILTER_V2_DASHBOARD_ARTIFACT,
        "shadow_simulator_v2_dashboard": SHADOW_SIMULATOR_V2_DASHBOARD_ARTIFACT,
        "router_v2_dashboard": ROUTER_V2_DASHBOARD_ARTIFACT,
        "paper_lifecycle_v2_dashboard": PAPER_LIFECYCLE_V2_DASHBOARD_ARTIFACT,
        "learning_attribution_v2_dashboard": LEARNING_ATTRIBUTION_V2_DASHBOARD_ARTIFACT,
        "dashboard_vnext_dashboard": DASHBOARD_VNEXT_DASHBOARD_ARTIFACT,
        "telegram_vnext_dashboard": TELEGRAM_VNEXT_DASHBOARD_ARTIFACT,
        "telegram_vnext_communications_mirror": TELEGRAM_VNEXT_COMMUNICATIONS_MIRROR_ARTIFACT,
        "qadam_self_healing_status": QADAM_SELF_HEALING_STATUS_ARTIFACT,
        "qadam_self_healing_dashboard": QADAM_SELF_HEALING_DASHBOARD_ARTIFACT,
        "qadam_self_healing_repair_queue": QADAM_SELF_HEALING_REPAIR_QUEUE_ARTIFACT,
        "pattern_score_v3": PATTERN_SCORE_V3_ARTIFACT,
        "backtest_results_summary": BACKTEST_RESULTS_SUMMARY_ARTIFACT,
        "quantum_usefulness_summary": QUANTUM_USEFULNESS_SUMMARY_ARTIFACT,
        "edge_registry_summary": EDGE_REGISTRY_SUMMARY_ARTIFACT,
        "strategy_evidence_map_v3": STRATEGY_EVIDENCE_MAP_V3_ARTIFACT,
        "strategy_foundry_v3": STRATEGY_FOUNDRY_V3_ARTIFACT,
        "unusual_whales_research_status": UNUSUAL_WHALES_RESEARCH_STATUS_ARTIFACT,
        "unusual_whales_feature_manifest": UNUSUAL_WHALES_FEATURE_MANIFEST_ARTIFACT,
        "power_market_checks": POWER_MARKET_CHECK_ARTIFACT,
        "power_market_strategy": POWER_MARKET_STRATEGY_ARTIFACT,
        "power_market_dashboard": POWER_MARKET_DASHBOARD_ARTIFACT,
        "layered_market_judgment": LAYERED_MARKET_JUDGMENT_DASHBOARD_ARTIFACT,
        "current_paper_epoch": "current_paper_epoch.json",
    }
    context: dict[str, Any] = {
        "runtime_dir": runtime,
        **{key: _read_json(runtime / filename) for key, filename in json_files.items()},
        "alpaca_history": _read_jsonl(runtime / ALPACA_PAPER_MIRROR_HISTORY_ARTIFACT, limit=120),
        "paper_positions": _read_jsonl(runtime / PAPER_POSITIONS_ARTIFACT, limit=100),
        "paper_orders": _read_jsonl(runtime / PAPER_ORDERS_ARTIFACT, limit=100),
        "paper_closed_trades": _read_jsonl(runtime / PAPER_CLOSED_TRADES_ARTIFACT, limit=100),
        "strategy_hypotheses": _read_jsonl(runtime / STRATEGY_HYPOTHESES_ARTIFACT, limit=100),
        "rejected_strategy_hypotheses": _read_jsonl(runtime / REJECTED_STRATEGY_HYPOTHESES_ARTIFACT, limit=100),
        "akber_results": _read_jsonl(runtime / AKBER_FILTER_RESULTS_ARTIFACT, limit=100),
        "linear_results": _read_jsonl(runtime / LINEAR_RESULTS_ARTIFACT, limit=100),
        "nonlinear_results": _read_jsonl(runtime / NONLINEAR_RESULTS_ARTIFACT, limit=100),
        "quantum_reviews": _read_jsonl(runtime / QUANTUM_REVIEWS_ARTIFACT, limit=100),
        "router_decisions": _read_jsonl(runtime / ROUTER_DECISIONS_ARTIFACT, limit=100),
        "strategy_evidence_map_records": _read_jsonl(runtime / STRATEGY_EVIDENCE_MAP_RECORDS_ARTIFACT, limit=100),
        "akber_v2_results": _read_jsonl(runtime / AKBER_FILTER_V2_RESULTS_ARTIFACT, limit=100),
        "router_v2_decisions": _read_jsonl(runtime / ROUTER_V2_DECISIONS_ARTIFACT, limit=100),
        "pattern_score_v3_records": _read_jsonl(runtime / PATTERN_SCORE_V3_RECORDS_ARTIFACT, limit=500),
        "power_market_pattern_scores": _read_jsonl(runtime / POWER_MARKET_SCORES_ARTIFACT, limit=100),
        "new_strategy_family_proposals": _read_jsonl(runtime / NEW_STRATEGY_FAMILY_PROPOSALS_ARTIFACT, limit=100),
        "strategy_hypotheses_v3": _read_jsonl(runtime / STRATEGY_HYPOTHESES_V3_ARTIFACT, limit=100),
        "strategy_hypothesis_rejections_v3": _read_jsonl(runtime / STRATEGY_HYPOTHESIS_REJECTIONS_V3_ARTIFACT, limit=100),
        "paperops_gate_records": _read_jsonl(runtime / PAPEROPS_GATE_RECORDS_ARTIFACT, limit=100),
        "learning_records": _read_jsonl(runtime / LEARNING_LEDGER_RECORDS_ARTIFACT, limit=150),
    }
    current_epoch = context.get("current_paper_epoch", {})
    clean_epoch = current_epoch.get("paper_epoch_kind") == "clean_operator_epoch"
    execution_rows_before = {
        key: len(context.get(key, []))
        for key in (
            "alpaca_history",
            "paper_positions",
            "paper_orders",
            "paper_closed_trades",
        )
    }
    for key in execution_rows_before:
        context[key] = filter_current_epoch_records(
            context.get(key, []),
            epoch=current_epoch,
            permit_legacy_testing_records=not clean_epoch,
        )
    context["paper_epoch_isolation"] = {
        "paper_epoch_id": current_epoch.get("paper_epoch_id"),
        "paper_epoch_kind": current_epoch.get("paper_epoch_kind") or "legacy_test",
        "strict_epoch_filtering": clean_epoch,
        "input_row_counts": execution_rows_before,
        "current_epoch_row_counts": {
            key: len(context.get(key, [])) for key in execution_rows_before
        },
        "excluded_legacy_row_counts": {
            key: execution_rows_before[key] - len(context.get(key, []))
            for key in execution_rows_before
        },
    }
    context["input_snapshots"] = {
        key: _file_snapshot(runtime, filename, context.get(key)) for key, filename in json_files.items()
    }
    context["input_snapshots"]["alpaca_history"] = _file_snapshot(runtime, ALPACA_PAPER_MIRROR_HISTORY_ARTIFACT)
    context["input_snapshots"]["paper_positions"] = _file_snapshot(runtime, PAPER_POSITIONS_ARTIFACT)
    context["input_snapshots"]["paper_orders"] = _file_snapshot(runtime, PAPER_ORDERS_ARTIFACT)
    context["input_snapshots"]["paper_closed_trades"] = _file_snapshot(runtime, PAPER_CLOSED_TRADES_ARTIFACT)
    context["input_snapshots"]["pattern_score_v3_records"] = _file_snapshot(runtime, PATTERN_SCORE_V3_RECORDS_ARTIFACT)
    context["input_snapshots"]["power_market_pattern_scores"] = _file_snapshot(runtime, POWER_MARKET_SCORES_ARTIFACT)
    context["input_snapshots"]["new_strategy_family_proposals"] = _file_snapshot(runtime, NEW_STRATEGY_FAMILY_PROPOSALS_ARTIFACT)
    context["input_snapshots"]["strategy_hypotheses_v3"] = _file_snapshot(runtime, STRATEGY_HYPOTHESES_V3_ARTIFACT)
    if context.get("power_market_checks", {}).get("safe_to_consume") is True:
        context["pattern_score_v3_records"].extend(
            row
            for row in context.get("power_market_pattern_scores", [])
            if isinstance(row, dict)
        )
    return context


def _decision_record(
    *,
    module: str,
    state: str,
    headline: str,
    reason: str,
    blocker: str,
    next_allowed_action: str,
    artifact_refs: list[str],
    strategy_family: str = "aggregate",
    evidence: list[str] | None = None,
) -> dict[str, Any]:
    record_id = _hash_id([SCHEMA_VERSION, module, state, headline, artifact_refs], "qsase-dashboard")
    return {
        "schema_version": SCHEMA_VERSION,
        "decision_record_id": record_id,
        "module": module,
        "state": state,
        "headline": headline[:120],
        "strategy_family": strategy_family,
        "evidence": (evidence or [])[:4],
        "reason": reason[:220],
        "blocker": blocker[:120],
        "next_allowed_action": next_allowed_action[:180],
        "authority_boundary": "read_only_dashboard_mirror_no_commands_no_orders_no_proof_no_live_capital",
        "artifact_refs": artifact_refs,
        "applied_change": False,
        "paper_order_created": False,
        "proof_credit_allowed": False,
        "live_capital_enabled": False,
        "authority": _dashboard_authority(),
    }


def _section_base(artifact_type: str, generated_at: str) -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": artifact_type,
        "generated_at": generated_at,
        "public_safe": True,
        "command_disabled": True,
        "read_only": True,
        "paper_only": True,
        "authority": _dashboard_authority(),
    }


def _round_money(value: Any) -> float | None:
    if value is None:
        return None
    return round(_float(value), 2)


def _latest_alpaca_snapshot(context: dict[str, Any]) -> dict[str, Any]:
    mirror = context.get("alpaca_mirror", {})
    snapshot = mirror.get("snapshot") if isinstance(mirror.get("snapshot"), dict) else {}
    epoch = context.get("current_paper_epoch", {})
    clean_epoch = epoch.get("paper_epoch_kind") == "clean_operator_epoch"
    if snapshot and record_matches_epoch(
        snapshot,
        epoch,
        permit_legacy_testing_records=not clean_epoch,
    ):
        return snapshot
    for item in reversed(context.get("alpaca_history", [])):
        history_snapshot = item.get("snapshot")
        if isinstance(history_snapshot, dict):
            return history_snapshot
    return {}


def _portfolio_series_from_history(context: dict[str, Any], current_snapshot: dict[str, Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    seen: set[str] = set()
    for item in context.get("alpaca_history", []):
        snapshot = item.get("snapshot", {})
        if not isinstance(snapshot, dict):
            continue
        observed_at = snapshot.get("observed_at") or item.get("generated_at")
        value = canonical_money(
            snapshot,
            "current_balance",
            "equity",
            "current_balance_gbp",
            "equity_gbp",
            "source_equity",
        )
        if observed_at is None or value is None:
            continue
        seen.add(str(observed_at))
        rows.append(
            {
                "timestamp": observed_at,
                "observed_at": observed_at,
                "portfolio_value": _round_money(value),
                "equity": _round_money(canonical_money(snapshot, "equity", "equity_gbp") or value),
                "equity_gbp": _round_money(canonical_money(snapshot, "equity", "equity_gbp") or value),
                "cash": _round_money(canonical_money(snapshot, "cash", "cash_gbp")),
                "cash_gbp": _round_money(canonical_money(snapshot, "cash", "cash_gbp")),
                "display_currency": snapshot.get("display_currency") or item.get("display_currency"),
                "drawdown_pct": snapshot.get("drawdown_pct"),
                "paper_epoch_id": snapshot.get("paper_epoch_id") or item.get("paper_epoch_id"),
                "read_only_source": _artifact_ref(ALPACA_PAPER_MIRROR_HISTORY_ARTIFACT),
            }
        )
    observed_at = current_snapshot.get("observed_at")
    current_value = canonical_money(
        current_snapshot,
        "current_balance",
        "equity",
        "current_balance_gbp",
        "equity_gbp",
    )
    if observed_at and current_value is not None and str(observed_at) not in seen:
        rows.append(
            {
                "timestamp": observed_at,
                "observed_at": observed_at,
                "portfolio_value": _round_money(current_value),
                "equity": _round_money(canonical_money(current_snapshot, "equity", "equity_gbp") or current_value),
                "equity_gbp": _round_money(canonical_money(current_snapshot, "equity", "equity_gbp") or current_value),
                "cash": _round_money(canonical_money(current_snapshot, "cash", "cash_gbp")),
                "cash_gbp": _round_money(canonical_money(current_snapshot, "cash", "cash_gbp")),
                "display_currency": current_snapshot.get("display_currency"),
                "drawdown_pct": current_snapshot.get("drawdown_pct"),
                "paper_epoch_id": current_snapshot.get("paper_epoch_id"),
                "read_only_source": _artifact_ref(ALPACA_PAPER_MIRROR_ARTIFACT),
            }
        )
    return rows[-160:]


def _portfolio_consistency(
    *,
    current_snapshot: dict[str, Any],
    series: list[dict[str, Any]],
    positions: list[dict[str, Any]],
) -> dict[str, Any]:
    current_value = _round_money(
        canonical_money(
            current_snapshot,
            "current_balance",
            "equity",
            "current_balance_gbp",
            "equity_gbp",
        )
    )
    latest_chart_value = _round_money(series[-1].get("portfolio_value")) if series else None
    realized = _round_money(
        canonical_money(current_snapshot, "realized_pnl", "realized_pnl_gbp")
    ) or 0.0
    unrealized = _round_money(
        canonical_money(current_snapshot, "unrealized_pnl", "unrealized_pnl_gbp")
    ) or 0.0
    total = _round_money(realized + unrealized)
    reported_total = _round_money(
        canonical_money(current_snapshot, "total_pnl", "total_pnl_gbp")
    )
    if reported_total is None:
        reported_total = total
    reported_positions = int(current_snapshot.get("open_position_count") or len(positions) or 0)
    row_count = len(positions)
    value_delta = None
    if current_value is not None and latest_chart_value is not None:
        value_delta = _round_money(current_value - latest_chart_value)
    pnl_delta = _round_money((reported_total or 0) - (total or 0))
    position_count_delta = reported_positions - row_count
    errors = []
    if value_delta is None:
        errors.append("portfolio_value_or_chart_point_missing")
    elif abs(value_delta) > 0.01:
        errors.append("portfolio_value_chart_mismatch")
    if abs(pnl_delta or 0) > 0.01:
        errors.append("portfolio_pnl_reconciliation_mismatch")
    if position_count_delta != 0:
        errors.append("open_position_count_mismatch")
    return {
        "status": "ok" if not errors else "mismatch",
        "errors": errors,
        "current_value": current_value,
        "latest_chart_value": latest_chart_value,
        "value_delta": value_delta,
        "realized_pnl": realized,
        "unrealized_pnl": unrealized,
        "calculated_total_pnl": total,
        "reported_total_pnl": reported_total,
        "pnl_delta": pnl_delta,
        "reported_open_position_count": reported_positions,
        "holding_row_count": row_count,
        "position_count_delta": position_count_delta,
    }


def build_dashboard_portfolio_contract(context: dict[str, Any], generated_at: str) -> dict[str, Any]:
    current_snapshot = _latest_alpaca_snapshot(context)
    positions = [
        {
            "row_type": "open_paper_position_mirror",
            "position_id": row.get("position_id"),
            "instrument": row.get("instrument"),
            "symbol": row.get("instrument"),
            "status": row.get("status"),
            "direction": row.get("direction"),
            "quantity": row.get("quantity"),
            "entry_price": row.get("entry_price"),
            "current_price": row.get("current_price"),
            "current_value_gbp": _round_money(row.get("risk_size_gbp")),
            "market_value_gbp": _round_money(row.get("risk_size_gbp")),
            "unrealized_pnl_gbp": _round_money(row.get("unrealized_pnl_gbp")),
            "current_value": _round_money(canonical_money(row, "risk_size", "risk_size_gbp")),
            "market_value": _round_money(canonical_money(row, "risk_size", "risk_size_gbp")),
            "unrealized_pnl": _round_money(canonical_money(row, "unrealized_pnl", "unrealized_pnl_gbp")),
            "paper_epoch_id": row.get("paper_epoch_id"),
            "source_intent_id": row.get("source_intent_id"),
            "invalidation": row.get("invalidation"),
            "next_lifecycle_action": "monitor paper position mirror",
            "boundary": "read_only_paper_position_mirror_no_close_or_modify",
            "artifact_refs": [_artifact_ref(PAPER_POSITIONS_ARTIFACT)],
            "paper_order_created": False,
            "broker_write_allowed": False,
        }
        for row in context.get("paper_positions", [])
    ]
    series = _portfolio_series_from_history(context, current_snapshot)
    consistency = _portfolio_consistency(
        current_snapshot=current_snapshot,
        series=series,
        positions=positions,
    )
    observed_at = current_snapshot.get("observed_at")
    observed_dt = _parse_timestamp(observed_at)
    generated_dt = _parse_timestamp(generated_at) or _now()
    broker_age = int((_now() - observed_dt).total_seconds()) if observed_dt else None
    public_age = int((_now() - generated_dt).total_seconds())
    broker_threshold = 2700
    public_threshold = 1800
    market_clock = context.get("alpaca_mirror", {}).get("market_clock", {})
    if not isinstance(market_clock, dict):
        market_clock = {}
    market_is_closed = (
        market_clock.get("is_open") is False
        or str(market_clock.get("status") or "").lower() in {"closed", "market_closed"}
    )
    if broker_age is not None and broker_age <= broker_threshold:
        broker_freshness_status = "fresh"
        broker_freshness_reason = "Broker mirror is within the active freshness threshold."
    elif market_is_closed:
        broker_freshness_status = "market_closed"
        broker_freshness_reason = "Market closed; displaying the latest completed broker snapshot."
    else:
        broker_freshness_status = "stale"
        broker_freshness_reason = "Broker mirror exceeded the active-market freshness threshold."
    current_value = _round_money(
        canonical_money(
            current_snapshot,
            "current_balance",
            "equity",
            "current_balance_gbp",
            "equity_gbp",
        )
    )
    starting_value = _round_money(
        canonical_money(current_snapshot, "starting_balance", "starting_balance_gbp")
    ) or current_value
    epoch = context.get("current_paper_epoch", {})
    return {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "dashboard_portfolio_canonical_contract",
        "generated_at": generated_at,
        "status": "dashboard_portfolio_consistent" if consistency["status"] == "ok" else "dashboard_portfolio_mismatch",
        "public_safe": True,
        "read_only": True,
        "paper_only": True,
        "command_disabled": True,
        "source_of_truth": "data/runtime/alpaca_paper_mirror.json:snapshot",
        "history_source": "data/runtime/alpaca_paper_mirror.jsonl",
        "position_source": "data/runtime/paper_positions.jsonl",
        "account_scope": current_snapshot.get("account_scope"),
        "broker": current_snapshot.get("broker"),
        "connection_status": current_snapshot.get("connection_status"),
        "market_clock": market_clock,
        "paper_epoch_id": epoch.get("paper_epoch_id") or current_snapshot.get("paper_epoch_id"),
        "paper_epoch_kind": epoch.get("paper_epoch_kind") or current_snapshot.get("paper_epoch_kind") or "legacy_test",
        "paper_epoch_started_at": epoch.get("paper_epoch_started_at"),
        "paper_epoch_isolation": context.get("paper_epoch_isolation", {}),
        "observed_at": observed_at,
        "current_value": current_value,
        "current_balance": current_value,
        "equity": _round_money(canonical_money(current_snapshot, "equity", "equity_gbp") or current_value),
        "cash": _round_money(canonical_money(current_snapshot, "cash", "cash_gbp")),
        "starting_balance": starting_value,
        "realized_pnl": _round_money(canonical_money(current_snapshot, "realized_pnl", "realized_pnl_gbp")),
        "unrealized_pnl": _round_money(canonical_money(current_snapshot, "unrealized_pnl", "unrealized_pnl_gbp")),
        "total_pnl": consistency["reported_total_pnl"],
        "current_value_gbp": current_value,
        "current_balance_gbp": current_value,
        "equity_gbp": _round_money(canonical_money(current_snapshot, "equity", "equity_gbp") or current_value),
        "cash_gbp": _round_money(canonical_money(current_snapshot, "cash", "cash_gbp")),
        "starting_balance_gbp": starting_value,
        "realized_pnl_gbp": _round_money(canonical_money(current_snapshot, "realized_pnl", "realized_pnl_gbp")),
        "unrealized_pnl_gbp": _round_money(canonical_money(current_snapshot, "unrealized_pnl", "unrealized_pnl_gbp")),
        "total_pnl_gbp": consistency["reported_total_pnl"],
        "delta_pct": (
            round(((current_value - starting_value) / starting_value) * 100, 4)
            if current_value is not None and starting_value
            else 0
        ),
        "drawdown_pct": current_snapshot.get("drawdown_pct"),
        "open_position_count": len(positions),
        "closed_trade_count": int(current_snapshot.get("closed_trade_count") or 0),
        "order_count": int(context.get("alpaca_mirror", {}).get("order_count") or 0),
        "postmortem_due_count": int(current_snapshot.get("postmortem_due_count") or 0),
        "display_currency": current_snapshot.get("display_currency") or "USD",
        "account_currency": current_snapshot.get("account_currency") or "USD",
        "portfolio_value_source": "alpaca_paper_account_mirror",
        "positions": positions,
        "equity_curve": series,
        "equity_curve_count": len(series),
        "latest_curve_point": series[-1] if series else None,
        "portfolio_consistency": consistency,
        "broker_mirror_freshness": {
            "status": broker_freshness_status,
            "age_seconds": broker_age,
            "threshold_seconds": broker_threshold,
            "observed_at": observed_at,
            "reason": broker_freshness_reason,
            "market_is_open": market_clock.get("is_open"),
            "next_open": market_clock.get("next_open"),
        },
        "public_snapshot_freshness": {
            "status": "fresh" if public_age <= public_threshold else "stale",
            "age_seconds": public_age,
            "threshold_seconds": public_threshold,
            "generated_at": generated_at,
        },
        "live_capital_enabled": False,
        "write_authority": False,
        "paper_order_allowed": False,
        "broker_write_allowed": False,
        "boundary": (
            "Canonical public dashboard portfolio. It mirrors Alpaca paper account state "
            "and cannot create, cancel, replace, close, or approve orders."
        ),
        "artifact_refs": [
            _artifact_ref(ALPACA_PAPER_MIRROR_ARTIFACT),
            _artifact_ref(ALPACA_PAPER_MIRROR_HISTORY_ARTIFACT),
            _artifact_ref(PAPER_POSITIONS_ARTIFACT),
        ],
    }


def build_portfolio_value_series(context: dict[str, Any], generated_at: str) -> dict[str, Any]:
    artifact = _section_base("qsase_dashboard_portfolio_value_series", generated_at)
    portfolio = context.get("dashboard_portfolio", {})
    rows = _safe_list(portfolio.get("equity_curve"))
    artifact.update(
        {
            "status": "portfolio_value_series_available" if rows else "portfolio_value_series_unavailable",
            "line_graph_available": bool(rows),
            "unavailable_reason": None if rows else "alpaca_paper_mirror_history_missing_or_empty",
            "series_count": len(rows),
            "series": rows,
            "latest_value": rows[-1]["portfolio_value"] if rows else None,
            "current_value": portfolio.get("current_value"),
            "paper_epoch_id": portfolio.get("paper_epoch_id"),
            "paper_epoch_kind": portfolio.get("paper_epoch_kind"),
            "current_value_gbp": portfolio.get("current_value_gbp"),
            "cash": portfolio.get("cash"),
            "cash_gbp": portfolio.get("cash_gbp"),
            "portfolio_consistency": portfolio.get("portfolio_consistency", {}),
            "broker_mirror_freshness": portfolio.get("broker_mirror_freshness", {}),
            "public_snapshot_freshness": portfolio.get("public_snapshot_freshness", {}),
            "artifact_refs": [_artifact_ref(ALPACA_PAPER_MIRROR_ARTIFACT), _artifact_ref(ALPACA_PAPER_MIRROR_HISTORY_ARTIFACT)],
            "write_authority": False,
        }
    )
    return artifact


def build_current_portfolio(context: dict[str, Any], generated_at: str) -> dict[str, Any]:
    artifact = _section_base("qsase_dashboard_current_portfolio", generated_at)
    portfolio = context.get("dashboard_portfolio", {})
    rows = _safe_list(portfolio.get("positions"))
    consistency = portfolio.get("portfolio_consistency", {})
    reported_count = int(consistency.get("reported_open_position_count") or portfolio.get("open_position_count") or 0)
    row_count = len(rows)
    reconciliation_status = "ok" if reported_count == row_count else "mismatch"
    artifact.update(
        {
            "status": (
                "current_portfolio_reconciliation_mismatch"
                if reconciliation_status == "mismatch"
                else ("current_portfolio_present" if rows else "current_portfolio_explicitly_empty")
            ),
            "position_count": row_count,
            "paper_epoch_id": portfolio.get("paper_epoch_id"),
            "paper_epoch_kind": portfolio.get("paper_epoch_kind"),
            "reported_open_position_count": reported_count,
            "holding_row_count": row_count,
            "reconciliation_status": reconciliation_status,
            "reconciliation_note": (
                (
                    "No broker-filled positions are currently held. This only describes the current holdings view; "
                    "trade candidates, staged paper orders, pending orders, and closed trades are shown in the trade lifecycle sections."
                )
                if reconciliation_status == "ok" and not rows
                else (
                    "The broker mirror and exported position rows agree."
                    if reconciliation_status == "ok"
                    else "The broker mirror and exported position rows disagree; the dashboard must show this as a data-truth mismatch."
                )
            ),
            "rows": rows,
            "explicitly_empty": not rows,
            "portfolio_consistency": consistency,
            "broker_mirror_freshness": portfolio.get("broker_mirror_freshness", {}),
            "artifact_refs": [_artifact_ref(PAPER_POSITIONS_ARTIFACT), _artifact_ref(ALPACA_PAPER_MIRROR_ARTIFACT)],
        }
    )
    return artifact


def build_trading_history(context: dict[str, Any], generated_at: str) -> dict[str, Any]:
    artifact = _section_base("qsase_dashboard_trading_history", generated_at)
    closed_rows = [
        {
            "event_type": "sell_or_close",
            "event_label": "Sell / close",
            "row_type": "closed_paper_trade_mirror",
            "trade_id": row.get("trade_id"),
            "paper_epoch_id": row.get("paper_epoch_id"),
            "instrument": row.get("instrument"),
            "direction": row.get("direction"),
            "opened_at": row.get("opened_at"),
            "closed_at": row.get("closed_at"),
            "realized_pnl": canonical_money(row, "realized_pnl", "realized_pnl_gbp"),
            "postmortem_status": row.get("postmortem_status"),
            "source_intent_id": row.get("source_intent_id"),
            "boundary": "mirrored_closed_paper_trade_not_new_proof_credit",
            "artifact_refs": [_artifact_ref(PAPER_CLOSED_TRADES_ARTIFACT)],
        }
        for row in context.get("paper_closed_trades", [])[-50:]
    ]
    order_rows = [
        {
            "event_type": "buy_or_order",
            "event_label": "Buy / order",
            "row_type": "paper_order_mirror_not_trade_intent",
            "order_id": row.get("order_id"),
            "paper_epoch_id": row.get("paper_epoch_id"),
            "instrument": row.get("instrument"),
            "direction": row.get("direction"),
            "status": row.get("status"),
            "submitted_at": row.get("submitted_at"),
            "filled_at": row.get("filled_at"),
            "filled_quantity": row.get("filled_quantity"),
            "boundary": "mirrored_order_only_no_create_cancel_replace_or_close",
            "artifact_refs": [_artifact_ref(PAPER_ORDERS_ARTIFACT)],
        }
        for row in context.get("paper_orders", [])[-30:]
    ]
    rows = closed_rows + order_rows
    rows.sort(
        key=lambda row: _parse_timestamp(row.get("closed_at") or row.get("filled_at") or row.get("submitted_at") or row.get("opened_at"))
        or datetime.min.replace(tzinfo=timezone.utc),
        reverse=True,
    )
    artifact.update(
        {
            "status": "trading_history_present" if closed_rows or order_rows else "trading_history_explicitly_empty",
            "paper_epoch_id": context.get("dashboard_portfolio", {}).get("paper_epoch_id"),
            "paper_epoch_kind": context.get("dashboard_portfolio", {}).get("paper_epoch_kind"),
            "closed_trade_row_count": len(closed_rows),
            "paper_order_mirror_row_count": len(order_rows),
            "timeline_order": "newest_first",
            "rows": rows,
            "explicitly_empty": not (closed_rows or order_rows),
            "artifact_refs": [_artifact_ref(PAPER_CLOSED_TRADES_ARTIFACT), _artifact_ref(PAPER_ORDERS_ARTIFACT)],
        }
    )
    return artifact


def build_source_network(context: dict[str, Any], generated_at: str) -> dict[str, Any]:
    artifact = _section_base("qsase_dashboard_source_network", generated_at)
    source_universe = context.get("universal_matrix", {}).get("source_universe", {})
    trading_universe = context.get("universal_matrix", {}).get("trading_universe", {})
    family_payload = source_universe.get("source_families", {})
    category_rows = []
    if isinstance(family_payload, dict):
        for family, row in sorted(family_payload.items()):
            category_rows.append(
                {
                    "family": family,
                    "source_count": row.get("source_count"),
                    "fresh_count": row.get("fresh_count"),
                    "degraded_count": row.get("degraded_count"),
                    "credential_gated_count": row.get("credential_gated_count"),
                    "quorum_contributing_count": row.get("quorum_contributing_count"),
                    "state": "connected" if int(row.get("source_count") or 0) else "empty",
                    "description": _source_family_description(family),
                    "artifact_refs": [_artifact_ref(UNIVERSAL_MATRIX_ARTIFACT, f"source_universe.source_families.{family}")],
                }
            )
    source_rows = [
        {
            "source_key": row.get("source_key"),
            "source_name": row.get("source_name"),
            "family": row.get("source_family"),
            "state": row.get("state"),
            "freshness_status": row.get("freshness_status"),
            "last_update": row.get("last_update") or row.get("observed_at") or row.get("generated_at") or row.get("updated_at"),
            "trust_posture": row.get("trust_posture"),
            "quorum_contribution": row.get("source_quorum_contribution", {}).get("can_contribute"),
            "credential_gated": row.get("credential_gated"),
            "trade_candidate_creation_allowed": False,
            "artifact_refs": [_artifact_ref(UNIVERSAL_MATRIX_ARTIFACT, f"source_universe.sources.{index}")],
        }
        for index, row in enumerate(_safe_list(source_universe.get("sources")))
    ]
    unusual_whales_status = context.get("unusual_whales_research_status", {})
    unusual_whales_features = context.get("unusual_whales_feature_manifest", {})
    if unusual_whales_status:
        feature_ready = unusual_whales_features.get("backtest_feature_ready") is True
        access_state = str(
            unusual_whales_status.get("status") or "ready_not_initialized"
        )
        unusual_row = next(
            (row for row in source_rows if row.get("source_key") == "unusual_whales"),
            None,
        )
        if unusual_row is not None:
            was_fresh = unusual_row.get("freshness_status") in {"fresh", "recent"}
            unusual_row.update(
                {
                    "state": (
                        "historical_archive"
                        if access_state == "expired_archive_only"
                        else "historical_trial"
                    ),
                    "freshness_status": "captured" if feature_ready else "not_captured",
                    "credential_gated": unusual_whales_status.get("credential_state")
                    != "configured",
                    "historical_research_only": True,
                    "historical_backtest_allowed": feature_ready,
                    "fresh_ingestion_allowed": unusual_whales_status.get(
                        "fresh_ingestion_allowed"
                    )
                    is True,
                    "access_state": access_state,
                    "access_expires_on": unusual_whales_status.get(
                        "access_expires_on", "2026-07-21"
                    ),
                    "post_expiry_mode": "historical_archive_only",
                    "backtest_eligible_record_count": int(
                        unusual_whales_features.get("backtest_eligible_record_count") or 0
                    ),
                    "coverage_start": unusual_whales_features.get("coverage_start"),
                    "coverage_end": unusual_whales_features.get("coverage_end"),
                    "source_quorum_allowed": False,
                    "artifact_refs": [
                        *unusual_row["artifact_refs"],
                        _artifact_ref(UNUSUAL_WHALES_RESEARCH_STATUS_ARTIFACT),
                        _artifact_ref(UNUSUAL_WHALES_FEATURE_MANIFEST_ARTIFACT),
                    ],
                }
            )
            market_category = next(
                (row for row in category_rows if row.get("family") == "market"),
                None,
            )
            if market_category is not None:
                market_category["historical_research_count"] = int(
                    market_category.get("historical_research_count") or 0
                ) + 1
            if market_category is not None and was_fresh:
                market_category["fresh_count"] = max(
                    int(market_category.get("fresh_count") or 0) - 1,
                    0,
                )
                market_category["credential_gated_count"] = int(
                    market_category.get("credential_gated_count") or 0
                ) + int(unusual_row["credential_gated"])
    trading_rows = [
        {
            "instrument_id": row.get("instrument_id"),
            "symbol": row.get("symbol"),
            "display_name": row.get("display_name"),
            "market_family": row.get("market_family"),
            "paperability_state": row.get("paperability_state"),
            "paper_route_available": row.get("paper_route_available"),
            "qualified_setup_state": row.get("qualified_setup_state"),
            "live_route_enabled": False,
            "paper_order_allowed": False,
            "artifact_refs": [_artifact_ref(UNIVERSAL_MATRIX_ARTIFACT, f"trading_universe.instruments.{index}")],
        }
        for index, row in enumerate(_safe_list(trading_universe.get("instruments")))
    ]
    canonical_source_row_count = len(source_rows)
    canonical_trading_universe_row_count = len(trading_rows)
    canonical_category_row_count = len(category_rows)
    power_extension = context.get("power_market_dashboard", {}).get("research_extension")
    power_extension = power_extension if isinstance(power_extension, dict) else {}
    extension_sources = _safe_list(power_extension.get("source_feeds"))
    extension_instruments = _safe_list(power_extension.get("instruments"))
    if (
        context.get("power_market_checks", {}).get("safe_to_consume") is True
        and power_extension.get("status") == "research_running"
        and extension_sources
        and extension_instruments
    ):
        category_rows.append(
            {
                "family": "power_grid_constraints",
                "source_count": len(extension_sources),
                "fresh_count": sum(
                    row.get("freshness_status") == "fresh"
                    for row in extension_sources
                    if isinstance(row, dict)
                ),
                "degraded_count": sum(
                    row.get("freshness_status") != "fresh"
                    for row in extension_sources
                    if isinstance(row, dict)
                ),
                "credential_gated_count": 0,
                "quorum_contributing_count": len(extension_sources),
                "state": "research_running",
                "description": _source_family_description("power_grid_constraints"),
                "research_extension": True,
                "extension_label": power_extension.get("label"),
                "provider_independence_note": power_extension.get(
                    "provider_independence_note"
                ),
                "artifact_refs": [_artifact_ref(POWER_MARKET_DASHBOARD_ARTIFACT)],
            }
        )
        for row in extension_sources:
            if not isinstance(row, dict):
                continue
            source_rows.append(
                {
                    "source_key": row.get("source_key"),
                    "source_name": row.get("source_name"),
                    "family": "power_grid_constraints",
                    "state": row.get("state"),
                    "freshness_status": row.get("freshness_status"),
                    "last_update": context.get("power_market_dashboard", {}).get(
                        "generated_at"
                    ),
                    "trust_posture": "authoritative_grid_operator",
                    "quorum_contribution": row.get("quorum_contribution") is True,
                    "credential_gated": False,
                    "trade_candidate_creation_allowed": False,
                    "description": row.get("description"),
                    "provider_url": row.get("provider_url"),
                    "research_extension": True,
                    "artifact_refs": [_artifact_ref(POWER_MARKET_DASHBOARD_ARTIFACT)],
                }
            )
        for row in extension_instruments:
            if not isinstance(row, dict):
                continue
            symbol = row.get("symbol")
            trading_rows.append(
                {
                    "instrument_id": f"power-research-instrument:{str(symbol).lower()}",
                    "symbol": symbol,
                    "display_name": row.get("display_name") or symbol,
                    "market_family": "power_markets",
                    "paperability_state": row.get("paperability_state"),
                    "paper_route_available": row.get("paper_route_available") is True,
                    "qualified_setup_state": "research_running",
                    "live_route_enabled": False,
                    "paper_order_allowed": False,
                    "role": row.get("role"),
                    "research_extension": True,
                    "artifact_refs": [_artifact_ref(POWER_MARKET_DASHBOARD_ARTIFACT)],
                }
            )
    artifact.update(
        {
            "status": "source_network_visible" if category_rows and source_rows else "source_network_degraded",
            "category_row_count": len(category_rows),
            "source_row_count": len(source_rows),
            "trading_universe_row_count": len(trading_rows),
            "canonical_source_row_count": canonical_source_row_count,
            "canonical_category_row_count": canonical_category_row_count,
            "canonical_trading_universe_row_count": canonical_trading_universe_row_count,
            "research_extension_source_row_count": len(source_rows)
            - canonical_source_row_count,
            "research_extension_trading_row_count": len(trading_rows)
            - canonical_trading_universe_row_count,
            "research_extension_status": (
                power_extension.get("status") if extension_sources else "not_active"
            ),
            "research_extension_label": power_extension.get("label"),
            "research_extension_note": (
                "The power sleeve is a live research extension. Its feeds and proxies were not "
                "part of the frozen 41-source by 19-instrument historical baseline."
                if extension_sources
                else None
            ),
            "category_rows": category_rows,
            "source_rows": source_rows,
            "trading_universe_rows": trading_rows,
            "artifact_refs": [_artifact_ref(UNIVERSAL_MATRIX_ARTIFACT)],
        }
    )
    return artifact


def _strategy_family_from_router(row: dict[str, Any]) -> str:
    family = row.get("strategy_family")
    if isinstance(family, dict):
        return _first_text(family.get("primary_family"), family.get("mapped_existing_family"), default="unmapped_strategy_family")
    identity = row.get("candidate_identity") if isinstance(row.get("candidate_identity"), dict) else {}
    return _first_text(
        family,
        row.get("strategy_hypothesis_lineage", {}).get("strategy_family"),
        identity.get("strategy_family_id"),
        default="unmapped_strategy_family",
    )


def _strategy_evidence_by_family(context: dict[str, Any]) -> dict[str, dict[str, Any]]:
    records: dict[str, dict[str, Any]] = {}
    for row in context.get("strategy_evidence_map_records", []):
        if not isinstance(row, dict):
            continue
        family_id = _first_text(row.get("strategy_family_id"), default="")
        if family_id and family_id not in records:
            records[family_id] = row
    return records


def _router_v2_by_family(context: dict[str, Any]) -> dict[str, list[dict[str, Any]]]:
    records: dict[str, list[dict[str, Any]]] = {}
    for row in context.get("router_v2_decisions", []):
        if not isinstance(row, dict):
            continue
        identity = row.get("candidate_identity") if isinstance(row.get("candidate_identity"), dict) else {}
        family_id = _first_text(identity.get("strategy_family_id"), default="")
        if family_id:
            records.setdefault(family_id, []).append(row)
    return records


def _instrument_explanations(
    *,
    playbook_rows: list[dict[str, Any]],
    watched_markets: list[dict[str, Any]],
    contribution_rows: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    watched_index = {
        str(row.get("symbol") or row.get("display_name") or "").lower(): row
        for row in watched_markets
        if isinstance(row, dict)
    }
    contribution_index = {
        str(row.get("symbol") or "").lower(): row
        for row in contribution_rows
        if isinstance(row, dict)
    }
    rows = []
    for item in playbook_rows:
        symbol = _first_text(item.get("symbol"), default="")
        if not symbol:
            continue
        key = symbol.lower()
        watched = watched_index.get(key, {})
        contribution = contribution_index.get(key, {})
        rows.append(
            {
                "symbol": symbol,
                "role": item.get("role"),
                "explanation": item.get("explanation"),
                "paperability_state": watched.get("paperability_state") or contribution.get("paperability_state"),
                "paper_route_available": bool(watched.get("paper_order_allowed") or contribution.get("paper_route_available")),
                "price_data_state": contribution.get("price_data_state"),
                "pattern_support_count": _int(contribution.get("pattern_support_count"), 0),
                "contribution_score": contribution.get("contribution_score"),
            }
        )
    return rows


def _human_strategy_status(row: dict[str, Any], evidence: dict[str, Any]) -> str:
    dashboard_status = str(evidence.get("dashboard_card_status") or "").lower()
    state = str(row.get("current_state") or "").lower()
    if "evidence-backed" in dashboard_status:
        return "Evidence building: Qadam has research support, but practical trading confirmation is still missing."
    if "under-evidenced" in dashboard_status:
        return "Research watch: Qadam understands the playbook, but the historical evidence is still too thin."
    if "currently_in_play" in state:
        return "In play, held: Qadam is studying this strategy now, but the final trading gate is not open."
    return "Available playbook: Qadam can use this lens when future source-price evidence supports it."


def _strategy_blocker_plain_english(evidence: dict[str, Any], router_rows: list[dict[str, Any]]) -> str:
    akber = evidence.get("akber_sensitivity") if isinstance(evidence.get("akber_sensitivity"), dict) else {}
    missing = akber.get("dominant_missing_inputs") if isinstance(akber.get("dominant_missing_inputs"), dict) else {}
    if missing:
        readable = ", ".join(sorted(key.replace("missing_", "").replace("_", " ") for key in missing.keys())[:3])
        return f"Not tradeable yet because Akber still needs practical confirmation: {readable}."
    if router_rows:
        blockers = router_rows[0].get("soft_blockers") if isinstance(router_rows[0].get("soft_blockers"), list) else []
        if blockers:
            return "Not tradeable yet because " + ", ".join(str(item).replace("_", " ") for item in blockers[:3]) + "."
    if evidence.get("evidence_state") == "under_evidenced_research_map":
        return "Not tradeable yet because the historical source-price evidence is not strong enough."
    return "Not tradeable yet until source agreement, backtest evidence, Akber confirmation, risk checks, and PaperOps all align."


def _strategy_next_action_plain_english(evidence: dict[str, Any], router_rows: list[dict[str, Any]]) -> str:
    if router_rows:
        return "Refresh practical market context, complete the backtest windows, then rerun Akber and Router without creating orders."
    if evidence.get("evidence_state") == "under_evidenced_research_map":
        return "Collect more complete historical windows and compare this strategy against its watched instruments."
    return "Keep gathering source-price evidence and only advance if the pattern survives backtesting, Akber, and Router review."


def _strategy_live_evidence(evidence: dict[str, Any], router_rows: list[dict[str, Any]]) -> dict[str, Any]:
    confidence = evidence.get("confidence_class") if isinstance(evidence.get("confidence_class"), dict) else {}
    expectancy = evidence.get("expectancy_profile") if isinstance(evidence.get("expectancy_profile"), dict) else {}
    sources = evidence.get("source_contribution") if isinstance(evidence.get("source_contribution"), dict) else {}
    instruments = evidence.get("instrument_contribution") if isinstance(evidence.get("instrument_contribution"), dict) else {}
    akber = evidence.get("akber_sensitivity") if isinstance(evidence.get("akber_sensitivity"), dict) else {}
    quantum = evidence.get("quantum_nonlinear_usefulness") if isinstance(evidence.get("quantum_nonlinear_usefulness"), dict) else {}
    router = router_rows[0] if router_rows else {}
    router_akber = router.get("akber_state") if isinstance(router.get("akber_state"), dict) else {}
    return {
        "confidence_label": confidence.get("dashboard_label") or confidence.get("label") or "not measured",
        "confidence_score": confidence.get("confidence_score"),
        "supporting_pattern_count": _int(evidence.get("supporting_pattern_count"), 0),
        "expectancy_state": expectancy.get("expectancy_state"),
        "effective_expectancy": expectancy.get("effective_expectancy"),
        "strongest_sources": sources.get("strongest_sources", [])[:4] if isinstance(sources.get("strongest_sources"), list) else [],
        "strongest_instruments": instruments.get("strongest_instruments", [])[:5] if isinstance(instruments.get("strongest_instruments"), list) else [],
        "akber_state": akber.get("state") or router_akber.get("status"),
        "akber_missing_inputs": sorted((akber.get("dominant_missing_inputs") or {}).keys()) if isinstance(akber.get("dominant_missing_inputs"), dict) else [],
        "quantum_nonlinear_usefulness": quantum.get("usefulness") or "not measured",
        "router_final_state": router.get("final_state"),
        "router_reason": router.get("final_state_reason"),
        "paper_review_candidate": bool(router.get("clean_paper_review_candidate")),
    }


def _strategy_self_refinement_loop(family_id: str, evidence: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
    backtest = context.get("whole_universe_backfill_backtest_dashboard", {})
    missing_windows = _int(backtest.get("missing_forward_window_count"), 0)
    complete_windows = _int(backtest.get("complete_forward_window_count"), 0)
    return {
        "plain_english": (
            "Qadam does not assume this strategy is correct forever. It replays historical examples and asks: "
            "when this kind of signal appeared before, did the market usually move afterward?"
        ),
        "what_gets_tested": "Source events, price moves, timing lags, similar historical cases, nonlinear interactions, Akber outcomes, and Router holds.",
        "what_backtesting_teaches": (
            f"The current whole-universe baseline has {complete_windows} complete forward windows and {missing_windows} missing windows. "
            "As those windows fill, Qadam can see which signals tended to lead prices and which only explained moves after the fact."
        ),
        "what_can_change_over_time": "Qadam may propose better instruments, stronger confirmation thresholds, weaker strategy weights, or stricter blockers.",
        "what_cannot_change_without_review": (
            "Backtesting cannot grant trade authority, bypass Akber, bypass Router, bypass PaperOps, create broker writes, "
            "enable live capital, or create paper proof ledger credit."
        ),
        "current_strategy_family": family_id,
        "supporting_pattern_count": _int(evidence.get("supporting_pattern_count"), 0),
    }


def _strategy_playbook_payload(
    *,
    family_id: str,
    family: dict[str, Any],
    row: dict[str, Any],
    strategy_markets: list[dict[str, Any]],
    evidence_by_family: dict[str, dict[str, Any]],
    router_by_family: dict[str, list[dict[str, Any]]],
    context: dict[str, Any],
) -> dict[str, Any]:
    playbook = STRATEGY_PLAYBOOK_DESCRIPTIONS.get(family_id, {})
    evidence = evidence_by_family.get(family_id, {})
    router_rows = router_by_family.get(family_id, [])
    instrument_contribution = evidence.get("instrument_contribution") if isinstance(evidence.get("instrument_contribution"), dict) else {}
    contribution_rows = instrument_contribution.get("rows") if isinstance(instrument_contribution.get("rows"), list) else []
    core = _instrument_explanations(
        playbook_rows=_safe_list(playbook.get("core_instruments")),
        watched_markets=strategy_markets,
        contribution_rows=contribution_rows,
    )
    secondary = _instrument_explanations(
        playbook_rows=_safe_list(playbook.get("secondary_instruments")),
        watched_markets=strategy_markets,
        contribution_rows=contribution_rows,
    )
    current_status = _human_strategy_status(row, evidence)
    return {
        "plain_english_summary": _first_text(playbook.get("plain_english_summary"), family.get("label"), default="Qadam uses this strategy as a research lens."),
        "how_strategy_works": _first_text(playbook.get("how_strategy_works"), default="Qadam compares real-world evidence with market movement before deciding whether a setup deserves more review."),
        "why_this_can_create_an_edge": _first_text(playbook.get("why_this_can_create_an_edge"), default="The possible edge is that scattered evidence may appear before the market fully reprices it."),
        "example_scenario": _first_text(playbook.get("example_scenario"), default="Qadam records an example scenario only as research evidence, not as a trade instruction."),
        "what_qadam_watches": _first_text(playbook.get("what_qadam_watches"), default=", ".join(_safe_list(family.get("source_keywords")))),
        "current_status_plain_english": current_status,
        "current_evidence_state": _first_text(evidence.get("what_this_means"), current_status, default="Evidence state not exported yet."),
        "current_blocker_plain_english": _strategy_blocker_plain_english(evidence, router_rows),
        "next_action_plain_english": _strategy_next_action_plain_english(evidence, router_rows),
        "core_instruments_explained": core,
        "secondary_instruments_explained": secondary,
        "live_evidence": _strategy_live_evidence(evidence, router_rows),
        "self_refinement_loop": _strategy_self_refinement_loop(family_id, evidence, context),
        "qualitative_copy_source": "dashboard_strategy_playbook_v2",
    }


def _strategy_v3_by_family(context: dict[str, Any]) -> dict[str, dict[str, Any]]:
    artifact = context.get("strategy_evidence_map_v3", {})
    rows = artifact.get("strategies") if isinstance(artifact.get("strategies"), list) else []
    return {
        str(row.get("strategy_family_id")): row
        for row in rows
        if isinstance(row, dict) and row.get("strategy_family_id")
    }


def _apply_strategy_validation_truth(row: dict[str, Any], validation: dict[str, Any]) -> dict[str, Any]:
    live_evidence = dict(row.get("live_evidence") or {})
    research_score = live_evidence.get("confidence_score")
    evidence_class = _first_text(validation.get("evidence_class"), default="validation_not_exported")
    validated_edge_count = _int(validation.get("edge_count"), len(_safe_list(validation.get("edge_ids"))))
    paper_attention_allowed = validation.get("paper_attention_allowed") is True
    if validated_edge_count > 0:
        validation_label = "Validated edge available"
        current_status = "Validated research playbook: at least one edge has passed the current evidence registry."
        current_evidence = f"{validated_edge_count} validated edge{'s' if validated_edge_count != 1 else ''} currently support this playbook."
    elif evidence_class == "degraded":
        validation_label = "Evidence degraded"
        current_status = "Defined playbook: current validation inputs are degraded and no edge has passed."
        current_evidence = "No provider-backed, out-of-sample edge has passed validation for this playbook yet."
    elif evidence_class == "under_evidenced":
        validation_label = "Not yet validated"
        current_status = "Defined playbook: Qadam can investigate it, but no edge has passed validation."
        current_evidence = "The playbook is mapped to sources and instruments, but its repeatable historical edge is not established."
    else:
        validation_label = "Validation not exported"
        current_status = "Defined playbook: current validation evidence has not been exported."
        current_evidence = "Qadam has not exported enough evidence to say whether this playbook has a repeatable edge."
    live_evidence.update(
        {
            "research_score": research_score,
            "research_score_label": "Research evidence score",
            "validation_state": evidence_class,
            "validation_state_label": validation_label,
            "validated_edge_count": validated_edge_count,
            "paper_attention_allowed": paper_attention_allowed,
            "promotion_class": validation.get("promotion_class"),
            "confidence_label": validation_label,
        }
    )
    row.update(
        {
            "defined_playbook": True,
            "validation_state": evidence_class,
            "validation_state_label": validation_label,
            "validated_edge_count": validated_edge_count,
            "paper_attention_allowed": paper_attention_allowed,
            "current_status_plain_english": current_status,
            "current_evidence_state": current_evidence,
            "live_evidence": live_evidence,
        }
    )
    if validated_edge_count == 0:
        row["current_blocker_plain_english"] = (
            "No validated edge exists yet. Qadam still needs provider-backed forward outcomes, "
            "cost-aware backtesting, and untouched holdout evidence."
        )
        row["next_action_plain_english"] = (
            "Complete historical score-label pairs, run the statistical backtest, and only then test whether this playbook deserves promotion."
        )
    return row


def _strategy_discovery_engine(context: dict[str, Any]) -> dict[str, Any]:
    score = context.get("pattern_score_v3", {})
    score_records = [row for row in context.get("pattern_score_v3_records", []) if isinstance(row, dict)]
    agnostic_records = [row for row in score_records if row.get("strategy_agnostic") is True and row.get("negative_control") is not True]
    ready_records = [row for row in agnostic_records if row.get("confidence_state") == "score_ready_for_tape"]
    blocked_records = [row for row in agnostic_records if row.get("confidence_state") != "score_ready_for_tape"]
    linear = context.get("linear_lab", {})
    nonlinear = context.get("nonlinear_lab", {})
    backtest = context.get("backtest_results_summary", {})
    quantum = context.get("quantum_usefulness_summary", {})
    nonlinear_methods = set(_safe_list(nonlinear.get("nonlinear_method_families")))
    tested_relationships = _int(linear.get("tested_relationship_count"), 0)
    tested_interactions = _int(nonlinear.get("tested_interaction_count"), 0)
    accepted_linear = _int(linear.get("accepted_linear_pattern_count"), 0)
    accepted_nonlinear = _int(nonlinear.get("accepted_nonlinear_pattern_count"), 0)
    measured_quantum = _int(quantum.get("measured_comparison_count"), 0)
    methods = [
        {
            "method_id": "strategy_agnostic_source_price_scan",
            "label": "Open source-price scanning",
            "role": "Open discovery",
            "state": "active_with_evidence_holds" if agnostic_records else "not_operational",
            "tone": "pending" if agnostic_records else "degraded",
            "state_label": "Active with evidence holds" if agnostic_records else "Not operational",
            "plain_english": "Searches every watched instrument for relationships with Qadam's information sources without forcing the result into one of the five defined strategies.",
            "metric": f"{len(agnostic_records)} instrument scans recorded",
            "evidence": f"{len(ready_records)} observation ready for deeper testing; {len(blocked_records)} still need critical evidence inputs.",
            "next_step": "Write point-in-time scores before future outcomes are known, then collect the matching forward labels.",
            "destination": "Historical evidence tape",
        },
        {
            "method_id": "historical_occurrence_lead_lag",
            "label": "Source-to-price occurrence and lead-lag",
            "role": "Primary discovery",
            "state": "testing_with_evidence_holds" if tested_relationships else "not_operational",
            "tone": "pending" if tested_relationships else "degraded",
            "state_label": "Testing with evidence holds" if tested_relationships else "Not operational",
            "plain_english": "Checks whether source events repeatedly appeared before, alongside, or after price moves instead of assuming that correlation means prediction.",
            "metric": f"{tested_relationships} relationships tested",
            "evidence": f"{accepted_linear} accepted; {_int(linear.get('inconclusive_linear_pattern_count'), 0)} inconclusive; {_int(linear.get('coverage_blocked_count'), 0)} coverage blocked.",
            "next_step": "Fill historical forward windows and rerun cost-aware, out-of-sample tests.",
            "destination": "Validated edge registry",
        },
        {
            "method_id": "historical_analog_matching",
            "label": "Historical analog matching",
            "role": "Context and prediction research",
            "state": "research_protocol_active" if "cluster_nearest_regime_matching" in nonlinear_methods else "not_operational",
            "tone": "pending" if "cluster_nearest_regime_matching" in nonlinear_methods else "degraded",
            "state_label": "Research protocol active" if "cluster_nearest_regime_matching" in nonlinear_methods else "Not operational",
            "plain_english": "Looks for previous multi-source market situations that resemble the present one, then asks what happened next. Similarity alone is never treated as a forecast.",
            "metric": f"{tested_interactions} nonlinear interactions examined",
            "evidence": f"{accepted_nonlinear} nonlinear relationships accepted. kNN and DTW outcome models are not yet measured as validated edge producers.",
            "next_step": "Build provider-backed analog memories with forward outcomes and untouched holdouts.",
            "destination": "Historical backtest",
        },
        {
            "method_id": "regime_state_testing",
            "label": "Regime and state testing",
            "role": "Conditional evidence",
            "state": "research_protocol_active" if "regime_conditioned_test" in nonlinear_methods else "not_operational",
            "tone": "pending" if "regime_conditioned_test" in nonlinear_methods else "degraded",
            "state_label": "Research protocol active" if "regime_conditioned_test" in nonlinear_methods else "Not operational",
            "plain_english": "Tests whether a relationship only works in particular conditions, such as high geopolitical stress, tight liquidity, rising volatility, or trending markets.",
            "metric": f"{_int(backtest.get('completed_method_count'), 0)} completed backtest methods",
            "evidence": f"{_int(backtest.get('results_by_regime', {}).get('result_count') if isinstance(backtest.get('results_by_regime'), dict) else 0, 0)} regime results exported; no state matrix is validated yet.",
            "next_step": "Measure enough occurrences per regime and compare each conditional result with its base rate.",
            "destination": "Strategy evidence map",
        },
        {
            "method_id": "nonlinear_quantum_usefulness",
            "label": "Nonlinear and quantum usefulness",
            "role": "Complexity challenge",
            "state": "measured" if measured_quantum else "protocols_not_measured",
            "tone": "online" if measured_quantum else "pending",
            "state_label": "Measured comparisons available" if measured_quantum else "Protocols prepared, not measured",
            "plain_english": "Challenges the normal statistical result with more complex interactions. Quantum work only matters if it improves an untouched result after latency, reliability, and complexity costs.",
            "metric": f"{measured_quantum} measured comparisons",
            "evidence": f"{_int(quantum.get('experiment_count'), 0)} experiments defined; current review mode is {str(context.get('nonlinear_lab', {}).get('quantum_state', {}).get('quantum_mode') or 'not exported').replace('_', ' ')}.",
            "next_step": "Complete classical-versus-quantum comparisons before claiming incremental value.",
            "destination": "Pattern Discovery",
        },
    ]
    validated_edges = _int(context.get("edge_registry_summary", {}).get("validated_edge_count"), 0)
    return {
        "status": "validated_edge_available" if validated_edges else "discovery_active_no_validated_edge",
        "headline": "Qadam can search beyond its defined playbooks, but no novel edge is validated yet.",
        "plain_english": (
            "The discovery engine scans the trading universe without requiring a strategy label first. "
            "A relationship only becomes a strategy candidate after forward outcomes, costs, holdout tests, and evidence controls pass."
        ),
        "strategy_agnostic_scan_count": len(agnostic_records) or _int(score.get("strategy_agnostic_record_count"), 0),
        "score_record_count": len(score_records) or _int(score.get("record_count"), 0),
        "evidence_ready_observation_count": len(ready_records),
        "blocked_observation_count": len(blocked_records),
        "validated_edge_count": validated_edges,
        "methods": methods,
        "artifact_refs": [
            _artifact_ref(PATTERN_SCORE_V3_ARTIFACT),
            _artifact_ref(LINEAR_LAB_ARTIFACT),
            _artifact_ref(NONLINEAR_LAB_ARTIFACT),
            _artifact_ref(BACKTEST_RESULTS_SUMMARY_ARTIFACT),
            _artifact_ref(QUANTUM_USEFULNESS_SUMMARY_ARTIFACT),
        ],
    }


def _emerging_strategy_candidates(context: dict[str, Any], discovery: dict[str, Any]) -> dict[str, Any]:
    proposals = [row for row in context.get("new_strategy_family_proposals", []) if isinstance(row, dict)]
    for hypothesis in context.get("strategy_hypotheses_v3", []):
        if not isinstance(hypothesis, dict) or hypothesis.get("hypothesis_type") != "new_strategy_family_candidate":
            continue
        proposals.append(hypothesis)
    rows = []
    seen: set[str] = set()
    for index, proposal in enumerate(proposals):
        candidate_id = _first_text(
            proposal.get("new_strategy_family_proposal_id"),
            proposal.get("strategy_hypothesis_id"),
            proposal.get("proposal_id"),
            default=f"emerging_strategy_{index}",
        )
        if candidate_id in seen:
            continue
        seen.add(candidate_id)
        state = _first_text(proposal.get("admission_state"), proposal.get("status"), default="research_only")
        rows.append(
            {
                "candidate_id": candidate_id,
                "label": _first_text(proposal.get("name"), proposal.get("proposed_family_name"), proposal.get("label"), default="Unnamed strategy proposal"),
                "state": state,
                "state_label": state.replace("_", " ").title(),
                "thesis": _first_text(proposal.get("thesis"), proposal.get("summary"), proposal.get("plain_english"), default="The proposal has not exported a plain-English thesis yet."),
                "research_score": proposal.get("research_score") or proposal.get("pattern_rank_score"),
                "instruments": _safe_list(proposal.get("instruments") or proposal.get("market_symbols")),
                "sources": _safe_list(proposal.get("source_keys")),
                "blocker": _first_text(proposal.get("blocker"), proposal.get("why_not_ready"), default="Human admission and complete validation evidence are required."),
                "next_action": _first_text(proposal.get("next_action"), default="Continue backtest and shadow review without creating orders."),
                "human_admission_required": True,
                "paper_order_allowed": False,
            }
        )
    if context.get("power_market_checks", {}).get("safe_to_consume") is True:
        for strategy in _safe_list(context.get("power_market_strategy", {}).get("strategies")):
            if not isinstance(strategy, dict) or not strategy.get("strategy_family_id"):
                continue
            candidate_id = f"power-market:{strategy['strategy_family_id']}"
            if candidate_id in seen:
                continue
            seen.add(candidate_id)
            admission_state = _first_text(
                strategy.get("admission_state"), default="research_sleeve_under_evidenced"
            )
            current_signal = strategy.get("current_signal")
            current_signal = current_signal if isinstance(current_signal, dict) else {}
            rows.append(
                {
                    "candidate_id": candidate_id,
                    "label": _first_text(strategy.get("label"), default="Power-market strategy"),
                    "state": admission_state,
                    "state_label": admission_state.replace("_", " ").title(),
                    "thesis": _first_text(
                        strategy.get("plain_english"), strategy.get("thesis"),
                        default="The power-market research thesis has not exported yet.",
                    ),
                    "research_score": current_signal.get("research_score"),
                    "instruments": [
                        row.get("symbol")
                        for row in _safe_list(strategy.get("watched_markets"))
                        if isinstance(row, dict) and row.get("symbol")
                    ],
                    "sources": _safe_list(strategy.get("source_keys")),
                    "blocker": (
                        "The frozen current trigger, Akber, risk, Router, or PaperOps gates have not all passed."
                    ),
                    "next_action": _first_text(
                        context.get("power_market_dashboard", {}).get("next_action"),
                        strategy.get("next_evidence_requirement"),
                        default="Continue provider-backed collection and testing.",
                    ),
                    "human_admission_required": False,
                    "automatic_policy_admission": True,
                    "automatic_risk_envelope_expansion_allowed": False,
                    "paper_order_allowed": False,
                }
            )
    score_records = [row for row in context.get("pattern_score_v3_records", []) if isinstance(row, dict)]
    agnostic = [row for row in score_records if row.get("strategy_agnostic") is True and row.get("negative_control") is not True]
    agnostic.sort(key=lambda row: _float(row.get("raw_pattern_score"), 0.0), reverse=True)
    nearest = agnostic[0] if agnostic else {}
    admitted_count = sum(
        str(row.get("state") or "").lower() in {
            "admitted",
            "approved",
            "human_approved",
            "emerging_strategy_admitted_for_current_experimental_review",
            "validated_candidate_pending_canonical_edge_admission",
        }
        for row in rows
    )
    return {
        "status": "emerging_candidates_present" if rows else "no_candidate_has_earned_emerging_status",
        "candidate_count": len(rows),
        "admitted_count": admitted_count,
        "rows": rows,
        "empty_state_headline": "No new strategy has earned candidate status yet.",
        "empty_state_explanation": (
            "Qadam has strategy-agnostic observations, but none has passed provider-backed backtesting, "
            "untouched holdout validation, costs, and the new-family proposal gate."
        ),
        "nearest_research_observation": {
            "instrument": nearest.get("instrument"),
            "research_score": nearest.get("raw_pattern_score"),
            "state": nearest.get("confidence_state"),
            "missing_critical_features": _safe_list(nearest.get("missing_critical_features")),
            "next_gate": "Provider-backed forward labels and statistical backtesting",
        } if nearest else {},
        "observations_waiting_for_evidence_count": discovery.get("strategy_agnostic_scan_count", 0),
        "artifact_refs": [
            _artifact_ref(NEW_STRATEGY_FAMILY_PROPOSALS_ARTIFACT),
            _artifact_ref(STRATEGY_HYPOTHESES_V3_ARTIFACT),
            _artifact_ref(STRATEGY_FOUNDRY_V3_ARTIFACT),
        ],
    }


def _strategy_admission_path(
    context: dict[str, Any],
    discovery: dict[str, Any],
    emerging: dict[str, Any],
) -> dict[str, Any]:
    backtest = context.get("backtest_results_summary", {})
    edge_registry = context.get("edge_registry_summary", {})
    stage_specs = [
        ("open_discovery", "Open discovery", _int(discovery.get("strategy_agnostic_scan_count"), 0), "Strategy-agnostic observations across the trading universe."),
        ("evidence_ready", "Evidence-ready observation", _int(discovery.get("evidence_ready_observation_count"), 0), "Enough current features exist to write a point-in-time score."),
        ("historical_backtest", "Historical backtest", _int(backtest.get("completed_method_count"), 0), "Forward outcomes, costs, walk-forward folds, and holdouts are completed."),
        ("validated_edge", "Validated edge", _int(edge_registry.get("validated_edge_count"), 0), "A repeatable result survives false-discovery and untouched-holdout checks."),
        ("strategy_proposal", "Emerging strategy proposal", _int(emerging.get("candidate_count"), 0), "A novel edge receives a strategy thesis, instruments, invalidation, and lineage."),
        (
            "bounded_policy_admission",
            "Bounded policy admission",
            _int(emerging.get("admitted_count"), 0),
            "A proposal that satisfies the frozen evidence contract becomes a paper-only research strategy without expanding its risk envelope.",
        ),
    ]
    stages = []
    current_assigned = False
    for stage_id, label, count, explanation in stage_specs:
        if count > 0:
            state = "reached"
        elif not current_assigned:
            state = "current_gate"
            current_assigned = True
        else:
            state = "waiting"
        stages.append(
            {
                "stage_id": stage_id,
                "label": label,
                "count": count,
                "state": state,
                "explanation": explanation,
            }
        )
    current = next((row for row in stages if row["state"] == "current_gate"), stages[-1])
    return {
        "status": "admission_path_visible",
        "stages": stages,
        "current_stage_id": current["stage_id"],
        "current_stage_label": current["label"],
        "current_explanation": (
            f"Qadam is currently stopped at {current['label'].lower()}. "
            "Later stages remain at zero until their own evidence exists."
        ),
        "after_admission": ["Generate a current hypothesis", "Open the Decision Room"],
        "next_destination": {
            "label": "Decision Room",
            "module_id": "decide",
            "view_id": "decision",
            "explanation": "Once an admitted strategy produces a current setup, the Decision Room applies the six-stage practical filter and Router to that specific setup.",
        },
        "authority_boundary": "Admission changes research classification only; it cannot create an order, approval, broker write, proof credit, or live-capital authority.",
        "artifact_refs": [
            _artifact_ref(PATTERN_SCORE_V3_ARTIFACT),
            _artifact_ref(BACKTEST_RESULTS_SUMMARY_ARTIFACT),
            _artifact_ref(EDGE_REGISTRY_SUMMARY_ARTIFACT),
            _artifact_ref(NEW_STRATEGY_FAMILY_PROPOSALS_ARTIFACT),
        ],
    }


def build_strategy_universe(context: dict[str, Any], generated_at: str) -> dict[str, Any]:
    artifact = _section_base("qsase_dashboard_strategy_universe", generated_at)
    family_map = context.get("strategy_family_map", {})
    known_families = family_map.get("known_families", {}) if isinstance(family_map.get("known_families"), dict) else {}
    router_families = {_strategy_family_from_router(row) for row in context.get("router_decisions", [])}
    router_families.update(_strategy_family_from_router(row) for row in context.get("router_v2_decisions", []))
    router_families.discard("unmapped_strategy_family")
    evidence_by_family = _strategy_evidence_by_family(context)
    validation_by_family = _strategy_v3_by_family(context)
    router_by_family = _router_v2_by_family(context)
    trading_universe = context.get("universal_matrix", {}).get("trading_universe", {})
    watched_markets = _safe_list(trading_universe.get("instruments"))
    assigned_market_ids: set[str] = set()

    def _market_matches_family(market: dict[str, Any], family: dict[str, Any]) -> bool:
        haystack = " ".join(
            str(market.get(key) or "")
            for key in ("instrument_id", "symbol", "display_name", "market_family")
        ).lower()
        for keyword in _safe_list(family.get("instrument_keywords")) + _safe_list(family.get("allowed_proxy_set")):
            token = str(keyword or "").strip().lower()
            if token and token in haystack:
                return True
        catalyst = str(family.get("catalyst_class") or "").lower()
        return bool(catalyst and any(part in haystack for part in catalyst.split("_") if len(part) > 3))

    def _strategy_markets(family: dict[str, Any]) -> list[dict[str, Any]]:
        rows = []
        for index, market in enumerate(watched_markets):
            if not isinstance(market, dict) or not _market_matches_family(market, family):
                continue
            market_id = _first_text(market.get("instrument_id"), market.get("symbol"), default=f"market_{index}")
            assigned_market_ids.add(market_id)
            rows.append(
                {
                    "instrument_id": market.get("instrument_id"),
                    "symbol": market.get("symbol"),
                    "display_name": market.get("display_name"),
                    "market_family": market.get("market_family"),
                    "paperability_state": market.get("paperability_state"),
                    "qualified_setup_state": market.get("qualified_setup_state"),
                    "paper_order_allowed": False,
                }
            )
        return rows

    all_rows = []
    for family_id, family in sorted(known_families.items()):
        current_state = "currently_in_play_blocked_or_rejected" if family_id in router_families else "available_strategy_family"
        strategy_markets = _strategy_markets(family)
        row = {
            "strategy_family_id": family_id,
            "label": family.get("label") or family_id,
            "catalyst_class": family.get("catalyst_class"),
            "allowed_proxy_set": family.get("allowed_proxy_set", []),
            "source_keywords": family.get("source_keywords", []),
            "instrument_keywords": family.get("instrument_keywords", []),
            "watched_markets": strategy_markets,
            "watched_market_count": len(strategy_markets),
            "current_state": current_state,
            "currently_in_play": family_id in router_families,
            "artifact_refs": [
                _artifact_ref(STRATEGY_FAMILY_MAP_ARTIFACT, f"known_families.{family_id}"),
                _artifact_ref(STRATEGY_EVIDENCE_MAP_RECORDS_ARTIFACT),
                _artifact_ref(ROUTER_V2_DECISIONS_ARTIFACT),
            ],
        }
        row.update(
            _strategy_playbook_payload(
                family_id=family_id,
                family=family,
                row=row,
                strategy_markets=strategy_markets,
                evidence_by_family=evidence_by_family,
                router_by_family=router_by_family,
                context=context,
            )
        )
        _apply_strategy_validation_truth(row, validation_by_family.get(family_id, {}))
        all_rows.append(row)
    for family in sorted(router_families - set(known_families.keys())):
        row = {
            "strategy_family_id": family,
            "label": family.replace("_", " ").title(),
            "catalyst_class": "router_discovered_or_unmapped",
            "allowed_proxy_set": [],
            "source_keywords": [],
            "instrument_keywords": [],
            "watched_markets": [],
            "watched_market_count": 0,
            "current_state": "currently_in_play_blocked_or_rejected",
            "currently_in_play": True,
            "artifact_refs": [_artifact_ref(ROUTER_DECISIONS_ARTIFACT), _artifact_ref(ROUTER_V2_DECISIONS_ARTIFACT)],
        }
        row.update(
            _strategy_playbook_payload(
                family_id=family,
                family={"label": row["label"]},
                row=row,
                strategy_markets=[],
                evidence_by_family=evidence_by_family,
                router_by_family=router_by_family,
                context=context,
            )
        )
        _apply_strategy_validation_truth(row, validation_by_family.get(family, {}))
        all_rows.append(row)
    in_play_rows = [row for row in all_rows if row["currently_in_play"]]
    unassigned_markets = []
    for index, market in enumerate(watched_markets):
        if not isinstance(market, dict):
            continue
        market_id = _first_text(market.get("instrument_id"), market.get("symbol"), default=f"market_{index}")
        if market_id in assigned_market_ids:
            continue
        unassigned_markets.append(
            {
                "instrument_id": market.get("instrument_id"),
                "symbol": market.get("symbol"),
                "display_name": market.get("display_name"),
                "market_family": market.get("market_family"),
                "paperability_state": market.get("paperability_state"),
                "qualified_setup_state": market.get("qualified_setup_state"),
                "paper_order_allowed": False,
            }
        )
    discovery = _strategy_discovery_engine(context)
    emerging = _emerging_strategy_candidates(context, discovery)
    admission = _strategy_admission_path(context, discovery, emerging)
    validated_strategy_count = sum(_int(row.get("validated_edge_count"), 0) > 0 for row in all_rows)
    artifact.update(
        {
            "status": "strategy_universe_visible" if all_rows else "strategy_universe_explicitly_empty",
            "all_strategy_count": len(all_rows),
            "currently_in_play_count": len(in_play_rows),
            "watched_market_count": len(watched_markets),
            "unassigned_watched_market_count": len(unassigned_markets),
            "strategy_hypothesis_count": int(context.get("strategy_foundry", {}).get("strategy_hypothesis_count") or 0),
            "rejected_hypothesis_count": len(context.get("rejected_strategy_hypotheses", [])),
            "defined_strategy_count": len(all_rows),
            "validated_strategy_count": validated_strategy_count,
            "emerging_strategy_candidate_count": emerging["candidate_count"],
            "strategy_discovery_engine": discovery,
            "emerging_strategy_candidates": emerging,
            "strategy_admission_path": admission,
            "all_strategy_rows": all_rows,
            "currently_in_play_rows": in_play_rows,
            "unassigned_watched_markets": unassigned_markets,
            "artifact_refs": [
                _artifact_ref(STRATEGY_FAMILY_MAP_ARTIFACT),
                _artifact_ref(ROUTER_DECISIONS_ARTIFACT),
                _artifact_ref(STRATEGY_EVIDENCE_MAP_V3_ARTIFACT),
                _artifact_ref(PATTERN_SCORE_V3_ARTIFACT),
                _artifact_ref(NEW_STRATEGY_FAMILY_PROPOSALS_ARTIFACT),
            ],
        }
    )
    return artifact


def build_pattern_lab(context: dict[str, Any], generated_at: str) -> dict[str, Any]:
    artifact = _section_base("qsase_dashboard_pattern_lab", generated_at)
    linear_rows = [
        {
            "pattern_type": "linear",
            "pattern_id": row.get("linear_pattern_id"),
            "source_pattern_id": row.get("source_pattern_id"),
            "instrument": row.get("market_expression", {}).get("instrument"),
            "direction": row.get("market_expression", {}).get("direction"),
            "state": row.get("decision", {}).get("linear_status"),
            "score": row.get("linear_score"),
            "reason": row.get("decision", {}).get("reason"),
            "candidate_for_strategy_foundry": row.get("candidate_for_strategy_foundry"),
            "paper_order_allowed": False,
            "artifact_refs": [_artifact_ref(LINEAR_RESULTS_ARTIFACT, str(row.get("linear_pattern_id")))],
        }
        for row in context.get("linear_results", [])[:20]
    ]
    nonlinear_rows = [
        {
            "pattern_type": "nonlinear",
            "pattern_id": row.get("nonlinear_pattern_id"),
            "source_pattern_id": row.get("source_pattern_id"),
            "linear_pattern_id": row.get("source_linear_pattern_id"),
            "instrument": row.get("market_expression", {}).get("instrument"),
            "state": row.get("decision", {}).get("nonlinear_status"),
            "quantum_review_state": row.get("quantum_review_state"),
            "quantum_review_id": row.get("quantum_review_id"),
            "score": row.get("nonlinear_tests", {}).get("nonlinear_score"),
            "linear_baseline_beaten": row.get("nonlinear_tests", {}).get("linear_baseline_beaten"),
            "paper_order_allowed": False,
            "artifact_refs": [_artifact_ref(NONLINEAR_RESULTS_ARTIFACT, str(row.get("nonlinear_pattern_id")))],
        }
        for row in context.get("nonlinear_results", [])[:20]
    ]
    quantum_rows = [
        {
            "review_id": row.get("quantum_review_id"),
            "state": row.get("review_state"),
            "backend": row.get("backend"),
            "quantum_mode": row.get("quantum_mode"),
            "recommendation": row.get("recommendation"),
            "usefulness_class": row.get("quantum_usefulness", {}).get("usefulness_class"),
            "trade_confirmation": False,
            "artifact_refs": [_artifact_ref(QUANTUM_REVIEWS_ARTIFACT, str(row.get("quantum_review_id")))],
        }
        for row in context.get("quantum_reviews", [])[:20]
    ]
    artifact.update(
        {
            "status": "pattern_lab_visible" if linear_rows or nonlinear_rows else "pattern_lab_degraded",
            "linear_pattern_count": len(linear_rows),
            "nonlinear_pattern_count": len(nonlinear_rows),
            "quantum_review_count": len(quantum_rows),
            "linear_rows": linear_rows,
            "nonlinear_rows": nonlinear_rows,
            "quantum_rows": quantum_rows,
            "artifact_refs": [
                _artifact_ref(LINEAR_LAB_ARTIFACT),
                _artifact_ref(NONLINEAR_LAB_ARTIFACT),
                _artifact_ref(QUANTUM_REVIEWS_ARTIFACT),
            ],
        }
    )
    return artifact


def build_trade_intents(context: dict[str, Any], generated_at: str) -> dict[str, Any]:
    artifact = _section_base("qsase_dashboard_trade_intents", generated_at)
    rows = []
    for row in context.get("router_decisions", []):
        decision = row.get("decision", {})
        identity = row.get("candidate_identity", {})
        rows.append(
            {
                "row_type": "trade_intent_review_record",
                "intent_id": row.get("router_decision_id"),
                "strategy_family": _strategy_family_from_router(row),
                "candidate_identity_key": identity.get("candidate_identity_key"),
                "instrument": identity.get("instrument"),
                "thesis": identity.get("thesis"),
                "state": decision.get("router_output"),
                "reason": decision.get("reason"),
                "next_allowed_action": decision.get("next_required_action"),
                "source_quorum": row.get("gates", {}).get("source_quorum"),
                "akber_filter": row.get("gates", {}).get("akber_filter"),
                "quantum_review": row.get("gates", {}).get("quantum_review"),
                "paper_route": row.get("gates", {}).get("paper_route"),
                "is_trade": False,
                "is_order": False,
                "is_approval": False,
                "is_qualified_setup": False,
                "paper_order_created": False,
                "artifact_refs": [_artifact_ref(ROUTER_DECISIONS_ARTIFACT, str(row.get("router_decision_id")))],
            }
        )
    artifact.update(
        {
            "status": "trade_intents_visible" if rows else "trade_intents_explicitly_empty",
            "intent_count": len(rows),
            "rows": rows,
            "explicitly_empty": not rows,
            "rows_are_not_orders": True,
            "rows_are_not_approvals": True,
            "rows_are_not_qualified_setups": True,
            "artifact_refs": [_artifact_ref(ROUTER_DECISIONS_ARTIFACT), _artifact_ref(AKBER_FILTER_RESULTS_ARTIFACT)],
        }
    )
    return artifact


def _pattern_candidates(context: dict[str, Any]) -> list[dict[str, Any]]:
    engine_patterns = _safe_list(context.get("pattern_engine", {}).get("candidate_patterns"))
    if engine_patterns:
        return engine_patterns
    return _safe_list(context.get("edge_pattern_ledger", {}).get("patterns"))


def _workflow_missing_text(missing: list[Any]) -> str:
    labels = [str(item).replace("_", " ") for item in missing if item]
    return ", ".join(labels) if labels else "final review gates"


def _workflow_paperops_ready(pattern: dict[str, Any], context: dict[str, Any]) -> bool:
    paperops_gate = context.get("paperops_gate", {})
    guarded_route = str(paperops_gate.get("guarded_alpaca_paper_route_state") or "").lower()
    missing = _safe_list(pattern.get("missing_criteria"))
    route_ready = any(token in guarded_route for token in ("ready", "available", "enabled"))
    return (
        not missing
        and _float(pattern.get("edge_readiness_score")) >= 0.8
        and bool(pattern.get("quantum_gate_dependency_satisfied", pattern.get("quantum_required", False)))
        and route_ready
        and int(paperops_gate.get("qctrl_hold_count") or 0) == 0
        and int(paperops_gate.get("drawdown_block_count") or 0) == 0
        and int(paperops_gate.get("duplicate_exposure_count") or 0) == 0
        and int(paperops_gate.get("duplicate_idempotency_count") or 0) == 0
    )


def _workflow_telegram_message(records: list[dict[str, Any]]) -> dict[str, Any]:
    ready_count = sum(1 for record in records if record.get("paperops_handoff_candidate"))
    top_labels = [record.get("market_sleeve") for record in records[:3] if record.get("market_sleeve")]
    needs = records[0].get("missing_criteria") if records else []
    state = f"{len(records)} patterns documented; {ready_count} ready for PaperOps"
    reason = (
        f"{', '.join(top_labels)} need {_workflow_missing_text(needs)}"
        if records
        else "no pattern records are exported yet"
    )
    body = (
        "Qadam pattern note\n"
        f"State: {state}\n"
        f"Reason: {reason}\n"
        "Next: keep shadow review; handoff only after gates pass\n"
        "Order: none submitted"
    )
    return {
        "message_class": "qsase_pattern_to_paper_workflow",
        "review_only": True,
        "command_disabled": True,
        "telegram_live_send_allowed": False,
        "telegram_command_path_enabled": False,
        "contains_command": False,
        "contains_broker_instruction": False,
        "body": body,
    }


def _evidence_quality_by_sleeve(context: dict[str, Any]) -> dict[str, dict[str, Any]]:
    evidence = context.get("evidence_quality", {})
    records: dict[str, dict[str, Any]] = {}
    for record in _safe_list(evidence.get("records")):
        if not isinstance(record, dict):
            continue
        sleeve = _first_text(record.get("sleeve_key"), record.get("market_sleeve"), default="")
        if sleeve:
            records[sleeve.lower()] = record
    return records


def build_evidence_quality(context: dict[str, Any], generated_at: str) -> dict[str, Any]:
    artifact = _section_base("qsase_evidence_quality", generated_at)
    evidence = context.get("evidence_quality", {})
    if not evidence or evidence.get("public_safe") is not True:
        artifact.update(
            {
                "status": "evidence_quality_missing",
                "summary": "Evidence quality has not exported a public-safe artifact yet.",
                "evidence_record_count": 0,
                "paper_review_candidate_count": 0,
                "held_for_evidence_count": 0,
                "records": [],
                "boundary": "Dashboard visibility only. No trade candidate, order, broker write, proof credit, or live-capital authority.",
                "artifact_refs": [_artifact_ref(EVIDENCE_QUALITY_ARTIFACT)],
            }
        )
        return artifact
    artifact.update(copy.deepcopy(evidence))
    artifact["artifact_type"] = "qsase_evidence_quality"
    artifact["dashboard_section"] = True
    artifact["generated_at"] = evidence.get("generated_at") or generated_at
    artifact.setdefault("artifact_refs", [_artifact_ref(EVIDENCE_QUALITY_ARTIFACT)])
    return artifact


def build_pattern_to_paper_workflow(context: dict[str, Any], generated_at: str) -> dict[str, Any]:
    artifact = _section_base("qsase_pattern_to_paper_workflow", generated_at)
    paperops_gate = context.get("paperops_gate", {})
    router = context.get("router", {})
    evidence_by_sleeve = _evidence_quality_by_sleeve(context)
    records = []
    for index, pattern in enumerate(_pattern_candidates(context)):
        sleeve = _first_text(pattern.get("market_sleeve"), pattern.get("label"), pattern.get("sleeve_key"), default="Pattern")
        sleeve_key = _first_text(pattern.get("sleeve_key"), sleeve, default=sleeve).lower()
        evidence_quality = evidence_by_sleeve.get(sleeve_key, {})
        symbols = _safe_list(pattern.get("instrument_symbols"))
        missing = _safe_list(pattern.get("missing_criteria"))
        passed = _safe_list(pattern.get("passed_criteria"))
        paperops_ready = _workflow_paperops_ready(pattern, context) and evidence_quality.get("tradeability_state") == "paper_review_candidate"
        state = "paperops_handoff_candidate" if paperops_ready else "documented_research_pattern"
        next_action = _first_text(
            evidence_quality.get("next_action"),
            default=(
                "route to guarded PaperOps handoff review"
                if paperops_ready
                else f"collect {_workflow_missing_text(missing)} before PaperOps handoff review"
            ),
        )
        workflow_id = _hash_id([pattern.get("pattern_id"), sleeve, symbols, state], "qsase-pattern-workflow")
        records.append(
            {
                "workflow_id": workflow_id,
                "source_pattern_id": pattern.get("pattern_id"),
                "market_sleeve": sleeve,
                "instrument_symbols": symbols,
                "pattern_question": pattern.get("pattern_question"),
                "pattern_thesis": f"{sleeve}: {pattern.get('pattern_question')}",
                "qualitative_summary": pattern.get("strategy_use") or pattern.get("current_observation") or pattern.get("pattern_question"),
                "source_packet_summary": {
                    "source_application": pattern.get("source_application"),
                    "source_count": pattern.get("source_count"),
                    "primary_lens_source_keys": _safe_list(pattern.get("primary_lens_source_keys"))[:8],
                    "source_health": pattern.get("source_health", {}),
                },
                "linear_state": "source_price_lead_lag_or_divergence_observed" if "lead_lag_or_divergence" in passed else "linear_review_needed",
                "nonlinear_state": pattern.get("quantum_gate_decision_status") or pattern.get("status"),
                "quantum_state": {
                    "gate_dependency_satisfied": bool(pattern.get("quantum_gate_dependency_satisfied", False)),
                    "oracle_execution_status": pattern.get("oracle_execution_status"),
                    "hardware_submission_allowed": False,
                    "provider_call_allowed": False,
                },
                "evidence_scores": {
                    "edge_readiness_score": pattern.get("edge_readiness_score"),
                    "source_pressure_score": pattern.get("source_pressure_score"),
                    "signal_review_coverage_score": pattern.get("signal_review_coverage_score"),
                    "ambiguity_score": pattern.get("ambiguity_score"),
                },
                "passed_criteria": passed,
                "missing_criteria": missing,
                "invalidation": f"Invalidate if {_workflow_missing_text(missing)} remains unresolved, source pressure fades, or market confirmation fails.",
                "tradeability_state": evidence_quality.get("tradeability_state", "research_only"),
                "evidence_quality_state": evidence_quality.get("status", evidence_quality.get("tradeability_state", "not_recorded")),
                "evidence_quality_score": evidence_quality.get("scores", {}).get("evidence_quality_score"),
                "evidence_quality": {
                    "available": bool(evidence_quality),
                    "tradeability_state": evidence_quality.get("tradeability_state"),
                    "score": evidence_quality.get("scores", {}).get("evidence_quality_score"),
                    "source_reliability_score": evidence_quality.get("scores", {}).get("source_reliability_score"),
                    "historical_completeness_score": evidence_quality.get("scores", {}).get("historical_completeness_score"),
                    "akber_practical_confirmation_score": evidence_quality.get("scores", {}).get("akber_practical_confirmation_score"),
                    "shadow_replay_score": evidence_quality.get("scores", {}).get("shadow_replay_score"),
                    "quality_bar": evidence_quality.get("quality_bar", {}),
                    "what_qadam_thinks": evidence_quality.get("what_qadam_thinks"),
                    "what_would_confirm": evidence_quality.get("what_would_confirm"),
                    "what_blocks_trade": evidence_quality.get("what_blocks_trade"),
                    "next_action": evidence_quality.get("next_action"),
                },
                "what_qadam_thinks": evidence_quality.get("what_qadam_thinks"),
                "what_would_confirm": evidence_quality.get("what_would_confirm"),
                "what_blocks_trade": evidence_quality.get("what_blocks_trade"),
                "paperops_state": state,
                "paperops_handoff_candidate": paperops_ready,
                "paper_review_eligible": paperops_ready,
                "next_allowed_action": next_action,
                "telegram_summary": {
                    "review_only": True,
                    "live_send_allowed": False,
                    "command_disabled": True,
                    "text": f"{sleeve}: watching {', '.join(symbols) or 'mapped instruments'}; needs {_workflow_missing_text(missing)} before guarded PaperOps review.",
                },
                "paper_order_allowed": False,
                "paper_order_created": False,
                "trade_candidate_created": False,
                "qualified_setup_created": False,
                "broker_write_allowed": False,
                "broker_write_count": 0,
                "proof_credit_allowed": False,
                "live_capital_enabled": False,
                "artifact_refs": [
                    _artifact_ref(PATTERN_ENGINE_ARTIFACT, f"candidate_patterns.{index}"),
                    _artifact_ref(EDGE_PATTERN_LEDGER_ARTIFACT),
                    _artifact_ref(EVIDENCE_QUALITY_ARTIFACT),
                    _artifact_ref(ROUTER_ARTIFACT),
                    _artifact_ref(PAPEROPS_GATE_ARTIFACT),
                ],
            }
        )
    handoff_count = sum(1 for record in records if record["paperops_handoff_candidate"])
    documented_count = len(records)
    telegram_message = _workflow_telegram_message(records)
    status = "pattern_to_paper_workflow_ready" if records else "pattern_to_paper_workflow_empty"
    trade_state = "paperops_handoff_candidate_available" if handoff_count else "research_only_waiting_for_validated_pattern"
    artifact.update(
        {
            "status": status,
            "workflow_state": trade_state,
            "recognized_pattern_count": documented_count,
            "documented_thesis_count": documented_count,
            "telegram_candidate_count": 1 if records else 0,
            "paperops_handoff_candidate_count": handoff_count,
            "paperops_gate_status": paperops_gate.get("status"),
            "paperops_top_blocking_gate": paperops_gate.get("top_blocking_gate"),
            "router_status": router.get("status"),
            "router_why_not_trading_now": router.get("why_not_trading_now", {}),
            "workflow_steps": [
                {"step": "Recognize", "state": f"{documented_count} patterns recognized from the source-price universe"},
                {"step": "Document", "state": f"{documented_count} thesis records written with source and instrument lineage"},
                {"step": "Communicate", "state": "review-only Telegram candidate prepared" if records else "no message candidate"},
                {"step": "Paper review", "state": f"{handoff_count} guarded PaperOps handoff candidates; no direct orders"},
            ],
            "records": records,
            "telegram_candidate": telegram_message,
            "paper_order_allowed": False,
            "paper_order_created_count": 0,
            "trade_candidate_created": False,
            "qualified_setup_created": False,
            "broker_write_allowed": False,
            "broker_write_count": 0,
            "proof_credit_allowed": False,
            "live_capital_enabled": False,
            "boundary": "Pattern workflow documents evidence and prepares guarded PaperOps review context only; it cannot create orders, approvals, broker writes, proof credit, Telegram commands, or live capital.",
            "artifact_refs": [
                _artifact_ref(PATTERN_ENGINE_ARTIFACT),
                _artifact_ref(EDGE_PATTERN_LEDGER_ARTIFACT),
                _artifact_ref(EVIDENCE_QUALITY_ARTIFACT),
                _artifact_ref(ROUTER_ARTIFACT),
                _artifact_ref(PAPEROPS_GATE_ARTIFACT),
            ],
        }
    )
    return artifact


SOURCE_NAME_MAP = {
    "acled": "ACLED conflict data",
    "gdelt": "GDELT news events",
    "nasa_firms": "NASA FIRMS fire activity",
    "ais_maritime": "AIS maritime movement",
    "aviationstack": "AviationStack flight data",
    "gps_jamming": "GPS interference",
    "fred": "FRED macro data",
    "un_comtrade": "UN Comtrade trade data",
    "tradingview_mcp": "TradingView technical analysis",
    "tradingview_paid_alerts": "TradingView alerts",
    "alpaca": "Alpaca market data",
    "bis": "BIS macro data",
    "ecb": "ECB macro data",
    "usgs": "USGS commodity data",
    "rss": "RSS news feeds",
    "twitter_x": "X/Twitter social signal",
    "reddit": "Reddit narrative signal",
}

CRITERION_TRANSLATIONS = {
    "all_source_price_cross_scan": "all connected sources were compared against the watched market",
    "lead_lag_or_divergence": "a source-price lead, lag, or divergence was observed",
    "llm_adversarial_review": "the LLM review challenged the thesis",
    "market_confirmation": "market data gave some confirmation",
    "multi_source_corroboration": "more than one source family supported the pattern",
    "paper_safety_route": "the paper-only safety route is intact",
    "quantum_nonlinear_review": "the nonlinear quantum review gate was satisfied",
    "thirty_day_persistence": "the pattern still needs to keep appearing over the paper trial window",
}


def _source_names(source_keys: list[Any]) -> list[str]:
    names = []
    for key in source_keys:
        source_key = str(key)
        names.append(SOURCE_NAME_MAP.get(source_key, source_key.replace("_", " ").title()))
    return names


def _plain_criteria(items: list[Any]) -> list[str]:
    return [CRITERION_TRANSLATIONS.get(str(item), str(item).replace("_", " ")) for item in items if item]


def _confidence_label(score: Any) -> str:
    value = _float(score)
    if value >= 0.85:
        return "strong evidence, still gated"
    if value >= 0.7:
        return "building evidence"
    if value > 0:
        return "early evidence"
    return "not scored yet"


def _finding_stage(record: dict[str, Any], edge_record: dict[str, Any] | None = None) -> tuple[str, str]:
    tradeability_state = str(record.get("tradeability_state") or "")
    if tradeability_state == "paper_review_candidate":
        return "paper_ready", "Paper-ready review candidate"
    if record.get("paperops_handoff_candidate"):
        return "paper_ready", "Paper-ready review candidate"
    if tradeability_state in {
        "hold_missing_akber_inputs",
        "hold_missing_historical_forward_windows",
        "hold_unvalidated_edge",
        "shadow_only",
    }:
        return "documented", tradeability_state.replace("_", " ").title()
    missing = _safe_list(record.get("missing_criteria"))
    edge_stage = str((edge_record or {}).get("edge_stage") or "").lower()
    if "validated" in edge_stage and "not_validated" not in edge_stage:
        return "validated", "Validated edge"
    if record.get("paper_review_eligible"):
        return "trade_candidate", "Trade candidate"
    if record.get("pattern_thesis") and record.get("source_packet_summary"):
        return "documented", "Documented research finding"
    if missing:
        return "found", "Found signal"
    return "found", "Found signal"


def _stage_counts(findings: list[dict[str, Any]]) -> dict[str, int]:
    counts = Counter(finding.get("stage_key", "found") for finding in findings)
    return {
        "found": counts.get("found", 0),
        "documented": counts.get("documented", 0),
        "validated": counts.get("validated", 0),
        "trade_candidate": counts.get("trade_candidate", 0),
        "paper_ready": counts.get("paper_ready", 0),
        "blocked": counts.get("blocked", 0),
    }


def _edge_record_by_sleeve(context: dict[str, Any]) -> dict[str, dict[str, Any]]:
    records = {}
    for pattern in _safe_list(context.get("edge_pattern_ledger", {}).get("patterns")):
        sleeve = _first_text(pattern.get("label"), pattern.get("market_sleeve"), pattern.get("sleeve_key"), default="")
        if sleeve:
            records[sleeve.lower()] = pattern
    return records


def _top_rank_flags(findings: list[dict[str, Any]]) -> dict[str, str | None]:
    if not findings:
        return {
            "most_actionable_pattern_id": None,
            "strongest_evidence_pattern_id": None,
            "closest_to_paper_review_pattern_id": None,
            "largest_blocker_pattern_id": None,
        }
    most_actionable = max(findings, key=lambda row: row.get("ranking_scores", {}).get("actionability", 0))
    strongest = max(findings, key=lambda row: row.get("ranking_scores", {}).get("evidence_strength", 0))
    closest = max(findings, key=lambda row: row.get("ranking_scores", {}).get("paper_review_closeness", 0))
    largest_blocker = max(findings, key=lambda row: len(row.get("blockers", [])))
    return {
        "most_actionable_pattern_id": most_actionable.get("pattern_id"),
        "strongest_evidence_pattern_id": strongest.get("pattern_id"),
        "closest_to_paper_review_pattern_id": closest.get("pattern_id"),
        "largest_blocker_pattern_id": largest_blocker.get("pattern_id"),
    }


def _human_pattern_brief(context: dict[str, Any], workflow: dict[str, Any], findings: list[dict[str, Any]]) -> dict[str, Any]:
    daily = context.get("daily_telegram_learning_brief", {})
    human = context.get("telegram_human_brief", {})
    body = _first_text(daily.get("body"), human.get("body"), default="")
    if not body:
        ready_count = sum(1 for finding in findings if finding.get("stage_key") == "paper_ready")
        top = findings[0] if findings else {}
        body = (
            f"Qadam has documented {len(findings)} pattern findings and {ready_count} are ready for paper-trade review. "
            f"The strongest current watch is {top.get('market_affected', 'the watched universe')}: {top.get('what_qadam_thinks', 'Qadam is still gathering evidence.')}"
        )
    body = body.replace("PaperOps", "paper-trade review").replace("paper proof ledger", "paper proof record")
    return {
        "source": "daily_telegram_learning_brief" if daily.get("body") else "telegram_human_brief" if human.get("body") else "pattern_intelligence_fallback",
        "body": body,
        "review_only": True,
        "command_disabled": True,
        "telegram_live_send_allowed": False,
        "telegram_command_path_enabled": False,
    }


def build_pattern_intelligence(
    context: dict[str, Any],
    generated_at: str,
    pattern_lab: dict[str, Any],
    workflow: dict[str, Any],
) -> dict[str, Any]:
    artifact = _section_base("qsase_pattern_intelligence", generated_at)
    edge_by_sleeve = _edge_record_by_sleeve(context)
    findings: list[dict[str, Any]] = []
    for index, record in enumerate(_safe_list(workflow.get("records"))):
        sleeve = _first_text(record.get("market_sleeve"), default="Watched market")
        edge_record = edge_by_sleeve.get(sleeve.lower())
        source_keys = _safe_list(record.get("source_packet_summary", {}).get("primary_lens_source_keys"))
        source_names = _source_names(source_keys)
        scores = record.get("evidence_scores", {}) if isinstance(record.get("evidence_scores"), dict) else {}
        evidence_quality = record.get("evidence_quality", {}) if isinstance(record.get("evidence_quality"), dict) else {}
        readiness_score = _float(scores.get("edge_readiness_score"))
        evidence_quality_score = _float(record.get("evidence_quality_score"), _float(evidence_quality.get("score"), 0.0))
        if evidence_quality_score:
            readiness_score = evidence_quality_score
        source_pressure_score = _float(scores.get("source_pressure_score"))
        coverage_score = _float(scores.get("signal_review_coverage_score"))
        ambiguity_score = _float(scores.get("ambiguity_score"))
        missing = _safe_list(record.get("missing_criteria"))
        passed = _safe_list(record.get("passed_criteria"))
        stage_key, stage_label = _finding_stage(record, edge_record)
        pattern_id = _first_text(record.get("source_pattern_id"), record.get("workflow_id"), default=f"pattern_{index}")
        source_chain_text = ", ".join(source_names[:4])
        if len(source_names) > 4:
            source_chain_text = f"{source_chain_text}, plus {len(source_names) - 4} more"
        what_blocks = _first_text(
            record.get("what_blocks_trade"),
            evidence_quality.get("what_blocks_trade"),
            default=(
                f"Still needs {_workflow_missing_text(missing)} before it can enter paper-trade review."
                if missing
                else "No upstream research blocker is recorded; it still needs final risk and paper-route checks."
            ),
        )
        what_confirms = _first_text(
            record.get("what_would_confirm"),
            evidence_quality.get("what_would_confirm"),
            default=(
                "The relationship needs to keep appearing over real elapsed time, with source agreement and market reaction staying aligned."
                if missing
                else "Sustained source agreement, price confirmation, and clean risk checks would confirm it."
            ),
        )
        raw_next_action = str(record.get("next_allowed_action") or "continue observation before paper-trade review")
        next_action = (
            raw_next_action
            .replace("PaperOps handoff review", "paper-trade review")
            .replace("PaperOps handoff", "paper-trade review")
        )
        actionability = readiness_score * 100 + source_pressure_score * 20 + coverage_score * 10 - len(missing) * 25 - ambiguity_score * 10
        evidence_strength = readiness_score * 35 + source_pressure_score * 35 + coverage_score * 20 - ambiguity_score * 10
        paper_review_closeness = 100 if record.get("paperops_handoff_candidate") else max(0, 80 - len(missing) * 20)
        findings.append(
            {
                "finding_id": _hash_id([pattern_id, sleeve, index], "qsase-pattern-finding"),
                "pattern_id": pattern_id,
                "rank": index + 1,
                "title": f"{sleeve} pattern watch",
                "market_affected": sleeve,
                "instrument_symbols": _safe_list(record.get("instrument_symbols")),
                "stage_key": stage_key,
                "stage_label": stage_label,
                "lifecycle_label": stage_label,
                "confidence_label": _confidence_label(readiness_score),
                "confidence_score": round(readiness_score, 3),
                "detected_signal": _first_text(record.get("pattern_question"), record.get("pattern_thesis")),
                "source_chain": source_names,
                "source_signal_summary": (
                    f"{source_chain_text} are being cross-checked against {sleeve} prices."
                    if source_names
                    else f"Connected Qadam sources are being cross-checked against {sleeve} prices."
                ),
                "price_relationship": (
                    "Qadam has observed source-price lead, lag, or divergence evidence."
                    if "lead_lag_or_divergence" in passed
                    else "Qadam has not yet exported a source-price relationship strong enough to rely on."
                ),
                "evidence_summary": _first_text(record.get("qualitative_summary"), default="Evidence summary pending."),
                "what_qadam_thinks": _first_text(
                    record.get("what_qadam_thinks"),
                    evidence_quality.get("what_qadam_thinks"),
                    default=(
                        f"Qadam sees a possible {sleeve} relationship, but it is still a research finding rather than a trade."
                        if stage_key in {"found", "documented"}
                        else f"Qadam sees {sleeve} moving closer to paper-trade review."
                    ),
                ),
                "what_would_confirm": what_confirms,
                "what_blocks_trade": what_blocks,
                "next_action": next_action,
                "tradeability_state": record.get("tradeability_state"),
                "evidence_quality_state": record.get("evidence_quality_state"),
                "evidence_quality_score": round(evidence_quality_score, 3),
                "quality_bar": evidence_quality.get("quality_bar", {}),
                "passed_plain_english": _plain_criteria(passed),
                "missing_plain_english": _plain_criteria(missing),
                "blockers": _plain_criteria(missing) or ["final risk and paper-route review"],
                "quantum_review": {
                    "required": True,
                    "status": "nonlinear review gate satisfied" if record.get("quantum_state", {}).get("gate_dependency_satisfied") else "nonlinear review still pending",
                    "plain_english_result": (
                        "The nonlinear quantum review is satisfied for research, but it does not create a trade by itself."
                        if record.get("quantum_state", {}).get("gate_dependency_satisfied")
                        else "Qadam cannot promote this pattern until the nonlinear review gate is satisfied."
                    ),
                    "provider_call_allowed": False,
                    "hardware_submission_allowed": False,
                },
                "readiness": {
                    "research_finding": True,
                    "validated_edge": stage_key in {"validated", "trade_candidate", "paper_ready"},
                    "tradeable": stage_key == "paper_ready",
                    "paper_review_eligible": bool(record.get("paper_review_eligible")),
                    "paper_order_allowed": False,
                },
                "ranking_scores": {
                    "actionability": round(actionability, 3),
                    "evidence_strength": round(evidence_strength, 3),
                    "paper_review_closeness": round(paper_review_closeness, 3),
                },
                "rank_badges": [],
                "paper_order_allowed": False,
                "paper_order_created": False,
                "broker_write_allowed": False,
                "live_capital_enabled": False,
                "artifact_refs": record.get("artifact_refs", []),
            }
        )
    findings.sort(
        key=lambda row: (
            row.get("ranking_scores", {}).get("paper_review_closeness", 0),
            row.get("ranking_scores", {}).get("actionability", 0),
            row.get("ranking_scores", {}).get("evidence_strength", 0),
        ),
        reverse=True,
    )
    flags = _top_rank_flags(findings)
    badge_by_flag = {
        "most_actionable_pattern_id": "most actionable pattern",
        "strongest_evidence_pattern_id": "strongest evidence",
        "closest_to_paper_review_pattern_id": "closest to paper-trade review",
        "largest_blocker_pattern_id": "clearest blocker",
    }
    for finding in findings:
        badges = [
            label
            for flag, label in badge_by_flag.items()
            if flags.get(flag) and finding.get("pattern_id") == flags.get(flag)
        ]
        finding["rank_badges"] = badges
    counts = _stage_counts(findings)
    human_brief = _human_pattern_brief(context, workflow, findings)
    paper_ready = counts["paper_ready"]
    artifact.update(
        {
            "status": "pattern_intelligence_visible" if findings else "pattern_intelligence_empty",
            "summary": (
                f"Qadam has {len(findings)} documented research findings, {counts['validated']} validated edges, "
                f"and {paper_ready} paper-ready candidates. These are pattern-recognition findings, not orders."
            ),
            "stage_counts": counts,
            "finding_count": len(findings),
            "validated_edge_count": counts["validated"],
            "paper_ready_count": paper_ready,
            "rank_flags": flags,
            "findings": findings,
            "human_brief": human_brief,
            "evidence_quality_summary": {
                "status": context.get("evidence_quality", {}).get("status"),
                "evidence_record_count": context.get("evidence_quality", {}).get("evidence_record_count", 0),
                "paper_review_candidate_count": context.get("evidence_quality", {}).get("paper_review_candidate_count", 0),
                "held_for_evidence_count": context.get("evidence_quality", {}).get("held_for_evidence_count", 0),
                "historical_complete_forward_window_ratio": context.get("evidence_quality", {}).get("historical_memory", {}).get("complete_forward_window_ratio"),
                "source_freshness_ratio": context.get("evidence_quality", {}).get("source_reliability", {}).get("freshness_ratio"),
                "akber_missing_context_count": context.get("evidence_quality", {}).get("akber_missing_context_count"),
                "most_important_missing_piece": context.get("evidence_quality", {}).get("most_important_missing_piece"),
            },
            "technical_diagnostics": {
                "linear_pattern_count": pattern_lab.get("linear_pattern_count", 0),
                "nonlinear_pattern_count": pattern_lab.get("nonlinear_pattern_count", 0),
                "quantum_review_count": pattern_lab.get("quantum_review_count", 0),
                "linear_rows": _safe_list(pattern_lab.get("linear_rows"))[:12],
                "nonlinear_rows": _safe_list(pattern_lab.get("nonlinear_rows"))[:12],
                "quantum_rows": _safe_list(pattern_lab.get("quantum_rows"))[:12],
            },
            "plain_english_terms": {
                "paper_trade_review": "Qadam is allowed to ask the guarded paper-trading route to review the idea, but it still cannot bypass risk checks.",
                "nonlinear_quantum_review": "The Head of Quant checks whether a combination of signals matters together, not just one at a time.",
                "six_stage_trade_quality_checklist": "Akber's filter checks context, catalyst, confirmation, risk, execution route, and postmortem learning.",
                "persistence": "The pattern must keep appearing over real elapsed time before Qadam treats it as stronger evidence.",
            },
            "boundary": "Pattern intelligence is dashboard visibility only. It cannot create Telegram commands, trade candidates, paper orders, broker writes, proof credit, or live-capital authority.",
            "paper_order_allowed": False,
            "paper_order_created_count": 0,
            "trade_candidate_created": False,
            "qualified_setup_created": False,
            "broker_write_allowed": False,
            "broker_write_count": 0,
            "proof_credit_allowed": False,
            "live_capital_enabled": False,
            "artifact_refs": [
                _artifact_ref(PATTERN_INTELLIGENCE_ARTIFACT),
                _artifact_ref(PATTERN_LAB_ARTIFACT),
                _artifact_ref(PATTERN_TO_PAPER_WORKFLOW_ARTIFACT),
                _artifact_ref(EDGE_PATTERN_LEDGER_ARTIFACT),
                _artifact_ref(DAILY_TELEGRAM_LEARNING_BRIEF_ARTIFACT),
            ],
        }
    )
    return artifact


def build_learning_ledger(context: dict[str, Any], generated_at: str) -> dict[str, Any]:
    artifact = _section_base("qsase_dashboard_learning_ledger", generated_at)
    rows = [
        {
            "row_type": "learning_decision_record",
            "attribution_record_id": row.get("attribution_record_id"),
            "evidence_class": row.get("evidence_class"),
            "state": row.get("status"),
            "outcome": row.get("dashboard_decision_record", {}).get("outcome"),
            "cause": row.get("dashboard_decision_record", {}).get("cause"),
            "attribution": row.get("dashboard_decision_record", {}).get("attribution"),
            "proposal": row.get("dashboard_decision_record", {}).get("proposal"),
            "applied": False,
            "artifact_refs": [_artifact_ref(LEARNING_LEDGER_RECORDS_ARTIFACT, str(row.get("attribution_record_id")))],
        }
        for row in context.get("learning_records", [])[:30]
    ]
    ledger = context.get("learning_ledger", {})
    artifact.update(
        {
            "status": "learning_ledger_visible" if rows else "learning_ledger_explicitly_empty",
            "row_count": len(rows),
            "rows": rows,
            "attribution_record_count": ledger.get("attribution_record_count"),
            "active_proposal_count": ledger.get("active_proposal_count"),
            "applied_update_count": ledger.get("applied_update_count"),
            "artifact_refs": [_artifact_ref(COMPONENT_ATTRIBUTION_LEDGER_ARTIFACT), _artifact_ref(LEARNING_LEDGER_RECORDS_ARTIFACT)],
        }
    )
    return artifact


def build_repair_queue(context: dict[str, Any], generated_at: str) -> dict[str, Any]:
    artifact = _section_base("qsase_dashboard_repair_queue", generated_at)
    rows = []
    for item in _safe_list(context.get("self_model", {}).get("degraded_components")):
        rows.append(
            {
                "repair_queue_id": _hash_id([item.get("component"), item.get("reason")], "qsase-repair"),
                "source": "qsase_self_model",
                "component": item.get("component"),
                "state": "repair_or_review_needed",
                "reason": item.get("reason"),
                "severity": item.get("severity"),
                "next_allowed_action": "repair runtime artifact or source state, then rerun QSASE checks",
                "applied_strategy_change": False,
                "artifact_refs": [_artifact_ref(SELF_MODEL_ARTIFACT, "degraded_components")],
            }
        )
    approval_queue = context.get("learning_approval_queue", {})
    for item in _safe_list(approval_queue.get("queue_items"))[:20]:
        rows.append(
            {
                "repair_queue_id": item.get("approval_queue_id"),
                "source": "learning_approval_queue",
                "component": item.get("proposal_surface"),
                "state": item.get("review_state"),
                "reason": item.get("proposal_type"),
                "severity": "review",
                "next_allowed_action": "human or governance review required before any change",
                "applied_strategy_change": False,
                "artifact_refs": [_artifact_ref(LEARNING_APPROVAL_QUEUE_ARTIFACT, str(item.get("approval_queue_id")))],
            }
        )
    self_healing_queue = context.get("qadam_self_healing_repair_queue", {})
    for item in _safe_list(self_healing_queue.get("entries"))[:20]:
        rows.append(
            {
                "repair_queue_id": item.get("repair_queue_id"),
                "source": "qadam_self_healing",
                "component": item.get("defect_type"),
                "state": item.get("state", "repair_requested"),
                "reason": item.get("summary"),
                "severity": item.get("severity", "review"),
                "next_allowed_action": "safe refresh verification or explicit development workflow only",
                "applied_strategy_change": False,
                "artifact_refs": [_artifact_ref(QADAM_SELF_HEALING_REPAIR_QUEUE_ARTIFACT, str(item.get("repair_queue_id")))],
            }
        )
    artifact.update(
        {
            "status": "repair_queue_visible" if rows else "repair_queue_explicitly_empty",
            "repair_queue_count": len(rows),
            "rows": rows,
            "self_healing_repair_queue_count": self_healing_queue.get("repair_queue_count", 0),
            "artifact_refs": [
                _artifact_ref(SELF_MODEL_ARTIFACT),
                _artifact_ref(LEARNING_APPROVAL_QUEUE_ARTIFACT),
                _artifact_ref(QADAM_SELF_HEALING_REPAIR_QUEUE_ARTIFACT),
            ],
        }
    )
    return artifact


def build_next_generation_backtest_state(context: dict[str, Any], generated_at: str) -> dict[str, Any]:
    artifact = _section_base("qadam_next_generation_backtest_state", generated_at)
    lock = context.get("next_generation_research_lock", {})
    dashboard_summary = context.get("next_generation_backtest_dashboard", {})
    phase1_summary = context.get("whole_universe_backfill_backtest_dashboard", {})
    evidence_contracts = context.get("evidence_contracts_dashboard", {})
    world_model = context.get("world_model_dashboard", {})
    pattern_engine_v2 = context.get("pattern_engine_v2_dashboard", {})
    strategy_evidence_map = context.get("strategy_evidence_map_dashboard", {})
    strategy_foundry_v2 = context.get("strategy_foundry_v2_dashboard", {})
    akber_filter_v2 = context.get("akber_filter_v2_dashboard", {})
    shadow_simulator_v2 = context.get("shadow_simulator_v2_dashboard", {})
    router_v2 = context.get("router_v2_dashboard", {})
    paper_lifecycle_v2 = context.get("paper_lifecycle_v2_dashboard", {})
    learning_attribution_v2 = context.get("learning_attribution_v2_dashboard", {})
    dashboard_vnext = context.get("dashboard_vnext_dashboard", {})
    telegram_vnext = context.get("telegram_vnext_dashboard", {})
    lock_active = (
        lock.get("lock_type") == "qadam_next_generation_whole_universe_backfill_backtest"
        and lock.get("status") == "active"
        and lock.get("paperops_watch_only_mode") is True
    )
    state = phase1_summary.get("backtest_running_state") or dashboard_summary.get("backtest_running_state") or (
        "backtest_research_lock_active" if lock_active else "backtest_research_lock_inactive"
    )
    artifact.update(
        {
            "status": state,
            "long_backtest_lock_active": lock_active,
            "paperops_watch_only_mode": lock.get("paperops_watch_only_mode") is True,
            "phase_1_backfill_started": lock.get("phase_1_backfill_started") is True,
            "phase_1_baseline_status": phase1_summary.get("status"),
            "complete_forward_window_count": phase1_summary.get("complete_forward_window_count"),
            "missing_forward_window_count": phase1_summary.get("missing_forward_window_count"),
            "baseline_result_count": phase1_summary.get("baseline_result_count"),
            "baseline_rejection_count": phase1_summary.get("baseline_rejection_count"),
            "akber_calibration_state": phase1_summary.get("akber_calibration_state"),
            "akber_calibrated_strategy_count": phase1_summary.get("akber_calibrated_strategy_count"),
            "shadow_router_state": phase1_summary.get("shadow_router_state"),
            "shadow_router_paper_review_candidate_count": phase1_summary.get("shadow_router_paper_review_candidate_count"),
            "evidence_contracts_state": evidence_contracts.get("status"),
            "evidence_contract_count": evidence_contracts.get("total_contract_count"),
            "missing_typed_evidence_count": evidence_contracts.get("missing_evidence_count"),
            "contracts_with_missing_evidence_count": evidence_contracts.get("contracts_with_missing_evidence_count"),
            "downstream_reader_state": evidence_contracts.get("downstream_reader_state"),
            "world_model_state": world_model.get("status"),
            "world_model_hypothesis_count": world_model.get("hypothesis_count"),
            "world_model_research_question_count": world_model.get("research_question_count"),
            "world_model_mapped_market_count": world_model.get("mapped_market_count"),
            "world_model_trade_candidate_creation_allowed": world_model.get("trade_candidate_creation_allowed"),
            "pattern_engine_v2_state": pattern_engine_v2.get("status"),
            "pattern_engine_v2_pattern_count": pattern_engine_v2.get("pattern_count"),
            "pattern_engine_v2_ranked_pattern_count": pattern_engine_v2.get("ranked_pattern_count"),
            "pattern_engine_v2_held_for_more_evidence_count": pattern_engine_v2.get("held_for_more_evidence_count"),
            "pattern_engine_v2_rejected_pattern_count": pattern_engine_v2.get("rejected_pattern_count"),
            "pattern_engine_v2_research_only": pattern_engine_v2.get("research_only"),
            "pattern_engine_v2_trade_candidate_creation_allowed": pattern_engine_v2.get("trade_candidate_creation_allowed"),
            "strategy_evidence_map_state": strategy_evidence_map.get("status"),
            "strategy_evidence_map_strategy_count": strategy_evidence_map.get("strategy_count"),
            "strategy_evidence_map_evidence_backed_strategy_count": strategy_evidence_map.get("evidence_backed_strategy_count"),
            "strategy_evidence_map_under_evidenced_strategy_count": strategy_evidence_map.get("under_evidenced_strategy_count"),
            "strategy_evidence_map_research_only": strategy_evidence_map.get("research_only"),
            "strategy_evidence_map_strategy_hypothesis_creation_allowed": strategy_evidence_map.get("strategy_hypothesis_creation_allowed"),
            "strategy_evidence_map_trade_candidate_creation_allowed": strategy_evidence_map.get("trade_candidate_creation_allowed"),
            "strategy_foundry_v2_state": strategy_foundry_v2.get("status"),
            "strategy_foundry_v2_hypothesis_count": strategy_foundry_v2.get("strategy_hypothesis_count"),
            "strategy_foundry_v2_accepted_for_akber_input_builder_count": strategy_foundry_v2.get("accepted_for_akber_input_builder_count"),
            "strategy_foundry_v2_rejected_before_akber_count": strategy_foundry_v2.get("rejected_before_akber_count"),
            "strategy_foundry_v2_weak_pattern_rejection_count": strategy_foundry_v2.get("weak_pattern_rejection_count"),
            "strategy_foundry_v2_research_only": strategy_foundry_v2.get("research_only"),
            "strategy_foundry_v2_akber_filter_run": strategy_foundry_v2.get("akber_filter_run"),
            "strategy_foundry_v2_trade_candidate_creation_allowed": strategy_foundry_v2.get("trade_candidate_creation_allowed"),
            "akber_filter_v2_state": akber_filter_v2.get("status"),
            "akber_filter_v2_input_count": akber_filter_v2.get("akber_input_count"),
            "akber_filter_v2_result_count": akber_filter_v2.get("akber_result_count"),
            "akber_filter_v2_pass_count": akber_filter_v2.get("pass_count"),
            "akber_filter_v2_hold_count": akber_filter_v2.get("hold_count"),
            "akber_filter_v2_veto_count": akber_filter_v2.get("veto_count"),
            "akber_filter_v2_router_eligible_count": akber_filter_v2.get("router_eligible_count"),
            "akber_filter_v2_router_eligible_with_missing_context_count": akber_filter_v2.get("router_eligible_with_missing_context_count"),
            "akber_filter_v2_no_router_eligible_setup_has_missing_context": akber_filter_v2.get("no_router_eligible_setup_has_missing_akber_context"),
            "akber_filter_v2_pass_is_execution_approval": akber_filter_v2.get("akber_filter_pass_is_execution_approval"),
            "akber_filter_v2_execution_approval_created": akber_filter_v2.get("execution_approval_created"),
            "shadow_simulator_v2_state": shadow_simulator_v2.get("status"),
            "shadow_simulator_v2_hypothesis_count": shadow_simulator_v2.get("hypothesis_count"),
            "shadow_simulator_v2_hypothesis_with_shadow_evidence_count": shadow_simulator_v2.get("hypothesis_with_shadow_evidence_count"),
            "shadow_simulator_v2_missing_shadow_evidence_count": shadow_simulator_v2.get("missing_shadow_evidence_count"),
            "shadow_simulator_v2_historical_shadow_replay_count": shadow_simulator_v2.get("historical_shadow_replay_count"),
            "shadow_simulator_v2_forward_tracking_count": shadow_simulator_v2.get("forward_tracking_count"),
            "shadow_simulator_v2_counterfactual_no_order_count": shadow_simulator_v2.get("counterfactual_no_order_count"),
            "shadow_simulator_v2_alternate_threshold_outcome_count": shadow_simulator_v2.get("alternate_threshold_outcome_count"),
            "shadow_simulator_v2_missed_opportunity_count": shadow_simulator_v2.get("missed_opportunity_count"),
            "shadow_simulator_v2_every_hypothesis_has_shadow_evidence": shadow_simulator_v2.get("every_hypothesis_has_shadow_evidence"),
            "shadow_simulator_v2_router_confidence_increase_without_shadow_evidence_count": shadow_simulator_v2.get("router_confidence_increase_without_shadow_evidence_count"),
            "shadow_simulator_v2_router_confidence_increase_created": shadow_simulator_v2.get("router_confidence_increase_created"),
            "shadow_simulator_v2_shadow_success_cannot_create_paper_order": shadow_simulator_v2.get("shadow_success_cannot_create_paper_order"),
            "shadow_simulator_v2_shadow_success_cannot_create_proof_credit": shadow_simulator_v2.get("shadow_success_cannot_create_proof_credit"),
            "router_v2_state": router_v2.get("status"),
            "router_v2_setup_count": router_v2.get("setup_count"),
            "router_v2_decision_count": router_v2.get("decision_count"),
            "router_v2_all_setups_have_exactly_one_final_state": router_v2.get("all_setups_have_exactly_one_final_state"),
            "router_v2_paper_review_candidate_count": router_v2.get("paper_review_candidate_count"),
            "router_v2_clean_paper_review_candidate_count": router_v2.get("clean_paper_review_candidate_count"),
            "router_v2_handoff_record_count": router_v2.get("handoff_record_count"),
            "router_v2_rejected_handoff_count": router_v2.get("rejected_handoff_count"),
            "router_v2_only_clean_paper_review_candidates_reach_paperops": router_v2.get("only_clean_paper_review_candidates_reach_paperops"),
            "router_v2_duplicate_idempotency_count": router_v2.get("duplicate_idempotency_count"),
            "router_v2_duplicate_exposure_count": router_v2.get("duplicate_exposure_count"),
            "router_v2_why_not_trading_now_reason": router_v2.get("why_not_trading_now_reason"),
            "router_v2_why_not_trading_now_plain_english": router_v2.get("why_not_trading_now_plain_english"),
            "router_v2_paper_order_created_count": router_v2.get("paper_order_created_count"),
            "router_v2_broker_write_count": router_v2.get("broker_write_count"),
            "router_v2_proof_credit_allowed": router_v2.get("proof_credit_allowed"),
            "paper_lifecycle_v2_state": paper_lifecycle_v2.get("status"),
            "paper_lifecycle_v2_order_count": paper_lifecycle_v2.get("paper_order_mirror_count"),
            "paper_lifecycle_v2_open_position_count": paper_lifecycle_v2.get("open_position_mirror_count"),
            "paper_lifecycle_v2_closed_trade_count": paper_lifecycle_v2.get("closed_paper_trade_count"),
            "paper_lifecycle_v2_lifecycle_record_count": paper_lifecycle_v2.get("lifecycle_record_count"),
            "paper_lifecycle_v2_ambiguous_lifecycle_count": paper_lifecycle_v2.get("ambiguous_lifecycle_count"),
            "paper_lifecycle_v2_no_paper_order_ambiguous": paper_lifecycle_v2.get("no_paper_order_ambiguous"),
            "paper_lifecycle_v2_stale_accepted_order_count": paper_lifecycle_v2.get("stale_accepted_order_count"),
            "paper_lifecycle_v2_cancel_replace_needed_count": paper_lifecycle_v2.get("cancel_replace_needed_count"),
            "paper_lifecycle_v2_state_counts": paper_lifecycle_v2.get("state_counts"),
            "paper_lifecycle_v2_proof_boundary_state": paper_lifecycle_v2.get("proof_boundary_state"),
            "paper_lifecycle_v2_proof_eligible_count": paper_lifecycle_v2.get("proof_eligible_count"),
            "paper_lifecycle_v2_proof_rejected_count": paper_lifecycle_v2.get("proof_rejected_count"),
            "paper_lifecycle_v2_proof_credit_requires_real_closed_trade_with_complete_lineage": paper_lifecycle_v2.get("proof_credit_requires_real_closed_trade_with_complete_lineage"),
            "paper_lifecycle_v2_backtest_shadow_or_synthetic_proof_credit_count": paper_lifecycle_v2.get("backtest_shadow_or_synthetic_proof_credit_count"),
            "paper_lifecycle_v2_paper_proof_ledger_credit_allowed": paper_lifecycle_v2.get("paper_proof_ledger_credit_allowed"),
            "paper_lifecycle_v2_proof_credit_allowed": paper_lifecycle_v2.get("proof_credit_allowed"),
            "learning_attribution_v2_state": learning_attribution_v2.get("status"),
            "learning_attribution_v2_record_count": learning_attribution_v2.get("attribution_record_count"),
            "learning_attribution_v2_backtest_record_count": learning_attribution_v2.get("backtest_record_count"),
            "learning_attribution_v2_shadow_record_count": learning_attribution_v2.get("shadow_record_count"),
            "learning_attribution_v2_akber_record_count": learning_attribution_v2.get("akber_record_count"),
            "learning_attribution_v2_router_record_count": learning_attribution_v2.get("router_record_count"),
            "learning_attribution_v2_paperops_record_count": learning_attribution_v2.get("paperops_record_count"),
            "learning_attribution_v2_missed_opportunity_record_count": learning_attribution_v2.get("missed_opportunity_record_count"),
            "learning_attribution_v2_paper_trade_outcome_record_count": learning_attribution_v2.get("paper_trade_outcome_record_count"),
            "learning_attribution_v2_proof_rejected_record_count": learning_attribution_v2.get("proof_rejected_record_count"),
            "learning_attribution_v2_hold_record_count": learning_attribution_v2.get("hold_record_count"),
            "learning_attribution_v2_veto_record_count": learning_attribution_v2.get("veto_record_count"),
            "learning_attribution_v2_proposal_count": learning_attribution_v2.get("proposal_count"),
            "learning_attribution_v2_proposal_applied_count": learning_attribution_v2.get("proposal_applied_count"),
            "learning_attribution_v2_authority_mutation_count": learning_attribution_v2.get("authority_mutation_count"),
            "learning_attribution_v2_applied_update_count": learning_attribution_v2.get("applied_update_count"),
            "learning_attribution_v2_learning_outputs_are_proposals_only": learning_attribution_v2.get("learning_outputs_are_proposals_only"),
            "dashboard_vnext_state": dashboard_vnext.get("status"),
            "dashboard_vnext_protected_section_count": dashboard_vnext.get("protected_section_count"),
            "dashboard_vnext_protected_sections_not_reordered": dashboard_vnext.get("protected_sections_not_reordered"),
            "dashboard_vnext_protected_sections_not_renamed": dashboard_vnext.get("protected_sections_not_renamed"),
            "dashboard_vnext_protected_sections_not_removed": dashboard_vnext.get("protected_sections_not_removed"),
            "dashboard_vnext_protected_sections_not_structurally_overhauled": dashboard_vnext.get("protected_sections_not_structurally_overhauled"),
            "dashboard_vnext_enrichment_only_inside_protected_sections": dashboard_vnext.get("enrichment_only_inside_protected_sections"),
            "dashboard_vnext_all_portfolio_values_agree": dashboard_vnext.get("all_portfolio_values_agree"),
            "dashboard_vnext_downstream_section_count": dashboard_vnext.get("downstream_section_count"),
            "dashboard_vnext_strategy_card_count": dashboard_vnext.get("strategy_card_count"),
            "dashboard_vnext_pattern_card_count": dashboard_vnext.get("pattern_card_count"),
            "dashboard_vnext_router_paperops_single_answer": dashboard_vnext.get("router_paperops_single_answer"),
            "telegram_vnext_state": telegram_vnext.get("status"),
            "telegram_vnext_message_candidate_count": telegram_vnext.get("message_candidate_count"),
            "telegram_vnext_message_ready_count": telegram_vnext.get("message_ready_count"),
            "telegram_vnext_message_rejected_duplicate_count": telegram_vnext.get("message_rejected_duplicate_count"),
            "telegram_vnext_message_rejected_quality_count": telegram_vnext.get("message_rejected_quality_count"),
            "telegram_vnext_message_rejected_unsafe_count": telegram_vnext.get("message_rejected_unsafe_count"),
            "telegram_vnext_quality_pass_count": telegram_vnext.get("quality_pass_count"),
            "telegram_vnext_latest_message_preview": telegram_vnext.get("latest_message_preview"),
            "telegram_vnext_live_send_allowed": telegram_vnext.get("telegram_live_send_allowed"),
            "telegram_vnext_command_path_enabled": telegram_vnext.get("telegram_command_path_enabled"),
            "telegram_vnext_trade_candidate_created": telegram_vnext.get("trade_candidate_created"),
            "telegram_vnext_risk_approval_created": telegram_vnext.get("risk_approval_created"),
            "telegram_vnext_execution_approval_created": telegram_vnext.get("execution_approval_created"),
            "telegram_vnext_paper_order_created_count": telegram_vnext.get("paper_order_created_count"),
            "telegram_vnext_broker_write_count": telegram_vnext.get("broker_write_count"),
            "telegram_vnext_proof_credit_allowed": telegram_vnext.get("proof_credit_allowed"),
            "telegram_vnext_live_capital_enabled": telegram_vnext.get("live_capital_enabled"),
            "paper_order_created_count": phase1_summary.get("paper_order_created_count"),
            "broker_write_count": phase1_summary.get("broker_write_count"),
            "live_capital_enabled": phase1_summary.get("live_capital_enabled"),
            "proof_credit_allowed": phase1_summary.get("proof_credit_allowed"),
            "paper_growth_trial_calendar_advanced": phase1_summary.get("paper_growth_trial_calendar_advanced"),
            "paperops_guard": (
                "PaperOps is watch-only while this lock is active."
                if lock_active
                else "No long backtest research lock is active."
            ),
            "dashboard_message": phase1_summary.get("message")
            or dashboard_summary.get("message")
            or (
                "Qadam can show existing state only while the long research lock is active."
                if lock_active
                else "No whole-universe historical backfill/backtest is running."
            ),
            "authority": next_generation_lock_authority_flags(),
            "artifact_refs": [
                _artifact_ref(NEXT_GENERATION_RESEARCH_LOCK_ARTIFACT),
                _artifact_ref(NEXT_GENERATION_BACKTEST_DASHBOARD_ARTIFACT),
                _artifact_ref(WHOLE_UNIVERSE_BACKFILL_BACKTEST_DASHBOARD_ARTIFACT),
                _artifact_ref(EVIDENCE_CONTRACTS_DASHBOARD_ARTIFACT),
                _artifact_ref(WORLD_MODEL_DASHBOARD_ARTIFACT),
                _artifact_ref(PATTERN_ENGINE_V2_DASHBOARD_ARTIFACT),
                _artifact_ref(STRATEGY_EVIDENCE_MAP_DASHBOARD_ARTIFACT),
                _artifact_ref(STRATEGY_FOUNDRY_V2_DASHBOARD_ARTIFACT),
                _artifact_ref(AKBER_FILTER_V2_DASHBOARD_ARTIFACT),
                _artifact_ref(SHADOW_SIMULATOR_V2_DASHBOARD_ARTIFACT),
                _artifact_ref(ROUTER_V2_DASHBOARD_ARTIFACT),
                _artifact_ref(PAPER_LIFECYCLE_V2_DASHBOARD_ARTIFACT),
                _artifact_ref(LEARNING_ATTRIBUTION_V2_DASHBOARD_ARTIFACT),
                _artifact_ref(DASHBOARD_VNEXT_DASHBOARD_ARTIFACT),
                _artifact_ref(TELEGRAM_VNEXT_DASHBOARD_ARTIFACT),
                _artifact_ref(TELEGRAM_VNEXT_COMMUNICATIONS_MIRROR_ARTIFACT),
            ],
        }
    )
    return artifact


def build_system_map(sections: dict[str, dict[str, Any]], generated_at: str) -> dict[str, Any]:
    artifact = _section_base("qsase_dashboard_system_map", generated_at)
    order = [
        "qsase_snapshot",
        "portfolio_value",
        "current_portfolio",
        "trading_history",
        "source_network",
        "strategy_universe",
        "pattern_lab",
        "evidence_quality",
        "trade_intents",
        "pattern_to_paper_workflow",
        "router_paperops_state",
        "learning_ledger",
        "repair_queue",
        "freshness",
    ]
    nodes = [
        {
            "node_id": key,
            "label": key.replace("_", " ").title(),
            "state": sections.get(key, {}).get("status", "visible"),
            "artifact_refs": sections.get(key, {}).get("artifact_refs", []),
            "overview_detail_level": "summary_only",
        }
        for key in order
    ]
    artifact.update(
        {
            "status": "system_map_visible",
            "node_count": len(nodes),
            "nodes": nodes,
            "edges": [
                {"from": order[index], "to": order[index + 1], "relationship": "dashboard_flow"}
                for index in range(len(order) - 1)
            ],
            "overview_detail_policy": {
                "detailed_ledgers_in_overview": False,
                "overview_uses_decision_records": True,
                "default_dashboard_keeps_core_sections_visible": True,
            },
            "artifact_refs": [artifact.get("artifact_refs") for artifact in sections.values() if artifact.get("artifact_refs")],
        }
    )
    return artifact


def build_decision_records(sections: dict[str, dict[str, Any]], context: dict[str, Any]) -> dict[str, Any]:
    generated_at = sections["qsase_snapshot"]["generated_at"]
    records = [
        _decision_record(
            module="qsase_snapshot",
            state=sections["qsase_snapshot"]["status"],
            headline="QSASE snapshot labels the current state.",
            reason=sections["qsase_snapshot"]["reason"],
            blocker=sections["qsase_snapshot"]["blocker"],
            next_allowed_action=sections["qsase_snapshot"]["next_allowed_action"],
            artifact_refs=[_artifact_ref(STATUS_ARTIFACT), _artifact_ref(SELF_MODEL_ARTIFACT)],
            evidence=["self-model", "router", "PaperOps", "learning ledger"],
        ),
        _decision_record(
            module="portfolio_value",
            state=sections["portfolio_value"]["status"],
            headline="Portfolio line graph is available.",
            reason="Read-only Alpaca paper mirror provides portfolio value points."
            if sections["portfolio_value"]["line_graph_available"]
            else sections["portfolio_value"]["unavailable_reason"],
            blocker="none" if sections["portfolio_value"]["line_graph_available"] else "portfolio_history_missing",
            next_allowed_action="render line graph from qsase_dashboard_portfolio_value_series",
            artifact_refs=sections["portfolio_value"]["artifact_refs"],
        ),
        _decision_record(
            module="source_network",
            state=sections["source_network"]["status"],
            headline="Source network exposes categories and sources.",
            reason=f"{sections['source_network']['category_row_count']} categories and {sections['source_network']['source_row_count']} source rows are visible.",
            blocker="credential_gated_sources_labeled"
            if any(row.get("credential_gated_count") for row in sections["source_network"].get("category_rows", []))
            else "none",
            next_allowed_action="render source categories, individual sources, and trading universe rows",
            artifact_refs=sections["source_network"]["artifact_refs"],
        ),
        _decision_record(
            module="strategy_universe",
            state=sections["strategy_universe"]["status"],
            headline="Strategy Universe separates all strategies from active reviews.",
            reason=f"{sections['strategy_universe']['all_strategy_count']} strategy families, {sections['strategy_universe']['currently_in_play_count']} currently in play.",
            blocker="no_paper_review_candidate" if sections["strategy_universe"]["currently_in_play_count"] else "none",
            next_allowed_action="show all strategy rows and current in-play rows separately",
            artifact_refs=sections["strategy_universe"]["artifact_refs"],
        ),
        _decision_record(
            module="pattern_lab",
            state=sections["pattern_lab"]["status"],
            headline="Pattern Lab separates linear and nonlinear evidence.",
            reason=f"{sections['pattern_lab']['linear_pattern_count']} linear rows and {sections['pattern_lab']['nonlinear_pattern_count']} nonlinear rows are visible.",
            blocker="quantum_review_is_research_only",
            next_allowed_action="render linear, nonlinear, and quantum review rows without trade authority",
            artifact_refs=sections["pattern_lab"]["artifact_refs"],
        ),
        _decision_record(
            module="evidence_quality",
            state=sections["evidence_quality"]["status"],
            headline="Evidence Quality decides whether patterns are tradeable now.",
            reason=sections["evidence_quality"].get("summary", "Evidence quality has not exported a summary."),
            blocker=_first_text(
                sections["evidence_quality"].get("most_important_missing_piece"),
                default="evidence_quality_not_ready",
            ),
            next_allowed_action="collect missing evidence until Akber and Router can promote a setup",
            artifact_refs=sections["evidence_quality"].get("artifact_refs", [_artifact_ref(EVIDENCE_QUALITY_ARTIFACT)]),
        ),
        _decision_record(
            module="trade_intents",
            state=sections["trade_intents"]["status"],
            headline="Trade intents are visible as review records.",
            reason=f"{sections['trade_intents']['intent_count']} router records are shown as intents, not orders.",
            blocker="router_or_akber_safety_boundary",
            next_allowed_action="show intent rows with source quorum, Akber, quantum, and route state",
            artifact_refs=sections["trade_intents"]["artifact_refs"],
        ),
        _decision_record(
            module="pattern_to_paper_workflow",
            state=sections["pattern_to_paper_workflow"]["status"],
            headline="Pattern workflow documents how evidence can reach paper review.",
            reason=f"{sections['pattern_to_paper_workflow']['recognized_pattern_count']} recognized patterns, {sections['pattern_to_paper_workflow']['paperops_handoff_candidate_count']} guarded handoff candidates.",
            blocker=_first_text(sections["pattern_to_paper_workflow"].get("paperops_top_blocking_gate"), default="pattern_validation_pending"),
            next_allowed_action="wait for validated edge evidence before guarded PaperOps handoff",
            artifact_refs=sections["pattern_to_paper_workflow"]["artifact_refs"],
        ),
        _decision_record(
            module="router_paperops",
            state=context.get("paperops_gate", {}).get("status", "not_recorded"),
            headline="PaperOps gate state is visible.",
            reason=_first_text(context.get("paperops_gate", {}).get("top_blocking_gate"), default="no paper handoff currently eligible"),
            blocker=_first_text(context.get("paperops_gate", {}).get("top_blocking_gate"), default="none"),
            next_allowed_action="wait for distinct paperable setup or rerun guarded PaperOps checks",
            artifact_refs=[_artifact_ref(ROUTER_ARTIFACT), _artifact_ref(PAPEROPS_GATE_ARTIFACT)],
        ),
        _decision_record(
            module="learning_ledger",
            state=sections["learning_ledger"]["status"],
            headline="Learning ledger is shown as attribution records.",
            reason=f"{sections['learning_ledger']['row_count']} learning rows are visible; applied updates remain zero.",
            blocker="approval_required_for_any_change",
            next_allowed_action="route proposals to review without mutating strategy, source, model, or filter state",
            artifact_refs=sections["learning_ledger"]["artifact_refs"],
        ),
        _decision_record(
            module="repair_queue",
            state=sections["repair_queue"]["status"],
            headline="Repair queue separates defects from strategy discipline.",
            reason=f"{sections['repair_queue']['repair_queue_count']} repair or approval rows are visible.",
            blocker="repair_or_review_needed" if sections["repair_queue"]["repair_queue_count"] else "none",
            next_allowed_action="repair runtime/source gaps or review proposals before any change",
            artifact_refs=sections["repair_queue"]["artifact_refs"],
        ),
    ]
    return {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "qsase_dashboard_decision_records",
        "generated_at": generated_at,
        "status": "decision_records_visible",
        "public_safe": True,
        "command_disabled": True,
        "read_only": True,
        "record_count": len(records),
        "records": records,
        "authority": _dashboard_authority(),
    }


def build_freshness_section(context: dict[str, Any], generated_at: str) -> dict[str, Any]:
    artifact = _section_base("qsase_dashboard_freshness", generated_at)
    rows = []
    for name, snapshot in sorted(context.get("input_snapshots", {}).items()):
        rows.append(
            {
                "input": name,
                "artifact": snapshot.get("artifact"),
                "exists": snapshot.get("exists"),
                "freshness_status": snapshot.get("freshness_status"),
                "staleness_label": snapshot.get("staleness_label"),
                "age_seconds": snapshot.get("age_seconds"),
                "generated_at": snapshot.get("generated_at"),
                "next_allowed_action": "refresh source artifact before presenting as current"
                if snapshot.get("freshness_status") == "stale_labeled"
                else "render with recorded timestamp",
            }
        )
    stale_count = sum(1 for row in rows if row["freshness_status"] == "stale_labeled")
    artifact.update(
        {
            "status": "freshness_visible_with_stale_labels" if stale_count else "freshness_visible",
            "freshness_row_count": len(rows),
            "stale_labeled_count": stale_count,
            "rows": rows,
            "artifact_refs": [_artifact_ref(STATUS_ARTIFACT)],
        }
    )
    return artifact


def _build_snapshot_section(context: dict[str, Any], generated_at: str) -> dict[str, Any]:
    self_model = context.get("self_model", {})
    router = context.get("router", {})
    paperops_gate = context.get("paperops_gate", {})
    learning = context.get("learning_ledger", {})
    reason = _first_text(
        router.get("why_not_trading_now", {}).get("reason"),
        self_model.get("why_not_trading_now", {}).get("reason"),
        paperops_gate.get("top_blocking_gate"),
        default="qsase_state_recorded",
    )
    blocker = _first_text(paperops_gate.get("top_blocking_gate"), self_model.get("status"), default="none")
    section = _section_base("qsase_dashboard_snapshot", generated_at)
    section.update(
        {
            "status": "qsase_dashboard_snapshot_visible",
            "state": "review_only",
            "reason": reason,
            "blocker": blocker,
            "next_allowed_action": "render decision records and wait for a fresh distinct paperable setup",
            "self_model_status": self_model.get("status"),
            "router_status": router.get("status"),
            "paperops_gate_status": paperops_gate.get("status"),
            "learning_ledger_status": learning.get("status"),
            "artifact_refs": [
                _artifact_ref(SELF_MODEL_ARTIFACT),
                _artifact_ref(ROUTER_ARTIFACT),
                _artifact_ref(PAPEROPS_GATE_ARTIFACT),
                _artifact_ref(COMPONENT_ATTRIBUTION_LEDGER_ARTIFACT),
            ],
        }
    )
    return section


def _generic_phrase_hits(text: str) -> list[str]:
    lowered = text.lower()
    return [phrase for phrase in GENERIC_AI_PHRASES if phrase in lowered]


def run_dashboard_anti_slop_checks(payload: dict[str, Any]) -> dict[str, Any]:
    generated_at = payload["generated_at"]
    errors: list[str] = []
    warnings: list[str] = []
    decision_records = payload.get("decision_records", {}).get("records", [])
    headlines = [record.get("headline") for record in decision_records]
    duplicate_headlines = [headline for headline, count in Counter(headlines).items() if headline and count > 1]
    for headline in duplicate_headlines:
        errors.append(f"duplicate_headline:{headline}")
    for record in decision_records:
        record_id = record.get("decision_record_id")
        for field in REQUIRED_DECISION_RECORD_FIELDS:
            if field not in record or record.get(field) in (None, "", []):
                errors.append(f"decision_record_{record_id}_missing_{field}")
        for field in ("headline", "reason", "next_allowed_action", "blocker"):
            hits = _generic_phrase_hits(str(record.get(field) or ""))
            for hit in hits:
                errors.append(f"decision_record_{record_id}_generic_phrase_{hit}")
        if len(str(record.get("headline") or "")) > 120:
            errors.append(f"decision_record_{record_id}_headline_too_long")
        if len(str(record.get("reason") or "")) > 220:
            errors.append(f"decision_record_{record_id}_reason_too_long")
        if len(str(record.get("next_allowed_action") or "")) > 180:
            errors.append(f"decision_record_{record_id}_next_action_too_long")
        for field in ("applied_change", "paper_order_created", "proof_credit_allowed", "live_capital_enabled"):
            if record.get(field) is not False:
                errors.append(f"decision_record_{record_id}_{field}_must_be_false")
        for field in FALSE_AUTHORITY_FIELDS:
            if record.get("authority", {}).get(field) is not False:
                errors.append(f"decision_record_{record_id}_authority_{field}_must_be_false")
    trade_intents = payload.get("trade_intents", {})
    for row in trade_intents.get("rows", []):
        row_text = " ".join(str(row.get(key) or "") for key in ("row_type", "state"))
        if any(label == row_text for label in PROHIBITED_INTENT_LABELS):
            errors.append(f"trade_intent_{row.get('intent_id')}_invalid_label")
        for field in ("is_trade", "is_order", "is_approval", "is_qualified_setup", "paper_order_created"):
            if row.get(field) is not False:
                errors.append(f"trade_intent_{row.get('intent_id')}_{field}_must_be_false")
    overview_policy = payload.get("system_map", {}).get("overview_detail_policy", {})
    if overview_policy.get("detailed_ledgers_in_overview") is not False:
        errors.append("overview_contains_detailed_ledgers")
    freshness = payload.get("freshness", {})
    for row in freshness.get("rows", []):
        if row.get("freshness_status") == "stale_labeled" and not row.get("staleness_label"):
            errors.append(f"freshness_{row.get('input')}_stale_without_label")
        if row.get("freshness_status") == "missing":
            warnings.append(f"freshness_{row.get('input')}_missing")
    for section_name in (
        "portfolio_value",
        "current_portfolio",
        "trading_history",
        "source_network",
        "strategy_universe",
        "pattern_lab",
        "trade_intents",
        "pattern_to_paper_workflow",
        "learning_ledger",
        "repair_queue",
    ):
        section = payload.get(section_name, {})
        if section.get("read_only") is not True or section.get("command_disabled") is not True:
            errors.append(f"{section_name}_read_only_boundary_missing")
        for field in FALSE_AUTHORITY_FIELDS:
            if section.get("authority", {}).get(field) is not False:
                errors.append(f"{section_name}_authority_{field}_must_be_false")
    strategy_universe = payload.get("strategy_universe", {})
    strategy_rows = strategy_universe.get("all_strategy_rows", [])
    required_strategy_fields = (
        "plain_english_summary",
        "how_strategy_works",
        "why_this_can_create_an_edge",
        "example_scenario",
        "what_qadam_watches",
        "current_status_plain_english",
        "current_blocker_plain_english",
        "next_action_plain_english",
    )
    for row in strategy_rows:
        family_id = row.get("strategy_family_id") or "unknown_strategy"
        for field in required_strategy_fields:
            text = str(row.get(field) or "").strip()
            if len(text) < 40:
                errors.append(f"strategy_{family_id}_{field}_missing_plain_english")
            for hit in _generic_phrase_hits(text):
                errors.append(f"strategy_{family_id}_{field}_generic_phrase_{hit}")
            if any(raw in text for raw in ("currently_in_play", "blocked_or_rejected", "missing_typed")):
                errors.append(f"strategy_{family_id}_{field}_leaks_internal_state")
        if len(_safe_list(row.get("core_instruments_explained"))) < 2:
            errors.append(f"strategy_{family_id}_core_instrument_explanations_missing")
        if len(_safe_list(row.get("secondary_instruments_explained"))) < 2:
            errors.append(f"strategy_{family_id}_secondary_instrument_explanations_missing")
        for group_name in ("core_instruments_explained", "secondary_instruments_explained"):
            for instrument in _safe_list(row.get(group_name)):
                if not isinstance(instrument, dict):
                    errors.append(f"strategy_{family_id}_{group_name}_invalid")
                    continue
                for field in ("symbol", "role", "explanation"):
                    if not str(instrument.get(field) or "").strip():
                        errors.append(f"strategy_{family_id}_{group_name}_{field}_missing")
        loop = row.get("self_refinement_loop") if isinstance(row.get("self_refinement_loop"), dict) else {}
        for field in (
            "plain_english",
            "what_gets_tested",
            "what_backtesting_teaches",
            "what_can_change_over_time",
            "what_cannot_change_without_review",
        ):
            text = str(loop.get(field) or "").strip()
            if len(text) < 40:
                errors.append(f"strategy_{family_id}_self_refinement_{field}_missing")
        if "cannot grant trade authority" not in str(loop.get("what_cannot_change_without_review") or ""):
            errors.append(f"strategy_{family_id}_self_refinement_boundary_missing")
    return {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "qsase_dashboard_anti_slop_audit",
        "generated_at": generated_at,
        "status": "anti_slop_passed" if not errors else "anti_slop_failed",
        "public_safe": True,
        "command_disabled": True,
        "read_only": True,
        "error_count": len(errors),
        "warning_count": len(warnings),
        "errors": sorted(set(errors)),
        "warnings": sorted(set(warnings)),
        "checks": {
            "duplicate_headlines_rejected": True,
            "generic_ai_prose_rejected": True,
            "trade_intents_not_orders": True,
            "overview_detail_ledgers_excluded": True,
            "stale_state_labeled": True,
            "authority_drift_rejected": True,
        },
        "authority": _dashboard_authority(),
    }


def build_dashboard_view_model(settings: Settings | None = None) -> dict[str, Any]:
    context = _load_context(settings)
    generated_at = _iso(_now())
    context["dashboard_portfolio"] = build_dashboard_portfolio_contract(context, generated_at)
    sections: dict[str, dict[str, Any]] = {}
    sections["qsase_snapshot"] = _build_snapshot_section(context, generated_at)
    sections["portfolio_value"] = build_portfolio_value_series(context, generated_at)
    sections["current_portfolio"] = build_current_portfolio(context, generated_at)
    sections["trading_history"] = build_trading_history(context, generated_at)
    sections["source_network"] = build_source_network(context, generated_at)
    sections["strategy_universe"] = build_strategy_universe(context, generated_at)
    sections["pattern_lab"] = build_pattern_lab(context, generated_at)
    sections["evidence_quality"] = build_evidence_quality(context, generated_at)
    sections["trade_intents"] = build_trade_intents(context, generated_at)
    sections["pattern_to_paper_workflow"] = build_pattern_to_paper_workflow(context, generated_at)
    sections["pattern_intelligence"] = build_pattern_intelligence(
        context,
        generated_at,
        sections["pattern_lab"],
        sections["pattern_to_paper_workflow"],
    )
    sections["learning_ledger"] = build_learning_ledger(context, generated_at)
    sections["repair_queue"] = build_repair_queue(context, generated_at)
    sections["next_generation_backtest"] = build_next_generation_backtest_state(
        context,
        generated_at,
    )
    sections["freshness"] = build_freshness_section(context, generated_at)
    sections["router_paperops_state"] = {
        "status": context.get("paperops_gate", {}).get("status", "not_recorded"),
        "artifact_refs": [_artifact_ref(ROUTER_ARTIFACT), _artifact_ref(PAPEROPS_GATE_ARTIFACT)],
    }
    system_map = build_system_map(sections, generated_at)
    sections["system_map"] = system_map
    decision_records = build_decision_records(sections, context)
    payload = {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "qsase_dashboard_view_model",
        "phase_id": PHASE_ID,
        "phase_name": PHASE_NAME,
        "generated_at": generated_at,
        "status": "qsase_dashboard_visibility_ready",
        "public_safe": True,
        "command_disabled": True,
        "read_only": True,
        "paper_only": True,
        "proposal_first": True,
        "default_dashboard_sections_visible": True,
        "overview_detail_policy": system_map["overview_detail_policy"],
        "portfolio_value_line_graph_state": sections["portfolio_value"]["status"],
        "current_portfolio_state": sections["current_portfolio"]["status"],
        "trading_history_state": sections["trading_history"]["status"],
        "source_network_state": sections["source_network"]["status"],
        "strategy_universe_state": sections["strategy_universe"]["status"],
        "pattern_lab_state": sections["pattern_lab"]["status"],
        "evidence_quality_state": sections["evidence_quality"]["status"],
        "trade_intents_state": sections["trade_intents"]["status"],
        "pattern_to_paper_workflow_state": sections["pattern_to_paper_workflow"]["status"],
        "pattern_intelligence_state": sections["pattern_intelligence"]["status"],
        "learning_ledger_state": sections["learning_ledger"]["status"],
        "repair_queue_state": sections["repair_queue"]["status"],
        "layered_market_judgment_state": context.get(
            "layered_market_judgment", {}
        ).get("status"),
        "layered_market_judgment_activity_health": context.get(
            "layered_market_judgment", {}
        ).get("activity_health"),
        "layered_market_judgment_consequence_counts": context.get(
            "layered_market_judgment", {}
        ).get("consequence_counts", {}),
        "self_healing_state": context.get("qadam_self_healing_status", {}).get("status")
        or context.get("qadam_self_healing_dashboard", {}).get("status"),
        "self_healing_repair_queue_count": context.get("qadam_self_healing_repair_queue", {}).get("repair_queue_count", 0),
        "self_healing_provider_outage_count": context.get("qadam_self_healing_status", {}).get("provider_outage_classification", {}).get("provider_outage_count"),
        "self_healing_stale_or_missing_artifact_count": context.get("qadam_self_healing_status", {}).get("stale_artifact_recovery", {}).get("stale_or_missing_artifact_count"),
        "next_generation_backtest_state": sections["next_generation_backtest"]["status"],
        "evidence_contracts_state": sections["next_generation_backtest"].get("evidence_contracts_state"),
        "evidence_contract_count": sections["next_generation_backtest"].get("evidence_contract_count"),
        "missing_typed_evidence_count": sections["next_generation_backtest"].get("missing_typed_evidence_count"),
        "contracts_with_missing_evidence_count": sections["next_generation_backtest"].get("contracts_with_missing_evidence_count"),
        "evidence_contract_downstream_reader_state": sections["next_generation_backtest"].get("downstream_reader_state"),
        "world_model_state": sections["next_generation_backtest"].get("world_model_state"),
        "world_model_hypothesis_count": sections["next_generation_backtest"].get("world_model_hypothesis_count"),
        "world_model_research_question_count": sections["next_generation_backtest"].get("world_model_research_question_count"),
        "world_model_mapped_market_count": sections["next_generation_backtest"].get("world_model_mapped_market_count"),
        "world_model_trade_candidate_creation_allowed": sections["next_generation_backtest"].get("world_model_trade_candidate_creation_allowed"),
        "pattern_engine_v2_state": sections["next_generation_backtest"].get("pattern_engine_v2_state"),
        "pattern_engine_v2_pattern_count": sections["next_generation_backtest"].get("pattern_engine_v2_pattern_count"),
        "pattern_engine_v2_ranked_pattern_count": sections["next_generation_backtest"].get("pattern_engine_v2_ranked_pattern_count"),
        "pattern_engine_v2_held_for_more_evidence_count": sections["next_generation_backtest"].get("pattern_engine_v2_held_for_more_evidence_count"),
        "pattern_engine_v2_rejected_pattern_count": sections["next_generation_backtest"].get("pattern_engine_v2_rejected_pattern_count"),
        "pattern_engine_v2_research_only": sections["next_generation_backtest"].get("pattern_engine_v2_research_only"),
        "pattern_engine_v2_trade_candidate_creation_allowed": sections["next_generation_backtest"].get("pattern_engine_v2_trade_candidate_creation_allowed"),
        "strategy_evidence_map_state": sections["next_generation_backtest"].get("strategy_evidence_map_state"),
        "strategy_evidence_map_strategy_count": sections["next_generation_backtest"].get("strategy_evidence_map_strategy_count"),
        "strategy_evidence_map_evidence_backed_strategy_count": sections["next_generation_backtest"].get("strategy_evidence_map_evidence_backed_strategy_count"),
        "strategy_evidence_map_under_evidenced_strategy_count": sections["next_generation_backtest"].get("strategy_evidence_map_under_evidenced_strategy_count"),
        "strategy_evidence_map_research_only": sections["next_generation_backtest"].get("strategy_evidence_map_research_only"),
        "strategy_evidence_map_strategy_hypothesis_creation_allowed": sections["next_generation_backtest"].get("strategy_evidence_map_strategy_hypothesis_creation_allowed"),
        "strategy_evidence_map_trade_candidate_creation_allowed": sections["next_generation_backtest"].get("strategy_evidence_map_trade_candidate_creation_allowed"),
        "strategy_foundry_v2_state": sections["next_generation_backtest"].get("strategy_foundry_v2_state"),
        "strategy_foundry_v2_hypothesis_count": sections["next_generation_backtest"].get("strategy_foundry_v2_hypothesis_count"),
        "strategy_foundry_v2_accepted_for_akber_input_builder_count": sections["next_generation_backtest"].get("strategy_foundry_v2_accepted_for_akber_input_builder_count"),
        "strategy_foundry_v2_rejected_before_akber_count": sections["next_generation_backtest"].get("strategy_foundry_v2_rejected_before_akber_count"),
        "strategy_foundry_v2_weak_pattern_rejection_count": sections["next_generation_backtest"].get("strategy_foundry_v2_weak_pattern_rejection_count"),
        "strategy_foundry_v2_research_only": sections["next_generation_backtest"].get("strategy_foundry_v2_research_only"),
        "strategy_foundry_v2_akber_filter_run": sections["next_generation_backtest"].get("strategy_foundry_v2_akber_filter_run"),
        "strategy_foundry_v2_trade_candidate_creation_allowed": sections["next_generation_backtest"].get("strategy_foundry_v2_trade_candidate_creation_allowed"),
        "akber_filter_v2_state": sections["next_generation_backtest"].get("akber_filter_v2_state"),
        "akber_filter_v2_input_count": sections["next_generation_backtest"].get("akber_filter_v2_input_count"),
        "akber_filter_v2_result_count": sections["next_generation_backtest"].get("akber_filter_v2_result_count"),
        "akber_filter_v2_pass_count": sections["next_generation_backtest"].get("akber_filter_v2_pass_count"),
        "akber_filter_v2_hold_count": sections["next_generation_backtest"].get("akber_filter_v2_hold_count"),
        "akber_filter_v2_veto_count": sections["next_generation_backtest"].get("akber_filter_v2_veto_count"),
        "akber_filter_v2_router_eligible_count": sections["next_generation_backtest"].get("akber_filter_v2_router_eligible_count"),
        "akber_filter_v2_router_eligible_with_missing_context_count": sections["next_generation_backtest"].get("akber_filter_v2_router_eligible_with_missing_context_count"),
        "akber_filter_v2_no_router_eligible_setup_has_missing_context": sections["next_generation_backtest"].get("akber_filter_v2_no_router_eligible_setup_has_missing_context"),
        "akber_filter_v2_pass_is_execution_approval": sections["next_generation_backtest"].get("akber_filter_v2_pass_is_execution_approval"),
        "akber_filter_v2_execution_approval_created": sections["next_generation_backtest"].get("akber_filter_v2_execution_approval_created"),
        "shadow_simulator_v2_state": sections["next_generation_backtest"].get("shadow_simulator_v2_state"),
        "shadow_simulator_v2_hypothesis_count": sections["next_generation_backtest"].get("shadow_simulator_v2_hypothesis_count"),
        "shadow_simulator_v2_hypothesis_with_shadow_evidence_count": sections["next_generation_backtest"].get("shadow_simulator_v2_hypothesis_with_shadow_evidence_count"),
        "shadow_simulator_v2_missing_shadow_evidence_count": sections["next_generation_backtest"].get("shadow_simulator_v2_missing_shadow_evidence_count"),
        "shadow_simulator_v2_historical_shadow_replay_count": sections["next_generation_backtest"].get("shadow_simulator_v2_historical_shadow_replay_count"),
        "shadow_simulator_v2_forward_tracking_count": sections["next_generation_backtest"].get("shadow_simulator_v2_forward_tracking_count"),
        "shadow_simulator_v2_counterfactual_no_order_count": sections["next_generation_backtest"].get("shadow_simulator_v2_counterfactual_no_order_count"),
        "shadow_simulator_v2_alternate_threshold_outcome_count": sections["next_generation_backtest"].get("shadow_simulator_v2_alternate_threshold_outcome_count"),
        "shadow_simulator_v2_missed_opportunity_count": sections["next_generation_backtest"].get("shadow_simulator_v2_missed_opportunity_count"),
        "shadow_simulator_v2_every_hypothesis_has_shadow_evidence": sections["next_generation_backtest"].get("shadow_simulator_v2_every_hypothesis_has_shadow_evidence"),
        "shadow_simulator_v2_router_confidence_increase_without_shadow_evidence_count": sections["next_generation_backtest"].get("shadow_simulator_v2_router_confidence_increase_without_shadow_evidence_count"),
        "shadow_simulator_v2_router_confidence_increase_created": sections["next_generation_backtest"].get("shadow_simulator_v2_router_confidence_increase_created"),
        "shadow_simulator_v2_shadow_success_cannot_create_paper_order": sections["next_generation_backtest"].get("shadow_simulator_v2_shadow_success_cannot_create_paper_order"),
        "shadow_simulator_v2_shadow_success_cannot_create_proof_credit": sections["next_generation_backtest"].get("shadow_simulator_v2_shadow_success_cannot_create_proof_credit"),
        "router_v2_state": sections["next_generation_backtest"].get("router_v2_state"),
        "router_v2_setup_count": sections["next_generation_backtest"].get("router_v2_setup_count"),
        "router_v2_decision_count": sections["next_generation_backtest"].get("router_v2_decision_count"),
        "router_v2_all_setups_have_exactly_one_final_state": sections["next_generation_backtest"].get("router_v2_all_setups_have_exactly_one_final_state"),
        "router_v2_paper_review_candidate_count": sections["next_generation_backtest"].get("router_v2_paper_review_candidate_count"),
        "router_v2_clean_paper_review_candidate_count": sections["next_generation_backtest"].get("router_v2_clean_paper_review_candidate_count"),
        "router_v2_handoff_record_count": sections["next_generation_backtest"].get("router_v2_handoff_record_count"),
        "router_v2_rejected_handoff_count": sections["next_generation_backtest"].get("router_v2_rejected_handoff_count"),
        "router_v2_only_clean_paper_review_candidates_reach_paperops": sections["next_generation_backtest"].get("router_v2_only_clean_paper_review_candidates_reach_paperops"),
        "router_v2_duplicate_idempotency_count": sections["next_generation_backtest"].get("router_v2_duplicate_idempotency_count"),
        "router_v2_duplicate_exposure_count": sections["next_generation_backtest"].get("router_v2_duplicate_exposure_count"),
        "router_v2_why_not_trading_now_reason": sections["next_generation_backtest"].get("router_v2_why_not_trading_now_reason"),
        "router_v2_why_not_trading_now_plain_english": sections["next_generation_backtest"].get("router_v2_why_not_trading_now_plain_english"),
        "router_v2_paper_order_created_count": sections["next_generation_backtest"].get("router_v2_paper_order_created_count"),
        "router_v2_broker_write_count": sections["next_generation_backtest"].get("router_v2_broker_write_count"),
        "router_v2_proof_credit_allowed": sections["next_generation_backtest"].get("router_v2_proof_credit_allowed"),
        "paper_lifecycle_v2_state": sections["next_generation_backtest"].get("paper_lifecycle_v2_state"),
        "paper_lifecycle_v2_order_count": sections["next_generation_backtest"].get("paper_lifecycle_v2_order_count"),
        "paper_lifecycle_v2_open_position_count": sections["next_generation_backtest"].get("paper_lifecycle_v2_open_position_count"),
        "paper_lifecycle_v2_closed_trade_count": sections["next_generation_backtest"].get("paper_lifecycle_v2_closed_trade_count"),
        "paper_lifecycle_v2_lifecycle_record_count": sections["next_generation_backtest"].get("paper_lifecycle_v2_lifecycle_record_count"),
        "paper_lifecycle_v2_ambiguous_lifecycle_count": sections["next_generation_backtest"].get("paper_lifecycle_v2_ambiguous_lifecycle_count"),
        "paper_lifecycle_v2_no_paper_order_ambiguous": sections["next_generation_backtest"].get("paper_lifecycle_v2_no_paper_order_ambiguous"),
        "paper_lifecycle_v2_stale_accepted_order_count": sections["next_generation_backtest"].get("paper_lifecycle_v2_stale_accepted_order_count"),
        "paper_lifecycle_v2_cancel_replace_needed_count": sections["next_generation_backtest"].get("paper_lifecycle_v2_cancel_replace_needed_count"),
        "paper_lifecycle_v2_state_counts": sections["next_generation_backtest"].get("paper_lifecycle_v2_state_counts"),
        "paper_lifecycle_v2_proof_boundary_state": sections["next_generation_backtest"].get("paper_lifecycle_v2_proof_boundary_state"),
        "paper_lifecycle_v2_proof_eligible_count": sections["next_generation_backtest"].get("paper_lifecycle_v2_proof_eligible_count"),
        "paper_lifecycle_v2_proof_rejected_count": sections["next_generation_backtest"].get("paper_lifecycle_v2_proof_rejected_count"),
        "paper_lifecycle_v2_proof_credit_requires_real_closed_trade_with_complete_lineage": sections["next_generation_backtest"].get("paper_lifecycle_v2_proof_credit_requires_real_closed_trade_with_complete_lineage"),
        "paper_lifecycle_v2_backtest_shadow_or_synthetic_proof_credit_count": sections["next_generation_backtest"].get("paper_lifecycle_v2_backtest_shadow_or_synthetic_proof_credit_count"),
        "paper_lifecycle_v2_paper_proof_ledger_credit_allowed": sections["next_generation_backtest"].get("paper_lifecycle_v2_paper_proof_ledger_credit_allowed"),
        "paper_lifecycle_v2_proof_credit_allowed": sections["next_generation_backtest"].get("paper_lifecycle_v2_proof_credit_allowed"),
        "learning_attribution_v2_state": sections["next_generation_backtest"].get("learning_attribution_v2_state"),
        "learning_attribution_v2_record_count": sections["next_generation_backtest"].get("learning_attribution_v2_record_count"),
        "learning_attribution_v2_backtest_record_count": sections["next_generation_backtest"].get("learning_attribution_v2_backtest_record_count"),
        "learning_attribution_v2_shadow_record_count": sections["next_generation_backtest"].get("learning_attribution_v2_shadow_record_count"),
        "learning_attribution_v2_akber_record_count": sections["next_generation_backtest"].get("learning_attribution_v2_akber_record_count"),
        "learning_attribution_v2_router_record_count": sections["next_generation_backtest"].get("learning_attribution_v2_router_record_count"),
        "learning_attribution_v2_paperops_record_count": sections["next_generation_backtest"].get("learning_attribution_v2_paperops_record_count"),
        "learning_attribution_v2_missed_opportunity_record_count": sections["next_generation_backtest"].get("learning_attribution_v2_missed_opportunity_record_count"),
        "learning_attribution_v2_paper_trade_outcome_record_count": sections["next_generation_backtest"].get("learning_attribution_v2_paper_trade_outcome_record_count"),
        "learning_attribution_v2_proof_rejected_record_count": sections["next_generation_backtest"].get("learning_attribution_v2_proof_rejected_record_count"),
        "learning_attribution_v2_hold_record_count": sections["next_generation_backtest"].get("learning_attribution_v2_hold_record_count"),
        "learning_attribution_v2_veto_record_count": sections["next_generation_backtest"].get("learning_attribution_v2_veto_record_count"),
        "learning_attribution_v2_proposal_count": sections["next_generation_backtest"].get("learning_attribution_v2_proposal_count"),
        "learning_attribution_v2_proposal_applied_count": sections["next_generation_backtest"].get("learning_attribution_v2_proposal_applied_count"),
            "learning_attribution_v2_authority_mutation_count": sections["next_generation_backtest"].get("learning_attribution_v2_authority_mutation_count"),
            "learning_attribution_v2_applied_update_count": sections["next_generation_backtest"].get("learning_attribution_v2_applied_update_count"),
            "learning_attribution_v2_learning_outputs_are_proposals_only": sections["next_generation_backtest"].get("learning_attribution_v2_learning_outputs_are_proposals_only"),
            "dashboard_vnext_state": sections["next_generation_backtest"].get("dashboard_vnext_state"),
            "dashboard_vnext_protected_section_count": sections["next_generation_backtest"].get("dashboard_vnext_protected_section_count"),
            "dashboard_vnext_protected_sections_not_reordered": sections["next_generation_backtest"].get("dashboard_vnext_protected_sections_not_reordered"),
            "dashboard_vnext_protected_sections_not_renamed": sections["next_generation_backtest"].get("dashboard_vnext_protected_sections_not_renamed"),
            "dashboard_vnext_protected_sections_not_removed": sections["next_generation_backtest"].get("dashboard_vnext_protected_sections_not_removed"),
            "dashboard_vnext_protected_sections_not_structurally_overhauled": sections["next_generation_backtest"].get("dashboard_vnext_protected_sections_not_structurally_overhauled"),
            "dashboard_vnext_enrichment_only_inside_protected_sections": sections["next_generation_backtest"].get("dashboard_vnext_enrichment_only_inside_protected_sections"),
            "dashboard_vnext_all_portfolio_values_agree": sections["next_generation_backtest"].get("dashboard_vnext_all_portfolio_values_agree"),
            "dashboard_vnext_downstream_section_count": sections["next_generation_backtest"].get("dashboard_vnext_downstream_section_count"),
            "dashboard_vnext_strategy_card_count": sections["next_generation_backtest"].get("dashboard_vnext_strategy_card_count"),
            "dashboard_vnext_pattern_card_count": sections["next_generation_backtest"].get("dashboard_vnext_pattern_card_count"),
            "dashboard_vnext_router_paperops_single_answer": sections["next_generation_backtest"].get("dashboard_vnext_router_paperops_single_answer"),
            "telegram_vnext_state": sections["next_generation_backtest"].get("telegram_vnext_state"),
            "telegram_vnext_message_candidate_count": sections["next_generation_backtest"].get("telegram_vnext_message_candidate_count"),
            "telegram_vnext_message_ready_count": sections["next_generation_backtest"].get("telegram_vnext_message_ready_count"),
            "telegram_vnext_message_rejected_duplicate_count": sections["next_generation_backtest"].get("telegram_vnext_message_rejected_duplicate_count"),
            "telegram_vnext_message_rejected_quality_count": sections["next_generation_backtest"].get("telegram_vnext_message_rejected_quality_count"),
            "telegram_vnext_message_rejected_unsafe_count": sections["next_generation_backtest"].get("telegram_vnext_message_rejected_unsafe_count"),
            "telegram_vnext_quality_pass_count": sections["next_generation_backtest"].get("telegram_vnext_quality_pass_count"),
            "telegram_vnext_latest_message_preview": sections["next_generation_backtest"].get("telegram_vnext_latest_message_preview"),
            "telegram_vnext_live_send_allowed": sections["next_generation_backtest"].get("telegram_vnext_live_send_allowed"),
            "telegram_vnext_command_path_enabled": sections["next_generation_backtest"].get("telegram_vnext_command_path_enabled"),
            "telegram_vnext_trade_candidate_created": sections["next_generation_backtest"].get("telegram_vnext_trade_candidate_created"),
            "telegram_vnext_risk_approval_created": sections["next_generation_backtest"].get("telegram_vnext_risk_approval_created"),
            "telegram_vnext_execution_approval_created": sections["next_generation_backtest"].get("telegram_vnext_execution_approval_created"),
            "telegram_vnext_paper_order_created_count": sections["next_generation_backtest"].get("telegram_vnext_paper_order_created_count"),
            "telegram_vnext_broker_write_count": sections["next_generation_backtest"].get("telegram_vnext_broker_write_count"),
            "telegram_vnext_proof_credit_allowed": sections["next_generation_backtest"].get("telegram_vnext_proof_credit_allowed"),
            "telegram_vnext_live_capital_enabled": sections["next_generation_backtest"].get("telegram_vnext_live_capital_enabled"),
            "long_backtest_lock_active": sections["next_generation_backtest"]["long_backtest_lock_active"],
            "paperops_watch_only_mode": sections["next_generation_backtest"]["paperops_watch_only_mode"],
            "phase_1_backfill_started": sections["next_generation_backtest"]["phase_1_backfill_started"],
        "freshness_state": sections["freshness"]["status"],
        "portfolio_consistency_status": context["dashboard_portfolio"]["portfolio_consistency"]["status"],
        "portfolio_value_series_count": sections["portfolio_value"]["series_count"],
        "current_position_count": sections["current_portfolio"]["position_count"],
        "trading_history_row_count": len(sections["trading_history"]["rows"]),
        "source_category_row_count": sections["source_network"]["category_row_count"],
        "source_row_count": sections["source_network"]["source_row_count"],
        "trading_universe_row_count": sections["source_network"]["trading_universe_row_count"],
        "all_strategy_count": sections["strategy_universe"]["all_strategy_count"],
        "currently_in_play_count": sections["strategy_universe"]["currently_in_play_count"],
        "linear_pattern_count": sections["pattern_lab"]["linear_pattern_count"],
        "nonlinear_pattern_count": sections["pattern_lab"]["nonlinear_pattern_count"],
        "evidence_quality_record_count": sections["evidence_quality"].get("evidence_record_count", 0),
        "evidence_quality_paper_review_candidate_count": sections["evidence_quality"].get("paper_review_candidate_count", 0),
        "evidence_quality_held_for_evidence_count": sections["evidence_quality"].get("held_for_evidence_count", 0),
        "trade_intent_count": sections["trade_intents"]["intent_count"],
        "pattern_workflow_record_count": sections["pattern_to_paper_workflow"]["recognized_pattern_count"],
        "pattern_workflow_handoff_candidate_count": sections["pattern_to_paper_workflow"]["paperops_handoff_candidate_count"],
        "pattern_workflow_telegram_candidate_count": sections["pattern_to_paper_workflow"]["telegram_candidate_count"],
        "pattern_intelligence_finding_count": sections["pattern_intelligence"]["finding_count"],
        "pattern_intelligence_paper_ready_count": sections["pattern_intelligence"]["paper_ready_count"],
        "learning_ledger_row_count": sections["learning_ledger"]["row_count"],
        "repair_queue_count": sections["repair_queue"]["repair_queue_count"],
        "stale_labeled_count": sections["freshness"]["stale_labeled_count"],
        "applied_change_count": 0,
        "paper_order_created_count": 0,
        "broker_write_count": 0,
        "proof_credit_allowed": False,
        "live_capital_enabled": False,
        "paper_growth_trial_calendar_advanced": False,
        "simulated_elapsed_time_allowed": False,
        "view_model_refs": {
            "decision_records": _artifact_ref(DECISION_RECORDS_ARTIFACT),
            "system_map": _artifact_ref(SYSTEM_MAP_ARTIFACT),
            "portfolio_value_series": _artifact_ref(PORTFOLIO_SERIES_ARTIFACT),
            "current_portfolio": _artifact_ref(CURRENT_PORTFOLIO_ARTIFACT),
            "trading_history": _artifact_ref(TRADING_HISTORY_ARTIFACT),
            "source_network": _artifact_ref(SOURCE_NETWORK_ARTIFACT),
            "strategy_universe": _artifact_ref(STRATEGY_UNIVERSE_ARTIFACT),
            "pattern_lab": _artifact_ref(PATTERN_LAB_ARTIFACT),
            "evidence_quality": _artifact_ref(EVIDENCE_QUALITY_ARTIFACT),
            "trade_intents": _artifact_ref(TRADE_INTENTS_ARTIFACT),
            "pattern_to_paper_workflow": _artifact_ref(PATTERN_TO_PAPER_WORKFLOW_ARTIFACT),
            "pattern_intelligence": _artifact_ref(PATTERN_INTELLIGENCE_ARTIFACT),
            "learning_ledger": _artifact_ref(LEARNING_LEDGER_ARTIFACT),
            "repair_queue": _artifact_ref(REPAIR_QUEUE_ARTIFACT),
            "next_generation_backtest": _artifact_ref(NEXT_GENERATION_BACKTEST_DASHBOARD_ARTIFACT),
            "evidence_contracts": _artifact_ref(EVIDENCE_CONTRACTS_DASHBOARD_ARTIFACT),
            "world_model": _artifact_ref(WORLD_MODEL_DASHBOARD_ARTIFACT),
            "pattern_engine_v2": _artifact_ref(PATTERN_ENGINE_V2_DASHBOARD_ARTIFACT),
            "strategy_evidence_map": _artifact_ref(STRATEGY_EVIDENCE_MAP_DASHBOARD_ARTIFACT),
            "strategy_foundry_v2": _artifact_ref(STRATEGY_FOUNDRY_V2_DASHBOARD_ARTIFACT),
            "akber_filter_v2": _artifact_ref(AKBER_FILTER_V2_DASHBOARD_ARTIFACT),
            "shadow_simulator_v2": _artifact_ref(SHADOW_SIMULATOR_V2_DASHBOARD_ARTIFACT),
            "router_v2": _artifact_ref(ROUTER_V2_DASHBOARD_ARTIFACT),
            "paper_lifecycle_v2": _artifact_ref(PAPER_LIFECYCLE_V2_DASHBOARD_ARTIFACT),
            "learning_attribution_v2": _artifact_ref(LEARNING_ATTRIBUTION_V2_DASHBOARD_ARTIFACT),
            "dashboard_vnext": _artifact_ref(DASHBOARD_VNEXT_DASHBOARD_ARTIFACT),
            "telegram_vnext": _artifact_ref(TELEGRAM_VNEXT_DASHBOARD_ARTIFACT),
            "telegram_vnext_communications": _artifact_ref(TELEGRAM_VNEXT_COMMUNICATIONS_MIRROR_ARTIFACT),
            "self_healing_status": _artifact_ref(QADAM_SELF_HEALING_STATUS_ARTIFACT),
            "self_healing_repair_queue": _artifact_ref(QADAM_SELF_HEALING_REPAIR_QUEUE_ARTIFACT),
            "layered_market_judgment": _artifact_ref(
                LAYERED_MARKET_JUDGMENT_DASHBOARD_ARTIFACT
            ),
            "anti_slop": _artifact_ref(ANTI_SLOP_ARTIFACT),
        },
        "qsase_snapshot": sections["qsase_snapshot"],
        "dashboard_portfolio": context["dashboard_portfolio"],
        "portfolio_value": sections["portfolio_value"],
        "current_portfolio": sections["current_portfolio"],
        "trading_history": sections["trading_history"],
        "source_network": sections["source_network"],
        "strategy_universe": sections["strategy_universe"],
        "pattern_lab": sections["pattern_lab"],
        "evidence_quality": sections["evidence_quality"],
        "trade_intents": sections["trade_intents"],
        "pattern_to_paper_workflow": sections["pattern_to_paper_workflow"],
        "pattern_intelligence": sections["pattern_intelligence"],
        "learning_ledger": sections["learning_ledger"],
        "repair_queue": sections["repair_queue"],
        "next_generation_backtest": sections["next_generation_backtest"],
        "self_healing": context.get("qadam_self_healing_status") or context.get("qadam_self_healing_dashboard", {}),
        "self_healing_dashboard_summary": context.get("qadam_self_healing_dashboard", {}),
        "self_healing_repair_queue": context.get("qadam_self_healing_repair_queue", {}),
        "layered_market_judgment": context.get("layered_market_judgment", {}),
        "telegram_summary_v2": context.get("telegram_vnext_dashboard", {}),
        "telegram_communications_mirror_v2": context.get("telegram_vnext_communications_mirror", {}),
        "freshness": sections["freshness"],
        "system_map": system_map,
        "decision_records": decision_records,
        "input_snapshots": context.get("input_snapshots", {}),
        "authority": universal_authority_flags(),
        "authority_flags": _dashboard_authority(),
    }
    anti_slop = run_dashboard_anti_slop_checks(payload)
    payload["anti_slop_audit"] = anti_slop
    if anti_slop["error_count"]:
        payload["status"] = "qsase_dashboard_visibility_blocked"
    elif payload["stale_labeled_count"]:
        payload["status"] = "qsase_dashboard_visibility_ready_with_stale_labels"
    return payload


def _status_summary(payload: dict[str, Any]) -> dict[str, Any]:
    keys = (
        "schema_version",
        "artifact_type",
        "phase_id",
        "phase_name",
        "generated_at",
        "status",
        "public_safe",
        "command_disabled",
        "read_only",
        "paper_only",
        "proposal_first",
        "default_dashboard_sections_visible",
        "overview_detail_policy",
        "portfolio_value_line_graph_state",
        "current_portfolio_state",
        "trading_history_state",
        "source_network_state",
        "strategy_universe_state",
        "pattern_lab_state",
        "evidence_quality_state",
        "trade_intents_state",
        "pattern_to_paper_workflow_state",
        "pattern_intelligence_state",
        "learning_ledger_state",
        "repair_queue_state",
        "self_healing_state",
        "self_healing_repair_queue_count",
        "self_healing_provider_outage_count",
        "self_healing_stale_or_missing_artifact_count",
        "next_generation_backtest_state",
        "evidence_contracts_state",
        "evidence_contract_count",
        "missing_typed_evidence_count",
        "contracts_with_missing_evidence_count",
        "evidence_contract_downstream_reader_state",
        "world_model_state",
        "world_model_hypothesis_count",
        "world_model_research_question_count",
        "world_model_mapped_market_count",
        "world_model_trade_candidate_creation_allowed",
        "pattern_engine_v2_state",
        "pattern_engine_v2_pattern_count",
        "pattern_engine_v2_ranked_pattern_count",
        "pattern_engine_v2_held_for_more_evidence_count",
        "pattern_engine_v2_rejected_pattern_count",
        "pattern_engine_v2_research_only",
        "pattern_engine_v2_trade_candidate_creation_allowed",
        "strategy_evidence_map_state",
        "strategy_evidence_map_strategy_count",
        "strategy_evidence_map_evidence_backed_strategy_count",
        "strategy_evidence_map_under_evidenced_strategy_count",
        "strategy_evidence_map_research_only",
        "strategy_evidence_map_strategy_hypothesis_creation_allowed",
        "strategy_evidence_map_trade_candidate_creation_allowed",
        "strategy_foundry_v2_state",
        "strategy_foundry_v2_hypothesis_count",
        "strategy_foundry_v2_accepted_for_akber_input_builder_count",
        "strategy_foundry_v2_rejected_before_akber_count",
        "strategy_foundry_v2_weak_pattern_rejection_count",
        "strategy_foundry_v2_research_only",
        "strategy_foundry_v2_akber_filter_run",
        "strategy_foundry_v2_trade_candidate_creation_allowed",
        "akber_filter_v2_state",
        "akber_filter_v2_input_count",
        "akber_filter_v2_result_count",
        "akber_filter_v2_pass_count",
        "akber_filter_v2_hold_count",
        "akber_filter_v2_veto_count",
        "akber_filter_v2_router_eligible_count",
        "akber_filter_v2_router_eligible_with_missing_context_count",
        "akber_filter_v2_no_router_eligible_setup_has_missing_context",
        "akber_filter_v2_pass_is_execution_approval",
        "akber_filter_v2_execution_approval_created",
        "shadow_simulator_v2_state",
        "shadow_simulator_v2_hypothesis_count",
        "shadow_simulator_v2_hypothesis_with_shadow_evidence_count",
        "shadow_simulator_v2_missing_shadow_evidence_count",
        "shadow_simulator_v2_historical_shadow_replay_count",
        "shadow_simulator_v2_forward_tracking_count",
        "shadow_simulator_v2_counterfactual_no_order_count",
        "shadow_simulator_v2_alternate_threshold_outcome_count",
        "shadow_simulator_v2_missed_opportunity_count",
        "shadow_simulator_v2_every_hypothesis_has_shadow_evidence",
        "shadow_simulator_v2_router_confidence_increase_without_shadow_evidence_count",
        "shadow_simulator_v2_router_confidence_increase_created",
        "shadow_simulator_v2_shadow_success_cannot_create_paper_order",
        "shadow_simulator_v2_shadow_success_cannot_create_proof_credit",
        "router_v2_state",
        "router_v2_setup_count",
        "router_v2_decision_count",
        "router_v2_all_setups_have_exactly_one_final_state",
        "router_v2_paper_review_candidate_count",
        "router_v2_clean_paper_review_candidate_count",
        "router_v2_handoff_record_count",
        "router_v2_rejected_handoff_count",
        "router_v2_only_clean_paper_review_candidates_reach_paperops",
        "router_v2_duplicate_idempotency_count",
        "router_v2_duplicate_exposure_count",
        "router_v2_why_not_trading_now_reason",
        "router_v2_why_not_trading_now_plain_english",
        "router_v2_paper_order_created_count",
        "router_v2_broker_write_count",
        "router_v2_proof_credit_allowed",
        "paper_lifecycle_v2_state",
        "paper_lifecycle_v2_order_count",
        "paper_lifecycle_v2_open_position_count",
        "paper_lifecycle_v2_closed_trade_count",
        "paper_lifecycle_v2_lifecycle_record_count",
        "paper_lifecycle_v2_ambiguous_lifecycle_count",
        "paper_lifecycle_v2_no_paper_order_ambiguous",
        "paper_lifecycle_v2_stale_accepted_order_count",
        "paper_lifecycle_v2_cancel_replace_needed_count",
        "paper_lifecycle_v2_state_counts",
        "paper_lifecycle_v2_proof_boundary_state",
        "paper_lifecycle_v2_proof_eligible_count",
        "paper_lifecycle_v2_proof_rejected_count",
        "paper_lifecycle_v2_proof_credit_requires_real_closed_trade_with_complete_lineage",
        "paper_lifecycle_v2_backtest_shadow_or_synthetic_proof_credit_count",
        "paper_lifecycle_v2_paper_proof_ledger_credit_allowed",
        "paper_lifecycle_v2_proof_credit_allowed",
        "learning_attribution_v2_state",
        "learning_attribution_v2_record_count",
        "learning_attribution_v2_backtest_record_count",
        "learning_attribution_v2_shadow_record_count",
        "learning_attribution_v2_akber_record_count",
        "learning_attribution_v2_router_record_count",
        "learning_attribution_v2_paperops_record_count",
        "learning_attribution_v2_missed_opportunity_record_count",
        "learning_attribution_v2_paper_trade_outcome_record_count",
        "learning_attribution_v2_proof_rejected_record_count",
        "learning_attribution_v2_hold_record_count",
        "learning_attribution_v2_veto_record_count",
        "learning_attribution_v2_proposal_count",
        "learning_attribution_v2_proposal_applied_count",
        "learning_attribution_v2_authority_mutation_count",
        "learning_attribution_v2_applied_update_count",
        "learning_attribution_v2_learning_outputs_are_proposals_only",
        "dashboard_vnext_state",
        "dashboard_vnext_protected_section_count",
        "dashboard_vnext_protected_sections_not_reordered",
        "dashboard_vnext_protected_sections_not_renamed",
        "dashboard_vnext_protected_sections_not_removed",
        "dashboard_vnext_protected_sections_not_structurally_overhauled",
        "dashboard_vnext_enrichment_only_inside_protected_sections",
        "dashboard_vnext_all_portfolio_values_agree",
        "dashboard_vnext_downstream_section_count",
        "dashboard_vnext_strategy_card_count",
        "dashboard_vnext_pattern_card_count",
        "dashboard_vnext_router_paperops_single_answer",
        "telegram_vnext_state",
        "telegram_vnext_message_candidate_count",
        "telegram_vnext_message_ready_count",
        "telegram_vnext_message_rejected_duplicate_count",
        "telegram_vnext_message_rejected_quality_count",
        "telegram_vnext_message_rejected_unsafe_count",
        "telegram_vnext_quality_pass_count",
        "telegram_vnext_latest_message_preview",
        "telegram_vnext_live_send_allowed",
        "telegram_vnext_command_path_enabled",
        "telegram_vnext_trade_candidate_created",
        "telegram_vnext_risk_approval_created",
        "telegram_vnext_execution_approval_created",
        "telegram_vnext_paper_order_created_count",
        "telegram_vnext_broker_write_count",
        "telegram_vnext_proof_credit_allowed",
        "telegram_vnext_live_capital_enabled",
        "telegram_summary_v2",
        "telegram_communications_mirror_v2",
        "long_backtest_lock_active",
        "paperops_watch_only_mode",
        "phase_1_backfill_started",
        "freshness_state",
        "dashboard_portfolio",
        "portfolio_consistency_status",
        "portfolio_value_series_count",
        "current_position_count",
        "trading_history_row_count",
        "source_category_row_count",
        "source_row_count",
        "trading_universe_row_count",
        "all_strategy_count",
        "currently_in_play_count",
        "linear_pattern_count",
        "nonlinear_pattern_count",
        "evidence_quality_record_count",
        "evidence_quality_paper_review_candidate_count",
        "evidence_quality_held_for_evidence_count",
        "trade_intent_count",
        "pattern_workflow_record_count",
        "pattern_workflow_handoff_candidate_count",
        "pattern_workflow_telegram_candidate_count",
        "pattern_intelligence_finding_count",
        "pattern_intelligence_paper_ready_count",
        "learning_ledger_row_count",
        "repair_queue_count",
        "stale_labeled_count",
        "applied_change_count",
        "paper_order_created_count",
        "broker_write_count",
        "proof_credit_allowed",
        "live_capital_enabled",
        "paper_growth_trial_calendar_advanced",
        "simulated_elapsed_time_allowed",
        "view_model_refs",
        "authority",
        "authority_flags",
    )
    return {key: payload[key] for key in keys}


def load_dashboard_view_model(settings: Settings | None = None) -> dict[str, Any]:
    runtime = _runtime_dir(settings)
    status = _read_json(runtime / STATUS_ARTIFACT)
    if not status:
        return {}
    status["decision_records"] = _read_json(runtime / DECISION_RECORDS_ARTIFACT)
    status["system_map"] = _read_json(runtime / SYSTEM_MAP_ARTIFACT)
    status["portfolio_value"] = _read_json(runtime / PORTFOLIO_SERIES_ARTIFACT)
    status["current_portfolio"] = _read_json(runtime / CURRENT_PORTFOLIO_ARTIFACT)
    status["trading_history"] = _read_json(runtime / TRADING_HISTORY_ARTIFACT)
    status["source_network"] = _read_json(runtime / SOURCE_NETWORK_ARTIFACT)
    status["strategy_universe"] = _read_json(runtime / STRATEGY_UNIVERSE_ARTIFACT)
    status["pattern_lab"] = _read_json(runtime / PATTERN_LAB_ARTIFACT)
    status["evidence_quality"] = _read_json(runtime / EVIDENCE_QUALITY_ARTIFACT)
    status["trade_intents"] = _read_json(runtime / TRADE_INTENTS_ARTIFACT)
    status["pattern_to_paper_workflow"] = _read_json(runtime / PATTERN_TO_PAPER_WORKFLOW_ARTIFACT)
    status["pattern_intelligence"] = _read_json(runtime / PATTERN_INTELLIGENCE_ARTIFACT)
    status["learning_ledger"] = _read_json(runtime / LEARNING_LEDGER_ARTIFACT)
    status["repair_queue"] = _read_json(runtime / REPAIR_QUEUE_ARTIFACT)
    status["telegram_summary_v2"] = _read_json(runtime / TELEGRAM_VNEXT_DASHBOARD_ARTIFACT)
    status["telegram_communications_mirror_v2"] = _read_json(runtime / TELEGRAM_VNEXT_COMMUNICATIONS_MIRROR_ARTIFACT)
    status["anti_slop_audit"] = _read_json(runtime / ANTI_SLOP_ARTIFACT)
    return status


def validate_dashboard_view_model(payload: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if payload.get("artifact_type") != "qsase_dashboard_view_model":
        errors.append("artifact_type_invalid")
    if payload.get("schema_version") != SCHEMA_VERSION:
        errors.append("schema_version_invalid")
    if payload.get("status") not in {
        "qsase_dashboard_visibility_ready",
        "qsase_dashboard_visibility_ready_with_stale_labels",
        "qsase_dashboard_visibility_degraded",
        "qsase_dashboard_visibility_blocked",
    }:
        errors.append("status_invalid")
    for key in ("public_safe", "command_disabled", "read_only", "paper_only", "proposal_first", "default_dashboard_sections_visible"):
        if payload.get(key) is not True:
            errors.append(f"{key}_must_be_true")
    for key in (
        "proof_credit_allowed",
        "live_capital_enabled",
        "paper_growth_trial_calendar_advanced",
        "simulated_elapsed_time_allowed",
    ):
        if payload.get(key) is not False:
            errors.append(f"{key}_must_be_false")
    for key in ("applied_change_count", "paper_order_created_count", "broker_write_count"):
        if int(payload.get(key, -1) or 0) != 0:
            errors.append(f"{key}_must_be_zero")
    if any(value is not False for value in payload.get("authority", {}).values()):
        errors.append("universal_authority_flags_must_all_be_false")
    for field in FALSE_AUTHORITY_FIELDS:
        if payload.get("authority_flags", {}).get(field) is not False:
            errors.append(f"dashboard_authority_{field}_must_be_false")
    portfolio = payload.get("dashboard_portfolio", {})
    if portfolio.get("artifact_type") != "dashboard_portfolio_canonical_contract":
        errors.append("dashboard_portfolio_contract_missing")
    if portfolio.get("portfolio_consistency", {}).get("status") != "ok":
        errors.append("dashboard_portfolio_consistency_mismatch")
    if payload.get("portfolio_consistency_status") != "ok":
        errors.append("portfolio_consistency_status_not_ok")
    portfolio_latest = _round_money(portfolio.get("current_value_gbp"))
    chart_latest = _round_money(payload.get("portfolio_value", {}).get("latest_value"))
    if portfolio_latest is None or chart_latest is None or abs(portfolio_latest - chart_latest) > 0.01:
        errors.append("portfolio_value_latest_chart_mismatch")
    portfolio_position_count = int(portfolio.get("open_position_count") or 0)
    current_position_count = int(payload.get("current_portfolio", {}).get("position_count") or 0)
    if portfolio_position_count != current_position_count:
        errors.append("portfolio_position_count_mismatch")
    if payload.get("portfolio_value", {}).get("line_graph_available") is not True and not payload.get("portfolio_value", {}).get("unavailable_reason"):
        errors.append("portfolio_value_line_graph_missing_without_reason")
    if not isinstance(payload.get("current_portfolio", {}).get("rows"), list):
        errors.append("current_portfolio_rows_missing")
    if not isinstance(payload.get("trading_history", {}).get("rows"), list):
        errors.append("trading_history_rows_missing")
    if int(payload.get("source_network", {}).get("category_row_count") or 0) <= 0:
        errors.append("source_category_rows_missing")
    if int(payload.get("source_network", {}).get("source_row_count") or 0) <= 0:
        errors.append("source_rows_missing")
    if int(payload.get("source_network", {}).get("trading_universe_row_count") or 0) <= 0:
        errors.append("trading_universe_rows_missing")
    if int(payload.get("strategy_universe", {}).get("all_strategy_count") or 0) <= 0:
        errors.append("strategy_universe_rows_missing")
    if "currently_in_play_rows" not in payload.get("strategy_universe", {}):
        errors.append("strategy_currently_in_play_rows_missing")
    strategy_universe = payload.get("strategy_universe", {})
    if int(strategy_universe.get("defined_strategy_count") or 0) != len(strategy_universe.get("all_strategy_rows", [])):
        errors.append("strategy_defined_count_mismatch")
    discovery = strategy_universe.get("strategy_discovery_engine", {})
    if len(discovery.get("methods", [])) < 5:
        errors.append("strategy_discovery_methods_missing")
    if int(discovery.get("strategy_agnostic_scan_count") or 0) <= 0:
        errors.append("strategy_agnostic_discovery_missing")
    emerging = strategy_universe.get("emerging_strategy_candidates", {})
    if int(emerging.get("candidate_count") or 0) != len(emerging.get("rows", [])):
        errors.append("emerging_strategy_candidate_count_mismatch")
    admission = strategy_universe.get("strategy_admission_path", {})
    if len(admission.get("stages", [])) < 6 or not admission.get("current_stage_id"):
        errors.append("strategy_admission_path_incomplete")
    if "cannot create an order" not in str(admission.get("authority_boundary") or ""):
        errors.append("strategy_admission_authority_boundary_missing")
    if admission.get("next_destination", {}).get("label") != "Decision Room":
        errors.append("strategy_admission_decision_room_handoff_missing")
    if any("akber" in str(label).lower() for label in admission.get("after_admission", [])):
        errors.append("strategy_page_duplicates_akber_decision_stage")
    for row in strategy_universe.get("all_strategy_rows", []):
        if row.get("defined_playbook") is not True:
            errors.append(f"strategy_not_marked_defined:{row.get('strategy_family_id')}")
        if not row.get("validation_state_label"):
            errors.append(f"strategy_validation_state_missing:{row.get('strategy_family_id')}")
        if row.get("validated_edge_count") is None:
            errors.append(f"strategy_validated_edge_count_missing:{row.get('strategy_family_id')}")
    if int(payload.get("pattern_lab", {}).get("linear_pattern_count") or 0) <= 0:
        errors.append("linear_pattern_rows_missing")
    if int(payload.get("pattern_lab", {}).get("nonlinear_pattern_count") or 0) <= 0:
        errors.append("nonlinear_pattern_rows_missing")
    evidence_quality = payload.get("evidence_quality", {})
    if evidence_quality.get("artifact_type") != "qsase_evidence_quality":
        errors.append("evidence_quality_artifact_missing")
    if int(evidence_quality.get("evidence_record_count") or 0) <= 0:
        errors.append("evidence_quality_records_missing")
    for field in (
        "paper_order_allowed",
        "trade_candidate_created",
        "qualified_setup_created",
        "broker_write_allowed",
        "proof_credit_allowed",
        "live_capital_enabled",
    ):
        if evidence_quality.get(field) is not False:
            errors.append(f"evidence_quality_{field}_must_be_false")
    if "rows" not in payload.get("trade_intents", {}):
        errors.append("trade_intent_rows_missing")
    for row in payload.get("trade_intents", {}).get("rows", []):
        for field in ("is_trade", "is_order", "is_approval", "is_qualified_setup", "paper_order_created"):
            if row.get(field) is not False:
                errors.append(f"trade_intent_{row.get('intent_id')}_{field}_must_be_false")
    workflow = payload.get("pattern_to_paper_workflow", {})
    if workflow.get("artifact_type") != "qsase_pattern_to_paper_workflow":
        errors.append("pattern_to_paper_workflow_artifact_missing")
    if int(workflow.get("recognized_pattern_count") or 0) <= 0:
        errors.append("pattern_to_paper_workflow_records_missing")
    if workflow.get("telegram_candidate", {}).get("telegram_live_send_allowed") is not False:
        errors.append("pattern_to_paper_workflow_live_send_must_be_false")
    if workflow.get("telegram_candidate", {}).get("telegram_command_path_enabled") is not False:
        errors.append("pattern_to_paper_workflow_telegram_command_must_be_false")
    for field in ("paper_order_created_count", "broker_write_count"):
        if int(workflow.get(field, -1) or 0) != 0:
            errors.append(f"pattern_to_paper_workflow_{field}_must_be_zero")
    for field in (
        "paper_order_allowed",
        "trade_candidate_created",
        "qualified_setup_created",
        "broker_write_allowed",
        "proof_credit_allowed",
        "live_capital_enabled",
    ):
        if workflow.get(field) is not False:
            errors.append(f"pattern_to_paper_workflow_{field}_must_be_false")
    for record in workflow.get("records", []):
        record_id = record.get("workflow_id")
        for required in ("pattern_thesis", "invalidation", "next_allowed_action", "telegram_summary", "artifact_refs"):
            if not record.get(required):
                errors.append(f"pattern_workflow_{record_id}_missing_{required}")
        for field in (
            "paper_order_allowed",
            "paper_order_created",
            "trade_candidate_created",
            "qualified_setup_created",
            "broker_write_allowed",
            "proof_credit_allowed",
            "live_capital_enabled",
        ):
            if record.get(field) is not False:
                errors.append(f"pattern_workflow_{record_id}_{field}_must_be_false")
    intelligence = payload.get("pattern_intelligence", {})
    if intelligence.get("artifact_type") != "qsase_pattern_intelligence":
        errors.append("pattern_intelligence_artifact_missing")
    if int(intelligence.get("finding_count") or 0) <= 0:
        errors.append("pattern_intelligence_findings_missing")
    if not intelligence.get("human_brief", {}).get("body"):
        errors.append("pattern_intelligence_human_brief_missing")
    if intelligence.get("human_brief", {}).get("telegram_live_send_allowed") is not False:
        errors.append("pattern_intelligence_live_send_must_be_false")
    if intelligence.get("human_brief", {}).get("telegram_command_path_enabled") is not False:
        errors.append("pattern_intelligence_telegram_command_must_be_false")
    for field in (
        "paper_order_allowed",
        "trade_candidate_created",
        "qualified_setup_created",
        "broker_write_allowed",
        "proof_credit_allowed",
        "live_capital_enabled",
    ):
        if intelligence.get(field) is not False:
            errors.append(f"pattern_intelligence_{field}_must_be_false")
    for finding in intelligence.get("findings", []):
        finding_id = finding.get("finding_id")
        for required in (
            "detected_signal",
            "market_affected",
            "source_signal_summary",
            "evidence_summary",
            "what_qadam_thinks",
            "what_would_confirm",
            "what_blocks_trade",
            "next_action",
            "stage_label",
        ):
            if not finding.get(required):
                errors.append(f"pattern_intelligence_{finding_id}_missing_{required}")
        if finding.get("paper_order_allowed") is not False:
            errors.append(f"pattern_intelligence_{finding_id}_paper_order_allowed_must_be_false")
        if finding.get("broker_write_allowed") is not False:
            errors.append(f"pattern_intelligence_{finding_id}_broker_write_allowed_must_be_false")
        if finding.get("live_capital_enabled") is not False:
            errors.append(f"pattern_intelligence_{finding_id}_live_capital_enabled_must_be_false")
    if not payload.get("decision_records", {}).get("records"):
        errors.append("decision_records_missing")
    if payload.get("system_map", {}).get("overview_detail_policy", {}).get("detailed_ledgers_in_overview") is not False:
        errors.append("overview_contains_detailed_ledgers")
    if not payload.get("learning_ledger", {}).get("rows"):
        errors.append("learning_ledger_rows_missing")
    if "rows" not in payload.get("repair_queue", {}):
        errors.append("repair_queue_rows_missing")
    anti_slop = payload.get("anti_slop_audit", {})
    if anti_slop.get("status") != "anti_slop_passed":
        errors.extend(anti_slop.get("errors", []) or ["anti_slop_not_passed"])
    return sorted(set(errors))


def build_qsase_phase_implementation_status(payload: dict[str, Any]) -> dict[str, Any]:
    runtime_dir = _runtime_dir()
    existing = _read_json(runtime_dir / PHASE_STATUS_ARTIFACT)
    phases = existing.get("phases") if isinstance(existing.get("phases"), dict) else {}
    existing_safety = existing.get("safety") if isinstance(existing.get("safety"), dict) else {}
    safety = {
        **existing_safety,
        **payload["authority"],
    }
    phases[PHASE_ID] = {
        "name": PHASE_NAME,
        "status": payload["status"],
        "artifact_path": f"data/runtime/{STATUS_ARTIFACT}",
        "decision_records_path": f"data/runtime/{DECISION_RECORDS_ARTIFACT}",
        "system_map_path": f"data/runtime/{SYSTEM_MAP_ARTIFACT}",
        "portfolio_value_series_path": f"data/runtime/{PORTFOLIO_SERIES_ARTIFACT}",
        "source_network_path": f"data/runtime/{SOURCE_NETWORK_ARTIFACT}",
        "strategy_universe_path": f"data/runtime/{STRATEGY_UNIVERSE_ARTIFACT}",
        "pattern_lab_path": f"data/runtime/{PATTERN_LAB_ARTIFACT}",
        "evidence_quality_path": f"data/runtime/{EVIDENCE_QUALITY_ARTIFACT}",
        "trade_intents_path": f"data/runtime/{TRADE_INTENTS_ARTIFACT}",
        "pattern_to_paper_workflow_path": f"data/runtime/{PATTERN_TO_PAPER_WORKFLOW_ARTIFACT}",
        "pattern_intelligence_path": f"data/runtime/{PATTERN_INTELLIGENCE_ARTIFACT}",
        "learning_ledger_path": f"data/runtime/{LEARNING_LEDGER_ARTIFACT}",
        "anti_slop_path": f"data/runtime/{ANTI_SLOP_ARTIFACT}",
        "portfolio_value_series_count": payload["portfolio_value_series_count"],
        "current_position_count": payload["current_position_count"],
        "trading_history_row_count": payload["trading_history_row_count"],
        "source_category_row_count": payload["source_category_row_count"],
        "source_row_count": payload["source_row_count"],
        "all_strategy_count": payload["all_strategy_count"],
        "currently_in_play_count": payload["currently_in_play_count"],
        "linear_pattern_count": payload["linear_pattern_count"],
        "nonlinear_pattern_count": payload["nonlinear_pattern_count"],
        "evidence_quality_record_count": payload["evidence_quality_record_count"],
        "evidence_quality_paper_review_candidate_count": payload["evidence_quality_paper_review_candidate_count"],
        "evidence_quality_held_for_evidence_count": payload["evidence_quality_held_for_evidence_count"],
        "trade_intent_count": payload["trade_intent_count"],
        "pattern_workflow_record_count": payload["pattern_workflow_record_count"],
        "pattern_workflow_handoff_candidate_count": payload["pattern_workflow_handoff_candidate_count"],
        "pattern_workflow_telegram_candidate_count": payload["pattern_workflow_telegram_candidate_count"],
        "pattern_intelligence_finding_count": payload["pattern_intelligence_finding_count"],
        "pattern_intelligence_paper_ready_count": payload["pattern_intelligence_paper_ready_count"],
        "learning_ledger_row_count": payload["learning_ledger_row_count"],
        "repair_queue_count": payload["repair_queue_count"],
        "anti_slop_error_count": payload["anti_slop_audit"]["error_count"],
        "paper_only": True,
        "read_only": True,
        "public_safe": True,
        "no_authority_created": True,
        "no_paper_orders_created": True,
        "no_broker_writes": True,
        "no_proof_credit_granted": True,
        "later_qsase_phases_implemented": False,
    }
    return {
        "schema_version": 1,
        "generated_at": payload["generated_at"],
        "active_phase": PHASE_ID,
        "phases": phases,
        "safety": safety,
    }


def _append_implementation_log(payload: dict[str, Any]) -> None:
    log_path = _repo_root() / IMPLEMENTATION_LOG
    log_path.parent.mkdir(parents=True, exist_ok=True)
    existing = log_path.read_text(encoding="utf-8") if log_path.exists() else "# QSASE Implementation Log\n"
    marker = f"<!-- {PHASE_ID} -->"
    entry = (
        f"{marker}\n"
        f"## QSASE-13: Dashboard Visibility\n\n"
        f"- Generated at: `{payload.get('generated_at')}`\n"
        f"- Status: `{payload.get('status')}`\n"
        f"- Runtime artifact: `data/runtime/{STATUS_ARTIFACT}`\n"
        f"- Portfolio series / positions / trading history rows: `{payload.get('portfolio_value_series_count')}` / `{payload.get('current_position_count')}` / `{payload.get('trading_history_row_count')}`\n"
        f"- Source categories / sources / trading universe rows: `{payload.get('source_category_row_count')}` / `{payload.get('source_row_count')}` / `{payload.get('trading_universe_row_count')}`\n"
        f"- Strategy families / in-play / linear / nonlinear / trade-intent rows: `{payload.get('all_strategy_count')}` / `{payload.get('currently_in_play_count')}` / `{payload.get('linear_pattern_count')}` / `{payload.get('nonlinear_pattern_count')}` / `{payload.get('trade_intent_count')}`\n"
        f"- Pattern workflow records / guarded handoff candidates / Telegram candidates: `{payload.get('pattern_workflow_record_count')}` / `{payload.get('pattern_workflow_handoff_candidate_count')}` / `{payload.get('pattern_workflow_telegram_candidate_count')}`\n"
        f"- Pattern intelligence findings / paper-ready findings: `{payload.get('pattern_intelligence_finding_count')}` / `{payload.get('pattern_intelligence_paper_ready_count')}`\n"
        f"- Learning / repair / anti-slop errors: `{payload.get('learning_ledger_row_count')}` / `{payload.get('repair_queue_count')}` / `{payload.get('anti_slop_audit', {}).get('error_count')}`\n"
        f"- Safety: dashboard artifacts are read-only decision records; no commands, trade candidates, qualified setups, approvals, paper orders, broker writes, live capital, 30-day paper growth trial calendar advancement, or paper proof ledger credit created.\n"
    )
    from orchestrator.qadam_marked_log import upsert_marked_section

    updated = upsert_marked_section(existing, marker, entry)
    log_path.write_text(updated, encoding="utf-8")


def write_dashboard_view_model(
    payload: dict[str, Any],
    settings: Settings | None = None,
    *,
    append_history: bool = True,
    append_log: bool = True,
) -> dict[str, str]:
    runtime = _runtime_dir(settings)
    runtime.mkdir(parents=True, exist_ok=True)
    paths = {
        "status": runtime / STATUS_ARTIFACT,
        "decision_records": runtime / DECISION_RECORDS_ARTIFACT,
        "system_map": runtime / SYSTEM_MAP_ARTIFACT,
        "portfolio_value": runtime / PORTFOLIO_SERIES_ARTIFACT,
        "current_portfolio": runtime / CURRENT_PORTFOLIO_ARTIFACT,
        "trading_history": runtime / TRADING_HISTORY_ARTIFACT,
        "source_network": runtime / SOURCE_NETWORK_ARTIFACT,
        "strategy_universe": runtime / STRATEGY_UNIVERSE_ARTIFACT,
        "pattern_lab": runtime / PATTERN_LAB_ARTIFACT,
        "evidence_quality": runtime / EVIDENCE_QUALITY_ARTIFACT,
        "trade_intents": runtime / TRADE_INTENTS_ARTIFACT,
        "pattern_to_paper_workflow": runtime / PATTERN_TO_PAPER_WORKFLOW_ARTIFACT,
        "pattern_intelligence": runtime / PATTERN_INTELLIGENCE_ARTIFACT,
        "learning_ledger": runtime / LEARNING_LEDGER_ARTIFACT,
        "repair_queue": runtime / REPAIR_QUEUE_ARTIFACT,
        "next_generation_backtest": runtime / NEXT_GENERATION_BACKTEST_DASHBOARD_ARTIFACT,
        "anti_slop": runtime / ANTI_SLOP_ARTIFACT,
        "phase_status": runtime / PHASE_STATUS_ARTIFACT,
    }
    _write_json(paths["status"], _status_summary(payload))
    _write_json(paths["decision_records"], payload["decision_records"])
    _write_json(paths["system_map"], payload["system_map"])
    _write_json(paths["portfolio_value"], payload["portfolio_value"])
    _write_json(paths["current_portfolio"], payload["current_portfolio"])
    _write_json(paths["trading_history"], payload["trading_history"])
    _write_json(paths["source_network"], payload["source_network"])
    _write_json(paths["strategy_universe"], payload["strategy_universe"])
    _write_json(paths["pattern_lab"], payload["pattern_lab"])
    _write_json(paths["evidence_quality"], payload["evidence_quality"])
    _write_json(paths["trade_intents"], payload["trade_intents"])
    _write_json(paths["pattern_to_paper_workflow"], payload["pattern_to_paper_workflow"])
    _write_json(paths["pattern_intelligence"], payload["pattern_intelligence"])
    _write_json(paths["learning_ledger"], payload["learning_ledger"])
    _write_json(paths["repair_queue"], payload["repair_queue"])
    _write_json(paths["next_generation_backtest"], payload["next_generation_backtest"])
    _write_json(paths["anti_slop"], payload["anti_slop_audit"])
    _write_json(paths["phase_status"], build_qsase_phase_implementation_status(payload))
    written = {key: str(path) for key, path in paths.items()}
    if append_history:
        history_path = runtime / HISTORY_ARTIFACT
        events_path = runtime / EVENTS_ARTIFACT
        _append_jsonl(
            history_path,
            {
                "generated_at": payload["generated_at"],
                "status": payload["status"],
                "portfolio_value_series_count": payload["portfolio_value_series_count"],
                "source_row_count": payload["source_row_count"],
                "all_strategy_count": payload["all_strategy_count"],
                "trade_intent_count": payload["trade_intent_count"],
                "pattern_workflow_record_count": payload["pattern_workflow_record_count"],
                "pattern_workflow_handoff_candidate_count": payload["pattern_workflow_handoff_candidate_count"],
                "pattern_intelligence_finding_count": payload["pattern_intelligence_finding_count"],
                "pattern_intelligence_paper_ready_count": payload["pattern_intelligence_paper_ready_count"],
                "learning_ledger_row_count": payload["learning_ledger_row_count"],
                "anti_slop_error_count": payload["anti_slop_audit"]["error_count"],
                "no_authority_created": True,
            },
        )
        _append_jsonl(
            events_path,
            {
                "generated_at": payload["generated_at"],
                "event_type": "qsase_dashboard_view_model_written",
                "status": payload["status"],
                "public_safe": True,
                "read_only": True,
                "anti_slop_passed": payload["anti_slop_audit"]["error_count"] == 0,
            },
        )
        written["history"] = str(history_path)
        written["events"] = str(events_path)
    if append_log:
        _append_implementation_log(payload)
        written["implementation_log"] = str(_repo_root() / IMPLEMENTATION_LOG)
    return written


def build_and_write_dashboard_view_model(
    settings: Settings | None = None,
) -> tuple[dict[str, Any], dict[str, str], list[str]]:
    payload = build_dashboard_view_model(settings)
    errors = validate_dashboard_view_model(payload)
    written = write_dashboard_view_model(payload, settings)
    return payload, written, errors


def validate_dashboard_anti_slop(payload: dict[str, Any]) -> list[str]:
    audit = run_dashboard_anti_slop_checks(payload)
    return audit.get("errors", [])


def validate_negative_dashboard_view_model_probes() -> list[str]:
    base = build_dashboard_view_model()
    errors: list[str] = []
    duplicate_probe = copy.deepcopy(base)
    duplicate_probe["decision_records"]["records"][1]["headline"] = duplicate_probe["decision_records"]["records"][0]["headline"]
    duplicate_probe["anti_slop_audit"] = run_dashboard_anti_slop_checks(duplicate_probe)
    if not any("duplicate_headline" in error for error in validate_dashboard_view_model(duplicate_probe)):
        errors.append("negative_probe_failed_for_duplicate_headline")
    generic_probe = copy.deepcopy(base)
    generic_probe["decision_records"]["records"][0]["reason"] = "AI-powered seamless dynamic insights"
    generic_probe["anti_slop_audit"] = run_dashboard_anti_slop_checks(generic_probe)
    if not any("generic_phrase" in error for error in validate_dashboard_view_model(generic_probe)):
        errors.append("negative_probe_failed_for_generic_phrase")
    authority_probe = copy.deepcopy(base)
    authority_rows = authority_probe["trade_intents"]["rows"]
    if not authority_rows:
        authority_rows.append(
            {
                "intent_id": "negative-probe-empty-queue",
                "row_type": "research review",
                "state": "research only",
                "is_trade": False,
                "is_order": False,
                "is_approval": False,
                "is_qualified_setup": False,
                "paper_order_created": False,
            }
        )
    authority_rows[0]["is_order"] = True
    authority_probe["anti_slop_audit"] = run_dashboard_anti_slop_checks(authority_probe)
    if not any("is_order" in error for error in validate_dashboard_view_model(authority_probe)):
        errors.append("negative_probe_failed_for_trade_intent_order_label")
    proof_probe = copy.deepcopy(base)
    proof_probe["proof_credit_allowed"] = True
    if not any("proof_credit_allowed" in error for error in validate_dashboard_view_model(proof_probe)):
        errors.append("negative_probe_failed_for_proof_credit")
    return errors


if __name__ == "__main__":
    artifact = build_dashboard_view_model()
    print(_json_dump(_status_summary(artifact)))
