#!/usr/bin/env python3
"""Validate Q6-2 read-only learning source intake."""

from __future__ import annotations

from copy import deepcopy
import hashlib
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from orchestrator.config import Settings  # noqa: E402
from orchestrator.event_log import EventLog  # noqa: E402
from orchestrator.phase6_artifacts import (  # noqa: E402
    build_phase6_sample_artifacts,
    phase6_artifact_bundle_summary,
)
from orchestrator.phase6_learning_source_intake import (  # noqa: E402
    REQUIRED_SOURCE_KEYS,
    SOURCE_REF_PATHS,
    build_phase6_learning_source_intake,
    phase6_learning_source_intake_paths,
    validate_phase6_learning_source_intake,
    write_phase6_learning_source_intake,
)
from orchestrator.phase6_readiness import (  # noqa: E402
    build_phase6_readiness,
    validate_phase6_readiness,
)


def _repo_root(settings: Settings) -> Path:
    return Path(settings.runtime_dir).parent.parent


def _phase5_source_refs() -> list[str]:
    return [
        ref
        for key, ref in SOURCE_REF_PATHS.items()
        if key not in {"phase6_readiness", "phase6_artifact_schema"}
        and ref.startswith("data/runtime/")
    ]


def _file_hashes(settings: Settings) -> dict[str, str | None]:
    root = _repo_root(settings)
    hashes: dict[str, str | None] = {}
    for ref in _phase5_source_refs():
        path = root / ref
        if not path.exists():
            hashes[ref] = None
            continue
        hashes[ref] = hashlib.sha256(path.read_bytes()).hexdigest()
    return hashes


def main() -> int:
    errors: list[str] = []
    settings = Settings.from_env()
    before_hashes = _file_hashes(settings)
    output_path, history_path, event_log_path = phase6_learning_source_intake_paths(settings)
    if event_log_path.exists():
        event_log_path.unlink()

    readiness = build_phase6_readiness(settings=settings)
    readiness_errors = validate_phase6_readiness(readiness)
    schema_summary = phase6_artifact_bundle_summary(build_phase6_sample_artifacts())

    artifact = build_phase6_learning_source_intake(settings=settings)
    output_path, history_path, event_log_path, written = write_phase6_learning_source_intake(
        artifact,
        settings=settings,
        record_event=True,
        event_log_path=event_log_path,
    )
    validation_errors = validate_phase6_learning_source_intake(written)
    replay = EventLog(event_log_path, echo=False).replay()
    after_hashes = _file_hashes(settings)
    phase5_mutated_refs = [
        ref for ref, before_hash in before_hashes.items() if after_hashes.get(ref) != before_hash
    ]

    missing_due_probe = deepcopy(written)
    missing_due_probe["postmortem_due_count"] = 0
    missing_due_probe["postmortem_due_records"] = []
    missing_due_errors = validate_phase6_learning_source_intake(missing_due_probe)

    learning_write_probe = deepcopy(written)
    learning_write_probe["learning_write_created"] = True
    learning_write_probe["phase6_learning_write_allowed"] = True
    learning_write_probe["phase6_learning_write_allowed_count"] = 1
    learning_write_errors = validate_phase6_learning_source_intake(learning_write_probe)

    knowledge_graph_probe = deepcopy(written)
    knowledge_graph_probe["knowledge_graph_write_created"] = True
    knowledge_graph_probe["phase6_knowledge_graph_write_allowed"] = True
    knowledge_graph_probe["phase6_knowledge_graph_write_allowed_count"] = 1
    knowledge_graph_errors = validate_phase6_learning_source_intake(knowledge_graph_probe)

    optional_fail_open_probe = deepcopy(written)
    optional_fail_open_probe["missing_optional_refs_fail_open"] = True
    optional_fail_open_errors = validate_phase6_learning_source_intake(optional_fail_open_probe)

    required_source_probe = deepcopy(written)
    required_source_probe["required_source_present_count"] = max(
        0, int(required_source_probe["required_source_present_count"]) - 1
    )
    for record in required_source_probe["source_records"]:
        if record.get("source_key") in REQUIRED_SOURCE_KEYS:
            record["present"] = False
            break
    required_source_errors = validate_phase6_learning_source_intake(required_source_probe)

    local_path_probe = deepcopy(written)
    local_path_probe["source_records"][0]["source_ref"] = (
        "/Users/raminhoodeh/Desktop/qadam/data/runtime/private.json"
    )
    local_path_errors = validate_phase6_learning_source_intake(local_path_probe)

    phase5_mutation_probe = deepcopy(written)
    phase5_mutation_probe["phase5_source_artifacts_mutated"] = True
    phase5_mutation_errors = validate_phase6_learning_source_intake(phase5_mutation_probe)

    proof_credit_probe = deepcopy(written)
    proof_credit_probe["phase7_proof_credit_allowed"] = True
    proof_credit_probe["phase7_proof_credit_allowed_count"] = 1
    proof_credit_errors = validate_phase6_learning_source_intake(proof_credit_probe)

    if readiness_errors:
        errors.extend(readiness_errors)
    if schema_summary["status"] != "ok":
        errors.append("phase6_artifact_schema_not_valid")
    if validation_errors:
        errors.extend(validation_errors)
    if phase5_mutated_refs:
        errors.append("phase5_source_artifacts_mutated")
    if written["status"] != "read_only":
        errors.append("learning_source_intake_not_read_only")
    if written["postmortem_due_count"] < 1:
        errors.append("postmortem_due_missing")
    if written["source_inventory_write_allowed"] is not False:
        errors.append("source_inventory_write_allowed")
    if written["learning_write_created"] is not False:
        errors.append("learning_write_created")
    if written["knowledge_graph_write_created"] is not False:
        errors.append("knowledge_graph_write_created")
    if written["postmortem_draft_created"] is not False:
        errors.append("postmortem_draft_created")
    if written["phase5_source_artifacts_mutated"] is not False:
        errors.append("phase5_mutation_flag_true")
    if written["required_source_present_count"] != written["required_source_count"]:
        errors.append("required_sources_missing")
    if written["blocker_count"] != 0:
        errors.append("learning_source_intake_blockers_present")
    if written["phase7_proof_credit_allowed"] is not False:
        errors.append("phase7_proof_credit_allowed")
    if written["unsafe_write_counter_total"] != 0:
        errors.append("unsafe_write_counter_nonzero")
    if written["event_log_written"] is not True:
        errors.append("event_log_not_written")
    if written["event_log_event_count"] != 1:
        errors.append("event_log_count_mismatch")
    if replay["total_events"] != 1:
        errors.append("event_replay_count_mismatch")
    if "postmortem_due_marker_missing" not in missing_due_errors:
        errors.append("missing_due_probe_not_rejected")
    if "learning_source_intake_write_enabled:learning_write_created" not in learning_write_errors:
        errors.append("learning_write_probe_not_rejected")
    if "authority_enabled:phase6_learning_write_allowed" not in learning_write_errors:
        errors.append("learning_write_authority_probe_not_rejected")
    if (
        "learning_source_intake_write_enabled:knowledge_graph_write_created"
        not in knowledge_graph_errors
    ):
        errors.append("knowledge_graph_probe_not_rejected")
    if "missing_optional_refs_fail_open" not in optional_fail_open_errors:
        errors.append("optional_fail_open_probe_not_rejected")
    if "required_source_missing" not in required_source_errors:
        errors.append("required_source_probe_not_rejected")
    if not any(error.startswith("source_ref_local_path") for error in local_path_errors):
        errors.append("local_path_probe_not_rejected")
    if "phase5_source_artifacts_mutated" not in phase5_mutation_errors:
        errors.append("phase5_mutation_probe_not_rejected")
    if "phase7_proof_credit_allowed" not in proof_credit_errors:
        errors.append("proof_credit_probe_not_rejected")

    print(f"phase6_learning_source_intake_status={written['status']}")
    print(f"phase6_learning_source_intake_artifact_path={output_path}")
    print(f"phase6_learning_source_intake_history_path={history_path}")
    print(f"phase6_learning_source_intake_event_log_path={event_log_path}")
    print(f"phase6_learning_source_intake_postmortem_due_count={written['postmortem_due_count']}")
    print(f"phase6_learning_source_intake_source_ref_count={written['source_ref_count']}")
    print(
        "phase6_learning_source_intake_required_source_present_count="
        f"{written['required_source_present_count']}"
    )
    print(
        "phase6_learning_source_intake_required_source_count="
        f"{written['required_source_count']}"
    )
    print(
        "phase6_learning_source_intake_optional_source_present_count="
        f"{written['optional_source_present_count']}"
    )
    print(
        "phase6_learning_source_intake_optional_ref_missing_count="
        f"{written['optional_ref_missing_count']}"
    )
    print(
        "phase6_learning_source_intake_source_inventory_write_allowed="
        f"{written['source_inventory_write_allowed']}"
    )
    print(
        "phase6_learning_source_intake_learning_write_created="
        f"{written['learning_write_created']}"
    )
    print(
        "phase6_learning_source_intake_knowledge_graph_write_created="
        f"{written['knowledge_graph_write_created']}"
    )
    print(
        "phase6_learning_source_intake_phase5_source_artifacts_mutated="
        f"{written['phase5_source_artifacts_mutated']}"
    )
    print(
        "phase6_learning_source_intake_phase5_hash_mutation_count="
        f"{len(phase5_mutated_refs)}"
    )
    print(
        "phase6_learning_source_intake_phase7_proof_credit_allowed="
        f"{written['phase7_proof_credit_allowed']}"
    )
    print(
        "phase6_learning_source_intake_unsafe_write_counter_total="
        f"{written['unsafe_write_counter_total']}"
    )
    print(f"phase6_learning_source_intake_blocker_count={written['blocker_count']}")
    print(
        "phase6_learning_source_intake_event_log_replay_total_events="
        f"{replay['total_events']}"
    )
    print(f"phase6_learning_source_intake_readiness_error_count={len(readiness_errors)}")
    print(f"phase6_learning_source_intake_schema_summary_status={schema_summary['status']}")
    print(
        "phase6_learning_source_intake_missing_due_probe_error_count="
        f"{len(missing_due_errors)}"
    )
    print(
        "phase6_learning_source_intake_learning_write_probe_error_count="
        f"{len(learning_write_errors)}"
    )
    print(
        "phase6_learning_source_intake_knowledge_graph_probe_error_count="
        f"{len(knowledge_graph_errors)}"
    )
    print(
        "phase6_learning_source_intake_optional_fail_open_probe_error_count="
        f"{len(optional_fail_open_errors)}"
    )
    print(
        "phase6_learning_source_intake_required_source_probe_error_count="
        f"{len(required_source_errors)}"
    )
    print(
        "phase6_learning_source_intake_local_path_probe_error_count="
        f"{len(local_path_errors)}"
    )
    print(
        "phase6_learning_source_intake_phase5_mutation_probe_error_count="
        f"{len(phase5_mutation_errors)}"
    )
    print(
        "phase6_learning_source_intake_proof_credit_probe_error_count="
        f"{len(proof_credit_errors)}"
    )
    print(f"phase6_learning_source_intake_next_stage={written['recommended_next_stage']}")
    print("phase6_learning_source_intake_boundary=" + written["boundary"])

    if errors:
        for error in sorted(set(errors)):
            print(f"phase6_learning_source_intake_error={error}")
        print("phase6_learning_source_intake_check=failed")
        return 1

    print("phase6_learning_source_intake_check=ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
