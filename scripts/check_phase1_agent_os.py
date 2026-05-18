#!/usr/bin/env python3
"""Acceptance check for Phase 1E/1F Agent OS readiness."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from orchestrator.agent_registry import (
    AGENTS_ROOT,
    EXPECTED_AGENT_KEYS,
    EXPECTED_SKILL_KEYS,
    agent_registry,
    skill_registry,
    validate_agent_os,
)
from orchestrator.agent_runtime import (
    agent_authority_matrix,
    agent_runtime_summary,
    authorize_tool_call,
    validate_all_sample_outputs,
)

AUTHORITY_FLAGS = ("execution_allowed", "paper_order_allowed", "broker_write_allowed")
SECRET_STATUS_AGENT_KEYS = {"execution_auditor", "head_of_quant", "risk_agent"}
REQUIRED_AGENT_TOOLS = {
    "coo": {"run_source_heartbeat", "run_test_ingestion", "agent_runtime_status"},
    "research_analyst": {"source_registry", "create_research_shadow_triage_packet", "run_local_research_analyst_inference"},
    "strategy_lead": {"gemini_credential_status", "local_research_analyst_status"},
    "head_of_quant": {"quantum_provider_registry"},
    "risk_agent": {"execution_venues", "agent_tool_authorization"},
    "signal_auditor": {"source_registry", "source_heartbeat_status"},
    "execution_auditor": {"execution_venues", "secret_registry_status"},
    "fund_manager_interface": {"governance_comments", "create_governance_comment", "telegram_communications_status"},
}
REQUIRED_ALLOWED = (
    ("coo", "run_source_heartbeat"),
    ("research_analyst", "run_local_research_analyst_inference"),
    ("strategy_lead", "gemini_credential_status"),
    ("head_of_quant", "quantum_provider_registry"),
    ("risk_agent", "execution_venues"),
    ("signal_auditor", "source_registry"),
    ("execution_auditor", "execution_venues"),
    ("fund_manager_interface", "create_governance_comment"),
)
REQUIRED_BLOCKED = (
    ("research_analyst", "execution_venues"),
    ("strategy_lead", "place_order"),
    ("fund_manager_interface", "execution_venues"),
    ("coo", "cancel_order"),
)


def _load_fixture(agent_key: str) -> dict[str, object]:
    path = AGENTS_ROOT / agent_key / "fixtures" / "sample_output.json"
    with path.open("r", encoding="utf-8") as handle:
        payload = json.load(handle)
    if not isinstance(payload, dict):
        raise ValueError(f"expected JSON object: {path}")
    return payload


def main() -> int:
    errors: list[str] = []
    validation = validate_agent_os()
    runtime = agent_runtime_summary()
    sample_outputs = validate_all_sample_outputs()
    authority_matrix = agent_authority_matrix()
    agents = agent_registry()
    skills = skill_registry()

    if validation["status"] != "ok":
        errors.extend(f"agent_manifest:{error}" for error in validation["errors"])
    if runtime["status"] != "ok":
        errors.extend(f"agent_runtime:{error}" for error in runtime["errors"])
    if sample_outputs["status"] != "ok":
        errors.extend(f"sample_output:{error}" for error in sample_outputs["errors"])
    if authority_matrix["status"] != "ok":
        errors.append("authority_matrix_failed")
    if len(agents) != len(EXPECTED_AGENT_KEYS):
        errors.append("agent_count_mismatch")
    if len(skills) != len(EXPECTED_SKILL_KEYS):
        errors.append("skill_count_mismatch")

    for agent in agents:
        key = str(agent["key"])
        tools = set(agent.get("allowed_tools") or [])
        required_tools = REQUIRED_AGENT_TOOLS.get(key, set())
        missing_tools = sorted(required_tools - tools)
        if missing_tools:
            errors.append(f"missing_phase1_tools:{key}:{','.join(missing_tools)}")
        if agent.get("allowed_secret_names") and key not in SECRET_STATUS_AGENT_KEYS:
            errors.append(f"unexpected_secret_name_grant:{key}")
        if "agent_runtime_status" not in tools:
            errors.append(f"agent_runtime_status_not_visible:{key}")

        fixture = _load_fixture(key)
        for flag in AUTHORITY_FLAGS:
            if fixture.get(flag) is not False:
                errors.append(f"fixture_authority_flag_not_false:{key}:{flag}")
        boundary = fixture.get("boundary")
        if not isinstance(boundary, str) or len(boundary.strip()) < 20:
            errors.append(f"fixture_boundary_missing:{key}")

    for skill in skills:
        if not skill.get("source_documents"):
            errors.append(f"skill_source_documents_missing:{skill['key']}")
        if not skill.get("allowed_agent_keys"):
            errors.append(f"skill_allowed_agents_missing:{skill['key']}")

    for agent_key, tool_name in REQUIRED_ALLOWED:
        check = authorize_tool_call(agent_key, tool_name)
        if not check.allowed:
            errors.append(f"required_allowed_blocked:{agent_key}:{tool_name}:{check.reason}")
    for agent_key, tool_name in REQUIRED_BLOCKED:
        check = authorize_tool_call(agent_key, tool_name)
        if check.allowed:
            errors.append(f"required_blocked_allowed:{agent_key}:{tool_name}")

    print("phase1_agent_os_status=" + ("ok" if not errors else "error"))
    print(f"phase1_agent_os_agent_count={len(agents)}")
    print(f"phase1_agent_os_skill_count={len(skills)}")
    print(f"phase1_agent_os_tool_grant_count={validation['tool_grant_count']}")
    print(f"phase1_agent_os_secret_name_grant_count={validation['secret_name_grant_count']}")
    print(f"phase1_agent_os_broker_write_block_count={authority_matrix['broker_write_block_count']}")
    print(f"phase1_agent_os_expected_broker_write_block_count={authority_matrix['expected_broker_write_block_count']}")
    print(f"phase1_agent_os_undeclared_tool_block_count={authority_matrix['undeclared_tool_block_count']}")
    print(f"phase1_agent_os_sample_output_count={sample_outputs['sample_output_count']}")
    print("phase1_agent_os_boundary=Agents are permissioned, sample outputs are non-executable, and broker-write tools fail closed.")
    for error in errors:
        print(f"phase1_agent_os_error={error}")

    if errors:
        return 1
    print("phase1_agent_os_check=ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
