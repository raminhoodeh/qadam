"""Stat-validated source manifests, shared across service revalidation checks."""

from functools import lru_cache
from hashlib import sha256
from pathlib import Path


def _signature(path: Path) -> tuple[int, ...]:
    stat = path.stat()
    return (stat.st_dev, stat.st_ino, stat.st_size, stat.st_mtime_ns, stat.st_ctime_ns)


@lru_cache(maxsize=4096)
def _digest(path: Path, signature: tuple[int, ...]) -> str:
    value = sha256(path.read_bytes()).hexdigest()
    if _signature(path) != signature:
        raise OSError(f"reviewed_source_changed_during_read:{path.name}")
    return value


def reviewed_source_state(root: Path) -> list[dict]:
    paths = set((root / "orchestrator").rglob("*.py"))
    paths.update((root / "scripts").rglob("*.py"))
    for extension in ("*.json", "*.toml", "*.yaml", "*.yml"):
        paths.update((root / "config").rglob(extension))
    paths.update(path for name in ("pyproject.toml", "requirements.txt", "requirements.lock", "uv.lock")
                 if (path := root / name).is_file())
    return [{"path": str(path.relative_to(root)), "size": (signature := _signature(path))[2],
             "sha256": _digest(path.resolve(), signature)} for path in sorted(paths)]
