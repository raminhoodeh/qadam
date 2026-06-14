"""Credential-bound read-only source contracts.

This module tracks sources that are implemented only up to the point where
provider credentials or provider contract details are needed. It never returns
secret values, and it never grants signal or execution authority.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

from orchestrator.config import Settings
from orchestrator.secrets import secret_status, secret_value


CREDENTIAL_BOUND_ADAPTER_SCHEMA_VERSION = 1


@dataclass(frozen=True)
class CredentialBoundAdapterSpec:
    source_key: str
    provider_name: str
    required_env_vars: tuple[str, ...]
    optional_env_vars: tuple[str, ...]
    credential_kind: str
    auth_flow: str
    setup_url: str
    default_endpoint: str
    endpoint_env_var: str = ""
    provider_endpoint_required: bool = False
    evidence_packet_types: tuple[str, ...] = ()
    notes: str = ""


CREDENTIAL_BOUND_ADAPTERS: dict[str, CredentialBoundAdapterSpec] = {
    "reddit": CredentialBoundAdapterSpec(
        source_key="reddit",
        provider_name="Reddit API",
        required_env_vars=("REDDIT_CLIENT_ID", "REDDIT_CLIENT_SECRET"),
        optional_env_vars=("REDDIT_USER_AGENT",),
        credential_kind="oauth_client_credentials",
        auth_flow="client_credentials_token_exchange",
        setup_url="https://www.reddit.com/prefs/apps",
        default_endpoint="https://oauth.reddit.com/r/worldnews/new",
        evidence_packet_types=("narrative_signal", "retail_attention_context", "edge_decay_context"),
        notes="Uses read-only OAuth client credentials; subreddit posts require corroboration before research weight.",
    ),
    "kalshi": CredentialBoundAdapterSpec(
        source_key="kalshi",
        provider_name="Kalshi",
        required_env_vars=("KALSHI_API_KEY", "KALSHI_API_SECRET"),
        optional_env_vars=("KALSHI_API_BASE_URL",),
        credential_kind="key_id_and_rsa_private_key",
        auth_flow="rsa_pss_signed_request_headers",
        setup_url="https://kalshi.com/account/profile",
        default_endpoint="https://trading-api.kalshi.com/trade-api/v2/markets",
        evidence_packet_types=("prediction_market", "probability_context", "market_lifecycle_context"),
        notes="Authenticated market reads only; no Kalshi spend, orders, or execution authority in this adapter.",
    ),
    "stock_act": CredentialBoundAdapterSpec(
        source_key="stock_act",
        provider_name="Capitol Trades / STOCK Act provider",
        required_env_vars=("CAPITOL_TRADES_API_KEY",),
        optional_env_vars=("CAPITOL_TRADES_API_URL",),
        credential_kind="provider_api_key",
        auth_flow="provider_confirmed_bearer_or_header_auth",
        setup_url="mailto:info@2iqresearch.com",
        default_endpoint="https://www.capitoltrades.com/trades",
        endpoint_env_var="CAPITOL_TRADES_API_URL",
        provider_endpoint_required=True,
        evidence_packet_types=("politician_trade_disclosure", "policy_trading_context"),
        notes=(
            "Requires an official provider API endpoint before live reads. The public website URL is not treated "
            "as a stable API contract."
        ),
    ),
}


def _configured_missing(required_env_vars: tuple[str, ...], settings: Settings) -> tuple[tuple[str, ...], tuple[str, ...]]:
    configured: list[str] = []
    missing: list[str] = []
    for key in required_env_vars:
        status = secret_status(key, settings)
        if status.configured:
            configured.append(key)
        else:
            missing.append(key)
    return tuple(configured), tuple(missing)


def _configured_optional(optional_env_vars: tuple[str, ...], settings: Settings) -> tuple[str, ...]:
    return tuple(key for key in optional_env_vars if secret_status(key, settings).configured)


def credential_bound_adapter_state(source_key: str, settings: Settings | None = None) -> dict[str, Any]:
    """Return a public-safe credential-bound readiness state for one source."""

    if source_key not in CREDENTIAL_BOUND_ADAPTERS:
        raise KeyError(f"unknown credential-bound adapter: {source_key}")
    settings = settings or Settings.from_env()
    spec = CREDENTIAL_BOUND_ADAPTERS[source_key]
    configured, missing = _configured_missing(spec.required_env_vars, settings)
    optional_configured = _configured_optional(spec.optional_env_vars, settings)
    endpoint_configured = bool(spec.endpoint_env_var and secret_value(spec.endpoint_env_var, settings))

    if missing:
        activation_state = "missing_credentials"
    elif spec.provider_endpoint_required and not endpoint_configured:
        activation_state = "provider_endpoint_unconfirmed"
    else:
        activation_state = "ready_for_live_readonly"

    endpoint_status = "provider_confirmed_endpoint_configured" if endpoint_configured else "default_or_documented_endpoint"
    if spec.provider_endpoint_required and not endpoint_configured:
        endpoint_status = "provider_endpoint_unconfirmed"

    payload = {
        "schema_version": CREDENTIAL_BOUND_ADAPTER_SCHEMA_VERSION,
        "source_key": spec.source_key,
        "provider_name": spec.provider_name,
        "credential_status": "configured" if not missing else "missing",
        "activation_state": activation_state,
        "activation_ready": activation_state == "ready_for_live_readonly",
        "can_fetch_live_readonly": activation_state == "ready_for_live_readonly",
        "configured_required_env_vars": configured,
        "missing_required_env_vars": missing,
        "configured_optional_env_vars": optional_configured,
        "required_env_var_count": len(spec.required_env_vars),
        "optional_env_var_count": len(spec.optional_env_vars),
        "credential_kind": spec.credential_kind,
        "auth_flow": spec.auth_flow,
        "setup_url": spec.setup_url,
        "default_endpoint": spec.default_endpoint,
        "endpoint_env_var": spec.endpoint_env_var,
        "endpoint_status": endpoint_status,
        "provider_endpoint_required": spec.provider_endpoint_required,
        "evidence_packet_types": spec.evidence_packet_types,
        "evidence_authority": "supplemental_readonly_context",
        "signal_authority": "none_without_strategy_and_risk_gates",
        "order_authority": "none",
        "paper_trading_blocking": False,
        "live_capital_authority": False,
        "notes": spec.notes,
        "boundary": "Credential-bound adapter state only. No secret values, signal approval, orders, broker writes, or live capital.",
    }
    return payload


def credential_bound_adapter_registry(settings: Settings | None = None) -> dict[str, Any]:
    settings = settings or Settings.from_env()
    states = [credential_bound_adapter_state(key, settings) for key in CREDENTIAL_BOUND_ADAPTERS]
    return {
        "schema_version": CREDENTIAL_BOUND_ADAPTER_SCHEMA_VERSION,
        "status": "ok",
        "adapter_count": len(states),
        "activation_ready_count": sum(1 for state in states if state["activation_ready"]),
        "missing_credentials_count": sum(1 for state in states if state["activation_state"] == "missing_credentials"),
        "provider_endpoint_unconfirmed_count": sum(
            1 for state in states if state["activation_state"] == "provider_endpoint_unconfirmed"
        ),
        "states": states,
        "boundary": "Credential-bound adapters are read-only source contracts and cannot create trades.",
    }


def credential_bound_adapter_keys() -> tuple[str, ...]:
    return tuple(CREDENTIAL_BOUND_ADAPTERS)


def public_safe_credential_bound_adapter_specs() -> list[dict[str, Any]]:
    return [asdict(spec) for spec in CREDENTIAL_BOUND_ADAPTERS.values()]
