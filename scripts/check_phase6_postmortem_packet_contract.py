#!/usr/bin/env python3
"""Validate Q6-4 postmortem packet contract."""

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
    PHASE6_CLOSED_TRADE_OUTCOME_RUNTIME_ARTIFACT,
    validate_phase6_closed_trade_outcome,
)
from orchestrator.phase6_postmortem_packets import (  # noqa: E402
    POSTMORTEM_PACKET_SECTIONS,
    SOURCE_OUTCOME_ARTIFACT_REF,
    build_phase6_postmortem_packet_contract,
    build_postmortem_packet_validation_fixture,
    phase6_postmortem_packet_contract_paths,
    validate_phase6_postmortem_packet_contract,
    validate_postmortem_packet_payload,
    write_phase6_postmortem_packet_contract,
)
from orchestrator.phase6_readiness import (  # noqa: E402
    build_phase6_readiness,
    validate_phase6_readiness,
)


SOURCE_OUTCOME_REF = f"data/runtime/{PHASE6_CLOSED_TRADE_OUTCOME_RUNTIME_ARTIFACT}"


def _repo_root(settings: Settings) -> Path:
    return Path(settings.runtime_dir).parent.parent


def _source_refs() -> list[str]:
    return [
        "data/runtime/phase6_learning_source_intake.json",
        SOURCE_OUTCOME_REF,
        SOURCE_OUTCOME_ARTIFACT_REF,
        "data/runtime/phase5_guarded_closed_trade.json",
        "data/runtime/phase5_guarded_postmortem_due.json",
        "data/runtime/phase5_paper_order_staging_gate.json",
        "data/runtime/phase5_guarded_paper_submit_receipt.json",
        "data/runtime/phase5_position_monitor.json",
        "data/runtime/phase5_risk_sizing_reviews.json",
        "data/runtime/phase5_approval_policy_decisions.json",
        "data/runtime/phase5_execution_adapter_status.json",
        "data/runtime/signal_integrity_reviews.jsonl",
        "data/runtime/cockpit-status.json",
        "data/runtime/preference_shadow_context.json",
        "data/runtime/preference_provenance_source_quorum.json",
        "data/runtime/preference_source_promotion_decisions.json",
    ]


def _file_hashes(settings: Settings) -> dict[str, str | None]:
    root = _repo_root(settings)
    hashes: dict[str, str | None] = {}
    for ref in sorted(set(_source_refs())):
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
    output_path, history_path, event_log_path = phase6_postmortem_packet_contract_paths(
        settings
    )
    if event_log_path.exists():
        event_log_path.unlink()

    readiness = build_phase6_readiness(settings=settings)
    readiness_errors = validate_phase6_readiness(readiness)
    schema_summary = phase6_artifact_bundle_summary(build_phase6_sample_artifacts())
    outcome = _read_json(_repo_root(settings) / SOURCE_OUTCOME_REF)
    outcome_errors = validate_phase6_closed_trade_outcome(outcome) if outcome else []

    artifact = build_phase6_postmortem_packet_contract(settings=settings)
    output_path, history_path, event_log_path, written = write_phase6_postmortem_packet_contract(
        artifact,
        settings=settings,
        record_event=True,
        event_log_path=event_log_path,
    )
    validation_errors = validate_phase6_postmortem_packet_contract(written)
    replay = EventLog(event_log_path, echo=False).replay()
    after_hashes = _file_hashes(settings)
    mutated_refs = [
        ref for ref, before_hash in before_hashes.items() if after_hashes.get(ref) != before_hash
    ]

    valid_fixture = build_postmortem_packet_validation_fixture(written)
    valid_fixture_errors = validate_postmortem_packet_payload(valid_fixture, written)

    missing_outcome_probe = deepcopy(valid_fixture)
    missing_outcome_probe["source_outcome_ref"] = None
    missing_outcome_errors = validate_postmortem_packet_payload(missing_outcome_probe, written)

    uncited_conclusion_probe = deepcopy(valid_fixture)
    target_assertion = uncited_conclusion_probe["sections"][0]["assertions"][0]
    target_assertion["source_refs"] = []
    target_assertion["conclusion"] = True
    target_assertion["is_hypothesis"] = False
    uncited_conclusion_errors = validate_postmortem_packet_payload(
        uncited_conclusion_probe,
        written,
    )

    narrative_only_probe = deepcopy(valid_fixture)
    narrative_only_probe["narrative_only"] = True
    narrative_only_probe["sections"] = []
    narrative_only_probe["narrative_body"] = "This is a prose-only postmortem."
    narrative_only_errors = validate_postmortem_packet_payload(narrative_only_probe, written)

    missing_section_probe = deepcopy(valid_fixture)
    missing_section_probe["sections"] = [
        section
        for section in missing_section_probe["sections"]
        if section.get("section_key") != "source_quality"
    ]
    missing_section_errors = validate_postmortem_packet_payload(missing_section_probe, written)

    local_path_probe = deepcopy(valid_fixture)
    local_path_probe["sections"][0]["assertions"][0]["source_refs"] = [
        "/Users/raminhoodeh/Desktop/qadam/data/runtime/private.json"
    ]
    local_path_errors = validate_postmortem_packet_payload(local_path_probe, written)

    hypothesis_probe = deepcopy(valid_fixture)
    hypothesis_assertion = hypothesis_probe["sections"][0]["assertions"][0]
    hypothesis_assertion["source_refs"] = []
    hypothesis_assertion["is_hypothesis"] = True
    hypothesis_assertion["assertion_kind"] = "hypothesis"
    hypothesis_assertion["hypothesis_reason"] = "Fixture hypothesis for validator coverage."
    hypothesis_assertion["conclusion"] = False
    hypothesis_assertion["review_required"] = True
    hypothesis_errors = validate_postmortem_packet_payload(hypothesis_probe, written)

    hidden_write_probe = deepcopy(written)
    hidden_write_probe["postmortem_draft_created"] = True
    hidden_write_probe["learning_write_created"] = True
    hidden_write_probe["knowledge_graph_write_created"] = True
    hidden_write_probe["model_weight_update_created"] = True
    hidden_write_probe["trust_score_update_created"] = True
    hidden_write_probe["policy_mutation_created"] = True
    hidden_write_probe["strategy_mutation_created"] = True
    hidden_write_probe["phase6_learning_write_allowed"] = True
    hidden_write_probe["phase6_learning_write_allowed_count"] = 1
    hidden_write_errors = validate_phase6_postmortem_packet_contract(hidden_write_probe)

    contract_narrative_probe = deepcopy(written)
    contract_narrative_probe["narrative_only_allowed"] = True
    contract_narrative_errors = validate_phase6_postmortem_packet_contract(
        contract_narrative_probe
    )

    contract_missing_outcome_probe = deepcopy(written)
    contract_missing_outcome_probe["source_outcome_ref"] = None
    contract_missing_outcome_errors = validate_phase6_postmortem_packet_contract(
        contract_missing_outcome_probe
    )

    proof_credit_probe = deepcopy(written)
    proof_credit_probe["phase7_proof_credit_allowed"] = True
    proof_credit_probe["phase7_proof_credit_allowed_count"] = 1
    proof_credit_errors = validate_phase6_postmortem_packet_contract(proof_credit_probe)

    if readiness_errors:
        errors.extend(readiness_errors)
    if schema_summary["status"] != "ok":
        errors.append("phase6_artifact_schema_not_valid")
    if outcome_errors:
        errors.extend(outcome_errors)
    if validation_errors:
        errors.extend(validation_errors)
    if mutated_refs:
        errors.append("q6_4_source_artifacts_mutated")
    if valid_fixture_errors:
        errors.append("valid_packet_fixture_rejected")
    if written["status"] != "schema_only":
        errors.append("postmortem_packet_contract_not_schema_only")
    if written["packet_section_count"] != len(POSTMORTEM_PACKET_SECTIONS):
        errors.append("postmortem_packet_section_count_invalid")
    if written["assertion_source_refs_required"] is not True:
        errors.append("assertion_source_refs_not_required")
    if written["uncited_conclusion_allowed"] is not False:
        errors.append("uncited_conclusion_allowed")
    if written["narrative_only_allowed"] is not False:
        errors.append("narrative_only_allowed")
    if written["postmortem_draft_created"] is not False:
        errors.append("postmortem_draft_created")
    if written["learning_write_created"] is not False:
        errors.append("learning_write_created")
    if written["knowledge_graph_write_created"] is not False:
        errors.append("knowledge_graph_write_created")
    if written["phase7_proof_credit_allowed"] is not False:
        errors.append("phase7_proof_credit_allowed")
    if written["unsafe_write_counter_total"] != 0:
        errors.append("unsafe_write_counter_nonzero")
    if written["blocker_count"] != 0:
        errors.append("postmortem_packet_contract_blockers_present")
    if written["event_log_written"] is not True:
        errors.append("event_log_not_written")
    if written["event_log_event_count"] != 1:
        errors.append("event_log_count_mismatch")
    if replay["total_events"] != 1:
        errors.append("event_replay_count_mismatch")
    if "packet_missing_outcome_ref" not in missing_outcome_errors:
        errors.append("missing_outcome_probe_not_rejected")
    if "uncited_conclusion" not in uncited_conclusion_errors:
        errors.append("uncited_conclusion_probe_not_rejected")
    if "narrative_only_packet" not in narrative_only_errors:
        errors.append("narrative_only_probe_not_rejected")
    if "packet_required_section_missing:source_quality" not in missing_section_errors:
        errors.append("missing_section_probe_not_rejected")
    if "packet_assertion_local_source_ref" not in local_path_errors:
        errors.append("local_path_probe_not_rejected")
    if hypothesis_errors:
        errors.append("hypothesis_probe_rejected")
    if "postmortem_packet_contract_write_enabled:learning_write_created" not in hidden_write_errors:
        errors.append("hidden_learning_write_probe_not_rejected")
    if (
        "postmortem_packet_contract_write_enabled:knowledge_graph_write_created"
        not in hidden_write_errors
    ):
        errors.append("hidden_knowledge_graph_probe_not_rejected")
    if "authority_enabled:phase6_learning_write_allowed" not in hidden_write_errors:
        errors.append("hidden_authority_probe_not_rejected")
    if "narrative_only_allowed" not in contract_narrative_errors:
        errors.append("contract_narrative_probe_not_rejected")
    if "source_outcome_ref_missing" not in contract_missing_outcome_errors:
        errors.append("contract_missing_outcome_probe_not_rejected")
    if "phase7_proof_credit_allowed" not in proof_credit_errors:
        errors.append("proof_credit_probe_not_rejected")

    print(f"phase6_postmortem_packet_contract_status={written['status']}")
    print(f"phase6_postmortem_packet_contract_artifact_path={output_path}")
    print(f"phase6_postmortem_packet_contract_history_path={history_path}")
    print(f"phase6_postmortem_packet_contract_event_log_path={event_log_path}")
    print(
        "phase6_postmortem_packet_contract_source_outcome_ref="
        f"{written['source_outcome_ref']}"
    )
    print(
        "phase6_postmortem_packet_contract_source_closed_trade_ref="
        f"{written['source_closed_trade_ref']}"
    )
    print(
        "phase6_postmortem_packet_contract_packet_section_count="
        f"{written['packet_section_count']}"
    )
    print(
        "phase6_postmortem_packet_contract_assertion_source_refs_required="
        f"{written['assertion_source_refs_required']}"
    )
    print(
        "phase6_postmortem_packet_contract_uncited_conclusion_allowed="
        f"{written['uncited_conclusion_allowed']}"
    )
    print(
        "phase6_postmortem_packet_contract_narrative_only_allowed="
        f"{written['narrative_only_allowed']}"
    )
    print(
        "phase6_postmortem_packet_contract_postmortem_draft_created="
        f"{written['postmortem_draft_created']}"
    )
    print(
        "phase6_postmortem_packet_contract_learning_write_created="
        f"{written['learning_write_created']}"
    )
    print(
        "phase6_postmortem_packet_contract_knowledge_graph_write_created="
        f"{written['knowledge_graph_write_created']}"
    )
    print(
        "phase6_postmortem_packet_contract_source_hash_mutation_count="
        f"{len(mutated_refs)}"
    )
    print(
        "phase6_postmortem_packet_contract_phase7_proof_credit_allowed="
        f"{written['phase7_proof_credit_allowed']}"
    )
    print(
        "phase6_postmortem_packet_contract_unsafe_write_counter_total="
        f"{written['unsafe_write_counter_total']}"
    )
    print(f"phase6_postmortem_packet_contract_blocker_count={written['blocker_count']}")
    print(
        "phase6_postmortem_packet_contract_event_log_replay_total_events="
        f"{replay['total_events']}"
    )
    print(
        "phase6_postmortem_packet_contract_valid_fixture_error_count="
        f"{len(valid_fixture_errors)}"
    )
    print(
        "phase6_postmortem_packet_contract_missing_outcome_probe_error_count="
        f"{len(missing_outcome_errors)}"
    )
    print(
        "phase6_postmortem_packet_contract_uncited_conclusion_probe_error_count="
        f"{len(uncited_conclusion_errors)}"
    )
    print(
        "phase6_postmortem_packet_contract_narrative_only_probe_error_count="
        f"{len(narrative_only_errors)}"
    )
    print(
        "phase6_postmortem_packet_contract_missing_section_probe_error_count="
        f"{len(missing_section_errors)}"
    )
    print(
        "phase6_postmortem_packet_contract_local_path_probe_error_count="
        f"{len(local_path_errors)}"
    )
    print(
        "phase6_postmortem_packet_contract_hypothesis_probe_error_count="
        f"{len(hypothesis_errors)}"
    )
    print(
        "phase6_postmortem_packet_contract_hidden_write_probe_error_count="
        f"{len(hidden_write_errors)}"
    )
    print(
        "phase6_postmortem_packet_contract_contract_narrative_probe_error_count="
        f"{len(contract_narrative_errors)}"
    )
    print(
        "phase6_postmortem_packet_contract_contract_missing_outcome_probe_error_count="
        f"{len(contract_missing_outcome_errors)}"
    )
    print(
        "phase6_postmortem_packet_contract_proof_credit_probe_error_count="
        f"{len(proof_credit_errors)}"
    )
    print(f"phase6_postmortem_packet_contract_readiness_error_count={len(readiness_errors)}")
    print(f"phase6_postmortem_packet_contract_schema_summary_status={schema_summary['status']}")
    print(f"phase6_postmortem_packet_contract_outcome_error_count={len(outcome_errors)}")
    print(
        "phase6_postmortem_packet_contract_next_stage="
        f"{written['recommended_next_stage']}"
    )
    print("phase6_postmortem_packet_contract_boundary=" + written["boundary"])

    if errors:
        for error in sorted(set(errors)):
            print(f"phase6_postmortem_packet_contract_error={error}")
        print("phase6_postmortem_packet_contract_check=failed")
        return 1

    print("phase6_postmortem_packet_contract_check=ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
