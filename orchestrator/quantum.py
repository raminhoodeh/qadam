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
from orchestrator.secrets import secret_status, secret_value

QUANTUM_ORACLE_SCHEMA_VERSION = 1
QUANTUM_PROVIDER_READINESS_SCHEMA_VERSION = 1
QUANTUM_LOCAL_SIMULATOR_SCHEMA_VERSION = 1
QCTRL_READINESS_SCHEMA_VERSION = 1
QCTRL_FIRE_OPAL_IBM_READINESS_SCHEMA_VERSION = 2
QCTRL_FIRE_OPAL_IBM_READINESS_RUNTIME_ARTIFACT = "qctrl_fire_opal_ibm_readiness.json"
QUANTUM_HARDWARE_PROVIDER_STUB_SCHEMA_VERSION = 1
QUANTUM_SCHEDULER_DRY_RUN_SCHEMA_VERSION = 1
QUANTUM_ORACLE_INPUT_CONTRACT_SCHEMA_VERSION = 1
QUANTUM_ORACLE_OUTPUT_ROUTING_SCHEMA_VERSION = 1
QUANTUM_ORACLE_JOB_TYPES = {"pattern_recognition", "strategy_collapse"}
QUANTUM_ORACLE_RECOMMENDATIONS = {"upgrade_shadow_confidence", "downgrade_or_hold", "hold"}
QUANTUM_ORACLE_CADENCE_DAYS = 7
QUANTUM_ORACLE_SHOTS = 256
QUANTUM_PROVIDER_KEYS = {"qiskit_aer", "qctrl", "ibm_quantum", "aws_braket"}
QUANTUM_HARDWARE_PROVIDER_KEYS = {"ibm_quantum", "aws_braket"}
QUANTUM_ORACLE_INPUT_SOURCE_TYPES = {"signal_integrity_review", "certified_shadow_review_packet"}
QUANTUM_PROVIDER_ALLOWED_STATUSES = {
    "available_without_secret",
    "missing_optional_package",
    "configured",
    "missing_secret",
    "disabled_by_policy",
}
QUANTUM_HARDWARE_PROVIDER_ALLOWED_STATUSES = {
    "missing_credentials",
    "missing_local_validation",
    "configured_policy_blocked",
    "disabled_by_policy",
}
QCTRL_READINESS_ALLOWED_STATUSES = {
    "configured_package_importable",
    "configured_missing_optional_package",
    "missing_secret",
    "disabled_by_policy",
}
QCTRL_SDK_MODULE_CANDIDATES = ("fireopal", "qctrl", "boulderopal")
FIRE_OPAL_IBM_SDK_MODULE_CANDIDATES = ("fireopal", "qiskit_ibm_runtime", "qiskit")
FIRE_OPAL_IBM_ALLOWED_STATUSES = {
    "blocked_missing_fire_opal_access",
    "blocked_missing_ibm_quantum_credentials",
    "blocked_missing_ibm_runtime_package",
    "ready_for_explicit_device_probe",
    "device_probe_submitted",
    "device_probe_recorded",
    "blocked_provider_probe_failed",
}
QCTRL_ZERO_AUTHORITY_FIELDS = (
    "live_probe_enabled",
    "live_probe_attempted",
    "provider_call_allowed",
    "optimization_job_submission_allowed",
    "optimization_job_submitted",
    "hardware_submission_allowed",
    "hardware_job_submitted",
    "hardware_scheduler_enabled",
    "execution_allowed",
    "paper_order_allowed",
    "trade_candidate_authority",
    "recommendation_authority",
    "secret_value_exposed",
    "raw_response_exposed",
)
FIRE_OPAL_IBM_ZERO_AUTHORITY_FIELDS = (
    "hardware_submission_allowed",
    "hardware_job_submitted",
    "hardware_scheduler_enabled",
    "execution_allowed",
    "paper_order_allowed",
    "trade_candidate_authority",
    "recommendation_authority",
    "secret_value_exposed",
    "raw_provider_response_persisted",
    "raw_response_exposed",
)
QUANTUM_LOCAL_SIMULATOR_ALLOWED_BACKENDS = {"classical_fallback", "qiskit_aer_local"}
QUANTUM_LOCAL_SIMULATOR_ZERO_AUTHORITY_FIELDS = (
    "provider_call_allowed",
    "hardware_provider_selected",
    "hardware_submission_allowed",
    "hardware_scheduler_enabled",
    "execution_allowed",
    "paper_order_allowed",
    "trade_candidate_authority",
)
QUANTUM_HARDWARE_PROVIDER_ZERO_AUTHORITY_FIELDS = (
    "provider_call_allowed",
    "live_probe_allowed",
    "hardware_backend_implemented",
    "submitting_backend_implemented",
    "hardware_submission_allowed",
    "hardware_submitted",
    "hardware_scheduler_enabled",
    "execution_allowed",
    "paper_order_allowed",
    "trade_candidate_authority",
    "secret_value_exposed",
    "raw_response_exposed",
)
QUANTUM_SCHEDULER_ZERO_AUTHORITY_FIELDS = (
    "scheduler_enabled",
    "autonomous_scheduler_enabled",
    "background_automation_created",
    "recurring_job_created",
    "queue_write_allowed",
    "job_submission_allowed",
    "hardware_scheduler_enabled",
    "hardware_submission_allowed",
    "provider_call_allowed",
    "execution_allowed",
    "paper_order_allowed",
    "trade_candidate_authority",
    "bypass_signal_integrity_allowed",
    "bypass_strategy_lead_allowed",
    "bypass_risk_agent_allowed",
    "bypass_execution_policy_allowed",
    "bypass_broker_reconciliation_allowed",
    "bypass_paper_submit_receipt_allowed",
)


@dataclass(frozen=True)
class QuantumProvider:
    key: str
    name: str
    role: str
    status: str
    credential_key: str | None
    credential_configured: bool
    notes: str
    public_safe: bool = True
    provider_call_allowed: bool = False
    hardware_submission_allowed: bool = False
    hardware_scheduler_enabled: bool = False
    execution_allowed: bool = False
    paper_order_allowed: bool = False
    trade_candidate_authority: bool = False
    secret_value_exposed: bool = False
    raw_response_exposed: bool = False
    boundary: str = (
        "Provider readiness is status-only. It cannot call providers, submit hardware jobs, "
        "enable schedulers, create trade candidates, approve execution, approve paper orders, or write to brokers."
    )

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
    input_contract: dict[str, Any]
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
    output_routing: dict[str, Any]
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


def _parse_datetime(value: Any) -> datetime | None:
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed


def _optional_module_available(module: str) -> bool:
    return importlib.util.find_spec(module) is not None


def qctrl_readiness(settings: Settings | None = None) -> dict[str, Any]:
    settings = settings or Settings.from_env()
    credential = secret_status("QCTRL_API_KEY", settings)
    importable_modules = [module for module in QCTRL_SDK_MODULE_CANDIDATES if _optional_module_available(module)]
    sdk_package_importable = bool(importable_modules)
    if credential.configured and sdk_package_importable:
        status = "configured_package_importable"
    elif credential.configured:
        status = "configured_missing_optional_package"
    else:
        status = "missing_secret"
    readiness = {
        "schema_version": QCTRL_READINESS_SCHEMA_VERSION,
        "status": status,
        "credential_configured": credential.configured,
        "credential_source": "configured" if credential.configured else "missing",
        "sdk_package_importable": sdk_package_importable,
        "sdk_module_candidates": list(QCTRL_SDK_MODULE_CANDIDATES),
        "importable_modules": importable_modules,
        "provider_role": "future_error_suppression_and_optimization",
        "hardware_backend_role": "not_hardware_backend",
        "default_mode": "metadata_only_no_provider_call",
        "live_probe_enabled": False,
        "live_probe_attempted": False,
        "live_probe_required_flag": "--live-qctrl-readiness",
        "provider_call_allowed": False,
        "provider_call_count": 0,
        "optimization_job_submission_allowed": False,
        "optimization_job_submitted": False,
        "hardware_submission_allowed": False,
        "hardware_job_submitted": False,
        "hardware_scheduler_enabled": False,
        "execution_allowed": False,
        "paper_order_allowed": False,
        "trade_candidate_authority": False,
        "recommendation_authority": False,
        "secret_value_exposed": False,
        "raw_response_exposed": False,
        "public_safe": True,
        "runtime_failure_policy": "Degrade to metadata-only readiness; never call Q-CTRL by default.",
        "boundary": (
            "Q-CTRL readiness is metadata-only. It can report credential and local package posture, "
            "but it cannot call Q-CTRL, submit optimization jobs, submit hardware jobs, select hardware, "
            "change recommendations, create signals, approve execution, approve paper orders, expose "
            "secret values, or store raw provider responses."
        ),
    }
    validate_qctrl_readiness(readiness)
    return readiness


def validate_qctrl_readiness(readiness: dict[str, Any]) -> None:
    required = {
        "boundary",
        "credential_configured",
        "credential_source",
        "default_mode",
        "execution_allowed",
        "hardware_backend_role",
        "hardware_job_submitted",
        "hardware_scheduler_enabled",
        "hardware_submission_allowed",
        "importable_modules",
        "live_probe_attempted",
        "live_probe_enabled",
        "live_probe_required_flag",
        "optimization_job_submission_allowed",
        "optimization_job_submitted",
        "paper_order_allowed",
        "provider_call_allowed",
        "provider_call_count",
        "provider_role",
        "public_safe",
        "raw_response_exposed",
        "recommendation_authority",
        "runtime_failure_policy",
        "schema_version",
        "sdk_module_candidates",
        "sdk_package_importable",
        "secret_value_exposed",
        "status",
        "trade_candidate_authority",
    }
    missing = sorted(required - set(readiness))
    if missing:
        raise ValueError(f"Q-CTRL readiness missing required fields: {missing}")
    if readiness.get("schema_version") != QCTRL_READINESS_SCHEMA_VERSION:
        raise ValueError("Q-CTRL readiness schema version mismatch")
    if readiness.get("status") not in QCTRL_READINESS_ALLOWED_STATUSES:
        raise ValueError(f"Q-CTRL readiness status is invalid: {readiness.get('status')}")
    if readiness.get("public_safe") is not True:
        raise ValueError("Q-CTRL readiness must remain public-safe")
    if readiness.get("credential_source") not in {"configured", "missing"}:
        raise ValueError("Q-CTRL readiness credential source must stay value-free")
    if readiness.get("hardware_backend_role") != "not_hardware_backend":
        raise ValueError("Q-CTRL readiness must not be treated as a hardware backend")
    if readiness.get("default_mode") != "metadata_only_no_provider_call":
        raise ValueError("Q-CTRL readiness default mode must remain metadata-only")
    if readiness.get("live_probe_required_flag") != "--live-qctrl-readiness":
        raise ValueError("Q-CTRL live readiness must require the explicit flag")
    if readiness.get("provider_call_count") != 0:
        raise ValueError("Q-CTRL readiness must not record provider calls by default")
    if not isinstance(readiness.get("sdk_module_candidates"), list):
        raise ValueError("Q-CTRL readiness SDK module candidates must be public-safe list metadata")
    if not isinstance(readiness.get("importable_modules"), list):
        raise ValueError("Q-CTRL readiness importable modules must be public-safe list metadata")
    if bool(readiness.get("importable_modules")) is not readiness.get("sdk_package_importable"):
        raise ValueError("Q-CTRL readiness SDK import status mismatch")
    for key in QCTRL_ZERO_AUTHORITY_FIELDS:
        if readiness.get(key) is not False:
            raise ValueError(f"Q-CTRL readiness must keep {key}=False")
    if "metadata-only" not in readiness.get("boundary", "") or "cannot call Q-CTRL" not in readiness.get("boundary", ""):
        raise ValueError("Q-CTRL readiness boundary is weak")


def _read_runtime_json(settings: Settings, filename: str) -> dict[str, Any]:
    path = Path(settings.runtime_dir) / filename
    if not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}
    return payload if isinstance(payload, dict) else {}


def _fire_opal_organization_slug(settings: Settings) -> str | None:
    value = secret_value("QCTRL_ORGANIZATION_SLUG", settings) or settings.qctrl_organization_slug
    if not value:
        return None
    stripped = value.strip()
    return stripped or None


def _provider_failure_category(exc: Exception) -> str:
    text = f"{type(exc).__name__}:{exc}".lower()
    if isinstance(exc, TimeoutError) or "fire_opal_ibm_provider_probe_timeout" in text:
        return "provider_probe_timeout"
    if "pypi.org" in text or "package version" in text:
        return "sdk_update_check_network_error"
    if "invalidaccounterror" in text or "unable to retrieve instances" in text:
        return "ibm_runtime_account_invalid"
    if "unauthorized" in text or "invalid api key" in text or "authentication" in text:
        return "auth_failed"
    if "forbidden" in text or "permission" in text or "not entitled" in text:
        return "provider_access_denied"
    if "token" in text or "instance" in text or "credential" in text:
        return "credential_rejected"
    if (
        "timeout" in text
        or "connect" in text
        or "network" in text
        or "name resolution" in text
        or "nodename nor servname" in text
        or "httpsconnectionpool" in text
    ):
        return "provider_network_error"
    return "provider_runtime_error"


def _exception_status_code(exc: Exception) -> int | None:
    for attr in ("status_code", "code"):
        value = getattr(exc, attr, None)
        if isinstance(value, int):
            return value
    response = getattr(exc, "response", None)
    value = getattr(response, "status_code", None)
    return value if isinstance(value, int) else None


def _exception_message_hash(exc: Exception) -> str:
    return sha256(f"{type(exc).__name__}:{exc}".encode("utf-8")).hexdigest()


def _exception_failure_detail(exc: Exception) -> dict[str, Any]:
    return {
        "failure_category": _provider_failure_category(exc),
        "failure_class": type(exc).__name__,
        "http_status_code": _exception_status_code(exc),
        "failure_message_hash": _exception_message_hash(exc),
    }


def _import_fireopal_without_update_check() -> Any:
    """Import Fire Opal without letting its PyPI update check block probes.

    Fire Opal 11.0.0 performs a package-version HTTP request during import.
    Device discovery should fail only on the Q-CTRL/IBM path, not on a cosmetic
    update check to PyPI, so the readiness probe replaces that hook before
    importing the SDK. This does not modify authentication or device discovery.
    """

    try:
        qctrl_utils = __import__("qctrlworkflowclient.utils", fromlist=["check_package_version"])
        setattr(qctrl_utils, "check_package_version", lambda _package: None)
    except Exception:
        pass
    return __import__("fireopal")


def _submit_fire_opal_supported_devices_async(credentials: dict[str, str]) -> dict[str, Any]:
    """Submit Fire Opal device discovery without the SDK async formatter bug."""

    from fireopal.config import get_config
    from fireopal.functions.base import (
        check_submission_workflow_permissions,
        provider_registry_selector,
    )
    from qctrlworkflowclient.router.api import ApiRouter

    check_submission_workflow_permissions(
        credentials["provider"],
        "show_supported_devices",
    )
    config = get_config()
    router = config.get_router()
    if not isinstance(router, ApiRouter):
        raise RuntimeError("Fire Opal device discovery requires the API router")
    router.set_async_state(is_async=True)
    data = {"credentials": credentials}
    registry = provider_registry_selector(data)
    result = router("show_supported_devices_workflow", data, registry=registry)
    if not isinstance(result, dict):
        raise RuntimeError("Fire Opal async device discovery returned invalid result")
    return result


def _poll_fire_opal_supported_devices_result(
    action_id: str,
    *,
    max_polls: int = 5,
) -> tuple[dict[str, Any] | None, str | None]:
    """Poll a submitted Fire Opal discovery action without indefinite blocking."""

    import time

    from fireopal.fire_opal_job import FireOpalJob

    job = FireOpalJob(action_id=action_id)
    last_status: str | None = None
    for _ in range(max_polls):
        status_payload = job.status()
        last_status = str(status_payload.get("action_status") or "UNKNOWN")
        if last_status == "SUCCESS":
            return job.result(), last_status
        if last_status in {"FAILURE", "REVOKED"}:
            return None, last_status
        time.sleep(2)
    return None, last_status


def _ibm_runtime_account_preflight(settings: Settings) -> dict[str, Any]:
    """Verify IBM account/runtime access without submitting jobs."""

    result: dict[str, Any] = {
        "attempted": True,
        "succeeded": False,
        "failure_category": None,
        "failure_class": None,
        "http_status_code": None,
        "failure_message_hash": None,
        "backend_count": 0,
        "backend_name_hashes": [],
    }
    try:
        import httpx

        iam_response = httpx.post(
            "https://iam.cloud.ibm.com/identity/token",
            data={
                "grant_type": "urn:ibm:params:oauth:grant-type:apikey",
                "apikey": secret_value("IBM_QUANTUM_TOKEN", settings),
            },
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            timeout=15,
        )
        if iam_response.status_code != 200:
            result.update(
                {
                    "failure_category": "ibm_iam_token_rejected",
                    "failure_class": "IbmIamTokenRejected",
                    "http_status_code": iam_response.status_code,
                    "failure_message_hash": sha256(
                        iam_response.text.encode("utf-8")
                    ).hexdigest(),
                }
            )
            return result

        from qiskit_ibm_runtime import QiskitRuntimeService

        QiskitRuntimeService(
            channel="ibm_quantum_platform",
            token=secret_value("IBM_QUANTUM_TOKEN", settings),
            instance=secret_value("IBM_QUANTUM_INSTANCE", settings),
        )
        result.update(
            {
                "succeeded": True,
            }
        )
    except Exception as exc:  # noqa: BLE001 - public artifact must stay sanitized.
        result.update(_exception_failure_detail(exc))
    return result


def _device_hashes(devices: Any) -> list[str]:
    if isinstance(devices, dict):
        values = list(devices.values())
    elif isinstance(devices, list):
        values = devices
    else:
        values = []
    hashes: list[str] = []
    for value in values[:20]:
        if isinstance(value, dict):
            name = value.get("name") or value.get("backend_name") or value.get("id")
        else:
            name = str(value)
        if name:
            hashes.append(sha256(str(name).encode("utf-8")).hexdigest())
    return hashes


def _fire_opal_ibm_readiness_path(settings: Settings | None = None) -> Path:
    return Path((settings or Settings.from_env()).runtime_dir) / QCTRL_FIRE_OPAL_IBM_READINESS_RUNTIME_ARTIFACT


def _persisted_fire_opal_ibm_probe(settings: Settings) -> dict[str, Any]:
    payload = _read_runtime_json(settings, QCTRL_FIRE_OPAL_IBM_READINESS_RUNTIME_ARTIFACT)
    if not payload:
        return {}
    try:
        validate_qctrl_fire_opal_ibm_readiness(payload)
    except ValueError:
        return {}
    if payload.get("provider_device_probe_requested") is not True:
        return {}
    if payload.get("provider_call_attempted") is not True:
        return {}
    return payload


def write_qctrl_fire_opal_ibm_readiness(
    readiness: dict[str, Any],
    settings: Settings | None = None,
) -> Path:
    validate_qctrl_fire_opal_ibm_readiness(readiness)
    path = _fire_opal_ibm_readiness_path(settings)
    path.parent.mkdir(parents=True, exist_ok=True)
    public_safe = dict(readiness)
    public_safe["secret_value_exposed"] = False
    public_safe["raw_provider_response_persisted"] = False
    public_safe["raw_response_exposed"] = False
    path.write_text(json.dumps(public_safe, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path


def qctrl_fire_opal_ibm_readiness(
    settings: Settings | None = None,
    *,
    probe_devices: bool = False,
) -> dict[str, Any]:
    """Return the Fire Opal + IBM Quantum readiness contract.

    The guide-backed path has three separate gates:
    Fire Opal product access, IBM Quantum credentials/runtime packages, then an
    explicit device-discovery probe. It never submits a hardware job.
    """

    settings = settings or Settings.from_env()
    qctrl = qctrl_readiness(settings)
    product_access = _read_runtime_json(settings, "paper_live_qctrl_product_access.json")
    fire_opal_product_access_verified = (
        product_access.get("product_access_verified") is True
        and product_access.get("paper_consultation_ready") is True
        and product_access.get("provider_call_succeeded") is True
    )
    organization_slug = _fire_opal_organization_slug(settings)
    ibm_token = secret_status("IBM_QUANTUM_TOKEN", settings)
    ibm_instance = secret_status("IBM_QUANTUM_INSTANCE", settings)
    fire_opal_importable = _optional_module_available("fireopal")
    qiskit_ibm_runtime_importable = _optional_module_available("qiskit_ibm_runtime")
    qiskit_importable = _optional_module_available("qiskit")
    credential_ready = ibm_token.configured and ibm_instance.configured
    package_ready = (
        fire_opal_importable and qiskit_ibm_runtime_importable and qiskit_importable
    )
    provider_probe_allowed = (
        fire_opal_product_access_verified
        and credential_ready
        and package_ready
        and organization_slug is not None
    )
    provider_call_attempted = False
    provider_call_succeeded = False
    provider_call_count = 0
    provider_failure_category: str | None = None
    provider_failure_class: str | None = None
    provider_failure_stage: str | None = None
    provider_http_status_code: int | None = None
    provider_failure_message_hash: str | None = None
    fire_opal_async_action_submitted = False
    fire_opal_async_action_completed = False
    fire_opal_async_action_status: str | None = None
    fire_opal_async_action_id_hash: str | None = None
    ibm_runtime_preflight_attempted = False
    ibm_runtime_preflight_succeeded = False
    ibm_runtime_backend_count = 0
    ibm_runtime_backend_name_hashes: list[str] = []
    supported_device_count = 0
    supported_device_name_hashes: list[str] = []
    persisted_probe = _persisted_fire_opal_ibm_probe(settings) if not probe_devices else {}

    if probe_devices and provider_probe_allowed:
        ibm_preflight = _ibm_runtime_account_preflight(settings)
        ibm_runtime_preflight_attempted = ibm_preflight["attempted"] is True
        ibm_runtime_preflight_succeeded = ibm_preflight["succeeded"] is True
        ibm_runtime_backend_count = int(ibm_preflight.get("backend_count") or 0)
        ibm_runtime_backend_name_hashes = list(
            ibm_preflight.get("backend_name_hashes") or []
        )
        if not ibm_runtime_preflight_succeeded:
            provider_failure_category = ibm_preflight["failure_category"]
            provider_failure_class = ibm_preflight["failure_class"]
            provider_failure_stage = "ibm_runtime_preflight"
            provider_http_status_code = ibm_preflight["http_status_code"]
            provider_failure_message_hash = ibm_preflight["failure_message_hash"]
        else:
            provider_call_attempted = True
            provider_call_count = 1
            provider_stage = "fireopal_import"
            try:
                fire_opal = _import_fireopal_without_update_check()
                configure_organization = getattr(fire_opal, "configure_organization", None)
                if callable(configure_organization):
                    provider_stage = "configure_organization"
                    configure_organization(organization_slug)
                provider_stage = "qctrl_auth"
                auth = getattr(fire_opal, "authenticate_qctrl_account")
                auth(api_key=secret_value("QCTRL_API_KEY", settings))
                provider_stage = "ibm_credentials"
                credentials = fire_opal.credentials.make_credentials_for_ibm_cloud(
                    token=secret_value("IBM_QUANTUM_TOKEN", settings),
                    instance=secret_value("IBM_QUANTUM_INSTANCE", settings),
                )
                provider_stage = "show_supported_devices_async_submit"
                supported = _submit_fire_opal_supported_devices_async(credentials)
                action = supported.get("async_result") if isinstance(supported, dict) else None
                action_id = getattr(action, "action_id", None)
                action_status = getattr(action, "status", None)
                if action_id:
                    fire_opal_async_action_submitted = True
                    fire_opal_async_action_status = str(action_status or "UNKNOWN")
                    fire_opal_async_action_id_hash = sha256(
                        str(action_id).encode("utf-8")
                    ).hexdigest()
                    result_payload, polled_status = _poll_fire_opal_supported_devices_result(
                        str(action_id)
                    )
                    if polled_status:
                        fire_opal_async_action_status = polled_status
                    if isinstance(result_payload, dict):
                        fire_opal_async_action_completed = True
                        devices = result_payload.get("supported_devices", [])
                        if isinstance(devices, dict):
                            supported_device_count = len(devices)
                        elif isinstance(devices, list):
                            supported_device_count = len(devices)
                        supported_device_name_hashes = _device_hashes(devices)
                else:
                    provider_stage = "show_supported_devices_result_parse"
                    devices = (
                        supported.get("supported_devices")
                        if isinstance(supported, dict)
                        else []
                    )
                    if isinstance(devices, dict):
                        supported_device_count = len(devices)
                    elif isinstance(devices, list):
                        supported_device_count = len(devices)
                    supported_device_name_hashes = _device_hashes(devices)
                provider_call_succeeded = True
            except Exception as exc:  # noqa: BLE001 - persisted state must stay sanitized.
                provider_failure_category = _provider_failure_category(exc)
                provider_failure_class = type(exc).__name__
                provider_failure_stage = provider_stage
                provider_http_status_code = _exception_status_code(exc)
                provider_failure_message_hash = _exception_message_hash(exc)

    if not fire_opal_product_access_verified:
        status = "blocked_missing_fire_opal_access"
        blocker = "fire_opal_product_access_not_verified"
        next_required_action = "Run PT-1 until Fire Opal product access is verified for qadam."
    elif not credential_ready:
        status = "blocked_missing_ibm_quantum_credentials"
        blocker = "ibm_quantum_token_or_instance_missing"
        next_required_action = (
            "Add IBM_QUANTUM_TOKEN and IBM_QUANTUM_INSTANCE to the local secret store, "
            "then rerun the Fire Opal IBM readiness check."
        )
    elif not package_ready:
        status = "blocked_missing_ibm_runtime_package"
        blocker = "qiskit_or_qiskit_ibm_runtime_missing"
        next_required_action = (
            "Install the quantum-ibm optional dependencies, then rerun the readiness check."
        )
    elif provider_call_succeeded and fire_opal_async_action_completed:
        status = "device_probe_recorded"
        blocker = "none"
        next_required_action = (
            "Keep hardware submission disabled until a separate hardware-submit policy is approved."
        )
    elif provider_call_succeeded and fire_opal_async_action_submitted:
        status = "device_probe_submitted"
        blocker = "none"
        next_required_action = (
            "Fire Opal accepted the read-only IBM device discovery action. "
            "Poll provider status separately before approving hardware submission."
        )
    elif provider_call_succeeded:
        status = "device_probe_recorded"
        blocker = "none"
        next_required_action = (
            "Keep hardware submission disabled until a separate hardware-submit policy is approved."
        )
    elif provider_call_attempted or provider_failure_category:
        status = "blocked_provider_probe_failed"
        blocker = provider_failure_category or "provider_probe_failed"
        next_required_action = "Resolve the sanitized provider probe failure, then rerun."
    elif (
        persisted_probe
        and provider_probe_allowed
        and persisted_probe.get("status")
        in {"device_probe_recorded", "device_probe_submitted", "blocked_provider_probe_failed"}
    ):
        return persisted_probe
    else:
        status = "ready_for_explicit_device_probe"
        blocker = "explicit_device_probe_not_run"
        next_required_action = (
            "Run the check with --probe-devices to discover IBM devices through Fire Opal."
        )

    readiness = {
        "schema_version": QCTRL_FIRE_OPAL_IBM_READINESS_SCHEMA_VERSION,
        "status": status,
        "generated_at": _now(),
        "mode": settings.mode,
        "public_safe": True,
        "qctrl_organization_slug_configured": organization_slug is not None,
        "qctrl_organization_slug_default": organization_slug == "qadam",
        "qctrl_fire_opal_product_required": True,
        "fire_opal_product_access_verified": fire_opal_product_access_verified,
        "qctrl_product_access_status": product_access.get("status", "missing"),
        "qctrl_auth_status": product_access.get("qctrl_auth_status"),
        "qctrl_provider_call_succeeded": product_access.get("provider_call_succeeded")
        is True,
        "qctrl_sdk_package_importable": qctrl.get("sdk_package_importable") is True,
        "fire_opal_sdk_importable": fire_opal_importable,
        "qiskit_ibm_runtime_importable": qiskit_ibm_runtime_importable,
        "qiskit_importable": qiskit_importable,
        "ibm_quantum_token_configured": ibm_token.configured,
        "ibm_quantum_instance_configured": ibm_instance.configured,
        "provider_device_probe_requested": probe_devices,
        "provider_device_probe_allowed": provider_probe_allowed,
        "provider_call_attempted": provider_call_attempted,
        "provider_call_succeeded": provider_call_succeeded,
        "provider_call_count": provider_call_count,
        "provider_failure_category": provider_failure_category,
        "provider_failure_class": provider_failure_class,
        "provider_failure_stage": provider_failure_stage,
        "provider_http_status_code": provider_http_status_code,
        "provider_failure_message_hash": provider_failure_message_hash,
        "fire_opal_async_action_submitted": fire_opal_async_action_submitted,
        "fire_opal_async_action_completed": fire_opal_async_action_completed,
        "fire_opal_async_action_status": fire_opal_async_action_status,
        "fire_opal_async_action_id_hash": fire_opal_async_action_id_hash,
        "ibm_runtime_preflight_attempted": ibm_runtime_preflight_attempted,
        "ibm_runtime_preflight_succeeded": ibm_runtime_preflight_succeeded,
        "ibm_runtime_backend_count": ibm_runtime_backend_count,
        "ibm_runtime_backend_name_hashes": ibm_runtime_backend_name_hashes,
        "supported_device_count": supported_device_count,
        "supported_device_name_hashes": supported_device_name_hashes,
        "hardware_submission_allowed": False,
        "hardware_job_submitted": False,
        "hardware_scheduler_enabled": False,
        "execution_allowed": False,
        "paper_order_allowed": False,
        "trade_candidate_authority": False,
        "recommendation_authority": False,
        "secret_value_exposed": False,
        "raw_provider_response_persisted": False,
        "raw_response_exposed": False,
        "blocker": blocker,
        "next_required_action": next_required_action,
        "boundary": (
            "Fire Opal IBM readiness is a mandatory Head-of-Quant provider path, "
            "but this artifact is readiness and device discovery only. It can verify "
            "Fire Opal access and optionally discover IBM Quantum devices through an "
            "explicit probe; it cannot submit hardware jobs, create trade candidates, "
            "approve execution, approve paper orders, call brokers, expose secrets, "
            "persist raw provider responses, enable schedulers, or promote live capital."
        ),
    }
    validate_qctrl_fire_opal_ibm_readiness(readiness)
    return readiness


def validate_qctrl_fire_opal_ibm_readiness(readiness: dict[str, Any]) -> None:
    required = {
        "blocker",
        "boundary",
        "execution_allowed",
        "fire_opal_async_action_completed",
        "fire_opal_async_action_id_hash",
        "fire_opal_async_action_status",
        "fire_opal_async_action_submitted",
        "fire_opal_product_access_verified",
        "fire_opal_sdk_importable",
        "generated_at",
        "hardware_job_submitted",
        "hardware_scheduler_enabled",
        "hardware_submission_allowed",
        "ibm_runtime_backend_count",
        "ibm_runtime_backend_name_hashes",
        "ibm_runtime_preflight_attempted",
        "ibm_runtime_preflight_succeeded",
        "ibm_quantum_instance_configured",
        "ibm_quantum_token_configured",
        "mode",
        "next_required_action",
        "paper_order_allowed",
        "provider_call_attempted",
        "provider_call_count",
        "provider_call_succeeded",
        "provider_device_probe_allowed",
        "provider_device_probe_requested",
        "provider_failure_category",
        "provider_failure_class",
        "public_safe",
        "qctrl_auth_status",
        "qctrl_fire_opal_product_required",
        "qctrl_organization_slug_configured",
        "qctrl_product_access_status",
        "qctrl_provider_call_succeeded",
        "qctrl_sdk_package_importable",
        "qiskit_ibm_runtime_importable",
        "qiskit_importable",
        "raw_provider_response_persisted",
        "raw_response_exposed",
        "recommendation_authority",
        "schema_version",
        "secret_value_exposed",
        "status",
        "supported_device_count",
        "supported_device_name_hashes",
        "trade_candidate_authority",
    }
    missing = sorted(required - set(readiness))
    if missing:
        raise ValueError(f"Fire Opal IBM readiness missing required fields: {missing}")
    if readiness.get("schema_version") != QCTRL_FIRE_OPAL_IBM_READINESS_SCHEMA_VERSION:
        raise ValueError("Fire Opal IBM readiness schema version mismatch")
    if readiness.get("status") not in FIRE_OPAL_IBM_ALLOWED_STATUSES:
        raise ValueError(f"Fire Opal IBM readiness status is invalid: {readiness.get('status')}")
    if readiness.get("public_safe") is not True:
        raise ValueError("Fire Opal IBM readiness must remain public-safe")
    if readiness.get("qctrl_fire_opal_product_required") is not True:
        raise ValueError("Fire Opal IBM readiness must require Fire Opal product access")
    if readiness.get("provider_call_count") not in {0, 1}:
        raise ValueError("Fire Opal IBM readiness provider call count must be 0 or 1")
    if readiness.get("provider_call_succeeded") is True and readiness.get("provider_call_attempted") is not True:
        raise ValueError("Fire Opal IBM readiness succeeded without provider attempt")
    if (
        readiness.get("status") == "device_probe_submitted"
        and readiness.get("fire_opal_async_action_submitted") is not True
    ):
        raise ValueError("Fire Opal IBM readiness submitted status requires async action")
    if (
        readiness.get("fire_opal_async_action_completed") is True
        and readiness.get("fire_opal_async_action_submitted") is not True
    ):
        raise ValueError("Fire Opal IBM readiness completed action requires submitted action")
    if readiness.get("provider_call_succeeded") is True and readiness.get("supported_device_count", 0) < 0:
        raise ValueError("Fire Opal IBM readiness supported device count invalid")
    if not isinstance(readiness.get("supported_device_name_hashes"), list):
        raise ValueError("Fire Opal IBM readiness device hashes must be a list")
    if not isinstance(readiness.get("ibm_runtime_backend_name_hashes"), list):
        raise ValueError("Fire Opal IBM readiness IBM backend hashes must be a list")
    if readiness.get("ibm_runtime_backend_count", 0) < 0:
        raise ValueError("Fire Opal IBM readiness IBM backend count invalid")
    if readiness.get("provider_call_attempted") is True and readiness.get("provider_device_probe_requested") is not True:
        raise ValueError("Fire Opal IBM readiness provider call requires explicit probe flag")
    for key in FIRE_OPAL_IBM_ZERO_AUTHORITY_FIELDS:
        if readiness.get(key) is not False:
            raise ValueError(f"Fire Opal IBM readiness must keep {key}=False")
    if "cannot submit hardware jobs" not in readiness.get("boundary", ""):
        raise ValueError("Fire Opal IBM readiness boundary is weak")


def _aws_region_configured(settings: Settings) -> bool:
    return secret_status("AWS_REGION", settings).configured or secret_status("AWS_DEFAULT_REGION", settings).configured


def _hardware_stub_status(*, credentials_configured: bool, local_validation_passed: bool, policy_approved: bool) -> str:
    if not credentials_configured:
        return "missing_credentials"
    if not local_validation_passed:
        return "missing_local_validation"
    if not policy_approved:
        return "configured_policy_blocked"
    return "disabled_by_policy"


def quantum_hardware_provider_stubs(settings: Settings | None = None) -> dict[str, Any]:
    settings = settings or Settings.from_env()
    local_simulator = quantum_local_simulator_status()
    local_validation_passed = (
        local_simulator["classical_fallback_available"] is True
        and local_simulator["schema_consistent_across_backends"] is True
        and local_simulator["required_job_count"] == len(QUANTUM_ORACLE_JOB_TYPES)
    )
    ibm_token = secret_status("IBM_QUANTUM_TOKEN", settings)
    aws_access_key = secret_status("AWS_ACCESS_KEY_ID", settings)
    aws_secret_key = secret_status("AWS_SECRET_ACCESS_KEY", settings)
    aws_region_configured = _aws_region_configured(settings)
    policy_approved = False
    providers = [
        _hardware_provider_stub(
            key="ibm_quantum",
            name="IBM Quantum / Qiskit Runtime",
            provider_role="future_primary_hardware_backend",
            credentials_configured=ibm_token.configured,
            credential_requirements={"token_configured": ibm_token.configured},
            local_validation_passed=local_validation_passed,
            policy_approved=policy_approved,
            sdk_module_candidates=("qiskit_ibm_runtime",),
            notes="Future IBM Quantum backend stub. No runtime service is constructed and no job can be submitted in Q3-4.",
        ),
        _hardware_provider_stub(
            key="aws_braket",
            name="AWS Braket",
            provider_role="future_secondary_hardware_backend",
            credentials_configured=aws_access_key.configured and aws_secret_key.configured and aws_region_configured,
            credential_requirements={
                "access_key_configured": aws_access_key.configured,
                "secret_key_configured": aws_secret_key.configured,
                "region_configured": aws_region_configured,
            },
            local_validation_passed=local_validation_passed,
            policy_approved=policy_approved,
            sdk_module_candidates=("braket",),
            notes="Future AWS Braket backend stub. No Braket client is constructed and no task can be submitted in Q3-4.",
        ),
    ]
    ledger = {
        "schema_version": QUANTUM_HARDWARE_PROVIDER_STUB_SCHEMA_VERSION,
        "status": "ok",
        "provider_count": len(providers),
        "expected_provider_count": len(QUANTUM_HARDWARE_PROVIDER_KEYS),
        "providers": providers,
        "local_simulator_validation_passed": local_validation_passed,
        "explicit_hardware_policy_approval_present": policy_approved,
        "missing_credentials_count": sum(1 for provider in providers if provider["status"] == "missing_credentials"),
        "missing_local_validation_count": sum(
            1 for provider in providers if provider["status"] == "missing_local_validation"
        ),
        "configured_policy_blocked_count": sum(
            1 for provider in providers if provider["status"] == "configured_policy_blocked"
        ),
        "disabled_by_policy_count": sum(1 for provider in providers if provider["status"] == "disabled_by_policy"),
        "credential_configured_count": sum(1 for provider in providers if provider["credential_configured"] is True),
        "provider_call_allowed_count": sum(1 for provider in providers if provider["provider_call_allowed"] is True),
        "live_probe_allowed_count": sum(1 for provider in providers if provider["live_probe_allowed"] is True),
        "hardware_backend_implemented_count": sum(
            1 for provider in providers if provider["hardware_backend_implemented"] is True
        ),
        "submitting_backend_implemented_count": sum(
            1 for provider in providers if provider["submitting_backend_implemented"] is True
        ),
        "hardware_submission_allowed_count": sum(
            1 for provider in providers if provider["hardware_submission_allowed"] is True
        ),
        "hardware_submitted_count": sum(1 for provider in providers if provider["hardware_submitted"] is True),
        "hardware_scheduler_enabled_count": sum(
            1 for provider in providers if provider["hardware_scheduler_enabled"] is True
        ),
        "execution_allowed_count": sum(1 for provider in providers if provider["execution_allowed"] is True),
        "paper_order_allowed_count": sum(1 for provider in providers if provider["paper_order_allowed"] is True),
        "trade_candidate_authority_count": sum(
            1 for provider in providers if provider["trade_candidate_authority"] is True
        ),
        "secret_value_exposed_count": sum(1 for provider in providers if provider["secret_value_exposed"] is True),
        "raw_response_exposed_count": sum(1 for provider in providers if provider["raw_response_exposed"] is True),
        "public_safe": True,
        "boundary": (
            "IBM Quantum and AWS Braket hardware provider stubs are readiness metadata only. "
            "They cannot call providers, create clients, implement a submitting backend, submit hardware jobs, "
            "enable schedulers, create trade candidates, approve execution, approve paper orders, "
            "or expose secret values or raw provider responses."
        ),
    }
    validate_quantum_hardware_provider_stubs(ledger)
    return ledger


def _hardware_provider_stub(
    *,
    key: str,
    name: str,
    provider_role: str,
    credentials_configured: bool,
    credential_requirements: dict[str, bool],
    local_validation_passed: bool,
    policy_approved: bool,
    sdk_module_candidates: tuple[str, ...],
    notes: str,
) -> dict[str, Any]:
    missing_prerequisites: list[str] = []
    if not credentials_configured:
        missing_prerequisites.append("credentials")
    if not local_validation_passed:
        missing_prerequisites.append("local_simulator_validation")
    if not policy_approved:
        missing_prerequisites.append("explicit_hardware_policy_approval")
    return {
        "schema_version": QUANTUM_HARDWARE_PROVIDER_STUB_SCHEMA_VERSION,
        "key": key,
        "name": name,
        "provider_role": provider_role,
        "status": _hardware_stub_status(
            credentials_configured=credentials_configured,
            local_validation_passed=local_validation_passed,
            policy_approved=policy_approved,
        ),
        "credential_configured": credentials_configured,
        "credential_requirements": credential_requirements,
        "sdk_module_candidates": list(sdk_module_candidates),
        "sdk_package_importable": any(_optional_module_available(module) for module in sdk_module_candidates),
        "local_simulator_validation_passed": local_validation_passed,
        "explicit_hardware_policy_approval_present": policy_approved,
        "missing_prerequisites": missing_prerequisites,
        "policy_block_reason": "explicit_hardware_policy_approval_missing",
        "provider_call_allowed": False,
        "provider_call_count": 0,
        "live_probe_allowed": False,
        "hardware_backend_implemented": False,
        "submitting_backend_implemented": False,
        "hardware_submission_allowed": False,
        "hardware_submitted": False,
        "hardware_scheduler_enabled": False,
        "execution_allowed": False,
        "paper_order_allowed": False,
        "trade_candidate_authority": False,
        "secret_value_exposed": False,
        "raw_response_exposed": False,
        "public_safe": True,
        "notes": notes,
        "boundary": (
            f"{name} is a hardware provider stub only. It cannot call providers, submit hardware jobs, "
            "enable schedulers, create trade candidates, approve execution, approve paper orders, "
            "or expose secret values or raw provider responses."
        ),
    }


def validate_quantum_hardware_provider_stubs(ledger: dict[str, Any]) -> None:
    required_ledger_fields = {
        "boundary",
        "configured_policy_blocked_count",
        "credential_configured_count",
        "disabled_by_policy_count",
        "execution_allowed_count",
        "expected_provider_count",
        "explicit_hardware_policy_approval_present",
        "hardware_backend_implemented_count",
        "hardware_scheduler_enabled_count",
        "hardware_submission_allowed_count",
        "hardware_submitted_count",
        "live_probe_allowed_count",
        "local_simulator_validation_passed",
        "missing_credentials_count",
        "missing_local_validation_count",
        "paper_order_allowed_count",
        "provider_call_allowed_count",
        "provider_count",
        "providers",
        "public_safe",
        "raw_response_exposed_count",
        "schema_version",
        "secret_value_exposed_count",
        "status",
        "submitting_backend_implemented_count",
        "trade_candidate_authority_count",
    }
    missing = sorted(required_ledger_fields - set(ledger))
    if missing:
        raise ValueError(f"quantum hardware provider stubs missing required fields: {missing}")
    if ledger.get("schema_version") != QUANTUM_HARDWARE_PROVIDER_STUB_SCHEMA_VERSION:
        raise ValueError("quantum hardware provider stub schema version mismatch")
    if ledger.get("public_safe") is not True:
        raise ValueError("quantum hardware provider stubs must remain public-safe")
    providers = ledger.get("providers")
    if not isinstance(providers, list):
        raise ValueError("quantum hardware provider stubs providers must be a list")
    provider_keys = {str(provider.get("key")) for provider in providers if isinstance(provider, dict)}
    if provider_keys != QUANTUM_HARDWARE_PROVIDER_KEYS:
        raise ValueError(f"quantum hardware provider stub keys mismatch: {sorted(provider_keys)}")
    if ledger.get("provider_count") != len(QUANTUM_HARDWARE_PROVIDER_KEYS):
        raise ValueError("quantum hardware provider stub provider count mismatch")
    if ledger.get("expected_provider_count") != len(QUANTUM_HARDWARE_PROVIDER_KEYS):
        raise ValueError("quantum hardware provider stub expected provider count mismatch")
    if ledger.get("explicit_hardware_policy_approval_present") is not False:
        raise ValueError("Q3-4 hardware policy approval must remain absent")
    for key in (
        "provider_call_allowed_count",
        "live_probe_allowed_count",
        "hardware_backend_implemented_count",
        "submitting_backend_implemented_count",
        "hardware_submission_allowed_count",
        "hardware_submitted_count",
        "hardware_scheduler_enabled_count",
        "execution_allowed_count",
        "paper_order_allowed_count",
        "trade_candidate_authority_count",
        "secret_value_exposed_count",
        "raw_response_exposed_count",
    ):
        if ledger.get(key) != 0:
            raise ValueError(f"quantum hardware provider stubs must keep {key}=0")
    for provider in providers:
        validate_quantum_hardware_provider_stub(provider)
    if "readiness metadata only" not in ledger.get("boundary", ""):
        raise ValueError("quantum hardware provider stubs boundary is weak")


def validate_quantum_hardware_provider_stub(provider: dict[str, Any]) -> None:
    required_provider_fields = {
        "boundary",
        "credential_configured",
        "credential_requirements",
        "execution_allowed",
        "explicit_hardware_policy_approval_present",
        "hardware_backend_implemented",
        "hardware_scheduler_enabled",
        "hardware_submission_allowed",
        "hardware_submitted",
        "key",
        "live_probe_allowed",
        "local_simulator_validation_passed",
        "missing_prerequisites",
        "name",
        "notes",
        "paper_order_allowed",
        "policy_block_reason",
        "provider_call_allowed",
        "provider_call_count",
        "provider_role",
        "public_safe",
        "raw_response_exposed",
        "schema_version",
        "sdk_module_candidates",
        "sdk_package_importable",
        "secret_value_exposed",
        "status",
        "submitting_backend_implemented",
        "trade_candidate_authority",
    }
    missing = sorted(required_provider_fields - set(provider))
    if missing:
        raise ValueError(f"quantum hardware provider stub missing fields for {provider.get('key')}: {missing}")
    if provider.get("schema_version") != QUANTUM_HARDWARE_PROVIDER_STUB_SCHEMA_VERSION:
        raise ValueError(f"quantum hardware provider stub schema mismatch for {provider.get('key')}")
    if provider.get("key") not in QUANTUM_HARDWARE_PROVIDER_KEYS:
        raise ValueError(f"unknown quantum hardware provider stub: {provider.get('key')}")
    if provider.get("status") not in QUANTUM_HARDWARE_PROVIDER_ALLOWED_STATUSES:
        raise ValueError(f"invalid quantum hardware provider stub status: {provider.get('key')}")
    if provider.get("public_safe") is not True:
        raise ValueError(f"quantum hardware provider stub must be public-safe: {provider.get('key')}")
    if not isinstance(provider.get("credential_requirements"), dict):
        raise ValueError(f"quantum hardware provider credential requirements must be object: {provider.get('key')}")
    if not isinstance(provider.get("missing_prerequisites"), list):
        raise ValueError(f"quantum hardware provider missing prerequisites must be a list: {provider.get('key')}")
    if provider.get("provider_call_count") != 0:
        raise ValueError(f"quantum hardware provider stub must not call providers: {provider.get('key')}")
    if provider.get("explicit_hardware_policy_approval_present") is not False:
        raise ValueError(f"quantum hardware provider policy approval must remain absent: {provider.get('key')}")
    if provider.get("policy_block_reason") != "explicit_hardware_policy_approval_missing":
        raise ValueError(f"quantum hardware provider policy block reason mismatch: {provider.get('key')}")
    for key in QUANTUM_HARDWARE_PROVIDER_ZERO_AUTHORITY_FIELDS:
        if provider.get(key) is not False:
            raise ValueError(f"quantum hardware provider stub must keep {key}=False for {provider.get('key')}")
    if "credential_key" in provider:
        raise ValueError("public quantum hardware provider stubs must not expose credential_key")
    if "stub only" not in provider.get("boundary", ""):
        raise ValueError(f"quantum hardware provider stub boundary is weak: {provider.get('key')}")


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
            notes="Credential is stored locally. No Q-CTRL API calls are made by default in Phase 3A readiness.",
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


def _public_provider(provider: dict[str, object]) -> dict[str, object]:
    return {
        "schema_version": QUANTUM_PROVIDER_READINESS_SCHEMA_VERSION,
        "key": provider.get("key"),
        "name": provider.get("name"),
        "role": provider.get("role"),
        "status": provider.get("status"),
        "credential_configured": bool(provider.get("credential_configured")),
        "public_safe": bool(provider.get("public_safe")),
        "provider_call_allowed": bool(provider.get("provider_call_allowed")),
        "hardware_submission_allowed": bool(provider.get("hardware_submission_allowed")),
        "hardware_scheduler_enabled": bool(provider.get("hardware_scheduler_enabled")),
        "execution_allowed": bool(provider.get("execution_allowed")),
        "paper_order_allowed": bool(provider.get("paper_order_allowed")),
        "trade_candidate_authority": bool(provider.get("trade_candidate_authority")),
        "secret_value_exposed": bool(provider.get("secret_value_exposed")),
        "raw_response_exposed": bool(provider.get("raw_response_exposed")),
        "notes": provider.get("notes"),
        "boundary": provider.get("boundary"),
    }


def quantum_provider_readiness(settings: Settings | None = None) -> dict[str, Any]:
    providers = tuple(_public_provider(provider) for provider in quantum_providers(settings))
    by_status = {status: sum(1 for provider in providers if provider["status"] == status) for status in sorted(QUANTUM_PROVIDER_ALLOWED_STATUSES)}
    qctrl = qctrl_readiness(settings)
    hardware_stubs = quantum_hardware_provider_stubs(settings)
    ledger = {
        "schema_version": QUANTUM_PROVIDER_READINESS_SCHEMA_VERSION,
        "status": "ok",
        "provider_count": len(providers),
        "expected_provider_count": len(QUANTUM_PROVIDER_KEYS),
        "providers": list(providers),
        "by_status": by_status,
        "configured_count": sum(1 for provider in providers if provider["status"] == "configured"),
        "missing_secret_count": sum(1 for provider in providers if provider["status"] == "missing_secret"),
        "missing_optional_package_count": sum(
            1 for provider in providers if provider["status"] == "missing_optional_package"
        ),
        "available_without_secret_count": sum(
            1 for provider in providers if provider["status"] == "available_without_secret"
        ),
        "disabled_by_policy_count": sum(1 for provider in providers if provider["status"] == "disabled_by_policy"),
        "qctrl_configured": any(provider["key"] == "qctrl" and provider["credential_configured"] for provider in providers),
        "qctrl_readiness": qctrl,
        "hardware_provider_stubs": hardware_stubs,
        "provider_call_allowed_count": sum(1 for provider in providers if provider["provider_call_allowed"] is True),
        "hardware_submission_allowed_count": sum(
            1 for provider in providers if provider["hardware_submission_allowed"] is True
        ),
        "hardware_scheduler_enabled_count": sum(
            1 for provider in providers if provider["hardware_scheduler_enabled"] is True
        ),
        "execution_allowed_count": sum(1 for provider in providers if provider["execution_allowed"] is True),
        "paper_order_allowed_count": sum(1 for provider in providers if provider["paper_order_allowed"] is True),
        "trade_candidate_authority_count": sum(
            1 for provider in providers if provider["trade_candidate_authority"] is True
        ),
        "secret_value_exposed_count": sum(1 for provider in providers if provider["secret_value_exposed"] is True),
        "raw_response_exposed_count": sum(1 for provider in providers if provider["raw_response_exposed"] is True),
        "public_safe": True,
        "boundary": (
            "Quantum provider readiness is public-safe status only. It does not call providers, "
            "submit hardware jobs, enable schedulers, create trade candidates, approve execution, "
            "approve paper orders, expose secret values, or expose raw provider responses."
        ),
    }
    validate_quantum_provider_readiness(ledger)
    return ledger


def validate_quantum_provider_readiness(ledger: dict[str, Any]) -> None:
    if ledger.get("schema_version") != QUANTUM_PROVIDER_READINESS_SCHEMA_VERSION:
        raise ValueError("quantum provider readiness schema version mismatch")
    providers = ledger.get("providers")
    if not isinstance(providers, list):
        raise ValueError("quantum provider readiness providers must be a list")
    provider_keys = {str(provider.get("key")) for provider in providers if isinstance(provider, dict)}
    if provider_keys != QUANTUM_PROVIDER_KEYS:
        raise ValueError(f"quantum provider readiness keys mismatch: {sorted(provider_keys)}")
    if ledger.get("provider_count") != len(QUANTUM_PROVIDER_KEYS):
        raise ValueError("quantum provider readiness provider count mismatch")
    if ledger.get("expected_provider_count") != len(QUANTUM_PROVIDER_KEYS):
        raise ValueError("quantum provider readiness expected provider count mismatch")
    if ledger.get("public_safe") is not True:
        raise ValueError("quantum provider readiness must be public-safe")
    validate_qctrl_readiness(ledger.get("qctrl_readiness", {}))
    validate_quantum_hardware_provider_stubs(ledger.get("hardware_provider_stubs", {}))
    for provider in providers:
        if not isinstance(provider, dict):
            raise ValueError("quantum provider readiness provider rows must be objects")
        if provider.get("status") not in QUANTUM_PROVIDER_ALLOWED_STATUSES:
            raise ValueError(f"invalid quantum provider status: {provider.get('key')}={provider.get('status')}")
        if provider.get("public_safe") is not True:
            raise ValueError(f"quantum provider must be public-safe: {provider.get('key')}")
        for key in (
            "provider_call_allowed",
            "hardware_submission_allowed",
            "hardware_scheduler_enabled",
            "execution_allowed",
            "paper_order_allowed",
            "trade_candidate_authority",
            "secret_value_exposed",
            "raw_response_exposed",
        ):
            if provider.get(key) is not False:
                raise ValueError(f"quantum provider readiness must keep {key}=False for {provider.get('key')}")
        if "credential_key" in provider:
            raise ValueError("public quantum provider readiness must not expose credential_key")
    for key in (
        "provider_call_allowed_count",
        "hardware_submission_allowed_count",
        "hardware_scheduler_enabled_count",
        "execution_allowed_count",
        "paper_order_allowed_count",
        "trade_candidate_authority_count",
        "secret_value_exposed_count",
        "raw_response_exposed_count",
    ):
        if ledger.get(key) != 0:
            raise ValueError(f"quantum provider readiness must keep {key}=0")


def quantum_local_simulator_status() -> dict[str, Any]:
    qiskit_available = _optional_module_available("qiskit")
    qiskit_aer_available = _optional_module_available("qiskit_aer")
    dependencies_available = qiskit_available and qiskit_aer_available
    status = {
        "schema_version": QUANTUM_LOCAL_SIMULATOR_SCHEMA_VERSION,
        "status": "qiskit_aer_ready" if dependencies_available else "classical_fallback_ready",
        "selected_backend": "qiskit_aer_local" if dependencies_available else "classical_fallback",
        "qiskit_available": qiskit_available,
        "qiskit_aer_available": qiskit_aer_available,
        "qiskit_dependencies_available": dependencies_available,
        "classical_fallback_available": True,
        "expected_job_types": sorted(QUANTUM_ORACLE_JOB_TYPES),
        "required_job_count": len(QUANTUM_ORACLE_JOB_TYPES),
        "output_schema_version": QUANTUM_ORACLE_SCHEMA_VERSION,
        "schema_consistent_across_backends": True,
        "local_only": True,
        "provider_call_allowed": False,
        "hardware_provider_selected": False,
        "hardware_submission_allowed": False,
        "hardware_scheduler_enabled": False,
        "execution_allowed": False,
        "paper_order_allowed": False,
        "trade_candidate_authority": False,
        "public_safe": True,
        "backend_selection_policy": (
            "Use qiskit_aer_local only when local qiskit and qiskit-aer imports are available; "
            "otherwise use classical_fallback."
        ),
        "runtime_failure_policy": "Degrade to classical_fallback with the same output schema.",
        "dependency_guidance": [
            "Optional local packages: qiskit and qiskit-aer.",
            "Install the quantum-local extra only on the local machine before expecting qiskit_aer_local.",
            "Classical fallback remains valid when packages are absent or a local simulator runtime fails.",
        ],
        "boundary": (
            "The local simulator track is local-only and non-executable. It cannot call providers, "
            "select hardware, submit hardware jobs, enable schedulers, create trade candidates, "
            "approve execution, approve paper orders, or write to brokers."
        ),
    }
    validate_quantum_local_simulator_status(status)
    return status


def validate_quantum_local_simulator_status(status: dict[str, Any]) -> None:
    required = {
        "backend_selection_policy",
        "boundary",
        "classical_fallback_available",
        "dependency_guidance",
        "execution_allowed",
        "expected_job_types",
        "hardware_provider_selected",
        "hardware_scheduler_enabled",
        "hardware_submission_allowed",
        "local_only",
        "output_schema_version",
        "paper_order_allowed",
        "provider_call_allowed",
        "public_safe",
        "qiskit_aer_available",
        "qiskit_available",
        "qiskit_dependencies_available",
        "required_job_count",
        "runtime_failure_policy",
        "schema_consistent_across_backends",
        "schema_version",
        "selected_backend",
        "status",
        "trade_candidate_authority",
    }
    missing = sorted(required - set(status))
    if missing:
        raise ValueError(f"quantum local simulator status missing required fields: {missing}")
    if status.get("schema_version") != QUANTUM_LOCAL_SIMULATOR_SCHEMA_VERSION:
        raise ValueError("quantum local simulator schema version mismatch")
    if status.get("output_schema_version") != QUANTUM_ORACLE_SCHEMA_VERSION:
        raise ValueError("quantum local simulator output schema mismatch")
    if status.get("selected_backend") not in QUANTUM_LOCAL_SIMULATOR_ALLOWED_BACKENDS:
        raise ValueError("quantum local simulator selected backend is invalid")
    if status.get("expected_job_types") != sorted(QUANTUM_ORACLE_JOB_TYPES):
        raise ValueError("quantum local simulator expected job types mismatch")
    if status.get("required_job_count") != len(QUANTUM_ORACLE_JOB_TYPES):
        raise ValueError("quantum local simulator job count mismatch")
    dependencies_available = status.get("qiskit_available") is True and status.get("qiskit_aer_available") is True
    if status.get("qiskit_dependencies_available") is not dependencies_available:
        raise ValueError("quantum local simulator dependency status mismatch")
    expected_backend = "qiskit_aer_local" if dependencies_available else "classical_fallback"
    if status.get("selected_backend") != expected_backend:
        raise ValueError("quantum local simulator backend selection mismatch")
    if status.get("classical_fallback_available") is not True:
        raise ValueError("quantum local simulator must keep classical fallback available")
    if status.get("schema_consistent_across_backends") is not True:
        raise ValueError("quantum local simulator schema must stay consistent across backends")
    if status.get("local_only") is not True:
        raise ValueError("quantum local simulator must remain local-only")
    if status.get("public_safe") is not True:
        raise ValueError("quantum local simulator status must remain public-safe")
    guidance = status.get("dependency_guidance")
    if not isinstance(guidance, list) or not guidance:
        raise ValueError("quantum local simulator dependency guidance is missing")
    if not any("qiskit" in str(item).lower() for item in guidance):
        raise ValueError("quantum local simulator dependency guidance must mention qiskit")
    for key in QUANTUM_LOCAL_SIMULATOR_ZERO_AUTHORITY_FIELDS:
        if status.get(key) is not False:
            raise ValueError(f"quantum local simulator must keep {key}=False")
    if "local-only" not in status.get("boundary", ""):
        raise ValueError("quantum local simulator boundary is weak")


def _scheduler_job(job_type: str) -> dict[str, Any]:
    return {
        "schema_version": QUANTUM_SCHEDULER_DRY_RUN_SCHEMA_VERSION,
        "job_type": job_type,
        "source": "latest_signal_integrity_review",
        "local_validation_required": True,
        "dry_run_only": True,
        "queue_write_allowed": False,
        "job_submission_allowed": False,
        "hardware_submission_allowed": False,
        "provider_call_allowed": False,
        "execution_allowed": False,
        "paper_order_allowed": False,
        "trade_candidate_authority": False,
        "required_gates": [
            "signal_integrity",
            "strategy_lead_shadow_context",
            "risk_agent",
            "execution_policy",
            "broker_reconciliation",
            "paper_submit_receipt",
        ],
        "boundary": (
            "Dry-run scheduler job metadata only. It cannot write queues, submit jobs, call providers, "
            "submit hardware, create trade candidates, approve execution, or approve paper orders."
        ),
    }


def quantum_scheduler_dry_run(
    settings: Settings | None = None,
    *,
    rows: tuple[dict[str, Any], ...] | None = None,
    now: datetime | None = None,
) -> dict[str, Any]:
    settings = settings or Settings.from_env()
    if rows is None:
        rows = QuantumOracleStore(settings=settings).read()
    results = [row.get("result", {}) for row in rows if isinstance(row.get("result"), dict)]
    latest = results[-1] if results else {}
    last_run_at = latest.get("created_at") if results else None
    next_due_at = _next_due_at(last_run_at) if results else None
    parsed_next_due_at = _parse_datetime(next_due_at)
    now = now or datetime.now(timezone.utc)
    due = parsed_next_due_at is None or now >= parsed_next_due_at
    intended_jobs = [_scheduler_job(job_type) for job_type in sorted(QUANTUM_ORACLE_JOB_TYPES)]
    would_queue_jobs = intended_jobs if due else []
    state = {
        "schema_version": QUANTUM_SCHEDULER_DRY_RUN_SCHEMA_VERSION,
        "status": "due" if due else "not_due",
        "cadence": "weekly_shadow_oracle",
        "cadence_days": QUANTUM_ORACLE_CADENCE_DAYS,
        "last_run_at": last_run_at,
        "next_due_at": next_due_at,
        "due": due,
        "due_reason": "next_due_elapsed" if due and results else "no_prior_result" if due else "cadence_not_elapsed",
        "dry_run_only": True,
        "scheduler_enabled": False,
        "autonomous_scheduler_enabled": False,
        "background_automation_created": False,
        "recurring_job_created": False,
        "queue_write_allowed": False,
        "job_submission_allowed": False,
        "hardware_scheduler_enabled": False,
        "hardware_submission_allowed": False,
        "provider_call_allowed": False,
        "execution_allowed": False,
        "paper_order_allowed": False,
        "trade_candidate_authority": False,
        "intended_jobs": intended_jobs,
        "intended_job_count": len(intended_jobs),
        "would_queue_jobs": would_queue_jobs,
        "would_queue_job_count": len(would_queue_jobs),
        "jobs_queued_count": 0,
        "jobs_submitted_count": 0,
        "hardware_jobs_submitted_count": 0,
        "hardware_scheduler_enabled_count": 0,
        "hardware_submission_allowed_count": 0,
        "bypass_signal_integrity_allowed": False,
        "bypass_strategy_lead_allowed": False,
        "bypass_risk_agent_allowed": False,
        "bypass_execution_policy_allowed": False,
        "bypass_broker_reconciliation_allowed": False,
        "bypass_paper_submit_receipt_allowed": False,
        "public_safe": True,
        "boundary": (
            "Quantum scheduler dry-run state is metadata only. It cannot create background automation, "
            "write queues, submit jobs, call providers, submit hardware, enable schedulers, bypass gates, "
            "create trade candidates, approve execution, or approve paper orders."
        ),
    }
    validate_quantum_scheduler_dry_run(state)
    return state


def validate_quantum_scheduler_dry_run(state: dict[str, Any]) -> None:
    required = {
        "autonomous_scheduler_enabled",
        "background_automation_created",
        "boundary",
        "bypass_broker_reconciliation_allowed",
        "bypass_execution_policy_allowed",
        "bypass_paper_submit_receipt_allowed",
        "bypass_risk_agent_allowed",
        "bypass_signal_integrity_allowed",
        "bypass_strategy_lead_allowed",
        "cadence",
        "cadence_days",
        "dry_run_only",
        "due",
        "due_reason",
        "execution_allowed",
        "hardware_jobs_submitted_count",
        "hardware_scheduler_enabled",
        "hardware_scheduler_enabled_count",
        "hardware_submission_allowed",
        "hardware_submission_allowed_count",
        "intended_job_count",
        "intended_jobs",
        "job_submission_allowed",
        "jobs_queued_count",
        "jobs_submitted_count",
        "last_run_at",
        "next_due_at",
        "paper_order_allowed",
        "provider_call_allowed",
        "public_safe",
        "queue_write_allowed",
        "recurring_job_created",
        "scheduler_enabled",
        "schema_version",
        "status",
        "trade_candidate_authority",
        "would_queue_job_count",
        "would_queue_jobs",
    }
    missing = sorted(required - set(state))
    if missing:
        raise ValueError(f"quantum scheduler dry-run missing required fields: {missing}")
    if state.get("schema_version") != QUANTUM_SCHEDULER_DRY_RUN_SCHEMA_VERSION:
        raise ValueError("quantum scheduler dry-run schema version mismatch")
    if state.get("status") not in {"due", "not_due"}:
        raise ValueError("quantum scheduler dry-run status is invalid")
    if state.get("cadence") != "weekly_shadow_oracle":
        raise ValueError("quantum scheduler dry-run cadence mismatch")
    if state.get("cadence_days") != QUANTUM_ORACLE_CADENCE_DAYS:
        raise ValueError("quantum scheduler dry-run cadence days mismatch")
    if state.get("due") is not (state.get("status") == "due"):
        raise ValueError("quantum scheduler dry-run due/status mismatch")
    if state.get("dry_run_only") is not True:
        raise ValueError("quantum scheduler dry-run must remain dry-run only")
    if state.get("public_safe") is not True:
        raise ValueError("quantum scheduler dry-run must remain public-safe")
    intended_jobs = state.get("intended_jobs")
    would_queue_jobs = state.get("would_queue_jobs")
    if not isinstance(intended_jobs, list) or not isinstance(would_queue_jobs, list):
        raise ValueError("quantum scheduler dry-run jobs must be lists")
    intended_job_types = {str(job.get("job_type")) for job in intended_jobs if isinstance(job, dict)}
    if intended_job_types != QUANTUM_ORACLE_JOB_TYPES:
        raise ValueError(f"quantum scheduler dry-run intended job types mismatch: {sorted(intended_job_types)}")
    if state.get("intended_job_count") != len(QUANTUM_ORACLE_JOB_TYPES):
        raise ValueError("quantum scheduler dry-run intended job count mismatch")
    if state.get("due") is True and state.get("would_queue_job_count") != len(QUANTUM_ORACLE_JOB_TYPES):
        raise ValueError("quantum scheduler dry-run due state must describe all jobs")
    if state.get("due") is False and state.get("would_queue_job_count") != 0:
        raise ValueError("quantum scheduler dry-run not-due state must not queue jobs")
    if state.get("jobs_queued_count") != 0 or state.get("jobs_submitted_count") != 0:
        raise ValueError("quantum scheduler dry-run must not queue or submit jobs")
    if state.get("hardware_jobs_submitted_count") != 0:
        raise ValueError("quantum scheduler dry-run must not submit hardware jobs")
    if state.get("hardware_scheduler_enabled_count") != 0 or state.get("hardware_submission_allowed_count") != 0:
        raise ValueError("quantum scheduler dry-run must keep hardware counters zero")
    for key in QUANTUM_SCHEDULER_ZERO_AUTHORITY_FIELDS:
        if state.get(key) is not False:
            raise ValueError(f"quantum scheduler dry-run must keep {key}=False")
    for job in intended_jobs + would_queue_jobs:
        if not isinstance(job, dict):
            raise ValueError("quantum scheduler dry-run job rows must be objects")
        if job.get("job_type") not in QUANTUM_ORACLE_JOB_TYPES:
            raise ValueError(f"quantum scheduler dry-run job type is invalid: {job.get('job_type')}")
        for key in (
            "queue_write_allowed",
            "job_submission_allowed",
            "hardware_submission_allowed",
            "provider_call_allowed",
            "execution_allowed",
            "paper_order_allowed",
            "trade_candidate_authority",
        ):
            if job.get(key) is not False:
                raise ValueError(f"quantum scheduler dry-run job must keep {key}=False")
    if "metadata only" not in state.get("boundary", "") or "bypass gates" not in state.get("boundary", ""):
        raise ValueError("quantum scheduler dry-run boundary is weak")


def _safe_int(value: Any, default: int = 0) -> int:
    try:
        if value is None or value == "":
            return default
        return int(float(value))
    except (TypeError, ValueError):
        return default


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        if value is None or value == "":
            return default
        return float(value)
    except (TypeError, ValueError):
        return default


def _safe_string_list(value: Any) -> list[str]:
    if isinstance(value, list):
        return [str(item).strip()[:160] for item in value if str(item).strip()][:12]
    if isinstance(value, tuple):
        return [str(item).strip()[:160] for item in value if str(item).strip()][:12]
    if isinstance(value, str) and value.strip():
        return [value.strip()[:160]]
    return []


def _is_yahoo_market_provider(provider: str) -> bool:
    provider_key = provider.lower()
    return provider_key in {"market.yahoo_finance", "yahoo_finance"} or "yahoo" in provider_key


def _oracle_input_source_type(review: dict[str, Any]) -> str:
    if review.get("source_type") == "certified_shadow_review_packet":
        return "certified_shadow_review_packet"
    if review.get("certified_shadow_review") is True and review.get("packet_id"):
        return "certified_shadow_review_packet"
    if review.get("review_id") and review.get("source_signal_id"):
        return "signal_integrity_review"
    return "unknown"


def _oracle_input_certification(review: dict[str, Any]) -> dict[str, Any]:
    certification = review.get("certification", {})
    return certification if isinstance(certification, dict) else {}


def _oracle_input_market_policy(review: dict[str, Any]) -> dict[str, Any]:
    direct = review.get("market_confirmation_policy", {})
    if isinstance(direct, dict) and direct:
        return direct
    certification = _oracle_input_certification(review)
    certified_policy = certification.get("market_confirmation_policy", {})
    return certified_policy if isinstance(certified_policy, dict) else {}


def _oracle_input_durable_context(review: dict[str, Any]) -> dict[str, Any]:
    direct = review.get("durable_evidence_context")
    source_context = review.get("source_context")
    if isinstance(direct, dict):
        context = dict(direct)
    elif isinstance(source_context, dict):
        context = dict(source_context)
    else:
        certification = _oracle_input_certification(review)
        certified_context = certification.get("durable_evidence_context", {})
        context = dict(certified_context) if isinstance(certified_context, dict) else {}

    if not context:
        return {
            "status": "not_available",
            "available": False,
            "required_when_available": True,
            "boundary": "No durable evidence context was supplied with this oracle input.",
        }

    missing_sources = _safe_int(
        context.get("durable_replay_missing_source_count", context.get("missing_source_count", 0)),
        0,
    )
    degraded_sources = _safe_int(context.get("source_degraded_count", 0), 0)
    replayed_sources = _safe_int(
        context.get("durable_replay_replayed_source_count", context.get("replayed_source_count", 0)),
        0,
    )
    status = str(context.get("status") or context.get("durable_replay_status") or "available")
    complete = status in {"ok", "available", "durable_phase2_replay_ready"} and missing_sources == 0
    return {
        "status": "available" if complete and degraded_sources == 0 else "degraded",
        "available": True,
        "required_when_available": True,
        "mode": context.get("mode", "unknown"),
        "durable_replay_status": context.get("durable_replay_status", status),
        "durable_replay_contract_status": context.get("durable_replay_contract_status", context.get("contract_status")),
        "durable_replay_replayed_source_count": replayed_sources,
        "durable_replay_missing_source_count": missing_sources,
        "source_degraded_count": degraded_sources,
        "write_authority": False,
        "signal_authority": False,
        "order_authority": False,
        "boundary": (
            "Durable evidence context is read-only provenance. When present it must be complete, "
            "but it cannot create signals, orders, broker writes, or live-capital authority."
        ),
    }


def _oracle_input_counts(review: dict[str, Any], source_type: str) -> dict[str, Any]:
    certification = _oracle_input_certification(review)
    strategy_review = review.get("strategy_review", {})
    if not isinstance(strategy_review, dict):
        strategy_review = {}
    missing = (
        certification.get("missing_correlations")
        or review.get("missing_correlations")
        or strategy_review.get("missing_correlations")
        or []
    )
    return {
        "evidence_item_count": _safe_int(
            certification.get("evidence_item_count", review.get("evidence_item_count")),
            0,
        ),
        "source_count": _safe_int(
            certification.get("source_count", review.get("source_count", strategy_review.get("source_count"))),
            0,
        ),
        "average_trust_score": round(
            _safe_float(certification.get("average_trust_score", review.get("average_trust_score"))),
            3,
        ),
        "min_trust_score": round(
            _safe_float(certification.get("min_trust_score", review.get("min_trust_score"))),
            3,
        ),
        "signal_confidence": round(
            _safe_float(certification.get("signal_confidence", review.get("signal_confidence", review.get("confidence")))),
            3,
        ),
        "missing_correlations": _safe_string_list(missing),
        "source_ref": str(
            review.get("review_id")
            or review.get("packet_id")
            or certification.get("review_id")
            or certification.get("packet_id")
            or "unknown_input"
        )[:120],
        "source_signal_id": str(
            review.get("source_signal_id")
            or certification.get("source_signal_id")
            or review.get("packet_id")
            or "unknown_signal"
        )[:120],
        "input_source_kind": source_type,
    }


def quantum_oracle_input_contract(review: dict[str, Any] | None) -> dict[str, Any]:
    review = review if isinstance(review, dict) else {}
    source_type = _oracle_input_source_type(review)
    certification = _oracle_input_certification(review)
    counts = _oracle_input_counts(review, source_type)
    market_policy = _oracle_input_market_policy(review)
    providers = sorted(str(provider)[:80] for provider in market_policy.get("providers", []) if str(provider).strip())
    uses_yahoo = bool(market_policy.get("uses_yahoo_finance")) or any(_is_yahoo_market_provider(provider) for provider in providers)
    non_yahoo_market_provider_count = sum(1 for provider in providers if not _is_yahoo_market_provider(provider))
    yahoo_only_market_confirmation = uses_yahoo and non_yahoo_market_provider_count == 0
    durable_context = _oracle_input_durable_context(review)
    signal_integrity_boundary = str(
        review.get("boundary") or certification.get("signal_integrity_boundary") or review.get("signal_integrity_boundary") or ""
    )
    signal_integrity_boundary_present = (
        "Signal Integrity Gate" in signal_integrity_boundary
        and "cannot approve" in signal_integrity_boundary
        and "create trade candidates" in signal_integrity_boundary
    )
    if source_type == "certified_shadow_review_packet":
        signal_integrity_boundary_present = signal_integrity_boundary_present and bool(
            review.get("certified_shadow_review") is True or certification.get("certified_shadow_review") is True
        )

    execution_allowed = bool(review.get("execution_allowed") or certification.get("execution_allowed"))
    paper_order_allowed = bool(review.get("paper_order_allowed") or certification.get("paper_order_allowed"))
    trade_candidate_created = bool(
        review.get("trade_candidate_created")
        or certification.get("trade_candidate_created")
        or certification.get("trade_candidate_allowed")
    )
    rejection_reasons: list[str] = []
    if source_type not in QUANTUM_ORACLE_INPUT_SOURCE_TYPES:
        rejection_reasons.append("unsupported_input_source")
    if not signal_integrity_boundary_present:
        rejection_reasons.append("missing_signal_integrity_boundary")
    if counts["evidence_item_count"] < 1:
        rejection_reasons.append("missing_evidence")
    if counts["source_count"] < 2:
        rejection_reasons.append("insufficient_independent_sources")
    if not market_policy:
        rejection_reasons.append("missing_market_confirmation_policy")
    market_status = str(market_policy.get("status") or "missing_market_confirmation_policy")
    if market_status == "market_confirmation_stale" or market_policy.get("stale") is True:
        rejection_reasons.append("market_confirmation_stale")
    if market_status == "market_confirmation_unavailable" or market_policy.get("unavailable") is True:
        rejection_reasons.append("market_confirmation_unavailable")
    if market_status == "market_confirmation_single_source_hold" or market_policy.get("single_source_hold") is True:
        rejection_reasons.append("single_source_market_confirmation")
    if yahoo_only_market_confirmation:
        rejection_reasons.append("single_source_yahoo_only_market_confirmation")
    if durable_context.get("available") is True and durable_context.get("status") != "available":
        rejection_reasons.append("durable_evidence_context_incomplete")
    if execution_allowed or paper_order_allowed or trade_candidate_created:
        rejection_reasons.append("execution_authority_already_set")
    if any(
        key in market_policy and market_policy.get(key) is not False
        for key in ("signal_authority", "order_authority", "broker_reconciliation_authority")
    ):
        rejection_reasons.append("market_confirmation_authority_enabled")

    rejection_reasons = list(dict.fromkeys(rejection_reasons))
    accepted = not rejection_reasons
    return {
        "schema_version": QUANTUM_ORACLE_INPUT_CONTRACT_SCHEMA_VERSION,
        "status": "accepted" if accepted else "rejected",
        "source_type": source_type,
        "source_ref": counts["source_ref"],
        "source_signal_id": counts["source_signal_id"],
        "input_source_kind": counts["input_source_kind"],
        "certified_shadow_review_packet": source_type == "certified_shadow_review_packet",
        "signal_integrity_boundary_present": signal_integrity_boundary_present,
        "durable_evidence_context": durable_context,
        "market_confirmation_policy": {
            "status": market_status,
            "market_price_confirmation": market_policy.get("market_price_confirmation"),
            "providers": providers,
            "uses_yahoo_finance": uses_yahoo,
            "yahoo_finance_role": "supplemental_market_confirmation" if uses_yahoo else "not_used",
            "non_yahoo_market_provider_count": non_yahoo_market_provider_count,
            "yahoo_only_market_confirmation": yahoo_only_market_confirmation,
            "stale": bool(market_policy.get("stale")),
            "unavailable": bool(market_policy.get("unavailable")),
            "single_source_hold": bool(market_policy.get("single_source_hold")),
            "latest_observed_at": market_policy.get("latest_observed_at"),
            "signal_authority": False,
            "order_authority": False,
            "broker_reconciliation_authority": False,
            "boundary": market_policy.get(
                "boundary",
                "Market confirmation must remain supplemental and cannot create signal or order authority.",
            ),
        },
        "market_confirmation_status": market_status,
        "market_confirmation_providers": providers,
        "uses_yahoo_finance": uses_yahoo,
        "yahoo_finance_role": "supplemental_market_confirmation" if uses_yahoo else "not_used",
        "yahoo_only_market_confirmation": yahoo_only_market_confirmation,
        "evidence_item_count": counts["evidence_item_count"],
        "source_count": counts["source_count"],
        "average_trust_score": counts["average_trust_score"],
        "min_trust_score": counts["min_trust_score"],
        "signal_confidence": counts["signal_confidence"],
        "missing_correlation_count": len(counts["missing_correlations"]),
        "missing_correlations": counts["missing_correlations"],
        "execution_allowed": execution_allowed,
        "paper_order_allowed": paper_order_allowed,
        "trade_candidate_created": trade_candidate_created,
        "input_rejected": not accepted,
        "rejection_reasons": rejection_reasons,
        "public_safe": True,
        "boundary": (
            "Head of Quant input must come from Signal Integrity or a certified shadow-review packet. "
            "It cannot originate signals, accept Yahoo-only market confirmation, inherit execution authority, "
            "or bypass durable evidence context when that context is available."
        ),
    }


def validate_quantum_oracle_input_contract(
    contract: dict[str, Any],
    *,
    require_accepted: bool = True,
) -> None:
    required = {
        "average_trust_score",
        "boundary",
        "certified_shadow_review_packet",
        "durable_evidence_context",
        "evidence_item_count",
        "execution_allowed",
        "input_rejected",
        "input_source_kind",
        "market_confirmation_policy",
        "market_confirmation_providers",
        "market_confirmation_status",
        "min_trust_score",
        "missing_correlation_count",
        "missing_correlations",
        "paper_order_allowed",
        "public_safe",
        "rejection_reasons",
        "schema_version",
        "signal_confidence",
        "signal_integrity_boundary_present",
        "source_count",
        "source_ref",
        "source_signal_id",
        "source_type",
        "status",
        "trade_candidate_created",
        "uses_yahoo_finance",
        "yahoo_finance_role",
        "yahoo_only_market_confirmation",
    }
    missing = sorted(required - set(contract))
    if missing:
        raise ValueError(f"quantum oracle input contract missing required fields: {missing}")
    if contract.get("schema_version") != QUANTUM_ORACLE_INPUT_CONTRACT_SCHEMA_VERSION:
        raise ValueError("quantum oracle input contract schema mismatch")
    if contract.get("source_type") not in QUANTUM_ORACLE_INPUT_SOURCE_TYPES:
        raise ValueError("quantum oracle input source type is invalid")
    if contract.get("public_safe") is not True:
        raise ValueError("quantum oracle input contract must be public-safe")
    if contract.get("yahoo_finance_role") not in {"supplemental_market_confirmation", "not_used"}:
        raise ValueError("quantum oracle input Yahoo Finance role is invalid")
    market_policy = contract.get("market_confirmation_policy", {})
    if not isinstance(market_policy, dict):
        raise ValueError("quantum oracle input market policy is invalid")
    for key in ("signal_authority", "order_authority", "broker_reconciliation_authority"):
        if market_policy.get(key) is not False:
            raise ValueError("quantum oracle input market confirmation must not carry authority")
    durable_context = contract.get("durable_evidence_context", {})
    if not isinstance(durable_context, dict):
        raise ValueError("quantum oracle input durable evidence context is invalid")
    if "Head of Quant input" not in contract.get("boundary", ""):
        raise ValueError("quantum oracle input boundary is weak")
    if require_accepted:
        if durable_context.get("available") is True and durable_context.get("status") != "available":
            raise ValueError("quantum oracle input durable evidence context is incomplete")
        if contract.get("execution_allowed") is not False:
            raise ValueError("quantum oracle input cannot carry execution authority")
        if contract.get("paper_order_allowed") is not False:
            raise ValueError("quantum oracle input cannot carry paper-order authority")
        if contract.get("trade_candidate_created") is not False:
            raise ValueError("quantum oracle input cannot carry trade-candidate authority")
        if contract.get("status") != "accepted" or contract.get("input_rejected") is not False:
            raise ValueError(f"quantum oracle input rejected: {contract.get('rejection_reasons', [])}")
        if contract.get("rejection_reasons"):
            raise ValueError("quantum oracle accepted input must not include rejection reasons")
        if contract.get("signal_integrity_boundary_present") is not True:
            raise ValueError("quantum oracle input must include Signal Integrity boundary")
        if contract.get("evidence_item_count", 0) < 1:
            raise ValueError("quantum oracle input must include evidence")
        if contract.get("source_count", 0) < 2:
            raise ValueError("quantum oracle input must include independent source context")
        if contract.get("market_confirmation_status") != "market_confirmation_corroboration_available":
            raise ValueError("quantum oracle input requires current market confirmation")
        if contract.get("yahoo_only_market_confirmation") is not False:
            raise ValueError("quantum oracle input cannot use Yahoo-only market confirmation")


def build_quantum_oracle_job(review: dict[str, Any] | None = None, *, job_type: str) -> QuantumOracleJob:
    if job_type not in QUANTUM_ORACLE_JOB_TYPES:
        raise ValueError(f"unsupported quantum oracle job type: {job_type}")
    input_contract = quantum_oracle_input_contract(review)
    validate_quantum_oracle_input_contract(input_contract)
    return QuantumOracleJob(
        schema_version=QUANTUM_ORACLE_SCHEMA_VERSION,
        job_id=str(uuid4()),
        job_type=job_type,
        source_ref=str(input_contract["source_ref"]),
        instrument_focus=str((review or {}).get("instrument_focus") or (review or {}).get("watch_focus") or "macro_watchlist")[
            :120
        ],
        evidence_item_count=int(input_contract["evidence_item_count"]),
        source_count=int(input_contract["source_count"]),
        average_trust_score=round(float(input_contract["average_trust_score"]), 3),
        signal_confidence=round(float(input_contract["signal_confidence"]), 3),
        missing_correlation_count=int(input_contract["missing_correlation_count"]),
        local_validation_required=True,
        hardware_submission_allowed=False,
        execution_allowed=False,
        paper_order_allowed=False,
        input_contract=input_contract,
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
        "input_source_type": job.input_contract.get("source_type"),
        "market_confirmation_status": job.input_contract.get("market_confirmation_status"),
        "yahoo_only_market_confirmation": job.input_contract.get("yahoo_only_market_confirmation"),
        "durable_evidence_status": job.input_contract.get("durable_evidence_context", {}).get("status"),
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


def quantum_oracle_output_routing(
    *,
    job: QuantumOracleJob,
    recommendation: str,
    confidence_delta: float,
    pattern_score: float,
    ambiguity_score: float,
) -> dict[str, Any]:
    return {
        "schema_version": QUANTUM_ORACLE_OUTPUT_ROUTING_SCHEMA_VERSION,
        "status": "shadow_annotation_ready",
        "route_type": "shadow_annotation",
        "storage_type": "oracle_review_result",
        "annotation_target": "reviewed_shadow_context",
        "source_ref": job.source_ref,
        "job_id": job.job_id,
        "job_type": job.job_type,
        "recommendation": recommendation,
        "recommendation_class": recommendation,
        "confidence_delta": round(float(confidence_delta), 3),
        "pattern_score": round(float(pattern_score), 3),
        "ambiguity_score": round(float(ambiguity_score), 3),
        "strategy_lead_context": {
            "read_allowed": True,
            "context_only": True,
            "can_modify_strategy_review": False,
            "risk_handoff_allowed": False,
            "trade_candidate_allowed": False,
            "execution_allowed": False,
            "paper_order_allowed": False,
            "boundary": "Strategy Lead may inspect Head of Quant output as context only.",
        },
        "signal_integrity_context": {
            "read_allowed": True,
            "context_only": True,
            "can_modify_signal_integrity_review": False,
            "can_upgrade_signal_status": False,
            "trade_candidate_allowed": False,
            "execution_allowed": False,
            "paper_order_allowed": False,
            "boundary": "Signal Integrity may inspect Head of Quant output as context only.",
        },
        "blocked_routes": {
            "trade_candidate_creation": False,
            "risk_agent_approval": False,
            "execution_policy_approval": False,
            "staged_paper_order": False,
            "broker_reconciliation": False,
            "paper_submit_receipt": False,
        },
        "trade_candidate_created_count": 0,
        "risk_approval_count": 0,
        "execution_policy_approval_count": 0,
        "staged_paper_order_created_count": 0,
        "broker_reconciliation_write_count": 0,
        "paper_submit_receipt_created_count": 0,
        "provider_call_allowed": False,
        "hardware_submission_allowed": False,
        "execution_allowed": False,
        "paper_order_allowed": False,
        "trade_candidate_authority": False,
        "risk_approval_authority": False,
        "execution_policy_authority": False,
        "staged_paper_order_authority": False,
        "broker_reconciliation_authority": False,
        "paper_submit_receipt_authority": False,
        "broker_write_allowed": False,
        "public_safe": True,
        "boundary": (
            "Head of Quant output is stored as a shadow annotation only. It can be read by Strategy Lead "
            "and Signal Integrity as context, but it cannot create or advance trade state, approve risk, "
            "approve execution, create staged paper orders, write broker reconciliation, or create receipts."
        ),
    }


def validate_quantum_oracle_output_routing(routing: dict[str, Any]) -> None:
    required = {
        "ambiguity_score",
        "annotation_target",
        "blocked_routes",
        "boundary",
        "broker_reconciliation_authority",
        "broker_reconciliation_write_count",
        "broker_write_allowed",
        "confidence_delta",
        "execution_allowed",
        "execution_policy_approval_count",
        "execution_policy_authority",
        "hardware_submission_allowed",
        "job_id",
        "job_type",
        "paper_order_allowed",
        "paper_submit_receipt_authority",
        "paper_submit_receipt_created_count",
        "pattern_score",
        "provider_call_allowed",
        "public_safe",
        "recommendation",
        "recommendation_class",
        "risk_approval_authority",
        "risk_approval_count",
        "route_type",
        "schema_version",
        "signal_integrity_context",
        "source_ref",
        "staged_paper_order_authority",
        "staged_paper_order_created_count",
        "status",
        "storage_type",
        "strategy_lead_context",
        "trade_candidate_authority",
        "trade_candidate_created_count",
    }
    missing = sorted(required - set(routing))
    if missing:
        raise ValueError(f"quantum oracle output routing missing required fields: {missing}")
    if routing.get("schema_version") != QUANTUM_ORACLE_OUTPUT_ROUTING_SCHEMA_VERSION:
        raise ValueError("quantum oracle output routing schema mismatch")
    if routing.get("status") != "shadow_annotation_ready":
        raise ValueError("quantum oracle output routing status is invalid")
    if routing.get("route_type") != "shadow_annotation":
        raise ValueError("quantum oracle output routing must be shadow annotation")
    if routing.get("storage_type") != "oracle_review_result":
        raise ValueError("quantum oracle output routing storage type is invalid")
    if routing.get("annotation_target") != "reviewed_shadow_context":
        raise ValueError("quantum oracle output routing target is invalid")
    if routing.get("recommendation_class") not in QUANTUM_ORACLE_RECOMMENDATIONS:
        raise ValueError("quantum oracle output routing recommendation class is invalid")
    if routing.get("recommendation") != routing.get("recommendation_class"):
        raise ValueError("quantum oracle output routing recommendation mismatch")
    for context_key in ("strategy_lead_context", "signal_integrity_context"):
        context = routing.get(context_key, {})
        if not isinstance(context, dict):
            raise ValueError(f"quantum oracle output routing {context_key} is invalid")
        if context.get("read_allowed") is not True or context.get("context_only") is not True:
            raise ValueError(f"quantum oracle output routing {context_key} must be context-only readable")
        for key in (
            "trade_candidate_allowed",
            "execution_allowed",
            "paper_order_allowed",
        ):
            if context.get(key) is not False:
                raise ValueError(f"quantum oracle output routing {context_key} must keep {key}=False")
    blocked_routes = routing.get("blocked_routes", {})
    if not isinstance(blocked_routes, dict):
        raise ValueError("quantum oracle output routing blocked routes are invalid")
    expected_routes = {
        "trade_candidate_creation",
        "risk_agent_approval",
        "execution_policy_approval",
        "staged_paper_order",
        "broker_reconciliation",
        "paper_submit_receipt",
    }
    if set(blocked_routes) != expected_routes:
        raise ValueError("quantum oracle output routing blocked routes mismatch")
    if any(value is not False for value in blocked_routes.values()):
        raise ValueError("quantum oracle output routing must block all downstream routes")
    for key in (
        "trade_candidate_created_count",
        "risk_approval_count",
        "execution_policy_approval_count",
        "staged_paper_order_created_count",
        "broker_reconciliation_write_count",
        "paper_submit_receipt_created_count",
    ):
        if routing.get(key) != 0:
            raise ValueError(f"quantum oracle output routing must keep {key}=0")
    for key in (
        "provider_call_allowed",
        "hardware_submission_allowed",
        "execution_allowed",
        "paper_order_allowed",
        "trade_candidate_authority",
        "risk_approval_authority",
        "execution_policy_authority",
        "staged_paper_order_authority",
        "broker_reconciliation_authority",
        "paper_submit_receipt_authority",
        "broker_write_allowed",
    ):
        if routing.get(key) is not False:
            raise ValueError(f"quantum oracle output routing must keep {key}=False")
    if routing.get("public_safe") is not True:
        raise ValueError("quantum oracle output routing must be public-safe")
    if "shadow annotation only" not in routing.get("boundary", ""):
        raise ValueError("quantum oracle output routing boundary is weak")


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
    output_routing = quantum_oracle_output_routing(
        job=job,
        recommendation=recommendation,
        confidence_delta=confidence_delta,
        pattern_score=pattern,
        ambiguity_score=ambiguity,
    )
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
        output_routing=output_routing,
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
    if sum(result.measurement_counts.values()) != QUANTUM_ORACLE_SHOTS:
        raise ValueError("quantum oracle measurement counts must match configured shots")
    if any(int(value) < 0 for value in result.measurement_counts.values()):
        raise ValueError("quantum oracle measurement counts must be non-negative")
    if not result.validation_checks:
        raise ValueError("quantum oracle result must include validation checks")
    if any(not str(value).startswith("pass") for value in result.validation_checks.values()):
        raise ValueError("quantum oracle validation checks must be passing before storage")
    if not 0 <= result.pattern_score <= 1:
        raise ValueError("quantum pattern score must be between 0 and 1")
    if not 0 <= result.ambiguity_score <= 1:
        raise ValueError("quantum ambiguity score must be between 0 and 1")
    validate_quantum_oracle_output_routing(result.output_routing)
    if result.output_routing.get("recommendation_class") != result.recommendation:
        raise ValueError("quantum oracle result output routing recommendation mismatch")


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
        jobs = [row.get("job", {}) for row in rows if isinstance(row.get("job"), dict)]
        latest = results[-1] if results else {}
        latest_job = jobs[-1] if jobs else {}
        latest_input_contract = (
            latest_job.get("input_contract", {}) if isinstance(latest_job.get("input_contract"), dict) else {}
        )
        latest_output_routing = (
            latest.get("output_routing", {}) if isinstance(latest.get("output_routing"), dict) else {}
        )
        latest_durable_context = latest_input_contract.get("durable_evidence_context", {})
        if not isinstance(latest_durable_context, dict):
            latest_durable_context = {}
        local_simulator = quantum_local_simulator_status()
        scheduler_dry_run = quantum_scheduler_dry_run(self.settings, rows=tuple(rows))
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
            "latest_output_route_type": latest_output_routing.get("route_type") if results else "not_run",
            "latest_output_storage_type": latest_output_routing.get("storage_type") if results else "not_run",
            "latest_output_routing_status": latest_output_routing.get("status") if results else "not_run",
            "latest_output_annotation_target": latest_output_routing.get("annotation_target") if results else "not_run",
            "latest_output_routing": latest_output_routing if results else {},
            "latest_input_contract_status": latest_input_contract.get("status") if results else "not_run",
            "latest_input_source_type": latest_input_contract.get("source_type") if results else "not_run",
            "latest_market_confirmation_status": latest_input_contract.get("market_confirmation_status")
            if results
            else "not_run",
            "latest_yahoo_finance_role": latest_input_contract.get("yahoo_finance_role") if results else "not_run",
            "latest_yahoo_only_market_confirmation": latest_input_contract.get("yahoo_only_market_confirmation")
            if results
            else False,
            "latest_durable_evidence_status": latest_durable_context.get("status") if results else "not_run",
            "latest_validation_checks": latest.get("validation_checks") if results else {},
            "latest_created_at": latest.get("created_at") if results else None,
            "cadence": "weekly_shadow_oracle",
            "cadence_days": QUANTUM_ORACLE_CADENCE_DAYS,
            "next_due_at": _next_due_at(latest.get("created_at")) if results else None,
            "local_simulator": local_simulator,
            "scheduler_dry_run": scheduler_dry_run,
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
    reviews = store.read()
    for review in reversed(reviews):
        try:
            if quantum_oracle_input_contract(review).get("status") == "accepted":
                return review
        except Exception:
            continue
    run_signal_integrity_gate(settings=settings, seed_sample_if_empty=True)
    reviews = store.read()
    for review in reversed(reviews):
        try:
            if quantum_oracle_input_contract(review).get("status") == "accepted":
                return review
        except Exception:
            continue
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
        "local_simulator": quantum_local_simulator_status(),
        "scheduler_dry_run": quantum_scheduler_dry_run(settings),
        "store": health,
        "event_log": event_log.health(),
        "boundary": health["boundary"],
    }


def quantum_oracle_summary(settings: Settings | None = None) -> dict[str, Any]:
    settings = settings or Settings.from_env()
    return QuantumOracleStore(settings=settings).health()
