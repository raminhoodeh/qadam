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
