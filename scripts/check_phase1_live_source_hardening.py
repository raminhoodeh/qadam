#!/usr/bin/env python3
"""Validate Phase 1 live source readiness one source at a time.

Default mode is contract-only and network-free. `--live` performs read-only
provider calls for configured or public promoted adapters, then records whether
each source is live, degraded, missing credentials, or deferred.
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
    fetch_fred_sample,
    fetch_gdelt_live_sync,
    fetch_gdelt_sample,
    fetch_nasa_firms_live_sync,
    fetch_nasa_firms_sample,
    fetch_oref_live_sync,
    fetch_oref_sample,
    fetch_rss_live_sync,
    fetch_rss_sample,
    fred_adapter_status,
    gdelt_adapter_status,
    nasa_firms_adapter_status,
    oref_adapter_status,
    rss_adapter_status,
)
from orchestrator.config import Settings  # noqa: E402
from orchestrator.event_log import EventLog  # noqa: E402
from orchestrator.phase1_live_adapters import (  # noqa: E402
    PHASE1_LIVE_ADAPTERS,
    PHASE1_LIVE_ADAPTER_KEYS,
    fetch_phase1_live_adapter_live_sync,
    fetch_phase1_live_adapter_sample,
    phase1_live_adapter_status,
)
from orchestrator.secrets import secret_status  # noqa: E402
from world_monitor.source_registry import SOURCE_SPECS  # noqa: E402


DEDICATED_SOURCE_KEYS = ("gdelt", "oref", "nasa_firms", "fred", "rss")
PROMOTED_SOURCE_KEYS = DEDICATED_SOURCE_KEYS + PHASE1_LIVE_ADAPTER_KEYS
PUBLIC_DEDICATED_SOURCE_KEYS = {"gdelt", "oref", "fred", "rss"}
OPTIONAL_SECRET_KEYS = {"fred": {"FRED_API_KEY"}, "oref": {"OREF_PROXY_AUTH"}}
SECRET_LIKE_PATTERNS = (
    re.compile(r"\d{6,}:[A-Za-z0-9_-]{20,}"),
    re.compile(r"\bghp_[A-Za-z0-9]{20,}\b"),
    re.compile(r"\bvcp_[A-Za-z0-9]{20,}\b"),
    re.compile(r"\bAIza[0-9A-Za-z_-]{20,}\b"),
    re.compile(r"\bsb_secret_[0-9A-Za-z_-]{12,}\b"),
    re.compile(r"\b[A-Za-z0-9_-]{40,}\.[A-Za-z0-9_-]{20,}\.[A-Za-z0-9_-]{20,}\b"),
)


@dataclass(frozen=True)
class LiveSourceValidation:
    source_key: str
    source_name: str
    pipeline: str
    tier: int
    adapter_family: str
    credential_state: str
    validation_status: str
    mode: str
    event_count: int
    degraded: bool
    degraded_reason: str | None
    configured_secrets: tuple[str, ...]
    missing_secrets: tuple[str, ...]
    raw_archive_written: bool
    checked_at: str
    boundary: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _spec_by_key() -> dict[str, Any]:
    return {source.key: source for source in SOURCE_SPECS}


def _secret_names(source_key: str, settings: Settings) -> tuple[tuple[str, ...], tuple[str, ...]]:
    spec = _spec_by_key()[source_key]
    configured: list[str] = []
    missing: list[str] = []
    optional = OPTIONAL_SECRET_KEYS.get(source_key, set())
    for key in spec.env_vars:
        status = secret_status(key, settings)
        if status.configured:
            configured.append(key)
        elif key not in optional:
            missing.append(key)
    return tuple(configured), tuple(missing)


def _credential_state(source_key: str, configured: tuple[str, ...], missing: tuple[str, ...]) -> str:
    if source_key in PHASE1_LIVE_ADAPTERS:
        config = PHASE1_LIVE_ADAPTERS[source_key]
        if config.public_live and not missing:
            return "public"
        status = phase1_live_adapter_status(source_key)
        if status["credential_configured"]:
            return "configured"
        if config.public_live:
            return "public_with_missing_auth_for_private_scope"
        return "missing"
    if source_key in PUBLIC_DEDICATED_SOURCE_KEYS:
        return "configured_with_optional_key" if configured else "public"
    if configured and not missing:
        return "configured"
    return "missing"


def _dedicated_status(source_key: str) -> dict[str, Any]:
    return {
        "gdelt": gdelt_adapter_status,
        "oref": oref_adapter_status,
        "nasa_firms": nasa_firms_adapter_status,
        "fred": fred_adapter_status,
        "rss": rss_adapter_status,
    }[source_key]()


def _sample_fetch(source_key: str) -> dict[str, Any]:
    fetchers: dict[str, Callable[[], dict[str, Any]]] = {
        "gdelt": lambda: fetch_gdelt_sample(query="oil"),
        "oref": fetch_oref_sample,
        "nasa_firms": lambda: fetch_nasa_firms_sample(days=1),
        "fred": lambda: fetch_fred_sample(series_ids=("DGS10", "DCOILWTICO", "VIXCLS")),
        "rss": lambda: fetch_rss_sample(keyword_filter=("oil", "semiconductor", "defence", "silver")),
    }
    if source_key in fetchers:
        return fetchers[source_key]()
    return fetch_phase1_live_adapter_sample(source_key)


def _live_fetch(source_key: str) -> dict[str, Any]:
    fetchers: dict[str, Callable[[], dict[str, Any]]] = {
        "gdelt": lambda: fetch_gdelt_live_sync(query="oil OR semiconductors", maxrecords=10),
        "oref": fetch_oref_live_sync,
        "nasa_firms": lambda: fetch_nasa_firms_live_sync(days=1),
        "fred": lambda: fetch_fred_live_sync(series_ids=("DGS10", "DCOILWTICO", "VIXCLS"), limit=20),
        "rss": lambda: fetch_rss_live_sync(keyword_filter=("oil", "semiconductor", "defence", "silver")),
    }
    if source_key in fetchers:
        return fetchers[source_key]()
    return fetch_phase1_live_adapter_live_sync(source_key)


def _is_runnable(source_key: str, credential_state: str) -> bool:
    if credential_state in {"configured", "configured_with_optional_key", "public"}:
        return True
    if credential_state == "public_with_missing_auth_for_private_scope":
        return True
    return False


def _safe_status_from_result(result: dict[str, Any], mode: str) -> tuple[str, int, bool, str | None, bool]:
    events = result.get("events", [])
    event_count = len(events) if isinstance(events, list) else 0
    degraded = bool(result.get("degraded"))
    degraded_reason = result.get("degraded_reason")
    raw_archive_written = bool(result.get("raw_archive_path"))
    if mode == "sample":
        validation_status = "sample_ready" if not degraded else "sample_degraded"
    elif degraded:
        validation_status = "degraded"
    else:
        validation_status = "live"
    return validation_status, event_count, degraded, degraded_reason, raw_archive_written


def _contains_secret_like_value(payload: Any) -> bool:
    encoded = json.dumps(payload, sort_keys=True, default=str)
    return any(pattern.search(encoded) for pattern in SECRET_LIKE_PATTERNS)


def validate_source(source_key: str, *, settings: Settings, live: bool, checked_at: str) -> LiveSourceValidation:
    spec = _spec_by_key()[source_key]
    adapter_family = "dedicated" if source_key in DEDICATED_SOURCE_KEYS else "phase1_promoted"
    configured, missing = _secret_names(source_key, settings)
    if source_key in PHASE1_LIVE_ADAPTERS:
        status = phase1_live_adapter_status(source_key, settings)
        if status.get("credential_configured"):
            missing = ()
    credential_state = _credential_state(source_key, configured, missing)
    runnable = _is_runnable(source_key, credential_state)
    mode = "live_read_only" if live and runnable else "sample_or_status"

    if not runnable:
        return LiveSourceValidation(
            source_key=source_key,
            source_name=spec.name,
            pipeline=spec.pipeline,
            tier=spec.tier,
            adapter_family=adapter_family,
            credential_state=credential_state,
            validation_status="missing_credentials",
            mode=mode,
            event_count=0,
            degraded=True,
            degraded_reason="missing_credentials",
            configured_secrets=configured,
            missing_secrets=missing,
            raw_archive_written=False,
            checked_at=checked_at,
            boundary="Read-only readiness status. Missing sources cannot influence signals.",
        )

    try:
        result = _live_fetch(source_key) if live else _sample_fetch(source_key)
    except Exception as exc:  # noqa: BLE001 - explicit degraded status is the contract.
        return LiveSourceValidation(
            source_key=source_key,
            source_name=spec.name,
            pipeline=spec.pipeline,
            tier=spec.tier,
            adapter_family=adapter_family,
            credential_state=credential_state,
            validation_status="degraded",
            mode=mode,
            event_count=0,
            degraded=True,
            degraded_reason=f"validation_error:{exc.__class__.__name__}",
            configured_secrets=configured,
            missing_secrets=missing,
            raw_archive_written=False,
            checked_at=checked_at,
            boundary="Read-only live validation failed closed. No signal or execution authority.",
        )

    validation_status, event_count, degraded, degraded_reason, raw_archive_written = _safe_status_from_result(
        result,
        "live" if live else "sample",
    )
    return LiveSourceValidation(
        source_key=source_key,
        source_name=spec.name,
        pipeline=spec.pipeline,
        tier=spec.tier,
        adapter_family=adapter_family,
        credential_state=credential_state,
        validation_status=validation_status,
        mode=mode,
        event_count=event_count,
        degraded=degraded,
        degraded_reason=degraded_reason,
        configured_secrets=configured,
        missing_secrets=missing,
        raw_archive_written=raw_archive_written,
        checked_at=checked_at,
        boundary="Read-only validation only. Adapter output cannot approve signals, risk, or orders.",
    )


def write_report(settings: Settings, report: dict[str, Any]) -> Path:
    output_path = Path(settings.runtime_dir) / "phase1_live_source_validation.json"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(report, indent=2, sort_keys=True), encoding="utf-8")
    history_path = Path(settings.runtime_dir) / "phase1_live_source_validation.jsonl"
    with history_path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(report, sort_keys=True) + "\n")
    return output_path


def build_report(settings: Settings, *, live: bool) -> dict[str, Any]:
    checked_at = _now()
    validations = tuple(validate_source(key, settings=settings, live=live, checked_at=checked_at) for key in PROMOTED_SOURCE_KEYS)
    by_status: dict[str, int] = {}
    by_credential_state: dict[str, int] = {}
    for validation in validations:
        by_status[validation.validation_status] = by_status.get(validation.validation_status, 0) + 1
        by_credential_state[validation.credential_state] = by_credential_state.get(validation.credential_state, 0) + 1

    report = {
        "schema_version": 1,
        "checked_at": checked_at,
        "mode": "live_read_only" if live else "contract_sample",
        "source_count": len(validations),
        "live_or_sample_count": sum(
            1 for validation in validations if validation.validation_status in {"live", "sample_ready"}
        ),
        "degraded_count": sum(1 for validation in validations if validation.validation_status in {"degraded", "sample_degraded"}),
        "missing_credentials_count": sum(1 for validation in validations if validation.validation_status == "missing_credentials"),
        "configured_or_public_count": sum(
            1
            for validation in validations
            if validation.credential_state in {"configured", "configured_with_optional_key", "public", "public_with_missing_auth_for_private_scope"}
        ),
        "by_status": dict(sorted(by_status.items())),
        "by_credential_state": dict(sorted(by_credential_state.items())),
        "validations": [validation.to_dict() for validation in validations],
        "boundary": "Phase 1 live source validation is read-only. It cannot change signal confidence, create trade candidates, or send broker orders.",
    }
    EventLog(echo=False).write(
        "phase1_live_source_validation_completed",
        "phase1_live_source_hardening",
        {
            "mode": report["mode"],
            "source_count": report["source_count"],
            "live_or_sample_count": report["live_or_sample_count"],
            "degraded_count": report["degraded_count"],
            "missing_credentials_count": report["missing_credentials_count"],
            "execution_allowed": False,
        },
    )
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description="Check Phase 1 live source hardening.")
    parser.add_argument("--live", action="store_true", help="Call configured/public providers read-only.")
    parser.add_argument(
        "--require-no-degraded",
        action="store_true",
        help="Fail if any attempted live/source validation is degraded.",
    )
    args = parser.parse_args()

    settings = Settings.from_env()
    report = build_report(settings, live=args.live)
    output_path = write_report(settings, report)
    secret_leak = _contains_secret_like_value(report)

    print("phase1_live_source_hardening_status=" + ("ok" if not secret_leak else "error"))
    print(f"phase1_live_source_hardening_mode={report['mode']}")
    print(f"phase1_live_source_hardening_source_count={report['source_count']}")
    print(f"phase1_live_source_hardening_live_or_sample_count={report['live_or_sample_count']}")
    print(f"phase1_live_source_hardening_configured_or_public_count={report['configured_or_public_count']}")
    print(f"phase1_live_source_hardening_degraded_count={report['degraded_count']}")
    print(f"phase1_live_source_hardening_missing_credentials_count={report['missing_credentials_count']}")
    print("phase1_live_source_hardening_by_status=" + json.dumps(report["by_status"], sort_keys=True))
    print("phase1_live_source_hardening_report_path=" + str(output_path))
    print("phase1_live_source_hardening_boundary=" + report["boundary"])

    for validation in report["validations"]:
        print(
            "phase1_live_source="
            + ",".join(
                [
                    validation["source_key"],
                    validation["validation_status"],
                    validation["credential_state"],
                    f"events={validation['event_count']}",
                    f"degraded={validation['degraded']}",
                    f"reason={validation['degraded_reason'] or 'none'}",
                ]
            )
        )

    if secret_leak:
        print("phase1_live_source_hardening_secret_like_value_detected=true")
        return 1
    if args.require_no_degraded and report["degraded_count"]:
        print("phase1_live_source_hardening_degraded_sources_present=true")
        return 1
    print("phase1_live_source_hardening_check=ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
