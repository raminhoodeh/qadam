# Qadam — World Monitor Integration Reference

<aside>
🔌

Per-source integration specs for all 35 World Monitor data sources described in [Qadam Specifications v3](../Qadam%20Specifications%20v3%203566fe2ecf37800abef8c5c717cc6656.md) §3.6. This is the Phase 1 build companion. The PRD describes *what* each source detects; this document specifies *how* to integrate it — auth, endpoint, request shape, response mapping, FastMCP tool definition, rate limits, and failure modes. Sources are organised by pipeline (A–E). Build order follows the Tier 1→2→3→4 priority in the PRD §3.6.

</aside>

---

# Conventions

## FastMCP Tool Naming

All 35 tools follow: `world_monitor_{pipeline}_{source_slug}`

Examples: `world_monitor_conflict_acled` · `world_monitor_physical_nasa_firms` · `world_monitor_market_unusual_whales`

## Shared Response Envelope

Every tool returns:

```json
{
  "events": [<UnifiedEventSchema>],
  "source": "pipeline_category.source_slug",
  "trust_score": 0.0,
  "fetched_at": "ISO-8601",
  "degraded": false,
  "degraded_reason": "string | null"
}
```

## Unified Event Schema (per event in `events[]`)

```json
{
  "event_id": "UUIDv7",
  "source": "string",
  "trust_score_at_ingestion": 0.0,
  "event_type": "physical_anomaly | conflict_event | market_microstructure | social_signal | macro_shift",
  "raw_payload": {},
  "normalised_summary": "string",
  "coordinates": {"lat": 0.0, "lon": 0.0},
  "ingested_at": "ISO-8601",
  "linked_catalyst_id": "string | null"
}
```

## Build Priority Tiers

- **Tier 1 — Wire first (Phase 1 Week 1):** Alpaca, ACLED, NASA FIRMS, Oref, Polymarket/pmxt, UnusualWhales
- **Tier 2 — Wire second (Phase 1 Week 1–2):** FRED, AIS, Wingbits, GDELT, RSS feeds, Twitter/X
- **Tier 3 — Wire third (Phase 1 Week 2):** BLS, ECB, UN Comtrade, BIS, USGS, Reddit, Telegram, SEC/EDGAR
- **Tier 4 — Wire last or Phase 2:** Space-Track, GPS Jamming, Internet Outage, Coinglass, Chainlink, Bookmap, GitHub, Patents, UCDP, ArcGIS, Hyperliquid

---

# Pipeline A — Geopolitical & Conflict *(The Energy of Instability)*

## A1 · ACLED API — **Tier 1**

`world_monitor_conflict_acled`

|  |  |
| --- | --- |
| **Auth** | OAuth 2.0 via `acled-oauth.mjs` (existing Node.js script) |
| **Base URL** | `https://api.acleddata.com/acled/read` |
| **Cadence** | Hourly polling |
| **Initial Trust Score** | 0.82 |
| **Latency SLA** | ≤ 60s |
| **Rate limit** | 500 requests/day (free tier); budget 24/day |

**Request shape:**

```
GET ?event_date_where=event_date>={date}&limit=500&format=json
    &fields=event_id_cnty,event_date,event_type,actor1,location,
            latitude,longitude,fatalities,notes
```

**Response → Unified Event Schema:**

- `event_type` → `conflict_event`
- `latitude`, `longitude` → `coordinates`
- `notes` → `normalised_summary` (truncated to 200 chars; Gemma 4 generates final summary)
- `event_date` → `ingested_at`

**FastMCP input schema:** `{ since: ISO-8601, region?: string, event_type_filter?: string[] }`

**Known failure modes:** OAuth token expiry (refresh every 55 minutes); API returns 429 on burst → exponential backoff

**Licensing:** ACLED data is free for non-commercial use and research. Commercial use requires a data licence. Qadam's single-operator use qualifies as research; review if community tier is added.

---

## A2 · GDELT Project API — **Tier 2**

`world_monitor_conflict_gdelt`

|  |  |
| --- | --- |
| **Auth** | None (public) |
| **Base URL** | `https://api.gdeltproject.org/api/v2/doc/doc` |
| **Cadence** | Every 15 minutes (GDELT updates every 15 min) |
| **Initial Trust Score** | 0.65 |
| **Latency SLA** | ≤ 60s |
| **Rate limit** | Unlimited (public CDN); recommend ≤ 4 req/min |

**Request shape:**

```
GET ?query={keyword}&mode=ArtList&maxrecords=250
    &startdatetime={YYYYMMDDHHMMSS}&format=json
    &SOURCELANG=eng&THEME={theme_code}
```

**Response → Unified Event Schema:**

- `event_type` → `conflict_event` or `social_signal` depending on article content
- Article URL → `raw_payload.url`; Gemma 4 extracts `normalised_summary` from headline
- No native lat/lon; geocoding applied post-ingestion for location-specific articles

**FastMCP input schema:** `{ query: string, since: ISO-8601, theme_code?: string }`

**Known failure modes:** Occasionally returns malformed JSON during high-traffic events → validate before parsing; retry after 5 minutes

**Licensing:** Fully open and free for any use.

---

## A3 · Oref API — **Tier 1**

`world_monitor_conflict_oref`

|  |  |
| --- | --- |
| **Auth** | None (public) |
| **Base URL** | `https://www.oref.org.il/WarningMessages/alert/alerts.json` |
| **Cadence** | Every 5 seconds during active hours |
| **Initial Trust Score** | 0.95 |
| **Latency SLA** | ≤ 15s |
| **Rate limit** | No documented limit; ≤ 12 req/min |

**Request shape:**

```
GET /WarningMessages/alert/alerts.json
Headers: Referer: https://www.oref.org.il/
         X-Requested-With: XMLHttpRequest
```

**Response → Unified Event Schema:**

- Returns JSON array of active alert zones (Hebrew/English city names)
- `event_type` → `conflict_event`
- Alert zones geocoded via static lookup table in repo
- `normalised_summary` → `"Red alert in {zone} ({alert_type})"`

**FastMCP input schema:** `{}` (no parameters; returns current active alerts)

**Known failure modes:** Returns `{}` when no alerts active (normal). Returns HTML during maintenance. Check `Content-Type: application/json` before parsing.

**Licensing:** Public government data; no restrictions.

---

## A4 · UCDP API — **Tier 4**

`world_monitor_conflict_ucdp`

|  |  |
| --- | --- |
| **Auth** | None (public REST API) |
| **Base URL** | `https://ucdpapi.pcr.uu.se/api/gedevents/23.1` |
| **Cadence** | Daily batch |
| **Initial Trust Score** | 0.75 |
| **Latency SLA** | ≤ 300s |
| **Rate limit** | ≤ 10 req/hour recommended |

**Request shape:**

```
GET ?PageSize=1000&page=1&StartDate={YYYY-MM-DD}&EndDate={YYYY-MM-DD}
```

**Response → Unified Event Schema:**

- `event_type` → `conflict_event`; `latitude`, `longitude` → `coordinates`
- Primary use: historical base rates for conflict escalation patterns; not real-time

**FastMCP input schema:** `{ start_date: YYYY-MM-DD, end_date: YYYY-MM-DD, country?: string }`

**Licensing:** Free for research and non-commercial use.

---

## A5 · Conflict Tracker *(Internal Derived Layer)*

`world_monitor_conflict_tracker`

Internal Orchestrator aggregation layer fusing ACLED + GDELT. No external API call. FastMCP tool queries PostgreSQL for pre-aggregated conflict scores per region per time window.

**FastMCP input schema:** `{ region_bbox: { lat_min, lat_max, lon_min, lon_max }, since: ISO-8601 }`

---

# Pipeline B — Logistics, Infrastructure & OSINT *(The Source of Truth)*

## B1 · NASA FIRMS — **Tier 1**

`world_monitor_physical_nasa_firms`

|  |  |
| --- | --- |
| **Auth** | API key (free registration at [firms.modaps.eosdis.nasa.gov](http://firms.modaps.eosdis.nasa.gov)) |
| **Base URL** | `https://firms.modaps.eosdis.nasa.gov/api/area/csv/{API_KEY}/VIIRS_SNPP_NRT/{bbox}/{days}` |
| **Cadence** | Every 3 hours (VIIRS NRT updates every 3h) |
| **Initial Trust Score** | 0.88 |
| **Latency SLA** | ≤ 30s |
| **Rate limit** | 250 requests/day free tier; budget 8/day |

**Request shape:**

```
GET /api/area/csv/{API_KEY}/VIIRS_SNPP_NRT/{bbox}/{days}
bbox: lon_min,lat_min,lon_max,lat_max   days: 1
```

**Response → Unified Event Schema:**

- CSV rows: `latitude,longitude,brightness,frp,acq_date,acq_time,confidence`
- `confidence=h` AND `frp > 50` → `event_type = physical_anomaly`
- Cross-reference coordinates against infrastructure DB (refineries, ports, power plants) → `raw_payload.infrastructure_type`

**FastMCP input schema:** `{ bbox: string, days?: number }`

**Known failure modes:** `404` when no fire data for bbox (normal, not an error). Rate limit → throttle and retry after 1 hour.

**Licensing:** Free for all uses. Attribution: "Data courtesy of NASA FIRMS."

---

## B2 · Wingbits ADS-B — **Tier 2**

`world_monitor_physical_wingbits`

|  |  |
| --- | --- |
| **Auth** | API key (Wingbits account) |
| **Base URL** | `https://api.wingbits.com/v1/aircraft` |
| **Cadence** | Every 5 minutes for watch-zone boxes |
| **Initial Trust Score** | 0.72 |
| **Latency SLA** | ≤ 30s |
| **Rate limit** | Plan-dependent; budget 288 req/day |

**Request shape:**

```
GET /v1/aircraft?bbox={lon_min},{lat_min},{lon_max},{lat_max}
                 &type=military,cargo&squawk_filter={range}
```

**Response → Unified Event Schema:**

- `event_type` → `physical_anomaly`
- `icao`, `callsign`, `altitude`, `heading`, `speed` → `raw_payload`
- Anomaly detection: unusual routing, military squawk codes, high-value cargo patterns → `normalised_summary`

**FastMCP input schema:** `{ bbox: string, aircraft_type?: string[], squawk_filter?: string }`

**Known failure modes:** Coverage gaps in some regions. Use Space-Track TLEs as fallback.

**Licensing:** Commercial use permitted.

---

## B3 · AIS Maritime (Spire / MarineTraffic) — **Tier 2**

`world_monitor_physical_ais`

|  |  |
| --- | --- |
| **Auth** | API key (Spire Maritime or MarineTraffic) |
| **Base URL** | Spire: `https://api.spire.com/v3/analytics/vessel` · MarineTraffic: `https://services.marinetraffic.com/api/exportvessels/v:8` |
| **Cadence** | Every 15 minutes for watch-zone areas |
| **Initial Trust Score** | 0.80 |
| **Latency SLA** | ≤ 30s |
| **Rate limit** | Spire: quota-based; MarineTraffic: credits-based; budget 96 req/day |

**Request shape (Spire):**

```
GET /v3/analytics/vessel?bbox={bbox}&vessel_type=TANKER,CARGO,MILITARY
    &fields=mmsi,vessel_name,lat,lon,speed,course,destination,eta,last_position_UTC
```

**Response → Unified Event Schema:**

- Anomalies: AIS dark, unusual speed/course change, congestion in Hormuz/Suez/Bab-el-Mandeb/Malacca → `event_type = physical_anomaly`
- `normalised_summary` → `"Vessel {name} ({type}) at ({lat},{lon}): {anomaly_description}"`
- Failover: Trust Score < 0.3 → Architect Agent switches to Wingbits + FIRMS triangulation

**FastMCP input schema:** `{ bbox: string, vessel_types?: string[], anomaly_only?: boolean }`

**Licensing:** Spire and MarineTraffic permit commercial use. Review redistribution restrictions if community tier is added.

---

## B4 · ArcGIS / USACE Geospatial — **Tier 4**

`world_monitor_physical_arcgis`

|  |  |
| --- | --- |
| **Auth** | None (public layers); ArcGIS token (premium layers) |
| **Base URL** | `https://services.arcgis.com/P3ePLMYs2RVChkJx/arcgis/rest/services/` |
| **Cadence** | Daily batch |
| **Initial Trust Score** | 0.70 |
| **Latency SLA** | ≤ 300s |
| **Rate limit** | Public: no limit |

**Request shape:**

```
GET /USACE_NAP_IWW/FeatureServer/0/query?where=1=1&outFields=*&f=json
```

Context layer for infrastructure status (canal closures, dam levels). Not a real-time signal source.

**FastMCP input schema:** `{ layer_url: string, where_clause?: string, bbox?: string }`

**Licensing:** USACE data is public domain. ArcGIS premium layers subject to Esri licence.

---

## B5 · Space-Track TLEs — **Tier 4**

`world_monitor_physical_space_track`

|  |  |
| --- | --- |
| **Auth** | [Space-Track.org](http://Space-Track.org) account (free) |
| **Base URL** | `https://www.space-track.org/basicspacedata/query/` |
| **Cadence** | Every 6 hours |
| **Initial Trust Score** | 0.65 |
| **Latency SLA** | ≤ 120s |
| **Rate limit** | 300 req/hour; budget 4/day |

**Request shape:**

```
GET /class/gp/EPOCH/>now-1&OBJECT_TYPE=PAYLOAD&format=json
```

Detects ISR satellite coverage gaps over conflict zones. Cross-references with ACLED/Oref. Mainly feeds Quantum batch Knowledge Graph context.

**FastMCP input schema:** `{ object_type?: string, epoch_filter?: string }`

**Licensing:** Free under Space-Track Terms of Service.

---

## B6 · GPS Jamming Monitors — **Tier 4**

`world_monitor_physical_gps_jamming`

|  |  |
| --- | --- |
| **Auth** | None (public) |
| **Base URL** | `https://gpsjam.org/api` |
| **Cadence** | Every 30 minutes |
| **Initial Trust Score** | 0.68 |
| **Latency SLA** | ≤ 120s |
| **Rate limit** | No documented limit; budget 48 req/day |

**Request shape:** `GET /api?date={YYYY-MM-DD}&bbox={bbox}`

**Response → Unified Event Schema:**

- `event_type` → `physical_anomaly`; jamming in port/shipping zones → cross-tagged `conflict_event`
- `normalised_summary` → `"GPS jamming in {region}: intensity={score}, area={km2} km²"`

**FastMCP input schema:** `{ bbox: string, min_intensity?: number }`

**Licensing:** Aggregates public ADS-B data. Free to use.

---

## B7 · Internet Outage Maps (IODA) — **Tier 4**

`world_monitor_physical_internet_outage`

|  |  |
| --- | --- |
| **Auth** | None (public) |
| **Base URL** | `https://ioda.inetintel.cc.gatech.edu/api` |
| **Cadence** | Every 30 minutes |
| **Initial Trust Score** | 0.62 |
| **Latency SLA** | ≤ 120s |
| **Rate limit** | No limit (public research API) |

**Request shape:**

```
GET /entities/signals?entityType=country&entityCode={cc}
    &from={unix_ts}&until={unix_ts}&datasource=bgp,ucsd-nt,merit-nt
```

Significant BGP withdrawal events (ASN going dark) cross-referenced with ACLED for conflict correlation.

**FastMCP input schema:** `{ country_code?: string, min_severity?: number, since?: ISO-8601 }`

**Licensing:** IODA is a Georgia Tech research project. Free for all uses.

---

# Pipeline C — Economic & Macro *(The Language of Money)*

## C1 · FRED API (Federal Reserve St. Louis) — **Tier 2**

`world_monitor_macro_fred`

|  |  |
| --- | --- |
| **Auth** | API key (free at [fred.stlouisfed.org](http://fred.stlouisfed.org)) |
| **Base URL** | `https://api.stlouisfed.org/fred/series/observations` |
| **Cadence** | Every 6 hours for fast-moving series (DXY, T-bill yields); daily for others |
| **Initial Trust Score** | 0.90 |
| **Latency SLA** | ≤ 30s |
| **Rate limit** | 120 requests/minute; practically unlimited for Qadam's usage |

**Request shape:**

```
GET /fred/series/observations?series_id={SERIES_ID}
    &api_key={KEY}&file_type=json
    &observation_start={YYYY-MM-DD}&sort_order=desc&limit=10
```

**Priority series to monitor:**

| Series ID | Description | Cadence |
| --- | --- | --- |
| `DFF` | Fed Funds Rate | Daily |
| `DGS10` | 10-Year Treasury Yield | Daily |
| `DGS2` | 2-Year Treasury Yield | Daily |
| `T10Y2Y` | Yield Curve (10Y–2Y) | Daily |
| `DTWEXBGS` | Broad Dollar Index | Daily |
| `VIXCLS` | VIX | Daily |
| `BAMLH0A0HYM2` | HY Credit Spread | Daily |
| `IORB` | Interest on Reserve Balances | Daily |

**Response → Unified Event Schema:**

- `event_type` → `macro_shift`
- `value`, `date`, `series_id` → `raw_payload`
- Shift detection: value change > 2σ from 20-day rolling mean → `normalised_summary` → `"{series} moved {delta} ({pct_change}%) — {sigma}σ deviation"`
- No coordinates (macro data; `coordinates: null`)

**FastMCP input schema:** `{ series_id: string, since?: YYYY-MM-DD, alert_on_sigma?: number }`

**Known failure modes:** FRED occasionally lags by one business day on release dates. Cross-check with BLS/ECB if critical timing.

**Licensing:** FRED data is in the public domain. Attribution recommended.

---

## C2 · BLS API (Bureau of Labor Statistics) — **Tier 3**

`world_monitor_macro_bls`

|  |  |
| --- | --- |
| **Auth** | API key (free registration at [api.bls.gov](http://api.bls.gov)) |
| **Base URL** | `https://api.bls.gov/publicAPI/v2/timeseries/data/` |
| **Cadence** | Daily check; event-driven on release calendar |
| **Initial Trust Score** | 0.88 |
| **Latency SLA** | ≤ 60s |
| **Rate limit** | 500 queries/day (registered); 25 series per query |

**Request shape:**

```json
POST /publicAPI/v2/timeseries/data/
{
  "seriesid": ["CUSR0000SA0", "LNS14000000", "PRS85006092"],
  "startyear": "{YYYY}",
  "endyear": "{YYYY}",
  "registrationkey": "{KEY}"
}
```

**Priority series:** CPI (`CUSR0000SA0`), Unemployment Rate (`LNS14000000`), Non-farm Productivity (`PRS85006092`), PCE proxy.

**Response → Unified Event Schema:**

- `event_type` → `macro_shift`
- Release surprises (actual vs. consensus from Polymarket/Kalshi) → high-priority flag
- `normalised_summary` → `"{series}: actual={value}, consensus={consensus}, surprise={delta}"`

**FastMCP input schema:** `{ series_ids: string[], year?: number, alert_on_surprise?: boolean }`

**Known failure modes:** BLS API is down on federal holidays and occasionally around major release times (high traffic) → retry with exponential backoff; fallback to FRED equivalent series.

**Licensing:** US government data, public domain.

---

## C3 · ECB Data Portal — **Tier 3**

`world_monitor_macro_ecb`

|  |  |
| --- | --- |
| **Auth** | None (public REST API) |
| **Base URL** | `https://data-api.ecb.europa.eu/service/data/` |
| **Cadence** | Daily |
| **Initial Trust Score** | 0.85 |
| **Latency SLA** | ≤ 60s |
| **Rate limit** | No documented limit; budget 10 req/day |

**Request shape:**

```
GET /service/data/FM/B.U2.EUR.4F.KR.MRR_FR.LEV
    ?format=jsondata&detail=dataonly&lastNObservations=5
```

**Priority data:** ECB main refinancing rate, EUR/USD spot, Eurozone inflation expectation series, TARGET2 balances.

**Response → Unified Event Schema:**

- `event_type` → `macro_shift`
- Rate change or surprise guidance → `normalised_summary`
- No coordinates; `coordinates: null`

**FastMCP input schema:** `{ flow_ref: string, key: string, last_n_observations?: number }`

**Known failure modes:** SDMX API format can change between releases; pin to `format=jsondata`. Check ECB release calendar for surprise events.

**Licensing:** ECB data is free for all uses.

---

## C4 · UN Comtrade API — **Tier 3**

`world_monitor_macro_un_comtrade`

|  |  |
| --- | --- |
| **Auth** | API key (free Comtrade+ subscription) |
| **Base URL** | `https://comtradeapi.un.org/data/v1/get/` |
| **Cadence** | Weekly batch (Comtrade updates monthly) |
| **Initial Trust Score** | 0.78 |
| **Latency SLA** | ≤ 300s (batch) |
| **Rate limit** | 100 requests/hour on free tier |

**Request shape:**

```
GET /C/M/{period}?reporterCode={iso3}&flowCode=M
    &cmdCode={hs_code}&partnerCode=0&format=JSON
    &subscription-key={KEY}
```

**Focus commodities:** HS 2709 (crude oil), HS 2701 (coal), HS 26 (ores), HS 10 (cereals).

**Response → Unified Event Schema:**

- `event_type` → `macro_shift`
- Unusual import/export flow changes for strategic commodities → flag for Gemini's geopolitical reasoning
- No real-time latency; used as context layer for trade-flow thesis support

**FastMCP input schema:** `{ reporter_code: string, hs_codes: string[], period: YYYYMM, flow?: "M" | "X" }`

**Licensing:** UN Comtrade data is free for research and non-commercial use.

---

## C5 · BIS Statistics — **Tier 3**

`world_monitor_macro_bis`

|  |  |
| --- | --- |
| **Auth** | None (public) |
| **Base URL** | `https://stats.bis.org/api/v1/data/` |
| **Cadence** | Weekly batch |
| **Initial Trust Score** | 0.80 |
| **Latency SLA** | ≤ 300s (batch) |
| **Rate limit** | No documented limit |

**Request shape:**

```
GET /CBS/Q.S.5J.W.A.A.TO1.A?format=jsondata&lastNObservations=4
```

**Focus data:** Global cross-border bank credit flows, FX reserves, derivatives market stats. Used as context layer for systemic risk thesis support (e.g., EM credit stress preceding FX volatility).

**FastMCP input schema:** `{ dataset: string, key: string, last_n?: number }`

**Licensing:** BIS statistics are free for all uses.

---

## C6 · USGS Commodity Statistics — **Tier 3**

`world_monitor_macro_usgs`

|  |  |
| --- | --- |
| **Auth** | None (public) |
| **Base URL** | `https://minerals.usgs.gov/minerals/pubs/mcs/` (static reports) + `https://mrdata.usgs.gov/api/` |
| **Cadence** | Weekly batch (USGS updates quarterly) |
| **Initial Trust Score** | 0.75 |
| **Latency SLA** | ≤ 300s |
| **Rate limit** | No documented limit |

**Focus data:** Critical minerals production (lithium, cobalt, nickel, rare earths, copper). Supply disruption events cross-referenced with ACLED/AIS for mining region conflict context.

**FastMCP input schema:** `{ commodity: string, year?: number }`

**Known failure modes:** USGS data is updated irregularly; cache responses for 7 days. Primary use is long-cycle context (quarterly), not real-time signal.

**Licensing:** US government data, public domain.

---

# Pipeline D — Market Microstructure *(The Paper Reality)*

## D1 · UnusualWhales — **Tier 1**

`world_monitor_market_unusual_whales`

|  |  |
| --- | --- |
| **Auth** | API key (UnusualWhales Pro subscription) |
| **Base URL** | `https://api.unusualwhales.com/api/option-trades/flow-alerts` |
| **Cadence** | Every 5 minutes during market hours; every 30 min pre/post-market |
| **Initial Trust Score** | 0.83 |
| **Latency SLA** | ≤ 30s |
| **Rate limit** | Depends on plan; budget 200 req/day |

**Request shape:**

```
GET /api/option-trades/flow-alerts
    ?min_premium=50000&limit=100
    &since={ISO-8601}&type=SWEEP,BLOCK
Headers: Authorization: Token {KEY}
```

**Response → Unified Event Schema:**

- `event_type` → `market_microstructure`
- `ticker`, `strike`, `expiry`, `type` (call/put), `premium`, `sentiment`, `is_sweep` → `raw_payload`
- `normalised_summary` → `"Large {type} sweep on {ticker}: ${premium} at {strike} exp {expiry} — {sentiment}"`
- No geographic coordinates; `coordinates: null`

**FastMCP input schema:** `{ min_premium?: number, tickers?: string[], since?: ISO-8601, flow_type?: string[] }`

**Known failure modes:** API rate-limits during high-volume market events (earnings, FOMC). Cache last response; retry with 30s backoff. Trust Score self-corrects via backtesting if flow signals are consistently misleading.

**Licensing:** Commercial API — subscription required. Data may not be redistributed.

---

## D2 · Polymarket / Kalshi (Prediction Markets) — **Tier 1**

`world_monitor_market_polymarket`

|  |  |
| --- | --- |
| **Auth** | Polymarket: None for public markets (CLOB API). Kalshi: API key. |
| **Base URL** | Polymarket: `https://clob.polymarket.com/markets` · Kalshi: `https://trading-api.kalshi.com/trade-api/v2/markets` |
| **Cadence** | Every 5 minutes |
| **Initial Trust Score** | 0.79 |
| **Latency SLA** | ≤ 30s |
| **Rate limit** | Polymarket: no documented limit; Kalshi: 100 req/min |

**Request shape (Polymarket CLOB):**

```
GET /markets?active=true&closed=false
GET /book?token_id={market_token_id}  (for specific market orderbook)
```

**Response → Unified Event Schema:**

- `event_type` → `market_microstructure`
- `market_slug`, `question`, `yes_price`, `no_price`, `volume_24h`, `liquidity` → `raw_payload`
- Significant price moves (>5% shift in 1h) → `normalised_summary` → `"Prediction market {question}: YES moved {delta} to {price} on ${volume} volume"`
- Key markets to track: Fed rate decisions, geopolitical events, election outcomes, commodity prices

**FastMCP input schema:** `{ market_slugs?: string[], min_volume?: number, price_move_threshold?: number }`

**Known failure modes:** Polymarket is blockchain-based; CLOB API occasionally returns stale orderbook data during network congestion. Cross-check with Kalshi for confirmation.

**Licensing:** Polymarket and Kalshi are commercial platforms. Public market data is freely accessible; trading activity is subject to their Terms of Service.

---

## D3 · Alpaca Markets API — **Tier 1**

`world_monitor_market_alpaca`

|  |  |
| --- | --- |
| **Auth** | API key + secret (Alpaca paper or live account) |
| **Base URL** | `https://data.alpaca.markets/v2/` (data) · `https://api.alpaca.markets/v2/` (trading) |
| **Cadence** | Real-time streaming via WebSocket during market hours; REST polling every 5 min otherwise |
| **Initial Trust Score** | 0.90 |
| **Latency SLA** | ≤ 5s (streaming) / ≤ 30s (REST) |
| **Rate limit** | 200 requests/min (data API); unlimited WebSocket |

**Request shapes:**

```
# Options chain (REST)
GET /v1beta1/options/snapshots/{underlying_symbol}
    ?feed=opra&limit=100
    Headers: APCA-API-KEY-ID / APCA-API-SECRET-KEY

# Real-time trades (WebSocket)
ws://stream.data.alpaca.markets/v2/iex
{ "action": "subscribe", "trades": ["AAPL","SPY"], "quotes": ["SPY"] }

# Historical bars (REST)
GET /v2/stocks/{symbol}/bars?timeframe=5Min&start={ISO-8601}
```

**Response → Unified Event Schema:**

- `event_type` → `market_microstructure`
- This is the **primary broker adapter** for Layer B execution (§7.2) as well as the options chain data source for Job 2 (Strategy Collapse)
- IV surface data, bid/ask spreads, volume, OI → `raw_payload`
- `normalised_summary` → `"{symbol} options: IV={iv_pct}%, max pain={strike}, volume={vol}, OI={oi}"`

**FastMCP input schema:** `{ symbol: string, expiry_range?: { min_dte: number, max_dte: number }, strike_range?: { pct_otm_min, pct_otm_max } }`

**Known failure modes:** WebSocket disconnects → auto-reconnect with 5s delay; use REST backup. Options data unavailable outside market hours → cache last snapshot.

**Licensing:** Alpaca API is free for market data (SIP feed requires paid plan). Paper trading is free. Live trading subject to broker agreement.

---

## D4 · Coinglass — **Tier 4**

`world_monitor_market_coinglass`

|  |  |
| --- | --- |
| **Auth** | API key (Coinglass Pro) |
| **Base URL** | `https://open-api.coinglass.com/public/v2/` |
| **Cadence** | Every 15 minutes |
| **Initial Trust Score** | 0.65 |
| **Latency SLA** | ≤ 60s |
| **Rate limit** | 30 req/min on free; 300 req/min Pro |

**Request shape:**

```
GET /liquidation_history?ex=Binance&symbol=BTCUSDT
    &interval=h1&limit=24
Headers: coinglassSecret: {KEY}
```

**Focus data:** Large liquidation cascades in BTC/ETH futures as proxy for broader risk-off sentiment. Liquidation spikes often precede equity futures moves in the same session. Also: funding rates, long/short ratios.

**FastMCP input schema:** `{ symbol: string, exchange?: string, lookback_hours?: number }`

**Licensing:** Coinglass data is for internal use only; redistribution restricted.

---

## D5 · Bookmap / Order Flow — **Tier 4**

`world_monitor_market_bookmap`

|  |  |
| --- | --- |
| **Auth** | Bookmap account + local WebSocket bridge |
| **Base URL** | Local WebSocket: `ws://localhost:8765/bookmap` (Bookmap runs locally on M5) |
| **Cadence** | Real-time streaming during market hours |
| **Initial Trust Score** | 0.70 |
| **Latency SLA** | ≤ 1s (local) |
| **Rate limit** | N/A (local process) |

**Architecture note:** Bookmap does not have a public REST API. Integration requires a local Python WebSocket bridge that subscribes to Bookmap's internal event stream and re-publishes to the Orchestrator. This bridge runs as a background process on the M5.

**Response → Unified Event Schema:**

- `event_type` → `market_microstructure`
- Liquidity clusters, iceberg order detection, volume absorption events → `raw_payload`
- `normalised_summary` → `"Significant liquidity cluster at {price} on {symbol}: {interpretation}"`

**FastMCP input schema:** `{ symbol: string, lookback_seconds?: number }`

**Known failure modes:** Local process dependency — if Bookmap is not running, tool returns `degraded: true`. Architect Agent treats Bookmap degradation as non-critical; Alpaca WebSocket data is sufficient fallback.

**Licensing:** Bookmap is a commercial application. Internal use only.

---

## D6 · Chainlink Price Feeds — **Tier 4**

`world_monitor_market_chainlink`

|  |  |
| --- | --- |
| **Auth** | Ethereum RPC endpoint (Alchemy or Infura — free tier) |
| **Base URL** | Alchemy: `https://eth-mainnet.g.alchemy.com/v2/{KEY}` |
| **Cadence** | Every 10 minutes |
| **Initial Trust Score** | 0.72 |
| **Latency SLA** | ≤ 30s |
| **Rate limit** | Alchemy free: 300M compute units/month; budget ~50 req/day |

**Request shape ([web3.py](http://web3.py)):**

```python
contract = web3.eth.contract(address=CHAINLINK_FEED_ADDRESS, abi=AGGREGATOR_ABI)
latest = contract.functions.latestRoundData().call()
# Returns: (roundId, answer, startedAt, updatedAt, answeredInRound)
```

**Focus feeds:** ETH/USD, BTC/USD, EUR/USD, XAU/USD, crude oil proxies. Used as tamper-proof price reference for cross-validation of Alpaca price data — if Chainlink and Alpaca diverge by >0.5%, flag for manual review.

**FastMCP input schema:** `{ feed_address: string, network?: string }`

**Licensing:** Chainlink feeds are on-chain public data. Free to read.

---

## D7 · Hyperliquid Perps — **Tier 4**

`world_monitor_market_hyperliquid`

|  |  |
| --- | --- |
| **Auth** | None (public API) |
| **Base URL** | `https://api.hyperliquid.xyz/info` |
| **Cadence** | Every 15 minutes |
| **Initial Trust Score** | 0.65 |
| **Latency SLA** | ≤ 30s |
| **Rate limit** | No documented limit; budget 96 req/day |

**Request shape:**

```
POST /info
{ "type": "metaAndAssetCtxs" }
```

**Focus data:** Open interest, funding rates, and liquidation data for perpetual futures on major crypto assets. Complements Coinglass. Cross-chain perp sentiment as risk-off/risk-on proxy.

**FastMCP input schema:** `{ assets?: string[], metric?: "funding" | "oi" | "liquidations" }`

**Licensing:** Public on-chain data. Free to use.

---

# Pipeline E — Social & Narrative *(The Collective Nervous System)*

## E1 · RSS Aggregator (Reuters, AP, Bloomberg headlines) — **Tier 2**

`world_monitor_social_rss`

|  |  |
| --- | --- |
| **Auth** | None (public RSS); Bloomberg RSS requires subscription |
| **Base URL** | Reuters: `https://feeds.reuters.com/reuters/businessNews` · AP: `https://rsshub.app/apnews/topics/business` · Bloomberg: `https://feeds.bloomberg.com/markets/news.rss` |
| **Cadence** | Every 5 minutes |
| **Initial Trust Score** | 0.78 |
| **Latency SLA** | ≤ 30s |
| **Rate limit** | No limits on public feeds |

**Request shape:** Standard HTTP GET to RSS endpoint; parse XML via `feedparser`.

**Response → Unified Event Schema:**

- `event_type` → `social_signal`
- `title`, `link`, `published`, `summary` → `raw_payload`
- Gemma 4 classifies headline relevance (relevant/not-relevant to Manifested Strategy watch-list); relevant headlines forwarded to Gemini
- `normalised_summary` → Gemma 4 one-sentence summary
- Deduplication: hash `title + published` to prevent duplicate event ingestion

**FastMCP input schema:** `{ feed_urls: string[], since?: ISO-8601, keyword_filter?: string[] }`

**Known failure modes:** Feed URLs change without notice → check monthly; maintain a fallback URL list in the config file.

**Licensing:** RSS feeds are publicly syndicated. Attribution to source required in any display context.

---

## E2 · Twitter / X API — **Tier 2**

`world_monitor_social_twitter`

|  |  |
| --- | --- |
| **Auth** | Bearer token (X API v2 Basic or Pro tier) |
| **Base URL** | `https://api.twitter.com/2/tweets/search/recent` |
| **Cadence** | Every 15 minutes |
| **Initial Trust Score** | 0.60 |
| **Latency SLA** | ≤ 60s |
| **Rate limit** | Basic: 60 req/15min; 1M tweets/month. Budget 4 req/15min per saved search. |

**Request shape:**

```
GET /2/tweets/search/recent
    ?query={query}&tweet.fields=created_at,author_id,public_metrics
    &expansions=author_id&max_results=100
    &start_time={ISO-8601}
Headers: Authorization: Bearer {TOKEN}
```

**Saved searches to maintain:**

- Breaking geopolitical news from verified journalists (list-based search)
- $TICKER + (options OR unusual OR whale) — per Manifested Strategy watch-list tickers
- Macro policy surprise language ("surprise hike", "emergency meeting", "flash crash")

**Response → Unified Event Schema:**

- `event_type` → `social_signal`
- High-engagement tweets (retweet_count > 500 in < 30 min) from verified accounts → elevated priority
- Gemma 4 performs sentiment classification (bullish/bearish/neutral) + entity extraction
- `normalised_summary` → Gemma 4 one-sentence summary; `raw_payload.engagement_velocity` added

**FastMCP input schema:** `{ query: string, since?: ISO-8601, min_retweets?: number, verified_only?: boolean }`

**Known failure modes:** X API rate limits are enforced strictly. Implement a per-search request budget to prevent exhausting the monthly cap on one query. Trust Score penalised for high noise-to-signal ratio on crypto-adjacent searches.

**Licensing:** X API Basic/Pro subscription required. Tweet content may not be stored for more than 30 days under X Developer Agreement.

---

## E3 · Reddit API — **Tier 3**

`world_monitor_social_reddit`

|  |  |
| --- | --- |
| **Auth** | OAuth 2.0 (Reddit app registration, free) |
| **Base URL** | `https://oauth.reddit.com/r/{subreddit}/new` |
| **Cadence** | Every 30 minutes |
| **Initial Trust Score** | 0.55 |
| **Latency SLA** | ≤ 60s |
| **Rate limit** | 100 req/minute (authenticated) |

**Target subreddits:** r/wallstreetbets, r/options, r/stocks, r/investing, r/MacroEconomics, r/geopolitics

**Request shape:**

```
GET /r/{subreddit}/new?limit=100&after={before_id}
Headers: Authorization: Bearer {TOKEN}
         User-Agent: Qadam/1.0
```

**Response → Unified Event Schema:**

- `event_type` → `social_signal`
- High-upvote posts (score > 1000 in < 2 hours) on financial subreddits → elevated priority
- Gemma 4 sentiment classification + entity extraction
- `normalised_summary` generated by Gemma 4
- Note: Reddit is a **confirmation signal** at best; never a primary signal. Trust Score reflects this.

**FastMCP input schema:** `{ subreddits: string[], since?: ISO-8601, min_score?: number, keyword_filter?: string[] }`

**Licensing:** Reddit API is free for non-commercial use. Commercial use requires a Data API licence. Review if Qadam is commercialised.

---

## E4 · Telegram Public Channels — **Tier 3**

`world_monitor_social_telegram`

|  |  |
| --- | --- |
| **Auth** | Telegram Bot API token + Telethon user session |
| **Base URL** | Bot API: `https://api.telegram.org/bot{TOKEN}/` · Telethon: MTProto (direct connection) |
| **Cadence** | Real-time via webhook or long-polling |
| **Initial Trust Score** | 0.58 |
| **Latency SLA** | ≤ 15s |
| **Rate limit** | Bot API: 30 messages/second; Telethon: subject to Telegram's flood limits |

**Target channels:** OSINT aggregators (e.g., Intel Slava Z, OSINTtechnical), regional geopolitical news channels, select financial analysis channels. Channel list maintained in config; not hardcoded.

**Response → Unified Event Schema:**

- `event_type` → `social_signal` or `conflict_event` depending on Gemma 4 classification
- `message_text`, `channel_name`, `message_id`, `date` → `raw_payload`
- Gemma 4 performs language detection + translation if non-English + relevance classification
- High-confidence conflict events from OSINT channels → cross-referenced with ACLED before elevating priority

**FastMCP input schema:** `{ channel_usernames: string[], since?: ISO-8601, language_filter?: string[] }`

**Known failure modes:** Telegram restricts bulk message fetching for accounts without established session history. Use a dedicated Telethon session that has been active for >30 days before production use. Bot API cannot read channel history — Telethon user session required.

**Licensing:** Scraping public Telegram channels is in a grey zone. For single-operator use, risk is low. Do not redistribute channel content.

---

## E5 · SEC EDGAR API — **Tier 3**

`world_monitor_social_sec_edgar`

|  |  |
| --- | --- |
| **Auth** | None (public EDGAR API; User-Agent header required) |
| **Base URL** | `https://efts.sec.gov/LATEST/search-index?q={query}` · `https://data.sec.gov/submissions/CIK{cik}.json` |
| **Cadence** | Every 30 minutes (new filings check); daily for insider transactions |
| **Initial Trust Score** | 0.82 |
| **Latency SLA** | ≤ 60s |
| **Rate limit** | 10 req/second; use User-Agent header per SEC Fair Access policy |

**Request shape:**

```
# Full-text search for new filings
GET https://efts.sec.gov/LATEST/search-index
    ?q="material+adverse"&dateRange=custom
    &startdt={YYYY-MM-DD}&enddt={YYYY-MM-DD}
    &forms=8-K,10-Q,SC+13D,Form+4
Headers: User-Agent: Qadam/1.0 (raminhoodeh@gmail.com)

# Insider transaction monitoring
GET https://data.sec.gov/submissions/CIK{cik}.json
```

**Focus filing types:** 8-K (material events), SC 13D/G (activist positions), Form 4 (insider transactions on watch-list tickers), 13F (institutional holdings quarterly).

**Response → Unified Event Schema:**

- `event_type` → `social_signal` (for narrative) or `market_microstructure` (for insider/institutional flows)
- `form_type`, `entity_name`, `cik`, `filed_at`, `filing_url` → `raw_payload`
- Gemma 4 extracts key facts from 8-K headline text
- Large insider buys/sells on watch-list tickers → elevated priority

**FastMCP input schema:** `{ form_types: string[], tickers?: string[], ciks?: string[], since?: ISO-8601 }`

**Licensing:** All EDGAR data is public domain.

---

## E6 · GitHub Trending / Commit Activity — **Tier 4**

`world_monitor_social_github`

|  |  |
| --- | --- |
| **Auth** | GitHub PAT (fine-grained, read-only) |
| **Base URL** | `https://api.github.com/` |
| **Cadence** | Daily |
| **Initial Trust Score** | 0.50 |
| **Latency SLA** | ≤ 60s |
| **Rate limit** | 5,000 req/hour (authenticated) |

**Focus:** Unusual commit spikes on repositories related to watch-list companies (e.g., a critical infrastructure provider's repo going dark, or a defence contractor's public repos showing anomalous activity). Also: new open-source releases from quantum computing or AI companies that could affect Qadam's own stack.

**Request shape:**

```
GET /repos/{owner}/{repo}/commits?since={ISO-8601}&per_page=100
GET /search/repositories?q=topic:quantum-computing+pushed:>{date}
```

**FastMCP input schema:** `{ repos?: string[], topics?: string[], since?: ISO-8601 }`

**Note:** Trust Score is low; this is a weak signal source. Primary value is detecting tech-sector catalyst precursors (AI model releases, quantum hardware announcements).

**Licensing:** GitHub public repository data is freely accessible under GitHub's Terms of Service.

---

## E7 · Patent Filings (USPTO / EPO) — **Tier 4**

`world_monitor_social_patents`

|  |  |
| --- | --- |
| **Auth** | None (public APIs) |
| **Base URL** | USPTO: `https://api.patentsview.org/patents/query` · EPO OPS: `https://ops.epo.org/3.2/rest-services/` |
| **Cadence** | Weekly batch |
| **Initial Trust Score** | 0.48 |
| **Latency SLA** | ≤ 300s |
| **Rate limit** | PatentsView: no limit; EPO OPS: 4,000 requests/week |

**Focus:** Unusual patent filing clusters from specific companies in strategic sectors (semiconductor, energy, defence, biotech). A spike in patent filings from a company in a specific technology area can precede an M&A announcement or a major product launch by 6–18 months. Long-lead-time signal; feeds the Knowledge Graph, not the real-time triage layer.

**Request shape (PatentsView):**

```json
POST /patents/query
{
  "q": { "_and": [ {"_gte": {"patent_date": "{YYYY-MM-DD}"}},
                   {"_text_any": {"patent_abstract": "{keywords}"}} ]},
  "f": ["patent_id", "patent_title", "assignee_organization", "patent_date"],
  "o": {"per_page": 100}
}
```

**FastMCP input schema:** `{ assignee_keywords?: string[], abstract_keywords?: string[], since?: YYYY-MM-DD }`

**Licensing:** USPTO data is public domain. EPO OPS data is free for non-commercial use.

---

## E8 · RapidAPI Hub (Catch-All Connector) — **Tier 3**

`world_monitor_social_rapidapi`

|  |  |
| --- | --- |
| **Auth** | RapidAPI key (single key covers all subscribed APIs) |
| **Base URL** | `https://rapidapi.com/hub` (varies per subscribed API) |
| **Cadence** | Per-source cadence (varies) |
| **Initial Trust Score** | 0.60 (varies by underlying source) |
| **Latency SLA** | ≤ 120s |
| **Rate limit** | Per-source plan limits |

**Purpose:** RapidAPI serves as the integration layer for niche data sources that don't have their own production-grade APIs. Initial candidates:

- Political speech sentiment APIs
- Executive travel pattern trackers
- Corporate jet tracking (supplementing Wingbits)
- Alternative news aggregators

**Architecture:** The `world_monitor_social_rapidapi` FastMCP tool is a parametric wrapper — `api_id` specifies which RapidAPI endpoint to call. Each underlying source gets its own Trust Score in the PostgreSQL Trust Score table.

**FastMCP input schema:** `{ api_id: string, endpoint: string, params: Record<string, unknown> }`

**Licensing:** Each RapidAPI source has its own licence terms. Review individually before production use.

---

# Source Summary Table

| **ID** | **Name** | **Pipeline** | **Tier** | **FastMCP Tool** | **Initial Trust Score** | **Cadence** |
| --- | --- | --- | --- | --- | --- | --- |
| A1 | ACLED | Conflict | 1 | `world_monitor_conflict_acled` | 0.82 | Hourly |
| A2 | GDELT | Conflict | 2 | `world_monitor_conflict_gdelt` | 0.65 | 15 min |
| A3 | Oref | Conflict | 1 | `world_monitor_conflict_oref` | 0.95 | 5 sec |
| A4 | UCDP | Conflict | 4 | `world_monitor_conflict_ucdp` | 0.75 | Daily |
| A5 | Conflict Tracker | Conflict | 1 | `world_monitor_conflict_tracker` | Derived | Derived |
| B1 | NASA FIRMS | Physical | 1 | `world_monitor_physical_nasa_firms` | 0.88 | 3 hr |
| B2 | Wingbits ADS-B | Physical | 2 | `world_monitor_physical_wingbits` | 0.72 | 5 min |
| B3 | AIS Maritime | Physical | 2 | `world_monitor_physical_ais` | 0.80 | 15 min |
| B4 | ArcGIS | Physical | 4 | `world_monitor_physical_arcgis` | 0.70 | Daily |
| B5 | Space-Track TLEs | Physical | 4 | `world_monitor_physical_space_track` | 0.65 | 6 hr |
| B6 | GPS Jamming | Physical | 4 | `world_monitor_physical_gps_jamming` | 0.68 | 30 min |
| B7 | Internet Outage (IODA) | Physical | 4 | `world_monitor_physical_internet_outage` | 0.62 | 30 min |
| C1 | FRED | Macro | 2 | `world_monitor_macro_fred` | 0.90 | 6 hr |
| C2 | BLS | Macro | 3 | `world_monitor_macro_bls` | 0.88 | Event-driven |
| C3 | ECB | Macro | 3 | `world_monitor_macro_ecb` | 0.85 | Daily |
| C4 | UN Comtrade | Macro | 3 | `world_monitor_macro_un_comtrade` | 0.78 | Weekly |
| C5 | BIS Statistics | Macro | 3 | `world_monitor_macro_bis` | 0.80 | Weekly |
| C6 | USGS Commodities | Macro | 3 | `world_monitor_macro_usgs` | 0.75 | Weekly |
| D1 | UnusualWhales | Market | 1 | `world_monitor_market_unusual_whales` | 0.83 | 5 min |
| D2 | Polymarket / Kalshi | Market | 1 | `world_monitor_market_polymarket` | 0.79 | 5 min |
| D3 | Alpaca | Market | 1 | `world_monitor_market_alpaca` | 0.90 | Real-time |
| D4 | Coinglass | Market | 4 | `world_monitor_market_coinglass` | 0.65 | 15 min |
| D5 | Bookmap | Market | 4 | `world_monitor_market_bookmap` | 0.70 | Real-time |
| D6 | Chainlink | Market | 4 | `world_monitor_market_chainlink` | 0.72 | 10 min |
| D7 | Hyperliquid | Market | 4 | `world_monitor_market_hyperliquid` | 0.65 | 15 min |
| E1 | RSS Feeds | Social | 2 | `world_monitor_social_rss` | 0.78 | 5 min |
| E2 | Twitter / X | Social | 2 | `world_monitor_social_twitter` | 0.60 | 15 min |
| E3 | Reddit | Social | 3 | `world_monitor_social_reddit` | 0.55 | 30 min |
| E4 | Telegram | Social | 3 | `world_monitor_social_telegram` | 0.58 | Real-time |
| E5 | SEC EDGAR | Social | 3 | `world_monitor_social_sec_edgar` | 0.82 | 30 min |
| E6 | GitHub | Social | 4 | `world_monitor_social_github` | 0.50 | Daily |
| E7 | Patents (USPTO/EPO) | Social | 4 | `world_monitor_social_patents` | 0.48 | Weekly |
| E8 | RapidAPI Hub | Social | 3 | `world_monitor_social_rapidapi` | 0.60 | Varies |