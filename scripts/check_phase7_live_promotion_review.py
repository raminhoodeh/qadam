#!/usr/bin/env python3
"""Validate Q7-18 Phase 7 live-promotion review flow."""

from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from orchestrator.config import Settings  # noqa: E402
from orchestrator.event_log import EventLog  # noqa: E402
from orchestrator.phase7_certification import (  # noqa: E402
    build_phase7_certification,
    write_phase7_certification,
)
from orchestrator.phase7_live_promotion_review import (  # noqa: E402
    PHASE7_LIVE_PROMOTION_COOLING_OFF_HOURS,
    PHASE7_LIVE_PROMOTION_REVIEW_SCHEMA_VERSION,
    PHASE7_LIVE_PROMOTION_REVIEW_SECTIONS,
    PUBLIC_STATUS_FIELDS,
    build_phase7_live_promotion_review,
    phase7_live_promotion_review_paths,
    validate_phase7_live_promotion_review,
    write_phase7_live_promotion_review,
)
from orchestrator.phase7_readiness import (  # noqa: E402
    PHASE7_HARNESS_DAY_COUNT,
    PHASE7_MATURE_CLOSED_TRADE_BENCHMARK,
)


def _read_json(path: Path) -> dict[str, object]:
    if not path.exists():
        return {}
    payload = json.loads(path.read_text(encoding="utf-8"))
    return payload if isinstance(payload, dict) else {}


def _sync_public_status(artifact: dict[str, object]) -> dict[str, object]:
    probe = deepcopy(artifact)
    probe["public_status"] = {
        field: deepcopy(probe.get(field))
        for field in PUBLIC_STATUS_FIELDS
        if field in probe
    }
    probe["public_status"]["validation_error_count"] = len(
        probe.get("validation_errors", []) or []
    )
    return probe


def _ready_probe(artifact: dict[str, object]) -> dict[str, object]:
    probe = deepcopy(artifact)
    probe.update(
        {
            "status": "read_only",
            "stage_status": "live_promotion_review_packet_ready",
            "live_promotion_review_state": "read_only_packet_ready_for_human_review",
            "source_certification_status": "certified",
            "source_certification_stage_status": "phase7_demo_proof_certified",
            "source_certification_validation_error_count": 0,
            "phase7_demo_proof_certified": True,
            "phase7_demo_proof_exit_gate": True,
            "phase7_30_day_operational_result_clean": True,
            "phase7_30_day_operational_result_preserved": True,
            "phase7_30_day_run_complete": True,
            "completed_calendar_day_count": PHASE7_HARNESS_DAY_COUNT,
            "phase7_harness_day_count": PHASE7_HARNESS_DAY_COUNT,
            "proof_week_count": 5,
            "weekly_review_packet_created_count": 5,
            "qualified_setup_count": 15,
            "evaluated_trade_count": 100,
            "expectancy_after_costs_positive": True,
            "drawdown_within_cap": True,
            "drawdown_cap_breached": False,
            "risk_halt_active": False,
            "manual_trade_level_override_count": 0,
            "sample_contaminated": False,
            "closed_proof_trade_count": 100,
            "postmortem_due_count": 100,
            "postmortem_missing_count": 0,
            "postmortem_reviewed_count": 100,
            "source_signal_chains_complete": True,
            "maturity_state": "statistically_mature",
            "maturity_classification": "statistically_mature_100_closed_trades",
            "mature_benchmark": PHASE7_MATURE_CLOSED_TRADE_BENCHMARK,
            "phase7_mature_benchmark_met": True,
            "phase7_statistically_immature": False,
            "phase7_statistical_immaturity_hidden": False,
            "certification_blocker_count": 0,
            "certification_blockers": [],
            "q7_18_live_promotion_review_stage_allowed": True,
            "live_promotion_review_packet_draft_allowed": True,
            "live_promotion_review_packet_created": True,
            "live_promotion_review_packet_section_count": len(
                PHASE7_LIVE_PROMOTION_REVIEW_SECTIONS
            ),
            "live_promotion_review_packet_sections": list(
                PHASE7_LIVE_PROMOTION_REVIEW_SECTIONS
            ),
            "cooling_off_required": True,
            "cooling_off_period_hours": PHASE7_LIVE_PROMOTION_COOLING_OFF_HOURS,
            "cooling_off_started_at": None,
            "cooling_off_ends_at": None,
            "cooling_off_complete": False,
            "live_promotion_approval_state": "not_requested",
            "live_promotion_approval_allowed": False,
            "ramins_explicit_approval_required": True,
            "fund_manager_review_required": True,
            "live_credentials_enabled": False,
            "live_credentials_loaded": False,
            "live_credentials_required_for_review": False,
            "live_credentials_write_allowed": False,
            "live_capital_enabled": False,
            "live_broker_write_allowed": False,
            "phase7_proof_credit_allowed": False,
            "phase5_test_trades_count_for_phase7": False,
            "broker_post_called_count": 0,
            "alpaca_post_called_count": 0,
            "broker_write_allowed_count": 0,
            "prediction_market_write_allowed_count": 0,
            "crypto_perps_write_allowed_count": 0,
            "live_endpoint_allowed_count": 0,
            "live_capital_enabled_count": 0,
            "phase7_proof_credit_allowed_count": 0,
            "phase5_test_trade_reuse_count": 0,
            "ui_inferred_readiness_count": 0,
            "unsafe_write_counter_total": 0,
            "raw_payload_exposed_count": 0,
            "private_payload_exposed_count": 0,
            "local_path_exposed_count": 0,
            "secret_ref_exposed_count": 0,
            "broker_identifier_exposed_count": 0,
            "operational_incident_count": 0,
            "operational_incidents": [],
            "blockers": [],
            "blocker_count": 0,
            "recommended_next_stage": (
                "Hold read-only packet for Ramin review, cooling-off, and a later explicit live gate"
            ),
            "validation_errors": [],
        }
    )
    probe["authority_ledger"]["q7_18_live_promotion_review_stage_allowed"] = True
    probe["review_packet"] = {
        "packet_id": "phase7:q7-18:live-promotion-review-packet",
        "packet_owner": "Ramin",
        "created_at": str(probe["generated_at"]),
        "review_state": "read_only_human_review_required",
        "sections": list(PHASE7_LIVE_PROMOTION_REVIEW_SECTIONS),
        "phase7_evidence_summary": {
            "phase7_demo_proof_certified": True,
            "completed_calendar_day_count": PHASE7_HARNESS_DAY_COUNT,
            "closed_proof_trade_count": 100,
            "expectancy_after_costs_positive": True,
        },
        "maturity_summary": {
            "maturity_state": "statistically_mature",
            "mature_benchmark": PHASE7_MATURE_CLOSED_TRADE_BENCHMARK,
            "phase7_mature_benchmark_met": True,
            "phase7_statistical_immaturity_hidden": False,
        },
        "drawdown_summary": {
            "drawdown_within_cap": True,
            "drawdown_cap_breached": False,
            "risk_halt_active": False,
        },
        "override_summary": {
            "sample_contaminated": False,
            "manual_trade_level_override_count": 0,
        },
        "postmortem_summary": {
            "postmortem_due_count": 100,
            "postmortem_missing_count": 0,
            "postmortem_reviewed_count": 100,
        },
        "source_health_summary": {
            "source_artifact_count": probe["source_artifact_count"],
            "source_missing_count": 0,
            "source_validation_error_count": 0,
            "complete_decision_chain_count": 100,
            "missing_decision_chain_count": 0,
            "private_priors_only_proof_trade_count": 0,
            "backend_derived": True,
        },
        "weekly_review_summary": {
            "weekly_review_packet_created_count": 5,
            "all_proof_weeks_have_review_packet": True,
            "future_policy_comment_allowed": True,
            "trade_level_intervention_allowed": False,
            "trade_level_intervention_count": 0,
        },
        "operational_incident_summary": {
            "operational_incident_count": 0,
            "operational_incidents": [],
            "lifecycle_event_count": 100,
            "source_closed_proof_trade_count": 100,
            "performance_evaluated_trade_count": 100,
            "risk_halt_active": False,
            "sample_contaminated": False,
        },
        "cooling_off_summary": {
            "cooling_off_required": True,
            "cooling_off_period_hours": PHASE7_LIVE_PROMOTION_COOLING_OFF_HOURS,
            "cooling_off_started_at": None,
            "cooling_off_ends_at": None,
            "cooling_off_complete": False,
        },
        "approval_summary": {
            "live_promotion_approval_state": "not_requested",
            "ramins_explicit_approval_required": True,
            "fund_manager_review_required": True,
            "live_promotion_approval_allowed": False,
        },
        "live_lockout_summary": {
            "live_credentials_enabled": False,
            "live_credentials_loaded": False,
            "live_credentials_required_for_review": False,
            "live_credentials_write_allowed": False,
            "live_capital_enabled": False,
            "live_broker_write_allowed": False,
        },
    }
    return _sync_public_status(probe)


def main() -> int:
    errors: list[str] = []
    settings = Settings.from_env()
    output_path, history_path, event_log_path = phase7_live_promotion_review_paths(
        settings
    )
    if event_log_path.exists():
        event_log_path.unlink()

    certification = build_phase7_certification(settings=settings)
    write_phase7_certification(certification, settings=settings, record_event=True)

    artifact = build_phase7_live_promotion_review(settings=settings)
    output_path, history_path, event_log_path, written = write_phase7_live_promotion_review(
        artifact,
        settings=settings,
        record_event=True,
        event_log_path=event_log_path,
    )
    validation_errors = validate_phase7_live_promotion_review(written)
    runtime_copy = _read_json(output_path)
    replay = EventLog(event_log_path, echo=False).replay()

    ready_errors = validate_phase7_live_promotion_review(_ready_probe(written))

    early_q7_18_probe = deepcopy(written)
    early_q7_18_probe["q7_18_live_promotion_review_stage_allowed"] = True
    early_q7_18_probe["authority_ledger"]["q7_18_live_promotion_review_stage_allowed"] = True
    early_q7_18_errors = validate_phase7_live_promotion_review(early_q7_18_probe)

    blocked_packet_probe = deepcopy(written)
    blocked_packet_probe["live_promotion_review_packet_draft_allowed"] = True
    blocked_packet_probe["live_promotion_review_packet_created"] = True
    blocked_packet_probe["live_promotion_review_packet_section_count"] = len(
        PHASE7_LIVE_PROMOTION_REVIEW_SECTIONS
    )
    blocked_packet_probe["live_promotion_review_packet_sections"] = list(
        PHASE7_LIVE_PROMOTION_REVIEW_SECTIONS
    )
    blocked_packet_probe["review_packet"] = _ready_probe(written)["review_packet"]
    blocked_packet_errors = validate_phase7_live_promotion_review(blocked_packet_probe)

    live_credentials_probe = _ready_probe(written)
    live_credentials_probe["live_credentials_enabled"] = True
    live_credentials_probe["live_credentials_loaded"] = True
    live_credentials_errors = validate_phase7_live_promotion_review(
        live_credentials_probe
    )

    live_capital_probe = _ready_probe(written)
    live_capital_probe["live_capital_enabled"] = True
    live_capital_probe["authority_ledger"]["live_capital_enabled"] = True
    live_capital_probe["live_capital_enabled_count"] = 1
    live_capital_errors = validate_phase7_live_promotion_review(live_capital_probe)

    broker_write_probe = _ready_probe(written)
    broker_write_probe["broker_post_allowed"] = True
    broker_write_probe["authority_ledger"]["broker_post_allowed"] = True
    broker_write_probe["broker_post_called_count"] = 1
    broker_write_probe["alpaca_post_called_count"] = 1
    broker_write_probe["prediction_market_write_allowed"] = True
    broker_write_probe["authority_ledger"]["prediction_market_write_allowed"] = True
    broker_write_probe["prediction_market_write_allowed_count"] = 1
    broker_write_errors = validate_phase7_live_promotion_review(broker_write_probe)

    proof_credit_probe = _ready_probe(written)
    proof_credit_probe["phase7_proof_credit_allowed"] = True
    proof_credit_probe["authority_ledger"]["phase7_proof_credit_allowed"] = True
    proof_credit_probe["phase7_proof_credit_allowed_count"] = 1
    proof_credit_errors = validate_phase7_live_promotion_review(proof_credit_probe)

    cooling_required_probe = _ready_probe(written)
    cooling_required_probe["cooling_off_required"] = False
    cooling_required_errors = validate_phase7_live_promotion_review(
        cooling_required_probe
    )

    cooling_complete_probe = _ready_probe(written)
    cooling_complete_probe["cooling_off_complete"] = True
    cooling_complete_probe["review_packet"]["cooling_off_summary"][
        "cooling_off_complete"
    ] = True
    cooling_complete_errors = validate_phase7_live_promotion_review(
        cooling_complete_probe
    )

    approval_probe = _ready_probe(written)
    approval_probe["live_promotion_approval_state"] = "approved"
    approval_probe["live_promotion_approval_allowed"] = True
    approval_probe["review_packet"]["approval_summary"][
        "live_promotion_approval_state"
    ] = "approved"
    approval_probe["review_packet"]["approval_summary"][
        "live_promotion_approval_allowed"
    ] = True
    approval_errors = validate_phase7_live_promotion_review(approval_probe)

    raw_payload_probe = deepcopy(written)
    raw_payload_probe["public_status"]["raw_payload"] = {"secret": "hidden"}
    raw_payload_errors = validate_phase7_live_promotion_review(raw_payload_probe)

    source_display_probe = deepcopy(written)
    source_display_probe["source_status_records"][0]["display_status"] = "frontend"
    source_display_errors = validate_phase7_live_promotion_review(source_display_probe)

    print(f"phase7_live_promotion_status={written['status']}")
    print(f"phase7_live_promotion_stage_status={written['stage_status']}")
    print(
        "phase7_live_promotion_schema_version="
        f"{PHASE7_LIVE_PROMOTION_REVIEW_SCHEMA_VERSION}"
    )
    print(f"phase7_live_promotion_artifact_path={output_path}")
    print(f"phase7_live_promotion_history_path={history_path}")
    print(f"phase7_live_promotion_event_log_path={event_log_path}")
    print(
        "phase7_live_promotion_source_certification_status="
        f"{written['source_certification_status']}"
    )
    print(
        "phase7_live_promotion_source_certification_stage_status="
        f"{written['source_certification_stage_status']}"
    )
    print(
        "phase7_live_promotion_phase7_demo_proof_certified="
        f"{written['phase7_demo_proof_certified']}"
    )
    print(
        "phase7_live_promotion_q7_18_live_promotion_review_stage_allowed="
        f"{written['q7_18_live_promotion_review_stage_allowed']}"
    )
    print(
        "phase7_live_promotion_review_packet_draft_allowed="
        f"{written['live_promotion_review_packet_draft_allowed']}"
    )
    print(
        "phase7_live_promotion_review_packet_created="
        f"{written['live_promotion_review_packet_created']}"
    )
    print(
        "phase7_live_promotion_review_state="
        f"{written['live_promotion_review_state']}"
    )
    print(
        "phase7_live_promotion_cooling_off_required="
        f"{written['cooling_off_required']}"
    )
    print(
        "phase7_live_promotion_cooling_off_complete="
        f"{written['cooling_off_complete']}"
    )
    print(
        "phase7_live_promotion_live_promotion_approval_state="
        f"{written['live_promotion_approval_state']}"
    )
    print(
        "phase7_live_promotion_live_credentials_enabled="
        f"{written['live_credentials_enabled']}"
    )
    print(
        "phase7_live_promotion_live_credentials_loaded="
        f"{written['live_credentials_loaded']}"
    )
    print(
        "phase7_live_promotion_live_capital_enabled="
        f"{written['live_capital_enabled']}"
    )
    print(
        "phase7_live_promotion_live_broker_write_allowed="
        f"{written['live_broker_write_allowed']}"
    )
    print(
        "phase7_live_promotion_phase7_proof_credit_allowed="
        f"{written['phase7_proof_credit_allowed']}"
    )
    print(
        "phase7_live_promotion_broker_post_called_count="
        f"{written['broker_post_called_count']}"
    )
    print(
        "phase7_live_promotion_alpaca_post_called_count="
        f"{written['alpaca_post_called_count']}"
    )
    print(
        "phase7_live_promotion_unsafe_write_counter_total="
        f"{written['unsafe_write_counter_total']}"
    )
    print(
        "phase7_live_promotion_operational_incident_count="
        f"{written['operational_incident_count']}"
    )
    print(f"phase7_live_promotion_blocker_count={written['blocker_count']}")
    print(f"phase7_live_promotion_blockers={','.join(written['blockers'])}")
    print(f"phase7_live_promotion_event_log_events={replay['total_events']}")
    print(f"phase7_live_promotion_validation_errors={validation_errors}")

    if validation_errors:
        errors.append(f"live-promotion validation failed: {validation_errors}")
    if runtime_copy.get("artifact_id") != written["artifact_id"]:
        errors.append("runtime artifact did not persist live-promotion artifact")
    if replay["total_events"] != 1:
        errors.append("live-promotion event log did not record exactly one event")
    if replay["by_type"].get("phase7_live_promotion_review_recorded") != 1:
        errors.append("live-promotion event log event type mismatch")
    if written["status"] != "blocked":
        errors.append("current Q7-18 should be blocked before Q7-17 certification")
    if written["phase7_demo_proof_certified"] is not False:
        errors.append("current Q7-18 falsely sees Phase 7 certification")
    if written["q7_18_live_promotion_review_stage_allowed"] is not False:
        errors.append("current Q7-18 falsely allows live-promotion review")
    if written["live_promotion_review_packet_created"] is not False:
        errors.append("current Q7-18 created packet before certification")
    for blocker in (
        "phase7_certification_not_certified",
        "q7_18_live_promotion_review_not_allowed",
    ):
        if blocker not in written["blockers"]:
            errors.append(f"current live-promotion blocker missing: {blocker}")
    if written["live_credentials_enabled"] is not False:
        errors.append("Q7-18 enables live credentials")
    if written["live_credentials_loaded"] is not False:
        errors.append("Q7-18 loads live credentials")
    if written["live_capital_enabled"] is not False:
        errors.append("Q7-18 enables live capital")
    if written["phase7_proof_credit_allowed"] is not False:
        errors.append("Q7-18 grants Phase 7 proof credit")
    if ready_errors:
        errors.append(f"valid post-certification review probe rejected: {ready_errors}")
    for label, probe_errors in (
        ("early Q7-18 handoff", early_q7_18_errors),
        ("blocked packet creation", blocked_packet_errors),
        ("live credentials", live_credentials_errors),
        ("live capital", live_capital_errors),
        ("broker/market write", broker_write_errors),
        ("proof credit", proof_credit_errors),
        ("cooling required", cooling_required_errors),
        ("cooling complete", cooling_complete_errors),
        ("approval", approval_errors),
        ("raw public payload", raw_payload_errors),
        ("source display mismatch", source_display_errors),
    ):
        if not probe_errors:
            errors.append(f"{label} probe was not rejected")

    if errors:
        print("phase7_live_promotion_check=failed")
        for error in errors:
            print(f"error={error}")
        return 1
    print("phase7_live_promotion_check=ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
