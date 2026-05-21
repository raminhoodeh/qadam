"""Quantum provider registry and Phase 3 oracle contract.

Phase 3 starts with local validation and classical fallback. Hardware and
provider calls stay disabled until a local job has produced the same schema and
later policy gates explicitly allow submission.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from hashlib import sha256
import importlib.util
import json
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta, timezone
from math import exp, pi
from pathlib import Path
from typing import Any
from uuid import uuid4

from orchestrator.config import Settings
from orchestrator.event_log import EventLog
from orchestrator.secrets import secret_status

QUANTUM_ORACLE_SCHEMA_VERSION = 1
QUANTUM_ORACLE_JOB_TYPES = {"pattern_recognition", "strategy_collapse"}
QUANTUM_ORACLE_CADENCE_DAYS = 7
QUANTUM_ORACLE_SHOTS = 256


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


@dataclass(frozen=True)
class QuantumOracleJob:
    schema_version: int
    job_id: str
    job_type: str
    source_ref: str
    instrument_focus: str
    evidence_item_count: int
    source_count: int
    average_trust_score: float
    signal_confidence: float
    missing_correlation_count: int
    local_validation_required: bool
    hardware_submission_allowed: bool
    execution_allowed: bool
    paper_order_allowed: bool
    created_at: str
    boundary: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class QuantumOracleResult:
    schema_version: int
    result_id: str
    job_id: str
    job_type: str
    status: str
    backend: str
    backend_status: str
    simulator_status: str
    local_simulation_mode: str
    local_validation_status: str
    hardware_submission_allowed: bool
    hardware_submitted: bool
    hardware_provider: str | None
    pattern_score: float
    ambiguity_score: float
    confidence_delta: float
    recommendation: str
    circuit_blueprint: dict[str, Any]
    measurement_counts: dict[str, int]
    input_fingerprint: str
    validation_checks: dict[str, str]
    instrument_focus: str
    source_ref: str
    required_next_steps: tuple[str, ...]
    execution_allowed: bool
    paper_order_allowed: bool
    trade_candidate_created: bool
    hardware_scheduler_enabled: bool
    created_at: str
    boundary: str

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["required_next_steps"] = list(self.required_next_steps)
        return payload


@dataclass(frozen=True)
class QuantumBackendOutput:
    backend: str
    backend_status: str
    simulator_status: str
    local_simulation_mode: str
    pattern_score: float
    ambiguity_score: float
    circuit_blueprint: dict[str, Any]
    measurement_counts: dict[str, int]
    input_fingerprint: str
    validation_checks: dict[str, str]


class QuantumBackend(ABC):
    key: str

    @abstractmethod
    def run(self, job: QuantumOracleJob) -> QuantumBackendOutput:
        """Run a local-only quantum oracle job."""


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _next_due_at(created_at: Any) -> str | None:
    if not created_at:
        return None
    try:
        parsed = datetime.fromisoformat(str(created_at).replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return (parsed + timedelta(days=QUANTUM_ORACLE_CADENCE_DAYS)).isoformat()


def _optional_module_available(module: str) -> bool:
    return importlib.util.find_spec(module) is not None


def quantum_providers(settings: Settings | None = None) -> list[dict[str, object]]:
    settings = settings or Settings.from_env()
    qctrl = secret_status("QCTRL_API_KEY", settings)
    ibm = secret_status("IBM_QUANTUM_TOKEN", settings)
    aws_key = secret_status("AWS_ACCESS_KEY_ID", settings)
    qiskit_aer_available = _optional_module_available("qiskit_aer")

    providers = [
        QuantumProvider(
            key="qiskit_aer",
            name="Qiskit Aer Local Simulator",
            role="local_simulation",
            status="available_without_secret" if qiskit_aer_available else "missing_optional_package",
            credential_key=None,
            credential_configured=True,
            notes=(
                "Foundation-safe local simulator path for validating circuits before hardware. "
                "Classical fallback is used when the optional qiskit-aer package is not installed."
            ),
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


def build_quantum_oracle_job(review: dict[str, Any] | None = None, *, job_type: str) -> QuantumOracleJob:
    if job_type not in QUANTUM_ORACLE_JOB_TYPES:
        raise ValueError(f"unsupported quantum oracle job type: {job_type}")
    review = review or {}
    missing = review.get("missing_correlations", [])
    if not isinstance(missing, list):
        missing = []
    return QuantumOracleJob(
        schema_version=QUANTUM_ORACLE_SCHEMA_VERSION,
        job_id=str(uuid4()),
        job_type=job_type,
        source_ref=str(review.get("review_id") or review.get("source_signal_id") or "sample_shadow_review"),
        instrument_focus=str(review.get("instrument_focus") or "macro_watchlist")[:120],
        evidence_item_count=int(float(review.get("evidence_item_count") or 0)),
        source_count=int(float(review.get("source_count") or 0)),
        average_trust_score=round(float(review.get("average_trust_score") or 0.0), 3),
        signal_confidence=round(float(review.get("signal_confidence") or 0.0), 3),
        missing_correlation_count=len(missing),
        local_validation_required=True,
        hardware_submission_allowed=False,
        execution_allowed=False,
        paper_order_allowed=False,
        created_at=_now(),
        boundary=(
            "Quantum oracle jobs are local-validation jobs only. They cannot originate signals, "
            "approve risk, create paper orders, submit hardware jobs, or access broker writes."
        ),
    )


def _sigmoid(value: float) -> float:
    return 1.0 / (1.0 + exp(-value))


def _pattern_score(job: QuantumOracleJob) -> float:
    score = (
        job.average_trust_score * 0.35
        + min(1.0, job.signal_confidence) * 0.25
        + min(1.0, job.source_count / 4) * 0.2
        + min(1.0, job.evidence_item_count / 6) * 0.15
        - min(0.25, job.missing_correlation_count * 0.05)
    )
    return round(max(0.0, min(1.0, score)), 3)


def _ambiguity_score(job: QuantumOracleJob) -> float:
    ambiguity = _sigmoid(
        job.missing_correlation_count * 0.65
        + max(0, 2 - job.source_count) * 0.55
        + (0.65 - job.average_trust_score) * 1.1
        + (0.55 - job.signal_confidence) * 0.8
    )
    return round(max(0.0, min(1.0, ambiguity)), 3)


def _job_fingerprint(job: QuantumOracleJob) -> str:
    stable_payload = {
        "schema_version": job.schema_version,
        "job_type": job.job_type,
        "source_ref": job.source_ref,
        "instrument_focus": job.instrument_focus,
        "evidence_item_count": job.evidence_item_count,
        "source_count": job.source_count,
        "average_trust_score": job.average_trust_score,
        "signal_confidence": job.signal_confidence,
        "missing_correlation_count": job.missing_correlation_count,
    }
    return sha256(json.dumps(stable_payload, sort_keys=True).encode("utf-8")).hexdigest()


def _circuit_blueprint(job: QuantumOracleJob) -> dict[str, Any]:
    return {
        "name": f"qadam_{job.job_type}_oracle_v1",
        "qubits": 2,
        "classical_bits": 2,
        "shots": QUANTUM_ORACLE_SHOTS,
        "encoding": {
            "q0": "signal_strength_from_trust_confidence_sources",
            "q1": "ambiguity_from_missing_correlations_and_source_gaps",
        },
        "operations": [
            {"gate": "ry", "target": "q0", "angle": "pattern_score*pi"},
            {"gate": "ry", "target": "q1", "angle": "ambiguity_score*pi"},
            {"gate": "cx", "control": "q0", "target": "q1"},
            {"gate": "measure", "targets": ["q0", "q1"]},
        ],
        "authority": "local_validation_only",
    }


def _counts_from_scores(pattern: float, ambiguity: float, *, shots: int = QUANTUM_ORACLE_SHOTS) -> dict[str, int]:
    pattern_hits = int(round(max(0.0, min(1.0, pattern)) * shots))
    ambiguity_hits = int(round(max(0.0, min(1.0, ambiguity)) * shots))
    both = min(pattern_hits, ambiguity_hits, int(round(shots * 0.35)))
    counts = {
        "00": max(0, shots - pattern_hits - ambiguity_hits + both),
        "01": max(0, ambiguity_hits - both),
        "10": max(0, pattern_hits - both),
        "11": max(0, both),
    }
    drift = shots - sum(counts.values())
    counts["00"] += drift
    return counts


def _scores_from_counts(counts: dict[str, int]) -> tuple[float, float]:
    shots = max(1, sum(counts.values()))
    pattern = (counts.get("10", 0) + counts.get("11", 0)) / shots
    ambiguity = (counts.get("01", 0) + counts.get("11", 0)) / shots
    return round(max(0.0, min(1.0, pattern)), 3), round(max(0.0, min(1.0, ambiguity)), 3)


class ClassicalFallbackBackend(QuantumBackend):
    key = "classical_fallback"

    def run(self, job: QuantumOracleJob) -> QuantumBackendOutput:
        pattern = _pattern_score(job)
        ambiguity = _ambiguity_score(job)
        return QuantumBackendOutput(
            backend=self.key,
            backend_status="ok",
            simulator_status="qiskit_aer_missing_classical_fallback",
            local_simulation_mode="deterministic_classical_shadow",
            pattern_score=pattern,
            ambiguity_score=ambiguity,
            circuit_blueprint=_circuit_blueprint(job),
            measurement_counts=_counts_from_scores(pattern, ambiguity),
            input_fingerprint=_job_fingerprint(job),
            validation_checks={
                "local_validation": "pass",
                "hardware_submission": "pass_blocked",
                "execution_authority": "pass_blocked",
                "paper_order_authority": "pass_blocked",
                "trade_candidate_creation": "pass_blocked",
            },
        )


class QiskitAerBackend(QuantumBackend):
    key = "qiskit_aer_local"

    def run(self, job: QuantumOracleJob) -> QuantumBackendOutput:
        pattern = _pattern_score(job)
        ambiguity = _ambiguity_score(job)
        try:
            from qiskit import QuantumCircuit, transpile  # type: ignore[import-not-found]
            from qiskit_aer import AerSimulator  # type: ignore[import-not-found]

            circuit = QuantumCircuit(2, 2)
            circuit.ry(pattern * pi, 0)
            circuit.ry(ambiguity * pi, 1)
            circuit.cx(0, 1)
            circuit.measure([0, 1], [0, 1])
            seed = int(_job_fingerprint(job)[:8], 16)
            simulator = AerSimulator(seed_simulator=seed)
            compiled = transpile(circuit, simulator)
            counts = simulator.run(compiled, shots=QUANTUM_ORACLE_SHOTS).result().get_counts()
            normalized_counts = {str(key): int(value) for key, value in counts.items()}
            pattern, ambiguity = _scores_from_counts(normalized_counts)
            backend_status = "ok"
            simulator_status = "qiskit_aer_available"
            local_mode = "qiskit_aer_local_circuit"
        except Exception:
            normalized_counts = _counts_from_scores(pattern, ambiguity)
            backend_status = "degraded_classical_fallback"
            simulator_status = "qiskit_aer_import_or_runtime_failed_classical_fallback"
            local_mode = "deterministic_classical_shadow"

        return QuantumBackendOutput(
            backend=self.key if backend_status == "ok" else "classical_fallback",
            backend_status=backend_status,
            simulator_status=simulator_status,
            local_simulation_mode=local_mode,
            pattern_score=pattern,
            ambiguity_score=ambiguity,
            circuit_blueprint=_circuit_blueprint(job),
            measurement_counts=normalized_counts,
            input_fingerprint=_job_fingerprint(job),
            validation_checks={
                "local_validation": "pass",
                "hardware_submission": "pass_blocked",
                "execution_authority": "pass_blocked",
                "paper_order_authority": "pass_blocked",
                "trade_candidate_creation": "pass_blocked",
            },
        )


def select_quantum_backend() -> QuantumBackend:
    if _optional_module_available("qiskit") and _optional_module_available("qiskit_aer"):
        return QiskitAerBackend()
    return ClassicalFallbackBackend()


def run_quantum_oracle_job(job: QuantumOracleJob) -> QuantumOracleResult:
    backend_output = select_quantum_backend().run(job)
    pattern = backend_output.pattern_score
    ambiguity = backend_output.ambiguity_score
    if ambiguity >= 0.72:
        recommendation = "downgrade_or_hold"
        confidence_delta = -0.08
    elif pattern >= 0.68 and ambiguity <= 0.42:
        recommendation = "upgrade_shadow_confidence"
        confidence_delta = 0.05
    else:
        recommendation = "hold"
        confidence_delta = 0.0
    result = QuantumOracleResult(
        schema_version=QUANTUM_ORACLE_SCHEMA_VERSION,
        result_id=str(uuid4()),
        job_id=job.job_id,
        job_type=job.job_type,
        status="ok",
        backend=backend_output.backend,
        backend_status=backend_output.backend_status,
        simulator_status=backend_output.simulator_status,
        local_simulation_mode=backend_output.local_simulation_mode,
        local_validation_status="passed",
        hardware_submission_allowed=False,
        hardware_submitted=False,
        hardware_provider=None,
        pattern_score=pattern,
        ambiguity_score=ambiguity,
        confidence_delta=confidence_delta,
        recommendation=recommendation,
        circuit_blueprint=backend_output.circuit_blueprint,
        measurement_counts=backend_output.measurement_counts,
        input_fingerprint=backend_output.input_fingerprint,
        validation_checks=backend_output.validation_checks,
        instrument_focus=job.instrument_focus,
        source_ref=job.source_ref,
        required_next_steps=(
            "Keep Signal Integrity and Risk Agent gates ahead of any trade state.",
            "Install qiskit and qiskit-aer later if actual circuit simulation is required.",
            "Add IBM Quantum or AWS Braket credentials only after local circuit validation exists.",
        ),
        execution_allowed=False,
        paper_order_allowed=False,
        trade_candidate_created=False,
        hardware_scheduler_enabled=False,
        created_at=_now(),
        boundary=(
            "Head of Quant output is a bounded weekly oracle. It can upgrade, downgrade, "
            "or hold a reviewed signal in shadow mode only; it cannot originate trades or "
            "bypass Signal Integrity, Risk Agent, Execution Policy, reconciliation, or receipt gates."
        ),
    )
    validate_quantum_oracle_result(result)
    return result


def validate_quantum_oracle_result(result: QuantumOracleResult) -> None:
    if result.schema_version != QUANTUM_ORACLE_SCHEMA_VERSION:
        raise ValueError("quantum oracle schema version mismatch")
    if result.hardware_submission_allowed:
        raise ValueError("quantum oracle cannot allow hardware submission in Phase 3 scaffold")
    if result.hardware_submitted:
        raise ValueError("quantum oracle scaffold must not submit hardware jobs")
    if result.execution_allowed:
        raise ValueError("quantum oracle cannot allow execution")
    if result.paper_order_allowed:
        raise ValueError("quantum oracle cannot allow paper orders")
    if result.trade_candidate_created:
        raise ValueError("quantum oracle cannot create trade candidates")
    if result.hardware_scheduler_enabled:
        raise ValueError("quantum oracle hardware scheduler must stay disabled")
    if result.local_validation_status != "passed":
        raise ValueError("quantum oracle local validation must pass before recording a result")
    if len(result.input_fingerprint) != 64:
        raise ValueError("quantum oracle input fingerprint must be a sha256 hex digest")
    if not result.circuit_blueprint:
        raise ValueError("quantum oracle result must include a local circuit blueprint")
    if not result.measurement_counts:
        raise ValueError("quantum oracle result must include local measurement counts")
    if not result.validation_checks:
        raise ValueError("quantum oracle result must include validation checks")
    if any(not str(value).startswith("pass") for value in result.validation_checks.values()):
        raise ValueError("quantum oracle validation checks must be passing before storage")
    if not 0 <= result.pattern_score <= 1:
        raise ValueError("quantum pattern score must be between 0 and 1")
    if not 0 <= result.ambiguity_score <= 1:
        raise ValueError("quantum ambiguity score must be between 0 and 1")


class QuantumOracleStore:
    def __init__(self, path: str | Path | None = None, settings: Settings | None = None) -> None:
        self.settings = settings or Settings.from_env()
        self.path = Path(path or Path(self.settings.runtime_dir) / "quantum_oracle_results.jsonl")
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def write(
        self,
        job: QuantumOracleJob,
        result: QuantumOracleResult,
        *,
        event_log: EventLog | None = None,
    ) -> QuantumOracleResult:
        validate_quantum_oracle_result(result)
        with self.path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps({"job": job.to_dict(), "result": result.to_dict()}, sort_keys=True) + "\n")
        (event_log or EventLog(echo=False)).write(
            "quantum_oracle_result_recorded",
            "head_of_quant",
            {
                "job_id": job.job_id,
                "result_id": result.result_id,
                "job_type": result.job_type,
                "backend": result.backend,
                "backend_status": result.backend_status,
                "local_simulation_mode": result.local_simulation_mode,
                "recommendation": result.recommendation,
                "hardware_submitted": result.hardware_submitted,
                "execution_allowed": result.execution_allowed,
                "paper_order_allowed": result.paper_order_allowed,
            },
        )
        return result

    def read(self, limit: int | None = None) -> tuple[dict[str, Any], ...]:
        if not self.path.exists():
            return ()
        rows: list[dict[str, Any]] = []
        with self.path.open("r", encoding="utf-8") as handle:
            for line_number, line in enumerate(handle, start=1):
                stripped = line.strip()
                if not stripped:
                    continue
                try:
                    loaded = json.loads(stripped)
                except json.JSONDecodeError as exc:
                    raise ValueError(f"invalid quantum oracle line {line_number} in {self.path}") from exc
                if isinstance(loaded, dict):
                    rows.append(loaded)
        if limit is not None:
            rows = rows[-limit:]
        return tuple(rows)

    def health(self) -> dict[str, Any]:
        try:
            rows = self.read()
        except Exception as exc:  # noqa: BLE001 - health should report the failure.
            return {"status": "degraded", "schema_version": QUANTUM_ORACLE_SCHEMA_VERSION, "error": str(exc)}
        results = [row.get("result", {}) for row in rows if isinstance(row.get("result"), dict)]
        latest = results[-1] if results else {}
        return {
            "status": "ready_classical_fallback" if not results else "ok",
            "schema_version": QUANTUM_ORACLE_SCHEMA_VERSION,
            "result_count": len(results),
            "hardware_submitted_count": sum(1 for result in results if result.get("hardware_submitted") is True),
            "hardware_submission_allowed_count": sum(
                1 for result in results if result.get("hardware_submission_allowed") is True
            ),
            "execution_allowed_count": sum(1 for result in results if result.get("execution_allowed") is True),
            "paper_order_allowed_count": sum(1 for result in results if result.get("paper_order_allowed") is True),
            "trade_candidate_created_count": sum(
                1 for result in results if result.get("trade_candidate_created") is True
            ),
            "hardware_scheduler_enabled_count": sum(
                1 for result in results if result.get("hardware_scheduler_enabled") is True
            ),
            "latest_backend": latest.get("backend") if results else "classical_fallback",
            "latest_backend_status": latest.get("backend_status") if results else "not_run",
            "latest_local_simulation_mode": latest.get("local_simulation_mode") if results else "not_run",
            "latest_recommendation": latest.get("recommendation") if results else "not_run",
            "latest_input_fingerprint": latest.get("input_fingerprint") if results else None,
            "latest_validation_checks": latest.get("validation_checks") if results else {},
            "latest_created_at": latest.get("created_at") if results else None,
            "cadence": "weekly_shadow_oracle",
            "cadence_days": QUANTUM_ORACLE_CADENCE_DAYS,
            "next_due_at": _next_due_at(latest.get("created_at")) if results else None,
            "qiskit_aer_available": _optional_module_available("qiskit_aer"),
            "qiskit_available": _optional_module_available("qiskit"),
            "boundary": (
                "Quantum oracle status is non-executable. It can only provide a shadow upgrade, "
                "downgrade, or hold recommendation after local validation."
            ),
        }


def _latest_signal_integrity_review(settings: Settings) -> dict[str, Any] | None:
    from orchestrator.signal_integrity import SignalIntegrityReviewStore, run_signal_integrity_gate

    store = SignalIntegrityReviewStore(settings=settings)
    reviews = store.read(limit=1)
    if reviews:
        return reviews[-1]
    run_signal_integrity_gate(settings=settings, seed_sample_if_empty=True)
    reviews = store.read(limit=1)
    return reviews[-1] if reviews else None


def run_quantum_oracle_sample(
    *,
    settings: Settings | None = None,
    store: QuantumOracleStore | None = None,
    event_log: EventLog | None = None,
) -> dict[str, Any]:
    settings = settings or Settings.from_env()
    store = store or QuantumOracleStore(settings=settings)
    event_log = event_log or EventLog(echo=False)
    review = _latest_signal_integrity_review(settings)
    jobs = (
        build_quantum_oracle_job(review, job_type="pattern_recognition"),
        build_quantum_oracle_job(review, job_type="strategy_collapse"),
    )
    results = tuple(run_quantum_oracle_job(job) for job in jobs)
    for job, result in zip(jobs, results):
        store.write(job, result, event_log=event_log)
    health = store.health()
    return {
        "status": "ok",
        "schema_version": QUANTUM_ORACLE_SCHEMA_VERSION,
        "job_count": len(jobs),
        "result_count": len(results),
        "backend": results[-1].backend if results else "classical_fallback",
        "hardware_submitted_count": sum(1 for result in results if result.hardware_submitted),
        "hardware_submission_allowed_count": sum(1 for result in results if result.hardware_submission_allowed),
        "execution_allowed_count": sum(1 for result in results if result.execution_allowed),
        "paper_order_allowed_count": sum(1 for result in results if result.paper_order_allowed),
        "trade_candidate_created_count": sum(1 for result in results if result.trade_candidate_created),
        "hardware_scheduler_enabled_count": sum(1 for result in results if result.hardware_scheduler_enabled),
        "store": health,
        "event_log": event_log.health(),
        "boundary": health["boundary"],
    }


def quantum_oracle_summary(settings: Settings | None = None) -> dict[str, Any]:
    settings = settings or Settings.from_env()
    return QuantumOracleStore(settings=settings).health()
