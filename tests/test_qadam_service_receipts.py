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
