# Qadam Pre-Phase-3 Baseline Audit - 2026-05-22

This is the Stage P3-0 baseline audit for `docs/qadam-pre-phase-3-implementation-plan.md`.

## Audit Decision

Stage P3-0 is complete with blockers recorded.

The repo is ready to proceed to P3-1 Foundation Health, but P3-3 Durable Observation Spine is blocked until the current Python runtime can import `asyncpg`.

## Git State

Main repo status:

- Modified: `README.md`
- Modified: `docs/api-source-inventory.md`
- Modified: `docs/api-specs.md`
- Modified: `docs/qadam-master-implementation-plan.md`
- Untracked: `docs/qadam-pre-phase-3-implementation-plan.md`
- Untracked: `quant-skills/`
- Untracked: `yahoo-finance-api/`

Nested `landing-page-repo` status:

- Clean.

Staging area:

- No staged files.

Git worktree boundaries:

- Git repositories detected: main repo `.git`, nested `landing-page-repo/.git`.
- `yahoo-finance-api/` is not a separate Git worktree from this checkout.
- `quant-skills/` is not a separate Git worktree from this checkout.

Reference checkout sizes:

- `yahoo-finance-api/`: 5.5 MB.
- `quant-skills/`: 2.6 MB.

Baseline handling decision:

- Treat `yahoo-finance-api/` as a local reference checkout for P3-2A.
- Treat `quant-skills/` as unrelated local reference material until explicitly adopted.
- Do not stage either reference directory as bulk material without a deliberate decision.

## Service State

OrbStack / Docker:

- `qadam-postgres` is running and healthy.
- Container image: `timescale/timescaledb:latest-pg16`.
- Observed status: up for roughly 22 hours at audit time.

Postgres / Timescale from Qadam checks:

- Service connection outside the sandbox reports `postgres_timescale_status=online`.
- Schema check reports `postgres_timescale_schema_status=unavailable`.
- Blocker: `asyncpg is not installed. Run scripts/bootstrap_runtime.sh first.`
- Replay check reports `postgres_replay_contract_status=schema_unavailable`.

LM Studio:

- Local live model-list probe reports `llm_provider_status=ok`.
- `gemini_configured=True`, but Gemini was not called.
- `local_probe_status=ok`.
- `local_model_available=True`.
- Resolved local model: `google/gemma-4-e4b`.
- Available local model count: 2.

## Phase 1 Data Spine

`scripts/check_phase1_data_spine.py` passed.

- `source_count=35`
- `expected_source_count=35`
- `pipeline_count=5`
- `promoted_adapter_count=19`
- `missing_credential_source_count=12`
- `deferred_count=3`
- `test_observation_count=35`
- Boundary: read-only deterministic observations only; no signal confidence or execution authority.

## Agent OS

`scripts/check_phase1_agent_os.py` passed.

- `agent_count=8`
- `skill_count=7`
- `tool_grant_count=165`
- `secret_name_grant_count=13`
- `broker_write_block_count=24`
- `undeclared_tool_block_count=8`
- `sample_output_count=8`
- Boundary: agents are permissioned, sample outputs are non-executable, and broker-write tools fail closed.

## Safety And Authority Counters

Signal Integrity Gate:

- Status: ok.
- Reviews processed in latest check: 5.
- Blocked: 2.
- Hold for corroboration: 3.
- Passed to risk shadow: 0.
- Execution allowed: 0.
- Paper order allowed: 0.
- Trade candidate created: 0.

Risk Agent:

- Status: ok.
- Review count: 7.
- Blocked before risk: 7.
- Shadow ready: 0.
- Execution allowed: 0.
- Paper order allowed: 0.
- Order created: 0.
- Broker write allowed: 0.

Execution Policy:

- Status: ok.
- Review count: 5.
- Kill-switch hold: 5.
- Paper-order shadow ready: 0.
- Execution allowed: 0.
- Staged paper order allowed: 0.
- Paper order created: 0.
- Broker write allowed: 0.
- Live capital enabled: 0.

Disabled staged paper-order contract:

- Status: ok.
- Review count: 5.
- Blocked before staging: 5.
- Execution allowed: 0.
- Staged paper order created: 0.
- Paper order submittable: 0.
- Broker write allowed: 0.
- Live capital enabled: 0.

Broker reconciliation:

- Status: ok.
- Review count: 5.
- Blocked before broker reconciliation: 5.
- Idempotency key allocated: 0.
- Event Log prewrite created: 0.
- Pre-trade snapshot created: 0.
- Duplicate-order guard ready: 0.
- Broker echo verified: 0.
- Post-submit reconciliation ready: 0.
- Paper order submit allowed: 0.
- Broker write allowed: 0.
- Live capital enabled: 0.

Dry-run paper-submit receipt:

- Status: ok.
- Review count: 5.
- Blocked before dry-run submit: 5.
- Dry-run receipt created: 0.
- Paper order submitted: 0.
- Broker POST called: 0.
- Broker write allowed: 0.
- Live capital enabled: 0.

Quantum oracle:

- Status: ok.
- Backend: `classical_fallback`.
- Local simulation mode: `deterministic_classical_shadow`.
- Job count: 2.
- Result count in latest check: 2.
- Store result count: 12.
- Qiskit available: false.
- Qiskit Aer available: false.
- Hardware submitted: 0.
- Hardware submission allowed: 0.
- Hardware scheduler enabled: 0.
- Execution allowed: 0.
- Paper order allowed: 0.
- Trade candidate created: 0.

## Runtime Blockers

P3-3 blocker:

- `qadam-postgres` is healthy, but Qadam's current Python runtime cannot run schema/replay checks because `asyncpg` is missing.
- Required next action before certifying P3-3: run `scripts/bootstrap_runtime.sh` or activate/fix the intended virtual environment so `asyncpg` is available, then rerun:

```bash
./scripts/check_postgres_timescale_ingestion.py --require-live
./scripts/check_postgres_timescale_replay.py --require-full-source-coverage
```

Git hygiene blocker before committing:

- Decide whether `yahoo-finance-api/` and `quant-skills/` should be ignored, adopted, vendored, or moved outside the main repo.
- Do not commit those directories accidentally as unreviewed bulk reference material.

## P3-0 Acceptance Checklist

- Main repo status checked.
- Nested static-site repo status checked.
- Local reference checkouts identified.
- Staging area checked.
- OrbStack/Postgres state checked.
- LM Studio state checked.
- Phase 1 data-spine gate checked.
- Agent OS gate checked.
- Safety and zero-authority counters checked.
- Quantum zero-authority counters checked.
- Runtime blockers recorded.
- No staged secret-containing file detected because no files are staged.

## Next Stage

Proceed to P3-1 Foundation Health.

Do not certify P3-3 Durable Observation Spine until the `asyncpg` runtime blocker is resolved.
