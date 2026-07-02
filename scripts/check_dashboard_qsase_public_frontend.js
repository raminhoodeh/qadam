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
        "data-qsase-section=\"source_intelligence_network\"",
        "data-qsase-section=\"trading_strategy_universe\"",
        "data-qsase-section=\"pattern_opportunity_lab\"",
        "data-qsase-section=\"trade_intents\"",
        "data-qsase-section=\"router_paperops_gate\"",
        "Portfolio Value &amp; Return",
        "Current Portfolio",
        "Trading History",
        "Source Intelligence Network",
        "Trading Strategy Universe",
        "Pattern & Opportunity Lab",
        "Trade Intents / What Qadam Is Thinking",
        "Router & PaperOps Gate",
        "trade markers are read-only history, not proof credit",
        "No order authority",
        "qsase-detail-ledger",
        "qsase-jump-row"
    ], "QSASE renderer");

    assertIncludesAll(css, [
        ".qsase-dashboard-shell",
        ".qsase-dashboard-hero",
        ".qsase-portfolio-chart",
        ".qsase-card-grid",
        ".qsase-table",
        ".qsase-category-grid",
        ".qsase-final-decision",
        ".qsase-dashboard-v2",
        ".qsase-jump-row",
        ".qsase-detail-ledger"
    ], "QSASE stylesheet");

    assertIncludesAll(dashboardHtml, [
        "/auth.css?v=20260702-public-fund-v2",
        "/dashboard.js?v=20260702-public-fund-v2",
        "data-stage7-dashboard-visibility"
    ], "dashboard shell");

    assertIncludesAll(cockpitStatus, [
        "QSASE_DASHBOARD_PUBLIC_ARTIFACTS",
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
        "Public paper fund dashboard",
        "Portfolio Value &amp; Return",
        "Current Portfolio",
        "Trading History",
        "Source Intelligence Network",
        "Trading Strategy Universe",
        "Pattern &amp; Opportunity Lab",
        "Trade Intents / What Qadam Is Thinking",
        "Router &amp; PaperOps Gate"
    ].forEach((needle) => assertIncludes(rendered, "[data-stage7-dashboard-visibility]", needle));

    [
        "portfolio_value_return",
        "current_portfolio",
        "trading_history",
        "source_intelligence_network",
        "trading_strategy_universe",
        "pattern_opportunity_lab",
        "trade_intents",
        "router_paperops_gate"
    ].forEach((section) => {
        assert(stageHtml.includes(`data-qsase-section="${section}"`), `rendered QSASE dashboard missing section ${section}`);
    });

    const order = [
        "Portfolio Value &amp; Return",
        "Current Portfolio",
        "Trading History",
        "Source Intelligence Network",
        "Trading Strategy Universe",
        "Pattern &amp; Opportunity Lab",
        "Trade Intents / What Qadam Is Thinking",
        "Router &amp; PaperOps Gate"
    ].map((label) => stageHtml.indexOf(label));
    assert(order.every((index) => index >= 0), "rendered QSASE dashboard missing required labels");
    assert(order.every((index, position) => position === 0 || index > order[position - 1]), "rendered QSASE dashboard order is not money-first");

    [
        "live-capital authority",
        "paper proof ledger credit",
        "trade markers are read-only history"
    ].forEach((needle) => {
        assert(stageHtml.toLowerCase().includes(needle.toLowerCase()), `rendered QSASE dashboard missing boundary wording ${needle}`);
    });

    [
        "data-cc6-real-portfolio-timeline",
        "Mission Control walkthrough"
    ].forEach((needle) => {
        assert(!stageHtml.includes(needle), `QSASE dashboard should not render old overview element ${needle}`);
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
