"""EF-0 reproducible evidence-fit baseline and contract audit.

This module records the current conversion funnel and field ownership without
creating a hypothesis, candidate, approval, order, proof record, or calendar
progress.  It is deliberately read-only apart from its own runtime artifacts.
"""

from __future__ import annotations

from collections import Counter
from pathlib import Path
from typing import Any

from orchestrator.config import Settings
from orchestrator.qadam_canonical_contracts import AtomicArtifactStore
from orchestrator.qadam_operator_ready_common import (
    ROOT,
    artifact_metadata,
    authority_flags,
    git_snapshot,
    now_iso,
    read_json,
    read_jsonl,
    runtime_dir,
    sha256_json,
    unique_errors,
    validate_authority,
)

SCHEMA_VERSION = "qadam_evidence_fit_baseline.v1"
PHASE_ID = "EF-0"

BASELINE_ARTIFACT = "qadam_evidence_fit_baseline.json"
OWNERSHIP_ARTIFACT = "qadam_evidence_gate_ownership_matrix.json"
DRIFT_ARTIFACT = "qadam_evidence_fit_contract_drift.json"
PHASE_STATUS_ARTIFACT = "qadam_evidence_fit_phase_status.json"

INPUT_ARTIFACTS = (
    "qsase_source_universe.json",
    "qsase_trading_universe.json",
    "qadam_pattern_score_v3_records.jsonl",
    "qadam_strategy_foundry_v3.json",
    "qadam_strategy_hypotheses_v3.jsonl",
    "qadam_akber_filter_v3_results.jsonl",
    "qadam_router_v3_why_not_trading_now.json",
    "qadam_experimental_paper_policy.json",
    "qadam_backtest_completion_coverage.json",
    "qadam_backtest_completion_provider_gate.json",
)

CODE_INPUTS = (
    "orchestrator/qadam_strategy_foundry_v3.py",
    "orchestrator/qadam_akber_filter_v3.py",
    "orchestrator/qadam_forward_shadow.py",
    "orchestrator/qadam_portfolio_risk_engine.py",
    "orchestrator/qadam_router_v3_paperops.py",
    "orchestrator/paperops_active_paper_trading_automation.py",
)


def _artifact_rows(runtime: Path, name: str) -> list[dict[str, Any]]:
    return read_jsonl(runtime / name) if name.endswith(".jsonl") else []


def _ownership_rows() -> list[dict[str, Any]]:
    fields = (
        ("historical_source_support", "EF-1 source contract", "EF-4 packet", "Akber Context"),
        ("current_trigger", "EF-2 trigger factory", "EF-4 packet", "Akber Catalyst"),
        ("actionable_direction", "EF-3 direction resolver", "EF-4 packet", "Foundry and Akber"),
        ("current_price", "provider-backed market context", "EF-4 packet", "Akber Confirmation"),
        (
            "volatility_context",
            "provider-backed market context",
            "EF-4 packet",
            "Akber Confirmation",
        ),
        (
            "volume_or_flow_confirmation",
            "provider-backed market context",
            "EF-4 packet",
            "Akber Confirmation",
        ),
        (
            "technical_confirmation",
            "supplemental technical provider",
            "EF-4 packet",
            "Akber Confirmation",
        ),
        ("pricing_gap_evidence", "EF-2 dislocation builder", "EF-4 packet", "Akber Confirmation"),
        ("expected_net_return", "Strategy Foundry", "EF-4 packet", "Akber Risk"),
        ("invalidation", "Strategy Foundry plus current volatility", "EF-4 packet", "Akber Risk"),
        ("reward_to_risk", "Strategy Foundry plus current volatility", "EF-4 packet", "Akber Risk"),
        ("spread", "provider-backed regular-session quote", "EF-4 packet", "Akber Execution"),
        ("liquidity", "provider-backed market context", "EF-4 packet", "Akber Execution"),
        ("paper_route", "EF-1 instrument registry", "EF-4 packet", "Akber Execution"),
        ("proxy_basis_risk", "EF-1 proxy registry", "EF-4 packet", "Akber and portfolio risk"),
        ("negative_control", "Pattern Score V3", "EF-3 and EF-4", "Foundry and Akber"),
        ("market_session", "provider-backed market context", "EF-4 packet", "Akber Execution"),
    )
    return [
        {
            "field": field,
            "canonical_producer": producer,
            "canonical_join": join,
            "canonical_consumer": consumer,
            "missing_value_policy": "typed_hold_never_adverse",
            "authority_created": False,
        }
        for field, producer, join, consumer in fields
    ]


def build_evidence_fit_baseline(
    runtime: Path,
    *,
    generated_at: str,
    repo: Path = ROOT,
) -> dict[str, Any]:
    source_universe = read_json(runtime / "qsase_source_universe.json")
    trading_universe = read_json(runtime / "qsase_trading_universe.json")
    pattern_rows = _artifact_rows(runtime, "qadam_pattern_score_v3_records.jsonl")
    foundry = read_json(runtime / "qadam_strategy_foundry_v3.json")
    hypotheses = _artifact_rows(runtime, "qadam_strategy_hypotheses_v3.jsonl")
    akber_rows = _artifact_rows(runtime, "qadam_akber_filter_v3_results.jsonl")
    router = read_json(runtime / "qadam_router_v3_why_not_trading_now.json")
    coverage = read_json(runtime / "qadam_backtest_completion_coverage.json")

    input_metadata = {name: artifact_metadata(runtime / name) for name in INPUT_ARTIFACTS}
    code_metadata = {name: artifact_metadata(repo / name) for name in CODE_INPUTS}
    counts = {
        "registered_source_count": len(source_universe.get("sources", [])),
        "watched_instrument_count": len(trading_universe.get("instruments", [])),
        "pattern_score_count": len(pattern_rows),
        "score_ready_count": sum(
            row.get("confidence_state") == "score_ready_for_tape" for row in pattern_rows
        ),
        "foundry_hypothesis_count": len(hypotheses),
        "foundry_reported_hypothesis_count": foundry.get("hypothesis_count"),
        "akber_review_count": len(akber_rows),
        "akber_decision_counts": dict(
            sorted(Counter(str(row.get("decision")) for row in akber_rows).items())
        ),
        "router_handoff_count": int(router.get("paperops_handoff_count", 0) or 0),
        "router_order_count": int(router.get("paper_order_count", 0) or 0),
        "provider_backed_historical_rows": int(
            coverage.get("provider_backed_historical_rows", 0) or 0
        ),
    }
    fingerprint_material = {
        "inputs": {name: row.get("sha256") for name, row in input_metadata.items()},
        "code": {name: row.get("sha256") for name, row in code_metadata.items()},
        "counts": counts,
    }
    baseline_id = f"evidence-fit-baseline:{sha256_json(fingerprint_material)[:24]}"
    ownership_rows = _ownership_rows()
    ownership = {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "qadam_evidence_gate_ownership_matrix",
        "phase_id": PHASE_ID,
        "generated_at": generated_at,
        "baseline_id": baseline_id,
        "field_count": len(ownership_rows),
        "fields": ownership_rows,
        "authority": authority_flags(),
    }

    drift_rows: list[dict[str, Any]] = []
    legacy_history_ready = sum(
        row.get("backtest_ready") is True
        for row in trading_universe.get("instruments", [])
        if isinstance(row, dict)
    )
    if coverage.get("status") == "complete" and legacy_history_ready == 0:
        drift_rows.append(
            {
                "drift_id": "legacy_universe_understates_historical_coverage",
                "severity": "high",
                "producer": "qsase_trading_universe.json",
                "canonical_truth": "qadam_backtest_completion_coverage.json",
                "repair_phase": "EF-1",
            }
        )
    if any(
        str(row.get("direction_hypothesis") or "").startswith("conditional_")
        for row in pattern_rows
    ):
        drift_rows.append(
            {
                "drift_id": "conditional_direction_not_resolved",
                "severity": "high",
                "producer": "qadam_pattern_score_v3_records.jsonl",
                "canonical_truth": "explicit_long_short_or_abstain_required",
                "repair_phase": "EF-3",
            }
        )
    if akber_rows and all(row.get("decision") == "hold_missing_context" for row in akber_rows):
        drift_rows.append(
            {
                "drift_id": "typed_current_triggers_not_joined_to_akber",
                "severity": "high",
                "producer": "market_context_packet.json",
                "canonical_truth": "profile_specific_trigger_required",
                "repair_phase": "EF-2_and_EF-4",
            }
        )
    drift = {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "qadam_evidence_fit_contract_drift",
        "phase_id": PHASE_ID,
        "generated_at": generated_at,
        "baseline_id": baseline_id,
        "drift_count": len(drift_rows),
        "drifts": drift_rows,
        "authority": authority_flags(),
    }
    baseline = {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "qadam_evidence_fit_baseline",
        "phase_id": PHASE_ID,
        "generated_at": generated_at,
        "status": "baseline_frozen",
        "baseline_id": baseline_id,
        "immutable_snapshot": True,
        "fingerprint": sha256_json(fingerprint_material),
        "git": git_snapshot(repo),
        "counts": counts,
        "input_artifacts": input_metadata,
        "code_inputs": code_metadata,
        "no_runtime_authority_created": True,
        "authority": authority_flags(),
    }
    return {"baseline": baseline, "ownership": ownership, "drift": drift}


def validate_evidence_fit_baseline(state: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    baseline = state.get("baseline", {})
    ownership = state.get("ownership", {})
    drift = state.get("drift", {})
    if baseline.get("immutable_snapshot") is not True or not baseline.get("fingerprint"):
        errors.append("baseline_not_immutable_or_checksummed")
    counts = baseline.get("counts", {})
    if counts.get("registered_source_count") != 41:
        errors.append("baseline_source_count_not_41")
    if counts.get("watched_instrument_count") != 19:
        errors.append("baseline_instrument_count_not_19")
    rows = ownership.get("fields", [])
    if ownership.get("field_count") != len(rows) or not rows:
        errors.append("baseline_ownership_matrix_incomplete")
    if len({row.get("field") for row in rows}) != len(rows):
        errors.append("baseline_field_has_multiple_canonical_owners")
    for payload, prefix in (
        (baseline, "baseline"),
        (ownership, "ownership"),
        (drift, "drift"),
    ):
        errors.extend(validate_authority(payload.get("authority", {}), prefix=prefix))
    return unique_errors(errors)


def build_and_write_evidence_fit_baseline(
    settings: Settings | None = None,
) -> tuple[dict[str, Any], dict[str, Any], list[str]]:
    runtime = runtime_dir(settings)
    store = AtomicArtifactStore(runtime)
    generated_at = now_iso()
    state = build_evidence_fit_baseline(runtime, generated_at=generated_at)
    errors = validate_evidence_fit_baseline(state)
    store.write_json(BASELINE_ARTIFACT, state["baseline"])
    store.write_json(OWNERSHIP_ARTIFACT, state["ownership"])
    store.write_json(DRIFT_ARTIFACT, state["drift"])
    status = {
        "schema_version": "qadam_evidence_fit_phase_status.v1",
        "artifact_type": "qadam_evidence_fit_phase_status",
        "generated_at": generated_at,
        "status": "blocked" if errors else "in_progress",
        "baseline_id": state["baseline"]["baseline_id"],
        "phases": [
            {
                "phase_id": "EF-0",
                "implementation_state": "blocked" if errors else "completed",
                "pass": not errors,
                "blockers": errors,
                "output_artifacts": [
                    BASELINE_ARTIFACT,
                    OWNERSHIP_ARTIFACT,
                    DRIFT_ARTIFACT,
                    PHASE_STATUS_ARTIFACT,
                ],
                "dashboard_impact": "none",
                "authority_impact": "none",
                "next_phase_allowed": not errors,
            },
            *[
                {
                    "phase_id": f"EF-{number}",
                    "implementation_state": "pending",
                    "pass": False,
                    "blockers": [],
                    "dashboard_impact": "none",
                    "authority_impact": "none",
                    "next_phase_allowed": False,
                }
                for number in range(1, 11)
            ],
        ],
        "validation_error_count": len(errors),
        "validation_errors": errors,
        "authority": authority_flags(),
    }
    store.write_json(PHASE_STATUS_ARTIFACT, status)
    return state, status, errors


def write_evidence_fit_phase_status(
    phase_results: dict[str, dict[str, Any]],
    settings: Settings | None = None,
    *,
    generated_at: str | None = None,
) -> dict[str, Any]:
    """Persist cumulative implementation truth without granting authority."""

    runtime = runtime_dir(settings)
    store = AtomicArtifactStore(runtime)
    previous = read_json(runtime / PHASE_STATUS_ARTIFACT)
    generated = generated_at or now_iso()
    phases: list[dict[str, Any]] = []
    all_errors: list[str] = []
    for number in range(0, 11):
        phase_id = f"EF-{number}"
        result = phase_results.get(phase_id)
        if result is None:
            prior = next(
                (row for row in previous.get("phases", []) if row.get("phase_id") == phase_id),
                {},
            )
            if prior.get("pass") is True:
                phases.append(prior)
            else:
                phases.append(
                    {
                        "phase_id": phase_id,
                        "implementation_state": "pending",
                        "pass": False,
                        "blockers": [],
                        "output_artifacts": prior.get("output_artifacts", []),
                        "dashboard_impact": "none",
                        "authority_impact": "none",
                        "next_phase_allowed": False,
                    }
                )
            continue
        errors = unique_errors(result.get("errors", []))
        all_errors.extend(f"{phase_id}:{error}" for error in errors)
        phases.append(
            {
                "phase_id": phase_id,
                "implementation_state": "completed" if not errors else "blocked",
                "pass": not errors,
                "blockers": errors,
                "output_artifacts": result.get("output_artifacts", []),
                "checks": result.get("checks", {}),
                "dashboard_impact": "none",
                "authority_impact": "none",
                "next_phase_allowed": not errors,
            }
        )
    implemented_through_number: int | None = None
    for number in range(0, 11):
        phase = next(row for row in phases if row["phase_id"] == f"EF-{number}")
        if phase.get("pass") is not True:
            break
        implemented_through_number = number
    status = {
        "schema_version": "qadam_evidence_fit_phase_status.v1",
        "artifact_type": "qadam_evidence_fit_phase_status",
        "generated_at": generated,
        "status": (
            "blocked"
            if all_errors
            else "complete"
            if implemented_through_number == 10
            else "in_progress"
        ),
        "baseline_id": previous.get("baseline_id"),
        "implemented_through_phase": (
            f"EF-{implemented_through_number}"
            if implemented_through_number is not None
            else None
        ),
        "later_phases_implemented": bool(
            implemented_through_number is not None and implemented_through_number > 4
        ),
        "phases": phases,
        "validation_error_count": len(all_errors),
        "validation_errors": all_errors,
        "authority": authority_flags(),
    }
    store.write_json(PHASE_STATUS_ARTIFACT, status)
    return status
