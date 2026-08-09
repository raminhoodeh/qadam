#!/usr/bin/env python3
"""Record a verified, paper-only EF11 production deployment."""

from __future__ import annotations

import argparse
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from orchestrator.config import Settings  # noqa: E402
from orchestrator.qadam_canonical_contracts import AtomicArtifactStore  # noqa: E402
from orchestrator.qadam_ef11_open_market_conversion import DEPLOYMENT_ARTIFACT  # noqa: E402
from orchestrator.qadam_operator_ready_common import authority_flags, now_iso, runtime_dir  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root-commit", required=True)
    parser.add_argument("--dashboard-commit", required=True)
    parser.add_argument("--production-url", required=True)
    parser.add_argument("--verified-bundle", required=True)
    args = parser.parse_args()
    if not args.production_url.startswith("https://"):
        raise SystemExit("production URL must use HTTPS")
    payload = {
        "schema_version": "qadam_ef11_deployment.v1",
        "artifact_type": "qadam_ef11_deployment_status",
        "generated_at": now_iso(),
        "status": "deployed_live",
        "root_commit": args.root_commit,
        "dashboard_commit": args.dashboard_commit,
        "production_url": args.production_url,
        "verified_bundle": args.verified_bundle,
        "protected_dashboard_ux_preserved": True,
        "paper_only": True,
        "canonical_paperops_only": True,
        "broker_write_count_by_deployment": 0,
        "live_capital_enabled": False,
        "public_safe": True,
        "read_only": True,
        "command_disabled": True,
        "authority": authority_flags(),
    }
    AtomicArtifactStore(runtime_dir(Settings.from_env())).write_json(
        DEPLOYMENT_ARTIFACT, payload
    )
    print("status=deployed_live")
    print(f"artifact=data/runtime/{DEPLOYMENT_ARTIFACT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
