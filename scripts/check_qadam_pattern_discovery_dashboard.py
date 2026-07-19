#!/usr/bin/env python3
"""Build and validate the public-safe Pattern Discovery projection."""

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
    PATTERN_DISCOVERY_ARTIFACT,
    build_pattern_dashboard_views,
    validate_pattern_discovery,
)


def main() -> int:
    settings = Settings.from_env()
    runtime = runtime_dir(settings)
    payload = build_pattern_dashboard_views(settings)["pattern_discovery"]
    errors = validate_pattern_discovery(payload)
    AtomicArtifactStore(runtime).write_json(PATTERN_DISCOVERY_ARTIFACT, payload)
    print(f"artifact={runtime / PATTERN_DISCOVERY_ARTIFACT}")
    print(f"status={payload['status']}")
    print(f"relationship_count={payload['relationship_count']}")
    print(
        "recent_pattern_bullet_count="
        f"{payload['qualitative_analysis']['bullet_count']}"
    )
    print(
        "validated_edge_count="
        f"{next(row['count'] for row in payload['funnel'] if row['key'] == 'validated')}"
    )
    print(f"validation_error_count={len(errors)}")
    for error in errors:
        print(f"error={error}")
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
