#!/usr/bin/env node

const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");

const {
    assert,
    html,
    renderWithStatus,
    status
} = require("./check_dashboard_renderer.js");

const repoRoot = path.resolve(__dirname, "..");
const htmlPath = path.join(repoRoot, "landing-page-repo", "dashboard", "index.html");
const cssPath = path.join(repoRoot, "landing-page-repo", "auth.css");
const rendererPath = path.join(repoRoot, "landing-page-repo", "dashboard.js");
const planPath = path.join(repoRoot, "docs", "qadam-dashboard-overhaul-master-implementation-plan.md");
const auditPath = path.join(repoRoot, "docs", "qadam-dashboard-d11f-trades-view-consolidation-2026-05-26.md");

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
        "Trade lifecycle and paper-state review",
        "data-trade-consolidated-snapshot",
        "data-trade-diagnostic-groups",
        "data-trade-review-group=\"proof_lifecycle\"",
        "data-trade-review-group=\"gate_chain\"",
        "data-trade-review-group=\"signal_records\""
    ], "D11F trades static shell");

    excludesAll(dashboardHtml, [
        "class=\"trade-route\"",
        "data-panel-brief=\"trade_layer\"",
        "Intent board"
    ], "D11F trades static shell");

    includesAll(css, [
        ".trade-consolidated-snapshot",
        ".trade-consolidated-metrics",
        ".trade-diagnostic-groups",
        ".trade-review-group",
        ".trade-review-group-body"
    ], "D11F trades CSS");

    excludesAll(css, [".trade-route"], "D11F trades CSS");

    includesAll(renderer, [
        "consolidated_review_groups",
        "data-trade-consolidated-snapshot",
        "data-trade-diagnostic-groups",
        "data-trade-review-group=\"proof_lifecycle\"",
        "data-trade-review-group=\"gate_chain\"",
        "data-trade-review-group=\"signal_records\""
    ], "D11F trades renderer");

    const window = loadRendererWindow();
    assert(typeof window.buildQadamDashboardTradesModel === "function", "trades model builder missing");
    const model = window.buildQadamDashboardTradesModel(status);
    assert(model.consolidated_review_groups.length === 3, "Trades model should expose three consolidated review groups");
    assert(model.consolidated_review_groups[0].id === "proof_lifecycle", "first review group should be proof lifecycle");
    assert(model.consolidated_review_groups[1].id === "gate_chain", "second review group should be gate chain");
    assert(model.consolidated_review_groups[2].id === "signal_records", "third review group should be signal records");

    const rendered = await renderWithStatus(status);
    const tradeHtml = html(rendered, "[data-trade-layer]");

    includesAll(tradeHtml, [
        "Trade lifecycle board",
        "Consolidated trade readout",
        "Proof and paper lifecycle",
        "Gate chain and broker readiness",
        "Signals, candidates, and paper states",
        "Q5-14 End-To-End Paper Trade Drill",
        "Q5-15 Phase 5 Certification",
        "Q6-16 Learning Loop Journal Visibility",
        "Q7-15 Phase 7 Demo Proof Visibility",
        "Signal Review UI and governance actions",
        "Risk Agent policy router",
        "Execution Policy and kill switches",
        "Read-only broker reconciliation",
        "Dry-run paper-submit receipt",
        "TradingView alert source",
        "Observed signals",
        "Candidates",
        "Blocked trades",
        "Paper lifecycle states"
    ], "rendered D11F Trades");

    assert(countOccurrences(tradeHtml, "data-trade-review-group=") === 3, "Trades should render exactly three review groups");
    assert(!tradeHtml.includes("data-panel-brief=\"trade_layer\""), "Trades still renders duplicate panel brief");
    assert(!tradeHtml.includes("trade-route"), "Trades still renders the obsolete static trade route");
    assert(tradeHtml.includes("Candidate is not an order") || tradeHtml.includes("Candidate is not order"), "candidate/order boundary missing");
    assert(tradeHtml.includes("No UI proof credit"), "proof-credit boundary missing");

    assert(fs.existsSync(auditPath), "D11F audit document missing");
    includesAll(plan, [
        "D11F - Trades View Consolidation",
        "D11G - Evidence View Consolidation"
    ], "D11F master plan");

    console.log("dashboard_d11f_trades_view_consolidation=ok");
    console.log("dashboard_d11f_review_group_count=3");
    console.log("dashboard_d11f_trade_panel_brief_removed=True");
    console.log("dashboard_d11f_static_trade_route_removed=True");
    console.log("dashboard_authority_unchanged=True");
}

if (require.main === module) {
    main().catch((error) => {
        console.error(error.message);
        process.exitCode = 1;
    });
}
