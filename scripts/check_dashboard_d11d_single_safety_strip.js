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
const contractPath = path.join(repoRoot, "docs", "qadam-dashboard-d11d-single-safety-strip-2026-05-26.md");
const planPath = path.join(repoRoot, "docs", "qadam-dashboard-overhaul-master-implementation-plan.md");

const dashboardHtml = fs.readFileSync(htmlPath, "utf8");
const css = fs.readFileSync(cssPath, "utf8");
const renderer = fs.readFileSync(rendererPath, "utf8");
const contract = fs.readFileSync(contractPath, "utf8");
const plan = fs.readFileSync(planPath, "utf8");

function count(text, needle) {
    return (text.match(new RegExp(needle.replace(/[.*+?^${}()|[\]\\]/g, "\\$&"), "g")) || []).length;
}

function includesAll(text, needles, label) {
    const missing = needles.filter((needle) => !text.includes(needle));
    assert(missing.length === 0, `${label} missing ${missing.join(", ")}`);
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

assert(count(dashboardHtml, "data-dashboard-safety-strip") === 1, "static shell must contain exactly one safety strip");

includesAll(dashboardHtml, [
    "Safety status",
    "Paper trading authorized",
    "Paper-only monitoring. Live capital is off; order authority stays behind runtime gates.",
    "Paper mode, capital state, and order authority in one strip.",
    "data-operations-safety-reference"
], "static single safety strip shell");
assert(count(dashboardHtml, "<dt>Limits</dt>") === 0, "static founder shell still contains Limits rows");
assert(count(dashboardHtml, "<dt>Boundary</dt>") === 0, "static founder shell still contains Boundary rows");
assert(count(dashboardHtml, "node-authority") === 0, "static founder shell still contains node-authority badges");

includesAll(css, [
    ".dashboard-safety-strip",
    ".dashboard-safety-strip-main",
    ".dashboard-safety-strip-badges",
    ".operations-safety-reference"
], "single safety strip CSS");

includesAll(renderer, [
    "function buildDashboardSafetyStripModel",
    "function renderDashboardSafetyStrip",
    "safety_strip_model",
    "data-dashboard-safety-strip",
    "data-safety-label",
    "Paper growth maturity requires verified records",
    "renderDashboardSafetyStrip(status, viewModels)",
    "window.buildQadamDashboardSafetyStripModel"
], "single safety strip renderer");

[
    "data-operations-safety-rail",
    ".operations-safety-rail",
    "Persistent safety rail"
].forEach((needle) => {
    assert(!`${dashboardHtml}\n${css}\n${renderer}`.includes(needle), `obsolete duplicate safety rail still present: ${needle}`);
});

includesAll(contract, [
    "D11D Safety Status Strip",
    "data-dashboard-safety-strip",
    "buildDashboardSafetyStripModel",
    "renderDashboardSafetyStrip",
    "Paper growth maturity requires verified records",
    "Existing authority remains unchanged and read-only"
], "D11D contract document");

includesAll(plan, [
    "D11D - Single Safety Strip",
    "D11E - Rebuild Overview"
], "master plan D11D status");

const window = loadRendererWindow();
assert(typeof window.buildQadamDashboardSafetyStripModel === "function", "safety strip model builder not exported");
const model = window.buildQadamDashboardSafetyStripModel(status);
assert(model.id === "dashboard_safety_strip", "safety strip model id mismatch");
assert(model.mode_label === "OK - paper only", "safety strip mode label mismatch");
assert(model.live_capital_label === "OK - live capital off", "safety strip live-capital label mismatch");
assert(model.safety_label === "Paper-only monitoring", "safety strip single label mismatch");
assert(model.write_authority === false, "safety strip reports write authority");
assert(model.live_capital_enabled === false, "safety strip reports live capital enabled");
assert(model.authority_flag_count === 0, "safety strip reports authority flags");

(async () => {
    const rendered = await renderWithStatus(status);
    const stripHtml = html(rendered, "[data-dashboard-safety-strip]");
    const overviewBoundaryHtml = html(rendered, "[data-overview-control-plane]");
    const operationsHtml = html(rendered, "[data-flow-map]");

    includesAll(stripHtml, [
        "Safety status",
        "Paper trading authorized",
        "Paper-only monitoring",
        "Order authority remains behind runtime gates"
    ], "rendered safety strip");
    assert(count(stripHtml, "inline-badge") === 1, "rendered safety strip should collapse to one badge");
    assert(!stripHtml.includes("<dt>Limits</dt>"), "rendered safety strip still contains Limits row");

    includesAll(overviewBoundaryHtml, [
        "authority stops",
        "only guarded paper checks can move toward paper trading",
        "Trade ideas stay candidates"
    ], "overview safety reference");
    assert(!overviewBoundaryHtml.includes("Broker writes blocked"), "overview still duplicates broker-write safety copy");
    assert(!overviewBoundaryHtml.includes("live capital disabled"), "overview still duplicates live-capital safety copy");

    includesAll(operationsHtml, [
        "Safety Status above",
        "Operations below show the evidence behind that state"
    ], "operations safety reference");
    assert(!operationsHtml.includes("Persistent safety rail"), "operations still renders duplicate safety rail");
    assert(!operationsHtml.includes("node-authority"), "operations still renders per-node authority badges");

    console.log("dashboard_d11d_single_safety_strip=ok");
    console.log("dashboard_d11d_static_safety_strip_count=1");
    console.log("dashboard_d11d_operations_safety_rail_removed=True");
    console.log("dashboard_d11d_authority_unchanged=True");
})().catch((error) => {
    console.error(error.message);
    process.exitCode = 1;
});
