"""World-model hypothesis library for Qadam next-generation flow Phase 3.

The library converts broad macro/geopolitical priors into falsifiable scenario
hypotheses. These records can generate research questions and source watchlists,
but they are not evidence, cannot satisfy source quorum, cannot create trade
candidates, and cannot route orders.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
from typing import Any, Iterable

from orchestrator.config import Settings
from orchestrator.world_model import world_model_claims, world_model_summary

SCHEMA_VERSION = "qadam_world_model_hypothesis_library.v1"
PHASE_ID = "qadam_next_generation_phase_3_world_model_hypothesis_library"

PRIMARY_ARTIFACT = "qadam_world_model_hypothesis_library.json"
HYPOTHESES_ARTIFACT = "qadam_world_model_hypotheses.jsonl"
RESEARCH_QUESTIONS_ARTIFACT = "qadam_world_model_research_questions.jsonl"
MARKET_MAPPINGS_ARTIFACT = "qadam_world_model_market_mappings.jsonl"
DASHBOARD_SUMMARY_ARTIFACT = "qadam_world_model_dashboard_summary.json"
EVENTS_ARTIFACT = "qadam_world_model_events.jsonl"

SOURCE_UNIVERSE_ARTIFACT = "qsase_source_universe.json"
TRADING_UNIVERSE_ARTIFACT = "qsase_trading_universe.json"
EVIDENCE_CONTRACTS_SUMMARY_ARTIFACT = "qadam_evidence_contracts_summary.json"
SOURCE_EVIDENCE_CONTRACTS_ARTIFACT = "qadam_source_evidence_contracts.jsonl"
PRICE_EVIDENCE_CONTRACTS_ARTIFACT = "qadam_price_evidence_contracts.jsonl"

AUTHORITY_FLAGS = {
    "read_only": True,
    "paper_only": True,
    "proposal_first": True,
    "context_only": True,
    "private_lens_only": True,
    "public_evidence_allowed": False,
    "factual_evidence_authority": False,
    "source_quorum_credit_allowed": False,
    "source_quorum_satisfied_by_world_model": False,
    "trade_candidate_creation_allowed": False,
    "trade_candidate_created": False,
    "qualified_setup_created": False,
    "risk_handoff_allowed": False,
    "risk_approval_allowed": False,
    "risk_approval_created": False,
    "execution_allowed": False,
    "execution_approval_allowed": False,
    "execution_approval_created": False,
    "paper_order_allowed": False,
    "paper_order_created": False,
    "broker_write_allowed": False,
    "broker_write_count": 0,
    "live_broker_endpoint_allowed": False,
    "live_capital_enabled": False,
    "proof_credit_allowed": False,
    "paper_proof_ledger_credit_allowed": False,
    "paper_growth_trial_calendar_advance_allowed": False,
    "simulated_elapsed_time_allowed": False,
    "strategy_mutation_allowed": False,
    "filter_threshold_update_allowed": False,
    "telegram_command_path_enabled": False,
    "telegram_trade_command_enabled": False,
}

FORBIDDEN_TRUE_FIELDS = tuple(
    key for key, value in AUTHORITY_FLAGS.items() if value is False
)
FORBIDDEN_NONZERO_FIELDS = tuple(
    key for key, value in AUTHORITY_FLAGS.items() if isinstance(value, int) and value == 0
)

SOURCE_ALIASES = {
    "x": "twitter_x",
}

BIAS_LABELS_BY_CLAIM = {
    "narrative_coordination_as_market_force": [
        "narrative_overfitting_risk",
        "social_signal_reflexivity",
        "selection_bias_from_visible_discourse",
    ],
    "institutional_self_preservation_blind_spot": [
        "anti_institutional_bias_risk",
        "policy_lag_misattribution",
        "confirmation_bias_against_official_sources",
    ],
    "hierarchical_power_flows_through_energy_security_and_money": [
        "grand_theory_overreach_risk",
        "commodity_causality_conflation",
        "geopolitical_base_rate_neglect",
    ],
    "us_china_grand_bargain_scenario": [
        "single_scenario_anchor_risk",
        "elite_bargain_speculation_risk",
        "policy_signal_false_positive_risk",
    ],
    "shadow_networks_as_coordination_risk": [
        "hidden_coordination_bias_risk",
        "actor_overlap_false_positive_risk",
        "non_public_information_inference_risk",
    ],
}

FALSIFIERS_BY_CLAIM = {
    "narrative_coordination_as_market_force": [
        "Narrative intensity rises but prediction markets, related ETFs, and source-confirmed events do not move in the hypothesized direction.",
        "Market repricing occurs before the narrative shift, implying the narrative is explanatory lag rather than causal lead.",
        "Independent physical or macro sources contradict the narrative signal.",
    ],
    "institutional_self_preservation_blind_spot": [
        "Official statements align with independent flow, filing, physical, or macro evidence in real time.",
        "No delayed disclosure, language shift, or policy correction follows the stress event.",
        "Market reaction is explained by scheduled macro data rather than institutional framing.",
    ],
    "hierarchical_power_flows_through_energy_security_and_money": [
        "Energy, shipping, dollar-liquidity, and defence indicators do not co-move during the alleged stress regime.",
        "Commodity and defence moves reverse without confirming source evidence.",
        "Source-confirmed chokepoint or reserve-flow stress fails to affect mapped markets across the tested horizon.",
    ],
    "us_china_grand_bargain_scenario": [
        "US-China policy files move in isolation rather than as a bundled settlement.",
        "Semiconductor, Treasury/stablecoin, Taiwan, Iran, and energy indicators contradict the proposed bargain direction.",
        "Mapped markets price a deterioration while policy evidence suggests de-escalation, or vice versa.",
    ],
    "shadow_networks_as_coordination_risk": [
        "Alleged actor overlap disappears after source de-duplication and timing controls.",
        "Policy leaks, filings, and positioning occur after public market repricing rather than before it.",
        "Independent disclosures show routine sector behavior rather than coordinated timing.",
    ],
}

TIME_HORIZONS_BY_CLAIM = {
    "narrative_coordination_as_market_force": ["intraday", "1d", "3d", "5d"],
    "institutional_self_preservation_blind_spot": ["1d", "5d", "20d"],
    "hierarchical_power_flows_through_energy_security_and_money": ["1d", "5d", "20d", "60d"],
    "us_china_grand_bargain_scenario": ["5d", "20d", "60d"],
    "shadow_networks_as_coordination_risk": ["1d", "5d", "20d"],
}

BASE_CONFIDENCE_BY_CLAIM = {
    "narrative_coordination_as_market_force": 0.24,
    "institutional_self_preservation_blind_spot": 0.22,
    "hierarchical_power_flows_through_energy_security_and_money": 0.26,
    "us_china_grand_bargain_scenario": 0.2,
    "shadow_networks_as_coordination_risk": 0.18,
}


@dataclass(frozen=True)
class WorldModelBundle:
    primary: dict[str, Any]
    hypotheses: list[dict[str, Any]]
    research_questions: list[dict[str, Any]]
    market_mappings: list[dict[str, Any]]
    dashboard_summary: dict[str, Any]


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def _runtime_dir(settings: Settings | None = None) -> Path:
    active_settings = settings or Settings.from_env()
    path = Path(active_settings.runtime_dir)
    if not path.is_absolute():
        path = _repo_root() / path
    return path


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _iso(dt: datetime | None = None) -> str:
    return (dt or _now()).astimezone(timezone.utc).isoformat()


def _json_dump(payload: dict[str, Any]) -> str:
    return json.dumps(payload, indent=2, sort_keys=True) + "\n"


def _jsonl_line(payload: dict[str, Any]) -> str:
    return json.dumps(payload, sort_keys=True) + "\n"


def _read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return payload if isinstance(payload, dict) else {}


def _read_jsonl(path: Path, limit: int | None = None) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError:
        return []
    if limit is not None:
        lines = lines[-limit:]
    records: list[dict[str, Any]] = []
    for line in lines:
        if not line.strip():
            continue
        try:
            payload = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(payload, dict):
            records.append(payload)
    return records


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(_json_dump(payload), encoding="utf-8")


def _write_jsonl(path: Path, records: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(_jsonl_line(record) for record in records), encoding="utf-8")


def _append_jsonl(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(_jsonl_line(payload))


def _safe_list(value: Any) -> list[Any]:
    if isinstance(value, list):
        return value
    if isinstance(value, tuple):
        return list(value)
    return []


def _safe_dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _int(value: Any, default: int = 0) -> int:
    if isinstance(value, bool):
        return default
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(value)
    if isinstance(value, str):
        try:
            return int(float(value))
        except ValueError:
            return default
    return default


def _hash_id(prefix: str, parts: Iterable[Any]) -> str:
    raw = "|".join(str(part) for part in parts)
    return f"{prefix}:{hashlib.sha256(raw.encode('utf-8')).hexdigest()[:20]}"


def _artifact_ref(filename: str, fragment: str | None = None) -> str:
    base = f"data/runtime/{filename}"
    return f"{base}#{fragment}" if fragment else base


def _authority() -> dict[str, Any]:
    return dict(AUTHORITY_FLAGS)


def _paths(settings: Settings | None = None) -> dict[str, Path]:
    runtime = _runtime_dir(settings)
    return {
        "primary": runtime / PRIMARY_ARTIFACT,
        "hypotheses": runtime / HYPOTHESES_ARTIFACT,
        "research_questions": runtime / RESEARCH_QUESTIONS_ARTIFACT,
        "market_mappings": runtime / MARKET_MAPPINGS_ARTIFACT,
        "dashboard_summary": runtime / DASHBOARD_SUMMARY_ARTIFACT,
        "events": runtime / EVENTS_ARTIFACT,
    }


def _load_context(settings: Settings | None = None) -> dict[str, Any]:
    runtime = _runtime_dir(settings)
    return {
        "runtime_dir": runtime,
        "source_universe": _read_json(runtime / SOURCE_UNIVERSE_ARTIFACT),
        "trading_universe": _read_json(runtime / TRADING_UNIVERSE_ARTIFACT),
        "evidence_contracts_summary": _read_json(runtime / EVIDENCE_CONTRACTS_SUMMARY_ARTIFACT),
        "source_evidence_contracts": _read_jsonl(runtime / SOURCE_EVIDENCE_CONTRACTS_ARTIFACT),
        "price_evidence_contracts": _read_jsonl(runtime / PRICE_EVIDENCE_CONTRACTS_ARTIFACT),
    }


def _source_contract_index(context: dict[str, Any]) -> dict[str, dict[str, Any]]:
    contracts = {}
    for contract in context.get("source_evidence_contracts", []):
        source_key = str(contract.get("subject", {}).get("source_key") or contract.get("source_record_id") or "")
        if source_key:
            contracts[source_key] = contract
    if contracts:
        return contracts
    for source in _safe_list(context.get("source_universe", {}).get("sources")):
        source_key = str(source.get("source_key") or "")
        if source_key:
            contracts[source_key] = {
                "source_record_id": source_key,
                "evidence_state": "fallback_from_source_universe",
                "subject": source,
                "missing_evidence": [],
            }
    return contracts


def _price_contracts_by_family(context: dict[str, Any]) -> dict[str, list[dict[str, Any]]]:
    by_family: dict[str, list[dict[str, Any]]] = {}
    for contract in context.get("price_evidence_contracts", []):
        family = str(contract.get("subject", {}).get("market_family") or "unknown")
        by_family.setdefault(family, []).append(contract)
    if by_family:
        return by_family
    for instrument in _safe_list(context.get("trading_universe", {}).get("instruments")):
        family = str(instrument.get("market_family") or "unknown")
        by_family.setdefault(family, []).append(
            {
                "source_record_id": instrument.get("symbol"),
                "evidence_state": "fallback_from_trading_universe",
                "subject": instrument,
                "missing_evidence": [],
            }
        )
    return by_family


def _market_family_matches(channel: str, family: str) -> bool:
    channel_norm = channel.lower().replace("-", "_")
    family_norm = family.lower().replace("-", "_")
    if channel_norm == family_norm:
        return True
    aliases = {
        "equities": {"semiconductors", "defence", "macro_watchlist"},
        "rates": {"macro_watchlist"},
        "fx": {"macro_watchlist"},
        "crude_oil": {"crude_oil"},
        "defence": {"defence"},
        "semiconductors": {"semiconductors"},
        "prediction_markets": {"prediction_markets"},
        "silver": {"silver"},
    }
    return family_norm in aliases.get(channel_norm, set())


def _source_requirements(
    claim: dict[str, Any],
    source_index: dict[str, dict[str, Any]],
) -> list[dict[str, Any]]:
    requirements = []
    for requested in _safe_list(claim.get("live_sources_to_check")):
        requested_key = str(requested)
        source_key = SOURCE_ALIASES.get(requested_key, requested_key)
        contract = source_index.get(source_key, {})
        subject = _safe_dict(contract.get("subject"))
        missing = _safe_list(contract.get("missing_evidence"))
        requirements.append(
            {
                "requested_source": requested_key,
                "source_key": source_key,
                "available": bool(contract),
                "source_family": subject.get("source_family"),
                "freshness_status": subject.get("freshness_status"),
                "trust_score": subject.get("trust_score"),
                "evidence_contract_id": contract.get("contract_id"),
                "missing_evidence_count": len(missing),
                "source_quorum_credit_allowed": False,
                "world_model_can_satisfy_requirement_alone": False,
                "required_role": "observable_indicator_check_only",
            }
        )
    return requirements


def _market_mappings_for_claim(
    hypothesis_id: str,
    claim: dict[str, Any],
    price_by_family: dict[str, list[dict[str, Any]]],
    generated_at: str,
) -> list[dict[str, Any]]:
    mappings: list[dict[str, Any]] = []
    for channel in _safe_list(claim.get("market_channels")):
        matched_contracts = [
            contract
            for family, contracts in price_by_family.items()
            if _market_family_matches(str(channel), family)
            for contract in contracts
        ]
        if not matched_contracts:
            mappings.append(
                {
                    "schema_version": SCHEMA_VERSION,
                    "phase_id": PHASE_ID,
                    "mapping_id": _hash_id("qadam-world-market-map", [hypothesis_id, channel, "missing"]),
                    "hypothesis_id": hypothesis_id,
                    "market_channel": channel,
                    "mapping_state": "no_current_trading_universe_match",
                    "symbols": [],
                    "primary_symbol": None,
                    "paperable_symbol_count": 0,
                    "price_contract_refs": [],
                    "missing_market_mapping_reason": "No current trading-universe instrument matched this market channel.",
                    "generated_at": generated_at,
                    "paper_order_allowed": False,
                    "trade_candidate_creation_allowed": False,
                    "authority": _authority(),
                }
            )
            continue
        symbols = [
            str(contract.get("subject", {}).get("symbol") or contract.get("source_record_id"))
            for contract in matched_contracts
            if contract.get("subject", {}).get("symbol") or contract.get("source_record_id")
        ]
        paperable_symbols = [
            symbol for symbol, contract in zip(symbols, matched_contracts, strict=False)
            if contract.get("subject", {}).get("paper_route_available") is True
        ]
        mappings.append(
            {
                "schema_version": SCHEMA_VERSION,
                "phase_id": PHASE_ID,
                "mapping_id": _hash_id("qadam-world-market-map", [hypothesis_id, channel, symbols]),
                "hypothesis_id": hypothesis_id,
                "market_channel": channel,
                "mapping_state": "mapped_to_current_trading_universe",
                "symbols": symbols,
                "primary_symbol": paperable_symbols[0] if paperable_symbols else (symbols[0] if symbols else None),
                "paperable_symbol_count": len(paperable_symbols),
                "price_contract_refs": [
                    contract.get("contract_id") for contract in matched_contracts if contract.get("contract_id")
                ],
                "missing_market_mapping_reason": None,
                "generated_at": generated_at,
                "paper_order_allowed": False,
                "trade_candidate_creation_allowed": False,
                "authority": _authority(),
            }
        )
    return mappings


def _research_questions_for_hypothesis(hypothesis: dict[str, Any]) -> list[dict[str, Any]]:
    questions: list[dict[str, Any]] = []
    indicators = _safe_list(hypothesis.get("observable_indicators"))
    markets = _safe_list(hypothesis.get("affected_markets"))
    for index, indicator in enumerate(indicators[:4], start=1):
        market = markets[(index - 1) % len(markets)] if markets else "mapped_market"
        question = (
            f"If {indicator}, do {market} instruments move before, with, or after the source evidence "
            f"across {', '.join(hypothesis.get('expected_time_horizons', [])[:3])}?"
        )
        questions.append(
            {
                "schema_version": SCHEMA_VERSION,
                "phase_id": PHASE_ID,
                "research_question_id": _hash_id("qadam-world-question", [hypothesis["hypothesis_id"], index, question]),
                "hypothesis_id": hypothesis["hypothesis_id"],
                "question": question,
                "question_type": "source_price_test_prompt",
                "required_sources": [
                    item["source_key"] for item in _safe_list(hypothesis.get("source_requirements")) if item.get("available")
                ],
                "affected_market": market,
                "output_role": "research_question_only",
                "can_create_trade_candidate": False,
                "can_satisfy_source_quorum": False,
                "paper_order_allowed": False,
                "authority": _authority(),
            }
        )
    return questions


def _hypothesis_from_claim(
    claim: dict[str, Any],
    source_index: dict[str, dict[str, Any]],
    price_by_family: dict[str, list[dict[str, Any]]],
    generated_at: str,
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    claim_key = str(claim.get("key"))
    hypothesis_id = _hash_id("qadam-world-hypothesis", [claim_key, claim.get("claim"), claim.get("mechanism")])
    source_requirements = _source_requirements(claim, source_index)
    market_mappings = _market_mappings_for_claim(hypothesis_id, claim, price_by_family, generated_at)
    available_source_count = sum(1 for item in source_requirements if item.get("available"))
    missing_source_count = sum(1 for item in source_requirements if not item.get("available"))
    mapped_market_count = sum(1 for item in market_mappings if item.get("mapping_state") == "mapped_to_current_trading_universe")
    confidence = BASE_CONFIDENCE_BY_CLAIM.get(claim_key, 0.18)
    if missing_source_count:
        confidence = max(0.05, confidence - 0.03 * missing_source_count)
    if mapped_market_count:
        confidence = min(0.35, confidence + 0.01 * min(mapped_market_count, 3))
    hypothesis = {
        "schema_version": SCHEMA_VERSION,
        "phase_id": PHASE_ID,
        "hypothesis_id": hypothesis_id,
        "source_claim_key": claim_key,
        "source_path": claim.get("source_path"),
        "title": str(claim_key).replace("_", " ").title(),
        "hypothesis_text": claim.get("claim"),
        "hypothesis_role": "falsifiable_research_question_generator",
        "world_model_scope": "private_lens_or_context_only",
        "public_evidence_role": "not_public_evidence",
        "actors": _safe_list(claim.get("actors")),
        "mechanism": claim.get("mechanism"),
        "observable_indicators": _safe_list(claim.get("observable_signatures")),
        "affected_markets": _safe_list(claim.get("market_channels")),
        "expected_time_horizons": TIME_HORIZONS_BY_CLAIM.get(claim_key, ["1d", "5d", "20d"]),
        "source_requirements": source_requirements,
        "falsifiers": FALSIFIERS_BY_CLAIM.get(
            claim_key,
            ["Mapped markets and independent sources fail to confirm the mechanism across tested windows."],
        ),
        "confidence": {
            "score": round(confidence, 4),
            "label": "low_context_prior" if confidence < 0.25 else "provisional_context_prior",
            "confidence_can_increase_without_evidence": False,
            "confidence_cap_without_external_evidence": 0.35,
        },
        "bias_labels": BIAS_LABELS_BY_CLAIM.get(claim_key, ["worldview_prior_bias_risk"]),
        "market_mappings": [mapping["mapping_id"] for mapping in market_mappings],
        "available_source_requirement_count": available_source_count,
        "missing_source_requirement_count": missing_source_count,
        "mapped_market_count": mapped_market_count,
        "falsifiable": bool(claim.get("observable_signatures")) and bool(source_requirements) and bool(claim.get("market_channels")),
        "research_question_generation_allowed": True,
        "source_quorum_credit_allowed": False,
        "source_quorum_satisfied_by_world_model": False,
        "trade_candidate_creation_allowed": False,
        "trade_candidate_created": False,
        "paper_order_allowed": False,
        "broker_write_allowed": False,
        "live_capital_enabled": False,
        "proof_credit_allowed": False,
        "boundary": (
            "World-model hypothesis only. It can sharpen questions and define falsifiers, "
            "but cannot satisfy source quorum, create trade candidates, approve risk, "
            "route orders, write brokers, grant proof credit, or enable live capital."
        ),
        "generated_at": generated_at,
        "authority": _authority(),
        "lineage": {
            "world_model_claim_key": claim_key,
            "world_model_source_path": claim.get("source_path"),
            "world_model_summary_ref": _artifact_ref(PRIMARY_ARTIFACT),
            "evidence_contracts_summary_ref": _artifact_ref(EVIDENCE_CONTRACTS_SUMMARY_ARTIFACT),
        },
    }
    return hypothesis, market_mappings


def build_world_model_hypothesis_library(settings: Settings | None = None) -> WorldModelBundle:
    context = _load_context(settings)
    generated_at = _iso()
    source_index = _source_contract_index(context)
    price_by_family = _price_contracts_by_family(context)
    source_summary = world_model_summary()
    hypotheses: list[dict[str, Any]] = []
    market_mappings: list[dict[str, Any]] = []
    research_questions: list[dict[str, Any]] = []
    for claim in world_model_claims():
        hypothesis, mappings = _hypothesis_from_claim(claim, source_index, price_by_family, generated_at)
        hypotheses.append(hypothesis)
        market_mappings.extend(mappings)
        research_questions.extend(_research_questions_for_hypothesis(hypothesis))
    market_mapping_state_counts = Counter(mapping["mapping_state"] for mapping in market_mappings)
    confidence_labels = Counter(hypothesis["confidence"]["label"] for hypothesis in hypotheses)
    bias_labels = Counter(
        label for hypothesis in hypotheses for label in _safe_list(hypothesis.get("bias_labels"))
    )
    status = "world_model_hypothesis_library_ready" if hypotheses and research_questions else "world_model_hypothesis_library_blocked"
    primary = {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "qadam_world_model_hypothesis_library",
        "phase_id": PHASE_ID,
        "generated_at": generated_at,
        "status": status,
        "source_world_model_status": source_summary.get("status"),
        "source_claim_count": source_summary.get("claim_count"),
        "hypothesis_count": len(hypotheses),
        "falsifiable_hypothesis_count": sum(1 for hypothesis in hypotheses if hypothesis.get("falsifiable") is True),
        "research_question_count": len(research_questions),
        "market_mapping_count": len(market_mappings),
        "market_mapping_state_counts": dict(market_mapping_state_counts),
        "confidence_label_counts": dict(confidence_labels),
        "bias_label_counts": dict(sorted(bias_labels.items())),
        "context_boundary": (
            "World-model hypotheses are context-only priors. They generate research "
            "questions and falsifiers, but cannot create source quorum, candidates, "
            "orders, broker writes, proof credit, or live-capital authority."
        ),
        "hypotheses": hypotheses,
        "dashboard_summary_ref": _artifact_ref(DASHBOARD_SUMMARY_ARTIFACT),
        "hypotheses_artifact_ref": _artifact_ref(HYPOTHESES_ARTIFACT),
        "research_questions_artifact_ref": _artifact_ref(RESEARCH_QUESTIONS_ARTIFACT),
        "market_mappings_artifact_ref": _artifact_ref(MARKET_MAPPINGS_ARTIFACT),
        "research_question_generation_allowed": True,
        "source_quorum_credit_allowed": False,
        "trade_candidate_creation_allowed": False,
        "trade_candidate_created_count": 0,
        "paper_order_created_count": 0,
        "broker_write_count": 0,
        "live_capital_enabled": False,
        "proof_credit_allowed": False,
        "authority": _authority(),
    }
    dashboard_summary = {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "qadam_world_model_dashboard_summary",
        "phase_id": PHASE_ID,
        "generated_at": generated_at,
        "status": status,
        "public_safe": True,
        "read_only": True,
        "paper_only": True,
        "command_disabled": True,
        "hypothesis_count": len(hypotheses),
        "falsifiable_hypothesis_count": primary["falsifiable_hypothesis_count"],
        "research_question_count": len(research_questions),
        "market_mapping_count": len(market_mappings),
        "mapped_market_count": market_mapping_state_counts.get("mapped_to_current_trading_universe", 0),
        "confidence_label_counts": dict(confidence_labels),
        "top_bias_labels": dict(bias_labels.most_common(8)),
        "message": (
            "Qadam has converted its world-model lens into falsifiable scenario "
            "hypotheses with actors, mechanisms, indicators, source requirements, "
            "falsifiers, confidence labels, and market mappings. These generate "
            "research questions only."
        ),
        "source_quorum_credit_allowed": False,
        "trade_candidate_creation_allowed": False,
        "trade_candidate_created_count": 0,
        "paper_order_created_count": 0,
        "broker_write_count": 0,
        "live_capital_enabled": False,
        "proof_credit_allowed": False,
        "authority": _authority(),
        "artifact_refs": {
            "primary": _artifact_ref(PRIMARY_ARTIFACT),
            "hypotheses": _artifact_ref(HYPOTHESES_ARTIFACT),
            "research_questions": _artifact_ref(RESEARCH_QUESTIONS_ARTIFACT),
            "market_mappings": _artifact_ref(MARKET_MAPPINGS_ARTIFACT),
            "evidence_contracts_summary": _artifact_ref(EVIDENCE_CONTRACTS_SUMMARY_ARTIFACT),
        },
    }
    return WorldModelBundle(
        primary=primary,
        hypotheses=hypotheses,
        research_questions=research_questions,
        market_mappings=market_mappings,
        dashboard_summary=dashboard_summary,
    )


def write_world_model_hypothesis_library(
    bundle: WorldModelBundle,
    settings: Settings | None = None,
) -> dict[str, str]:
    paths = _paths(settings)
    _write_json(paths["primary"], bundle.primary)
    _write_jsonl(paths["hypotheses"], bundle.hypotheses)
    _write_jsonl(paths["research_questions"], bundle.research_questions)
    _write_jsonl(paths["market_mappings"], bundle.market_mappings)
    _write_json(paths["dashboard_summary"], bundle.dashboard_summary)
    _append_jsonl(
        paths["events"],
        {
            "generated_at": bundle.primary["generated_at"],
            "event": "world_model_hypothesis_library_written",
            "status": bundle.primary["status"],
            "hypothesis_count": bundle.primary["hypothesis_count"],
            "research_question_count": bundle.primary["research_question_count"],
            "trade_candidate_created_count": bundle.primary["trade_candidate_created_count"],
        },
    )
    return {key: str(path) for key, path in paths.items()}


def build_and_write_world_model_hypothesis_library(
    settings: Settings | None = None,
) -> tuple[WorldModelBundle, dict[str, str], list[str]]:
    bundle = build_world_model_hypothesis_library(settings)
    written = write_world_model_hypothesis_library(bundle, settings)
    errors = validate_world_model_hypothesis_bundle(load_world_model_hypothesis_library(settings))
    return bundle, written, errors


def load_world_model_hypothesis_library(settings: Settings | None = None) -> dict[str, Any]:
    paths = _paths(settings)
    return {
        "primary": _read_json(paths["primary"]),
        "hypotheses": _read_jsonl(paths["hypotheses"]),
        "research_questions": _read_jsonl(paths["research_questions"]),
        "market_mappings": _read_jsonl(paths["market_mappings"]),
        "dashboard_summary": _read_json(paths["dashboard_summary"]),
    }


def _validate_authority(payload: dict[str, Any], prefix: str) -> list[str]:
    errors: list[str] = []
    authority = _safe_dict(payload.get("authority"))
    for field in FORBIDDEN_TRUE_FIELDS:
        if payload.get(field) is True:
            errors.append(f"{prefix}_forbidden_true:{field}")
        if authority.get(field) is True:
            errors.append(f"{prefix}_authority_forbidden_true:{field}")
    for field in FORBIDDEN_NONZERO_FIELDS:
        if _int(payload.get(field)) != 0 and field in payload:
            errors.append(f"{prefix}_forbidden_nonzero:{field}")
        if _int(authority.get(field)) != 0:
            errors.append(f"{prefix}_authority_forbidden_nonzero:{field}")
    return errors


def validate_world_model_hypothesis(hypothesis: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    required = {
        "schema_version",
        "phase_id",
        "hypothesis_id",
        "source_claim_key",
        "hypothesis_text",
        "actors",
        "mechanism",
        "observable_indicators",
        "affected_markets",
        "expected_time_horizons",
        "source_requirements",
        "falsifiers",
        "confidence",
        "bias_labels",
        "market_mappings",
        "research_question_generation_allowed",
        "source_quorum_credit_allowed",
        "trade_candidate_creation_allowed",
        "authority",
    }
    missing = required - set(hypothesis)
    errors.extend(f"hypothesis_missing_field:{field}" for field in sorted(missing))
    if hypothesis.get("schema_version") != SCHEMA_VERSION:
        errors.append("hypothesis_schema_version_invalid")
    for field in ("actors", "observable_indicators", "affected_markets", "source_requirements", "falsifiers", "bias_labels"):
        if not _safe_list(hypothesis.get(field)):
            errors.append(f"hypothesis_{field}_empty:{hypothesis.get('hypothesis_id')}")
    if not _safe_dict(hypothesis.get("confidence")).get("label"):
        errors.append(f"hypothesis_confidence_label_missing:{hypothesis.get('hypothesis_id')}")
    if _safe_dict(hypothesis.get("confidence")).get("confidence_can_increase_without_evidence") is not False:
        errors.append(f"hypothesis_confidence_can_increase_without_evidence:{hypothesis.get('hypothesis_id')}")
    if hypothesis.get("research_question_generation_allowed") is not True:
        errors.append(f"hypothesis_research_question_generation_not_allowed:{hypothesis.get('hypothesis_id')}")
    if hypothesis.get("source_quorum_credit_allowed") is not False:
        errors.append(f"hypothesis_source_quorum_allowed:{hypothesis.get('hypothesis_id')}")
    if hypothesis.get("source_quorum_satisfied_by_world_model") is not False:
        errors.append(f"hypothesis_source_quorum_satisfied_by_world_model:{hypothesis.get('hypothesis_id')}")
    if hypothesis.get("trade_candidate_creation_allowed") is not False:
        errors.append(f"hypothesis_trade_candidate_creation_allowed:{hypothesis.get('hypothesis_id')}")
    errors.extend(_validate_authority(hypothesis, str(hypothesis.get("hypothesis_id") or "hypothesis")))
    return errors


def validate_world_model_hypothesis_bundle(bundle: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    primary = _safe_dict(bundle.get("primary"))
    hypotheses = _safe_list(bundle.get("hypotheses"))
    research_questions = _safe_list(bundle.get("research_questions"))
    market_mappings = _safe_list(bundle.get("market_mappings"))
    dashboard = _safe_dict(bundle.get("dashboard_summary"))
    if primary.get("schema_version") != SCHEMA_VERSION:
        errors.append("primary_schema_version_invalid")
    if primary.get("status") not in {"world_model_hypothesis_library_ready", "world_model_hypothesis_library_blocked"}:
        errors.append("primary_status_invalid")
    if _int(primary.get("hypothesis_count")) != len(hypotheses):
        errors.append("hypothesis_count_mismatch")
    if _int(primary.get("research_question_count")) != len(research_questions):
        errors.append("research_question_count_mismatch")
    if _int(primary.get("market_mapping_count")) != len(market_mappings):
        errors.append("market_mapping_count_mismatch")
    if not hypotheses:
        errors.append("hypotheses_missing")
    if not research_questions:
        errors.append("research_questions_missing")
    for hypothesis in hypotheses:
        errors.extend(validate_world_model_hypothesis(hypothesis))
    hypothesis_ids = {str(hypothesis.get("hypothesis_id")) for hypothesis in hypotheses}
    for question in research_questions:
        if question.get("hypothesis_id") not in hypothesis_ids:
            errors.append(f"research_question_orphaned:{question.get('research_question_id')}")
        if question.get("can_create_trade_candidate") is not False:
            errors.append(f"research_question_trade_candidate_allowed:{question.get('research_question_id')}")
        if question.get("can_satisfy_source_quorum") is not False:
            errors.append(f"research_question_source_quorum_allowed:{question.get('research_question_id')}")
        errors.extend(_validate_authority(question, str(question.get("research_question_id") or "question")))
    for mapping in market_mappings:
        if mapping.get("hypothesis_id") not in hypothesis_ids:
            errors.append(f"market_mapping_orphaned:{mapping.get('mapping_id')}")
        if mapping.get("paper_order_allowed") is not False:
            errors.append(f"market_mapping_paper_order_allowed:{mapping.get('mapping_id')}")
        if mapping.get("trade_candidate_creation_allowed") is not False:
            errors.append(f"market_mapping_trade_candidate_allowed:{mapping.get('mapping_id')}")
        errors.extend(_validate_authority(mapping, str(mapping.get("mapping_id") or "mapping")))
    if dashboard.get("read_only") is not True or dashboard.get("command_disabled") is not True:
        errors.append("dashboard_boundary_invalid")
    for field in (
        "source_quorum_credit_allowed",
        "trade_candidate_creation_allowed",
        "live_capital_enabled",
        "proof_credit_allowed",
    ):
        if primary.get(field) is not False:
            errors.append(f"primary_forbidden_true:{field}")
        if dashboard.get(field) is not False:
            errors.append(f"dashboard_forbidden_true:{field}")
    for field in ("trade_candidate_created_count", "paper_order_created_count", "broker_write_count"):
        if _int(primary.get(field)) != 0:
            errors.append(f"primary_forbidden_nonzero:{field}")
        if _int(dashboard.get(field)) != 0:
            errors.append(f"dashboard_forbidden_nonzero:{field}")
    errors.extend(_validate_authority(primary, "primary"))
    errors.extend(_validate_authority(dashboard, "dashboard"))
    return sorted(set(errors))


def validate_negative_world_model_hypothesis_probes(settings: Settings | None = None) -> list[str]:
    bundle = load_world_model_hypothesis_library(settings)
    errors: list[str] = []
    if not bundle.get("primary"):
        return ["negative_probe_skipped_missing_world_model_library"]
    quorum_probe = json.loads(json.dumps(bundle))
    if quorum_probe.get("hypotheses"):
        quorum_probe["hypotheses"][0]["source_quorum_credit_allowed"] = True
        if not any("source_quorum_allowed" in error for error in validate_world_model_hypothesis_bundle(quorum_probe)):
            errors.append("negative_probe_failed_for_hypothesis_source_quorum")
    candidate_probe = json.loads(json.dumps(bundle))
    candidate_probe["primary"]["trade_candidate_created_count"] = 1
    if not any("trade_candidate_created_count" in error for error in validate_world_model_hypothesis_bundle(candidate_probe)):
        errors.append("negative_probe_failed_for_trade_candidate_count")
    question_probe = json.loads(json.dumps(bundle))
    if question_probe.get("research_questions"):
        question_probe["research_questions"][0]["can_create_trade_candidate"] = True
        if not any("research_question_trade_candidate_allowed" in error for error in validate_world_model_hypothesis_bundle(question_probe)):
            errors.append("negative_probe_failed_for_question_candidate_authority")
    authority_probe = json.loads(json.dumps(bundle))
    if authority_probe.get("market_mappings"):
        authority_probe["market_mappings"][0]["authority"]["paper_order_allowed"] = True
        if not any("paper_order_allowed" in error for error in validate_world_model_hypothesis_bundle(authority_probe)):
            errors.append("negative_probe_failed_for_mapping_paper_order_authority")
    return errors
