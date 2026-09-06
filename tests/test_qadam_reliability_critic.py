from __future__ import annotations

from dataclasses import replace
from pathlib import Path
import plistlib
import pytest

from orchestrator.config import Settings
from orchestrator.qadam_operator_ready_common import ROOT, authority_flags
from orchestrator.qadam_reliability_critic import (
    REPAIR_PACKET_ARTIFACT,
    STATUS_ARTIFACT,
    classify_reliability_snapshot,
    plan_safe_repairs,
    run_reliability_critic,
    validate_reliability_critic_payload,
)
import orchestrator.qadam_reliability_critic as critic_module


@pytest.mark.parametrize("reason", ["full_heal_request_superseded", "operator_build_changed"])
def test_obsolete_full_heal_wait_returns_for_replanning(tmp_path, monkeypatch, reason):
    request = {"request_id": "old-request", "git_commit": "old-build"}
    monkeypatch.setattr(critic_module, "request_operator_full_heal", lambda *a, **k: request)

    def read(path):
        if path.name == critic_module.FULL_HEAL_REQUEST_ARTIFACT:
            return {"request_id": "new-request" if reason.endswith("superseded") else "old-request"}
        if path.name == critic_module.LEASE_ARTIFACT:
            return {"status": "active", "build_identity": {"git_commit": "new-build"}}
        return {}

    monkeypatch.setattr(critic_module, "read_json", read)
    results = critic_module.execute_safe_repairs(
        [{"action_type": "request_operator_full_heal", "service_ids": ["public_status_publication"]}],
        _settings(tmp_path), operator_heal_wait_seconds=7200,
        sleep_fn=lambda _: pytest.fail("obsolete build must not wait for an impossible receipt"),
    )
    assert results[0]["status"] == "replan_required"
    assert results[0]["replan_reason"] == reason
    assert results[0]["verified"] is False


def _settings(tmp_path: Path) -> Settings:
    return replace(
        Settings.from_env(),
        runtime_dir=str(tmp_path),
        data_root=str(tmp_path.parent),
    )


def _authority() -> dict[str, bool | int]:
    return {
        **authority_flags(),
        "autonomous_code_edit_allowed": False,
        "risk_threshold_mutation_allowed": False,
        "strategy_admission_allowed": False,
        "paperops_invocation_allowed": False,
        "operator_full_heal_request_allowed": True,
        "operator_restart_allowed": True,
        "safe_runtime_revalidation_allowed": True,
    }


def _healthy_snapshot(
    *,
    fresh_eligible: int = 0,
    accepted_handoffs: int = 0,
    session_phase: str = "regular",
) -> dict:
    return {
        "schema_version": "qadam_reliability_critic.v1",
        "observed_at": "2026-08-26T08:00:00+00:00",
        "market": {"expected_session_phase": session_phase},
        "operator": {
            "present": True,
            "age_seconds": 20.0,
            "lease_age_seconds": 5.0,
            "lease_process_alive": True,
            "service_running": True,
            "service_installed": True,
            "operational_ready": True,
            "observation_ready": True,
            "committed_release": True,
            "running_build_matches_current": True,
            "launchd_template_matches": True,
            "fresh_service_count": 21,
            "stale_service_count": 0,
            "not_run_service_count": 0,
            "open_circuit_count": 0,
            "order_exposure_integrity": {"status": "passed"},
        },
        "repair_queue": {
            "open_request_count": 0,
            "critical_request_count": 0,
        },
        "circuits": {"open_circuit_count": 0, "services": {}},
        "self_healing": {
            "stale_or_missing_artifact_count": 0,
            "repair_request_count": 0,
        },
        "hedge_fund_team": {
            "present": True,
            "age_seconds": 30.0,
            "status": "passed",
            "required_role_count": 4,
            "healthy_required_role_count": 4,
            "team": {},
            "trading_pipeline": {
                "status": "healthy",
                "healthy_stage_count": 10,
                "stage_count": 10,
            },
            "blockers": [],
        },
        "paperops": {
            "present": True,
            "age_seconds": 100.0,
            "summary_fresh": True,
            "status": "ready_idle",
            "blockers": [],
            "canonical_control_status": "canonical_paper_control_ready",
            "canonical_control_blockers": [],
            "fresh_eligible_submit_count": fresh_eligible,
            "accepted_handoff_count": accepted_handoffs,
        },
        "router": {
            "status": "not_trading",
            "age_seconds": 20.0,
            "primary_reason": "No current setup is ready for paper review.",
        },
        "control_plane": {
            "present": True,
            "unresolved_repair_request_count": 0,
            "latest_reconciliation": {
                "status": "passed",
                "blocker_count": 0,
            },
            "latest_liveness": {},
            "current_handoff_count": accepted_handoffs,
        },
        "automation": {
            "installed": True,
            "loaded": True,
            "installed_template_matches": True,
        },
        "authority": _authority(),
    }


def test_healthy_idle_is_not_misclassified_as_failure() -> None:
    classification = classify_reliability_snapshot(_healthy_snapshot())

    assert classification["healthy"] is True
    assert classification["state"] == "healthy_idle_explained"
    assert classification["blockers"] == []


def test_scheduled_repair_pass_does_not_replay_a_healthy_pipeline() -> None:
    snapshot = _healthy_snapshot()
    classification = classify_reliability_snapshot(snapshot)

    actions = plan_safe_repairs(snapshot, classification)

    assert actions == []


def test_live_owner_cannot_make_a_stale_paperops_summary_healthy() -> None:
    snapshot = _healthy_snapshot()
    snapshot["paperops"].update(
        {
            "age_seconds": 7_200.0,
            "summary_fresh": False,
            "owner_liveness_current": True,
            "owner_service_state": "idle_no_eligible_work",
            "owner_skip_reason": "no_eligible_work",
        }
    )

    classification = classify_reliability_snapshot(snapshot)

    assert classification["healthy"] is False
    assert classification["state"] == "pipeline_degraded_repairable"
    assert classification["blockers"][0]["code"] == "paperops_summary_stale"
    actions = plan_safe_repairs(snapshot, classification)
    assert actions[0]["action_type"] == "request_operator_full_heal"
    assert "guarded_paperops" in actions[0]["service_ids"]


def test_stale_actionable_counts_cannot_create_a_current_trade_ready_claim() -> None:
    snapshot = _healthy_snapshot(
        fresh_eligible=1,
        accepted_handoffs=1,
        session_phase="pre_market",
    )
    snapshot["paperops"].update(
        {
            "age_seconds": 48 * 60 * 60,
            "summary_fresh": False,
            "owner_liveness_current": True,
            "owner_service_state": "idle_no_eligible_work",
            "owner_skip_reason": "no_eligible_work",
        }
    )

    classification = classify_reliability_snapshot(snapshot)

    assert classification["healthy"] is False
    assert classification["state"] == "pipeline_degraded_repairable"
    assert classification["blockers"][0]["code"] == "paperops_summary_stale"


def test_stale_summary_and_stale_owner_remain_fail_closed() -> None:
    snapshot = _healthy_snapshot()
    snapshot["paperops"].update(
        {
            "age_seconds": 7_200.0,
            "summary_fresh": False,
            "owner_liveness_current": False,
            "owner_service_state": "supervised",
        }
    )

    classification = classify_reliability_snapshot(snapshot)

    assert classification["healthy"] is False
    assert classification["blockers"][0]["code"] == "paperops_summary_stale"


def test_long_worker_cycle_uses_fresh_lease_instead_of_false_staleness() -> None:
    snapshot = _healthy_snapshot()
    snapshot["operator"]["age_seconds"] = 31 * 60

    classification = classify_reliability_snapshot(snapshot)

    assert classification["healthy"] is True
    assert classification["state"] == "healthy_idle_explained"


def test_actionable_setup_waiting_for_market_is_healthy() -> None:
    classification = classify_reliability_snapshot(
        _healthy_snapshot(fresh_eligible=1, accepted_handoffs=1, session_phase="pre_market")
    )

    assert classification["healthy"] is True
    assert classification["state"] == "healthy_actionable_waiting_market_session"


def test_stopped_reviewed_operator_restarts_without_replaying_healthy_services() -> None:
    snapshot = _healthy_snapshot()
    snapshot["operator"].update(
        {
            "service_running": False,
            "age_seconds": 10.0,
            "service_installed": True,
            "committed_release": True,
            "launchd_template_matches": True,
        }
    )
    classification = classify_reliability_snapshot(snapshot)
    actions = plan_safe_repairs(snapshot, classification)

    assert classification["state"] == "pipeline_degraded_repairable"
    assert actions[0] == {
        "action_type": "restart_operator_owner",
        "service_id": None,
        "trigger_code": "operator_owner_not_running",
        "trigger_codes": ["operator_owner_not_running"],
    }
    assert len(actions) == 1


def test_broker_disagreement_escalates_without_auto_repair() -> None:
    snapshot = _healthy_snapshot()
    snapshot["operator"]["order_exposure_integrity"] = {"status": "blocked_duplicate_exposure"}
    classification = classify_reliability_snapshot(snapshot)

    assert classification["state"] == "pipeline_degraded_escalation_required"
    assert plan_safe_repairs(snapshot, classification) == []
    assert classification["blockers"][0]["code"] == ("broker_order_exposure_disagreement")


def test_degraded_team_role_blocks_false_green_critic() -> None:
    snapshot = _healthy_snapshot()
    snapshot["hedge_fund_team"].update(
        {
            "status": "degraded",
            "healthy_required_role_count": 3,
            "blockers": ["team_role_degraded:frontier_strategy_lead"],
        }
    )

    classification = classify_reliability_snapshot(snapshot)

    assert classification["healthy"] is False
    assert classification["blockers"][0]["code"] == "hedge_fund_team_role_degraded"
    assert classification["state"] == "pipeline_degraded_repairable"
    assert plan_safe_repairs(snapshot, classification) == []


def test_build_mismatch_restarts_reviewed_singleton_owner() -> None:
    snapshot = _healthy_snapshot()
    snapshot["operator"]["running_build_matches_current"] = False

    classification = classify_reliability_snapshot(snapshot)
    actions = plan_safe_repairs(snapshot, classification)

    assert classification["state"] == "pipeline_degraded_repairable"
    assert actions == [
        {
            "action_type": "restart_operator_owner",
            "service_id": None,
            "trigger_code": "operator_build_mismatch",
            "trigger_codes": ["operator_build_mismatch"],
        }
    ]


def test_one_degraded_service_does_not_replay_unrelated_pipeline() -> None:
    snapshot = _healthy_snapshot()
    snapshot["hedge_fund_team"]["trading_pipeline"] = {
        "status": "degraded",
        "healthy_stage_count": 9,
        "stage_count": 10,
        "stages": [
            {
                "stage": 5,
                "degraded_services": ["active_discovery_trial"],
            }
        ],
    }
    snapshot["operator"].update(
        {
            "stale_service_count": 1,
            "services": {
                "active_discovery_trial": {"freshness": {"state": "stale"}}
            },
        }
    )

    classification = classify_reliability_snapshot(snapshot)
    actions = plan_safe_repairs(snapshot, classification)

    assert len(actions) == 1
    assert actions[0]["action_type"] == "request_operator_full_heal"
    assert actions[0]["service_ids"] == ["active_discovery_trial"]


def test_legacy_projection_staleness_does_not_override_healthy_service_truth() -> None:
    snapshot = _healthy_snapshot()
    snapshot["self_healing"]["stale_or_missing_artifact_count"] = 99

    classification = classify_reliability_snapshot(snapshot)

    assert classification["healthy"] is True
    assert plan_safe_repairs(snapshot, classification) == []


def test_degraded_pipeline_does_not_claim_a_healthy_team_role_failed() -> None:
    snapshot = _healthy_snapshot()
    snapshot["hedge_fund_team"].update(
        {
            "status": "degraded",
            "trading_pipeline": {
                "status": "degraded",
                "healthy_stage_count": 9,
                "stage_count": 10,
                "stages": [
                    {
                        "stage": 8,
                        "degraded_services": ["guarded_paperops"],
                    }
                ],
            },
        }
    )

    classification = classify_reliability_snapshot(snapshot)

    codes = [blocker["code"] for blocker in classification["blockers"]]
    assert "hedge_fund_team_role_degraded" not in codes
    assert "trading_pipeline_service_degraded" in codes


def test_stale_mirror_only_reconciliation_requests_verified_full_heal() -> None:
    snapshot = _healthy_snapshot()
    snapshot["control_plane"]["latest_reconciliation"] = {
        "status": "blocked",
        "blocker_count": 1,
        "blockers": ["paper_account_mirror_stale"],
    }

    classification = classify_reliability_snapshot(snapshot)
    actions = plan_safe_repairs(snapshot, classification)

    reconciliation = next(
        blocker
        for blocker in classification["blockers"]
        if blocker["code"] == "canonical_reconciliation_failed"
    )
    assert reconciliation["safe_auto_repair_allowed"] is True
    assert actions[0]["action_type"] == "request_operator_full_heal"
    assert "guarded_paperops" in actions[0]["service_ids"]


def test_corrected_code_identity_can_revalidate_an_old_code_defect() -> None:
    snapshot = _healthy_snapshot()
    snapshot["circuits"] = {
        "open_circuit_count": 1,
        "services": {
            "open_market_conversion": {
                "state": "open",
                "failure_class": "code_defect",
                "failure_revalidation_identity": "old-build-identity",
            }
        },
    }

    classification = classify_reliability_snapshot(snapshot)
    actions = plan_safe_repairs(snapshot, classification)

    circuit = next(
        blocker
        for blocker in classification["blockers"]
        if blocker["code"] == "operator_service_circuit_open"
    )
    assert circuit["safe_auto_repair_allowed"] is True
    assert actions[0]["action_type"] == "request_operator_full_heal"
    assert "open_market_conversion" in actions[0]["service_ids"]


def test_safe_transient_circuits_are_delegated_to_singleton_full_heal() -> None:
    snapshot = _healthy_snapshot()
    snapshot["circuits"] = {
        "open_circuit_count": 2,
        "services": {
            "dashboard_refresh": {
                "state": "open",
                "failure_class": "transient_provider_network",
            },
            "guarded_paperops": {
                "state": "open",
                "failure_class": "transient_provider_network",
            },
        },
    }
    classification = classify_reliability_snapshot(snapshot)
    actions = plan_safe_repairs(snapshot, classification)

    assert classification["state"] == "pipeline_degraded_repairable"
    assert len(actions) == 1
    assert actions[0]["action_type"] == "request_operator_full_heal"
    assert "dashboard_refresh" in actions[0]["service_ids"]
    assert "guarded_paperops" in actions[0]["service_ids"]


def test_bounded_historical_worker_joins_safe_full_heal() -> None:
    snapshot = _healthy_snapshot()
    snapshot["hedge_fund_team"]["trading_pipeline"] = {
        "status": "degraded",
        "healthy_stage_count": 9,
        "stage_count": 10,
        "stages": [
            {
                "stage": 1,
                "degraded_services": [
                    "historical_source_worker",
                    "source_ingestion",
                ],
            }
        ],
    }
    snapshot["operator"].update(
        {
            "stale_service_count": 2,
            "services": {
                "historical_source_worker": {"freshness": {"state": "stale"}},
                "source_ingestion": {"freshness": {"state": "stale"}},
            },
        }
    )
    classification = classify_reliability_snapshot(snapshot)

    actions = plan_safe_repairs(snapshot, classification)

    assert classification["state"] == "pipeline_degraded_repairable"
    assert len(actions) == 1
    assert actions[0]["action_type"] == "request_operator_full_heal"
    assert "source_ingestion" in actions[0]["service_ids"]
    assert "historical_source_worker" in actions[0]["service_ids"]


def test_bounded_challenger_failure_can_no_longer_be_detected_without_recovery() -> None:
    snapshot = _healthy_snapshot()
    snapshot["hedge_fund_team"]["trading_pipeline"] = {
        "status": "degraded",
        "healthy_stage_count": 9,
        "stage_count": 10,
        "stages": [
            {
                "stage": 5,
                "degraded_services": ["challenger_research"],
            }
        ],
    }
    snapshot["operator"].update(
        {
            "stale_service_count": 1,
            "services": {
                "challenger_research": {"freshness": {"state": "stale"}},
            },
        }
    )

    classification = classify_reliability_snapshot(snapshot)
    actions = plan_safe_repairs(snapshot, classification)

    assert classification["state"] == "pipeline_degraded_repairable"
    assert len(actions) == 1
    assert actions[0]["action_type"] == "request_operator_full_heal"
    assert "challenger_research" in actions[0]["service_ids"]


def test_unsafe_paperops_circuit_requires_review_and_cannot_auto_heal() -> None:
    snapshot = _healthy_snapshot()
    snapshot["circuits"] = {
        "open_circuit_count": 1,
        "services": {
            "guarded_paperops": {
                "state": "open",
                "failure_class": "safety_violation",
            }
        },
    }

    classification = classify_reliability_snapshot(snapshot)

    assert classification["state"] == "pipeline_degraded_escalation_required"
    assert plan_safe_repairs(snapshot, classification) == []


def test_critic_requires_two_independent_healthy_samples(tmp_path: Path) -> None:
    snapshots = iter([_healthy_snapshot(), _healthy_snapshot()])
    payload, errors = run_reliability_critic(
        _settings(tmp_path),
        repair=False,
        verification_wait_seconds=0,
        snapshot_reader=lambda: next(snapshots),
        sleep_fn=lambda _seconds: None,
    )

    assert errors == []
    assert payload["status"] == "passed"
    assert payload["verification_passed"] is True
    assert payload["consecutive_healthy_verification_count"] == 2
    assert payload["paper_order_created_count"] == 0
    assert payload["broker_write_count"] == 0
    assert (tmp_path / STATUS_ARTIFACT).exists()
    assert (tmp_path / REPAIR_PACKET_ARTIFACT).exists()


def test_repair_mode_can_verify_health_without_requesting_a_full_heal(
    tmp_path: Path,
) -> None:
    snapshots = iter([_healthy_snapshot(), _healthy_snapshot()])
    payload, errors = run_reliability_critic(
        _settings(tmp_path),
        repair=True,
        verification_wait_seconds=0,
        snapshot_reader=lambda: next(snapshots),
        team_cycle_runner=lambda: ({"status": "passed"}, []),
        sleep_fn=lambda _seconds: None,
    )

    assert errors == []
    assert payload["status"] == "passed"
    assert payload["planned_action_count"] == 0
    assert payload["full_heal"]["requested"] is False
    assert payload["full_heal"]["all_scopes_verified"] is True


def test_persisting_failure_writes_deterministic_repair_packet(tmp_path: Path) -> None:
    broken = _healthy_snapshot()
    broken["operator"]["order_exposure_integrity"] = {"status": "blocked"}
    snapshots = iter([broken, broken])
    payload, errors = run_reliability_critic(
        _settings(tmp_path),
        repair=True,
        verification_wait_seconds=0,
        lock_wait_seconds=0,
        snapshot_reader=lambda: next(snapshots),
        team_cycle_runner=lambda: (
            {"status": "passed"},
            [],
        ),
        sleep_fn=lambda _seconds: None,
    )

    packet = __import__("json").loads(
        (tmp_path / REPAIR_PACKET_ARTIFACT).read_text(encoding="utf-8")
    )
    assert errors == []
    assert payload["status"] == "degraded"
    assert packet["status"] == "operator_review_required"
    assert packet["failure_fingerprint"]
    assert payload["planned_action_count"] == 0


def test_validator_rejects_unsafe_action_or_authority() -> None:
    payload = {
        "schema_version": "qadam_reliability_critic.v1",
        "artifact_type": "qadam_reliability_critic_status",
        "status": "degraded",
        "verification_passed": False,
        "consecutive_healthy_verification_count": 0,
        "actions": [
            {
                "action_type": "repair_safe_runtime_circuit",
                "service_id": "guarded_paperops",
            }
        ],
        "paper_order_created_count": 0,
        "broker_write_count": 0,
        "authority": {**_authority(), "broker_write_allowed": True},
    }

    errors = validate_reliability_critic_payload(payload)

    assert "reliability_critic_paper_service_repair_forbidden" in errors
    assert "reliability_critic_unsafe_authority:broker_write_allowed" in errors


def test_validator_allows_guarded_wrapper_only_via_singleton_full_heal_request() -> None:
    payload = {
        "schema_version": "qadam_reliability_critic.v1",
        "artifact_type": "qadam_reliability_critic_status",
        "status": "degraded",
        "verification_passed": False,
        "consecutive_healthy_verification_count": 0,
        "repair_enabled": True,
        "actions": [
            {
                "action_type": "request_operator_full_heal",
                "service_id": None,
                "service_ids": ["dashboard_refresh", "guarded_paperops"],
            }
        ],
        "paper_order_created_count": 0,
        "broker_write_count": 0,
        "authority": _authority(),
    }

    errors = validate_reliability_critic_payload(payload)

    assert "reliability_critic_paper_service_repair_forbidden" not in errors
    assert not any("full_heal_service_forbidden" in error for error in errors)


def test_launchd_schedule_is_bounded_and_cannot_invoke_execution() -> None:
    template = (ROOT / "ops" / "launchd" / "com.qadam.reliability-critic.plist.template").read_text(
        encoding="utf-8"
    )
    payload = plistlib.loads(template.replace("__QADAM_ROOT__", str(ROOT)).encode())
    arguments = [str(item) for item in payload["ProgramArguments"]]

    assert payload["Label"] == "com.qadam.reliability-critic"
    assert payload["StartInterval"] == 3 * 60 * 60
    assert payload["RunAtLoad"] is True
    assert payload["ProcessType"] == "Standard"
    assert "--repair" in arguments
    assert "--force-team-cycle" in arguments
    assert arguments[arguments.index("--operator-heal-wait-seconds") + 1] == "7200"
    assert arguments[arguments.index("--verification-wait-seconds") + 1] == "70"
    assert arguments[arguments.index("--lock-wait-seconds") + 1] == "60"
    assert arguments[3].endswith("scripts/run_qadam_reliability_critic.py")
    assert all("paperops" not in argument.lower() for argument in arguments)
    assert all("open_market_conversion" not in argument for argument in arguments)
    assert payload["EnvironmentVariables"]["QADAM_LIVE_CAPITAL_ENABLED"] == "false"
