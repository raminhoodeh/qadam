"""RF-6 legacy quarantine metadata and post-refactor rebaseline."""

from __future__ import annotations

import ast
from copy import deepcopy
from pathlib import Path
from typing import Any

from orchestrator.config import Settings
from orchestrator.qadam_architecture_audit import build_and_write_architecture_audit
from orchestrator.qadam_canonical_contracts import (
    CANONICAL_ARTIFACTS,
    AtomicArtifactStore,
    build_and_write_canonical_contracts,
)
from orchestrator.qadam_characterization_harness import (
    build_and_write_characterization_harness,
)
from orchestrator.qadam_decision_execution_boundaries import (
    build_and_write_decision_execution_boundaries,
)
from orchestrator.qadam_dynamic_plan import (
    PHASE_ORDER,
    build_plan_drift,
    load_or_create_phase_status,
    validate_dynamic_plan_state,
)
from orchestrator.qadam_operator_ready_common import (
    ROOT,
    authority_flags,
    file_sha256,
    now_iso,
    read_json,
    read_jsonl,
    runtime_dir,
    unique_errors,
    validate_authority,
)
from orchestrator.qadam_refactor_baseline import (
    BASELINE_ARTIFACT,
    build_refactor_baseline,
)
from orchestrator.qadam_research_boundaries import build_and_write_research_boundaries

SCHEMA_VERSION = "qadam_post_refactor_baseline.v1"
PHASE_ID = "RF-6"

QUARANTINE_ARTIFACT = "qadam_legacy_quarantine_registry.json"
POST_BASELINE_ARTIFACT = "qadam_post_refactor_baseline.json"
BEHAVIOR_DIFF_ARTIFACT = "qadam_post_refactor_behavior_diff.json"
PLAN_REBASELINE_ARTIFACT = "qadam_post_refactor_plan_rebaseline.json"
CHECK_ARTIFACT = "qadam_post_refactor_baseline_checks.json"

PRIOR_CHECK_ARTIFACTS = {
    "RF-0": "qadam_refactor_baseline_checks.json",
    "DP-0": "qadam_dynamic_plan_checks.json",
    "RF-1": "qadam_architecture_audit_checks.json",
    "RF-2": "qadam_characterization_harness_checks.json",
    "RF-3": "qadam_canonical_contracts_checks.json",
    "RF-4": "qadam_research_boundaries_checks.json",
    "RF-5": "qadam_decision_execution_boundaries_checks.json",
}

WAVE0_MODULES = (
    "orchestrator/qadam_operator_ready_common.py",
    "orchestrator/qadam_refactor_baseline.py",
    "orchestrator/qadam_dynamic_plan.py",
    "orchestrator/qadam_architecture_audit.py",
    "orchestrator/qadam_characterization_harness.py",
    "orchestrator/qadam_canonical_contracts.py",
    "orchestrator/qadam_research_boundaries.py",
    "orchestrator/qadam_decision_execution_boundaries.py",
    "orchestrator/qadam_post_refactor_baseline.py",
)

LEGACY_IMPORT_PREFIXES = (
    "orchestrator.qsase_",
    "orchestrator.phase4_",
    "orchestrator.phase5_",
    "orchestrator.phase6_",
    "orchestrator.phase7_",
)


def _paths(settings: Settings | None = None) -> dict[str, Path]:
    runtime = runtime_dir(settings)
    return {
        "quarantine": runtime / QUARANTINE_ARTIFACT,
        "post_baseline": runtime / POST_BASELINE_ARTIFACT,
        "behavior_diff": runtime / BEHAVIOR_DIFF_ARTIFACT,
        "plan_rebaseline": runtime / PLAN_REBASELINE_ARTIFACT,
        "checks": runtime / CHECK_ARTIFACT,
    }


def _wave0_legacy_imports() -> list[dict[str, str]]:
    records: list[dict[str, str]] = []
    for relative in WAVE0_MODULES:
        path = ROOT / relative
        if not path.exists():
            continue
        try:
            tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        except (OSError, SyntaxError):
            continue
        imports: set[str] = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imports.update(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                imports.add(node.module)
        for imported in sorted(imports):
            if imported.startswith(LEGACY_IMPORT_PREFIXES):
                records.append({"source": relative, "legacy_import": imported})
    return records


def build_legacy_quarantine_registry(settings: Settings | None = None) -> dict[str, Any]:
    runtime = runtime_dir(settings)
    compatibility = read_json(runtime / "qadam_compatibility_reader_audit.json")
    architecture = read_json(runtime / "qadam_architecture_inventory.json")
    compatibility_records = compatibility.get("records")
    if not isinstance(compatibility_records, list):
        compatibility_records = []
    architecture_records = architecture.get("records")
    if not isinstance(architecture_records, list):
        architecture_records = []
    legacy_components = [
        {
            "path": record.get("path"),
            "state": "compatibility_only_not_for_new_imports",
            "new_import_allowed": False,
            "new_canonical_artifact_write_allowed": False,
            "deletion_allowed": False,
            "replacement": "canonical_contract_or_declared_compatibility_reader",
        }
        for record in architecture_records
        if "compatibility_generation" in record.get("classifications", [])
    ]
    canonical_runtime_collisions = [
        artifact
        for artifact in CANONICAL_ARTIFACTS.values()
        if (runtime / artifact).exists()
    ]
    wave0_legacy_imports = _wave0_legacy_imports()
    return {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "qadam_legacy_quarantine_registry",
        "phase_id": PHASE_ID,
        "generated_at": now_iso(),
        "status": "legacy_paths_metadata_quarantined",
        "legacy_component_count": len(legacy_components),
        "legacy_components": legacy_components,
        "compatibility_reader_count": len(compatibility_records),
        "compatibility_readers": compatibility_records,
        "wave0_legacy_import_count": len(wave0_legacy_imports),
        "wave0_legacy_imports": wave0_legacy_imports,
        "canonical_runtime_collision_count": len(canonical_runtime_collisions),
        "canonical_runtime_collisions": canonical_runtime_collisions,
        "legacy_file_deletion_count": 0,
        "legacy_artifact_deletion_count": 0,
        "mass_deletion_allowed": False,
        "authority": authority_flags(),
    }


def _prior_check_status(settings: Settings | None = None) -> list[dict[str, Any]]:
    runtime = runtime_dir(settings)
    records: list[dict[str, Any]] = []
    for phase, filename in PRIOR_CHECK_ARTIFACTS.items():
        payload = read_json(runtime / filename)
        records.append(
            {
                "phase_id": phase,
                "artifact": f"data/runtime/{filename}",
                "exists": bool(payload),
                "status": payload.get("status"),
                "validation_error_count": len(payload.get("validation_errors", []))
                if isinstance(payload.get("validation_errors"), list)
                else None,
                "sha256": file_sha256(runtime / filename),
            }
        )
    return records


def build_behavior_diff(
    pre_baseline: dict[str, Any],
    post_baseline: dict[str, Any],
    *,
    settings: Settings | None = None,
) -> dict[str, Any]:
    runtime = runtime_dir(settings)
    characterization = read_json(runtime / "qadam_characterization_harness_checks.json")
    decision = read_json(runtime / "qadam_decision_execution_boundaries_checks.json")
    comparisons = [
        {
            "field": "root_head",
            "before": pre_baseline.get("root_worktree", {}).get("head"),
            "after": post_baseline.get("root_worktree", {}).get("head"),
        },
        {
            "field": "dashboard_head",
            "before": pre_baseline.get("dashboard_worktree", {}).get("head"),
            "after": post_baseline.get("dashboard_worktree", {}).get("head"),
        },
        {
            "field": "dashboard_renderer_sha256",
            "before": pre_baseline.get("dashboard_contract", {}).get("renderer_sha256"),
            "after": post_baseline.get("dashboard_contract", {}).get("renderer_sha256"),
        },
        {
            "field": "dashboard_routes",
            "before": pre_baseline.get("dashboard_contract", {}).get("routes"),
            "after": post_baseline.get("dashboard_contract", {}).get("routes"),
        },
        {
            "field": "research_lock_status",
            "before": pre_baseline.get("research_lock", {}).get("status"),
            "after": post_baseline.get("research_lock", {}).get("status"),
        },
        {
            "field": "paperops_watch_only_mode",
            "before": pre_baseline.get("research_lock", {}).get("paperops_watch_only_mode"),
            "after": post_baseline.get("research_lock", {}).get("paperops_watch_only_mode"),
        },
        {
            "field": "paper_trial_name",
            "before": pre_baseline.get("paper_trial", {}).get("canonical_user_facing_name"),
            "after": post_baseline.get("paper_trial", {}).get("canonical_user_facing_name"),
        },
    ]
    unexpected = [record for record in comparisons if record["before"] != record["after"]]
    expected_changes = [
        {
            "field": "root_dirty_file_inventory",
            "reason": "Wave 0 adds reviewed source and generated audit artifacts without cleaning existing changes.",
        },
        {
            "field": "dynamic_status_block",
            "reason": "DP-0 refreshes only the hash-excluded controlled status block.",
        },
        {
            "field": "legacy_dashboard_checker_debt",
            "before": pre_baseline.get("dashboard_contract", {}).get("legacy_checker_debt_count"),
            "after": post_baseline.get("dashboard_contract", {}).get("legacy_checker_debt_count"),
            "reason": "The two obsolete checks now validate the current decision-flow contract.",
        },
    ]
    return {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "qadam_post_refactor_behavior_diff",
        "generated_at": now_iso(),
        "status": "behaviorally_equivalent" if not unexpected else "unexpected_behavior_diff",
        "comparison_count": len(comparisons),
        "comparisons": comparisons,
        "unexpected_diff_count": len(unexpected),
        "unexpected_diffs": unexpected,
        "expected_change_count": len(expected_changes),
        "expected_changes": expected_changes,
        "characterization_passed": characterization.get("status") == "passed",
        "portfolio_truth_passed": characterization.get("status") == "passed",
        "paperops_equivalence_passed": decision.get("status") == "passed",
        "order_call_count": decision.get("order_call_count"),
        "broker_write_count": decision.get("broker_write_count"),
        "authority": authority_flags(),
    }


def build_plan_rebaseline(settings: Settings | None = None) -> dict[str, Any]:
    phase_status = load_or_create_phase_status(settings)
    drift = build_plan_drift(settings)
    amendments = read_jsonl(runtime_dir(settings) / "qadam_operator_ready_plan_amendments.jsonl")
    applied_ids = {
        record.get("proposal_id")
        for record in amendments
        if record.get("state") == "applied_after_explicit_review"
    }
    proposed_ids = {
        record.get("proposal_id")
        for record in amendments
        if record.get("state") == "proposed_not_applied"
    }
    outstanding = sorted(proposed_ids - applied_ids)
    phases = phase_status.get("phases", {})
    prior_wave0_passed = sum(
        phases.get(phase, {}).get("state") == "passed" for phase in PHASE_ORDER[:7]
    )
    return {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "qadam_post_refactor_plan_rebaseline",
        "generated_at": now_iso(),
        "status": "ready_to_record_rf6" if not drift.get("drift_detected") else "blocked_plan_drift",
        "plan_drift_status": drift.get("status"),
        "plan_drift_reasons": drift.get("drift_reasons", []),
        "prior_wave0_phase_pass_count": prior_wave0_passed,
        "rf6_state_before_record": phases.get("RF-6", {}).get("state"),
        "expected_next_phase_after_record": "OR-0",
        "amendment_record_count": len(amendments),
        "outstanding_amendment_count": len(outstanding),
        "outstanding_amendment_ids": outstanding,
        "automatic_normative_plan_edits": False,
        "authority": authority_flags(),
    }


def build_post_refactor_baseline(settings: Settings | None = None) -> dict[str, Any]:
    runtime = runtime_dir(settings)
    pre_baseline = read_json(runtime / BASELINE_ARTIFACT)
    post_baseline = build_refactor_baseline(settings)
    prior_checks = _prior_check_status(settings)
    return {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "qadam_post_refactor_baseline",
        "phase_id": PHASE_ID,
        "generated_at": now_iso(),
        "status": "post_refactor_baseline_ready",
        "pre_baseline_generated_at": pre_baseline.get("generated_at"),
        "post_baseline_snapshot": post_baseline,
        "prior_check_count": len(prior_checks),
        "prior_checks": prior_checks,
        "all_prior_checks_passed": all(record.get("status") == "passed" for record in prior_checks),
        "canonical_artifact_activation_count": sum(
            (runtime / artifact).exists() for artifact in CANONICAL_ARTIFACTS.values()
        ),
        "authority": authority_flags(),
    }


def validate_post_refactor_bundle(bundle: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    quarantine = bundle.get("quarantine") if isinstance(bundle.get("quarantine"), dict) else {}
    post = bundle.get("post") if isinstance(bundle.get("post"), dict) else {}
    behavior = bundle.get("behavior") if isinstance(bundle.get("behavior"), dict) else {}
    plan = bundle.get("plan") if isinstance(bundle.get("plan"), dict) else {}
    if quarantine.get("legacy_file_deletion_count") != 0:
        errors.append("rf6_legacy_file_deleted")
    if quarantine.get("legacy_artifact_deletion_count") != 0:
        errors.append("rf6_legacy_artifact_deleted")
    if quarantine.get("wave0_legacy_import_count") != 0:
        errors.append("rf6_wave0_imports_legacy_generation")
    if quarantine.get("canonical_runtime_collision_count") != 0:
        errors.append("rf6_canonical_artifact_collision")
    if post.get("all_prior_checks_passed") is not True:
        errors.append("rf6_prior_phase_check_not_passed")
    if post.get("canonical_artifact_activation_count") != 0:
        errors.append("rf6_canonical_producer_activated")
    if behavior.get("unexpected_diff_count") != 0:
        errors.append("rf6_unexpected_behavior_diff")
    if behavior.get("characterization_passed") is not True:
        errors.append("rf6_characterization_not_passed")
    if behavior.get("paperops_equivalence_passed") is not True:
        errors.append("rf6_paperops_equivalence_not_passed")
    if behavior.get("order_call_count") != 0 or behavior.get("broker_write_count") != 0:
        errors.append("rf6_order_or_broker_call_detected")
    if plan.get("plan_drift_status") != "no_drift":
        errors.append("rf6_plan_drift_detected")
    if plan.get("prior_wave0_phase_pass_count") != 7:
        errors.append("rf6_prior_wave0_phase_count_mismatch")
    errors.extend(validate_dynamic_plan_state())
    for label, payload in (
        ("quarantine", quarantine),
        ("post", post),
        ("behavior", behavior),
        ("plan", plan),
    ):
        errors.extend(validate_authority(payload.get("authority", {}), prefix=label))
    return unique_errors(errors)


def validate_negative_post_refactor_probes(bundle: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    deletion = deepcopy(bundle)
    deletion["quarantine"]["legacy_file_deletion_count"] = 1
    if "rf6_legacy_file_deleted" not in validate_post_refactor_bundle(deletion):
        errors.append("rf6_deletion_probe_not_rejected")

    drift = deepcopy(bundle)
    drift["plan"]["plan_drift_status"] = "drift_detected"
    if "rf6_plan_drift_detected" not in validate_post_refactor_bundle(drift):
        errors.append("rf6_drift_probe_not_rejected")

    call = deepcopy(bundle)
    call["behavior"]["broker_write_count"] = 1
    if "rf6_order_or_broker_call_detected" not in validate_post_refactor_bundle(call):
        errors.append("rf6_broker_probe_not_rejected")
    return unique_errors(errors)


def build_and_write_post_refactor_baseline(
    settings: Settings | None = None,
) -> tuple[dict[str, Any], dict[str, Any], list[str]]:
    # Refresh each Wave 0 audit against the final source layout before comparing behavior.
    build_and_write_architecture_audit(settings)
    build_and_write_characterization_harness(settings)
    build_and_write_canonical_contracts(settings)
    build_and_write_research_boundaries(settings)
    build_and_write_decision_execution_boundaries(settings)

    runtime = runtime_dir(settings)
    pre_baseline = read_json(runtime / BASELINE_ARTIFACT)
    quarantine = build_legacy_quarantine_registry(settings)
    post = build_post_refactor_baseline(settings)
    behavior = build_behavior_diff(
        pre_baseline,
        post["post_baseline_snapshot"],
        settings=settings,
    )
    plan = build_plan_rebaseline(settings)
    bundle = {"quarantine": quarantine, "post": post, "behavior": behavior, "plan": plan}
    errors = validate_post_refactor_bundle(bundle)
    errors.extend(validate_negative_post_refactor_probes(bundle))
    errors = unique_errors(errors)
    checks = {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "qadam_post_refactor_baseline_checks",
        "phase_id": PHASE_ID,
        "generated_at": now_iso(),
        "status": "passed" if not errors else "blocked",
        "validation_errors": errors,
        "prior_wave0_phase_pass_count": plan["prior_wave0_phase_pass_count"],
        "unexpected_behavior_diff_count": behavior["unexpected_diff_count"],
        "legacy_file_deletion_count": quarantine["legacy_file_deletion_count"],
        "canonical_runtime_collision_count": quarantine["canonical_runtime_collision_count"],
        "order_call_count": behavior["order_call_count"],
        "broker_write_count": behavior["broker_write_count"],
        "negative_probe_count": 3,
        "next_phase": "OR-0",
        "authority": authority_flags(),
    }
    store: AtomicArtifactStore[dict[str, Any]] = AtomicArtifactStore(runtime)
    store.write_json(QUARANTINE_ARTIFACT, quarantine)
    store.write_json(POST_BASELINE_ARTIFACT, post)
    store.write_json(BEHAVIOR_DIFF_ARTIFACT, behavior)
    store.write_json(PLAN_REBASELINE_ARTIFACT, plan)
    store.write_json(CHECK_ARTIFACT, checks)
    return bundle, checks, errors
