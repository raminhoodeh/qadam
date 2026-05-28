#!/usr/bin/env python3
"""Validate the Fire Opal + IBM Quantum readiness path.

Default mode is public-safe and provider-call-free. Use --probe-devices only
after Fire Opal product access, IBM Quantum token/instance, and local runtime
packages are configured.
"""

from __future__ import annotations

import argparse
import re
import signal
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from orchestrator.config import Settings  # noqa: E402
from orchestrator.quantum import (  # noqa: E402
    FIRE_OPAL_IBM_ALLOWED_STATUSES,
    QCTRL_FIRE_OPAL_IBM_READINESS_SCHEMA_VERSION,
    qctrl_fire_opal_ibm_readiness,
    validate_qctrl_fire_opal_ibm_readiness,
    write_qctrl_fire_opal_ibm_readiness,
)


PROHIBITED_VALUE_PATTERNS = (
    re.compile(r"ghp_[A-Za-z0-9_]{20,}"),
    re.compile(r"vcp_[A-Za-z0-9_]{20,}"),
    re.compile(r"AIza[0-9A-Za-z_-]{20,}"),
    re.compile(r"sb_secret_[0-9A-Za-z_-]{12,}"),
    re.compile(r"sk-[A-Za-z0-9_-]{20,}"),
    re.compile(r"pref_agent_[0-9A-Za-z_-]{12,}"),
    re.compile(r"[0-9]{6,}:[A-Za-z0-9_-]{20,}"),
)


def _contains_secret_shape(value: object) -> bool:
    return any(pattern.search(str(value)) for pattern in PROHIBITED_VALUE_PATTERNS)


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--probe-devices",
        action="store_true",
        help="Explicitly call Fire Opal to discover IBM Quantum devices; never submits jobs.",
    )
    parser.add_argument(
        "--probe-timeout-seconds",
        type=int,
        default=45,
        help="Maximum wall-clock seconds for the explicit provider device probe.",
    )
    return parser.parse_args()


def _timeout(_signum: int, _frame: object) -> None:
    raise TimeoutError("fire_opal_ibm_provider_probe_timeout")


def main() -> int:
    args = _parse_args()
    settings = Settings.from_env()
    if args.probe_devices:
        signal.signal(signal.SIGALRM, _timeout)
        signal.alarm(max(1, args.probe_timeout_seconds))
    try:
        readiness = qctrl_fire_opal_ibm_readiness(
            settings,
            probe_devices=args.probe_devices,
        )
    except TimeoutError:
        readiness = qctrl_fire_opal_ibm_readiness(settings, probe_devices=False)
        readiness.update(
            {
                "status": "blocked_provider_probe_failed",
                "provider_device_probe_requested": True,
                "provider_call_attempted": True,
                "provider_call_succeeded": False,
                "provider_call_count": 1,
                "provider_failure_category": "provider_probe_timeout",
                "provider_failure_class": "TimeoutError",
                "blocker": "provider_probe_timeout",
                "next_required_action": (
                    "Retry the explicit read-only device probe after the IBM/FIRE Opal "
                    "provider call path responds within the timeout."
                ),
            }
        )
    finally:
        if args.probe_devices:
            signal.alarm(0)
    validate_qctrl_fire_opal_ibm_readiness(readiness)
    if args.probe_devices:
        write_qctrl_fire_opal_ibm_readiness(readiness, settings)

    print(f"fire_opal_ibm_readiness_status={readiness.get('status')}")
    print(
        "fire_opal_ibm_readiness_schema_version="
        f"{readiness.get('schema_version')}"
    )
    print(
        "fire_opal_ibm_qctrl_organization_slug_configured="
        f"{readiness.get('qctrl_organization_slug_configured')}"
    )
    print(
        "fire_opal_ibm_fire_opal_product_access_verified="
        f"{readiness.get('fire_opal_product_access_verified')}"
    )
    print(
        "fire_opal_ibm_qctrl_product_access_status="
        f"{readiness.get('qctrl_product_access_status')}"
    )
    print(
        "fire_opal_ibm_qctrl_provider_call_succeeded="
        f"{readiness.get('qctrl_provider_call_succeeded')}"
    )
    print(
        "fire_opal_ibm_fire_opal_sdk_importable="
        f"{readiness.get('fire_opal_sdk_importable')}"
    )
    print(
        "fire_opal_ibm_qiskit_ibm_runtime_importable="
        f"{readiness.get('qiskit_ibm_runtime_importable')}"
    )
    print(f"fire_opal_ibm_qiskit_importable={readiness.get('qiskit_importable')}")
    print(
        "fire_opal_ibm_ibm_quantum_token_configured="
        f"{readiness.get('ibm_quantum_token_configured')}"
    )
    print(
        "fire_opal_ibm_ibm_quantum_instance_configured="
        f"{readiness.get('ibm_quantum_instance_configured')}"
    )
    print(
        "fire_opal_ibm_device_probe_requested="
        f"{readiness.get('provider_device_probe_requested')}"
    )
    print(
        "fire_opal_ibm_device_probe_allowed="
        f"{readiness.get('provider_device_probe_allowed')}"
    )
    print(
        "fire_opal_ibm_provider_call_attempted="
        f"{readiness.get('provider_call_attempted')}"
    )
    print(
        "fire_opal_ibm_provider_call_succeeded="
        f"{readiness.get('provider_call_succeeded')}"
    )
    print(f"fire_opal_ibm_provider_call_count={readiness.get('provider_call_count')}")
    print(
        "fire_opal_ibm_provider_failure_category="
        f"{readiness.get('provider_failure_category')}"
    )
    print(f"fire_opal_ibm_supported_device_count={readiness.get('supported_device_count')}")
    print(f"fire_opal_ibm_blocker={readiness.get('blocker')}")
    print(
        "fire_opal_ibm_hardware_submission_allowed="
        f"{readiness.get('hardware_submission_allowed')}"
    )
    print(
        "fire_opal_ibm_hardware_job_submitted="
        f"{readiness.get('hardware_job_submitted')}"
    )
    print(
        "fire_opal_ibm_hardware_scheduler_enabled="
        f"{readiness.get('hardware_scheduler_enabled')}"
    )
    print(f"fire_opal_ibm_execution_allowed={readiness.get('execution_allowed')}")
    print(f"fire_opal_ibm_paper_order_allowed={readiness.get('paper_order_allowed')}")
    print(f"fire_opal_ibm_secret_value_exposed={readiness.get('secret_value_exposed')}")
    print(
        "fire_opal_ibm_raw_provider_response_persisted="
        f"{readiness.get('raw_provider_response_persisted')}"
    )

    if readiness.get("schema_version") != QCTRL_FIRE_OPAL_IBM_READINESS_SCHEMA_VERSION:
        print("fire_opal_ibm_schema_mismatch=true")
        return 1
    if readiness.get("status") not in FIRE_OPAL_IBM_ALLOWED_STATUSES:
        print("fire_opal_ibm_status_invalid=true")
        return 1
    if readiness.get("qctrl_organization_slug_configured") is not True:
        print("fire_opal_ibm_qctrl_organization_slug_missing=true")
        return 1
    if readiness.get("fire_opal_sdk_importable") is not True:
        print("fire_opal_ibm_fire_opal_sdk_missing=true")
        return 1
    if readiness.get("fire_opal_product_access_verified") is not True:
        print("fire_opal_ibm_fire_opal_access_not_verified=true")
        return 1
    if (
        readiness.get("provider_call_attempted") is True
        and readiness.get("provider_device_probe_requested") is not True
    ):
        print("fire_opal_ibm_provider_call_without_explicit_probe=true")
        return 1
    for key in (
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
    ):
        if readiness.get(key) is not False:
            print(f"fire_opal_ibm_forbidden_flag={key}")
            return 1
    if _contains_secret_shape(readiness):
        print("fire_opal_ibm_secret_shape_exposed=true")
        return 1

    print("qctrl_fire_opal_ibm_quantum_check=ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
