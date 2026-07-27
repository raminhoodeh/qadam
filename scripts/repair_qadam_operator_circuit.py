#!/usr/bin/env python3
"""Re-run one allowlisted read-only operator service to repair its circuit."""

from __future__ import annotations

import argparse
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from orchestrator.config import Settings  # noqa: E402
from orchestrator.qadam_operator_service import repair_operator_service_circuit  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--service-id", required=True)
    parser.add_argument(
        "--confirm-guarded-paperops",
        action="store_true",
        help=(
            "Explicitly authorize three canonical paper-only PaperOps revalidation "
            "passes. This never permits live capital or an alternate broker route."
        ),
    )
    args = parser.parse_args()
    try:
        result = repair_operator_service_circuit(
            args.service_id,
            Settings.from_env(),
            explicit_guarded_paperops_confirmation=args.confirm_guarded_paperops,
        )
    except ValueError as exc:
        print("operator_circuit_repair_status=blocked")
        print(f"operator_circuit_repair_error={exc}")
        return 1
    print(f"operator_circuit_repair_status={result['status']}")
    print(f"operator_circuit_repair_service_id={result['service_id']}")
    print(f"operator_circuit_repair_state={result.get('state', result.get('prior_circuit_state'))}")
    print("operator_circuit_repair_paper_order_created_count=0")
    print("operator_circuit_repair_broker_write_count=0")
    return 0 if result["status"] in {"repaired", "not_required"} else 1


if __name__ == "__main__":
    raise SystemExit(main())
