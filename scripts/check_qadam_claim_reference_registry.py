#!/usr/bin/env python3
"""Build and check QEG-3 reference and claim intake."""

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from orchestrator.qadam_claim_reference_registry import build_claim_registry


if __name__ == "__main__":
    claims, references, errors = build_claim_registry()
    print(f"claim_count={claims['claim_count']}")
    print(f"reference_count={references['reference_count']}")
    print(f"validation_error_count={len(errors)}")
    for error in errors:
        print(f"error={error}")
    raise SystemExit(1 if errors else 0)
