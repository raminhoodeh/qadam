"""Read-only Reddit Narrative Proxy via ApeWisdom aggregate endpoints.

The proxy fills Qadam's existing Reddit social/narrative slot without Reddit
OAuth credentials. It is aggregate retail-attention context only: no raw Reddit
posts, no source-quorum credit, no trade candidates, no approvals, and no
broker or live-capital authority.
"""

from __future__ import annotations

import asyncio
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4

from orchestrator.adapters import RawPayloadArchive, SourceEnvelope, UnifiedEvent, UNIFIED_EVENT_SCHEMA_VERSION
from orchestrator.config import Settings
from orchestrator.event_log import EventLog


REDDIT_NARRATIVE_PROXY_SCHEMA_VERSION = 1
REDDIT_NARRATIVE_PROXY_SOURCE_KEY = "reddit_narrative_proxy"
REDDIT_NARRATIVE_PROXY_REGISTRY_SLOT = "reddit"
REDDIT_NARRATIVE_PROXY_SOURCE_VARIANT = "apewisdom_public_aggregate"
REDDIT_NARRATIVE_PROXY_RUNTIME_ARTIFACT = "reddit_narrative_proxy_validation.json"
REDDIT_NARRATIVE_PROXY_HISTORY = "reddit_narrative_proxy_history.jsonl"
REDDIT_NARRATIVE_PROXY_EVENT_LOG = "reddit_narrative_proxy_events.jsonl"
TRUST_SCORE_SEED = 0.46

APEWISDOM_ENDPOINTS: dict[str, str] = {
    "all_stocks": "https://apewisdom.io/api/v1.0/filter/all-stocks/page/1",
    "all_crypto": "https://apewisdom.io/api/v1.0/filter/all-crypto/page/1",
    "4chan": "https://apewisdom.io/api/v1.0/filter/4chan/page/1",
}

AUTHORITY_FLAGS = {
    "source_quorum_credit_allowed": False,
    "trade_candidate_creation_allowed": False,
    "risk_approval_allowed": False,
    "execution_allowed": False,
    "paper_order_allowed": False,
    "broker_write_allowed": False,
    "live_capital_enabled": False,
    "proof_credit_allowed": False,
}

ALLOWED_CONTEXT_TAGS = (
    "social_confirmation",
    "social_contradiction",
    "crowding_warning",
    "late_consensus_warning",
    "retail_attention_anomaly",
)

REQUIRED_OBSERVATION_FIELDS = {
    "source_key",
    "source_variant",
    "pipeline",
    "event_type",
    "collected_at",
    "asset_type",
    "ticker",
    "name",
    "rank",
    "rank_24h_ago",
    "mentions",
    "mentions_24h_ago",
    "upvotes",
    "mention_change_abs",
    "mention_change_pct",
    "attention_velocity",
    "crowding_risk",
    "qadam_use",
    "trust_score_seed",
    "authority",
}


@dataclass(frozen=True)
class RedditNarrativeProxyResult:
    packet: dict[str, Any]
    degraded: bool
    degraded_reason: str | None = None


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _runtime_dir(settings: Settings | None = None) -> Path:
    return Path((settings or Settings.from_env()).runtime_dir)


def _read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return payload if isinstance(payload, dict) else {}


def _int(value: Any, default: int = 0) -> int:
    try:
        if value is None or value == "":
            return default
        return int(float(value))
    except (TypeError, ValueError):
        return default


def _float(value: Any, default: float = 0.0) -> float:
    try:
        if value is None or value == "":
            return default
        return float(value)
    except (TypeError, ValueError):
        return default


def _safe_pct(current: int, previous: int) -> float:
    if previous <= 0:
        return 100.0 if current > 0 else 0.0
    return round(((current - previous) / previous) * 100.0, 2)


def _asset_type(filter_key: str) -> str:
    if filter_key == "all_crypto":
        return "crypto"
    if filter_key == "4chan":
        return "forum_cross_asset"
    return "equity"


def _crowding_risk(rank: int, mentions: int, mention_change_pct: float) -> str:
    if rank <= 5 and mentions >= 750 and mention_change_pct >= 100:
        return "high"
    if rank <= 15 or mentions >= 250 or mention_change_pct >= 50:
        return "medium"
    return "low"


def _qadam_use(rank: int, rank_24h_ago: int, mention_change_pct: float, crowding_risk: str) -> str:
    if crowding_risk == "high" and rank <= 5:
        return "saturation_warning"
    if rank_24h_ago and rank < rank_24h_ago and mention_change_pct > 25:
        return "confirmation"
    if mention_change_pct < -25:
        return "contradiction"
    return "anomaly"


def _attention_velocity(rank: int, mentions: int, mentions_24h_ago: int) -> float:
    velocity = min(1.0, max(0.0, _safe_pct(mentions, mentions_24h_ago) / 250.0))
    rank_boost = 0.15 if 0 < rank <= 10 else 0.0
    return round(min(1.0, velocity + rank_boost), 3)


def _records_from_payload(filter_payload: Any) -> list[dict[str, Any]]:
    if isinstance(filter_payload, list):
        return [record for record in filter_payload if isinstance(record, dict)]
    if not isinstance(filter_payload, dict):
        return []
    for key in ("results", "data", "items", "records", "observations"):
        value = filter_payload.get(key)
        if isinstance(value, list):
            return [record for record in value if isinstance(record, dict)]
    return [filter_payload]


def sample_reddit_narrative_proxy_payload(*, collected_at: str | None = None) -> dict[str, Any]:
    generated_at = collected_at or _now()
    return {
        "sample": True,
        "source_key": REDDIT_NARRATIVE_PROXY_SOURCE_KEY,
        "source_variant": REDDIT_NARRATIVE_PROXY_SOURCE_VARIANT,
        "registry_slot": REDDIT_NARRATIVE_PROXY_REGISTRY_SLOT,
        "generated_at": generated_at,
        "filters": {
            "all_stocks": {
                "results": [
                    {
                        "ticker": "NVDA",
                        "name": "NVIDIA",
                        "rank": 1,
                        "rank_24h_ago": 8,
                        "mentions": 1258,
                        "mentions_24h_ago": 442,
                        "upvotes": 3890,
                    },
                    {
                        "ticker": "SMCI",
                        "name": "Super Micro Computer",
                        "rank": 9,
                        "rank_24h_ago": 14,
                        "mentions": 302,
                        "mentions_24h_ago": 211,
                        "upvotes": 720,
                    },
                ]
            },
            "all_crypto": {
                "results": [
                    {
                        "ticker": "BTC",
                        "name": "Bitcoin",
                        "rank": 2,
                        "rank_24h_ago": 4,
                        "mentions": 980,
                        "mentions_24h_ago": 774,
                        "upvotes": 2540,
                    }
                ]
            },
            "4chan": {
                "results": [
                    {
                        "ticker": "SILVER",
                        "name": "Silver",
                        "rank": 12,
                        "rank_24h_ago": 35,
                        "mentions": 188,
                        "mentions_24h_ago": 41,
                        "upvotes": 0,
                    }
                ]
            },
        },
    }


def normalize_reddit_narrative_proxy_payload(
    payload: dict[str, Any],
    *,
    collected_at: str | None = None,
) -> list[dict[str, Any]]:
    collected = collected_at or str(payload.get("generated_at") or _now())
    filters = payload.get("filters")
    if isinstance(filters, dict):
        filter_items = filters.items()
    else:
        filter_items = (("all_stocks", payload),)

    observations: list[dict[str, Any]] = []
    for filter_key, filter_payload in filter_items:
        for record in _records_from_payload(filter_payload)[:25]:
            ticker = str(record.get("ticker") or record.get("symbol") or record.get("name") or "").strip().upper()
            if not ticker:
                continue
            name = str(record.get("name") or record.get("title") or ticker).strip()
            rank = _int(record.get("rank"))
            rank_24h_ago = _int(record.get("rank_24h_ago") or record.get("rank_24h") or record.get("rank_last_24h"))
            mentions = _int(record.get("mentions") or record.get("mentions_count"))
            mentions_24h_ago = _int(record.get("mentions_24h_ago") or record.get("mentions_24h") or record.get("mentions_last_24h"))
            upvotes = _int(record.get("upvotes") or record.get("upvotes_count"))
            mention_change_abs = mentions - mentions_24h_ago
            mention_change_pct = _safe_pct(mentions, mentions_24h_ago)
            crowding_risk = _crowding_risk(rank, mentions, mention_change_pct)
            observations.append(
                {
                    "source_key": REDDIT_NARRATIVE_PROXY_SOURCE_KEY,
                    "source_variant": REDDIT_NARRATIVE_PROXY_SOURCE_VARIANT,
                    "registry_slot": REDDIT_NARRATIVE_PROXY_REGISTRY_SLOT,
                    "pipeline": "social",
                    "event_type": "social_signal",
                    "collected_at": collected,
                    "asset_type": _asset_type(str(filter_key)),
                    "ticker": ticker,
                    "name": name,
                    "rank": rank,
                    "rank_24h_ago": rank_24h_ago,
                    "mentions": mentions,
                    "mentions_24h_ago": mentions_24h_ago,
                    "upvotes": upvotes,
                    "mention_change_abs": mention_change_abs,
                    "mention_change_pct": mention_change_pct,
                    "attention_velocity": _attention_velocity(rank, mentions, mentions_24h_ago),
                    "crowding_risk": crowding_risk,
                    "qadam_use": _qadam_use(rank, rank_24h_ago, mention_change_pct, crowding_risk),
                    "trust_score_seed": TRUST_SCORE_SEED,
                    "authority": "read_only_context_only",
                    **AUTHORITY_FLAGS,
                }
            )
    return observations


def _market_join_state(observation: dict[str, Any], settings: Settings | None = None) -> dict[str, Any]:
    runtime = _runtime_dir(settings)
    ticker = str(observation.get("ticker") or "").upper()
    market_context = _read_json(runtime / "market_context_packet.json")
    alpaca_mirror = _read_json(runtime / "alpaca_paper_mirror.json")
    prediction_adapter = _read_json(runtime / "phase5_prediction_market_adapter.json")
    joined_artifacts: list[str] = []

    market_text = json.dumps(market_context, sort_keys=True)[:20000].upper() if market_context else ""
    alpaca_text = json.dumps(alpaca_mirror, sort_keys=True)[:20000].upper() if alpaca_mirror else ""
    prediction_text = json.dumps(prediction_adapter, sort_keys=True)[:20000].upper() if prediction_adapter else ""
    if ticker and ticker in market_text:
        joined_artifacts.append("data/runtime/market_context_packet.json")
    if ticker and ticker in alpaca_text:
        joined_artifacts.append("data/runtime/alpaca_paper_mirror.json")
    if ticker and ticker in prediction_text:
        joined_artifacts.append("data/runtime/phase5_prediction_market_adapter.json")

    return {
        "ticker": ticker,
        "market_context_join_state": "joined_read_only_context" if joined_artifacts else "pending_market_context_join",
        "joined_artifacts": joined_artifacts,
        "attention_vs_price_gap": "not_computed_without_current_price_join",
        "attention_vs_volume_gap": "not_computed_without_volume_join",
        "retail_arrival_lag": "pending_historical_alignment",
        "prediction_market_theme_overlap": "pending_theme_join",
        "execution_authority": False,
    }


def build_retail_attention_packet(
    observations: list[dict[str, Any]],
    *,
    settings: Settings | None = None,
) -> dict[str, Any]:
    top_observations = sorted(
        observations,
        key=lambda item: (_float(item.get("attention_velocity")), _int(item.get("mentions"))),
        reverse=True,
    )[:10]
    early_attention = [
        item
        for item in top_observations
        if item.get("qadam_use") in {"confirmation", "anomaly"} and item.get("crowding_risk") != "high"
    ]
    crowding_warnings = [item for item in top_observations if item.get("crowding_risk") == "high"]
    return {
        "packet_type": "retail_attention_packet",
        "status": "retail_attention_context_ready" if observations else "retail_attention_context_empty",
        "source_key": REDDIT_NARRATIVE_PROXY_SOURCE_KEY,
        "source_variant": REDDIT_NARRATIVE_PROXY_SOURCE_VARIANT,
        "raw_reddit_text_present": False,
        "local_llm_task": "compress_only_non_executable",
        "strategy_lead_role": "confidence_or_urgency_modifier_only",
        "akber_filter_role": {
            "stage_1_catalyst": "may_confirm_that_a_catalyst_entered_retail_attention",
            "stage_2_sector_theme": "may_reveal_crowding_in_qadam_sleeves",
            "stage_3_macro_news_context": "requires_rss_gdelt_fred_sec_or_physical_corroboration",
            "stage_4_technical": "requires_price_volume_tradingview_yahoo_or_alpaca_context",
            "stage_5_risk": "euphoric_attention_raises_slippage_and_reversal_risk",
            "stage_6_execution": "never_execution_authorizing",
        },
        "allowed_context_tags": list(ALLOWED_CONTEXT_TAGS),
        "top_observations": top_observations,
        "early_attention_count": len(early_attention),
        "crowding_warning_count": len(crowding_warnings),
        "market_joins": [_market_join_state(item, settings) for item in top_observations],
        **AUTHORITY_FLAGS,
    }


def build_reddit_narrative_proxy_packet(
    payload: dict[str, Any] | None = None,
    *,
    settings: Settings | None = None,
    generated_at: str | None = None,
    degraded: bool = False,
    degraded_reason: str | None = None,
    live_mode: bool = False,
) -> dict[str, Any]:
    generated = generated_at or _now()
    raw_payload = payload or sample_reddit_narrative_proxy_payload(collected_at=generated)
    observations = normalize_reddit_narrative_proxy_payload(raw_payload, collected_at=generated)
    packet = {
        "schema_version": REDDIT_NARRATIVE_PROXY_SCHEMA_VERSION,
        "artifact_type": "reddit_narrative_proxy_validation",
        "artifact_id": "reddit:narrative-proxy:latest",
        "status": (
            "degraded"
            if degraded
            else "live_proxy_observations_ready"
            if live_mode
            else "sample_proxy_observations_ready"
        ),
        "generated_at": generated,
        "source_key": REDDIT_NARRATIVE_PROXY_SOURCE_KEY,
        "source_variant": REDDIT_NARRATIVE_PROXY_SOURCE_VARIANT,
        "registry_slot": REDDIT_NARRATIVE_PROXY_REGISTRY_SLOT,
        "source_registry_slot": REDDIT_NARRATIVE_PROXY_REGISTRY_SLOT,
        "canonical_source_count_unchanged": 35,
        "do_not_add_source_36": True,
        "source_count_delta": 0,
        "reference_repo": "Sam120204/Stock_Trading_Reddit",
        "reference_repo_imported_runtime_code": False,
        "reference_repo_license_recorded": "MIT_reference_only",
        "deferred_reference_components": ["praw", "raw_reddit_scraping", "mongodb", "streamlit", "random_forest"],
        "active_reference_pattern": "apewisdom_public_aggregate_client",
        "reddit_oauth_state": "optional_upgrade_pending",
        "reddit_oauth_required": False,
        "raw_reddit_scraping_enabled": False,
        "credential_required": False,
        "live_mode": live_mode,
        "degraded": degraded,
        "degraded_reason": degraded_reason,
        "endpoints": dict(APEWISDOM_ENDPOINTS),
        "trust_score_seed": TRUST_SCORE_SEED,
        "qadam_use": "secondary_social_narrative_context_only",
        "can_support_setup": True,
        "can_challenge_setup": True,
        "cannot_originate_trade": True,
        "primary_source_quorum_allowed": False,
        "observations": observations,
        "observation_count": len(observations),
        "retail_attention_packet": build_retail_attention_packet(observations, settings=settings),
        "paperops_safety": {
            "cannot_create_trade_candidate_alone": True,
            "cannot_satisfy_minimum_source_quorum_alone": True,
            "cannot_approve_risk": True,
            "cannot_stage_orders": True,
            "cannot_submit_orders": True,
            "cannot_grant_paper_proof_ledger_credit": True,
            "guarded_alpaca_paper_route_unchanged": True,
        },
        "public_dashboard_copy": {
            "data_source_label": "Reddit Narrative Proxy connected through ApeWisdom aggregate data",
            "oauth_label": "Reddit OAuth optional upgrade pending",
            "mission_snapshot_note": "Retail/forum attention is available through aggregate public data.",
            "strategy_note": "Retail attention can flag crowding and edge decay, but never creates trades.",
        },
        "authority_flags": dict(AUTHORITY_FLAGS),
        "public_safe": True,
        "command_disabled": True,
    }
    packet["validation_errors"] = validate_reddit_narrative_proxy_packet(packet)
    packet["validation_error_count"] = len(packet["validation_errors"])
    if packet["validation_errors"]:
        packet["status"] = "invalid"
    return packet


def validate_reddit_narrative_proxy_packet(packet: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if packet.get("source_registry_slot") != REDDIT_NARRATIVE_PROXY_REGISTRY_SLOT:
        errors.append("source_registry_slot_not_reddit")
    if packet.get("source_key") != REDDIT_NARRATIVE_PROXY_SOURCE_KEY:
        errors.append("source_key_mismatch")
    if packet.get("source_variant") != REDDIT_NARRATIVE_PROXY_SOURCE_VARIANT:
        errors.append("source_variant_mismatch")
    if packet.get("do_not_add_source_36") is not True or _int(packet.get("source_count_delta")) != 0:
        errors.append("source_36_violation")
    if packet.get("canonical_source_count_unchanged") != 35:
        errors.append("canonical_source_count_changed")
    if packet.get("reference_repo_imported_runtime_code") is not False:
        errors.append("reference_repo_runtime_imported")
    if packet.get("reddit_oauth_required") is not False or packet.get("credential_required") is not False:
        errors.append("reddit_oauth_required_unexpectedly")
    if packet.get("raw_reddit_scraping_enabled") is not False:
        errors.append("raw_reddit_scraping_enabled")
    for key, expected in AUTHORITY_FLAGS.items():
        if packet.get("authority_flags", {}).get(key) is not expected:
            errors.append(f"authority_flag_enabled:{key}")
        if packet.get("retail_attention_packet", {}).get(key) is not expected:
            errors.append(f"retail_packet_authority_enabled:{key}")
    observations = packet.get("observations")
    if not isinstance(observations, list):
        errors.append("observations_not_list")
        observations = []
    for index, observation in enumerate(observations):
        if not isinstance(observation, dict):
            errors.append(f"observation_invalid:{index}")
            continue
        missing = sorted(REQUIRED_OBSERVATION_FIELDS - set(observation))
        if missing:
            errors.append(f"observation_missing_fields:{index}:{','.join(missing)}")
        if observation.get("authority") != "read_only_context_only":
            errors.append(f"observation_authority_invalid:{index}")
        for key, expected in AUTHORITY_FLAGS.items():
            if observation.get(key) is not expected:
                errors.append(f"observation_authority_enabled:{index}:{key}")
    safety = packet.get("paperops_safety")
    if not isinstance(safety, dict):
        errors.append("paperops_safety_missing")
    else:
        for key in (
            "cannot_create_trade_candidate_alone",
            "cannot_satisfy_minimum_source_quorum_alone",
            "cannot_approve_risk",
            "cannot_stage_orders",
            "cannot_submit_orders",
            "cannot_grant_paper_proof_ledger_credit",
            "guarded_alpaca_paper_route_unchanged",
        ):
            if safety.get(key) is not True:
                errors.append(f"paperops_safety_not_true:{key}")
    return sorted(set(errors))


async def fetch_reddit_narrative_proxy_live_packet(
    *,
    settings: Settings | None = None,
    timeout_seconds: float = 12.0,
) -> RedditNarrativeProxyResult:
    generated_at = _now()
    try:
        import httpx
    except ImportError:
        packet = build_reddit_narrative_proxy_packet(
            {"filters": {}},
            settings=settings,
            generated_at=generated_at,
            degraded=True,
            degraded_reason="missing_dependency:httpx",
            live_mode=True,
        )
        return RedditNarrativeProxyResult(packet=packet, degraded=True, degraded_reason="missing_dependency:httpx")

    filters: dict[str, Any] = {}
    errors: dict[str, str] = {}
    async with httpx.AsyncClient(timeout=timeout_seconds, follow_redirects=True) as client:
        for filter_key, endpoint in APEWISDOM_ENDPOINTS.items():
            try:
                response = await client.get(endpoint, headers={"User-Agent": "Qadam/0.1 reddit narrative proxy"})
                response.raise_for_status()
                filters[filter_key] = response.json()
            except Exception as exc:  # noqa: BLE001 - provider failures must degrade safely.
                errors[filter_key] = f"{exc.__class__.__name__}:{exc}"

    degraded = not filters
    degraded_reason = "apewisdom_unavailable" if degraded else ("apewisdom_partial_unavailable" if errors else None)
    packet = build_reddit_narrative_proxy_packet(
        {
            "sample": False,
            "generated_at": generated_at,
            "filters": filters,
            "provider_errors": errors,
        },
        settings=settings,
        generated_at=generated_at,
        degraded=degraded,
        degraded_reason=degraded_reason,
        live_mode=True,
    )
    return RedditNarrativeProxyResult(packet=packet, degraded=degraded, degraded_reason=degraded_reason)


def reddit_narrative_proxy_events(packet: dict[str, Any]) -> tuple[UnifiedEvent, ...]:
    events: list[UnifiedEvent] = []
    for observation in packet.get("observations", [])[:25]:
        if not isinstance(observation, dict):
            continue
        ticker = str(observation.get("ticker") or "unknown")
        crowding = str(observation.get("crowding_risk") or "unknown")
        use = str(observation.get("qadam_use") or "context")
        summary = (
            f"{ticker} retail attention {use}; mentions {observation.get('mentions')} "
            f"vs {observation.get('mentions_24h_ago')} 24h ago; crowding risk {crowding}."
        )
        events.append(
            UnifiedEvent(
                schema_version=UNIFIED_EVENT_SCHEMA_VERSION,
                event_id=str(uuid4()),
                source="social.reddit_narrative_proxy",
                trust_score_at_ingestion=TRUST_SCORE_SEED,
                event_type="social_signal",
                raw_payload={
                    "source_key": REDDIT_NARRATIVE_PROXY_SOURCE_KEY,
                    "registry_slot": REDDIT_NARRATIVE_PROXY_REGISTRY_SLOT,
                    "ticker": ticker,
                    "rank": observation.get("rank"),
                    "source_variant": REDDIT_NARRATIVE_PROXY_SOURCE_VARIANT,
                    "source_quorum_credit_allowed": False,
                    "trade_candidate_creation_allowed": False,
                },
                normalised_summary=summary[:240],
                coordinates=None,
                ingested_at=str(observation.get("collected_at") or packet.get("generated_at") or _now()),
                linked_catalyst_id=None,
            )
        )
    return tuple(events)


def reddit_narrative_proxy_envelope_from_packet(
    packet: dict[str, Any],
    *,
    settings: Settings | None = None,
    archive: RawPayloadArchive | None = None,
    event_log: EventLog | None = None,
) -> SourceEnvelope:
    settings = settings or Settings.from_env()
    archive = archive or RawPayloadArchive(settings)
    event_log = event_log or EventLog(echo=False)
    archive_path = archive.write(REDDIT_NARRATIVE_PROXY_REGISTRY_SLOT, packet)
    envelope = SourceEnvelope(
        events=reddit_narrative_proxy_events(packet),
        source="social.reddit_narrative_proxy",
        trust_score=TRUST_SCORE_SEED,
        fetched_at=_now(),
        degraded=packet.get("degraded") is True,
        degraded_reason=packet.get("degraded_reason"),
        raw_archive_path=str(archive_path),
    )
    event_log.write(
        "source_adapter_fetch_completed",
        "reddit_narrative_proxy",
        {
            "source": envelope.source,
            "source_key": REDDIT_NARRATIVE_PROXY_SOURCE_KEY,
            "registry_slot": REDDIT_NARRATIVE_PROXY_REGISTRY_SLOT,
            "event_count": len(envelope.events),
            "degraded": envelope.degraded,
            "degraded_reason": envelope.degraded_reason,
            "raw_archive_path": envelope.raw_archive_path,
            "source_quorum_credit_allowed": False,
            "execution_allowed": False,
        },
    )
    return envelope


def fetch_reddit_narrative_proxy_sample_envelope(
    *,
    settings: Settings | None = None,
    archive: RawPayloadArchive | None = None,
    event_log: EventLog | None = None,
) -> SourceEnvelope:
    packet = build_reddit_narrative_proxy_packet(settings=settings)
    return reddit_narrative_proxy_envelope_from_packet(
        packet,
        settings=settings,
        archive=archive,
        event_log=event_log,
    )


async def fetch_reddit_narrative_proxy_live_envelope(
    *,
    settings: Settings | None = None,
    archive: RawPayloadArchive | None = None,
    event_log: EventLog | None = None,
    timeout_seconds: float = 12.0,
) -> SourceEnvelope:
    result = await fetch_reddit_narrative_proxy_live_packet(
        settings=settings,
        timeout_seconds=timeout_seconds,
    )
    return reddit_narrative_proxy_envelope_from_packet(
        result.packet,
        settings=settings,
        archive=archive,
        event_log=event_log,
    )


def write_reddit_narrative_proxy_artifact(
    packet: dict[str, Any],
    settings: Settings | None = None,
) -> tuple[Path, Path, Path]:
    runtime = _runtime_dir(settings)
    artifact_path = runtime / REDDIT_NARRATIVE_PROXY_RUNTIME_ARTIFACT
    history_path = runtime / REDDIT_NARRATIVE_PROXY_HISTORY
    event_path = runtime / REDDIT_NARRATIVE_PROXY_EVENT_LOG
    artifact_path.parent.mkdir(parents=True, exist_ok=True)
    artifact_path.write_text(json.dumps(packet, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    with history_path.open("a", encoding="utf-8") as handle:
        handle.write(
            json.dumps(
                {
                    "schema_version": REDDIT_NARRATIVE_PROXY_SCHEMA_VERSION,
                    "artifact_id": packet.get("artifact_id"),
                    "status": packet.get("status"),
                    "recorded_at": _now(),
                    "observation_count": packet.get("observation_count"),
                    "validation_error_count": packet.get("validation_error_count"),
                    "degraded": packet.get("degraded"),
                    "source_quorum_credit_allowed": False,
                },
                sort_keys=True,
            )
            + "\n"
        )
    EventLog(event_path, echo=False).write(
        "reddit_narrative_proxy_validated",
        "reddit_narrative_proxy",
        {
            "status": packet.get("status"),
            "observation_count": packet.get("observation_count"),
            "validation_error_count": packet.get("validation_error_count"),
            "source_quorum_credit_allowed": False,
            "trade_candidate_creation_allowed": False,
            "execution_allowed": False,
        },
    )
    return artifact_path, history_path, event_path


def reddit_narrative_proxy_public_status(settings: Settings | None = None) -> dict[str, Any]:
    artifact = _read_json(_runtime_dir(settings) / REDDIT_NARRATIVE_PROXY_RUNTIME_ARTIFACT)
    if not artifact:
        artifact = build_reddit_narrative_proxy_packet(settings=settings)
    return {
        "schema_version": artifact.get("schema_version"),
        "status": artifact.get("status"),
        "source_key": artifact.get("source_key"),
        "source_variant": artifact.get("source_variant"),
        "source_registry_slot": artifact.get("source_registry_slot"),
        "reddit_oauth_state": artifact.get("reddit_oauth_state"),
        "credential_required": artifact.get("credential_required"),
        "observation_count": artifact.get("observation_count"),
        "trust_score_seed": artifact.get("trust_score_seed"),
        "primary_source_quorum_allowed": artifact.get("primary_source_quorum_allowed"),
        "cannot_originate_trade": artifact.get("cannot_originate_trade"),
        "public_dashboard_copy": artifact.get("public_dashboard_copy"),
        "authority_flags": artifact.get("authority_flags"),
        "validation_error_count": artifact.get("validation_error_count"),
        "public_safe": artifact.get("public_safe"),
        "command_disabled": artifact.get("command_disabled"),
    }


def fetch_reddit_narrative_proxy_live_envelope_sync(
    *,
    settings: Settings | None = None,
    archive: RawPayloadArchive | None = None,
    event_log: EventLog | None = None,
    timeout_seconds: float = 12.0,
) -> SourceEnvelope:
    return asyncio.run(
        fetch_reddit_narrative_proxy_live_envelope(
            settings=settings,
            archive=archive,
            event_log=event_log,
            timeout_seconds=timeout_seconds,
        )
    )
