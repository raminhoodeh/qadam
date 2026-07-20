"""Canonical Results & Lessons projection for Qadam's learning loop.

The projection joins postmortems, attribution, proof, performance, and the
human learning brief. It is read-only: records can explain lessons and propose
tests, but they cannot mutate policy or create trading authority.
"""

from __future__ import annotations

from collections import Counter
import re
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
LEARNING_BACKTEST_GAP_ARTIFACT = "qadam_learning_backtest_dashboard_summary.json"

RESULTS_PRESENTATION_VERSION = "qadam_results_lessons.v2"
RESULTS_PAGE_COPY = {
    "eyebrow": "Performance Attribution & Governance",
    "title": "What Qadam Learned",
    "subtitle": (
        "Qadam's learning engine looks backward: Qadam separates its own attributable "
        "outcomes from reference history, compares expectation with reality, and "
        "records only lessons the evidence can support."
    ),
}
RESULTS_HANDOFF = {
    "label": "Continue to Tests & Improvements",
    "supporting_text": (
        "See whether a supported lesson survives testing, review, and version approval "
        "before it can change Qadam."
    ),
    "module_id": "learn",
    "view_id": "improvements",
}


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


def _integer_or_none(value: Any) -> int | None:
    if value is None or isinstance(value, bool):
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _dedupe_records(*groups: list[dict[str, Any]]) -> list[dict[str, Any]]:
    records: dict[str, dict[str, Any]] = {}
    for group in groups:
        for index, record in enumerate(group):
            if not isinstance(record, dict):
                continue
            key = str(record.get("record_id") or f"anonymous:{index}:{id(group)}")
            records.setdefault(key, record)
    return sorted(
        records.values(),
        key=lambda row: str(row.get("generated_at") or row.get("occurred_at") or ""),
        reverse=True,
    )


def _learning_review_projection(event: dict[str, Any]) -> dict[str, Any]:
    outcome_type = str(event.get("outcome_type") or "").lower()
    lesson = event.get("lesson") if isinstance(event.get("lesson"), dict) else {}
    actual = event.get("actual_outcome") if isinstance(event.get("actual_outcome"), dict) else {}
    next_test = event.get("next_test") if isinstance(event.get("next_test"), dict) else {}
    if outcome_type == "strategy_hypothesis_rejected":
        display_type = "Research review"
        title = "Research idea stopped before practical testing"
        happened = "A research relationship was stopped before it reached practical paper-trade testing."
        blocker = "The available historical evidence was not complete enough to justify advancing it."
        state = "Stopped after review"
        tone = "stopped"
    elif outcome_type == "operational_release_blocked":
        display_type = "Operating review"
        title = "Research cycle held while required evidence remained incomplete"
        happened = "The research cycle stayed in watch-only mode instead of changing Qadam's behavior."
        blocker = "Required evidence or approvals remained incomplete."
        state = "Held for evidence"
        tone = "pending"
    elif event.get("qadam_origin") is True:
        display_type = "Paper outcome review"
        title = "Paper outcome reviewed against its original expectation"
        happened = str(actual.get("summary") or "A Qadam paper outcome was recorded for review.")
        blocker = (
            "No unresolved attribution blocker is recorded."
            if event.get("proof_eligible") is True
            else "Complete research-to-execution evidence is still required before the lesson is verified."
        )
        state = "Verified lesson" if event.get("proof_eligible") is True else "Held for evidence"
        tone = "verified" if event.get("proof_eligible") is True else "pending"
    else:
        display_type = _human(event.get("record_kind"), "Learning review")
        title = _human(event.get("outcome_type"), "Learning record under review")
        happened = str(actual.get("summary") or "A research or operating event was recorded for review.")
        blocker = str(lesson.get("what_failed") or "The available evidence remains incomplete.")
        state = "Ready for testing" if lesson.get("supported") is True else "Held for evidence"
        tone = "ready" if lesson.get("supported") is True else "pending"
    supported_lesson = str(
        lesson.get("summary")
        or "The evidence does not yet support a stronger conclusion."
    )
    next_action = (
        "Keep the idea closed unless new independent evidence supports a new review."
        if str(next_test.get("state") or "").lower() in {"rejected", "retired"}
        else "Send the supported question to Tests & Improvements without changing current behavior."
    )
    return {
        "record_id": str(event.get("record_id") or "unknown"),
        "occurred_at": event.get("generated_at"),
        "display_type": display_type,
        "title": title,
        "what_happened": happened,
        "supported_lesson": supported_lesson,
        "blocker_or_hold_reason": blocker,
        "next_action": next_action,
        "state": state,
        "tone": tone,
        "proof_eligible": event.get("proof_eligible") is True,
        "source_origin": event.get("origin_class"),
    }


def _reference_record_projection(event: dict[str, Any]) -> dict[str, Any]:
    actual = event.get("actual_outcome") if isinstance(event.get("actual_outcome"), dict) else {}
    projected: dict[str, Any] = {
        "record_id": str(event.get("record_id") or "unknown"),
        "occurred_at": event.get("generated_at"),
        "display_type": "Reference broker record",
        "title": str(actual.get("summary") or "Historical broker record"),
        "state": "Reference only",
        "explanation": "No complete Qadam research thesis is attached to this record.",
        "learnable": False,
        "proof_eligible": False,
    }
    for key in ("instrument", "action", "quantity", "outcome"):
        value = event.get(key) or actual.get(key)
        if value not in (None, ""):
            projected[key] = value
    return projected


def build_learning_immediate_answer(
    counts: dict[str, Any],
    *,
    projection_available: bool = True,
    projection_stale: bool = False,
) -> dict[str, Any]:
    generated_from = {
        key: _integer_or_none(counts.get(key))
        for key in (
            "qadam_origin_outcome_count",
            "learnable_event_count",
            "proof_eligible_count",
            "mirror_reference_count",
            "lesson_awaiting_test_count",
        )
    }
    qadam_outcomes = generated_from["qadam_origin_outcome_count"]
    proof_eligible = generated_from["proof_eligible_count"]
    awaiting_test = generated_from["lesson_awaiting_test_count"]
    if not projection_available or projection_stale or qadam_outcomes is None or proof_eligible is None:
        state = "status_unavailable"
        tone = "unavailable"
        headline = "Learning status is temporarily unavailable"
        summary = (
            "Qadam cannot confirm a current learning answer because the public learning projection is missing or outside its freshness policy. "
            "Any last known records remain read-only, and no trading-performance or system-change conclusion should be inferred until the projection refreshes."
        )
    elif qadam_outcomes == 0:
        state = "waiting_for_attributable_paper_outcome"
        tone = "pending"
        headline = "Waiting for the first complete Qadam paper outcome"
        summary = (
            "Qadam has recorded research and operating lessons, but it has not yet completed a paper trade with complete research-to-execution evidence that can support an official judgment of its trading decisions. "
            "Historical broker records remain available for context only and do not count toward Qadam's performance record. "
            "No verified trading lesson exists yet, and any supported lesson must still pass testing and review before it can change the system."
        )
    elif proof_eligible == 0:
        state = "paper_outcomes_under_review"
        tone = "pending"
        headline = "Paper outcomes recorded; lessons still under review"
        summary = (
            "Qadam has attributable paper outcomes, but their evidence is not yet complete enough to support a verified lesson about its trading decisions. "
            "Research and operating records may still support cautious follow-up, while historical broker records remain context only. "
            "The evidence must complete attribution review before any lesson can move to governed testing."
        )
    elif (awaiting_test or 0) > 0:
        state = "verified_lessons_ready_for_testing"
        tone = "ready"
        headline = "Verified lessons are ready for testing"
        summary = (
            "Qadam has at least one attributable lesson supported by complete paper-outcome evidence. "
            "Reference broker history remains separate from that judgment and cannot strengthen the track record. "
            "The supported lesson now belongs in Tests & Improvements, where it must survive historical testing, forward observation, and review before Qadam can change."
        )
    else:
        state = "verified_lessons_recorded"
        tone = "verified"
        headline = "Verified lessons recorded"
        summary = (
            "Qadam has recorded at least one verified lesson from a complete attributable paper outcome. "
            "Historical broker records remain separate context and do not count toward that result. "
            "No verified lesson is currently waiting for a new test here; any approved system change is governed separately in Tests & Improvements."
        )
    return {
        "state": state,
        "tone": tone,
        "eyebrow": "Attribution status",
        "headline": headline,
        "summary": summary,
        "generated_from": generated_from,
        "projection_available": projection_available,
        "projection_stale": projection_stale,
    }


def build_learning_presentation(
    *,
    counts: dict[str, Any],
    learnable_outcomes: list[dict[str, Any]],
    learning_events: list[dict[str, Any]],
    reference_records: list[dict[str, Any]],
    projection_available: bool = True,
    projection_stale: bool = False,
) -> dict[str, Any]:
    reviews = [
        _learning_review_projection(record)
        for record in _dedupe_records(learnable_outcomes, learning_events)
    ]
    references = [
        _reference_record_projection(record)
        for record in _dedupe_records(reference_records)
    ]
    metric_specs = (
        ("learning_reviews", "What Qadam is learning", "Learning reviews recorded", "learnable_event_count"),
        ("verified_lessons", "Verified lessons", "Complete, attributable evidence", "proof_eligible_count"),
        ("reference_history", "Reference trade history", "Excluded from Qadam performance", "mirror_reference_count"),
    )
    return {
        "presentation_contract_version": RESULTS_PRESENTATION_VERSION,
        "page_copy": dict(RESULTS_PAGE_COPY),
        "immediate_answer": build_learning_immediate_answer(
            counts,
            projection_available=projection_available,
            projection_stale=projection_stale,
        ),
        "metric_groups": [
            {
                "id": metric_id,
                "label": label,
                "subtitle": subtitle,
                "binding": binding,
                "value": _integer_or_none(counts.get(binding)),
            }
            for metric_id, label, subtitle, binding in metric_specs
        ],
        "repositories": {
            "learning_reviews": {
                "label": "Learning Reviews",
                "summary": "Research, operating, and paper-outcome records Qadam is allowed to examine.",
                "count": len(reviews),
                "records": reviews,
            },
            "reference_history": {
                "label": "Reference Broker History",
                "summary": (
                    "Past broker records retained for context but excluded from Qadam's official performance and learning record."
                ),
                "exclusion_note": (
                    "These records are retained for historical context but excluded from Qadam's official performance and learning record because their complete research-to-execution lineage is unavailable."
                ),
                "count": len(references),
                "records": references,
            },
        },
        "handoff": dict(RESULTS_HANDOFF),
    }


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
    learning_backtest_gap = read_json(runtime / LEARNING_BACKTEST_GAP_ARTIFACT)
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
    learnable_outcomes = [
        record for record in events if record["qadam_origin"] and record["learnable"]
    ]
    learning_events = [record for record in learnable_events if not record["qadam_origin"]]
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
    required_projection_paths = (
        runtime / ATTRIBUTION_ARTIFACT,
        runtime / PROOF_ARTIFACT,
        runtime / PERFORMANCE_ARTIFACT,
    )
    projection_available = all(path.exists() for path in required_projection_paths)
    presentation = build_learning_presentation(
        counts=counts,
        learnable_outcomes=learnable_outcomes,
        learning_events=learning_events,
        reference_records=reference_records,
        projection_available=projection_available,
        projection_stale=False,
    )
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
        "historical_research_program": learning_backtest_gap,
        "counts": counts,
        "events": events,
        "learnable_outcomes": learnable_outcomes,
        "learning_events": learning_events,
        "reference_records": reference_records,
        "projection_state": {
            "available": projection_available,
            "stale": False,
            "required_source_count": len(required_projection_paths),
            "available_source_count": len([path for path in required_projection_paths if path.exists()]),
        },
        **presentation,
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
    if model.get("presentation_contract_version") != RESULTS_PRESENTATION_VERSION:
        errors.append("learning_cycle_presentation_contract_missing")
    metric_groups = model.get("metric_groups")
    metric_groups = metric_groups if isinstance(metric_groups, list) else []
    expected_metrics = (
        ("learning_reviews", "learnable_event_count"),
        ("verified_lessons", "proof_eligible_count"),
        ("reference_history", "mirror_reference_count"),
    )
    if len(metric_groups) != len(expected_metrics):
        errors.append("learning_cycle_primary_metric_count_invalid")
    if [(row.get("id"), row.get("binding")) for row in metric_groups] != list(expected_metrics):
        errors.append("learning_cycle_primary_metric_binding_invalid")
    for row in metric_groups:
        binding = row.get("binding")
        if binding in counts and row.get("value") != _integer_or_none(counts.get(binding)):
            errors.append("learning_cycle_primary_metric_value_mismatch")
    repositories = model.get("repositories")
    repositories = repositories if isinstance(repositories, dict) else {}
    if set(repositories) != {"learning_reviews", "reference_history"}:
        errors.append("learning_cycle_repository_contract_invalid")
    review_repository = repositories.get("learning_reviews")
    review_repository = review_repository if isinstance(review_repository, dict) else {}
    review_records = review_repository.get("records")
    review_records = review_records if isinstance(review_records, list) else []
    if review_repository.get("count") != len(review_records):
        errors.append("learning_cycle_review_repository_count_mismatch")
    if counts.get("learnable_event_count") != len(review_records):
        errors.append("learning_cycle_review_metric_repository_mismatch")
    reference_repository = repositories.get("reference_history")
    reference_repository = reference_repository if isinstance(reference_repository, dict) else {}
    projected_reference = reference_repository.get("records")
    projected_reference = projected_reference if isinstance(projected_reference, list) else []
    if reference_repository.get("count") != len(projected_reference):
        errors.append("learning_cycle_reference_repository_count_mismatch")
    if counts.get("mirror_reference_count") != len(projected_reference):
        errors.append("learning_cycle_reference_metric_repository_mismatch")
    if any(record.get("learnable") is not False for record in projected_reference):
        errors.append("learning_cycle_projected_reference_marked_learnable")
    if any(record.get("proof_eligible") is not False for record in projected_reference):
        errors.append("learning_cycle_projected_reference_granted_proof")
    answer = model.get("immediate_answer")
    answer = answer if isinstance(answer, dict) else {}
    projection = model.get("projection_state")
    projection = projection if isinstance(projection, dict) else {}
    expected_answer = build_learning_immediate_answer(
        counts,
        projection_available=projection.get("available") is True,
        projection_stale=projection.get("stale") is True,
    )
    if answer.get("state") != expected_answer["state"] or answer.get("headline") != expected_answer["headline"]:
        errors.append("learning_cycle_immediate_answer_contradicts_counts")
    summary = str(answer.get("summary") or "")
    sentence_count = len([part for part in re.split(r"(?<=[.!?])\s+", summary) if part.strip()])
    if answer.get("state") != "status_unavailable" and not 2 <= sentence_count <= 4:
        errors.append("learning_cycle_immediate_answer_sentence_count_invalid")
    handoff = model.get("handoff")
    handoff = handoff if isinstance(handoff, dict) else {}
    if (handoff.get("module_id"), handoff.get("view_id")) != ("learn", "improvements"):
        errors.append("learning_cycle_handoff_target_invalid")
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
