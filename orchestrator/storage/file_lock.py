"""A shared path lock for replace, append and retention on the same artifact."""

from contextlib import contextmanager
import fcntl
from hashlib import sha256
from pathlib import Path


@contextmanager
def path_lock(path: Path, lock_directory: Path):
    lock_directory.mkdir(parents=True, exist_ok=True)
    name = sha256(str(path.resolve()).encode("utf-8")).hexdigest() + ".lock"
    with (lock_directory / name).open("a+b") as handle:
        fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
        try:
            yield
        finally:
            fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
