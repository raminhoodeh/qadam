"""OR-4 point-in-time alignment, eligibility, typed gaps, and leakage audit."""

from __future__ import annotations

from bisect import bisect_left
from collections import Counter
from datetime import datetime, timedelta, timezone
import errno
import hashlib
import json
import os
from pathlib import Path
import time
from typing import Any

from orchestrator.config import Settings
from orchestrator.qadam_canonical_contracts import AtomicArtifactStore
from orchestrator.qadam_operator_ready_common import (
    ROOT,
    authority_flags,
    now_iso,
    read_json,
    read_jsonl,
    runtime_dir,
    unique_errors,
    validate_authority,
)

SCHEMA_VERSION = "qadam_point_in_time_evidence.v1"
PHASE_ID = "OR-4"

ALIGNMENT_ARTIFACT = "qadam_point_in_time_alignment_summary.json"
ELIGIBILITY_ARTIFACT = "qadam_relationship_eligibility_graph.jsonl"
FORWARD_COVERAGE_ARTIFACT = "qadam_forward_window_coverage.json"
TYPED_COMPLETION_ARTIFACT = "qadam_typed_evidence_completion.json"
LEAKAGE_ARTIFACT = "qadam_leakage_audit_v2.json"
CHECK_ARTIFACT = "qadam_point_in_time_evidence_checks.json"
PROVIDER_ALIGNMENT_ARTIFACT = "qadam_provider_point_in_time_alignment.json"
PROVIDER_ALIGNMENT_RECORDS_PATH = (
    ROOT / "data" / "research" / "aligned" / "or4" / "provider_alignment.jsonl"
)

MEMORY_RECORDS_ARTIFACT = "qsase_historical_source_price_memory.jsonl"
SOURCE_UNIVERSE_ARTIFACT = "qsase_source_universe.json"
TRADING_UNIVERSE_ARTIFACT = "qsase_trading_universe.json"
SOURCE_OPERATIONAL_ARTIFACT = "qadam_source_operational_state.jsonl"
EVIDENCE_SUMMARY_ARTIFACT = "qadam_evidence_contracts_summary.json"
SOURCE_BACKFILL_MANIFEST_ARTIFACT = "qadam_source_backfill_manifest.json"
PRICE_BACKFILL_MANIFEST_ARTIFACT = "qadam_price_backfill_manifest.json"
BACKFILL_COVERAGE_ARTIFACT = "qadam_backfill_coverage.json"

PRICE_ONLY_SOURCE_KEYS = {
    "alpaca",
    "tradingview_mcp",
    "tradingview_paid_alerts",
    "yahoo_finance",
    "yahoo_finance_or_tradingview",
}
HORIZON_OFFSETS = {
    "1d_forward": 1,
    "3d_forward": 3,
    "5d_forward": 5,
    "10d_forward": 10,
    "20d_forward": 20,
    "30d_forward": 30,
}
MAX_SOURCE_EVENT_AVAILABILITY_LAG = timedelta(days=7)
MAX_SOURCE_TO_MARKET_ALIGNMENT_LAG = timedelta(days=7)

EVIDENCE_CONTRACT_ARTIFACTS = (
    "qadam_source_evidence_contracts.jsonl",
    "qadam_price_evidence_contracts.jsonl",
    "qadam_source_price_relationship_evidence_contracts.jsonl",
    "qadam_hypothesis_evidence_contracts.jsonl",
    "qadam_strategy_evidence_contracts.jsonl",
    "qadam_akber_evidence_contracts.jsonl",
    "qadam_shadow_evidence_contracts.jsonl",
    "qadam_router_evidence_contracts.jsonl",
)

SOURCE_MARKET_MAP = {
    "conflict": {"crude_oil", "defence", "prediction_markets"},
    "physical": {"crude_oil", "defence", "semiconductors"},
    "macro": {"silver", "macro_watchlist", "crude_oil", "semiconductors"},
}
SOURCE_KEY_MARKET_MAP = {
    "github": {"semiconductors"},
    "patents": {"semiconductors", "defence"},
    "sec_edgar": {"semiconductors", "defence", "crude_oil", "silver"},
    "stock_act": {"defence", "semiconductors"},
    "kalshi": {"prediction_markets"},
    "polymarket": {"prediction_markets"},
    "ais_maritime": {"crude_oil"},
    "ais_or_shipping": {"crude_oil"},
}
BROAD_DISCOVERY_FAMILIES = {"market", "market_context_taxonomy", "social"}
DERIVED_SOURCE_CLUSTER = {
    "ais_or_shipping": "ais_maritime",
    "conflict_tracker": "conflict_fusion",
    "social.rss": "rss",
    "yahoo_finance_or_tradingview": "market_confirmation_derived",
}
FORWARD_WINDOWS = {
    "1d_forward",
    "3d_forward",
    "5d_forward",
    "10d_forward",
    "20d_forward",
    "30d_forward",
}

GAP_OWNERS = {
    "missing_current_price": "OR-2_live_source_freshness",
    "missing_forward_window": "OR-3_provider_backfill",
    "missing_price_history": "OR-3_provider_backfill",
    "provider_history_required": "OR-3_provider_backfill",
    "missing_source_quorum": "OR-2_source_freshness",
    "missing_fresh_catalyst": "OR-5_pattern_score",
    "missing_pricing_gap_evidence": "OR-7_akber_filter",
    "missing_risk_reward": "OR-7_akber_filter",
    "missing_technical_confirmation": "OR-7_akber_filter",
    "missing_volatility_context": "OR-7_akber_filter",
    "missing_volume_or_flow": "OR-7_akber_filter",
    "missing_shadow_replay": "OR-8_shadow_simulator",
    "missing_router_decision": "OR-9_router",
}


def _parse(value: Any) -> datetime | None:
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _pair_id(source_key: str, symbol: str) -> str:
    digest = hashlib.sha256(f"{source_key}|{symbol}".encode("utf-8")).hexdigest()[:24]
    return f"relationship:{digest}"


def _mapping_class(source: dict[str, Any], instrument: dict[str, Any]) -> str:
    key = str(source.get("source_key") or "")
    family = str(source.get("source_family") or "")
    market = str(instrument.get("market_family") or "")
    mapped = SOURCE_KEY_MARKET_MAP.get(key, SOURCE_MARKET_MAP.get(family, set()))
    if market in mapped:
        return "causal_strategy_mapping"
    if family in BROAD_DISCOVERY_FAMILIES:
        return "broad_discovery_mapping"
    digest = int(hashlib.sha256(f"{key}|{market}".encode("utf-8")).hexdigest()[:4], 16)
    if digest % 7 == 0:
        return "negative_control"
    return "pair_intentionally_not_meaningful"


def _independence_cluster(source_key: str) -> str:
    canonical = DERIVED_SOURCE_CLUSTER.get(source_key, source_key)
    return f"source-cluster:{hashlib.sha256(canonical.encode('utf-8')).hexdigest()[:16]}"


def build_eligibility_graph(
    sources: list[dict[str, Any]],
    instruments: list[dict[str, Any]],
    operational_by_key: dict[str, dict[str, Any]],
) -> list[dict[str, Any]]:
    generated_at = now_iso()
    records: list[dict[str, Any]] = []
    for source in sources:
        source_key = str(source.get("source_key") or "unknown")
        operational = operational_by_key.get(source_key, {})
        for instrument in instruments:
            symbol = str(instrument.get("symbol") or "unknown")
            mapping = _mapping_class(source, instrument)
            historical_research_eligible = mapping != "pair_intentionally_not_meaningful"
            records.append(
                {
                    "schema_version": SCHEMA_VERSION,
                    "artifact_type": "qadam_relationship_eligibility",
                    "generated_at": generated_at,
                    "relationship_id": _pair_id(source_key, symbol),
                    "source_key": source_key,
                    "source_family": source.get("source_family"),
                    "instrument": symbol,
                    "market_family": instrument.get("market_family"),
                    "mapping_class": mapping,
                    "historical_research_eligible": historical_research_eligible,
                    "negative_control": mapping == "negative_control",
                    "live_scoring_eligible": bool(
                        historical_research_eligible
                        and mapping != "negative_control"
                        and operational.get("raw_scoring_eligible") is True
                    ),
                    "live_source_quorum_eligible": operational.get("source_quorum_eligible")
                    is True,
                    "source_independence_cluster_id": _independence_cluster(source_key),
                    "source_independence_measured_after_duplicate_clustering": True,
                    "strategy_promotion_allowed": False,
                    "authority": authority_flags(),
                }
            )
    return records


def _safe_number(value: Any) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _source_numeric_features(record: dict[str, Any]) -> dict[str, float]:
    price = record.get("price") if isinstance(record.get("price"), dict) else {}
    candidates = {
        "magnitude": record.get("magnitude"),
        "provider_price": price.get("mean") or price.get("close") or record.get("price"),
        "volume": record.get("volume"),
        "open_interest": record.get("open_interest"),
        "best_death_estimate": record.get("best_death_estimate"),
    }
    return {
        key: number
        for key, value in candidates.items()
        if (number := _safe_number(value)) is not None
    }


def _file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


_RETRYABLE_PARTITION_ERRNOS = {errno.EAGAIN, errno.EBUSY, errno.EDEADLK}
if hasattr(errno, "ESTALE"):
    _RETRYABLE_PARTITION_ERRNOS.add(errno.ESTALE)


def _read_jsonl_partition(
    path: Path,
    *,
    maximum_attempts: int = 4,
) -> list[dict[str, Any]]:
    """Read one partition atomically from the consumer's perspective.

    A retry starts from byte zero, preventing a transient mid-stream filesystem
    error from duplicating partially consumed rows in the caller's aggregate.
    """

    for attempt in range(maximum_attempts):
        try:
            records: list[dict[str, Any]] = []
            with path.open("r", encoding="utf-8") as handle:
                for line in handle:
                    if not line.strip():
                        continue
                    payload = json.loads(line)
                    if isinstance(payload, dict):
                        records.append(payload)
            return records
        except OSError as exc:
            if exc.errno not in _RETRYABLE_PARTITION_ERRNOS or attempt + 1 >= maximum_attempts:
                raise
            time.sleep(0.05 * (2**attempt))
    raise RuntimeError(f"partition_read_retry_exhausted:{path}")


def _build_source_day_features(
    source_manifest: dict[str, Any],
) -> tuple[list[dict[str, Any]], dict[str, int]]:
    groups: dict[tuple[str, str], dict[str, Any]] = {}
    counters: Counter[str] = Counter()
    for job in source_manifest.get("jobs", []):
        if job.get("status") != "complete":
            continue
        source_key = str(job.get("source") or "unknown")
        row_count = int(job.get("row_count") or 0)
        if source_key in PRICE_ONLY_SOURCE_KEYS:
            counters["price_only_source_rows_excluded"] += row_count
            continue
        if int(job.get("point_in_time_safe_row_count") or 0) <= 0:
            counters["current_revision_source_rows_excluded"] += row_count
            continue
        normalized = str(job.get("normalized_path") or "")
        path = ROOT / normalized if normalized else Path()
        if not normalized or not path.is_file():
            counters["source_partition_missing_count"] += 1
            continue
        counters["source_partition_count"] += 1
        for record in _read_jsonl_partition(path):
            counters["source_rows_scanned"] += 1
            if record.get("point_in_time_safe") is not True:
                counters["non_point_in_time_rows_excluded"] += 1
                continue
            available_at = _parse(record.get("source_available_at"))
            event_at = _parse(record.get("event_timestamp"))
            if available_at is None:
                counters["source_available_at_missing_count"] += 1
                continue
            if event_at is not None and (
                event_at > available_at
                or available_at - event_at > MAX_SOURCE_EVENT_AVAILABILITY_LAG
            ):
                counters["stale_or_invalid_source_revision_rows_excluded"] += 1
                continue
            key = (source_key, available_at.date().isoformat())
            group = groups.setdefault(
                key,
                {
                    "source_key": source_key,
                    "availability_date": available_at.date().isoformat(),
                    "source_available_at": available_at,
                    "first_event_at": event_at,
                    "last_event_at": event_at,
                    "event_count": 0,
                    "numeric_sums": Counter(),
                    "numeric_counts": Counter(),
                    "record_type_counts": Counter(),
                    "source_partition_paths": set(),
                },
            )
            group["source_available_at"] = max(group["source_available_at"], available_at)
            if event_at is not None:
                group["first_event_at"] = (
                    min(group["first_event_at"], event_at)
                    if group["first_event_at"] is not None
                    else event_at
                )
                group["last_event_at"] = (
                    max(group["last_event_at"], event_at)
                    if group["last_event_at"] is not None
                    else event_at
                )
            group["event_count"] += 1
            group["record_type_counts"][
                str(record.get("record_type") or "provider_observation")
            ] += 1
            for feature, value in _source_numeric_features(record).items():
                group["numeric_sums"][feature] += value
                group["numeric_counts"][feature] += 1
            group["source_partition_paths"].add(normalized)
            counters["point_in_time_source_rows"] += 1
    features: list[dict[str, Any]] = []
    for group in groups.values():
        features.append(
            {
                "source_key": group["source_key"],
                "availability_date": group["availability_date"],
                "source_available_at": group["source_available_at"].isoformat(),
                "first_event_at": (
                    group["first_event_at"].isoformat()
                    if group["first_event_at"] is not None
                    else None
                ),
                "last_event_at": (
                    group["last_event_at"].isoformat()
                    if group["last_event_at"] is not None
                    else None
                ),
                "event_count": group["event_count"],
                "numeric_feature_means": {
                    feature: group["numeric_sums"][feature] / group["numeric_counts"][feature]
                    for feature in sorted(group["numeric_sums"])
                },
                "record_type_counts": dict(sorted(group["record_type_counts"].items())),
                "source_partition_paths": sorted(group["source_partition_paths"]),
            }
        )
    features.sort(key=lambda row: (row["source_available_at"], row["source_key"]))
    counters["source_day_feature_count"] = len(features)
    return features, dict(counters)


def _derived_daily_bar_available_at(observed_at: datetime) -> datetime:
    return observed_at + timedelta(days=1)


def _market_alignment_is_timely(
    source_available_at: datetime,
    price_available_at: datetime,
) -> bool:
    lag = price_available_at - source_available_at
    return timedelta(0) <= lag <= MAX_SOURCE_TO_MARKET_ALIGNMENT_LAG


def _load_price_bars(
    price_manifest: dict[str, Any],
) -> tuple[dict[str, list[dict[str, Any]]], dict[str, int]]:
    bars_by_symbol: dict[str, dict[str, dict[str, Any]]] = {}
    counters: Counter[str] = Counter()
    seen_paths: set[str] = set()
    for job in price_manifest.get("jobs", []):
        if job.get("status") != "complete":
            continue
        symbol = str(job.get("instrument") or "unknown")
        year = str(job.get("date_partition") or "")
        normalized = str(job.get("normalized_path") or "")
        if not normalized:
            normalized = (
                f"data/research/prices/symbol={symbol.replace('/', '_')}"
                f"/interval=1d/year={year}/bars.jsonl"
            )
        if normalized in seen_paths:
            continue
        seen_paths.add(normalized)
        path = ROOT / normalized
        if not path.is_file():
            counters["price_partition_missing_count"] += 1
            continue
        counters["price_partition_count"] += 1
        provider = str(job.get("provider") or "unknown")
        for record in _read_jsonl_partition(path):
            observed_at = _parse(record.get("observed_at"))
            close = _safe_number(record.get("close"))
            if observed_at is None or close is None:
                counters["invalid_price_bar_count"] += 1
                continue
            if provider == "alpaca_market_data_v2":
                available_at = _derived_daily_bar_available_at(observed_at)
                availability_policy = "derived_daily_bar_available_after_session"
            else:
                available_at = _parse(record.get("available_at"))
                availability_policy = str(
                    record.get("point_in_time_policy") or "provider_available_at"
                )
            if available_at is None:
                counters["price_available_at_missing_count"] += 1
                continue
            bars_by_symbol.setdefault(symbol, {})[observed_at.isoformat()] = {
                "symbol": symbol,
                "observed_at": observed_at,
                "available_at": available_at,
                "close": close,
                "volume": _safe_number(record.get("volume")),
                "provider": provider,
                "availability_policy": availability_policy,
                "normalized_path": normalized,
            }
            counters["price_bar_count"] += 1
    result = {
        symbol: sorted(rows.values(), key=lambda row: row["available_at"])
        for symbol, rows in bars_by_symbol.items()
    }
    counters["price_symbol_count"] = len(result)
    return result, dict(counters)


def build_provider_lake_alignment(
    runtime: Path,
    eligibility: list[dict[str, Any]],
    *,
    output_path: Path = PROVIDER_ALIGNMENT_RECORDS_PATH,
) -> dict[str, Any]:
    source_manifest = read_json(runtime / SOURCE_BACKFILL_MANIFEST_ARTIFACT)
    price_manifest = read_json(runtime / PRICE_BACKFILL_MANIFEST_ARTIFACT)
    backfill = read_json(runtime / BACKFILL_COVERAGE_ARTIFACT)
    source_features, source_counters = _build_source_day_features(source_manifest)
    price_bars, price_counters = _load_price_bars(price_manifest)
    price_availability = {
        symbol: [bar["available_at"] for bar in bars] for symbol, bars in price_bars.items()
    }
    eligibility_by_source: dict[str, list[dict[str, Any]]] = {}
    for relationship in eligibility:
        if relationship.get("historical_research_eligible") is not True:
            continue
        eligibility_by_source.setdefault(
            str(relationship.get("source_key") or "unknown"), []
        ).append(relationship)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    temporary = output_path.with_name(f".{output_path.name}.{os.getpid()}.tmp")
    alignment_count = 0
    eligible_window_count = 0
    no_forward_horizon_count = 0
    unavailable_price_pair_count = 0
    negative_control_count = 0
    with temporary.open("w", encoding="utf-8") as handle:
        for feature in source_features:
            source_available_at = _parse(feature["source_available_at"])
            if source_available_at is None:
                continue
            for relationship in eligibility_by_source.get(feature["source_key"], []):
                symbol = str(relationship.get("instrument") or "unknown")
                bars = price_bars.get(symbol, [])
                if not bars:
                    unavailable_price_pair_count += 1
                    continue
                baseline_index = bisect_left(price_availability[symbol], source_available_at)
                if baseline_index >= len(bars):
                    unavailable_price_pair_count += 1
                    continue
                baseline = bars[baseline_index]
                if not _market_alignment_is_timely(source_available_at, baseline["available_at"]):
                    unavailable_price_pair_count += 1
                    continue
                future_horizon_availability = {
                    horizon: bars[baseline_index + offset]["available_at"].isoformat()
                    for horizon, offset in HORIZON_OFFSETS.items()
                    if baseline_index + offset < len(bars)
                }
                available_horizons = sorted(
                    future_horizon_availability,
                    key=lambda horizon: HORIZON_OFFSETS[horizon],
                )
                if not available_horizons:
                    no_forward_horizon_count += 1
                eligible_window_count += len(available_horizons)
                negative_control = relationship.get("negative_control") is True
                negative_control_count += int(negative_control)
                identity = f"{feature['source_key']}|{feature['source_available_at']}|{symbol}"
                record = {
                    "schema_version": SCHEMA_VERSION,
                    "artifact_type": "qadam_provider_point_in_time_alignment_record",
                    "alignment_record_id": (
                        "provider-alignment:"
                        + hashlib.sha256(identity.encode("utf-8")).hexdigest()[:24]
                    ),
                    "relationship_id": relationship.get("relationship_id"),
                    "source_key": feature["source_key"],
                    "instrument": symbol,
                    "mapping_class": relationship.get("mapping_class"),
                    "negative_control": negative_control,
                    "source_available_at": feature["source_available_at"],
                    "decision_at": baseline["available_at"].isoformat(),
                    "feature_snapshot": {
                        "source_event_count": feature["event_count"],
                        "source_numeric_feature_means": feature["numeric_feature_means"],
                        "source_record_type_counts": feature["record_type_counts"],
                        "first_event_at": feature["first_event_at"],
                        "last_event_at": feature["last_event_at"],
                        "baseline_price_observed_at": baseline["observed_at"].isoformat(),
                        "baseline_price_available_at": baseline["available_at"].isoformat(),
                        "baseline_close": baseline["close"],
                        "baseline_volume": baseline["volume"],
                    },
                    "available_horizons": available_horizons,
                    "future_horizon_availability": future_horizon_availability,
                    "future_label_values_included": False,
                    "score_before_label_boundary": True,
                    "point_in_time_safe": True,
                    "provenance": {
                        "source_partition_paths": feature["source_partition_paths"],
                        "price_partition_path": baseline["normalized_path"],
                        "price_provider": baseline["provider"],
                        "price_availability_policy": baseline["availability_policy"],
                    },
                    "strategy_promotion_allowed": False,
                }
                handle.write(json.dumps(record, sort_keys=True, separators=(",", ":")))
                handle.write("\n")
                alignment_count += 1
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(temporary, output_path)
    manifest_closed = backfill.get("provider_history_acquisition_contract_complete") is True
    status = (
        "provider_alignment_ready"
        if alignment_count > 0 and eligible_window_count > 0
        else "provider_alignment_has_no_eligible_windows"
    )
    return {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "qadam_provider_point_in_time_alignment",
        "phase_id": PHASE_ID,
        "generated_at": now_iso(),
        "status": status,
        "provider_backfill_contract_complete": manifest_closed,
        "provider_backfill_empirically_complete": (
            backfill.get("provider_history_certified_complete") is True
        ),
        "alignment_records_path": str(output_path.relative_to(ROOT)),
        "alignment_records_sha256": _file_sha256(output_path),
        "alignment_record_count": alignment_count,
        "eligible_forward_window_count": eligible_window_count,
        "no_forward_horizon_record_count": no_forward_horizon_count,
        "unavailable_price_pair_count": unavailable_price_pair_count,
        "negative_control_alignment_count": negative_control_count,
        "future_label_value_count": 0,
        "score_before_label_boundary": True,
        "source_counters": source_counters,
        "price_counters": price_counters,
        "paperops_watch_only_mode": True,
        "authority": authority_flags(),
    }


def _timestamp_semantics(record: dict[str, Any]) -> dict[str, Any]:
    return {
        "observed_at": record.get("event_timestamp"),
        "published_at": record.get("source_available_at"),
        "available_at": record.get("source_available_at"),
        "ingested_at": record.get("as_of_timestamp"),
        "decision_at": record.get("decision_timestamp"),
        "outcome_available_at": record.get("outcome_available_at"),
        "revision_vintage": record.get("revision_vintage"),
    }


def _leakage_reasons(record: dict[str, Any]) -> list[str]:
    reasons: list[str] = []
    source_available = _parse(record.get("source_available_at"))
    decision = _parse(record.get("decision_timestamp"))
    feature = _parse(record.get("feature_availability", {}).get("feature_timestamp"))
    outcome = _parse(record.get("outcome_available_at"))
    window = str(record.get("forward_outcomes", {}).get("window") or "")
    if source_available is None:
        reasons.append("source_available_at_missing")
    elif decision is not None and source_available > decision:
        reasons.append("source_available_after_decision")
    if feature is None:
        reasons.append("feature_available_at_missing")
    elif decision is not None and feature > decision:
        reasons.append("feature_available_after_decision")
    if record.get("feature_availability", {}).get("forbidden_future_features_detected") is True:
        reasons.append("forbidden_future_feature_detected")
    if (
        record.get("forward_outcomes", {}).get("outcome_available") is True
        and window in FORWARD_WINDOWS
    ):
        if outcome is None:
            reasons.append("forward_outcome_available_at_missing")
        elif decision is not None and outcome <= decision:
            reasons.append("forward_outcome_not_strictly_after_decision")
    return reasons


def _typed_window_reason(
    record: dict[str, Any],
    mapping_class: str,
    leakage_reasons: list[str],
) -> str:
    window = str(record.get("forward_outcomes", {}).get("window") or "")
    outcome_available = record.get("forward_outcomes", {}).get("outcome_available") is True
    symbol = str(record.get("market_snapshot", {}).get("instrument") or "")
    market_session = str(record.get("market_snapshot", {}).get("market_session") or "")
    if mapping_class == "pair_intentionally_not_meaningful":
        return "pair_intentionally_not_meaningful"
    if leakage_reasons:
        return "source_revision_or_future_information_leakage"
    if outcome_available:
        if window in {"pre_event_baseline", "event_time_move"}:
            return "descriptive_window_complete_not_forward_label"
        return "forward_window_complete"
    if symbol.startswith(("KALSHI:", "POLYMARKET:")):
        return "contract_expired_or_identity_history_missing"
    source_available = _parse(record.get("source_available_at"))
    decision = _parse(record.get("decision_timestamp"))
    if source_available is not None and decision is not None and source_available > decision:
        return "source_published_too_late"
    if market_session in {"market_closed", "holiday_closed"}:
        return "market_closed"
    if record.get("market_snapshot", {}).get("price") is None:
        return "price_history_absent"
    if window in FORWARD_WINDOWS:
        return "insufficient_forward_horizon"
    return "provider_gap"


def build_forward_coverage(
    memory_records: list[dict[str, Any]],
    eligibility: list[dict[str, Any]],
) -> tuple[dict[str, Any], dict[str, Any]]:
    eligibility_by_pair = {
        (record["source_key"], record["instrument"]): record for record in eligibility
    }
    windows: list[dict[str, Any]] = []
    reason_counts: Counter[str] = Counter()
    leakage_quarantine: list[dict[str, Any]] = []
    eligible_score_inputs = 0
    for record in memory_records:
        source_key = str(record.get("source_snapshot", {}).get("source_name") or "unknown")
        symbol = str(record.get("market_snapshot", {}).get("instrument") or "unknown")
        pair = eligibility_by_pair.get((source_key, symbol), {})
        leakage_reasons = _leakage_reasons(record)
        typed_reason = _typed_window_reason(
            record,
            str(pair.get("mapping_class") or "pair_intentionally_not_meaningful"),
            leakage_reasons,
        )
        reason_counts[typed_reason] += 1
        eligible = bool(
            typed_reason == "forward_window_complete"
            and pair.get("historical_research_eligible") is True
            and not leakage_reasons
            and record.get("source_available_at")
            and record.get("provenance")
        )
        eligible_score_inputs += int(eligible)
        if leakage_reasons:
            leakage_quarantine.append(
                {
                    "memory_record_id": record.get("memory_record_id"),
                    "reasons": leakage_reasons,
                    "excluded_from_scoring": True,
                }
            )
        windows.append(
            {
                "memory_record_id": record.get("memory_record_id"),
                "matrix_row_ids": record.get("matrix_row_ids", []),
                "relationship_id": pair.get("relationship_id"),
                "source_key": source_key,
                "instrument": symbol,
                "time_window": record.get("forward_outcomes", {}).get("window"),
                "mapping_class": pair.get("mapping_class"),
                "typed_state": typed_reason,
                "eligible_score_input": eligible,
                "timestamp_semantics": _timestamp_semantics(record),
                "provenance": record.get("provenance", []),
                "source_independence_cluster_id": pair.get("source_independence_cluster_id"),
            }
        )
    missing_count = sum(
        count
        for reason, count in reason_counts.items()
        if reason
        not in {"forward_window_complete", "descriptive_window_complete_not_forward_label"}
    )
    coverage = {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "qadam_forward_window_coverage",
        "phase_id": PHASE_ID,
        "generated_at": now_iso(),
        "status": "classified_with_evidence_gaps" if missing_count else "complete",
        "memory_record_count": len(memory_records),
        "classified_record_count": len(windows),
        "classification_ratio": round(len(windows) / len(memory_records), 6)
        if memory_records
        else 0.0,
        "typed_state_counts": dict(sorted(reason_counts.items())),
        "missing_or_ineligible_window_count": missing_count,
        "eligible_forward_score_input_count": eligible_score_inputs,
        "all_missing_windows_have_typed_reason": len(windows) == len(memory_records),
        "windows": windows,
        "authority": authority_flags(),
    }
    leakage = {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "qadam_leakage_audit_v2",
        "phase_id": PHASE_ID,
        "generated_at": now_iso(),
        "status": "passed_zero_eligible_leakage",
        "input_record_count": len(memory_records),
        "quarantined_input_record_count": len(leakage_quarantine),
        "eligible_leakage_violation_count": 0,
        "leakage_violation_count": 0,
        "quarantined_records": leakage_quarantine,
        "forward_label_requires_outcome_available_strictly_after_decision": True,
        "descriptive_event_time_records_are_not_forward_labels": True,
        "authority": authority_flags(),
    }
    return coverage, leakage


def build_typed_evidence_completion(runtime: Any) -> dict[str, Any]:
    summary = read_json(runtime / EVIDENCE_SUMMARY_ARTIFACT)
    records: list[dict[str, Any]] = []
    type_counts: Counter[str] = Counter()
    contract_counts: Counter[str] = Counter()
    for artifact in EVIDENCE_CONTRACT_ARTIFACTS:
        for contract in read_jsonl(runtime / artifact):
            for missing in contract.get("missing_evidence", []):
                gap_type = str(missing.get("missing_evidence_type") or "unclassified")
                type_counts[gap_type] += 1
                contract_counts[str(contract.get("contract_type") or "unknown")] += 1
                records.append(
                    {
                        "contract_id": contract.get("contract_id"),
                        "contract_type": contract.get("contract_type"),
                        "source_record_id": contract.get("source_record_id"),
                        "field": missing.get("field"),
                        "missing_evidence_type": gap_type,
                        "severity": missing.get("severity"),
                        "completion_state": "awaiting_evidence_owner",
                        "phase_owner": GAP_OWNERS.get(gap_type, "review_required"),
                        "underlying_data_verified_available": False,
                        "synthetic_completion_allowed": False,
                    }
                )
    return {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "qadam_typed_evidence_completion",
        "phase_id": PHASE_ID,
        "generated_at": now_iso(),
        "status": "fully_typed_evidence_still_maturing" if records else "complete",
        "source_summary_missing_evidence_count": summary.get("missing_evidence_count"),
        "typed_gap_record_count": len(records),
        "all_gaps_typed": len(records) == summary.get("missing_evidence_count"),
        "completed_from_verified_existing_data_count": 0,
        "awaiting_real_evidence_count": len(records),
        "missing_evidence_type_counts": dict(sorted(type_counts.items())),
        "missing_by_contract_type": dict(sorted(contract_counts.items())),
        "records": records,
        "authority": authority_flags(),
    }


def _alignment_summary(
    eligibility: list[dict[str, Any]],
    coverage: dict[str, Any],
    leakage: dict[str, Any],
    provider_alignment: dict[str, Any],
) -> dict[str, Any]:
    mapping_counts = Counter(record.get("mapping_class") for record in eligibility)
    clusters = {record.get("source_independence_cluster_id") for record in eligibility}
    return {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "qadam_point_in_time_alignment_summary",
        "phase_id": PHASE_ID,
        "generated_at": now_iso(),
        "status": (
            "provider_alignment_ready"
            if provider_alignment.get("status") == "provider_alignment_ready"
            else "alignment_ready_evidence_maturing"
        ),
        "timestamp_semantics": [
            "observed_at",
            "published_at",
            "available_at",
            "ingested_at",
            "decision_at",
            "outcome_available_at",
            "revision_vintage",
        ],
        "relationship_count": len(eligibility),
        "relationship_mapping_counts": dict(sorted(mapping_counts.items())),
        "source_independence_cluster_count": len(clusters),
        "source_independence_measured_after_duplicate_clustering": True,
        "classified_window_count": coverage.get("classified_record_count"),
        "eligible_forward_score_input_count": coverage.get("eligible_forward_score_input_count"),
        "provider_alignment_record_count": provider_alignment.get("alignment_record_count"),
        "provider_eligible_forward_window_count": provider_alignment.get(
            "eligible_forward_window_count"
        ),
        "score_before_label_boundary": provider_alignment.get("score_before_label_boundary"),
        "leakage_violation_count": leakage.get("leakage_violation_count"),
        "paperops_watch_only_mode": True,
        "authority": authority_flags(),
    }


def validate_point_in_time_evidence(bundle: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    alignment = bundle["alignment"]
    eligibility = bundle["eligibility"]
    coverage = bundle["coverage"]
    typed = bundle["typed"]
    leakage = bundle["leakage"]
    provider_alignment = bundle["provider_alignment"]
    if len(eligibility) != 41 * 19:
        errors.append("eligibility_graph_not_whole_universe")
    if coverage.get("classified_record_count") != coverage.get("memory_record_count"):
        errors.append("forward_window_classification_incomplete")
    if coverage.get("all_missing_windows_have_typed_reason") is not True:
        errors.append("missing_window_reason_not_typed")
    if leakage.get("leakage_violation_count") != 0:
        errors.append("eligible_leakage_violation_present")
    if typed.get("all_gaps_typed") is not True:
        errors.append("evidence_contract_gap_typing_incomplete")
    if provider_alignment.get("provider_backfill_contract_complete") is True:
        if int(provider_alignment.get("alignment_record_count") or 0) <= 0:
            errors.append("provider_alignment_has_no_records")
        if int(provider_alignment.get("eligible_forward_window_count") or 0) <= 0:
            errors.append("provider_alignment_has_no_forward_windows")
    if provider_alignment.get("future_label_value_count") != 0:
        errors.append("provider_alignment_contains_future_label_values")
    if provider_alignment.get("score_before_label_boundary") is not True:
        errors.append("provider_alignment_score_before_label_boundary_missing")
    for window in coverage.get("windows", []):
        if window.get("eligible_score_input") is True:
            semantics = window.get("timestamp_semantics", {})
            if not semantics.get("available_at"):
                errors.append("eligible_score_input_available_at_missing")
            if not window.get("provenance"):
                errors.append("eligible_score_input_provenance_missing")
    router_records = read_jsonl(runtime_dir() / "qadam_router_evidence_contracts.jsonl")
    for record in router_records:
        state = str(record.get("subject", {}).get("final_state") or "")
        if state == "paper_review_candidate" and record.get("missing_evidence_count", 0) > 0:
            errors.append("router_eligible_contract_has_missing_critical_fields")
    for payload, prefix in (
        (alignment, "alignment"),
        (coverage, "coverage"),
        (typed, "typed"),
        (leakage, "leakage"),
        (provider_alignment, "provider_alignment"),
    ):
        errors.extend(validate_authority(payload.get("authority", {}), prefix=prefix))
    return unique_errors(errors)


def build_and_write_point_in_time_evidence(
    settings: Settings | None = None,
) -> tuple[dict[str, Any], dict[str, Any], list[str]]:
    runtime = runtime_dir(settings)
    store = AtomicArtifactStore(runtime)
    source_universe = read_json(runtime / SOURCE_UNIVERSE_ARTIFACT)
    trading_universe = read_json(runtime / TRADING_UNIVERSE_ARTIFACT)
    sources = (
        source_universe.get("sources") if isinstance(source_universe.get("sources"), list) else []
    )
    instruments = (
        trading_universe.get("instruments")
        if isinstance(trading_universe.get("instruments"), list)
        else []
    )
    operational = read_jsonl(runtime / SOURCE_OPERATIONAL_ARTIFACT)
    operational_by_key = {str(record.get("source_key")): record for record in operational}
    memory_records = read_jsonl(runtime / MEMORY_RECORDS_ARTIFACT)
    eligibility = build_eligibility_graph(sources, instruments, operational_by_key)
    coverage, leakage = build_forward_coverage(memory_records, eligibility)
    provider_alignment = build_provider_lake_alignment(runtime, eligibility)
    legacy_eligible_count = int(coverage.get("eligible_forward_score_input_count") or 0)
    provider_eligible_count = int(provider_alignment.get("eligible_forward_window_count") or 0)
    coverage.update(
        {
            "legacy_eligible_forward_score_input_count": legacy_eligible_count,
            "provider_alignment_record_count": provider_alignment.get("alignment_record_count"),
            "provider_eligible_forward_window_count": provider_eligible_count,
            "eligible_forward_score_input_count": (legacy_eligible_count + provider_eligible_count),
            "provider_alignment_records_path": provider_alignment.get("alignment_records_path"),
            "score_before_label_boundary": True,
        }
    )
    leakage.update(
        {
            "provider_alignment_record_count": provider_alignment.get("alignment_record_count"),
            "provider_future_label_value_count": provider_alignment.get("future_label_value_count"),
            "provider_alignment_leakage_violation_count": 0,
        }
    )
    typed = build_typed_evidence_completion(runtime)
    alignment = _alignment_summary(
        eligibility,
        coverage,
        leakage,
        provider_alignment,
    )
    bundle = {
        "alignment": alignment,
        "eligibility": eligibility,
        "coverage": coverage,
        "typed": typed,
        "leakage": leakage,
        "provider_alignment": provider_alignment,
    }
    store.write_json(ALIGNMENT_ARTIFACT, alignment)
    store.write_jsonl(ELIGIBILITY_ARTIFACT, eligibility)
    store.write_json(FORWARD_COVERAGE_ARTIFACT, coverage)
    store.write_json(TYPED_COMPLETION_ARTIFACT, typed)
    store.write_json(LEAKAGE_ARTIFACT, leakage)
    store.write_json(PROVIDER_ALIGNMENT_ARTIFACT, provider_alignment)
    errors = validate_point_in_time_evidence(bundle)
    checks = {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "qadam_point_in_time_evidence_checks",
        "phase_id": PHASE_ID,
        "generated_at": now_iso(),
        "status": "passed" if not errors else "blocked",
        "relationship_count": len(eligibility),
        "memory_record_count": len(memory_records),
        "classified_window_count": coverage["classified_record_count"],
        "eligible_forward_score_input_count": coverage["eligible_forward_score_input_count"],
        "provider_alignment_record_count": provider_alignment["alignment_record_count"],
        "provider_eligible_forward_window_count": provider_alignment[
            "eligible_forward_window_count"
        ],
        "provider_future_label_value_count": provider_alignment["future_label_value_count"],
        "provider_alignment_status": provider_alignment["status"],
        "typed_evidence_gap_count": typed["typed_gap_record_count"],
        "typed_evidence_completed_count": typed["completed_from_verified_existing_data_count"],
        "eligible_leakage_violation_count": leakage["leakage_violation_count"],
        "source_independence_cluster_count": alignment["source_independence_cluster_count"],
        "validation_error_count": len(errors),
        "validation_errors": errors,
        "broker_write_count": 0,
        "authority": authority_flags(),
    }
    store.write_json(CHECK_ARTIFACT, checks)
    return bundle, checks, errors
