"""OR-7 separate forward outcomes and versioned transaction-cost labels."""

from __future__ import annotations

from bisect import bisect_left
from collections import Counter, defaultdict
from datetime import datetime, timedelta
import json
from pathlib import Path
from statistics import pstdev
from typing import Any

from orchestrator.config import Settings
from orchestrator.qadam_canonical_contracts import AtomicArtifactStore
from orchestrator.qadam_operator_ready_common import (
    ROOT,
    authority_flags,
    canonical_json,
    file_sha256,
    now_iso,
    read_json,
    read_jsonl,
    runtime_dir,
    sha256_text,
    unique_errors,
    validate_authority,
)
from orchestrator.qadam_wave_b_common import (
    parse_timestamp,
    record_set_hash,
    stable_id,
    write_jsonl_atomic,
)

SCHEMA_VERSION = "qadam_forward_labels.v2"
PHASE_ID = "OR-7"
COST_MODEL_VERSION = "qadam_cost_model.v2_daily_conservative"

MANIFEST_ARTIFACT = "qadam_forward_label_manifest.json"
COST_MODEL_ARTIFACT = "qadam_transaction_cost_model.json"
COVERAGE_ARTIFACT = "qadam_label_coverage.json"
QUALITY_ARTIFACT = "qadam_label_quality_audit.json"
CHECK_ARTIFACT = "qadam_forward_labels_checks.json"

SCORE_TAPE_MANIFEST_ARTIFACT = "qadam_pattern_score_tape_manifest.json"
TRADING_UNIVERSE_ARTIFACT = "qsase_trading_universe.json"
PRICE_MANIFEST_ARTIFACT = "qadam_price_backfill_manifest.json"
BACKFILL_COVERAGE_ARTIFACT = "qadam_backfill_coverage.json"

RESEARCH_LABEL_ROOT = ROOT / "data" / "research" / "forward_labels"
PROXY_MAP = {"CL=F": "USO", "SI=F": "SLV"}
HORIZON_OFFSETS = {
    "1d_forward": 1,
    "3d_forward": 3,
    "5d_forward": 5,
    "10d_forward": 10,
    "20d_forward": 20,
    "30d_forward": 30,
}
MAX_EXTERNAL_ALIGNMENT_LAG = timedelta(days=7)
FAVORABLE_THRESHOLD = 0.01


def _number(value: Any) -> float | None:
    if value is None or isinstance(value, bool):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _return(before: float, after: float) -> float:
    return round((after / before) - 1.0, 10)


def _derived_daily_bar_available_at(observed_at: datetime) -> datetime:
    return observed_at + timedelta(days=1)


def _instrument_cost_record(
    instrument: dict[str, Any],
    price_coverage: dict[str, dict[str, Any]] | None = None,
) -> dict[str, Any]:
    symbol = str(instrument.get("symbol") or "unknown")
    prediction = symbol.startswith(("KALSHI:", "POLYMARKET:"))
    futures = symbol.endswith("=F")
    direct_paperable = instrument.get("paper_route_available") is True
    proxy = PROXY_MAP.get(symbol)
    if prediction:
        base_bps = None
        state = "unsupported_specialized_contract_cost_model"
        net_allowed = False
        cost_basis_instrument = None
    elif futures:
        base_bps = 8.0
        state = "conservative_proxy_cost_with_explicit_basis_risk"
        net_allowed = True
        cost_basis_instrument = proxy
    else:
        base_bps = 6.0 if direct_paperable else 10.0
        state = "conservative_daily_research_cost_assumption"
        net_allowed = True
        cost_basis_instrument = symbol
    coverage = (price_coverage or {}).get(proxy or symbol, {})
    period = {
        "period_id": stable_id(
            "transaction-cost-period", COST_MODEL_VERSION, symbol, "all_history"
        ),
        "effective_from": coverage.get("coverage_start"),
        "effective_to": coverage.get("coverage_end"),
        "round_trip_cost_bps": base_bps,
        "commission_bps": 0.0 if base_bps is not None else None,
        "spread_slippage_bps": base_bps,
        "assumption_source": (
            "conservative_research_assumption_not_historical_quote"
            if base_bps is not None
            else "unsupported_no_assumption_created"
        ),
    }
    return {
        "instrument": symbol,
        "asset_class": instrument.get("market_family"),
        "execution_proxy": proxy or (symbol if direct_paperable else None),
        "cost_basis_instrument": cost_basis_instrument,
        "research_execution_proxy_mismatch": proxy is not None,
        "round_trip_cost_bps": base_bps,
        "commission_bps": period["commission_bps"],
        "spread_slippage_bps": period["spread_slippage_bps"],
        "liquidity_assumption_state": state,
        "label_net_return_allowed": net_allowed,
        "paper_route_available": direct_paperable,
        "cost_is_versioned_research_assumption": True,
        "cost_periods": [period],
        "paperability_is_separate_from_research_net_label": True,
    }


def build_forward_label(
    score: dict[str, Any],
    *,
    price_before: float,
    price_after: float,
    outcome_available_at: str,
    cost_bps: float,
    benchmark_return: float | None = None,
) -> dict[str, Any]:
    """Small deterministic helper retained for unit and contract testing."""
    decision = parse_timestamp(score.get("scoring_as_of"))
    outcome_time = parse_timestamp(outcome_available_at)
    if decision is None or outcome_time is None or outcome_time <= decision:
        raise ValueError("forward_label_outcome_not_after_score")
    if price_before <= 0:
        raise ValueError("forward_label_price_before_invalid")
    gross = (price_after / price_before) - 1.0
    net = gross - (cost_bps / 10_000.0)
    return {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "qadam_forward_label",
        "label_id": stable_id(
            "forward-label", score.get("score_id"), outcome_available_at
        ),
        "score_id": score.get("score_id"),
        "score_created_before_label": True,
        "decision_at": score.get("scoring_as_of"),
        "outcome_available_at": outcome_available_at,
        "horizon": score.get("horizon_hypothesis"),
        "gross_return": round(gross, 10),
        "net_return": round(net, 10),
        "benchmark_relative_return": (
            round(gross - benchmark_return, 10)
            if benchmark_return is not None
            else None
        ),
        "max_favorable_excursion": None,
        "max_adverse_excursion": None,
        "realized_volatility": None,
        "time_to_threshold": None,
        "gap_risk": None,
        "liquidity_spread_state": "cost_model_assumption",
        "unfilled_or_delayed_entry_proxy": None,
        "market_regime": "unclassified",
        "invalidation_occurred": None,
        "transaction_cost_bps": cost_bps,
        "overlap_group_id": stable_id(
            "label-overlap-group",
            score.get("instrument"),
            score.get("scoring_as_of"),
            score.get("horizon_hypothesis"),
        ),
        "independent_sample": False,
        "authority": authority_flags(),
    }


def _load_price_series(
    price_manifest: dict[str, Any],
) -> tuple[dict[str, dict[str, Any]], dict[str, Any]]:
    bars_by_symbol: dict[str, dict[str, dict[str, Any]]] = defaultdict(dict)
    partition_evidence: list[dict[str, Any]] = []
    counters: Counter[str] = Counter()
    seen_paths: set[str] = set()
    for job in price_manifest.get("jobs", []):
        if job.get("status") != "complete":
            continue
        symbol = str(job.get("instrument") or "unknown")
        year = str(job.get("date_partition") or "")
        path_text = str(job.get("normalized_path") or "")
        if not path_text:
            path_text = (
                f"data/research/prices/symbol={symbol.replace('/', '_')}"
                f"/interval=1d/year={year}/bars.jsonl"
            )
        if path_text in seen_paths:
            continue
        seen_paths.add(path_text)
        path = ROOT / path_text
        if not path.is_file():
            counters["price_partition_missing_count"] += 1
            continue
        dataset_sha = file_sha256(path)
        partition_evidence.append(
            {
                "symbol": symbol,
                "year": year,
                "provider": job.get("provider"),
                "path": path_text,
                "sha256": dataset_sha,
                "row_count": job.get("row_count"),
            }
        )
        provider = str(job.get("provider") or "unknown")
        counters["price_partition_count"] += 1
        with path.open("r", encoding="utf-8") as handle:
            for line in handle:
                if not line.strip():
                    continue
                try:
                    raw = json.loads(line)
                except json.JSONDecodeError:
                    counters["invalid_price_json_count"] += 1
                    continue
                observed_at = parse_timestamp(raw.get("observed_at"))
                close = _number(raw.get("close"))
                if observed_at is None or close is None or close <= 0:
                    counters["invalid_price_bar_count"] += 1
                    continue
                if provider == "alpaca_market_data_v2":
                    available_at = _derived_daily_bar_available_at(observed_at)
                    availability_policy = "derived_daily_bar_available_after_session"
                else:
                    available_at = parse_timestamp(raw.get("available_at"))
                    availability_policy = str(
                        raw.get("point_in_time_policy") or "provider_available_at"
                    )
                if available_at is None:
                    counters["price_available_at_missing_count"] += 1
                    continue
                bars_by_symbol[symbol][observed_at.isoformat()] = {
                    "symbol": symbol,
                    "observed_at": observed_at,
                    "available_at": available_at,
                    "open": _number(raw.get("open")) or close,
                    "high": _number(raw.get("high")) or close,
                    "low": _number(raw.get("low")) or close,
                    "close": close,
                    "volume": _number(raw.get("volume")),
                    "provider": provider,
                    "availability_policy": availability_policy,
                    "partition_path": path_text,
                    "roll_event": raw.get("roll_event") is True,
                    "roll_gap_ratio": _number(raw.get("roll_gap_ratio")),
                    "contract_symbol": raw.get("contract_symbol"),
                    "corporate_action_policy": raw.get("provider_adjustment"),
                }
                counters["price_bar_count"] += 1
    series: dict[str, dict[str, Any]] = {}
    coverage: dict[str, dict[str, Any]] = {}
    for symbol, rows in bars_by_symbol.items():
        bars = sorted(rows.values(), key=lambda row: row["available_at"])
        series[symbol] = {
            "bars": bars,
            "available_times": [bar["available_at"] for bar in bars],
        }
        coverage[symbol] = {
            "bar_count": len(bars),
            "coverage_start": bars[0]["available_at"].isoformat(),
            "coverage_end": bars[-1]["available_at"].isoformat(),
            "providers": sorted({bar["provider"] for bar in bars}),
        }
    price_lake_hash = sha256_text(canonical_json(sorted(partition_evidence, key=canonical_json)))
    counters["price_symbol_count"] = len(series)
    return series, {
        "price_lake_sha256": price_lake_hash,
        "partition_evidence": sorted(partition_evidence, key=canonical_json),
        "coverage": coverage,
        "counters": dict(counters),
    }


def _exact_baseline_index(series: dict[str, Any], decision: datetime) -> int | None:
    times = series["available_times"]
    index = bisect_left(times, decision)
    if index < len(times) and abs((times[index] - decision).total_seconds()) <= 1:
        return index
    return None


def _external_window(
    series: dict[str, Any] | None,
    decision: datetime,
    offset: int,
) -> tuple[dict[str, Any] | None, dict[str, Any] | None, float | None]:
    if not series:
        return None, None, None
    times = series["available_times"]
    index = bisect_left(times, decision)
    if index >= len(times) or times[index] - decision > MAX_EXTERNAL_ALIGNMENT_LAG:
        return None, None, None
    outcome_index = index + offset
    if outcome_index >= len(times):
        return series["bars"][index], None, None
    return (
        series["bars"][index],
        series["bars"][outcome_index],
        (times[index] - decision).total_seconds() / 3600.0,
    )


def _direction_class(direction: Any) -> str:
    value = str(direction or "").lower()
    if "upside" in value or value.startswith("long"):
        return "long"
    if "downside" in value or value.startswith("short"):
        return "short"
    return "unresolved"


def _path_metrics(
    baseline: dict[str, Any],
    future_bars: list[dict[str, Any]],
    direction: str,
) -> dict[str, Any]:
    before = float(baseline["close"])
    highs = [float(bar["high"]) for bar in future_bars]
    lows = [float(bar["low"]) for bar in future_bars]
    closes = [before, *[float(bar["close"]) for bar in future_bars]]
    upside = max((high / before) - 1.0 for high in highs)
    downside = min((low / before) - 1.0 for low in lows)
    returns = [
        (current / previous) - 1.0
        for previous, current in zip(closes, closes[1:])
        if previous > 0
    ]
    gaps: list[float] = []
    previous_close = before
    for bar in future_bars:
        gaps.append(abs((float(bar["open"]) / previous_close) - 1.0))
        previous_close = float(bar["close"])
    time_to_threshold: int | None = None
    if direction == "long":
        for index, high in enumerate(highs, start=1):
            if (high / before) - 1.0 >= FAVORABLE_THRESHOLD:
                time_to_threshold = index
                break
        favorable = upside
        adverse = downside
    elif direction == "short":
        for index, low in enumerate(lows, start=1):
            if 1.0 - (low / before) >= FAVORABLE_THRESHOLD:
                time_to_threshold = index
                break
        favorable = -downside
        adverse = -upside
    else:
        favorable = None
        adverse = None
    roll_events = [bar for bar in future_bars if bar.get("roll_event") is True]
    return {
        "maximum_upside_excursion": round(upside, 10),
        "maximum_downside_excursion": round(downside, 10),
        "max_favorable_excursion": (
            round(favorable, 10) if favorable is not None else None
        ),
        "max_adverse_excursion": (
            round(adverse, 10) if adverse is not None else None
        ),
        "realized_volatility": (
            round(pstdev(returns), 10) if len(returns) >= 2 else None
        ),
        "time_to_threshold": time_to_threshold,
        "threshold_return": FAVORABLE_THRESHOLD,
        "gap_risk": round(max(gaps), 10) if gaps else None,
        "futures_roll_crossed": bool(roll_events),
        "futures_roll_event_count": len(roll_events),
        "futures_roll_gap_ratios": [
            bar.get("roll_gap_ratio")
            for bar in roll_events
            if bar.get("roll_gap_ratio") is not None
        ],
    }


def _label_score(
    score: dict[str, Any],
    *,
    source_score_partition_id: str,
    series_by_symbol: dict[str, dict[str, Any]],
    cost_by_instrument: dict[str, dict[str, Any]],
    price_lake_sha256: str,
    cost_model_hash: str,
) -> tuple[dict[str, Any] | None, dict[str, Any] | None]:
    score_id = str(score.get("score_id") or "")
    instrument = str(score.get("instrument") or "unknown")
    horizon = str(score.get("horizon_hypothesis") or "unknown")
    decision = parse_timestamp(score.get("scoring_as_of"))
    offset = HORIZON_OFFSETS.get(horizon)
    missing_base = {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "qadam_forward_label_missing",
        "missing_label_id": stable_id(
            "forward-label-missing", score_id, price_lake_sha256, cost_model_hash
        ),
        "score_id": score_id,
        "source_score_partition_id": source_score_partition_id,
        "instrument": instrument,
        "horizon": horizon,
        "decision_at": score.get("scoring_as_of"),
        "classified": True,
        "label_created": False,
    }
    if decision is None:
        return None, {**missing_base, "reason": "score_decision_timestamp_invalid"}
    if offset is None:
        return None, {**missing_base, "reason": "unsupported_or_event_expiry_horizon"}
    series = series_by_symbol.get(instrument)
    if not series:
        return None, {**missing_base, "reason": "instrument_price_history_unavailable"}
    baseline_index = _exact_baseline_index(series, decision)
    if baseline_index is None:
        return None, {**missing_base, "reason": "score_baseline_not_found_exactly"}
    outcome_index = baseline_index + offset
    if outcome_index >= len(series["bars"]):
        return None, {**missing_base, "reason": "forward_window_not_yet_complete"}

    baseline = series["bars"][baseline_index]
    outcome = series["bars"][outcome_index]
    future_bars = series["bars"][baseline_index + 1 : outcome_index + 1]
    research_gross = _return(float(baseline["close"]), float(outcome["close"]))
    direction = _direction_class(score.get("direction_hypothesis"))
    path_metrics = _path_metrics(baseline, future_bars, direction)

    cost = cost_by_instrument.get(instrument, {})
    execution_symbol = cost.get("cost_basis_instrument")
    execution_entry: dict[str, Any] | None = None
    execution_outcome: dict[str, Any] | None = None
    execution_lag_hours: float | None = None
    execution_gross: float | None = None
    if cost.get("label_net_return_allowed") is True and execution_symbol:
        if execution_symbol == instrument:
            execution_entry = baseline
            execution_outcome = outcome
            execution_lag_hours = 0.0
        else:
            execution_entry, execution_outcome, execution_lag_hours = _external_window(
                series_by_symbol.get(str(execution_symbol)), decision, offset
            )
        if execution_entry and execution_outcome:
            execution_gross = _return(
                float(execution_entry["close"]), float(execution_outcome["close"])
            )
    cost_bps = _number(cost.get("round_trip_cost_bps"))
    if execution_gross is not None and cost_bps is not None:
        long_net_return = round(execution_gross - (cost_bps / 10_000.0), 10)
        short_net_return = round(-execution_gross - (cost_bps / 10_000.0), 10)
        if direction == "long":
            net_return = long_net_return
        elif direction == "short":
            net_return = short_net_return
        else:
            net_return = None
        if direction == "unresolved":
            net_state = "direction_unresolved_counterfactuals_only"
        else:
            net_state = (
                "proxy_adjusted_directional_research_estimate"
                if execution_symbol != instrument
                else "direct_instrument_directional_research_estimate"
            )
    elif cost.get("label_net_return_allowed") is not True:
        long_net_return = None
        short_net_return = None
        net_return = None
        net_state = "unsupported_cost_model_fail_closed"
    else:
        long_net_return = None
        short_net_return = None
        net_return = None
        net_state = "execution_proxy_history_missing_fail_closed"

    direction_adjusted_gross = (
        research_gross
        if direction == "long"
        else -research_gross
        if direction == "short"
        else None
    )

    benchmark_entry, benchmark_outcome, _benchmark_lag = _external_window(
        series_by_symbol.get("SPY"), decision, offset
    )
    benchmark_return = (
        _return(float(benchmark_entry["close"]), float(benchmark_outcome["close"]))
        if benchmark_entry and benchmark_outcome
        else None
    )
    availability_candidates = [outcome["available_at"]]
    if execution_outcome:
        availability_candidates.append(execution_outcome["available_at"])
    if benchmark_outcome:
        availability_candidates.append(benchmark_outcome["available_at"])
    outcome_available_at = max(availability_candidates)
    if outcome_available_at <= decision:
        return None, {**missing_base, "reason": "outcome_not_strictly_after_score"}

    input_material = {
        "score_id": score_id,
        "source_score_partition_id": source_score_partition_id,
        "instrument": instrument,
        "horizon": horizon,
        "decision_at": decision.isoformat(),
        "research_outcome_available_at": outcome["available_at"].isoformat(),
        "research_gross_return": research_gross,
        "direction_adjusted_gross_return": direction_adjusted_gross,
        "execution_instrument": execution_symbol,
        "execution_gross_return": execution_gross,
        "long_net_return": long_net_return,
        "short_net_return": short_net_return,
        "net_return": net_return,
        "benchmark_return": benchmark_return,
        "price_lake_sha256": price_lake_sha256,
        "cost_model_hash": cost_model_hash,
    }
    fingerprint = sha256_text(canonical_json(input_material))
    label = {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "qadam_forward_label",
        "phase_id": PHASE_ID,
        "label_id": stable_id("forward-label", score_id, fingerprint),
        "score_id": score_id,
        "source_score_partition_id": source_score_partition_id,
        "score_created_before_label": True,
        "score_partition_read_only": True,
        "decision_at": decision.isoformat(),
        "research_outcome_available_at": outcome["available_at"].isoformat(),
        "outcome_available_at": outcome_available_at.isoformat(),
        "instrument": instrument,
        "strategy_family_id": score.get("strategy_family_id"),
        "direction_hypothesis": score.get("direction_hypothesis"),
        "direction_class": direction,
        "horizon": horizon,
        "price_before": round(float(baseline["close"]), 10),
        "price_after": round(float(outcome["close"]), 10),
        "gross_return": research_gross,
        "research_gross_return": research_gross,
        "gross_return_state": "raw_instrument_forward_return_not_trade_pnl",
        "direction_adjusted_gross_return": direction_adjusted_gross,
        "directional_outcome_available": direction != "unresolved",
        "execution_instrument": execution_symbol,
        "execution_proxy_used": execution_symbol != instrument,
        "execution_entry_delay_hours": (
            round(execution_lag_hours, 6)
            if execution_lag_hours is not None
            else None
        ),
        "execution_gross_return": execution_gross,
        "long_net_return": long_net_return,
        "short_net_return": short_net_return,
        "net_return": net_return,
        "net_return_state": net_state,
        "benchmark_instrument": "SPY",
        "benchmark_return": benchmark_return,
        "benchmark_relative_return": (
            round(research_gross - benchmark_return, 10)
            if benchmark_return is not None
            else None
        ),
        "research_execution_basis_return": (
            round(execution_gross - research_gross, 10)
            if execution_gross is not None and execution_symbol != instrument
            else 0.0
            if execution_gross is not None
            else None
        ),
        **path_metrics,
        "liquidity_spread_state": cost.get("liquidity_assumption_state"),
        "unfilled_or_delayed_entry_proxy": {
            "state": (
                "entry_proxy_aligned"
                if execution_entry and execution_outcome
                else "entry_proxy_history_missing"
                if execution_symbol and execution_symbol != instrument
                else "not_required_or_unsupported"
            ),
            "entry_delay_hours": execution_lag_hours,
            "historical_fill_simulated": False,
        },
        "market_regime": score.get("regime_state") or "unclassified",
        "invalidation_occurred": None,
        "invalidation_state": "not_defined_at_or6_score",
        "transaction_cost_model_version": COST_MODEL_VERSION,
        "transaction_cost_bps": cost_bps,
        "cost_model_hash": cost_model_hash,
        "price_lake_sha256": price_lake_sha256,
        "research_price_provider": baseline.get("provider"),
        "execution_price_provider": (
            execution_entry.get("provider") if execution_entry else None
        ),
        "corporate_action_policy": baseline.get("corporate_action_policy"),
        "overlap_group_id": None,
        "overlap_group_size": None,
        "independent_sample": False,
        "input_fingerprint": fingerprint,
        "candidate_creation_allowed": False,
        "order_creation_allowed": False,
        "proof_credit_allowed": False,
        "authority_contract_ref": f"data/runtime/{MANIFEST_ARTIFACT}#authority",
    }
    return label, None


def _assign_overlap_groups(labels: list[dict[str, Any]]) -> None:
    grouped: defaultdict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for label in labels:
        grouped[(str(label["instrument"]), str(label["horizon"]))].append(label)
    group_members: defaultdict[str, list[dict[str, Any]]] = defaultdict(list)
    for (instrument, horizon), rows in sorted(grouped.items()):
        rows.sort(
            key=lambda row: (
                str(row["decision_at"]),
                str(row["outcome_available_at"]),
                str(row["score_id"]),
            )
        )
        current_group: str | None = None
        current_end: datetime | None = None
        for row in rows:
            decision = parse_timestamp(row["decision_at"])
            outcome = parse_timestamp(row["research_outcome_available_at"])
            if decision is None or outcome is None:
                continue
            if current_group is None or current_end is None or decision >= current_end:
                current_group = stable_id(
                    "label-overlap-group", instrument, horizon, row["score_id"]
                )
                current_end = outcome
            row["overlap_group_id"] = current_group
            group_members[current_group].append(row)
    for members in group_members.values():
        members.sort(key=lambda row: (row["decision_at"], row["score_id"]))
        for index, row in enumerate(members):
            row["overlap_group_size"] = len(members)
            row["independent_sample"] = index == 0


def _write_partition(path: Path, rows: list[dict[str, Any]]) -> tuple[str, bool]:
    resolved = path.resolve()
    if not resolved.is_relative_to(RESEARCH_LABEL_ROOT.resolve()):
        raise ValueError("forward_label_path_outside_research_store")
    expected_hash = record_set_hash(rows)
    if resolved.exists():
        if record_set_hash(read_jsonl(resolved)) != expected_hash:
            raise ValueError("completed_forward_label_partition_immutable_mismatch")
        return expected_hash, True
    write_jsonl_atomic(resolved, rows)
    return expected_hash, False


def _score_plane_hash(partitions: list[dict[str, Any]]) -> str:
    material = [
        {
            "partition_id": row.get("partition_id"),
            "dataset_path": row.get("dataset_path"),
            "dataset_sha256": row.get("dataset_sha256"),
            "record_set_hash": row.get("record_set_hash"),
            "row_count": row.get("row_count"),
        }
        for row in partitions
    ]
    return sha256_text(canonical_json(material))


def build_forward_label_state(settings: Settings | None = None) -> dict[str, Any]:
    runtime = runtime_dir(settings)
    score_manifest = read_json(runtime / SCORE_TAPE_MANIFEST_ARTIFACT)
    trading = read_json(runtime / TRADING_UNIVERSE_ARTIFACT)
    price_manifest = read_json(runtime / PRICE_MANIFEST_ARTIFACT)
    backfill = read_json(runtime / BACKFILL_COVERAGE_ARTIFACT)
    score_partitions = [
        row
        for row in score_manifest.get("partitions", [])
        if row.get("status") == "complete" and int(row.get("row_count") or 0) > 0
    ]
    if score_manifest.get("status") != "complete_with_classified_gaps":
        raise ValueError("or6_score_tape_not_empirically_complete")
    if not score_partitions:
        raise ValueError("or6_score_tape_has_no_completed_partitions")
    score_plane_hash_before = _score_plane_hash(score_partitions)
    series_by_symbol, price_state = _load_price_series(price_manifest)
    instruments = (
        trading.get("instruments")
        if isinstance(trading.get("instruments"), list)
        else []
    )
    cost_records = [
        _instrument_cost_record(instrument, price_state["coverage"])
        for instrument in instruments
    ]
    cost_model_hash = sha256_text(canonical_json(cost_records))
    cost_by_instrument = {row["instrument"]: row for row in cost_records}

    labels: list[dict[str, Any]] = []
    missing: list[dict[str, Any]] = []
    labels_by_source_partition: defaultdict[str, list[dict[str, Any]]] = defaultdict(list)
    missing_by_source_partition: defaultdict[str, list[dict[str, Any]]] = defaultdict(list)
    score_partition_meta: dict[str, dict[str, Any]] = {}
    score_input_count = 0
    for partition in score_partitions:
        partition_id = str(partition["partition_id"])
        score_partition_meta[partition_id] = partition
        score_path = ROOT / str(partition.get("dataset_path") or "")
        if not score_path.is_file() or file_sha256(score_path) != partition.get(
            "dataset_sha256"
        ):
            raise ValueError(f"or6_score_partition_checksum_mismatch:{partition_id}")
        score_rows = read_jsonl(score_path)
        if len(score_rows) != int(partition.get("row_count") or 0):
            raise ValueError(f"or6_score_partition_row_count_mismatch:{partition_id}")
        score_input_count += len(score_rows)
        for score in score_rows:
            label, missing_record = _label_score(
                score,
                source_score_partition_id=partition_id,
                series_by_symbol=series_by_symbol,
                cost_by_instrument=cost_by_instrument,
                price_lake_sha256=price_state["price_lake_sha256"],
                cost_model_hash=cost_model_hash,
            )
            if label:
                labels.append(label)
                labels_by_source_partition[partition_id].append(label)
            elif missing_record:
                missing.append(missing_record)
                missing_by_source_partition[partition_id].append(missing_record)
    _assign_overlap_groups(labels)

    output_partitions: list[dict[str, Any]] = []
    reused_count = 0
    for source_partition_id, source_partition in sorted(score_partition_meta.items()):
        label_rows = sorted(
            labels_by_source_partition[source_partition_id],
            key=lambda row: (row["decision_at"], row["score_id"]),
        )
        missing_rows = sorted(
            missing_by_source_partition[source_partition_id],
            key=lambda row: (str(row.get("decision_at")), row["score_id"]),
        )
        partition_material_hash = sha256_text(
            canonical_json(
                {
                    "source_score_partition_id": source_partition_id,
                    "source_score_sha256": source_partition.get("dataset_sha256"),
                    "price_lake_sha256": price_state["price_lake_sha256"],
                    "cost_model_hash": cost_model_hash,
                    "label_record_set_hash": record_set_hash(label_rows),
                    "missing_record_set_hash": record_set_hash(missing_rows),
                }
            )
        )
        base = (
            RESEARCH_LABEL_ROOT
            / f"score_tape={score_plane_hash_before[:16]}"
            / f"price_lake={price_state['price_lake_sha256'][:16]}"
            / f"cost_model={cost_model_hash[:16]}"
            / f"source_partition={source_partition_id.split(':')[-1]}"
            / f"partition={partition_material_hash[:24]}"
        )
        label_path = base / "labels.jsonl"
        missing_path = base / "missing.jsonl"
        label_hash, label_reused = _write_partition(label_path, label_rows)
        missing_hash, missing_reused = _write_partition(missing_path, missing_rows)
        reused_count += int(label_reused and missing_reused)
        output_partitions.append(
            {
                "partition_id": stable_id(
                    "forward-label-partition",
                    source_partition_id,
                    partition_material_hash,
                ),
                "source_score_partition_id": source_partition_id,
                "source_score_dataset_sha256": source_partition.get("dataset_sha256"),
                "strategy_family_id": source_partition.get("strategy_family_id"),
                "instrument": source_partition.get("instrument"),
                "date_partition": source_partition.get("date_partition"),
                "horizon": source_partition.get("horizon"),
                "status": (
                    "complete_with_labels"
                    if label_rows
                    else "complete_no_labels_classified"
                ),
                "score_created_before_label": True,
                "score_plane_read_only": True,
                "score_row_count": int(source_partition.get("row_count") or 0),
                "row_count": len(label_rows),
                "missing_row_count": len(missing_rows),
                "classified_row_count": len(label_rows) + len(missing_rows),
                "dataset_path": str(label_path.relative_to(ROOT)),
                "dataset_sha256": file_sha256(label_path),
                "record_set_hash": label_hash,
                "missing_dataset_path": str(missing_path.relative_to(ROOT)),
                "missing_dataset_sha256": file_sha256(missing_path),
                "missing_record_set_hash": missing_hash,
                "price_lake_sha256": price_state["price_lake_sha256"],
                "cost_model_hash": cost_model_hash,
                "completed_partition_immutable": True,
                "reused_existing_partition": label_reused and missing_reused,
                "resume_cursor": (
                    {
                        "score_id": (label_rows or missing_rows)[-1]["score_id"],
                        "decision_at": (label_rows or missing_rows)[-1]["decision_at"],
                    }
                    if label_rows or missing_rows
                    else None
                ),
            }
        )
    output_partitions.sort(key=lambda row: row["partition_id"])
    score_plane_hash_after = _score_plane_hash(score_partitions)
    generated_at = now_iso()
    classified_count = len(labels) + len(missing)
    classification_ratio = (
        classified_count / score_input_count if score_input_count else 0.0
    )
    missing_reasons = Counter(row["reason"] for row in missing)
    label_ids = [row["label_id"] for row in labels]
    label_score_ids = [row["score_id"] for row in labels]
    labeled_score_ids = {row["score_id"] for row in labels}
    overlap_counts = Counter(row.get("overlap_group_id") for row in labels)
    source_counts = Counter(
        source.get("source_key")
        for partition in score_partitions
        for score in read_jsonl(ROOT / str(partition["dataset_path"]))
        if score.get("score_id") in labeled_score_ids
        for source in score.get("feature_inputs", [])
        if source.get("source_key")
    )
    manifest = {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "qadam_forward_label_manifest",
        "phase_id": PHASE_ID,
        "generated_at": generated_at,
        "status": (
            "complete_with_classified_gaps"
            if labels and classification_ratio == 1.0
            else "evidence_maturing"
        ),
        "research_store": str(RESEARCH_LABEL_ROOT.relative_to(ROOT)),
        "partition_count": len(output_partitions),
        "completed_partition_count": len(output_partitions),
        "label_count": len(labels),
        "typed_missing_label_count": len(missing),
        "score_input_count": score_input_count,
        "classified_score_input_count": classified_count,
        "classification_ratio": round(classification_ratio, 10),
        "partitions": output_partitions,
        "label_join_key": "score_id",
        "score_plane_read_only": True,
        "score_plane_hash_before": score_plane_hash_before,
        "score_plane_hash_after": score_plane_hash_after,
        "score_plane_unchanged": score_plane_hash_before == score_plane_hash_after,
        "label_write_after_score_required": True,
        "content_addressed_partitions": True,
        "completed_partitions_rewritten": False,
        "reused_completed_partition_count": reused_count,
        "price_lake_sha256": price_state["price_lake_sha256"],
        "cost_model_version": COST_MODEL_VERSION,
        "cost_model_hash": cost_model_hash,
        "paperops_watch_only_mode": True,
        "authority": authority_flags(),
    }
    cost_model = {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "qadam_transaction_cost_model",
        "phase_id": PHASE_ID,
        "generated_at": generated_at,
        "status": "versioned_conservative_model_with_fail_closed_unsupported_contracts",
        "cost_model_version": COST_MODEL_VERSION,
        "cost_model_hash": cost_model_hash,
        "instrument_count": len(cost_records),
        "instruments": cost_records,
        "unsupported_liquidity_assumption_count": sum(
            row["label_net_return_allowed"] is not True for row in cost_records
        ),
        "proxy_map": PROXY_MAP,
        "historical_spread_quotes_available": False,
        "conservative_assumption_disclosed": True,
        "cost_model_grants_no_paperability_or_execution_authority": True,
        "paperops_watch_only_mode": True,
        "authority": authority_flags(),
    }
    gross_count = len(labels)
    net_count = sum(row.get("net_return") is not None for row in labels)
    cost_adjusted_counterfactual_count = sum(
        row.get("long_net_return") is not None
        and row.get("short_net_return") is not None
        for row in labels
    )
    directional_gross_count = sum(
        row.get("direction_adjusted_gross_return") is not None for row in labels
    )
    net_return_states = Counter(row.get("net_return_state") for row in labels)
    coverage = {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "qadam_label_coverage",
        "phase_id": PHASE_ID,
        "generated_at": generated_at,
        "status": "complete_with_classified_gaps",
        "score_tape_row_count": score_input_count,
        "label_count": len(labels),
        "gross_label_count": gross_count,
        "net_label_count": net_count,
        "directional_gross_label_count": directional_gross_count,
        "directional_net_label_count": net_count,
        "cost_adjusted_counterfactual_label_count": cost_adjusted_counterfactual_count,
        "typed_missing_label_count": len(missing),
        "classification_ratio": round(classification_ratio, 10),
        "gross_coverage_ratio": round(gross_count / score_input_count, 10),
        "net_coverage_ratio": round(net_count / score_input_count, 10),
        "cost_adjusted_counterfactual_coverage_ratio": round(
            cost_adjusted_counterfactual_count / score_input_count, 10
        ),
        "missing_reason_counts": dict(sorted(missing_reasons.items())),
        "net_return_state_counts": dict(sorted(net_return_states.items())),
        "supported_horizons": sorted(HORIZON_OFFSETS),
        "provider_backfill_row_count": backfill.get("provider_row_count", 0),
        "coverage_by_source": dict(sorted(source_counts.items())),
        "coverage_by_strategy": dict(
            sorted(Counter(row.get("strategy_family_id") for row in labels).items())
        ),
        "coverage_by_instrument": dict(
            sorted(Counter(row["instrument"] for row in labels).items())
        ),
        "coverage_by_horizon": dict(
            sorted(Counter(row["horizon"] for row in labels).items())
        ),
        "coverage_by_regime": dict(
            sorted(Counter(row["market_regime"] for row in labels).items())
        ),
        "paperops_watch_only_mode": True,
        "authority": authority_flags(),
    }
    quality = {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "qadam_label_quality_audit",
        "phase_id": PHASE_ID,
        "generated_at": generated_at,
        "status": "passed" if labels and classification_ratio == 1.0 else "blocked",
        "score_created_before_label_violation_count": sum(
            parse_timestamp(row["outcome_available_at"])
            <= parse_timestamp(row["decision_at"])
            for row in labels
        ),
        "score_plane_unchanged": score_plane_hash_before == score_plane_hash_after,
        "duplicate_label_count": len(label_ids) - len(set(label_ids)),
        "duplicate_score_label_count": len(label_score_ids)
        - len(set(label_score_ids)),
        "unsupported_liquidity_net_label_count": sum(
            row.get("net_return") is not None
            and cost_by_instrument.get(row["instrument"], {}).get(
                "label_net_return_allowed"
            )
            is not True
            for row in labels
        ),
        "gross_and_net_retained": all(
            row.get("gross_return") is not None
            and (
                (
                    row.get("long_net_return") is not None
                    and row.get("short_net_return") is not None
                )
                or row.get("net_return_state")
                in {
                    "unsupported_cost_model_fail_closed",
                    "execution_proxy_history_missing_fail_closed",
                }
            )
            for row in labels
        ),
        "unresolved_direction_label_count": sum(
            row.get("direction_class") == "unresolved" for row in labels
        ),
        "unresolved_direction_assigned_net_return_count": sum(
            row.get("direction_class") == "unresolved"
            and row.get("net_return") is not None
            for row in labels
        ),
        "directional_net_consistency_violation_count": sum(
            (
                row.get("direction_class") == "long"
                and row.get("net_return") != row.get("long_net_return")
            )
            or (
                row.get("direction_class") == "short"
                and row.get("net_return") != row.get("short_net_return")
            )
            for row in labels
        ),
        "direction_policy": "raw_forward_return_is_direction_neutral; net_return_requires_a_direction_frozen_before_outcome; long_and_short_cost_adjusted_counterfactuals_support_train_only_direction_selection",
        "overlap_group_count": len(overlap_counts),
        "overlapping_label_count": sum(
            count for count in overlap_counts.values() if count > 1
        ),
        "independent_effective_sample_count": sum(
            row.get("independent_sample") is True for row in labels
        ),
        "overlap_policy": "anchored_forward_windows_share_one_group_until_the_anchor_outcome_and_admit_one_independent_sample",
        "proxy_adjusted_label_count": sum(
            row.get("execution_proxy_used") is True for row in labels
        ),
        "proxy_basis_risk_missing_count": sum(
            row.get("execution_proxy_used") is True
            and row.get("research_execution_basis_return") is None
            for row in labels
        ),
        "futures_roll_crossing_label_count": sum(
            row.get("futures_roll_crossed") is True for row in labels
        ),
        "benchmark_relative_label_count": sum(
            row.get("benchmark_relative_return") is not None for row in labels
        ),
        "invalidation_not_defined_count": sum(
            row.get("invalidation_occurred") is None for row in labels
        ),
        "calendar_and_market_session_policy": "provider_daily_bar_sequence_not_calendar_day_arithmetic",
        "proxy_basis_risk_required": True,
        "historical_fill_simulated": False,
        "paperops_watch_only_mode": True,
        "authority": authority_flags(),
    }
    return {
        "manifest": manifest,
        "cost_model": cost_model,
        "coverage": coverage,
        "quality": quality,
        "labels": labels,
        "missing": missing,
    }


def validate_forward_label_state(state: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    manifest = state["manifest"]
    costs = state["cost_model"]
    coverage = state["coverage"]
    quality = state["quality"]
    labels = state.get("labels", [])
    if costs.get("instrument_count") != 19:
        errors.append("transaction_cost_model_not_whole_universe")
    if manifest.get("label_write_after_score_required") is not True:
        errors.append("forward_label_score_order_not_enforced")
    if manifest.get("score_plane_read_only") is not True:
        errors.append("forward_label_score_plane_not_read_only")
    if manifest.get("score_plane_unchanged") is not True:
        errors.append("forward_label_score_plane_changed")
    if manifest.get("completed_partitions_rewritten") is not False:
        errors.append("forward_label_completed_partition_rewritten")
    if quality.get("score_created_before_label_violation_count") != 0:
        errors.append("forward_label_created_before_score")
    if quality.get("duplicate_label_count") != 0:
        errors.append("forward_label_duplicate_ids")
    if quality.get("duplicate_score_label_count") != 0:
        errors.append("forward_label_duplicate_score_ids")
    if quality.get("gross_and_net_retained") is not True:
        errors.append("forward_label_gross_net_not_retained")
    if quality.get("unsupported_liquidity_net_label_count") != 0:
        errors.append("unsupported_liquidity_not_fail_closed")
    if quality.get("unresolved_direction_assigned_net_return_count") != 0:
        errors.append("unresolved_direction_received_trade_pnl")
    if quality.get("directional_net_consistency_violation_count") != 0:
        errors.append("directional_net_return_inconsistent")
    if coverage.get("classification_ratio") != 1.0:
        errors.append("forward_label_score_inputs_not_fully_classified")
    if coverage.get("label_count") != len(labels) or not labels:
        errors.append("forward_label_count_invalid")
    if any(
        parse_timestamp(row.get("outcome_available_at"))
        <= parse_timestamp(row.get("decision_at"))
        for row in labels
    ):
        errors.append("forward_label_chronology_violation")
    overlap_independent_counts = Counter(
        row.get("overlap_group_id")
        for row in labels
        if row.get("independent_sample") is True
    )
    if any(count != 1 for count in overlap_independent_counts.values()):
        errors.append("forward_label_overlap_independence_invalid")
    if len(overlap_independent_counts) != quality.get("overlap_group_count"):
        errors.append("forward_label_overlap_group_missing_independent_sample")
    for partition in manifest.get("partitions", []):
        for path_key, sha_key in (
            ("dataset_path", "dataset_sha256"),
            ("missing_dataset_path", "missing_dataset_sha256"),
        ):
            path = ROOT / str(partition.get(path_key) or "")
            if not path.is_file():
                errors.append(
                    f"forward_label_partition_missing:{partition.get('partition_id')}:{path_key}"
                )
            elif file_sha256(path) != partition.get(sha_key):
                errors.append(
                    f"forward_label_partition_checksum_mismatch:{partition.get('partition_id')}:{path_key}"
                )
    for payload, prefix in (
        (manifest, "forward_label_manifest"),
        (costs, "transaction_cost_model"),
        (coverage, "label_coverage"),
        (quality, "label_quality"),
    ):
        errors.extend(validate_authority(payload.get("authority", {}), prefix=prefix))
    return unique_errors(errors)


def build_and_write_forward_labels(
    settings: Settings | None = None,
) -> tuple[dict[str, Any], dict[str, Any], list[str]]:
    runtime = runtime_dir(settings)
    store = AtomicArtifactStore(runtime)
    try:
        state = build_forward_label_state(settings)
        errors = validate_forward_label_state(state)
    except (OSError, TypeError, ValueError) as exc:
        generated_at = now_iso()
        state = {
            "manifest": {
                "schema_version": SCHEMA_VERSION,
                "artifact_type": "qadam_forward_label_manifest",
                "phase_id": PHASE_ID,
                "generated_at": generated_at,
                "status": "blocked",
                "partition_count": 0,
                "completed_partition_count": 0,
                "label_count": 0,
                "partitions": [],
                "paperops_watch_only_mode": True,
                "authority": authority_flags(),
            },
            "cost_model": {
                "schema_version": SCHEMA_VERSION,
                "artifact_type": "qadam_transaction_cost_model",
                "phase_id": PHASE_ID,
                "generated_at": generated_at,
                "status": "blocked",
                "instrument_count": 0,
                "instruments": [],
                "unsupported_liquidity_assumption_count": 0,
                "paperops_watch_only_mode": True,
                "authority": authority_flags(),
            },
            "coverage": {
                "schema_version": SCHEMA_VERSION,
                "artifact_type": "qadam_label_coverage",
                "phase_id": PHASE_ID,
                "generated_at": generated_at,
                "status": "blocked",
                "score_tape_row_count": 0,
                "label_count": 0,
                "classification_ratio": 0.0,
                "blockers": [str(exc)],
                "paperops_watch_only_mode": True,
                "authority": authority_flags(),
            },
            "quality": {
                "schema_version": SCHEMA_VERSION,
                "artifact_type": "qadam_label_quality_audit",
                "phase_id": PHASE_ID,
                "generated_at": generated_at,
                "status": "blocked",
                "score_created_before_label_violation_count": 0,
                "paperops_watch_only_mode": True,
                "authority": authority_flags(),
            },
            "labels": [],
            "missing": [],
        }
        errors = [str(exc)]
    store.write_json(MANIFEST_ARTIFACT, state["manifest"])
    store.write_json(COST_MODEL_ARTIFACT, state["cost_model"])
    store.write_json(COVERAGE_ARTIFACT, state["coverage"])
    store.write_json(QUALITY_ARTIFACT, state["quality"])
    empirical_complete = (
        state["manifest"].get("status") == "complete_with_classified_gaps"
    )
    checks = {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "qadam_forward_labels_checks",
        "phase_id": PHASE_ID,
        "generated_at": now_iso(),
        "status": "passed" if not errors and empirical_complete else "blocked",
        "acceptance_passed": not errors and empirical_complete,
        "implementation_ready": not errors,
        "empirical_labels_complete": empirical_complete,
        "score_tape_row_count": state["coverage"].get("score_tape_row_count", 0),
        "label_count": state["coverage"].get("label_count", 0),
        "gross_label_count": state["coverage"].get("gross_label_count", 0),
        "net_label_count": state["coverage"].get("net_label_count", 0),
        "cost_adjusted_counterfactual_label_count": state["coverage"].get(
            "cost_adjusted_counterfactual_label_count", 0
        ),
        "typed_missing_label_count": state["coverage"].get(
            "typed_missing_label_count", 0
        ),
        "classification_ratio": state["coverage"].get("classification_ratio", 0.0),
        "cost_model_instrument_count": state["cost_model"].get(
            "instrument_count", 0
        ),
        "unsupported_cost_model_count": state["cost_model"].get(
            "unsupported_liquidity_assumption_count", 0
        ),
        "score_label_order_violation_count": state["quality"].get(
            "score_created_before_label_violation_count", 0
        ),
        "score_plane_unchanged": state["manifest"].get(
            "score_plane_unchanged", False
        ),
        "overlap_group_count": state["quality"].get("overlap_group_count", 0),
        "independent_effective_sample_count": state["quality"].get(
            "independent_effective_sample_count", 0
        ),
        "validation_error_count": len(errors),
        "validation_errors": errors,
        "broker_write_count": 0,
        "paper_order_created_count": 0,
        "proof_credit_created_count": 0,
        "paper_growth_trial_calendar_advanced": False,
        "paperops_watch_only_mode": True,
        "authority": authority_flags(),
    }
    store.write_json(CHECK_ARTIFACT, checks)
    return state, checks, errors
