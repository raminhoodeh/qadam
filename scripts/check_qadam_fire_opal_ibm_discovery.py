#!/usr/bin/env python3
"""Prepare and verify Wave D without contacting Fire Opal or IBM."""

from __future__ import annotations

import stat
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from orchestrator.config import Settings  # noqa: E402
from orchestrator.qadam_classical_discovery import run_classical_discovery  # noqa: E402
from orchestrator.qadam_discovery_contract_fixture import (  # noqa: E402
    build_wave_c_contract_fixture_batch,
)
from orchestrator.qadam_fire_opal_ibm_discovery import (  # noqa: E402
    FireOpalIbmExperimentStore,
    prepare_fire_opal_ibm_smoke_manifest,
    validate_prepared_manifest,
    validate_private_state,
    validate_public_state,
)
from orchestrator.qadam_local_quantum_discovery import (  # noqa: E402
    QiskitLocalQuantumDiscoveryBackend,
)


def main() -> int:
    settings = Settings.from_env()
    batch = build_wave_c_contract_fixture_batch()
    classical = run_classical_discovery(batch)
    local = QiskitLocalQuantumDiscoveryBackend().run(
        batch,
        mode="ideal",
        matched_classical_result=classical,
    )
    bundle = prepare_fire_opal_ibm_smoke_manifest(
        batch,
        matched_classical_result=classical,
        local_quantum_result=local,
        prepared_at="2026-07-12T00:00:00+00:00",
    )
    store = FireOpalIbmExperimentStore(settings.runtime_dir)
    public_path, private_path = store.write_prepared(bundle)
    public_state = store.read_public(bundle.manifest.manifest_hash)
    private_state = store.read_private(bundle.manifest.manifest_hash)
    validate_prepared_manifest(bundle.manifest.to_public_dict())
    validate_public_state(public_state)
    validate_private_state(
        private_state,
        manifest_hash=bundle.manifest.manifest_hash,
    )

    errors: list[str] = []
    if bundle.manifest.circuit_count != 100:
        errors.append("unexpected_fidelity_circuit_count")
    if bundle.manifest.qubit_count != 6:
        errors.append("unexpected_qubit_count")
    if bundle.manifest.total_shots != 25_600:
        errors.append("unexpected_total_shots")
    if public_state.get("lifecycle_status") != "prepared":
        errors.append("public_state_not_prepared")
    if public_state.get("provider_call_count") != 0:
        errors.append("provider_call_occurred")
    if public_state.get("hardware_execution_authorized") is not False:
        errors.append("hardware_authority_created")
    if public_state.get("hardware_job_submitted") is not False:
        errors.append("hardware_job_submitted")
    if public_state.get("hardware_experiment_completed") is not False:
        errors.append("hardware_experiment_claimed")
    if stat.S_IMODE(private_path.stat().st_mode) != 0o600:
        errors.append("private_state_permissions_invalid")
    if "qasm_circuits" in public_path.read_text(encoding="utf-8"):
        errors.append("qasm_exposed_publicly")

    print(f"fire_opal_ibm_manifest_public_path={public_path}")
    print(f"fire_opal_ibm_manifest_private_path={private_path}")
    print(f"fire_opal_ibm_manifest_hash={bundle.manifest.manifest_hash}")
    print(f"fire_opal_ibm_shared_manifest_hash={bundle.manifest.shared_manifest_hash}")
    print(f"fire_opal_ibm_circuit_count={bundle.manifest.circuit_count}")
    print(f"fire_opal_ibm_qubit_count={bundle.manifest.qubit_count}")
    print(f"fire_opal_ibm_circuit_depth_max={bundle.manifest.circuit_depth_max}")
    print(f"fire_opal_ibm_shots_per_circuit={bundle.manifest.shots_per_circuit}")
    print(f"fire_opal_ibm_total_shots={bundle.manifest.total_shots}")
    print(f"fire_opal_ibm_local_qasm_validation={bundle.manifest.local_qasm_validation_passed}")
    print(f"fire_opal_ibm_provider_call_count={public_state.get('provider_call_count')}")
    print(
        "fire_opal_ibm_hardware_execution_authorized="
        f"{public_state.get('hardware_execution_authorized')}"
    )
    print(f"fire_opal_ibm_hardware_job_submitted={public_state.get('hardware_job_submitted')}")
    print(
        "fire_opal_ibm_hardware_experiment_completed="
        f"{public_state.get('hardware_experiment_completed')}"
    )
    print(f"fire_opal_ibm_private_mode={oct(stat.S_IMODE(private_path.stat().st_mode))}")
    print(f"fire_opal_ibm_errors={errors}")
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
