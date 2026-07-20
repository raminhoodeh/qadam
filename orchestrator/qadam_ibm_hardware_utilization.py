"""Receipt-bound utilization and follow-up for IBM hardware research results.

The provider lookup is explicit and read-only. Recurring research cycles consume
the resulting public artifact without contacting IBM or Q-CTRL, spending money,
or promoting a structural relationship into a strategy or trade.
"""

from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Any

from orchestrator.config import Settings
from orchestrator.qadam_quantum_discovery_evidence import stable_hash
from orchestrator.secrets import secret_value


SCHEMA_VERSION = "qadam.IbmHardwareUtilization.v1"
FOLLOWUP_SCHEMA_VERSION = "qadam.IbmHardwareFollowup.v1"
USAGE_ARTIFACT = "qadam_ibm_hardware_utilization.json"
FOLLOWUP_ARTIFACT = "qadam_ibm_hardware_followup.json"
RESULT_ARTIFACT = "qadam_ibm_full_history_experiment_result.json"
VALIDATION_ARTIFACT = "qadam_ibm_hardware_candidate_validation.json"
STORE_DIR = "qadam_fire_opal_ibm_discovery"

ZERO_AUTHORITY = {
    "validated_edge_creation_allowed": False,
    "strategy_hypothesis_creation_allowed": False,
    "trade_candidate_creation_allowed": False,
    "risk_approval_allowed": False,
    "execution_approval_allowed": False,
    "paper_order_allowed": False,
    "broker_write_allowed": False,
    "proof_credit_allowed": False,
    "live_capital_enabled": False,
    "hardware_scheduler_enabled": False,
    "automatic_paid_hardware_rerun_allowed": False,
}

FEATURE_EXPLANATIONS = {
    "causal_mapping_strength": (
        "How strongly the available evidence supports a plausible chain from a "
        "world event or source signal to a market reaction."
    ),
    "market_flow": (
        "How strongly observed market activity confirms, contradicts, or changes "
        "the source-led signal."
    ),
}


def _read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return payload if isinstance(payload, dict) else {}


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    temporary.replace(path)


def _parse_time(value: Any) -> datetime:
    parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _content_hash(payload: dict[str, Any]) -> str:
    return stable_hash({key: value for key, value in payload.items() if key != "content_hash"})


def _private_and_public_state(runtime: Path, manifest_hash: str) -> tuple[dict[str, Any], dict[str, Any]]:
    stem = manifest_hash[:24]
    root = runtime / STORE_DIR
    return (
        _read_json(root / f".{stem}.private.json"),
        _read_json(root / f"{stem}.public.json"),
    )


def collect_provider_usage(runtime_dir: str | Path, settings: Settings | None = None) -> dict[str, Any]:
    """Read the completed Q-CTRL/IBM workload and return sanitized usage facts."""

    from qiskit_ibm_runtime import QiskitRuntimeService

    from orchestrator.qadam_fire_opal_ibm_discovery import FireOpalSdkIbmGateway

    runtime = Path(runtime_dir)
    result = _read_json(runtime / RESULT_ARTIFACT)
    if result.get("status") != "completed" or result.get("provider_status") != "SUCCESS":
        raise ValueError("ibm_hardware_completed_result_required")
    manifest_hash = str(result.get("hardware_manifest_hash") or "")
    private, public = _private_and_public_state(runtime, manifest_hash)
    action_id = str(private.get("action_id") or "")
    submitted_at = private.get("submitted_at")
    completed_at = (public.get("receipt") or {}).get("completed_at")
    public_receipt = public.get("receipt") or {}
    if not action_id or not submitted_at or not completed_at:
        raise ValueError("ibm_hardware_private_timing_or_action_missing")

    resolved = settings or Settings.from_env()
    raw = FireOpalSdkIbmGateway(resolved).job_result(action_id=action_id)
    provider_job_ids = [str(value) for value in raw.get("provider_job_ids") or [] if value]
    unique_job_ids = sorted(set(provider_job_ids))
    if not unique_job_ids:
        raise ValueError("ibm_hardware_provider_job_missing")

    instance = secret_value("IBM_QUANTUM_INSTANCE", resolved)
    service = QiskitRuntimeService(
        channel="ibm_quantum_platform",
        token=secret_value("IBM_QUANTUM_TOKEN", resolved),
        instance=instance,
    )
    instance_record = next(
        (row for row in service.instances() if row.get("crn") == instance),
        {},
    )
    plan = str(instance_record.get("plan") or "unknown").lower()
    workload_metrics: list[dict[str, Any]] = []
    for job_id in unique_job_ids:
        job = service.job(job_id)
        metrics = job.metrics()
        workload_metrics.append(
            {
                "status": str(job.status()),
                "quantum_seconds": float((metrics.get("usage") or {}).get("quantum_seconds") or 0),
                "timestamps": metrics.get("timestamps") or {},
            }
        )
    quantum_seconds = sum(row["quantum_seconds"] for row in workload_metrics)
    account_usage = service.usage()
    provider_execution_timestamp = (raw.get("execution_metadata") or {}).get(
        "execution_timestamp"
    )

    return {
        "plan": plan,
        "provider_job_reference_count": len(provider_job_ids),
        "unique_ibm_workload_count": len(unique_job_ids),
        "circuit_count": public_receipt.get("circuit_count"),
        "total_shots": public_receipt.get("total_shots"),
        "quantum_seconds": quantum_seconds,
        "workload_statuses": sorted({row["status"] for row in workload_metrics}),
        "provider_execution_timestamp": provider_execution_timestamp,
        "submitted_at": submitted_at,
        "completed_at": completed_at,
        "account_usage_consumed_seconds": account_usage.get("usage_consumed_seconds"),
        "account_usage_limit_seconds": account_usage.get("usage_limit_seconds"),
        "account_usage_remaining_seconds": account_usage.get("usage_remaining_seconds"),
        "cost_usd": 0.0 if plan == "open" else None,
        "cost_state": (
            "no_incremental_charge_open_plan"
            if plan == "open"
            else "billing_record_required_for_paid_plan"
        ),
        "billing_fields_exposed_by_fire_opal_result": False,
        "source": "qctrl_receipt_plus_ibm_quantum_platform_readback",
        "queried_at": datetime.now(timezone.utc).isoformat(),
    }


def build_utilization_artifact(
    result: dict[str, Any],
    provider_usage: dict[str, Any],
    *,
    generated_at: str,
) -> dict[str, Any]:
    if result.get("status") != "completed" or result.get("provider_status") != "SUCCESS":
        raise ValueError("ibm_hardware_completed_result_required")
    submitted = _parse_time(provider_usage.get("submitted_at"))
    completed = _parse_time(provider_usage.get("completed_at"))
    wall_clock_seconds = (completed - submitted).total_seconds()
    if wall_clock_seconds < 0:
        raise ValueError("ibm_hardware_timing_invalid")
    plan = str(provider_usage.get("plan") or "unknown")
    cost_usd = provider_usage.get("cost_usd")
    payload = {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "qadam_ibm_hardware_utilization",
        "generated_at": generated_at,
        "status": "verified",
        "experiment_id": result.get("experiment_id"),
        "hardware_manifest_hash": result.get("hardware_manifest_hash"),
        "hardware_receipt_hash": result.get("receipt_hash"),
        "provider_plan": plan,
        "cost": {
            "currency": "USD",
            "billed_cost": cost_usd,
            "state": provider_usage.get("cost_state"),
            "authorized_ceiling_usd": 100.0,
            "ceiling_is_not_actual_cost": True,
            "source": provider_usage.get("source"),
        },
        "timing": {
            "submitted_at": submitted.isoformat(),
            "provider_execution_timestamp": provider_usage.get(
                "provider_execution_timestamp"
            ),
            "completed_at": completed.isoformat(),
            "provider_turnaround_seconds": round(wall_clock_seconds, 6),
            "provider_turnaround_includes_queue_and_result_retrieval": True,
            "ibm_quantum_seconds": provider_usage.get("quantum_seconds"),
            "quantum_seconds_definition": (
                "Time the IBM quantum system was committed to processing the workload."
            ),
        },
        "workload": {
            "circuit_count": provider_usage.get("circuit_count"),
            "provider_job_reference_count": provider_usage.get(
                "provider_job_reference_count"
            ),
            "unique_ibm_workload_count": provider_usage.get(
                "unique_ibm_workload_count"
            ),
            "total_shots": provider_usage.get("total_shots"),
            "workload_statuses": provider_usage.get("workload_statuses") or [],
        },
        "account_allowance_snapshot": {
            "usage_consumed_seconds": provider_usage.get(
                "account_usage_consumed_seconds"
            ),
            "usage_limit_seconds": provider_usage.get("account_usage_limit_seconds"),
            "usage_remaining_seconds": provider_usage.get(
                "account_usage_remaining_seconds"
            ),
        },
        "provider_result_exposed_direct_billing_fields": provider_usage.get(
            "billing_fields_exposed_by_fire_opal_result"
        )
        is True,
        "authority": dict(ZERO_AUTHORITY),
    }
    payload["content_hash"] = _content_hash(payload)
    errors = validate_utilization_artifact(payload)
    if errors:
        raise ValueError("ibm_hardware_utilization_invalid:" + ",".join(errors))
    return payload


def build_followup_artifact(
    result: dict[str, Any],
    utilization: dict[str, Any],
    *,
    generated_at: str,
    validation: dict[str, Any] | None = None,
) -> dict[str, Any]:
    validation = validation or {}
    candidates = []
    for source in result.get("research_candidates") or []:
        pair = [str(value) for value in source.get("feature_pair") or []]
        programme_material = {
            "candidate_id": source.get("candidate_id"),
            "receipt_hash": result.get("receipt_hash"),
            "feature_pair": pair,
        }
        programme_id = f"ibm-validation-program:{stable_hash(programme_material)[:24]}"
        candidate_validation = (
            validation
            if validation.get("candidate_id") == source.get("candidate_id")
            and validation.get("hardware_receipt_hash") == result.get("receipt_hash")
            and validation.get("status")
            in {
                "tested_historical_survivor_requires_forward_shadow",
                "tested_rejected_no_predictive_value",
            }
            else {}
        )
        validation_verdict = candidate_validation.get("verdict") or {}
        historical_survivor = validation_verdict.get("historical_survivor") is True
        historical_rejected = (
            candidate_validation.get("status") == "tested_rejected_no_predictive_value"
        )
        if historical_survivor:
            lifecycle_state = "historical_survivor_waiting_forward_shadow"
            current_meaning = (
                "The hardware-originated interaction survived its historical challenger, "
                "but it remains research-only until the frozen rule survives new market data."
            )
        elif historical_rejected:
            lifecycle_state = "historically_tested_not_predictive"
            current_meaning = (
                "The hardware-originated interaction was tested against future price "
                "outcomes and did not beat the simpler classical explanation. It is "
                "retained as rejected research evidence and cannot change a strategy."
            )
        else:
            lifecycle_state = "research_validation_active"
            current_meaning = (
                "IBM hardware preserved a nonlinear structure worth testing. It has "
                "not shown that the relationship predicts a profitable price move."
            )
        if candidate_validation:
            interaction_metrics = (
                (candidate_validation.get("models") or {})
                .get("hardware_originated_interaction", {})
                .get("holdout_metrics", {})
            )
            baseline_metrics = (
                (candidate_validation.get("models") or {})
                .get("additive_classical", {})
                .get("holdout_metrics", {})
            )
            historical_validation = {
                "status": candidate_validation.get("status"),
                "content_hash": candidate_validation.get("content_hash"),
                "verdict": validation_verdict.get("label"),
                "plain_english": validation_verdict.get("plain_english"),
                "holdout_start_at": (candidate_validation.get("split") or {}).get(
                    "holdout_start_at"
                ),
                "holdout_end_at": (candidate_validation.get("split") or {}).get(
                    "holdout_end_at"
                ),
                "interaction_trade_count": interaction_metrics.get("trade_count"),
                "interaction_mean_net_return": interaction_metrics.get(
                    "mean_net_return"
                ),
                "classical_trade_count": baseline_metrics.get("trade_count"),
                "classical_mean_net_return": baseline_metrics.get("mean_net_return"),
                "incremental_mean_net_return_per_opportunity": (
                    candidate_validation.get("comparison") or {}
                ).get("interaction_minus_baseline_mean_net_return_per_opportunity"),
                "multiple_testing_adjusted_p_value": (
                    candidate_validation.get("comparison") or {}
                ).get("multiple_testing_adjusted_p_value"),
                "rejection_reasons": validation_verdict.get("rejection_reasons") or [],
                "next_action": validation_verdict.get("next_action"),
                "validated_edge_created": False,
                "strategy_change_created": False,
                "trade_candidate_created": False,
            }
        else:
            historical_validation = {
                "status": "scheduled",
                "validated_edge_created": False,
                "strategy_change_created": False,
                "trade_candidate_created": False,
            }
        validation_step_state = "complete" if candidate_validation else "scheduled"
        forward_step_state = (
            "ready_for_untouched_forward_shadow"
            if historical_survivor
            else "closed_after_historical_rejection"
            if historical_rejected
            else "waiting_for_historical_validation"
        )
        strategy_step_state = (
            "gated_until_forward_validation"
            if historical_survivor
            else "closed_no_strategy_change"
            if historical_rejected
            else "gated_until_edge_validation"
        )
        candidates.append(
            {
                "validation_program_id": programme_id,
                "candidate_id": source.get("candidate_id"),
                "research_goal_id": f"research-goal:{stable_hash(programme_material)[:24]}",
                "research_question": source.get("research_question"),
                "feature_pair": pair,
                "feature_explanations": {
                    feature: FEATURE_EXPLANATIONS.get(
                        feature, "A normalized input used by the frozen research model."
                    )
                    for feature in pair
                },
                "structural_score": source.get("structural_score"),
                "lifecycle_state": lifecycle_state,
                "current_meaning": current_meaning,
                "historical_validation": historical_validation,
                "automatic_research_steps": [
                    {
                        "order": 1,
                        "key": "receipt_and_identity",
                        "label": "Preserve the result and its lineage",
                        "state": "complete",
                    },
                    {
                        "order": 2,
                        "key": "matched_classical_challenger",
                        "label": "Compare it with the strongest conventional method",
                        "state": validation_step_state,
                    },
                    {
                        "order": 3,
                        "key": "historical_predictive_validation",
                        "label": "Test whether it predicts future returns after costs",
                        "state": validation_step_state,
                    },
                    {
                        "order": 4,
                        "key": "untouched_forward_shadow",
                        "label": "Observe the frozen rule on new market data",
                        "state": forward_step_state,
                    },
                    {
                        "order": 5,
                        "key": "strategy_and_akber_review",
                        "label": "Consider strategy mapping and Akber's 6-Stage Filter",
                        "state": strategy_step_state,
                    },
                ],
                "hardware_repeat": {
                    "state": "operator_authorization_required",
                    "reason": (
                        "The first run carried an elevated measurement-error warning; a "
                        "repeat should use a healthier device and identical frozen inputs."
                    ),
                    "automatic_paid_rerun_allowed": False,
                },
                "validated_edge_created": False,
                "strategy_hypothesis_created": False,
                "trade_candidate_created": False,
                "paper_order_created": False,
                "proof_credit_created": False,
                "authority": dict(ZERO_AUTHORITY),
            }
        )
    envelope = result.get("input_envelope") or {}
    terminal_rejected = bool(candidates) and all(
        candidate.get("lifecycle_state") == "historically_tested_not_predictive"
        for candidate in candidates
    )
    forward_required = any(
        candidate.get("lifecycle_state") == "historical_survivor_waiting_forward_shadow"
        for candidate in candidates
    )
    status = (
        "no_hardware_candidate"
        if not candidates
        else "validation_program_complete_no_edge"
        if terminal_rejected
        else "forward_shadow_required"
        if forward_required
        else "validation_program_active"
    )
    payload = {
        "schema_version": FOLLOWUP_SCHEMA_VERSION,
        "artifact_type": "qadam_ibm_hardware_followup",
        "generated_at": generated_at,
        "status": status,
        "experiment_id": result.get("experiment_id"),
        "hardware_receipt_hash": result.get("receipt_hash"),
        "utilization_content_hash": utilization.get("content_hash"),
        "candidate_count": len(candidates),
        "scope": {
            "canonical_source_count": envelope.get("canonical_source_count"),
            "canonical_instrument_count": envelope.get("canonical_instrument_count"),
            "historically_scored_source_count": envelope.get(
                "historically_scored_source_count"
            ),
            "score_plane_instrument_count": envelope.get(
                "score_plane_instrument_count"
            ),
            "scoreable_row_count": envelope.get("paired_score_label_row_count"),
            "prototype_count": (envelope.get("prototype_audit") or {}).get(
                "prototype_count"
            ),
        },
        "candidates": candidates,
        "next_autonomous_action": (
            "none_historical_candidate_rejected"
            if terminal_rejected
            else "begin_untouched_forward_shadow"
            if forward_required
            else "matched_classical_and_historical_predictive_validation"
            if candidates
            else "none"
        ),
        "current_strategy_impact_count": 0,
        "current_trade_impact_count": 0,
        "current_proof_credit_count": 0,
        "boundary": (
            "The result is automatically used as research input. It cannot alter a "
            "strategy, pass Akber, create an order, or earn proof until independent "
            "predictive validation succeeds. A rejected result is retained so later "
            "research cannot silently rediscover and promote the same failed claim."
        ),
        "authority": dict(ZERO_AUTHORITY),
    }
    payload["content_hash"] = _content_hash(payload)
    errors = validate_followup_artifact(payload)
    if errors:
        raise ValueError("ibm_hardware_followup_invalid:" + ",".join(errors))
    return payload


def validate_utilization_artifact(payload: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if payload.get("schema_version") != SCHEMA_VERSION:
        errors.append("schema_invalid")
    if payload.get("artifact_type") != "qadam_ibm_hardware_utilization":
        errors.append("artifact_type_invalid")
    if payload.get("status") != "verified":
        errors.append("status_invalid")
    if not payload.get("hardware_receipt_hash"):
        errors.append("receipt_hash_missing")
    timing = payload.get("timing") or {}
    if float(timing.get("provider_turnaround_seconds") or 0) <= 0:
        errors.append("provider_turnaround_invalid")
    if float(timing.get("ibm_quantum_seconds") or 0) <= 0:
        errors.append("quantum_seconds_invalid")
    cost = payload.get("cost") or {}
    if payload.get("provider_plan") == "open" and cost.get("billed_cost") != 0.0:
        errors.append("open_plan_cost_invalid")
    if any(value is not False for value in (payload.get("authority") or {}).values()):
        errors.append("authority_escalated")
    if payload.get("content_hash") != _content_hash(payload):
        errors.append("content_hash_invalid")
    return errors


def validate_followup_artifact(payload: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if payload.get("schema_version") != FOLLOWUP_SCHEMA_VERSION:
        errors.append("schema_invalid")
    if payload.get("artifact_type") != "qadam_ibm_hardware_followup":
        errors.append("artifact_type_invalid")
    candidates = payload.get("candidates")
    if not isinstance(candidates, list):
        errors.append("candidates_invalid")
        candidates = []
    if payload.get("candidate_count") != len(candidates):
        errors.append("candidate_count_invalid")
    if payload.get("status") not in {
        "validation_program_active",
        "validation_program_complete_no_edge",
        "forward_shadow_required",
        "no_hardware_candidate",
    }:
        errors.append("status_invalid")
    for candidate in candidates:
        if candidate.get("lifecycle_state") not in {
            "research_validation_active",
            "historically_tested_not_predictive",
            "historical_survivor_waiting_forward_shadow",
        }:
            errors.append("candidate_lifecycle_invalid")
        if len(candidate.get("automatic_research_steps") or []) != 5:
            errors.append("candidate_steps_invalid")
        historical = candidate.get("historical_validation") or {}
        if historical.get("status") in {
            "tested_historical_survivor_requires_forward_shadow",
            "tested_rejected_no_predictive_value",
        }:
            if not historical.get("content_hash"):
                errors.append("candidate_historical_validation_hash_missing")
            for field in (
                "validated_edge_created",
                "strategy_change_created",
                "trade_candidate_created",
            ):
                if historical.get(field) is not False:
                    errors.append(f"candidate_historical_boundary_breach:{field}")
        for field in (
            "validated_edge_created",
            "strategy_hypothesis_created",
            "trade_candidate_created",
            "paper_order_created",
            "proof_credit_created",
        ):
            if candidate.get(field) is not False:
                errors.append(f"candidate_boundary_breach:{field}")
        if any(value is not False for value in (candidate.get("authority") or {}).values()):
            errors.append("candidate_authority_escalated")
    if any(
        int(payload.get(field) or 0) != 0
        for field in (
            "current_strategy_impact_count",
            "current_trade_impact_count",
            "current_proof_credit_count",
        )
    ):
        errors.append("downstream_impact_created")
    if any(value is not False for value in (payload.get("authority") or {}).values()):
        errors.append("authority_escalated")
    if payload.get("content_hash") != _content_hash(payload):
        errors.append("content_hash_invalid")
    return sorted(set(errors))


def write_artifacts(
    runtime_dir: str | Path,
    utilization: dict[str, Any],
    followup: dict[str, Any],
) -> dict[str, Path]:
    runtime = Path(runtime_dir)
    _write_json(runtime / USAGE_ARTIFACT, utilization)
    _write_json(runtime / FOLLOWUP_ARTIFACT, followup)
    return {
        "utilization": runtime / USAGE_ARTIFACT,
        "followup": runtime / FOLLOWUP_ARTIFACT,
    }


def refresh_followup(runtime_dir: str | Path, *, generated_at: str) -> dict[str, Any]:
    """Refresh the no-provider follow-up during recurring research cycles."""

    runtime = Path(runtime_dir)
    result = _read_json(runtime / RESULT_ARTIFACT)
    utilization = _read_json(runtime / USAGE_ARTIFACT)
    validation = _read_json(runtime / VALIDATION_ARTIFACT)
    if validate_utilization_artifact(utilization):
        return {}
    followup = build_followup_artifact(
        result,
        utilization,
        generated_at=generated_at,
        validation=validation,
    )
    _write_json(runtime / FOLLOWUP_ARTIFACT, followup)
    return followup


__all__ = [
    "FOLLOWUP_ARTIFACT",
    "FOLLOWUP_SCHEMA_VERSION",
    "SCHEMA_VERSION",
    "USAGE_ARTIFACT",
    "VALIDATION_ARTIFACT",
    "build_followup_artifact",
    "build_utilization_artifact",
    "collect_provider_usage",
    "refresh_followup",
    "validate_followup_artifact",
    "validate_utilization_artifact",
    "write_artifacts",
]
