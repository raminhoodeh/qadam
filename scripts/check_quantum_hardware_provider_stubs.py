#!/usr/bin/env python3
"""Validate IBM Quantum and AWS Braket hardware provider stubs without provider calls."""

from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from orchestrator.config import Settings  # noqa: E402
from orchestrator.quantum import (  # noqa: E402
    QUANTUM_HARDWARE_PROVIDER_ALLOWED_STATUSES,
    QUANTUM_HARDWARE_PROVIDER_KEYS,
    QUANTUM_HARDWARE_PROVIDER_STUB_SCHEMA_VERSION,
    quantum_hardware_provider_stubs,
    validate_quantum_hardware_provider_stubs,
)

REQUIRED_LEDGER_FIELDS = {
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

REQUIRED_PROVIDER_FIELDS = {
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
    ledger = quantum_hardware_provider_stubs(Settings.from_env())
    validate_quantum_hardware_provider_stubs(ledger)
    providers = ledger.get("providers", [])

    print("quantum_hardware_provider_stubs_status=" + str(ledger.get("status")))
    print(f"quantum_hardware_provider_stubs_schema_version={ledger.get('schema_version')}")
    print(f"quantum_hardware_provider_count={ledger.get('provider_count')}")
    print(f"quantum_hardware_provider_expected_count={ledger.get('expected_provider_count')}")
    print(f"quantum_hardware_provider_missing_credentials_count={ledger.get('missing_credentials_count')}")
    print(f"quantum_hardware_provider_configured_policy_blocked_count={ledger.get('configured_policy_blocked_count')}")
    print(f"quantum_hardware_provider_credential_configured_count={ledger.get('credential_configured_count')}")
    print(f"quantum_hardware_provider_local_validation={ledger.get('local_simulator_validation_passed')}")
    print(
        "quantum_hardware_provider_policy_approval="
        f"{ledger.get('explicit_hardware_policy_approval_present')}"
    )
    print(f"quantum_hardware_provider_call_allowed_count={ledger.get('provider_call_allowed_count')}")
    print(f"quantum_hardware_submission_allowed_count={ledger.get('hardware_submission_allowed_count')}")
    print(f"quantum_hardware_submitted_count={ledger.get('hardware_submitted_count')}")
    print(f"quantum_hardware_scheduler_enabled_count={ledger.get('hardware_scheduler_enabled_count')}")
    print(f"quantum_hardware_execution_allowed_count={ledger.get('execution_allowed_count')}")
    print(f"quantum_hardware_paper_order_allowed_count={ledger.get('paper_order_allowed_count')}")
    print(f"quantum_hardware_trade_candidate_authority_count={ledger.get('trade_candidate_authority_count')}")
    print(f"quantum_hardware_secret_value_exposed_count={ledger.get('secret_value_exposed_count')}")
    print(f"quantum_hardware_raw_response_exposed_count={ledger.get('raw_response_exposed_count')}")

    missing_ledger_fields = sorted(REQUIRED_LEDGER_FIELDS - set(ledger))
    if missing_ledger_fields:
        print("quantum_hardware_provider_stubs_fields_missing=" + ",".join(missing_ledger_fields))
        return 1
    if ledger.get("schema_version") != QUANTUM_HARDWARE_PROVIDER_STUB_SCHEMA_VERSION:
        print("quantum_hardware_provider_stubs_schema_mismatch=true")
        return 1
    if ledger.get("provider_count") != len(QUANTUM_HARDWARE_PROVIDER_KEYS):
        print("quantum_hardware_provider_count_mismatch=true")
        return 1
    if ledger.get("expected_provider_count") != len(QUANTUM_HARDWARE_PROVIDER_KEYS):
        print("quantum_hardware_provider_expected_count_mismatch=true")
        return 1
    if ledger.get("explicit_hardware_policy_approval_present") is not False:
        print("quantum_hardware_policy_approval_present=true")
        return 1
    if ledger.get("local_simulator_validation_passed") is not True:
        print("quantum_hardware_local_simulator_validation_missing=true")
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
        if ledger.get(key) != 0:
            print(f"quantum_hardware_provider_stubs_nonzero={key}")
            return 1

    provider_keys = {str(provider.get("key")) for provider in providers if isinstance(provider, dict)}
    if provider_keys != QUANTUM_HARDWARE_PROVIDER_KEYS:
        print("quantum_hardware_provider_keys_mismatch=true")
        return 1
    for provider in providers:
        if not isinstance(provider, dict):
            print("quantum_hardware_provider_row_invalid=true")
            return 1
        key = provider.get("key")
        print(
            "quantum_hardware_provider="
            f"{key},{provider.get('status')},credential_configured={provider.get('credential_configured')},"
            f"policy_approval={provider.get('explicit_hardware_policy_approval_present')},"
            f"hardware_submission_allowed={provider.get('hardware_submission_allowed')}"
        )
        missing_provider_fields = sorted(REQUIRED_PROVIDER_FIELDS - set(provider))
        if missing_provider_fields:
            print(f"quantum_hardware_provider_fields_missing={key}:{','.join(missing_provider_fields)}")
            return 1
        if provider.get("status") not in QUANTUM_HARDWARE_PROVIDER_ALLOWED_STATUSES:
            print(f"quantum_hardware_provider_status_invalid={key}")
            return 1
        if provider.get("public_safe") is not True:
            print(f"quantum_hardware_provider_not_public_safe={key}")
            return 1
        if provider.get("policy_block_reason") != "explicit_hardware_policy_approval_missing":
            print(f"quantum_hardware_provider_policy_block_reason_invalid={key}")
            return 1
        if "credential_key" in provider:
            print(f"quantum_hardware_provider_exposes_credential_key={key}")
            return 1
        if _contains_secret_shape(provider):
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
            if provider.get(flag) is not False:
                print(f"quantum_hardware_provider_flag_not_false={key}:{flag}")
                return 1

    print("quantum_hardware_provider_stubs_check=ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
