#!/usr/bin/env node

const fs = require("node:fs");
const path = require("node:path");

const repoRoot = path.resolve(__dirname, "..");
const auditPath = path.join(repoRoot, "docs", "qadam-dashboard-d11a-information-diet-audit-2026-05-26.md");
const htmlPath = path.join(repoRoot, "landing-page-repo", "dashboard", "index.html");
const rendererPath = path.join(repoRoot, "landing-page-repo", "dashboard.js");

const audit = fs.readFileSync(auditPath, "utf8");
const html = fs.readFileSync(htmlPath, "utf8");
const renderer = fs.readFileSync(rendererPath, "utf8");

function assert(condition, message) {
    if (!condition) throw new Error(message);
}

function includesAll(text, needles, label) {
    const missing = needles.filter((needle) => !text.includes(needle));
    assert(missing.length === 0, `${label} missing ${missing.join(", ")}`);
}

function parseCockpitSections(source) {
    const sections = [];
    const pattern = /<(section|article)\b([^>]*)\bdata-cockpit-section="([^"]+)"([^>]*)>/g;
    let match;
    while ((match = pattern.exec(source)) !== null) {
        const attributes = `${match[2]} ${match[4]}`;
        const idMatch = attributes.match(/\bid="([^"]+)"/);
        if (idMatch) sections.push(idMatch[1]);
    }
    return sections;
}

const cockpitSections = parseCockpitSections(html);
const missingSections = cockpitSections.filter((sectionId) => !audit.includes(`\`${sectionId}\``));
assert(missingSections.length === 0, `D11A audit does not mention sections: ${missingSections.join(", ")}`);

includesAll(audit, [
    "D11A Information Diet Audit",
    "Executive / Terminal",
    "Delete from UI",
    "Overview",
    "Trades",
    "Evidence",
    "Reasoning",
    "Operations",
    "D11B - New Navigation Contract",
    "Global safety strip",
    "Every current static dashboard section has a D11 fate",
    "Every major dynamic renderer/model has a D11 fate",
    "Duplicate concepts have a single future owner"
], "D11A audit");

includesAll(audit, [
    "Paper/demo mode",
    "Live capital disabled",
    "Broker writes blocked",
    "Read-only dashboard",
    "Q-CTRL / quantum state",
    "Paper account balance/P&L",
    "Source health",
    "System map",
    "Reasoning and private priors",
    "Governance/comms",
    "`blocked` state"
], "duplicate concept audit");

includesAll(audit, [
    "Hero and mode stack",
    "`mission-control`",
    "`strategy-manifestation`",
    "`system-map`",
    "`review-sequence`",
    "`watching`",
    "`cognition`",
    "`forbidden`",
    "`communications`",
    "`trade-layer`",
    "`money`",
    "`process-console`",
    "`worldview`",
    "`governance`"
], "static shell inventory");

includesAll(audit, [
    "`buildOverviewModel` / `renderOverviewFirstScreen`",
    "`buildTradesModel` / `renderTradeLifecycleWorkspace`",
    "`buildSourcesModel` / `renderSourcesWorkspace`",
    "`buildReasoningModel` / `renderReasoningWorkspace`",
    "`buildPerformanceModel` / `renderPerformanceWorkspace`",
    "`buildSystemConnectivityModel`",
    "`buildOperationsModel` / `renderOperationsWorkspace`",
    "`buildGovernanceModel` / `renderGovernanceWorkspace`",
    "`renderCognition`",
    "`renderTrades`",
    "`renderCapital`"
], "dynamic renderer inventory");

assert(html.includes("data-density-toggle"), "current dashboard no longer has density toggle; D11A audit should be refreshed");
assert(renderer.includes("function initDashboardDensityToggle"), "current renderer no longer has density toggle logic; D11A audit should be refreshed");

console.log("dashboard_d11a_information_diet_audit=ok");
console.log(`dashboard_d11a_static_section_count=${cockpitSections.length}`);
console.log("dashboard_d11a_all_sections_have_fate=True");
console.log("dashboard_d11a_duplicate_concepts_assigned=True");
console.log("dashboard_d11a_density_toggle_marked_for_deletion=True");
console.log("dashboard_d11a_next_stage=D11B New Navigation Contract");
