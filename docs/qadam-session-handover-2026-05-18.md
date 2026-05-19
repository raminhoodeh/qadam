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
- `missing_credential_source_count=11`
- `deferred_count=3`
- `trust_score_above_half_count=22`
- `physical_logistics_latency_pass_count=3`
- `historical_backfill_plan_count=12`
- `historical_backfill_run_recorded_count=8`
- `historical_backfill_run_blocked_count=4`
- `paper_account_current_balance_gbp=1000.0`
- `live_capital_enabled=False`
- `postgres_timescale_status=offline`

Local credential status as of 2026-05-18:

- Stored locally in `data/runtime/qadam-secrets.env` with strict local permissions: NASA FIRMS, Alpaca paper, ACLED email/password/access token/refresh token, FRED, Q-CTRL, Telegram bot token/username, Gemini/Google model keys, and local LM Studio settings.
- Still missing or not usable locally: Kalshi credentials, UnusualWhales, BLS, UN Comtrade, Reddit, X, AIS/Wingbits/logistics providers, SEC user agent, IBM Quantum, and AWS Braket.
- Telegram has private and group delivery targets locally configured, but remains dry-run and disabled for normal sends until explicit send approval exists.
- Phase 1 live source hardening now exists as `scripts/check_phase1_live_source_hardening.py`. It writes the ignored local report `data/runtime/phase1_live_source_validation.json` and keeps each promoted source explicitly marked as `live`, `degraded`, `missing_credentials`, or `sample_ready`.
- Current live read-only validation: NASA FIRMS, FRED, RSS, Polymarket, Alpaca, BLS, ECB, SEC EDGAR, and Telegram are live; GDELT, Oref, and ACLED are degraded; UnusualWhales, Kalshi, AIS Maritime, Wingbits, UN Comtrade, Reddit, and X/Twitter remain missing or deferred.
- Supplied credential validation now exists as `scripts/check_supplied_credentials.py`. Current 2026-05-19 result: NASA FIRMS, FRED, Alpaca paper, Telegram, Gemini, and LM Studio are live; ACLED is configured but degraded with provider HTTP 403; Kalshi remains deferred; UnusualWhales remains the useful missing Batch A key.
- ACLED token refresh automation now exists as `scripts/refresh_acled_token.py --write --validate-read`. It writes only to the ignored local secret file and ignored local refresh reports. A 2026-05-19 run successfully refreshed token material with the refresh-token grant, but the post-refresh read validation still returned HTTP 403, so ACLED needs provider entitlement/account-scope confirmation before it counts as durable live infrastructure.
- Alpaca paper-account mirroring now exists as `scripts/check_alpaca_paper_mirror.py --live`. It calls only GET endpoints for account, positions, orders, and portfolio history, writes sanitized local mirror state, and keeps broker writes, live capital, and paper-order authority disabled.
- Phase 2 shadow cycle now exists as `scripts/run_phase2_shadow_cycle.py --live-sources --live-local-llm`. A 2026-05-19 live run fed FRED, RSS, Polymarket, Alpaca, and Telegram observations into the Research Analyst queue, ran local Gemma in shadow mode, reviewed shadow signals through the first Signal Integrity Gate, and queued a Strategy Lead shadow handoff. It does not create signals with execution authority, risk approvals, trade candidates, paper orders, or broker actions.
- Signal Integrity Gate now exists as `orchestrator/signal_integrity.py`, with `scripts/check_signal_integrity_gate.py` as its contract check. It can block, hold for corroboration, or mark a signal ready for future risk-shadow review, but it cannot approve risk or create orders.
- Kalshi is blocked by current location/account availability and should remain deferred until eligibility is resolved.

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

- Start Postgres/Timescale locally.
- Dedicated bootstrap now exists at `scripts/start_postgres_timescale_ingestion.sh`, but the current Mac session has no Docker-compatible CLI available, so it exits with `postgres_timescale_runtime_status=missing`.
- Run true live adapter checks source by source for the newly configured local keys.
- Add remaining provider credentials only when each source is needed.
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
./scripts/start_postgres_timescale_ingestion.sh
./scripts/check_postgres_timescale_ingestion.py --require-live
./scripts/check_postgres_timescale_replay.py --require-full-source-coverage
```

2. Validate the locally configured Batch A keys without exposing values:

```bash
./start_qadam.sh
```

3. Run source-specific checks only after approving live provider calls:

```bash
./scripts/check_nasa_firms_adapter.py --live
./scripts/check_fred_adapter.py --live
./scripts/check_phase1_live_source_hardening.py --live
```

4. Keep Kalshi deferred until credentials and location eligibility are available:

```bash
./scripts/check_phase1_live_source_hardening.py --live
```

5. Keep Telegram in `QADAM_TELEGRAM_ENABLED=false` and `QADAM_TELEGRAM_DRY_RUN=true` until explicit send testing is approved.

6. Refresh and deploy the cockpit only after checks pass:

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
