"""Span-grounded qualitative claim extraction from cleared external evidence."""

from __future__ import annotations

from collections import Counter
import json
import re
from typing import Any

from orchestrator.config import Settings
from orchestrator.qadam_canonical_contracts import AtomicArtifactStore
from orchestrator.qadam_qualitative_common import (
    EXTERNAL_DOCUMENTS_ARTIFACT,
    QUALITATIVE_CLAIMS_ARTIFACT,
    QUALITATIVE_CLAIM_SUMMARY_ARTIFACT,
    QUALITATIVE_REJECTIONS_ARTIFACT,
    now_iso,
    public_authority,
    read_jsonl,
    repo_root,
    research_root,
    runtime_dir,
    stable_id,
)

SCHEMA_VERSION = "qadam_qualitative_claim.v1"
EXTRACTOR_VERSION = "qadam_deterministic_span_extractor.v1"

_CLAIM_RECIPES: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("demand_change", ("demand", "orders", "sales", "bookings")),
    ("capacity_change", ("capacity", "production", "output", "utilization")),
    ("backlog_change", ("backlog", "order book")),
    ("delivery_timing", ("delivery", "lead time", "shipment")),
    ("guidance_change", ("guidance", "outlook", "forecast")),
    ("margin_change", ("margin", "profitability")),
    ("capex_change", ("capital expenditure", "capex", "investment")),
    ("inventory_change", ("inventory", "stockpile", "drawdown")),
    ("regulatory_change", ("regulation", "approval", "restriction", "sanction")),
    ("supply_change", ("supply", "disruption", "shortage", "normalization")),
    ("management_confidence", ("confidence", "uncertainty", "concern")),
    ("release_or_deprecation", ("release", "deprecated", "security", "upgrade")),
)
_POSITIVE = ("increase", "raise", "strengthen", "improve", "expand", "growth", "higher", "record")
_NEGATIVE = ("decrease", "cut", "weaken", "decline", "compress", "lower", "shortage", "disruption", "delay")


def _internal_text(document_id: str) -> str:
    path = research_root() / "evidence_lake" / f"{document_id.replace(':', '_')}.json"
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return ""
    return str(value.get("text") or "") if isinstance(value, dict) else ""


def _sentences(text: str) -> list[tuple[int, int, str]]:
    rows: list[tuple[int, int, str]] = []
    start = 0
    boundaries = re.finditer(
        r"\n+|(?<=[!?])\s+|(?<=[A-Za-z0-9)\]])\.\s+(?=[A-Z])",
        text,
    )
    for boundary in boundaries:
        end = boundary.start()
        if boundary.group(0).startswith("."):
            end += 1
        raw = text[start:end]
        sentence = raw.strip()
        if sentence:
            offset = start + len(raw) - len(raw.lstrip())
            rows.append((offset, offset + len(sentence), sentence))
        start = boundary.end()
    raw = text[start:]
    sentence = raw.strip()
    if sentence:
        offset = start + len(raw) - len(raw.lstrip())
        rows.append((offset, offset + len(sentence), sentence))
    return rows


def _direction(sentence: str) -> str:
    lowered = sentence.lower()
    positive = sum(token in lowered for token in _POSITIVE)
    negative = sum(token in lowered for token in _NEGATIVE)
    if positive > negative:
        return "strengthening"
    if negative > positive:
        return "weakening"
    return "unspecified"


def _magnitude(sentence: str) -> str | None:
    match = re.search(r"(?<!\w)(?:\$?\d+(?:\.\d+)?\s?(?:%|percent|million|billion|days?|weeks?|months?|years?))", sentence, re.I)
    return match.group(0) if match else None


def extract_qualitative_claims(
    settings: Settings | None = None,
) -> tuple[dict[str, Any], list[str]]:
    runtime = runtime_dir(settings)
    documents = read_jsonl(runtime / EXTERNAL_DOCUMENTS_ARTIFACT)
    accepted: list[dict[str, Any]] = []
    rejected: list[dict[str, Any]] = []
    errors: list[str] = []
    for document in documents:
        document_id = str(document.get("document_id") or "")
        if not document.get("research_eligible"):
            rejected.append({
                "schema_version": SCHEMA_VERSION,
                "rejection_id": stable_id("claim-rejection", document_id, "ineligible"),
                "document_id": document_id,
                "reason": "document_not_research_eligible",
                "authority": public_authority(),
            })
            continue
        text = _internal_text(document_id)
        matched = 0
        for start, end, sentence in _sentences(text):
            lowered = sentence.lower()
            claim_type = next((kind for kind, terms in _CLAIM_RECIPES if any(term in lowered for term in terms)), None)
            if claim_type is None or len(sentence) < 20:
                continue
            matched += 1
            direction = _direction(sentence)
            magnitude = _magnitude(sentence)
            subject = str(document.get("publisher") or document.get("origin_id") or "unknown")
            claim_id = stable_id("qualitative-claim", document_id, start, end, claim_type)
            accepted.append({
                "schema_version": SCHEMA_VERSION,
                "artifact_type": "qadam_qualitative_claim",
                "claim_id": claim_id,
                "document_id": document_id,
                "claim_type": claim_type,
                "subject": subject,
                "predicate": claim_type,
                "object": sentence[:240],
                "speaker_identity": subject,
                "speaker_role": "official_origin",
                "affected_entities": [],
                "affected_products": [],
                "affected_geographies": [],
                "affected_time_period": None,
                "direction": direction,
                "magnitude": magnitude,
                "supporting_span": {"start": start, "end": end, "text": sentence},
                "extraction_model": EXTRACTOR_VERSION,
                "extraction_confidence": 0.82 if direction != "unspecified" else 0.68,
                "source_trust": document.get("trust_tier"),
                "novelty_state": "unreviewed",
                "contradiction_claim_ids": [],
                "corroboration_claim_ids": [],
                "strategy_family_hypotheses": document.get("strategy_family_ids") or [],
                "instrument_hypotheses": document.get("instrument_symbols") or [],
                "falsifier": "The declared relationship does not recur on point-in-time forward outcomes after costs.",
                "model_review_state": "candidate_extracted",
                "independence_cluster": document.get("independence_cluster"),
                "availability_time": document.get("availability_time"),
                "prompt_version": "deterministic_claim_recipe.v1",
                "source_quorum_credit_allowed": False,
                "authority": public_authority(),
            })
        if matched == 0:
            rejected.append({
                "schema_version": SCHEMA_VERSION,
                "rejection_id": stable_id("claim-rejection", document_id, "no-supported-claim"),
                "document_id": document_id,
                "reason": "no_supported_atomic_claim_detected",
                "authority": public_authority(),
            })
    # Repeated text from one origin remains one evidentiary cluster.
    by_signature: dict[tuple[str, str, str], list[dict[str, Any]]] = {}
    for claim in accepted:
        signature = (str(claim["claim_type"]), str(claim["direction"]), str(claim["independence_cluster"]))
        by_signature.setdefault(signature, []).append(claim)
    for group in by_signature.values():
        ordered = sorted(group, key=lambda row: (str(row.get("availability_time") or ""), str(row["claim_id"])))
        for index, claim in enumerate(ordered):
            claim["novelty_state"] = "first_in_cluster" if index == 0 else "same_origin_repeat"
            if index:
                claim["corroboration_claim_ids"] = [str(ordered[index - 1]["claim_id"])]
    store = AtomicArtifactStore(runtime)
    store.write_jsonl(QUALITATIVE_CLAIMS_ARTIFACT, accepted)
    store.write_jsonl(QUALITATIVE_REJECTIONS_ARTIFACT, rejected)
    summary = {
        "schema_version": "qadam_qualitative_claim_summary.v1",
        "artifact_type": "qadam_qualitative_claim_summary",
        "generated_at": now_iso(),
        "status": "passed" if not errors else "blocked",
        "document_count": len(documents),
        "accepted_claim_count": len(accepted),
        "rejected_document_count": len(rejected),
        "claim_type_counts": dict(sorted(Counter(str(row["claim_type"]) for row in accepted).items())),
        "independence_cluster_count": len({str(row.get("independence_cluster")) for row in accepted}),
        "local_model_mode": "deterministic_schema_fallback",
        "grounded_span_coverage": 1.0 if accepted else 0.0,
        "validation_errors": errors,
        "authority": public_authority(),
    }
    store.write_json(QUALITATIVE_CLAIM_SUMMARY_ARTIFACT, summary)
    return {"claims": accepted, "rejections": rejected, "summary": summary}, errors


__all__ = ["extract_qualitative_claims"]
