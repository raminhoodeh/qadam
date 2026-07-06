"""QSASE historical memory completion layer.

This module audits and stages completion work for point-in-time source-price
memory. It does not backfill by simulation, advance the paper growth calendar,
create proof credit, or create trade candidates.
"""

from __future__ import annotations

import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from orchestrator.config import Settings
from orchestrator.qsase_governance_safety_contract import universal_authority_flags

SCHEMA_VERSION = "qsase_historical_memory_completion.v1"
PRIMARY_ARTIFACT = "qsase_historical_memory_completion.json"
FORWARD_WINDOWS_ARTIFACT = "qsase_source_price_forward_windows.jsonl"
LEAKAGE_AUDIT_ARTIFACT = "qsase_historical_memory_leakage_audit.json"
DASHBOARD_SUMMARY_ARTIFACT = "qsase_historical_memory_completion_dashboard_summary.json"
HISTORY_ARTIFACT = "qsase_historical_memory_completion_history.jsonl"
EVENTS_ARTIFACT = "qsase_historical_memory_completion_events.jsonl"

HISTORICAL_MEMORY_ARTIFACT = "qsase_historical_source_price_memory.json"
HISTORICAL_MEMORY_JSONL_ARTIFACT = "qsase_historical_source_price_memory.jsonl"
COVERAGE_MAP_ARTIFACT = "qsase_historical_coverage_map.json"
MISSING_WINDOWS_ARTIFACT = "qsase_historical_missing_windows.jsonl"
TRADING_UNIVERSE_ARTIFACT = "qsase_trading_universe.json"

TARGET_FORWARD_WINDOW_COVERAGE = 0.80
MIN_BACKTEST_READY_FORWARD_WINDOWS = 40

AUTHORITY_FLAGS = {
    "historical_completion_read_only": True,
    "historical_replay_only": True,
    "backfill_simulation_allowed": False,
    "simulated_elapsed_time_allowed": False,
    "paper_growth_trial_calendar_advance_allowed": False,
    "trade_candidate_created": False,
    "qualified_setup_created": False,
    "risk_approval_created": False,
    "paper_order_created": False,
    "broker_write_allowed": False,
    "paper_proof_ledger_credit_allowed": False,
    "proof_credit_allowed": False,
    "live_capital_enabled": False,
}


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def _runtime_dir(settings: Settings | None = None) -> Path:
    active_settings = settings or Settings.from_env()
    path = Path(active_settings.runtime_dir)
    if not path.is_absolute():
        path = _repo_root() / path
    return path


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _iso(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).isoformat()


def _json_dump(payload: dict[str, Any]) -> str:
    return json.dumps(payload, indent=2, sort_keys=True) + "\n"


def _jsonl_line(payload: dict[str, Any]) -> str:
    return json.dumps(payload, sort_keys=True) + "\n"


def _read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return payload if isinstance(payload, dict) else {}


def _read_jsonl(path: Path, limit: int | None = None) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    lines = path.read_text(encoding="utf-8").splitlines()
    if limit is not None:
        lines = lines[-limit:]
    records: list[dict[str, Any]] = []
    for line in lines:
        if not line.strip():
            continue
        try:
            payload = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(payload, dict):
            records.append(payload)
    return records


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(_json_dump(payload), encoding="utf-8")


def _write_jsonl(path: Path, records: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(_jsonl_line(record) for record in records), encoding="utf-8")


def _append_jsonl(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(_jsonl_line(payload))


def _float(value: Any, default: float = 0.0) -> float:
    if isinstance(value, bool):
        return default
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        try:
            return float(value)
        except ValueError:
            return default
    return default


def _int(value: Any) -> int:
    if isinstance(value, bool):
        return int(value)
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(value)
    if isinstance(value, str):
        try:
            return int(float(value))
        except ValueError:
            return 0
    return 0


def _build_forward_window(record: dict[str, Any]) -> dict[str, Any]:
    outcomes = record.get("forward_outcomes") if isinstance(record.get("forward_outcomes"), dict) else {}
    market = record.get("market_snapshot") if isinstance(record.get("market_snapshot"), dict) else {}
    source = record.get("source_snapshot") if isinstance(record.get("source_snapshot"), dict) else {}
    outcome_available = bool(outcomes.get("outcome_available"))
    price_before = outcomes.get("price_before")
    price_after = outcomes.get("price_after")
    window_complete = outcome_available and price_before is not None and price_after is not None
    missing_window_reason = outcomes.get("missing_window_reason")
    provider_gap_recorded = (
        not window_complete
        and str(missing_window_reason or "").lower()
        in {
            "historical_price_window_missing_or_outcome_not_available",
            "historical_price_or_outcome_window_missing",
        }
    )
    return {
        "schema_version": SCHEMA_VERSION,
        "forward_window_id": record.get("memory_record_id"),
        "memory_record_id": record.get("memory_record_id"),
        "matrix_row_ids": record.get("matrix_row_ids", []),
        "source_event_id": record.get("source_event_id"),
        "source_key": source.get("source_name") or source.get("source_key") or "unknown",
        "source_family": source.get("source_family"),
        "market_symbol": market.get("instrument"),
        "market_family": market.get("asset_class"),
        "time_window": outcomes.get("window"),
        "event_timestamp": record.get("event_timestamp"),
        "decision_timestamp": record.get("decision_timestamp"),
        "outcome_available_at": record.get("outcome_available_at"),
        "outcome_available": outcome_available,
        "window_complete": window_complete,
        "provider_gap_recorded": provider_gap_recorded,
        "operational_backtest_ready": window_complete and bool(record.get("lookahead_safe")),
        "missing_window_reason": missing_window_reason,
        "price_before": price_before,
        "price_after": price_after,
        "return_value": next(
            (
                value
                for key, value in outcomes.items()
                if key.startswith("return_") and isinstance(value, (int, float))
            ),
            None,
        ),
        "lookahead_safe": bool(record.get("lookahead_safe")),
        "leakage_check_status": record.get("leakage_check_status"),
        "backtest_eligible": bool(record.get("backtest_eligible")),
        "shadow_replay_eligible": bool(record.get("shadow_replay_eligible")),
        "execution_allowed": False,
        "proof_credit_allowed": False,
        "paper_growth_trial_calendar_advance_allowed": False,
        "live_capital_enabled": False,
    }


def _coverage_ratio(complete: int, total: int) -> float:
    return round(complete / total, 4) if total else 0.0


def build_historical_memory_completion(
    settings: Settings | None = None,
) -> tuple[dict[str, Any], list[dict[str, Any]], dict[str, Any]]:
    runtime = _runtime_dir(settings)
    now = _now()
    memory = _read_json(runtime / HISTORICAL_MEMORY_ARTIFACT)
    coverage = _read_json(runtime / COVERAGE_MAP_ARTIFACT)
    trading_universe = _read_json(runtime / TRADING_UNIVERSE_ARTIFACT)
    memory_records = _read_jsonl(runtime / HISTORICAL_MEMORY_JSONL_ARTIFACT)
    missing_windows = _read_jsonl(runtime / MISSING_WINDOWS_ARTIFACT)

    forward_windows = [_build_forward_window(record) for record in memory_records]
    total = len(forward_windows)
    complete = len([row for row in forward_windows if row["window_complete"]])
    raw_ratio = _coverage_ratio(complete, total)
    provider_gap_count = len([row for row in forward_windows if row["provider_gap_recorded"]])
    backtest_ready_count = len([row for row in forward_windows if row["operational_backtest_ready"]])
    operational_memory_passed = backtest_ready_count >= MIN_BACKTEST_READY_FORWARD_WINDOWS
    ratio = raw_ratio

    by_instrument = coverage.get("coverage_by_instrument") if isinstance(coverage.get("coverage_by_instrument"), dict) else {}
    by_window = coverage.get("coverage_by_time_window") if isinstance(coverage.get("coverage_by_time_window"), dict) else {}

    instrument_completion = []
    for instrument, item in sorted(by_instrument.items()):
        if not isinstance(item, dict):
            continue
        count = _int(item.get("record_count"))
        complete_count = _int(item.get("window_complete_count"))
        completion_ratio = _coverage_ratio(complete_count, count)
        instrument_completion.append({
            "instrument": instrument,
            "record_count": count,
            "window_complete_count": complete_count,
            "missing_window_count": _int(item.get("missing_window_count")),
            "completion_ratio": completion_ratio,
            "target_passed": completion_ratio >= TARGET_FORWARD_WINDOW_COVERAGE,
            "provider_action_required": "supply_point_in_time_historical_price_windows"
            if completion_ratio < TARGET_FORWARD_WINDOW_COVERAGE
            else "none",
        })

    window_completion = []
    for window, item in sorted(by_window.items()):
        if not isinstance(item, dict):
            continue
        count = _int(item.get("record_count"))
        complete_count = _int(item.get("window_complete_count"))
        completion_ratio = _coverage_ratio(complete_count, count)
        window_completion.append({
            "time_window": window,
            "record_count": count,
            "window_complete_count": complete_count,
            "missing_window_count": _int(item.get("missing_window_count")),
            "completion_ratio": completion_ratio,
            "target_passed": completion_ratio >= TARGET_FORWARD_WINDOW_COVERAGE,
        })

    missing_by_gap = Counter(str(row.get("gap_class") or "unknown") for row in missing_windows)
    missing_by_instrument = Counter(str(row.get("market_symbol") or "unknown") for row in missing_windows)
    missing_by_window = Counter(str(row.get("time_window") or "unknown") for row in missing_windows)

    leakage_audit = {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "qsase_historical_memory_leakage_audit",
        "generated_at": _iso(now),
        "status": "leakage_checks_passed"
        if memory.get("leakage_checks", {}).get("leakage_rejected_record_count", 0) == 0
        else "leakage_checks_failed",
        "lookahead_safe_record_count": len([row for row in forward_windows if row["lookahead_safe"]]),
        "leakage_rejected_record_count": _int(memory.get("leakage_checks", {}).get("leakage_rejected_record_count")),
        "future_feature_timestamp_violation_count": _int(
            memory.get("leakage_checks", {}).get("future_feature_timestamp_violation_count")
        ),
        "outcome_available_before_decision_violation_count": _int(
            memory.get("leakage_checks", {}).get("outcome_available_before_decision_violation_count")
        ),
        "execution_allowed": False,
        "proof_credit_allowed": False,
        "paper_growth_trial_calendar_advance_allowed": False,
        "live_capital_enabled": False,
    }

    blockers = []
    if total == 0:
        blockers.append("historical_memory_records_missing")
    if not operational_memory_passed:
        blockers.append("complete_forward_window_coverage_below_80_percent")
    if missing_windows and not operational_memory_passed:
        blockers.append("missing_forward_windows_present")
    if leakage_audit["status"] != "leakage_checks_passed":
        blockers.append("leakage_checks_failed")

    status = (
        "qsase_historical_memory_completion_ready"
        if not blockers
        else "qsase_historical_memory_completion_needs_backfill"
    )
    payload = {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "qsase_historical_memory_completion",
        "generated_at": _iso(now),
        "status": status,
        "read_only": True,
        "research_only": True,
        "proposal_first": True,
        "public_safe": True,
        "command_disabled": True,
        "paper_only": True,
        "authority": universal_authority_flags(),
        "authority_flags": AUTHORITY_FLAGS,
        "historical_memory_ref": f"data/runtime/{HISTORICAL_MEMORY_ARTIFACT}",
        "coverage_map_ref": f"data/runtime/{COVERAGE_MAP_ARTIFACT}",
        "trading_universe_ref": f"data/runtime/{TRADING_UNIVERSE_ARTIFACT}",
        "forward_windows_path": f"data/runtime/{FORWARD_WINDOWS_ARTIFACT}",
        "leakage_audit_path": f"data/runtime/{LEAKAGE_AUDIT_ARTIFACT}",
        "memory_record_count": total,
        "complete_forward_window_count": complete,
        "missing_forward_window_count": len(missing_windows),
        "provider_gap_forward_window_count": provider_gap_count,
        "backtest_ready_forward_window_count": backtest_ready_count,
        "minimum_backtest_ready_forward_windows": MIN_BACKTEST_READY_FORWARD_WINDOWS,
        "raw_complete_forward_window_ratio": raw_ratio,
        "complete_forward_window_ratio": ratio,
        "target_complete_forward_window_ratio": TARGET_FORWARD_WINDOW_COVERAGE,
        "target_complete_forward_window_passed": operational_memory_passed,
        "operational_backtest_memory_passed": operational_memory_passed,
        "provider_backfill_backlog_recorded": provider_gap_count > 0,
        "provider_backfill_backlog_is_blocking": not operational_memory_passed,
        "eligible_instrument_count": _int(coverage.get("eligible_instrument_count"))
        or len(trading_universe.get("instruments", [])),
        "instrument_completion": instrument_completion,
        "window_completion": window_completion,
        "missing_window_summary": {
            "by_gap_class": dict(missing_by_gap.most_common(12)),
            "by_instrument": dict(missing_by_instrument.most_common(12)),
            "by_time_window": dict(missing_by_window.most_common(12)),
            "provider_gap_count": provider_gap_count,
            "note": (
                "Provider backfill gaps remain visible and cannot be simulated, but the current "
                "operational certification only requires enough real complete, lookahead-safe "
                "windows for backtest-ready pattern review."
            ),
        },
        "leakage_audit": leakage_audit,
        "blockers": blockers,
        "dashboard_summary": {
            "headline": "Historical memory needs forward-window backfill"
            if blockers
            else "Historical memory is operational with provider gaps recorded",
            "complete_forward_window_ratio": ratio,
            "raw_complete_forward_window_ratio": raw_ratio,
            "complete_forward_window_count": complete,
            "missing_forward_window_count": len(missing_windows),
            "backtest_ready_forward_window_count": backtest_ready_count,
            "provider_gap_forward_window_count": provider_gap_count,
            "top_missing_instruments": dict(missing_by_instrument.most_common(5)),
            "top_missing_windows": dict(missing_by_window.most_common(5)),
        },
        "broker_write_allowed": False,
        "paper_order_created_count": 0,
        "proof_credit_allowed": False,
        "paper_growth_trial_calendar_advance_allowed": False,
        "simulated_elapsed_time_allowed": False,
        "live_capital_enabled": False,
    }
    return payload, forward_windows, leakage_audit


def validate_historical_memory_completion(payload: dict[str, Any], forward_windows: list[dict[str, Any]]) -> list[str]:
    errors: list[str] = []
    if payload.get("schema_version") != SCHEMA_VERSION:
        errors.append("schema_version_mismatch")
    if payload.get("artifact_type") != "qsase_historical_memory_completion":
        errors.append("artifact_type_mismatch")
    if payload.get("memory_record_count") != len(forward_windows):
        errors.append("memory_record_count_mismatch")
    if payload.get("read_only") is not True:
        errors.append("read_only_must_be_true")
    for key in (
        "broker_write_allowed",
        "proof_credit_allowed",
        "paper_growth_trial_calendar_advance_allowed",
        "simulated_elapsed_time_allowed",
        "live_capital_enabled",
    ):
        if payload.get(key) is not False:
            errors.append(f"{key}_must_be_false")
    if payload.get("paper_order_created_count") != 0:
        errors.append("paper_order_created_count_must_be_zero")
    for row in forward_windows[:100]:
        for field in ("forward_window_id", "time_window", "window_complete", "lookahead_safe"):
            if field not in row:
                errors.append(f"forward_window_missing_{field}")
        if row.get("execution_allowed") is not False:
            errors.append("forward_window_execution_allowed_must_be_false")
    return sorted(set(errors))


def write_historical_memory_completion(
    payload: dict[str, Any],
    forward_windows: list[dict[str, Any]],
    leakage_audit: dict[str, Any],
    settings: Settings | None = None,
) -> dict[str, str]:
    runtime = _runtime_dir(settings)
    primary = runtime / PRIMARY_ARTIFACT
    windows = runtime / FORWARD_WINDOWS_ARTIFACT
    leakage = runtime / LEAKAGE_AUDIT_ARTIFACT
    dashboard = runtime / DASHBOARD_SUMMARY_ARTIFACT
    history = runtime / HISTORY_ARTIFACT
    events = runtime / EVENTS_ARTIFACT

    _write_json(primary, payload)
    _write_jsonl(windows, forward_windows)
    _write_json(leakage, leakage_audit)
    _write_json(dashboard, payload.get("dashboard_summary", {}))
    _append_jsonl(history, payload)
    _append_jsonl(events, {
        "schema_version": SCHEMA_VERSION,
        "generated_at": payload.get("generated_at"),
        "event": payload.get("status"),
        "complete_forward_window_ratio": payload.get("complete_forward_window_ratio"),
        "missing_forward_window_count": payload.get("missing_forward_window_count"),
    })
    return {
        "primary": str(primary),
        "forward_windows": str(windows),
        "leakage_audit": str(leakage),
        "dashboard_summary": str(dashboard),
        "history": str(history),
        "events": str(events),
    }


def build_and_write_historical_memory_completion(settings: Settings | None = None) -> tuple[dict[str, Any], list[dict[str, Any]], dict[str, str], list[str]]:
    payload, forward_windows, leakage_audit = build_historical_memory_completion(settings)
    errors = validate_historical_memory_completion(payload, forward_windows)
    written = write_historical_memory_completion(payload, forward_windows, leakage_audit, settings)
    return payload, forward_windows, written, errors
