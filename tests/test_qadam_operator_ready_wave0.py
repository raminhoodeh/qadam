from __future__ import annotations

from dataclasses import asdict
from pathlib import Path
import sys

import pytest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from orchestrator.qadam_canonical_contracts import (  # noqa: E402
    AtomicArtifactStore,
    PaperOpsHandoff,
    sample_records,
    validate_canonical_record,
)
from orchestrator.qadam_characterization_harness import (  # noqa: E402
    validate_execution_route,
    validate_point_in_time_record,
    validate_provenance_record,
)
from orchestrator.qadam_decision_execution_boundaries import (  # noqa: E402
    PaperOpsHandoffEnvelope,
    validate_paperops_handoff,
)
from orchestrator.qadam_dynamic_plan import (  # noqa: E402
    DynamicPlanError,
    STATUS_END,
    STATUS_START,
    normative_plan_hash,
    split_plan,
)
from orchestrator.qadam_operator_ready_common import (  # noqa: E402
    authority_flags,
    validate_authority,
)
from orchestrator.qadam_refactor_baseline import (  # noqa: E402
    DASHBOARD_RENDERER,
    parse_dashboard_navigation,
)


def test_dynamic_status_is_excluded_from_normative_hash() -> None:
    first = f"before\n{STATUS_START}\nfirst\n{STATUS_END}\nafter\n"
    second = f"before\n{STATUS_START}\nsecond\n{STATUS_END}\nafter\n"
    assert normative_plan_hash(first) == normative_plan_hash(second)


def test_dynamic_plan_rejects_missing_markers() -> None:
    with pytest.raises(DynamicPlanError, match="dynamic_status_markers_invalid"):
        split_plan("no controlled status block")


def test_dashboard_navigation_parser_reads_current_grouped_routes() -> None:
    modules = parse_dashboard_navigation(DASHBOARD_RENDERER.read_text(encoding="utf-8"))
    routes = [route for module in modules for route in module["routes"]]
    assert [module["module_id"] for module in modules] == [
        "fund",
        "observe",
        "patterns",
        "decide",
        "trade",
        "learn",
        "system",
    ]
    assert len(routes) == 12
    assert routes[0] == "fund/portfolio"
    assert routes[-1] == "system/overview"


def test_atomic_store_confines_paths_and_round_trips(tmp_path: Path) -> None:
    store: AtomicArtifactStore[dict] = AtomicArtifactStore(tmp_path)
    store.write_json("record.json", {"state": "safe"})
    assert store.read_json("record.json") == {"state": "safe"}
    with pytest.raises(ValueError, match="artifact_name_must_be_basename"):
        store.write_json("../escape.json", {"unsafe": True})


def test_all_canonical_sample_records_validate() -> None:
    records = sample_records()
    assert len(records) == 15
    assert all(validate_canonical_record(record) == [] for record in records)


def test_canonical_handoff_cannot_create_order() -> None:
    handoff = PaperOpsHandoff(
        record_id="fixture:handoff",
        generated_at="2026-01-01T00:00:00+00:00",
        origin_class="fixture",
        order_created=True,
    ).to_dict()
    assert "canonical_handoff_created_order" in validate_canonical_record(handoff)


def test_characterization_rejects_leakage_and_fixture_proof() -> None:
    assert "future_information_leakage" in validate_point_in_time_record(
        {
            "available_at": "2026-01-02T00:00:00+00:00",
            "decision_at": "2026-01-01T00:00:00+00:00",
        }
    )
    errors = validate_provenance_record(
        {
            "origin_class": "fixture",
            "fixture": True,
            "evidence_eligible": True,
            "proof_eligible": True,
        }
    )
    assert "fixture_marked_evidence_eligible" in errors
    assert "nonproof_origin_marked_proof_eligible:fixture" in errors


def test_execution_boundaries_reject_live_route() -> None:
    errors = validate_execution_route(
        {
            "live_capital_enabled": True,
            "broker_route": "live_endpoint",
            "direct_broker_call_allowed": True,
            "qctrl_bypass_allowed": True,
        }
    )
    assert len(errors) == 4


def test_paperops_handoff_requires_every_guard() -> None:
    safe = PaperOpsHandoffEnvelope(
        handoff_id="fixture:handoff",
        setup_id="fixture:setup",
        research_goal_id="fixture:goal",
        candidate_identity="fixture:candidate",
        idempotency_material="fixture:idempotency",
        instrument="SPY",
        direction="watch",
        source_quorum_passed=True,
        akber_passed=True,
        risk_approved=True,
        duplicate_exposure_conflict=False,
        daily_drawdown_breached=False,
        qctrl_consultation_clear=True,
    )
    assert validate_paperops_handoff(safe) == []
    unsafe = PaperOpsHandoffEnvelope(
        **{
            **asdict(safe),
            "duplicate_exposure_conflict": True,
            "qctrl_consultation_clear": False,
        }
    )
    errors = validate_paperops_handoff(unsafe)
    assert "paperops_handoff_duplicate_exposure" in errors
    assert "paperops_handoff_qctrl_not_clear" in errors


def test_common_authority_rejects_live_capital() -> None:
    unsafe = authority_flags()
    unsafe["live_capital_enabled"] = True
    assert "wave0_forbidden_true:live_capital_enabled" in validate_authority(
        unsafe,
        prefix="wave0",
    )
