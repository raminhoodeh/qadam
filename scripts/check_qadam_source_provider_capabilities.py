#!/usr/bin/env python3
"""Build and validate OR-2 provider capability and freshness contracts."""

from __future__ import annotations

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from orchestrator.config import Settings  # noqa: E402
from orchestrator.qadam_operator_ready_common import runtime_dir  # noqa: E402
from orchestrator.qadam_source_provider_capabilities import (  # noqa: E402
    CAPABILITY_ARTIFACT,
    CHECK_ARTIFACT,
    FRESHNESS_POLICY_ARTIFACT,
    OPERATIONAL_STATE_ARTIFACT,
    QUARANTINE_ARTIFACT,
    REPAIR_REQUESTS_ARTIFACT,
    build_and_write_source_provider_capabilities,
)


def main() -> int:
    settings = Settings.from_env()
    runtime = runtime_dir(settings)
    _bundle, checks, errors = build_and_write_source_provider_capabilities(settings)
    for name in (
        CAPABILITY_ARTIFACT,
        FRESHNESS_POLICY_ARTIFACT,
        OPERATIONAL_STATE_ARTIFACT,
        QUARANTINE_ARTIFACT,
        REPAIR_REQUESTS_ARTIFACT,
        CHECK_ARTIFACT,
    ):
        print(f"artifact={runtime / name}")
    print(f"status={checks['status']}")
    print(f"registered_source_count={checks['registered_source_count']}")
    print(f"fresh_scoring_eligible_count={checks['fresh_scoring_eligible_count']}")
    print(f"quarantined_or_context_only_count={checks['quarantined_or_context_only_count']}")
    print(f"historical_supported_interface_count={checks['historical_supported_interface_count']}")
    print(f"historical_validated_this_run_count={checks['historical_validated_this_run_count']}")
    print(f"validation_error_count={len(errors)}")
    for error in errors:
        print(f"error={error}")
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
