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
        "data-overview-strategy-universe",
        "data-overview-paper-trade-state",
        "data-overview-control-plane",
        "data-overview-source-summary",
        "20260607-cc11-final-dashboard-structure"
    ], "D11E overview HTML");

    excludesAll(dashboardHtml, [
        "overview-snapshot-grid",
        "overview-metric-grid",
        "overview-status-card",
        "Checking live-capital state"
    ], "D11E overview HTML");

    includesAll(css, [
        ".overview-mission-brief",
        ".overview-mission-snapshot-grid",
        ".overview-strategy-narrative",
        ".overview-paper-trade-state-panel",
        ".paper-trade-state-grid",
        ".overview-control-plane",
        ".control-plane-grid",
        ".overview-source-summary-panel",
        ".overview-ledger-routing",
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
        "renderContractControlPlane",
        "renderContractStrategyUniverse",
        "renderContractStrategyNarrative",
        "renderContractStrategyBlock",
        "renderContractPortfolioBlock",
        "renderContractTradeStateSummary",
        "renderContractPaperTradeState",
        "renderContractSourceSummary",
        "renderOverviewDecisionRecords",
        "function renderOverviewCapacityChart",
        "detail_ledger_placement",
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
    assert(overview.mission_brief.question_count === 7, "Overview must expose the seven-question Founder brief");
    assert(overview.mission_brief.authority.live_capital_enabled === false, "Overview Mission Brief must keep live capital disabled");
    assert(overview.mission_brief.authority.dashboard_write_authority === false, "Overview Mission Brief must be read-only");
    assert(!overview.summary.toLowerCase().includes("live capital"), "Overview summary must not duplicate live-capital safety copy");
    assert(overview.system_status.length >= 6, "Overview should expose paper system status and runner cards");
    assert(overview.source_summary.detail_view === "evidence", "Overview should route source detail to Evidence");
    assert(overview.trading_strategies.length >= 5, "Overview should expose approved trading strategy families");
    assert(overview.reasoning_summary.detail_view === "reasoning", "Overview should route reasoning detail to Reasoning");
    assert(overview.trade_state_summary.detail_view === "trades", "Overview should route trade detail to Trades");
    assert(overview.detail_ledger_placement.overview_scope === "summary_only", "Overview should keep detailed ledgers out of the first screen");
    assert(overview.paper_capacity.total_gbp === 100000, "Overview should expose GBP 100,000 paper capacity");

    const rendered = await renderWithStatus(status);
    const missionBrief = html(rendered, "[data-overview-mission-brief]");
    const strategyNarrative = html(rendered, "[data-overview-strategy-narrative]");
    const paperTradeState = html(rendered, "[data-overview-paper-trade-state]");
    const sourceSummary = html(rendered, "[data-overview-source-summary]");
    const controlPlane = html(rendered, "[data-overview-control-plane]");

    includesAll(missionBrief, [
        "Mission Snapshot",
        "Default to Mission Snapshot",
        "data-overview-decision-records",
        "Durable replay",
        "Data sources",
        "Trade lifecycle",
        "Safety boundary",
        "Paper-only, read-only"
    ], "rendered D11E Mission Snapshot");

    includesAll(strategyNarrative, [
        "Strategy Universe",
        "Use Strategy Universe for strategy posture",
        "Asymmetric Catalyst Proxy Trading",
        "Universe",
        "Currently qualified",
        "Waiting on gates",
        "Second-order AI infrastructure beneficiary lens",
        "Boundary",
        "Strategy family ledger",
        "Open the full universe",
        "Qadam-native edge",
        "Semiconductor Policy Options Asymmetry",
        "Defence Repricing Geopolitical Watch",
        "Silver Macro Liquidity Stress",
        "Crude Oil Energy Security Disruption",
        "Prediction Market Geopolitical Dislocation",
        "Akber filter",
        "guarded Alpaca Paper"
    ], "rendered D11E strategy narrative");

    includesAll(paperTradeState, [
        "Paper Account &amp; Trade State",
        "mirror",
        "data-paper-capacity-line",
        "Realized",
        "Unrealized",
        "Trade state",
        "Read paper mirror and lifecycle counts",
        "observed",
        "candidate",
        "Full signal rows, candidate lineage"
    ], "rendered D11E paper account and trade state");

    includesAll(sourceSummary, [
        "Evidence summary",
        "Show source posture only",
        "Full source rows and connection ledgers live in Evidence",
        "Reasoning owns hypotheses",
        "Trades owns signal rows"
    ], "rendered D11E source summary");
    assert(!paperTradeState.includes("USO options watch"), "D11E Overview must not show named trade rows");
    assert(!sourceSummary.includes("ACLED API"), "D11E Overview must not show named source rows");
    assert(!sourceSummary.includes("Worldview prior"), "D11E Overview must not show reasoning ledger rows");

    includesAll(controlPlane, [
        "Control Plane",
        "Control Plane owns operating flow",
        "Human oversight",
        "Chief Operating Officer",
        "Local LLM",
        "Frontier LLM",
        "Head of Quant",
        "Trade ideas stay candidates until gated paper-order records exist"
    ], "rendered D11E Control Plane");

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
