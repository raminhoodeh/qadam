#!/usr/bin/env python3
"""Run tests without live runtime inputs or outbound network access.

Older research tests need the committed historical JSON fixtures. Export those
from Git, not the running account, into a disposable repository-local runtime.
Use a real entrypoint so macOS multiprocessing spawn can import its main module.
"""

import os
from pathlib import Path
import socket
import subprocess
import sys
import tarfile
import tempfile

ROOT = Path(__file__).resolve().parents[1]


def _offline_connect(self, address):
    if self.family != socket.AF_UNIX:
        raise OSError("network disabled for isolated verification")
    return _CONNECT(self, address)


_CONNECT = socket.socket.connect
_CONNECT_EX = socket.socket.connect_ex


def _offline_connect_ex(self, address):
    if self.family != socket.AF_UNIX:
        raise OSError("network disabled for isolated verification")
    return _CONNECT_EX(self, address)


def main():
    sys.path.insert(0, str(ROOT))
    import pytest

    with tempfile.TemporaryDirectory(prefix=".qadam-test-", dir=ROOT) as directory:
        root = Path(directory)
        process = subprocess.Popen(["git", "archive", "HEAD", "data/runtime"], cwd=ROOT,
                                   stdout=subprocess.PIPE)
        try:
            with tarfile.open(fileobj=process.stdout, mode="r|") as archive:
                archive.extractall(root, filter="data")
        finally:
            if process.stdout is not None:
                process.stdout.close()
            result = process.wait()
        if result:
            raise RuntimeError("committed_test_fixture_export_failed")
        for key, folder in {
            "QADAM_DATA_ROOT": "data", "QADAM_STATE_ROOT": "data",
            "QADAM_RUNTIME_DIR": "data/runtime", "QADAM_RAW_PAYLOAD_DIR": "data/raw_payloads",
            "QADAM_LOCAL_BACKUP_DIR": "data/backups", "QADAM_POSTGRES_DATA_DIR": "data/postgres",
            "QADAM_CHROMA_PERSIST_DIR": "data/chroma",
        }.items():
            path = root / folder
            path.mkdir(parents=True, exist_ok=True)
            os.environ[key] = str(path)
        os.environ["QADAM_SECRETS_FILE"] = str(root / "data/runtime/absent-secrets.env")
        os.environ["QADAM_LIVE_CAPITAL_ENABLED"] = "false"
        os.environ["QADAM_TELEGRAM_DRY_RUN"] = "true"
        socket.socket.connect = _offline_connect
        socket.socket.connect_ex = _offline_connect_ex
        print("isolated_verification_network_disabled=true", flush=True)
        return pytest.main(sys.argv[1:] or ["-q", "tests"])


if __name__ == "__main__":
    raise SystemExit(main())
