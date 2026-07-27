from datetime import datetime, timedelta, timezone
import json

from orchestrator import qadam_permanent_operator_reliability as reliability


def _write_json(path, payload):
    path.write_text(json.dumps(payload), encoding="utf-8")


def _write_sessions(path, records):
    path.write_text(
        "".join(json.dumps(record, sort_keys=True) + "\n" for record in records),
        encoding="utf-8",
    )


def _healthy_session(timestamp):
    return {
        "generated_at": timestamp.isoformat(),
        "dispatch_failed_count": 0,
        "operator_observation_ready": True,
        "operator_build_identity_matches": True,
        "paper_order_created_count": 0,
        "broker_write_count": 0,
        "authority": reliability.authority_flags(),
    }


def test_soak_requires_one_contiguous_healthy_window(tmp_path, monkeypatch):
    identity = {
        "service_contract_hash": "contract",
        "git_commit": "commit",
        "dirty_worktree_digest": "dirty",
        "python_executable": "python",
        "python_version": "3.12",
        "dependency_lock_digest": "deps",
        "state_root": str(tmp_path),
        "launchd_template_sha256": "launchd",
    }
    monkeypatch.setattr(reliability, "operator_build_identity", lambda: identity)
    started = datetime(2026, 7, 24, 0, 0, tzinfo=timezone.utc)
    _write_json(
        tmp_path / reliability.SOAK_ARTIFACT,
        {"activation_identity": identity, "started_at": started.isoformat()},
    )
    _write_json(tmp_path / reliability.CIRCUIT_BREAKERS_ARTIFACT, {"open_circuit_count": 0})
    _write_json(
        tmp_path / reliability.REPAIR_QUEUE_ARTIFACT,
        {"critical_request_count": 0},
    )
    sessions = [_healthy_session(started + timedelta(minutes=15 * index)) for index in range(120)]
    _write_sessions(tmp_path / reliability.SESSION_LEDGER_ARTIFACT, sessions)

    result = reliability.build_reliability_soak(tmp_path)

    assert result["status"] == "passed"
    assert result["real_session_count"] == 120
    assert set(result["observed_market_periods"]) == {"market_closed", "market_open"}


def test_unhealthy_session_resets_soak_instead_of_being_hidden(tmp_path, monkeypatch):
    identity = {
        "service_contract_hash": "contract",
        "git_commit": "commit",
        "dirty_worktree_digest": "dirty",
        "python_executable": "python",
        "python_version": "3.12",
        "dependency_lock_digest": "deps",
        "state_root": str(tmp_path),
        "launchd_template_sha256": "launchd",
    }
    monkeypatch.setattr(reliability, "operator_build_identity", lambda: identity)
    started = datetime(2026, 7, 24, 0, 0, tzinfo=timezone.utc)
    _write_json(
        tmp_path / reliability.SOAK_ARTIFACT,
        {"activation_identity": identity, "started_at": started.isoformat()},
    )
    _write_json(tmp_path / reliability.CIRCUIT_BREAKERS_ARTIFACT, {"open_circuit_count": 0})
    _write_json(
        tmp_path / reliability.REPAIR_QUEUE_ARTIFACT,
        {"critical_request_count": 0},
    )
    records = [_healthy_session(started + timedelta(minutes=15 * index)) for index in range(120)]
    unhealthy = _healthy_session(started + timedelta(hours=31))
    unhealthy["operator_observation_ready"] = False
    records.append(unhealthy)
    _write_sessions(tmp_path / reliability.SESSION_LEDGER_ARTIFACT, records)

    result = reliability.build_reliability_soak(tmp_path)

    assert result["status"] == "running"
    assert result["real_session_count"] == 0
    assert result["invalid_session_count"] == 1
