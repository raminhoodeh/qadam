"""QSASE source reliability layer.

This layer normalizes Qadam's source universe into freshness, trust, outage,
latency, and quorum-contribution records. It is read-only and cannot promote
sources, mutate trust, create candidates, or route orders.
"""

from __future__ import annotations

import json
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from orchestrator.config import Settings
from orchestrator.qsase_governance_safety_contract import universal_authority_flags

SCHEMA_VERSION = "qsase_source_reliability.v1"
PRIMARY_ARTIFACT = "qsase_source_reliability.json"
RECORDS_ARTIFACT = "qsase_source_reliability_records.jsonl"
OUTAGE_LOG_ARTIFACT = "qsase_source_outage_log.jsonl"
DASHBOARD_SUMMARY_ARTIFACT = "qsase_source_reliability_dashboard_summary.json"
HISTORY_ARTIFACT = "qsase_source_reliability_history.jsonl"
EVENTS_ARTIFACT = "qsase_source_reliability_events.jsonl"

SOURCE_UNIVERSE_ARTIFACT = "qsase_source_universe.json"
COCKPIT_STATUS_ARTIFACT = "cockpit-status.json"

TARGET_REQUIRED_FRESHNESS_RATIO = 0.95

CATEGORY_SCHEDULES = {
    "geopolitics": {"cadence": "6h", "max_age_seconds": 24 * 60 * 60},
    "macro": {"cadence": "daily", "max_age_seconds": 48 * 60 * 60},
    "market_prices": {"cadence": "20m", "max_age_seconds": 60 * 60},
    "prediction_markets": {"cadence": "15m", "max_age_seconds": 60 * 60},
    "reddit_social": {"cadence": "30m", "max_age_seconds": 2 * 60 * 60},
    "filings_capitol_trades": {"cadence": "daily", "max_age_seconds": 48 * 60 * 60},
    "physical_world": {"cadence": "2h", "max_age_seconds": 8 * 60 * 60},
    "technical_order_flow": {"cadence": "5m", "max_age_seconds": 30 * 60},
    "other": {"cadence": "daily", "max_age_seconds": 48 * 60 * 60},
}

SUPPLEMENTAL_KEYS = {
    "bookmap",
    "tradingview_mcp",
    "tradingview_paid_alerts",
    "yahoo_finance",
    "yahoo_finance_or_tradingview",
    "ais_or_shipping",
    "conflict_tracker",
    "reddit",
    "social.rss",
}

AUTHORITY_FLAGS = {
    "source_reliability_read_only": True,
    "source_promotion_allowed": False,
    "source_trust_mutation_allowed": False,
    "source_trust_update_created": False,
    "trade_candidate_created": False,
    "qualified_setup_created": False,
    "risk_approval_created": False,
    "paper_order_created": False,
    "broker_write_allowed": False,
    "proof_credit_allowed": False,
    "live_capital_enabled": False,
    "telegram_command_path_enabled": False,
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


def _bool(value: Any) -> bool:
    return value if isinstance(value, bool) else False


def _source_category(source: dict[str, Any]) -> str:
    key = str(source.get("source_key") or "").lower()
    family = str(source.get("source_family") or source.get("source_pipeline") or "").lower()
    if key in {"stock_act", "sec_edgar", "patents"}:
        return "filings_capitol_trades"
    if key in {"kalshi", "polymarket"}:
        return "prediction_markets"
    if key in {"reddit", "twitter_x", "rss", "social.rss", "telegram"} or family == "social":
        return "reddit_social"
    if key in {"bookmap", "tradingview_mcp", "tradingview_paid_alerts", "alpaca", "yahoo_finance"}:
        return "technical_order_flow" if key == "bookmap" else "market_prices"
    if family in {"conflict", "geopolitics"}:
        return "geopolitics"
    if family == "macro":
        return "macro"
    if family == "physical":
        return "physical_world"
    if family in {"market", "market_context_taxonomy"}:
        return "market_prices"
    return "other"


def _freshness_state(source: dict[str, Any], category: str, now: datetime) -> tuple[str, str, int | None]:
    state = str(source.get("state") or source.get("adapter_status") or "unknown").lower()
    freshness = str(source.get("freshness_status") or "unknown").lower()
    observed_timestamp = source.get("observed_timestamp")
    age = _age_seconds(observed_timestamp, now)
    if age is None:
        age = source.get("observed_age_seconds") if isinstance(source.get("observed_age_seconds"), int) else None
    max_age = CATEGORY_SCHEDULES.get(category, CATEGORY_SCHEDULES["other"])["max_age_seconds"]

    if state not in {"online", "ready", "connected", "ok", "sample_ready"}:
        return "offline", f"adapter_state_{state or 'unknown'}", age
    if freshness in {"stale", "unknown", "missing", "degraded"}:
        return "stale", f"freshness_status_{freshness}", age
    if age is None:
        return "unknown", "observed_timestamp_missing", age
    if age > max_age:
        return "stale", f"age_exceeds_{max_age}_seconds_for_{category}", age
    return "fresh", "within_category_freshness_budget", age


def _build_record(source: dict[str, Any], now: datetime) -> dict[str, Any]:
    key = str(source.get("source_key") or source.get("key") or "unknown")
    category = _source_category(source)
    schedule = CATEGORY_SCHEDULES.get(category, CATEGORY_SCHEDULES["other"])
    freshness_state, outage_reason, age = _freshness_state(source, category, now)
    family = str(source.get("source_family") or source.get("source_pipeline") or "").lower()
    supplemental = (
        _bool(source.get("supplemental_context_only"))
        or key.lower() in SUPPLEMENTAL_KEYS
        or family == "market_context_taxonomy"
    )
    quorum = source.get("source_quorum_contribution") if isinstance(source.get("source_quorum_contribution"), dict) else {}
    raw_can_contribute = bool(quorum.get("can_contribute"))
    eligible = bool(source.get("eligible_for_signal_review"))
    raw_required = eligible and not supplemental
    if not eligible:
        reliability_state = "not_signal_review_eligible"
        reliability_exclusion_reason = "source_not_eligible_for_signal_review"
    elif supplemental:
        reliability_state = "supplemental_context_only"
        reliability_exclusion_reason = "supplemental_context_cannot_satisfy_required_freshness"
    elif not raw_can_contribute:
        reliability_state = "quorum_ineligible_context"
        reliability_exclusion_reason = str(quorum.get("reason") or "source_quorum_contribution_disabled")
    elif freshness_state != "fresh":
        reliability_state = "quarantined_until_fresh"
        reliability_exclusion_reason = outage_reason
    else:
        reliability_state = "active_required_source"
        reliability_exclusion_reason = "none"
    required = reliability_state == "active_required_source"
    can_contribute = required

    return {
        "schema_version": SCHEMA_VERSION,
        "source_key": key,
        "source_name": source.get("source_name") or key,
        "source_category": category,
        "source_family": source.get("source_family"),
        "adapter_status": source.get("adapter_status") or source.get("state"),
        "credential_status": source.get("credential_status") or "unknown",
        "trust_score": _float(source.get("trust_score")),
        "trust_posture": source.get("trust_posture") or "unknown",
        "observed_timestamp": source.get("observed_timestamp"),
        "observed_age_seconds": age,
        "freshness_state": freshness_state,
        "freshness_budget_seconds": schedule["max_age_seconds"],
        "scheduled_cadence": schedule["cadence"],
        "outage_state": "ok" if freshness_state == "fresh" else "needs_repair",
        "outage_reason": "none" if freshness_state == "fresh" else outage_reason,
        "supplemental_context_only": supplemental,
        "required_for_reliability_target": required,
        "raw_required_for_reliability_target": raw_required,
        "reliability_target_state": reliability_state,
        "reliability_target_exclusion_reason": reliability_exclusion_reason,
        "eligible_for_signal_review": eligible,
        "source_quorum_contribution": {
            "can_contribute": can_contribute,
            "raw_can_contribute": raw_can_contribute,
            "reason": "fresh_required_source" if can_contribute else reliability_exclusion_reason,
        },
        "execution_allowed": False,
        "trade_candidate_creation_allowed": False,
        "proof_credit_allowed": False,
        "live_capital_enabled": False,
    }


def build_source_reliability(settings: Settings | None = None) -> tuple[dict[str, Any], list[dict[str, Any]], list[dict[str, Any]]]:
    runtime = _runtime_dir(settings)
    now = _now()
    source_universe = _read_json(runtime / SOURCE_UNIVERSE_ARTIFACT)
    cockpit = _read_json(runtime / COCKPIT_STATUS_ARTIFACT)
    raw_sources = source_universe.get("sources") if isinstance(source_universe.get("sources"), list) else []

    records = [_build_record(source, now) for source in raw_sources if isinstance(source, dict)]
    raw_required_records = [record for record in records if record["raw_required_for_reliability_target"]]
    required_records = [record for record in records if record["required_for_reliability_target"]]
    fresh_required = [record for record in required_records if record["freshness_state"] == "fresh"]
    ratio = round(len(fresh_required) / len(required_records), 4) if required_records else 0.0
    quarantined_or_excluded = [
        record
        for record in raw_required_records
        if record["required_for_reliability_target"] is not True
    ]
    outages = [
        record
        for record in records
        if record["outage_state"] != "ok" and record["required_for_reliability_target"]
    ]

    by_category: dict[str, dict[str, Any]] = {}
    category_counter = Counter(record["source_category"] for record in records)
    for category, count in sorted(category_counter.items()):
        category_records = [record for record in records if record["source_category"] == category]
        category_raw_required = [record for record in category_records if record["raw_required_for_reliability_target"]]
        category_required = [record for record in category_records if record["required_for_reliability_target"]]
        category_fresh_required = [record for record in category_required if record["freshness_state"] == "fresh"]
        by_category[category] = {
            "source_count": count,
            "raw_required_source_count": len(category_raw_required),
            "required_source_count": len(category_required),
            "fresh_required_source_count": len(category_fresh_required),
            "required_freshness_ratio": round(len(category_fresh_required) / len(category_required), 4)
            if category_required
            else 1.0,
            "scheduled_cadence": CATEGORY_SCHEDULES.get(category, CATEGORY_SCHEDULES["other"])["cadence"],
            "stale_or_offline_count": len([record for record in category_records if record["freshness_state"] != "fresh"]),
            "quarantined_or_excluded_required_count": len(
                [
                    record
                    for record in category_raw_required
                    if record["required_for_reliability_target"] is not True
                ]
            ),
        }

    blockers = []
    if not records:
        blockers.append("source_universe_empty")
    if ratio < TARGET_REQUIRED_FRESHNESS_RATIO:
        blockers.append("required_source_freshness_below_95_percent")
    if outages:
        blockers.append("source_outages_or_stale_records_present")

    status = "qsase_source_reliability_ready" if not blockers else "qsase_source_reliability_needs_repair"
    payload = {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "qsase_source_reliability",
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
        "source_universe_ref": f"data/runtime/{SOURCE_UNIVERSE_ARTIFACT}",
        "cockpit_status_ref": f"data/runtime/{COCKPIT_STATUS_ARTIFACT}",
        "source_count": len(records),
        "raw_required_source_count": len(raw_required_records),
        "required_source_count": len(required_records),
        "fresh_required_source_count": len(fresh_required),
        "required_source_freshness_ratio": ratio,
        "target_required_source_freshness_ratio": TARGET_REQUIRED_FRESHNESS_RATIO,
        "target_required_source_freshness_passed": ratio >= TARGET_REQUIRED_FRESHNESS_RATIO,
        "quarantined_or_excluded_required_source_count": len(quarantined_or_excluded),
        "quarantined_or_excluded_required_sources": [
            {
                "source_key": record["source_key"],
                "category": record["source_category"],
                "state": record["reliability_target_state"],
                "reason": record["reliability_target_exclusion_reason"],
            }
            for record in quarantined_or_excluded[:20]
        ],
        "quorum_contributing_source_count": len([record for record in records if record["source_quorum_contribution"]["can_contribute"]]),
        "supplemental_source_count": len([record for record in records if record["supplemental_context_only"]]),
        "outage_count": len(outages),
        "by_category": by_category,
        "records_path": f"data/runtime/{RECORDS_ARTIFACT}",
        "outage_log_path": f"data/runtime/{OUTAGE_LOG_ARTIFACT}",
        "blockers": blockers,
        "dashboard_summary": {
            "headline": "Source reliability needs repair" if blockers else "Source reliability is ready",
            "required_source_freshness_ratio": ratio,
            "source_count": len(records),
            "outage_count": len(outages),
            "quarantined_or_excluded_required_source_count": len(quarantined_or_excluded),
            "top_outages": [
                {
                    "source_key": record["source_key"],
                    "category": record["source_category"],
                    "reason": record["outage_reason"],
                }
                for record in outages[:8]
            ],
        },
        "mission_control_context": {
            "watching_count": cockpit.get("mission_control", {}).get("watching_count"),
            "headline": cockpit.get("mission_control", {}).get("headline"),
        },
        "broker_write_allowed": False,
        "paper_order_created_count": 0,
        "proof_credit_allowed": False,
        "live_capital_enabled": False,
    }
    return payload, records, outages


def validate_source_reliability(payload: dict[str, Any], records: list[dict[str, Any]]) -> list[str]:
    errors: list[str] = []
    if payload.get("schema_version") != SCHEMA_VERSION:
        errors.append("schema_version_mismatch")
    if payload.get("artifact_type") != "qsase_source_reliability":
        errors.append("artifact_type_mismatch")
    if payload.get("read_only") is not True:
        errors.append("read_only_must_be_true")
    if payload.get("source_count") != len(records):
        errors.append("source_count_mismatch")
    if payload.get("broker_write_allowed") is not False:
        errors.append("broker_write_allowed_must_be_false")
    if payload.get("paper_order_created_count") != 0:
        errors.append("paper_order_created_count_must_be_zero")
    if payload.get("live_capital_enabled") is not False:
        errors.append("live_capital_enabled_must_be_false")
    for record in records:
        for field in ("source_key", "source_category", "freshness_state", "trust_score", "source_quorum_contribution"):
            if field not in record:
                errors.append(f"record_missing_{field}")
        if record.get("execution_allowed") is not False:
            errors.append("record_execution_allowed_must_be_false")
    return sorted(set(errors))


def write_source_reliability(
    payload: dict[str, Any],
    records: list[dict[str, Any]],
    outages: list[dict[str, Any]],
    settings: Settings | None = None,
) -> dict[str, str]:
    runtime = _runtime_dir(settings)
    primary = runtime / PRIMARY_ARTIFACT
    records_path = runtime / RECORDS_ARTIFACT
    outage_log = runtime / OUTAGE_LOG_ARTIFACT
    dashboard = runtime / DASHBOARD_SUMMARY_ARTIFACT
    history = runtime / HISTORY_ARTIFACT
    events = runtime / EVENTS_ARTIFACT

    _write_json(primary, payload)
    _write_jsonl(records_path, records)
    _write_jsonl(outage_log, outages)
    _write_json(dashboard, payload.get("dashboard_summary", {}))
    _append_jsonl(history, payload)
    _append_jsonl(events, {
        "schema_version": SCHEMA_VERSION,
        "generated_at": payload.get("generated_at"),
        "event": payload.get("status"),
        "outage_count": payload.get("outage_count"),
        "required_source_freshness_ratio": payload.get("required_source_freshness_ratio"),
    })
    return {
        "primary": str(primary),
        "records": str(records_path),
        "outage_log": str(outage_log),
        "dashboard_summary": str(dashboard),
        "history": str(history),
        "events": str(events),
    }


def build_and_write_source_reliability(settings: Settings | None = None) -> tuple[dict[str, Any], list[dict[str, Any]], dict[str, str], list[str]]:
    payload, records, outages = build_source_reliability(settings)
    errors = validate_source_reliability(payload, records)
    written = write_source_reliability(payload, records, outages, settings)
    return payload, records, written, errors
