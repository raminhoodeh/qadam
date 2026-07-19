"""RF-0 baseline capture for Qadam's operator-ready edge-engine program."""

from __future__ import annotations

from copy import deepcopy
import os
from pathlib import Path
import re
from typing import Any

from orchestrator.config import Settings
from orchestrator.qadam_operator_ready_common import (
    ROOT,
    artifact_metadata,
    authority_flags,
    file_sha256,
    git_snapshot,
    now_iso,
    public_path,
    read_json,
    run_read_only_command,
    runtime_dir,
    unique_errors,
    validate_authority,
    write_json_atomic,
)

SCHEMA_VERSION = "qadam_refactor_baseline.v1"
PHASE_ID = "RF-0"

BASELINE_ARTIFACT = "qadam_refactor_baseline.json"
DASHBOARD_CONTRACT_ARTIFACT = "qadam_dashboard_navigation_contract.json"
SCOPE_ARTIFACT = "qadam_refactor_scope.json"
CHECKS_ARTIFACT = "qadam_refactor_baseline_checks.json"
PHASE_STATUS_ARTIFACT = "qadam_operator_ready_phase_status.json"

PLAN_PATH = ROOT / "docs" / "qadam-operator-ready-edge-engine-implementation-plan.md"
DASHBOARD_RENDERER = ROOT / "landing-page-repo" / "dashboard.js"

EXPECTED_MODULES = (
    "fund",
    "observe",
    "patterns",
    "decide",
    "trade",
    "learn",
    "system",
)
EXPECTED_ROUTE_COUNT = 14

DASHBOARD_CHECKERS: tuple[tuple[str, str, tuple[str, ...]], ...] = (
    (
        "current_navigable_modules",
        "scripts/check_dashboard_navigable_modules.js",
        (),
    ),
    (
        "legacy_navigation_ux",
        "scripts/check_dashboard_navigation_ux.js",
        ("missing data-cockpit-nav",),
    ),
    (
        "legacy_d11b_navigation",
        "scripts/check_dashboard_d11b_new_navigation_contract.js",
        ("D11B nav targets mismatch",),
    ),
)

PROCESS_PATTERNS: tuple[tuple[str, str], ...] = (
    ("paperops", "scripts/run_paperops_autonomous_pass.py"),
    ("active_paper", "scripts/run_active_paper_trading_automation.py"),
    ("daily_learning_live", "scripts/run_daily_learning_automation.py --live"),
    ("whole_universe_backfill", "scripts/run_qsase_whole_universe_backfill_backtest.py"),
)

RUNTIME_INPUTS = (
    "qadam_long_backtest_lock.json",
    "qadam_next_generation_phase0_safety_lock.json",
    "qadam_next_generation_backtest_dashboard_summary.json",
    "qadam_next_generation_flow_certification.json",
    "qsase_whole_universe_backfill_backtest_state.json",
    "qsase_whole_universe_backfill_backtest_dashboard_summary.json",
    "qsase_dashboard_status.json",
    "paperops_autonomous_pass_summary.json",
)

WAVE0_PHASES = (
    "RF-0",
    "DP-0",
    "RF-1",
    "RF-2",
    "RF-3",
    "RF-4",
    "RF-5",
    "RF-6",
    *(f"OR-{index}" for index in range(20)),
)


def _paths(settings: Settings | None = None) -> dict[str, Path]:
    runtime = runtime_dir(settings)
    return {
        "baseline": runtime / BASELINE_ARTIFACT,
        "dashboard_contract": runtime / DASHBOARD_CONTRACT_ARTIFACT,
        "scope": runtime / SCOPE_ARTIFACT,
        "checks": runtime / CHECKS_ARTIFACT,
        "phase_status": runtime / PHASE_STATUS_ARTIFACT,
    }


def _extract_balanced_array(text: str, marker: str) -> str:
    start = text.find(marker)
    if start < 0:
        return ""
    start = text.find("[", start)
    if start < 0:
        return ""
    depth = 0
    quote: str | None = None
    escaped = False
    for index in range(start, len(text)):
        char = text[index]
        if quote is not None:
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == quote:
                quote = None
            continue
        if char in {'"', "'", "`"}:
            quote = char
        elif char == "[":
            depth += 1
        elif char == "]":
            depth -= 1
            if depth == 0:
                return text[start : index + 1]
    return ""


def parse_dashboard_navigation(renderer_text: str) -> list[dict[str, Any]]:
    block = _extract_balanced_array(renderer_text, "const QSASE_DASHBOARD_NAVIGATION")
    if not block:
        return []
    module_pattern = re.compile(
        r"\{\s*id:\s*\"(?P<id>[^\"]+)\"\s*,\s*"
        r"icon:\s*\"[^\"]+\"\s*,\s*"
        r"label:\s*\"(?P<label>[^\"]+)\"\s*,\s*"
        r"stage:\s*\"(?P<stage>[^\"]+)\"\s*,\s*"
        r"(?:crossCutting:\s*(?:true|false)\s*,\s*)?"
        r"views:\s*\[(?P<views>.*?)\]\s*\}",
        re.DOTALL,
    )
    view_pattern = re.compile(
        r"\{\s*id:\s*\"(?P<id>[^\"]+)\"\s*,\s*label:\s*\"(?P<label>[^\"]+)\"\s*\}"
    )
    modules: list[dict[str, Any]] = []
    for match in module_pattern.finditer(block):
        views = [
            {"view_id": view.group("id"), "label": view.group("label")}
            for view in view_pattern.finditer(match.group("views"))
        ]
        modules.append(
            {
                "module_id": match.group("id"),
                "label": match.group("label"),
                "stage": match.group("stage"),
                "views": views,
                "routes": [f"{match.group('id')}/{view['view_id']}" for view in views],
            }
        )
    return modules


def _dashboard_checker_results() -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []
    for checker_id, checker_path, superseded_signatures in DASHBOARD_CHECKERS:
        outcome = run_read_only_command(
            ["node", checker_path],
            cwd=ROOT,
            timeout_seconds=45,
            output_line_limit=80,
        )
        combined = "\n".join(
            [*outcome.get("stdout_lines", []), *outcome.get("stderr_lines", [])]
        )
        classification = outcome.get("status")
        if outcome.get("status") == "failed" and any(
            signature in combined for signature in superseded_signatures
        ):
            classification = "superseded_contract_failure"
        results.append(
            {
                "checker_id": checker_id,
                "checker": checker_path,
                "returncode": outcome.get("returncode"),
                "classification": classification,
                "superseded_contract_signatures": list(superseded_signatures),
                "output_tail": combined.splitlines()[-12:],
            }
        )
    return results


def _process_snapshot() -> dict[str, Any]:
    outcome = run_read_only_command(
        ["ps", "-axo", "pid=,command="],
        timeout_seconds=10,
        output_line_limit=10000,
    )
    if outcome.get("status") != "passed":
        return {"status": "not_verified", "matches": [], "match_count": 0}
    current_pid = os.getpid()
    matches: list[dict[str, Any]] = []
    for line in outcome.get("stdout_lines", []):
        stripped = line.strip()
        pid_text, _, command = stripped.partition(" ")
        try:
            pid = int(pid_text)
        except ValueError:
            continue
        if pid == current_pid:
            continue
        for process_id, signature in PROCESS_PATTERNS:
            if signature in command:
                matches.append({"process_id": process_id, "pid": pid})
    return {"status": "passed", "matches": matches, "match_count": len(matches)}


def _scheduler_snapshot() -> dict[str, Any]:
    outcome = run_read_only_command(
        ["launchctl", "list"],
        timeout_seconds=10,
        output_line_limit=5000,
    )
    if outcome.get("status") != "passed":
        return {"status": "not_verified", "qadam_labels": []}
    labels = [line.split()[-1] for line in outcome.get("stdout_lines", []) if "qadam" in line.lower()]
    return {"status": "passed", "qadam_labels": sorted(set(labels))}


def _runtime_snapshot(settings: Settings | None = None) -> list[dict[str, Any]]:
    runtime = runtime_dir(settings)
    return [artifact_metadata(runtime / filename) for filename in RUNTIME_INPUTS]


def build_dashboard_contract() -> dict[str, Any]:
    try:
        renderer_text = DASHBOARD_RENDERER.read_text(encoding="utf-8")
    except OSError:
        renderer_text = ""
    modules = parse_dashboard_navigation(renderer_text)
    routes = [route for module in modules for route in module["routes"]]
    checker_results = _dashboard_checker_results()
    return {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "qadam_dashboard_navigation_contract",
        "generated_at": now_iso(),
        "contract_version": "decision_flow_navigation_v1",
        "source_renderer": public_path(DASHBOARD_RENDERER),
        "source_renderer_sha256": file_sha256(DASHBOARD_RENDERER),
        "default_route": "fund/portfolio",
        "query_contract": "/dashboard/?module=<module>&view=<view>",
        "module_count": len(modules),
        "route_count": len(routes),
        "modules": modules,
        "routes": routes,
        "refresh_interval_seconds": 15,
        "behavior_contract": {
            "desktop_left_sidebar": True,
            "mobile_section_control": True,
            "route_persists_across_refresh": True,
            "previous_next_journey_navigation": True,
            "read_only": True,
            "command_disabled": True,
        },
        "checker_results": checker_results,
        "canonical_checker_id": "current_navigable_modules",
        "legacy_checker_debt_count": sum(
            result["classification"] == "superseded_contract_failure"
            for result in checker_results
        ),
        "authority": authority_flags(),
    }


def build_refactor_scope() -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "qadam_refactor_scope",
        "generated_at": now_iso(),
        "phase_id": PHASE_ID,
        "in_scope": [
            "edge_path_architecture_and_artifact_ownership",
            "runtime_and_dashboard_characterization",
            "provider_storage_and_research_boundaries",
            "decision_risk_router_and_paperops_handoff_boundaries",
            "compatibility_readers_and_legacy_quarantine_metadata",
            "controlled_dynamic_plan_status_and_evidence",
        ],
        "out_of_scope": [
            "strategy_logic_changes",
            "provider_backfill_acquisition",
            "paper_order_submission",
            "broker_behavior_changes",
            "secrets_or_environment_edits",
            "live_capital",
            "paper_trial_calendar_changes",
            "dashboard_information_architecture_changes",
            "unrelated_dirty_worktree_cleanup",
        ],
        "allowed_writes": [
            "new_wave0_orchestrator_modules",
            "new_wave0_check_scripts",
            "wave0_runtime_audit_artifacts",
            "controlled_dynamic_status_block",
            "reviewed_documentation_updates",
        ],
        "authority": authority_flags(),
    }


def _initial_phase_status(generated_at: str) -> dict[str, Any]:
    return {
        "schema_version": "qadam_operator_ready_phase_status.v1",
        "artifact_type": "qadam_operator_ready_phase_status",
        "generated_at": generated_at,
        "program": "qadam_operator_ready_edge_engine",
        "current_phase": PHASE_ID,
        "status": "wave0_baseline_captured",
        "phases": {
            phase: {
                "state": "in_progress" if phase == PHASE_ID else "not_started",
                "checker_artifact": None,
                "evidence_hash": None,
                "updated_at": generated_at if phase == PHASE_ID else None,
            }
            for phase in WAVE0_PHASES
        },
        "authority": authority_flags(),
    }


def build_refactor_baseline(settings: Settings | None = None) -> dict[str, Any]:
    generated_at = now_iso()
    runtime = runtime_dir(settings)
    lock = read_json(runtime / "qadam_long_backtest_lock.json")
    certification = read_json(runtime / "qadam_next_generation_flow_certification.json")
    dashboard_contract = build_dashboard_contract()
    baseline = {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "qadam_refactor_baseline",
        "phase_id": PHASE_ID,
        "generated_at": generated_at,
        "status": "rf0_baseline_ready",
        "public_safe": True,
        "behavior_change_allowed": False,
        "root_worktree": git_snapshot(ROOT),
        "dashboard_worktree": git_snapshot(ROOT / "landing-page-repo"),
        "plan": artifact_metadata(PLAN_PATH),
        "dashboard_contract": {
            "contract_version": dashboard_contract["contract_version"],
            "module_count": dashboard_contract["module_count"],
            "route_count": dashboard_contract["route_count"],
            "routes": dashboard_contract["routes"],
            "renderer_sha256": dashboard_contract["source_renderer_sha256"],
            "legacy_checker_debt_count": dashboard_contract["legacy_checker_debt_count"],
        },
        "runtime_inputs": _runtime_snapshot(settings),
        "processes": _process_snapshot(),
        "schedulers": _scheduler_snapshot(),
        "research_lock": {
            "artifact_present": bool(lock),
            "status": lock.get("status"),
            "lock_type": lock.get("lock_type"),
            "paperops_watch_only_mode": lock.get("paperops_watch_only_mode"),
            "phase_1_backfill_started": lock.get("phase_1_backfill_started"),
            "release_requires_explicit_operator_action": lock.get(
                "release_requires_explicit_operator_action"
            ),
        },
        "next_generation_certification": {
            "artifact_present": bool(certification),
            "status": certification.get("status"),
            "generated_at": certification.get("generated_at"),
            "blocker_count": len(certification.get("blockers", []))
            if isinstance(certification.get("blockers"), list)
            else None,
        },
        "paper_trial": {
            "canonical_user_facing_name": "30-day paper growth trial",
            "calendar_advanced": False,
            "simulated_elapsed_time": False,
        },
        "authority": authority_flags(),
    }
    errors = validate_refactor_baseline(baseline, dashboard_contract=dashboard_contract)
    baseline["validation_errors"] = errors
    if errors:
        baseline["status"] = "rf0_baseline_blocked"
    return baseline


def validate_dashboard_contract(payload: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if payload.get("schema_version") != SCHEMA_VERSION:
        errors.append("dashboard_contract_schema_mismatch")
    modules = payload.get("modules") if isinstance(payload.get("modules"), list) else []
    module_ids = tuple(module.get("module_id") for module in modules)
    if module_ids != EXPECTED_MODULES:
        errors.append("dashboard_module_order_mismatch")
    routes = payload.get("routes") if isinstance(payload.get("routes"), list) else []
    if len(routes) != EXPECTED_ROUTE_COUNT or len(set(routes)) != EXPECTED_ROUTE_COUNT:
        errors.append("dashboard_route_count_mismatch")
    if payload.get("default_route") != "fund/portfolio":
        errors.append("dashboard_default_route_mismatch")
    checker_results = payload.get("checker_results")
    if not isinstance(checker_results, list):
        errors.append("dashboard_checker_results_missing")
    else:
        canonical = next(
            (item for item in checker_results if item.get("checker_id") == "current_navigable_modules"),
            {},
        )
        if canonical.get("classification") != "passed":
            errors.append("dashboard_canonical_navigation_checker_failed")
        allowed = {"passed", "superseded_contract_failure"}
        for checker in checker_results:
            if checker.get("classification") not in allowed:
                errors.append(f"dashboard_checker_unclassified_failure:{checker.get('checker_id')}")
    errors.extend(validate_authority(payload.get("authority", {}), prefix="dashboard_contract"))
    return unique_errors(errors)


def validate_refactor_baseline(
    payload: dict[str, Any],
    *,
    dashboard_contract: dict[str, Any] | None = None,
) -> list[str]:
    errors: list[str] = []
    if payload.get("schema_version") != SCHEMA_VERSION:
        errors.append("refactor_baseline_schema_mismatch")
    if payload.get("artifact_type") != "qadam_refactor_baseline":
        errors.append("refactor_baseline_type_mismatch")
    for key in ("root_worktree", "dashboard_worktree"):
        snapshot = payload.get(key) if isinstance(payload.get(key), dict) else {}
        if snapshot.get("git_probe_status") != "passed" or not snapshot.get("head"):
            errors.append(f"{key}_git_snapshot_not_verified")
    lock = payload.get("research_lock") if isinstance(payload.get("research_lock"), dict) else {}
    if lock.get("status") != "active":
        errors.append("research_lock_not_active")
    if lock.get("paperops_watch_only_mode") is not True:
        errors.append("paperops_watch_only_not_active")
    if lock.get("release_requires_explicit_operator_action") is not True:
        errors.append("research_lock_release_not_explicit")
    trial = payload.get("paper_trial") if isinstance(payload.get("paper_trial"), dict) else {}
    if trial.get("canonical_user_facing_name") != "30-day paper growth trial":
        errors.append("paper_trial_name_mismatch")
    if trial.get("calendar_advanced") is not False:
        errors.append("paper_trial_calendar_advanced")
    if trial.get("simulated_elapsed_time") is not False:
        errors.append("simulated_elapsed_time_detected")
    errors.extend(validate_authority(payload.get("authority", {}), prefix="refactor_baseline"))
    contract = dashboard_contract
    if contract is None:
        contract_summary = payload.get("dashboard_contract", {})
        if contract_summary.get("route_count") != EXPECTED_ROUTE_COUNT:
            errors.append("baseline_dashboard_route_count_mismatch")
    else:
        errors.extend(validate_dashboard_contract(contract))
    return unique_errors(errors)


def validate_negative_refactor_baseline_probes(
    baseline: dict[str, Any], dashboard_contract: dict[str, Any]
) -> list[str]:
    errors: list[str] = []
    authority_probe = deepcopy(baseline)
    authority_probe["authority"]["broker_write_allowed"] = True
    if "refactor_baseline_forbidden_true:broker_write_allowed" not in validate_refactor_baseline(
        authority_probe,
        dashboard_contract=dashboard_contract,
    ):
        errors.append("rf0_broker_write_probe_not_rejected")
    live_probe = deepcopy(baseline)
    live_probe["authority"]["live_capital_enabled"] = True
    if "refactor_baseline_forbidden_true:live_capital_enabled" not in validate_refactor_baseline(
        live_probe,
        dashboard_contract=dashboard_contract,
    ):
        errors.append("rf0_live_capital_probe_not_rejected")
    route_probe = deepcopy(dashboard_contract)
    route_probe["routes"] = route_probe.get("routes", [])[:-1]
    route_probe["route_count"] = len(route_probe["routes"])
    if "dashboard_route_count_mismatch" not in validate_dashboard_contract(route_probe):
        errors.append("rf0_dashboard_route_probe_not_rejected")
    calendar_probe = deepcopy(baseline)
    calendar_probe["paper_trial"]["calendar_advanced"] = True
    if "paper_trial_calendar_advanced" not in validate_refactor_baseline(
        calendar_probe,
        dashboard_contract=dashboard_contract,
    ):
        errors.append("rf0_calendar_probe_not_rejected")
    return unique_errors(errors)


def build_and_write_refactor_baseline(
    settings: Settings | None = None,
) -> tuple[dict[str, Any], dict[str, Any], list[str]]:
    paths = _paths(settings)
    dashboard_contract = build_dashboard_contract()
    baseline = build_refactor_baseline(settings)
    scope = build_refactor_scope()
    validation_errors = validate_refactor_baseline(
        baseline,
        dashboard_contract=dashboard_contract,
    )
    validation_errors.extend(
        validate_negative_refactor_baseline_probes(baseline, dashboard_contract)
    )
    validation_errors = unique_errors(validation_errors)
    checks = {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "qadam_refactor_baseline_checks",
        "phase_id": PHASE_ID,
        "generated_at": now_iso(),
        "status": "passed" if not validation_errors else "blocked",
        "validation_errors": validation_errors,
        "negative_safety_probe_count": 4,
        "negative_safety_probes_passed": not any(
            error.endswith("probe_not_rejected") for error in validation_errors
        ),
        "dashboard_checker_results": dashboard_contract["checker_results"],
        "authority": authority_flags(),
    }
    write_json_atomic(paths["dashboard_contract"], dashboard_contract)
    write_json_atomic(paths["scope"], scope)
    write_json_atomic(paths["baseline"], baseline)
    write_json_atomic(paths["checks"], checks)
    if not paths["phase_status"].exists():
        write_json_atomic(paths["phase_status"], _initial_phase_status(baseline["generated_at"]))
    return baseline, checks, validation_errors
