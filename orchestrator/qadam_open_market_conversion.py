"""Atomic same-generation coordinator for the guarded paper conversion path."""

from __future__ import annotations

from datetime import datetime, timezone
import fcntl
import os
from pathlib import Path
import subprocess
import sys
import time
from typing import Any

from orchestrator.config import Settings
from orchestrator.qadam_canonical_contracts import AtomicArtifactStore
from orchestrator.qadam_ef11_open_market_conversion import (
    CONVERSION_CYCLES_ARTIFACT,
    CONVERSION_STATUS_ARTIFACT,
    DAILY_SUMMARY_ARTIFACT,
    append_conversion_cycles,
    build_and_write_ef11_state,
    primary_root_cause,
)
from orchestrator.qadam_market_session_truth import build_and_write_market_clock_truth
from orchestrator.qadam_operator_ready_common import (
    authority_flags,
    file_sha256,
    now_iso,
    read_json,
    read_jsonl,
    runtime_dir,
    sha256_json,
)

SCHEMA_VERSION = "qadam_open_market_conversion.v1"
GENERATION_ARTIFACT = "qadam_open_market_conversion_generation.json"
RECEIPTS_ARTIFACT = "qadam_open_market_conversion_receipts.jsonl"
FAILURES_ARTIFACT = "qadam_open_market_conversion_failures.jsonl"
LOCK_FILENAME = ".qadam_open_market_conversion.lock"

PIPELINE_COMMANDS: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("market_context", ("scripts/check_market_context_packet.py",)),
    ("strategy_translation", ("scripts/check_qadam_strategy_translation.py",)),
    ("decision_evidence", ("scripts/check_qadam_decision_evidence_packets.py",)),
    ("akber_evidence_fit", ("scripts/check_qadam_akber_evidence_fit.py",)),
    ("akber", ("scripts/check_qadam_akber_filter_v3.py",)),
    ("shadow", ("scripts/run_qadam_forward_shadow.py", "--once", "--allow-network")),
    ("risk", ("scripts/check_qadam_portfolio_risk_engine.py",)),
    ("router", ("scripts/check_qadam_router_v3_paperops.py",)),
)

OUTPUT_ARTIFACTS = {
    "market_context": "market_context_packet.json",
    "strategy_translation": "qadam_strategy_hypotheses_v3.jsonl",
    "decision_evidence": "qadam_decision_evidence_packets.jsonl",
    "akber_evidence_fit": "qadam_akber_evidence_fit_checks.json",
    "akber": "qadam_akber_filter_v3_results.jsonl",
    "shadow": "qadam_forward_shadow_decisions.jsonl",
    "risk": "qadam_position_size_proposals.jsonl",
    "router": "qadam_router_v3_decisions.jsonl",
}


def _run_command(
    command: tuple[str, ...],
    *,
    timeout_seconds: int,
) -> dict[str, Any]:
    started = time.monotonic()
    env = os.environ.copy()
    env.update(
        {
            "QADAM_OPERATOR_DISPATCH": "1",
            "QADAM_OPERATOR_SAFETY_MODE": "paper_only",
            "QADAM_LIVE_CAPITAL_ENABLED": "false",
        }
    )
    try:
        result = subprocess.run(
            [sys.executable, *command],
            cwd=Path(__file__).resolve().parents[1],
            env=env,
            capture_output=True,
            text=True,
            timeout=timeout_seconds,
            check=False,
        )
    except subprocess.TimeoutExpired:
        return {
            "command": [".venv/bin/python", *command],
            "returncode": 124,
            "status": "timeout",
            "duration_seconds": round(time.monotonic() - started, 3),
            "output_tail": [],
        }
    output = (result.stdout + "\n" + result.stderr).strip().splitlines()
    return {
        "command": [".venv/bin/python", *command],
        "returncode": result.returncode,
        "status": "passed" if result.returncode == 0 else "failed",
        "duration_seconds": round(time.monotonic() - started, 3),
        "output_tail": output[-12:],
    }


def _score_id(row: dict[str, Any]) -> str:
    return str(
        row.get("score_id")
        or row.get("pattern_lineage", {}).get("score_id")
        or row.get("lineage", {}).get("score_id")
        or ""
    )


def _records_by_score(runtime: Path, name: str) -> dict[str, dict[str, Any]]:
    return {
        _score_id(row): row
        for row in read_jsonl(runtime / name)
        if _score_id(row)
    }


def _latest_execution_by_setup(bundle: dict[str, Any]) -> dict[str, dict[str, Any]]:
    rows: dict[str, dict[str, Any]] = {}
    for row in bundle.get("execution_context", []):
        prestage_id = str(row.get("prestage_id") or "")
        if prestage_id:
            rows[prestage_id] = row
    return rows


def _parse_timestamp(value: Any) -> datetime | None:
    try:
        parsed = datetime.fromisoformat(str(value or "").replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _current_accepted_handoffs(
    runtime: Path,
    *,
    bundle: dict[str, Any],
    cycle_started_at: str,
    router_written_in_generation: bool,
) -> list[dict[str, Any]]:
    """Return only handoffs created by this cycle's Router evaluation."""

    if not router_written_in_generation:
        return []
    started = _parse_timestamp(cycle_started_at)
    if started is None:
        return []
    score_ids = {
        str(row.get("score_id") or "") for row in bundle.get("prestage", [])
    }
    candidate_ids = {
        str(row.get("candidate_identity_id") or "")
        for row in bundle.get("prestage", [])
    }
    score_ids.discard("")
    candidate_ids.discard("")
    current = []
    for accepted in read_jsonl(runtime / "qadam_paperops_handoff_v3_accepted.jsonl"):
        accepted_at = _parse_timestamp(accepted.get("generated_at"))
        source = accepted.get("source_handoff")
        source = source if isinstance(source, dict) else {}
        lineage = source.get("lineage")
        lineage = lineage if isinstance(lineage, dict) else {}
        if accepted_at is None or accepted_at < started:
            continue
        if source.get("route") != "guarded_alpaca_paper_via_paperops":
            continue
        if str(lineage.get("score_id") or "") not in score_ids:
            continue
        if str(source.get("candidate_identity_id") or "") not in candidate_ids:
            continue
        current.append(accepted)
    return current


def _generation_id(
    *,
    baseline_id: str,
    market_truth_id: str,
    generated_at: str,
    prestaged: list[dict[str, Any]],
) -> str:
    timestamp = datetime.fromisoformat(generated_at.replace("Z", "+00:00"))
    if timestamp.tzinfo is None:
        timestamp = timestamp.replace(tzinfo=timezone.utc)
    five_minute_bucket = int(timestamp.timestamp()) // 300
    return "conversion-generation:" + sha256_json(
        {
            "baseline_id": baseline_id,
            "market_truth_id": market_truth_id,
            "bucket": five_minute_bucket,
            "prestage_ids": sorted(row.get("prestage_id") for row in prestaged),
        }
    )[:24]


def _artifact_state(runtime: Path, command_id: str, started_at: float) -> dict[str, Any]:
    name = OUTPUT_ARTIFACTS[command_id]
    path = runtime / name
    return {
        "artifact": name,
        "exists": path.is_file(),
        "sha256": file_sha256(path) if path.is_file() else None,
        "written_in_generation": path.is_file() and path.stat().st_mtime >= started_at,
    }


def _conversion_cycles(
    *,
    runtime: Path,
    bundle: dict[str, Any],
    generation_id: str,
    generated_at: str,
    command_receipts: list[dict[str, Any]],
    paperops_handoffs: list[dict[str, Any]],
    paper_order_count: int,
    provider_canary: bool,
) -> list[dict[str, Any]]:
    market_truth = bundle["market_truth"]
    prestaged = bundle["prestage"]
    if not prestaged:
        prestaged = [
            {
                "prestage_id": None,
                "hypothesis_id": None,
                "score_id": None,
                "execution_proxy": None,
                "candidate_identity_id": None,
            }
        ]
    executions = _latest_execution_by_setup(bundle)
    akber = _records_by_score(runtime, "qadam_akber_filter_v3_results.jsonl")
    risks = _records_by_score(runtime, "qadam_position_size_proposals.jsonl")
    risk_rejections = _records_by_score(runtime, "qadam_risk_rejections.jsonl")
    routers = _records_by_score(runtime, "qadam_router_v3_decisions.jsonl")
    handoff_score_ids = {
        str(row.get("source_handoff", {}).get("lineage", {}).get("score_id") or "")
        for row in paperops_handoffs
    }
    receipts_passed = {row["command_id"] for row in command_receipts if row["status"] == "passed"}
    rows = []
    for setup in prestaged:
        score_id = str(setup.get("score_id") or "")
        execution = executions.get(str(setup.get("prestage_id") or ""), {})
        akber_row = akber.get(score_id, {})
        risk_row = risks.get(score_id) or risk_rejections.get(score_id, {})
        router_row = routers.get(score_id, {})
        setup_handoff_count = int(score_id in handoff_score_ids)
        root, propagated = primary_root_cause(
            market_truth=market_truth,
            setup=setup if setup.get("prestage_id") else None,
            execution=execution,
            akber=akber_row,
            risk=risk_row,
            router=router_row,
        )
        highest = 1
        if setup.get("prestage_id"):
            highest = 3
        if execution.get("execution_context_actionable") is True:
            highest = 5
        if "akber" in receipts_passed and akber_row:
            highest = 6
        if "shadow" in receipts_passed:
            highest = 7
        if "risk" in receipts_passed and risk_row:
            highest = 8
        if "router" in receipts_passed and router_row:
            highest = 9
        if setup_handoff_count:
            highest = 9
        if paper_order_count and setup_handoff_count:
            highest = 10
        cycle_material = {
            "generation_id": generation_id,
            "prestage_id": setup.get("prestage_id"),
            "setup_identity": setup.get("candidate_identity_id"),
        }
        rows.append(
            {
                "schema_version": SCHEMA_VERSION,
                "artifact_type": "qadam_open_market_conversion_cycle",
                "cycle_id": "conversion-cycle:" + sha256_json(cycle_material)[:24],
                "generated_at": generated_at,
                "decision_at": generated_at,
                "baseline_id": bundle["baseline"]["baseline_id"],
                "conversion_generation_id": generation_id,
                "session_date": market_truth.get("session_date"),
                "session_phase": market_truth.get("session_phase"),
                "market_clock_truth_id": market_truth.get("truth_id"),
                "market_clock_fresh": market_truth.get("provider_fresh") is True,
                "eligible_cycle": bool(
                    market_truth.get("actionable_for_conversion") is True
                    and setup.get("prestage_id")
                    and execution.get("execution_context_actionable") is True
                ),
                "setup_id": setup.get("prestage_id"),
                "candidate_identity_id": setup.get("candidate_identity_id"),
                "hypothesis_id": setup.get("hypothesis_id"),
                "score_id": score_id or None,
                "instrument": setup.get("execution_proxy"),
                "trigger_ids": setup.get("trigger_ids", []),
                "execution_context_id": execution.get("context_id"),
                "execution_context_actionable": execution.get(
                    "execution_context_actionable"
                )
                is True,
                "execution_mode": execution.get("execution_mode"),
                "akber_result_id": akber_row.get("akber_result_id"),
                "akber_decision": akber_row.get("decision"),
                "risk_proposal_id": risk_row.get("risk_proposal_id"),
                "risk_state": "proposal"
                if risk_row.get("position_size_proposed") is True
                else "rejected"
                if risk_row
                else "not_reached",
                "router_decision_id": router_row.get("router_decision_id"),
                "router_state": router_row.get("final_state"),
                "highest_stage_reached": highest,
                "paperops_handoff_count": setup_handoff_count,
                "paper_order_count": paper_order_count if setup_handoff_count else 0,
                "primary_root_cause": root,
                "propagated_downstream_states": propagated,
                "provider_canary": provider_canary,
                "broker_write_disabled": provider_canary,
                "coordinator_broker_write_count": 0,
                "canonical_paperops_only": True,
                "ambiguous_broker_write_retry_allowed": False,
                "proof_credit_count": 0,
                "live_capital_enabled": False,
                "authority": authority_flags(),
            }
        )
    return rows


def run_open_market_conversion(
    settings: Settings | None = None,
    *,
    allow_network: bool,
    broker_disabled_canary: bool = False,
    allow_paperops: bool = True,
) -> tuple[dict[str, Any], list[str]]:
    settings = settings or Settings.from_env()
    runtime = runtime_dir(settings)
    lock_path = runtime / LOCK_FILENAME
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    handle = lock_path.open("a+", encoding="utf-8")
    try:
        fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        handle.close()
        return {
            "status": "skipped_conversion_cycle_already_active",
            "paper_order_count": 0,
            "broker_write_count": 0,
        }, []
    generated_at = now_iso()
    errors: list[str] = []
    command_receipts: list[dict[str, Any]] = []
    failures = read_jsonl(runtime / FAILURES_ARTIFACT)
    try:
        if allow_network:
            refresh = _run_command(
                ("scripts/check_alpaca_paper_mirror.py", "--live"),
                timeout_seconds=180,
            )
            refresh["command_id"] = "market_clock_refresh"
            command_receipts.append(refresh)
            if refresh["returncode"] != 0:
                errors.append("market_clock_refresh_failed")
        market_truth, _checks, market_errors = build_and_write_market_clock_truth(settings)
        errors.extend(market_errors)
        bundle, _ef_checks, ef_errors = build_and_write_ef11_state(settings)
        errors.extend(ef_errors)
        generation_id = _generation_id(
            baseline_id=bundle["baseline"]["baseline_id"],
            market_truth_id=str(market_truth.get("truth_id") or ""),
            generated_at=generated_at,
            prestaged=bundle["prestage"],
        )
        generation = {
            "schema_version": SCHEMA_VERSION,
            "artifact_type": "qadam_open_market_conversion_generation",
            "generated_at": generated_at,
            "conversion_generation_id": generation_id,
            "baseline_id": bundle["baseline"]["baseline_id"],
            "market_clock_truth_id": market_truth.get("truth_id"),
            "market_session_actionable": market_truth.get("actionable_for_conversion"),
            "provider_canary": broker_disabled_canary,
            "paperops_allowed": allow_paperops and not broker_disabled_canary,
            "canonical_paperops_only": True,
            "broker_write_count_by_coordinator": 0,
            "live_capital_enabled": False,
            "authority": authority_flags(),
        }
        AtomicArtifactStore(runtime).write_json(GENERATION_ARTIFACT, generation)

        if market_truth.get("actionable_for_conversion") is True and not errors:
            for command_id, command in PIPELINE_COMMANDS:
                started_at = time.time()
                receipt = _run_command(command, timeout_seconds=900)
                receipt.update(
                    {
                        "receipt_id": "conversion-receipt:" + sha256_json(
                            {
                                "generation": generation_id,
                                "command": command_id,
                            }
                        )[:24],
                        "command_id": command_id,
                        "generated_at": now_iso(),
                        "conversion_generation_id": generation_id,
                        "artifact_state": _artifact_state(runtime, command_id, started_at),
                    }
                )
                command_receipts.append(receipt)
                if receipt["returncode"] != 0:
                    errors.append(f"conversion_stage_failed:{command_id}")
                    break
                if receipt["artifact_state"]["written_in_generation"] is not True:
                    errors.append(f"conversion_stage_artifact_not_current:{command_id}")
                    break
                if command_id == "strategy_translation":
                    bundle, _ef_checks, ef_errors = build_and_write_ef11_state(settings)
                    errors.extend(error for error in ef_errors if error not in errors)
                    if errors:
                        break
            bundle, _ef_checks, ef_errors = build_and_write_ef11_state(settings)
            errors.extend(ef_errors)

        router_receipt = next(
            (row for row in reversed(command_receipts) if row.get("command_id") == "router"),
            {},
        )
        accepted = _current_accepted_handoffs(
            runtime,
            bundle=bundle,
            cycle_started_at=generated_at,
            router_written_in_generation=bool(
                router_receipt.get("artifact_state", {}).get("written_in_generation") is True
            ),
        )
        handoff_count = len(accepted) if not errors else 0
        generation.update(
            {
                "pipeline_completed_at": now_iso(),
                "current_prestage_ids": sorted(
                    str(row.get("prestage_id"))
                    for row in bundle.get("prestage", [])
                    if row.get("prestage_id")
                ),
                "current_score_ids": sorted(
                    str(row.get("score_id"))
                    for row in bundle.get("prestage", [])
                    if row.get("score_id")
                ),
                "artifact_receipts": [
                    {
                        "command_id": row.get("command_id"),
                        "status": row.get("status"),
                        "artifact": row.get("artifact_state", {}).get("artifact"),
                        "artifact_sha256": row.get("artifact_state", {}).get("sha256"),
                        "written_in_generation": row.get("artifact_state", {}).get(
                            "written_in_generation"
                        ),
                    }
                    for row in command_receipts
                    if row.get("artifact_state")
                ],
                "accepted_current_handoff_ids": [
                    row.get("source_handoff", {}).get("paperops_handoff_id")
                    for row in accepted
                ],
                "accepted_current_handoff_count": handoff_count,
                "stale_handoff_reuse_allowed": False,
            }
        )
        AtomicArtifactStore(runtime).write_json(GENERATION_ARTIFACT, generation)
        paper_order_count = 0
        research_lock = read_json(runtime / "qadam_long_backtest_lock.json")
        validated_release = read_json(runtime / "qadam_research_lock_release_readiness.json")
        experimental_release = read_json(
            runtime / "qadam_experimental_paper_release_readiness.json"
        )
        paper_release_effective = bool(
            validated_release.get("release_effective") is True
            or experimental_release.get("experimental_paper_release_effective") is True
        )
        if handoff_count and allow_paperops and not broker_disabled_canary and not errors:
            if research_lock.get("status") == "active" or not paper_release_effective:
                errors.append("paperops_release_not_effective")
                handoff_count = 0
        if handoff_count and allow_paperops and not broker_disabled_canary and not errors:
            paperops = _run_command(
                ("scripts/run_paperops_autonomous_pass.py",), timeout_seconds=1800
            )
            paperops.update(
                {
                    "receipt_id": "conversion-receipt:" + sha256_json(
                        {"generation": generation_id, "command": "canonical_paperops"}
                    )[:24],
                    "command_id": "canonical_paperops",
                    "generated_at": now_iso(),
                    "conversion_generation_id": generation_id,
                }
            )
            command_receipts.append(paperops)
            if paperops["returncode"] != 0:
                errors.append("canonical_paperops_failed")
            summary = read_json(runtime / "paperops_autonomous_pass_summary.json")
            paper_order_count = int(
                summary.get("paper_runtime", {}).get("submitted_paper_order_count") or 0
            )

        cycle_rows = _conversion_cycles(
            runtime=runtime,
            bundle=bundle,
            generation_id=generation_id,
            generated_at=generated_at,
            command_receipts=command_receipts,
            paperops_handoffs=accepted if not errors else [],
            paper_order_count=paper_order_count,
            provider_canary=broker_disabled_canary,
        )
        cycles, summaries, status = append_conversion_cycles(runtime, cycle_rows)
        status.update(
            {
                "latest_conversion_generation_id": generation_id,
                "latest_cycle_error_count": len(errors),
                "latest_cycle_errors": errors,
            }
        )
        store = AtomicArtifactStore(runtime)
        store.write_jsonl(CONVERSION_CYCLES_ARTIFACT, cycles)
        store.write_jsonl(DAILY_SUMMARY_ARTIFACT, summaries)
        store.write_json(CONVERSION_STATUS_ARTIFACT, status)
        existing_receipts = read_jsonl(runtime / RECEIPTS_ARTIFACT)
        receipt_map = {
            str(row.get("receipt_id")): row
            for row in existing_receipts
            if row.get("receipt_id")
        }
        for receipt in command_receipts:
            if receipt.get("receipt_id"):
                receipt_map.setdefault(str(receipt["receipt_id"]), receipt)
        store.write_jsonl(
            RECEIPTS_ARTIFACT,
            sorted(receipt_map.values(), key=lambda row: str(row.get("generated_at") or "")),
        )
        if errors:
            failure = {
                "schema_version": SCHEMA_VERSION,
                "artifact_type": "qadam_open_market_conversion_failure",
                "failure_id": "conversion-failure:" + sha256_json(
                    {"generation": generation_id, "errors": errors}
                )[:24],
                "generated_at": now_iso(),
                "conversion_generation_id": generation_id,
                "errors": errors,
                "broker_write_count": 0,
                "live_capital_enabled": False,
                "authority": authority_flags(),
            }
            failures = [
                row for row in failures if row.get("failure_id") != failure["failure_id"]
            ] + [failure]
            store.write_jsonl(FAILURES_ARTIFACT, failures)
        final_bundle, final_checks, final_errors = build_and_write_ef11_state(settings)
        errors.extend(error for error in final_errors if error not in errors)
        result = {
            "schema_version": SCHEMA_VERSION,
            "artifact_type": "qadam_open_market_conversion_result",
            "generated_at": now_iso(),
            "status": (
                "passed_closed_market_hold"
                if market_truth.get("actionable_for_conversion") is not True and not errors
                else "passed"
                if not errors
                else "blocked"
            ),
            "conversion_generation_id": generation_id,
            "market_session_phase": market_truth.get("session_phase"),
            "market_session_actionable": market_truth.get("actionable_for_conversion"),
            "pre_staged_setup_count": final_bundle["prestage_status"].get("setup_count"),
            "handoff_count": handoff_count,
            "paper_order_count": paper_order_count,
            "broker_write_count_by_coordinator": 0,
            "canonical_paperops_invoked": any(
                row.get("command_id") == "canonical_paperops" for row in command_receipts
            ),
            "certification_state": final_bundle["certification"].get("status"),
            "engineering_contract_ready": final_checks.get("engineering_contract_ready"),
            "live_capital_enabled": False,
            "authority": authority_flags(),
        }
        return result, errors
    finally:
        fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
        handle.close()


__all__ = ["run_open_market_conversion"]
