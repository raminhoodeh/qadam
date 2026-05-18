#!/usr/bin/env node

const {
    assert,
    assertIncludes,
    renderWithStatus,
    status,
    statusPath
} = require("./check_dashboard_renderer.js");

const TRADINGVIEW_SUMMARY_FIELDS = [
    "alert_count",
    "boundary",
    "duplicate_protection",
    "execution_allowed_count",
    "latest_observed_at",
    "observed_signals",
    "paper_order_allowed_count",
    "receiver_status",
    "status",
    "trade_candidate_created_count"
];

const OBSERVED_SIGNAL_FIELDS = [
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

const WATCHING_SOURCE_FIELDS = [
    "auth_class",
    "cadence",
    "can_influence_signals",
    "credential_status",
    "influence_boundary",
    "last_heartbeat",
    "last_payload_time",
    "pipeline",
    "promoted_adapter",
    "readiness",
    "registry_status",
    "source_key",
    "source_name",
    "status"
];

function hasOwn(value, key) {
    return Object.prototype.hasOwnProperty.call(value, key);
}

function missingFields(value, fields) {
    return fields.filter((field) => !hasOwn(value, field));
}

function assertObservationOnly(signal, label) {
    assert(signal.status === "observed_signal", `${label} is not observed_signal`);
    assert(signal.source_type === "tradingview_paid_alert", `${label} has wrong source_type`);
    assert(signal.execution_allowed === false, `${label} allows execution`);
    assert(signal.paper_order_allowed === false, `${label} allows paper orders`);
    assert(signal.trade_candidate_created === false, `${label} created a trade candidate`);
    assert(
        /cannot create a trade candidate, paper order, or broker action/i.test(signal.boundary || ""),
        `${label} boundary is weak`
    );
}

async function main() {
    const tradingView = status.tradingview_alerts || {};
    const watching = Array.isArray(status.watching) ? status.watching : [];
    const tradeWatching = Array.isArray(status.trade_layer?.watching) ? status.trade_layer.watching : [];
    const observedSignals = Array.isArray(tradingView.observed_signals) ? tradingView.observed_signals : [];
    const sourceRow = watching.find((source) => source.source_key === "tradingview_paid_alerts");

    const missingSummary = missingFields(tradingView, TRADINGVIEW_SUMMARY_FIELDS);
    assert(!missingSummary.length, `tradingview_alerts missing fields: ${missingSummary.join(", ")}`);
    assert(sourceRow, "TradingView watching source row is missing");
    const missingSource = missingFields(sourceRow, WATCHING_SOURCE_FIELDS);
    assert(!missingSource.length, `TradingView watching row missing fields: ${missingSource.join(", ")}`);

    assert(tradingView.status === "ok", "TradingView alert store is not ok");
    assert(tradingView.receiver_status === "local_contract_only", "TradingView receiver is not local-contract-only");
    assert(tradingView.duplicate_protection === "dedupe_key_sha256", "TradingView duplicate protection is not sha256");
    assert(tradingView.alert_count === observedSignals.length, "TradingView alert count mismatch");
    assert(observedSignals.length >= 1, "TradingView observed signals are missing");
    assert(tradingView.execution_allowed_count === 0, "TradingView summary allows execution");
    assert(tradingView.paper_order_allowed_count === 0, "TradingView summary allows paper orders");
    assert(tradingView.trade_candidate_created_count === 0, "TradingView summary created candidates");
    assert(/observed signals only/i.test(tradingView.boundary || ""), "TradingView summary boundary is weak");

    assert(sourceRow.pipeline === "market", "TradingView source is not in market pipeline");
    assert(sourceRow.registry_status === "d7_local_contract", "TradingView source registry status mismatch");
    assert(sourceRow.readiness === "observed alert source", "TradingView source readiness mismatch");
    assert(sourceRow.credential_status === "receiver_pending", "TradingView receiver credential state mismatch");
    assert(sourceRow.auth_class === "account_required", "TradingView auth class mismatch");
    assert(sourceRow.can_influence_signals === false, "TradingView can influence signals too early");
    assert(sourceRow.influence_boundary === "observed_signal_only_no_execution_path", "TradingView influence boundary mismatch");

    for (const signal of observedSignals) {
        const missingSignal = missingFields(signal, OBSERVED_SIGNAL_FIELDS);
        assert(!missingSignal.length, `${signal.alert_id || "TradingView signal"} missing fields: ${missingSignal.join(", ")}`);
        assertObservationOnly(signal, signal.alert_id);
        assert(!hasOwn(signal, "dedupe_key"), `${signal.alert_id} leaked dedupe key into public status`);
        assert(!hasOwn(signal, "qadam_receiver_key"), `${signal.alert_id} leaked receiver key`);
        assert(signal.indicator_state && Object.keys(signal.indicator_state).length > 0, `${signal.alert_id} missing indicator state`);
    }

    const tradeSignals = tradeWatching.filter((signal) => signal.source_type === "tradingview_paid_alert");
    assert(tradeSignals.length === observedSignals.length, "Trade Layer TradingView signal count mismatch");
    for (const signal of tradeSignals) {
        assertObservationOnly(signal, signal.alert_id);
    }

    const rendered = await renderWithStatus(status);
    assertIncludes(rendered, "[data-watching-list]", "TradingView Paid Alerts");
    assertIncludes(rendered, "[data-watching-list]", "observed alert source");
    assertIncludes(rendered, "[data-watching-list]", "receiver pending");
    assertIncludes(rendered, "[data-watching-list]", "d7 local contract");
    assertIncludes(rendered, "[data-watching-list]", "observed signal only no execution path");
    assertIncludes(rendered, "[data-trade-layer]", "TradingView alert source");
    assertIncludes(rendered, "[data-trade-layer]", "local contract only");
    assertIncludes(rendered, "[data-trade-layer]", "dedupe key sha256");
    assertIncludes(rendered, "[data-trade-layer]", "TradingView alerts are observed signals only. D7 has no execution route.");
    assertIncludes(rendered, "[data-trade-layer]", "TVC:USOIL");
    assertIncludes(rendered, "[data-trade-layer]", "Observed signal only");
    assertIncludes(rendered, "[data-trade-layer]", "not a candidate");
    assertIncludes(rendered, "[data-trade-layer]", "execution blocked");
    assertIncludes(rendered, "[data-trade-layer]", "no paper order");
    assertIncludes(rendered, "[data-trade-layer]", "cannot create a trade candidate, paper order, or broker action");

    const emptyStatus = {
        ...status,
        tradingview_alerts: {
            status: "ok",
            receiver_status: "local_contract_only",
            duplicate_protection: "dedupe_key_sha256",
            alert_count: 0,
            latest_observed_at: null,
            execution_allowed_count: 0,
            paper_order_allowed_count: 0,
            trade_candidate_created_count: 0,
            observed_signals: [],
            boundary: "TradingView alerts are observed signals only. D7 has no execution route."
        },
        watching: watching.map((source) => (
            source.source_key === "tradingview_paid_alerts"
                ? {
                    ...source,
                    status: "pending",
                    raw_status: "ok",
                    readiness: "secure receiver pending",
                    promoted_adapter: false,
                    last_heartbeat: null,
                    last_payload_time: null,
                    degraded_reason: "no alert snapshot yet"
                }
                : source
        )),
        trade_layer: {
            ...status.trade_layer,
            watching: [],
            summary: {
                ...(status.trade_layer?.summary || {}),
                observed_signal_count: 0,
                execution_allowed_count: 0,
                paper_order_allowed_count: 0
            }
        }
    };
    const emptyRendered = await renderWithStatus(emptyStatus);
    assertIncludes(emptyRendered, "[data-watching-list]", "secure receiver pending");
    assertIncludes(emptyRendered, "[data-trade-layer]", "No observed signals");
    assertIncludes(emptyRendered, "[data-trade-layer]", "local contract only");

    console.log("Dashboard TradingView source contract OK");
    console.log(`Rendered snapshot: ${statusPath}`);
    console.log(`TradingView alerts: ${observedSignals.length}`);
}

main().catch((error) => {
    console.error(error.message);
    process.exitCode = 1;
});
