# Qadam API Specs

This document is the working credential and API inventory for Qadam.

For the operational checklist to acquire keys in the right order, use `docs/qadam-api-key-acquisition-plan.md`.

Source hierarchy:

1. `specs/qadam-specs.md` is the product source of truth.
2. `specs/Qadam - World Monitor Integration Reference.md` gives endpoint-level integration detail.
3. `world_monitor/source_registry.py` is the canonical current 35-source implementation registry.
4. `world-monitor/` is a pasted reference codebase. It is useful for patterns and optional providers, but it is not Qadam's canonical architecture.
5. `yahoo-finance-api/` is a local `yfinance` reference checkout. It is useful for supplemental market confirmation, but it is not a broker, not an execution venue, and not automatically a canonical 36th source.
6. Preference/PREF MCP is a registered supplemental multi-source data plane. It can enrich discovery and context across prediction markets and real-world signals, but it is not automatically a canonical source and must be gated through `docs/qadam-preference-mcp-integration-plan.md`.

Rule: keep all real credentials out of Git, docs, screenshots, and chat. This file only uses placeholders.

## 1. Credential Storage Rule

All API keys, tokens, private keys, account credentials, webhook secrets, and broker credentials belong in local runtime storage:

```bash
data/runtime/qadam-secrets.env
```

That file must stay gitignored and local to the MacBook. Public dashboards may show credential status only as `configured`, `missing`, `deferred`, or `blocked`, never the variable name paired with a real value.

If any real credential appears in chat, Git, a screenshot, or a public dashboard, treat it as exposed and rotate it at the provider before using it again.

## 1A. Current Phase 1 Adapter Status

Implemented locally:

- Dedicated read-only adapters: GDELT, Oref, NASA FIRMS, FRED, RSS.
- Generic Phase 1 read-only adapters: ACLED, UnusualWhales, Polymarket, Kalshi, Alpaca, AIS Maritime, Wingbits, BLS, ECB, UN Comtrade, SEC EDGAR, Reddit, X, Telegram.
- Adapter coverage: 19 promoted source contracts out of the 35-source registry.
- Every promoted adapter has sample mode, masked credential status, raw payload archival, normalized event output, degraded-state handling, and no signal/order authority.
- `scripts/check_phase1_live_source_hardening.py` now validates all promoted sources one by one and records the result in the ignored local report `data/runtime/phase1_live_source_validation.json`.
- `scripts/check_supplied_credentials.py` validates the currently supplied Batch A credentials and local model settings in one read-only pass, writing the ignored local report `data/runtime/supplied_credential_validation.json`.
- `scripts/refresh_acled_token.py --write --validate-read` refreshes ACLED OAuth tokens into the ignored local secret file, appends the ignored local report `data/runtime/acled_token_refresh.jsonl`, and keeps token values out of stdout, docs, Event Log payloads, and Git.
- Historical backfill planning and local sample-run records exist for ACLED, GDELT, NASA FIRMS, FRED, RSS, Polymarket, Kalshi, Alpaca, BLS, ECB, UN Comtrade, and SEC EDGAR.
- Trust Score seed covers all 35 sources, but scores are priors until replaced by backtests and live observations.
- Postgres/Timescale durable ingestion is coded as a local contract and is live only when the local database service is running. Use `scripts/start_postgres_timescale_ingestion.sh` for the Postgres-only bootstrap and `scripts/check_postgres_timescale_replay.py --require-full-source-coverage` to verify replayable 35-source coverage.
- Yahoo Finance / yfinance is accepted as a supplemental read-only market-data capability with classification `accepted_supplemental_pending_live_dependencies`. It has a dormant Qadam wrapper with sample mode and guarded live mode, but it should not be consumed by Phase 2 or Phase 3 until live dependencies, public-safe cockpit status, and corroboration policy checks pass.
- Preference/PREF MCP is a registered supplemental read-only multi-source capability with status/catalog/sample/provenance/domain-pack/shadow-context checks first, not a canonical-source promotion. PREF-1 identity/status gating now exists in `orchestrator/preference_mcp_identity.py` and `scripts/check_preference_mcp_identity.py`; PREF-2 catalog/schema gating now exists in `orchestrator/preference_mcp_catalog.py` and `scripts/check_preference_tool_catalog.py`; PREF-3 offline sample adapter scaffolding now exists in `orchestrator/preference_mcp_adapter.py` and `scripts/check_preference_mcp_adapter.py`; PREF-4 status/catalog-only live smoke gating now exists behind `scripts/check_preference_mcp_adapter.py --live-status-only` and `--live-catalog-only`; PREF-5 provenance/source-quorum policy now exists in `orchestrator/preference_mcp_provenance.py` and `scripts/check_preference_provenance.py`; PREF-6 Resource Registry, Data Veracity, and Trust Score policy now keeps Preference as `supplemental_data_plane` with no canonical rank impact; PREF-7 domain-pack mapping now exists in `orchestrator/preference_mcp_domain_packs.py` and `scripts/check_preference_domain_packs.py`; PREF-8 shadow-intelligence enrichment now exists in `orchestrator/preference_mcp_shadow_context.py` and `scripts/check_preference_shadow_context.py`; PREF-9 cockpit/Mission Control visibility now exists in `orchestrator/cockpit_status.py`, `landing-page-repo/dashboard.js`, `scripts/check_cockpit_status.py`, `scripts/check_dashboard_renderer.js`, and `scripts/check_dashboard_mission_control.js`; PREF-10 Phase 4 re-manifestation now exists in `orchestrator/phase4_candidate_strategy_universe.py`, `orchestrator/phase4_manifested_strategy.py`, `scripts/check_phase4_candidate_strategy_universe.py`, `scripts/check_phase4_manifested_strategy.py`, and `docs/qadam-manifested-strategy.md`; PREF-11 Q4-10/Q4-12 approval and certification gating now exists in `orchestrator/phase4_approval_record.py`, `orchestrator/phase4_certification.py`, `scripts/check_phase4_approval_record.py`, and `scripts/check_phase4_certification.py`; PREF-12 upstream source-promotion decisions now exist in `orchestrator/preference_mcp_source_promotion.py` and `scripts/check_preference_source_promotion.py`. Current local live status is fail-closed until `PREFERENCE_MCP_ENABLED=true` and a local `PREFERENCE_API_KEY` are deliberately configured. Deterministic Preference sample context may be consumed by Phase 2, shown in the public cockpit, reflected in Phase 4 strategy manifestation, verified by Phase 4 certification, and scored by Data Veracity/Trust Score only as supplemental challenge/context; it cannot satisfy source quorum, create trade candidates, approve risk, route execution, create paper orders, write brokers, call quantum providers, enable schedulers, promote canonical sources, change canonical source count, or enable live capital.
- Phase 4 data-source closeout now requires Q4-10 approval scope and Q4-12 certification to validate PREF-12 source-promotion status: zero promoted Preference upstreams, canonical source count 35, `preference_mcp_source_36=False`, and Yahoo Finance still `supplemental_market_confirmation_only`.

Not yet proven live:

- Any credential-gated source without a configured local secret remains blocked as `missing_credentials`.
- Any public or configured source that fails a read-only live check is kept as `degraded` with the provider error class preserved locally.
- No adapter may promote signal confidence or create paper/live orders by itself.

Current supplied-credential snapshot as of 2026-05-19:

- Live in read-only credential validation: NASA FIRMS, FRED, Alpaca paper account mirror, Telegram bot status, Gemini model-list access, and LM Studio Gemma 4 E4B model-list access.
- Alpaca paper mirror status: `scripts/check_alpaca_paper_mirror.py --live` uses only GET endpoints for `/account`, `/positions`, `/orders`, and `/account/portfolio/history`; it writes sanitized mirror state locally and exposes no broker-write route.
- Degraded in read-only credential validation: ACLED. ACLED is locally configured and refresh automation succeeded on 2026-05-19, but the post-refresh read endpoint still returned HTTP 403, so ACLED needs entitlement/account-scope confirmation before it can count as durable live.
- Missing or deferred from this credential batch: UnusualWhales remains a useful missing Batch A key; Kalshi remains deferred due to current location/account eligibility.
- Configured in the local ignored secret file: NASA FIRMS, Alpaca paper, ACLED email/password/access token/refresh token, FRED, Q-CTRL, Telegram bot token/username/private target/group target, Gemini/Google model keys, and LM Studio settings.
- ACLED refresh-token automation exists, but ACLED remains degraded until the refreshed token is accepted by the data-read endpoint or entitlement/account-scope is confirmed.
- Telegram remains outbound-only and cannot trigger execution.

## 2. API Onboarding Batches

The full inventory is large. Qadam should add keys in batches so the system remains testable.

### Batch A - First Data Spine

These unlock the most important Phase 1 read-only data adapters and first paper-trading rail:

| Provider | Placeholders | Why It Matters |
| --- | --- | --- |
| NASA FIRMS | `NASA_FIRMS_API_KEY` | Thermal anomalies near refineries, ports, logistics corridors, military zones, and commodity infrastructure. |
| ACLED | `ACLED_EMAIL`, `ACLED_PASSWORD`, `ACLED_ACCESS_TOKEN`, `ACLED_REFRESH_TOKEN` | Conflict and protest event data for escalation monitoring. |
| UnusualWhales | `UNUSUAL_WHALES_API_KEY` | Options flow, dark pool, gamma, congressional trading, and institutional confirmation. |
| Kalshi | `KALSHI_API_KEY`, `KALSHI_API_SECRET` | Prediction-market monitoring and later guarded paper/live venue path. |
| Alpaca paper | `ALPACA_API_KEY`, `ALPACA_API_SECRET`, `ALPACA_PAPER=true` | Paper account mirror and guarded £100,000 paper proof execution. |
| Gemini | `GEMINI_API_KEY` | Frontier LLM Strategy Lead / deep research packets. |
| Supabase | `NEXT_PUBLIC_SUPABASE_URL`, `NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY`, `SUPABASE_SECRET_KEY` | Founding Fund Manager cockpit auth. |
| Telegram bot | `TELEGRAM_BOT_TOKEN`, `TELEGRAM_BOT_USERNAME`, `TELEGRAM_DEFAULT_CHAT_ID`, `TELEGRAM_GROUP_CHAT_ID` | Outbound member communications, alerts, and delivery status. |

### Batch B - Market, Macro, And Social Confirmation

| Provider | Placeholders | Why It Matters |
| --- | --- | --- |
| FRED | `FRED_API_KEY` | Official macro regime data; public CSV fallback exists. |
| Yahoo Finance / yfinance | none by default; optional local runtime controls | Supplemental OHLCV, volume, options-chain, market-status, quote-search, sector, screener, and news context for market confirmation. Not a broker and not a canonical source until explicitly promoted. |
| Preference / PREF MCP | `PREFERENCE_API_KEY` plus local runtime controls | Supplemental multi-source MCP data plane for prediction markets, orderbooks, weather, vessel/aircraft/satellite context, SEC filings, smart wallets, news, macro, and sports lines. Status/catalog/sample/provenance only first; no paid tools, execution, fills, receipts, reconciliation, broker writes, source-quorum credit, or canonical promotion without explicit approval. |
| BLS | `BLS_API_KEY` | CPI, PPI, labour, and inflation surprise context. |
| UN Comtrade | `COMTRADE_API_KEY` | Trade-flow and supply-chain rerouting context. |
| X API v2 | `X_BEARER_TOKEN` | High-velocity narrative and breaking-news triage. |
| Reddit | `REDDIT_CLIENT_ID`, `REDDIT_CLIENT_SECRET` | Retail attention and narrative saturation checks. |
| Telegram MTProto | `TELEGRAM_API_ID`, `TELEGRAM_API_HASH`, `TELEGRAM_SESSION` | OSINT channel ingestion, separate from the member bot. |
| AIS provider | `AISSTREAM_API_KEY`, `SPIRE_API_KEY`, `MARINETRAFFIC_API_KEY` | Vessel movements, port congestion, chokepoints, tanker routes. |
| Wingbits | `WINGBITS_API_KEY` | ADS-B aircraft enrichment and unusual aviation movements. |

### Batch C - Physical, Crypto, And Specialist Feeds

| Provider | Placeholders | Why It Matters |
| --- | --- | --- |
| Space-Track | `SPACE_TRACK_USERNAME`, `SPACE_TRACK_PASSWORD` | Satellite/TLE monitoring; CelesTrak remains public fallback. |
| Coinglass | `COINGLASS_API_KEY` | Funding, liquidation, open-interest, and crypto derivatives context. |
| Chainlink / RPC | `ETH_RPC_URL` | On-chain price-feed cross-checking. |
| RapidAPI | `RAPIDAPI_KEY` | Fallback marketplace for niche sources not covered by direct integrations. |
| GitHub | `GITHUB_TOKEN` | Developer/release-cycle signal for semiconductors and software-linked equities. |
| EPO OPS | `EPO_OPS_CONSUMER_KEY`, `EPO_OPS_CONSUMER_SECRET` | Patent filings where public USPTO/PatentsView is not enough. |
| ArcGIS | `ARCGIS_API_TOKEN` | Optional token for non-public ArcGIS layers. |
| SEC EDGAR | `SEC_USER_AGENT` | Required identity string for responsible SEC data access. |

### Batch D - Model, Quantum, Alerts, And Later Execution

| Provider | Placeholders | Why It Matters |
| --- | --- | --- |
| LM Studio local LLM | `LM_STUDIO_BASE_URL`, `LM_STUDIO_MODEL` | Local Research Analyst triage; usually no API key. |
| Q-CTRL Fire Opal | `QCTRL_API_KEY`, `QCTRL_ORGANIZATION_SLUG` when required | Mandatory quantum consultation provider for paper-live parity; Qadam defaults the organization slug to `qadam` when no secret override is present. |
| IBM Quantum | `IBM_QUANTUM_TOKEN`, `IBM_QUANTUM_INSTANCE` | Primary future hardware backend through Fire Opal on IBM Quantum / Qiskit Runtime. |
| AWS Braket | `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, `AWS_REGION` | Secondary future quantum backend. |
| TradingView alerts | `TRADINGVIEW_WEBHOOK_SECRET`, `TRADINGVIEW_ALERT_RECEIVER_URL` | Paid-account alert intake. TradingView does not provide a normal retail market-data API key. |
| Polymarket execution | `POLYMARKET_PRIVATE_KEY`, `POLYMARKET_FUNDER_ADDRESS`, `POLYMARKET_CHAIN_ID` | Later guarded prediction-market execution only; public market data needs no key. |
| Polyrouter / pmxt | `POLYROUTER_API_KEY`, `PMXT_CONFIG_PATH` | Optional exchange abstraction for prediction markets. |
| Hyperliquid later | `HYPERLIQUID_PRIVATE_KEY`, `HYPERLIQUID_WALLET_ADDRESS` | Deferred crypto-perps execution; disabled by default. |
| IBKR later | `IBKR_HOST`, `IBKR_PORT`, `IBKR_CLIENT_ID`, `IBKR_PAPER=true` | Deferred broker alternative; local gateway dependency. |

## 3. Canonical 35 World Monitor Sources

These are Qadam's active or planned live/live-adjacent data sources. Some require credentials; others are public but still need adapter configuration, rate limits, and heartbeat status.

| # | Source | Pipeline | Tier | Credential Placeholders | Endpoint / Access Pattern | Qadam Use |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | ACLED API | Conflict | 1 | `ACLED_EMAIL`, `ACLED_PASSWORD`, `ACLED_ACCESS_TOKEN`, `ACLED_REFRESH_TOKEN` | `https://acleddata.com/api/acled/read` | Political violence, protests, port-region escalation, and corridor risk. |
| 2 | UCDP API | Conflict | 4 | `UCDP_ACCESS_TOKEN` optional/reference | `https://ucdpapi.pcr.uu.se/api/gedevents/23.1` | Historical conflict base rates and longer-cycle geopolitical context. |
| 3 | GDELT Project API | Conflict | 2 | none | `https://api.gdeltproject.org/api/v2/doc/doc` | News tone, narrative velocity, global event extraction, and cross-language tension maps. |
| 4 | Oref API | Conflict | 1 | `OREF_PROXY_AUTH` optional | `https://www.oref.org.il/WarningMessages/alert/alerts.json` | Israeli Home Front Command alerts; high-trust regional instability signal. |
| 5 | Conflict Tracker | Conflict | 1 | none | Internal ACLED/GDELT fusion | Derived conflict layer; not an external credentialed API. |
| 6 | NASA FIRMS | Physical | 1 | `NASA_FIRMS_API_KEY` | FIRMS area CSV endpoint | Thermal anomalies near refineries, ports, mining, logistics, and military infrastructure. |
| 7 | Wingbits ADS-B | Physical | 2 | `WINGBITS_API_KEY` | `https://api.wingbits.com/v1/aircraft` | Aircraft enrichment, unusual routing, cargo and military aviation movements. |
| 8 | AIS Maritime | Physical | 2 | `AISSTREAM_API_KEY`, `SPIRE_API_KEY`, `MARINETRAFFIC_API_KEY` | AISStream WebSocket, Spire, or MarineTraffic | Vessel movements, tanker flows, port congestion, chokepoints, diversions. |
| 9 | ArcGIS / USACE Geospatial | Physical | 4 | `ARCGIS_API_TOKEN` optional | ArcGIS REST feature services | Infrastructure, waterways, dams, canals, ports, and structural physical context. |
| 10 | Space-Track / CelesTrak TLEs | Physical | 4 | `SPACE_TRACK_USERNAME`, `SPACE_TRACK_PASSWORD` | `https://www.space-track.org/basicspacedata/query/` | Satellite/TLE context, orbital infrastructure, and space-linked disruption monitoring. |
| 11 | GPS Jamming Monitors | Physical | 4 | none | `https://gpsjam.org/api` | Electronic-warfare and navigation-disruption context. |
| 12 | Internet Outage / IODA | Physical | 4 | none | `https://ioda.inetintel.cc.gatech.edu/api` | Connectivity disruption, cyber/geopolitical stress, and regional blackout context. |
| 13 | FRED API | Macro | 2 | `FRED_API_KEY` optional | FRED observations API and public CSV fallback | Interest rates, yields, money supply, liquidity, and macro regime features. |
| 14 | BLS API | Macro | 3 | `BLS_API_KEY` | `https://api.bls.gov/publicAPI/v2/timeseries/data/` | CPI, PPI, labour, and inflation context. |
| 15 | BIS Statistics | Macro | 3 | none | `https://stats.bis.org/api/v1/data/` | Global banking, settlement, liquidity, and systemic-risk context. |
| 16 | ECB Data Portal | Macro | 3 | none | `https://data-api.ecb.europa.eu/service/data/EXR/D.USD.EUR.SP00.A` | FX, rates, European policy, and USD/EUR-sensitive catalyst calibration. |
| 17 | UN Comtrade API | Macro | 3 | `COMTRADE_API_KEY` | `https://comtradeapi.un.org/data/v1/get/` | Trade flows, tariff trends, supply-chain rerouting, commodity demand. |
| 18 | USGS | Macro / Physical conflict | 3 | none currently | USGS minerals APIs or earthquake API | Spec conflict: qadam-specs says earthquake API; integration reference says minerals/commodity statistics. |
| 19 | UnusualWhales | Market | 1 | `UNUSUAL_WHALES_API_KEY` | `https://api.unusualwhales.com/api/option-trades/flow-alerts` | Options flow, dark pool, gamma, congressional trades, institutional confirmation. |
| 20 | Polymarket | Market | 1 | none for public data; later `POLYMARKET_PRIVATE_KEY`, `POLYMARKET_FUNDER_ADDRESS` | `https://clob.polymarket.com/markets` | Prediction-market prices, probability gaps, and later guarded execution. |
| 21 | Kalshi | Market | 1 | `KALSHI_API_KEY`, `KALSHI_API_SECRET` | `https://trading-api.kalshi.com/trade-api/v2/markets` | Regulated prediction-market monitoring and later guarded venue path. |
| 22 | Hyperliquid Perps | Market | 4 | none for public info; later `HYPERLIQUID_PRIVATE_KEY`, `HYPERLIQUID_WALLET_ADDRESS` | `https://api.hyperliquid.xyz/info` | Crypto/perps liquidity, funding context, optional later sandbox execution. |
| 23 | Alpaca Markets API | Market | 1 | `ALPACA_API_KEY`, `ALPACA_API_SECRET`, `ALPACA_PAPER=true` | Alpaca market data and trading APIs | US equities/options data and £100,000 paper account rail. |
| 24 | RapidAPI Hub | Market | 3 | `RAPIDAPI_KEY` | `https://rapidapi.com/hub` | Fallback marketplace for niche finance, sentiment, and alternative data APIs. |
| 25 | Coinglass | Market | 4 | `COINGLASS_API_KEY` | `https://open-api.coinglass.com/public/v2/` | Crypto derivatives, liquidations, funding rates, open interest. |
| 26 | Chainlink Price Feeds | Market | 4 | `ETH_RPC_URL` | Ethereum RPC endpoint | On-chain price-feed cross-checking. |
| 27 | Bookmap / Order Flow | Market | 4 | `BOOKMAP_BRIDGE_URL`, local Bookmap account | Local WebSocket bridge | Local order-flow confirmation and technical microstructure context. |
| 28 | RSS / Atom Feeds | Social | 2 | none or publisher subscription | Reuters, AP, Bloomberg, RSSHub, and curated feeds | Narrative velocity, consensus timing, and news catalyst triage. |
| 29 | Telegram APIs / Scrapers | Social | 3 | `TELEGRAM_API_ID`, `TELEGRAM_API_HASH`, `TELEGRAM_SESSION`, plus `TELEGRAM_BOT_TOKEN` for bot route | MTProto and Bot API | OSINT channels, pre-news reports, and outbound member alerts. |
| 30 | Twitter / X API v2 | Social | 2 | `X_BEARER_TOKEN` | `https://api.twitter.com/2/tweets/search/recent` | High-velocity sentiment, breaking news, and social narrative acceleration. |
| 31 | Reddit API | Social | 3 | `REDDIT_CLIENT_ID`, `REDDIT_CLIENT_SECRET` | `https://oauth.reddit.com/r/{subreddit}/new` | Retail attention, options chatter, and saturation / edge-decay checks. |
| 32 | SEC EDGAR API | Social | 3 | `SEC_USER_AGENT` | SEC search and submissions APIs | Corporate filings, 10-K/10-Q/8-K context, high-trust slow data. |
| 33 | STOCK Act Filings | Social | 3 | `STOCK_ACT_SOURCE_URL`, `STOCK_ACT_API_KEY` if provider chosen | Endpoint unresolved | Politician trade disclosures; must be cross-validated with UnusualWhales and SEC context. |
| 34 | Patent Filings | Social | 4 | `EPO_OPS_CONSUMER_KEY`, `EPO_OPS_CONSUMER_SECRET` optional | PatentsView and EPO OPS | Long-cycle R&D, semiconductor, defence, and technology inflection signals. |
| 35 | GitHub API | Social | 4 | `GITHUB_TOKEN` | `https://api.github.com/` | Developer activity, release-cycle changes, and weak tech-sector precursor signals. |

Supplemental market-confirmation capability, not counted in the 35-source registry until explicitly promoted:

| Capability | Pipeline | Access | Endpoint / Access Pattern | Qadam Use |
| --- | --- | --- | --- | --- |
| Yahoo Finance / yfinance | Market | No key by default; local library wrapper | `yahoo-finance-api/` `Ticker`, `Tickers`, `download`, `Market`, `Search`, `Sector`, `Industry`, `screen` | Read-only market price, volume, options-chain, market-status, quote-search, sector, screener, and news context. Useful for `market_price_confirmation`, pricing-gap context, and volume/technical confirmation. Cannot execute, reconcile, or stand alone as trade evidence. |

## 4. Platform, Model, Broker, And Notification APIs

These are not all World Monitor data sources, but they are required to make Qadam operate as a system.

| Area | Provider / Service | Placeholders | Authority Boundary |
| --- | --- | --- | --- |
| Cockpit auth | Supabase | `NEXT_PUBLIC_SUPABASE_URL`, `NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY`, `SUPABASE_SECRET_KEY` | Login and allowlist only; no trade authority. |
| Deployment | Vercel | `VERCEL_TOKEN`, `VERCEL_PROJECT_ID`, `VERCEL_TEAM_ID` | Deploys static cockpit / web shell; no local orchestrator secrets in Vercel unless explicitly approved. |
| Frontier LLM | Gemini | `GEMINI_API_KEY` | Strategy Lead research packets; cannot execute trades. |
| Local LLM | LM Studio / Gemma | `LM_STUDIO_BASE_URL`, `LM_STUDIO_MODEL` | Local Research Analyst triage; no cloud key required. |
| Quantum | Q-CTRL Fire Opal | `QCTRL_API_KEY`, `QCTRL_ORGANIZATION_SLUG` when required | Mandatory paper-live quantum consultation; no broker, risk, or execution authority. |
| Quantum | IBM Quantum | `IBM_QUANTUM_TOKEN`, `IBM_QUANTUM_INSTANCE` | Future hardware backend through Fire Opal device discovery and Qiskit Runtime; explicit probe required and hardware submission remains separately blocked. |
| Quantum | AWS Braket | `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, `AWS_REGION` | Optional hardware backend; restricted IAM only. |
| Paper broker | Alpaca | `ALPACA_API_KEY`, `ALPACA_API_SECRET`, `ALPACA_PAPER=true` | Paper account only until live promotion review. |
| Market data supplement | Yahoo Finance / yfinance | none by default; optional `YFINANCE_ENABLED`, `YFINANCE_CACHE_DIR`, `YFINANCE_REQUEST_BUDGET_PER_RUN`, `YFINANCE_SYMBOL_ALLOWLIST` | Read-only supplemental market confirmation. No broker execution, no fill prices, no receipts, no reconciliation truth. |
| Multi-source data plane | Preference / PREF MCP | `PREFERENCE_API_KEY`, optional `PREFERENCE_MCP_ENABLED`, `PREFERENCE_MCP_ENDPOINT`, `PREFERENCE_RUN_CALL_BUDGET`, `PREFERENCE_DAILY_CALL_BUDGET`, `PREFERENCE_TOOL_ALLOWLIST`, `PREFERENCE_DOMAIN_ALLOWLIST` | Read-only supplemental world-data and prediction-market context. Registered as `supplemental_data_plane`, not source 36. Status/catalog/sample/provenance checks first; no anonymous identity, no paid tools unless approved, no broker execution, no fill prices, no receipts, no reconciliation truth, no source-quorum credit, no canonical rank impact, and no canonical source promotion without a registry decision for a specific upstream source. |
| Prediction markets | Kalshi | `KALSHI_API_KEY`, `KALSHI_API_SECRET` | Read-only first; guarded execution later. |
| Prediction markets | Polymarket / pmxt / Polyrouter | `POLYMARKET_PRIVATE_KEY`, `POLYMARKET_FUNDER_ADDRESS`, `POLYMARKET_CHAIN_ID`, `POLYROUTER_API_KEY`, `PMXT_CONFIG_PATH` | Disabled until paper/sandbox-safe path is explicit. |
| Charts / alerts | TradingView | `TRADINGVIEW_WEBHOOK_SECRET`, `TRADINGVIEW_ALERT_RECEIVER_URL` | Paid-account alerts become observed signals only. No normal retail market-data API key. |
| Member alerts | Telegram Bot API | `TELEGRAM_BOT_TOKEN`, `TELEGRAM_BOT_USERNAME`, `TELEGRAM_DEFAULT_CHAT_ID`, `TELEGRAM_GROUP_CHAT_ID` | Outbound notifications only. No Telegram trade commands. |
| Email fallback | Resend or SMTP | `RESEND_API_KEY`, `RESEND_FROM_EMAIL`, `SMTP_HOST`, `SMTP_USER`, `SMTP_PASSWORD` | Delivery fallback only. |
| External uptime | UptimeRobot or equivalent | `UPTIMEROBOT_API_KEY` | Optional monitor for public cockpit availability. |

## 5. Reference Providers Found In `world-monitor/`

The pasted `world-monitor/` codebase includes many useful providers that are not yet canonical Qadam requirements. Keep them in a reference bucket until a Qadam module explicitly needs them.

| Reference Provider | Placeholders Seen / Proposed | Qadam Treatment |
| --- | --- | --- |
| Groq | `GROQ_API_KEY` | Reference LLM provider only. Qadam's current frontier model path is Gemini. |
| OpenRouter | `OPENROUTER_API_KEY` | Optional future model router; not required for first release. |
| Upstash Redis | `UPSTASH_REDIS_REST_URL`, `UPSTASH_REDIS_REST_TOKEN` | World Monitor cloud cache pattern. Qadam should not require Redis for correctness in v1. |
| Finnhub | `FINNHUB_API_KEY` | Optional stock quote/reference feed; Alpaca is canonical first broker/data rail. |
| EIA | `EIA_API_KEY` | Strong future oil/energy macro source; useful for crude oil thesis. |
| IMF SDMX | `IMF_API_KEY` | Optional macro reserve/debt dataset. |
| OpenAQ | `OPENAQ_API_KEY` | Optional air-quality / environmental context. |
| WAQI | `WAQI_API_KEY` | Optional air-quality supplement. |
| AviationStack | `AVIATIONSTACK_API` | Optional aviation data supplement; Wingbits is canonical first ADS-B provider. |
| ICAO | `ICAO_API_KEY` | Optional NOTAM/airport closure enrichment. |
| Travelpayouts | `TRAVELPAYOUTS_API_TOKEN` | Not a Qadam first-release signal source. |
| OpenSky | `OPENSKY_CLIENT_ID`, `OPENSKY_CLIENT_SECRET` | Optional aircraft feed fallback or supplement. |
| Cloudflare Radar | `CLOUDFLARE_API_TOKEN` | Optional internet outage / network stress supplement. |
| Cloudflare R2 | `CLOUDFLARE_R2_ACCOUNT_ID`, `CLOUDFLARE_R2_ACCESS_KEY_ID`, `CLOUDFLARE_R2_SECRET_ACCESS_KEY` | Cloud object storage pattern. Qadam v1 canonical saved state stays local. |
| ReliefWeb | `RELIEFWEB_APPNAME` | Optional disaster/humanitarian context. |
| CorridorRisk | `CORRIDOR_RISK_API_KEY` | Optional maritime corridor-risk score. |
| UNHCR / Open-Meteo / WorldPop | none | Public optional physical/humanitarian/geospatial context. |
| Windy webcams | `WINDY_API_KEY` | Optional visual corroboration for locations. |
| CoinGecko | `COINGECKO_API_KEY` | Optional crypto market supplement. |
| Cyber feeds | `OTX_API_KEY`, `ABUSEIPDB_API_KEY`, `URLHAUS_AUTH_KEY` | Optional cyber-disruption context; not in current 35-source registry. |
| Exa | `EXA_API_KEY`, `EXA_API_KEYS` | Optional web search/scrape discovery. |
| Firecrawl | `FIRECRAWL_API_KEY` | Optional structured web extraction. |
| P0 | `P0_API_KEY` | Optional upstream consumer-prices workflow dependency. |
| World Monitor snapshot | `WORLDMONITOR_SNAPSHOT_API_KEY`, `WORLDMONITOR_VALID_KEYS` | Upstream access-control pattern, not Qadam v1. |
| Convex | `CONVEX_URL`, `CONVEX_SITE_URL`, `CONVEX_SERVER_SHARED_SECRET` | Upstream cloud registration/billing pattern. Qadam uses Supabase for cockpit auth now. |
| Clerk | `VITE_CLERK_PUBLISHABLE_KEY`, `CLERK_SECRET_KEY`, `CLERK_JWT_ISSUER_DOMAIN` | Upstream auth pattern only. Qadam switched to Supabase. |
| Dodo Payments | `DODO_API_KEY`, `DODO_WEBHOOK_SECRET`, `DODO_PAYMENTS_WEBHOOK_SECRET` | Upstream billing pattern only. Not first-release Qadam. |
| Discord OAuth | `DISCORD_CLIENT_ID`, `DISCORD_CLIENT_SECRET`, `DISCORD_REDIRECT_URI` | Optional future member comms, not first-release. |

## 6. Placeholder Secret File Template

Use this as the canonical placeholder list for `data/runtime/qadam-secrets.env`. Fill only the keys you actually have. Leave everything else blank.

```bash
# Core model providers
GEMINI_API_KEY=
LM_STUDIO_BASE_URL=http://127.0.0.1:1234/v1
LM_STUDIO_MODEL=gemma-4-e4b

# Quantum providers
QCTRL_API_KEY=
QCTRL_ORGANIZATION_SLUG=
IBM_QUANTUM_TOKEN=
IBM_QUANTUM_INSTANCE=
AWS_ACCESS_KEY_ID=
AWS_SECRET_ACCESS_KEY=
AWS_REGION=

# Cockpit auth and deploy
NEXT_PUBLIC_SUPABASE_URL=
NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY=
SUPABASE_SECRET_KEY=
VERCEL_TOKEN=
VERCEL_PROJECT_ID=
VERCEL_TEAM_ID=

# First paper/execution rails
ALPACA_API_KEY=
ALPACA_API_SECRET=
ALPACA_PAPER=true
ALPACA_ENDPOINT=https://paper-api.alpaca.markets/v2
ALPACA_TO_GBP_RATE=
KALSHI_API_KEY=
KALSHI_API_SECRET=

# Later/deferred venue rails
POLYMARKET_PRIVATE_KEY=
POLYMARKET_FUNDER_ADDRESS=
POLYMARKET_CHAIN_ID=
POLYROUTER_API_KEY=
PMXT_CONFIG_PATH=
HYPERLIQUID_PRIVATE_KEY=
HYPERLIQUID_WALLET_ADDRESS=
IBKR_HOST=
IBKR_PORT=
IBKR_CLIENT_ID=
IBKR_PAPER=true

# Conflict pipeline
ACLED_EMAIL=
ACLED_PASSWORD=
ACLED_ACCESS_TOKEN=
ACLED_REFRESH_TOKEN=
ACLED_TOKEN_TYPE=
ACLED_TOKEN_EXPIRES_IN=
ACLED_TOKEN_EXPIRES_AT=
ACLED_TOKEN_REFRESHED_AT=
UCDP_ACCESS_TOKEN=
OREF_PROXY_AUTH=

# Physical / logistics pipeline
NASA_FIRMS_API_KEY=
WINGBITS_API_KEY=
AISSTREAM_API_KEY=
SPIRE_API_KEY=
MARINETRAFFIC_API_KEY=
ARCGIS_API_TOKEN=
SPACE_TRACK_USERNAME=
SPACE_TRACK_PASSWORD=
BOOKMAP_BRIDGE_URL=ws://localhost:8765/bookmap

# Macro pipeline
FRED_API_KEY=
BLS_API_KEY=
COMTRADE_API_KEY=
USGS_API_MODE=

# Market pipeline
UNUSUAL_WHALES_API_KEY=
RAPIDAPI_KEY=
COINGLASS_API_KEY=
ETH_RPC_URL=
YFINANCE_ENABLED=false
YFINANCE_CACHE_DIR=data/runtime/yfinance-cache
YFINANCE_REQUEST_BUDGET_PER_RUN=25
YFINANCE_SYMBOL_ALLOWLIST=CL=F,BZ=F,USO,XLE,SI=F,SLV,SIL,PAAS,ITA,XAR,LMT,RTX,NOC,SMH,SOXX,NVDA,TSM,ASML,AMD,SPY,QQQ,TLT,HYG,^VIX,DX-Y.NYB

# Social / narrative pipeline
RSS_FEED_CONFIG_PATH=
TELEGRAM_API_ID=
TELEGRAM_API_HASH=
TELEGRAM_SESSION=
TELEGRAM_CHANNEL_SET=
X_BEARER_TOKEN=
REDDIT_CLIENT_ID=
REDDIT_CLIENT_SECRET=
SEC_USER_AGENT=
STOCK_ACT_SOURCE_URL=
STOCK_ACT_API_KEY=
EPO_OPS_CONSUMER_KEY=
EPO_OPS_CONSUMER_SECRET=
GITHUB_TOKEN=

# TradingView observed-signal intake
TRADINGVIEW_WEBHOOK_SECRET=
TRADINGVIEW_ALERT_RECEIVER_URL=
TRADINGVIEW_MCP_ENABLED=false

# Telegram member communications
TELEGRAM_BOT_TOKEN=
TELEGRAM_BOT_USERNAME=
TELEGRAM_DEFAULT_CHAT_ID=
TELEGRAM_GROUP_CHAT_ID=
QADAM_TELEGRAM_ENABLED=false
QADAM_TELEGRAM_DRY_RUN=true

# Optional email fallback
RESEND_API_KEY=
RESEND_FROM_EMAIL=
SMTP_HOST=
SMTP_USER=
SMTP_PASSWORD=

# Optional future/reference providers from world-monitor
GROQ_API_KEY=
OPENROUTER_API_KEY=
FINNHUB_API_KEY=
EIA_API_KEY=
IMF_API_KEY=
OPENAQ_API_KEY=
WAQI_API_KEY=
AVIATIONSTACK_API=
ICAO_API_KEY=
TRAVELPAYOUTS_API_TOKEN=
OPENSKY_CLIENT_ID=
OPENSKY_CLIENT_SECRET=
CLOUDFLARE_API_TOKEN=
RELIEFWEB_APPNAME=
CORRIDOR_RISK_API_KEY=
WINDY_API_KEY=
COINGECKO_API_KEY=
OTX_API_KEY=
ABUSEIPDB_API_KEY=
URLHAUS_AUTH_KEY=
EXA_API_KEY=
FIRECRAWL_API_KEY=
```

## 7. Open Decisions / Conflicts

These need to stay visible in the implementation plan:

- USGS is unresolved. `qadam-specs.md` names earthquake data; the integration reference points toward USGS minerals / commodities. Qadam should either split this into `USGS Earthquake` and `USGS Minerals` or select one explicit v1 path.
- AIS provider choice is unresolved. The spec names Spire / MarineTraffic; the reference code has AISStream. Qadam can support all three, but one should be selected as the first paid provider.
- Space-Track / CelesTrak is a combined registry source. Space-Track requires an account; CelesTrak is public. The adapter should support public fallback where possible.
- STOCK Act filings need a concrete provider or official source selection.
- TradingView has account value through alerts and charting, not a normal retail market-data API key.
- Yahoo Finance / yfinance is resolved for now as a supplemental market-confirmation tool, not a canonical source-registry change. The dormant wrapper and sample check exist; live mode still requires deliberate dependency installation, `YFINANCE_ENABLED=true`, public-safe cockpit status, and no execution/reconciliation authority.
- The pasted `world-monitor/` cloud stack uses Redis, Railway, Convex, Clerk, Dodo, and Cloudflare. Qadam may reuse data-access ideas, but v1 must remain local-first and Supabase-authenticated.

## 8. Adapter Acceptance Rules

Every source adapter must ship with:

- Declared source key matching `world_monitor/source_registry.py`.
- Pipeline, tier, credential status, cadence, heartbeat SLA, and rate-limit budget.
- Read-only mode before any write or execution path.
- Raw payload archive with local retention rules.
- Normalized observation schema.
- Degraded-state handling for missing keys, quota errors, timeout, parse failure, stale data, and provider outage.
- For public/scraped market-data libraries such as yfinance, explicit terms-of-use, caching, request budget, and stale-data boundaries.
- Trust Score seed and future monthly update path.
- Event Log write for every ingest attempt, success, degradation, and adapter error.
- Dashboard status that answers: live, degraded, unavailable, deferred, blocked, or local-only.
- No real secrets in the public status contract.
