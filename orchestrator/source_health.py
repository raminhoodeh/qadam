"""Source heartbeat and data-environment map builder."""

from __future__ import annotations

import json
from collections import Counter
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from orchestrator.adapters import (
    fred_adapter_status,
    gdelt_adapter_status,
    nasa_firms_adapter_status,
    oref_adapter_status,
    rss_adapter_status,
)
from orchestrator.config import Settings
from orchestrator.event_log import EventLog
from orchestrator.phase1_live_adapters import PHASE1_LIVE_ADAPTER_KEYS, phase1_live_adapter_status
from orchestrator.secrets import secret_status
from world_monitor.source_registry import (
    EXPECTED_SOURCE_COUNT,
    SOURCE_SPECS,
    SourceSpec,
    source_registry_action_category,
)

SOURCE_HEARTBEAT_SCHEMA_VERSION = 1
DATA_ENVIRONMENT_MAP_SCHEMA_VERSION = 1

PROMOTED_ADAPTER_STATUS = {
    "gdelt": gdelt_adapter_status,
    "oref": oref_adapter_status,
    "nasa_firms": nasa_firms_adapter_status,
    "fred": fred_adapter_status,
    "rss": rss_adapter_status,
    **{
        key: (lambda settings=None, key=key: phase1_live_adapter_status(key, settings))
        for key in PHASE1_LIVE_ADAPTER_KEYS
    },
}

OPTIONAL_SECRET_KEYS = {
    "fred": {"FRED_API_KEY"},
    "oref": {"OREF_PROXY_AUTH"},
}


@dataclass(frozen=True)
class SourceHeartbeat:
    schema_version: int
    source_key: str
    source_name: str
    pipeline: str
    tier: int
    runtime_status: str
    registry_status: str
    promoted_adapter: bool
    credential_bound: bool
    credential_activation_state: str | None
    credential_activation_ready: bool
    trust_score: float | None
    checked_at: str
    cadence: str
    auth: str
    endpoint_count: int
    configured_secrets: tuple[str, ...]
    missing_secrets: tuple[str, ...]
    notes: str
    selection_status: str
    operator_action: str
    action_category: str
    degraded_reason: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class SourceHeartbeatStore:
    def __init__(self, path: str | Path | None = None, settings: Settings | None = None) -> None:
        self.settings = settings or Settings.from_env()
        self.path = Path(path or Path(self.settings.runtime_dir) / "source_heartbeats.jsonl")
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def write_run(self, payload: dict[str, Any]) -> None:
        with self.path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(payload, sort_keys=True) + "\n")

    def read_runs(self) -> tuple[dict[str, Any], ...]:
        if not self.path.exists():
            return ()
        runs: list[dict[str, Any]] = []
        with self.path.open("r", encoding="utf-8") as handle:
            for line_number, line in enumerate(handle, start=1):
                stripped = line.strip()
                if not stripped:
                    continue
                try:
                    runs.append(json.loads(stripped))
                except json.JSONDecodeError as exc:
                    raise ValueError(f"invalid source heartbeat line {line_number} in {self.path}") from exc
        return tuple(runs)

    def health(self) -> dict[str, Any]:
        try:
            runs = self.read_runs()
        except Exception as exc:  # noqa: BLE001 - health should report the failure
            return {"status": "degraded", "path": str(self.path), "error": str(exc)}
        last = runs[-1] if runs else None
        return {
            "status": "ok" if runs else "not_started",
            "path": str(self.path),
            "schema_version": SOURCE_HEARTBEAT_SCHEMA_VERSION,
            "run_count": len(runs),
            "last_checked_at": last.get("checked_at") if last else None,
            "last_source_count": last.get("summary", {}).get("source_count") if last else 0,
        }


def _secret_state(source: SourceSpec, settings: Settings) -> tuple[tuple[str, ...], tuple[str, ...]]:
    if source.selection_status in {"optional_disabled", "not_selected"}:
        return (), ()
    if source.status in {"intentionally_disabled", "needs_adapter", "provider_decision_required"}:
        return (), ()
    configured: list[str] = []
    missing: list[str] = []
    optional = OPTIONAL_SECRET_KEYS.get(source.key, set())
    for key in source.env_vars:
        status = secret_status(key, settings)
        if status.configured:
            configured.append(key)
        elif key not in optional:
            missing.append(key)
    return tuple(configured), tuple(missing)


def _runtime_status(source: SourceSpec, missing_secrets: tuple[str, ...], promoted: bool) -> tuple[str, str | None]:
    if source.status == "derived":
        return "derived", None
    if source.status == "local_bridge":
        return "local_bridge_required", None
    if source.status == "intentionally_disabled":
        return "intentionally_disabled", None
    if source.status == "needs_adapter":
        return "needs_adapter", None
    if source.status == "provider_decision_required":
        return "provider_decision_required", None
    if promoted and missing_secrets:
        return "unavailable_missing_credentials", "missing_credentials"
    if promoted:
        return "live_optional", None
    if source.status in {"needs_clarity", "needs_choice", "needs_new_adapter"}:
        return "deferred", source.status
    if source.status == "fallback":
        return "fallback_only", None
    if missing_secrets:
        return "unavailable_missing_credentials", "missing_credentials"
    if source.status in {"ready_to_port", "ready_to_build"}:
        return source.status, None
    return "registered", None


def build_source_heartbeat(source: SourceSpec, checked_at: str, settings: Settings) -> SourceHeartbeat:
    promoted = source.key in PROMOTED_ADAPTER_STATUS
    configured, missing = _secret_state(source, settings)
    adapter_status = PROMOTED_ADAPTER_STATUS[source.key](settings) if promoted else {}
    if source.key in PHASE1_LIVE_ADAPTER_KEYS:
        binding_state = adapter_status.get("credential_binding") or {}
        activation_state = binding_state.get("activation_state")
        activation_ready = bool(adapter_status.get("activation_ready"))
        if activation_state == "ready_for_live_readonly":
            missing = ()
        elif activation_state == "provider_endpoint_unconfirmed":
            missing = ()
        elif not activation_state and (
            adapter_status.get("credential_configured") or adapter_status.get("mode") == "sample_ready_live_optional"
        ):
            missing = ()
    else:
        binding_state = {}
        activation_state = None
        activation_ready = False
    runtime_status, degraded_reason = _runtime_status(source, missing, promoted)
    if source.key in PHASE1_LIVE_ADAPTER_KEYS and activation_state == "provider_endpoint_unconfirmed":
        runtime_status = "unavailable_provider_endpoint_unconfirmed"
        degraded_reason = "provider_endpoint_unconfirmed"
    return SourceHeartbeat(
        schema_version=SOURCE_HEARTBEAT_SCHEMA_VERSION,
        source_key=source.key,
        source_name=source.name,
        pipeline=source.pipeline,
        tier=source.tier,
        runtime_status=runtime_status,
        registry_status=source.status,
        promoted_adapter=promoted,
        credential_bound=bool(binding_state),
        credential_activation_state=str(activation_state) if activation_state else None,
        credential_activation_ready=activation_ready,
        trust_score=adapter_status.get("trust_score") if promoted else None,
        checked_at=checked_at,
        cadence=source.cadence,
        auth=source.auth,
        endpoint_count=len(source.endpoints),
        configured_secrets=configured,
        missing_secrets=missing,
        notes=source.notes,
        selection_status=source.selection_status,
        operator_action=source.operator_action,
        action_category=source_registry_action_category(source),
        degraded_reason=degraded_reason,
    )


def _summarise(heartbeats: tuple[SourceHeartbeat, ...]) -> dict[str, Any]:
    by_status = Counter(heartbeat.runtime_status for heartbeat in heartbeats)
    by_pipeline = Counter(heartbeat.pipeline for heartbeat in heartbeats)
    by_selection = Counter(heartbeat.selection_status for heartbeat in heartbeats)
    by_action = Counter(heartbeat.action_category for heartbeat in heartbeats)
    missing_credentials = {
        heartbeat.source_key: list(heartbeat.missing_secrets)
        for heartbeat in heartbeats
        if heartbeat.missing_secrets
    }
    return {
        "status": "ok",
        "schema_version": SOURCE_HEARTBEAT_SCHEMA_VERSION,
        "source_count": len(heartbeats),
        "expected_source_count": EXPECTED_SOURCE_COUNT,
        "promoted_adapter_count": sum(1 for heartbeat in heartbeats if heartbeat.promoted_adapter),
        "credential_bound_source_count": sum(1 for heartbeat in heartbeats if heartbeat.credential_bound),
        "credential_bound_activation_ready_count": sum(
            1 for heartbeat in heartbeats if heartbeat.credential_bound and heartbeat.credential_activation_ready
        ),
        "provider_endpoint_unconfirmed_count": sum(
            1
            for heartbeat in heartbeats
            if heartbeat.credential_activation_state == "provider_endpoint_unconfirmed"
        ),
        "deferred_count": sum(1 for heartbeat in heartbeats if heartbeat.runtime_status == "deferred"),
        "missing_credential_source_count": len(missing_credentials),
        "by_runtime_status": dict(sorted(by_status.items())),
        "by_pipeline": dict(sorted(by_pipeline.items())),
        "by_selection_status": dict(sorted(by_selection.items())),
        "by_action_category": dict(sorted(by_action.items())),
        "missing_credentials": missing_credentials,
        "intentionally_disabled_count": by_status.get("intentionally_disabled", 0),
        "needs_adapter_count": by_status.get("needs_adapter", 0),
        "provider_decision_required_count": by_status.get("provider_decision_required", 0),
        "local_bridge_required_count": by_status.get("local_bridge_required", 0),
    }


def build_data_environment_map(settings: Settings | None = None) -> dict[str, Any]:
    settings = settings or Settings.from_env()
    checked_at = datetime.now(timezone.utc).isoformat()
    heartbeats = tuple(build_source_heartbeat(source, checked_at, settings) for source in SOURCE_SPECS)
    summary = _summarise(heartbeats)
    return {
        "schema_version": DATA_ENVIRONMENT_MAP_SCHEMA_VERSION,
        "generated_at": checked_at,
        "summary": summary,
        "sources": [heartbeat.to_dict() for heartbeat in heartbeats],
        "boundary": "This map describes source readiness and credentials only. It does not authorize trading.",
    }


def write_data_environment_map(
    payload: dict[str, Any],
    settings: Settings | None = None,
    path: str | Path | None = None,
) -> Path:
    settings = settings or Settings.from_env()
    output_path = Path(path or Path(settings.runtime_dir) / "data_environment_map.json")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    return output_path


def run_source_heartbeat(
    *,
    settings: Settings | None = None,
    store: SourceHeartbeatStore | None = None,
    event_log: EventLog | None = None,
) -> dict[str, Any]:
    settings = settings or Settings.from_env()
    store = store or SourceHeartbeatStore(settings=settings)
    event_log = event_log or EventLog(echo=False)
    data_map = build_data_environment_map(settings)
    output_path = write_data_environment_map(data_map, settings)
    run_payload = {
        "schema_version": SOURCE_HEARTBEAT_SCHEMA_VERSION,
        "checked_at": data_map["generated_at"],
        "summary": data_map["summary"],
        "data_environment_map_path": str(output_path),
    }
    store.write_run(run_payload)
    event_log.write(
        "source_heartbeat_completed",
        "source_heartbeat",
        {
            "source_count": data_map["summary"]["source_count"],
            "promoted_adapter_count": data_map["summary"]["promoted_adapter_count"],
            "missing_credential_source_count": data_map["summary"]["missing_credential_source_count"],
            "data_environment_map_path": str(output_path),
        },
    )
    return {
        "status": "ok",
        "checked_at": data_map["generated_at"],
        "summary": data_map["summary"],
        "store": store.health(),
        "data_environment_map_path": str(output_path),
        "event_log": event_log.health(),
    }


def source_heartbeat_summary(settings: Settings | None = None) -> dict[str, Any]:
    settings = settings or Settings.from_env()
    store = SourceHeartbeatStore(settings=settings)
    map_path = Path(settings.runtime_dir) / "data_environment_map.json"
    store_health = store.health()
    if not map_path.exists():
        return {
            "status": "not_started",
            "store": store_health,
            "data_environment_map_path": str(map_path),
            "boundary": "Run scripts/check_source_heartbeat.py to create the first data environment map.",
        }
    try:
        payload = json.loads(map_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        return {
            "status": "degraded",
            "store": store_health,
            "data_environment_map_path": str(map_path),
            "error": str(exc),
        }
    return {
        "status": "ok",
        "store": store_health,
        "data_environment_map_path": str(map_path),
        "generated_at": payload.get("generated_at"),
        "summary": payload.get("summary", {}),
        "boundary": payload.get("boundary"),
    }
