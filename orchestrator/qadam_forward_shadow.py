"""OR-13 continuous, real-time forward-shadow validation.

The service freezes provider-backed hypothetical decisions before outcomes
exist, observes them over real elapsed time, and never creates orders, proof
credit, or paper-calendar progress.
"""

from __future__ import annotations

from collections import Counter
from datetime import datetime, timedelta, timezone
import json
import math
import re
from typing import Any
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from orchestrator.config import Settings
from orchestrator.qadam_canonical_contracts import AtomicArtifactStore
from orchestrator.qadam_operator_ready_common import (
    authority_flags,
    now_iso,
    read_json,
    read_jsonl,
    runtime_dir,
    sha256_json,
    unique_errors,
    validate_authority,
)
from orchestrator.qadam_wave_b_common import parse_timestamp, safe_float, stable_id
from orchestrator.secrets import secret_value

SCHEMA_VERSION = "qadam_forward_shadow.v2"
PHASE_ID = "OR-13"
POLICY_VERSION = "qadam-forward-shadow-policy.2-provider-backed-real-time"

STATE_ARTIFACT = "qadam_forward_shadow_state.json"
DECISIONS_ARTIFACT = "qadam_forward_shadow_decisions.jsonl"
OUTCOMES_ARTIFACT = "qadam_forward_shadow_outcomes.jsonl"
CALIBRATION_ARTIFACT = "qadam_shadow_calibration.json"
PROMOTION_ARTIFACT = "qadam_shadow_promotion_readiness.json"
HEARTBEAT_ARTIFACT = "qadam_forward_shadow_heartbeat.json"
CHECK_ARTIFACT = "qadam_forward_shadow_checks.json"

HYPOTHESES_ARTIFACT = "qadam_strategy_hypotheses_v3.jsonl"
AKBER_INPUTS_ARTIFACT = "qadam_akber_filter_v3_inputs.jsonl"
AKBER_RESULTS_ARTIFACT = "qadam_akber_filter_v3_results.jsonl"
AKBER_THRESHOLD_PROPOSALS_ARTIFACT = "qadam_akber_filter_v3_threshold_proposals.jsonl"
MARKET_CONTEXT_ARTIFACT = "market_context_packet.json"
SUPERVISOR_STATUS_ARTIFACT = "qadam_research_supervisor_status.json"
SUPERVISOR_HEARTBEAT_ARTIFACT = "qadam_research_supervisor_heartbeat.json"
OPERATOR_STATUS_ARTIFACT = "qadam_operator_service_status.json"

ALPACA_DATA_BASE_URL = "https://data.alpaca.markets/v2"
ALPACA_PRICE_PROVIDER = "alpaca_market_data_v2"
CANONICAL_PRICE_PROVIDERS = {
    ALPACA_PRICE_PROVIDER,
    "databento_glbx_mdp3",
    "kalshi_official_api",
    "polymarket_official_clob",
}

MIN_INDEPENDENT_COMPLETED_SIGNALS = 20
MIN_REAL_ELAPSED_DAYS = 10.0
MIN_ESTIMATED_POWER = 0.80
MIN_INDEPENDENT_EDGES = 2
ENTRY_OBSERVATION_MAX_AGE_SECONDS = 15 * 60
OUTCOME_GRACE_SECONDS = 3 * 24 * 60 * 60
SERVICE_HEARTBEAT_MAX_AGE_SECONDS = 5 * 60
DEFAULT_COST_BPS = 5.0
TERMINAL_DECISION_STATES = {
    "completed",
    "expired_unscored",
    "superseded_logical_duplicate",
}


def _normal_cdf(value: float) -> float:
    return 0.5 * (1.0 + math.erf(value / math.sqrt(2.0)))


def _safe_int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _horizon_seconds(value: Any) -> int:
    normalized = str(value or "").strip().lower().replace("_forward", "")
    match = re.fullmatch(r"(\d+)\s*(m|min|h|hr|d|day|w|week)", normalized)
    if not match:
        raise ValueError("shadow_horizon_unsupported")
    amount = int(match.group(1))
    if amount <= 0:
        raise ValueError("shadow_horizon_non_positive")
    units = match.group(2)
    multiplier = {
        "m": 60,
        "min": 60,
        "h": 3600,
        "hr": 3600,
        "d": 86_400,
        "day": 86_400,
        "w": 604_800,
        "week": 604_800,
    }[units]
    return amount * multiplier


def _expected_return_range(hypothesis: dict[str, Any]) -> dict[str, float | None]:
    expected = hypothesis.get("expected_edge_range")
    expected = expected if isinstance(expected, dict) else {}
    distribution = expected.get("confidence_distribution")
    distribution = distribution if isinstance(distribution, dict) else {}

    def optional_float(value: Any) -> float | None:
        if value is None:
            return None
        try:
            return float(value)
        except (TypeError, ValueError):
            return None

    point = optional_float(expected.get("net_expectancy"))
    lower = optional_float(distribution.get("lower"))
    upper = optional_float(distribution.get("upper"))
    if lower is not None and upper is not None and lower > upper:
        lower, upper = upper, lower
    return {"point": point, "lower": lower, "upper": upper}


def _shadow_eligible(
    hypothesis: dict[str, Any], akber_result: dict[str, Any] | None
) -> tuple[bool, str]:
    if hypothesis.get("hypothesis_state") == "shadow_only":
        return True, "exploratory_edge_shadow_only"
    if hypothesis.get("hypothesis_state") == "ready_for_akber_review" and isinstance(
        akber_result, dict
    ):
        decision = str(akber_result.get("decision") or "")
        if decision == "pass" and akber_result.get("router_eligible") is True:
            return True, "akber_passed_research_hypothesis"
        if decision == "hold_missing_context":
            return True, "akber_hold_counterfactual_observation"
        if decision == "veto":
            return True, "akber_veto_counterfactual_observation"
    return False, "not_shadow_eligible"


def _promotion_evidence_allowed(eligibility_basis: str) -> bool:
    """Counterfactual holds and vetoes teach Akber without promoting a setup."""

    return eligibility_basis in {
        "exploratory_edge_shadow_only",
        "akber_passed_research_hypothesis",
    }


def _signal_observation_date(value: Any) -> str:
    parsed = parse_timestamp(value)
    if parsed is None:
        raise ValueError("shadow_signal_observation_date_invalid")
    return parsed.astimezone(timezone.utc).date().isoformat()


def _hypothesis_signal_window(
    hypothesis: dict[str, Any], akber_input: dict[str, Any] | None = None
) -> str:
    pattern_lineage = hypothesis.get("pattern_lineage")
    pattern_lineage = pattern_lineage if isinstance(pattern_lineage, dict) else {}
    candidate = hypothesis.get("candidate_identity_material")
    candidate = candidate if isinstance(candidate, dict) else {}
    value = (
        hypothesis.get("signal_observation_date")
        or pattern_lineage.get("operating_date")
        or candidate.get("signal_observation_date")
    )
    if isinstance(akber_input, dict):
        evidence = akber_input.get("evidence")
        evidence = evidence if isinstance(evidence, dict) else {}
        trigger = evidence.get("fresh_catalyst")
        trigger = trigger if isinstance(trigger, dict) else {}
        trigger_state = str(
            trigger.get("state")
            or akber_input.get("current_trigger_state")
            or ""
        ).lower()
        if (
            trigger.get("available") is True
            and trigger.get("observed_at")
            and trigger_state
            in {"active", "confirmed", "current_event_confirmed"}
        ):
            source_refs = sorted(
                str(value) for value in trigger.get("source_refs", []) if value
            )
            causal_refs = [
                value
                for value in source_refs
                if not value.startswith("current-market-direction:")
            ]
            trigger_value = trigger.get("value")
            trigger_value = trigger_value if isinstance(trigger_value, dict) else {}
            trigger_identity = stable_id(
                "forward-shadow-current-trigger-v3",
                causal_refs or source_refs,
                trigger_value.get("direction"),
                _signal_observation_date(trigger.get("observed_at")),
                sorted(
                    str(value)
                    for value in akber_input.get("current_trigger_sources", [])
                    if value
                ),
            )
            return f"current-trigger:{trigger_identity}"
    return _signal_observation_date(value) if value else "unspecified_signal_window"


def _hypothesis_signal_observation_date(
    hypothesis: dict[str, Any], akber_input: dict[str, Any] | None = None
) -> str:
    """Keep the human-facing signal date separate from event identity."""

    if isinstance(akber_input, dict):
        evidence = akber_input.get("evidence")
        evidence = evidence if isinstance(evidence, dict) else {}
        trigger = evidence.get("fresh_catalyst")
        trigger = trigger if isinstance(trigger, dict) else {}
        if trigger.get("available") is True and trigger.get("observed_at"):
            return _signal_observation_date(trigger["observed_at"])
    pattern_lineage = hypothesis.get("pattern_lineage")
    pattern_lineage = pattern_lineage if isinstance(pattern_lineage, dict) else {}
    candidate = hypothesis.get("candidate_identity_material")
    candidate = candidate if isinstance(candidate, dict) else {}
    value = (
        hypothesis.get("signal_observation_date")
        or pattern_lineage.get("operating_date")
        or candidate.get("signal_observation_date")
    )
    return _signal_observation_date(value) if value else "unspecified_signal_window"


def _economic_signal_identity(
    *,
    edge_id: Any,
    instrument: Any,
    direction: Any,
    horizon: Any,
    signal_window: Any,
) -> str:
    """Identify one testable market view independently of refreshed metadata."""

    return stable_id(
        "forward-shadow-economic-signal-v1",
        str(edge_id or "experimental_unvalidated_relationship"),
        str(instrument or ""),
        str(direction or ""),
        str(horizon or ""),
        str(signal_window or "unspecified_signal_window"),
        POLICY_VERSION,
    )


def economic_signal_identity_for_hypothesis(
    hypothesis: dict[str, Any],
    akber_input: dict[str, Any] | None = None,
) -> str:
    """Return the immutable signal identity shared by shadow and portfolio risk."""

    direction_horizon = hypothesis.get("direction_horizon")
    direction_horizon = (
        direction_horizon if isinstance(direction_horizon, dict) else {}
    )
    return _economic_signal_identity(
        edge_id=hypothesis.get("edge_lineage", {}).get("edge_id"),
        instrument=hypothesis.get("instrument_proxy_mapping", {}).get(
            "execution_proxy"
        ),
        direction=direction_horizon.get("direction"),
        horizon=direction_horizon.get("horizon"),
        signal_window=_hypothesis_signal_window(hypothesis, akber_input),
    )


def _decision_economic_signal_identity(record: dict[str, Any]) -> str:
    existing = str(record.get("economic_signal_identity_id") or "")
    if existing:
        return existing
    if "signal_observation_date" in record:
        signal_window = str(
            record.get("signal_observation_date") or "unspecified_signal_window"
        )
    else:
        # Legacy decisions predate an explicit signal window. Their decision date
        # is the only immutable point-in-time identity available for reconciliation.
        signal_window = _signal_observation_date(record.get("decision_at"))
    return _economic_signal_identity(
        edge_id=record.get("edge_id"),
        instrument=record.get("instrument"),
        direction=record.get("direction"),
        horizon=record.get("horizon"),
        signal_window=signal_window,
    )


def _reconcile_logical_duplicate_decisions(
    decisions: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], int]:
    """Retain duplicate evidence while allowing only the first signal to mature."""

    reconciled: list[dict[str, Any]] = []
    canonical_by_signal: dict[str, str] = {}
    duplicate_count = 0
    for source in sorted(
        decisions,
        key=lambda record: (
            str(record.get("decision_at") or ""),
            str(record.get("decision_id") or ""),
        ),
    ):
        record = dict(source)
        signal_id = _decision_economic_signal_identity(record)
        record["economic_signal_identity_id"] = signal_id
        canonical_id = canonical_by_signal.get(signal_id)
        if canonical_id is None:
            canonical_by_signal[signal_id] = str(record.get("decision_id") or "")
            record["logical_duplicate_detected"] = False
            record["logical_duplicate_of_decision_id"] = None
        else:
            duplicate_count += 1
            record["logical_duplicate_detected"] = True
            record["logical_duplicate_of_decision_id"] = canonical_id
            record["lifecycle_state"] = "superseded_logical_duplicate"
            record["typed_expiry_reason"] = "superseded_duplicate_economic_signal"
            record["promotion_evidence_allowed"] = False
            record["counterfactual_observation_only"] = True
        reconciled.append(record)
    return reconciled, duplicate_count


def _observation_errors(record: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if not str(record.get("instrument") or ""):
        errors.append("instrument_missing")
    if safe_float(record.get("price"), 0.0) <= 0:
        errors.append("price_missing_or_non_positive")
    if parse_timestamp(record.get("observed_at")) is None:
        errors.append("observed_at_invalid")
    if parse_timestamp(record.get("available_at")) is None:
        errors.append("available_at_invalid")
    if record.get("provider_backed") is not True:
        errors.append("not_provider_backed")
    if str(record.get("provider") or "") not in CANONICAL_PRICE_PROVIDERS:
        errors.append("provider_not_canonical_for_shadow")
    if record.get("sample") is not False or record.get("fixture") is not False:
        errors.append("sample_or_fixture_forbidden")
    if record.get("read_only_market_data") is not True:
        errors.append("read_only_boundary_missing")
    return errors


def _latest_entry_observation(
    records: list[dict[str, Any]], instrument: str, *, decision_at: datetime
) -> dict[str, Any] | None:
    candidates: list[dict[str, Any]] = []
    for record in records:
        if str(record.get("instrument") or "") != instrument or _observation_errors(record):
            continue
        observed = parse_timestamp(record.get("observed_at"))
        available = parse_timestamp(record.get("available_at"))
        if observed is None or available is None:
            continue
        if observed > decision_at or available > decision_at:
            continue
        age = (decision_at - observed).total_seconds()
        if 0 <= age <= ENTRY_OBSERVATION_MAX_AGE_SECONDS:
            candidates.append(record)
    return max(
        candidates,
        key=lambda row: (
            parse_timestamp(row.get("observed_at")) or datetime.min.replace(tzinfo=timezone.utc)
        ),
        default=None,
    )


def _first_outcome_observation(
    records: list[dict[str, Any]], instrument: str, *, due_at: datetime, as_of: datetime
) -> dict[str, Any] | None:
    candidates: list[dict[str, Any]] = []
    for record in records:
        if str(record.get("instrument") or "") != instrument or _observation_errors(record):
            continue
        observed = parse_timestamp(record.get("observed_at"))
        available = parse_timestamp(record.get("available_at"))
        if observed is None or available is None:
            continue
        if observed >= due_at and available <= as_of and observed <= as_of:
            candidates.append(record)
    return min(
        candidates,
        key=lambda row: (
            parse_timestamp(row.get("observed_at")) or datetime.max.replace(tzinfo=timezone.utc)
        ),
        default=None,
    )


def extract_runtime_price_observations(
    market_context: dict[str, Any], *, generated_at: str
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Read only canonical provider-backed records from the market context."""

    accepted: list[dict[str, Any]] = []
    rejected: list[dict[str, Any]] = []
    packets = market_context.get("recent_packets")
    packets = packets if isinstance(packets, list) else []
    for packet in packets:
        if not isinstance(packet, dict):
            continue
        context = packet.get("price_volume_context")
        context = context if isinstance(context, dict) else {}
        provider = str(context.get("provider") or "")
        observed_at = str(packet.get("generated_at") or generated_at)
        canonical = context.get("canonical_source") is True
        records = context.get("records")
        records = records if isinstance(records, list) else []
        for row in records:
            if not isinstance(row, dict):
                continue
            observation = {
                "observation_id": stable_id(
                    "shadow-price-observation",
                    provider,
                    row.get("symbol"),
                    observed_at,
                    row.get("last_close"),
                ),
                "instrument": row.get("symbol"),
                "price": row.get("last_close"),
                "observed_at": observed_at,
                "available_at": observed_at,
                "provider": provider,
                "provider_backed": canonical,
                "origin_class": "runtime_market_context",
                "market_state": row.get("market_state"),
                "volume": row.get("volume"),
                "sample": "sample" in str(row.get("market_state") or "").lower(),
                "fixture": False,
                "read_only_market_data": True,
                "broker_endpoint_used": False,
            }
            errors = _observation_errors(observation)
            if errors:
                rejected.append(
                    {
                        "instrument": observation.get("instrument"),
                        "provider": provider or "missing",
                        "reasons": errors,
                    }
                )
            else:
                accepted.append(observation)
    return accepted, rejected


def fetch_alpaca_latest_bar_observations(
    instruments: list[str],
    settings: Settings,
    *,
    generated_at: str,
    timeout_seconds: int = 15,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Fetch read-only latest bars; never use an Alpaca broker endpoint."""

    symbols = sorted(
        {symbol for symbol in instruments if re.fullmatch(r"[A-Z][A-Z0-9.\-]{0,14}", symbol)}
    )
    unsupported = sorted(set(instruments) - set(symbols))
    status: dict[str, Any] = {
        "provider": ALPACA_PRICE_PROVIDER,
        "endpoint_class": "read_only_market_data",
        "broker_endpoint_used": False,
        "requested_symbol_count": len(symbols),
        "unsupported_instruments": unsupported,
        "returned_observation_count": 0,
        "status": (
            "unsupported_realtime_instruments"
            if unsupported and not symbols
            else "not_needed_no_supported_symbols"
            if not symbols
            else "pending"
        ),
    }
    if not symbols:
        return [], status
    api_key = secret_value("ALPACA_API_KEY", settings)
    api_secret = secret_value("ALPACA_API_SECRET", settings)
    if not api_key or not api_secret:
        status["status"] = "missing_credentials"
        return [], status
    query = urlencode({"symbols": ",".join(symbols), "feed": "iex"})
    endpoint = f"{ALPACA_DATA_BASE_URL}/stocks/bars/latest?{query}"
    request = Request(
        endpoint,
        headers={
            "APCA-API-KEY-ID": api_key,
            "APCA-API-SECRET-KEY": api_secret,
            "Accept": "application/json",
            "User-Agent": "qadam-forward-shadow/2",
        },
        method="GET",
    )
    try:
        with urlopen(request, timeout=timeout_seconds) as response:  # noqa: S310
            payload = json.loads(response.read().decode("utf-8"))
    except Exception as exc:  # Network failures become typed evidence gaps.
        status.update(
            {
                "status": "provider_error",
                "failure_category": type(exc).__name__,
                "error_detail_redacted": True,
            }
        )
        return [], status
    bars = payload.get("bars") if isinstance(payload, dict) else None
    bars = bars if isinstance(bars, dict) else {}
    observations: list[dict[str, Any]] = []
    for symbol in symbols:
        bar = bars.get(symbol)
        if not isinstance(bar, dict):
            continue
        observed_at = str(bar.get("t") or "")
        observation = {
            "observation_id": stable_id(
                "shadow-price-observation",
                ALPACA_PRICE_PROVIDER,
                symbol,
                observed_at,
                bar.get("c"),
            ),
            "instrument": symbol,
            "price": bar.get("c"),
            "observed_at": observed_at,
            "available_at": generated_at,
            "provider": ALPACA_PRICE_PROVIDER,
            "provider_backed": True,
            "origin_class": "live_read_only_provider_call",
            "market_state": "latest_iex_bar",
            "volume": bar.get("v"),
            "sample": False,
            "fixture": False,
            "read_only_market_data": True,
            "broker_endpoint_used": False,
        }
        if not _observation_errors(observation):
            observations.append(observation)
    status.update(
        {
            "status": "ok" if observations else "empty_provider_response",
            "returned_observation_count": len(observations),
        }
    )
    return observations, status


def _source_runtime_snapshot(
    akber_input: dict[str, Any] | None, *, decision_at: str
) -> dict[str, Any]:
    evidence = akber_input.get("evidence") if isinstance(akber_input, dict) else {}
    evidence = evidence if isinstance(evidence, dict) else {}
    missing = [key for key, row in evidence.items() if row.get("available") is not True]
    stale = [key for key, row in evidence.items() if row.get("freshness_state") == "stale"]
    unsafe = [
        key
        for key, row in evidence.items()
        if row.get("fixture_backed") is True or row.get("provenance_complete") is not True
    ]
    observed_times = [
        parse_timestamp(row.get("observed_at"))
        for row in evidence.values()
        if isinstance(row, dict)
    ]
    observed_times = [value for value in observed_times if value is not None]
    decision = parse_timestamp(decision_at)
    maximum_latency = None
    if decision is not None and observed_times:
        maximum_latency = max(
            max((decision - value).total_seconds(), 0.0) for value in observed_times
        )
    if not evidence:
        outage_state = "unknown_no_akber_context_for_exploratory_shadow"
    elif missing or unsafe:
        outage_state = "degraded"
    else:
        outage_state = "clear"
    return {
        "evidence_field_count": len(evidence),
        "missing_field_count": len(missing),
        "missing_fields": sorted(missing),
        "stale_field_count": len(stale),
        "stale_fields": sorted(stale),
        "unsafe_origin_field_count": len(unsafe),
        "unsafe_origin_fields": sorted(unsafe),
        "outage_state": outage_state,
        "latency_state": "unknown" if maximum_latency is None else "measured",
        "maximum_evidence_latency_seconds": maximum_latency,
        "unknown_state_is_not_assumed_healthy": True,
    }


def _alternate_policy_snapshot(
    proposals: list[dict[str, Any]], akber_result: dict[str, Any] | None
) -> list[dict[str, Any]]:
    return [
        {
            "proposal_id": proposal.get("proposal_id"),
            "threshold_name": proposal.get("threshold_name"),
            "current_value": proposal.get("current_value"),
            "proposed_value": proposal.get("proposed_value"),
            "proposal_state": proposal.get("proposal_state"),
            "hypothetical_decision": "not_evaluated_proposal_only",
            "baseline_akber_decision": (
                akber_result.get("decision")
                if isinstance(akber_result, dict)
                else "not_required_exploratory_shadow"
            ),
            "threshold_change_applied": False,
        }
        for proposal in proposals
        if isinstance(proposal, dict) and proposal.get("proposal_id")
    ]


def freeze_shadow_decision(
    hypothesis: dict[str, Any],
    akber_result: dict[str, Any] | None,
    *,
    decision_at: str,
    entry_observation: dict[str, Any] | None = None,
    akber_input: dict[str, Any] | None = None,
    threshold_proposals: list[dict[str, Any]] | None = None,
    require_entry_observation: bool = False,
) -> dict[str, Any]:
    """Freeze one hypothetical no-order decision before any outcome exists."""

    eligible, basis = _shadow_eligible(hypothesis, akber_result)
    if not eligible:
        raise ValueError("hypothesis_not_shadow_eligible")
    decided = parse_timestamp(decision_at)
    if decided is None:
        raise ValueError("decision_at_invalid")
    hypothesis_id = str(hypothesis.get("hypothesis_id") or "")
    if not hypothesis_id:
        raise ValueError("hypothesis_id_missing")
    direction_horizon = hypothesis.get("direction_horizon")
    if not isinstance(direction_horizon, dict):
        raise ValueError("direction_horizon_missing")
    direction = str(direction_horizon.get("direction") or "")
    horizon = str(direction_horizon.get("horizon") or "")
    if not direction or not horizon:
        raise ValueError("direction_or_horizon_missing")
    horizon_seconds = _horizon_seconds(horizon)
    instrument = str(hypothesis.get("instrument_proxy_mapping", {}).get("execution_proxy") or "")
    if not instrument:
        raise ValueError("execution_proxy_missing")
    if require_entry_observation and (
        not isinstance(entry_observation, dict) or _observation_errors(entry_observation)
    ):
        raise ValueError("provider_backed_entry_observation_required")
    if isinstance(entry_observation, dict):
        if str(entry_observation.get("instrument") or "") != instrument:
            raise ValueError("entry_observation_instrument_mismatch")
        observed = parse_timestamp(entry_observation.get("observed_at"))
        available = parse_timestamp(entry_observation.get("available_at"))
        if observed is None or available is None or observed > decided or available > decided:
            raise ValueError("entry_observation_not_available_at_decision")
    expected_range = _expected_return_range(hypothesis)
    due_at = decided + timedelta(seconds=horizon_seconds)
    grace_at = due_at + timedelta(seconds=OUTCOME_GRACE_SECONDS)
    candidate_identity = hypothesis.get("candidate_identity_material", {}).get(
        "candidate_identity_id"
    )
    edge_id = hypothesis.get("edge_lineage", {}).get("edge_id")
    signal_window = _hypothesis_signal_window(hypothesis, akber_input)
    signal_observation_date = _hypothesis_signal_observation_date(
        hypothesis, akber_input
    )
    economic_signal_id = economic_signal_identity_for_hypothesis(
        hypothesis, akber_input
    )
    decision_id = stable_id(
        "forward-shadow-decision",
        economic_signal_id,
        POLICY_VERSION,
    )
    source_snapshot = _source_runtime_snapshot(akber_input, decision_at=decision_at)
    alternate_policies = _alternate_policy_snapshot(threshold_proposals or [], akber_result)
    frozen_payload = {
        "hypothesis_id": hypothesis_id,
        "edge_id": edge_id,
        "research_goal_id": hypothesis.get("research_goal_lineage", {}).get("research_goal_id"),
        "candidate_identity_id": candidate_identity,
        "instrument": instrument,
        "direction": direction,
        "horizon": horizon,
        "horizon_seconds": horizon_seconds,
        "predicted_return_range": expected_range,
        "akber_result_id": (
            akber_result.get("akber_result_id") if isinstance(akber_result, dict) else None
        ),
        "akber_input_id": (
            akber_input.get("akber_input_id") if isinstance(akber_input, dict) else None
        ),
        "decision_generation_id": (
            akber_input.get("decision_generation_id")
            if isinstance(akber_input, dict)
            else None
        ),
        "akber_decision": (
            akber_result.get("decision")
            if isinstance(akber_result, dict)
            else "not_required_exploratory_shadow"
        ),
        "decision_at": decision_at,
        "signal_observation_date": signal_observation_date,
        "signal_window_identity": signal_window,
        "economic_signal_identity_id": economic_signal_id,
        "outcome_due_at": due_at.isoformat(),
        "entry_observation": entry_observation,
        "policy_version": POLICY_VERSION,
        "alternate_threshold_policy_snapshot": alternate_policies,
        "source_runtime_snapshot": source_snapshot,
    }
    return {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "qadam_forward_shadow_decision",
        "phase_id": PHASE_ID,
        "generated_at": decision_at,
        "decision_id": decision_id,
        "signal_identity_id": economic_signal_id,
        **frozen_payload,
        "frozen_decision_payload": frozen_payload,
        "frozen_decision_hash": sha256_json(frozen_payload),
        "frozen_policy_hash": sha256_json(
            {
                "policy_version": POLICY_VERSION,
                "minimum_signals": MIN_INDEPENDENT_COMPLETED_SIGNALS,
                "minimum_elapsed_days": MIN_REAL_ELAPSED_DAYS,
                "minimum_power": MIN_ESTIMATED_POWER,
            }
        ),
        "eligibility_basis": basis,
        "promotion_evidence_allowed": _promotion_evidence_allowed(basis),
        "counterfactual_observation_only": not _promotion_evidence_allowed(basis),
        "available_evidence_cutoff": decision_at,
        "decision_frozen_before_outcome": True,
        "entry_observation_required": require_entry_observation,
        "entry_observation_provider_backed": bool(entry_observation),
        "lifecycle_state": "open_awaiting_real_outcome",
        "expiry_at": grace_at.isoformat(),
        "outcome_grace_expires_at": grace_at.isoformat(),
        "typed_expiry_reason": None,
        "counterfactuals_required": [
            "trade_now_hypothetical",
            "wait",
            "hold",
            "veto_no_order",
            "alternate_threshold",
        ],
        "outcome_observed": False,
        "simulated_elapsed_time": False,
        "paper_order_created": False,
        "proof_eligible": False,
        "authority": authority_flags(),
    }


def _forecast_evaluation(decision: dict[str, Any], net_return: float) -> dict[str, Any]:
    predicted = decision.get("predicted_return_range")
    predicted = predicted if isinstance(predicted, dict) else {}
    point = predicted.get("point")
    lower = predicted.get("lower")
    upper = predicted.get("upper")
    absolute_error = abs(net_return - safe_float(point)) if point is not None else None
    range_hit = (
        safe_float(lower) <= net_return <= safe_float(upper)
        if lower is not None and upper is not None
        else None
    )
    return {
        "predicted_point_return": point,
        "predicted_lower_return": lower,
        "predicted_upper_return": upper,
        "forecast_absolute_error": absolute_error,
        "forecast_range_hit": range_hit,
        "historical_confidence_drift": (
            "inside_expected_range"
            if range_hit is True
            else "outside_expected_range"
            if range_hit is False
            else "not_measurable_missing_range"
        ),
    }


def _alternate_threshold_outcomes(
    decision: dict[str, Any], net_return: float
) -> list[dict[str, Any]]:
    rows = decision.get("alternate_threshold_policy_snapshot")
    rows = rows if isinstance(rows, list) else []
    outcomes: list[dict[str, Any]] = []
    for row in rows:
        hypothetical = row.get("hypothetical_decision")
        if hypothetical == "pass":
            counterfactual_return: float | None = net_return
        elif hypothetical in {"hold_missing_context", "veto"}:
            counterfactual_return = 0.0
        else:
            counterfactual_return = None
        outcomes.append(
            {
                "proposal_id": row.get("proposal_id"),
                "hypothetical_decision": hypothetical,
                "counterfactual_net_return": counterfactual_return,
                "measurement_state": (
                    "measured_from_frozen_alternate_decision"
                    if counterfactual_return is not None
                    else "not_measurable_proposal_was_not_applied_or_replayed"
                ),
                "threshold_change_applied": False,
            }
        )
    return outcomes


def complete_shadow_outcome(
    decision: dict[str, Any],
    *,
    outcome_available_at: str,
    gross_return: float,
    cost_bps: float,
    source_outage_effect: str = "none_observed",
    latency_effect: str = "none_observed",
    outcome_observation: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Score one frozen decision only after its real horizon has elapsed."""

    decision_at = parse_timestamp(decision.get("decision_at"))
    outcome_at = parse_timestamp(outcome_available_at)
    due_at = parse_timestamp(decision.get("outcome_due_at"))
    if decision_at is None or outcome_at is None:
        raise ValueError("shadow_timestamp_invalid")
    if outcome_at <= decision_at:
        raise ValueError("shadow_outcome_not_after_decision")
    if due_at is not None and outcome_at < due_at:
        raise ValueError("shadow_outcome_before_horizon")
    raw_market_return = float(gross_return)
    direction = str(decision.get("direction") or "").lower()
    if any(token in direction for token in ("down", "short", "downside")):
        strategy_gross_return = -raw_market_return
    else:
        strategy_gross_return = raw_market_return
    costs = max(float(cost_bps), 0.0) / 10_000.0
    net = strategy_gross_return - costs
    elapsed_seconds = (outcome_at - decision_at).total_seconds()
    forecast = _forecast_evaluation(decision, net)
    alternate_outcomes = _alternate_threshold_outcomes(decision, net)
    counterfactuals = {
        "trade_now_hypothetical_net_return": round(net, 10),
        "wait_no_position_return": 0.0,
        "hold_no_position_return": 0.0,
        "veto_no_order_return": 0.0,
        "alternate_threshold_outcomes": alternate_outcomes,
    }
    akber_decision = decision.get("akber_decision")
    return {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "qadam_forward_shadow_outcome",
        "phase_id": PHASE_ID,
        "generated_at": outcome_available_at,
        "outcome_id": stable_id(
            "forward-shadow-outcome", decision.get("decision_id"), outcome_available_at
        ),
        "decision_id": decision.get("decision_id"),
        "signal_identity_id": decision.get("signal_identity_id"),
        "economic_signal_identity_id": _decision_economic_signal_identity(decision),
        "hypothesis_id": decision.get("hypothesis_id"),
        "edge_id": decision.get("edge_id"),
        "decision_at": decision.get("decision_at"),
        "outcome_due_at": decision.get("outcome_due_at"),
        "outcome_available_at": outcome_available_at,
        "real_elapsed_seconds": elapsed_seconds,
        "underlying_market_return": round(raw_market_return, 10),
        "gross_return": round(strategy_gross_return, 10),
        "cost_bps": float(cost_bps),
        "net_return": round(net, 10),
        "direction_correct": strategy_gross_return > 0,
        "akber_decision": akber_decision,
        "counterfactuals": counterfactuals,
        "missed_opportunity_return": (
            max(net, 0.0) if akber_decision in {"hold_missing_context", "veto"} else 0.0
        ),
        "source_outage_effect": source_outage_effect,
        "latency_effect": latency_effect,
        "entry_observation": decision.get("entry_observation"),
        "outcome_observation": outcome_observation,
        **forecast,
        "simulated_elapsed_time": False,
        "paper_order_created": False,
        "proof_eligible": False,
        "authority": authority_flags(),
    }


def complete_shadow_outcome_from_observation(
    decision: dict[str, Any],
    observation: dict[str, Any],
    *,
    cost_bps: float = DEFAULT_COST_BPS,
) -> dict[str, Any]:
    if _observation_errors(observation):
        raise ValueError("shadow_outcome_observation_invalid")
    entry = decision.get("entry_observation")
    if not isinstance(entry, dict) or _observation_errors(entry):
        raise ValueError("shadow_entry_observation_invalid")
    if observation.get("instrument") != decision.get("instrument"):
        raise ValueError("shadow_outcome_instrument_mismatch")
    entry_price = safe_float(entry.get("price"))
    outcome_price = safe_float(observation.get("price"))
    if entry_price <= 0 or outcome_price <= 0:
        raise ValueError("shadow_price_non_positive")
    market_return = (outcome_price / entry_price) - 1.0
    source_snapshot = decision.get("source_runtime_snapshot")
    source_snapshot = source_snapshot if isinstance(source_snapshot, dict) else {}
    return complete_shadow_outcome(
        decision,
        outcome_available_at=str(observation.get("available_at")),
        gross_return=market_return,
        cost_bps=cost_bps,
        source_outage_effect=str(source_snapshot.get("outage_state") or "unknown"),
        latency_effect=str(source_snapshot.get("latency_state") or "unknown"),
        outcome_observation=observation,
    )


def _refresh_lifecycle(
    decision: dict[str, Any], outcome_ids: set[str], *, now: datetime
) -> dict[str, Any]:
    refreshed = dict(decision)
    if refreshed.get("lifecycle_state") == "superseded_logical_duplicate":
        return refreshed
    decision_id = str(refreshed.get("decision_id") or "")
    if decision_id in outcome_ids:
        refreshed["lifecycle_state"] = "completed"
        refreshed["outcome_observed"] = True
        refreshed["typed_expiry_reason"] = None
        return refreshed
    due_at = parse_timestamp(refreshed.get("outcome_due_at"))
    grace_at = parse_timestamp(refreshed.get("outcome_grace_expires_at"))
    if grace_at is not None and now >= grace_at:
        refreshed["lifecycle_state"] = "expired_unscored"
        refreshed["typed_expiry_reason"] = (
            "provider_backed_outcome_unavailable_after_real_horizon_and_grace"
        )
    elif due_at is not None and now >= due_at:
        refreshed["lifecycle_state"] = "open_outcome_due_waiting_provider"
    else:
        refreshed["lifecycle_state"] = "open_awaiting_real_outcome"
    return refreshed


def _calibration(
    decisions: list[dict[str, Any]], outcomes: list[dict[str, Any]], generated_at: str
) -> dict[str, Any]:
    decision_by_id = {
        str(record.get("decision_id")): record
        for record in decisions
        if record.get("decision_id")
    }
    completed_by_signal: dict[str, dict[str, Any]] = {}
    for record in sorted(
        outcomes,
        key=lambda row: (
            str(row.get("outcome_available_at") or ""),
            str(row.get("outcome_id") or ""),
        ),
    ):
        if record.get("net_return") is None:
            continue
        decision = decision_by_id.get(str(record.get("decision_id") or ""), {})
        signal_id = (
            _decision_economic_signal_identity(decision)
            if decision
            else str(record.get("economic_signal_identity_id") or record.get("signal_identity_id"))
        )
        completed_by_signal.setdefault(signal_id, record)
    completed = list(completed_by_signal.values())
    directional = [
        record for record in completed if isinstance(record.get("direction_correct"), bool)
    ]
    range_rows = [
        record for record in completed if isinstance(record.get("forecast_range_hit"), bool)
    ]
    errors = [
        safe_float(record.get("forecast_absolute_error"))
        for record in completed
        if record.get("forecast_absolute_error") is not None
    ]
    return {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "qadam_shadow_calibration",
        "phase_id": PHASE_ID,
        "generated_at": generated_at,
        "status": "not_measurable" if not completed else "measured_research_only",
        "decision_count": len(decisions),
        "completed_outcome_count": len(completed),
        "directional_outcome_count": len(directional),
        "directional_hit_rate": (
            round(
                sum(record.get("direction_correct") is True for record in directional)
                / len(directional),
                8,
            )
            if directional
            else None
        ),
        "mean_net_return": (
            round(
                sum(safe_float(record.get("net_return")) for record in completed) / len(completed),
                10,
            )
            if completed
            else None
        ),
        "forecast_range_observation_count": len(range_rows),
        "forecast_range_coverage": (
            round(
                sum(record.get("forecast_range_hit") is True for record in range_rows)
                / len(range_rows),
                8,
            )
            if range_rows
            else None
        ),
        "mean_absolute_forecast_error": (round(sum(errors) / len(errors), 10) if errors else None),
        "source_outage_affected_outcome_count": sum(
            record.get("source_outage_effect") not in {"clear", "none_observed"}
            for record in completed
        ),
        "latency_affected_outcome_count": sum(
            record.get("latency_effect") not in {"measured", "none_observed"}
            for record in completed
        ),
        "alternate_threshold_outcome_count": sum(
            len(record.get("counterfactuals", {}).get("alternate_threshold_outcomes", []))
            for record in completed
        ),
        "missed_opportunity_return_sum": round(
            sum(safe_float(record.get("missed_opportunity_return")) for record in completed),
            10,
        ),
        "calibration_claim_allowed": len(completed) >= MIN_INDEPENDENT_COMPLETED_SIGNALS,
        "metrics_are_forward_shadow_research_not_portfolio_returns": True,
        "proof_eligible": False,
        "authority": authority_flags(),
    }


def _promotion_readiness(
    decisions: list[dict[str, Any]],
    outcomes: list[dict[str, Any]],
    generated_at: str,
) -> dict[str, Any]:
    decision_by_id = {
        str(record.get("decision_id")): record
        for record in decisions
        if record.get("decision_id")
    }
    unique_outcomes = {
        _decision_economic_signal_identity(
            decision_by_id[str(record.get("decision_id"))]
        ): record
        for record in outcomes
        if record.get("decision_id")
        and decision_by_id.get(str(record.get("decision_id")), {}).get(
            "promotion_evidence_allowed"
        )
        is True
    }
    completed = list(unique_outcomes.values())
    counterfactual_completed = list({
        _decision_economic_signal_identity(
            decision_by_id[str(record.get("decision_id"))]
        ): record
        for record in outcomes
        if record.get("decision_id")
        and decision_by_id.get(str(record.get("decision_id")), {}).get(
            "counterfactual_observation_only"
        )
        is True
    }.values())
    independent_edges = {
        str(record.get("edge_id")) for record in completed if record.get("edge_id")
    }
    completed_count = len(completed)
    timestamps = [
        value
        for value in (
            [parse_timestamp(record.get("decision_at")) for record in decisions]
            + [parse_timestamp(record.get("outcome_available_at")) for record in completed]
        )
        if value is not None
    ]
    elapsed_days = (
        (max(timestamps) - min(timestamps)).total_seconds() / 86_400.0
        if len(timestamps) >= 2
        else 0.0
    )
    returns = [safe_float(record.get("net_return")) for record in completed]
    estimated_power = None
    if len(returns) >= 5:
        mean_return = sum(returns) / len(returns)
        variance = sum((value - mean_return) ** 2 for value in returns) / (len(returns) - 1)
        if variance > 0:
            standard_error = math.sqrt(variance / len(returns))
            observed_z = abs(mean_return) / standard_error
            estimated_power = round(
                max(
                    0.0,
                    min(
                        1.0,
                        _normal_cdf(observed_z - 1.959963984540054)
                        + _normal_cdf(-observed_z - 1.959963984540054),
                    ),
                ),
                8,
            )
    blockers: list[str] = []
    if completed_count < MIN_INDEPENDENT_COMPLETED_SIGNALS:
        blockers.append("insufficient_completed_forward_signals")
    if len(independent_edges) < MIN_INDEPENDENT_EDGES:
        blockers.append("insufficient_independent_edges")
    if elapsed_days < MIN_REAL_ELAPSED_DAYS:
        blockers.append("insufficient_real_elapsed_time")
    if estimated_power is None or estimated_power < MIN_ESTIMATED_POWER:
        blockers.append("insufficient_estimated_statistical_power")
    return {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "qadam_shadow_promotion_readiness",
        "phase_id": PHASE_ID,
        "generated_at": generated_at,
        "status": "ready" if not blockers else "evidence_maturing",
        "promotion_ready": not blockers,
        "completed_signal_count": completed_count,
        "counterfactual_completed_signal_count": len(counterfactual_completed),
        "independent_edge_count": len(independent_edges),
        "real_elapsed_days": round(elapsed_days, 8),
        "estimated_power": estimated_power,
        "estimated_power_method": (
            "two_sided_normal_approximation_from_observed_net_returns"
            if estimated_power is not None
            else "not_measurable"
        ),
        "requirements": {
            "minimum_independent_completed_signals": MIN_INDEPENDENT_COMPLETED_SIGNALS,
            "minimum_independent_edges": MIN_INDEPENDENT_EDGES,
            "minimum_real_elapsed_days": MIN_REAL_ELAPSED_DAYS,
            "minimum_estimated_power": MIN_ESTIMATED_POWER,
            "signal_count_and_power_required_not_calendar_alone": True,
        },
        "blockers": blockers,
        "historical_replay_can_satisfy_forward_requirement": False,
        "simulated_elapsed_time_allowed": False,
        "proof_eligible": False,
        "authority": authority_flags(),
    }


def _heartbeat_fresh(
    heartbeat: dict[str, Any], *, generated_at: datetime
) -> tuple[bool, float | None]:
    observed = parse_timestamp(heartbeat.get("generated_at"))
    if observed is None:
        return False, None
    age = (generated_at - observed).total_seconds()
    return 0 <= age <= SERVICE_HEARTBEAT_MAX_AGE_SECONDS, age


def build_forward_shadow_state_from_inputs(
    hypotheses: list[dict[str, Any]],
    akber_inputs: list[dict[str, Any]],
    akber_results: list[dict[str, Any]],
    existing_decisions: list[dict[str, Any]],
    existing_outcomes: list[dict[str, Any]],
    threshold_proposals: list[dict[str, Any]],
    price_observations: list[dict[str, Any]],
    supervisor_status: dict[str, Any],
    supervisor_heartbeat: dict[str, Any],
    shadow_heartbeat: dict[str, Any],
    *,
    generated_at: str,
    supervised_cycle: bool = False,
    provider_status: dict[str, Any] | None = None,
    rejected_price_observations: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    now = parse_timestamp(generated_at)
    if now is None:
        raise ValueError("shadow_generated_at_invalid")
    akber_by_hypothesis = {
        str(record.get("hypothesis_id")): record
        for record in akber_results
        if record.get("hypothesis_id")
    }
    akber_inputs_by_id = {
        str(record.get("akber_input_id")): record
        for record in akber_inputs
        if record.get("akber_input_id")
    }
    reconciled_existing, reconciled_semantic_duplicate_count = (
        _reconcile_logical_duplicate_decisions(existing_decisions)
    )
    decisions_by_id = {
        str(record.get("decision_id")): record
        for record in reconciled_existing
        if record.get("decision_id")
    }
    outcome_by_decision = {
        str(record.get("decision_id")): record
        for record in existing_outcomes
        if record.get("decision_id")
    }
    duplicate_input_decision_count = len(existing_decisions) - len(decisions_by_id)
    duplicate_input_outcome_count = len(existing_outcomes) - len(outcome_by_decision)
    eligible_count = 0
    trade_progression_eligible_count = 0
    counterfactual_observation_count = 0
    waiting_for_entry: list[dict[str, Any]] = []
    for hypothesis in hypotheses:
        hypothesis_id = str(hypothesis.get("hypothesis_id") or "")
        akber = akber_by_hypothesis.get(hypothesis_id)
        eligible, basis = _shadow_eligible(hypothesis, akber)
        if not eligible:
            continue
        eligible_count += 1
        if _promotion_evidence_allowed(basis):
            trade_progression_eligible_count += 1
        else:
            counterfactual_observation_count += 1
        akber_input = (
            akber_inputs_by_id.get(str(akber.get("akber_input_id")))
            if isinstance(akber, dict)
            else None
        )
        expected_signal_id = economic_signal_identity_for_hypothesis(
            hypothesis, akber_input
        )
        if any(
            _decision_economic_signal_identity(record) == expected_signal_id
            for record in decisions_by_id.values()
        ):
            continue
        instrument = str(
            hypothesis.get("instrument_proxy_mapping", {}).get("execution_proxy") or ""
        )
        observation = _latest_entry_observation(price_observations, instrument, decision_at=now)
        if observation is None:
            waiting_for_entry.append(
                {
                    "hypothesis_id": hypothesis_id,
                    "edge_id": hypothesis.get("edge_lineage", {}).get("edge_id"),
                    "instrument": instrument,
                    "eligibility_basis": basis,
                    "state": "waiting_for_fresh_provider_backed_entry_observation",
                    "synthetic_or_sample_fallback_allowed": False,
                }
            )
            continue
        decision = freeze_shadow_decision(
            hypothesis,
            akber,
            decision_at=generated_at,
            entry_observation=observation,
            akber_input=akber_input,
            threshold_proposals=threshold_proposals,
            require_entry_observation=True,
        )
        decisions_by_id[str(decision["decision_id"])] = decision

    for decision_id, decision in list(decisions_by_id.items()):
        if decision_id in outcome_by_decision:
            continue
        if decision.get("lifecycle_state") == "superseded_logical_duplicate":
            continue
        due_at = parse_timestamp(decision.get("outcome_due_at"))
        if due_at is None or now < due_at:
            continue
        observation = _first_outcome_observation(
            price_observations,
            str(decision.get("instrument") or ""),
            due_at=due_at,
            as_of=now,
        )
        if observation is None:
            continue
        outcome_by_decision[decision_id] = complete_shadow_outcome_from_observation(
            decision, observation
        )

    outcome_ids = set(outcome_by_decision)
    decisions = [
        _refresh_lifecycle(record, outcome_ids, now=now) for record in decisions_by_id.values()
    ]
    decisions.sort(
        key=lambda record: (
            str(record.get("decision_at")),
            str(record.get("decision_id")),
        )
    )
    outcomes = list(outcome_by_decision.values())
    outcomes.sort(
        key=lambda record: (
            str(record.get("outcome_available_at")),
            str(record.get("outcome_id")),
        )
    )
    calibration = _calibration(decisions, outcomes, generated_at)
    promotion = _promotion_readiness(decisions, outcomes, generated_at)
    supervisor_fresh, supervisor_age = _heartbeat_fresh(supervisor_heartbeat, generated_at=now)
    shadow_fresh, shadow_age = _heartbeat_fresh(shadow_heartbeat, generated_at=now)
    supervisor_phase_matches = supervisor_heartbeat.get("current_phase") == PHASE_ID
    supervisor_state_matches = supervisor_heartbeat.get("status") in {
        "working",
        "idle_ready",
    }
    operator_scheduler_active = supervisor_status.get("operator_scheduler_active") is True
    scheduler_owner = (
        "qadam_operator_service"
        if supervised_cycle or operator_scheduler_active
        else "legacy_research_supervisor"
    )
    shadow_supervised = shadow_heartbeat.get("supervised_by") in {
        "OR-1",
        "qadam_operator_service",
    }
    supervisor_heartbeat_proves_cycle = bool(
        supervised_cycle
        or (
            supervisor_fresh
            and shadow_fresh
            and supervisor_phase_matches
            and supervisor_state_matches
            and shadow_supervised
        )
    )
    continuous_scheduler_installed = bool(
        supervised_cycle
        or operator_scheduler_active
        or supervisor_status.get("supervisor_schedule_loaded") is True
    )
    shadow_service_cycle_fresh = supervisor_heartbeat_proves_cycle
    shadow_service_running = bool(shadow_service_cycle_fresh and continuous_scheduler_installed)
    if shadow_service_cycle_fresh and not continuous_scheduler_installed:
        status = "cycle_verified_not_continuously_scheduled"
    elif not shadow_service_running:
        status = "ready_not_running"
    elif eligible_count == 0:
        status = "running_idle_no_eligible_hypothesis"
    elif waiting_for_entry:
        status = "running_waiting_for_provider_context"
    elif any(record.get("lifecycle_state") not in TERMINAL_DECISION_STATES for record in decisions):
        status = "running_tracking_real_outcomes"
    else:
        status = "running_idle_all_current_signals_terminal"
    lifecycle_counts = Counter(record.get("lifecycle_state") for record in decisions)
    phase_acceptance_ready = bool(
        promotion.get("promotion_ready") is True
        and supervisor_heartbeat_proves_cycle
        and continuous_scheduler_installed
        and not waiting_for_entry
    )
    state = {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "qadam_forward_shadow_state",
        "phase_id": PHASE_ID,
        "generated_at": generated_at,
        "status": status,
        "policy_version": POLICY_VERSION,
        "implementation_complete": True,
        "hypothesis_count": len(hypotheses),
        "eligible_hypothesis_count": eligible_count,
        "trade_progression_eligible_hypothesis_count": trade_progression_eligible_count,
        "counterfactual_observation_hypothesis_count": counterfactual_observation_count,
        "eligible_waiting_for_entry_count": len(waiting_for_entry),
        "eligible_waiting_for_entry": waiting_for_entry,
        "decision_count": len(decisions),
        "outcome_count": len(outcomes),
        "duplicate_input_decision_count": duplicate_input_decision_count,
        "duplicate_input_outcome_count": duplicate_input_outcome_count,
        "reconciled_semantic_duplicate_decision_count": (
            reconciled_semantic_duplicate_count
        ),
        "lifecycle_counts": dict(sorted(lifecycle_counts.items(), key=lambda item: str(item[0]))),
        "supervisor_status": supervisor_status.get("status") or "missing",
        "supervisor_installed": supervisor_status.get("supervisor_installed") is True,
        "supervisor_heartbeat_status": supervisor_heartbeat.get("status") or "missing",
        "supervisor_heartbeat_age_seconds": supervisor_age,
        "shadow_heartbeat_age_seconds": shadow_age,
        "supervisor_heartbeat_proves_shadow_cycle": supervisor_heartbeat_proves_cycle,
        "shadow_service_cycle_fresh": shadow_service_cycle_fresh,
        "shadow_service_running": shadow_service_running,
        "continuous_scheduler_installed": continuous_scheduler_installed,
        "scheduler_owner": scheduler_owner,
        "phase_acceptance_ready": phase_acceptance_ready,
        "real_elapsed_time_only": True,
        "historical_replay_credit_count": 0,
        "paper_order_created_count": 0,
        "proof_credit_count": 0,
        "provider_status": provider_status or {},
        "accepted_price_observation_count": len(price_observations),
        "rejected_price_observation_count": len(rejected_price_observations or []),
        "valid_no_eligible_hypothesis_outcome": eligible_count == 0,
        "plain_english": (
            "Forward shadowing is running safely, but no edge-backed idea is eligible yet."
            if shadow_service_cycle_fresh and eligible_count == 0
            else "Qadam is recording hypothetical decisions without placing orders."
            if shadow_service_cycle_fresh
            else "The forward-shadow code is ready, but no supervised cycle is currently fresh."
        ),
        "authority": authority_flags(),
    }
    heartbeat = {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "qadam_forward_shadow_heartbeat",
        "phase_id": PHASE_ID,
        "generated_at": generated_at,
        "status": status,
        "supervised_by": scheduler_owner if supervised_cycle else shadow_heartbeat.get("supervised_by"),
        "decision_count": len(decisions),
        "outcome_count": len(outcomes),
        "eligible_hypothesis_count": eligible_count,
        "paper_order_created_count": 0,
        "proof_credit_count": 0,
        "authority": authority_flags(),
    }
    return {
        "state": state,
        "decisions": decisions,
        "outcomes": outcomes,
        "calibration": calibration,
        "promotion": promotion,
        "heartbeat": heartbeat,
    }


def build_forward_shadow_state(
    settings: Settings | None = None,
    *,
    generated_at: str | None = None,
    allow_network: bool = False,
    supervised_cycle: bool = False,
) -> dict[str, Any]:
    settings = settings or Settings.from_env()
    runtime = runtime_dir(settings)
    generated = generated_at or now_iso()
    # The canonical compiler owns the only downstream hypothesis and Akber lane.
    hypotheses = read_jsonl(runtime / HYPOTHESES_ARTIFACT)
    akber_inputs = read_jsonl(runtime / AKBER_INPUTS_ARTIFACT)
    akber_results = read_jsonl(runtime / AKBER_RESULTS_ARTIFACT)
    market_context = read_json(runtime / MARKET_CONTEXT_ARTIFACT)
    observations, rejected = extract_runtime_price_observations(
        market_context, generated_at=generated
    )
    eligible_instruments: list[str] = []
    akber_by_hypothesis = {
        str(row.get("hypothesis_id")): row for row in akber_results if row.get("hypothesis_id")
    }
    for hypothesis in hypotheses:
        eligible, _basis = _shadow_eligible(
            hypothesis, akber_by_hypothesis.get(str(hypothesis.get("hypothesis_id")))
        )
        if eligible:
            instrument = str(
                hypothesis.get("instrument_proxy_mapping", {}).get("execution_proxy") or ""
            )
            if instrument:
                eligible_instruments.append(instrument)
    provider_status: dict[str, Any] = {
        "provider": ALPACA_PRICE_PROVIDER,
        "status": (
            "not_needed_no_eligible_hypotheses"
            if not eligible_instruments
            else "network_disabled_for_read_only_check"
        ),
        "broker_endpoint_used": False,
        "requested_symbol_count": 0,
        "returned_observation_count": 0,
    }
    if allow_network:
        provider_observations, provider_status = fetch_alpaca_latest_bar_observations(
            eligible_instruments,
            settings,
            generated_at=generated,
        )
        observations.extend(provider_observations)
    legacy_supervisor_status = read_json(runtime / SUPERVISOR_STATUS_ARTIFACT)
    operator_status = read_json(runtime / OPERATOR_STATUS_ARTIFACT)
    operator_forward_shadow = next(
        (
            row
            for row in operator_status.get("services", [])
            if isinstance(row, dict) and row.get("service_id") == "forward_shadow"
        ),
        {},
    )
    scheduler_status = dict(legacy_supervisor_status)
    scheduler_status["operator_scheduler_active"] = bool(
        operator_status.get("service_running") is True
        and operator_status.get("liveness", {}).get("process_running") is True
        and operator_forward_shadow.get("current_execution_allowed") is True
    )
    return build_forward_shadow_state_from_inputs(
        hypotheses,
        akber_inputs,
        akber_results,
        read_jsonl(runtime / DECISIONS_ARTIFACT),
        read_jsonl(runtime / OUTCOMES_ARTIFACT),
        read_jsonl(runtime / AKBER_THRESHOLD_PROPOSALS_ARTIFACT),
        observations,
        scheduler_status,
        read_json(runtime / SUPERVISOR_HEARTBEAT_ARTIFACT),
        read_json(runtime / HEARTBEAT_ARTIFACT),
        generated_at=generated,
        supervised_cycle=supervised_cycle,
        provider_status=provider_status,
        rejected_price_observations=rejected,
    )


def validate_forward_shadow_state(bundle: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    state = bundle["state"]
    decisions = bundle["decisions"]
    outcomes = bundle["outcomes"]
    decision_by_id = {
        str(record.get("decision_id")): record for record in decisions if record.get("decision_id")
    }
    if len(decision_by_id) != len(decisions):
        errors.append("shadow_decision_id_missing_or_duplicate")
    if state.get("duplicate_input_decision_count") != 0:
        errors.append("shadow_duplicate_input_decision_detected")
    if state.get("duplicate_input_outcome_count") != 0:
        errors.append("shadow_duplicate_input_outcome_detected")
    active_signals = [
        _decision_economic_signal_identity(record)
        for record in decisions
        if record.get("lifecycle_state") != "superseded_logical_duplicate"
    ]
    if len(active_signals) != len(set(active_signals)):
        errors.append("shadow_duplicate_active_economic_signal")
    outcomes_by_decision: dict[str, list[dict[str, Any]]] = {}
    for outcome in outcomes:
        decision_id = str(outcome.get("decision_id") or "")
        outcomes_by_decision.setdefault(decision_id, []).append(outcome)
        decision = decision_by_id.get(decision_id)
        if decision is None:
            errors.append(f"shadow_outcome_decision_missing:{decision_id}")
        else:
            decided = parse_timestamp(decision.get("decision_at"))
            due_at = parse_timestamp(decision.get("outcome_due_at"))
            observed = parse_timestamp(outcome.get("outcome_available_at"))
            if decided is None or observed is None or observed <= decided:
                errors.append(f"shadow_outcome_temporal_leakage:{decision_id}")
            if due_at is not None and observed is not None and observed < due_at:
                errors.append(f"shadow_outcome_before_real_horizon:{decision_id}")
        if outcome.get("simulated_elapsed_time") is not False:
            errors.append("shadow_outcome_simulated_elapsed_time")
        if outcome.get("paper_order_created") is not False:
            errors.append("shadow_outcome_created_order")
        if outcome.get("proof_eligible") is not False:
            errors.append("shadow_outcome_proof_eligible")
        errors.extend(validate_authority(outcome.get("authority", {}), prefix="shadow_outcome"))
    if any(len(rows) != 1 for rows in outcomes_by_decision.values()):
        errors.append("shadow_multiple_outcomes_for_one_decision")
    for decision in decisions:
        decision_id = str(decision.get("decision_id") or "")
        if decision.get("decision_frozen_before_outcome") is not True:
            errors.append(f"shadow_decision_not_frozen:{decision_id}")
        frozen_payload = decision.get("frozen_decision_payload")
        if not isinstance(frozen_payload, dict) or sha256_json(frozen_payload) != decision.get(
            "frozen_decision_hash"
        ):
            errors.append(f"shadow_frozen_decision_hash_invalid:{decision_id}")
        if decision.get("entry_observation_required") is True:
            entry = decision.get("entry_observation")
            if not isinstance(entry, dict) or _observation_errors(entry):
                errors.append(f"shadow_entry_observation_invalid:{decision_id}")
        if decision.get("simulated_elapsed_time") is not False:
            errors.append(f"shadow_decision_simulated_elapsed:{decision_id}")
        if decision.get("paper_order_created") is not False:
            errors.append(f"shadow_decision_created_order:{decision_id}")
        if decision.get("proof_eligible") is not False:
            errors.append(f"shadow_decision_proof_eligible:{decision_id}")
        if decision.get("lifecycle_state") == "superseded_logical_duplicate":
            if not decision.get("logical_duplicate_of_decision_id"):
                errors.append(f"shadow_superseded_duplicate_lineage_missing:{decision_id}")
            if decision.get("promotion_evidence_allowed") is not False:
                errors.append(f"shadow_superseded_duplicate_can_promote:{decision_id}")
        lifecycle = decision.get("lifecycle_state")
        if lifecycle == "completed" and not outcomes_by_decision.get(decision_id):
            errors.append(f"shadow_completed_without_outcome:{decision_id}")
        if lifecycle == "expired_unscored" and not decision.get("typed_expiry_reason"):
            errors.append(f"shadow_expiry_reason_missing:{decision_id}")
        errors.extend(validate_authority(decision.get("authority", {}), prefix="shadow_decision"))
    promotion = bundle["promotion"]
    if promotion.get("promotion_ready") is True:
        requirements = promotion.get("requirements", {})
        if promotion.get("completed_signal_count", 0) < requirements.get(
            "minimum_independent_completed_signals",
            MIN_INDEPENDENT_COMPLETED_SIGNALS,
        ):
            errors.append("shadow_promotion_without_signal_count")
        if promotion.get("independent_edge_count", 0) < requirements.get(
            "minimum_independent_edges", MIN_INDEPENDENT_EDGES
        ):
            errors.append("shadow_promotion_without_independent_edges")
        if promotion.get("real_elapsed_days", 0) < requirements.get(
            "minimum_real_elapsed_days", MIN_REAL_ELAPSED_DAYS
        ):
            errors.append("shadow_promotion_without_real_elapsed_time")
        if safe_float(promotion.get("estimated_power")) < safe_float(
            requirements.get("minimum_estimated_power"), MIN_ESTIMATED_POWER
        ):
            errors.append("shadow_promotion_without_power")
    if promotion.get("historical_replay_can_satisfy_forward_requirement") is not False:
        errors.append("historical_replay_allowed_forward_credit")
    for field in (
        "historical_replay_credit_count",
        "paper_order_created_count",
        "proof_credit_count",
    ):
        if state.get(field) != 0:
            errors.append(f"shadow_forbidden_count_nonzero:{field}")
    if (
        state.get("shadow_service_running") is True
        and state.get("supervisor_heartbeat_proves_shadow_cycle") is not True
    ):
        errors.append("shadow_service_running_without_supervisor_heartbeat")
    errors.extend(validate_authority(state.get("authority", {}), prefix="shadow_state"))
    errors.extend(
        validate_authority(bundle["calibration"].get("authority", {}), prefix="shadow_calibration")
    )
    errors.extend(validate_authority(promotion.get("authority", {}), prefix="shadow_promotion"))
    errors.extend(
        validate_authority(bundle["heartbeat"].get("authority", {}), prefix="shadow_heartbeat")
    )
    return unique_errors(errors)


def build_and_write_forward_shadow(
    settings: Settings | None = None,
    *,
    allow_network: bool = False,
    supervised_cycle: bool = False,
) -> tuple[dict[str, Any], dict[str, Any], list[str]]:
    settings = settings or Settings.from_env()
    runtime = runtime_dir(settings)
    store = AtomicArtifactStore(runtime)
    bundle = build_forward_shadow_state(
        settings,
        allow_network=allow_network,
        supervised_cycle=supervised_cycle,
    )
    store.write_json(STATE_ARTIFACT, bundle["state"])
    store.write_jsonl(DECISIONS_ARTIFACT, bundle["decisions"])
    store.write_jsonl(OUTCOMES_ARTIFACT, bundle["outcomes"])
    store.write_json(CALIBRATION_ARTIFACT, bundle["calibration"])
    store.write_json(PROMOTION_ARTIFACT, bundle["promotion"])
    if supervised_cycle:
        store.write_json(HEARTBEAT_ARTIFACT, bundle["heartbeat"])
    errors = validate_forward_shadow_state(bundle)
    phase_acceptance_ready = bool(
        not errors and bundle["state"].get("phase_acceptance_ready") is True
    )
    blockers = list(bundle["promotion"].get("blockers", []))
    if bundle["state"].get("supervisor_heartbeat_proves_shadow_cycle") is not True:
        blockers.append("supervisor_shadow_cycle_not_fresh")
    if bundle["state"].get("continuous_scheduler_installed") is not True:
        blockers.append("continuous_supervisor_installation_pending_operator_action")
    if bundle["state"].get("eligible_waiting_for_entry_count", 0) > 0:
        blockers.append("eligible_hypothesis_missing_fresh_provider_backed_entry")
    if bundle["state"].get("eligible_hypothesis_count", 0) == 0:
        blockers.append("no_eligible_hypothesis_from_or11_or_akber")
    checks = {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "qadam_forward_shadow_checks",
        "phase_id": PHASE_ID,
        "generated_at": now_iso(),
        "status": (
            "blocked" if errors else "passed" if phase_acceptance_ready else "evidence_maturing"
        ),
        "implementation_ready": not errors,
        "implementation_complete": not errors,
        "phase_acceptance_ready": phase_acceptance_ready,
        "service_state": bundle["state"]["status"],
        "supervisor_running": bundle["state"]["continuous_scheduler_installed"],
        "supervisor_heartbeat_proves_shadow_cycle": bundle["state"][
            "supervisor_heartbeat_proves_shadow_cycle"
        ],
        "shadow_service_cycle_fresh": bundle["state"]["shadow_service_cycle_fresh"],
        "continuous_scheduler_installed": bundle["state"]["continuous_scheduler_installed"],
        "shadow_service_running": bundle["state"]["shadow_service_running"],
        "eligible_hypothesis_count": bundle["state"]["eligible_hypothesis_count"],
        "trade_progression_eligible_hypothesis_count": bundle["state"][
            "trade_progression_eligible_hypothesis_count"
        ],
        "counterfactual_observation_hypothesis_count": bundle["state"][
            "counterfactual_observation_hypothesis_count"
        ],
        "eligible_waiting_for_entry_count": bundle["state"]["eligible_waiting_for_entry_count"],
        "valid_no_eligible_hypothesis_outcome": bundle["state"][
            "valid_no_eligible_hypothesis_outcome"
        ],
        "decision_count": len(bundle["decisions"]),
        "outcome_count": len(bundle["outcomes"]),
        "counterfactual_completed_signal_count": bundle["promotion"].get(
            "counterfactual_completed_signal_count", 0
        ),
        "completed_or_typed_expiry_count": sum(
            record.get("lifecycle_state") in TERMINAL_DECISION_STATES
            for record in bundle["decisions"]
        ),
        "promotion_ready": bundle["promotion"]["promotion_ready"],
        "promotion_blockers": bundle["promotion"].get("blockers", []),
        "real_elapsed_days": bundle["promotion"]["real_elapsed_days"],
        "estimated_power": bundle["promotion"].get("estimated_power"),
        "calibration_state": bundle["calibration"].get("status"),
        "provider_status": bundle["state"].get("provider_status", {}),
        "blockers": unique_errors(blockers),
        "historical_replay_credit_count": 0,
        "simulated_elapsed_time_count": 0,
        "paper_order_created_count": 0,
        "proof_credit_count": 0,
        "paper_calendar_advanced": False,
        "validation_error_count": len(errors),
        "validation_errors": errors,
        "broker_write_count": 0,
        "paperops_watch_only": True,
        "authority": authority_flags(),
    }
    store.write_json(CHECK_ARTIFACT, checks)
    return bundle, checks, errors
