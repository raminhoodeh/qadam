"""Provider-decision contracts for unresolved optional/local sources.

This module records provider choices without pretending those providers are
connected. It is public-safe, read-only, and carries no execution authority.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any


PROVIDER_DECISION_PASS_SCHEMA_VERSION = 1


@dataclass(frozen=True)
class ProviderDecision:
    source_key: str
    decision_status: str
    selected_provider: str
    provider_class: str
    activation_state: str
    access_pattern: str
    endpoint_policy: str
    credential_policy: str
    evidence_packet_types: tuple[str, ...]
    qadam_role: str
    selected_for_current_paper_core: bool
    credential_required_now: bool
    adapter_work_required: bool
    local_bridge_required: bool
    setup_url: str
    next_action: str
    notes: str = ""


PROVIDER_DECISIONS: dict[str, ProviderDecision] = {
    "rapidapi": ProviderDecision(
        source_key="rapidapi",
        decision_status="marketplace_disabled_no_provider",
        selected_provider="none",
        provider_class="marketplace_not_source",
        activation_state="disabled_until_specific_provider_selected",
        access_pattern="no_adapter",
        endpoint_policy="RapidAPI is a marketplace wrapper, not a canonical Qadam source.",
        credential_policy="Do not request or store RAPIDAPI_KEY until a concrete RapidAPI-backed provider is selected.",
        evidence_packet_types=(),
        qadam_role="not_used",
        selected_for_current_paper_core=False,
        credential_required_now=False,
        adapter_work_required=False,
        local_bridge_required=False,
        setup_url="https://rapidapi.com/hub",
        next_action="Select a specific RapidAPI-backed provider only if it fills a named Qadam evidence gap.",
        notes="Keeps RapidAPI out of missing-credential counts and source quorum.",
    ),
    "coinglass": ProviderDecision(
        source_key="coinglass",
        decision_status="provider_selected_pending_adapter",
        selected_provider="CoinGlass API",
        provider_class="hosted_market_data_api",
        activation_state="optional_adapter_not_built",
        access_pattern="read_only_http_api",
        endpoint_policy="Use the current official CoinGlass API reference when the adapter is built; do not rely on stale v2 paths without revalidation.",
        credential_policy="Do not request COINGLASS_API_KEY until Qadam explicitly promotes crypto/perps derivatives context.",
        evidence_packet_types=("funding_context", "open_interest_context", "liquidation_context"),
        qadam_role="optional_crypto_derivatives_context",
        selected_for_current_paper_core=False,
        credential_required_now=False,
        adapter_work_required=True,
        local_bridge_required=False,
        setup_url="https://docs.coinglass.com/reference",
        next_action="Build a read-only sample adapter only if crypto/perps becomes part of an approved Qadam strategy surface.",
        notes="Provider decision is recorded, but Coinglass is not needed for current oil/defence/silver/semiconductor paper mode.",
    ),
    "chainlink": ProviderDecision(
        source_key="chainlink",
        decision_status="provider_selected_pending_public_adapter",
        selected_provider="Chainlink Data Feeds",
        provider_class="public_oracle_network",
        activation_state="optional_public_adapter_not_built",
        access_pattern="public_feed_catalog_plus_read_only_rpc",
        endpoint_policy="Use data.chain.link/feed contract metadata and read AggregatorV3 latestRoundData through a read-only EVM RPC path when implemented.",
        credential_policy="No RPC credential is required now. ETH_RPC_URL remains optional until a read-only adapter exists.",
        evidence_packet_types=("oracle_price_crosscheck", "stale_feed_context", "market_price_integrity_context"),
        qadam_role="optional_price_integrity_crosscheck",
        selected_for_current_paper_core=False,
        credential_required_now=False,
        adapter_work_required=True,
        local_bridge_required=False,
        setup_url="https://docs.chain.link/data-feeds",
        next_action="Build a public feed-catalog/read-only RPC adapter before requesting any paid RPC credential.",
        notes="Chainlink is useful as a corroboration layer, not as a trade signal or execution venue.",
    ),
    "github": ProviderDecision(
        source_key="github",
        decision_status="provider_selected_pending_public_adapter",
        selected_provider="GitHub REST API",
        provider_class="public_developer_activity_api",
        activation_state="optional_public_adapter_not_built",
        access_pattern="public_rest_search_first_optional_pat_later",
        endpoint_policy="Use GitHub REST search/repository/release endpoints against a narrow Qadam watchlist.",
        credential_policy="No GITHUB_TOKEN is required now. Add a fine-grained read-only token only if rate limits block the approved watchlist.",
        evidence_packet_types=("technology_release_context", "developer_velocity_context", "supply_chain_software_context"),
        qadam_role="optional_technology_supply_chain_context",
        selected_for_current_paper_core=False,
        credential_required_now=False,
        adapter_work_required=True,
        local_bridge_required=False,
        setup_url="https://docs.github.com/en/rest",
        next_action="Define a semiconductor/AI-infrastructure repository watchlist before building the adapter.",
        notes="GitHub must never become a broad social scrape; it needs a narrow repo and release-event scope.",
    ),
    "bookmap": ProviderDecision(
        source_key="bookmap",
        decision_status="local_bridge_selected",
        selected_provider="Bookmap local API bridge",
        provider_class="local_desktop_bridge",
        activation_state="local_bridge_required",
        access_pattern="local_websocket_from_bookmap_addon_or_brapi_consumer",
        endpoint_policy="Use a local read-only bridge such as ws://localhost:8765/bookmap; do not expose Bookmap data through hosted public endpoints.",
        credential_policy="No hosted API key. Requires the user's local Bookmap install, market-data entitlements, and an explicitly read-only local bridge.",
        evidence_packet_types=("orderflow_context", "absorption_context", "sweep_context", "microstructure_confirmation"),
        qadam_role="optional_local_orderflow_confirmation",
        selected_for_current_paper_core=False,
        credential_required_now=False,
        adapter_work_required=True,
        local_bridge_required=True,
        setup_url="https://bookmap.com/knowledgebase/docs/API",
        next_action="Build/run the local read-only bridge on the Mac only when the operator wants Bookmap order-flow context.",
        notes="Bookmap remains local-only; Qadam must not use its inject/order-management capabilities.",
    ),
}


def provider_decision_state(source_key: str) -> dict[str, Any] | None:
    decision = PROVIDER_DECISIONS.get(source_key)
    if decision is None:
        return None
    payload = asdict(decision)
    payload.update(
        {
            "schema_version": PROVIDER_DECISION_PASS_SCHEMA_VERSION,
            "source_key": source_key,
            "source_authority": "observation_only_after_adapter_exists",
            "signal_authority": "none_without_strategy_and_risk_gates",
            "order_authority": "none",
            "broker_write_authority": False,
            "live_capital_authority": False,
            "paper_trading_blocking": False,
            "public_safe": True,
            "boundary": (
                "Provider decision only. It cannot fetch live data, create evidence, approve signals, "
                "submit orders, call brokers, or enable live capital."
            ),
        }
    )
    return payload


def provider_decision_registry() -> dict[str, Any]:
    states = [provider_decision_state(key) for key in PROVIDER_DECISIONS]
    safe_states = [state for state in states if state is not None]
    return {
        "schema_version": PROVIDER_DECISION_PASS_SCHEMA_VERSION,
        "status": "ok",
        "decision_count": len(safe_states),
        "provider_selected_pending_adapter_count": sum(
            1 for state in safe_states if state["decision_status"].startswith("provider_selected")
        ),
        "marketplace_disabled_count": sum(
            1 for state in safe_states if state["decision_status"] == "marketplace_disabled_no_provider"
        ),
        "local_bridge_selected_count": sum(
            1 for state in safe_states if state["decision_status"] == "local_bridge_selected"
        ),
        "credential_required_now_count": sum(1 for state in safe_states if state["credential_required_now"]),
        "adapter_work_required_count": sum(1 for state in safe_states if state["adapter_work_required"]),
        "local_bridge_required_count": sum(1 for state in safe_states if state["local_bridge_required"]),
        "states": safe_states,
        "boundary": "Provider decisions are planning/readiness metadata only and cannot create trades.",
    }


def provider_decision_keys() -> tuple[str, ...]:
    return tuple(PROVIDER_DECISIONS)
