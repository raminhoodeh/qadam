#!/usr/bin/env python3
"""Refresh only the dynamic PORR status block from canonical runtime state."""

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from orchestrator.qadam_operator_ready_common import (  # noqa: E402
    atomic_write_text,
    read_json,
    runtime_dir,
)

PLAN = ROOT / "docs" / "qadam-permanent-operator-reliability-repair-implementation-plan.md"
START = "<!-- QADAM_PORR_DYNAMIC_STATUS_START -->"
END = "<!-- QADAM_PORR_DYNAMIC_STATUS_END -->"


def main() -> int:
    runtime = runtime_dir()
    operator = read_json(runtime / "qadam_operator_service_status.json")
    circuits = read_json(runtime / "qadam_operator_circuit_breakers.json")
    repairs = read_json(runtime / "qadam_operator_repair_queue.json")
    paperops = read_json(runtime / "paperops_autonomous_pass_summary.json")
    certification = read_json(runtime / "qadam_permanent_operator_reliability_certification.json")
    status = certification.get("status") or "implementation_in_progress"
    current_phase = "PORR-14" if status == "provisional_soak" else "PORR-13"
    if status == "passed":
        current_phase = "PORR-16"
    block = "\n".join(
        (
            START,
            "",
            "| Field | Current Value |",
            "| --- | --- |",
            "| Plan version | `1.1` |",
            f"| Plan state | `{status}` |",
            f"| Current phase | `{current_phase}` |",
            f"| Operator service | `{operator.get('status') or 'not_running'}` |",
            f"| Observation ready | `{str(operator.get('observation_ready') is True).lower()}` |",
            f"| Open circuits | `{int(circuits.get('open_circuit_count') or 0)}` |",
            f"| Open repair requests | `{int(repairs.get('open_request_count') or 0)}` |",
            f"| Stale services | `{int(operator.get('freshness', {}).get('stale_service_count') or 0)}` |",
            f"| Canonical PaperOps summary | `{paperops.get('status') or 'not_refreshed'}` |",
            "| Live capital | `disabled` |",
            "| Dashboard UX restructuring | `forbidden` |",
            "",
            END,
        )
    )
    text = PLAN.read_text(encoding="utf-8")
    before, separator, remainder = text.partition(START)
    if not separator or END not in remainder:
        raise RuntimeError("porr_dynamic_status_markers_missing")
    _old, _end, after = remainder.partition(END)
    atomic_write_text(PLAN, before + block + after)
    print(f"qadam_porr_plan_status={status}")
    print(f"qadam_porr_plan_phase={current_phase}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
