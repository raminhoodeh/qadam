# Qadam API Key Acquisition Plan

This is the working plan for getting Qadam's provider keys without overspending or leaking secrets.

Principle: acquire keys in batches, test one provider at a time, and only pay for a source after the free/public spine proves that Qadam can use it.

## 1. Secret Handling Rule

Never paste keys into chat, docs, Git, screenshots, or the public dashboard.

All real values go here only:

```bash
cd /Users/raminhoodeh/Desktop/qadam
mkdir -p data/runtime
touch data/runtime/qadam-secrets.env
chmod 600 data/runtime/qadam-secrets.env
```

Then add values manually in this shape:

```bash
PROVIDER_KEY_NAME=real_value_here
```

After adding any key, run:

```bash
./start_qadam.sh
```

The cockpit and source heartbeat should show only `configured`, `missing`, `deferred`, or `blocked`. They must never show the raw key.

## 2. Acquisition Strategy

Use four passes:

1. Free/public critical keys.
2. Low-cost paper-trading and prediction-market keys.
3. Paid edge sources only if needed.
4. Later specialist and execution keys.

Do not buy all providers upfront. The first useful version of Qadam should work with free/public data, Alpaca paper, Kalshi/Polymarket public market data, NASA FIRMS, FRED, BLS, SEC EDGAR, RSS, GDELT, Oref, and the local LLM.

## 2A. Current Local Credential State

As of 2026-05-18, the local MacBook secret file has configured values for these providers, with no values committed or documented:

- NASA FIRMS.
- Alpaca paper.
- ACLED email/password, access token, and refresh token.
- FRED.
- Q-CTRL.
- Telegram bot token and bot username.
- Gemini/Google model keys and local LM Studio settings.

Still pending:

- Kalshi is not available in the current UK/UAE account/location context, so keep it deferred.
- Telegram now has local private and group delivery targets configured; it remains dry-run and send-disabled until explicit send testing is approved.
- ACLED token refresh automation now exists in `scripts/refresh_acled_token.py`. A 2026-05-19 refresh run succeeded with the refresh-token grant, but the ACLED read endpoint still returned HTTP 403, so ACLED still needs provider entitlement/account-scope confirmation before it counts as durable live.
- BLS, Reddit, Kalshi, Capitol Trades/STOCK Act, SEC user agent, IBM Quantum, and AWS Braket remain future or optional credentials. AIS, Aviationstack, UN Comtrade, and X now have local credential placeholders when supplied. UnusualWhales is intentionally disabled unless re-selected.

## 3. Batch A - Get These First

These are the highest-value keys for Phase 1 and the first paper proof.

| Order | Provider | Cost posture | Variables | What to do | Verification |
| --- | --- | --- | --- | --- | --- |
| 1 | NASA FIRMS | Free | `NASA_FIRMS_API_KEY` | Request a FIRMS MAP_KEY from NASA. | `./scripts/check_nasa_firms_adapter.py --live` |
| 2 | Alpaca Paper | Free to start | `ALPACA_API_KEY`, `ALPACA_API_SECRET`, `ALPACA_PAPER=true` | Create an Alpaca account, open Paper Trading, generate paper API keys. Use paper keys only. | `./scripts/check_phase1_live_source_hardening.py --live` |
| 3 | Kalshi | Usually free key; trading fees later | `KALSHI_API_KEY`, `KALSHI_API_SECRET` | Create a Kalshi account, generate API credentials, keep read-only/paper posture until execution policy exists. Current setup remains region/account gated. | `./scripts/check_phase1_live_source_hardening.py --live` |
| 4 | ACLED | Access/account dependent | `ACLED_ACCESS_TOKEN`, `ACLED_REFRESH_TOKEN`, or `ACLED_EMAIL`, `ACLED_PASSWORD` | Create/sign into ACLED, request API access/token. Use `./scripts/refresh_acled_token.py --write --validate-read` to refresh local ignored tokens before live source checks. Current endpoint is `https://acleddata.com/api/acled/read`. | `./scripts/refresh_acled_token.py --write --validate-read && ./scripts/check_phase1_live_source_hardening.py --live` |
| 5 | FRED | Free | `FRED_API_KEY` | Create a FRED API key. Qadam has CSV fallback, but a key improves reliability. | `./scripts/check_fred_adapter.py --live` |
| 6 | Telegram Bot | Free | `TELEGRAM_BOT_TOKEN`, `TELEGRAM_BOT_USERNAME`, `TELEGRAM_DEFAULT_CHAT_ID`, `TELEGRAM_GROUP_CHAT_ID` | Create a bot with BotFather. Keep `QADAM_TELEGRAM_DRY_RUN=true` first. | `./scripts/check_telegram_config.py && ./scripts/check_telegram_outbox.py` |

Minimum useful outcome after Batch A:

- Physical anomaly data works.
- Paper account can be read.
- Prediction-market metadata can be read.
- Macro data can be read.
- Telegram can be dry-run without sending.
- All credentials remain local.

Current Batch A note: NASA FIRMS, Alpaca paper, ACLED, FRED, and Telegram bot private/group delivery targets are locally configured. Kalshi remains unavailable in Ramin's current regions. The selected remaining data-source credential gaps are Reddit, Kalshi, and Capitol Trades/STOCK Act; UnusualWhales is no longer a Batch A credential gap.

## 4. Batch B - Add Confirmation Feeds

These improve signal quality but should not block the first proof.

| Order | Provider | Cost posture | Variables | What to do | Verification |
| --- | --- | --- | --- | --- | --- |
| 7 | BLS | Free with key / public limits | `BLS_API_KEY` | Register for a BLS API key. | `./scripts/check_phase1_live_source_hardening.py --live` |
| 8 | SEC EDGAR | Free, no secret | `SEC_USER_AGENT` | Set a real user-agent string with contact email. Do not leave the placeholder. | `./scripts/check_phase1_live_source_hardening.py --live` |
| 9 | UN Comtrade | Free/plan dependent | `COMTRADE_API_KEY` | Create a UN Comtrade account/API subscription key. | `./scripts/check_phase1_live_source_hardening.py --live` |
| 10 | Reddit | Usually free at low scale; terms-sensitive | `REDDIT_CLIENT_ID`, `REDDIT_CLIENT_SECRET` | Create a Reddit developer app for read-only monitoring. Keep usage low and compliant. | `./scripts/check_phase1_live_source_hardening.py --live` |
| 11 | X API | Paid/credit-based | `X_BEARER_TOKEN` | Only buy if RSS/GDELT/Reddit cannot cover the narrative edge. Start with the lowest useful tier. | `./scripts/check_phase1_live_source_hardening.py --live` |

Minimum useful outcome after Batch B:

- Macro official sources are live.
- Filing data is live.
- Narrative sources have at least one compliant API path.
- X is treated as optional, not mandatory.

## 5. Batch C - Paid Edge Sources

Only buy these after Qadam shows that a source category genuinely improves trade candidates.

| Provider | Cost posture | Variables | Decision rule |
| --- | --- | --- | --- |
| UnusualWhales | Paid | intentionally disabled | Re-select only if options flow becomes central to the strategy; do not buy as part of the current cleanup. |
| AISStream / Spire / MarineTraffic | Free/cheap to expensive depending provider | `AISSTREAM_API_KEY`, `SPIRE_API_KEY`, `MARINETRAFFIC_API_KEY` | Start with AISStream if available. Upgrade to Spire/MarineTraffic only if vessel data becomes core to oil/logistics signals. |
| Aviationstack | Free/freemium to paid depending usage | `AVIATIONSTACK_API_KEY` | Use as the v1 flight-data source instead of Wingbits. Keep it read-only and quota-aware. |
| Capitol Trades / STOCK Act provider | Provider/account dependent | `CAPITOL_TRADES_API_KEY` | Use for congressional trade disclosures instead of routing STOCK Act through UnusualWhales. |
| Coinglass | Paid/freemium | not selected | Decide crypto/perps relevance and build an adapter before requesting a key. |
| RapidAPI | Per-source paid | intentionally disabled | Use only when a specific direct provider is unavailable and chosen. |

Minimum useful outcome after Batch C:

- At least two physical/logistics sources pass live latency and trust checks.
- Paid feeds have evidence of improving Qadam's signal quality.
- Monthly data spend remains controlled.

## 6. Batch D - Specialist And Later Execution

These are not required for Phase 1 Data Spine.

| Provider | Variables | Timing |
| --- | --- | --- |
| Space-Track | `SPACE_TRACK_USERNAME`, `SPACE_TRACK_PASSWORD` | Later physical/satellite context. |
| GitHub | not selected | Decide the semiconductor/software signal role and build a read-only adapter before requesting `GITHUB_TOKEN`. |
| EPO OPS | `EPO_OPS_CONSUMER_KEY`, `EPO_OPS_CONSUMER_SECRET` | Later patent signal work. |
| ArcGIS | `ARCGIS_API_TOKEN` | Later non-public geospatial layers. |
| IBM Quantum | `IBM_QUANTUM_TOKEN` | Phase 3 quantum backend. |
| AWS Braket | `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, `AWS_REGION` | Phase 3 secondary quantum backend. |
| Polymarket execution | `POLYMARKET_PRIVATE_KEY`, `POLYMARKET_FUNDER_ADDRESS`, `POLYMARKET_CHAIN_ID` | Later guarded execution only. Not needed for public market data. |
| Hyperliquid | `HYPERLIQUID_PRIVATE_KEY`, `HYPERLIQUID_WALLET_ADDRESS` | Deferred. Disabled by default. |
| IBKR | `IBKR_HOST`, `IBKR_PORT`, `IBKR_CLIENT_ID`, `IBKR_PAPER=true` | Deferred broker alternative. |

## 7. Provider Links

Use official pages where possible:

- NASA FIRMS API: `https://firms.modaps.eosdis.nasa.gov/api/area/`
- Alpaca paper trading: `https://docs.alpaca.markets/docs/trading/paper-trading/`
- Alpaca authentication: `https://docs.alpaca.markets/reference/authentication-2`
- Kalshi API keys: `https://docs.kalshi.com/getting_started/api_keys`
- ACLED API documentation: `https://acleddata.com/api-documentation/getting-started`
- FRED API keys: `https://fred.stlouisfed.org/docs/api/api_key.html`
- BLS API FAQ: `https://www.bls.gov/developers/api_FAQs.htm`
- SEC EDGAR access rules: `https://www.sec.gov/search-filings/edgar-search-assistance/accessing-edgar-data`
- Telegram Bot API: `https://core.telegram.org/bots/api`
- X API pricing: `https://docs.x.com/x-api/getting-started/pricing`
- UnusualWhales API: `https://unusualwhales.com/public-api`

## 8. Validation Checklist

After each provider:

1. Add the key locally.
2. Run the provider-specific check.
3. Run `./scripts/check_phase1_data_spine.py`.
4. Run `./start_qadam.sh`.
5. Confirm the dashboard shows configured/degraded status without secrets.
6. Only then decide whether to keep, upgrade, or cancel the provider.

## 9. Success Criteria

The acquisition phase is complete when:

- Batch A is configured and checked.
- At least one macro source, one conflict source, one prediction-market source, one paper-account source, and one physical/logistics source are live.
- At least two physical/logistics sources pass live trust/latency checks.
- At least 20 sources have Trust Score above 0.5 using real observations, not only priors.
- Postgres/Timescale durable ingestion is running through `scripts/start_postgres_timescale_ingestion.sh`, and replay coverage passes with `scripts/check_postgres_timescale_replay.py --require-full-source-coverage`.
- No key has been committed, pasted, or exposed.
