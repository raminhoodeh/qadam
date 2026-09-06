"""Serialize local inference and reviewed model reloads without blocking trading."""

from contextlib import contextmanager
import fcntl
from pathlib import Path


@contextmanager
def local_model_lock(runtime: Path):
    runtime.mkdir(parents=True, exist_ok=True)
    with (runtime / ".qadam_local_model.lock").open("a+") as handle:
        acquired = False
        try:
            try:
                fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
                acquired = True
            except BlockingIOError:
                pass
            yield acquired
        finally:
            if acquired:
                fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
