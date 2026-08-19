#!/usr/bin/env python3
# ruff: noqa: E402
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from orchestrator.qadam_operator_ready_common import now_iso, runtime_dir, write_json_atomic
from orchestrator.qadam_operator_service import SERVICE_DEFINITIONS
from orchestrator.qadam_runtime_domains import load_domain_policy, validate_domain_coverage


def main() -> int:
    errors = validate_domain_coverage(row.service_id for row in SERVICE_DEFINITIONS)
    policy = load_domain_policy()
    payload = {
        "schema_version": "qadam_runtime_domain_checks.v1",
        "artifact_type": "qadam_runtime_domain_checks",
        "generated_at": now_iso(),
        "status": "passed" if not errors else "blocked",
        "service_count": len(SERVICE_DEFINITIONS),
        "domains": {
            name: {
                "service_count": len(record.get("service_ids", [])),
                "priority": record.get("priority"),
                "reserved_jobs_per_cycle": record.get("reserved_jobs_per_cycle"),
            }
            for name, record in policy["domains"].items()
        },
        "execution_capacity_reserved": True,
        "dashboard_failure_can_open_execution_circuit": False,
        "quantum_failure_can_open_execution_circuit": False,
        "validation_errors": errors,
        "paper_order_created_count": 0,
        "broker_write_count": 0,
        "live_capital_enabled": False,
    }
    write_json_atomic(runtime_dir() / "qadam_runtime_domain_checks.json", payload)
    print(f"qadam_runtime_domain_status={payload['status']}")
    print(f"service_count={payload['service_count']}")
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
