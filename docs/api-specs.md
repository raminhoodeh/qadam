# Qadam API Specs

This document is the working credential and API inventory for Qadam.

For the operational checklist to acquire keys in the right order, use `docs/qadam-api-key-acquisition-plan.md`.

Source hierarchy:

1. `specs/qadam-specs.md` is the product source of truth.
2. `specs/Qadam - World Monitor Integration Reference.md` gives endpoint-level integration detail.
3. `world_monitor/source_registry.py` is the canonical current 35-source implementation registry.
4. `world-monitor/` is a pasted reference codebase. It is useful for patterns and optional providers, but it is not Qadam's canonical architecture.

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
- Historical backfill planning and local sample-run records exist for ACLED, GDELT, NASA FIRMS, FRED, RSS, Polymarket, Kalshi, Alpaca, BLS, ECB, UN Comtrade, and SEC EDGAR.
- Trust Score seed covers all 35 sources, but scores are priors until replaced by backtests and live observations.
- Postgres/Timescale durable ingestion is coded as a local contract and is live only when the local database service is running.

Not yet proven live:

- Any credential-gated source without a configured local secret remains blocked as `missing_credentials`.
- Any public or configured source that fails a read-only live check is kept as `degraded` with the provider error class preserved locally.
- No adapter may promote signal confidence or create paper/live orders by itself.

Current local live-readiness snapshot as of 2026-05-18:

- Live in read-only validation: NASA FIRMS, FRED, RSS, Polymarket, Alpaca paper account mirror, BLS public sample, ECB public exchange-rate series, SEC EDGAR public filing metadata, and Telegram bot status.
- Degraded in read-only validation: GDELT, Oref, and ACLED. ACLED has local credentials but currently fails live validation with HTTP 403, so token refresh, entitlement, or account-scope confirmation is still required.
- Missing or deferred credentials: UnusualWhales, Kalshi, AIS Maritime, Wingbits, UN Comtrade, Reddit, and X/Twitter.
- Configured in the local ignored secret file: NASA FIRMS, Alpaca paper, ACLED email/password/access token/refresh token, FRED, Q-CTRL, Telegram bot token/username/private target/group target, Gemini/Google model keys, and LM Studio settings.
- ACLED refresh-token automation is required before treating ACLED as durable live infrastructure.
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
| Alpaca paper | `ALPACA_API_KEY`, `ALPACA_API_SECRET`, `ALPACA_PAPER=true` | Paper account mirror and eventual £1000 autonomous test execution. |
| Gemini | `GEMINI_API_KEY` | Frontier LLM Strategy Lead / deep research packets. |
| Supabase | `NEXT_PUBLIC_SUPABASE_URL`, `NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY`, `SUPABASE_SECRET_KEY` | Founding Fund Manager cockpit auth. |
| Telegram bot | `TELEGRAM_BOT_TOKEN`, `TELEGRAM_BOT_USERNAME`, `TELEGRAM_DEFAULT_CHAT_ID`, `TELEGRAM_GROUP_CHAT_ID` | Outbound member communications, alerts, and delivery status. |

### Batch B - Market, Macro, And Social Confirmation

| Provider | Placeholders | Why It Matters |
| --- | --- | --- |
| FRED | `FRED_API_KEY` | Official macro regime data; public CSV fallback exists. |
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
| Q-CTRL | `QCTRL_API_KEY` | Optional future quantum optimization/error-suppression layer. |
| IBM Quantum | `IBM_QUANTUM_TOKEN` | Primary future hardware backend through Qiskit Runtime. |
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
| 23 | Alpaca Markets API | Market | 1 | `ALPACA_API_KEY`, `ALPACA_API_SECRET`, `ALPACA_PAPER=true` | Alpaca market data and trading APIs | US equities/options data and £1000 paper account rail. |
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

## 4. Platform, Model, Broker, And Notification APIs

These are not all World Monitor data sources, but they are required to make Qadam operate as a system.

| Area | Provider / Service | Placeholders | Authority Boundary |
| --- | --- | --- | --- |
| Cockpit auth | Supabase | `NEXT_PUBLIC_SUPABASE_URL`, `NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY`, `SUPABASE_SECRET_KEY` | Login and allowlist only; no trade authority. |
| Deployment | Vercel | `VERCEL_TOKEN`, `VERCEL_PROJECT_ID`, `VERCEL_TEAM_ID` | Deploys static cockpit / web shell; no local orchestrator secrets in Vercel unless explicitly approved. |
| Frontier LLM | Gemini | `GEMINI_API_KEY` | Strategy Lead research packets; cannot execute trades. |
| Local LLM | LM Studio / Gemma | `LM_STUDIO_BASE_URL`, `LM_STUDIO_MODEL` | Local Research Analyst triage; no cloud key required. |
| Quantum | Q-CTRL | `QCTRL_API_KEY` | Optional provider; weekly oracle only. |
| Quantum | IBM Quantum | `IBM_QUANTUM_TOKEN` | Optional hardware backend; classical fallback required. |
| Quantum | AWS Braket | `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, `AWS_REGION` | Optional hardware backend; restricted IAM only. |
| Paper broker | Alpaca | `ALPACA_API_KEY`, `ALPACA_API_SECRET`, `ALPACA_PAPER=true` | Paper account only until live promotion review. |
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
IBM_QUANTUM_TOKEN=
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
- The pasted `world-monitor/` cloud stack uses Redis, Railway, Convex, Clerk, Dodo, and Cloudflare. Qadam may reuse data-access ideas, but v1 must remain local-first and Supabase-authenticated.

## 8. Adapter Acceptance Rules

Every source adapter must ship with:

- Declared source key matching `world_monitor/source_registry.py`.
- Pipeline, tier, credential status, cadence, heartbeat SLA, and rate-limit budget.
- Read-only mode before any write or execution path.
- Raw payload archive with local retention rules.
- Normalized observation schema.
- Degraded-state handling for missing keys, quota errors, timeout, parse failure, stale data, and provider outage.
- Trust Score seed and future monthly update path.
- Event Log write for every ingest attempt, success, degradation, and adapter error.
- Dashboard status that answers: live, degraded, unavailable, deferred, blocked, or local-only.
- No real secrets in the public status contract.
