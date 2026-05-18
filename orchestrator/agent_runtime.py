"""Runtime permission checks for Qadam agent manifests."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4

from orchestrator.agent_registry import (
    AGENTS_ROOT,
    DECLARED_MCP_TOOLS,
    EXPECTED_AGENT_KEYS,
    REPO_ROOT,
    agent_detail,
    validate_agent_os,
)
from orchestrator.config import Settings
from orchestrator.event_log import EventLog

AGENT_RUNTIME_SCHEMA_VERSION = 1
BROKER_WRITE_TOOLS = frozenset({"place_order", "cancel_order", "close_position"})
UNDECLARED_TOOL_PROBE = "__undeclared_phase1_probe__"


@dataclass(frozen=True)
class ToolAuthorization:
    agent_key: str
    tool_name: str
    allowed: bool
    reason: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class ShadowTriagePacket:
    schema_version: int
    packet_id: str
    agent_key: str
    status: str
    source_event_refs: tuple[str, ...]
    summary: str
    uncertainty: str
    created_at: str
    boundary: str

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["source_event_refs"] = list(self.source_event_refs)
        return payload


def authorize_tool_call(agent_key: str, tool_name: str) -> ToolAuthorization:
    validation = validate_agent_os()
    if validation["status"] != "ok":
        return ToolAuthorization(agent_key, tool_name, False, "agent_os_invalid")
    if agent_key not in EXPECTED_AGENT_KEYS:
        return ToolAuthorization(agent_key, tool_name, False, "unknown_agent")
    if tool_name in BROKER_WRITE_TOOLS:
        return ToolAuthorization(agent_key, tool_name, False, "broker_write_tool_blocked")
    if tool_name not in DECLARED_MCP_TOOLS:
        return ToolAuthorization(agent_key, tool_name, False, "undeclared_tool")

    agent = agent_detail(agent_key)
    allowed_tools = set(agent["allowed_tools"])
    if tool_name not in allowed_tools:
        return ToolAuthorization(agent_key, tool_name, False, "missing_tool_grant")
    return ToolAuthorization(agent_key, tool_name, True, "allowed")


def _load_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        loaded = json.load(handle)
    if not isinstance(loaded, dict):
        raise ValueError(f"expected JSON object: {path}")
    return loaded


def _type_matches(value: Any, schema_type: str) -> bool:
    if schema_type == "string":
        return isinstance(value, str)
    if schema_type == "boolean":
        return isinstance(value, bool)
    if schema_type == "array":
        return isinstance(value, list)
    if schema_type == "object":
        return isinstance(value, dict)
    if schema_type == "number":
        return isinstance(value, int | float) and not isinstance(value, bool)
    if schema_type == "integer":
        return isinstance(value, int) and not isinstance(value, bool)
    return True


def validate_sample_output(agent_key: str) -> dict[str, Any]:
    agent = agent_detail(agent_key)
    fixture_path = AGENTS_ROOT / agent_key / "fixtures" / "sample_output.json"
    errors: list[str] = []
    if not fixture_path.exists():
        return {"agent_key": agent_key, "status": "error", "errors": ["missing_sample_output"]}

    fixture = _load_json(fixture_path)
    for schema_ref in agent["output_schemas"]:
        schema_path = AGENTS_ROOT / agent_key / str(schema_ref)
        schema = _load_json(schema_path)
        required = schema.get("required", [])
        if isinstance(required, list):
            for key in required:
                if isinstance(key, str) and key not in fixture:
                    errors.append(f"missing_required:{key}")
        properties = schema.get("properties", {})
        if isinstance(properties, dict):
            for key, property_schema in properties.items():
                if key not in fixture or not isinstance(property_schema, dict):
                    continue
                if "const" in property_schema and fixture[key] != property_schema["const"]:
                    errors.append(f"const_mismatch:{key}")
                schema_type = property_schema.get("type")
                if isinstance(schema_type, str) and not _type_matches(fixture[key], schema_type):
                    errors.append(f"type_mismatch:{key}:{schema_type}")

    return {
        "agent_key": agent_key,
        "status": "ok" if not errors else "error",
        "path": str(fixture_path.relative_to(REPO_ROOT)),
        "errors": errors,
    }


def validate_all_sample_outputs() -> dict[str, Any]:
    results = [validate_sample_output(agent_key) for agent_key in EXPECTED_AGENT_KEYS]
    errors = [error for result in results for error in result["errors"]]
    return {
        "status": "ok" if not errors else "error",
        "sample_output_count": len(results),
        "expected_sample_output_count": len(EXPECTED_AGENT_KEYS),
        "errors": errors,
        "results": results,
    }


def agent_authority_matrix() -> dict[str, Any]:
    broker_checks = [
        authorize_tool_call(agent_key, tool_name)
        for agent_key in EXPECTED_AGENT_KEYS
        for tool_name in sorted(BROKER_WRITE_TOOLS)
    ]
    undeclared_checks = [
        authorize_tool_call(agent_key, UNDECLARED_TOOL_PROBE)
        for agent_key in EXPECTED_AGENT_KEYS
    ]
    broker_write_failures = [
        check.to_dict()
        for check in broker_checks
        if check.allowed or check.reason != "broker_write_tool_blocked"
    ]
    undeclared_failures = [
        check.to_dict()
        for check in undeclared_checks
        if check.allowed or check.reason != "undeclared_tool"
    ]
    return {
        "status": "ok" if not broker_write_failures and not undeclared_failures else "error",
        "agent_count": len(EXPECTED_AGENT_KEYS),
        "broker_write_tool_count": len(BROKER_WRITE_TOOLS),
        "broker_write_block_count": len(broker_checks) - len(broker_write_failures),
        "expected_broker_write_block_count": len(EXPECTED_AGENT_KEYS) * len(BROKER_WRITE_TOOLS),
        "undeclared_tool_block_count": len(undeclared_checks) - len(undeclared_failures),
        "expected_undeclared_tool_block_count": len(EXPECTED_AGENT_KEYS),
        "broker_write_failures": broker_write_failures,
        "undeclared_tool_failures": undeclared_failures,
        "boundary": "Every agent must fail closed for broker-write tools and undeclared tools.",
    }


def _queue_path(settings: Settings | None = None) -> Path:
    settings = settings or Settings.from_env()
    return Path(settings.runtime_dir) / "research_triage_queue.jsonl"


def create_shadow_triage_packet(
    *,
    source_event_refs: tuple[str, ...],
    summary: str,
    uncertainty: str = "unknown",
    settings: Settings | None = None,
    event_log: EventLog | None = None,
) -> dict[str, Any]:
    authorization = authorize_tool_call("research_analyst", "source_registry")
    if not authorization.allowed:
        raise PermissionError(f"research_analyst runtime authorization failed: {authorization.reason}")

    settings = settings or Settings.from_env()
    path = _queue_path(settings)
    path.parent.mkdir(parents=True, exist_ok=True)
    packet = ShadowTriagePacket(
        schema_version=AGENT_RUNTIME_SCHEMA_VERSION,
        packet_id=str(uuid4()),
        agent_key="research_analyst",
        status="queued_shadow_only",
        source_event_refs=source_event_refs,
        summary=summary,
        uncertainty=uncertainty,
        created_at=datetime.now(timezone.utc).isoformat(),
        boundary="Shadow triage only. No signal, risk decision, or execution authority.",
    )
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(packet.to_dict(), sort_keys=True) + "\n")

    (event_log or EventLog(echo=False)).write(
        "agent_shadow_triage_packet_queued",
        "agent_runtime",
        {
            "packet_id": packet.packet_id,
            "agent_key": packet.agent_key,
            "source_event_ref_count": len(source_event_refs),
            "queue_path": str(path),
        },
    )
    return packet.to_dict() | {"queue_path": str(path)}


def shadow_triage_queue_summary(settings: Settings | None = None) -> dict[str, Any]:
    path = _queue_path(settings)
    if not path.exists():
        return {"status": "empty", "path": str(path), "packet_count": 0, "last_packet_id": None}
    packet_count = 0
    last_packet_id: str | None = None
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            stripped = line.strip()
            if not stripped:
                continue
            packet_count += 1
            try:
                last_packet_id = json.loads(stripped).get("packet_id")
            except json.JSONDecodeError:
                return {"status": "degraded", "path": str(path), "packet_count": packet_count, "last_packet_id": None}
    return {"status": "ok", "path": str(path), "packet_count": packet_count, "last_packet_id": last_packet_id}


def agent_runtime_summary(settings: Settings | None = None) -> dict[str, Any]:
    checks = (
        authorize_tool_call("research_analyst", "source_registry"),
        authorize_tool_call("research_analyst", "execution_venues"),
        authorize_tool_call("risk_agent", "execution_venues"),
        authorize_tool_call("strategy_lead", "place_order"),
    )
    sample_outputs = validate_all_sample_outputs()
    authority_matrix = agent_authority_matrix()
    queue = shadow_triage_queue_summary(settings)
    expected_blocks = sum(1 for check in checks if not check.allowed)
    errors: list[str] = []
    if checks[0].allowed is not True:
        errors.append("research_analyst_source_registry_should_allow")
    if checks[1].allowed is not False:
        errors.append("research_analyst_execution_venues_should_block")
    if checks[2].allowed is not True:
        errors.append("risk_agent_execution_venues_should_allow")
    if checks[3].allowed is not False:
        errors.append("strategy_lead_place_order_should_block")
    if sample_outputs["status"] != "ok":
        errors.extend(f"sample_output:{error}" for error in sample_outputs["errors"])
    if authority_matrix["status"] != "ok":
        errors.append("authority_matrix_failed")

    return {
        "status": "ok" if not errors else "error",
        "schema_version": AGENT_RUNTIME_SCHEMA_VERSION,
        "authorization_check_count": len(checks),
        "expected_block_count": expected_blocks,
        "broker_write_block_count": authority_matrix["broker_write_block_count"],
        "expected_broker_write_block_count": authority_matrix["expected_broker_write_block_count"],
        "undeclared_tool_block_count": authority_matrix["undeclared_tool_block_count"],
        "expected_undeclared_tool_block_count": authority_matrix["expected_undeclared_tool_block_count"],
        "sample_output_count": sample_outputs["sample_output_count"],
        "shadow_queue_status": queue["status"],
        "shadow_queue_packet_count": queue["packet_count"],
        "errors": errors,
        "checks": [check.to_dict() for check in checks],
        "authority_matrix": authority_matrix,
        "queue": queue,
        "boundary": "Runtime grants are enforced before tool use. Shadow triage has no execution authority.",
    }
