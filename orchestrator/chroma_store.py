"""Embedded local Chroma Knowledge Graph shell."""

from __future__ import annotations

import json
import subprocess
import sys
from typing import Any

from orchestrator.config import Settings

KNOWLEDGE_COLLECTION = "qadam_knowledge_graph"


def _load_chromadb():
    try:
        import chromadb
    except ImportError as exc:
        raise RuntimeError("chromadb is not installed. Run scripts/bootstrap_runtime.sh first.") from exc
    return chromadb


def initialize_knowledge_graph(settings: Settings | None = None) -> dict[str, Any]:
    chromadb = _load_chromadb()
    settings = settings or Settings.from_env()
    client = chromadb.PersistentClient(path=settings.chroma_persist_dir)
    collection = client.get_or_create_collection(
        KNOWLEDGE_COLLECTION,
        metadata={
            "owner": "qadam",
            "phase": "foundation",
            "mode": "local_embedded",
        },
    )
    return {
        "status": "ok",
        "backend": "embedded_chroma",
        "collection": KNOWLEDGE_COLLECTION,
        "path": settings.chroma_persist_dir,
        "count": collection.count(),
    }


def knowledge_graph_health(
    settings: Settings | None = None,
    *,
    timeout_seconds: float = 5.0,
) -> dict[str, Any]:
    settings = settings or Settings.from_env()
    try:
        completed = subprocess.run(
            [
                sys.executable,
                "-m",
                "orchestrator.chroma_health_probe",
                str(settings.chroma_persist_dir),
            ],
            capture_output=True,
            check=False,
            text=True,
            timeout=timeout_seconds,
        )
    except subprocess.TimeoutExpired:
        return {
            "status": "degraded",
            "backend": "embedded_chroma",
            "collection": KNOWLEDGE_COLLECTION,
            "path": settings.chroma_persist_dir,
            "error_code": "health_check_timeout",
            "error": f"health check timed out after {timeout_seconds:g} seconds",
        }
    except Exception as exc:  # noqa: BLE001 - health should report process failures
        return {
            "status": "degraded",
            "backend": "embedded_chroma",
            "collection": KNOWLEDGE_COLLECTION,
            "path": settings.chroma_persist_dir,
            "error_code": "health_check_failed",
            "error": str(exc),
        }

    if completed.returncode != 0:
        error = (completed.stderr or completed.stdout or "health probe failed").strip()
        return {
            "status": "degraded",
            "backend": "embedded_chroma",
            "collection": KNOWLEDGE_COLLECTION,
            "path": settings.chroma_persist_dir,
            "error_code": "health_check_failed",
            "error": error[:500],
        }

    try:
        payload = json.loads(completed.stdout)
    except json.JSONDecodeError:
        return {
            "status": "degraded",
            "backend": "embedded_chroma",
            "collection": KNOWLEDGE_COLLECTION,
            "path": settings.chroma_persist_dir,
            "error_code": "invalid_health_payload",
            "error": "health probe did not return valid JSON",
        }
    return payload
