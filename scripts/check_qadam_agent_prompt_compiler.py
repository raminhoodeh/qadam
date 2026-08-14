#!/usr/bin/env python3
"""Validate Qadam's versioned, bounded agent prompt compiler."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from orchestrator.qadam_agent_compiler import (
    build_agent_task_packet,
    build_and_write_agent_compiler_checks,
    compile_agent_prompt,
)
from orchestrator.qadam_operator_ready_common import sha256_json


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    evidence = {"artifact": "provider-backed research fixture", "value": 1}
    task = build_agent_task_packet(
        "local_research_assessment",
        decision_generation_id="compiler-self-test-generation",
        objective="Summarize the supplied research evidence without creating authority.",
        evidence_refs=["compiler-self-test.json"],
        evidence_hashes={"compiler-self-test.json": sha256_json(evidence)},
        untrusted_context={"evidence": evidence},
    )
    compiled = compile_agent_prompt(task)
    checks, errors = build_and_write_agent_compiler_checks()
    errors = list(errors)
    if compiled.get("task_id") != task.task_id:
        errors.append("compiled_prompt_task_id_mismatch")
    if "output_schema" not in str(compiled.get("system_prompt") or ""):
        errors.append("compiled_prompt_schema_missing")
    if compiled.get("authority", {}).get("paper_order_allowed") is not False:
        errors.append("compiled_prompt_authority_violation")
    result = {
        "status": "passed" if not errors else "blocked",
        "task_id": task.task_id,
        "prompt_hash": compiled.get("prompt_hash"),
        "validation_errors": errors,
        "compiler_checks": checks,
    }
    if args.json:
        print(json.dumps(result, sort_keys=True))
    else:
        print(
            f"status={result['status']} task_id={task.task_id} "
            f"error_count={len(errors)}"
        )
        for error in errors:
            print(f"- {error}")
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
