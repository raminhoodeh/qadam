#!/usr/bin/env python3
"""Validate the pre-Phase-5 Layer B readiness gate."""

from __future__ import annotations

from copy import deepcopy
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from orchestrator.config import Settings  # noqa: E402
from orchestrator.phase5_readiness import (  # noqa: E402
    PHASE5_READINESS_SCHEMA_VERSION,
    build_phase5_layer_b_readiness,
    validate_phase5_layer_b_readiness,
    write_phase5_layer_b_readiness,
)


def main() -> int:
    errors: list[str] = []
    settings = Settings.from_env()
    artifact = build_phase5_layer_b_readiness(settings=settings)
    output_path, history_path = write_phase5_layer_b_readiness(
        artifact,
        settings=settings,
    )
    validation_errors = validate_phase5_layer_b_readiness(artifact)

    dishonest_probe = deepcopy(artifact)
    dishonest_probe["phase5_layer_b_implementation_allowed"] = True
    dishonest_probe["phase4_certified"] = False
    dishonest_probe["phase5_handoff_allowed"] = False
    dishonest_probe["readiness_blockers"] = ["phase4_not_certified", "phase5_handoff_not_allowed"]
    dishonest_probe["readiness_blocker_count"] = len(dishonest_probe["readiness_blockers"])
    dishonest_probe_errors = validate_phase5_layer_b_readiness(dishonest_probe)

    orchestration_probe = deepcopy(artifact)
    orchestration_probe["phase5_orchestration_start_allowed"] = True
    orchestration_probe_errors = validate_phase5_layer_b_readiness(orchestration_probe)

    authority_probe = deepcopy(artifact)
    authority_probe["paper_execution_allowed"] = True
    authority_probe_errors = validate_phase5_layer_b_readiness(authority_probe)

    source_promotion_probe = deepcopy(artifact)
    source_promotion_probe["preference_mcp_source_36"] = True
    source_promotion_errors = validate_phase5_layer_b_readiness(source_promotion_probe)

    print("phase5_readiness_status=" + artifact["status"])
    print(f"phase5_readiness_schema_version={PHASE5_READINESS_SCHEMA_VERSION}")
    print(f"phase5_readiness_artifact_path={output_path}")
    print(f"phase5_readiness_history_path={history_path}")
    print(
        "phase5_readiness_plan_allowed="
        f"{artifact['phase5_layer_b_implementation_plan_allowed']}"
    )
    print(
        "phase5_readiness_implementation_allowed="
        f"{artifact['phase5_layer_b_implementation_allowed']}"
    )
    print(
        "phase5_readiness_orchestration_start_allowed="
        f"{artifact['phase5_orchestration_start_allowed']}"
    )
    print(f"phase5_readiness_phase4_certified={artifact['phase4_certified']}")
    print(f"phase5_readiness_phase5_handoff_allowed={artifact['phase5_handoff_allowed']}")
    print(f"phase5_readiness_approval_state={artifact['approval_state']}")
    print(
        "phase5_readiness_blockers="
        + ",".join(artifact["readiness_blockers"])
    )
    print(f"phase5_readiness_blocker_count={artifact['readiness_blocker_count']}")
    print(
        "phase5_readiness_nonapproval_blocker_count="
        f"{artifact['nonapproval_blocker_count']}"
    )
    print(
        "phase5_readiness_only_explicit_approval_blocks_plan="
        f"{artifact['only_explicit_approval_blocks_phase5_plan']}"
    )
    print(
        "phase5_readiness_preference_source_promotion_status="
        f"{artifact['preference_source_promotion_status']}"
    )
    print(
        "phase5_readiness_preference_source_promotion_promoted_count="
        f"{artifact['preference_source_promotion_promoted_decision_count']}"
    )
    print(
        "phase5_readiness_preference_source_promotion_source_count_after="
        f"{artifact['preference_source_promotion_canonical_source_count_after']}"
    )
    print(f"phase5_readiness_preference_source36={artifact['preference_mcp_source_36']}")
    print(f"phase5_readiness_yahoo_role={artifact['yahoo_finance_role']}")
    print(f"phase5_readiness_scope_count={artifact['phase5_layer_b_scope_count']}")
    print(f"phase5_readiness_validation_error_count={len(validation_errors)}")
    print(f"phase5_readiness_dishonest_probe_error_count={len(dishonest_probe_errors)}")
    print(
        "phase5_readiness_orchestration_probe_error_count="
        f"{len(orchestration_probe_errors)}"
    )
    print(f"phase5_readiness_authority_probe_error_count={len(authority_probe_errors)}")
    print(
        "phase5_readiness_source_promotion_probe_error_count="
        f"{len(source_promotion_errors)}"
    )
    print(f"phase5_readiness_boundary={artifact['boundary']}")

    if validation_errors:
        errors.extend(validation_errors)
    if artifact["phase5_layer_b_implementation_plan_allowed"] is not True:
        errors.append("phase5_plan_not_allowed_despite_only_approval_blocker")
    if artifact["phase5_orchestration_start_allowed"] is not False:
        errors.append("phase5_orchestration_start_allowed")
    if artifact["phase5_layer_b_implementation_allowed"] is True:
        if artifact["status"] != "ready_for_phase5_layer_b_implementation":
            errors.append("phase5_readiness_status_not_ready")
        if artifact["phase4_certified"] is not True:
            errors.append("phase4_not_certified")
        if artifact["phase5_handoff_allowed"] is not True:
            errors.append("phase5_handoff_not_allowed")
        if artifact["approval_state"] != "approved":
            errors.append("phase5_readiness_approval_state_not_approved")
        if artifact["readiness_blockers"]:
            errors.append("phase5_readiness_has_blockers")
        if artifact["only_explicit_approval_blocks_phase5_plan"] is not False:
            errors.append("only_explicit_approval_flag_true_after_approval")
    else:
        if artifact["status"] != "blocked_pending_phase4_certification":
            errors.append("phase5_readiness_status_not_blocked")
        if artifact["phase4_certified"] is not False:
            errors.append("phase4_certified_unexpected")
        if artifact["phase5_handoff_allowed"] is not False:
            errors.append("phase5_handoff_allowed")
        if artifact["approval_state"] != "amendments_required":
            errors.append("phase5_readiness_approval_state_mismatch")
        if "explicit_fund_manager_approval_required" not in artifact["readiness_blockers"]:
            errors.append("explicit_approval_blocker_missing")
        if artifact["only_explicit_approval_blocks_phase5_plan"] is not True:
            errors.append("only_explicit_approval_flag_false")
    if artifact["nonapproval_blocker_count"] != 0:
        errors.append("nonapproval_blockers_present")
    if artifact["preference_source_promotion_status"] != "validated":
        errors.append("preference_source_promotion_not_validated")
    if artifact["preference_source_promotion_promoted_decision_count"] != 0:
        errors.append("preference_source_promotion_promoted")
    if artifact["preference_source_promotion_canonical_source_count_after"] != 35:
        errors.append("preference_source_promotion_count_mismatch")
    if artifact["preference_mcp_source_36"] is not False:
        errors.append("preference_source36_enabled")
    if artifact["yahoo_finance_role"] != "supplemental_market_confirmation_only":
        errors.append("yahoo_role_not_supplemental")
    if (
        "phase5_layer_b_implementation_allowed_without_certified_phase4"
        not in dishonest_probe_errors
    ):
        errors.append("dishonest_probe_not_rejected")
    if "phase5_orchestration_start_allowed" not in orchestration_probe_errors:
        errors.append("orchestration_probe_not_rejected")
    if (
        "phase5_readiness_authority_enabled:paper_execution_allowed"
        not in authority_probe_errors
    ):
        errors.append("authority_probe_not_rejected")
    if "preference_mcp_source_36" not in source_promotion_errors:
        errors.append("source_promotion_probe_not_rejected")

    for key in (
        "approval_policy_router_enabled",
        "risk_agent_approval_authority",
        "kill_switch_mutation_authority",
        "execution_adapter_write_authority",
        "paper_execution_allowed",
        "paper_order_allowed",
        "broker_write_allowed",
        "prediction_market_write_allowed",
        "telegram_live_notifications_allowed",
        "position_monitor_write_authority",
        "live_capital_enabled",
    ):
        if artifact.get(key) is not False:
            errors.append(f"phase5_readiness_authority_enabled:{key}")

    if errors:
        for error in errors:
            print(f"phase5_readiness_error={error}")
        print("phase5_readiness_check=failed")
        return 1

    print("phase5_readiness_check=ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
