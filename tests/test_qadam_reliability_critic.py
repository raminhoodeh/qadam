from __future__ import annotations

from dataclasses import replace
from pathlib import Path
import plistlib

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
        "paperops": {
            "present": True,
            "age_seconds": 100.0,
            "status": "ready_idle",
            "blockers": [],
            "canonical_control_status": "canonical_paper_control_ready",
            "canonical_control_blockers": [],
            "fresh_eligible_submit_count": fresh_eligible,
            "accepted_handoff_count": accepted_handoffs,
        },
        "router": {
            "status": "not_trading",
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


def test_stopped_reviewed_operator_plans_only_owner_restart() -> None:
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
    assert actions == [
        {
            "action_type": "restart_operator_owner",
            "service_id": None,
            "trigger_code": "operator_owner_not_running",
        }
    ]


def test_broker_disagreement_escalates_without_auto_repair() -> None:
    snapshot = _healthy_snapshot()
    snapshot["operator"]["order_exposure_integrity"] = {
        "status": "blocked_duplicate_exposure"
    }
    classification = classify_reliability_snapshot(snapshot)

    assert classification["state"] == "pipeline_degraded_escalation_required"
    assert plan_safe_repairs(snapshot, classification) == []
    assert classification["blockers"][0]["code"] == (
        "broker_order_exposure_disagreement"
    )


def test_safe_circuit_can_revalidate_but_paperops_cannot() -> None:
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

    assert classification["state"] == "pipeline_degraded_escalation_required"
    assert actions == [
        {
            "action_type": "repair_safe_runtime_circuit",
            "service_id": "dashboard_refresh",
            "trigger_code": "operator_service_circuit_open",
        }
    ]


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


def test_launchd_schedule_is_bounded_and_cannot_invoke_execution() -> None:
    template = (
        ROOT / "ops" / "launchd" / "com.qadam.reliability-critic.plist.template"
    ).read_text(encoding="utf-8")
    payload = plistlib.loads(template.replace("__QADAM_ROOT__", str(ROOT)).encode())
    arguments = [str(item) for item in payload["ProgramArguments"]]

    assert payload["Label"] == "com.qadam.reliability-critic"
    assert payload["StartInterval"] == 3 * 60 * 60
    assert payload["RunAtLoad"] is True
    assert arguments[-5:] == [
        "--repair",
        "--verification-wait-seconds",
        "70",
        "--lock-wait-seconds",
        "60",
    ]
    assert arguments[3].endswith("scripts/run_qadam_reliability_critic.py")
    assert all("paperops" not in argument.lower() for argument in arguments)
    assert all("open_market_conversion" not in argument for argument in arguments)
    assert payload["EnvironmentVariables"]["QADAM_LIVE_CAPITAL_ENABLED"] == "false"
