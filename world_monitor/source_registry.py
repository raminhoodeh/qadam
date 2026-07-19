"""Source registry built from the Qadam specification documents.

The registry intentionally records unresolved spec conflicts instead of hiding them.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable


EXPECTED_SOURCE_COUNT = 35
DECISION_SOURCE_COVERAGE_SCHEMA_VERSION = 1


@dataclass(frozen=True)
class SourceSpec:
    key: str
    name: str
    pipeline: str
    tier: int
    tool_name: str
    auth: str
    endpoints: tuple[str, ...]
    cadence: str
    rate_limit: str
    env_vars: tuple[str, ...] = ()
    status: str = "ready_to_build"
    notes: str = ""
    selection_status: str = "selected"
    operator_action: str = "none"


SOURCE_SPECS: tuple[SourceSpec, ...] = (
    SourceSpec(
        "acled",
        "ACLED API",
        "conflict",
        1,
        "world_monitor_conflict_acled",
        "OAuth 2.0",
        ("https://api.acleddata.com/acled/read",),
        "hourly",
        "500 requests/day free tier; budget 24/day",
        ("ACLED_EMAIL", "ACLED_PASSWORD", "ACLED_ACCESS_TOKEN", "ACLED_REFRESH_TOKEN"),
        "ready_to_port",
        "World Monitor has token management patterns.",
    ),
    SourceSpec(
        "ucdp",
        "UCDP API",
        "conflict",
        4,
        "world_monitor_conflict_ucdp",
        "none",
        ("https://ucdpapi.pcr.uu.se/api/gedevents/23.1",),
        "daily",
        "10 requests/hour recommended",
        status="adapter_live_optional",
        notes="Promoted as a read-only public historical conflict/base-rate adapter.",
    ),
    SourceSpec(
        "gdelt",
        "GDELT Project API",
        "conflict",
        2,
        "world_monitor_conflict_gdelt",
        "none",
        ("https://api.gdeltproject.org/api/v2/doc/doc",),
        "15 minutes",
        "recommend <= 4 requests/minute",
        status="adapter_live_optional",
        notes="Promoted into Qadam as a read-only adapter with sample mode, raw archive, and degraded-state handling.",
    ),
    SourceSpec(
        "oref",
        "Oref API",
        "conflict",
        1,
        "world_monitor_conflict_oref",
        "none",
        ("https://www.oref.org.il/WarningMessages/alert/alerts.json",),
        "5 seconds in spec",
        "no documented limit; spec says <= 12 requests/minute",
        ("OREF_PROXY_AUTH",),
        "adapter_live_optional",
        "Promoted into Qadam as a read-only adapter; cadence remains conservative and live failures degrade cleanly.",
    ),
    SourceSpec(
        "conflict_tracker",
        "Conflict Tracker",
        "conflict",
        1,
        "world_monitor_conflict_tracker",
        "internal",
        ("internal://conflict_tracker",),
        "derived",
        "n/a",
        status="adapter_live_optional",
        notes="Promoted as a read-only derived adapter fusing ACLED/GDELT context; no external credential required.",
    ),
    SourceSpec(
        "nasa_firms",
        "NASA FIRMS",
        "physical",
        1,
        "world_monitor_physical_nasa_firms",
        "API key",
        ("https://firms.modaps.eosdis.nasa.gov/api/area/csv/{API_KEY}/VIIRS_SNPP_NRT/{bbox}/{days}",),
        "3 hours",
        "250 requests/day free tier; budget 8/day",
        ("NASA_FIRMS_API_KEY",),
        "adapter_live_requires_key",
        "Promoted into Qadam as a read-only bbox-first adapter; live mode is credential-gated.",
    ),
    SourceSpec(
        "aviationstack",
        "Aviationstack Flight Data",
        "physical",
        2,
        "world_monitor_physical_aviationstack",
        "API key",
        (
            "https://api.aviationstack.com/v1/flights",
            "https://api.aviationstack.com/v1/airports",
            "https://api.aviationstack.com/v1/airlines",
            "https://api.aviationstack.com/v1/routes",
        ),
        "5 minutes",
        "plan dependent; budget 288/day only if quota permits",
        ("AVIATIONSTACK_API_KEY",),
        "adapter_live_requires_key",
        "Provider update: Aviationstack replaces Wingbits as the v1 flight-data adapter for Qadam.",
    ),
    SourceSpec(
        "ais_maritime",
        "AIS Maritime",
        "physical",
        2,
        "world_monitor_physical_ais",
        "API key",
        (
            "wss://stream.aisstream.io/v0/stream",
            "https://api.spire.com/v3/analytics/vessel",
            "https://services.marinetraffic.com/api/exportvessels/v:8",
        ),
        "15 minutes",
        "provider dependent; budget 96/day for polling adapters",
        ("SPIRE_API_KEY", "MARINETRAFFIC_API_KEY", "AISSTREAM_API_KEY"),
        "adapter_live_requires_key",
        "Provider decision recorded: AISStream is the v1 read-only MVP path; Spire and MarineTraffic remain paid fallback candidates.",
    ),
    SourceSpec(
        "arcgis_usace",
        "ArcGIS / USACE Geospatial",
        "physical",
        4,
        "world_monitor_physical_arcgis",
        "none or ArcGIS token",
        ("https://services.arcgis.com/P3ePLMYs2RVChkJx/arcgis/rest/services/",),
        "daily",
        "public layers no limit",
        status="adapter_live_optional",
        notes="Promoted as a read-only public geospatial/infrastructure adapter.",
    ),
    SourceSpec(
        "space_track_celestrak",
        "Space-Track / CelesTrak TLEs",
        "physical",
        4,
        "world_monitor_physical_space_track",
        "Space-Track account; CelesTrak public fallback",
        (
            "https://www.space-track.org/basicspacedata/query/",
            "https://celestrak.org/NORAD/elements/gp.php?GROUP=stations&FORMAT=json",
        ),
        "6 hours",
        "Space-Track 300 requests/hour; CelesTrak public fallback budget 4/day",
        ("SPACE_TRACK_USERNAME", "SPACE_TRACK_PASSWORD"),
        "adapter_live_optional",
        "Provider decision recorded: Space-Track remains authenticated primary; CelesTrak GP JSON is the public fallback/smoke path.",
    ),
    SourceSpec(
        "gps_jamming",
        "GPS Jamming Monitors",
        "physical",
        4,
        "world_monitor_physical_gps_jamming",
        "none",
        ("https://gpsjam.org/api",),
        "30 minutes",
        "no documented limit; budget 48/day",
        status="adapter_live_optional",
        notes="Promoted as a read-only public GPS interference context adapter.",
    ),
    SourceSpec(
        "internet_outage",
        "Internet Outage / IODA",
        "physical",
        4,
        "world_monitor_physical_internet_outage",
        "none",
        ("https://ioda.inetintel.cc.gatech.edu/api",),
        "30 minutes",
        "no documented limit",
        status="adapter_live_optional",
        notes="Promoted as a read-only public internet-outage context adapter.",
    ),
    SourceSpec(
        "fred",
        "FRED API",
        "macro",
        2,
        "world_monitor_macro_fred",
        "optional API key; public CSV fallback",
        (
            "https://api.stlouisfed.org/fred/series/observations",
            "https://fred.stlouisfed.org/graph/fredgraph.csv",
        ),
        "6 hours or daily",
        "120 requests/minute",
        ("FRED_API_KEY",),
        "adapter_live_optional",
        "Promoted into Qadam as a read-only macro adapter with public CSV fallback when no API key is configured.",
    ),
    SourceSpec(
        "bls",
        "BLS API",
        "macro",
        3,
        "world_monitor_macro_bls",
        "API key",
        ("https://api.bls.gov/publicAPI/v2/timeseries/data/",),
        "daily or event-driven",
        "500 queries/day registered",
        ("BLS_API_KEY",),
        "ready_to_build",
        "FRED equivalents should be fallback.",
    ),
    SourceSpec(
        "bis",
        "BIS Statistics",
        "macro",
        3,
        "world_monitor_macro_bis",
        "none",
        ("https://stats.bis.org/api/v1/data/",),
        "weekly",
        "no documented limit",
        status="adapter_live_optional",
        notes="Promoted as a read-only public macro/liquidity adapter.",
    ),
    SourceSpec(
        "ecb",
        "ECB Data Portal",
        "macro",
        3,
        "world_monitor_macro_ecb",
        "none",
        ("https://data-api.ecb.europa.eu/service/data/",),
        "daily",
        "budget 10/day",
    ),
    SourceSpec(
        "un_comtrade",
        "UN Comtrade API",
        "macro",
        3,
        "world_monitor_macro_un_comtrade",
        "API key",
        ("https://comtradeapi.un.org/data/v1/get/",),
        "weekly",
        "100 requests/hour free tier",
        ("COMTRADE_API_KEY",),
    ),
    SourceSpec(
        "usgs",
        "USGS",
        "macro",
        3,
        "world_monitor_macro_usgs",
        "none",
        (
            "https://minerals.usgs.gov/minerals/pubs/mcs/",
            "https://mrdata.usgs.gov/api/",
            "https://earthquake.usgs.gov/fdsnws/event/1/query",
        ),
        "weekly or event-driven",
        "no documented limit",
        status="adapter_live_optional",
        notes=(
            "Scope decision recorded: USGS is a mineral/supply-chain context source for commodities and defence; "
            "the public earthquake API is the event-driven physical-risk adapter path."
        ),
    ),
    SourceSpec(
        "unusual_whales",
        "UnusualWhales",
        "market",
        1,
        "world_monitor_market_unusual_whales",
        "API key",
        ("https://api.unusualwhales.com/api/option-trades/flow-alerts",),
        "5 minutes during market hours",
        "plan dependent; budget 200/day",
        (),
        "intentionally_disabled",
        (
            "Live source-quorum use remains intentionally disabled. A separate read-only "
            "historical research adapter can collect options-flow, market-tide, options-volume, "
            "and dark-pool features during the trial through 2026-07-21; captured features remain "
            "available for later backtests in archive-only mode and have no trading authority."
        ),
        "optional_disabled",
        "reselect_unusual_whales_before_requesting_credentials",
    ),
    SourceSpec(
        "polymarket",
        "Polymarket",
        "market",
        1,
        "world_monitor_market_polymarket",
        "none for public market data",
        ("https://clob.polymarket.com/markets",),
        "5 minutes",
        "no documented limit",
        status="adapter_live_optional",
        notes="Qadam uses the public CLOB/orderbook path as the v1 read-only adapter; Gamma remains discovery-only context.",
    ),
    SourceSpec(
        "kalshi",
        "Kalshi / OddsPipe",
        "market",
        1,
        "world_monitor_market_kalshi",
        "OddsPipe API key; direct Kalshi API key only if region/account later allows",
        (
            "https://oddspipe.com/v1/spreads",
            "https://oddspipe.com/v1/markets",
            "https://oddspipe.com/v1/markets/search",
            "https://trading-api.kalshi.com/trade-api/v2/markets",
        ),
        "1-5 minutes",
        "OddsPipe free tier 100 requests/minute; direct Kalshi limit provider-dependent",
        ("ODDSPIPE_API_KEY", "KALSHI_API_KEY", "KALSHI_API_SECRET"),
        "adapter_live_via_oddspipe",
        (
            "Kalshi direct signup is region/identity gated for Ramin. OddsPipe is the selected v1 read-only "
            "coverage route for normalized Kalshi and Polymarket markets, OHLCV, and cross-platform spreads."
        ),
        operator_action="use_oddspipe_for_prediction_market_coverage",
    ),
    SourceSpec(
        "hyperliquid",
        "Hyperliquid Perps",
        "market",
        4,
        "world_monitor_market_hyperliquid",
        "none",
        ("https://api.hyperliquid.xyz/info",),
        "15 minutes",
        "no documented limit; budget 96/day",
        status="adapter_live_optional",
        notes="Promoted as a read-only public crypto/perps context adapter; no execution authority.",
    ),
    SourceSpec(
        "alpaca",
        "Alpaca Markets API",
        "market",
        1,
        "world_monitor_market_alpaca",
        "API key and secret",
        (
            "https://data.alpaca.markets/v2/",
            "https://paper-api.alpaca.markets/v2/account",
            "https://api.alpaca.markets/v2/",
        ),
        "real-time stream plus REST fallback",
        "200 requests/minute data API",
        ("ALPACA_API_KEY", "ALPACA_API_SECRET"),
        "adapter_live_broker_split",
        "Paper execution exists separately; this registry row is the read-only account/market-data mirror contract.",
    ),
    SourceSpec(
        "rapidapi",
        "RapidAPI Hub",
        "market",
        3,
        "world_monitor_market_rapidapi",
        "API key",
        ("https://rapidapi.com/hub",),
        "varies",
        "per-source plan limits",
        (),
        "intentionally_disabled",
        (
            "RapidAPI is a marketplace, not a canonical source. Keep disabled until a specific "
            "RapidAPI-backed provider is selected."
        ),
        "optional_disabled",
        "select_specific_rapidapi_provider_before_activation",
    ),
    SourceSpec(
        "coinglass",
        "Coinglass",
        "market",
        4,
        "world_monitor_market_coinglass",
        "API key",
        ("https://open-api.coinglass.com/public/v2/",),
        "15 minutes",
        "30 requests/min free; 300/min pro",
        (),
        status="needs_adapter",
        notes=(
            "Provider candidate for crypto/perps context only. It is not selected for the current "
            "paper-trading core and should not appear as a missing credential."
        ),
        selection_status="not_selected",
        operator_action="decide_crypto_perps_role_before_requesting_credentials",
    ),
    SourceSpec(
        "chainlink",
        "Chainlink Price Feeds",
        "market",
        4,
        "world_monitor_market_chainlink",
        "Ethereum RPC endpoint",
        ("https://eth-mainnet.g.alchemy.com/v2/{KEY}",),
        "10 minutes",
        "Alchemy free tier budget about 50/day",
        (),
        status="needs_adapter",
        notes=(
            "Public oracle/price-feed context candidate. Needs a read-only adapter decision before "
            "any RPC credential is requested."
        ),
        selection_status="not_selected",
        operator_action="build_public_price_feed_adapter_before_requesting_rpc",
    ),
    SourceSpec(
        "bookmap",
        "Bookmap / Order Flow",
        "market",
        4,
        "world_monitor_market_bookmap",
        "local Bookmap account and bridge",
        ("ws://localhost:8765/bookmap",),
        "real-time",
        "local process",
        ("BOOKMAP_BRIDGE_URL",),
        status="local_bridge",
        notes="Read-only local bridge contract; Qadam shows it connected only when the local bridge is configured/running.",
        operator_action="configure_bookmap_readonly_local_bridge",
    ),
    SourceSpec(
        "rss",
        "RSS / Atom Feeds",
        "social",
        2,
        "world_monitor_social_rss",
        "none or publisher subscription",
        (
            "https://feeds.reuters.com/reuters/businessNews",
            "https://rsshub.app/apnews/topics/business",
            "https://feeds.bloomberg.com/markets/news.rss",
        ),
        "5 minutes",
        "public feeds generally no hard limit",
        status="adapter_live_optional",
        notes="Promoted into Qadam as a read-only narrative adapter with feed validation, keyword filtering, and fallback feeds.",
    ),
    SourceSpec(
        "telegram",
        "Telegram APIs / Scrapers",
        "social",
        3,
        "world_monitor_social_telegram",
        "Bot API token and MTProto session",
        ("https://api.telegram.org/bot{TOKEN}/",),
        "real-time or polling",
        "Bot API 30 messages/second; MTProto flood limits",
        ("TELEGRAM_BOT_TOKEN", "TELEGRAM_API_ID", "TELEGRAM_API_HASH", "TELEGRAM_SESSION"),
        "ready_to_port",
    ),
    SourceSpec(
        "twitter_x",
        "Twitter / X API v2",
        "social",
        2,
        "world_monitor_social_twitter",
        "Bearer token",
        ("https://api.twitter.com/2/tweets/search/recent",),
        "15 minutes",
        "Basic: 60 requests/15 minutes",
        ("X_BEARER_TOKEN",),
    ),
    SourceSpec(
        "reddit",
        "Reddit Narrative Proxy / Reddit API",
        "social",
        3,
        "world_monitor_social_reddit",
        "none for ApeWisdom aggregate; OAuth 2.0 optional later",
        (
            "https://apewisdom.io/api/v1.0/filter/all-stocks/page/{page}",
            "https://apewisdom.io/api/v1.0/filter/all-crypto/page/{page}",
            "https://apewisdom.io/api/v1.0/filter/4chan/page/{page}",
            "https://oauth.reddit.com/r/{subreddit}/new",
        ),
        "20-30 minutes",
        "ApeWisdom public aggregate; Reddit OAuth 100 requests/min authenticated if later approved",
        ("REDDIT_CLIENT_ID", "REDDIT_CLIENT_SECRET"),
        status="adapter_live_via_reddit_narrative_proxy",
        notes=(
            "Selected narrative source is covered by the no-key Reddit Narrative Proxy using "
            "ApeWisdom aggregate attention data. Reddit OAuth remains an optional later enrichment "
            "path for raw post/comment access if approved. Proxy evidence is read-only, "
            "secondary-only, and cannot create trades or satisfy source quorum alone."
        ),
        operator_action="oauth_optional_upgrade_pending",
    ),
    SourceSpec(
        "sec_edgar",
        "SEC EDGAR API",
        "social",
        3,
        "world_monitor_social_sec_edgar",
        "none; User-Agent required",
        ("https://efts.sec.gov/LATEST/search-index", "https://data.sec.gov/submissions/CIK{cik}.json"),
        "30 minutes",
        "10 requests/second",
        ("SEC_USER_AGENT",),
    ),
    SourceSpec(
        "stock_act",
        "Capitol Trades / STOCK Act Filings",
        "social",
        3,
        "world_monitor_social_stock_act",
        "Apify API token",
        ("https://api.apify.com/v2/actors/saswave~capitol-trades-scraper/run-sync-get-dataset-items",),
        "daily or event-driven",
        "Apify actor pricing; budget 1 page per validation poll",
        ("CAPITOL_TRADES_API_KEY",),
        status="adapter_live_via_apify",
        notes=(
            "Provider direction updated: use the Apify Capitol Trades Scraper actor for v1 congressional trade "
            "disclosures, not UnusualWhales. The adapter remains read-only and cross-validates against price action "
            "and SEC context before research use."
        ),
        operator_action="maintain_capitol_trades_apify_key",
    ),
    SourceSpec(
        "patents",
        "Patent Filings",
        "social",
        4,
        "world_monitor_social_patents",
        "none for USPTO; EPO may require registration",
        ("https://api.patentsview.org/patents/query", "https://ops.epo.org/3.2/rest-services/"),
        "weekly",
        "PatentsView no limit; EPO OPS 4,000/week",
        status="adapter_live_optional",
        notes="Promoted as a read-only public patent/intellectual-property context adapter.",
    ),
    SourceSpec(
        "github",
        "GitHub API",
        "social",
        4,
        "world_monitor_social_github",
        "read-only PAT",
        ("https://api.github.com/",),
        "daily",
        "5,000 requests/hour authenticated",
        (),
        status="needs_adapter",
        notes=(
            "Optional technology/supply-chain context candidate. Needs a specific signal role and "
            "read-only adapter before any GitHub token is requested."
        ),
        selection_status="not_selected",
        operator_action="decide_github_signal_role_before_requesting_credentials",
    ),
)


def get_source(key: str) -> SourceSpec:
    for source in SOURCE_SPECS:
        if source.key == key:
            return source
    raise KeyError(f"Unknown source key: {key}")


def sources_by_tier(tier: int) -> tuple[SourceSpec, ...]:
    return tuple(source for source in SOURCE_SPECS if source.tier == tier)


def sources_by_pipeline(pipeline: str) -> tuple[SourceSpec, ...]:
    return tuple(source for source in SOURCE_SPECS if source.pipeline == pipeline)


def unresolved_sources() -> tuple[SourceSpec, ...]:
    return tuple(
        source
        for source in SOURCE_SPECS
        if source.status in {"needs_clarity", "needs_choice", "needs_new_adapter"}
    )


def source_registry_action_category(source: SourceSpec) -> str:
    if source.status == "local_bridge":
        return "local_bridge_required"
    if source.status == "intentionally_disabled":
        return "intentionally_disabled"
    if source.status == "adapter_live_via_reddit_narrative_proxy":
        return "no_user_action"
    if source.status in {"needs_adapter", "needs_new_adapter"}:
        return "needs_adapter"
    if source.status in {"needs_clarity", "needs_choice"}:
        return "provider_decision_required"
    if source.env_vars:
        return "needs_credentials"
    return "no_user_action"


def missing_environment_variables(environ: dict[str, str]) -> dict[str, tuple[str, ...]]:
    missing: dict[str, tuple[str, ...]] = {}
    for source in SOURCE_SPECS:
        required = tuple(name for name in source.env_vars if not environ.get(name))
        if required:
            missing[source.key] = required
    return missing


def iter_external_sources() -> Iterable[SourceSpec]:
    return (source for source in SOURCE_SPECS if source.auth != "internal")


def canonical_source_keys() -> tuple[str, ...]:
    return tuple(source.key for source in SOURCE_SPECS)


def _float(value: Any) -> float:
    try:
        return float(value or 0.0)
    except (TypeError, ValueError):
        return 0.0


def canonical_decision_source_coverage(
    *,
    required_source_groups: Iterable[str] = (),
    source_weights: dict[str, Any] | None = None,
    coverage_scope: str = "strategy_decision",
) -> dict[str, Any]:
    """Return the public-safe source-coverage contract for a decision artifact."""

    canonical = canonical_source_keys()
    canonical_set = set(canonical)
    required = tuple(
        dict.fromkeys(
            str(source).strip()
            for source in required_source_groups
            if str(source).strip()
        )
    )
    missing_required = tuple(source for source in required if source not in canonical_set)
    missing_canonical = tuple(
        source
        for source in canonical
        if source not in canonical_set
    )
    unresolved = tuple(source.key for source in unresolved_sources())
    weights = source_weights or {}
    weighted_keys = tuple(
        sorted(str(source).strip() for source in weights if str(source).strip())
    )
    weighted_key_set = set(weighted_keys)
    zero_weight_required = tuple(
        sorted(
            source
            for source in required
            if source in weights and _float(weights.get(source)) <= 0.0
        )
    )
    required_weights_complete = bool(required) and weighted_key_set == set(required)
    source_weight_sum = round(sum(_float(value) for value in weights.values()), 4)
    source_weights_normalized = (
        0.995 <= source_weight_sum <= 1.005 if weights else None
    )
    all_canonical_sources_considered = (
        len(canonical) == EXPECTED_SOURCE_COUNT
        and not missing_canonical
        and not unresolved
    )
    decision_source_usage_complete = (
        all_canonical_sources_considered
        and not missing_required
        and (not required or (required_weights_complete and not zero_weight_required))
    )
    return {
        "schema_version": DECISION_SOURCE_COVERAGE_SCHEMA_VERSION,
        "coverage_scope": coverage_scope,
        "canonical_source_count": len(canonical),
        "expected_canonical_source_count": EXPECTED_SOURCE_COUNT,
        "canonical_source_keys": list(canonical),
        "missing_canonical_source_keys": list(missing_canonical),
        "unresolved_canonical_source_keys": list(unresolved),
        "all_canonical_sources_considered": all_canonical_sources_considered,
        "required_source_groups": list(required),
        "required_source_group_count": len(required),
        "missing_required_source_groups": list(missing_required),
        "weighted_required_source_groups": list(weighted_keys),
        "weighted_required_source_count": len(weighted_keys),
        "required_source_weights_complete": required_weights_complete,
        "zero_weight_required_source_groups": list(zero_weight_required),
        "source_weight_sum": source_weight_sum,
        "source_weights_normalized": source_weights_normalized,
        "decision_source_usage_complete": decision_source_usage_complete,
        "source_quorum_bypass_allowed": False,
        "supplemental_source_bypass_allowed": False,
        "decision_use_policy": (
            "Every strategy decision must consider the full canonical source registry; "
            "strategy-specific required source groups receive weights, while Yahoo Finance, "
            "Preference/PREF MCP, TradingView MCP, private priors, and Q-CTRL remain "
            "supplemental unless a later audited promotion changes the registry."
        ),
    }
