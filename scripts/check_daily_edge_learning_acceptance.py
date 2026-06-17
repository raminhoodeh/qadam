#!/usr/bin/env python3
"""Stage 8 aggregate acceptance gate for Qadam's daily edge-learning loop."""

from __future__ import annotations

import json
import subprocess
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
REPORT_PATH = ROOT / "data/runtime/daily_edge_learning_acceptance.json"


@dataclass(frozen=True)
class CheckCommand:
    key: str
    command: tuple[str, ...]
    success_key: str | None = None
    success_value: str = "ok"
    stdout_success_text: str | None = None
    report_path: str | None = None


CHECKS: tuple[CheckCommand, ...] = (
    CheckCommand(
        "daily_edge_findings",
        ("python", "scripts/check_daily_edge_findings_brief.py"),
        "daily_edge_findings_brief_check",
        report_path="data/runtime/daily_edge_findings_brief_check.json",
    ),
    CheckCommand(
        "quantum_mandatory_review_gate",
        ("python", "scripts/check_quantum_mandatory_review_gate.py"),
        "quantum_mandatory_review_gate_check",
        report_path="data/runtime/quantum_mandatory_review_gate_check.json",
    ),
    CheckCommand(
        "pattern_recognition_engine",
        ("python", "scripts/check_pattern_recognition_engine.py"),
        "pattern_recognition_engine_check",
        report_path="data/runtime/pattern_recognition_engine_check.json",
    ),
    CheckCommand(
        "edge_memory_ledger",
        ("python", "scripts/check_edge_memory_ledger.py"),
        "edge_memory_ledger_check",
        report_path="data/runtime/edge_memory_ledger_check.json",
    ),
    CheckCommand(
        "strategy_update_record",
        ("python", "scripts/check_strategy_update_record.py"),
        "strategy_update_record_check",
        report_path="data/runtime/strategy_update_record_check.json",
    ),
    CheckCommand(
        "hypothesis_lifecycle",
        ("python", "scripts/check_hypothesis_lifecycle.py"),
        "hypothesis_lifecycle_check",
        report_path="data/runtime/hypothesis_lifecycle_check.json",
    ),
    CheckCommand(
        "strategy_weight_updates",
        ("python", "scripts/check_strategy_weight_updates.py"),
        "strategy_weight_updates_check",
        report_path="data/runtime/strategy_weight_updates_check.json",
    ),
    CheckCommand(
        "quantum_meta_review",
        ("python", "scripts/check_quantum_meta_review.py"),
        "quantum_meta_review_check",
        report_path="data/runtime/quantum_meta_review_check.json",
    ),
    CheckCommand(
        "self_improvement_proposals",
        ("python", "scripts/check_self_improvement_proposals.py"),
        "self_improvement_proposals_check",
        report_path="data/runtime/self_improvement_proposals_check.json",
    ),
    CheckCommand(
        "promotion_gates",
        ("python", "scripts/check_promotion_gates.py"),
        "promotion_gates_check",
        report_path="data/runtime/promotion_gates_check.json",
    ),
    CheckCommand(
        "telegram_human_brief",
        ("python", "scripts/check_telegram_human_brief.py"),
        "telegram_human_brief_check",
        report_path="data/runtime/telegram_human_brief_check.json",
    ),
    CheckCommand(
        "daily_learning_automation",
        ("python", "scripts/check_daily_learning_automation.py"),
        "daily_learning_automation_check",
        report_path="data/runtime/daily_learning_automation_check.json",
    ),
    CheckCommand(
        "dashboard_stage7_visibility",
        ("node", "scripts/check_dashboard_stage7_visibility.js"),
        stdout_success_text="Dashboard Stage 7 visibility contract OK",
    ),
)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _parse_key_values(output: str) -> dict[str, str]:
    parsed: dict[str, str] = {}
    for line in output.splitlines():
        if "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        if key:
            parsed[key] = value.strip()
    return parsed


def _read_report(relative_path: str | None) -> dict[str, Any] | None:
    if not relative_path:
        return None
    path = ROOT / relative_path
    if not path.exists():
        return {"status": "missing", "path": relative_path}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        return {"status": "invalid_json", "path": relative_path, "error": str(exc)}


def _run_check(check: CheckCommand) -> dict[str, Any]:
    executable, *args = check.command
    if executable == "python":
        command = (sys.executable, *args)
    else:
        command = check.command
    result = subprocess.run(
        command,
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    output = result.stdout + ("\n" + result.stderr if result.stderr else "")
    parsed = _parse_key_values(output)
    key_success = True
    if check.success_key:
        key_success = parsed.get(check.success_key) == check.success_value
    text_success = True
    if check.stdout_success_text:
        text_success = check.stdout_success_text in output
    return {
        "key": check.key,
        "command": " ".join(command),
        "exit_code": result.returncode,
        "parsed": parsed,
        "success_key": check.success_key,
        "success_value": parsed.get(check.success_key) if check.success_key else None,
        "stdout_success_text": check.stdout_success_text,
        "report": _read_report(check.report_path),
        "passed": result.returncode == 0 and key_success and text_success,
        "stdout_tail": result.stdout.splitlines()[-30:],
        "stderr_tail": result.stderr.splitlines()[-20:],
    }


def _int(value: Any, default: int = 0) -> int:
    try:
        return int(str(value))
    except (TypeError, ValueError):
        return default


def _bool(value: Any) -> bool | None:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        lowered = value.strip().lower()
        if lowered == "true":
            return True
        if lowered == "false":
            return False
    return None


def _parsed(results: dict[str, dict[str, Any]], key: str) -> dict[str, str]:
    return dict(results.get(key, {}).get("parsed") or {})


def _report(results: dict[str, dict[str, Any]], key: str) -> dict[str, Any]:
    report = results.get(key, {}).get("report")
    return report if isinstance(report, dict) else {}


def _expect_equal(
    errors: list[str],
    results: dict[str, dict[str, Any]],
    check_key: str,
    field: str,
    expected: Any,
) -> None:
    actual = _report(results, check_key).get(field, _parsed(results, check_key).get(field))
    if actual != expected:
        errors.append(f"{check_key}.{field}_expected_{expected}_actual_{actual}")


def _expect_int_at_least(
    errors: list[str],
    results: dict[str, dict[str, Any]],
    check_key: str,
    field: str,
    minimum: int,
) -> None:
    actual = _report(results, check_key).get(field, _parsed(results, check_key).get(field))
    if _int(actual, -1) < minimum:
        errors.append(f"{check_key}.{field}_below_{minimum}_actual_{actual}")


def _expect_bool(
    errors: list[str],
    results: dict[str, dict[str, Any]],
    check_key: str,
    field: str,
    expected: bool,
) -> None:
    actual = _report(results, check_key).get(field, _parsed(results, check_key).get(field))
    if _bool(actual) is not expected:
        errors.append(f"{check_key}.{field}_expected_{expected}_actual_{actual}")


def _check_report_statuses(
    errors: list[str],
    results: dict[str, dict[str, Any]],
) -> None:
    for key, result in results.items():
        if not result["passed"]:
            errors.append(f"{key}_command_failed")
        report = result.get("report")
        if isinstance(report, dict) and report.get("status") not in {None, "ok"}:
            errors.append(f"{key}_report_status_{report.get('status')}")


def _cross_check(results: dict[str, dict[str, Any]]) -> list[str]:
    errors: list[str] = []
    _check_report_statuses(errors, results)

    _expect_equal(
        errors,
        results,
        "daily_edge_findings",
        "brief_status",
        "daily_edge_findings_ready_for_review",
    )
    _expect_int_at_least(errors, results, "daily_edge_findings", "source_count", 30)
    _expect_int_at_least(errors, results, "daily_edge_findings", "watched_instrument_count", 20)
    _expect_equal(errors, results, "daily_edge_findings", "candidate_pattern_count", 5)
    _expect_bool(errors, results, "daily_edge_findings", "quantum_core_gate", True)
    _expect_equal(
        errors,
        results,
        "daily_edge_findings",
        "quantum_mandatory_review_gate_status",
        "quantum_review_gate_passed",
    )
    _expect_bool(
        errors,
        results,
        "daily_edge_findings",
        "quantum_mandatory_review_gate_passed",
        True,
    )

    _expect_equal(
        errors,
        results,
        "quantum_mandatory_review_gate",
        "gate_status",
        "quantum_review_gate_passed",
    )
    _expect_bool(errors, results, "quantum_mandatory_review_gate", "quantum_core_gate", True)
    _expect_equal(
        errors,
        results,
        "quantum_mandatory_review_gate",
        "pattern_review_dependency_blocked_count",
        0,
    )
    _expect_bool(
        errors,
        results,
        "quantum_mandatory_review_gate",
        "fail_closed_probe_rejected",
        True,
    )
    _expect_bool(
        errors,
        results,
        "quantum_mandatory_review_gate",
        "pattern_bypass_probe_rejected",
        True,
    )

    _expect_equal(
        errors,
        results,
        "pattern_recognition_engine",
        "engine_status",
        "pattern_engine_ready_for_quantum_oracle",
    )
    _expect_int_at_least(errors, results, "pattern_recognition_engine", "source_count", 30)
    _expect_int_at_least(
        errors,
        results,
        "pattern_recognition_engine",
        "watched_instrument_count",
        20,
    )
    _expect_equal(errors, results, "pattern_recognition_engine", "candidate_pattern_count", 5)
    _expect_equal(
        errors,
        results,
        "pattern_recognition_engine",
        "quantum_oracle_contract_accepted_count",
        5,
    )
    _expect_bool(errors, results, "pattern_recognition_engine", "quantum_optimized", True)
    _expect_bool(errors, results, "pattern_recognition_engine", "fail_closed_probe_rejected", True)
    _expect_bool(errors, results, "pattern_recognition_engine", "authority_probe_rejected", True)

    _expect_equal(errors, results, "edge_memory_ledger", "ledger_status", "edge_memory_active")
    _expect_equal(errors, results, "edge_memory_ledger", "memory_record_count", 5)
    _expect_bool(errors, results, "edge_memory_ledger", "fail_closed_probe_rejected", True)
    _expect_bool(errors, results, "edge_memory_ledger", "authority_probe_rejected", True)

    _expect_equal(
        errors,
        results,
        "strategy_update_record",
        "record_status",
        "strategy_update_record_ready",
    )
    _expect_equal(errors, results, "strategy_update_record", "strategy_update_proposal_count", 5)
    _expect_equal(errors, results, "strategy_update_record", "strategy_update_applied_count", 0)
    _expect_bool(errors, results, "strategy_update_record", "fail_closed_probe_rejected", True)
    _expect_bool(errors, results, "strategy_update_record", "applied_probe_rejected", True)

    _expect_equal(
        errors,
        results,
        "hypothesis_lifecycle",
        "lifecycle_status",
        "hypothesis_lifecycle_active",
    )
    _expect_int_at_least(errors, results, "hypothesis_lifecycle", "source_hypothesis_count", 1)
    _expect_equal(errors, results, "hypothesis_lifecycle", "candidate_promotion_count", 0)
    _expect_bool(errors, results, "hypothesis_lifecycle", "promotion_probe_rejected", True)

    _expect_equal(
        errors,
        results,
        "strategy_weight_updates",
        "record_status",
        "strategy_weight_updates_ready",
    )
    _expect_equal(
        errors,
        results,
        "strategy_weight_updates",
        "strategy_weight_update_applied_count",
        0,
    )
    _expect_equal(
        errors,
        results,
        "strategy_weight_updates",
        "active_strategy_weight_mutation_count",
        0,
    )
    _expect_bool(errors, results, "strategy_weight_updates", "active_mutation_probe_rejected", True)

    _expect_equal(
        errors,
        results,
        "quantum_meta_review",
        "record_status",
        "quantum_meta_review_ready",
    )
    _expect_equal(errors, results, "quantum_meta_review", "quantum_meta_review_count", 5)
    _expect_equal(errors, results, "quantum_meta_review", "meta_review_applied_count", 0)
    _expect_equal(errors, results, "quantum_meta_review", "active_strategy_weight_mutation_count", 0)
    _expect_bool(errors, results, "quantum_meta_review", "quantum_bypass_probe_rejected", True)

    _expect_equal(
        errors,
        results,
        "self_improvement_proposals",
        "record_status",
        "self_improvement_proposals_ready",
    )
    _expect_equal(
        errors,
        results,
        "self_improvement_proposals",
        "self_improvement_proposal_count",
        5,
    )
    _expect_equal(
        errors,
        results,
        "self_improvement_proposals",
        "self_improvement_applied_count",
        0,
    )
    _expect_equal(errors, results, "self_improvement_proposals", "code_change_applied_count", 0)
    _expect_equal(
        errors,
        results,
        "self_improvement_proposals",
        "paper_order_submission_count",
        0,
    )
    _expect_bool(errors, results, "self_improvement_proposals", "quantum_bypass_probe_rejected", True)

    _expect_equal(errors, results, "promotion_gates", "record_status", "promotion_gates_ready")
    _expect_equal(errors, results, "promotion_gates", "promotion_gate_decision_count", 5)
    _expect_equal(errors, results, "promotion_gates", "promotion_review_ready_count", 5)
    _expect_equal(errors, results, "promotion_gates", "promotion_gate_passed_count", 0)
    _expect_equal(errors, results, "promotion_gates", "promotion_gate_held_count", 5)
    _expect_equal(errors, results, "promotion_gates", "promotion_allowed_count", 0)
    _expect_equal(errors, results, "promotion_gates", "promotion_applied_count", 0)
    _expect_equal(errors, results, "promotion_gates", "human_approval_present_count", 0)
    _expect_bool(errors, results, "promotion_gates", "promotion_bypass_probe_rejected", True)

    _expect_equal(errors, results, "telegram_human_brief", "message_human_style_status", "human")
    _expect_equal(errors, results, "telegram_human_brief", "message_specificity_status", "specific")
    _expect_int_at_least(errors, results, "telegram_human_brief", "message_specificity_score", 70)
    _expect_bool(errors, results, "telegram_human_brief", "live_send_attempted", False)
    _expect_bool(errors, results, "telegram_human_brief", "command_probe_rejected", True)
    _expect_bool(errors, results, "telegram_human_brief", "technical_message_probe_rejected", True)

    automation_report = _report(results, "daily_learning_automation")
    if automation_report.get("automation_status") not in {
        "daily_learning_automation_dry_run_ready",
        "daily_learning_automation_ready_to_send",
        "daily_learning_automation_sent",
        "daily_learning_automation_already_sent",
    }:
        errors.append(
            "daily_learning_automation.automation_status_unexpected_"
            f"{automation_report.get('automation_status')}"
        )
    learning_brief_status = automation_report.get("learning_brief_status")
    if learning_brief_status not in {
        "daily_telegram_learning_brief_dry_run_ready",
        "daily_telegram_learning_brief_ready_to_send",
        "daily_telegram_learning_brief_sent",
        "daily_telegram_learning_brief_already_sent",
    }:
        errors.append(
            "daily_learning_automation.learning_brief_status_unexpected_"
            f"{learning_brief_status}"
        )
    _expect_bool(errors, results, "daily_learning_automation", "due_or_forced", True)
    _expect_bool(errors, results, "daily_learning_automation", "live_send_attempted", False)
    _expect_bool(errors, results, "daily_learning_automation", "command_probe_rejected", True)
    _expect_bool(errors, results, "daily_learning_automation", "paper_order_probe_rejected", True)
    _expect_bool(errors, results, "daily_learning_automation", "quantum_probe_rejected", True)
    _expect_bool(errors, results, "daily_learning_automation", "strategy_probe_rejected", True)
    _expect_bool(
        errors,
        results,
        "daily_learning_automation",
        "technical_message_probe_rejected",
        True,
    )

    return errors


def main() -> None:
    results_list = [_run_check(check) for check in CHECKS]
    results = {result["key"]: result for result in results_list}
    errors = _cross_check(results)
    summary = {
        "schema_version": 1,
        "artifact_type": "daily_edge_learning_acceptance",
        "stage": "Stage 8 - Acceptance Tests",
        "generated_at": _now(),
        "status": "ok" if not errors else "failed",
        "errors": errors,
        "check_count": len(results_list),
        "passed_check_count": sum(1 for result in results_list if result["passed"]),
        "failed_check_count": sum(1 for result in results_list if not result["passed"]),
        "acceptance_contract": {
            "all_stage_checks_passed": not errors,
            "quantum_mandatory_gate_enforced": not errors,
            "all_sources_scan_required": True,
            "strategy_updates_recommendation_only": True,
            "telegram_message_human_plain_language": True,
            "dashboard_stage7_visibility_required": True,
            "dashboard_write_authority": False,
            "telegram_command_path_enabled": False,
            "paper_order_submission_allowed": False,
            "broker_write_allowed": False,
            "quantum_provider_call_allowed": False,
            "live_capital_enabled": False,
        },
        "checks": results_list,
    }
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text(json.dumps(summary, indent=2, sort_keys=True), encoding="utf-8")

    if errors:
        raise SystemExit("; ".join(errors))

    print("daily_edge_learning_acceptance_check=ok")
    print("daily_edge_learning_acceptance_status=ok")
    print(f"daily_edge_learning_acceptance_check_count={summary['check_count']}")
    print(f"daily_edge_learning_acceptance_passed_check_count={summary['passed_check_count']}")
    print("daily_edge_learning_acceptance_stage=Stage 8 - Acceptance Tests")
    print(f"daily_edge_learning_acceptance_artifact_path={REPORT_PATH.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
