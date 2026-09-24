# Source Coverage Repair - 24 September 2026

## Contract

The 41 dashboard catalogue entries are not 41 independent, authorized live APIs.
They include aliases, derived views, broker/control-plane connections, optional
unselected integrations and disabled paid providers. Collection, timestamped
event evidence and execution authority are separate states.

This release repairs collection and observation extraction. It does not enable
live capital, bypass Q-CTRL, change position limits, manufacture signals, or
guarantee more trades or profitable strategies.

## Repairs

| Source | Repair and remaining scope |
| --- | --- |
| ACLED | One bounded OAuth renewal after HTTP 401, authenticated password scope, then one read retry. HTTP 403 remains an access problem, not a refresh loop. |
| UCDP | Current GED endpoint and `x-ucdp-access-token` authentication; no longer advertised as a public unauthenticated API. Historical base-rate context. |
| PatentsView | Search API and `X-Api-Key`, bounded latest 25 records. Retired HTML endpoint cannot count as data. |
| GDELT | Correct grouped OR query and language query operator; explicit parse/HTTP failure and rate backoff. |
| Oref | Valid empty/BOM-prefixed response is not a parse error. HTTP 403 remains unavailable, not zero alerts. |
| GPSJAM | Public manifest selects the latest complete, non-suspect daily CSV. Two-megabyte response cap; highest 25 degraded-accuracy cells retained with the full cell count. No inference that accuracy degradation proves jamming. |
| IODA | Real v2 country outage alerts, last-hour bounded query, country, observation time, measurement and baseline retained. Not a complete historical outage census. |
| ArcGIS | Actual NOAA/Esri observed-cyclone FeatureServer records rather than a service directory. Storm timestamp and measurements retained; does not claim USACE infrastructure coverage. |
| BLS | Individual CPI/payroll observations extracted from nested series envelopes. Reference month is not relabelled as publication time. |
| ECB | SDMX observation dimensions joined to exchange-rate values. Reference date retained without inventing availability time. |
| SEC EDGAR | Individual filing records and actual acceptance timestamps instead of one generic submissions envelope. Existing issuer scope remains bounded. |
| Hyperliquid | Asset metadata joined to mark price, funding and open interest for BTC/ETH/SOL. Indicative context, not broker quotes. |
| Polymarket | Active, non-closed Gamma markets instead of the first historical CLOB catalogue page. Prices, liquidity, volume, condition and timestamps retained. Prices are indicative, not execution quotes. |
| Kalshi/OddsPipe | Both contract descriptions, prices and proposed spread retained. A suggested match is explicitly not proof of equivalent settlement conditions or arbitrage. |
| USGS | Earthquake timestamp, magnitude and coordinates retained. |
| CelesTrak | Orbital elements and reference epoch retained, not only the satellite name. |
| STOCK Act | Transaction details retained; trade date and relative publication wording are not promoted to verified disclosure availability time. |
| NASA FIRMS | All four configured corridors rotate on the three-hour cadence. Raw detections are counted separately from qualifying high-confidence/high-FRP events. Malformed CSV/404 does not mean no fires. |
| AISStream | Compressed, bounded subscriptions; metadata-coordinate support, invalid-coordinate rejection and frame/rejection counters. Empty captures do not establish absence of shipping activity. |
| Yahoo Finance | Installed pinned dependencies, enabled read-only collection, fixed both MultiIndex layouts, scheduled bounded supplemental reads. Daily bar date is not publication time. |
| TradingView | Installed pinned dependencies, enabled scheduled read-only collection, corrected exchange casing and daily interval. Snapshot retrieval time does not become historical event time. |
| Telegram | The command bridge remains the only update consumer. Source health uses bot identity, not `getUpdates`; bot/control messages do not count as market research. |
| Conflict tracker | Explicit derived alias of ACLED/GDELT, not an independent provider observation. |

Yahoo/TradingView third-party reads run in a child process with a 45-second wall
deadline. The parent records timeout/failure rather than blocking the collector
indefinitely. Provider failures retain bounded retry schedules; credential and
entitlement errors are not hammered. No proxy or geographic bypass was added.

The goal-ingestion batch reuses one validated history snapshot for corrections
and new observations instead of reparsing the entire append-only history for
each row. Durable receipts, stable IDs and the 20-goal cycle cap remain intact.

## Operator Actions Still Required

| Source | Current requirement |
| --- | --- |
| ACLED | Existing credentials authenticate but the data API returns 403. Resolve data access with the provider; token renewal alone is insufficient. |
| Oref | Provider returns 403 from this host. Obtain an authorized access route; do not evade geographic/provider restrictions. |
| UCDP | Configure provider-issued `UCDP_ACCESS_TOKEN` locally. The API documentation describes the token request process. |
| PatentsView | Configure an existing `PATENTSVIEW_API_KEY`; new issuance is subject to the provider's availability. |
| Bookmap | Configure and run the actual read-only Bookmap bridge (`BOOKMAP_BRIDGE_URL`). No mock bridge or fabricated measurements. |
| X | Existing bearer credential receives HTTP 402. Provider access/credits must be resolved outside the collector. |
| Aviationstack | HTTP 429; remain on provider-safe backoff and review account quota. No subscription upgrade was purchased. |
| GDELT | Latest repaired-query probe received HTTP 429; scheduled retry remains necessary. |
| TradingView paid alerts | A real authenticated receiver and genuine alert receipts remain unconfigured. The existing local contract/fixtures are not a live feed. |
| Unusual Whales / RapidAPI | Remain intentionally disabled; no purchases or automatic reactivation. |
| GitHub / CoinGlass / Chainlink | Remain unselected research integrations, not silently counted as connected market feeds. Define their role and entitlement before adding collection. |

Set credentials only in the existing private secret store, never Telegram or a
committed file. `.env.example` lists the new key names. Local read-only Yahoo and
TradingView flags are persisted in the private `.env.local`. Reproducible optional
packages are in `pyproject.toml` under `market-context`.

## Verification and Ongoing Truth

- `data/runtime/phase1_live_source_validation.json`: source-level check time,
  actual normalized/provider record counts, evidence state and provider error.
- `data/runtime/qadam_live_source_scheduler.json`: last attempt/success, next
  attempt and backoff; failure never advances the last-success timestamp.
- `data/runtime/qadam_source_collection_coverage.json`: all catalogue entries,
  aliases, optional/disabled services and outstanding actions.
- `data/runtime/qadam_source_capability_registry.json`: collection state alongside
  strategy relevance and evidence eligibility.
- Raw provider archives preserve the captured payload. Unknown publication times
  remain unknown; new data must mature under the existing research contracts.

New regression tests cover envelope parsing, stale/closed-market exclusion,
timestamp provenance, authentication, bounded recovery, GPS publication scope,
Yahoo column layouts, contract non-equivalence and history-scan reuse. The
existing source refresh, source matrix and Qadam regression suites are also run.

## Provider References

- [ACLED authentication](https://acleddata.com/api-documentation/getting-started)
- [UCDP API](https://ucdp.uu.se/apidocs/)
- [PatentsView Search API](https://search.patentsview.org/docs/docs/Search%20API/SearchAPIReference/)
- [GPSJAM scope and limitations](https://gpsjam.org/faq)
- [IODA v2 API](https://api.ioda.inetintel.cc.gatech.edu/v2/)
- [Polymarket market-list contract](https://docs.polymarket.com/api-reference/markets/list-markets)
- [AISStream subscription and message contract](https://aisstream.io/documentation)
- [NASA FIRMS API](https://firms2.modaps.eosdis.nasa.gov/content/academy/data_api/firms_api_use.html)
