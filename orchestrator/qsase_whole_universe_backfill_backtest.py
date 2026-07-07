"""Whole-universe historical backfill/backtest baseline for Qadam.

This module implements Phase 1 of the next-generation flow. It is an evidence
foundation only: it classifies the full current source and trading universes,
builds a resumable local baseline from existing point-in-time artifacts, and
records provider gaps explicitly. It cannot create trade candidates, approvals,
orders, broker writes, live-capital authority, or paper proof ledger credit.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path
import statistics
import time
from typing import Any

from orchestrator.config import Settings
from orchestrator.qadam_next_generation_safety_lock import (
    LOCK_ARTIFACT,
    is_long_backtest_lock_active,
    read_long_backtest_lock,
)

SCHEMA_VERSION = 1
ARTIFACT_PREFIX = "qsase_whole_universe_backfill_backtest"

MANIFEST_ARTIFACT = f"{ARTIFACT_PREFIX}_manifest.json"
STATE_ARTIFACT = f"{ARTIFACT_PREFIX}_state.json"
PROGRESS_ARTIFACT = f"{ARTIFACT_PREFIX}_progress.jsonl"
ERRORS_ARTIFACT = f"{ARTIFACT_PREFIX}_errors.jsonl"
SUMMARY_ARTIFACT = f"{ARTIFACT_PREFIX}_summary.json"
DASHBOARD_SUMMARY_ARTIFACT = f"{ARTIFACT_PREFIX}_dashboard_summary.json"

UNIVERSE_FREEZE_ARTIFACT = "qsase_backtest_universe_freeze.json"
PROVIDER_CAPABILITY_ARTIFACT = "qsase_backfill_provider_capability_audit.json"
SOURCE_HISTORY_MANIFEST_ARTIFACT = "qsase_backfill_source_history_manifest.json"
PRICE_HISTORY_MANIFEST_ARTIFACT = "qsase_backfill_price_history_manifest.json"
FORWARD_WINDOW_COMPLETION_ARTIFACT = "qsase_backfill_forward_window_completion.json"
BASELINE_RESULTS_ARTIFACT = "qsase_baseline_backtest_results.jsonl"
BASELINE_REJECTIONS_ARTIFACT = "qsase_baseline_backtest_rejections.jsonl"
BASELINE_EVIDENCE_MAP_ARTIFACT = "qsase_baseline_backtest_evidence_map.json"
BASELINE_STRATEGY_EVIDENCE_MAP_ARTIFACT = "qsase_baseline_strategy_evidence_map.json"
AKBER_BACKTEST_CALIBRATION_ARTIFACT = "qsase_akber_backtest_calibration.json"
BASELINE_SHADOW_ROUTER_MAP_ARTIFACT = "qsase_baseline_shadow_router_map.json"

SOURCE_NETWORK_ARTIFACT = "qsase_dashboard_source_network.json"
SOURCE_UNIVERSE_ARTIFACT = "qsase_source_universe.json"
TRADING_UNIVERSE_ARTIFACT = "qsase_trading_universe.json"
STRATEGY_UNIVERSE_ARTIFACT = "qsase_dashboard_strategy_universe.json"
HISTORICAL_MEMORY_ARTIFACT = "qsase_historical_source_price_memory.json"
HISTORICAL_MEMORY_JSONL_ARTIFACT = "qsase_historical_source_price_memory.jsonl"
MISSING_WINDOWS_ARTIFACT = "qsase_historical_missing_windows.jsonl"
PAPEROPS_SUMMARY_ARTIFACT = "paperops_autonomous_pass_summary.json"

MIN_BASELINE_SAMPLE_COUNT = 3

AUTHORITY_FLAGS = {
    "read_only": True,
    "paper_only": True,
    "proposal_first": True,
    "trade_candidate_creation_allowed": False,
    "risk_approval_allowed": False,
    "execution_allowed": False,
    "paper_order_allowed": False,
    "broker_write_allowed": False,
    "live_capital_enabled": False,
    "proof_credit_allowed": False,
    "paper_growth_trial_calendar_advance_allowed": False,
    "simulated_elapsed_time_allowed": False,
    "telegram_command_path_enabled": False,
}

FORBIDDEN_TRUE_FLAGS = tuple(
    key for key, value in AUTHORITY_FLAGS.items() if value is False
)

PROVIDER_CLASSES_BY_FAMILY = {
    "conflict": "geopolitics",
    "physical": "physical_world",
    "macro": "macro",
    "market": "market_prices",
    "market_context_taxonomy": "technical_order_flow",
    "social": "social_narrative",
    "prediction_markets": "prediction_markets",
}


@dataclass(frozen=True)
class RunnerOptions:
    dry_run: bool = False
    resume: bool = False
    max_runtime_hours: float = 120.0
    batch_limit: int | None = None
    sources: tuple[str, ...] = ()
    instruments: tuple[str, ...] = ()
    from_date: str | None = None
    to_date: str | None = None
    max_provider_calls: int = 0
    sleep_between_calls: float = 0.0
    network_disabled: bool = True
    paperops_paused_required: bool = True


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


def _iso(dt: datetime | None = None) -> str:
    return (dt or _now()).astimezone(timezone.utc).isoformat()


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
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError:
        return []
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


def _hash_id(parts: list[Any], prefix: str) -> str:
    raw = "|".join(str(part) for part in parts)
    return f"{prefix}:{hashlib.sha256(raw.encode('utf-8')).hexdigest()[:20]}"


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


def _float(value: Any) -> float | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        try:
            return float(value)
        except ValueError:
            return None
    return None


def _safe_list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def _artifact_ref(filename: str, pointer: str | None = None) -> str:
    base = f"data/runtime/{filename}"
    return f"{base}#{pointer}" if pointer else base


def _paths(settings: Settings | None = None) -> dict[str, Path]:
    runtime = _runtime_dir(settings)
    return {
        "manifest": runtime / MANIFEST_ARTIFACT,
        "state": runtime / STATE_ARTIFACT,
        "progress": runtime / PROGRESS_ARTIFACT,
        "errors": runtime / ERRORS_ARTIFACT,
        "summary": runtime / SUMMARY_ARTIFACT,
        "dashboard_summary": runtime / DASHBOARD_SUMMARY_ARTIFACT,
        "universe_freeze": runtime / UNIVERSE_FREEZE_ARTIFACT,
        "provider_capability": runtime / PROVIDER_CAPABILITY_ARTIFACT,
        "source_history_manifest": runtime / SOURCE_HISTORY_MANIFEST_ARTIFACT,
        "price_history_manifest": runtime / PRICE_HISTORY_MANIFEST_ARTIFACT,
        "forward_window_completion": runtime / FORWARD_WINDOW_COMPLETION_ARTIFACT,
        "baseline_results": runtime / BASELINE_RESULTS_ARTIFACT,
        "baseline_rejections": runtime / BASELINE_REJECTIONS_ARTIFACT,
        "baseline_evidence_map": runtime / BASELINE_EVIDENCE_MAP_ARTIFACT,
        "baseline_strategy_evidence_map": runtime / BASELINE_STRATEGY_EVIDENCE_MAP_ARTIFACT,
        "akber_backtest_calibration": runtime / AKBER_BACKTEST_CALIBRATION_ARTIFACT,
        "baseline_shadow_router_map": runtime / BASELINE_SHADOW_ROUTER_MAP_ARTIFACT,
    }


def _load_context(settings: Settings | None = None) -> dict[str, Any]:
    runtime = _runtime_dir(settings)
    return {
        "runtime_dir": runtime,
        "source_network": _read_json(runtime / SOURCE_NETWORK_ARTIFACT),
        "source_universe": _read_json(runtime / SOURCE_UNIVERSE_ARTIFACT),
        "trading_universe": _read_json(runtime / TRADING_UNIVERSE_ARTIFACT),
        "strategy_universe": _read_json(runtime / STRATEGY_UNIVERSE_ARTIFACT),
        "historical_memory": _read_json(runtime / HISTORICAL_MEMORY_ARTIFACT),
        "memory_records": _read_jsonl(runtime / HISTORICAL_MEMORY_JSONL_ARTIFACT),
        "missing_windows": _read_jsonl(runtime / MISSING_WINDOWS_ARTIFACT),
        "paperops_summary": _read_json(runtime / PAPEROPS_SUMMARY_ARTIFACT),
        "lock": read_long_backtest_lock(settings),
    }


def _return_from_record(record: dict[str, Any]) -> float | None:
    outcomes = record.get("forward_outcomes")
    if not isinstance(outcomes, dict):
        return None
    for key, value in outcomes.items():
        if key.startswith("return_") and value is not None:
            return _float(value)
    return None


def _source_key(record: dict[str, Any]) -> str:
    return str(record.get("source_snapshot", {}).get("source_name") or "unknown")


def _source_family(record: dict[str, Any]) -> str:
    return str(record.get("source_snapshot", {}).get("source_family") or "unknown")


def _instrument(record: dict[str, Any]) -> str:
    return str(record.get("market_snapshot", {}).get("instrument") or "unknown")


def _market_family(record: dict[str, Any]) -> str:
    return str(record.get("market_snapshot", {}).get("asset_class") or "unknown")


def _window(record: dict[str, Any]) -> str:
    return str(record.get("forward_outcomes", {}).get("window") or "unknown")


def _selected(value: str, requested: tuple[str, ...]) -> bool:
    if not requested or "all" in requested:
        return True
    lowered = {item.lower() for item in requested}
    return value.lower() in lowered


def _memory_counts(records: list[dict[str, Any]], key_fn) -> dict[str, dict[str, int]]:
    counts: dict[str, dict[str, int]] = defaultdict(lambda: {"record_count": 0, "complete_window_count": 0, "missing_window_count": 0})
    for record in records:
        key = key_fn(record)
        counts[key]["record_count"] += 1
        if record.get("backtest_eligible") is True and _return_from_record(record) is not None:
            counts[key]["complete_window_count"] += 1
        else:
            counts[key]["missing_window_count"] += 1
    return dict(counts)


def _strategy_by_symbol(strategy_universe: dict[str, Any]) -> dict[str, list[dict[str, Any]]]:
    mapping: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for strategy in _safe_list(strategy_universe.get("all_strategy_rows")):
        for market in _safe_list(strategy.get("watched_markets")):
            symbol = str(market.get("symbol") or "").upper()
            if symbol:
                mapping[symbol].append(strategy)
    return dict(mapping)


def _authority() -> dict[str, Any]:
    return dict(AUTHORITY_FLAGS)


def _mark_lock_phase1_started(settings: Settings | None = None) -> dict[str, Any]:
    runtime = _runtime_dir(settings)
    lock_path = runtime / LOCK_ARTIFACT
    lock = _read_json(lock_path)
    if not is_long_backtest_lock_active(lock):
        return lock
    lock["phase_1_backfill_started"] = True
    lock["phase_1_started_at"] = lock.get("phase_1_started_at") or _iso()
    lock["reason"] = "whole-universe historical backfill/backtest baseline in progress"
    lock["paperops_watch_only_mode"] = True
    lock["paper_order_allowed"] = False
    lock["broker_write_allowed"] = False
    lock["live_capital_enabled"] = False
    lock["proof_credit_allowed"] = False
    _write_json(lock_path, lock)
    return lock


def build_preflight(settings: Settings | None = None) -> dict[str, Any]:
    context = _load_context(settings)
    source_rows = _safe_list(context["source_network"].get("source_rows"))
    instrument_rows = _safe_list(context["source_network"].get("trading_universe_rows"))
    memory_records = _safe_list(context.get("memory_records"))
    lock = context.get("lock", {})
    errors: list[str] = []
    if not is_long_backtest_lock_active(lock):
        errors.append("long_backtest_lock_not_active")
    if len(source_rows) < 1:
        errors.append("source_rows_missing")
    if len(instrument_rows) < 1:
        errors.append("trading_universe_rows_missing")
    if len(memory_records) < 1:
        errors.append("historical_memory_records_missing")
    return {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "qsase_whole_universe_backfill_backtest_preflight",
        "generated_at": _iso(),
        "status": "preflight_passed" if not errors else "preflight_blocked",
        "source_row_count": len(source_rows),
        "watched_instrument_count": len(instrument_rows),
        "memory_record_count": len(memory_records),
        "long_backtest_lock_active": is_long_backtest_lock_active(lock),
        "paperops_watch_only_mode": lock.get("paperops_watch_only_mode") is True,
        "phase_1_backfill_started": lock.get("phase_1_backfill_started") is True,
        "errors": errors,
        "error_count": len(errors),
        "authority": _authority(),
    }


def build_manifest(context: dict[str, Any], options: RunnerOptions) -> dict[str, Any]:
    source_rows = [
        row for row in _safe_list(context["source_network"].get("source_rows"))
        if _selected(str(row.get("source_key") or ""), options.sources)
    ]
    instrument_rows = [
        row for row in _safe_list(context["source_network"].get("trading_universe_rows"))
        if _selected(str(row.get("symbol") or ""), options.instruments)
    ]
    jobs = [
        {
            "job_id": "phase1:universe_freeze",
            "phase": "universe_freeze",
            "status": "pending",
            "writes": [_artifact_ref(UNIVERSE_FREEZE_ARTIFACT)],
        },
        {
            "job_id": "phase1:provider_capability_audit",
            "phase": "provider_capability_audit",
            "status": "pending",
            "writes": [_artifact_ref(PROVIDER_CAPABILITY_ARTIFACT)],
        },
        {
            "job_id": "phase1:history_manifests",
            "phase": "history_manifests",
            "status": "pending",
            "writes": [
                _artifact_ref(SOURCE_HISTORY_MANIFEST_ARTIFACT),
                _artifact_ref(PRICE_HISTORY_MANIFEST_ARTIFACT),
                _artifact_ref(FORWARD_WINDOW_COMPLETION_ARTIFACT),
            ],
        },
        {
            "job_id": "phase1:baseline_backtest",
            "phase": "baseline_backtest",
            "status": "pending",
            "writes": [
                _artifact_ref(BASELINE_RESULTS_ARTIFACT),
                _artifact_ref(BASELINE_REJECTIONS_ARTIFACT),
                _artifact_ref(BASELINE_EVIDENCE_MAP_ARTIFACT),
                _artifact_ref(BASELINE_STRATEGY_EVIDENCE_MAP_ARTIFACT),
            ],
        },
        {
            "job_id": "phase1:akber_shadow_dry_mapping",
            "phase": "akber_shadow_dry_mapping",
            "status": "pending",
            "writes": [
                _artifact_ref(AKBER_BACKTEST_CALIBRATION_ARTIFACT),
                _artifact_ref(BASELINE_SHADOW_ROUTER_MAP_ARTIFACT),
            ],
        },
        {
            "job_id": "phase1:summary",
            "phase": "summary",
            "status": "pending",
            "writes": [
                _artifact_ref(SUMMARY_ARTIFACT),
                _artifact_ref(DASHBOARD_SUMMARY_ARTIFACT),
            ],
        },
    ]
    return {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "qsase_whole_universe_backfill_backtest_manifest",
        "generated_at": _iso(),
        "status": "manifest_ready",
        "run_mode": "dry_run" if options.dry_run else "resume",
        "max_runtime_hours": options.max_runtime_hours,
        "batch_limit": options.batch_limit,
        "network_disabled": options.network_disabled,
        "max_provider_calls": options.max_provider_calls,
        "source_count": len(source_rows),
        "watched_instrument_count": len(instrument_rows),
        "source_keys": [row.get("source_key") for row in source_rows],
        "instrument_symbols": [row.get("symbol") for row in instrument_rows],
        "jobs": jobs,
        "job_count": len(jobs),
        "boundary": "Research-only Phase 1 baseline. No trade candidates, orders, broker writes, live capital, or proof credit.",
        "authority": _authority(),
    }


def build_universe_freeze(context: dict[str, Any], options: RunnerOptions) -> dict[str, Any]:
    records = context["memory_records"]
    counts_by_source = _memory_counts(records, _source_key)
    counts_by_instrument = _memory_counts(records, _instrument)
    strategy_map = _strategy_by_symbol(context["strategy_universe"])
    sources = []
    for row in _safe_list(context["source_network"].get("source_rows")):
        source_key = str(row.get("source_key") or "")
        if not _selected(source_key, options.sources):
            continue
        counts = counts_by_source.get(source_key, {})
        credential_gated = bool(row.get("credential_gated"))
        state = str(row.get("state") or "unknown")
        historical_availability = (
            "local_point_in_time_records_available"
            if counts.get("record_count", 0)
            else "blocked_missing_history"
        )
        if credential_gated and state not in {"online", "available"}:
            historical_availability = "blocked_missing_credentials"
        sources.append(
            {
                "source_key": source_key,
                "source_name": row.get("source_name"),
                "source_category": row.get("family"),
                "provider": source_key,
                "credential_required": credential_gated,
                "credential_state": "configured" if not credential_gated or state == "online" else "missing_or_unverified",
                "historical_availability": historical_availability,
                "freshness_state": row.get("freshness_status"),
                "quorum_role": "can_contribute" if row.get("quorum_contribution") else "context_only",
                "backtest_eligible": counts.get("complete_window_count", 0) > 0,
                "record_count": counts.get("record_count", 0),
                "complete_forward_window_count": counts.get("complete_window_count", 0),
                "missing_forward_window_count": counts.get("missing_window_count", 0),
                "blocked_reason": None if counts.get("record_count", 0) else "no_local_point_in_time_history",
                "trade_candidate_creation_allowed": False,
            }
        )
    instruments = []
    for row in _safe_list(context["source_network"].get("trading_universe_rows")):
        symbol = str(row.get("symbol") or "")
        if not _selected(symbol, options.instruments):
            continue
        counts = counts_by_instrument.get(symbol, {})
        strategies = strategy_map.get(symbol.upper(), [])
        instruments.append(
            {
                "symbol": symbol,
                "instrument_id": row.get("instrument_id"),
                "display_name": row.get("display_name"),
                "instrument_family": row.get("market_family"),
                "paperability": row.get("paperability_state"),
                "paper_route_available": row.get("paper_route_available") is True,
                "strategy_family_ids": [strategy.get("strategy_family_id") for strategy in strategies],
                "strategy_labels": [strategy.get("label") for strategy in strategies],
                "instrument_role": "core_or_proxy" if strategies else "context",
                "backtest_eligible": counts.get("complete_window_count", 0) > 0,
                "record_count": counts.get("record_count", 0),
                "complete_forward_window_count": counts.get("complete_window_count", 0),
                "missing_forward_window_count": counts.get("missing_window_count", 0),
                "blocked_reason": None if counts.get("record_count", 0) else "no_local_point_in_time_price_history",
                "paper_order_allowed": False,
            }
        )
    status = "universe_freeze_ready" if sources and instruments else "universe_freeze_blocked"
    return {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "qsase_backtest_universe_freeze",
        "generated_at": _iso(),
        "status": status,
        "source_count": len(sources),
        "watched_instrument_count": len(instruments),
        "sources": sources,
        "instruments": instruments,
        "input_artifacts": [
            _artifact_ref(SOURCE_NETWORK_ARTIFACT),
            _artifact_ref(SOURCE_UNIVERSE_ARTIFACT),
            _artifact_ref(TRADING_UNIVERSE_ARTIFACT),
            _artifact_ref(STRATEGY_UNIVERSE_ARTIFACT),
            _artifact_ref(HISTORICAL_MEMORY_JSONL_ARTIFACT),
        ],
        "authority": _authority(),
    }


def build_provider_capability_audit(universe_freeze: dict[str, Any]) -> dict[str, Any]:
    providers = []
    for source in _safe_list(universe_freeze.get("sources")):
        family = str(source.get("source_category") or "unknown")
        status = "available" if source.get("record_count", 0) else "blocked_missing_history"
        if source.get("historical_availability") == "blocked_missing_credentials":
            status = "blocked_missing_credentials"
        providers.append(
            {
                "provider": source.get("provider"),
                "source_key": source.get("source_key"),
                "provider_class": PROVIDER_CLASSES_BY_FAMILY.get(family, family),
                "status": status,
                "available": status == "available",
                "historical_availability": source.get("historical_availability"),
                "credential_required": source.get("credential_required"),
                "credential_state": source.get("credential_state"),
                "record_count": source.get("record_count"),
                "complete_forward_window_count": source.get("complete_forward_window_count"),
                "blocked_reason": source.get("blocked_reason"),
                "live_fetch_attempted": False,
                "network_disabled": True,
                "paper_order_allowed": False,
                "broker_write_allowed": False,
            }
        )
    status = "provider_capability_ready_with_gaps" if providers else "provider_capability_blocked"
    return {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "qsase_backfill_provider_capability_audit",
        "generated_at": _iso(),
        "status": status,
        "provider_count": len(providers),
        "available_provider_count": sum(1 for provider in providers if provider["status"] == "available"),
        "blocked_missing_credentials_count": sum(1 for provider in providers if provider["status"] == "blocked_missing_credentials"),
        "blocked_missing_history_count": sum(1 for provider in providers if provider["status"] == "blocked_missing_history"),
        "providers": providers,
        "authority": _authority(),
    }


def build_history_manifests(
    context: dict[str, Any],
    universe_freeze: dict[str, Any],
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    memory_records = context["memory_records"]
    memory_summary = context["historical_memory"]
    source_records = []
    for source in _safe_list(universe_freeze.get("sources")):
        complete = _int(source.get("complete_forward_window_count"))
        source_records.append(
            {
                "source_key": source.get("source_key"),
                "source_category": source.get("source_category"),
                "status": "local_history_available" if source.get("record_count", 0) else "blocked_missing_history",
                "record_count": source.get("record_count", 0),
                "complete_forward_window_count": complete,
                "source_available_at_required": True,
                "point_in_time_safe": True,
                "blocked_reason": source.get("blocked_reason"),
                "raw_history_path": f"data/runtime/backfill/source_history/{source.get('source_key')}",
                "append_only": True,
            }
        )
    instrument_records = []
    for instrument in _safe_list(universe_freeze.get("instruments")):
        complete = _int(instrument.get("complete_forward_window_count"))
        instrument_records.append(
            {
                "symbol": instrument.get("symbol"),
                "market_family": instrument.get("instrument_family"),
                "status": "local_price_windows_available" if complete else "blocked_missing_price_history",
                "record_count": instrument.get("record_count", 0),
                "complete_forward_window_count": complete,
                "missing_forward_window_count": instrument.get("missing_forward_window_count", 0),
                "paper_route_available": instrument.get("paper_route_available"),
                "paperability": instrument.get("paperability"),
                "blocked_reason": instrument.get("blocked_reason") or ("missing_complete_forward_window" if not complete else None),
                "raw_history_path": f"data/runtime/backfill/price_history/{instrument.get('symbol')}/daily",
                "paper_order_allowed": False,
            }
        )
    complete_count = sum(1 for record in memory_records if record.get("backtest_eligible") is True and _return_from_record(record) is not None)
    total_count = len(memory_records)
    missing_count = max(0, total_count - complete_count)
    ratio = round(complete_count / total_count, 6) if total_count else 0.0
    source_manifest = {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "qsase_backfill_source_history_manifest",
        "generated_at": _iso(),
        "status": "source_history_manifest_ready_with_gaps",
        "source_count": len(source_records),
        "local_history_available_count": sum(1 for item in source_records if item["status"] == "local_history_available"),
        "blocked_missing_history_count": sum(1 for item in source_records if item["status"] != "local_history_available"),
        "records": source_records,
        "authority": _authority(),
    }
    price_manifest = {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "qsase_backfill_price_history_manifest",
        "generated_at": _iso(),
        "status": "price_history_manifest_ready_with_gaps",
        "instrument_count": len(instrument_records),
        "local_price_window_available_count": sum(1 for item in instrument_records if item["status"] == "local_price_windows_available"),
        "blocked_missing_price_history_count": sum(1 for item in instrument_records if item["status"] != "local_price_windows_available"),
        "records": instrument_records,
        "authority": _authority(),
    }
    forward_completion = {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "qsase_backfill_forward_window_completion",
        "generated_at": _iso(),
        "status": "forward_window_completion_ready_with_provider_gaps",
        "memory_record_count": total_count,
        "complete_forward_window_count": complete_count,
        "missing_forward_window_count": missing_count,
        "complete_forward_window_ratio": ratio,
        "previous_missing_forward_window_count": memory_summary.get("missing_window_record_count"),
        "missing_windows_materially_reduced": False,
        "material_reduction_status": "provider_backfill_required_for_material_reduction",
        "leakage_rejected_record_count": memory_summary.get("leakage_rejected_record_count", 0),
        "leakage_check_status": "passed" if memory_summary.get("leakage_rejected_record_count", 0) == 0 else "blocked",
        "source_price_memory_artifact": _artifact_ref(HISTORICAL_MEMORY_ARTIFACT),
        "missing_windows_artifact": _artifact_ref(MISSING_WINDOWS_ARTIFACT),
        "paper_growth_trial_calendar_advanced": False,
        "proof_credit_allowed": False,
        "authority": _authority(),
    }
    return source_manifest, price_manifest, forward_completion


def _metrics_for_returns(returns: list[float]) -> dict[str, Any]:
    sample_count = len(returns)
    if not returns:
        return {
            "sample_count": 0,
            "hit_rate": None,
            "average_forward_return": None,
            "median_forward_return": None,
            "expectancy": None,
            "max_adverse_excursion": None,
            "max_favorable_excursion": None,
            "drawdown_proxy": None,
            "confidence_interval": None,
            "p_value_or_non_parametric_equivalent": None,
            "false_positive_rate": None,
        }
    average = statistics.fmean(returns)
    stdev = statistics.pstdev(returns) if sample_count > 1 else 0.0
    half_width = 1.96 * stdev / math.sqrt(sample_count) if sample_count > 1 else 0.0
    negative_count = sum(1 for value in returns if value <= 0)
    return {
        "sample_count": sample_count,
        "hit_rate": round(sum(1 for value in returns if value > 0) / sample_count, 6),
        "average_forward_return": round(average, 8),
        "median_forward_return": round(statistics.median(returns), 8),
        "expectancy": round(average, 8),
        "max_adverse_excursion": round(min(returns), 8),
        "max_favorable_excursion": round(max(returns), 8),
        "drawdown_proxy": round(min(0.0, min(returns)), 8),
        "confidence_interval": {
            "method": "normal_approximation_descriptive",
            "lower": round(average - half_width, 8),
            "upper": round(average + half_width, 8),
        },
        "p_value_or_non_parametric_equivalent": None,
        "false_positive_rate": round(negative_count / sample_count, 6),
    }


def _group_records(records: list[dict[str, Any]]) -> dict[tuple[str, str, str, str], list[dict[str, Any]]]:
    groups: dict[tuple[str, str, str, str], list[dict[str, Any]]] = defaultdict(list)
    for record in records:
        if record.get("backtest_eligible") is not True:
            continue
        if _return_from_record(record) is None:
            continue
        group_specs = (
            ("whole_universe", "all_sources", "all_markets", _window(record)),
            ("source_category_to_market", _source_family(record), _market_family(record), _window(record)),
            ("individual_source_to_market", _source_key(record), _instrument(record), _window(record)),
            ("market_family_response", _market_family(record), _instrument(record), _window(record)),
        )
        for spec in group_specs:
            groups[spec].append(record)
    return dict(groups)


def build_baseline_backtest(
    context: dict[str, Any],
    universe_freeze: dict[str, Any],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], dict[str, Any], dict[str, Any]]:
    records = context["memory_records"]
    complete_records = [
        record for record in records
        if record.get("backtest_eligible") is True and _return_from_record(record) is not None
    ]
    groups = _group_records(complete_records)
    results: list[dict[str, Any]] = []
    rejections: list[dict[str, Any]] = []
    for (relationship_type, source_or_family, market_or_symbol, window), grouped in sorted(groups.items()):
        returns = [_return_from_record(record) for record in grouped]
        numeric_returns = [value for value in returns if value is not None]
        metrics = _metrics_for_returns(numeric_returns)
        record_id = _hash_id(
            [relationship_type, source_or_family, market_or_symbol, window, metrics["sample_count"]],
            "qsase-baseline",
        )
        status = (
            "baseline_relationship_observed"
            if metrics["sample_count"] >= MIN_BASELINE_SAMPLE_COUNT
            else "insufficient_sample_rejected"
        )
        result = {
            "schema_version": SCHEMA_VERSION,
            "baseline_result_id": record_id,
            "relationship_type": relationship_type,
            "source_or_family": source_or_family,
            "market_or_symbol": market_or_symbol,
            "time_window": window,
            "status": status,
            **metrics,
            "regime_split": "not_available_in_phase1_local_baseline",
            "liquidity_paperability_flag": "mixed_or_context_only",
            "overfit_warning": metrics["sample_count"] < 10,
            "source_record_ids": [record.get("memory_record_id") for record in grouped[:12]],
            "trade_candidate_created": False,
            "paper_order_allowed": False,
            "broker_write_allowed": False,
            "live_capital_enabled": False,
            "proof_credit_allowed": False,
            "authority": _authority(),
        }
        if status == "baseline_relationship_observed":
            results.append(result)
        else:
            rejections.append(
                {
                    **result,
                    "rejection_reason": "sample_count_below_minimum_for_baseline_relationship",
                    "minimum_sample_count": MIN_BASELINE_SAMPLE_COUNT,
                }
            )
    strongest = sorted(
        results,
        key=lambda item: (
            abs(item.get("average_forward_return") or 0.0),
            item.get("sample_count") or 0,
        ),
        reverse=True,
    )[:12]
    by_source_category: dict[str, dict[str, Any]] = {}
    for result in results:
        if result["relationship_type"] != "source_category_to_market":
            continue
        bucket = by_source_category.setdefault(
            result["source_or_family"],
            {"result_count": 0, "sample_count": 0, "best_relationships": []},
        )
        bucket["result_count"] += 1
        bucket["sample_count"] += result["sample_count"]
        if len(bucket["best_relationships"]) < 5:
            bucket["best_relationships"].append(result["baseline_result_id"])
    evidence_map = {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "qsase_baseline_backtest_evidence_map",
        "generated_at": _iso(),
        "status": "baseline_evidence_map_ready_with_provider_gaps",
        "complete_record_count": len(complete_records),
        "baseline_result_count": len(results),
        "rejected_relationship_count": len(rejections),
        "strongest_relationships": strongest,
        "coverage_by_source_category": by_source_category,
        "baseline_results_artifact": _artifact_ref(BASELINE_RESULTS_ARTIFACT),
        "baseline_rejections_artifact": _artifact_ref(BASELINE_REJECTIONS_ARTIFACT),
        "no_trade_candidates_created": True,
        "proof_credit_allowed": False,
        "authority": _authority(),
    }
    strategy_map = build_strategy_evidence_map(
        context,
        universe_freeze,
        results,
        rejections,
    )
    return results, rejections, evidence_map, strategy_map


def build_strategy_evidence_map(
    context: dict[str, Any],
    universe_freeze: dict[str, Any],
    results: list[dict[str, Any]],
    rejections: list[dict[str, Any]],
) -> dict[str, Any]:
    strategies = _safe_list(context["strategy_universe"].get("all_strategy_rows"))
    by_market = defaultdict(list)
    for result in results:
        by_market[str(result.get("market_or_symbol")).upper()].append(result)
    records = []
    for strategy in strategies:
        symbols = [
            str(market.get("symbol") or "").upper()
            for market in _safe_list(strategy.get("watched_markets"))
            if market.get("symbol")
        ]
        supporting = []
        for symbol in symbols:
            supporting.extend(by_market.get(symbol, []))
        sample_count = sum(_int(item.get("sample_count")) for item in supporting)
        avg_returns = [
            item.get("average_forward_return")
            for item in supporting
            if item.get("average_forward_return") is not None
        ]
        expectancy = round(statistics.fmean(avg_returns), 8) if avg_returns else None
        confidence = (
            "baseline_supported"
            if sample_count >= MIN_BASELINE_SAMPLE_COUNT
            else "held_for_provider_history"
        )
        records.append(
            {
                "strategy_family_id": strategy.get("strategy_family_id"),
                "label": strategy.get("label"),
                "current_state": strategy.get("current_state"),
                "currently_in_play": strategy.get("currently_in_play"),
                "core_or_proxy_symbols": symbols,
                "supporting_relationship_count": len(supporting),
                "backtest_sample_count": sample_count,
                "expectancy": expectancy,
                "drawdown_proxy": min(
                    [item.get("drawdown_proxy") for item in supporting if item.get("drawdown_proxy") is not None],
                    default=None,
                ),
                "regime_dependency": "not_available_in_phase1_local_baseline",
                "akber_confirmation_requirements": [
                    "volatility_context",
                    "technical_confirmation",
                    "volume_or_flow_confirmation",
                    "pricing_gap_evidence",
                    "risk_reward_and_invalidation",
                ],
                "strategy_evidence_state": confidence,
                "recommended_research_state": "shadow_research_only" if supporting else "hold_for_history",
                "supporting_result_ids": [item.get("baseline_result_id") for item in supporting[:12]],
                "unsupported_assumptions": []
                if supporting
                else ["No complete local forward windows currently support this strategy family."],
                "paper_order_allowed": False,
                "broker_write_allowed": False,
                "proof_credit_allowed": False,
                "live_capital_enabled": False,
            }
        )
    return {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "qsase_baseline_strategy_evidence_map",
        "generated_at": _iso(),
        "status": "strategy_evidence_map_ready_with_provider_gaps",
        "strategy_count": len(records),
        "strategy_supported_count": sum(1 for item in records if item["supporting_relationship_count"] > 0),
        "rejected_relationship_count": len(rejections),
        "records": records,
        "strategy_labels_do_not_determine_evidence": True,
        "new_strategy_family_proposal_allowed": False,
        "new_strategy_family_created": False,
        "authority": _authority(),
    }


def build_akber_backtest_calibration(
    strategy_evidence_map: dict[str, Any],
    baseline_results: list[dict[str, Any]],
    forward_window_completion: dict[str, Any],
) -> dict[str, Any]:
    """Calibrate Akber as a dry practical-trader filter from baseline evidence.

    This does not change thresholds in production. It records what Akber would
    require before any baseline-backed idea could progress toward a separate
    PaperOps review path.
    """
    result_by_id = {
        str(result.get("baseline_result_id")): result
        for result in baseline_results
        if result.get("baseline_result_id")
    }
    records: list[dict[str, Any]] = []
    for strategy in _safe_list(strategy_evidence_map.get("records")):
        supporting = [
            result_by_id[result_id]
            for result_id in _safe_list(strategy.get("supporting_result_ids"))
            if str(result_id) in result_by_id
        ]
        sample_count = _int(strategy.get("backtest_sample_count"))
        false_positive_values = [
            result.get("false_positive_rate")
            for result in supporting
            if result.get("false_positive_rate") is not None
        ]
        false_positive_proxy = (
            round(statistics.fmean(false_positive_values), 6)
            if false_positive_values
            else None
        )
        has_baseline = sample_count >= MIN_BASELINE_SAMPLE_COUNT and bool(supporting)
        practical_gaps = [
            "fresh_current_catalyst",
            "live_volatility_context",
            "technical_confirmation",
            "volume_or_flow_confirmation",
            "pricing_gap_evidence",
            "current_liquidity_and_spread",
            "risk_reward_and_invalidation",
        ]
        stages = [
            {
                "stage": "context",
                "state": "pass" if has_baseline else "hold",
                "reason": (
                    "Historical source-price baseline exists for this strategy."
                    if has_baseline
                    else "No sufficient source-price baseline yet."
                ),
            },
            {
                "stage": "catalyst",
                "state": "hold",
                "reason": "A fresh current catalyst is required before PaperOps review.",
            },
            {
                "stage": "confirmation",
                "state": "hold",
                "reason": "Historical evidence needs live technical and source confirmation.",
            },
            {
                "stage": "volatility",
                "state": "hold",
                "reason": "Current volatility context is not supplied by the Phase 1 baseline.",
            },
            {
                "stage": "volume_flow",
                "state": "hold",
                "reason": "Current volume or flow confirmation is not supplied by the Phase 1 baseline.",
            },
            {
                "stage": "risk_reward",
                "state": "hold",
                "reason": "Risk/reward and invalidation must be calculated on a fresh setup.",
            },
            {
                "stage": "execution_feasibility",
                "state": "hold",
                "reason": "Execution feasibility belongs to the guarded PaperOps route, not the backtest.",
            },
        ]
        records.append(
            {
                "strategy_family_id": strategy.get("strategy_family_id"),
                "label": strategy.get("label"),
                "calibration_state": (
                    "research_calibrated_practical_inputs_missing"
                    if has_baseline
                    else "held_missing_baseline_evidence"
                ),
                "backtest_sample_count": sample_count,
                "supporting_relationship_count": strategy.get("supporting_relationship_count", 0),
                "expectancy": strategy.get("expectancy"),
                "drawdown_proxy": strategy.get("drawdown_proxy"),
                "false_positive_rate_proxy": false_positive_proxy,
                "akber_stage_records": stages,
                "pass_stage_count": sum(1 for stage in stages if stage["state"] == "pass"),
                "hold_stage_count": sum(1 for stage in stages if stage["state"] == "hold"),
                "veto_stage_count": 0,
                "practical_input_gaps": practical_gaps,
                "threshold_proposals": {
                    "minimum_backtest_sample_count": max(MIN_BASELINE_SAMPLE_COUNT, 10),
                    "maximum_false_positive_rate": 0.45,
                    "minimum_expected_return_requires_positive_after_cost_proxy": True,
                    "requires_fresh_catalyst": True,
                    "requires_live_confirmation": True,
                    "requires_invalidation": True,
                },
                "thresholds_mutated": False,
                "akber_pass_is_execution_approval": False,
                "router_receives_calibrated_evidence_only": True,
                "trade_candidate_created": False,
                "paper_order_allowed": False,
                "broker_write_allowed": False,
                "live_capital_enabled": False,
                "proof_credit_allowed": False,
                "authority": _authority(),
            }
        )
    return {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "qsase_akber_backtest_calibration",
        "generated_at": _iso(),
        "status": "akber_calibration_ready_with_practical_input_gaps",
        "strategy_count": len(records),
        "calibrated_strategy_count": sum(
            1 for record in records
            if record["calibration_state"] == "research_calibrated_practical_inputs_missing"
        ),
        "held_missing_baseline_count": sum(
            1 for record in records
            if record["calibration_state"] == "held_missing_baseline_evidence"
        ),
        "complete_forward_window_count": forward_window_completion.get("complete_forward_window_count", 0),
        "missing_forward_window_count": forward_window_completion.get("missing_forward_window_count", 0),
        "thresholds_mutated": False,
        "paper_order_allowed": False,
        "broker_write_allowed": False,
        "live_capital_enabled": False,
        "proof_credit_allowed": False,
        "records": records,
        "authority": _authority(),
    }


def build_baseline_shadow_router_map(
    strategy_evidence_map: dict[str, Any],
    akber_calibration: dict[str, Any],
) -> dict[str, Any]:
    calibration_by_strategy = {
        str(record.get("strategy_family_id")): record
        for record in _safe_list(akber_calibration.get("records"))
        if record.get("strategy_family_id")
    }
    records: list[dict[str, Any]] = []
    for strategy in _safe_list(strategy_evidence_map.get("records")):
        strategy_id = str(strategy.get("strategy_family_id") or "unknown")
        calibration = calibration_by_strategy.get(strategy_id, {})
        has_baseline = _int(strategy.get("supporting_relationship_count")) > 0
        practical_hold = _int(calibration.get("hold_stage_count")) > 0
        dry_router_state = "shadow_only" if has_baseline else "hold_for_provider_history"
        if practical_hold:
            dry_router_state = "shadow_only_practical_confirmation_missing" if has_baseline else dry_router_state
        records.append(
            {
                "strategy_family_id": strategy.get("strategy_family_id"),
                "label": strategy.get("label"),
                "dry_router_state": dry_router_state,
                "paper_review_candidate_created": False,
                "paper_order_created": False,
                "proof_credit_created": False,
                "counterfactuals": {
                    "trade_now": {
                        "state": "rejected_dry_run",
                        "reason": "Backtest evidence cannot become a current order without fresh PaperOps handoff evidence.",
                    },
                    "wait": {
                        "state": "preferred_dry_action",
                        "reason": "Wait for fresh catalyst, Akber practical confirmation, and guarded PaperOps review.",
                    },
                    "veto": {
                        "state": "available",
                        "reason": "Router may veto if provider gaps or practical confirmations remain unresolved.",
                    },
                    "no_order": {
                        "state": "baseline_outcome",
                        "reason": "Phase 1 is research-only and cannot create orders.",
                    },
                    "alternate_threshold_replay": {
                        "state": "proposal_only",
                        "reason": "Akber thresholds are proposals only and were not mutated.",
                    },
                },
                "supporting_relationship_count": strategy.get("supporting_relationship_count", 0),
                "backtest_sample_count": strategy.get("backtest_sample_count", 0),
                "akber_calibration_state": calibration.get("calibration_state"),
                "blocking_reasons": (
                    calibration.get("practical_input_gaps")
                    if has_baseline
                    else ["provider_history_required_for_baseline_support"]
                ),
                "router_output_is_dry_research": True,
                "trade_candidate_created": False,
                "risk_approval_created": False,
                "execution_approval_created": False,
                "paper_order_allowed": False,
                "broker_write_allowed": False,
                "live_capital_enabled": False,
                "proof_credit_allowed": False,
                "authority": _authority(),
            }
        )
    return {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "qsase_baseline_shadow_router_map",
        "generated_at": _iso(),
        "status": "shadow_router_map_ready_with_provider_gaps",
        "strategy_count": len(records),
        "shadow_only_count": sum(1 for record in records if str(record["dry_router_state"]).startswith("shadow_only")),
        "hold_for_provider_history_count": sum(1 for record in records if record["dry_router_state"] == "hold_for_provider_history"),
        "paper_review_candidate_count": 0,
        "trade_candidate_created_count": 0,
        "paper_order_created_count": 0,
        "broker_write_count": 0,
        "live_capital_enabled": False,
        "proof_credit_allowed": False,
        "records": records,
        "authority": _authority(),
    }


def build_state(
    *,
    manifest: dict[str, Any],
    completed_jobs: list[str],
    failed_jobs: list[str],
    current_phase: str,
    status: str,
    started_at: str,
    summary: dict[str, Any] | None = None,
) -> dict[str, Any]:
    all_jobs = [job["job_id"] for job in _safe_list(manifest.get("jobs"))]
    pending = [job for job in all_jobs if job not in completed_jobs and job not in failed_jobs]
    return {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "qsase_whole_universe_backfill_backtest_state",
        "generated_at": _iso(),
        "status": status,
        "started_at": started_at,
        "updated_at": _iso(),
        "max_runtime_hours": manifest.get("max_runtime_hours"),
        "completed_job_count": len(completed_jobs),
        "failed_job_count": len(failed_jobs),
        "pending_job_count": len(pending),
        "completed_jobs": completed_jobs,
        "failed_jobs": failed_jobs,
        "last_completed_job_id": completed_jobs[-1] if completed_jobs else None,
        "current_job_id": pending[0] if pending else None,
        "current_phase": current_phase,
        "safe_to_resume": True,
        "paper_order_created_count": 0,
        "broker_write_count": 0,
        "live_capital_enabled": False,
        "proof_credit_allowed": False,
        "phase_1_backfill_started": True,
        "baseline_status": (summary or {}).get("status"),
        "authority": _authority(),
    }


def build_summary(
    *,
    manifest: dict[str, Any],
    universe_freeze: dict[str, Any],
    provider_capability: dict[str, Any],
    source_history_manifest: dict[str, Any],
    price_history_manifest: dict[str, Any],
    forward_window_completion: dict[str, Any],
    baseline_results: list[dict[str, Any]],
    baseline_rejections: list[dict[str, Any]],
    evidence_map: dict[str, Any],
    strategy_evidence_map: dict[str, Any],
    akber_backtest_calibration: dict[str, Any],
    baseline_shadow_router_map: dict[str, Any],
    started_at: str,
) -> dict[str, Any]:
    missing = _int(forward_window_completion.get("missing_forward_window_count"))
    complete = _int(forward_window_completion.get("complete_forward_window_count"))
    status = (
        "baseline_ready_with_provider_gaps"
        if complete > 0 and baseline_results
        else "baseline_blocked_missing_complete_windows"
    )
    return {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "qsase_whole_universe_backfill_backtest_summary",
        "generated_at": _iso(),
        "started_at": started_at,
        "status": status,
        "run_mode": manifest.get("run_mode"),
        "source_count": universe_freeze.get("source_count", 0),
        "watched_instrument_count": universe_freeze.get("watched_instrument_count", 0),
        "provider_count": provider_capability.get("provider_count", 0),
        "available_provider_count": provider_capability.get("available_provider_count", 0),
        "source_history_available_count": source_history_manifest.get("local_history_available_count", 0),
        "price_history_available_count": price_history_manifest.get("local_price_window_available_count", 0),
        "memory_record_count": forward_window_completion.get("memory_record_count", 0),
        "complete_forward_window_count": complete,
        "missing_forward_window_count": missing,
        "complete_forward_window_ratio": forward_window_completion.get("complete_forward_window_ratio", 0),
        "missing_windows_materially_reduced": forward_window_completion.get("missing_windows_materially_reduced") is True,
        "baseline_result_count": len(baseline_results),
        "baseline_rejection_count": len(baseline_rejections),
        "strategy_evidence_count": strategy_evidence_map.get("strategy_count", 0),
        "strategy_supported_count": strategy_evidence_map.get("strategy_supported_count", 0),
        "akber_calibration_state": akber_backtest_calibration.get("status"),
        "akber_calibrated_strategy_count": akber_backtest_calibration.get("calibrated_strategy_count", 0),
        "akber_thresholds_mutated": akber_backtest_calibration.get("thresholds_mutated") is True,
        "shadow_router_state": baseline_shadow_router_map.get("status"),
        "shadow_only_count": baseline_shadow_router_map.get("shadow_only_count", 0),
        "shadow_router_paper_review_candidate_count": baseline_shadow_router_map.get("paper_review_candidate_count", 0),
        "paper_order_created_count": 0,
        "broker_write_count": 0,
        "live_capital_enabled": False,
        "proof_credit_allowed": False,
        "paper_growth_trial_calendar_advanced": False,
        "simulated_elapsed_time_allowed": False,
        "trade_candidate_created_count": 0,
        "risk_approval_created_count": 0,
        "execution_approval_created_count": 0,
        "phase_1_backfill_started": True,
        "phase_2_or_later_implemented": False,
        "provider_gap_count": missing,
        "blockers": [
            "provider_backfill_required_for_missing_forward_windows"
        ] if missing else [],
        "dashboard_message": (
            "Qadam has a local whole-universe historical evidence baseline from "
            f"{complete} complete source-price windows. {missing} windows still "
            "need provider-backed history before confidence can improve."
        ),
        "artifact_refs": {
            "manifest": _artifact_ref(MANIFEST_ARTIFACT),
            "state": _artifact_ref(STATE_ARTIFACT),
            "universe_freeze": _artifact_ref(UNIVERSE_FREEZE_ARTIFACT),
            "provider_capability": _artifact_ref(PROVIDER_CAPABILITY_ARTIFACT),
            "source_history_manifest": _artifact_ref(SOURCE_HISTORY_MANIFEST_ARTIFACT),
            "price_history_manifest": _artifact_ref(PRICE_HISTORY_MANIFEST_ARTIFACT),
            "forward_window_completion": _artifact_ref(FORWARD_WINDOW_COMPLETION_ARTIFACT),
            "baseline_results": _artifact_ref(BASELINE_RESULTS_ARTIFACT),
            "baseline_rejections": _artifact_ref(BASELINE_REJECTIONS_ARTIFACT),
            "baseline_evidence_map": _artifact_ref(BASELINE_EVIDENCE_MAP_ARTIFACT),
            "baseline_strategy_evidence_map": _artifact_ref(BASELINE_STRATEGY_EVIDENCE_MAP_ARTIFACT),
            "akber_backtest_calibration": _artifact_ref(AKBER_BACKTEST_CALIBRATION_ARTIFACT),
            "baseline_shadow_router_map": _artifact_ref(BASELINE_SHADOW_ROUTER_MAP_ARTIFACT),
        },
        "authority": _authority(),
    }


def build_dashboard_summary(summary: dict[str, Any]) -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "qsase_whole_universe_backfill_backtest_dashboard_summary",
        "generated_at": _iso(),
        "status": summary.get("status"),
        "public_safe": True,
        "read_only": True,
        "paper_only": True,
        "command_disabled": True,
        "backtest_running_state": "baseline_completed_with_provider_gaps",
        "source_count": summary.get("source_count"),
        "watched_instrument_count": summary.get("watched_instrument_count"),
        "complete_forward_window_count": summary.get("complete_forward_window_count"),
        "missing_forward_window_count": summary.get("missing_forward_window_count"),
        "baseline_result_count": summary.get("baseline_result_count"),
        "baseline_rejection_count": summary.get("baseline_rejection_count"),
        "strategy_supported_count": summary.get("strategy_supported_count"),
        "akber_calibration_state": summary.get("akber_calibration_state"),
        "akber_calibrated_strategy_count": summary.get("akber_calibrated_strategy_count"),
        "akber_thresholds_mutated": summary.get("akber_thresholds_mutated"),
        "shadow_router_state": summary.get("shadow_router_state"),
        "shadow_only_count": summary.get("shadow_only_count"),
        "shadow_router_paper_review_candidate_count": summary.get("shadow_router_paper_review_candidate_count"),
        "paper_order_created_count": summary.get("paper_order_created_count"),
        "broker_write_count": summary.get("broker_write_count"),
        "live_capital_enabled": summary.get("live_capital_enabled"),
        "proof_credit_allowed": summary.get("proof_credit_allowed"),
        "paper_growth_trial_calendar_advanced": summary.get("paper_growth_trial_calendar_advanced"),
        "message": summary.get("dashboard_message"),
        "why_no_trade_created": "Historical baseline evidence is research-only and cannot create paper orders.",
        "authority": _authority(),
        "artifact_refs": summary.get("artifact_refs", {}),
    }


def _write_all(
    *,
    settings: Settings | None,
    manifest: dict[str, Any],
    universe_freeze: dict[str, Any] | None = None,
    provider_capability: dict[str, Any] | None = None,
    source_history_manifest: dict[str, Any] | None = None,
    price_history_manifest: dict[str, Any] | None = None,
    forward_window_completion: dict[str, Any] | None = None,
    baseline_results: list[dict[str, Any]] | None = None,
    baseline_rejections: list[dict[str, Any]] | None = None,
    evidence_map: dict[str, Any] | None = None,
    strategy_evidence_map: dict[str, Any] | None = None,
    akber_backtest_calibration: dict[str, Any] | None = None,
    baseline_shadow_router_map: dict[str, Any] | None = None,
    summary: dict[str, Any] | None = None,
    dashboard_summary: dict[str, Any] | None = None,
    state: dict[str, Any] | None = None,
) -> dict[str, str]:
    paths = _paths(settings)
    written: dict[str, str] = {}
    _write_json(paths["manifest"], manifest)
    written["manifest"] = str(paths["manifest"])
    if state is not None:
        _write_json(paths["state"], state)
        written["state"] = str(paths["state"])
    if universe_freeze is not None:
        _write_json(paths["universe_freeze"], universe_freeze)
        written["universe_freeze"] = str(paths["universe_freeze"])
    if provider_capability is not None:
        _write_json(paths["provider_capability"], provider_capability)
        written["provider_capability"] = str(paths["provider_capability"])
    if source_history_manifest is not None:
        _write_json(paths["source_history_manifest"], source_history_manifest)
        written["source_history_manifest"] = str(paths["source_history_manifest"])
    if price_history_manifest is not None:
        _write_json(paths["price_history_manifest"], price_history_manifest)
        written["price_history_manifest"] = str(paths["price_history_manifest"])
    if forward_window_completion is not None:
        _write_json(paths["forward_window_completion"], forward_window_completion)
        written["forward_window_completion"] = str(paths["forward_window_completion"])
    if baseline_results is not None:
        _write_jsonl(paths["baseline_results"], baseline_results)
        written["baseline_results"] = str(paths["baseline_results"])
    if baseline_rejections is not None:
        _write_jsonl(paths["baseline_rejections"], baseline_rejections)
        written["baseline_rejections"] = str(paths["baseline_rejections"])
    if evidence_map is not None:
        _write_json(paths["baseline_evidence_map"], evidence_map)
        written["baseline_evidence_map"] = str(paths["baseline_evidence_map"])
    if strategy_evidence_map is not None:
        _write_json(paths["baseline_strategy_evidence_map"], strategy_evidence_map)
        written["baseline_strategy_evidence_map"] = str(paths["baseline_strategy_evidence_map"])
    if akber_backtest_calibration is not None:
        _write_json(paths["akber_backtest_calibration"], akber_backtest_calibration)
        written["akber_backtest_calibration"] = str(paths["akber_backtest_calibration"])
    if baseline_shadow_router_map is not None:
        _write_json(paths["baseline_shadow_router_map"], baseline_shadow_router_map)
        written["baseline_shadow_router_map"] = str(paths["baseline_shadow_router_map"])
    if summary is not None:
        _write_json(paths["summary"], summary)
        written["summary"] = str(paths["summary"])
    if dashboard_summary is not None:
        _write_json(paths["dashboard_summary"], dashboard_summary)
        written["dashboard_summary"] = str(paths["dashboard_summary"])
    return written


def run_whole_universe_backfill_backtest(
    *,
    settings: Settings | None = None,
    options: RunnerOptions | None = None,
) -> tuple[dict[str, Any], dict[str, str], list[str]]:
    settings = settings or Settings.from_env()
    options = options or RunnerOptions()
    started_at = _iso()
    paths = _paths(settings)
    context = _load_context(settings)
    errors: list[str] = []
    completed_jobs: list[str] = []
    failed_jobs: list[str] = []

    if options.paperops_paused_required and not is_long_backtest_lock_active(context.get("lock", {})):
        errors.append("long_backtest_lock_not_active")
    if errors:
        manifest = build_manifest(context, options)
        state = build_state(
            manifest=manifest,
            completed_jobs=completed_jobs,
            failed_jobs=["phase1:preflight"],
            current_phase="preflight",
            status="blocked",
            started_at=started_at,
        )
        written = _write_all(settings=settings, manifest=manifest, state=state)
        _append_jsonl(paths["errors"], {"generated_at": _iso(), "errors": errors})
        return state, written, errors

    context["lock"] = _mark_lock_phase1_started(settings)
    manifest = build_manifest(context, options)
    state = build_state(
        manifest=manifest,
        completed_jobs=completed_jobs,
        failed_jobs=failed_jobs,
        current_phase="manifest",
        status="running",
        started_at=started_at,
    )
    written = _write_all(settings=settings, manifest=manifest, state=state)
    _append_jsonl(paths["progress"], {"generated_at": _iso(), "event": "manifest_written", "job_count": manifest["job_count"]})

    if options.dry_run:
        state = build_state(
            manifest=manifest,
            completed_jobs=["phase1:dry_run_manifest"],
            failed_jobs=[],
            current_phase="dry_run_complete",
            status="dry_run_complete",
            started_at=started_at,
        )
        written.update(_write_all(settings=settings, manifest=manifest, state=state))
        _append_jsonl(paths["progress"], {"generated_at": _iso(), "event": "dry_run_complete"})
        return state, written, []

    deadline = time.monotonic() + max(1.0, options.max_runtime_hours * 3600)
    if time.monotonic() > deadline:
        errors.append("max_runtime_elapsed_before_start")

    universe_freeze = build_universe_freeze(context, options)
    completed_jobs.append("phase1:universe_freeze")
    _append_jsonl(paths["progress"], {"generated_at": _iso(), "event": "universe_freeze_written", "source_count": universe_freeze["source_count"], "instrument_count": universe_freeze["watched_instrument_count"]})

    provider_capability = build_provider_capability_audit(universe_freeze)
    completed_jobs.append("phase1:provider_capability_audit")
    _append_jsonl(paths["progress"], {"generated_at": _iso(), "event": "provider_capability_written", "provider_count": provider_capability["provider_count"]})

    source_history_manifest, price_history_manifest, forward_window_completion = build_history_manifests(context, universe_freeze)
    completed_jobs.append("phase1:history_manifests")
    _append_jsonl(paths["progress"], {"generated_at": _iso(), "event": "history_manifests_written", "complete_forward_window_count": forward_window_completion["complete_forward_window_count"], "missing_forward_window_count": forward_window_completion["missing_forward_window_count"]})

    baseline_results, baseline_rejections, evidence_map, strategy_evidence_map = build_baseline_backtest(context, universe_freeze)
    completed_jobs.append("phase1:baseline_backtest")
    _append_jsonl(paths["progress"], {"generated_at": _iso(), "event": "baseline_backtest_written", "baseline_result_count": len(baseline_results), "baseline_rejection_count": len(baseline_rejections)})

    akber_backtest_calibration = build_akber_backtest_calibration(
        strategy_evidence_map,
        baseline_results,
        forward_window_completion,
    )
    baseline_shadow_router_map = build_baseline_shadow_router_map(
        strategy_evidence_map,
        akber_backtest_calibration,
    )
    completed_jobs.append("phase1:akber_shadow_dry_mapping")
    _append_jsonl(
        paths["progress"],
        {
            "generated_at": _iso(),
            "event": "akber_shadow_dry_mapping_written",
            "akber_calibrated_strategy_count": akber_backtest_calibration["calibrated_strategy_count"],
            "shadow_only_count": baseline_shadow_router_map["shadow_only_count"],
            "paper_review_candidate_count": baseline_shadow_router_map["paper_review_candidate_count"],
        },
    )

    summary = build_summary(
        manifest=manifest,
        universe_freeze=universe_freeze,
        provider_capability=provider_capability,
        source_history_manifest=source_history_manifest,
        price_history_manifest=price_history_manifest,
        forward_window_completion=forward_window_completion,
        baseline_results=baseline_results,
        baseline_rejections=baseline_rejections,
        evidence_map=evidence_map,
        strategy_evidence_map=strategy_evidence_map,
        akber_backtest_calibration=akber_backtest_calibration,
        baseline_shadow_router_map=baseline_shadow_router_map,
        started_at=started_at,
    )
    dashboard_summary = build_dashboard_summary(summary)
    completed_jobs.append("phase1:summary")
    state = build_state(
        manifest=manifest,
        completed_jobs=completed_jobs,
        failed_jobs=failed_jobs,
        current_phase="complete",
        status="complete_with_provider_gaps",
        started_at=started_at,
        summary=summary,
    )
    written.update(
        _write_all(
            settings=settings,
            manifest=manifest,
            universe_freeze=universe_freeze,
            provider_capability=provider_capability,
            source_history_manifest=source_history_manifest,
            price_history_manifest=price_history_manifest,
            forward_window_completion=forward_window_completion,
            baseline_results=baseline_results,
            baseline_rejections=baseline_rejections,
            evidence_map=evidence_map,
            strategy_evidence_map=strategy_evidence_map,
            akber_backtest_calibration=akber_backtest_calibration,
            baseline_shadow_router_map=baseline_shadow_router_map,
            summary=summary,
            dashboard_summary=dashboard_summary,
            state=state,
        )
    )
    validation_errors = validate_whole_universe_backfill_backtest(load_whole_universe_backfill_backtest(settings))
    if validation_errors:
        _append_jsonl(paths["errors"], {"generated_at": _iso(), "errors": validation_errors})
    _append_jsonl(paths["progress"], {"generated_at": _iso(), "event": "phase1_complete", "status": summary["status"], "validation_error_count": len(validation_errors)})
    return summary, written, validation_errors


def load_whole_universe_backfill_backtest(settings: Settings | None = None) -> dict[str, Any]:
    paths = _paths(settings)
    return {
        "manifest": _read_json(paths["manifest"]),
        "state": _read_json(paths["state"]),
        "summary": _read_json(paths["summary"]),
        "dashboard_summary": _read_json(paths["dashboard_summary"]),
        "universe_freeze": _read_json(paths["universe_freeze"]),
        "provider_capability": _read_json(paths["provider_capability"]),
        "source_history_manifest": _read_json(paths["source_history_manifest"]),
        "price_history_manifest": _read_json(paths["price_history_manifest"]),
        "forward_window_completion": _read_json(paths["forward_window_completion"]),
        "baseline_results": _read_jsonl(paths["baseline_results"]),
        "baseline_rejections": _read_jsonl(paths["baseline_rejections"]),
        "baseline_evidence_map": _read_json(paths["baseline_evidence_map"]),
        "baseline_strategy_evidence_map": _read_json(paths["baseline_strategy_evidence_map"]),
        "akber_backtest_calibration": _read_json(paths["akber_backtest_calibration"]),
        "baseline_shadow_router_map": _read_json(paths["baseline_shadow_router_map"]),
    }


def _validate_authority(payload: Any, prefix: str) -> list[str]:
    errors: list[str] = []
    if isinstance(payload, dict):
        for key in FORBIDDEN_TRUE_FLAGS:
            if payload.get(key) is not False and key in payload:
                errors.append(f"{prefix}_forbidden_true:{key}")
        authority = payload.get("authority")
        if isinstance(authority, dict):
            for key in FORBIDDEN_TRUE_FLAGS:
                if authority.get(key) is not False:
                    errors.append(f"{prefix}_authority_forbidden_true:{key}")
    return errors


def validate_whole_universe_backfill_backtest(bundle: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    summary = bundle.get("summary", {})
    state = bundle.get("state", {})
    universe = bundle.get("universe_freeze", {})
    forward = bundle.get("forward_window_completion", {})
    evidence_map = bundle.get("baseline_evidence_map", {})
    strategy_map = bundle.get("baseline_strategy_evidence_map", {})
    akber = bundle.get("akber_backtest_calibration", {})
    shadow_router = bundle.get("baseline_shadow_router_map", {})
    dashboard = bundle.get("dashboard_summary", {})
    results = bundle.get("baseline_results", [])
    rejections = bundle.get("baseline_rejections", [])

    if summary.get("status") not in {"baseline_ready_with_provider_gaps", "baseline_blocked_missing_complete_windows"}:
        errors.append("summary_status_invalid")
    if state.get("safe_to_resume") is not True:
        errors.append("state_not_safe_to_resume")
    if state.get("phase_1_backfill_started") is not True:
        errors.append("phase1_started_flag_missing")
    if _int(universe.get("source_count")) < 1:
        errors.append("universe_source_count_missing")
    if _int(universe.get("watched_instrument_count")) < 1:
        errors.append("universe_instrument_count_missing")
    if _int(forward.get("complete_forward_window_count")) < 1:
        errors.append("complete_forward_windows_missing")
    if _int(forward.get("leakage_rejected_record_count")) != 0:
        errors.append("leakage_rejected_records_nonzero")
    if not results:
        errors.append("baseline_results_missing")
    if not rejections:
        errors.append("baseline_rejections_missing")
    if evidence_map.get("status") != "baseline_evidence_map_ready_with_provider_gaps":
        errors.append("baseline_evidence_map_status_invalid")
    if strategy_map.get("status") != "strategy_evidence_map_ready_with_provider_gaps":
        errors.append("strategy_evidence_map_status_invalid")
    if akber.get("status") != "akber_calibration_ready_with_practical_input_gaps":
        errors.append("akber_backtest_calibration_status_invalid")
    if akber.get("thresholds_mutated") is not False:
        errors.append("akber_thresholds_mutated")
    for index, record in enumerate(_safe_list(akber.get("records"))[:200]):
        if record.get("thresholds_mutated") is not False:
            errors.append(f"akber_record_thresholds_mutated:{index}")
        if record.get("akber_pass_is_execution_approval") is not False:
            errors.append(f"akber_record_execution_authority_invalid:{index}")
    if shadow_router.get("status") != "shadow_router_map_ready_with_provider_gaps":
        errors.append("baseline_shadow_router_map_status_invalid")
    if _int(shadow_router.get("paper_review_candidate_count")) != 0:
        errors.append("shadow_router_paper_review_candidate_count_nonzero")
    for key in (
        "trade_candidate_created_count",
        "paper_order_created_count",
        "broker_write_count",
    ):
        if _int(shadow_router.get(key)) != 0:
            errors.append(f"shadow_router_unsafe_counter_nonzero:{key}")
    if dashboard.get("command_disabled") is not True or dashboard.get("read_only") is not True:
        errors.append("dashboard_summary_boundary_invalid")
    for key in (
        "paper_order_created_count",
        "broker_write_count",
        "trade_candidate_created_count",
        "risk_approval_created_count",
        "execution_approval_created_count",
    ):
        if _int(summary.get(key)) != 0:
            errors.append(f"summary_unsafe_counter_nonzero:{key}")
    for key in (
        "live_capital_enabled",
        "proof_credit_allowed",
        "paper_growth_trial_calendar_advanced",
        "simulated_elapsed_time_allowed",
    ):
        if summary.get(key) is not False:
            errors.append(f"summary_forbidden_true:{key}")
    for name, payload in bundle.items():
        if isinstance(payload, dict):
            errors.extend(_validate_authority(payload, name))
        elif isinstance(payload, list):
            for index, record in enumerate(payload[:200]):
                errors.extend(_validate_authority(record, f"{name}_{index}"))
    return sorted(set(errors))


def validate_negative_whole_universe_probes() -> list[str]:
    bundle = load_whole_universe_backfill_backtest()
    errors: list[str] = []
    if not bundle.get("summary"):
        return ["negative_probe_skipped_missing_summary"]
    broker_probe = json.loads(json.dumps(bundle))
    broker_probe["summary"]["broker_write_count"] = 1
    if not any("broker_write_count" in error for error in validate_whole_universe_backfill_backtest(broker_probe)):
        errors.append("negative_probe_failed_for_broker_write_count")
    proof_probe = json.loads(json.dumps(bundle))
    proof_probe["summary"]["proof_credit_allowed"] = True
    if not any("proof_credit_allowed" in error for error in validate_whole_universe_backfill_backtest(proof_probe)):
        errors.append("negative_probe_failed_for_proof_credit_allowed")
    order_probe = json.loads(json.dumps(bundle))
    if order_probe.get("baseline_results"):
        order_probe["baseline_results"][0]["paper_order_allowed"] = True
        if not any("paper_order_allowed" in error for error in validate_whole_universe_backfill_backtest(order_probe)):
            errors.append("negative_probe_failed_for_paper_order_allowed")
    akber_probe = json.loads(json.dumps(bundle))
    if akber_probe.get("akber_backtest_calibration"):
        akber_probe["akber_backtest_calibration"]["thresholds_mutated"] = True
        if not any("akber_thresholds_mutated" in error for error in validate_whole_universe_backfill_backtest(akber_probe)):
            errors.append("negative_probe_failed_for_akber_threshold_mutation")
    router_probe = json.loads(json.dumps(bundle))
    if router_probe.get("baseline_shadow_router_map"):
        router_probe["baseline_shadow_router_map"]["paper_review_candidate_count"] = 1
        if not any("shadow_router_paper_review_candidate_count_nonzero" in error for error in validate_whole_universe_backfill_backtest(router_probe)):
            errors.append("negative_probe_failed_for_shadow_router_paper_candidate")
    return errors
