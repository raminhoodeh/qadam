from pathlib import Path

from orchestrator.runtime.operator import _cycle_material_change_state, _result_is_evidence_hold
from orchestrator.runtime.processes import run_command

ROOT = Path(__file__).resolve().parents[1]


def test_real_child_receipt_does_not_depend_on_stdout_tail():
    result = run_command(("tests/fixtures/refactor_receipt_probe.py",), 10, root=ROOT, sanitize=lambda value: value[-100:])
    assert result["returncode"] == 0
    assert result["command_receipt_valid"] is True
    assert result["work_result"]["material_change_detected"] is True
    assert _cycle_material_change_state([{"service_id": "pattern_scoring", "command_results": [result]}], "pattern_scoring") is True


def test_zero_exit_without_receipt_is_failed():
    result = run_command(("tests/fixtures/refactor_receipt_probe.py", "--missing-receipt"), 10, root=ROOT, sanitize=str)
    assert result["returncode"] == 70
    assert result["command_receipt_valid"] is False


def test_required_work_receipt_and_normal_sibling_imports_work_in_real_child():
    result = run_command(("tests/fixtures/refactor_receipt_probe.py", "--sibling-import"), 10,
                         root=ROOT, sanitize=str, require_work_result=True)
    assert result["returncode"] == 0
    assert result["command_receipt_valid"] is True
    assert result["work_result"]["checked_at"]
    missing = run_command(("tests/fixtures/refactor_receipt_probe.py", "--missing-work"), 10,
                          root=ROOT, sanitize=str, require_work_result=True)
    assert missing["returncode"] == 70
    assert missing["command_receipt_valid"] is False


def test_every_scheduled_terminal_checker_has_a_semantic_result_producer():
    from orchestrator.runtime.services import SERVICE_DEFINITIONS
    for service in SERVICE_DEFINITIONS:
        path = ROOT / service.command_sequence[-1][0]
        if path.name == "check_qadam_backtest_completion.py":
            path = ROOT / "scripts/qadam_qbc_check.py"
        assert "report_work_result(" in path.read_text(), service.service_id


def test_busy_execution_owner_cannot_refresh_generations_or_clear_circuit(tmp_path, monkeypatch):
    from orchestrator.runtime import operator
    from orchestrator.runtime.services import ServiceDefinition
    definition = ServiceDefinition(service_id="fixture-owner", purpose="test", cadence_seconds=60,
        trigger="test", ownership="test", safe_retry_class="test", recovery_mode="test",
        command_sequence=(("tests/fixtures/refactor_receipt_probe.py",),), timeout_seconds=5,
        dependencies=(), concurrency_group="test", lock_requirement="test", safety_mode="test")
    def forbidden(*args):
        raise AssertionError("busy owner must not republish yesterday's output")
    monkeypatch.setattr(operator, "_publish_service_generations", forbidden)
    result = operator._execute_service_synchronously(definition, runtime=tmp_path,
        executor=lambda *args: {"returncode": 0, "work_result": {"status": "deferred_owner_busy"}})
    assert result["state"] == "deferred_resource_busy"
    assert result["generation_ids"] == {}


def test_log_words_never_grant_evidence_hold_or_no_change():
    result = {"returncode": 1, "stdout": "status=hold\nvalidation_error_count=0\nmaterial_change_detected=False"}
    assert _result_is_evidence_hold(result) is False
    assert _cycle_material_change_state([{"service_id": "pattern_scoring", "command_results": [result]}], "pattern_scoring") is None


def test_worker_output_is_bounded_and_timeout_reaps_child_group(tmp_path):
    import os
    import sys
    import time
    from orchestrator.runtime.processes import _invoke

    large = _invoke([sys.executable, "-c", "print('x'*2000000)"], root=tmp_path,
                    environment=dict(os.environ), timeout=5)
    assert large["returncode"] == 0
    assert len(large["stdout"].encode()) <= 65536
    assert large["output_byte_counts"]["stdout"] == 2000001
    started = time.monotonic()
    hung = _invoke([sys.executable, "-c", "import time; time.sleep(60)"], root=tmp_path,
                   environment=dict(os.environ), timeout=1)
    assert hung["timed_out"] is True
    assert hung["returncode"] == 124
    assert time.monotonic() - started < 4


def test_completed_wrapper_cannot_leave_a_writer_running_after_resource_release(tmp_path):
    import os
    import sys
    import time
    from orchestrator.runtime.processes import _invoke

    delayed_write = "import time; from pathlib import Path; time.sleep(2); Path('orphan-write').touch()"
    parent = f"import subprocess,sys; subprocess.Popen([sys.executable, '-c', {delayed_write!r}])"
    result = _invoke([sys.executable, "-c", parent], root=tmp_path,
                     environment=dict(os.environ), timeout=5)
    assert result["returncode"] == 0
    time.sleep(2)
    assert not (tmp_path / "orphan-write").exists()
