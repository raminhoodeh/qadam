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
- Source registry cleanup now separates selected missing credentials from unselected optional sources. The current selected optional credential gaps are Reddit and Capitol Trades/STOCK Act. Direct Kalshi remains deferred, but OddsPipe is now the selected read-only Kalshi/Polymarket coverage route for Stage 0. UnusualWhales and RapidAPI are intentionally disabled. Coinglass, Chainlink, GitHub, and Bookmap now have provider decisions recorded, but remain unconnected until their read-only adapters or local bridge are explicitly built/started.

## Tier 1 - Wire First

| Source | Access | Notes |
| --- | --- | --- |
| ACLED | OAuth, `https://acleddata.com/api/acled/read` | World Monitor has reusable OAuth/token-cache logic; current live validation is degraded until token refresh, entitlement, or account scope is confirmed. |
| Oref | Public, `https://www.oref.org.il/WarningMessages/alert/alerts.json` | Spec says 5s cadence, but practical relay code uses a slower protected path. |
| NASA FIRMS | API key, FIRMS area CSV endpoint | Promoted as the first physical adapter; bbox-first, read-only, credential-gated, and paced conservatively. |
| UnusualWhales | Intentionally disabled | Optional options-flow source; not a current credential request because Capitol Trades is the selected politician-trading path. |
| Polymarket | Public CLOB plus wallet/execution later | Read-only CLOB adapter scaffolded; execution remains disabled. |
| Kalshi / OddsPipe | OddsPipe API key now; direct Kalshi API key and RSA private key later | OddsPipe is the selected read-only normalized Kalshi/Polymarket coverage route. Direct Kalshi account eligibility remains deferred. |
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
| Coinglass | CoinGlass API selected; adapter pending | Optional crypto derivatives context only if crypto/perps becomes relevant. No key requested now. |
| Bookmap | Local WebSocket bridge | Local process dependency. |
| Chainlink | Chainlink Data Feeds selected; public adapter pending | Prefer a public read-only price-feed adapter before requesting RPC credentials. |
| Hyperliquid | Public info API | Crypto/perp sentiment and liquidity context. |
| GitHub | GitHub REST API selected; public adapter pending | Optional tech/supply-chain context; no token requested until a narrow watchlist and signal role are selected. |
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

## Supplemental Internet Reach Layer - Agent Reach

Agent Reach is now registered as a local reference bridge through
`orchestrator/agent_reach_bridge.py` and validated by
`scripts/check_agent_reach_bridge.py`.

This does not change Qadam's canonical 35-source count. It enriches Qadam's
read-only evidence layer by mapping the local `Agent-Reach-main/` checkout into
supplemental channels for:

- RSS/news feeds, public web article readback, and Exa-style source discovery;
- X/Twitter and Reddit local logged-in/cookie routes where API access is weak
  or unavailable;
- GitHub public developer activity for narrow semiconductor/AI-infrastructure
  watchlists;
- YouTube transcripts and public video briefings;
- V2EX, Xueqiu, Bilibili, Xiaohongshu, LinkedIn, and Xiaoyuzhou as optional
  regional, developer, company, video, or podcast context channels.

The bridge is deliberately metadata-first. It does not install Agent Reach,
does not run browser sessions, does not read cookies, does not call external
networks, and does not promote any channel into source quorum. Its normalized
`social_news_discovery_packet` is persisted in the evidence runtime as
supplemental context only.

Current practical missing data after this bridge:

- Reddit remains unavailable until a local logged-in OpenCLI or `rdt-cli`
  route is configured.
- X/Twitter has API credentials, but Agent Reach's local cookie/browser route
  is not activated unless the operator sets it up separately.
- Capitol Trades/STOCK Act and Kalshi still need their provider credentials.
- LinkedIn/Xiaohongshu/Xueqiu-style cookie channels should use dedicated
  low-risk accounts if ever activated.

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

## Provider Decision Pass

As of 2026-06-14, Qadam has explicit provider decisions for the remaining optional/provider-choice entries that are not selected credential gaps:

| Source | Provider Decision | Current State | Boundary |
| --- | --- | --- | --- |
| `rapidapi` | No provider selected; marketplace disabled. | Intentionally disabled. | Do not request `RAPIDAPI_KEY` unless a specific RapidAPI-backed source is chosen. |
| `coinglass` | CoinGlass API selected for a possible future crypto/perps derivatives context. | Provider selected, adapter not built. | No `COINGLASS_API_KEY` request now; no source quorum credit. |
| `chainlink` | Chainlink Data Feeds selected for possible future price-integrity cross-checking. | Provider selected, public adapter not built. | No RPC credential request now; read-only adapter comes first. |
| `github` | GitHub REST API selected for possible future technology and supply-chain context. | Provider selected, public adapter not built. | No `GITHUB_TOKEN` request now; a narrow watchlist must exist first. |
| `bookmap` | Local Bookmap API bridge selected for possible order-flow confirmation. | Adapter ready; local bridge process required. | No hosted API key; must run locally and remain read-only. |

These decisions are planning/readiness metadata only. Bookmap now has a read-only local bridge adapter, but it still cannot create evidence from a live Bookmap session until the local bridge process is running. None of these decisions can submit orders, call brokers, or enable live capital.

## Evidence Packet Normalization

As of 2026-06-14, Qadam normalizes source evidence through `orchestrator/evidence_packet_normalization.py`.

The normalizer accepts:

- shadow-signal evidence trails from the research pipeline;
- TradingView MCP technical-analysis evidence items;
- Bookmap local bridge order-flow evidence items;
- provider-decision and credential-bound evidence packet type declarations for future adapters.

Every normalized packet must expose:

- `schema_version`, `normalization_version`, `packet_id`, `packet_type`, and `packet_role`;
- `signal_id`, `trail_id`, `sources`, `source_count`, `item_count`, and normalized `items`;
- trust scores, missing correlations, summary, created time, and a public-safe boundary;
- false authority flags for source quorum credit, risk handoff, trade-candidate creation, execution, paper orders, broker writes, quantum jobs, performance credit, and live capital.

The normalizer strips `raw_ref` from public evidence items and rejects authority leakage in `scripts/check_evidence_packet_normalization.py` and `scripts/check_cockpit_status.py`.

## Durable Evidence Packet Runtime

As of 2026-06-14, normalized evidence packets are also persisted through `orchestrator/evidence_packet_runtime.py`.

The durable runtime writes:

- `data/runtime/evidence_packet_runtime.json` as the latest replayable snapshot;
- `data/runtime/evidence_packet_runtime_history.jsonl` as append-only packet-runtime history;
- `data/runtime/evidence_packet_runtime_events.jsonl` as the local event-log audit trail.

This runtime is deliberately replay-only. It can preserve the exact normalized evidence packets that the cockpit saw, but it cannot create source quorum, trade ideas, risk approval, orders, broker writes, quantum jobs, performance credit, or live capital. `scripts/check_evidence_packet_runtime.py` validates the snapshot, history append, event-log write, packet counts, authority flags, and raw-reference stripping. The production dashboard preflight now runs that check before exporting cockpit status.

## Acceptance Tests

As of 2026-06-14, the non-dashboard source/evidence/runtime work is covered by
`scripts/check_source_evidence_acceptance.py`.

The acceptance gate runs the source-registry cleanup, Phase 1 data spine,
read-only source hardening, credential-bound adapter, provider-decision, Agent
Reach bridge, TradingView MCP, Bookmap local bridge, evidence normalization,
durable evidence runtime, and cockpit-status checks. It deliberately excludes
Stage 7 dashboard simplification because that work is plan-only until
explicitly implemented.

The gate must report:

- `source_evidence_acceptance_status=ok`;
- zero legacy source-registry blockers;
- no provider-decision credentials required now;
- no more than the current selected optional credential gaps;
- Agent Reach reference ready without changing the canonical source count or
  reading cookies/browser sessions;
- TradingView MCP and Bookmap evidence available as read-only supplemental
  context;
- zero evidence authority leaks and zero raw-reference leaks;
- durable runtime replay ready;
- no trade-blocking or silent source gaps in the paper-operation cockpit
  export;
- live capital disabled and no broker/order authority introduced.

## Deployment Discipline

As of 2026-06-14, source/evidence/runtime acceptance is part of the production
dashboard deploy preflight in `scripts/preflight_dashboard_deployment.sh`.

The deploy discipline is enforced by
`scripts/check_source_evidence_deployment_discipline.py`. The checker validates
that:

- `scripts/check_source_evidence_acceptance.py` has already produced an `ok`
  source/evidence/runtime acceptance report;
- the production deploy script still routes through local preflight before
  Vercel deploy and before aliasing `qadam.trade` / `www.qadam.trade`;
- the public cockpit status mirror exposes the durable evidence runtime,
  TradingView MCP, Bookmap local bridge, and optional source-gap visibility
  without secrets or write authority;
- the detached cockpit-status digest remains read-only and aligned to the
  exported payload;
- the deployment receipt, when present, records the Vercel URL, aliases, and
  preflight status without exposing tokens, broker credentials, dashboard
  secrets, provider keys, or session material.

This deployment discipline is deliberately narrower than dashboard UX work. It
does not implement Stage 7 dashboard simplification, and it cannot approve
trades, submit paper orders, call brokers, call providers, run quantum jobs,
grant proof credit, or enable live capital.

## Conflicts To Carry Into Implementation

- The documents say "35 sources", but the integration reference details fewer because some sources are combined. The registry resolves this by splitting Polymarket/Kalshi and SEC/STOCK Act.
- `qadam-specs.md` names USGS Earthquake API, while the integration reference specifies USGS commodity/minerals data. The v1 decision is minerals/supply-chain context plus public earthquake event monitoring.
- `qadam-specs.md` names Space-Track / CelesTrak, but only Space-Track has detailed authenticated endpoint specs. The v1 public fallback is CelesTrak GP JSON.
- Oref cadence says 5 seconds, while the World Monitor implementation suggests a slower practical polling setup with Tzeva Adom/Oref fallback behavior.
- World Monitor contains strong source-access patterns, but Qadam should not inherit its Redis/Railway/Vercel architecture.
- Yahoo Finance creates a source-count decision: keep it supplemental for market confirmation, or deliberately promote it into the canonical registry with a new source count and acceptance gate.
