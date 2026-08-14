"""CTC-0/1 inventory and constitutional hierarchy checks."""

from __future__ import annotations

import json
from pathlib import Path
import re
import subprocess
from typing import Any

from orchestrator.config import Settings
from orchestrator.qadam_canonical_contracts import AtomicArtifactStore
from orchestrator.qadam_operator_ready_common import (
    authority_flags,
    now_iso,
    read_json,
    runtime_dir,
    unique_errors,
    validate_authority,
)
from orchestrator.qadam_tradeability_capabilities import FIELD_CAPABILITIES

SCHEMA_VERSION = "qadam_tradeability_baseline.v1"
CONTRACT_INVENTORY_ARTIFACT = "qadam_tradeability_contract_inventory.json"
PROMPT_INVENTORY_ARTIFACT = "qadam_agent_prompt_inventory.json"
PARALLEL_AUDIT_ARTIFACT = "qadam_parallel_pipeline_audit.json"
RELEASE_BASELINE_ARTIFACT = "qadam_release_reproducibility_baseline.json"
FIELD_DRIFT_ARTIFACT = "qadam_contract_field_drift_report.json"
HIERARCHY_CHECK_ARTIFACT = "qadam_contract_hierarchy_checks.json"
PRECEDENCE_AUDIT_ARTIFACT = "qadam_instruction_precedence_audit.json"
CHECK_ARTIFACT = "qadam_ctc0_baseline_checks.json"

ROOT = Path(__file__).resolve().parents[1]
ARTIFACT_PATTERN = re.compile(r"[\"']([a-zA-Z0-9_.-]+\.(?:json|jsonl))[\"']")


def _git(*args: str) -> str:
    completed = subprocess.run(
        ("git", *args),
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    return completed.stdout.strip()


def _runtime_module_status() -> dict[str, Any]:
    lines = [line for line in _git("status", "--porcelain=v1").splitlines() if line]
    runtime_code = [
        line
        for line in lines
        if line[3:].startswith(("orchestrator/", "scripts/", "agents/", "config/", "schemas/"))
    ]
    untracked_runtime_code = [line[3:] for line in runtime_code if line.startswith("??")]
    return {
        "branch": _git("branch", "--show-current"),
        "commit": _git("rev-parse", "HEAD"),
        "dirty_path_count": len(lines),
        "runtime_code_dirty_path_count": len(runtime_code),
        "active_untracked_runtime_code_count": len(untracked_runtime_code),
        "active_untracked_runtime_code": sorted(untracked_runtime_code),
        "committed_release": not runtime_code,
    }


def _artifact_references() -> list[dict[str, Any]]:
    references: dict[str, dict[str, Any]] = {}
    for path in sorted((ROOT / "orchestrator").glob("*.py")):
        try:
            text = path.read_text(encoding="utf-8")
        except OSError:
            continue
        for artifact in ARTIFACT_PATTERN.findall(text):
            if not artifact.startswith("qadam_"):
                continue
            row = references.setdefault(
                artifact,
                {
                    "artifact": artifact,
                    "referencing_modules": [],
                    "declared_owner_count": 0,
                    "declared_owner": None,
                },
            )
            row["referencing_modules"].append(path.relative_to(ROOT).as_posix())
    owners = {
        "qadam_tradeability_envelopes.jsonl": "orchestrator.qadam_tradeability_pipeline",
        "qadam_strategy_hypotheses_v3.jsonl": "orchestrator.qadam_tradeability_pipeline",
        "qadam_decision_evidence_packets.jsonl": "orchestrator.qadam_tradeability_pipeline",
        "qadam_akber_filter_v3_results.jsonl": "orchestrator.qadam_akber_filter_v3",
        "qadam_forward_shadow_decisions.jsonl": "orchestrator.qadam_forward_shadow",
        "qadam_position_size_proposals.jsonl": "orchestrator.qadam_portfolio_risk_engine",
        "qadam_router_v3_decisions.jsonl": "orchestrator.qadam_router_v3_paperops",
        "qadam_paperops_handoff_v3_accepted.jsonl": "orchestrator.qadam_router_v3_paperops",
    }
    for artifact, owner in owners.items():
        row = references.setdefault(
            artifact,
            {"artifact": artifact, "referencing_modules": []},
        )
        row.update({"declared_owner_count": 1, "declared_owner": owner})
    return sorted(references.values(), key=lambda row: str(row["artifact"]))


def _prompt_inventory() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for path in sorted((ROOT / "agents").rglob("*")):
        if not path.is_file() or path.name == ".DS_Store":
            continue
        rows.append(
            {
                "path": path.relative_to(ROOT).as_posix(),
                "kind": (
                    "schema"
                    if path.suffix == ".json" and "schemas" in path.parts
                    else "fixture"
                    if "fixtures" in path.parts
                    else "template"
                    if "templates" in path.parts or path.name == "agent.md"
                    else "manifest"
                ),
                "versioned_filename": bool(re.search(r"\.v\d+\.", path.name)),
            }
        )
    embedded = []
    for path in sorted((ROOT / "orchestrator").glob("*.py")):
        text = path.read_text(encoding="utf-8")
        if re.search(r"\bsystem_prompt\s*=", text):
            embedded.append(path.relative_to(ROOT).as_posix())
    return rows + [
        {
            "path": path,
            "kind": "embedded_system_prompt",
            "versioned_filename": False,
        }
        for path in embedded
    ]


def build_baseline(settings: Settings | None = None) -> dict[str, Any]:
    runtime = runtime_dir(settings)
    generated_at = now_iso()
    hierarchy = json.loads(
        (ROOT / "config/qadam_contract_hierarchy.json").read_text(encoding="utf-8")
    )
    task_registry = json.loads(
        (ROOT / "config/qadam_agent_task_registry.json").read_text(encoding="utf-8")
    )
    artifacts = _artifact_references()
    prompts = _prompt_inventory()
    release = _runtime_module_status()
    parallel = {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "qadam_parallel_pipeline_audit",
        "generated_at": generated_at,
        "legacy_lane": {
            "draft": "qadam_strategy_hypotheses_v3.jsonl",
            "akber": "qadam_akber_filter_v3_results.jsonl",
        },
        "qeg_lane": {
            "draft": "qadam_qeg_strategy_hypotheses.jsonl",
            "akber": "qadam_qeg_akber_results.jsonl",
        },
        "parallel_downstream_truth_detected": True,
        "required_resolution": "one_compiler_one_canonical_akber_source",
        "qeg_projection_may_remain_audit_only": True,
        "authority": authority_flags(),
    }
    inventory = {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "qadam_tradeability_contract_inventory",
        "generated_at": generated_at,
        "status": "complete",
        "artifact_count": len(artifacts),
        "artifacts": artifacts,
        "canonical_decision_artifacts": [
            row for row in artifacts if row.get("declared_owner_count") == 1
        ],
        "authority": authority_flags(),
    }
    prompt_payload = {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "qadam_agent_prompt_inventory",
        "generated_at": generated_at,
        "record_count": len(prompts),
        "embedded_prompt_count": sum(
            row["kind"] == "embedded_system_prompt" for row in prompts
        ),
        "records": prompts,
        "authority": authority_flags(),
    }
    field_drift = {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "qadam_contract_field_drift_report",
        "generated_at": generated_at,
        "required_field_count": len(FIELD_CAPABILITIES),
        "fields": [
            {"field_id": field_id, **contract}
            for field_id, contract in sorted(FIELD_CAPABILITIES.items())
        ],
        "missing_producer_count": sum(
            not row.get("producer") for row in FIELD_CAPABILITIES.values()
        ),
        "authority": authority_flags(),
    }
    precedence_errors: list[str] = []
    expected = [
        "constitutional_safety",
        "canonical_data_contract",
        "agent_task_contract",
        "strategy_profile",
        "prompt_template",
        "runtime_task",
    ]
    if hierarchy.get("precedence") != expected:
        precedence_errors.append("contract_precedence_invalid")
    boundaries = hierarchy.get("immutable_boundaries", {})
    if boundaries.get("paper_only") is not True:
        precedence_errors.append("hierarchy_paper_only_missing")
    if boundaries.get("live_capital_enabled") is not False:
        precedence_errors.append("hierarchy_live_capital_enabled")
    if any(
        row.get("authority") != "research_proposal_only"
        for row in task_registry.get("task_types", {}).values()
    ):
        precedence_errors.append("agent_task_authority_invalid")
    precedence = {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "qadam_instruction_precedence_audit",
        "generated_at": generated_at,
        "status": "passed" if not precedence_errors else "blocked",
        "trusted_instruction_classes": expected,
        "untrusted_data_classes": ["provider_payload", "web_content", "telegram_inbound"],
        "validation_errors": precedence_errors,
        "authority": authority_flags(),
    }
    return {
        "inventory": inventory,
        "prompts": prompt_payload,
        "parallel": parallel,
        "release": {
            "schema_version": SCHEMA_VERSION,
            "artifact_type": "qadam_release_reproducibility_baseline",
            "generated_at": generated_at,
            **release,
            "authority": authority_flags(),
        },
        "field_drift": field_drift,
        "hierarchy": hierarchy,
        "precedence": precedence,
        "runtime_root": str(runtime),
    }


def validate_baseline(payload: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    inventory = payload.get("inventory", {})
    if not inventory.get("artifacts"):
        errors.append("contract_inventory_empty")
    if payload.get("parallel", {}).get("parallel_downstream_truth_detected") is not True:
        errors.append("parallel_pipeline_not_detected_at_baseline")
    if payload.get("field_drift", {}).get("missing_producer_count") != 0:
        errors.append("required_field_producer_missing")
    errors.extend(payload.get("precedence", {}).get("validation_errors", []))
    for key in ("inventory", "prompts", "parallel", "release", "field_drift", "precedence"):
        errors.extend(validate_authority(payload[key].get("authority", {}), prefix=key))
    return unique_errors(errors)


def build_and_write_baseline(
    settings: Settings | None = None,
) -> tuple[dict[str, Any], dict[str, Any], list[str]]:
    runtime = runtime_dir(settings)
    payload = build_baseline(settings)
    errors = validate_baseline(payload)
    checks = {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "qadam_ctc0_baseline_checks",
        "generated_at": now_iso(),
        "status": "passed" if not errors else "blocked",
        "implementation_complete": not errors,
        "artifact_count": payload["inventory"]["artifact_count"],
        "prompt_record_count": payload["prompts"]["record_count"],
        "active_untracked_runtime_code_count": payload["release"][
            "active_untracked_runtime_code_count"
        ],
        "parallel_pipeline_detected": payload["parallel"][
            "parallel_downstream_truth_detected"
        ],
        "validation_errors": errors,
        "authority": authority_flags(),
    }
    store = AtomicArtifactStore(runtime)
    store.write_json(CONTRACT_INVENTORY_ARTIFACT, payload["inventory"])
    store.write_json(PROMPT_INVENTORY_ARTIFACT, payload["prompts"])
    store.write_json(PARALLEL_AUDIT_ARTIFACT, payload["parallel"])
    store.write_json(RELEASE_BASELINE_ARTIFACT, payload["release"])
    store.write_json(FIELD_DRIFT_ARTIFACT, payload["field_drift"])
    store.write_json(PRECEDENCE_AUDIT_ARTIFACT, payload["precedence"])
    store.write_json(
        HIERARCHY_CHECK_ARTIFACT,
        {
            **payload["precedence"],
            "artifact_type": "qadam_contract_hierarchy_checks",
        },
    )
    store.write_json(CHECK_ARTIFACT, checks)
    return payload, checks, errors


__all__ = [
    "CHECK_ARTIFACT",
    "build_and_write_baseline",
    "build_baseline",
    "validate_baseline",
]
