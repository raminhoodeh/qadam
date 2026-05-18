"""Agent and skill manifest registry for Qadam Phase 1E."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any


AGENT_MANIFEST_SCHEMA_VERSION = 1
SKILL_BUNDLE_SCHEMA_VERSION = 1

REPO_ROOT = Path(__file__).resolve().parents[1]
AGENTS_ROOT = REPO_ROOT / "agents"
SKILLS_ROOT = REPO_ROOT / "skills"

EXPECTED_AGENT_KEYS: tuple[str, ...] = (
    "coo",
    "research_analyst",
    "strategy_lead",
    "head_of_quant",
    "risk_agent",
    "signal_auditor",
    "execution_auditor",
    "fund_manager_interface",
)

EXPECTED_SKILL_KEYS: tuple[str, ...] = (
    "macro_intelligence",
    "prediction_markets",
    "physical_anomaly_monitoring",
    "options_volatility_flow",
    "akber_6_stage_filter",
    "private_edge_world_model",
    "risk_and_postmortems",
)

DECLARED_MCP_TOOLS: tuple[str, ...] = (
    "ticker_echo",
    "source_registry",
    "source_detail",
    "resource_registry",
    "resource_detail",
    "world_model_claims",
    "world_model_claim_detail",
    "governance_comments",
    "create_governance_comment",
    "ingestion_status",
    "source_heartbeat_status",
    "run_source_heartbeat",
    "run_test_ingestion",
    "phase1_live_adapter_registry_status",
    "phase1_live_adapter_status",
    "phase1_live_adapter_sample",
    "phase1_live_adapter_live_read_only",
    "historical_backfill_plan",
    "run_historical_backfill_sample",
    "trust_score_seed_status",
    "postgres_timescale_ingestion_status",
    "shadow_intelligence_status",
    "shadow_intelligence_provider_status",
    "shadow_intelligence_provider_probes",
    "lm_studio_models_status",
    "gemini_credential_status",
    "run_shadow_intelligence_sample",
    "run_research_shadow_triage_queue",
    "local_research_analyst_status",
    "run_local_research_analyst_inference",
    "telegram_communications_status",
    "queue_telegram_dry_run_samples",
    "gdelt_status",
    "gdelt_sample",
    "gdelt_live_read_only",
    "oref_status",
    "oref_sample",
    "oref_live_read_only",
    "nasa_firms_status",
    "nasa_firms_sample",
    "nasa_firms_live_read_only",
    "rss_status",
    "rss_sample",
    "rss_live_read_only",
    "fred_status",
    "fred_sample",
    "fred_live_read_only",
    "system_health",
    "execution_venues",
    "founding_manager_access",
    "qadam_module_map",
    "quantum_provider_registry",
    "secret_registry_status",
    "agent_registry_status",
    "agent_registry",
    "agent_detail",
    "skill_registry",
    "skill_detail",
    "agent_runtime_status",
    "agent_tool_authorization",
    "research_shadow_triage_queue",
    "create_research_shadow_triage_packet",
)

KNOWN_SOURCE_GROUPS: tuple[str, ...] = (
    "live_source_registry",
    "resource_registry",
    "world_model_corpus",
    "source_heartbeat",
    "adapters",
    "execution_registry",
    "quantum_provider_registry",
    "governance_forum",
    "telegram_communications",
    "secret_status",
    "cockpit_health",
    "local_stores",
    "event_log",
)

REQUIRED_FORBIDDEN_ACTIONS: tuple[str, ...] = (
    "broker_write",
    "live_capital_execution",
    "undeclared_tool_call",
    "raw_secret_access",
)

RAW_SECRET_PATTERNS: tuple[str, ...] = (
    "ghp" + "_",
    "vcp" + "_",
    "PV" + "Zj",
    "sk_live",
    "sk_test",
    "QCTRL_API_KEY" + "=",
    "NASA_FIRMS_API_KEY" + "=",
    "ALPACA_API_KEY" + "=",
    "ALPACA_API_SECRET" + "=",
    "KALSHI_API_KEY" + "=",
    "KALSHI_API_SECRET" + "=",
    "CLERK_SECRET_KEY" + "=",
)


@dataclass(frozen=True)
class AgentManifest:
    key: str
    display_name: str
    owner: str
    status: str
    role: str
    allowed_tools: tuple[str, ...]
    allowed_source_groups: tuple[str, ...]
    allowed_skills: tuple[str, ...]
    allowed_secret_names: tuple[str, ...]
    forbidden_actions: tuple[str, ...]
    output_schemas: tuple[str, ...]
    escalation: str
    path: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class SkillBundle:
    key: str
    name: str
    purpose: str
    allowed_agent_keys: tuple[str, ...]
    source_documents: tuple[str, ...]
    forbidden_actions: tuple[str, ...]
    path: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _load_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        loaded = json.load(handle)
    if not isinstance(loaded, dict):
        raise ValueError(f"expected JSON object: {path}")
    return loaded


def _as_tuple(value: Any) -> tuple[str, ...]:
    if not isinstance(value, list):
        return ()
    return tuple(item for item in value if isinstance(item, str))


def _agent_from_path(path: Path) -> AgentManifest:
    data = _load_json(path / "permissions.json")
    return AgentManifest(
        key=str(data.get("key") or path.name),
        display_name=str(data.get("display_name") or path.name),
        owner=str(data.get("owner") or "unassigned"),
        status=str(data.get("status") or "unknown"),
        role=str(data.get("role") or ""),
        allowed_tools=_as_tuple(data.get("allowed_tools")),
        allowed_source_groups=_as_tuple(data.get("allowed_source_groups")),
        allowed_skills=_as_tuple(data.get("allowed_skills")),
        allowed_secret_names=_as_tuple(data.get("allowed_secret_names")),
        forbidden_actions=_as_tuple(data.get("forbidden_actions")),
        output_schemas=_as_tuple(data.get("output_schemas")),
        escalation=str(data.get("escalation") or ""),
        path=str(path.relative_to(REPO_ROOT)),
    )


def _skill_from_path(path: Path) -> SkillBundle:
    data = _load_json(path / "skill.json")
    return SkillBundle(
        key=str(data.get("key") or path.name),
        name=str(data.get("name") or path.name),
        purpose=str(data.get("purpose") or ""),
        allowed_agent_keys=_as_tuple(data.get("allowed_agent_keys")),
        source_documents=_as_tuple(data.get("source_documents")),
        forbidden_actions=_as_tuple(data.get("forbidden_actions")),
        path=str(path.relative_to(REPO_ROOT)),
    )


def agent_registry() -> list[dict[str, Any]]:
    agents: list[AgentManifest] = []
    for key in EXPECTED_AGENT_KEYS:
        path = AGENTS_ROOT / key
        if path.exists():
            agents.append(_agent_from_path(path))
    return [agent.to_dict() for agent in agents]


def agent_detail(key: str) -> dict[str, Any]:
    if key not in EXPECTED_AGENT_KEYS:
        raise KeyError(f"unknown agent: {key}")
    path = AGENTS_ROOT / key
    if not path.exists():
        raise KeyError(f"agent manifest missing: {key}")
    agent = _agent_from_path(path).to_dict()
    agent_md = path / "agent.md"
    agent["agent_md_exists"] = agent_md.exists()
    return agent


def skill_registry() -> list[dict[str, Any]]:
    skills: list[SkillBundle] = []
    for key in EXPECTED_SKILL_KEYS:
        path = SKILLS_ROOT / key
        if path.exists():
            skills.append(_skill_from_path(path))
    return [skill.to_dict() for skill in skills]


def skill_detail(key: str) -> dict[str, Any]:
    if key not in EXPECTED_SKILL_KEYS:
        raise KeyError(f"unknown skill: {key}")
    path = SKILLS_ROOT / key
    if not path.exists():
        raise KeyError(f"skill bundle missing: {key}")
    skill = _skill_from_path(path).to_dict()
    skill["skill_md_exists"] = (path / "SKILL.md").exists()
    return skill


def _file_has_raw_secret(path: Path) -> bool:
    if not path.exists() or not path.is_file():
        return False
    text = path.read_text(encoding="utf-8")
    return any(pattern in text for pattern in RAW_SECRET_PATTERNS)


def validate_agent_os() -> dict[str, Any]:
    errors: list[str] = []
    warnings: list[str] = []
    agents: list[AgentManifest] = []
    skills: list[SkillBundle] = []

    for key in EXPECTED_AGENT_KEYS:
        path = AGENTS_ROOT / key
        if not path.exists():
            errors.append(f"missing_agent_folder:{key}")
            continue
        permissions_path = path / "permissions.json"
        agent_md = path / "agent.md"
        if not permissions_path.exists():
            errors.append(f"missing_permissions:{key}")
            continue
        if not agent_md.exists():
            errors.append(f"missing_agent_md:{key}")
        if _file_has_raw_secret(permissions_path) or _file_has_raw_secret(agent_md):
            errors.append(f"raw_secret_pattern:{key}")
        agent = _agent_from_path(path)
        agents.append(agent)
        if agent.key != key:
            errors.append(f"agent_key_mismatch:{key}:{agent.key}")
        if not agent.role:
            errors.append(f"missing_role:{key}")
        missing_forbidden = sorted(set(REQUIRED_FORBIDDEN_ACTIONS) - set(agent.forbidden_actions))
        if missing_forbidden:
            errors.append(f"missing_forbidden_actions:{key}:{','.join(missing_forbidden)}")
        unknown_tools = sorted(set(agent.allowed_tools) - set(DECLARED_MCP_TOOLS))
        if unknown_tools:
            errors.append(f"undeclared_tools:{key}:{','.join(unknown_tools)}")
        unknown_sources = sorted(set(agent.allowed_source_groups) - set(KNOWN_SOURCE_GROUPS))
        if unknown_sources:
            errors.append(f"unknown_source_groups:{key}:{','.join(unknown_sources)}")
        unknown_skills = sorted(set(agent.allowed_skills) - set(EXPECTED_SKILL_KEYS))
        if unknown_skills:
            errors.append(f"unknown_skills:{key}:{','.join(unknown_skills)}")
        if any(tool in agent.allowed_tools for tool in ("place_order", "cancel_order", "close_position")):
            errors.append(f"broker_write_tool_granted:{key}")
        for schema in agent.output_schemas:
            schema_path = path / schema
            if not schema_path.exists():
                errors.append(f"missing_output_schema:{key}:{schema}")
            elif _file_has_raw_secret(schema_path):
                errors.append(f"raw_secret_pattern:{key}:{schema}")

    for key in EXPECTED_SKILL_KEYS:
        path = SKILLS_ROOT / key
        if not path.exists():
            errors.append(f"missing_skill_folder:{key}")
            continue
        skill_json = path / "skill.json"
        skill_md = path / "SKILL.md"
        if not skill_json.exists():
            errors.append(f"missing_skill_json:{key}")
            continue
        if not skill_md.exists():
            errors.append(f"missing_skill_md:{key}")
        if _file_has_raw_secret(skill_json) or _file_has_raw_secret(skill_md):
            errors.append(f"raw_secret_pattern:skill:{key}")
        skill = _skill_from_path(path)
        skills.append(skill)
        if skill.key != key:
            errors.append(f"skill_key_mismatch:{key}:{skill.key}")
        unknown_agents = sorted(set(skill.allowed_agent_keys) - set(EXPECTED_AGENT_KEYS))
        if unknown_agents:
            errors.append(f"unknown_skill_agents:{key}:{','.join(unknown_agents)}")
        missing_forbidden = sorted(set(REQUIRED_FORBIDDEN_ACTIONS) - set(skill.forbidden_actions))
        if missing_forbidden:
            warnings.append(f"skill_missing_forbidden_actions:{key}:{','.join(missing_forbidden)}")

    granted_skills = {skill for agent in agents for skill in agent.allowed_skills}
    unused_skills = sorted(set(EXPECTED_SKILL_KEYS) - granted_skills)
    if unused_skills:
        warnings.append(f"unused_skills:{','.join(unused_skills)}")

    tool_grant_count = sum(len(agent.allowed_tools) for agent in agents)
    secret_name_count = sum(len(agent.allowed_secret_names) for agent in agents)
    return {
        "status": "ok" if not errors else "error",
        "schema_version": AGENT_MANIFEST_SCHEMA_VERSION,
        "agent_count": len(agents),
        "expected_agent_count": len(EXPECTED_AGENT_KEYS),
        "skill_count": len(skills),
        "expected_skill_count": len(EXPECTED_SKILL_KEYS),
        "tool_grant_count": tool_grant_count,
        "secret_name_grant_count": secret_name_count,
        "errors": errors,
        "warnings": warnings,
        "boundary": "Agents declare permissions and skills only. They do not receive broker-write authority.",
    }


def agent_registry_summary() -> dict[str, Any]:
    validation = validate_agent_os()
    return {
        "status": validation["status"],
        "schema_version": validation["schema_version"],
        "agent_count": validation["agent_count"],
        "expected_agent_count": validation["expected_agent_count"],
        "skill_count": validation["skill_count"],
        "expected_skill_count": validation["expected_skill_count"],
        "tool_grant_count": validation["tool_grant_count"],
        "secret_name_grant_count": validation["secret_name_grant_count"],
        "error_count": len(validation["errors"]),
        "warning_count": len(validation["warnings"]),
        "boundary": validation["boundary"],
    }
