"""Parse job state before diagnostic output is truncated or persisted."""

from typing import Any, Mapping
import re


def launchd_state(label: str, result: Mapping[str, Any]) -> dict[str, Any]:
    loaded = result.get("returncode") == 0
    state = None
    pid = None
    depth = 0
    for line in str(result.get("stdout") or "").splitlines():
        stripped = line.strip()
        # A launchctl job is at depth one; nested coalition states are unrelated.
        if loaded and depth <= 1:
            match = re.fullmatch(r"state = ([a-zA-Z][a-zA-Z -]*)", stripped)
            if match and state is None:
                state = match.group(1)
            match = re.fullmatch(r"pid = ([0-9]+)", stripped)
            if match and pid is None:
                pid = int(match.group(1))
        if stripped.endswith("{"):
            depth += 1
        elif stripped == "}":
            depth = max(0, depth - 1)
    return {
        "label": label,
        "loaded": loaded,
        "state_known": loaded and state is not None,
        "state": state or "unknown",
        "running": loaded and state == "running",
        "pid": pid,
        "probe_returncode": result.get("returncode"),
    }
