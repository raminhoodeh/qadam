"""Publish declared outputs without rereading another producer's mutable files."""

from contextlib import ExitStack
from pathlib import Path
import time

from orchestrator.qadam_artifact_generations import ArtifactGenerationStore, GenerationError

MAX_CAPTURE_ATTEMPTS = 3


def publish_owned_outputs(store: ArtifactGenerationStore, outputs: dict[str, Path], *, producer, provenance):
    """Carry other owners' last verified bytes forward under a reader lease.

    An absent initial pointer means only declared outputs are available. An
    invalid existing pointer is an integrity failure, never a bootstrap excuse.
    Capture retries copy bytes only; they cannot rerun commands or broker calls.
    """
    with ExitStack() as stack:
        prior = stack.enter_context(store.lease_current()) if store.current_path.exists() else None
        carried = {
            row["name"]: prior.path / row["name"]
            for row in prior.manifest["files"]
            if row["name"] not in outputs
        } if prior else {}
        files = {**carried, **outputs}
        details = {**provenance,
                   "snapshot_scope": "declared_outputs_plus_last_verified_generation",
                   "carried_forward_generation_id": prior.generation_id if prior else None,
                   "carried_forward_artifacts": sorted(carried)}
        for attempt in range(MAX_CAPTURE_ATTEMPTS):
            try:
                return store.publish_files(files, producer=producer, provenance=details, copy_mode="copy")
            except GenerationError as exc:
                if (not str(exc).startswith("generation_source_changed_during_copy:")
                        or attempt + 1 == MAX_CAPTURE_ATTEMPTS):
                    raise
                time.sleep(0.05 * (attempt + 1))
