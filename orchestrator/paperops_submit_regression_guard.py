"""Public-safe submit-side regression guard for PaperOps.

This verifier sits beside PaperOps-2. It does not submit orders; it checks that
the current submit artifact still classifies fresh and duplicate candidates
coherently before the active runner is allowed to delegate to PaperOps-2.
"""

from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Any

from orchestrator.config import Settings
from orchestrator.event_log import EventLog
from orchestrator.paperops_alpaca_paper_post import (
    build_paperops_alpaca_paper_post,
    paperops_alpaca_paper_post_submission_ledger_path,
    read_latest_paperops_alpaca_paper_post,
    validate_paperops_alpaca_paper_post,
)


PAPEROPS_SUBMIT_REGRESSION_SCHEMA_VERSION = 1
PAPEROPS_SUBMIT_REGRESSION_RUNTIME_ARTIFACT = "paperops_submit_regression_guard.json"
PAPEROPS_SUBMIT_REGRESSION_HISTORY = "paperops_submit_regression_guard_history.jsonl"
PAPEROPS_SUBMIT_REGRESSION_EVENT_LOG = "paperops_submit_regression_guard_events.jsonl"
PAPEROPS_SUBMIT_REGRESSION_EVENT_TYPE = "paperops_submit_regression_guard_recorded"
PAPEROPS_SUBMIT_REGRESSION_COMPONENT = "paperops_submit_regression_guard"
SOURCE_FRESHNESS_TOLERANCE_SECONDS = 120.0

PAPEROPS_SUBMIT_REGRESSION_BOUNDARY = (
    "Public-safe PaperOps submit-side regression guard. It can verify PaperOps-2 "
    "source freshness, idempotency-ledger classification, distinct Research Goal "
    "lineage, candidate identity, and paper-submit idempotency keys before "
    "delegation, but it cannot submit, approve, close, cancel, resize, write "
    "broker state, cannot call live endpoints, cannot expose secrets, cannot "
    "enable live capital, or cannot grant proof credit."
)

PAPEROPS_SUBMIT_REGRESSION_READY_STATUSES = {
    "healthy_idle_idempotency_guarded",
    "healthy_idle_no_fresh_submit",
    "healthy_submitted_idempotency_recorded",
    "ready_fresh_submit_consistent",
}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _runtime_dir(settings: Settings | None = None) -> Path:
    return Path((settings or Settings.from_env()).runtime_dir)


def _read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    payload = json.loads(path.read_text(encoding="utf-8"))
    return payload if isinstance(payload, dict) else {}


def _int(value: Any) -> int:
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0


def _parse_time(value: Any) -> datetime | None:
    if not value:
        return None
    text = str(value)
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed


def _newer_by_seconds(later: Any, earlier: Any) -> float:
    later_dt = _parse_time(later)
    earlier_dt = _parse_time(earlier)
    if not later_dt or not earlier_dt:
        return 0.0
    return (later_dt - earlier_dt).total_seconds()


def paperops_submit_regression_guard_paths(
    settings: Settings | None = None,
) -> tuple[Path, Path, Path]:
    runtime = _runtime_dir(settings)
    return (
        runtime / PAPEROPS_SUBMIT_REGRESSION_RUNTIME_ARTIFACT,
        runtime / PAPEROPS_SUBMIT_REGRESSION_HISTORY,
        runtime / PAPEROPS_SUBMIT_REGRESSION_EVENT_LOG,
    )


def read_latest_paperops_submit_regression_guard(
    settings: Settings | None = None,
) -> dict[str, Any]:
    output_path, _, _ = paperops_submit_regression_guard_paths(settings)
    return _read_json(output_path)


def _source_artifacts(settings: Settings) -> list[dict[str, Any]]:
    runtime = _runtime_dir(settings)
    specs = (
        ("paperops_qualified_setup_production", "paperops_qualified_setup_production.json"),
        ("paperops_auto_approval_staged_order", "paperops_auto_approval_staged_order.json"),
        ("phase7_qualified_setup_ledger", "phase7_qualified_setup_ledger.json"),
        ("phase7_test_mode_auto_approval_router", "phase7_test_mode_auto_approval_router.json"),
        ("phase7_proof_order_staging", "phase7_proof_order_staging.json"),
        ("phase7_guarded_alpaca_paper_submit_path", "phase7_guarded_alpaca_paper_submit_path.json"),
        ("paperops_first_week_paper_trade_mandate", "paperops_first_week_paper_trade_mandate.json"),
    )
    artifacts: list[dict[str, Any]] = []
    for key, filename in specs:
        path = runtime / filename
        payload = _read_json(path)
        status = str(payload.get("status") or ("missing" if not payload else "unknown"))
        active = bool(payload) and status not in {"missing", "not_run"}
        if key == "paperops_first_week_paper_trade_mandate":
            active = (
                payload.get("active") is True
                or _int(payload.get("mandate_record_count")) > 0
                or len(payload.get("mandate_records", []) or []) > 0
            )
        artifacts.append(
            {
                "key": key,
                "path": str(path),
                "artifact_id": payload.get("artifact_id"),
                "status": status,
                "generated_at": payload.get("generated_at"),
                "active": active,
            }
        )
    return artifacts


def _submission_ledger(settings: Settings) -> dict[str, Any]:
    return _read_json(paperops_alpaca_paper_post_submission_ledger_path(settings))


def _candidate_identity(record: dict[str, Any]) -> str:
    for key in (
        "candidate_identity",
        "source_setup_record_id",
        "source_staged_order_artifact_id",
        "source_submit_record_artifact_id",
        "request_fingerprint",
    ):
        value = str(record.get(key) or "").strip()
        if value:
            return value
    return ""


def _research_goal_identity(record: dict[str, Any]) -> str:
    for key in ("research_goal_id", "source_setup_record_id", "source_staged_order_artifact_id"):
        value = str(record.get(key) or "").strip()
        if value:
            return value
    lineage = record.get("research_goal_lineage")
    if isinstance(lineage, dict) and lineage:
        return json.dumps(lineage, sort_keys=True, default=str)
    return ""


def _idempotency_identity(record: dict[str, Any]) -> str:
    for key in ("source_idempotency_key", "idempotency_key", "request_fingerprint"):
        value = str(record.get(key) or "").strip()
        if value:
            return value
    return ""


def _duplicate_value_count(values: list[str]) -> int:
    seen: set[str] = set()
    duplicated: set[str] = set()
    for value in values:
        if not value:
            continue
        if value in seen:
            duplicated.add(value)
        seen.add(value)
    return len(duplicated)


def _candidate_summary(record: dict[str, Any]) -> dict[str, Any]:
    return {
        "source_family": record.get("source_family"),
        "status": record.get("status"),
        "source_setup_record_id": record.get("source_setup_record_id"),
        "research_goal_id": record.get("research_goal_id"),
        "candidate_identity": record.get("candidate_identity"),
        "source_idempotency_key": record.get("source_idempotency_key"),
        "idempotency_key": record.get("idempotency_key"),
        "eligible_for_paper_post": record.get("eligible_for_paper_post") is True,
        "fresh_for_paper_post": record.get("fresh_for_paper_post") is True,
        "previously_submitted_to_alpaca_paper": (
            record.get("previously_submitted_to_alpaca_paper") is True
        ),
    }


def build_paperops_submit_regression_guard(
    settings: Settings | None = None,
    *,
    paperops2: dict[str, Any] | None = None,
) -> dict[str, Any]:
    settings = settings or Settings.from_env()
    generated_at = _now()
    source = paperops2 or read_latest_paperops_alpaca_paper_post(settings)
    if not source:
        source = build_paperops_alpaca_paper_post(settings=settings, execute_post=False)
    source_errors = validate_paperops_alpaca_paper_post(source)
    post_generated_at = source.get("generated_at")
    source_artifacts = _source_artifacts(settings)
    stale_sources = [
        item
        for item in source_artifacts
        if item["active"]
        and _newer_by_seconds(item.get("generated_at"), post_generated_at)
        > SOURCE_FRESHNESS_TOLERANCE_SECONDS
    ]

    records = [
        record
        for record in source.get("post_candidates", []) or []
        if isinstance(record, dict)
    ]
    source_eligible_records = [
        record for record in records if record.get("eligible_for_paper_post") is True
    ]
    fresh_records = [
        record
        for record in source_eligible_records
        if record.get("fresh_for_paper_post") is True
        and record.get("previously_submitted_to_alpaca_paper") is not True
        and record.get("status") != "blocked_duplicate_paper_submit"
    ]
    duplicate_records = [
        record
        for record in source_eligible_records
        if record.get("previously_submitted_to_alpaca_paper") is True
    ]
    misclassified_duplicate_records = [
        record
        for record in duplicate_records
        if record.get("fresh_for_paper_post") is True
        or record.get("status") != "blocked_duplicate_paper_submit"
    ]

    ledger = _submission_ledger(settings)
    submitted_client_ids = set(ledger.get("submitted_client_order_ids", []) or [])
    submitted_source_keys = set(ledger.get("submitted_source_idempotency_keys", []) or [])
    paperops2_submitted_to_paper = (
        source.get("status") == "submitted_to_alpaca_paper"
        and _int(source.get("alpaca_paper_post_succeeded_count")) > 0
        and _int(source.get("broker_submit_receipt_created_count")) > 0
    )

    def _fresh_record_in_submission_ledger(record: dict[str, Any]) -> bool:
        return (
            str(record.get("idempotency_key") or "") in submitted_client_ids
            or str(record.get("source_idempotency_key") or "") in submitted_source_keys
        )

    fresh_submitted_idempotency_records = [
        record
        for record in fresh_records
        if paperops2_submitted_to_paper and _fresh_record_in_submission_ledger(record)
    ]
    fresh_submitted_idempotency_missing_records = [
        record
        for record in fresh_records
        if source.get("status") == "submitted_to_alpaca_paper"
        and not _fresh_record_in_submission_ledger(record)
    ]
    fresh_ledger_collisions = [
        record
        for record in fresh_records
        if _fresh_record_in_submission_ledger(record)
        and record not in fresh_submitted_idempotency_records
    ]
    fresh_candidate_identities = [_candidate_identity(record) for record in fresh_records]
    fresh_research_goals = [_research_goal_identity(record) for record in fresh_records]
    fresh_idempotency_keys = [_idempotency_identity(record) for record in fresh_records]

    blockers: list[str] = []
    if source_errors:
        blockers.append("paperops2_submit_artifact_invalid")
    if source.get("idempotency_ledger_active") is not True:
        blockers.append("paperops2_idempotency_ledger_inactive")
    if stale_sources:
        blockers.append("paperops2_source_artifact_stale_after_submit_artifact")
    if _int(source.get("source_eligible_submit_record_count")) != len(source_eligible_records):
        blockers.append("paperops2_source_eligible_count_mismatch")
    if _int(source.get("fresh_eligible_submit_record_count")) != len(fresh_records):
        blockers.append("paperops2_fresh_eligible_count_mismatch")
    if _int(source.get("duplicate_submit_record_count")) != len(duplicate_records):
        blockers.append("paperops2_duplicate_submit_count_mismatch")
    if fresh_ledger_collisions:
        blockers.append("fresh_submit_candidate_already_in_idempotency_ledger")
    if fresh_submitted_idempotency_missing_records:
        blockers.append("paperops2_submitted_fresh_candidate_missing_idempotency_ledger")
    if misclassified_duplicate_records:
        blockers.append("duplicate_submit_candidate_misclassified_as_fresh")
    if any(not value for value in fresh_candidate_identities):
        blockers.append("fresh_submit_candidate_identity_missing")
    if any(not value for value in fresh_research_goals):
        blockers.append("fresh_submit_research_goal_lineage_missing")
    if any(not value for value in fresh_idempotency_keys):
        blockers.append("fresh_submit_idempotency_key_missing")
    if _duplicate_value_count(fresh_candidate_identities):
        blockers.append("fresh_submit_candidate_identity_collision")
    if _duplicate_value_count(fresh_research_goals):
        blockers.append("fresh_submit_research_goal_lineage_collision")
    if _duplicate_value_count(fresh_idempotency_keys):
        blockers.append("fresh_submit_idempotency_key_collision")
    if source.get("live_capital_enabled") is not False:
        blockers.append("paperops2_live_capital_enabled")
    if _int(source.get("live_endpoint_called_count")) != 0:
        blockers.append("paperops2_live_endpoint_called")

    blocker_count = len(sorted(set(blockers)))
    if blocker_count:
        status = "blocked_submit_regression"
    elif (
        paperops2_submitted_to_paper
        and fresh_records
        and len(fresh_submitted_idempotency_records) == len(fresh_records)
    ):
        status = "healthy_submitted_idempotency_recorded"
    elif fresh_records:
        status = "ready_fresh_submit_consistent"
    elif duplicate_records:
        status = "healthy_idle_idempotency_guarded"
    else:
        status = "healthy_idle_no_fresh_submit"

    artifact = {
        "schema_version": PAPEROPS_SUBMIT_REGRESSION_SCHEMA_VERSION,
        "artifact_type": "paperops_submit_regression_guard",
        "artifact_id": "paperops:submit-regression-guard:latest",
        "phase": "PaperOps",
        "stage": "PaperOps-submit-regression-guard",
        "status": status,
        "generated_at": generated_at,
        "public_safe": True,
        "recorded": False,
        "event_log_required": True,
        "event_log_written": False,
        "event_log_path": None,
        "event_log_event_count": 0,
        "runtime_artifact_path": None,
        "history_log_path": None,
        "source_paperops2_artifact_id": source.get("artifact_id"),
        "source_paperops2_status": source.get("status", "missing"),
        "source_paperops2_generated_at": post_generated_at,
        "source_paperops2_validation_error_count": len(source_errors),
        "source_paperops2_validation_errors": source_errors[:12],
        "source_artifact_records": source_artifacts,
        "source_artifact_count": len(source_artifacts),
        "source_stale_after_post_tolerance_seconds": SOURCE_FRESHNESS_TOLERANCE_SECONDS,
        "source_stale_after_post_tolerance_count": len(stale_sources),
        "source_stale_after_post_records": stale_sources,
        "source_submit_record_count": len(records),
        "source_eligible_submit_record_count": len(source_eligible_records),
        "fresh_eligible_submit_record_count": len(fresh_records),
        "duplicate_submit_record_count": len(duplicate_records),
        "paperops2_reported_source_eligible_submit_record_count": _int(
            source.get("source_eligible_submit_record_count")
        ),
        "paperops2_reported_fresh_eligible_submit_record_count": _int(
            source.get("fresh_eligible_submit_record_count")
        ),
        "paperops2_reported_duplicate_submit_record_count": _int(
            source.get("duplicate_submit_record_count")
        ),
        "submitted_client_order_id_count": len(submitted_client_ids),
        "submitted_source_idempotency_key_count": len(submitted_source_keys),
        "idempotency_ledger_active": source.get("idempotency_ledger_active") is True,
        "fresh_submitted_ledger_collision_count": len(fresh_ledger_collisions),
        "fresh_submitted_idempotency_recorded_count": len(
            fresh_submitted_idempotency_records
        ),
        "fresh_submitted_idempotency_missing_count": len(
            fresh_submitted_idempotency_missing_records
        ),
        "duplicate_misclassified_as_fresh_count": len(misclassified_duplicate_records),
        "fresh_candidate_identity_missing_count": sum(
            1 for value in fresh_candidate_identities if not value
        ),
        "fresh_research_goal_lineage_missing_count": sum(
            1 for value in fresh_research_goals if not value
        ),
        "fresh_idempotency_key_missing_count": sum(
            1 for value in fresh_idempotency_keys if not value
        ),
        "fresh_candidate_identity_collision_count": _duplicate_value_count(
            fresh_candidate_identities
        ),
        "fresh_research_goal_lineage_collision_count": _duplicate_value_count(
            fresh_research_goals
        ),
        "fresh_idempotency_key_collision_count": _duplicate_value_count(
            fresh_idempotency_keys
        ),
        "fresh_candidate_records": [_candidate_summary(record) for record in fresh_records],
        "duplicate_candidate_records": [
            _candidate_summary(record) for record in duplicate_records
        ],
        "fresh_submitted_ledger_collision_records": [
            _candidate_summary(record) for record in fresh_ledger_collisions
        ],
        "fresh_submitted_idempotency_recorded_records": [
            _candidate_summary(record)
            for record in fresh_submitted_idempotency_records
        ],
        "fresh_submitted_idempotency_missing_records": [
            _candidate_summary(record)
            for record in fresh_submitted_idempotency_missing_records
        ],
        "duplicate_misclassified_records": [
            _candidate_summary(record) for record in misclassified_duplicate_records
        ],
        "live_capital_enabled": False,
        "live_endpoint_called_count": 0,
        "broker_post_called_count": 0,
        "broker_write_allowed_count": 0,
        "phase7_proof_credit_allowed": False,
        "secret_value_exposed": False,
        "raw_payload_exposed": False,
        "raw_broker_payload_exposed": False,
        "broker_order_identifier_exposed": False,
        "blockers": sorted(set(blockers)),
        "blocker_count": blocker_count,
        "next_required_action": (
            "Fix PaperOps-2 submit-source freshness or idempotency classification before delegation."
            if blocker_count
            else (
                (
                    "Keep active runner idle: the guarded paper submit is already recorded in the idempotency ledger."
                    if status == "healthy_submitted_idempotency_recorded"
                    else "Delegate only through PaperOps-2 guarded Alpaca Paper route when the active runner executes."
                )
                if fresh_records
                else "Keep active runner idle until a fresh distinct PaperOps-2 submit candidate appears."
            )
        ),
        "boundary": PAPEROPS_SUBMIT_REGRESSION_BOUNDARY,
    }
    artifact["validation_errors"] = validate_paperops_submit_regression_guard(artifact)
    artifact["validation_error_count"] = len(artifact["validation_errors"])
    if artifact["validation_errors"]:
        artifact["status"] = "invalid"
    return artifact


def validate_paperops_submit_regression_guard(artifact: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    required = {
        "artifact_id",
        "artifact_type",
        "blocker_count",
        "blockers",
        "boundary",
        "broker_order_identifier_exposed",
        "broker_post_called_count",
        "duplicate_misclassified_as_fresh_count",
        "duplicate_submit_record_count",
        "fresh_candidate_identity_collision_count",
        "fresh_candidate_identity_missing_count",
        "fresh_eligible_submit_record_count",
        "fresh_idempotency_key_collision_count",
        "fresh_idempotency_key_missing_count",
        "fresh_research_goal_lineage_collision_count",
        "fresh_research_goal_lineage_missing_count",
        "fresh_submitted_ledger_collision_count",
        "fresh_submitted_idempotency_recorded_count",
        "fresh_submitted_idempotency_missing_count",
        "generated_at",
        "idempotency_ledger_active",
        "live_capital_enabled",
        "live_endpoint_called_count",
        "phase",
        "phase7_proof_credit_allowed",
        "public_safe",
        "raw_broker_payload_exposed",
        "schema_version",
        "secret_value_exposed",
        "source_artifact_records",
        "source_eligible_submit_record_count",
        "source_paperops2_status",
        "source_stale_after_post_tolerance_count",
        "stage",
        "status",
    }
    missing = sorted(required - set(artifact))
    if missing:
        errors.append("paperops_submit_regression_missing_fields:" + ",".join(missing))
    if artifact.get("schema_version") != PAPEROPS_SUBMIT_REGRESSION_SCHEMA_VERSION:
        errors.append("paperops_submit_regression_schema_version_mismatch")
    if artifact.get("artifact_type") != "paperops_submit_regression_guard":
        errors.append("paperops_submit_regression_artifact_type_mismatch")
    if artifact.get("phase") != "PaperOps":
        errors.append("paperops_submit_regression_phase_invalid")
    if artifact.get("public_safe") is not True:
        errors.append("paperops_submit_regression_not_public_safe")
    for key in (
        "live_capital_enabled",
        "phase7_proof_credit_allowed",
        "secret_value_exposed",
        "raw_payload_exposed",
        "raw_broker_payload_exposed",
        "broker_order_identifier_exposed",
    ):
        if artifact.get(key) is not False:
            errors.append(f"paperops_submit_regression_forbidden:{key}")
    for key in (
        "live_endpoint_called_count",
        "broker_post_called_count",
        "broker_write_allowed_count",
    ):
        if _int(artifact.get(key)) != 0:
            errors.append(f"paperops_submit_regression_unsafe_counter_nonzero:{key}")
    blockers = artifact.get("blockers", [])
    if not isinstance(blockers, list):
        errors.append("paperops_submit_regression_blockers_not_list")
        blockers = []
    if _int(artifact.get("blocker_count")) != len(blockers):
        errors.append("paperops_submit_regression_blocker_count_mismatch")
    guarded_metrics = (
        ("source_stale_after_post_tolerance_count", "paperops2_source_artifact_stale_after_submit_artifact"),
        ("fresh_submitted_ledger_collision_count", "fresh_submit_candidate_already_in_idempotency_ledger"),
        ("fresh_submitted_idempotency_missing_count", "paperops2_submitted_fresh_candidate_missing_idempotency_ledger"),
        ("duplicate_misclassified_as_fresh_count", "duplicate_submit_candidate_misclassified_as_fresh"),
        ("fresh_candidate_identity_missing_count", "fresh_submit_candidate_identity_missing"),
        ("fresh_research_goal_lineage_missing_count", "fresh_submit_research_goal_lineage_missing"),
        ("fresh_idempotency_key_missing_count", "fresh_submit_idempotency_key_missing"),
        ("fresh_candidate_identity_collision_count", "fresh_submit_candidate_identity_collision"),
        ("fresh_research_goal_lineage_collision_count", "fresh_submit_research_goal_lineage_collision"),
        ("fresh_idempotency_key_collision_count", "fresh_submit_idempotency_key_collision"),
    )
    for field, blocker in guarded_metrics:
        if _int(artifact.get(field)) > 0 and blocker not in blockers:
            errors.append(f"paperops_submit_regression_unblocked:{field}")
    if artifact.get("idempotency_ledger_active") is not True and (
        "paperops2_idempotency_ledger_inactive" not in blockers
    ):
        errors.append("paperops_submit_regression_idempotency_inactive_unblocked")
    if blockers and artifact.get("status") != "blocked_submit_regression":
        errors.append("paperops_submit_regression_blockers_status_mismatch")
    if not blockers and artifact.get("status") not in PAPEROPS_SUBMIT_REGRESSION_READY_STATUSES:
        errors.append("paperops_submit_regression_ready_status_invalid")
    source_records = artifact.get("source_artifact_records", [])
    if not isinstance(source_records, list):
        errors.append("paperops_submit_regression_source_records_not_list")
    boundary = str(artifact.get("boundary") or "")
    for phrase in (
        "submit-side regression guard",
        "source freshness",
        "idempotency-ledger classification",
        "distinct Research Goal lineage",
        "cannot submit",
        "cannot call live endpoints",
        "cannot enable live capital",
        "cannot grant proof credit",
    ):
        if phrase not in boundary:
            errors.append("paperops_submit_regression_boundary_weak")
            break
    return sorted(set(errors))


def write_paperops_submit_regression_guard(
    artifact: dict[str, Any],
    settings: Settings | None = None,
    *,
    record_event: bool = True,
    event_log_path: str | Path | None = None,
) -> tuple[Path, Path, Path, dict[str, Any]]:
    settings = settings or Settings.from_env()
    output_path, history_path, default_event_path = paperops_submit_regression_guard_paths(
        settings
    )
    event_path = Path(event_log_path or default_event_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    written = deepcopy(artifact)
    written["recorded"] = True
    written["runtime_artifact_path"] = str(output_path)
    written["history_log_path"] = str(history_path)
    if record_event:
        event = EventLog(event_path, echo=False).write(
            PAPEROPS_SUBMIT_REGRESSION_EVENT_TYPE,
            PAPEROPS_SUBMIT_REGRESSION_COMPONENT,
            payload={
                "status": written.get("status"),
                "fresh_eligible_submit_record_count": written.get(
                    "fresh_eligible_submit_record_count"
                ),
                "duplicate_submit_record_count": written.get(
                    "duplicate_submit_record_count"
                ),
                "fresh_submitted_ledger_collision_count": written.get(
                    "fresh_submitted_ledger_collision_count"
                ),
                "duplicate_misclassified_as_fresh_count": written.get(
                    "duplicate_misclassified_as_fresh_count"
                ),
                "blocker_count": written.get("blocker_count"),
                "live_endpoint_called_count": written.get("live_endpoint_called_count"),
                "broker_post_called_count": written.get("broker_post_called_count"),
                "live_capital_enabled": written.get("live_capital_enabled"),
            },
        )
        written["event_log_written"] = True
        written["event_log_path"] = str(event_path)
        written["event_log_event_count"] = 1
        written["event_log_correlation_id"] = event.correlation_id
        written["event_log_created_at"] = event.created_at
    written["validation_errors"] = validate_paperops_submit_regression_guard(written)
    written["validation_error_count"] = len(written["validation_errors"])
    if written["validation_errors"]:
        written["status"] = "invalid"
    output_path.write_text(
        json.dumps(written, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    history_record = {
        "schema_version": PAPEROPS_SUBMIT_REGRESSION_SCHEMA_VERSION,
        "artifact_id": written.get("artifact_id"),
        "status": written.get("status"),
        "recorded_at": _now(),
        "fresh_eligible_submit_record_count": written.get(
            "fresh_eligible_submit_record_count"
        ),
        "duplicate_submit_record_count": written.get("duplicate_submit_record_count"),
        "fresh_submitted_ledger_collision_count": written.get(
            "fresh_submitted_ledger_collision_count"
        ),
        "duplicate_misclassified_as_fresh_count": written.get(
            "duplicate_misclassified_as_fresh_count"
        ),
        "blocker_count": written.get("blocker_count"),
        "validation_error_count": written.get("validation_error_count"),
    }
    with history_path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(history_record, sort_keys=True) + "\n")
    return output_path, history_path, event_path, written


def paperops_submit_regression_guard_public_status(
    settings: Settings | None = None,
) -> dict[str, Any]:
    artifact = read_latest_paperops_submit_regression_guard(settings)
    if not artifact:
        return {
            "schema_version": PAPEROPS_SUBMIT_REGRESSION_SCHEMA_VERSION,
            "status": "not_run",
            "public_safe": True,
            "fresh_eligible_submit_record_count": 0,
            "duplicate_submit_record_count": 0,
            "fresh_submitted_ledger_collision_count": 0,
            "duplicate_misclassified_as_fresh_count": 0,
            "source_stale_after_post_tolerance_count": 0,
            "blocker_count": 0,
            "blockers": [],
            "live_endpoint_called_count": 0,
            "broker_post_called_count": 0,
            "broker_write_allowed_count": 0,
            "live_capital_enabled": False,
            "phase7_proof_credit_allowed": False,
            "secret_value_exposed": False,
            "raw_payload_exposed": False,
            "raw_broker_payload_exposed": False,
            "broker_order_identifier_exposed": False,
            "boundary": PAPEROPS_SUBMIT_REGRESSION_BOUNDARY,
        }
    keys = (
        "schema_version",
        "status",
        "public_safe",
        "source_paperops2_status",
        "source_paperops2_generated_at",
        "source_artifact_count",
        "source_stale_after_post_tolerance_count",
        "source_submit_record_count",
        "source_eligible_submit_record_count",
        "fresh_eligible_submit_record_count",
        "duplicate_submit_record_count",
        "submitted_client_order_id_count",
        "submitted_source_idempotency_key_count",
        "idempotency_ledger_active",
        "fresh_submitted_ledger_collision_count",
        "duplicate_misclassified_as_fresh_count",
        "fresh_candidate_identity_missing_count",
        "fresh_research_goal_lineage_missing_count",
        "fresh_idempotency_key_missing_count",
        "fresh_candidate_identity_collision_count",
        "fresh_research_goal_lineage_collision_count",
        "fresh_idempotency_key_collision_count",
        "blockers",
        "blocker_count",
        "next_required_action",
        "live_endpoint_called_count",
        "broker_post_called_count",
        "broker_write_allowed_count",
        "live_capital_enabled",
        "phase7_proof_credit_allowed",
        "secret_value_exposed",
        "raw_payload_exposed",
        "raw_broker_payload_exposed",
        "broker_order_identifier_exposed",
        "boundary",
    )
    return {key: deepcopy(artifact.get(key)) for key in keys}
