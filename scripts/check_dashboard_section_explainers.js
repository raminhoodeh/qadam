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
    assertIncludes(block, "<dt>Use it to</dt>", id);
    assertIncludes(block, "<dt>Watch for</dt>", id);
    assertIncludes(block, "<dt>Boundary</dt>", id);
    assertIncludes(block, "<dd>", id);
});

[
    "This cockpit is read-only",
    "This is a read-only summary",
    "No node is a command button",
    "Every detail panel renders sanitized status only",
    "A watched source is observation only",
    "A hypothesis is not a trade",
    "This panel cannot unlock them",
    "Telegram is outbound notify-only",
    "A candidate is not an order",
    "paper mirror only",
    "not shell access",
    "Worldview is context only, not evidence",
    "Comments are governance only"
].forEach((needle) => assertIncludes(html, needle, "dashboard explainer boundary"));

[
    ".section-explainer",
    ".explainer-grid",
    ".explainer-grid dt",
    ".explainer-grid dd",
    ".section-intro-heading"
].forEach((needle) => assertIncludes(css, needle, "explainer CSS"));

assertIncludes(html, "/auth.css?v=20260526-paper-equity-chart", "dashboard stylesheet cache key");
assertIncludes(plan, "Phase D10E - Section Explainers", "dashboard implementation plan");
assertNoUnsafePublicText(html, "dashboard explainers");

console.log("dashboard_section_explainers=ok");
