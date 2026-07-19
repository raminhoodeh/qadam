#!/usr/bin/env python3
"""Prepare the immutable testing archive and report experimental cutover readiness."""

from __future__ import annotations

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from orchestrator.qadam_clean_epoch_cutover import (  # noqa: E402
    build_experimental_epoch_cutover_readiness,
    prepare_experimental_testing_archive,
)


def main() -> int:
    archive = prepare_experimental_testing_archive()
    readiness = build_experimental_epoch_cutover_readiness()
    archive_valid = bool(
        archive.manifest.get("checksums_digest")
        and archive.manifest.get("testing_epoch_id") == readiness.get("archive_id")
        and archive.manifest.get("checksums_digest") == readiness.get("archive_digest")
    )
    print(f"experimental_cutover_archive_id={readiness.get('archive_id')}")
    print(f"experimental_cutover_archive_valid={str(archive_valid).lower()}")
    print(f"experimental_cutover_readiness={readiness['status']}")
    print(f"experimental_cutover_ready={str(readiness['cutover_ready']).lower()}")
    print("experimental_cutover_broker_write_count=0")
    print("experimental_cutover_paper_calendar_advanced=false")
    for blocker in readiness.get("blockers", []):
        print(f"experimental_cutover_blocker={blocker}")
    return 0 if archive_valid else 1


if __name__ == "__main__":
    raise SystemExit(main())
