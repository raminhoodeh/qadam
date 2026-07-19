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
const siteRoot = path.resolve(
    process.env.QADAM_DASHBOARD_SITE_ROOT || path.join(repoRoot, "landing-page-repo")
);
const renderer = fs.readFileSync(path.join(siteRoot, "dashboard.js"), "utf8");
const css = fs.readFileSync(path.join(siteRoot, "auth.css"), "utf8");

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
        "Paper execution oversight",
        "Connection Path",
        "Alpaca Paper (Read-Only)",
        "Last Synchronization",
        "Mirror Freshness",
        "Reconciliation State",
        "Zero data skew. The internal system state matches the Alpaca broker mirror database perfectly.",
        "Lifecycle Integrity",
        "Live Mirror State",
        "Broker Mirror Idle — No active paper orders or positions.",
        "The broker mirror possesses no unresolved order or open-position exposure to monitor.",
        "Active Orders",
        "Open Positions",
        "Broker Exceptions",
        "Order History",
        "Order Activity",
        "Sort activity",
        "<option value=\"newest\">Newest</option>",
        "<option value=\"oldest\">Oldest</option>",
        "<option value=\"largest\">Largest Size</option>",
        "<option value=\"smallest\">Smallest Size</option>",
        "<option value=\"state\">Execution State</option>",
        "Stage 8 to Stage 9 handoff",
        "View full Trading History",
        "Read-only Alpaca Paper mirror",
        "The first seven are shown initially; View More reveals the next seven.",
        "data-order-mirror-state=\"idle\"",
        "data-order-active-count=\"0\"",
        "data-order-open-position-count=\"0\"",
        "data-order-broker-exception-count=\"0\"",
        "data-order-health-metric=\"connection-path\"",
        "data-order-health-metric=\"last-synchronization\"",
        "data-order-health-metric=\"mirror-freshness\"",
        "data-order-health-metric=\"reconciliation-state\"",
        "data-order-health-metric=\"lifecycle-integrity\"",
        "data-qsase-order-activity-sort",
        "data-qsase-order-activity-list",
        "data-qsase-progressive-count",
        "data-qsase-progressive-list=\"order-monitor\"",
        "data-qsase-page-size=\"7\"",
        "data-qsase-progressive-toggle-for=\"order-monitor\"",
        "View More +",
        "data-guide-marker=\"order_monitor\"",
        "data-guide-marker=\"order_monitor_recent_activity\"",
        "data-guide-marker=\"order_monitor_authority_boundary\"",
        "data-qsase-order-recent",
        "qsase-flow-handoff"
    ].forEach((needle) => assert(orderMonitor.includes(needle), `simplified Order Monitor missing ${needle}`));

    assert(
        /(?:\d+ closed paper trades? (?:is|are) ready for postmortem review\.|No closed paper trades currently await postmortem review\.)/.test(orderMonitor),
        "Order Monitor handoff does not reflect the current dynamic postmortem count"
    );

    [
        "How this page fits the flow",
        "Back to Test &amp; Decide",
        "Completed fills",
        "Orders needing attention",
        "Paper account chronology",
        "Position Lifecycle",
        "Same read-only chronology as Trading History",
        "data-qsase-order-timeline",
        "data-qsase-timeline-surface=\"order-monitor\"",
        "data-qsase-order-active",
        "Order Monitor Health",
        "Recent activity",
        "Newest first",
        ">All clear<",
        ">ALL CLEAR<"
    ].forEach((needle) => assert(!orderMonitor.includes(needle), `repeated Order Monitor content returned: ${needle}`));

    [
        "Broker context",
        "Can this snapshot be trusted?"
    ].forEach((needle) => assert(!orderMonitor.includes(needle), `retired Order Monitor label returned: ${needle}`));

    const recentRowCount = (orderMonitor.match(/class="qsase-recent-order-row/g) || []).length;
    assert(recentRowCount >= 7, `Order Monitor should export enough broker events for seven-row progressive disclosure, found ${recentRowCount}`);
    assert((orderMonitor.match(/<details class="qsase-recent-order-row/g) || []).length === recentRowCount, "recent events are not expandable disclosures");
    assert((orderMonitor.match(/class="qsase-order-record-detail"/g) || []).length >= recentRowCount, "recent events are missing expanded evidence");
    assert(orderMonitor.includes("Open Decision Room"), "expanded broker records do not reconnect to Decision Room context");
    assert(orderMonitor.includes('data-qsase-module-target="fund" data-qsase-view-target="timeline"'), "Trading History handoff missing");
    const outcomesLinkCount = (orderMonitor.match(/data-qsase-module-target="learn" data-qsase-view-target="outcomes"/g) || []).length;
    assert(outcomesLinkCount === 2, `Order Monitor should expose one lifecycle destination and one consistent Stage 9 handoff, found ${outcomesLinkCount}`);

    [
        "function renderQsaseRecentOrderActivityRow",
        "function qsaseRecentPaperActivity",
        "function qsaseOrderSortSize",
        "function renderQsaseOrderRecordDetails",
        "function qsaseOrderMonitorContext",
        "function initQsaseOrderActivitySorting",
        "function readQsaseOrderActivitySortPreference",
        "function writeQsaseOrderActivitySortPreference",
        "data-order-sort-time",
        "data-order-sort-size",
        "data-order-sort-state",
        "const recentRows = qsaseRecentPaperActivity(allRows, Math.max(allRows.length, 1))",
        "data-qsase-progressive-list=\"order-monitor\" data-qsase-page-size=\"7\"",
        "data-qsase-progressive-toggle-for=\"order-monitor\"",
        "initQsaseOrderActivitySorting(target)",
        "container.addEventListener(\"qsase:progressive-refresh\""
    ].forEach((needle) => assert(renderer.includes(needle), `Order Monitor renderer missing ${needle}`));

    [
        "function renderQsasePaperOrderRow",
        "function renderQsasePositionLifecycle",
        "function renderQsasePaperOrders"
    ].forEach((needle) => assert(!renderer.includes(needle), `legacy Order Monitor renderer returned: ${needle}`));

    [
        ".qsase-order-monitor-v3",
        ".qsase-order-page-header",
        ".qsase-order-health-strip",
        ".qsase-order-health-tooltip",
        ".qsase-order-mirror-banner",
        ".qsase-order-mirror-counts",
        ".qsase-order-activity-tools",
        ".qsase-order-sort-controls",
        ".qsase-order-help",
        ".qsase-recent-order-row",
        ".qsase-order-record-detail",
        ".qsase-order-detail-grid",
        ".qsase-order-decision-context",
        ".qsase-flow-handoff"
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
    assert(activeMonitor.includes("Active Exposure — Monitoring live paper orders or open positions."), "active mirror headline did not render");
    assert(activeMonitor.includes("Qadam is actively tracking execution loops and open position parameters inside the broker environment."), "active mirror explanation did not render");
    assert(activeMonitor.includes('data-order-mirror-state="active"'), "active mirror state marker missing");
    assert(activeMonitor.includes('data-order-active-count="1"'), "active order count was not bound from the fixture");
    assert(activeMonitor.includes("TEST"), "active order row did not render");
    assert(activeMonitor.includes("Accepted at broker"), "active order stage did not render");
    assert(activeMonitor.includes('<details class="qsase-recent-order-row buy"'), "active order is not present in the activity ledger");
    assert(activeMonitor.includes("Duplicate protection"), "active order details omit duplicate protection");
    assert(activeMonitor.includes("Risk context"), "active order details omit risk context");
    assert(activeMonitor.includes("Next expected event"), "active order details omit the next event");

    const degradedFixture = JSON.parse(JSON.stringify(status));
    const portfolio = degradedFixture.dashboard_portfolio;
    const qsasePortfolio = degradedFixture.qsase_dashboard?.dashboard_portfolio;
    const lifecycle = degradedFixture.qsase_dashboard?.sections?.paper_lifecycle_v2;
    const compatibilityLifecycle = degradedFixture.qsase_dashboard?.sections?.operator_dashboard?.compatibility_sections?.paper_lifecycle_v2;
    assert(portfolio && qsasePortfolio && lifecycle && compatibilityLifecycle, "Order Monitor degraded fixture inputs missing");
    portfolio.connection_status = "alpaca_paper_readonly_disconnected";
    portfolio.broker_mirror_freshness = {
        ...(portfolio.broker_mirror_freshness || {}),
        status: "stale",
        observed_at: "2026-07-01T08:00:00Z"
    };
    portfolio.portfolio_consistency = {
        ...(portfolio.portfolio_consistency || {}),
        status: "mismatch"
    };
    qsasePortfolio.connection_status = portfolio.connection_status;
    qsasePortfolio.broker_mirror_freshness = { ...portfolio.broker_mirror_freshness };
    qsasePortfolio.portfolio_consistency = { ...portfolio.portfolio_consistency };
    lifecycle.stale_accepted_order_count = 2;
    lifecycle.ambiguous_lifecycle_count = 1;
    compatibilityLifecycle.stale_accepted_order_count = 2;
    compatibilityLifecycle.ambiguous_lifecycle_count = 1;
    const degradedRendered = await renderWithStatus(degradedFixture);
    const degradedMonitor = orderMonitorHtml(degradedRendered);
    assert(degradedMonitor.includes("Alpaca Paper (Connection Unconfirmed)"), "connection path did not react to disconnected live data");
    assert(degradedMonitor.includes(">Stale</dd>"), "mirror freshness did not react to stale live data");
    assert(degradedMonitor.includes(">Needs review</dd>"), "reconciliation did not react to inconsistent live data");
    assert(degradedMonitor.includes(">3 records need review</dd>"), "lifecycle integrity did not react to record-health data");

    console.log("dashboard_order_monitor=ok");
    console.log(`dashboard_order_monitor_recent_event_count=${recentRowCount}`);
}

main().catch((error) => {
    console.error(error.message);
    process.exitCode = 1;
});
