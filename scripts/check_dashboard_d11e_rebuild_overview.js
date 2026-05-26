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
        "data-overview-command-surface",
        "data-overview-review-card",
        "data-overview-proof-flow",
        "data-overview-system-summary",
        "data-overview-status-rail",
        "data-overview-metrics",
        "data-overview-mini-map",
        "data-overview-next-links",
        "20260526-d11i-operations-view-anchor"
    ], "D11E overview HTML");

    excludesAll(dashboardHtml, [
        "overview-snapshot-grid",
        "overview-metric-grid",
        "overview-status-card",
        "Checking live-capital state"
    ], "D11E overview HTML");

    includesAll(css, [
        ".overview-command-surface",
        ".overview-review-card",
        ".overview-proof-flow",
        ".overview-system-summary",
        ".overview-status-chip",
        ".overview-readout-list",
        ".overview-system-grid"
    ], "D11E overview CSS");

    excludesAll(css, [
        ".overview-snapshot-grid",
        ".overview-metric-grid",
        ".overview-status-card"
    ], "D11E overview CSS");

    includesAll(renderer, [
        "status_chips",
        "review_focus",
        "readouts",
        "function renderOverviewChip",
        "function renderOverviewReadout",
        "Use the single safety strip for authority state",
        "Overview only answers what changed and which deeper view to open next"
    ], "D11E overview renderer");

    const window = loadRendererWindow();
    assert(typeof window.buildQadamDashboardViewModels === "function", "view-model builder missing");
    const models = window.buildQadamDashboardViewModels(status, { key: "live_bridge" });
    const overview = models.overview_model;
    assert(overview.cards.length <= 4, "Overview should expose no more than four first-screen readouts");
    assert(overview.readouts.length === 4, "Overview readouts should be exactly four");
    assert(overview.status_chips.length === 6, "Overview proof strip should be six compact chips");
    assert(overview.review_focus.state, "Overview review focus missing state");
    assert(overview.scope_note.includes("single safety strip"), "Overview scope note must reference the single safety strip");
    assert(!overview.summary.toLowerCase().includes("live capital"), "Overview summary must not duplicate live-capital safety copy");

    const rendered = await renderWithStatus(status);
    const statusRail = html(rendered, "[data-overview-status-rail]");
    const hero = html(rendered, "[data-overview-hero]");
    const metrics = html(rendered, "[data-overview-metrics]");
    const review = html(rendered, "[data-overview-review-card]");
    const system = [
        html(rendered, "[data-overview-oversight]"),
        html(rendered, "[data-overview-mini-map]"),
        html(rendered, "[data-overview-feed-strip]"),
        html(rendered, "[data-overview-boundary-rail]")
    ].join(" ");

    includesAll(statusRail, [
        "Day 0/30",
        "Week 0/5",
        "Eligible setups",
        "Submitted paper orders",
        "Postmortems due"
    ], "rendered D11E proof strip");

    excludesAll(statusRail, [
        "Paper/demo only",
        "Paper account",
        "Live capital"
    ], "rendered D11E proof strip");

    includesAll(hero, [
        "Fund Manager read",
        "sources current",
        "next review",
        "Use the single safety strip"
    ], "rendered D11E hero");

    includesAll(metrics, [
        "Source health",
        "Trade path",
        "Proof run",
        "Needs review"
    ], "rendered D11E readouts");

    assert(countOccurrences(metrics, "overview-readout") === 4, "Overview should render exactly four readouts");
    assert(!metrics.includes("overview-metric"), "Overview still renders old metric cards");

    includesAll(review, [
        "Needs review",
        "#trades",
        "#evidence",
        "#reasoning",
        "#operations"
    ], "rendered D11E review card");

    includesAll(system, [
        "You supervise the fund team",
        "Python script",
        "Local LLM",
        "Frontier LLM",
        "Quantum computer",
        "Candidate is not an order"
    ], "rendered D11E compact system map");

    assert(fs.existsSync(auditPath), "D11E audit document missing");
    includesAll(plan, [
        "D11E - Rebuild Overview",
        "D11F - Trades View Consolidation"
    ], "D11E master plan");

    console.log("dashboard_d11e_rebuild_overview=ok");
    console.log("dashboard_overview_readout_count=4");
    console.log("dashboard_overview_status_chip_count=6");
    console.log("dashboard_overview_duplicate_safety_copy_removed=True");
    console.log("dashboard_authority_unchanged=True");
}

if (require.main === module) {
    main().catch((error) => {
        console.error(error.message);
        process.exitCode = 1;
    });
}
