# Qadam Session Handover - 2026-05-18

Use this document to resume Qadam in a new chat without replaying the whole prior conversation.

## Start Here

Primary plan:

- `docs/qadam-master-implementation-plan.md`

API key plan:

- `docs/qadam-api-key-acquisition-plan.md`

Provider inventory:

- `docs/api-specs.md`

Local secret setup:

- `docs/api-key-setup.md`

User guide / dashboard context:

- `docs/qadam-user-guide.md`
- `docs/qadam-dashboard-implementation-plan.md`

## Current State

Qadam is in first-release paper mode:

- Local-first MacBook runtime.
- GBP 1000 paper/test account mirror.
- No live capital.
- No broker-write path.
- Public cockpit at `qadam.trade` is a read-only status/dashboard shell.
- Canonical saved runtime data remains local under `data/`.

Implemented foundations:

- 35-source World Monitor registry across 5 pipelines.
- 19 promoted read-only adapter contracts.
- Dedicated adapters: GDELT, Oref, NASA FIRMS, FRED, RSS.
- Generic Phase 1 adapter contracts: ACLED, UnusualWhales, Polymarket, Kalshi, Alpaca, AIS Maritime, Wingbits, BLS, ECB, UN Comtrade, SEC EDGAR, Reddit, X, Telegram.
- Historical backfill planning and local sample-runner for 12 priority sources.
- Trust Score seed across all 35 sources.
- Phase 1 Agent OS with 8 named agents and explicit tool grants.
- Dashboard phases D0-D7+ shell: system map, watching view, cognition view, trade intent board, paper account mirror, TradingView observed-alert contract, Telegram dry-run comms, Fund Manager forum, user guide.

Important verified numbers from the last completed run:

- `source_count=35`
- `pipeline_count=5`
- `promoted_adapter_count=19`
- `missing_credential_source_count=14`
- `deferred_count=3`
- `trust_score_above_half_count=22`
- `physical_logistics_latency_pass_count=3`
- `historical_backfill_plan_count=12`
- `historical_backfill_run_recorded_count=6`
- `historical_backfill_run_blocked_count=6`
- `paper_account_current_balance_gbp=1000.0`
- `live_capital_enabled=False`
- `postgres_timescale_status=offline`

## Key Boundary

The system is not fully live yet.

What is real:

- Adapter contracts.
- Sample-mode normalization.
- Source heartbeat classification.
- Dashboard status export.
- Local JSONL runtime/event stores.
- Read-only public Polymarket smoke test passed previously.

What still needs work:

- Add missing provider credentials locally.
- Start Postgres/Timescale locally.
- Run true live adapter checks source by source.
- Run true historical backfills.
- Replace Trust Score priors with real observation/backtest scores.
- Promote paper broker read-only checks before any execution work.

## Secret Handling

Do not paste API keys into Git, docs, screenshots, or public dashboard output.

Preferred local storage:

```bash
cd /Users/raminhoodeh/Desktop/qadam
mkdir -p data/runtime
touch data/runtime/qadam-secrets.env
chmod 600 data/runtime/qadam-secrets.env
```

Then add provider values manually to:

```bash
data/runtime/qadam-secrets.env
```

If a key is ever exposed in chat or a screenshot, rotate it at the provider before treating it as production-safe.

## Next Implementation Step

1. Start local durable stores:

```bash
cd /Users/raminhoodeh/Desktop/qadam
./scripts/start_local_stores.sh
./scripts/check_postgres_timescale_ingestion.py --require-live
```

2. Add Batch A API keys from `docs/qadam-api-key-acquisition-plan.md`:

- `NASA_FIRMS_API_KEY`
- `ALPACA_API_KEY`
- `ALPACA_API_SECRET`
- `ALPACA_PAPER=true`
- `KALSHI_API_KEY`
- `KALSHI_API_SECRET`
- `ACLED_ACCESS_TOKEN` or `ACLED_EMAIL` plus `ACLED_PASSWORD`
- `FRED_API_KEY`
- `TELEGRAM_BOT_TOKEN`
- `TELEGRAM_BOT_USERNAME`
- `TELEGRAM_DEFAULT_CHAT_ID`

3. Validate after each key:

```bash
./start_qadam.sh
```

4. Run source-specific checks:

```bash
./scripts/check_nasa_firms_adapter.py --live
./scripts/check_phase1_live_adapters.py --live --source=alpaca
./scripts/check_phase1_live_adapters.py --live --source=kalshi
./scripts/check_phase1_live_adapters.py --live --source=acled
./scripts/check_fred_adapter.py --live
```

5. Refresh and deploy the cockpit only after checks pass:

```bash
cd /Users/raminhoodeh/Desktop/qadam/landing-page-repo
set -a
source ../data/runtime/vercel.env
set +a
./scripts/deploy-vercel-production.sh
```

## How To Resume In A New Chat

Give Codex this handover file and say:

```text
Continue Qadam from docs/qadam-session-handover-2026-05-18.md.
Use docs/qadam-master-implementation-plan.md as the master plan and docs/qadam-api-key-acquisition-plan.md for API onboarding.
Start with Postgres/Timescale live durable ingestion, then Batch A API keys, then live adapter checks.
Do not expose or commit secrets.
```

## Verification Commands

Core local checks:

```bash
./scripts/check_phase1_data_spine.py
./scripts/check_phase1_live_adapters.py
./scripts/check_historical_backfills.py
./scripts/check_trust_score_seed.py
./scripts/check_postgres_timescale_ingestion.py
./scripts/check_phase1_agent_os.py
./start_qadam.sh
```

Secret-pattern scan before committing:

```bash
rg -n "(ghp_|vcp_|AIza|sb_secret_|QCTRL_API_KEY=.+|NASA_FIRMS_API_KEY=.+|ALPACA_API_SECRET=.+|KALSHI_API_SECRET=.+|TELEGRAM_BOT_TOKEN=.+|X_BEARER_TOKEN=.+)" docs orchestrator scripts README.md .env.example
```

Expected result: no output.
