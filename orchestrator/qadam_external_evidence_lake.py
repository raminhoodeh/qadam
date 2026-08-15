"""Immutable, point-in-time evidence lake for approved external documents."""

from __future__ import annotations

from collections import Counter, defaultdict
from datetime import datetime, timezone
import json
from pathlib import Path
import re
from typing import Any

from orchestrator.config import Settings
from orchestrator.qadam_canonical_contracts import AtomicArtifactStore
from orchestrator.qadam_qualitative_common import (
    EXTERNAL_DOCUMENTS_ARTIFACT,
    EXTERNAL_MANIFEST_ARTIFACT,
    EXTERNAL_PROVENANCE_ARTIFACT,
    EXTERNAL_SECURITY_ARTIFACT,
    now_iso,
    public_authority,
    read_jsonl,
    repo_root,
    research_root,
    runtime_dir,
    sha256_json,
    stable_id,
    unique,
)

SCHEMA_VERSION = "qadam_external_document.v1"
PARSER_VERSION = "qadam_external_evidence_lake.v1"
MAX_PUBLIC_SUPPORTING_TEXT = 240

_INJECTION_PATTERNS = (
    r"ignore (all |any )?(previous|prior|system) instructions",
    r"reveal (the )?(system prompt|credentials|api key)",
    r"you are now ",
    r"developer message",
    r"execute (this )?(command|shell)",
)
_SECRET_PATTERNS = (
    r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----",
    r"\b(?:sk|pk|db)-[A-Za-z0-9_-]{20,}\b",
    r"\bBearer\s+[A-Za-z0-9._~-]{20,}\b",
)


def _inside(path: Path, root: Path) -> bool:
    try:
        path.resolve().relative_to(root.resolve())
    except (OSError, ValueError):
        return False
    return True


def _availability(row: dict[str, Any]) -> tuple[str | None, str]:
    published = str(row.get("published_at") or "").strip()
    if published:
        candidate = published
        if re.fullmatch(r"\d{4}-\d{2}-\d{2}", candidate):
            candidate += "T00:00:00+00:00"
        try:
            parsed = datetime.fromisoformat(candidate.replace("Z", "+00:00"))
        except ValueError:
            parsed = None
        if parsed is not None:
            if parsed.tzinfo is None:
                parsed = parsed.replace(tzinfo=timezone.utc)
            return parsed.astimezone(timezone.utc).isoformat(), "published_time_or_date"
    retrieved = str(row.get("retrieved_at") or "").strip()
    return (retrieved or None), "first_retrieval_only"


def _security(text: str) -> dict[str, Any]:
    lowered = text.lower()
    injections = [pattern for pattern in _INJECTION_PATTERNS if re.search(pattern, lowered)]
    secrets = [pattern for pattern in _SECRET_PATTERNS if re.search(pattern, text, re.I)]
    hidden = "display:none" in lowered or "visibility:hidden" in lowered
    return {
        "prompt_injection_state": "detected" if injections else "clear",
        "prompt_injection_match_count": len(injections),
        "secret_scan_state": "detected" if secrets else "clear",
        "secret_match_count": len(secrets),
        "hidden_text_state": "detected" if hidden else "clear",
        "pii_classification": "public_origin_content_unclassified",
        "quarantine_state": "quarantined" if injections or secrets or hidden else "cleared",
    }


def build_external_evidence_lake(
    settings: Settings | None = None,
) -> tuple[dict[str, Any], list[str]]:
    runtime = runtime_dir(settings)
    research = research_root()
    normalized_root = research / "normalized"
    lake_root = research / "evidence_lake"
    lake_root.mkdir(parents=True, exist_ok=True)
    manifest = read_jsonl(runtime / EXTERNAL_MANIFEST_ARTIFACT)
    errors: list[str] = []
    public_rows: list[dict[str, Any]] = []
    security_rows: list[dict[str, Any]] = []
    revision_groups: dict[str, list[dict[str, Any]]] = defaultdict(list)

    for row in manifest:
        document_id = str(row.get("document_id") or "")
        ref = repo_root() / str(row.get("normalized_text_ref") or "")
        reasons: list[str] = []
        if not document_id:
            reasons.append("document_id_missing")
        if not _inside(ref, normalized_root):
            reasons.append("normalized_text_ref_outside_approved_root")
        payload: dict[str, Any] = {}
        if not reasons:
            try:
                loaded = json.loads(ref.read_text(encoding="utf-8"))
                payload = loaded if isinstance(loaded, dict) else {}
            except (OSError, json.JSONDecodeError):
                reasons.append("normalized_text_unreadable")
        text = str(payload.get("text") or "")
        content_hash = sha256_json(text)
        if payload and content_hash != str(row.get("content_sha256") or ""):
            reasons.append("normalized_text_hash_mismatch")
        available_at, availability_basis = _availability(row)
        if not available_at:
            reasons.append("availability_time_missing")
        safety = _security(text)
        if safety["quarantine_state"] == "quarantined":
            reasons.append("security_quarantine")
        security_rows.append(
            {
                "document_id": document_id,
                **safety,
                "reasons": unique(reasons),
            }
        )
        eligible = not reasons and bool(text.strip())
        if not text.strip():
            reasons.append("document_text_empty")
            eligible = False
        internal = {
            "schema_version": SCHEMA_VERSION,
            "document_id": document_id,
            "origin_id": row.get("evidence_origin"),
            "canonical_url": row.get("canonical_url"),
            "published_at": row.get("published_at"),
            "first_seen_at": row.get("first_seen_at"),
            "retrieved_at": row.get("retrieved_at"),
            "available_at": available_at,
            "availability_basis": availability_basis,
            "raw_hash": row.get("retrieval_content_sha256"),
            "normalized_text_hash": content_hash,
            "parser_version": PARSER_VERSION,
            "text": text,
            "security": safety,
        }
        internal_path = lake_root / f"{document_id.replace(':', '_')}.json"
        internal_path.write_text(json.dumps(internal, sort_keys=True) + "\n", encoding="utf-8")
        revision_key = str(row.get("canonical_url") or row.get("title") or document_id)
        revision_groups[revision_key].append(row)
        public_rows.append(
            {
                "schema_version": SCHEMA_VERSION,
                "artifact_type": "qadam_external_document",
                "document_id": document_id,
                "canonical_url": row.get("canonical_url"),
                "origin_domain": str(row.get("canonical_url") or "").split("/")[2] if str(row.get("canonical_url") or "").startswith("http") else None,
                "origin_id": row.get("evidence_origin"),
                "origin_type": row.get("origin_class"),
                "transport": row.get("retrieval_transport"),
                "event_time": row.get("published_at"),
                "publication_time": row.get("published_at"),
                "first_seen_time": row.get("first_seen_at"),
                "retrieval_time": row.get("retrieved_at"),
                "availability_time": available_at,
                "availability_basis": availability_basis,
                "publication_time_confidence": row.get("publication_time_confidence"),
                "raw_hash": row.get("retrieval_content_sha256"),
                "normalized_text_hash": content_hash,
                "parser_version": PARSER_VERSION,
                "retrieval_version": row.get("retrieval_id"),
                "media_type": row.get("content_type"),
                "language": "en",
                "title": row.get("title"),
                "bounded_supporting_text": text[:MAX_PUBLIC_SUPPORTING_TEXT],
                "publisher": row.get("evidence_origin"),
                "trust_tier": row.get("trust_tier"),
                "independence_cluster": row.get("independence_cluster"),
                "strategy_family_ids": row.get("strategy_family_ids") or [],
                "instrument_symbols": row.get("instrument_symbols") or [],
                "terms_review_state": row.get("terms_state"),
                "retention_class": "ignored_internal_normalized_text",
                "redistribution_class": "public_safe_metadata_and_short_span",
                "expiry": None,
                "security": safety,
                "research_eligible": eligible,
                "ineligibility_reasons": unique(reasons),
                "source_quorum_credit_allowed": False,
                "authority": public_authority(),
            }
        )

    revisions: dict[str, dict[str, Any]] = {}
    for rows in revision_groups.values():
        ordered = sorted(rows, key=lambda item: str(item.get("retrieved_at") or ""))
        previous_id: str | None = None
        for row in ordered:
            revisions[str(row.get("document_id"))] = {
                "supersedes_document_id": previous_id,
                "revision_index": ordered.index(row),
            }
            previous_id = str(row.get("document_id"))
    for row in public_rows:
        row["revision"] = revisions.get(str(row.get("document_id")), {})

    public_rows.sort(key=lambda item: str(item.get("document_id") or ""))
    store = AtomicArtifactStore(runtime)
    store.write_jsonl(EXTERNAL_DOCUMENTS_ARTIFACT, public_rows)
    security_audit = {
        "schema_version": "qadam_external_evidence_security_audit.v1",
        "artifact_type": "qadam_external_evidence_security_audit",
        "generated_at": now_iso(),
        "status": "passed" if not any(row["quarantine_state"] == "quarantined" for row in security_rows) else "passed_with_quarantine",
        "document_count": len(public_rows),
        "quarantined_count": sum(row["quarantine_state"] == "quarantined" for row in security_rows),
        "empty_document_count": sum("document_text_empty" in row["reasons"] for row in security_rows),
        "records": security_rows,
        "quarantined_content_reaches_models": False,
        "authority": public_authority(),
    }
    provenance_audit = {
        "schema_version": "qadam_external_evidence_provenance_audit.v1",
        "artifact_type": "qadam_external_evidence_provenance_audit",
        "generated_at": security_audit["generated_at"],
        "status": "passed" if not errors else "blocked",
        "manifest_count": len(manifest),
        "document_count": len(public_rows),
        "research_eligible_count": sum(bool(row["research_eligible"]) for row in public_rows),
        "origin_counts": dict(sorted(Counter(str(row.get("origin_id")) for row in public_rows).items())),
        "revision_chain_count": sum(bool(row.get("revision", {}).get("supersedes_document_id")) for row in public_rows),
        "point_in_time_reproducible": all(bool(row.get("availability_time")) for row in public_rows),
        "public_artifacts_contain_local_paths": False,
        "public_artifacts_contain_full_raw_text": False,
        "validation_errors": errors,
        "authority": public_authority(),
    }
    store.write_json(EXTERNAL_SECURITY_ARTIFACT, security_audit)
    store.write_json(EXTERNAL_PROVENANCE_ARTIFACT, provenance_audit)
    return {"documents": public_rows, "security": security_audit, "provenance": provenance_audit}, errors


__all__ = ["build_external_evidence_lake"]
