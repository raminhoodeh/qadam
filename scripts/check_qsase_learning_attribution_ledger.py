#!/usr/bin/env python3
"""Validate and write QSASE-12 Learning And Attribution Ledger artifacts."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from orchestrator.config import Settings
from orchestrator.qsase_learning_attribution_ledger import (
    DASHBOARD_SUMMARY_ARTIFACT,
    EVENTS_ARTIFACT,
    FILTER_THRESHOLD_PROPOSALS_ARTIFACT,
    HISTORY_ARTIFACT,
    LEARNING_APPROVAL_QUEUE_ARTIFACT,
    LEDGER_JSONL_ARTIFACT,
    MODEL_WEIGHT_PROPOSALS_ARTIFACT,
    PRIMARY_ARTIFACT,
    SOURCE_TRUST_PROPOSALS_ARTIFACT,
    STRATEGY_WEIGHT_PROPOSALS_ARTIFACT,
    _read_jsonl,
    _runtime_dir,
    build_and_write_learning_attribution_ledger,
    load_learning_attribution_ledger,
    validate_learning_attribution_ledger,
    validate_negative_learning_attribution_ledger_probes,
)


def _load_json(path: Path) -> dict:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> int:
    settings = Settings.from_env()
    payload, written, errors = build_and_write_learning_attribution_ledger(settings)
    runtime_dir = _runtime_dir(settings)

    validation_errors = list(errors)
    for filename in (
        PRIMARY_ARTIFACT,
        LEDGER_JSONL_ARTIFACT,
        STRATEGY_WEIGHT_PROPOSALS_ARTIFACT,
        SOURCE_TRUST_PROPOSALS_ARTIFACT,
        MODEL_WEIGHT_PROPOSALS_ARTIFACT,
        FILTER_THRESHOLD_PROPOSALS_ARTIFACT,
        LEARNING_APPROVAL_QUEUE_ARTIFACT,
        DASHBOARD_SUMMARY_ARTIFACT,
        HISTORY_ARTIFACT,
        EVENTS_ARTIFACT,
    ):
        path = runtime_dir / filename
        if not path.exists():
            validation_errors.append(f"{filename}_missing")

    primary = _load_json(runtime_dir / PRIMARY_ARTIFACT)
    records = _read_jsonl(runtime_dir / LEDGER_JSONL_ARTIFACT)
    loaded = load_learning_attribution_ledger(settings)

    if primary.get("generated_at") != payload.get("generated_at"):
        validation_errors.append("written_primary_generated_at_mismatch")
    if len(records) != payload.get("attribution_record_count"):
        validation_errors.append("written_attribution_record_count_mismatch")
    validation_errors.extend(validate_learning_attribution_ledger(loaded))
    validation_errors.extend(validate_negative_learning_attribution_ledger_probes())

    print(f"artifact={written.get('component_attribution_ledger')}")
    print(f"ledger_records={written.get('ledger_records')}")
    print(f"strategy_weight_proposals={written.get('strategy_weight_proposals')}")
    print(f"source_trust_proposals={written.get('source_trust_proposals')}")
    print(f"model_weight_proposals={written.get('model_weight_proposals')}")
    print(f"filter_threshold_proposals={written.get('filter_threshold_proposals')}")
    print(f"learning_approval_queue={written.get('learning_approval_queue')}")
    print(f"dashboard_summary={written.get('dashboard_summary')}")
    print(f"phase_status={written.get('phase_status')}")
    print(f"implementation_log={written.get('implementation_log')}")
    print(f"status={payload.get('status')}")
    print(f"attribution_record_count={payload.get('attribution_record_count')}")
    print(f"real_paper_lifecycle_record_count={payload.get('real_paper_lifecycle_record_count')}")
    print(f"non_trade_record_count={payload.get('non_trade_record_count')}")
    print(f"shadow_replay_record_count={payload.get('shadow_replay_record_count')}")
    print(f"backtest_record_count={payload.get('backtest_record_count')}")
    print(f"rejected_hypothesis_record_count={payload.get('rejected_hypothesis_record_count')}")
    print(f"blocked_route_record_count={payload.get('blocked_route_record_count')}")
    print(f"system_defect_record_count={payload.get('system_defect_record_count')}")
    print(f"strategy_weight_proposal_count={payload.get('strategy_weight_proposal_count')}")
    print(f"source_trust_proposal_count={payload.get('source_trust_proposal_count')}")
    print(f"model_weight_proposal_count={payload.get('model_weight_proposal_count')}")
    print(f"filter_threshold_proposal_count={payload.get('filter_threshold_proposal_count')}")
    print(f"approval_required_count={payload.get('approval_required_count')}")
    print(f"approved_proposal_count={payload.get('approved_proposal_count')}")
    print(f"applied_update_count={payload.get('applied_update_count')}")
    print(f"learning_write_created={payload.get('learning_write_created')}")
    print(f"strategy_mutation_created={payload.get('strategy_mutation_created')}")
    print(f"policy_mutation_created={payload.get('policy_mutation_created')}")
    print(f"model_weight_update_created={payload.get('model_weight_update_created')}")
    print(f"trust_score_update_created={payload.get('trust_score_update_created')}")
    print(f"paper_order_created_count={payload.get('paper_order_created_count')}")
    print(f"broker_write_count={payload.get('broker_write_count')}")
    print(f"proof_credit_allowed={payload.get('proof_credit_allowed')}")
    print(f"live_capital_enabled={payload.get('live_capital_enabled')}")
    if validation_errors:
        for error in validation_errors:
            print(f"error={error}")
        return 1
    print("qsase_learning_attribution_ledger_check=ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
