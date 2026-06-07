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
const rendererPath = path.join(repoRoot, "landing-page-repo", "dashboard.js");
const contractPath = path.join(repoRoot, "docs", "qadam-dashboard-d11c-canonical-status-language-2026-05-26.md");
const planPath = path.join(repoRoot, "docs", "qadam-dashboard-overhaul-master-implementation-plan.md");

const dashboardHtml = fs.readFileSync(htmlPath, "utf8");
const renderer = fs.readFileSync(rendererPath, "utf8");
const contract = fs.readFileSync(contractPath, "utf8");
const plan = fs.readFileSync(planPath, "utf8");

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

includesAll(renderer, [
    "const CANONICAL_STATUS_LANGUAGE",
    "function canonicalStatusRecord",
    "function canonicalStatusLabel",
    "function canonicalStatusTone",
    "function canonicalBadgeText",
    "window.canonicalQadamDashboardStatus",
    "window.canonicalQadamDashboardStatusLabel",
    "window.canonicalQadamDashboardStatusTone"
], "renderer canonical status API");

includesAll(renderer, [
    "Blocked",
    "Waiting",
    "Not configured",
    "Optional",
    "OK - live capital off",
    "OK - read-only",
    "OK - paper only",
    "Dry run",
    "Fault",
    "Review only",
    "Local only"
], "renderer canonical vocabulary");

includesAll(dashboardHtml, [
    "Blocked",
    "Waiting",
    "Paper action ready through guarded route",
    "Paper-only readout · live capital off",
    "Read-only lock"
], "static fallback canonical vocabulary");

includesAll(contract, [
    "D11C Canonical Status Language",
    "OK",
    "OK - read-only",
    "OK - paper only",
    "OK - live capital off",
    "Waiting",
    "Optional",
    "Not configured",
    "Blocked",
    "Fault",
    "Dashboard authority remains read-only and status-derived"
], "D11C contract document");

includesAll(plan, [
    "D11C - Canonical Status Language",
    "D11D - Single Safety Strip"
], "master plan D11C status");

const window = loadRendererWindow();
assert(typeof window.canonicalQadamDashboardStatus === "function", "canonical status function not exported");

[
    ["online", "OK", "online"],
    ["read_only_ready", "OK - read-only", "online"],
    ["paper/demo only", "OK - paper only", "online"],
    ["live capital disabled", "OK - live capital off", "online"],
    ["dry_run", "Dry run", "pending"],
    ["pending", "Waiting", "pending"],
    ["not required", "Optional", "pending"],
    ["not exported", "Not configured", "degraded"],
    ["degraded", "Needs attention", "degraded"],
    ["local_only", "Local only", "local-only"],
    ["non_executable", "Review only", "blocked"],
    ["blocked", "Blocked", "blocked"],
    ["failed", "Fault", "blocked"]
].forEach(([raw, expectedLabel, expectedTone]) => {
    const record = window.canonicalQadamDashboardStatus(raw);
    assert(record.label === expectedLabel, `${raw} canonical label ${record.label} !== ${expectedLabel}`);
    assert(record.tone === expectedTone, `${raw} canonical tone ${record.tone} !== ${expectedTone}`);
});

(async () => {
    const rendered = await renderWithStatus(status);
    const flowHtml = html(rendered, "[data-flow-map]");
    const safetyStripHtml = html(rendered, "[data-dashboard-safety-strip]");
    const reasoningHtml = html(rendered, "[data-cognition]");

    includesAll(`${flowHtml} ${safetyStripHtml} ${reasoningHtml}`, [
        "OK",
        "Paper-only readout · live capital off",
        "Waiting",
        "Blocked"
    ], "rendered canonical status output");

    assert(!/node-status pending\">Pending<\/b>/.test(`${flowHtml} ${reasoningHtml}`), "raw Pending status pill leaked");
    assert(!/node-status blocked\">Safety stop<\/b>/.test(`${flowHtml} ${reasoningHtml}`), "old safety-stop status pill leaked");

    console.log("dashboard_d11c_canonical_status_language=ok");
    console.log("dashboard_d11c_status_label_count=13");
    console.log("dashboard_d11c_blocked_language=True");
    console.log("dashboard_d11c_waiting_language=True");
    console.log("dashboard_d11c_not_configured_language=True");
    console.log("dashboard_authority_unchanged=True");
})().catch((error) => {
    console.error(error.message);
    process.exitCode = 1;
});
