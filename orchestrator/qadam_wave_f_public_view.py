"""Public-safe Wave F views for Pattern Recognition, Quantum Edge, and strategies."""

from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Any

from orchestrator.qadam_quantum_discovery_evidence import stable_hash

SCHEMA_VERSION = "qadam.QuantumEdgeWaveFPublicView.v1"
ARTIFACT_NAME = "qadam_quantum_edge_wave_f_public_view.json"
SITE_ARTIFACT_NAME = "quantum-edge-wave-f.json"

PATTERN_ROUTE = {"module_id": "patterns", "view_id": "findings"}
QUANTUM_EDGE_ROUTE = {"module_id": "patterns", "view_id": "nonlinear"}
STRATEGY_ROUTE = {"module_id": "decide", "view_id": "strategies"}

DISCOVERY_ORIGINS = {
    "classical_discovery",
    "quantum_assisted_discovery",
    "joint_discovery",
}
VALIDATION_CONTRIBUTIONS = {
    "not_tested",
    "quantum_strengthened",
    "joint_corroboration",
    "classical_preferred",
    "weakened",
    "inconclusive",
    "not_measurable",
    "failed_safely",
}
PROOF_STATES = {
    "quantum_edge_not_yet_proven",
    "provisional_quantum_evidence",
    "validated_quantum_contribution",
    "quantum_contribution_decayed",
}
ZERO_AUTHORITY_FIELDS = (
    "validated_edge_creation_allowed",
    "strategy_hypothesis_creation_allowed",
    "trade_candidate_creation_allowed",
    "risk_approval_allowed",
    "position_sizing_allowed",
    "execution_approval_allowed",
    "execution_allowed",
    "paper_order_allowed",
    "direct_broker_call_allowed",
    "broker_write_allowed",
    "proof_credit_allowed",
    "paper_proof_ledger_credit_allowed",
    "hardware_submission_allowed",
    "hardware_scheduler_enabled",
    "dashboard_command_authority",
    "telegram_command_authority",
    "live_capital_enabled",
)
FORBIDDEN_PUBLIC_KEYS = {
    "action_id",
    "api_key",
    "backend_name",
    "credentials",
    "password",
    "provider_job_ids",
    "qasm_circuits",
    "raw_provider_response",
    "secret",
    "token",
}


def _authority() -> dict[str, bool]:
    return {field_name: False for field_name in ZERO_AUTHORITY_FIELDS}


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
    rows: list[dict[str, Any]] = []
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
            rows.append(payload)
    return rows


def _contains_forbidden_key(value: Any) -> bool:
    if isinstance(value, dict):
        for key, child in value.items():
            if str(key).lower() in FORBIDDEN_PUBLIC_KEYS:
                return True
            if _contains_forbidden_key(child):
                return True
    elif isinstance(value, (list, tuple)):
        return any(_contains_forbidden_key(child) for child in value)
    return False


def _as_list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def _text(value: Any, fallback: str) -> str:
    resolved = str(value or "").strip()
    return resolved or fallback


def _first(values: Any, fallback: str) -> str:
    rows = [str(value).strip() for value in _as_list(values) if str(value).strip()]
    return rows[0] if rows else fallback


def _origin_label(origin: str) -> str:
    return {
        "classical_discovery": "Classical",
        "quantum_assisted_discovery": "Quantum-assisted",
        "joint_discovery": "Joint classical + quantum",
    }.get(origin, "Unknown origin")


def _validation_label(value: str) -> str:
    return {
        "not_tested": "Not independently tested",
        "quantum_strengthened": "Quantum added holdout value",
        "joint_corroboration": "Both methods corroborated it",
        "classical_preferred": "Classical method preferred",
        "weakened": "Evidence weakened",
        "inconclusive": "Comparison inconclusive",
        "not_measurable": "Not measurable yet",
        "failed_safely": "Evaluation failed safely",
    }.get(value, "Validation state unavailable")


def _legacy_pattern(row: dict[str, Any]) -> dict[str, Any]:
    blockers = [
        str(value)
        for value in _as_list(row.get("blocked_by") or row.get("blockers"))
        if value
    ]
    source_chain = [str(value) for value in _as_list(row.get("source_chain")) if value]
    stage = _text(row.get("stage") or row.get("stage_key"), "research_observation")
    validated = stage == "validated_edge" or row.get("readiness", {}).get(
        "validated_edge"
    ) is True
    return {
        "candidate_id": _text(row.get("pattern_id"), "unidentified-classical-pattern"),
        "title": _text(row.get("title"), "Classical research observation"),
        "discovery_origin": "classical_discovery",
        "discovery_origin_label": "Classical",
        "validation_contribution": "classical_preferred" if validated else "not_tested",
        "validation_contribution_label": (
            "Validated by the classical evidence policy"
            if validated
            else "Not independently tested"
        ),
        "relationship": _text(
            row.get("plain_english_question") or row.get("detected_signal"),
            row.get("relationship_type") or "Relationship under review",
        ),
        "source_chain": source_chain,
        "source_chain_summary": (
            ", ".join(source_chain)
            if source_chain
            else "No contributing source chain was exported."
        ),
        "market": _text(
            row.get("target_market") or row.get("market_affected"),
            "Market not exported",
        ),
        "instruments": [
            str(value)
            for value in _as_list(
                row.get("target_instruments") or row.get("instrument_symbols")
            )
            if value
        ],
        "interpretation": _text(
            row.get("what_qadam_thinks") or row.get("plain_english_analysis"),
            "Qadam has not exported an interpretation.",
        ),
        "confirmation": _text(
            row.get("what_would_confirm"),
            "Provider-backed outcomes and an untouched holdout must confirm it.",
        ),
        "falsifier": _first(
            row.get("falsifiers"),
            _text(
                row.get("what_blocks_trade"),
                "The relationship fails on provider-backed untouched evidence.",
            ),
        ),
        "evidence_state": _text(
            row.get("stage_label") or row.get("lifecycle_label"),
            stage.replace("_", " "),
        ),
        "lifecycle_stage": stage,
        "blocker": _first(blockers, "No explicit research blocker was exported."),
        "next_action": _text(
            row.get("next_action"),
            "Collect outcomes and run the frozen historical test.",
        ),
        "execution_mode": "classical_pattern_engine",
        "execution_mode_label": "Classical pattern engine",
        "quantum_involved": False,
        "hardware_receipt_verified": False,
        "contract_fixture_only": False,
        "empirical_evidence_count": 0,
        "method_evidence": [],
        "strategy_family_id": row.get("strategy_family_id"),
        "validated_edge": validated,
        "pattern_recognition_route": dict(PATTERN_ROUTE),
        "quantum_edge_route": None,
        "authority": _authority(),
    }


def _hybrid_pattern(
    candidate: dict[str, Any],
    evaluation: dict[str, Any],
) -> dict[str, Any]:
    origin = _text(candidate.get("discovery_origin"), "joint_discovery")
    contribution = _text(
        evaluation.get("validation_contribution")
        or candidate.get("validation_contribution"),
        "not_tested",
    )
    evidence = _as_list(candidate.get("evidence_records"))
    hardware_receipt_verified = any(
        row.get("hardware_experiment_completed") is True
        and bool(row.get("hardware_receipt_hash"))
        for row in evidence
    )
    simulation_used = any(row.get("quantum_simulation_completed") is True for row in evidence)
    if hardware_receipt_verified:
        mode = "ibm_quantum_via_qctrl_fire_opal"
        mode_label = "IBM Quantum via Q-CTRL Fire Opal"
    elif simulation_used:
        mode = "local_quantum_simulation"
        mode_label = "Local quantum simulation"
    else:
        mode = "classical_discovery"
        mode_label = "Classical discovery"
    feature_pair = [
        str(value)
        for value in _as_list(candidate.get("source_chain", {}).get("feature_pair"))
        if value
    ]
    method_evidence = [
        {
            "discovery_origin": row.get("discovery_origin"),
            "method": row.get("method"),
            "execution_mode": row.get("execution_mode"),
            "structural_score": row.get("structural_score"),
            "quantum_simulation_completed": row.get("quantum_simulation_completed") is True,
            "hardware_experiment_completed": row.get("hardware_experiment_completed") is True,
            "hardware_receipt_hash": row.get("hardware_receipt_hash"),
        }
        for row in evidence
    ]
    return {
        "candidate_id": candidate.get("candidate_id"),
        "title": "Joint source-regime interaction for crude-oil repricing",
        "discovery_origin": origin,
        "discovery_origin_label": _origin_label(origin),
        "validation_contribution": contribution,
        "validation_contribution_label": _validation_label(contribution),
        "relationship": _text(
            candidate.get("relationship"),
            "A nonlinear source relationship was observed.",
        ),
        "source_chain": feature_pair,
        "source_chain_summary": (
            "Engine features: " + ", ".join(value.replace("_", " ") for value in feature_pair)
            if feature_pair
            else "No feature lineage was exported."
        ),
        "market": _text(candidate.get("market"), "Market not exported"),
        "instruments": [
            str(value) for value in _as_list(candidate.get("observed_instruments")) if value
        ],
        "interpretation": _text(
            candidate.get("interpretation"),
            "Qadam has not exported an interpretation.",
        ),
        "confirmation": _text(
            candidate.get("confirmation"),
            "Repeat on untouched evidence.",
        ),
        "falsifier": _text(
            candidate.get("falsifier"),
            "No improvement over the matched classical method.",
        ),
        "evidence_state": _text(candidate.get("evidence_state"), "unvalidated"),
        "lifecycle_stage": _text(
            candidate.get("lifecycle_state"),
            "candidate_relationship",
        ),
        "blocker": _first(
            evaluation.get("measurability_blockers"),
            _text(candidate.get("blocker"), "No blocker was exported."),
        ).replace("_", " "),
        "next_action": _text(
            candidate.get("next_action"),
            "Run independent holdout evaluation.",
        ),
        "execution_mode": mode,
        "execution_mode_label": mode_label,
        "quantum_involved": origin in {"quantum_assisted_discovery", "joint_discovery"},
        "hardware_receipt_verified": hardware_receipt_verified,
        "contract_fixture_only": candidate.get("contract_fixture_only") is True,
        "empirical_evidence_count": int(candidate.get("empirical_evidence_count") or 0),
        "method_evidence": method_evidence,
        "strategy_family_id": "crude_oil_energy_security_disruption",
        "validated_edge": (
            contribution
            in {"quantum_strengthened", "joint_corroboration", "classical_preferred"}
            and evaluation.get("empirical_claim_allowed") is True
        ),
        "pattern_recognition_route": dict(PATTERN_ROUTE),
        "quantum_edge_route": dict(QUANTUM_EDGE_ROUTE),
        "authority": _authority(),
    }


def _proof_state(evaluation_summary: dict[str, Any]) -> str:
    counts = evaluation_summary.get("verdict_counts", {})
    if int(counts.get("quantum_strengthened") or 0) > 0:
        return "validated_quantum_contribution"
    if int(counts.get("weakened") or 0) > 0 and int(
        evaluation_summary.get("empirical_measured_count") or 0
    ) > 0:
        return "quantum_contribution_decayed"
    if int(evaluation_summary.get("empirical_measured_count") or 0) > 0:
        return "provisional_quantum_evidence"
    return "quantum_edge_not_yet_proven"


def _strategy_record(
    row: dict[str, Any],
    patterns: list[dict[str, Any]],
    *,
    admitted: bool,
) -> dict[str, Any]:
    family_id = row.get("strategy_family_id")
    lineage = [pattern for pattern in patterns if pattern.get("strategy_family_id") == family_id]
    origins = sorted({str(pattern["discovery_origin"]) for pattern in lineage})
    contributions = sorted(
        {str(pattern["validation_contribution"]) for pattern in lineage}
    )
    core = [
        str(item.get("symbol"))
        for item in _as_list(row.get("core_instruments_explained"))
        if isinstance(item, dict) and item.get("symbol")
    ]
    return {
        "strategy_family_id": family_id,
        "label": _text(row.get("label"), "Unnamed strategy playbook"),
        "admission_state": "validated_strategy" if admitted else "research_playbook",
        "market": _text(
            row.get("catalyst_class"),
            family_id.replace("_", " ") if family_id else "Market not exported",
        ),
        "instruments": core,
        "thesis": _text(
            row.get("plain_english_summary"),
            "A bounded research playbook awaiting evidence.",
        ),
        "catalyst": _text(row.get("what_qadam_watches"), "Catalyst not exported."),
        "confirmation": _text(
            row.get("current_evidence_state"),
            "Confirmation evidence has not been exported.",
        ),
        "entry": "A current setup must pass the Decision Room and every downstream gate.",
        "invalidation": _text(
            row.get("current_blocker_plain_english"),
            "The evidence no longer supports the playbook.",
        ),
        "exits": "Exit logic is governed later by the approved strategy and risk record.",
        "risk_assumptions": "No sizing or execution authority exists on this page.",
        "akber_stage": _text(row.get("current_state"), "not reached").replace("_", " "),
        "present_blocker": _text(
            row.get("current_blocker_plain_english"),
            "No validated edge exists yet.",
        ),
        "next_action": _text(
            row.get("next_action_plain_english"),
            "Complete historical validation.",
        ),
        "validated_edge_count": int(row.get("validated_edge_count") or 0),
        "underlying_pattern_ids": [pattern["candidate_id"] for pattern in lineage],
        "discovery_origins": origins,
        "validation_contributions": contributions,
        "pattern_recognition_route": dict(PATTERN_ROUTE),
        "quantum_edge_route": (
            dict(QUANTUM_EDGE_ROUTE)
            if any(pattern.get("quantum_involved") for pattern in lineage)
            else None
        ),
        "authority": _authority(),
    }


def build_wave_f_public_view_from_artifacts(
    artifacts: dict[str, Any],
    *,
    generated_at: str,
) -> dict[str, Any]:
    legacy_projection = artifacts.get("pattern_discovery", {})
    hybrid_candidates = artifacts.get("hybrid_candidates", [])
    evaluations = artifacts.get("evaluations", [])
    evaluation_summary = artifacts.get("evaluation_summary", {})
    local_quantum = artifacts.get("local_quantum", {})
    readiness = artifacts.get("provider_readiness", {})
    hardware = artifacts.get("hardware_public", {})
    strategy_universe = artifacts.get("strategy_universe", {})

    evaluation_by_candidate = {
        row.get("candidate_id"): row
        for row in evaluations
        if isinstance(row, dict) and row.get("candidate_id")
    }
    patterns = [
        _legacy_pattern(row)
        for row in _as_list(legacy_projection.get("relationships"))
        if isinstance(row, dict)
    ]
    patterns.extend(
        _hybrid_pattern(candidate, evaluation_by_candidate.get(candidate.get("candidate_id"), {}))
        for candidate in hybrid_candidates
        if isinstance(candidate, dict)
    )
    patterns.sort(
        key=lambda row: (
            {"joint_discovery": 0, "quantum_assisted_discovery": 1}.get(
                row["discovery_origin"],
                2,
            ),
            row["title"],
        )
    )
    origin_counts = {
        origin: sum(row["discovery_origin"] == origin for row in patterns)
        for origin in DISCOVERY_ORIGINS
    }

    proof_state = _proof_state(evaluation_summary)
    provider_configured = (
        readiness.get("credentials_configured") is True
        and readiness.get("product_entitled") is True
    )
    provider_accessible = (
        provider_configured
        and readiness.get("qctrl_authenticated") is True
        and readiness.get("ibm_configured_instance_accessible") is True
        and readiness.get("backend_discovered") is True
        and readiness.get("circuit_validation_available") is True
        and int(readiness.get("supported_device_count") or 0) > 0
        and readiness.get("blocker") in {None, "", "none"}
    )
    provider_status_summary = (
        "Provider access is healthy and eligible IBM backends were discovered. "
        "No hardware experiment has been authorized or submitted."
        if provider_accessible
        else _text(
            readiness.get("blocker"),
            "Provider access is not yet proven.",
        ).replace("_", " ")
    )
    hardware_completed = hardware.get("hardware_experiment_completed") is True
    receipt_verified = hardware_completed and bool(hardware.get("receipt_hash"))
    local_ready = local_quantum.get("status") == "local_quantum_discovery_ready"
    ideal = local_quantum.get("ideal_result", {})
    finite = local_quantum.get("finite_shot_result", {})
    manifest = hardware.get("manifest", {})
    evaluation = evaluations[0] if evaluations else {}
    proof_ladder = [
        {
            "key": "provider_configured",
            "label": "Provider configured",
            "state": (
                "complete"
                if provider_accessible
                else "partial"
                if provider_configured
                else "blocked"
            ),
            "explanation": (
                "Q-CTRL authenticated, the configured IBM instance is accessible, and supported devices were discovered. Access is ready; no hardware experiment was authorized or run."
                if provider_accessible
                else "Q-CTRL product access and credentials are present, but the IBM token cannot access the configured instance."
                if readiness.get("blocker") == "ibm_token_instance_access_mismatch"
                else "Provider configuration is visible, but complete backend access is not proven."
            ),
        },
        {
            "key": "ibm_hardware_executed",
            "label": "IBM hardware executed",
            "state": "complete" if receipt_verified else "not_reached",
            "explanation": (
                "A sanitized receipt proves that the prepared experiment completed on IBM hardware."
                if receipt_verified
                else "No IBM hardware job has been submitted or completed."
            ),
        },
        {
            "key": "result_reproduced",
            "label": "Result reproduced",
            "state": "partial" if local_ready else "not_reached",
            "explanation": (
                "Ideal and finite-shot local simulations reproduce the engineering control; hardware reproduction has not occurred."
                if local_ready
                else "No reproducible result is available."
            ),
        },
        {
            "key": "classical_baseline_beaten",
            "label": "Classical baseline beaten",
            "state": "complete"
            if evaluation.get("validation_contribution") == "quantum_strengthened"
            else "not_reached",
            "explanation": (
                "The quantum-assisted method added cost-adjusted value over the matched classical baseline."
                if evaluation.get("validation_contribution") == "quantum_strengthened"
                else "No empirical comparison has beaten the matched classical baseline."
            ),
        },
        {
            "key": "untouched_advantage_survived",
            "label": "Untouched-data advantage survived",
            "state": "complete"
            if evaluation.get("empirical_claim_allowed") is True
            else "not_reached",
            "explanation": (
                "The frozen result survived untouched chronological evidence and operational penalties."
                if evaluation.get("empirical_claim_allowed") is True
                else "Provider-backed untouched holdout evidence does not exist yet."
            ),
        },
        {
            "key": "paper_decision_improved",
            "label": "Paper decision improved",
            "state": "not_reached",
            "explanation": "No paper decision can be attributed to a validated quantum contribution.",
        },
    ]
    experiments = [
        {
            "experiment_id": "matched-classical-contract-control",
            "title": "Matched classical discovery control",
            "kind": "classical",
            "state": "complete" if artifacts.get("classical_discovery") else "missing",
            "result": "Eight label-blind classical methods recovered the fixture interaction.",
            "boundary": "Contract fixture only; no historical edge claim.",
        },
        {
            "experiment_id": "local-ideal-quantum-kernel",
            "title": "Local ideal quantum-kernel control",
            "kind": "quantum_simulator",
            "state": "complete" if ideal.get("quantum_simulation_completed") is True else "missing",
            "result": (
                f"{int(ideal.get('qubit_count') or 0)} qubits and "
                f"{int(ideal.get('circuit_evaluation_count') or 0)} bounded circuit evaluations recovered the same feature pair."
            ),
            "boundary": "Local statevector simulation, not IBM hardware.",
        },
        {
            "experiment_id": "local-finite-shot-quantum-kernel",
            "title": "Local finite-shot control",
            "kind": "quantum_simulator",
            "state": "complete" if finite.get("quantum_simulation_completed") is True else "missing",
            "result": f"The finite-shot run used {int(finite.get('shots') or 0)} shots per circuit.",
            "boundary": "Local Aer simulation, not IBM hardware.",
        },
        {
            "experiment_id": hardware.get("manifest_hash") or "fire-opal-manifest-pending",
            "title": "Fire Opal / IBM hardware experiment",
            "kind": "hardware",
            "state": "complete" if receipt_verified else _text(
                hardware.get("lifecycle_status"),
                "not_prepared",
            ),
            "result": (
                "A verified hardware receipt exists."
                if receipt_verified
                else (
                    f"Prepared {int(manifest.get('circuit_count') or 0)} circuits, "
                    f"{int(manifest.get('shots_per_circuit') or 0)} shots each; provider calls remain 0."
                )
            ),
            "boundary": (
                "IBM Quantum via Q-CTRL Fire Opal."
                if receipt_verified
                else "Prepared only; no provider validation, submission, or hardware result."
            ),
        },
        {
            "experiment_id": evaluation.get("evaluation_id") or "holdout-evaluation-pending",
            "title": "Independent untouched-holdout comparison",
            "kind": "evaluation",
            "state": evaluation.get("validation_contribution") or "not_measurable",
            "result": _validation_label(
                evaluation.get("validation_contribution") or "not_measurable"
            ),
            "boundary": "The discovery methods cannot judge themselves.",
        },
    ]

    strategy_rows = [
        row
        for row in _as_list(strategy_universe.get("all_strategy_rows"))
        if isinstance(row, dict)
    ]
    eligible_pattern_ids = {
        pattern["candidate_id"]
        for pattern in patterns
        if pattern["validated_edge"] is True
    }
    admitted: list[dict[str, Any]] = []
    research: list[dict[str, Any]] = []
    for row in strategy_rows:
        candidate = _strategy_record(row, patterns, admitted=False)
        lineage_validated = bool(
            eligible_pattern_ids.intersection(candidate["underlying_pattern_ids"])
        )
        is_admitted = int(row.get("validated_edge_count") or 0) > 0 and lineage_validated
        candidate = _strategy_record(row, patterns, admitted=is_admitted)
        (admitted if is_admitted else research).append(candidate)

    quantum_influenced_strategies = [
        strategy
        for strategy in admitted
        if any(
            origin in {"quantum_assisted_discovery", "joint_discovery"}
            for origin in strategy["discovery_origins"]
        )
        and any(
            contribution in {"quantum_strengthened", "joint_corroboration"}
            for contribution in strategy["validation_contributions"]
        )
    ]
    comparison_summary = {
        "candidate_id": evaluation.get("candidate_id"),
        "verdict": evaluation.get("validation_contribution") or "not_measurable",
        "verdict_label": _validation_label(
            evaluation.get("validation_contribution") or "not_measurable"
        ),
        "empirical_claim_allowed": evaluation.get("empirical_claim_allowed") is True,
        "evidence_class": _text(evaluation.get("evidence_class"), "no_holdout"),
        "classical_baseline": _text(
            evaluation.get("matched_classical_baseline_id"),
            "Matched classical baseline pending",
        ),
        "quantum_method": _text(
            evaluation.get("quantum_method_id"),
            "Provider-backed quantum method pending",
        ),
        "blocker": _first(
            evaluation.get("measurability_blockers"),
            "No untouched comparison has been completed.",
        ).replace("_", " "),
        "plain_english_summary": (
            "There is no fair market-data comparison yet. Qadam must test the quantum "
            "method and its strongest matched classical method on the same untouched "
            "chronological evidence before either can win."
            if evaluation.get("empirical_claim_allowed") is not True
            else "The independent evaluator completed a like-for-like comparison on untouched evidence."
        ),
    }

    payload = {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "qadam_quantum_edge_wave_f_public_view",
        "generated_at": generated_at,
        "routes": {
            "pattern_recognition": dict(PATTERN_ROUTE),
            "quantum_edge": dict(QUANTUM_EDGE_ROUTE),
            "trading_strategies": dict(STRATEGY_ROUTE),
        },
        "navigation_labels": {
            "pattern_recognition": "Pattern Recognition",
            "quantum_edge": "Quantum Edge",
            "trading_strategies": "Trading Strategies",
        },
        "pattern_recognition": {
            "status": "research_only",
            "headline": "What Qadam has recognised, and how it was found",
            "plain_english_summary": (
                f"Qadam is tracking {len(patterns)} research relationships: "
                f"{origin_counts['classical_discovery']} classical, "
                f"{origin_counts['quantum_assisted_discovery']} quantum-assisted, and "
                f"{origin_counts['joint_discovery']} found by both lanes. None is currently an approved trade."
            ),
            "candidate_count": len(patterns),
            "filters": [
                {"key": "all", "label": "All", "count": len(patterns)},
                {
                    "key": "classical_discovery",
                    "label": "Classical",
                    "count": origin_counts["classical_discovery"],
                },
                {
                    "key": "quantum_assisted_discovery",
                    "label": "Quantum",
                    "count": origin_counts["quantum_assisted_discovery"],
                },
                {
                    "key": "joint_discovery",
                    "label": "Joint",
                    "count": origin_counts["joint_discovery"],
                },
            ],
            "candidates": patterns,
            "boundary": (
                "Recognition records are research evidence. They cannot create a strategy, "
                "risk approval, order, broker write, proof credit, or live-capital authority."
            ),
            "authority": _authority(),
        },
        "quantum_edge": {
            "status": proof_state,
            "proof_state": proof_state,
            "headline": "Quantum edge has not yet been proven",
            "plain_english_summary": (
                "The local quantum lane reproduced a known synthetic interaction and merged it "
                "with the classical finding. That proves the engineering loop works. It does not "
                "prove market advantage: IBM hardware has not run and no untouched historical "
                "holdout exists."
            ),
            "proof_ladder": proof_ladder,
            "completed_proof_step_count": sum(
                step["state"] == "complete" for step in proof_ladder
            ),
            "strongest_evidence": {
                "title": "Classical and local quantum methods recovered the same fixture interaction",
                "summary": (
                    "Both lanes identified the source-density and source-agreement interaction "
                    "from the same frozen, label-blind manifest. This is a synthetic engineering "
                    "control, not an empirical trading edge."
                ),
                "candidate_id": next(
                    (
                        pattern["candidate_id"]
                        for pattern in patterns
                        if pattern["discovery_origin"] == "joint_discovery"
                    ),
                    None,
                ),
                "verdict": evaluation.get("validation_contribution") or "not_measurable",
            },
            "experiments": experiments,
            "comparisons": evaluations,
            "comparison_summary": comparison_summary,
            "hardware_authenticity": {
                "qctrl_product_entitled": readiness.get("product_entitled") is True,
                "ibm_instance_accessible": provider_accessible,
                "provider_blocker": readiness.get("blocker"),
                "provider_status_summary": provider_status_summary,
                "prepared_manifest_hash": hardware.get("manifest_hash"),
                "provider_call_count": int(hardware.get("provider_call_count") or 0),
                "hardware_execution_authorized": hardware.get(
                    "hardware_execution_authorized"
                )
                is True,
                "hardware_job_submitted": hardware.get("hardware_job_submitted") is True,
                "hardware_experiment_completed": hardware_completed,
                "hardware_receipt_verified": receipt_verified,
            },
            "negative_results": [
                {
                    "title": "Independent value is not measurable",
                    "explanation": "Provider-backed untouched holdout evidence is missing.",
                },
                {
                    "title": (
                        "IBM hardware has not been run"
                        if provider_accessible
                        else "IBM hardware access is blocked"
                    ),
                    "explanation": provider_status_summary,
                },
                {
                    "title": "The current joint finding is a fixture",
                    "explanation": (
                        "Synthetic controls test the machinery but cannot become empirical proof "
                        "or an approved strategy."
                    ),
                },
            ],
            "strategy_influence": {
                "validated_strategy_count": len(quantum_influenced_strategies),
                "strategy_family_ids": [
                    strategy["strategy_family_id"]
                    for strategy in quantum_influenced_strategies
                ],
                "summary": (
                    f"{len(quantum_influenced_strategies)} validated strategies currently "
                    "carry an independently validated quantum contribution."
                    if quantum_influenced_strategies
                    else "No trading strategy has changed because no quantum contribution is validated."
                ),
            },
            "paper_outcome_lineage": {
                "attributed_paper_decision_count": 0,
                "summary": (
                    "No paper decision or paper outcome is attributed to quantum evidence. "
                    "This remains empty until a validated contribution changes a governed "
                    "paper decision and that outcome is recorded."
                ),
            },
            "provenance": {
                "shared_manifest_hash": manifest.get("shared_manifest_hash"),
                "hardware_manifest_hash": hardware.get("manifest_hash"),
                "evaluation_policy_hash": evaluation_summary.get("evaluator_policy_hash"),
                "candidate_ids": [
                    pattern["candidate_id"]
                    for pattern in patterns
                    if pattern["quantum_involved"]
                ],
            },
            "boundary": (
                "A protocol, simulator result, prepared job, submitted job, or hardware receipt "
                "alone is not a quantum edge."
            ),
            "authority": _authority(),
        },
        "trading_strategies": {
            "status": "awaiting_validated_edges" if not admitted else "validated_playbooks_visible",
            "headline": "Validated trading playbooks",
            "plain_english_summary": (
                f"{len(admitted)} strategies are admitted from validated patterns. "
                f"{len(research)} defined research playbooks remain outside the approved strategy set."
            ),
            "validated_strategy_count": len(admitted),
            "research_playbook_count": len(research),
            "admitted_strategies": admitted,
            "research_playbooks": research,
            "boundary": (
                "A playbook can enter this page as an approved strategy only after its underlying "
                "pattern is independently validated. Hardware activity and provisional patterns do not qualify."
            ),
            "authority": _authority(),
        },
        "authority": _authority(),
    }
    payload["content_hash"] = stable_hash(
        {key: value for key, value in payload.items() if key != "generated_at"}
    )
    validate_wave_f_public_view(payload)
    return payload


def _latest_hardware_public(runtime_dir: Path) -> dict[str, Any]:
    candidates = sorted(
        (runtime_dir / "qadam_fire_opal_ibm_discovery").glob("*.public.json"),
        key=lambda path: path.stat().st_mtime,
        reverse=True,
    )
    return _read_json(candidates[0]) if candidates else {}


def _pattern_discovery_projection(runtime_dir: Path) -> dict[str, Any]:
    """Load the legacy projection or rebuild it from tracked QSASE findings.

    The original Wave F export consumed a local-only
    ``qadam_pattern_discovery_dashboard.json`` artifact. A clean checkout does
    not contain that file, while ``qsase_pattern_intelligence.json`` is the
    tracked public-safe source for the same five classical observations.
    """

    projection = _read_json(runtime_dir / "qadam_pattern_discovery_dashboard.json")
    if _as_list(projection.get("relationships")):
        return projection
    intelligence = _read_json(runtime_dir / "qsase_pattern_intelligence.json")
    findings = [
        row
        for row in _as_list(intelligence.get("findings"))
        if isinstance(row, dict)
    ]
    return {"relationships": findings}


def build_wave_f_public_view(
    runtime_dir: str | Path,
    *,
    generated_at: str | None = None,
) -> dict[str, Any]:
    root = Path(runtime_dir)
    artifacts = {
        "pattern_discovery": _pattern_discovery_projection(root),
        "hybrid_candidates": _read_jsonl(root / "qadam_hybrid_candidates.jsonl"),
        "evaluations": _read_jsonl(
            root / "qadam_independent_quantum_value_evaluations.jsonl"
        ),
        "evaluation_summary": _read_json(
            root / "qadam_independent_quantum_value_summary.json"
        ),
        "classical_discovery": _read_json(root / "qadam_classical_discovery_contract.json"),
        "local_quantum": _read_json(root / "qadam_local_quantum_discovery_contract.json"),
        "provider_readiness": _read_json(root / "qctrl_fire_opal_ibm_readiness.json"),
        "hardware_public": _latest_hardware_public(root),
        "strategy_universe": _read_json(root / "qsase_dashboard_strategy_universe.json"),
    }
    return build_wave_f_public_view_from_artifacts(
        artifacts,
        generated_at=generated_at or datetime.now(timezone.utc).isoformat(),
    )


def validate_wave_f_public_view(payload: dict[str, Any]) -> None:
    if payload.get("schema_version") != SCHEMA_VERSION:
        raise ValueError("wave_f_public_view_schema_invalid")
    if payload.get("routes") != {
        "pattern_recognition": PATTERN_ROUTE,
        "quantum_edge": QUANTUM_EDGE_ROUTE,
        "trading_strategies": STRATEGY_ROUTE,
    }:
        raise ValueError("wave_f_route_contract_changed")
    patterns = payload.get("pattern_recognition", {}).get("candidates")
    if not isinstance(patterns, list):
        raise ValueError("wave_f_pattern_candidates_invalid")
    for pattern in patterns:
        if pattern.get("discovery_origin") not in DISCOVERY_ORIGINS:
            raise ValueError("wave_f_pattern_origin_invalid")
        if pattern.get("validation_contribution") not in VALIDATION_CONTRIBUTIONS:
            raise ValueError("wave_f_pattern_validation_invalid")
        for field_name in (
            "candidate_id",
            "title",
            "relationship",
            "market",
            "interpretation",
            "confirmation",
            "falsifier",
            "evidence_state",
            "lifecycle_stage",
            "blocker",
            "next_action",
        ):
            if not str(pattern.get(field_name) or "").strip():
                raise ValueError(f"wave_f_pattern_field_missing:{field_name}")
        if (
            pattern.get("execution_mode_label") == "IBM Quantum via Q-CTRL Fire Opal"
            and pattern.get("hardware_receipt_verified") is not True
        ):
            raise ValueError("wave_f_unearned_hardware_label")
        if any(value is not False for value in pattern.get("authority", {}).values()):
            raise ValueError("wave_f_pattern_authority_escalated")
    quantum_edge = payload.get("quantum_edge", {})
    if quantum_edge.get("proof_state") not in PROOF_STATES:
        raise ValueError("wave_f_proof_state_invalid")
    authenticity = quantum_edge.get("hardware_authenticity", {})
    if authenticity.get("hardware_experiment_completed") is True and authenticity.get(
        "hardware_receipt_verified"
    ) is not True:
        raise ValueError("wave_f_hardware_completion_without_receipt")
    if quantum_edge.get("proof_state") == "validated_quantum_contribution" and not any(
        comparison.get("validation_contribution") == "quantum_strengthened"
        and comparison.get("empirical_claim_allowed") is True
        for comparison in quantum_edge.get("comparisons", [])
    ):
        raise ValueError("wave_f_unearned_quantum_edge_claim")
    strategies = payload.get("trading_strategies", {})
    for strategy in strategies.get("admitted_strategies", []):
        if strategy.get("admission_state") != "validated_strategy":
            raise ValueError("wave_f_strategy_admission_state_invalid")
        if int(strategy.get("validated_edge_count") or 0) <= 0:
            raise ValueError("wave_f_strategy_without_validated_edge")
        if not strategy.get("underlying_pattern_ids"):
            raise ValueError("wave_f_strategy_lineage_missing")
    if strategies.get("validated_strategy_count") != len(
        strategies.get("admitted_strategies", [])
    ):
        raise ValueError("wave_f_strategy_count_mismatch")
    for section_key in (
        "pattern_recognition",
        "quantum_edge",
        "trading_strategies",
    ):
        if any(
            value is not False
            for value in payload.get(section_key, {}).get("authority", {}).values()
        ):
            raise ValueError(f"wave_f_section_authority_escalated:{section_key}")
    if any(value is not False for value in payload.get("authority", {}).values()):
        raise ValueError("wave_f_authority_escalated")
    expected_hash = stable_hash(
        {
            key: value
            for key, value in payload.items()
            if key not in {"generated_at", "content_hash"}
        }
    )
    if payload.get("content_hash") != expected_hash:
        raise ValueError("wave_f_content_hash_mismatch")
    if _contains_forbidden_key(payload):
        raise ValueError("wave_f_forbidden_public_key")


def _atomic_write(path: Path, payload: dict[str, Any]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    temporary.replace(path)
    return path


def write_wave_f_public_view(
    payload: dict[str, Any],
    *,
    runtime_dir: str | Path,
    site_root: str | Path | None = None,
) -> dict[str, Path]:
    validate_wave_f_public_view(payload)
    outputs = {
        "runtime": _atomic_write(Path(runtime_dir) / ARTIFACT_NAME, payload),
    }
    if site_root is not None:
        outputs["site"] = _atomic_write(
            Path(site_root) / "status" / SITE_ARTIFACT_NAME,
            payload,
        )
    return outputs
