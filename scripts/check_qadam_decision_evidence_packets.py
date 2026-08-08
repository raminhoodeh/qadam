#!/usr/bin/env python3
"""Build and validate EF-4 packets and their Akber bindings."""

from __future__ import annotations

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from orchestrator.qadam_akber_filter_v3 import build_and_write_akber_filter_v3  # noqa: E402
from orchestrator.qadam_decision_evidence_packets import (  # noqa: E402
    INTEGRITY_ARTIFACT,
    PACKETS_ARTIFACT,
    REJECTIONS_ARTIFACT,
    SUMMARY_ARTIFACT,
    build_and_write_decision_evidence_packets,
)


def main() -> int:
    _state, checks, errors = build_and_write_decision_evidence_packets()
    _akber_state, akber_checks, akber_errors = build_and_write_akber_filter_v3()
    all_errors = [*errors, *akber_errors]
    for name in (PACKETS_ARTIFACT, SUMMARY_ARTIFACT, REJECTIONS_ARTIFACT, INTEGRITY_ARTIFACT):
        print(f"artifact={ROOT / 'data' / 'runtime' / name}")
    print(f"status={'passed' if not all_errors else 'blocked'}")
    print(f"packet_count={checks['packet_count']}")
    print(f"mixed_generation_join_count={checks['mixed_generation_join_count']}")
    print(f"akber_input_count={akber_checks['input_count']}")
    if all_errors:
        for error in all_errors:
            print(f"error={error}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
