#!/usr/bin/env python3
"""Validate the persisted canonical tradeability-envelope registry."""

from __future__ import annotations

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from orchestrator.qadam_operator_ready_common import read_json, read_jsonl, runtime_dir
from orchestrator.qadam_tradeability_envelope import (
    CHECK_ARTIFACT,
    ENVELOPES_ARTIFACT,
    REGISTRY_ARTIFACT,
    validate_envelope_dict,
)


def main() -> int:
    runtime = runtime_dir()
    checks = read_json(runtime / CHECK_ARTIFACT)
    registry = read_json(runtime / REGISTRY_ARTIFACT)
    envelopes = read_jsonl(runtime / ENVELOPES_ARTIFACT)
    errors = list(checks.get("validation_errors") or [])
    errors.extend(
        error for envelope in envelopes for error in validate_envelope_dict(envelope)
    )
    if checks.get("status") != "passed" or registry.get("status") != "passed":
        errors.append("canonical_tradeability_envelope_registry_not_passed")
    if int(registry.get("envelope_count") or 0) != len(envelopes):
        errors.append("canonical_tradeability_envelope_count_mismatch")
    errors = sorted(set(errors))
    print(f"status={checks.get('status')}")
    print(f"envelope_count={len(envelopes)}")
    print(f"contract_defect_count={checks.get('contract_defect_count')}")
    for error in errors:
        print(f"error={error}")
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
