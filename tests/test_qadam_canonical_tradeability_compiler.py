from __future__ import annotations

from dataclasses import replace
from pathlib import Path
from tempfile import TemporaryDirectory

import pytest
from pydantic import ValidationError

from orchestrator.config import Settings
from orchestrator.qadam_canonical_contracts import AtomicArtifactStore
from orchestrator.qadam_evidence_contracts import build_lane_contribution
from orchestrator.qadam_operator_service import SERVICE_DEFINITIONS
import orchestrator.qadam_tradeability_pipeline as tradeability_pipeline
from orchestrator.qadam_tradeability_pipeline import _collect_drafts
from orchestrator.qadam_tradeability_audits import (
    build_and_write_consumer_audit,
    build_and_write_decision_generation_audit,
    build_and_write_migration_audit,
)
from orchestrator.qadam_tradeability_envelope import TradeabilityEnvelope
from orchestrator.qadam_tradeability_reliability import (
    _front_half,
    _load_fixture,
    _valid_full_journey,
    build_and_write_contract_defect_state,
    build_and_write_golden_journeys,
    build_and_write_reachability_canary,
)


def _settings(runtime: Path) -> Settings:
    base = Settings.from_env()
    return replace(
        base,
        runtime_dir=str(runtime),
        state_root=str(runtime / "state"),
        data_root=str(runtime.parent),
    )


def test_idle_compiler_does_not_load_historical_decision_context(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    loaded = False

    def unexpected_current_artifacts(_settings):
        nonlocal loaded
        loaded = True
        raise AssertionError("idle compiler loaded historical decision context")

    monkeypatch.setattr(
        tradeability_pipeline,
        "current_decision_artifacts",
        unexpected_current_artifacts,
    )

    state = tradeability_pipeline.build_tradeability_pipeline_state(
        _settings(tmp_path)
    )

    assert loaded is False
    assert state["registry"]["source_draft_count"] == 0


def test_strict_envelope_rejects_unknown_fields() -> None:
    with TemporaryDirectory() as temporary:
        result = _front_half(
            _load_fixture("strict-envelope"),
            "valid_pass",
            Path(temporary),
        )
        payload = result["envelope"].model_dump(mode="json")
        payload["undocumented_consumer_field"] = True
        with pytest.raises(ValidationError):
            TradeabilityEnvelope.model_validate(payload)


def test_disk_backed_golden_journeys_cover_positive_and_negative_paths(
    tmp_path: Path,
) -> None:
    payload, checks, errors = build_and_write_golden_journeys(_settings(tmp_path))
    assert errors == []
    assert checks["status"] == "passed"
    assert payload["journey_count"] == 10
    assert payload["passed_count"] == 10
    assert payload["paper_order_created_count"] == 0
    assert payload["broker_write_count"] == 0


def test_valid_journey_preserves_generation_through_handoff(tmp_path: Path) -> None:
    result = _valid_full_journey(_load_fixture("generation-lineage"), tmp_path)
    assert result["actual"] == "accepted_for_guarded_paperops_sequence"
    generation_id = result["decision"]["decision_generation_id"]
    assert generation_id
    assert result["handoff"]["decision_generation_id"] == generation_id
    assert result["decision"]["hypothesis_id"] == "hypothesis:generation-lineage"
    assert result["handoff"]["hypothesis_id"] == "hypothesis:generation-lineage"
    manifest, checks, errors = build_and_write_decision_generation_audit(
        _settings(tmp_path)
    )
    assert errors == []
    assert checks["status"] == "passed"
    assert manifest["completed_generation_count"] == 1
    assert manifest["mixed_generation_join_count"] == 0


def test_idle_generation_ignores_legacy_shadow_history(tmp_path: Path) -> None:
    AtomicArtifactStore(tmp_path).write_jsonl(
        "qadam_forward_shadow_decisions.jsonl",
        [{"hypothesis_id": "legacy-only", "decision_id": "old-shadow"}],
    )
    manifest, checks, errors = build_and_write_decision_generation_audit(
        _settings(tmp_path)
    )
    assert errors == []
    assert checks["valid_idle_state"] is True
    assert manifest["status"] == "ready_idle"


def test_terminal_router_hold_completes_generation_without_execution_lanes(
    tmp_path: Path,
) -> None:
    store = AtomicArtifactStore(tmp_path)
    hypothesis_id = "hypothesis:terminal-hold"
    current_generation = "decision-generation:current"
    base = {
        "hypothesis_id": hypothesis_id,
        "decision_generation_id": current_generation,
    }
    envelope_id = "envelope:terminal-hold"
    store.write_jsonl(
        "qadam_tradeability_envelopes.jsonl",
        [{**base, "envelope_id": envelope_id}],
    )
    store.write_jsonl(
        "qadam_strategy_hypotheses_v3.jsonl",
        [{**base, "tradeability_envelope_id": envelope_id}],
    )
    for filename in (
        "qadam_decision_evidence_packets.jsonl",
        "qadam_akber_filter_v3_inputs.jsonl",
    ):
        store.write_jsonl(filename, [base])
    store.write_jsonl(
        "qadam_akber_filter_v3_results.jsonl",
        [{**base, "decision": "pass", "akber_result_id": "akber:current"}],
    )
    store.write_jsonl(
        "qadam_forward_shadow_decisions.jsonl",
        [
            {
                "hypothesis_id": hypothesis_id,
                "decision_generation_id": "decision-generation:historical",
                "decision_id": "shadow:historical",
            }
        ],
    )
    store.write_jsonl(
        "qadam_router_v3_decisions.jsonl",
        [
            {
                **base,
                "router_decision_id": "router:hold",
                "final_state": "hold",
                "exactly_one_final_state": True,
                "paperops_handoff_allowed": False,
            }
        ],
    )

    manifest, checks, errors = build_and_write_decision_generation_audit(
        _settings(tmp_path)
    )

    assert errors == []
    assert checks["status"] == "passed"
    assert manifest["completed_generation_count"] == 1
    assert manifest["mixed_generation_join_count"] == 0
    assert manifest["stale_generation_record_count_ignored"] == 1

    consumer, consumer_checks, consumer_errors = build_and_write_consumer_audit(
        _settings(tmp_path)
    )
    assert consumer_errors == []
    assert consumer_checks["status"] == "passed"
    assert consumer["downstream_counts"]["shadow"] == 0
    assert consumer["stale_generation_record_count_ignored"] == 1


def _write_referenced_shadow_generation(
    tmp_path: Path,
    *,
    source_signal_id: str,
    router_signal_id: str,
) -> None:
    store = AtomicArtifactStore(tmp_path)
    hypothesis_id = "hypothesis:current"
    generation_id = "decision-generation:current"
    envelope_id = "envelope:current"
    base = {
        "hypothesis_id": hypothesis_id,
        "decision_generation_id": generation_id,
    }
    store.write_jsonl(
        "qadam_tradeability_envelopes.jsonl",
        [{**base, "envelope_id": envelope_id}],
    )
    store.write_jsonl(
        "qadam_strategy_hypotheses_v3.jsonl",
        [{**base, "tradeability_envelope_id": envelope_id}],
    )
    store.write_jsonl("qadam_decision_evidence_packets.jsonl", [base])
    store.write_jsonl("qadam_akber_filter_v3_inputs.jsonl", [base])
    store.write_jsonl(
        "qadam_akber_filter_v3_results.jsonl",
        [{**base, "decision": "pass", "akber_result_id": "akber:current"}],
    )
    store.write_jsonl(
        "qadam_forward_shadow_decisions.jsonl",
        [
            {
                "hypothesis_id": "hypothesis:historical",
                "decision_generation_id": "decision-generation:historical",
                "decision_id": "shadow:immutable",
                "economic_signal_identity_id": source_signal_id,
            }
        ],
    )
    store.write_jsonl(
        "qadam_position_size_proposals.jsonl",
        [{**base, "proposal_id": "risk:current"}],
    )
    store.write_jsonl(
        "qadam_router_v3_decisions.jsonl",
        [
            {
                **base,
                "router_decision_id": "router:current",
                "economic_signal_identity_id": router_signal_id,
                "final_state": "experimental_paper_review_candidate",
                "exactly_one_final_state": True,
                "paperops_handoff_allowed": True,
                "lineage": {
                    "hypothesis_id": hypothesis_id,
                    "shadow_evidence_id": "shadow:immutable",
                },
            }
        ],
    )
    store.write_jsonl(
        "qadam_paperops_handoff_v3.jsonl",
        [{**base, "paperops_handoff_id": "handoff:current"}],
    )


def test_generation_resolves_immutable_shadow_by_economic_signal(
    tmp_path: Path,
) -> None:
    _write_referenced_shadow_generation(
        tmp_path,
        source_signal_id="signal:stable",
        router_signal_id="signal:stable",
    )

    manifest, checks, errors = build_and_write_decision_generation_audit(
        _settings(tmp_path)
    )
    consumer, consumer_checks, consumer_errors = build_and_write_consumer_audit(
        _settings(tmp_path)
    )

    assert errors == consumer_errors == []
    assert checks["status"] == consumer_checks["status"] == "passed"
    assert manifest["completed_generation_count"] == 1
    assert manifest["immutable_shadow_reference_count"] == 1
    assert consumer["immutable_shadow_reference_count"] == 1
    assert consumer["downstream_counts"]["shadow"] == 1


def test_generation_rejects_mismatched_immutable_shadow_signal(
    tmp_path: Path,
) -> None:
    _write_referenced_shadow_generation(
        tmp_path,
        source_signal_id="signal:old",
        router_signal_id="signal:new",
    )

    manifest, checks, errors = build_and_write_decision_generation_audit(
        _settings(tmp_path)
    )

    assert manifest["status"] == "blocked"
    assert checks["status"] == "blocked"
    assert any("referenced_shadow_signal_identity_mismatch" in row for row in errors)


def test_contract_defect_repair_requests_are_deduplicated(tmp_path: Path) -> None:
    store = AtomicArtifactStore(tmp_path)
    defect = {
        "hypothesis_id": "hypothesis:defect",
        "source_draft_ref": "provider:test",
        "reasons": ["required_field_missing:liquidity_and_spread"],
    }
    store.write_jsonl("qadam_tradeability_contract_defects.jsonl", [defect])
    first, first_checks, first_errors = build_and_write_contract_defect_state(
        _settings(tmp_path)
    )
    second, second_checks, second_errors = build_and_write_contract_defect_state(
        _settings(tmp_path)
    )
    assert first_errors == second_errors == []
    assert first_checks["status"] == second_checks["status"] == "passed"
    assert first["new_repair_request_count"] == 1
    assert second["new_repair_request_count"] == 0
    assert second["open_repair_request_count"] == 1
    assert second["service_circuit_required"] is True


def test_reachability_canary_is_broker_disabled_and_separate_from_idle(
    tmp_path: Path,
) -> None:
    canary, checks, errors = build_and_write_reachability_canary(_settings(tmp_path))
    assert errors == []
    assert checks["reachability_state"] == "reachable"
    assert checks["current_setup_state"] == "no_current_setup"
    assert canary["broker_disabled"] is True
    assert canary["paper_order_created_count"] == 0
    assert canary["broker_write_count"] == 0
    assert canary["paper_calendar_advanced"] is False
    assert canary["real_market_session_observed"] is False


def test_reachability_soak_records_one_fresh_regular_market_session(
    tmp_path: Path,
) -> None:
    AtomicArtifactStore(tmp_path).write_json(
        "qadam_market_clock_truth.json",
        {
            "truth_id": "market-clock:test-session",
            "provider_backed": True,
            "provider_fresh": True,
            "actionable_for_conversion": True,
            "session_phase": "regular",
            "session_date": "2026-08-17",
        },
    )
    first, first_checks, first_errors = build_and_write_reachability_canary(
        _settings(tmp_path)
    )
    second, second_checks, second_errors = build_and_write_reachability_canary(
        _settings(tmp_path)
    )
    assert first_errors == second_errors == []
    assert first_checks["status"] == second_checks["status"] == "passed"
    assert first["real_market_session_observed"] is True
    assert first["market_session_date"] == "2026-08-17"
    assert second["canary_id"] == first["canary_id"]
    history = [
        row
        for row in (tmp_path / "qadam_tradeability_reachability_history.jsonl")
        .read_text(encoding="utf-8")
        .splitlines()
        if row.strip()
    ]
    assert len(history) == 1


def test_migration_and_consumers_have_one_canonical_path(tmp_path: Path) -> None:
    migration, migration_checks, migration_errors = build_and_write_migration_audit(
        _settings(tmp_path)
    )
    consumer, consumer_checks, consumer_errors = build_and_write_consumer_audit(
        _settings(tmp_path)
    )
    assert migration_errors == consumer_errors == []
    assert migration_checks["status"] == consumer_checks["status"] == "passed"
    assert migration["active_canonical_producer_count"] == 1
    assert consumer["legacy_qeg_reader_count"] == 0


def test_operator_runs_contract_checks_as_scheduled_health_gates() -> None:
    services = {service.service_id: service for service in SERVICE_DEFINITIONS}
    canonical_commands = {
        command[0] for command in services["canonical_tradeability"].command_sequence
    }
    router_commands = {
        command[0] for command in services["portfolio_router_review"].command_sequence
    }
    assert "scripts/check_qadam_contract_defect_handling.py" in canonical_commands
    assert "scripts/check_qadam_tradeability_pipeline.py" in canonical_commands
    assert "scripts/check_qadam_tradeability_migration.py" in canonical_commands
    assert "scripts/check_qadam_tradeability_reachability.py" in canonical_commands
    assert "scripts/check_qadam_decision_generation.py" in router_commands
    assert "scripts/check_qadam_tradeability_consumers.py" in router_commands
    dashboard_commands = {
        command[0] for command in services["dashboard_refresh"].command_sequence
    }
    assert "scripts/check_qadam_canonical_tradeability_compiler.py" not in dashboard_commands
    assert canonical_commands.isdisjoint(dashboard_commands)


def test_stale_lane_direction_does_not_replace_current_canonical_draft(
    tmp_path: Path,
) -> None:
    store = AtomicArtifactStore(tmp_path)
    current = {
        "hypothesis_id": "hypothesis:current",
        "evidence_class": "experimental_unvalidated",
        "candidate_identity_material": {"candidate_identity_id": "candidate:one"},
        "direction_horizon": {"direction_resolution_id": "direction:current"},
    }
    stale = {
        **current,
        "hypothesis_id": "hypothesis:stale-lane",
        "direction_horizon": {"direction_resolution_id": "direction:stale"},
    }
    contribution = build_lane_contribution(
        lane_id="strategy_informed",
        contribution_state="strategy_nominated",
        authority_tier="A4",
        evidence_profile="event_catalyst",
        subject={"hypothesis_id": stale["hypothesis_id"]},
        evidence_refs=["evidence:test"],
        generation_id="generation:stale",
        observed_at="2026-08-18T00:00:00+00:00",
        expires_at=None,
        canonical_draft=stale,
    )
    store.write_jsonl("qadam_strategy_drafts_v3.jsonl", [current])
    store.write_jsonl("qadam_qeg_strategy_hypotheses.jsonl", [])
    store.write_jsonl("qadam_lane_contributions.jsonl", [contribution])
    store.write_jsonl(
        "qadam_direction_resolutions.jsonl",
        [{"direction_resolution_id": "direction:current"}],
    )

    accepted, rejections = _collect_drafts(tmp_path)

    assert [row["hypothesis_id"] for row in accepted] == ["hypothesis:current"]
    assert any(
        "stale_direction_generation_suppressed" in row["reasons"]
        for row in rejections
    )


def test_failed_compile_preserves_last_good_canonical_generation(
    tmp_path: Path,
    monkeypatch,
) -> None:
    store = AtomicArtifactStore(tmp_path)
    store.write_jsonl(
        "qadam_strategy_hypotheses_v3.jsonl",
        [{"hypothesis_id": "hypothesis:last-good"}],
    )
    store.write_json("qadam_tradeability_envelope_registry.json", {"status": "passed"})
    failed_state = {
        "envelopes": [{"envelope_id": "envelope:partial"}],
        "projections": [{"hypothesis_id": "hypothesis:partial"}],
        "rejections": [],
        "defects": [{"reasons": ["test_contract_defect"]}],
        "packet_state": {
            "packets": [],
            "rejections": [],
            "integrity": {},
            "summary": {},
        },
        "registry": {"status": "blocked"},
        "foundry": {"status": "blocked"},
        "checks": {
            "status": "blocked",
            "validation_errors": ["canonical_contract_defects_active:1"],
        },
    }
    monkeypatch.setattr(
        tradeability_pipeline,
        "build_tradeability_pipeline_state",
        lambda _settings=None: failed_state,
    )

    _, checks, errors = tradeability_pipeline.build_and_write_tradeability_pipeline(
        _settings(tmp_path)
    )

    rows = [
        row
        for row in (tmp_path / "qadam_strategy_hypotheses_v3.jsonl")
        .read_text(encoding="utf-8")
        .splitlines()
        if row.strip()
    ]
    assert "hypothesis:last-good" in rows[0]
    assert "hypothesis:partial" not in rows[0]
    assert checks["canonical_output_updated"] is False
    assert checks["last_good_generation_preserved"] is True
    assert errors == ["canonical_contract_defects_active:1"]
