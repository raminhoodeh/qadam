import json

from scripts import apply_qadam_discovery_micro_policy as cli
from tests.test_qadam_experimental_policy_amendment import _inputs


def test_staged_policy_needs_explicit_new_approval_and_original_mandate(tmp_path, monkeypatch):
    previous, staged, approval, epoch, calendar = _inputs()
    records = {"qadam_operator_maintenance_window.json": {"status": "active"},
               cli.POLICY_ARTIFACT: staged,
               "qadam_experimental_paper_release_approval.json": approval,
               "current_paper_epoch.json": epoch, "qadam_paper_trial_calendar.json": calendar,
               "qadam_guarded_paper_launch_receipt.json": {"launch_executed": True, "direct_broker_call_count": 0},
               "qadam_long_backtest_lock.json": {"status": "released", "paperops_watch_only_mode": False},
               cli.AMENDMENT_ARTIFACT: {"amendment_id": "old-invalid-amendment"}}
    monkeypatch.setattr(cli, "runtime_dir", lambda: tmp_path)
    monkeypatch.setattr(cli, "read_json", lambda path: records.get(path.name, {}))
    monkeypatch.setattr(cli, "read_jsonl", lambda path: [previous])
    monkeypatch.setattr(cli, "file_sha256", lambda path: "approval-sha")
    monkeypatch.setattr(cli, "build_and_write_experimental_policy", lambda: None)
    monkeypatch.setattr("sys.argv", ["apply", "--approve-discovery-micro"])
    assert cli.main() == 1
    monkeypatch.setattr("sys.argv", ["apply", "--approve-discovery-micro", "--reapprove-staged-policy"])
    assert cli.main() == 0
    amended = json.loads((tmp_path / cli.AMENDMENT_ARTIFACT).read_text())
    assert amended["explicit_staged_policy_reapproval"] is True
    assert amended["replaces_amendment_id"] == "old-invalid-amendment"
    assert amended["supersedes_policy_version"] is None
    assert amended["paper_trial_calendar_reset"] is False
    assert amended["broker_write_count"] == 0
    records["qadam_experimental_paper_release_approval.json"] = {**approval, "experimental_paper_mandate_approved": False}
    assert cli.main() == 1
