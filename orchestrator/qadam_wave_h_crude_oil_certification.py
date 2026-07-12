"""Wave H crude-oil pilot and honest Quantum Edge certification.

Wave H certifies that Qadam has a reproducible mechanism for testing quantum
value. It does not turn contract fixtures, local simulation, a prepared
hardware manifest, or missing historical evidence into a market-edge claim.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
from typing import Any

from orchestrator.config import Settings
from orchestrator.qadam_classical_discovery import run_classical_discovery
from orchestrator.qadam_discovery_contract_fixture import (
    build_wave_c_contract_fixture_batch,
)
from orchestrator.qadam_fire_opal_ibm_discovery import (
    prepare_fire_opal_ibm_smoke_manifest,
)
from orchestrator.qadam_local_quantum_discovery import (
    QiskitLocalQuantumDiscoveryBackend,
)
from orchestrator.qadam_quantum_discovery_evidence import (
    build_point_in_time_foundation,
)
from orchestrator.qadam_quantum_discovery_manifest import (
    build_shared_manifest_contract,
)


SCHEMA_VERSION = "qadam.QuantumEdgeWaveHCrudeOilCertification.v1"
PILOT_MANIFEST_SCHEMA_VERSION = "qadam.QuantumEdgeCrudeOilPilotManifest.v1"
ARTIFACT_NAME = "qadam_quantum_edge_wave_h_crude_oil_certification.json"
SITE_ARTIFACT_NAME = "quantum-edge-wave-h.json"

PUBLIC_PROOF_STATES = (
    "unproven",
    "provisional",
    "validated",
    "classically_dominated",
    "decayed",
)

ZERO_AUTHORITY_FIELDS = (
    "broker_write_allowed",
    "candidate_promotion_allowed",
    "dashboard_command_authority",
    "direct_broker_call_allowed",
    "execution_allowed",
    "execution_approval_allowed",
    "hardware_scheduler_enabled",
    "hardware_submission_allowed",
    "live_capital_enabled",
    "paper_order_allowed",
    "paper_proof_ledger_credit_allowed",
    "position_sizing_allowed",
    "proof_credit_allowed",
    "risk_approval_allowed",
    "strategy_hypothesis_creation_allowed",
    "strategy_mutation_allowed",
    "telegram_command_authority",
    "trade_candidate_creation_allowed",
    "validated_edge_creation_allowed",
)

FORBIDDEN_PUBLIC_KEYS = {
    "action_id",
    "api_key",
    "authorization",
    "credentials",
    "password",
    "qasm_circuits",
    "raw_provider_response",
    "secret",
    "token",
}

SECRET_PATTERNS = (
    re.compile(r"\bsk-[A-Za-z0-9_-]{20,}\b"),
    re.compile(r"\bghp_[A-Za-z0-9_]{20,}\b"),
    re.compile(r"\b\d{6,}:[A-Za-z0-9_-]{20,}\b"),
)


@dataclass(frozen=True)
class CrudeOilPilotPolicy:
    random_seed: int = 1729
    transaction_cost_bps: float = 10.0
    minimum_holdout_observations: int = 32
    permutation_iterations: int = 4096
    false_discovery_rate_alpha: float = 0.05
    maximum_qubits: int = 8
    maximum_circuits: int = 128
    maximum_total_shots: int = 32768
    maximum_provider_budget_usd: float = 10.0


def _authority() -> dict[str, bool]:
    return {field: False for field in ZERO_AUTHORITY_FIELDS}


def _safe_dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _safe_list(value: Any) -> list[Any]:
    if isinstance(value, list):
        return value
    if isinstance(value, tuple):
        return list(value)
    return []


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


def _write_json_atomic(path: Path, payload: dict[str, Any]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    temporary.replace(path)
    return path


def _public_key_errors(value: Any, *, path: str = "root") -> list[str]:
    errors: list[str] = []
    if isinstance(value, dict):
        for key, item in value.items():
            key_text = str(key).lower()
            if key_text in FORBIDDEN_PUBLIC_KEYS:
                errors.append(f"forbidden_public_key:{path}.{key}")
            errors.extend(_public_key_errors(item, path=f"{path}.{key}"))
    elif isinstance(value, list):
        for index, item in enumerate(value):
            errors.extend(_public_key_errors(item, path=f"{path}[{index}]"))
    elif isinstance(value, str):
        if value.startswith("/Users/"):
            errors.append(f"local_path_exposed:{path}")
        for pattern in SECRET_PATTERNS:
            if pattern.search(value):
                errors.append(f"secret_like_value:{path}")
    return errors


def build_crude_oil_pilot_manifest(
    *,
    engineering_hardware_manifest_hash: str,
    policy: CrudeOilPilotPolicy | None = None,
) -> dict[str, Any]:
    """Freeze the empirical pilot design without claiming that data exists."""

    selected = policy or CrudeOilPilotPolicy()
    payload: dict[str, Any] = {
        "schema_version": PILOT_MANIFEST_SCHEMA_VERSION,
        "pilot_id": "quantum-edge-pilot:crude-oil-v1",
        "market_sleeve": "crude_oil",
        "paper_targets": ["BNO", "USO"],
        "market_context": ["CL=F", "BZ=F", "XLE"],
        "research_question": (
            "Do interacting physical-disruption and market-response signals improve "
            "untouched crude-oil return forecasts beyond the strongest matched classical method?"
        ),
        "point_in_time_features": [
            {
                "key": "conflict_event_acceleration",
                "meaning": "Change in conflict and sanctions activity known by the cutoff.",
            },
            {
                "key": "tanker_chokepoint_disruption",
                "meaning": "Vessel delays, route avoidance, and chokepoint interruption known by the cutoff.",
            },
            {
                "key": "port_congestion",
                "meaning": "Port waiting time and vessel-density changes known by the cutoff.",
            },
            {
                "key": "inventory_surprise",
                "meaning": "Released crude-inventory change versus the pre-release expectation.",
            },
            {
                "key": "weather_fire_disruption",
                "meaning": "Weather and fire events affecting production, refining, or transport.",
            },
            {
                "key": "futures_curve_structure",
                "meaning": "Contango, backwardation, and nearby spread state at the cutoff.",
            },
            {
                "key": "realized_volatility",
                "meaning": "Trailing volatility computed only from prices available by the cutoff.",
            },
            {
                "key": "muted_or_divergent_price_response",
                "meaning": "A weak or contradictory market response despite stronger real-world evidence.",
            },
        ],
        "outcomes": [
            "BNO one-day net directional return",
            "BNO five-day net return",
            "USO one-day net directional return",
            "USO five-day net return",
        ],
        "chronology": {
            "training": "expanding chronological training only",
            "validation": "later chronological model selection with embargo",
            "untouched_holdout": "final period unavailable to discovery and tuning",
            "labels_visible_during_discovery": False,
        },
        "matched_methods": {
            "classical": [
                "regularized linear baseline",
                "RBF kernel baseline",
                "random forest",
                "gradient boosting",
                "depth-two interaction tree",
            ],
            "quantum": [
                "ideal local fidelity-kernel simulation",
                "finite-shot local fidelity-kernel simulation",
                "separately authorized Fire Opal experiment on IBM hardware",
            ],
        },
        "controls": [
            "placebo target",
            "time-shift control",
            "feature and label permutation",
            "multiple-testing correction",
        ],
        "policy": asdict(selected),
        "engineering_smoke_manifest_hash": engineering_hardware_manifest_hash,
        "empirical_hardware_manifest_prepared": False,
        "hardware_submission_authorized": False,
        "authority": _authority(),
    }
    payload["manifest_hash"] = _stable_hash(payload)
    return payload


def classify_public_proof_state(
    *,
    scientific_verdict: str,
    empirical_measured: bool,
    hardware_completed: bool,
    controls_passed: bool,
    edge_decay_detected: bool = False,
) -> str:
    if edge_decay_detected:
        return "decayed"
    if scientific_verdict == "classical_preferred" and empirical_measured:
        return "classically_dominated"
    if (
        scientific_verdict in {"quantum_strengthened", "joint_corroboration"}
        and empirical_measured
        and hardware_completed
        and controls_passed
    ):
        return "validated"
    if (
        scientific_verdict in {"quantum_strengthened", "joint_corroboration"}
        and empirical_measured
    ):
        return "provisional"
    return "unproven"


def _control_register(*, empirical_ready: bool) -> list[dict[str, Any]]:
    controls = (
        (
            "placebo target",
            "Tests whether the method also appears to predict an unrelated outcome.",
        ),
        (
            "time-shift control",
            "Moves evidence earlier and later to detect accidental timing or lookahead.",
        ),
        (
            "feature and label permutation",
            "Breaks the real pairing to estimate how often an apparent edge occurs by chance.",
        ),
        (
            "multiple-testing correction",
            "Penalizes the search for trying many relationships before selecting a winner.",
        ),
    )
    return [
        {
            "control": name,
            "status": "ready_to_run" if empirical_ready else "not_run_no_eligible_holdout",
            "passed": False,
            "explanation": explanation,
        }
        for name, explanation in controls
    ]


def _check(
    key: str,
    category: str,
    passed: bool,
    status: str,
    explanation: str,
) -> dict[str, Any]:
    return {
        "key": key,
        "category": category,
        "passed": passed,
        "status": status,
        "explanation": explanation,
    }


def build_wave_h_certification(
    *,
    evidence: dict[str, Any],
    manifest_contract: dict[str, Any],
    classical_result: dict[str, Any],
    classical_reproduced: bool,
    ideal_result: dict[str, Any],
    ideal_reproduced: bool,
    finite_result: dict[str, Any],
    hardware_public_state: dict[str, Any],
    provider_readiness: dict[str, Any],
    evaluation_summary: dict[str, Any],
    wave_g: dict[str, Any],
    generated_at: str,
) -> dict[str, Any]:
    evidence_truth = _safe_dict(evidence.get("provider_history_truth"))
    alignment_truth = _safe_dict(evidence.get("alignment_truth"))
    leakage_truth = _safe_dict(evidence.get("leakage_truth"))
    hardware_manifest = _safe_dict(hardware_public_state.get("manifest"))
    pilot_manifest = build_crude_oil_pilot_manifest(
        engineering_hardware_manifest_hash=_text(
            hardware_public_state.get("manifest_hash"),
            "not-prepared",
        )
    )

    empirical_ready = evidence.get("empirical_evidence_ready") is True
    eligible_windows = _safe_int(
        alignment_truth.get("eligible_point_in_time_window_count")
    )
    provider_rows = _safe_int(evidence_truth.get("provider_row_count"))
    provider_complete = evidence_truth.get("provider_history_certified_complete") is True
    leakage_clear = _safe_int(leakage_truth.get("leakage_violation_count")) == 0
    manifest_equal = (
        _text(classical_result.get("shared_manifest_hash"))
        == _text(ideal_result.get("shared_manifest_hash"))
        == _text(finite_result.get("shared_manifest_hash"))
    )
    fixture_only = all(
        result.get("contract_fixture_only") is True
        for result in (classical_result, ideal_result, finite_result)
    )
    hardware_prepared = hardware_public_state.get("lifecycle_status") == "prepared"
    hardware_completed = hardware_public_state.get("hardware_experiment_completed") is True
    hardware_submitted = hardware_public_state.get("hardware_job_submitted") is True
    provider_calls = _safe_int(hardware_public_state.get("provider_call_count"))
    scientific_verdict = "not_measurable"
    verdict_counts = _safe_dict(evaluation_summary.get("verdict_counts"))
    for verdict in (
        "quantum_strengthened",
        "joint_corroboration",
        "classical_preferred",
        "weakened",
        "inconclusive",
        "failed_safely",
        "not_measurable",
    ):
        if _safe_int(verdict_counts.get(verdict)) > 0:
            scientific_verdict = verdict
            break
    empirical_measured = _safe_int(
        evaluation_summary.get("empirical_measured_count")
    ) > 0
    controls = _control_register(empirical_ready=empirical_ready)
    controls_passed = all(row["passed"] is True for row in controls)
    public_state = classify_public_proof_state(
        scientific_verdict=scientific_verdict,
        empirical_measured=empirical_measured,
        hardware_completed=hardware_completed,
        controls_passed=controls_passed,
    )

    wave_g_integration = _safe_dict(wave_g.get("paper_integration"))
    engineering_checks = [
        _check(
            "pilot_manifest_frozen",
            "reproducibility",
            bool(pilot_manifest.get("manifest_hash")),
            "passed",
            "The crude-oil feature, target, split, method, and control contract is content-addressed.",
        ),
        _check(
            "point_in_time_contract",
            "lineage",
            evidence.get("implementation_contract_ready") is True,
            "passed" if evidence.get("implementation_contract_ready") is True else "blocked",
            "The evidence contract separates discovery inputs from later outcomes.",
        ),
        _check(
            "zero_lookahead_leakage",
            "lineage",
            leakage_clear,
            "passed" if leakage_clear else "failed",
            f"Observed leakage violations: {_safe_int(leakage_truth.get('leakage_violation_count'))}.",
        ),
        _check(
            "matched_lane_manifest",
            "reproducibility",
            manifest_equal,
            "passed" if manifest_equal else "failed",
            "Classical, ideal-quantum, and finite-shot controls used the same frozen engineering fixture.",
        ),
        _check(
            "classical_control_reproduced",
            "reproducibility",
            classical_reproduced,
            "passed" if classical_reproduced else "failed",
            "The eight-method classical engineering control rebuilt deterministically.",
        ),
        _check(
            "ideal_quantum_control_reproduced",
            "reproducibility",
            ideal_reproduced,
            "passed" if ideal_reproduced else "failed",
            "The ideal local fidelity-kernel control rebuilt deterministically.",
        ),
        _check(
            "finite_shot_control_completed",
            "reproducibility",
            _safe_int(finite_result.get("shots")) > 0,
            "passed" if _safe_int(finite_result.get("shots")) > 0 else "failed",
            "The bounded finite-shot local control completed without hardware authority.",
        ),
        _check(
            "hardware_smoke_manifest_prepared",
            "provider_lineage",
            hardware_prepared and hardware_manifest.get("local_qasm_validation_passed") is True,
            "passed" if hardware_prepared else "blocked",
            "The engineering smoke manifest passed local QASM and budget validation; it was not submitted.",
        ),
        _check(
            "secret_safety",
            "security",
            hardware_public_state.get("secret_value_exposed") is False,
            "passed" if hardware_public_state.get("secret_value_exposed") is False else "failed",
            "The public hardware record contains no secret value, circuit payload, or raw provider response.",
        ),
        _check(
            "authority_isolation",
            "authority",
            not hardware_submitted
            and provider_calls == 0
            and _safe_int(wave_g_integration.get("broker_write_count")) == 0
            and _safe_int(wave_g_integration.get("paper_order_created_count")) == 0,
            "passed",
            "Wave H made no provider call, hardware submission, order, risk approval, or broker write.",
        ),
        _check(
            "strategy_provenance",
            "provenance",
            _safe_int(wave_g_integration.get("strategy_count")) == 0,
            "passed",
            "No unvalidated fixture or quantum result entered Trading Strategies.",
        ),
    ]

    scientific_checks = [
        _check(
            "provider_history_complete",
            "empirical_evidence",
            provider_complete and provider_rows > 0,
            "passed" if provider_complete and provider_rows > 0 else "blocked",
            f"Provider rows: {provider_rows}; completed partitions: {_safe_int(evidence_truth.get('completed_partition_count'))}.",
        ),
        _check(
            "untouched_holdout_available",
            "empirical_evidence",
            empirical_ready and eligible_windows > 0,
            "passed" if empirical_ready and eligible_windows > 0 else "blocked",
            f"Eligible untouched point-in-time windows: {eligible_windows}.",
        ),
        _check(
            "ibm_provider_recovered",
            "hardware_evidence",
            _text(provider_readiness.get("status")) not in {"", "blocked_provider_probe_failed"},
            "blocked"
            if _text(provider_readiness.get("status")) == "blocked_provider_probe_failed"
            else "waiting",
            (
                "IBM device discovery is blocked by the configured token and instance entitlement mismatch."
                if provider_readiness.get("blocker") == "ibm_token_instance_access_mismatch"
                else "IBM provider readiness has not yet been certified for this pilot."
            ),
        ),
        _check(
            "ibm_hardware_result",
            "hardware_evidence",
            hardware_completed,
            "passed" if hardware_completed else "not_run",
            "No IBM hardware job was authorized, submitted, or completed in Wave H.",
        ),
        _check(
            "untouched_control_suite",
            "statistical_controls",
            controls_passed,
            "passed" if controls_passed else "not_run",
            "Placebo, timing, permutation, and multiple-testing controls require an eligible untouched holdout.",
        ),
        _check(
            "matched_quantum_value_measured",
            "scientific_verdict",
            empirical_measured,
            "passed" if empirical_measured else "not_measurable",
            "No empirical matched classical-versus-quantum holdout comparison exists yet.",
        ),
    ]
    mechanism_certified = all(row["passed"] is True for row in engineering_checks)
    scientific_certified = all(row["passed"] is True for row in scientific_checks)

    run_ledger = [
        {
            "run": "Matched classical baselines",
            "status": "engineering_control_reproduced",
            "fixture_only": True,
            "result": f"{len(_safe_list(classical_result.get('method_results')))} methods rebuilt deterministically.",
        },
        {
            "run": "Ideal quantum simulation",
            "status": "engineering_control_reproduced",
            "fixture_only": True,
            "result": "Local ideal fidelity-kernel result reproduced; this is not market proof.",
        },
        {
            "run": "Finite-shot quantum simulation",
            "status": "engineering_control_reproduced",
            "fixture_only": True,
            "result": f"Local finite-shot control completed at {_safe_int(finite_result.get('shots'))} shots.",
        },
        {
            "run": "Fire Opal on IBM hardware",
            "status": "not_run_not_authorized",
            "fixture_only": False,
            "result": "Engineering manifest prepared; no pilot hardware job was authorized or submitted.",
        },
        {
            "run": "Untouched chronological holdout",
            "status": "not_run_no_eligible_windows",
            "fixture_only": False,
            "result": f"{eligible_windows} eligible windows and {provider_rows} provider-history rows are available.",
        },
        {
            "run": "Placebo and robustness controls",
            "status": "not_run_no_eligible_holdout",
            "fixture_only": False,
            "result": "The control suite is frozen but cannot run before an untouched holdout exists.",
        },
    ]

    provider_readiness_status = _text(
        provider_readiness.get("status"),
        "not_checked",
    )
    provider_blocker = _text(provider_readiness.get("blocker"))
    if not provider_blocker or provider_blocker == "none":
        provider_blocker = (
            "provider_readiness_not_exported"
            if provider_readiness_status == "not_checked"
            else "none"
        )
    blockers = list(dict.fromkeys([
        *_safe_list(evidence.get("blockers")),
        *([provider_blocker] if provider_blocker != "none" else []),
        "exact_hardware_manifest_not_separately_authorized",
        "untouched_control_suite_not_run",
    ]))

    proof_state_key = [
        {
            "state": state,
            "current": state == public_state,
            "meaning": {
                "unproven": "The mechanism works, but no empirical quantum advantage has been measured.",
                "provisional": "Untouched evidence is positive, but hardware or robustness proof is incomplete.",
                "validated": "Matched hardware and classical evidence survives the full control suite.",
                "classically_dominated": "The strongest classical method performs as well as or better than quantum.",
                "decayed": "A previously supported relationship no longer survives current evidence.",
            }[state],
        }
        for state in PUBLIC_PROOF_STATES
    ]

    payload: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "wave_h_crude_oil_pilot_certification",
        "generated_at": generated_at,
        "status": (
            "mechanism_certified_result_unproven"
            if mechanism_certified and not scientific_certified
            else "mechanism_and_result_certified"
            if mechanism_certified and scientific_certified
            else "mechanism_certification_failed"
        ),
        "mechanism_certified": mechanism_certified,
        "scientific_result_certified": scientific_certified,
        "scientific_verdict": scientific_verdict,
        "public_proof_state": public_state,
        "proof_state_key": proof_state_key,
        "plain_english_summary": (
            "Qadam has certified the engineering route for a bounded crude-oil quantum-edge test. "
            "The market result is still unproven: the available historical spine has no eligible "
            "untouched windows, and no IBM hardware experiment was authorized or run."
        ),
        "pilot_manifest": pilot_manifest,
        "evidence_truth": {
            "classified_window_count": _safe_int(alignment_truth.get("classified_window_count")),
            "eligible_window_count": eligible_windows,
            "provider_row_count": provider_rows,
            "completed_partition_count": _safe_int(
                evidence_truth.get("completed_partition_count")
            ),
            "provider_history_certified_complete": provider_complete,
            "leakage_violation_count": _safe_int(
                leakage_truth.get("leakage_violation_count")
            ),
        },
        "engineering_fixture": {
            "contract_fixture_only": fixture_only,
            "shared_manifest_hash": _text(classical_result.get("shared_manifest_hash")),
            "classical_method_count": len(_safe_list(classical_result.get("method_results"))),
            "ideal_quantum_circuit_evaluations": _safe_int(
                ideal_result.get("circuit_evaluation_count")
            ),
            "finite_shot_count": _safe_int(finite_result.get("shots")),
            "hardware_smoke_manifest_hash": _text(
                hardware_public_state.get("manifest_hash")
            ),
            "hardware_smoke_manifest_prepared": hardware_prepared,
            "provider_call_count": provider_calls,
            "hardware_job_submitted": hardware_submitted,
            "hardware_experiment_completed": hardware_completed,
        },
        "run_ledger": run_ledger,
        "controls": controls,
        "certification": {
            "engineering_checks": engineering_checks,
            "scientific_checks": scientific_checks,
            "engineering_pass_count": sum(row["passed"] is True for row in engineering_checks),
            "engineering_check_count": len(engineering_checks),
            "scientific_pass_count": sum(row["passed"] is True for row in scientific_checks),
            "scientific_check_count": len(scientific_checks),
        },
        "hardware_authorization_checkpoint": {
            "separate_authorization_required": True,
            "authorized": False,
            "engineering_manifest_hash": _text(
                hardware_public_state.get("manifest_hash")
            ),
            "qubit_count": _safe_int(hardware_manifest.get("qubit_count")),
            "circuit_count": _safe_int(hardware_manifest.get("circuit_count")),
            "shots_per_circuit": _safe_int(hardware_manifest.get("shots_per_circuit")),
            "total_shots": _safe_int(hardware_manifest.get("total_shots")),
            "maximum_provider_budget_usd": _safe_dict(
                hardware_manifest.get("policy_contract")
            ).get("maximum_provider_budget_usd"),
            "provider_readiness_status": provider_readiness_status,
            "provider_blocker": provider_blocker,
        },
        "downstream_truth": {
            "validated_edge_count": len(_safe_list(wave_g.get("validated_edge_admissions"))),
            "strategy_count": _safe_int(wave_g_integration.get("strategy_count")),
            "risk_review_count": _safe_int(wave_g_integration.get("risk_review_count")),
            "paperops_review_handoff_count": _safe_int(
                wave_g_integration.get("paperops_review_handoff_count")
            ),
            "paper_order_count": _safe_int(
                wave_g_integration.get("paper_order_created_count")
            ),
            "broker_write_count": _safe_int(wave_g_integration.get("broker_write_count")),
        },
        "blockers": blockers,
        "next_actions": [
            "Complete real provider backfill and produce eligible point-in-time crude-oil windows.",
            "Freeze a real empirical manifest and run the untouched classical and simulator comparison.",
            "Fix IBM token-to-instance entitlement, then request separate authorization for the exact empirical hardware manifest.",
            "Run placebo, timing, permutation, and multiple-testing controls before any edge claim.",
        ],
        "expansion": {
            "allowed": False,
            "next_markets": ["silver", "defence", "semiconductors", "prediction_markets"],
            "reason": "Crude-oil empirical and hardware proof is not yet reproducible.",
        },
        "authority": _authority(),
    }
    material = {key: value for key, value in payload.items() if key != "generated_at"}
    payload["content_hash"] = _stable_hash(material)
    errors = validate_wave_h_payload(payload)
    if errors:
        raise ValueError(";".join(errors))
    return payload


def validate_wave_h_payload(payload: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if payload.get("schema_version") != SCHEMA_VERSION:
        errors.append("wave_h_schema_invalid")
    if payload.get("public_proof_state") not in PUBLIC_PROOF_STATES:
        errors.append("wave_h_public_proof_state_invalid")
    authority = _safe_dict(payload.get("authority"))
    for field in ZERO_AUTHORITY_FIELDS:
        if authority.get(field) is not False:
            errors.append(f"wave_h_authority_escalated:{field}")
    if any(value is True for value in authority.values()):
        errors.append("wave_h_unrecognized_true_authority")
    downstream = _safe_dict(payload.get("downstream_truth"))
    if payload.get("scientific_result_certified") is not True and any(
        _safe_int(downstream.get(field)) > 0
        for field in (
            "validated_edge_count",
            "strategy_count",
            "risk_review_count",
            "paperops_review_handoff_count",
            "paper_order_count",
            "broker_write_count",
        )
    ):
        errors.append("wave_h_unproven_result_reached_downstream")
    fixture = _safe_dict(payload.get("engineering_fixture"))
    if fixture.get("contract_fixture_only") is True and payload.get(
        "public_proof_state"
    ) in {"provisional", "validated"}:
        errors.append("wave_h_fixture_promoted_to_edge")
    if fixture.get("provider_call_count") != 0:
        errors.append("wave_h_provider_call_occurred")
    if fixture.get("hardware_job_submitted") is not False:
        errors.append("wave_h_hardware_submission_occurred")
    if payload.get("expansion", {}).get("allowed") is True and payload.get(
        "public_proof_state"
    ) != "validated":
        errors.append("wave_h_expansion_allowed_without_validation")
    material = {
        key: value
        for key, value in payload.items()
        if key not in {"generated_at", "content_hash"}
    }
    if payload.get("content_hash") != _stable_hash(material):
        errors.append("wave_h_content_hash_mismatch")
    errors.extend(_public_key_errors(payload))
    return sorted(set(errors))


def build_current_wave_h_certification(
    *,
    settings: Settings | None = None,
    generated_at: str | None = None,
) -> dict[str, Any]:
    selected = settings or Settings.from_env()
    runtime_dir = Path(selected.runtime_dir)
    evidence = build_point_in_time_foundation(settings=selected)
    manifest_contract = build_shared_manifest_contract(
        empirical_evidence_ready=evidence["empirical_evidence_ready"],
        empirical_blockers=evidence["blockers"],
    )
    batch = build_wave_c_contract_fixture_batch()
    classical = run_classical_discovery(batch)
    classical_repeat = run_classical_discovery(batch)
    quantum_backend = QiskitLocalQuantumDiscoveryBackend()
    ideal = quantum_backend.run(
        batch,
        mode="ideal",
        matched_classical_result=classical,
    )
    ideal_repeat = quantum_backend.run(
        batch,
        mode="ideal",
        matched_classical_result=classical,
    )
    finite = quantum_backend.run(
        batch,
        mode="finite_shot",
        shots=256,
        matched_classical_result=classical,
    )
    hardware_bundle = prepare_fire_opal_ibm_smoke_manifest(
        batch,
        matched_classical_result=classical,
        local_quantum_result=ideal,
        prepared_at="2026-07-12T00:00:00+00:00",
    )
    hardware_public_state = {
        "lifecycle_status": "prepared",
        "manifest_hash": hardware_bundle.manifest.manifest_hash,
        "manifest": hardware_bundle.manifest.to_public_dict(),
        "provider_call_count": 0,
        "hardware_execution_authorized": False,
        "hardware_job_submitted": False,
        "hardware_experiment_completed": False,
        "secret_value_exposed": False,
    }
    return build_wave_h_certification(
        evidence=evidence,
        manifest_contract=manifest_contract,
        classical_result=classical.to_dict(),
        classical_reproduced=classical.to_dict() == classical_repeat.to_dict(),
        ideal_result=ideal.to_dict(),
        ideal_reproduced=ideal.to_dict() == ideal_repeat.to_dict(),
        finite_result=finite.to_dict(),
        hardware_public_state=hardware_public_state,
        provider_readiness=_read_json(runtime_dir / "qctrl_fire_opal_ibm_readiness.json"),
        evaluation_summary=_read_json(
            runtime_dir / "qadam_independent_quantum_value_summary.json"
        ),
        wave_g=_read_json(runtime_dir / "qadam_quantum_edge_wave_g_hybrid_loop.json"),
        generated_at=generated_at or datetime.now(timezone.utc).isoformat(),
    )


def write_wave_h_certification(
    payload: dict[str, Any],
    *,
    runtime_dir: Path | str,
    site_root: Path | None = None,
) -> dict[str, Path]:
    errors = validate_wave_h_payload(payload)
    if errors:
        raise ValueError(";".join(errors))
    resolved_runtime_dir = Path(runtime_dir)
    paths = {
        "runtime": _write_json_atomic(resolved_runtime_dir / ARTIFACT_NAME, payload),
    }
    if site_root is not None:
        paths["site"] = _write_json_atomic(
            site_root / "status" / SITE_ARTIFACT_NAME,
            payload,
        )
    return paths
