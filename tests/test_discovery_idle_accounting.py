from copy import deepcopy

import pytest

from orchestrator.qadam_discovery_micro_certification import active_pattern_accounting

NOW = "2026-10-20T20:00:00+00:00"


def scan(rows=None):
    rows = [] if rows is None else rows
    return {"status": "complete", "generated_at": NOW, "graph_generation_id": "observed:one",
            "candidates": rows, "candidate_count": len(rows)}


def test_market_close_empty_scan_is_valid_idle_not_an_instruction_to_trade():
    passed, state = active_pattern_accounting(scan(), [], generated_at=NOW)
    assert passed and state == "valid_idle_no_qualifying_active_patterns"


@pytest.mark.parametrize("change", [{}, {"status": "pending"}, {"candidate_count": 1},
                                    {"graph_generation_id": None}, {"generated_at": "2020-01-01T00:00:00+00:00"}])
def test_missing_or_unverified_empty_input_cannot_be_certified(change):
    value = {**scan(), **change} if change else {}
    assert active_pattern_accounting(value, [], generated_at=NOW)[0] is False


def test_active_unaccounted_pattern_still_fails():
    value = scan([{"pattern_relationship_id": "one", "research_rank": 0.7, "current_trigger_active": True}])
    assert active_pattern_accounting(value, [], generated_at=NOW)[0] is False
    assert active_pattern_accounting(value, [{"pattern_relationship_id": "one", "accounted_for": False}], generated_at=NOW)[0] is False
    assert active_pattern_accounting(value, [{"pattern_relationship_id": "one", "accounted_for": True}], generated_at=NOW)[0] is True


def test_partial_or_duplicate_accounting_is_not_success():
    one = {"pattern_relationship_id": "one", "research_rank": 0.7, "current_trigger_active": True}
    two = {**one, "pattern_relationship_id": "two"}
    value = scan([one, two])
    outcomes = [{"pattern_relationship_id": "one", "accounted_for": True}]
    assert active_pattern_accounting(value, outcomes, generated_at=NOW)[0] is False
    assert active_pattern_accounting(scan([one]), outcomes * 2, generated_at=NOW)[0] is False


def test_inactive_or_low_scoring_observations_are_not_unaccounted_active_setups():
    row = {"pattern_relationship_id": "one", "research_rank": 0.7, "current_trigger_active": False}
    assert active_pattern_accounting(scan([row]), [], generated_at=NOW)[0] is True
    row = deepcopy(row)
    row.update(current_trigger_active=True, research_rank=0.1)
    assert active_pattern_accounting(scan([row]), [], generated_at=NOW)[0] is True


def test_absent_and_stale_scans_are_typed_dependency_holds_not_valid_idle():
    assert active_pattern_accounting({}, [], generated_at=NOW) == (False, "candidate_scan_missing")
    stale = {**scan(), "generated_at": "2026-10-20T18:00:00+00:00"}
    assert active_pattern_accounting(stale, [], generated_at=NOW) == (False, "candidate_scan_stale")
