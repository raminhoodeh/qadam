from dataclasses import replace
import json

import pytest

from orchestrator.config import Settings
from orchestrator.research_goal import (
    ResearchGoalStore,
    build_research_goal_from_observation,
    research_goal_summary,
)


def goal(index):
    return build_research_goal_from_observation(
        summary=f"Oil supply disruption observation {index}",
        source_event_refs=(f"source:{index}",),
        origin="live_source",
    ).to_dict()


def test_full_summary_validates_history_once(tmp_path, monkeypatch):
    settings = replace(Settings.from_env(), runtime_dir=str(tmp_path))
    path = tmp_path / "research_goals.jsonl"
    path.write_text("\n".join(json.dumps(goal(i)) for i in range(3)) + "\n")
    original = ResearchGoalStore.read
    calls = []

    def read_once(store):
        calls.append(store.path)
        return original(store)

    monkeypatch.setattr(ResearchGoalStore, "read", read_once)
    summary = research_goal_summary(settings, limit=2)
    assert summary["status"] == "ok"
    assert summary["goal_record_count"] == 3
    assert len(summary["recent_goals"]) == 2
    assert len(calls) == 1


def test_recent_projection_does_not_replay_or_certify_old_history(tmp_path, monkeypatch):
    settings = replace(Settings.from_env(), runtime_dir=str(tmp_path))
    path = tmp_path / "research_goals.jsonl"
    path.write_text('{"broken":}\n' * 20_000
                    + "\n".join(json.dumps(goal(i)) for i in range(2)) + "\n")
    monkeypatch.setattr(ResearchGoalStore, "read", lambda *_: pytest.fail("full journal replay"))
    summary = research_goal_summary(settings, limit=2, history_limit=2)
    assert summary["status"] == "ok"
    assert summary["goal_record_count"] == 2
    assert summary["history_scope"] == "recent_journal_window"
    assert summary["full_history_validated"] is False
    assert summary["history_record_limit"] == 2
    assert len(summary["recent_goals"]) == 2
    assert all(not row["execution_allowed"] for row in summary["recent_goals"])
    monkeypatch.undo()
    assert ResearchGoalStore(settings=settings).health()["status"] == "degraded"


@pytest.mark.parametrize("invalid", ['{"partial":', 'null', '{"execution_allowed":true}'])
def test_recent_corruption_cannot_be_reported_healthy(tmp_path, invalid):
    settings = replace(Settings.from_env(), runtime_dir=str(tmp_path))
    (tmp_path / "research_goals.jsonl").write_text(json.dumps(goal(1)) + "\n" + invalid)
    summary = research_goal_summary(settings, limit=2, history_limit=2)
    assert summary["status"] == "degraded"
    assert summary["recent_goals"] == []
    assert summary["full_history_validated"] is False


def test_recent_projection_has_a_hard_byte_budget(tmp_path):
    settings = replace(Settings.from_env(), runtime_dir=str(tmp_path))
    (tmp_path / "research_goals.jsonl").write_bytes(b"x" * (5 * 1024 * 1024))
    summary = research_goal_summary(settings, limit=2, history_limit=2)
    assert summary["status"] == "degraded"
    assert "history_tail_exceeds_byte_budget" in summary["error"]


def test_cockpit_requests_a_bounded_goal_projection(tmp_path, monkeypatch):
    import orchestrator.cockpit_status as cockpit

    class ProjectionReached(Exception):
        pass

    for name in (
        "shadow_intelligence_summary", "paper_account_shadow_context", "signal_integrity_summary",
        "quantum_oracle_summary", "quantum_provider_readiness", "_safe_phase2_shadow_cycle",
    ):
        monkeypatch.setattr(cockpit, name, lambda *_: {})
    for name in ("ShadowSignalStore", "LocalResearchAssessmentStore", "StrategyLeadShadowStore"):
        monkeypatch.setattr(cockpit, name, lambda **_: None)

    def bounded(**kwargs):
        assert kwargs["limit"] == 8
        assert kwargs["history_limit"] == 256
        raise ProjectionReached

    monkeypatch.setattr(cockpit, "research_goal_summary", bounded)
    with pytest.raises(ProjectionReached):
        cockpit._build_cognition(replace(Settings.from_env(), runtime_dir=str(tmp_path)))
