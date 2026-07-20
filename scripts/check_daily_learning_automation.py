#!/usr/bin/env python3
"""Validate and write Qadam's Stage 6 daily learning automation artifacts."""

from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from orchestrator.cockpit_status import build_cockpit_status  # noqa: E402
from orchestrator.config import Settings  # noqa: E402
from orchestrator.daily_edge_findings import (  # noqa: E402
    build_daily_edge_findings_brief,
    validate_daily_edge_findings_brief,
    write_daily_edge_findings_brief,
)
from orchestrator.daily_learning_automation import (  # noqa: E402
    build_daily_learning_automation,
    validate_daily_learning_automation,
    write_daily_learning_automation,
)
from orchestrator.daily_telegram_learning_brief import (  # noqa: E402
    build_daily_telegram_learning_brief,
    validate_daily_telegram_learning_brief,
    write_daily_telegram_learning_brief,
)
from orchestrator.telegram_human_brief import (  # noqa: E402
    TELEGRAM_HUMAN_BRIEF_FALSE_FIELDS,
    build_telegram_human_brief,
    validate_telegram_human_brief,
    write_telegram_human_brief,
)


REPORT_PATH = ROOT / "data/runtime/daily_learning_automation_check.json"


def _probe_rejected(validator, payload: dict[str, object]) -> bool:
    try:
        validator(payload)
    except ValueError:
        return True
    return False


def main() -> None:
    settings = Settings.from_env()
    cockpit_status = build_cockpit_status(settings)
    generated_at = cockpit_status["generated_at"]
    daily_findings = build_daily_edge_findings_brief(
        cockpit_status=cockpit_status,
        generated_at=generated_at,
    )
    validate_daily_edge_findings_brief(daily_findings)
    daily_paths = write_daily_edge_findings_brief(daily_findings, settings=settings)

    human_brief = build_telegram_human_brief(
        daily_edge_findings=daily_findings,
        promotion_gates=cockpit_status["promotion_gates"],
        settings=settings,
        send_requested=False,
        generated_at=generated_at,
    )
    validate_telegram_human_brief(human_brief)
    human_paths = write_telegram_human_brief(human_brief, settings=settings)

    learning_brief = build_daily_telegram_learning_brief(
        daily_edge_findings=daily_findings,
        promotion_gates=cockpit_status["promotion_gates"],
        settings=settings,
        send_requested=False,
        force_delivery_window=True,
        generated_at=generated_at,
    )
    validate_daily_telegram_learning_brief(learning_brief)
    learning_paths = write_daily_telegram_learning_brief(learning_brief, settings=settings)

    automation = build_daily_learning_automation(
        daily_edge_findings=daily_findings,
        daily_telegram_learning_brief=learning_brief,
        settings=settings,
        send_requested=False,
        force_delivery_window=True,
        generated_at=generated_at,
    )
    validate_daily_learning_automation(automation)
    automation_paths = write_daily_learning_automation(automation, settings=settings)

    errors: list[str] = []
    expected_statuses = {
        "daily_learning_automation_dry_run_ready",
        "daily_learning_automation_ready_to_send",
        "daily_learning_automation_sent",
        "daily_learning_automation_already_sent",
    }
    if automation["status"] not in expected_statuses:
        errors.append(f"daily_learning_automation_not_ready={automation['status']}")
    expected_learning_statuses = {
        "daily_telegram_learning_brief_dry_run_ready",
        "daily_telegram_learning_brief_ready_to_send",
        "daily_telegram_learning_brief_sent",
        "daily_telegram_learning_brief_already_sent",
    }
    if learning_brief["status"] not in expected_learning_statuses:
        errors.append(f"daily_telegram_learning_brief_not_ready={learning_brief['status']}")
    if learning_brief["message_human_style_status"] != "human":
        errors.append("daily_telegram_learning_brief_not_human")
    if learning_brief["message_specificity_status"] != "specific":
        errors.append("daily_telegram_learning_brief_not_specific")
    if int(learning_brief["message_specificity_score"]) < 70:
        errors.append("daily_telegram_learning_brief_specificity_low")
    if int(learning_brief["paragraph_count"]) not in {1, 2}:
        errors.append("daily_telegram_learning_brief_paragraph_count_invalid")
    for phrase in ("learning", "quantum", "data sources", "paper order"):
        if phrase not in learning_brief["body"].lower():
            errors.append(f"daily_telegram_learning_brief_missing_{phrase.replace(' ', '_')}")
    if automation["due_or_forced"] is not True:
        errors.append("daily_learning_automation_not_due_or_forced")
    if automation["quantum_gate_passed"] is not True:
        errors.append("daily_learning_automation_quantum_gate_not_passed")
    if automation["source_count"] < 30:
        errors.append("daily_learning_automation_source_count_low")
    if automation["watched_instrument_count"] < 19:
        errors.append("daily_learning_automation_watched_count_low")
    if automation["candidate_pattern_count"] < 5:
        errors.append("daily_learning_automation_candidate_count_low")
    if automation["strategy_learning_applied_count"] != 0:
        errors.append("daily_learning_automation_applied_learning")
    if learning_brief["strategy_learning_applied_count"] != 0:
        errors.append("daily_telegram_learning_brief_applied_learning")
    if automation["live_send_attempted"] is not False:
        errors.append("daily_learning_automation_attempted_live_send")
    if learning_brief["live_send_attempted"] is not False:
        errors.append("daily_telegram_learning_brief_attempted_live_send")

    automation_authority_leaks = [
        field for field in TELEGRAM_HUMAN_BRIEF_FALSE_FIELDS if automation.get(field) is not False
    ]
    learning_authority_leaks = [
        field for field in TELEGRAM_HUMAN_BRIEF_FALSE_FIELDS if learning_brief.get(field) is not False
    ]
    if automation_authority_leaks:
        errors.append("automation_authority_leaks=" + ",".join(automation_authority_leaks))
    if learning_authority_leaks:
        errors.append("learning_brief_authority_leaks=" + ",".join(learning_authority_leaks))

    command_probe = deepcopy(learning_brief)
    command_probe["telegram_command_path_enabled"] = True
    command_probe_rejected = _probe_rejected(validate_daily_telegram_learning_brief, command_probe)
    if not command_probe_rejected:
        errors.append("learning_command_probe_not_rejected")

    paper_order_probe = deepcopy(learning_brief)
    paper_order_probe["paper_order_submission_allowed"] = True
    paper_order_probe_rejected = _probe_rejected(
        validate_daily_telegram_learning_brief,
        paper_order_probe,
    )
    if not paper_order_probe_rejected:
        errors.append("learning_paper_order_probe_not_rejected")

    quantum_probe = deepcopy(automation)
    quantum_probe["quantum_gate_passed"] = False
    quantum_probe_rejected = _probe_rejected(validate_daily_learning_automation, quantum_probe)
    if not quantum_probe_rejected:
        errors.append("automation_quantum_probe_not_rejected")

    live_capital_probe = deepcopy(automation)
    live_capital_probe["live_capital_enabled"] = True
    live_capital_probe_rejected = _probe_rejected(
        validate_daily_learning_automation,
        live_capital_probe,
    )
    if not live_capital_probe_rejected:
        errors.append("automation_live_capital_probe_not_rejected")

    strategy_probe = deepcopy(automation)
    strategy_probe["active_strategy_mutation_allowed"] = True
    strategy_probe_rejected = _probe_rejected(validate_daily_learning_automation, strategy_probe)
    if not strategy_probe_rejected:
        errors.append("automation_strategy_probe_not_rejected")

    technical_message_probe = deepcopy(learning_brief)
    technical_message_probe["body"] = (
        "Status: stage 6 commit deployed.\n"
        "Evidence: artifact path data/runtime/daily_learning_automation.json."
    )
    technical_message_probe_rejected = _probe_rejected(
        validate_daily_telegram_learning_brief,
        technical_message_probe,
    )
    if not technical_message_probe_rejected:
        errors.append("learning_technical_message_probe_not_rejected")

    report = {
        "status": "ok" if not errors else "failed",
        "errors": errors,
        "automation_status": automation["status"],
        "learning_brief_status": learning_brief["status"],
        "local_date": automation["local_date"],
        "timezone": automation["timezone"],
        "delivery_after_local_time": automation["delivery_after_local_time"],
        "due_or_forced": automation["due_or_forced"],
        "source_count": automation["source_count"],
        "watched_instrument_count": automation["watched_instrument_count"],
        "candidate_pattern_count": automation["candidate_pattern_count"],
        "validated_edge_count": automation["validated_edge_count"],
        "quantum_gate_status": automation["quantum_gate_status"],
        "message_specificity_score": learning_brief["message_specificity_score"],
        "message_human_style_status": learning_brief["message_human_style_status"],
        "promotion_review_ready_count": automation["promotion_review_ready_count"],
        "promotion_gate_held_count": automation["promotion_gate_held_count"],
        "live_send_attempted": automation["live_send_attempted"],
        "live_send_succeeded": automation["live_send_succeeded"],
        "command_probe_rejected": command_probe_rejected,
        "paper_order_probe_rejected": paper_order_probe_rejected,
        "quantum_probe_rejected": quantum_probe_rejected,
        "live_capital_probe_rejected": live_capital_probe_rejected,
        "strategy_probe_rejected": strategy_probe_rejected,
        "technical_message_probe_rejected": technical_message_probe_rejected,
        "paths": {
            "daily_edge_findings": daily_paths,
            "telegram_human_brief": human_paths,
            "daily_telegram_learning_brief": learning_paths,
            "daily_learning_automation": automation_paths,
        },
    }
    REPORT_PATH.write_text(json.dumps(report, indent=2, sort_keys=True), encoding="utf-8")
    if errors:
        raise SystemExit("; ".join(errors))

    print("daily_learning_automation_check=ok")
    print(f"daily_learning_automation_status={automation['status']}")
    print(f"daily_learning_automation_local_date={automation['local_date']}")
    print(f"daily_learning_automation_timezone={automation['timezone']}")
    print(f"daily_learning_automation_due_or_forced={automation['due_or_forced']}")
    print(f"daily_learning_automation_learning_brief_status={learning_brief['status']}")
    print(
        "daily_learning_automation_learning_brief_specificity="
        f"{learning_brief['message_specificity_status']}:{learning_brief['message_specificity_score']}"
    )
    print(
        "daily_learning_automation_learning_brief_human_style="
        f"{learning_brief['message_human_style_status']}"
    )
    print(f"daily_learning_automation_source_count={automation['source_count']}")
    print(
        "daily_learning_automation_watched_instrument_count="
        f"{automation['watched_instrument_count']}"
    )
    print(
        "daily_learning_automation_candidate_pattern_count="
        f"{automation['candidate_pattern_count']}"
    )
    print(f"daily_learning_automation_quantum_gate_status={automation['quantum_gate_status']}")
    print(f"daily_learning_automation_promotion_review_ready_count={automation['promotion_review_ready_count']}")
    print(f"daily_learning_automation_promotion_held_count={automation['promotion_gate_held_count']}")
    print(f"daily_learning_automation_live_send_attempted={automation['live_send_attempted']}")
    print(f"daily_learning_automation_live_send_succeeded={automation['live_send_succeeded']}")
    print(f"daily_learning_automation_artifact_path={automation_paths['output_path']}")
    print(f"daily_telegram_learning_brief_artifact_path={learning_paths['output_path']}")


if __name__ == "__main__":
    main()
