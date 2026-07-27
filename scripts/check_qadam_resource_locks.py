#!/usr/bin/env python3
"""Validate Qadam resource claims and lock lifecycle."""

from pathlib import Path
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from orchestrator.qadam_operator_ready_common import (  # noqa: E402
    authority_flags,
    now_iso,
    runtime_dir,
    write_json_atomic,
)
from orchestrator.qadam_operator_service import SERVICE_DEFINITIONS  # noqa: E402
from orchestrator.qadam_resource_locks import (  # noqa: E402
    ResourceClaims,
    ResourceLease,
    RESOURCE_ORDER,
    reconcile_stale_resource_leases,
)


def main() -> int:
    runtime = runtime_dir()
    reconciled = reconcile_stale_resource_leases(runtime)
    errors = []
    for definition in SERVICE_DEFINITIONS:
        try:
            definition.resource_claims().validate()
        except ValueError as exc:
            errors.append(f"{definition.service_id}:{exc}")
    with tempfile.TemporaryDirectory(prefix="qadam-lock-check-") as temporary:
        claims = ResourceClaims(reads=RESOURCE_ORDER)
        with ResourceLease(
            Path(temporary),
            service_id="resource_lock_check",
            claims=claims,
            timeout_seconds=1,
        ):
            pass
    result = {
        "schema_version": "qadam_resource_lock_check.v1",
        "artifact_type": "qadam_resource_lock_check",
        "generated_at": now_iso(),
        "status": "passed" if not errors else "blocked",
        "resource_count": len(RESOURCE_ORDER),
        "service_count": len(SERVICE_DEFINITIONS),
        "errors": errors,
        "stale_lease_mirror_reconciled_count": len(reconciled),
        "paper_order_created_count": 0,
        "broker_write_count": 0,
        "authority": authority_flags(),
    }
    write_json_atomic(runtime / "qadam_resource_lock_checks.json", result)
    print(f"qadam_resource_lock_status={result['status']}")
    print(f"qadam_resource_lock_error_count={len(errors)}")
    return 0 if result["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
