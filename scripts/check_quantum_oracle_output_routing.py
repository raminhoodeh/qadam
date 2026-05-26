#!/usr/bin/env python3
"""Validate the Q3-7 Head of Quant output routing contract."""

from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from orchestrator.intelligence import EvidenceItem, build_evidence_trail  # noqa: E402
from orchestrator.quantum import (  # noqa: E402
    build_quantum_oracle_job,
    run_quantum_oracle_job,
    validate_quantum_oracle_output_routing,
    validate_quantum_oracle_result,
)
from orchestrator.signal_integrity import build_signal_integrity_review  # noqa: E402


def _review() -> dict[str, Any]:
    now = datetime.now(timezone.utc).isoformat()
    evidence = (
        EvidenceItem(
            evidence_id="q3_7:yahoo:smh",
            source="market.yahoo_finance",
            event_type="market_price_confirmation",
            summary="SMH supplemental Yahoo Finance market confirmation for oracle output-routing probe.",
            trust_score=0.72,
            observed_at=now,
            raw_ref="q3_7_output_routing_probe",
        ),
        EvidenceItem(
            evidence_id="q3_7:alpaca:smh",
            source="market.alpaca_readonly",
            event_type="market_price_confirmation",
            summary="SMH independent read-only market confirmation for oracle output-routing probe.",
            trust_score=0.76,
            observed_at=now,
            raw_ref="q3_7_output_routing_probe",
        ),
        EvidenceItem(
            evidence_id="q3_7:rss:semiconductors",
            source="news.rss",
            event_type="news_observation",
            summary="Semiconductor supply-chain catalyst remains a shadow-only review item.",
            trust_score=0.74,
            observed_at=now,
            raw_ref="q3_7_output_routing_probe",
        ),
    )
    signal = {
        "schema_version": 1,
        "signal_id": "q3_7_quantum_oracle_output_probe",
        "status": "shadow_only",
        "title": "Q3-7 Head of Quant output-routing probe",
        "instrument_focus": "semiconductors",
        "thesis": "Synthetic upstream Signal Integrity review for oracle output-routing validation only.",
        "confidence": 0.71,
        "invalidation": "Synthetic probe only; no execution authority exists.",
        "evidence_trail": build_evidence_trail(evidence).to_dict(),
        "generated_by": "q3_7_oracle_output_routing_probe",
        "execution_allowed": False,
        "created_at": now,
    }
    return build_signal_integrity_review(signal).to_dict()


def _rejection_cases(routing: dict[str, Any]) -> dict[str, dict[str, Any]]:
    route_type = deepcopy(routing)
    route_type["route_type"] = "trade_candidate"

    unblocked_route = deepcopy(routing)
    unblocked_route["blocked_routes"]["risk_agent_approval"] = True

    nonzero_count = deepcopy(routing)
    nonzero_count["execution_policy_approval_count"] = 1

    authority = deepcopy(routing)
    authority["execution_allowed"] = True

    strategy_write = deepcopy(routing)
    strategy_write["strategy_lead_context"]["context_only"] = False

    bad_recommendation = deepcopy(routing)
    bad_recommendation["recommendation_class"] = "buy"

    return {
        "route_type": route_type,
        "unblocked_route": unblocked_route,
        "nonzero_downstream_count": nonzero_count,
        "authority_enabled": authority,
        "strategy_context_write": strategy_write,
        "bad_recommendation": bad_recommendation,
    }


def main() -> int:
    review = _review()
    job = build_quantum_oracle_job(review, job_type="strategy_collapse")
    result = run_quantum_oracle_job(job)
    validate_quantum_oracle_result(result)
    validate_quantum_oracle_output_routing(result.output_routing)

    routing = result.output_routing
    print("quantum_oracle_output_routing_status=" + routing["status"])
    print("quantum_oracle_output_route_type=" + routing["route_type"])
    print("quantum_oracle_output_storage_type=" + routing["storage_type"])
    print("quantum_oracle_output_annotation_target=" + routing["annotation_target"])
    print("quantum_oracle_output_recommendation_class=" + routing["recommendation_class"])
    print(f"quantum_oracle_output_trade_candidate_created_count={routing['trade_candidate_created_count']}")
    print(f"quantum_oracle_output_risk_approval_count={routing['risk_approval_count']}")
    print(f"quantum_oracle_output_execution_policy_approval_count={routing['execution_policy_approval_count']}")
    print(f"quantum_oracle_output_staged_paper_order_created_count={routing['staged_paper_order_created_count']}")
    print(f"quantum_oracle_output_broker_reconciliation_write_count={routing['broker_reconciliation_write_count']}")
    print(f"quantum_oracle_output_paper_submit_receipt_created_count={routing['paper_submit_receipt_created_count']}")

    if routing["route_type"] != "shadow_annotation":
        print("quantum_oracle_output_route_not_shadow_annotation=true")
        return 1
    if routing["storage_type"] != "oracle_review_result":
        print("quantum_oracle_output_storage_not_review_result=true")
        return 1
    if any(value is not False for value in routing["blocked_routes"].values()):
        print("quantum_oracle_output_downstream_route_unblocked=true")
        return 1

    for case_name, candidate in _rejection_cases(routing).items():
        try:
            validate_quantum_oracle_output_routing(candidate)
        except ValueError:
            print(f"quantum_oracle_output_rejection_probe={case_name}:rejected")
            continue
        print(f"quantum_oracle_output_rejection_probe_failed={case_name}")
        return 1

    print("quantum_oracle_output_routing_check=ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
