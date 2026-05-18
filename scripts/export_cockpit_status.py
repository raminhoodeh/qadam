#!/usr/bin/env python3
# ruff: noqa: E402
"""Export the public-safe cockpit status snapshot."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from orchestrator.cockpit_status import export_cockpit_status  # noqa: E402


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="Optional output path. Defaults to data/runtime/cockpit-status.json.",
    )
    parser.add_argument(
        "--landing-repo",
        type=Path,
        default=ROOT / "landing-page-repo",
        help="Static landing repo to receive status/cockpit-status.json.",
    )
    parser.add_argument(
        "--no-landing-copy",
        action="store_true",
        help="Write only the local runtime snapshot.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    result = export_cockpit_status(
        output_path=args.output,
        landing_repo_path=args.landing_repo,
        copy_to_landing=not args.no_landing_copy,
    )
    print("cockpit_status_export=ok")
    print(f"cockpit_status_schema_version={result['schema_version']}")
    print(f"cockpit_status_generated_at={result['generated_at']}")
    print("cockpit_status_d1_phase=D1")
    print("cockpit_status_d1_read_only=True")
    print("cockpit_status_d1_public_safe=True")
    print(f"cockpit_status_runtime_path={result['runtime_path']}")
    print(f"cockpit_status_landing_path={result['landing_path']}")
    print(f"cockpit_status_runtime_signature_path={result['runtime_signature_path']}")
    print(f"cockpit_status_landing_signature_path={result['landing_signature_path']}")
    print(f"cockpit_status_module_count={result['module_count']}")
    print(f"cockpit_status_watching_count={result['watching_count']}")
    print(f"cockpit_status_hypothesis_count={result['hypothesis_count']}")
    print(f"cockpit_status_trade_candidate_count={result['trade_candidate_count']}")
    print(f"cockpit_status_forbidden_action_count={result['forbidden_action_count']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
