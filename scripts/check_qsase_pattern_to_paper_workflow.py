#!/usr/bin/env python3
"""Validate the QSASE pattern-to-paper workflow dashboard artifact."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from orchestrator.config import Settings
from orchestrator.qsase_dashboard_view_model import (
    PATTERN_TO_PAPER_WORKFLOW_ARTIFACT,
    _runtime_dir,
    build_and_write_dashboard_view_model,
)
from orchestrator.qsase_telegram_notification_boundary import score_qsase_telegram_message


def main() -> int:
    settings = Settings.from_env()
    payload, written, errors = build_and_write_dashboard_view_model(settings)
    runtime_dir = _runtime_dir(settings)
    workflow = payload.get("pattern_to_paper_workflow", {})
    validation_errors = list(errors)

    if not (runtime_dir / PATTERN_TO_PAPER_WORKFLOW_ARTIFACT).exists():
        validation_errors.append("pattern_to_paper_workflow_artifact_missing")
    if workflow.get("artifact_type") != "qsase_pattern_to_paper_workflow":
        validation_errors.append("pattern_to_paper_workflow_artifact_type_invalid")
    if workflow.get("public_safe") is not True or workflow.get("read_only") is not True:
        validation_errors.append("pattern_to_paper_workflow_public_readonly_boundary_missing")
    if int(workflow.get("recognized_pattern_count") or 0) <= 0:
        validation_errors.append("recognized_pattern_count_missing")
    if int(workflow.get("documented_thesis_count") or 0) != len(workflow.get("records", [])):
        validation_errors.append("documented_thesis_count_mismatch")

    for field in (
        "paper_order_allowed",
        "trade_candidate_created",
        "qualified_setup_created",
        "broker_write_allowed",
        "proof_credit_allowed",
        "live_capital_enabled",
    ):
        if workflow.get(field) is not False:
            validation_errors.append(f"{field}_must_be_false")
    for field in ("paper_order_created_count", "broker_write_count"):
        if int(workflow.get(field, -1) or 0) != 0:
            validation_errors.append(f"{field}_must_be_zero")

    for record in workflow.get("records", []):
        record_id = record.get("workflow_id")
        for field in ("pattern_thesis", "qualitative_summary", "source_packet_summary", "invalidation", "next_allowed_action"):
            if not record.get(field):
                validation_errors.append(f"record_{record_id}_missing_{field}")
        for field in (
            "paper_order_allowed",
            "paper_order_created",
            "trade_candidate_created",
            "qualified_setup_created",
            "broker_write_allowed",
            "proof_credit_allowed",
            "live_capital_enabled",
        ):
            if record.get(field) is not False:
                validation_errors.append(f"record_{record_id}_{field}_must_be_false")
        telegram = record.get("telegram_summary", {})
        if telegram.get("live_send_allowed") is not False or telegram.get("command_disabled") is not True:
            validation_errors.append(f"record_{record_id}_telegram_boundary_invalid")

    telegram_candidate = workflow.get("telegram_candidate", {})
    if telegram_candidate.get("telegram_live_send_allowed") is not False:
        validation_errors.append("workflow_telegram_live_send_allowed_must_be_false")
    if telegram_candidate.get("telegram_command_path_enabled") is not False:
        validation_errors.append("workflow_telegram_command_path_must_be_false")
    quality = score_qsase_telegram_message(
        {
            "title": "Qadam pattern note",
            "body": telegram_candidate.get("body", ""),
            "source_artifact_refs": workflow.get("artifact_refs", []),
            "strategy_family": "pattern_to_paper_workflow",
        }
    )
    if quality.get("specificity_status") != "specific":
        validation_errors.append("workflow_telegram_message_not_specific")
    if quality.get("human_style_status") != "human":
        validation_errors.append("workflow_telegram_message_not_human")
    if quality.get("unsafe_rejected"):
        validation_errors.append("workflow_telegram_message_unsafe")

    print(f"pattern_to_paper_workflow={written.get('pattern_to_paper_workflow')}")
    print(f"status={workflow.get('status')}")
    print(f"workflow_state={workflow.get('workflow_state')}")
    print(f"recognized_pattern_count={workflow.get('recognized_pattern_count')}")
    print(f"documented_thesis_count={workflow.get('documented_thesis_count')}")
    print(f"telegram_candidate_count={workflow.get('telegram_candidate_count')}")
    print(f"paperops_handoff_candidate_count={workflow.get('paperops_handoff_candidate_count')}")
    print(f"paper_order_created_count={workflow.get('paper_order_created_count')}")
    print(f"broker_write_count={workflow.get('broker_write_count')}")

    if validation_errors:
        for error in sorted(set(validation_errors)):
            print(f"error={error}")
        return 1
    print("qsase_pattern_to_paper_workflow_check=ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
