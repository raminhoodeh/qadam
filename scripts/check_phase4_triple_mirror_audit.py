#!/usr/bin/env python3
"""Run and validate the Phase 4 Triple-Mirror Audit."""

from __future__ import annotations

from copy import deepcopy
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from orchestrator.phase4_triple_mirror import (  # noqa: E402
    build_triple_mirror_audit,
    validate_triple_mirror_audit,
    write_triple_mirror_audit,
)


def main() -> int:
    errors: list[str] = []
    artifact = build_triple_mirror_audit()
    output_path = write_triple_mirror_audit(artifact)
    validation_errors = validate_triple_mirror_audit(artifact)

    authority_probe = deepcopy(artifact)
    authority_probe["runtime_mirror"]["authority_mismatch_count"] = 1
    authority_probe["authority_mismatch_count"] = 1
    authority_probe_errors = validate_triple_mirror_audit(authority_probe)

    promotion_probe = deepcopy(artifact)
    promotion_probe["strategy_promotion_allowed"] = True
    promotion_probe_errors = validate_triple_mirror_audit(promotion_probe)

    docs = artifact["docs_mirror"]
    resources = artifact["resource_mirror"]
    runtime = artifact["runtime_mirror"]
    print("phase4_triple_mirror_status=" + ("ok" if not validation_errors else "error"))
    print(f"phase4_triple_mirror_schema_version={artifact['audit_schema_version']}")
    print(f"phase4_triple_mirror_artifact_path={output_path}")
    print(f"phase4_triple_mirror_drift_status={artifact['drift_status']}")
    print(f"phase4_triple_mirror_mirror_count={artifact['mirror_count']}")
    print(f"phase4_triple_mirror_plan_status={docs['status']}")
    print(f"phase4_triple_mirror_plan_missing_terms={docs['missing_term_count']}")
    print(f"phase4_triple_mirror_resource_status={resources['status']}")
    print(f"phase4_triple_mirror_resource_count={resources['resource_count']}")
    print(f"phase4_triple_mirror_resource_unmapped_count={resources['unmapped_resource_count']}")
    print(f"phase4_triple_mirror_resource_missing_mapping_count={resources['missing_mapping_count']}")
    print(f"phase4_triple_mirror_resource_production_active_count={resources['production_active_count']}")
    print(f"phase4_triple_mirror_runtime_status={runtime['status']}")
    print(f"phase4_triple_mirror_runtime_source={runtime['source']}")
    print(f"phase4_triple_mirror_runtime_generated_at={runtime['generated_at']}")
    print(f"phase4_triple_mirror_runtime_missing_section_count={runtime['missing_section_count']}")
    print(f"phase4_triple_mirror_authority_mismatch_count={runtime['authority_mismatch_count']}")
    print(
        "phase4_triple_mirror_durable_replay="
        f"{runtime['durable_replay']['status']},"
        f"{runtime['durable_replay']['contract_status']},"
        f"replayed={runtime['durable_replay']['replayed_source_count']},"
        f"missing={runtime['durable_replay']['missing_source_count']}"
    )
    print(
        "phase4_triple_mirror_quantum="
        f"{runtime['quantum_oracle']['status']},"
        f"{runtime['quantum_oracle']['backend']},"
        f"results={runtime['quantum_oracle']['result_count']},"
        f"hardware={runtime['quantum_oracle']['hardware_submitted_count']}"
    )
    print(
        "phase4_triple_mirror_yahoo="
        f"{runtime['yahoo_finance']['status']},"
        f"enabled={runtime['yahoo_finance']['enabled']},"
        f"role={runtime['yahoo_finance']['market_confirmation_role']},"
        f"canonical={runtime['yahoo_finance']['canonical_source']}"
    )
    print(f"phase4_triple_mirror_validation_error_count={len(validation_errors)}")
    print(f"phase4_triple_mirror_authority_probe_error_count={len(authority_probe_errors)}")
    print(f"phase4_triple_mirror_promotion_probe_error_count={len(promotion_probe_errors)}")
    print(f"phase4_triple_mirror_advisory_only={artifact['advisory_only']}")
    print(f"phase4_triple_mirror_strategy_promotion_allowed={artifact['strategy_promotion_allowed']}")
    print(f"phase4_triple_mirror_execution_allowed={artifact['execution_allowed']}")
    print("phase4_triple_mirror_boundary=" + artifact["boundary"])

    if validation_errors:
        errors.extend(validation_errors)
    if runtime["missing_section_count"] != 0:
        errors.append("runtime_sections_missing")
    if runtime["authority_mismatch_count"] != 0:
        errors.append("runtime_authority_mismatch")
    if not any(error == "runtime_authority_mismatch" for error in authority_probe_errors):
        errors.append("authority_probe_not_rejected")
    if not any(error == "authority_enabled:strategy_promotion_allowed" for error in promotion_probe_errors):
        errors.append("promotion_probe_not_rejected")
    if artifact["advisory_only"] is not True:
        errors.append("advisory_only_not_true")
    if artifact["strategy_promotion_allowed"] is not False:
        errors.append("strategy_promotion_enabled")
    if artifact["execution_allowed"] is not False:
        errors.append("execution_enabled")

    if errors:
        for error in errors:
            print(f"phase4_triple_mirror_error={error}")
        print("phase4_triple_mirror_check=failed")
        return 1

    print("phase4_triple_mirror_check=ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
