# Qadam API Key Setup

Qadam is a public repository and a local-first system. Real API keys belong only in local runtime storage, never in Git, screenshots, docs, or chat.

For the full provider inventory, including all 35 World Monitor data sources, optional `world-monitor/` reference providers, model keys, quantum keys, broker rails, TradingView alert placeholders, and the current provider decisions, use `docs/api-specs.md`.

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
KALSHI_API_BASE_URL=https://trading-api.kalshi.com
AISSTREAM_API_KEY=
AVIATIONSTACK_API_KEY=
COMTRADE_API_KEY=
COMTRADE_V1_PRIMARY_KEY=
COMTRADE_V1_SECONDARY_KEY=
COMTRADE_TOOLS_V1_PRIMARY_KEY=
COMTRADE_TOOLS_V1_SECONDARY_KEY=
COMTRADE_PUBLIC_V1_PRIMARY_KEY=
COMTRADE_PUBLIC_V1_SECONDARY_KEY=
X_BEARER_TOKEN=
REDDIT_CLIENT_ID=
REDDIT_CLIENT_SECRET=
REDDIT_USER_AGENT=Qadam/0.1 by u/<reddit_username>
CAPITOL_TRADES_API_KEY=
CAPITOL_TRADES_API_URL=
ACLED_EMAIL=
ACLED_PASSWORD=
ACLED_ACCESS_TOKEN=
ACLED_REFRESH_TOKEN=
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

## Credential-Bound Adapter Pass

As of 2026-06-14, Reddit, Kalshi, and Capitol Trades/STOCK Act have explicit credential-bound read-only adapter contracts. They are not counted as connected until their required credentials are present locally and, for Capitol Trades, a provider-confirmed API endpoint is supplied.

| Source | Adapter state without credentials | Required local values | Activation behavior |
| --- | --- | --- | --- |
| Reddit | `missing_credentials` | `REDDIT_CLIENT_ID`, `REDDIT_CLIENT_SECRET`; optional `REDDIT_USER_AGENT` | Exchanges client credentials for a read-only OAuth bearer token and reads Reddit context only. |
| Kalshi | `missing_credentials` | `KALSHI_API_KEY`, `KALSHI_API_SECRET`; optional `KALSHI_API_BASE_URL` | Builds RSA-signed read-only request headers for Kalshi market metadata. |
| Capitol Trades / STOCK Act | `missing_credentials`, or `provider_endpoint_unconfirmed` if only the key is present | `CAPITOL_TRADES_API_KEY` and provider-confirmed `CAPITOL_TRADES_API_URL` | Reads congressional trading disclosures only after the provider endpoint contract is known. |

Validate the credential-bound contract without using real secrets:

```bash
.venv/bin/python scripts/check_credential_bound_adapters.py
```

The check must show these adapters as read-only. They cannot approve signals, create trade candidates, submit Alpaca paper orders, call broker write endpoints, or enable live capital.

## Provider Decisions That Do Not Need Keys Yet

As of 2026-06-14, Qadam has resolved the remaining provider-choice/local-only sources as metadata, not as connected sources. Do not add these keys to `data/runtime/qadam-secrets.env` unless their read-only adapter or local bridge is explicitly promoted later.

| Source | Current decision | What you do now |
| --- | --- | --- |
| RapidAPI | Disabled because RapidAPI is a marketplace, not a canonical source. | Nothing. Do not add `RAPIDAPI_KEY` unless a specific RapidAPI-backed provider is selected. |
| Coinglass | CoinGlass API selected for optional future crypto/perps context; adapter not built. | Nothing. Do not add `COINGLASS_API_KEY` yet. |
| Chainlink | Chainlink Data Feeds selected for optional future price-integrity checks; public adapter not built. | Nothing. Do not add `ETH_RPC_URL` yet. |
| GitHub | GitHub REST API selected for optional future technology/supply-chain context; public adapter not built. | Nothing. Do not add `GITHUB_TOKEN` until Qadam has a narrow watchlist and adapter. |
| Bookmap | Local Bookmap bridge selected for optional future order-flow confirmation. | Nothing unless you want to run Bookmap locally; if promoted later, use `BOOKMAP_BRIDGE_URL` and keep the bridge read-only. |

Validate this provider-decision contract:

```bash
.venv/bin/python scripts/check_provider_decision_pass.py
```

This check must show zero credentials required now and zero order, broker-write, or live-capital authority.

## First Keys To Get

| Priority | Provider | Qadam variable | Why it matters | How to get it |
| --- | --- | --- | --- | --- |
| 1 | NASA FIRMS | `NASA_FIRMS_API_KEY` | Enables Phase 1D physical anomaly monitoring for ports, oil corridors, and chokepoints. | Request a free FIRMS MAP_KEY from the official FIRMS API page. |
| 2 | Alpaca Paper | `ALPACA_API_KEY`, `ALPACA_API_SECRET`, `ALPACA_PAPER=true` | Required for the £100,000 paper-account proof rail once the execution adapter is built. | Create/sign in to Alpaca, open Paper Trading, generate paper API keys, and use the paper endpoint. |
| 3 | Kalshi | `KALSHI_API_KEY`, `KALSHI_API_SECRET`, optional `KALSHI_API_BASE_URL` | Required for prediction-market monitoring and later guarded execution. | Create an API key from Kalshi account settings when the account and region are eligible. Store the private key immediately because it cannot be retrieved later. |
| 4 | ACLED | `ACLED_EMAIL`, `ACLED_PASSWORD`, `ACLED_ACCESS_TOKEN`, `ACLED_REFRESH_TOKEN` | High-value conflict and geopolitical event source. | Create a myACLED account, then request API auth and refresh tokens for `https://acleddata.com/api/acled/read`. Prefer token refresh automation over repeated password use. |
| 5 | Capitol Trades / STOCK Act provider | `CAPITOL_TRADES_API_KEY`, `CAPITOL_TRADES_API_URL` | Congressional trading context for the STOCK Act source. | Use the provider/API path selected for Qadam and store the key plus the provider-confirmed endpoint locally. |
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

### Evidence Packet Normalization

All new source adapters should emit `EvidenceItem` records and let
`orchestrator/evidence_packet_normalization.py` build public-safe packets.
Do not expose raw provider references, local paths, secrets, broker identifiers,
or execution hints in dashboard packets. The normalized packet must keep source
quorum, trade-candidate creation, risk handoff, paper orders, broker writes,
quantum jobs, performance credit, and live capital set to `false`.

After normalization, Qadam persists the public-safe packet surface through
`orchestrator/evidence_packet_runtime.py`. The runtime writes a latest snapshot,
append-only JSONL history, and local event-log audit trail under
`data/runtime/`. This is replay-only storage: it lets Qadam prove what evidence
was visible to the cockpit, but it cannot create a signal, source quorum, trade
idea, order, broker write, quantum job, proof credit, or live-capital state.

## Bookmap Local Bridge

Bookmap is not a hosted API-key source for Qadam. It is a local-only, read-only order-flow bridge that can provide supplemental microstructure context when Bookmap is running on the Mac.

Use it only in this shape:

| Variable | Purpose |
| --- | --- |
| `BOOKMAP_LOCAL_BRIDGE_ENABLED=true` | Allows Qadam to expose the Bookmap adapter contract. Defaults enabled. |
| `BOOKMAP_LOCAL_BRIDGE_LIVE_PROBE_ENABLED=false` | Keeps live local probing off until the bridge process is running. |
| `BOOKMAP_LOCAL_BRIDGE_TIMEOUT_SECONDS=3` | Short localhost probe timeout. |
| `BOOKMAP_BRIDGE_URL=http://127.0.0.1:8765/bookmap` | Local read-only HTTP JSON snapshot endpoint. `ws://127.0.0.1:8765/bookmap` is also supported when the Python `websockets` package is available. |

Expected bridge response shape:

```json
{
  "records": [
    {
      "symbol": "CL",
      "setup_type": "absorption_range_watch",
      "direction": "watch_breakout_or_reversal",
      "orderflow_score": 0.68,
      "liquidity_state": "resting_liquidity_near_range_edges",
      "absorption_state": "possible_absorption",
      "imbalance_state": "mixed"
    }
  ]
}
```

Validation:

```bash
.venv/bin/python scripts/check_bookmap_local_bridge.py
```

Boundary: Bookmap observes local orderflow only. It cannot inject orders, place trades in Bookmap, create Qadam trade candidates, submit Alpaca Paper orders, call brokers, satisfy source quorum by itself, run quantum jobs, or enable live capital.

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

As of 2026-06-14, the remaining selected credential-bound gaps are Reddit OAuth, Kalshi account credentials, and Capitol Trades/STOCK Act provider access. Their adapter contracts are implemented, but they remain disconnected until the local values above are supplied. Capitol Trades also requires a real API endpoint, not only the public website URL.

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
