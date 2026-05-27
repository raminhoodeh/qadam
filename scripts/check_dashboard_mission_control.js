#!/usr/bin/env node

const {
    assert,
    assertIncludes,
    renderWithStatus,
    status
} = require("./check_dashboard_renderer.js");

const MISSION_REQUIRED_FIELDS = [
    "data_sources",
    "durable_spine",
    "headline",
    "phase3_readiness",
    "phase4_strategy",
    "phase5_layer_b",
    "phase6_learning_loop",
    "portfolio",
    "safety",
    "schema_version",
    "source",
    "status",
    "system_stack",
    "thinking",
    "trade_intent",
    "trading_philosophy"
];

function hasOwn(value, key) {
    return Object.prototype.hasOwnProperty.call(value, key);
}

function missingFields(value, fields) {
    return fields.filter((field) => !hasOwn(value || {}, field));
}

async function main() {
    const mission = status.mission_control || {};
    const missing = missingFields(mission, MISSION_REQUIRED_FIELDS);
    assert(!missing.length, `mission control missing fields: ${missing.join(", ")}`);
    assert(mission.status === "read_only_mission_control", "mission control status mismatch");
    assert(/sources online/i.test(mission.headline || ""), "mission headline does not summarize source state");
    assert(/live capital disabled/i.test(mission.headline || ""), "mission headline does not show live-capital boundary");
    assert(mission.data_sources.total_count === status.watching.length, "mission source total mismatch");
    assert(Array.isArray(mission.data_sources.logged_in_sources), "mission logged-in sources list missing");
    assert(Array.isArray(mission.data_sources.connected_sources), "mission connected sources list missing");
    assert(mission.data_sources.durable_expected_source_count === status.durable_ingestion.expected_source_count, "mission durable source target mismatch");
    assert(mission.data_sources.durable_replayed_source_count === status.durable_ingestion.replayed_source_count, "mission durable replay count mismatch");
    assert(/observation inputs only/i.test(mission.data_sources.boundary || ""), "mission source boundary is weak");
    const preferenceMcp = status.preference_mcp || {};
    assert(preferenceMcp.public_safe === true, "Preference MCP status is not public-safe");
    assert(preferenceMcp.source_key === "preference_mcp", "Preference MCP source key mismatch");
    assert(preferenceMcp.provider_label === "preference_labs_mcp", "Preference MCP provider label mismatch");
    assert(preferenceMcp.approved_domain_pack_count >= 1, "Preference MCP domain-pack coverage missing");
    assert(preferenceMcp.approved_domain_pack_count === preferenceMcp.approved_domain_packs.length, "Preference MCP domain-pack count mismatch");
    assert(preferenceMcp.source_quorum_credit_allowed === false, "Preference MCP source-quorum credit enabled");
    assert(preferenceMcp.preference_only_confirmation_allowed === false, "Preference MCP only confirmation enabled");
    assert(preferenceMcp.trade_candidate_creation_allowed === false, "Preference MCP trade creation enabled");
    assert(preferenceMcp.execution_allowed === false, "Preference MCP execution enabled");
    assert(preferenceMcp.broker_write_allowed === false, "Preference MCP broker write enabled");
    assert(preferenceMcp.live_capital_enabled === false, "Preference MCP live capital enabled");
    assert(preferenceMcp.raw_key_exposed === false, "Preference MCP raw key exposed");
    assert(preferenceMcp.raw_payload_exposed === false, "Preference MCP raw payload exposed");
    assert(preferenceMcp.private_source_payload_exposed === false, "Preference MCP private source payload exposed");
    assert(/read-only/i.test(preferenceMcp.boundary || ""), "Preference MCP boundary is not read-only");
    assert(/without secrets/i.test(preferenceMcp.boundary || ""), "Preference MCP boundary does not block secrets");
    assert(mission.data_sources.preference_mcp_status === preferenceMcp.status, "mission Preference MCP status mismatch");
    assert(mission.data_sources.preference_mcp_identity_status === preferenceMcp.identity_status, "mission Preference MCP identity mismatch");
    assert(mission.data_sources.preference_mcp_quota_status === preferenceMcp.quota_status, "mission Preference MCP quota mismatch");
    assert(mission.data_sources.preference_mcp_catalog_status === preferenceMcp.catalog_status, "mission Preference MCP catalog mismatch");
    assert(mission.data_sources.preference_mcp_domain_pack_count === preferenceMcp.approved_domain_pack_count, "mission Preference MCP domain-pack count mismatch");
    assert(mission.data_sources.preference_mcp_provenance_status === preferenceMcp.provenance_status, "mission Preference MCP provenance mismatch");
    assert(mission.data_sources.preference_mcp_shadow_context_status === preferenceMcp.shadow_context_status, "mission Preference MCP shadow context mismatch");
    assert(/supplemental data planes are observation inputs only/i.test(mission.data_sources.boundary || ""), "mission Preference MCP boundary is weak");
    assert(mission.durable_spine.expected_source_count === status.durable_ingestion.expected_source_count, "mission durable expected source count mismatch");
    assert(mission.durable_spine.replayed_source_count === status.durable_ingestion.replayed_source_count, "mission durable replayed source count mismatch");
    assert(mission.durable_spine.write_authority === false, "mission durable write authority enabled");
    assert(mission.durable_spine.signal_authority === false, "mission durable signal authority enabled");
    assert(mission.durable_spine.order_authority === false, "mission durable order authority enabled");
    assert(/cannot create signals/i.test(mission.durable_spine.boundary || ""), "mission durable boundary is weak");
    const phase3 = mission.phase3_readiness || {};
    assert(phase3.phase === "Q3", "mission Phase 3 readiness phase mismatch");
    assert(phase3.status === "provider_scheduler_readiness", "mission Phase 3 readiness status mismatch");
    assert(phase3.readiness_scope === "provider_scheduler_readiness", "mission Phase 3 readiness scope mismatch");
    assert(phase3.execution_readiness === "not_execution_ready", "mission Phase 3 readiness implies execution readiness");
    assert(phase3.public_safe === true, "mission Phase 3 readiness is not public-safe");
    assert(phase3.provider_count === status.quantum_oracle.provider_readiness.provider_count, "mission Phase 3 provider count mismatch");
    assert(phase3.configured_provider_count === status.quantum_oracle.provider_readiness.configured_count, "mission Phase 3 configured provider count mismatch");
    assert(phase3.qctrl_configured === true, "mission Phase 3 Q-CTRL should appear configured");
    assert(phase3.qctrl_live_probe_enabled === false, "mission Phase 3 Q-CTRL live probe enabled");
    assert(phase3.qctrl_provider_call_count === 0, "mission Phase 3 Q-CTRL provider call count is nonzero");
    assert(phase3.qctrl_optimization_job_submitted === false, "mission Phase 3 Q-CTRL optimization job submitted");
    assert(typeof phase3.qiskit_available === "boolean", "mission Phase 3 Qiskit availability is not boolean");
    assert(typeof phase3.qiskit_aer_available === "boolean", "mission Phase 3 Qiskit Aer availability is not boolean");
    assert(phase3.local_simulator_backend === status.quantum_oracle.local_simulator.selected_backend, "mission Phase 3 local simulator backend mismatch");
    assert(
        ["missing_secret", "configured", "configured_policy_blocked"].includes(phase3.ibm_quantum_status),
        "mission Phase 3 IBM status mismatch"
    );
    assert(phase3.aws_braket_status === "missing_secret", "mission Phase 3 AWS status mismatch");
    assert(phase3.scheduler_enabled === false, "mission Phase 3 scheduler enabled");
    assert(phase3.autonomous_scheduler_enabled === false, "mission Phase 3 autonomous scheduler enabled");
    assert(phase3.scheduler_jobs_queued_count === 0, "mission Phase 3 queued jobs present");
    assert(phase3.scheduler_jobs_submitted_count === 0, "mission Phase 3 submitted jobs present");
    assert(phase3.hardware_submission_allowed_count === 0, "mission Phase 3 hardware submission allowed");
    assert(phase3.hardware_submitted_count === 0, "mission Phase 3 hardware submitted");
    assert(phase3.hardware_scheduler_enabled_count === 0, "mission Phase 3 hardware scheduler enabled");
    assert(phase3.execution_allowed_count === 0, "mission Phase 3 execution allowed");
    assert(phase3.paper_order_allowed_count === 0, "mission Phase 3 paper orders allowed");
    assert(phase3.trade_candidate_created_count === 0, "mission Phase 3 trade candidates created");
    assert(phase3.secret_value_exposed_count === 0, "mission Phase 3 exposes secret values");
    assert(phase3.raw_response_exposed_count === 0, "mission Phase 3 exposes raw responses");
    assert(phase3.local_absolute_path_exposed_count === 0, "mission Phase 3 exposes local absolute paths");
    assert(phase3.cloud_job_identifier_exposed_count === 0, "mission Phase 3 exposes cloud job identifiers");
    assert(/provider\/scheduler readiness only/i.test(phase3.boundary || ""), "mission Phase 3 boundary missing provider/scheduler scope");
    assert(/not execution readiness/i.test(phase3.boundary || ""), "mission Phase 3 boundary missing execution-readiness block");
    const phase4 = mission.phase4_strategy || {};
    assert(phase4.phase === "Q4", "mission Phase 4 phase mismatch");
    assert(phase4.stage === "Q4-12", "mission Phase 4 stage mismatch");
    assert(phase4.strategy_document_status === "validated", "mission Phase 4 strategy document not validated");
    const phase4Approved = phase4.approval_event_status === "approved";
    if (phase4Approved) {
        assert(phase4.stage_status === "phase4_certified", "mission Phase 4 stage status mismatch");
    } else {
        assert(phase4.stage_status === "blocked_pending_explicit_approval", "mission Phase 4 stage status mismatch");
        assert(phase4.approval_event_status === "amendments_required", "mission Phase 4 approval state mismatch");
    }
    assert(phase4.approval_logged === true, "mission Phase 4 approval event not logged");
    assert(phase4.toggle_count === status.phase4_strategy.toggle_count, "mission Phase 4 toggle count mismatch");
    if (phase4Approved) {
        assert(phase4.approved_shadow_strategy_toggle_count === phase4.toggle_count, "mission Phase 4 approved-shadow toggle count mismatch");
        assert(phase4.phase4_certification_allowed === true, "mission Phase 4 certification not allowed");
        assert(phase4.phase4_certified === true, "mission Phase 4 not certified");
        assert(phase4.phase5_handoff_allowed === true, "mission Phase 4 handoff not allowed");
        assert(phase4.certification_status === "certified", "mission Phase 4 certification status mismatch");
        assert(phase4.certification_blocker_count === 0, "mission Phase 4 blockers present");
    } else {
        assert(phase4.approved_shadow_strategy_toggle_count === 0, "mission Phase 4 approved-shadow toggles enabled");
        assert(phase4.phase4_certification_allowed === false, "mission Phase 4 certification allowed");
        assert(phase4.phase4_certified === false, "mission Phase 4 certified unexpectedly");
        assert(phase4.phase5_handoff_allowed === false, "mission Phase 4 handoff allowed");
        assert(phase4.certification_status === "blocked", "mission Phase 4 certification status mismatch");
        assert(phase4.certification_blocker_count >= 1, "mission Phase 4 blocker count missing");
    }
    assert(phase4.trade_candidate_count === 0, "mission Phase 4 trade candidates created");
    assert(phase4.execution_allowed_count === 0, "mission Phase 4 execution allowed");
    assert(phase4.paper_order_allowed_count === 0, "mission Phase 4 paper orders allowed");
    assert(phase4.broker_write_allowed_count === 0, "mission Phase 4 broker writes allowed");
    assert(phase4.live_capital_enabled_count === 0, "mission Phase 4 live capital enabled");
    assert(/cannot create trade candidates/i.test(phase4.boundary || ""), "mission Phase 4 boundary is weak");
    const phase5 = mission.phase5_layer_b || {};
    assert(phase5.phase === "Q5", "mission Phase 5 phase mismatch");
    assert(phase5.layer === "Layer B", "mission Phase 5 layer mismatch");
    assert(phase5.status === status.phase5_layer_b_readiness.status, "mission Phase 5 status mismatch");
    assert(phase5.implementation_plan_allowed === true, "mission Phase 5 plan should be allowed");
    assert(phase5.implementation_allowed === Boolean(status.phase5_layer_b_readiness.phase5_layer_b_implementation_allowed), "mission Phase 5 implementation mismatch");
    assert(phase5.orchestration_start_allowed === false, "mission Phase 5 orchestration start allowed");
    assert(phase5.nonapproval_blocker_count === 0, "mission Phase 5 non-approval blockers present");
    assert(phase5.paper_order_staging_status === status.phase5_paper_order_staging_gate.status, "mission Phase 5 paper-order staging status mismatch");
    assert(phase5.paper_order_staging_record_count === status.phase5_paper_order_staging_gate.staging_record_count, "mission Phase 5 paper-order staging record mismatch");
    assert(phase5.paper_order_staged_count === status.phase5_paper_order_staging_gate.staged_order_count, "mission Phase 5 staged order count mismatch");
    assert(phase5.paper_order_staging_event_log_written === true, "mission Phase 5 staging event log missing");
    assert(phase5.alpaca_paper_dry_run_status === status.phase5_alpaca_paper_dry_run.status, "mission Phase 5 Alpaca dry-run status mismatch");
    assert(phase5.alpaca_paper_dry_run_record_count === status.phase5_alpaca_paper_dry_run.dry_run_record_count, "mission Phase 5 Alpaca dry-run record mismatch");
    assert(phase5.alpaca_paper_dry_run_request_preview_count === status.phase5_alpaca_paper_dry_run.request_preview_count, "mission Phase 5 Alpaca dry-run request preview mismatch");
    assert(phase5.alpaca_paper_dry_run_receipt_count === status.phase5_alpaca_paper_dry_run.dry_run_receipt_count, "mission Phase 5 Alpaca dry-run receipt mismatch");
    assert(phase5.alpaca_paper_dry_run_event_log_written === true, "mission Phase 5 Alpaca dry-run event log missing");
    assert(phase5.alpaca_paper_dry_run_broker_post_called === false, "mission Phase 5 Alpaca dry-run broker POST called");
    assert(phase5.paper_submit_enablement_status === status.phase5_paper_submit_enablement_gate.status, "mission Phase 5 paper-submit enablement status mismatch");
    assert(phase5.paper_submit_enablement_record_count === status.phase5_paper_submit_enablement_gate.submit_enablement_record_count, "mission Phase 5 paper-submit enablement record mismatch");
    assert(phase5.paper_submit_path_available_count === status.phase5_paper_submit_enablement_gate.submit_path_available_count, "mission Phase 5 paper-submit path count mismatch");
    assert(phase5.paper_submit_approval_state === status.phase5_paper_submit_enablement_gate.paper_submit_approval_state, "mission Phase 5 paper-submit approval state mismatch");
    assert(phase5.paper_submit_approval_present === Boolean(status.phase5_paper_submit_enablement_gate.paper_submit_approval_present), "mission Phase 5 paper-submit approval mismatch");
    assert(phase5.paper_submit_event_log_written === true, "mission Phase 5 paper-submit event log missing");
    assert(phase5.paper_submit_broker_post_called === false, "mission Phase 5 paper-submit broker POST called");
    assert(phase5.prediction_market_adapter_status === status.phase5_prediction_market_adapter.status, "mission Phase 5 prediction-market adapter status mismatch");
    assert(phase5.prediction_market_route_count === status.phase5_prediction_market_adapter.prediction_market_route_count, "mission Phase 5 prediction-market route count mismatch");
    assert(phase5.prediction_market_context_count === status.phase5_prediction_market_adapter.prediction_market_context_count, "mission Phase 5 prediction-market context count mismatch");
    assert(phase5.prediction_market_read_only_route_count === status.phase5_prediction_market_adapter.read_only_route_count, "mission Phase 5 prediction-market read-only count mismatch");
    assert(phase5.prediction_market_live_blocked_route_count === status.phase5_prediction_market_adapter.live_blocked_count, "mission Phase 5 prediction-market live-blocked count mismatch");
    assert(phase5.prediction_market_write_allowed_count === 0, "mission Phase 5 prediction-market writes allowed");
    assert(phase5.prediction_market_spend_allowed_count === 0, "mission Phase 5 prediction-market spend allowed");
    assert(phase5.prediction_market_preference_provenance_status === status.phase5_prediction_market_adapter.preference_provenance_status, "mission Phase 5 prediction-market provenance mismatch");
    assert(phase5.prediction_market_preference_source_quorum_credit_allowed === false, "mission Phase 5 prediction-market source-quorum credit allowed");
    assert(phase5.prediction_market_event_log_written === true, "mission Phase 5 prediction-market event log missing");
    assert(phase5.telegram_notifier_status === status.phase5_telegram_notifier.status, "mission Phase 5 Telegram notifier status mismatch");
    assert(phase5.telegram_notifier_alert_type_count === status.phase5_telegram_notifier.alert_type_count, "mission Phase 5 Telegram notifier alert count mismatch");
    assert(phase5.telegram_notifier_eligible_alert_count === status.phase5_telegram_notifier.eligible_alert_count, "mission Phase 5 Telegram notifier eligible count mismatch");
    assert(phase5.telegram_notifier_queued_count === status.phase5_telegram_notifier.queued_dry_run_alert_count, "mission Phase 5 Telegram notifier queued count mismatch");
    assert(phase5.telegram_notifier_outbox_written_count === status.phase5_telegram_notifier.outbox_message_written_count, "mission Phase 5 Telegram notifier outbox count mismatch");
    assert(phase5.telegram_notifier_suppressed_count === status.phase5_telegram_notifier.suppressed_alert_count, "mission Phase 5 Telegram notifier suppressed count mismatch");
    assert(phase5.telegram_notifier_send_gate === "disabled", "mission Phase 5 Telegram notifier send gate enabled");
    assert(phase5.telegram_notifier_mode === "dry_run", "mission Phase 5 Telegram notifier not dry-run");
    assert(phase5.telegram_notifier_command_path_enabled_count === 0, "mission Phase 5 Telegram command path enabled");
    assert(phase5.telegram_notifier_live_send_allowed_count === 0, "mission Phase 5 Telegram live send allowed");
    assert(phase5.telegram_notifier_event_log_written === true, "mission Phase 5 Telegram notifier event log missing");
    assert(phase5.position_monitor_status === status.phase5_position_monitor.status, "mission Phase 5 position monitor status mismatch");
    assert(phase5.position_monitor_record_count === status.phase5_position_monitor.monitor_record_count, "mission Phase 5 position monitor record mismatch");
    assert(phase5.position_monitor_position_record_count === status.phase5_position_monitor.position_record_count, "mission Phase 5 position record mismatch");
    assert(phase5.position_monitor_closed_trade_summary_count === status.phase5_position_monitor.closed_trade_summary_count, "mission Phase 5 closed trade summary mismatch");
    assert(phase5.position_monitor_submitted_order_count === status.phase5_position_monitor.submitted_order_count, "mission Phase 5 position monitor submitted order mismatch");
    assert(phase5.position_monitor_mirrored_order_count === status.phase5_position_monitor.mirrored_order_count, "mission Phase 5 position monitor mirrored order mismatch");
    assert(phase5.position_monitor_mirrored_order_count >= phase5.position_monitor_submitted_order_count, "mission Phase 5 submitted orders are not mirrored");
    assert(phase5.position_monitor_open_position_count === status.phase5_position_monitor.open_position_count, "mission Phase 5 position monitor open position mismatch");
    assert(phase5.position_monitor_closed_trade_count === status.phase5_position_monitor.closed_trade_count, "mission Phase 5 position monitor closed trade mismatch");
    assert(phase5.position_monitor_failed_reconciliation_count === 0, "mission Phase 5 position monitor reconciliation failures present");
    assert(phase5.position_monitor_event_log_written === true, "mission Phase 5 position monitor event log missing");
    assert(phase5.position_monitor_write_authority_count === 0, "mission Phase 5 position monitor write authority enabled");
    assert(phase5.position_monitor_close_allowed_count === 0, "mission Phase 5 position monitor close allowed");
    assert(phase5.position_monitor_resize_allowed_count === 0, "mission Phase 5 position monitor resize allowed");
    assert(phase5.position_monitor_cancel_allowed_count === 0, "mission Phase 5 position monitor cancel allowed");
    const signalReview = status.phase5_signal_review || {};
    assert(phase5.signal_review_status === signalReview.status, "mission Phase 5 signal review status mismatch");
    assert(phase5.signal_review_record_count === signalReview.signal_review_record_count, "mission Phase 5 signal review record mismatch");
    assert(phase5.signal_review_decision_chain_count === signalReview.decision_chain_count, "mission Phase 5 signal review chain mismatch");
    assert(phase5.signal_review_governance_comment_event_count === signalReview.governance_comment_event_count, "mission Phase 5 signal review comment event mismatch");
    assert(phase5.signal_review_kill_switch_action_event_count === signalReview.kill_switch_action_event_count, "mission Phase 5 signal review kill-switch event mismatch");
    assert(phase5.signal_review_backend_truth_displayed_count === signalReview.backend_truth_displayed_count, "mission Phase 5 signal review backend truth mismatch");
    assert(phase5.signal_review_ui_inferred_readiness_count === 0, "mission Phase 5 signal review inferred readiness present");
    assert(phase5.signal_review_event_log_written === true, "mission Phase 5 signal review event log missing");
    assert(phase5.signal_review_trade_approval_control_count === 0, "mission Phase 5 signal review approval controls present");
    assert(phase5.signal_review_order_place_control_count === 0, "mission Phase 5 signal review order controls present");
    assert(phase5.signal_review_position_close_control_count === 0, "mission Phase 5 signal review close controls present");
    assert(phase5.signal_review_position_resize_control_count === 0, "mission Phase 5 signal review resize controls present");
    assert(phase5.signal_review_order_cancel_control_count === 0, "mission Phase 5 signal review cancel controls present");
    assert(phase5.signal_review_broker_write_allowed_count === 0, "mission Phase 5 signal review broker writes present");
    assert(phase5.signal_review_prediction_market_write_allowed_count === 0, "mission Phase 5 signal review prediction-market writes present");
    assert(phase5.signal_review_live_capital_enabled_count === 0, "mission Phase 5 signal review live capital enabled");
    const paperTradeDrill = status.phase5_paper_trade_drill || {};
    assert(phase5.paper_trade_drill_status === paperTradeDrill.status, "mission Phase 5 paper trade drill status mismatch");
    assert(phase5.paper_trade_drill_state === paperTradeDrill.paper_trade_drill_state, "mission Phase 5 paper trade drill state mismatch");
    assert(phase5.paper_trade_drill_step_count === paperTradeDrill.step_count, "mission Phase 5 paper trade drill step count mismatch");
    assert(phase5.paper_trade_drill_blocker_count === paperTradeDrill.blocker_count, "mission Phase 5 paper trade drill blocker count mismatch");
    assert(phase5.paper_trade_drill_implementation_ready === true, "mission Phase 5 paper trade drill implementation not ready");
    assert(
        phase5.paper_trade_drill_complete === paperTradeDrill.paper_trade_drill_complete,
        "mission Phase 5 paper trade drill complete mismatch"
    );
    assert(
        phase5.paper_trade_drill_exit_gate_passed === paperTradeDrill.phase5_paper_trade_drill_exit_gate_passed,
        "mission Phase 5 paper trade drill exit gate mismatch"
    );
    assert(phase5.paper_trade_drill_submit_approval_present === Boolean(paperTradeDrill.paper_submit_approval_present), "mission Phase 5 paper trade drill approval mismatch");
    assert(phase5.paper_trade_drill_submit_path_available_count === paperTradeDrill.paper_submit_path_available_count, "mission Phase 5 paper trade drill submit path mismatch");
    assert(phase5.paper_trade_drill_submitted_order_count === paperTradeDrill.submitted_paper_order_count, "mission Phase 5 paper trade drill submitted order mismatch");
    assert(phase5.paper_trade_drill_open_position_count === paperTradeDrill.open_position_count, "mission Phase 5 paper trade drill open position mismatch");
    assert(phase5.paper_trade_drill_closed_trade_count === paperTradeDrill.closed_trade_count, "mission Phase 5 paper trade drill closed trade mismatch");
    assert(
        phase5.paper_trade_drill_postmortem_due_count === paperTradeDrill.postmortem_due_count,
        "mission Phase 5 paper trade drill postmortem due mismatch"
    );
    assert(phase5.paper_trade_drill_broker_post_called_count === 0, "mission Phase 5 paper trade drill broker POST called");
    assert(phase5.paper_trade_drill_live_capital_enabled_count === 0, "mission Phase 5 paper trade drill live capital enabled");
    const phase5Certification = status.phase5_certification || {};
    assert(phase5.certification_status === phase5Certification.status, "mission Phase 5 certification status mismatch");
    assert(phase5.certification_stage_status === phase5Certification.stage_status, "mission Phase 5 certification stage status mismatch");
    assert(phase5.certification_phase5_certified === phase5Certification.phase5_certified, "mission Phase 5 certification certified mismatch");
    assert(phase5.certification_phase5_exit_gate === phase5Certification.phase5_exit_gate, "mission Phase 5 certification exit gate mismatch");
    assert(
        phase5.certification_phase6_handoff_allowed === phase5Certification.phase6_handoff_allowed,
        "mission Phase 5 certification Phase 6 handoff mismatch"
    );
    assert(
        phase5.certification_phase7_planning_allowed === phase5Certification.phase7_planning_allowed,
        "mission Phase 5 certification Phase 7 planning mismatch"
    );
    assert(phase5.certification_phase7_proof_credit_allowed === false, "mission Phase 5 certification grants proof credit");
    assert(phase5.certification_input_gate_count === phase5Certification.input_gate_count, "mission Phase 5 certification gate count mismatch");
    assert(phase5.certification_input_gate_passed_count === phase5Certification.input_gate_passed_count, "mission Phase 5 certification passed count mismatch");
    assert(phase5.certification_input_gate_blocked_count === phase5Certification.input_gate_blocked_count, "mission Phase 5 certification blocked count mismatch");
    assert(phase5.certification_blocker_count === phase5Certification.certification_blocker_count, "mission Phase 5 certification blocker count mismatch");
    assert(
        phase5.certification_paper_trade_drill_complete === phase5Certification.paper_trade_drill_complete,
        "mission Phase 5 certification drill complete mismatch"
    );
    assert(
        phase5.certification_paper_trade_drill_exit_gate_passed === phase5Certification.paper_trade_drill_exit_gate_passed,
        "mission Phase 5 certification drill exit gate mismatch"
    );
    assert(phase5.certification_submitted_paper_order_count === phase5Certification.submitted_paper_order_count, "mission Phase 5 certification submitted order mismatch");
    assert(phase5.certification_open_position_count === phase5Certification.open_position_count, "mission Phase 5 certification open position mismatch");
    assert(phase5.certification_closed_trade_count === phase5Certification.closed_trade_count, "mission Phase 5 certification closed trade mismatch");
    assert(phase5.certification_live_capital_enabled_count === 0, "mission Phase 5 certification live capital enabled");
    const phase5Phase6Handoff = status.phase5_phase6_handoff || {};
    assert(phase5.phase6_handoff_status === phase5Phase6Handoff.status, "mission Phase 5 Phase 6 handoff status mismatch");
    assert(phase5.phase6_handoff_state === phase5Phase6Handoff.handoff_state, "mission Phase 5 Phase 6 handoff state mismatch");
    assert(phase5.phase6_handoff_blocker_count === phase5Phase6Handoff.blocker_count, "mission Phase 5 Phase 6 handoff blocker mismatch");
    assert(phase5.phase6_handoff_event_log_written === true, "mission Phase 5 Phase 6 handoff event log missing");
    assert(phase5.phase6_learning_loop_plan_allowed === phase5Phase6Handoff.phase6_learning_loop_plan_allowed, "mission Phase 5 Phase 6 plan mismatch");
    assert(phase5.phase6_learning_loop_implementation_allowed === false, "mission Phase 5 Phase 6 implementation allowed");
    assert(phase5.phase6_learning_write_allowed === false, "mission Phase 5 Phase 6 learning writes allowed");
    assert(phase5.phase6_knowledge_graph_write_allowed === false, "mission Phase 5 Phase 6 knowledge writes allowed");
    assert(phase5.phase6_required_module_count === phase5Phase6Handoff.phase6_required_module_count, "mission Phase 5 Phase 6 module count mismatch");
    assert(phase5.phase6_handoff_closed_trade_count === phase5Phase6Handoff.closed_trade_count, "mission Phase 5 Phase 6 closed trade mismatch");
    assert(phase5.phase6_handoff_postmortem_due_count === phase5Phase6Handoff.postmortem_due_count, "mission Phase 5 Phase 6 postmortem mismatch");
    assert(phase5.phase6_handoff_phase7_proof_credit_allowed === false, "mission Phase 5 Phase 6 grants proof credit");
    assert(phase5.phase6_handoff_live_capital_enabled_count === 0, "mission Phase 5 Phase 6 live capital enabled");
    const systemMap = status.phase5_system_map || {};
    assert(phase5.system_map_status === systemMap.status, "mission Phase 5 system map status mismatch");
    assert(phase5.system_map_node_count === systemMap.node_count, "mission Phase 5 system map node count mismatch");
    assert(phase5.system_map_lane_count === systemMap.lane_count, "mission Phase 5 system map lane count mismatch");
    assert(phase5.system_map_layer_b_node_count === systemMap.layer_b_node_count, "mission Phase 5 system map Layer B count mismatch");
    assert(phase5.system_map_backend_parity_error_count === 0, "mission Phase 5 system map parity errors present");
    assert(phase5.system_map_unsafe_control_count === 0, "mission Phase 5 system map unsafe controls present");
    assert(phase5.system_map_event_log_written === true, "mission Phase 5 system map event log missing");
    assert(phase5.system_map_dashboard_claims_trading_now === false, "mission Phase 5 system map claims trading now");
    assert(/cannot start Layer B orchestration/i.test(phase5.boundary || ""), "mission Phase 5 boundary is weak");
    assert(mission.system_stack.phase5_layer_b === status.phase5_layer_b_readiness.status, "mission stack Phase 5 mismatch");
    assert(mission.system_stack.phase5_paper_order_staging === status.phase5_paper_order_staging_gate.status, "mission stack Phase 5 paper-order staging mismatch");
    assert(mission.system_stack.phase5_alpaca_paper_dry_run === status.phase5_alpaca_paper_dry_run.status, "mission stack Phase 5 Alpaca dry-run mismatch");
    assert(mission.system_stack.phase5_paper_submit_enablement === status.phase5_paper_submit_enablement_gate.status, "mission stack Phase 5 paper-submit enablement mismatch");
    assert(mission.system_stack.phase5_prediction_market_adapter === status.phase5_prediction_market_adapter.status, "mission stack Phase 5 prediction-market adapter mismatch");
    assert(mission.system_stack.phase5_telegram_notifier === status.phase5_telegram_notifier.status, "mission stack Phase 5 Telegram notifier mismatch");
    assert(mission.system_stack.phase5_position_monitor === status.phase5_position_monitor.status, "mission stack Phase 5 position monitor mismatch");
    assert(mission.system_stack.phase5_signal_review === signalReview.status, "mission stack Phase 5 signal review mismatch");
    assert(mission.system_stack.phase5_paper_trade_drill === paperTradeDrill.status, "mission stack Phase 5 paper trade drill mismatch");
    assert(mission.system_stack.phase5_certification === phase5Certification.status, "mission stack Phase 5 certification mismatch");
    assert(mission.system_stack.phase5_phase6_handoff === phase5Phase6Handoff.status, "mission stack Phase 5 Phase 6 handoff mismatch");
    assert(mission.system_stack.phase5_system_map === systemMap.status, "mission stack Phase 5 system map mismatch");
    const phase6 = mission.phase6_learning_loop || {};
    const phase6Status = status.phase6_learning_loop || {};
    assert(mission.system_stack.phase6_learning_loop === phase6Status.status, "mission stack Phase 6 learning loop mismatch");
    assert(phase6.status === phase6Status.status, "mission Phase 6 status mismatch");
    assert(phase6.learning_state === phase6Status.learning_state, "mission Phase 6 learning state mismatch");
    assert(phase6.backend_derived === true, "mission Phase 6 is not backend-derived");
    assert(phase6.ui_inferred_readiness_count === 0, "mission Phase 6 inferred readiness present");
    assert(phase6.backend_parity_error_count === 0, "mission Phase 6 backend parity errors present");
    assert(phase6.postmortem_due_count === phase6Status.postmortem_due_count, "mission Phase 6 postmortem due mismatch");
    assert(phase6.approval_state === phase6Status.approval_state, "mission Phase 6 approval mismatch");
    assert(phase6.staged_graph_entry_count === phase6Status.staged_graph_entry_count, "mission Phase 6 graph staged mismatch");
    assert(phase6.model_weight_proposal_count === phase6Status.model_weight_proposal_count, "mission Phase 6 model proposal mismatch");
    assert(phase6.trust_score_proposal_count === phase6Status.trust_score_proposal_count, "mission Phase 6 trust proposal mismatch");
    assert(phase6.blocked_authority_count === phase6Status.blocked_authority_count, "mission Phase 6 blocked authority mismatch");
    assert(phase6.phase6_learning_write_allowed === false, "mission Phase 6 learning writes allowed");
    assert(phase6.phase6_knowledge_graph_write_allowed === false, "mission Phase 6 graph writes allowed");
    assert(phase6.phase7_proof_credit_allowed === false, "mission Phase 6 grants proof credit");
    assert(phase6.live_capital_enabled === false, "mission Phase 6 live capital enabled");
    assert(phase6.unsafe_write_counter_total === 0, "mission Phase 6 unsafe writes present");
    assert(/backend/i.test(phase6.boundary || ""), "mission Phase 6 boundary missing backend derivation");
    assert(/private prior/i.test(mission.trading_philosophy.boundary || ""), "mission philosophy boundary is weak");
    assert(mission.trading_philosophy.current_self_directive.length >= 4, "mission self-directive is too thin");
    assert(mission.trade_intent.candidate_count === status.trade_layer.candidates.length, "mission candidate count mismatch");
    assert(mission.trade_intent.observed_signal_count === status.trade_layer.watching.length, "mission observed signal count mismatch");
    assert(mission.trade_intent.execution_allowed_count === 0, "mission exposes execution authority");
    assert(mission.trade_intent.paper_order_submitted_count === 0, "mission exposes submitted paper orders");
    assert(mission.trade_intent.broker_post_called_count === 0, "mission exposes broker POST calls");
    assert(mission.portfolio.open_position_count === status.capital.open_positions.length, "mission open position count mismatch");
    assert(mission.portfolio.live_capital_enabled === false, "mission portfolio live capital enabled");
    assert(mission.portfolio.write_authority === false, "mission portfolio write authority enabled");
    assert(mission.safety.live_capital_enabled === false, "mission safety live capital enabled");
    assert(mission.safety.broker_write_allowed === false, "mission safety broker write enabled");
    assert(/read-only/i.test(mission.safety.boundary || ""), "mission safety boundary is weak");
    assert(mission.system_stack.preference_mcp === preferenceMcp.status, "mission stack Preference MCP mismatch");

    const rendered = await renderWithStatus(status);
    assertIncludes(rendered, "[data-mission-primary]", "Operating thesis");
    assertIncludes(rendered, "[data-mission-primary]", "hypotheses");
    assertIncludes(rendered, "[data-mission-primary]", "Mission control is read-only");
    assertIncludes(rendered, "[data-mission-primary]", "Replay");
    assertIncludes(rendered, "[data-mission-sources]", "logged-in/configured");
    assertIncludes(rendered, "[data-mission-sources]", "missing credentials");
    assertIncludes(rendered, "[data-mission-sources]", "replay");
    assertIncludes(rendered, "[data-mission-sources]", "Preference MCP");
    assertIncludes(rendered, "[data-mission-sources]", "domain packs");
    assertIncludes(rendered, "[data-mission-sources]", "observation inputs only");
    assertIncludes(rendered, "[data-mission-philosophy]", "Trading philosophy");
    assertIncludes(rendered, "[data-mission-philosophy]", "private prior");
    assertIncludes(rendered, "[data-mission-stack]", "Local LLM");
    assertIncludes(rendered, "[data-mission-stack]", "quantum oracle");
    assertIncludes(rendered, "[data-mission-stack]", "Phase 3");
    assertIncludes(rendered, "[data-mission-stack]", "Q-CTRL configured");
    assertIncludes(rendered, "[data-mission-stack]", "scheduler blocked");
    assertIncludes(rendered, "[data-mission-stack]", "hardware blocked");
    assertIncludes(rendered, "[data-mission-stack]", "not execution readiness");
    assertIncludes(rendered, "[data-mission-stack]", "Preference");
    assertIncludes(rendered, "[data-mission-stack]", "Phase 5");
    assertIncludes(rendered, "[data-mission-stack]", "Q5-6");
    assertIncludes(rendered, "[data-mission-stack]", "Q5-7");
    assertIncludes(rendered, "[data-mission-stack]", "Q5-8");
    assertIncludes(rendered, "[data-mission-stack]", "Q5-9");
    assertIncludes(rendered, "[data-mission-stack]", "Q5-10");
    assertIncludes(rendered, "[data-mission-stack]", "Q5-11");
    assertIncludes(rendered, "[data-mission-stack]", "Q5-12");
    assertIncludes(rendered, "[data-mission-stack]", "Q5-13");
    assertIncludes(rendered, "[data-mission-stack]", "Q5-14");
    assertIncludes(rendered, "[data-mission-stack]", "Q5E-10");
    assertIncludes(rendered, "[data-mission-stack]", "Q6 plan");
    assertIncludes(rendered, "[data-mission-stack]", "Q6 writes");
    assertIncludes(rendered, "[data-mission-stack]", "Q6-16");
    assertIncludes(rendered, "[data-mission-stack]", "deferred learning visible");
    assertIncludes(rendered, "[data-mission-stack]", "UI inferred 0");
    assertIncludes(rendered, "[data-mission-stack]", "blocked authorities");
    assertIncludes(rendered, "[data-mission-stack]", "Layer B plan allowed");
    assertIncludes(rendered, "[data-mission-stack]", "replay");
    assertIncludes(rendered, "[data-mission-stack]", "risk");
    assertIncludes(rendered, "[data-mission-strategy]", "Phase 4 strategy");
    assertIncludes(rendered, "[data-mission-strategy]", "approved");
    assertIncludes(rendered, "[data-mission-strategy]", "approved-shadow 5");
    assertIncludes(rendered, "[data-mission-strategy]", "cannot create trade candidates");
    assertIncludes(rendered, "[data-mission-trades]", "Trade intent");
    assertIncludes(rendered, "[data-mission-trades]", "Submitted");
    assertIncludes(rendered, "[data-mission-trades]", "non-executing");
    assertIncludes(rendered, "[data-mission-portfolio]", "Paper account");
    assertIncludes(rendered, "[data-mission-portfolio]", "P&L");
    assertIncludes(rendered, "[data-mission-portfolio]", "Write");

    console.log("dashboard_mission_control=ok");
}

main().catch((error) => {
    console.error(error.message);
    process.exitCode = 1;
});
