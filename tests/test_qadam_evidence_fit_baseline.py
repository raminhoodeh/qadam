from dataclasses import replace
from pathlib import Path

from orchestrator.config import Settings
from orchestrator.qadam_evidence_fit_baseline import (
    build_evidence_fit_baseline,
    validate_evidence_fit_baseline,
    write_evidence_fit_phase_status,
)
from orchestrator.qadam_operator_ready_common import authority_flags, write_json_atomic


def test_baseline_is_read_only_and_owns_each_field_once(tmp_path: Path) -> None:
    write_json_atomic(
        tmp_path / "qsase_source_universe.json",
        {"sources": [{"source_key": f"s{index}"} for index in range(41)]},
    )
    write_json_atomic(
        tmp_path / "qsase_trading_universe.json",
        {"instruments": [{"symbol": f"I{index}"} for index in range(19)]},
    )
    write_json_atomic(
        tmp_path / "qadam_backtest_completion_coverage.json",
        {"status": "complete", "provider_backed_historical_rows": 10},
    )
    state = build_evidence_fit_baseline(
        tmp_path,
        generated_at="2026-08-08T12:00:00+00:00",
        repo=tmp_path,
    )
    assert validate_evidence_fit_baseline(state) == []
    assert state["baseline"]["immutable_snapshot"] is True
    assert state["baseline"]["authority"] == authority_flags()
    rows = state["ownership"]["fields"]
    assert len(rows) == len({row["field"] for row in rows})


def test_phase_status_marks_only_requested_phases_complete(tmp_path: Path) -> None:
    settings = replace(Settings.from_env(), runtime_dir=str(tmp_path))
    write_json_atomic(
        tmp_path / "qadam_evidence_fit_phase_status.json",
        {"baseline_id": "baseline:test", "phases": []},
    )
    results = {
        f"EF-{number}": {"errors": [], "checks": {}, "output_artifacts": []}
        for number in range(0, 5)
    }
    status = write_evidence_fit_phase_status(
        results,
        settings,
        generated_at="2026-08-08T12:00:00+00:00",
    )
    assert status["implemented_through_phase"] == "EF-4"
    assert all(row["pass"] for row in status["phases"][:5])
    assert all(row["implementation_state"] == "pending" for row in status["phases"][5:])
    assert status["later_phases_implemented"] is False
