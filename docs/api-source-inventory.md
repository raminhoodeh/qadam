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
- Space-Track and CelesTrak remain one TLE source for now because only Space-Track has a detailed endpoint in the specs.
- Spire and MarineTraffic remain one AIS source for now because the tool contract is identical.

## Tier 1 - Wire First

| Source | Access | Notes |
| --- | --- | --- |
| ACLED | OAuth, `https://api.acleddata.com/acled/read` | World Monitor has reusable OAuth/token-cache logic. |
| Oref | Public, `https://www.oref.org.il/WarningMessages/alert/alerts.json` | Spec says 5s cadence, but practical relay code uses a slower protected path. |
| NASA FIRMS | API key, FIRMS area CSV endpoint | Promoted as the first physical adapter; bbox-first, read-only, credential-gated, and paced conservatively. |
| UnusualWhales | API key, `https://api.unusualwhales.com/api/option-trades/flow-alerts` | Not implemented in World Monitor; build fresh. |
| Polymarket | Public CLOB plus wallet/execution later | World Monitor uses Gamma discovery, not full CLOB execution. |
| Kalshi | API key, trading API | World Monitor uses an elections/trade endpoint for discovery. |
| Alpaca | API key + secret, data/trading APIs | Not implemented in World Monitor; build fresh. |

## Tier 2 - Wire Second

| Source | Access | Notes |
| --- | --- | --- |
| FRED | API key, FRED observations endpoint | World Monitor has seeders and FRED fallback patterns. |
| AIS Maritime | Spire or MarineTraffic API key | World Monitor uses AISStream WebSocket as an MVP substitute. |
| Wingbits | API key | World Monitor has bbox and military-flight classification patterns. |
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
| USGS | Conflict: main spec says earthquake API; integration ref says commodity stats | Needs final implementation choice. |
| Reddit | OAuth app | Confirmation source, not primary. |
| Telegram | Bot API plus Telethon/MTProto user session | World Monitor has strong channel polling logic. |
| SEC EDGAR | Public API, User-Agent required | High-trust corporate filing source. |
| STOCK Act filings | Endpoint not specified in current specs | Needed for politician trade disclosures. |

## Tier 4 - Wire Last Or Phase 2

| Source | Access | Notes |
| --- | --- | --- |
| UCDP | Public REST API | Historical conflict base rates. |
| ArcGIS / USACE | Public layers, optional ArcGIS token | Structural infrastructure context. |
| Space-Track / CelesTrak | Space-Track account; CelesTrak endpoint unresolved in specs | Satellite/TLE context. |
| GPS Jamming | Public `gpsjam.org` API | Electronic-warfare context. |
| IODA Internet Outage | Public Georgia Tech API | Regional connectivity/cyber disruption context. |
| Coinglass | API key | Crypto derivatives context. |
| Bookmap | Local WebSocket bridge | Local process dependency. |
| Chainlink | Ethereum RPC endpoint | Price-feed cross-checking. |
| Hyperliquid | Public info API | Crypto/perp sentiment and liquidity context. |
| GitHub | Read-only PAT | Weak tech-sector precursor signal. |
| Patents | Public USPTO/EPO APIs | Long-cycle R&D signal. |
| RapidAPI | RapidAPI key | Catch-all fallback for niche sources. |

## Conflicts To Carry Into Implementation

- The documents say "35 sources", but the integration reference details fewer because some sources are combined. The registry resolves this by splitting Polymarket/Kalshi and SEC/STOCK Act.
- `qadam-specs.md` names USGS Earthquake API, while the integration reference specifies USGS commodity/minerals data. The registry marks USGS as `needs_clarity`.
- `qadam-specs.md` names Space-Track / CelesTrak, but only Space-Track has endpoint details.
- Oref cadence says 5 seconds, while the World Monitor implementation suggests a slower practical polling setup with Tzeva Adom/Oref fallback behavior.
- World Monitor contains strong source-access patterns, but Qadam should not inherit its Redis/Railway/Vercel architecture.
