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
const rendererPath = path.join(repoRoot, "landing-page-repo", "dashboard.js");
const cssPath = path.join(repoRoot, "landing-page-repo", "auth.css");
const dashboardHtmlPath = path.join(repoRoot, "landing-page-repo", "dashboard", "index.html");
const cockpitPath = path.join(repoRoot, "orchestrator", "cockpit_status.py");
const runtimeDir = path.join(repoRoot, "data", "runtime");

const renderer = fs.readFileSync(rendererPath, "utf8");
const css = fs.readFileSync(cssPath, "utf8");
const dashboardHtml = fs.readFileSync(dashboardHtmlPath, "utf8");
const cockpitStatus = fs.readFileSync(cockpitPath, "utf8");

const artifactMap = {
    status: "qsase_dashboard_status.json",
    portfolio_value: "qsase_dashboard_portfolio_value_series.json",
    current_portfolio: "qsase_dashboard_current_portfolio.json",
    trading_history: "qsase_dashboard_trading_history.json",
    source_network: "qsase_dashboard_source_network.json",
    strategy_universe: "qsase_dashboard_strategy_universe.json",
    pattern_lab: "qsase_dashboard_pattern_lab.json",
    trade_intents: "qsase_dashboard_trade_intents.json",
    pattern_to_paper_workflow: "qsase_pattern_to_paper_workflow.json",
    pattern_intelligence: "qsase_pattern_intelligence.json",
    learning_ledger: "qsase_dashboard_learning_ledger.json",
    repair_queue: "qsase_dashboard_repair_queue.json",
    router: "qsase_strategy_router_decisions.json",
    paperops_gate: "qsase_paperops_gate_interface.json"
};

function readJson(filename) {
    const artifactPath = path.join(runtimeDir, filename);
    assert(fs.existsSync(artifactPath), `missing QSASE runtime artifact ${filename}`);
    return JSON.parse(fs.readFileSync(artifactPath, "utf8"));
}

function clone(value) {
    return JSON.parse(JSON.stringify(value));
}

function assertIncludesAll(text, needles, label) {
    needles.forEach((needle) => assert(text.includes(needle), `${label} missing ${needle}`));
}

function buildQsaseFixture() {
    const artifactStatus = readJson(artifactMap.status);
    const sections = Object.fromEntries(
        Object.entries(artifactMap)
            .filter(([key]) => key !== "status")
            .map(([key, filename]) => [key, readJson(filename)])
    );

    return {
        ...artifactStatus,
        schema_version: "qsase_public_dashboard.v1",
        status: artifactStatus.status || "qsase_dashboard_visibility_ready",
        public_safe: true,
        read_only: true,
        sections,
        boundary: "Public dashboard visibility only. QSASE cannot create orders, approvals, broker writes, Telegram commands, live-capital authority, or paper proof ledger credit.",
        authority_flags: {
            creates_trade_candidates: false,
            creates_paper_orders: false,
            grants_proof_credit: false,
            enables_live_capital: false,
            sends_broker_writes: false,
            telegram_command_path_enabled: false
        }
    };
}

function assertStaticContract() {
    assertIncludesAll(renderer, [
        "function buildQsaseDashboardModel(status = {})",
        "status.qsase_dashboard",
        "qsase_dashboard_model",
        "function renderQsaseDashboardVisibility(qsase = {})",
        "data-qsase-dashboard-rendered",
        "data-qsase-dashboard-contract=\"qsase_public_dashboard_v2\"",
        "data-qsase-section=\"portfolio_value_return\"",
        "data-qsase-section=\"current_portfolio\"",
        "data-qsase-section=\"trading_history\"",
        "data-qsase-section=\"hedge_fund_team\"",
        "data-qsase-section=\"source_intelligence_network\"",
        "data-qsase-section=\"trading_universe\"",
        "data-qsase-section=\"trading_strategy_universe\"",
        "data-qsase-section=\"pattern_intelligence_findings\"",
        "data-qsase-section=\"trade_intents\"",
        "data-qsase-section=\"router_paperops_gate\"",
        "data-qsase-section=\"pulse_terminal\"",
        "data-qsase-section=\"paper_fund_status\"",
        "Paper Fund Status",
        "Portfolio Value &amp; Return",
        "Current Portfolio",
        "Portfolio status",
        "Open exposure",
        "Trading History",
        "Hedge Fund Team",
        "Qadam Team Overview",
        "Python script [COO]",
        "local LLM [Research Analyst]",
        "frontier LLM [Strategy Lead]",
        "quantum computer [Head of Quant]",
        "Source Intelligence Network",
        "Multi-Asset Funds",
        "Trading Universe",
        "QSASE_INSTRUMENT_FULL_NAMES",
        "qsaseInstrumentTooltip",
        "qsase-trading-universe-card",
        "qsase-instrument-chip",
        "qsase-universe-key",
        "Self-Refining Multi-Strategy Approach",
        "Core Trading Strategies",
        "Pattern Recognition Findings",
        "Trade Intents / What Qadam Is Thinking",
        "Final Paper-Trade Gate",
        "Qadam Pulse Terminal",
        "How to read portfolio status",
        "Most actionable pattern",
        "data-tooltip-contract=\"nontechnical-guide\"",
        "data-guide-marker=",
        "pulse_terminal",
        "Python COO",
        "Local LLM",
        "Frontier LLM",
        "Head of Quant",
        "QADAM HEARTBEAT",
        "matrix-rain",
        "qsase-terminal-line",
        "current_portfolio",
        "pattern_intelligence_findings",
        "No order authority",
        "qsase-detail-ledger",
        "qsase-fund-status",
        "qsase-fund-context",
        "qsase-kpi-row",
        "qsase-final-gate-summary",
        "qsase-trading-timeline",
        "qsase-source-category-row",
        "qsase-market-pill-row",
        "pointTimeMs",
        "xForPoint",
        "timeTicks",
        "data-time-scaled-axis=",
        "data-qsase-time-axis",
        "chart-axis-time"
    ], "QSASE renderer");
    [
        "qsase-jump-row",
        "Money first. Decisions last.",
        "Portfolio value</a>",
        "Holdings</a>",
        "Pattern workflow</a>",
        "PaperOps gate</a>"
    ].forEach((needle) => {
        assert(!renderer.includes(needle), `QSASE renderer still contains removed navigation/copy ${needle}`);
    });

    assertIncludesAll(css, [
        ".qsase-dashboard-shell",
        ".qsase-dashboard-hero",
        ".qsase-portfolio-chart",
        ".qsase-card-grid",
        ".qsase-table",
        ".qsase-source-category-list",
        ".qsase-source-category-row",
        ".qsase-trading-timeline",
        ".qsase-trade-event",
        ".qsase-kpi-row",
        ".qsase-fund-status",
        ".qsase-fund-context",
        ".qsase-market-pill-row",
        ".qsase-final-decision",
        ".qsase-guide-marker",
        ".qsase-guide-card",
        ".qsase-callout-head",
        ".qsase-dashboard-v2 .qsase-dashboard-hero .qsase-callout-head",
        ".qsase-final-gate-summary",
        ".chart-time-tick",
        ".chart-axis-time",
        "grid-template-columns: minmax(8rem, 0.42fr) minmax(14rem, 1fr);",
        "data-guide-tooltip-bound=\"true\"",
        "--qadam-tooltip-left",
        "--qadam-tooltip-top",
        "position: fixed;",
        "max-height: min(72vh, 32rem);",
        ".qsase-workflow-message",
        ".qsase-dashboard-v2",
        ".qsase-detail-ledger",
        ".qsase-pulse-terminal",
        ".qsase-terminal-frame",
        ".matrix-rain",
        ".qsase-terminal-line",
        "grid-template-columns: minmax(0, 1fr);",
        "max-width: 100%;",
        "@keyframes qadamMatrixFall"
    ], "QSASE stylesheet");
    assert(
        !css.includes("grid-template-columns: minmax(0, 1fr) minmax(18rem, 0.68fr);"),
        "QSASE hero stylesheet still contains the removed two-column dashboard hero layout"
    );
    assert(!css.includes(".qsase-jump-row"), "QSASE stylesheet still styles removed jump row");

    assertIncludesAll(renderer, [
        "function positionDashboardGuideTooltip(marker)",
        "function initDashboardGuideTooltips()",
        "clampDashboardTooltipValue",
        "data-tooltip-contract=\"nontechnical-guide\"",
        "initDashboardGuideTooltips();"
    ], "QSASE tooltip positioning controller");

    assertIncludesAll(dashboardHtml, [
        "/auth.css?v=20260706-time-axis-v1",
        "/dashboard.js?v=20260706-time-axis-v1",
        "data-stage7-dashboard-visibility"
    ], "dashboard shell");
    [
        "Qadam Mission Control",
        "Paper trading mode",
        "Paper-only monitoring",
        "data-dashboard-debug-toggle",
        "data-dashboard-view-link"
    ].forEach((needle) => {
        assert(!dashboardHtml.includes(needle), `dashboard shell still contains removed chrome ${needle}`);
    });

    assertIncludesAll(cockpitStatus, [
        "QSASE_DASHBOARD_PUBLIC_ARTIFACTS",
        "\"pattern_to_paper_workflow\": \"qsase_pattern_to_paper_workflow.json\"",
        "\"pattern_intelligence\": \"qsase_pattern_intelligence.json\"",
        "def _qsase_dashboard_public_status",
        "\"qsase_dashboard\": _qsase_dashboard_public_status(settings)",
        "\"creates_paper_orders\": False",
        "\"enables_live_capital\": False",
        "\"telegram_command_path_enabled\": False"
    ], "cockpit status QSASE export");
}

async function assertRenderedContract() {
    const fixtureStatus = clone(status);
    fixtureStatus.qsase_dashboard = buildQsaseFixture();
    const rendered = await renderWithStatus(fixtureStatus);
    const stageHtml = html(rendered, "[data-stage7-dashboard-visibility]");

    [
        "Qadam Paper Fund",
        "Paper Fund Status",
        "Portfolio Value &amp; Return",
        "Portfolio status",
        "Open exposure",
        "Trading History",
        "Hedge Fund Team",
        "Source Intelligence Network",
        "Multi-Asset Funds",
        "Trading Universe",
        "19 Instruments over 6 Fund Categories",
        "United States Oil Fund",
        "Lockheed Martin Corporation",
        "Kalshi event contracts",
        "Self-Refining Multi-Strategy Approach",
        "Core Trading Strategies",
        "Pattern Recognition Findings",
        "Trade Intents / What Qadam Is Thinking",
        "Final Paper-Trade Gate",
        "Qadam Pulse Terminal",
        "data-time-scaled-axis=\"true\"",
        "data-qsase-time-axis",
        "chart-axis-time"
    ].forEach((needle) => assertIncludes(rendered, "[data-stage7-dashboard-visibility]", needle));

    [
        "paper_fund_status",
        "portfolio_value_return",
        "trading_history",
        "hedge_fund_team",
        "source_intelligence_network",
        "trading_universe",
        "trading_strategy_universe",
        "pattern_intelligence_findings",
        "trade_intents",
        "router_paperops_gate",
        "pulse_terminal"
    ].forEach((section) => {
        assert(stageHtml.includes(`data-qsase-section="${section}"`), `rendered QSASE dashboard missing section ${section}`);
    });

    const order = [
        "paper_fund_status",
        "portfolio_value_return",
        "trading_history",
        "hedge_fund_team",
        "source_intelligence_network",
        "trading_universe",
        "trading_strategy_universe",
        "pattern_intelligence_findings",
        "trade_intents",
        "router_paperops_gate",
        "pulse_terminal"
    ].map((section) => stageHtml.indexOf(`data-qsase-section="${section}"`));
    assert(order.every((index) => index >= 0), "rendered QSASE dashboard missing required labels");
    assert(order.every((index, position) => position === 0 || index > order[position - 1]), "rendered QSASE dashboard order is not money-first");

    [
        "live-capital authority",
        "paper proof ledger credit"
    ].forEach((needle) => {
        assert(stageHtml.toLowerCase().includes(needle.toLowerCase()), `rendered QSASE dashboard missing boundary wording ${needle}`);
    });

    [
        "data-cc6-real-portfolio-timeline",
        "Mission Control walkthrough",
        "qsase-jump-row",
        "Money first. Decisions last.",
        "Paper trading mode",
        "Paper-only monitoring",
        "Connected Data Sources",
        "Watched Trading Universe",
        "19 watched instruments · 6 categories · 19 paper-route candidates",
        "source network visible",
        "dashboard portfolio consistent",
        "portfolio values match",
        "Snapshot fresh (age unknown)",
        "trade markers are read-only history, not proof credit"
    ].forEach((needle) => {
        assert(!stageHtml.includes(needle), `QSASE dashboard should not render old overview element ${needle}`);
    });

    [
        "qsase-kpi-row",
        "qsase-fund-status",
        "qsase-final-gate-summary",
        "Final gate",
        "Current gate:",
        "qsase-trading-timeline",
        "qsase-trading-summary",
        "Recent trading summary",
        "No accepted paper orders look stale",
        "qsase-source-category-row",
        "qsase-trading-universe-card",
        "qsase-instrument-chip-cloud",
        "qsase-instrument-chip",
        "qsase-universe-key",
        "Paper proxy",
        "Research only",
        "Context only",
        "Held",
        "WTI crude oil futures continuous contract",
        "NVIDIA Corporation",
        "qsase-market-pill-row",
        "qsase-pattern-brief",
        "qsase-pattern-flow",
        "Qadam's current read",
        "Paper Fund Status",
        "Most actionable pattern",
        "data-tooltip-contract=\"nontechnical-guide\"",
        "data-guide-marker=\"pattern_intelligence_findings\"",
        "How to read pattern recognition",
        "Guide: How to read pattern recognition",
        "What a trade intent means",
        "How to read the pulse terminal",
        "QADAM HEARTBEAT",
        "Python script",
        "COO",
        "Research Analyst",
        "Local LLM",
        "Strategy Lead",
        "Frontier LLM",
        "Head of Quant",
        "Quantum computer",
        "Expand details",
        "Plain-English role",
        "Where it fits in Qadam",
        "Current snapshot",
        "Decision boundary",
        "fallback review path",
        "Public thought stream refreshes with the dashboard status file",
        "What blocks the trade",
        "Technical evidence ledger",
        "These sources can inform hypotheses, but none of them can place trades."
    ].forEach((needle) => {
        assert(stageHtml.includes(needle), `rendered QSASE dashboard missing redesigned UX element ${needle}`);
    });

    [
        "Router &amp; PaperOps Gate",
        "guarded PaperOps decision state",
        "Nothing is currently being considered by QSASE",
        "No filled holdings yet",
        "0 filled holdings",
        "Current Holdings",
        "qsase-fund-detail",
        "proof-eligible",
        "Lifecycle audit:",
        "Paper proof ledger:",
        "stale accepted order mirrors need review",
        "Hybrid boutique macro desk: Python COO, local analyst, frontier strategist, Head of Quant",
        "Self-awareness",
        "Mode: deterministic classical shadow",
        "State: consultation recorded",
        "Qadam can analyse this market sleeve, but each instrument still needs evidence, risk, and PaperOps gates before paper execution.",
        "alpaca paper proxy available guarded route only",
        "research only proxy not direct alpaca paperable",
        "context only until governed prediction market paper route"
    ].forEach((needle) => {
        assert(!stageHtml.includes(needle), `rendered QSASE dashboard still exposes internal copy ${needle}`);
    });
}

async function main() {
    assertStaticContract();
    await assertRenderedContract();
    console.log("dashboard_qsase_public_frontend=ok");
}

if (require.main === module) {
    main().catch((error) => {
        console.error(error.message);
        process.exitCode = 1;
    });
}
