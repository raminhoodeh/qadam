"""EF-10 fail-closed certification for evidence-fit active paper trading."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from orchestrator.config import Settings
from orchestrator.qadam_canonical_contracts import AtomicArtifactStore
from orchestrator.qadam_operator_ready_common import (
    authority_flags,
    now_iso,
    read_json,
    read_jsonl,
    runtime_dir,
    unique_errors,
    validate_authority,
)
from orchestrator.release_contract import LIVE_CAPITAL_ENABLED

SCHEMA_VERSION = "qadam_evidence_fit_active_paper_trading_certification.v1"
PHASE_ID = "EF-10"
CERTIFICATION_ARTIFACT = "qadam_evidence_fit_active_paper_trading_certification.json"


def _age_seconds(value: Any, reference: datetime) -> float | None:
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except (TypeError, ValueError):
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return max(0.0, (reference - parsed.astimezone(timezone.utc)).total_seconds())


def evaluate_negative_safety_probe(probe_id: str, payload: dict[str, Any]) -> bool:
    """Return true only when the unsafe payload is rejected by its boundary."""

    if probe_id == "fixture_labeled_live":
        return not (
            payload.get("sample_or_fixture") is True
            and payload.get("availability_state") in {"live", "live_fresh"}
        )
    if probe_id == "stale_source_trigger":
        return not (
            payload.get("freshness_status") == "stale"
            and payload.get("trigger_state") == "active"
        )
    if probe_id == "context_only_alpaca_order":
        return not (
            payload.get("instrument_role") == "research_price_context"
            and payload.get("route") == "alpaca_paper"
        )
    if probe_id == "prediction_contract_alpaca_order":
        return not (
            payload.get("instrument_role") == "prediction_contract_context"
            and payload.get("route") == "alpaca_paper"
        )
    if probe_id == "missing_spread_treated_valid":
        return not (
            payload.get("spread") is None and payload.get("spread_state") == "valid"
        )
    if probe_id == "negative_control_hypothesis":
        return not (
            payload.get("negative_control") is True
            and payload.get("hypothesis_created") is True
        )
    if probe_id == "mixed_generation_join":
        return len(set(payload.get("generation_ids") or [])) <= 1
    if probe_id == "duplicate_second_order":
        return not (
            payload.get("duplicate_idempotency") is True
            and payload.get("second_order_created") is True
        )
    if probe_id == "discovery_claims_validated_edge":
        return not (
            payload.get("evidence_class") == "experimental_unvalidated"
            and payload.get("validated_edge_claimed") is True
        )
    if probe_id == "surface_broker_authority":
        return not (
            payload.get("surface") in {"model", "telegram", "dashboard"}
            and payload.get("broker_write_allowed") is True
        )
    if probe_id == "live_endpoint_enabled":
        return payload.get("live_capital_enabled") is False
    raise ValueError(f"unknown negative safety probe: {probe_id}")


def run_negative_safety_probes() -> list[dict[str, Any]]:
    unsafe_cases = [
        ("fixture_labeled_live", {"sample_or_fixture": True, "availability_state": "live_fresh"}),
        ("stale_source_trigger", {"freshness_status": "stale", "trigger_state": "active"}),
        ("context_only_alpaca_order", {"instrument_role": "research_price_context", "route": "alpaca_paper"}),
        ("prediction_contract_alpaca_order", {"instrument_role": "prediction_contract_context", "route": "alpaca_paper"}),
        ("missing_spread_treated_valid", {"spread": None, "spread_state": "valid"}),
        ("negative_control_hypothesis", {"negative_control": True, "hypothesis_created": True}),
        ("mixed_generation_join", {"generation_ids": ["generation-a", "generation-b"]}),
        ("duplicate_second_order", {"duplicate_idempotency": True, "second_order_created": True}),
        ("discovery_claims_validated_edge", {"evidence_class": "experimental_unvalidated", "validated_edge_claimed": True}),
        ("surface_broker_authority", {"surface": "telegram", "broker_write_allowed": True}),
        ("live_endpoint_enabled", {"live_capital_enabled": True}),
    ]
    return [
        {
            "probe_id": probe_id,
            "unsafe_payload_rejected": not evaluate_negative_safety_probe(
                probe_id, payload
            ),
            "status": (
                "passed"
                if not evaluate_negative_safety_probe(probe_id, payload)
                else "failed"
            ),
        }
        for probe_id, payload in unsafe_cases
    ]


def _check(check_id: str, passed: bool, evidence: Any) -> dict[str, Any]:
    return {
        "check_id": check_id,
        "status": "passed" if passed else "blocked",
        "evidence": evidence,
    }


def build_evidence_fit_certification(
    runtime: Path,
    *,
    generated_at: str,
) -> dict[str, Any]:
    reference = datetime.fromisoformat(generated_at.replace("Z", "+00:00"))
    if reference.tzinfo is None:
        reference = reference.replace(tzinfo=timezone.utc)
    source = read_json(runtime / "qadam_strategy_source_contract.json")
    instruments = read_json(runtime / "qadam_instrument_role_registry.json")
    trigger_checks = read_json(runtime / "qadam_trigger_factory_summary.json")
    triggers = [
        *read_jsonl(runtime / "qadam_current_event_triggers.jsonl"),
        *read_jsonl(runtime / "qadam_current_regime_observations.jsonl"),
        *read_jsonl(runtime / "qadam_current_market_dislocations.jsonl"),
    ]
    generation = read_json(runtime / "qadam_generation_integrity_checks.json")
    translation = read_json(runtime / "qadam_strategy_translation_summary.json")
    akber = read_json(runtime / "qadam_akber_filter_v3_checks.json")
    akber_fit = read_json(runtime / "qadam_akber_evidence_fit_checks.json")
    shadow = read_json(runtime / "qadam_forward_shadow_checks.json")
    router = read_json(runtime / "qadam_router_v3_paperops_checks.json")
    risk = read_json(runtime / "qadam_risk_router_alignment_checks.json")
    trial = read_json(runtime / "qadam_active_discovery_trial_checks.json")
    learning = read_json(runtime / "qadam_outcome_learning_promotion_checks.json")
    lifecycle = read_json(runtime / "qadam_paper_lineage_and_proof_checks.json")
    visibility = read_json(runtime / "qadam_evidence_fit_visibility_checks.json")
    dashboard = read_json(runtime / "qadam_evidence_fit_dashboard_summary.json")
    frontend = read_json(runtime / "qadam_dashboard_evidence_fit_frontend_checks.json")
    paperops = read_json(runtime / "paperops_autonomous_pass_summary.json")
    operator = read_json(runtime / "qadam_operator_service_status.json")
    phase_status = read_json(runtime / "qadam_evidence_fit_phase_status.json")

    active_triggers = [
        row
        for row in triggers
        if row.get("trigger_state") == "active"
        or row.get("regime_state") == "active"
        or row.get("dislocation_state") == "active"
    ]
    trigger_truth = all(
        row.get("sample_or_fixture") is False
        and (
            not row.get("expires_at")
            or datetime.fromisoformat(str(row["expires_at"]).replace("Z", "+00:00"))
            >= reference
        )
        for row in active_triggers
    )
    paperops_age = _age_seconds(paperops.get("generated_at"), reference)
    operator_age = _age_seconds(operator.get("generated_at"), reference)
    current_order_count = int(
        (dashboard.get("areas") or {}).get("orders", {}).get("metrics", [{}])[0].get("value", 0)
        if (dashboard.get("areas") or {}).get("orders", {}).get("metrics")
        else 0
    )
    checks = [
        _check("source_contract_41", source.get("source_count") == 41 and source.get("status") == "complete", {"count": source.get("source_count"), "status": source.get("status")}),
        _check("instrument_contract_19", instruments.get("instrument_count") == 19 and instruments.get("status") == "complete", {"count": instruments.get("instrument_count"), "status": instruments.get("status")}),
        _check("profile_specific_trigger_truth", trigger_checks.get("status") == "passed" and trigger_truth, {"active_trigger_count": len(active_triggers), "factory_status": trigger_checks.get("status")}),
        _check("same_generation_packets", generation.get("status") == "passed" and generation.get("mixed_generation_join_count") == 0, generation.get("mixed_generation_join_count")),
        _check("direction_resolution", translation.get("status") == "passed", translation.get("status")),
        _check("akber_profile_requirements", akber.get("status") == "passed" and akber_fit.get("status") == "passed", {"akber": akber.get("status"), "fit": akber_fit.get("status")}),
        _check("shadow_sequencing", shadow.get("implementation_ready") is True, shadow.get("status")),
        _check("risk_and_concentration", risk.get("status") == "passed" and risk.get("risk_envelope_unchanged") is True, {"status": risk.get("status"), "risk_envelope_unchanged": risk.get("risk_envelope_unchanged")}),
        _check("router_single_state_and_idempotency", router.get("status") == "passed" and router.get("duplicate_idempotency_count", 0) == 0, {"status": router.get("status"), "duplicates": router.get("duplicate_idempotency_count", 0)}),
        _check("active_trial_real_calendar", trial.get("status") == "passed" and trial.get("implementation_ready") is True and trial.get("simulated_time_used") is not True, {"state": trial.get("trial_state"), "eligible_days": trial.get("eligible_market_days_observed")}),
        _check("learning_proposal_only", learning.get("status") == "passed" and learning.get("risk_envelope_mutation_count", 0) == 0, {"status": learning.get("status"), "mutations": learning.get("risk_envelope_mutation_count", 0)}),
        _check("paper_lifecycle_and_proof_boundary", lifecycle.get("implementation_ready") is True and lifecycle.get("ambiguous_order_count", 0) == 0 and lifecycle.get("proof_credit_created_count", 0) == 0, {"status": lifecycle.get("status"), "proof_credit": lifecycle.get("proof_credit_created_count", 0)}),
        _check("dashboard_and_notification_truth", visibility.get("status") == "passed" and frontend.get("status") == "passed" and dashboard.get("notification", {}).get("live_send_attempted") is False, {"runtime": visibility.get("status"), "frontend": frontend.get("status"), "notification": dashboard.get("notification", {}).get("status")}),
        _check("historical_guarded_handoff_proof", dashboard.get("funnel", {}).get("historical_guarded_handoff_proof_count", 0) >= 1, dashboard.get("funnel", {}).get("historical_guarded_handoff_proof_count", 0)),
        _check("projection_created_no_order", current_order_count == 0 and visibility.get("paper_order_created_count", 0) == 0, current_order_count),
        _check("canonical_paperops_fresh_guarded", paperops.get("status") in {"ready_idle", "ready_actionable"} and paperops.get("validation_error_count", 0) == 0 and paperops.get("states", {}).get("closeout_status") == "ready" and paperops_age is not None and paperops_age <= 1800, {"status": paperops.get("status"), "age_seconds": paperops_age, "closeout": paperops.get("states", {}).get("closeout_status")}),
        _check("operator_observation_ready", operator.get("service_running") is True and operator.get("operational_ready") is True and operator.get("observation_ready") is True and operator_age is not None and operator_age <= 1800, {"status": operator.get("status"), "age_seconds": operator_age, "observation_ready": operator.get("observation_ready")}),
        _check("prior_phases_complete", all(next((row.get("pass") for row in phase_status.get("phases", []) if row.get("phase_id") == f"EF-{number}"), False) for number in range(9)), phase_status.get("implemented_through_phase")),
        _check("live_capital_disabled", LIVE_CAPITAL_ENABLED is False and paperops.get("safety", {}).get("live_capital_enabled") is False, {"release_contract": LIVE_CAPITAL_ENABLED, "paperops": paperops.get("safety", {}).get("live_capital_enabled")}),
    ]
    probes = run_negative_safety_probes()
    errors = [
        f"certification_check_failed:{row['check_id']}"
        for row in checks
        if row["status"] != "passed"
    ]
    errors.extend(
        f"negative_safety_probe_failed:{row['probe_id']}"
        for row in probes
        if row["status"] != "passed"
    )
    errors.extend(validate_authority(authority_flags(), prefix="certification"))
    errors = unique_errors(errors)
    return {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "qadam_evidence_fit_active_paper_trading_certification",
        "phase_id": PHASE_ID,
        "generated_at": generated_at,
        "status": "passed" if not errors else "blocked",
        "certified_for_autonomous_paper_observation": not errors,
        "empirical_trial_complete": trial.get("empirical_trial_complete") is True,
        "empirical_trial_state": trial.get("trial_state"),
        "checks": checks,
        "negative_safety_probes": probes,
        "check_count": len(checks),
        "passed_check_count": sum(row["status"] == "passed" for row in checks),
        "negative_probe_count": len(probes),
        "passed_negative_probe_count": sum(row["status"] == "passed" for row in probes),
        "validation_error_count": len(errors),
        "validation_errors": errors,
        "live_capital_enabled": False,
        "paper_order_created_by_certification": False,
        "broker_write_count": 0,
        "proof_credit_granted_count": 0,
        "authority": authority_flags(),
        "boundary": "Certification permits autonomous guarded paper observation only; it grants no live-capital or broker authority.",
    }


def validate_evidence_fit_certification(certification: dict[str, Any]) -> list[str]:
    errors = list(certification.get("validation_errors") or [])
    errors.extend(validate_authority(certification.get("authority") or {}))
    if certification.get("status") == "passed" and errors:
        errors.append("certification_passed_with_errors")
    if certification.get("live_capital_enabled") is not False:
        errors.append("certification_live_capital_enabled")
    if certification.get("paper_order_created_by_certification") is not False:
        errors.append("certification_created_paper_order")
    return unique_errors(errors)


def build_and_write_evidence_fit_certification(
    settings: Settings | None = None,
) -> tuple[dict[str, Any], list[str]]:
    runtime = runtime_dir(settings)
    certification = build_evidence_fit_certification(
        runtime,
        generated_at=now_iso(),
    )
    errors = validate_evidence_fit_certification(certification)
    AtomicArtifactStore(runtime).write_json(CERTIFICATION_ARTIFACT, certification)
    return certification, errors


__all__ = [
    "CERTIFICATION_ARTIFACT",
    "build_and_write_evidence_fit_certification",
    "build_evidence_fit_certification",
    "evaluate_negative_safety_probe",
    "run_negative_safety_probes",
    "validate_evidence_fit_certification",
]
