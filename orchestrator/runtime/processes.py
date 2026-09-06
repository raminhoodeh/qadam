"""Bounded script invocation with independently validated completion receipts."""

import json
import os
from pathlib import Path
import subprocess
import selectors
import signal
import sys
from tempfile import TemporaryDirectory
import time
from uuid import uuid4

from orchestrator.contracts.service import validate_command_receipt


def _terminate_group(process) -> None:
    try:
        os.killpg(process.pid, signal.SIGKILL)
    except ProcessLookupError:
        pass  # The child can exit between poll() and termination.


def _invoke(arguments: list[str], *, root: Path, environment: dict, timeout: int) -> dict:
    process = subprocess.Popen(arguments, cwd=root, env=environment, stdout=subprocess.PIPE,
                               stderr=subprocess.PIPE, start_new_session=True)
    tails = {"stdout": bytearray(), "stderr": bytearray()}
    counts = {"stdout": 0, "stderr": 0}
    deadline = time.monotonic() + timeout
    timed_out = False
    exit_seen = None
    with selectors.DefaultSelector() as selector:
        for name in tails:
            selector.register(getattr(process, name), selectors.EVENT_READ, name)
        try:
            while selector.get_map():
                now = time.monotonic()
                if now >= deadline and process.poll() is None:
                    timed_out = True
                    _terminate_group(process)
                if process.poll() is not None:
                    exit_seen = exit_seen or now
                    if now - exit_seen > 1:
                        break  # A detached descendant must not pin the dispatcher.
                for key, _ in selector.select(timeout=.05):
                    chunk = os.read(key.fileobj.fileno(), 65536)
                    if not chunk:
                        selector.unregister(key.fileobj)
                        continue
                    name = key.data
                    counts[name] += len(chunk)
                    tails[name].extend(chunk)
                    del tails[name][:-65536]
            remaining = max(.01, deadline - time.monotonic())
            try:
                process.wait(timeout=remaining)
            except subprocess.TimeoutExpired:
                timed_out = True
                _terminate_group(process)
                process.wait(timeout=5)
        finally:
            # Completion of the wrapper is not permission for its descendants
            # to keep writing after the scheduler releases the service resources.
            _terminate_group(process)
            if process.poll() is None:
                process.wait(timeout=5)
            process.stdout.close()
            process.stderr.close()
    return {"returncode": 124 if timed_out else process.returncode, "timed_out": timed_out,
            "output_byte_counts": counts,
            **{name: bytes(value).decode("utf-8", errors="replace") for name, value in tails.items()}}


def run_command(command: tuple[str, ...], timeout_seconds: int, *, root: Path, sanitize,
                require_work_result: bool | None = None) -> dict:
    if require_work_result is None:
        from orchestrator.runtime.services import SERVICE_DEFINITIONS
        terminals = {definition.command_sequence[-1][0] for definition in SERVICE_DEFINITIONS}
        require_work_result = bool(command and command[0] in terminals)
    started = time.monotonic()
    environment = {**os.environ, "QADAM_OPERATOR_DISPATCH": "1",
                   "QADAM_OPERATOR_SAFETY_MODE": "paper_only", "QADAM_LIVE_CAPITAL_ENABLED": "false"}
    run_id = str(uuid4())
    with TemporaryDirectory(prefix="qadam-command-") as temporary:
        receipt_path = Path(temporary) / "receipt.json"
        try:
            completed = _invoke(
                [sys.executable, "-m", "orchestrator.runtime.command", "--receipt", str(receipt_path),
                 "--run-id", run_id, "--", *command],
                root=root, environment=environment, timeout=timeout_seconds)
            if completed["timed_out"]:
                return {**completed, "stdout": sanitize(completed["stdout"]),
                        "stderr": f"timeout after {timeout_seconds}s; child process group terminated",
                        "duration_seconds": time.monotonic() - started, "command_receipt_valid": False}
            try:
                receipt = validate_command_receipt(json.loads(receipt_path.read_text()),
                    run_id=run_id, command=command, returncode=completed["returncode"],
                    require_work_result=require_work_result)
            except (OSError, ValueError) as error:
                return {"returncode": completed["returncode"] or 70, "stdout": sanitize(completed["stdout"]),
                        "stderr": f"command_receipt_invalid:{type(error).__name__}",
                        "duration_seconds": time.monotonic() - started, "timed_out": False,
                        "command_receipt_valid": False}
            return {"returncode": completed["returncode"], "stdout": sanitize(completed["stdout"]),
                    "stderr": sanitize(completed["stderr"]), "duration_seconds": time.monotonic() - started,
                    "output_byte_counts": completed["output_byte_counts"],
                    "timed_out": False, "command_receipt_valid": True,
                    "command_receipt": receipt.model_dump(), "work_result": receipt.work_result}
        except subprocess.TimeoutExpired:
            return {"returncode": 124, "stdout": "", "stderr": f"timeout after {timeout_seconds}s",
                    "duration_seconds": time.monotonic() - started, "timed_out": True,
                    "command_receipt_valid": False}
