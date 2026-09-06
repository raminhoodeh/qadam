#!/usr/bin/env python3
"""Validate and write QSASE-13 dashboard view-model artifacts."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from orchestrator.config import Settings  # noqa: E402
from orchestrator.qsase_dashboard_view_model import (  # noqa: E402
    AKBER_FILTER_V2_DASHBOARD_ARTIFACT,
    ANTI_SLOP_ARTIFACT,
    CURRENT_PORTFOLIO_ARTIFACT,
    DASHBOARD_VNEXT_DASHBOARD_ARTIFACT,
    DECISION_RECORDS_ARTIFACT,
    EVIDENCE_QUALITY_ARTIFACT,
    EVENTS_ARTIFACT,
    HISTORY_ARTIFACT,
    LEARNING_ATTRIBUTION_V2_DASHBOARD_ARTIFACT,
    LEARNING_LEDGER_ARTIFACT,
    NEXT_GENERATION_BACKTEST_DASHBOARD_ARTIFACT,
    PAPER_LIFECYCLE_V2_DASHBOARD_ARTIFACT,
    PATTERN_ENGINE_V2_DASHBOARD_ARTIFACT,
    PATTERN_TO_PAPER_WORKFLOW_ARTIFACT,
    PATTERN_INTELLIGENCE_ARTIFACT,
    PATTERN_LAB_ARTIFACT,
    PORTFOLIO_SERIES_ARTIFACT,
    REPAIR_QUEUE_ARTIFACT,
    ROUTER_V2_DASHBOARD_ARTIFACT,
    SOURCE_NETWORK_ARTIFACT,
    STATUS_ARTIFACT,
    SHADOW_SIMULATOR_V2_DASHBOARD_ARTIFACT,
    STRATEGY_EVIDENCE_MAP_DASHBOARD_ARTIFACT,
    STRATEGY_FOUNDRY_V2_DASHBOARD_ARTIFACT,
    STRATEGY_UNIVERSE_ARTIFACT,
    SYSTEM_MAP_ARTIFACT,
    TELEGRAM_VNEXT_COMMUNICATIONS_MIRROR_ARTIFACT,
    TELEGRAM_VNEXT_DASHBOARD_ARTIFACT,
    TRADE_INTENTS_ARTIFACT,
    TRADING_HISTORY_ARTIFACT,
    _runtime_dir,
    build_and_write_dashboard_view_model,
    load_dashboard_view_model,
    validate_dashboard_view_model,
    validate_negative_dashboard_view_model_probes,
)


def _load_json(path: Path) -> dict:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> int:
    settings = Settings.from_env()
    payload, written, errors = build_and_write_dashboard_view_model(settings)
    runtime_dir = _runtime_dir(settings)

    validation_errors = list(errors)
    for filename in (
        STATUS_ARTIFACT,
        DECISION_RECORDS_ARTIFACT,
        SYSTEM_MAP_ARTIFACT,
        PORTFOLIO_SERIES_ARTIFACT,
        CURRENT_PORTFOLIO_ARTIFACT,
        TRADING_HISTORY_ARTIFACT,
        SOURCE_NETWORK_ARTIFACT,
        STRATEGY_UNIVERSE_ARTIFACT,
        PATTERN_LAB_ARTIFACT,
        EVIDENCE_QUALITY_ARTIFACT,
        TRADE_INTENTS_ARTIFACT,
        PATTERN_TO_PAPER_WORKFLOW_ARTIFACT,
        PATTERN_INTELLIGENCE_ARTIFACT,
        LEARNING_LEDGER_ARTIFACT,
        REPAIR_QUEUE_ARTIFACT,
        NEXT_GENERATION_BACKTEST_DASHBOARD_ARTIFACT,
        PATTERN_ENGINE_V2_DASHBOARD_ARTIFACT,
        STRATEGY_EVIDENCE_MAP_DASHBOARD_ARTIFACT,
        STRATEGY_FOUNDRY_V2_DASHBOARD_ARTIFACT,
        AKBER_FILTER_V2_DASHBOARD_ARTIFACT,
        SHADOW_SIMULATOR_V2_DASHBOARD_ARTIFACT,
        ROUTER_V2_DASHBOARD_ARTIFACT,
        PAPER_LIFECYCLE_V2_DASHBOARD_ARTIFACT,
        LEARNING_ATTRIBUTION_V2_DASHBOARD_ARTIFACT,
        DASHBOARD_VNEXT_DASHBOARD_ARTIFACT,
        TELEGRAM_VNEXT_DASHBOARD_ARTIFACT,
        TELEGRAM_VNEXT_COMMUNICATIONS_MIRROR_ARTIFACT,
        ANTI_SLOP_ARTIFACT,
        HISTORY_ARTIFACT,
        EVENTS_ARTIFACT,
    ):
        if not (runtime_dir / filename).exists():
            validation_errors.append(f"{filename}_missing")

    loaded = load_dashboard_view_model(settings)
    attempt = _load_json(runtime_dir / "qadam_dashboard_projection_attempt.json")
    if attempt.get("status") != "passed" or attempt.get("generated_at") != payload.get("generated_at"):
        validation_errors.append("projection_validation_attempt_failed")
    validation_errors.extend(validate_dashboard_view_model(loaded))
    validation_errors.extend(validate_negative_dashboard_view_model_probes())

    print(f"status_artifact={written.get('status')}")
    print(f"decision_records={written.get('decision_records')}")
    print(f"system_map={written.get('system_map')}")
    print(f"portfolio_value={written.get('portfolio_value')}")
    print(f"current_portfolio={written.get('current_portfolio')}")
    print(f"trading_history={written.get('trading_history')}")
    print(f"source_network={written.get('source_network')}")
    print(f"strategy_universe={written.get('strategy_universe')}")
    print(f"pattern_lab={written.get('pattern_lab')}")
    print(f"evidence_quality={written.get('evidence_quality')}")
    print(f"trade_intents={written.get('trade_intents')}")
    print(f"pattern_to_paper_workflow={written.get('pattern_to_paper_workflow')}")
    print(f"pattern_intelligence={written.get('pattern_intelligence')}")
    print(f"learning_ledger={written.get('learning_ledger')}")
    print(f"repair_queue={written.get('repair_queue')}")
    print(f"next_generation_backtest={written.get('next_generation_backtest')}")
    print(f"anti_slop={written.get('anti_slop')}")
    print(f"phase_status={written.get('phase_status')}")
    print(f"implementation_log={written.get('implementation_log')}")
    print(f"status={payload.get('status')}")
    print(f"portfolio_value_series_count={payload.get('portfolio_value_series_count')}")
    print(f"current_position_count={payload.get('current_position_count')}")
    print(f"trading_history_row_count={payload.get('trading_history_row_count')}")
    print(f"source_category_row_count={payload.get('source_category_row_count')}")
    print(f"source_row_count={payload.get('source_row_count')}")
    print(f"trading_universe_row_count={payload.get('trading_universe_row_count')}")
    print(f"all_strategy_count={payload.get('all_strategy_count')}")
    print(f"currently_in_play_count={payload.get('currently_in_play_count')}")
    print(f"linear_pattern_count={payload.get('linear_pattern_count')}")
    print(f"nonlinear_pattern_count={payload.get('nonlinear_pattern_count')}")
    print(f"evidence_quality_record_count={payload.get('evidence_quality_record_count')}")
    print(f"evidence_quality_paper_review_candidate_count={payload.get('evidence_quality_paper_review_candidate_count')}")
    print(f"evidence_quality_held_for_evidence_count={payload.get('evidence_quality_held_for_evidence_count')}")
    print(f"trade_intent_count={payload.get('trade_intent_count')}")
    print(f"pattern_workflow_record_count={payload.get('pattern_workflow_record_count')}")
    print(f"pattern_workflow_handoff_candidate_count={payload.get('pattern_workflow_handoff_candidate_count')}")
    print(f"pattern_workflow_telegram_candidate_count={payload.get('pattern_workflow_telegram_candidate_count')}")
    print(f"pattern_intelligence_finding_count={payload.get('pattern_intelligence_finding_count')}")
    print(f"pattern_intelligence_paper_ready_count={payload.get('pattern_intelligence_paper_ready_count')}")
    print(f"learning_ledger_row_count={payload.get('learning_ledger_row_count')}")
    print(f"repair_queue_count={payload.get('repair_queue_count')}")
    print(f"next_generation_backtest_state={payload.get('next_generation_backtest_state')}")
    print(f"evidence_contracts_state={payload.get('evidence_contracts_state')}")
    print(f"evidence_contract_count={payload.get('evidence_contract_count')}")
    print(f"missing_typed_evidence_count={payload.get('missing_typed_evidence_count')}")
    print(f"contracts_with_missing_evidence_count={payload.get('contracts_with_missing_evidence_count')}")
    print(f"evidence_contract_downstream_reader_state={payload.get('evidence_contract_downstream_reader_state')}")
    print(f"world_model_state={payload.get('world_model_state')}")
    print(f"world_model_hypothesis_count={payload.get('world_model_hypothesis_count')}")
    print(f"world_model_research_question_count={payload.get('world_model_research_question_count')}")
    print(f"world_model_mapped_market_count={payload.get('world_model_mapped_market_count')}")
    print(f"world_model_trade_candidate_creation_allowed={payload.get('world_model_trade_candidate_creation_allowed')}")
    print(f"pattern_engine_v2_state={payload.get('pattern_engine_v2_state')}")
    print(f"pattern_engine_v2_pattern_count={payload.get('pattern_engine_v2_pattern_count')}")
    print(f"pattern_engine_v2_ranked_pattern_count={payload.get('pattern_engine_v2_ranked_pattern_count')}")
    print(f"pattern_engine_v2_held_for_more_evidence_count={payload.get('pattern_engine_v2_held_for_more_evidence_count')}")
    print(f"pattern_engine_v2_rejected_pattern_count={payload.get('pattern_engine_v2_rejected_pattern_count')}")
    print(f"pattern_engine_v2_research_only={payload.get('pattern_engine_v2_research_only')}")
    print(f"pattern_engine_v2_trade_candidate_creation_allowed={payload.get('pattern_engine_v2_trade_candidate_creation_allowed')}")
    print(f"strategy_evidence_map_state={payload.get('strategy_evidence_map_state')}")
    print(f"strategy_evidence_map_strategy_count={payload.get('strategy_evidence_map_strategy_count')}")
    print(f"strategy_evidence_map_evidence_backed_strategy_count={payload.get('strategy_evidence_map_evidence_backed_strategy_count')}")
    print(f"strategy_evidence_map_under_evidenced_strategy_count={payload.get('strategy_evidence_map_under_evidenced_strategy_count')}")
    print(f"strategy_evidence_map_research_only={payload.get('strategy_evidence_map_research_only')}")
    print(f"strategy_evidence_map_strategy_hypothesis_creation_allowed={payload.get('strategy_evidence_map_strategy_hypothesis_creation_allowed')}")
    print(f"strategy_evidence_map_trade_candidate_creation_allowed={payload.get('strategy_evidence_map_trade_candidate_creation_allowed')}")
    print(f"strategy_foundry_v2_state={payload.get('strategy_foundry_v2_state')}")
    print(f"strategy_foundry_v2_hypothesis_count={payload.get('strategy_foundry_v2_hypothesis_count')}")
    print(f"strategy_foundry_v2_accepted_for_akber_input_builder_count={payload.get('strategy_foundry_v2_accepted_for_akber_input_builder_count')}")
    print(f"strategy_foundry_v2_rejected_before_akber_count={payload.get('strategy_foundry_v2_rejected_before_akber_count')}")
    print(f"strategy_foundry_v2_weak_pattern_rejection_count={payload.get('strategy_foundry_v2_weak_pattern_rejection_count')}")
    print(f"strategy_foundry_v2_research_only={payload.get('strategy_foundry_v2_research_only')}")
    print(f"strategy_foundry_v2_akber_filter_run={payload.get('strategy_foundry_v2_akber_filter_run')}")
    print(f"strategy_foundry_v2_trade_candidate_creation_allowed={payload.get('strategy_foundry_v2_trade_candidate_creation_allowed')}")
    print(f"akber_filter_v2_state={payload.get('akber_filter_v2_state')}")
    print(f"akber_filter_v2_input_count={payload.get('akber_filter_v2_input_count')}")
    print(f"akber_filter_v2_result_count={payload.get('akber_filter_v2_result_count')}")
    print(f"akber_filter_v2_pass_count={payload.get('akber_filter_v2_pass_count')}")
    print(f"akber_filter_v2_hold_count={payload.get('akber_filter_v2_hold_count')}")
    print(f"akber_filter_v2_veto_count={payload.get('akber_filter_v2_veto_count')}")
    print(f"akber_filter_v2_router_eligible_count={payload.get('akber_filter_v2_router_eligible_count')}")
    print(f"akber_filter_v2_router_eligible_with_missing_context_count={payload.get('akber_filter_v2_router_eligible_with_missing_context_count')}")
    print(f"akber_filter_v2_no_router_eligible_setup_has_missing_context={payload.get('akber_filter_v2_no_router_eligible_setup_has_missing_context')}")
    print(f"akber_filter_v2_pass_is_execution_approval={payload.get('akber_filter_v2_pass_is_execution_approval')}")
    print(f"akber_filter_v2_execution_approval_created={payload.get('akber_filter_v2_execution_approval_created')}")
    print(f"shadow_simulator_v2_state={payload.get('shadow_simulator_v2_state')}")
    print(f"shadow_simulator_v2_hypothesis_count={payload.get('shadow_simulator_v2_hypothesis_count')}")
    print(
        "shadow_simulator_v2_hypothesis_with_shadow_evidence_count="
        f"{payload.get('shadow_simulator_v2_hypothesis_with_shadow_evidence_count')}"
    )
    print(f"shadow_simulator_v2_missing_shadow_evidence_count={payload.get('shadow_simulator_v2_missing_shadow_evidence_count')}")
    print(f"shadow_simulator_v2_historical_shadow_replay_count={payload.get('shadow_simulator_v2_historical_shadow_replay_count')}")
    print(f"shadow_simulator_v2_forward_tracking_count={payload.get('shadow_simulator_v2_forward_tracking_count')}")
    print(f"shadow_simulator_v2_counterfactual_no_order_count={payload.get('shadow_simulator_v2_counterfactual_no_order_count')}")
    print(f"shadow_simulator_v2_alternate_threshold_outcome_count={payload.get('shadow_simulator_v2_alternate_threshold_outcome_count')}")
    print(f"shadow_simulator_v2_missed_opportunity_count={payload.get('shadow_simulator_v2_missed_opportunity_count')}")
    print(
        "shadow_simulator_v2_every_hypothesis_has_shadow_evidence="
        f"{payload.get('shadow_simulator_v2_every_hypothesis_has_shadow_evidence')}"
    )
    print(
        "shadow_simulator_v2_router_confidence_increase_without_shadow_evidence_count="
        f"{payload.get('shadow_simulator_v2_router_confidence_increase_without_shadow_evidence_count')}"
    )
    print(f"shadow_simulator_v2_router_confidence_increase_created={payload.get('shadow_simulator_v2_router_confidence_increase_created')}")
    print(
        "shadow_simulator_v2_shadow_success_cannot_create_paper_order="
        f"{payload.get('shadow_simulator_v2_shadow_success_cannot_create_paper_order')}"
    )
    print(
        "shadow_simulator_v2_shadow_success_cannot_create_proof_credit="
        f"{payload.get('shadow_simulator_v2_shadow_success_cannot_create_proof_credit')}"
    )
    print(f"router_v2_state={payload.get('router_v2_state')}")
    print(f"router_v2_setup_count={payload.get('router_v2_setup_count')}")
    print(f"router_v2_decision_count={payload.get('router_v2_decision_count')}")
    print(f"router_v2_all_setups_have_exactly_one_final_state={payload.get('router_v2_all_setups_have_exactly_one_final_state')}")
    print(f"router_v2_paper_review_candidate_count={payload.get('router_v2_paper_review_candidate_count')}")
    print(f"router_v2_clean_paper_review_candidate_count={payload.get('router_v2_clean_paper_review_candidate_count')}")
    print(f"router_v2_handoff_record_count={payload.get('router_v2_handoff_record_count')}")
    print(f"router_v2_rejected_handoff_count={payload.get('router_v2_rejected_handoff_count')}")
    print(
        "router_v2_only_clean_paper_review_candidates_reach_paperops="
        f"{payload.get('router_v2_only_clean_paper_review_candidates_reach_paperops')}"
    )
    print(f"router_v2_duplicate_idempotency_count={payload.get('router_v2_duplicate_idempotency_count')}")
    print(f"router_v2_duplicate_exposure_count={payload.get('router_v2_duplicate_exposure_count')}")
    print(f"router_v2_why_not_trading_now_reason={payload.get('router_v2_why_not_trading_now_reason')}")
    print(f"router_v2_why_not_trading_now_plain_english={payload.get('router_v2_why_not_trading_now_plain_english')}")
    print(f"router_v2_paper_order_created_count={payload.get('router_v2_paper_order_created_count')}")
    print(f"router_v2_broker_write_count={payload.get('router_v2_broker_write_count')}")
    print(f"router_v2_proof_credit_allowed={payload.get('router_v2_proof_credit_allowed')}")
    print(f"paper_lifecycle_v2_state={payload.get('paper_lifecycle_v2_state')}")
    print(f"paper_lifecycle_v2_order_count={payload.get('paper_lifecycle_v2_order_count')}")
    print(f"paper_lifecycle_v2_open_position_count={payload.get('paper_lifecycle_v2_open_position_count')}")
    print(f"paper_lifecycle_v2_closed_trade_count={payload.get('paper_lifecycle_v2_closed_trade_count')}")
    print(f"paper_lifecycle_v2_lifecycle_record_count={payload.get('paper_lifecycle_v2_lifecycle_record_count')}")
    print(f"paper_lifecycle_v2_ambiguous_lifecycle_count={payload.get('paper_lifecycle_v2_ambiguous_lifecycle_count')}")
    print(f"paper_lifecycle_v2_no_paper_order_ambiguous={payload.get('paper_lifecycle_v2_no_paper_order_ambiguous')}")
    print(f"paper_lifecycle_v2_stale_accepted_order_count={payload.get('paper_lifecycle_v2_stale_accepted_order_count')}")
    print(f"paper_lifecycle_v2_cancel_replace_needed_count={payload.get('paper_lifecycle_v2_cancel_replace_needed_count')}")
    print(f"paper_lifecycle_v2_state_counts={payload.get('paper_lifecycle_v2_state_counts')}")
    print(f"paper_lifecycle_v2_proof_boundary_state={payload.get('paper_lifecycle_v2_proof_boundary_state')}")
    print(f"paper_lifecycle_v2_proof_eligible_count={payload.get('paper_lifecycle_v2_proof_eligible_count')}")
    print(f"paper_lifecycle_v2_proof_rejected_count={payload.get('paper_lifecycle_v2_proof_rejected_count')}")
    print(
        "paper_lifecycle_v2_proof_credit_requires_real_closed_trade_with_complete_lineage="
        f"{payload.get('paper_lifecycle_v2_proof_credit_requires_real_closed_trade_with_complete_lineage')}"
    )
    print(
        "paper_lifecycle_v2_backtest_shadow_or_synthetic_proof_credit_count="
        f"{payload.get('paper_lifecycle_v2_backtest_shadow_or_synthetic_proof_credit_count')}"
    )
    print(f"paper_lifecycle_v2_paper_proof_ledger_credit_allowed={payload.get('paper_lifecycle_v2_paper_proof_ledger_credit_allowed')}")
    print(f"paper_lifecycle_v2_proof_credit_allowed={payload.get('paper_lifecycle_v2_proof_credit_allowed')}")
    print(f"learning_attribution_v2_state={payload.get('learning_attribution_v2_state')}")
    print(f"learning_attribution_v2_record_count={payload.get('learning_attribution_v2_record_count')}")
    print(f"learning_attribution_v2_backtest_record_count={payload.get('learning_attribution_v2_backtest_record_count')}")
    print(f"learning_attribution_v2_shadow_record_count={payload.get('learning_attribution_v2_shadow_record_count')}")
    print(f"learning_attribution_v2_akber_record_count={payload.get('learning_attribution_v2_akber_record_count')}")
    print(f"learning_attribution_v2_router_record_count={payload.get('learning_attribution_v2_router_record_count')}")
    print(f"learning_attribution_v2_paperops_record_count={payload.get('learning_attribution_v2_paperops_record_count')}")
    print(
        "learning_attribution_v2_missed_opportunity_record_count="
        f"{payload.get('learning_attribution_v2_missed_opportunity_record_count')}"
    )
    print(
        "learning_attribution_v2_paper_trade_outcome_record_count="
        f"{payload.get('learning_attribution_v2_paper_trade_outcome_record_count')}"
    )
    print(f"learning_attribution_v2_proof_rejected_record_count={payload.get('learning_attribution_v2_proof_rejected_record_count')}")
    print(f"learning_attribution_v2_hold_record_count={payload.get('learning_attribution_v2_hold_record_count')}")
    print(f"learning_attribution_v2_veto_record_count={payload.get('learning_attribution_v2_veto_record_count')}")
    print(f"learning_attribution_v2_proposal_count={payload.get('learning_attribution_v2_proposal_count')}")
    print(f"learning_attribution_v2_proposal_applied_count={payload.get('learning_attribution_v2_proposal_applied_count')}")
    print(f"learning_attribution_v2_authority_mutation_count={payload.get('learning_attribution_v2_authority_mutation_count')}")
    print(f"learning_attribution_v2_applied_update_count={payload.get('learning_attribution_v2_applied_update_count')}")
    print(
        "learning_attribution_v2_learning_outputs_are_proposals_only="
        f"{payload.get('learning_attribution_v2_learning_outputs_are_proposals_only')}"
    )
    print(f"dashboard_vnext_state={payload.get('dashboard_vnext_state')}")
    print(f"dashboard_vnext_protected_section_count={payload.get('dashboard_vnext_protected_section_count')}")
    print(f"dashboard_vnext_protected_sections_not_reordered={payload.get('dashboard_vnext_protected_sections_not_reordered')}")
    print(f"dashboard_vnext_protected_sections_not_renamed={payload.get('dashboard_vnext_protected_sections_not_renamed')}")
    print(f"dashboard_vnext_protected_sections_not_removed={payload.get('dashboard_vnext_protected_sections_not_removed')}")
    print(
        "dashboard_vnext_protected_sections_not_structurally_overhauled="
        f"{payload.get('dashboard_vnext_protected_sections_not_structurally_overhauled')}"
    )
    print(
        "dashboard_vnext_enrichment_only_inside_protected_sections="
        f"{payload.get('dashboard_vnext_enrichment_only_inside_protected_sections')}"
    )
    print(f"dashboard_vnext_all_portfolio_values_agree={payload.get('dashboard_vnext_all_portfolio_values_agree')}")
    print(f"dashboard_vnext_downstream_section_count={payload.get('dashboard_vnext_downstream_section_count')}")
    print(f"dashboard_vnext_strategy_card_count={payload.get('dashboard_vnext_strategy_card_count')}")
    print(f"dashboard_vnext_pattern_card_count={payload.get('dashboard_vnext_pattern_card_count')}")
    print(f"dashboard_vnext_router_paperops_single_answer={payload.get('dashboard_vnext_router_paperops_single_answer')}")
    print(f"telegram_vnext_state={payload.get('telegram_vnext_state')}")
    print(f"telegram_vnext_message_candidate_count={payload.get('telegram_vnext_message_candidate_count')}")
    print(f"telegram_vnext_message_ready_count={payload.get('telegram_vnext_message_ready_count')}")
    print(f"telegram_vnext_message_rejected_duplicate_count={payload.get('telegram_vnext_message_rejected_duplicate_count')}")
    print(f"telegram_vnext_message_rejected_quality_count={payload.get('telegram_vnext_message_rejected_quality_count')}")
    print(f"telegram_vnext_message_rejected_unsafe_count={payload.get('telegram_vnext_message_rejected_unsafe_count')}")
    print(f"telegram_vnext_quality_pass_count={payload.get('telegram_vnext_quality_pass_count')}")
    print(f"telegram_vnext_live_send_allowed={payload.get('telegram_vnext_live_send_allowed')}")
    print(f"telegram_vnext_command_path_enabled={payload.get('telegram_vnext_command_path_enabled')}")
    print(f"telegram_vnext_trade_candidate_created={payload.get('telegram_vnext_trade_candidate_created')}")
    print(f"telegram_vnext_risk_approval_created={payload.get('telegram_vnext_risk_approval_created')}")
    print(f"telegram_vnext_execution_approval_created={payload.get('telegram_vnext_execution_approval_created')}")
    print(f"telegram_vnext_paper_order_created_count={payload.get('telegram_vnext_paper_order_created_count')}")
    print(f"telegram_vnext_broker_write_count={payload.get('telegram_vnext_broker_write_count')}")
    print(f"telegram_vnext_proof_credit_allowed={payload.get('telegram_vnext_proof_credit_allowed')}")
    print(f"telegram_vnext_live_capital_enabled={payload.get('telegram_vnext_live_capital_enabled')}")
    print(f"long_backtest_lock_active={payload.get('long_backtest_lock_active')}")
    print(f"paperops_watch_only_mode={payload.get('paperops_watch_only_mode')}")
    print(f"phase_1_backfill_started={payload.get('phase_1_backfill_started')}")
    print(f"stale_labeled_count={payload.get('stale_labeled_count')}")
    print(f"anti_slop_error_count={payload.get('anti_slop_audit', {}).get('error_count')}")
    print(f"applied_change_count={payload.get('applied_change_count')}")
    print(f"paper_order_created_count={payload.get('paper_order_created_count')}")
    print(f"broker_write_count={payload.get('broker_write_count')}")
    print(f"proof_credit_allowed={payload.get('proof_credit_allowed')}")
    print(f"live_capital_enabled={payload.get('live_capital_enabled')}")
    if validation_errors:
        from orchestrator.runtime.command import report_work_result
        report_work_result({"status": "failed", "reason": "dashboard_validation_failed"}, validation_errors)
        for error in validation_errors:
            print(f"error={error}")
        return 1
    from orchestrator.runtime.command import report_work_result
    publication = _load_json(runtime_dir / "qadam_dashboard_projection_check.json")
    report_work_result({"status": "passed", "reason": "coherent_projection_verified",
                        "material_change_detected": bool(publication.get("changed_document_count"))})
    print("qsase_dashboard_view_model_check=ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
