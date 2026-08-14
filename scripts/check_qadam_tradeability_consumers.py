#!/usr/bin/env python3
"""Verify Akber, shadow, risk, and Router use canonical current hypotheses."""

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from orchestrator.qadam_tradeability_audits import build_and_write_consumer_audit


def main() -> int:
    audit, checks, errors = build_and_write_consumer_audit()
    print(f"status={checks.get('status')}")
    print(f"canonical_envelope_count={audit.get('canonical_envelope_count')}")
    print(f"canonical_projection_count={audit.get('canonical_projection_count')}")
    print(f"legacy_qeg_reader_count={audit.get('legacy_qeg_reader_count')}")
    for error in errors:
        print(f"error={error}")
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
