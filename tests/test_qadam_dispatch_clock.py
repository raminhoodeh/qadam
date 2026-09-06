from dataclasses import replace
from datetime import datetime, timedelta, timezone
import json

import pytest

from orchestrator.config import Settings
import orchestrator.qadam_operator_service as operator


@pytest.mark.parametrize(
    ("scenario", "expected_state", "expected_reason"),
    [
        ("becomes_due", "completed", None),
        ("market_closes", "skipped", "market_closed"),
        ("evidence_expires", "skipped", "stale_prerequisite"),
    ],
)
def test_dispatch_rechecks_time_after_preceding_work(
    tmp_path, monkeypatch, scenario, expected_state, expected_reason
):
    start = datetime(2026, 9, 8, 19, 59, tzinfo=timezone.utc)
    clock = [start]
    definitions = tuple(
        replace(
            definition,
            dependencies=(),
            prerequisite_artifacts=(),
            read_resources=(),
            write_resources=(),
            append_resources=(),
            generation_artifacts=(),
            market_session_only=False,
            paperops_dependency=False,
            provider_budget_required=False,
            long_running=False,
            wake_on_dependency_advance=False,
        )
        for service_id in ("source_ingestion", "pattern_scoring")
        for definition in operator.SERVICE_DEFINITIONS
        if definition.service_id == service_id
    )
    first, second = definitions
    if scenario == "market_closes":
        second = replace(second, market_session_only=True)
    elif scenario == "evidence_expires":
        second = replace(
            second,
            prerequisite_artifacts=("evidence.json",),
            prerequisite_max_age_seconds=60,
        )
        (tmp_path / "evidence.json").write_text(
            json.dumps({"generated_at": start.isoformat()}), encoding="utf-8"
        )
    else:
        second = replace(second, cadence_seconds=60)
        operator._append_receipt(
            tmp_path,
            {
                "service_id": second.service_id,
                "state": "completed",
                "completed_at": start.isoformat(),
            },
        )
    definitions = (first, second)
    monkeypatch.setattr(operator, "SERVICE_DEFINITIONS", definitions)
    monkeypatch.setattr(operator, "validate_domain_coverage", lambda _ids: [])
    monkeypatch.setattr(operator, "_fair_dispatch_order", lambda *a, **kw: (definitions, None))
    monkeypatch.setattr(operator, "now_iso", lambda: clock[0].isoformat())
    executed = []

    def execute(definition, **_kwargs):
        executed.append(definition.service_id)
        clock[0] += timedelta(minutes=2)
        return {
            "state": "completed",
            "duration_seconds": 120,
            "command_results": [],
            "generation_ids": {},
            "input_generation_ids": {},
            "input_generation_binding_complete": True,
            "mixed_generation_join_count": 0,
        }

    monkeypatch.setattr(operator, "_execute_service_synchronously", execute)
    settings = replace(Settings.from_env(), runtime_dir=str(tmp_path), data_root=str(tmp_path.parent))
    cycle = operator.dispatch_due_jobs(
        settings, service_ids=tuple(row.service_id for row in definitions), executor=lambda *a: None
    )
    receipt = cycle["receipts"][1]
    assert cycle["generated_at"] == start.isoformat()
    assert receipt["generated_at"] == (start + timedelta(minutes=2)).isoformat()
    assert receipt["state"] == expected_state
    assert receipt.get("skip_reason") == expected_reason
    assert executed == ([first.service_id, second.service_id] if expected_state == "completed" else [first.service_id])
