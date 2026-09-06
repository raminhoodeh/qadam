"""Coherent dashboard snapshots with unchanged business documents reused."""

import json
from datetime import datetime, timezone
from pathlib import Path
from tempfile import TemporaryDirectory

from orchestrator.qadam_artifact_generations import ArtifactGenerationStore, GENERATION_ROOT
from orchestrator.qadam_operator_ready_common import ATOMIC_WRITE_LOCK_DIR, write_json_atomic
from orchestrator.storage.file_lock import path_lock

RESOURCE = "dashboard-view-snapshot"
CHECK_FILE = "qadam_dashboard_projection_check.json"


def _repair_exports(runtime: Path, documents: dict[str, dict]) -> int:
    repaired = 0
    for name, document in documents.items():
        try:
            current = json.loads((runtime / name).read_text())
        except (OSError, ValueError):
            current = None
        if current != document:
            write_json_atomic(runtime / name, document)
            repaired += 1
    return repaired


def _checked(runtime: Path, generation_id: str, changed: int, repaired: int) -> dict:
    receipt = {"schema_version": "dashboard-projection-check.1", "generation_id": generation_id,
               "last_successful_check_at": datetime.now(timezone.utc).isoformat(),
               "changed_document_count": changed, "compatibility_exports_repaired": repaired}
    write_json_atomic(runtime / CHECK_FILE, receipt)
    return receipt


def _business(document: dict) -> dict:
    # Only the projection's own publication time is incidental. Source observation,
    # expiry, market-session and nested event times remain part of the identity.
    return {key: value for key, value in document.items() if key != "generated_at"}


def publish_projection(runtime: Path, documents: dict[str, dict]) -> dict:
    if not documents or any(Path(name).name != name or not isinstance(value, dict)
                            for name, value in documents.items()):
        raise ValueError("nonempty_projection_basename_documents_required")
    runtime.mkdir(parents=True, exist_ok=True)
    with path_lock(runtime / ".dashboard-view-writer", ATOMIC_WRITE_LOCK_DIR):
        store = ArtifactGenerationStore(runtime, RESOURCE)
        previous = read_projection(runtime)
        previous_documents = previous[0] if previous else {}
        changed = []
        normalized = {}
        for name, document in documents.items():
            old = previous_documents.get(name)
            if old is not None and _business(old) == _business(document):
                normalized[name] = old
            else:
                changed.append(name)
                normalized[name] = document
        removed = set(previous_documents) - set(documents)
        if previous and not changed and not removed:
            repaired = _repair_exports(runtime, normalized)
            return _checked(runtime, previous[1], 0, repaired)
        with TemporaryDirectory(prefix=".dashboard-view-", dir=runtime) as temporary:
            files = {}
            for name, document in normalized.items():
                if Path(name).name != name:
                    raise ValueError("projection_basename_required")
                target = Path(temporary) / name
                write_json_atomic(target, document)
                files[name] = target
            reference = store.publish_files(files, producer="qsase_dashboard_view_model",
                                            provenance={"schema": "dashboard-view-snapshot.1"})
        # Compatibility exports are not the multi-file publication authority.
        repaired = _repair_exports(runtime, normalized)
        store.collect(retain=3)
        return _checked(runtime, reference.generation_id, len(changed) + len(removed), repaired)


def read_projection(runtime: Path) -> tuple[dict[str, dict], str] | None:
    pointer = runtime / GENERATION_ROOT / RESOURCE / "current.json"
    if not pointer.is_file():
        return None
    store = ArtifactGenerationStore(runtime, RESOURCE)
    with store.lease_current() as reference:
        documents = {record["name"]: json.loads((reference.path / record["name"]).read_text())
                     for record in reference.manifest["files"]}
        return documents, reference.generation_id
