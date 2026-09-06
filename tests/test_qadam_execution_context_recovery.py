from dataclasses import replace
from datetime import datetime, timezone
import json

from orchestrator.config import Settings
from orchestrator.qadam_execution_context import build_execution_contexts
from orchestrator.qadam_operator_service import SERVICE_DEFINITIONS, dispatch_due_jobs
import orchestrator.qadam_operator_service as operator


def test_context_can_recover_without_market_hours_receipt(tmp_path, monkeypatch):
    settings = replace(Settings.from_env(), runtime_dir=str(tmp_path),
                       data_root=str(tmp_path.parent), state_root=str(tmp_path.parent))
    definition = next(d for d in SERVICE_DEFINITIONS if d.service_id == "execution_context")
    assert definition.dependencies == ()
    assert definition.market_session_only is False
    monkeypatch.setattr(operator, "_market_is_open", lambda timestamp: False)
    for name in definition.generation_artifacts:
        if name.endswith(".json"):
            (tmp_path / name).write_text(json.dumps({"status": "passed", "fixture": True}))
    calls = []

    def execute(command, timeout):
        calls.append(command)
        return {"returncode": 0, "stdout": "", "stderr": "", "duration_seconds": 0.01,
                "timed_out": False}

    result = dispatch_due_jobs(settings, service_ids=("execution_context",),
                               executor=execute, force_due=True)
    assert result["receipts"][0]["state"] == "completed"
    assert calls == [("scripts/check_qadam_execution_context.py",)]


def test_empty_context_recovery_does_not_create_actionability(tmp_path):
    settings = replace(Settings.from_env(), runtime_dir=str(tmp_path))
    (tmp_path / "qadam_instrument_role_registry.json").write_text(json.dumps({
        "instruments": [{"symbol": "SPY", "guarded_paper_route_confirmed": True}]}))
    contexts, summary, errors = build_execution_contexts(
        settings, timestamp=datetime(2026, 9, 6, 18, tzinfo=timezone.utc))
    assert errors == []
    assert contexts[0]["status"] == "provider_degraded"
    assert summary["quote_ready_count"] == 0
    assert summary["broker_write_count"] == 0
