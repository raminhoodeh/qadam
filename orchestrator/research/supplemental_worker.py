"""Isolate third-party read-only libraries behind a hard wall-clock deadline."""

import contextlib
import io
import json
from pathlib import Path
import subprocess
import sys


def collect(source_key, *, timeout=45):
    if source_key not in {"yahoo_finance", "tradingview_mcp"}:
        raise ValueError("unknown_supplemental_source")
    try:
        process = subprocess.run(
            [sys.executable, "-m", __name__, source_key],
            cwd=Path(__file__).resolve().parents[2], capture_output=True, text=True, timeout=timeout,
        )
        if process.returncode:
            raise ValueError("supplemental_worker_failed")
        return json.loads(process.stdout)
    except (subprocess.TimeoutExpired, ValueError):
        return {"events": [], "degraded": True, "degraded_reason": "supplemental_worker_timeout_or_failure",
                "raw_archive_path": None}


def main():
    from orchestrator.yahoo_finance_adapter import fetch_yahoo_finance_live
    from orchestrator.tradingview_mcp_adapter import fetch_tradingview_mcp_live

    fetcher = {"yahoo_finance": fetch_yahoo_finance_live, "tradingview_mcp": fetch_tradingview_mcp_live}[sys.argv[1]]
    # Third-party diagnostic output must not corrupt the envelope protocol.
    with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
        payload = fetcher()
    print(json.dumps(payload))


if __name__ == "__main__":
    main()
