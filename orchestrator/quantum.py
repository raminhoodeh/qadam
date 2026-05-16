"""Quantum provider registry.

Phase 0 does not submit quantum jobs. It only exposes provider readiness and
credential state so the future Head of Quant can be wired deliberately.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass

from orchestrator.config import Settings
from orchestrator.secrets import secret_status


@dataclass(frozen=True)
class QuantumProvider:
    key: str
    name: str
    role: str
    status: str
    credential_key: str | None
    credential_configured: bool
    notes: str

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


def quantum_providers(settings: Settings | None = None) -> list[dict[str, object]]:
    settings = settings or Settings.from_env()
    qctrl = secret_status("QCTRL_API_KEY", settings)
    ibm = secret_status("IBM_QUANTUM_TOKEN", settings)
    aws_key = secret_status("AWS_ACCESS_KEY_ID", settings)

    providers = [
        QuantumProvider(
            key="qiskit_aer",
            name="Qiskit Aer Local Simulator",
            role="local_simulation",
            status="available_without_secret",
            credential_key=None,
            credential_configured=True,
            notes="Foundation-safe local simulator path for validating circuits before hardware.",
        ),
        QuantumProvider(
            key="qctrl",
            name="Q-CTRL",
            role="future_error_suppression_and_optimization",
            status="configured" if qctrl.configured else "missing_secret",
            credential_key="QCTRL_API_KEY",
            credential_configured=qctrl.configured,
            notes="Credential is stored locally. No Q-CTRL API calls are part of Phase 0.",
        ),
        QuantumProvider(
            key="ibm_quantum",
            name="IBM Quantum / Qiskit Runtime",
            role="future_hardware_backend",
            status="configured" if ibm.configured else "missing_secret",
            credential_key="IBM_QUANTUM_TOKEN",
            credential_configured=ibm.configured,
            notes="Planned primary hardware backend after local circuit validation.",
        ),
        QuantumProvider(
            key="aws_braket",
            name="AWS Braket",
            role="future_secondary_hardware_backend",
            status="configured" if aws_key.configured else "missing_secret",
            credential_key="AWS_ACCESS_KEY_ID",
            credential_configured=aws_key.configured,
            notes="Optional secondary backend; requires AWS credential/profile setup later.",
        ),
    ]
    return [provider.to_dict() for provider in providers]
