"""Shared system-state builders for health, tools, and cockpit contracts."""

from __future__ import annotations

from collections import Counter
from typing import Any

from orchestrator.adapters import (
    fred_adapter_status,
    gdelt_adapter_status,
    nasa_firms_adapter_status,
    oref_adapter_status,
    rss_adapter_status,
)
from orchestrator.agent_registry import agent_registry_summary
from orchestrator.agent_runtime import agent_runtime_summary
from orchestrator.broker_reconciliation import broker_reconciliation_summary
from orchestrator.chroma_store import knowledge_graph_health
from orchestrator.config import Settings
from orchestrator.execution import execution_registry
from orchestrator.execution_policy import execution_policy_summary
from orchestrator.governance import GovernanceStore
from orchestrator.heartbeat import registry_heartbeats
from orchestrator.ingestion import ingestion_spine_summary
from orchestrator.intelligence import shadow_intelligence_summary
from orchestrator.local_store import local_store_health
from orchestrator.paper_submit_receipt import paper_submit_receipt_summary
from orchestrator.quantum import quantum_providers
from orchestrator.resource_registry import resource_registry_summary
from orchestrator.risk_agent import risk_agent_summary
from orchestrator.secrets import validate_secret_file
from orchestrator.signal_integrity import signal_integrity_summary
from orchestrator.source_health import source_heartbeat_summary
from orchestrator.staged_paper_order import staged_paper_order_summary
from orchestrator.telegram_comms import telegram_status
from orchestrator.world_model import world_model_summary
from world_monitor.source_registry import EXPECTED_SOURCE_COUNT, SOURCE_SPECS, unresolved_sources


def founding_fund_managers(settings: Settings | None = None) -> dict[str, object]:
    settings = settings or Settings.from_env()
    return {
        "allowlist_emails": list(settings.fund_manager_allowlist),
        "pending_names": list(settings.pending_fund_managers),
        "access_model": "allowlist",
        "login_surface": "qadam.trade",
    }


def _service_status(storage_health: dict[str, Any], key: str, fallback: str) -> str:
    for service in storage_health["services"]:
        if service["key"] == key:
            return "registered" if service["reachable"] else fallback
    return fallback


def module_map(storage_health: dict[str, Any] | None = None, settings: Settings | None = None) -> list[dict[str, str]]:
    storage_health = storage_health or local_store_health()
    settings = settings or Settings.from_env()
    telegram = telegram_status(settings)
    return [
        {"key": "coo", "label": "COO", "owner": "Python Orchestrator", "status": "registered"},
        {"key": "research_analyst", "label": "Research Analyst", "owner": "Local LLM", "status": "pending"},
        {"key": "strategy_lead", "label": "Strategy Lead", "owner": "Frontier LLM", "status": "pending"},
        {"key": "head_of_quant", "label": "Head of Quant", "owner": "Quantum Compute", "status": "registered"},
        {
            "key": "event_log",
            "label": "Event Log",
            "owner": "Postgres/Timescale",
            "status": _service_status(storage_health, "postgres", "jsonl_fallback"),
        },
        {
            "key": "knowledge_graph",
            "label": "Knowledge Graph",
            "owner": "ChromaDB",
            "status": "registered" if knowledge_graph_health().get("status") == "ok" else _service_status(storage_health, "chroma", "not_running"),
        },
        {"key": "execution_registry", "label": "Execution Registry", "owner": "Risk Agent", "status": "disabled"},
        {"key": "resource_registry", "label": "Resource Registry", "owner": "Reference Provenance", "status": "registered"},
        {"key": "world_model", "label": "World-Model Lens", "owner": "Private Corpus", "status": "foundational_prior"},
        {"key": "agent_os", "label": "Agent OS", "owner": "Manifest Registry", "status": "manifest_ready"},
        {"key": "agent_runtime", "label": "Agent Runtime", "owner": "Permission Gate", "status": "enforced"},
        {"key": "shadow_intelligence", "label": "Shadow Intelligence", "owner": "Research Analyst", "status": "shadow_ready"},
        {"key": "signal_integrity_gate", "label": "Signal Integrity Gate", "owner": "Signal Auditor", "status": "shadow_ready"},
        {"key": "risk_agent", "label": "Risk Agent", "owner": "Policy Router", "status": "read_only_ready"},
        {"key": "execution_policy", "label": "Execution Policy", "owner": "Kill Switches", "status": "read_only_ready"},
        {"key": "staged_order_contract", "label": "Staged Order Contract", "owner": "Paper Order Gate", "status": "read_only_ready"},
        {"key": "broker_reconciliation", "label": "Broker Reconciliation", "owner": "Paper Order Gate", "status": "read_only_ready"},
        {"key": "paper_submit_receipt", "label": "Paper Submit Receipt", "owner": "Paper Order Gate", "status": "dry_run"},
        {"key": "governance_forum", "label": "Governance Forum", "owner": "Fund Managers", "status": "local"},
        {"key": "telegram_bot", "label": "Telegram Bot", "owner": "Fund Manager Interface", "status": str(telegram.get("status", "disabled"))},
        {
            "key": "live_bridge",
            "label": "Secure Live Bridge",
            "owner": "qadam.trade API",
            "status": "read_only_ready" if settings.live_bridge_enabled else "disabled",
        },
        {"key": "ingestion_spine", "label": "Test Ingestion Spine", "owner": "World Monitor Adapters", "status": "test_data_ready"},
        {"key": "gdelt_adapter", "label": "GDELT Adapter", "owner": "Conflict Pipeline", "status": "sample_ready"},
        {"key": "oref_adapter", "label": "Oref Adapter", "owner": "Conflict Pipeline", "status": "sample_ready"},
        {"key": "nasa_firms_adapter", "label": "NASA FIRMS Adapter", "owner": "Physical Pipeline", "status": "credential_gated"},
        {"key": "fred_adapter", "label": "FRED Adapter", "owner": "Macro Pipeline", "status": "sample_ready"},
        {"key": "rss_adapter", "label": "RSS Adapter", "owner": "Narrative Pipeline", "status": "sample_ready"},
        {"key": "cockpit", "label": "Cockpit", "owner": "qadam.trade", "status": "shell"},
    ]


def build_system_health(
    settings: Settings | None = None,
    *,
    event_log_health: dict[str, Any] | None = None,
) -> dict[str, Any]:
    settings = settings or Settings.from_env()
    pipeline_counts = Counter(source.pipeline for source in SOURCE_SPECS)
    venues = execution_registry()
    storage_health = local_store_health(settings)
    knowledge_health = knowledge_graph_health(settings)
    governance_health = GovernanceStore(settings=settings).health()
    agent_health = agent_registry_summary()
    runtime_health = agent_runtime_summary(settings)
    event_status = (event_log_health or {}).get("status", "not_started")
    system_status = "ok"
    if (
        event_status == "degraded"
        or storage_health["status"] == "error"
        or governance_health["status"] == "degraded"
        or agent_health["status"] == "error"
        or runtime_health["status"] == "error"
    ):
        system_status = "error"
    elif storage_health["status"] == "degraded":
        system_status = "degraded"
    return {
        "ok": system_status == "ok",
        "status": system_status,
        "env": settings.env,
        "mode": settings.mode,
        "trial_balance_gbp": settings.trial_balance_gbp,
        "local_first": True,
        "source_count": len(SOURCE_SPECS),
        "expected_source_count": EXPECTED_SOURCE_COUNT,
        "pipeline_counts": dict(sorted(pipeline_counts.items())),
        "unresolved_sources": [source.key for source in unresolved_sources()],
        "heartbeats": [heartbeat.__dict__ for heartbeat in registry_heartbeats()],
        "fund_managers": founding_fund_managers(settings),
        "modules": module_map(storage_health, settings),
        "local_stores": storage_health,
        "knowledge_graph": knowledge_health,
        "resource_registry": resource_registry_summary(),
        "world_model": world_model_summary(),
        "agent_os": agent_health,
        "agent_runtime": runtime_health,
        "shadow_intelligence": shadow_intelligence_summary(settings),
        "signal_integrity": signal_integrity_summary(settings),
        "risk_agent": risk_agent_summary(settings),
        "execution_policy": execution_policy_summary(settings),
        "staged_paper_order": staged_paper_order_summary(settings),
        "broker_reconciliation": broker_reconciliation_summary(settings),
        "paper_submit_receipt": paper_submit_receipt_summary(settings),
        "governance_forum": governance_health,
        "telegram_communications": telegram_status(settings),
        "ingestion_spine": ingestion_spine_summary(settings),
        "source_heartbeat": source_heartbeat_summary(settings),
        "adapters": {
            "gdelt": gdelt_adapter_status(settings),
            "oref": oref_adapter_status(settings),
            "nasa_firms": nasa_firms_adapter_status(settings),
            "fred": fred_adapter_status(settings),
            "rss": rss_adapter_status(settings),
        },
        "secret_file": validate_secret_file(settings.secrets_file),
        "quantum_providers": quantum_providers(settings),
        "event_log": event_log_health or {"status": "not_started", "backend": "local_jsonl"},
        "execution_venues": venues,
        "execution_summary": {
            "total": len(venues),
            "write_enabled": 0,
            "first_release_allowed": sum(1 for venue in venues if venue["first_release_allowed"]),
            "live_blocked": [venue["key"] for venue in venues if venue["mode"] == "live_blocked"],
        },
    }
