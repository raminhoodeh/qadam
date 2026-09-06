import pytest

from orchestrator.presentation.generations import publish_projection, read_projection
from orchestrator.qadam_artifact_generations import ArtifactGenerationStore


def test_no_change_reuses_business_documents_without_refreshing_evidence_time(tmp_path):
    document = {"generated_at": "2026-09-01T00:00:00Z", "observed_at": "2026-08-31T00:00:00Z", "equity": 100}
    first = publish_projection(tmp_path, {"portfolio.json": document})
    before = (tmp_path / "portfolio.json").stat().st_mtime_ns
    second = publish_projection(tmp_path, {"portfolio.json": {**document, "generated_at": "2026-09-02T00:00:00Z"}})
    assert second["generation_id"] == first["generation_id"]
    assert second["changed_document_count"] == 0
    assert (tmp_path / "portfolio.json").stat().st_mtime_ns == before
    assert read_projection(tmp_path)[0]["portfolio.json"] == document
    changed = publish_projection(tmp_path, {"portfolio.json": {**document, "observed_at": "2026-09-02T00:00:00Z"}})
    assert changed["changed_document_count"] == 1


def test_failed_publication_cannot_expose_half_a_portfolio(tmp_path, monkeypatch):
    initial = {"equity.json": {"equity": 100}, "positions.json": {"quantity": 0}}
    publish_projection(tmp_path, initial)
    def fail(*args, **kwargs):
        raise OSError("simulated disk failure before pointer commit")
    monkeypatch.setattr(ArtifactGenerationStore, "publish_files", fail)
    with pytest.raises(OSError):
        publish_projection(tmp_path, {"equity.json": {"equity": 110}, "positions.json": {"quantity": 1}})
    assert read_projection(tmp_path)[0] == initial


def test_crash_after_pointer_commit_repairs_exports_on_unchanged_retry(tmp_path, monkeypatch):
    from orchestrator.presentation import generations
    initial = {"portfolio.json": {"equity": 100}}
    generations.publish_projection(tmp_path, initial)
    updated = {"portfolio.json": {"equity": 110}}
    original = generations._repair_exports
    monkeypatch.setattr(generations, "_repair_exports", lambda *args: (_ for _ in ()).throw(OSError("crash")))
    with pytest.raises(OSError):
        generations.publish_projection(tmp_path, updated)
    assert generations.read_projection(tmp_path)[0] == updated
    monkeypatch.setattr(generations, "_repair_exports", original)
    receipt = generations.publish_projection(tmp_path, updated)
    assert receipt["changed_document_count"] == 0
    assert receipt["compatibility_exports_repaired"] == 1
    assert '110' in (tmp_path / "portfolio.json").read_text()
    assert receipt["last_successful_check_at"]


def test_removing_a_document_changes_the_coherent_generation(tmp_path):
    first = publish_projection(tmp_path, {"a.json": {"value": 1}, "b.json": {"value": 2}})
    second = publish_projection(tmp_path, {"a.json": {"value": 1}})
    assert first["generation_id"] != second["generation_id"]
    assert set(read_projection(tmp_path)[0]) == {"a.json"}


def test_dashboard_reader_uses_committed_generation_not_partially_repaired_exports(tmp_path):
    from dataclasses import replace
    from orchestrator.config import Settings
    from orchestrator.presentation.dashboard import load_dashboard_view_model
    publish_projection(tmp_path, {
        "qsase_dashboard_status.json": {"status": "fixture", "generated_at": "2026-09-06T12:00:00Z"},
        "qsase_current_portfolio.json": {"position_count": 2},
    })
    (tmp_path / "qsase_dashboard_status.json").write_text('{"status":"partial"}')
    result = load_dashboard_view_model(replace(Settings.from_env(), runtime_dir=str(tmp_path)))
    assert result["status"] == "fixture"
    assert result["source_generation_id"]


def test_invalid_rebuild_does_not_publish_or_refresh_last_good_snapshot(tmp_path, monkeypatch):
    from dataclasses import replace
    from orchestrator.config import Settings
    from orchestrator.presentation import dashboard
    first = publish_projection(tmp_path, {"qsase_dashboard_status.json": {"status": "fixture"}})
    monkeypatch.setattr(dashboard, "build_dashboard_view_model", lambda settings: {"generated_at": "2026-09-06T12:00:00Z"})
    monkeypatch.setattr(dashboard, "validate_dashboard_view_model", lambda payload: ["portfolio_mismatch"])
    _, written, errors = dashboard.build_and_write_dashboard_view_model(
        replace(Settings.from_env(), runtime_dir=str(tmp_path)))
    assert written == {}
    assert errors == ["portfolio_mismatch"]
    assert read_projection(tmp_path)[1] == first["generation_id"]
    assert 'failed' in (tmp_path / "qadam_dashboard_projection_attempt.json").read_text()
