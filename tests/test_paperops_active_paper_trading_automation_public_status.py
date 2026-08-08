from __future__ import annotations

from orchestrator import paperops_active_paper_trading_automation as module


def test_public_status_redacts_internal_action_record_details(monkeypatch) -> None:
    artifact = {
        key: None for key in module.PAPEROPS_ACTIVE_AUTOMATION_PUBLIC_FIELDS
    }
    artifact.update(
        {
            "action_records": [
                {
                    "label": "paper_submit",
                    "ok": True,
                    "returncode": 0,
                    "args": ["--runtime-dir", "/Users/operator/qadam/data/runtime"],
                    "stderr_tail": ["read /Users/operator/qadam/private.json"],
                    "parsed": {
                        "paperops_alpaca_post_artifact_path": (
                            "/Users/operator/qadam/data/runtime/paper_post.json"
                        )
                    },
                    "live_endpoint_called_count": 0,
                    "live_capital_enabled": False,
                    "secret_value_exposed": False,
                }
            ],
            "action_record_count": 1,
            "blockers": [],
            "paperops_blockers": [],
            "validation_errors": [],
        }
    )
    monkeypatch.setattr(
        module,
        "read_latest_paperops_active_paper_trading_automation",
        lambda settings=None: artifact,
    )

    public = module.paperops_active_paper_trading_automation_public_status()

    assert public["action_record_count"] == 1
    assert public["action_records"] == [
        {
            "label": "paper_submit",
            "ok": True,
            "returncode": 0,
            "live_endpoint_called_count": 0,
            "live_capital_enabled": False,
            "secret_value_exposed": False,
        }
    ]
    assert "/Users/" not in str(public)
