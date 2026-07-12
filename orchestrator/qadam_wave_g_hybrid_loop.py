"""Guarded Wave G bridge from validated edges to Qadam PaperOps review.

Wave G coordinates research and review artifacts. It deliberately cannot submit
hardware jobs, size positions, approve risk, create orders, or call a broker.
The only broker-write boundary remains the existing explicit PaperOps-2 Alpaca
paper POST gate.
"""

from __future__ import annotations

import ast
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
from typing import Any, Callable

from orchestrator.qsase_phase5_to10_completion import (
    build_akber_v2,
    build_router_and_handoff_v2,
    build_shadow_v2,
    build_strategy_foundry_v2,
)


SCHEMA_VERSION = "qadam.QuantumEdgeWaveGHybridLoop.v1"
CHECKPOINT_SCHEMA_VERSION = "qadam.QuantumEdgeWaveGCheckpoint.v1"
ARTIFACT_NAME = "qadam_quantum_edge_wave_g_hybrid_loop.json"
SITE_ARTIFACT_NAME = "quantum-edge-wave-g.json"
CHECKPOINT_DIR = "qadam_quantum_edge_wave_g_cycles"
EVENTS_ARTIFACT = "qadam_quantum_edge_wave_g_events.jsonl"
HISTORY_ARTIFACT = "qadam_quantum_edge_wave_g_history.jsonl"
POSTMORTEMS_ARTIFACT = "qadam_quantum_edge_wave_g_postmortems.jsonl"
PROPOSALS_ARTIFACT = "qadam_quantum_edge_wave_g_learning_proposals.jsonl"
OPERATIONAL_CONTEXT_ARTIFACT = "qadam_quantum_edge_wave_g_operational_context.json"
PAPER_OUTCOMES_ARTIFACT = "qadam_quantum_edge_wave_g_paper_outcomes.jsonl"

PUBLIC_LIFECYCLE_STATES = (
    "candidate noticed",
    "experiment prepared",
    "experiment executed",
    "result reproduced",
    "evidence strengthened",
    "edge validated",
    "strategy influenced",
    "paper outcome observed",
)
AUTOMATION_STAGES = (
    "source_refresh",
    "feature_construction",
    "classical_discovery",
    "local_quantum_simulation",
    "candidate_admission",
    "guarded_paper_integration",
    "learning_attribution",
    "hardware_experiment_preparation",
    "comparison_evaluation",
    "public_visibility",
)
POSITIVE_VALIDATION_CONTRIBUTIONS = {
    "quantum_strengthened",
    "joint_corroboration",
    "classical_preferred",
}
QUANTUM_POSITIVE_CONTRIBUTIONS = {
    "quantum_strengthened",
    "joint_corroboration",
}
RISK_REVIEW_CHECKS = (
    "paper_mode_confirmed",
    "kill_switch_clear",
    "source_freshness_clear",
    "duplicate_exposure_clear",
    "notional_within_policy_cap",
    "qctrl_paper_consultation_satisfied",
)
ZERO_AUTHORITY_FIELDS = (
    "candidate_promotion_allowed",
    "direct_broker_call_allowed",
    "execution_allowed",
    "execution_approval_allowed",
    "execution_approval_created",
    "hardware_scheduler_enabled",
    "hardware_submission_allowed",
    "live_capital_enabled",
    "paper_order_allowed",
    "paper_order_created",
    "paperops_bypass_allowed",
    "position_sizing_allowed",
    "proof_credit_allowed",
    "provider_call_allowed",
    "qctrl_bypass_allowed",
    "risk_approval_allowed",
    "risk_approval_created",
    "strategy_mutation_allowed",
    "telegram_command_authority",
    "telegram_send_allowed",
    "trade_candidate_creation_allowed",
)
FORBIDDEN_PUBLIC_KEYS = {
    "action_id",
    "api_key",
    "authorization",
    "credentials",
    "password",
    "provider_job_ids",
    "raw_broker_payload",
    "raw_provider_response",
    "secret",
    "token",
}


@dataclass(frozen=True)
class WaveGBudgets:
    max_candidates_per_cycle: int = 25
    max_local_circuit_evaluations: int = 250
    max_prepared_hardware_experiments: int = 1
    max_provider_calls_this_cycle: int = 0
    max_learning_proposals: int = 30


class WaveGInterrupted(RuntimeError):
    """Raised by the acceptance-only interruption hook after checkpointing."""


def _authority() -> dict[str, bool]:
    return {field: False for field in ZERO_AUTHORITY_FIELDS}


def _safe_dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _safe_list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def _safe_int(value: Any, default: int = 0) -> int:
    if isinstance(value, bool):
        return default
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _text(value: Any, fallback: str = "") -> str:
    resolved = str(value or "").strip()
    return resolved or fallback


def _slug(value: Any) -> str:
    return _text(value, "unclassified").lower().replace("&", "and").replace(" ", "_").replace("-", "_")


def _stable_hash(value: Any) -> str:
    encoded = json.dumps(value, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def _read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return payload if isinstance(payload, dict) else {}


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    records: list[dict[str, Any]] = []
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError:
        return []
    for line in lines:
        if not line.strip():
            continue
        try:
            payload = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(payload, dict):
            records.append(payload)
    return records


def _atomic_write(path: Path, payload: dict[str, Any]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    temporary.replace(path)
    return path


def _merge_jsonl(path: Path, records: list[dict[str, Any]], *, identity_key: str) -> Path:
    existing = _read_jsonl(path)
    indexed = {
        str(record.get(identity_key)): record
        for record in existing
        if record.get(identity_key)
    }
    for record in records:
        identity = str(record.get(identity_key) or "")
        if identity:
            indexed[identity] = record
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(
        "".join(json.dumps(record, sort_keys=True) + "\n" for record in indexed.values()),
        encoding="utf-8",
    )
    temporary.replace(path)
    return path


def _latest_hardware_public(runtime_dir: Path) -> dict[str, Any]:
    paths = sorted(
        (runtime_dir / "qadam_fire_opal_ibm_discovery").glob("*.public.json"),
        key=lambda path: path.stat().st_mtime,
        reverse=True,
    )
    return _read_json(paths[0]) if paths else {}


def load_wave_g_artifacts(runtime_dir: str | Path) -> dict[str, Any]:
    root = Path(runtime_dir)
    return {
        "wave_f": _read_json(root / "qadam_quantum_edge_wave_f_public_view.json"),
        "hybrid_candidates": _read_jsonl(root / "qadam_hybrid_candidates.jsonl"),
        "evaluations": _read_jsonl(root / "qadam_independent_quantum_value_evaluations.jsonl"),
        "evaluation_summary": _read_json(root / "qadam_independent_quantum_value_summary.json"),
        "source_rows": _read_jsonl(root / "qadam_source_operational_state.jsonl"),
        "point_in_time": _read_json(root / "qadam_point_in_time_evidence_checks.json"),
        "feature_manifest": _read_json(root / "qadam_quantum_discovery_manifest_contract.json"),
        "classical_discovery": _read_json(root / "qadam_classical_discovery_contract.json"),
        "local_quantum": _read_json(root / "qadam_local_quantum_discovery_contract.json"),
        "hardware_public": _latest_hardware_public(root),
        "operational_context": _read_json(root / OPERATIONAL_CONTEXT_ARTIFACT),
        "paper_outcomes": _read_jsonl(root / PAPER_OUTCOMES_ARTIFACT),
    }


def _candidate_operational_context(artifacts: dict[str, Any], candidate_id: str) -> dict[str, Any]:
    context = _safe_dict(artifacts.get("operational_context"))
    candidates = _safe_dict(context.get("candidates"))
    return _safe_dict(candidates.get(candidate_id))


def _validation_hashes(
    pattern: dict[str, Any],
    evaluation: dict[str, Any],
) -> tuple[str, str]:
    evidence = _safe_dict(pattern.get("validation_evidence"))
    holdout = _text(
        evaluation.get("holdout_manifest_hash")
        or evidence.get("untouched_holdout_hash")
        or pattern.get("holdout_manifest_hash")
    )
    training = _text(
        evaluation.get("training_validation_manifest_hash")
        or evidence.get("training_validation_hash")
        or pattern.get("training_validation_manifest_hash")
    )
    invalid_values = {"pending", "missing", "unavailable_pending_empirical_backfill"}
    if holdout.lower() in invalid_values:
        holdout = ""
    if training.lower() in invalid_values:
        training = ""
    return holdout, training


def build_validated_edge_admissions(
    artifacts: dict[str, Any],
    *,
    generated_at: str,
    budgets: WaveGBudgets,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    wave_f = _safe_dict(artifacts.get("wave_f"))
    patterns = _safe_list(_safe_dict(wave_f.get("pattern_recognition")).get("candidates"))
    evaluations = {
        row.get("candidate_id"): row
        for row in _safe_list(artifacts.get("evaluations"))
        if isinstance(row, dict) and row.get("candidate_id")
    }
    raw_candidates = {
        row.get("candidate_id"): row
        for row in _safe_list(artifacts.get("hybrid_candidates"))
        if isinstance(row, dict) and row.get("candidate_id")
    }
    admitted: list[dict[str, Any]] = []
    rejected: list[dict[str, Any]] = []
    for index, pattern in enumerate(patterns):
        candidate_id = _text(pattern.get("candidate_id"), f"unidentified:{index}")
        evaluation = _safe_dict(evaluations.get(candidate_id))
        raw = _safe_dict(raw_candidates.get(candidate_id))
        origin = _text(pattern.get("discovery_origin"), "classical_discovery")
        contribution = _text(
            evaluation.get("validation_contribution")
            or pattern.get("validation_contribution"),
            "not_tested",
        )
        empirical_count = max(
            _safe_int(pattern.get("empirical_evidence_count")),
            _safe_int(raw.get("empirical_evidence_count")),
        )
        holdout_hash, training_hash = _validation_hashes(pattern, evaluation)
        blockers: list[str] = []
        if index >= budgets.max_candidates_per_cycle:
            blockers.append("daily candidate review budget exhausted")
        if pattern.get("validated_edge") is not True:
            blockers.append("edge has not passed independent validation")
        if pattern.get("contract_fixture_only") is True or raw.get("contract_fixture_only") is True:
            blockers.append("engineering fixture cannot enter a trading strategy")
        if contribution not in POSITIVE_VALIDATION_CONTRIBUTIONS:
            blockers.append("validation result does not support strategy admission")
        if (
            empirical_count <= 0
            and evaluation.get("empirical_claim_allowed") is not True
            and not (holdout_hash and training_hash)
        ):
            blockers.append("provider-backed empirical evidence is missing")
        if origin in {"quantum_assisted_discovery", "joint_discovery"}:
            if evaluation.get("empirical_claim_allowed") is not True:
                blockers.append("quantum contribution has not survived untouched evidence")
            if not holdout_hash or not training_hash:
                blockers.append("frozen training and untouched holdout lineage is incomplete")
        elif not holdout_hash or not training_hash:
            blockers.append("classical validation lineage is incomplete")

        operational_context = _candidate_operational_context(artifacts, candidate_id)
        record = {
            "admission_id": f"wave-g-admission:{_stable_hash([candidate_id, contribution, holdout_hash, training_hash])[:24]}",
            "candidate_id": candidate_id,
            "generated_at": generated_at,
            "discovery_origin": origin,
            "validation_contribution": contribution,
            "quantum_contribution_to_strategy_evidence": contribution in QUANTUM_POSITIVE_CONTRIBUTIONS,
            "strategy_family_id": _text(
                pattern.get("strategy_family_id"),
                _slug(pattern.get("market")),
            ),
            "market": _text(pattern.get("market"), "Market not exported"),
            "instrument": _text((_safe_list(pattern.get("instruments")) or ["unknown"])[0], "unknown"),
            "holdout_manifest_hash": holdout_hash or None,
            "training_validation_manifest_hash": training_hash or None,
            "empirical_evidence_count": empirical_count,
            "admission_state": "validated_edge_admitted" if not blockers else "held_outside_strategy",
            "blockers": blockers,
            "operational_context": {
                "akber_context_complete": operational_context.get("akber_context_complete") is True,
                "akber_missing_inputs": [
                    _text(value)
                    for value in _safe_list(operational_context.get("akber_missing_inputs"))
                    if _text(value)
                ],
                "forward_shadow_validation": _safe_dict(
                    operational_context.get("forward_shadow_validation")
                ),
                "risk_review": {
                    key: _safe_dict(operational_context.get("risk_review")).get(key) is True
                    for key in RISK_REVIEW_CHECKS
                },
            },
            "authority": _authority(),
        }
        (admitted if not blockers else rejected).append(record)
    return admitted, rejected


def _edge_record(admission: dict[str, Any]) -> dict[str, Any]:
    return {
        "accepted_as_validated_edge": True,
        "validated_edge_id": f"wave-g-edge:{_stable_hash(admission['admission_id'])[:24]}",
        "source_pattern_id": admission["candidate_id"],
        "strategy_family": admission["strategy_family_id"],
        "instrument": admission["instrument"],
        "source_price_lineage": {
            "candidate_id": admission["candidate_id"],
            "discovery_origin": admission["discovery_origin"],
            "validation_contribution": admission["validation_contribution"],
            "holdout_manifest_hash": admission["holdout_manifest_hash"],
            "training_validation_manifest_hash": admission[
                "training_validation_manifest_hash"
            ],
        },
    }


def _recalculate_shadow_payload(
    payload: dict[str, Any],
    results: list[dict[str, Any]],
    rejections: list[dict[str, Any]],
) -> None:
    support_count = sum(row.get("shadow_supports_router") is True for row in results)
    payload["shadow_support_count"] = support_count
    payload["shadow_rejection_count"] = len(rejections)
    payload["status"] = (
        "qsase_shadow_simulator_v2_ready"
        if support_count
        else "qsase_shadow_simulator_v2_ready_with_holds"
    )


def _forward_shadow_passed(context: dict[str, Any]) -> bool:
    forward = _safe_dict(context.get("forward_shadow_validation"))
    return (
        forward.get("state") == "passed_on_matured_outcomes"
        and _safe_int(forward.get("complete_outcome_count")) >= 20
        and forward.get("leakage_audit_passed") is True
        and forward.get("costs_included") is True
    )


def _risk_review(
    router_handoff: dict[str, Any],
    admission: dict[str, Any],
    *,
    generated_at: str,
) -> dict[str, Any]:
    checks = _safe_dict(_safe_dict(admission.get("operational_context")).get("risk_review"))
    failed = [key for key in RISK_REVIEW_CHECKS if checks.get(key) is not True]
    eligible = not failed
    return {
        "risk_review_id": f"wave-g-risk:{_stable_hash([router_handoff.get('paperops_handoff_v2_id'), checks])[:24]}",
        "generated_at": generated_at,
        "candidate_id": admission["candidate_id"],
        "router_handoff_id": router_handoff.get("paperops_handoff_v2_id"),
        "state": (
            "within_policy_for_guarded_paperops_review"
            if eligible
            else "held_by_risk_review"
        ),
        "checks": {key: checks.get(key) is True for key in RISK_REVIEW_CHECKS},
        "failed_checks": failed,
        "eligible_for_guarded_paperops_review": eligible,
        "position_size_source": "existing risk and PaperOps policy only",
        "position_size_created": False,
        "risk_approval_created": False,
        "boundary": "Risk may hold this record; this review does not approve execution or create a position size.",
        "authority": _authority(),
    }


def _paperops_review_handoff(
    risk_review: dict[str, Any],
    hypothesis: dict[str, Any],
    *,
    generated_at: str,
) -> dict[str, Any]:
    return {
        "paperops_review_handoff_id": f"wave-g-paperops:{_stable_hash([risk_review['risk_review_id'], hypothesis.get('strategy_hypothesis_id')])[:24]}",
        "generated_at": generated_at,
        "strategy_hypothesis_id": hypothesis.get("strategy_hypothesis_id"),
        "candidate_id": risk_review["candidate_id"],
        "state": "ready_for_existing_guarded_paperops_review",
        "guarded_runner": "scripts/run_paperops_autonomous_pass.py",
        "only_submission_boundary": "orchestrator.paperops_alpaca_paper_post",
        "alpaca_route": "paper only",
        "handoff_is_not_order": True,
        "handoff_is_not_execution_approval": True,
        "paper_order_created": False,
        "broker_write_count": 0,
        "boundary": "The existing PaperOps runner must independently re-check every paper gate before Alpaca Paper can be reached.",
        "authority": _authority(),
    }


def build_guarded_paper_integration(
    admissions: list[dict[str, Any]],
    *,
    generated_at: str,
) -> dict[str, Any]:
    edge_records = [_edge_record(record) for record in admissions]
    pattern_records = [
        {
            "source_pattern_id": record["candidate_id"],
            "strategy_family": record["strategy_family_id"],
        }
        for record in admissions
    ]
    foundry, hypotheses, foundry_rejections = build_strategy_foundry_v2(
        edge_records,
        pattern_records,
        generated_at,
    )
    admissions_by_candidate = {record["candidate_id"]: record for record in admissions}
    for hypothesis in hypotheses:
        admission = admissions_by_candidate.get(hypothesis.get("source_pattern_id"), {})
        hypothesis["wave_g_lineage"] = {
            "candidate_id": admission.get("candidate_id"),
            "discovery_origin": admission.get("discovery_origin"),
            "validation_contribution": admission.get("validation_contribution"),
            "quantum_contribution_to_strategy_evidence": admission.get(
                "quantum_contribution_to_strategy_evidence"
            )
            is True,
        }

    market_packets: list[dict[str, Any]] = []
    for hypothesis in hypotheses:
        admission = admissions_by_candidate[hypothesis["source_pattern_id"]]
        context = _safe_dict(admission.get("operational_context"))
        missing = _safe_list(context.get("akber_missing_inputs"))
        if context.get("akber_context_complete") is not True and not missing:
            missing = ["current market confirmation", "source quorum", "invalidation"]
        market_packets.append(
            {
                "market_confirmation_packet_id": f"wave-g-market:{_stable_hash([hypothesis['strategy_hypothesis_id'], context])[:24]}",
                "strategy_hypothesis_id": hypothesis["strategy_hypothesis_id"],
                "akber_input_complete": context.get("akber_context_complete") is True,
                "missing_inputs": missing,
                "completeness_score": 1.0 if context.get("akber_context_complete") is True else 0.0,
            }
        )
    builder_context = {"market_packets": market_packets, "v1_strategy_hypotheses": []}
    akber, akber_records = build_akber_v2(builder_context, hypotheses, generated_at)
    shadow, shadow_results, counterfactuals, shadow_rejections = build_shadow_v2(
        builder_context,
        hypotheses,
        akber_records,
        generated_at,
    )
    for result in shadow_results:
        hypothesis = next(
            (
                row
                for row in hypotheses
                if row.get("strategy_hypothesis_id") == result.get("strategy_hypothesis_id")
            ),
            {},
        )
        admission = admissions_by_candidate.get(hypothesis.get("source_pattern_id"), {})
        if not _forward_shadow_passed(_safe_dict(admission.get("operational_context"))):
            result["shadow_supports_router"] = False
            result["replay_state"] = "waiting_for_mature_forward_outcomes"
            result["reason"] = "Forward outcomes have not matured under leakage-audited, cost-aware shadow validation."
            if not any(
                rejection.get("shadow_result_v2_id") == result.get("shadow_result_v2_id")
                for rejection in shadow_rejections
            ):
                shadow_rejections.append(
                    {
                        **result,
                        "artifact_type": "qsase_shadow_rejection_v2",
                        "shadow_rejection_id": f"wave-g-shadow-reject:{_stable_hash(result.get('shadow_result_v2_id'))[:24]}",
                        "rejection_reasons": ["mature_forward_shadow_validation_missing"],
                    }
                )
    _recalculate_shadow_payload(shadow, shadow_results, shadow_rejections)
    (
        router,
        router_decisions,
        router_scoreboard,
        why_not,
        router_handoffs,
        rejected_router_handoffs,
        upstream_handoff,
    ) = build_router_and_handoff_v2(
        builder_context,
        hypotheses,
        akber_records,
        shadow_results,
        generated_at,
    )

    hypotheses_by_id = {
        row.get("strategy_hypothesis_id"): row for row in hypotheses
    }
    admission_by_hypothesis = {
        row.get("strategy_hypothesis_id"): admissions_by_candidate.get(
            row.get("source_pattern_id"), {}
        )
        for row in hypotheses
    }
    risk_reviews = [
        _risk_review(
            handoff,
            admission_by_hypothesis.get(handoff.get("strategy_hypothesis_id"), {}),
            generated_at=generated_at,
        )
        for handoff in router_handoffs
    ]
    paperops_handoffs = [
        _paperops_review_handoff(
            review,
            hypotheses_by_id.get(
                next(
                    (
                        handoff.get("strategy_hypothesis_id")
                        for handoff in router_handoffs
                        if handoff.get("paperops_handoff_v2_id")
                        == review.get("router_handoff_id")
                    ),
                    None,
                ),
                {},
            ),
            generated_at=generated_at,
        )
        for review in risk_reviews
        if review.get("eligible_for_guarded_paperops_review") is True
    ]
    pipeline_records = []
    for hypothesis in hypotheses:
        hypothesis_id = hypothesis["strategy_hypothesis_id"]
        admission = admission_by_hypothesis[hypothesis_id]
        akber_record = next(
            (row for row in akber_records if row.get("strategy_hypothesis_id") == hypothesis_id),
            {},
        )
        shadow_record = next(
            (row for row in shadow_results if row.get("strategy_hypothesis_id") == hypothesis_id),
            {},
        )
        router_record = next(
            (row for row in router_decisions if row.get("strategy_hypothesis_id") == hypothesis_id),
            {},
        )
        risk_record = next(
            (row for row in risk_reviews if row.get("candidate_id") == admission.get("candidate_id")),
            {},
        )
        handoff_record = next(
            (row for row in paperops_handoffs if row.get("candidate_id") == admission.get("candidate_id")),
            {},
        )
        pipeline_records.append(
            {
                "candidate_id": admission["candidate_id"],
                "strategy_hypothesis_id": hypothesis_id,
                "stages": [
                    {"stage": "Trading Strategy", "state": "validated edge admitted"},
                    {
                        "stage": "Akber filter",
                        "state": _safe_dict(akber_record.get("decision")).get(
                            "filter_decision", "not reached"
                        ),
                    },
                    {
                        "stage": "forward shadow validation",
                        "state": shadow_record.get("replay_state", "not reached"),
                    },
                    {
                        "stage": "Router",
                        "state": _safe_dict(router_record.get("decision")).get(
                            "router_output", "not reached"
                        ),
                    },
                    {"stage": "Risk", "state": risk_record.get("state", "not reached")},
                    {
                        "stage": "guarded PaperOps",
                        "state": handoff_record.get("state", "not reached"),
                    },
                    {
                        "stage": "Alpaca Paper",
                        "state": "delegated to existing explicit PaperOps-2 boundary"
                        if handoff_record
                        else "not reached",
                    },
                ],
                "quantum_role": (
                    "documented validated strategy evidence only"
                    if admission.get("quantum_contribution_to_strategy_evidence") is True
                    else "no quantum strategy influence"
                ),
                "paper_order_created": False,
                "broker_write_count": 0,
                "authority": _authority(),
            }
        )

    return {
        "route_contract": {
            "stages": [
                "Trading Strategy",
                "Akber filter",
                "forward shadow validation",
                "Router",
                "Risk",
                "guarded PaperOps",
                "Alpaca Paper",
            ],
            "guarded_runner": "scripts/run_paperops_autonomous_pass.py",
            "only_broker_write_boundary": "orchestrator.paperops_alpaca_paper_post",
            "wave_g_calls_broker": False,
            "wave_g_submits_orders": False,
        },
        "strategy_foundry": foundry,
        "strategy_hypotheses": hypotheses,
        "strategy_rejections": foundry_rejections,
        "akber": akber,
        "akber_records": akber_records,
        "shadow": shadow,
        "shadow_results": shadow_results,
        "shadow_counterfactuals": counterfactuals,
        "shadow_rejections": shadow_rejections,
        "router": router,
        "router_decisions": router_decisions,
        "router_scoreboard": router_scoreboard,
        "why_not": why_not,
        "upstream_handoff": upstream_handoff,
        "router_handoffs": router_handoffs,
        "rejected_router_handoffs": rejected_router_handoffs,
        "risk_reviews": risk_reviews,
        "paperops_review_handoffs": paperops_handoffs,
        "pipeline_records": pipeline_records,
        "strategy_count": len(hypotheses),
        "risk_review_count": len(risk_reviews),
        "paperops_review_handoff_count": len(paperops_handoffs),
        "paper_order_created_count": 0,
        "broker_write_count": 0,
        "authority": _authority(),
    }


def build_postmortems_and_proposals(
    artifacts: dict[str, Any],
    integration: dict[str, Any],
    *,
    generated_at: str,
    budgets: WaveGBudgets,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    pipelines = {
        row.get("strategy_hypothesis_id"): row
        for row in _safe_list(integration.get("pipeline_records"))
        if isinstance(row, dict) and row.get("strategy_hypothesis_id")
    }
    postmortems: list[dict[str, Any]] = []
    proposals: list[dict[str, Any]] = []
    for outcome in _safe_list(artifacts.get("paper_outcomes")):
        if not isinstance(outcome, dict):
            continue
        hypothesis_id = outcome.get("strategy_hypothesis_id")
        pipeline = pipelines.get(hypothesis_id)
        if not pipeline or outcome.get("outcome_matured") is not True:
            continue
        postmortem_id = f"wave-g-postmortem:{_stable_hash([hypothesis_id, outcome.get('outcome_id')])[:24]}"
        attribution = {
            "classical_evidence": _text(
                outcome.get("classical_evidence_summary"),
                "Classical evidence contribution was not separately exported.",
            ),
            "quantum_contribution": _text(
                outcome.get("quantum_contribution_summary"),
                "No validated quantum contribution changed this decision.",
            ),
            "strategy_logic": _text(
                outcome.get("strategy_logic_summary"),
                "Strategy logic attribution is pending review.",
            ),
            "akber_and_risk": _text(
                outcome.get("akber_and_risk_summary"),
                "Akber and risk attribution is pending review.",
            ),
            "execution_quality": _text(
                outcome.get("execution_quality_summary"),
                "Execution-quality attribution is pending review.",
            ),
            "market_movement": _text(
                outcome.get("market_movement_summary"),
                "Market-movement attribution is pending review.",
            ),
        }
        postmortem = {
            "postmortem_id": postmortem_id,
            "generated_at": generated_at,
            "outcome_id": outcome.get("outcome_id"),
            "strategy_hypothesis_id": hypothesis_id,
            "result": _text(outcome.get("result"), "paper outcome observed"),
            "attribution": attribution,
            "attribution_factor_count": len(attribution),
            "paper_outcome_only": True,
            "proof_credit_allowed": False,
            "authority": _authority(),
        }
        postmortems.append(postmortem)
        for proposal_type in ("feature", "experiment", "strategy"):
            if len(proposals) >= budgets.max_learning_proposals:
                break
            proposals.append(
                {
                    "proposal_id": f"wave-g-proposal:{_stable_hash([postmortem_id, proposal_type])[:24]}",
                    "generated_at": generated_at,
                    "postmortem_id": postmortem_id,
                    "proposal_type": proposal_type,
                    "state": "pending governed review",
                    "summary": f"Review whether the {proposal_type} layer should change after this paper outcome.",
                    "automatic_application_allowed": False,
                    "human_review_required": True,
                    "authority": _authority(),
                }
            )
    return postmortems, proposals


def _source_refresh_stage(artifacts: dict[str, Any]) -> dict[str, Any]:
    rows = [row for row in _safe_list(artifacts.get("source_rows")) if isinstance(row, dict)]
    fresh = sum(row.get("freshness_state") in {"fresh", "current", "ok"} for row in rows)
    return {
        "state": "canonical source snapshot refreshed" if rows else "waiting for source adapter outputs",
        "source_count": len(rows),
        "fresh_source_count": fresh,
        "scope": "Rebuilds the canonical snapshot from current adapter outputs; it does not invent network observations.",
    }


def _feature_stage(artifacts: dict[str, Any]) -> dict[str, Any]:
    point_in_time = _safe_dict(artifacts.get("point_in_time"))
    manifest = _safe_dict(artifacts.get("feature_manifest"))
    ready = point_in_time.get("status") == "passed" and bool(manifest)
    return {
        "state": "point-in-time features ready" if ready else "waiting for point-in-time feature evidence",
        "point_in_time_checks_passed": point_in_time.get("status") == "passed",
        "shared_manifest_hash": manifest.get("shared_manifest_hash"),
        "contract_fixture_only": manifest.get("contract_fixture_only") is True,
    }


def _classical_stage(artifacts: dict[str, Any]) -> dict[str, Any]:
    classical = _safe_dict(artifacts.get("classical_discovery"))
    methods = _safe_list(classical.get("method_results"))
    return {
        "state": "classical result reproduced" if methods else "classical discovery unavailable",
        "method_count": len(methods),
        "shared_manifest_hash": classical.get("shared_manifest_hash"),
        "contract_fixture_only": classical.get("contract_fixture_only") is True,
        "run_mode": "content-addressed daily reuse",
    }


def _local_quantum_stage(
    artifacts: dict[str, Any], budgets: WaveGBudgets
) -> dict[str, Any]:
    local = _safe_dict(artifacts.get("local_quantum"))
    ideal = _safe_dict(local.get("ideal_result"))
    finite = _safe_dict(local.get("finite_shot_result"))
    evaluations = _safe_int(ideal.get("circuit_evaluation_count")) + _safe_int(
        finite.get("circuit_evaluation_count")
    )
    within_budget = evaluations <= budgets.max_local_circuit_evaluations
    return {
        "state": (
            "local quantum result reproduced"
            if local.get("status") == "local_quantum_discovery_ready" and within_budget
            else "local quantum simulation held"
        ),
        "circuit_evaluation_count": evaluations,
        "budget": budgets.max_local_circuit_evaluations,
        "within_budget": within_budget,
        "shared_manifest_hash": local.get("shared_manifest_hash"),
        "contract_fixture_only": local.get("contract_fixture_only") is True,
        "hardware_experiment_completed": False,
        "provider_calls_this_cycle": 0,
        "run_mode": "content-addressed daily reuse",
    }


def _hardware_preparation_stage(
    artifacts: dict[str, Any], budgets: WaveGBudgets
) -> dict[str, Any]:
    hardware = _safe_dict(artifacts.get("hardware_public"))
    prepared = bool(hardware.get("manifest_hash")) and hardware.get("lifecycle_status") in {
        "prepared",
        "blocked_provider_probe_failed",
        "ready_for_separate_authorization",
    }
    return {
        "state": "experiment prepared" if prepared else "experiment not prepared",
        "prepared_experiment_count": 1 if prepared else 0,
        "prepared_manifest_hash": hardware.get("manifest_hash"),
        "preparation_budget": budgets.max_prepared_hardware_experiments,
        "separate_exact_manifest_authorization_required": True,
        "hardware_execution_authorized_by_wave_g": False,
        "hardware_job_submitted_by_wave_g": False,
        "provider_calls_this_cycle": 0,
        "observed_provider_call_count": _safe_int(hardware.get("provider_call_count")),
    }


def _comparison_stage(artifacts: dict[str, Any]) -> dict[str, Any]:
    evaluations = [
        row for row in _safe_list(artifacts.get("evaluations")) if isinstance(row, dict)
    ]
    measured = [row for row in evaluations if row.get("empirical_claim_allowed") is True]
    strengthened = [
        row
        for row in measured
        if row.get("validation_contribution") in QUANTUM_POSITIVE_CONTRIBUTIONS
    ]
    return {
        "state": "comparison complete on matured outcomes" if measured else "waiting for naturally matured outcomes",
        "evaluation_count": len(evaluations),
        "mature_empirical_comparison_count": len(measured),
        "evidence_strengthened_count": len(strengthened),
        "forced_outcome_maturation_allowed": False,
    }


def _public_lifecycle(
    artifacts: dict[str, Any],
    admissions: list[dict[str, Any]],
    integration: dict[str, Any],
    postmortems: list[dict[str, Any]],
    stages: dict[str, Any],
) -> list[dict[str, Any]]:
    wave_f = _safe_dict(artifacts.get("wave_f"))
    patterns = _safe_list(_safe_dict(wave_f.get("pattern_recognition")).get("candidates"))
    hardware = _safe_dict(artifacts.get("hardware_public"))
    local = _safe_dict(artifacts.get("local_quantum"))
    comparison = _safe_dict(stages.get("comparison_evaluation"))
    completed = {
        "candidate noticed": bool(patterns),
        "experiment prepared": _safe_dict(stages.get("hardware_experiment_preparation")).get("state") == "experiment prepared",
        "experiment executed": hardware.get("hardware_experiment_completed") is True,
        "result reproduced": local.get("status") == "local_quantum_discovery_ready",
        "evidence strengthened": _safe_int(comparison.get("evidence_strengthened_count")) > 0,
        "edge validated": bool(admissions),
        "strategy influenced": _safe_int(integration.get("strategy_count")) > 0,
        "paper outcome observed": bool(postmortems),
    }
    explanations = {
        "candidate noticed": "A research relationship is visible; this is not yet a trading edge.",
        "experiment prepared": "A bounded hardware manifest exists, but Wave G cannot authorize or submit it.",
        "experiment executed": "Complete only after a separately authorized provider run produces a sanitized record.",
        "result reproduced": "The local simulator reproduced the engineering control; this is not market proof.",
        "evidence strengthened": "Complete only when independent untouched evidence adds measurable value.",
        "edge validated": "Complete only for non-fixture edges with frozen training and untouched holdout lineage.",
        "strategy influenced": "Complete only after a validated edge enters the governed strategy path.",
        "paper outcome observed": "Complete only after a naturally matured paper outcome has separate attribution.",
    }
    return [
        {
            "state": state,
            "status": "complete" if completed[state] else "not reached",
            "explanation": explanations[state],
        }
        for state in PUBLIC_LIFECYCLE_STATES
    ]


def _telegram_brief(
    admissions: list[dict[str, Any]],
    rejected: list[dict[str, Any]],
    integration: dict[str, Any],
    postmortems: list[dict[str, Any]],
    stages: dict[str, Any],
) -> dict[str, Any]:
    rejected_reason = (
        _text((_safe_list(rejected[0].get("blockers")) or [""])[0])
        if rejected
        else "no research blocker is currently exported"
    )
    first = (
        f"Today Qadam reviewed {len(admissions) + len(rejected)} pattern records. "
        f"{len(admissions)} passed the independent edge-admission checks and "
        f"{len(rejected)} stayed in research. The leading reason for holding a finding was that {rejected_reason}."
    )
    second = (
        f"The local quantum control is {_safe_dict(stages.get('local_quantum_simulation')).get('state', 'unavailable')}, "
        f"while hardware still requires separate authorization. {integration.get('strategy_count', 0)} strategies were influenced, "
        f"{integration.get('paperops_review_handoff_count', 0)} records reached guarded PaperOps review, and "
        f"{len(postmortems)} mature paper outcomes were learned from. Nothing in this update can place an order."
    )
    return {
        "text": first + "\n\n" + second,
        "paragraph_count": 2,
        "human_readable": True,
        "delivery_state": "ready for existing daily brief transport",
        "telegram_send_allowed": False,
        "telegram_command_authority": False,
    }


def _checkpoint_path(runtime_dir: Path, cycle_id: str) -> Path:
    return runtime_dir / CHECKPOINT_DIR / f"{cycle_id.split(':', 1)[-1]}.json"


def _cycle_input_hash(artifacts: dict[str, Any], budgets: WaveGBudgets) -> str:
    material = {
        "wave_f": artifacts.get("wave_f"),
        "hybrid_candidates": artifacts.get("hybrid_candidates"),
        "evaluations": artifacts.get("evaluations"),
        "source_rows": artifacts.get("source_rows"),
        "point_in_time": artifacts.get("point_in_time"),
        "feature_manifest": artifacts.get("feature_manifest"),
        "classical_discovery": artifacts.get("classical_discovery"),
        "local_quantum": artifacts.get("local_quantum"),
        "hardware_public": artifacts.get("hardware_public"),
        "operational_context": artifacts.get("operational_context"),
        "paper_outcomes": artifacts.get("paper_outcomes"),
        "budgets": asdict(budgets),
    }
    return _stable_hash(material)


def _record_checkpoint_stage(
    checkpoint_path: Path,
    checkpoint: dict[str, Any],
    name: str,
    output: Any,
    *,
    generated_at: str,
) -> None:
    checkpoint.setdefault("stage_outputs", {})[name] = output
    completed = checkpoint.setdefault("completed_stages", [])
    if name not in completed:
        completed.append(name)
    checkpoint["updated_at"] = generated_at
    _atomic_write(checkpoint_path, checkpoint)


def _stage(
    name: str,
    builder: Callable[[], Any],
    *,
    checkpoint: dict[str, Any],
    checkpoint_path: Path,
    generated_at: str,
    interrupt_after_stage: str | None,
) -> Any:
    if name in _safe_list(checkpoint.get("completed_stages")):
        return _safe_dict(checkpoint.get("stage_outputs")).get(name)
    output = builder()
    _record_checkpoint_stage(
        checkpoint_path,
        checkpoint,
        name,
        output,
        generated_at=generated_at,
    )
    if interrupt_after_stage == name:
        raise WaveGInterrupted(f"wave_g_interrupted_after:{name}")
    return output


def _contains_forbidden_public_key(value: Any) -> bool:
    if isinstance(value, dict):
        for key, child in value.items():
            if str(key).lower() in FORBIDDEN_PUBLIC_KEYS:
                return True
            if _contains_forbidden_public_key(child):
                return True
    elif isinstance(value, list):
        return any(_contains_forbidden_public_key(child) for child in value)
    return False


def _authority_escalated(value: Any) -> bool:
    if isinstance(value, dict):
        for key, child in value.items():
            if key in ZERO_AUTHORITY_FIELDS and child is not False:
                return True
            if _authority_escalated(child):
                return True
    elif isinstance(value, list):
        return any(_authority_escalated(child) for child in value)
    return False


def _imported_modules(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    modules: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            modules.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            modules.add(node.module)
    return modules


def validate_wave_g_broker_boundary(repo_root: str | Path) -> list[str]:
    """Prove research and quantum modules have no direct broker dependency."""

    root = Path(repo_root)
    research_modules = (
        "orchestrator/qadam_wave_g_hybrid_loop.py",
        "orchestrator/qadam_wave_f_public_view.py",
        "orchestrator/qadam_hybrid_candidate_merger.py",
        "orchestrator/qadam_independent_quantum_value.py",
        "orchestrator/qadam_classical_discovery.py",
        "orchestrator/qadam_local_quantum_discovery.py",
        "orchestrator/qadam_fire_opal_ibm_discovery.py",
    )
    forbidden_broker_prefixes = (
        "alpaca",
        "orchestrator.paperops_alpaca",
        "orchestrator.phase7_guarded_alpaca",
    )
    errors: list[str] = []
    for relative in research_modules:
        path = root / relative
        if not path.exists():
            errors.append(f"wave_g_boundary_module_missing:{relative}")
            continue
        for module in _imported_modules(path):
            if module.startswith(forbidden_broker_prefixes):
                errors.append(f"wave_g_research_imports_broker:{relative}:{module}")

    broker_path = root / "orchestrator/paperops_alpaca_paper_post.py"
    if not broker_path.exists():
        errors.append("wave_g_broker_boundary_module_missing")
    else:
        forbidden_research_prefixes = (
            "orchestrator.qadam_wave_g",
            "orchestrator.qadam_wave_f",
            "orchestrator.qadam_hybrid_candidate",
            "orchestrator.qadam_independent_quantum",
            "orchestrator.qadam_local_quantum",
            "orchestrator.qadam_fire_opal",
        )
        for module in _imported_modules(broker_path):
            if module.startswith(forbidden_research_prefixes):
                errors.append(f"wave_g_broker_imports_research:{module}")
    return errors


def validate_wave_g_payload(payload: dict[str, Any]) -> None:
    if payload.get("schema_version") != SCHEMA_VERSION:
        raise ValueError("wave_g_schema_invalid")
    lifecycle = _safe_list(payload.get("public_lifecycle"))
    if [row.get("state") for row in lifecycle] != list(PUBLIC_LIFECYCLE_STATES):
        raise ValueError("wave_g_public_lifecycle_contract_changed")
    if _authority_escalated(payload):
        raise ValueError("wave_g_authority_escalated")
    if _contains_forbidden_public_key(payload):
        raise ValueError("wave_g_forbidden_public_key")
    integration = _safe_dict(payload.get("paper_integration"))
    if _safe_int(integration.get("paper_order_created_count")) != 0:
        raise ValueError("wave_g_created_paper_order")
    if _safe_int(integration.get("broker_write_count")) != 0:
        raise ValueError("wave_g_broker_write_detected")
    if _safe_dict(integration.get("route_contract")).get("wave_g_calls_broker") is not False:
        raise ValueError("wave_g_broker_boundary_invalid")
    automation = _safe_dict(payload.get("automation"))
    if _safe_int(automation.get("provider_calls_this_cycle")) != 0:
        raise ValueError("wave_g_provider_call_detected")
    if automation.get("hardware_submission_allowed") is not False:
        raise ValueError("wave_g_hardware_submission_authority")
    for admission in _safe_list(payload.get("validated_edge_admissions")):
        if admission.get("admission_state") != "validated_edge_admitted":
            raise ValueError("wave_g_invalid_admission_state")
        if admission.get("blockers"):
            raise ValueError("wave_g_admitted_edge_has_blockers")
    for handoff in _safe_list(integration.get("paperops_review_handoffs")):
        if handoff.get("handoff_is_not_order") is not True:
            raise ValueError("wave_g_handoff_order_boundary_missing")
        if handoff.get("paper_order_created") is not False:
            raise ValueError("wave_g_handoff_created_order")
    brief = _safe_dict(payload.get("telegram_brief"))
    if brief.get("paragraph_count") != 2 or brief.get("telegram_send_allowed") is not False:
        raise ValueError("wave_g_telegram_boundary_invalid")
    expected_hash = _stable_hash(
        {
            key: value
            for key, value in payload.items()
            if key not in {"generated_at", "content_hash"}
        }
    )
    if payload.get("content_hash") != expected_hash:
        raise ValueError("wave_g_content_hash_mismatch")


def run_wave_g_cycle(
    runtime_dir: str | Path,
    *,
    site_root: str | Path | None = None,
    generated_at: str | None = None,
    evidence_date: str | None = None,
    budgets: WaveGBudgets | None = None,
    interrupt_after_stage: str | None = None,
) -> dict[str, Any]:
    root = Path(runtime_dir)
    root.mkdir(parents=True, exist_ok=True)
    active_budgets = budgets or WaveGBudgets()
    artifacts = load_wave_g_artifacts(root)
    input_hash = _cycle_input_hash(artifacts, active_budgets)
    current = generated_at or datetime.now(timezone.utc).isoformat()
    day = evidence_date or current[:10]
    cycle_id = f"wave-g-cycle:{_stable_hash([SCHEMA_VERSION, day, input_hash, asdict(active_budgets)])[:24]}"
    checkpoint_path = _checkpoint_path(root, cycle_id)
    checkpoint = _read_json(checkpoint_path)
    if checkpoint and checkpoint.get("input_hash") != input_hash:
        raise ValueError("wave_g_checkpoint_input_hash_mismatch")
    if not checkpoint:
        checkpoint = {
            "schema_version": CHECKPOINT_SCHEMA_VERSION,
            "cycle_id": cycle_id,
            "evidence_date": day,
            "input_hash": input_hash,
            "started_at": current,
            "updated_at": current,
            "completed_stages": [],
            "stage_outputs": {},
            "complete": False,
        }
        _atomic_write(checkpoint_path, checkpoint)
    cycle_generated_at = _text(checkpoint.get("started_at"), current)
    output_path = root / ARTIFACT_NAME
    if checkpoint.get("complete") is True:
        existing = _read_json(output_path)
        if existing.get("cycle_id") == cycle_id:
            validate_wave_g_payload(existing)
            if site_root is not None:
                _atomic_write(Path(site_root) / "status" / SITE_ARTIFACT_NAME, existing)
            return existing

    resumed = bool(checkpoint.get("completed_stages"))
    stages: dict[str, Any] = {}
    stages["source_refresh"] = _stage(
        "source_refresh",
        lambda: _source_refresh_stage(artifacts),
        checkpoint=checkpoint,
        checkpoint_path=checkpoint_path,
        generated_at=cycle_generated_at,
        interrupt_after_stage=interrupt_after_stage,
    )
    stages["feature_construction"] = _stage(
        "feature_construction",
        lambda: _feature_stage(artifacts),
        checkpoint=checkpoint,
        checkpoint_path=checkpoint_path,
        generated_at=cycle_generated_at,
        interrupt_after_stage=interrupt_after_stage,
    )
    stages["classical_discovery"] = _stage(
        "classical_discovery",
        lambda: _classical_stage(artifacts),
        checkpoint=checkpoint,
        checkpoint_path=checkpoint_path,
        generated_at=cycle_generated_at,
        interrupt_after_stage=interrupt_after_stage,
    )
    stages["local_quantum_simulation"] = _stage(
        "local_quantum_simulation",
        lambda: _local_quantum_stage(artifacts, active_budgets),
        checkpoint=checkpoint,
        checkpoint_path=checkpoint_path,
        generated_at=cycle_generated_at,
        interrupt_after_stage=interrupt_after_stage,
    )
    def build_admission_output() -> dict[str, Any]:
        admitted_records, rejected_records = build_validated_edge_admissions(
            artifacts,
            generated_at=cycle_generated_at,
            budgets=active_budgets,
        )
        return {"admitted": admitted_records, "rejected": rejected_records}

    admission_output = _stage(
        "candidate_admission",
        build_admission_output,
        checkpoint=checkpoint,
        checkpoint_path=checkpoint_path,
        generated_at=cycle_generated_at,
        interrupt_after_stage=interrupt_after_stage,
    )
    admissions = _safe_list(_safe_dict(admission_output).get("admitted"))
    rejected = _safe_list(_safe_dict(admission_output).get("rejected"))
    integration = _stage(
        "guarded_paper_integration",
        lambda: build_guarded_paper_integration(
            admissions,
            generated_at=cycle_generated_at,
        ),
        checkpoint=checkpoint,
        checkpoint_path=checkpoint_path,
        generated_at=cycle_generated_at,
        interrupt_after_stage=interrupt_after_stage,
    )
    learning_output = _stage(
        "learning_attribution",
        lambda: dict(
            zip(
                ("postmortems", "proposals"),
                build_postmortems_and_proposals(
                    artifacts,
                    _safe_dict(integration),
                    generated_at=cycle_generated_at,
                    budgets=active_budgets,
                ),
            )
        ),
        checkpoint=checkpoint,
        checkpoint_path=checkpoint_path,
        generated_at=cycle_generated_at,
        interrupt_after_stage=interrupt_after_stage,
    )
    postmortems = _safe_list(_safe_dict(learning_output).get("postmortems"))
    proposals = _safe_list(_safe_dict(learning_output).get("proposals"))
    stages["hardware_experiment_preparation"] = _stage(
        "hardware_experiment_preparation",
        lambda: _hardware_preparation_stage(artifacts, active_budgets),
        checkpoint=checkpoint,
        checkpoint_path=checkpoint_path,
        generated_at=cycle_generated_at,
        interrupt_after_stage=interrupt_after_stage,
    )
    stages["comparison_evaluation"] = _stage(
        "comparison_evaluation",
        lambda: _comparison_stage(artifacts),
        checkpoint=checkpoint,
        checkpoint_path=checkpoint_path,
        generated_at=cycle_generated_at,
        interrupt_after_stage=interrupt_after_stage,
    )
    lifecycle = _public_lifecycle(
        artifacts,
        admissions,
        _safe_dict(integration),
        postmortems,
        stages,
    )
    brief = _telegram_brief(
        admissions,
        rejected,
        _safe_dict(integration),
        postmortems,
        stages,
    )
    visibility = _stage(
        "public_visibility",
        lambda: {
            "public_lifecycle": lifecycle,
            "telegram_brief": brief,
        },
        checkpoint=checkpoint,
        checkpoint_path=checkpoint_path,
        generated_at=cycle_generated_at,
        interrupt_after_stage=interrupt_after_stage,
    )
    lifecycle = _safe_list(_safe_dict(visibility).get("public_lifecycle"))
    brief = _safe_dict(_safe_dict(visibility).get("telegram_brief"))

    payload = {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "qadam_quantum_edge_wave_g_hybrid_loop",
        "generated_at": cycle_generated_at,
        "evidence_date": day,
        "cycle_id": cycle_id,
        "status": (
            "wave_g_cycle_complete_with_guarded_handoffs"
            if _safe_int(_safe_dict(integration).get("paperops_review_handoff_count"))
            else "wave_g_cycle_complete_safe_idle"
        ),
        "plain_english_summary": (
            f"Wave G reviewed {len(admissions) + len(rejected)} pattern records, admitted {len(admissions)} validated edges, "
            f"and prepared {_safe_int(_safe_dict(integration).get('paperops_review_handoff_count'))} guarded PaperOps review handoffs. "
            "It made no provider call, order, risk approval, position size, or broker write."
        ),
        "validated_edge_admissions": admissions,
        "held_research_records": rejected,
        "paper_integration": integration,
        "postmortems": postmortems,
        "learning_proposals": proposals,
        "daily_stages": stages,
        "public_lifecycle": lifecycle,
        "telegram_brief": brief,
        "automation": {
            "cadence": {
                "daily": [
                    "source refresh",
                    "feature construction",
                    "classical discovery",
                    "local quantum simulation",
                ],
                "weekly_or_explicit_eligibility": "prepare one bounded hardware experiment",
                "hardware_submission": "separate exact-manifest authorization only",
                "comparison": "only after outcomes mature naturally",
            },
            "checkpointed": True,
            "resumed_from_checkpoint": resumed,
            "idempotency_key": cycle_id,
            "completed_stages": list(AUTOMATION_STAGES),
            "budgets": asdict(active_budgets),
            "provider_calls_this_cycle": 0,
            "hardware_submission_allowed": False,
            "forced_promotion_allowed": False,
            "forced_strategy_allowed": False,
            "forced_trade_allowed": False,
        },
        "authority": _authority(),
    }
    payload["content_hash"] = _stable_hash(
        {
            key: value
            for key, value in payload.items()
            if key != "generated_at"
        }
    )
    validate_wave_g_payload(payload)
    _atomic_write(output_path, payload)
    if site_root is not None:
        _atomic_write(Path(site_root) / "status" / SITE_ARTIFACT_NAME, payload)
    events = [
        {
            "event_id": f"{cycle_id}:{stage}",
            "cycle_id": cycle_id,
            "event_type": "wave_g_stage_completed",
            "stage": stage,
            "generated_at": cycle_generated_at,
            "authority": _authority(),
        }
        for stage in AUTOMATION_STAGES
    ]
    _merge_jsonl(root / EVENTS_ARTIFACT, events, identity_key="event_id")
    _merge_jsonl(
        root / HISTORY_ARTIFACT,
        [
            {
                "cycle_id": cycle_id,
                "generated_at": cycle_generated_at,
                "status": payload["status"],
                "content_hash": payload["content_hash"],
                "validated_edge_count": len(admissions),
                "paperops_review_handoff_count": _safe_int(
                    _safe_dict(integration).get("paperops_review_handoff_count")
                ),
                "provider_calls_this_cycle": 0,
            }
        ],
        identity_key="cycle_id",
    )
    _merge_jsonl(root / POSTMORTEMS_ARTIFACT, postmortems, identity_key="postmortem_id")
    _merge_jsonl(root / PROPOSALS_ARTIFACT, proposals, identity_key="proposal_id")
    checkpoint["complete"] = True
    checkpoint["content_hash"] = payload["content_hash"]
    checkpoint["updated_at"] = cycle_generated_at
    _atomic_write(checkpoint_path, checkpoint)
    return payload
