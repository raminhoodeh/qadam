# Qadam Pre-Phase-3 Durable Observation Spine Audit - 2026-05-22

This is the Stage P3-3 durable observation spine audit for `docs/qadam-pre-phase-3-implementation-plan.md`.

## Audit Decision

Stage P3-3 is complete.

Postgres/Timescale is running locally, migrations are applied, durable foundation/reference rows are seeded, deterministic source observations exist for all 35 canonical sources, strict replay coverage is green, replay is read-only, offline service degradation is explicit, and cockpit Mission Control reports the durable replay state accurately.

No signal, candidate, order, broker-write, live-capital, or quantum hardware authority was added.

## Commands Run

Primary durable spine entrypoint:

```bash
./scripts/start_postgres_timescale_ingestion.sh
```

Replay and read-only stability checks:

```bash
.venv/bin/python scripts/check_postgres_timescale_replay.py --require-full-source-coverage
.venv/bin/python -c "<read-only source_observation/event_log count query>"
.venv/bin/python scripts/check_postgres_timescale_replay.py --require-full-source-coverage
.venv/bin/python -c "<read-only source_observation/event_log count query>"
```

Offline-degrade checks without stopping the real local service:

```bash
env DATABASE_URL=postgresql://qadam:qadam@127.0.0.1:65432/qadam .venv/bin/python scripts/check_postgres_timescale_ingestion.py
env DATABASE_URL=postgresql://qadam:qadam@127.0.0.1:65432/qadam .venv/bin/python scripts/check_postgres_timescale_replay.py
```

Cockpit status checks:

```bash
.venv/bin/python scripts/export_cockpit_status.py
.venv/bin/python scripts/check_cockpit_status.py
```

## Durable Startup And Migration

`scripts/start_postgres_timescale_ingestion.sh` passed.

Key startup results:

- `postgres_timescale_runtime_status=found`
- `qadam-postgres` container was already running.
- `postgres_wait_status=ok`
- `postgres_wait_attempts=1`
- `migration_count=4`
- `migrations_applied=0`
- `migrations_skipped=4`
- `migration_check=ok`

Interpretation:

- The local Docker-compatible runtime is available.
- Postgres/Timescale is reachable.
- The database schema is already current.

## Durable Foundation Seed

Foundation seed passed.

Key results:

- `durable_seed_status=ok`
- `reference_registry_seeded=29`
- `world_model_claim_seeded=5`

Interpretation:

- Durable reference registry rows and world-model claim rows are available for local replay/context.
- These are local foundation records only and do not create trading authority.

## Deterministic Durable Ingestion

Full deterministic durable ingestion passed.

Key results:

- `durable_test_ingestion_status=ok`
- `durable_test_ingestion_selected_count=35`
- `durable_test_ingestion_expected_source_count=35`
- `event_log_inserted=35`
- `source_observation_inserted=35`

The follow-on live ingestion check also passed:

- `postgres_timescale_status=online`
- `postgres_timescale_require_live=True`
- `postgres_timescale_database_url_configured=True`
- `postgres_timescale_schema_status=ok`
- `postgres_timescale_missing_tables=[]`
- `postgres_timescale_source_observation_inserted=5`
- `postgres_timescale_event_log_inserted=5`
- `postgres_timescale_ingestion_check=ok`

Boundary:

- Durable ingestion writes local Postgres/Timescale observations only.
- It cannot create signals, trade candidates, orders, broker writes, live capital, or quantum jobs.

## Strict Replay Coverage

Strict replay check passed.

Key results:

- `postgres_replay_schema_status=ok`
- `postgres_replay_missing_tables=[]`
- `postgres_replay_status=ok`
- `postgres_replay_contract_status=durable_replay_ready`
- `postgres_replay_observation_count=90`
- `postgres_replay_distinct_source_count=35`
- `postgres_replay_expected_source_count=35`
- `postgres_replay_event_log_ingestion_event_count=90`
- `postgres_replay_first_observed_at=2026-05-21 16:39:38.735284+00:00`
- `postgres_replay_latest_observed_at=2026-05-22 18:26:04.051596+00:00`
- `postgres_replay_missing_source_count=0`
- `postgres_replay_check=ok`

Read-only stability check:

- Count before replay: `source_observation=90`, distinct sources 35, ingestion events 90.
- Count after replay: `source_observation=90`, distinct sources 35, ingestion events 90.
- The replay command did not write new rows.

Boundary:

- Replay is read-only.
- Replayable durable observations cannot create signals or orders.

## Offline Degradation

Offline behavior was checked by pointing `DATABASE_URL` at an unused local port. The real Postgres container was not stopped.

Ingestion offline-degrade result:

- `postgres_timescale_status=offline`
- `postgres_timescale_require_live=False`
- `postgres_timescale_contract_status=ready_waiting_for_local_service`
- `postgres_timescale_ingestion_check=ok`

Replay offline-degrade result:

- `postgres_replay_status=offline`
- `postgres_replay_missing_service=postgres`
- `postgres_replay_contract_status=ready_waiting_for_local_service`
- `postgres_replay_check=ok`

Interpretation:

- When Postgres is unavailable and live mode is not required, the contract reports `ready_waiting_for_local_service`.
- It does not report false durable readiness.

## Cockpit Mission Control

`scripts/export_cockpit_status.py` passed and refreshed the public-safe status snapshot.

Key export results:

- `cockpit_status_export=ok`
- `cockpit_status_d1_phase=D1`
- `cockpit_status_d1_read_only=True`
- `cockpit_status_d1_public_safe=True`
- Runtime snapshot: `data/runtime/cockpit-status.json`
- Static snapshot: `landing-page-repo/status/cockpit-status.json`

`scripts/check_cockpit_status.py` passed.

Key durable Mission Control results:

- `cockpit_status_check=ok`
- `cockpit_status_mode=paper`
- `cockpit_status_d1_read_only=True`
- `cockpit_status_d1_public_safe=True`
- `cockpit_status_mission_control_status=read_only_mission_control`
- `cockpit_status_live_capital_enabled=False`
- `cockpit_status_durable_ingestion_status=ok`
- `cockpit_status_durable_ingestion_contract_status=durable_replay_ready`
- `cockpit_status_durable_ingestion_replay_status=ok`
- `cockpit_status_durable_ingestion_replayed_source_count=35`
- Boundary: public-safe read-only snapshot; it cannot trigger trading and contains no secrets.

File-state note:

- `landing-page-repo/status/cockpit-status.json` and `landing-page-repo/status/cockpit-status.signature.json` were refreshed by the cockpit export.
- Do not deploy or commit those nested static-site files blindly; review them with the surrounding deployment plan first.

## P3-3 Acceptance Checklist

- Docker-compatible local runtime is available.
- Postgres/Timescale is reachable.
- Migrations are applied.
- Durable reference registry rows are seeded.
- Durable world-model claim rows are seeded.
- Deterministic source observations were written for all 35 canonical sources.
- `source_observation` can replay all 35 canonical source keys.
- Replay is read-only and leaves counts unchanged.
- Offline Postgres degrades to `ready_waiting_for_local_service`.
- Cockpit Mission Control reports durable replay as `durable_replay_ready`.
- No signal, candidate, order, broker-write, live-capital, or quantum hardware authority is enabled.

## Next Stage

Proceed to P3-4 Agent OS Enforcement.
