#!/usr/bin/env python3
"""Read-only captured-input dashboard characterization; no operational authority.

Run this script using each checkout's interpreter import path and the same private
capture. The output is an engineering measurement, not a market observation.
"""

import argparse
from contextlib import closing
import cProfile
from dataclasses import replace
from datetime import datetime
import hashlib
import json
import os
from pathlib import Path
import resource
import statistics
import sqlite3
import sys
import time
import tracemalloc


def _deny_effects(event, args):
    if event in {"socket.connect", "socket.bind", "socket.getaddrinfo", "subprocess.Popen", "os.system",
                 "os.posix_spawn", "os.fork", "os.exec"}:
        raise RuntimeError("read_only_replay_external_effect_denied:" + event)
    if event == "sqlite3.connect" and not str(args[0]).endswith("?mode=ro"):
        raise RuntimeError("read_only_replay_writable_database_denied")
    if event == "open":
        name = Path(str(args[0])).name.lower()
        if name.startswith(".env") or name.endswith(".env") or name in {"secrets.json", "credentials.json"}:
            raise RuntimeError("read_only_replay_credential_file_denied")
        mode, flags = args[1:3]
        if (isinstance(mode, str) and any(char in mode for char in "wax+")) or (
                isinstance(flags, int) and flags & (os.O_WRONLY | os.O_RDWR | os.O_CREAT | os.O_TRUNC)):
            raise RuntimeError("read_only_replay_file_write_denied")
    if event in {"os.remove", "os.rename", "os.mkdir", "os.rmdir", "os.truncate"}:
        raise RuntimeError("read_only_replay_file_mutation_denied:" + event)


def _replay_environment(environment, checkout, runtime):
    allowed = {"PATH", "HOME", "LANG", "LC_ALL", "TMPDIR", "TZ", "PYTHONIOENCODING"}
    return {**{key: value for key, value in environment.items() if key in allowed},
        "QADAM_RUNTIME_DIR": str(runtime), "QADAM_SECRETS_FILE": "/nonexistent",
        "QADAM_PROJECT_ROOT": str(checkout), "QADAM_MODE": "paper",
        "QADAM_LIVE_CAPITAL_ENABLED": "false", "QADAM_ALPACA_PAPER_SUBMIT_ENABLED": "false",
        "QADAM_ALPACA_PAPER_EXIT_ENABLED": "false"}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--checkout", required=True, type=Path)
    parser.add_argument("--capture", required=True, type=Path)
    parser.add_argument("--samples", type=int, default=5)
    parser.add_argument("--component", choices=("dashboard", "canonical_tradeability", "foundry", "exit_selection"), default="dashboard")
    parser.add_argument("--ledger-copy", type=Path)
    parser.add_argument("--profile-calls", action="store_true")
    args = parser.parse_args()
    if not 1 <= args.samples <= 30:
        parser.error("samples must be between 1 and 30")
    manifest = json.loads((args.capture / "capture-manifest.json").read_text())
    if manifest.get("fixture_only") is not True or manifest.get("authority") != "none":
        parser.error("requires a captured fixture with no authority")
    runtime = (args.capture / "data" / "runtime").resolve()
    if list(runtime.glob("*.sqlite*")) or list(runtime.glob("*.env")):
        parser.error("capture must not contain a database or credentials")
    sys.dont_write_bytecode = True
    sys.path.insert(0, str(args.checkout.resolve()))
    environment = _replay_environment(os.environ, args.checkout.resolve(), runtime)
    os.environ.clear()
    os.environ.update(environment)
    sys.addaudithook(_deny_effects)
    from orchestrator.config import Settings
    from orchestrator import qsase_dashboard_view_model as dashboard
    settings = replace(Settings.from_env(), runtime_dir=str(runtime))
    # Frozen time is restricted to this explicitly isolated characterization.
    frozen = datetime.fromisoformat(manifest["captured_at"])
    dashboard._now = lambda: frozen
    if args.component == "foundry":
        from orchestrator import qadam_strategy_foundry_v3 as foundry
        foundry.now_iso = lambda: frozen.isoformat()
    if args.component == "exit_selection":
        if not args.ledger_copy or args.ledger_copy.name != "isolated-control-plane.sqlite3":
            parser.error("exit selection requires the explicitly isolated migration copy")
        from orchestrator.qadam_operating_ledger import OperatingLedger

        class ReadOnlyStore:
            def connect(self):
                connection = sqlite3.connect(args.ledger_copy.resolve().as_uri() + "?mode=ro", uri=True)
                connection.row_factory = sqlite3.Row
                connection.execute("PRAGMA query_only=ON")
                return closing(connection)

        ledger = OperatingLedger(settings, store=ReadOnlyStore())
    if args.component == "canonical_tradeability":
        from orchestrator import qadam_tradeability_pipeline as pipeline
        from orchestrator import qadam_tradeability_capabilities as capabilities
        pipeline.now_iso = lambda: frozen.isoformat()
        capabilities.now_iso = lambda: frozen.isoformat()
        try:
            from orchestrator.decisions import draft_selection
            draft_selection.now_iso = lambda: frozen.isoformat()
        except ImportError:
            pass  # Baseline has no extracted selection module.
        if hasattr(pipeline, "build_and_write_capability_matrix"):
            # Suppress only the baseline publication adapter. Both sides still
            # execute the real capability producer and validator on the capture.
            def read_only_capability(settings):
                matrix = capabilities.build_capability_matrix(settings)
                errors = capabilities.validate_capability_matrix(matrix)
                return matrix, {"status": "blocked" if errors else "passed"}, errors
            pipeline.build_and_write_capability_matrix = read_only_capability
    def build():
        if args.component == "dashboard":
            return dashboard.build_dashboard_view_model(settings)
        if args.component == "foundry":
            return foundry.build_strategy_foundry_v3_state(settings, generated_at=frozen.isoformat())
        if args.component == "exit_selection":
            return {"candidates": ledger.due_exit_candidates(current_time=frozen)}
        return pipeline.build_tradeability_pipeline_state(settings)

    timings, cpus = [], []
    tracemalloc.start()
    for _ in range(args.samples):
        started, cpu = time.perf_counter(), time.process_time()
        payload = build()
        timings.append(time.perf_counter() - started)
        cpus.append(time.process_time() - cpu)
    _, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    callers = []
    if args.profile_calls:
        profiler = cProfile.Profile()
        profiler.runcall(build)
        stats = profiler.getstats()
        checkout = str(args.checkout.resolve()) + "/"
        for entry in stats:
            code = entry.code
            if isinstance(code, str) or not code.co_filename.startswith(checkout):
                continue
            callers.append({"file": code.co_filename.removeprefix(checkout), "line": code.co_firstlineno,
                "function": code.co_name, "calls": entry.callcount,
                "inclusive_seconds": entry.totaltime, "exclusive_seconds": entry.inlinetime,
                "callees": sorted({sub.code.co_name for sub in (entry.calls or [])
                    if not isinstance(sub.code, str) and sub.code.co_filename.startswith(checkout)})})
        callers.sort(key=lambda row: (-row["inclusive_seconds"], row["file"], row["line"]))
    # Compare economic and lifecycle fields, not publication timestamps or new UI sections.
    financial = {key: payload.get(key) for key in (
        "current_portfolio", "trading_history", "portfolio_value",
        "current_position_count", "trading_history_row_count", "source_row_count",
        "trading_universe_row_count")}
    if args.component == "canonical_tradeability":
        financial = {key: payload.get(key) for key in (
            "envelopes", "projections", "rejections", "defects", "packet_state", "registry", "foundry", "checks")}
    elif args.component in {"foundry", "exit_selection"}:
        financial = payload

    def stable(value):
        if isinstance(value, dict):
            return {key: stable(item) for key, item in value.items()
                    if key not in {"generated_at", "age_seconds", "mtime", "runtime_dir"}}
        if isinstance(value, list):
            return [stable(item) for item in value]
        return value

    financial = stable(financial)
    errors = (dashboard.validate_dashboard_view_model(payload) if args.component == "dashboard"
              else foundry.validate_strategy_foundry_v3_state(payload) if args.component == "foundry"
              else payload["checks"]["validation_errors"] if args.component == "canonical_tradeability" else [])
    print(json.dumps({
        "fixture_only": True, "component": args.component,
        "broker_write_count": 0, "network_calls_allowed": False,
        "capture_at": manifest["captured_at"], "sample_count": args.samples,
        "duration_p50_seconds": statistics.median(timings),
        "duration_p95_seconds": sorted(timings)[max(0, int(.95 * len(timings) + .9999) - 1)],
        "cpu_p50_seconds": statistics.median(cpus), "python_peak_allocation_bytes": peak,
        "process_peak_rss_native_units": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
        "rss_units": "bytes on macOS; KiB on Linux",
        "validation_errors": errors,
        "dynamic_call_inventory": callers,
        "dynamic_inventory_scope": "Only functions exercised by this captured input; absence is not proof of dead code",
        ("financial_projection_sha256" if args.component == "dashboard" else "comparison_projection_sha256"):
            hashlib.sha256(json.dumps(financial, sort_keys=True).encode()).hexdigest(),
        ("financial_projection" if args.component == "dashboard" else "comparison_projection"): financial,
        "scope": "bounded captured producer replay, not full application or economic performance",
    }, sort_keys=True))
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
