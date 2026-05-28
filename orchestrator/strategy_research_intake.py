"""Strategy research intake for external trading notes.

This module turns rough strategy notes into structured decision-engine context.
It does not approve a strategy, create a signal, create a trade candidate, hand
off to Risk Agent, stage orders, call brokers, or enable live capital.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Any

from orchestrator.config import Settings
from orchestrator.event_log import EventLog
from orchestrator.telegram_inbound_intake import TelegramInboundIntakeStore


STRATEGY_RESEARCH_INTAKE_SCHEMA_VERSION = 1
STRATEGY_RESEARCH_INTAKE_RUNTIME_ARTIFACT = "strategy_research_intake.json"
STRATEGY_RESEARCH_INTAKE_HISTORY = "strategy_research_intake_history.jsonl"
STRATEGY_RESEARCH_INTAKE_EVENT_LOG = "strategy_research_intake_events.jsonl"
STRATEGY_RESEARCH_INTAKE_EVENT_TYPE = "strategy_research_intake_recorded"
STRATEGY_RESEARCH_INTAKE_COMPONENT = "strategy_research_intake"

SOURCE_NOTE_REF = "docs/qadam-trading-strategy-research-notes.md"

AUTHORITY_FIELDS: tuple[str, ...] = (
    "signal_authority",
    "signal_confidence_authority",
    "trade_candidate_creation_allowed",
    "risk_handoff_allowed",
    "risk_approval_authority",
    "execution_policy_handoff_allowed",
    "execution_authority",
    "paper_order_authority",
    "staged_paper_order_authority",
    "broker_write_authority",
    "paper_submit_authority",
    "fill_confirmation_authority",
    "receipt_evidence_authority",
    "reconciliation_truth_authority",
    "live_capital_authority",
    "quantum_provider_call_allowed",
    "quantum_hardware_submission_allowed",
    "scheduler_enabled",
    "policy_mutation_allowed",
    "strategy_mutation_allowed",
)

STRATEGY_RESEARCH_BOUNDARY = (
    "Strategy research intake is decision context only. It can seed Strategy "
    "Lead challenges, Phase 4 strategy-family annotations, backtest requests, "
    "and PaperOps candidate tracking, but it cannot create signals, trade "
    "candidates, risk approvals, execution approvals, staged paper orders, "
    "broker writes, Q-CTRL/provider calls, policy mutations, strategy mutations, "
    "or live-capital authority."
)


@dataclass(frozen=True)
class ResearchStrategyCandidate:
    candidate_key: str
    name: str
    status: str
    qadam_role: str
    source_note_ref: str
    qadam_family_links: tuple[str, ...]
    instrument_scope: tuple[str, ...]
    data_requirements: tuple[str, ...]
    entry_rule_summary: str
    exit_rule_summary: str
    sizing_rule_summary: str
    validation_requirements: tuple[str, ...]
    paperops_readiness: str
    decision_engine_use: tuple[str, ...]
    strategy_lead_challenges: tuple[str, ...]
    blockers: tuple[str, ...]
    authority_flags: dict[str, bool]
    signal_authority: bool
    trade_candidate_creation_allowed: bool
    risk_handoff_allowed: bool
    execution_allowed: bool
    paper_order_allowed: bool
    broker_write_allowed: bool
    live_capital_enabled: bool
    boundary: str

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["qadam_family_links"] = list(self.qadam_family_links)
        payload["instrument_scope"] = list(self.instrument_scope)
        payload["data_requirements"] = list(self.data_requirements)
        payload["validation_requirements"] = list(self.validation_requirements)
        payload["decision_engine_use"] = list(self.decision_engine_use)
        payload["strategy_lead_challenges"] = list(self.strategy_lead_challenges)
        payload["blockers"] = list(self.blockers)
        return payload


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _runtime_dir(settings: Settings | None = None) -> Path:
    return Path((settings or Settings.from_env()).runtime_dir)


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def _authority_defaults() -> dict[str, bool]:
    return {field: False for field in AUTHORITY_FIELDS}


def strategy_research_intake_paths(settings: Settings | None = None) -> tuple[Path, Path, Path]:
    runtime = _runtime_dir(settings)
    return (
        runtime / STRATEGY_RESEARCH_INTAKE_RUNTIME_ARTIFACT,
        runtime / STRATEGY_RESEARCH_INTAKE_HISTORY,
        runtime / STRATEGY_RESEARCH_INTAKE_EVENT_LOG,
    )


def _candidate(
    *,
    candidate_key: str,
    name: str,
    status: str,
    qadam_role: str,
    qadam_family_links: tuple[str, ...],
    instrument_scope: tuple[str, ...],
    data_requirements: tuple[str, ...],
    entry_rule_summary: str,
    exit_rule_summary: str,
    sizing_rule_summary: str,
    validation_requirements: tuple[str, ...],
    paperops_readiness: str,
    decision_engine_use: tuple[str, ...],
    strategy_lead_challenges: tuple[str, ...],
    blockers: tuple[str, ...],
) -> ResearchStrategyCandidate:
    return ResearchStrategyCandidate(
        candidate_key=candidate_key,
        name=name,
        status=status,
        qadam_role=qadam_role,
        source_note_ref=SOURCE_NOTE_REF,
        qadam_family_links=qadam_family_links,
        instrument_scope=instrument_scope,
        data_requirements=data_requirements,
        entry_rule_summary=entry_rule_summary,
        exit_rule_summary=exit_rule_summary,
        sizing_rule_summary=sizing_rule_summary,
        validation_requirements=validation_requirements,
        paperops_readiness=paperops_readiness,
        decision_engine_use=decision_engine_use,
        strategy_lead_challenges=strategy_lead_challenges,
        blockers=blockers,
        authority_flags=_authority_defaults(),
        signal_authority=False,
        trade_candidate_creation_allowed=False,
        risk_handoff_allowed=False,
        execution_allowed=False,
        paper_order_allowed=False,
        broker_write_allowed=False,
        live_capital_enabled=False,
        boundary=STRATEGY_RESEARCH_BOUNDARY,
    )


def _research_candidates() -> tuple[ResearchStrategyCandidate, ...]:
    return (
        _candidate(
            candidate_key="pead_long_only_concordant",
            name="Post-Earnings Announcement Drift - Long-Only Concordant",
            status="research_candidate_data_required",
            qadam_role="event_driven_equity_strategy_candidate",
            qadam_family_links=(
                "semiconductor_policy_options_asymmetry",
                "defence_repricing_geopolitical_watch",
                "crude_oil_energy_security_disruption",
                "silver_macro_liquidity_stress",
            ),
            instrument_scope=("semiconductors", "defence_equities", "energy_equities", "miners", "etf_components"),
            data_requirements=(
                "earnings_announcement_date",
                "announcement_timing_flag",
                "actual_eps",
                "consensus_eps_before_announcement",
                "adjusted_price_reaction",
                "corporate_action_adjusted_daily_prices",
            ),
            entry_rule_summary=(
                "Enter long only when reported earnings beat consensus and the market reaction is positive "
                "after the full reaction window."
            ),
            exit_rule_summary="Time exit around 60 trading days unless a later Qadam risk policy overrides.",
            sizing_rule_summary="Start with capped fixed percentage or volatility-adjusted paper sizing.",
            validation_requirements=(
                "verify consensus estimate timestamp",
                "avoid announcement timing lookahead",
                "test large-cap, mid-cap, and small-cap universes separately",
                "compare concordant filter versus no concordant filter",
                "compare long-only versus long-short",
                "validate out of sample before PaperOps activation",
            ),
            paperops_readiness="blocked_pending_earnings_data_adapter",
            decision_engine_use=(
                "Strategy Lead challenge packet",
                "Phase 4 strategy-family annotation",
                "future PEAD backtest request",
                "PaperOps candidate once earnings data exists",
            ),
            strategy_lead_challenges=(
                "Is the earnings surprise timestamp clean enough to avoid lookahead?",
                "Does the long-only concordant filter beat a simple sector ETF baseline?",
                "Which Qadam families have enough earnings coverage to test this without selection bias?",
            ),
            blockers=("earnings_data_adapter_missing", "backtest_not_run", "paperops_not_approved"),
        ),
        _candidate(
            candidate_key="opening_range_breakout_vol_target",
            name="Opening Range Breakout With Volatility-Targeted Sizing",
            status="research_candidate_backtest_required",
            qadam_role="intraday_market_structure_candidate",
            qadam_family_links=(
                "crude_oil_energy_security_disruption",
                "silver_macro_liquidity_stress",
                "semiconductor_policy_options_asymmetry",
            ),
            instrument_scope=("QQQ", "SMH", "SOXX", "XLE", "USO", "SLV", "SPY"),
            data_requirements=(
                "intraday_bars",
                "regular_session_clock",
                "opening_range_high_low",
                "spread_and_slippage_assumptions",
                "paper_tradable_symbol_mapping",
            ),
            entry_rule_summary="Enter long when price closes above the first 30-minute opening range high.",
            exit_rule_summary="Use opening range low as stop, 1R target, and same-session time exit.",
            sizing_rule_summary="Risk a fixed paper amount per trade by scaling size to opening-range width.",
            validation_requirements=(
                "test with and without volume delta",
                "compare fixed size versus volatility-targeted size",
                "split pre-2020 and post-2020 regimes",
                "include realistic slippage and spread",
                "reject if performance is only broad bull-market beta",
            ),
            paperops_readiness="candidate_for_intraday_backtest_scaffold",
            decision_engine_use=(
                "Strategy Lead challenge packet",
                "PaperOps intraday backtest candidate",
                "risk sizing rule candidate",
            ),
            strategy_lead_challenges=(
                "Does volatility-targeted sizing improve drawdown-adjusted return across both sample halves?",
                "Can the futures rule be translated cleanly to Alpaca-paper ETFs without changing the edge?",
                "Is volume delta redundant once the breakout candle is already observed?",
            ),
            blockers=("intraday_backtest_not_run", "instrument_translation_required", "paperops_not_approved"),
        ),
        _candidate(
            candidate_key="trend_following_baseline_control",
            name="Simple Trend-Following Baseline Control",
            status="benchmark_candidate_ready_for_scaffold",
            qadam_role="control_model_for_strategy_review",
            qadam_family_links=(
                "crude_oil_energy_security_disruption",
                "silver_macro_liquidity_stress",
                "semiconductor_policy_options_asymmetry",
                "defence_repricing_geopolitical_watch",
            ),
            instrument_scope=("Qadam_first_trading_universe_etf_proxies",),
            data_requirements=("daily_or_intraday_bars", "moving_average", "atr", "benchmark_return_series"),
            entry_rule_summary="Use a simple trend filter and breakout rule as a control model.",
            exit_rule_summary="Use ATR-based stop and trend/breakout exit rules.",
            sizing_rule_summary="Use fixed fractional paper risk per trade for comparability.",
            validation_requirements=(
                "run across every candidate instrument",
                "compare each proposed strategy against the baseline",
                "separate long and short legs",
                "check whether a few outlier winners dominate returns",
            ),
            paperops_readiness="benchmark_scaffold_candidate",
            decision_engine_use=(
                "Strategy Lead benchmark challenge",
                "Head of Quant ambiguity baseline",
                "Phase 6 shadow replay control",
            ),
            strategy_lead_challenges=(
                "Does the proposed strategy beat a simple trend-following baseline after costs?",
                "Is the signal adding value or merely recreating broad trend exposure?",
            ),
            blockers=("baseline_backtest_scaffold_not_built",),
        ),
        _candidate(
            candidate_key="volume_delta_dislocation",
            name="Volume-Delta Dislocation",
            status="blocked_missing_order_flow_data",
            qadam_role="future_microstructure_feature",
            qadam_family_links=(
                "semiconductor_policy_options_asymmetry",
                "crude_oil_energy_security_disruption",
                "silver_macro_liquidity_stress",
            ),
            instrument_scope=("futures_or_order_flow_enabled_symbols",),
            data_requirements=(
                "bid_ask_trade_classification",
                "volume_delta_by_bar",
                "previous_session_levels",
                "exchange_specific_session_clock",
            ),
            entry_rule_summary=(
                "Observe a price/delta dislocation near a key level, such as price down while aggressive "
                "buying delta is positive."
            ),
            exit_rule_summary="Use fixed stop/target or same-session exit only after out-of-sample validation.",
            sizing_rule_summary="No sizing rule accepted until order-flow data semantics are verified.",
            validation_requirements=(
                "verify data source and delta semantics",
                "avoid TradingView versus broker calculation mismatch",
                "test thresholds out of sample",
                "check threshold transfer across instruments",
            ),
            paperops_readiness="blocked_until_order_flow_provider_exists",
            decision_engine_use=(
                "future Signal Integrity feature idea",
                "future Head of Quant ambiguity feature",
            ),
            strategy_lead_challenges=(
                "Do we have a reliable order-flow source with reproducible delta semantics?",
                "Does the dislocation remain predictive after threshold optimization is moved out of sample?",
            ),
            blockers=("order_flow_data_provider_missing", "backtest_not_run", "paperops_not_approved"),
        ),
    )


def _compact_candidates(candidates: tuple[ResearchStrategyCandidate, ...]) -> list[dict[str, Any]]:
    return [
        {
            "candidate_key": candidate.candidate_key,
            "name": candidate.name,
            "status": candidate.status,
            "qadam_role": candidate.qadam_role,
            "qadam_family_links": list(candidate.qadam_family_links),
            "paperops_readiness": candidate.paperops_readiness,
            "strategy_lead_challenges": list(candidate.strategy_lead_challenges),
            "blockers": list(candidate.blockers),
            "trade_candidate_creation_allowed": False,
            "risk_handoff_allowed": False,
            "execution_allowed": False,
            "paper_order_allowed": False,
            "broker_write_allowed": False,
            "live_capital_enabled": False,
        }
        for candidate in candidates
    ]


def _telegram_strategy_considerations(settings: Settings) -> list[dict[str, Any]]:
    rows = TelegramInboundIntakeStore(settings=settings).read_strategy_considerations(limit=20)
    considerations: list[dict[str, Any]] = []
    for row in rows:
        considerations.append(
            {
                "consideration_id": str(row.get("consideration_id") or "")[:160],
                "summary": str(row.get("summary") or "")[:500],
                "topic_tags": list(row.get("topic_tags") or [])[:8],
                "observed_at": str(row.get("observed_at") or ""),
                "strategy_lead_context_allowed": row.get("strategy_lead_context_allowed") is True,
                "trade_candidate_creation_allowed": False,
                "risk_handoff_allowed": False,
                "execution_allowed": False,
                "paper_order_allowed": False,
                "broker_write_allowed": False,
                "live_capital_enabled": False,
            }
        )
    return considerations


def _decision_context(
    candidates: tuple[ResearchStrategyCandidate, ...],
    telegram_considerations: list[dict[str, Any]],
) -> dict[str, Any]:
    challenge_rows = [
        {
            "candidate_key": candidate.candidate_key,
            "challenge": challenge,
        }
        for candidate in candidates
        for challenge in candidate.strategy_lead_challenges
    ]
    member_challenges = [
        {
            "candidate_key": "telegram_member_strategy_consideration",
            "consideration_id": row["consideration_id"],
            "challenge": (
                "Does this member-submitted strategy consideration survive "
                "source corroboration, backtest, paper sizing, and risk-policy review?"
            ),
        }
        for row in telegram_considerations
    ]
    return {
        "status": "ready_for_strategy_review",
        "context_role": "strategy_research_challenge_context",
        "source_note_ref": SOURCE_NOTE_REF,
        "candidate_count": len(candidates),
        "telegram_strategy_consideration_count": len(telegram_considerations),
        "telegram_strategy_considerations": telegram_considerations,
        "active_decision_candidate_count": 0,
        "best_initial_research_candidate": "pead_long_only_concordant",
        "benchmark_candidate": "trend_following_baseline_control",
        "candidate_refs": [candidate.candidate_key for candidate in candidates],
        "strategy_lead_challenge_count": len(challenge_rows) + len(member_challenges),
        "strategy_lead_challenges": (challenge_rows + member_challenges)[:16],
        "paperops_candidate_count": sum(
            1 for candidate in candidates if "blocked" not in candidate.paperops_readiness
        ),
        "blocked_candidate_count": sum(1 for candidate in candidates if candidate.blockers),
        "trade_candidate_creation_allowed": False,
        "risk_handoff_allowed": False,
        "execution_allowed": False,
        "paper_order_allowed": False,
        "broker_write_allowed": False,
        "live_capital_enabled": False,
        "boundary": STRATEGY_RESEARCH_BOUNDARY,
    }


def build_strategy_research_intake(settings: Settings | None = None) -> dict[str, Any]:
    settings = settings or Settings.from_env()
    candidates = _research_candidates()
    telegram_considerations = _telegram_strategy_considerations(settings)
    source_note_exists = (_repo_root() / SOURCE_NOTE_REF).exists()
    candidate_rows = [candidate.to_dict() for candidate in candidates]
    artifact = {
        "schema_version": STRATEGY_RESEARCH_INTAKE_SCHEMA_VERSION,
        "artifact_type": "strategy_research_intake",
        "artifact_id": "strategy-research:intake:external-notes",
        "status": "ready_for_strategy_review" if source_note_exists else "degraded_missing_source_note",
        "generated_at": _now(),
        "public_safe": True,
        "recorded": False,
        "event_log_required": True,
        "event_log_written": False,
        "event_log_path": None,
        "event_log_event_count": 0,
        "runtime_artifact_path": None,
        "history_log_path": None,
        "source_note_ref": SOURCE_NOTE_REF,
        "source_note_exists": source_note_exists,
        "candidate_count": len(candidates),
        "candidate_records": candidate_rows,
        "compact_candidates": _compact_candidates(candidates),
        "user_strategy_consideration_count": len(telegram_considerations),
        "user_strategy_considerations": telegram_considerations,
        "decision_engine_context": _decision_context(candidates, telegram_considerations),
        "strategy_lead_context_allowed": True,
        "phase4_candidate_annotation_allowed": True,
        "paperops_backtest_request_allowed": True,
        "phase7_qualified_setup_allowed": False,
        "phase7_proof_credit_allowed": False,
        "trade_candidate_creation_allowed": False,
        "risk_handoff_allowed": False,
        "execution_allowed": False,
        "paper_order_allowed": False,
        "broker_write_allowed": False,
        "live_capital_enabled": False,
        "authority_flags": _authority_defaults(),
        "boundary": STRATEGY_RESEARCH_BOUNDARY,
    }
    artifact["validation_errors"] = validate_strategy_research_intake(artifact)
    if artifact["validation_errors"]:
        artifact["status"] = "error"
    return artifact


def validate_strategy_research_intake(artifact: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if artifact.get("schema_version") != STRATEGY_RESEARCH_INTAKE_SCHEMA_VERSION:
        errors.append("strategy_research_schema_version_mismatch")
    if artifact.get("artifact_type") != "strategy_research_intake":
        errors.append("strategy_research_artifact_type_invalid")
    if artifact.get("public_safe") is not True:
        errors.append("strategy_research_not_public_safe")
    if not artifact.get("source_note_exists"):
        errors.append("strategy_research_source_note_missing")
    candidates = artifact.get("candidate_records", [])
    if not isinstance(candidates, list) or len(candidates) != 4:
        errors.append("strategy_research_candidate_count_invalid")
        candidates = []
    if artifact.get("candidate_count") != len(candidates):
        errors.append("strategy_research_candidate_count_mismatch")
    telegram_considerations = artifact.get("user_strategy_considerations", [])
    if not isinstance(telegram_considerations, list):
        errors.append("strategy_research_user_considerations_invalid")
        telegram_considerations = []
    if artifact.get("user_strategy_consideration_count") != len(telegram_considerations):
        errors.append("strategy_research_user_consideration_count_mismatch")
    for row in telegram_considerations:
        if not isinstance(row, dict):
            errors.append("strategy_research_user_consideration_row_invalid")
            continue
        if row.get("strategy_lead_context_allowed") is not True:
            errors.append("strategy_research_user_consideration_not_allowed_for_context")
        for field in (
            "trade_candidate_creation_allowed",
            "risk_handoff_allowed",
            "execution_allowed",
            "paper_order_allowed",
            "broker_write_allowed",
            "live_capital_enabled",
        ):
            if row.get(field) is not False:
                errors.append(f"strategy_research_user_consideration_authority_enabled:{field}")
    required_candidate_fields = {
        "candidate_key",
        "name",
        "status",
        "qadam_role",
        "source_note_ref",
        "qadam_family_links",
        "instrument_scope",
        "data_requirements",
        "entry_rule_summary",
        "exit_rule_summary",
        "sizing_rule_summary",
        "validation_requirements",
        "paperops_readiness",
        "decision_engine_use",
        "strategy_lead_challenges",
        "blockers",
        "authority_flags",
        "signal_authority",
        "trade_candidate_creation_allowed",
        "risk_handoff_allowed",
        "execution_allowed",
        "paper_order_allowed",
        "broker_write_allowed",
        "live_capital_enabled",
        "boundary",
    }
    seen_keys: set[str] = set()
    for candidate in candidates:
        if not isinstance(candidate, dict):
            errors.append("strategy_research_candidate_invalid")
            continue
        candidate_key = str(candidate.get("candidate_key") or "unknown")
        if candidate_key in seen_keys:
            errors.append(f"strategy_research_duplicate_candidate:{candidate_key}")
        seen_keys.add(candidate_key)
        missing = sorted(required_candidate_fields - set(candidate))
        if missing:
            errors.append(f"strategy_research_candidate_fields_missing:{candidate_key}:{','.join(missing)}")
        for field in (
            "qadam_family_links",
            "instrument_scope",
            "data_requirements",
            "validation_requirements",
            "decision_engine_use",
            "strategy_lead_challenges",
        ):
            if not candidate.get(field):
                errors.append(f"strategy_research_candidate_required_list_empty:{candidate_key}:{field}")
        for field in (
            "signal_authority",
            "trade_candidate_creation_allowed",
            "risk_handoff_allowed",
            "execution_allowed",
            "paper_order_allowed",
            "broker_write_allowed",
            "live_capital_enabled",
        ):
            if candidate.get(field) is not False:
                errors.append(f"strategy_research_candidate_authority_enabled:{candidate_key}:{field}")
        flags = candidate.get("authority_flags", {})
        if not isinstance(flags, dict):
            errors.append(f"strategy_research_candidate_authority_flags_missing:{candidate_key}")
        else:
            for field in AUTHORITY_FIELDS:
                if flags.get(field) is not False:
                    errors.append(f"strategy_research_candidate_authority_flag_enabled:{candidate_key}:{field}")
    context = artifact.get("decision_engine_context", {})
    if not isinstance(context, dict):
        errors.append("strategy_research_decision_context_missing")
    else:
        if context.get("status") != "ready_for_strategy_review":
            errors.append("strategy_research_decision_context_status_invalid")
        if context.get("context_role") != "strategy_research_challenge_context":
            errors.append("strategy_research_decision_context_role_invalid")
        if int(context.get("active_decision_candidate_count", 0) or 0) != 0:
            errors.append("strategy_research_active_decision_candidate_nonzero")
        if int(context.get("strategy_lead_challenge_count", 0) or 0) < 4:
            errors.append("strategy_research_strategy_lead_challenges_missing")
        if int(context.get("telegram_strategy_consideration_count", 0) or 0) != len(
            telegram_considerations
        ):
            errors.append("strategy_research_context_telegram_consideration_count_mismatch")
        for field in (
            "trade_candidate_creation_allowed",
            "risk_handoff_allowed",
            "execution_allowed",
            "paper_order_allowed",
            "broker_write_allowed",
            "live_capital_enabled",
        ):
            if context.get(field) is not False:
                errors.append(f"strategy_research_decision_context_authority_enabled:{field}")
    for field in (
        "phase7_qualified_setup_allowed",
        "phase7_proof_credit_allowed",
        "trade_candidate_creation_allowed",
        "risk_handoff_allowed",
        "execution_allowed",
        "paper_order_allowed",
        "broker_write_allowed",
        "live_capital_enabled",
    ):
        if artifact.get(field) is not False:
            errors.append(f"strategy_research_artifact_authority_enabled:{field}")
    flags = artifact.get("authority_flags", {})
    if not isinstance(flags, dict):
        errors.append("strategy_research_authority_flags_missing")
    else:
        for field in AUTHORITY_FIELDS:
            if flags.get(field) is not False:
                errors.append(f"strategy_research_authority_flag_enabled:{field}")
    if "decision context only" not in str(artifact.get("boundary") or ""):
        errors.append("strategy_research_boundary_weak")
    return errors


def write_strategy_research_intake(
    artifact: dict[str, Any],
    settings: Settings | None = None,
    *,
    record_event: bool = True,
) -> tuple[Path, Path, Path, dict[str, Any]]:
    settings = settings or Settings.from_env()
    output_path, history_path, event_path = strategy_research_intake_paths(settings)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    written = dict(artifact)
    written["recorded"] = True
    written["runtime_artifact_path"] = str(output_path)
    written["history_log_path"] = str(history_path)
    if record_event:
        if event_path.exists():
            event_path.unlink()
        event = EventLog(event_path, echo=False).write(
            STRATEGY_RESEARCH_INTAKE_EVENT_TYPE,
            STRATEGY_RESEARCH_INTAKE_COMPONENT,
            payload={
                "status": written["status"],
                "candidate_count": written["candidate_count"],
                "user_strategy_consideration_count": written["user_strategy_consideration_count"],
                "strategy_lead_challenge_count": written["decision_engine_context"][
                    "strategy_lead_challenge_count"
                ],
                "trade_candidate_creation_allowed": False,
                "execution_allowed": False,
                "paper_order_allowed": False,
            },
        )
        written["event_log_written"] = True
        written["event_log_path"] = str(event_path)
        written["event_log_event_count"] = 1
        written["event_log_correlation_id"] = event.correlation_id
        written["event_log_created_at"] = event.created_at
    output_path.write_text(json.dumps(written, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    with history_path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(written, sort_keys=True) + "\n")
    return output_path, history_path, event_path, written


def strategy_research_decision_context(settings: Settings | None = None) -> dict[str, Any]:
    artifact = build_strategy_research_intake(settings)
    return artifact["decision_engine_context"]
