"""Truthful lifecycle state for Qadam's ranked research programmes."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from orchestrator.qadam_operator_ready_common import (
    authority_flags,
    read_json,
    sha256_json,
    validate_authority,
    write_json_atomic,
)


SCHEMA_VERSION = "qadam_research_programme_state.v1"
PROGRAMME_STATES = {
    "queued",
    "active",
    "blocked_external_data",
    "awaiting_outcome",
    "completed",
    "rejected",
}
RUNNABLE_STATES = {"active"}
KNOWN_PROGRAMME_IDS = {
    "programme-a-prediction-market-disagreement",
    "programme-b-stock-act-sector-repricing",
    "programme-c-unusual-whales-confirmation",
}


def _provider_contracts(runtime: Path) -> dict[str, dict[str, Any]]:
    payload = read_json(runtime / "qadam_focus_provider_contracts.json")
    records = payload.get("providers")
    records = records if isinstance(records, list) else []
    return {
        str(record.get("provider") or ""): record
        for record in records
        if isinstance(record, dict) and record.get("provider")
    }


def _stock_act_state(runtime: Path) -> tuple[str, str, str | None]:
    coverage = read_json(runtime / "qadam_stock_act_detail_coverage.json")
    generated_at = str(coverage.get("generated_at") or "") or None
    if (
        coverage.get("transaction_detail_signal_backtestable") is True
        and int(coverage.get("parsed_transaction_detail_count") or 0) > 0
    ):
        return (
            "active",
            "Official transaction-level disclosures are available for point-in-time testing.",
            generated_at,
        )
    if coverage.get("transaction_detail_state") == (
        "terminally_classified_not_present_in_acquired_archive"
    ):
        return (
            "blocked_external_data",
            "The acquired official archive contains filing-index events but no parsed transaction details.",
            generated_at,
        )
    return (
        "queued",
        "Transaction-detail coverage has not yet been classified conclusively.",
        generated_at,
    )


def _unusual_whales_state(runtime: Path) -> tuple[str, str, str | None]:
    history = read_json(runtime / "qadam_unusual_whales_history_coverage.json")
    forward = read_json(runtime / "qadam_unusual_whales_forward_capture_status.json")
    generated_at = (
        max(
            str(history.get("generated_at") or ""),
            str(forward.get("generated_at") or ""),
        )
        or None
    )
    if (
        history.get("historical_backtest_allowed") is True
        and int(history.get("backtest_eligible_record_count") or 0) > 0
    ):
        return (
            "active",
            "An approved historical flow sample is available for confirmation testing.",
            generated_at,
        )
    if forward.get("capture_running") is True:
        return (
            "awaiting_outcome",
            "Forward flow capture is active and must mature before outcome testing.",
            generated_at,
        )
    return (
        "blocked_external_data",
        "No approved historical flow sample or active forward capture is currently available.",
        generated_at,
    )


def _prediction_market_state(runtime: Path) -> tuple[str, str, str | None]:
    contracts = _provider_contracts(runtime)
    kalshi = contracts.get("kalshi") or {}
    polymarket = contracts.get("polymarket") or {}
    generated_at = (
        str(read_json(runtime / "qadam_focus_provider_contracts.json").get("generated_at") or "")
        or None
    )
    approved_states = {"approved_bounded_capture", "forward_only"}
    if (
        str(kalshi.get("state") or "") in approved_states
        and str(polymarket.get("state") or "") in approved_states
    ):
        return (
            "active",
            "Kalshi and Polymarket are approved for bounded research while Qadam refines contract identity and liquidity comparisons.",
            generated_at,
        )
    return (
        "blocked_external_data",
        "Both prediction-market research interfaces are not currently approved and available.",
        generated_at,
    )


def _derived_state(runtime: Path, programme_id: str) -> tuple[str, str, str | None]:
    if programme_id == "programme-a-prediction-market-disagreement":
        return _prediction_market_state(runtime)
    if programme_id == "programme-b-stock-act-sector-repricing":
        return _stock_act_state(runtime)
    if programme_id == "programme-c-unusual-whales-confirmation":
        return _unusual_whales_state(runtime)
    return (
        "active",
        "The programme has an executable research action under the current evidence contract.",
        None,
    )


def build_research_programme_state(
    runtime: Path,
    queue_payload: dict[str, Any],
    *,
    generated_at: str,
) -> dict[str, Any]:
    """Enrich a ranked queue and select the highest-ranked runnable programme."""

    rows = queue_payload.get("queue")
    rows = rows if isinstance(rows, list) else []
    programmes: list[dict[str, Any]] = []
    for position, source in enumerate(rows, start=1):
        if not isinstance(source, dict):
            continue
        programme_id = str(source.get("programme_id") or "").strip()
        if not programme_id:
            continue
        explicit_state = str(source.get("state") or "")
        if programme_id in KNOWN_PROGRAMME_IDS:
            state, state_reason, evidence_generated_at = _derived_state(
                runtime,
                programme_id,
            )
        elif explicit_state in PROGRAMME_STATES:
            state = explicit_state
            state_reason = str(source.get("state_reason") or "").strip()
            evidence_generated_at = source.get("evidence_generated_at")
        else:
            state, state_reason, evidence_generated_at = _derived_state(
                runtime,
                programme_id,
            )
        programme = {
            **source,
            "rank": int(source.get("rank") or position),
            "state": state,
            "state_reason": state_reason,
            "runnable": state in RUNNABLE_STATES,
            "evidence_generated_at": evidence_generated_at,
        }
        programme["progress_fingerprint"] = sha256_json(
            {
                "programme_id": programme_id,
                "question": programme.get("question"),
                "state": state,
                "state_reason": state_reason,
                "required_action": programme.get("required_action"),
            }
        )
        programmes.append(programme)

    programmes.sort(key=lambda row: (int(row.get("rank") or 0), row["programme_id"]))
    selected = next((row for row in programmes if row["runnable"]), None)
    result = {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "qadam_research_programme_state",
        "generated_at": generated_at,
        "status": "runnable_focus_selected" if selected else "no_runnable_programme",
        "programme_count": len(programmes),
        "active_count": sum(row["state"] == "active" for row in programmes),
        "blocked_external_data_count": sum(
            row["state"] == "blocked_external_data" for row in programmes
        ),
        "awaiting_outcome_count": sum(row["state"] == "awaiting_outcome" for row in programmes),
        "selected_programme": dict(selected) if selected else None,
        "programmes": programmes,
        "selection_rule": "highest_ranked_runnable_programme_not_queue_head",
        "blocked_programmes_can_be_selected": False,
        "trade_candidate_created": False,
        "paper_order_created_count": 0,
        "broker_write_count": 0,
        "public_safe": True,
        "authority": authority_flags(),
    }
    return result


def validate_research_programme_state(payload: dict[str, Any]) -> None:
    """Fail closed if a blocked programme can masquerade as active work."""

    required = {
        "schema_version",
        "artifact_type",
        "generated_at",
        "status",
        "programme_count",
        "selected_programme",
        "programmes",
        "selection_rule",
        "blocked_programmes_can_be_selected",
        "trade_candidate_created",
        "paper_order_created_count",
        "broker_write_count",
        "public_safe",
        "authority",
    }
    missing = sorted(required - set(payload))
    if missing:
        raise ValueError(f"Research programme state missing fields: {missing}")
    if payload.get("schema_version") != SCHEMA_VERSION:
        raise ValueError("Research programme state schema mismatch")
    if payload.get("artifact_type") != "qadam_research_programme_state":
        raise ValueError("Research programme state artifact type mismatch")
    programmes = payload.get("programmes")
    if not isinstance(programmes, list):
        raise ValueError("Research programme state programmes must be a list")
    if int(payload.get("programme_count") or 0) != len(programmes):
        raise ValueError("Research programme state count mismatch")
    for programme in programmes:
        if not isinstance(programme, dict):
            raise ValueError("Research programme state row invalid")
        state = str(programme.get("state") or "")
        if state not in PROGRAMME_STATES:
            raise ValueError(f"Research programme state invalid: {state}")
        if programme.get("runnable") is not (state in RUNNABLE_STATES):
            raise ValueError("Research programme runnable flag mismatch")
    selected = payload.get("selected_programme")
    if selected is not None:
        if not isinstance(selected, dict) or selected.get("state") not in RUNNABLE_STATES:
            raise ValueError("Research programme selected a non-runnable programme")
        if selected.get("runnable") is not True:
            raise ValueError("Research programme selected row is not runnable")
    if payload.get("blocked_programmes_can_be_selected") is not False:
        raise ValueError("Research programme state permits blocked selection")
    if payload.get("trade_candidate_created") is not False:
        raise ValueError("Research programme state created a trade candidate")
    if int(payload.get("paper_order_created_count") or 0) != 0:
        raise ValueError("Research programme state created a paper order")
    if int(payload.get("broker_write_count") or 0) != 0:
        raise ValueError("Research programme state created a broker write")
    if payload.get("public_safe") is not True:
        raise ValueError("Research programme state is not public-safe")
    authority_errors = validate_authority(payload.get("authority") or {})
    if authority_errors:
        raise ValueError(
            "Research programme state authority invalid: " + ", ".join(authority_errors)
        )


def refresh_research_programme_state(
    runtime: Path,
    *,
    generated_at: str,
) -> dict[str, Any]:
    """Refresh programme truth without rerunning research or creating authority."""

    queue_path = runtime / "qadam_value_of_information_queue.json"
    queue_payload = read_json(queue_path)
    state = build_research_programme_state(
        runtime,
        queue_payload,
        generated_at=generated_at,
    )
    validate_research_programme_state(state)
    write_json_atomic(runtime / "qadam_research_programme_state.json", state)

    if queue_payload:
        selected = state.get("selected_programme")
        selected = selected if isinstance(selected, dict) else None
        queue_payload.update(
            {
                "queue": state["programmes"],
                "programme_state_status": state["status"],
                "active_programme_count": state["active_count"],
                "blocked_external_data_count": state["blocked_external_data_count"],
                "awaiting_outcome_count": state["awaiting_outcome_count"],
                "selected_programme_id": (selected.get("programme_id") if selected else None),
                "selection_rule": state["selection_rule"],
                "programme_state_refreshed_at": generated_at,
            }
        )
        write_json_atomic(queue_path, queue_payload)

        post_path = runtime / "qadam_post_backtest_decision.json"
        post_decision = read_json(post_path)
        if post_decision:
            post_decision.update(
                {
                    "next_test": (
                        str(selected.get("question") or "").strip()
                        if selected
                        else "Wait for new provider-backed evidence or a forward outcome to mature."
                    ),
                    "next_programme_id": (selected.get("programme_id") if selected else None),
                    "next_programme_state": selected.get("state") if selected else None,
                    "blocked_programmes_are_not_active_questions": True,
                    "research_programme_state_refreshed_at": generated_at,
                }
            )
            write_json_atomic(post_path, post_decision)
    return state
