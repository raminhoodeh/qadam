#!/usr/bin/env python3
"""Validate Q-CTRL readiness without calling Q-CTRL."""

from __future__ import annotations

import argparse
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
    qctrl_readiness,
    validate_qctrl_readiness,
)

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
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--live-qctrl-readiness",
        action="store_true",
        help="Reserved guard for a future explicit live metadata-only probe.",
    )
    args = parser.parse_args()

    if args.live_qctrl_readiness:
        print("qctrl_live_readiness_probe_requested=true")
        print("qctrl_live_readiness_probe_status=not_implemented_no_provider_call")
        return 2

    readiness = qctrl_readiness(Settings.from_env())
    validate_qctrl_readiness(readiness)

    print("qctrl_readiness_status=" + str(readiness.get("status")))
    print(f"qctrl_readiness_schema_version={readiness.get('schema_version')}")
    print(f"qctrl_credential_configured={readiness.get('credential_configured')}")
    print(f"qctrl_sdk_package_importable={readiness.get('sdk_package_importable')}")
    print(f"qctrl_live_probe_enabled={readiness.get('live_probe_enabled')}")
    print(f"qctrl_live_probe_attempted={readiness.get('live_probe_attempted')}")
    print(f"qctrl_provider_call_allowed={readiness.get('provider_call_allowed')}")
    print(f"qctrl_provider_call_count={readiness.get('provider_call_count')}")
    print(f"qctrl_optimization_job_submission_allowed={readiness.get('optimization_job_submission_allowed')}")
    print(f"qctrl_optimization_job_submitted={readiness.get('optimization_job_submitted')}")
    print(f"qctrl_hardware_submission_allowed={readiness.get('hardware_submission_allowed')}")
    print(f"qctrl_hardware_job_submitted={readiness.get('hardware_job_submitted')}")
    print(f"qctrl_hardware_scheduler_enabled={readiness.get('hardware_scheduler_enabled')}")
    print(f"qctrl_recommendation_authority={readiness.get('recommendation_authority')}")
    print(f"qctrl_execution_allowed={readiness.get('execution_allowed')}")
    print(f"qctrl_paper_order_allowed={readiness.get('paper_order_allowed')}")
    print(f"qctrl_trade_candidate_authority={readiness.get('trade_candidate_authority')}")
    print(f"qctrl_secret_value_exposed={readiness.get('secret_value_exposed')}")
    print(f"qctrl_raw_response_exposed={readiness.get('raw_response_exposed')}")

    missing = sorted(REQUIRED_QCTRL_READINESS_FIELDS - set(readiness))
    if missing:
        print("qctrl_readiness_fields_missing=" + ",".join(missing))
        return 1
    if readiness.get("schema_version") != QCTRL_READINESS_SCHEMA_VERSION:
        print("qctrl_readiness_schema_mismatch=true")
        return 1
    if readiness.get("status") not in QCTRL_READINESS_ALLOWED_STATUSES:
        print("qctrl_readiness_status_invalid=true")
        return 1
    if readiness.get("credential_configured") is not True:
        print("qctrl_credential_missing=true")
        return 1
    if readiness.get("hardware_backend_role") != "not_hardware_backend":
        print("qctrl_hardware_backend_role_invalid=true")
        return 1
    if readiness.get("default_mode") != "metadata_only_no_provider_call":
        print("qctrl_default_mode_invalid=true")
        return 1
    if readiness.get("live_probe_required_flag") != "--live-qctrl-readiness":
        print("qctrl_live_probe_flag_missing=true")
        return 1
    if readiness.get("provider_call_count") != 0:
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
        if readiness.get(key) is not False:
            print(f"qctrl_readiness_flag_not_false={key}")
            return 1
    if _contains_secret_shape(readiness):
        print("qctrl_readiness_secret_shape_exposed=true")
        return 1

    print("qctrl_readiness_check=ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
