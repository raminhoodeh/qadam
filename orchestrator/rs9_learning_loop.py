"""RS-9 Learning Loop and full-potential review.

RS-9 consolidates the existing Phase 6 postmortem, model-weight, trust-score,
shadow replay, and Architect artifacts into a public-safe learning review. It
can recommend improvements, but it cannot silently mutate strategy, source
trust, risk sizing, market-context interpretation, worldview lens strength, or
any trading/execution route.
"""

from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Any

from orchestrator.config import Settings
from orchestrator.event_log import EventLog, EventLogEntry


RS9_LEARNING_LOOP_SCHEMA_VERSION = 1
RS9_LEARNING_LOOP_RUNTIME_ARTIFACT = "rs9_learning_loop_review.json"
RS9_LEARNING_LOOP_HISTORY = "rs9_learning_loop_review_history.jsonl"
RS9_LEARNING_LOOP_EVENT_LOG = "rs9_learning_loop_review_events.jsonl"
RS9_LEARNING_LOOP_EVENT_TYPE = "rs9_learning_loop_review_recorded"
RS9_LEARNING_LOOP_COMPONENT = "rs9_learning_loop"

SOURCE_REFS: dict[str, str] = {
    "phase6_visibility": "data/runtime/phase6_cockpit_learning_visibility.json",
    "paper_lifecycle": "data/runtime/paper_lifecycle_portfolio_postmortem.json",
    "postmortem_review": "data/runtime/phase6_postmortem_reduced_review.json",
    "learning_approval": "data/runtime/phase6_learning_approval_ledger.json",
    "model_weights": "data/runtime/phase6_model_weight_update_proposals.json",
    "source_trust": "data/runtime/phase6_trust_score_update_proposals.json",
    "shadow_replay": "data/runtime/phase6_shadow_strategy_replay.json",
    "architect_learning": "data/runtime/phase6_architect_learning_summary.json",
}

RS9_BOUNDARY = (
    "RS-9 is a public-safe Learning Loop review. It can recommend strategy "
    "weight, source trust, risk sizing, market-context, and worldview-lens "
    "improvements from reviewed paper outcomes, but it cannot silently rewrite "
    "strategy, cannot apply source trust, cannot change risk sizing, cannot "
    "mutate worldview lens strength, cannot create orders, cannot call broker "
    "or Alpaca POST routes, cannot enable live capital, cannot give dashboard "
    "or Telegram command authority, and cannot grant Phase 7 proof credit."
)

MUTATION_AUTHORITY_FIELDS: tuple[str, ...] = (
    "strategy_weight_mutation_allowed",
    "source_trust_mutation_allowed",
    "risk_sizing_mutation_allowed",
    "market_context_interpretation_mutation_allowed",
    "worldview_lens_strength_mutation_allowed",
    "knowledge_graph_write_allowed",
    "model_weight_update_allowed",
    "trust_score_update_allowed",
    "policy_mutation_allowed",
    "strategy_mutation_allowed",
    "learning_write_allowed",
    "dashboard_command_authority",
    "telegram_command_authority",
    "broker_write_allowed",
    "broker_post_allowed",
    "alpaca_post_allowed",
    "live_capital_enabled",
    "phase7_proof_credit_allowed",
)

UNSAFE_COUNT_FIELDS: tuple[str, ...] = (
    "broker_post_called_count",
    "alpaca_post_called_count",
    "broker_write_allowed_count",
    "live_endpoint_called_count",
    "live_capital_enabled_count",
    "phase7_proof_credit_allowed_count",
    "unsafe_write_counter_total",
    "raw_payload_exposed_count",
    "private_payload_exposed_count",
    "local_path_exposed_count",
    "secret_ref_exposed_count",
    "broker_identifier_exposed_count",
)

LEARNING_PROPOSAL_REQUIRED_FIELDS: tuple[str, ...] = (
    "proposal_key",
    "proposal_surface",
    "status",
    "recommendation",
    "rationale",
    "source_refs",
    "approval_required",
    "apply_allowed",
    "mutation_allowed",
    "fund_manager_review_state",
)

PUBLIC_STATUS_FIELDS: tuple[str, ...] = (
    "schema_version",
    "rs9_learning_loop_schema_version",
    "artifact_type",
    "artifact_id",
    "phase",
    "stage",
    "status",
    "generated_at",
    "public_safe",
    "recorded",
    "event_log_required",
    "event_log_written",
    "event_log_event_count",
    "validation_error_count",
    "source_artifact_count",
    "source_missing_count",
    "source_validation_error_count",
    "source_status_records",
    "learning_direction",
    "learning_direction_reason",
    "full_potential_state",
    "paperops_guarded_paper_trading_not_blocked",
    "postmortem_due_count",
    "postmortem_resolved_count",
    "postmortem_deferred_count",
    "closed_trade_postmortem_coverage_count",
    "closed_trade_missing_postmortem_count",
    "proposal_count",
    "active_proposal_count",
    "blocked_proposal_count",
    "strategy_weight_proposal_count",
    "source_trust_proposal_count",
    "risk_sizing_proposal_count",
    "market_context_proposal_count",
    "worldview_lens_proposal_count",
    "learning_proposals",
    "blocked_authorities",
    "blocked_authority_count",
    *MUTATION_AUTHORITY_FIELDS,
    *UNSAFE_COUNT_FIELDS,
    "next_action",
    "boundary",
)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _runtime_dir(settings: Settings | None = None) -> Path:
    return Path((settings or Settings.from_env()).runtime_dir)


def _repo_root(settings: Settings | None = None) -> Path:
    return _runtime_dir(settings).parent.parent


def _path(ref: str, settings: Settings | None = None) -> Path:
    return _repo_root(settings) / ref


def _read_json(ref: str, settings: Settings | None = None) -> dict[str, Any] | None:
    path = _path(ref, settings)
    if not path.exists():
        return None
    payload = json.loads(path.read_text(encoding="utf-8"))
    return payload if isinstance(payload, dict) else None


def _int(value: Any) -> int:
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0


def _list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def _has_local_path(ref: str) -> bool:
    if ref.startswith("/") or ref.startswith("~"):
        return True
    return len(ref) > 2 and ref[1:3] == ":\\"


def _authority_defaults() -> dict[str, bool]:
    return {field: False for field in MUTATION_AUTHORITY_FIELDS}


def _unsafe_counter_defaults() -> dict[str, int]:
    return {field: 0 for field in UNSAFE_COUNT_FIELDS}


def _source_status_record(
    source_key: str,
    source_ref: str,
    artifact: dict[str, Any] | None,
) -> dict[str, Any]:
    return {
        "source_key": source_key,
        "source_ref": source_ref,
        "source_status": (artifact or {}).get("status", "missing"),
        "source_stage": (artifact or {}).get("stage", "missing"),
        "public_safe": (artifact or {}).get("public_safe") is True,
        "recorded": artifact is not None and (artifact or {}).get("recorded") is True,
        "event_log_written": (artifact or {}).get("event_log_written") is True,
        "validation_error_count": len((artifact or {}).get("validation_errors", []) or []),
    }


def _safe_source_refs(*refs: Any) -> list[str]:
    output: list[str] = []
    for ref in refs:
        if isinstance(ref, list):
            output.extend(_safe_source_refs(*ref))
            continue
        if isinstance(ref, str) and ref.startswith("data/runtime/") and not _has_local_path(ref):
            if ref not in output:
                output.append(ref)
    return output


def _first_record(artifact: dict[str, Any], key: str) -> dict[str, Any]:
    records = _list(artifact.get(key))
    for record in records:
        if isinstance(record, dict):
            return record
    return {}


def _proposal(
    *,
    key: str,
    surface: str,
    recommendation: str,
    rationale: str,
    source_refs: list[str],
    review_state: str,
) -> dict[str, Any]:
    return {
        "proposal_key": key,
        "proposal_surface": surface,
        "status": "blocked_pending_fund_manager_review",
        "recommendation": recommendation,
        "rationale": rationale,
        "source_refs": _safe_source_refs(source_refs),
        "approval_required": True,
        "apply_allowed": False,
        "mutation_allowed": False,
        "fund_manager_review_state": review_state,
    }


def _learning_direction(
    *,
    postmortem_due_count: int,
    postmortem_resolved_count: int,
    active_proposal_count: int,
    blocked_proposal_count: int,
    missing_postmortem_count: int,
) -> tuple[str, str]:
    if postmortem_resolved_count > 0 and active_proposal_count > 0 and blocked_proposal_count == 0:
        return (
            "improving",
            "Reviewed postmortems produced active learning proposals without blocked mutations.",
        )
    if missing_postmortem_count > 0:
        return (
            "uncertain",
            "Closed paper outcomes still need complete postmortem coverage before Qadam can judge improvement.",
        )
    if postmortem_due_count > postmortem_resolved_count:
        return (
            "uncertain",
            "Learning evidence exists, but postmortems are not fully resolved and mutations remain locked.",
        )
    return (
        "uncertain",
        "Learning artifacts are visible, but no approved update has been applied yet.",
    )


def _public_status_from_artifact(artifact: dict[str, Any]) -> dict[str, Any]:
    output = {field: deepcopy(artifact.get(field)) for field in PUBLIC_STATUS_FIELDS if field in artifact}
    output["validation_error_count"] = len(artifact.get("validation_errors", []) or [])
    return output


def _refresh_validation(artifact: dict[str, Any]) -> dict[str, Any]:
    artifact.setdefault("validation_errors", [])
    artifact["public_status"] = _public_status_from_artifact(artifact)
    for _ in range(2):
        artifact["validation_errors"] = validate_rs9_learning_loop(artifact)
        artifact["validation_error_count"] = len(artifact["validation_errors"])
        artifact["public_status"] = _public_status_from_artifact(artifact)
    if artifact["validation_errors"]:
        artifact["status"] = "blocked"
        artifact["public_status"] = _public_status_from_artifact(artifact)
    return artifact


def rs9_learning_loop_paths(settings: Settings | None = None) -> tuple[Path, Path, Path]:
    runtime = _runtime_dir(settings)
    return (
        runtime / RS9_LEARNING_LOOP_RUNTIME_ARTIFACT,
        runtime / RS9_LEARNING_LOOP_HISTORY,
        runtime / RS9_LEARNING_LOOP_EVENT_LOG,
    )


def build_rs9_learning_loop(settings: Settings | None = None) -> dict[str, Any]:
    settings = settings or Settings.from_env()
    generated_at = _now()
    sources = {key: _read_json(ref, settings) for key, ref in SOURCE_REFS.items()}
    source_status_records = [
        _source_status_record(key, SOURCE_REFS[key], sources[key]) for key in SOURCE_REFS
    ]
    source_missing_count = len([record for record in source_status_records if record["source_status"] == "missing"])
    source_validation_error_count = sum(record["validation_error_count"] for record in source_status_records)

    phase6 = sources["phase6_visibility"] or {}
    lifecycle = sources["paper_lifecycle"] or {}
    approval = sources["learning_approval"] or {}
    model = sources["model_weights"] or {}
    trust = sources["source_trust"] or {}
    shadow = sources["shadow_replay"] or {}
    architect = sources["architect_learning"] or {}

    review_state = str(approval.get("approval_state") or phase6.get("approval_state") or "not_requested")
    model_record = _first_record(model, "proposal_records")
    trust_record = _first_record(trust, "proposal_records")
    shadow_record = _first_record(shadow, "replay_records")
    architect_record = _first_record(architect, "recommendation_records")

    proposals = [
        _proposal(
            key="strategy_weights",
            surface="strategy_weights",
            recommendation=(
                "Keep active strategy weights unchanged until reviewed paper postmortems approve a delta."
            ),
            rationale=str(
                model_record.get("rationale")
                or "Model-weight updates are proposal-only until explicit learning approval exists."
            ),
            source_refs=_safe_source_refs(SOURCE_REFS["model_weights"], model_record.get("source_refs", [])),
            review_state=review_state,
        ),
        _proposal(
            key="source_trust",
            surface="source_trust",
            recommendation=(
                "Keep source trust scores unchanged; use current proposals as review inputs only."
            ),
            rationale=str(
                trust_record.get("rationale")
                or "Source trust changes cannot apply until Fund Manager approval exists."
            ),
            source_refs=_safe_source_refs(SOURCE_REFS["source_trust"], trust_record.get("source_refs", [])),
            review_state=review_state,
        ),
        _proposal(
            key="risk_sizing",
            surface="risk_sizing",
            recommendation=(
                "Keep risk sizing unchanged until closed-trade postmortems prove sizing changes are warranted."
            ),
            rationale=str(
                architect_record.get("rationale")
                or "Architect recommendations are blocked from risk-limit mutation until learning review."
            ),
            source_refs=_safe_source_refs(SOURCE_REFS["architect_learning"], architect_record.get("source_refs", [])),
            review_state=review_state,
        ),
        _proposal(
            key="market_context_interpretation",
            surface="market_context_interpretation",
            recommendation=(
                "Use shadow replay as comparison evidence, not as a candidate or order generator."
            ),
            rationale=str(
                shadow_record.get("rationale")
                or "Shadow strategy replay can compare outcomes but cannot create trade candidates."
            ),
            source_refs=_safe_source_refs(SOURCE_REFS["shadow_replay"], shadow_record.get("source_refs", [])),
            review_state=review_state,
        ),
        _proposal(
            key="worldview_lens_strength",
            surface="worldview_lens_strength",
            recommendation=(
                "Keep worldview lens strength stable until resolved evidence marks it helpful, harmful, neutral, or untestable."
            ),
            rationale=(
                "Worldview interpretation can be reviewed against paper outcomes, but it cannot silently become stronger or weaker."
            ),
            source_refs=_safe_source_refs(
                SOURCE_REFS["postmortem_review"],
                SOURCE_REFS["architect_learning"],
                architect_record.get("source_refs", []),
            ),
            review_state=review_state,
        ),
    ]

    postmortem_due_count = _int(phase6.get("postmortem_due_count") or lifecycle.get("postmortem_due_count"))
    postmortem_resolved_count = _int(phase6.get("postmortem_resolved_count"))
    missing_postmortem_count = _int(
        lifecycle.get("closed_trade_missing_postmortem_count")
        or lifecycle.get("missing_postmortem_count")
    )
    blocked_proposal_count = len([proposal for proposal in proposals if proposal["mutation_allowed"] is False])
    active_proposal_count = len([proposal for proposal in proposals if proposal["apply_allowed"] is True])
    learning_direction, learning_direction_reason = _learning_direction(
        postmortem_due_count=postmortem_due_count,
        postmortem_resolved_count=postmortem_resolved_count,
        active_proposal_count=active_proposal_count,
        blocked_proposal_count=blocked_proposal_count,
        missing_postmortem_count=missing_postmortem_count,
    )

    blockers = []
    if source_missing_count:
        blockers.append("rs9_source_artifact_missing")
    if source_validation_error_count:
        blockers.append("rs9_source_validation_errors")

    artifact = {
        "schema_version": 1,
        "rs9_learning_loop_schema_version": RS9_LEARNING_LOOP_SCHEMA_VERSION,
        "artifact_type": "rs9_learning_loop_review",
        "artifact_id": "rs:rs-9:learning-loop-review",
        "phase": "RS",
        "stage": "RS-9",
        "status": "review_ready" if not blockers else "blocked",
        "generated_at": generated_at,
        "public_safe": True,
        "recorded": False,
        "event_log_required": True,
        "event_log_written": False,
        "event_log_event_count": 0,
        "event_log_correlation_id": None,
        "event_log_created_at": None,
        "validation_error_count": 0,
        "source_refs": list(SOURCE_REFS.values()),
        "source_status_records": source_status_records,
        "source_artifact_count": len(source_status_records),
        "source_missing_count": source_missing_count,
        "source_validation_error_count": source_validation_error_count,
        "learning_direction": learning_direction,
        "learning_direction_reason": learning_direction_reason,
        "full_potential_state": "learning_visible_but_mutation_locked",
        "paperops_guarded_paper_trading_not_blocked": True,
        "postmortem_due_count": postmortem_due_count,
        "postmortem_resolved_count": postmortem_resolved_count,
        "postmortem_deferred_count": _int(phase6.get("deferred_action_count")),
        "closed_trade_postmortem_coverage_count": _int(
            lifecycle.get("closed_trade_postmortem_coverage_count")
        ),
        "closed_trade_missing_postmortem_count": missing_postmortem_count,
        "proposal_count": len(proposals),
        "active_proposal_count": active_proposal_count,
        "blocked_proposal_count": blocked_proposal_count,
        "strategy_weight_proposal_count": 1,
        "source_trust_proposal_count": 1,
        "risk_sizing_proposal_count": 1,
        "market_context_proposal_count": 1,
        "worldview_lens_proposal_count": 1,
        "learning_proposals": proposals,
        "blocked_authorities": list(MUTATION_AUTHORITY_FIELDS),
        "blocked_authority_count": len(MUTATION_AUTHORITY_FIELDS),
        **_authority_defaults(),
        **_unsafe_counter_defaults(),
        "blockers": sorted(set(blockers)),
        "blocker_count": len(set(blockers)),
        "next_action": (
            "Review RS-9 learning proposals before allowing any strategy, source, risk, market-context, or worldview mutation."
        ),
        "boundary": RS9_BOUNDARY,
    }
    return _refresh_validation(artifact)


def _public_safety_errors(payload: Any, path: str = "$") -> list[str]:
    errors: list[str] = []
    if isinstance(payload, dict):
        for key, value in payload.items():
            lowered = str(key).lower()
            if lowered in {
                "raw_payload",
                "private_payload",
                "broker_order_id",
                "external_order_id",
                "access_token",
                "refresh_token",
                "secret",
            }:
                errors.append(f"public_forbidden_key:{path}.{key}")
            errors.extend(_public_safety_errors(value, f"{path}.{key}"))
    elif isinstance(payload, list):
        for index, value in enumerate(payload):
            errors.extend(_public_safety_errors(value, f"{path}[{index}]"))
    elif isinstance(payload, str):
        lowered = payload.lower()
        if _has_local_path(payload):
            errors.append(f"public_local_path:{path}")
        if any(marker in lowered for marker in ("api_key", "bearer ", "secret_", "token_", "token=", "secret=")):
            errors.append(f"public_secret_ref:{path}")
        if any(marker in lowered for marker in ("broker_order_id", "external_order_id", "fill_id")):
            errors.append(f"public_broker_identifier:{path}")
    return errors


def validate_rs9_learning_loop(artifact: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    required = set(PUBLIC_STATUS_FIELDS) | {"public_status", "source_refs", "blockers", "blocker_count"}
    missing = sorted(required - set(artifact))
    if missing:
        errors.append("rs9_missing_fields:" + ",".join(missing))
    if artifact.get("rs9_learning_loop_schema_version") != RS9_LEARNING_LOOP_SCHEMA_VERSION:
        errors.append("rs9_schema_version_mismatch")
    if artifact.get("phase") != "RS" or artifact.get("stage") != "RS-9":
        errors.append("rs9_phase_stage_mismatch")
    if artifact.get("status") not in {"review_ready", "blocked"}:
        errors.append("rs9_status_invalid")
    if artifact.get("public_safe") is not True:
        errors.append("rs9_not_public_safe")
    if artifact.get("recorded") is not True and artifact.get("event_log_written") is True:
        errors.append("rs9_event_written_before_recorded")
    if artifact.get("learning_direction") not in {"improving", "degrading", "uncertain"}:
        errors.append("rs9_learning_direction_invalid")
    if artifact.get("full_potential_state") != "learning_visible_but_mutation_locked":
        errors.append("rs9_full_potential_state_invalid")
    if artifact.get("paperops_guarded_paper_trading_not_blocked") is not True:
        errors.append("rs9_blocks_guarded_paperops")

    source_records = artifact.get("source_status_records", [])
    if not isinstance(source_records, list) or not source_records:
        errors.append("rs9_source_records_missing")
        source_records = []
    if artifact.get("source_artifact_count") != len(source_records):
        errors.append("rs9_source_count_mismatch")
    source_missing_count = 0
    source_validation_error_count = 0
    for record in source_records:
        if not isinstance(record, dict):
            errors.append("rs9_source_record_invalid")
            continue
        source_ref = str(record.get("source_ref", ""))
        if not source_ref.startswith("data/runtime/") or _has_local_path(source_ref):
            errors.append("rs9_source_ref_not_public_safe")
        if record.get("source_status") == "missing":
            source_missing_count += 1
        source_validation_error_count += _int(record.get("validation_error_count"))
    if artifact.get("source_missing_count") != source_missing_count:
        errors.append("rs9_source_missing_count_mismatch")
    if artifact.get("source_validation_error_count") != source_validation_error_count:
        errors.append("rs9_source_validation_count_mismatch")
    for ref in artifact.get("source_refs", []):
        if not isinstance(ref, str) or not ref.startswith("data/runtime/") or _has_local_path(ref):
            errors.append("rs9_source_refs_not_public_safe")

    proposals = artifact.get("learning_proposals", [])
    if not isinstance(proposals, list) or len(proposals) < 5:
        errors.append("rs9_learning_proposals_missing")
        proposals = []
    proposal_surfaces = {str(proposal.get("proposal_surface")) for proposal in proposals if isinstance(proposal, dict)}
    required_surfaces = {
        "strategy_weights",
        "source_trust",
        "risk_sizing",
        "market_context_interpretation",
        "worldview_lens_strength",
    }
    if proposal_surfaces != required_surfaces:
        errors.append("rs9_learning_proposal_surfaces_mismatch")
    active_count = 0
    blocked_count = 0
    for proposal in proposals:
        if not isinstance(proposal, dict):
            errors.append("rs9_learning_proposal_invalid")
            continue
        missing_proposal = sorted(set(LEARNING_PROPOSAL_REQUIRED_FIELDS) - set(proposal))
        if missing_proposal:
            errors.append("rs9_learning_proposal_missing:" + ",".join(missing_proposal))
        if proposal.get("apply_allowed") is not False:
            errors.append("rs9_learning_proposal_apply_allowed")
        if proposal.get("mutation_allowed") is not False:
            errors.append("rs9_learning_proposal_mutation_allowed")
        if proposal.get("approval_required") is not True:
            errors.append("rs9_learning_proposal_without_approval_required")
        if str(proposal.get("status", "")).startswith("blocked"):
            blocked_count += 1
        if proposal.get("apply_allowed") is True:
            active_count += 1
        for ref in proposal.get("source_refs", []):
            if not isinstance(ref, str) or not ref.startswith("data/runtime/") or _has_local_path(ref):
                errors.append("rs9_learning_proposal_source_ref_not_public_safe")
    if artifact.get("proposal_count") != len(proposals):
        errors.append("rs9_proposal_count_mismatch")
    if artifact.get("active_proposal_count") != active_count:
        errors.append("rs9_active_proposal_count_mismatch")
    if artifact.get("blocked_proposal_count") != blocked_count:
        errors.append("rs9_blocked_proposal_count_mismatch")
    for key in (
        "strategy_weight_proposal_count",
        "source_trust_proposal_count",
        "risk_sizing_proposal_count",
        "market_context_proposal_count",
        "worldview_lens_proposal_count",
    ):
        if artifact.get(key) != 1:
            errors.append(f"rs9_surface_proposal_count_invalid:{key}")

    for field in MUTATION_AUTHORITY_FIELDS:
        if artifact.get(field) is not False:
            errors.append(f"rs9_authority_enabled:{field}")
    if artifact.get("blocked_authority_count") != len(artifact.get("blocked_authorities", [])):
        errors.append("rs9_blocked_authority_count_mismatch")
    if sorted(artifact.get("blocked_authorities", [])) != sorted(MUTATION_AUTHORITY_FIELDS):
        errors.append("rs9_blocked_authorities_incomplete")

    unsafe_total = 0
    for field in UNSAFE_COUNT_FIELDS:
        value = _int(artifact.get(field))
        if field != "unsafe_write_counter_total":
            unsafe_total += value
        if value != 0:
            errors.append(f"rs9_unsafe_count_nonzero:{field}")
    if artifact.get("unsafe_write_counter_total") != unsafe_total:
        errors.append("rs9_unsafe_total_mismatch")

    boundary = str(artifact.get("boundary") or "")
    for phrase in (
        "cannot silently rewrite strategy",
        "cannot apply source trust",
        "cannot change risk sizing",
        "cannot mutate worldview lens strength",
        "cannot create orders",
        "cannot enable live capital",
        "cannot give dashboard or Telegram command authority",
    ):
        if phrase not in boundary:
            errors.append("rs9_boundary_weak")
            break
    public_status = artifact.get("public_status")
    if not isinstance(public_status, dict):
        errors.append("rs9_public_status_missing")
    else:
        extra = sorted(set(public_status) - set(PUBLIC_STATUS_FIELDS))
        if extra:
            errors.append("rs9_public_status_extra_fields:" + ",".join(extra))
        for field in PUBLIC_STATUS_FIELDS:
            if field == "validation_error_count":
                continue
            if field in artifact and public_status.get(field) != artifact.get(field):
                errors.append(f"rs9_public_status_mismatch:{field}")
        errors.extend(_public_safety_errors(public_status))
    if artifact.get("event_log_written") is True:
        if not artifact.get("event_log_correlation_id"):
            errors.append("rs9_event_correlation_missing")
        if artifact.get("event_log_event_count") != 1:
            errors.append("rs9_event_count_mismatch")
    return sorted(set(errors))


def attach_rs9_learning_loop_event_log(
    artifact: dict[str, Any],
    *,
    event_log: EventLog | None = None,
    event_log_path: str | Path | None = None,
    settings: Settings | None = None,
) -> tuple[dict[str, Any], EventLogEntry]:
    output = deepcopy(artifact)
    log_path = Path(event_log_path or (_runtime_dir(settings) / RS9_LEARNING_LOOP_EVENT_LOG))
    log = event_log or EventLog(log_path, echo=False)
    entry = log.write(
        RS9_LEARNING_LOOP_EVENT_TYPE,
        RS9_LEARNING_LOOP_COMPONENT,
        {
            "artifact_id": output.get("artifact_id"),
            "status": output.get("status"),
            "learning_direction": output.get("learning_direction"),
            "proposal_count": output.get("proposal_count"),
            "blocked_proposal_count": output.get("blocked_proposal_count"),
            "postmortem_due_count": output.get("postmortem_due_count"),
            "postmortem_resolved_count": output.get("postmortem_resolved_count"),
            "blocked_authority_count": output.get("blocked_authority_count"),
            "paperops_guarded_paper_trading_not_blocked": output.get(
                "paperops_guarded_paper_trading_not_blocked"
            ),
            "boundary": output.get("boundary"),
        },
    )
    output["recorded"] = True
    output["event_log_written"] = True
    output["event_log_event_count"] = 1
    output["event_log_correlation_id"] = entry.correlation_id
    output["event_log_created_at"] = entry.created_at
    return _refresh_validation(output), entry


def write_rs9_learning_loop(
    artifact: dict[str, Any],
    *,
    settings: Settings | None = None,
    record_event: bool = True,
    event_log_path: str | Path | None = None,
) -> tuple[Path, Path, Path, dict[str, Any]]:
    output = deepcopy(artifact)
    output_path, history_path, default_event_path = rs9_learning_loop_paths(settings)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    if record_event:
        output, _ = attach_rs9_learning_loop_event_log(
            output,
            event_log_path=event_log_path or default_event_path,
            settings=settings,
        )
    else:
        output = _refresh_validation(output)
    output = _refresh_validation(output)
    output_path.write_text(json.dumps(output, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    history_record = {
        "schema_version": RS9_LEARNING_LOOP_SCHEMA_VERSION,
        "artifact_id": output.get("artifact_id"),
        "status": output.get("status"),
        "generated_at": output.get("generated_at"),
        "recorded_at": _now(),
        "learning_direction": output.get("learning_direction"),
        "proposal_count": output.get("proposal_count"),
        "blocked_proposal_count": output.get("blocked_proposal_count"),
        "postmortem_due_count": output.get("postmortem_due_count"),
        "postmortem_resolved_count": output.get("postmortem_resolved_count"),
        "blocked_authority_count": output.get("blocked_authority_count"),
        "event_log_written": output.get("event_log_written"),
        "event_log_event_count": output.get("event_log_event_count"),
        "validation_error_count": len(output.get("validation_errors", [])),
    }
    with history_path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(history_record, sort_keys=True) + "\n")
    return output_path, history_path, Path(event_log_path or default_event_path), output


def rs9_learning_loop_public_status(settings: Settings | None = None) -> dict[str, Any]:
    output_path, _, _ = rs9_learning_loop_paths(settings)
    artifact = None
    if output_path.exists():
        payload = json.loads(output_path.read_text(encoding="utf-8"))
        artifact = payload if isinstance(payload, dict) else None
    if artifact is None or artifact.get("recorded") is not True:
        _, _, _, artifact = write_rs9_learning_loop(
            build_rs9_learning_loop(settings=settings),
            settings=settings,
            record_event=True,
        )
    validation_errors = validate_rs9_learning_loop(artifact)
    public_status = _public_status_from_artifact(artifact)
    public_status["validation_error_count"] = len(validation_errors)
    return public_status
