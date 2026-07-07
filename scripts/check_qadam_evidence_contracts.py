#!/usr/bin/env python3
"""Build and certify Qadam Phase 2 evidence-native contracts."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from orchestrator.config import Settings
from orchestrator.qadam_evidence_contracts import (
    CONTRACT_ARTIFACTS,
    DASHBOARD_SUMMARY_ARTIFACT,
    PRIMARY_ARTIFACT,
    SUMMARY_ARTIFACT,
    _paths,
    build_and_write_evidence_contracts,
    build_evidence_contracts,
    load_evidence_contracts,
    validate_evidence_contract_bundle,
    validate_negative_evidence_contract_probes,
)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    settings = Settings.from_env()
    if args.dry_run:
        bundle = build_evidence_contracts(settings)
        written: dict[str, str] = {}
        validation_errors = validate_evidence_contract_bundle(
            {
                "primary": bundle.primary,
                "summary": bundle.summary,
                "dashboard_summary": bundle.dashboard_summary,
                "records_by_type": bundle.records_by_type,
            }
        )
    else:
        bundle, written, validation_errors = build_and_write_evidence_contracts(settings)
        validation_errors.extend(validate_negative_evidence_contract_probes(settings))
        loaded = load_evidence_contracts(settings)
        validation_errors.extend(validate_evidence_contract_bundle(loaded))
        paths = _paths(settings)
        for path_key in ("primary", "summary", "dashboard_summary", *CONTRACT_ARTIFACTS):
            if not paths[path_key].exists():
                validation_errors.append(f"{paths[path_key].name}_missing")

    summary = bundle.summary
    dashboard = bundle.dashboard_summary
    print(f"primary={written.get('primary', PRIMARY_ARTIFACT)}")
    print(f"summary={written.get('summary', SUMMARY_ARTIFACT)}")
    print(f"dashboard_summary={written.get('dashboard_summary', DASHBOARD_SUMMARY_ARTIFACT)}")
    print(f"status={summary.get('status')}")
    print(f"contract_type_count={summary.get('contract_type_count')}")
    print(f"total_contract_count={summary.get('total_contract_count')}")
    print(f"missing_evidence_count={summary.get('missing_evidence_count')}")
    print(f"contracts_with_missing_evidence_count={summary.get('contracts_with_missing_evidence_count')}")
    for contract_type, count in sorted(summary.get("contract_counts", {}).items()):
        print(f"{contract_type}_count={count}")
    print(f"downstream_reader_state={dashboard.get('downstream_reader_state')}")
    print(f"paper_order_created_count={summary.get('paper_order_created_count')}")
    print(f"broker_write_count={summary.get('broker_write_count')}")
    print(f"live_capital_enabled={summary.get('live_capital_enabled')}")
    print(f"proof_credit_allowed={summary.get('proof_credit_allowed')}")
    print(f"validation_error_count={len(set(validation_errors))}")
    if validation_errors:
        for error in sorted(set(validation_errors)):
            print(f"error={error}")
        return 1
    print("qadam_evidence_contracts_check=ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
