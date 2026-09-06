"""Run an approved script and persist a bound receipt independently of stdout."""

import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import runpy
import sys
import traceback

from orchestrator.contracts.service import CommandReceipt, command_digest


def report_work_result(payload: dict, errors: list | tuple = ()) -> None:
    destination = os.environ.get("QADAM_COMMAND_WORK_RESULT")
    if not destination or os.environ.get("QADAM_COMMAND_RECEIPT_PID") != str(os.getpid()):
        return
    # Only the explicit boundary fields travel to the scheduler, not raw evidence.
    keys = ("status", "material_change_detected", "reason", "progress_cursor", "next_due_at")
    result = {key: payload[key] for key in keys if key in payload}
    result["validation_error_count"] = len(errors)
    _write(Path(destination), result)


def _write(path: Path, payload: dict) -> None:
    temporary = path.with_suffix(".tmp")
    with temporary.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, allow_nan=False)
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(temporary, path)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--receipt", required=True)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("command", nargs=argparse.REMAINDER)
    args = parser.parse_args()
    command = args.command[1:] if args.command[:1] == ["--"] else args.command
    if not command:
        parser.error("approved command required")
    receipt_path = Path(args.receipt)
    work_path = receipt_path.with_suffix(".work.json")
    os.environ["QADAM_COMMAND_WORK_RESULT"] = str(work_path)
    os.environ["QADAM_COMMAND_RECEIPT_PID"] = str(os.getpid())
    started = datetime.now(timezone.utc).isoformat()
    returncode = 0
    sys.argv = command
    try:
        runpy.run_path(command[0], run_name="__main__")
    except SystemExit as error:
        returncode = error.code if isinstance(error.code, int) else (0 if error.code is None else 1)
    except BaseException:
        traceback.print_exc()
        returncode = 1
    work = json.loads(work_path.read_text()) if work_path.is_file() else {}
    receipt = CommandReceipt(run_id=args.run_id, command_digest=command_digest(command),
        started_at=started, completed_at=datetime.now(timezone.utc).isoformat(),
        returncode=returncode, state="completed" if returncode == 0 else "failed", work_result=work)
    _write(receipt_path, receipt.model_dump())
    return returncode


if __name__ == "__main__":
    raise SystemExit(main())
