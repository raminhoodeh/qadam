# Unusual Whales Historical Research Integration

## Purpose

Qadam can collect Unusual Whales market-positioning data as a supplemental,
time-bounded feature set for later historical backtests. The adapter is ready,
but it is disabled by default and has not called the provider.

Fresh provider access ends on 2026-07-21 in `Asia/Dubai`. After that date the
adapter fails closed and previously captured normalized features remain
archive-only.

This integration is not a live Qadam source-quorum adapter. It cannot create a
signal, hypothesis, trade candidate, approval, paper order, broker write, or
proof credit.

## Registered Data

The default bounded capture plan includes:

- Market Tide for broad options sentiment and regime context.
- Unusual flow alerts for signal generation, lead-lag confirmation, and entry confirmation.
- Ticker dark-pool prints for institutional and divergence confirmation.
- Ticker options-volume history for put/call, premium, open-interest, and regime features.

Optional allowlisted endpoints can add net-premium ticks, Greeks, spot gamma
exposure, and interpolated implied volatility. The adapter does not use the
full options tape endpoint because access and commercial entitlement must be
validated separately.

The default symbol set is limited to Qadam's US-listed paper-research proxies:
`BNO`, `GLD`, `ITA`, `LMT`, `NVDA`, `PPA`, `QQQ`, `SIL`, `SLV`, `SMH`, `SOXX`,
`SPY`, `USO`, `XAR`, and `XLE`.

## Storage And Lineage

Normalized research data is stored below:

```text
data/research/unusual_whales/
  normalized/
  metadata/
  manifests/
  raw/                 # only when separately approved
```

Runtime lineage is exported through:

```text
data/runtime/unusual_whales_research_status.json
data/runtime/unusual_whales_backtest_feature_manifest.json
data/runtime/unusual_whales_capture_plan.json
data/runtime/unusual_whales_capture_run_summary.json
```

Each normalized feature records `event_at`, conservative `available_at`,
`retrieved_at`, capture identity, parser version, source endpoint, instrument,
and point-in-time eligibility. Historical joins only accept features whose
`available_at` is not later than the score timestamp.

## Readiness Check

The default command plans the capture without network access:

```bash
.venv/bin/python scripts/run_unusual_whales_historical_capture.py \
  --start-date 2026-07-01 \
  --end-date 2026-07-14
```

Run the offline contract check with:

```bash
.venv/bin/python scripts/check_unusual_whales_historical_research.py
```

## Enabling Capture

The token previously pasted into chat must be revoked and rotated before use.
Store only the replacement token as `UNUSUAL_WHALES_API_KEY` in Qadam's strict
local secret store. Do not put it in tracked files, command arguments, logs, or
dashboard data.

Set the non-secret controls only after provider terms and retention rights have
been reviewed:

```text
UNUSUAL_WHALES_RESEARCH_ENABLED=true
UNUSUAL_WHALES_PROVIDER_TERMS_REVIEWED=true
```

Then run a deliberately bounded capture on or before 2026-07-21:

```bash
.venv/bin/python scripts/run_unusual_whales_historical_capture.py \
  --allow-network \
  --provider-terms-reviewed \
  --start-date 2026-07-01 \
  --end-date 2026-07-14 \
  --max-requests 250
```

Raw provider payloads remain off by default. They require both
`UNUSUAL_WHALES_RAW_RETENTION_ALLOWED=true` and `--retain-raw` after the
provider's storage terms have been confirmed.

## Backtest Integration

Once features exist, refresh the normal historical chain:

```bash
.venv/bin/python scripts/check_qadam_source_provider_capabilities.py
.venv/bin/python scripts/check_qadam_provider_backfill.py
.venv/bin/python scripts/check_qadam_pattern_score_tape.py
.venv/bin/python scripts/check_qadam_statistical_backtest.py
```

The frozen backtest protocol registers five required comparisons:

1. Qadam core without Unusual Whales.
2. Qadam core plus Unusual Whales.
3. Unusual Whales only.
4. Time-shifted negative control.
5. Shuffled negative control.

Unusual Whales is supplemental: missing trial data does not block Qadam's core
historical work, and provider-only results cannot replace the Qadam baseline.
No comparison can validate an edge without the existing chronological folds,
purging, embargo, cost, multiple-testing, untouched-holdout, and quantum review
gates.
