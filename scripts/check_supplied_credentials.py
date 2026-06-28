#!/usr/bin/env python3
"""Validate supplied Qadam credentials without printing secret values.

This gate is intentionally read-only. It verifies credentials and local model
connectivity for the current Batch A foundation providers, while keeping Kalshi
deferred and UnusualWhales explicit as a missing useful key.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from orchestrator.adapters import (  # noqa: E402
    fetch_fred_live_sync,
    fetch_nasa_firms_live_sync,
)
from orchestrator.config import Settings  # noqa: E402
from orchestrator.event_log import EventLog  # noqa: E402
from orchestrator.intelligence import gemini_credential_probe, lm_studio_models_probe  # noqa: E402
from orchestrator.phase1_live_adapters import (  # noqa: E402
    fetch_phase1_live_adapter_live_sync,
    phase1_live_adapter_status,
)
from orchestrator.secrets import secret_status  # noqa: E402
from orchestrator.telegram_comms import TelegramCommunicationsStore  # noqa: E402


SECRET_LIKE_PATTERNS = (
    re.compile(r"\d{6,}:[A-Za-z0-9_-]{20,}"),
    re.compile(r"\bghp_[A-Za-z0-9]{20,}\b"),
    re.compile(r"\bvcp_[A-Za-z0-9]{20,}\b"),
    re.compile(r"\bAIza[0-9A-Za-z_-]{20,}\b"),
    re.compile(r"\bsb_secret_[0-9A-Za-z_-]{12,}\b"),
    re.compile(r"\b[A-Za-z0-9_-]{40,}\.[A-Za-z0-9_-]{20,}\.[A-Za-z0-9_-]{20,}\b"),
)


@dataclass(frozen=True)
class CredentialValidation:
    provider: str
    role: str
    credential_state: str
    validation_status: str
    live_called: bool
    event_count: int
    degraded_reason: str | None
    configured_secret_count: int
    required_secret_count: int
    checked_at: str
    boundary: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _configured_count(settings: Settings, keys: tuple[str, ...]) -> int:
    return sum(1 for key in keys if secret_status(key, settings).configured)


def _credential_state(settings: Settings, keys: tuple[str, ...], *, optional: bool = False) -> str:
    configured = _configured_count(settings, keys)
    if configured == len(keys):
        return "configured"
    if optional and configured:
        return "partially_configured_optional"
    if optional:
        return "optional_missing"
    return "missing"


def _status_from_envelope(
    provider: str,
    *,
    role: str,
    settings: Settings,
    keys: tuple[str, ...],
    fetcher: Callable[[], dict[str, Any]],
    checked_at: str,
    optional: bool = False,
) -> CredentialValidation:
    credential_state = _credential_state(settings, keys, optional=optional)
    configured_count = _configured_count(settings, keys)
    if credential_state == "missing":
        return CredentialValidation(
            provider=provider,
            role=role,
            credential_state=credential_state,
            validation_status="missing_credentials",
            live_called=False,
            event_count=0,
            degraded_reason="missing_credentials",
            configured_secret_count=configured_count,
            required_secret_count=len(keys),
            checked_at=checked_at,
            boundary="Credential missing. Provider cannot influence signals or execution.",
        )

    try:
        envelope = fetcher()
    except Exception as exc:  # noqa: BLE001 - validation must fail closed.
        return CredentialValidation(
            provider=provider,
            role=role,
            credential_state=credential_state,
            validation_status="degraded",
            live_called=True,
            event_count=0,
            degraded_reason=f"validation_error:{exc.__class__.__name__}",
            configured_secret_count=configured_count,
            required_secret_count=len(keys),
            checked_at=checked_at,
            boundary="Read-only provider validation failed closed. No execution authority.",
        )

    events = envelope.get("events", [])
    event_count = len(events) if isinstance(events, list) else 0
    degraded = bool(envelope.get("degraded"))
    return CredentialValidation(
        provider=provider,
        role=role,
        credential_state=credential_state,
        validation_status="degraded" if degraded else "live",
        live_called=True,
        event_count=event_count,
        degraded_reason=envelope.get("degraded_reason"),
        configured_secret_count=configured_count,
        required_secret_count=len(keys),
        checked_at=checked_at,
        boundary="Read-only provider validation only. No signal confidence, risk, or order authority.",
    )


def _phase1_provider(
    provider: str,
    *,
    source_key: str,
    role: str,
    settings: Settings,
    checked_at: str,
) -> CredentialValidation:
    adapter_status = phase1_live_adapter_status(source_key, settings)
    configured = bool(adapter_status["credential_configured"])
    required_count = int(adapter_status["required_group_count"])
    configured_count = int(adapter_status["configured_secret_group_count"])
    if not configured:
        return CredentialValidation(
            provider=provider,
            role=role,
            credential_state="missing",
            validation_status="missing_credentials",
            live_called=False,
            event_count=0,
            degraded_reason="missing_credentials",
            configured_secret_count=configured_count,
            required_secret_count=required_count,
            checked_at=checked_at,
            boundary="Credential missing. Provider cannot influence signals or execution.",
        )

    try:
        envelope = fetch_phase1_live_adapter_live_sync(source_key)
    except Exception as exc:  # noqa: BLE001
        return CredentialValidation(
            provider=provider,
            role=role,
            credential_state="configured",
            validation_status="degraded",
            live_called=True,
            event_count=0,
            degraded_reason=f"validation_error:{exc.__class__.__name__}",
            configured_secret_count=configured_count,
            required_secret_count=required_count,
            checked_at=checked_at,
            boundary="Read-only provider validation failed closed. No execution authority.",
        )
    events = envelope.get("events", [])
    event_count = len(events) if isinstance(events, list) else 0
    degraded = bool(envelope.get("degraded"))
    return CredentialValidation(
        provider=provider,
        role=role,
        credential_state="configured",
        validation_status="degraded" if degraded else "live",
        live_called=True,
        event_count=event_count,
        degraded_reason=envelope.get("degraded_reason"),
        configured_secret_count=configured_count,
        required_secret_count=required_count,
        checked_at=checked_at,
        boundary="Read-only provider validation only. No signal confidence, risk, or order authority.",
    )


def _gemini(settings: Settings, checked_at: str) -> CredentialValidation:
    configured = any(secret_status(key, settings).configured for key in ("GEMINI_API_KEY", "GOOGLE_API_KEY"))
    if not configured:
        return CredentialValidation(
            provider="gemini",
            role="frontier_llm_strategy_lead",
            credential_state="missing",
            validation_status="missing_credentials",
            live_called=False,
            event_count=0,
            degraded_reason="missing_credentials",
            configured_secret_count=0,
            required_secret_count=1,
            checked_at=checked_at,
            boundary="Gemini missing. Strategy Lead cannot call frontier model.",
        )
    result = gemini_credential_probe(settings, live=True, timeout_seconds=8.0)
    return CredentialValidation(
        provider="gemini",
        role="frontier_llm_strategy_lead",
        credential_state="configured",
        validation_status="live" if result["probe_status"] == "ok" else "degraded",
        live_called=True,
        event_count=int(result.get("model_count", 0)),
        degraded_reason=None if result["probe_status"] == "ok" else f"probe_status:{result['probe_status']}",
        configured_secret_count=1,
        required_secret_count=1,
        checked_at=checked_at,
        boundary="Gemini validation lists models only. It sends no trading content and generates no text.",
    )


def _lm_studio(settings: Settings, checked_at: str) -> CredentialValidation:
    # LOCAL_LLM_PROVIDER and LM_STUDIO_BASE_URL have safe defaults; the model id
    # is the required local setting that proves this machine knows what to load.
    configured_count = _configured_count(settings, ("LM_STUDIO_MODEL",))
    result = lm_studio_models_probe(settings, live=True, timeout_seconds=2.5)
    configured = result["mode"] != "missing_config"
    if not configured:
        return CredentialValidation(
            provider="lm_studio",
            role="local_llm_research_analyst",
            credential_state="missing",
            validation_status="missing_config",
            live_called=False,
            event_count=0,
            degraded_reason="missing_config",
            configured_secret_count=configured_count,
            required_secret_count=1,
            checked_at=checked_at,
            boundary="LM Studio local model config missing. No inference or execution authority.",
        )
    live = result["probe_status"] == "ok" and bool(result["model_available"])
    return CredentialValidation(
        provider="lm_studio",
        role="local_llm_research_analyst",
        credential_state="configured",
        validation_status="live" if live else "degraded",
        live_called=True,
        event_count=int(result.get("available_model_count", 0)),
        degraded_reason=None if live else f"probe_status:{result['probe_status']};model_available:{result['model_available']}",
        configured_secret_count=configured_count,
        required_secret_count=1,
        checked_at=checked_at,
        boundary="LM Studio validation lists local models only. It does not run inference.",
    )


def _telegram(settings: Settings, checked_at: str) -> CredentialValidation:
    store = TelegramCommunicationsStore(settings=settings)
    public_status = store.public_status()
    result = _phase1_provider(
        "telegram",
        source_key="telegram",
        role="member_communications_bot",
        settings=settings,
        checked_at=checked_at,
    )
    return CredentialValidation(
        provider=result.provider,
        role=result.role,
        credential_state=(
            "configured"
            if public_status["bot_configured"] and public_status["delivery_target_count"] > 0
            else result.credential_state
        ),
        validation_status=result.validation_status,
        live_called=result.live_called,
        event_count=result.event_count,
        degraded_reason=result.degraded_reason,
        configured_secret_count=int(public_status["bot_configured"]) + int(public_status["delivery_target_count"]),
        required_secret_count=2,
        checked_at=checked_at,
        boundary="Telegram validation is read-only getUpdates/config status. It sends no message and has no command path.",
    )


def _static_validation(
    provider: str,
    *,
    role: str,
    status: str,
    reason: str,
    checked_at: str,
) -> CredentialValidation:
    return CredentialValidation(
        provider=provider,
        role=role,
        credential_state=status,
        validation_status=status,
        live_called=False,
        event_count=0,
        degraded_reason=reason,
        configured_secret_count=0,
        required_secret_count=1,
        checked_at=checked_at,
        boundary="Provider intentionally not called in this validation pass.",
    )


def _contains_secret_like_value(payload: Any) -> bool:
    encoded = json.dumps(payload, sort_keys=True, default=str)
    return any(pattern.search(encoded) for pattern in SECRET_LIKE_PATTERNS)


def build_report(settings: Settings) -> dict[str, Any]:
    checked_at = _now()
    validations = [
        _status_from_envelope(
            "nasa_firms",
            role="physical_fire_thermal_anomalies",
            settings=settings,
            keys=("NASA_FIRMS_API_KEY",),
            fetcher=lambda: fetch_nasa_firms_live_sync(days=1),
            checked_at=checked_at,
        ),
        _status_from_envelope(
            "fred",
            role="macro_regime_data",
            settings=settings,
            keys=("FRED_API_KEY",),
            fetcher=lambda: fetch_fred_live_sync(series_ids=("DGS10", "DCOILWTICO", "VIXCLS"), limit=20),
            checked_at=checked_at,
            optional=True,
        ),
        _phase1_provider("acled", source_key="acled", role="conflict_events", settings=settings, checked_at=checked_at),
        _phase1_provider("alpaca", source_key="alpaca", role="paper_account_read_only", settings=settings, checked_at=checked_at),
        _telegram(settings, checked_at),
        _gemini(settings, checked_at),
        _lm_studio(settings, checked_at),
        _phase1_provider(
            "oddspipe",
            source_key="kalshi",
            role="prediction_market_aggregator",
            settings=settings,
            checked_at=checked_at,
        ),
        _phase1_provider(
            "capitol_trades",
            source_key="stock_act",
            role="politician_trade_disclosures",
            settings=settings,
            checked_at=checked_at,
        ),
        _static_validation(
            "kalshi_direct",
            role="prediction_market_regulated_direct_account",
            status="deferred",
            reason="region_identity_signup_deferred_oddspipe_used_for_readonly_coverage",
            checked_at=checked_at,
        ),
        _static_validation(
            "unusual_whales",
            role="options_flow_confirmation",
            status="missing_credentials",
            reason="useful_missing_batch_a_key",
            checked_at=checked_at,
        ),
    ]
    by_status: dict[str, int] = {}
    for validation in validations:
        by_status[validation.validation_status] = by_status.get(validation.validation_status, 0) + 1
    report = {
        "schema_version": 1,
        "checked_at": checked_at,
        "mode": "live_read_only_credential_validation",
        "provider_count": len(validations),
        "live_count": sum(1 for validation in validations if validation.validation_status == "live"),
        "degraded_count": sum(1 for validation in validations if validation.validation_status == "degraded"),
        "missing_count": sum(1 for validation in validations if validation.validation_status == "missing_credentials"),
        "deferred_count": sum(1 for validation in validations if validation.validation_status == "deferred"),
        "by_status": dict(sorted(by_status.items())),
        "validations": [validation.to_dict() for validation in validations],
        "boundary": "Supplied credential validation is read-only. It cannot create signals, risk approvals, messages, or orders.",
    }
    EventLog(echo=False).write(
        "supplied_credentials_validation_completed",
        "credential_validation",
        {
            "provider_count": report["provider_count"],
            "live_count": report["live_count"],
            "degraded_count": report["degraded_count"],
            "missing_count": report["missing_count"],
            "deferred_count": report["deferred_count"],
            "execution_allowed": False,
        },
    )
    return report


def write_report(settings: Settings, report: dict[str, Any]) -> Path:
    output_path = Path(settings.runtime_dir) / "supplied_credential_validation.json"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(report, indent=2, sort_keys=True), encoding="utf-8")
    history_path = Path(settings.runtime_dir) / "supplied_credential_validation.jsonl"
    with history_path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(report, sort_keys=True) + "\n")
    return output_path


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate supplied Qadam credentials.")
    parser.add_argument("--require-live-core", action="store_true", help="Fail if a non-deferred supplied core provider is not live.")
    args = parser.parse_args()

    settings = Settings.from_env()
    report = build_report(settings)
    report_path = write_report(settings, report)
    secret_leak = _contains_secret_like_value(report)

    print("supplied_credential_validation_status=" + ("ok" if not secret_leak else "error"))
    print(f"supplied_credential_validation_provider_count={report['provider_count']}")
    print(f"supplied_credential_validation_live_count={report['live_count']}")
    print(f"supplied_credential_validation_degraded_count={report['degraded_count']}")
    print(f"supplied_credential_validation_missing_count={report['missing_count']}")
    print(f"supplied_credential_validation_deferred_count={report['deferred_count']}")
    print("supplied_credential_validation_by_status=" + json.dumps(report["by_status"], sort_keys=True))
    print("supplied_credential_validation_report_path=" + str(report_path))
    print("supplied_credential_validation_boundary=" + report["boundary"])
    for validation in report["validations"]:
        print(
            "supplied_credential="
            + ",".join(
                [
                    validation["provider"],
                    validation["validation_status"],
                    validation["credential_state"],
                    f"live_called={validation['live_called']}",
                    f"events={validation['event_count']}",
                    f"reason={validation['degraded_reason'] or 'none'}",
                ]
            )
        )

    if secret_leak:
        print("supplied_credential_validation_secret_like_value_detected=true")
        return 1
    if args.require_live_core:
        allowed_non_live = {"kalshi_direct", "unusual_whales"}
        not_live = [
            validation["provider"]
            for validation in report["validations"]
            if validation["provider"] not in allowed_non_live and validation["validation_status"] != "live"
        ]
        if not_live:
            print("supplied_credential_validation_non_live_core=" + ",".join(not_live))
            return 1

    print("supplied_credential_validation_check=ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
