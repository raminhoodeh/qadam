"""Applied-only learning input for the next Stage 1 Observe cycle.

Only explicitly approved and applied learning versions are exported as active
Stage 1 handoffs. Proposals, tests, holds, and rejected changes stay inert.
"""

from __future__ import annotations

from typing import Any

from orchestrator.config import Settings
from orchestrator.qadam_canonical_contracts import AtomicArtifactStore
from orchestrator.qadam_improvement_pipeline_view_model import (
    APPLIED_VERSIONS_ARTIFACT,
    IMPROVEMENT_PIPELINE_ARTIFACT,
)
from orchestrator.qadam_operator_ready_common import (
    authority_flags,
    now_iso,
    read_json,
    read_jsonl,
    runtime_dir,
    sha256_json,
    unique_errors,
    validate_authority,
)

SCHEMA_VERSION = "qadam_stage1_learning_input.v1"
PHASE_ID = "LI-3"

STAGE1_INPUT_ARTIFACT = "qadam_stage1_learning_input.json"
STAGE1_HANDOFFS_ARTIFACT = "qadam_stage1_learning_handoffs.jsonl"
CHECK_ARTIFACT = "qadam_stage1_learning_input_checks.json"

ALLOWED_TARGET_STAGES = {"observe", "patterns", "decide", "trade", "system"}


def _valid_applied_version(record: dict[str, Any]) -> bool:
    approval = record.get("approval")
    approval = approval if isinstance(approval, dict) else {}
    return bool(
        record.get("decision_state") == "applied"
        and approval.get("approved") is True
        and record.get("applied_version")
        and record.get("effective_from")
        and record.get("target_stage") in ALLOWED_TARGET_STAGES
        and record.get("expected_behavior")
        and record.get("monitoring_window")
        and record.get("rollback_condition")
    )


def _handoff(record: dict[str, Any]) -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "qadam_stage1_learning_handoff",
        "handoff_id": str(record.get("handoff_id") or record.get("proposal_id") or record.get("applied_version")),
        "proposal_id": record.get("proposal_id"),
        "applied_version": record.get("applied_version"),
        "target_stage": record.get("target_stage"),
        "target": record.get("target"),
        "effective_from": record.get("effective_from"),
        "evidence_refs": record.get("evidence_refs") or [],
        "expected_behavior": record.get("expected_behavior"),
        "monitoring_window": record.get("monitoring_window"),
        "rollback_condition": record.get("rollback_condition"),
        "approval": record.get("approval"),
        "state": "applied_stage1_input",
        "authority": authority_flags(),
    }


def build_stage1_learning_input(
    settings: Settings | None = None,
    *,
    generated_at: str | None = None,
    pipeline_override: dict[str, Any] | None = None,
) -> dict[str, Any]:
    runtime = runtime_dir(settings)
    generated = generated_at or now_iso()
    versions = read_jsonl(runtime / APPLIED_VERSIONS_ARTIFACT)
    pipeline = pipeline_override or read_json(runtime / IMPROVEMENT_PIPELINE_ARTIFACT)
    applied = [_handoff(record) for record in versions if _valid_applied_version(record)]
    rejected = [record for record in versions if not _valid_applied_version(record)]
    applied.sort(key=lambda row: (str(row.get("effective_from") or ""), str(row.get("applied_version") or "")))
    version_ids = [str(record.get("applied_version")) for record in applied]
    status = "ready_with_applied_learning_versions" if applied else "ready_no_applied_learning_versions"
    return {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "qadam_stage1_learning_input",
        "phase_id": PHASE_ID,
        "generated_at": generated,
        "status": status,
        "input_version": sha256_json({"applied_learning_version_ids": version_ids}),
        "applied_learning_version_ids": version_ids,
        "applied_handoff_count": len(applied),
        "rejected_non_applied_record_count": len(rejected),
        "handoffs": applied,
        "pipeline_status": pipeline.get("status") or "not_exported",
        "pipeline_generated_at": pipeline.get("generated_at"),
        "next_cycle_behavior": (
            "The next Observe cycle will record these approved versions in downstream lineage."
            if applied
            else "The next Observe cycle uses the current behavior because no learning version is approved and applied."
        ),
        "public_safe": True,
        "read_only": True,
        "command_disabled": True,
        "paper_only": True,
        "authority": authority_flags(),
        "boundary": (
            "This input pack exposes applied learning versions only. It cannot approve a proposal, mutate policy, "
            "create a trade candidate, approve risk, submit an order, or enable live capital."
        ),
    }


def validate_stage1_learning_input(model: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    handoffs = model.get("handoffs") if isinstance(model.get("handoffs"), list) else []
    version_ids = model.get("applied_learning_version_ids")
    version_ids = version_ids if isinstance(version_ids, list) else []
    if model.get("applied_handoff_count") != len(handoffs):
        errors.append("stage1_learning_handoff_count_mismatch")
    if len(version_ids) != len(set(version_ids)):
        errors.append("stage1_learning_version_duplicate")
    if version_ids != [str(record.get("applied_version")) for record in handoffs]:
        errors.append("stage1_learning_version_lineage_mismatch")
    for handoff in handoffs:
        approval = handoff.get("approval") if isinstance(handoff.get("approval"), dict) else {}
        if approval.get("approved") is not True:
            errors.append("stage1_learning_unapproved_handoff")
        if handoff.get("state") != "applied_stage1_input":
            errors.append("stage1_learning_non_applied_handoff")
        if handoff.get("target_stage") not in ALLOWED_TARGET_STAGES:
            errors.append("stage1_learning_target_invalid")
        if not handoff.get("effective_from"):
            errors.append("stage1_learning_effective_timestamp_missing")
        if not handoff.get("expected_behavior"):
            errors.append("stage1_learning_expected_behavior_missing")
        if not handoff.get("monitoring_window"):
            errors.append("stage1_learning_monitoring_window_missing")
        if not handoff.get("rollback_condition"):
            errors.append("stage1_learning_rollback_condition_missing")
        errors.extend(
            validate_authority(
                handoff.get("authority", {}),
                prefix=f"stage1_handoff:{handoff.get('handoff_id')}",
            )
        )
    if model.get("public_safe") is not True or model.get("read_only") is not True:
        errors.append("stage1_learning_input_not_public_read_only")
    if model.get("command_disabled") is not True:
        errors.append("stage1_learning_input_command_path_enabled")
    errors.extend(validate_authority(model.get("authority", {}), prefix="stage1_learning_input"))
    return unique_errors(errors)


def build_and_write_stage1_learning_input(
    settings: Settings | None = None,
) -> tuple[dict[str, Any], dict[str, Any], list[str]]:
    runtime = runtime_dir(settings)
    store = AtomicArtifactStore(runtime)
    model = build_stage1_learning_input(settings)
    errors = validate_stage1_learning_input(model)
    store.write_json(STAGE1_INPUT_ARTIFACT, model)
    store.write_jsonl(STAGE1_HANDOFFS_ARTIFACT, model["handoffs"])
    checks = {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "qadam_stage1_learning_input_checks",
        "phase_id": PHASE_ID,
        "generated_at": now_iso(),
        "status": "passed" if not errors else "blocked",
        "implementation_ready": not errors,
        "applied_handoff_count": model["applied_handoff_count"],
        "rejected_non_applied_record_count": model["rejected_non_applied_record_count"],
        "only_applied_versions_consumed": all(
            record.get("state") == "applied_stage1_input" for record in model["handoffs"]
        ),
        "paper_order_created_count": 0,
        "broker_write_count": 0,
        "proof_credit_created_count": 0,
        "validation_error_count": len(errors),
        "validation_errors": errors,
        "authority": authority_flags(),
    }
    store.write_json(CHECK_ARTIFACT, checks)
    return model, checks, errors
