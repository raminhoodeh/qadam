#!/usr/bin/env python3
# ruff: noqa: E402
"""Fail closed unless source, dashboard, and installed CATC runtime agree."""

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from orchestrator.qadam_catc_release_reproducibility import (
    build_and_write_release_reproducibility,
)


def main() -> int:
    payload = build_and_write_release_reproducibility()
    print(f"qadam_catc_release_reproducibility_status={payload['status']}")
    print(f"installed_commit={payload['installed_commit']}")
    print(f"operator_build_scope_clean={payload['operator_build_scope_clean']}")
    print(
        "guarded_paperops_runtime_owner_active="
        f"{payload['guarded_paperops_runtime_owner_active']}"
    )
    return 0 if payload["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
