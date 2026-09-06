"""Deterministic draft selection; no reads, scheduling or execution authority."""

from typing import Any
from orchestrator.qadam_operator_ready_common import sha256_json, authority_flags, now_iso, unique_errors
from orchestrator.qadam_qualitative_common import LANE_CONTRIBUTIONS_ARTIFACT

SCHEMA_VERSION = "qadam_tradeability_pipeline.v1"
DRAFTS_ARTIFACT = "qadam_strategy_drafts_v3.jsonl"

def _candidate_identity(row: dict[str, Any]) -> str:
    candidate = row.get("candidate_identity_material")
    candidate = candidate if isinstance(candidate, dict) else {}
    return str(candidate.get("candidate_identity_id") or "")

def _draft_priority(row: dict[str, Any], source: str) -> tuple[int, int, str]:
    evidence_class = str(row.get("evidence_class") or "")
    evidence_rank = 2 if evidence_class == "validated_paper_strategy" else 1
    source_rank = 2 if source == LANE_CONTRIBUTIONS_ARTIFACT else 1 if source == DRAFTS_ARTIFACT else 0
    return evidence_rank, source_rank, str(row.get("generated_at") or "")

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

def select_drafts(source_rows: list[tuple[dict[str, Any], str]],
                  current_direction_ids: set[str],
                  rejections: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
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
