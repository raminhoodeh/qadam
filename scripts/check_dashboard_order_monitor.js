#!/usr/bin/env node

const fs = require("node:fs");
const path = require("node:path");

const {
    assert,
    html,
    renderWithStatus,
    status
} = require("./check_dashboard_renderer.js");

const repoRoot = path.resolve(__dirname, "..");
const renderer = fs.readFileSync(path.join(repoRoot, "landing-page-repo", "dashboard.js"), "utf8");
const css = fs.readFileSync(path.join(repoRoot, "landing-page-repo", "auth.css"), "utf8");

function orderMonitorHtml(rendered) {
    const dashboard = html(rendered, "[data-stage7-dashboard-visibility]");
    const start = dashboard.indexOf('data-qsase-module-panel="trade" data-qsase-view-panel="orders"');
    const end = dashboard.indexOf('data-qsase-module-panel="learn"', start);
    assert(start >= 0 && end > start, "Order Monitor panel could not be isolated");
    return dashboard.slice(start, end);
}

async function main() {
    const rendered = await renderWithStatus(status);
    const orderMonitor = orderMonitorHtml(rendered);

    [
        "Order Monitor",
        "Pipeline",
        "No active paper orders or positions",
        "Order Monitor Health",
        "Mirror freshness",
        "Reconciliation",
        "Lifecycle integrity",
        "Recent activity",
        "Stage 9 learning queue",
        "View full Fund Timeline",
        "Read-only Alpaca Paper mirror",
        "Ten most recent paper broker events",
        "data-guide-marker=\"order_monitor\"",
        "data-guide-marker=\"order_monitor_pipeline\"",
        "data-guide-marker=\"order_monitor_health\"",
        "data-guide-marker=\"order_monitor_recent_activity\"",
        "data-guide-marker=\"order_monitor_authority_boundary\"",
        "data-qsase-order-recent",
        "qsase-order-learning-link"
    ].forEach((needle) => assert(orderMonitor.includes(needle), `simplified Order Monitor missing ${needle}`));

    [
        "How this page fits the flow",
        "Back to Test &amp; Decide",
        "Completed fills",
        "Orders needing attention",
        "Paper account chronology",
        "Position Lifecycle",
        "Same read-only chronology as the Fund Timeline",
        "data-qsase-order-timeline",
        "data-qsase-timeline-surface=\"order-monitor\""
    ].forEach((needle) => assert(!orderMonitor.includes(needle), `repeated Order Monitor content returned: ${needle}`));

    [
        "Broker context",
        "Can this snapshot be trusted?"
    ].forEach((needle) => assert(!orderMonitor.includes(needle), `retired Order Monitor label returned: ${needle}`));

    const recentRowCount = (orderMonitor.match(/class="qsase-recent-order-row/g) || []).length;
    assert(recentRowCount === 10, `Order Monitor should show ten recent events when enough records exist, found ${recentRowCount}`);
    assert((orderMonitor.match(/<details class="qsase-recent-order-row/g) || []).length === recentRowCount, "recent events are not expandable disclosures");
    assert((orderMonitor.match(/class="qsase-order-record-detail"/g) || []).length >= recentRowCount, "recent events are missing expanded evidence");
    assert(orderMonitor.includes("Open Decision Room"), "expanded broker records do not reconnect to Decision Room context");
    assert(orderMonitor.includes('data-qsase-module-target="fund" data-qsase-view-target="timeline"'), "Fund Timeline handoff missing");
    const outcomesLinkCount = (orderMonitor.match(/data-qsase-module-target="learn" data-qsase-view-target="outcomes"/g) || []).length;
    assert(outcomesLinkCount === 2, `Order Monitor should expose one lifecycle destination and one item-specific Stage 9 queue link, found ${outcomesLinkCount}`);

    [
        "function renderQsaseActiveOrderRow",
        "function renderQsaseActivePositionRow",
        "function renderQsaseRecentOrderActivityRow",
        "function qsaseRecentPaperActivity",
        "function renderQsaseOrderRecordDetails",
        "function qsaseOrderMonitorContext",
        "const recentRows = qsaseRecentPaperActivity(allRows, 10)"
    ].forEach((needle) => assert(renderer.includes(needle), `Order Monitor renderer missing ${needle}`));

    [
        "function renderQsasePaperOrderRow",
        "function renderQsasePositionLifecycle",
        "function renderQsasePaperOrders"
    ].forEach((needle) => assert(!renderer.includes(needle), `legacy Order Monitor renderer returned: ${needle}`));

    [
        ".qsase-order-monitor-v2",
        ".qsase-order-current-state",
        ".qsase-order-state-counts",
        ".qsase-order-broker-context",
        ".qsase-order-help",
        ".qsase-active-trade-row",
        ".qsase-order-lifecycle",
        ".qsase-recent-order-row",
        ".qsase-order-record-detail",
        ".qsase-order-detail-grid",
        ".qsase-order-decision-context",
        ".qsase-order-learning-link"
    ].forEach((needle) => assert(css.includes(needle), `Order Monitor CSS missing ${needle}`));

    [
        ".qsase-order-monitor-links",
        ".qsase-order-monitor-attention",
        ".qsase-order-monitor-timeline",
        ".qsase-order-timeline-list",
        ".qsase-lifecycle-path"
    ].forEach((needle) => assert(!css.includes(needle), `legacy Order Monitor CSS returned: ${needle}`));

    const fixture = JSON.parse(JSON.stringify(status));
    const history = fixture.qsase_dashboard?.sections?.trading_history;
    assert(history && Array.isArray(history.rows), "Order Monitor fixture history missing");
    history.rows.unshift({
        row_type: "paper_order_mirror_not_trade_intent",
        event_type: "buy_or_order",
        event_label: "Buy / order",
        instrument: "TEST",
        status: "accepted",
        quantity: 2,
        submitted_at: "2026-07-12T08:00:00Z"
    });
    const activeRendered = await renderWithStatus(fixture);
    const activeMonitor = orderMonitorHtml(activeRendered);
    assert(activeMonitor.includes("Active now"), "active order section did not render");
    assert(activeMonitor.includes("data-qsase-order-active"), "active order section marker missing");
    assert(activeMonitor.includes("TEST"), "active order row did not render");
    assert(activeMonitor.includes("Accepted at broker"), "active order stage did not render");
    assert(activeMonitor.includes('aria-current="step"'), "active order lifecycle lacks a current step");
    assert(activeMonitor.includes('<details class="qsase-active-trade-row pending"'), "active order is not expandable");
    assert(activeMonitor.includes("Duplicate protection"), "active order details omit duplicate protection");
    assert(activeMonitor.includes("Risk context"), "active order details omit risk context");
    assert(activeMonitor.includes("Next expected event"), "active order details omit the next event");

    console.log("dashboard_order_monitor=ok");
    console.log(`dashboard_order_monitor_recent_event_count=${recentRowCount}`);
}

main().catch((error) => {
    console.error(error.message);
    process.exitCode = 1;
});
