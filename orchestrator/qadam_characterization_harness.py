"""RF-2 behavior characterization and negative safety regression harness."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from orchestrator.config import Settings
from orchestrator.qadam_operator_ready_common import (
    ROOT,
    artifact_metadata,
    authority_flags,
    now_iso,
    read_json,
    run_read_only_command,
    runtime_dir,
    unique_errors,
    validate_authority,
    write_json_atomic,
)
from orchestrator.qadam_refactor_baseline import (
    build_dashboard_contract,
    validate_dashboard_contract,
)

SCHEMA_VERSION = "qadam_characterization_harness.v1"
PHASE_ID = "RF-2"

CONTRACT_ARTIFACT = "qadam_characterization_contract.json"
RESULTS_ARTIFACT = "qadam_characterization_results.json"
SAFETY_RESULTS_ARTIFACT = "qadam_safety_regression_results.json"
DASHBOARD_RESULTS_ARTIFACT = "qadam_dashboard_route_characterization.json"
CHECK_ARTIFACT = "qadam_characterization_harness_checks.json"

CANONICAL_PAPEROPS_COMMAND = ".venv/bin/python scripts/run_paperops_autonomous_pass.py"
CANONICAL_PAPEROPS_SCRIPT = ROOT / "scripts" / "run_paperops_autonomous_pass.py"

CURRENT_CHECKS: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("dashboard_navigable_modules", ("node", "scripts/check_dashboard_navigable_modules.js")),
    ("dashboard_navigation_ux", ("node", "scripts/check_dashboard_navigation_ux.js")),
    (
        "dashboard_d11b_compatibility",
        ("node", "scripts/check_dashboard_d11b_new_navigation_contract.js"),
    ),
    (
        "portfolio_consistency",
        (".venv/bin/python", "scripts/check_dashboard_portfolio_consistency.py"),
    ),
)

SCHEMA_SAMPLES = (
    "qadam_long_backtest_lock.json",
    "qadam_next_generation_phase0_safety_lock.json",
    "qadam_next_generation_flow_certification.json",
    "qsase_dashboard_status.json",
    "paperops_autonomous_pass_summary.json",
    "qadam_refactor_baseline.json",
    "qadam_operator_ready_plan_state.json",
)

ALLOWED_ORIGIN_CLASSES = {
    "qadam_runtime",
    "qadam_origin_paper",
    "broker_mirror",
    "provider_historical",
    "provider_current",
    "backtest",
    "shadow",
    "fixture",
    "synthetic",
    "imported",
    "operator",
}


def _paths(settings: Settings | None = None) -> dict[str, Path]:
    runtime = runtime_dir(settings)
    return {
        "contract": runtime / CONTRACT_ARTIFACT,
        "results": runtime / RESULTS_ARTIFACT,
        "safety": runtime / SAFETY_RESULTS_ARTIFACT,
        "dashboard": runtime / DASHBOARD_RESULTS_ARTIFACT,
        "checks": runtime / CHECK_ARTIFACT,
    }


def _check_results() -> list[dict[str, Any]]:
    output: list[dict[str, Any]] = []
    for check_id, command in CURRENT_CHECKS:
        result = run_read_only_command(
            list(command),
            cwd=ROOT,
            timeout_seconds=60,
            output_line_limit=50,
        )
        output.append(
            {
                "check_id": check_id,
                "command": " ".join(command),
                "status": result.get("status"),
                "returncode": result.get("returncode"),
                "output_tail": [
                    *result.get("stdout_lines", [])[-10:],
                    *result.get("stderr_lines", [])[-10:],
                ],
            }
        )
    return output


def _schema_snapshot(settings: Settings | None = None) -> list[dict[str, Any]]:
    runtime = runtime_dir(settings)
    records: list[dict[str, Any]] = []
    for filename in SCHEMA_SAMPLES:
        path = runtime / filename
        payload = read_json(path)
        metadata = artifact_metadata(path)
        records.append(
            {
                **metadata,
                "artifact_type": payload.get("artifact_type"),
                "schema_version": payload.get("schema_version"),
                "status": payload.get("status"),
                "generated_at": payload.get("generated_at"),
                "origin_class": "qadam_runtime",
                "fixture": False,
                "proof_eligible": False,
            }
        )
    return records


def _paperops_source_contract() -> dict[str, Any]:
    try:
        source = CANONICAL_PAPEROPS_SCRIPT.read_text(encoding="utf-8")
    except OSError:
        source = ""
    required_tokens = (
        "read_long_backtest_lock",
        "is_long_backtest_lock_active",
        "build_research_lock_watch_only_summary",
    )
    return {
        "command": CANONICAL_PAPEROPS_COMMAND,
        "script": str(CANONICAL_PAPEROPS_SCRIPT.relative_to(ROOT)),
        "script_exists": CANONICAL_PAPEROPS_SCRIPT.exists(),
        "research_lock_tokens_present": all(token in source for token in required_tokens),
        "research_lock_tokens": list(required_tokens),
        "behavior": "watch_only_when_long_research_lock_active",
        "broker_route": "guarded_alpaca_paper_only",
        "direct_broker_calls_added_by_wave0": False,
    }


def _proof_boundary() -> dict[str, Any]:
    return {
        "eligible_origin_class": "qadam_origin_paper",
        "requires_real_closed_paper_trade": True,
        "requires_complete_lineage": True,
        "ineligible_origin_classes": sorted(
            ALLOWED_ORIGIN_CLASSES - {"qadam_origin_paper"}
        ),
        "backtest_proof_credit_allowed": False,
        "shadow_proof_credit_allowed": False,
        "fixture_proof_credit_allowed": False,
        "broker_mirror_proof_credit_allowed": False,
    }


def validate_provenance_record(record: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    origin = record.get("origin_class")
    if origin not in ALLOWED_ORIGIN_CLASSES:
        errors.append("origin_class_invalid")
    if record.get("fixture") is True and record.get("evidence_eligible") is not False:
        errors.append("fixture_marked_evidence_eligible")
    if origin in {"fixture", "synthetic", "backtest", "shadow", "broker_mirror"}:
        if record.get("proof_eligible") is not False:
            errors.append(f"nonproof_origin_marked_proof_eligible:{origin}")
    if record.get("proof_eligible") is True:
        if origin != "qadam_origin_paper":
            errors.append("proof_origin_not_qadam_paper")
        if record.get("lifecycle_state") != "closed":
            errors.append("proof_trade_not_closed")
        if record.get("complete_lineage") is not True:
            errors.append("proof_lineage_incomplete")
    return unique_errors(errors)


def validate_point_in_time_record(record: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    try:
        available = datetime.fromisoformat(str(record.get("available_at")).replace("Z", "+00:00"))
        decision = datetime.fromisoformat(str(record.get("decision_at")).replace("Z", "+00:00"))
    except (TypeError, ValueError):
        return ["point_in_time_timestamp_invalid"]
    if available.tzinfo is None:
        available = available.replace(tzinfo=timezone.utc)
    if decision.tzinfo is None:
        decision = decision.replace(tzinfo=timezone.utc)
    if available > decision:
        errors.append("future_information_leakage")
    return errors


def validate_execution_route(record: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if record.get("live_capital_enabled") is not False:
        errors.append("execution_live_capital_not_disabled")
    if record.get("broker_route") != "guarded_alpaca_paper_only":
        errors.append("execution_route_not_guarded_alpaca_paper")
    if record.get("direct_broker_call_allowed") is not False:
        errors.append("direct_broker_call_allowed")
    if record.get("qctrl_bypass_allowed") is not False:
        errors.append("qctrl_bypass_allowed")
    return unique_errors(errors)


def build_characterization_contract(settings: Settings | None = None) -> dict[str, Any]:
    runtime = runtime_dir(settings)
    lock = read_json(runtime / "qadam_long_backtest_lock.json")
    dashboard = build_dashboard_contract()
    return {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "qadam_characterization_contract",
        "phase_id": PHASE_ID,
        "generated_at": now_iso(),
        "status": "characterization_contract_defined",
        "behavior_change_allowed": False,
        "paperops": _paperops_source_contract(),
        "research_lock": {
            "status": lock.get("status"),
            "paperops_watch_only_mode": lock.get("paperops_watch_only_mode"),
            "release_requires_explicit_operator_action": lock.get(
                "release_requires_explicit_operator_action"
            ),
        },
        "dashboard": {
            "contract_version": dashboard.get("contract_version"),
            "default_route": dashboard.get("default_route"),
            "module_count": dashboard.get("module_count"),
            "route_count": dashboard.get("route_count"),
            "routes": dashboard.get("routes"),
            "read_only": True,
            "command_disabled": True,
        },
        "paper_trial": {
            "canonical_name": "30-day paper growth trial",
            "calendar_advance_allowed": False,
            "simulated_elapsed_time_allowed": False,
        },
        "provenance": {
            "allowed_origin_classes": sorted(ALLOWED_ORIGIN_CLASSES),
            "fixtures_are_evidence": False,
            "fixtures_are_proof": False,
        },
        "proof_boundary": _proof_boundary(),
        "authority": authority_flags(),
    }


def build_safety_regression_results() -> dict[str, Any]:
    probes: list[dict[str, Any]] = []

    unsafe_authority = authority_flags()
    unsafe_authority["broker_write_allowed"] = True
    authority_errors = validate_authority(unsafe_authority, prefix="safety_probe")
    probes.append(
        {
            "probe_id": "broker_write_authority",
            "passed": "safety_probe_forbidden_true:broker_write_allowed" in authority_errors,
            "errors": authority_errors,
        }
    )

    provenance_errors = validate_provenance_record(
        {
            "origin_class": "fixture",
            "fixture": True,
            "evidence_eligible": True,
            "proof_eligible": True,
        }
    )
    probes.append(
        {
            "probe_id": "fixture_evidence_and_proof",
            "passed": {
                "fixture_marked_evidence_eligible",
                "nonproof_origin_marked_proof_eligible:fixture",
            }.issubset(provenance_errors),
            "errors": provenance_errors,
        }
    )

    leakage_errors = validate_point_in_time_record(
        {
            "available_at": "2026-01-02T00:00:00+00:00",
            "decision_at": "2026-01-01T00:00:00+00:00",
        }
    )
    probes.append(
        {
            "probe_id": "future_information_leakage",
            "passed": "future_information_leakage" in leakage_errors,
            "errors": leakage_errors,
        }
    )

    route_errors = validate_execution_route(
        {
            "live_capital_enabled": True,
            "broker_route": "live_endpoint",
            "direct_broker_call_allowed": True,
            "qctrl_bypass_allowed": True,
        }
    )
    probes.append(
        {
            "probe_id": "unsafe_execution_route",
            "passed": len(route_errors) == 4,
            "errors": route_errors,
        }
    )

    proof_errors = validate_provenance_record(
        {
            "origin_class": "qadam_origin_paper",
            "fixture": False,
            "evidence_eligible": True,
            "proof_eligible": True,
            "lifecycle_state": "open",
            "complete_lineage": False,
        }
    )
    probes.append(
        {
            "probe_id": "incomplete_open_trade_proof",
            "passed": {
                "proof_trade_not_closed",
                "proof_lineage_incomplete",
            }.issubset(proof_errors),
            "errors": proof_errors,
        }
    )

    return {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "qadam_safety_regression_results",
        "generated_at": now_iso(),
        "status": "passed" if all(probe["passed"] for probe in probes) else "blocked",
        "probe_count": len(probes),
        "passed_probe_count": sum(probe["passed"] for probe in probes),
        "probes": probes,
        "authority": authority_flags(),
    }


def build_characterization_results(settings: Settings | None = None) -> dict[str, Any]:
    contract = build_characterization_contract(settings)
    dashboard = build_dashboard_contract()
    checks = _check_results()
    return {
        "contract": contract,
        "dashboard": dashboard,
        "results": {
            "schema_version": SCHEMA_VERSION,
            "artifact_type": "qadam_characterization_results",
            "generated_at": now_iso(),
            "status": "passed" if all(check["status"] == "passed" for check in checks) else "blocked",
            "behavior_change_detected": False,
            "checks": checks,
            "schema_snapshots": _schema_snapshot(settings),
            "golden_fixture_contract": {
                "origin_class": "fixture",
                "fixture": True,
                "evidence_eligible": False,
                "proof_eligible": False,
                "trade_candidate_eligible": False,
                "paper_order_eligible": False,
            },
            "authority": authority_flags(),
        },
    }


def validate_characterization_bundle(bundle: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    contract = bundle.get("contract") if isinstance(bundle.get("contract"), dict) else {}
    dashboard = bundle.get("dashboard") if isinstance(bundle.get("dashboard"), dict) else {}
    results = bundle.get("results") if isinstance(bundle.get("results"), dict) else {}
    paperops = contract.get("paperops") if isinstance(contract.get("paperops"), dict) else {}
    lock = contract.get("research_lock") if isinstance(contract.get("research_lock"), dict) else {}
    if paperops.get("command") != CANONICAL_PAPEROPS_COMMAND:
        errors.append("canonical_paperops_command_mismatch")
    if paperops.get("research_lock_tokens_present") is not True:
        errors.append("paperops_research_lock_awareness_missing")
    if lock.get("status") != "active" or lock.get("paperops_watch_only_mode") is not True:
        errors.append("characterized_research_lock_not_watch_only")
    errors.extend(validate_dashboard_contract(dashboard))
    checker_results = results.get("checks") if isinstance(results.get("checks"), list) else []
    if len(checker_results) != len(CURRENT_CHECKS):
        errors.append("characterization_check_count_mismatch")
    for check in checker_results:
        if check.get("status") != "passed":
            errors.append(f"characterization_check_failed:{check.get('check_id')}")
    if contract.get("paper_trial", {}).get("calendar_advance_allowed") is not False:
        errors.append("characterization_calendar_boundary_invalid")
    if results.get("golden_fixture_contract", {}).get("proof_eligible") is not False:
        errors.append("golden_fixture_proof_eligible")
    for label, payload in (("contract", contract), ("results", results), ("dashboard", dashboard)):
        errors.extend(validate_authority(payload.get("authority", {}), prefix=label))
    return unique_errors(errors)


def build_and_write_characterization_harness(
    settings: Settings | None = None,
) -> tuple[dict[str, Any], dict[str, Any], list[str]]:
    paths = _paths(settings)
    bundle = build_characterization_results(settings)
    safety = build_safety_regression_results()
    errors = validate_characterization_bundle(bundle)
    if safety.get("status") != "passed":
        errors.append("negative_safety_regression_failed")
    errors = unique_errors(errors)
    checks = {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "qadam_characterization_harness_checks",
        "phase_id": PHASE_ID,
        "generated_at": now_iso(),
        "status": "passed" if not errors else "blocked",
        "validation_errors": errors,
        "negative_probe_count": safety["probe_count"],
        "negative_probe_passed_count": safety["passed_probe_count"],
        "current_dashboard_checker_count": len(CURRENT_CHECKS),
        "superseded_dashboard_checker_count": 0,
        "behavior_change_detected": False,
        "authority": authority_flags(),
    }
    dashboard_characterization = {
        **bundle["dashboard"],
        "artifact_type": "qadam_dashboard_route_characterization",
        "characterized_at": now_iso(),
        "route_contract_passed": not validate_dashboard_contract(bundle["dashboard"]),
    }
    write_json_atomic(paths["contract"], bundle["contract"])
    write_json_atomic(paths["results"], bundle["results"])
    write_json_atomic(paths["safety"], safety)
    write_json_atomic(paths["dashboard"], dashboard_characterization)
    write_json_atomic(paths["checks"], checks)
    return bundle, checks, errors
