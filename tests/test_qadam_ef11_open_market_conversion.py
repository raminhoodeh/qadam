from __future__ import annotations

import json
from datetime import datetime, timezone

from orchestrator.qadam_ef11_open_market_conversion import (
    build_baseline,
    build_daily_summaries,
    build_execution_evidence,
    build_prestaged_setups,
    build_root_cause_and_repair,
    build_visibility,
    primary_root_cause,
)
from orchestrator.qadam_open_market_conversion import (
    OUTPUT_ARTIFACTS,
    _conversion_cycles,
    _current_accepted_handoffs,
)
from orchestrator.qadam_market_session_truth import (
    build_market_clock_truth,
    expected_market_session_phase,
    validate_market_clock_truth,
)
from orchestrator.qadam_operator_dashboard import (
    EF11_CERTIFICATION_ARTIFACT,
    EF11_CLOSED_MARKET_FRESHNESS_SECONDS,
    EF11_DASHBOARD_ARTIFACT,
    FRESHNESS_SPECS,
    build_freshness_audit,
)


def _write_json(path, payload) -> None:
    path.write_text(json.dumps(payload), encoding="utf-8")


def _write_jsonl(path, rows) -> None:
    path.write_text("".join(json.dumps(row) + "\n" for row in rows), encoding="utf-8")


def test_strategy_translation_stage_tracks_its_own_output() -> None:
    assert (
        OUTPUT_ARTIFACTS["strategy_translation"]
        == "qadam_strategy_translation_summary.json"
    )
    assert OUTPUT_ARTIFACTS["canonical_tradeability"] == (
        "qadam_tradeability_envelopes.jsonl"
    )


def test_fresh_provider_clock_is_actionable_only_during_regular_session() -> None:
    mirror = {
        "market_clock": {
            "timestamp": "2026-08-10T09:59:30-04:00",
            "is_open": True,
            "next_close": "2026-08-10T16:00:00-04:00",
        },
        "snapshot": {"observed_at": "2026-08-10T13:59:40+00:00"},
    }
    truth = build_market_clock_truth(
        mirror, generated_at="2026-08-10T14:00:00+00:00"
    )
    assert truth["provider_fresh"] is True
    assert truth["session_phase"] == "regular"
    assert truth["actionable_for_conversion"] is True
    assert validate_market_clock_truth(truth) == []


def test_yesterdays_open_clock_is_rejected_today() -> None:
    mirror = {
        "market_clock": {
            "timestamp": "2026-08-10T10:00:00-04:00",
            "is_open": True,
        },
        "snapshot": {"observed_at": "2026-08-10T14:00:01+00:00"},
    }
    truth = build_market_clock_truth(
        mirror, generated_at="2026-08-11T14:00:00+00:00"
    )
    assert truth["provider_fresh"] is False
    assert truth["actionable_for_conversion"] is False
    assert truth["session_phase"] == "provider_stale"


def test_weekend_clock_cannot_create_eligible_session() -> None:
    mirror = {
        "market_clock": {
            "timestamp": "2026-08-09T10:00:00-04:00",
            "is_open": True,
        },
        "snapshot": {"observed_at": "2026-08-09T14:00:01+00:00"},
    }
    truth = build_market_clock_truth(
        mirror, generated_at="2026-08-09T14:00:30+00:00"
    )
    assert truth["calendar_disagreement"] is True
    assert truth["actionable_for_conversion"] is False


def test_expected_market_phase_uses_new_york_session_boundaries() -> None:
    sunday = datetime(2026, 8, 9, 14, 0, tzinfo=timezone.utc)
    monday_regular = datetime(2026, 8, 10, 14, 0, tzinfo=timezone.utc)
    assert expected_market_session_phase(sunday) == "weekend"
    assert expected_market_session_phase(monday_regular) == "regular"


def test_dashboard_ef11_freshness_is_session_aware(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(
        "orchestrator.qadam_operator_dashboard.runtime_dir", lambda _settings=None: tmp_path
    )

    weekend = build_freshness_audit(
        generated_at="2026-08-09T14:00:00+00:00"
    )
    weekend_records = {
        row["artifact"].rsplit("/", 1)[-1]: row for row in weekend["records"]
    }
    assert (
        weekend_records[EF11_DASHBOARD_ARTIFACT]["stale_after_seconds"]
        == EF11_CLOSED_MARKET_FRESHNESS_SECONDS
    )
    assert (
        weekend_records[EF11_CERTIFICATION_ARTIFACT]["stale_after_seconds"]
        == EF11_CLOSED_MARKET_FRESHNESS_SECONDS
    )

    regular = build_freshness_audit(
        generated_at="2026-08-10T14:00:00+00:00"
    )
    regular_records = {
        row["artifact"].rsplit("/", 1)[-1]: row for row in regular["records"]
    }
    assert (
        regular_records[EF11_DASHBOARD_ARTIFACT]["stale_after_seconds"]
        == FRESHNESS_SPECS[EF11_DASHBOARD_ARTIFACT]
    )
    assert (
        regular_records[EF11_CERTIFICATION_ARTIFACT]["stale_after_seconds"]
        == FRESHNESS_SPECS[EF11_CERTIFICATION_ARTIFACT]
    )


def test_closed_market_hypothesis_is_preserved_for_open_revalidation(tmp_path) -> None:
    hypothesis = {
        "hypothesis_id": "hypothesis:1",
        "candidate_identity_material": {
            "candidate_identity_id": "identity:1",
            "research_goal_id": "goal:1",
            "observed_instrument": "SMH",
            "direction": "long",
            "time_window": "5d_forward",
        },
        "instrument_proxy_mapping": {"execution_proxy": "SMH"},
        "freshness": {"expires_at": "2026-08-14T14:00:00+00:00"},
        "pattern_lineage": {
            "score_id": "score:1",
            "pattern_relationship_id": "pattern:1",
            "raw_research_score": 0.64,
            "fresh_support_sources": ["sec_edgar"],
            "fresh_quorum_sources": ["sec_edgar"],
        },
        "strategy_mapping": {"strategy_family_id": "semiconductors"},
    }
    _write_jsonl(tmp_path / "qadam_strategy_hypotheses_v3.jsonl", [hypothesis])
    rows, status, rejections = build_prestaged_setups(
        tmp_path,
        baseline_id="baseline:1",
        market_truth={"actionable_for_conversion": False, "next_open": "2026-08-10"},
        generated_at="2026-08-09T14:00:00+00:00",
    )
    assert rejections == []
    assert status["setup_count"] == 1
    assert rows[0]["state"] == "pending_market_open_confirmation"
    assert rows[0]["paper_order_created"] is False


def test_limit_fallback_requires_measured_history_and_caps_notional(tmp_path) -> None:
    setup = {
        "prestage_id": "prestage:1",
        "hypothesis_id": "hypothesis:1",
        "score_id": "score:1",
        "execution_proxy": "SMH",
    }
    history = [
        {
            "context_id": f"history:{index}",
            "generated_at": f"2026-08-0{index % 8 + 1}T14:00:00+00:00",
            "instrument": "SMH",
            "provider_backed": True,
            "quote_actionable": True,
            "observed_spread_bps": 4.0 + index / 100,
        }
        for index in range(20)
    ]
    _write_jsonl(tmp_path / "qadam_execution_evidence_context.jsonl", history)
    packet = {
        "recent_packets": [
            {
                "price_volume_context": {
                    "records": [
                        {
                            "symbol": "SMH",
                            "provider": "alpaca_market_data_v2",
                            "provider_backed": True,
                            "available_at": "2026-08-10T14:00:00+00:00",
                            "quote_actionable": False,
                            "trade_actionable": True,
                            "trade_age_seconds": 10,
                            "last_trade_observed_at": "2026-08-10T13:59:50+00:00",
                            "last_trade_price": 500,
                            "current_price": 500,
                            "average_daily_dollar_volume": 100_000_000,
                        }
                    ]
                }
            }
        ]
    }
    _write_json(tmp_path / "market_context_packet.json", packet)
    rows, profiles, rejections = build_execution_evidence(
        tmp_path,
        baseline_id="baseline:1",
        market_truth={
            "actionable_for_conversion": True,
            "session_date": "2026-08-10",
            "session_phase": "regular",
            "truth_id": "truth:1",
        },
        prestaged=[setup],
        generated_at="2026-08-10T14:00:00+00:00",
    )
    current = next(row for row in rows if row["context_id"] not in {f"history:{i}" for i in range(20)})
    assert profiles["profiles"]["SMH"]["fallback_history_sufficient"] is True
    assert current["execution_mode"] == "fresh_trade_limit_only"
    assert current["order_type"] == "limit"
    assert current["maximum_notional_usd"] == 500.0
    assert rejections == []


def test_akber_hold_is_one_root_cause_with_downstream_not_reached() -> None:
    root, propagated = primary_root_cause(
        market_truth={
            "provider_backed": True,
            "provider_fresh": True,
            "calendar_disagreement": False,
            "actionable_for_conversion": True,
        },
        setup={"prestage_id": "setup:1"},
        execution={"execution_context_actionable": True},
        akber={"decision": "hold_missing_context"},
    )
    assert root == "akber_hold"
    assert propagated == ["shadow_not_reached", "risk_not_reached", "router_not_reached"]


def test_conversion_cycle_retains_risk_rejection_diagnostics(tmp_path) -> None:
    _write_jsonl(
        tmp_path / "qadam_risk_rejections.jsonl",
        [
            {
                "rejection_id": "risk-rejection:1",
                "score_id": "score:1",
                "rejection_reasons": ["decision_time_shadow_snapshot_not_ready"],
                "position_size_proposed": False,
            }
        ],
    )
    rows = _conversion_cycles(
        runtime=tmp_path,
        bundle={
            "market_truth": {
                "provider_backed": True,
                "provider_fresh": True,
                "actionable_for_conversion": True,
                "session_date": "2026-08-13",
                "session_phase": "regular",
                "truth_id": "truth:1",
            },
            "baseline": {"baseline_id": "baseline:1"},
            "prestage": [
                {
                    "prestage_id": "prestage:1",
                    "score_id": "score:1",
                    "execution_proxy": "NVDA",
                }
            ],
            "execution_context": [
                {
                    "prestage_id": "prestage:1",
                    "execution_context_actionable": True,
                }
            ],
        },
        generation_id="generation:1",
        generated_at="2026-08-13T16:56:00+00:00",
        command_receipts=[{"command_id": "risk", "status": "passed"}],
        paperops_handoffs=[],
        paper_order_count=0,
        provider_canary=False,
    )
    assert rows[0]["risk_rejection_id"] == "risk-rejection:1"
    assert rows[0]["risk_rejection_reasons"] == [
        "decision_time_shadow_snapshot_not_ready"
    ]


def test_stale_clock_outside_regular_session_is_not_an_infrastructure_alert(
    tmp_path,
) -> None:
    market_truth = {
        "provider_backed": True,
        "provider_fresh": False,
        "expected_session_phase": "weekend",
        "actionable_for_conversion": False,
        "next_open": "2026-08-10T09:30:00-04:00",
    }
    root, propagated = primary_root_cause(market_truth=market_truth)
    assert root == "market_closed"
    assert propagated == []

    root_artifact, repair_queue, _history = build_root_cause_and_repair(
        tmp_path,
        baseline_id="baseline:1",
        market_truth=market_truth,
        conversion_status={"latest_primary_root_cause": "provider_clock_stale"},
        generated_at="2026-08-09T14:00:00+00:00",
    )
    assert root_artifact["primary_root_cause"] == "market_closed"
    assert root_artifact["next_recheck_at"] == "2026-08-10T09:30:00-04:00"
    assert repair_queue["repair_request_count"] == 0


def test_stale_clock_during_regular_session_remains_repairable(tmp_path) -> None:
    market_truth = {
        "provider_backed": True,
        "provider_fresh": False,
        "expected_session_phase": "regular",
        "actionable_for_conversion": False,
    }
    root, _propagated = primary_root_cause(market_truth=market_truth)
    assert root == "provider_clock_stale"

    root_artifact, repair_queue, _history = build_root_cause_and_repair(
        tmp_path,
        baseline_id="baseline:1",
        market_truth=market_truth,
        conversion_status={},
        generated_at="2026-08-10T14:00:00+00:00",
    )
    assert root_artifact["automatically_repairable"] is True
    assert repair_queue["repair_request_count"] == 1


def test_daily_reducer_is_deterministic_and_preserves_best_cycle() -> None:
    cycles = [
        {
            "cycle_id": "cycle:1",
            "baseline_id": "baseline:1",
            "session_date": "2026-08-10",
            "generated_at": "2026-08-10T14:00:00+00:00",
            "decision_at": "2026-08-10T14:00:00+00:00",
            "setup_id": "setup:1",
            "execution_context_actionable": False,
            "highest_stage_reached": 3,
            "primary_root_cause": "execution_context_missing",
        },
        {
            "cycle_id": "cycle:2",
            "baseline_id": "baseline:1",
            "session_date": "2026-08-10",
            "generated_at": "2026-08-10T14:05:00+00:00",
            "decision_at": "2026-08-10T14:05:00+00:00",
            "setup_id": "setup:1",
            "execution_context_actionable": True,
            "highest_stage_reached": 9,
            "paperops_handoff_count": 1,
            "primary_root_cause": None,
        },
    ]
    summary = build_daily_summaries(cycles)[0]
    assert summary["best_evidence_complete_cycle_id"] == "cycle:2"
    assert summary["highest_stage_reached"] == 9
    assert summary["paperops_handoff_count"] == 1


def test_baseline_is_immutable_for_same_paper_epoch(tmp_path) -> None:
    _write_json(
        tmp_path / "qadam_strategy_source_contract.json",
        {"source_count": 41},
    )
    _write_json(
        tmp_path / "qadam_instrument_role_registry.json",
        {"instrument_count": 19},
    )
    _write_json(
        tmp_path / "alpaca_paper_mirror.json",
        {"snapshot": {"paper_epoch_id": "paper:test", "equity": 100_000}},
    )
    baseline, _ = build_baseline(
        tmp_path, generated_at="2026-08-09T10:00:00+00:00"
    )
    _write_json(tmp_path / "qadam_ef11_baseline.json", baseline)
    _write_json(
        tmp_path / "qadam_strategy_source_contract.json",
        {"source_count": 41, "new_runtime_detail": True},
    )
    second, reconciliation = build_baseline(
        tmp_path, generated_at="2026-08-09T11:00:00+00:00"
    )
    assert second == baseline
    assert reconciliation["baseline_reused"] is True
    assert reconciliation["changed_artifact_count"] >= 1


def test_current_handoff_filter_rejects_prior_cycle_and_wrong_lineage(tmp_path) -> None:
    rows = [
        {
            "generated_at": "2026-08-09T09:59:00+00:00",
            "source_handoff": {
                "route": "guarded_alpaca_paper_via_paperops",
                "candidate_identity_id": "identity:1",
                "lineage": {"score_id": "score:1"},
            },
        },
        {
            "generated_at": "2026-08-09T10:00:05+00:00",
            "source_handoff": {
                "route": "guarded_alpaca_paper_via_paperops",
                "candidate_identity_id": "identity:wrong",
                "lineage": {"score_id": "score:1"},
            },
        },
        {
            "generated_at": "2026-08-09T10:00:06+00:00",
            "source_handoff": {
                "route": "guarded_alpaca_paper_via_paperops",
                "candidate_identity_id": "identity:1",
                "lineage": {"score_id": "score:1"},
            },
        },
    ]
    _write_jsonl(tmp_path / "qadam_paperops_handoff_v3_accepted.jsonl", rows)
    current = _current_accepted_handoffs(
        tmp_path,
        bundle={
            "prestage": [
                {"score_id": "score:1", "candidate_identity_id": "identity:1"}
            ]
        },
        cycle_started_at="2026-08-09T10:00:00+00:00",
        router_written_in_generation=True,
    )
    assert current == [rows[-1]]
    assert (
        _current_accepted_handoffs(
            tmp_path,
            bundle={"prestage": []},
            cycle_started_at="2026-08-09T10:00:00+00:00",
            router_written_in_generation=False,
        )
        == []
    )


def test_visibility_is_quiet_without_material_change_and_specific_for_order() -> None:
    base = {
        "certification": {
            "status": "collecting_empirical_conversion_evidence",
            "structural_ready": True,
            "provider_conversion_ready": False,
            "empirically_conversion_proven": False,
            "eligible_market_days_observed": 0,
            "eligible_market_day_target": 5,
        },
        "market_truth": {"provider_fresh": True, "session_phase": "weekend"},
        "prestaged_status": {
            "setup_count": 0,
            "ready_for_open_market_revalidation_count": 0,
        },
        "risk_status": {
            "current_default_tier": "discovery_micro",
            "maximum_current_first_time_notional_usd": 500.0,
            "absolute_notional_ceiling_usd": 5000.0,
        },
        "generated_at": "2026-08-09T12:00:00+00:00",
    }
    _summary, quiet = build_visibility(
        **base,
        root_cause={
            "primary_root_cause": "market_closed",
            "owner": "market_calendar",
            "next_recheck_at": "2026-08-10T13:30:00+00:00",
        },
        conversion_status={
            "latest_conversion_generation_id": None,
            "paperops_handoff_count": 0,
            "paper_order_count": 0,
        },
    )
    assert quiet["send_candidate"] is False
    assert quiet["material_event_type"] == "no_material_change"

    _summary, order = build_visibility(
        **base,
        root_cause={"primary_root_cause": None, "owner": "conversion_coordinator"},
        conversion_status={
            "latest_conversion_generation_id": "generation:1",
            "paperops_handoff_count": 1,
            "paper_order_count": 1,
        },
    )
    assert order["send_candidate"] is True
    assert order["material_event_type"] == "paper_order_submitted"
    assert "guarded Alpaca Paper order" in order["message"]
    assert order["live_capital_enabled"] is False
