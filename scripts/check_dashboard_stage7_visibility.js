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
const guideDocPath = path.join(repoRoot, "docs", "qadam-user-guide.md");
const guideHtmlPath = path.join(repoRoot, "landing-page-repo", "guide", "index.html");

const dashboardHtml = fs.readFileSync(htmlPath, "utf8");
const css = fs.readFileSync(cssPath, "utf8");
const renderer = fs.readFileSync(rendererPath, "utf8");
const guideDoc = fs.readFileSync(guideDocPath, "utf8");
const guideHtml = fs.readFileSync(guideHtmlPath, "utf8");

const REQUIRED_SECTIONS = [
    "system_operating_map",
    "system_status",
    "data_sources_connected",
    "trading_strategies",
    "qadam_activity_feed",
    "trade_consideration_board",
    "paper_portfolio_capacity"
];

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
        "data-stage7-dashboard-visibility",
        "Stage 7 Fund Manager cockpit",
        "Stage 7 Fund Manager cockpit: system map, status, sources, strategies, activity feed, trade consideration board, and paper portfolio capacity.",
        "data-dashboard-debug-only hidden",
        "data-overview-portfolio-hero",
        "data-overview-mission-brief",
        "data-overview-control-plane",
        "data-overview-source-summary",
        "data-overview-edge-tracker"
    ], "Stage 7 dashboard HTML");

    includesAll(css, [
        ".stage7-dashboard-visibility",
        ".stage7-visibility-shell",
        ".stage7-system-map",
        ".stage7-system-status",
        ".stage7-sources",
        ".stage7-strategies",
        ".stage7-activity-feed",
        ".stage7-trade-board",
        ".stage7-paper-capacity",
        ".stage7-proof-drawer",
        ".stage7-board-grid",
        ".stage7-feed-list",
        "@media (max-width: 900px)"
    ], "Stage 7 dashboard CSS");

    includesAll(renderer, [
        "const STAGE7_LEVEL1_SECTIONS",
        "function buildStage7VisibilityModel",
        "function renderStage7Visibility",
        "function renderStage7SystemMap",
        "function renderStage7SystemStatus",
        "function renderStage7Sources",
        "function renderStage7Strategies",
        "function renderStage7ActivityFeed",
        "function renderStage7TradeBoard",
        "function renderStage7PortfolioCapacity",
        "stage7_visibility_model",
        "Dashboard Visibility is read-only"
    ], "Stage 7 dashboard renderer");

    [guideDoc, guideHtml].forEach((guideText, index) => {
        const label = index === 0 ? "Stage 7 guide markdown" : "Stage 7 guide HTML";
        includesAll(guideText, [
            "Seven Stage 7 Dashboard Sections",
            "System Operating Map",
            "System Status",
            "Data Sources Connected",
            "Trading Strategies",
            "Qadam Activity Feed",
            "Trade Consideration Board",
            "Paper Portfolio Capacity",
            "Advanced / Debug Mode",
            "GBP 100,000",
            "GBP 200,000",
            "hidden chain-of-thought"
        ], label);
    });

    const models = buildModels();
    const stage7 = models.stage7_visibility_model;
    assert(stage7.schema_version === "stage7_dashboard_visibility.v1", "Stage 7 schema mismatch");
    assert(stage7.status === "stage7_visibility_ready", "Stage 7 status mismatch");
    assert(stage7.level_1_section_count === 7, "Stage 7 must expose seven default sections");
    assert(JSON.stringify(stage7.level_1_sections.map((section) => section.id)) === JSON.stringify(REQUIRED_SECTIONS), "Stage 7 section order mismatch");
    assert(stage7.operating_map.nodes.length === 9, "Stage 7 operating map must show nine fund-team nodes");
    assert(stage7.operating_map.edges.some((edge) => edge.state === "locked"), "Stage 7 operating map must show locked authority edge");
    assert(stage7.operating_map.sentence.includes("Alpaca Paper only when gates pass"), "Stage 7 operating sentence missing paper gate");
    assert(stage7.system_status.rows.length === 5, "Stage 7 system status must group by consequence");
    assert(stage7.data_sources.total >= 30, "Stage 7 source count too low");
    assert(stage7.data_sources.required_blocker_count === 0, "Stage 7 should not show required trade-blocking source gaps");
    assert(stage7.trading_strategies.mandate.includes("GBP 100,000"), "Stage 7 mandate missing paper baseline");
    assert(stage7.trading_strategies.mandate.includes("GBP 200,000"), "Stage 7 mandate missing paper target");
    ["Prediction markets", "Crude oil", "Defence", "Silver", "Semiconductors"].forEach((domain) => {
        assert(stage7.trading_strategies.domains.includes(domain), `Stage 7 strategy domain missing ${domain}`);
    });
    assert(stage7.activity_feed.item_count >= 7, "Stage 7 activity feed is too thin");
    assert(stage7.activity_feed.public_safe === true, "Stage 7 activity feed must be public safe");
    assert(stage7.activity_feed.hidden_chain_of_thought_exposed === false, "Stage 7 must not expose hidden chain-of-thought");
    assert(stage7.trade_consideration_board.column_count === 7, "Stage 7 trade board must expose seven decision columns");
    assert(stage7.trade_consideration_board.paper_order_authority === false, "Stage 7 trade board cannot place paper orders");
    assert(stage7.paper_portfolio_capacity.baseline_gbp === 100000, "Stage 7 paper capacity baseline mismatch");
    assert(stage7.paper_portfolio_capacity.target_gbp === 200000, "Stage 7 paper capacity target mismatch");
    Object.entries(stage7.authority).forEach(([key, value]) => {
        assert(value === false, `Stage 7 authority flag must be false: ${key}`);
    });

    const rendered = await renderWithStatus(status);
    const stage7Html = html(rendered, "[data-stage7-dashboard-visibility]");
    REQUIRED_SECTIONS.forEach((sectionId) => {
        assert(stage7Html.includes(`data-stage7-section="${sectionId}"`), `Rendered Stage 7 missing section ${sectionId}`);
    });
    [
        "System Operating Map",
        "System Status",
        "Data Sources Connected",
        "Trading Strategies",
        "Qadam Activity Feed",
        "Trade Consideration Board",
        "Paper Portfolio Capacity",
        "Fund Manager cockpit",
        "You supervise",
        "Data sources",
        "Research Analyst",
        "Strategy Lead",
        "Head of Quant",
        "Risk gate",
        "Paper desk",
        "Learning loop",
        "Prediction markets",
        "Crude oil",
        "Defence",
        "Silver",
        "Semiconductors",
        "GBP 100,000",
        "GBP 200,000",
        "Dashboard Visibility is read-only"
    ].forEach((needle) => {
        assert(stage7Html.includes(needle), `Rendered Stage 7 missing visible copy: ${needle}`);
    });
    assertIncludes(rendered, "[data-stage7-dashboard-visibility]", "data-stage7-contract=\"dashboard_visibility_v1\"");
    assert(!stage7Html.includes("Phase 7"), "Stage 7 default dashboard should not expose Phase 7 copy");
    assert(
        !/\b(can|may|allowed to|able to)\s+(submit paper orders?|place orders?|approve trades?|enable live capital)\b/i.test(stage7Html),
        "Stage 7 rendered permissive unsafe action language"
    );

    console.log("Dashboard Stage 7 visibility contract OK");
    console.log(`Stage 7 sections: ${REQUIRED_SECTIONS.join(", ")}`);
}

if (require.main === module) {
    main().catch((error) => {
        console.error(error.message);
        process.exitCode = 1;
    });
}
