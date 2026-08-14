#!/usr/bin/env python3
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from orchestrator.qadam_experiment_memory import build_experiment_memory, validate_experiment_memory
from orchestrator.qadam_qeg_common import write_phase_status


if __name__ == "__main__":
    summary, errors = build_experiment_memory()
    errors.extend(validate_experiment_memory())
    write_phase_status(
        "QEG-5", status="passed" if not errors else "blocked", implementation_complete=not errors,
        empirical_state="persistent_experiment_memory_built",
        artifacts=["qadam_experiment_memory_index.json", "qadam_experiment_memory_summary.json"],
        blockers=errors,
    )
    print(f"memory_record_count={summary['memory_record_count']}")
    print(f"negative_result_count={summary['negative_result_count']}")
    print(f"validation_error_count={len(errors)}")
    for error in errors:
        print(f"error={error}")
    raise SystemExit(1 if errors else 0)
