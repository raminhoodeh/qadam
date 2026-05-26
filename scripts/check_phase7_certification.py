#!/usr/bin/env python3
"""Validate Q7-17 Phase 7 Demo Proof certification."""

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
    PHASE7_CERTIFICATION_REQUIRED_GATES,
    PHASE7_CERTIFICATION_SCHEMA_VERSION,
    PUBLIC_STATUS_FIELDS,
    build_phase7_certification,
    phase7_certification_paths,
    validate_phase7_certification,
    write_phase7_certification,
)
from orchestrator.phase7_readiness import PHASE7_HARNESS_DAY_COUNT  # noqa: E402
from orchestrator.phase7_weekly_review_pack import (  # noqa: E402
    build_phase7_weekly_review_pack,
    validate_phase7_weekly_review_pack,
    write_phase7_weekly_review_pack,
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


def _set_gate(
    artifact: dict[str, object],
    gate_name: str,
    *,
    passed: bool,
    blocker: str | None = None,
) -> None:
    for gate in artifact["certification_gate_records"]:
        if gate.get("gate_name") != gate_name:
            continue
        gate["backend_status"] = "passed" if passed else "blocked"
        gate["display_status"] = gate["backend_status"]
        gate["gate_passed"] = passed
        gate["blocker"] = None if passed else blocker
        return
    raise RuntimeError(f"gate not found: {gate_name}")


def _refresh_gate_counts(artifact: dict[str, object], blockers: list[str]) -> None:
    artifact["certification_gate_count"] = len(artifact["certification_gate_records"])
    artifact["certification_gate_passed_count"] = sum(
        1 for gate in artifact["certification_gate_records"] if gate.get("gate_passed") is True
    )
    artifact["certification_gate_blocked_count"] = (
        artifact["certification_gate_count"] - artifact["certification_gate_passed_count"]
    )
    artifact["certification_blockers"] = sorted(set(blockers))
    artifact["certification_blocker_count"] = len(artifact["certification_blockers"])


def _mature_certified_probe(artifact: dict[str, object]) -> dict[str, object]:
    probe = deepcopy(artifact)
    for gate in PHASE7_CERTIFICATION_REQUIRED_GATES:
        _set_gate(probe, gate, passed=True)
    probe.update(
        {
            "status": "certified",
            "stage_status": "phase7_demo_proof_certified",
            "certification_state": "certified_mature_sample",
            "phase7_demo_proof_certified": True,
            "phase7_demo_proof_exit_gate": True,
            "phase7_30_day_operational_result_clean": True,
            "phase7_30_day_operational_result_preserved": True,
            "phase7_30_day_operational_result_erased_by_immaturity": False,
            "phase7_30_day_run_complete": True,
            "completed_calendar_day_count": PHASE7_HARNESS_DAY_COUNT,
            "proof_week_count": 5,
            "weekly_cadence_satisfied_count": 5,
            "weekly_cadence_failed_count": 0,
            "weekly_review_packet_created_count": 5,
            "qualified_setup_count": 15,
            "missed_qualified_setup_count": 0,
            "missed_qualified_setup_unexplained_count": 0,
            "evaluated_trade_count": 100,
            "expectancy_after_costs_gbp": 18.75,
            "expectancy_after_costs_positive": True,
            "drawdown_within_cap": True,
            "drawdown_cap_breached": False,
            "max_drawdown_fraction_observed": 0.08,
            "risk_halt_active": False,
            "override_count": 0,
            "manual_trade_level_override_count": 0,
            "sample_contaminated": False,
            "closed_proof_trade_count": 100,
            "postmortem_due_count": 100,
            "postmortem_missing_count": 0,
            "postmortem_reviewed_count": 100,
            "postmortem_coverage_satisfied": True,
            "complete_decision_chain_count": 100,
            "missing_decision_chain_count": 0,
            "private_priors_only_proof_trade_count": 0,
            "source_signal_chains_complete": True,
            "maturity_state": "statistically_mature",
            "maturity_classification": "statistically_mature_100_closed_trades",
            "phase7_mature_benchmark_met": True,
            "phase7_mature_status_blocked": False,
            "phase7_statistically_immature": False,
            "phase7_statistical_immaturity_hidden": False,
            "phase7_certification_blocked_by_maturity": False,
            "q7_18_live_promotion_review_stage_allowed": True,
            "recommended_next_stage": "Q7-18 Live Promotion Review Flow",
            "validation_errors": [],
        }
    )
    probe["authority_ledger"]["q7_18_live_promotion_review_stage_allowed"] = True
    _refresh_gate_counts(probe, [])
    return _sync_public_status(probe)


def _immature_operational_probe(artifact: dict[str, object]) -> dict[str, object]:
    probe = _mature_certified_probe(artifact)
    _set_gate(
        probe,
        "maturity_classified_and_benchmark_met",
        passed=False,
        blocker="phase7_maturity_benchmark_not_met",
    )
    probe.update(
        {
            "status": "blocked",
            "stage_status": "phase7_operational_clean_but_maturity_blocked",
            "certification_state": "blocked_by_maturity_benchmark",
            "phase7_demo_proof_certified": False,
            "phase7_demo_proof_exit_gate": False,
            "closed_proof_trade_count": 25,
            "postmortem_due_count": 25,
            "postmortem_reviewed_count": 25,
            "complete_decision_chain_count": 25,
            "evaluated_trade_count": 25,
            "maturity_state": "statistically_immature_after_30_days",
            "maturity_classification": (
                "statistically_immature_after_30_days_under_100_closed_trades"
            ),
            "phase7_mature_benchmark_met": False,
            "phase7_mature_status_blocked": True,
            "phase7_statistically_immature": True,
            "phase7_certification_blocked_by_maturity": True,
            "q7_18_live_promotion_review_stage_allowed": False,
            "recommended_next_stage": (
                "Complete the 30-day proof run and maturity benchmark before Q7-18"
            ),
            "validation_errors": [],
        }
    )
    probe["authority_ledger"]["q7_18_live_promotion_review_stage_allowed"] = False
    _refresh_gate_counts(probe, ["phase7_maturity_benchmark_not_met"])
    return _sync_public_status(probe)


def main() -> int:
    errors: list[str] = []
    settings = Settings.from_env()
    output_path, history_path, event_log_path = phase7_certification_paths(settings)
    if event_log_path.exists():
        event_log_path.unlink()

    weekly_review = build_phase7_weekly_review_pack(settings=settings)
    _, _, _, weekly_written = write_phase7_weekly_review_pack(
        weekly_review,
        settings=settings,
        record_event=True,
    )
    weekly_errors = validate_phase7_weekly_review_pack(weekly_written)

    artifact = build_phase7_certification(settings=settings)
    output_path, history_path, event_log_path, written = write_phase7_certification(
        artifact,
        settings=settings,
        record_event=True,
        event_log_path=event_log_path,
    )
    validation_errors = validate_phase7_certification(written)
    runtime_copy = _read_json(output_path)
    replay = EventLog(event_log_path, echo=False).replay()

    mature_certified_errors = validate_phase7_certification(
        _mature_certified_probe(written)
    )
    immature_operational_errors = validate_phase7_certification(
        _immature_operational_probe(written)
    )

    false_certified_probe = deepcopy(written)
    false_certified_probe["status"] = "certified"
    false_certified_probe["phase7_demo_proof_certified"] = True
    false_certified_probe["phase7_demo_proof_exit_gate"] = True
    false_certified_errors = validate_phase7_certification(false_certified_probe)

    run_incomplete_probe = _mature_certified_probe(written)
    run_incomplete_probe["phase7_30_day_run_complete"] = False
    run_incomplete_probe["completed_calendar_day_count"] = 29
    run_incomplete_errors = validate_phase7_certification(run_incomplete_probe)

    expectancy_probe = _mature_certified_probe(written)
    expectancy_probe["expectancy_after_costs_positive"] = False
    expectancy_errors = validate_phase7_certification(expectancy_probe)

    drawdown_probe = _mature_certified_probe(written)
    drawdown_probe["drawdown_within_cap"] = False
    drawdown_probe["drawdown_cap_breached"] = True
    drawdown_errors = validate_phase7_certification(drawdown_probe)

    override_probe = _mature_certified_probe(written)
    override_probe["manual_trade_level_override_count"] = 1
    override_probe["override_count"] = 1
    override_errors = validate_phase7_certification(override_probe)

    postmortem_probe = _mature_certified_probe(written)
    postmortem_probe["postmortem_missing_count"] = 1
    postmortem_probe["postmortem_coverage_satisfied"] = False
    postmortem_errors = validate_phase7_certification(postmortem_probe)

    signal_probe = _mature_certified_probe(written)
    signal_probe["missing_decision_chain_count"] = 1
    signal_probe["source_signal_chains_complete"] = False
    signal_errors = validate_phase7_certification(signal_probe)

    hidden_immaturity_probe = _immature_operational_probe(written)
    hidden_immaturity_probe["phase7_statistical_immaturity_hidden"] = True
    hidden_immaturity_errors = validate_phase7_certification(hidden_immaturity_probe)

    proof_credit_probe = _mature_certified_probe(written)
    proof_credit_probe["phase7_proof_credit_allowed"] = True
    proof_credit_probe["authority_ledger"]["phase7_proof_credit_allowed"] = True
    proof_credit_probe["phase7_proof_credit_allowed_count"] = 1
    proof_credit_errors = validate_phase7_certification(proof_credit_probe)

    live_capital_probe = _mature_certified_probe(written)
    live_capital_probe["live_capital_enabled"] = True
    live_capital_probe["authority_ledger"]["live_capital_enabled"] = True
    live_capital_probe["live_capital_enabled_count"] = 1
    live_capital_errors = validate_phase7_certification(live_capital_probe)

    broker_write_probe = _mature_certified_probe(written)
    broker_write_probe["broker_post_allowed"] = True
    broker_write_probe["authority_ledger"]["broker_post_allowed"] = True
    broker_write_probe["broker_post_called_count"] = 1
    broker_write_probe["prediction_market_write_allowed"] = True
    broker_write_probe["authority_ledger"]["prediction_market_write_allowed"] = True
    broker_write_probe["prediction_market_write_allowed_count"] = 1
    broker_write_errors = validate_phase7_certification(broker_write_probe)

    q7_18_probe = deepcopy(written)
    q7_18_probe["q7_18_live_promotion_review_stage_allowed"] = True
    q7_18_probe["authority_ledger"]["q7_18_live_promotion_review_stage_allowed"] = True
    q7_18_errors = validate_phase7_certification(q7_18_probe)

    raw_payload_probe = deepcopy(written)
    raw_payload_probe["public_status"]["raw_payload"] = {"secret": "hidden"}
    raw_payload_errors = validate_phase7_certification(raw_payload_probe)

    source_display_probe = deepcopy(written)
    source_display_probe["source_status_records"][0]["display_status"] = "frontend"
    source_display_errors = validate_phase7_certification(source_display_probe)

    print(f"phase7_certification_status={written['status']}")
    print(f"phase7_certification_stage_status={written['stage_status']}")
    print(f"phase7_certification_schema_version={PHASE7_CERTIFICATION_SCHEMA_VERSION}")
    print(f"phase7_certification_artifact_path={output_path}")
    print(f"phase7_certification_history_path={history_path}")
    print(f"phase7_certification_event_log_path={event_log_path}")
    print(
        "phase7_certification_phase7_demo_proof_certified="
        f"{written['phase7_demo_proof_certified']}"
    )
    print(
        "phase7_certification_phase7_demo_proof_exit_gate="
        f"{written['phase7_demo_proof_exit_gate']}"
    )
    print(
        "phase7_certification_30_day_operational_result_clean="
        f"{written['phase7_30_day_operational_result_clean']}"
    )
    print(
        "phase7_certification_30_day_operational_result_preserved="
        f"{written['phase7_30_day_operational_result_preserved']}"
    )
    print(
        "phase7_certification_phase7_30_day_run_complete="
        f"{written['phase7_30_day_run_complete']}"
    )
    print(
        "phase7_certification_completed_calendar_day_count="
        f"{written['completed_calendar_day_count']}"
    )
    print(f"phase7_certification_proof_week_count={written['proof_week_count']}")
    print(
        "phase7_certification_weekly_cadence_satisfied_count="
        f"{written['weekly_cadence_satisfied_count']}"
    )
    print(
        "phase7_certification_weekly_cadence_failed_count="
        f"{written['weekly_cadence_failed_count']}"
    )
    print(
        "phase7_certification_weekly_review_packet_created_count="
        f"{written['weekly_review_packet_created_count']}"
    )
    print(f"phase7_certification_evaluated_trade_count={written['evaluated_trade_count']}")
    print(
        "phase7_certification_expectancy_after_costs_positive="
        f"{written['expectancy_after_costs_positive']}"
    )
    print(f"phase7_certification_drawdown_within_cap={written['drawdown_within_cap']}")
    print(
        "phase7_certification_manual_trade_level_override_count="
        f"{written['manual_trade_level_override_count']}"
    )
    print(f"phase7_certification_closed_proof_trade_count={written['closed_proof_trade_count']}")
    print(f"phase7_certification_postmortem_missing_count={written['postmortem_missing_count']}")
    print(
        "phase7_certification_source_signal_chains_complete="
        f"{written['source_signal_chains_complete']}"
    )
    print(f"phase7_certification_maturity_state={written['maturity_state']}")
    print(f"phase7_certification_maturity_classification={written['maturity_classification']}")
    print(
        "phase7_certification_phase7_mature_benchmark_met="
        f"{written['phase7_mature_benchmark_met']}"
    )
    print(
        "phase7_certification_phase7_statistically_immature="
        f"{written['phase7_statistically_immature']}"
    )
    print(
        "phase7_certification_phase7_statistical_immaturity_hidden="
        f"{written['phase7_statistical_immaturity_hidden']}"
    )
    print(
        "phase7_certification_phase5_test_trades_count_for_phase7="
        f"{written['phase5_test_trades_count_for_phase7']}"
    )
    print(
        "phase7_certification_phase7_proof_credit_allowed="
        f"{written['phase7_proof_credit_allowed']}"
    )
    print(f"phase7_certification_live_capital_enabled={written['live_capital_enabled']}")
    print(f"phase7_certification_broker_post_called_count={written['broker_post_called_count']}")
    print(f"phase7_certification_alpaca_post_called_count={written['alpaca_post_called_count']}")
    print(f"phase7_certification_unsafe_write_counter_total={written['unsafe_write_counter_total']}")
    print(f"phase7_certification_source_missing_count={written['source_missing_count']}")
    print(
        "phase7_certification_source_validation_error_count="
        f"{written['source_validation_error_count']}"
    )
    print(f"phase7_certification_gate_count={written['certification_gate_count']}")
    print(
        "phase7_certification_gate_passed_count="
        f"{written['certification_gate_passed_count']}"
    )
    print(
        "phase7_certification_gate_blocked_count="
        f"{written['certification_gate_blocked_count']}"
    )
    print(f"phase7_certification_blocker_count={written['certification_blocker_count']}")
    print(
        "phase7_certification_blockers="
        f"{','.join(written['certification_blockers'])}"
    )
    print(
        "phase7_certification_q7_18_live_promotion_review_stage_allowed="
        f"{written['q7_18_live_promotion_review_stage_allowed']}"
    )
    print(f"phase7_certification_event_log_events={replay['total_events']}")
    print(f"phase7_certification_validation_errors={validation_errors}")

    if weekly_errors:
        errors.append(f"weekly review validation failed: {weekly_errors}")
    if validation_errors:
        errors.append(f"certification validation failed: {validation_errors}")
    if runtime_copy.get("artifact_id") != written["artifact_id"]:
        errors.append("runtime artifact did not persist certification artifact")
    if replay["total_events"] != 1:
        errors.append("certification event log did not record exactly one event")
    if replay["by_type"].get("phase7_certification_recorded") != 1:
        errors.append("certification event log event type mismatch")
    if written["status"] != "blocked":
        errors.append("current Q7-17 certification should be blocked")
    if written["phase7_demo_proof_certified"] is not False:
        errors.append("current Q7-17 falsely certified the demo proof")
    if written["phase7_demo_proof_exit_gate"] is not False:
        errors.append("current Q7-17 falsely opened the exit gate")
    if written["phase7_30_day_run_complete"] is not False:
        errors.append("current Q7-17 falsely marked the 30-day run complete")
    for blocker in (
        "phase7_30_day_run_incomplete",
        "positive_expectancy_after_costs_missing",
        "phase7_maturity_benchmark_not_met",
    ):
        if blocker not in written["certification_blockers"]:
            errors.append(f"current certification blocker missing: {blocker}")
    if written["phase7_proof_credit_allowed"] is not False:
        errors.append("Q7-17 grants Phase 7 proof credit")
    if written["live_capital_enabled"] is not False:
        errors.append("Q7-17 enables live capital")
    if written["q7_18_live_promotion_review_stage_allowed"] is not False:
        errors.append("Q7-17 allows Q7-18 before certification")
    if mature_certified_errors:
        errors.append(f"valid mature certification probe rejected: {mature_certified_errors}")
    if immature_operational_errors:
        errors.append(
            "valid immature operational-result probe rejected: "
            f"{immature_operational_errors}"
        )
    for label, probe_errors in (
        ("false certification", false_certified_errors),
        ("run incomplete", run_incomplete_errors),
        ("expectancy", expectancy_errors),
        ("drawdown", drawdown_errors),
        ("override", override_errors),
        ("postmortem", postmortem_errors),
        ("signal", signal_errors),
        ("hidden immaturity", hidden_immaturity_errors),
        ("proof credit", proof_credit_errors),
        ("live capital", live_capital_errors),
        ("broker/market write", broker_write_errors),
        ("Q7-18 early handoff", q7_18_errors),
        ("raw public payload", raw_payload_errors),
        ("source display mismatch", source_display_errors),
    ):
        if not probe_errors:
            errors.append(f"{label} probe was not rejected")

    if errors:
        print("phase7_certification_check=failed")
        for error in errors:
            print(f"error={error}")
        return 1
    print("phase7_certification_check=ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
