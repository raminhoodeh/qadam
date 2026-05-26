#!/usr/bin/env python3
"""Validate Qadam strategy research intake."""

from __future__ import annotations

from copy import deepcopy
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from orchestrator.config import Settings  # noqa: E402
from orchestrator.strategy_research_intake import (  # noqa: E402
    STRATEGY_RESEARCH_INTAKE_SCHEMA_VERSION,
    build_strategy_research_intake,
    validate_strategy_research_intake,
    write_strategy_research_intake,
)


def main() -> int:
    errors: list[str] = []
    settings = Settings.from_env()
    artifact = build_strategy_research_intake(settings)
    output_path, history_path, event_path, written = write_strategy_research_intake(
        artifact,
        settings,
        record_event=True,
    )
    validation_errors = validate_strategy_research_intake(written)

    authority_probe = deepcopy(written)
    authority_probe["candidate_records"][0]["trade_candidate_creation_allowed"] = True
    authority_errors = validate_strategy_research_intake(authority_probe)

    execution_probe = deepcopy(written)
    execution_probe["decision_engine_context"]["execution_allowed"] = True
    execution_errors = validate_strategy_research_intake(execution_probe)

    missing_challenge_probe = deepcopy(written)
    missing_challenge_probe["decision_engine_context"]["strategy_lead_challenge_count"] = 0
    missing_challenge_probe["decision_engine_context"]["strategy_lead_challenges"] = []
    missing_challenge_errors = validate_strategy_research_intake(missing_challenge_probe)

    context = written["decision_engine_context"]

    print(f"strategy_research_intake_status={written['status']}")
    print(f"strategy_research_intake_schema_version={STRATEGY_RESEARCH_INTAKE_SCHEMA_VERSION}")
    print(f"strategy_research_intake_artifact_path={output_path}")
    print(f"strategy_research_intake_history_path={history_path}")
    print(f"strategy_research_intake_event_log_path={event_path}")
    print(f"strategy_research_intake_source_note_exists={written['source_note_exists']}")
    print(f"strategy_research_intake_candidate_count={written['candidate_count']}")
    print(f"strategy_research_intake_candidate_refs={','.join(context['candidate_refs'])}")
    print(f"strategy_research_intake_best_initial_candidate={context['best_initial_research_candidate']}")
    print(f"strategy_research_intake_benchmark_candidate={context['benchmark_candidate']}")
    print(f"strategy_research_intake_strategy_lead_challenge_count={context['strategy_lead_challenge_count']}")
    print(f"strategy_research_intake_active_decision_candidate_count={context['active_decision_candidate_count']}")
    print(
        "strategy_research_intake_trade_candidate_creation_allowed="
        f"{written['trade_candidate_creation_allowed']}"
    )
    print(f"strategy_research_intake_risk_handoff_allowed={written['risk_handoff_allowed']}")
    print(f"strategy_research_intake_execution_allowed={written['execution_allowed']}")
    print(f"strategy_research_intake_paper_order_allowed={written['paper_order_allowed']}")
    print(f"strategy_research_intake_broker_write_allowed={written['broker_write_allowed']}")
    print(f"strategy_research_intake_live_capital_enabled={written['live_capital_enabled']}")
    print(f"strategy_research_intake_validation_error_count={len(validation_errors)}")
    print(f"strategy_research_intake_authority_probe_error_count={len(authority_errors)}")
    print(f"strategy_research_intake_execution_probe_error_count={len(execution_errors)}")
    print(f"strategy_research_intake_missing_challenge_probe_error_count={len(missing_challenge_errors)}")

    if validation_errors:
        errors.extend(validation_errors)
    if written["candidate_count"] != 4:
        errors.append("candidate_count_not_four")
    if not written["source_note_exists"]:
        errors.append("source_note_missing")
    if context["best_initial_research_candidate"] != "pead_long_only_concordant":
        errors.append("best_initial_candidate_mismatch")
    if context["benchmark_candidate"] != "trend_following_baseline_control":
        errors.append("benchmark_candidate_mismatch")
    if context["active_decision_candidate_count"] != 0:
        errors.append("active_decision_candidate_nonzero")
    if context["strategy_lead_challenge_count"] < 4:
        errors.append("strategy_lead_challenges_missing")
    for field in (
        "trade_candidate_creation_allowed",
        "risk_handoff_allowed",
        "execution_allowed",
        "paper_order_allowed",
        "broker_write_allowed",
        "live_capital_enabled",
    ):
        if written[field] is not False:
            errors.append(f"artifact_authority_enabled:{field}")
        if context[field] is not False:
            errors.append(f"context_authority_enabled:{field}")
    if not any(
        error.startswith("strategy_research_candidate_authority_enabled:")
        for error in authority_errors
    ):
        errors.append("authority_probe_not_rejected")
    if "strategy_research_decision_context_authority_enabled:execution_allowed" not in execution_errors:
        errors.append("execution_probe_not_rejected")
    if "strategy_research_strategy_lead_challenges_missing" not in missing_challenge_errors:
        errors.append("missing_challenge_probe_not_rejected")

    if errors:
        for error in errors:
            print(f"strategy_research_intake_error={error}")
        print("strategy_research_intake_check=failed")
        return 1

    print("strategy_research_intake_check=ok")
    print("strategy_research_intake_boundary=decision context only; no trade authority")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
