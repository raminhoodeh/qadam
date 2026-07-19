#!/usr/bin/env python3
"""Plan or run bounded Unusual Whales historical research capture.

The command is network-disabled by default. A provider request requires all of
the following: the research adapter is enabled, a locally configured token is
present, provider terms have been reviewed, access has not expired, and the
operator passes ``--allow-network``.
"""

from __future__ import annotations

import argparse
from dataclasses import replace
from datetime import date, datetime, timedelta, timezone
import hashlib
import json
from pathlib import Path
import sys
from typing import Any, Iterable
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from orchestrator.config import Settings  # noqa: E402
from orchestrator.qadam_canonical_contracts import AtomicArtifactStore  # noqa: E402
from orchestrator.qadam_operator_ready_common import authority_flags, runtime_dir  # noqa: E402
from orchestrator.unusual_whales_adapter import (  # noqa: E402
    ENDPOINTS,
    UnusualWhalesResearchAdapter,
    UnusualWhalesResearchConfig,
    refresh_unusual_whales_public_artifacts,
)

PLAN_ARTIFACT = "unusual_whales_capture_plan.json"
RUN_SUMMARY_ARTIFACT = "unusual_whales_capture_run_summary.json"
DEFAULT_ENDPOINTS = (
    "market_tide",
    "flow_alerts",
    "darkpool_ticker",
    "options_volume",
)


def _parse_date(value: str) -> date:
    try:
        return date.fromisoformat(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("dates must use YYYY-MM-DD") from exc


def _dates(start: date, end: date) -> Iterable[date]:
    current = start
    while current <= end:
        if current.weekday() < 5:
            yield current
        current += timedelta(days=1)


def _task_id(endpoint: str, symbol: str | None, params: dict[str, Any]) -> str:
    fingerprint = json.dumps(
        {"endpoint": endpoint, "symbol": symbol, "params": params},
        sort_keys=True,
        separators=(",", ":"),
    )
    return f"uw-task:{hashlib.sha256(fingerprint.encode('utf-8')).hexdigest()[:20]}"


def build_capture_tasks(
    *,
    endpoints: tuple[str, ...],
    symbols: tuple[str, ...],
    start_date: date,
    end_date: date,
) -> list[dict[str, Any]]:
    tasks: list[dict[str, Any]] = []
    trading_dates = list(_dates(start_date, end_date))
    for endpoint in endpoints:
        if endpoint == "market_tide":
            for active_date in trading_dates:
                params = {"date": active_date.isoformat(), "interval_5m": True}
                tasks.append(
                    {
                        "task_id": _task_id(endpoint, None, params),
                        "endpoint": endpoint,
                        "symbol": None,
                        "params": params,
                        "pagination": False,
                    }
                )
        elif endpoint == "flow_alerts":
            joined_symbols = ",".join(symbols)
            for active_date in trading_dates:
                params = {
                    "ticker_symbol": joined_symbols,
                    "unusual": True,
                    "newer_than": active_date.isoformat(),
                    "older_than": (active_date + timedelta(days=1)).isoformat(),
                    "limit": 200,
                }
                tasks.append(
                    {
                        "task_id": _task_id(endpoint, None, params),
                        "endpoint": endpoint,
                        "symbol": None,
                        "params": params,
                        "pagination": True,
                    }
                )
        elif endpoint == "darkpool_ticker":
            for active_date in trading_dates:
                for symbol in symbols:
                    params = {
                        "date": active_date.isoformat(),
                        "limit": 500,
                        "order": "desc",
                        "order_by": "executed_at",
                    }
                    tasks.append(
                        {
                            "task_id": _task_id(endpoint, symbol, params),
                            "endpoint": endpoint,
                            "symbol": symbol,
                            "params": params,
                            "pagination": True,
                        }
                    )
        elif endpoint == "options_volume":
            for symbol in symbols:
                params = {"limit": 500}
                tasks.append(
                    {
                        "task_id": _task_id(endpoint, symbol, params),
                        "endpoint": endpoint,
                        "symbol": symbol,
                        "params": params,
                        "pagination": False,
                    }
                )
        elif endpoint in {"net_premium_ticks", "greeks", "spot_gex", "interpolated_iv"}:
            for active_date in trading_dates:
                for symbol in symbols:
                    params = {"date": active_date.isoformat()}
                    tasks.append(
                        {
                            "task_id": _task_id(endpoint, symbol, params),
                            "endpoint": endpoint,
                            "symbol": symbol,
                            "params": params,
                            "pagination": False,
                        }
                    )
        else:
            raise ValueError(f"capture_planner_not_implemented:{endpoint}")
    return tasks


def _next_older_than(result: dict[str, Any]) -> str | None:
    timestamps = [
        str(record.get("event_at"))
        for record in result.get("records", [])
        if record.get("event_at")
    ]
    return min(timestamps) if timestamps else None


def _capture_task(
    adapter: UnusualWhalesResearchAdapter,
    task: dict[str, Any],
    *,
    request_budget_remaining: int,
    allow_network: bool,
    retain_raw: bool,
    timeout_seconds: float,
) -> tuple[list[dict[str, Any]], int]:
    results: list[dict[str, Any]] = []
    params = dict(task["params"])
    previous_cursor: str | None = None
    maximum_limit = ENDPOINTS[task["endpoint"]].maximum_limit
    while request_budget_remaining > 0:
        result = adapter.capture(
            task["endpoint"],
            params=params,
            symbol=task.get("symbol"),
            allow_network=allow_network,
            provider_terms_reviewed=True,
            retain_raw=retain_raw,
            timeout_seconds=timeout_seconds,
        )
        results.append(
            {
                "task_id": task["task_id"],
                "endpoint": task["endpoint"],
                "symbol": task.get("symbol"),
                "status": result.get("status"),
                "reason": result.get("reason"),
                "capture_id": result.get("capture_id"),
                "normalized_record_count": int(result.get("normalized_record_count") or 0),
                "backtest_eligible_record_count": int(
                    result.get("backtest_eligible_record_count") or 0
                ),
            }
        )
        if result.get("network_called") is True:
            request_budget_remaining -= 1
        if result.get("status") != "captured" or not task.get("pagination"):
            break
        record_count = int(result.get("normalized_record_count") or 0)
        if maximum_limit is None or record_count < maximum_limit:
            break
        cursor = _next_older_than(result)
        if not cursor or cursor == previous_cursor:
            break
        previous_cursor = cursor
        params["older_than"] = cursor
    return results, request_budget_remaining


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Prepare or run read-only Unusual Whales historical feature capture."
    )
    parser.add_argument("--allow-network", action="store_true")
    parser.add_argument("--provider-terms-reviewed", action="store_true")
    parser.add_argument("--retain-raw", action="store_true")
    parser.add_argument("--start-date", type=_parse_date)
    parser.add_argument("--end-date", type=_parse_date)
    parser.add_argument("--symbol", action="append", default=[])
    parser.add_argument("--endpoint", action="append", choices=sorted(ENDPOINTS), default=[])
    parser.add_argument("--max-requests", type=int)
    parser.add_argument("--timeout-seconds", type=float, default=20.0)
    return parser


def main() -> int:
    args = _parser().parse_args()
    settings = Settings.from_env()
    configured = UnusualWhalesResearchConfig.from_env()
    now = datetime.now(timezone.utc)
    local_today = now.astimezone(ZoneInfo(configured.timezone_name)).date()
    start_date = args.start_date or local_today
    end_date = args.end_date or start_date
    if start_date > end_date:
        raise SystemExit("start_date_must_not_follow_end_date")
    if end_date > local_today:
        raise SystemExit("future_capture_dates_are_not_allowed")
    if (end_date - start_date).days > 3_660:
        raise SystemExit("capture_date_range_exceeds_ten_year_guard")

    symbols = tuple(
        dict.fromkeys(symbol.strip().upper() for symbol in args.symbol if symbol.strip())
    ) or configured.symbol_allowlist
    unknown_symbols = sorted(set(symbols) - set(configured.symbol_allowlist))
    if unknown_symbols:
        raise SystemExit(f"symbols_not_allowlisted:{','.join(unknown_symbols)}")
    endpoints = tuple(dict.fromkeys(args.endpoint)) or DEFAULT_ENDPOINTS
    if "technical_indicator" in endpoints:
        raise SystemExit("technical_indicator_requires_a_separate_registered_function_plan")

    active_config = replace(
        configured,
        provider_terms_reviewed=(
            configured.provider_terms_reviewed or args.provider_terms_reviewed
        ),
    )
    tasks = build_capture_tasks(
        endpoints=endpoints,
        symbols=symbols,
        start_date=start_date,
        end_date=end_date,
    )
    request_budget = min(
        active_config.run_request_budget,
        args.max_requests if args.max_requests is not None else active_config.run_request_budget,
    )
    if request_budget < 1:
        raise SystemExit("max_requests_must_be_positive")

    store = AtomicArtifactStore(runtime_dir(settings))
    generated_at = now.isoformat()
    plan = {
        "schema_version": "unusual_whales_capture_plan.v1",
        "artifact_type": "unusual_whales_capture_plan",
        "generated_at": generated_at,
        "status": "network_authorized" if args.allow_network else "planned_network_disabled",
        "start_date": start_date.isoformat(),
        "end_date": end_date.isoformat(),
        "symbols": list(symbols),
        "endpoints": list(endpoints),
        "planned_task_count": len(tasks),
        "request_budget": request_budget,
        "access_expires_on": active_config.access_expires_on.isoformat(),
        "historical_research_only": True,
        "secret_values_recorded": False,
        "tasks": tasks,
        "authority": authority_flags(),
    }
    store.write_json(PLAN_ARTIFACT, plan)

    adapter = UnusualWhalesResearchAdapter(
        settings=settings,
        config=active_config,
        now_provider=lambda: now,
    )
    results: list[dict[str, Any]] = []
    remaining = request_budget
    if args.allow_network:
        if not active_config.provider_terms_reviewed:
            raise SystemExit("provider_terms_review_required")
        for task in tasks:
            if remaining <= 0:
                break
            task_results, remaining = _capture_task(
                adapter,
                task,
                request_budget_remaining=remaining,
                allow_network=True,
                retain_raw=args.retain_raw,
                timeout_seconds=args.timeout_seconds,
            )
            results.extend(task_results)
            last_reason = str(task_results[-1].get("reason") or "") if task_results else ""
            if last_reason in {
                "expired_archive_only",
                "ready_disabled",
                "ready_missing_credential",
                "provider_terms_review_required",
                "credential_expired_or_denied",
                "rate_limited",
            } or last_reason.startswith("provider_transport_error"):
                break

    status, feature_manifest = refresh_unusual_whales_public_artifacts(
        settings,
        config=active_config,
        now=now,
    )
    blocked_count = sum(record.get("status") == "blocked" for record in results)
    captured_count = sum(record.get("status") == "captured" for record in results)
    summary = {
        "schema_version": "unusual_whales_capture_run_summary.v1",
        "artifact_type": "unusual_whales_capture_run_summary",
        "generated_at": generated_at,
        "status": (
            "planned_network_disabled"
            if not args.allow_network
            else ("completed" if not blocked_count else "completed_with_provider_blocks")
        ),
        "network_allowed": bool(args.allow_network),
        "planned_task_count": len(tasks),
        "processed_request_count": request_budget - remaining,
        "captured_request_count": captured_count,
        "blocked_request_count": blocked_count,
        "unprocessed_task_count": max(len(tasks) - len({row["task_id"] for row in results}), 0),
        "normalized_record_count": feature_manifest["normalized_record_count"],
        "backtest_eligible_record_count": feature_manifest[
            "backtest_eligible_record_count"
        ],
        "coverage_start": feature_manifest["coverage_start"],
        "coverage_end": feature_manifest["coverage_end"],
        "access_state": status["status"],
        "access_expires_on": status["access_expires_on"],
        "credential_state": status["credential_state"],
        "provider_terms_reviewed": status["provider_terms_reviewed"],
        "historical_research_only": True,
        "secret_values_recorded": False,
        "source_quorum_allowed": False,
        "execution_allowed": False,
        "proof_credit_allowed": False,
        "results": results,
        "authority": authority_flags(),
    }
    store.write_json(RUN_SUMMARY_ARTIFACT, summary)
    print(json.dumps({key: value for key, value in summary.items() if key != "results"}, sort_keys=True))
    return 1 if args.allow_network and blocked_count else 0


if __name__ == "__main__":
    raise SystemExit(main())
