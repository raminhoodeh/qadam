#!/usr/bin/env node

const {
    assert,
    assertIncludes,
    html,
    renderWithStatus,
    status
} = require("./check_dashboard_renderer.js");

const EXPECTED_CHAIN_STEPS = [
    "signal_integrity",
    "approval_policy",
    "risk_agent",
    "kill_switches",
    "source_posture",
    "venue_status",
    "staged_order_status",
    "broker_receipt",
    "position_state"
];

const ZERO_COUNT_FIELDS = [
    "trade_approval_control_enabled_count",
    "trade_rejection_control_enabled_count",
    "order_place_control_enabled_count",
    "order_modify_control_enabled_count",
    "position_resize_control_enabled_count",
    "position_close_control_enabled_count",
    "order_cancel_control_enabled_count",
    "broker_write_allowed_count",
    "broker_post_called_count",
    "alpaca_post_called_count",
    "prediction_market_write_allowed_count",
    "paper_order_allowed_count",
    "paper_order_submitted_count",
    "telegram_command_path_enabled_count",
    "live_endpoint_allowed_count",
    "live_capital_enabled_count",
    "secret_value_exposed_count",
    "raw_payload_exposed_count",
    "local_path_exposed_count",
    "authorization_header_exposed_count",
    "account_identifier_exposed_count",
    "broker_order_identifier_exposed_count"
];

async function main() {
    const signalReview = status.phase5_signal_review || {};
    const records = Array.isArray(signalReview.records) ? signalReview.records : [];

    assert(signalReview.phase === "Q5", "signal review phase mismatch");
    assert(signalReview.stage === "Q5-12", "signal review stage mismatch");
    assert(signalReview.status === "ok", "signal review status mismatch");
    assert(signalReview.public_safe === true, "signal review is not public-safe");
    assert(signalReview.recorded === true, "signal review runtime artifact missing");
    assert(signalReview.event_log_written === true, "signal review event log missing");
    assert(signalReview.validation_error_count === 0, "signal review validation errors present");
    assert(signalReview.backend_validation_error_count === 0, "signal review backend validation errors present");
    assert(signalReview.signal_review_record_count === 5, "signal review record count mismatch");
    assert(signalReview.chain_step_count === EXPECTED_CHAIN_STEPS.length, "signal review chain step count mismatch");
    assert(signalReview.decision_chain_count === signalReview.signal_review_record_count * EXPECTED_CHAIN_STEPS.length, "signal review decision chain count mismatch");
    assert(signalReview.governance_action_count === signalReview.signal_review_record_count, "signal review governance action count mismatch");
    assert(signalReview.governance_comment_event_count === signalReview.signal_review_record_count, "signal review governance comment event count mismatch");
    assert(signalReview.kill_switch_action_available_count === signalReview.signal_review_record_count, "signal review kill-switch action availability mismatch");
    assert(signalReview.kill_switch_action_event_count === signalReview.signal_review_record_count, "signal review kill-switch event count mismatch");
    assert(signalReview.backend_truth_displayed_count === signalReview.signal_review_record_count, "signal review backend truth count mismatch");
    assert(signalReview.ui_inferred_readiness_count === 0, "signal review UI inferred readiness present");
    assert(signalReview.event_log_event_count === (
        signalReview.signal_review_record_count
        + signalReview.governance_comment_event_count
        + signalReview.kill_switch_action_event_count
    ), "signal review event log count mismatch");
    assert(records.length === signalReview.signal_review_record_count, "signal review public records mismatch");
    assert(/cannot call brokers or venues/i.test(signalReview.boundary || ""), "signal review boundary does not block brokers");
    assert(/cannot enable live capital/i.test(signalReview.boundary || ""), "signal review boundary does not block live capital");

    for (const field of ZERO_COUNT_FIELDS) {
        assert(signalReview[field] === 0, `signal review count should be zero: ${field}`);
    }

    const serialized = JSON.stringify(signalReview);
    assert(!serialized.includes("/Users/"), "signal review exposes a local absolute path");
    assert(!serialized.includes("Authorization"), "signal review exposes an authorization header");
    assert(!serialized.includes("pref_agent_"), "signal review exposes a Preference key");

    for (const record of records) {
        assert(record.backend_truth_displayed === true, "signal review record does not display backend truth");
        assert(record.ui_inferred_readiness === false, "signal review record infers readiness in UI");
        assert(record.trade_approval_control_enabled === false, "signal review record exposes approval control");
        assert(record.order_place_control_enabled === false, "signal review record exposes order control");
        assert(record.broker_write_allowed === false, "signal review record exposes broker write");
        assert(record.prediction_market_write_allowed === false, "signal review record exposes prediction-market write");
        assert(record.live_capital_enabled === false, "signal review record exposes live capital");

        const chain = record.decision_chain || {};
        for (const stepKey of EXPECTED_CHAIN_STEPS) {
            const step = chain[stepKey] || {};
            assert(step.key === stepKey, `signal review chain step key mismatch: ${stepKey}`);
            assert(step.truth_source === "backend_runtime_artifact", `signal review step is not backend truth: ${stepKey}`);
            assert(step.backend_status === step.display_status, `signal review step display mismatch: ${stepKey}`);
            assert(step.ui_inferred === false, `signal review step inferred in UI: ${stepKey}`);
            assert(Boolean(step.source_artifact_id), `signal review step missing source artifact: ${stepKey}`);
        }

        const action = record.governance_action || {};
        assert(Boolean(action.target_artifact_id), "signal review governance action missing target artifact");
        assert(action.comment_event_log_written === true, "signal review governance comment not event-logged");
        assert(action.kill_switch_action_event_log_written === true, "signal review kill-switch action not event-logged");
        assert(action.kill_switch_action_mode === "event_log_only_no_mutation", "signal review kill-switch action mode mismatch");
        assert(action.kill_switch_mutation_authority === false, "signal review kill-switch action can mutate state");
        assert(action.trade_approval_control_enabled === false, "signal review governance action exposes approval control");
        assert(action.order_place_control_enabled === false, "signal review governance action exposes order control");
        assert(action.broker_write_allowed === false, "signal review governance action exposes broker write");
        assert(action.live_capital_enabled === false, "signal review governance action exposes live capital");
    }

    const rendered = await renderWithStatus(status);
    const tradeHtml = html(rendered, "[data-trade-layer]");
    assert(tradeHtml.includes("data-phase5-signal-review"), "dashboard did not render the Q5-12 signal-review section");
    assertIncludes(rendered, "[data-trade-layer]", "Signal Review UI and governance actions");
    assertIncludes(rendered, "[data-trade-layer]", "Signal Review");
    assertIncludes(rendered, "[data-trade-layer]", "Decision chain");
    assertIncludes(rendered, "[data-trade-layer]", "Signal Integrity");
    assertIncludes(rendered, "[data-trade-layer]", "Approval policy");
    assertIncludes(rendered, "[data-trade-layer]", "Risk Agent");
    assertIncludes(rendered, "[data-trade-layer]", "Kill switches");
    assertIncludes(rendered, "[data-trade-layer]", "Source posture");
    assertIncludes(rendered, "[data-trade-layer]", "Venue status");
    assertIncludes(rendered, "[data-trade-layer]", "Staged order status");
    assertIncludes(rendered, "[data-trade-layer]", "Broker receipt");
    assertIncludes(rendered, "[data-trade-layer]", "Position state");
    assertIncludes(rendered, "[data-trade-layer]", "Governance comment");
    assertIncludes(rendered, "[data-trade-layer]", "Kill-switch action");
    assertIncludes(rendered, "[data-trade-layer]", "event_log_only_no_mutation");
    assertIncludes(rendered, "[data-trade-layer]", "no approval control");
    assertIncludes(rendered, "[data-trade-layer]", "no order control");
    assertIncludes(rendered, "[data-trade-layer]", "no broker write");
    assertIncludes(rendered, "[data-trade-layer]", "live capital disabled");

    console.log("dashboard_phase5_signal_review=ok");
}

main().catch((error) => {
    console.error(error.message);
    process.exitCode = 1;
});
