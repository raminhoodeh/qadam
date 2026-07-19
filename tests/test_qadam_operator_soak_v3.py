from __future__ import annotations

import json

from orchestrator.qadam_operator_soak_v3 import (
    build_operator_soak_v3,
    operator_service_contract_hash,
    validate_operator_soak_v3,
)


def _write(path, payload) -> None:
    path.write_text(json.dumps(payload) + "\n", encoding="utf-8")


def test_pre_release_sessions_do_not_count(monkeypatch, tmp_path) -> None:
    monkeypatch.setattr(
        "orchestrator.qadam_operator_soak_v3.runtime_dir", lambda _settings=None: tmp_path
    )
    _write(
        tmp_path / "qadam_operator_session_ledger.jsonl",
        {
            "generated_at": "2026-07-19T00:00:00+00:00",
            "real_calendar_date": "2026-07-19",
            "real_elapsed_time": True,
            "simulated_elapsed_time_used": False,
        },
    )
    soak = build_operator_soak_v3()
    assert soak["completed_real_session_count"] == 0
    assert soak["pre_release_or_version_mismatched_session_count"] == 1
    assert soak["soak_complete"] is False


def test_only_exact_release_bound_sessions_receive_credit(monkeypatch, tmp_path) -> None:
    monkeypatch.setattr(
        "orchestrator.qadam_operator_soak_v3.runtime_dir", lambda _settings=None: tmp_path
    )
    _write(
        tmp_path / "qadam_experimental_paper_release_readiness.json",
        {
            "experimental_paper_release_effective": True,
            "release_started_at": "2026-07-19T00:00:00+00:00",
            "binding_digest": "binding:test",
            "policy_version": "policy:test",
            "risk_policy_version": "risk:test",
        },
    )
    _write(
        tmp_path / "current_paper_epoch.json",
        {
            "paper_epoch_id": "epoch:test",
            "paper_epoch_kind": "clean_experimental_operator_epoch",
        },
    )
    rows = []
    for day in range(1, 8):
        rows.append(
            {
                "generated_at": f"2026-07-{18 + day:02d}T12:00:00+00:00",
                "real_calendar_date": f"2026-07-{18 + day:02d}",
                "real_elapsed_time": True,
                "simulated_elapsed_time_used": False,
                "paper_epoch_id": "epoch:test",
                "release_binding_digest": "binding:test",
                "policy_version": "policy:test",
                "risk_policy_version": "risk:test",
                "operator_service_contract_hash": operator_service_contract_hash(),
            }
        )
    (tmp_path / "qadam_operator_session_ledger.jsonl").write_text(
        "".join(json.dumps(row) + "\n" for row in rows), encoding="utf-8"
    )
    scenarios = [
        {
            "scenario": name,
            "classification_passed": True,
            "safe_response_passed": True,
            "paper_order_created": False,
            "broker_write_count": 0,
        }
        for name in (
            "network_loss",
            "laptop_sleep",
            "sigterm",
            "provider_429",
            "malformed_response",
            "stale_lock",
            "disk_threshold",
            "unsafe_route",
        )
    ]
    _write(tmp_path / "qadam_operator_soak_test.json", {"scenarios": scenarios})
    _write(tmp_path / "qadam_operator_service_checks.json", {"service_running": True})
    _write(tmp_path / "qadam_public_status_bridge_checks.json", {"operating_ready": True})
    _write(tmp_path / "qadam_operator_repair_queue.json", {"critical_request_count": 0})
    soak = build_operator_soak_v3()
    assert soak["completed_real_session_count"] == 7
    assert soak["soak_complete"] is True


def test_soak_validator_rejects_fabricated_time() -> None:
    soak = {
        "simulated_elapsed_time_used": True,
        "soak_complete": False,
        "broker_write_count": 0,
        "live_capital_enabled": False,
        "authority": {},
    }
    probes = {
        "automatic_paperops_retry_allowed": False,
        "broker_write_count": 0,
        "live_capital_enabled": False,
        "authority": {},
    }
    assert "operator_soak_v3_simulated_elapsed_time" in validate_operator_soak_v3(
        soak, probes
    )
