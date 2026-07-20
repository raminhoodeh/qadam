"""Shared command helper for PLBG stage checks."""

from __future__ import annotations

import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from orchestrator.qadam_learning_backtest_gap_closure import (  # noqa: E402
    SCHEMA_VERSION,
    validate_stage,
)
from orchestrator.qadam_operator_ready_common import (  # noqa: E402
    authority_flags,
    now_iso,
    runtime_dir,
    write_json_atomic,
)


def run(stage_id: str, artifact_name: str) -> int:
    errors = validate_stage(stage_id)
    payload = {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "qadam_plbg_stage_check",
        "stage_id": stage_id,
        "generated_at": now_iso(),
        "status": "passed" if not errors else "blocked",
        "validation_error_count": len(errors),
        "validation_errors": errors,
        "authority": authority_flags(),
    }
    write_json_atomic(runtime_dir() / artifact_name, payload)
    print(json.dumps(payload, sort_keys=True))
    return 0 if not errors else 1
