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
COPY_VERSION = "quantum-edge-elegant-simplification-v1"
PRESENTATION_CONTRACT_VERSION = "quantum-edge-elegant-v1"
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
            "Distinguishes a real quantum-hardware job from a local simulation or a prepared test."
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
            "The more demanding test reduces confidence in the relationship Qadam originally found."
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
    "label": "Research reminder",
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

PAGE_COPY = {
    "eyebrow": "Quantum Benchmark Framework",
    "title": "Quantum Edge",
    "subtitle": PURPOSE_PARAGRAPH,
    "conclusion_label": "Current conclusion",
}

PRESENTATION_SECTIONS = {
    "evidence": {
        "sequence": "01",
        "eyebrow": "Experiment & Evidence",
        "title": "What was run, what was compared, and what was verified?",
    },
    "consequence": {
        "sequence": "02",
        "eyebrow": "Strategy & Paper Impact",
        "title": "Did this change a validated strategy or paper decision?",
    },
    "answer": {
        "sequence": "03",
        "eyebrow": "Quantum Edge Verdict",
        "title": "Has a genuine market-level quantum advantage been proven?",
    },
}

PRESENTATION_GATES = (
    ("experiment_works", "Does the experiment work?"),
    ("hardware_evidence_exists", "Does hardware evidence exist?"),
    ("market_comparison_holds_up", "Does the market comparison hold up?"),
    (
        "downstream_decision_improved",
        "Did it improve a strategy or paper decision?",
    ),
)

GATE_STATE_LABELS = {
    "passed": "Passed",
    "waiting": "Waiting",
    "not_run": "Not run",
    "failed": "Failed",
    "unavailable": "Unavailable",
}

TECHNICAL_RECORD_INDEX = (
    ("proof_ladder", "Six-step proof ladder", "answer.proof_ladder"),
    ("engineering_checks", "Engineering checks", "answer.engineering_checks"),
    ("market_checks", "Market-proof checks", "answer.market_proof_prerequisites"),
    ("experiments", "Experiment record", "evidence.experiments"),
    ("matched_comparison", "Matched comparison", "evidence.matched_classical_comparison"),
    ("negative_evidence", "Negative evidence", "evidence.negative_evidence"),
    ("hardware", "Hardware authenticity", "evidence.hardware_authenticity"),
    ("pilot", "Pilot specification", "evidence.pilot"),
    ("certification", "Certification controls", "evidence.certification"),
    ("operations", "Operational evidence", "evidence.operational_evidence"),
    ("provenance", "Evidence provenance", "evidence.provenance"),
    ("lifecycle", "Hybrid lifecycle", "consequence.hybrid_lifecycle"),
    ("route", "Governed downstream route", "consequence.guarded_route"),
    ("strategy", "Strategy influence", "consequence.strategy_influence"),
    ("paper", "Paper-outcome lineage", "consequence.paper_outcome_lineage"),
    ("sources", "Source artifacts", "source_artifacts"),
    ("freshness", "Freshness record", "freshness"),
)

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
    experiments = [row for row in _safe_list(f_quantum.get("experiments")) if isinstance(row, dict)]
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
        if key not in {"generated_at", "content_hash", "render_contract_hash"}
    }


def _render_contract_material(payload: dict[str, Any]) -> dict[str, Any]:
    """Return the JSON-native, browser-verifiable page truth contract."""

    source_hashes = {
        _text(row.get("source_id")): _text(row.get("content_hash"))
        for row in _safe_list(payload.get("source_artifacts"))
        if isinstance(row, dict) and _text(row.get("source_id"))
    }
    return {
        "content_hash": payload.get("content_hash"),
        "schema_version": payload.get("schema_version"),
        "contract_version": payload.get("contract_version"),
        "projection_status": payload.get("projection_status"),
        "page_copy": payload.get("page_copy"),
        "state_axes": payload.get("state_axes"),
        "presentation": payload.get("presentation"),
        "source_content_hashes": source_hashes,
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
                        errors.append(f"authority_escalated:{child_path}.{authority_key}")
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
            errors.append(f"semantic_contradiction:{group}:{key}:passed_vs_explanation")
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
        row.get("key") for row in _safe_list(f_quantum.get("proof_ladder")) if isinstance(row, dict)
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
        if (
            _safe_dict(f_quantum.get("hardware_authenticity")).get("ibm_instance_accessible")
            is not True
        ):
            errors.append("provider_readiness_conflict:wave_f_hardware_authenticity")
        if provider_step.get("state") != "complete":
            errors.append("provider_readiness_conflict:wave_f_proof_ladder")
        if provider_access_blocked_recorded:
            errors.append("provider_readiness_conflict:wave_f_negative_evidence")

    f_hardware = _safe_dict(f_quantum.get("hardware_authenticity"))
    hardware_pairs = {
        "hardware_authorized": (
            f_hardware.get("hardware_execution_authorized") is True,
            h_hardware.get("authorized") is True,
        ),
        "hardware_submitted": (
            f_hardware.get("hardware_job_submitted") is True,
            h_fixture.get("hardware_job_submitted") is True,
        ),
        "hardware_completed": (
            f_hardware.get("hardware_experiment_completed") is True,
            h_fixture.get("hardware_experiment_completed") is True,
        ),
    }
    for state_key, pair in hardware_pairs.items():
        if pair[0] is not pair[1]:
            errors.append(f"hardware_state_conflict:{state_key}")
    if (
        f_hardware.get("hardware_receipt_verified") is True
        and f_hardware.get("hardware_experiment_completed") is not True
    ):
        errors.append("hardware_receipt_without_completed_experiment")
    hardware_result_check = next(
        (
            row
            for row in _safe_list(h_certification.get("scientific_checks"))
            if isinstance(row, dict) and row.get("key") == "ibm_hardware_result"
        ),
        {},
    )
    if hardware_result_check.get("passed") is True and not (
        f_hardware.get("hardware_experiment_completed") is True
        and f_hardware.get("hardware_receipt_verified") is True
    ):
        errors.append("hardware_check_passed_without_verified_receipt")

    lifecycle_states = [
        row.get("state") for row in _safe_list(g.get("public_lifecycle")) if isinstance(row, dict)
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
        actual_passes = sum(isinstance(row, dict) and row.get("passed") is True for row in checks)
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
    errors.extend(_matching_nonempty(shared_manifest_values, key="shared_manifest_hash"))
    hardware_manifest_values = [
        _safe_dict(f_quantum.get("hardware_authenticity")).get("prepared_manifest_hash"),
        _safe_dict(g_stages.get("hardware_experiment_preparation")).get("prepared_manifest_hash"),
        h_fixture.get("hardware_smoke_manifest_hash"),
        h_hardware.get("engineering_manifest_hash"),
        h_pilot.get("engineering_smoke_manifest_hash"),
    ]
    errors.extend(_matching_nonempty(hardware_manifest_values, key="hardware_manifest_hash"))

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
        isinstance(row, dict) and row.get("passed") is True for row in engineering_checks
    )
    scientific_from_checks = bool(scientific_checks) and all(
        isinstance(row, dict) and row.get("passed") is True for row in scientific_checks
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
                "content_hash_verified": bool(source)
                and not any(error.endswith(f":{source_id}") for error in integrity_errors),
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
            if value is not None and (generated - value).total_seconds() > STALE_AFTER_SECONDS
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
    rows = [row for row in _safe_list(certification.get(source_group)) if isinstance(row, dict)]
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


def _comparison_eligibility(payload: dict[str, Any]) -> list[dict[str, Any]]:
    """Return the eight fair-comparison requirements from existing audit facts."""

    ready = payload.get("projection_status") == "ready"
    evidence = _safe_dict(payload.get("evidence"))
    operational = _safe_dict(evidence.get("operational_evidence"))
    evidence_truth = _safe_dict(operational.get("evidence_truth"))
    pilot = _safe_dict(evidence.get("pilot"))
    provenance = _safe_dict(evidence.get("provenance"))
    wave_f_provenance = _safe_dict(provenance.get("wave_f"))
    matched_methods = _safe_dict(pilot.get("matched_methods"))
    chronology = _safe_dict(pilot.get("chronology"))
    policy = _safe_dict(pilot.get("policy"))
    point_features = _safe_list(pilot.get("point_in_time_features"))
    controls = [str(value).lower() for value in _safe_list(pilot.get("controls"))]
    feature_stage = _safe_dict(operational.get("daily_stages")).get("feature_construction")
    feature_stage = _safe_dict(feature_stage)
    evaluation_policy_hash = _text(wave_f_provenance.get("evaluation_policy_hash"))

    checks = (
        (
            "same_frozen_manifest_and_features",
            "Same frozen manifest and features",
            bool(wave_f_provenance.get("shared_manifest_hash")) and bool(point_features),
            "Both lanes must use the same frozen evidence manifest and feature definitions.",
            [
                "evidence.provenance.wave_f.shared_manifest_hash",
                "evidence.pilot.point_in_time_features",
            ],
        ),
        (
            "same_target_outcome_and_horizon",
            "Same target, outcome, and horizon",
            bool(_text(pilot.get("research_question"))) and bool(_safe_list(pilot.get("outcomes"))),
            "Both lanes must predict the same pre-declared outcomes over the same horizons.",
            ["evidence.pilot.research_question", "evidence.pilot.outcomes"],
        ),
        (
            "same_chronological_split",
            "Same chronological train, calibration, and holdout split",
            bool(_text(chronology.get("training")))
            and bool(_text(chronology.get("validation")))
            and bool(_text(chronology.get("untouched_holdout")))
            and _safe_int(evidence_truth.get("eligible_window_count")) > 0,
            "Both lanes must share one eligible chronological development and untouched-holdout split.",
            [
                "evidence.pilot.chronology.training",
                "evidence.pilot.chronology.validation",
                "evidence.pilot.chronology.untouched_holdout",
                "evidence.operational_evidence.evidence_truth.eligible_window_count",
            ],
        ),
        (
            "point_in_time_preprocessing_and_leakage",
            "Point-in-time preprocessing and leakage controls",
            feature_stage.get("point_in_time_checks_passed") is True
            and bool(point_features)
            and evidence_truth.get("leakage_violation_count") == 0,
            "All preprocessing must be point-in-time and free of recorded label leakage.",
            [
                "/evidence/operational_evidence/daily_stages/feature_construction/point_in_time_checks_passed",
                "evidence.pilot.point_in_time_features",
                "evidence.operational_evidence.evidence_truth.leakage_violation_count",
            ],
        ),
        (
            "same_metric_cost_and_statistical_rule",
            "Same metric, costs, and statistical rule",
            bool(_text(pilot.get("evaluation_metric")))
            and policy.get("false_discovery_rate_alpha") is not None
            and policy.get("transaction_cost_bps") is not None
            and bool(_text(policy.get("statistical_rule"))),
            "Both lanes must be scored under one frozen metric, cost, and statistical policy.",
            ["evidence.pilot.evaluation_metric", "evidence.pilot.policy"],
        ),
        (
            "comparable_frozen_tuning_budget",
            "Comparable frozen tuning and model-selection budget",
            policy.get("comparable_tuning_budget") is not None
            and bool(_safe_list(matched_methods.get("classical")))
            and bool(_safe_list(matched_methods.get("quantum"))),
            "A public fact must confirm that neither lane received a looser tuning budget.",
            ["evidence.pilot.policy.comparable_tuning_budget", "evidence.pilot.matched_methods"],
        ),
        (
            "same_negative_multiple_testing_and_minimum_evidence_controls",
            "Same negative, multiple-testing, and minimum-evidence controls",
            any("placebo" in value or "negative" in value for value in controls)
            and any("multiple" in value for value in controls)
            and policy.get("minimum_holdout_observations") is not None,
            "Both lanes must face the same negative controls, multiple-testing correction, and evidence minimum.",
            ["evidence.pilot.controls", "evidence.pilot.policy.minimum_holdout_observations"],
        ),
        (
            "reproducible_provenance",
            "Reproducible provenance",
            bool(_text(pilot.get("manifest_hash")))
            and bool(evaluation_policy_hash)
            and bool(wave_f_provenance.get("shared_manifest_hash")),
            "The manifest, evaluation policy, and shared evidence identity must be reproducible.",
            [
                "evidence.pilot.manifest_hash",
                "evidence.provenance.wave_f.evaluation_policy_hash",
                "evidence.provenance.wave_f.shared_manifest_hash",
            ],
        ),
    )
    return [
        {
            "key": key,
            "label": label,
            "passed": passed if ready else None,
            "summary": summary,
            "fact_refs": fact_refs,
        }
        for key, label, passed, summary, fact_refs in checks
    ]


def _comparison_axis(payload: dict[str, Any]) -> dict[str, Any]:
    evidence = _safe_dict(payload.get("evidence"))
    comparison = _safe_dict(evidence.get("matched_classical_comparison"))
    checks = _comparison_eligibility(payload)
    eligible = bool(checks) and all(row.get("passed") is True for row in checks)
    if payload.get("projection_status") != "ready":
        key = "unavailable"
        label = "Comparison unavailable"
        outcome_label = label
        summary = "Qadam cannot compare the methods until the public evidence records agree."
    elif not eligible:
        key = "not_measurable"
        label = "Not measurable yet"
        outcome_label = "No fair market-data winner yet"
        summary = _text(
            comparison.get("plain_english_summary"),
            "A fair comparison on the same untouched market evidence has not run yet.",
        )
    elif comparison.get("empirical_claim_allowed") is not True:
        key = "not_measurable"
        label = "Not measurable yet"
        outcome_label = "No fair market-data winner yet"
        summary = (
            "The comparison protocol is eligible, but the canonical comparison record "
            "does not permit an empirical winner claim."
        )
    elif _text(comparison.get("verdict")) in {
        "classical_preferred",
        "classically_dominated",
    }:
        key = "classical_preferred"
        label = "Classical preferred"
        outcome_label = label
        summary = "The conventional method matched or beat the quantum-assisted method."
    elif _text(comparison.get("verdict")) in {
        "joint_corroboration",
        "tie",
        "tied",
    }:
        key = "tied"
        label = "Tied"
        outcome_label = "Methods tied"
        summary = "The two methods performed equivalently under the frozen comparison."
    elif _text(comparison.get("verdict")) in {
        "quantum_positive",
        "quantum_strengthened",
        "validated",
    }:
        key = "quantum_positive"
        label = "Quantum positive"
        outcome_label = "Quantum contribution positive"
        summary = "The quantum-assisted method added information under the frozen comparison."
    else:
        key = "not_measurable"
        label = "Not measurable yet"
        outcome_label = "No fair market-data winner yet"
        summary = _text(
            comparison.get("plain_english_summary"),
            "The eligible comparison did not establish a measurable outcome.",
        )
    return {
        "key": key,
        "label": label,
        "outcome_label": outcome_label,
        "summary": summary,
        "eligible": eligible,
        "eligibility_checks": checks,
        "fact_refs": [
            "evidence.matched_classical_comparison",
            "evidence.pilot",
            "evidence.operational_evidence.evidence_truth",
        ],
    }


def _execution_axis(payload: dict[str, Any]) -> dict[str, Any]:
    if payload.get("projection_status") not in {"ready", "source_stale"}:
        return {
            "key": "unavailable",
            "label": "Execution evidence unavailable",
            "summary": "Execution state is withheld until the public source records agree.",
            "execution_mode": "unavailable",
            "local_simulation_reproduced": None,
            "provider_accessible": None,
            "hardware_authorized": None,
            "hardware_submitted": None,
            "hardware_completed": None,
            "hardware_receipt_verified": None,
            "fact_refs": ["evidence.hardware_authenticity"],
        }
    evidence = _safe_dict(payload.get("evidence"))
    hardware = _safe_dict(evidence.get("hardware_authenticity"))
    wave_f = _safe_dict(hardware.get("wave_f_record"))
    experiments = [row for row in _safe_list(evidence.get("experiments")) if isinstance(row, dict)]
    local_reproduced = any(
        "simulat" in _text(row.get("kind")).lower()
        and _text(row.get("state")).lower() in POSITIVE_CHECK_STATUSES
        for row in experiments
    )
    provider = wave_f.get("ibm_instance_accessible") is True
    authorized = wave_f.get("hardware_execution_authorized") is True
    submitted = wave_f.get("hardware_job_submitted") is True
    completed = wave_f.get("hardware_experiment_completed") is True
    receipt = wave_f.get("hardware_receipt_verified") is True
    if completed and receipt:
        key, label, mode = "hardware_verified", "IBM hardware result verified", "ibm_hardware"
        summary = "A completed IBM hardware result and its sanitized receipt are recorded."
    elif completed:
        key, label, mode = (
            "hardware_unverified",
            "IBM hardware result awaiting verification",
            "ibm_hardware",
        )
        summary = "Hardware execution is recorded, but its public receipt is not verified."
    elif submitted:
        key, label, mode = "hardware_pending", "IBM hardware result pending", "hardware_pending"
        summary = "A hardware job was submitted, but no completed result is available."
    elif authorized:
        key, label, mode = (
            "hardware_authorized",
            "IBM hardware authorized—not run",
            "hardware_authorized",
        )
        summary = "The exact experiment is authorized but has not been submitted."
    elif provider:
        key, label = "provider_ready_hardware_not_run", "Provider ready; hardware not run"
        mode = "local_simulator" if local_reproduced else "not_run"
        summary = "The provider path is ready, but no IBM hardware experiment has run."
    elif local_reproduced:
        key, label, mode = "local_simulation_only", "Local simulation only", "local_simulator"
        summary = "The local experiment reproduced; provider-backed hardware has not run."
    else:
        key, label, mode = "not_run", "No experiment result", "not_run"
        summary = "Neither a reproducible local result nor a hardware result is available."
    return {
        "key": key,
        "label": label,
        "summary": summary,
        "execution_mode": mode,
        "local_simulation_reproduced": local_reproduced,
        "provider_accessible": provider,
        "hardware_authorized": authorized,
        "hardware_submitted": submitted,
        "hardware_completed": completed,
        "hardware_receipt_verified": receipt,
        "fact_refs": ["evidence.experiments", "evidence.hardware_authenticity"],
    }


def _downstream_axis(payload: dict[str, Any]) -> dict[str, Any]:
    if payload.get("projection_status") not in {"ready", "source_stale"}:
        return {
            "key": "unavailable",
            "label": "Downstream impact unavailable",
            "summary": "Strategy and paper impact are withheld until source records agree.",
            "strategy_count": None,
            "paper_decision_count": None,
            "fact_refs": [
                "consequence.strategy_influence",
                "consequence.paper_outcome_lineage",
            ],
        }
    consequence = _safe_dict(payload.get("consequence"))
    strategy = _safe_dict(consequence.get("strategy_influence"))
    paper = _safe_dict(consequence.get("paper_outcome_lineage"))
    strategy_count = _safe_int(strategy.get("validated_strategy_count"))
    paper_count = _safe_int(paper.get("attributed_paper_decision_count"))
    if paper_count > 0:
        key, label = "paper_decision_influenced", "Paper decision influenced"
    elif strategy_count > 0:
        key, label = "strategy_changed", "Validated strategy changed"
    else:
        key, label = "no_downstream_change", "No downstream change"
    if strategy_count == 0 and paper_count == 0:
        summary = (
            "No validated strategy or governed paper decision has changed because "
            "of quantum evidence."
        )
    elif paper_count > 0:
        summary = "Validated quantum evidence influenced a governed paper decision."
    else:
        summary = (
            "Validated quantum evidence changed a strategy; no paper decision is attributed yet."
        )
    return {
        "key": key,
        "label": label,
        "summary": summary,
        "strategy_count": strategy_count,
        "paper_decision_count": paper_count,
        "fact_refs": [
            "consequence.strategy_influence.validated_strategy_count",
            "consequence.paper_outcome_lineage.attributed_paper_decision_count",
        ],
    }


def _freshness_axis(payload: dict[str, Any]) -> dict[str, Any]:
    freshness = _safe_dict(payload.get("freshness"))
    projection_status = _text(payload.get("projection_status"), "source_unavailable")
    raw_proof_state = _text(_safe_dict(payload.get("answer")).get("raw_proof_state"))
    if projection_status == "source_truth_conflict":
        key, label, summary = (
            "contradictory",
            "Evidence contradictory",
            "The public source records disagree, so no current claim is permitted.",
        )
    elif projection_status == "source_unavailable":
        key, label, summary = (
            "unavailable",
            "Freshness unavailable",
            "Required public source records are unavailable.",
        )
    elif raw_proof_state == "decayed":
        key, label, summary = (
            "decayed",
            "Evidence no longer current",
            "Previously supported evidence no longer meets the current stability contract.",
        )
    elif projection_status == "source_stale":
        key, label, summary = (
            "stale",
            "Evidence stale",
            "One or more required evidence records are outside the freshness window.",
        )
    elif freshness.get("status") == "fresh":
        key, label, summary = (
            "current",
            "Evidence current",
            "All required public evidence records are within the freshness window.",
        )
    else:
        key, label, summary = (
            "unavailable",
            "Freshness unavailable",
            "Freshness is not asserted while source truth is incomplete or contradictory.",
        )
    return {
        "key": key,
        "label": label,
        "summary": summary,
        "as_of": freshness.get("newest_source_generated_at"),
        "oldest_source_generated_at": freshness.get("oldest_source_generated_at"),
        "source_content_hashes": {
            _text(row.get("source_id")): row.get("content_hash")
            for row in _safe_list(payload.get("source_artifacts"))
            if isinstance(row, dict) and _text(row.get("source_id"))
        },
        "current_claim_allowed": key == "current",
        "fact_refs": ["freshness"],
    }


def _proof_axis(payload: dict[str, Any]) -> dict[str, Any]:
    answer = _safe_dict(payload.get("answer"))
    raw_state = _text(answer.get("raw_proof_state"), "unproven")
    historical_state = _text(answer.get("historical_proof_state"))
    candidate = historical_state if raw_state == "decayed" else raw_state
    state = candidate if candidate in {"unproven", "provisional", "validated"} else "unproven"
    return {
        "key": state,
        "label": PROOF_LABELS[state],
        "fact_refs": [
            "answer.raw_proof_state",
            "answer.historical_proof_state",
        ],
    }


def _state_axes(payload: dict[str, Any]) -> dict[str, Any]:
    return {
        "proof": _proof_axis(payload),
        "comparison": _comparison_axis(payload),
        "execution": _execution_axis(payload),
        "downstream": _downstream_axis(payload),
        "freshness": _freshness_axis(payload),
    }


def _gate(
    key: str,
    state: str,
    summary: str,
    fact_refs: list[str],
) -> dict[str, Any]:
    labels = dict(PRESENTATION_GATES)
    return {
        "key": key,
        "label": labels[key],
        "state": state,
        "state_label": GATE_STATE_LABELS[state],
        "summary": summary,
        "fact_refs": fact_refs,
    }


def _presentation_gates(
    payload: dict[str, Any],
    axes: dict[str, Any],
) -> list[dict[str, Any]]:
    if payload.get("projection_status") != "ready":
        return [
            _gate(
                key,
                "unavailable",
                "This gate is unavailable until the public source records agree.",
                ["projection_status", "source_lineage"],
            )
            for key, _ in PRESENTATION_GATES
        ]

    answer = _safe_dict(payload.get("answer"))
    engineering = _safe_dict(answer.get("engineering_checks"))
    rows = [row for row in _safe_list(engineering.get("checks")) if isinstance(row, dict)]
    engineering_complete = (
        engineering.get("available") is True
        and _safe_int(engineering.get("check_count")) > 0
        and engineering.get("pass_count") == engineering.get("check_count")
    )
    engineering_failed = any(
        _text(row.get("status")).lower() in {"failed", "failed_safely"} for row in rows
    )
    if engineering_complete:
        experiment_state = "passed"
        experiment_summary = "The frozen experimental mechanism reproduced successfully."
    elif engineering_failed:
        experiment_state = "failed"
        experiment_summary = "One or more engineering controls ran and failed."
    elif rows:
        experiment_state = "waiting"
        experiment_summary = "The engineering control set is not complete."
    else:
        experiment_state = "not_run"
        experiment_summary = "No engineering-control result is recorded."

    execution = _safe_dict(axes.get("execution"))
    if (
        execution.get("hardware_completed") is True
        and execution.get("hardware_receipt_verified") is True
    ):
        hardware_state = "passed"
        hardware_summary = "A completed IBM hardware result and verified receipt exist."
    elif execution.get("hardware_submitted") is True:
        hardware_state = "waiting"
        hardware_summary = "The hardware job is submitted and awaiting a completed result."
    elif execution.get("hardware_authorized") is True:
        hardware_state = "not_run"
        hardware_summary = "The exact hardware experiment is authorized but not submitted."
    else:
        hardware_state = "not_run"
        hardware_summary = "No authorized IBM hardware experiment has run."

    comparison = _safe_dict(axes.get("comparison"))
    freshness = _safe_dict(axes.get("freshness"))
    if freshness.get("key") == "decayed":
        comparison_state = "failed"
        comparison_summary = (
            "The historical comparison no longer meets the current stability contract."
        )
    elif comparison.get("eligible") is not True:
        comparison_state = "not_run"
        comparison_summary = "A fair untouched-market comparison is not yet eligible to run."
    elif comparison.get("key") in {
        "tied",
        "classical_preferred",
        "quantum_positive",
    }:
        comparison_state = "passed"
        comparison_summary = "The governed matched comparison produced a valid conclusion."
    else:
        comparison_state = "waiting"
        comparison_summary = "The eligible comparison has not established a final conclusion."

    downstream = _safe_dict(axes.get("downstream"))
    downstream_count = _safe_int(downstream.get("strategy_count")) + _safe_int(
        downstream.get("paper_decision_count")
    )
    if downstream_count > 0 and comparison_state == "passed":
        downstream_state = "passed"
        downstream_summary = "Validated evidence changed a governed strategy or paper decision."
    elif downstream_count > 0:
        downstream_state = "unavailable"
        downstream_summary = "Downstream activity conflicts with the comparison state."
    else:
        downstream_state = "waiting"
        downstream_summary = "No governed strategy or paper decision has changed."

    return [
        _gate(
            "experiment_works",
            experiment_state,
            experiment_summary,
            ["answer.engineering_checks"],
        ),
        _gate(
            "hardware_evidence_exists",
            hardware_state,
            hardware_summary,
            ["evidence.hardware_authenticity"],
        ),
        _gate(
            "market_comparison_holds_up",
            comparison_state,
            comparison_summary,
            ["state_axes.comparison", "answer.market_proof_prerequisites"],
        ),
        _gate(
            "downstream_decision_improved",
            downstream_state,
            downstream_summary,
            ["state_axes.downstream"],
        ),
    ]


def _build_presentation(
    payload: dict[str, Any],
    axes: dict[str, Any],
) -> dict[str, Any]:
    ready = payload.get("projection_status") == "ready"
    answer = _safe_dict(payload.get("answer"))
    evidence = _safe_dict(payload.get("evidence"))
    operational = _safe_dict(evidence.get("operational_evidence"))
    daily_stages = _safe_dict(operational.get("daily_stages"))
    classical_stage = _safe_dict(daily_stages.get("classical_discovery"))
    shared_manifest = _text(
        _safe_dict(_safe_dict(evidence.get("provenance")).get("wave_f")).get("shared_manifest_hash")
    )
    comparison = _safe_dict(axes.get("comparison"))
    execution = _safe_dict(axes.get("execution"))
    downstream = _safe_dict(axes.get("downstream"))
    proof = _safe_dict(axes.get("proof"))
    freshness = _safe_dict(axes.get("freshness"))
    engineering = _safe_dict(answer.get("engineering_checks"))

    shared_basis = {
        "label": "Same frozen evidence",
        "state": "verified" if ready and shared_manifest else "unavailable",
        "state_label": "Evidence identity verified" if ready and shared_manifest else "Unavailable",
        "summary": (
            "Both lanes received the same content-addressed, label-blind evidence basis."
            if ready and shared_manifest
            else "The shared evidence basis is unavailable until source records agree."
        ),
        "fact_refs": [
            "evidence.provenance.wave_f.shared_manifest_hash",
        ],
    }
    classical_reproduced = ready and "reproduced" in _text(classical_stage.get("state")).lower()
    conventional_lane = {
        "label": "Classical benchmark",
        "state": "reproduced"
        if classical_reproduced
        else "unavailable"
        if not ready
        else "not_run",
        "state_label": "Reproduced locally"
        if classical_reproduced
        else "Unavailable"
        if not ready
        else "Not run",
        "summary": (
            "Conventional methods reproduced the engineering control on the frozen evidence."
            if classical_reproduced
            else "No reproducible conventional benchmark is currently available."
        ),
        "reproducibility_label": "Reproduced locally"
        if classical_reproduced
        else "Not established",
        "holdout_label": "Eligible" if comparison.get("eligible") else "Not yet eligible",
        "details": [
            {
                "key": "environment",
                "label": "Run environment",
                "value": "Local Python research runtime",
            },
            {
                "key": "result",
                "label": "Current result",
                "value": (
                    "Engineering control reproduced locally"
                    if classical_reproduced
                    else "No reproducible result yet"
                ),
            },
            {
                "key": "market_test",
                "label": "Untouched market test",
                "value": "Eligible" if comparison.get("eligible") else "Not yet eligible",
            },
            {
                "key": "limitation",
                "label": "Main limitation",
                "value": (
                    "No untouched market comparison yet"
                    if comparison.get("eligible") is not True
                    else "No material limitation reported"
                ),
            },
        ],
        "fact_refs": [
            "evidence.operational_evidence.daily_stages.classical_discovery",
        ],
    }
    local_reproduced = execution.get("local_simulation_reproduced") is True
    quantum_lane = {
        "label": "Quantum-assisted method",
        "state": execution.get("key"),
        "state_label": execution.get("label"),
        "summary": execution.get("summary"),
        "execution_mode": execution.get("execution_mode"),
        "provider_label": (
            "Provider ready"
            if execution.get("provider_accessible") is True
            else "Provider not ready"
            if execution.get("provider_accessible") is False
            else "Provider unavailable"
        ),
        "hardware_label": (
            "Hardware result verified"
            if execution.get("hardware_completed") is True
            and execution.get("hardware_receipt_verified") is True
            else "Hardware result pending"
            if execution.get("hardware_submitted") is True
            else "Hardware not run"
            if ready
            else "Hardware unavailable"
        ),
        "reproducibility_label": "Reproduced locally" if local_reproduced else "Not established",
        "details": [
            {
                "key": "environment",
                "label": "Run environment",
                "value": (
                    "Local quantum-circuit simulator; provider path ready"
                    if execution.get("provider_accessible") is True
                    else "Local quantum-circuit simulator"
                ),
            },
            {
                "key": "result",
                "label": "Current result",
                "value": (
                    "Engineering control reproduced locally"
                    if local_reproduced
                    else "No reproducible result yet"
                ),
            },
            {
                "key": "market_test",
                "label": "Untouched market test",
                "value": "Eligible" if comparison.get("eligible") else "Not yet eligible",
            },
            {
                "key": "limitation",
                "label": "Main limitation",
                "value": (
                    "IBM hardware has not run; no untouched market comparison yet"
                    if execution.get("hardware_completed") is False
                    else "No untouched market comparison yet"
                    if comparison.get("eligible") is not True
                    else "No material limitation reported"
                ),
            },
        ],
        "fact_refs": list(execution.get("fact_refs", [])),
    }
    facts = [
        {
            "key": "shared_evidence",
            "label": "Evidence basis",
            "value": "Same frozen evidence" if ready and shared_manifest else "Unavailable",
            "status": shared_basis["state"],
            "fact_refs": ["presentation.evidence.shared_basis"],
        },
        {
            "key": "execution",
            "label": "Execution",
            "value": (
                "Local simulator reproduced / hardware not run"
                if local_reproduced and execution.get("hardware_completed") is False
                else execution.get("label")
            ),
            "status": execution.get("key"),
            "fact_refs": ["state_axes.execution"],
        },
        {
            "key": "market_comparison",
            "label": "Market comparison",
            "value": (
                "Untouched comparison unavailable"
                if comparison.get("eligible") is not True
                else comparison.get("outcome_label")
            ),
            "status": comparison.get("key"),
            "fact_refs": ["state_axes.comparison"],
        },
    ]
    gates = _presentation_gates(payload, axes)
    next_items = [str(item) for item in _safe_list(answer.get("next_required_evidence"))]
    next_summary = (
        next_items[0] if next_items else "No additional evidence requirement is currently exported."
    )
    strategy_count = downstream.get("strategy_count")
    paper_count = downstream.get("paper_decision_count")
    impact_headline = {
        **downstream,
        "fact_refs": list(downstream.get("fact_refs", [])),
    }
    impact_outcomes = [
        {
            "key": "strategy",
            "label": "Validated strategy",
            "value": (
                f"{strategy_count} validated strategies changed"
                if strategy_count
                else "No validated strategy changed"
            ),
            "state": downstream.get("key"),
            "fact_refs": ["state_axes.downstream.strategy_count"],
        },
        {
            "key": "paper_decision",
            "label": "Paper decision",
            "value": (
                f"{paper_count} governed paper decisions changed"
                if paper_count
                else "No governed paper decision changed"
            ),
            "state": downstream.get("key"),
            "fact_refs": ["state_axes.downstream.paper_decision_count"],
        },
    ]
    metrics = [
        {
            "key": "experiment",
            "label": "Experiment",
            "value": (
                "Reproduced locally"
                if ready
                and engineering.get("available") is True
                and engineering.get("pass_count") == engineering.get("check_count")
                else "Unavailable"
                if not ready
                else "Not fully reproduced"
            ),
            "status": engineering.get("status") if ready else "unavailable",
            "fact_refs": ["answer.engineering_checks"],
        },
        {
            "key": "market_proof",
            "label": "Market proof",
            "value": comparison.get("label"),
            "status": comparison.get("key"),
            "fact_refs": ["state_axes.comparison"],
        },
        {
            "key": "downstream",
            "label": "Downstream impact",
            "value": (
                "No strategy or paper-decision change"
                if strategy_count == 0 and paper_count == 0
                else "Paper decision influenced"
                if paper_count and paper_count > 0
                else "Validated strategy changed"
                if strategy_count and strategy_count > 0
                else "Unavailable"
            ),
            "status": downstream.get("key"),
            "fact_refs": ["state_axes.downstream"],
        },
    ]
    if not ready:
        evidence_row_summary = "Evidence summary unavailable until the public source records agree."
    elif comparison.get("eligible"):
        evidence_row_summary = (
            f"Both methods were compared fairly. {comparison.get('outcome_label')}."
        )
    elif (
        local_reproduced
        and execution.get("provider_accessible") is True
        and execution.get("hardware_completed") is False
    ):
        evidence_row_summary = "The experimental loop reproduced locally; provider access is ready, IBM hardware has not run, and no fair untouched market comparison is available."
    else:
        evidence_row_summary = "The shared comparison is still waiting for reproducible evidence."
    consequence_row_summary = (
        downstream.get("summary")
        if ready
        else "Strategy and paper impact are unavailable until source records agree."
    )
    if freshness.get("key") in {"contradictory", "unavailable"}:
        answer_row_summary = (
            f"{proof.get('label')} historically — the current market-level verdict is "
            "unavailable until source records agree."
        )
    elif freshness.get("key") == "stale":
        answer_row_summary = (
            f"{proof.get('label')} historically — the evidence is stale and cannot support "
            "a current advantage claim."
        )
    elif freshness.get("key") == "decayed":
        answer_row_summary = (
            f"{proof.get('label')} historically — the evidence no longer meets the current "
            "stability contract."
        )
    elif proof.get("key") == "unproven" and comparison.get("key") == "not_measurable":
        answer_row_summary = "Unproven — the engineering pathway works, but market-level quantum advantage is not measurable yet."
    else:
        answer_row_summary = f"{proof.get('label')} — {comparison.get('label')}."

    if freshness.get("key") in {"contradictory", "unavailable"}:
        verdict_summary = "The market-level quantum verdict is unavailable until the public evidence records agree."
    elif freshness.get("key") == "stale":
        verdict_summary = (
            "The historical proof and execution record remains visible, but the evidence is "
            "outside the freshness window and cannot support a current advantage claim."
        )
    elif freshness.get("key") == "decayed":
        verdict_summary = (
            "The historical proof and execution record remains intact, but its evidence no "
            "longer satisfies the current stability contract and cannot support a current claim."
        )
    elif proof.get("key") == "unproven" and comparison.get("key") == "not_measurable":
        verdict_summary = "Qadam's hybrid classical-quantum experimental pathway is implemented and reproducible locally. A genuine market-level quantum advantage remains unproven because no authorized IBM hardware result, untouched market comparison, or forward-validated strategy impact exists yet."
    elif comparison.get("key") == "classical_preferred":
        verdict_summary = (
            "The fair comparison supports the conventional method. The simpler method is "
            "preferred while the market-level quantum proof remains unchanged."
        )
    elif proof.get("key") == "validated":
        verdict_summary = "The quantum-assisted contribution has passed the governed hardware, untouched-market, and matched-comparison requirements."
    elif proof.get("key") == "provisional":
        verdict_summary = "The quantum-assisted contribution is promising on untouched evidence, but the complete governed proof remains unfinished."
    else:
        verdict_summary = _text(
            answer.get("plain_english_summary"), "No market-level conclusion is available."
        )
    verdict_statements = [
        {
            "key": "known",
            "label": "What Qadam knows",
            "summary": (
                "The governed hybrid experiment can be reproduced locally on the same frozen evidence."
                if ready and local_reproduced and classical_reproduced
                else "The current experiment record is not complete enough to state a reproducible result."
            ),
            "state": "verified"
            if ready and local_reproduced and classical_reproduced
            else "unavailable",
        },
        {
            "key": "cannot_claim",
            "label": "What Qadam cannot claim",
            "summary": (
                "It cannot claim a market-level quantum edge or a better trading decision without an authorized IBM hardware result and an untouched fair market comparison."
                if proof.get("key") == "unproven"
                else verdict_summary
            ),
            "state": proof.get("key"),
        },
        {
            "key": "next",
            "label": "What must happen next",
            "summary": next_summary,
            "state": "waiting" if next_items else "complete",
        },
    ]
    row_summaries = {
        "evidence": evidence_row_summary,
        "consequence": consequence_row_summary,
        "answer": answer_row_summary,
    }
    rows = {
        key: {
            "id": key,
            **definition,
            "collapsed_by_default": True,
            "summary": row_summaries[key],
            "fact_refs": {
                "evidence": ["presentation.evidence"],
                "consequence": ["presentation.impact"],
                "answer": ["presentation.verdict"],
            }[key],
        }
        for key, definition in PRESENTATION_SECTIONS.items()
    }
    return {
        "section_order": ["evidence", "consequence", "answer"],
        "rows": rows,
        "evidence": {
            "shared_basis": shared_basis,
            "conventional_lane": conventional_lane,
            "quantum_lane": quantum_lane,
            "matched_outcome": {
                key: value for key, value in comparison.items() if key != "eligibility_checks"
            },
            "facts": facts,
        },
        "impact": {
            "headline": impact_headline,
            "outcomes": impact_outcomes,
            "gates": gates,
            "boundary": (
                "Quantum findings remain research-only until they survive a fair classical "
                "comparison, untouched market evidence, required hardware evidence, and the "
                "governed strategy and paper-decision gates."
            ),
        },
        "verdict": {
            "proof_state": proof.get("key"),
            "proof_state_label": proof.get("label"),
            "comparison_state": comparison.get("key"),
            "comparison_label": comparison.get("label"),
            "scientific_verdict": comparison.get("key"),
            "scientific_verdict_label": comparison.get("label"),
            "freshness_state": freshness.get("key"),
            "freshness_label": freshness.get("label"),
            "summary": verdict_summary,
            "statements": verdict_statements,
            "metrics": metrics,
            "next_evidence": {
                "label": "Next proof required",
                "summary": next_summary,
                "items": next_items,
                "item_refs": ["answer.next_required_evidence"],
            },
        },
        "technical_record": {
            "label": "View technical evidence",
            "closed_by_default": True,
            "index": [
                {"key": key, "label": label, "path": path}
                for key, label, path in TECHNICAL_RECORD_INDEX
            ],
        },
    }


def build_quantum_edge_page_view_model_from_sources(
    sources: dict[str, dict[str, Any]],
    *,
    generated_at: str,
) -> dict[str, Any]:
    """Validate Wave F/G/H and build one deterministic, fail-closed page model."""

    safety_errors: list[str] = []
    for source_id, source in sources.items():
        safety_errors.extend(f"{source_id}:{error}" for error in _public_safety_errors(source))
    if safety_errors:
        raise ValueError("unsafe_quantum_edge_source:" + ";".join(sorted(safety_errors)))

    integrity_errors = _source_integrity_errors(sources)
    semantic_errors = _source_semantic_errors(sources) if not integrity_errors else []
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
        error.startswith(
            (
                "evidence_identity_conflict:",
                "downstream_lineage_conflict:",
                "wave_h_",
                "provider_readiness_conflict:",
                "fixture_promoted",
                "unproven_result",
            )
        )
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
    historical_proof_state = _text(
        h.get("prior_public_proof_state"),
        raw_proof_state
        if raw_proof_state in {"unproven", "provisional", "validated"}
        else "unproven",
    )
    proof_state, verdict, verdict_label, plain_summary = _proof_summary(
        projection_status=projection_status,
        raw_proof_state=raw_proof_state,
        raw_verdict=raw_verdict,
    )
    proof_label = PROOF_LABELS.get(proof_state, "Unproven")
    proof_steps = [
        dict(row) for row in _safe_list(f_quantum.get("proof_ladder")) if isinstance(row, dict)
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
        "contract_version": PRESENTATION_CONTRACT_VERSION,
        "page_copy": dict(PAGE_COPY),
        "projection_status": projection_status,
        "source_artifacts": source_records,
        "source_lineage": {
            "mode": "verified_content_hashes_and_shared_evidence_identity",
            "source_count": len(source_records),
            "content_hashes_verified": not any(
                error.startswith("source_content_hash_mismatch:") for error in integrity_errors
            ),
            "semantic_coherence_passed": coherence_passed,
            "shared_evidence_identity": {
                "shared_manifest_hash": _safe_dict(f_quantum.get("provenance")).get(
                    "shared_manifest_hash"
                ),
                "hardware_manifest_hash": _safe_dict(f_quantum.get("provenance")).get(
                    "hardware_manifest_hash"
                ),
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
            "read_more_label": "How Qadam researches, finds evidence and makes a conclusion",
            "read_less_label": "Minimize -",
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
            "historical_proof_state": historical_proof_state,
            "proof_state_label": proof_label,
            "scientific_verdict": verdict,
            "raw_scientific_verdict": raw_verdict,
            "scientific_verdict_label": verdict_label,
            "plain_english_summary": plain_summary,
            "proof_ladder": {
                "completed_count": sum(row.get("state") == "complete" for row in proof_steps),
                "step_count": len(proof_steps),
                "steps": proof_steps,
            },
            "engineering_checks": engineering,
            "market_proof_prerequisites": market,
            "current_blockers": [str(row) for row in _safe_list(h.get("blockers"))],
            "next_required_evidence": [str(row) for row in _safe_list(h.get("next_actions"))],
        },
        "evidence": {
            "strongest_evidence": _safe_dict(f_quantum.get("strongest_evidence")),
            "experiments": [
                dict(row)
                for row in _safe_list(f_quantum.get("experiments"))
                if isinstance(row, dict)
            ],
            "matched_classical_comparison": _safe_dict(f_quantum.get("comparison_summary")),
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
                    dict(row) for row in _safe_list(h.get("controls")) if isinstance(row, dict)
                ],
            },
            "operational_evidence": {
                "wave_g_cycle_id": g.get("cycle_id"),
                "wave_g_status": g.get("status"),
                "wave_g_evidence_date": g.get("evidence_date"),
                "daily_stages": _safe_dict(g.get("daily_stages")),
                "run_ledger": [
                    dict(row) for row in _safe_list(h.get("run_ledger")) if isinstance(row, dict)
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
                "validated_strategy_count": _safe_int(h_downstream.get("strategy_count")),
                "strategy_family_ids": _safe_list(f_strategy.get("strategy_family_ids")),
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
                dict(row) for row in _safe_list(g.get("public_lifecycle")) if isinstance(row, dict)
            ],
            "guarded_route": {
                "route_contract": _safe_dict(g_integration.get("route_contract")),
                "validated_edge_count": _safe_int(h_downstream.get("validated_edge_count")),
                "strategy_count": _safe_int(h_downstream.get("strategy_count")),
                "risk_review_count": _safe_int(h_downstream.get("risk_review_count")),
                "paperops_review_handoff_count": _safe_int(
                    h_downstream.get("paperops_review_handoff_count")
                ),
                "paper_order_count": _safe_int(h_downstream.get("paper_order_count")),
                "broker_write_count": _safe_int(h_downstream.get("broker_write_count")),
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
    payload["state_axes"] = _state_axes(payload)
    payload["presentation"] = _build_presentation(payload, payload["state_axes"])
    payload["content_hash"] = stable_hash(_canonical_material(payload))
    payload["render_contract_hash"] = stable_hash(_render_contract_material(payload))
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
    if payload.get("contract_version") != PRESENTATION_CONTRACT_VERSION:
        errors.append("quantum_edge_page_presentation_contract_invalid")
    if payload.get("page_copy") != PAGE_COPY:
        errors.append("quantum_edge_page_locked_copy_changed")
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
    if explainer.get("title") != "Quantum Edge":
        errors.append("quantum_edge_page_title_changed")
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

    state_axes = _safe_dict(payload.get("state_axes"))
    expected_axes = _state_axes(payload)
    if state_axes != expected_axes:
        errors.append("quantum_edge_page_state_axes_invalid")
    expected_axis_keys = [
        "proof",
        "comparison",
        "execution",
        "downstream",
        "freshness",
    ]
    if len(state_axes) != len(expected_axis_keys) or set(state_axes) != set(expected_axis_keys):
        errors.append("quantum_edge_page_state_axis_order_invalid")
    comparison_axis = _safe_dict(state_axes.get("comparison"))
    comparison_checks = _safe_list(comparison_axis.get("eligibility_checks"))
    if (
        len(comparison_checks) != 8
        or len({row.get("key") for row in comparison_checks if isinstance(row, dict)}) != 8
    ):
        errors.append("quantum_edge_page_comparison_protocol_invalid")
    expected_check_keys = [
        "same_frozen_manifest_and_features",
        "same_target_outcome_and_horizon",
        "same_chronological_split",
        "point_in_time_preprocessing_and_leakage",
        "same_metric_cost_and_statistical_rule",
        "comparable_frozen_tuning_budget",
        "same_negative_multiple_testing_and_minimum_evidence_controls",
        "reproducible_provenance",
    ]
    if [
        row.get("key") for row in comparison_checks if isinstance(row, dict)
    ] != expected_check_keys:
        errors.append("quantum_edge_page_comparison_protocol_order_invalid")
    eligible_from_checks = bool(comparison_checks) and all(
        isinstance(row, dict) and row.get("passed") is True for row in comparison_checks
    )
    if comparison_axis.get("eligible") is not eligible_from_checks:
        errors.append("quantum_edge_page_comparison_eligibility_invalid")
    proof_axis = _safe_dict(state_axes.get("proof"))
    if proof_axis.get("key") not in {"unproven", "provisional", "validated"}:
        errors.append("quantum_edge_page_proof_axis_invalid")
    if comparison_axis.get("key") not in {
        "unavailable",
        "not_measurable",
        "tied",
        "classical_preferred",
        "quantum_positive",
    }:
        errors.append("quantum_edge_page_comparison_axis_invalid")
    if any(str(ref).startswith("answer.") for ref in _safe_list(comparison_axis.get("fact_refs"))):
        errors.append("quantum_edge_page_comparison_depends_on_proof")
    freshness_axis = _safe_dict(state_axes.get("freshness"))
    if freshness_axis.get("key") not in {
        "current",
        "stale",
        "decayed",
        "unavailable",
        "contradictory",
    }:
        errors.append("quantum_edge_page_freshness_axis_invalid")

    presentation = _safe_dict(payload.get("presentation"))
    expected_presentation = _build_presentation(payload, expected_axes)
    if presentation != expected_presentation:
        errors.append("quantum_edge_page_presentation_invalid")
    if presentation.get("section_order") != ["evidence", "consequence", "answer"]:
        errors.append("quantum_edge_page_presentation_order_invalid")
    rows = _safe_dict(presentation.get("rows"))
    if len(rows) != 3 or set(rows) != {"evidence", "consequence", "answer"}:
        errors.append("quantum_edge_page_presentation_rows_invalid")
    for key, definition in PRESENTATION_SECTIONS.items():
        row = _safe_dict(rows.get(key))
        if (
            row.get("id") != key
            or row.get("sequence") != definition["sequence"]
            or row.get("eyebrow") != definition["eyebrow"]
            or row.get("title") != definition["title"]
            or row.get("collapsed_by_default") is not True
            or not _text(row.get("summary"))
        ):
            errors.append(f"quantum_edge_page_presentation_row_invalid:{key}")
    gates = _safe_list(_safe_dict(presentation.get("impact")).get("gates"))
    if [row.get("key") for row in gates if isinstance(row, dict)] != [
        key for key, _ in PRESENTATION_GATES
    ]:
        errors.append("quantum_edge_page_presentation_gates_invalid")
    for gate in gates:
        if not isinstance(gate, dict) or gate.get("state") not in GATE_STATE_LABELS:
            errors.append("quantum_edge_page_presentation_gate_state_invalid")
    technical = _safe_dict(presentation.get("technical_record"))
    if technical.get("closed_by_default") is not True or technical.get("index") != [
        {"key": key, "label": label, "path": path} for key, label, path in TECHNICAL_RECORD_INDEX
    ]:
        errors.append("quantum_edge_page_technical_record_index_invalid")

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
            expected = sum(isinstance(row, dict) and row.get("passed") is True for row in rows)
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
        if (
            comparison_axis.get("key") != "unavailable"
            or comparison_axis.get("eligible") is not False
        ):
            errors.append("quantum_edge_page_fail_closed_comparison_invalid")
        execution_axis = _safe_dict(state_axes.get("execution"))
        downstream_axis = _safe_dict(state_axes.get("downstream"))
        if projection_status in {"source_unavailable", "source_truth_conflict"}:
            for field in (
                "local_simulation_reproduced",
                "provider_accessible",
                "hardware_authorized",
                "hardware_submitted",
                "hardware_completed",
                "hardware_receipt_verified",
            ):
                if execution_axis.get(field) is not None:
                    errors.append(f"quantum_edge_page_fail_closed_execution_exposed:{field}")
            if (
                downstream_axis.get("strategy_count") is not None
                or downstream_axis.get("paper_decision_count") is not None
            ):
                errors.append("quantum_edge_page_fail_closed_downstream_exposed")
        if any(isinstance(gate, dict) and gate.get("state") != "unavailable" for gate in gates):
            errors.append("quantum_edge_page_fail_closed_gate_exposed")
    else:
        execution_axis = _safe_dict(state_axes.get("execution"))
        downstream_axis = _safe_dict(state_axes.get("downstream"))
        if proof_axis.get("key") in {
            "provisional",
            "validated",
        } and (
            comparison_axis.get("eligible") is not True
            or comparison_axis.get("key") != "quantum_positive"
        ):
            errors.append("quantum_edge_page_proof_without_fair_comparison")
        if proof_axis.get("key") == "validated" and not (
            execution_axis.get("hardware_completed") is True
            and execution_axis.get("hardware_receipt_verified") is True
        ):
            errors.append("quantum_edge_page_validated_without_hardware_evidence")
        downstream_total = _safe_int(downstream_axis.get("strategy_count")) + _safe_int(
            downstream_axis.get("paper_decision_count")
        )
        if downstream_total > 0 and not (
            proof_axis.get("key") == "validated" and comparison_axis.get("eligible") is True
        ):
            errors.append("quantum_edge_page_downstream_without_validated_comparison")
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
    errors.extend(f"quantum_edge_page_{error}" for error in _public_safety_errors(payload))
    expected_hash = stable_hash(_canonical_material(payload))
    if payload.get("content_hash") != expected_hash:
        errors.append("quantum_edge_page_content_hash_mismatch")
    expected_render_hash = stable_hash(_render_contract_material(payload))
    if payload.get("render_contract_hash") != expected_render_hash:
        errors.append("quantum_edge_page_render_contract_hash_mismatch")
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
