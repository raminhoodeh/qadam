#!/usr/bin/env python3
"""Validate and write QSASE-10 Strategy Router artifacts."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from orchestrator.config import Settings
from orchestrator.qsase_strategy_router import (
    DASHBOARD_SUMMARY_ARTIFACT,
    DECISIONS_ARTIFACT,
    EVENTS_ARTIFACT,
    HARD_VETOES_ARTIFACT,
    HISTORY_ARTIFACT,
    PRIMARY_ARTIFACT,
    SCOREBOARD_ARTIFACT,
    SOFT_BLOCKERS_ARTIFACT,
    WHY_NOT_ARTIFACT,
    _read_jsonl,
    _runtime_dir,
    build_and_write_strategy_router_decisions,
    load_strategy_router_decisions,
    validate_negative_strategy_router_probes,
    validate_strategy_router_decisions,
)


def _load_json(path: Path) -> dict:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> int:
    settings = Settings.from_env()
    payload, written, errors = build_and_write_strategy_router_decisions(settings)
    runtime_dir = _runtime_dir(settings)

    validation_errors = list(errors)
    for filename in (
        PRIMARY_ARTIFACT,
        DECISIONS_ARTIFACT,
        SCOREBOARD_ARTIFACT,
        WHY_NOT_ARTIFACT,
        HARD_VETOES_ARTIFACT,
        SOFT_BLOCKERS_ARTIFACT,
        EVENTS_ARTIFACT,
        HISTORY_ARTIFACT,
        DASHBOARD_SUMMARY_ARTIFACT,
    ):
        path = runtime_dir / filename
        if not path.exists():
            validation_errors.append(f"{filename}_missing")

    primary = _load_json(runtime_dir / PRIMARY_ARTIFACT)
    decisions = _read_jsonl(runtime_dir / DECISIONS_ARTIFACT)
    hard_vetoes = _read_jsonl(runtime_dir / HARD_VETOES_ARTIFACT)
    soft_blockers = _read_jsonl(runtime_dir / SOFT_BLOCKERS_ARTIFACT)
    scoreboard = _load_json(runtime_dir / SCOREBOARD_ARTIFACT)
    why_not = _load_json(runtime_dir / WHY_NOT_ARTIFACT)
    loaded = load_strategy_router_decisions(settings)

    if primary.get("generated_at") != payload.get("generated_at"):
        validation_errors.append("written_primary_generated_at_mismatch")
    if len(decisions) != payload.get("strategy_input_count"):
        validation_errors.append("written_router_decision_count_mismatch")
    if len(hard_vetoes) != payload.get("hard_veto_count"):
        validation_errors.append("written_hard_veto_count_mismatch")
    if len(soft_blockers) != payload.get("soft_blocker_count"):
        validation_errors.append("written_soft_blocker_count_mismatch")
    if scoreboard.get("ranked_count") != payload.get("strategy_input_count"):
        validation_errors.append("written_scoreboard_ranked_count_mismatch")
    if why_not.get("reason") != payload.get("why_not_trading_now", {}).get("reason"):
        validation_errors.append("written_why_not_trading_now_mismatch")
    validation_errors.extend(validate_strategy_router_decisions(loaded))
    validation_errors.extend(validate_negative_strategy_router_probes())

    print(f"artifact={written.get('strategy_router')}")
    print(f"router_decisions={written.get('router_decisions')}")
    print(f"scoreboard={written.get('scoreboard')}")
    print(f"why_not_trading_now={written.get('why_not_trading_now')}")
    print(f"hard_vetoes={written.get('hard_vetoes')}")
    print(f"soft_blockers={written.get('soft_blockers')}")
    print(f"dashboard_summary={written.get('dashboard_summary')}")
    print(f"phase_status={written.get('phase_status')}")
    print(f"implementation_log={written.get('implementation_log')}")
    print(f"status={payload.get('status')}")
    print(f"strategy_input_count={payload.get('strategy_input_count')}")
    print(f"paper_review_candidate_count={payload.get('paper_review_candidate_count')}")
    print(f"blocked_safety_boundary_count={payload.get('blocked_safety_boundary_count')}")
    print(f"reject_count={payload.get('reject_count')}")
    print(f"hold_count={payload.get('hold_count')}")
    print(f"shadow_only_count={payload.get('shadow_only_count')}")
    print(f"watchlist_only_count={payload.get('watchlist_only_count')}")
    print(f"repair_requested_count={payload.get('repair_requested_count')}")
    print(f"hard_veto_count={payload.get('hard_veto_count')}")
    print(f"soft_blocker_count={payload.get('soft_blocker_count')}")
    print(f"why_not_trading_now_reason={payload.get('why_not_trading_now', {}).get('reason')}")
    print(f"paper_order_allowed={payload.get('paper_order_allowed')}")
    print(f"broker_write_allowed={payload.get('broker_write_allowed')}")
    print(f"proof_credit_allowed={payload.get('proof_credit_allowed')}")
    if validation_errors:
        for error in validation_errors:
            print(f"error={error}")
        return 1
    print("qsase_strategy_router_check=ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
