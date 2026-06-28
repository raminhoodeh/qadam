#!/usr/bin/env python3
"""Validate and write QSASE-7 Strategy Foundry artifacts."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from orchestrator.config import Settings
from orchestrator.qsase_strategy_foundry import (
    DASHBOARD_SUMMARY_ARTIFACT,
    EVENTS_ARTIFACT,
    FAMILY_MAP_ARTIFACT,
    HISTORY_ARTIFACT,
    HYPOTHESES_ARTIFACT,
    PRIMARY_ARTIFACT,
    REJECTED_HYPOTHESES_ARTIFACT,
    _read_jsonl,
    _runtime_dir,
    build_and_write_strategy_hypotheses,
    load_strategy_hypotheses,
    validate_negative_strategy_foundry_probes,
    validate_strategy_hypotheses,
)


def _load_json(path: Path) -> dict:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> int:
    settings = Settings.from_env()
    payload, written, errors = build_and_write_strategy_hypotheses(settings)
    runtime_dir = _runtime_dir(settings)

    validation_errors = list(errors)
    for filename in (
        PRIMARY_ARTIFACT,
        HYPOTHESES_ARTIFACT,
        REJECTED_HYPOTHESES_ARTIFACT,
        FAMILY_MAP_ARTIFACT,
        EVENTS_ARTIFACT,
        HISTORY_ARTIFACT,
        DASHBOARD_SUMMARY_ARTIFACT,
    ):
        path = runtime_dir / filename
        if not path.exists():
            validation_errors.append(f"{filename}_missing")

    primary = _load_json(runtime_dir / PRIMARY_ARTIFACT)
    hypotheses = _read_jsonl(runtime_dir / HYPOTHESES_ARTIFACT)
    rejected = _read_jsonl(runtime_dir / REJECTED_HYPOTHESES_ARTIFACT)
    family_map = _load_json(runtime_dir / FAMILY_MAP_ARTIFACT)
    loaded = load_strategy_hypotheses(settings)
    if primary.get("generated_at") != payload.get("generated_at"):
        validation_errors.append("written_primary_generated_at_mismatch")
    if len(hypotheses) != payload.get("strategy_hypothesis_count"):
        validation_errors.append("written_strategy_hypothesis_count_mismatch")
    if len(rejected) != payload.get("rejected_pattern_count"):
        validation_errors.append("written_rejected_hypothesis_count_mismatch")
    if not family_map.get("known_families"):
        validation_errors.append("written_strategy_family_map_missing")
    validation_errors.extend(validate_strategy_hypotheses(loaded))
    validation_errors.extend(validate_negative_strategy_foundry_probes())

    print(f"artifact={written.get('strategy_foundry')}")
    print(f"strategy_hypotheses={written.get('strategy_hypotheses')}")
    print(f"rejected_strategy_hypotheses={written.get('rejected_strategy_hypotheses')}")
    print(f"strategy_family_map={written.get('strategy_family_map')}")
    print(f"dashboard_summary={written.get('dashboard_summary')}")
    print(f"phase_status={written.get('phase_status')}")
    print(f"implementation_log={written.get('implementation_log')}")
    print(f"status={payload.get('status')}")
    print(f"input_pattern_count={payload.get('input_pattern_count')}")
    print(f"strategy_hypothesis_count={payload.get('strategy_hypothesis_count')}")
    print(f"existing_family_match_count={payload.get('existing_family_match_count')}")
    print(f"new_family_proposal_count={payload.get('new_family_proposal_count')}")
    print(f"strategy_modification_proposal_count={payload.get('strategy_modification_proposal_count')}")
    print(f"shadow_only_monitor_count={payload.get('shadow_only_monitor_count')}")
    print(f"rejected_pattern_count={payload.get('rejected_pattern_count')}")
    print(f"paper_review_candidate_count={payload.get('paper_review_candidate_count')}")
    print(f"akber_filter_inputs_prepared_count={payload.get('akber_filter_inputs_prepared_count')}")
    print(f"shadow_replay_inputs_prepared_count={payload.get('shadow_replay_inputs_prepared_count')}")
    print(f"strategy_hypotheses_are_not_trades={payload.get('strategy_hypotheses_are_not_trades')}")
    print(f"trade_candidate_created={payload.get('trade_candidate_created')}")
    print(f"paper_order_allowed={payload.get('paper_order_allowed')}")
    if validation_errors:
        for error in validation_errors:
            print(f"error={error}")
        return 1
    print("qsase_strategy_foundry_check=ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
