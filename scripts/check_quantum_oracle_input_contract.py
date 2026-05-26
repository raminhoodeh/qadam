#!/usr/bin/env python3
"""Validate the Q3-6 Head of Quant input contract."""

from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timedelta, timezone
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from orchestrator.intelligence import EvidenceItem, build_evidence_trail  # noqa: E402
from orchestrator.quantum import (  # noqa: E402
    build_quantum_oracle_job,
    quantum_oracle_input_contract,
    validate_quantum_oracle_input_contract,
)
from orchestrator.signal_integrity import build_signal_integrity_review  # noqa: E402


def _review(*, observed_at: str | None = None) -> dict[str, Any]:
    now = observed_at or datetime.now(timezone.utc).isoformat()
    evidence = (
        EvidenceItem(
            evidence_id="q3_6:yahoo:smh",
            source="market.yahoo_finance",
            event_type="market_price_confirmation",
            summary="SMH supplemental Yahoo Finance market confirmation for oracle input-contract probe.",
            trust_score=0.72,
            observed_at=now,
            raw_ref="q3_6_contract_probe",
        ),
        EvidenceItem(
            evidence_id="q3_6:alpaca:smh",
            source="market.alpaca_readonly",
            event_type="market_price_confirmation",
            summary="SMH independent read-only market confirmation for oracle input-contract probe.",
            trust_score=0.76,
            observed_at=now,
            raw_ref="q3_6_contract_probe",
        ),
        EvidenceItem(
            evidence_id="q3_6:rss:semiconductors",
            source="news.rss",
            event_type="news_observation",
            summary="Semiconductor supply-chain catalyst remains a shadow-only review item.",
            trust_score=0.74,
            observed_at=now,
            raw_ref="q3_6_contract_probe",
        ),
    )
    signal = {
        "schema_version": 1,
        "signal_id": "q3_6_quantum_oracle_input_probe",
        "status": "shadow_only",
        "title": "Q3-6 Head of Quant input-contract probe",
        "instrument_focus": "semiconductors",
        "thesis": "Synthetic upstream Signal Integrity review for oracle input-contract validation only.",
        "confidence": 0.71,
        "invalidation": "Synthetic probe only; no execution authority exists.",
        "evidence_trail": build_evidence_trail(evidence).to_dict(),
        "generated_by": "q3_6_oracle_input_contract_probe",
        "execution_allowed": False,
        "created_at": now,
    }
    return build_signal_integrity_review(signal).to_dict()


def _certified_shadow_review_packet(valid_review: dict[str, Any]) -> dict[str, Any]:
    return {
        "source_type": "certified_shadow_review_packet",
        "packet_id": "q3_6_certified_shadow_review_packet",
        "certified_shadow_review": True,
        "watch_focus": valid_review["instrument_focus"],
        "market_confirmation_policy": valid_review["market_confirmation_policy"],
        "durable_evidence_context": {
            "status": "ok",
            "mode": "durable_replay",
            "durable_replay_status": "ok",
            "durable_replay_contract_status": "durable_phase2_replay_ready",
            "durable_replay_replayed_source_count": 6,
            "durable_replay_missing_source_count": 0,
            "source_degraded_count": 0,
            "write_authority": False,
            "signal_authority": False,
            "order_authority": False,
        },
        "certification": {
            "certified_shadow_review": True,
            "source_signal_id": valid_review["source_signal_id"],
            "signal_integrity_boundary": valid_review["boundary"],
            "evidence_item_count": valid_review["evidence_item_count"],
            "source_count": valid_review["source_count"],
            "average_trust_score": valid_review["average_trust_score"],
            "min_trust_score": valid_review["min_trust_score"],
            "signal_confidence": valid_review["signal_confidence"],
            "missing_correlations": valid_review["missing_correlations"],
            "execution_allowed": False,
            "paper_order_allowed": False,
            "trade_candidate_created": False,
        },
        "execution_allowed": False,
        "paper_order_allowed": False,
        "trade_candidate_created": False,
    }


def _rejection_cases(valid_review: dict[str, Any]) -> dict[str, tuple[dict[str, Any], str]]:
    stale_time = (datetime.now(timezone.utc) - timedelta(days=5)).isoformat()
    stale = deepcopy(valid_review)
    stale["market_confirmation_policy"]["status"] = "market_confirmation_stale"
    stale["market_confirmation_policy"]["stale"] = True
    stale["market_confirmation_policy"]["latest_observed_at"] = stale_time

    unavailable = deepcopy(valid_review)
    unavailable["market_confirmation_policy"]["status"] = "market_confirmation_unavailable"
    unavailable["market_confirmation_policy"]["unavailable"] = True

    yahoo_only = deepcopy(valid_review)
    yahoo_only["market_confirmation_policy"]["providers"] = ["market.yahoo_finance"]
    yahoo_only["market_confirmation_policy"]["uses_yahoo_finance"] = True
    yahoo_only["market_confirmation_policy"]["single_source_hold"] = False
    yahoo_only["market_confirmation_policy"]["status"] = "market_confirmation_corroboration_available"

    missing_evidence = deepcopy(valid_review)
    missing_evidence["evidence_item_count"] = 0

    execution_authority = deepcopy(valid_review)
    execution_authority["execution_allowed"] = True

    missing_boundary = deepcopy(valid_review)
    missing_boundary["boundary"] = "Shadow context lacks Signal Integrity boundary."

    missing_policy = deepcopy(valid_review)
    missing_policy.pop("market_confirmation_policy", None)

    return {
        "missing_evidence": (missing_evidence, "missing_evidence"),
        "stale_market_confirmation": (stale, "market_confirmation_stale"),
        "unavailable_market_confirmation": (unavailable, "market_confirmation_unavailable"),
        "yahoo_only_market_confirmation": (yahoo_only, "single_source_yahoo_only_market_confirmation"),
        "execution_authority": (execution_authority, "execution_authority_already_set"),
        "missing_signal_integrity_boundary": (missing_boundary, "missing_signal_integrity_boundary"),
        "missing_market_confirmation_policy": (missing_policy, "missing_market_confirmation_policy"),
    }


def main() -> int:
    valid_review = _review()
    valid_contract = quantum_oracle_input_contract(valid_review)
    validate_quantum_oracle_input_contract(valid_contract)
    valid_job = build_quantum_oracle_job(valid_review, job_type="pattern_recognition")
    validate_quantum_oracle_input_contract(valid_job.input_contract)

    certified_packet = _certified_shadow_review_packet(valid_review)
    certified_contract = quantum_oracle_input_contract(certified_packet)
    validate_quantum_oracle_input_contract(certified_contract)

    print("quantum_oracle_input_contract_status=" + valid_contract["status"])
    print("quantum_oracle_input_source_type=" + valid_contract["source_type"])
    print("quantum_oracle_input_market_confirmation_status=" + valid_contract["market_confirmation_status"])
    print("quantum_oracle_input_yahoo_finance_role=" + valid_contract["yahoo_finance_role"])
    print(f"quantum_oracle_input_yahoo_only_market_confirmation={valid_contract['yahoo_only_market_confirmation']}")
    print(
        "quantum_oracle_certified_packet_durable_status="
        f"{certified_contract['durable_evidence_context']['status']}"
    )

    for case_name, (candidate, expected_reason) in _rejection_cases(valid_review).items():
        contract = quantum_oracle_input_contract(candidate)
        validate_quantum_oracle_input_contract(contract, require_accepted=False)
        print(f"quantum_oracle_input_rejection_probe={case_name}:{contract['rejection_reasons']}")
        if contract["status"] != "rejected":
            print(f"quantum_oracle_input_rejection_not_rejected={case_name}")
            return 1
        if expected_reason not in contract["rejection_reasons"]:
            print(f"quantum_oracle_input_rejection_reason_missing={case_name}:{expected_reason}")
            return 1
        try:
            build_quantum_oracle_job(candidate, job_type="strategy_collapse")
        except ValueError:
            continue
        print(f"quantum_oracle_input_rejection_created_job={case_name}")
        return 1

    print("quantum_oracle_input_contract_check=ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
