"""Preregistered, version-matched forward review; this module cannot place orders."""

from datetime import datetime, timezone
from collections import Counter
import math
from statistics import mean, stdev
from typing import Any


def _time(value: Any):
    try:
        result = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        return result.astimezone(timezone.utc) if result.tzinfo else None
    except ValueError:
        return None


def evaluate_forward_version(version: str | None, records: list[dict], *, as_of: str, trial_index: int = 1) -> dict:
    eligible = []
    latest_end = None
    seen_events = set()
    exclusions = []
    for row in sorted(records, key=lambda item: str(item.get("decision_at") or "")):
        if not version or row.get("strategy_version_id") != version:
            continue
        start, end, cutoff = _time(row.get("decision_at")), _time(row.get("outcome_available_at")), _time(as_of)
        event = row.get("economic_signal_identity_id")
        values = (row.get("net_return"), row.get("benchmark_net_return"))
        reasons = []
        if row.get("simulated_elapsed_time") is not False:
            reasons.append("not_real_elapsed_time")
        if not start or not end or not cutoff or not start < end <= cutoff:
            reasons.append("invalid_or_unmatured_window")
        if not event:
            reasons.append("missing_economic_event_identity")
        if event in seen_events:
            reasons.append("duplicate_economic_event")
        if start and latest_end and start <= latest_end:
            reasons.append("overlapping_event_window")
        if (row.get("evaluation_contract") or {}).get("version") != "matched-forward.1":
            reasons.append("evaluation_contract_mismatch")
        if row.get("benchmark_comparison_available") is not True:
            reasons.append("matched_benchmark_unavailable")
        if any(isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v) for v in values):
            reasons.append("invalid_return_value")
        if any((row.get(key) or {}).get("provider_backed") is not True
               for key in ("entry_observation", "outcome_observation", "benchmark_observation")):
            reasons.append("provider_evidence_missing")
        if reasons:
            exclusions.append({"outcome_id": row.get("outcome_id"), "reasons": reasons})
            continue
        seen_events.add(event)
        latest_end = end
        eligible.append(row)
    available_count = len(eligible)
    look = 1
    review_count = 20
    while review_count * 2 <= available_count:
        review_count *= 2
        look += 1
    eligible = eligible[:review_count]
    returns = [row["net_return"] for row in eligible]
    deltas = [row["net_return"] - row["benchmark_net_return"] for row in eligible]
    n = len(returns)
    # A conservative review screen, not a claim of statistical or economic proof.
    lower = mean(returns) - 3.5 * stdev(returns) / math.sqrt(n) if n > 1 else None
    relative_lower = mean(deltas) - 3.5 * stdev(deltas) / math.sqrt(n) if n > 1 else None
    blockers = []
    if n < 20:
        blockers.append("insufficient_independent_matched_forward_events")
    if lower is None or lower <= 0:
        blockers.append("positive_conservative_forward_return_not_demonstrated")
    if relative_lower is None or relative_lower <= 0:
        blockers.append("incremental_value_over_matched_benchmark_not_demonstrated")
    positive = [max(value, 0) for value in returns]
    if positive and sum(positive) > 0 and max(positive) > sum(positive) * 0.5:
        blockers.append("single_event_dominates_positive_returns")
    # Summable error budgets cover both comparators, all registered versions and
    # the frozen 20/40/80/... review checkpoints. This tests win consistency, not
    # a distribution-free guarantee of positive expected profit.
    trial_index = max(1, int(trial_index))
    alpha = 0.05 / (2 * trial_index * (trial_index + 1) * look * (look + 1))
    def sign_probability(values):
        wins = sum(value > 0 for value in values)
        return sum(math.comb(len(values), k) for k in range(wins, len(values) + 1)) / (2 ** len(values))
    p_cash, p_benchmark = sign_probability(returns), sign_probability(deltas)
    if max(p_cash, p_benchmark) > alpha:
        blockers.append("multiplicity_adjusted_win_consistency_not_demonstrated")
    event_equity = high_water = 1.0
    event_drawdown = 0.0
    for value in returns:
        event_equity *= 1 + value
        if event_equity <= 0:
            event_drawdown = None
            break
        high_water = max(high_water, event_equity)
        event_drawdown = max(event_drawdown, 1 - event_equity / high_water)
    return {
        "strategy_version_id": version, "evaluation_policy_version": "matched-forward.1",
        "raw_matching_outcome_count": sum(row.get("strategy_version_id") == version for row in records) if version else 0,
        "independent_outcome_count": n, "minimum_independent_outcomes": 20,
        "available_independent_outcomes": available_count, "review_checkpoint": review_count,
        "exclusions": exclusions,
        "exclusion_counts": dict(Counter(reason for row in exclusions for reason in row["reasons"])),
        "eligible_pending_next_checkpoint_count": max(0, available_count - n),
        "next_review_checkpoint": review_count if n < review_count else review_count * 2,
        "discovery_permission_requires_review_completion": False,
        "trial_index": trial_index, "review_index": look, "comparator_alpha": alpha,
        "cash_sign_p": p_cash, "benchmark_sign_p": p_benchmark,
        "regime_generalization_proven": False,
        "mean_net_return": mean(returns) if returns else None,
        "mean_benchmark_delta": mean(deltas) if deltas else None,
        "return_dispersion_stdev": stdev(returns) if n > 1 else None,
        "worst_event_net_return": min(returns) if returns else None,
        "largest_positive_event_share": max(positive) / sum(positive) if sum(positive) else None,
        "equal_notional_event_curve_max_drawdown": event_drawdown if returns else None,
        "event_curve_is_actual_portfolio_drawdown": False,
        "regime_observation_counts": dict(Counter(str(row.get("regime") or "unavailable") for row in eligible)),
        "conservative_return_bound": lower, "conservative_relative_bound": relative_lower,
        "eligible_for_emerging_review": not blockers, "blockers": blockers,
        "units": "decimal_return_after_modelled_costs", "paper_only": True,
        "validated_lane_authority_granted": False, "broker_write_count": 0,
    }
