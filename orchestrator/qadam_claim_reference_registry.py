"""QEG-3 classified intake for Qadam research references and claims."""

from __future__ import annotations

from collections import Counter
import hashlib
import re
import shutil
from typing import Any
from urllib.parse import urlparse

from orchestrator.config import Settings
from orchestrator.qadam_operator_ready_common import now_iso, runtime_dir, write_json_atomic
from orchestrator.qadam_qeg_common import (
    ATTACHMENT_PATH,
    ATTACHMENT_SHA256,
    CLAIM_SUMMARY_ARTIFACT,
    REFERENCE_SUMMARY_ARTIFACT,
    qeg_authority,
    research_root,
    stable_id,
    write_phase_status,
)
from orchestrator.qadam_temporal_graph_contracts import build_edge, build_node
from orchestrator.qadam_temporal_graph_store import TemporalGraphStore

URL_RE = re.compile(r"https?://[^\s)>\]}]+")

PRIMARY_DOMAINS = {
    "arxiv.org", "doi.org", "github.com", "ibm.com", "q-ctrl.com", "qiskit.org",
    "sec.gov", "congress.gov", "federalreserve.gov", "fred.stlouisfed.org",
    "kalshi.com", "polymarket.com", "docs.alpaca.markets", "alpaca.markets",
}
SOCIAL_DOMAINS = {
    "x.com", "twitter.com", "instagram.com", "tiktok.com", "youtube.com",
    "youtu.be", "reddit.com", "linkedin.com", "threads.net",
}


def _source_class(url: str) -> str:
    host = urlparse(url).netloc.lower().removeprefix("www.")
    if host in SOCIAL_DOMAINS or any(host.endswith("." + domain) for domain in SOCIAL_DOMAINS):
        return "social_or_anecdotal"
    if host in PRIMARY_DOMAINS or any(host.endswith("." + domain) for domain in PRIMARY_DOMAINS):
        return "primary"
    if any(token in host for token in ("docs", "developer", "research", "papers")):
        return "technical_secondary"
    return "vendor_or_marketing"


def _claim_state(text: str) -> str:
    lower = text.lower()
    if any(token in lower for token in ("500+ live", "300 market", "five-agent", "version 1")):
        return "superseded"
    if any(token in lower for token in ("not a proven", "remains unproven", "research question")):
        return "verified_current"
    return "unreviewed"


def build_claim_registry(settings: Settings | None = None) -> tuple[dict[str, Any], dict[str, Any], list[str]]:
    errors: list[str] = []
    canonical_raw = research_root(settings) / "raw_intake" / f"{ATTACHMENT_SHA256}.md"
    source_path = ATTACHMENT_PATH if ATTACHMENT_PATH.is_file() else canonical_raw
    if not source_path.is_file():
        errors.append("attachment_missing_reattachment_required")
        text = ""
    else:
        digest = hashlib.sha256(source_path.read_bytes()).hexdigest()
        if digest != ATTACHMENT_SHA256:
            errors.append("attachment_checksum_mismatch")
            text = ""
        else:
            text = source_path.read_text(encoding="utf-8")
            canonical_raw.parent.mkdir(parents=True, exist_ok=True)
            if source_path != canonical_raw and not canonical_raw.exists():
                shutil.copy2(source_path, canonical_raw)

    document = build_node(
        "reference_document", f"qadam-blueprint:{ATTACHMENT_SHA256}", layer="observed",
        evidence_state="metadata_only",
        payload={
            "title": "Qadam research blueprint and reference library",
            "sha256": ATTACHMENT_SHA256,
            "namespace": "research_reference",
            "market_evidence_eligible": False,
            "full_text_storage_basis": "operator_supplied_attachment",
        },
        source_artifact=f"data/research/qadam_temporal_evidence_graph/raw_intake/{ATTACHMENT_SHA256}.md",
    )
    urls = sorted(set(URL_RE.findall(text)))
    references: list[dict[str, Any]] = []
    nodes = [document]
    edges: list[dict[str, Any]] = []
    for url in urls:
        cleaned = url.rstrip(".,;:'\"")
        source_class = _source_class(cleaned)
        reference = {
            "reference_id": stable_id("research-reference", cleaned),
            "url": cleaned,
            "host": urlparse(cleaned).netloc.lower(),
            "source_class": source_class,
            "verification_state": "unreviewed",
            "namespace": "research_reference",
            "market_evidence_eligible": False,
            "source_quorum_eligible": False,
            "collection_state": "metadata_only_pending_terms_review",
        }
        references.append(reference)
        node = build_node(
            "reference_document", cleaned, layer="observed", evidence_state="metadata_only",
            payload=reference, source_artifact=document["source_artifact"],
        )
        nodes.append(node)
        edges.append(
            build_edge(
                "mentions", document["node_id"], node["node_id"], layer="observed",
                evidence_state="metadata_only", payload={"relationship": "document_lists_reference"},
                source_artifact=document["source_artifact"],
            )
        )

    paragraphs = [part.strip() for part in re.split(r"\n\s*\n", text) if part.strip()]
    claims: list[dict[str, Any]] = []
    for index, paragraph in enumerate(paragraphs):
        if paragraph.startswith(("|", "```")) or len(paragraph) < 30:
            continue
        claim = {
            "claim_id": stable_id("external-claim", ATTACHMENT_SHA256, index, paragraph),
            "atomic_claim_text": paragraph[:2000],
            "source_reference": document["node_id"],
            "source_class": "operator_supplied_mixed_reference",
            "verification_state": _claim_state(paragraph),
            "namespace": "research_reference",
            "market_evidence_eligible": False,
            "source_quorum_eligible": False,
            "trading_authority": False,
            "falsifier_required_before_testing": True,
        }
        claims.append(claim)
        claim_node = build_node(
            "external_claim", claim["claim_id"], layer="inferred",
            evidence_state="provisional_inference", payload=claim,
            source_artifact=document["source_artifact"],
        )
        nodes.append(claim_node)
        edges.append(
            build_edge(
                "derived_from", claim_node["node_id"], document["node_id"], layer="inferred",
                evidence_state="provisional_inference", payload={"parser": "paragraph_atomic_intake_v1"},
                source_artifact=document["source_artifact"],
            )
        )

    store = TemporalGraphStore(settings)
    append = store.append([*nodes, *edges]) if text else {"written": 0, "duplicates": 0}
    class_counts = Counter(item["source_class"] for item in references)
    state_counts = Counter(item["verification_state"] for item in claims)
    claim_summary = {
        "schema_version": "qadam_claim_reference_registry.v1",
        "artifact_type": "qadam_claim_registry_summary",
        "generated_at": now_iso(),
        "status": "complete" if not errors else "blocked",
        "claim_count": len(claims),
        "claim_state_counts": dict(sorted(state_counts.items())),
        "unreviewed_claim_count": state_counts.get("unreviewed", 0),
        "market_evidence_eligible_count": 0,
        "source_quorum_credit_count": 0,
        "graph_records_written": append["written"],
        "authority": qeg_authority(),
        "blockers": errors,
    }
    reference_summary = {
        "schema_version": "qadam_claim_reference_registry.v1",
        "artifact_type": "qadam_reference_registry_summary",
        "generated_at": now_iso(),
        "status": "complete" if not errors else "blocked",
        "reference_count": len(references),
        "source_class_counts": dict(sorted(class_counts.items())),
        "namespace": "research_reference",
        "full_text_fetch_attempted": False,
        "terms_review_required_before_fetch": True,
        "source_quorum_credit_count": 0,
        "authority": qeg_authority(),
        "blockers": errors,
    }
    runtime = runtime_dir(settings)
    write_json_atomic(runtime / CLAIM_SUMMARY_ARTIFACT, claim_summary)
    write_json_atomic(runtime / REFERENCE_SUMMARY_ARTIFACT, reference_summary)
    write_phase_status(
        "QEG-3", status="passed" if not errors else "blocked",
        implementation_complete=not errors, empirical_state="reference_corpus_classified",
        artifacts=[CLAIM_SUMMARY_ARTIFACT, REFERENCE_SUMMARY_ARTIFACT], blockers=errors,
        settings=settings,
    )
    return claim_summary, reference_summary, errors
