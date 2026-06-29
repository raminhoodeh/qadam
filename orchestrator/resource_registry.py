"""Non-live resource registry for Qadam build and research references."""

from __future__ import annotations

from collections import Counter
from dataclasses import asdict, dataclass
from typing import Any


@dataclass(frozen=True)
class ResourceEntry:
    key: str
    name: str
    category: str
    source: str
    role: str
    mapped_modules: tuple[str, ...]
    validation_status: str = "provisional_reference"
    production_active: bool = False
    decision_notes: str = "Reference only until mapped to a test, module, or risk control."

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


RESOURCE_ENTRIES: tuple[ResourceEntry, ...] = (
    ResourceEntry(
        "edge_beats_excitement",
        "Edge Beats Excitement",
        "strategy_guardrail",
        "specs/qadam-general-context.md",
        "Operating discipline for avoiding hype-driven trades.",
        ("risk_agent", "signal_review", "postmortem"),
        decision_notes="No trade remains a first-class outcome.",
    ),
    ResourceEntry(
        "paper_forward_evidence",
        "Paper-Forward Evidence",
        "strategy_guardrail",
        "specs/qadam-general-context.md",
        "Treats backtests as weaker than observed paper-forward behavior.",
        ("event_log", "proof_plane", "strategy_manifestation"),
    ),
    ResourceEntry(
        "unusual_whales",
        "Unusual Whales",
        "signal_benchmark",
        "specs/qadam-general-context.md",
        "Benchmark for options-flow presentation and market-moving activity.",
        ("market_pipeline", "cockpit", "signal_review"),
    ),
    ResourceEntry(
        "glint_trade",
        "Glint Trade",
        "signal_benchmark",
        "specs/qadam-general-context.md",
        "Comparable market-intelligence UX reference.",
        ("cockpit", "signal_review"),
    ),
    ResourceEntry(
        "quantmap_report",
        "QuantMap Report",
        "signal_benchmark",
        "specs/qadam-general-context.md",
        "Reference for professional quant communication.",
        ("strategy_lead", "signal_review"),
    ),
    ResourceEntry(
        "hermes_xgboost_unusual_whales",
        "Hermes + XGBoost + Unusual Whales Stack",
        "ai_architecture",
        "specs/qadam-general-context.md",
        "Candidate pattern for options-mispricing modelling.",
        ("research_analyst", "strategy_lead", "market_pipeline"),
    ),
    ResourceEntry(
        "mirofish_swarm_probability",
        "MiroFish Swarm Probability",
        "ai_architecture",
        "specs/qadam-general-context.md",
        "Blueprint for swarm-derived probabilities against market pricing.",
        ("research_analyst", "strategy_lead", "learning_plane"),
    ),
    ResourceEntry(
        "graph_rag_personas",
        "Graph RAG + Personas",
        "ai_architecture",
        "specs/qadam-general-context.md",
        "Reference for knowledge graph plus agent-persona simulations.",
        ("knowledge_graph", "research_analyst"),
    ),
    ResourceEntry(
        "markov_regime_engine",
        "Markov Regime Engine",
        "ai_architecture",
        "specs/qadam-general-context.md",
        "Regime-aware gating before signals fire.",
        ("risk_agent", "strategy_lead"),
    ),
    ResourceEntry(
        "timesfm",
        "Google TimesFM",
        "ai_architecture",
        "specs/qadam-general-context.md",
        "Candidate time-series forecasting model for research tests.",
        ("research_analyst", "quant_plane"),
    ),
    ResourceEntry(
        "anthropic_financial_services",
        "Anthropic Financial Services",
        "ai_architecture",
        "https://github.com/anthropics/financial-services",
        "Reference pattern for named financial workflow agents, reusable skill bundles, connector grants, validation, and secret scanning.",
        ("agent_os", "research_analyst", "strategy_lead", "risk_agent", "fund_manager_cockpit"),
        validation_status="architecture_reference",
        decision_notes="Adopt the manifest/permission pattern, not the licensed connector set or vendor dependency.",
    ),
    ResourceEntry(
        "how_the_world_works",
        "How The World Works Corpus",
        "private_world_model",
        "how-the-world-works/",
        "Private worldview prior and adversarial hypothesis source.",
        ("world_model", "research_analyst", "strategy_lead"),
        validation_status="foundational_prior",
        decision_notes="Never factual evidence without live-source corroboration.",
    ),
    ResourceEntry(
        "polymarket_cli",
        "Polymarket CLI",
        "prediction_market_stack",
        "specs/qadam-general-context.md",
        "Read-only prototype reference for market discovery and price checks.",
        ("prediction_market_router", "market_pipeline"),
    ),
    ResourceEntry(
        "pmxt",
        "pmxt",
        "prediction_market_stack",
        "specs/qadam-general-context.md",
        "Unified prediction-market exchange abstraction reference.",
        ("prediction_market_router",),
    ),
    ResourceEntry(
        "polymarket_mcp_server",
        "Polymarket MCP Server",
        "prediction_market_stack",
        "specs/qadam-general-context.md",
        "Sandbox reference with demo mode, limits, and monitoring.",
        ("mcp_tools", "prediction_market_router"),
    ),
    ResourceEntry(
        "fastmcp",
        "FastMCP",
        "technical_infrastructure",
        "specs/qadam-general-context.md",
        "Tool framework candidate for exposing Qadam modules.",
        ("mcp_tools", "orchestrator"),
    ),
    ResourceEntry(
        "polyrouter_mcp",
        "Polyrouter MCP",
        "prediction_market_stack",
        "specs/qadam-general-context.md",
        "Practical guarded access reference for Polymarket and Kalshi.",
        ("prediction_market_router", "risk_agent"),
    ),
    ResourceEntry(
        "operation_epic_fury",
        "Operation Epic Fury Reconstruction",
        "osint_reference",
        "specs/qadam-general-context.md",
        "Blueprint for geopolitical monitoring, timeline replay, and OSINT fusion.",
        ("conflict_pipeline", "cockpit", "event_log"),
    ),
    ResourceEntry(
        "spy_satellite_simulator",
        "Spy Satellite Simulator",
        "osint_reference",
        "specs/qadam-general-context.md",
        "Spatial intelligence and satellite visualization reference.",
        ("physical_pipeline", "cockpit"),
    ),
    ResourceEntry(
        "rapidapi_hub",
        "RapidAPI Hub",
        "technical_infrastructure",
        "specs/qadam-general-context.md",
        "Discovery layer for niche APIs outside the current source registry.",
        ("resource_registry", "source_registry"),
    ),
    ResourceEntry(
        "preference_mcp",
        "Preference / PREF MCP",
        "supplemental_data_plane",
        "https://pref.trade/mcp",
        "Supplemental multi-source data-plane reference for status, catalog, provenance, and upstream-source context.",
        (
            "source_registry",
            "resource_registry",
            "data_veracity",
            "trust_scores",
            "research_analyst",
            "strategy_lead",
            "signal_integrity",
        ),
        validation_status="architecture_reference",
        decision_notes=(
            "Supplemental only; not source 36 and cannot affect canonical source rank unless an individual "
            "upstream source is separately promoted through the source registry."
        ),
    ),
    ResourceEntry(
        "stock_trading_reddit_reference",
        "Stock_Trading_Reddit Reference",
        "social_narrative_reference",
        "https://github.com/Sam120204/Stock_Trading_Reddit",
        "Reference pattern for ApeWisdom aggregate retail-attention collection and later Reddit OAuth enrichment ideas.",
        (
            "source_registry",
            "research_analyst",
            "strategy_lead",
            "signal_integrity",
            "fund_manager_cockpit",
        ),
        validation_status="reference_reviewed",
        production_active=False,
        decision_notes=(
            "MIT reference only; Qadam implements a native Reddit Narrative Proxy. "
            "PRAW, raw Reddit scraping, MongoDB, Streamlit, and model code are deferred "
            "and not imported into runtime."
        ),
    ),
    ResourceEntry(
        "tradingview_mcp",
        "TradingView MCP",
        "supplemental_data_plane",
        "tradingview-mcp-main/.codex-mcp.json",
        "Read-only technical-analysis context for market structure, indicators, volatility, and watchlists.",
        (
            "research_analyst",
            "strategy_lead",
            "signal_integrity",
            "fund_manager_cockpit",
        ),
        validation_status="read_only_adapter",
        decision_notes=(
            "Supplemental technical confirmation only; cannot create source quorum, trade candidates, "
            "paper orders, broker writes, quantum jobs, or live capital."
        ),
    ),
    ResourceEntry(
        "prive_x_starter",
        "PriveX Starter",
        "technical_infrastructure",
        "specs/qadam-general-context.md",
        "Execution-adapter reference for auth, subaccounts, network scope, and no automatic POST retries.",
        ("execution_registry", "risk_agent"),
        validation_status="architecture_reference",
        decision_notes="Optional later rail; live-blocked for the first-release trial.",
    ),
    ResourceEntry(
        "alpaca",
        "Alpaca",
        "technical_infrastructure",
        "specs/qadam-general-context.md",
        "Primary paper/live equities and options execution API candidate.",
        ("execution_registry", "risk_agent"),
    ),
    ResourceEntry(
        "goldman_stock_screener",
        "Goldman Sachs Stock Screener",
        "analytical_framework",
        "specs/qadam-general-context.md",
        "Candidate list and opportunity scoring before catalyst filtering.",
        ("strategy_lead", "signal_review"),
    ),
    ResourceEntry(
        "bridgewater_risk_assessment",
        "Bridgewater Risk Assessment",
        "analytical_framework",
        "specs/qadam-general-context.md",
        "Portfolio and macro risk review pattern.",
        ("risk_agent", "strategy_lead"),
    ),
    ResourceEntry(
        "citadel_technical_analysis",
        "Citadel Technical Analysis",
        "analytical_framework",
        "specs/qadam-general-context.md",
        "Technical-analysis reference for Akber's six-stage process.",
        ("strategy_lead", "signal_review"),
    ),
    ResourceEntry(
        "motionsites_ai",
        "motionsites.ai",
        "product_positioning",
        "specs/qadam-general-context.md",
        "Landing-page visual reference.",
        ("landing_page",),
    ),
    ResourceEntry(
        "qadam_intro_video",
        "Qadam Intro Video",
        "product_positioning",
        "specs/qadam-general-context.md",
        "Founding vision alignment reference.",
        ("landing_page", "fund_manager_cockpit"),
    ),
    ResourceEntry(
        "black_scholes_prediction_markets",
        "Toward Black-Scholes For Prediction Markets",
        "prediction_market_paper",
        "specs/qadam-general-context.md",
        "Probability-as-asset framing and options-style modelling.",
        ("prediction_market_router", "quant_plane"),
    ),
    ResourceEntry(
        "anatomy_of_polymarket",
        "The Anatomy Of Polymarket",
        "prediction_market_paper",
        "specs/qadam-general-context.md",
        "Empirical behaviour of Polymarket trades and participants.",
        ("prediction_market_router", "research_analyst"),
    ),
)


def resource_registry(category: str | None = None) -> list[dict[str, Any]]:
    resources = RESOURCE_ENTRIES
    if category:
        resources = tuple(resource for resource in resources if resource.category == category)
    return [resource.to_dict() for resource in resources]


def resource_detail(key: str) -> dict[str, Any]:
    for resource in RESOURCE_ENTRIES:
        if resource.key == key:
            return resource.to_dict()
    raise KeyError(f"unknown resource: {key}")


def resource_registry_summary() -> dict[str, Any]:
    by_category = Counter(resource.category for resource in RESOURCE_ENTRIES)
    production_active = [resource.key for resource in RESOURCE_ENTRIES if resource.production_active]
    return {
        "status": "ok" if not production_active else "needs_review",
        "source_document": "specs/qadam-general-context.md plus linked resource-specific references",
        "resource_count": len(RESOURCE_ENTRIES),
        "categories": dict(sorted(by_category.items())),
        "production_active_count": len(production_active),
        "production_active": production_active,
        "boundary": "Non-live references guide architecture, research, and UX; they are not live data feeds.",
    }
