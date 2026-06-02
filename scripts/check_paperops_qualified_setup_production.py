#!/usr/bin/env python3
"""Validate PT-3 qualified setup production path."""

from __future__ import annotations

from copy import deepcopy
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from orchestrator.config import Settings  # noqa: E402
from orchestrator.event_log import EventLog  # noqa: E402
from orchestrator.paperops_qualified_setup_production import (  # noqa: E402
    PAPEROPS_QUALIFIED_SETUP_SCHEMA_VERSION,
    build_paperops_qualified_setup_production,
    paperops_qualified_setup_production_paths,
    validate_paperops_qualified_setup_production,
    write_paperops_qualified_setup_production,
)


def main() -> int:
    errors: list[str] = []
    settings = Settings.from_env()
    output_path, history_path, event_log_path = paperops_qualified_setup_production_paths(
        settings
    )
    if event_log_path.exists():
        event_log_path.unlink()

    artifact = build_paperops_qualified_setup_production(settings=settings)
    output_path, history_path, event_log_path, written = (
        write_paperops_qualified_setup_production(
            artifact,
            settings=settings,
            record_event=True,
            event_log_path=event_log_path,
        )
    )
    validation_errors = validate_paperops_qualified_setup_production(written)
    replay = EventLog(event_log_path, echo=False).replay()

    live_capital_probe = deepcopy(written)
    live_capital_probe["live_capital_enabled"] = True
    live_capital_errors = validate_paperops_qualified_setup_production(
        live_capital_probe
    )

    submit_probe = deepcopy(written)
    submit_probe["paper_order_submission_allowed"] = True
    submit_errors = validate_paperops_qualified_setup_production(submit_probe)

    broker_probe = deepcopy(written)
    broker_probe["broker_post_called_count"] = 1
    broker_probe["unsafe_write_counter_total"] = 1
    broker_errors = validate_paperops_qualified_setup_production(broker_probe)

    qctrl_execution_probe = deepcopy(written)
    qctrl_execution_probe["qctrl_direct_execution_allowed"] = True
    qctrl_execution_errors = validate_paperops_qualified_setup_production(
        qctrl_execution_probe
    )

    proof_credit_probe = deepcopy(written)
    proof_credit_probe["phase7_proof_credit_allowed"] = True
    proof_credit_errors = validate_paperops_qualified_setup_production(
        proof_credit_probe
    )

    forced_trade_probe = deepcopy(written)
    forced_trade_probe["forced_trades_allowed"] = True
    forced_trade_errors = validate_paperops_qualified_setup_production(
        forced_trade_probe
    )

    ready_without_setup_probe = deepcopy(written)
    ready_without_setup_probe["ready_to_stage_q7_order"] = True
    ready_without_setup_probe["qualified_setup_count"] = 0
    ready_without_setup_errors = validate_paperops_qualified_setup_production(
        ready_without_setup_probe
    )

    supplemental_probe = deepcopy(written)
    supplemental_probe["source_quorum_bypass_allowed"] = True
    supplemental_probe["supplemental_source_bypass_allowed"] = True
    supplemental_errors = validate_paperops_qualified_setup_production(
        supplemental_probe
    )

    source_coverage_probe = deepcopy(written)
    if source_coverage_probe.get("candidate_setup_records"):
        source_coverage_probe["candidate_setup_records"][0]["source_quorum_passed"] = True
        source_coverage_probe["candidate_setup_records"][0][
            "decision_source_coverage_complete"
        ] = False
    source_coverage_errors = validate_paperops_qualified_setup_production(
        source_coverage_probe
    )

    event_probe = deepcopy(written)
    event_probe["event_log_written"] = False
    event_probe["event_log_event_count"] = 0
    event_errors = validate_paperops_qualified_setup_production(event_probe)

    source_coverage_complete_count = sum(
        1
        for record in written.get("candidate_setup_records", [])
        if isinstance(record, dict)
        and record.get("decision_source_coverage_complete") is True
    )

    print(f"paperops_qualified_setup_status={written['status']}")
    print(
        "paperops_qualified_setup_schema_version="
        f"{PAPEROPS_QUALIFIED_SETUP_SCHEMA_VERSION}"
    )
    print(f"paperops_qualified_setup_artifact_path={output_path}")
    print(f"paperops_qualified_setup_history_path={history_path}")
    print(f"paperops_qualified_setup_event_log_path={event_log_path}")
    print(f"paperops_qualified_setup_event_log_events={replay['total_events']}")
    print(
        "paperops_qualified_setup_paper_operational_mode_status="
        f"{written['paper_operational_mode_status']}"
    )
    print(
        "paperops_qualified_setup_paper_operational_mode_effective="
        f"{written['paper_operational_mode_effective']}"
    )
    print(
        "paperops_qualified_setup_phase7_run_state="
        f"{written['phase7_run_state']}"
    )
    print(
        "paperops_qualified_setup_phase7_active_day_number="
        f"{written['phase7_active_day_number']}"
    )
    print(
        "paperops_qualified_setup_phase7_demo_qualified_setup_count="
        f"{written['phase7_demo_qualified_setup_count']}"
    )
    print(
        "paperops_qualified_setup_production_candidate_count="
        f"{written['production_candidate_count']}"
    )
    print(
        "paperops_qualified_setup_qualified_setup_count="
        f"{written['qualified_setup_count']}"
    )
    print(
        "paperops_qualified_setup_blocked_candidate_count="
        f"{written['blocked_candidate_count']}"
    )
    print(
        "paperops_qualified_setup_ready_to_stage_q7_order="
        f"{written['ready_to_stage_q7_order']}"
    )
    print(
        "paperops_qualified_setup_path_ready="
        f"{written['qualified_setup_production_path_ready']}"
    )
    print(
        "paperops_qualified_setup_no_trade_rationale="
        f"{written['no_trade_rationale']}"
    )
    print(
        "paperops_qualified_setup_paper_size_eligible_count="
        f"{written['paper_size_eligible_count']}"
    )
    print(f"paperops_qualified_setup_staged_order_count={written['staged_order_count']}")
    print(
        "paperops_qualified_setup_q7_ledger_status="
        f"{written['source_qualified_setup_ledger_status']}"
    )
    print(
        "paperops_qualified_setup_q7_ledger_count="
        f"{written['source_qualified_setup_ledger_count']}"
    )
    print(
        "paperops_qualified_setup_production_gate_pass_count="
        f"{written['production_gate_pass_count']}"
    )
    print(
        "paperops_qualified_setup_production_gate_required_count="
        f"{written['production_gate_required_count']}"
    )
    print(
        "paperops_qualified_setup_qctrl_consultation_required_for_full_parity="
        f"{written['qctrl_consultation_required_for_full_parity']}"
    )
    print(
        "paperops_qualified_setup_qctrl_paper_consultation_status="
        f"{written['qctrl_paper_consultation_status']}"
    )
    print(
        "paperops_qualified_setup_qctrl_paper_consultation_connected="
        f"{written['qctrl_paper_consultation_connected']}"
    )
    print(
        "paperops_qualified_setup_qctrl_product_access_status="
        f"{written['qctrl_product_access_status']}"
    )
    print(
        "paperops_qualified_setup_qctrl_product_access_verified="
        f"{written['qctrl_product_access_verified']}"
    )
    print(
        "paperops_qualified_setup_qctrl_consultation_blocker="
        f"{written['qctrl_consultation_blocker']}"
    )
    print(
        "paperops_qualified_setup_source_posture_canonical_source_count="
        f"{written['source_posture_canonical_source_count']}"
    )
    print(
        "paperops_qualified_setup_source_quorum_bypass_allowed="
        f"{written['source_quorum_bypass_allowed']}"
    )
    print(
        "paperops_qualified_setup_supplemental_source_bypass_allowed="
        f"{written['supplemental_source_bypass_allowed']}"
    )
    print(f"paperops_qualified_setup_yahoo_finance_role={written['yahoo_finance_role']}")
    print(f"paperops_qualified_setup_preference_mcp_role={written['preference_mcp_role']}")
    print(f"paperops_qualified_setup_execution_allowed={written['execution_allowed']}")
    print(
        "paperops_qualified_setup_paper_order_staging_allowed="
        f"{written['paper_order_staging_allowed']}"
    )
    print(
        "paperops_qualified_setup_paper_order_submission_allowed="
        f"{written['paper_order_submission_allowed']}"
    )
    print(f"paperops_qualified_setup_broker_post_allowed={written['broker_post_allowed']}")
    print(f"paperops_qualified_setup_live_capital_enabled={written['live_capital_enabled']}")
    print(
        "paperops_qualified_setup_phase7_proof_credit_allowed="
        f"{written['phase7_proof_credit_allowed']}"
    )
    print(f"paperops_qualified_setup_forced_trades_allowed={written['forced_trades_allowed']}")
    print(
        "paperops_qualified_setup_qualified_setup_creation_forced="
        f"{written['qualified_setup_creation_forced']}"
    )
    print(
        "paperops_qualified_setup_broker_post_called_count="
        f"{written['broker_post_called_count']}"
    )
    print(
        "paperops_qualified_setup_alpaca_post_called_count="
        f"{written['alpaca_post_called_count']}"
    )
    print(
        "paperops_qualified_setup_live_endpoint_called_count="
        f"{written['live_endpoint_called_count']}"
    )
    print(
        "paperops_qualified_setup_qctrl_provider_call_count="
        f"{written['qctrl_provider_call_count']}"
    )
    print(
        "paperops_qualified_setup_qctrl_broker_post_called_count="
        f"{written['qctrl_broker_post_called_count']}"
    )
    print(
        "paperops_qualified_setup_qctrl_live_endpoint_called_count="
        f"{written['qctrl_live_endpoint_called_count']}"
    )
    print(
        "paperops_qualified_setup_phase7_proof_credit_granted_count="
        f"{written['phase7_proof_credit_granted_count']}"
    )
    print(
        "paperops_qualified_setup_forced_trade_count="
        f"{written['forced_trade_count']}"
    )
    print(
        "paperops_qualified_setup_unsafe_write_counter_total="
        f"{written['unsafe_write_counter_total']}"
    )
    print(
        "paperops_qualified_setup_next_required_action="
        f"{written['next_required_action']}"
    )
    print(f"paperops_qualified_setup_validation_errors={validation_errors}")
    print(
        "paperops_qualified_setup_source_coverage_probe_error_count="
        f"{len(source_coverage_errors)}"
    )
    print(
        "paperops_qualified_setup_source_coverage_complete_count="
        f"{source_coverage_complete_count}"
    )

    if validation_errors:
        errors.append(f"PT-3 validation failed: {validation_errors}")
    if replay["total_events"] != 1:
        errors.append("PT-3 event log did not record exactly one event")
    if written["status"] not in {
        "production_path_ready_with_qualified_setup",
        "production_path_ready_no_current_qualified_setup",
    }:
        errors.append("PT-3 production path is not ready")
    if written["qualified_setup_production_path_ready"] is not True:
        errors.append("PT-3 production path readiness is false")
    if written["production_candidate_count"] < 1:
        errors.append("PT-3 did not observe any production candidates")
    if source_coverage_complete_count != written["production_candidate_count"]:
        errors.append("PT-3 candidate source coverage incomplete")
    if written["qualified_setup_count"] == 0:
        if written["status"] != "production_path_ready_no_current_qualified_setup":
            errors.append("PT-3 no-qualified status mismatch")
        if written["ready_to_stage_q7_order"] is not False:
            errors.append("PT-3 ready-to-stage true without current qualified setup")
        if written["no_trade_rationale"] != "no_current_pt3_qualified_setup_detected":
            errors.append("PT-3 no-trade rationale mismatch")
    else:
        if written["paper_size_eligible_count"] < 1:
            errors.append("PT-3 did not observe the Q5 paper-size eligible setup")
        if written["staged_order_count"] < 1:
            errors.append("PT-3 did not observe the Q5 staged paper order")
        if written["source_qualified_setup_ledger_count"] > written["qualified_setup_count"]:
            errors.append("PT-3 observed more Q7 ledger setups than PT-3 qualified")
        if written["phase7_demo_qualified_setup_count"] > written["qualified_setup_count"]:
            errors.append("PT-3 observed more Phase 7 demo setups than PT-3 qualified")
    if written["live_capital_enabled"] is not False:
        errors.append("PT-3 enabled live capital")
    if written["paper_order_submission_allowed"] is not False:
        errors.append("PT-3 opened paper submission authority")
    if written["broker_post_called_count"] != 0:
        errors.append("PT-3 called broker POST")
    if written["qctrl_broker_post_called_count"] != 0:
        errors.append("PT-3 called Q-CTRL broker POST")
    if written["qctrl_direct_execution_allowed"] is not False:
        errors.append("PT-3 gave Q-CTRL execution authority")
    if written["phase7_proof_credit_allowed"] is not False:
        errors.append("PT-3 granted proof credit")
    if written["forced_trades_allowed"] is not False:
        errors.append("PT-3 allowed forced trades")
    if written["unsafe_write_counter_total"] != 0:
        errors.append("PT-3 unsafe write counter is nonzero")
    if "paperops_qualified_setup_live_capital_enabled" not in live_capital_errors:
        errors.append("live-capital probe was not rejected")
    if (
        "paperops_qualified_setup_forbidden:paper_order_submission_allowed"
        not in submit_errors
    ):
        errors.append("paper-submit authority probe was not rejected")
    if (
        "paperops_qualified_setup_unsafe_counter_nonzero:broker_post_called_count"
        not in broker_errors
    ):
        errors.append("broker POST probe was not rejected")
    if (
        "paperops_qualified_setup_forbidden:qctrl_direct_execution_allowed"
        not in qctrl_execution_errors
    ):
        errors.append("Q-CTRL execution probe was not rejected")
    if (
        "paperops_qualified_setup_forbidden:phase7_proof_credit_allowed"
        not in proof_credit_errors
    ):
        errors.append("proof-credit probe was not rejected")
    if (
        "paperops_qualified_setup_forbidden:forced_trades_allowed"
        not in forced_trade_errors
    ):
        errors.append("forced-trade probe was not rejected")
    if (
        "paperops_qualified_setup_ready_without_qualified_setup"
        not in ready_without_setup_errors
    ):
        errors.append("ready-without-setup probe was not rejected")
    if (
        "paperops_qualified_setup_source_quorum_bypass_allowed"
        not in supplemental_errors
    ):
        errors.append("source-quorum bypass probe was not rejected")
    if (
        "paperops_qualified_setup_supplemental_bypass_allowed"
        not in supplemental_errors
    ):
        errors.append("supplemental bypass probe was not rejected")
    if (
        source_coverage_probe.get("candidate_setup_records")
        and "paperops_qualified_setup_source_quorum_without_decision_coverage"
        not in source_coverage_errors
    ):
        errors.append("source-coverage probe was not rejected")
    if "paperops_qualified_setup_event_log_missing" not in event_errors:
        errors.append("event-log probe was not rejected")

    if errors:
        print("paperops_qualified_setup_production_check=failed")
        for error in errors:
            print(f"error={error}")
        return 1
    print("paperops_qualified_setup_production_check=ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
