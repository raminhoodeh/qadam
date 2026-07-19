"""Controlled dynamic-plan governance for the operator-ready edge engine.

Only the delimited status block may be refreshed automatically. The normative
plan body is hash-protected and can change only through an explicit, reviewed,
exact-text amendment with safety-boundary validation.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from orchestrator.config import Settings
from orchestrator.qadam_operator_ready_common import (
    ROOT,
    append_jsonl_durable,
    atomic_write_text,
    authority_flags,
    file_sha256,
    now_iso,
    read_json,
    read_jsonl,
    runtime_dir,
    sha256_json,
    sha256_text,
    unique_errors,
    validate_authority,
    write_json_atomic,
)

SCHEMA_VERSION = "qadam_dynamic_plan.v1"
PHASE_ID = "DP-0"

PLAN_PATH = ROOT / "docs" / "qadam-operator-ready-edge-engine-implementation-plan.md"
IMPLEMENTATION_LOG_PATH = (
    ROOT / "docs" / "qadam-operator-ready-edge-engine-implementation-log.md"
)

STATUS_START = "<!-- QADAM_OPERATOR_READY_DYNAMIC_STATUS_START -->"
STATUS_END = "<!-- QADAM_OPERATOR_READY_DYNAMIC_STATUS_END -->"
STATUS_PLACEHOLDER = "<!-- DYNAMIC_STATUS_EXCLUDED_FROM_NORMATIVE_HASH -->"

PLAN_STATE_ARTIFACT = "qadam_operator_ready_plan_state.json"
PHASE_EVIDENCE_ARTIFACT = "qadam_operator_ready_plan_phase_evidence.jsonl"
AMENDMENTS_ARTIFACT = "qadam_operator_ready_plan_amendments.jsonl"
DRIFT_ARTIFACT = "qadam_operator_ready_plan_drift.json"
CHECK_ARTIFACT = "qadam_dynamic_plan_checks.json"
PHASE_STATUS_ARTIFACT = "qadam_operator_ready_phase_status.json"

ALLOWED_PHASE_STATES = {
    "not_started",
    "in_progress",
    "blocked",
    "passed",
    "superseded_by_reviewed_amendment",
    "evidence_maturing",
}

PHASE_ORDER = (
    "RF-0",
    "DP-0",
    "RF-1",
    "RF-2",
    "RF-3",
    "RF-4",
    "RF-5",
    "RF-6",
    *(f"OR-{index}" for index in range(3)),
    "OR-2R",
    *(f"OR-{index}" for index in range(3, 20)),
)

PHASE_DEPENDENCIES = {
    phase: ([] if index == 0 else [PHASE_ORDER[index - 1]])
    for index, phase in enumerate(PHASE_ORDER)
}

EVIDENCE_MATURING_PHASES = {
    "OR-2R",
    "OR-3",
    "OR-6",
    "OR-7",
    "OR-8",
    "OR-9",
    "OR-12",
    "OR-13",
    "OR-16",
    "OR-19",
}

PROGRAM_WAVES = (
    ("wave0", PHASE_ORDER[:8]),
    ("wave_a", ("OR-0", "OR-1", "OR-2", "OR-2R", "OR-3", "OR-4")),
    ("wave_b", tuple(f"OR-{index}" for index in range(5, 11))),
    ("wave_c", tuple(f"OR-{index}" for index in range(11, 15))),
    ("wave_d", tuple(f"OR-{index}" for index in range(15, 17))),
    ("wave_e", tuple(f"OR-{index}" for index in range(17, 20))),
)

SAFETY_SENTINELS = (
    "30-day paper growth trial",
    "guarded Alpaca Paper",
    "live capital",
    "proof credit",
    "simulated elapsed time",
)


class DynamicPlanError(RuntimeError):
    """Raised when a plan mutation violates the controlled update contract."""


@dataclass(frozen=True)
class PlanParts:
    before: str
    dynamic: str
    after: str


def _paths(settings: Settings | None = None) -> dict[str, Path]:
    runtime = runtime_dir(settings)
    return {
        "plan_state": runtime / PLAN_STATE_ARTIFACT,
        "phase_evidence": runtime / PHASE_EVIDENCE_ARTIFACT,
        "amendments": runtime / AMENDMENTS_ARTIFACT,
        "drift": runtime / DRIFT_ARTIFACT,
        "checks": runtime / CHECK_ARTIFACT,
        "phase_status": runtime / PHASE_STATUS_ARTIFACT,
    }


def split_plan(text: str) -> PlanParts:
    if text.count(STATUS_START) != 1 or text.count(STATUS_END) != 1:
        raise DynamicPlanError("dynamic_status_markers_invalid")
    start = text.index(STATUS_START)
    end = text.index(STATUS_END, start) + len(STATUS_END)
    return PlanParts(before=text[:start], dynamic=text[start:end], after=text[end:])


def normative_plan_text(text: str) -> str:
    parts = split_plan(text)
    return f"{parts.before}{STATUS_START}\n{STATUS_PLACEHOLDER}\n{STATUS_END}{parts.after}"


def normative_plan_hash(text: str) -> str:
    return sha256_text(normative_plan_text(text))


def dynamic_block_hash(text: str) -> str:
    return sha256_text(split_plan(text).dynamic)


def _load_plan(path: Path = PLAN_PATH) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except OSError as exc:
        raise DynamicPlanError("plan_unreadable") from exc


def _initial_phase_status(generated_at: str) -> dict[str, Any]:
    return {
        "schema_version": "qadam_operator_ready_phase_status.v1",
        "artifact_type": "qadam_operator_ready_phase_status",
        "generated_at": generated_at,
        "program": "qadam_operator_ready_edge_engine",
        "current_phase": "RF-0",
        "status": "wave0_in_progress",
        "phases": {
            phase: {
                "state": "not_started",
                "checker_artifact": None,
                "evidence_hash": None,
                "updated_at": None,
            }
            for phase in PHASE_ORDER
        },
        "authority": authority_flags(),
    }


def load_or_create_phase_status(settings: Settings | None = None) -> dict[str, Any]:
    path = _paths(settings)["phase_status"]
    payload = read_json(path)
    if not payload:
        payload = _initial_phase_status(now_iso())
        write_json_atomic(path, payload)
    phases = payload.get("phases")
    if not isinstance(phases, dict):
        phases = {}
        payload["phases"] = phases
    registry_migrated = "OR-2R" not in phases
    for phase in PHASE_ORDER:
        phases.setdefault(
            phase,
            {
                "state": "not_started",
                "checker_artifact": None,
                "evidence_hash": None,
                "updated_at": None,
            },
        )
    if registry_migrated:
        generated_at = now_iso()
        phases["OR-2R"] = {
            "state": "evidence_maturing",
            "checker_artifact": None,
            "evidence_hash": None,
            "evidence_class": "mandatory_operational_reentry_gate_pending",
            "updated_at": generated_at,
            "migration_note": "Inserted between OR-2 and OR-3; OR-3 may not start until this gate passes.",
        }
        payload["generated_at"] = generated_at
        payload["current_phase"] = "OR-2R"
        payload["status"] = program_status(phases)
        write_json_atomic(path, payload)
        plan_state_path = _paths(settings)["plan_state"]
        plan_state = read_json(plan_state_path)
        if plan_state:
            plan_state["phase_order"] = list(PHASE_ORDER)
            plan_state["phase_dependencies"] = PHASE_DEPENDENCIES
            plan_state["current_phase"] = "OR-2R"
            plan_state["generated_at"] = generated_at
            write_json_atomic(plan_state_path, plan_state)
    return payload


def initialize_dynamic_plan(
    settings: Settings | None = None,
    *,
    plan_path: Path = PLAN_PATH,
) -> dict[str, Any]:
    paths = _paths(settings)
    text = _load_plan(plan_path)
    phase_status = load_or_create_phase_status(settings)
    current_hash = normative_plan_hash(text)
    existing = read_json(paths["plan_state"])
    generated_at = now_iso()
    if existing and existing.get("accepted_normative_plan_hash") != current_hash:
        drift = build_plan_drift(settings, plan_path=plan_path)
        write_json_atomic(paths["drift"], drift)
        raise DynamicPlanError("normative_plan_hash_drift")
    state = {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "qadam_operator_ready_plan_state",
        "generated_at": generated_at,
        "status": "controlled_dynamic_plan_active",
        "plan_path": str(plan_path.relative_to(ROOT)) if plan_path.is_relative_to(ROOT) else plan_path.name,
        "accepted_normative_plan_hash": current_hash,
        "dynamic_status_block_hash": dynamic_block_hash(text),
        "phase_order": list(PHASE_ORDER),
        "phase_dependencies": PHASE_DEPENDENCIES,
        "allowed_phase_states": sorted(ALLOWED_PHASE_STATES),
        "current_phase": phase_status.get("current_phase", "RF-0"),
        "automatic_normative_edits_allowed": False,
        "explicit_reviewed_amendment_required": True,
        "authority": authority_flags(),
    }
    write_json_atomic(paths["plan_state"], state)
    return state


def validate_phase_status(payload: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    phases = payload.get("phases") if isinstance(payload.get("phases"), dict) else {}
    for phase in PHASE_ORDER:
        record = phases.get(phase) if isinstance(phases.get(phase), dict) else {}
        state = record.get("state")
        if state not in ALLOWED_PHASE_STATES:
            errors.append(f"phase_state_invalid:{phase}:{state}")
        if state in {"passed", "evidence_maturing"}:
            for dependency in PHASE_DEPENDENCIES[phase]:
                dependency_state = phases.get(dependency, {}).get("state")
                if dependency_state not in {
                    "passed",
                    "superseded_by_reviewed_amendment",
                    "evidence_maturing",
                }:
                    errors.append(f"phase_dependency_not_passed:{phase}:{dependency}")
        if state == "passed" and phase in EVIDENCE_MATURING_PHASES:
            evidence_class = record.get("evidence_class")
            if evidence_class in {"code_only", "fixture_only", "synthetic_only"}:
                errors.append(f"phase_empirical_evidence_missing:{phase}")
    errors.extend(validate_authority(payload.get("authority", {}), prefix="phase_status"))
    return unique_errors(errors)


def _checker_passed(payload: dict[str, Any]) -> bool:
    status = str(payload.get("status") or "").lower()
    return status in {"passed", "ready", "ok", "rf0_baseline_ready"} or status.endswith(
        "_ready"
    )


def program_status(phases: dict[str, Any]) -> str:
    """Summarize the highest active wave without hiding maturing evidence."""

    if any(record.get("state") == "blocked" for record in phases.values() if isinstance(record, dict)):
        return "blocked"
    active_wave_name = "wave0"
    active_wave_phases = PHASE_ORDER[:8]
    for wave_name, wave_phases in PROGRAM_WAVES:
        if any(phases.get(phase, {}).get("state") != "not_started" for phase in wave_phases):
            active_wave_name = wave_name
            active_wave_phases = wave_phases
    states = [phases.get(phase, {}).get("state") for phase in active_wave_phases]
    complete_states = {"passed", "superseded_by_reviewed_amendment"}
    if states and all(state in complete_states for state in states):
        return f"{active_wave_name}_passed"
    if "evidence_maturing" in states:
        return f"{active_wave_name}_evidence_maturing"
    return f"{active_wave_name}_in_progress"


def record_phase_result(
    phase_id: str,
    checker_artifact: Path,
    *,
    settings: Settings | None = None,
    requested_state: str | None = None,
    evidence_class: str = "implementation_and_checks",
    plan_path: Path = PLAN_PATH,
) -> dict[str, Any]:
    if phase_id not in PHASE_ORDER:
        raise DynamicPlanError("unknown_phase")
    checker = read_json(checker_artifact)
    if not checker:
        raise DynamicPlanError("checker_artifact_missing_or_unreadable")
    checker_hash = file_sha256(checker_artifact)
    passed = _checker_passed(checker) and not checker.get("validation_errors")
    state = requested_state or ("passed" if passed else "blocked")
    if state not in ALLOWED_PHASE_STATES:
        raise DynamicPlanError("phase_state_invalid")
    if state == "passed" and not passed:
        raise DynamicPlanError("checker_does_not_support_passed_state")
    if phase_id in EVIDENCE_MATURING_PHASES and state == "passed" and evidence_class in {
        "code_only",
        "fixture_only",
        "synthetic_only",
    }:
        raise DynamicPlanError("empirical_phase_cannot_pass_from_non_empirical_evidence")
    paths = _paths(settings)
    phase_status = load_or_create_phase_status(settings)
    phases = phase_status["phases"]
    for dependency in PHASE_DEPENDENCIES[phase_id]:
        dependency_state = phases.get(dependency, {}).get("state")
        if dependency_state not in {
            "passed",
            "superseded_by_reviewed_amendment",
            "evidence_maturing",
        }:
            raise DynamicPlanError(f"phase_dependency_not_passed:{dependency}")
    generated_at = now_iso()
    evidence_id = "phase-evidence:" + sha256_json(
        {
            "phase_id": phase_id,
            "checker_hash": checker_hash,
            "state": state,
            "evidence_class": evidence_class,
        }
    )[:24]
    existing_ids = {
        record.get("evidence_id") for record in read_jsonl(paths["phase_evidence"])
    }
    evidence = {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "qadam_operator_ready_plan_phase_evidence",
        "evidence_id": evidence_id,
        "generated_at": generated_at,
        "phase_id": phase_id,
        "state": state,
        "evidence_class": evidence_class,
        "checker_artifact": str(checker_artifact.relative_to(ROOT))
        if checker_artifact.is_relative_to(ROOT)
        else checker_artifact.name,
        "checker_sha256": checker_hash,
        "checker_status": checker.get("status"),
        "validation_error_count": len(checker.get("validation_errors", []))
        if isinstance(checker.get("validation_errors"), list)
        else None,
        "authority": authority_flags(),
    }
    if evidence_id not in existing_ids:
        append_jsonl_durable(paths["phase_evidence"], evidence)
        _append_implementation_log(evidence)
    phases[phase_id] = {
        "state": state,
        "checker_artifact": evidence["checker_artifact"],
        "evidence_hash": checker_hash,
        "evidence_id": evidence_id,
        "evidence_class": evidence_class,
        "updated_at": generated_at,
    }
    phase_status["generated_at"] = generated_at
    phase_status["current_phase"] = _next_phase(phases)
    phase_status["status"] = program_status(phases)
    errors = validate_phase_status(phase_status)
    if errors:
        raise DynamicPlanError("phase_status_invalid:" + ",".join(errors))
    write_json_atomic(paths["phase_status"], phase_status)
    refresh_dynamic_status(settings, plan_path=plan_path)
    return evidence


def _next_phase(phases: dict[str, Any]) -> str:
    for phase in PHASE_ORDER:
        state = phases.get(phase, {}).get("state")
        if state not in {"passed", "superseded_by_reviewed_amendment"}:
            return phase
    return PHASE_ORDER[-1]


def _append_implementation_log(evidence: dict[str, Any]) -> None:
    evidence_id = evidence["evidence_id"]
    existing = ""
    if IMPLEMENTATION_LOG_PATH.exists():
        existing = IMPLEMENTATION_LOG_PATH.read_text(encoding="utf-8")
    if evidence_id in existing:
        return
    if not existing:
        existing = (
            "# Qadam Operator-Ready Edge Engine Implementation Log\n\n"
            "Append-only checker-backed implementation evidence.\n"
        )
    entry = (
        f"\n## {evidence['phase_id']} - {evidence['state']}\n\n"
        f"- Recorded at: `{evidence['generated_at']}`\n"
        f"- Evidence ID: `{evidence_id}`\n"
        f"- Checker: `{evidence['checker_artifact']}`\n"
        f"- Checker SHA-256: `{evidence['checker_sha256']}`\n"
        f"- Evidence class: `{evidence['evidence_class']}`\n"
        "- Authority: paper-only, non-authoritative, no broker write, no proof credit.\n"
    )
    atomic_write_text(IMPLEMENTATION_LOG_PATH, existing.rstrip() + "\n" + entry)


def _dynamic_status_markdown(
    phase_status: dict[str, Any], settings: Settings | None = None
) -> str:
    runtime = runtime_dir(settings)
    certification = read_json(runtime / "qadam_operator_ready_edge_engine_certification.json")
    lock = read_json(runtime / "qadam_long_backtest_lock.json")
    current_phase = phase_status.get("current_phase", "RF-0")
    current_state = phase_status.get("phases", {}).get(current_phase, {}).get(
        "state", "not_started"
    )
    passed_wave0 = sum(
        phase_status.get("phases", {}).get(phase, {}).get("state") == "passed"
        for phase in PHASE_ORDER[:8]
    )
    rows = [
        ("Plan version", "`2.0-operational-reentry`"),
        ("Plan state", f"`{phase_status.get('status', 'wave0_in_progress')}`"),
        ("Current stage", f"`{current_phase}`"),
        ("Current stage state", f"`{current_state}`"),
        ("Wave 0 phases passed", f"`{passed_wave0}_of_8`"),
        ("Last plan evidence refresh", f"`{now_iso()}`"),
        (
            "Latest operator-ready certification",
            f"`{certification.get('status', 'not_available')}`",
        ),
        ("Current execution state", "`paperops_watch_only_research_lock_active`"),
        ("Current dashboard contract", "`ten_stage_lifecycle_v4_13_routes`"),
        ("Next required action", f"`implement_or_repair_{current_phase.lower()}`"),
        ("Research lock active", f"`{lock.get('status') == 'active'}`"),
        ("Live capital", "`disabled`"),
        ("Automatic normative plan edits", "`forbidden`"),
    ]
    table = [STATUS_START, "", "| Field | Current Value |", "| --- | --- |"]
    table.extend(f"| {label} | {value} |" for label, value in rows)
    table.extend(["", STATUS_END])
    return "\n".join(table)


def _synchronize_wave0_rebaseline(
    phase_status: dict[str, Any], settings: Settings | None = None
) -> None:
    phases = phase_status.get("phases", {})
    wave0_phases = PHASE_ORDER[:8]
    passed_count = sum(phases.get(phase, {}).get("state") == "passed" for phase in wave0_phases)
    if passed_count != len(wave0_phases):
        return
    path = runtime_dir(settings) / "qadam_post_refactor_plan_rebaseline.json"
    payload = read_json(path)
    if not payload:
        return
    payload.update(
        {
            "generated_at": now_iso(),
            "status": "wave0_rebaselined",
            "wave0_phase_pass_count": passed_count,
            "rf6_state_after_record": phases.get("RF-6", {}).get("state"),
            "current_phase_after_record": phase_status.get("current_phase"),
            "next_phase": "OR-0",
        }
    )
    write_json_atomic(path, payload)


def refresh_dynamic_status(
    settings: Settings | None = None,
    *,
    plan_path: Path = PLAN_PATH,
) -> dict[str, Any]:
    paths = _paths(settings)
    state = read_json(paths["plan_state"])
    if not state:
        state = initialize_dynamic_plan(settings, plan_path=plan_path)
    text = _load_plan(plan_path)
    current_normative_hash = normative_plan_hash(text)
    if current_normative_hash != state.get("accepted_normative_plan_hash"):
        drift = build_plan_drift(settings, plan_path=plan_path)
        write_json_atomic(paths["drift"], drift)
        raise DynamicPlanError("normative_plan_hash_drift")
    phase_status = load_or_create_phase_status(settings)
    errors = validate_phase_status(phase_status)
    if errors:
        raise DynamicPlanError("phase_status_invalid:" + ",".join(errors))
    _synchronize_wave0_rebaseline(phase_status, settings)
    parts = split_plan(text)
    replacement = _dynamic_status_markdown(phase_status, settings)
    new_text = f"{parts.before}{replacement}{parts.after}"
    if normative_plan_hash(new_text) != current_normative_hash:
        raise DynamicPlanError("dynamic_refresh_changed_normative_hash")
    atomic_write_text(plan_path, new_text)
    state["generated_at"] = now_iso()
    state["dynamic_status_block_hash"] = dynamic_block_hash(new_text)
    state["current_phase"] = phase_status.get("current_phase")
    write_json_atomic(paths["plan_state"], state)
    drift = build_plan_drift(settings, plan_path=plan_path)
    write_json_atomic(paths["drift"], drift)
    return state


def build_plan_drift(
    settings: Settings | None = None,
    *,
    plan_path: Path = PLAN_PATH,
) -> dict[str, Any]:
    paths = _paths(settings)
    state = read_json(paths["plan_state"])
    text = _load_plan(plan_path)
    current_hash = normative_plan_hash(text)
    phase_status = load_or_create_phase_status(settings)
    phase_errors = validate_phase_status(phase_status)
    accepted_hash = state.get("accepted_normative_plan_hash")
    drift_reasons: list[str] = []
    if accepted_hash and accepted_hash != current_hash:
        drift_reasons.append("normative_plan_hash_changed_without_reviewed_amendment")
    drift_reasons.extend(phase_errors)
    return {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "qadam_operator_ready_plan_drift",
        "generated_at": now_iso(),
        "status": "drift_detected" if drift_reasons else "no_drift",
        "drift_detected": bool(drift_reasons),
        "drift_reasons": unique_errors(drift_reasons),
        "accepted_normative_plan_hash": accepted_hash,
        "current_normative_plan_hash": current_hash,
        "phase_status_error_count": len(phase_errors),
        "amendment_required": bool(drift_reasons),
        "authority": authority_flags(),
    }


def propose_amendment(
    *,
    reason: str,
    target_heading: str,
    old_text: str = "",
    new_text: str = "",
    settings: Settings | None = None,
    plan_path: Path = PLAN_PATH,
) -> dict[str, Any]:
    if not reason.strip() or not target_heading.strip():
        raise DynamicPlanError("amendment_reason_and_target_required")
    plan_text = _load_plan(plan_path)
    proposal_id = "plan-amendment:" + sha256_json(
        {
            "reason": reason,
            "target_heading": target_heading,
            "old_text": old_text,
            "new_text": new_text,
            "plan_hash": normative_plan_hash(plan_text),
        }
    )[:24]
    proposal = {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "qadam_operator_ready_plan_amendment",
        "proposal_id": proposal_id,
        "generated_at": now_iso(),
        "state": "proposed_not_applied",
        "reason": reason.strip(),
        "target_heading": target_heading.strip(),
        "old_text": old_text,
        "new_text": new_text,
        "expected_normative_plan_hash": normative_plan_hash(plan_text),
        "operator_reviewed": False,
        "automatic_application_allowed": False,
        "safety_impact": "must_remain_none",
        "authority": authority_flags(),
    }
    path = _paths(settings)["amendments"]
    existing = {record.get("proposal_id") for record in read_jsonl(path)}
    if proposal_id not in existing:
        append_jsonl_durable(path, proposal)
    return proposal


def apply_reviewed_amendment(
    proposal_id: str,
    *,
    operator_reviewed: bool,
    settings: Settings | None = None,
    plan_path: Path = PLAN_PATH,
) -> dict[str, Any]:
    if operator_reviewed is not True:
        raise DynamicPlanError("explicit_operator_review_required")
    paths = _paths(settings)
    records = read_jsonl(paths["amendments"])
    proposal = next(
        (record for record in reversed(records) if record.get("proposal_id") == proposal_id),
        None,
    )
    if proposal is None:
        raise DynamicPlanError("amendment_proposal_not_found")
    if proposal.get("state") != "proposed_not_applied":
        raise DynamicPlanError("amendment_not_in_proposed_state")
    old_text = str(proposal.get("old_text") or "")
    new_text = str(proposal.get("new_text") or "")
    if not old_text or not new_text:
        raise DynamicPlanError("amendment_exact_text_required")
    text = _load_plan(plan_path)
    if normative_plan_hash(text) != proposal.get("expected_normative_plan_hash"):
        raise DynamicPlanError("amendment_plan_hash_precondition_failed")
    if text.count(old_text) != 1:
        raise DynamicPlanError("amendment_old_text_must_match_once")
    amended = text.replace(old_text, new_text, 1)
    split_plan(amended)
    lowered = amended.lower()
    for sentinel in SAFETY_SENTINELS:
        if sentinel.lower() not in lowered:
            raise DynamicPlanError(f"amendment_removed_safety_sentinel:{sentinel}")
    atomic_write_text(plan_path, amended)
    state = read_json(paths["plan_state"])
    state["accepted_normative_plan_hash"] = normative_plan_hash(amended)
    state["generated_at"] = now_iso()
    state["last_reviewed_amendment_id"] = proposal_id
    write_json_atomic(paths["plan_state"], state)
    applied = dict(proposal)
    applied["generated_at"] = now_iso()
    applied["state"] = "applied_after_explicit_review"
    applied["operator_reviewed"] = True
    applied["applied_normative_plan_hash"] = state["accepted_normative_plan_hash"]
    append_jsonl_durable(paths["amendments"], applied)
    refresh_dynamic_status(settings, plan_path=plan_path)
    return applied


def accept_current_plan_revision_after_explicit_review(
    *,
    operator_reviewed: bool,
    reason: str,
    settings: Settings | None = None,
    plan_path: Path = PLAN_PATH,
) -> dict[str, Any]:
    """Accept an already-authored plan revision after explicit operator review.

    This is for revisions the operator supplied or explicitly instructed Qadam to
    implement before the controlled state was refreshed. It does not edit the
    normative plan and cannot be invoked without the explicit review flag.
    """

    if operator_reviewed is not True:
        raise DynamicPlanError("explicit_operator_review_required")
    if not reason.strip():
        raise DynamicPlanError("review_reason_required")
    text = _load_plan(plan_path)
    lowered = text.lower()
    for sentinel in SAFETY_SENTINELS:
        if sentinel.lower() not in lowered:
            raise DynamicPlanError(f"reviewed_revision_missing_safety_sentinel:{sentinel}")
    paths = _paths(settings)
    state = read_json(paths["plan_state"])
    previous_hash = state.get("accepted_normative_plan_hash")
    current_hash = normative_plan_hash(text)
    generated_at = now_iso()
    acceptance_id = "plan-revision-acceptance:" + sha256_json(
        {
            "previous_hash": previous_hash,
            "current_hash": current_hash,
            "reason": reason.strip(),
        }
    )[:24]
    acceptance = {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "qadam_operator_ready_plan_amendment",
        "proposal_id": acceptance_id,
        "generated_at": generated_at,
        "state": "accepted_existing_revision_after_explicit_review",
        "reason": reason.strip(),
        "target_heading": "OR-2R - Connection Truth And OR-3 Acquisition Readiness",
        "previous_normative_plan_hash": previous_hash,
        "applied_normative_plan_hash": current_hash,
        "operator_reviewed": True,
        "normative_plan_edited_by_acceptance": False,
        "automatic_application_allowed": False,
        "authority": authority_flags(),
    }
    existing = {row.get("proposal_id") for row in read_jsonl(paths["amendments"])}
    if acceptance_id not in existing:
        append_jsonl_durable(paths["amendments"], acceptance)
    phase_status = load_or_create_phase_status(settings)
    state.update(
        {
            "schema_version": SCHEMA_VERSION,
            "artifact_type": "qadam_operator_ready_plan_state",
            "generated_at": generated_at,
            "status": "controlled_dynamic_plan_active",
            "plan_path": str(plan_path.relative_to(ROOT))
            if plan_path.is_relative_to(ROOT)
            else plan_path.name,
            "accepted_normative_plan_hash": current_hash,
            "dynamic_status_block_hash": dynamic_block_hash(text),
            "phase_order": list(PHASE_ORDER),
            "phase_dependencies": PHASE_DEPENDENCIES,
            "allowed_phase_states": sorted(ALLOWED_PHASE_STATES),
            "current_phase": phase_status.get("current_phase", "OR-2R"),
            "automatic_normative_edits_allowed": False,
            "explicit_reviewed_amendment_required": True,
            "last_reviewed_amendment_id": acceptance_id,
            "authority": authority_flags(),
        }
    )
    write_json_atomic(paths["plan_state"], state)
    refresh_dynamic_status(settings, plan_path=plan_path)
    return acceptance


def validate_dynamic_plan_state(
    settings: Settings | None = None,
    *,
    plan_path: Path = PLAN_PATH,
) -> list[str]:
    paths = _paths(settings)
    errors: list[str] = []
    state = read_json(paths["plan_state"])
    if state.get("schema_version") != SCHEMA_VERSION:
        errors.append("dynamic_plan_state_schema_mismatch")
    if state.get("automatic_normative_edits_allowed") is not False:
        errors.append("automatic_normative_edits_not_forbidden")
    try:
        text = _load_plan(plan_path)
        current_hash = normative_plan_hash(text)
    except DynamicPlanError as exc:
        errors.append(str(exc))
        current_hash = None
    if current_hash != state.get("accepted_normative_plan_hash"):
        errors.append("accepted_normative_plan_hash_mismatch")
    phase_status = load_or_create_phase_status(settings)
    errors.extend(validate_phase_status(phase_status))
    errors.extend(validate_authority(state.get("authority", {}), prefix="dynamic_plan"))
    return unique_errors(errors)


def validate_negative_dynamic_plan_probes(settings: Settings | None = None) -> list[str]:
    errors: list[str] = []
    try:
        split_plan("no controlled markers")
    except DynamicPlanError:
        pass
    else:
        errors.append("malformed_marker_probe_not_rejected")
    try:
        apply_reviewed_amendment(
            "missing-proposal",
            operator_reviewed=False,
            settings=settings,
        )
    except DynamicPlanError as exc:
        if str(exc) != "explicit_operator_review_required":
            errors.append("unreviewed_amendment_probe_wrong_error")
    else:
        errors.append("unreviewed_amendment_probe_not_rejected")
    phase_status = _initial_phase_status(now_iso())
    phase_status["phases"]["RF-1"]["state"] = "passed"
    if not any(
        error.startswith("phase_dependency_not_passed:RF-1")
        for error in validate_phase_status(phase_status)
    ):
        errors.append("phase_skip_probe_not_rejected")
    unsafe = authority_flags()
    unsafe["live_capital_enabled"] = True
    if "dynamic_probe_forbidden_true:live_capital_enabled" not in validate_authority(
        unsafe, prefix="dynamic_probe"
    ):
        errors.append("dynamic_live_capital_probe_not_rejected")
    return unique_errors(errors)
