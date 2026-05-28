#!/usr/bin/env node

const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");

const {
    assert,
    html: renderedHtml,
    renderWithStatus,
    status
} = require("./check_dashboard_renderer.js");

const repoRoot = path.resolve(__dirname, "..");
const htmlPath = path.join(repoRoot, "landing-page-repo", "dashboard", "index.html");
const cssPath = path.join(repoRoot, "landing-page-repo", "auth.css");
const rendererPath = path.join(repoRoot, "landing-page-repo", "dashboard.js");
const contractPath = path.join(repoRoot, "docs", "qadam-dashboard-d11b-new-navigation-contract-2026-05-26.md");
const planPath = path.join(repoRoot, "docs", "qadam-dashboard-overhaul-master-implementation-plan.md");

const dashboardHtml = fs.readFileSync(htmlPath, "utf8");
const css = fs.readFileSync(cssPath, "utf8");
const renderer = fs.readFileSync(rendererPath, "utf8");
const contract = fs.readFileSync(contractPath, "utf8");
const plan = fs.readFileSync(planPath, "utf8");

function includesAll(text, needles, label) {
    const missing = needles.filter((needle) => !text.includes(needle));
    assert(missing.length === 0, `${label} missing ${missing.join(", ")}`);
}

function excludesAll(text, needles, label) {
    const present = needles.filter((needle) => text.includes(needle));
    assert(present.length === 0, `${label} still contains ${present.join(", ")}`);
}

function parseViewLinks(source) {
    const links = [];
    const pattern = /<a\b([^>]*)\bdata-dashboard-view-link\b([^>]*)>([^<]+)<\/a>/g;
    let match;
    while ((match = pattern.exec(source)) !== null) {
        const attributes = `${match[1]} ${match[2]}`;
        links.push({
            label: match[3].trim(),
            href: attributes.match(/\bhref="([^"]+)"/)?.[1],
            target: attributes.match(/\bdata-dashboard-view-target="([^"]+)"/)?.[1],
            section: attributes.match(/\bdata-target-section="([^"]+)"/)?.[1]
        });
    }
    return links;
}

function parseViewSections(source) {
    const sections = [];
    const pattern = /<(section|article)\b([^>]*)\bdata-dashboard-view-section="([^"]+)"([^>]*)>/g;
    let match;
    while ((match = pattern.exec(source)) !== null) {
        const attributes = `${match[2]} ${match[4]}`;
        sections.push({
            id: attributes.match(/\bid="([^"]+)"/)?.[1],
            view: match[3]
        });
    }
    return sections;
}

function loadRendererContext() {
    const documentElement = { dataset: {} };
    const document = {
        documentElement,
        querySelector() {
            return null;
        },
        querySelectorAll() {
            return [];
        }
    };
    const window = {
        document,
        location: { hash: "" },
        addEventListener() {},
        history: { pushState() {} },
        requestAnimationFrame(callback) {
            callback();
        },
        scrollTo() {}
    };
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
        fetch: async () => ({ ok: true, json: async () => ({}) }),
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

const expectedViews = ["overview", "trades", "evidence", "reasoning", "operations"];
const expectedLabels = ["Overview", "Trades", "Evidence", "Reasoning", "Operations"];
const links = parseViewLinks(dashboardHtml);
const sections = parseViewSections(dashboardHtml);
const sectionById = new Map(sections.map((section) => [section.id, section.view]));

assert(JSON.stringify(links.map((link) => link.target)) === JSON.stringify(expectedViews), "D11B nav targets mismatch");
assert(JSON.stringify(links.map((link) => link.label)) === JSON.stringify(expectedLabels), "D11B nav labels mismatch");
links.forEach((link) => {
    assert(link.href === `#${link.target}`, `${link.target} href should be canonical`);
    assert(link.section === link.target, `${link.target} data-target-section should match`);
});

[
    ["mission-control", "overview"],
    ["review-sequence", "overview"],
    ["trade-layer", "trades"],
    ["money", "trades"],
    ["watching", "evidence"],
    ["cognition", "reasoning"],
    ["strategy-manifestation", "reasoning"],
    ["worldview", "reasoning"],
    ["system-map", "operations"],
    ["forbidden", "operations"],
    ["process-console", "operations"],
    ["communications", "operations"],
    ["governance", "operations"]
].forEach(([sectionId, viewId]) => {
    assert(sectionById.get(sectionId) === viewId, `${sectionId} should belong to ${viewId}`);
});

includesAll(dashboardHtml, [
    "/auth.css?v=20260528-daily-digest",
    "/dashboard.js?v=20260528-daily-digest",
    "data-dashboard-debug-toggle",
    "data-dashboard-advanced-links",
    "data-dashboard-debug-only"
], "dashboard cache keys");

excludesAll(`${dashboardHtml}\n${css}\n${renderer}`, [
    "data-density-toggle",
    "data-density-option",
    "DASHBOARD_DENSITY_KEY",
    "function initDashboardDensityToggle",
    "window.setDashboardDensity",
    "document.documentElement.dataset.dashboardDensity",
    ".density-toggle",
    "html[data-dashboard-density=\"terminal\"]"
], "D11B codebase");

includesAll(renderer, [
    "const DASHBOARD_ADVANCED_DEBUG_KEY",
    "function setDashboardDebugMode",
    "window.setQadamDashboardDebugMode",
    "const DASHBOARD_LEGACY_HASH_TARGETS",
    "sources: { viewId: \"evidence\", targetId: \"watching\" }",
    "performance: { viewId: \"trades\", targetId: \"money\" }",
    "communications: { viewId: \"operations\", targetId: \"operations-readout\" }"
], "D11B renderer contract");

const window = loadRendererContext();
[
    ["#sources", "evidence", "watching"],
    ["#performance", "trades", "money"],
    ["#money", "trades", "money"],
    ["#governance", "operations", "operations-readout"],
    ["#communications", "operations", "operations-readout"],
    ["#system-map", "operations", "system-map"],
    ["#process-console", "operations", "operations-readout"],
    ["#forbidden", "operations", "operations-readout"],
    ["#worldview", "reasoning", "worldview"],
    ["#strategy-manifestation", "reasoning", "strategy-manifestation"]
].forEach(([hash, viewId, targetId]) => {
    const resolved = window.resolveQadamDashboardHash(hash);
    assert(resolved.viewId === viewId, `${hash} should resolve to ${viewId}`);
    assert(resolved.targetId === targetId, `${hash} should preserve target ${targetId}`);
    assert(resolved.legacy === true, `${hash} should be marked as legacy`);
});

includesAll(contract, [
    "exposes all five as primary Fund",
    "Manager navigation",
    "Diagnostics toggle",
    "`#evidence`",
    "`Executive / Terminal` density switcher is removed",
    "`#sources`",
    "`#performance`",
    "`#governance`",
    "Dashboard authority remains read-only and status-derived"
], "D11B contract document");

includesAll(plan, [
    "D11 Simplification Pass",
    "D11A - Information Diet Audit",
    "D11B - New Navigation Contract"
], "master plan D11 status");

(async () => {
    const rendered = await renderWithStatus(status);
    assert(rendered.document.documentElement.dataset.dashboardDensity === undefined, "rendered dashboard must not set density state");
    includesAll(dashboardHtml, ["data-dashboard-debug-toggle", "data-dashboard-advanced-links hidden"], "D11B advanced debug shell");
    const nextLinks = renderedHtml(rendered, "[data-overview-next-links]");
    includesAll(nextLinks, ["#trades", "#evidence", "#reasoning", "#operations"], "rendered overview next links");
    excludesAll(nextLinks, ["#sources", "#performance", "#governance"], "rendered overview next links");
    console.log("dashboard_d11b_new_navigation_contract=ok");
    console.log("dashboard_d11b_registered_view_count=5");
    console.log("dashboard_d11b_primary_views_visible=overview,trades,evidence,reasoning,operations");
    console.log("dashboard_d11b_diagnostics_toggle=True");
    console.log("dashboard_d11b_density_toggle_removed=True");
    console.log("dashboard_d11b_legacy_redirect_count=10");
    console.log("dashboard_authority_unchanged=True");
})().catch((error) => {
    console.error(error.message);
    process.exitCode = 1;
});
