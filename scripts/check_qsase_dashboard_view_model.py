#!/usr/bin/env python3
"""Validate and write QSASE-13 dashboard view-model artifacts."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from orchestrator.config import Settings
from orchestrator.qsase_dashboard_view_model import (
    ANTI_SLOP_ARTIFACT,
    CURRENT_PORTFOLIO_ARTIFACT,
    DECISION_RECORDS_ARTIFACT,
    EVENTS_ARTIFACT,
    HISTORY_ARTIFACT,
    LEARNING_LEDGER_ARTIFACT,
    PATTERN_TO_PAPER_WORKFLOW_ARTIFACT,
    PATTERN_LAB_ARTIFACT,
    PORTFOLIO_SERIES_ARTIFACT,
    REPAIR_QUEUE_ARTIFACT,
    SOURCE_NETWORK_ARTIFACT,
    STATUS_ARTIFACT,
    STRATEGY_UNIVERSE_ARTIFACT,
    SYSTEM_MAP_ARTIFACT,
    TRADE_INTENTS_ARTIFACT,
    TRADING_HISTORY_ARTIFACT,
    _runtime_dir,
    build_and_write_dashboard_view_model,
    load_dashboard_view_model,
    validate_dashboard_view_model,
    validate_negative_dashboard_view_model_probes,
)


def _load_json(path: Path) -> dict:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> int:
    settings = Settings.from_env()
    payload, written, errors = build_and_write_dashboard_view_model(settings)
    runtime_dir = _runtime_dir(settings)

    validation_errors = list(errors)
    for filename in (
        STATUS_ARTIFACT,
        DECISION_RECORDS_ARTIFACT,
        SYSTEM_MAP_ARTIFACT,
        PORTFOLIO_SERIES_ARTIFACT,
        CURRENT_PORTFOLIO_ARTIFACT,
        TRADING_HISTORY_ARTIFACT,
        SOURCE_NETWORK_ARTIFACT,
        STRATEGY_UNIVERSE_ARTIFACT,
        PATTERN_LAB_ARTIFACT,
        TRADE_INTENTS_ARTIFACT,
        PATTERN_TO_PAPER_WORKFLOW_ARTIFACT,
        LEARNING_LEDGER_ARTIFACT,
        REPAIR_QUEUE_ARTIFACT,
        ANTI_SLOP_ARTIFACT,
        HISTORY_ARTIFACT,
        EVENTS_ARTIFACT,
    ):
        if not (runtime_dir / filename).exists():
            validation_errors.append(f"{filename}_missing")

    primary = _load_json(runtime_dir / STATUS_ARTIFACT)
    loaded = load_dashboard_view_model(settings)
    if primary.get("generated_at") != payload.get("generated_at"):
        validation_errors.append("written_status_generated_at_mismatch")
    validation_errors.extend(validate_dashboard_view_model(loaded))
    validation_errors.extend(validate_negative_dashboard_view_model_probes())

    print(f"status_artifact={written.get('status')}")
    print(f"decision_records={written.get('decision_records')}")
    print(f"system_map={written.get('system_map')}")
    print(f"portfolio_value={written.get('portfolio_value')}")
    print(f"current_portfolio={written.get('current_portfolio')}")
    print(f"trading_history={written.get('trading_history')}")
    print(f"source_network={written.get('source_network')}")
    print(f"strategy_universe={written.get('strategy_universe')}")
    print(f"pattern_lab={written.get('pattern_lab')}")
    print(f"trade_intents={written.get('trade_intents')}")
    print(f"pattern_to_paper_workflow={written.get('pattern_to_paper_workflow')}")
    print(f"learning_ledger={written.get('learning_ledger')}")
    print(f"repair_queue={written.get('repair_queue')}")
    print(f"anti_slop={written.get('anti_slop')}")
    print(f"phase_status={written.get('phase_status')}")
    print(f"implementation_log={written.get('implementation_log')}")
    print(f"status={payload.get('status')}")
    print(f"portfolio_value_series_count={payload.get('portfolio_value_series_count')}")
    print(f"current_position_count={payload.get('current_position_count')}")
    print(f"trading_history_row_count={payload.get('trading_history_row_count')}")
    print(f"source_category_row_count={payload.get('source_category_row_count')}")
    print(f"source_row_count={payload.get('source_row_count')}")
    print(f"trading_universe_row_count={payload.get('trading_universe_row_count')}")
    print(f"all_strategy_count={payload.get('all_strategy_count')}")
    print(f"currently_in_play_count={payload.get('currently_in_play_count')}")
    print(f"linear_pattern_count={payload.get('linear_pattern_count')}")
    print(f"nonlinear_pattern_count={payload.get('nonlinear_pattern_count')}")
    print(f"trade_intent_count={payload.get('trade_intent_count')}")
    print(f"pattern_workflow_record_count={payload.get('pattern_workflow_record_count')}")
    print(f"pattern_workflow_handoff_candidate_count={payload.get('pattern_workflow_handoff_candidate_count')}")
    print(f"pattern_workflow_telegram_candidate_count={payload.get('pattern_workflow_telegram_candidate_count')}")
    print(f"learning_ledger_row_count={payload.get('learning_ledger_row_count')}")
    print(f"repair_queue_count={payload.get('repair_queue_count')}")
    print(f"stale_labeled_count={payload.get('stale_labeled_count')}")
    print(f"anti_slop_error_count={payload.get('anti_slop_audit', {}).get('error_count')}")
    print(f"applied_change_count={payload.get('applied_change_count')}")
    print(f"paper_order_created_count={payload.get('paper_order_created_count')}")
    print(f"broker_write_count={payload.get('broker_write_count')}")
    print(f"proof_credit_allowed={payload.get('proof_credit_allowed')}")
    print(f"live_capital_enabled={payload.get('live_capital_enabled')}")
    if validation_errors:
        for error in validation_errors:
            print(f"error={error}")
        return 1
    print("qsase_dashboard_view_model_check=ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
