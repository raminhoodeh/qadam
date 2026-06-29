"""Public-safe source-gap visibility for PaperOps.

This contract makes optional source coverage gaps explicit without turning them
into hidden blockers for guarded Alpaca Paper operation.
"""

from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Any

from orchestrator.config import Settings
from orchestrator.event_log import EventLog
from orchestrator.secrets import secret_status


PAPEROPS_SOURCE_GAP_VISIBILITY_SCHEMA_VERSION = 1
PAPEROPS_SOURCE_GAP_VISIBILITY_RUNTIME_ARTIFACT = "paperops_source_gap_visibility.json"
PAPEROPS_SOURCE_GAP_VISIBILITY_HISTORY = "paperops_source_gap_visibility_history.jsonl"
PAPEROPS_SOURCE_GAP_VISIBILITY_EVENT_LOG = "paperops_source_gap_visibility_events.jsonl"
PAPEROPS_SOURCE_GAP_VISIBILITY_EVENT_TYPE = "paperops_source_gap_visibility_recorded"
PAPEROPS_SOURCE_GAP_VISIBILITY_COMPONENT = "paperops_source_gap_visibility"

OPTIONAL_SOURCE_GAP_DEFINITIONS: tuple[dict[str, Any], ...] = (
    {
        "gap_key": "twitter_x_bearer_token_missing",
        "source_key": "twitter_x",
        "source_name": "X/Twitter",
        "coverage_role": "social_event_context",
        "credential_groups": (("X_BEARER_TOKEN",),),
    },
    {
        "gap_key": "reddit_credentials_missing",
        "source_key": "reddit",
        "source_name": "Reddit Narrative Proxy / Reddit OAuth",
        "coverage_role": "retail_forum_context",
        "credential_groups": (("REDDIT_CLIENT_ID", "REDDIT_CLIENT_SECRET"),),
        "proxy_coverage_active": True,
        "proxy_coverage_key": "reddit_narrative_proxy",
        "proxy_coverage_name": "Reddit Narrative Proxy via ApeWisdom aggregate data",
        "source_variant": "apewisdom_public_aggregate",
        "oauth_upgrade_state": "optional_upgrade_pending",
        "resolution_note": (
            "The first-release social narrative gap is covered by the no-key Reddit Narrative Proxy. "
            "Reddit OAuth remains an optional later enrichment path and is not a PaperOps blocker."
        ),
    },
    {
        "gap_key": "ais_maritime_credential_missing",
        "source_key": "ais_maritime",
        "source_name": "AIS maritime feeds",
        "coverage_role": "shipping_and_supply_chain_context",
        "credential_groups": (
            ("AISSTREAM_API_KEY",),
            ("SPIRE_API_KEY",),
            ("MARINETRAFFIC_API_KEY",),
        ),
    },
    {
        "gap_key": "aviationstack_api_key_missing",
        "source_key": "aviationstack",
        "source_name": "Aviationstack",
        "coverage_role": "air_traffic_context",
        "credential_groups": (("AVIATIONSTACK_API_KEY",),),
    },
    {
        "gap_key": "un_comtrade_api_key_missing",
        "source_key": "un_comtrade",
        "source_name": "UN Comtrade",
        "coverage_role": "trade_flow_context",
        "credential_groups": (("COMTRADE_API_KEY",),),
    },
    {
        "gap_key": "kalshi_credentials_missing",
        "source_key": "kalshi",
        "source_name": "Kalshi/OddsPipe prediction-market coverage",
        "coverage_role": "prediction_market_context",
        "credential_groups": (
            ("KALSHI_API_KEY", "KALSHI_API_SECRET"),
            ("ODDSPIPE_API_KEY",),
        ),
        "resolution_note": (
            "Direct Kalshi account access remains region/identity gated. "
            "OddsPipe satisfies the read-only Kalshi/Polymarket market-data coverage path."
        ),
    },
    {
        "gap_key": "stock_act_capitol_trades_api_key_missing",
        "source_key": "stock_act",
        "source_name": "Capitol Trades / STOCK Act",
        "coverage_role": "political_trading_context",
        "credential_groups": (("CAPITOL_TRADES_API_KEY",),),
    },
)

PAPEROPS_SOURCE_GAP_VISIBILITY_BOUNDARY = (
    "Public-safe source-gap visibility. It can report optional missing source "
    "coverage and credential configuration status, but optional gaps are not "
    "trade blockers. Source-quorum failures must be enforced at candidate "
    "review gates, not by silently promoting optional source gaps to PaperOps "
    "blockers. This artifact cannot create signals, cannot create trade "
    "candidates, cannot approve risk, cannot submit orders, cannot call "
    "brokers, cannot call live endpoints, cannot expose secrets, cannot "
    "enable live capital, and cannot grant paper proof ledger credit."
)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _runtime_dir(settings: Settings | None = None) -> Path:
    return Path((settings or Settings.from_env()).runtime_dir)


def _read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    payload = json.loads(path.read_text(encoding="utf-8"))
    return payload if isinstance(payload, dict) else {}


def _int(value: Any) -> int:
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0


def _configured_group_count(
    settings: Settings,
    credential_groups: tuple[tuple[str, ...], ...],
) -> int:
    configured = 0
    for group in credential_groups:
        if all(secret_status(key, settings).configured is True for key in group):
            configured += 1
    return configured


def _source_gap_record(definition: dict[str, Any], settings: Settings) -> dict[str, Any]:
    groups = tuple(tuple(group) for group in definition["credential_groups"])
    configured_group_count = _configured_group_count(settings, groups)
    proxy_coverage_active = definition.get("proxy_coverage_active") is True
    gap_present = configured_group_count == 0 and not proxy_coverage_active
    if configured_group_count:
        credential_status = "configured"
    elif proxy_coverage_active:
        credential_status = "covered_by_proxy_oauth_optional"
    else:
        credential_status = "missing_optional"
    return {
        "gap_key": definition["gap_key"],
        "source_key": definition["source_key"],
        "source_name": definition["source_name"],
        "coverage_role": definition["coverage_role"],
        "proxy_coverage_active": proxy_coverage_active,
        "proxy_coverage_key": definition.get("proxy_coverage_key"),
        "proxy_coverage_name": definition.get("proxy_coverage_name"),
        "source_variant": definition.get("source_variant"),
        "oauth_upgrade_state": definition.get("oauth_upgrade_state"),
        "severity": "optional",
        "gap_present": gap_present,
        "credential_group_count": len(groups),
        "configured_credential_group_count": configured_group_count,
        "credential_status": credential_status,
        "resolution_note": definition.get("resolution_note"),
        "trade_blocking": False,
        "source_quorum_blocking": False,
        "paper_order_submission_blocking": False,
        "paper_exit_blocking": False,
        "proof_credit_blocking": False,
        "next_action": (
            "No trading action required; Reddit OAuth remains an optional upgrade."
            if proxy_coverage_active and not configured_group_count
            else "Configure optional source credentials to expand context coverage."
            if gap_present
            else "No action required."
        ),
        "public_safe": True,
    }


def paperops_source_gap_visibility_paths(
    settings: Settings | None = None,
) -> tuple[Path, Path, Path]:
    runtime = _runtime_dir(settings)
    return (
        runtime / PAPEROPS_SOURCE_GAP_VISIBILITY_RUNTIME_ARTIFACT,
        runtime / PAPEROPS_SOURCE_GAP_VISIBILITY_HISTORY,
        runtime / PAPEROPS_SOURCE_GAP_VISIBILITY_EVENT_LOG,
    )


def read_latest_paperops_source_gap_visibility(
    settings: Settings | None = None,
) -> dict[str, Any]:
    output_path, _, _ = paperops_source_gap_visibility_paths(settings)
    return _read_json(output_path)


def build_paperops_source_gap_visibility(
    settings: Settings | None = None,
    *,
    generated_at: str | None = None,
) -> dict[str, Any]:
    settings = settings or Settings.from_env()
    generated = generated_at or _now()
    records = [
        _source_gap_record(definition, settings)
        for definition in OPTIONAL_SOURCE_GAP_DEFINITIONS
    ]
    optional_gap_records = [record for record in records if record["gap_present"]]
    optional_gap_keys = [record["gap_key"] for record in optional_gap_records]
    covered_proxy_records = [
        record
        for record in records
        if record.get("proxy_coverage_active") is True and not record.get("gap_present")
    ]
    trade_blocking_gap_count = sum(1 for record in records if record["trade_blocking"])
    artifact = {
        "schema_version": PAPEROPS_SOURCE_GAP_VISIBILITY_SCHEMA_VERSION,
        "artifact_type": "paperops_source_gap_visibility",
        "artifact_id": "paperops:source-gap-visibility:latest",
        "phase": "PaperOps",
        "stage": "PaperOps-source-gap-visibility",
        "status": (
            "explicit_optional_source_gaps"
            if optional_gap_records
            else "all_optional_sources_configured"
        ),
        "generated_at": generated,
        "public_safe": True,
        "recorded": False,
        "event_log_required": True,
        "event_log_written": False,
        "event_log_path": None,
        "event_log_event_count": 0,
        "runtime_artifact_path": None,
        "history_log_path": None,
        "source_gap_policy_status": "optional_gaps_explicit_non_blocking",
        "source_gap_count": len(records),
        "source_gap_records": records,
        "optional_gap_count": len(optional_gap_records),
        "optional_gap_keys": optional_gap_keys,
        "optional_gap_records": optional_gap_records,
        "covered_proxy_count": len(covered_proxy_records),
        "covered_proxy_records": covered_proxy_records,
        "non_blocking_gap_count": len(optional_gap_records),
        "non_blocking_gap_keys": optional_gap_keys,
        "required_gap_count": 0,
        "required_gap_keys": [],
        "required_gap_records": [],
        "trade_blocking_source_gap_count": trade_blocking_gap_count,
        "source_quorum_blocking_gap_count": 0,
        "silent_blocker_count": 0,
        "silent_blocker_keys": [],
        "blockers": [],
        "blocker_count": 0,
        "broker_post_called_count": 0,
        "broker_write_allowed_count": 0,
        "live_endpoint_called_count": 0,
        "live_capital_enabled": settings.live_capital_enabled,
        "phase7_proof_credit_allowed": False,
        "paper_order_submission_allowed": False,
        "source_gap_can_create_trade_candidate": False,
        "secret_value_exposed": False,
        "raw_secret_key_exposed": False,
        "next_required_action": (
            "Optional source gaps are visible and non-blocking; keep candidate-level source quorum gates enforced."
        ),
        "boundary": PAPEROPS_SOURCE_GAP_VISIBILITY_BOUNDARY,
    }
    artifact["validation_errors"] = validate_paperops_source_gap_visibility(artifact)
    artifact["validation_error_count"] = len(artifact["validation_errors"])
    if artifact["validation_errors"]:
        artifact["status"] = "invalid"
    return artifact


def validate_paperops_source_gap_visibility(artifact: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    required = {
        "artifact_id",
        "artifact_type",
        "blocker_count",
        "blockers",
        "boundary",
        "broker_post_called_count",
        "broker_write_allowed_count",
        "generated_at",
        "live_capital_enabled",
        "live_endpoint_called_count",
        "non_blocking_gap_count",
        "non_blocking_gap_keys",
        "optional_gap_count",
        "optional_gap_keys",
        "optional_gap_records",
        "paper_order_submission_allowed",
        "phase7_proof_credit_allowed",
        "public_safe",
        "required_gap_count",
        "required_gap_keys",
        "schema_version",
        "secret_value_exposed",
        "silent_blocker_count",
        "source_gap_can_create_trade_candidate",
        "source_gap_policy_status",
        "source_gap_records",
        "stage",
        "status",
        "trade_blocking_source_gap_count",
    }
    missing = sorted(required - set(artifact))
    if missing:
        errors.append("paperops_source_gap_visibility_missing_fields:" + ",".join(missing))
    if artifact.get("schema_version") != PAPEROPS_SOURCE_GAP_VISIBILITY_SCHEMA_VERSION:
        errors.append("paperops_source_gap_visibility_schema_mismatch")
    if artifact.get("artifact_type") != "paperops_source_gap_visibility":
        errors.append("paperops_source_gap_visibility_type_mismatch")
    if artifact.get("public_safe") is not True:
        errors.append("paperops_source_gap_visibility_not_public_safe")
    if artifact.get("status") not in {
        "explicit_optional_source_gaps",
        "all_optional_sources_configured",
        "invalid",
    }:
        errors.append("paperops_source_gap_visibility_status_invalid")
    if artifact.get("source_gap_policy_status") != "optional_gaps_explicit_non_blocking":
        errors.append("paperops_source_gap_visibility_policy_invalid")
    for key in (
        "live_capital_enabled",
        "phase7_proof_credit_allowed",
        "paper_order_submission_allowed",
        "source_gap_can_create_trade_candidate",
        "secret_value_exposed",
        "raw_secret_key_exposed",
    ):
        if artifact.get(key) is not False:
            errors.append(f"paperops_source_gap_visibility_forbidden:{key}")
    for key in (
        "broker_post_called_count",
        "broker_write_allowed_count",
        "live_endpoint_called_count",
        "trade_blocking_source_gap_count",
        "source_quorum_blocking_gap_count",
        "silent_blocker_count",
        "required_gap_count",
    ):
        if _int(artifact.get(key)) != 0:
            errors.append(f"paperops_source_gap_visibility_counter_nonzero:{key}")
    blockers = artifact.get("blockers", [])
    if not isinstance(blockers, list):
        errors.append("paperops_source_gap_visibility_blockers_not_list")
        blockers = []
    if _int(artifact.get("blocker_count")) != len(blockers):
        errors.append("paperops_source_gap_visibility_blocker_count_mismatch")
    optional_gap_keys = [
        str(key)
        for key in artifact.get("optional_gap_keys", []) or []
        if str(key).strip()
    ]
    non_blocking_gap_keys = [
        str(key)
        for key in artifact.get("non_blocking_gap_keys", []) or []
        if str(key).strip()
    ]
    if sorted(optional_gap_keys) != sorted(non_blocking_gap_keys):
        errors.append("paperops_source_gap_visibility_non_blocking_key_mismatch")
    if blockers and set(blockers) & set(optional_gap_keys):
        errors.append("paperops_source_gap_visibility_optional_promoted_to_blocker")
    optional_gap_records = artifact.get("optional_gap_records", [])
    if not isinstance(optional_gap_records, list):
        errors.append("paperops_source_gap_visibility_optional_records_not_list")
        optional_gap_records = []
    if _int(artifact.get("optional_gap_count")) != len(optional_gap_records):
        errors.append("paperops_source_gap_visibility_optional_count_mismatch")
    source_gap_records = artifact.get("source_gap_records", [])
    if not isinstance(source_gap_records, list):
        errors.append("paperops_source_gap_visibility_records_not_list")
        source_gap_records = []
    for record in source_gap_records:
        if not isinstance(record, dict):
            errors.append("paperops_source_gap_visibility_record_invalid")
            continue
        if record.get("severity") != "optional":
            errors.append("paperops_source_gap_visibility_record_not_optional")
        if record.get("public_safe") is not True:
            errors.append("paperops_source_gap_visibility_record_not_public_safe")
        for key in (
            "trade_blocking",
            "source_quorum_blocking",
            "paper_order_submission_blocking",
            "paper_exit_blocking",
            "proof_credit_blocking",
        ):
            if record.get(key) is not False:
                errors.append(f"paperops_source_gap_visibility_record_blocks:{key}")
    optional_record_keys = [
        str(record.get("gap_key"))
        for record in optional_gap_records
        if isinstance(record, dict) and record.get("gap_key")
    ]
    if sorted(optional_record_keys) != sorted(optional_gap_keys):
        errors.append("paperops_source_gap_visibility_optional_record_key_mismatch")
    boundary = str(artifact.get("boundary") or "")
    for phrase in (
        "optional gaps are not trade blockers",
        "candidate review gates",
        "cannot create signals",
        "cannot call live endpoints",
        "cannot expose secrets",
        "cannot enable live capital",
        "cannot grant paper proof ledger credit",
    ):
        if phrase not in boundary:
            errors.append("paperops_source_gap_visibility_boundary_weak")
            break
    return sorted(set(errors))


def write_paperops_source_gap_visibility(
    artifact: dict[str, Any],
    settings: Settings | None = None,
    *,
    record_event: bool = True,
    event_log_path: str | Path | None = None,
) -> tuple[Path, Path, Path, dict[str, Any]]:
    settings = settings or Settings.from_env()
    output_path, history_path, default_event_path = paperops_source_gap_visibility_paths(
        settings
    )
    event_path = Path(event_log_path or default_event_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    written = deepcopy(artifact)
    written["recorded"] = True
    written["runtime_artifact_path"] = str(output_path)
    written["history_log_path"] = str(history_path)
    if record_event:
        event = EventLog(event_path, echo=False).write(
            PAPEROPS_SOURCE_GAP_VISIBILITY_EVENT_TYPE,
            PAPEROPS_SOURCE_GAP_VISIBILITY_COMPONENT,
            payload={
                "status": written.get("status"),
                "optional_gap_count": written.get("optional_gap_count"),
                "required_gap_count": written.get("required_gap_count"),
                "trade_blocking_source_gap_count": written.get(
                    "trade_blocking_source_gap_count"
                ),
                "silent_blocker_count": written.get("silent_blocker_count"),
                "blocker_count": written.get("blocker_count"),
            },
        )
        written["event_log_written"] = True
        written["event_log_path"] = str(event_path)
        written["event_log_event_count"] = 1
        written["event_log_correlation_id"] = event.correlation_id
        written["event_log_created_at"] = event.created_at
    written["validation_errors"] = validate_paperops_source_gap_visibility(written)
    written["validation_error_count"] = len(written["validation_errors"])
    if written["validation_errors"]:
        written["status"] = "invalid"
    output_path.write_text(
        json.dumps(written, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    history_record = {
        "schema_version": PAPEROPS_SOURCE_GAP_VISIBILITY_SCHEMA_VERSION,
        "artifact_id": written.get("artifact_id"),
        "status": written.get("status"),
        "recorded_at": _now(),
        "optional_gap_count": written.get("optional_gap_count"),
        "required_gap_count": written.get("required_gap_count"),
        "trade_blocking_source_gap_count": written.get(
            "trade_blocking_source_gap_count"
        ),
        "silent_blocker_count": written.get("silent_blocker_count"),
        "blocker_count": written.get("blocker_count"),
        "validation_error_count": written.get("validation_error_count"),
    }
    with history_path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(history_record, sort_keys=True) + "\n")
    return output_path, history_path, event_path, written


def paperops_source_gap_visibility_public_status(
    settings: Settings | None = None,
) -> dict[str, Any]:
    artifact = read_latest_paperops_source_gap_visibility(settings)
    if not artifact:
        artifact = build_paperops_source_gap_visibility(settings)
    keys = (
        "schema_version",
        "status",
        "public_safe",
        "source_gap_policy_status",
        "source_gap_count",
        "optional_gap_count",
        "optional_gap_keys",
        "optional_gap_records",
        "non_blocking_gap_count",
        "non_blocking_gap_keys",
        "required_gap_count",
        "required_gap_keys",
        "trade_blocking_source_gap_count",
        "source_quorum_blocking_gap_count",
        "silent_blocker_count",
        "silent_blocker_keys",
        "blockers",
        "blocker_count",
        "broker_post_called_count",
        "broker_write_allowed_count",
        "live_endpoint_called_count",
        "live_capital_enabled",
        "phase7_proof_credit_allowed",
        "paper_order_submission_allowed",
        "source_gap_can_create_trade_candidate",
        "secret_value_exposed",
        "raw_secret_key_exposed",
        "next_required_action",
        "boundary",
        "validation_error_count",
        "covered_proxy_count",
        "covered_proxy_records",
    )
    return {key: deepcopy(artifact.get(key)) for key in keys}
