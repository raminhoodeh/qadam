from __future__ import annotations

from dataclasses import replace
from pathlib import Path
from tempfile import TemporaryDirectory

import pytest
from pydantic import ValidationError

from orchestrator.config import Settings
from orchestrator.qadam_canonical_contracts import AtomicArtifactStore
from orchestrator.qadam_operator_service import SERVICE_DEFINITIONS
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
    assert "scripts/check_qadam_tradeability_migration.py" in canonical_commands
    assert "scripts/check_qadam_decision_generation.py" in router_commands
    assert "scripts/check_qadam_tradeability_consumers.py" in router_commands
