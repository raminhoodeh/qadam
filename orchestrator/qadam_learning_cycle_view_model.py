"""Canonical Results & Lessons projection for Qadam's learning loop.

The projection joins postmortems, attribution, proof, performance, and the
human learning brief. It is read-only: records can explain lessons and propose
tests, but they cannot mutate policy or create trading authority.
"""

from __future__ import annotations

from collections import Counter
from typing import Any

from orchestrator.config import Settings
from orchestrator.qadam_canonical_contracts import AtomicArtifactStore
from orchestrator.qadam_learning_loop_contract import (
    build_learning_loop_overview,
    validate_learning_loop_overview,
)
from orchestrator.qadam_operator_ready_common import (
    authority_flags,
    now_iso,
    read_json,
    read_jsonl,
    runtime_dir,
    unique_errors,
    validate_authority,
)

SCHEMA_VERSION = "qadam_learning_cycle_dashboard.v2"
PHASE_ID = "LI-1"

LEARNING_CYCLE_ARTIFACT = "qadam_learning_cycle_dashboard.json"
LEARNING_CYCLE_EVENTS_ARTIFACT = "qadam_learning_cycle_events.jsonl"
CHECK_ARTIFACT = "qadam_learning_cycle_checks.json"

POSTMORTEMS_ARTIFACT = "qadam_paper_postmortems_v3.jsonl"
ATTRIBUTION_ARTIFACT = "qadam_learning_attribution_v3.jsonl"
PROOF_ARTIFACT = "qadam_paper_proof_eligibility.json"
PERFORMANCE_ARTIFACT = "qadam_paper_performance_summary.json"
DAILY_BRIEF_ARTIFACT = "daily_telegram_learning_brief.json"
BACKFILL_ARTIFACT = "qadam_backfill_coverage.json"
BACKTEST_ARTIFACT = "qadam_backtest_results_summary.json"
SHADOW_STATE_ARTIFACT = "qadam_forward_shadow_state.json"


def _human(value: Any, fallback: str = "Not recorded") -> str:
    text = str(value or "").strip()
    if not text:
        return fallback
    return text.replace("_", " ").replace("-", " ").strip().capitalize()


def _is_qadam_origin(value: Any) -> bool:
    return str(value or "").startswith("qadam_origin")


def _postmortem_index(records: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    return {
        str(record.get("lineage_record_id")): record
        for record in records
        if record.get("lineage_record_id")
    }


def _event_kind(outcome_type: str) -> str:
    token = outcome_type.lower()
    if "mirror" in token:
        return "paper_outcome"
    if "hypothesis_rejected" in token:
        return "veto"
    if "release_blocked" in token or "system" in token:
        return "system_defect"
    if "shadow" in token:
        return "shadow"
    if "backtest" in token:
        return "backtest"
    if "missed" in token:
        return "missed_opportunity"
    if "hold" in token:
        return "hold"
    return "paper_outcome"


def _event_from_attribution(
    record: dict[str, Any],
    postmortem: dict[str, Any],
) -> dict[str, Any]:
    origin = str(record.get("origin_class") or postmortem.get("origin_class") or "unknown")
    outcome_type = str(record.get("outcome_type") or "unknown")
    champion = record.get("champion_challenger")
    champion = champion if isinstance(champion, dict) else {}
    metrics = record.get("outcome_metrics")
    metrics = metrics if isinstance(metrics, dict) else {}
    lineage = record.get("lineage")
    lineage = lineage if isinstance(lineage, dict) else {}
    qadam_origin = _is_qadam_origin(origin)
    postmortem_learnable = postmortem.get("learning_attribution_allowed") is True
    research_event = origin == "qadam_runtime"
    learnable = bool(postmortem_learnable or research_event)
    reason = str(champion.get("reason") or "No supported lesson was recorded.")
    proposal_type = str(champion.get("proposal_type") or "no_test_proposed")
    return {
        "record_id": str(record.get("attribution_id") or record.get("source_record_id") or "unknown"),
        "generated_at": record.get("generated_at") or postmortem.get("generated_at"),
        "record_kind": _event_kind(outcome_type),
        "outcome_type": outcome_type,
        "origin_class": origin,
        "qadam_origin": qadam_origin,
        "learnable": learnable,
        "reference_only": not learnable,
        "lineage": lineage,
        "expectation": {
            "summary": postmortem.get("entry_thesis") or "No Qadam thesis is attached to this record.",
            "measurable": bool(postmortem.get("entry_thesis")),
        },
        "actual_outcome": {
            "summary": _human(outcome_type),
            "exit_reason": postmortem.get("exit_reason") or metrics.get("exit_reason"),
            "realized_net_pnl": metrics.get("realized_net_pnl"),
            "currency": metrics.get("currency"),
            "holding_period_seconds": metrics.get("holding_period_seconds"),
            "maximum_adverse_excursion": metrics.get("maximum_adverse_excursion"),
            "maximum_favourable_excursion": metrics.get("maximum_favourable_excursion"),
            "metrics_missing": metrics.get("metrics_missing") or [],
        },
        "component_attribution": record.get("component_attribution") or {},
        "lesson": {
            "summary": reason if learnable else "This reference record cannot measure Qadam's decision quality.",
            "supported": learnable,
            "what_worked": postmortem.get("what_worked"),
            "what_failed": postmortem.get("what_failed"),
        },
        "lesson_confidence": "weak" if learnable else "not_measurable",
        "next_test": {
            "proposal_type": proposal_type,
            "state": str(champion.get("state") or "not_proposed"),
            "route": {"module_id": "learn", "view_id": "improvements"},
        },
        "proof_eligible": record.get("proof_credit_granted") is True,
        "authority": authority_flags(),
    }


def _latest_brief(
    brief: dict[str, Any],
    *,
    qadam_outcome_count: int,
    reference_count: int,
    learnable_event_count: int,
    backfill: dict[str, Any],
    backtest: dict[str, Any],
    shadow: dict[str, Any],
) -> dict[str, Any]:
    if qadam_outcome_count == 0:
        summary = (
            "Qadam has not yet completed a paper trade it can use to judge its own decisions. "
            f"{reference_count} historical broker records remain reference-only."
        )
    else:
        summary = f"Qadam has {qadam_outcome_count} attributable paper outcomes available for review."
    completed_partitions = int(backfill.get("completed_partition_count", 0) or 0)
    total_partitions = int(backfill.get("total_partition_count", 0) or 0)
    attempted = int(backtest.get("attempted_hypothesis_count", 0) or 0)
    shadow_decisions = int(shadow.get("decision_count", 0) or 0)
    bullets = [
        (
            f"Strongest lesson: {learnable_event_count} Qadam research or operating events can support cautious follow-up; "
            "historical broker mirrors cannot."
        ),
        (
            f"Biggest uncertainty: provider history covers {completed_partitions} of {total_partitions} required data slices, "
            f"and {attempted} proposed relationships have entered a statistical test."
        ),
        (
            f"Next test: fill the eligible historical gaps, then watch qualifying ideas in real time without placing orders; "
            f"{shadow_decisions} no-order decisions exist now."
        ),
    ]
    return {
        "status": brief.get("status") or "not_exported",
        "generated_at": brief.get("generated_at"),
        "summary": summary,
        "bullets": bullets,
        "source_body": brief.get("body"),
        "message_safe": brief.get("message_safe") is True,
        "live_send_attempted": brief.get("live_send_attempted") is True,
        "live_send_succeeded": brief.get("live_send_succeeded") is True,
        "telegram_live_send_allowed": False,
        "telegram_command_path_enabled": False,
    }


def build_learning_cycle_view_model(
    settings: Settings | None = None,
    *,
    generated_at: str | None = None,
) -> dict[str, Any]:
    runtime = runtime_dir(settings)
    generated = generated_at or now_iso()
    postmortems = read_jsonl(runtime / POSTMORTEMS_ARTIFACT)
    attributions = read_jsonl(runtime / ATTRIBUTION_ARTIFACT)
    proof = read_json(runtime / PROOF_ARTIFACT)
    performance = read_json(runtime / PERFORMANCE_ARTIFACT)
    brief = read_json(runtime / DAILY_BRIEF_ARTIFACT)
    backfill = read_json(runtime / BACKFILL_ARTIFACT)
    backtest = read_json(runtime / BACKTEST_ARTIFACT)
    shadow = read_json(runtime / SHADOW_STATE_ARTIFACT)
    postmortems_by_lineage = _postmortem_index(postmortems)
    events = [
        _event_from_attribution(
            record,
            postmortems_by_lineage.get(str(record.get("source_record_id")), {}),
        )
        for record in attributions
    ]
    events.sort(key=lambda row: str(row.get("generated_at") or ""), reverse=True)
    reference_records = [record for record in events if record["reference_only"]]
    learnable_events = [record for record in events if record["learnable"]]
    qadam_postmortems = [
        record
        for record in postmortems
        if _is_qadam_origin(record.get("origin_class"))
        and record.get("learning_attribution_allowed") is True
    ]
    qadam_outcome_count = int(performance.get("qadam_origin_complete_trade_count", 0) or 0)
    kind_counts = Counter(str(record.get("record_kind")) for record in events)
    counts = {
        "attribution_record_count": len(events),
        "qadam_origin_outcome_count": qadam_outcome_count,
        "learnable_postmortem_count": len(qadam_postmortems),
        "learnable_event_count": len(learnable_events),
        "mirror_reference_count": len(reference_records),
        "proof_eligible_count": int(proof.get("proof_eligible_count", 0) or 0),
        "lesson_awaiting_test_count": len(
            [record for record in learnable_events if record["next_test"]["state"] not in {"rejected", "retired"}]
        ),
        "record_kind_counts": dict(sorted(kind_counts.items())),
    }
    status = "learning_waiting_for_qadam_outcomes" if not qadam_outcome_count else "learning_outcomes_available"
    return {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "qadam_learning_cycle_dashboard",
        "phase_id": PHASE_ID,
        "generated_at": generated,
        "status": status,
        "headline": "What Qadam Learned",
        "plain_english": (
            "Qadam compares what it expected with what actually happened, records only supported lessons, "
            "and sends each lesson to testing before any behavior can change."
        ),
        "loop_overview": build_learning_loop_overview("results"),
        "latest_brief": _latest_brief(
            brief,
            qadam_outcome_count=qadam_outcome_count,
            reference_count=len(reference_records),
            learnable_event_count=len(learnable_events),
            backfill=backfill,
            backtest=backtest,
            shadow=shadow,
        ),
        "counts": counts,
        "events": events,
        "learnable_outcomes": [record for record in events if record["qadam_origin"] and record["learnable"]],
        "learning_events": [record for record in learnable_events if not record["qadam_origin"]],
        "reference_records": reference_records,
        "performance": performance,
        "proof": proof,
        "communications": {
            "status": brief.get("status") or "not_exported",
            "draft_body": brief.get("body"),
            "live_send_attempted": brief.get("live_send_attempted") is True,
            "live_send_succeeded": brief.get("live_send_succeeded") is True,
            "delivery_retry_status": brief.get("delivery_retry_status"),
            "telegram_live_send_allowed": False,
            "telegram_command_path_enabled": False,
        },
        "public_safe": True,
        "read_only": True,
        "command_disabled": True,
        "paper_only": True,
        "authority": authority_flags(),
        "boundary": (
            "Results and lessons are read-only research evidence. Mirror-only records cannot measure Qadam, "
            "and no lesson can mutate policy, create an order, or grant proof credit."
        ),
    }


def validate_learning_cycle_view_model(model: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    events = model.get("events") if isinstance(model.get("events"), list) else []
    counts = model.get("counts") if isinstance(model.get("counts"), dict) else {}
    if counts.get("attribution_record_count") != len(events):
        errors.append("learning_cycle_attribution_count_mismatch")
    reference = [record for record in events if record.get("reference_only") is True]
    if counts.get("mirror_reference_count") != len(reference):
        errors.append("learning_cycle_reference_count_mismatch")
    if any(record.get("learnable") is not False for record in reference):
        errors.append("learning_cycle_reference_record_marked_learnable")
    if any(record.get("proof_eligible") is not False for record in reference):
        errors.append("learning_cycle_reference_record_granted_proof")
    learnable_outcomes = model.get("learnable_outcomes")
    learnable_outcomes = learnable_outcomes if isinstance(learnable_outcomes, list) else []
    if any(not _is_qadam_origin(record.get("origin_class")) for record in learnable_outcomes):
        errors.append("learning_cycle_non_qadam_outcome_marked_learnable")
    if model.get("public_safe") is not True or model.get("read_only") is not True:
        errors.append("learning_cycle_not_public_read_only")
    if model.get("command_disabled") is not True:
        errors.append("learning_cycle_command_path_enabled")
    errors.extend(validate_learning_loop_overview(model.get("loop_overview"), expected_page="results"))
    errors.extend(validate_authority(model.get("authority", {}), prefix="learning_cycle"))
    return unique_errors(errors)


def build_and_write_learning_cycle_view_model(
    settings: Settings | None = None,
) -> tuple[dict[str, Any], dict[str, Any], list[str]]:
    runtime = runtime_dir(settings)
    store = AtomicArtifactStore(runtime)
    model = build_learning_cycle_view_model(settings)
    errors = validate_learning_cycle_view_model(model)
    store.write_json(LEARNING_CYCLE_ARTIFACT, model)
    store.write_jsonl(LEARNING_CYCLE_EVENTS_ARTIFACT, model["events"])
    checks = {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "qadam_learning_cycle_checks",
        "phase_id": PHASE_ID,
        "generated_at": now_iso(),
        "status": "passed" if not errors else "blocked",
        "implementation_ready": not errors,
        **model["counts"],
        "mirror_records_are_reference_only": all(
            record.get("learnable") is False for record in model["reference_records"]
        ),
        "paper_order_created_count": 0,
        "broker_write_count": 0,
        "proof_credit_created_count": 0,
        "validation_error_count": len(errors),
        "validation_errors": errors,
        "authority": authority_flags(),
    }
    store.write_json(CHECK_ARTIFACT, checks)
    return model, checks, errors
