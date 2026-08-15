"""Public-safe qualitative research and communications projections."""

from __future__ import annotations

from typing import Any

from orchestrator.config import Settings
from orchestrator.qadam_canonical_contracts import AtomicArtifactStore
from orchestrator.qadam_operator_ready_common import append_jsonl_durable
from orchestrator.qadam_qualitative_common import (
    EXTERNAL_ACQUISITION_ARTIFACT,
    EXTERNAL_PROVENANCE_ARTIFACT,
    LANE_FUNNEL_ARTIFACT,
    PREDICTION_RESEARCH_ARTIFACT,
    QUALITATIVE_BACKTEST_ARTIFACT,
    QUALITATIVE_CLAIM_SUMMARY_ARTIFACT,
    QUALITATIVE_COMMUNICATIONS_ARTIFACT,
    QUALITATIVE_DASHBOARD_ARTIFACT,
    QUALITATIVE_FORWARD_WINDOWS_ARTIFACT,
    QUALITATIVE_GRAPH_SUMMARY_ARTIFACT,
    QUALITATIVE_NOTIFICATION_DEDUPE_ARTIFACT,
    QUALITATIVE_PAPER_ELIGIBILITY_ARTIFACT,
    now_iso,
    public_authority,
    read_json,
    read_jsonl,
    runtime_dir,
    sha256_json,
    stable_id,
)


def validate_qualitative_visibility(bundle: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    dashboard = bundle.get("dashboard") or {}
    communications = bundle.get("communications") or {}
    if dashboard.get("status") != "research_operational":
        errors.append("qualitative_dashboard_not_operational")
    if dashboard.get("existing_dashboard_structure_preserved") is not True:
        errors.append("qualitative_dashboard_structure_not_preserved")
    if int(dashboard.get("research_eligible_document_count") or 0) > int(
        dashboard.get("official_document_count") or 0
    ):
        errors.append("qualitative_dashboard_eligible_documents_exceed_documents")
    for field in (
        "official_document_count",
        "research_eligible_document_count",
        "grounded_claim_count",
        "graph_relationship_count",
        "pending_forward_window_count",
        "mature_forward_label_count",
        "qualified_pattern_count",
        "prediction_contract_count",
        "prediction_disagreement_count",
        "liquidity_qualified_prediction_disagreement_count",
        "lane_contribution_count",
        "a4_paper_review_nomination_count",
        "qualitative_paper_review_eligible_count",
    ):
        if int(dashboard.get(field) or 0) < 0:
            errors.append(f"qualitative_dashboard_negative_count:{field}")
    authority = dashboard.get("authority") or {}
    for field in ("command_disabled", "read_only", "paper_only"):
        if authority.get(field) is not True:
            errors.append(f"qualitative_dashboard_authority_missing:{field}")
    for field in (
        "trade_candidate_creation_allowed",
        "risk_approval_allowed",
        "execution_approval_allowed",
        "paper_order_allowed",
        "broker_write_allowed",
        "live_capital_enabled",
        "proof_credit_allowed",
        "telegram_live_send_allowed",
        "telegram_command_path_enabled",
    ):
        if authority.get(field) is not False:
            errors.append(f"qualitative_dashboard_unsafe_authority:{field}")
    if communications.get("status") not in {
        "material_update_candidate",
        "quiet_no_material_change",
    }:
        errors.append("qualitative_communications_status_invalid")
    material_change = communications.get("material_change") is True
    message = communications.get("message_candidate")
    if material_change and not str(message or "").strip():
        errors.append("qualitative_material_change_message_missing")
    if not material_change and message is not None:
        errors.append("qualitative_unchanged_cycle_message_present")
    if message is not None and len(str(message)) > 500:
        errors.append("qualitative_message_too_long")
    if communications.get("live_send_allowed") is not False:
        errors.append("qualitative_communications_live_send_enabled")
    if communications.get("live_send_attempted") is not False:
        errors.append("qualitative_communications_send_attempted")
    if communications.get("command_path_enabled") is not False:
        errors.append("qualitative_communications_command_path_enabled")
    return sorted(set(errors))


def build_qualitative_visibility(
    settings: Settings | None = None,
) -> tuple[dict[str, Any], list[str]]:
    runtime = runtime_dir(settings)
    acquisition = read_json(runtime / EXTERNAL_ACQUISITION_ARTIFACT)
    provenance = read_json(runtime / EXTERNAL_PROVENANCE_ARTIFACT)
    claims = read_json(runtime / QUALITATIVE_CLAIM_SUMMARY_ARTIFACT)
    graph = read_json(runtime / QUALITATIVE_GRAPH_SUMMARY_ARTIFACT)
    windows = read_json(runtime / QUALITATIVE_FORWARD_WINDOWS_ARTIFACT)
    backtest = read_json(runtime / QUALITATIVE_BACKTEST_ARTIFACT)
    prediction = read_json(runtime / PREDICTION_RESEARCH_ARTIFACT)
    funnel = read_json(runtime / LANE_FUNNEL_ARTIFACT)
    eligibility = read_json(runtime / QUALITATIVE_PAPER_ELIGIBILITY_ARTIFACT)
    router = read_jsonl(runtime / "qadam_router_v3_decisions.jsonl")

    current_router_state = str(router[0].get("final_state") or "no_current_setup") if router else "no_current_setup"
    pending_count = int(windows.get("pending_window_count") or 0)
    candidate_count = int(backtest.get("candidate_count") or 0)
    liquidity_qualified = int(prediction.get("liquidity_qualified_disagreement_count") or 0)
    graph_relationship_count = sum(
        int((graph.get("record_type_counts") or {}).get(record_type) or 0)
        for record_type in (
            "affects",
            "derived_from",
            "maps_to_strategy",
            "mentions",
            "published_by",
        )
    )
    next_action = (
        "Observe real market time until the current qualitative forward windows mature."
        if pending_count
        else "Acquire new independent qualitative events and rerun the frozen tests."
    )
    dashboard = {
        "schema_version": "qadam_qualitative_dashboard_summary.v1",
        "artifact_type": "qadam_qualitative_dashboard_summary",
        "generated_at": now_iso(),
        "status": "research_operational",
        "headline": "Qualitative evidence is being converted into testable market relationships.",
        "official_document_count": int(acquisition.get("document_count") or 0),
        "research_eligible_document_count": int(
            provenance.get("research_eligible_count") or 0
        ),
        "grounded_claim_count": int(claims.get("accepted_claim_count") or 0),
        "graph_relationship_count": graph_relationship_count,
        "pending_forward_window_count": pending_count,
        "mature_forward_label_count": int(backtest.get("label_count") or 0),
        "qualified_pattern_count": candidate_count,
        "prediction_contract_count": int(prediction.get("contract_count") or 0),
        "prediction_disagreement_count": int(
            prediction.get("disagreement_record_count") or 0
        ),
        "liquidity_qualified_prediction_disagreement_count": liquidity_qualified,
        "lane_contribution_count": int(funnel.get("contribution_count") or 0),
        "a4_paper_review_nomination_count": int(funnel.get("a4_nomination_count") or 0),
        "current_router_disposition": current_router_state,
        "qualitative_paper_review_eligible_count": int(eligibility.get("paper_review_eligible_count") or 0),
        "what_changed": (
            f"Qadam has {int(claims.get('accepted_claim_count') or 0)} grounded qualitative claims "
            f"and {int(prediction.get('disagreement_count') or 0)} prediction-market disagreements under review."
        ),
        "why_not_tradeable_yet": (
            "Qualitative claims are waiting for real forward outcomes, while prediction-market comparisons lack matched decision-time liquidity."
            if not candidate_count and not liquidity_qualified
            else "Every nominated setup still needs its current Akber, shadow, risk and Router disposition."
        ),
        "next_action": next_action,
        "existing_dashboard_structure_preserved": True,
        "authority": public_authority(),
    }
    fingerprint = sha256_json(
        {
            key: dashboard[key]
            for key in (
                "grounded_claim_count",
                "pending_forward_window_count",
                "mature_forward_label_count",
                "qualified_pattern_count",
                "prediction_disagreement_count",
                "liquidity_qualified_prediction_disagreement_count",
                "a4_paper_review_nomination_count",
                "current_router_disposition",
            )
        }
    )
    history = read_jsonl(runtime / QUALITATIVE_NOTIFICATION_DEDUPE_ARTIFACT)
    material_change = not history or history[-1].get("fingerprint") != fingerprint
    message = (
        "Qadam research update. "
        f"{dashboard['grounded_claim_count']} grounded official claims; "
        f"{dashboard['mature_forward_label_count']} mature forward labels; "
        f"{dashboard['qualified_pattern_count']} qualified qualitative patterns. "
        f"Prediction markets: {dashboard['prediction_disagreement_count']} disagreements, "
        f"{dashboard['liquidity_qualified_prediction_disagreement_count']} with matched liquidity. "
        f"Current governed disposition: {current_router_state}. "
        f"Next: {next_action}"
    )
    communications = {
        "schema_version": "qadam_qualitative_communications_summary.v1",
        "artifact_type": "qadam_qualitative_communications_summary",
        "generated_at": dashboard["generated_at"],
        "status": "material_update_candidate" if material_change else "quiet_no_material_change",
        "material_change": material_change,
        "message_candidate": message if material_change else None,
        "fingerprint": fingerprint,
        "live_send_allowed": False,
        "live_send_attempted": False,
        "command_path_enabled": False,
        "authority": public_authority(),
    }
    store = AtomicArtifactStore(runtime)
    store.write_json(QUALITATIVE_DASHBOARD_ARTIFACT, dashboard)
    store.write_json(QUALITATIVE_COMMUNICATIONS_ARTIFACT, communications)
    if material_change:
        append_jsonl_durable(
            runtime / QUALITATIVE_NOTIFICATION_DEDUPE_ARTIFACT,
            {
                "notification_id": stable_id("qualitative-notification", fingerprint),
                "generated_at": dashboard["generated_at"],
                "fingerprint": fingerprint,
                "delivery_state": "candidate_only_not_sent",
                "authority": public_authority(),
            },
        )
    bundle = {"dashboard": dashboard, "communications": communications}
    return bundle, validate_qualitative_visibility(bundle)


__all__ = ["build_qualitative_visibility", "validate_qualitative_visibility"]
