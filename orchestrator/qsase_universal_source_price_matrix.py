"""QSASE-2 universal source-price pattern matrix.

This phase normalizes Qadam's source universe against its watched trading
universe. It is a research-only substrate: it creates no strategy hypotheses,
trade candidates, risk approvals, paper orders, broker writes, or proof credit.
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

SCHEMA_VERSION = "qsase_universal_source_price_matrix.v1"
PHASE_ID = "qsase_2_universal_source_price_pattern_matrix"
PHASE_NAME = "QSASE-2: Universal Source-Price Pattern Matrix"
IMPLEMENTATION_LOG = "docs/qsase-implementation-log.md"

PRIMARY_ARTIFACT = "qsase_universal_source_price_matrix.json"
SOURCE_UNIVERSE_ARTIFACT = "qsase_source_universe.json"
TRADING_UNIVERSE_ARTIFACT = "qsase_trading_universe.json"
SOURCE_PRICE_EDGES_ARTIFACT = "qsase_source_price_edges.jsonl"
EVENTS_ARTIFACT = "qsase_universal_source_price_matrix_events.jsonl"
HISTORY_ARTIFACT = "qsase_universal_source_price_matrix_history.jsonl"
DASHBOARD_SUMMARY_ARTIFACT = "qsase_universal_source_price_matrix_dashboard_summary.json"

TIME_WINDOWS = [
    "pre_event_baseline",
    "event_time_move",
    "1d_forward",
    "3d_forward",
    "5d_forward",
    "10d_forward",
    "20d_forward",
    "60d_forward",
]

MATRIX_AUTHORITY_FLAGS = {
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
    "proof_credit_allowed": False,
}

SUPPLEMENTAL_SOURCE_KEYS = {
    "ais_or_shipping",
    "alpaca",
    "bookmap",
    "conflict_tracker",
    "reddit",
    "reddit_narrative_proxy",
    "social.rss",
    "tradingview",
    "tradingview_mcp",
    "yahoo_finance",
    "yahoo_finance_or_tradingview",
}

PREDICTION_MARKET_KEYS = {
    "kalshi",
    "oddspipe",
    "polymarket",
    "prediction_market",
    "prediction_markets",
}

DEFAULT_FAMILY_SYMBOLS = {
    "semiconductors": ["SMH", "SOXX", "NVDA", "QQQ"],
    "semiconductor": ["SMH", "SOXX", "NVDA", "QQQ"],
    "defence": ["ITA", "PPA", "XAR", "LMT"],
    "defense": ["ITA", "PPA", "XAR", "LMT"],
    "silver": ["SLV", "SIL", "SI=F"],
    "crude_oil": ["USO", "XLE", "CL=F", "BNO"],
    "crude oil": ["USO", "XLE", "CL=F", "BNO"],
    "prediction_markets": ["KALSHI:EVENTS", "POLYMARKET:EVENTS"],
    "prediction markets": ["KALSHI:EVENTS", "POLYMARKET:EVENTS"],
    "macro_watchlist": ["SPY", "QQQ", "GLD", "USO"],
}

REQUIRED_ROW_FIELDS = [
    "schema_version",
    "matrix_row_id",
    "generated_at",
    "source_event_id",
    "source_key",
    "source_pipeline",
    "source_event_timestamp",
    "source_event_type",
    "source_trust_score",
    "source_freshness_status",
    "source_credential_status",
    "market_symbol",
    "market_family",
    "market_observation_timestamp",
    "relationship_type",
    "time_window",
    "price_before",
    "price_after",
    "forward_return",
    "volatility_before",
    "volatility_after",
    "volume_context",
    "market_confirmation_status",
    "strategy_labels",
    "paper_route_available",
    "backtest_only",
    "proof_credit_allowed",
    "execution_allowed",
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


def _age_seconds(value: Any, now: datetime) -> int | None:
    parsed = _parse_datetime(value)
    if parsed is None:
        return None
    return max(0, int((now - parsed).total_seconds()))


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


def _bool(value: Any) -> bool:
    return value if isinstance(value, bool) else False


def _clean_key(value: Any) -> str:
    text = str(value or "").strip().lower()
    return text.replace(" / ", "_").replace("/", "_").replace(" ", "_").replace("-", "_")


def _relative_runtime_path(path: Path) -> str:
    try:
        return str(path.relative_to(_repo_root()))
    except ValueError:
        return str(path)


def _hash_id(parts: list[Any], prefix: str) -> str:
    raw = "|".join(str(part) for part in parts)
    return f"{prefix}:{hashlib.sha256(raw.encode('utf-8')).hexdigest()[:20]}"


def _timestamp_for_source(record: dict[str, Any], fallback: str) -> str:
    for key in (
        "observed_at",
        "provider_observation_at",
        "event_timestamp",
        "updated_at",
        "created_at",
    ):
        value = record.get(key)
        if _parse_datetime(value):
            return str(value)
    # A health-check or matrix-generation timestamp is not source evidence.
    return ""


def _freshness_status(timestamp: Any, now: datetime) -> tuple[str, int | None]:
    age = _age_seconds(timestamp, now)
    if age is None:
        return "unknown", None
    if age <= 6 * 60 * 60:
        return "fresh", age
    if age <= 24 * 60 * 60:
        return "recent", age
    if age <= 7 * 24 * 60 * 60:
        return "stale", age
    return "very_stale", age


def _trust_posture(score: Any) -> str:
    value = _float(score)
    if value is None:
        return "trust_unknown"
    if value >= 0.8:
        return "high_trust"
    if value >= 0.6:
        return "moderate_trust"
    if value >= 0.45:
        return "context_trust"
    return "low_trust"


def _credential_status(record: dict[str, Any]) -> str:
    source_key = _clean_key(record.get("source_key"))
    registry_status = str(record.get("registry_status") or record.get("readiness") or "").lower()
    source_name = str(record.get("source_name") or "").lower()
    if record.get("proxy_coverage_active") is True:
        return "covered_by_proxy_oauth_optional"
    if source_key == "reddit" and (
        "adapter_live_via_reddit_narrative_proxy" in registry_status
        or "reddit narrative proxy" in source_name
    ):
        return "covered_by_proxy_oauth_optional"
    explicit = record.get("credential_status")
    if isinstance(explicit, str) and explicit:
        return explicit
    if record.get("runtime_status") == "unavailable_missing_credentials":
        return "missing"
    missing = record.get("missing_secrets")
    if isinstance(missing, list) and missing:
        return "missing"
    configured = record.get("configured_secrets")
    if isinstance(configured, list) and configured:
        return "configured"
    auth = str(record.get("auth") or "").lower()
    if auth in {"", "none", "not_required", "internal"}:
        return "not_required"
    return "unknown"


def _source_state(record: dict[str, Any], credential_status: str) -> str:
    status = str(record.get("status") or record.get("runtime_status") or "").lower()
    readiness = str(record.get("readiness") or record.get("registry_status") or "").lower()
    if credential_status in {"missing", "missing_optional", "unavailable_missing_credentials"}:
        return "credential_gated"
    if "degraded" in status or "degraded" in readiness or record.get("degraded_reason"):
        return "degraded"
    if status in {"online", "ok", "ready"}:
        return "online"
    if "live_optional" in status or "adapter_live_optional" in readiness:
        return "live_optional"
    if "sample_ready" in status:
        return "sample_ready"
    if "disabled" in status:
        return "disabled"
    if status:
        return status
    return "registered"


def _is_supplemental_source(source_key: str, record: dict[str, Any]) -> bool:
    role = str(record.get("role") or "").lower()
    pipeline = str(record.get("pipeline") or "").lower()
    return (
        source_key in SUPPLEMENTAL_SOURCE_KEYS
        or "supplemental" in role
        or "paper_account_context" in role
        or (pipeline == "market" and source_key in SUPPLEMENTAL_SOURCE_KEYS)
    )


def _source_can_contribute_quorum(
    source_key: str,
    record: dict[str, Any],
    state: str,
    credential_status: str,
    supplemental: bool,
    freshness_status: str,
    provider_backed_observation: bool,
) -> tuple[bool, str]:
    if supplemental:
        return False, "supplemental_context_cannot_satisfy_source_quorum"
    if credential_status in {"missing", "missing_optional", "unavailable_missing_credentials"}:
        return False, "credential_gated_source_cannot_satisfy_source_quorum"
    if state in {"degraded", "disabled", "credential_gated"}:
        return False, f"{state}_source_cannot_satisfy_source_quorum"
    if not provider_backed_observation:
        return False, "provider_backed_observation_required_for_current_quorum"
    if freshness_status not in {"fresh", "recent"}:
        return False, "fresh_provider_observation_required_for_current_quorum"
    if source_key in PREDICTION_MARKET_KEYS:
        return False, "prediction_market_context_requires_governed_route_before_quorum"
    eligible = record.get("eligible_for_signal_review")
    if eligible is False:
        return False, "source_not_eligible_for_signal_review"
    usable = record.get("usable_for_research_context")
    if usable is False:
        return False, "source_not_usable_for_research_context"
    return True, "canonical_research_source_available_for_candidate_level_quorum"


def _merge_source_record(target: dict[str, Any], update: dict[str, Any], provenance: str) -> None:
    for key, value in update.items():
        if value in (None, "", [], {}):
            continue
        if key not in target or target.get(key) in (None, "", [], {}):
            target[key] = value
    refs = target.setdefault("provenance_refs", [])
    if provenance not in refs:
        refs.append(provenance)


def _build_context(settings: Settings | None, now: datetime) -> dict[str, Any]:
    runtime_dir = _runtime_dir(settings)
    return {
        "runtime_dir": runtime_dir,
        "data_environment_map": _read_json(runtime_dir / "data_environment_map.json"),
        "cockpit_status": _read_json(runtime_dir / "cockpit-status.json"),
        "paperops_summary": _read_json(runtime_dir / "paperops_autonomous_pass_summary.json"),
        "self_model": _read_json(runtime_dir / "qsase_self_model.json"),
        "market_context": _read_json(runtime_dir / "market_context_packet.json"),
        "source_heartbeats": _read_jsonl(runtime_dir / "source_heartbeats.jsonl", limit=10),
        "paper_positions": _read_jsonl(runtime_dir / "paper_positions.jsonl", limit=50),
        "alpaca_paper_mirror": _read_json(runtime_dir / "alpaca_paper_mirror.json"),
        "phase5_prediction_market_adapter": _read_json(
            runtime_dir / "phase5_prediction_market_adapter.json"
        ),
        "phase1_live_source_validation": _read_json(
            runtime_dir / "phase1_live_source_validation.json"
        ),
        "universe_freeze": _read_json(runtime_dir / "qsase_backtest_universe_freeze.json"),
        "now": now,
    }


def build_qsase_source_universe(
    context: dict[str, Any],
    generated_at: str,
) -> dict[str, Any]:
    now = context["now"]
    data_environment = context["data_environment_map"]
    cockpit = context["cockpit_status"]
    paperops = context["paperops_summary"]
    market_context = context["market_context"]
    universe_freeze = context.get("universe_freeze")
    if not isinstance(universe_freeze, dict):
        universe_freeze = {}
    frozen_source_keys = {
        _clean_key(row.get("source_key"))
        for row in universe_freeze.get("sources", [])
        if isinstance(row, dict) and row.get("source_key")
    }

    records_by_key: dict[str, dict[str, Any]] = {}

    for record in data_environment.get("sources", []):
        if not isinstance(record, dict):
            continue
        source_key = _clean_key(record.get("source_key"))
        if not source_key:
            continue
        target = records_by_key.setdefault(source_key, {"source_key": source_key})
        _merge_source_record(target, record, "data/runtime/data_environment_map.json")

    mission = cockpit.get("mission_control") if isinstance(cockpit.get("mission_control"), dict) else {}
    data_sources = mission.get("data_sources") if isinstance(mission.get("data_sources"), dict) else {}
    for record in data_sources.get("ledger", []):
        if not isinstance(record, dict):
            continue
        source_key = _clean_key(record.get("source_key"))
        if not source_key:
            continue
        target = records_by_key.setdefault(source_key, {"source_key": source_key})
        _merge_source_record(target, record, "data/runtime/cockpit-status.json:mission_control.data_sources.ledger")

    source_gap_visibility = paperops.get("source_gap_visibility")
    if not isinstance(source_gap_visibility, dict):
        source_gap_visibility = {}
    for record in source_gap_visibility.get("source_gap_records", []):
        if not isinstance(record, dict):
            continue
        source_key = _clean_key(record.get("source_key"))
        if not source_key:
            continue
        target = records_by_key.setdefault(source_key, {"source_key": source_key})
        _merge_source_record(target, record, "data/runtime/paperops_autonomous_pass_summary.json:source_gap_visibility")

    for packet in market_context.get("recent_packets", []):
        if not isinstance(packet, dict):
            continue
        for record in packet.get("source_taxonomy", []):
            if not isinstance(record, dict):
                continue
            source_key = _clean_key(record.get("source_key"))
            if not source_key:
                continue
            target = records_by_key.setdefault(source_key, {"source_key": source_key})
            update = dict(record)
            update.setdefault("pipeline", "market_context_taxonomy")
            _merge_source_record(target, update, "data/runtime/market_context_packet.json:recent_packets.source_taxonomy")

    for heartbeat in context.get("source_heartbeats", []):
        summary = heartbeat.get("summary") if isinstance(heartbeat.get("summary"), dict) else {}
        missing = summary.get("missing_credentials") if isinstance(summary.get("missing_credentials"), dict) else {}
        for source_key, secret_names in missing.items():
            clean = _clean_key(source_key)
            target = records_by_key.setdefault(clean, {"source_key": clean})
            update = {
                "source_key": clean,
                "credential_status": "missing",
                "missing_secrets": secret_names if isinstance(secret_names, list) else [],
                "checked_at": heartbeat.get("checked_at"),
            }
            _merge_source_record(target, update, "data/runtime/source_heartbeats.jsonl")

    live_validation = context.get("phase1_live_source_validation")
    if not isinstance(live_validation, dict):
        live_validation = {}
    for validation in live_validation.get("validations", []):
        if not isinstance(validation, dict):
            continue
        source_key = _clean_key(validation.get("source_key"))
        if not source_key:
            continue
        target = records_by_key.setdefault(source_key, {"source_key": source_key})
        target["latest_health_check_at"] = validation.get("checked_at")
        target["latest_validation_status"] = validation.get("validation_status")
        target["evidence_origin"] = validation.get("evidence_origin") or "status_only"
        target["sample_fixture"] = validation.get("sample_fixture") is True
        target["provider_backed_observation"] = (
            validation.get("freshness_evidence_eligible") is True
        )
        if validation.get("freshness_evidence_eligible") is True:
            target["observed_at"] = validation.get("provider_observation_at")
            target["provider_event_latest_at"] = validation.get("latest_event_at")
            target["status"] = "online"
            target["runtime_status"] = "provider_live_read_only"
            target["eligible_for_signal_review"] = True
            target["usable_for_research_context"] = True
        elif validation.get("validation_status") == "degraded":
            # Preserve the latest failed live probe as health truth without
            # allowing its check timestamp to masquerade as fresh evidence.
            target["status"] = "degraded"
            target["runtime_status"] = "provider_probe_degraded"
            target["degraded_reason"] = (
                validation.get("degraded_reason")
                or "latest_live_provider_probe_did_not_produce_eligible_evidence"
            )
            target["eligible_for_signal_review"] = False
        refs = target.setdefault("provenance_refs", [])
        ref = "data/runtime/phase1_live_source_validation.json"
        if ref not in refs:
            refs.append(ref)

    sources: list[dict[str, Any]] = []
    for source_key in sorted(records_by_key):
        if frozen_source_keys and source_key not in frozen_source_keys:
            continue
        record = records_by_key[source_key]
        credential_status = _credential_status(record)
        state = _source_state(record, credential_status)
        timestamp = _timestamp_for_source(record, generated_at)
        freshness_status, age = _freshness_status(timestamp, now)
        supplemental = _is_supplemental_source(source_key, record)
        quorum_allowed, quorum_reason = _source_can_contribute_quorum(
            source_key,
            record,
            state,
            credential_status,
            supplemental,
            freshness_status,
            record.get("provider_backed_observation") is True,
        )
        trust_score = _float(record.get("trust_score"))
        pipeline = str(record.get("pipeline") or "unclassified")
        source = {
            "source_key": source_key,
            "source_name": record.get("source_name") or source_key,
            "source_pipeline": pipeline,
            "source_family": pipeline,
            "state": state,
            "adapter_status": record.get("status")
            or record.get("runtime_status")
            or record.get("registry_status")
            or "registered",
            "credential_status": credential_status,
            "credential_gated": credential_status
            in {"missing", "missing_optional", "unavailable_missing_credentials"},
            "freshness_status": freshness_status,
            "observed_timestamp": timestamp,
            "observed_age_seconds": age,
            "latest_health_check_at": record.get("latest_health_check_at"),
            "provider_event_latest_at": record.get("provider_event_latest_at"),
            "evidence_origin": record.get("evidence_origin") or "unverified_registry_state",
            "provider_backed_observation": record.get("provider_backed_observation") is True,
            "sample_fixture": record.get("sample_fixture") is True,
            "trust_score": trust_score,
            "trust_posture": _trust_posture(trust_score),
            "research_context_allowed": state not in {"disabled"} and credential_status != "missing",
            "eligible_for_signal_review": record.get("eligible_for_signal_review", True),
            "supplemental_context_only": supplemental,
            "source_quorum_contribution": {
                "can_contribute": quorum_allowed,
                "reason": quorum_reason,
                "candidate_level_gate_required": True,
            },
            "telegram_command_authority": False,
            "trade_candidate_creation_allowed": False,
            "execution_allowed": False,
            "proof_credit_allowed": False,
            "raw_payload_reference": None,
            "durable_replay_reference": record.get("data_environment_map_path"),
            "provenance": [
                {
                    "artifact": ref,
                    "role": "source_state",
                    "public_safe": True,
                }
                for ref in record.get("provenance_refs", [])
            ],
        }
        sources.append(source)

    by_family: dict[str, dict[str, Any]] = {}
    for source in sources:
        family = source["source_family"]
        bucket = by_family.setdefault(
            family,
            {
                "family": family,
                "source_count": 0,
                "fresh_count": 0,
                "credential_gated_count": 0,
                "quorum_contributing_count": 0,
                "degraded_count": 0,
                "provenance": [],
            },
        )
        bucket["source_count"] += 1
        if source["freshness_status"] in {"fresh", "recent"}:
            bucket["fresh_count"] += 1
        if source["credential_gated"]:
            bucket["credential_gated_count"] += 1
        if source["source_quorum_contribution"]["can_contribute"]:
            bucket["quorum_contributing_count"] += 1
        if source["state"] == "degraded":
            bucket["degraded_count"] += 1
        for provenance in source["provenance"]:
            artifact = provenance["artifact"]
            if artifact not in bucket["provenance"]:
                bucket["provenance"].append(artifact)

    credential_gated_count = sum(1 for source in sources if source["credential_gated"])
    degraded_count = sum(1 for source in sources if source["state"] == "degraded")
    supplemental_count = sum(1 for source in sources if source["supplemental_context_only"])
    quorum_count = sum(1 for source in sources if source["source_quorum_contribution"]["can_contribute"])
    stale_count = sum(1 for source in sources if source["freshness_status"] in {"stale", "very_stale", "unknown"})

    return {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "qsase_source_universe",
        "generated_at": generated_at,
        "status": "source_universe_degraded"
        if credential_gated_count or degraded_count or stale_count
        else "source_universe_ready",
        "source_count": len(sources),
        "universe_freeze_applied": bool(frozen_source_keys),
        "frozen_source_count": len(frozen_source_keys),
        "excluded_noncanonical_source_keys": sorted(set(records_by_key) - frozen_source_keys)
        if frozen_source_keys
        else [],
        "source_quorum_contributing_count": quorum_count,
        "credential_gated_source_count": credential_gated_count,
        "degraded_source_count": degraded_count,
        "supplemental_source_count": supplemental_count,
        "stale_or_unknown_freshness_count": stale_count,
        "source_families": by_family,
        "sources": sources,
        "coverage": {
            "total_eligible_source_count": len(sources),
            "source_count_with_historical_coverage": 0,
            "source_count_with_live_only_coverage": sum(
                1 for source in sources if source["freshness_status"] in {"fresh", "recent"}
            ),
            "source_count_blocked_by_missing_credentials": credential_gated_count,
            "source_count_blocked_by_provider_limits": 0,
            "source_count_with_stale_data": stale_count,
            "coverage_by_source_class": by_family,
            "historical_coverage_note": "deferred_to_qsase_3_historical_source_price_memory",
        },
        "authority_flags": dict(MATRIX_AUTHORITY_FLAGS),
        "public_safe": True,
        "command_disabled": True,
    }


def _market_family_key(value: Any) -> str:
    text = str(value or "").strip()
    return _clean_key(text)


def _family_symbols(family_key: str, family_label: str) -> list[str]:
    symbols = DEFAULT_FAMILY_SYMBOLS.get(family_key) or DEFAULT_FAMILY_SYMBOLS.get(family_label)
    return list(symbols or [family_label or family_key])


def _paperability(symbol: str, family_key: str, route_fit: str) -> tuple[str, bool]:
    upper = symbol.upper()
    if family_key in {"prediction_markets", "prediction_market"} or upper.startswith(("KALSHI:", "POLYMARKET:")):
        return "context_only_until_governed_prediction_market_paper_route", False
    if "=" in symbol or upper.startswith("TVC:"):
        return "research_only_proxy_not_direct_alpaca_paperable", False
    if "blocked" in route_fit:
        return "observable_not_paper_route_ready", False
    if "paper_proxy_fit" in route_fit or route_fit in {
        "strong_alpaca_paper_proxy_fit",
        "clean_alpaca_paper_proxy_fit",
        "conditional_paper_proxy_fit",
    }:
        return "alpaca_paper_proxy_available_guarded_route_only", True
    return "paperability_unknown_context_only", False


def _collect_market_records(market_context: dict[str, Any]) -> dict[str, dict[str, Any]]:
    records: dict[str, dict[str, Any]] = {}
    for packet in market_context.get("recent_packets", []):
        if not isinstance(packet, dict):
            continue
        generated_at = packet.get("generated_at") or market_context.get("generated_at")
        for section, status_key in (
            ("price_volume_context", "price_sample"),
            ("technical_context", "technical_sample"),
            ("orderflow_context", "orderflow_sample"),
        ):
            context_section = packet.get(section)
            if not isinstance(context_section, dict):
                continue
            for record in context_section.get("records", []):
                if not isinstance(record, dict):
                    continue
                symbol = str(record.get("symbol") or "").strip()
                if not symbol:
                    continue
                current = records.setdefault(symbol, {})
                current.update(
                    {
                        "symbol": symbol,
                        "provider": record.get("source") or context_section.get("provider"),
                        "market_observation_timestamp": generated_at,
                        "price_data_state": status_key,
                        "last_close": record.get("last_close"),
                        "previous_close": record.get("previous_close"),
                        "rolling_volatility_20d": record.get("rolling_volatility_20d"),
                        "volume_ratio": record.get("volume_ratio"),
                        "market_state": record.get("market_state"),
                        "technical_score": record.get("technical_score"),
                        "orderflow_score": record.get("orderflow_score"),
                        "authority": record.get("authority"),
                    }
                )
    return records


def build_qsase_trading_universe(
    context: dict[str, Any],
    generated_at: str,
) -> dict[str, Any]:
    cockpit = context["cockpit_status"]
    market_context = context["market_context"]
    paper_positions = context.get("paper_positions", [])
    mission = cockpit.get("mission_control") if isinstance(cockpit.get("mission_control"), dict) else {}
    strategy = mission.get("strategy") if isinstance(mission.get("strategy"), dict) else {}
    families = strategy.get("strategy_families") if isinstance(strategy.get("strategy_families"), list) else []
    universe = strategy.get("universe") if isinstance(strategy.get("universe"), list) else []
    market_records = _collect_market_records(market_context)
    universe_freeze = context.get("universe_freeze")
    if not isinstance(universe_freeze, dict):
        universe_freeze = {}
    frozen_symbols = {
        str(row.get("symbol") or "").strip()
        for row in universe_freeze.get("instruments", [])
        if isinstance(row, dict) and str(row.get("symbol") or "").strip()
    }

    instruments_by_key: dict[str, dict[str, Any]] = {}

    for family in families:
        if not isinstance(family, dict):
            continue
        family_label = str(family.get("instrument") or family.get("label") or family.get("key") or "")
        family_key = _market_family_key(family_label or family.get("key"))
        route_fit = str(family.get("route_fit") or "")
        symbols = _family_symbols(family_key, family_label)
        for symbol in symbols:
            paperability_state, paper_route_available = _paperability(symbol, family_key, route_fit)
            market_record = market_records.get(symbol, {})
            instrument_key = _clean_key(symbol)
            instruments_by_key[instrument_key] = {
                "instrument_id": f"qsase-instrument:{instrument_key}",
                "symbol": symbol,
                "display_name": family.get("label") or symbol,
                "market_family": family_key,
                "market_family_label": family_label,
                "venue_or_provider": market_record.get("provider") or "alpaca_paper_proxy_or_context",
                "mapping_state": "mapped_to_strategy_universe_family",
                "price_data_state": market_record.get("price_data_state") or "price_history_gap_explicit",
                "market_observation_timestamp": market_record.get("market_observation_timestamp")
                or market_context.get("generated_at")
                or generated_at,
                "price_or_odds_value": market_record.get("last_close"),
                "previous_price_or_odds_value": market_record.get("previous_close"),
                "rolling_volatility_20d": market_record.get("rolling_volatility_20d"),
                "volume_context": "available" if market_record.get("volume_ratio") is not None else "missing",
                "volatility_context": "available"
                if market_record.get("rolling_volatility_20d") is not None
                else "missing",
                "market_session_status": market_record.get("market_state") or "not_recorded",
                "paperability_state": paperability_state,
                "paper_route_available": paper_route_available,
                "paper_order_allowed": False,
                "broker_write_allowed": False,
                "live_route_enabled": False,
                "live_capital_enabled": False,
                "observable_for_research": True,
                "backtest_ready": False,
                "backtest_gap_reason": "historical_price_windows_deferred_to_qsase_3",
                "route_fit": route_fit,
                "qualified_setup_state": family.get("setup_state"),
                "provenance": [
                    {
                        "artifact": "data/runtime/cockpit-status.json:mission_control.strategy.strategy_families",
                        "role": "trading_universe_family",
                        "public_safe": True,
                    }
                ],
            }

    for family_label in universe:
        family_key = _market_family_key(family_label)
        for symbol in _family_symbols(family_key, str(family_label)):
            instrument_key = _clean_key(symbol)
            if instrument_key in instruments_by_key:
                continue
            paperability_state, paper_route_available = _paperability(symbol, family_key, "")
            instruments_by_key[instrument_key] = {
                "instrument_id": f"qsase-instrument:{instrument_key}",
                "symbol": symbol,
                "display_name": symbol,
                "market_family": family_key,
                "market_family_label": family_label,
                "venue_or_provider": "watched_market_context",
                "mapping_state": "mapped_from_watched_market_universe",
                "price_data_state": "price_history_gap_explicit",
                "market_observation_timestamp": market_context.get("generated_at") or generated_at,
                "price_or_odds_value": None,
                "previous_price_or_odds_value": None,
                "rolling_volatility_20d": None,
                "volume_context": "missing",
                "volatility_context": "missing",
                "market_session_status": "not_recorded",
                "paperability_state": paperability_state,
                "paper_route_available": paper_route_available,
                "paper_order_allowed": False,
                "broker_write_allowed": False,
                "live_route_enabled": False,
                "live_capital_enabled": False,
                "observable_for_research": True,
                "backtest_ready": False,
                "backtest_gap_reason": "historical_price_windows_deferred_to_qsase_3",
                "route_fit": "not_recorded",
                "qualified_setup_state": "not_recorded",
                "provenance": [
                    {
                        "artifact": "data/runtime/cockpit-status.json:mission_control.strategy.universe",
                        "role": "watched_market_family",
                        "public_safe": True,
                    }
                ],
            }

    for packet in market_context.get("recent_packets", []):
        if not isinstance(packet, dict):
            continue
        family_key = _market_family_key(packet.get("market_channel") or "market_context")
        for symbol in packet.get("watched_instruments", []):
            if not isinstance(symbol, str):
                continue
            instrument_key = _clean_key(symbol)
            if instrument_key in instruments_by_key:
                instruments_by_key[instrument_key]["provenance"].append(
                    {
                        "artifact": "data/runtime/market_context_packet.json:recent_packets.watched_instruments",
                        "role": "market_context_watch",
                        "public_safe": True,
                    }
                )
                continue
            market_record = market_records.get(symbol, {})
            paperability_state, paper_route_available = _paperability(symbol, family_key, "")
            instruments_by_key[instrument_key] = {
                "instrument_id": f"qsase-instrument:{instrument_key}",
                "symbol": symbol,
                "display_name": symbol,
                "market_family": family_key,
                "market_family_label": packet.get("market_channel") or "market_context",
                "venue_or_provider": market_record.get("provider") or "market_context_packet",
                "mapping_state": "mapped_from_market_context_packet",
                "price_data_state": market_record.get("price_data_state") or "price_history_gap_explicit",
                "market_observation_timestamp": market_record.get("market_observation_timestamp")
                or packet.get("generated_at")
                or generated_at,
                "price_or_odds_value": market_record.get("last_close"),
                "previous_price_or_odds_value": market_record.get("previous_close"),
                "rolling_volatility_20d": market_record.get("rolling_volatility_20d"),
                "volume_context": "available" if market_record.get("volume_ratio") is not None else "missing",
                "volatility_context": "available"
                if market_record.get("rolling_volatility_20d") is not None
                else "missing",
                "market_session_status": market_record.get("market_state") or "not_recorded",
                "paperability_state": paperability_state,
                "paper_route_available": paper_route_available,
                "paper_order_allowed": False,
                "broker_write_allowed": False,
                "live_route_enabled": False,
                "live_capital_enabled": False,
                "observable_for_research": True,
                "backtest_ready": False,
                "backtest_gap_reason": "historical_price_windows_deferred_to_qsase_3",
                "route_fit": "market_context_only",
                "qualified_setup_state": "not_recorded",
                "provenance": [
                    {
                        "artifact": "data/runtime/market_context_packet.json:recent_packets.watched_instruments",
                        "role": "market_context_watch",
                        "public_safe": True,
                    }
                ],
            }

    for position in paper_positions:
        if not isinstance(position, dict):
            continue
        symbol = str(position.get("instrument") or "").strip()
        if not symbol:
            continue
        instrument_key = _clean_key(symbol)
        if instrument_key in instruments_by_key:
            instruments_by_key[instrument_key]["open_paper_position_state"] = position.get("status")
            instruments_by_key[instrument_key]["provenance"].append(
                {
                    "artifact": "data/runtime/paper_positions.jsonl",
                    "role": "read_only_paper_position_mirror",
                    "public_safe": True,
                }
            )

    excluded_noncanonical_symbols = sorted(
        record["symbol"]
        for record in instruments_by_key.values()
        if frozen_symbols and record["symbol"] not in frozen_symbols
    )
    instruments = [
        instruments_by_key[key]
        for key in sorted(instruments_by_key)
        if not frozen_symbols or instruments_by_key[key]["symbol"] in frozen_symbols
    ]
    family_counts: dict[str, int] = {}
    for instrument in instruments:
        family_counts[instrument["market_family"]] = family_counts.get(instrument["market_family"], 0) + 1

    price_history_count = sum(
        1 for instrument in instruments if instrument["price_data_state"] != "price_history_gap_explicit"
    )
    paper_route_count = sum(1 for instrument in instruments if instrument["paper_route_available"])
    context_only_count = sum(1 for instrument in instruments if not instrument["paper_route_available"])

    return {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "qsase_trading_universe",
        "generated_at": generated_at,
        "status": "trading_universe_degraded"
        if price_history_count < len(instruments)
        else "trading_universe_ready",
        "watched_market_count": len(instruments),
        "universe_freeze_applied": bool(frozen_symbols),
        "frozen_watched_market_count": len(frozen_symbols),
        "excluded_noncanonical_symbols": excluded_noncanonical_symbols,
        "market_count_with_price_history": 0,
        "market_count_with_only_current_price": price_history_count,
        "market_count_with_paper_route_availability": paper_route_count,
        "market_count_context_only": context_only_count,
        "coverage_by_market_family": family_counts,
        "instruments": instruments,
        "coverage": {
            "historical_price_window_status": "deferred_to_qsase_3_historical_source_price_memory",
            "current_sample_price_count": price_history_count,
            "paper_route_available_count": paper_route_count,
            "live_route_enabled_count": 0,
        },
        "authority_flags": dict(MATRIX_AUTHORITY_FLAGS),
        "public_safe": True,
        "command_disabled": True,
    }


def _price_fields(instrument: dict[str, Any], time_window: str) -> dict[str, Any]:
    previous_price = _float(instrument.get("previous_price_or_odds_value"))
    current_price = _float(instrument.get("price_or_odds_value"))
    has_current_move = previous_price is not None and current_price is not None and time_window in {
        "pre_event_baseline",
        "event_time_move",
    }
    if has_current_move and previous_price:
        forward_return = (current_price - previous_price) / previous_price
    else:
        forward_return = None
    volatility = None
    if instrument.get("volatility_context") == "available":
        volatility = instrument.get("rolling_volatility_20d")
    return {
        "price_before": previous_price if has_current_move else None,
        "price_after": current_price if has_current_move else None,
        "forward_return": forward_return,
        "volatility_before": volatility,
        "volatility_after": volatility,
        "market_confirmation_status": "current_sample_available"
        if has_current_move
        else instrument.get("price_data_state", "price_history_gap_explicit"),
        "data_completeness_score": 0.35 if has_current_move else 0.1,
        "time_window_status": "current_sample_only"
        if has_current_move
        else "pending_qsase_3_historical_memory",
    }


def _stable_row_id(source_key: str, instrument_id: str, time_window: str) -> str:
    return _hash_id(
        [SCHEMA_VERSION, source_key, instrument_id, "source_to_asset", time_window],
        "qsase-matrix",
    )


def build_source_price_edges(
    source_universe: dict[str, Any],
    trading_universe: dict[str, Any],
    generated_at: str,
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for source in source_universe["sources"]:
        source_event_timestamp = source.get("observed_timestamp") or generated_at
        source_event_id = _hash_id(
            [source["source_key"], source_event_timestamp, source["state"]],
            "qsase-source-event",
        )
        for instrument in trading_universe["instruments"]:
            for time_window in TIME_WINDOWS:
                price = _price_fields(instrument, time_window)
                row = {
                    "schema_version": SCHEMA_VERSION,
                    "matrix_row_id": _stable_row_id(
                        source["source_key"],
                        instrument["instrument_id"],
                        time_window,
                    ),
                    "generated_at": generated_at,
                    "source_event_id": source_event_id,
                    "source_key": source["source_key"],
                    "source_pipeline": source["source_pipeline"],
                    "source_event_timestamp": source_event_timestamp,
                    "source_event_type": "source_state_snapshot",
                    "source_trust_score": source["trust_score"],
                    "source_freshness_status": source["freshness_status"],
                    "source_credential_status": source["credential_status"],
                    "source_quorum_credit_allowed": source["source_quorum_contribution"]["can_contribute"],
                    "source_quorum_reason": source["source_quorum_contribution"]["reason"],
                    "market_symbol": instrument["symbol"],
                    "market_instrument_id": instrument["instrument_id"],
                    "market_family": instrument["market_family"],
                    "market_observation_timestamp": instrument["market_observation_timestamp"],
                    "relationship_type": "source_to_asset",
                    "relationship_state": "coverage_edge_ready"
                    if price["market_confirmation_status"] == "current_sample_available"
                    else "coverage_edge_with_explicit_price_gap",
                    "time_window": time_window,
                    "price_before": price["price_before"],
                    "price_after": price["price_after"],
                    "forward_return": price["forward_return"],
                    "volatility_before": price["volatility_before"],
                    "volatility_after": price["volatility_after"],
                    "volume_context": instrument["volume_context"],
                    "market_confirmation_status": price["market_confirmation_status"],
                    "data_completeness_score": price["data_completeness_score"],
                    "time_window_status": price["time_window_status"],
                    "strategy_labels": [],
                    "paperability_state": instrument["paperability_state"],
                    "paper_route_available": instrument["paper_route_available"],
                    "backtest_only": True,
                    "proof_credit_allowed": False,
                    "execution_allowed": False,
                    "paper_order_allowed": False,
                    "broker_write_allowed": False,
                    "live_capital_enabled": False,
                    "trade_candidate_creation_allowed": False,
                    "strategy_hypothesis_creation_allowed": False,
                    "public_safe": True,
                }
                rows.append(row)
    return rows


def build_qsase_universal_source_price_matrix(
    settings: Settings | None = None,
) -> dict[str, Any]:
    now = _now()
    generated_at = _iso(now)
    context = _build_context(settings, now)
    source_universe = build_qsase_source_universe(context, generated_at)
    trading_universe = build_qsase_trading_universe(context, generated_at)
    edges = build_source_price_edges(source_universe, trading_universe, generated_at)
    self_model = context["self_model"]

    self_model_present = bool(self_model)
    missing_required_state: list[str] = []
    if not self_model_present:
        missing_required_state.append("qsase_self_model_missing")
    if not source_universe["source_count"]:
        missing_required_state.append("source_universe_empty")
    if not trading_universe["watched_market_count"]:
        missing_required_state.append("trading_universe_empty")

    coverage_gaps: list[dict[str, Any]] = []
    if source_universe["credential_gated_source_count"]:
        coverage_gaps.append(
            {
                "gap_type": "credential_gated_sources",
                "count": source_universe["credential_gated_source_count"],
                "authority_impact": "cannot_satisfy_source_quorum",
            }
        )
    if source_universe["degraded_source_count"]:
        coverage_gaps.append(
            {
                "gap_type": "degraded_sources",
                "count": source_universe["degraded_source_count"],
                "authority_impact": "cannot_satisfy_source_quorum",
            }
        )
    if trading_universe["market_count_with_price_history"] < trading_universe["watched_market_count"]:
        coverage_gaps.append(
            {
                "gap_type": "historical_price_windows_pending",
                "count": trading_universe["watched_market_count"]
                - trading_universe["market_count_with_price_history"],
                "authority_impact": "research_only_until_qsase_3",
            }
        )

    expected_rows = (
        source_universe["source_count"]
        * trading_universe["watched_market_count"]
        * len(TIME_WINDOWS)
    )
    full_cross_product = expected_rows == len(edges) and expected_rows > 0
    degraded_reasons: list[str] = []
    hold_reasons = [gap["gap_type"] for gap in coverage_gaps]
    if self_model.get("status") in {"qsase_self_model_blocked", "qsase_self_model_stale"}:
        degraded_reasons.append("self_model_not_ready")
    status = "qsase_source_price_matrix_ready"
    if missing_required_state:
        status = "qsase_source_price_matrix_blocked"
    elif degraded_reasons:
        status = "qsase_source_price_matrix_degraded"
    elif hold_reasons:
        status = "qsase_source_price_matrix_ready_with_gaps"

    payload = {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "qsase_universal_source_price_matrix",
        "phase_id": PHASE_ID,
        "phase_name": PHASE_NAME,
        "generated_at": generated_at,
        "status": status,
        "public_safe": True,
        "command_disabled": True,
        "paper_only": True,
        "proposal_first": True,
        "research_only": True,
        "source_universe": source_universe,
        "trading_universe": trading_universe,
        "matrix_scope": {
            "relationship_types": ["source_to_asset"],
            "supported_future_relationship_types": [
                "source_to_source",
                "asset_to_asset",
                "source_cluster_to_asset",
                "regime_to_asset",
                "strategy_label_to_asset",
            ],
            "time_windows": TIME_WINDOWS,
            "all_sources_cross_all_markets": full_cross_product,
            "strategy_family_neutral": True,
            "strategy_labels_downstream_only": True,
            "source_count": source_universe["source_count"],
            "watched_market_count": trading_universe["watched_market_count"],
            "time_window_count": len(TIME_WINDOWS),
            "expected_row_count": expected_rows,
            "matrix_row_count": len(edges),
        },
        "coverage": {
            "coverage_gaps": coverage_gaps,
            "source_coverage": source_universe["coverage"],
            "market_coverage": trading_universe["coverage"],
            "minimum_observation_timestamp": min(
                [
                    source.get("observed_timestamp")
                    for source in source_universe["sources"]
                    if source.get("observed_timestamp")
                ]
                or [None]
            ),
            "maximum_observation_timestamp": max(
                [
                    source.get("observed_timestamp")
                    for source in source_universe["sources"]
                    if source.get("observed_timestamp")
                ]
                or [None]
            ),
            "coverage_by_time_window": {
                window: {
                    "row_count": sum(1 for edge in edges if edge["time_window"] == window),
                    "forward_outcome_available_count": sum(
                        1
                        for edge in edges
                        if edge["time_window"] == window and edge["forward_return"] is not None
                    ),
                }
                for window in TIME_WINDOWS
            },
        },
        "source_price_edges_path": f"data/runtime/{SOURCE_PRICE_EDGES_ARTIFACT}",
        "source_price_edge_count": len(edges),
        "source_price_edge_sample": edges[:10],
        "degraded_reasons": sorted(set(degraded_reasons)),
        "hold_reasons": sorted(set(hold_reasons)),
        "missing_required_state": missing_required_state,
        "self_model_ref": {
            "path": "data/runtime/qsase_self_model.json",
            "present": self_model_present,
            "status": self_model.get("status"),
            "generated_at": self_model.get("generated_at"),
        },
        "no_strategy_hypotheses_created": True,
        "no_trade_candidates_created": True,
        "no_paper_orders_created": True,
        "no_proof_credit_granted": True,
        "authority": universal_authority_flags(),
        "authority_flags": dict(MATRIX_AUTHORITY_FLAGS),
        "dashboard_safe_summary": {},
    }
    payload["dashboard_safe_summary"] = build_dashboard_summary(payload)
    return payload


def build_dashboard_summary(payload: dict[str, Any]) -> dict[str, Any]:
    source_universe = payload["source_universe"]
    trading_universe = payload["trading_universe"]
    return {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "qsase_universal_source_price_matrix_dashboard_summary",
        "generated_at": payload["generated_at"],
        "status": payload["status"],
        "public_safe": True,
        "command_disabled": True,
        "live_send_allowed": False,
        "summary_rows": [
            {"label": "Source universe", "value": source_universe["source_count"]},
            {"label": "Quorum-capable sources", "value": source_universe["source_quorum_contributing_count"]},
            {"label": "Credential-gated sources", "value": source_universe["credential_gated_source_count"]},
            {"label": "Watched instruments", "value": trading_universe["watched_market_count"]},
            {"label": "Paperable via guarded route", "value": trading_universe["market_count_with_paper_route_availability"]},
            {"label": "Source-price rows", "value": payload["source_price_edge_count"]},
            {"label": "Matrix scope", "value": "all_sources_x_all_watched_markets_x_time_windows"},
        ],
        "coverage_gaps": payload["coverage"]["coverage_gaps"],
        "authority_flags_false": all(value is False for value in payload["authority_flags"].values()),
        "research_only": True,
        "no_strategy_hypotheses_created": True,
        "no_trade_candidates_created": True,
        "no_paper_orders_created": True,
        "no_proof_credit_granted": True,
    }


def _validate_authority_flags(flags: dict[str, Any], prefix: str) -> list[str]:
    errors: list[str] = []
    for key, expected in MATRIX_AUTHORITY_FLAGS.items():
        if flags.get(key) is not expected:
            errors.append(f"{prefix}_{key}_must_be_false")
    return errors


def validate_qsase_universal_source_price_matrix(
    payload: dict[str, Any],
    edges: list[dict[str, Any]] | None = None,
) -> list[str]:
    errors: list[str] = []
    if payload.get("artifact_type") != "qsase_universal_source_price_matrix":
        errors.append("artifact_type_invalid")
    if payload.get("schema_version") != SCHEMA_VERSION:
        errors.append("schema_version_invalid")
    if payload.get("status") not in {
        "qsase_source_price_matrix_ready",
        "qsase_source_price_matrix_ready_with_gaps",
        "qsase_source_price_matrix_degraded",
        "qsase_source_price_matrix_blocked",
    }:
        errors.append("status_invalid")
    if payload.get("public_safe") is not True or payload.get("command_disabled") is not True:
        errors.append("public_safe_command_disabled_required")
    if payload.get("research_only") is not True:
        errors.append("research_only_required")
    for forbidden in (
        "strategy_hypotheses",
        "strategy_hypothesis",
        "trade_candidates",
        "paper_orders",
        "proof_credit",
    ):
        if forbidden in payload:
            errors.append(f"{forbidden}_must_not_exist_in_qsase_2")

    errors.extend(_validate_authority_flags(payload.get("authority_flags", {}), "matrix"))
    authority = payload.get("authority", {})
    if not isinstance(authority, dict) or any(value is not False for value in authority.values()):
        errors.append("universal_authority_flags_must_all_be_false")
    for key in (
        "no_strategy_hypotheses_created",
        "no_trade_candidates_created",
        "no_paper_orders_created",
        "no_proof_credit_granted",
    ):
        if payload.get(key) is not True:
            errors.append(f"{key}_must_be_true")

    source_universe = payload.get("source_universe")
    if not isinstance(source_universe, dict) or not source_universe.get("sources"):
        errors.append("source_universe_missing_or_empty")
        sources = []
    else:
        sources = source_universe["sources"]
        errors.extend(_validate_authority_flags(source_universe.get("authority_flags", {}), "source_universe"))

    source_keys = set()
    for source in sources:
        source_key = source.get("source_key")
        if not source_key:
            errors.append("source_missing_source_key")
            continue
        source_keys.add(source_key)
        if not source.get("provenance"):
            errors.append(f"source_{source_key}_missing_provenance")
        if not source.get("freshness_status"):
            errors.append(f"source_{source_key}_missing_freshness_status")
        if not source.get("trust_posture"):
            errors.append(f"source_{source_key}_missing_trust_posture")
        quorum = source.get("source_quorum_contribution")
        if not isinstance(quorum, dict):
            errors.append(f"source_{source_key}_missing_quorum_contribution")
            continue
        if source.get("credential_gated") and quorum.get("can_contribute"):
            errors.append(f"source_{source_key}_credential_gated_quorum_violation")
        if source.get("state") == "degraded" and quorum.get("can_contribute"):
            errors.append(f"source_{source_key}_degraded_quorum_violation")
        if source.get("supplemental_context_only") and quorum.get("can_contribute"):
            errors.append(f"source_{source_key}_supplemental_quorum_violation")
        if source_key in {"telegram", "telegram_apis_scrapers"} and source.get("telegram_command_authority") is not False:
            errors.append("telegram_command_authority_must_be_false")
        if source.get("execution_allowed") is not False or source.get("proof_credit_allowed") is not False:
            errors.append(f"source_{source_key}_authority_violation")

    trading_universe = payload.get("trading_universe")
    if not isinstance(trading_universe, dict) or not trading_universe.get("instruments"):
        errors.append("trading_universe_missing_or_empty")
        instruments = []
    else:
        instruments = trading_universe["instruments"]
        errors.extend(_validate_authority_flags(trading_universe.get("authority_flags", {}), "trading_universe"))

    instrument_ids = set()
    for instrument in instruments:
        instrument_id = instrument.get("instrument_id")
        symbol = instrument.get("symbol")
        if not instrument_id or not symbol:
            errors.append("instrument_missing_id_or_symbol")
            continue
        instrument_ids.add(instrument_id)
        for required in ("market_family", "mapping_state", "paperability_state", "price_data_state"):
            if not instrument.get(required):
                errors.append(f"instrument_{symbol}_missing_{required}")
        if not isinstance(instrument.get("paper_route_available"), bool):
            errors.append(f"instrument_{symbol}_paper_route_available_not_bool")
        for key in ("paper_order_allowed", "broker_write_allowed", "live_route_enabled", "live_capital_enabled"):
            if instrument.get(key) is not False:
                errors.append(f"instrument_{symbol}_{key}_must_be_false")

    edge_rows = edges if edges is not None else payload.get("source_price_edge_sample", [])
    if not isinstance(edge_rows, list) or not edge_rows:
        errors.append("source_price_edges_missing")
    for row in edge_rows:
        for field in REQUIRED_ROW_FIELDS:
            if field not in row:
                errors.append(f"edge_missing_{field}")
        source_key = row.get("source_key")
        instrument_id = row.get("market_instrument_id")
        time_window = row.get("time_window")
        if source_key not in source_keys:
            errors.append(f"edge_unknown_source_{source_key}")
        if instrument_id not in instrument_ids:
            errors.append(f"edge_unknown_instrument_{instrument_id}")
        if time_window not in TIME_WINDOWS:
            errors.append(f"edge_invalid_time_window_{time_window}")
        if row.get("relationship_type") != "source_to_asset":
            errors.append("edge_relationship_type_invalid")
        if row.get("matrix_row_id") != _stable_row_id(str(source_key), str(instrument_id), str(time_window)):
            errors.append("edge_matrix_row_id_not_stable")
        if row.get("strategy_labels") != []:
            errors.append("edge_strategy_labels_must_be_empty")
        for key in (
            "proof_credit_allowed",
            "execution_allowed",
            "paper_order_allowed",
            "broker_write_allowed",
            "live_capital_enabled",
            "trade_candidate_creation_allowed",
            "strategy_hypothesis_creation_allowed",
        ):
            if row.get(key) is not False:
                errors.append(f"edge_{key}_must_be_false")

    scope = payload.get("matrix_scope", {})
    if scope.get("all_sources_cross_all_markets") is not True:
        errors.append("matrix_scope_not_full_cross_product")
    if scope.get("strategy_family_neutral") is not True:
        errors.append("strategy_family_neutral_required")
    if scope.get("strategy_labels_downstream_only") is not True:
        errors.append("strategy_labels_downstream_only_required")
    if scope.get("expected_row_count") != scope.get("matrix_row_count"):
        errors.append("matrix_row_count_expected_count_mismatch")
    if scope.get("time_windows") != TIME_WINDOWS:
        errors.append("matrix_time_windows_invalid")

    summary = payload.get("dashboard_safe_summary", {})
    if summary.get("public_safe") is not True or summary.get("command_disabled") is not True:
        errors.append("dashboard_summary_public_safe_required")
    if summary.get("live_send_allowed") is not False:
        errors.append("dashboard_summary_live_send_must_be_false")
    if summary.get("authority_flags_false") is not True:
        errors.append("dashboard_summary_authority_flags_false_required")

    return sorted(set(errors))


def build_qsase_phase_implementation_status(payload: dict[str, Any]) -> dict[str, Any]:
    runtime_dir = _runtime_dir()
    existing = _read_json(runtime_dir / PHASE_STATUS_ARTIFACT)
    phases = existing.get("phases") if isinstance(existing.get("phases"), dict) else {}
    phases[PHASE_ID] = {
        "name": PHASE_NAME,
        "status": payload["status"],
        "artifact_path": f"data/runtime/{PRIMARY_ARTIFACT}",
        "source_universe_path": f"data/runtime/{SOURCE_UNIVERSE_ARTIFACT}",
        "trading_universe_path": f"data/runtime/{TRADING_UNIVERSE_ARTIFACT}",
        "source_price_edges_path": f"data/runtime/{SOURCE_PRICE_EDGES_ARTIFACT}",
        "source_count": payload["source_universe"]["source_count"],
        "watched_market_count": payload["trading_universe"]["watched_market_count"],
        "source_price_edge_count": payload["source_price_edge_count"],
        "credential_gated_source_count": payload["source_universe"]["credential_gated_source_count"],
        "paperable_instrument_count": payload["trading_universe"]["market_count_with_paper_route_availability"],
        "paper_only": True,
        "research_only": True,
        "proposal_first": True,
        "public_safe": True,
        "authority_flags_false": True,
        "no_strategy_hypotheses_created": True,
        "no_trade_candidates_created": True,
        "no_paper_orders_created": True,
        "no_proof_credit_granted": True,
        "later_qsase_phases_implemented": False,
    }
    return {
        "schema_version": 1,
        "generated_at": payload["generated_at"],
        "active_phase": PHASE_ID,
        "phases": phases,
        "safety": payload["authority"],
    }


def _append_implementation_log(payload: dict[str, Any]) -> None:
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
        f"## QSASE-2: Universal Source-Price Pattern Matrix\n\n"
        f"- Generated at: `{payload.get('generated_at')}`\n"
        f"- Status: `{payload.get('status')}`\n"
        f"- Runtime artifact: `data/runtime/{PRIMARY_ARTIFACT}`\n"
        f"- Source universe: `{payload['source_universe']['source_count']}` sources\n"
        f"- Trading universe: `{payload['trading_universe']['watched_market_count']}` watched instruments\n"
        f"- Source-price rows: `{payload.get('source_price_edge_count')}`\n"
        f"- Safety: research-only; no strategy hypotheses, trade candidates, paper orders, broker writes, live capital, or proof credit created.\n"
    )
    if marker in existing:
        before = existing.split(marker, 1)[0].rstrip()
        updated = before + "\n\n" + entry
    elif existing.endswith("\n"):
        updated = existing + "\n" + entry
    else:
        updated = existing + "\n\n" + entry
    log_path.write_text(updated, encoding="utf-8")


def write_qsase_universal_source_price_matrix(
    payload: dict[str, Any],
    edges: list[dict[str, Any]],
    settings: Settings | None = None,
    *,
    append_history: bool = True,
    append_log: bool = True,
) -> dict[str, str]:
    runtime_dir = _runtime_dir(settings)
    runtime_dir.mkdir(parents=True, exist_ok=True)
    written: dict[str, str] = {}

    paths = {
        "matrix": runtime_dir / PRIMARY_ARTIFACT,
        "source_universe": runtime_dir / SOURCE_UNIVERSE_ARTIFACT,
        "trading_universe": runtime_dir / TRADING_UNIVERSE_ARTIFACT,
        "source_price_edges": runtime_dir / SOURCE_PRICE_EDGES_ARTIFACT,
        "dashboard_summary": runtime_dir / DASHBOARD_SUMMARY_ARTIFACT,
        "phase_status": runtime_dir / PHASE_STATUS_ARTIFACT,
    }
    _write_json(paths["matrix"], payload)
    _write_json(paths["source_universe"], payload["source_universe"])
    _write_json(paths["trading_universe"], payload["trading_universe"])
    _write_json(paths["dashboard_summary"], payload["dashboard_safe_summary"])
    _write_jsonl(paths["source_price_edges"], edges)
    _write_json(paths["phase_status"], build_qsase_phase_implementation_status(payload))
    written.update({key: str(path) for key, path in paths.items()})

    if append_history:
        history_path = runtime_dir / HISTORY_ARTIFACT
        events_path = runtime_dir / EVENTS_ARTIFACT
        _append_jsonl(
            history_path,
            {
                "generated_at": payload["generated_at"],
                "status": payload["status"],
                "source_count": payload["source_universe"]["source_count"],
                "watched_market_count": payload["trading_universe"]["watched_market_count"],
                "source_price_edge_count": payload["source_price_edge_count"],
                "coverage_gap_count": len(payload["coverage"]["coverage_gaps"]),
            },
        )
        _append_jsonl(
            events_path,
            {
                "generated_at": payload["generated_at"],
                "event_type": "qsase_universal_source_price_matrix_written",
                "status": payload["status"],
                "public_safe": True,
                "authority_flags_false": True,
            },
        )
        written["history"] = str(history_path)
        written["events"] = str(events_path)
    if append_log:
        _append_implementation_log(payload)
        written["implementation_log"] = str(_repo_root() / IMPLEMENTATION_LOG)
    return written


def build_and_write_qsase_universal_source_price_matrix(
    settings: Settings | None = None,
) -> tuple[dict[str, Any], list[dict[str, Any]], dict[str, str], list[str]]:
    payload = build_qsase_universal_source_price_matrix(settings)
    edges = build_source_price_edges(
        payload["source_universe"],
        payload["trading_universe"],
        payload["generated_at"],
    )
    errors = validate_qsase_universal_source_price_matrix(payload, edges)
    written = write_qsase_universal_source_price_matrix(payload, edges, settings)
    return payload, edges, written, errors


def validate_negative_matrix_probes() -> list[str]:
    base = build_qsase_universal_source_price_matrix()
    edges = build_source_price_edges(
        base["source_universe"],
        base["trading_universe"],
        base["generated_at"],
    )
    errors: list[str] = []

    for flag in MATRIX_AUTHORITY_FLAGS:
        probe = copy.deepcopy(base)
        probe["authority_flags"][flag] = True
        if not any(flag in error for error in validate_qsase_universal_source_price_matrix(probe, edges)):
            errors.append(f"negative_probe_failed_for_{flag}")

    source_probe = copy.deepcopy(base)
    source_probe["source_universe"]["sources"][0]["credential_gated"] = True
    source_probe["source_universe"]["sources"][0]["source_quorum_contribution"]["can_contribute"] = True
    if not any("credential_gated_quorum_violation" in error for error in validate_qsase_universal_source_price_matrix(source_probe, edges)):
        errors.append("negative_probe_failed_for_credential_gated_quorum")

    edge_probe = copy.deepcopy(base)
    edge_probe["source_price_edge_sample"][0]["proof_credit_allowed"] = True
    if not any("proof_credit_allowed" in error for error in validate_qsase_universal_source_price_matrix(edge_probe)):
        errors.append("negative_probe_failed_for_edge_proof_credit")

    missing_source_probe = copy.deepcopy(base)
    missing_source_probe["source_universe"]["sources"] = []
    if not any("source_universe_missing_or_empty" in error for error in validate_qsase_universal_source_price_matrix(missing_source_probe, edges)):
        errors.append("negative_probe_failed_for_missing_source_universe")

    missing_market_probe = copy.deepcopy(base)
    missing_market_probe["trading_universe"]["instruments"] = []
    if not any("trading_universe_missing_or_empty" in error for error in validate_qsase_universal_source_price_matrix(missing_market_probe, edges)):
        errors.append("negative_probe_failed_for_missing_trading_universe")

    return errors


if __name__ == "__main__":
    artifact = build_qsase_universal_source_price_matrix()
    rows = build_source_price_edges(
        artifact["source_universe"],
        artifact["trading_universe"],
        artifact["generated_at"],
    )
    print(_json_dump({"artifact": artifact, "edge_count": len(rows)}))
