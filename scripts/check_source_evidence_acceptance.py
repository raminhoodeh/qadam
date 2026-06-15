#!/usr/bin/env python3
"""Aggregate non-dashboard acceptance gate for Qadam source/evidence work.

This intentionally excludes the Stage 7 dashboard simplification plan. It
validates the source-registry cleanup, credential-bound adapters, provider
decisions, TradingView MCP, Bookmap local bridge, evidence packet
normalization, durable evidence runtime, and cockpit export contract.
"""

from __future__ import annotations

import json
import subprocess
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
REPORT_PATH = ROOT / "data/runtime/source_evidence_acceptance.json"


@dataclass(frozen=True)
class CheckCommand:
    key: str
    script: str
    success_key: str
    success_value: str = "ok"


CHECKS: tuple[CheckCommand, ...] = (
    CheckCommand("source_registry", "scripts/check_source_registry_blockers.py", "source_registry_blocker_check"),
    CheckCommand("phase1_data_spine", "scripts/check_phase1_data_spine.py", "phase1_data_spine_check"),
    CheckCommand(
        "phase1_live_source_hardening",
        "scripts/check_phase1_live_source_hardening.py",
        "phase1_live_source_hardening_check",
    ),
    CheckCommand(
        "credential_bound_adapters",
        "scripts/check_credential_bound_adapters.py",
        "credential_bound_adapter_check",
    ),
    CheckCommand("provider_decision_pass", "scripts/check_provider_decision_pass.py", "provider_decision_pass_check"),
    CheckCommand("agent_reach_bridge", "scripts/check_agent_reach_bridge.py", "agent_reach_bridge_check"),
    CheckCommand("tradingview_mcp_adapter", "scripts/check_tradingview_mcp_adapter.py", "tradingview_mcp_adapter_check"),
    CheckCommand("bookmap_local_bridge", "scripts/check_bookmap_local_bridge.py", "bookmap_local_bridge_check"),
    CheckCommand(
        "evidence_packet_normalization",
        "scripts/check_evidence_packet_normalization.py",
        "evidence_packet_normalization_check",
    ),
    CheckCommand("evidence_packet_runtime", "scripts/check_evidence_packet_runtime.py", "evidence_packet_runtime_check"),
    CheckCommand("cockpit_status", "scripts/check_cockpit_status.py", "cockpit_status_check"),
)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _parse_key_values(output: str) -> dict[str, str]:
    values: dict[str, str] = {}
    for line in output.splitlines():
        if "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        if key:
            values[key] = value.strip()
    return values


def _as_bool(value: Any) -> bool | None:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        lowered = value.strip().lower()
        if lowered == "true":
            return True
        if lowered == "false":
            return False
    return None


def _as_int(value: Any, default: int = 0) -> int:
    try:
        return int(str(value))
    except (TypeError, ValueError):
        return default


def _run_check(command: CheckCommand) -> dict[str, Any]:
    result = subprocess.run(
        [sys.executable, str(ROOT / command.script)],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    output = result.stdout + ("\n" + result.stderr if result.stderr else "")
    parsed = _parse_key_values(output)
    return {
        "key": command.key,
        "script": command.script,
        "exit_code": result.returncode,
        "success_key": command.success_key,
        "success_value": parsed.get(command.success_key),
        "passed": result.returncode == 0 and parsed.get(command.success_key) == command.success_value,
        "parsed": parsed,
        "stdout_tail": result.stdout.splitlines()[-40:],
        "stderr_tail": result.stderr.splitlines()[-20:],
    }


def _expect_equal(
    checks: dict[str, dict[str, str]],
    check_key: str,
    field: str,
    expected: str,
    errors: list[str],
) -> None:
    actual = checks.get(check_key, {}).get(field)
    if actual != expected:
        errors.append(f"{check_key}.{field}_expected_{expected}_actual_{actual}")


def _expect_int_at_least(
    checks: dict[str, dict[str, str]],
    check_key: str,
    field: str,
    minimum: int,
    errors: list[str],
) -> None:
    actual = _as_int(checks.get(check_key, {}).get(field), -1)
    if actual < minimum:
        errors.append(f"{check_key}.{field}_below_{minimum}_actual_{actual}")


def _expect_int_at_most(
    checks: dict[str, dict[str, str]],
    check_key: str,
    field: str,
    maximum: int,
    errors: list[str],
) -> None:
    actual = _as_int(checks.get(check_key, {}).get(field), maximum + 1)
    if actual > maximum:
        errors.append(f"{check_key}.{field}_above_{maximum}_actual_{actual}")


def _expect_false(checks: dict[str, dict[str, str]], check_key: str, field: str, errors: list[str]) -> None:
    actual = _as_bool(checks.get(check_key, {}).get(field))
    if actual is not False:
        errors.append(f"{check_key}.{field}_not_false_actual_{checks.get(check_key, {}).get(field)}")


def _expect_true(checks: dict[str, dict[str, str]], check_key: str, field: str, errors: list[str]) -> None:
    actual = _as_bool(checks.get(check_key, {}).get(field))
    if actual is not True:
        errors.append(f"{check_key}.{field}_not_true_actual_{checks.get(check_key, {}).get(field)}")


def _cross_check(parsed_by_check: dict[str, dict[str, str]]) -> list[str]:
    errors: list[str] = []

    _expect_equal(parsed_by_check, "source_registry", "source_registry_blocker_source_count", "35", errors)
    _expect_equal(parsed_by_check, "source_registry", "source_registry_blocker_legacy_unresolved_count", "0", errors)
    _expect_equal(
        parsed_by_check,
        "source_registry",
        "source_registry_provider_decision_credential_required_now_count",
        "0",
        errors,
    )

    _expect_equal(parsed_by_check, "phase1_data_spine", "phase1_data_spine_source_count", "35", errors)
    _expect_equal(parsed_by_check, "phase1_data_spine", "phase1_data_spine_test_observation_count", "35", errors)
    _expect_int_at_least(parsed_by_check, "phase1_data_spine", "phase1_data_spine_promoted_adapter_count", 30, errors)
    _expect_int_at_most(parsed_by_check, "phase1_data_spine", "phase1_data_spine_missing_credential_source_count", 3, errors)

    _expect_int_at_least(
        parsed_by_check,
        "phase1_live_source_hardening",
        "phase1_live_source_hardening_live_or_sample_count",
        27,
        errors,
    )
    _expect_int_at_most(
        parsed_by_check,
        "phase1_live_source_hardening",
        "phase1_live_source_hardening_missing_credentials_count",
        3,
        errors,
    )

    _expect_equal(parsed_by_check, "credential_bound_adapters", "credential_bound_adapter_count", "3", errors)
    _expect_true(parsed_by_check, "credential_bound_adapters", "credential_bound_authority_unchanged", errors)
    _expect_true(parsed_by_check, "credential_bound_adapters", "credential_bound_secret_values_public_safe", errors)

    _expect_equal(parsed_by_check, "provider_decision_pass", "provider_decision_pass_decision_count", "5", errors)
    _expect_equal(
        parsed_by_check,
        "provider_decision_pass",
        "provider_decision_pass_credential_required_now_count",
        "0",
        errors,
    )
    _expect_true(parsed_by_check, "provider_decision_pass", "provider_decision_pass_authority_unchanged", errors)

    _expect_equal(parsed_by_check, "agent_reach_bridge", "agent_reach_bridge_status", "ok", errors)
    _expect_equal(parsed_by_check, "agent_reach_bridge", "agent_reach_bridge_reference_status", "reference_ready", errors)
    _expect_equal(parsed_by_check, "agent_reach_bridge", "agent_reach_bridge_canonical_source_count", "35", errors)
    _expect_false(parsed_by_check, "agent_reach_bridge", "agent_reach_bridge_counts_as_canonical_source", errors)
    _expect_int_at_least(
        parsed_by_check,
        "agent_reach_bridge",
        "agent_reach_bridge_selected_runtime_evidence_channel_count",
        8,
        errors,
    )
    _expect_int_at_least(
        parsed_by_check,
        "agent_reach_bridge",
        "agent_reach_bridge_qadam_existing_source_match_count",
        5,
        errors,
    )
    _expect_equal(parsed_by_check, "agent_reach_bridge", "agent_reach_bridge_authority_leak_count", "0", errors)
    _expect_false(parsed_by_check, "agent_reach_bridge", "agent_reach_bridge_secret_like_value_present", errors)
    _expect_false(parsed_by_check, "agent_reach_bridge", "agent_reach_bridge_source_quorum_credit_allowed", errors)
    _expect_false(parsed_by_check, "agent_reach_bridge", "agent_reach_bridge_paper_order_allowed", errors)
    _expect_false(parsed_by_check, "agent_reach_bridge", "agent_reach_bridge_broker_write_allowed", errors)
    _expect_false(parsed_by_check, "agent_reach_bridge", "agent_reach_bridge_live_capital_enabled", errors)

    _expect_true(parsed_by_check, "tradingview_mcp_adapter", "tradingview_mcp_adapter_connected", errors)
    _expect_false(parsed_by_check, "tradingview_mcp_adapter", "tradingview_mcp_adapter_live_calls_enabled", errors)
    _expect_false(parsed_by_check, "tradingview_mcp_adapter", "tradingview_mcp_adapter_execution_allowed", errors)
    _expect_false(parsed_by_check, "tradingview_mcp_adapter", "tradingview_mcp_adapter_paper_order_allowed", errors)
    _expect_false(parsed_by_check, "tradingview_mcp_adapter", "tradingview_mcp_adapter_broker_write_allowed", errors)

    _expect_true(parsed_by_check, "bookmap_local_bridge", "bookmap_local_bridge_fixture_connected", errors)
    _expect_false(parsed_by_check, "bookmap_local_bridge", "bookmap_local_bridge_execution_allowed", errors)
    _expect_false(parsed_by_check, "bookmap_local_bridge", "bookmap_local_bridge_paper_order_allowed", errors)
    _expect_false(parsed_by_check, "bookmap_local_bridge", "bookmap_local_bridge_broker_write_allowed", errors)
    _expect_false(parsed_by_check, "bookmap_local_bridge", "bookmap_local_bridge_bookmap_order_injection_allowed", errors)
    _expect_false(parsed_by_check, "bookmap_local_bridge", "bookmap_local_bridge_bookmap_trading_mode_allowed", errors)

    _expect_equal(parsed_by_check, "evidence_packet_normalization", "evidence_packet_normalization_status", "ok", errors)
    _expect_equal(
        parsed_by_check,
        "evidence_packet_normalization",
        "evidence_packet_normalization_authority_leak_count",
        "0",
        errors,
    )
    _expect_equal(
        parsed_by_check,
        "evidence_packet_normalization",
        "evidence_packet_normalization_raw_ref_leak_count",
        "0",
        errors,
    )
    _expect_false(
        parsed_by_check,
        "evidence_packet_normalization",
        "evidence_packet_normalization_secret_like_value_present",
        errors,
    )

    _expect_equal(parsed_by_check, "evidence_packet_runtime", "evidence_packet_runtime_status", "ok", errors)
    _expect_equal(
        parsed_by_check,
        "evidence_packet_runtime",
        "evidence_packet_runtime_replay_status",
        "local_jsonl_replay_ready",
        errors,
    )
    _expect_equal(parsed_by_check, "evidence_packet_runtime", "evidence_packet_runtime_authority_leak_count", "0", errors)
    _expect_equal(parsed_by_check, "evidence_packet_runtime", "evidence_packet_runtime_raw_ref_leak_count", "0", errors)
    _expect_true(parsed_by_check, "evidence_packet_runtime", "evidence_packet_runtime_public_safe", errors)

    _expect_equal(parsed_by_check, "cockpit_status", "cockpit_status_evidence_packet_normalization_status", "ok", errors)
    _expect_equal(parsed_by_check, "cockpit_status", "cockpit_status_evidence_packet_runtime_status", "ok", errors)
    _expect_equal(
        parsed_by_check,
        "cockpit_status",
        "cockpit_status_evidence_packet_runtime_replay_status",
        "local_jsonl_replay_ready",
        errors,
    )
    _expect_equal(parsed_by_check, "cockpit_status", "cockpit_status_tradingview_mcp_status", "connected", errors)
    _expect_true(parsed_by_check, "cockpit_status", "cockpit_status_tradingview_mcp_connected", errors)
    _expect_equal(parsed_by_check, "cockpit_status", "cockpit_status_bookmap_local_bridge_status", "sample_ready", errors)
    _expect_false(parsed_by_check, "cockpit_status", "cockpit_status_live_capital_enabled", errors)
    _expect_equal(parsed_by_check, "cockpit_status", "cockpit_status_mission_trade_blocking_source_gap_count", "0", errors)
    _expect_equal(parsed_by_check, "cockpit_status", "cockpit_status_mission_source_gap_silent_blocker_count", "0", errors)
    _expect_equal(
        parsed_by_check,
        "cockpit_status",
        "cockpit_status_paperops_source_gap_visibility_trade_blocking_count",
        "0",
        errors,
    )
    _expect_equal(
        parsed_by_check,
        "cockpit_status",
        "cockpit_status_paperops_source_gap_visibility_silent_blocker_count",
        "0",
        errors,
    )

    return errors


def _write_report(report: dict[str, Any]) -> None:
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    temp_path = REPORT_PATH.with_name(f".{REPORT_PATH.name}.tmp")
    temp_path.write_text(json.dumps(report, indent=2, sort_keys=True), encoding="utf-8")
    temp_path.replace(REPORT_PATH)


def main() -> int:
    results = [_run_check(command) for command in CHECKS]
    parsed_by_check = {str(result["key"]): dict(result["parsed"]) for result in results}
    errors: list[str] = [
        f"{result['key']}_failed_exit_{result['exit_code']}_success_{result['success_value']}"
        for result in results
        if not result["passed"]
    ]
    errors.extend(_cross_check(parsed_by_check))

    report = {
        "schema_version": 1,
        "status": "ok" if not errors else "error",
        "generated_at": _now(),
        "dashboard_simplification_scope": "excluded_by_request",
        "check_count": len(results),
        "passed_check_count": sum(1 for result in results if result["passed"]),
        "failed_check_count": sum(1 for result in results if not result["passed"]),
        "cross_check_error_count": len(errors),
        "errors": errors,
        "checks": results,
        "boundary": (
            "Stage 8 acceptance covers source/evidence/runtime contracts only. "
            "It excludes dashboard simplification and cannot approve trades, "
            "submit orders, call brokers, run quantum jobs, grant proof credit, "
            "or enable live capital."
        ),
    }
    _write_report(report)

    print("source_evidence_acceptance_status=" + report["status"])
    print(f"source_evidence_acceptance_check_count={report['check_count']}")
    print(f"source_evidence_acceptance_passed_check_count={report['passed_check_count']}")
    print(f"source_evidence_acceptance_failed_check_count={report['failed_check_count']}")
    print(f"source_evidence_acceptance_cross_check_error_count={report['cross_check_error_count']}")
    print("source_evidence_acceptance_dashboard_simplification_skipped=True")
    print(f"source_evidence_acceptance_report={REPORT_PATH.relative_to(ROOT)}")
    print(
        "source_evidence_acceptance_boundary="
        "source/evidence/runtime acceptance only; no dashboard simplification, trading authority, broker writes, or live capital"
    )
    for error in errors:
        print(f"source_evidence_acceptance_error={error}")

    if errors:
        return 1
    print("source_evidence_acceptance_check=ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
