from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace

import pytest

from orchestrator.config import Settings
import orchestrator.quantum as quantum


def _settings(tmp_path: Path) -> Settings:
    return replace(Settings.from_env(), runtime_dir=str(tmp_path))


def _mock_ready_local_contract(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        quantum,
        "qctrl_readiness",
        lambda _settings: {
            "credential_configured": True,
            "sdk_package_importable": True,
        },
    )

    def read_runtime(_settings: Settings, filename: str):
        if filename == "paper_live_qctrl_product_access.json":
            return {
                "status": "qctrl_paper_consultation_ready",
                "product_access_verified": True,
                "paper_consultation_ready": True,
                "provider_call_succeeded": True,
                "qctrl_auth_status": "authenticated",
            }
        return {}

    monkeypatch.setattr(quantum, "_read_runtime_json", read_runtime)
    monkeypatch.setattr(
        quantum,
        "secret_status",
        lambda _name, _settings: SimpleNamespace(configured=True),
    )
    monkeypatch.setattr(quantum, "_optional_module_available", lambda _module: True)
    monkeypatch.setattr(quantum, "_fire_opal_organization_slug", lambda _settings: "qadam")


def _fake_fire_opal() -> SimpleNamespace:
    return SimpleNamespace(
        configure_organization=lambda _slug: None,
        authenticate_qctrl_account=lambda **_kwargs: None,
        credentials=SimpleNamespace(
            make_credentials_for_ibm_cloud=lambda **_kwargs: {"provider": "ibm"}
        ),
    )


def test_provider_truth_separates_configuration_from_authenticated_backend(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    _mock_ready_local_contract(monkeypatch)

    readiness = quantum.qctrl_fire_opal_ibm_readiness(_settings(tmp_path))

    quantum.validate_qctrl_fire_opal_ibm_readiness(readiness)
    assert readiness["status"] == "ready_for_explicit_device_probe"
    assert readiness["credentials_configured"] is True
    assert readiness["qctrl_authenticated"] is True
    assert readiness["ibm_authenticated"] is False
    assert readiness["authenticated"] is False
    assert readiness["product_entitled"] is True
    assert readiness["backend_discovered"] is False
    assert readiness["circuit_validation_available"] is False
    assert readiness["hardware_execution_authorized"] is False
    assert readiness["hardware_experiment_completed"] is False
    assert readiness["provider_call_attempted"] is False


def test_private_probe_state_is_mode_0600_and_round_trips(tmp_path: Path):
    settings = _settings(tmp_path)

    path = quantum._write_fire_opal_ibm_probe_private(settings, "action-private-123")
    payload = quantum._read_fire_opal_ibm_probe_private(settings)

    assert path.stat().st_mode & 0o777 == 0o600
    assert payload["action_id"] == "action-private-123"
    assert payload["action_id_hash"] != payload["action_id"]

    quantum._clear_fire_opal_ibm_probe_private(settings)
    assert not path.exists()


def test_poll_existing_probe_records_supported_backend_without_resubmission(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    _mock_ready_local_contract(monkeypatch)
    settings = _settings(tmp_path)
    quantum._write_fire_opal_ibm_probe_private(settings, "existing-action")

    monkeypatch.setattr(
        quantum,
        "_ibm_runtime_account_preflight",
        lambda _settings: {
            "attempted": True,
            "succeeded": True,
            "failure_category": None,
            "failure_class": None,
            "http_status_code": None,
            "failure_message_hash": None,
            "backend_count": 2,
            "backend_name_hashes": ["runtime-a", "runtime-b"],
        },
    )
    monkeypatch.setattr(
        quantum,
        "_import_fireopal_without_update_check",
        _fake_fire_opal,
    )
    monkeypatch.setattr(quantum, "secret_value", lambda _name, _settings: "configured")
    monkeypatch.setattr(
        quantum,
        "_poll_fire_opal_supported_devices_result",
        lambda _action_id: (
            {"supported_devices": [{"name": "ibm_test_backend"}]},
            "SUCCESS",
        ),
    )
    monkeypatch.setattr(
        quantum,
        "_submit_fire_opal_supported_devices_async",
        lambda _credentials: pytest.fail("polling must not submit a second probe"),
    )

    readiness = quantum.qctrl_fire_opal_ibm_readiness(
        settings,
        poll_devices=True,
    )

    quantum.validate_qctrl_fire_opal_ibm_readiness(readiness)
    assert readiness["status"] == "device_probe_recorded"
    assert readiness["provider_operation"] == "poll_existing_device_probe"
    assert readiness["authenticated"] is True
    assert readiness["backend_discovery_completed"] is True
    assert readiness["backend_discovered"] is True
    assert readiness["supported_device_count"] == 1
    assert readiness["circuit_validation_available"] is True
    assert readiness["hardware_execution_authorized"] is False
    assert readiness["hardware_experiment_completed"] is False
    assert "action_id" not in readiness
    assert not quantum._fire_opal_ibm_probe_private_path(settings).exists()


def test_completed_probe_with_no_devices_reports_precise_blocker(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    _mock_ready_local_contract(monkeypatch)
    settings = _settings(tmp_path)
    quantum._write_fire_opal_ibm_probe_private(settings, "empty-action")

    monkeypatch.setattr(
        quantum,
        "_ibm_runtime_account_preflight",
        lambda _settings: {
            "attempted": True,
            "succeeded": True,
            "failure_category": None,
            "failure_class": None,
            "http_status_code": None,
            "failure_message_hash": None,
            "backend_count": 1,
            "backend_name_hashes": ["runtime-a"],
        },
    )
    monkeypatch.setattr(
        quantum,
        "_import_fireopal_without_update_check",
        _fake_fire_opal,
    )
    monkeypatch.setattr(quantum, "secret_value", lambda _name, _settings: "configured")
    monkeypatch.setattr(
        quantum,
        "_poll_fire_opal_supported_devices_result",
        lambda _action_id: ({"supported_devices": []}, "SUCCESS"),
    )

    readiness = quantum.qctrl_fire_opal_ibm_readiness(
        settings,
        poll_devices=True,
    )

    quantum.validate_qctrl_fire_opal_ibm_readiness(readiness)
    assert readiness["status"] == "blocked_no_supported_devices"
    assert readiness["blocker"] == "no_supported_fire_opal_ibm_devices_discovered"
    assert readiness["backend_discovery_completed"] is True
    assert readiness["backend_discovered"] is False
    assert readiness["circuit_validation_available"] is False


def test_provider_truth_rejects_hardware_authority_escalation(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    _mock_ready_local_contract(monkeypatch)
    readiness = quantum.qctrl_fire_opal_ibm_readiness(_settings(tmp_path))
    readiness["hardware_execution_authorized"] = True
    readiness["provider_truth"]["hardware_execution_authorized"] = True

    with pytest.raises(ValueError, match="hardware_execution_authorized"):
        quantum.validate_qctrl_fire_opal_ibm_readiness(readiness)


def test_ibm_token_instance_mismatch_has_precise_public_category():
    error = RuntimeError(
        "The given API token is associated with an account that does not have "
        "access to the instance configured-for-test."
    )

    assert (
        quantum._provider_failure_category(error)
        == "ibm_token_instance_access_mismatch"
    )


def test_ibm_preflight_failure_persists_across_readiness_refresh(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    _mock_ready_local_contract(monkeypatch)
    settings = _settings(tmp_path)
    runtime_payloads: dict[str, dict] = {}

    def read_runtime(_settings: Settings, filename: str):
        if filename == "paper_live_qctrl_product_access.json":
            return {
                "status": "qctrl_paper_consultation_ready",
                "product_access_verified": True,
                "paper_consultation_ready": True,
                "provider_call_succeeded": True,
                "qctrl_auth_status": "authenticated",
            }
        return runtime_payloads.get(filename, {})

    monkeypatch.setattr(quantum, "_read_runtime_json", read_runtime)
    monkeypatch.setattr(
        quantum,
        "_ibm_runtime_account_preflight",
        lambda _settings: {
            "attempted": True,
            "succeeded": False,
            "failure_category": "ibm_token_instance_access_mismatch",
            "failure_class": "IBMInputValueError",
            "http_status_code": None,
            "failure_message_hash": "sanitized-message-hash",
            "backend_count": 0,
            "backend_name_hashes": [],
            "configured_instance_accessible": False,
            "accessible_instance_discovery_succeeded": False,
            "accessible_instance_count": 0,
            "accessible_instance_hashes": [],
        },
    )

    probed = quantum.qctrl_fire_opal_ibm_readiness(settings, probe_devices=True)
    runtime_payloads[quantum.QCTRL_FIRE_OPAL_IBM_READINESS_RUNTIME_ARTIFACT] = probed
    refreshed = quantum.qctrl_fire_opal_ibm_readiness(settings)

    assert probed["status"] == "blocked_provider_probe_failed"
    assert probed["blocker"] == "ibm_token_instance_access_mismatch"
    assert probed["ibm_runtime_preflight_attempted"] is True
    assert probed["provider_call_attempted"] is False
    assert refreshed == probed
