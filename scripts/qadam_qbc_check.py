"""Shared fail-closed command helper for QBC phase checks."""

from __future__ import annotations

import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from orchestrator.qadam_backtest_completion import (  # noqa: E402
    SCHEMA_VERSION,
    build_certification,
    validate_phase,
)
from orchestrator.qadam_operator_ready_common import (  # noqa: E402
    authority_flags,
    now_iso,
    runtime_dir,
    write_json_atomic,
)


SCRIPT_PHASES = {
    "check_qadam_backtest_completion_baseline.py": "QBC-0",
    "check_qadam_backtest_completion_roles.py": "QBC-1",
    "check_qadam_acquired_source_scoreability.py": "QBC-2",
    "check_qadam_stock_act_transaction_detail_completion.py": "QBC-3",
    "check_qadam_kalshi_contract_history_completion.py": "QBC-4",
    "check_qadam_polymarket_contract_history_completion.py": "QBC-5",
    "check_qadam_unusual_whales_completion.py": "QBC-6",
    "check_qadam_public_archive_completion.py": "QBC-7",
    "check_qadam_forward_source_maturity.py": "QBC-8",
    "check_qadam_selective_microstructure_completion.py": "QBC-9",
    "check_qadam_backtest_completion_point_in_time.py": "QBC-10",
    "check_qadam_backtest_completion_score_tape.py": "QBC-11",
    "check_qadam_backtest_completion_statistical.py": "QBC-12",
    "check_qadam_backtest_completion_nonlinear_quantum.py": "QBC-13",
    "check_qadam_backtest_strategy_translation.py": "QBC-14",
    "check_qadam_forward_strategy_tournament.py": "QBC-15",
    "check_qadam_guarded_paper_canary.py": "QBC-16",
    "check_qadam_backtest_completion_visibility.py": "QBC-17",
}


def main_for_script(filename: str) -> int:
    script_name = Path(filename).name
    phase_id = SCRIPT_PHASES.get(script_name)
    if not phase_id:
        raise SystemExit(f"Unregistered QBC checker: {script_name}")
    errors = validate_phase(phase_id)
    payload = {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "qadam_backtest_completion_phase_check",
        "phase_id": phase_id,
        "generated_at": now_iso(),
        "status": "passed" if not errors else "blocked",
        "validation_error_count": len(errors),
        "validation_errors": errors,
        "authority": authority_flags(),
    }
    artifact_name = script_name.removeprefix("check_").removesuffix(".py") + "_checks.json"
    write_json_atomic(runtime_dir() / artifact_name, payload)
    print(json.dumps(payload, sort_keys=True))
    return 0 if not errors else 1


def main_certification() -> int:
    certification = build_certification()
    from orchestrator.runtime.command import report_work_result
    report_work_result(certification, [] if certification.get("status") == "passed" else ["backtest_certification_incomplete"])
    print(json.dumps(certification, sort_keys=True))
    return 0 if certification.get("status") == "passed" else 1
