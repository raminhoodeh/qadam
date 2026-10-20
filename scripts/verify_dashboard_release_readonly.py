#!/usr/bin/env python3
"""Validate existing release projections without refreshing operational state."""

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from orchestrator.cockpit_status import validate_cockpit_status  # noqa: E402
from orchestrator.qadam_autonomous_experimental_paper_epoch import _dashboard_hash_audit  # noqa: E402


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--site-root", type=Path, required=True)
    parser.add_argument("--runtime-dir", type=Path, required=True)
    args = parser.parse_args()
    snapshot = args.runtime_dir / "cockpit-status.json"
    if snapshot.stat().st_size > 16 * 1024 * 1024:
        raise ValueError("public_snapshot_exceeds_transport_budget")
    validate_cockpit_status(json.loads(snapshot.read_text()))
    deployed = json.loads((args.site_root / "status/cockpit-status.json").read_text())
    validate_cockpit_status(deployed)
    audit = _dashboard_hash_audit()
    if audit["matching_asset_count"] != audit["asset_count"]:
        raise ValueError("dashboard_assets_not_bound_to_reviewed_commit")
    print("dashboard_release_readonly=passed")
    print("broker_write_count=0")
    print("runtime_projection_refresh_count=0")


if __name__ == "__main__":
    raise SystemExit(main())
