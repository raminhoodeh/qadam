"""Q6-13 trust-score update proposals.

This stage prepares the proposal surface for source trust-score changes. The
current learning approval ledger is still pending, so the artifact records
blocked no-op proposals for the canonical source score table and preserves
Yahoo Finance plus Preference/PREF as supplemental-only, non-scoring context.
"""

from __future__ import annotations

import json
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
from statistics import fmean
from typing import Any

from orchestrator.config import Settings
from orchestrator.event_log import EventLog, EventLogEntry
from orchestrator.phase4_trust_scores import validate_trust_score_recalculation
from orchestrator.phase6_artifacts import (
    PHASE6_ARTIFACT_SCHEMA_VERSION,
    PHASE6_UNSAFE_COUNT_FIELDS,
    phase6_authority_defaults,
    phase6_authority_ledger,
    phase6_event_contract,
    phase6_provenance,
    phase6_source_posture,
    phase6_unsafe_counter_defaults,
    validate_phase6_artifact,
)
from orchestrator.phase6_model_weight_updates import (
    PHASE6_MODEL_WEIGHT_UPDATES_RUNTIME_ARTIFACT,
    validate_phase6_model_weight_updates,
)


PHASE6_TRUST_SCORE_UPDATES_SCHEMA_VERSION = 1
PHASE6_TRUST_SCORE_UPDATES_RUNTIME_ARTIFACT = "phase6_trust_score_update_proposals.json"
PHASE6_TRUST_SCORE_UPDATES_HISTORY = "phase6_trust_score_update_proposals_history.jsonl"
PHASE6_TRUST_SCORE_UPDATES_EVENT_LOG = "phase6_trust_score_update_proposals_events.jsonl"
PHASE6_TRUST_SCORE_UPDATES_EVENT_TYPE = "phase6_trust_score_update_proposed"
PHASE6_TRUST_SCORE_UPDATES_COMPONENT = "phase6_trust_score_updates"

SOURCE_MODEL_WEIGHT_REF = f"data/runtime/{PHASE6_MODEL_WEIGHT_UPDATES_RUNTIME_ARTIFACT}"
SOURCE_TRUST_SCORE_REF = "data/runtime/phase4_trust_score_recalculation.json"

PHASE6_TRUST_SCORE_UPDATES_BOUNDARY = (
    "Q6-13 creates source trust-score update proposals only. It can compute "
    "source-cited before/after score proposals from explicitly approved "
    "postmortem learning evidence, or record blocked no-op proposals when "
    "approval is missing, but it cannot apply trust scores, cannot mutate "
    "canonical source rank, cannot let Yahoo Finance or Preference/PREF satisfy "
    "source quorum, cannot write learning data, cannot write or commit a "
    "Knowledge Graph, cannot write Chroma or graph backend state, cannot update "
    "model weights, cannot mutate policy, cannot mutate strategies, cannot "
    "mutate Phase 5 source artifacts, cannot call broker POST routes, cannot "
    "call Alpaca POST routes, cannot call live endpoints, cannot enable live "
    "capital, and cannot count Phase 5 test trades toward Phase 7 proof."
)

WRITE_DISABLED_FIELDS: tuple[str, ...] = (
    "apply_allowed",
    "trust_score_update_allowed",
    "trust_score_update_proposal_allowed",
    "trust_score_update_proposed",
    "trust_score_update_applied",
    "active_trust_score_mutated",
    "canonical_rank_mutated",
    "source_quorum_credit_granted",
    "learning_write_created",
    "knowledge_graph_write_created",
    "knowledge_graph_commit_created",
    "chroma_write_created",
    "graph_backend_write_created",
    "model_weight_update_created",
    "trust_score_update_created",
    "policy_mutation_created",
    "strategy_mutation_created",
    "phase5_source_artifacts_mutated",
    "phase7_proof_credit_allowed",
)

PROPOSAL_RECORD_REQUIRED_FIELDS: tuple[str, ...] = (
    "proposal_id",
    "proposal_state",
    "source_key",
    "source_name",
    "canonical_source",
    "supplemental_source",
    "source_role",
    "source_score_included",
    "canonical_rank_impact_allowed",
    "source_quorum_credit_allowed",
    "before_score",
    "after_score",
    "score_delta",
    "usefulness_score",
    "error_penalty",
    "staleness_penalty",
    "provenance_quality_score",
    "corroboration_score",
    "source_refs",
    "approved_learning_entry",
    "trust_score_update_proposal_allowed",
    "apply_allowed",
    "trust_score_update_applied",
    "active_trust_score_mutated",
    "reference_only",
    "raw_payload_copied",
    "private_payload_copied",
    "rationale",
)

SUPPLEMENTAL_POLICY_REQUIRED_FIELDS: tuple[str, ...] = (
    "source_key",
    "source_role",
    "canonical_source",
    "score_included",
    "canonical_rank_impact_allowed",
    "source_quorum_credit_allowed",
    "supplemental_only_verdict_rejected",
    "source_refs",
)

COCKPIT_SAFE_STATUS_FIELDS: tuple[str, ...] = (
    "status",
    "proposal_state",
    "source_model_weight_status",
    "source_approval_state",
    "proposal_record_count",
    "active_proposal_count",
    "blocked_proposal_count",
    "canonical_source_score_count",
    "supplemental_policy_record_count",
    "approved_evidence_count",
    "trust_score_update_count",
    "apply_allowed",
    "trust_score_update_applied",
    "active_trust_score_mutated",
    "phase7_proof_credit_allowed",
    "unsafe_write_counter_total",
)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _runtime_dir(settings: Settings | None = None) -> Path:
    return Path((settings or Settings.from_env()).runtime_dir)


def _repo_root(settings: Settings | None = None) -> Path:
    return _runtime_dir(settings).parent.parent


def _path(ref: str, settings: Settings | None = None) -> Path:
    return _repo_root(settings) / ref


def _read_json(ref: str, settings: Settings | None = None) -> dict[str, Any] | None:
    path = _path(ref, settings)
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def _list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def _disabled_write_fields() -> dict[str, bool]:
    return {field: False for field in WRITE_DISABLED_FIELDS}


def _has_local_path(ref: str) -> bool:
    if ref.startswith("/") or ref.startswith("~"):
        return True
    return len(ref) > 2 and ref[1:3] == ":\\"


def phase6_trust_score_updates_paths(
    settings: Settings | None = None,
) -> tuple[Path, Path, Path]:
    runtime = _runtime_dir(settings)
    return (
        runtime / PHASE6_TRUST_SCORE_UPDATES_RUNTIME_ARTIFACT,
        runtime / PHASE6_TRUST_SCORE_UPDATES_HISTORY,
        runtime / PHASE6_TRUST_SCORE_UPDATES_EVENT_LOG,
    )


def _scores(trust_artifact: dict[str, Any]) -> dict[str, dict[str, Any]]:
    rows: dict[str, dict[str, Any]] = {}
    for row in _list(trust_artifact.get("scores")):
        if isinstance(row, dict) and isinstance(row.get("source_key"), str):
            rows[str(row["source_key"])] = row
    return dict(sorted(rows.items()))


def _score_table(rows: dict[str, dict[str, Any]]) -> dict[str, float]:
    output: dict[str, float] = {}
    for source_key, row in rows.items():
        value = row.get("final_provisional_score")
        if isinstance(value, int | float):
            output[source_key] = round(float(value), 6)
    return output


def _score_average(scores: dict[str, float]) -> float:
    return round(float(fmean(scores.values())), 6) if scores else 0.0


def _zero_delta(scores: dict[str, float]) -> dict[str, float]:
    return {source_key: 0.0 for source_key in scores}


def _safe_source_refs(refs: list[Any]) -> list[str]:
    safe_refs = [SOURCE_MODEL_WEIGHT_REF, SOURCE_TRUST_SCORE_REF]
    for ref in refs:
        if isinstance(ref, str) and ref.startswith("data/") and ref not in safe_refs:
            safe_refs.append(ref)
    return safe_refs


def _source_refs(model_weight: dict[str, Any], trust_artifact: dict[str, Any]) -> list[str]:
    refs: list[Any] = [SOURCE_MODEL_WEIGHT_REF, SOURCE_TRUST_SCORE_REF]
    provenance = model_weight.get("provenance")
    if isinstance(provenance, dict):
        refs.extend(_list(provenance.get("source_refs")))
    refs.extend(
        [
            "data/runtime/phase4_data_veracity_audit.json",
            "data/runtime/preference_source_promotion_decisions.json",
        ]
    )
    for row in _list(trust_artifact.get("supplemental_market_confirmation")):
        if isinstance(row, dict):
            refs.extend(_list(row.get("source_refs")))
    return _safe_source_refs(refs)


def _proposal_gate_open(model_weight: dict[str, Any]) -> bool:
    if model_weight.get("status") not in {"proposal", "blocked"}:
        return False
    if model_weight.get("source_approval_state") != "approved":
        return False
    if int(model_weight.get("approved_evidence_count", 0) or 0) <= 0:
        return False
    return model_weight.get("model_weight_update_proposal_allowed") is True


def _metric_scores(row: dict[str, Any]) -> dict[str, float]:
    reason_codes = [str(reason) for reason in _list(row.get("reason_codes"))]
    evidence_mode = str(row.get("evidence_mode") or "")
    usefulness = 0.65
    if row.get("score_change_direction") == "up":
        usefulness += 0.12
    if row.get("score_change_direction") == "down":
        usefulness -= 0.16
    if row.get("quarantine") is True:
        usefulness -= 0.25
    usefulness = max(0.0, min(1.0, usefulness))
    error_penalty = 0.18 if row.get("quarantine") is True else 0.0
    if any("missing_credentials" in reason for reason in reason_codes):
        error_penalty = max(error_penalty, 0.22)
    staleness_penalty = 0.0 if any("fresh_replay_snapshot" in reason for reason in reason_codes) else 0.08
    provenance_quality = {
        "durable_replay": 0.9,
        "deterministic_sample": 0.7,
        "registered_prior": 0.45,
    }.get(evidence_mode, 0.5)
    corroboration = (
        0.85
        if any("corroboration_ready_read_only" in reason for reason in reason_codes)
        else 0.35
    )
    if any("corroboration_limited" in reason for reason in reason_codes):
        corroboration = 0.25
    return {
        "usefulness_score": round(usefulness, 6),
        "error_penalty": round(error_penalty, 6),
        "staleness_penalty": round(staleness_penalty, 6),
        "provenance_quality_score": round(provenance_quality, 6),
        "corroboration_score": round(corroboration, 6),
    }


def _blocked_record(
    *,
    row: dict[str, Any],
    source_refs: list[str],
    source_approval_state: str | None,
) -> dict[str, Any]:
    source_key = str(row.get("source_key") or "unknown_source")
    before_score = round(float(row.get("final_provisional_score", 0.0) or 0.0), 6)
    return {
        "proposal_id": f"q6-13-trust-score-proposal:{source_key}",
        "proposal_state": "blocked_pending_learning_approval",
        "source_key": source_key,
        "source_name": str(row.get("source_name") or source_key),
        "canonical_source": row.get("canonical_source") is True,
        "supplemental_source": False,
        "source_role": "canonical_source",
        "source_score_included": True,
        "canonical_rank_impact_allowed": False,
        "source_quorum_credit_allowed": False,
        "source_approval_state": source_approval_state,
        "before_score": before_score,
        "after_score": before_score,
        "score_delta": 0.0,
        **_metric_scores(row),
        "source_refs": source_refs,
        "approved_learning_entry": False,
        "trust_score_update_proposal_allowed": False,
        "apply_allowed": False,
        "trust_score_update_applied": False,
        "active_trust_score_mutated": False,
        "reference_only": True,
        "raw_payload_copied": False,
        "private_payload_copied": False,
        "rationale": (
            "Q6-9 approval is still pending, so Q6-13 records a source "
            "trust-score before/after proposal with zero delta."
        ),
    }


def _active_record(
    *,
    row: dict[str, Any],
    source_refs: list[str],
    source_approval_state: str | None,
) -> dict[str, Any]:
    source_key = str(row.get("source_key") or "unknown_source")
    before_score = round(float(row.get("final_provisional_score", 0.0) or 0.0), 6)
    metrics = _metric_scores(row)
    evidence_signal = (
        metrics["usefulness_score"]
        + metrics["provenance_quality_score"]
        + metrics["corroboration_score"]
        - metrics["error_penalty"]
        - metrics["staleness_penalty"]
    ) / 3
    delta = round(max(-0.03, min(0.03, (evidence_signal - 0.55) * 0.05)), 6)
    after_score = round(max(0.0, min(0.99, before_score + delta)), 6)
    return {
        "proposal_id": f"q6-13-trust-score-proposal:{source_key}",
        "proposal_state": "proposal_ready_pending_apply_approval",
        "source_key": source_key,
        "source_name": str(row.get("source_name") or source_key),
        "canonical_source": row.get("canonical_source") is True,
        "supplemental_source": False,
        "source_role": "canonical_source",
        "source_score_included": True,
        "canonical_rank_impact_allowed": False,
        "source_quorum_credit_allowed": False,
        "source_approval_state": source_approval_state,
        "before_score": before_score,
        "after_score": after_score,
        "score_delta": round(after_score - before_score, 6),
        **metrics,
        "source_refs": source_refs,
        "approved_learning_entry": True,
        "trust_score_update_proposal_allowed": True,
        "apply_allowed": False,
        "trust_score_update_applied": False,
        "active_trust_score_mutated": False,
        "reference_only": True,
        "raw_payload_copied": False,
        "private_payload_copied": False,
        "rationale": (
            "Approved postmortem evidence permits a trust-score proposal, but "
            "application and canonical-rank mutation remain disabled."
        ),
    }


def _supplemental_policy_records(trust_artifact: dict[str, Any], source_refs: list[str]) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for row in _list(trust_artifact.get("supplemental_market_confirmation")):
        if not isinstance(row, dict):
            continue
        source_key = str(row.get("source_key") or "")
        if source_key not in {"yahoo_finance", "preference_mcp"}:
            continue
        records.append(
            {
                "source_key": source_key,
                "source_role": str(row.get("source_role") or "supplemental_context"),
                "canonical_source": False,
                "score_included": False,
                "canonical_rank_impact_allowed": False,
                "source_quorum_credit_allowed": False,
                "supplemental_only_verdict_rejected": True,
                "single_source_verdict_rejected": True,
                "source_refs": source_refs,
                "rationale": (
                    "Supplemental-only context cannot drive a trust-score update "
                    "or satisfy source quorum."
                ),
            }
        )
    return records


def _provenance(source_refs: list[str]) -> dict[str, Any]:
    output = phase6_provenance(source_refs)
    output["execution_evidence_refs"] = [
        ref for ref in source_refs if any(marker in ref for marker in ("closed_trade", "outcome_links"))
    ]
    output["market_context_refs"] = [
        ref for ref in source_refs if any(marker in ref for marker in ("cockpit-status", "preference_", "yahoo"))
    ]
    output["model_interpretation_refs"] = [
        ref for ref in source_refs if "phase6_model_weight_update_proposals" in ref
    ]
    output["governance_refs"] = [
        ref for ref in source_refs if any(marker in ref for marker in ("approval", "reduced_review"))
    ]
    return output


def _cockpit_safe_status(
    *,
    status: str,
    proposal_state: str,
    model_weight: dict[str, Any],
    records: list[dict[str, Any]],
    supplemental_records: list[dict[str, Any]],
    trust_score_update_count: int,
) -> dict[str, Any]:
    return {
        "status": status,
        "proposal_state": proposal_state,
        "source_model_weight_status": model_weight.get("status"),
        "source_approval_state": model_weight.get("source_approval_state"),
        "proposal_record_count": len(records),
        "active_proposal_count": len(
            [record for record in records if record.get("trust_score_update_proposal_allowed") is True]
        ),
        "blocked_proposal_count": len(
            [record for record in records if record.get("proposal_state") == "blocked_pending_learning_approval"]
        ),
        "canonical_source_score_count": len(records),
        "supplemental_policy_record_count": len(supplemental_records),
        "approved_evidence_count": int(model_weight.get("approved_evidence_count", 0) or 0),
        "trust_score_update_count": trust_score_update_count,
        "apply_allowed": False,
        "trust_score_update_applied": False,
        "active_trust_score_mutated": False,
        "phase7_proof_credit_allowed": False,
        "unsafe_write_counter_total": 0,
    }


def build_phase6_trust_score_updates(settings: Settings | None = None) -> dict[str, Any]:
    settings = settings or Settings.from_env()
    generated_at = _now()
    model_weight = _read_json(SOURCE_MODEL_WEIGHT_REF, settings) or {}
    trust_artifact = _read_json(SOURCE_TRUST_SCORE_REF, settings) or {}
    model_weight_errors = validate_phase6_model_weight_updates(model_weight) if model_weight else []
    trust_errors = validate_trust_score_recalculation(trust_artifact) if trust_artifact else []
    source_rows = _scores(trust_artifact)
    before_table = _score_table(source_rows)
    source_refs = _source_refs(model_weight, trust_artifact)
    blockers: list[str] = []
    if not model_weight:
        blockers.append("model_weight_update_proposals_missing")
    if model_weight_errors:
        blockers.append("model_weight_update_proposals_validation_errors")
    if not trust_artifact:
        blockers.append("trust_score_recalculation_missing")
    if trust_errors:
        blockers.append("trust_score_recalculation_validation_errors")
    if not before_table:
        blockers.append("canonical_trust_scores_missing")
    gate_open = not blockers and _proposal_gate_open(model_weight)
    records = [
        (
            _active_record(
                row=row,
                source_refs=source_refs,
                source_approval_state=model_weight.get("source_approval_state"),
            )
            if gate_open
            else _blocked_record(
                row=row,
                source_refs=source_refs,
                source_approval_state=model_weight.get("source_approval_state"),
            )
        )
        for row in source_rows.values()
    ]
    if not gate_open:
        if model_weight.get("source_approval_state") != "approved":
            blockers.append("learning_approval_pending")
        if int(model_weight.get("approved_evidence_count", 0) or 0) == 0:
            blockers.append("approved_learning_entries_missing")
    after_table = {
        str(record["source_key"]): round(float(record["after_score"]), 6)
        for record in records
        if record.get("canonical_source") is True
    }
    score_delta = {
        source_key: round(float(after_table.get(source_key, 0.0)) - float(before_table.get(source_key, 0.0)), 6)
        for source_key in before_table
    }
    supplemental_records = _supplemental_policy_records(trust_artifact, source_refs)
    proposal_state = (
        "proposal_ready_pending_apply_approval"
        if gate_open
        else "blocked_pending_learning_approval"
    )
    status = "proposal" if gate_open else "blocked"
    active_proposal_count = len(
        [record for record in records if record.get("trust_score_update_proposal_allowed") is True]
    )
    blocked_proposal_count = len(
        [record for record in records if record.get("proposal_state") == "blocked_pending_learning_approval"]
    )
    trust_score_update_count = active_proposal_count if gate_open else 0
    authority = phase6_authority_ledger()
    authority["stage"] = "Q6-13"
    authority["boundary"] = PHASE6_TRUST_SCORE_UPDATES_BOUNDARY
    artifact = {
        "schema_version": PHASE6_ARTIFACT_SCHEMA_VERSION,
        "phase6_trust_score_updates_schema_version": PHASE6_TRUST_SCORE_UPDATES_SCHEMA_VERSION,
        "artifact_type": "trust_score_update_proposal",
        "artifact_id": "phase6:q6-13:trust-score-update-proposals",
        "phase": "Q6",
        "stage": "Q6-13",
        "status": status,
        "generated_at": generated_at,
        "public_safe": True,
        "recorded": False,
        "event_log_required": True,
        "event_log_written": False,
        "event_log_path": None,
        "event_log_event_count": 0,
        "event_log_correlation_id": None,
        "event_log_created_at": None,
        "runtime_artifact_path": None,
        "history_log_path": None,
        "event_contract": phase6_event_contract("trust_update_proposal"),
        "authority_ledger": authority,
        "source_posture": phase6_source_posture(),
        "provenance": _provenance(source_refs),
        "boundary": PHASE6_TRUST_SCORE_UPDATES_BOUNDARY,
        **phase6_authority_defaults(),
        **phase6_unsafe_counter_defaults(),
        **_disabled_write_fields(),
        "proposal_state": proposal_state,
        "source_model_weight_ref": SOURCE_MODEL_WEIGHT_REF,
        "source_model_weight_status": model_weight.get("status"),
        "source_model_weight_proposal_state": model_weight.get("proposal_state"),
        "source_approval_state": model_weight.get("source_approval_state"),
        "source_approved_evidence_count": int(model_weight.get("approved_evidence_count", 0) or 0),
        "source_trust_score_ref": SOURCE_TRUST_SCORE_REF,
        "canonical_source_score_count": len(before_table),
        "supplemental_policy_record_count": len(supplemental_records),
        "before_score": _score_average(before_table),
        "after_score": _score_average(after_table),
        "score_delta_total_abs": round(sum(abs(float(value)) for value in score_delta.values()), 6),
        "before_score_table": before_table,
        "after_score_table": after_table,
        "score_delta_table": score_delta,
        "proposal_records": records,
        "proposal_record_count": len(records),
        "active_proposal_count": active_proposal_count,
        "blocked_proposal_count": blocked_proposal_count,
        "approved_evidence_count": int(model_weight.get("approved_evidence_count", 0) or 0),
        "trust_score_update_count": trust_score_update_count,
        "trust_score_update_proposal_allowed": gate_open,
        "trust_score_update_proposed": gate_open,
        "apply_allowed": False,
        "trust_score_update_allowed": False,
        "trust_score_update_applied": False,
        "active_trust_score_mutated": False,
        "canonical_rank_mutated": False,
        "source_quorum_credit_granted": False,
        "supplemental_policy_records": supplemental_records,
        "single_source_verdict_rejected": True,
        "supplemental_only_verdict_rejected": True,
        "single_source_verdict_rejection_count": 1,
        "supplemental_only_verdict_rejection_count": len(supplemental_records),
        "yahoo_finance_score_included": False,
        "yahoo_finance_canonical_rank_impact_allowed": False,
        "yahoo_finance_source_quorum_credit_allowed": False,
        "preference_mcp_score_included": False,
        "preference_mcp_canonical_rank_impact_allowed": False,
        "preference_mcp_source_quorum_credit_allowed": False,
        "preference_mcp_source_36": False,
        "learning_write_created": False,
        "knowledge_graph_write_created": False,
        "knowledge_graph_commit_created": False,
        "chroma_write_created": False,
        "graph_backend_write_created": False,
        "model_weight_update_created": False,
        "trust_score_update_created": False,
        "policy_mutation_created": False,
        "strategy_mutation_created": False,
        "raw_payload_copied_count": 0,
        "private_payload_copied_count": 0,
        "local_path_exposed_count": 0,
        "secret_ref_exposed_count": 0,
        "source_hash_mutation_count": 0,
        "phase5_source_artifacts_mutated": False,
        "phase5_test_trades_count_for_phase7": False,
        "phase7_proof_credit_allowed": False,
        "unsafe_write_counter_total": 0,
        "cockpit_safe_status": _cockpit_safe_status(
            status=status,
            proposal_state=proposal_state,
            model_weight=model_weight,
            records=records,
            supplemental_records=supplemental_records,
            trust_score_update_count=trust_score_update_count,
        ),
        "blockers": sorted(set(blockers)),
        "blocker_count": len(set(blockers)),
        "recommended_next_stage": "Q6-14 Shadow Strategy Runner",
    }
    artifact["validation_errors"] = validate_phase6_trust_score_updates(artifact)
    if artifact["validation_errors"]:
        artifact["status"] = "blocked"
    return artifact


def _source_ref_errors(prefix: str, refs: Any) -> list[str]:
    errors: list[str] = []
    if not isinstance(refs, list) or not refs:
        return [f"{prefix}_source_refs_missing"]
    for ref in refs:
        if not isinstance(ref, str) or not ref.strip():
            errors.append(f"{prefix}_source_ref_invalid")
            continue
        if _has_local_path(ref):
            errors.append(f"{prefix}_local_source_ref")
        if any(secret_word in ref.lower() for secret_word in ("api_key", "secret", "token")):
            errors.append(f"{prefix}_secret_source_ref")
    return errors


def _write_disabled_errors(prefix: str, payload: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    for field in WRITE_DISABLED_FIELDS:
        if payload.get(field) is not False:
            errors.append(f"{prefix}_write_enabled:{field}")
    return errors


def _score_table_errors(prefix: str, value: Any) -> tuple[dict[str, float], list[str]]:
    errors: list[str] = []
    if not isinstance(value, dict) or not value:
        return {}, [f"{prefix}_missing"]
    output: dict[str, float] = {}
    for key, item in value.items():
        if not isinstance(key, str) or not isinstance(item, int | float):
            errors.append(f"{prefix}_invalid")
            continue
        output[key] = round(float(item), 6)
    return output, errors


def validate_phase6_trust_score_updates(artifact: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    required_fields = {
        "schema_version",
        "phase6_trust_score_updates_schema_version",
        "artifact_type",
        "artifact_id",
        "phase",
        "stage",
        "status",
        "generated_at",
        "public_safe",
        "event_log_required",
        "event_log_written",
        "event_contract",
        "authority_ledger",
        "source_posture",
        "provenance",
        "boundary",
        "proposal_state",
        "source_model_weight_ref",
        "source_model_weight_status",
        "source_model_weight_proposal_state",
        "source_approval_state",
        "source_approved_evidence_count",
        "source_trust_score_ref",
        "canonical_source_score_count",
        "supplemental_policy_record_count",
        "before_score",
        "after_score",
        "score_delta_total_abs",
        "before_score_table",
        "after_score_table",
        "score_delta_table",
        "proposal_records",
        "proposal_record_count",
        "active_proposal_count",
        "blocked_proposal_count",
        "approved_evidence_count",
        "trust_score_update_count",
        "trust_score_update_proposal_allowed",
        "trust_score_update_proposed",
        "apply_allowed",
        "trust_score_update_allowed",
        "trust_score_update_applied",
        "active_trust_score_mutated",
        "canonical_rank_mutated",
        "source_quorum_credit_granted",
        "supplemental_policy_records",
        "single_source_verdict_rejected",
        "supplemental_only_verdict_rejected",
        "single_source_verdict_rejection_count",
        "supplemental_only_verdict_rejection_count",
        "yahoo_finance_score_included",
        "yahoo_finance_canonical_rank_impact_allowed",
        "yahoo_finance_source_quorum_credit_allowed",
        "preference_mcp_score_included",
        "preference_mcp_canonical_rank_impact_allowed",
        "preference_mcp_source_quorum_credit_allowed",
        "preference_mcp_source_36",
        "learning_write_created",
        "knowledge_graph_write_created",
        "knowledge_graph_commit_created",
        "chroma_write_created",
        "graph_backend_write_created",
        "model_weight_update_created",
        "trust_score_update_created",
        "policy_mutation_created",
        "strategy_mutation_created",
        "raw_payload_copied_count",
        "private_payload_copied_count",
        "local_path_exposed_count",
        "secret_ref_exposed_count",
        "source_hash_mutation_count",
        "phase5_source_artifacts_mutated",
        "phase5_test_trades_count_for_phase7",
        "phase7_proof_credit_allowed",
        "unsafe_write_counter_total",
        "cockpit_safe_status",
        "blockers",
        "blocker_count",
    }
    missing = sorted(required_fields - set(artifact))
    if missing:
        errors.append("trust_score_updates_missing_fields:" + ",".join(missing))
    if artifact.get("phase6_trust_score_updates_schema_version") != (
        PHASE6_TRUST_SCORE_UPDATES_SCHEMA_VERSION
    ):
        errors.append("trust_score_updates_schema_version_mismatch")
    errors.extend(validate_phase6_artifact(artifact, expected_stage="Q6-13"))
    if artifact.get("artifact_type") != "trust_score_update_proposal":
        errors.append("trust_score_updates_artifact_type_mismatch")
    if artifact.get("status") not in {"blocked", "proposal"}:
        errors.append("trust_score_updates_status_invalid")
    if artifact.get("source_model_weight_ref") != SOURCE_MODEL_WEIGHT_REF:
        errors.append("source_model_weight_ref_invalid")
    if artifact.get("source_trust_score_ref") != SOURCE_TRUST_SCORE_REF:
        errors.append("source_trust_score_ref_invalid")
    if artifact.get("source_model_weight_status") not in {"blocked", "proposal"}:
        errors.append("source_model_weight_status_invalid")
    if artifact.get("source_approval_state") not in {"pending_review", "approved", "deferred"}:
        errors.append("source_approval_state_invalid")
    errors.extend(_write_disabled_errors("trust_score_updates", artifact))

    before_table, before_errors = _score_table_errors("before_score_table", artifact.get("before_score_table"))
    after_table, after_errors = _score_table_errors("after_score_table", artifact.get("after_score_table"))
    errors.extend(before_errors)
    errors.extend(after_errors)
    if before_table and after_table and set(before_table) != set(after_table):
        errors.append("trust_score_updates_score_keys_mismatch")
    if before_table and artifact.get("canonical_source_score_count") != len(before_table):
        errors.append("canonical_source_score_count_mismatch")
    if before_table and artifact.get("before_score") != _score_average(before_table):
        errors.append("before_score_average_mismatch")
    if after_table and artifact.get("after_score") != _score_average(after_table):
        errors.append("after_score_average_mismatch")
    delta = artifact.get("score_delta_table")
    if not isinstance(delta, dict):
        errors.append("score_delta_table_invalid")
        delta_values: dict[str, float] = {}
    else:
        delta_values = {
            str(key): round(float(value), 6)
            for key, value in delta.items()
            if isinstance(value, int | float)
        }
    expected_delta = {
        key: round(float(after_table.get(key, 0.0)) - float(before_table.get(key, 0.0)), 6)
        for key in before_table
    }
    if before_table and after_table and delta_values != expected_delta:
        errors.append("score_delta_table_mismatch")
    delta_total_abs = round(sum(abs(float(value)) for value in expected_delta.values()), 6)
    if artifact.get("score_delta_total_abs") != delta_total_abs:
        errors.append("score_delta_total_abs_mismatch")

    records = _list(artifact.get("proposal_records"))
    if artifact.get("proposal_record_count") != len(records):
        errors.append("proposal_record_count_mismatch")
    if len(records) < 1:
        errors.append("proposal_records_missing")
    active_count = 0
    blocked_count = 0
    raw_payload_count = 0
    private_payload_count = 0
    local_path_count = 0
    secret_ref_count = 0
    for record in records:
        if not isinstance(record, dict):
            errors.append("proposal_record_invalid")
            continue
        missing_record_fields = sorted(set(PROPOSAL_RECORD_REQUIRED_FIELDS) - set(record))
        if missing_record_fields:
            errors.append("proposal_record_missing_fields:" + ",".join(missing_record_fields))
        if record.get("canonical_source") is not True:
            errors.append("proposal_record_not_canonical")
        if record.get("supplemental_source") is not False:
            errors.append("proposal_record_supplemental")
        if record.get("canonical_rank_impact_allowed") is not False:
            errors.append("proposal_record_rank_impact_allowed")
        if record.get("source_quorum_credit_allowed") is not False:
            errors.append("proposal_record_source_quorum_credit_allowed")
        if record.get("trust_score_update_proposal_allowed") is True:
            active_count += 1
        if record.get("proposal_state") == "blocked_pending_learning_approval":
            blocked_count += 1
        if record.get("apply_allowed") is not False:
            errors.append("proposal_record_apply_allowed")
        if record.get("trust_score_update_applied") is not False:
            errors.append("proposal_record_trust_score_update_applied")
        if record.get("active_trust_score_mutated") is not False:
            errors.append("proposal_record_active_trust_score_mutated")
        if record.get("reference_only") is not True:
            errors.append("proposal_record_not_reference_only")
        if record.get("raw_payload_copied") is not False:
            raw_payload_count += 1
        if record.get("private_payload_copied") is not False:
            private_payload_count += 1
        if "raw_payload" in record or "private_payload" in record:
            errors.append("proposal_record_forbidden_payload")
        ref_errors = _source_ref_errors("proposal_record", record.get("source_refs"))
        errors.extend(ref_errors)
        local_path_count += len([error for error in ref_errors if error == "proposal_record_local_source_ref"])
        secret_ref_count += len([error for error in ref_errors if error == "proposal_record_secret_source_ref"])
    if artifact.get("active_proposal_count") != active_count:
        errors.append("active_proposal_count_mismatch")
    if artifact.get("blocked_proposal_count") != blocked_count:
        errors.append("blocked_proposal_count_mismatch")
    if artifact.get("raw_payload_copied_count") != raw_payload_count:
        errors.append("raw_payload_copied_count_mismatch")
    if artifact.get("private_payload_copied_count") != private_payload_count:
        errors.append("private_payload_copied_count_mismatch")
    if artifact.get("local_path_exposed_count") != local_path_count:
        errors.append("local_path_exposed_count_mismatch")
    if artifact.get("secret_ref_exposed_count") != secret_ref_count:
        errors.append("secret_ref_exposed_count_mismatch")
    if raw_payload_count or private_payload_count or local_path_count or secret_ref_count:
        errors.append("trust_score_updates_private_or_local_payload_exposed")

    supplemental_records = _list(artifact.get("supplemental_policy_records"))
    if artifact.get("supplemental_policy_record_count") != len(supplemental_records):
        errors.append("supplemental_policy_record_count_mismatch")
    if len(supplemental_records) < 2:
        errors.append("supplemental_policy_records_missing")
    for record in supplemental_records:
        if not isinstance(record, dict):
            errors.append("supplemental_policy_record_invalid")
            continue
        missing_policy_fields = sorted(set(SUPPLEMENTAL_POLICY_REQUIRED_FIELDS) - set(record))
        if missing_policy_fields:
            errors.append("supplemental_policy_record_missing_fields:" + ",".join(missing_policy_fields))
        if record.get("canonical_source") is not False:
            errors.append("supplemental_policy_marked_canonical")
        if record.get("score_included") is not False:
            errors.append("supplemental_policy_score_included")
        if record.get("canonical_rank_impact_allowed") is not False:
            errors.append("supplemental_policy_rank_impact_allowed")
        if record.get("source_quorum_credit_allowed") is not False:
            errors.append("supplemental_policy_source_quorum_credit_allowed")
        if record.get("supplemental_only_verdict_rejected") is not True:
            errors.append("supplemental_only_verdict_not_rejected")
        errors.extend(_source_ref_errors("supplemental_policy_record", record.get("source_refs")))
    for key in (
        "single_source_verdict_rejected",
        "supplemental_only_verdict_rejected",
    ):
        if artifact.get(key) is not True:
            errors.append(f"{key}_not_true")
    if int(artifact.get("single_source_verdict_rejection_count", 0) or 0) < 1:
        errors.append("single_source_verdict_rejection_count_missing")
    if int(artifact.get("supplemental_only_verdict_rejection_count", 0) or 0) < 2:
        errors.append("supplemental_only_verdict_rejection_count_missing")
    for key in (
        "yahoo_finance_score_included",
        "yahoo_finance_canonical_rank_impact_allowed",
        "yahoo_finance_source_quorum_credit_allowed",
        "preference_mcp_score_included",
        "preference_mcp_canonical_rank_impact_allowed",
        "preference_mcp_source_quorum_credit_allowed",
        "preference_mcp_source_36",
    ):
        if artifact.get(key) is not False:
            errors.append(f"{key}_not_false")

    if artifact.get("source_approval_state") != "approved":
        if artifact.get("status") != "blocked":
            errors.append("trust_score_updates_unapproved_status_not_blocked")
        if artifact.get("proposal_state") != "blocked_pending_learning_approval":
            errors.append("trust_score_updates_unapproved_state_not_blocked")
        if artifact.get("trust_score_update_proposal_allowed") is not False:
            errors.append("trust_score_updates_unapproved_proposal_allowed")
        if artifact.get("trust_score_update_proposed") is not False:
            errors.append("trust_score_updates_unapproved_proposed")
        if artifact.get("active_proposal_count") != 0:
            errors.append("trust_score_updates_unapproved_active_proposals")
        if artifact.get("trust_score_update_count") != 0:
            errors.append("trust_score_updates_unapproved_update_count")
        if before_table and after_table and before_table != after_table:
            errors.append("trust_score_updates_unapproved_after_changed")
        if artifact.get("score_delta_total_abs") != 0.0:
            errors.append("trust_score_updates_unapproved_delta_nonzero")
    if artifact.get("status") == "proposal":
        if artifact.get("source_approval_state") != "approved":
            errors.append("trust_score_updates_proposal_without_approval")
        if artifact.get("active_proposal_count", 0) < 1:
            errors.append("trust_score_updates_proposal_without_active_records")
        if artifact.get("trust_score_update_proposal_allowed") is not True:
            errors.append("trust_score_updates_proposal_allowed_missing")
    if artifact.get("apply_allowed") is not False:
        errors.append("apply_allowed")
    if artifact.get("trust_score_update_applied") is not False:
        errors.append("trust_score_update_applied")
    if artifact.get("active_trust_score_mutated") is not False:
        errors.append("active_trust_score_mutated")
    if artifact.get("canonical_rank_mutated") is not False:
        errors.append("canonical_rank_mutated")
    if artifact.get("source_quorum_credit_granted") is not False:
        errors.append("source_quorum_credit_granted")
    if artifact.get("phase5_test_trades_count_for_phase7") is not False:
        errors.append("phase5_test_trades_count_for_phase7")
    errors.extend(_source_ref_errors("trust_score_updates", artifact.get("provenance", {}).get("source_refs")))

    cockpit = artifact.get("cockpit_safe_status")
    if not isinstance(cockpit, dict):
        errors.append("cockpit_safe_status_missing")
    else:
        extra = sorted(set(cockpit) - set(COCKPIT_SAFE_STATUS_FIELDS))
        if extra:
            errors.append("cockpit_safe_status_forbidden_fields:" + ",".join(extra))
        for forbidden in ("source_refs", "before_score_table", "after_score_table", "score_delta_table", "raw_payload"):
            if forbidden in cockpit:
                errors.append(f"cockpit_safe_status_exposes:{forbidden}")
        for field in COCKPIT_SAFE_STATUS_FIELDS:
            if field in cockpit and field in artifact and cockpit[field] != artifact[field]:
                errors.append(f"cockpit_safe_status_mismatch:{field}")
    unsafe_total = 0
    for field in PHASE6_UNSAFE_COUNT_FIELDS:
        value = int(artifact.get(field, 0) or 0)
        unsafe_total += value
        if value != 0:
            errors.append(f"trust_score_updates_unsafe_count_nonzero:{field}")
    if artifact.get("unsafe_write_counter_total") != unsafe_total:
        errors.append("trust_score_updates_unsafe_total_mismatch")
    if artifact.get("unsafe_write_counter_total") != 0:
        errors.append("trust_score_updates_unsafe_total_nonzero")

    boundary = str(artifact.get("boundary") or "")
    for phrase in (
        "cannot apply trust scores",
        "cannot mutate canonical source rank",
        "cannot let Yahoo Finance or Preference/PREF satisfy source quorum",
        "cannot write learning data",
        "cannot count Phase 5 test trades toward Phase 7 proof",
    ):
        if phrase not in boundary:
            errors.append("trust_score_updates_boundary_weak")
            break
    if artifact.get("event_log_written") is True:
        if not artifact.get("event_log_path"):
            errors.append("trust_score_updates_event_log_path_missing")
        if not artifact.get("event_log_correlation_id"):
            errors.append("trust_score_updates_event_correlation_missing")
        if artifact.get("event_log_event_count") != 1:
            errors.append("trust_score_updates_event_log_count_mismatch")
    return sorted(set(errors))


def attach_phase6_trust_score_updates_event_log(
    artifact: dict[str, Any],
    *,
    event_log: EventLog | None = None,
    event_log_path: str | Path | None = None,
    settings: Settings | None = None,
) -> tuple[dict[str, Any], EventLogEntry]:
    output = deepcopy(artifact)
    log_path = Path(event_log_path or (_runtime_dir(settings) / PHASE6_TRUST_SCORE_UPDATES_EVENT_LOG))
    log = event_log or EventLog(log_path, echo=False)
    entry = log.write(
        PHASE6_TRUST_SCORE_UPDATES_EVENT_TYPE,
        PHASE6_TRUST_SCORE_UPDATES_COMPONENT,
        {
            "artifact_id": output.get("artifact_id"),
            "status": output.get("status"),
            "proposal_state": output.get("proposal_state"),
            "source_approval_state": output.get("source_approval_state"),
            "proposal_record_count": output.get("proposal_record_count"),
            "active_proposal_count": output.get("active_proposal_count"),
            "blocked_proposal_count": output.get("blocked_proposal_count"),
            "canonical_source_score_count": output.get("canonical_source_score_count"),
            "supplemental_policy_record_count": output.get("supplemental_policy_record_count"),
            "approved_evidence_count": output.get("approved_evidence_count"),
            "trust_score_update_count": output.get("trust_score_update_count"),
            "apply_allowed": output.get("apply_allowed"),
            "trust_score_update_applied": output.get("trust_score_update_applied"),
            "active_trust_score_mutated": output.get("active_trust_score_mutated"),
            "phase7_proof_credit_allowed": output.get("phase7_proof_credit_allowed"),
            "unsafe_write_counter_total": output.get("unsafe_write_counter_total"),
            "boundary": output.get("boundary"),
        },
    )
    output["recorded"] = True
    output["event_log_written"] = True
    output["event_log_path"] = str(log.path)
    output["event_log_event_count"] = 1
    output["event_log_correlation_id"] = entry.correlation_id
    output["event_log_created_at"] = entry.created_at
    output["validation_errors"] = validate_phase6_trust_score_updates(output)
    if output["validation_errors"]:
        output["status"] = "blocked"
    return output, entry


def write_phase6_trust_score_updates(
    artifact: dict[str, Any],
    *,
    settings: Settings | None = None,
    record_event: bool = True,
    event_log_path: str | Path | None = None,
) -> tuple[Path, Path, Path, dict[str, Any]]:
    output = deepcopy(artifact)
    output_path, history_path, default_event_path = phase6_trust_score_updates_paths(settings)
    event_path = Path(event_log_path or default_event_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    if record_event:
        output, _ = attach_phase6_trust_score_updates_event_log(
            output,
            event_log_path=event_path,
            settings=settings,
        )
    else:
        output["validation_errors"] = validate_phase6_trust_score_updates(output)
        if output["validation_errors"]:
            output["status"] = "blocked"
    output["runtime_artifact_path"] = str(output_path)
    output["history_log_path"] = str(history_path)
    output["validation_errors"] = validate_phase6_trust_score_updates(output)
    if output["validation_errors"]:
        output["status"] = "blocked"
    output_path.write_text(json.dumps(output, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    history_record = {
        "schema_version": PHASE6_TRUST_SCORE_UPDATES_SCHEMA_VERSION,
        "artifact_id": output.get("artifact_id"),
        "status": output.get("status"),
        "generated_at": output.get("generated_at"),
        "recorded_at": _now(),
        "proposal_state": output.get("proposal_state"),
        "source_approval_state": output.get("source_approval_state"),
        "proposal_record_count": output.get("proposal_record_count"),
        "active_proposal_count": output.get("active_proposal_count"),
        "blocked_proposal_count": output.get("blocked_proposal_count"),
        "canonical_source_score_count": output.get("canonical_source_score_count"),
        "supplemental_policy_record_count": output.get("supplemental_policy_record_count"),
        "approved_evidence_count": output.get("approved_evidence_count"),
        "trust_score_update_count": output.get("trust_score_update_count"),
        "apply_allowed": output.get("apply_allowed"),
        "trust_score_update_applied": output.get("trust_score_update_applied"),
        "active_trust_score_mutated": output.get("active_trust_score_mutated"),
        "score_delta_total_abs": output.get("score_delta_total_abs"),
        "phase7_proof_credit_allowed": output.get("phase7_proof_credit_allowed"),
        "unsafe_write_counter_total": output.get("unsafe_write_counter_total"),
        "blocker_count": output.get("blocker_count"),
        "event_log_written": output.get("event_log_written"),
        "event_log_event_count": output.get("event_log_event_count"),
        "validation_error_count": len(output.get("validation_errors", [])),
    }
    with history_path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(history_record, sort_keys=True) + "\n")
    return output_path, history_path, event_path, output
