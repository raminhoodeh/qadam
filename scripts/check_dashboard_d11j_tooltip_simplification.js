#!/usr/bin/env node

const fs = require("node:fs");
const path = require("node:path");

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
const planPath = path.join(repoRoot, "docs", "qadam-dashboard-overhaul-master-implementation-plan.md");
const auditPath = path.join(repoRoot, "docs", "qadam-dashboard-d11j-tooltip-simplification-2026-05-26.md");

const html = fs.readFileSync(htmlPath, "utf8");
const css = fs.readFileSync(cssPath, "utf8");
const renderer = fs.readFileSync(rendererPath, "utf8");
const plan = fs.readFileSync(planPath, "utf8");

const tooltipIds = [
    "status_safety",
    "mission_control",
    "phase4_strategy",
    "system_operating_map",
    "watching",
    "cognition",
    "trade_layer",
    "money"
];

function includesAll(text, needles, label) {
    needles.forEach((needle) => {
        assert(text.includes(needle), `${label} missing ${needle}`);
    });
}

function blockFor(id) {
    const marker = `data-section-explainer="${id}"`;
    const markerIndex = html.indexOf(marker);
    assert(markerIndex >= 0, `missing tooltip ${id}`);
    const start = html.lastIndexOf("<div", markerIndex);
    const end = html.indexOf("</dl>", markerIndex);
    assert(start >= 0 && end >= 0, `tooltip ${id} has invalid shell`);
    return html.slice(start, end + "</dl>".length);
}

function plainText(value) {
    return value
        .replace(/<[^>]+>/g, "")
        .replace(/&amp;/g, "&")
        .replace(/\s+/g, " ")
        .trim();
}

function compactTextItems(block) {
    return [...block.matchAll(/<(p|dd)>(.*?)<\/\1>/g)].map((match) => plainText(match[2]));
}

function assertCompactBlock(block, id) {
    includesAll(block, [
        "role=\"tooltip\"",
        "data-tooltip-contract=\"compact\"",
        "explainer-grid compact",
        "<dt>Shows</dt>",
        "<dt>Watch</dt>",
        "<dt>Scope</dt>"
    ], `tooltip ${id}`);

    [
        "<dt>Use it to</dt>",
        "<dt>Watch for</dt>",
        "<dt>Limits</dt>",
        "<dt>Boundary</dt>",
        "cannot approve, place, modify",
        "cannot place, approve, reject",
        "cannot create trade candidates",
        "Every detail panel renders sanitized"
    ].forEach((forbidden) => {
        assert(!block.includes(forbidden), `tooltip ${id} still contains verbose copy: ${forbidden}`);
    });

    const textItems = compactTextItems(block);
    assert(textItems.length === 4, `tooltip ${id} should have one summary and three rows`);
    textItems.forEach((text) => {
        assert(text.length > 0, `tooltip ${id} has empty text`);
        assert(text.length <= 88, `tooltip ${id} text too long: ${text}`);
    });
}

async function main() {
    const compactCount = (html.match(/data-tooltip-contract="compact"/g) || []).length;
    assert(compactCount === tooltipIds.length, `expected ${tooltipIds.length} compact tooltips, found ${compactCount}`);

    tooltipIds.forEach((id) => assertCompactBlock(blockFor(id), id));

    includesAll(css, [
        "width: min(340px, calc(100vw - 48px))",
        ".explainer-grid.compact div:first-child",
        "grid-template-columns: 64px minmax(0, 1fr)"
    ], "D11J tooltip CSS");

    includesAll(renderer, [
        "data-tooltip-contract=\"compact\"",
        "explainer-grid compact",
        "<dt>Shows</dt>",
        "<dt>Watch</dt>",
        "<dt>Scope</dt>"
    ], "D11J renderer tooltip");
    assert(!renderer.includes("<p>${htmlText(strip.boundary)}</p>"), "renderer still injects long safety boundary into tooltip");

    const rendered = await renderWithStatus(status);
    const renderedSafetyTooltip = renderedHtml(rendered, "[data-dashboard-safety-strip]");
    includesAll(renderedSafetyTooltip, [
        "data-section-explainer=\"status_safety\"",
        "data-tooltip-contract=\"compact\"",
        "<dt>Shows</dt>",
        "<dt>Watch</dt>",
        "<dt>Scope</dt>"
    ], "rendered D11J safety tooltip");
    assert(!renderedSafetyTooltip.includes("Use it to"), "rendered safety tooltip still uses Use it to");
    assert(!renderedSafetyTooltip.includes("Watch for"), "rendered safety tooltip still uses Watch for");

    assert(fs.existsSync(auditPath), "D11J audit document missing");
    includesAll(plan, [
        "D11J - Tooltip Simplification",
        "D11K - View Model Refactor"
    ], "D11J master plan");

    console.log("dashboard_d11j_tooltip_simplification=ok");
}

main().catch((error) => {
    console.error(error);
    process.exit(1);
});
