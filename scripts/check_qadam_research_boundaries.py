#!/usr/bin/env python3
"""Build and validate RF-4 provider, storage, and research boundaries."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from orchestrator.config import Settings  # noqa: E402
from orchestrator.qadam_operator_ready_common import runtime_dir  # noqa: E402
from orchestrator.qadam_research_boundaries import (  # noqa: E402
    BASELINE_ORIGIN_ARTIFACT,
    CHECK_ARTIFACT,
    PROVIDER_REGISTRY_ARTIFACT,
    RESEARCH_AUDIT_ARTIFACT,
    STORAGE_REGISTRY_ARTIFACT,
    build_and_write_research_boundaries,
)


def main() -> int:
    settings = Settings.from_env()
    runtime = runtime_dir(settings)
    bundle, checks, errors = build_and_write_research_boundaries(settings)
    baseline = bundle["baseline"]
    print(f"provider_registry={runtime / PROVIDER_REGISTRY_ARTIFACT}")
    print(f"storage_registry={runtime / STORAGE_REGISTRY_ARTIFACT}")
    print(f"research_audit={runtime / RESEARCH_AUDIT_ARTIFACT}")
    print(f"baseline_origin_audit={runtime / BASELINE_ORIGIN_ARTIFACT}")
    print(f"checks_artifact={runtime / CHECK_ARTIFACT}")
    print(f"status={checks['status']}")
    print(f"provider_protocol_count={checks['provider_protocol_count']}")
    print(f"storage_plane_count={checks['storage_plane_count']}")
    print(f"research_service_count={checks['research_service_count']}")
    print(f"provider_call_count={checks['provider_call_count']}")
    print(f"local_baseline_origin_class={baseline['origin_class']}")
    print(f"provider_backed_history={baseline['provider_backed_historical_acquisition']}")
    print(f"edge_promotion_allowed={baseline['edge_promotion_allowed']}")
    print(f"behavior_changed={checks['behavior_changed']}")
    print(f"broker_write_allowed={checks['authority']['broker_write_allowed']}")
    print(f"validation_error_count={len(errors)}")
    if errors:
        for error in errors:
            print(f"error={error}")
        return 1
    print("qadam_research_boundaries_check=ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
