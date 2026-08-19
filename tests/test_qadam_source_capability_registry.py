from pathlib import Path

from orchestrator.config import Settings
from orchestrator.qadam_source_capability_registry import build_source_capability_registry
from orchestrator.qadam_operator_ready_common import write_json_atomic


def _settings(tmp_path: Path) -> Settings:
    base = Settings.from_env()
    return Settings(**{**base.__dict__, "runtime_dir": str(tmp_path), "state_root": str(tmp_path)})


def test_empirically_scored_sources_define_historical_alpha_count(tmp_path: Path) -> None:
    sources = []
    empirical = []
    historical = []
    for index in range(41):
        key = f"source_{index}"
        sources.append(
            {
                "source_key": key,
                "source_name": key,
                "source_family": "test",
                "provider_backed_observation": index < 7,
                "freshness_status": "fresh" if index < 5 else "unknown",
                "sample_fixture": False,
                "source_quorum_contribution": {"can_contribute": index < 3},
            }
        )
        empirical.append(
            {
                "source_key": key,
                "historically_scored": index < 5,
                "empirical_role": "scored_signal" if index < 5 else "forward_only_capture",
                "closure_state": "provider_backed_acquired" if index < 5 else "forward_only",
                "provider_backed_row_count": 100 if index < 5 else 0,
                "scoreability_disposition": "historically_scored" if index < 5 else "real_forward_time_required",
            }
        )
        historical.append(
            {
                "source_key": key,
                "status": "pilot_ready",
                "evidence_eligible_from_pilot": False,
                "forward_only": index >= 5,
            }
        )
    write_json_atomic(tmp_path / "qsase_source_universe.json", {"sources": sources})
    write_json_atomic(
        tmp_path / "qadam_source_empirical_role_registry.json",
        {"sources": empirical},
    )
    write_json_atomic(
        tmp_path / "qadam_historical_source_coverage_matrix.json",
        {"rows": historical},
    )

    payload = build_source_capability_registry(_settings(tmp_path))

    assert payload["status"] == "passed"
    assert payload["counts"]["catalogue"] == 41
    assert payload["counts"]["historical_alpha_usable"] == 5
    assert payload["counts"]["provider_backed_current"] == 7
