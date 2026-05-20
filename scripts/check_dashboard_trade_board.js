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

    assert(tradeLayer.store_status === "ok", "trade intent store is not ok");
    assert(summary.status === "ok", "trade summary is not ok");
    assert(/No broker order path exists/i.test(tradeLayer.boundary || ""), "trade layer boundary is weak");
    assert(/No broker order path exists/i.test(summary.boundary || ""), "trade summary boundary is weak");
    assert(observedSignals.length >= 1, "observed signals are missing");
    assert(candidates.length >= 1, "candidate trades are missing");
    assert(blocked.length >= 1, "blocked trades are missing");
    assert(summary.candidate_count === candidates.length, "candidate count mismatch");
    assert(summary.blocked_count === blocked.length, "blocked count mismatch");
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
    assertIncludes(rendered, "[data-trade-layer]", "Trade state ladder");
    assertIncludes(rendered, "[data-trade-layer]", "Watching");
    assertIncludes(rendered, "[data-trade-layer]", "Observed signal only");
    assertIncludes(rendered, "[data-trade-layer]", "not a candidate");
    assertIncludes(rendered, "[data-trade-layer]", "Considering Trade");
    assertIncludes(rendered, "[data-trade-layer]", "Candidate, not order");
    assertIncludes(rendered, "[data-trade-layer]", "USO options watch");
    assertIncludes(rendered, "[data-trade-layer]", "Blocked trade");
    assertIncludes(rendered, "[data-trade-layer]", "Semiconductor basket watch");
    assertIncludes(rendered, "[data-trade-layer]", "insufficient independent corroboration");
    assertIncludes(rendered, "[data-trade-layer]", "Akber filter");
    assertIncludes(rendered, "[data-trade-layer]", "Risk checks");
    assertIncludes(rendered, "[data-trade-layer]", "Risk Agent policy router");
    assertIncludes(rendered, "[data-trade-layer]", "Policy score");
    assertIncludes(rendered, "[data-trade-layer]", "broker write blocked");
    assertIncludes(rendered, "[data-trade-layer]", "Required next steps");
    assertIncludes(rendered, "[data-trade-layer]", "Execution Policy and kill switches");
    assertIncludes(rendered, "[data-trade-layer]", "Kill switches");
    assertIncludes(rendered, "[data-trade-layer]", "Execution checks");
    assertIncludes(rendered, "[data-trade-layer]", "no staged paper order");
    assertIncludes(rendered, "[data-trade-layer]", "live capital disabled");
    assertIncludes(rendered, "[data-trade-layer]", "No broker order path exists");
    assertIncludes(rendered, "[data-trade-layer]", "no broker route exists");
    assertIncludes(rendered, "[data-trade-layer]", "0 execution allowed");
    assertIncludes(rendered, "[data-trade-layer]", "0 paper orders allowed");
    assertIncludes(rendered, "[data-trade-layer]", "Preparing Paper Trade");
    assertIncludes(rendered, "[data-trade-layer]", "not connected yet");

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
