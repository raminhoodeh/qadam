from copy import deepcopy
import json

import pytest

from orchestrator.qadam_discovery_micro_certification import expectancy_runtime_contract
from orchestrator.qadam_discovery_micro_conversion import CURRENT_EXPECTANCY_ARTIFACT
from orchestrator.qadam_operator_ready_common import sha256_json

NOW = "2026-09-28T20:00:00+00:00"


def generation(tmp_path, rows):
    queue = {"rows": [{"state": "ready_for_preregistered_experiment"} for _ in rows]}
    foundry = {
        "status": "passed",
        "queue_ready_count": len(rows),
        "current_expectancy_record_count": len(rows),
        "current_expectancy_generation": {
            "completed_at": NOW,
            "record_count": len(rows),
            "records_digest": sha256_json(rows),
            "queue_digest": sha256_json(queue),
            "state": "completed" if rows else "completed_empty",
        },
    }
    (tmp_path / CURRENT_EXPECTANCY_ARTIFACT).write_text(
        "".join(json.dumps(row) + "\n" for row in rows)
    )
    return foundry, queue


def test_active_empty_active_scans_remain_valid(tmp_path):
    row = {
        "artifact_type": "qadam_current_expectancy_v2",
        "research_score_is_probability": False,
        "historical_expectancy_required": False,
        "not_execution_approval": True,
    }
    for rows, state in [([row], "completed"), ([], "completed_empty"), ([row], "completed")]:
        foundry, queue = generation(tmp_path, rows)
        actual, report = expectancy_runtime_contract(tmp_path, foundry, queue, NOW)
        assert actual == rows
        assert report["state"] == state


def test_missing_file_cannot_be_certified_empty(tmp_path):
    foundry, queue = generation(tmp_path, [])
    (tmp_path / CURRENT_EXPECTANCY_ARTIFACT).unlink()
    assert (
        expectancy_runtime_contract(tmp_path, foundry, queue, NOW)[1]["state"]
        == "dependency_unavailable"
    )


def test_new_queue_requests_producer_refresh(tmp_path):
    foundry, queue = generation(tmp_path, [])
    queue["rows"].append({"state": "ready_for_preregistered_experiment"})
    assert (
        expectancy_runtime_contract(tmp_path, foundry, queue, NOW)[1]["reason"]
        == "queue_generation_advanced"
    )


def test_stale_empty_scan_is_not_healthy(tmp_path):
    foundry, queue = generation(tmp_path, [])
    foundry["current_expectancy_generation"]["completed_at"] = "2026-09-28T18:00:00+00:00"
    assert (
        expectancy_runtime_contract(tmp_path, foundry, queue, NOW)[1]["reason"]
        == "producer_not_current"
    )


@pytest.mark.parametrize("corruption", ["malformed", "count", "digest", "ready", "authority"])
def test_corruption_does_not_become_safe_idle(tmp_path, corruption):
    foundry, queue = generation(tmp_path, [])
    if corruption == "malformed":
        (tmp_path / CURRENT_EXPECTANCY_ARTIFACT).write_text("{truncated")
    elif corruption == "count":
        foundry["current_expectancy_generation"]["record_count"] = 1
    elif corruption == "digest":
        foundry["current_expectancy_generation"]["records_digest"] = "wrong"
    elif corruption == "ready":
        queue["rows"] = [{"state": "ready_for_preregistered_experiment"}]
        foundry["current_expectancy_generation"]["queue_digest"] = sha256_json(queue)
    else:
        foundry, queue = generation(tmp_path, [{"not_execution_approval": False}])
    assert (
        expectancy_runtime_contract(tmp_path, deepcopy(foundry), queue, NOW)[1]["state"]
        == "invalid"
    )
