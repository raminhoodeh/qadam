#!/usr/bin/env python3
"""Validate the supplemental Yahoo Finance market-confirmation adapter."""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from orchestrator.yahoo_finance_adapter import (  # noqa: E402
    fetch_yahoo_finance_live,
    fetch_yahoo_finance_sample,
    yahoo_finance_adapter_status,
)
from world_monitor.source_registry import EXPECTED_SOURCE_COUNT  # noqa: E402

SECRET_LIKE_PATTERNS = (
    re.compile(r"\d{6,}:[A-Za-z0-9_-]{20,}"),
    re.compile(r"\bghp_[A-Za-z0-9]{20,}\b"),
    re.compile(r"\bvcp_[A-Za-z0-9]{20,}\b"),
    re.compile(r"\bAIza[0-9A-Za-z_-]{20,}\b"),
    re.compile(r"\bsb_secret_[0-9A-Za-z_-]{12,}\b"),
    re.compile(r"\b[A-Za-z0-9_-]{40,}\.[A-Za-z0-9_-]{20,}\.[A-Za-z0-9_-]{20,}\b"),
)


def _arg_value(prefix: str) -> str | None:
    for arg in sys.argv:
        if arg.startswith(prefix):
            return arg.split("=", 1)[1]
    return None


def _symbols() -> tuple[str, ...] | None:
    raw = _arg_value("--symbols=")
    if not raw:
        return None
    return tuple(symbol.strip().upper() for symbol in raw.split(",") if symbol.strip())


def _contains_secret_like_value(payload: Any) -> bool:
    encoded = json.dumps(payload, sort_keys=True, default=str)
    return any(pattern.search(encoded) for pattern in SECRET_LIKE_PATTERNS)


def main() -> int:
    live = "--live" in sys.argv
    period = _arg_value("--period=") or "1mo"
    interval = _arg_value("--interval=") or "1d"
    status = yahoo_finance_adapter_status()

    try:
        envelope = (
            fetch_yahoo_finance_live(symbols=_symbols(), period=period, interval=interval)
            if live
            else fetch_yahoo_finance_sample(symbols=_symbols())
        )
    except Exception as exc:  # noqa: BLE001 - check should make failures explicit
        print("yahoo_finance_adapter_status=failed")
        print(f"yahoo_finance_adapter_error_type={exc.__class__.__name__}")
        print(f"yahoo_finance_adapter_error={exc!r}")
        return 1

    events = envelope.get("events", [])
    event_count = len(events) if isinstance(events, list) else 0
    errors: list[str] = []
    if status["canonical_source_count"] != EXPECTED_SOURCE_COUNT:
        errors.append("canonical_source_count_changed")
    if not live and event_count == 0:
        errors.append("sample_event_count_empty")
    if _contains_secret_like_value(envelope) or _contains_secret_like_value(status):
        errors.append("secret_like_value_in_output")

    print("yahoo_finance_adapter_status=" + ("ok" if not errors else "error"))
    print(f"yahoo_finance_adapter_classification={status['classification']}")
    print(f"yahoo_finance_adapter_mode={'live_read_only' if live else 'sample'}")
    print(f"yahoo_finance_adapter_source={envelope.get('source')}")
    print(f"yahoo_finance_adapter_event_count={event_count}")
    print(f"yahoo_finance_adapter_degraded={envelope.get('degraded')}")
    print(f"yahoo_finance_adapter_degraded_reason={envelope.get('degraded_reason')}")
    print(f"yahoo_finance_adapter_enabled={status['enabled']}")
    print(f"yahoo_finance_adapter_local_checkout_exists={status['local_checkout_exists']}")
    print(f"yahoo_finance_adapter_dependency_importable={status['dependency_importable']}")
    print(f"yahoo_finance_adapter_missing_dependency={status['missing_dependency']}")
    print(f"yahoo_finance_adapter_request_budget_per_run={status['request_budget_per_run']}")
    print(f"yahoo_finance_adapter_symbol_allowlist_count={status['symbol_allowlist_count']}")
    print(f"yahoo_finance_adapter_canonical_source_count={status['canonical_source_count']}")
    print(f"yahoo_finance_adapter_raw_archive_path={envelope.get('raw_archive_path')}")
    print("yahoo_finance_adapter_execution_allowed=False")
    print("yahoo_finance_adapter_paper_order_allowed=False")
    print("yahoo_finance_adapter_broker_write_allowed=False")
    print("yahoo_finance_adapter_boundary=Read-only supplemental market confirmation; no signal, order, broker, fill, reconciliation, live-capital, or quantum authority.")
    for error in errors:
        print(f"yahoo_finance_adapter_error={error}")

    if errors:
        return 1
    print("yahoo_finance_adapter_check=ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
