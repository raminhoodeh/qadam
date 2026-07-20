#!/usr/bin/env python3
"""Validate the public-safe result of Qadam's full-history IBM experiment."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from orchestrator.config import Settings  # noqa: E402
from orchestrator.qadam_ibm_full_history_experiment import (  # noqa: E402
    RESULT_ARTIFACT,
    validate_full_history_result,
)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--require-completed", action="store_true")
    args = parser.parse_args()
    settings = Settings.from_env()
    path = Path(settings.runtime_dir) / RESULT_ARTIFACT
    try:
        result = json.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, OSError, json.JSONDecodeError):
        print("ibm_full_history_check=blocked")
        print("ibm_full_history_errors=['result_missing_or_invalid']")
        return 1
    errors = validate_full_history_result(
        result,
        require_completed=args.require_completed,
    )
    print(f"ibm_full_history_check={'ok' if not errors else 'blocked'}")
    print(f"ibm_full_history_status={result.get('status')}")
    print(
        "ibm_full_history_hardware_completed="
        f"{result.get('hardware_experiment_completed')}"
    )
    print(
        "ibm_full_history_research_candidate_count="
        f"{result.get('hardware_research_candidate_count', 0)}"
    )
    print(f"ibm_full_history_errors={errors}")
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
