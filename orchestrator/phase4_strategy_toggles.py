"""Phase 4 strategy toggle snapshot contract.

Strategy toggles make manifested strategy availability visible for future
orchestration design. They do not route Risk Agent, Execution Policy, paper
orders, broker writes, quantum jobs, schedulers, or live capital.
"""

from __future__ import annotations

import json
from copy import deepcopy
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from orchestrator.config import Settings
from orchestrator.event_log import EventLog, EventLogEntry
from orchestrator.phase4_artifacts import (
    PHASE4_ARTIFACT_SCHEMA_VERSION,
    PHASE4_STRATEGY_TOGGLE_STATES,
    phase4_authority_boundary,
    validate_phase4_artifact,
)
from orchestrator.phase4_candidate_strategy_universe import build_candidate_strategy_universe
from orchestrator.phase4_manifested_strategy import build_manifested_strategy_metadata


STRATEGY_TOGGLE_CONTRACT_SCHEMA_VERSION = 1

STRATEGY_TOGGLE_AUTHORITY_FLAGS: tuple[str, ...] = (
    "trade_candidate_creation_allowed",
    "risk_agent_handoff_allowed",
    "risk_approval_allowed",
    "risk_approval_authority",
    "execution_policy_handoff_allowed",
    "execution_allowed",
    "execution_authority",
    "paper_order_allowed",
    "paper_order_authority",
    "staged_paper_order_allowed",
    "staged_paper_order_authority",
    "broker_write_allowed",
    "broker_write_authority",
    "fill_confirmation_authority",
    "receipt_evidence_authority",
    "reconciliation_truth_authority",
    "live_capital_enabled",
    "live_capital_authority",
    "quantum_provider_call_allowed",
    "quantum_hardware_submission_allowed",
    "scheduler_enabled",
)

TOGGLE_EVENT_TYPE = "phase4_strategy_toggle_snapshot_written"
TOGGLE_EVENT_COMPONENT = "phase4_strategy_toggles"
TOGGLE_RUNTIME_ARTIFACT = "phase4_strategy_toggle_snapshot.json"
TOGGLE_EVENT_LOG = "phase4_strategy_toggle_events.jsonl"


@dataclass(frozen=True)
class StrategyToggle:
    object_type: str
    strategy_key: str
    label: str
    source_candidate_key: str
    toggle_state: str
    visible_in_cockpit: bool
    event_log_required: bool
    event_log_correlation_id: str | None
    transition_event_logged: bool
    transition_reason: str
    allowed_next_states: tuple[str, ...]
    approval_state: str
    approval_event_logged: bool
    approval_event_id: str | None
    draft_document_fingerprint: str | None
    approved_document_fingerprint: str | None
    risk_agent_handoff_allowed: bool
    execution_policy_handoff_allowed: bool
    trade_candidate_created: bool
    execution_allowed: bool
    paper_order_allowed: bool
    staged_paper_order_allowed: bool
    broker_write_allowed: bool
    live_capital_enabled: bool
    authority_flags: dict[str, bool]
    boundary: str

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["allowed_next_states"] = list(self.allowed_next_states)
        return payload


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _runtime_dir(settings: Settings | None = None) -> Path:
    return Path((settings or Settings.from_env()).runtime_dir)


def _read_json(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def _candidate_universe(settings: Settings | None = None) -> dict[str, Any]:
    runtime_path = _runtime_dir(settings) / "phase4_candidate_strategy_universe.json"
    return _read_json(runtime_path) or build_candidate_strategy_universe(settings)


def _manifested_strategy_metadata(settings: Settings | None = None) -> dict[str, Any]:
    runtime_path = _runtime_dir(settings) / "phase4_manifested_strategy_metadata.json"
    return _read_json(runtime_path) or build_manifested_strategy_metadata(settings=settings)


def _fund_manager_approval_event(settings: Settings | None = None) -> dict[str, Any] | None:
    runtime_path = _runtime_dir(settings) / "phase4_fund_manager_approval_event.json"
    return _read_json(runtime_path)


def _authority_flags() -> dict[str, bool]:
    return {flag: False for flag in STRATEGY_TOGGLE_AUTHORITY_FLAGS}


def _approval_context(
    manifested_strategy: dict[str, Any],
    approval_event: dict[str, Any] | None,
) -> dict[str, Any]:
    approval = approval_event or {}
    approval_state = str(
        approval.get("approval_state")
        or manifested_strategy.get("approval_state")
        or "not_requested"
    )
    approval_event_logged = bool(
        approval.get("approval_logged") is True
        or manifested_strategy.get("approval_event_logged") is True
    )
    approval_event_id = (
        approval.get("event_log_correlation_id")
        or approval.get("approval_event_id")
        or manifested_strategy.get("event_log_correlation_id")
    )
    document_fingerprint = manifested_strategy.get("document_fingerprint")
    approved_shadow_ready = (
        approval_state == "approved"
        and approval_event_logged
        and bool(str(approval_event_id or "").strip())
        and bool(str(document_fingerprint or "").strip())
    )
    return {
        "approval_state": approval_state,
        "approval_event_logged": approval_event_logged,
        "approval_event_id": str(approval_event_id) if approval_event_id else None,
        "document_fingerprint": str(document_fingerprint) if document_fingerprint else None,
        "approved_shadow_ready": approved_shadow_ready,
    }


def _toggle_state(approval_context: dict[str, Any]) -> str:
    if approval_context["approved_shadow_ready"]:
        return "approved_shadow"
    return "draft"


def _allowed_next_states(state: str) -> tuple[str, ...]:
    if state == "inactive":
        return ("draft", "retired")
    if state == "draft":
        return ("inactive", "approved_shadow", "suspended", "retired")
    if state == "approved_shadow":
        return ("suspended", "retired")
    if state == "suspended":
        return ("draft", "approved_shadow", "retired")
    if state == "retired":
        return ()
    return ()


def _strategy_toggle(
    candidate: dict[str, Any],
    *,
    approval_context: dict[str, Any],
    event_log_correlation_id: str | None = None,
    transition_event_logged: bool = False,
) -> StrategyToggle:
    state = _toggle_state(approval_context)
    document_fingerprint = approval_context["document_fingerprint"]
    approved_fingerprint = document_fingerprint if state == "approved_shadow" else None
    return StrategyToggle(
        object_type="phase4_strategy_toggle",
        strategy_key=str(candidate.get("candidate_key") or "unknown_strategy"),
        label=str(candidate.get("name") or candidate.get("candidate_key") or "Unknown Strategy"),
        source_candidate_key=str(candidate.get("candidate_key") or "unknown_strategy"),
        toggle_state=state,
        visible_in_cockpit=True,
        event_log_required=True,
        event_log_correlation_id=event_log_correlation_id,
        transition_event_logged=transition_event_logged,
        transition_reason=(
            "approved_manifested_strategy_available"
            if state == "approved_shadow"
            else "manifested_strategy_draft_without_fund_manager_approval"
        ),
        allowed_next_states=_allowed_next_states(state),
        approval_state=approval_context["approval_state"],
        approval_event_logged=approval_context["approval_event_logged"],
        approval_event_id=approval_context["approval_event_id"],
        draft_document_fingerprint=document_fingerprint,
        approved_document_fingerprint=approved_fingerprint,
        risk_agent_handoff_allowed=False,
        execution_policy_handoff_allowed=False,
        trade_candidate_created=False,
        execution_allowed=False,
        paper_order_allowed=False,
        staged_paper_order_allowed=False,
        broker_write_allowed=False,
        live_capital_enabled=False,
        authority_flags=_authority_flags(),
        boundary=(
            "This toggle is a strategy-availability state for future orchestration design only. "
            "It cannot create trade candidates, hand off to Risk Agent or Execution Policy, "
            "stage or submit paper orders, write to brokers, or enable live capital."
        ),
    )


def build_strategy_toggle_snapshot(
    *,
    settings: Settings | None = None,
    approval_event: dict[str, Any] | None = None,
) -> dict[str, Any]:
    candidate_universe = _candidate_universe(settings)
    manifested_strategy = _manifested_strategy_metadata(settings)
    approval_event = approval_event or _fund_manager_approval_event(settings)
    approval_context = _approval_context(manifested_strategy, approval_event)
    candidates = candidate_universe.get("candidates", [])
    toggles = [
        _strategy_toggle(candidate, approval_context=approval_context).to_dict()
        for candidate in candidates
        if isinstance(candidate, dict)
    ]
    state_counts = {
        state: sum(1 for toggle in toggles if toggle.get("toggle_state") == state)
        for state in PHASE4_STRATEGY_TOGGLE_STATES
    }
    artifact = {
        "schema_version": PHASE4_ARTIFACT_SCHEMA_VERSION,
        "strategy_toggle_contract_schema_version": STRATEGY_TOGGLE_CONTRACT_SCHEMA_VERSION,
        "artifact_type": "strategy_toggle_snapshot",
        "artifact_id": "phase4:q4-9:strategy-toggle-snapshot",
        "status": "approved_shadow" if state_counts["approved_shadow"] else "draft",
        "generated_at": _now(),
        "public_safe": True,
        "authority_boundary": phase4_authority_boundary(),
        "boundary": (
            "Strategy toggles are visible governance states only and cannot route execution."
        ),
        "toggle_count": len(toggles),
        "toggles": toggles,
        "event_log_required": True,
        "event_log_written": False,
        "event_log_path": None,
        "event_log_correlation_id": None,
        "event_log_created_at": None,
        "approval_state": approval_context["approval_state"],
        "approval_event_logged": approval_context["approval_event_logged"],
        "approval_event_id": approval_context["approval_event_id"],
        "approved_shadow_ready": approval_context["approved_shadow_ready"],
        "document_fingerprint": approval_context["document_fingerprint"],
        "candidate_strategy_universe_artifact_id": candidate_universe.get("artifact_id"),
        "manifested_strategy_artifact_id": manifested_strategy.get("artifact_id"),
        "strategy_family_candidate_count": int(
            candidate_universe.get("strategy_family_candidate_count") or 0
        ),
        "trade_candidate_count": 0,
        "inactive_toggle_count": state_counts["inactive"],
        "draft_toggle_count": state_counts["draft"],
        "approved_shadow_toggle_count": state_counts["approved_shadow"],
        "suspended_toggle_count": state_counts["suspended"],
        "retired_toggle_count": state_counts["retired"],
        "risk_agent_handoff_allowed_count": 0,
        "execution_policy_handoff_allowed_count": 0,
        "trade_candidate_created_count": 0,
        "execution_allowed_count": 0,
        "paper_order_allowed_count": 0,
        "staged_paper_order_allowed_count": 0,
        "broker_write_allowed_count": 0,
        "live_capital_enabled_count": 0,
        "authority_flag_violation_count": 0,
        "trade_candidate_creation_allowed": False,
        "risk_agent_handoff_allowed": False,
        "execution_policy_handoff_allowed": False,
        "execution_allowed": False,
        "paper_order_allowed": False,
        "staged_paper_order_allowed": False,
        "broker_write_allowed": False,
        "live_capital_enabled": False,
        "quantum_provider_call_allowed": False,
        "quantum_hardware_submission_allowed": False,
        "scheduler_enabled": False,
    }
    artifact["validation_errors"] = validate_strategy_toggle_snapshot(artifact)
    return artifact


def _state_count_errors(artifact: dict[str, Any], toggles: list[dict[str, Any]]) -> list[str]:
    errors: list[str] = []
    for state in PHASE4_STRATEGY_TOGGLE_STATES:
        key = f"{state}_toggle_count"
        observed = sum(1 for toggle in toggles if toggle.get("toggle_state") == state)
        if artifact.get(key) != observed:
            errors.append(f"toggle_state_count_mismatch:{key}")
    return errors


def validate_strategy_toggle_snapshot(artifact: dict[str, Any]) -> list[str]:
    errors = list(validate_phase4_artifact(artifact))
    if artifact.get("artifact_type") != "strategy_toggle_snapshot":
        errors.append("artifact_type_not_strategy_toggle_snapshot")
    if artifact.get("event_log_required") is not True:
        errors.append("event_log_required_not_true")
    if artifact.get("trade_candidate_count") != 0:
        errors.append("trade_candidate_count_not_zero")

    toggles = artifact.get("toggles")
    if not isinstance(toggles, list):
        errors.append("strategy_toggles_missing")
        toggles = []
    if artifact.get("toggle_count") != len(toggles):
        errors.append("toggle_count_mismatch")
    errors.extend(_state_count_errors(artifact, toggles))

    approved_shadow_allowed = (
        artifact.get("approval_state") == "approved"
        and artifact.get("approval_event_logged") is True
        and artifact.get("approved_shadow_ready") is True
        and bool(str(artifact.get("approval_event_id") or "").strip())
        and bool(str(artifact.get("document_fingerprint") or "").strip())
    )

    if artifact.get("approved_shadow_toggle_count", 0) > 0 and not approved_shadow_allowed:
        errors.append("approved_shadow_without_logged_approval")
    if artifact.get("event_log_written") is True:
        if not str(artifact.get("event_log_correlation_id") or "").strip():
            errors.append("event_log_correlation_id_missing")
        if not str(artifact.get("event_log_path") or "").strip():
            errors.append("event_log_path_missing")

    required_toggle_fields = {
        "object_type",
        "strategy_key",
        "label",
        "source_candidate_key",
        "toggle_state",
        "visible_in_cockpit",
        "event_log_required",
        "transition_event_logged",
        "allowed_next_states",
        "approval_state",
        "approval_event_logged",
        "risk_agent_handoff_allowed",
        "execution_policy_handoff_allowed",
        "trade_candidate_created",
        "execution_allowed",
        "paper_order_allowed",
        "staged_paper_order_allowed",
        "broker_write_allowed",
        "live_capital_enabled",
        "authority_flags",
        "boundary",
    }
    for index, toggle in enumerate(toggles):
        if not isinstance(toggle, dict):
            errors.append(f"strategy_toggle_invalid:{index}")
            continue
        strategy_key = str(toggle.get("strategy_key") or f"toggle_{index}")
        missing = sorted(required_toggle_fields - set(toggle))
        if missing:
            errors.append(f"strategy_toggle_fields_missing:{strategy_key}:{','.join(missing)}")
        if toggle.get("object_type") != "phase4_strategy_toggle":
            errors.append(f"strategy_toggle_object_type_invalid:{strategy_key}")
        if toggle.get("toggle_state") not in PHASE4_STRATEGY_TOGGLE_STATES:
            errors.append(f"strategy_toggle_state_invalid:{strategy_key}")
        if toggle.get("visible_in_cockpit") is not True:
            errors.append(f"strategy_toggle_not_visible:{strategy_key}")
        if toggle.get("event_log_required") is not True:
            errors.append(f"strategy_toggle_event_log_not_required:{strategy_key}")
        if artifact.get("event_log_written") is True:
            if toggle.get("transition_event_logged") is not True:
                errors.append(f"strategy_toggle_transition_not_logged:{strategy_key}")
            if toggle.get("event_log_correlation_id") != artifact.get("event_log_correlation_id"):
                errors.append(f"strategy_toggle_event_log_correlation_mismatch:{strategy_key}")
        if toggle.get("toggle_state") == "approved_shadow" and not approved_shadow_allowed:
            errors.append(f"strategy_toggle_approved_shadow_without_approval:{strategy_key}")
        if (
            toggle.get("toggle_state") == "approved_shadow"
            and not toggle.get("approved_document_fingerprint")
        ):
            errors.append(f"strategy_toggle_approved_fingerprint_missing:{strategy_key}")
        for key in (
            "risk_agent_handoff_allowed",
            "execution_policy_handoff_allowed",
            "trade_candidate_created",
            "execution_allowed",
            "paper_order_allowed",
            "staged_paper_order_allowed",
            "broker_write_allowed",
            "live_capital_enabled",
        ):
            if toggle.get(key) is not False:
                errors.append(f"strategy_toggle_authority_enabled:{strategy_key}:{key}")
        flags = toggle.get("authority_flags")
        if not isinstance(flags, dict):
            errors.append(f"strategy_toggle_authority_flags_missing:{strategy_key}")
        else:
            for flag in STRATEGY_TOGGLE_AUTHORITY_FLAGS:
                if flags.get(flag) is not False:
                    errors.append(f"strategy_toggle_authority_flag_enabled:{strategy_key}:{flag}")

    for key in (
        "risk_agent_handoff_allowed_count",
        "execution_policy_handoff_allowed_count",
        "trade_candidate_created_count",
        "execution_allowed_count",
        "paper_order_allowed_count",
        "staged_paper_order_allowed_count",
        "broker_write_allowed_count",
        "live_capital_enabled_count",
        "authority_flag_violation_count",
    ):
        if artifact.get(key) != 0:
            errors.append(f"artifact_toggle_authority_count_not_zero:{key}")
    for key in (
        "trade_candidate_creation_allowed",
        "risk_agent_handoff_allowed",
        "execution_policy_handoff_allowed",
        "execution_allowed",
        "paper_order_allowed",
        "staged_paper_order_allowed",
        "broker_write_allowed",
        "live_capital_enabled",
        "quantum_provider_call_allowed",
        "quantum_hardware_submission_allowed",
        "scheduler_enabled",
    ):
        if artifact.get(key) is not False:
            errors.append(f"artifact_toggle_authority_enabled:{key}")
    return errors


def attach_strategy_toggle_event_log(
    artifact: dict[str, Any],
    *,
    event_log: EventLog | None = None,
    event_log_path: str | Path | None = None,
    settings: Settings | None = None,
) -> tuple[dict[str, Any], EventLogEntry]:
    output = deepcopy(artifact)
    log_path = Path(event_log_path or (_runtime_dir(settings) / TOGGLE_EVENT_LOG))
    log = event_log or EventLog(log_path, echo=False)
    state_counts = {
        state: output.get(f"{state}_toggle_count", 0)
        for state in PHASE4_STRATEGY_TOGGLE_STATES
    }
    entry = log.write(
        TOGGLE_EVENT_TYPE,
        TOGGLE_EVENT_COMPONENT,
        {
            "artifact_id": output.get("artifact_id"),
            "toggle_count": output.get("toggle_count"),
            "state_counts": state_counts,
            "approval_state": output.get("approval_state"),
            "approval_event_logged": output.get("approval_event_logged"),
            "approved_shadow_ready": output.get("approved_shadow_ready"),
            "trade_candidate_count": output.get("trade_candidate_count"),
            "execution_allowed_count": output.get("execution_allowed_count"),
            "paper_order_allowed_count": output.get("paper_order_allowed_count"),
            "broker_write_allowed_count": output.get("broker_write_allowed_count"),
            "live_capital_enabled_count": output.get("live_capital_enabled_count"),
            "boundary": output.get("boundary"),
        },
    )
    output["event_log_written"] = True
    output["event_log_path"] = str(log.path)
    output["event_log_correlation_id"] = entry.correlation_id
    output["event_log_created_at"] = entry.created_at
    for toggle in output.get("toggles", []):
        if isinstance(toggle, dict):
            toggle["event_log_correlation_id"] = entry.correlation_id
            toggle["transition_event_logged"] = True
    output["validation_errors"] = validate_strategy_toggle_snapshot(output)
    return output, entry


def write_strategy_toggle_snapshot(
    artifact: dict[str, Any],
    path: str | Path | None = None,
    *,
    settings: Settings | None = None,
    record_event: bool = True,
    event_log_path: str | Path | None = None,
) -> tuple[Path, dict[str, Any]]:
    output = deepcopy(artifact)
    if record_event:
        output, _ = attach_strategy_toggle_event_log(
            output,
            event_log_path=event_log_path,
            settings=settings,
        )
    else:
        output["validation_errors"] = validate_strategy_toggle_snapshot(output)
    output_path = Path(path or (_runtime_dir(settings) / TOGGLE_RUNTIME_ARTIFACT))
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(output, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return output_path, output
