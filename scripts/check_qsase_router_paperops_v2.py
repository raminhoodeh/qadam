#!/usr/bin/env python3
"""Validate and write QSASE Phase 10 Router and PaperOps handoff V2 artifacts."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from orchestrator.config import Settings
from orchestrator.qsase_phase5_to10_completion import (
    PAPEROPS_HANDOFF_RECORDS_V2_ARTIFACT,
    PAPEROPS_HANDOFF_V2_ARTIFACT,
    PAPEROPS_REJECTED_HANDOFFS_V2_ARTIFACT,
    ROUTER_DECISIONS_V2_ARTIFACT,
    ROUTER_SCOREBOARD_V2_ARTIFACT,
    ROUTER_V2_ARTIFACT,
    ROUTER_V2_DASHBOARD_ARTIFACT,
    WHY_NOT_V2_ARTIFACT,
    _runtime_dir,
    build_and_write_phase5_to10_completion,
    validate_payload,
)


def _load_json(path: Path) -> dict:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def _read_jsonl(path: Path) -> list[dict]:
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def main() -> int:
    settings = Settings.from_env()
    summary, written, errors = build_and_write_phase5_to10_completion(settings)
    runtime = _runtime_dir(settings)
    router = _load_json(runtime / ROUTER_V2_ARTIFACT)
    handoff = _load_json(runtime / PAPEROPS_HANDOFF_V2_ARTIFACT)
    decisions = _read_jsonl(runtime / ROUTER_DECISIONS_V2_ARTIFACT)
    handoffs = _read_jsonl(runtime / PAPEROPS_HANDOFF_RECORDS_V2_ARTIFACT)
    rejected_handoffs = _read_jsonl(runtime / PAPEROPS_REJECTED_HANDOFFS_V2_ARTIFACT)
    validation_errors = list(errors)

    for filename in (
        ROUTER_V2_ARTIFACT,
        ROUTER_DECISIONS_V2_ARTIFACT,
        ROUTER_SCOREBOARD_V2_ARTIFACT,
        WHY_NOT_V2_ARTIFACT,
        PAPEROPS_HANDOFF_V2_ARTIFACT,
        PAPEROPS_HANDOFF_RECORDS_V2_ARTIFACT,
        PAPEROPS_REJECTED_HANDOFFS_V2_ARTIFACT,
        ROUTER_V2_DASHBOARD_ARTIFACT,
    ):
        if not (runtime / filename).exists():
            validation_errors.append(f"{filename}_missing")

    validation_errors.extend(validate_payload(router, "qsase_strategy_router_v2"))
    validation_errors.extend(validate_payload(handoff, "qsase_paperops_handoff_v2"))
    if len(decisions) != router.get("decision_count"):
        validation_errors.append("router_decision_count_mismatch")
    if len(handoffs) != handoff.get("handoff_count"):
        validation_errors.append("paperops_handoff_count_mismatch")
    if len(rejected_handoffs) != handoff.get("rejected_handoff_count"):
        validation_errors.append("paperops_rejected_handoff_count_mismatch")

    print(f"router_artifact={written.get(ROUTER_V2_ARTIFACT)}")
    print(f"handoff_artifact={written.get(PAPEROPS_HANDOFF_V2_ARTIFACT)}")
    print(f"decisions={written.get(ROUTER_DECISIONS_V2_ARTIFACT)}")
    print(f"handoffs={written.get(PAPEROPS_HANDOFF_RECORDS_V2_ARTIFACT)}")
    print(f"rejected_handoffs={written.get(PAPEROPS_REJECTED_HANDOFFS_V2_ARTIFACT)}")
    print(f"router_status={router.get('status')}")
    print(f"router_decision_count={router.get('decision_count')}")
    print(f"paper_review_candidate_count={router.get('paper_review_candidate_count')}")
    print(f"router_handoff_count={router.get('handoff_count')}")
    print(f"handoff_status={handoff.get('status')}")
    print(f"paperops_handoff_count={handoff.get('handoff_count')}")
    print(f"rejected_handoff_count={handoff.get('rejected_handoff_count')}")
    print(f"paper_order_created_count={handoff.get('paper_order_created_count')}")
    print(f"broker_write_count={handoff.get('broker_write_count')}")
    print(f"proof_credit_allowed={handoff.get('proof_credit_allowed')}")
    print(f"live_capital_enabled={handoff.get('live_capital_enabled')}")

    if validation_errors:
        for error in sorted(set(validation_errors)):
            print(f"error={error}")
        return 1
    if summary.get("router", {}).get("paper_review_candidate_count") != router.get("paper_review_candidate_count"):
        print("error=summary_router_candidate_count_mismatch")
        return 1
    print("qsase_router_paperops_v2_check=ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
