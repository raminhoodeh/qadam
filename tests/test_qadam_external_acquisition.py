from __future__ import annotations

from dataclasses import replace
import json
from pathlib import Path
import shutil

from orchestrator.config import Settings
import orchestrator.qadam_external_acquisition as acquisition


ROOT = Path(__file__).resolve().parents[1]


def _settings(runtime: Path) -> Settings:
    return replace(Settings.from_env(), runtime_dir=str(runtime))


def test_real_network_receipt_survives_offline_validation_and_respects_limit(
    tmp_path: Path, monkeypatch
) -> None:
    fake_root = tmp_path / "repo"
    config = fake_root / "config"
    config.mkdir(parents=True)
    shutil.copy(ROOT / "config/qadam_agent_reach_command_policy.json", config)
    shutil.copy(ROOT / "config/qadam_external_origin_registry.json", config)
    runtime = fake_root / "data/runtime"
    runtime.mkdir(parents=True)
    research = fake_root / "data/research/qadam_external_evidence"

    calls: list[str] = []

    def fake_worker(request, _spool, _policy):
        calls.append(str(request["origin_id"]))
        return {
            "state": "retrieved",
            "request_id": request["request_id"],
            "retrieved_at": "2026-08-15T12:00:00+00:00",
            "final_url": request["url"],
            "content_utf8": "One bounded official research document.",
            "content_type": "text/plain",
            "content_sha256": "a" * 64,
            "byte_count": 39,
            "etag": '"official-v1"',
            "last_modified": "Fri, 15 Aug 2026 12:00:00 GMT",
        }

    monkeypatch.setattr(acquisition, "repo_root", lambda: fake_root)
    monkeypatch.setattr(acquisition, "research_root", lambda: research)
    monkeypatch.setattr(acquisition, "_run_worker", fake_worker)

    online, online_errors = acquisition.run_external_acquisition(
        _settings(runtime), allow_network=True, max_documents=1
    )
    assert online_errors == []
    assert online["ever_completed_real_network_fetch"] is True
    assert online["new_document_count"] == 1
    assert len(calls) == 1

    offline, offline_errors = acquisition.run_external_acquisition(
        _settings(runtime), allow_network=False
    )
    assert offline_errors == []
    assert offline["status"] == "ready_network_not_requested"
    assert offline["ever_completed_real_network_fetch"] is True
    assert offline["last_successful_network_at"] == online["last_successful_network_at"]
    health = json.loads(
        (runtime / "qadam_external_channel_health.json").read_text(encoding="utf-8")
    )
    first_channel = next(
        row for row in health["channels"] if row["origin_id"] == calls[0]
    )
    assert first_channel["etag"] == '"official-v1"'
    assert first_channel["last_network_state"] == "retrieved"
