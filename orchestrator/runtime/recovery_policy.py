"""Deterministic failure classification and bounded recovery policy."""

import re
from typing import Any


def classify_exception(exc: Exception) -> str:
    """Keep typed transport/status failures intact without logging secrets."""
    import httpx

    if isinstance(exc, httpx.HTTPStatusError):
        status = exc.response.status_code
        if status >= 500:
            return "transient_provider_network"
        return classify_failure(f"http status {status}", status_code=status)
    if isinstance(exc, (httpx.NetworkError, httpx.TimeoutException, httpx.RemoteProtocolError)):
        return "transient_provider_network"
    return classify_failure(type(exc).__name__)


def classify_failure(message: str, *, status_code: int | None = None) -> str:
    text = str(message or "").lower()
    # Only failed-command diagnostics belong here, but that command can also
    # print successful schema checks, counters, and paths containing keywords.
    markers = re.findall(r"(?m)^qadam_failure_class=([a-z_]+)\s*$", text)
    protected = {"safety_violation", "research_integrity_hold", "credential_operator_action"}
    for marker in markers:
        if marker in protected:
            return marker
    if any(
        token in text
        for token in (
            "resource_lock_busy:",
            "score_tape_input_snapshot_unstable:",
            "generation_source_changed_during_copy:",
            "resource deadlock avoided",
            "errno 11",
            "errno 35",
            "errno 45",
            "temporarily unavailable",
            "stale file handle",
        )
    ):
        return "concurrent_artifact_access"
    if any(
        token in text
        for token in ("live broker", "live capital", "unauthorized write", "safety violation")
    ):
        return "safety_violation"
    if any(
        token in text
        for token in (
            "research_integrity_hold",
            "negative_control_calibration_hold",
            "backtest_negative_control_promotion_gate_breach",
            "completed_score_tape_partition_immutable_mismatch",
            "score_tape_input_snapshot_integrity_hold",
        )
    ):
        return "research_integrity_hold"
    if "control_plane_disk_ceiling_exceeded" in text:
        return "storage_maintenance_due"
    if any(token in text for token in (
        "decision_dependency_circuit_open", "decision_dependency_repair_request_open",
        "conversion_stage_failed:shadow",
    )):
        return "dependency_unavailable"
    known_markers = {
        "transient_provider_network", "rate_limit", "parser_schema_drift", "code_defect",
        "database_io_unavailable", "storage_maintenance_due", "concurrent_artifact_access",
        "stale_artifact", "interrupted_resumable_job", "disk_resource_pressure",
    }
    if markers:
        # Conflicting or unknown typed failures cannot authorize a retry.
        return markers[0] if len(set(markers)) == 1 and markers[0] in known_markers else "code_defect"
    if any(
        token in text
        for token in (
            "receiver_not_configured",
            "public_status_receiver_not_configured",
        )
    ):
        return "optional_transport_unconfigured"
    if status_code == 429 or "429" in text or "rate limit" in text:
        return "rate_limit"
    if re.search(
        r"\b(?:credential(?:s)?|unauthorized|forbidden|token expired|401|403)\b",
        text,
    ):
        return "credential_operator_action"
    if re.search(r"\bqadam_failure_class=credential_operator_action\b", text):
        return "credential_operator_action"
    if re.search(r"\bqadam_failure_class=rate_limit\b", text):
        return "rate_limit"
    if re.search(r"malformed|schema(?:_| )?(?:error|mismatch|invalid|drift)|parse(?:error| error)|invalid json|jsondecode", text):
        return "parser_schema_drift"
    if any(token in text for token in (
        "sqlite3.operationalerror: disk i/o error", "unable to open database file",
        "database is locked", "database table is locked",
    )):
        return "database_io_unavailable"
    if "storage_generation_retention_exceeded:" in text:
        return "storage_maintenance_due"
    if any(token in text for token in ("disk", "no space", "resource pressure", "memory pressure")):
        return "disk_resource_pressure"
    if any(token in text for token in ("stale artifact", "freshness deadline", "artifact missing")):
        return "stale_artifact"
    if any(
        token in text
        for token in ("sigterm", "sleep", "interrupted", "stale lock", "resume cursor", "service_execution_deadline_exceeded")
    ):
        return "interrupted_resumable_job"
    if re.search(
        r"\b(?:connecterror|readerror|writeerror|remoteprotocolerror|"
        r"qadam_failure_class=transient_provider_network)\b", text
    ):
        return "transient_provider_network"
    if any(
        token in text
        for token in (
            "network",
            "timeout",
            "connection",
            "provider unavailable",
            "market_clock_refresh_failed",
            "alpaca_paper_mirror_refresh_failed",
            "paper_mirror_refresh_failed",
            "dns",
            "transport_error",
            "urlerror",
            "httperror",
        )
    ):
        return "transient_provider_network"
    if "paperops_recovery_class=broker_history_incomplete" in text:
        return "broker_history_incomplete"
    return "code_defect"

def retry_policy(failure_class: str, *, attempt_count: int = 0) -> dict[str, Any]:
    policies: dict[str, dict[str, Any]] = {
        "dependency_unavailable": {
            "automatic_retry_allowed": attempt_count < 3,
            "maximum_attempts": 3,
            "backoff_seconds": 60,
            "circuit_breaker_after_attempts": 3,
            "next_action": "revalidate_after_upstream_recovery_without_bypassing_gates",
        },
        "broker_history_incomplete": {
            "automatic_retry_allowed": attempt_count < 3,
            "maximum_attempts": 3,
            "backoff_seconds": min(60 * (2**attempt_count), 300),
            "circuit_breaker_after_attempts": 3,
            "next_action": "refresh_complete_broker_history_then_verify_protection_twice",
        },
        "database_io_unavailable": {
            "automatic_retry_allowed": attempt_count < 3,
            "maximum_attempts": 3,
            "backoff_seconds": min(30 * (2**attempt_count), 300),
            "circuit_breaker_after_attempts": 3,
            "next_action": "reopen_authoritative_database_without_replaying_broker_writes",
        },
        "storage_maintenance_due": {
            "automatic_retry_allowed": attempt_count < 3,
            "maximum_attempts": 3,
            "backoff_seconds": 60,
            "circuit_breaker_after_attempts": 3,
            "next_action": "run_bounded_generation_retention_then_revalidate",
        },
        "concurrent_artifact_access": {
            "automatic_retry_allowed": attempt_count < 5,
            "maximum_attempts": 5,
            "backoff_seconds": min(5 * (2**attempt_count), 60),
            "circuit_breaker_after_attempts": 5,
            "next_action": "wait_for_resource_lease_then_retry_same_generation",
        },
        "transient_provider_network": {
            "automatic_retry_allowed": attempt_count < 3,
            "maximum_attempts": 3,
            "backoff_seconds": min(30 * (2**attempt_count), 300),
            "circuit_breaker_after_attempts": 3,
            "next_action": "retry_idempotent_read_then_open_circuit",
        },
        "rate_limit": {
            "automatic_retry_allowed": attempt_count < 5,
            "maximum_attempts": 5,
            "backoff_seconds": min(60 * (2**attempt_count), 3600),
            "circuit_breaker_after_attempts": 5,
            "next_action": "respect_provider_retry_after",
        },
        "stale_artifact": {
            "automatic_retry_allowed": attempt_count < 1,
            "maximum_attempts": 1,
            "backoff_seconds": 0,
            "circuit_breaker_after_attempts": 1,
            "next_action": "run_known_safe_refresh_then_validate",
        },
        "interrupted_resumable_job": {
            "automatic_retry_allowed": attempt_count < 1,
            "maximum_attempts": 1,
            "backoff_seconds": 0,
            "circuit_breaker_after_attempts": 1,
            "next_action": "resume_incomplete_idempotent_job_from_checkpoint",
        },
        "research_integrity_hold": {
            "automatic_retry_allowed": False,
            "maximum_attempts": 0,
            "backoff_seconds": None,
            "circuit_breaker_after_attempts": 0,
            "next_action": (
                "quarantine_promotion_continue_observation_and_revalidate_after_evidence_change"
            ),
        },
        "optional_transport_unconfigured": {
            "automatic_retry_allowed": False,
            "maximum_attempts": 0,
            "backoff_seconds": None,
            "circuit_breaker_after_attempts": 0,
            "next_action": "retain_local_projection_and_report_transport_hold",
        },
    }
    policy = policies.get(
        failure_class,
        {
            "automatic_retry_allowed": False,
            "maximum_attempts": 0,
            "backoff_seconds": None,
            "circuit_breaker_after_attempts": 0,
            "next_action": (
                "stop_affected_work_and_require_safety_review"
                if failure_class == "safety_violation"
                else "write_specific_repair_request"
            ),
        },
    )
    return {
        "failure_class": failure_class,
        "attempt_count": attempt_count,
        "safe_idempotent_operations_only": True,
        "paperops_retry_allowed": False,
        "broker_write_retry_allowed": False,
        "code_edit_allowed": False,
        "secret_change_allowed": False,
        "authority_change_allowed": False,
        **policy,
    }
