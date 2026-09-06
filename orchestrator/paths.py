"""Locate reviewed resources independently of module depth or working directory."""

import os
from pathlib import Path


def project_root() -> Path:
    configured = os.environ.get("QADAM_PROJECT_ROOT")
    if configured:
        candidate = Path(configured).expanduser()
        if not candidate.is_absolute():
            raise ValueError("QADAM_PROJECT_ROOT_must_be_absolute")
        candidate = candidate.resolve()
        if not (candidate / "config").is_dir() or not (candidate / "pyproject.toml").is_file():
            raise ValueError("QADAM_PROJECT_ROOT_missing_reviewed_resources")
        return candidate
    for candidate in Path(__file__).resolve().parents:
        if (candidate / "pyproject.toml").is_file() and (candidate / "config").is_dir():
            return candidate
    raise RuntimeError("installed_qadam_requires_explicit_QADAM_PROJECT_ROOT")
