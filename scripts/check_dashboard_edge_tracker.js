#!/usr/bin/env node

const fs = require("node:fs");
const path = require("node:path");

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

const dashboardHtml = fs.readFileSync(htmlPath, "utf8");
const css = fs.readFileSync(cssPath, "utf8");
const renderer = fs.readFileSync(rendererPath, "utf8");

async function main() {
    assert(dashboardHtml.includes("data-overview-edge-tracker"), "Overview HTML missing edge tracker mount");
    assert(css.includes(".overview-edge-tracker"), "CSS missing edge tracker shell");
    assert(css.includes(".edge-sleeve-grid"), "CSS missing edge sleeve grid");
    assert(renderer.includes("function buildEdgeTrackerModel"), "Renderer missing edge tracker model");
    assert(renderer.includes("function renderOverviewEdgeTracker"), "Renderer missing edge tracker renderer");

    const edge = status.edge_tracker || {};
    assert(edge.status === "tracking", "Status JSON missing active edge tracker");
    assert(edge.sleeve_count === 5, "Edge tracker must expose five sleeves");
    assert(edge.weekly_thesis?.cadence === "weekly", "Edge tracker must expose weekly thesis cadence");
    assert(edge.quantum_pattern_review?.role?.includes("non-linear"), "Edge tracker must explain quantum non-linear review");
    assert(edge.paper_order_allowed === false, "Edge tracker must not allow paper orders");
    assert(edge.broker_write_allowed === false, "Edge tracker must not allow broker writes");
    assert(edge.live_capital_enabled === false, "Edge tracker must not enable live capital");

    const symbols = new Set(edge.market_price_watch?.symbols || []);
    [
        "CL=F",
        "BZ=F",
        "USO",
        "XLE",
        "SI=F",
        "SLV",
        "SMH",
        "SOXX",
        "NVDA",
        "AMD",
        "Polymarket CLOB",
        "Kalshi events",
        "ITA",
        "XAR",
        "LMT",
        "RTX",
        "NOC"
    ].forEach((symbol) => {
        assert(symbols.has(symbol), `Edge tracker missing watched symbol ${symbol}`);
    });

    const rendered = await renderWithStatus(status);
    assertIncludes(rendered, "[data-overview-edge-tracker]", "Edge Tracker");
    assertIncludes(rendered, "[data-overview-edge-tracker]", "Current weekly thesis");
    assertIncludes(rendered, "[data-overview-edge-tracker]", "Non-linear check");
    assertIncludes(rendered, "[data-overview-edge-tracker]", "Oil");
    assertIncludes(rendered, "[data-overview-edge-tracker]", "Silver");
    assertIncludes(rendered, "[data-overview-edge-tracker]", "Semiconductors");
    assertIncludes(rendered, "[data-overview-edge-tracker]", "Prediction markets");
    assertIncludes(rendered, "[data-overview-edge-tracker]", "Defence stocks");
    assertIncludes(rendered, "[data-overview-edge-tracker]", "CL=F");
    assertIncludes(rendered, "[data-overview-edge-tracker]", "SLV");
    assertIncludes(rendered, "[data-overview-edge-tracker]", "SMH");
    assertIncludes(rendered, "[data-overview-edge-tracker]", "LMT");

    const trackerHtml = html(rendered, "[data-overview-edge-tracker]");
    assert(!trackerHtml.includes("order authority</em>") || trackerHtml.includes("0 order authority"), "Rendered edge tracker must keep order authority at zero");

    console.log("Dashboard edge tracker contract OK");
}

main().catch((error) => {
    console.error(error.message);
    process.exitCode = 1;
});
