"""QSASE-3 historical source-price memory.

Historical memory turns QSASE-2 matrix rows into point-in-time replay records.
It is research infrastructure only: it cannot advance the 30-day paper growth
trial, create paper proof ledger credit, submit orders, or enable live capital.
"""

from __future__ import annotations

import copy
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from orchestrator.config import Settings
from orchestrator.qsase_governance_safety_contract import (
    PHASE_STATUS_ARTIFACT,
    universal_authority_flags,
)

SCHEMA_VERSION = "qsase_historical_source_price_memory.v1"
PHASE_ID = "qsase_3_historical_source_price_memory"
PHASE_NAME = "QSASE-3: Historical Source-Price Memory"
IMPLEMENTATION_LOG = "docs/qsase-implementation-log.md"

PRIMARY_ARTIFACT = "qsase_historical_source_price_memory.json"
MEMORY_JSONL_ARTIFACT = "qsase_historical_source_price_memory.jsonl"
COVERAGE_MAP_ARTIFACT = "qsase_historical_coverage_map.json"
REPLAY_MANIFEST_ARTIFACT = "qsase_historical_replay_manifest.json"
POINT_IN_TIME_REPLAY_INDEX_ARTIFACT = "qsase_point_in_time_replay_index.json"
MISSING_WINDOWS_ARTIFACT = "qsase_historical_missing_windows.jsonl"
EVENTS_ARTIFACT = "qsase_historical_source_price_memory_events.jsonl"
HISTORY_ARTIFACT = "qsase_historical_source_price_memory_history.jsonl"
DASHBOARD_SUMMARY_ARTIFACT = "qsase_historical_source_price_memory_dashboard_summary.json"

MATRIX_ARTIFACT = "qsase_universal_source_price_matrix.json"
MATRIX_EDGES_ARTIFACT = "qsase_source_price_edges.jsonl"
SOURCE_UNIVERSE_ARTIFACT = "qsase_source_universe.json"
TRADING_UNIVERSE_ARTIFACT = "qsase_trading_universe.json"
HISTORICAL_BACKFILL_RUNS_ARTIFACT = "historical_backfill_runs.jsonl"

FORWARD_OUTCOME_WINDOWS = {
    "event_time_move": "return_event_time",
    "same_session_close": "return_same_session_close",
    "1d_forward": "return_1d",
    "3d_forward": "return_3d",
    "5d_forward": "return_5d",
    "10d_forward": "return_10d",
    "20d_forward": "return_20d",
    "60d_forward": "return_60d",
}

HISTORICAL_MEMORY_AUTHORITY_FLAGS = {
    "strategy_hypothesis_creation_allowed": False,
    "trade_candidate_creation_allowed": False,
    "risk_approval_allowed": False,
    "execution_allowed": False,
    "paper_order_allowed": False,
    "broker_write_allowed": False,
    "prediction_market_write_allowed": False,
    "telegram_command_path_enabled": False,
    "telegram_trade_command_enabled": False,
    "quantum_job_authority": False,
    "live_capital_enabled": False,
    "paper_growth_trial_calendar_advance_allowed": False,
    "simulated_elapsed_time_allowed": False,
    "paper_proof_ledger_credit_allowed": False,
    "proof_credit_allowed": False,
}

REQUIRED_MEMORY_RECORD_FIELDS = [
    "memory_record_id",
    "source_event_id",
    "matrix_row_ids",
    "as_of_timestamp",
    "event_timestamp",
    "source_available_at",
    "market_available_at",
    "decision_timestamp",
    "outcome_available_at",
    "source_snapshot",
    "market_snapshot",
    "feature_availability",
    "features",
    "forward_outcomes",
    "strategy_labels",
    "evidence_class",
    "replay_mode",
    "backtest_eligible",
    "shadow_replay_eligible",
    "paper_proof_ledger_eligible",
    "lookahead_safe",
    "execution_allowed",
    "proof_credit_allowed",
]


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


def _parse_datetime(value: Any) -> datetime | None:
    if not isinstance(value, str) or not value.strip():
        return None
    text = value.strip()
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _max_iso(*values: Any, fallback: str) -> str:
    parsed = [_parse_datetime(value) for value in values]
    parsed = [value for value in parsed if value is not None]
    if not parsed:
        return fallback
    return _iso(max(parsed))


def _hash_id(parts: list[Any], prefix: str) -> str:
    raw = "|".join(str(part) for part in parts)
    return f"{prefix}:{hashlib.sha256(raw.encode('utf-8')).hexdigest()[:20]}"


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


def _bool(value: Any) -> bool:
    return value if isinstance(value, bool) else False


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


def _load_context(settings: Settings | None) -> dict[str, Any]:
    runtime = _runtime_dir(settings)
    return {
        "runtime_dir": runtime,
        "matrix": _read_json(runtime / MATRIX_ARTIFACT),
        "matrix_edges": _read_jsonl(runtime / MATRIX_EDGES_ARTIFACT),
        "source_universe": _read_json(runtime / SOURCE_UNIVERSE_ARTIFACT),
        "trading_universe": _read_json(runtime / TRADING_UNIVERSE_ARTIFACT),
        "historical_backfill_runs": _read_jsonl(runtime / HISTORICAL_BACKFILL_RUNS_ARTIFACT),
    }


def _window_is_complete(edge: dict[str, Any]) -> bool:
    return edge.get("forward_return") is not None and edge.get("price_before") is not None and edge.get("price_after") is not None


def _outcome_key(time_window: str) -> str:
    return FORWARD_OUTCOME_WINDOWS.get(time_window, f"return_{time_window}")


def _source_snapshot(edge: dict[str, Any]) -> dict[str, Any]:
    return {
        "source_name": edge.get("source_key"),
        "source_family": edge.get("source_pipeline"),
        "source_type": edge.get("source_event_type"),
        "event_type": edge.get("source_event_type"),
        "trust_score": edge.get("source_trust_score"),
        "freshness_status": edge.get("source_freshness_status"),
        "credential_status": edge.get("source_credential_status"),
        "source_quorum_credit_allowed": edge.get("source_quorum_credit_allowed"),
        "payload_ref": None,
        "provenance_ref": "data/runtime/qsase_source_price_edges.jsonl",
        "known_before_decision": True,
    }


def _market_snapshot(edge: dict[str, Any]) -> dict[str, Any]:
    return {
        "instrument": edge.get("market_symbol"),
        "asset_class": edge.get("market_family"),
        "provider": "qsase_universal_source_price_matrix",
        "price": edge.get("price_after"),
        "price_before": edge.get("price_before"),
        "volume_context": edge.get("volume_context"),
        "volatility_state": "available" if edge.get("volatility_after") is not None else "missing",
        "market_session": edge.get("market_confirmation_status"),
        "tradable": edge.get("paper_route_available"),
        "paperability_state": edge.get("paperability_state"),
        "paper_route_available": edge.get("paper_route_available"),
        "broker_write_allowed": False,
        "paper_order_allowed": False,
        "live_capital_enabled": False,
    }


def _feature_availability(edge: dict[str, Any], decision_timestamp: str) -> dict[str, Any]:
    source_available = edge.get("source_credential_status") not in {"missing", "missing_optional"}
    market_available = edge.get("market_confirmation_status") in {
        "current_sample_available",
        "available",
        "ok",
    }
    return {
        "source_features_available": source_available,
        "market_features_available": market_available,
        "macro_features_available": edge.get("source_pipeline") == "macro",
        "options_features_available": False,
        "prediction_market_features_available": edge.get("market_family") == "prediction_markets",
        "feature_timestamp": decision_timestamp,
        "decision_timestamp": decision_timestamp,
        "forbidden_future_features_detected": False,
        "outcome_fields_available_before_decision": False,
        "missing_data_behavior": "explicit_missing_window_record"
        if not _window_is_complete(edge)
        else "observed_current_or_historical_window",
    }


def _features(edge: dict[str, Any], decision_timestamp: str) -> dict[str, Any]:
    return {
        "source_trust_score": edge.get("source_trust_score"),
        "source_quorum_credit_allowed": edge.get("source_quorum_credit_allowed"),
        "source_freshness_status": edge.get("source_freshness_status"),
        "market_family": edge.get("market_family"),
        "paper_route_available": edge.get("paper_route_available"),
        "data_completeness_score": edge.get("data_completeness_score"),
        "feature_version": "qsase_3_initial_point_in_time_features",
        "availability_timestamp": decision_timestamp,
        "leakage_check_status": "passed_no_outcome_features",
    }


def _forward_outcomes(edge: dict[str, Any]) -> dict[str, Any]:
    time_window = str(edge.get("time_window") or "")
    complete = _window_is_complete(edge)
    return {
        "window": time_window,
        "outcome_available": complete,
        _outcome_key(time_window): edge.get("forward_return") if complete else None,
        "price_before": edge.get("price_before") if complete else None,
        "price_after": edge.get("price_after") if complete else None,
        "max_favorable_excursion": None,
        "max_adverse_excursion": None,
        "volatility_change": None,
        "volume_change": None,
        "benchmark_relative_return": None,
        "sector_relative_return": None,
        "cross_asset_confirmation": "not_evaluated_in_qsase_3",
        "missing_window_reason": None if complete else "historical_price_window_missing_or_outcome_not_available",
    }


def _memory_record_from_edge(edge: dict[str, Any], generated_at: str) -> dict[str, Any]:
    event_timestamp = str(edge.get("source_event_timestamp") or generated_at)
    source_available_at = event_timestamp
    market_available_at = str(edge.get("market_observation_timestamp") or generated_at)
    decision_timestamp = _max_iso(source_available_at, market_available_at, fallback=generated_at)
    complete = _window_is_complete(edge)
    outcome_available_at = decision_timestamp if complete else None
    replay_state = "window_complete" if complete else "missing_outcome_window"
    point_in_time_safe = True
    record = {
        "schema_version": SCHEMA_VERSION,
        "memory_record_id": _hash_id(
            [edge.get("matrix_row_id"), edge.get("time_window"), "historical-memory"],
            "qsase-memory",
        ),
        "source_event_id": edge.get("source_event_id"),
        "matrix_row_ids": [edge.get("matrix_row_id")],
        "as_of_timestamp": decision_timestamp,
        "event_timestamp": event_timestamp,
        "source_available_at": source_available_at,
        "market_available_at": market_available_at,
        "decision_timestamp": decision_timestamp,
        "outcome_available_at": outcome_available_at,
        "source_snapshot": _source_snapshot(edge),
        "market_snapshot": _market_snapshot(edge),
        "feature_availability": _feature_availability(edge, decision_timestamp),
        "features": _features(edge, decision_timestamp),
        "forward_outcomes": _forward_outcomes(edge),
        "strategy_labels": [],
        "evidence_class": "historical_backfill_evidence",
        "replay_mode": "point_in_time_replay",
        "replay_state": replay_state,
        "backtest_eligible": complete and point_in_time_safe,
        "shadow_replay_eligible": False,
        "paper_proof_ledger_eligible": False,
        "lookahead_safe": point_in_time_safe,
        "point_in_time_safe": point_in_time_safe,
        "leakage_check_status": "passed",
        "execution_allowed": False,
        "paper_order_allowed": False,
        "broker_write_allowed": False,
        "live_capital_enabled": False,
        "proof_credit_allowed": False,
        "paper_growth_trial_calendar_advance_allowed": False,
        "simulated_elapsed_time_allowed": False,
        "paper_proof_ledger_credit_allowed": False,
        "provenance": [
            {
                "artifact": "data/runtime/qsase_source_price_edges.jsonl",
                "record_id": edge.get("matrix_row_id"),
                "role": "source_price_alignment_input",
                "public_safe": True,
            },
            {
                "artifact": "data/runtime/qsase_universal_source_price_matrix.json",
                "role": "matrix_summary_input",
                "public_safe": True,
            },
        ],
        "missing_window_record_id": None
        if complete
        else _hash_id(
            [edge.get("matrix_row_id"), edge.get("time_window"), "missing-window"],
            "qsase-missing-window",
        ),
    }
    return record


def _missing_window_record(record: dict[str, Any]) -> dict[str, Any] | None:
    if record.get("replay_state") != "missing_outcome_window":
        return None
    return {
        "schema_version": SCHEMA_VERSION,
        "missing_window_record_id": record["missing_window_record_id"],
        "memory_record_id": record["memory_record_id"],
        "matrix_row_id": record["matrix_row_ids"][0],
        "source_key": record["source_snapshot"]["source_name"],
        "market_symbol": record["market_snapshot"]["instrument"],
        "market_family": record["market_snapshot"]["asset_class"],
        "time_window": record["forward_outcomes"]["window"],
        "reason": record["forward_outcomes"]["missing_window_reason"],
        "gap_class": "historical_price_or_outcome_window_missing",
        "provider_action_required": "supply_point_in_time_historical_source_and_price_window",
        "interpolation_allowed": False,
        "paper_proof_ledger_eligible": False,
        "proof_credit_allowed": False,
        "execution_allowed": False,
        "live_capital_enabled": False,
        "public_safe": True,
    }


def _build_records(edges: list[dict[str, Any]], generated_at: str) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    records = [_memory_record_from_edge(edge, generated_at) for edge in edges]
    missing_windows = [
        missing
        for missing in (_missing_window_record(record) for record in records)
        if missing is not None
    ]
    return records, missing_windows


def _increment_index(index: dict[str, dict[str, Any]], key: Any, record_id: str) -> None:
    text = str(key or "unknown")
    bucket = index.setdefault(text, {"count": 0, "sample_record_ids": []})
    bucket["count"] += 1
    if len(bucket["sample_record_ids"]) < 20:
        bucket["sample_record_ids"].append(record_id)


def build_point_in_time_replay_index(memory: dict[str, Any]) -> dict[str, Any]:
    records = memory.get("records")
    if not isinstance(records, list):
        records = memory.get("memory_records", [])
    generated_at = memory.get("generated_at") or _iso(_now())
    indices: dict[str, dict[str, dict[str, Any]]] = {
        "by_source_family": {},
        "by_source_name": {},
        "by_instrument": {},
        "by_asset_class": {},
        "by_event_type": {},
        "by_time_window": {},
        "by_outcome_direction": {},
        "by_replay_mode": {},
        "by_evidence_class": {},
        "by_route_readiness_state": {},
        "by_source_quorum_state": {},
        "by_paper_route_state": {},
        "by_missing_window_reason": {},
    }
    for record in records:
        record_id = record.get("memory_record_id")
        source = record.get("source_snapshot", {})
        market = record.get("market_snapshot", {})
        outcomes = record.get("forward_outcomes", {})
        route_state = "paper_route_available" if market.get("paper_route_available") else "research_only_or_context"
        source_quorum_state = (
            "source_quorum_credit_allowed"
            if source.get("source_quorum_credit_allowed")
            else "source_quorum_credit_not_allowed"
        )
        paper_route_state = "paper_route_available_guarded_only" if market.get("paper_route_available") else "no_paper_route"
        forward_return = next(
            (value for key, value in outcomes.items() if key.startswith("return_") and value is not None),
            None,
        )
        if forward_return is None:
            outcome_direction = "missing"
        elif forward_return > 0:
            outcome_direction = "positive"
        elif forward_return < 0:
            outcome_direction = "negative"
        else:
            outcome_direction = "flat"
        _increment_index(indices["by_source_family"], source.get("source_family"), record_id)
        _increment_index(indices["by_source_name"], source.get("source_name"), record_id)
        _increment_index(indices["by_instrument"], market.get("instrument"), record_id)
        _increment_index(indices["by_asset_class"], market.get("asset_class"), record_id)
        _increment_index(indices["by_event_type"], source.get("event_type"), record_id)
        _increment_index(indices["by_time_window"], outcomes.get("window"), record_id)
        _increment_index(indices["by_outcome_direction"], outcome_direction, record_id)
        _increment_index(indices["by_replay_mode"], record.get("replay_mode"), record_id)
        _increment_index(indices["by_evidence_class"], record.get("evidence_class"), record_id)
        _increment_index(indices["by_route_readiness_state"], route_state, record_id)
        _increment_index(indices["by_source_quorum_state"], source_quorum_state, record_id)
        _increment_index(indices["by_paper_route_state"], paper_route_state, record_id)
        _increment_index(indices["by_missing_window_reason"], outcomes.get("missing_window_reason") or "none", record_id)
    return {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "qsase_point_in_time_replay_index",
        "generated_at": generated_at,
        "status": "point_in_time_replay_index_ready" if records else "point_in_time_replay_index_blocked",
        "record_count": len(records),
        "indices": indices,
        "public_safe": True,
        "command_disabled": True,
        "paper_proof_ledger_eligible": False,
        "proof_credit_allowed": False,
        "execution_allowed": False,
        "live_capital_enabled": False,
    }


def _coverage_map(
    records: list[dict[str, Any]],
    missing_windows: list[dict[str, Any]],
    matrix: dict[str, Any],
    backfill_runs: list[dict[str, Any]],
    generated_at: str,
) -> dict[str, Any]:
    by_source_family: dict[str, dict[str, int]] = {}
    by_instrument: dict[str, dict[str, int]] = {}
    by_window: dict[str, dict[str, int]] = {}
    source_keys = set()
    instrument_keys = set()
    for record in records:
        source = record["source_snapshot"]
        market = record["market_snapshot"]
        outcomes = record["forward_outcomes"]
        source_keys.add(source["source_name"])
        instrument_keys.add(market["instrument"])
        source_bucket = by_source_family.setdefault(
            str(source["source_family"]),
            {"record_count": 0, "window_complete_count": 0, "missing_window_count": 0},
        )
        instrument_bucket = by_instrument.setdefault(
            str(market["instrument"]),
            {"record_count": 0, "window_complete_count": 0, "missing_window_count": 0},
        )
        window_bucket = by_window.setdefault(
            str(outcomes["window"]),
            {"record_count": 0, "window_complete_count": 0, "missing_window_count": 0},
        )
        for bucket in (source_bucket, instrument_bucket, window_bucket):
            bucket["record_count"] += 1
            if record["replay_state"] == "window_complete":
                bucket["window_complete_count"] += 1
            else:
                bucket["missing_window_count"] += 1
    blocked_backfills = [run for run in backfill_runs if run.get("status") == "blocked"]
    recorded_backfills = [run for run in backfill_runs if run.get("status") == "recorded"]
    return {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "qsase_historical_coverage_map",
        "generated_at": generated_at,
        "status": "historical_coverage_degraded" if missing_windows or blocked_backfills else "historical_coverage_ready",
        "eligible_source_count": matrix.get("source_universe", {}).get("source_count"),
        "covered_source_count": len(source_keys),
        "missing_source_count": 0 if records else matrix.get("source_universe", {}).get("source_count", 0),
        "eligible_instrument_count": matrix.get("trading_universe", {}).get("watched_market_count"),
        "covered_instrument_count": len(instrument_keys),
        "missing_instrument_count": 0 if records else matrix.get("trading_universe", {}).get("watched_market_count", 0),
        "matrix_row_count": matrix.get("source_price_edge_count"),
        "memory_record_count": len(records),
        "point_in_time_safe_record_count": sum(1 for record in records if record["point_in_time_safe"]),
        "leakage_rejected_record_count": sum(1 for record in records if not record["lookahead_safe"]),
        "window_complete_record_count": sum(1 for record in records if record["replay_state"] == "window_complete"),
        "window_incomplete_record_count": len(missing_windows),
        "revision_aware_macro_record_count": 0,
        "credential_blocked_source_count": matrix.get("source_universe", {}).get("credential_gated_source_count"),
        "provider_stale_source_count": matrix.get("source_universe", {}).get("stale_or_unknown_freshness_count"),
        "historical_backfill_recorded_count": len(recorded_backfills),
        "historical_backfill_blocked_count": len(blocked_backfills),
        "coverage_by_source_family": by_source_family,
        "coverage_by_instrument": by_instrument,
        "coverage_by_time_window": by_window,
        "missing_window_records_path": f"data/runtime/{MISSING_WINDOWS_ARTIFACT}",
        "public_safe": True,
        "command_disabled": True,
        "paper_proof_ledger_eligible": False,
        "proof_credit_allowed": False,
    }


def _replay_manifest(
    records: list[dict[str, Any]],
    missing_windows: list[dict[str, Any]],
    coverage: dict[str, Any],
    generated_at: str,
) -> dict[str, Any]:
    backtest_count = sum(1 for record in records if record["backtest_eligible"])
    point_in_time_safe_count = sum(1 for record in records if record["point_in_time_safe"])
    return {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "qsase_historical_replay_manifest",
        "generated_at": generated_at,
        "status": "historical_replay_manifest_degraded" if missing_windows else "historical_replay_manifest_ready",
        "input_artifacts": [
            f"data/runtime/{MATRIX_ARTIFACT}",
            f"data/runtime/{MATRIX_EDGES_ARTIFACT}",
            f"data/runtime/{HISTORICAL_BACKFILL_RUNS_ARTIFACT}",
        ],
        "replay_modes": {
            "historical_backtest_replay": {
                "status": "degraded_missing_forward_windows" if missing_windows else "ready",
                "eligible_record_count": backtest_count,
                "research_only": True,
                "paper_proof_ledger_eligible": False,
            },
            "point_in_time_replay": {
                "status": "ready" if point_in_time_safe_count else "blocked",
                "eligible_record_count": point_in_time_safe_count,
                "leakage_safe_required": True,
                "paper_proof_ledger_eligible": False,
            },
            "forward_shadow_replay": {
                "status": "not_started_deferred_to_later_qsase_phases",
                "eligible_record_count": 0,
                "paper_proof_ledger_eligible": False,
            },
            "counterfactual_strategy_replay": {
                "status": "not_started_deferred_until_strategy_rules_exist",
                "eligible_record_count": 0,
                "paper_proof_ledger_eligible": False,
            },
            "paper_lifecycle_replay": {
                "status": "not_in_scope_for_simulated_historical_memory",
                "eligible_record_count": 0,
                "paper_proof_ledger_eligible": False,
            },
        },
        "calendar_integrity": {
            "paper_growth_trial_calendar_advanced": False,
            "paper_growth_trial_day_delta": 0,
            "simulated_elapsed_time_created": False,
            "historical_replay_can_create_paper_proof_ledger_credit": False,
            "paper_proof_ledger_credit_granted": False,
        },
        "coverage_ref": "data/runtime/qsase_historical_coverage_map.json",
        "missing_window_count": len(missing_windows),
        "public_safe": True,
        "command_disabled": True,
        "execution_allowed": False,
        "broker_write_allowed": False,
        "live_capital_enabled": False,
        "proof_credit_allowed": False,
    }


def _leakage_checks(records: list[dict[str, Any]]) -> dict[str, Any]:
    future_feature_violations = 0
    outcome_feature_violations = 0
    unavailable_outcome_feature_violations = 0
    for record in records:
        decision = _parse_datetime(record.get("decision_timestamp"))
        feature_time = _parse_datetime(record.get("feature_availability", {}).get("feature_timestamp"))
        if decision and feature_time and feature_time > decision:
            future_feature_violations += 1
        for key in record.get("features", {}):
            if key.startswith("return_") or key.startswith("outcome") or "drawdown" in key:
                outcome_feature_violations += 1
        if record.get("feature_availability", {}).get("outcome_fields_available_before_decision") is not False:
            unavailable_outcome_feature_violations += 1
    total = future_feature_violations + outcome_feature_violations + unavailable_outcome_feature_violations
    return {
        "status": "leakage_checks_passed" if total == 0 else "leakage_checks_failed",
        "future_feature_timestamp_violation_count": future_feature_violations,
        "outcome_feature_violation_count": outcome_feature_violations,
        "outcome_available_before_decision_violation_count": unavailable_outcome_feature_violations,
        "leakage_rejected_record_count": total,
        "point_in_time_safe_record_count": sum(1 for record in records if record.get("point_in_time_safe")),
    }


def _dashboard_summary(memory: dict[str, Any]) -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "qsase_historical_source_price_memory_dashboard_summary",
        "generated_at": memory["generated_at"],
        "status": memory["status"],
        "public_safe": True,
        "command_disabled": True,
        "live_send_allowed": False,
        "summary_rows": [
            {"label": "Historical memory records", "value": memory["memory_record_count"]},
            {"label": "Point-in-time safe", "value": memory["point_in_time_safe_record_count"]},
            {"label": "Backtest eligible", "value": memory["backtest_eligible_record_count"]},
            {"label": "Missing windows", "value": memory["missing_window_record_count"]},
            {"label": "Leakage rejected", "value": memory["leakage_rejected_record_count"]},
            {"label": "Replay mode", "value": "point_in_time_replay"},
            {"label": "Proof boundary", "value": "not_paper_proof_ledger_credit"},
        ],
        "memory_state_language": "Historical memory informs research. It is not paper proof ledger credit.",
        "authority_flags_false": all(value is False for value in memory["authority_flags"].values()),
        "paper_growth_trial_calendar_advanced": False,
        "paper_proof_ledger_credit_granted": False,
        "research_only": True,
    }


def build_historical_source_price_memory(settings: Settings | None = None) -> dict[str, Any]:
    context = _load_context(settings)
    generated_at = _iso(_now())
    matrix = context["matrix"]
    edges = context["matrix_edges"]
    records, missing_windows = _build_records(edges, generated_at)
    coverage = _coverage_map(records, missing_windows, matrix, context["historical_backfill_runs"], generated_at)
    replay_manifest = _replay_manifest(records, missing_windows, coverage, generated_at)
    memory_for_index = {"generated_at": generated_at, "records": records}
    replay_index = build_point_in_time_replay_index(memory_for_index)
    leakage = _leakage_checks(records)

    missing_required_state: list[str] = []
    if not matrix:
        missing_required_state.append("qsase_universal_source_price_matrix_missing")
    if not edges:
        missing_required_state.append("qsase_source_price_edges_missing")

    degraded_reasons: list[str] = []
    hold_reasons: list[str] = []
    if leakage["status"] != "leakage_checks_passed":
        degraded_reasons.append("leakage_checks_not_passed")
    if missing_windows:
        hold_reasons.append("historical_forward_windows_missing_or_incomplete")

    status = "qsase_historical_source_price_memory_ready"
    if missing_required_state:
        status = "qsase_historical_source_price_memory_blocked"
    elif degraded_reasons:
        status = "qsase_historical_source_price_memory_degraded"
    elif hold_reasons:
        status = "qsase_historical_source_price_memory_ready_with_gaps"

    memory = {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "qsase_historical_source_price_memory",
        "phase_id": PHASE_ID,
        "phase_name": PHASE_NAME,
        "generated_at": generated_at,
        "status": status,
        "public_safe": True,
        "command_disabled": True,
        "paper_only": True,
        "proposal_first": True,
        "research_only": True,
        "memory_record_count": len(records),
        "point_in_time_safe_record_count": sum(1 for record in records if record["point_in_time_safe"]),
        "leakage_rejected_record_count": leakage["leakage_rejected_record_count"],
        "window_complete_record_count": sum(1 for record in records if record["replay_state"] == "window_complete"),
        "missing_window_record_count": len(missing_windows),
        "backtest_eligible_record_count": sum(1 for record in records if record["backtest_eligible"]),
        "shadow_replay_eligible_record_count": sum(1 for record in records if record["shadow_replay_eligible"]),
        "paper_proof_ledger_eligible_record_count": sum(
            1 for record in records if record["paper_proof_ledger_eligible"]
        ),
        "memory_records_path": f"data/runtime/{MEMORY_JSONL_ARTIFACT}",
        "coverage_map_path": f"data/runtime/{COVERAGE_MAP_ARTIFACT}",
        "replay_manifest_path": f"data/runtime/{REPLAY_MANIFEST_ARTIFACT}",
        "point_in_time_replay_index_path": f"data/runtime/{POINT_IN_TIME_REPLAY_INDEX_ARTIFACT}",
        "missing_windows_path": f"data/runtime/{MISSING_WINDOWS_ARTIFACT}",
        "source_price_matrix_ref": {
            "path": f"data/runtime/{MATRIX_ARTIFACT}",
            "status": matrix.get("status"),
            "generated_at": matrix.get("generated_at"),
            "matrix_row_count": matrix.get("source_price_edge_count"),
        },
        "historical_backfill_ref": {
            "path": f"data/runtime/{HISTORICAL_BACKFILL_RUNS_ARTIFACT}",
            "record_count": len(context["historical_backfill_runs"]),
            "read_only": True,
            "runner_executed_by_qsase_3": False,
        },
        "coverage_map": coverage,
        "replay_manifest": replay_manifest,
        "point_in_time_replay_index": replay_index,
        "missing_required_state": missing_required_state,
        "degraded_reasons": sorted(set(degraded_reasons)),
        "hold_reasons": sorted(set(hold_reasons)),
        "leakage_checks": leakage,
        "calendar_integrity": replay_manifest["calendar_integrity"],
        "memory_record_sample": records[:10],
        "missing_window_sample": missing_windows[:20],
        "evidence_classes": {
            "historical_backfill_evidence": {
                "research_only": True,
                "paper_proof_ledger_eligible": False,
            },
            "forward_shadow_evidence": {
                "implemented_in_qsase_3": False,
                "paper_proof_ledger_eligible": False,
            },
            "real_paper_evidence": {
                "implemented_in_qsase_3": False,
                "requires_actual_guarded_paper_route": True,
            },
        },
        "no_30_day_paper_growth_trial_advance": True,
        "no_paper_proof_ledger_credit": True,
        "no_strategy_hypotheses_created": True,
        "no_trade_candidates_created": True,
        "no_paper_orders_created": True,
        "no_broker_writes": True,
        "no_live_capital": True,
        "authority": universal_authority_flags(),
        "authority_flags": dict(HISTORICAL_MEMORY_AUTHORITY_FLAGS),
        "dashboard_safe_summary": {},
    }
    memory["dashboard_safe_summary"] = _dashboard_summary(memory)
    memory["records"] = records
    memory["missing_windows"] = missing_windows
    return memory


def load_historical_source_price_memory(settings: Settings | None = None) -> dict[str, Any]:
    runtime = _runtime_dir(settings)
    memory = _read_json(runtime / PRIMARY_ARTIFACT)
    records = _read_jsonl(runtime / MEMORY_JSONL_ARTIFACT)
    missing_windows = _read_jsonl(runtime / MISSING_WINDOWS_ARTIFACT)
    if memory:
        memory["records"] = records
        memory["missing_windows"] = missing_windows
    return memory


def validate_historical_source_price_memory(memory: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if memory.get("artifact_type") != "qsase_historical_source_price_memory":
        errors.append("artifact_type_invalid")
    if memory.get("schema_version") != SCHEMA_VERSION:
        errors.append("schema_version_invalid")
    if memory.get("status") not in {
        "qsase_historical_source_price_memory_ready",
        "qsase_historical_source_price_memory_ready_with_gaps",
        "qsase_historical_source_price_memory_degraded",
        "qsase_historical_source_price_memory_blocked",
    }:
        errors.append("status_invalid")
    if memory.get("public_safe") is not True or memory.get("command_disabled") is not True:
        errors.append("public_safe_command_disabled_required")
    if memory.get("research_only") is not True:
        errors.append("research_only_required")
    if memory.get("no_30_day_paper_growth_trial_advance") is not True:
        errors.append("paper_growth_trial_advance_guard_required")
    if memory.get("no_paper_proof_ledger_credit") is not True:
        errors.append("paper_proof_ledger_credit_guard_required")
    for key in (
        "no_strategy_hypotheses_created",
        "no_trade_candidates_created",
        "no_paper_orders_created",
        "no_broker_writes",
        "no_live_capital",
    ):
        if memory.get(key) is not True:
            errors.append(f"{key}_must_be_true")

    authority = memory.get("authority", {})
    if not isinstance(authority, dict) or any(value is not False for value in authority.values()):
        errors.append("universal_authority_flags_must_all_be_false")
    flags = memory.get("authority_flags", {})
    for key, expected in HISTORICAL_MEMORY_AUTHORITY_FLAGS.items():
        if flags.get(key) is not expected:
            errors.append(f"authority_flag_{key}_must_be_false")

    calendar = memory.get("calendar_integrity", {})
    if calendar.get("paper_growth_trial_calendar_advanced") is not False:
        errors.append("paper_growth_trial_calendar_must_not_advance")
    if calendar.get("paper_growth_trial_day_delta") != 0:
        errors.append("paper_growth_trial_day_delta_must_be_zero")
    if calendar.get("simulated_elapsed_time_created") is not False:
        errors.append("simulated_elapsed_time_must_be_false")
    if calendar.get("paper_proof_ledger_credit_granted") is not False:
        errors.append("paper_proof_ledger_credit_granted_must_be_false")

    records = memory.get("records")
    if not isinstance(records, list) or not records:
        errors.append("memory_records_missing")
        records = []
    missing_windows = memory.get("missing_windows")
    if not isinstance(missing_windows, list):
        missing_windows = []
    missing_ids = {row.get("missing_window_record_id") for row in missing_windows}
    record_ids: set[str] = set()
    for record in records:
        record_id = record.get("memory_record_id")
        if not record_id:
            errors.append("memory_record_id_missing")
            continue
        if record_id in record_ids:
            errors.append(f"duplicate_memory_record_id_{record_id}")
        record_ids.add(record_id)
        for field in REQUIRED_MEMORY_RECORD_FIELDS:
            if field not in record:
                errors.append(f"memory_record_{record_id}_missing_{field}")
        for timestamp_field in (
            "as_of_timestamp",
            "event_timestamp",
            "source_available_at",
            "market_available_at",
            "decision_timestamp",
        ):
            if _parse_datetime(record.get(timestamp_field)) is None:
                errors.append(f"memory_record_{record_id}_{timestamp_field}_invalid")
        decision = _parse_datetime(record.get("decision_timestamp"))
        feature_time = _parse_datetime(record.get("feature_availability", {}).get("feature_timestamp"))
        source_available = _parse_datetime(record.get("source_available_at"))
        market_available = _parse_datetime(record.get("market_available_at"))
        if decision and feature_time and feature_time > decision:
            errors.append(f"memory_record_{record_id}_future_feature_timestamp")
        if decision and source_available and source_available > decision:
            errors.append(f"memory_record_{record_id}_source_after_decision")
        if decision and market_available and market_available > decision:
            errors.append(f"memory_record_{record_id}_market_after_decision")
        features = record.get("features", {})
        if not isinstance(features, dict):
            errors.append(f"memory_record_{record_id}_features_invalid")
            features = {}
        for key in features:
            if key.startswith("return_") or key.startswith("outcome") or "drawdown" in key:
                errors.append(f"memory_record_{record_id}_outcome_feature_leakage")
        availability = record.get("feature_availability", {})
        if availability.get("forbidden_future_features_detected") is not False:
            errors.append(f"memory_record_{record_id}_future_features_detected")
        if availability.get("outcome_fields_available_before_decision") is not False:
            errors.append(f"memory_record_{record_id}_outcome_available_before_decision")
        if not record.get("evidence_class"):
            errors.append(f"memory_record_{record_id}_evidence_class_missing")
        if not record.get("replay_mode"):
            errors.append(f"memory_record_{record_id}_replay_mode_missing")
        if record.get("paper_proof_ledger_eligible") is not False:
            errors.append(f"memory_record_{record_id}_paper_proof_ledger_must_be_false")
        for key in (
            "execution_allowed",
            "paper_order_allowed",
            "broker_write_allowed",
            "live_capital_enabled",
            "proof_credit_allowed",
            "paper_growth_trial_calendar_advance_allowed",
            "simulated_elapsed_time_allowed",
            "paper_proof_ledger_credit_allowed",
        ):
            if record.get(key) is not False:
                errors.append(f"memory_record_{record_id}_{key}_must_be_false")
        if record.get("replay_state") == "missing_outcome_window":
            missing_id = record.get("missing_window_record_id")
            if missing_id not in missing_ids:
                errors.append(f"memory_record_{record_id}_missing_window_record_absent")
        else:
            if record.get("outcome_available_at") is None:
                errors.append(f"memory_record_{record_id}_complete_window_outcome_timestamp_missing")

    leakage = memory.get("leakage_checks", {})
    if leakage.get("status") != "leakage_checks_passed":
        errors.append("leakage_checks_must_pass")
    coverage = memory.get("coverage_map", {})
    if coverage.get("public_safe") is not True or coverage.get("proof_credit_allowed") is not False:
        errors.append("coverage_map_boundary_invalid")
    replay = memory.get("replay_manifest", {})
    modes = replay.get("replay_modes")
    if not isinstance(modes, dict) or "point_in_time_replay" not in modes:
        errors.append("replay_manifest_modes_missing")
    if replay.get("proof_credit_allowed") is not False or replay.get("live_capital_enabled") is not False:
        errors.append("replay_manifest_authority_invalid")
    index = memory.get("point_in_time_replay_index", {})
    if index.get("artifact_type") != "qsase_point_in_time_replay_index":
        errors.append("point_in_time_replay_index_missing")
    summary = memory.get("dashboard_safe_summary", {})
    if summary.get("public_safe") is not True or summary.get("command_disabled") is not True:
        errors.append("dashboard_summary_public_safe_required")
    if summary.get("live_send_allowed") is not False:
        errors.append("dashboard_summary_live_send_must_be_false")
    if summary.get("paper_proof_ledger_credit_granted") is not False:
        errors.append("dashboard_summary_proof_credit_must_be_false")
    return sorted(set(errors))


def _summary_without_records(memory: dict[str, Any]) -> dict[str, Any]:
    summary = dict(memory)
    summary.pop("records", None)
    summary.pop("missing_windows", None)
    return summary


def build_qsase_phase_implementation_status(memory: dict[str, Any]) -> dict[str, Any]:
    runtime_dir = _runtime_dir()
    existing = _read_json(runtime_dir / PHASE_STATUS_ARTIFACT)
    phases = existing.get("phases") if isinstance(existing.get("phases"), dict) else {}
    phases[PHASE_ID] = {
        "name": PHASE_NAME,
        "status": memory["status"],
        "artifact_path": f"data/runtime/{PRIMARY_ARTIFACT}",
        "memory_records_path": f"data/runtime/{MEMORY_JSONL_ARTIFACT}",
        "coverage_map_path": f"data/runtime/{COVERAGE_MAP_ARTIFACT}",
        "replay_manifest_path": f"data/runtime/{REPLAY_MANIFEST_ARTIFACT}",
        "point_in_time_replay_index_path": f"data/runtime/{POINT_IN_TIME_REPLAY_INDEX_ARTIFACT}",
        "memory_record_count": memory["memory_record_count"],
        "point_in_time_safe_record_count": memory["point_in_time_safe_record_count"],
        "missing_window_record_count": memory["missing_window_record_count"],
        "leakage_rejected_record_count": memory["leakage_rejected_record_count"],
        "paper_only": True,
        "research_only": True,
        "proposal_first": True,
        "public_safe": True,
        "authority_flags_false": True,
        "paper_growth_trial_calendar_advanced": False,
        "paper_proof_ledger_credit_granted": False,
        "later_qsase_phases_implemented": False,
    }
    return {
        "schema_version": 1,
        "generated_at": memory["generated_at"],
        "active_phase": PHASE_ID,
        "phases": phases,
        "safety": memory["authority"],
    }


def _append_implementation_log(memory: dict[str, Any]) -> None:
    log_path = _repo_root() / IMPLEMENTATION_LOG
    log_path.parent.mkdir(parents=True, exist_ok=True)
    existing = (
        log_path.read_text(encoding="utf-8")
        if log_path.exists()
        else "# QSASE Implementation Log\n"
    )
    marker = f"<!-- {PHASE_ID} -->"
    entry = (
        f"{marker}\n"
        f"## QSASE-3: Historical Source-Price Memory\n\n"
        f"- Generated at: `{memory.get('generated_at')}`\n"
        f"- Status: `{memory.get('status')}`\n"
        f"- Runtime artifact: `data/runtime/{PRIMARY_ARTIFACT}`\n"
        f"- Memory records: `{memory.get('memory_record_count')}`\n"
        f"- Point-in-time safe records: `{memory.get('point_in_time_safe_record_count')}`\n"
        f"- Missing windows: `{memory.get('missing_window_record_count')}`\n"
        f"- Safety: historical replay cannot advance the 30-day paper growth trial, create paper proof ledger credit, submit orders, write brokers, or enable live capital.\n"
    )
    if marker in existing:
        before = existing.split(marker, 1)[0].rstrip()
        updated = before + "\n\n" + entry
    elif existing.endswith("\n"):
        updated = existing + "\n" + entry
    else:
        updated = existing + "\n\n" + entry
    log_path.write_text(updated, encoding="utf-8")


def write_historical_source_price_memory(
    memory: dict[str, Any],
    settings: Settings | None = None,
    *,
    append_history: bool = True,
    append_log: bool = True,
) -> dict[str, str]:
    runtime_dir = _runtime_dir(settings)
    runtime_dir.mkdir(parents=True, exist_ok=True)
    records = memory.get("records", [])
    missing_windows = memory.get("missing_windows", [])
    summary = _summary_without_records(memory)
    paths = {
        "memory": runtime_dir / PRIMARY_ARTIFACT,
        "memory_records": runtime_dir / MEMORY_JSONL_ARTIFACT,
        "coverage_map": runtime_dir / COVERAGE_MAP_ARTIFACT,
        "replay_manifest": runtime_dir / REPLAY_MANIFEST_ARTIFACT,
        "point_in_time_replay_index": runtime_dir / POINT_IN_TIME_REPLAY_INDEX_ARTIFACT,
        "missing_windows": runtime_dir / MISSING_WINDOWS_ARTIFACT,
        "dashboard_summary": runtime_dir / DASHBOARD_SUMMARY_ARTIFACT,
        "phase_status": runtime_dir / PHASE_STATUS_ARTIFACT,
    }
    _write_json(paths["memory"], summary)
    _write_jsonl(paths["memory_records"], records)
    _write_json(paths["coverage_map"], memory["coverage_map"])
    _write_json(paths["replay_manifest"], memory["replay_manifest"])
    _write_json(paths["point_in_time_replay_index"], memory["point_in_time_replay_index"])
    _write_jsonl(paths["missing_windows"], missing_windows)
    _write_json(paths["dashboard_summary"], memory["dashboard_safe_summary"])
    _write_json(paths["phase_status"], build_qsase_phase_implementation_status(memory))
    written = {key: str(path) for key, path in paths.items()}
    if append_history:
        history_path = runtime_dir / HISTORY_ARTIFACT
        events_path = runtime_dir / EVENTS_ARTIFACT
        _append_jsonl(
            history_path,
            {
                "generated_at": memory["generated_at"],
                "status": memory["status"],
                "memory_record_count": memory["memory_record_count"],
                "point_in_time_safe_record_count": memory["point_in_time_safe_record_count"],
                "missing_window_record_count": memory["missing_window_record_count"],
                "paper_growth_trial_calendar_advanced": False,
                "paper_proof_ledger_credit_granted": False,
            },
        )
        _append_jsonl(
            events_path,
            {
                "generated_at": memory["generated_at"],
                "event_type": "qsase_historical_source_price_memory_written",
                "status": memory["status"],
                "public_safe": True,
                "authority_flags_false": True,
            },
        )
        written["history"] = str(history_path)
        written["events"] = str(events_path)
    if append_log:
        _append_implementation_log(memory)
        written["implementation_log"] = str(_repo_root() / IMPLEMENTATION_LOG)
    return written


def build_and_write_historical_source_price_memory(
    settings: Settings | None = None,
) -> tuple[dict[str, Any], dict[str, str], list[str]]:
    memory = build_historical_source_price_memory(settings)
    errors = validate_historical_source_price_memory(memory)
    written = write_historical_source_price_memory(memory, settings)
    return memory, written, errors


def validate_negative_historical_memory_probes() -> list[str]:
    base = build_historical_source_price_memory()
    errors: list[str] = []
    for flag in HISTORICAL_MEMORY_AUTHORITY_FLAGS:
        probe = copy.deepcopy(base)
        probe["authority_flags"][flag] = True
        if not any(flag in error for error in validate_historical_source_price_memory(probe)):
            errors.append(f"negative_probe_failed_for_{flag}")

    proof_probe = copy.deepcopy(base)
    proof_probe["records"][0]["paper_proof_ledger_eligible"] = True
    if not any("paper_proof_ledger" in error for error in validate_historical_source_price_memory(proof_probe)):
        errors.append("negative_probe_failed_for_paper_proof_ledger")

    future_feature_probe = copy.deepcopy(base)
    future_feature_probe["records"][0]["feature_availability"]["feature_timestamp"] = "2999-01-01T00:00:00+00:00"
    if not any("future_feature_timestamp" in error for error in validate_historical_source_price_memory(future_feature_probe)):
        errors.append("negative_probe_failed_for_future_feature_timestamp")

    leakage_probe = copy.deepcopy(base)
    leakage_probe["records"][0]["features"]["return_1d"] = 0.1
    if not any("outcome_feature_leakage" in error for error in validate_historical_source_price_memory(leakage_probe)):
        errors.append("negative_probe_failed_for_outcome_feature_leakage")

    calendar_probe = copy.deepcopy(base)
    calendar_probe["calendar_integrity"]["paper_growth_trial_calendar_advanced"] = True
    if not any("paper_growth_trial_calendar" in error for error in validate_historical_source_price_memory(calendar_probe)):
        errors.append("negative_probe_failed_for_calendar_integrity")

    return errors


if __name__ == "__main__":
    payload = build_historical_source_price_memory()
    print(_json_dump(_summary_without_records(payload)))
