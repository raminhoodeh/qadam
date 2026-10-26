from copy import deepcopy

import pytest

from orchestrator.qadam_discovery_micro_certification import certification_recovery_class

EXPECTANCY = "acceptance_check_failed:fix_02_current_expectancy_v2"
SCAN = "acceptance_target_failed:high_scoring_active_patterns_accounted_for"


def payload():
    return {"active_pattern_accounting_state": "candidate_scan_stale", "checks": [{
        "check_id": "fix_02_current_expectancy_v2", "passed": False,
        "evidence": {"runtime_generation": {
            "state": "dependency_unavailable", "reason": "producer_not_current"}},
    }]}


@pytest.mark.parametrize("errors", [[EXPECTANCY], [SCAN], [EXPECTANCY, SCAN], [SCAN, EXPECTANCY]])
def test_independent_stale_dependencies_compose_without_becoming_code_defects(errors):
    assert certification_recovery_class(payload(), errors) == "dependency_unavailable"


@pytest.mark.parametrize("fault", ["unknown", "corrupt", "missing", "unexpected_reason", "invalid_scan", "pass", "no_errors"])
def test_unknown_or_integrity_failures_are_never_downgraded(fault):
    row = deepcopy(payload())
    errors = [EXPECTANCY, SCAN]
    generation = row["checks"][0]["evidence"]["runtime_generation"]
    if fault == "unknown":
        errors.append("acceptance_check_failed:policy_authority")
    elif fault == "corrupt":
        generation["state"] = "invalid"
    elif fault == "missing":
        row["checks"] = []
    elif fault == "unexpected_reason":
        generation["reason"] = "payload_corruption"
    elif fault == "invalid_scan":
        row["active_pattern_accounting_state"] = "candidate_scan_invalid"
    elif fault == "pass":
        row["checks"][0]["passed"] = True
    else:
        errors = []
    assert certification_recovery_class(row, errors) is None
