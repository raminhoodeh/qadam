#!/usr/bin/env python3
"""Stage 9 safety-boundary gate for Qadam's daily edge-learning loop."""

from __future__ import annotations

from collections.abc import Callable
from copy import deepcopy
from dataclasses import dataclass
from datetime import datetime, timezone
import json
import subprocess
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from orchestrator.daily_edge_findings import (  # noqa: E402
    EDGE_PATTERN_AUTHORITY_FALSE_FIELDS,
    validate_daily_edge_findings_brief,
)
from orchestrator.daily_learning_automation import validate_daily_learning_automation  # noqa: E402
from orchestrator.daily_telegram_learning_brief import (  # noqa: E402
    validate_daily_telegram_learning_brief,
)
from orchestrator.edge_memory_ledger import (  # noqa: E402
    EDGE_MEMORY_LEDGER_AUTHORITY_FALSE_FIELDS,
    validate_edge_memory_ledger,
)
from orchestrator.hypothesis_lifecycle import (  # noqa: E402
    HYPOTHESIS_LIFECYCLE_AUTHORITY_FALSE_FIELDS,
    validate_hypothesis_lifecycle,
)
from orchestrator.pattern_recognition_engine import (  # noqa: E402
    PATTERN_RECOGNITION_ENGINE_AUTHORITY_FALSE_FIELDS,
    validate_pattern_recognition_engine,
)
from orchestrator.promotion_gates import (  # noqa: E402
    PROMOTION_GATES_AUTHORITY_FALSE_FIELDS,
    validate_promotion_gates,
)
from orchestrator.quantum_mandatory_review_gate import (  # noqa: E402
    validate_quantum_mandatory_review_gate,
)
from orchestrator.quantum_meta_review import (  # noqa: E402
    QUANTUM_META_REVIEW_AUTHORITY_FALSE_FIELDS,
    validate_quantum_meta_review,
)
from orchestrator.self_improvement_proposals import (  # noqa: E402
    SELF_IMPROVEMENT_PROPOSALS_AUTHORITY_FALSE_FIELDS,
    validate_self_improvement_proposals,
)
from orchestrator.strategy_update_record import (  # noqa: E402
    STRATEGY_UPDATE_RECORD_AUTHORITY_FALSE_FIELDS,
    validate_strategy_update_record,
)
from orchestrator.strategy_weight_updates import (  # noqa: E402
    STRATEGY_WEIGHT_UPDATES_AUTHORITY_FALSE_FIELDS,
    validate_strategy_weight_updates,
)
from orchestrator.telegram_human_brief import (  # noqa: E402
    TELEGRAM_HUMAN_BRIEF_FALSE_FIELDS,
    validate_telegram_human_brief,
)


REPORT_PATH = ROOT / "data/runtime/daily_edge_learning_safety_boundary.json"
ACCEPTANCE_PATH = ROOT / "data/runtime/daily_edge_learning_acceptance.json"


Validator = Callable[[dict[str, Any]], None]


@dataclass(frozen=True)
class ArtifactContract:
    key: str
    relative_path: str
    validator: Validator
    expected_statuses: frozenset[str]
    false_fields: tuple[str, ...] = ()
    zero_count_fields: tuple[str, ...] = ()
    forbidden_true_fields: tuple[str, ...] = ()


COMMON_FORBIDDEN_TRUE_FIELDS: tuple[str, ...] = (
    "telegram_command_path_enabled",
    "telegram_trade_command_enabled",
    "telegram_place_trade_command_enabled",
    "telegram_approve_trade_command_enabled",
    "telegram_reject_trade_command_enabled",
    "trade_candidate_creation_allowed",
    "trade_candidate_created",
    "risk_approval_allowed",
    "execution_allowed",
    "paper_execution_allowed",
    "paper_order_allowed",
    "paper_order_staging_allowed",
    "paper_order_submission_allowed",
    "paper_trade_submission_allowed",
    "broker_write_allowed",
    "broker_post_allowed",
    "alpaca_post_allowed",
    "order_cancel_allowed",
    "position_close_allowed",
    "position_resize_allowed",
    "prediction_market_write_allowed",
    "quantum_provider_call_allowed",
    "quantum_hardware_submission_allowed",
    "quantum_job_authority",
    "quantum_job_creation_allowed",
    "active_strategy_mutation_allowed",
    "active_strategy_weight_mutation_allowed",
    "strategy_weight_application_allowed",
    "strategy_weight_update_allowed",
    "strategy_mutation_allowed",
    "repo_write_allowed",
    "repository_write_allowed",
    "code_change_allowed",
    "prompt_mutation_allowed",
    "deployment_allowed",
    "deploy_allowed",
    "auto_merge_allowed",
    "live_endpoint_allowed",
    "live_capital_enabled",
    "live_capital_enablement_allowed",
    "proof_credit_allowed",
    "proof_credit_grant_allowed",
    "can_promote_proposals",
    "can_create_implementation_tickets",
    "can_edit_code",
    "can_mutate_prompts",
    "can_apply_strategy_weights",
    "can_mutate_strategy",
    "can_change_order_sizing",
    "can_submit_paper_orders",
    "can_call_brokers",
    "can_call_quantum_providers",
    "can_deploy",
)


ARTIFACTS: tuple[ArtifactContract, ...] = (
    ArtifactContract(
        key="daily_edge_findings_brief",
        relative_path="data/runtime/daily_edge_findings_brief.json",
        validator=validate_daily_edge_findings_brief,
        expected_statuses=frozenset({"daily_edge_findings_ready_for_review"}),
        false_fields=EDGE_PATTERN_AUTHORITY_FALSE_FIELDS,
        forbidden_true_fields=COMMON_FORBIDDEN_TRUE_FIELDS,
    ),
    ArtifactContract(
        key="quantum_mandatory_review_gate",
        relative_path="data/runtime/quantum_mandatory_review_gate.json",
        validator=validate_quantum_mandatory_review_gate,
        expected_statuses=frozenset({"quantum_review_gate_passed"}),
        false_fields=EDGE_PATTERN_AUTHORITY_FALSE_FIELDS,
        forbidden_true_fields=COMMON_FORBIDDEN_TRUE_FIELDS,
    ),
    ArtifactContract(
        key="pattern_recognition_engine",
        relative_path="data/runtime/pattern_recognition_engine.json",
        validator=validate_pattern_recognition_engine,
        expected_statuses=frozenset({"pattern_engine_ready_for_quantum_oracle"}),
        false_fields=PATTERN_RECOGNITION_ENGINE_AUTHORITY_FALSE_FIELDS,
        forbidden_true_fields=COMMON_FORBIDDEN_TRUE_FIELDS,
    ),
    ArtifactContract(
        key="edge_memory_ledger",
        relative_path="data/runtime/edge_memory_ledger.json",
        validator=validate_edge_memory_ledger,
        expected_statuses=frozenset({"edge_memory_active"}),
        false_fields=EDGE_MEMORY_LEDGER_AUTHORITY_FALSE_FIELDS,
        forbidden_true_fields=COMMON_FORBIDDEN_TRUE_FIELDS,
    ),
    ArtifactContract(
        key="strategy_update_record",
        relative_path="data/runtime/strategy_update_record.json",
        validator=validate_strategy_update_record,
        expected_statuses=frozenset({"strategy_update_record_ready"}),
        false_fields=STRATEGY_UPDATE_RECORD_AUTHORITY_FALSE_FIELDS,
        zero_count_fields=("strategy_update_applied_count",),
        forbidden_true_fields=COMMON_FORBIDDEN_TRUE_FIELDS,
    ),
    ArtifactContract(
        key="hypothesis_lifecycle",
        relative_path="data/runtime/hypothesis_lifecycle.json",
        validator=validate_hypothesis_lifecycle,
        expected_statuses=frozenset({"hypothesis_lifecycle_active"}),
        false_fields=HYPOTHESIS_LIFECYCLE_AUTHORITY_FALSE_FIELDS,
        zero_count_fields=(
            "candidate_promotion_count",
            "applied_lifecycle_transition_count",
        ),
        forbidden_true_fields=COMMON_FORBIDDEN_TRUE_FIELDS,
    ),
    ArtifactContract(
        key="strategy_weight_updates",
        relative_path="data/runtime/strategy_weight_updates.json",
        validator=validate_strategy_weight_updates,
        expected_statuses=frozenset({"strategy_weight_updates_ready"}),
        false_fields=STRATEGY_WEIGHT_UPDATES_AUTHORITY_FALSE_FIELDS,
        zero_count_fields=(
            "strategy_weight_update_applied_count",
            "active_strategy_weight_mutation_count",
        ),
        forbidden_true_fields=COMMON_FORBIDDEN_TRUE_FIELDS,
    ),
    ArtifactContract(
        key="quantum_meta_review",
        relative_path="data/runtime/quantum_meta_review.json",
        validator=validate_quantum_meta_review,
        expected_statuses=frozenset({"quantum_meta_review_ready"}),
        false_fields=QUANTUM_META_REVIEW_AUTHORITY_FALSE_FIELDS,
        zero_count_fields=(
            "meta_review_applied_count",
            "active_strategy_weight_mutation_count",
        ),
        forbidden_true_fields=COMMON_FORBIDDEN_TRUE_FIELDS,
    ),
    ArtifactContract(
        key="self_improvement_proposals",
        relative_path="data/runtime/self_improvement_proposals.json",
        validator=validate_self_improvement_proposals,
        expected_statuses=frozenset({"self_improvement_proposals_ready"}),
        false_fields=SELF_IMPROVEMENT_PROPOSALS_AUTHORITY_FALSE_FIELDS,
        zero_count_fields=(
            "self_improvement_applied_count",
            "code_change_applied_count",
            "paper_order_submission_count",
            "broker_write_count",
            "quantum_provider_call_count",
        ),
        forbidden_true_fields=COMMON_FORBIDDEN_TRUE_FIELDS,
    ),
    ArtifactContract(
        key="promotion_gates",
        relative_path="data/runtime/promotion_gates.json",
        validator=validate_promotion_gates,
        expected_statuses=frozenset({"promotion_gates_ready"}),
        false_fields=PROMOTION_GATES_AUTHORITY_FALSE_FIELDS,
        zero_count_fields=(
            "promotion_gate_passed_count",
            "promotion_allowed_count",
            "promotion_applied_count",
            "human_approval_present_count",
            "implementation_ticket_created_count",
            "code_change_applied_count",
            "strategy_weight_application_count",
            "paper_order_submission_count",
            "broker_write_count",
            "quantum_provider_call_count",
        ),
        forbidden_true_fields=COMMON_FORBIDDEN_TRUE_FIELDS,
    ),
    ArtifactContract(
        key="telegram_human_brief",
        relative_path="data/runtime/telegram_human_brief.json",
        validator=validate_telegram_human_brief,
        expected_statuses=frozenset(
            {
                "telegram_human_brief_dry_run_ready",
                "telegram_human_brief_ready_to_send",
                "telegram_human_brief_sent",
                "telegram_human_brief_already_sent",
            }
        ),
        false_fields=TELEGRAM_HUMAN_BRIEF_FALSE_FIELDS,
        forbidden_true_fields=COMMON_FORBIDDEN_TRUE_FIELDS,
    ),
    ArtifactContract(
        key="daily_telegram_learning_brief",
        relative_path="data/runtime/daily_telegram_learning_brief.json",
        validator=validate_daily_telegram_learning_brief,
        expected_statuses=frozenset(
            {
                "daily_telegram_learning_brief_dry_run_ready",
                "daily_telegram_learning_brief_ready_to_send",
                "daily_telegram_learning_brief_sent",
                "daily_telegram_learning_brief_already_sent",
            }
        ),
        false_fields=TELEGRAM_HUMAN_BRIEF_FALSE_FIELDS,
        zero_count_fields=("strategy_learning_applied_count",),
        forbidden_true_fields=COMMON_FORBIDDEN_TRUE_FIELDS,
    ),
    ArtifactContract(
        key="daily_learning_automation",
        relative_path="data/runtime/daily_learning_automation.json",
        validator=validate_daily_learning_automation,
        expected_statuses=frozenset(
            {
                "daily_learning_automation_disabled",
                "daily_learning_automation_not_due",
                "daily_learning_automation_dry_run_ready",
                "daily_learning_automation_ready_to_send",
                "daily_learning_automation_sent",
                "daily_learning_automation_already_sent",
            }
        ),
        false_fields=TELEGRAM_HUMAN_BRIEF_FALSE_FIELDS,
        zero_count_fields=("strategy_learning_applied_count",),
        forbidden_true_fields=COMMON_FORBIDDEN_TRUE_FIELDS,
    ),
)


ACCEPTANCE_FALSE_FIELDS: tuple[str, ...] = (
    "dashboard_write_authority",
    "telegram_command_path_enabled",
    "paper_order_submission_allowed",
    "broker_write_allowed",
    "quantum_provider_call_allowed",
    "live_capital_enabled",
)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _read_json(relative_path: str) -> dict[str, Any]:
    path = ROOT / relative_path
    if not path.exists():
        raise FileNotFoundError(relative_path)
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"{relative_path} must contain a JSON object")
    return payload


def _int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _run_stage8_if_needed() -> tuple[bool, list[str]]:
    if ACCEPTANCE_PATH.exists():
        try:
            payload = json.loads(ACCEPTANCE_PATH.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            payload = {}
        if isinstance(payload, dict) and payload.get("status") == "ok":
            return False, []

    result = subprocess.run(
        (sys.executable, "scripts/check_daily_edge_learning_acceptance.py"),
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode == 0:
        return True, []
    return True, (result.stdout + "\n" + result.stderr).splitlines()[-40:]


def _probe_rejected(validator: Validator, payload: dict[str, Any]) -> bool:
    try:
        validator(payload)
    except ValueError:
        return True
    return False


def _nested_true_paths(payload: Any, field_names: set[str], path: str = "$") -> list[str]:
    found: list[str] = []
    if isinstance(payload, dict):
        for key, value in payload.items():
            child_path = f"{path}.{key}"
            if key in field_names and value is True:
                found.append(child_path)
            found.extend(_nested_true_paths(value, field_names, child_path))
    elif isinstance(payload, list):
        for index, value in enumerate(payload):
            found.extend(_nested_true_paths(value, field_names, f"{path}[{index}]"))
    return found


def _validate_acceptance(acceptance: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if acceptance.get("status") != "ok":
        errors.append(f"stage8_acceptance_status_{acceptance.get('status')}")
    if _int(acceptance.get("failed_check_count")) != 0:
        errors.append(f"stage8_failed_check_count_{acceptance.get('failed_check_count')}")
    if acceptance.get("errors") not in ([], None):
        errors.append("stage8_acceptance_errors_present")
    checks = acceptance.get("checks")
    if not isinstance(checks, list) or not checks:
        errors.append("stage8_checks_missing")
    else:
        failed = [str(check.get("key")) for check in checks if not check.get("passed")]
        if failed:
            errors.append("stage8_checks_failed=" + ",".join(failed))
    contract = acceptance.get("acceptance_contract")
    if not isinstance(contract, dict):
        errors.append("stage8_acceptance_contract_missing")
        return errors
    if contract.get("all_stage_checks_passed") is not True:
        errors.append("stage8_contract_not_all_passed")
    if contract.get("quantum_mandatory_gate_enforced") is not True:
        errors.append("stage8_contract_quantum_gate_not_enforced")
    if contract.get("strategy_updates_recommendation_only") is not True:
        errors.append("stage8_contract_strategy_not_recommendation_only")
    for field in ACCEPTANCE_FALSE_FIELDS:
        if contract.get(field) is not False:
            errors.append(f"stage8_acceptance_contract_authority_enabled:{field}")
    return errors


def _validate_artifact(contract: ArtifactContract, payload: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    try:
        contract.validator(payload)
    except ValueError as exc:
        errors.append(f"{contract.key}_validator_failed:{exc}")
    status = str(payload.get("status") or "")
    if status not in contract.expected_statuses:
        errors.append(f"{contract.key}_status_unexpected:{status}")
    for field in contract.false_fields:
        if payload.get(field) is not False:
            errors.append(f"{contract.key}_authority_enabled:{field}")
    for field in contract.zero_count_fields:
        if _int(payload.get(field), -1) != 0:
            errors.append(f"{contract.key}_count_nonzero:{field}={payload.get(field)}")
    leaked_paths = _nested_true_paths(payload, set(contract.forbidden_true_fields))
    if leaked_paths:
        errors.append(f"{contract.key}_nested_authority_true:" + ",".join(leaked_paths[:20]))
    return errors


def _run_tamper_probes(
    acceptance: dict[str, Any],
    artifacts: dict[str, dict[str, Any]],
) -> tuple[list[dict[str, Any]], list[str]]:
    errors: list[str] = []
    probes: list[dict[str, Any]] = []

    tampered_acceptance = deepcopy(acceptance)
    tampered_acceptance.setdefault("acceptance_contract", {})[
        "paper_order_submission_allowed"
    ] = True
    rejected = bool(_validate_acceptance(tampered_acceptance))
    probes.append({"probe": "acceptance_paper_order_authority", "rejected": rejected})
    if not rejected:
        errors.append("acceptance_paper_order_authority_probe_not_rejected")

    probe_specs: tuple[tuple[str, str], ...] = (
        ("pattern_recognition_engine", "quantum_provider_call_allowed"),
        ("pattern_recognition_engine", "paper_order_allowed"),
        ("edge_memory_ledger", "strategy_weight_update_allowed"),
        ("strategy_update_record", "strategy_update_applied_count"),
        ("strategy_weight_updates", "active_strategy_weight_mutated"),
        ("quantum_meta_review", "quantum_provider_call_allowed"),
        ("self_improvement_proposals", "code_change_allowed"),
        ("self_improvement_proposals", "paper_order_submission_allowed"),
        ("promotion_gates", "promotion_allowed"),
        ("telegram_human_brief", "telegram_command_path_enabled"),
        ("daily_telegram_learning_brief", "paper_order_submission_allowed"),
        ("daily_learning_automation", "quantum_provider_call_allowed"),
    )
    validators = {contract.key: contract.validator for contract in ARTIFACTS}
    for artifact_key, field in probe_specs:
        payload = deepcopy(artifacts[artifact_key])
        payload[field] = 1 if field.endswith("_count") else True
        rejected = _probe_rejected(validators[artifact_key], payload)
        probes.append({"probe": f"{artifact_key}.{field}", "rejected": rejected})
        if not rejected:
            errors.append(f"{artifact_key}_{field}_probe_not_rejected")
    return probes, errors


def _validate_cockpit_boundary() -> tuple[dict[str, Any], list[str]]:
    errors: list[str] = []
    cockpit = _read_json("data/runtime/cockpit-status.json")
    live_values = {
        "top_level": cockpit.get("live_capital_enabled"),
        "mission_control": (cockpit.get("mission_control") or {}).get("live_capital_enabled")
        if isinstance(cockpit.get("mission_control"), dict)
        else None,
        "system_stack": (
            ((cockpit.get("mission_control") or {}).get("system_stack") or {}).get(
                "live_capital_enabled"
            )
            if isinstance(cockpit.get("mission_control"), dict)
            else None
        ),
        "capital": (cockpit.get("capital") or {}).get("live_capital_enabled")
        if isinstance(cockpit.get("capital"), dict)
        else None,
    }
    for key, value in live_values.items():
        if value is True:
            errors.append(f"cockpit_live_capital_enabled:{key}")
    capital = cockpit.get("capital") if isinstance(cockpit.get("capital"), dict) else {}
    if capital.get("write_authority") is not False:
        errors.append("cockpit_capital_write_authority_not_false")
    boundary = str(capital.get("boundary") or "").lower()
    if "read-only" not in boundary or "no broker write" not in boundary:
        errors.append("cockpit_capital_boundary_weak")
    learning = cockpit.get("daily_learning_automation")
    if isinstance(learning, dict):
        if learning.get("telegram_command_path_enabled") is True:
            errors.append("cockpit_daily_learning_command_path_enabled")
        if learning.get("paper_order_submission_allowed") is True:
            errors.append("cockpit_daily_learning_paper_order_allowed")
        if learning.get("quantum_provider_call_allowed") is True:
            errors.append("cockpit_daily_learning_quantum_provider_allowed")
    return cockpit, errors


def main() -> None:
    refreshed_stage8, refresh_errors = _run_stage8_if_needed()
    errors: list[str] = list(refresh_errors)

    acceptance = _read_json("data/runtime/daily_edge_learning_acceptance.json")
    errors.extend(_validate_acceptance(acceptance))

    artifacts: dict[str, dict[str, Any]] = {}
    artifact_summaries: list[dict[str, Any]] = []
    for contract in ARTIFACTS:
        payload = _read_json(contract.relative_path)
        artifacts[contract.key] = payload
        artifact_errors = _validate_artifact(contract, payload)
        errors.extend(artifact_errors)
        artifact_summaries.append(
            {
                "key": contract.key,
                "status": payload.get("status"),
                "authority_leak_count": len(artifact_errors),
                "false_field_count": len(contract.false_fields),
                "zero_count_field_count": len(contract.zero_count_fields),
            }
        )

    cockpit, cockpit_errors = _validate_cockpit_boundary()
    errors.extend(cockpit_errors)

    probes, probe_errors = _run_tamper_probes(acceptance, artifacts)
    errors.extend(probe_errors)

    boundary_contract = {
        "learning_cannot_trade": True,
        "learning_cannot_mutate_strategy": True,
        "telegram_cannot_accept_commands": True,
        "dashboard_cannot_write": True,
        "quantum_review_required": True,
        "daily_loop_cannot_call_quantum_providers_directly": True,
        "strategy_updates_recommendation_only": True,
        "promotion_requires_human_approval": True,
        "alpaca_paper_is_only_execution_route": True,
        "live_capital_disabled": True,
    }
    summary = {
        "schema_version": 1,
        "artifact_type": "daily_edge_learning_safety_boundary",
        "stage": "Stage 9 - Safety Boundary",
        "generated_at": _now(),
        "status": "ok" if not errors else "failed",
        "errors": errors,
        "stage8_refreshed": refreshed_stage8,
        "boundary_count": len(boundary_contract),
        "authority_artifact_count": len(artifact_summaries),
        "authority_leak_count": len(errors),
        "tamper_probe_count": len(probes),
        "tamper_probe_rejected_count": sum(1 for probe in probes if probe["rejected"]),
        "boundary_contract": boundary_contract,
        "artifact_summaries": artifact_summaries,
        "tamper_probes": probes,
        "cockpit_boundary": {
            "generated_at": cockpit.get("generated_at"),
            "headline": (cockpit.get("mission_control") or {}).get("headline")
            if isinstance(cockpit.get("mission_control"), dict)
            else None,
            "capital_broker": (cockpit.get("capital") or {}).get("broker")
            if isinstance(cockpit.get("capital"), dict)
            else None,
            "capital_write_authority": (cockpit.get("capital") or {}).get("write_authority")
            if isinstance(cockpit.get("capital"), dict)
            else None,
            "live_capital_enabled_seen": False,
        },
    }
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text(json.dumps(summary, indent=2, sort_keys=True), encoding="utf-8")

    if errors:
        raise SystemExit("; ".join(errors))

    print("daily_edge_learning_safety_boundary_check=ok")
    print("daily_edge_learning_safety_boundary_status=ok")
    print(f"daily_edge_learning_safety_boundary_stage={summary['stage']}")
    print(f"daily_edge_learning_safety_boundary_boundary_count={summary['boundary_count']}")
    print(
        "daily_edge_learning_safety_boundary_tamper_probe_rejected_count="
        f"{summary['tamper_probe_rejected_count']}"
    )
    print(
        "daily_edge_learning_safety_boundary_authority_artifact_count="
        f"{summary['authority_artifact_count']}"
    )
    print(f"daily_edge_learning_safety_boundary_artifact_path={REPORT_PATH.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
