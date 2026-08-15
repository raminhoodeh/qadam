"""Bounded zero-auth acquisition for approved qualitative origins."""

from __future__ import annotations

from datetime import datetime, timezone
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
from typing import Any
import xml.etree.ElementTree as ET

from orchestrator.config import Settings
from orchestrator.qadam_canonical_contracts import AtomicArtifactStore
from orchestrator.qadam_qualitative_common import (
    COMMAND_POLICY_PATH,
    EXTERNAL_ACQUISITION_ARTIFACT,
    EXTERNAL_CHANNEL_HEALTH_ARTIFACT,
    EXTERNAL_MANIFEST_ARTIFACT,
    ORIGIN_REGISTRY_PATH,
    now_iso,
    public_authority,
    read_json,
    read_jsonl,
    repo_root,
    research_root,
    runtime_dir,
    sha256_json,
    stable_id,
)


def _filtered_env(policy: dict[str, Any]) -> dict[str, str]:
    allowed = set(policy.get("environment_allowlist") or [])
    return {key: value for key, value in os.environ.items() if key in allowed}


def _sandbox_profile(worker: Path, request: Path, spool: Path) -> str:
    home = str(Path.home().resolve())
    python_runtime = str(Path(sys.executable).resolve().parents[1])
    return (
        '(version 1) '
        '(deny default) '
        '(allow process*) (allow sysctl-read) (allow mach-lookup) '
        f'(allow file-read* (require-not (subpath "{home}"))) '
        f'(allow file-read* (subpath "{python_runtime}") (subpath "{spool}") (literal "{worker}") (literal "{request}")) '
        f'(allow file-write* (subpath "{spool}")) '
        '(allow network*)'
    )


def _run_worker(request: dict[str, Any], spool: Path, policy: dict[str, Any]) -> dict[str, Any]:
    spool.mkdir(parents=True, exist_ok=True)
    request_path = spool / f"{request['request_id']}.request.json"
    response_path = spool / f"{request['request_id']}.response.json"
    request_path.write_text(json.dumps(request, sort_keys=True) + "\n", encoding="utf-8")
    worker = (repo_root() / str(policy.get("allowed_worker"))).resolve()
    python = Path(sys.executable).resolve()
    command = [str(python), "-I", str(worker), str(request_path), str(response_path)]
    sandbox = shutil.which("sandbox-exec")
    if sandbox:
        command = [sandbox, "-p", _sandbox_profile(worker, request_path, spool), *command]
    try:
        completed = subprocess.run(
            command,
            cwd=spool,
            env=_filtered_env(policy),
            capture_output=True,
            text=True,
            timeout=int(policy.get("request_timeout_seconds") or 30) + 10,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        return {"state": "worker_error", "error": type(exc).__name__}
    if not response_path.is_file():
        return {
            "state": "worker_error",
            "error": "response_missing",
            "returncode": completed.returncode,
            "stderr": completed.stderr[-500:],
        }
    return read_json(response_path)


def _xml_entries(text: str) -> list[dict[str, Any]]:
    try:
        root = ET.fromstring(text)
    except ET.ParseError:
        return []
    rows: list[dict[str, Any]] = []
    for item in root.findall(".//item") + root.findall(".//{http://www.w3.org/2005/Atom}entry"):
        def value(name: str) -> str | None:
            node = item.find(name)
            if node is None:
                node = item.find(f"{{http://www.w3.org/2005/Atom}}{name}")
            if node is None:
                return None
            return (node.text or node.attrib.get("href") or "").strip() or None
        rows.append(
            {
                "title": value("title"),
                "url": value("link"),
                "published_at": value("pubDate") or value("published") or value("updated"),
                "text": value("description") or value("summary") or "",
            }
        )
    return rows


def _json_entries(payload: Any, origin_id: str) -> list[dict[str, Any]]:
    if isinstance(payload, list):
        return [
            {
                "title": row.get("name") or row.get("tag_name") or row.get("title"),
                "url": row.get("html_url") or row.get("url"),
                "published_at": row.get("published_at") or row.get("created_at"),
                "text": row.get("body") or row.get("description") or "",
            }
            for row in payload[:25]
            if isinstance(row, dict)
        ]
    if isinstance(payload, dict) and origin_id.startswith("sec_"):
        recent = payload.get("filings", {}).get("recent", {})
        if isinstance(recent, dict):
            accessions = recent.get("accessionNumber") or []
            forms = recent.get("form") or []
            dates = recent.get("filingDate") or []
            documents = recent.get("primaryDocument") or []
            cik = str(payload.get("cik") or "").zfill(10)
            rows = []
            for index, accession in enumerate(accessions[:40]):
                accession_compact = str(accession).replace("-", "")
                document = str(documents[index]) if index < len(documents) else ""
                rows.append(
                    {
                        "title": f"{forms[index] if index < len(forms) else 'SEC filing'} {accession}",
                        "url": f"https://www.sec.gov/Archives/edgar/data/{int(cik)}/{accession_compact}/{document}",
                        "published_at": dates[index] if index < len(dates) else None,
                        "text": f"Official SEC filing metadata for form {forms[index] if index < len(forms) else 'unknown'}.",
                    }
                )
            return rows
    if isinstance(payload, dict):
        return [{"title": payload.get("title") or origin_id, "url": None, "published_at": None, "text": json.dumps(payload)[:4000]}]
    return []


def _logical_documents(origin: dict[str, Any], result: dict[str, Any]) -> list[dict[str, Any]]:
    content = str(result.get("content_utf8") or "")
    content_type = str(result.get("content_type") or "")
    rows: list[dict[str, Any]]
    if "xml" in content_type or content.lstrip().startswith("<rss") or "<feed" in content[:500]:
        rows = _xml_entries(content)
    elif "json" in content_type or content.lstrip().startswith(("{", "[")):
        try:
            rows = _json_entries(json.loads(content), str(origin.get("origin_id") or ""))
        except json.JSONDecodeError:
            rows = []
    else:
        rows = [{"title": origin.get("display_name"), "url": result.get("final_url"), "published_at": None, "text": content[:4000]}]
    generated_at = now_iso()
    documents = []
    for row in rows:
        text = str(row.get("text") or "").strip()
        identity = sha256_json(
            {
                "origin": origin.get("origin_id"),
                "url": row.get("url"),
                "title": row.get("title"),
                "published_at": row.get("published_at"),
                "text": text,
            }
        )
        documents.append(
            {
                "schema_version": "qadam_external_retrieval_envelope.v1",
                "artifact_type": "qadam_external_document_manifest_record",
                "document_id": f"external-document:{identity[:24]}",
                "retrieval_id": result.get("request_id"),
                "generated_at": generated_at,
                "retrieved_at": result.get("retrieved_at"),
                "first_seen_at": generated_at,
                "published_at": row.get("published_at"),
                "publication_time_confidence": "provider_declared" if row.get("published_at") else "unknown",
                "retrieval_transport": origin.get("transport"),
                "evidence_origin": origin.get("origin_id"),
                "origin_class": origin.get("origin_class"),
                "trust_tier": origin.get("trust_tier"),
                "independence_cluster": origin.get("independence_cluster"),
                "title": row.get("title"),
                "canonical_url": row.get("url") or result.get("final_url"),
                "strategy_family_ids": origin.get("strategy_family_ids") or [],
                "instrument_symbols": origin.get("instrument_symbols") or [],
                "content_sha256": sha256_json(text),
                "retrieval_content_sha256": result.get("content_sha256"),
                "content_type": result.get("content_type"),
                "byte_count": len(text.encode("utf-8")),
                "raw_text": text,
                "terms_state": origin.get("terms_state"),
                "source_quorum_credit_allowed": False,
                "authority": public_authority(),
            }
        )
    return documents


def run_external_acquisition(
    settings: Settings | None = None,
    *,
    allow_network: bool = False,
    max_documents: int | None = None,
) -> tuple[dict[str, Any], list[str]]:
    runtime = runtime_dir(settings)
    research = research_root()
    spool = research / "spool"
    raw = research / "raw"
    normalized = research / "normalized"
    policy = read_json(repo_root() / COMMAND_POLICY_PATH)
    registry = read_json(repo_root() / ORIGIN_REGISTRY_PATH)
    previous = read_jsonl(runtime / EXTERNAL_MANIFEST_ARTIFACT)
    previous_status = read_json(runtime / EXTERNAL_ACQUISITION_ARTIFACT)
    previous_health = read_json(runtime / EXTERNAL_CHANNEL_HEALTH_ARTIFACT)
    prior_channels = {
        str(row.get("origin_id")): row
        for row in previous_health.get("channels") or []
        if isinstance(row, dict) and row.get("origin_id")
    }
    existing = {str(row.get("document_id")): row for row in previous if row.get("document_id")}
    origins = [row for row in registry.get("origins") or [] if isinstance(row, dict) and row.get("enabled") is True]
    limit = min(int(max_documents or policy.get("max_documents_per_run") or 24), 24)
    channel_rows = []
    errors: list[str] = []
    isolated_failures: list[str] = []
    fetched_bytes = 0
    new_added_count = 0
    if allow_network:
        for origin in origins:
            if new_added_count >= limit:
                break
            request = {
                "request_id": stable_id("external-retrieval", origin.get("origin_id"), now_iso()),
                "origin_id": origin.get("origin_id"),
                "transport": origin.get("transport"),
                "url": origin.get("url"),
                "allowed_domains": origin.get("allowed_domains") or [],
                "max_response_bytes": int(policy.get("max_response_bytes") or 2_000_000),
                "timeout_seconds": int(policy.get("request_timeout_seconds") or 30),
                "if_none_match": prior_channels.get(str(origin.get("origin_id")), {}).get("etag"),
                "if_modified_since": prior_channels.get(str(origin.get("origin_id")), {}).get("last_modified"),
            }
            result = _run_worker(request, spool, policy)
            channel_rows.append(
                {
                    "origin_id": origin.get("origin_id"),
                    "transport": origin.get("transport"),
                    "state": result.get("state"),
                    "retrieved_at": result.get("retrieved_at"),
                    "error": result.get("error"),
                    "byte_count": result.get("byte_count", 0),
                    "etag": result.get("etag") or prior_channels.get(str(origin.get("origin_id")), {}).get("etag"),
                    "last_modified": result.get("last_modified") or prior_channels.get(str(origin.get("origin_id")), {}).get("last_modified"),
                }
            )
            if result.get("state") == "not_modified":
                continue
            if result.get("state") != "retrieved":
                isolated_failures.append(f"origin_retrieval_failed:{origin.get('origin_id')}:{result.get('error') or result.get('state')}")
                continue
            fetched_bytes += int(result.get("byte_count") or 0)
            raw_dir = raw / str(origin.get("origin_id"))
            raw_dir.mkdir(parents=True, exist_ok=True)
            raw_path = raw_dir / f"{result.get('content_sha256')}.json"
            if not raw_path.exists():
                raw_path.write_text(json.dumps(result, sort_keys=True) + "\n", encoding="utf-8")
            for document in _logical_documents(origin, result):
                document_id = str(document["document_id"])
                if document_id not in existing and new_added_count >= limit:
                    break
                document["raw_artifact_ref"] = str(raw_path.relative_to(repo_root()))
                normalized_dir = normalized / str(origin.get("origin_id"))
                normalized_dir.mkdir(parents=True, exist_ok=True)
                normalized_path = normalized_dir / f"{document['document_id'].split(':', 1)[-1]}.json"
                normalized_path.write_text(
                    json.dumps(
                        {
                            "document_id": document["document_id"],
                            "content_sha256": document["content_sha256"],
                            "text": document.get("raw_text") or "",
                        },
                        sort_keys=True,
                    )
                    + "\n",
                    encoding="utf-8",
                )
                document["normalized_text_ref"] = str(normalized_path.relative_to(repo_root()))
                if document_id not in existing:
                    new_added_count += 1
                existing[document_id] = document
    else:
        channel_rows = [
            {
                "origin_id": origin.get("origin_id"),
                "transport": origin.get("transport"),
                "state": "network_not_requested",
                "retrieved_at": None,
                "error": None,
                "byte_count": 0,
                "last_network_state": prior_channels.get(
                    str(origin.get("origin_id")), {}
                ).get("last_network_state")
                or prior_channels.get(str(origin.get("origin_id")), {}).get("state"),
                "last_network_retrieved_at": prior_channels.get(
                    str(origin.get("origin_id")), {}
                ).get("last_network_retrieved_at")
                or prior_channels.get(str(origin.get("origin_id")), {}).get("retrieved_at"),
                "etag": prior_channels.get(str(origin.get("origin_id")), {}).get("etag"),
                "last_modified": prior_channels.get(
                    str(origin.get("origin_id")), {}
                ).get("last_modified"),
            }
            for origin in origins
        ]
    rows = sorted(existing.values(), key=lambda row: (str(row.get("published_at") or ""), str(row.get("document_id") or "")))
    for row in rows:
        row.pop("raw_text", None)
    store = AtomicArtifactStore(runtime)
    store.write_jsonl(EXTERNAL_MANIFEST_ARTIFACT, rows)
    network_healthy_count = sum(
        row.get("state") in {"retrieved", "not_modified"} for row in channel_rows
    )
    if allow_network:
        for row in channel_rows:
            row["last_network_state"] = row.get("state")
            row["last_network_retrieved_at"] = row.get("retrieved_at")
    last_network_attempt_at = (
        now_iso()
        if allow_network
        else previous_health.get("last_network_attempt_at")
        or previous_status.get("last_network_attempt_at")
    )
    last_successful_network_at = (
        last_network_attempt_at
        if allow_network and network_healthy_count > 0
        else previous_health.get("last_successful_network_at")
        or previous_status.get("last_successful_network_at")
    )
    ever_completed_real_network_fetch = bool(
        (allow_network and network_healthy_count > 0)
        or previous_status.get("ever_completed_real_network_fetch") is True
        or previous_health.get("ever_completed_real_network_fetch") is True
    )
    health = {
        "schema_version": "qadam_external_channel_health.v1",
        "artifact_type": "qadam_external_channel_health",
        "generated_at": now_iso(),
        "network_requested": allow_network,
        "channels": channel_rows,
        "healthy_count": network_healthy_count if allow_network else int(
            previous_health.get("last_network_healthy_count") or 0
        ),
        "last_network_healthy_count": network_healthy_count if allow_network else int(
            previous_health.get("last_network_healthy_count") or 0
        ),
        "last_network_attempt_at": last_network_attempt_at,
        "last_successful_network_at": last_successful_network_at,
        "ever_completed_real_network_fetch": ever_completed_real_network_fetch,
        "isolated_failure_count": len(isolated_failures),
        "isolated_failures": isolated_failures,
        "authority": public_authority(),
    }
    status = {
        "schema_version": "qadam_external_acquisition_status.v1",
        "artifact_type": "qadam_external_acquisition_status",
        "generated_at": health["generated_at"],
        "status": "completed" if allow_network and not isolated_failures else "completed_with_isolated_failures" if allow_network else "ready_network_not_requested",
        "enabled_origin_count": len(origins),
        "document_count": len(rows),
        "new_document_count": max(0, len(rows) - len(previous)),
        "bytes_fetched": fetched_bytes,
        "duplicate_logical_write_count": 0,
        "resumable": True,
        "idempotent": True,
        "authenticated_session_used": False,
        "last_network_attempt_at": last_network_attempt_at,
        "last_successful_network_at": last_successful_network_at,
        "last_network_healthy_count": network_healthy_count if allow_network else int(
            previous_status.get("last_network_healthy_count") or 0
        ),
        "ever_completed_real_network_fetch": ever_completed_real_network_fetch,
        "validation_errors": errors,
        "isolated_failures": isolated_failures,
        "authority": public_authority(),
    }
    store.write_json(EXTERNAL_CHANNEL_HEALTH_ARTIFACT, health)
    store.write_json(EXTERNAL_ACQUISITION_ARTIFACT, status)
    return status, errors


__all__ = ["run_external_acquisition"]
