from __future__ import annotations

import json
import subprocess
from types import SimpleNamespace

from orchestrator import chroma_store


def test_knowledge_graph_health_returns_success(monkeypatch) -> None:
    expected = {"status": "ok", "backend": "embedded_chroma"}
    completed = subprocess.CompletedProcess(
        args=["probe"],
        returncode=0,
        stdout=json.dumps(expected),
        stderr="",
    )
    monkeypatch.setattr(chroma_store.subprocess, "run", lambda *_args, **_kwargs: completed)

    settings = SimpleNamespace(chroma_persist_dir="data/chroma")
    assert chroma_store.knowledge_graph_health(settings, timeout_seconds=0.1) == expected


def test_knowledge_graph_health_bounds_a_stalled_dependency(monkeypatch) -> None:
    def stalled_probe(*_args, **_kwargs):
        raise subprocess.TimeoutExpired(cmd=["probe"], timeout=0.02)

    monkeypatch.setattr(chroma_store.subprocess, "run", stalled_probe)

    settings = SimpleNamespace(chroma_persist_dir="data/chroma")
    health = chroma_store.knowledge_graph_health(settings, timeout_seconds=0.02)

    assert health["status"] == "degraded"
    assert health["error_code"] == "health_check_timeout"
    assert "0.02 seconds" in health["error"]
