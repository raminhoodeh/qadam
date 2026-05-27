#!/usr/bin/env python3
"""Validate the PaperOps-Q Q-CTRL paper consultation gate."""

from __future__ import annotations

from copy import deepcopy
from dataclasses import replace
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from orchestrator.config import Settings  # noqa: E402
from orchestrator.event_log import EventLog  # noqa: E402
from orchestrator.paperops_qctrl_consultation import (  # noqa: E402
    PAPEROPS_QCTRL_CONSULTATION_SCHEMA_VERSION,
    build_paperops_qctrl_consultation,
    read_latest_paperops_qctrl_consultation,
    validate_paperops_qctrl_consultation,
    write_paperops_qctrl_consultation,
)


def main() -> int:
    errors: list[str] = []
    settings = Settings.from_env()
    existing = read_latest_paperops_qctrl_consultation(settings)
    preserve_recorded_consultation = (
        settings.qctrl_paper_consultation_enabled is False
        and existing.get("status") == "consultation_recorded"
        and existing.get("provider_call_succeeded") is True
        and existing.get("qctrl_paper_consultation_enabled") is True
    )
    artifact = (
        existing
        if preserve_recorded_consultation
        else build_paperops_qctrl_consultation(settings)
    )
    output_path, history_path, event_path, written = write_paperops_qctrl_consultation(
        artifact,
        settings,
    )
    validation_errors = validate_paperops_qctrl_consultation(written)
    replay = EventLog(event_path, echo=False).replay()

    live_mode_probe = deepcopy(written)
    live_mode_probe["mode"] = "live"
    live_mode_errors = validate_paperops_qctrl_consultation(live_mode_probe)

    live_capital_probe = deepcopy(written)
    live_capital_probe["live_capital_enabled"] = True
    live_capital_errors = validate_paperops_qctrl_consultation(live_capital_probe)

    no_flag_provider_probe = deepcopy(written)
    no_flag_provider_probe["qctrl_paper_consultation_enabled"] = False
    no_flag_provider_probe["provider_call_count"] = 1
    no_flag_provider_errors = validate_paperops_qctrl_consultation(no_flag_provider_probe)

    authority_probe = deepcopy(written)
    authority_probe["execution_allowed"] = True
    authority_probe["paper_order_allowed"] = True
    authority_probe["broker_post_allowed"] = True
    authority_errors = validate_paperops_qctrl_consultation(authority_probe)

    head_note_probe = deepcopy(written)
    head_note_probe["head_of_quant_note"]["counts_as_execution_truth"] = True
    head_note_errors = validate_paperops_qctrl_consultation(head_note_probe)

    secret_probe = deepcopy(written)
    secret_probe["provider_failure_class"] = "sk-thisShouldNeverAppear1234567890"
    secret_errors = validate_paperops_qctrl_consultation(secret_probe)

    event_probe = deepcopy(written)
    event_probe["event_log_written"] = False
    event_probe["event_log_event_count"] = 0
    event_errors = validate_paperops_qctrl_consultation(event_probe)

    enabled_settings = replace(settings, qctrl_paper_consultation_enabled=True)
    enabled_preview = build_paperops_qctrl_consultation(
        enabled_settings,
        allow_provider_call=False,
    )

    print(f"paperops_qctrl_status={written['status']}")
    print(f"paperops_qctrl_schema_version={PAPEROPS_QCTRL_CONSULTATION_SCHEMA_VERSION}")
    print(f"paperops_qctrl_artifact_path={output_path}")
    print(f"paperops_qctrl_history_path={history_path}")
    print(f"paperops_qctrl_event_log_path={event_path}")
    print(f"paperops_qctrl_enabled={written['qctrl_paper_consultation_enabled']}")
    print(f"paperops_qctrl_readiness_status={written['qctrl_readiness_status']}")
    print(f"paperops_qctrl_credential_configured={written['qctrl_credential_configured']}")
    print(
        "paperops_qctrl_fire_opal_product_required="
        f"{written['qctrl_fire_opal_product_required']}"
    )
    print(
        "paperops_qctrl_organization_slug_configured="
        f"{written['qctrl_organization_slug_configured']}"
    )
    print(
        "paperops_qctrl_organization_config_applied="
        f"{written['qctrl_organization_config_applied']}"
    )
    print(f"paperops_qctrl_sdk_package_importable={written['qctrl_sdk_package_importable']}")
    print(f"paperops_qctrl_sdk_module_selected={written['qctrl_sdk_module_selected']}")
    print(f"paperops_qctrl_provider_call_allowed={written['provider_call_allowed']}")
    print(f"paperops_qctrl_provider_call_attempted={written['provider_call_attempted']}")
    print(f"paperops_qctrl_provider_call_succeeded={written['provider_call_succeeded']}")
    print(f"paperops_qctrl_provider_call_count={written['provider_call_count']}")
    print(f"paperops_qctrl_auth_status={written['qctrl_auth_status']}")
    print(f"paperops_qctrl_provider_failure_category={written['provider_failure_category']}")
    print(
        "paperops_qctrl_head_of_quant_note_status="
        f"{written['head_of_quant_note']['status']}"
    )
    print(f"paperops_qctrl_execution_allowed={written['execution_allowed']}")
    print(f"paperops_qctrl_paper_order_allowed={written['paper_order_allowed']}")
    print(f"paperops_qctrl_broker_post_allowed={written['broker_post_allowed']}")
    print(f"paperops_qctrl_secret_value_exposed={written['secret_value_exposed']}")
    print(f"paperops_qctrl_raw_response_exposed={written['raw_response_exposed']}")
    print(f"paperops_qctrl_event_log_events={replay['total_events']}")
    print(
        "paperops_qctrl_preserved_recorded_consultation="
        f"{preserve_recorded_consultation}"
    )
    print(f"paperops_qctrl_enabled_preview_status={enabled_preview['status']}")
    print(
        "paperops_qctrl_enabled_preview_provider_call_allowed="
        f"{enabled_preview['provider_call_allowed']}"
    )
    print(
        "paperops_qctrl_enabled_preview_provider_call_count="
        f"{enabled_preview['provider_call_count']}"
    )
    print(f"paperops_qctrl_validation_errors={validation_errors}")

    if validation_errors:
        errors.append(f"PaperOps-Q validation failed: {validation_errors}")
    if replay["total_events"] < 1 or written["event_log_event_count"] != 1:
        errors.append("PaperOps-Q event log did not record the current event")
    if written["mode"] != "paper":
        errors.append("PaperOps-Q current mode is not paper")
    if written["live_capital_enabled"] is not False:
        errors.append("PaperOps-Q enables live capital")
    if written["qctrl_credential_configured"] is not True:
        errors.append("PaperOps-Q does not see the configured Q-CTRL credential")
    if written["qctrl_fire_opal_product_required"] is not True:
        errors.append("PaperOps-Q does not require Fire Opal for quantum parity")
    if (
        settings.qctrl_paper_consultation_enabled is False
        and written["qctrl_paper_consultation_enabled"] is False
    ):
        if written["status"] != "disabled_pending_enablement":
            errors.append("PaperOps-Q should stay disabled pending explicit enablement")
        if written["provider_call_count"] != 0:
            errors.append("PaperOps-Q called provider while disabled")
    if written["provider_call_succeeded"] is True and written["provider_call_count"] < 1:
        errors.append("PaperOps-Q succeeded without recording a provider call")
    for key in (
        "execution_allowed",
        "paper_order_allowed",
        "broker_post_allowed",
        "alpaca_post_allowed",
        "live_endpoint_allowed",
        "live_capital_enabled",
        "secret_value_exposed",
        "raw_response_exposed",
    ):
        if written[key] is not False:
            errors.append(f"PaperOps-Q unsafe flag is enabled: {key}")
    if enabled_preview["qctrl_paper_consultation_enabled"] is not True:
        errors.append("PaperOps-Q enabled preview did not set the explicit flag")
    if enabled_preview["provider_call_count"] != 0:
        errors.append("PaperOps-Q enabled preview called provider despite allow_provider_call=False")
    if "paperops_qctrl_mode_not_paper" not in live_mode_errors:
        errors.append("live-mode probe was not rejected")
    if "paperops_qctrl_forbidden:live_capital_enabled" not in live_capital_errors:
        errors.append("live-capital probe was not rejected")
    if "paperops_qctrl_provider_call_without_flag" not in no_flag_provider_errors:
        errors.append("provider-call-without-flag probe was not rejected")
    if "paperops_qctrl_forbidden:execution_allowed" not in authority_errors:
        errors.append("execution-authority probe was not rejected")
    if "paperops_qctrl_head_note_forbidden:counts_as_execution_truth" not in head_note_errors:
        errors.append("Head of Quant note authority probe was not rejected")
    if "paperops_qctrl_secret_shape_exposed" not in secret_errors:
        errors.append("secret-shape probe was not rejected")
    if "paperops_qctrl_event_log_missing" not in event_errors:
        errors.append("missing-event-log probe was not rejected")

    if errors:
        print("paperops_qctrl_consultation_check=failed")
        for error in errors:
            print(f"error={error}")
        return 1
    print("paperops_qctrl_consultation_check=ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
