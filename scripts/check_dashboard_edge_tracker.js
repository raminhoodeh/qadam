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
    assert(renderer.includes("function renderEdgeSourceUniverseLedger"), "Renderer missing shared source universe ledger");

    const edge = status.edge_tracker || {};
    assert(edge.status === "tracking", "Status JSON missing active edge tracker");
    assert(edge.sleeve_count === 5, "Edge tracker must expose five sleeves");
    assert(edge.source_scan?.mode === "all_sources_every_sleeve", "Edge tracker must scan all sources for every sleeve");
    assert(edge.source_universe?.source_count === edge.source_scan?.total_source_count, "Source universe count must match source scan");
    assert(edge.weekly_thesis?.cadence === "weekly", "Edge tracker must expose weekly thesis cadence");
    assert(edge.quantum_pattern_review?.role?.includes("non-linear"), "Edge tracker must explain quantum non-linear review");
    assert(edge.paper_order_allowed === false, "Edge tracker must not allow paper orders");
    assert(edge.broker_write_allowed === false, "Edge tracker must not allow broker writes");
    assert(edge.live_capital_enabled === false, "Edge tracker must not enable live capital");
    const ledger = status.edge_pattern_ledger || {};
    assert(ledger.status, "Status JSON missing edge pattern ledger");
    assert(ledger.sprint?.length_days === 30, "Edge pattern ledger must define a 30-day hunt");
    assert(ledger.quantum_review?.core_gate === true, "Edge pattern ledger must make quantum a core gate");
    assert(ledger.quantum_review?.required_before_validated_edge === true, "Quantum review must be required before a validated edge");
    assert(ledger.candidate_pattern_count === 5, "Edge pattern ledger must expose five candidate pattern records");
    assert(Array.isArray(ledger.criteria) && ledger.criteria.length === 8, "Edge pattern ledger must expose eight edge criteria");
    assert(ledger.criteria.some((criterion) => criterion.key === "quantum_nonlinear_review"), "Edge pattern ledger missing quantum criterion");
    assert(ledger.telegram_summary?.telegram_command_path_enabled === false, "Telegram edge summary must not enable commands");
    assert(ledger.telegram_summary?.telegram_live_send_allowed === false, "Telegram edge summary must not send live by default");
    assert(ledger.patterns.every((pattern) => pattern.quantum_required === true), "Every candidate pattern must require quantum review");
    assert(ledger.patterns.every((pattern) => pattern.paper_order_allowed === false), "Candidate patterns must not create paper order authority");

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
    const allSourceKeys = new Set(edge.source_scan?.all_source_keys || []);
    assert(allSourceKeys.size >= 30, "Edge tracker source universe is unexpectedly small");
    (edge.sleeves || []).forEach((sleeve) => {
        assert(sleeve.source_application === "all_qadam_sources_cross_scanned_for_this_sleeve", `Sleeve ${sleeve.key} does not use the all-source scan contract`);
        assert(sleeve.source_count === allSourceKeys.size, `Sleeve ${sleeve.key} source count does not match full universe`);
        assert((sleeve.source_keys || []).length === allSourceKeys.size, `Sleeve ${sleeve.key} source key list does not match full universe`);
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
    assertIncludes(rendered, "[data-overview-edge-tracker]", "all sources every sleeve");
    assertIncludes(rendered, "[data-overview-edge-tracker]", "Shared source universe");
    assertIncludes(rendered, "[data-overview-edge-tracker]", "sources cross-scanned");
    assertIncludes(rendered, "[data-overview-edge-tracker]", "How Qadam knows it found an edge");
    assertIncludes(rendered, "[data-overview-edge-tracker]", "Quantum core gate");
    assertIncludes(rendered, "[data-overview-edge-tracker]", "Telegram documentation");
    assertIncludes(rendered, "[data-overview-edge-tracker]", "Candidate pattern records");
    assertIncludes(rendered, "[data-overview-edge-tracker]", "30-day edge hunt");
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
