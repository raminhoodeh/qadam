#!/usr/bin/env python3
"""Validate Q6-3 closed-trade outcome normalization."""

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
from orchestrator.phase6_closed_trade_outcome import (  # noqa: E402
    SOURCE_INTAKE_REF,
    build_phase6_closed_trade_outcome,
    phase6_closed_trade_outcome_paths,
    validate_phase6_closed_trade_outcome,
    write_phase6_closed_trade_outcome,
)
from orchestrator.phase6_learning_source_intake import (  # noqa: E402
    SOURCE_REF_PATHS,
    validate_phase6_learning_source_intake,
)
from orchestrator.phase6_readiness import (  # noqa: E402
    build_phase6_readiness,
    validate_phase6_readiness,
)


def _repo_root(settings: Settings) -> Path:
    return Path(settings.runtime_dir).parent.parent


def _source_refs() -> list[str]:
    refs = [
        ref
        for ref in SOURCE_REF_PATHS.values()
        if ref.startswith("data/runtime/")
        and not ref.startswith("data/runtime/phase6_closed_trade_outcome")
    ]
    refs.append(SOURCE_INTAKE_REF)
    return sorted(set(refs))


def _file_hashes(settings: Settings) -> dict[str, str | None]:
    root = _repo_root(settings)
    hashes: dict[str, str | None] = {}
    for ref in _source_refs():
        path = root / ref
        if not path.exists():
            hashes[ref] = None
            continue
        hashes[ref] = hashlib.sha256(path.read_bytes()).hexdigest()
    return hashes


def _read_json(path: Path) -> dict[str, object]:
    import json

    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> int:
    errors: list[str] = []
    settings = Settings.from_env()
    before_hashes = _file_hashes(settings)
    output_path, history_path, event_log_path = phase6_closed_trade_outcome_paths(settings)
    if event_log_path.exists():
        event_log_path.unlink()

    readiness = build_phase6_readiness(settings=settings)
    readiness_errors = validate_phase6_readiness(readiness)
    schema_summary = phase6_artifact_bundle_summary(build_phase6_sample_artifacts())
    source_intake = _read_json(_repo_root(settings) / SOURCE_INTAKE_REF)
    source_intake_errors = (
        validate_phase6_learning_source_intake(source_intake) if source_intake else []
    )

    artifact = build_phase6_closed_trade_outcome(settings=settings)
    output_path, history_path, event_log_path, written = write_phase6_closed_trade_outcome(
        artifact,
        settings=settings,
        record_event=True,
        event_log_path=event_log_path,
    )
    validation_errors = validate_phase6_closed_trade_outcome(written)
    replay = EventLog(event_log_path, echo=False).replay()
    after_hashes = _file_hashes(settings)
    mutated_refs = [
        ref for ref, before_hash in before_hashes.items() if after_hashes.get(ref) != before_hash
    ]

    missing_record_probe = deepcopy(written)
    missing_record_probe["outcome_record_count"] = 0
    missing_record_probe["outcome_records"] = []
    missing_record_errors = validate_phase6_closed_trade_outcome(missing_record_probe)

    learning_write_probe = deepcopy(written)
    learning_write_probe["learning_write_allowed"] = True
    learning_write_probe["learning_write_created"] = True
    learning_write_probe["phase6_learning_write_allowed"] = True
    learning_write_probe["phase6_learning_write_allowed_count"] = 1
    learning_write_errors = validate_phase6_closed_trade_outcome(learning_write_probe)

    knowledge_graph_probe = deepcopy(written)
    knowledge_graph_probe["knowledge_graph_write_created"] = True
    knowledge_graph_probe["phase6_knowledge_graph_write_allowed"] = True
    knowledge_graph_probe["phase6_knowledge_graph_write_allowed_count"] = 1
    knowledge_graph_errors = validate_phase6_closed_trade_outcome(knowledge_graph_probe)

    broker_truth_probe = deepcopy(written)
    broker_truth_probe["broker_truth_separated"] = False
    broker_truth = broker_truth_probe["outcome_records"][0]["truth_partition"]["broker_truth"]
    broker_truth["broker_truth_accepted_as_fill_truth"] = True
    broker_truth["broker_post_called"] = True
    broker_truth_errors = validate_phase6_closed_trade_outcome(broker_truth_probe)

    invented_catalyst_probe = deepcopy(written)
    invented_catalyst_probe["outcome_records"][0]["thesis"]["actual_catalyst"] = (
        "invented_catalyst_without_source"
    )
    invented_catalyst_errors = validate_phase6_closed_trade_outcome(invented_catalyst_probe)

    missing_deferred_probe = deepcopy(written)
    missing_deferred_probe["outcome_records"][0]["deferred_fields"] = []
    missing_deferred_probe["outcome_records"][0]["deferred_field_count"] = 0
    missing_deferred_probe["deferred_field_count"] = 0
    missing_deferred_errors = validate_phase6_closed_trade_outcome(missing_deferred_probe)

    local_path_probe = deepcopy(written)
    local_path_probe["provenance"]["source_refs"][0] = (
        "/Users/raminhoodeh/Desktop/qadam/data/runtime/private.json"
    )
    local_path_errors = validate_phase6_closed_trade_outcome(local_path_probe)

    source_mutation_probe = deepcopy(written)
    source_mutation_probe["phase5_source_artifacts_mutated"] = True
    source_mutation_errors = validate_phase6_closed_trade_outcome(source_mutation_probe)

    proof_credit_probe = deepcopy(written)
    proof_credit_probe["phase7_proof_credit_allowed"] = True
    proof_credit_probe["phase7_proof_credit_allowed_count"] = 1
    proof_credit_probe["outcome_records"][0]["realized_outcome"][
        "phase7_proof_credit_allowed"
    ] = True
    proof_credit_errors = validate_phase6_closed_trade_outcome(proof_credit_probe)

    source_intake_status_probe = deepcopy(written)
    source_intake_status_probe["source_intake_status"] = "blocked"
    source_intake_status_errors = validate_phase6_closed_trade_outcome(
        source_intake_status_probe
    )

    if readiness_errors:
        errors.extend(readiness_errors)
    if schema_summary["status"] != "ok":
        errors.append("phase6_artifact_schema_not_valid")
    if source_intake_errors:
        errors.extend(source_intake_errors)
    if validation_errors:
        errors.extend(validation_errors)
    if mutated_refs:
        errors.append("q6_3_source_artifacts_mutated")
    if written["status"] != "read_only":
        errors.append("closed_trade_outcome_not_read_only")
    if written["outcome_record_count"] != 1:
        errors.append("closed_trade_outcome_record_count_invalid")
    if written["outcome_status"] != "closed_trade_outcome_normalized":
        errors.append("closed_trade_outcome_status_not_normalized")
    if written["closed_trade_ref"] != "q5e7-closed-trade-crude_oil_energy_security_disruption":
        errors.append("closed_trade_ref_unexpected")
    if written["learning_write_allowed"] is not False:
        errors.append("learning_write_allowed")
    if written["knowledge_graph_write_created"] is not False:
        errors.append("knowledge_graph_write_created")
    if written["broker_truth_separated"] is not True:
        errors.append("broker_truth_not_separated")
    if written["phase5_source_artifacts_mutated"] is not False:
        errors.append("phase5_source_artifacts_mutated")
    if written["phase7_proof_credit_allowed"] is not False:
        errors.append("phase7_proof_credit_allowed")
    if written["unsafe_write_counter_total"] != 0:
        errors.append("unsafe_write_counter_nonzero")
    if written["blocker_count"] != 0:
        errors.append("closed_trade_outcome_blockers_present")
    if written["event_log_written"] is not True:
        errors.append("event_log_not_written")
    if written["event_log_event_count"] != 1:
        errors.append("event_log_count_mismatch")
    if replay["total_events"] != 1:
        errors.append("event_replay_count_mismatch")
    if "closed_trade_outcome_record_missing" not in missing_record_errors:
        errors.append("missing_outcome_record_probe_not_rejected")
    if "learning_write_allowed" not in learning_write_errors:
        errors.append("learning_write_allowed_probe_not_rejected")
    if "authority_enabled:phase6_learning_write_allowed" not in learning_write_errors:
        errors.append("learning_write_authority_probe_not_rejected")
    if (
        "closed_trade_outcome_write_enabled:knowledge_graph_write_created"
        not in knowledge_graph_errors
    ):
        errors.append("knowledge_graph_probe_not_rejected")
    if "broker_truth_not_separated" not in broker_truth_errors:
        errors.append("broker_truth_separation_probe_not_rejected")
    if "broker_truth_accepted_as_fill_truth" not in broker_truth_errors:
        errors.append("broker_truth_fill_probe_not_rejected")
    if "actual_catalyst_invented" not in invented_catalyst_errors:
        errors.append("invented_catalyst_probe_not_rejected")
    if "deferred_fields_missing" not in missing_deferred_errors:
        errors.append("missing_deferred_probe_not_rejected")
    if "provenance_local_path_leak" not in local_path_errors:
        errors.append("local_path_probe_not_rejected")
    if "closed_trade_outcome_write_enabled:phase5_source_artifacts_mutated" not in (
        source_mutation_errors
    ):
        errors.append("source_mutation_probe_not_rejected")
    if "phase7_proof_credit_allowed" not in proof_credit_errors:
        errors.append("proof_credit_probe_not_rejected")
    if "source_intake_not_read_only" not in source_intake_status_errors:
        errors.append("source_intake_status_probe_not_rejected")

    print(f"phase6_closed_trade_outcome_status={written['status']}")
    print(f"phase6_closed_trade_outcome_artifact_path={output_path}")
    print(f"phase6_closed_trade_outcome_history_path={history_path}")
    print(f"phase6_closed_trade_outcome_event_log_path={event_log_path}")
    print(f"phase6_closed_trade_outcome_closed_trade_ref={written['closed_trade_ref']}")
    print(f"phase6_closed_trade_outcome_outcome_status={written['outcome_status']}")
    print(f"phase6_closed_trade_outcome_record_count={written['outcome_record_count']}")
    print(
        "phase6_closed_trade_outcome_broker_truth_separated="
        f"{written['broker_truth_separated']}"
    )
    print(
        "phase6_closed_trade_outcome_unknown_field_count="
        f"{written['unknown_field_count']}"
    )
    print(
        "phase6_closed_trade_outcome_deferred_field_count="
        f"{written['deferred_field_count']}"
    )
    print(
        "phase6_closed_trade_outcome_learning_write_allowed="
        f"{written['learning_write_allowed']}"
    )
    print(
        "phase6_closed_trade_outcome_knowledge_graph_write_created="
        f"{written['knowledge_graph_write_created']}"
    )
    print(
        "phase6_closed_trade_outcome_phase5_source_artifacts_mutated="
        f"{written['phase5_source_artifacts_mutated']}"
    )
    print(
        "phase6_closed_trade_outcome_source_hash_mutation_count="
        f"{len(mutated_refs)}"
    )
    print(
        "phase6_closed_trade_outcome_phase7_proof_credit_allowed="
        f"{written['phase7_proof_credit_allowed']}"
    )
    print(
        "phase6_closed_trade_outcome_unsafe_write_counter_total="
        f"{written['unsafe_write_counter_total']}"
    )
    print(f"phase6_closed_trade_outcome_blocker_count={written['blocker_count']}")
    print(
        "phase6_closed_trade_outcome_event_log_replay_total_events="
        f"{replay['total_events']}"
    )
    print(f"phase6_closed_trade_outcome_readiness_error_count={len(readiness_errors)}")
    print(f"phase6_closed_trade_outcome_schema_summary_status={schema_summary['status']}")
    print(
        "phase6_closed_trade_outcome_source_intake_error_count="
        f"{len(source_intake_errors)}"
    )
    print(
        "phase6_closed_trade_outcome_missing_record_probe_error_count="
        f"{len(missing_record_errors)}"
    )
    print(
        "phase6_closed_trade_outcome_learning_write_probe_error_count="
        f"{len(learning_write_errors)}"
    )
    print(
        "phase6_closed_trade_outcome_knowledge_graph_probe_error_count="
        f"{len(knowledge_graph_errors)}"
    )
    print(
        "phase6_closed_trade_outcome_broker_truth_probe_error_count="
        f"{len(broker_truth_errors)}"
    )
    print(
        "phase6_closed_trade_outcome_invented_catalyst_probe_error_count="
        f"{len(invented_catalyst_errors)}"
    )
    print(
        "phase6_closed_trade_outcome_missing_deferred_probe_error_count="
        f"{len(missing_deferred_errors)}"
    )
    print(
        "phase6_closed_trade_outcome_local_path_probe_error_count="
        f"{len(local_path_errors)}"
    )
    print(
        "phase6_closed_trade_outcome_source_mutation_probe_error_count="
        f"{len(source_mutation_errors)}"
    )
    print(
        "phase6_closed_trade_outcome_proof_credit_probe_error_count="
        f"{len(proof_credit_errors)}"
    )
    print(
        "phase6_closed_trade_outcome_source_intake_status_probe_error_count="
        f"{len(source_intake_status_errors)}"
    )
    print(f"phase6_closed_trade_outcome_next_stage={written['recommended_next_stage']}")
    print("phase6_closed_trade_outcome_boundary=" + written["boundary"])

    if errors:
        for error in sorted(set(errors)):
            print(f"phase6_closed_trade_outcome_error={error}")
        print("phase6_closed_trade_outcome_check=failed")
        return 1

    print("phase6_closed_trade_outcome_check=ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
