#!/usr/bin/env python3
"""Validate that public dashboard portfolio values have one source of truth."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from orchestrator.config import Settings


def _read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return payload if isinstance(payload, dict) else {}


def _money(value: Any) -> float | None:
    if value is None or isinstance(value, bool):
        return None
    try:
        return round(float(value), 2)
    except (TypeError, ValueError):
        return None


def _require(condition: bool, errors: list[str], code: str) -> None:
    if not condition:
        errors.append(code)


def _value_delta(left: Any, right: Any) -> float | None:
    left_value = _money(left)
    right_value = _money(right)
    if left_value is None or right_value is None:
        return None
    return round(left_value - right_value, 2)


def validate_portfolio(status: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    portfolio = status.get("dashboard_portfolio", {})
    capital = status.get("capital", {})
    mission = status.get("mission_control", {}).get("portfolio", {})
    qsase = status.get("qsase_dashboard", {})
    qsase_portfolio = qsase.get("dashboard_portfolio", {})
    qsase_sections = qsase.get("sections", {})
    qsase_value_section = qsase_sections.get("portfolio_value", {})
    qsase_current_section = qsase_sections.get("current_portfolio", {})

    _require(portfolio.get("artifact_type") == "dashboard_portfolio_canonical_contract", errors, "dashboard_portfolio_missing")
    _require(portfolio.get("read_only") is True, errors, "dashboard_portfolio_not_read_only")
    _require(portfolio.get("live_capital_enabled") is False, errors, "dashboard_portfolio_live_capital_enabled")
    _require(portfolio.get("broker_write_allowed") is False, errors, "dashboard_portfolio_broker_write_allowed")
    _require(portfolio.get("portfolio_consistency", {}).get("status") == "ok", errors, "dashboard_portfolio_consistency_not_ok")

    canonical_value = portfolio.get("current_value_gbp")
    capital_value = capital.get("equity_gbp") or capital.get("current_balance_gbp")
    mission_value = mission.get("current_balance_gbp") or mission.get("balance_gbp")
    qsase_value = qsase_portfolio.get("current_value_gbp") or qsase_value_section.get("current_value_gbp")
    chart_value = (
        portfolio.get("latest_curve_point", {}).get("portfolio_value")
        or portfolio.get("latest_curve_point", {}).get("equity_gbp")
        or qsase_value_section.get("latest_value")
    )

    comparisons = {
        "capital_value_mismatch": _value_delta(canonical_value, capital_value),
        "mission_value_mismatch": _value_delta(canonical_value, mission_value),
        "qsase_value_mismatch": _value_delta(canonical_value, qsase_value),
        "chart_value_mismatch": _value_delta(canonical_value, chart_value),
    }
    for code, delta in comparisons.items():
        if delta is None or abs(delta) > 0.01:
            errors.append(code)

    canonical_positions = int(portfolio.get("open_position_count") or 0)
    capital_positions = int(capital.get("open_position_count") or len(capital.get("open_positions") or []) or 0)
    mission_positions = int(mission.get("open_position_count") or len(mission.get("open_positions") or []) or 0)
    qsase_positions = int(qsase_portfolio.get("open_position_count") or qsase_current_section.get("position_count") or 0)
    position_rows = len(portfolio.get("positions") or [])
    if canonical_positions != capital_positions:
        errors.append("capital_position_count_mismatch")
    if canonical_positions != mission_positions:
        errors.append("mission_position_count_mismatch")
    if canonical_positions != qsase_positions:
        errors.append("qsase_position_count_mismatch")
    if canonical_positions != position_rows:
        errors.append("dashboard_position_row_count_mismatch")

    realized = _money(portfolio.get("realized_pnl_gbp")) or 0.0
    unrealized = _money(portfolio.get("unrealized_pnl_gbp")) or 0.0
    total = _money(portfolio.get("total_pnl_gbp"))
    if total is None or abs(round((realized + unrealized) - total, 2)) > 0.01:
        errors.append("dashboard_total_pnl_mismatch")

    if qsase_value_section.get("line_graph_available") is True and qsase_value_section.get("current_value_gbp") is None:
        errors.append("qsase_graph_available_without_current_value")

    for freshness_key in ("broker_mirror_freshness", "public_snapshot_freshness"):
        freshness = portfolio.get(freshness_key, {})
        if not isinstance(freshness, dict) or freshness.get("status") not in {"fresh", "stale"}:
            errors.append(f"{freshness_key}_missing")

    return sorted(set(errors))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--status-path",
        default=None,
        help="Status JSON to validate. Defaults to data/runtime/cockpit-status.json.",
    )
    args = parser.parse_args()
    settings = Settings.from_env()
    status_path = Path(args.status_path) if args.status_path else Path(settings.runtime_dir) / "cockpit-status.json"
    if not status_path.is_absolute():
        status_path = ROOT / status_path
    status = _read_json(status_path)
    errors = validate_portfolio(status)
    portfolio = status.get("dashboard_portfolio", {})
    consistency = portfolio.get("portfolio_consistency", {})
    print(f"dashboard_portfolio_status={portfolio.get('status')}")
    print(f"dashboard_portfolio_generated_at={portfolio.get('generated_at')}")
    print(f"dashboard_portfolio_value={portfolio.get('current_value_gbp')}")
    print(f"dashboard_portfolio_latest_chart_value={consistency.get('latest_curve_value')}")
    print(f"dashboard_portfolio_value_delta={consistency.get('value_delta')}")
    print(f"dashboard_portfolio_open_position_count={portfolio.get('open_position_count')}")
    print(f"dashboard_portfolio_row_count={len(portfolio.get('positions') or [])}")
    print(f"dashboard_portfolio_consistency={consistency.get('status')}")
    if errors:
        for error in errors:
            print(f"error={error}")
        return 1
    print("dashboard_portfolio_consistency_check=ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
