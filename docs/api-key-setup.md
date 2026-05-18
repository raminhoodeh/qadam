# Qadam API Key Setup

Qadam is a public repository and a local-first system. Real API keys belong only in local runtime storage, never in Git, screenshots, docs, or chat.

For the full provider inventory, including all 35 World Monitor data sources, optional `world-monitor/` reference providers, model keys, quantum keys, broker rails, TradingView alert placeholders, and unresolved provider choices, use `docs/api-specs.md`.

For the step-by-step acquisition order, cost posture, provider links, and validation command for each key, use `docs/qadam-api-key-acquisition-plan.md`.

## Local Secret File

Create one local secret file:

```bash
mkdir -p data/runtime
touch data/runtime/qadam-secrets.env
chmod 600 data/runtime/qadam-secrets.env
```

Add only the keys you actually have:

```bash
NASA_FIRMS_API_KEY=
ALPACA_API_KEY=
ALPACA_API_SECRET=
ALPACA_PAPER=true
KALSHI_API_KEY=
KALSHI_API_SECRET=
ACLED_EMAIL=
ACLED_PASSWORD=
ACLED_ACCESS_TOKEN=
UNUSUAL_WHALES_API_KEY=
FRED_API_KEY=
QCTRL_API_KEY=
IBM_QUANTUM_TOKEN=
AWS_ACCESS_KEY_ID=
AWS_SECRET_ACCESS_KEY=
AWS_REGION=
TELEGRAM_BOT_TOKEN=
TELEGRAM_BOT_USERNAME=
TELEGRAM_DEFAULT_CHAT_ID=
QADAM_TELEGRAM_ENABLED=false
QADAM_TELEGRAM_DRY_RUN=true
```

The larger placeholder ledger is in `docs/api-specs.md`. Do not copy unused keys into runtime storage unless you are actively configuring that provider.

If a key is ever pasted into a chat, committed, or shown publicly, rotate it at the provider before using it for production or live trading.

## First Keys To Get

| Priority | Provider | Qadam variable | Why it matters | How to get it |
| --- | --- | --- | --- | --- |
| 1 | NASA FIRMS | `NASA_FIRMS_API_KEY` | Enables Phase 1D physical anomaly monitoring for ports, oil corridors, and chokepoints. | Request a free FIRMS MAP_KEY from the official FIRMS API page. |
| 2 | Alpaca Paper | `ALPACA_API_KEY`, `ALPACA_API_SECRET`, `ALPACA_PAPER=true` | Required for the £1000 paper-account proof rail once the execution adapter is built. | Create/sign in to Alpaca, open Paper Trading, generate paper API keys, and use the paper endpoint. |
| 3 | Kalshi | `KALSHI_API_KEY`, `KALSHI_API_SECRET` | Required for prediction-market monitoring and later guarded execution. | Create an API key from Kalshi account settings. Store the private key immediately because it cannot be retrieved later. |
| 4 | ACLED | `ACLED_EMAIL`, `ACLED_PASSWORD`, later `ACLED_ACCESS_TOKEN` | High-value conflict and geopolitical event source. | Create a myACLED account, then request an API auth token with your credentials. |
| 5 | Unusual Whales | `UNUSUAL_WHALES_API_KEY` | Options flow, dark pool, congressional trading, and volatility context. | Subscribe/request API access, then create/copy the API token from the API dashboard. |
| 6 | FRED | `FRED_API_KEY` | Better official macro API access. | Log into a FRED account and request a distinct API key for Qadam. Qadam can still use public CSV fallback without it. |

## TradingView

Your paid TradingView account is useful, but it does not provide a normal retail API key for direct Qadam market-data pulls.

Use TradingView in two separate ways:

| Use | Status | Qadam treatment |
| --- | --- | --- |
| TradingView MCP | Now | Read-only market and technical-analysis tooling through Codex/MCP. No TradingView login or API key expected. |
| TradingView paid-account alerts | Local D7 contract now; public webhook later | Qadam can store and display observed alert fixtures with duplicate protection and no execution path. A real TradingView webhook URL waits for the secure bridge. |

Setup command for the MCP tool after installing `uv`:

```bash
codex mcp add tradingview -- uvx --from tradingview-mcp-server tradingview-mcp
```

## Telegram Bot

Telegram is Qadam's founding-member communications rail. It is not a trading interface.

Required later for Phase D8A/T1:

| Variable | Purpose |
| --- | --- |
| `TELEGRAM_BOT_TOKEN` | BotFather token for the Qadam Telegram bot. Store locally only. |
| `TELEGRAM_BOT_USERNAME` | Human-readable bot username for diagnostics. |
| `TELEGRAM_DEFAULT_CHAT_ID` | Optional private group/chat target for first test delivery. |
| `QADAM_TELEGRAM_ENABLED=false` | Global send gate. Defaults disabled. |
| `QADAM_TELEGRAM_DRY_RUN=true` | Writes outbox messages without sending. Defaults dry-run. |

Setup path:

1. Create the bot in Telegram through BotFather.
2. Store the token only in `data/runtime/qadam-secrets.env`.
3. Start with `QADAM_TELEGRAM_ENABLED=false` and `QADAM_TELEGRAM_DRY_RUN=true`.
4. Verify the dashboard shows Telegram as disabled/dry-run.
5. Send one explicit private test message only after the local checks pass.

Never commit the bot token or chat IDs. If either appears in chat, Git, screenshots, or public dashboard output, rotate the token and replace the chat registry before using Telegram for real delivery.

## Quantum Keys

Qadam does not need quantum hardware to complete Phase 1D. Keep these as readiness credentials until the quantum provider registry is promoted:

| Provider | Qadam variable | Notes |
| --- | --- | --- |
| Q-CTRL Fire Opal | `QCTRL_API_KEY` | Error-suppression layer; authenticate through Fire Opal when the quantum module is active. |
| IBM Quantum | `IBM_QUANTUM_TOKEN` | Primary future quantum backend through Qiskit Runtime. |
| AWS Braket | `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, `AWS_REGION` | Secondary future backend; use a restricted IAM user/role when enabled. |

## Current Phase 1D State

NASA FIRMS is now the first physical pipeline adapter promoted into Qadam. Without `NASA_FIRMS_API_KEY`, the adapter is healthy in sample mode and marked `unavailable_missing_credentials` for live mode. With the key configured, `scripts/check_nasa_firms_adapter.py --live` can make a read-only FIRMS area CSV request and archive the sanitized result locally.

Official references:

- NASA FIRMS API: https://firms.modaps.eosdis.nasa.gov/api/area/csv
- Alpaca paper trading: https://docs.alpaca.markets/docs/trading/paper-trading/
- Alpaca authentication: https://docs.alpaca.markets/reference/authentication-2
- Kalshi API keys: https://docs.kalshi.com/getting_started/api_keys
- ACLED API getting started: https://acleddata.com/api-documentation/getting-started
- Unusual Whales API docs: https://api.unusualwhales.com/docs
- FRED API keys: https://fred.stlouisfed.org/docs/api/fred/v2/api_key.html
- Q-CTRL Fire Opal setup: https://docs.q-ctrl.com/fire-opal/discover/start-using/how-to-set-up-and-install-fire-opal
- IBM Quantum account setup: https://quantum.cloud.ibm.com/docs/guides/initialize-account
- AWS Braket getting started: https://aws.amazon.com/braket/getting-started/
