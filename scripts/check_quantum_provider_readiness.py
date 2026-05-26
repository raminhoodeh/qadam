#!/usr/bin/env python3
"""Validate the Phase 3 quantum provider-readiness ledger.

This check is intentionally status-only. It must not call Q-CTRL, IBM Quantum,
AWS Braket, Qiskit Runtime, brokers, order routers, or live-capital code.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from orchestrator.config import Settings  # noqa: E402
from orchestrator.quantum import (  # noqa: E402
    QCTRL_READINESS_ALLOWED_STATUSES,
    QCTRL_READINESS_SCHEMA_VERSION,
    QUANTUM_HARDWARE_PROVIDER_ALLOWED_STATUSES,
    QUANTUM_HARDWARE_PROVIDER_KEYS,
    QUANTUM_HARDWARE_PROVIDER_STUB_SCHEMA_VERSION,
    QUANTUM_PROVIDER_ALLOWED_STATUSES,
    QUANTUM_PROVIDER_KEYS,
    QUANTUM_PROVIDER_READINESS_SCHEMA_VERSION,
    quantum_provider_readiness,
    validate_quantum_provider_readiness,
)

REQUIRED_LEDGER_FIELDS = {
    "available_without_secret_count",
    "boundary",
    "by_status",
    "configured_count",
    "disabled_by_policy_count",
    "execution_allowed_count",
    "expected_provider_count",
    "hardware_provider_stubs",
    "hardware_scheduler_enabled_count",
    "hardware_submission_allowed_count",
    "missing_optional_package_count",
    "missing_secret_count",
    "paper_order_allowed_count",
    "provider_call_allowed_count",
    "provider_count",
    "providers",
    "public_safe",
    "qctrl_configured",
    "qctrl_readiness",
    "raw_response_exposed_count",
    "schema_version",
    "secret_value_exposed_count",
    "status",
    "trade_candidate_authority_count",
}

REQUIRED_PROVIDER_FIELDS = {
    "boundary",
    "credential_configured",
    "execution_allowed",
    "hardware_scheduler_enabled",
    "hardware_submission_allowed",
    "key",
    "name",
    "notes",
    "paper_order_allowed",
    "provider_call_allowed",
    "public_safe",
    "raw_response_exposed",
    "role",
    "schema_version",
    "secret_value_exposed",
    "status",
    "trade_candidate_authority",
}

REQUIRED_HARDWARE_STUB_LEDGER_FIELDS = {
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

REQUIRED_HARDWARE_STUB_PROVIDER_FIELDS = {
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

REQUIRED_QCTRL_READINESS_FIELDS = {
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

PROHIBITED_VALUE_PATTERNS = (
    re.compile(r"ghp_[A-Za-z0-9_]{20,}"),
    re.compile(r"vcp_[A-Za-z0-9_]{20,}"),
    re.compile(r"AIza[0-9A-Za-z_-]{20,}"),
    re.compile(r"sb_secret_[0-9A-Za-z_-]{12,}"),
    re.compile(r"sk-[A-Za-z0-9_-]{20,}"),
    re.compile(r"[0-9]{6,}:[A-Za-z0-9_-]{20,}"),
)


def _contains_secret_shape(value: object) -> bool:
    text = str(value)
    return any(pattern.search(text) for pattern in PROHIBITED_VALUE_PATTERNS)


def main() -> int:
    settings = Settings.from_env()
    ledger = quantum_provider_readiness(settings)
    validate_quantum_provider_readiness(ledger)
    providers = ledger.get("providers", [])

    print("quantum_provider_readiness_status=" + str(ledger.get("status")))
    print(f"quantum_provider_readiness_schema_version={ledger.get('schema_version')}")
    print(f"quantum_provider_count={ledger.get('provider_count')}")
    print(f"quantum_provider_expected_count={ledger.get('expected_provider_count')}")
    print(f"quantum_provider_configured_count={ledger.get('configured_count')}")
    print(f"quantum_provider_missing_secret_count={ledger.get('missing_secret_count')}")
    print(f"quantum_provider_missing_optional_package_count={ledger.get('missing_optional_package_count')}")
    print(f"quantum_provider_qctrl_configured={ledger.get('qctrl_configured')}")
    print(f"quantum_provider_call_allowed_count={ledger.get('provider_call_allowed_count')}")
    print(f"quantum_provider_hardware_submission_allowed_count={ledger.get('hardware_submission_allowed_count')}")
    print(f"quantum_provider_hardware_scheduler_enabled_count={ledger.get('hardware_scheduler_enabled_count')}")
    print(f"quantum_provider_execution_allowed_count={ledger.get('execution_allowed_count')}")
    print(f"quantum_provider_paper_order_allowed_count={ledger.get('paper_order_allowed_count')}")
    print(f"quantum_provider_trade_candidate_authority_count={ledger.get('trade_candidate_authority_count')}")
    print(f"quantum_provider_secret_value_exposed_count={ledger.get('secret_value_exposed_count')}")
    print(f"quantum_provider_raw_response_exposed_count={ledger.get('raw_response_exposed_count')}")
    qctrl = ledger.get("qctrl_readiness", {})
    hardware_stubs = ledger.get("hardware_provider_stubs", {})
    if isinstance(qctrl, dict):
        print(f"qctrl_readiness_status={qctrl.get('status')}")
        print(f"qctrl_credential_configured={qctrl.get('credential_configured')}")
        print(f"qctrl_sdk_package_importable={qctrl.get('sdk_package_importable')}")
        print(f"qctrl_live_probe_enabled={qctrl.get('live_probe_enabled')}")
        print(f"qctrl_provider_call_count={qctrl.get('provider_call_count')}")
        print(f"qctrl_optimization_job_submitted={qctrl.get('optimization_job_submitted')}")
    if isinstance(hardware_stubs, dict):
        print(f"quantum_hardware_provider_stubs_status={hardware_stubs.get('status')}")
        print(f"quantum_hardware_provider_count={hardware_stubs.get('provider_count')}")
        print(
            "quantum_hardware_provider_missing_credentials_count="
            f"{hardware_stubs.get('missing_credentials_count')}"
        )
        print(
            "quantum_hardware_provider_configured_policy_blocked_count="
            f"{hardware_stubs.get('configured_policy_blocked_count')}"
        )
        print(
            "quantum_hardware_submission_allowed_count="
            f"{hardware_stubs.get('hardware_submission_allowed_count')}"
        )
        print(f"quantum_hardware_submitted_count={hardware_stubs.get('hardware_submitted_count')}")

    missing_ledger_fields = sorted(REQUIRED_LEDGER_FIELDS - set(ledger))
    if missing_ledger_fields:
        print("quantum_provider_readiness_fields_missing=" + ",".join(missing_ledger_fields))
        return 1
    if ledger.get("schema_version") != QUANTUM_PROVIDER_READINESS_SCHEMA_VERSION:
        print("quantum_provider_readiness_schema_mismatch=true")
        return 1
    if ledger.get("provider_count") != len(QUANTUM_PROVIDER_KEYS):
        print("quantum_provider_count_mismatch=true")
        return 1
    if ledger.get("expected_provider_count") != len(QUANTUM_PROVIDER_KEYS):
        print("quantum_provider_expected_count_mismatch=true")
        return 1
    if ledger.get("qctrl_configured") is not True:
        print("quantum_provider_qctrl_not_configured=true")
        return 1
    if not isinstance(qctrl, dict):
        print("qctrl_readiness_invalid=true")
        return 1
    missing_qctrl_fields = sorted(REQUIRED_QCTRL_READINESS_FIELDS - set(qctrl))
    if missing_qctrl_fields:
        print("qctrl_readiness_fields_missing=" + ",".join(missing_qctrl_fields))
        return 1
    if qctrl.get("schema_version") != QCTRL_READINESS_SCHEMA_VERSION:
        print("qctrl_readiness_schema_mismatch=true")
        return 1
    if qctrl.get("status") not in QCTRL_READINESS_ALLOWED_STATUSES:
        print("qctrl_readiness_status_invalid=true")
        return 1
    if qctrl.get("credential_configured") is not True:
        print("qctrl_credential_missing=true")
        return 1
    if qctrl.get("hardware_backend_role") != "not_hardware_backend":
        print("qctrl_hardware_backend_role_invalid=true")
        return 1
    if qctrl.get("live_probe_required_flag") != "--live-qctrl-readiness":
        print("qctrl_live_probe_flag_missing=true")
        return 1
    if qctrl.get("provider_call_count") != 0:
        print("qctrl_provider_call_count_nonzero=true")
        return 1
    for key in (
        "live_probe_enabled",
        "live_probe_attempted",
        "provider_call_allowed",
        "optimization_job_submission_allowed",
        "optimization_job_submitted",
        "hardware_submission_allowed",
        "hardware_job_submitted",
        "hardware_scheduler_enabled",
        "recommendation_authority",
        "execution_allowed",
        "paper_order_allowed",
        "trade_candidate_authority",
        "secret_value_exposed",
        "raw_response_exposed",
    ):
        if qctrl.get(key) is not False:
            print(f"qctrl_readiness_flag_not_false={key}")
            return 1
    if _contains_secret_shape(qctrl):
        print("qctrl_readiness_secret_shape_exposed=true")
        return 1
    if ledger.get("public_safe") is not True:
        print("quantum_provider_readiness_not_public_safe=true")
        return 1
    if not isinstance(hardware_stubs, dict):
        print("quantum_hardware_provider_stubs_invalid=true")
        return 1
    missing_hardware_fields = sorted(REQUIRED_HARDWARE_STUB_LEDGER_FIELDS - set(hardware_stubs))
    if missing_hardware_fields:
        print("quantum_hardware_provider_stubs_fields_missing=" + ",".join(missing_hardware_fields))
        return 1
    if hardware_stubs.get("schema_version") != QUANTUM_HARDWARE_PROVIDER_STUB_SCHEMA_VERSION:
        print("quantum_hardware_provider_stubs_schema_mismatch=true")
        return 1
    if hardware_stubs.get("provider_count") != len(QUANTUM_HARDWARE_PROVIDER_KEYS):
        print("quantum_hardware_provider_count_mismatch=true")
        return 1
    if hardware_stubs.get("expected_provider_count") != len(QUANTUM_HARDWARE_PROVIDER_KEYS):
        print("quantum_hardware_provider_expected_count_mismatch=true")
        return 1
    if hardware_stubs.get("explicit_hardware_policy_approval_present") is not False:
        print("quantum_hardware_policy_approval_present=true")
        return 1
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
        if hardware_stubs.get(key) != 0:
            print(f"quantum_hardware_provider_stubs_nonzero={key}")
            return 1
    hardware_provider_rows = hardware_stubs.get("providers", [])
    if not isinstance(hardware_provider_rows, list):
        print("quantum_hardware_provider_list_invalid=true")
        return 1
    hardware_provider_keys = {
        str(provider.get("key")) for provider in hardware_provider_rows if isinstance(provider, dict)
    }
    if hardware_provider_keys != QUANTUM_HARDWARE_PROVIDER_KEYS:
        print("quantum_hardware_provider_keys_mismatch=true")
        return 1
    for hardware_provider in hardware_provider_rows:
        if not isinstance(hardware_provider, dict):
            print("quantum_hardware_provider_row_invalid=true")
            return 1
        key = hardware_provider.get("key")
        missing_provider_fields = sorted(REQUIRED_HARDWARE_STUB_PROVIDER_FIELDS - set(hardware_provider))
        if missing_provider_fields:
            print(f"quantum_hardware_provider_fields_missing={key}:{','.join(missing_provider_fields)}")
            return 1
        if hardware_provider.get("status") not in QUANTUM_HARDWARE_PROVIDER_ALLOWED_STATUSES:
            print(f"quantum_hardware_provider_status_invalid={key}")
            return 1
        if hardware_provider.get("policy_block_reason") != "explicit_hardware_policy_approval_missing":
            print(f"quantum_hardware_provider_policy_block_reason_invalid={key}")
            return 1
        if "credential_key" in hardware_provider:
            print(f"quantum_hardware_provider_exposes_credential_key={key}")
            return 1
        if _contains_secret_shape(hardware_provider):
            print(f"quantum_hardware_provider_secret_shape_exposed={key}")
            return 1
        for flag in (
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
        ):
            if hardware_provider.get(flag) is not False:
                print(f"quantum_hardware_provider_flag_not_false={key}:{flag}")
                return 1
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
            print(f"quantum_provider_readiness_nonzero={key}")
            return 1

    provider_keys = {str(provider.get("key")) for provider in providers if isinstance(provider, dict)}
    if provider_keys != QUANTUM_PROVIDER_KEYS:
        print("quantum_provider_keys_mismatch=true")
        return 1
    for provider in providers:
        if not isinstance(provider, dict):
            print("quantum_provider_row_invalid=true")
            return 1
        key = provider.get("key")
        print(
            "quantum_provider="
            f"{key},{provider.get('status')},credential_configured={provider.get('credential_configured')},"
            f"provider_call_allowed={provider.get('provider_call_allowed')},"
            f"hardware_submission_allowed={provider.get('hardware_submission_allowed')}"
        )
        missing_provider_fields = sorted(REQUIRED_PROVIDER_FIELDS - set(provider))
        if missing_provider_fields:
            print(f"quantum_provider_fields_missing={key}:{','.join(missing_provider_fields)}")
            return 1
        if "credential_key" in provider:
            print(f"quantum_provider_exposes_credential_key={key}")
            return 1
        if provider.get("status") not in QUANTUM_PROVIDER_ALLOWED_STATUSES:
            print(f"quantum_provider_status_invalid={key}")
            return 1
        if provider.get("public_safe") is not True:
            print(f"quantum_provider_not_public_safe={key}")
            return 1
        if _contains_secret_shape(provider):
            print(f"quantum_provider_secret_shape_exposed={key}")
            return 1
        for flag in (
            "provider_call_allowed",
            "hardware_submission_allowed",
            "hardware_scheduler_enabled",
            "execution_allowed",
            "paper_order_allowed",
            "trade_candidate_authority",
            "secret_value_exposed",
            "raw_response_exposed",
        ):
            if provider.get(flag) is not False:
                print(f"quantum_provider_flag_not_false={key}:{flag}")
                return 1

    print("quantum_provider_readiness_check=ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
