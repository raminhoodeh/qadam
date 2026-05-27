#!/usr/bin/env node

const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");

const {
    assert,
    assertIncludes,
    html,
    renderWithStatus,
    status
} = require("./check_dashboard_renderer.js");

const repoRoot = path.resolve(__dirname, "..");
const htmlPath = path.join(repoRoot, "landing-page-repo", "dashboard", "index.html");
const cssPath = path.join(repoRoot, "landing-page-repo", "auth.css");
const rendererPath = path.join(repoRoot, "landing-page-repo", "dashboard.js");
const planPath = path.join(repoRoot, "docs", "qadam-dashboard-overhaul-master-implementation-plan.md");

const dashboardHtml = fs.readFileSync(htmlPath, "utf8");
const css = fs.readFileSync(cssPath, "utf8");
const renderer = fs.readFileSync(rendererPath, "utf8");
const plan = fs.readFileSync(planPath, "utf8");

function includesAll(text, needles, label) {
    needles.forEach((needle) => {
        assert(text.includes(needle), `${label} missing ${needle}`);
    });
}

function buildModels(snapshot = status) {
    const document = {
        documentElement: { dataset: {} },
        querySelector() {
            return null;
        },
        querySelectorAll() {
            return [];
        }
    };
    const window = { document };
    const context = {
        Array,
        Boolean,
        Date,
        Error,
        Intl,
        Map,
        Math,
        Number,
        Object,
        Promise,
        Set,
        String,
        console,
        document,
        fetch: async () => ({ ok: true, json: async () => snapshot }),
        localStorage: {
            getItem() {
                return null;
            },
            setItem() {}
        },
        sessionStorage: {
            getItem() {
                return null;
            },
            setItem() {}
        },
        window
    };
    window.window = window;
    vm.createContext(context);
    vm.runInContext(renderer, context, { filename: rendererPath });
    return window.buildQadamDashboardViewModels(snapshot, { key: "static_snapshot" });
}

async function main() {
    includesAll(dashboardHtml, [
        "data-overview-first-screen",
        "data-overview-command-surface",
        "data-overview-review-card",
        "data-overview-cockpit-grid",
        "data-overview-system-status",
        "data-overview-paper-capacity",
        "data-overview-proof-flow",
        "data-overview-system-summary",
        "data-overview-status-rail",
        "data-overview-hero",
        "data-overview-metrics",
        "data-overview-lifecycle",
        "data-overview-oversight",
        "data-overview-feed-strip",
        "data-overview-mini-map",
        "data-overview-boundary-rail",
        "data-overview-data-sources",
        "data-overview-trading-strategies",
        "data-overview-thought-feed",
        "data-overview-trade-considerations",
        "data-overview-next-links"
    ], "Overview first-screen HTML");

    includesAll(css, [
        ".overview-first-screen",
        ".overview-command-surface",
        ".overview-review-card",
        ".overview-cockpit-grid",
        ".overview-system-status-panel",
        ".overview-paper-capacity-panel",
        ".overview-proof-flow",
        ".overview-system-summary",
        ".overview-plain-grid",
        ".overview-plain-card-grid",
        ".overview-capacity-line",
        ".overview-status-rail",
        ".overview-readout-list",
        ".overview-lifecycle-strip",
        ".overview-mini-map",
        ".overview-boundary-rail",
        ".overview-next-links",
        "@media (max-width: 900px)"
    ], "Overview first-screen CSS");

    includesAll(renderer, [
        "function renderOverviewFirstScreen",
        "overview.demo_proof",
        "overview.status_chips",
        "overview.review_focus",
        "overview.next_review_links",
        "overview.system_status",
        "overview.data_sources_connected",
        "overview.trading_strategies",
        "overview.thought_feed",
        "overview.trade_considerations",
        "overview.paper_capacity",
        "OVERVIEW_NODE_LABELS",
        "Fund Manager oversight",
        "Use Safety Status for order authority"
    ], "Overview renderer");

    const models = buildModels();
    const overview = models.overview_model;
    assert(overview.id === "overview", "Overview model id mismatch");
    assert(overview.readouts.length === 4, "Overview should expose four primary readouts after D11E");
    assert(overview.status_chips.length === 6, "Overview should expose six compact status chips after D11E");
    assert(overview.demo_proof.required_calendar_day_count === 30, "Overview must expose 30-day demo window");
    assert(overview.demo_proof.weekly_proof_trade_target === 3, "Overview must expose 3 proof trades per week target");
    assert(typeof overview.demo_proof.eligible_setup_count === "number", "Overview must expose eligible setup count");
    assert(overview.lifecycle.length >= 8, "Overview lifecycle strip must expose trade lifecycle states");
    assert(overview.next_review_links.length === 4, "Overview must expose four next-review links after D11B");
    assert(overview.mini_map.source_model === "system_connectivity_model", "Overview mini-map must use shared connectivity model");
    assert(overview.system_status.length === 4, "Overview must expose plain system status");
    assert(overview.data_sources_connected.length >= 3, "Overview must expose source groups on the main page");
    assert(overview.trading_strategies.length >= 5, "Overview must expose the approved strategy families on the main page");
    assert(overview.thought_feed.length >= 4, "Overview must expose Qadam's thought feed on the main page");
    assert(overview.trade_considerations.length >= 2, "Overview must expose trade considerations on the main page");
    assert(overview.paper_capacity.total_gbp === 100000, "Overview must expose the GBP 100,000 paper capacity");
    assert(models.system_connectivity_model.overview_scope.placement === "overview-mini-map", "Mini-map placement mismatch");
    assert(models.system_connectivity_model.feed_clusters.length >= 3, "Overview should expose feed clusters");

    const nextViews = overview.next_review_links.map((link) => link.view_id);
    assert(
        JSON.stringify(nextViews) === JSON.stringify(["trades", "evidence", "reasoning", "operations"]),
        "Overview next-review link order mismatch"
    );

    const rendered = await renderWithStatus(status);
    assertIncludes(rendered, "[data-dashboard-safety-strip]", "Live capital off");
    assertIncludes(rendered, "[data-overview-status-rail]", "Day 0/30");
    assertIncludes(rendered, "[data-overview-status-rail]", "Week 0/5");
    assertIncludes(rendered, "[data-overview-status-rail]", "Potential setups");
    assertIncludes(rendered, "[data-overview-hero]", "Current summary");
    assertIncludes(rendered, "[data-overview-hero]", "Use Safety Status");
    assertIncludes(rendered, "[data-overview-review-card]", "Needs review");
    assertIncludes(rendered, "[data-overview-system-status]", "System status");
    assertIncludes(rendered, "[data-overview-system-status]", "Paper trading");
    assertIncludes(rendered, "[data-overview-paper-capacity]", "Paper capacity");
    assertIncludes(rendered, "[data-overview-paper-capacity]", "£0 of £100,000 deployed");
    assertIncludes(rendered, "[data-overview-paper-capacity]", "data-paper-capacity-line");
    assertIncludes(rendered, "[data-overview-metrics]", "Source health");
    assertIncludes(rendered, "[data-overview-metrics]", "Trade path");
    assertIncludes(rendered, "[data-overview-metrics]", "Proof run");
    assertIncludes(rendered, "[data-overview-lifecycle]", "Observed signals");
    assertIncludes(rendered, "[data-overview-lifecycle]", "Postmortems due");
    assertIncludes(rendered, "[data-overview-oversight]", "You supervise Qadam");
    assertIncludes(rendered, "[data-overview-oversight]", "Qadam Orchestrator");
    assertIncludes(rendered, "[data-overview-mini-map]", "Python script");
    assertIncludes(rendered, "[data-overview-mini-map]", "Local LLM");
    assertIncludes(rendered, "[data-overview-mini-map]", "Frontier LLM");
    assertIncludes(rendered, "[data-overview-mini-map]", "Quantum computer");
    assertIncludes(rendered, "[data-overview-boundary-rail]", "Use Safety Status for order authority");
    assertIncludes(rendered, "[data-overview-boundary-rail]", "A trade idea is not an order");
    assertIncludes(rendered, "[data-overview-data-sources]", "Data sources connected");
    assertIncludes(rendered, "[data-overview-data-sources]", "Markets, broker, and prediction markets");
    assertIncludes(rendered, "[data-overview-trading-strategies]", "Trading strategies");
    assertIncludes(rendered, "[data-overview-trading-strategies]", "Crude Oil Energy Security Disruption");
    assertIncludes(rendered, "[data-overview-thought-feed]", "Qadam's thoughts");
    assertIncludes(rendered, "[data-overview-thought-feed]", "Head of Quant");
    assertIncludes(rendered, "[data-overview-trade-considerations]", "Trades being considered");
    assertIncludes(rendered, "[data-overview-trade-considerations]", "Candidate, not order");
    assertIncludes(rendered, "[data-overview-next-links]", "#trades");
    assertIncludes(rendered, "[data-overview-next-links]", "#operations");

    const overviewText = [
        html(rendered, "[data-overview-status-rail]"),
        html(rendered, "[data-overview-hero]"),
        html(rendered, "[data-overview-metrics]"),
        html(rendered, "[data-overview-review-card]"),
        html(rendered, "[data-overview-system-status]"),
        html(rendered, "[data-overview-paper-capacity]"),
        html(rendered, "[data-overview-lifecycle]"),
        html(rendered, "[data-overview-oversight]"),
        html(rendered, "[data-overview-mini-map]"),
        html(rendered, "[data-overview-boundary-rail]"),
        html(rendered, "[data-overview-data-sources]"),
        html(rendered, "[data-overview-trading-strategies]"),
        html(rendered, "[data-overview-thought-feed]"),
        html(rendered, "[data-overview-trade-considerations]"),
        html(rendered, "[data-overview-next-links]")
    ].join(" ");
    [
        "D0",
        "D1",
        "D5",
        "D7",
        "D9",
        "Q4",
        "Q5",
        "Q5E",
        "Q6",
        "Q7",
        "Phase 4",
        "Phase 5",
        "Phase 6",
        "Phase 7",
        "static snapshot",
        "secure bridge",
        "shadow toggles"
    ].forEach((term) => {
        assert(!overviewText.includes(term), `Overview first screen contains disallowed primary term: ${term}`);
    });

    [
        "DX-5 - Overview First Screen",
        "Build the Overview from the `overview_model`",
        "Add a compact lifecycle strip",
        "Add the compact system mini-map"
    ].forEach((needle) => {
        assert(plan.includes(needle), `master plan missing DX-5 marker: ${needle}`);
    });

    console.log("dashboard_overhaul_overview=ok");
    console.log("dashboard_overview_first_screen_enabled=True");
    console.log("dashboard_overview_uses_view_model=True");
    console.log("dashboard_overview_demo_day_count=30");
    console.log("dashboard_overview_weekly_proof_trade_target=3");
    console.log("dashboard_overview_next_review_links=4");
    console.log("dashboard_overview_mini_map_shared_model=True");
    console.log("dashboard_authority_unchanged=True");
}

if (require.main === module) {
    main().catch((error) => {
        console.error(error.message);
        process.exitCode = 1;
    });
}
