#!/usr/bin/env python3
"""Build and validate the public-safe Quantum Review projection."""

from __future__ import annotations

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from orchestrator.config import Settings  # noqa: E402
from orchestrator.qadam_canonical_contracts import AtomicArtifactStore  # noqa: E402
from orchestrator.qadam_operator_ready_common import runtime_dir  # noqa: E402
from orchestrator.qadam_pattern_dashboard_views import (  # noqa: E402
    QUANTUM_REVIEW_ARTIFACT,
    build_pattern_dashboard_views,
    validate_quantum_review,
)


def main() -> int:
    settings = Settings.from_env()
    runtime = runtime_dir(settings)
    payload = build_pattern_dashboard_views(settings)["quantum_review"]
    errors = validate_quantum_review(payload)
    AtomicArtifactStore(runtime).write_json(QUANTUM_REVIEW_ARTIFACT, payload)
    print(f"artifact={runtime / QUANTUM_REVIEW_ARTIFACT}")
    print(f"status={payload['status']}")
    print(f"review_count={payload['review_count']}")
    print(f"defined_protocol_count={payload['defined_protocol_count']}")
    print(f"empirical_comparison_count={payload['empirical_comparison_count']}")
    print(f"quantum_usefulness_score={payload['quantum_usefulness_score']}")
    print(f"validation_error_count={len(errors)}")
    for error in errors:
        print(f"error={error}")
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
