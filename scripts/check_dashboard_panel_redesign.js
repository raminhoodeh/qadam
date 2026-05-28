#!/usr/bin/env node

const fs = require("node:fs");
const path = require("node:path");

const {
    assert,
    assertIncludes,
    renderWithStatus,
    status
} = require("./check_dashboard_renderer.js");

const repoRoot = path.resolve(__dirname, "..");
const htmlPath = path.join(repoRoot, "landing-page-repo", "dashboard", "index.html");
const cssPath = path.join(repoRoot, "landing-page-repo", "auth.css");
const rendererPath = path.join(repoRoot, "landing-page-repo", "dashboard.js");
const planPath = path.join(repoRoot, "docs", "qadam-dashboard-implementation-plan.md");

const html = fs.readFileSync(htmlPath, "utf8");
const css = fs.readFileSync(cssPath, "utf8");
const renderer = fs.readFileSync(rendererPath, "utf8");
const plan = fs.readFileSync(planPath, "utf8");

function assertText(text, expected, label) {
    assert(text.includes(expected), `${label} missing ${expected}`);
}

function staticBriefBlock(id) {
    const marker = `data-panel-brief="${id}"`;
    const start = html.indexOf(marker);
    assert(start >= 0, `static panel brief missing ${id}`);
    const sectionStart = html.lastIndexOf("<section", start);
    const sectionEnd = html.indexOf("</section>", start);
    assert(sectionStart >= 0 && sectionEnd >= 0, `static panel brief ${id} is incomplete`);
    return html.slice(sectionStart, sectionEnd + "</section>".length);
}

[
    "forbidden_actions",
    "telegram_communications",
    "money",
    "process_console",
    "private_edge_layer",
    "fund_manager_comments"
].forEach((id) => {
    const block = staticBriefBlock(id);
    assertText(block, "Panel readout", id);
    assertText(block, "<dt>State</dt>", id);
    assertText(block, "<dt>Watch</dt>", id);
    assertText(block, "<dt>Boundary</dt>", id);
});

[
    "function renderPanelBrief",
    "function replacePanelBrief",
    "data-panel-brief",
    "Are Qadam's inputs healthy enough to trust?",
    "Is the paper account proving or losing trust?",
    "What did Qadam last report about itself?"
].forEach((needle) => assertText(renderer, needle, "dashboard renderer"));

[
    ".panel-brief",
    ".panel-brief-main",
    ".panel-brief-facts",
    ".panel-brief.online",
    ".panel-brief.pending",
    ".panel-brief.blocked"
].forEach((needle) => assertText(css, needle, "panel redesign CSS"));

assertText(html, "/auth.css?v=20260528-overview-drilldown", "stylesheet cache key");
assertText(html, "/dashboard.js?v=20260528-overview-drilldown", "dashboard script cache key");
assertText(plan, "Phase D10F - Panel-Level Redesign", "implementation plan");

(async () => {
    const rendered = await renderWithStatus(status);
    assertIncludes(rendered, "[data-cognition]", "Reasoning readout");
    assertIncludes(rendered, "[data-cognition]", "Can this idea move beyond research?");
    assertIncludes(rendered, "[data-worldview]", "Which private priors are shaping the questions?");
    assertIncludes(rendered, "[data-communications]", "What has Qadam told or learned from Telegram?");
    assertIncludes(rendered, "[data-trade-layer]", "Consolidated trade readout");
    assertIncludes(rendered, "[data-capital]", "Is the paper account proving or losing trust?");
    console.log("dashboard_panel_redesign=ok");
})().catch((error) => {
    console.error(error);
    process.exit(1);
});
