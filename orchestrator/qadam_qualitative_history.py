"""Point-in-time price alignment and forward-label maturation for claims."""

from __future__ import annotations

from bisect import bisect_left
from collections import Counter
from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
from typing import Any

from orchestrator.config import Settings
from orchestrator.qadam_canonical_contracts import AtomicArtifactStore
from orchestrator.qadam_qualitative_common import (
    QUALITATIVE_CLAIMS_ARTIFACT,
    QUALITATIVE_FORWARD_WINDOWS_ARTIFACT,
    QUALITATIVE_HISTORY_ARTIFACT,
    QUALITATIVE_LABELS_ARTIFACT,
    now_iso,
    parse_iso,
    public_authority,
    read_jsonl,
    repo_root,
    research_root,
    runtime_dir,
    stable_id,
)

HORIZONS = {"1d": 1, "3d": 3, "5d": 5, "20d": 20, "60d": 60}


def _bars(symbol: str) -> list[dict[str, Any]]:
    root = repo_root() / "data" / "research" / "prices" / f"symbol={symbol.replace('/', '_')}" / "interval=1d"
    rows: dict[str, dict[str, Any]] = {}
    for path in sorted(root.glob("year=*/bars.jsonl")):
        for record in read_jsonl(path):
            observed = parse_iso(record.get("observed_at"))
            try:
                close = float(record.get("close"))
            except (TypeError, ValueError):
                continue
            if observed is None or close <= 0:
                continue
            available = observed + timedelta(days=1)
            rows[observed.isoformat()] = {
                "observed_at": observed,
                "available_at": available,
                "close": close,
                "volume": record.get("volume"),
                "provider": record.get("provider") or "provider_price_lake",
                "partition": str(path.relative_to(repo_root())),
            }
    return sorted(rows.values(), key=lambda row: row["available_at"])


def build_qualitative_history(
    settings: Settings | None = None,
) -> tuple[dict[str, Any], list[str]]:
    runtime = runtime_dir(settings)
    claims = read_jsonl(runtime / QUALITATIVE_CLAIMS_ARTIFACT)
    symbols = sorted({str(symbol) for claim in claims for symbol in claim.get("instrument_hypotheses") or []})
    bars_by_symbol = {symbol: _bars(symbol) for symbol in symbols}
    availability = {symbol: [row["available_at"] for row in bars] for symbol, bars in bars_by_symbol.items()}
    labels: list[dict[str, Any]] = []
    windows: list[dict[str, Any]] = []
    missing = Counter()
    errors: list[str] = []
    generated_at = now_iso()

    for claim in claims:
        decision_time = parse_iso(claim.get("availability_time"))
        for symbol in claim.get("instrument_hypotheses") or []:
            symbol = str(symbol)
            bars = bars_by_symbol.get(symbol, [])
            status = {
                "window_id": stable_id("qualitative-window", claim.get("claim_id"), symbol),
                "claim_id": claim.get("claim_id"),
                "instrument_symbol": symbol,
                "decision_time": claim.get("availability_time"),
                "horizons": {},
                "point_in_time_safe": True,
                "paper_growth_trial_advanced": False,
                "proof_credit_created": False,
                "authority": public_authority(),
            }
            if decision_time is None:
                status["state"] = "missing"
                status["reason"] = "claim_availability_time_invalid"
                missing[status["reason"]] += 1
                windows.append(status)
                continue
            if not bars:
                status["state"] = "missing"
                status["reason"] = "instrument_price_history_unavailable"
                missing[status["reason"]] += 1
                windows.append(status)
                continue
            base_index = bisect_left(availability[symbol], decision_time.astimezone(timezone.utc))
            if base_index >= len(bars):
                status["state"] = "pending"
                status["reason"] = "first_tradeable_bar_not_yet_available"
                missing[status["reason"]] += 1
                windows.append(status)
                continue
            baseline = bars[base_index]
            complete = 0
            for name, offset in HORIZONS.items():
                target_index = base_index + offset
                if target_index >= len(bars):
                    status["horizons"][name] = {"state": "pending", "reason": "forward_market_time_not_mature"}
                    missing["forward_market_time_not_mature"] += 1
                    continue
                target = bars[target_index]
                value = (target["close"] / baseline["close"]) - 1.0
                label = {
                    "schema_version": "qadam_qualitative_label.v1",
                    "artifact_type": "qadam_qualitative_forward_label",
                    "label_id": stable_id("qualitative-label", claim.get("claim_id"), symbol, name),
                    "claim_id": claim.get("claim_id"),
                    "claim_type": claim.get("claim_type"),
                    "claim_direction": claim.get("direction"),
                    "independence_cluster": claim.get("independence_cluster"),
                    "instrument_symbol": symbol,
                    "horizon": name,
                    "decision_time": claim.get("availability_time"),
                    "baseline_observed_at": baseline["observed_at"].isoformat(),
                    "baseline_available_at": baseline["available_at"].isoformat(),
                    "baseline_close": baseline["close"],
                    "outcome_observed_at": target["observed_at"].isoformat(),
                    "outcome_available_at": target["available_at"].isoformat(),
                    "forward_return": value,
                    "market_data_provider": baseline["provider"],
                    "source_partition": baseline["partition"],
                    "point_in_time_safe": baseline["available_at"] >= decision_time,
                    "classification": "forward" if decision_time.date() >= datetime.now(timezone.utc).date() - timedelta(days=90) else "historical",
                    "negative_control": False,
                    "authority": public_authority(),
                }
                labels.append(label)
                status["horizons"][name] = {"state": "mature", "label_id": label["label_id"]}
                complete += 1
            status["state"] = "mature" if complete == len(HORIZONS) else "partially_mature" if complete else "pending"
            status["reason"] = None if complete else "forward_market_time_not_mature"
            windows.append(status)

    feature_root = research_root() / "features"
    feature_root.mkdir(parents=True, exist_ok=True)
    (feature_root / "qualitative_labels.jsonl").write_text(
        "".join(json.dumps(row, sort_keys=True) + "\n" for row in labels),
        encoding="utf-8",
    )
    store = AtomicArtifactStore(runtime)
    store.write_jsonl(QUALITATIVE_LABELS_ARTIFACT, labels)
    forward = {
        "schema_version": "qadam_qualitative_forward_window_status.v1",
        "artifact_type": "qadam_qualitative_forward_window_status",
        "generated_at": generated_at,
        "status": "ready" if windows else "ready_no_claims",
        "window_count": len(windows),
        "mature_window_count": sum(row.get("state") == "mature" for row in windows),
        "partially_mature_window_count": sum(row.get("state") == "partially_mature" for row in windows),
        "pending_window_count": sum(row.get("state") == "pending" for row in windows),
        "missing_window_count": sum(row.get("state") == "missing" for row in windows),
        "missing_reason_counts": dict(sorted(missing.items())),
        "windows": windows,
        "authority": public_authority(),
    }
    coverage = {
        "schema_version": "qadam_qualitative_history_coverage.v1",
        "artifact_type": "qadam_qualitative_history_coverage",
        "generated_at": generated_at,
        "status": "ready_with_pending_forward_time" if forward["pending_window_count"] else "ready",
        "claim_count": len(claims),
        "instrument_count": len(symbols),
        "price_bar_counts": {symbol: len(rows) for symbol, rows in bars_by_symbol.items()},
        "label_count": len(labels),
        "leakage_violation_count": sum(row.get("point_in_time_safe") is not True for row in labels),
        "restart_idempotent": True,
        "paper_growth_trial_advanced": False,
        "proof_credit_created": False,
        "validation_errors": errors,
        "authority": public_authority(),
    }
    store.write_json(QUALITATIVE_FORWARD_WINDOWS_ARTIFACT, forward)
    store.write_json(QUALITATIVE_HISTORY_ARTIFACT, coverage)
    return {"coverage": coverage, "forward": forward, "labels": labels}, errors


__all__ = ["build_qualitative_history", "HORIZONS"]
