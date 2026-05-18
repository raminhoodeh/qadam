"""Public-safe cockpit status contract.

The live qadam.trade cockpit starts as a static site, so this module exports a
sanitized snapshot that can be served without exposing the local MacBook, raw
credentials, shell access, or broker authority.
"""

from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from orchestrator.config import Settings
from orchestrator.event_log import EventLog
from orchestrator.execution import execution_registry
from orchestrator.governance import GovernanceStore
from orchestrator.intelligence import (
    LocalResearchAssessmentStore,
    ShadowSignalStore,
    read_research_shadow_triage_queue,
    shadow_intelligence_summary,
)
from orchestrator.live_bridge import live_bridge_contract, write_status_signature
from orchestrator.paper_account import PaperAccountMirrorStore, paper_account_summary
from orchestrator.source_health import SourceHeartbeatStore, build_data_environment_map
from orchestrator.system_state import build_system_health
from orchestrator.telegram_comms import telegram_status
from orchestrator.trade_intent import TradeIntentStore, trade_intent_summary
from orchestrator.tradingview_alerts import (
    TradingViewAlertStore,
    tradingview_alert_summary,
)
from orchestrator.world_model import world_model_claims, world_model_summary

COCKPIT_STATUS_SCHEMA_VERSION = 1
COCKPIT_STATUS_FILENAME = "cockpit-status.json"

PROHIBITED_KEYS = {
    "access_token",
    "allowlist_emails",
    "api_key",
    "authorization",
    "bearer",
    "bot_token",
    "bot_username",
    "chat_id",
    "chat_ids",
    "configured_secrets",
    "email",
    "handle",
    "member_handles",
    "missing_secrets",
    "password",
    "path",
    "private_key",
    "raw_ref",
    "raw_payload",
    "refresh_token",
    "secret_file",
    "secrets_file",
    "telegram_bot_token",
    "telegram_default_chat_id",
    "telegram_payload",
    "token",
    "webhook_secret",
}

PROHIBITED_VALUE_PATTERNS = (
    re.compile(r"[A-Z0-9._%+\-]+@[A-Z0-9.\-]+\.[A-Z]{2,}", re.IGNORECASE),
    re.compile(r"sk-[A-Za-z0-9_\-]{20,}"),
    re.compile(r"ghp_[A-Za-z0-9_]{20,}"),
    re.compile(r"vcp_[A-Za-z0-9_]{20,}"),
    re.compile(r"AIza[0-9A-Za-z_\-]{20,}"),
    re.compile(r"sb_secret_[0-9A-Za-z_\-]{12,}"),
    re.compile(r"PVZ[0-9A-Za-z_\-]{20,}"),
    re.compile(r"\d{6,}:[A-Za-z0-9_\-]{20,}"),
    re.compile(r"@[A-Za-z0-9_]{5,}"),
)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _dashboard_status(raw_status: str) -> str:
    if raw_status in {
        "registered",
        "manifest_ready",
        "enforced",
        "shadow_ready",
        "test_data_ready",
        "sample_ready",
        "live_optional",
        "read_only_ready",
        "ok",
        "dry_run",
        "shell",
    }:
        return "online"
    if raw_status in {"pending", "not_started"}:
        return "pending"
    if raw_status in {"disabled", "live_blocked", "blocked_foundation_phase", "blocked_first_release"}:
        return "blocked"
    if raw_status in {"jsonl_fallback", "local", "local_bridge_required", "foundational_prior"}:
        return "local_only"
    if raw_status in {"credential_gated", "unavailable_missing_credentials", "not_running", "degraded"}:
        return "degraded"
    if raw_status in {"deferred", "ready_to_build", "ready_to_port", "fallback_only", "derived"}:
        return "pending"
    return "pending"


def _module_authority(module_key: str, raw_status: str) -> str:
    if module_key in {"execution_registry", "risk_agent", "trade_layer"}:
        return "write_blocked"
    if module_key == "telegram_bot":
        return "notify_only"
    if module_key == "live_bridge":
        return "read_only"
    if module_key in {"research_analyst", "strategy_lead", "head_of_quant", "shadow_intelligence"}:
        return "non_executable"
    if raw_status in {"disabled", "live_blocked"}:
        return "blocked"
    return "read_only"


def _module_process(module_key: str, raw_status: str) -> str:
    processes = {
        "coo": "supervising local modules",
        "event_log": "recording local audit trail",
        "knowledge_graph": "holding local memory shell",
        "research_analyst": "waiting for local LLM readiness",
        "strategy_lead": "waiting for frontier model probe",
        "head_of_quant": "deferred weekly oracle",
        "execution_registry": "execution disabled in foundation mode",
        "agent_os": "manifest permissions available",
        "agent_runtime": "broker-write tools blocked",
        "shadow_intelligence": "shadow-only review packets available",
        "telegram_bot": "outbound dry-run member communications",
        "live_bridge": "serving authenticated public-safe status snapshots",
        "cockpit": "static live shell frozen",
    }
    return processes.get(module_key, raw_status.replace("_", " "))


def _build_modules(health: dict[str, Any], generated_at: str) -> list[dict[str, Any]]:
    modules: list[dict[str, Any]] = []
    for module in health.get("modules", []):
        raw_status = str(module.get("status", "pending"))
        module_key = str(module.get("key", "unknown"))
        dashboard_status = _dashboard_status(raw_status)
        modules.append(
            {
                "key": module_key,
                "label": str(module.get("label", module_key)),
                "owner": str(module.get("owner", "unknown")),
                "status": dashboard_status,
                "raw_status": raw_status,
                "last_heartbeat": generated_at,
                "current_process": _module_process(module_key, raw_status),
                "authority": _module_authority(module_key, raw_status),
                "local_only": module_key
                in {
                    "event_log",
                    "knowledge_graph",
                    "governance_forum",
                    "world_model",
                    "ingestion_spine",
                    "telegram_bot",
                    "live_bridge",
                },
            }
        )
    return modules


def _d1_snapshot_contract(generated_at: str) -> dict[str, Any]:
    return {
        "phase": "D1",
        "status": "public_safe_snapshot_ready",
        "generated_at": generated_at,
        "read_only": True,
        "public_safe": True,
        "source_of_truth": "local_qadam_runtime_export",
        "browser_authority": "read_only",
        "local_orchestrator_exposed": False,
        "landing_copy": "landing-page-repo/status/cockpit-status.json",
        "runtime_copy": "data/runtime/cockpit-status.json",
        "sanitizer_rules": [
            "no_tokens",
            "no_secret_names",
            "no_allowlist_emails",
            "no_local_absolute_paths",
            "no_raw_payloads",
            "no_browser_to_broker_authority",
        ],
    }


def _credential_status(source: dict[str, Any]) -> str:
    if source.get("auth") in {"none", "public"}:
        return "not_required"
    if source.get("missing_secrets"):
        return "missing"
    if source.get("configured_secrets"):
        return "configured"
    return "unknown"


def _public_auth_class(source: dict[str, Any]) -> str:
    auth = str(source.get("auth") or "").lower()
    if auth in {"none", "public"}:
        return "public_or_none"
    if any(term in auth for term in ("api key", "bearer", "token", "session", "oauth", "password")):
        return "credential_required"
    if any(term in auth for term in ("browser", "account", "login")):
        return "account_required"
    if "local" in auth:
        return "local_bridge"
    return "review_required"


def _readiness_label(source: dict[str, Any], runtime_status: str) -> str:
    if source.get("promoted_adapter") and runtime_status == "live_optional":
        return "adapter ready"
    if runtime_status == "unavailable_missing_credentials":
        return "credential required"
    if runtime_status == "deferred":
        return "deferred"
    if runtime_status == "local_bridge_required":
        return "local bridge required"
    if runtime_status == "fallback_only":
        return "fallback only"
    if runtime_status == "derived":
        return "derived signal"
    if runtime_status in {"ready_to_build", "ready_to_port"}:
        return runtime_status.replace("_", " ")
    return runtime_status.replace("_", " ")


def _tradingview_watching_row(settings: Settings) -> dict[str, Any]:
    summary = tradingview_alert_summary(settings)
    alert_count = int(summary.get("alert_count", 0) or 0)
    status = "online" if alert_count else "pending"
    return {
        "source_key": "tradingview_paid_alerts",
        "source_name": "TradingView Paid Alerts",
        "pipeline": "market",
        "tier": 2,
        "status": status,
        "raw_status": summary.get("status", "not_initialized"),
        "registry_status": "d7_local_contract",
        "readiness": "observed alert source" if alert_count else "secure receiver pending",
        "promoted_adapter": bool(alert_count),
        "auth_class": "account_required",
        "cadence": "event-driven from paid TradingView alerts",
        "endpoint_count": 0,
        "degraded_reason": None if alert_count else "no alert snapshot yet",
        "trust_score": None,
        "last_heartbeat": summary.get("latest_observed_at"),
        "last_payload_time": summary.get("latest_observed_at"),
        "credential_status": "receiver_pending",
        "latency_ms": None,
        "can_influence_signals": False,
        "influence_boundary": "observed_signal_only_no_execution_path",
    }


def _build_watching(data_map: dict[str, Any], settings: Settings) -> list[dict[str, Any]]:
    watching: list[dict[str, Any]] = []
    for source in data_map.get("sources", []):
        runtime_status = str(source.get("runtime_status", "registered"))
        watching.append(
            {
                "source_key": source.get("source_key"),
                "source_name": source.get("source_name"),
                "pipeline": source.get("pipeline"),
                "tier": source.get("tier"),
                "status": _dashboard_status(runtime_status),
                "raw_status": runtime_status,
                "registry_status": source.get("registry_status"),
                "readiness": _readiness_label(source, runtime_status),
                "promoted_adapter": bool(source.get("promoted_adapter")),
                "auth_class": _public_auth_class(source),
                "cadence": source.get("cadence"),
                "endpoint_count": source.get("endpoint_count"),
                "degraded_reason": source.get("degraded_reason"),
                "trust_score": source.get("trust_score"),
                "last_heartbeat": source.get("checked_at"),
                "last_payload_time": None,
                "credential_status": _credential_status(source),
                "latency_ms": None,
                "can_influence_signals": False,
                "influence_boundary": "blocked_until_signal_integrity_gate",
            }
        )
    watching.append(_tradingview_watching_row(settings))
    return watching


def _build_source_pipeline_summary(watching: list[dict[str, Any]]) -> list[dict[str, Any]]:
    pipelines: dict[str, dict[str, Any]] = {}
    for source in watching:
        pipeline = str(source.get("pipeline") or "unknown")
        current = pipelines.setdefault(
            pipeline,
            {
                "pipeline": pipeline,
                "source_count": 0,
                "online_count": 0,
                "degraded_count": 0,
                "pending_count": 0,
                "local_only_count": 0,
                "missing_credential_count": 0,
                "adapter_ready_count": 0,
            },
        )
        current["source_count"] += 1
        if source.get("status") == "online":
            current["online_count"] += 1
        elif source.get("status") == "degraded":
            current["degraded_count"] += 1
        elif source.get("status") == "pending":
            current["pending_count"] += 1
        elif source.get("status") == "local_only":
            current["local_only_count"] += 1
        if source.get("credential_status") == "missing":
            current["missing_credential_count"] += 1
        if source.get("promoted_adapter"):
            current["adapter_ready_count"] += 1
    return [pipelines[key] for key in sorted(pipelines)]


def _build_source_heartbeat_history(settings: Settings) -> list[dict[str, Any]]:
    store = SourceHeartbeatStore(settings=settings)
    try:
        runs = store.read_runs()[-5:]
    except Exception:
        return []
    history: list[dict[str, Any]] = []
    for run in runs:
        summary = run.get("summary", {})
        history.append(
            {
                "checked_at": run.get("checked_at"),
                "source_count": summary.get("source_count"),
                "promoted_adapter_count": summary.get("promoted_adapter_count"),
                "deferred_count": summary.get("deferred_count"),
                "missing_credential_source_count": summary.get("missing_credential_source_count"),
                "by_runtime_status": summary.get("by_runtime_status", {}),
                "by_pipeline": summary.get("by_pipeline", {}),
            }
        )
    return history


def _decision_philosophy() -> dict[str, Any]:
    summary = world_model_summary()
    claims = world_model_claims()
    active_lenses = [
        {
            "key": claim.get("key"),
            "claim_type": claim.get("claim_type"),
            "claim": claim.get("claim"),
            "mechanism": claim.get("mechanism"),
            "actors": claim.get("actors", []),
            "observable_signatures": claim.get("observable_signatures", []),
            "live_sources_to_check": claim.get("live_sources_to_check", []),
            "market_channels": claim.get("market_channels", []),
            "corroboration_status": claim.get("corroboration_status"),
            "evidence_boundary": claim.get("evidence_boundary"),
        }
        for claim in claims
    ]
    return {
        "status": summary.get("status", "ok"),
        "corpus": "how-the-world-works",
        "corpus_file_count": summary.get("corpus_file_count", 0),
        "claim_count": summary.get("claim_count", 0),
        "foundational_prior_count": summary.get("foundational_prior_count", 0),
        "role": "private_worldview_prior",
        "trading_philosophy": (
            "Qadam starts from a power-map worldview: energy, security, money, institutional "
            "incentives, narrative control, and hidden coordination shape what markets price late. "
            "The worldview powers questions and scenario generation, but live evidence, the Akber "
            "filter, Signal Integrity Gate, and Risk Agent decide whether anything can move toward a trade."
        ),
        "decision_chain": [
            "private worldview prior",
            "observable signatures",
            "live-source corroboration",
            "Akber 6-stage filter",
            "Signal Integrity Gate",
            "Risk Agent",
            "paper trade or postmortem",
        ],
        "active_lenses": active_lenses,
        "default_decision_context": [
            "power hierarchy",
            "narrative asymmetry",
            "institutional incentive",
            "US-China grand-bargain scenario",
            "hidden coordination risk",
        ],
        "boundary": summary.get(
            "evidence_boundary",
            "World-model claims are private priors, not factual evidence or trade triggers.",
        ),
    }


def _event_summary(entry: Any) -> str:
    event_type = getattr(entry, "event_type", "event")
    component = getattr(entry, "component", "system")
    severity = getattr(entry, "severity", "info")
    return f"{component}: {event_type} ({severity})"


def _build_process_console(settings: Settings, generated_at: str) -> list[dict[str, str]]:
    event_log = EventLog(echo=False)
    try:
        entries = event_log.read_entries()[-8:]
    except Exception:
        entries = ()
    if entries:
        return [
            {
                "timestamp": entry.created_at,
                "component": entry.component,
                "severity": entry.severity,
                "message": _event_summary(entry),
            }
            for entry in entries
        ]
    return [
        {
            "timestamp": generated_at,
            "component": "cockpit",
            "severity": "info",
            "message": "cockpit: static shell frozen; waiting for local status snapshots",
        },
        {
            "timestamp": generated_at,
            "component": "execution",
            "severity": "warning",
            "message": f"execution: paper mode only; live capital disabled for GBP {settings.trial_balance_gbp} trial",
        },
    ]


def _safe_evidence_packet(signal: dict[str, Any]) -> dict[str, Any]:
    trail = signal.get("evidence_trail", {})
    items = trail.get("evidence_items", []) if isinstance(trail, dict) else []
    safe_items: list[dict[str, Any]] = []
    for item in items:
        if not isinstance(item, dict):
            continue
        safe_items.append(
            {
                "evidence_id": item.get("evidence_id"),
                "source": item.get("source"),
                "event_type": item.get("event_type"),
                "summary": item.get("summary"),
                "trust_score": item.get("trust_score"),
                "observed_at": item.get("observed_at"),
            }
        )
    return {
        "signal_id": signal.get("signal_id"),
        "trail_id": trail.get("trail_id") if isinstance(trail, dict) else None,
        "source_count": trail.get("source_count") if isinstance(trail, dict) else 0,
        "sources": [
            str(item.get("source"))
            for item in safe_items
            if isinstance(item.get("source"), str)
        ],
        "items": safe_items,
        "min_trust_score": trail.get("min_trust_score") if isinstance(trail, dict) else None,
        "average_trust_score": trail.get("average_trust_score") if isinstance(trail, dict) else None,
        "missing_correlations": trail.get("missing_correlations", []) if isinstance(trail, dict) else [],
        "created_at": trail.get("created_at") if isinstance(trail, dict) else None,
    }


def _safe_shadow_packets(settings: Settings) -> list[dict[str, Any]]:
    try:
        packets = list(read_research_shadow_triage_queue(settings))[-5:]
    except Exception:
        packets = []
    return [
        {
            "packet_id": packet.get("packet_id"),
            "agent_key": packet.get("agent_key"),
            "status": packet.get("status"),
            "summary": packet.get("summary"),
            "uncertainty": packet.get("uncertainty"),
            "source_event_refs": packet.get("source_event_refs", []),
            "created_at": packet.get("created_at"),
            "boundary": packet.get("boundary"),
        }
        for packet in packets
    ]


def _build_cognition(settings: Settings) -> dict[str, Any]:
    summary = shadow_intelligence_summary(settings)
    store = ShadowSignalStore(settings=settings)
    local_research_store = LocalResearchAssessmentStore(settings=settings)
    try:
        signals = list(store.read())[-5:]
    except Exception:
        signals = []
    try:
        local_assessments = list(local_research_store.read())[-3:]
    except Exception:
        local_assessments = []

    evidence_packets = [_safe_evidence_packet(signal) for signal in signals]
    hypotheses = [
        {
            "signal_id": signal.get("signal_id"),
            "title": signal.get("title"),
            "instrument_focus": signal.get("instrument_focus"),
            "thesis": signal.get("thesis"),
            "confidence": signal.get("confidence"),
            "status": signal.get("status", "shadow_only"),
            "execution_allowed": bool(signal.get("execution_allowed")),
            "blocked_reason": "shadow_only_no_signal_integrity_gate",
            "invalidation": signal.get("invalidation"),
            "generated_by": signal.get("generated_by"),
            "evidence_packet_id": signal.get("signal_id"),
            "evidence_source_count": evidence_packets[index].get("source_count", 0)
            if index < len(evidence_packets)
            else 0,
            "missing_correlations": evidence_packets[index].get("missing_correlations", [])
            if index < len(evidence_packets)
            else [],
            "created_at": signal.get("created_at"),
        }
        for index, signal in enumerate(signals)
    ]

    current_focus = []
    if hypotheses:
        current_focus.append("reviewing shadow-only hypotheses")
    if local_assessments:
        current_focus.append(
            f"local Research Analyst focus: {local_assessments[-1].get('watch_focus', 'shadow review')}"
        )
    if not current_focus:
        current_focus.append("waiting for source heartbeat and shadow triage inputs")

    provider_status = summary.get("provider_status", {})
    latest_local_assessment = local_assessments[-1] if local_assessments else {}
    local_llm_status = provider_status.get("local_llm", {})
    research_provider = latest_local_assessment.get("provider") or local_llm_status.get("provider", "lm_studio")
    research_model = latest_local_assessment.get("model") or local_llm_status.get("model")
    research_status = local_llm_status.get("probe_status", "not_called")
    if latest_local_assessment:
        research_status = "ok" if latest_local_assessment.get("raw_response_status") == "ok" else "shadow_only"
    model_activity = [
        {
            "role": "Research Analyst",
            "provider": research_provider,
            "status": research_status,
            "model": research_model,
            "authority": "non_executable",
            "current_task": "local shadow assessment" if local_assessments else "shadow triage and local compression",
        },
        {
            "role": "Strategy Lead",
            "provider": "gemini",
            "status": provider_status.get("frontier_llm", {}).get("probe_status", "not_called"),
            "model": "configured_frontier_model",
            "authority": "non_executable",
            "current_task": "scenario challenge after local triage",
        },
        {
            "role": "Head of Quant",
            "provider": "quantum_or_classical",
            "status": "deferred",
            "model": "weekly_oracle",
            "authority": "non_executable",
            "current_task": "no real-time role",
        },
    ]
    return {
        "status": summary.get("status", "shadow_ready"),
        "current_focus": current_focus,
        "shadow_packets": _safe_shadow_packets(settings),
        "local_research_assessments": [
            {
                "assessment_id": assessment.get("assessment_id"),
                "status": assessment.get("status", "shadow_only"),
                "mode": assessment.get("mode"),
                "provider": assessment.get("provider"),
                "model": assessment.get("model"),
                "summary": assessment.get("summary"),
                "watch_focus": assessment.get("watch_focus"),
                "anomalies": assessment.get("anomalies", []),
                "missing_correlations": assessment.get("missing_correlations", []),
                "next_questions": assessment.get("next_questions", []),
                "escalation_recommendation": assessment.get("escalation_recommendation"),
                "confidence": assessment.get("confidence"),
                "execution_allowed": bool(assessment.get("execution_allowed")),
                "paper_order_allowed": bool(assessment.get("paper_order_allowed")),
                "created_at": assessment.get("created_at"),
            }
            for assessment in local_assessments
        ],
        "hypotheses": hypotheses,
        "evidence_packets": evidence_packets,
        "model_activity": model_activity,
        "analysis_timeline": [
            "source observation",
            "research analyst shadow packet",
            "local research assessment",
            "deterministic triage",
            "strategy review pending",
            "signal integrity gate blocked",
            "trade layer not reached",
        ],
        "blocked_reasons": [
            "shadow_only_no_signal_integrity_gate",
            "no_risk_agent_approval",
            "no_trade_candidate_store",
            "no_broker_write_authority",
        ],
        "boundary": "Cognition is shadow-only until Signal Integrity Gate and Risk Agent exist.",
    }


def _safe_paper_position(position: Any) -> dict[str, Any]:
    return {
        "position_id": position.position_id,
        "status": position.status,
        "instrument": position.instrument,
        "direction": position.direction,
        "quantity": position.quantity,
        "entry_price": position.entry_price,
        "current_price": position.current_price,
        "unrealized_pnl_gbp": position.unrealized_pnl_gbp,
        "risk_size_gbp": position.risk_size_gbp,
        "opened_at": position.opened_at,
        "invalidation": position.invalidation,
        "source_intent_id": position.source_intent_id,
        "boundary": position.boundary,
    }


def _safe_closed_trade(trade: Any) -> dict[str, Any]:
    return {
        "trade_id": trade.trade_id,
        "instrument": trade.instrument,
        "direction": trade.direction,
        "entry_price": trade.entry_price,
        "exit_price": trade.exit_price,
        "realized_pnl_gbp": trade.realized_pnl_gbp,
        "r_multiple": trade.r_multiple,
        "close_reason": trade.close_reason,
        "opened_at": trade.opened_at,
        "closed_at": trade.closed_at,
        "postmortem_status": trade.postmortem_status,
        "source_intent_id": trade.source_intent_id,
        "boundary": trade.boundary,
    }


def _safe_tradingview_alert(alert: Any) -> dict[str, Any]:
    return {
        "alert_id": alert.alert_id,
        "status": alert.status,
        "source": "tradingview_alerts",
        "source_type": "tradingview_paid_alert",
        "instrument": alert.symbol,
        "symbol": alert.symbol,
        "timeframe": alert.timeframe,
        "setup_type": alert.setup_type,
        "direction": alert.direction,
        "trigger": alert.trigger,
        "price": alert.price,
        "indicator_state": alert.indicator_state,
        "chart_context": alert.chart_context,
        "received_at": alert.received_at,
        "observed_at": alert.observed_at,
        "execution_allowed": alert.execution_allowed,
        "paper_order_allowed": alert.paper_order_allowed,
        "trade_candidate_created": alert.trade_candidate_created,
        "boundary": alert.boundary,
    }


def _tradingview_alerts(settings: Settings) -> dict[str, Any]:
    summary = tradingview_alert_summary(settings)
    try:
        alerts = TradingViewAlertStore(settings=settings).read_alerts(limit=10)
        store_status = summary.get("status", "ok")
    except Exception:  # noqa: BLE001 - public status should degrade safely
        alerts = ()
        store_status = "degraded"
        summary = {
            "status": "degraded",
            "alert_count": 0,
            "error": str(exc),
            "receiver_status": "local_contract_only",
            "duplicate_protection": "dedupe_key_sha256",
            "boundary": "TradingView alert store could not be read.",
        }
    return {
        "status": store_status,
        "receiver_status": summary.get("receiver_status", "local_contract_only"),
        "duplicate_protection": summary.get("duplicate_protection", "dedupe_key_sha256"),
        "alert_count": summary.get("alert_count", 0),
        "latest_observed_at": summary.get("latest_observed_at"),
        "execution_allowed_count": summary.get("execution_allowed_count", 0),
        "paper_order_allowed_count": summary.get("paper_order_allowed_count", 0),
        "trade_candidate_created_count": summary.get("trade_candidate_created_count", 0),
        "observed_signals": [_safe_tradingview_alert(alert) for alert in alerts],
        "boundary": summary.get(
            "boundary",
            "TradingView alerts are observed signals only. D7 has no execution route.",
        ),
    }


def _fund_manager_notes(settings: Settings) -> dict[str, Any]:
    store = GovernanceStore(settings=settings)
    try:
        comments = tuple(reversed(store.read_comments(limit=10)))
        health = store.health()
        status = health.get("status", "ok")
    except Exception as exc:  # noqa: BLE001 - public status should degrade safely
        comments = ()
        health = {
            "status": "degraded",
            "schema_version": 1,
            "comment_count": 0,
            "suggestion_count": 0,
            "accepted_count": 0,
            "rejected_count": 0,
            "implemented_count": 0,
            "event_log_export_count": 0,
            "allowed_target_types": [],
            "allowed_statuses": [],
            "visibility": "founding_fund_managers",
            "error": str(exc),
        }
        status = "degraded"
    return {
        "status": status,
        "schema_version": health.get("schema_version", 1),
        "comment_count": health.get("comment_count", 0),
        "suggestion_count": health.get("suggestion_count", 0),
        "accepted_count": health.get("accepted_count", 0),
        "rejected_count": health.get("rejected_count", 0),
        "implemented_count": health.get("implemented_count", 0),
        "event_log_export_count": health.get("event_log_export_count", 0),
        "allowed_target_types": health.get("allowed_target_types", []),
        "allowed_statuses": health.get("allowed_statuses", ["suggestion", "accepted", "rejected", "implemented"]),
        "visibility": "founding_fund_managers",
        "supabase_table": "fund_manager_comments",
        "browser_write_scope": "comments_only",
        "local_event_log_export": "accepted_or_implemented_only",
        "recent_comments": [
            {
                "comment_id": comment.comment_id,
                "author_label": "founding_fund_manager",
                "target_type": comment.target_type,
                "target_key": comment.target_key,
                "body": comment.body,
                "tags": list(comment.tags),
                "status": "suggestion" if comment.status == "open" else comment.status,
                "visibility": comment.visibility,
                "created_at": comment.created_at,
            }
            for comment in comments
        ],
        "boundary": (
            "Fund Manager comments are governance notes only. They cannot approve trades, "
            "place orders, or expose local secrets."
        ),
    }


def _communications(settings: Settings) -> dict[str, Any]:
    try:
        telegram = telegram_status(settings)
    except Exception as exc:  # noqa: BLE001 - public status should degrade safely
        telegram = {
            "status": "degraded",
            "schema_version": 1,
            "mode": "dry_run",
            "send_gate": "disabled",
            "bot_configured": False,
            "bot_username_configured": False,
            "default_chat_configured": False,
            "member_count": 0,
            "verified_member_count": 0,
            "pending_member_count": 0,
            "failed_member_count": 0,
            "pending_queue_count": 0,
            "sent_count": 0,
            "failed_count": 0,
            "retried_count": 0,
            "suppressed_count": 0,
            "last_sent_time": None,
            "last_failure_reason": "telegram communications status unavailable",
            "last_digest_title": "",
            "active_message_classes": [],
            "dry_run_message_count": 0,
            "recent_messages": [],
            "boundary": (
                "Telegram is outbound-only member communication. It cannot place, approve, "
                "reject, modify, close, or resize trades."
            ),
        }
    return {
        "telegram": telegram,
        "boundary": (
            "Communications are notify-only. The browser and Telegram rail cannot create "
            "broker actions or hidden approvals."
        ),
    }


def _capital(settings: Settings) -> dict[str, Any]:
    store = PaperAccountMirrorStore(settings=settings)
    summary = paper_account_summary(settings)
    latest = store.latest_snapshot()
    positions = [_safe_paper_position(position) for position in store.read_positions()]
    closed_trades = [_safe_closed_trade(trade) for trade in store.read_closed_trades()]
    postmortems_due = [
        trade for trade in closed_trades if trade.get("postmortem_status") == "postmortem_due"
    ]
    postmortems_complete = [
        trade for trade in closed_trades if trade.get("postmortem_status") == "postmortem_complete"
    ]
    equity_curve = [
        {
            "observed_at": snapshot.observed_at,
            "equity_gbp": snapshot.equity_gbp,
            "drawdown_pct": snapshot.drawdown_pct,
        }
        for snapshot in store.read_snapshots(limit=20)
    ]
    if latest is None:
        return {
            "mirror_status": summary["status"],
            "starting_balance_gbp": settings.trial_balance_gbp,
            "current_balance_gbp": settings.trial_balance_gbp,
            "cash_gbp": settings.trial_balance_gbp,
            "equity_gbp": settings.trial_balance_gbp,
            "realized_pnl_gbp": 0,
            "unrealized_pnl_gbp": 0,
            "drawdown_pct": 0,
            "max_drawdown_pct": 0,
            "live_capital_enabled": False,
            "write_authority": False,
            "connection_status": "not_initialized",
            "timeline_status": "not_initialized",
            "maturity_closed_trade_target": 100,
            "maturity_closed_trade_count": 0,
            "open_positions": [],
            "closed_trades": [],
            "postmortems_due": [],
            "postmortems_complete": [],
            "equity_curve": [],
            "boundary": summary["boundary"],
        }
    return {
        "mirror_status": summary["status"],
        "account_scope": latest.account_scope,
        "broker": latest.broker,
        "starting_balance_gbp": latest.starting_balance_gbp,
        "current_balance_gbp": latest.current_balance_gbp,
        "cash_gbp": latest.cash_gbp,
        "equity_gbp": latest.equity_gbp,
        "peak_equity_gbp": latest.peak_equity_gbp,
        "realized_pnl_gbp": latest.realized_pnl_gbp,
        "unrealized_pnl_gbp": latest.unrealized_pnl_gbp,
        "drawdown_pct": latest.drawdown_pct,
        "max_drawdown_pct": latest.max_drawdown_pct,
        "live_capital_enabled": latest.live_capital_enabled,
        "write_authority": latest.write_authority,
        "connection_status": latest.connection_status,
        "timeline_status": latest.timeline_status,
        "observed_at": latest.observed_at,
        "maturity_closed_trade_target": latest.maturity_closed_trade_target,
        "maturity_closed_trade_count": latest.maturity_closed_trade_count,
        "open_position_count": len(positions),
        "closed_trade_count": len(closed_trades),
        "postmortem_due_count": len(postmortems_due),
        "postmortem_complete_count": len(postmortems_complete),
        "open_positions": positions,
        "closed_trades": closed_trades,
        "postmortems_due": postmortems_due,
        "postmortems_complete": postmortems_complete,
        "equity_curve": equity_curve,
        "boundary": latest.boundary,
    }


def _safe_trade_item(intent: Any) -> dict[str, Any]:
    return {
        "intent_id": intent.intent_id,
        "status": intent.status,
        "instrument": intent.instrument,
        "direction": intent.direction,
        "venue": intent.venue,
        "strategy": intent.strategy,
        "catalyst": intent.catalyst,
        "evidence_summary": intent.evidence_summary,
        "probability_estimate": intent.probability_estimate,
        "market_implied_probability": intent.market_implied_probability,
        "price_gap": intent.price_gap,
        "proposed_entry": intent.proposed_entry,
        "invalidation": intent.invalidation,
        "holding_window": intent.holding_window,
        "risk_size_gbp": intent.risk_size_gbp,
        "risk_size_pct": intent.risk_size_pct,
        "risk_state": intent.risk_state,
        "blocked_reason": intent.blocked_reason,
        "execution_allowed": intent.execution_allowed,
        "paper_order_allowed": intent.paper_order_allowed,
        "source_signal_id": intent.source_signal_id,
        "source_type": intent.source_type,
        "akber_filter": intent.akber_filter,
        "risk_checks": intent.risk_checks,
        "tags": list(intent.tags),
        "created_at": intent.created_at,
        "updated_at": intent.updated_at,
        "boundary": intent.boundary,
    }


def _trade_layer(settings: Settings) -> dict[str, Any]:
    try:
        intents = TradeIntentStore(settings=settings).read_intents()
        store_status = "ok"
    except Exception:
        intents = ()
        store_status = "degraded"
    try:
        paper_store = PaperAccountMirrorStore(settings=settings)
        paper_positions = paper_store.read_positions()
        paper_closed_trades = paper_store.read_closed_trades()
    except Exception:
        paper_positions = ()
        paper_closed_trades = ()
    try:
        tradingview_alerts = TradingViewAlertStore(settings=settings).read_alerts(limit=10)
    except Exception:
        tradingview_alerts = ()

    trade_layer: dict[str, Any] = {
        "summary": trade_intent_summary(settings) if store_status == "ok" else {"status": store_status},
        "store_status": store_status,
        "watching": [],
        "candidates": [],
        "blocked": [],
        "staged_orders": [],
        "submitted_orders": [],
        "open_positions": [],
        "closed_trades": [],
        "postmortems_due": [],
        "postmortems_complete": [],
        "boundary": "D5 trade intent is local and non-executing. No broker order path exists.",
    }
    trade_layer["watching"].extend(_safe_tradingview_alert(alert) for alert in tradingview_alerts)
    for intent in intents:
        item = _safe_trade_item(intent)
        if intent.status in {"candidate", "risk_review"}:
            trade_layer["candidates"].append(item)
        elif intent.status == "blocked":
            trade_layer["blocked"].append(item)
        elif intent.status == "staged_paper_order":
            trade_layer["staged_orders"].append(item)
        elif intent.status == "submitted_paper_order":
            trade_layer["submitted_orders"].append(item)
        elif intent.status in {"open_position", "exit_planned"}:
            trade_layer["open_positions"].append(item)
        elif intent.status == "closed_trade":
            trade_layer["closed_trades"].append(item)
        elif intent.status == "postmortem_due":
            trade_layer["postmortems_due"].append(item)
        elif intent.status == "postmortem_complete":
            trade_layer["postmortems_complete"].append(item)
        else:
            trade_layer["watching"].append(item)
    trade_layer["open_positions"].extend(
        _safe_paper_position(position) | {"source": "paper_account_mirror"}
        for position in paper_positions
    )
    trade_layer["closed_trades"].extend(
        _safe_closed_trade(trade) | {"source": "paper_account_mirror"}
        for trade in paper_closed_trades
    )
    trade_layer["postmortems_due"].extend(
        _safe_closed_trade(trade) | {"source": "paper_account_mirror"}
        for trade in paper_closed_trades
        if trade.postmortem_status == "postmortem_due"
    )
    trade_layer["postmortems_complete"].extend(
        _safe_closed_trade(trade) | {"source": "paper_account_mirror"}
        for trade in paper_closed_trades
        if trade.postmortem_status == "postmortem_complete"
    )
    if isinstance(trade_layer["summary"], dict):
        trade_layer["summary"]["observed_signal_count"] = len(trade_layer["watching"])
    return trade_layer


def _forbidden_actions() -> list[dict[str, str]]:
    return [
        {
            "key": "live_capital",
            "status": "blocked",
            "reason": "first_release_paper_mode_only",
        },
        {
            "key": "browser_to_broker",
            "status": "blocked",
            "reason": "no_direct_ui_to_broker_path",
        },
        {
            "key": "llm_to_broker",
            "status": "blocked",
            "reason": "no_llm_to_broker_path",
        },
        {
            "key": "broker_write",
            "status": "blocked",
            "reason": "execution_venues_disabled_until_phase_5_gates",
        },
        {
            "key": "tradingview_alert_execution",
            "status": "blocked",
            "reason": "future_alerts_can_only_write_observed_signal_events",
        },
        {
            "key": "quantum_realtime_trading",
            "status": "blocked",
            "reason": "quantum_is_weekly_oracle_not_execution_engine",
        },
    ]


def build_cockpit_status(settings: Settings | None = None) -> dict[str, Any]:
    settings = settings or Settings.from_env()
    generated_at = _now()
    data_map = build_data_environment_map(settings)
    health = build_system_health(settings, event_log_health=EventLog(echo=False).health())
    watching = _build_watching(data_map, settings)
    payload = {
        "schema_version": COCKPIT_STATUS_SCHEMA_VERSION,
        "generated_at": generated_at,
        "mode": settings.mode,
        "d1_snapshot": _d1_snapshot_contract(generated_at),
        "d0_shell": {
            "status": "frozen",
            "surface": "qadam.trade static Supabase-authenticated shell",
            "routing": ["/login/", "/sign-up/", "/dashboard/"],
            "live_orchestrator_exposed": False,
        },
        "capital": _capital(settings),
        "watching": watching,
        "source_pipeline_summary": _build_source_pipeline_summary(watching),
        "source_heartbeat_history": _build_source_heartbeat_history(settings),
        "modules": _build_modules(health, generated_at),
        "process_console": _build_process_console(settings, generated_at),
        "decision_philosophy": _decision_philosophy(),
        "cognition": _build_cognition(settings),
        "tradingview_alerts": _tradingview_alerts(settings),
        "trade_layer": _trade_layer(settings),
        "communications": _communications(settings),
        "live_bridge": live_bridge_contract(settings, generated_at),
        "forbidden_actions": _forbidden_actions(),
        "fund_manager_notes": _fund_manager_notes(settings),
        "execution_venues": [
            {
                "key": venue["key"],
                "name": venue["name"],
                "mode": venue["mode"],
                "account_scope": venue["account_scope"],
                "read_health": venue["read_health"],
                "write_health": venue["write_health"],
                "kill_switch_status": venue["kill_switch_status"],
                "first_release_allowed": venue["first_release_allowed"],
            }
            for venue in execution_registry()
        ],
        "boundary": "Public-safe read-only snapshot. It cannot trigger trading and contains no secrets.",
    }
    validate_cockpit_status(payload)
    return payload


def _walk_payload(payload: Any, path: str = "$") -> list[str]:
    problems: list[str] = []
    if isinstance(payload, dict):
        for key, value in payload.items():
            if key in PROHIBITED_KEYS:
                problems.append(f"prohibited key at {path}.{key}")
            problems.extend(_walk_payload(value, f"{path}.{key}"))
    elif isinstance(payload, list):
        for index, value in enumerate(payload):
            problems.extend(_walk_payload(value, f"{path}[{index}]"))
    elif isinstance(payload, str):
        for pattern in PROHIBITED_VALUE_PATTERNS:
            if pattern.search(payload):
                problems.append(f"token-like value at {path}")
        if (
            "/Users/" in payload
            or "\\Users\\" in payload
            or "/private/" in payload
            or "/var/folders/" in payload
            or payload.startswith("/tmp/")
        ):
            problems.append(f"local absolute path at {path}")
    return problems


def validate_cockpit_status(payload: dict[str, Any]) -> None:
    required = {
        "schema_version",
        "generated_at",
        "mode",
        "d1_snapshot",
        "d0_shell",
        "capital",
        "watching",
        "modules",
        "process_console",
        "decision_philosophy",
        "cognition",
        "tradingview_alerts",
        "trade_layer",
        "communications",
        "forbidden_actions",
        "fund_manager_notes",
        "live_bridge",
    }
    missing = sorted(required - set(payload))
    if missing:
        raise ValueError(f"cockpit status missing required keys: {missing}")
    if payload["schema_version"] != COCKPIT_STATUS_SCHEMA_VERSION:
        raise ValueError("cockpit status schema version mismatch")
    if payload["mode"] != "paper":
        raise ValueError("cockpit status can only be exported in paper mode")
    d1_snapshot = payload["d1_snapshot"]
    if d1_snapshot.get("phase") != "D1":
        raise ValueError("cockpit status D1 snapshot phase mismatch")
    if d1_snapshot.get("read_only") is not True:
        raise ValueError("cockpit status D1 snapshot must be read-only")
    if d1_snapshot.get("public_safe") is not True:
        raise ValueError("cockpit status D1 snapshot must be public-safe")
    if d1_snapshot.get("browser_authority") != "read_only":
        raise ValueError("browser authority must remain read-only")
    if d1_snapshot.get("local_orchestrator_exposed") is not False:
        raise ValueError("local orchestrator must not be exposed in D1")
    if payload["capital"].get("live_capital_enabled") is not False:
        raise ValueError("cockpit status must keep live capital disabled")
    if payload["d0_shell"].get("status") != "frozen":
        raise ValueError("D0 shell must be frozen before D1 export")
    live_bridge = payload["live_bridge"]
    if live_bridge.get("phase") != "D9":
        raise ValueError("live bridge phase must be D9")
    if live_bridge.get("read_only") is not True:
        raise ValueError("live bridge must be read-only")
    if live_bridge.get("browser_authority") != "read_only":
        raise ValueError("live bridge browser authority must remain read-only")
    if live_bridge.get("write_authority") is not False:
        raise ValueError("live bridge must not have write authority")
    if live_bridge.get("broker_write_route") is not False:
        raise ValueError("live bridge must not expose a broker write route")
    if live_bridge.get("local_orchestrator_exposed") is not False:
        raise ValueError("live bridge must not expose the local orchestrator")

    problems = _walk_payload(payload)
    if problems:
        raise ValueError("cockpit status is not public-safe: " + "; ".join(problems))


def write_cockpit_status(payload: dict[str, Any], path: str | Path | None = None) -> Path:
    validate_cockpit_status(payload)
    settings = Settings.from_env()
    output_path = Path(path or Path(settings.runtime_dir) / COCKPIT_STATUS_FILENAME)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    write_status_signature(payload, output_path)
    return output_path


def export_cockpit_status(
    *,
    settings: Settings | None = None,
    output_path: str | Path | None = None,
    landing_repo_path: str | Path | None = "landing-page-repo",
    copy_to_landing: bool = True,
) -> dict[str, Any]:
    settings = settings or Settings.from_env()
    payload = build_cockpit_status(settings)
    runtime_path = write_cockpit_status(payload, output_path)
    landing_path: Path | None = None
    if copy_to_landing and landing_repo_path:
        repo_path = Path(landing_repo_path)
        if repo_path.exists():
            landing_path = repo_path / "status" / COCKPIT_STATUS_FILENAME
            write_cockpit_status(payload, landing_path)
    return {
        "status": "ok",
        "runtime_path": str(runtime_path),
        "landing_path": str(landing_path) if landing_path else None,
        "runtime_signature_path": str(runtime_path.with_name("cockpit-status.signature.json")),
        "landing_signature_path": str(landing_path.with_name("cockpit-status.signature.json")) if landing_path else None,
        "schema_version": payload["schema_version"],
        "generated_at": payload["generated_at"],
        "module_count": len(payload["modules"]),
        "watching_count": len(payload["watching"]),
        "hypothesis_count": len(payload["cognition"]["hypotheses"]),
        "trade_candidate_count": len(payload["trade_layer"]["candidates"]),
        "forbidden_action_count": len(payload["forbidden_actions"]),
    }
