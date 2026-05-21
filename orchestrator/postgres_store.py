"""Optional Postgres/Timescale persistence helpers.

The foundation runs without this module when Postgres is unavailable. Once the
local store is running and dependencies are installed, these helpers seed and
verify the durable tables defined in `migrations/`.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from orchestrator.config import Settings
from orchestrator.ingestion import SourceObservation
from orchestrator.local_store import local_store_health
from orchestrator.resource_registry import RESOURCE_ENTRIES
from orchestrator.world_model import CLAIM_CARDS
from world_monitor.source_registry import EXPECTED_SOURCE_COUNT, SOURCE_SPECS


def _load_asyncpg():
    try:
        import asyncpg
    except ImportError as exc:
        raise RuntimeError("asyncpg is not installed. Run scripts/bootstrap_runtime.sh first.") from exc
    return asyncpg


async def connect(settings: Settings | None = None):
    asyncpg = _load_asyncpg()
    settings = settings or Settings.from_env()
    return await asyncpg.connect(settings.database_url)


async def schema_state(settings: Settings | None = None) -> dict[str, Any]:
    table_names = (
        "event_log",
        "reference_registry",
        "world_model_claim",
        "governance_comment",
        "source_observation",
        "schema_migrations",
    )
    conn = await connect(settings)
    try:
        rows = await conn.fetch(
            """
            SELECT table_name
            FROM information_schema.tables
            WHERE table_schema = 'public'
              AND table_name = ANY($1::text[])
            ORDER BY table_name
            """,
            list(table_names),
        )
        existing_tables = [row["table_name"] for row in rows]
        migrations = []
        if "schema_migrations" in existing_tables:
            migrations = [
                row["version"]
                for row in await conn.fetch("SELECT version FROM schema_migrations ORDER BY version")
            ]
        return {
            "status": "ok",
            "expected_tables": list(table_names),
            "tables": existing_tables,
            "missing_tables": [name for name in table_names if name not in existing_tables],
            "migrations": migrations,
        }
    finally:
        await conn.close()


async def seed_reference_and_world_model(settings: Settings | None = None) -> dict[str, int]:
    conn = await connect(settings)
    try:
        async with conn.transaction():
            for resource in RESOURCE_ENTRIES:
                await conn.execute(
                    """
                    INSERT INTO reference_registry (
                        key,
                        name,
                        category,
                        source,
                        role,
                        mapped_modules,
                        validation_status,
                        production_active,
                        decision_notes
                    )
                    VALUES ($1, $2, $3, $4, $5, $6::text[], $7, $8, $9)
                    ON CONFLICT (key) DO UPDATE SET
                        name = EXCLUDED.name,
                        category = EXCLUDED.category,
                        source = EXCLUDED.source,
                        role = EXCLUDED.role,
                        mapped_modules = EXCLUDED.mapped_modules,
                        validation_status = EXCLUDED.validation_status,
                        production_active = EXCLUDED.production_active,
                        decision_notes = EXCLUDED.decision_notes
                    """,
                    resource.key,
                    resource.name,
                    resource.category,
                    resource.source,
                    resource.role,
                    list(resource.mapped_modules),
                    resource.validation_status,
                    resource.production_active,
                    resource.decision_notes,
                )

            for claim in CLAIM_CARDS:
                await conn.execute(
                    """
                    INSERT INTO world_model_claim (
                        key,
                        source_path,
                        claim,
                        claim_type,
                        actors,
                        mechanism,
                        observable_signatures,
                        live_sources_to_check,
                        market_channels,
                        corroboration_status,
                        postmortem_score,
                        evidence_boundary
                    )
                    VALUES ($1, $2, $3, $4, $5::text[], $6, $7::text[], $8::text[], $9::text[], $10, $11, $12)
                    ON CONFLICT (key) DO UPDATE SET
                        source_path = EXCLUDED.source_path,
                        claim = EXCLUDED.claim,
                        claim_type = EXCLUDED.claim_type,
                        actors = EXCLUDED.actors,
                        mechanism = EXCLUDED.mechanism,
                        observable_signatures = EXCLUDED.observable_signatures,
                        live_sources_to_check = EXCLUDED.live_sources_to_check,
                        market_channels = EXCLUDED.market_channels,
                        corroboration_status = EXCLUDED.corroboration_status,
                        postmortem_score = EXCLUDED.postmortem_score,
                        evidence_boundary = EXCLUDED.evidence_boundary
                    """,
                    claim.key,
                    claim.source_path,
                    claim.claim,
                    claim.claim_type,
                    list(claim.actors),
                    claim.mechanism,
                    list(claim.observable_signatures),
                    list(claim.live_sources_to_check),
                    list(claim.market_channels),
                    claim.corroboration_status,
                    claim.postmortem_score,
                    claim.evidence_boundary,
                )

        return {
            "reference_registry": len(RESOURCE_ENTRIES),
            "world_model_claim": len(CLAIM_CARDS),
        }
    finally:
        await conn.close()


async def write_source_observations(
    observations: list[SourceObservation],
    settings: Settings | None = None,
) -> dict[str, int]:
    conn = await connect(settings)
    try:
        async with conn.transaction():
            for observation in observations:
                observed_at = datetime.fromisoformat(observation.observed_at)
                await conn.execute(
                    """
                    INSERT INTO source_observation (
                        schema_version,
                        source_key,
                        source_name,
                        pipeline,
                        tier,
                        mode,
                        adapter_status,
                        observed_at,
                        latency_ms,
                        trust_score,
                        payload
                    )
                    VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11::jsonb)
                    """,
                    observation.schema_version,
                    observation.source_key,
                    observation.source_name,
                    observation.pipeline,
                    observation.tier,
                    observation.mode,
                    observation.adapter_status,
                    observed_at,
                    observation.latency_ms,
                    observation.trust_score,
                    json.dumps(observation.payload, sort_keys=True),
                )
                await conn.execute(
                    """
                    INSERT INTO event_log (
                        schema_version,
                        event_type,
                        component,
                        severity,
                        payload,
                        correlation_id,
                        created_at
                    )
                    VALUES ($1, $2, $3, $4, $5::jsonb, $6, $7)
                    """,
                    1,
                    "source_test_observation_recorded",
                    "ingestion",
                    "info",
                    json.dumps(
                        {
                            "source_key": observation.source_key,
                            "pipeline": observation.pipeline,
                            "tier": observation.tier,
                            "mode": observation.mode,
                            "adapter_status": observation.adapter_status,
                        },
                        sort_keys=True,
                    ),
                    uuid4(),
                    datetime.now(timezone.utc),
                )
        return {"source_observation": len(observations), "event_log": len(observations)}
    finally:
        await conn.close()


async def durable_ingestion_state(settings: Settings | None = None) -> dict[str, Any]:
    """Return read-only durable replay coverage for the cockpit.

    This does not write observations. It only verifies whether the local
    Postgres/Timescale target can replay the canonical source set.
    """

    settings = settings or Settings.from_env()
    expected_source_keys = {source.key for source in SOURCE_SPECS}
    base: dict[str, Any] = {
        "schema_version": 1,
        "database_configured": bool(settings.database_url),
        "expected_source_count": EXPECTED_SOURCE_COUNT,
        "observation_count": 0,
        "replayed_source_count": 0,
        "event_log_ingestion_event_count": 0,
        "missing_source_count": EXPECTED_SOURCE_COUNT,
        "missing_sources": sorted(expected_source_keys),
        "first_observed_at": None,
        "latest_observed_at": None,
        "write_authority": False,
        "signal_authority": False,
        "order_authority": False,
        "boundary": (
            "Read-only durable ingestion readiness. It cannot create signals, "
            "trade candidates, orders, broker writes, or live-capital authority."
        ),
    }

    stores = local_store_health(settings)
    postgres_online = "postgres" not in stores["summary"]["offline_services"]
    if not postgres_online:
        return base | {
            "status": "ready_waiting_for_local_service",
            "service_status": "offline",
            "contract_status": "ready_waiting_for_local_service",
            "replay_status": "offline",
            "schema_status": "not_checked",
            "missing_tables": [],
            "next_step": (
                "Start Docker, OrbStack, Podman, or Colima and run "
                "scripts/start_postgres_timescale_ingestion.sh."
            ),
        }

    try:
        state = await schema_state(settings)
    except Exception as exc:  # noqa: BLE001 - cockpit needs safe degradation details.
        return base | {
            "status": "degraded",
            "service_status": "online",
            "contract_status": "schema_unavailable",
            "replay_status": "unavailable",
            "schema_status": "unavailable",
            "schema_error": exc.__class__.__name__,
            "missing_tables": [],
            "next_step": "Apply migrations and rerun the durable ingestion bootstrap.",
        }

    missing_tables = list(state.get("missing_tables", []))
    if missing_tables:
        return base | {
            "status": "missing_tables",
            "service_status": "online",
            "contract_status": "schema_incomplete",
            "replay_status": "missing_tables",
            "schema_status": state.get("status", "unknown"),
            "missing_tables": missing_tables,
            "next_step": "Run scripts/apply_migrations.py, then rerun durable ingestion.",
        }

    conn = await connect(settings)
    try:
        summary = await conn.fetchrow(
            """
            SELECT
                COUNT(*)::int AS observation_count,
                COUNT(DISTINCT source_key)::int AS distinct_source_count,
                MIN(observed_at) AS first_observed_at,
                MAX(observed_at) AS latest_observed_at
            FROM source_observation
            """
        )
        event_log_count = await conn.fetchval(
            """
            SELECT COUNT(*)::int
            FROM event_log
            WHERE event_type = 'source_test_observation_recorded'
            """
        )
        rows = await conn.fetch(
            """
            SELECT source_key
            FROM source_observation
            GROUP BY source_key
            ORDER BY source_key
            """
        )
    finally:
        await conn.close()

    observed_source_keys = {row["source_key"] for row in rows}
    missing_source_keys = sorted(expected_source_keys - observed_source_keys)
    replay_status = "ok" if not missing_source_keys else "partial"

    return base | {
        "status": "ok" if replay_status == "ok" else "partial",
        "service_status": "online",
        "contract_status": "durable_replay_ready" if replay_status == "ok" else "durable_replay_partial",
        "replay_status": replay_status,
        "schema_status": state.get("status", "ok"),
        "missing_tables": [],
        "observation_count": int(summary["observation_count"] or 0),
        "replayed_source_count": int(summary["distinct_source_count"] or 0),
        "event_log_ingestion_event_count": int(event_log_count or 0),
        "missing_source_count": len(missing_source_keys),
        "missing_sources": missing_source_keys,
        "first_observed_at": str(summary["first_observed_at"]) if summary["first_observed_at"] else None,
        "latest_observed_at": str(summary["latest_observed_at"]) if summary["latest_observed_at"] else None,
        "next_step": (
            "Replay coverage is complete."
            if replay_status == "ok"
            else "Run scripts/run_test_ingestion_durable.py --all, then verify replay coverage."
        ),
    }


def durable_ingestion_status(settings: Settings | None = None) -> dict[str, Any]:
    """Synchronous public-safe durable ingestion readiness wrapper."""

    import asyncio

    return asyncio.run(durable_ingestion_state(settings))
