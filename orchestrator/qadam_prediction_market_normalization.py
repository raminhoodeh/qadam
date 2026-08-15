"""Normalize archived Kalshi and Polymarket histories into contract identities."""

from __future__ import annotations

from collections import defaultdict
import json
from pathlib import Path
import re
from typing import Any, Iterable

from orchestrator.config import Settings
from orchestrator.qadam_canonical_contracts import AtomicArtifactStore
from orchestrator.qadam_qualitative_common import (
    PREDICTION_CONTRACTS_ARTIFACT,
    PREDICTION_CONTRACTS_PUBLIC_ARTIFACT,
    now_iso,
    public_authority,
    repo_root,
    runtime_dir,
    stable_id,
)


def iter_prediction_history(venue: str) -> Iterable[dict[str, Any]]:
    root = repo_root() / "data" / "research" / "normalized" / f"source={venue}"
    for path in sorted(root.glob("date=*/records.jsonl")):
        try:
            handle = path.open("r", encoding="utf-8")
        except OSError:
            continue
        with handle:
            for line in handle:
                if not line.strip():
                    continue
                try:
                    row = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if isinstance(row, dict):
                    yield row


def _identity(venue: str, row: dict[str, Any]) -> str | None:
    if venue == "kalshi":
        ticker = str(row.get("market_ticker") or row.get("event_ticker") or "")
        return f"kalshi:{ticker}" if ticker else None
    condition = str(row.get("condition_id") or row.get("market_id") or "")
    outcome = str(row.get("outcome") or row.get("token_id") or "market")
    return f"polymarket:{condition}:{outcome}" if condition else None


def listed_proxy_mapping(question: str, terms: list[str]) -> dict[str, Any]:
    text = " ".join([question, *terms]).lower()
    recipes = (
        (("oil", "energy", "opec", "gas"), ["USO", "XLE"], "Energy-supply expectations may affect listed energy proxies."),
        (("war", "defence", "defense", "military", "conflict"), ["XAR", "ITA"], "Geopolitical risk may affect listed defence proxies."),
        (("chip", "semiconductor", "ai", "technology"), ["SMH", "SOXX"], "Technology-policy expectations may affect semiconductor proxies."),
        (("gold", "silver", "metal"), ["GLD", "SLV"], "Monetary or geopolitical expectations may affect precious-metal proxies."),
        (("recession", "inflation", "rates", "fed", "election", "economy"), ["SPY", "QQQ"], "Macro expectations may affect broad listed-market proxies."),
    )
    for keywords, symbols, mechanism in recipes:
        if any(keyword in text for keyword in keywords):
            return {"symbols": symbols, "mechanism": mechanism, "mapping_state": "research_hypothesis"}
    return {"symbols": [], "mechanism": None, "mapping_state": "unmapped"}


def normalize_prediction_contracts(
    settings: Settings | None = None,
) -> tuple[list[dict[str, Any]], dict[str, Any], list[str]]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    venue_by_id: dict[str, str] = {}
    for venue in ("kalshi", "polymarket"):
        for row in iter_prediction_history(venue):
            identity = _identity(venue, row)
            if identity:
                grouped[identity].append(row)
                venue_by_id[identity] = venue
    contracts: list[dict[str, Any]] = []
    for identity, rows in sorted(grouped.items()):
        venue = venue_by_id[identity]
        ordered = sorted(rows, key=lambda row: str(row.get("source_available_at") or row.get("event_timestamp") or ""))
        first, latest = ordered[0], ordered[-1]
        question = str(next((row.get("question") or row.get("title") for row in ordered if row.get("question") or row.get("title")), identity))
        terms = sorted({str(term) for row in ordered for term in row.get("matched_research_terms") or []})
        mapping = listed_proxy_mapping(question, terms)
        contracts.append({
            "schema_version": "qadam_prediction_contract.v1",
            "artifact_type": "qadam_prediction_contract",
            "contract_id": stable_id("prediction-contract", identity),
            "venue": venue,
            "venue_contract_identity": identity,
            "event_identity": first.get("event_ticker") or first.get("condition_id") or first.get("market_id"),
            "market_identity": first.get("market_ticker") or first.get("market_id"),
            "condition_identity": first.get("condition_id"),
            "outcome_token_identity": first.get("token_id") or first.get("outcome"),
            "canonical_question": question,
            "normalized_event_ontology": terms,
            "relationships": {"mutually_exclusive": "unknown", "exhaustive": "unknown", "conditional": [], "equivalent": []},
            "open_time": first.get("source_available_at") or first.get("event_timestamp"),
            "close_time": None,
            "expiry_time": None,
            "resolution_time": next((row.get("source_available_at") for row in reversed(ordered) if row.get("record_type") == "prediction_market_result"), None),
            "definition_revisions": [{"available_at": first.get("source_available_at"), "question": question}],
            "resolution_source": "venue_archive",
            "settlement_rule": "not_present_in_normalized_signal_archive",
            "dispute_state": "unknown",
            "ambiguity_label": "semantics_review_required",
            "observation_count": len(rows),
            "coverage_start": first.get("source_available_at") or first.get("event_timestamp"),
            "coverage_end": latest.get("source_available_at") or latest.get("event_timestamp"),
            "available_fields": sorted({key for row in rows for key in row}),
            "listed_proxy_mapping": mapping,
            "direct_venue_paperability": False,
            "origin": venue,
            "transport": "provider_backed_historical_archive",
            "parser_version": "qadam_prediction_market_normalization.v1",
            "terms_state": "reviewed_private_internal_research",
            "record_set_hash": stable_id("prediction-record-set", identity, len(rows), latest.get("source_available_at")),
            "source_quorum_credit_allowed": False,
            "strategy_or_trade_authority": False,
            "authority": public_authority(),
        })
    runtime = runtime_dir(settings)
    store = AtomicArtifactStore(runtime)
    store.write_jsonl(PREDICTION_CONTRACTS_ARTIFACT, contracts)
    store.write_jsonl(PREDICTION_CONTRACTS_PUBLIC_ARTIFACT, contracts)
    summary = {
        "schema_version": "qadam_prediction_market_normalization.v1",
        "artifact_type": "qadam_prediction_market_normalization_summary",
        "generated_at": now_iso(),
        "status": "passed" if contracts else "blocked_no_contract_history",
        "contract_count": len(contracts),
        "venue_counts": {venue: sum(row["venue"] == venue for row in contracts) for venue in ("kalshi", "polymarket")},
        "mapped_contract_count": sum(bool(row["listed_proxy_mapping"]["symbols"]) for row in contracts),
        "direct_venue_paperability_count": 0,
        "authority": public_authority(),
    }
    return contracts, summary, [] if contracts else ["prediction_contract_history_missing"]


__all__ = ["iter_prediction_history", "listed_proxy_mapping", "normalize_prediction_contracts"]
