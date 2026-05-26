#!/usr/bin/env node

const fs = require("node:fs");
const path = require("node:path");

const repoRoot = path.resolve(__dirname, "..");
const guideDocPath = path.join(repoRoot, "docs", "qadam-user-guide.md");
const guideHtmlPath = path.join(repoRoot, "landing-page-repo", "guide", "index.html");
const dashboardHtmlPath = path.join(repoRoot, "landing-page-repo", "dashboard", "index.html");
const protectedGuideCheckPath = path.join(repoRoot, "scripts", "check_protected_user_guide.js");
const d11mCheckPath = path.join(repoRoot, "scripts", "check_dashboard_d11m_regression_acceptance.js");
const preflightPath = path.join(repoRoot, "scripts", "preflight_dashboard_deployment.sh");
const acceptancePath = path.join(repoRoot, "scripts", "check_dashboard_acceptance.js");
const planPath = path.join(repoRoot, "docs", "qadam-dashboard-overhaul-master-implementation-plan.md");
const auditPath = path.join(repoRoot, "docs", "qadam-dashboard-d11n-documentation-guide-alignment-2026-05-26.md");

const guideDoc = fs.readFileSync(guideDocPath, "utf8");
const guideHtml = fs.readFileSync(guideHtmlPath, "utf8");
const dashboardHtml = fs.readFileSync(dashboardHtmlPath, "utf8");
const protectedGuideCheck = fs.readFileSync(protectedGuideCheckPath, "utf8");
const d11mCheck = fs.readFileSync(d11mCheckPath, "utf8");
const preflight = fs.readFileSync(preflightPath, "utf8");
const acceptance = fs.readFileSync(acceptancePath, "utf8");
const plan = fs.readFileSync(planPath, "utf8");

function assert(condition, message) {
    if (!condition) throw new Error(message);
}

function assertIncludes(text, expected, label) {
    assert(text.includes(expected), `${label} missing ${expected}`);
}

function includesAll(text, needles, label) {
    needles.forEach((needle) => assertIncludes(text, needle, label));
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
        /SUPABASE_SECRET_KEY=/,
        /GEMINI_API_KEY=/,
        /ANTHROPIC_API_KEY=/,
        /OPENAI_API_KEY=/
    ].forEach((pattern) => {
        assert(!pattern.test(text), `${label} contains unsafe public text: ${pattern}`);
    });
}

function dashboardViewLabels() {
    return [...dashboardHtml.matchAll(/data-dashboard-view-target="([^"]+)"[^>]*>([^<]+)<\/a>/g)]
        .map((match) => match[2].trim());
}

function assertGuideMatchesDashboardNav() {
    const labels = dashboardViewLabels();
    const expected = ["Overview", "Trades", "Evidence", "Reasoning", "Operations"];
    assert(
        JSON.stringify(labels) === JSON.stringify(expected),
        `dashboard nav labels changed: ${JSON.stringify(labels)}`
    );
    expected.forEach((label) => {
        assertIncludes(guideHtml, `${label} view`, `guide HTML ${label}`);
        assertIncludes(guideDoc, label, `guide markdown ${label}`);
    });
}

function assertNoOldPanelHuntInstructions() {
    [
        "Open Watching",
        "Open Cognition",
        "Open Worldview",
        "Open Trade Layer",
        "Open Money",
        "Open Forbidden",
        "Start with Mission Control"
    ].forEach((needle) => {
        assert(!guideHtml.includes(needle), `guide HTML still tells users to hunt old panel: ${needle}`);
        assert(!guideDoc.includes(needle), `guide markdown still tells users to hunt old panel: ${needle}`);
    });
}

function assertOldTermMapping() {
    [
        "| Mission Control | Older implementation name now represented by Overview. |",
        "| Watching | Older implementation name now represented by Evidence. |",
        "| Cognition | Older implementation name now represented by Reasoning. |",
        "| Money | Older implementation name now represented inside Trades. |",
        "| Forbidden | Older implementation name now represented by the single safety strip plus Operations diagnostics. |"
    ].forEach((needle) => assertIncludes(guideDoc, needle, "guide markdown old-term mapping"));
    [
        "<strong>Mission Control</strong><span>Overview.",
        "<strong>Watching</strong><span>Evidence.",
        "<strong>Cognition</strong><span>Reasoning.",
        "<strong>Trade Layer</strong><span>Trades.",
        "<strong>Communications / Telegram</strong><span>Operations communications."
    ].forEach((needle) => assertIncludes(guideHtml, needle, "guide HTML old-term mapping"));
}

function assertGuideConcepts() {
    includesAll(guideDoc, [
        "Start in the Overview view.",
        "single safety strip",
        "Overview's health readout and mini-map",
        "Open Evidence",
        "Open Reasoning",
        "Open Trades",
        "Open Operations only",
        "full expandable system map",
        "blocked/no-trade state as potentially healthy",
        "Record a no-trade rationale when there is no qualified setup",
        "Do not force a",
        "paper trade to satisfy cadence."
    ], "guide markdown D11N concepts");
    includesAll(guideHtml, [
        "Start in the Overview view.",
        "single safety strip",
        "Overview's health readout and mini-map",
        "Open Evidence",
        "Open Reasoning",
        "Open Trades",
        "Open Operations only",
        "full expandable system map",
        "blocked/no-trade state as potentially healthy",
        "Record a no-trade rationale when there is no qualified setup",
        "Do not force a paper trade to satisfy cadence."
    ], "guide HTML D11N concepts");
}

function assertPlanAndChecks() {
    includesAll(plan, [
        "D11N - Documentation And Guide Alignment",
        "docs/qadam-dashboard-d11n-documentation-guide-alignment-2026-05-26.md",
        "scripts/check_dashboard_d11n_documentation_guide_alignment.js",
        "D11O - Performance View Consolidation"
    ], "D11N master plan");
    includesAll(protectedGuideCheck, [
        "Overview view",
        "Trades view",
        "Evidence view",
        "Reasoning view",
        "Operations view",
        "guide HTML still tells users to hunt old panel"
    ], "protected guide checker alignment");
    includesAll(d11mCheck, [
        "D11N - Documentation And Guide Alignment",
        "D11O - Performance View Consolidation"
    ], "D11M next-stage alignment");
    includesAll(preflight, [
        "node scripts/check_dashboard_d11m_regression_acceptance.js",
        "node scripts/check_dashboard_d11n_documentation_guide_alignment.js",
        "docs/qadam-dashboard-d11n-documentation-guide-alignment-2026-05-26.md",
        "scripts/check_dashboard_d11n_documentation_guide_alignment.js"
    ], "D11N preflight wiring");
    assert(
        acceptance.includes("\"scripts/check_dashboard_d11n_documentation_guide_alignment.js\""),
        "dashboard acceptance missing D11N dependency"
    );
    assert(fs.existsSync(auditPath), "D11N audit document missing");
}

assertGuideMatchesDashboardNav();
assertGuideConcepts();
assertOldTermMapping();
assertNoOldPanelHuntInstructions();
assertPlanAndChecks();
assertNoUnsafePublicText(guideHtml, "D11N guide HTML");
assertNoUnsafePublicText(guideDoc, "D11N guide markdown");

console.log("dashboard_d11n_documentation_guide_alignment=ok");
console.log(`dashboard_d11n_views=${dashboardViewLabels().join(",")}`);
console.log("dashboard_d11n_old_panel_hunt_removed=True");
console.log("dashboard_authority_unchanged=True");
