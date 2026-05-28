"""PaperOps opportunity scan cadence contract.

This layer separates frequent opportunity discovery from guarded paper-order
submission. It can refresh candidate state every 20 minutes, but it cannot
submit, close, resize, approve, or force trades.
"""

from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
import json
from pathlib import Path
import tomllib
from typing import Any

from orchestrator.config import Settings
from orchestrator.event_log import EventLog, EventLogEntry


PAPEROPS_OPPORTUNITY_SCAN_CADENCE_SCHEMA_VERSION = 1
PAPEROPS_OPPORTUNITY_SCAN_CADENCE_RUNTIME_ARTIFACT = (
    "paperops_opportunity_scan_cadence.json"
)
PAPEROPS_OPPORTUNITY_SCAN_CADENCE_HISTORY = (
    "paperops_opportunity_scan_cadence_history.jsonl"
)
PAPEROPS_OPPORTUNITY_SCAN_CADENCE_EVENT_LOG = (
    "paperops_opportunity_scan_cadence_events.jsonl"
)
PAPEROPS_OPPORTUNITY_SCAN_CADENCE_EVENT_TYPE = (
    "paperops_opportunity_scan_cadence_recorded"
)
PAPEROPS_OPPORTUNITY_SCAN_CADENCE_COMPONENT = "paperops_opportunity_scan_cadence"

PAPEROPS_30_DAY_AUTOMATION_ID = "qadam-phase-7-demo-proof-runner"
OPPORTUNITY_SCAN_INTERVAL_MINUTES = 20
MODEL_REVIEW_INTERVAL_MINUTES = 60
PAPER_SUBMIT_RUNNER_INTERVAL_MINUTES = 60
PAPER_LIFECYCLE_POLL_INTERVAL_MINUTES = 10

PAPEROPS_OPPORTUNITY_SCAN_CADENCE_PUBLIC_FIELDS: tuple[str, ...] = (
    "schema_version",
    "artifact_type",
    "artifact_id",
    "phase",
    "stage",
    "status",
    "generated_at",
    "public_safe",
    "opportunity_scan_interval_minutes",
    "opportunity_scan_frequency_per_hour",
    "model_review_interval_minutes",
    "paper_submit_runner_interval_minutes",
    "paper_lifecycle_poll_interval_minutes",
    "phase7_calendar_proof_cadence",
    "scan_contract_state",
    "twenty_minute_scan_ready",
    "twenty_minute_recurring_scheduler_active",
    "recurring_scheduler_status",
    "codex_cron_minute_interval_supported",
    "external_scheduler_required_for_twenty_minute_loop",
    "local_scheduler_command_ready",
    "hourly_paperops_runner_status",
    "hourly_paperops_runner_active",
    "hourly_paperops_runner_rrule",
    "hourly_paperops_runner_preserved",
    "candidate_refresh_allowed",
    "model_inference_required_for_every_scan",
    "trade_submission_cadence",
    "trade_submission_allowed_by_scan",
    "fresh_eligible_submit_count",
    "duplicate_submit_count",
    "production_qualified_setup_count",
    "observed_trade_candidate_count",
    "submitted_paper_order_count",
    "open_position_count",
    "closed_paper_trade_count",
    "postmortem_due_count",
    "escalation_to_hourly_runner_recommended",
    "escalation_reason",
    "forced_trades_allowed",
    "broker_post_called_count",
    "alpaca_post_called_count",
    "live_endpoint_called_count",
    "live_capital_enabled",
    "phase7_proof_credit_allowed",
    "broker_write_allowed_count",
    "unsafe_write_counter_total",
    "recommended_next_action",
    "boundary",
)

PAPEROPS_OPPORTUNITY_SCAN_CADENCE_BOUNDARY = (
    "PaperOps opportunity scanning is a read-only candidate refresh cadence. "
    "It may inspect source observations, shadow intelligence, staged candidates, "
    "paper-account mirrors, and gating artifacts every 20 minutes, but it cannot "
    "submit broker orders, cannot close or resize positions, cannot force trades, "
    "cannot bypass model, Signal Integrity, Risk, Execution Policy, Q-CTRL, "
    "idempotency, or paper receipt gates, cannot call live endpoints, cannot "
    "enable live capital, and cannot grant Phase 7 proof credit. The hourly "
    "PaperOps runner remains the guarded submission transport."
)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _runtime_dir(settings: Settings | None = None) -> Path:
    return Path((settings or Settings.from_env()).runtime_dir)


def _repo_root(settings: Settings | None = None) -> Path:
    return _runtime_dir(settings).parent.parent


def _read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    payload = json.loads(path.read_text(encoding="utf-8"))
    return payload if isinstance(payload, dict) else {}


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    records: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            payload = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(payload, dict):
            records.append(payload)
    return records


def _int(value: Any) -> int:
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0


def _safe_bool(value: Any) -> bool:
    return value is True or str(value).strip().lower() in {"1", "true", "yes", "on"}


def paperops_opportunity_scan_cadence_paths(
    settings: Settings | None = None,
) -> tuple[Path, Path, Path]:
    runtime = _runtime_dir(settings)
    return (
        runtime / PAPEROPS_OPPORTUNITY_SCAN_CADENCE_RUNTIME_ARTIFACT,
        runtime / PAPEROPS_OPPORTUNITY_SCAN_CADENCE_HISTORY,
        runtime / PAPEROPS_OPPORTUNITY_SCAN_CADENCE_EVENT_LOG,
    )


def read_latest_paperops_opportunity_scan_cadence(
    settings: Settings | None = None,
) -> dict[str, Any]:
    output_path, _, _ = paperops_opportunity_scan_cadence_paths(settings)
    return _read_json(output_path)


def _automation_path() -> Path:
    return (
        Path.home()
        / ".codex"
        / "automations"
        / PAPEROPS_30_DAY_AUTOMATION_ID
        / "automation.toml"
    )


def _automation_config() -> dict[str, Any]:
    path = _automation_path()
    if not path.exists():
        return {
            "present": False,
            "id": PAPEROPS_30_DAY_AUTOMATION_ID,
            "status": "missing",
            "kind": "missing",
            "rrule": "",
            "cwds": [],
        }
    with path.open("rb") as handle:
        payload = tomllib.load(handle)
    payload["present"] = True
    return payload


def _hourly_runner_status(settings: Settings) -> dict[str, Any]:
    automation = _automation_config()
    cwds = automation.get("cwds") or []
    if isinstance(cwds, str):
        cwds = [cwds]
    rrule = str(automation.get("rrule") or "")
    active = (
        automation.get("present") is True
        and automation.get("status") == "ACTIVE"
        and automation.get("kind") == "cron"
        and rrule == "FREQ=HOURLY;INTERVAL=1"
        and str(_repo_root(settings).resolve()) in [str(item) for item in cwds]
    )
    return {
        "hourly_paperops_runner_status": str(automation.get("status") or "missing"),
        "hourly_paperops_runner_active": active,
        "hourly_paperops_runner_rrule": rrule,
        "hourly_paperops_runner_preserved": rrule == "FREQ=HOURLY;INTERVAL=1",
    }


def _source_snapshot(settings: Settings) -> dict[str, Any]:
    runtime = _runtime_dir(settings)
    return {
        "active_automation": _read_json(
            runtime / "paperops_active_paper_trading_automation.json"
        ),
        "qualified_setup_production": _read_json(
            runtime / "paperops_qualified_setup_production.json"
        ),
        "auto_approval": _read_json(runtime / "paperops_auto_approval_staged_order.json"),
        "paperops_30_day": _read_json(runtime / "paperops_30_day_operations.json"),
        "paper_post": _read_json(runtime / "paperops_alpaca_paper_post.json"),
        "paper_lifecycle": _read_json(
            runtime / "paperops_paper_lifecycle_poller.json"
        ),
        "paper_live_certification": _read_json(runtime / "paper_live_certification.json"),
        "phase7_demo": _read_json(runtime / "phase7_demo_proof_run.json"),
        "trade_candidates": _read_jsonl(runtime / "trade_candidates.jsonl"),
        "paper_orders": _read_jsonl(runtime / "paper_orders.jsonl"),
        "paper_positions": _read_jsonl(runtime / "paper_positions.jsonl"),
        "paper_closed_trades": _read_jsonl(runtime / "paper_closed_trades.jsonl"),
    }


def _recommended_next_action(artifact: dict[str, Any]) -> str:
    if artifact.get("fresh_eligible_submit_count", 0) > 0:
        return (
            "Let the preserved hourly PaperOps runner process the fresh eligible "
            "paper order through the guarded submit path"
        )
    if artifact.get("production_qualified_setup_count", 0) > 0:
        return (
            "Use the 20-minute scanner to keep the qualified setup fresh, then "
            "allow the hourly runner to submit only if the fresh-order gate passes"
        )
    if artifact.get("observed_trade_candidate_count", 0) > 0:
        return (
            "Refresh candidate evidence every 20 minutes and escalate only if "
            "Signal Integrity, Risk, Execution Policy, Q-CTRL, and idempotency "
            "state remain clean"
        )
    return (
        "Run the read-only opportunity scanner every 20 minutes while keeping "
        "model review and paper submission on guarded hourly/event-gated paths"
    )


def build_paperops_opportunity_scan_cadence(
    settings: Settings | None = None,
) -> dict[str, Any]:
    settings = settings or Settings.from_env()
    generated_at = _now()
    snapshot = _source_snapshot(settings)
    active_automation = snapshot["active_automation"]
    qualified_setup = snapshot["qualified_setup_production"]
    paperops_30_day = snapshot["paperops_30_day"]
    paper_live = snapshot["paper_live_certification"]
    phase7_demo = snapshot["phase7_demo"]
    paper_lifecycle = snapshot["paper_lifecycle"]
    hourly_runner = _hourly_runner_status(settings)

    fresh_submit_count = _int(
        active_automation.get("paperops2_fresh_eligible_submit_record_count")
        or paperops_30_day.get("paperops_active_paper_trading_fresh_submit_count")
    )
    duplicate_submit_count = _int(
        active_automation.get("paperops2_duplicate_submit_record_count")
        or paperops_30_day.get("paperops_active_paper_trading_duplicate_submit_count")
    )
    qualified_count = _int(qualified_setup.get("qualified_setup_count"))
    observed_candidate_count = max(
        len(snapshot["trade_candidates"]),
        _int(qualified_setup.get("production_candidate_count")),
    )
    submitted_order_count = max(
        _int(active_automation.get("submitted_paper_order_count")),
        _int(paperops_30_day.get("submitted_paper_order_count")),
        len(snapshot["paper_orders"]),
    )
    open_position_count = max(
        _int(paper_lifecycle.get("open_position_count")),
        len(snapshot["paper_positions"]),
    )
    closed_trade_count = max(
        _int(paper_lifecycle.get("closed_paper_trade_count")),
        _int(paperops_30_day.get("closed_proof_trade_count")),
        len(snapshot["paper_closed_trades"]),
    )
    unsafe_total = sum(
        _int(source.get(key))
        for source in (active_automation, paperops_30_day, paper_live, phase7_demo)
        for key in (
            "broker_post_called_count",
            "alpaca_post_called_count",
            "live_endpoint_called_count",
            "live_endpoint_allowed_count",
            "broker_write_allowed_count",
            "unsafe_write_counter_total",
        )
    )
    broker_post_count = sum(
        _int(source.get("broker_post_called_count"))
        for source in (active_automation, paperops_30_day, paper_live, phase7_demo)
    )
    alpaca_post_count = sum(
        _int(source.get("alpaca_post_called_count"))
        for source in (active_automation, paperops_30_day, paper_live, phase7_demo)
    )
    live_endpoint_count = sum(
        _int(source.get("live_endpoint_called_count"))
        + _int(source.get("live_endpoint_allowed_count"))
        for source in (active_automation, paperops_30_day, paper_live, phase7_demo)
    )
    broker_write_count = sum(
        _int(source.get("broker_write_allowed_count"))
        for source in (active_automation, paperops_30_day, paper_live, phase7_demo)
    )

    artifact = {
        "schema_version": PAPEROPS_OPPORTUNITY_SCAN_CADENCE_SCHEMA_VERSION,
        "artifact_type": "paperops_opportunity_scan_cadence",
        "artifact_id": "paperops-opportunity-scan-cadence-v1",
        "phase": "PaperOps",
        "stage": "PaperOps-Opportunity-Scan",
        "status": "scan_ready_no_candidate",
        "generated_at": generated_at,
        "public_safe": True,
        "mode": settings.mode,
        "recorded": False,
        "event_log_required": True,
        "event_log_written": False,
        "event_log_event_count": 0,
        "event_log_correlation_id": None,
        "opportunity_scan_interval_minutes": OPPORTUNITY_SCAN_INTERVAL_MINUTES,
        "opportunity_scan_frequency_per_hour": 3,
        "model_review_interval_minutes": MODEL_REVIEW_INTERVAL_MINUTES,
        "paper_submit_runner_interval_minutes": PAPER_SUBMIT_RUNNER_INTERVAL_MINUTES,
        "paper_lifecycle_poll_interval_minutes": PAPER_LIFECYCLE_POLL_INTERVAL_MINUTES,
        "phase7_calendar_proof_cadence": "calendar_preserved_no_backfill",
        "scan_contract_state": "ready",
        "twenty_minute_scan_ready": True,
        "twenty_minute_recurring_scheduler_active": False,
        "recurring_scheduler_status": "local_or_external_scheduler_required",
        "codex_cron_minute_interval_supported": False,
        "external_scheduler_required_for_twenty_minute_loop": True,
        "local_scheduler_command_ready": True,
        **hourly_runner,
        "candidate_refresh_allowed": True,
        "model_inference_required_for_every_scan": False,
        "trade_submission_cadence": (
            "hourly_or_event_gated_guarded_runner_only_after_fresh_order_gate"
        ),
        "trade_submission_allowed_by_scan": False,
        "fresh_eligible_submit_count": fresh_submit_count,
        "duplicate_submit_count": duplicate_submit_count,
        "production_qualified_setup_count": qualified_count,
        "observed_trade_candidate_count": observed_candidate_count,
        "submitted_paper_order_count": submitted_order_count,
        "open_position_count": open_position_count,
        "closed_paper_trade_count": closed_trade_count,
        "postmortem_due_count": _int(paper_lifecycle.get("postmortem_due_count")),
        "escalation_to_hourly_runner_recommended": fresh_submit_count > 0,
        "escalation_reason": (
            "fresh_eligible_paper_order_available"
            if fresh_submit_count > 0
            else "no_fresh_eligible_paper_order"
        ),
        "forced_trades_allowed": False,
        "broker_post_called_count": broker_post_count,
        "alpaca_post_called_count": alpaca_post_count,
        "live_endpoint_called_count": live_endpoint_count,
        "live_capital_enabled": bool(settings.live_capital_enabled),
        "phase7_proof_credit_allowed": _safe_bool(
            phase7_demo.get("phase7_proof_credit_allowed")
        ),
        "broker_write_allowed_count": broker_write_count,
        "unsafe_write_counter_total": unsafe_total,
        "boundary": PAPEROPS_OPPORTUNITY_SCAN_CADENCE_BOUNDARY,
    }
    if fresh_submit_count > 0:
        artifact["status"] = "scan_ready_fresh_submit_pending_hourly_runner"
    elif qualified_count > 0 or observed_candidate_count > 0:
        artifact["status"] = "scan_ready_candidate_monitoring"
    artifact["recommended_next_action"] = _recommended_next_action(artifact)
    artifact["validation_errors"] = validate_paperops_opportunity_scan_cadence(artifact)
    if artifact["validation_errors"]:
        artifact["status"] = "invalid"
    artifact["public_status"] = (
        paperops_opportunity_scan_cadence_public_status_from_artifact(artifact)
    )
    return artifact


def validate_paperops_opportunity_scan_cadence(artifact: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    required = set(PAPEROPS_OPPORTUNITY_SCAN_CADENCE_PUBLIC_FIELDS) | {
        "recorded",
        "event_log_required",
        "event_log_written",
        "event_log_correlation_id",
    }
    missing = sorted(required - set(artifact))
    if missing:
        errors.append(
            "paperops_opportunity_scan_cadence_missing_fields:" + ",".join(missing)
        )
    if artifact.get("schema_version") != PAPEROPS_OPPORTUNITY_SCAN_CADENCE_SCHEMA_VERSION:
        errors.append("paperops_opportunity_scan_cadence_schema_mismatch")
    if artifact.get("artifact_type") != "paperops_opportunity_scan_cadence":
        errors.append("paperops_opportunity_scan_cadence_type_mismatch")
    if artifact.get("phase") != "PaperOps":
        errors.append("paperops_opportunity_scan_cadence_phase_mismatch")
    if artifact.get("public_safe") is not True:
        errors.append("paperops_opportunity_scan_cadence_not_public_safe")
    if artifact.get("mode") != "paper":
        errors.append("paperops_opportunity_scan_cadence_mode_not_paper")
    if artifact.get("opportunity_scan_interval_minutes") != 20:
        errors.append("paperops_opportunity_scan_cadence_interval_not_20_minutes")
    if artifact.get("opportunity_scan_frequency_per_hour") != 3:
        errors.append("paperops_opportunity_scan_cadence_frequency_not_three")
    if _int(artifact.get("model_review_interval_minutes")) < 60:
        errors.append("paperops_opportunity_scan_cadence_model_review_too_fast")
    if _int(artifact.get("paper_submit_runner_interval_minutes")) < 60:
        errors.append("paperops_opportunity_scan_cadence_submit_runner_too_fast")
    if artifact.get("trade_submission_allowed_by_scan") is not False:
        errors.append("paperops_opportunity_scan_cadence_scan_can_submit")
    for key in (
        "forced_trades_allowed",
        "live_capital_enabled",
        "phase7_proof_credit_allowed",
    ):
        if artifact.get(key) is not False:
            errors.append(f"paperops_opportunity_scan_cadence_forbidden:{key}")
    for key in (
        "broker_post_called_count",
        "alpaca_post_called_count",
        "live_endpoint_called_count",
        "broker_write_allowed_count",
        "unsafe_write_counter_total",
    ):
        if _int(artifact.get(key)) != 0:
            errors.append(f"paperops_opportunity_scan_cadence_unsafe_counter:{key}")
    if artifact.get("codex_cron_minute_interval_supported") is not False:
        errors.append("paperops_opportunity_scan_cadence_codex_cron_claims_minutes")
    if artifact.get("hourly_paperops_runner_preserved") is not True:
        errors.append("paperops_opportunity_scan_cadence_hourly_runner_not_preserved")
    if (
        artifact.get("recorded") is True
        and artifact.get("event_log_required") is True
        and artifact.get("event_log_written") is not True
    ):
        errors.append("paperops_opportunity_scan_cadence_event_log_missing")
    if artifact.get("event_log_written") is True:
        if artifact.get("event_log_event_count") != 1:
            errors.append("paperops_opportunity_scan_cadence_event_count_mismatch")
        if not artifact.get("event_log_correlation_id"):
            errors.append("paperops_opportunity_scan_cadence_event_correlation_missing")
    boundary = str(artifact.get("boundary") or "")
    for phrase in (
        "read-only candidate refresh cadence",
        "every 20 minutes",
        "cannot submit broker orders",
        "cannot force trades",
        "cannot call live endpoints",
        "cannot enable live capital",
        "cannot grant Phase 7 proof credit",
        "hourly PaperOps runner remains the guarded submission transport",
    ):
        if phrase not in boundary:
            errors.append("paperops_opportunity_scan_cadence_boundary_weak")
            break
    return sorted(set(errors))


def paperops_opportunity_scan_cadence_public_status_from_artifact(
    artifact: dict[str, Any],
) -> dict[str, Any]:
    public_status = {
        field: deepcopy(artifact.get(field))
        for field in PAPEROPS_OPPORTUNITY_SCAN_CADENCE_PUBLIC_FIELDS
        if field in artifact
    }
    public_status["validation_error_count"] = len(
        artifact.get("validation_errors", []) or []
    )
    public_status["recorded"] = artifact.get("recorded") is True
    public_status["event_log_written"] = artifact.get("event_log_written") is True
    public_status["event_log_event_count"] = artifact.get("event_log_event_count", 0)
    return public_status


def paperops_opportunity_scan_cadence_public_status(
    settings: Settings | None = None,
) -> dict[str, Any]:
    artifact = read_latest_paperops_opportunity_scan_cadence(settings)
    if not artifact:
        return {
            "schema_version": PAPEROPS_OPPORTUNITY_SCAN_CADENCE_SCHEMA_VERSION,
            "status": "not_run",
            "stage": "PaperOps-Opportunity-Scan",
            "public_safe": True,
            "recorded": False,
            "event_log_written": False,
            "event_log_event_count": 0,
            "opportunity_scan_interval_minutes": OPPORTUNITY_SCAN_INTERVAL_MINUTES,
            "opportunity_scan_frequency_per_hour": 3,
            "model_review_interval_minutes": MODEL_REVIEW_INTERVAL_MINUTES,
            "paper_submit_runner_interval_minutes": PAPER_SUBMIT_RUNNER_INTERVAL_MINUTES,
            "paper_lifecycle_poll_interval_minutes": PAPER_LIFECYCLE_POLL_INTERVAL_MINUTES,
            "twenty_minute_scan_ready": False,
            "twenty_minute_recurring_scheduler_active": False,
            "recurring_scheduler_status": "not_run",
            "trade_submission_allowed_by_scan": False,
            "fresh_eligible_submit_count": 0,
            "production_qualified_setup_count": 0,
            "observed_trade_candidate_count": 0,
            "submitted_paper_order_count": 0,
            "open_position_count": 0,
            "closed_paper_trade_count": 0,
            "unsafe_write_counter_total": 0,
            "validation_error_count": 0,
            "boundary": PAPEROPS_OPPORTUNITY_SCAN_CADENCE_BOUNDARY,
        }
    return paperops_opportunity_scan_cadence_public_status_from_artifact(artifact)


def attach_paperops_opportunity_scan_cadence_event_log(
    artifact: dict[str, Any],
    *,
    event_log: EventLog | None = None,
    event_log_path: str | Path | None = None,
    settings: Settings | None = None,
) -> tuple[dict[str, Any], EventLogEntry]:
    output = deepcopy(artifact)
    log_path = Path(
        event_log_path
        or (_runtime_dir(settings) / PAPEROPS_OPPORTUNITY_SCAN_CADENCE_EVENT_LOG)
    )
    log = event_log or EventLog(log_path, echo=False)
    entry = log.write(
        PAPEROPS_OPPORTUNITY_SCAN_CADENCE_EVENT_TYPE,
        PAPEROPS_OPPORTUNITY_SCAN_CADENCE_COMPONENT,
        {
            "status": output.get("status"),
            "opportunity_scan_interval_minutes": output.get(
                "opportunity_scan_interval_minutes"
            ),
            "fresh_eligible_submit_count": output.get("fresh_eligible_submit_count"),
            "production_qualified_setup_count": output.get(
                "production_qualified_setup_count"
            ),
            "observed_trade_candidate_count": output.get(
                "observed_trade_candidate_count"
            ),
            "submitted_paper_order_count": output.get("submitted_paper_order_count"),
            "hourly_paperops_runner_active": output.get(
                "hourly_paperops_runner_active"
            ),
            "twenty_minute_recurring_scheduler_active": output.get(
                "twenty_minute_recurring_scheduler_active"
            ),
            "unsafe_write_counter_total": output.get("unsafe_write_counter_total"),
        },
    )
    output["recorded"] = True
    output["event_log_required"] = True
    output["event_log_written"] = True
    output["event_log_path"] = str(log.path)
    output["event_log_event_count"] = 1
    output["event_log_correlation_id"] = entry.correlation_id
    output["event_log_created_at"] = entry.created_at
    output["validation_errors"] = validate_paperops_opportunity_scan_cadence(output)
    if output["validation_errors"]:
        output["status"] = "invalid"
    output["public_status"] = (
        paperops_opportunity_scan_cadence_public_status_from_artifact(output)
    )
    return output, entry


def write_paperops_opportunity_scan_cadence(
    artifact: dict[str, Any],
    *,
    settings: Settings | None = None,
    record_event: bool = True,
    event_log_path: str | Path | None = None,
) -> tuple[Path, Path, Path, dict[str, Any]]:
    output = deepcopy(artifact)
    output_path, history_path, default_event_path = (
        paperops_opportunity_scan_cadence_paths(settings)
    )
    event_path = Path(event_log_path or default_event_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output.setdefault("event_log_required", True)
    output.setdefault("recorded", False)
    output.setdefault("event_log_written", False)
    output.setdefault("event_log_correlation_id", None)
    if record_event:
        output, _ = attach_paperops_opportunity_scan_cadence_event_log(
            output,
            event_log_path=event_path,
            settings=settings,
        )
    else:
        output["validation_errors"] = validate_paperops_opportunity_scan_cadence(
            output
        )
        output["public_status"] = (
            paperops_opportunity_scan_cadence_public_status_from_artifact(output)
        )
    output["runtime_artifact_path"] = str(output_path)
    output["history_log_path"] = str(history_path)
    output["validation_errors"] = validate_paperops_opportunity_scan_cadence(output)
    if output["validation_errors"]:
        output["status"] = "invalid"
    output["public_status"] = (
        paperops_opportunity_scan_cadence_public_status_from_artifact(output)
    )
    output_path.write_text(
        json.dumps(output, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    history_record = {
        "schema_version": PAPEROPS_OPPORTUNITY_SCAN_CADENCE_SCHEMA_VERSION,
        "artifact_id": output.get("artifact_id"),
        "status": output.get("status"),
        "recorded_at": _now(),
        "opportunity_scan_interval_minutes": output.get(
            "opportunity_scan_interval_minutes"
        ),
        "fresh_eligible_submit_count": output.get("fresh_eligible_submit_count"),
        "production_qualified_setup_count": output.get(
            "production_qualified_setup_count"
        ),
        "observed_trade_candidate_count": output.get("observed_trade_candidate_count"),
        "submitted_paper_order_count": output.get("submitted_paper_order_count"),
        "unsafe_write_counter_total": output.get("unsafe_write_counter_total"),
        "validation_error_count": len(output.get("validation_errors", []) or []),
    }
    with history_path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(history_record, sort_keys=True) + "\n")
    return output_path, history_path, event_path, output
