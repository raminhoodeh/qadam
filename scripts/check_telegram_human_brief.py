#!/usr/bin/env python3
"""Validate and write Qadam's Stage 5 Telegram Human Brief."""

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
from orchestrator.telegram_human_brief import (  # noqa: E402
    TELEGRAM_HUMAN_BRIEF_FALSE_FIELDS,
    build_telegram_human_brief,
    validate_telegram_human_brief,
    write_telegram_human_brief,
)


REPORT_PATH = ROOT / "data/runtime/telegram_human_brief_check.json"


def _probe_rejected(payload: dict[str, object]) -> bool:
    try:
        validate_telegram_human_brief(payload)
    except ValueError:
        return True
    return False


def main() -> None:
    settings = Settings.from_env()
    cockpit_status = build_cockpit_status(settings)
    record = build_telegram_human_brief(
        daily_edge_findings=cockpit_status["daily_edge_findings_brief"],
        promotion_gates=cockpit_status["promotion_gates"],
        settings=settings,
        send_requested=False,
        generated_at=cockpit_status["generated_at"],
    )
    validate_telegram_human_brief(record)
    paths = write_telegram_human_brief(record, settings=settings)

    errors: list[str] = []
    if record["status"] not in {
        "telegram_human_brief_dry_run_ready",
        "telegram_human_brief_ready_to_send",
        "telegram_human_brief_already_sent",
    }:
        errors.append(f"telegram_human_brief_not_ready={record['status']}")
    if record["message_human_style_status"] != "human":
        errors.append("message_not_human")
    if record["message_specificity_status"] != "specific":
        errors.append("message_not_specific")
    if int(record["message_specificity_score"]) < 70:
        errors.append("specificity_score_below_70")
    if int(record["paragraph_count"]) not in {1, 2}:
        errors.append("paragraph_count_not_human")
    if int(record["message_technical_noise_count"]) != 0:
        errors.append("technical_noise_present")
    if int(record["message_section_header_count"]) != 0:
        errors.append("section_headers_present")
    if "quantum" not in record["body"].lower():
        errors.append("body_missing_quantum")
    if "data sources" not in record["body"].lower():
        errors.append("body_missing_data_sources")
    if "paper order" not in record["body"].lower():
        errors.append("body_missing_paper_order_boundary")
    if record["source_count"] < 30:
        errors.append("source_count_below_30")
    if record["watched_instrument_count"] < 20:
        errors.append("watched_instrument_count_below_20")
    if record["candidate_pattern_count"] < 5:
        errors.append("candidate_pattern_count_below_5")
    if record["quantum_required"] is not True:
        errors.append("quantum_not_required")
    if record["quantum_gate_passed"] is not True:
        errors.append("quantum_gate_not_passed")
    if record["promotion_gate_decision_count"] != 5:
        errors.append("promotion_gate_decision_count_not_5")
    if record["promotion_review_ready_count"] != 5:
        errors.append("promotion_review_ready_count_not_5")
    if record["human_approval_missing_count"] < 1:
        errors.append("human_approval_missing_not_visible")
    if record["live_send_attempted"] is not False:
        errors.append("live_send_attempted_without_send_request")
    if record["live_send_succeeded"] is not False:
        errors.append("live_send_succeeded_without_send_request")
    authority_leaks = [
        field for field in TELEGRAM_HUMAN_BRIEF_FALSE_FIELDS if record.get(field) is not False
    ]
    if authority_leaks:
        errors.append("authority_leaks=" + ",".join(authority_leaks))

    command_probe = deepcopy(record)
    command_probe["telegram_command_path_enabled"] = True
    command_probe_rejected = _probe_rejected(command_probe)
    if not command_probe_rejected:
        errors.append("command_probe_not_rejected")

    paper_order_probe = deepcopy(record)
    paper_order_probe["paper_order_submission_allowed"] = True
    paper_order_probe_rejected = _probe_rejected(paper_order_probe)
    if not paper_order_probe_rejected:
        errors.append("paper_order_probe_not_rejected")

    broker_probe = deepcopy(record)
    broker_probe["broker_write_allowed"] = True
    broker_probe_rejected = _probe_rejected(broker_probe)
    if not broker_probe_rejected:
        errors.append("broker_probe_not_rejected")

    strategy_probe = deepcopy(record)
    strategy_probe["active_strategy_mutation_allowed"] = True
    strategy_probe_rejected = _probe_rejected(strategy_probe)
    if not strategy_probe_rejected:
        errors.append("strategy_probe_not_rejected")

    technical_message_probe = deepcopy(record)
    technical_message_probe["body"] = (
        "Status: commit ac76fdd deployed to qadam.trade/dashboard.\n"
        "Evidence: artifact and schema changed."
    )
    technical_message_probe_rejected = _probe_rejected(technical_message_probe)
    if not technical_message_probe_rejected:
        errors.append("technical_message_probe_not_rejected")

    live_send_probe = deepcopy(record)
    live_send_probe["telegram_live_send_allowed"] = True
    live_send_probe["enabled"] = False
    live_send_probe_rejected = _probe_rejected(live_send_probe)
    if not live_send_probe_rejected:
        errors.append("live_send_probe_not_rejected")

    report = {
        "status": "ok" if not errors else "failed",
        "errors": errors,
        "record_status": record["status"],
        "brief_date": record["brief_date"],
        "message_specificity_status": record["message_specificity_status"],
        "message_specificity_score": record["message_specificity_score"],
        "message_human_style_status": record["message_human_style_status"],
        "paragraph_count": record["paragraph_count"],
        "source_count": record["source_count"],
        "watched_instrument_count": record["watched_instrument_count"],
        "candidate_pattern_count": record["candidate_pattern_count"],
        "validated_edge_count": record["validated_edge_count"],
        "quantum_review_status": record["quantum_review_status"],
        "quantum_gate_status": record["quantum_gate_status"],
        "promotion_gate_decision_count": record["promotion_gate_decision_count"],
        "promotion_review_ready_count": record["promotion_review_ready_count"],
        "promotion_gate_held_count": record["promotion_gate_held_count"],
        "human_approval_missing_count": record["human_approval_missing_count"],
        "telegram_live_send_allowed": record["telegram_live_send_allowed"],
        "live_send_attempted": record["live_send_attempted"],
        "live_send_succeeded": record["live_send_succeeded"],
        "command_probe_rejected": command_probe_rejected,
        "paper_order_probe_rejected": paper_order_probe_rejected,
        "broker_probe_rejected": broker_probe_rejected,
        "strategy_probe_rejected": strategy_probe_rejected,
        "technical_message_probe_rejected": technical_message_probe_rejected,
        "live_send_probe_rejected": live_send_probe_rejected,
        "paths": paths,
    }
    REPORT_PATH.write_text(json.dumps(report, indent=2, sort_keys=True), encoding="utf-8")
    if errors:
        raise SystemExit("; ".join(errors))

    print("telegram_human_brief_check=ok")
    print(f"telegram_human_brief_status={record['status']}")
    print(f"telegram_human_brief_date={record['brief_date']}")
    print(f"telegram_human_brief_specificity={record['message_specificity_status']}:{record['message_specificity_score']}")
    print(f"telegram_human_brief_human_style={record['message_human_style_status']}")
    print(f"telegram_human_brief_paragraph_count={record['paragraph_count']}")
    print(f"telegram_human_brief_source_count={record['source_count']}")
    print(f"telegram_human_brief_watched_instrument_count={record['watched_instrument_count']}")
    print(f"telegram_human_brief_candidate_pattern_count={record['candidate_pattern_count']}")
    print(f"telegram_human_brief_quantum_status={record['quantum_review_status']}")
    print(f"telegram_human_brief_quantum_gate_status={record['quantum_gate_status']}")
    print(f"telegram_human_brief_promotion_review_ready_count={record['promotion_review_ready_count']}")
    print(f"telegram_human_brief_promotion_held_count={record['promotion_gate_held_count']}")
    print(f"telegram_human_brief_live_send_allowed={record['telegram_live_send_allowed']}")
    print(f"telegram_human_brief_live_send_attempted={record['live_send_attempted']}")
    print(f"telegram_human_brief_artifact_path={paths['output_path']}")


if __name__ == "__main__":
    main()
