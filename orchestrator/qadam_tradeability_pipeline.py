"""Single canonical producer from research drafts to Akber-compatible inputs.

The compiler absorbs V3 and QEG research drafts, builds one same-generation
decision packet per accepted draft, validates the strict tradeability envelope,
and emits the sole hypothesis projection consumed by Akber and every downstream
stage. QEG-specific Akber files remain historical audit artifacts only.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from orchestrator.config import Settings
from orchestrator.qadam_canonical_contracts import AtomicArtifactStore
from orchestrator.qadam_decision_evidence_packets import (
    INTEGRITY_ARTIFACT,
    PACKETS_ARTIFACT,
    REJECTIONS_ARTIFACT as PACKET_REJECTIONS_ARTIFACT,
    SUMMARY_ARTIFACT as PACKET_SUMMARY_ARTIFACT,
    build_decision_evidence_packets_from_inputs,
    current_decision_artifacts,
    validate_decision_evidence_packets,
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
from orchestrator.qadam_tradeability_capabilities import (
    build_and_write_capability_matrix,
    uncollectable_fields_for_profile,
)
from orchestrator.qadam_tradeability_envelope import (
    CHECK_ARTIFACT,
    ENVELOPES_ARTIFACT,
    REGISTRY_ARTIFACT,
    REJECTIONS_ARTIFACT,
    SCHEMA_PATH,
    TradeabilityEnvelope,
    compile_tradeability_envelope,
    envelope_schema,
    envelope_to_hypothesis_projection,
)
from orchestrator.qadam_evidence_contracts import validate_lane_contribution
from orchestrator.qadam_qualitative_common import LANE_CONTRIBUTIONS_ARTIFACT
from orchestrator.qadam_wave_b_common import record_set_hash

SCHEMA_VERSION = "qadam_tradeability_pipeline.v1"
DRAFTS_ARTIFACT = "qadam_strategy_drafts_v3.jsonl"
LEGACY_HYPOTHESES_ARTIFACT = "qadam_strategy_hypotheses_v3.jsonl"
QEG_DRAFTS_ARTIFACT = "qadam_qeg_strategy_hypotheses.jsonl"
CANONICAL_FOUNDRY_ARTIFACT = "qadam_canonical_tradeability_foundry_summary.json"
PIPELINE_CHECK_ARTIFACT = "qadam_tradeability_pipeline_checks.json"
PIPELINE_SUMMARY_ARTIFACT = "qadam_tradeability_pipeline_summary.json"
CONTRACT_DEFECTS_ARTIFACT = "qadam_tradeability_contract_defects.jsonl"

DIRECTIONS_ARTIFACT = "qadam_direction_resolutions.jsonl"
EVENT_ARTIFACT = "qadam_current_event_triggers.jsonl"
REGIME_ARTIFACT = "qadam_current_regime_observations.jsonl"
DISLOCATION_ARTIFACT = "qadam_current_market_dislocations.jsonl"
LEGACY_FOUNDRY_ARTIFACT = "qadam_strategy_foundry_v3.json"


def _candidate_identity(row: dict[str, Any]) -> str:
    candidate = row.get("candidate_identity_material")
    candidate = candidate if isinstance(candidate, dict) else {}
    return str(candidate.get("candidate_identity_id") or "")


def _draft_priority(row: dict[str, Any], source: str) -> tuple[int, int, str]:
    evidence_class = str(row.get("evidence_class") or "")
    evidence_rank = 2 if evidence_class == "validated_paper_strategy" else 1
    source_rank = 2 if source == LANE_CONTRIBUTIONS_ARTIFACT else 1 if source == DRAFTS_ARTIFACT else 0
    return evidence_rank, source_rank, str(row.get("generated_at") or "")


def _collect_drafts(runtime: Path) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    v3_path = runtime / DRAFTS_ARTIFACT
    v3_source = DRAFTS_ARTIFACT if v3_path.is_file() else LEGACY_HYPOTHESES_ARTIFACT
    source_rows = [
        (row, v3_source)
        for row in read_jsonl(runtime / v3_source)
        if isinstance(row, dict)
    ]
    source_rows.extend(
        (row, QEG_DRAFTS_ARTIFACT)
        for row in read_jsonl(runtime / QEG_DRAFTS_ARTIFACT)
        if isinstance(row, dict)
    )
    rejections: list[dict[str, Any]] = []
    current_direction_ids = {
        str(row.get("direction_resolution_id"))
        for row in read_jsonl(runtime / DIRECTIONS_ARTIFACT)
        if isinstance(row, dict) and row.get("direction_resolution_id")
    }
    for contribution in read_jsonl(runtime / LANE_CONTRIBUTIONS_ARTIFACT):
        if not isinstance(contribution, dict):
            continue
        contribution_errors = validate_lane_contribution(contribution)
        draft = contribution.get("canonical_draft")
        if contribution_errors or not isinstance(draft, dict):
            if contribution_errors:
                rejections.append(
                    _rejection(
                        draft if isinstance(draft, dict) else contribution,
                        LANE_CONTRIBUTIONS_ARTIFACT,
                        contribution_errors,
                        defect_class="lane_contribution_contract_defect",
                    )
                )
            continue
        enriched = dict(draft)
        enriched["_lane_contribution_id"] = contribution.get("contribution_id")
        enriched["_agent_contributions"] = contribution.get("agent_contributions") or []
        enriched["_critic_receipts"] = contribution.get("critic_receipts") or []
        source_rows.append((enriched, LANE_CONTRIBUTIONS_ARTIFACT))
    generation_aligned_rows: list[tuple[dict[str, Any], str]] = []
    for row, source in source_rows:
        if str(row.get("evidence_class") or "") == "experimental_unvalidated":
            direction = row.get("direction_horizon")
            direction = direction if isinstance(direction, dict) else {}
            resolution_id = str(direction.get("direction_resolution_id") or "")
            if not resolution_id or resolution_id not in current_direction_ids:
                rejections.append(
                    _rejection(
                        row,
                        source,
                        ["stale_direction_generation_suppressed"],
                        defect_class="stale_input_generation_suppressed",
                    )
                )
                continue
        generation_aligned_rows.append((row, source))
    source_rows = generation_aligned_rows
    selected: dict[str, tuple[dict[str, Any], str]] = {}
    for row, source in source_rows:
        hypothesis_id = str(row.get("hypothesis_id") or "")
        identity = _candidate_identity(row)
        if not hypothesis_id or not identity:
            rejections.append(
                _rejection(
                    row,
                    source,
                    ["draft_identity_contract_incomplete"],
                    defect_class="contract_defect",
                )
            )
            continue
        existing = selected.get(identity)
        if existing is None or _draft_priority(row, source) > _draft_priority(*existing):
            if existing is not None:
                rejections.append(
                    _rejection(
                        existing[0],
                        existing[1],
                        ["duplicate_candidate_identity_superseded"],
                        defect_class="duplicate_suppressed",
                    )
                )
            selected[identity] = (row, source)
        else:
            rejections.append(
                _rejection(
                    row,
                    source,
                    ["duplicate_candidate_identity_suppressed"],
                    defect_class="duplicate_suppressed",
                )
            )
    accepted = []
    for row, source in selected.values():
        copied = dict(row)
        copied["_canonical_source_draft_ref"] = source
        accepted.append(copied)
    accepted.sort(key=lambda row: str(row.get("hypothesis_id") or ""))
    return accepted, rejections


def _rejection(
    row: dict[str, Any],
    source: str,
    reasons: list[str],
    *,
    defect_class: str,
) -> dict[str, Any]:
    material = {
        "source": source,
        "hypothesis_id": row.get("hypothesis_id"),
        "reasons": reasons,
    }
    return {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "qadam_tradeability_envelope_rejection",
        "rejection_id": "tradeability-rejection:" + sha256_json(material)[:24],
        "generated_at": now_iso(),
        "hypothesis_id": row.get("hypothesis_id"),
        "candidate_identity_id": _candidate_identity(row) or None,
        "source_draft_ref": source,
        "source_draft_hash": sha256_json(row),
        "defect_class": defect_class,
        "reasons": unique_errors(reasons),
        "automatic_policy_change_allowed": False,
        "paper_order_created": False,
        "authority": authority_flags(),
    }


def _profile_for(row: dict[str, Any], packet: dict[str, Any]) -> str:
    if str(row.get("experimental_tier") or "") == "discovery_micro":
        return "discovery_micro"
    profile = str(packet.get("evidence_profile") or "")
    return profile if profile else "validated_paper_strategy"


def _canonical_foundry_summary(
    drafts: list[dict[str, Any]],
    projections: list[dict[str, Any]],
    generated_at: str,
    runtime: Path,
) -> dict[str, Any]:
    legacy = read_json(runtime / LEGACY_FOUNDRY_ARTIFACT)
    edge_class_counts = legacy.get("edge_class_counts")
    return {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "qadam_canonical_tradeability_foundry_summary",
        "generated_at": generated_at,
        "status": "canonical_tradeability_compiled",
        "implementation_complete": True,
        "valid_no_hypothesis_outcome": not projections,
        "admission_contract": "durable_or10_edge_registry_plus_bounded_experimental_pattern_scores",
        "draft_count": len(drafts),
        "hypothesis_count": len(projections),
        "edge_class_counts": edge_class_counts if isinstance(edge_class_counts, dict) else {},
        "canonical_envelope_required": True,
        "parallel_hypothesis_consumption_allowed": False,
        "authority": authority_flags(),
    }


def build_tradeability_pipeline_state(settings: Settings | None = None) -> dict[str, Any]:
    runtime = runtime_dir(settings)
    generated_at = now_iso()
    matrix, matrix_checks, matrix_errors = build_and_write_capability_matrix(settings)
    drafts, rejections = _collect_drafts(runtime)
    clean_drafts = []
    source_by_hypothesis: dict[str, str] = {}
    contribution_meta_by_hypothesis: dict[str, dict[str, Any]] = {}
    for draft in drafts:
        source = str(draft.pop("_canonical_source_draft_ref", LEGACY_HYPOTHESES_ARTIFACT))
        hypothesis_id = str(draft.get("hypothesis_id") or "")
        source_by_hypothesis[hypothesis_id] = source
        contribution_meta_by_hypothesis[hypothesis_id] = {
            "contribution_id": draft.pop("_lane_contribution_id", None),
            "agent_contributions": draft.pop("_agent_contributions", []),
            "critic_receipts": draft.pop("_critic_receipts", []),
        }
        clean_drafts.append(draft)

    packet_state = build_decision_evidence_packets_from_inputs(
        clean_drafts,
        read_jsonl(runtime / DIRECTIONS_ARTIFACT),
        read_jsonl(runtime / EVENT_ARTIFACT),
        read_jsonl(runtime / REGIME_ARTIFACT),
        read_jsonl(runtime / DISLOCATION_ARTIFACT),
        current_decision_artifacts(settings),
        generated_at=generated_at,
    )
    packet_errors = validate_decision_evidence_packets(packet_state)
    packet_by_hypothesis = {
        str(row.get("hypothesis_id")): row
        for row in packet_state.get("packets", [])
        if row.get("hypothesis_id")
    }
    packet_rejections = {
        str(row.get("hypothesis_id")): row
        for row in packet_state.get("rejections", [])
        if row.get("hypothesis_id")
    }

    envelopes: list[TradeabilityEnvelope] = []
    projections: list[dict[str, Any]] = []
    defects: list[dict[str, Any]] = []
    for draft in clean_drafts:
        hypothesis_id = str(draft.get("hypothesis_id") or "")
        source = source_by_hypothesis.get(hypothesis_id, LEGACY_HYPOTHESES_ARTIFACT)
        packet = packet_by_hypothesis.get(hypothesis_id)
        if packet is None:
            reasons = list(packet_rejections.get(hypothesis_id, {}).get("reasons") or [])
            reasons = reasons or ["same_generation_decision_packet_missing"]
            rejection = _rejection(
                draft,
                source,
                reasons,
                defect_class="producer_consumer_contract_defect",
            )
            rejections.append(rejection)
            defects.append(rejection)
            continue
        profile = _profile_for(draft, packet)
        try:
            contribution_meta = contribution_meta_by_hypothesis.get(hypothesis_id, {})
            envelope = compile_tradeability_envelope(
                draft,
                packet,
                source_draft_ref=f"{source}#{hypothesis_id}",
                agent_contributions=contribution_meta.get("agent_contributions") or [],
                critic_receipts=contribution_meta.get("critic_receipts") or [],
                structurally_uncollectable_fields=uncollectable_fields_for_profile(
                    matrix, profile
                ),
            )
        except Exception as exc:
            rejection = _rejection(
                draft,
                source,
                [f"tradeability_envelope_compile_failed:{exc}"],
                defect_class="producer_consumer_contract_defect",
            )
            rejections.append(rejection)
            defects.append(rejection)
            continue
        envelopes.append(envelope)
        projections.append(envelope_to_hypothesis_projection(envelope, draft))

    envelope_rows = [envelope.model_dump(mode="json") for envelope in envelopes]
    ids = [str(row.get("envelope_id") or "") for row in envelope_rows]
    hypothesis_ids = [str(row.get("identity", {}).get("hypothesis_id") or "") for row in envelope_rows]
    validation_errors = [*matrix_errors, *packet_errors]
    if defects:
        validation_errors.append(f"canonical_contract_defects_active:{len(defects)}")
    if len(ids) != len(set(ids)) or any(not value for value in ids):
        validation_errors.append("canonical_envelope_id_missing_or_duplicate")
    if len(hypothesis_ids) != len(set(hypothesis_ids)):
        validation_errors.append("canonical_hypothesis_id_duplicate")
    if len(envelope_rows) != len(projections):
        validation_errors.append("canonical_projection_cardinality_mismatch")
    if any(row.get("artifact_type") != "qadam_canonical_strategy_hypothesis_projection" for row in projections):
        validation_errors.append("noncanonical_hypothesis_projection_emitted")
    for row in envelope_rows:
        validation_errors.extend(
            validate_authority(row.get("authority", {}), prefix="tradeability_envelope")
        )
    validation_errors = unique_errors(validation_errors)
    registry = {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "qadam_tradeability_envelope_registry",
        "generated_at": generated_at,
        "status": "passed" if not validation_errors else "blocked",
        "source_draft_count": len(clean_drafts),
        "envelope_count": len(envelope_rows),
        "projection_count": len(projections),
        "rejection_count": len(rejections),
        "contract_defect_count": len(defects),
        "decision_generation_id": packet_state.get("summary", {}).get(
            "decision_generation_id"
        ),
        "envelope_record_set_hash": record_set_hash(envelope_rows),
        "projection_record_set_hash": record_set_hash(projections),
        "sole_downstream_hypothesis_artifact": LEGACY_HYPOTHESES_ARTIFACT,
        "parallel_qeg_downstream_consumption_allowed": False,
        "authority": authority_flags(),
    }
    foundry = _canonical_foundry_summary(
        clean_drafts, projections, generated_at, runtime
    )
    checks = {
        **registry,
        "artifact_type": "qadam_tradeability_pipeline_checks",
        "implementation_complete": not validation_errors,
        "capability_matrix_status": matrix_checks.get("status"),
        "packet_validation_error_count": len(packet_errors),
        "validation_error_count": len(validation_errors),
        "validation_errors": validation_errors,
        "candidate_created_count": 0,
        "order_created_count": 0,
        "broker_write_count": 0,
        "proof_credit_created_count": 0,
    }
    return {
        "envelopes": envelope_rows,
        "projections": projections,
        "rejections": rejections,
        "defects": defects,
        "packet_state": packet_state,
        "registry": registry,
        "foundry": foundry,
        "checks": checks,
    }


def build_and_write_tradeability_pipeline(
    settings: Settings | None = None,
) -> tuple[dict[str, Any], dict[str, Any], list[str]]:
    runtime = runtime_dir(settings)
    state = build_tradeability_pipeline_state(settings)
    store = AtomicArtifactStore(runtime)
    packet_state = state["packet_state"]
    errors = list(state["checks"].get("validation_errors") or [])
    last_good_present = bool(
        (runtime / LEGACY_HYPOTHESES_ARTIFACT).is_file()
        and (runtime / REGISTRY_ARTIFACT).is_file()
    )
    state["checks"]["canonical_output_updated"] = not errors
    state["checks"]["last_good_generation_preserved"] = bool(
        errors and last_good_present
    )
    state["registry"]["canonical_output_updated"] = not errors
    state["registry"]["last_good_generation_preserved"] = bool(
        errors and last_good_present
    )
    if not errors:
        store.write_jsonl(ENVELOPES_ARTIFACT, state["envelopes"])
        store.write_jsonl(LEGACY_HYPOTHESES_ARTIFACT, state["projections"])
        store.write_json(REGISTRY_ARTIFACT, state["registry"])
        store.write_json(CANONICAL_FOUNDRY_ARTIFACT, state["foundry"])
        store.write_jsonl(PACKETS_ARTIFACT, packet_state["packets"])
        store.write_jsonl(PACKET_REJECTIONS_ARTIFACT, packet_state["rejections"])
        store.write_json(INTEGRITY_ARTIFACT, packet_state["integrity"])
        packet_checks = {
            **packet_state["summary"],
            "status": "passed",
            "implementation_ready": True,
            "validation_errors": [],
        }
        store.write_json(PACKET_SUMMARY_ARTIFACT, packet_checks)
    store.write_jsonl(REJECTIONS_ARTIFACT, state["rejections"])
    store.write_jsonl(CONTRACT_DEFECTS_ARTIFACT, state["defects"])
    store.write_json(CHECK_ARTIFACT, state["checks"])
    store.write_json(PIPELINE_CHECK_ARTIFACT, state["checks"])
    store.write_json(PIPELINE_SUMMARY_ARTIFACT, state["registry"])
    schema_path = Path(__file__).resolve().parents[1] / SCHEMA_PATH
    schema_path.parent.mkdir(parents=True, exist_ok=True)
    AtomicArtifactStore(schema_path.parent).write_json(schema_path.name, envelope_schema())
    return state, state["checks"], errors


__all__ = [
    "CANONICAL_FOUNDRY_ARTIFACT",
    "CONTRACT_DEFECTS_ARTIFACT",
    "DRAFTS_ARTIFACT",
    "PIPELINE_CHECK_ARTIFACT",
    "PIPELINE_SUMMARY_ARTIFACT",
    "build_and_write_tradeability_pipeline",
    "build_tradeability_pipeline_state",
]
