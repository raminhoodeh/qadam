"""Local storage and service health checks for the Qadam foundation."""

from __future__ import annotations

import socket
from pathlib import Path
from typing import Any

from orchestrator.config import Settings


def _resolve(path: str | Path) -> Path:
    candidate = Path(path)
    if candidate.is_absolute():
        return candidate
    return Path.cwd() / candidate


def _directory_health(key: str, label: str, path: str | Path) -> dict[str, Any]:
    resolved = _resolve(path)
    exists = resolved.exists()
    is_dir = resolved.is_dir()
    return {
        "key": key,
        "label": label,
        "path": str(resolved),
        "exists": exists,
        "is_directory": is_dir,
        "status": "ok" if exists and is_dir else "missing",
    }


def _tcp_health(
    key: str,
    label: str,
    host: str,
    port: int,
    *,
    required_for: str,
    fallback: str,
    timeout_seconds: float = 0.35,
) -> dict[str, Any]:
    try:
        with socket.create_connection((host, port), timeout=timeout_seconds):
            reachable = True
    except OSError:
        reachable = False

    return {
        "key": key,
        "label": label,
        "host": host,
        "port": port,
        "status": "reachable" if reachable else "not_running",
        "reachable": reachable,
        "required_for": required_for,
        "fallback": fallback,
    }


def local_store_health(settings: Settings | None = None) -> dict[str, Any]:
    settings = settings or Settings.from_env()
    directories = [
        _directory_health("data_root", "Data Root", settings.data_root),
        _directory_health("raw_payloads", "Raw Payload Archive", settings.raw_payload_dir),
        _directory_health("runtime", "Runtime State", settings.runtime_dir),
        _directory_health("postgres", "Postgres Data", settings.postgres_data_dir),
        _directory_health("chroma", "Chroma Persistence", settings.chroma_persist_dir),
        _directory_health("backups", "Local Backups", settings.local_backup_dir),
    ]
    services = [
        _tcp_health(
            "postgres",
            "Postgres/Timescale Event Log",
            "127.0.0.1",
            5432,
            required_for="durable_event_log",
            fallback="local_jsonl_event_log",
        ),
        _tcp_health(
            "chroma",
            "ChromaDB Knowledge Graph",
            settings.chroma_host,
            settings.chroma_port,
            required_for="knowledge_graph",
            fallback="empty_knowledge_graph_shell",
        ),
    ]

    missing_directories = [item for item in directories if item["status"] != "ok"]
    offline_services = [item for item in services if not item["reachable"]]
    status = "ok"
    if missing_directories:
        status = "error"
    elif offline_services:
        status = "degraded"

    return {
        "status": status,
        "directories": directories,
        "services": services,
        "summary": {
            "directory_count": len(directories),
            "missing_directories": len(missing_directories),
            "service_count": len(services),
            "reachable_services": sum(1 for item in services if item["reachable"]),
            "offline_services": [item["key"] for item in offline_services],
        },
    }
