# Qadam API Source Inventory

Source of truth: `specs/qadam-specs.md`.
Detailed endpoint companion: `specs/Qadam - World Monitor Integration Reference.md`.
Credential and placeholder companion: `docs/api-specs.md`.

## Scan Result

The specs describe five World Monitor pipelines and repeatedly refer to 35 sources. The detailed integration reference gives strong endpoint-level specs, but some entries are combined there. For the foundation registry, Qadam treats the combined entries as separate sources when they imply different credentials, venues, or operating risk.

Boundary: this inventory covers live and live-adjacent machine-readable feeds. It does not include `how-the-world-works/`, which is Qadam's private foundational world-model corpus. That corpus informs hypotheses, hidden-incentive maps, and scenario generation, but it is not a live source, heartbeat, or factual evidence feed.

Key split decisions:

- Polymarket and Kalshi are separate market sources, even though the integration reference combines them.
- SEC EDGAR and STOCK Act / politician filings are separate narrative sources, even though the integration reference combines them.
- Space-Track and CelesTrak remain one TLE source. Space-Track is the authenticated primary path; CelesTrak GP JSON is the public fallback/smoke path.
- Spire and MarineTraffic remain one AIS source because the tool contract is identical. AISStream is the v1 read-only MVP provider; Spire and MarineTraffic remain paid fallback candidates.
- Yahoo Finance / yfinance is an accepted supplemental market-confirmation capability from the local `yahoo-finance-api/` checkout, currently classified as `accepted_supplemental_pending_live_dependencies`. It is not counted in the current 35-source registry unless the master plan deliberately promotes it.
- Preference/PREF MCP is a registered supplemental multi-source data capability plane. It is not counted as a 36th canonical source; individual upstream sources discovered through Preference require separate registry decisions before promotion.
- Source registry cleanup now separates selected missing credentials from unselected optional sources. The current selected optional credential gaps are Reddit, Kalshi, and Capitol Trades/STOCK Act. Their credential-bound read-only adapter contracts exist, but they stay disconnected until credentials are supplied. UnusualWhales and RapidAPI are intentionally disabled; Coinglass, Chainlink, and GitHub need adapter/provider decisions before any key is requested.

## Tier 1 - Wire First

| Source | Access | Notes |
| --- | --- | --- |
| ACLED | OAuth, `https://acleddata.com/api/acled/read` | World Monitor has reusable OAuth/token-cache logic; current live validation is degraded until token refresh, entitlement, or account scope is confirmed. |
| Oref | Public, `https://www.oref.org.il/WarningMessages/alert/alerts.json` | Spec says 5s cadence, but practical relay code uses a slower protected path. |
| NASA FIRMS | API key, FIRMS area CSV endpoint | Promoted as the first physical adapter; bbox-first, read-only, credential-gated, and paced conservatively. |
| UnusualWhales | Intentionally disabled | Optional options-flow source; not a current credential request because Capitol Trades is the selected politician-trading path. |
| Polymarket | Public CLOB plus wallet/execution later | Read-only CLOB adapter scaffolded; execution remains disabled. |
| Kalshi | API key, RSA private key, trading API | Credential-bound read-only adapter scaffolded; region/account eligibility remains the practical gate. |
| Alpaca | API key + secret, data/trading APIs | Paper execution exists separately; registry row is the read-only account/market-data mirror contract. |

## Tier 2 - Wire Second

| Source | Access | Notes |
| --- | --- | --- |
| FRED | API key, FRED observations endpoint | World Monitor has seeders and FRED fallback patterns. |
| AIS Maritime | AISStream, Spire, or MarineTraffic API key | AISStream is the v1 read-only MVP; Spire/MarineTraffic remain paid fallback candidates. |
| Aviationstack | API key | World Monitor uses Aviationstack as the v1 flight-data source for route, airport, airline, and flight-status context. |
| GDELT | Public doc API | World Monitor has retry and proxy-fallback logic. |
| RSS / Atom | Public feeds | World Monitor has a large curated feed list and digest scoring. |
| Twitter / X | Bearer token | Strict API limits; store tweet content carefully. |

## Tier 3 - Wire Third

| Source | Access | Notes |
| --- | --- | --- |
| BLS | API key | World Monitor notes cloud IP friction; FRED equivalents are fallback. |
| ECB | Public data API | Use SDMX JSON format. |
| UN Comtrade | API key | Weekly/monthly context source. |
| BIS | Public stats API | Weekly systemic-risk context. |
| USGS | Public minerals data and earthquake API | Scope decision recorded: minerals/supply-chain context is the strategic role; the public earthquake API is the event-driven physical-risk adapter path. |
| Reddit | OAuth app | Credential-bound confirmation source, not primary. |
| Telegram | Bot API plus Telethon/MTProto user session | World Monitor has strong channel polling logic. |
| SEC EDGAR | Public API, User-Agent required | High-trust corporate filing source. |
| STOCK Act filings | Capitol Trades/provider-selected congressional trades path | Credential-bound v1 provider direction recorded; needed for politician trade disclosures and cross-validation. |

## Tier 4 - Wire Last Or Phase 2

| Source | Access | Notes |
| --- | --- | --- |
| UCDP | Public REST API | Historical conflict base rates. |
| ArcGIS / USACE | Public layers, optional ArcGIS token | Structural infrastructure context. |
| Space-Track / CelesTrak | Space-Track account; CelesTrak GP JSON public fallback | Satellite/TLE context. |
| GPS Jamming | Public `gpsjam.org` API | Electronic-warfare context. |
| IODA Internet Outage | Public Georgia Tech API | Regional connectivity/cyber disruption context. |
| Coinglass | Not selected; adapter decision required | Crypto derivatives context only if crypto/perps becomes relevant. |
| Bookmap | Local WebSocket bridge | Local process dependency. |
| Chainlink | Not selected; adapter decision required | Prefer a public read-only price-feed adapter before requesting RPC credentials. |
| Hyperliquid | Public info API | Crypto/perp sentiment and liquidity context. |
| GitHub | Not selected; adapter decision required | Optional tech/supply-chain context; no token requested until a signal role is selected. |
| Patents | Public USPTO/EPO APIs | Long-cycle R&D signal. |
| RapidAPI | Intentionally disabled | Marketplace only; activate only after selecting a specific RapidAPI-backed provider. |

## Supplemental Market Confirmation - Accepted Pending Live Dependencies

| Capability | Access | Notes |
| --- | --- | --- |
| Yahoo Finance / yfinance | No key by default; local `yahoo-finance-api/` wrapper | Useful for OHLCV, volume, options-chain, market status, quote search, sector, screener, and news context. A dormant wrapper now exists in `orchestrator/yahoo_finance_adapter.py`; live mode still needs dependencies installed and must remain corroboration only. Cannot be used for broker execution, fills, receipts, reconciliation, or sole signal authority. |

## Supplemental Multi-Source Data Plane - Registered Supplemental Reference

| Capability | Access | Notes |
| --- | --- | --- |
| Preference / PREF MCP | Remote Streamable HTTP MCP at `https://pref.trade/mcp`; bearer key `pref_agent_*` or account key | Registered in the Resource Registry as `preference_mcp` with category `supplemental_data_plane`. It is a read-only data plane for prediction markets, orderbooks, physical movement, weather, filings, wallet intelligence, news, macro, sports lines, and other world data. Current Qadam posture is status/catalog/sample/provenance/domain-pack/shadow-context, public cockpit visibility, Preference-aware Phase 4 strategy manifestation, Q4-10/Q4-12 certification gating, and PREF-12 upstream source-promotion decisions only until identity and allowlist gates pass. PREF-12 currently promotes zero sources: Polymarket, Kalshi, SEC EDGAR, and vessel tracking map to existing registry entries; NOAA-style weather and KOL wallet context are deferred. It is not source 36, not an execution venue, not a broker, not a fill/receipt/reconciliation source, and cannot affect canonical trust rank unless a specific upstream source is separately promoted. |

## Resolved Source-Registry Blockers

The May 2026 source-registry blocker pass resolved the eight stale blockers into explicit v1 decisions:

| Source | Decision | Remaining Gate |
| --- | --- | --- |
| `stock_act` | Use Capitol Trades or the selected STOCK Act provider path for v1 congressional trade disclosures. | Needs `CAPITOL_TRADES_API_KEY` and provider-confirmed `CAPITOL_TRADES_API_URL`; key-only setup stays endpoint-unconfirmed. |
| `usgs` | Treat USGS as mineral/supply-chain context first, with the public earthquake API as event-driven physical-risk input. | Provider-specific minerals parsing still needs deeper research normalization. |
| `space_track_celestrak` | Keep Space-Track as authenticated primary and CelesTrak GP JSON as public fallback. | Space-Track credentials only needed for the fuller authenticated path. |
| `ais_maritime` | Use AISStream as the v1 read-only MVP; keep Spire/MarineTraffic as paid fallbacks. | Needs one AIS credential before live vessel data is available. |
| `aviationstack` | Use Aviationstack as the v1 flight-data provider instead of Wingbits. | Needs `AVIATIONSTACK_API_KEY`; live adapter stays read-only and quota-aware. |
| `unusual_whales` | Intentionally disabled until re-selected. | No key requested in the current source plan. |
| `polymarket` | Use public CLOB/orderbook path, not Gamma-only discovery. | Execution remains separately disabled. |
| `kalshi` | Keep credential-bound read-only market adapter; classify region/account as the gate. | Needs account eligibility and credentials. |
| `alpaca` | Separate read-only market/account mirror from Alpaca paper execution. | Broader market-data scope depends on account/data entitlements. |

## Conflicts To Carry Into Implementation

- The documents say "35 sources", but the integration reference details fewer because some sources are combined. The registry resolves this by splitting Polymarket/Kalshi and SEC/STOCK Act.
- `qadam-specs.md` names USGS Earthquake API, while the integration reference specifies USGS commodity/minerals data. The v1 decision is minerals/supply-chain context plus public earthquake event monitoring.
- `qadam-specs.md` names Space-Track / CelesTrak, but only Space-Track has detailed authenticated endpoint specs. The v1 public fallback is CelesTrak GP JSON.
- Oref cadence says 5 seconds, while the World Monitor implementation suggests a slower practical polling setup with Tzeva Adom/Oref fallback behavior.
- World Monitor contains strong source-access patterns, but Qadam should not inherit its Redis/Railway/Vercel architecture.
- Yahoo Finance creates a source-count decision: keep it supplemental for market confirmation, or deliberately promote it into the canonical registry with a new source count and acceptance gate.
