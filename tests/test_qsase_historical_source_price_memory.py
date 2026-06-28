from orchestrator.qsase_historical_source_price_memory import (
    HISTORICAL_MEMORY_AUTHORITY_FLAGS,
    build_historical_source_price_memory,
    build_point_in_time_replay_index,
    validate_historical_source_price_memory,
    validate_negative_historical_memory_probes,
)


def test_historical_memory_builds_point_in_time_records_from_matrix():
    memory = build_historical_source_price_memory()

    assert memory["memory_record_count"] == memory["source_price_matrix_ref"]["matrix_row_count"]
    assert memory["point_in_time_safe_record_count"] == memory["memory_record_count"]
    assert memory["missing_window_record_count"] > 0
    assert memory["coverage_map"]["memory_record_count"] == memory["memory_record_count"]
    assert validate_historical_source_price_memory(memory) == []


def test_historical_memory_keeps_replay_research_only_and_proof_blocked():
    memory = build_historical_source_price_memory()
    records = memory["records"]

    assert memory["authority_flags"] == HISTORICAL_MEMORY_AUTHORITY_FLAGS
    assert all(value is False for value in memory["authority"].values())
    assert memory["calendar_integrity"]["paper_growth_trial_calendar_advanced"] is False
    assert memory["calendar_integrity"]["paper_growth_trial_day_delta"] == 0
    assert memory["calendar_integrity"]["paper_proof_ledger_credit_granted"] is False
    assert memory["no_30_day_paper_growth_trial_advance"] is True
    assert memory["no_paper_proof_ledger_credit"] is True
    assert all(record["paper_proof_ledger_eligible"] is False for record in records[:100])
    assert all(record["proof_credit_allowed"] is False for record in records[:100])
    assert all(record["execution_allowed"] is False for record in records[:100])


def test_historical_memory_leakage_checks_missing_windows_and_index():
    memory = build_historical_source_price_memory()
    first_missing = next(record for record in memory["records"] if record["replay_state"] == "missing_outcome_window")
    index = build_point_in_time_replay_index(memory)

    assert memory["leakage_checks"]["status"] == "leakage_checks_passed"
    assert first_missing["missing_window_record_id"]
    assert first_missing["outcome_available_at"] is None
    assert not any(key.startswith("return_") for key in first_missing["features"])
    assert index["record_count"] == memory["memory_record_count"]
    assert "point_in_time_replay" in index["indices"]["by_replay_mode"]
    assert validate_negative_historical_memory_probes() == []
