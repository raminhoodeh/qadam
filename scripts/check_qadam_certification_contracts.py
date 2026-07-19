#!/usr/bin/env python3
"""Validate provider, point-in-time, and backtest inputs consumed by OR-19."""

from __future__ import annotations

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from orchestrator.qadam_certification_contracts import (  # noqa: E402
    run_certification_contract_audit,
)


def main() -> int:
    audit, compatibility = run_certification_contract_audit()
    print(f"certification_contract_status={audit.get('status')}")
    print(
        "certification_provider_terminal="
        f"{audit.get('provider_terminal_state', {}).get('passed')}"
    )
    print(
        "certification_backtest_fold_result_count="
        f"{compatibility.get('resolved_fold_count')}"
    )
    print(
        "certification_negative_control_executed_count="
        f"{compatibility.get('negative_control_executed_count')}"
    )
    print(
        "certification_negative_control_false_positive_count="
        f"{compatibility.get('negative_control_statistically_positive_count')}"
    )
    print(f"certification_contract_error_count={audit.get('validation_error_count')}")
    return 0 if audit.get("status") == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
