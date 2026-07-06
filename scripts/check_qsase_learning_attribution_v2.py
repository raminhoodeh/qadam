#!/usr/bin/env python3
"""Validate and write QSASE Phase 12 learning attribution V2 artifacts."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from orchestrator.config import Settings
from orchestrator.qsase_phase11_to14_completion import (
    LEARNING_ATTRIBUTION_RECORDS_V2_ARTIFACT,
    LEARNING_ATTRIBUTION_V2_ARTIFACT,
    POLICY_PROPOSALS_V2_ARTIFACT,
    _runtime_dir,
    build_and_write_phase11_to14_completion,
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
    summary, written, errors = build_and_write_phase11_to14_completion(settings)
    runtime = _runtime_dir(settings)
    payload = _load_json(runtime / LEARNING_ATTRIBUTION_V2_ARTIFACT)
    records = _read_jsonl(runtime / LEARNING_ATTRIBUTION_RECORDS_V2_ARTIFACT)
    proposals = _read_jsonl(runtime / POLICY_PROPOSALS_V2_ARTIFACT)
    validation_errors = list(errors)

    for filename in (
        LEARNING_ATTRIBUTION_V2_ARTIFACT,
        LEARNING_ATTRIBUTION_RECORDS_V2_ARTIFACT,
        POLICY_PROPOSALS_V2_ARTIFACT,
    ):
        if not (runtime / filename).exists():
            validation_errors.append(f"{filename}_missing")

    validation_errors.extend(validate_payload(payload, "qsase_learning_attribution_v2"))
    if len(records) != payload.get("attribution_record_count"):
        validation_errors.append("learning_record_count_mismatch")
    if len(proposals) != payload.get("policy_proposal_count"):
        validation_errors.append("policy_proposal_count_mismatch")
    if any(proposal.get("applied") is True or proposal.get("apply_allowed") is True for proposal in proposals):
        validation_errors.append("policy_proposal_applied_or_apply_allowed")

    print(f"artifact={written.get(LEARNING_ATTRIBUTION_V2_ARTIFACT)}")
    print(f"records={written.get(LEARNING_ATTRIBUTION_RECORDS_V2_ARTIFACT)}")
    print(f"policy_proposals={written.get(POLICY_PROPOSALS_V2_ARTIFACT)}")
    print(f"status={payload.get('status')}")
    print(f"attribution_record_count={payload.get('attribution_record_count')}")
    print(f"policy_proposal_count={payload.get('policy_proposal_count')}")
    print(f"source_trust_proposal_count={payload.get('source_trust_proposal_count')}")
    print(f"strategy_weight_proposal_count={payload.get('strategy_weight_proposal_count')}")
    print(f"akber_threshold_proposal_count={payload.get('akber_threshold_proposal_count')}")
    print(f"model_routing_proposal_count={payload.get('model_routing_proposal_count')}")
    print(f"data_source_repair_proposal_count={payload.get('data_source_repair_proposal_count')}")
    print(f"policy_mutation_created={payload.get('policy_mutation_created')}")
    print(f"paper_order_created_count={payload.get('paper_order_created_count')}")
    print(f"broker_write_count={payload.get('broker_write_count')}")

    if validation_errors:
        for error in sorted(set(validation_errors)):
            print(f"error={error}")
        return 1
    if summary.get("learning", {}).get("policy_proposal_count") != payload.get("policy_proposal_count"):
        print("error=summary_learning_proposal_count_mismatch")
        return 1
    print("qsase_learning_attribution_v2_check=ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
