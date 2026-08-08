#!/usr/bin/env python3
"""Build and validate EF-1 canonical source and instrument truth."""

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from orchestrator.qadam_operator_ready_common import runtime_dir  # noqa: E402
from orchestrator.qadam_universe_contract import (  # noqa: E402
    CHECK_ARTIFACT,
    FRESHNESS_SLA_ARTIFACT,
    INSTRUMENT_REGISTRY_ARTIFACT,
    PROXY_REGISTRY_ARTIFACT,
    SOURCE_CONTRACT_ARTIFACT,
    build_and_write_universe_contract,
)


def main() -> int:
    runtime = runtime_dir()
    _state, checks, errors = build_and_write_universe_contract()
    for name in (
        SOURCE_CONTRACT_ARTIFACT,
        INSTRUMENT_REGISTRY_ARTIFACT,
        PROXY_REGISTRY_ARTIFACT,
        FRESHNESS_SLA_ARTIFACT,
        CHECK_ARTIFACT,
    ):
        print(f"artifact={runtime / name}")
    for key in ("status", "source_count", "instrument_count", "guarded_route_count"):
        print(f"{key}={checks[key]}")
    print(f"validation_error_count={len(errors)}")
    for error in errors:
        print(f"error={error}")
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
