"""Canonical public projection for the three-layer Quantum Edge page.

This module is deliberately a read-only aggregator.  It reads the existing
public-safe Wave F, G, and H artifacts, verifies their content-addressed
contracts, and projects one plain-English page model.  It never runs research,
calls a provider, submits hardware, creates trading authority, or touches a
broker.
"""

from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
from typing import Any


SCHEMA_VERSION = "qadam.QuantumEdgeThreeLayerPage.v1"
ARTIFACT_TYPE = "qadam_quantum_edge_three_layer_page"
COPY_VERSION = "quantum-edge-three-layer-v4"
ARTIFACT_NAME = "qadam_quantum_edge_page.json"
SITE_ARTIFACT_NAME = "quantum-edge-page.json"
STALE_AFTER_SECONDS = 7 * 24 * 60 * 60

SOURCE_SPECS = {
    "wave_f": {
        "filename": "qadam_quantum_edge_wave_f_public_view.json",
        "schema_version": "qadam.QuantumEdgeWaveFPublicView.v1",
        "artifact_type": "qadam_quantum_edge_wave_f_public_view",
        "responsibility": (
            "proof ladder, experiments, matched comparison, hardware authenticity, "
            "negative evidence, and provenance"
        ),
    },
    "wave_g": {
        "filename": "qadam_quantum_edge_wave_g_hybrid_loop.json",
        "schema_version": "qadam.QuantumEdgeWaveGHybridLoop.v1",
        "artifact_type": "qadam_quantum_edge_wave_g_hybrid_loop",
        "responsibility": (
            "recurring lifecycle, operational evidence, guarded downstream route, "
            "paper attribution, and daily explanation"
        ),
    },
    "wave_h": {
        "filename": "qadam_quantum_edge_wave_h_crude_oil_certification.json",
        "schema_version": "qadam.QuantumEdgeWaveHCrudeOilCertification.v1",
        "artifact_type": "wave_h_crude_oil_pilot_certification",
        "responsibility": (
            "current proof state, engineering and market-proof checks, pilot ledger, "
            "hardware checkpoint, blockers, and next evidence"
        ),
    },
}

PURPOSE_PARAGRAPH = (
    "Not every pattern needs quantum analysis. It is used when a relationship "
    "might involve complicated interactions, sequencing, regimes or path "
    "dependence that simpler analysis could miss. Quantum Edge is Qadam’s "
    "independent proof room for deciding whether a nonlinear or quantum-assisted "
    "method genuinely contributes something that the best conventional method "
    "missed. The framework presents the experiment record first, then any strategy "
    "and paper impact, and closes with the formal market-level verdict."
)

GUIDANCE_QUESTIONS = [
    "Can Qadam access the required technology?",
    "Was an actual hardware experiment executed?",
    "Can the result be reproduced?",
    "Did it beat the strongest fair classical comparison?",
    "Did that advantage survive completely untouched market data?",
    "Did it ultimately improve a governed paper decision?",
]

GUIDANCE_OUTCOMES = [
    "Strengthen the evidence.",
    "Agree with the classical result.",
    "Lose to the classical method.",
    "Weaken the original pattern.",
    "Remain unmeasurable because evidence is missing.",
]

GUIDANCE_INTRODUCTION = (
    "Quantum analysis earns a role in Qadam’s research process only when it clears "
    "six increasingly demanding standards—from infrastructure access to measurable "
    "decision value under paper-trading governance."
)

GUIDANCE_WORKFLOW_STEPS = [
    {
        "key": "evidence_assembly",
        "label": "Evidence assembly",
        "title": "Python prepares the evidence",
        "description": (
            "Qadam aligns prices, timestamps, source signals, instruments, and market "
            "regimes into a structured point-in-time dataset."
        ),
    },
    {
        "key": "classical_discovery",
        "label": "Classical discovery",
        "title": "Classical models search for patterns",
        "description": (
            "They identify lead-lag relationships, divergences, correlations, "
            "breakouts, and regime changes."
        ),
    },
    {
        "key": "quantum_exploration",
        "label": "Quantum exploration",
        "title": "The quantum lane examines selected problems",
        "description": (
            "Quantum-assisted methods test nonlinear, sequential, and path-dependent "
            "structure that classical analysis may have missed. This lane may originate "
            "a new candidate relationship; it does not merely review classical output."
        ),
    },
    {
        "key": "matched_comparison",
        "label": "Matched comparison",
        "title": "Both lanes are compared fairly",
        "description": (
            "The same frozen evidence and decision rules are applied to the strongest "
            "classical and quantum-assisted methods to isolate any incremental signal."
        ),
    },
    {
        "key": "ordinary_validation",
        "label": "Standard validation",
        "title": "Ordinary validation still applies",
        "description": (
            "Any quantum-originated pattern must survive historical testing, untouched "
            "data, trading costs, forward observation, and strategy validation before "
            "it can influence paper trading."
        ),
    },
]

GUIDANCE_OPERATING_MODEL = {
    "label": "Operating model",
    "title": "Hybrid by design—not a standalone quantum computer.",
    "body": (
        "Even when genuine IBM hardware is used, classical computing remains essential. "
        "It prepares the data, constructs circuits, submits jobs, decodes measurements, "
        "runs matched comparisons, and operates Qadam."
    ),
}

GUIDANCE_PROOF_STEPS = [
    {
        "key": "technology_access",
        "label": "Infrastructure readiness",
        "question": GUIDANCE_QUESTIONS[0],
        "meaning": (
            "Confirms that the required tools and providers are available. This "
            "establishes access only; it does not show that an experiment ran."
        ),
    },
    {
        "key": "hardware_execution",
        "label": "Hardware execution",
        "question": GUIDANCE_QUESTIONS[1],
        "meaning": (
            "Distinguishes a real quantum-hardware job from a local simulation "
            "or a prepared test."
        ),
    },
    {
        "key": "reproducibility",
        "label": "Result reproducibility",
        "question": GUIDANCE_QUESTIONS[2],
        "meaning": (
            "Checks whether the same method produces the same result again, "
            "rather than a one-off outcome."
        ),
    },
    {
        "key": "classical_comparison",
        "label": "Matched classical benchmark",
        "question": GUIDANCE_QUESTIONS[3],
        "meaning": (
            "Compares the quantum-assisted method with Qadam’s strongest "
            "conventional method using the same evidence and rules."
        ),
    },
    {
        "key": "untouched_market_data",
        "label": "Untouched holdout validation",
        "question": GUIDANCE_QUESTIONS[4],
        "meaning": (
            "Checks whether the advantage remains on market data that was never "
            "used to develop or tune the method."
        ),
    },
    {
        "key": "governed_paper_impact",
        "label": "Governed paper-decision impact",
        "question": GUIDANCE_QUESTIONS[5],
        "meaning": (
            "Asks whether the added evidence materially improved a paper decision "
            "while Qadam’s normal governance and risk controls remained in place."
        ),
    },
]

GUIDANCE_OUTCOME_STATES = [
    {
        "key": "evidence_strengthened",
        "label": "Incremental quantum evidence",
        "description": (
            "The quantum-assisted method finds useful information beyond the "
            "strongest conventional method."
        ),
    },
    {
        "key": "joint_corroboration",
        "label": "Corroborated classical signal",
        "description": (
            "Quantum supports the same conclusion as the conventional method, "
            "but does not show a unique advantage."
        ),
    },
    {
        "key": "classical_preferred",
        "label": "Classical method preferred",
        "description": "The conventional method performs equally well or better.",
    },
    {
        "key": "pattern_weakened",
        "label": "Original thesis weakened",
        "description": (
            "The more demanding test reduces confidence in the relationship "
            "Qadam originally found."
        ),
    },
    {
        "key": "not_measurable",
        "label": "Insufficient evidence",
        "description": (
            "Required evidence is missing, so the contribution cannot yet be measured."
        ),
    },
]

GUIDANCE_TAKEAWAY = {
    "label": "Research discipline",
    "title": "A classical-preferred result is a successful research outcome.",
    "body": (
        "It shows that the conventional method explains the evidence as well as or "
        "better than the more complex approach, allowing Qadam to avoid unsupported "
        "complexity."
    ),
}

PROOF_LABELS = {
    "unproven": "Unproven",
    "provisional": "Provisional evidence",
    "validated": "Validated",
    "classically_dominated": "Classical preferred",
    "decayed": "Decayed",
}

VERDICT_LABELS = {
    "not_run": "Not run",
    "not_measurable": "Not measurable yet",
    "waiting_for_evidence": "Waiting for evidence",
    "blocked": "Blocked",
    "failed": "Failed safely",
    "failed_safely": "Failed safely",
    "inconclusive": "Inconclusive",
    "quantum_strengthened": "Quantum evidence strengthened",
    "joint_corroboration": "Joint corroboration",
    "classical_preferred": "Classical preferred",
    "classically_dominated": "Classical preferred",
    "weakened": "Evidence weakened",
    "validated": "Validated",
    "decayed": "Decayed",
    "unavailable": "Unavailable until source records agree",
}

ZERO_AUTHORITY_FIELDS = (
    "broker_write_allowed",
    "candidate_promotion_allowed",
    "dashboard_command_authority",
    "direct_broker_call_allowed",
    "execution_allowed",
    "execution_approval_allowed",
    "execution_approval_created",
    "forced_promotion_allowed",
    "forced_strategy_allowed",
    "forced_trade_allowed",
    "hardware_scheduler_enabled",
    "hardware_submission_allowed",
    "live_capital_enabled",
    "paper_order_allowed",
    "paper_order_created",
    "paper_proof_ledger_credit_allowed",
    "paperops_bypass_allowed",
    "position_sizing_allowed",
    "proof_credit_allowed",
    "provider_call_allowed",
    "qctrl_bypass_allowed",
    "risk_approval_allowed",
    "risk_approval_created",
    "strategy_hypothesis_creation_allowed",
    "strategy_mutation_allowed",
    "telegram_command_authority",
    "telegram_send_allowed",
    "trade_candidate_creation_allowed",
    "validated_edge_creation_allowed",
)

FORBIDDEN_PUBLIC_KEYS = {
    "action_id",
    "api_key",
    "authorization",
    "backend_name",
    "credentials",
    "password",
    "private_key",
    "provider_job_ids",
    "qasm_circuits",
    "raw_broker_payload",
    "raw_provider_response",
    "secret",
    "token",
}

SECRET_PATTERNS = (
    re.compile(r"\bsk-[A-Za-z0-9_-]{20,}\b"),
    re.compile(r"\bghp_[A-Za-z0-9_]{20,}\b"),
    re.compile(r"\bAIza[A-Za-z0-9_-]{20,}\b"),
    re.compile(r"\b\d{6,}:[A-Za-z0-9_-]{20,}\b"),
    re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
)

POSITIVE_CHECK_STATUSES = {
    "passed",
    "complete",
    "completed",
    "ready",
    "available",
    "certified",
}
NEGATIVE_EXPLANATION_PATTERNS = (
    re.compile(r"\bwaiting\b", re.IGNORECASE),
    re.compile(r"\bnot (?:yet )?certified\b", re.IGNORECASE),
    re.compile(r"\bhas not (?:yet )?been certified\b", re.IGNORECASE),
)


def stable_hash(value: Any) -> str:
    """Return the repository's canonical deterministic SHA-256 digest."""

    encoded = json.dumps(value, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


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


def _guidance_current_capability(f_quantum: dict[str, Any]) -> dict[str, Any]:
    experiments = [
        row for row in _safe_list(f_quantum.get("experiments")) if isinstance(row, dict)
    ]
    hardware = _safe_dict(f_quantum.get("hardware_authenticity"))
    local_simulation_reproduced = any(
        "simulat" in _text(row.get("kind")).lower()
        and _text(row.get("state")).lower() in POSITIVE_CHECK_STATUSES
        for row in experiments
    )
    provider_accessible = hardware.get("ibm_instance_accessible") is True
    hardware_authorized = hardware.get("hardware_execution_authorized") is True
    hardware_submitted = hardware.get("hardware_job_submitted") is True
    hardware_completed = hardware.get("hardware_experiment_completed") is True

    readiness = (
        "Qadam has reproduced its quantum experiment through local simulation"
        if local_simulation_reproduced
        else "Qadam has not yet reproduced its quantum experiment through local simulation"
    )
    provider = (
        "and can access the configured Q-CTRL/IBM provider path."
        if provider_accessible
        else "and has not yet confirmed access to the configured Q-CTRL/IBM provider path."
    )
    if hardware_completed:
        title = "Hardware execution recorded; market validation still governs adoption."
        hardware_state = (
            "An IBM hardware experiment is recorded, but that result must still pass "
            "the same untouched-data, cost, forward-observation, and strategy tests "
            "before it can influence paper trading."
        )
    elif hardware_submitted:
        title = "IBM hardware execution is in progress; no completed result exists yet."
        hardware_state = (
            "An IBM hardware job has been submitted but not completed, so the quantum "
            "lane is not yet a hardware-proven pattern-discovery engine."
        )
    elif hardware_authorized:
        title = "IBM hardware is authorized but has not yet been executed."
        hardware_state = (
            "The experiment has separate authorization but no submitted or completed "
            "hardware result, so the quantum lane remains an experimental pathway."
        )
    else:
        title = "Experimental pathway implemented; IBM hardware proof pending."
        hardware_state = (
            "No IBM hardware experiment has been authorized, submitted, or executed. "
            "The quantum lane is therefore an implemented experimental pathway—not yet "
            "a hardware-proven pattern-discovery engine."
        )

    return {
        "label": "Current capability",
        "title": title,
        "body": f"{readiness} {provider} {hardware_state}",
        "local_simulation_reproduced": local_simulation_reproduced,
        "provider_accessible": provider_accessible,
        "hardware_authorized": hardware_authorized,
        "hardware_submitted": hardware_submitted,
        "hardware_completed": hardware_completed,
    }


def _authority() -> dict[str, bool]:
    return {field: False for field in ZERO_AUTHORITY_FIELDS}


def _canonical_material(payload: dict[str, Any]) -> dict[str, Any]:
    return {
        key: value
        for key, value in payload.items()
        if key not in {"generated_at", "content_hash"}
    }


def _read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return payload if isinstance(payload, dict) else {}


def load_quantum_edge_sources(runtime_dir: str | Path) -> dict[str, dict[str, Any]]:
    """Read only the three public Wave artifacts from the canonical runtime dir."""

    root = Path(runtime_dir)
    return {
        source_id: _read_json(root / str(spec["filename"]))
        for source_id, spec in SOURCE_SPECS.items()
    }


def _parse_time(value: Any) -> datetime | None:
    text = _text(value)
    if not text:
        return None
    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _public_safety_errors(value: Any, *, path: str = "root") -> list[str]:
    errors: list[str] = []
    if isinstance(value, dict):
        for key, child in value.items():
            key_text = str(key).lower()
            child_path = f"{path}.{key}"
            if key_text in FORBIDDEN_PUBLIC_KEYS:
                errors.append(f"forbidden_public_key:{child_path}")
            if key_text in ZERO_AUTHORITY_FIELDS and child is not False:
                errors.append(f"authority_field_escalated:{child_path}")
            if key_text == "authority" and isinstance(child, dict):
                for authority_key, authority_value in child.items():
                    if authority_value is not False:
                        errors.append(
                            f"authority_escalated:{child_path}.{authority_key}"
                        )
            errors.extend(_public_safety_errors(child, path=child_path))
    elif isinstance(value, list):
        for index, child in enumerate(value):
            errors.extend(_public_safety_errors(child, path=f"{path}[{index}]"))
    elif isinstance(value, str):
        if value.startswith("/Users/") or value.startswith("file://"):
            errors.append(f"local_path_exposed:{path}")
        for pattern in SECRET_PATTERNS:
            if pattern.search(value):
                errors.append(f"secret_like_value:{path}")
    return sorted(set(errors))


def _source_integrity_errors(
    sources: dict[str, dict[str, Any]],
) -> list[str]:
    errors: list[str] = []
    for source_id, spec in SOURCE_SPECS.items():
        source = _safe_dict(sources.get(source_id))
        if not source:
            errors.append(f"source_missing:{source_id}")
            continue
        if source.get("schema_version") != spec["schema_version"]:
            errors.append(f"source_schema_invalid:{source_id}")
        if source.get("artifact_type") != spec["artifact_type"]:
            errors.append(f"source_artifact_type_invalid:{source_id}")
        if _parse_time(source.get("generated_at")) is None:
            errors.append(f"source_generated_at_invalid:{source_id}")
        expected_hash = stable_hash(_canonical_material(source))
        if source.get("content_hash") != expected_hash:
            errors.append(f"source_content_hash_mismatch:{source_id}")
    return sorted(set(errors))


def _check_contradiction_errors(
    checks: Any,
    *,
    group: str,
) -> list[str]:
    errors: list[str] = []
    rows = [row for row in _safe_list(checks) if isinstance(row, dict)]
    seen: set[str] = set()
    for index, row in enumerate(rows):
        key = _text(row.get("key"), f"row_{index}")
        if key in seen:
            errors.append(f"duplicate_check_key:{group}:{key}")
        seen.add(key)
        passed = row.get("passed")
        status = _text(row.get("status")).lower().replace("-", "_").replace(" ", "_")
        explanation = _text(row.get("explanation"))
        status_is_positive = status in POSITIVE_CHECK_STATUSES
        if passed is True and not status_is_positive:
            errors.append(f"semantic_contradiction:{group}:{key}:passed_vs_{status or 'missing'}")
        if passed is False and status_is_positive:
            errors.append(f"semantic_contradiction:{group}:{key}:failed_vs_{status}")
        if passed not in {True, False}:
            errors.append(f"check_boolean_invalid:{group}:{key}")
        if passed is True and any(
            pattern.search(explanation) for pattern in NEGATIVE_EXPLANATION_PATTERNS
        ):
            errors.append(
                f"semantic_contradiction:{group}:{key}:passed_vs_explanation"
            )
    return errors


def _matching_nonempty(values: list[Any], *, key: str) -> list[str]:
    normalized = [_text(value) for value in values if _text(value)]
    return [] if len(set(normalized)) <= 1 else [f"evidence_identity_conflict:{key}"]


def _source_semantic_errors(
    sources: dict[str, dict[str, Any]],
) -> list[str]:
    f = _safe_dict(sources.get("wave_f"))
    g = _safe_dict(sources.get("wave_g"))
    h = _safe_dict(sources.get("wave_h"))
    if not all((f, g, h)):
        return []

    errors: list[str] = []
    f_quantum = _safe_dict(f.get("quantum_edge"))
    g_stages = _safe_dict(g.get("daily_stages"))
    g_integration = _safe_dict(g.get("paper_integration"))
    h_fixture = _safe_dict(h.get("engineering_fixture"))
    h_certification = _safe_dict(h.get("certification"))
    h_hardware = _safe_dict(h.get("hardware_authorization_checkpoint"))
    h_pilot = _safe_dict(h.get("pilot_manifest"))

    proof_keys = [
        row.get("key")
        for row in _safe_list(f_quantum.get("proof_ladder"))
        if isinstance(row, dict)
    ]
    expected_proof_keys = [
        "provider_configured",
        "ibm_hardware_executed",
        "result_reproduced",
        "classical_baseline_beaten",
        "untouched_advantage_survived",
        "paper_decision_improved",
    ]
    if proof_keys != expected_proof_keys:
        errors.append("wave_f_proof_ladder_contract_changed")

    provider_check = next(
        (
            row
            for row in _safe_list(h_certification.get("scientific_checks"))
            if isinstance(row, dict)
            and row.get("key") in {"ibm_provider_recovered", "provider_accessible"}
        ),
        {},
    )
    provider_step = next(
        (
            row
            for row in _safe_list(f_quantum.get("proof_ladder"))
            if isinstance(row, dict) and row.get("key") == "provider_configured"
        ),
        {},
    )
    provider_access_blocked_recorded = any(
        "hardware access is blocked" in _text(row.get("title")).lower()
        for row in _safe_list(f_quantum.get("negative_results"))
        if isinstance(row, dict)
    )
    if provider_check.get("passed") is True:
        if provider_step.get("state") != "complete":
            errors.append("provider_readiness_conflict:wave_f_proof_ladder")
        if provider_access_blocked_recorded:
            errors.append("provider_readiness_conflict:wave_f_negative_evidence")

    lifecycle_states = [
        row.get("state")
        for row in _safe_list(g.get("public_lifecycle"))
        if isinstance(row, dict)
    ]
    if lifecycle_states != [
        "candidate noticed",
        "experiment prepared",
        "experiment executed",
        "result reproduced",
        "evidence strengthened",
        "edge validated",
        "strategy influenced",
        "paper outcome observed",
    ]:
        errors.append("wave_g_public_lifecycle_contract_changed")

    engineering_checks = _safe_list(h_certification.get("engineering_checks"))
    scientific_checks = _safe_list(h_certification.get("scientific_checks"))
    errors.extend(
        _check_contradiction_errors(
            engineering_checks,
            group="engineering_checks",
        )
    )
    errors.extend(
        _check_contradiction_errors(
            scientific_checks,
            group="scientific_checks",
        )
    )
    for group, checks, prefix in (
        ("engineering", engineering_checks, "engineering"),
        ("scientific", scientific_checks, "scientific"),
    ):
        declared_count = _safe_int(h_certification.get(f"{prefix}_check_count"), -1)
        declared_passes = _safe_int(h_certification.get(f"{prefix}_pass_count"), -1)
        actual_passes = sum(
            isinstance(row, dict) and row.get("passed") is True for row in checks
        )
        if declared_count != len(checks):
            errors.append(f"check_count_mismatch:{group}")
        if declared_passes != actual_passes:
            errors.append(f"check_pass_count_mismatch:{group}")

    shared_manifest_values = [
        _safe_dict(f_quantum.get("provenance")).get("shared_manifest_hash"),
        _safe_dict(g_stages.get("classical_discovery")).get("shared_manifest_hash"),
        _safe_dict(g_stages.get("local_quantum_simulation")).get("shared_manifest_hash"),
        h_fixture.get("shared_manifest_hash"),
    ]
    errors.extend(
        _matching_nonempty(shared_manifest_values, key="shared_manifest_hash")
    )
    hardware_manifest_values = [
        _safe_dict(f_quantum.get("hardware_authenticity")).get("prepared_manifest_hash"),
        _safe_dict(g_stages.get("hardware_experiment_preparation")).get(
            "prepared_manifest_hash"
        ),
        h_fixture.get("hardware_smoke_manifest_hash"),
        h_hardware.get("engineering_manifest_hash"),
        h_pilot.get("engineering_smoke_manifest_hash"),
    ]
    errors.extend(
        _matching_nonempty(hardware_manifest_values, key="hardware_manifest_hash")
    )

    h_downstream = _safe_dict(h.get("downstream_truth"))
    downstream_pairs = {
        "validated_edge_count": (
            _safe_int(h_downstream.get("validated_edge_count")),
            len(_safe_list(g.get("validated_edge_admissions"))),
        ),
        "strategy_count": (
            _safe_int(h_downstream.get("strategy_count")),
            _safe_int(g_integration.get("strategy_count")),
        ),
        "risk_review_count": (
            _safe_int(h_downstream.get("risk_review_count")),
            _safe_int(g_integration.get("risk_review_count")),
        ),
        "paperops_review_handoff_count": (
            _safe_int(h_downstream.get("paperops_review_handoff_count")),
            _safe_int(g_integration.get("paperops_review_handoff_count")),
        ),
        "paper_order_count": (
            _safe_int(h_downstream.get("paper_order_count")),
            _safe_int(g_integration.get("paper_order_created_count")),
        ),
        "broker_write_count": (
            _safe_int(h_downstream.get("broker_write_count")),
            _safe_int(g_integration.get("broker_write_count")),
        ),
    }
    for field, pair in downstream_pairs.items():
        if pair[0] != pair[1]:
            errors.append(f"downstream_lineage_conflict:{field}")

    proof_state = _text(h.get("public_proof_state"))
    verdict = _text(h.get("scientific_verdict"))
    if proof_state not in PROOF_LABELS:
        errors.append("wave_h_public_proof_state_invalid")
    if proof_state == "classically_dominated" and verdict not in {
        "classical_preferred",
        "classically_dominated",
    }:
        errors.append("classical_preferred_verdict_conflict")
    if proof_state == "validated" and h.get("scientific_result_certified") is not True:
        errors.append("validated_state_without_scientific_certification")
    if h_fixture.get("contract_fixture_only") is True and proof_state in {
        "provisional",
        "validated",
    }:
        errors.append("fixture_promoted_to_market_proof")
    if h.get("scientific_result_certified") is not True and any(
        value > 0 for value, _ in downstream_pairs.values()
    ):
        errors.append("unproven_result_reached_downstream")

    mechanism_from_checks = bool(engineering_checks) and all(
        isinstance(row, dict) and row.get("passed") is True
        for row in engineering_checks
    )
    scientific_from_checks = bool(scientific_checks) and all(
        isinstance(row, dict) and row.get("passed") is True
        for row in scientific_checks
    )
    if h.get("mechanism_certified") is not mechanism_from_checks:
        errors.append("mechanism_certification_boolean_conflict")
    if h.get("scientific_result_certified") is not scientific_from_checks:
        errors.append("scientific_certification_boolean_conflict")
    return sorted(set(errors))


def _source_artifact_records(
    sources: dict[str, dict[str, Any]],
    integrity_errors: list[str],
) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for source_id, spec in SOURCE_SPECS.items():
        source = _safe_dict(sources.get(source_id))
        records.append(
            {
                "source_id": source_id,
                "artifact_name": spec["filename"],
                "artifact_type": source.get("artifact_type"),
                "schema_version": source.get("schema_version"),
                "generated_at": source.get("generated_at"),
                "content_hash": source.get("content_hash"),
                "content_hash_verified": bool(source) and not any(
                    error.endswith(f":{source_id}") for error in integrity_errors
                ),
                "responsibility": spec["responsibility"],
            }
        )
    return records


def _freshness(
    sources: dict[str, dict[str, Any]],
    *,
    generated_at: str,
    coherence_passed: bool,
) -> dict[str, Any]:
    timestamps = {
        source_id: _parse_time(_safe_dict(source).get("generated_at"))
        for source_id, source in sources.items()
    }
    available = [value for value in timestamps.values() if value is not None]
    if not coherence_passed:
        status = "not_evaluated_source_truth_conflict"
        stale_sources: list[str] = []
    else:
        generated = _parse_time(generated_at) or datetime.now(timezone.utc)
        stale_sources = sorted(
            source_id
            for source_id, value in timestamps.items()
            if value is not None
            and (generated - value).total_seconds() > STALE_AFTER_SECONDS
        )
        status = "stale" if stale_sources else "fresh"
    return {
        "status": status,
        "coherence_checked_before_freshness": True,
        "semantic_coherence_passed": coherence_passed,
        "stale_after_seconds": STALE_AFTER_SECONDS,
        "stale_source_ids": stale_sources,
        "oldest_source_generated_at": min(available).isoformat() if available else None,
        "newest_source_generated_at": max(available).isoformat() if available else None,
        "source_generated_at": {
            source_id: value.isoformat() if value else None
            for source_id, value in sorted(timestamps.items())
        },
    }


def _conflicting_check_keys(errors: list[str], *, group: str) -> set[str]:
    keys: set[str] = set()
    prefix = f"semantic_contradiction:{group}:"
    for error in errors:
        if error.startswith(prefix):
            remainder = error[len(prefix) :]
            keys.add(remainder.split(":", 1)[0])
    return keys


def _check_summary(
    certification: dict[str, Any],
    *,
    prefix: str,
    semantic_errors: list[str],
    globally_available: bool,
) -> dict[str, Any]:
    source_group = f"{prefix}_checks"
    rows = [
        row
        for row in _safe_list(certification.get(source_group))
        if isinstance(row, dict)
    ]
    conflict_keys = _conflicting_check_keys(semantic_errors, group=source_group)
    group_errors = [
        error
        for error in semantic_errors
        if f":{prefix}" in error or error.startswith(f"{prefix}_")
    ]
    available = globally_available and not conflict_keys and not group_errors
    public_rows: list[dict[str, Any]] = []
    for row in rows:
        key = _text(row.get("key"), "unidentified_check")
        conflict = key in conflict_keys
        public_rows.append(
            {
                "key": key,
                "category": _text(row.get("category"), "evidence"),
                "status": "source_truth_conflict" if conflict else row.get("status"),
                "passed": None if conflict else row.get("passed") is True,
                "explanation": (
                    "The source record marks this condition as both passed and incomplete. "
                    "Qadam excludes it from the score until the source is corrected."
                    if conflict
                    else _text(row.get("explanation"), "No explanation was exported.")
                ),
                "source_check_status": row.get("status") if conflict else None,
            }
        )
    pass_count = sum(row["passed"] is True for row in public_rows) if available else None
    check_count = len(public_rows)
    status = (
        "source_truth_conflict"
        if not available
        else "passed"
        if check_count > 0 and pass_count == check_count
        else "incomplete"
    )
    return {
        "available": available,
        "status": status,
        "pass_count": pass_count,
        "check_count": check_count,
        "score_label": f"{pass_count}/{check_count}" if available else "Unavailable",
        "checks": public_rows,
    }


def _proof_summary(
    *,
    projection_status: str,
    raw_proof_state: str,
    raw_verdict: str,
) -> tuple[str, str, str, str]:
    if projection_status != "ready":
        reason = {
            "source_unavailable": "one or more required public evidence records are unavailable",
            "source_stale": "one or more required public evidence records are stale",
        }.get(
            projection_status,
            "the public evidence records contain an internal contradiction",
        )
        return (
            "unproven",
            "unavailable",
            "Unavailable until source records agree",
            (
                "Qadam is keeping the market-level quantum edge unproven because "
                f"{reason}. No disputed score or downstream claim is being promoted."
            ),
        )

    state = raw_proof_state if raw_proof_state in PROOF_LABELS else "unproven"
    verdict = raw_verdict or "not_measurable"
    if state == "classically_dominated":
        summary = (
            "The fair comparison found that the strongest conventional method explains "
            "the evidence as well as, or better than, the quantum-assisted method. "
            "Qadam therefore prefers the simpler classical method."
        )
    elif state == "validated":
        summary = (
            "A quantum-assisted contribution has passed the governed market-evidence, "
            "hardware, robustness, and matched-comparison requirements recorded here."
        )
    elif state == "provisional":
        summary = (
            "Untouched evidence is provisionally positive, but the full hardware or "
            "robustness proof is not complete."
        )
    elif state == "decayed":
        summary = (
            "A previously supported contribution no longer survives current evidence. "
            "Qadam treats the edge as decayed rather than carrying old proof forward."
        )
    else:
        summary = (
            "A market-level quantum edge has not been proven. Qadam has evidence that "
            "its experimental machinery works, but incremental predictive and economic "
            "value has not yet been established on untouched market evidence."
        )
    return state, verdict, VERDICT_LABELS.get(verdict, verdict.replace("_", " ").title()), summary


def _help_item(label: str, text: str) -> dict[str, str]:
    return {"accessible_label": label, "text": text}


def _plain_english_help(
    *,
    projection_status: str,
    proof_label: str,
    engineering: dict[str, Any],
    market: dict[str, Any],
    h: dict[str, Any],
) -> dict[str, dict[str, str]]:
    h_evidence = _safe_dict(h.get("evidence_truth"))
    h_fixture = _safe_dict(h.get("engineering_fixture"))
    downstream = _safe_dict(h.get("downstream_truth"))
    hardware_complete = h_fixture.get("hardware_experiment_completed") is True
    engineering_score = engineering.get("score_label", "Unavailable")
    market_score = market.get("score_label", "Unavailable")
    market_check_labels = {
        "provider_history_complete": "complete, time-stamped provider history",
        "untouched_holdout_available": "untouched market evidence",
        "ibm_provider_recovered": "access to the configured quantum provider",
        "ibm_hardware_result": "a verified IBM hardware result",
        "untouched_control_suite": "robustness checks on untouched evidence",
        "matched_quantum_value_measured": "a fair classical-versus-quantum result",
    }
    if market.get("available"):
        passed = [
            market_check_labels.get(
                _text(row.get("key")),
                _text(row.get("key")).replace("_", " "),
            )
            for row in market.get("checks", [])
            if row.get("passed") is True
        ]
        missing = [
            market_check_labels.get(
                _text(row.get("key")),
                _text(row.get("key")).replace("_", " "),
            )
            for row in market.get("checks", [])
            if row.get("passed") is not True
        ]
        market_text = (
            "These checks show what is still required before Qadam may claim market value. "
            f"Currently passed: {', '.join(passed) if passed else 'none'}. "
            f"Still incomplete: {', '.join(missing) if missing else 'none'}. "
            "Provider access alone is not an IBM experiment or a market advantage."
        )
    else:
        market_text = (
            "The source checklist is internally inconsistent, so Qadam is not displaying "
            "a market-proof numerator. The market claim remains unproven until the source "
            "record is corrected."
        )
    current_snapshot = (
        f"The engineering score is {engineering_score}: it tests whether the experimental "
        f"machinery works. The market-proof score is {market_score}: it tests whether the "
        "investment claim has evidence. It is like proving an engine works on a test bench "
        "without yet proving that it wins races."
    )
    return {
        "current_proof_state": _help_item(
            "Explain the current proof state",
            (
                "A market-level quantum edge has not been proven. Qadam has shown that its "
                "testing process works, but it has not shown that a quantum-assisted method "
                "improves predictions on real untouched market evidence."
                if proof_label == "Unproven" and projection_status == "ready"
                else "The headline remains unproven while Qadam waits for coherent, complete evidence."
            ),
        ),
        "strongest_evidence": _help_item(
            "Explain the strongest evidence",
            "This is a known-answer synthetic test. Qadam deliberately used data containing a relationship it already knew was there, then checked whether the classical and local quantum methods could recover it. Passing shows that the test machinery works; it does not prove a market edge.",
        ),
        "local_quantum_simulation": _help_item(
            "Explain local quantum simulation",
            "This ran on a simulator, not IBM quantum hardware. It demonstrates that the software path and circuit logic can be reproduced, but it does not establish quantum-hardware performance or market advantage.",
        ),
        "engineering_mechanism": _help_item(
            "Explain the engineering mechanism score",
            "These checks test the experimental machinery. They cover frozen inputs, reproducibility, lineage, safety, and authority isolation. A complete engineering score certifies the test rig, not predictive or investment performance.",
        ),
        "engineering_vs_market_proof": _help_item(
            "Explain the two proof scores",
            current_snapshot,
        ),
        "market_proof_prerequisites": _help_item(
            "Explain market-proof prerequisites",
            market_text,
        ),
        "provider_access": _help_item(
            "Explain provider access",
            "Access is not execution. This confirms only that Qadam can reach the configured provider path. It does not mean a quantum circuit was run or that a result exists.",
        ),
        "ibm_hardware": _help_item(
            "Explain IBM hardware evidence",
            (
                "The current sanitized record says an IBM hardware experiment completed. That record still has to be read together with the matched comparison and untouched-market controls."
                if hardware_complete
                else "The current record shows that no IBM hardware experiment was authorized, submitted, completed, or verified. A prepared circuit manifest and a local simulation are not hardware execution."
            ),
        ),
        "untouched_holdout": _help_item(
            "Explain untouched market evidence",
            "An untouched holdout is market history kept completely out of discovery and tuning, then opened only for the final test. Without eligible untouched evidence, Qadam cannot fairly measure whether either method generalizes to unseen markets.",
        ),
        "matched_classical_comparison": _help_item(
            "Explain the matched classical comparison",
            "No winner exists until both methods are tested on the same unseen evidence. If the fair comparison has not run, the result is not measurable; it is neither a quantum loss nor a classical win.",
        ),
        "classical_preferred": _help_item(
            "Explain Classical preferred",
            "This is a useful scientific result. It means the simpler conventional method explains the evidence just as well as, or better than, the more complicated method. Qadam should prefer the simpler method.",
        ),
        "classified_vs_eligible_windows": _help_item(
            "Explain classified and eligible windows",
            (
                "Classified windows have been inspected and categorized. Eligible holdout "
                "windows also satisfy the stricter point-in-time, completeness, and independence "
                f"rules. The current record has {_safe_int(h_evidence.get('classified_window_count'))} "
                f"classified windows and {_safe_int(h_evidence.get('eligible_window_count'))} eligible windows."
            ),
        ),
        "provider_history": _help_item(
            "Explain provider-history readiness",
            "Provider-history rows are raw time-stamped records. Completed partitions are validated, coherent groups ready for point-in-time testing. Raw rows in incomplete or failing partitions cannot create eligible holdout evidence by themselves.",
        ),
        "strategy_influence": _help_item(
            "Explain strategy influence",
            (
                "No strategy may change because of quantum evidence until the contribution "
                "passes independent market validation. A simulator, synthetic fixture, provider "
                f"connection, or prepared manifest cannot do that. Current strategy count: {_safe_int(downstream.get('strategy_count'))}."
            ),
        ),
        "paper_outcome_lineage": _help_item(
            "Explain paper outcome lineage",
            "This count changes only after validated evidence affects a governed paper decision and the resulting paper outcome is recorded. A zero means no paper decision or result can currently be traced to validated quantum evidence.",
        ),
    }


def build_quantum_edge_page_view_model_from_sources(
    sources: dict[str, dict[str, Any]],
    *,
    generated_at: str,
) -> dict[str, Any]:
    """Validate Wave F/G/H and build one deterministic, fail-closed page model."""

    safety_errors: list[str] = []
    for source_id, source in sources.items():
        safety_errors.extend(
            f"{source_id}:{error}" for error in _public_safety_errors(source)
        )
    if safety_errors:
        raise ValueError("unsafe_quantum_edge_source:" + ";".join(sorted(safety_errors)))

    integrity_errors = _source_integrity_errors(sources)
    semantic_errors = (
        _source_semantic_errors(sources) if not integrity_errors else []
    )
    has_missing_source = any(error.startswith("source_missing:") for error in integrity_errors)
    coherence_passed = not integrity_errors and not semantic_errors
    freshness = _freshness(
        sources,
        generated_at=generated_at,
        coherence_passed=coherence_passed,
    )
    if has_missing_source:
        projection_status = "source_unavailable"
    elif integrity_errors or semantic_errors:
        projection_status = "source_truth_conflict"
    elif freshness["status"] == "stale":
        projection_status = "source_stale"
    else:
        projection_status = "ready"

    f = _safe_dict(sources.get("wave_f"))
    g = _safe_dict(sources.get("wave_g"))
    h = _safe_dict(sources.get("wave_h"))
    f_quantum = _safe_dict(f.get("quantum_edge"))
    certification = _safe_dict(h.get("certification"))
    global_check_availability = not integrity_errors and not any(
        error.startswith((
            "evidence_identity_conflict:",
            "downstream_lineage_conflict:",
            "wave_h_",
            "provider_readiness_conflict:",
            "fixture_promoted",
            "unproven_result",
        ))
        for error in semantic_errors
    )
    engineering = _check_summary(
        certification,
        prefix="engineering",
        semantic_errors=semantic_errors,
        globally_available=global_check_availability,
    )
    market = _check_summary(
        certification,
        prefix="scientific",
        semantic_errors=semantic_errors,
        globally_available=global_check_availability,
    )

    raw_proof_state = _text(h.get("public_proof_state"), "unproven")
    raw_verdict = _text(h.get("scientific_verdict"), "not_measurable")
    proof_state, verdict, verdict_label, plain_summary = _proof_summary(
        projection_status=projection_status,
        raw_proof_state=raw_proof_state,
        raw_verdict=raw_verdict,
    )
    proof_label = PROOF_LABELS.get(proof_state, "Unproven")
    proof_steps = [
        dict(row)
        for row in _safe_list(f_quantum.get("proof_ladder"))
        if isinstance(row, dict)
    ]
    f_strategy = _safe_dict(f_quantum.get("strategy_influence"))
    f_paper = _safe_dict(f_quantum.get("paper_outcome_lineage"))
    g_integration = _safe_dict(g.get("paper_integration"))
    h_downstream = _safe_dict(h.get("downstream_truth"))
    source_records = _source_artifact_records(sources, integrity_errors)

    payload: dict[str, Any] = {
        "artifact_type": ARTIFACT_TYPE,
        "schema_version": SCHEMA_VERSION,
        "generated_at": generated_at,
        "copy_version": COPY_VERSION,
        "projection_status": projection_status,
        "source_artifacts": source_records,
        "source_lineage": {
            "mode": "verified_content_hashes_and_shared_evidence_identity",
            "source_count": len(source_records),
            "content_hashes_verified": not any(
                error.startswith("source_content_hash_mismatch:")
                for error in integrity_errors
            ),
            "semantic_coherence_passed": coherence_passed,
            "shared_evidence_identity": {
                "shared_manifest_hash": _safe_dict(
                    f_quantum.get("provenance")
                ).get("shared_manifest_hash"),
                "hardware_manifest_hash": _safe_dict(
                    f_quantum.get("provenance")
                ).get("hardware_manifest_hash"),
                "wave_g_cycle_id": g.get("cycle_id"),
                "wave_h_pilot_id": _safe_dict(h.get("pilot_manifest")).get("pilot_id"),
            },
            "integrity_errors": integrity_errors,
            "semantic_errors": semantic_errors,
            "timestamps_used_for_lineage": False,
        },
        "freshness": freshness,
        "page_explainer": {
            "eyebrow": "Quantum Benchmark Framework",
            "title": "Quantum Edge",
            "purpose_paragraph": PURPOSE_PARAGRAPH,
            "read_more_label": "Read more +",
            "read_less_label": "Read less −",
            "guidance": {
                "eyebrow": "Quantum research mandate",
                "introduction": GUIDANCE_INTRODUCTION,
                "workflow_heading": "How the hybrid research loop works",
                "workflow_support": (
                    "Classical and quantum-assisted methods have distinct roles, then "
                    "meet under one validation standard."
                ),
                "workflow_steps": [dict(step) for step in GUIDANCE_WORKFLOW_STEPS],
                "operating_model": dict(GUIDANCE_OPERATING_MODEL),
                "current_capability": _guidance_current_capability(f_quantum),
                "proof_heading": "Six standards of evidence",
                "proof_support": (
                    "The standards are cumulative: passing an earlier stage does not "
                    "satisfy the stages that follow."
                ),
                "questions": list(GUIDANCE_QUESTIONS),
                "proof_steps": [dict(step) for step in GUIDANCE_PROOF_STEPS],
                "outcome_heading": "Permissible research conclusions",
                "outcome_introduction": (
                    "The evidence can support one of five governed conclusions."
                ),
                "possible_outcomes": list(GUIDANCE_OUTCOMES),
                "outcome_states": [dict(state) for state in GUIDANCE_OUTCOME_STATES],
                "takeaway": dict(GUIDANCE_TAKEAWAY),
            },
            "section_order": ["evidence", "consequence", "answer"],
        },
        "answer": {
            "proof_state": proof_state,
            "raw_proof_state": raw_proof_state,
            "proof_state_label": proof_label,
            "scientific_verdict": verdict,
            "raw_scientific_verdict": raw_verdict,
            "scientific_verdict_label": verdict_label,
            "plain_english_summary": plain_summary,
            "proof_ladder": {
                "completed_count": sum(
                    row.get("state") == "complete" for row in proof_steps
                ),
                "step_count": len(proof_steps),
                "steps": proof_steps,
            },
            "engineering_checks": engineering,
            "market_proof_prerequisites": market,
            "current_blockers": [str(row) for row in _safe_list(h.get("blockers"))],
            "next_required_evidence": [
                str(row) for row in _safe_list(h.get("next_actions"))
            ],
        },
        "evidence": {
            "strongest_evidence": _safe_dict(f_quantum.get("strongest_evidence")),
            "experiments": [
                dict(row)
                for row in _safe_list(f_quantum.get("experiments"))
                if isinstance(row, dict)
            ],
            "matched_classical_comparison": _safe_dict(
                f_quantum.get("comparison_summary")
            ),
            "negative_evidence": [
                dict(row)
                for row in _safe_list(f_quantum.get("negative_results"))
                if isinstance(row, dict)
            ],
            "hardware_authenticity": {
                "wave_f_record": _safe_dict(f_quantum.get("hardware_authenticity")),
                "current_hardware_checkpoint": _safe_dict(
                    h.get("hardware_authorization_checkpoint")
                ),
                "engineering_fixture": _safe_dict(h.get("engineering_fixture")),
            },
            "pilot": _safe_dict(h.get("pilot_manifest")),
            "certification": {
                "engineering_checks": engineering,
                "market_proof_prerequisites": market,
                "controls": [
                    dict(row)
                    for row in _safe_list(h.get("controls"))
                    if isinstance(row, dict)
                ],
            },
            "operational_evidence": {
                "wave_g_cycle_id": g.get("cycle_id"),
                "wave_g_status": g.get("status"),
                "wave_g_evidence_date": g.get("evidence_date"),
                "daily_stages": _safe_dict(g.get("daily_stages")),
                "run_ledger": [
                    dict(row)
                    for row in _safe_list(h.get("run_ledger"))
                    if isinstance(row, dict)
                ],
                "evidence_truth": _safe_dict(h.get("evidence_truth")),
            },
            "provenance": {
                "wave_f": _safe_dict(f_quantum.get("provenance")),
                "raw_public_proof_state": raw_proof_state,
                "raw_scientific_verdict": raw_verdict,
                "public_proof_state_label": PROOF_LABELS.get(
                    raw_proof_state,
                    "Unproven",
                ),
                "source_content_hashes": {
                    row["source_id"]: row.get("content_hash") for row in source_records
                },
            },
        },
        "consequence": {
            "strategy_influence": {
                "validated_strategy_count": _safe_int(
                    h_downstream.get("strategy_count")
                ),
                "strategy_family_ids": _safe_list(
                    f_strategy.get("strategy_family_ids")
                ),
                "summary": _text(
                    f_strategy.get("summary"),
                    "No strategy influence has been exported.",
                ),
            },
            "paper_outcome_lineage": {
                "attributed_paper_decision_count": _safe_int(
                    f_paper.get("attributed_paper_decision_count")
                ),
                "mature_postmortem_count": len(_safe_list(g.get("postmortems"))),
                "paper_order_count": _safe_int(h_downstream.get("paper_order_count")),
                "summary": _text(
                    f_paper.get("summary"),
                    "No paper outcome lineage has been exported.",
                ),
            },
            "hybrid_lifecycle": [
                dict(row)
                for row in _safe_list(g.get("public_lifecycle"))
                if isinstance(row, dict)
            ],
            "guarded_route": {
                "route_contract": _safe_dict(g_integration.get("route_contract")),
                "validated_edge_count": _safe_int(
                    h_downstream.get("validated_edge_count")
                ),
                "strategy_count": _safe_int(h_downstream.get("strategy_count")),
                "risk_review_count": _safe_int(
                    h_downstream.get("risk_review_count")
                ),
                "paperops_review_handoff_count": _safe_int(
                    h_downstream.get("paperops_review_handoff_count")
                ),
                "paper_order_count": _safe_int(
                    h_downstream.get("paper_order_count")
                ),
                "broker_write_count": _safe_int(
                    h_downstream.get("broker_write_count")
                ),
                "why_not": _safe_dict(g_integration.get("why_not")),
            },
            "daily_explanation_preview": _safe_dict(g.get("telegram_brief")),
        },
        "plain_english_help": {},
        "boundary": (
            "This page explains public research evidence. It cannot run research, call a "
            "provider, submit hardware, create or mutate a pattern or strategy, approve risk "
            "or execution, create a PaperOps handoff or order, write to a broker, award proof "
            "credit, send a Telegram message, accept a command, deploy code, or create "
            "live-capital authority."
        ),
        "authority": _authority(),
    }
    payload["plain_english_help"] = _plain_english_help(
        projection_status=projection_status,
        proof_label=proof_label,
        engineering=engineering,
        market=market,
        h=h,
    )
    payload["content_hash"] = stable_hash(_canonical_material(payload))
    errors = validate_quantum_edge_page_view_model(payload)
    if errors:
        raise ValueError(";".join(errors))
    return payload


def build_quantum_edge_page_view_model(
    runtime_dir: str | Path,
    *,
    generated_at: str | None = None,
) -> dict[str, Any]:
    sources = load_quantum_edge_sources(runtime_dir)
    return build_quantum_edge_page_view_model_from_sources(
        sources,
        generated_at=generated_at or datetime.now(timezone.utc).isoformat(),
    )


def validate_quantum_edge_page_view_model(payload: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if payload.get("schema_version") != SCHEMA_VERSION:
        errors.append("quantum_edge_page_schema_invalid")
    if payload.get("artifact_type") != ARTIFACT_TYPE:
        errors.append("quantum_edge_page_artifact_type_invalid")
    if payload.get("copy_version") != COPY_VERSION:
        errors.append("quantum_edge_page_copy_version_invalid")
    if payload.get("projection_status") not in {
        "ready",
        "source_unavailable",
        "source_truth_conflict",
        "source_stale",
    }:
        errors.append("quantum_edge_page_projection_status_invalid")
    source_records = _safe_list(payload.get("source_artifacts"))
    if [row.get("source_id") for row in source_records if isinstance(row, dict)] != list(
        SOURCE_SPECS
    ):
        errors.append("quantum_edge_page_source_lineage_invalid")
    for row in source_records:
        if not isinstance(row, dict):
            errors.append("quantum_edge_page_source_record_invalid")
            continue
        content_hash = _text(row.get("content_hash"))
        if content_hash and not re.fullmatch(r"[0-9a-f]{64}", content_hash):
            errors.append(f"quantum_edge_page_source_hash_invalid:{row.get('source_id')}")

    explainer = _safe_dict(payload.get("page_explainer"))
    if explainer.get("eyebrow") != "Quantum Benchmark Framework":
        errors.append("quantum_edge_page_eyebrow_changed")
    if explainer.get("purpose_paragraph") != PURPOSE_PARAGRAPH:
        errors.append("quantum_edge_page_purpose_copy_changed")
    guidance = _safe_dict(explainer.get("guidance"))
    if guidance.get("workflow_steps") != GUIDANCE_WORKFLOW_STEPS:
        errors.append("quantum_edge_page_guidance_workflow_steps_changed")
    if guidance.get("operating_model") != GUIDANCE_OPERATING_MODEL:
        errors.append("quantum_edge_page_guidance_operating_model_changed")
    current_capability = _safe_dict(guidance.get("current_capability"))
    if current_capability.get("label") != "Current capability":
        errors.append("quantum_edge_page_guidance_current_capability_invalid")
    for key in (
        "local_simulation_reproduced",
        "provider_accessible",
        "hardware_authorized",
        "hardware_submitted",
        "hardware_completed",
    ):
        if not isinstance(current_capability.get(key), bool):
            errors.append(f"quantum_edge_page_guidance_current_capability_invalid:{key}")
    if guidance.get("questions") != GUIDANCE_QUESTIONS:
        errors.append("quantum_edge_page_guidance_questions_changed")
    if guidance.get("proof_steps") != GUIDANCE_PROOF_STEPS:
        errors.append("quantum_edge_page_guidance_proof_steps_changed")
    if guidance.get("possible_outcomes") != GUIDANCE_OUTCOMES:
        errors.append("quantum_edge_page_guidance_outcomes_changed")
    if guidance.get("outcome_states") != GUIDANCE_OUTCOME_STATES:
        errors.append("quantum_edge_page_guidance_outcome_states_changed")
    if guidance.get("takeaway") != GUIDANCE_TAKEAWAY:
        errors.append("quantum_edge_page_guidance_takeaway_changed")
    if explainer.get("section_order") != ["evidence", "consequence", "answer"]:
        errors.append("quantum_edge_page_section_order_changed")

    answer = _safe_dict(payload.get("answer"))
    ladder = _safe_dict(answer.get("proof_ladder"))
    if ladder.get("step_count") != 6 or len(_safe_list(ladder.get("steps"))) != 6:
        errors.append("quantum_edge_page_proof_ladder_invalid")
    engineering = _safe_dict(answer.get("engineering_checks"))
    market = _safe_dict(answer.get("market_proof_prerequisites"))
    for label, summary in (("engineering", engineering), ("market", market)):
        rows = _safe_list(summary.get("checks"))
        if summary.get("check_count") != len(rows):
            errors.append(f"quantum_edge_page_{label}_count_invalid")
        if summary.get("available") is True:
            expected = sum(
                isinstance(row, dict) and row.get("passed") is True for row in rows
            )
            if summary.get("pass_count") != expected:
                errors.append(f"quantum_edge_page_{label}_pass_count_invalid")
        elif summary.get("pass_count") is not None:
            errors.append(f"quantum_edge_page_{label}_unavailable_numerator_exposed")
        for check_error in _check_contradiction_errors(
            [row for row in rows if isinstance(row, dict) and row.get("passed") is not None],
            group=f"projected_{label}_checks",
        ):
            errors.append(check_error)

    projection_status = payload.get("projection_status")
    if projection_status != "ready":
        if answer.get("proof_state") != "unproven":
            errors.append("quantum_edge_page_fail_closed_proof_state_invalid")
        if answer.get("scientific_verdict") != "unavailable":
            errors.append("quantum_edge_page_fail_closed_verdict_invalid")
    raw_state = answer.get("raw_proof_state")
    expected_label = PROOF_LABELS.get(_text(raw_state), "Unproven")
    provenance = _safe_dict(_safe_dict(payload.get("evidence")).get("provenance"))
    if provenance.get("public_proof_state_label") != expected_label:
        errors.append("quantum_edge_page_public_proof_label_invalid")
    if raw_state == "classically_dominated" and expected_label != "Classical preferred":
        errors.append("quantum_edge_page_classical_preferred_mapping_invalid")

    consequence = _safe_dict(payload.get("consequence"))
    guarded_route = _safe_dict(consequence.get("guarded_route"))
    route_contract = _safe_dict(guarded_route.get("route_contract"))
    if route_contract and route_contract.get("wave_g_calls_broker") is not False:
        errors.append("quantum_edge_page_broker_boundary_invalid")
    brief = _safe_dict(consequence.get("daily_explanation_preview"))
    if brief and (
        brief.get("telegram_send_allowed") is not False
        or brief.get("telegram_command_authority") is not False
    ):
        errors.append("quantum_edge_page_telegram_boundary_invalid")
    authority = _safe_dict(payload.get("authority"))
    for field in ZERO_AUTHORITY_FIELDS:
        if authority.get(field) is not False:
            errors.append(f"quantum_edge_page_authority_escalated:{field}")
    if any(value is True for value in authority.values()):
        errors.append("quantum_edge_page_unknown_authority_escalated")
    errors.extend(
        f"quantum_edge_page_{error}" for error in _public_safety_errors(payload)
    )
    expected_hash = stable_hash(_canonical_material(payload))
    if payload.get("content_hash") != expected_hash:
        errors.append("quantum_edge_page_content_hash_mismatch")
    return sorted(set(errors))


def _write_json_atomic(path: Path, payload: dict[str, Any]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    temporary.replace(path)
    return path


def write_quantum_edge_page_view_model(
    payload: dict[str, Any],
    *,
    runtime_dir: str | Path,
    site_root: str | Path | None = None,
) -> dict[str, Path]:
    errors = validate_quantum_edge_page_view_model(payload)
    if errors:
        raise ValueError(";".join(errors))
    outputs = {
        "runtime": _write_json_atomic(Path(runtime_dir) / ARTIFACT_NAME, payload),
    }
    if site_root is not None:
        outputs["site"] = _write_json_atomic(
            Path(site_root) / "status" / SITE_ARTIFACT_NAME,
            payload,
        )
    for path in outputs.values():
        written = _read_json(path)
        if written != payload or written.get("content_hash") != payload.get("content_hash"):
            raise ValueError(f"quantum_edge_page_mirror_verification_failed:{path.name}")
    return outputs
