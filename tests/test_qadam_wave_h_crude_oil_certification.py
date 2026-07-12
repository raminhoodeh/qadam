from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path

import pytest

from orchestrator.qadam_wave_h_crude_oil_certification import (
    PUBLIC_PROOF_STATES,
    _stable_hash,
    build_crude_oil_pilot_manifest,
    build_current_wave_h_certification,
    classify_public_proof_state,
    validate_wave_h_payload,
    write_wave_h_certification,
)


ROOT = Path(__file__).resolve().parents[1]


def _rehash(payload: dict) -> None:
    material = {
        key: value
        for key, value in payload.items()
        if key not in {"generated_at", "content_hash"}
    }
    payload["content_hash"] = _stable_hash(material)


@pytest.fixture(scope="module")
def certification() -> dict:
    return build_current_wave_h_certification(
        generated_at="2026-07-12T16:00:00+00:00"
    )


def test_current_wave_h_certifies_mechanism_without_claiming_edge(certification):
    assert certification["status"] == "mechanism_certified_result_unproven"
    assert certification["mechanism_certified"] is True
    assert certification["scientific_result_certified"] is False
    assert certification["scientific_verdict"] == "not_measurable"
    assert certification["public_proof_state"] == "unproven"
    assert certification["certification"]["engineering_pass_count"] == 11
    assert certification["certification"]["engineering_check_count"] == 11
    assert certification["certification"]["scientific_pass_count"] == 0
    assert certification["certification"]["scientific_check_count"] == 6


def test_current_wave_h_preserves_empirical_and_hardware_truth(certification):
    evidence = certification["evidence_truth"]
    hardware = certification["hardware_authorization_checkpoint"]
    fixture = certification["engineering_fixture"]
    assert evidence["classified_window_count"] >= evidence["eligible_window_count"]
    assert evidence["eligible_window_count"] == 0
    assert evidence["provider_row_count"] == 0
    assert evidence["leakage_violation_count"] == 0
    assert hardware["authorized"] is False
    assert hardware["provider_blocker"] in {
        "ibm_token_instance_access_mismatch",
        "provider_readiness_not_exported",
    }
    assert fixture["provider_call_count"] == 0
    assert fixture["hardware_job_submitted"] is False
    assert fixture["hardware_experiment_completed"] is False


def test_current_wave_h_creates_no_downstream_authority(certification):
    assert set(certification["authority"].values()) == {False}
    assert set(certification["downstream_truth"].values()) == {0}
    assert certification["expansion"]["allowed"] is False
    assert validate_wave_h_payload(certification) == []


def test_crude_oil_manifest_is_deterministic_and_complete():
    first = build_crude_oil_pilot_manifest(
        engineering_hardware_manifest_hash="fixture-hardware-manifest"
    )
    second = build_crude_oil_pilot_manifest(
        engineering_hardware_manifest_hash="fixture-hardware-manifest"
    )
    assert first == second
    assert first["manifest_hash"] == second["manifest_hash"]
    assert first["paper_targets"] == ["BNO", "USO"]
    assert len(first["point_in_time_features"]) == 8
    assert {row["key"] for row in first["point_in_time_features"]} == {
        "conflict_event_acceleration",
        "tanker_chokepoint_disruption",
        "port_congestion",
        "inventory_surprise",
        "weather_fire_disruption",
        "futures_curve_structure",
        "realized_volatility",
        "muted_or_divergent_price_response",
    }
    assert first["chronology"]["labels_visible_during_discovery"] is False
    assert first["hardware_submission_authorized"] is False


def test_public_proof_classifier_exposes_all_five_states():
    observed = {
        classify_public_proof_state(
            scientific_verdict="not_measurable",
            empirical_measured=False,
            hardware_completed=False,
            controls_passed=False,
        ),
        classify_public_proof_state(
            scientific_verdict="quantum_strengthened",
            empirical_measured=True,
            hardware_completed=False,
            controls_passed=True,
        ),
        classify_public_proof_state(
            scientific_verdict="quantum_strengthened",
            empirical_measured=True,
            hardware_completed=True,
            controls_passed=True,
        ),
        classify_public_proof_state(
            scientific_verdict="classical_preferred",
            empirical_measured=True,
            hardware_completed=True,
            controls_passed=True,
        ),
        classify_public_proof_state(
            scientific_verdict="quantum_strengthened",
            empirical_measured=True,
            hardware_completed=True,
            controls_passed=True,
            edge_decay_detected=True,
        ),
    }
    assert observed == set(PUBLIC_PROOF_STATES)


def test_validator_rejects_authority_escalation(certification):
    tampered = deepcopy(certification)
    tampered["authority"]["hardware_submission_allowed"] = True
    _rehash(tampered)
    errors = validate_wave_h_payload(tampered)
    assert "wave_h_authority_escalated:hardware_submission_allowed" in errors
    assert "wave_h_unrecognized_true_authority" in errors


def test_validator_rejects_fixture_promotion(certification):
    tampered = deepcopy(certification)
    tampered["public_proof_state"] = "validated"
    _rehash(tampered)
    assert "wave_h_fixture_promoted_to_edge" in validate_wave_h_payload(tampered)


def test_validator_rejects_unproven_downstream_promotion(certification):
    tampered = deepcopy(certification)
    tampered["downstream_truth"]["strategy_count"] = 1
    _rehash(tampered)
    assert "wave_h_unproven_result_reached_downstream" in validate_wave_h_payload(
        tampered
    )


def test_validator_rejects_secret_like_public_material(certification):
    tampered = deepcopy(certification)
    tampered["pilot_manifest"]["token"] = "ghp_abcdefghijklmnopqrstuvwxyz123456"
    _rehash(tampered)
    errors = validate_wave_h_payload(tampered)
    assert any(error.startswith("forbidden_public_key:") for error in errors)
    assert any(error.startswith("secret_like_value:") for error in errors)


def test_certification_writes_matching_runtime_and_site_artifacts(
    certification,
    tmp_path,
):
    runtime_dir = tmp_path / "runtime"
    site_root = tmp_path / "site"
    paths = write_wave_h_certification(
        certification,
        runtime_dir=runtime_dir,
        site_root=site_root,
    )
    runtime_payload = json.loads(paths["runtime"].read_text(encoding="utf-8"))
    site_payload = json.loads(paths["site"].read_text(encoding="utf-8"))
    assert runtime_payload == site_payload == certification


def test_wave_h_module_has_no_direct_broker_or_provider_client_import():
    source = (ROOT / "orchestrator/qadam_wave_h_crude_oil_certification.py").read_text(
        encoding="utf-8"
    )
    assert "paperops_alpaca_paper_post" not in source
    assert "requests." not in source
    assert "httpx." not in source
    assert "qiskit_ibm_runtime" not in source
    assert "fireopal" not in source.lower()
