#!/usr/bin/env python3
"""Validate and write QSASE Phase 11 paper lifecycle and proof ledger V2 artifacts."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from orchestrator.config import Settings
from orchestrator.qsase_phase11_to14_completion import (
    PAPER_LIFECYCLE_RECORDS_V2_ARTIFACT,
    PAPER_LIFECYCLE_V2_ARTIFACT,
    PROOF_LEDGER_V2_ARTIFACT,
    PROOF_LINEAGE_RECORDS_V2_ARTIFACT,
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
    lifecycle = _load_json(runtime / PAPER_LIFECYCLE_V2_ARTIFACT)
    proof = _load_json(runtime / PROOF_LEDGER_V2_ARTIFACT)
    lifecycle_records = _read_jsonl(runtime / PAPER_LIFECYCLE_RECORDS_V2_ARTIFACT)
    proof_records = _read_jsonl(runtime / PROOF_LINEAGE_RECORDS_V2_ARTIFACT)
    validation_errors = list(errors)

    for filename in (
        PAPER_LIFECYCLE_V2_ARTIFACT,
        PAPER_LIFECYCLE_RECORDS_V2_ARTIFACT,
        PROOF_LEDGER_V2_ARTIFACT,
        PROOF_LINEAGE_RECORDS_V2_ARTIFACT,
    ):
        if not (runtime / filename).exists():
            validation_errors.append(f"{filename}_missing")

    validation_errors.extend(validate_payload(lifecycle, "qsase_paper_lifecycle_v2"))
    validation_errors.extend(validate_payload(proof, "qsase_proof_ledger_v2"))
    if len(lifecycle_records) != lifecycle.get("lifecycle_record_count"):
        validation_errors.append("lifecycle_record_count_mismatch")
    if len(proof_records) != proof.get("proof_lineage_record_count"):
        validation_errors.append("proof_lineage_record_count_mismatch")
    if lifecycle.get("ambiguous_lifecycle_count", 0):
        validation_errors.append("ambiguous_lifecycle_records_present")
    if proof.get("backtest_shadow_or_synthetic_proof_credit_count", 0):
        validation_errors.append("backtest_shadow_or_synthetic_proof_credit_present")

    print(f"lifecycle_artifact={written.get(PAPER_LIFECYCLE_V2_ARTIFACT)}")
    print(f"proof_artifact={written.get(PROOF_LEDGER_V2_ARTIFACT)}")
    print(f"lifecycle_status={lifecycle.get('status')}")
    print(f"lifecycle_record_count={lifecycle.get('lifecycle_record_count')}")
    print(f"ambiguous_lifecycle_count={lifecycle.get('ambiguous_lifecycle_count')}")
    print(f"stale_accepted_order_count={lifecycle.get('stale_accepted_order_count')}")
    print(f"proof_status={proof.get('status')}")
    print(f"closed_paper_trade_count={proof.get('closed_paper_trade_count')}")
    print(f"proof_eligible_count={proof.get('proof_eligible_count')}")
    print(f"proof_rejected_count={proof.get('proof_rejected_count')}")
    print(f"paper_order_created_count={proof.get('paper_order_created_count')}")
    print(f"broker_write_count={proof.get('broker_write_count')}")
    print(f"proof_credit_allowed={proof.get('proof_credit_allowed')}")
    print(f"live_capital_enabled={proof.get('live_capital_enabled')}")

    if validation_errors:
        for error in sorted(set(validation_errors)):
            print(f"error={error}")
        return 1
    if summary.get("proof", {}).get("proof_eligible_count") != proof.get("proof_eligible_count"):
        print("error=summary_proof_count_mismatch")
        return 1
    print("qsase_paper_lifecycle_proof_v2_check=ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
