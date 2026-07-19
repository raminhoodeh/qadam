"""OR-3 partitioned provider-backed historical source and price lake."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import time
from typing import Any
from urllib.parse import quote, urlencode
from urllib.request import Request, urlopen

from orchestrator.config import Settings
from orchestrator.qadam_canonical_contracts import AtomicArtifactStore
from orchestrator.qadam_operator_ready_common import (
    ROOT,
    append_jsonl_durable,
    authority_flags,
    now_iso,
    read_json,
    read_jsonl,
    runtime_dir,
    unique_errors,
    validate_authority,
)
from orchestrator.qadam_research_supervisor import ResearchSupervisor, stable_job_id
from orchestrator.secrets import secret_value

SCHEMA_VERSION = "qadam_provider_backfill.v1"
PHASE_ID = "OR-3"

SOURCE_MANIFEST_ARTIFACT = "qadam_source_backfill_manifest.json"
PRICE_MANIFEST_ARTIFACT = "qadam_price_backfill_manifest.json"
COVERAGE_ARTIFACT = "qadam_backfill_coverage.json"
ERRORS_ARTIFACT = "qadam_backfill_errors.jsonl"
DASHBOARD_ARTIFACT = "qadam_backfill_dashboard_summary.json"
CHECK_ARTIFACT = "qadam_provider_backfill_checks.json"
COST_RATE_LIMIT_ARTIFACT = "qadam_backfill_cost_and_rate_limit_state.json"
UNAVAILABLE_WINDOWS_ARTIFACT = "qadam_backfill_unavailable_windows.jsonl"

CAPABILITY_ARTIFACT = "qadam_provider_capability_registry.jsonl"
SOURCE_COVERAGE_MATRIX_ARTIFACT = "qadam_historical_source_coverage_matrix.json"
TRADING_UNIVERSE_ARTIFACT = "qsase_trading_universe.json"
LONG_LOCK_ARTIFACT = "qadam_long_backtest_lock.json"
OR3_READINESS_ARTIFACT = "qadam_or3_acquisition_readiness.json"
DATABENTO_ACQUISITION_ARTIFACT = "qadam_databento_futures_acquisition.json"
DATABENTO_NORMALIZATION_ARTIFACT = "qadam_databento_futures_normalization.json"
LEGACY_MISSING_WINDOWS_ARTIFACT = "qsase_historical_missing_windows.jsonl"

RESEARCH_ROOT = ROOT / "data" / "research"
ALPACA_DATA_BASE_URL = "https://data.alpaca.markets/v2"
ALPACA_PARSER_VERSION = "alpaca_stock_bars_daily.v1"
ALPACA_PRICE_PROVIDER = "alpaca_market_data_v2"
DATABENTO_PRICE_PROVIDER = "databento_glbx_mdp3"
SPECIALIZED_SYMBOL_PREFIXES = ("KALSHI:", "POLYMARKET:")
FUTURES_SYMBOLS = frozenset({"CL=F", "SI=F"})


@dataclass(frozen=True, kw_only=True)
class BackfillOptions:
    dry_run: bool = True
    resume: bool = True
    allow_network: bool = False
    provider_terms_reviewed: bool = False
    start_year: int = 2016
    end_year: int = datetime.now(timezone.utc).year
    max_jobs: int = 0
    sleep_between_calls: float = 0.5
    request_timeout_seconds: int = 30
    minimum_free_gb: float = 5.0


def _git_ignored(path: Path) -> bool:
    try:
        relative = path.relative_to(ROOT)
    except ValueError:
        return False
    completed = subprocess.run(
        ["git", "check-ignore", "-q", str(relative)],
        cwd=ROOT,
        check=False,
        capture_output=True,
        timeout=10,
    )
    return completed.returncode == 0


def _lock_safe(runtime: Path) -> bool:
    lock = read_json(runtime / LONG_LOCK_ARTIFACT)
    return lock.get("status") == "active" and lock.get("paperops_watch_only_mode") is True


def build_preflight(settings: Settings | None = None) -> dict[str, Any]:
    runtime = runtime_dir(settings)
    probe = RESEARCH_ROOT / ".qadam-git-ignore-probe"
    target_confined = RESEARCH_ROOT.is_relative_to(ROOT / "data")
    ignored = _git_ignored(probe)
    lock_safe = _lock_safe(runtime)
    readiness = read_json(runtime / OR3_READINESS_ARTIFACT)
    acquisition_ready = (
        readiness.get("status") == "ready"
        and readiness.get("or3_start_allowed") is True
        and readiness.get("pilot_status") == "passed"
        and int(readiness.get("pilot_provider_row_count") or 0) > 0
    )
    blockers: list[str] = []
    if not target_confined:
        blockers.append("research_root_outside_data_directory")
    if not ignored:
        blockers.append("research_root_is_git_trackable")
    if not lock_safe:
        blockers.append("research_lock_or_watch_only_state_missing")
    if not acquisition_ready:
        blockers.append("or2r_acquisition_readiness_not_passed")
    return {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "qadam_provider_backfill_preflight",
        "generated_at": now_iso(),
        "status": "passed" if not blockers else "blocked",
        "research_root": str(RESEARCH_ROOT.relative_to(ROOT)),
        "research_root_git_ignored": ignored,
        "target_confined_to_data_directory": target_confined,
        "paperops_watch_only_mode": lock_safe,
        "or2r_acquisition_ready": acquisition_ready,
        "or2r_readiness_status": readiness.get("status") or "missing",
        "or2r_pilot_status": readiness.get("pilot_status") or "missing",
        "blockers": blockers,
        "authority": authority_flags(),
    }


def _source_jobs(
    coverage_rows: list[dict[str, Any]],
    capabilities: list[dict[str, Any]],
    options: BackfillOptions,
) -> list[dict[str, Any]]:
    jobs: list[dict[str, Any]] = []
    capabilities_by_key = {
        str(row.get("source_key") or "unknown"): row for row in capabilities
    }
    for coverage in coverage_rows:
        key = str(coverage.get("source_key") or "unknown")
        capability = capabilities_by_key.get(key, {})
        if capability.get("historical_capture_mode") == "supplemental_feature_manifest":
            feature_ready = capability.get("backtest_feature_ready") is True
            row_count = int(capability.get("backtest_eligible_record_count") or 0)
            jobs.append(
                {
                    "schema_version": SCHEMA_VERSION,
                    "job_id": stable_job_id(
                        job_type="source_acquisition",
                        source=key,
                        provider=str(capability.get("provider_backfill_adapter") or key),
                        instrument=None,
                        date_partition="trial-through-2026-07-21",
                        requested_granularity=str(
                            capability.get("native_granularity") or "provider_native"
                        ),
                    ),
                    "job_type": "source_acquisition",
                    "source": key,
                    "provider": capability.get("provider_backfill_adapter") or key,
                    "instrument": None,
                    "date_partition": "trial-through-2026-07-21",
                    "requested_granularity": capability.get("native_granularity"),
                    "status": "complete" if feature_ready else "unavailable_classified",
                    "failure_category": (
                        None if feature_ready else "optional_time_bounded_features_not_captured"
                    ),
                    "retry_class": "idempotent_read_during_trial",
                    "rate_limit_class": "bounded_trial_budget",
                    "resume_cursor": None,
                    "row_count": row_count,
                    "checksum": None,
                    "started_at": capability.get("coverage_start"),
                    "completed_at": capability.get("coverage_end") if feature_ready else None,
                    "raw_response_storage_required": False,
                    "normalized_feature_manifest_required": True,
                    "historical_research_only": True,
                    "supplemental_feature_source": True,
                    "access_expires_on": capability.get("access_expires_on"),
                    "post_expiry_mode": "historical_archive_only",
                    "authority": authority_flags(),
                }
            )
            continue
        review_status = str(coverage.get("status") or "excluded")
        acquisition_ready = review_status == "pilot_ready"
        partitions: tuple[str, ...] = (
            tuple(str(year) for year in range(options.start_year, options.end_year + 1))
            if acquisition_ready
            else ("reviewed-classification",)
        )
        for date_partition in partitions:
            status = "pending_source_adapter" if acquisition_ready else "unavailable_classified"
            provider_id = key
            failure_category = (
                None
                if acquisition_ready
                else "forward_only_source"
                if review_status == "forward_only"
                else "excluded_by_reviewed_provider_terms"
            )
            jobs.append(
                {
                    "schema_version": SCHEMA_VERSION,
                    "job_id": stable_job_id(
                        job_type="source_acquisition",
                        source=key,
                        provider=provider_id,
                        instrument=None,
                        date_partition=date_partition,
                        requested_granularity=str(
                            coverage.get("granularity")
                            or capability.get("native_granularity")
                            or "unknown"
                        ),
                    ),
                    "job_type": "source_acquisition",
                    "source": key,
                    "provider": provider_id,
                    "provider_label": coverage.get("provider") or key,
                    "instrument": None,
                    "date_partition": date_partition,
                    "requested_granularity": (
                        coverage.get("granularity")
                        or capability.get("native_granularity")
                        or "unknown"
                    ),
                    "status": status,
                    "failure_category": failure_category,
                    "typed_unavailable_reason": (
                        review_status if not acquisition_ready else None
                    ),
                    "reviewed_source_state": review_status,
                    "retry_class": "idempotent_read" if acquisition_ready else "not_retryable",
                    "rate_limit_class": coverage.get("rate_limits") or "provider_specific",
                    "resume_cursor": None,
                    "row_count": 0,
                    "checksum": None,
                    "started_at": None,
                    "completed_at": None,
                    "raw_response_storage_required": True,
                    "terms_reference": coverage.get("terms_reference"),
                    "operator_approval_complete": coverage.get(
                        "operator_approval_complete"
                    )
                    is True,
                    "authority": authority_flags(),
                }
            )
    return jobs


def _price_jobs(instruments: list[dict[str, Any]], options: BackfillOptions) -> list[dict[str, Any]]:
    jobs: list[dict[str, Any]] = []
    for instrument in instruments:
        symbol = str(instrument.get("symbol") or "").upper()
        specialized = symbol.startswith(SPECIALIZED_SYMBOL_PREFIXES)
        futures = symbol in FUTURES_SYMBOLS
        provider = (
            symbol.split(":", 1)[0].lower()
            if specialized
            else DATABENTO_PRICE_PROVIDER
            if futures
            else ALPACA_PRICE_PROVIDER
        )
        partitions = ("specialized-adapter",) if specialized else tuple(
            str(year) for year in range(options.start_year, options.end_year + 1)
        )
        for partition in partitions:
            jobs.append(
                {
                    "schema_version": SCHEMA_VERSION,
                    "job_id": stable_job_id(
                        job_type="price_acquisition",
                        source="market_price",
                        provider=provider,
                        instrument=symbol,
                        date_partition=partition,
                        requested_granularity="1d",
                    ),
                    "job_type": "price_acquisition",
                    "source": "market_price",
                    "provider": provider,
                    "instrument": symbol,
                    "date_partition": partition,
                    "requested_granularity": "1d",
                    "status": (
                        "unavailable_classified"
                        if specialized
                        else "pending_external_import"
                        if futures
                        else "pending"
                    ),
                    "failure_category": (
                        "specialized_prediction_market_history_adapter_required"
                        if specialized
                        else "databento_batch_import_pending"
                        if futures
                        else None
                    ),
                    "retry_class": (
                        "not_retryable"
                        if specialized
                        else "external_batch_resume"
                        if futures
                        else "idempotent_read"
                    ),
                    "rate_limit_class": (
                        "provider_batch_job"
                        if futures
                        else "bounded_serial_read"
                    ),
                    "resume_cursor": None,
                    "row_count": 0,
                    "checksum": None,
                    "started_at": None,
                    "completed_at": None,
                    "corporate_action_policy": (
                        "not_applicable_futures"
                        if futures
                        else "alpaca_adjustment_all"
                    ),
                    "futures_roll_policy": (
                        "databento_parent_contract_definitions_and_roll_metadata_required"
                        if futures
                        else "not_applicable"
                    ),
                    "authority": authority_flags(),
                }
            )
    return jobs


def build_manifests(
    settings: Settings | None = None,
    *,
    options: BackfillOptions | None = None,
) -> tuple[dict[str, Any], dict[str, Any]]:
    active = options or BackfillOptions()
    runtime = runtime_dir(settings)
    capabilities = read_jsonl(runtime / CAPABILITY_ARTIFACT)
    source_coverage = read_json(runtime / SOURCE_COVERAGE_MATRIX_ARTIFACT)
    coverage_rows = (
        source_coverage.get("rows")
        if isinstance(source_coverage.get("rows"), list)
        else []
    )
    universe = read_json(runtime / TRADING_UNIVERSE_ARTIFACT)
    instruments = universe.get("instruments") if isinstance(universe.get("instruments"), list) else []
    generated_at = now_iso()
    source_jobs = _source_jobs(coverage_rows, capabilities, active)
    price_jobs = _price_jobs(instruments, active)
    source_manifest = {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "qadam_source_backfill_manifest",
        "generated_at": generated_at,
        "status": "planned_with_provider_validation_gaps",
        "partition_model": "provider_source_year",
        "source_count": len(coverage_rows),
        "job_count": len(source_jobs),
        "jobs": source_jobs,
        "authority": authority_flags(),
    }
    price_manifest = {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "qadam_price_backfill_manifest",
        "generated_at": generated_at,
        "status": "ready_for_explicit_provider_run",
        "price_first": True,
        "partition_model": "symbol_interval_year",
        "instrument_count": len(instruments),
        "job_count": len(price_jobs),
        "jobs": price_jobs,
        "authority": authority_flags(),
    }
    return source_manifest, price_manifest


def _apply_databento_import(
    price_manifest: dict[str, Any],
    *,
    runtime: Path,
) -> None:
    normalization = read_json(runtime / DATABENTO_NORMALIZATION_ARTIFACT)
    if normalization.get("status") != "complete":
        return
    partitions = (
        normalization.get("partitions")
        if isinstance(normalization.get("partitions"), list)
        else []
    )
    by_key = {
        (str(row.get("symbol") or ""), str(row.get("date_partition") or "")): row
        for row in partitions
        if isinstance(row, dict)
    }
    for job in price_manifest.get("jobs", []):
        if job.get("provider") != DATABENTO_PRICE_PROVIDER:
            continue
        partition = by_key.get(
            (str(job.get("instrument") or ""), str(job.get("date_partition") or ""))
        )
        if not partition:
            continue
        job.update(
            {
                "status": partition.get("status"),
                "completed_at": partition.get("generated_at"),
                "row_count": int(partition.get("normalized_row_count") or 0),
                "checksum": partition.get("normalized_sha256"),
                "failure_category": (
                    None
                    if partition.get("status") == "complete"
                    else "databento_partition_has_no_selected_outright_bars"
                ),
                "typed_unavailable_reason": partition.get("typed_unavailable_reason"),
                "normalized_path": partition.get("normalized_path"),
                "roll_metadata_path": partition.get("roll_metadata_path"),
                "roll_count": int(partition.get("roll_count") or 0),
                "continuous_contract_policy": partition.get(
                    "continuous_contract_policy"
                ),
                "back_adjusted": partition.get("back_adjusted") is True,
                "definition_job_verified": (
                    partition.get("definition_job_verified") is True
                ),
                "credentials_recorded": False,
            }
        )


def _research_disk_bytes() -> int:
    total = 0
    if not RESEARCH_ROOT.exists():
        return total
    for path in RESEARCH_ROOT.rglob("*"):
        if not path.is_file():
            continue
        try:
            total += path.stat().st_size
        except OSError:
            continue
    return total


def _build_cost_and_rate_limit_state(
    source_manifest: dict[str, Any],
    price_manifest: dict[str, Any],
    *,
    runtime: Path,
) -> dict[str, Any]:
    databento = read_json(runtime / DATABENTO_ACQUISITION_ARTIFACT)
    databento_quote = (
        databento.get("quote") if isinstance(databento.get("quote"), dict) else {}
    )
    actual_databento_cost = float(databento_quote.get("total_usd") or 0.0)
    price_jobs = (
        price_manifest.get("jobs")
        if isinstance(price_manifest.get("jobs"), list)
        else []
    )
    source_jobs = (
        source_manifest.get("jobs")
        if isinstance(source_manifest.get("jobs"), list)
        else []
    )
    call_eligible_states = {"complete", "unavailable_classified", "retryable_failure"}
    alpaca_partition_calls = sum(
        job.get("provider") == ALPACA_PRICE_PROVIDER
        and job.get("status") in call_eligible_states
        for job in price_jobs
    )
    disk = shutil.disk_usage(RESEARCH_ROOT.parent)
    provider_states = []
    for provider in sorted(
        {
            str(job.get("provider") or "unknown")
            for job in [*source_jobs, *price_jobs]
        }
    ):
        jobs = [
            job
            for job in [*source_jobs, *price_jobs]
            if str(job.get("provider") or "unknown") == provider
        ]
        provider_states.append(
            {
                "provider": provider,
                "partition_count": len(jobs),
                "complete_count": sum(job.get("status") == "complete" for job in jobs),
                "unavailable_classified_count": sum(
                    job.get("status") == "unavailable_classified" for job in jobs
                ),
                "pending_count": sum(
                    str(job.get("status") or "").startswith("pending") for job in jobs
                ),
                "rate_limit_policy": sorted(
                    {
                        str(job.get("rate_limit_class") or "provider_specific")
                        for job in jobs
                    }
                ),
            }
        )
    return {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "qadam_backfill_cost_and_rate_limit_state",
        "generated_at": now_iso(),
        "status": "within_limits",
        "budget_scope": "historical_data_acquisition_only",
        "paper_account_starting_capital_usd": 100_000,
        "paper_account_is_not_provider_budget": True,
        "historical_data_budget_usd": 150.0,
        "historical_data_spent_usd": round(actual_databento_cost, 8),
        "historical_data_budget_remaining_usd": round(
            max(0.0, 150.0 - actual_databento_cost), 8
        ),
        "unapproved_incremental_spend_usd": 0.0,
        "databento_batch_job_count": len(databento.get("jobs", {})),
        "alpaca_partition_call_count_lower_bound": alpaca_partition_calls,
        "research_data_bytes": _research_disk_bytes(),
        "disk_free_bytes": disk.free,
        "disk_total_bytes": disk.total,
        "provider_states": provider_states,
        "credentials_recorded": False,
        "paper_trial_calendar_advanced": False,
        "trade_candidate_created_count": 0,
        "paper_order_created_count": 0,
        "broker_write_count": 0,
        "proof_credit_created_count": 0,
        "authority": authority_flags(),
    }


def _build_unavailable_window_records(
    source_manifest: dict[str, Any],
    price_manifest: dict[str, Any],
    *,
    runtime: Path,
) -> list[dict[str, Any]]:
    generated_at = now_iso()
    records: list[dict[str, Any]] = []
    all_jobs = [*source_manifest.get("jobs", []), *price_manifest.get("jobs", [])]
    for job in all_jobs:
        if job.get("status") != "unavailable_classified":
            continue
        records.append(
            {
                "schema_version": SCHEMA_VERSION,
                "record_type": "provider_partition_unavailable",
                "generated_at": generated_at,
                "job_id": job.get("job_id"),
                "source_key": job.get("source"),
                "market_symbol": job.get("instrument"),
                "date_partition": job.get("date_partition"),
                "provider": job.get("provider"),
                "typed_reason": (
                    job.get("typed_unavailable_reason")
                    or job.get("failure_category")
                    or "provider_partition_unavailable"
                ),
                "interpolation_allowed": False,
                "proxy_credit_allowed": False,
                "authority": authority_flags(),
            }
        )

    source_jobs_by_key: dict[str, list[dict[str, Any]]] = {}
    for job in source_manifest.get("jobs", []):
        source_jobs_by_key.setdefault(str(job.get("source") or "unknown"), []).append(job)
    price_jobs_by_symbol: dict[str, list[dict[str, Any]]] = {}
    for job in price_manifest.get("jobs", []):
        price_jobs_by_symbol.setdefault(str(job.get("instrument") or "unknown"), []).append(
            job
        )

    for missing in read_jsonl(runtime / LEGACY_MISSING_WINDOWS_ARTIFACT):
        source_key = str(missing.get("source_key") or "unknown")
        symbol = str(missing.get("market_symbol") or "unknown")
        source_jobs = source_jobs_by_key.get(source_key, [])
        price_jobs = price_jobs_by_symbol.get(symbol, [])
        source_states = {str(job.get("status") or "unknown") for job in source_jobs}
        source_review_states = {
            str(job.get("reviewed_source_state") or "unknown") for job in source_jobs
        }
        price_states = {str(job.get("status") or "unknown") for job in price_jobs}
        if "forward_only" in source_review_states:
            reason = "forward_only_source_history"
        elif "excluded" in source_review_states:
            reason = "source_history_excluded_by_reviewed_terms_or_scope"
        elif price_states and price_states <= {"unavailable_classified"}:
            reason = "instrument_history_unavailable_or_specialized_archive_required"
        elif "complete" in price_states and "complete" in source_states:
            reason = "point_in_time_alignment_pending_or4"
        elif "complete" in price_states:
            reason = "source_history_acquisition_pending"
        elif "complete" in source_states:
            reason = "price_history_acquisition_or_alignment_pending"
        else:
            reason = "source_and_price_history_acquisition_pending"
        records.append(
            {
                **missing,
                "schema_version": SCHEMA_VERSION,
                "record_type": "source_price_forward_window_remainder",
                "generated_at": generated_at,
                "original_reason": missing.get("reason"),
                "typed_reason": reason,
                "source_partition_states": sorted(source_states),
                "price_partition_states": sorted(price_states),
                "interpolation_allowed": False,
                "proxy_credit_allowed": False,
                "or4_alignment_required": reason == "point_in_time_alignment_pending_or4",
                "authority": authority_flags(),
            }
        )
    return records


def _atomic_bytes(path: Path, payload: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    with temporary.open("wb") as handle:
        handle.write(payload)
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(temporary, path)


def _fetch_alpaca_price_partition(
    job: dict[str, Any],
    *,
    api_key: str,
    api_secret: str,
    timeout_seconds: int,
) -> tuple[bytes, list[dict[str, Any]], dict[str, Any]]:
    symbol = str(job["instrument"])
    year = int(job["date_partition"])
    fetched_at = now_iso()
    base_params: dict[str, Any] = {
        "timeframe": "1Day",
        "start": f"{year:04d}-01-01T00:00:00Z",
        "end": f"{year + 1:04d}-01-01T00:00:00Z",
        "limit": 10000,
        "adjustment": "all",
        "feed": "iex",
        "sort": "asc",
    }
    page_token: str | None = None
    pages: list[dict[str, Any]] = []
    response_statuses: list[int] = []
    request_url_hashes: list[str] = []
    while True:
        params = dict(base_params)
        if page_token:
            params["page_token"] = page_token
        url = (
            f"{ALPACA_DATA_BASE_URL}/stocks/{quote(symbol, safe='')}/bars?"
            f"{urlencode(params)}"
        )
        request = Request(
            url,
            headers={
                "APCA-API-KEY-ID": api_key,
                "APCA-API-SECRET-KEY": api_secret,
                "Accept": "application/json",
                "User-Agent": "Qadam-Research/1.0 read-only",
            },
        )
        with urlopen(  # noqa: S310 - fixed official Alpaca read-only endpoint
            request,
            timeout=timeout_seconds,
        ) as response:
            body = response.read()
            response_statuses.append(int(getattr(response, "status", 200)))
        payload = json.loads(body)
        if not isinstance(payload, dict):
            raise RuntimeError("alpaca_historical_payload_not_object")
        pages.append(payload)
        request_url_hashes.append(hashlib.sha256(url.encode("utf-8")).hexdigest())
        next_token = payload.get("next_page_token")
        if not isinstance(next_token, str) or not next_token.strip():
            break
        if len(pages) >= 100:
            raise RuntimeError("alpaca_historical_pagination_limit_exceeded")
        page_token = next_token.strip()

    raw = json.dumps(
        {"pages": pages},
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    raw_sha256 = hashlib.sha256(raw).hexdigest()
    bars: list[dict[str, Any]] = []
    for page in pages:
        rows = page.get("bars") if isinstance(page.get("bars"), list) else []
        for row in rows:
            if not isinstance(row, dict) or not row.get("t"):
                continue
            bars.append(
                {
                    "schema_version": SCHEMA_VERSION,
                    "symbol": symbol,
                    "interval": "1d",
                    "observed_at": row.get("t"),
                    "available_at": fetched_at,
                    "open": row.get("o"),
                    "high": row.get("h"),
                    "low": row.get("l"),
                    "close": row.get("c"),
                    "adjusted_close": row.get("c"),
                    "volume": row.get("v"),
                    "trade_count": row.get("n"),
                    "volume_weighted_average_price": row.get("vw"),
                    "provider": ALPACA_PRICE_PROVIDER,
                    "provider_feed": "iex",
                    "provider_adjustment": "all",
                    "provider_response_sha256": raw_sha256,
                }
            )
    bars.sort(key=lambda row: str(row.get("observed_at") or ""))
    return raw, bars, {
        "endpoint": f"{ALPACA_DATA_BASE_URL}/stocks/{symbol}/bars",
        "query": base_params,
        "http_statuses": response_statuses,
        "page_count": len(pages),
        "fetched_at": fetched_at,
        "credentials_recorded": False,
        "request_url_sha256": request_url_hashes,
    }


def _write_price_partition(
    job: dict[str, Any],
    raw: bytes,
    bars: list[dict[str, Any]],
    request_metadata: dict[str, Any],
) -> dict[str, Any]:
    symbol = str(job["instrument"]).replace("/", "_")
    year = str(job["date_partition"])
    provider = str(job["provider"])
    raw_dir = RESEARCH_ROOT / "raw" / f"source={provider}" / f"date={year}"
    normalized_dir = (
        RESEARCH_ROOT / "prices" / f"symbol={symbol}" / "interval=1d" / f"year={year}"
    )
    raw_path = raw_dir / f"{job['job_id'].replace(':', '_')}.json"
    rows_path = normalized_dir / "bars.jsonl"
    metadata_path = normalized_dir / "metadata.json"
    _atomic_bytes(raw_path, raw)
    encoded_rows = b"".join(
        (json.dumps(record, sort_keys=True, separators=(",", ":")) + "\n").encode("utf-8")
        for record in bars
    )
    _atomic_bytes(rows_path, encoded_rows)
    metadata = {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "qadam_price_partition_metadata",
        "generated_at": now_iso(),
        "job_id": job["job_id"],
        "provider": provider,
        "symbol": job["instrument"],
        "date_partition": year,
        "request": request_metadata,
        "raw_payload_path": str(raw_path.relative_to(ROOT)),
        "raw_payload_sha256": hashlib.sha256(raw).hexdigest(),
        "normalized_path": str(rows_path.relative_to(ROOT)),
        "normalized_sha256": hashlib.sha256(encoded_rows).hexdigest(),
        "parser_version": ALPACA_PARSER_VERSION,
        "provider_cursor": None,
        "normalized_row_count": len(bars),
        "authority": authority_flags(),
    }
    _atomic_bytes(metadata_path, (json.dumps(metadata, indent=2, sort_keys=True) + "\n").encode("utf-8"))
    return metadata


def _job_key(record: dict[str, Any]) -> str:
    return str(record.get("job_id") or "")


def _coverage(
    source_manifest: dict[str, Any],
    price_manifest: dict[str, Any],
    *,
    preflight: dict[str, Any],
) -> dict[str, Any]:
    source_jobs = source_manifest.get("jobs", [])
    price_jobs = price_manifest.get("jobs", [])
    all_jobs = [*source_jobs, *price_jobs]
    counts: dict[str, int] = {}
    for job in all_jobs:
        status = str(job.get("status") or "unknown")
        counts[status] = counts.get(status, 0) + 1
    complete = counts.get("complete", 0)
    unavailable = counts.get("unavailable_classified", 0)
    all_partitions_terminal = complete + unavailable == len(all_jobs)
    all_partitions_acquired = complete == len(all_jobs)
    supplemental_jobs = [job for job in source_jobs if job.get("supplemental_feature_source") is True]
    supplemental_rows = sum(int(job.get("row_count") or 0) for job in supplemental_jobs)
    core_rows = sum(
        int(job.get("row_count") or 0)
        for job in all_jobs
        if job.get("supplemental_feature_source") is not True
    )
    core_completed_partition_count = sum(
        job.get("status") == "complete"
        for job in all_jobs
        if job.get("supplemental_feature_source") is not True
    )
    return {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "qadam_backfill_coverage",
        "generated_at": now_iso(),
        "status": (
            "complete"
            if all_partitions_acquired
            else "complete_with_classified_gaps"
            if all_partitions_terminal
            else "evidence_maturing"
        ),
        "preflight_status": preflight.get("status"),
        "source_count": source_manifest.get("source_count", 0),
        "instrument_count": price_manifest.get("instrument_count", 0),
        "total_partition_count": len(all_jobs),
        "completed_partition_count": complete,
        "core_completed_partition_count": core_completed_partition_count,
        "unavailable_classified_partition_count": unavailable,
        "remaining_partition_count": len(all_jobs) - complete - unavailable,
        "status_counts": dict(sorted(counts.items())),
        "provider_row_count": core_rows + supplemental_rows,
        "core_provider_row_count": core_rows,
        "supplemental_feature_row_count": supplemental_rows,
        "supplemental_feature_source_count": len(supplemental_jobs),
        "unusual_whales_backtest_feature_row_count": sum(
            int(job.get("row_count") or 0)
            for job in supplemental_jobs
            if job.get("source") == "unusual_whales"
        ),
        "unusual_whales_backtest_feature_ready": any(
            job.get("source") == "unusual_whales" and job.get("status") == "complete"
            for job in supplemental_jobs
        ),
        "all_partitions_terminal": all_partitions_terminal,
        "all_partitions_acquired": all_partitions_acquired,
        "provider_history_acquisition_contract_complete": (
            core_completed_partition_count > 0 and all_partitions_terminal
        ),
        "provider_history_complete_with_classified_gaps": (
            core_completed_partition_count > 0
            and all_partitions_terminal
            and unavailable > 0
        ),
        "provider_history_certified_complete": (
            core_completed_partition_count > 0 and all_partitions_acquired
        ),
        "authority": authority_flags(),
    }


def build_dashboard_summary(coverage: dict[str, Any]) -> dict[str, Any]:
    status = str(coverage.get("status") or "evidence_maturing")
    if status == "complete":
        headline = "Historical evidence acquisition is complete"
    elif status == "complete_with_classified_gaps":
        headline = "Historical acquisition is complete with classified gaps"
    else:
        headline = "Historical evidence acquisition is still maturing"
    return {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "qadam_backfill_dashboard_summary",
        "generated_at": now_iso(),
        "status": status,
        "headline": headline,
        "plain_english": (
            f"{coverage.get('completed_partition_count', 0)} of "
            f"{coverage.get('total_partition_count', 0)} provider/date partitions contain "
            f"acquired records; {coverage.get('unavailable_classified_partition_count', 0)} "
            "are explicitly classified gaps. Missing history is not treated as evidence."
        ),
        "source_count": coverage.get("source_count"),
        "instrument_count": coverage.get("instrument_count"),
        "completed_partition_count": coverage.get("completed_partition_count"),
        "unavailable_classified_partition_count": coverage.get(
            "unavailable_classified_partition_count"
        ),
        "remaining_partition_count": coverage.get("remaining_partition_count"),
        "all_partitions_terminal": coverage.get("all_partitions_terminal"),
        "all_partitions_acquired": coverage.get("all_partitions_acquired"),
        "provider_history_acquisition_contract_complete": coverage.get(
            "provider_history_acquisition_contract_complete"
        ),
        "empirical_provider_evidence_complete": coverage.get(
            "provider_history_certified_complete"
        ),
        "provider_row_count": coverage.get("provider_row_count"),
        "supplemental_feature_row_count": coverage.get("supplemental_feature_row_count"),
        "unusual_whales_backtest_feature_ready": coverage.get(
            "unusual_whales_backtest_feature_ready"
        ),
        "paperops_watch_only_mode": True,
        "authority": authority_flags(),
    }


def validate_provider_backfill(
    source_manifest: dict[str, Any],
    price_manifest: dict[str, Any],
    coverage: dict[str, Any],
    preflight: dict[str, Any],
) -> list[str]:
    errors: list[str] = []
    if preflight.get("status") != "passed":
        errors.extend(f"preflight:{item}" for item in preflight.get("blockers", []))
    if source_manifest.get("source_count") != 41:
        errors.append("source_manifest_not_whole_universe")
    if price_manifest.get("instrument_count") != 19:
        errors.append("price_manifest_not_whole_universe")
    for name, manifest in (("source", source_manifest), ("price", price_manifest)):
        jobs = manifest.get("jobs") if isinstance(manifest.get("jobs"), list) else []
        identifiers = [_job_key(job) for job in jobs]
        if len(identifiers) != len(set(identifiers)):
            errors.append(f"{name}_manifest_duplicate_job_id")
        for job in jobs:
            for field in (
                "job_id",
                "provider",
                "date_partition",
                "requested_granularity",
                "retry_class",
                "rate_limit_class",
                "status",
            ):
                if job.get(field) in {None, ""}:
                    errors.append(f"{name}_job_field_missing:{field}")
            errors.extend(validate_authority(job.get("authority", {}), prefix=f"{name}_job"))
    if coverage.get("provider_row_count") == 0 and coverage.get("provider_history_certified_complete") is True:
        errors.append("zero_provider_rows_falsely_certified_complete")
    errors.extend(validate_authority(coverage.get("authority", {}), prefix="backfill_coverage"))
    return unique_errors(errors)


def build_and_write_provider_backfill_baseline(
    settings: Settings | None = None,
    *,
    options: BackfillOptions | None = None,
) -> tuple[dict[str, Any], dict[str, Any], list[str]]:
    runtime = runtime_dir(settings)
    store = AtomicArtifactStore(runtime)
    active = options or BackfillOptions()
    preflight = build_preflight(settings)
    source_manifest, price_manifest = build_manifests(settings, options=active)
    for artifact_name, new_manifest in (
        (SOURCE_MANIFEST_ARTIFACT, source_manifest),
        (PRICE_MANIFEST_ARTIFACT, price_manifest),
    ):
        existing_manifest = read_json(runtime / artifact_name)
        existing_jobs = existing_manifest.get("jobs") if isinstance(existing_manifest.get("jobs"), list) else []
        existing_by_id = {_job_key(job): job for job in existing_jobs}
        for job in new_manifest["jobs"]:
            previous = existing_by_id.get(_job_key(job))
            if previous and previous.get("status") == "empty_valid_response":
                previous = {
                    **previous,
                    "status": "unavailable_classified",
                    "failure_category": "provider_empty_for_symbol_year",
                    "typed_unavailable_reason": "provider_gap_or_no_trades",
                }
            if previous and previous.get("status") in {
                "complete",
                "unavailable_classified",
                "retryable_failure",
                "running",
            }:
                job.update(previous)
    _apply_databento_import(price_manifest, runtime=runtime)
    store.write_json(SOURCE_MANIFEST_ARTIFACT, source_manifest)
    store.write_json(PRICE_MANIFEST_ARTIFACT, price_manifest)
    supervisor = ResearchSupervisor(runtime)
    existing_supervisor_jobs = {_job_key(job): job for job in supervisor.load_jobs()}
    for job in [*source_manifest["jobs"], *price_manifest["jobs"]]:
        existing_supervisor_jobs[_job_key(job)] = job
    supervisor.write_jobs(existing_supervisor_jobs.values())
    if not (runtime / ERRORS_ARTIFACT).exists():
        store.write_jsonl(ERRORS_ARTIFACT, [])
    coverage = _coverage(source_manifest, price_manifest, preflight=preflight)
    dashboard = build_dashboard_summary(coverage)
    cost_state = _build_cost_and_rate_limit_state(
        source_manifest,
        price_manifest,
        runtime=runtime,
    )
    unavailable_windows = _build_unavailable_window_records(
        source_manifest,
        price_manifest,
        runtime=runtime,
    )
    store.write_json(COVERAGE_ARTIFACT, coverage)
    store.write_json(DASHBOARD_ARTIFACT, dashboard)
    store.write_json(COST_RATE_LIMIT_ARTIFACT, cost_state)
    store.write_jsonl(UNAVAILABLE_WINDOWS_ARTIFACT, unavailable_windows)
    errors = validate_provider_backfill(source_manifest, price_manifest, coverage, preflight)
    if cost_state["historical_data_spent_usd"] > cost_state["historical_data_budget_usd"]:
        errors.append("historical_data_budget_exceeded")
    if cost_state.get("credentials_recorded") is not False:
        errors.append("historical_cost_state_credentials_recorded")
    legacy_missing_count = len(read_jsonl(runtime / LEGACY_MISSING_WINDOWS_ARTIFACT))
    typed_remainders = [
        row
        for row in unavailable_windows
        if row.get("record_type") == "source_price_forward_window_remainder"
    ]
    if len(typed_remainders) != legacy_missing_count:
        errors.append("forward_window_remainders_not_fully_typed")
    if any(not row.get("typed_reason") for row in unavailable_windows):
        errors.append("unavailable_window_typed_reason_missing")
    errors = unique_errors(errors)
    acquisition_contract_complete = (
        coverage.get("provider_history_acquisition_contract_complete") is True
    )
    empirical_provider_evidence_complete = (
        coverage.get("provider_history_certified_complete") is True
    )
    checks = {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "qadam_provider_backfill_checks",
        "phase_id": PHASE_ID,
        "generated_at": now_iso(),
        "status": (
            "blocked"
            if errors
            else "passed"
            if acquisition_contract_complete
            else "evidence_maturing"
        ),
        "coverage_state": coverage.get("status"),
        "implementation_ready": not errors,
        "or3_acceptance_passed": not errors and acquisition_contract_complete,
        "provider_history_acquisition_contract_complete": acquisition_contract_complete,
        "empirical_provider_evidence_complete": empirical_provider_evidence_complete,
        "source_count": source_manifest["source_count"],
        "instrument_count": price_manifest["instrument_count"],
        "total_partition_count": coverage["total_partition_count"],
        "completed_partition_count": coverage["completed_partition_count"],
        "unavailable_classified_partition_count": coverage[
            "unavailable_classified_partition_count"
        ],
        "remaining_partition_count": coverage["remaining_partition_count"],
        "provider_row_count": coverage["provider_row_count"],
        "supplemental_feature_row_count": coverage["supplemental_feature_row_count"],
        "unusual_whales_backtest_feature_ready": coverage[
            "unusual_whales_backtest_feature_ready"
        ],
        "research_root_git_ignored": preflight["research_root_git_ignored"],
        "paperops_watch_only_mode": preflight["paperops_watch_only_mode"],
        "historical_data_spent_usd": cost_state["historical_data_spent_usd"],
        "historical_data_budget_usd": cost_state["historical_data_budget_usd"],
        "unavailable_window_record_count": len(unavailable_windows),
        "typed_forward_window_remainder_count": sum(
            row.get("record_type") == "source_price_forward_window_remainder"
            for row in unavailable_windows
        ),
        "network_called_by_checker": False,
        "validation_error_count": len(errors),
        "validation_errors": errors,
        "broker_write_count": 0,
        "authority": authority_flags(),
    }
    store.write_json(CHECK_ARTIFACT, checks)
    return coverage, checks, errors


def run_provider_backfill(
    settings: Settings | None = None,
    *,
    options: BackfillOptions,
) -> tuple[dict[str, Any], dict[str, Any], list[str]]:
    runtime = runtime_dir(settings)
    coverage, checks, errors = build_and_write_provider_backfill_baseline(settings, options=options)
    if errors or options.dry_run:
        return coverage, checks, errors
    if not options.allow_network:
        return coverage, checks, ["network_not_explicitly_allowed"]
    if not options.provider_terms_reviewed:
        return coverage, checks, ["provider_terms_review_not_confirmed"]
    supervisor = ResearchSupervisor(runtime)
    resource = supervisor.resource_state(minimum_free_gb=options.minimum_free_gb)
    if resource["disk_pause_required"]:
        return coverage, checks, ["backfill_paused_low_disk"]
    acquired, reason = supervisor.acquire_lease()
    if not acquired:
        return coverage, checks, [f"research_supervisor_lease:{reason}"]
    store = AtomicArtifactStore(runtime)
    source_manifest = read_json(runtime / SOURCE_MANIFEST_ARTIFACT)
    price_manifest = read_json(runtime / PRICE_MANIFEST_ARTIFACT)
    jobs = price_manifest.get("jobs") if isinstance(price_manifest.get("jobs"), list) else []
    alpaca_jobs_pending = any(
        job.get("provider") == ALPACA_PRICE_PROVIDER and job.get("status") == "pending"
        for job in jobs
    )
    alpaca_key = secret_value("ALPACA_API_KEY", settings) if alpaca_jobs_pending else None
    alpaca_secret = secret_value("ALPACA_API_SECRET", settings) if alpaca_jobs_pending else None
    if alpaca_jobs_pending and (not alpaca_key or not alpaca_secret):
        supervisor.release_lease(reason="alpaca_historical_credentials_missing")
        return coverage, checks, ["alpaca_historical_credentials_missing"]
    processed = 0
    run_errors: list[str] = []
    try:
        for job in jobs:
            if job.get("status") == "complete" and options.resume:
                continue
            if job.get("status") != "pending":
                continue
            if options.max_jobs and processed >= options.max_jobs:
                break
            started_at = now_iso()
            job.update({"status": "running", "started_at": started_at})
            store.write_json(PRICE_MANIFEST_ARTIFACT, price_manifest)
            supervisor.write_checkpoint(
                current_job_id=job["job_id"],
                resume_cursor=job["date_partition"],
                reason="provider_partition_started",
            )
            try:
                if job.get("provider") != ALPACA_PRICE_PROVIDER:
                    raise RuntimeError("unsupported_price_provider_dispatch")
                raw, bars, request_metadata = _fetch_alpaca_price_partition(
                    job,
                    api_key=str(alpaca_key),
                    api_secret=str(alpaca_secret),
                    timeout_seconds=options.request_timeout_seconds,
                )
                metadata = _write_price_partition(job, raw, bars, request_metadata)
                job.update(
                    {
                        "status": "complete" if bars else "unavailable_classified",
                        "completed_at": now_iso(),
                        "row_count": len(bars),
                        "checksum": metadata["raw_payload_sha256"],
                        "failure_category": (
                            None if bars else "provider_empty_for_symbol_year"
                        ),
                        "typed_unavailable_reason": (
                            None if bars else "provider_gap_or_no_trades"
                        ),
                    }
                )
            except Exception as exc:  # noqa: BLE001 - provider errors are classified and resumable
                category = "rate_limited" if "429" in repr(exc) else "provider_read_failure"
                job.update({"status": "retryable_failure", "failure_category": category})
                run_errors.append(f"{job['job_id']}:{category}:{exc.__class__.__name__}")
            processed += 1
            store.write_json(PRICE_MANIFEST_ARTIFACT, price_manifest)
            supervisor.write_heartbeat(
                state="provider_backfill_running",
                current_job_id=job["job_id"],
                processed_units=processed,
                elapsed_seconds=max(float(processed), 1.0),
                last_successful_provider_call_at=(
                    job.get("completed_at") if job.get("status") == "complete" else None
                ),
            )
            if options.sleep_between_calls > 0:
                time.sleep(options.sleep_between_calls)
    finally:
        supervisor.write_checkpoint(
            current_job_id=None,
            resume_cursor=None,
            reason="provider_backfill_cycle_complete",
        )
        supervisor.release_lease(reason="provider_backfill_cycle_complete")
    for message in run_errors:
        append_jsonl_durable(
            runtime / ERRORS_ARTIFACT,
            {
                "schema_version": SCHEMA_VERSION,
                "generated_at": now_iso(),
                "error": message,
                "authority": authority_flags(),
            },
        )
    coverage = _coverage(source_manifest, price_manifest, preflight=build_preflight(settings))
    dashboard = build_dashboard_summary(coverage)
    store.write_json(COVERAGE_ARTIFACT, coverage)
    store.write_json(DASHBOARD_ARTIFACT, dashboard)
    return coverage, checks, run_errors
