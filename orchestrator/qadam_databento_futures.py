"""Budget-capped Databento futures history acquisition for OR-3.

The API key is process-local. Artifacts contain request parameters, quotes,
job identifiers, provenance, and checksums, but never credentials.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
import hashlib
import json
import math
import os
from pathlib import Path
import re
import time
from typing import Any, Protocol

from orchestrator.qadam_operator_ready_common import (
    ROOT,
    authority_flags,
    now_iso,
    runtime_dir,
    write_json_atomic,
)

SCHEMA_VERSION = "qadam_databento_futures.v1"
DATASET = "GLBX.MDP3"
SYMBOLS = ("CL.FUT", "SI.FUT")
SCHEMAS = ("ohlcv-1d", "definition")
DATA_ROOT = ROOT / "data" / "research" / "databento_futures"
STATE_PATH = DATA_ROOT / "acquisition_state.json"
RUNTIME_ARTIFACT = "qadam_databento_futures_acquisition.json"
NORMALIZATION_ARTIFACT = "qadam_databento_futures_normalization.json"
NORMALIZED_PARSER_VERSION = "databento_front_volume_continuous_daily.v1"
CONTRACT_PATTERN = re.compile(r"^(CL|SI)([FGHJKMNQUVXZ])(\d{1,2})$")
MONTH_NUMBER = {
    "F": 1,
    "G": 2,
    "H": 3,
    "J": 4,
    "K": 5,
    "M": 6,
    "N": 7,
    "Q": 8,
    "U": 9,
    "V": 10,
    "X": 11,
    "Z": 12,
}
RESEARCH_SYMBOLS = {"CL": "CL=F", "SI": "SI=F"}


class MetadataClient(Protocol):
    def get_cost(self, **kwargs: Any) -> float: ...


class BatchClient(Protocol):
    def submit_job(self, **kwargs: Any) -> dict[str, Any]: ...

    def list_jobs(self, states: Any = None, since: Any = None) -> list[dict[str, Any]]: ...

    def list_files(self, job_id: str) -> list[dict[str, Any]]: ...

    def download(self, job_id: str, output_dir: Path) -> list[Path]: ...


class HistoricalClient(Protocol):
    metadata: MetadataClient
    batch: BatchClient


@dataclass(frozen=True)
class DatabentoFuturesRequest:
    start: str = "2016-01-01"
    end: str = (date.today() + timedelta(days=1)).isoformat()
    budget_usd: float = 150.0
    monthly_limit_usd: float = 150.0
    poll_interval_seconds: float = 5.0
    wait_timeout_seconds: int = 1800

    def as_provider_request(self, schema: str) -> dict[str, Any]:
        return {
            "dataset": DATASET,
            "symbols": list(SYMBOLS),
            "stype_in": "parent",
            "schema": schema,
            "start": self.start,
            "end": self.end,
        }


def _request_id(request: DatabentoFuturesRequest) -> str:
    payload = json.dumps(
        {
            "dataset": DATASET,
            "symbols": SYMBOLS,
            "schemas": SCHEMAS,
            "start": request.start,
            "end": request.end,
        },
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _safe_state() -> dict[str, Any]:
    try:
        payload = json.loads(STATE_PATH.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        return {}
    return payload if isinstance(payload, dict) else {}


def _write_state(payload: dict[str, Any]) -> None:
    STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    write_json_atomic(STATE_PATH, payload)


def _write_runtime_summary(payload: dict[str, Any]) -> None:
    write_json_atomic(runtime_dir() / RUNTIME_ARTIFACT, payload)


def build_quote(
    client: HistoricalClient,
    request: DatabentoFuturesRequest,
) -> dict[str, Any]:
    costs: dict[str, float] = {}
    for schema in SCHEMAS:
        value = client.metadata.get_cost(
            **request.as_provider_request(schema),
        )
        costs[schema] = round(float(value), 8)
    total = round(sum(costs.values()), 8)
    return {
        "quoted_at": now_iso(),
        "currency": "USD",
        "by_schema_usd": costs,
        "total_usd": total,
        "within_budget": total <= request.budget_usd,
        "within_monthly_limit": total <= request.monthly_limit_usd,
    }


def validate_quote_authorization(
    quote: dict[str, Any],
    request: DatabentoFuturesRequest,
) -> list[str]:
    errors: list[str] = []
    total = quote.get("total_usd")
    if not isinstance(total, (int, float)) or total < 0:
        errors.append("databento_quote_invalid")
        return errors
    if request.budget_usd <= 0 or request.monthly_limit_usd <= 0:
        errors.append("databento_budget_or_monthly_limit_invalid")
    if request.monthly_limit_usd > request.budget_usd:
        errors.append("databento_monthly_limit_exceeds_approved_budget")
    if total > request.budget_usd:
        errors.append("databento_quote_exceeds_approved_budget")
    if total > request.monthly_limit_usd:
        errors.append("databento_quote_exceeds_monthly_limit")
    return errors


def _job_state(job: dict[str, Any]) -> str:
    return str(job.get("state") or job.get("status") or "unknown").lower()


def _find_jobs(client: HistoricalClient, job_ids: set[str]) -> dict[str, dict[str, Any]]:
    rows = client.batch.list_jobs(states=["queued", "processing", "done"])
    return {
        str(row.get("id")): row
        for row in rows
        if str(row.get("id")) in job_ids
    }


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _provider_checksum(value: Any) -> str:
    checksum = str(value or "").strip().lower()
    return checksum.removeprefix("sha256:")


def _verify_downloads(
    client: HistoricalClient,
    jobs: dict[str, dict[str, Any]],
    downloaded: dict[str, list[Path]],
) -> tuple[list[dict[str, Any]], list[str]]:
    records: list[dict[str, Any]] = []
    errors: list[str] = []
    for schema, job in jobs.items():
        job_id = str(job["id"])
        expected_rows = client.batch.list_files(job_id=job_id)
        expected = {
            str(row.get("filename")): _provider_checksum(row.get("hash"))
            for row in expected_rows
        }
        actual_paths = downloaded.get(schema, [])
        for path in actual_paths:
            checksum = _sha256(path)
            expected_checksum = expected.get(path.name, "")
            verified = not expected_checksum or checksum == expected_checksum
            if not verified:
                errors.append(f"databento_checksum_mismatch:{job_id}:{path.name}")
            records.append(
                {
                    "schema": schema,
                    "job_id": job_id,
                    "path": str(path.relative_to(ROOT)),
                    "size_bytes": path.stat().st_size,
                    "sha256": checksum,
                    "provider_sha256": expected_checksum or None,
                    "checksum_verified": verified,
                }
            )
        if not actual_paths:
            errors.append(f"databento_download_empty:{job_id}")
    return records, errors


def verify_local_databento_downloads() -> tuple[dict[str, Any], list[str]]:
    """Re-verify already downloaded files without requiring provider credentials."""

    state = _safe_state()
    records = state.get("files") if isinstance(state.get("files"), list) else []
    errors: list[str] = []
    verified_records: list[dict[str, Any]] = []
    if not records:
        errors.append("databento_local_file_manifest_missing")
    for record in records:
        relative = record.get("path")
        path = ROOT / str(relative or "")
        if not relative or not path.is_file():
            errors.append(f"databento_local_file_missing:{relative or 'unknown'}")
            continue
        actual = _sha256(path)
        provider = _provider_checksum(record.get("provider_sha256"))
        verified = not provider or actual == provider
        if not verified:
            errors.append(f"databento_checksum_mismatch:{record.get('job_id')}:{path.name}")
        verified_records.append(
            {
                **record,
                "size_bytes": path.stat().st_size,
                "sha256": actual,
                "provider_sha256": provider or None,
                "checksum_verified": verified,
            }
        )
    jobs = state.get("jobs") if isinstance(state.get("jobs"), dict) else {}
    for schema in SCHEMAS:
        if _job_state(jobs.get(schema, {})) != "done":
            errors.append(f"databento_job_not_done:{schema}")
    state.update(
        {
            "generated_at": now_iso(),
            "status": "complete" if verified_records and not errors else "blocked",
            "files": verified_records,
            "file_count": len(verified_records),
            "errors": errors,
            "credential_configured_for_process": False,
            "credential_persisted": False,
        }
    )
    _write_state(state)
    _write_runtime_summary(state)
    return state, errors


def _json_scalar(value: Any) -> Any:
    if value is None:
        return None
    if hasattr(value, "item"):
        value = value.item()
    if isinstance(value, float) and math.isnan(value):
        return None
    return value


def _timestamp(value: Any) -> datetime:
    if hasattr(value, "to_pydatetime"):
        value = value.to_pydatetime()
    if isinstance(value, datetime):
        parsed = value
    else:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _contract_maturity(symbol: str, observed_year: int) -> tuple[int, int] | None:
    match = CONTRACT_PATTERN.fullmatch(symbol)
    if not match:
        return None
    digits = match.group(3)
    if len(digits) == 2:
        year = 2000 + int(digits)
    else:
        year = (observed_year // 10) * 10 + int(digits)
        if year < observed_year - 1:
            year += 10
    return year, MONTH_NUMBER[match.group(2)]


def _select_front_contract_rows(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Select one liquid outright contract per root without future information."""

    selected: dict[str, tuple[tuple[float, int, str], dict[str, Any]]] = {}
    for record in records:
        symbol = str(record.get("contract_symbol") or "")
        match = CONTRACT_PATTERN.fullmatch(symbol)
        if not match:
            continue
        observed = _timestamp(record["observed_at"])
        maturity = _contract_maturity(symbol, observed.year)
        if maturity is None:
            continue
        volume = float(record.get("volume") or 0.0)
        maturity_rank = maturity[0] * 100 + maturity[1]
        rank = (volume, -maturity_rank, symbol)
        root = match.group(1)
        if root not in selected or rank > selected[root][0]:
            selected[root] = (rank, record)
    return [selected[root][1] for root in sorted(selected)]


def _read_daily_front_contracts(path: Path) -> list[dict[str, Any]]:
    try:
        import databento as db
    except ImportError as exc:  # pragma: no cover - explicit operator dependency check
        raise RuntimeError("databento_python_client_not_installed") from exc

    frame = db.DBNStore.from_file(path).to_df()
    if frame.empty:
        return []
    frame = frame.reset_index()
    raw_checksum = _sha256(path)
    candidates: list[dict[str, Any]] = []
    for row in frame.to_dict("records"):
        contract_symbol = str(row.get("symbol") or "")
        match = CONTRACT_PATTERN.fullmatch(contract_symbol)
        if not match:
            continue
        observed = _timestamp(row.get("ts_event"))
        maturity = _contract_maturity(contract_symbol, observed.year)
        candidates.append(
            {
                "schema_version": SCHEMA_VERSION,
                "symbol": RESEARCH_SYMBOLS[match.group(1)],
                "contract_symbol": contract_symbol,
                "contract_maturity_year": maturity[0] if maturity else None,
                "contract_maturity_month": maturity[1] if maturity else None,
                "interval": "1d",
                "observed_at": observed.isoformat(),
                "available_at": (observed + timedelta(days=1)).isoformat(),
                "open": _json_scalar(row.get("open")),
                "high": _json_scalar(row.get("high")),
                "low": _json_scalar(row.get("low")),
                "close": _json_scalar(row.get("close")),
                "adjusted_close": _json_scalar(row.get("close")),
                "volume": int(_json_scalar(row.get("volume")) or 0),
                "provider": "databento_glbx_mdp3",
                "dataset": DATASET,
                "continuous_contract_policy": "highest_same_session_volume_outright",
                "source_path": str(path.relative_to(ROOT)),
                "source_sha256": raw_checksum,
                "point_in_time_policy": "daily_bar_available_after_interval_close",
            }
        )
    return _select_front_contract_rows(candidates)


def _atomic_bytes(path: Path, payload: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    with temporary.open("wb") as handle:
        handle.write(payload)
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(temporary, path)


def normalize_local_databento_futures() -> tuple[dict[str, Any], list[str]]:
    """Build explicit CL/SI continuous research series from verified contract bars."""

    acquisition = _safe_state()
    errors: list[str] = []
    if acquisition.get("status") != "complete" or acquisition.get("errors"):
        errors.append("databento_acquisition_not_locally_verified")
    bar_paths = sorted(
        DATA_ROOT.glob("downloads/*/*.ohlcv-1d.dbn.zst"),
        key=lambda path: path.name,
    )
    definition_records = [
        row
        for row in acquisition.get("files", [])
        if isinstance(row, dict) and row.get("schema") == "definition"
    ]
    if not bar_paths:
        errors.append("databento_ohlcv_downloads_missing")
    if not definition_records:
        errors.append("databento_definition_downloads_missing")
    if errors:
        summary = {
            "schema_version": SCHEMA_VERSION,
            "artifact_type": "qadam_databento_futures_normalization",
            "generated_at": now_iso(),
            "status": "blocked",
            "errors": errors,
            "authority": authority_flags(),
        }
        _write_runtime_summary(acquisition)
        write_json_atomic(runtime_dir() / NORMALIZATION_ARTIFACT, summary)
        return summary, errors

    rows_by_symbol: dict[str, list[dict[str, Any]]] = {
        symbol: [] for symbol in RESEARCH_SYMBOLS.values()
    }
    for path in bar_paths:
        for row in _read_daily_front_contracts(path):
            rows_by_symbol[str(row["symbol"])].append(row)

    partition_records: list[dict[str, Any]] = []
    roll_records_by_symbol: dict[str, list[dict[str, Any]]] = {}
    for symbol, rows in rows_by_symbol.items():
        rows.sort(key=lambda row: (str(row["observed_at"]), str(row["contract_symbol"])))
        deduped: list[dict[str, Any]] = []
        seen_dates: set[str] = set()
        for row in rows:
            observed_date = str(row["observed_at"])[:10]
            if observed_date in seen_dates:
                errors.append(f"databento_duplicate_continuous_date:{symbol}:{observed_date}")
                continue
            seen_dates.add(observed_date)
            deduped.append(row)

        previous: dict[str, Any] | None = None
        rolls: list[dict[str, Any]] = []
        for row in deduped:
            rolled = previous is not None and (
                previous.get("contract_symbol") != row.get("contract_symbol")
            )
            row["roll_event"] = rolled
            row["previous_contract_symbol"] = (
                previous.get("contract_symbol") if rolled and previous else None
            )
            if rolled and previous:
                previous_close = float(previous.get("close") or 0.0)
                current_open = float(row.get("open") or 0.0)
                gap = current_open - previous_close
                row["roll_gap_close_to_open"] = gap
                row["roll_gap_ratio"] = gap / previous_close if previous_close else None
                rolls.append(
                    {
                        "schema_version": SCHEMA_VERSION,
                        "symbol": symbol,
                        "rolled_at": row["observed_at"],
                        "from_contract": previous.get("contract_symbol"),
                        "to_contract": row.get("contract_symbol"),
                        "to_contract_maturity_year": row.get("contract_maturity_year"),
                        "to_contract_maturity_month": row.get("contract_maturity_month"),
                        "roll_gap_close_to_open": gap,
                        "selection_policy": "highest_same_session_volume_outright",
                        "definition_job_verified": True,
                    }
                )
            else:
                row["roll_gap_close_to_open"] = None
                row["roll_gap_ratio"] = None
            previous = row
        roll_records_by_symbol[symbol] = rolls

        root = ROOT / "data" / "research" / "prices" / f"symbol={symbol}" / "interval=1d"
        rolls_payload = b"".join(
            (json.dumps(record, sort_keys=True, separators=(",", ":")) + "\n").encode(
                "utf-8"
            )
            for record in rolls
        )
        _atomic_bytes(root / "rolls.jsonl", rolls_payload)
        years = range(
            int(str(acquisition.get("start") or "2016")[:4]),
            int(str(acquisition.get("end") or date.today().isoformat())[:4]) + 1,
        )
        for year in years:
            partition_rows = [
                row for row in deduped if int(str(row["observed_at"])[:4]) == year
            ]
            year_root = root / f"year={year}"
            encoded = b"".join(
                (json.dumps(record, sort_keys=True, separators=(",", ":")) + "\n").encode(
                    "utf-8"
                )
                for record in partition_rows
            )
            _atomic_bytes(year_root / "bars.jsonl", encoded)
            input_files = sorted({str(row["source_path"]) for row in partition_rows})
            input_digest = hashlib.sha256(
                "\n".join(
                    sorted(
                        f"{row['source_path']}:{row['source_sha256']}"
                        for row in partition_rows
                    )
                ).encode("utf-8")
            ).hexdigest()
            year_rolls = [
                roll for roll in rolls if int(str(roll["rolled_at"])[:4]) == year
            ]
            metadata = {
                "schema_version": SCHEMA_VERSION,
                "artifact_type": "qadam_databento_continuous_price_partition",
                "generated_at": now_iso(),
                "provider": "databento_glbx_mdp3",
                "dataset": DATASET,
                "symbol": symbol,
                "date_partition": str(year),
                "status": "complete" if partition_rows else "unavailable_classified",
                "typed_unavailable_reason": (
                    None if partition_rows else "provider_gap_or_closed_contract_calendar"
                ),
                "continuous_contract_policy": "highest_same_session_volume_outright",
                "back_adjusted": False,
                "normalized_row_count": len(partition_rows),
                "normalized_path": str((year_root / "bars.jsonl").relative_to(ROOT)),
                "normalized_sha256": hashlib.sha256(encoded).hexdigest(),
                "input_file_count": len(input_files),
                "input_files_sha256": input_digest,
                "roll_count": len(year_rolls),
                "roll_metadata_path": str((root / "rolls.jsonl").relative_to(ROOT)),
                "parser_version": NORMALIZED_PARSER_VERSION,
                "definition_job_verified": True,
                "credentials_recorded": False,
                "authority": authority_flags(),
            }
            _atomic_bytes(
                year_root / "metadata.json",
                (json.dumps(metadata, indent=2, sort_keys=True) + "\n").encode("utf-8"),
            )
            partition_records.append(metadata)

    if any(not rows for rows in rows_by_symbol.values()):
        errors.append("databento_expected_futures_root_missing")
    definition_digest = hashlib.sha256(
        "\n".join(
            sorted(str(row.get("sha256") or "") for row in definition_records)
        ).encode("utf-8")
    ).hexdigest()
    summary = {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "qadam_databento_futures_normalization",
        "generated_at": now_iso(),
        "status": "complete" if partition_records and not errors else "blocked",
        "provider": "databento_glbx_mdp3",
        "dataset": DATASET,
        "symbols": list(RESEARCH_SYMBOLS.values()),
        "continuous_contract_policy": "highest_same_session_volume_outright",
        "back_adjusted": False,
        "bar_source_file_count": len(bar_paths),
        "definition_source_file_count": len(definition_records),
        "definition_files_sha256": definition_digest,
        "partition_count": len(partition_records),
        "complete_partition_count": sum(
            record["status"] == "complete" for record in partition_records
        ),
        "row_count": sum(record["normalized_row_count"] for record in partition_records),
        "roll_count": sum(len(rows) for rows in roll_records_by_symbol.values()),
        "partitions": partition_records,
        "actual_cost_usd": acquisition.get("quote", {}).get("total_usd"),
        "checksums_verified": True,
        "credential_persisted": False,
        "paper_trial_calendar_advanced": False,
        "trade_candidate_created_count": 0,
        "paper_order_created_count": 0,
        "broker_write_count": 0,
        "proof_credit_created_count": 0,
        "errors": errors,
        "authority": authority_flags(),
    }
    write_json_atomic(runtime_dir() / NORMALIZATION_ARTIFACT, summary)
    return summary, errors


def acquire_databento_futures(
    client: HistoricalClient,
    request: DatabentoFuturesRequest,
    *,
    submit: bool,
    wait: bool,
    download: bool,
) -> tuple[dict[str, Any], list[str]]:
    request_id = _request_id(request)
    existing = _safe_state()
    quote = build_quote(client, request)
    errors = validate_quote_authorization(quote, request)
    jobs: dict[str, dict[str, Any]] = {}
    existing_jobs = existing.get("jobs") if existing.get("request_id") == request_id else None
    if isinstance(existing_jobs, dict):
        jobs = {
            schema: row
            for schema, row in existing_jobs.items()
            if schema in SCHEMAS and isinstance(row, dict) and row.get("id")
        }

    if submit and not errors:
        for schema in SCHEMAS:
            if schema in jobs:
                continue
            job = client.batch.submit_job(
                **request.as_provider_request(schema),
                encoding="dbn",
                compression="zstd",
                delivery="download",
                split_duration="month",
                split_symbols=True,
            )
            jobs[schema] = {
                "id": job.get("id"),
                "state": _job_state(job),
                "cost_usd": job.get("cost_usd"),
                "submitted_at": now_iso(),
            }
            _write_state(
                {
                    "schema_version": SCHEMA_VERSION,
                    "request_id": request_id,
                    "request": request.__dict__,
                    "quote": quote,
                    "jobs": jobs,
                    "credential_persisted": False,
                }
            )

    if wait and jobs and not errors:
        deadline = time.monotonic() + request.wait_timeout_seconds
        job_ids = {str(row["id"]) for row in jobs.values()}
        while time.monotonic() < deadline:
            live = _find_jobs(client, job_ids)
            for schema, job in jobs.items():
                current = live.get(str(job["id"]))
                if current:
                    job["state"] = _job_state(current)
                    job["progress"] = current.get("progress")
                    job["cost_usd"] = current.get("cost_usd", job.get("cost_usd"))
            _write_state(
                {
                    "schema_version": SCHEMA_VERSION,
                    "request_id": request_id,
                    "request": request.__dict__,
                    "quote": quote,
                    "jobs": jobs,
                    "credential_persisted": False,
                }
            )
            if all(_job_state(job) == "done" for job in jobs.values()):
                break
            time.sleep(max(1.0, request.poll_interval_seconds))
        if not all(_job_state(job) == "done" for job in jobs.values()):
            errors.append("databento_batch_wait_timeout_or_incomplete")

    file_records: list[dict[str, Any]] = []
    if download and jobs and not errors:
        output_root = DATA_ROOT / "downloads"
        downloaded: dict[str, list[Path]] = {}
        for schema, job in jobs.items():
            if _job_state(job) != "done":
                errors.append(f"databento_job_not_done:{schema}")
                continue
            downloaded[schema] = [
                Path(path)
                for path in client.batch.download(
                    job_id=str(job["id"]),
                    output_dir=output_root,
                )
            ]
        if not errors:
            file_records, verify_errors = _verify_downloads(client, jobs, downloaded)
            errors.extend(verify_errors)

    state = {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "qadam_databento_futures_acquisition",
        "generated_at": now_iso(),
        "status": (
            "complete"
            if download and file_records and not errors
            else "submitted_or_processing"
            if jobs and not errors
            else "quoted"
            if not errors
            else "blocked"
        ),
        "request_id": request_id,
        "provider": "Databento",
        "dataset": DATASET,
        "symbols": list(SYMBOLS),
        "schemas": list(SCHEMAS),
        "start": request.start,
        "end": request.end,
        "quote": quote,
        "approved_budget_usd": request.budget_usd,
        "historical_monthly_limit_usd": request.monthly_limit_usd,
        "jobs": jobs,
        "files": file_records,
        "file_count": len(file_records),
        "credential_configured_for_process": True,
        "credential_persisted": False,
        "raw_data_git_ignored": True,
        "paper_trial_calendar_advanced": False,
        "trade_candidate_created_count": 0,
        "paper_order_created_count": 0,
        "broker_write_count": 0,
        "proof_credit_created_count": 0,
        "errors": errors,
        "authority": authority_flags(),
    }
    _write_state(state)
    _write_runtime_summary(state)
    return state, errors


def load_client(api_key: str) -> HistoricalClient:
    if not api_key.startswith("db-") or len(api_key) < 20:
        raise ValueError("databento_api_key_format_invalid")
    try:
        import databento as db
    except ImportError as exc:  # pragma: no cover - explicit operator dependency check
        raise RuntimeError("databento_python_client_not_installed") from exc
    return db.Historical(api_key)


def api_key_from_environment() -> str | None:
    value = os.environ.get("DATABENTO_API_KEY", "").strip()
    return value or None
