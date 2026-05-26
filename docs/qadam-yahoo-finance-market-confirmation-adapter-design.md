# Qadam Yahoo Finance Market Confirmation Adapter Design

This design note records the P3-2A treatment of the local `yahoo-finance-api/` checkout.

## Decision

Yahoo Finance / yfinance is accepted as a supplemental read-only market-confirmation capability with classification `accepted_supplemental_pending_live_dependencies`.

It is not a canonical 36th World Monitor source, not a broker, not an execution venue, and not a reconciliation source.

## Implemented Boundary

Implemented wrapper:

- `orchestrator/yahoo_finance_adapter.py`
- `scripts/check_yahoo_finance_adapter.py`

The wrapper provides:

- Deterministic sample mode with `market_price_confirmation` events.
- Guarded live mode behind `YFINANCE_ENABLED=false` by default.
- A symbol allowlist tied to Qadam's first trading universe.
- Per-run request budgeting.
- Local raw archive writes through the existing Qadam archive envelope.
- Event Log writes for fetch attempts.
- A public-safe status shape that avoids cookies, crumb tokens, cache paths, raw HTML, and raw provider payloads.
- Zero execution, paper-order, broker-write, fill, receipt, reconciliation, live-capital, and quantum authority.

The wrapper is deliberately not wired into Phase 2, Signal Integrity, the cockpit, or the canonical source heartbeat yet.

## Runtime Controls

Environment controls:

```bash
YFINANCE_ENABLED=false
YFINANCE_CACHE_DIR=./data/runtime/yfinance-cache
YFINANCE_REQUEST_BUDGET_PER_RUN=25
YFINANCE_SYMBOL_ALLOWLIST=CL=F,BZ=F,USO,XLE,SI=F,SLV,SIL,PAAS,ITA,XAR,LMT,RTX,NOC,SMH,SOXX,NVDA,TSM,ASML,AMD,SPY,QQQ,TLT,HYG,^VIX,DX-Y.NYB
```

Live mode must stay disabled until the dependency set is deliberately installed into the active runtime and the live check passes.

## Local Checkout Findings

The local checkout is `yfinance` version `1.3.0` by source file.

Useful components:

- `Ticker` for single-symbol history, options, fundamentals, calendars, analyst data, and metadata.
- `download` and `Tickers` for multi-symbol historical data.
- `Market` for market status.
- `Search` for quote/news lookup.
- `Sector`, `Industry`, and `screen` for sector and screener context.
- `WebSocket` and `AsyncWebSocket` for streaming, deferred until later.

Live dependency footprint:

- `pandas`
- `numpy`
- `requests`
- `curl_cffi`
- `multitasking`
- `platformdirs`
- `pytz`
- `frozendict`
- `peewee`
- `beautifulsoup4`
- `protobuf`
- `websockets`
- Optional rate/cache helpers: `requests_cache`, `requests_ratelimiter`

Current active `.venv` status:

- The local checkout exists.
- Import through the local checkout fails because `pandas` is not installed.
- Sample mode does not require pandas or network access.

## Output Contract

Normalized events use:

- Source: `market.yahoo_finance`
- Event type: `market_price_confirmation`
- Trust score seed: `0.58`

Allowed normalized fields:

- `symbol`
- `instrument_name`
- `last_close`
- `previous_close`
- `percent_move`
- `volume`
- `volume_ratio`
- `rolling_volatility_20d`
- `option_chain_available`
- `market_state`
- `sample`

Disallowed public fields:

- Yahoo cookies.
- Yahoo crumb tokens.
- Local cache paths.
- Raw HTML.
- Full unfiltered provider payloads.
- Full provider tracebacks.
- Broker account identifiers.
- Fill prices, broker echoes, receipts, or order IDs.

## Consumption Rules

Phase 2 may consume Yahoo Finance context only after:

- `scripts/check_yahoo_finance_adapter.py` passes.
- Live mode either passes or is explicitly marked degraded.
- Signal Integrity treats the output as corroboration only.
- A second independent source remains required for any signal candidate.
- Public cockpit status shows only safe summary fields.

Phase 3 may consume Yahoo Finance context only as classical market-context input. It cannot make a quantum/classical oracle executable, and it cannot substitute for broker, fill, or reconciliation evidence.

## Verification

Current checks:

```bash
.venv/bin/python scripts/check_yahoo_finance_adapter.py
.venv/bin/python scripts/check_yahoo_finance_adapter.py --live
.venv/bin/python scripts/check_phase1_data_spine.py
```

Expected current result:

- Sample check passes with deterministic events.
- Live check passes as a degraded disabled state while `YFINANCE_ENABLED=false`.
- Phase 1 data spine remains 35 canonical sources and 19 promoted adapters.

