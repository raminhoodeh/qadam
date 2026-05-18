#!/usr/bin/env python3
"""Validate D7 TradingView alert intake without execution authority."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from orchestrator.config import Settings  # noqa: E402
from orchestrator.tradingview_alerts import (  # noqa: E402
    TRADINGVIEW_ALERT_SCHEMA_VERSION,
    TradingViewAlertStore,
    build_tradingview_alert_from_payload,
    d7_sample_tradingview_payload,
    ensure_d7_tradingview_alert_source,
    tradingview_alert_summary,
)

ALERT_REQUIRED_FIELDS = {
    "alert_id",
    "boundary",
    "chart_context",
    "dedupe_key",
    "direction",
    "execution_allowed",
    "indicator_state",
    "observed_at",
    "paper_order_allowed",
    "price",
    "received_at",
    "schema_version",
    "setup_type",
    "source_type",
    "status",
    "symbol",
    "timeframe",
    "trade_candidate_created",
    "trigger",
}

FORBIDDEN_PERSISTED_FIELDS = {
    "qadam_receiver_key",
    "receiver_key",
    "webhook_secret",
    "secret",
    "token",
    "raw_payload",
}


def main() -> int:
    settings = Settings.from_env()
    result = ensure_d7_tradingview_alert_source(settings)
    store = TradingViewAlertStore(settings=settings)
    alerts = store.read_alerts()
    before_duplicate_count = len(alerts)
    duplicate_result = store.add_alert(build_tradingview_alert_from_payload(d7_sample_tradingview_payload()))
    alerts_after_duplicate = store.read_alerts()
    summary = tradingview_alert_summary(settings)

    try:
        build_tradingview_alert_from_payload(
            d7_sample_tradingview_payload() | {"qadam_receiver_key": "wrong"},
            expected_receiver_key="expected",
        )
    except ValueError:
        receiver_auth_failed_closed = True
    else:
        receiver_auth_failed_closed = False

    print("tradingview_alert_status=" + summary["status"])
    print(f"tradingview_alert_created={result['created']}")
    print(f"tradingview_alert_duplicate_protection={result['duplicate_protection']}")
    print(f"tradingview_alert_direct_duplicate_status={duplicate_result['status']}")
    print(f"tradingview_alert_count={len(alerts)}")
    print(f"tradingview_alert_execution_allowed_count={summary['execution_allowed_count']}")
    print(f"tradingview_alert_paper_order_allowed_count={summary['paper_order_allowed_count']}")
    print(f"tradingview_alert_trade_candidate_created_count={summary['trade_candidate_created_count']}")
    print(f"tradingview_alert_receiver_auth_failed_closed={receiver_auth_failed_closed}")
    print("tradingview_alert_receiver_status=" + summary["receiver_status"])
    print("tradingview_alert_boundary=" + summary["boundary"])

    if summary["status"] != "ok":
        print("tradingview_alert_store_not_ok=true")
        return 1
    if len(alerts) < 1:
        print("tradingview_alert_missing_sample=true")
        return 1
    if result["duplicate_protection"] != "duplicate_ignored":
        print("tradingview_alert_duplicate_not_blocked=true")
        return 1
    if duplicate_result["status"] != "duplicate_ignored":
        print("tradingview_alert_direct_duplicate_not_blocked=true")
        return 1
    if len(alerts_after_duplicate) != before_duplicate_count:
        print("tradingview_alert_duplicate_changed_count=true")
        return 1
    if summary["schema_version"] != TRADINGVIEW_ALERT_SCHEMA_VERSION:
        print("tradingview_alert_schema_version_mismatch=true")
        return 1
    if summary["receiver_status"] != "local_contract_only":
        print("tradingview_alert_receiver_status_mismatch=true")
        return 1
    if summary["duplicate_protection"] != "dedupe_key_sha256":
        print("tradingview_alert_duplicate_protection_mismatch=true")
        return 1
    if "observed signals only" not in summary["boundary"]:
        print("tradingview_alert_boundary_weak=true")
        return 1
    if summary["execution_allowed_count"] != 0:
        print("tradingview_alert_execution_allowed_not_zero=true")
        return 1
    if summary["paper_order_allowed_count"] != 0:
        print("tradingview_alert_paper_order_allowed_not_zero=true")
        return 1
    if summary["trade_candidate_created_count"] != 0:
        print("tradingview_alert_created_trade_candidate=true")
        return 1
    if not receiver_auth_failed_closed:
        print("tradingview_alert_receiver_auth_not_fail_closed=true")
        return 1
    for alert in alerts:
        payload = alert.to_dict()
        missing_fields = sorted(ALERT_REQUIRED_FIELDS - set(payload))
        if missing_fields:
            print(f"tradingview_alert_fields_missing={alert.alert_id}:{','.join(missing_fields)}")
            return 1
        forbidden_fields = sorted(FORBIDDEN_PERSISTED_FIELDS & set(payload))
        if forbidden_fields:
            print(f"tradingview_alert_forbidden_fields_persisted={alert.alert_id}:{','.join(forbidden_fields)}")
            return 1
        if alert.status != "observed_signal":
            print(f"tradingview_alert_wrong_status={alert.alert_id}")
            return 1
        if alert.source_type != "tradingview_paid_alert":
            print(f"tradingview_alert_wrong_source_type={alert.alert_id}")
            return 1
        if alert.execution_allowed or alert.paper_order_allowed or alert.trade_candidate_created:
            print(f"tradingview_alert_authority_leak={alert.alert_id}")
            return 1
        if len(alert.dedupe_key) != 64:
            print(f"tradingview_alert_dedupe_key_not_sha256={alert.alert_id}")
            return 1
        if not alert.indicator_state:
            print(f"tradingview_alert_indicator_state_missing={alert.alert_id}")
            return 1
        if "cannot create a trade candidate, paper order, or broker action" not in alert.boundary:
            print(f"tradingview_alert_record_boundary_weak={alert.alert_id}")
            return 1

    print("tradingview_alert_check=ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
