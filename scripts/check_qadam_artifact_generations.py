#!/usr/bin/env python3
"""Exercise immutable generation publication and validation."""

from pathlib import Path
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from orchestrator.qadam_artifact_generations import ArtifactGenerationStore  # noqa: E402
from orchestrator.qadam_operator_ready_common import (  # noqa: E402
    authority_flags,
    now_iso,
    runtime_dir,
    write_json_atomic,
)


def main() -> int:
    runtime = runtime_dir()
    errors = []
    with tempfile.TemporaryDirectory(prefix="qadam-generation-check-") as temporary:
        root = Path(temporary)
        source = root / "evidence.json"
        source.write_text('{"status":"complete"}\n', encoding="utf-8")
        store = ArtifactGenerationStore(root, "point_in_time_evidence")
        first = store.publish_files({source.name: source}, producer="generation_check")
        source.write_text('{"status":"next"}\n', encoding="utf-8")
        second = store.publish_files({source.name: source}, producer="generation_check")
        if first.generation_id == second.generation_id:
            errors.append("generation_identity_did_not_change")
        try:
            with store.lease_current() as current:
                if current.generation_id != second.generation_id:
                    errors.append("current_generation_pointer_incorrect")
                store.validate_reference(current)
        except Exception as exc:  # pragma: no cover - defensive checker envelope
            errors.append(f"generation_validation_failed:{type(exc).__name__}:{exc}")
    result = {
        "schema_version": "qadam_artifact_generation_check.v1",
        "artifact_type": "qadam_artifact_generation_check",
        "generated_at": now_iso(),
        "status": "passed" if not errors else "blocked",
        "errors": errors,
        "paper_order_created_count": 0,
        "broker_write_count": 0,
        "authority": authority_flags(),
    }
    write_json_atomic(runtime / "qadam_artifact_generation_checks.json", result)
    print(f"qadam_artifact_generation_status={result['status']}")
    print(f"qadam_artifact_generation_error_count={len(errors)}")
    return 0 if result["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
