"""Q6-14 shadow strategy runner.

This stage prepares the what-would-have-happened replay surface for Phase 6.
The current learning approval ledger is still pending, so the artifact records
blocked no-op shadow variants and compares them to the guarded Phase 5 paper
lifecycle without creating candidates, orders, or execution intents.
"""

from __future__ import annotations

import json
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from orchestrator.config import Settings
from orchestrator.event_log import EventLog, EventLogEntry
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
from orchestrator.phase6_knowledge_graph_staging import TARGET_STRATEGY_FAMILY_KEY
from orchestrator.phase6_trust_score_updates import (
    PHASE6_TRUST_SCORE_UPDATES_RUNTIME_ARTIFACT,
    validate_phase6_trust_score_updates,
)


PHASE6_SHADOW_STRATEGY_RUNNER_SCHEMA_VERSION = 1
PHASE6_SHADOW_STRATEGY_RUNNER_RUNTIME_ARTIFACT = "phase6_shadow_strategy_replay.json"
PHASE6_SHADOW_STRATEGY_RUNNER_HISTORY = "phase6_shadow_strategy_replay_history.jsonl"
PHASE6_SHADOW_STRATEGY_RUNNER_EVENT_LOG = "phase6_shadow_strategy_replay_events.jsonl"
PHASE6_SHADOW_STRATEGY_RUNNER_EVENT_TYPE = "phase6_model_weight_update_proposed"
PHASE6_SHADOW_STRATEGY_RUNNER_COMPONENT = "phase6_shadow_strategy_runner"

SOURCE_TRUST_SCORE_UPDATES_REF = f"data/runtime/{PHASE6_TRUST_SCORE_UPDATES_RUNTIME_ARTIFACT}"
SOURCE_MODEL_WEIGHT_UPDATES_REF = "data/runtime/phase6_model_weight_update_proposals.json"
SOURCE_KG_READ_VIEW_REF = "data/runtime/phase6_knowledge_graph_read_view.json"
SOURCE_APPROVAL_REF = "data/runtime/phase6_learning_approval_ledger.json"
SOURCE_STRATEGY_UNIVERSE_REF = "data/runtime/phase4_candidate_strategy_universe.json"
SOURCE_POSITION_MONITOR_REF = "data/runtime/phase5_position_monitor.json"
SOURCE_CLOSED_TRADE_OUTCOME_REF = "data/runtime/phase6_closed_trade_outcome.json"
SOURCE_OUTCOME_LINK_REF = "data/runtime/phase6_outcome_links.json"

PHASE6_SHADOW_STRATEGY_RUNNER_BOUNDARY = (
    "Q6-14 creates a shadow strategy replay artifact only. It can compare "
    "actual guarded Phase 5 lifecycle evidence with what-would-have-happened "
    "strategy variants after explicit approved postmortem learning evidence, "
    "or record blocked no-op replay variants while approval is missing, but it "
    "cannot create trade candidates, cannot create or allow paper orders, "
    "cannot create execution intents, cannot call broker POST routes, cannot "
    "call Alpaca POST routes, cannot write learning data, cannot write or "
    "commit a Knowledge Graph, cannot update model weights, cannot update trust "
    "scores, cannot mutate policy, cannot mutate strategies, cannot mutate "
    "Phase 5 source artifacts, cannot call live endpoints, cannot enable live "
    "capital, and cannot count Phase 5 test trades toward Phase 7 proof."
)

WRITE_DISABLED_FIELDS: tuple[str, ...] = (
    "trade_candidate_creation_allowed",
    "trade_candidate_created",
    "order_creation_allowed",
    "paper_order_allowed",
    "paper_order_created",
    "execution_allowed",
    "execution_intent_created",
    "broker_post_allowed",
    "alpaca_post_allowed",
    "broker_write_allowed",
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

REPLAY_RECORD_REQUIRED_FIELDS: tuple[str, ...] = (
    "replay_id",
    "replay_state",
    "strategy_family_key",
    "variant_key",
    "variant_name",
    "variant_type",
    "source_refs",
    "source_approval_state",
    "approved_learning_entry",
    "actual_decision",
    "hypothetical_decision",
    "actual_vs_hypothetical_delta",
    "replay_allowed",
    "trade_candidate_creation_allowed",
    "trade_candidate_created",
    "order_creation_allowed",
    "paper_order_allowed",
    "paper_order_created",
    "execution_allowed",
    "execution_intent_created",
    "broker_post_allowed",
    "alpaca_post_allowed",
    "reference_only",
    "raw_payload_copied",
    "private_payload_copied",
    "rationale",
)

COCKPIT_SAFE_STATUS_FIELDS: tuple[str, ...] = (
    "status",
    "replay_state",
    "source_trust_score_status",
    "source_approval_state",
    "variant_record_count",
    "active_replay_count",
    "blocked_replay_count",
    "approved_fact_count",
    "actual_vs_hypothetical_comparison_count",
    "trade_candidate_created_count",
    "paper_order_allowed_count",
    "execution_allowed_count",
    "order_creation_allowed",
    "phase7_proof_credit_allowed",
    "unsafe_write_counter_total",
)

SHADOW_VARIANTS: tuple[dict[str, str], ...] = (
    {
        "variant_key": "baseline_current_strategy",
        "variant_name": "Baseline Current Strategy Replay",
        "variant_type": "baseline_no_learning_delta",
    },
    {
        "variant_key": "model_weight_counterfactual",
        "variant_name": "Model Weight Counterfactual Replay",
        "variant_type": "model_weight_update_proposal_variant",
    },
    {
        "variant_key": "trust_score_counterfactual",
        "variant_name": "Trust Score Counterfactual Replay",
        "variant_type": "trust_score_update_proposal_variant",
    },
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
    payload = json.loads(path.read_text(encoding="utf-8"))
    return payload if isinstance(payload, dict) else None


def _list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def _disabled_write_fields() -> dict[str, bool]:
    return {field: False for field in WRITE_DISABLED_FIELDS}


def _has_local_path(ref: str) -> bool:
    if ref.startswith("/") or ref.startswith("~"):
        return True
    return len(ref) > 2 and ref[1:3] == ":\\"


def phase6_shadow_strategy_runner_paths(
    settings: Settings | None = None,
) -> tuple[Path, Path, Path]:
    runtime = _runtime_dir(settings)
    return (
        runtime / PHASE6_SHADOW_STRATEGY_RUNNER_RUNTIME_ARTIFACT,
        runtime / PHASE6_SHADOW_STRATEGY_RUNNER_HISTORY,
        runtime / PHASE6_SHADOW_STRATEGY_RUNNER_EVENT_LOG,
    )


def _safe_source_refs(refs: list[Any]) -> list[str]:
    safe_refs = [
        SOURCE_TRUST_SCORE_UPDATES_REF,
        SOURCE_MODEL_WEIGHT_UPDATES_REF,
        SOURCE_KG_READ_VIEW_REF,
        SOURCE_APPROVAL_REF,
        SOURCE_STRATEGY_UNIVERSE_REF,
        SOURCE_POSITION_MONITOR_REF,
        SOURCE_CLOSED_TRADE_OUTCOME_REF,
        SOURCE_OUTCOME_LINK_REF,
    ]
    for ref in refs:
        if isinstance(ref, str) and ref.startswith("data/") and ref not in safe_refs:
            safe_refs.append(ref)
    return safe_refs


def _source_refs(trust_updates: dict[str, Any]) -> list[str]:
    refs: list[Any] = [
        SOURCE_TRUST_SCORE_UPDATES_REF,
        SOURCE_MODEL_WEIGHT_UPDATES_REF,
        SOURCE_KG_READ_VIEW_REF,
        SOURCE_APPROVAL_REF,
        SOURCE_STRATEGY_UNIVERSE_REF,
        SOURCE_POSITION_MONITOR_REF,
        SOURCE_CLOSED_TRADE_OUTCOME_REF,
        SOURCE_OUTCOME_LINK_REF,
    ]
    provenance = trust_updates.get("provenance")
    if isinstance(provenance, dict):
        refs.extend(_list(provenance.get("source_refs")))
    for record in _list(trust_updates.get("proposal_records")):
        if isinstance(record, dict):
            refs.extend(_list(record.get("source_refs")))
    return _safe_source_refs(refs)


def _strategy_candidate(strategy_universe: dict[str, Any]) -> dict[str, Any]:
    for candidate in _list(strategy_universe.get("candidates")):
        if isinstance(candidate, dict) and candidate.get("candidate_key") == TARGET_STRATEGY_FAMILY_KEY:
            return candidate
    return {}


def _actual_decision(position_monitor: dict[str, Any]) -> dict[str, Any]:
    records = [record for record in _list(position_monitor.get("records")) if isinstance(record, dict)]
    closed_records = [
        record
        for record in records
        if record.get("artifact_type") == "closed_trade_summary"
        or record.get("lifecycle_state") == "closed_trade"
    ]
    source = closed_records[-1] if closed_records else (records[-1] if records else {})
    return {
        "source_ref": SOURCE_POSITION_MONITOR_REF,
        "decision_state": "actual_phase5_guarded_lifecycle",
        "lifecycle_state": source.get("lifecycle_state") or position_monitor.get("status"),
        "instrument": source.get("instrument"),
        "side": source.get("side"),
        "submitted_order_count": int(position_monitor.get("submitted_order_count", 0) or 0),
        "open_position_count": int(position_monitor.get("open_position_count", 0) or 0),
        "closed_trade_count": int(position_monitor.get("closed_trade_count", 0) or 0),
        "realized_pnl_gbp": float(position_monitor.get("realized_pnl_gbp", 0.0) or 0.0),
        "phase5_test_trade": source.get("phase5_test_trade") is True,
        "trade_candidate_created": source.get("trade_candidate_created") is True,
        "paper_order_allowed": source.get("paper_order_allowed") is True,
        "execution_allowed": source.get("execution_allowed") is True,
        "reference_only": True,
    }


def _hypothetical_decision(*, gate_open: bool, variant: dict[str, str]) -> dict[str, Any]:
    if not gate_open:
        return {
            "decision_state": "not_evaluated_pending_learning_approval",
            "variant_key": variant["variant_key"],
            "would_create_trade_candidate": False,
            "would_allow_paper_order": False,
            "would_allow_execution": False,
            "would_call_broker": False,
            "would_call_alpaca": False,
            "reason": "explicit_approved_postmortem_learning_evidence_missing",
        }
    return {
        "decision_state": "evaluated_reference_only_no_trade_action",
        "variant_key": variant["variant_key"],
        "would_create_trade_candidate": False,
        "would_allow_paper_order": False,
        "would_allow_execution": False,
        "would_call_broker": False,
        "would_call_alpaca": False,
        "reason": "shadow_replay_is_reference_only_even_when_evidence_is_approved",
    }


def _decision_delta(*, gate_open: bool) -> dict[str, Any]:
    return {
        "comparison_state": "evaluated_reference_only" if gate_open else "blocked_not_evaluated",
        "trade_candidate_created_delta": 0,
        "paper_order_allowed_delta": 0,
        "execution_allowed_delta": 0,
        "broker_post_delta": 0,
        "alpaca_post_delta": 0,
        "risk_or_pnl_delta_computed": False,
    }


def _replay_records(
    *,
    gate_open: bool,
    source_refs: list[str],
    source_approval_state: str | None,
    actual_decision: dict[str, Any],
) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    replay_state = (
        "shadow_replay_ready_reference_only"
        if gate_open
        else "blocked_pending_learning_approval"
    )
    for variant in SHADOW_VARIANTS:
        records.append(
            {
                "replay_id": f"q6-14-shadow-replay:{variant['variant_key']}",
                "replay_state": replay_state,
                "strategy_family_key": TARGET_STRATEGY_FAMILY_KEY,
                "variant_key": variant["variant_key"],
                "variant_name": variant["variant_name"],
                "variant_type": variant["variant_type"],
                "source_refs": source_refs,
                "source_approval_state": source_approval_state,
                "approved_learning_entry": gate_open,
                "actual_decision": actual_decision,
                "hypothetical_decision": _hypothetical_decision(
                    gate_open=gate_open,
                    variant=variant,
                ),
                "actual_vs_hypothetical_delta": _decision_delta(gate_open=gate_open),
                "replay_allowed": gate_open,
                "trade_candidate_creation_allowed": False,
                "trade_candidate_created": False,
                "order_creation_allowed": False,
                "paper_order_allowed": False,
                "paper_order_created": False,
                "execution_allowed": False,
                "execution_intent_created": False,
                "broker_post_allowed": False,
                "alpaca_post_allowed": False,
                "reference_only": True,
                "raw_payload_copied": False,
                "private_payload_copied": False,
                "rationale": (
                    "Approved learning evidence permits a reference-only shadow replay; "
                    "candidate, order, execution, broker, and live actions remain disabled."
                    if gate_open
                    else "Q6-9 approval is still pending, so Q6-14 records a blocked "
                    "no-op shadow variant without evaluating a trade path."
                ),
            }
        )
    return records


def _provenance(source_refs: list[str]) -> dict[str, Any]:
    output = phase6_provenance(source_refs)
    output["execution_evidence_refs"] = [
        ref
        for ref in source_refs
        if any(marker in ref for marker in ("position_monitor", "closed_trade", "outcome_links"))
    ]
    output["market_context_refs"] = [
        ref
        for ref in source_refs
        if any(marker in ref for marker in ("cockpit-status", "preference_", "yahoo"))
    ]
    output["model_interpretation_refs"] = [
        ref
        for ref in source_refs
        if any(marker in ref for marker in ("model_weight", "trust_score", "quantum"))
    ]
    output["governance_refs"] = [
        ref
        for ref in source_refs
        if any(marker in ref for marker in ("approval", "reduced_review", "read_view"))
    ]
    return output


def _cockpit_safe_status(
    *,
    status: str,
    replay_state: str,
    trust_updates: dict[str, Any],
    records: list[dict[str, Any]],
    approved_fact_count: int,
) -> dict[str, Any]:
    return {
        "status": status,
        "replay_state": replay_state,
        "source_trust_score_status": trust_updates.get("status"),
        "source_approval_state": trust_updates.get("source_approval_state"),
        "variant_record_count": len(records),
        "active_replay_count": len([record for record in records if record.get("replay_allowed") is True]),
        "blocked_replay_count": len(
            [record for record in records if record.get("replay_state") == "blocked_pending_learning_approval"]
        ),
        "approved_fact_count": approved_fact_count,
        "actual_vs_hypothetical_comparison_count": len(records),
        "trade_candidate_created_count": 0,
        "paper_order_allowed_count": 0,
        "execution_allowed_count": 0,
        "order_creation_allowed": False,
        "phase7_proof_credit_allowed": False,
        "unsafe_write_counter_total": 0,
    }


def _gate_open(trust_updates: dict[str, Any], blockers: list[str]) -> bool:
    if blockers:
        return False
    if trust_updates.get("source_approval_state") != "approved":
        return False
    if int(trust_updates.get("approved_evidence_count", 0) or 0) <= 0:
        return False
    return True


def build_phase6_shadow_strategy_runner(settings: Settings | None = None) -> dict[str, Any]:
    settings = settings or Settings.from_env()
    generated_at = _now()
    trust_updates = _read_json(SOURCE_TRUST_SCORE_UPDATES_REF, settings) or {}
    strategy_universe = _read_json(SOURCE_STRATEGY_UNIVERSE_REF, settings) or {}
    position_monitor = _read_json(SOURCE_POSITION_MONITOR_REF, settings) or {}
    closed_trade_outcome = _read_json(SOURCE_CLOSED_TRADE_OUTCOME_REF, settings) or {}
    trust_errors = validate_phase6_trust_score_updates(trust_updates) if trust_updates else []
    strategy_candidate = _strategy_candidate(strategy_universe)
    source_refs = _source_refs(trust_updates)
    blockers: list[str] = []
    if not trust_updates:
        blockers.append("trust_score_update_proposals_missing")
    if trust_errors:
        blockers.append("trust_score_update_proposals_validation_errors")
    if not strategy_candidate:
        blockers.append("strategy_family_candidate_missing")
    if not position_monitor:
        blockers.append("position_monitor_missing")
    if not closed_trade_outcome:
        blockers.append("closed_trade_outcome_missing")
    gate_open = _gate_open(trust_updates, blockers)
    if not gate_open:
        if trust_updates.get("source_approval_state") != "approved":
            blockers.append("learning_approval_pending")
        if int(trust_updates.get("approved_evidence_count", 0) or 0) == 0:
            blockers.append("approved_learning_entries_missing")

    actual_decision = _actual_decision(position_monitor)
    records = _replay_records(
        gate_open=gate_open,
        source_refs=source_refs,
        source_approval_state=trust_updates.get("source_approval_state"),
        actual_decision=actual_decision,
    )
    replay_state = (
        "shadow_replay_ready_reference_only"
        if gate_open
        else "blocked_pending_learning_approval"
    )
    status = "replay" if gate_open else "blocked"
    active_replay_count = len([record for record in records if record.get("replay_allowed") is True])
    blocked_replay_count = len(
        [record for record in records if record.get("replay_state") == "blocked_pending_learning_approval"]
    )
    approved_fact_count = int(trust_updates.get("approved_evidence_count", 0) or 0)
    evaluated_variant_count = active_replay_count if gate_open else 0
    authority = phase6_authority_ledger()
    authority["stage"] = "Q6-14"
    authority["boundary"] = PHASE6_SHADOW_STRATEGY_RUNNER_BOUNDARY
    artifact = {
        "schema_version": PHASE6_ARTIFACT_SCHEMA_VERSION,
        "phase6_shadow_strategy_runner_schema_version": PHASE6_SHADOW_STRATEGY_RUNNER_SCHEMA_VERSION,
        "artifact_type": "shadow_strategy_replay",
        "artifact_id": "phase6:q6-14:shadow-strategy-replay:crude_oil_energy_security_disruption",
        "phase": "Q6",
        "stage": "Q6-14",
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
        "event_contract": phase6_event_contract("model_update_proposal"),
        "authority_ledger": authority,
        "source_posture": phase6_source_posture(),
        "provenance": _provenance(source_refs),
        "boundary": PHASE6_SHADOW_STRATEGY_RUNNER_BOUNDARY,
        **phase6_authority_defaults(),
        **phase6_unsafe_counter_defaults(),
        **_disabled_write_fields(),
        "replay_state": replay_state,
        "strategy_family_key": TARGET_STRATEGY_FAMILY_KEY,
        "source_trust_score_ref": SOURCE_TRUST_SCORE_UPDATES_REF,
        "source_trust_score_status": trust_updates.get("status"),
        "source_trust_score_proposal_state": trust_updates.get("proposal_state"),
        "source_approval_state": trust_updates.get("source_approval_state"),
        "source_approved_evidence_count": approved_fact_count,
        "source_model_weight_ref": SOURCE_MODEL_WEIGHT_UPDATES_REF,
        "source_model_weight_status": trust_updates.get("source_model_weight_status"),
        "source_strategy_universe_ref": SOURCE_STRATEGY_UNIVERSE_REF,
        "source_position_monitor_ref": SOURCE_POSITION_MONITOR_REF,
        "source_closed_trade_outcome_ref": SOURCE_CLOSED_TRADE_OUTCOME_REF,
        "source_outcome_link_ref": SOURCE_OUTCOME_LINK_REF,
        "source_model_weight_delta_total_abs": float(
            trust_updates.get("source_model_weight_delta_total_abs", 0.0) or 0.0
        ),
        "source_trust_score_delta_total_abs": float(trust_updates.get("score_delta_total_abs", 0.0) or 0.0),
        "replay_output_exists": True,
        "shadow_strategy_replay_allowed": gate_open,
        "shadow_strategy_replay_created": gate_open,
        "approved_fact_count": approved_fact_count,
        "variant_record_count": len(records),
        "active_replay_count": active_replay_count,
        "blocked_replay_count": blocked_replay_count,
        "evaluated_variant_count": evaluated_variant_count,
        "actual_vs_hypothetical_comparison_count": len(records),
        "evaluated_comparison_count": evaluated_variant_count,
        "replay_records": records,
        "actual_decision_summary": actual_decision,
        "trade_candidate_created_count": 0,
        "paper_order_allowed_count": 0,
        "execution_allowed_count": 0,
        "paper_order_created_count": 0,
        "execution_intent_created_count": 0,
        "broker_post_called_count": 0,
        "alpaca_post_called_count": 0,
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
            replay_state=replay_state,
            trust_updates=trust_updates,
            records=records,
            approved_fact_count=approved_fact_count,
        ),
        "blockers": sorted(set(blockers)),
        "blocker_count": len(set(blockers)),
        "recommended_next_stage": "Q6-15 Architect Learning Summary",
    }
    artifact["validation_errors"] = validate_phase6_shadow_strategy_runner(artifact)
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


def validate_phase6_shadow_strategy_runner(artifact: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    required_fields = {
        "schema_version",
        "phase6_shadow_strategy_runner_schema_version",
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
        "replay_state",
        "strategy_family_key",
        "source_trust_score_ref",
        "source_trust_score_status",
        "source_trust_score_proposal_state",
        "source_approval_state",
        "source_approved_evidence_count",
        "source_model_weight_ref",
        "source_model_weight_status",
        "source_strategy_universe_ref",
        "source_position_monitor_ref",
        "source_closed_trade_outcome_ref",
        "source_outcome_link_ref",
        "source_model_weight_delta_total_abs",
        "source_trust_score_delta_total_abs",
        "replay_output_exists",
        "shadow_strategy_replay_allowed",
        "shadow_strategy_replay_created",
        "approved_fact_count",
        "variant_record_count",
        "active_replay_count",
        "blocked_replay_count",
        "evaluated_variant_count",
        "actual_vs_hypothetical_comparison_count",
        "evaluated_comparison_count",
        "replay_records",
        "actual_decision_summary",
        "trade_candidate_created_count",
        "paper_order_allowed_count",
        "execution_allowed_count",
        "paper_order_created_count",
        "execution_intent_created_count",
        "broker_post_called_count",
        "alpaca_post_called_count",
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
        errors.append("shadow_strategy_runner_missing_fields:" + ",".join(missing))
    if artifact.get("phase6_shadow_strategy_runner_schema_version") != (
        PHASE6_SHADOW_STRATEGY_RUNNER_SCHEMA_VERSION
    ):
        errors.append("shadow_strategy_runner_schema_version_mismatch")
    errors.extend(validate_phase6_artifact(artifact, expected_stage="Q6-14"))
    if artifact.get("artifact_type") != "shadow_strategy_replay":
        errors.append("shadow_strategy_runner_artifact_type_mismatch")
    if artifact.get("status") not in {"blocked", "replay"}:
        errors.append("shadow_strategy_runner_status_invalid")
    if artifact.get("strategy_family_key") != TARGET_STRATEGY_FAMILY_KEY:
        errors.append("strategy_family_key_mismatch")
    if artifact.get("source_trust_score_ref") != SOURCE_TRUST_SCORE_UPDATES_REF:
        errors.append("source_trust_score_ref_invalid")
    if artifact.get("source_model_weight_ref") != SOURCE_MODEL_WEIGHT_UPDATES_REF:
        errors.append("source_model_weight_ref_invalid")
    if artifact.get("source_strategy_universe_ref") != SOURCE_STRATEGY_UNIVERSE_REF:
        errors.append("source_strategy_universe_ref_invalid")
    if artifact.get("source_position_monitor_ref") != SOURCE_POSITION_MONITOR_REF:
        errors.append("source_position_monitor_ref_invalid")
    if artifact.get("source_closed_trade_outcome_ref") != SOURCE_CLOSED_TRADE_OUTCOME_REF:
        errors.append("source_closed_trade_outcome_ref_invalid")
    if artifact.get("source_outcome_link_ref") != SOURCE_OUTCOME_LINK_REF:
        errors.append("source_outcome_link_ref_invalid")
    if artifact.get("source_trust_score_status") not in {"blocked", "proposal"}:
        errors.append("source_trust_score_status_invalid")
    if artifact.get("source_approval_state") not in {"pending_review", "approved", "deferred"}:
        errors.append("source_approval_state_invalid")
    errors.extend(_write_disabled_errors("shadow_strategy_runner", artifact))

    records = _list(artifact.get("replay_records"))
    if artifact.get("variant_record_count") != len(records):
        errors.append("variant_record_count_mismatch")
    if len(records) < 1:
        errors.append("replay_records_missing")
    active_count = 0
    blocked_count = 0
    raw_payload_count = 0
    private_payload_count = 0
    local_path_count = 0
    secret_ref_count = 0
    for record in records:
        if not isinstance(record, dict):
            errors.append("replay_record_invalid")
            continue
        missing_record_fields = sorted(set(REPLAY_RECORD_REQUIRED_FIELDS) - set(record))
        if missing_record_fields:
            errors.append("replay_record_missing_fields:" + ",".join(missing_record_fields))
        if record.get("strategy_family_key") != TARGET_STRATEGY_FAMILY_KEY:
            errors.append("replay_record_strategy_family_mismatch")
        if record.get("replay_allowed") is True:
            active_count += 1
        if record.get("replay_state") == "blocked_pending_learning_approval":
            blocked_count += 1
        for field in (
            "trade_candidate_creation_allowed",
            "trade_candidate_created",
            "order_creation_allowed",
            "paper_order_allowed",
            "paper_order_created",
            "execution_allowed",
            "execution_intent_created",
            "broker_post_allowed",
            "alpaca_post_allowed",
        ):
            if record.get(field) is not False:
                errors.append(f"replay_record_action_enabled:{field}")
        if record.get("reference_only") is not True:
            errors.append("replay_record_not_reference_only")
        if record.get("raw_payload_copied") is not False:
            raw_payload_count += 1
        if record.get("private_payload_copied") is not False:
            private_payload_count += 1
        if "raw_payload" in record or "private_payload" in record:
            errors.append("replay_record_forbidden_payload")
        delta = record.get("actual_vs_hypothetical_delta")
        if not isinstance(delta, dict):
            errors.append("replay_record_delta_invalid")
        else:
            for field in (
                "trade_candidate_created_delta",
                "paper_order_allowed_delta",
                "execution_allowed_delta",
                "broker_post_delta",
                "alpaca_post_delta",
            ):
                if int(delta.get(field, 0) or 0) != 0:
                    errors.append(f"replay_record_action_delta_nonzero:{field}")
        ref_errors = _source_ref_errors("replay_record", record.get("source_refs"))
        errors.extend(ref_errors)
        local_path_count += len([error for error in ref_errors if error == "replay_record_local_source_ref"])
        secret_ref_count += len([error for error in ref_errors if error == "replay_record_secret_source_ref"])
    if artifact.get("active_replay_count") != active_count:
        errors.append("active_replay_count_mismatch")
    if artifact.get("blocked_replay_count") != blocked_count:
        errors.append("blocked_replay_count_mismatch")
    if artifact.get("actual_vs_hypothetical_comparison_count") != len(records):
        errors.append("comparison_count_mismatch")
    if artifact.get("evaluated_variant_count") != active_count:
        errors.append("evaluated_variant_count_mismatch")
    if artifact.get("evaluated_comparison_count") != active_count:
        errors.append("evaluated_comparison_count_mismatch")
    if artifact.get("raw_payload_copied_count") != raw_payload_count:
        errors.append("raw_payload_copied_count_mismatch")
    if artifact.get("private_payload_copied_count") != private_payload_count:
        errors.append("private_payload_copied_count_mismatch")
    if artifact.get("local_path_exposed_count") != local_path_count:
        errors.append("local_path_exposed_count_mismatch")
    if artifact.get("secret_ref_exposed_count") != secret_ref_count:
        errors.append("secret_ref_exposed_count_mismatch")
    if raw_payload_count or private_payload_count or local_path_count or secret_ref_count:
        errors.append("shadow_strategy_runner_private_or_local_payload_exposed")

    if artifact.get("source_approval_state") != "approved":
        if artifact.get("status") != "blocked":
            errors.append("shadow_strategy_runner_unapproved_status_not_blocked")
        if artifact.get("replay_state") != "blocked_pending_learning_approval":
            errors.append("shadow_strategy_runner_unapproved_state_not_blocked")
        if artifact.get("shadow_strategy_replay_allowed") is not False:
            errors.append("shadow_strategy_runner_unapproved_replay_allowed")
        if artifact.get("shadow_strategy_replay_created") is not False:
            errors.append("shadow_strategy_runner_unapproved_replay_created")
        if artifact.get("active_replay_count") != 0:
            errors.append("shadow_strategy_runner_unapproved_active_replay")
        if artifact.get("evaluated_variant_count") != 0:
            errors.append("shadow_strategy_runner_unapproved_evaluated_variants")
    else:
        if artifact.get("status") != "replay":
            errors.append("shadow_strategy_runner_approved_status_not_replay")
        if artifact.get("active_replay_count", 0) < 1:
            errors.append("shadow_strategy_runner_approved_without_active_records")
        if artifact.get("shadow_strategy_replay_allowed") is not True:
            errors.append("shadow_strategy_runner_approved_replay_not_allowed")
    if artifact.get("approved_fact_count") != artifact.get("source_approved_evidence_count"):
        errors.append("approved_fact_count_mismatch")
    if artifact.get("replay_output_exists") is not True:
        errors.append("replay_output_missing")
    for field in (
        "trade_candidate_created_count",
        "paper_order_allowed_count",
        "execution_allowed_count",
        "paper_order_created_count",
        "execution_intent_created_count",
        "broker_post_called_count",
        "alpaca_post_called_count",
    ):
        if int(artifact.get(field, 0) or 0) != 0:
            errors.append(f"shadow_strategy_runner_action_count_nonzero:{field}")
    if artifact.get("phase5_test_trades_count_for_phase7") is not False:
        errors.append("phase5_test_trades_count_for_phase7")
    errors.extend(_source_ref_errors("shadow_strategy_runner", artifact.get("provenance", {}).get("source_refs")))

    cockpit = artifact.get("cockpit_safe_status")
    if not isinstance(cockpit, dict):
        errors.append("cockpit_safe_status_missing")
    else:
        extra = sorted(set(cockpit) - set(COCKPIT_SAFE_STATUS_FIELDS))
        if extra:
            errors.append("cockpit_safe_status_forbidden_fields:" + ",".join(extra))
        for forbidden in ("source_refs", "replay_records", "actual_decision_summary", "raw_payload"):
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
            errors.append(f"shadow_strategy_runner_unsafe_count_nonzero:{field}")
    if artifact.get("unsafe_write_counter_total") != unsafe_total:
        errors.append("shadow_strategy_runner_unsafe_total_mismatch")
    if artifact.get("unsafe_write_counter_total") != 0:
        errors.append("shadow_strategy_runner_unsafe_total_nonzero")

    boundary = str(artifact.get("boundary") or "")
    for phrase in (
        "cannot create trade candidates",
        "cannot create or allow paper orders",
        "cannot create execution intents",
        "cannot mutate strategies",
        "cannot count Phase 5 test trades toward Phase 7 proof",
    ):
        if phrase not in boundary:
            errors.append("shadow_strategy_runner_boundary_weak")
            break
    if artifact.get("event_log_written") is True:
        if not artifact.get("event_log_path"):
            errors.append("shadow_strategy_runner_event_log_path_missing")
        if not artifact.get("event_log_correlation_id"):
            errors.append("shadow_strategy_runner_event_correlation_missing")
        if artifact.get("event_log_event_count") != 1:
            errors.append("shadow_strategy_runner_event_log_count_mismatch")
    return sorted(set(errors))


def attach_phase6_shadow_strategy_runner_event_log(
    artifact: dict[str, Any],
    *,
    event_log: EventLog | None = None,
    event_log_path: str | Path | None = None,
    settings: Settings | None = None,
) -> tuple[dict[str, Any], EventLogEntry]:
    output = deepcopy(artifact)
    log_path = Path(event_log_path or (_runtime_dir(settings) / PHASE6_SHADOW_STRATEGY_RUNNER_EVENT_LOG))
    log = event_log or EventLog(log_path, echo=False)
    entry = log.write(
        PHASE6_SHADOW_STRATEGY_RUNNER_EVENT_TYPE,
        PHASE6_SHADOW_STRATEGY_RUNNER_COMPONENT,
        {
            "artifact_id": output.get("artifact_id"),
            "status": output.get("status"),
            "replay_state": output.get("replay_state"),
            "source_approval_state": output.get("source_approval_state"),
            "variant_record_count": output.get("variant_record_count"),
            "active_replay_count": output.get("active_replay_count"),
            "blocked_replay_count": output.get("blocked_replay_count"),
            "approved_fact_count": output.get("approved_fact_count"),
            "trade_candidate_created_count": output.get("trade_candidate_created_count"),
            "paper_order_allowed_count": output.get("paper_order_allowed_count"),
            "execution_allowed_count": output.get("execution_allowed_count"),
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
    output["validation_errors"] = validate_phase6_shadow_strategy_runner(output)
    if output["validation_errors"]:
        output["status"] = "blocked"
    return output, entry


def write_phase6_shadow_strategy_runner(
    artifact: dict[str, Any],
    *,
    settings: Settings | None = None,
    record_event: bool = True,
    event_log_path: str | Path | None = None,
) -> tuple[Path, Path, Path, dict[str, Any]]:
    output = deepcopy(artifact)
    output_path, history_path, default_event_path = phase6_shadow_strategy_runner_paths(settings)
    event_path = Path(event_log_path or default_event_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    if record_event:
        output, _ = attach_phase6_shadow_strategy_runner_event_log(
            output,
            event_log_path=event_path,
            settings=settings,
        )
    else:
        output["validation_errors"] = validate_phase6_shadow_strategy_runner(output)
        if output["validation_errors"]:
            output["status"] = "blocked"
    output["runtime_artifact_path"] = str(output_path)
    output["history_log_path"] = str(history_path)
    output["validation_errors"] = validate_phase6_shadow_strategy_runner(output)
    if output["validation_errors"]:
        output["status"] = "blocked"
    output_path.write_text(json.dumps(output, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    history_record = {
        "schema_version": PHASE6_SHADOW_STRATEGY_RUNNER_SCHEMA_VERSION,
        "artifact_id": output.get("artifact_id"),
        "status": output.get("status"),
        "generated_at": output.get("generated_at"),
        "recorded_at": _now(),
        "replay_state": output.get("replay_state"),
        "source_approval_state": output.get("source_approval_state"),
        "variant_record_count": output.get("variant_record_count"),
        "active_replay_count": output.get("active_replay_count"),
        "blocked_replay_count": output.get("blocked_replay_count"),
        "approved_fact_count": output.get("approved_fact_count"),
        "trade_candidate_created_count": output.get("trade_candidate_created_count"),
        "paper_order_allowed_count": output.get("paper_order_allowed_count"),
        "execution_allowed_count": output.get("execution_allowed_count"),
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
