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
ACLED_REFRESH_TOKEN=
UNUSUAL_WHALES_API_KEY=
FRED_API_KEY=
QCTRL_API_KEY=
QCTRL_ORGANIZATION_SLUG=
IBM_QUANTUM_TOKEN=
IBM_QUANTUM_INSTANCE=
AWS_ACCESS_KEY_ID=
AWS_SECRET_ACCESS_KEY=
AWS_REGION=
TELEGRAM_BOT_TOKEN=
TELEGRAM_BOT_USERNAME=
TELEGRAM_DEFAULT_CHAT_ID=
TELEGRAM_GROUP_CHAT_ID=
QADAM_TELEGRAM_ENABLED=false
QADAM_TELEGRAM_DRY_RUN=true
QADAM_TELEGRAM_TRADE_GROUP_NOTIFICATIONS_ENABLED=false
QADAM_TELEGRAM_TRADE_GROUP_NOTIFICATIONS_DRY_RUN=true
```

The larger placeholder ledger is in `docs/api-specs.md`. Do not copy unused keys into runtime storage unless you are actively configuring that provider.

If a key is ever pasted into a chat, committed, or shown publicly, rotate it at the provider before using it for production or live trading.

## First Keys To Get

| Priority | Provider | Qadam variable | Why it matters | How to get it |
| --- | --- | --- | --- | --- |
| 1 | NASA FIRMS | `NASA_FIRMS_API_KEY` | Enables Phase 1D physical anomaly monitoring for ports, oil corridors, and chokepoints. | Request a free FIRMS MAP_KEY from the official FIRMS API page. |
| 2 | Alpaca Paper | `ALPACA_API_KEY`, `ALPACA_API_SECRET`, `ALPACA_PAPER=true` | Required for the £100,000 paper-account proof rail once the execution adapter is built. | Create/sign in to Alpaca, open Paper Trading, generate paper API keys, and use the paper endpoint. |
| 3 | Kalshi | `KALSHI_API_KEY`, `KALSHI_API_SECRET` | Required for prediction-market monitoring and later guarded execution. | Create an API key from Kalshi account settings when the account and region are eligible. Store the private key immediately because it cannot be retrieved later. |
| 4 | ACLED | `ACLED_EMAIL`, `ACLED_PASSWORD`, `ACLED_ACCESS_TOKEN`, `ACLED_REFRESH_TOKEN` | High-value conflict and geopolitical event source. | Create a myACLED account, then request API auth and refresh tokens for `https://acleddata.com/api/acled/read`. Prefer token refresh automation over repeated password use. |
| 5 | Unusual Whales | `UNUSUAL_WHALES_API_KEY` | Options flow, dark pool, congressional trading, and volatility context. | Subscribe/request API access, then create/copy the API token from the API dashboard. |
| 6 | FRED | `FRED_API_KEY` | Better official macro API access. | Log into a FRED account and request a distinct API key for Qadam. Qadam can still use public CSV fallback without it. |

## TradingView

Your paid TradingView account is useful, but it does not provide a normal retail API key for direct Qadam market-data pulls.

Use TradingView in two separate ways:

| Use | Status | Qadam treatment |
| --- | --- | --- |
| TradingView MCP | Now | Read-only supplemental technical-analysis adapter. It observes and analyses; Qadam governs; Alpaca Paper executes. No TradingView login or API key expected. |
| TradingView paid-account alerts | Local D7 contract now; public webhook later | Qadam can store and display observed alert fixtures with duplicate protection and no execution path. A real TradingView webhook URL waits for the secure bridge. |

Setup command for the MCP tool after installing `uv`:

```bash
codex mcp add tradingview -- uvx --from tradingview-mcp-server tradingview-mcp
```

Qadam also checks the local `tradingview-mcp-main/` checkout directly:

```bash
.venv/bin/python scripts/check_tradingview_mcp_adapter.py
```

The adapter must remain read-only. It can produce technical context and evidence packets, but it cannot create trade candidates, submit Alpaca orders, or bypass Qadam risk/quantum gates.

## Telegram Bot

Telegram is Qadam's founding-member communications rail. It is not a trading interface.

Required later for Phase D8A/T1:

| Variable | Purpose |
| --- | --- |
| `TELEGRAM_BOT_TOKEN` | BotFather token for the Qadam Telegram bot. Store locally only. |
| `TELEGRAM_BOT_USERNAME` | Human-readable bot username for diagnostics. |
| `TELEGRAM_DEFAULT_CHAT_ID` | Optional private DM target for first test delivery. |
| `TELEGRAM_GROUP_CHAT_ID` | Optional private group target for founding-member delivery tests. |
| `QADAM_TELEGRAM_ENABLED=false` | Global send gate. Defaults disabled. |
| `QADAM_TELEGRAM_DRY_RUN=true` | Writes outbox messages without sending. Defaults dry-run. |
| `QADAM_TELEGRAM_TRADE_GROUP_NOTIFICATIONS_ENABLED=false` | Dedicated gate for outbound group alerts when Qadam has already submitted a paper order. |
| `QADAM_TELEGRAM_TRADE_GROUP_NOTIFICATIONS_DRY_RUN=true` | Keeps paper-trade group alerts in validation mode until explicitly flipped false. |

Setup path:

1. Create the bot in Telegram through BotFather.
2. Store the token only in `data/runtime/qadam-secrets.env`.
3. Send one message to the bot, then capture `TELEGRAM_DEFAULT_CHAT_ID` locally.
4. Add the bot to the intended private test group, then capture `TELEGRAM_GROUP_CHAT_ID` locally.
5. Keep the general member outbox at `QADAM_TELEGRAM_ENABLED=false` and `QADAM_TELEGRAM_DRY_RUN=true`; it has no command authority.
6. For submitted-paper-order group alerts, set `QADAM_TELEGRAM_TRADE_GROUP_NOTIFICATIONS_ENABLED=true` and `QADAM_TELEGRAM_TRADE_GROUP_NOTIFICATIONS_DRY_RUN=false` only after the group chat target exists.
7. Verify the dashboard shows Telegram as dry-run for the general outbox and live-ready for paper-trade group notifications.
8. Send one explicit private test message only after the local checks pass.
9. To let active PaperOps send group alerts after submitted paper orders, set `QADAM_TELEGRAM_TRADE_GROUP_NOTIFICATIONS_ENABLED=true` and `QADAM_TELEGRAM_TRADE_GROUP_NOTIFICATIONS_DRY_RUN=false`. Those alerts include the submitted trade, current paper portfolio value, total paper P&L, and signed performance percentage.

Never commit the bot token or chat IDs. If either appears in chat, Git, screenshots, or public dashboard output, rotate the token and replace the chat registry before using Telegram for real delivery.

## Quantum Keys

Qadam does not need quantum hardware to complete Phase 1D. Keep these as readiness credentials until the quantum provider registry is promoted:

| Provider | Qadam variable | Notes |
| --- | --- | --- |
| Q-CTRL Fire Opal | `QCTRL_API_KEY`, `QCTRL_ORGANIZATION_SLUG` when required | Mandatory paper-reality quantum parity provider for paper-live operation. Qadam defaults the organization slug to `qadam` when no secret override is present. |
| IBM Quantum | `IBM_QUANTUM_TOKEN`, `IBM_QUANTUM_INSTANCE` | Primary future quantum backend through Fire Opal on IBM Quantum / Qiskit Runtime. Device discovery is explicit and hardware submission remains separately blocked. |
| AWS Braket | `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, `AWS_REGION` | Secondary future backend; use a restricted IAM user/role when enabled. |

## Current Phase 1D State

NASA FIRMS is now the first physical pipeline adapter promoted into Qadam. Without `NASA_FIRMS_API_KEY`, the adapter is healthy in sample mode and marked `unavailable_missing_credentials` for live mode. With the key configured, `scripts/check_nasa_firms_adapter.py --live` can make a read-only FIRMS area CSV request and archive the sanitized result locally.

As of 2026-05-18, NASA FIRMS, Alpaca paper, ACLED, FRED, Q-CTRL, Telegram bot token/username/private target/group target, Gemini/Google model keys, and LM Studio settings are configured in the local ignored secret file. Kalshi remains region-unavailable.

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
