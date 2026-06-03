#!/usr/bin/env node

const fs = require("node:fs");
const path = require("node:path");

const repoRoot = path.resolve(__dirname, "..");
const htmlPath = path.join(repoRoot, "landing-page-repo", "dashboard", "index.html");
const cssPath = path.join(repoRoot, "landing-page-repo", "auth.css");
const planPath = path.join(repoRoot, "docs", "qadam-dashboard-implementation-plan.md");

const html = fs.readFileSync(htmlPath, "utf8");
const css = fs.readFileSync(cssPath, "utf8");
const plan = fs.readFileSync(planPath, "utf8");

function assert(condition, message) {
    if (!condition) throw new Error(message);
}

function assertIncludes(text, expected, label) {
    assert(text.includes(expected), `${label} missing: ${expected}`);
}

function assertNoUnsafePublicText(text, label) {
    [
        /\/Users\//,
        /\/private\//,
        /\/var\/folders\//,
        /\\Users\\/,
        /\d{6,}:[A-Za-z0-9_-]{20,}/,
        /sk-[A-Za-z0-9_-]{20,}/,
        /ghp_[A-Za-z0-9_]{20,}/,
        /PVZ[0-9A-Za-z_-]{20,}/,
        /TELEGRAM_BOT_TOKEN=/,
        /TELEGRAM_DEFAULT_CHAT_ID=/,
        /SUPABASE_SECRET_KEY=/,
        /GEMINI_API_KEY=/
    ].forEach((pattern) => {
        assert(!pattern.test(text), `${label} contains unsafe public text: ${pattern}`);
    });
}

function explainerBlock(id) {
    const marker = `data-section-explainer="${id}"`;
    const markerIndex = html.indexOf(marker);
    assert(markerIndex >= 0, `missing explainer ${id}`);
    const start = html.lastIndexOf("<div", markerIndex);
    assert(start >= 0, `explainer ${id} missing opening div`);
    const end = html.indexOf("</dl>", markerIndex);
    assert(end >= 0, `explainer ${id} missing explainer-grid`);
    return html.slice(start, end + "</dl>".length);
}

const requiredExplainers = [
    "status_safety",
    "mission_control",
    "phase4_strategy",
    "system_operating_map",
    "operating_detail",
    "watching",
    "cognition",
    "forbidden_actions",
    "telegram_communications",
    "trade_layer",
    "money",
    "process_console",
    "private_edge_layer",
    "fund_manager_comments"
];

requiredExplainers.forEach((id) => {
    const block = explainerBlock(id);
    assertIncludes(block, "section-explainer", id);
    assertIncludes(block, "role=\"tooltip\"", id);
    assertIncludes(block, "data-tooltip-contract=\"compact\"", id);
    assertIncludes(block, "explainer-grid compact", id);
    assertIncludes(block, "<dt>Shows</dt>", id);
    assertIncludes(block, "<dt>Watch</dt>", id);
    assertIncludes(block, "<dt>Limits</dt>", id);
    assertIncludes(block, "<dd>", id);
    assert(!block.includes("<dt>Use it to</dt>"), `${id} still uses verbose Use it to label`);
    assert(!block.includes("<dt>Watch for</dt>"), `${id} still uses verbose Watch for label`);
    assert(!block.includes("<dt>Boundary</dt>"), `${id} still uses verbose Boundary label`);

    const plainBlocks = [...block.matchAll(/<(p|dd)>(.*?)<\/\1>/g)].map((match) => (
        match[2]
            .replace(/<[^>]+>/g, "")
            .replace(/&amp;/g, "&")
            .replace(/\s+/g, " ")
            .trim()
    ));
    plainBlocks.forEach((text) => {
        assert(text.length <= 88, `${id} explainer text is too long: ${text}`);
    });
});

[
    "One place for paper mode, capital, and order authority.",
    "Summary only; Diagnostics has technical detail.",
    "Map only; nodes are not controls.",
    "Observation only; no order creation.",
    "Hypothesis only; risk still decides.",
    "Notify-only; no command path.",
    "A trade idea is not an order.",
    "Event stream only; not shell access.",
    "Context only; requires live corroboration.",
    "Governance only; no runtime or trade authority."
].forEach((needle) => assertIncludes(html, needle, "dashboard explainer boundary"));

[
    ".section-explainer",
    ".explainer-grid",
    ".explainer-grid.compact",
    ".explainer-grid dt",
    ".explainer-grid dd",
    ".section-intro-heading"
].forEach((needle) => assertIncludes(css, needle, "explainer CSS"));

assert(!html.includes("<dt>Use it to</dt>"), "dashboard still has verbose tooltip label: Use it to");
assert(!html.includes("<dt>Watch for</dt>"), "dashboard still has verbose tooltip label: Watch for");
assertIncludes(html, "/auth.css?v=20260603-rs3-market-context", "dashboard stylesheet cache key");
assertIncludes(plan, "Phase D10E - Section Explainers", "dashboard implementation plan");
assertNoUnsafePublicText(html, "dashboard explainers");

console.log("dashboard_section_explainers=ok");
