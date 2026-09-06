"""Rank research work by obtainable evidence, without granting trade permission."""

from datetime import datetime
import math


def latest_score_rows(scores: list[dict], *, as_of: str, max_age: int = 21600) -> list[dict]:
    """Use the newest observable score per family/instrument, never its historic maximum."""
    now = datetime.fromisoformat(as_of.replace("Z", "+00:00"))
    latest = {}
    for row in scores:
        if not isinstance(row, dict) or row.get("negative_control"):
            continue
        family, instrument = row.get("strategy_family_id"), row.get("instrument")
        try:
            stamp = datetime.fromisoformat(str(row.get("scoring_as_of") or row.get("generated_at")).replace("Z", "+00:00"))
            age = (now - stamp).total_seconds()
        except (ValueError, TypeError):
            continue
        value = row.get("raw_pattern_score")
        if (not family or not instrument or not 0 <= age <= max_age or isinstance(value, bool)
                or not isinstance(value, (int, float)) or not math.isfinite(value) or not 0 <= value <= 1):
            continue
        key = (family, instrument)
        if key not in latest or stamp > latest[key][0]:
            latest[key] = (stamp, row)
    return [latest[key][1] for key in sorted(latest)]


def rank_programmes(scores: list[dict], capability: dict, *, as_of: str, limit: int = 3) -> dict:
    try:
        age = (datetime.fromisoformat(as_of.replace("Z", "+00:00")) -
               datetime.fromisoformat(capability["generated_at"].replace("Z", "+00:00"))).total_seconds()
        current = 0 <= age <= 1800
    except (KeyError, ValueError, TypeError):
        current = False
    coverage = {row["strategy_family_id"]: row for row in capability.get("strategy_source_coverage", [])
                if isinstance(row, dict) and row.get("strategy_family_id")}
    best = {}
    for score in latest_score_rows(scores, as_of=as_of):
        value, family = score.get("raw_pattern_score"), score.get("strategy_family_id")
        if (not family or score.get("negative_control") or isinstance(value, bool)
            or not isinstance(value, (float, int)) or not math.isfinite(value)):
            continue
        if family not in best or value > best[family]["raw_pattern_score"]:
            best[family] = score
    rows = []
    for family, score in best.items():
        support = coverage.get(family) or {}
        fresh = support.get("fresh_provider_backed_source_keys") or []
        fresh = sorted(set(fresh)) if current else []
        rows.append({"strategy_family_id": family, "instrument": score.get("instrument"),
            "score_id": score.get("score_id"), "raw_pattern_score": score["raw_pattern_score"],
            "input_fingerprint": score.get("input_fingerprint"),
            "score_observed_at": score.get("scoring_as_of") or score.get("generated_at"),
            "fresh_source_keys": fresh, "fresh_source_count": len(fresh),
            "unavailable_source_keys": support.get("unavailable_source_keys") or [],
            "research_state": "evidence_available_for_research" if fresh else "awaiting_provider_evidence",
            "independent_event_count": None, "incremental_value_measured": False,
            "paper_order_authority": False})
    rows.sort(key=lambda row: (-row["fresh_source_count"], -row["raw_pattern_score"], row["strategy_family_id"]))
    selected = [row["strategy_family_id"] for row in rows if row["fresh_source_count"]][:max(0, min(3, limit))]
    return {"schema_version": "research-focus.1", "generated_at": as_of,
            "capability_observed_at": capability.get("generated_at"), "capability_current": current,
            "selected_families": selected, "programmes": rows,
            "selection_basis": "current provider coverage, then latest research score; not expected return",
            "score_max_age_seconds": 21600,
            "other_programmes_retained": True, "risk_policy_changed": False,
            "provider_cost_usd": None, "subscription_cost_usd": None,
            "cost_state": "not_reconciled_to_bills", "cost_is_separate_from_paper_pnl": True}
