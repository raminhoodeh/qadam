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
const auditPath = path.join(repoRoot, "docs", "qadam-dashboard-d11e-rebuild-overview-2026-05-26.md");

const dashboardHtml = fs.readFileSync(htmlPath, "utf8");
const css = fs.readFileSync(cssPath, "utf8");
const renderer = fs.readFileSync(rendererPath, "utf8");
const plan = fs.readFileSync(planPath, "utf8");

function includesAll(text, needles, label) {
    needles.forEach((needle) => {
        assert(text.includes(needle), `${label} missing ${needle}`);
    });
}

function excludesAll(text, needles, label) {
    needles.forEach((needle) => {
        assert(!text.includes(needle), `${label} still includes ${needle}`);
    });
}

function countOccurrences(text, needle) {
    return text.split(needle).length - 1;
}

function loadRendererWindow() {
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
        fetch: async () => ({ ok: true, json: async () => status }),
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
    return window;
}

async function main() {
    includesAll(dashboardHtml, [
        "data-overview-mission-brief",
        "data-overview-strategy-narrative",
        "data-overview-cockpit-grid",
        "data-overview-system-status",
        "data-overview-paper-capacity",
        "data-overview-system-summary",
        "data-overview-mini-map",
        "data-overview-data-sources",
        "data-overview-trading-strategies",
        "data-overview-thought-feed",
        "data-overview-trade-considerations",
        "20260607-cc8-prune-docs"
    ], "D11E overview HTML");

    excludesAll(dashboardHtml, [
        "overview-snapshot-grid",
        "overview-metric-grid",
        "overview-status-card",
        "Checking live-capital state"
    ], "D11E overview HTML");

    includesAll(css, [
        ".overview-mission-brief",
        ".overview-strategy-narrative",
        ".overview-cockpit-grid",
        ".overview-system-status-panel",
        ".overview-paper-capacity-panel",
        ".overview-system-summary",
        ".overview-plain-grid",
        ".overview-plain-card",
        ".overview-capacity-line",
        ".overview-expandable-ledger",
        ".overview-system-grid"
    ], "D11E overview CSS");

    excludesAll(css, [
        ".overview-snapshot-grid",
        ".overview-metric-grid",
        ".overview-status-card"
    ], "D11E overview CSS");

    includesAll(renderer, [
        "founder_contract_model",
        "renderContractTeamMap",
        "renderContractStrategyNarrative",
        "renderContractStrategyBlock",
        "renderContractPortfolioBlock",
        "renderContractTradeBoard",
        "renderContractThinkingBlock",
        "function renderOverviewCapacityChart",
        "overview-source-ledger",
        "data-cc5-contract-source"
    ], "D11E overview renderer");

    const window = loadRendererWindow();
    assert(typeof window.buildQadamDashboardViewModels === "function", "view-model builder missing");
    const models = window.buildQadamDashboardViewModels(status, { key: "live_bridge" });
    const overview = models.overview_model;
    const contract = models.founder_contract_model;
    assert(contract.source === "mission_control", "D11E successor must expose founder contract");
    assert(contract.team.length >= 6, "Founder contract should expose operating team");
    assert(contract.sources.ledger.length >= 20, "Founder contract should expose source ledger");
    assert(contract.portfolio.equity_curve.length >= 1, "Founder contract should expose portfolio line");
    assert(contract.trades.board.length >= 1, "Founder contract should expose trade board");
    assert(contract.thinking.research_goal_active_count >= 1, "Founder contract should expose research goals");
    assert(overview.mission_brief.question_count === 7, "Overview must expose the seven-question Mission Control brief");
    assert(overview.mission_brief.authority.live_capital_enabled === false, "Overview Mission Brief must keep live capital disabled");
    assert(overview.mission_brief.authority.dashboard_write_authority === false, "Overview Mission Brief must be read-only");
    assert(!overview.summary.toLowerCase().includes("live capital"), "Overview summary must not duplicate live-capital safety copy");
    assert(overview.system_status.length >= 6, "Overview should expose paper system status and runner cards");
    assert(overview.data_sources_connected.length >= 3, "Overview should expose connected source groups");
    assert(overview.trading_strategies.length >= 5, "Overview should expose approved trading strategy families");
    assert(overview.thought_feed.length >= 4, "Overview should expose Qadam thought feed");
    assert(overview.trade_considerations.length >= 2, "Overview should expose observed/candidate trade considerations");
    assert(overview.paper_capacity.total_gbp === 100000, "Overview should expose GBP 100,000 paper capacity");

    const rendered = await renderWithStatus(status);
    const missionBrief = html(rendered, "[data-overview-mission-brief]");
    const strategyNarrative = html(rendered, "[data-overview-strategy-narrative]");
    const systemStatus = html(rendered, "[data-overview-system-status]");
    const paperCapacity = html(rendered, "[data-overview-paper-capacity]");
    const dataSources = html(rendered, "[data-overview-data-sources]");
    const strategies = html(rendered, "[data-overview-trading-strategies]");
    const thoughtFeed = html(rendered, "[data-overview-thought-feed]");
    const tradeConsiderations = html(rendered, "[data-overview-trade-considerations]");
    const system = [
        html(rendered, "[data-overview-oversight]"),
        html(rendered, "[data-overview-mini-map]"),
        html(rendered, "[data-overview-feed-strip]"),
        html(rendered, "[data-overview-boundary-rail]")
    ].join(" ");

    includesAll(missionBrief, [
        "Mission Control brief",
        "mission_control",
        "Authority state",
        "Paper-only, read-only"
    ], "rendered D11E Mission Control brief");

    includesAll(strategyNarrative, [
        "Second-order AI infrastructure beneficiary lens",
        "Akber",
        "Worldview role"
    ], "rendered D11E strategy narrative");

    includesAll(systemStatus, [
        "System status",
        "Plain-language mission state",
        "Data sources",
        "Trade lifecycle"
    ], "rendered D11E system status");

    includesAll(paperCapacity, [
        "Paper portfolio",
        "mirror",
        "data-paper-capacity-line",
        "Realized",
        "Unrealized"
    ], "rendered D11E paper capacity");

    includesAll(dataSources, [
        "Data sources connected",
        "mission_control",
        "ACLED API"
    ], "rendered D11E data sources");

    includesAll(strategies, [
        "Trading strategy",
        "Akber filter",
        "Signal Integrity Gate"
    ], "rendered D11E trading strategies");

    includesAll(thoughtFeed, [
        "Qadam's thoughts",
        "Research goals",
        "Worldview prior"
    ], "rendered D11E thought feed");

    includesAll(tradeConsiderations, [
        "Trades being considered",
        "observed",
        "candidate",
        "USO options watch"
    ], "rendered D11E trade considerations");

    includesAll(system, [
        "You supervise Qadam",
        "Chief Operating Officer",
        "Local LLM",
        "Frontier LLM",
        "Head of Quant",
        "A trade idea is not an order"
    ], "rendered D11E compact system map");

    assert(fs.existsSync(auditPath), "D11E audit document missing");
    includesAll(plan, [
        "D11E - Rebuild Overview",
        "D11F - Trades View Consolidation"
    ], "D11E master plan");

    console.log("dashboard_d11e_rebuild_overview=ok");
    console.log("dashboard_overview_cc2_consolidated=True");
    console.log("dashboard_overview_mission_question_count=7");
    console.log("dashboard_overview_duplicate_safety_copy_removed=True");
    console.log("dashboard_authority_unchanged=True");
}

if (require.main === module) {
    main().catch((error) => {
        console.error(error.message);
        process.exitCode = 1;
    });
}
