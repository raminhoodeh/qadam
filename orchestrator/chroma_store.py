"""Embedded local Chroma Knowledge Graph shell."""

from __future__ import annotations

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


def knowledge_graph_health(settings: Settings | None = None) -> dict[str, Any]:
    try:
        return initialize_knowledge_graph(settings)
    except Exception as exc:  # noqa: BLE001 - health should report dependency/runtime failures
        settings = settings or Settings.from_env()
        return {
            "status": "degraded",
            "backend": "embedded_chroma",
            "collection": KNOWLEDGE_COLLECTION,
            "path": settings.chroma_persist_dir,
            "error": str(exc),
        }
