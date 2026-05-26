"""FastMCP-style tool scaffold.

This module can run without FastMCP installed so the repository remains inspectable
before dependencies are installed.
"""

from __future__ import annotations

from orchestrator.agent_registry import (
    agent_detail as registry_agent_detail,
    agent_registry as registry_agents,
    agent_registry_summary,
    skill_detail as registry_skill_detail,
    skill_registry as registry_skills,
)
from orchestrator.agent_runtime import (
    agent_runtime_summary,
    authorize_tool_call,
    create_shadow_triage_packet,
    shadow_triage_queue_summary,
)
from orchestrator.adapters import (
    fetch_gdelt_live_sync,
    fetch_gdelt_sample,
    fetch_fred_live_sync,
    fetch_fred_sample,
    fetch_oref_live_sync,
    fetch_oref_sample,
    fetch_nasa_firms_live_sync,
    fetch_nasa_firms_sample,
    fetch_rss_live_sync,
    fetch_rss_sample,
    fred_adapter_status,
    gdelt_adapter_status,
    nasa_firms_adapter_status,
    oref_adapter_status,
    rss_adapter_status,
)
from orchestrator.config import Settings
from orchestrator.execution import execution_registry
from orchestrator.governance import GovernanceStore
from orchestrator.ingestion import ingestion_spine_summary
from orchestrator.ingestion import run_test_ingestion as run_test_ingestion_spine
from orchestrator.intelligence import (
    gemini_credential_probe,
    local_research_analyst_status as local_research_analyst_status_once,
    lm_studio_models_probe,
    provider_status as intelligence_provider_status,
    run_local_research_analyst_inference as run_local_research_analyst_inference_once,
    run_research_shadow_triage_queue as run_research_shadow_triage_queue_once,
    run_shadow_intelligence_sample as run_shadow_intelligence_sample_once,
    shadow_intelligence_summary,
)
from orchestrator.historical_backfill import build_historical_backfill_plan, run_historical_backfill
from orchestrator.local_store import local_store_health
from orchestrator.phase1_live_adapters import (
    fetch_phase1_live_adapter_live_sync,
    fetch_phase1_live_adapter_sample,
    phase1_live_adapter_registry,
    phase1_live_adapter_status as phase1_live_adapter_status_once,
)
from orchestrator.postgres_store import schema_state
from orchestrator.quantum import quantum_providers
from orchestrator.resource_registry import (
    resource_detail as registry_resource_detail,
)
from orchestrator.resource_registry import (
    resource_registry as registry_resources,
)
from orchestrator.resource_registry import (
    resource_registry_summary,
)
from orchestrator.secrets import secret_statuses, validate_secret_file
from orchestrator.source_health import run_source_heartbeat as run_source_heartbeat_once
from orchestrator.source_health import source_heartbeat_summary
from orchestrator.system_state import build_system_health, founding_fund_managers, module_map
from orchestrator.telegram_comms import ensure_d8a_telegram_dry_run, telegram_status
from orchestrator.trust_scores import build_trust_score_seed
from orchestrator.world_model import (
    world_model_claim_detail as registry_world_model_claim_detail,
)
from orchestrator.world_model import (
    world_model_claims as registry_world_model_claims,
)
from orchestrator.world_model import (
    world_model_summary,
)
from world_monitor.source_registry import SOURCE_SPECS, get_source

try:
    from fastmcp import FastMCP
except Exception:  # pragma: no cover - dependency may not be installed yet
    FastMCP = None  # type: ignore[assignment]


def ticker_echo(ticker: str) -> dict[str, str]:
    return {"ticker": ticker.upper(), "status": "ok"}


def source_registry() -> list[dict[str, object]]:
    return [
        {
            "key": source.key,
            "name": source.name,
            "pipeline": source.pipeline,
            "tier": source.tier,
            "tool_name": source.tool_name,
            "status": source.status,
        }
        for source in SOURCE_SPECS
    ]


def source_detail(key: str) -> dict[str, object]:
    source = get_source(key)
    return {
        "key": source.key,
        "name": source.name,
        "pipeline": source.pipeline,
        "tier": source.tier,
        "auth": source.auth,
        "endpoints": source.endpoints,
        "cadence": source.cadence,
        "rate_limit": source.rate_limit,
        "env_vars": source.env_vars,
        "status": source.status,
        "notes": source.notes,
    }


def resource_registry(category: str | None = None) -> dict[str, object]:
    return {
        "summary": resource_registry_summary(),
        "resources": registry_resources(category),
    }


def resource_detail(key: str) -> dict[str, object]:
    return registry_resource_detail(key)


def world_model_claims() -> dict[str, object]:
    return {
        "summary": world_model_summary(),
        "claims": registry_world_model_claims(),
    }


def world_model_claim_detail(key: str) -> dict[str, object]:
    return registry_world_model_claim_detail(key)


def agent_registry_status() -> dict[str, object]:
    return agent_registry_summary()


def agent_registry() -> dict[str, object]:
    return {
        "summary": agent_registry_summary(),
        "agents": registry_agents(),
    }


def agent_detail(key: str) -> dict[str, object]:
    return registry_agent_detail(key)


def skill_registry() -> dict[str, object]:
    return {
        "summary": agent_registry_summary(),
        "skills": registry_skills(),
    }


def skill_detail(key: str) -> dict[str, object]:
    return registry_skill_detail(key)


def agent_runtime_status() -> dict[str, object]:
    return agent_runtime_summary(Settings.from_env())


def agent_tool_authorization(agent_key: str, tool_name: str) -> dict[str, object]:
    return authorize_tool_call(agent_key, tool_name).to_dict()


def research_shadow_triage_queue() -> dict[str, object]:
    return shadow_triage_queue_summary(Settings.from_env())


def create_research_shadow_triage_packet(
    source_event_refs: list[str],
    summary: str,
    uncertainty: str = "unknown",
) -> dict[str, object]:
    return create_shadow_triage_packet(
        source_event_refs=tuple(source_event_refs),
        summary=summary,
        uncertainty=uncertainty,
        settings=Settings.from_env(),
    )


def governance_comments(limit: int = 20) -> dict[str, object]:
    store = GovernanceStore()
    return {
        "health": store.health(),
        "comments": [comment.to_dict() for comment in store.read_comments(limit=limit)],
    }


def create_governance_comment(
    author_email: str,
    author_name: str,
    target_type: str,
    target_key: str,
    body: str,
    tags: list[str] | None = None,
    status: str = "suggestion",
) -> dict[str, object]:
    store = GovernanceStore()
    comment = store.add_comment(
        author_email=author_email,
        author_name=author_name,
        target_type=target_type,
        target_key=target_key,
        body=body,
        tags=tuple(tags or ()),
        status=status,
    )
    return comment.to_dict()


def ingestion_status() -> dict[str, object]:
    return ingestion_spine_summary(Settings.from_env())


def source_heartbeat_status() -> dict[str, object]:
    return source_heartbeat_summary(Settings.from_env())


def run_source_heartbeat() -> dict[str, object]:
    return run_source_heartbeat_once(settings=Settings.from_env())


def run_test_ingestion(limit: int = 5, tier: int | None = None, pipeline: str | None = None) -> dict[str, object]:
    return run_test_ingestion_spine(limit=limit, tier=tier, pipeline=pipeline)


def phase1_live_adapter_registry_status() -> dict[str, object]:
    return phase1_live_adapter_registry(Settings.from_env())


def phase1_live_adapter_status(source_key: str) -> dict[str, object]:
    return phase1_live_adapter_status_once(source_key, Settings.from_env())


def phase1_live_adapter_sample(source_key: str) -> dict[str, object]:
    return fetch_phase1_live_adapter_sample(source_key)


def phase1_live_adapter_live_read_only(source_key: str) -> dict[str, object]:
    return fetch_phase1_live_adapter_live_sync(source_key)


def historical_backfill_plan() -> dict[str, object]:
    return build_historical_backfill_plan(Settings.from_env())


def run_historical_backfill_sample(source_keys: list[str] | None = None) -> dict[str, object]:
    return run_historical_backfill(source_keys=tuple(source_keys or ()), settings=Settings.from_env())


def trust_score_seed_status() -> dict[str, object]:
    return build_trust_score_seed(Settings.from_env())


def postgres_timescale_ingestion_status() -> dict[str, object]:
    settings = Settings.from_env()
    stores = local_store_health(settings)
    postgres_online = "postgres" not in stores["summary"]["offline_services"]
    payload: dict[str, object] = {
        "status": "online" if postgres_online else "offline",
        "database_url_configured": bool(settings.database_url),
        "contract_status": "ready" if postgres_online else "ready_waiting_for_local_service",
        "boundary": "Durable ingestion status is read-only. It cannot create signals or orders.",
    }
    if postgres_online:
        import asyncio

        try:
            payload["schema"] = asyncio.run(schema_state(settings))
        except Exception as exc:  # noqa: BLE001 - MCP status should report degraded database details
            payload["status"] = "degraded"
            payload["schema_error"] = str(exc)
    return payload


def shadow_intelligence_status() -> dict[str, object]:
    return shadow_intelligence_summary(Settings.from_env())


def shadow_intelligence_provider_status() -> dict[str, object]:
    return intelligence_provider_status(Settings.from_env())


def shadow_intelligence_provider_probes(
    local_live: bool = False,
    gemini_live: bool = False,
) -> dict[str, object]:
    return intelligence_provider_status(
        Settings.from_env(),
        local_live=local_live,
        gemini_live=gemini_live,
    )


def lm_studio_models_status(live: bool = False) -> dict[str, object]:
    return lm_studio_models_probe(Settings.from_env(), live=live)


def gemini_credential_status(live: bool = False) -> dict[str, object]:
    return gemini_credential_probe(Settings.from_env(), live=live)


def run_shadow_intelligence_sample() -> dict[str, object]:
    return run_shadow_intelligence_sample_once()


def run_research_shadow_triage_queue(limit: int = 10) -> dict[str, object]:
    return run_research_shadow_triage_queue_once(limit=limit)


def local_research_analyst_status() -> dict[str, object]:
    return local_research_analyst_status_once(Settings.from_env())


def run_local_research_analyst_inference(limit: int = 5, live: bool = False) -> dict[str, object]:
    return run_local_research_analyst_inference_once(
        limit=limit,
        live=live,
        settings=Settings.from_env(),
    )


def telegram_communications_status() -> dict[str, object]:
    return telegram_status(Settings.from_env())


def queue_telegram_dry_run_samples() -> dict[str, object]:
    return ensure_d8a_telegram_dry_run(Settings.from_env())


def gdelt_status() -> dict[str, object]:
    return gdelt_adapter_status(Settings.from_env())


def gdelt_sample(query: str = "oil") -> dict[str, object]:
    return fetch_gdelt_sample(query=query)


def gdelt_live_read_only(
    query: str = "oil",
    since_iso: str | None = None,
    theme_code: str | None = None,
    maxrecords: int = 10,
) -> dict[str, object]:
    return fetch_gdelt_live_sync(
        query=query,
        since_iso=since_iso,
        theme_code=theme_code,
        maxrecords=maxrecords,
    )


def oref_status() -> dict[str, object]:
    return oref_adapter_status(Settings.from_env())


def oref_sample() -> dict[str, object]:
    return fetch_oref_sample()


def oref_live_read_only() -> dict[str, object]:
    return fetch_oref_live_sync()


def nasa_firms_status() -> dict[str, object]:
    return nasa_firms_adapter_status(Settings.from_env())


def nasa_firms_sample(bbox: str | None = None, days: int = 1) -> dict[str, object]:
    return fetch_nasa_firms_sample(bbox=bbox, days=days)


def nasa_firms_live_read_only(
    bbox: str | None = None,
    days: int = 1,
    source: str | None = None,
) -> dict[str, object]:
    return fetch_nasa_firms_live_sync(bbox=bbox, days=days, source=source)


def rss_status() -> dict[str, object]:
    return rss_adapter_status(Settings.from_env())


def rss_sample(keyword_filter: list[str] | None = None) -> dict[str, object]:
    return fetch_rss_sample(keyword_filter=tuple(keyword_filter or ()))


def rss_live_read_only(
    feed_urls: list[str] | None = None,
    since_iso: str | None = None,
    keyword_filter: list[str] | None = None,
) -> dict[str, object]:
    return fetch_rss_live_sync(
        feed_urls=tuple(feed_urls or ()),
        since_iso=since_iso,
        keyword_filter=tuple(keyword_filter or ()),
    )


def fred_status() -> dict[str, object]:
    return fred_adapter_status(Settings.from_env())


def fred_sample(
    series_ids: list[str] | None = None,
    alert_on_sigma: float | None = None,
) -> dict[str, object]:
    return fetch_fred_sample(
        series_ids=tuple(series_ids or ()),
        alert_on_sigma=alert_on_sigma,
    )


def fred_live_read_only(
    series_ids: list[str] | None = None,
    observation_start: str | None = None,
    limit: int = 45,
    alert_on_sigma: float | None = None,
) -> dict[str, object]:
    return fetch_fred_live_sync(
        series_ids=tuple(series_ids or ()),
        observation_start=observation_start,
        limit=limit,
        alert_on_sigma=alert_on_sigma,
    )


def system_health() -> dict[str, object]:
    return build_system_health(Settings.from_env())


def execution_venues() -> list[dict[str, object]]:
    return execution_registry()


def founding_manager_access() -> dict[str, object]:
    return founding_fund_managers(Settings.from_env())


def qadam_module_map() -> list[dict[str, str]]:
    return module_map()


def quantum_provider_registry() -> list[dict[str, object]]:
    return quantum_providers(Settings.from_env())


def secret_registry_status() -> dict[str, object]:
    settings = Settings.from_env()
    keys = ("QCTRL_API_KEY", "IBM_QUANTUM_TOKEN", "AWS_ACCESS_KEY_ID", "PREFERENCE_API_KEY")
    return {
        "secret_file": validate_secret_file(settings.secrets_file),
        "secrets": secret_statuses(keys, settings),
    }


def build_server():
    if FastMCP is None:
        return None
    mcp = FastMCP("qadam")
    mcp.tool()(ticker_echo)
    mcp.tool()(source_registry)
    mcp.tool()(source_detail)
    mcp.tool()(resource_registry)
    mcp.tool()(resource_detail)
    mcp.tool()(world_model_claims)
    mcp.tool()(world_model_claim_detail)
    mcp.tool()(agent_registry_status)
    mcp.tool()(agent_registry)
    mcp.tool()(agent_detail)
    mcp.tool()(skill_registry)
    mcp.tool()(skill_detail)
    mcp.tool()(agent_runtime_status)
    mcp.tool()(agent_tool_authorization)
    mcp.tool()(research_shadow_triage_queue)
    mcp.tool()(create_research_shadow_triage_packet)
    mcp.tool()(governance_comments)
    mcp.tool()(create_governance_comment)
    mcp.tool()(ingestion_status)
    mcp.tool()(source_heartbeat_status)
    mcp.tool()(run_source_heartbeat)
    mcp.tool()(run_test_ingestion)
    mcp.tool()(phase1_live_adapter_registry_status)
    mcp.tool()(phase1_live_adapter_status)
    mcp.tool()(phase1_live_adapter_sample)
    mcp.tool()(phase1_live_adapter_live_read_only)
    mcp.tool()(historical_backfill_plan)
    mcp.tool()(run_historical_backfill_sample)
    mcp.tool()(trust_score_seed_status)
    mcp.tool()(postgres_timescale_ingestion_status)
    mcp.tool()(shadow_intelligence_status)
    mcp.tool()(shadow_intelligence_provider_status)
    mcp.tool()(shadow_intelligence_provider_probes)
    mcp.tool()(lm_studio_models_status)
    mcp.tool()(gemini_credential_status)
    mcp.tool()(run_shadow_intelligence_sample)
    mcp.tool()(run_research_shadow_triage_queue)
    mcp.tool()(local_research_analyst_status)
    mcp.tool()(run_local_research_analyst_inference)
    mcp.tool()(telegram_communications_status)
    mcp.tool()(queue_telegram_dry_run_samples)
    mcp.tool()(gdelt_status)
    mcp.tool()(gdelt_sample)
    mcp.tool()(gdelt_live_read_only)
    mcp.tool()(oref_status)
    mcp.tool()(oref_sample)
    mcp.tool()(oref_live_read_only)
    mcp.tool()(nasa_firms_status)
    mcp.tool()(nasa_firms_sample)
    mcp.tool()(nasa_firms_live_read_only)
    mcp.tool()(rss_status)
    mcp.tool()(rss_sample)
    mcp.tool()(rss_live_read_only)
    mcp.tool()(fred_status)
    mcp.tool()(fred_sample)
    mcp.tool()(fred_live_read_only)
    mcp.tool()(system_health)
    mcp.tool()(execution_venues)
    mcp.tool()(founding_manager_access)
    mcp.tool()(qadam_module_map)
    mcp.tool()(quantum_provider_registry)
    mcp.tool()(secret_registry_status)
    return mcp


if __name__ == "__main__":
    server = build_server()
    if server is None:
        raise SystemExit("FastMCP is not installed yet. Install project dependencies first.")
    server.run()
