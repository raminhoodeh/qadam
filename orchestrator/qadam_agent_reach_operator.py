"""Resumable operator for Qadam's bounded qualitative evidence lane."""

from __future__ import annotations

import shutil
import subprocess
from typing import Any

from orchestrator.config import Settings
from orchestrator.qadam_canonical_contracts import AtomicArtifactStore
from orchestrator.qadam_operator_ready_common import append_jsonl_durable
from orchestrator.qadam_qualitative_common import (
    AGENT_REACH_OPERATOR_ARTIFACT,
    AGENT_REACH_REPAIR_ARTIFACT,
    AGENT_REACH_RESOURCE_ARTIFACT,
    AGENT_REACH_SOAK_ARTIFACT,
    COMMAND_POLICY_PATH,
    now_iso,
    public_authority,
    read_json,
    repo_root,
    research_root,
    runtime_dir,
    stable_id,
)
from orchestrator.qadam_qualitative_pipeline import run_qualitative_evidence_pipeline
from orchestrator.qadam_qualitative_visibility import build_qualitative_visibility


def _tree_size() -> int:
    total = 0
    for path in research_root().rglob("*") if research_root().exists() else ():
        try:
            if path.is_file():
                total += path.stat().st_size
        except OSError:
            continue
    return total


def _research_path_ignored() -> bool:
    completed = subprocess.run(
        ["git", "check-ignore", "data/research/qadam_external_evidence"],
        cwd=repo_root(),
        capture_output=True,
        text=True,
        check=False,
    )
    return completed.returncode == 0


def run_agent_reach_operator(
    settings: Settings | None = None,
    *,
    allow_network: bool = False,
    run_fast_path: bool = True,
) -> tuple[dict[str, Any], list[str]]:
    runtime = runtime_dir(settings)
    policy = read_json(repo_root() / COMMAND_POLICY_PATH)
    ceiling = int(policy.get("qualitative_lane_disk_ceiling_bytes") or 10_737_418_240)
    pause_fraction = float(policy.get("pause_at_fraction") or 0.8)
    lane_bytes = _tree_size()
    disk = shutil.disk_usage(repo_root())
    ignored = _research_path_ignored()
    resource_errors: list[str] = []
    if not ignored:
        resource_errors.append("qualitative_research_path_not_git_ignored")
    if lane_bytes >= int(ceiling * pause_fraction):
        resource_errors.append("qualitative_lane_disk_pause_threshold_reached")
    if disk.free < 5 * 1024**3:
        resource_errors.append("host_free_disk_below_five_gib")
    resource = {
        "schema_version": "qadam_agent_reach_resource_state.v1",
        "artifact_type": "qadam_agent_reach_resource_state",
        "generated_at": now_iso(),
        "status": "within_limits" if not resource_errors else "paused_resource_boundary",
        "lane_bytes": lane_bytes,
        "lane_ceiling_bytes": ceiling,
        "pause_at_fraction": pause_fraction,
        "host_free_bytes": disk.free,
        "research_path_git_ignored": ignored,
        "validation_errors": resource_errors,
        "authority": public_authority(),
    }
    store = AtomicArtifactStore(runtime)
    store.write_json(AGENT_REACH_RESOURCE_ARTIFACT, resource)

    pipeline: dict[str, Any] = {}
    pipeline_errors: list[str] = []
    if not resource_errors:
        pipeline, pipeline_errors = run_qualitative_evidence_pipeline(
            settings,
            allow_network=allow_network,
            run_fast_path=run_fast_path,
        )
        build_qualitative_visibility(settings)
    errors = sorted(set(resource_errors + pipeline_errors))
    prior_soak = read_json(runtime / AGENT_REACH_SOAK_ARTIFACT)
    consecutive = int(prior_soak.get("consecutive_successful_cycles") or 0)
    consecutive = consecutive + 1 if not errors else 0
    soak = {
        "schema_version": "qadam_agent_reach_soak_status.v1",
        "artifact_type": "qadam_agent_reach_soak_status",
        "generated_at": now_iso(),
        "status": "soak_complete" if consecutive >= 7 else "soak_in_progress" if not errors else "soak_reset_after_failure",
        "consecutive_successful_cycles": consecutive,
        "required_successful_cycles": 7,
        "restart_safe": True,
        "network_failure_safe": True,
        "disk_pressure_pauses_safely": True,
        "authority": public_authority(),
    }
    store.write_json(AGENT_REACH_SOAK_ARTIFACT, soak)

    if errors:
        append_jsonl_durable(
            runtime / AGENT_REACH_REPAIR_ARTIFACT,
            {
                "repair_request_id": stable_id("agent-reach-repair", errors),
                "generated_at": now_iso(),
                "state": "open",
                "failure_class": "safe_refresh_or_contract_failure",
                "errors": errors,
                "automatic_retry_allowed": not resource_errors,
                "silent_code_edit_allowed": False,
                "authority": public_authority(),
            },
        )
    status = {
        "schema_version": "qadam_agent_reach_operator_status.v1",
        "artifact_type": "qadam_agent_reach_operator_status",
        "generated_at": now_iso(),
        "status": "operational" if not errors else "paused_with_typed_repair",
        "network_enabled": allow_network,
        "fast_path_enabled": run_fast_path,
        "resource_state": resource["status"],
        "pipeline_status": pipeline.get("status") or "not_run_resource_boundary",
        "soak_status": soak["status"],
        "validation_errors": errors,
        "safe_refresh_retry_allowed": True,
        "silent_code_edit_allowed": False,
        "secret_change_allowed": False,
        "direct_broker_call_made": False,
        "paper_order_created_count": 0,
        "authority": public_authority(),
    }
    store.write_json(AGENT_REACH_OPERATOR_ARTIFACT, status)
    return status, errors


__all__ = ["run_agent_reach_operator"]
