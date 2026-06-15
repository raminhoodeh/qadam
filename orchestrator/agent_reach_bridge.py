"""Agent Reach source-enrichment bridge.

Agent Reach is treated as a local read-only capability map for internet/social
sources. It can tell Qadam which upstream tools could enrich research evidence,
but it must not create canonical source count, source quorum, trades, orders,
broker writes, browser authority, cookies, or live capital.
"""

from __future__ import annotations

import json
import os
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

from orchestrator.config import Settings
from world_monitor.source_registry import EXPECTED_SOURCE_COUNT


AGENT_REACH_BRIDGE_SCHEMA_VERSION = 1
AGENT_REACH_BRIDGE_SOURCE_KEY = "agent_reach"
AGENT_REACH_BRIDGE_PROVIDER_LABEL = "local_agent_reach_reference"
AGENT_REACH_BRIDGE_CLASSIFICATION = "supplemental_internet_reach_capability_layer"
AGENT_REACH_BRIDGE_PACKET_TYPE = "social_news_discovery_packet"
AGENT_REACH_BRIDGE_CONTEXT_ROLE = "supplemental_social_news_discovery_only"
AGENT_REACH_BRIDGE_BOUNDARY = (
    "Agent Reach bridge is read-only internet reach metadata. It can expose "
    "which local upstream tools could enrich web, news, social, video, forum, "
    "and developer evidence after separate operator setup, but it cannot "
    "create source quorum, trade candidates, risk approval, paper orders, "
    "broker writes, cookies, browser control, quantum jobs, or live capital."
)

AUTHORITY_FALSE_FIELDS: tuple[str, ...] = (
    "source_quorum_credit_allowed",
    "signal_authority",
    "risk_approval_authority",
    "trade_candidate_creation_allowed",
    "execution_allowed",
    "paper_order_allowed",
    "broker_write_allowed",
    "quantum_job_authority",
    "live_capital_enabled",
    "raw_payload_exposed",
    "local_path_exposed",
    "cookies_exposed",
    "browser_session_authority",
)


@dataclass(frozen=True)
class AgentReachChannelMapping:
    channel_key: str
    display_name: str
    channel_file: str
    access_level: str
    preferred_backends: tuple[str, ...]
    qadam_alignment: str
    qadam_existing_source_keys: tuple[str, ...]
    gap_coverage: tuple[str, ...]
    evidence_packet_types: tuple[str, ...]
    trading_relevance: str
    selected_for_runtime_evidence: bool
    setup_note: str
    trust_score: float


AGENT_REACH_CHANNELS: tuple[AgentReachChannelMapping, ...] = (
    AgentReachChannelMapping(
        channel_key="rss",
        display_name="RSS / Atom",
        channel_file="rss.py",
        access_level="zero_config",
        preferred_backends=("feedparser",),
        qadam_alignment="Existing Qadam RSS/news source. Use as curated news-feed expansion.",
        qadam_existing_source_keys=("rss",),
        gap_coverage=("news_feed_depth", "oil_defence_semiconductor_headlines"),
        evidence_packet_types=("news_feed_context", "headline_velocity_context"),
        trading_relevance="event_discovery_and_corroboration",
        selected_for_runtime_evidence=True,
        setup_note="No credential required for public feeds.",
        trust_score=0.72,
    ),
    AgentReachChannelMapping(
        channel_key="web",
        display_name="Web Reader",
        channel_file="web.py",
        access_level="zero_config",
        preferred_backends=("jina_reader",),
        qadam_alignment="Supplemental article/webpage reader for narrative evidence and source verification.",
        qadam_existing_source_keys=("gdelt", "rss"),
        gap_coverage=("article_readback", "source_verification"),
        evidence_packet_types=("web_article_context", "source_readback_context"),
        trading_relevance="article_validation_before_strategy_review",
        selected_for_runtime_evidence=True,
        setup_note="Reads public pages; do not scrape authenticated pages into public artifacts.",
        trust_score=0.68,
    ),
    AgentReachChannelMapping(
        channel_key="exa_search",
        display_name="Exa Search",
        channel_file="exa_search.py",
        access_level="mcp_or_local_setup",
        preferred_backends=("exa_mcp_via_mcporter",),
        qadam_alignment="Supplemental semantic web search for source discovery.",
        qadam_existing_source_keys=("gdelt", "rss", "reddit", "twitter_x"),
        gap_coverage=("web_search_discovery", "reddit_site_search", "x_site_search"),
        evidence_packet_types=("search_discovery_context", "source_discovery_context"),
        trading_relevance="find_missing_context_for_research_goals",
        selected_for_runtime_evidence=True,
        setup_note="Requires MCP/local tool setup; no Qadam provider calls from this bridge.",
        trust_score=0.62,
    ),
    AgentReachChannelMapping(
        channel_key="twitter",
        display_name="Twitter / X",
        channel_file="twitter.py",
        access_level="login_or_cookie_required",
        preferred_backends=("twitter-cli", "opencli", "bird"),
        qadam_alignment="Existing Qadam X/Twitter source. Agent Reach adds local cookie/browser-session fallback.",
        qadam_existing_source_keys=("twitter_x",),
        gap_coverage=("x_discussion_context", "api_rate_limit_fallback"),
        evidence_packet_types=("social_attention_context", "narrative_velocity_context"),
        trading_relevance="social_reaction_and_edge_decay_context",
        selected_for_runtime_evidence=True,
        setup_note="Use a dedicated read-only/social account; never expose cookies in Qadam artifacts.",
        trust_score=0.58,
    ),
    AgentReachChannelMapping(
        channel_key="reddit",
        display_name="Reddit",
        channel_file="reddit.py",
        access_level="login_or_cookie_required",
        preferred_backends=("opencli", "rdt-cli"),
        qadam_alignment="Existing optional Qadam Reddit gap. Agent Reach points to a practical logged-in local route.",
        qadam_existing_source_keys=("reddit",),
        gap_coverage=("reddit_credentials_missing", "retail_forum_context"),
        evidence_packet_types=("retail_attention_context", "forum_reaction_context"),
        trading_relevance="retail_attention_and_consensus_extreme_context",
        selected_for_runtime_evidence=True,
        setup_note="Anonymous Reddit is unreliable; use local login/session only and keep it read-only.",
        trust_score=0.55,
    ),
    AgentReachChannelMapping(
        channel_key="github",
        display_name="GitHub",
        channel_file="github.py",
        access_level="zero_config_public",
        preferred_backends=("gh_cli",),
        qadam_alignment="Existing optional GitHub provider decision. Use for narrow semiconductor/AI-infra watchlists.",
        qadam_existing_source_keys=("github",),
        gap_coverage=("github_adapter_pending", "technology_supply_chain_context"),
        evidence_packet_types=("technology_release_context", "developer_velocity_context"),
        trading_relevance="semiconductor_ai_infrastructure_context",
        selected_for_runtime_evidence=True,
        setup_note="Public reads first; add read-only token only if rate limits block an approved watchlist.",
        trust_score=0.6,
    ),
    AgentReachChannelMapping(
        channel_key="youtube",
        display_name="YouTube",
        channel_file="youtube.py",
        access_level="zero_config",
        preferred_backends=("yt-dlp",),
        qadam_alignment="Supplemental video/transcript source for public briefings, interviews, and technical explainers.",
        qadam_existing_source_keys=(),
        gap_coverage=("video_transcript_context", "public_briefing_context"),
        evidence_packet_types=("video_transcript_context", "public_briefing_context"),
        trading_relevance="event_explanation_and_source_context",
        selected_for_runtime_evidence=True,
        setup_note="Transcript/readback only; no account authority.",
        trust_score=0.52,
    ),
    AgentReachChannelMapping(
        channel_key="linkedin",
        display_name="LinkedIn",
        channel_file="linkedin.py",
        access_level="mcp_or_local_setup",
        preferred_backends=("linkedin_mcp", "jina_reader"),
        qadam_alignment="Supplemental company/people movement context for defence, energy, and semiconductor firms.",
        qadam_existing_source_keys=(),
        gap_coverage=("company_people_movement_context",),
        evidence_packet_types=("company_people_context", "hiring_signal_context"),
        trading_relevance="slow_signal_company_intelligence",
        selected_for_runtime_evidence=False,
        setup_note="Use public pages or local MCP only; do not expose private profile data.",
        trust_score=0.46,
    ),
    AgentReachChannelMapping(
        channel_key="v2ex",
        display_name="V2EX",
        channel_file="v2ex.py",
        access_level="zero_config",
        preferred_backends=("public_api",),
        qadam_alignment="Supplemental developer forum context for AI infrastructure and software supply-chain chatter.",
        qadam_existing_source_keys=(),
        gap_coverage=("developer_forum_context",),
        evidence_packet_types=("developer_forum_context",),
        trading_relevance="technology_sentiment_context",
        selected_for_runtime_evidence=True,
        setup_note="Public forum context only; corroboration required.",
        trust_score=0.44,
    ),
    AgentReachChannelMapping(
        channel_key="xueqiu",
        display_name="Xueqiu",
        channel_file="xueqiu.py",
        access_level="login_or_cookie_optional",
        preferred_backends=("public_or_cookie_cli",),
        qadam_alignment="Supplemental China-market social/retail context for semiconductors and commodities.",
        qadam_existing_source_keys=(),
        gap_coverage=("china_market_social_context",),
        evidence_packet_types=("china_market_social_context",),
        trading_relevance="regional_retail_attention_context",
        selected_for_runtime_evidence=True,
        setup_note="Prefer public readback; keep cookies local if used.",
        trust_score=0.43,
    ),
    AgentReachChannelMapping(
        channel_key="bilibili",
        display_name="Bilibili",
        channel_file="bilibili.py",
        access_level="zero_config",
        preferred_backends=("bili-cli", "opencli"),
        qadam_alignment="Supplemental China video/search context for technology narratives and public commentary.",
        qadam_existing_source_keys=(),
        gap_coverage=("china_video_context",),
        evidence_packet_types=("china_video_context", "video_search_context"),
        trading_relevance="regional_narrative_context",
        selected_for_runtime_evidence=False,
        setup_note="Search/readback only; no account authority.",
        trust_score=0.4,
    ),
    AgentReachChannelMapping(
        channel_key="xiaohongshu",
        display_name="Xiaohongshu",
        channel_file="xiaohongshu.py",
        access_level="login_or_cookie_required",
        preferred_backends=("opencli", "xiaohongshu-mcp", "xhs-cli"),
        qadam_alignment="Supplemental China consumer/social context; relevant only when a strategy needs it.",
        qadam_existing_source_keys=(),
        gap_coverage=("china_consumer_social_context",),
        evidence_packet_types=("consumer_social_context",),
        trading_relevance="regional_consumer_narrative_context",
        selected_for_runtime_evidence=False,
        setup_note="Use a dedicated account if ever enabled; no cookies in artifacts.",
        trust_score=0.36,
    ),
    AgentReachChannelMapping(
        channel_key="xiaoyuzhou",
        display_name="Xiaoyuzhou Podcast",
        channel_file="xiaoyuzhou.py",
        access_level="mcp_or_local_setup",
        preferred_backends=("whisper_transcription",),
        qadam_alignment="Supplemental podcast/audio transcription for long-form commentary.",
        qadam_existing_source_keys=(),
        gap_coverage=("podcast_transcript_context",),
        evidence_packet_types=("podcast_transcript_context",),
        trading_relevance="slow_narrative_context",
        selected_for_runtime_evidence=False,
        setup_note="Transcription/readback only; no account authority.",
        trust_score=0.34,
    ),
)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def _agent_reach_root() -> Path:
    return _repo_root() / "Agent-Reach-main"


def _channel_dir() -> Path:
    return _agent_reach_root() / "agent_reach/channels"


def _runtime_dir(settings: Settings | None = None) -> Path:
    return Path((settings or Settings.from_env()).runtime_dir)


def _available_channel_files() -> set[str]:
    channel_dir = _channel_dir()
    if not channel_dir.exists():
        return set()
    return {
        path.name
        for path in channel_dir.glob("*.py")
        if path.name not in {"__init__.py", "base.py"}
    }


def _public_channel(mapping: AgentReachChannelMapping, available_files: set[str]) -> dict[str, Any]:
    payload = asdict(mapping)
    payload.update(
        {
            "channel_available": mapping.channel_file in available_files,
            "backend_probe_status": "not_invoked_by_qadam",
            "source_quorum_credit_allowed": False,
            "signal_authority": False,
            "risk_approval_authority": False,
            "trade_candidate_creation_allowed": False,
            "execution_allowed": False,
            "paper_order_allowed": False,
            "broker_write_allowed": False,
            "quantum_job_authority": False,
            "live_capital_enabled": False,
            "raw_payload_exposed": False,
            "local_path_exposed": False,
            "cookies_exposed": False,
            "browser_session_authority": False,
            "public_safe": True,
        }
    )
    return payload


def build_agent_reach_bridge_status(
    *,
    settings: Settings | None = None,
    generated_at: str | None = None,
) -> dict[str, Any]:
    available_files = _available_channel_files()
    reference_checkout_available = _agent_reach_root().exists() and _channel_dir().exists()
    channels = [_public_channel(mapping, available_files) for mapping in AGENT_REACH_CHANNELS]
    missing_channel_keys = [
        channel["channel_key"]
        for channel in channels
        if channel["channel_available"] is not True
    ]
    selected_runtime_channels = [
        channel for channel in channels if channel["selected_for_runtime_evidence"] is True
    ]
    access_counts = {
        "zero_config": sum(1 for channel in channels if str(channel["access_level"]).startswith("zero_config")),
        "login_or_cookie": sum(1 for channel in channels if "login_or_cookie" in str(channel["access_level"])),
        "mcp_or_local_setup": sum(1 for channel in channels if channel["access_level"] == "mcp_or_local_setup"),
    }
    status = "reference_ready"
    if not reference_checkout_available:
        status = "missing_reference"
    elif missing_channel_keys:
        status = "degraded"

    payload = {
        "schema_version": AGENT_REACH_BRIDGE_SCHEMA_VERSION,
        "source_key": AGENT_REACH_BRIDGE_SOURCE_KEY,
        "provider_label": AGENT_REACH_BRIDGE_PROVIDER_LABEL,
        "classification": AGENT_REACH_BRIDGE_CLASSIFICATION,
        "status": status,
        "generated_at": generated_at or _now(),
        "enabled": True,
        "reference_checkout_available": reference_checkout_available,
        "channel_file_count": len(available_files),
        "mapped_channel_count": len(channels),
        "available_mapped_channel_count": sum(1 for channel in channels if channel["channel_available"] is True),
        "missing_channel_count": len(missing_channel_keys),
        "missing_channel_keys": missing_channel_keys,
        "selected_runtime_evidence_channel_count": len(selected_runtime_channels),
        "selected_runtime_evidence_channels": [
            channel["channel_key"] for channel in selected_runtime_channels
        ],
        "qadam_existing_source_match_count": sum(
            1 for channel in channels if channel["qadam_existing_source_keys"]
        ),
        "canonical_source_count": EXPECTED_SOURCE_COUNT,
        "counts_as_canonical_source": False,
        "zero_config_channel_count": access_counts["zero_config"],
        "login_or_cookie_channel_count": access_counts["login_or_cookie"],
        "mcp_or_local_setup_channel_count": access_counts["mcp_or_local_setup"],
        "browser_session_required_count": access_counts["login_or_cookie"],
        "sample_mode_available": True,
        "live_backend_probe_allowed": False,
        "agent_reach_install_allowed": False,
        "evidence_packet_type": AGENT_REACH_BRIDGE_PACKET_TYPE,
        "evidence_context_role": AGENT_REACH_BRIDGE_CONTEXT_ROLE,
        "evidence_item_count": len(selected_runtime_channels),
        "channels": channels,
        "gap_coverage": sorted(
            {
                gap
                for channel in selected_runtime_channels
                for gap in channel.get("gap_coverage", [])
                if gap
            }
        ),
        "public_safe": True,
        "boundary": AGENT_REACH_BRIDGE_BOUNDARY,
    }
    for field in AUTHORITY_FALSE_FIELDS:
        payload[field] = False
    return payload


def agent_reach_bridge_public_status(settings: Settings | None = None) -> dict[str, Any]:
    return build_agent_reach_bridge_status(settings=settings)


def agent_reach_bridge_evidence_items(status: dict[str, Any] | None = None) -> list[dict[str, Any]]:
    status = status or build_agent_reach_bridge_status()
    generated_at = str(status.get("generated_at") or _now())
    items: list[dict[str, Any]] = []
    for channel in status.get("channels", []):
        if not isinstance(channel, dict) or channel.get("selected_for_runtime_evidence") is not True:
            continue
        items.append(
            {
                "evidence_id": f"agent_reach:{channel.get('channel_key')}",
                "source": f"agent_reach.{channel.get('channel_key')}",
                "source_key": AGENT_REACH_BRIDGE_SOURCE_KEY,
                "event_type": "agent_reach_channel_mapping",
                "summary": (
                    f"{channel.get('display_name')} can enrich Qadam as "
                    f"{channel.get('trading_relevance')} through "
                    f"{', '.join(channel.get('preferred_backends', []) or [])}. "
                    f"Access posture: {channel.get('access_level')}. "
                    f"Qadam alignment: {channel.get('qadam_alignment')}"
                ),
                "trust_score": channel.get("trust_score", 0.0),
                "observed_at": generated_at,
                "public_safe": True,
            }
        )
    return items


def validate_agent_reach_bridge_status(status: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    required = {
        "schema_version",
        "source_key",
        "provider_label",
        "classification",
        "status",
        "enabled",
        "reference_checkout_available",
        "channel_file_count",
        "mapped_channel_count",
        "available_mapped_channel_count",
        "selected_runtime_evidence_channel_count",
        "qadam_existing_source_match_count",
        "canonical_source_count",
        "counts_as_canonical_source",
        "zero_config_channel_count",
        "login_or_cookie_channel_count",
        "mcp_or_local_setup_channel_count",
        "browser_session_required_count",
        "sample_mode_available",
        "live_backend_probe_allowed",
        "agent_reach_install_allowed",
        "evidence_packet_type",
        "evidence_context_role",
        "evidence_item_count",
        "channels",
        "gap_coverage",
        "public_safe",
        "boundary",
        *AUTHORITY_FALSE_FIELDS,
    }
    missing = sorted(required - set(status))
    errors.extend(f"missing_field:{field}" for field in missing)
    if status.get("schema_version") != AGENT_REACH_BRIDGE_SCHEMA_VERSION:
        errors.append("schema_version_mismatch")
    if status.get("source_key") != AGENT_REACH_BRIDGE_SOURCE_KEY:
        errors.append("source_key_mismatch")
    if status.get("provider_label") != AGENT_REACH_BRIDGE_PROVIDER_LABEL:
        errors.append("provider_label_mismatch")
    if status.get("classification") != AGENT_REACH_BRIDGE_CLASSIFICATION:
        errors.append("classification_mismatch")
    if status.get("status") not in {"reference_ready", "missing_reference", "degraded"}:
        errors.append("status_invalid")
    if status.get("status") != "reference_ready":
        errors.append("reference_not_ready")
    if status.get("reference_checkout_available") is not True:
        errors.append("reference_checkout_missing")
    if int(status.get("mapped_channel_count", 0) or 0) < 13:
        errors.append("mapped_channel_count_too_low")
    if int(status.get("available_mapped_channel_count", 0) or 0) < int(status.get("mapped_channel_count", 0) or 0):
        errors.append("available_channel_count_mismatch")
    if int(status.get("selected_runtime_evidence_channel_count", 0) or 0) < 8:
        errors.append("runtime_evidence_channel_count_too_low")
    if int(status.get("qadam_existing_source_match_count", 0) or 0) < 5:
        errors.append("qadam_existing_source_match_count_too_low")
    if status.get("canonical_source_count") != EXPECTED_SOURCE_COUNT:
        errors.append("canonical_source_count_mismatch")
    if status.get("counts_as_canonical_source") is not False:
        errors.append("counts_as_canonical_source_true")
    if status.get("public_safe") is not True:
        errors.append("public_safe_not_true")
    if status.get("live_backend_probe_allowed") is not False:
        errors.append("live_backend_probe_allowed")
    if status.get("agent_reach_install_allowed") is not False:
        errors.append("agent_reach_install_allowed")
    for field in AUTHORITY_FALSE_FIELDS:
        if status.get(field) is not False:
            errors.append(f"authority_enabled:{field}")
    for channel in status.get("channels", []):
        if not isinstance(channel, dict):
            errors.append("channel_not_object")
            continue
        if channel.get("public_safe") is not True:
            errors.append(f"channel_not_public_safe:{channel.get('channel_key')}")
        for field in AUTHORITY_FALSE_FIELDS:
            if channel.get(field) is not False:
                errors.append(f"channel_authority_enabled:{channel.get('channel_key')}:{field}")
    boundary = str(status.get("boundary") or "")
    for phrase in ("read-only internet reach", "cannot create source quorum", "paper orders", "broker writes"):
        if phrase not in boundary:
            errors.append(f"boundary_missing:{phrase}")
    return errors


def write_agent_reach_bridge_snapshot(settings: Settings | None = None) -> dict[str, Any]:
    settings = settings or Settings.from_env()
    status = build_agent_reach_bridge_status(settings=settings)
    path = _runtime_dir(settings) / "agent_reach_bridge.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    temp_path.write_text(json.dumps(status, indent=2, sort_keys=True), encoding="utf-8")
    temp_path.replace(path)
    return status
