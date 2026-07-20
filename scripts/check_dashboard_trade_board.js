#!/usr/bin/env node

const {
    assert,
    assertIncludes,
    renderWithStatus,
    status,
    statusPath
} = require("./check_dashboard_renderer.js");

const REQUIRED_TRADE_INTENT_FIELDS = [
    "akber_filter",
    "blocked_reason",
    "boundary",
    "catalyst",
    "created_at",
    "direction",
    "evidence_summary",
    "execution_allowed",
    "holding_window",
    "instrument",
    "intent_id",
    "invalidation",
    "market_implied_probability",
    "paper_order_allowed",
    "price_gap",
    "probability_estimate",
    "proposed_entry",
    "risk_checks",
    "risk_size_gbp",
    "risk_size_pct",
    "risk_state",
    "source_signal_id",
    "source_type",
    "status",
    "strategy",
    "tags",
    "updated_at",
    "venue"
];

const REQUIRED_OBSERVED_SIGNAL_FIELDS = [
    "alert_id",
    "boundary",
    "chart_context",
    "direction",
    "execution_allowed",
    "indicator_state",
    "instrument",
    "observed_at",
    "paper_order_allowed",
    "price",
    "received_at",
    "setup_type",
    "source",
    "source_type",
    "status",
    "symbol",
    "timeframe",
    "trade_candidate_created",
    "trigger"
];

const REQUIRED_AKBER_FIELDS = [
    "approval_policy",
    "catalyst_identification",
    "low_volatility",
    "obv_volume",
    "options_distribution_gap",
    "technical_setup"
];

const REQUIRED_RISK_FIELDS = [
    "broker_heartbeat",
    "event_log",
    "hard_caps",
    "kill_switch",
    "signal_approval"
];

const REQUIRED_RISK_AGENT_FIELDS = [
    "authority",
    "boundary",
    "broker_write_allowed_count",
    "by_status",
    "execution_allowed_count",
    "max_risk_pct_per_idea",
    "order_created_count",
    "paper_order_allowed_count",
    "review_count",
    "reviews",
    "schema_version",
    "status"
];

const REQUIRED_RISK_REVIEW_FIELDS = [
    "blocked_reasons",
    "boundary",
    "broker_write_allowed",
    "checks",
    "execution_allowed",
    "instrument",
    "max_risk_gbp",
    "max_risk_pct",
    "order_created",
    "paper_account_status",
    "paper_order_allowed",
    "policy_score",
    "proposed_risk_gbp",
    "proposed_risk_pct",
    "required_next_steps",
    "review_id",
    "reviewed_at",
    "signal_integrity_status",
    "source_ref",
    "source_type",
    "status"
];

const REQUIRED_RISK_POLICY_CHECKS = [
    "broker_order_route",
    "broker_write",
    "drawdown",
    "execution_policy",
    "kill_switch",
    "live_capital",
    "mode",
    "paper_order_authority"
];

const REQUIRED_EXECUTION_POLICY_FIELDS = [
    "authority",
    "boundary",
    "broker_write_allowed_count",
    "by_status",
    "execution_allowed_count",
    "kill_switch_block_count",
    "live_capital_enabled_count",
    "paper_order_created_count",
    "review_count",
    "reviews",
    "schema_version",
    "staged_paper_order_allowed_count",
    "status"
];

const REQUIRED_EXECUTION_POLICY_REVIEW_FIELDS = [
    "blocked_reasons",
    "boundary",
    "broker_write_allowed",
    "checks",
    "execution_allowed",
    "instrument",
    "kill_switches",
    "live_capital_enabled",
    "paper_order_created",
    "policy_score",
    "required_next_steps",
    "review_id",
    "reviewed_at",
    "schema_version",
    "selected_venue",
    "source_risk_review_id",
    "staged_paper_order_allowed",
    "status",
    "venue_mode"
];

const REQUIRED_EXECUTION_POLICY_CHECKS = [
    "broker_order_route",
    "closed_trade_maturity",
    "event_log",
    "execution_policy_registry",
    "global_kill_switch",
    "live_capital",
    "operating_mode",
    "paper_order_contract",
    "risk_agent",
    "risk_agent_authority",
    "strategy_kill_switch",
    "venue_kill_switch",
    "venue_registry"
];

const REQUIRED_EXECUTION_KILL_SWITCHES = ["data", "global", "model", "strategy", "venue"];

const REQUIRED_STAGED_ORDER_FIELDS = [
    "authority",
    "boundary",
    "broker_write_allowed_count",
    "by_status",
    "execution_allowed_count",
    "live_capital_enabled_count",
    "paper_order_submittable_count",
    "reconciliation_ready_count",
    "review_count",
    "reviews",
    "schema_version",
    "staged_paper_order_created_count",
    "status"
];

const REQUIRED_STAGED_ORDER_REVIEW_FIELDS = [
    "account_scope",
    "blocked_reasons",
    "boundary",
    "broker_write_allowed",
    "execution_allowed",
    "hypothetical_order",
    "instrument",
    "live_capital_enabled",
    "paper_order_submittable",
    "reconciliation_checks",
    "required_next_steps",
    "review_id",
    "reviewed_at",
    "schema_version",
    "selected_venue",
    "source_execution_policy_review_id",
    "staged_paper_order_created",
    "status",
    "venue_mode"
];

const REQUIRED_HYPOTHETICAL_ORDER_FIELDS = [
    "direction",
    "event_log_ref",
    "idempotency_key",
    "instrument",
    "invalidation",
    "notional_gbp",
    "order_type",
    "quantity",
    "risk_gbp",
    "status",
    "venue"
];

const REQUIRED_RECONCILIATION_CHECKS = [
    "broker_route",
    "duplicate_order_guard",
    "event_log_prewrite",
    "execution_policy",
    "idempotency_key",
    "live_capital",
    "paper_account_mirror",
    "paper_account_write_authority",
    "post_submit_reconciliation",
    "postmortem_link",
    "pre_trade_snapshot",
    "staging_contract"
];

const REQUIRED_BROKER_RECONCILIATION_FIELDS = [
    "authority",
    "boundary",
    "broker_echo_verified_count",
    "broker_write_allowed_count",
    "by_status",
    "duplicate_order_guard_ready_count",
    "event_log_prewrite_created_count",
    "idempotency_key_allocated_count",
    "live_capital_enabled_count",
    "paper_order_submit_allowed_count",
    "post_submit_reconciliation_ready_count",
    "postmortem_link_ready_count",
    "pre_trade_snapshot_created_count",
    "review_count",
    "reviews",
    "schema_version",
    "status"
];

const REQUIRED_BROKER_RECONCILIATION_REVIEW_FIELDS = [
    "account_scope",
    "blocked_reasons",
    "boundary",
    "broker_echo",
    "broker_echo_verified",
    "broker_write_allowed",
    "duplicate_order_guard_ready",
    "event_log_prewrite_created",
    "hypothetical_order",
    "idempotency_key_allocated",
    "instrument",
    "live_capital_enabled",
    "paper_order_submit_allowed",
    "post_submit_reconciliation_ready",
    "postmortem_link_ready",
    "pre_trade_snapshot_created",
    "reconciliation_checks",
    "required_next_steps",
    "review_id",
    "reviewed_at",
    "schema_version",
    "selected_venue",
    "source_execution_policy_review_id",
    "source_staged_paper_order_review_id",
    "status",
    "venue_mode"
];

const REQUIRED_BROKER_ECHO_FIELDS = [
    "ack_status",
    "adapter",
    "client_order_id",
    "external_order_id",
    "fill_status",
    "raw_broker_payload_stored",
    "status",
    "submitted_at",
    "venue"
];

const REQUIRED_BROKER_RECONCILIATION_CHECKS = [
    "broker_adapter_mode",
    "broker_echo",
    "broker_route",
    "duplicate_order_guard",
    "event_log_prewrite",
    "idempotency_key",
    "kill_switch",
    "live_capital",
    "paper_account_mirror",
    "paper_account_write_authority",
    "paper_order_submittable",
    "post_submit_reconciliation",
    "postmortem_link",
    "pre_trade_snapshot",
    "source_staged_status",
    "staged_order_contract",
    "staged_order_created",
    "venue_registry_write_health"
];

const REQUIRED_PAPER_SUBMIT_RECEIPT_FIELDS = [
    "authority",
    "boundary",
    "broker_post_called_count",
    "broker_write_allowed_count",
    "by_status",
    "dry_run_receipt_created_count",
    "live_capital_enabled_count",
    "paper_order_submitted_count",
    "review_count",
    "reviews",
    "schema_version",
    "status"
];

const REQUIRED_PAPER_SUBMIT_RECEIPT_REVIEW_FIELDS = [
    "account_scope",
    "blocked_reasons",
    "boundary",
    "broker_echo",
    "broker_post_called",
    "broker_write_allowed",
    "duplicate_order_guard",
    "dry_run_receipt_created",
    "event_log_prewrite_schema",
    "hypothetical_order",
    "idempotency_design",
    "instrument",
    "live_capital_enabled",
    "paper_order_submitted",
    "pre_trade_snapshot_schema",
    "receipt_checks",
    "required_next_steps",
    "review_id",
    "reviewed_at",
    "schema_version",
    "selected_venue",
    "simulated_receipt",
    "source_broker_reconciliation_review_id",
    "source_execution_policy_review_id",
    "source_staged_paper_order_review_id",
    "status",
    "submitted_at",
    "venue_mode"
];

const REQUIRED_SIMULATED_RECEIPT_FIELDS = [
    "adapter",
    "broker_post_called",
    "client_order_id",
    "external_order_id",
    "idempotency_preview_key",
    "mode",
    "paper_order_submitted",
    "raw_broker_payload_stored",
    "status",
    "venue"
];

const REQUIRED_PAPER_SUBMIT_RECEIPT_CHECKS = [
    "broker_echo",
    "broker_post",
    "broker_reconciliation_contract",
    "broker_reconciliation_status",
    "broker_write",
    "duplicate_order_guard",
    "duplicate_order_guard_schema",
    "dry_run_receipt",
    "event_log_prewrite",
    "event_log_prewrite_schema",
    "idempotency_design",
    "idempotency_key",
    "kill_switch",
    "live_capital",
    "paper_account_mirror",
    "paper_account_write_authority",
    "paper_order_submission",
    "paper_order_submit_permission",
    "post_submit_reconciliation",
    "postmortem_link",
    "pre_trade_snapshot",
    "pre_trade_snapshot_schema",
    "venue_registry_write_health"
];

function hasOwn(value, key) {
    return Object.prototype.hasOwnProperty.call(value, key);
}

function missingFields(value, fields) {
    return fields.filter((field) => !hasOwn(value, field));
}

function assertNoAuthority(intent, label) {
    assert(intent.execution_allowed === false, `${label} allows execution`);
    assert(intent.paper_order_allowed === false, `${label} allows paper orders`);
}

async function main() {
    const tradeLayer = status.trade_layer || {};
    const summary = tradeLayer.summary || {};
    const observedSignals = Array.isArray(tradeLayer.watching) ? tradeLayer.watching : [];
    const candidates = Array.isArray(tradeLayer.candidates) ? tradeLayer.candidates : [];
    const blocked = Array.isArray(tradeLayer.blocked) ? tradeLayer.blocked : [];
    const riskAgent = tradeLayer.risk_agent || status.risk_agent || {};
    const riskReviews = Array.isArray(riskAgent.reviews) ? riskAgent.reviews : [];
    const executionPolicy = tradeLayer.execution_policy || status.execution_policy || {};
    const executionPolicyReviews = Array.isArray(executionPolicy.reviews) ? executionPolicy.reviews : [];
    const stagedPaperOrder = tradeLayer.staged_paper_order || status.staged_paper_order || {};
    const stagedPaperOrderReviews = Array.isArray(stagedPaperOrder.reviews) ? stagedPaperOrder.reviews : [];
    const brokerReconciliation = tradeLayer.broker_reconciliation || status.broker_reconciliation || {};
    const brokerReconciliationReviews = Array.isArray(brokerReconciliation.reviews)
        ? brokerReconciliation.reviews
        : [];
    const paperSubmitReceipt = tradeLayer.paper_submit_receipt || status.paper_submit_receipt || {};
    const paperSubmitReceiptReviews = Array.isArray(paperSubmitReceipt.reviews)
        ? paperSubmitReceipt.reviews
        : [];

    assert(tradeLayer.store_status === "ok", "trade intent store is not ok");
    assert(summary.status === "ok", "trade summary is not ok");
    assert(/No broker order path exists/i.test(tradeLayer.boundary || ""), "trade layer boundary is weak");
    assert(/No broker order path exists/i.test(summary.boundary || ""), "trade summary boundary is weak");
    assert(observedSignals.length >= 1, "observed signals are missing");
    assert(summary.candidate_count === candidates.length, "candidate count mismatch");
    assert(summary.blocked_count === blocked.length, "blocked count mismatch");
    assert(
        summary.intent_count === candidates.length + blocked.length,
        "trade intent classification count mismatch"
    );
    assert(summary.observed_signal_count === observedSignals.length, "observed signal count mismatch");
    assert(summary.execution_allowed_count === 0, "summary allows execution");
    assert(summary.paper_order_allowed_count === 0, "summary allows paper orders");

    const missingRiskAgent = missingFields(riskAgent, REQUIRED_RISK_AGENT_FIELDS);
    assert(!missingRiskAgent.length, `risk agent missing fields: ${missingRiskAgent.join(", ")}`);
    assert(riskAgent.status === "ok", "risk agent is not ok");
    assert(riskAgent.authority === "read_only_policy_router", "risk agent authority mismatch");
    assert(riskAgent.execution_allowed_count === 0, "risk agent allows execution");
    assert(riskAgent.paper_order_allowed_count === 0, "risk agent allows paper orders");
    assert(riskAgent.order_created_count === 0, "risk agent created orders");
    assert(riskAgent.broker_write_allowed_count === 0, "risk agent allows broker writes");
    assert(/cannot approve risk/i.test(riskAgent.boundary || ""), "risk agent boundary is weak");
    assert(riskReviews.length >= 1, "risk reviews are missing");

    for (const review of riskReviews) {
        const missing = missingFields(review, REQUIRED_RISK_REVIEW_FIELDS);
        assert(!missing.length, `${review.review_id || "risk review"} missing fields: ${missing.join(", ")}`);
        assert(review.execution_allowed === false, `${review.review_id} allows execution`);
        assert(review.paper_order_allowed === false, `${review.review_id} allows paper order`);
        assert(review.order_created === false, `${review.review_id} created order`);
        assert(review.broker_write_allowed === false, `${review.review_id} allows broker write`);
        assert(review.policy_score >= 0 && review.policy_score <= 1, `${review.review_id} has invalid policy score`);
        assert(REQUIRED_RISK_POLICY_CHECKS.every((field) => hasOwn(review.checks, field)), `${review.review_id} risk policy checks are incomplete`);
        assert(/cannot approve risk/i.test(review.boundary || ""), `${review.review_id} boundary is weak`);
    }

    const missingExecutionPolicy = missingFields(executionPolicy, REQUIRED_EXECUTION_POLICY_FIELDS);
    assert(!missingExecutionPolicy.length, `execution policy missing fields: ${missingExecutionPolicy.join(", ")}`);
    assert(executionPolicy.status === "ok", "execution policy is not ok");
    assert(executionPolicy.authority === "read_only_execution_policy", "execution policy authority mismatch");
    assert(executionPolicy.execution_allowed_count === 0, "execution policy allows execution");
    assert(executionPolicy.staged_paper_order_allowed_count === 0, "execution policy allows staged paper orders");
    assert(executionPolicy.paper_order_created_count === 0, "execution policy created paper orders");
    assert(executionPolicy.broker_write_allowed_count === 0, "execution policy allows broker writes");
    assert(executionPolicy.live_capital_enabled_count === 0, "execution policy enables live capital");
    assert(/cannot stage paper orders/i.test(executionPolicy.boundary || ""), "execution policy boundary is weak");
    assert(executionPolicyReviews.length >= 1, "execution policy reviews are missing");

    for (const review of executionPolicyReviews) {
        const missing = missingFields(review, REQUIRED_EXECUTION_POLICY_REVIEW_FIELDS);
        assert(!missing.length, `${review.review_id || "execution policy review"} missing fields: ${missing.join(", ")}`);
        assert(review.execution_allowed === false, `${review.review_id} allows execution`);
        assert(review.staged_paper_order_allowed === false, `${review.review_id} allows staged paper order`);
        assert(review.paper_order_created === false, `${review.review_id} created paper order`);
        assert(review.broker_write_allowed === false, `${review.review_id} allows broker write`);
        assert(review.live_capital_enabled === false, `${review.review_id} enables live capital`);
        assert(review.policy_score >= 0 && review.policy_score <= 1, `${review.review_id} has invalid policy score`);
        assert(REQUIRED_EXECUTION_POLICY_CHECKS.every((field) => hasOwn(review.checks, field)), `${review.review_id} execution checks are incomplete`);
        assert(REQUIRED_EXECUTION_KILL_SWITCHES.every((field) => hasOwn(review.kill_switches, field)), `${review.review_id} kill switches are incomplete`);
        assert(/cannot stage orders/i.test(review.boundary || ""), `${review.review_id} boundary is weak`);
    }

    const missingStagedOrder = missingFields(stagedPaperOrder, REQUIRED_STAGED_ORDER_FIELDS);
    assert(!missingStagedOrder.length, `staged paper-order missing fields: ${missingStagedOrder.join(", ")}`);
    assert(stagedPaperOrder.status === "ok", "staged paper-order contract is not ok");
    assert(stagedPaperOrder.authority === "disabled_staged_order_contract", "staged paper-order authority mismatch");
    assert(stagedPaperOrder.execution_allowed_count === 0, "staged paper-order allows execution");
    assert(stagedPaperOrder.staged_paper_order_created_count === 0, "staged paper-order created staged orders");
    assert(stagedPaperOrder.paper_order_submittable_count === 0, "staged paper-order is submittable");
    assert(stagedPaperOrder.broker_write_allowed_count === 0, "staged paper-order allows broker writes");
    assert(stagedPaperOrder.live_capital_enabled_count === 0, "staged paper-order enables live capital");
    assert(/cannot create staged orders/i.test(stagedPaperOrder.boundary || ""), "staged paper-order boundary is weak");
    assert(stagedPaperOrderReviews.length >= 1, "staged paper-order reviews are missing");

    for (const review of stagedPaperOrderReviews) {
        const missing = missingFields(review, REQUIRED_STAGED_ORDER_REVIEW_FIELDS);
        assert(!missing.length, `${review.review_id || "staged order review"} missing fields: ${missing.join(", ")}`);
        assert(review.execution_allowed === false, `${review.review_id} allows execution`);
        assert(review.staged_paper_order_created === false, `${review.review_id} created staged order`);
        assert(review.paper_order_submittable === false, `${review.review_id} is submittable`);
        assert(review.broker_write_allowed === false, `${review.review_id} allows broker write`);
        assert(review.live_capital_enabled === false, `${review.review_id} enables live capital`);
        assert(REQUIRED_HYPOTHETICAL_ORDER_FIELDS.every((field) => hasOwn(review.hypothetical_order, field)), `${review.review_id} hypothetical order is incomplete`);
        assert(review.hypothetical_order.status === "not_created", `${review.review_id} hypothetical order was created`);
        assert(REQUIRED_RECONCILIATION_CHECKS.every((field) => hasOwn(review.reconciliation_checks, field)), `${review.review_id} reconciliation checks are incomplete`);
        assert(/cannot create a staged order/i.test(review.boundary || ""), `${review.review_id} boundary is weak`);
    }

    const missingBrokerReconciliation = missingFields(
        brokerReconciliation,
        REQUIRED_BROKER_RECONCILIATION_FIELDS
    );
    assert(
        !missingBrokerReconciliation.length,
        `broker reconciliation missing fields: ${missingBrokerReconciliation.join(", ")}`
    );
    assert(brokerReconciliation.status === "ok", "broker reconciliation contract is not ok");
    assert(
        brokerReconciliation.authority === "read_only_broker_reconciliation",
        "broker reconciliation authority mismatch"
    );
    [
        "idempotency_key_allocated_count",
        "event_log_prewrite_created_count",
        "pre_trade_snapshot_created_count",
        "duplicate_order_guard_ready_count",
        "broker_echo_verified_count",
        "post_submit_reconciliation_ready_count",
        "postmortem_link_ready_count",
        "paper_order_submit_allowed_count",
        "broker_write_allowed_count",
        "live_capital_enabled_count"
    ].forEach((field) => {
        assert(brokerReconciliation[field] === 0, `broker reconciliation ${field} is non-zero`);
    });
    assert(
        /cannot submit paper orders/i.test(brokerReconciliation.boundary || ""),
        "broker reconciliation boundary is weak"
    );
    assert(brokerReconciliationReviews.length >= 1, "broker reconciliation reviews are missing");

    for (const review of brokerReconciliationReviews) {
        const missing = missingFields(review, REQUIRED_BROKER_RECONCILIATION_REVIEW_FIELDS);
        assert(!missing.length, `${review.review_id || "broker reconciliation review"} missing fields: ${missing.join(", ")}`);
        [
            "idempotency_key_allocated",
            "event_log_prewrite_created",
            "pre_trade_snapshot_created",
            "duplicate_order_guard_ready",
            "broker_echo_verified",
            "post_submit_reconciliation_ready",
            "postmortem_link_ready",
            "paper_order_submit_allowed",
            "broker_write_allowed",
            "live_capital_enabled"
        ].forEach((field) => {
            assert(review[field] === false, `${review.review_id} has ${field} enabled`);
        });
        assert(
            REQUIRED_BROKER_ECHO_FIELDS.every((field) => hasOwn(review.broker_echo, field)),
            `${review.review_id} broker echo is incomplete`
        );
        assert(review.broker_echo.status === "not_requested", `${review.review_id} requested broker echo`);
        assert(
            REQUIRED_BROKER_RECONCILIATION_CHECKS.every((field) => hasOwn(review.reconciliation_checks, field)),
            `${review.review_id} broker reconciliation checks are incomplete`
        );
        assert(
            review.reconciliation_checks.broker_route === "fail_closed_no_broker_submit_route",
            `${review.review_id} broker route is not fail closed`
        );
        assert(
            review.reconciliation_checks.idempotency_key === "fail_not_allocated",
            `${review.review_id} allocated an idempotency key`
        );
        assert(
            review.reconciliation_checks.event_log_prewrite === "fail_not_written",
            `${review.review_id} wrote an Event Log prewrite`
        );
        assert(/cannot submit paper orders/i.test(review.boundary || ""), `${review.review_id} boundary is weak`);
    }

    const missingPaperSubmitReceipt = missingFields(
        paperSubmitReceipt,
        REQUIRED_PAPER_SUBMIT_RECEIPT_FIELDS
    );
    assert(
        !missingPaperSubmitReceipt.length,
        `paper-submit receipt missing fields: ${missingPaperSubmitReceipt.join(", ")}`
    );
    assert(paperSubmitReceipt.status === "ok", "paper-submit receipt contract is not ok");
    assert(paperSubmitReceipt.authority === "dry_run_receipt_only", "paper-submit receipt authority mismatch");
    [
        "paper_order_submitted_count",
        "broker_post_called_count",
        "broker_write_allowed_count",
        "live_capital_enabled_count"
    ].forEach((field) => {
        assert(paperSubmitReceipt[field] === 0, `paper-submit receipt ${field} is non-zero`);
    });
    assert(
        /cannot call broker POST routes/i.test(paperSubmitReceipt.boundary || ""),
        "paper-submit receipt boundary is weak"
    );
    assert(paperSubmitReceiptReviews.length >= 1, "paper-submit receipt reviews are missing");

    for (const review of paperSubmitReceiptReviews) {
        const missing = missingFields(review, REQUIRED_PAPER_SUBMIT_RECEIPT_REVIEW_FIELDS);
        assert(!missing.length, `${review.review_id || "paper-submit receipt review"} missing fields: ${missing.join(", ")}`);
        [
            "paper_order_submitted",
            "broker_post_called",
            "broker_write_allowed",
            "live_capital_enabled"
        ].forEach((field) => {
            assert(review[field] === false, `${review.review_id} has ${field} enabled`);
        });
        assert(review.submitted_at === "not_submitted", `${review.review_id} has submitted timestamp`);
        assert(
            REQUIRED_SIMULATED_RECEIPT_FIELDS.every((field) => hasOwn(review.simulated_receipt, field)),
            `${review.review_id} simulated receipt is incomplete`
        );
        assert(review.simulated_receipt.mode === "dry_run_only", `${review.review_id} is not dry-run only`);
        assert(review.simulated_receipt.broker_post_called === false, `${review.review_id} called broker POST`);
        assert(review.simulated_receipt.paper_order_submitted === false, `${review.review_id} submitted paper order`);
        assert(
            review.idempotency_design.broker_usable === false
                && review.idempotency_design.allocation_authority === false
                && String(review.idempotency_design.preview_key || "").startsWith("dryrun-"),
            `${review.review_id} idempotency design is not dry-run only`
        );
        assert(
            review.simulated_receipt.idempotency_preview_key === review.idempotency_design.preview_key,
            `${review.review_id} idempotency preview mismatch`
        );
        assert(
            review.event_log_prewrite_schema.write_performed === false
                && review.event_log_prewrite_schema.event_log_ref === "not_written",
            `${review.review_id} Event Log prewrite was performed`
        );
        assert(
            review.pre_trade_snapshot_schema.capture_performed === false
                && review.pre_trade_snapshot_schema.snapshot_ref === "not_captured",
            `${review.review_id} pre-trade snapshot was captured`
        );
        assert(
            review.duplicate_order_guard.lookup_performed === false
                && review.duplicate_order_guard.guard_write_performed === false
                && review.duplicate_order_guard.guard_key === review.idempotency_design.preview_key,
            `${review.review_id} duplicate-order guard has authority`
        );
        assert(
            REQUIRED_PAPER_SUBMIT_RECEIPT_CHECKS.every((field) => hasOwn(review.receipt_checks, field)),
            `${review.review_id} paper-submit receipt checks are incomplete`
        );
        assert(review.receipt_checks.broker_post === "pass_not_called", `${review.review_id} broker POST not closed`);
        assert(
            review.receipt_checks.paper_order_submission === "pass_not_submitted",
            `${review.review_id} paper order submission not closed`
        );
        assert(review.receipt_checks.idempotency_design === "pass_preview_only", `${review.review_id} idempotency design not closed`);
        assert(
            review.receipt_checks.event_log_prewrite_schema === "pass_schema_not_written",
            `${review.review_id} prewrite schema not closed`
        );
        assert(
            review.receipt_checks.pre_trade_snapshot_schema === "pass_schema_not_captured",
            `${review.review_id} snapshot schema not closed`
        );
        assert(
            review.receipt_checks.duplicate_order_guard_schema === "pass_guard_not_executed",
            `${review.review_id} duplicate guard schema not closed`
        );
        assert(/cannot call Alpaca POST routes/i.test(review.boundary || ""), `${review.review_id} boundary is weak`);
    }

    for (const signal of observedSignals) {
        if (signal.source_type !== "tradingview_paid_alert") continue;
        const missing = missingFields(signal, REQUIRED_OBSERVED_SIGNAL_FIELDS);
        assert(!missing.length, `${signal.alert_id || "observed signal"} missing fields: ${missing.join(", ")}`);
        assert(signal.status === "observed_signal", `${signal.alert_id} is not an observed signal`);
        assert(signal.trade_candidate_created === false, `${signal.alert_id} created a trade candidate`);
        assertNoAuthority(signal, signal.alert_id);
        assert(/cannot create a trade candidate, paper order, or broker action/i.test(signal.boundary || ""), `${signal.alert_id} boundary is weak`);
    }

    for (const intent of candidates) {
        const missing = missingFields(intent, REQUIRED_TRADE_INTENT_FIELDS);
        assert(!missing.length, `${intent.intent_id || "candidate"} missing fields: ${missing.join(", ")}`);
        assert(intent.status === "candidate" || intent.status === "risk_review", `${intent.intent_id} is not a candidate state`);
        assertNoAuthority(intent, intent.intent_id);
        assert(intent.risk_size_gbp === 0 && intent.risk_size_pct === 0, `${intent.intent_id} has non-zero risk`);
        assert(!intent.blocked_reason, `${intent.intent_id} has a blocked reason despite being a candidate`);
        assert(/no broker route exists/i.test(intent.boundary || ""), `${intent.intent_id} boundary is weak`);
        assert(REQUIRED_AKBER_FIELDS.every((field) => hasOwn(intent.akber_filter, field)), `${intent.intent_id} Akber filter is incomplete`);
        assert(REQUIRED_RISK_FIELDS.every((field) => hasOwn(intent.risk_checks, field)), `${intent.intent_id} risk checks are incomplete`);
    }

    for (const intent of blocked) {
        const missing = missingFields(intent, REQUIRED_TRADE_INTENT_FIELDS);
        assert(!missing.length, `${intent.intent_id || "blocked trade"} missing fields: ${missing.join(", ")}`);
        assert(intent.status === "blocked", `${intent.intent_id} is not blocked`);
        assertNoAuthority(intent, intent.intent_id);
        assert(intent.blocked_reason, `${intent.intent_id} missing blocked reason`);
        assert(intent.risk_size_gbp === 0 && intent.risk_size_pct === 0, `${intent.intent_id} has non-zero risk`);
        assert(/no broker route exists/i.test(intent.boundary || ""), `${intent.intent_id} boundary is weak`);
        assert(REQUIRED_AKBER_FIELDS.every((field) => hasOwn(intent.akber_filter, field)), `${intent.intent_id} Akber filter is incomplete`);
        assert(REQUIRED_RISK_FIELDS.every((field) => hasOwn(intent.risk_checks, field)), `${intent.intent_id} risk checks are incomplete`);
    }

    const rendered = await renderWithStatus(status);
    assertIncludes(rendered, "[data-trade-layer]", "Trades workspace");
    assertIncludes(rendered, "[data-trade-layer]", "Trade lifecycle board");
    assertIncludes(rendered, "[data-trade-layer]", "Verified performance only");
    assertIncludes(rendered, "[data-trade-layer]", "Observed signals");
    assertIncludes(rendered, "[data-trade-layer]", "Qualified setups");
    assertIncludes(rendered, "[data-trade-layer]", "Trade ideas");
    assertIncludes(rendered, "[data-trade-layer]", "Blocked ideas");
    assertIncludes(rendered, "[data-trade-layer]", "Draft paper orders");
    assertIncludes(rendered, "[data-trade-layer]", "Submitted paper orders");
    assertIncludes(rendered, "[data-trade-layer]", "Open positions");
    assertIncludes(rendered, "[data-trade-layer]", "Closed paper trades");
    assertIncludes(rendered, "[data-trade-layer]", "Postmortems due");
    assertIncludes(rendered, "[data-trade-layer]", "Consolidated trade readout");
    assertIncludes(rendered, "[data-trade-layer]", "Candidate is not order");
    assertIncludes(rendered, "[data-trade-layer]", "No broker order path exists");
    assertIncludes(rendered, "[data-trade-layer]", "0 execution allowed");
    assertIncludes(rendered, "[data-trade-layer]", "0 paper orders allowed");
    assertIncludes(rendered, "[data-trade-layer]", "Paper trade lifecycle");

    const emptyStatus = {
        ...status,
        trade_layer: {
            summary: {
                status: "ok",
                intent_count: 0,
                candidate_count: 0,
                blocked_count: 0,
                observed_signal_count: 0,
                execution_allowed_count: 0,
                paper_order_allowed_count: 0,
                boundary: "Local trade intent store only. No broker order path exists in D5."
            },
            risk_agent: {
                status: "ok",
                schema_version: 1,
                review_count: 0,
                by_status: {},
                execution_allowed_count: 0,
                paper_order_allowed_count: 0,
                order_created_count: 0,
                broker_write_allowed_count: 0,
                max_risk_pct_per_idea: 1,
                authority: "read_only_policy_router",
                reviews: [],
                boundary: "Risk Agent policy router is read-only and cannot approve risk or create orders."
            },
            execution_policy: {
                status: "ok",
                schema_version: 1,
                review_count: 0,
                by_status: {},
                execution_allowed_count: 0,
                staged_paper_order_allowed_count: 0,
                paper_order_created_count: 0,
                broker_write_allowed_count: 0,
                live_capital_enabled_count: 0,
                kill_switch_block_count: 0,
                authority: "read_only_execution_policy",
                reviews: [],
                boundary: "Execution policy is read-only and cannot stage paper orders or write to brokers."
            },
            staged_paper_order: {
                status: "ok",
                schema_version: 1,
                review_count: 0,
                by_status: {},
                execution_allowed_count: 0,
                staged_paper_order_created_count: 0,
                paper_order_submittable_count: 0,
                broker_write_allowed_count: 0,
                live_capital_enabled_count: 0,
                reconciliation_ready_count: 0,
                authority: "disabled_staged_order_contract",
                reviews: [],
                boundary: "Staged paper-order contract is disabled and read-only; it cannot create staged orders."
            },
            broker_reconciliation: {
                status: "ok",
                schema_version: 1,
                review_count: 0,
                by_status: {},
                idempotency_key_allocated_count: 0,
                event_log_prewrite_created_count: 0,
                pre_trade_snapshot_created_count: 0,
                duplicate_order_guard_ready_count: 0,
                broker_echo_verified_count: 0,
                post_submit_reconciliation_ready_count: 0,
                postmortem_link_ready_count: 0,
                paper_order_submit_allowed_count: 0,
                broker_write_allowed_count: 0,
                live_capital_enabled_count: 0,
                authority: "read_only_broker_reconciliation",
                reviews: [],
                boundary: "Broker reconciliation is read-only and cannot submit paper orders."
            },
            paper_submit_receipt: {
                status: "ok",
                schema_version: 1,
                review_count: 0,
                by_status: {},
                dry_run_receipt_created_count: 0,
                paper_order_submitted_count: 0,
                broker_post_called_count: 0,
                broker_write_allowed_count: 0,
                live_capital_enabled_count: 0,
                authority: "dry_run_receipt_only",
                reviews: [],
                boundary: "Paper-submit receipt is dry-run only and cannot call broker POST routes."
            },
            store_status: "ok",
            watching: [],
            candidates: [],
            blocked: [],
            staged_orders: [],
            submitted_orders: [],
            open_positions: [],
            closed_trades: [],
            postmortems_due: [],
            postmortems_complete: [],
            boundary: "D5 trade intent is local and non-executing. No broker order path exists."
        }
    };
    const emptyRendered = await renderWithStatus(emptyStatus);
    assertIncludes(emptyRendered, "[data-trade-layer]", "No observed signals");
    assertIncludes(emptyRendered, "[data-trade-layer]", "No candidates");
    assertIncludes(emptyRendered, "[data-trade-layer]", "No blocked trades");
    assertIncludes(emptyRendered, "[data-trade-layer]", "No Risk Agent reviews yet");
    assertIncludes(emptyRendered, "[data-trade-layer]", "No execution policy reviews yet");
    assertIncludes(emptyRendered, "[data-trade-layer]", "No staged paper-order reviews yet");
    assertIncludes(emptyRendered, "[data-trade-layer]", "No broker reconciliation reviews yet");
    assertIncludes(emptyRendered, "[data-trade-layer]", "No dry-run paper-submit reviews yet");
    assertIncludes(emptyRendered, "[data-trade-layer]", "not connected yet");

    console.log("Dashboard trade board contract OK");
    console.log(`Rendered snapshot: ${statusPath}`);
    console.log(`Observed signals: ${observedSignals.length}`);
    console.log(`Candidates: ${candidates.length}`);
    console.log(`Blocked trades: ${blocked.length}`);
}

main().catch((error) => {
    console.error(error.message);
    process.exitCode = 1;
});
