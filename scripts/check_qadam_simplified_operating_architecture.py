#!/usr/bin/env python3
"""Build and validate the simplified Qadam operating architecture."""

from __future__ import annotations

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from orchestrator.config import Settings  # noqa: E402
from orchestrator.qadam_simplified_operating_architecture import (  # noqa: E402
    build_simplified_operating_architecture_certification,
    validate_simplified_operating_architecture_certification,
    write_simplified_operating_architecture_certification,
)


def main() -> int:
    settings = Settings.from_env()
    artifact = build_simplified_operating_architecture_certification(settings)
    destination = write_simplified_operating_architecture_certification(artifact, settings)
    errors = validate_simplified_operating_architecture_certification(artifact)
    print(f"qadam_simplified_architecture_status={artifact['status']}")
    print(f"qadam_simplified_architecture_checks={artifact['passed_check_count']}/{artifact['check_count']}")
    print(f"qadam_simplified_architecture_blockers={','.join(artifact['blockers'])}")
    print(f"qadam_simplified_architecture_artifact={destination}")
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
