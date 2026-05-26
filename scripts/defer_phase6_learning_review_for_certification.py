#!/usr/bin/env python3
"""Explicitly defer Q6 learning review and refresh Phase 6 certification."""

from __future__ import annotations

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from orchestrator.cockpit_status import export_cockpit_status  # noqa: E402
from orchestrator.config import Settings  # noqa: E402
from orchestrator.phase6_architect_learning import (  # noqa: E402
    build_phase6_architect_learning,
    validate_phase6_architect_learning,
    write_phase6_architect_learning,
)
from orchestrator.phase6_certification import (  # noqa: E402
    build_phase6_certification,
    validate_phase6_certification,
    write_phase6_certification,
)
from orchestrator.phase6_cockpit_visibility import (  # noqa: E402
    build_phase6_cockpit_visibility,
    validate_phase6_cockpit_visibility,
    write_phase6_cockpit_visibility,
)
from orchestrator.phase6_knowledge_graph_read_path import (  # noqa: E402
    build_phase6_knowledge_graph_read_path,
    validate_phase6_knowledge_graph_read_path,
    write_phase6_knowledge_graph_read_path,
)
from orchestrator.phase6_knowledge_graph_staging import (  # noqa: E402
    build_phase6_knowledge_graph_staging,
    validate_phase6_knowledge_graph_staging,
    write_phase6_knowledge_graph_staging,
)
from orchestrator.phase6_learning_approval import (  # noqa: E402
    build_phase6_learning_approval,
    explicitly_defer_phase6_learning_approval,
    validate_phase6_learning_approval,
    write_phase6_learning_approval,
)
from orchestrator.phase6_model_weight_updates import (  # noqa: E402
    build_phase6_model_weight_updates,
    validate_phase6_model_weight_updates,
    write_phase6_model_weight_updates,
)
from orchestrator.phase6_shadow_strategy_runner import (  # noqa: E402
    build_phase6_shadow_strategy_runner,
    validate_phase6_shadow_strategy_runner,
    write_phase6_shadow_strategy_runner,
)
from orchestrator.phase6_trust_score_updates import (  # noqa: E402
    build_phase6_trust_score_updates,
    validate_phase6_trust_score_updates,
    write_phase6_trust_score_updates,
)


REVIEW_INSTRUCTION = (
    "Fund Manager instruction in the Codex thread on 2026-05-25: resolve or "
    "explicitly defer the pending Q6 learning approval/postmortem review, then "
    "rerun Q6-17 until it can certify Phase 6. This records an explicit "
    "deferral of all pending Q6 learning actions and the scoped postmortem "
    "review; it does not approve learning writes, Knowledge Graph commits, "
    "model-weight or trust-score application, strategy/policy mutation, broker "
    "writes, live capital, or Phase 7 proof credit."
)


def main() -> int:
    settings = Settings.from_env()
    errors: list[str] = []

    approval = explicitly_defer_phase6_learning_approval(
        build_phase6_learning_approval(settings=settings),
        reviewer_label="fund_manager_ramin",
        review_instruction=REVIEW_INSTRUCTION,
    )
    approval_path, approval_history, approval_event, approval = write_phase6_learning_approval(
        approval,
        settings=settings,
        record_event=True,
    )
    approval_errors = validate_phase6_learning_approval(approval)
    errors.extend(approval_errors)

    kg_staging = build_phase6_knowledge_graph_staging(settings=settings)
    kg_staging_path, kg_staging_history, kg_staging_event, kg_staging = (
        write_phase6_knowledge_graph_staging(
            kg_staging,
            settings=settings,
            record_event=True,
        )
    )
    kg_staging_errors = validate_phase6_knowledge_graph_staging(kg_staging)
    errors.extend(kg_staging_errors)

    kg_read = build_phase6_knowledge_graph_read_path(settings=settings)
    kg_read_path, kg_read_history, kg_read_event, kg_read = (
        write_phase6_knowledge_graph_read_path(
            kg_read,
            settings=settings,
            record_event=True,
        )
    )
    kg_read_errors = validate_phase6_knowledge_graph_read_path(kg_read)
    errors.extend(kg_read_errors)

    model_weight = build_phase6_model_weight_updates(settings=settings)
    model_path, model_history, model_event, model_weight = write_phase6_model_weight_updates(
        model_weight,
        settings=settings,
        record_event=True,
    )
    model_errors = validate_phase6_model_weight_updates(model_weight)
    errors.extend(model_errors)

    trust_score = build_phase6_trust_score_updates(settings=settings)
    trust_path, trust_history, trust_event, trust_score = write_phase6_trust_score_updates(
        trust_score,
        settings=settings,
        record_event=True,
    )
    trust_errors = validate_phase6_trust_score_updates(trust_score)
    errors.extend(trust_errors)

    shadow = build_phase6_shadow_strategy_runner(settings=settings)
    shadow_path, shadow_history, shadow_event, shadow = write_phase6_shadow_strategy_runner(
        shadow,
        settings=settings,
        record_event=True,
    )
    shadow_errors = validate_phase6_shadow_strategy_runner(shadow)
    errors.extend(shadow_errors)

    architect = build_phase6_architect_learning(settings=settings)
    architect_path, architect_history, architect_event, architect = (
        write_phase6_architect_learning(
            architect,
            settings=settings,
            record_event=True,
        )
    )
    architect_errors = validate_phase6_architect_learning(architect)
    errors.extend(architect_errors)

    visibility = build_phase6_cockpit_visibility(settings=settings)
    visibility_path, visibility_history, visibility_event, visibility = (
        write_phase6_cockpit_visibility(
            visibility,
            settings=settings,
            record_event=True,
        )
    )
    visibility_errors = validate_phase6_cockpit_visibility(visibility)
    errors.extend(visibility_errors)

    certification = build_phase6_certification(settings=settings)
    cert_path, cert_history, cert_event, certification = write_phase6_certification(
        certification,
        settings=settings,
        record_event=True,
    )
    cert_errors = validate_phase6_certification(certification)
    errors.extend(cert_errors)

    cockpit_export = export_cockpit_status(
        settings=settings,
        landing_repo_path=ROOT / "landing-page-repo",
    )

    print(f"phase6_learning_review_deferral_approval_path={approval_path}")
    print(f"phase6_learning_review_deferral_approval_history_path={approval_history}")
    print(f"phase6_learning_review_deferral_approval_event_path={approval_event}")
    print(f"phase6_learning_review_deferral_approval_state={approval['approval_state']}")
    print(f"phase6_learning_review_deferral_approval_logged={approval['approval_logged']}")
    print(f"phase6_learning_review_deferral_reviewer_label={approval['reviewer_label']}")
    print(
        "phase6_learning_review_deferral_deferred_action_count="
        f"{approval['deferred_action_count']}"
    )
    print(
        "phase6_learning_review_deferral_pending_review_action_count="
        f"{approval['pending_review_action_count']}"
    )
    print(f"phase6_learning_review_deferral_approval_error_count={len(approval_errors)}")
    print(f"phase6_learning_review_deferral_kg_staging_path={kg_staging_path}")
    print(f"phase6_learning_review_deferral_kg_staging_history_path={kg_staging_history}")
    print(f"phase6_learning_review_deferral_kg_staging_event_path={kg_staging_event}")
    print(f"phase6_learning_review_deferral_kg_staging_state={kg_staging['kg_write_state']}")
    print(f"phase6_learning_review_deferral_kg_staging_error_count={len(kg_staging_errors)}")
    print(f"phase6_learning_review_deferral_kg_read_path={kg_read_path}")
    print(f"phase6_learning_review_deferral_kg_read_history_path={kg_read_history}")
    print(f"phase6_learning_review_deferral_kg_read_event_path={kg_read_event}")
    print(f"phase6_learning_review_deferral_kg_read_state={kg_read['read_view_state']}")
    print(f"phase6_learning_review_deferral_kg_read_error_count={len(kg_read_errors)}")
    print(f"phase6_learning_review_deferral_model_path={model_path}")
    print(f"phase6_learning_review_deferral_model_history_path={model_history}")
    print(f"phase6_learning_review_deferral_model_event_path={model_event}")
    print(f"phase6_learning_review_deferral_model_error_count={len(model_errors)}")
    print(f"phase6_learning_review_deferral_trust_path={trust_path}")
    print(f"phase6_learning_review_deferral_trust_history_path={trust_history}")
    print(f"phase6_learning_review_deferral_trust_event_path={trust_event}")
    print(f"phase6_learning_review_deferral_trust_error_count={len(trust_errors)}")
    print(f"phase6_learning_review_deferral_shadow_path={shadow_path}")
    print(f"phase6_learning_review_deferral_shadow_history_path={shadow_history}")
    print(f"phase6_learning_review_deferral_shadow_event_path={shadow_event}")
    print(f"phase6_learning_review_deferral_shadow_error_count={len(shadow_errors)}")
    print(f"phase6_learning_review_deferral_architect_path={architect_path}")
    print(f"phase6_learning_review_deferral_architect_history_path={architect_history}")
    print(f"phase6_learning_review_deferral_architect_event_path={architect_event}")
    print(f"phase6_learning_review_deferral_architect_error_count={len(architect_errors)}")
    print(f"phase6_learning_review_deferral_visibility_path={visibility_path}")
    print(f"phase6_learning_review_deferral_visibility_history_path={visibility_history}")
    print(f"phase6_learning_review_deferral_visibility_event_path={visibility_event}")
    print(f"phase6_learning_review_deferral_visibility_state={visibility['learning_state']}")
    print(f"phase6_learning_review_deferral_visibility_error_count={len(visibility_errors)}")
    print(f"phase6_learning_review_deferral_certification_path={cert_path}")
    print(f"phase6_learning_review_deferral_certification_history_path={cert_history}")
    print(f"phase6_learning_review_deferral_certification_event_path={cert_event}")
    print(f"phase6_learning_review_deferral_certification_status={certification['status']}")
    print(
        "phase6_learning_review_deferral_phase6_certified="
        f"{certification['phase6_certified']}"
    )
    print(
        "phase6_learning_review_deferral_phase6_exit_gate="
        f"{certification['phase6_exit_gate']}"
    )
    print(
        "phase6_learning_review_deferral_phase7_demo_proof_planning_allowed="
        f"{certification['phase7_demo_proof_planning_allowed']}"
    )
    print(
        "phase6_learning_review_deferral_phase7_proof_credit_allowed="
        f"{certification['phase7_proof_credit_allowed']}"
    )
    print(
        "phase6_learning_review_deferral_phase5_test_trades_count_for_phase7="
        f"{certification['phase5_test_trades_count_for_phase7']}"
    )
    print(
        "phase6_learning_review_deferral_certification_blocker_count="
        f"{certification['certification_blocker_count']}"
    )
    print(f"phase6_learning_review_deferral_certification_error_count={len(cert_errors)}")
    print(f"cockpit_status_runtime_path={cockpit_export['runtime_path']}")
    print(f"cockpit_status_landing_path={cockpit_export['landing_path']}")

    if approval["approval_state"] != "deferred":
        errors.append("phase6_learning_review_deferral_not_recorded")
    if approval["approval_logged"] is not True:
        errors.append("phase6_learning_review_deferral_not_logged")
    if approval["pending_review_action_count"] != 0:
        errors.append("phase6_learning_review_deferral_pending_actions_remain")
    if certification["phase6_certified"] is not True:
        errors.append("phase6_certification_not_certified_after_deferral")
    if certification["phase6_exit_gate"] is not True:
        errors.append("phase6_exit_gate_not_open_after_deferral")
    if certification["phase7_demo_proof_planning_allowed"] is not True:
        errors.append("phase7_demo_planning_not_allowed_after_deferral")
    if certification["phase7_proof_credit_allowed"] is not False:
        errors.append("phase7_proof_credit_allowed_after_deferral")
    if certification["phase5_test_trades_count_for_phase7"] is not False:
        errors.append("phase5_test_trades_counted_for_phase7")

    if errors:
        for error in sorted(set(errors)):
            print(f"phase6_learning_review_deferral_error={error}")
        print("phase6_learning_review_deferral=failed")
        return 1

    print("phase6_learning_review_deferral=ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
