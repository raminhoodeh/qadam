#!/usr/bin/env node

const fs = require("node:fs");
const path = require("node:path");

const repoRoot = path.resolve(__dirname, "..");
const guideDocPath = path.join(repoRoot, "docs", "qadam-user-guide.md");
const guideHtmlPath = path.join(repoRoot, "landing-page-repo", "guide", "index.html");
const dashboardHtmlPath = path.join(repoRoot, "landing-page-repo", "dashboard", "index.html");
const dashboardJsPath = path.join(repoRoot, "landing-page-repo", "dashboard.js");
const protectedGuideCheckPath = path.join(repoRoot, "scripts", "check_protected_user_guide.js");
const d11mCheckPath = path.join(repoRoot, "scripts", "check_dashboard_d11m_regression_acceptance.js");
const preflightPath = path.join(repoRoot, "scripts", "preflight_dashboard_deployment.sh");
const acceptancePath = path.join(repoRoot, "scripts", "check_dashboard_acceptance.js");
const planPath = path.join(repoRoot, "docs", "qadam-dashboard-overhaul-master-implementation-plan.md");
const auditPath = path.join(repoRoot, "docs", "qadam-dashboard-d11n-documentation-guide-alignment-2026-05-26.md");

const guideDoc = fs.readFileSync(guideDocPath, "utf8");
const guideHtml = fs.readFileSync(guideHtmlPath, "utf8");
const dashboardHtml = fs.readFileSync(dashboardHtmlPath, "utf8");
const dashboardJs = fs.readFileSync(dashboardJsPath, "utf8");
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
    const viewsBlock = dashboardJs.match(/const QSASE_DASHBOARD_NAVIGATION = \[([\s\S]*?)\];\nconst QSASE_ROUTE_INDEX/)?.[1] || "";
    const grouped = [...viewsBlock.matchAll(/\{\s*id:\s*"[^"]+",\s*label:\s*"([^"]+)"\s*\}/g)]
        .map((match) => match[1].trim());
    return ["Qadam Team", ...grouped];
}

function assertGuideMatchesDashboardNav() {
    const labels = dashboardViewLabels();
    const expected = [
        "Qadam Team",
        "Portfolio",
        "Timeline",
        "Data Sources",
        "Trading Universe",
        "Pattern Recognition",
        "Quantum Edge",
        "Trading Strategies",
        "Decision Room",
        "Order Monitor",
        "Results & Lessons",
        "Tests & Improvements",
        "System Overview"
    ];
    assert(
        JSON.stringify(labels) === JSON.stringify(expected),
        `dashboard nav labels changed: ${JSON.stringify(labels)}`
    );
    expected.forEach((label) => {
        assertIncludes(guideHtml, label.replaceAll("&", "&amp;"), `guide HTML ${label}`);
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
        "| Mission Control | Older implementation name now represented by the QSASE Overview dashboard. |",
        "| Watching | Older implementation name now represented by Evidence. |",
        "| Cognition | Older implementation name now represented by Reasoning. |",
        "| Money | Older implementation name now represented by Portfolio and Timeline. |",
        "| Forbidden | Older implementation name now represented by Safety Status plus Operations diagnostics. |"
    ].forEach((needle) => assertIncludes(guideDoc, needle, "guide markdown old-term mapping"));
    [
        "<strong>Mission Control</strong><span>Legacy name. Read it now as the QSASE Overview dashboard.",
        "<strong>Watching</strong><span>Evidence.",
        "<strong>Cognition</strong><span>Reasoning.",
        "<strong>Money / Paper Account Timeline</strong><span>Portfolio and Timeline.",
        "<strong>Forbidden</strong><span>Operations safety diagnostics plus Safety Status."
    ].forEach((needle) => assertIncludes(guideHtml, needle, "guide HTML old-term mapping"));
}

function assertGuideConcepts() {
    includesAll(guideDoc, [
        "Start in Portfolio, the default page",
        "Qadam Team",
        "pinned above Fund",
        "Safety Status",
        "System Overview sits at the bottom",
        "Every dashboard page is a readout, not a command surface",
        "Every module starts with the same 10-stage lifecycle",
        "QSASE Dashboard Sections",
        "Portfolio",
        "Timeline",
        "composition by asset or market sleeve",
        "gross and net exposure",
        "P&L contribution",
        "Data Sources",
        "Trading Universe",
        "Trading Strategies",
        "Pattern Recognition",
        "Quantum Edge",
        "Decision Room",
        "Current Fund Position",
        "Research Ideas Approaching Decision",
        "Ready for Decision Room",
        "Previous Decision Reviews",
        "Akber's Multi-Stage Decision-Making Filter",
        "The practical questions and auditable lifecycle are one six-stage explanation",
        "Lifecycle Health by Stage",
        "Health by Domain",
        "Technical Diagnostics",
        "How Qadam Finds And Acts On Edge",
        "edge memory ledger",
        "daily Telegram learning brief",
        "weekly thesis refresh",
        "Alpaca Paper",
        "paper evaluation window",
        "paper proof ledger",
        "Qadam Self-Aware Strategy Engine",
        "Advanced / Debug Mode",
        "hidden chain-of-thought",
        "blocked or no-trade state as potentially healthy",
        "Record a no-trade rationale when there is no qualified setup",
        "Do not force a",
        "paper trade to satisfy cadence."
    ], "guide markdown D11N concepts");
    includesAll(guideHtml, [
        "Start in Portfolio, the default page",
        "Qadam Team",
        "pinned above Fund",
        "Safety Status",
        "System Overview sits at the bottom",
        "Every module uses the same 10-stage lifecycle map",
        "QSASE Dashboard Sections",
        "Portfolio",
        "Timeline",
        "composition by asset or market sleeve",
        "gross and net exposure",
        "P&amp;L contribution",
        "Data Sources",
        "Trading Universe",
        "Trading Strategies",
        "Pattern Recognition",
        "Quantum Edge",
        "Decision Room",
        "Current Fund Position",
        "Research Ideas Approaching Decision",
        "Ready for Decision Room",
        "Previous Decision Reviews",
        "Akber's Multi-Stage Decision-Making Filter",
        "The practical questions and auditable lifecycle are one six-stage explanation",
        "Lifecycle Health by Stage",
        "Health by Domain",
        "Technical Diagnostics",
        "How Qadam Finds And Acts On Edge",
        "edge memory ledger",
        "daily Telegram learning brief",
        "weekly thesis refresh",
        "Alpaca Paper",
        "paper evaluation window",
        "paper proof ledger",
        "Qadam Self-Aware Strategy Engine",
        "Advanced / Debug Mode",
        "hidden chain-of-thought",
        "blocked or no-trade state as potentially healthy",
        "Record a no-trade rationale when there is no qualified setup",
        "Do not force a paper trade to satisfy cadence."
    ], "guide HTML D11N concepts");
    [
        "The original six trading questions",
        "How Qadam makes those questions auditable",
        "Qadam preserves those questions and turns them into six auditable lifecycle stages"
    ].forEach((oldHeading) => {
        assert(!guideDoc.includes(oldHeading), `guide markdown retains split Akber explanation: ${oldHeading}`);
        assert(!guideHtml.includes(oldHeading), `guide HTML retains split Akber explanation: ${oldHeading}`);
    });
    const akberGuideHtml = guideHtml.slice(
        guideHtml.indexOf("<h2>Akber's Multi-Stage Decision-Making Filter</h2>"),
        guideHtml.indexOf("<h2>How Qadam Finds And Acts On Edge</h2>")
    );
    const akberGuideDoc = guideDoc.slice(
        guideDoc.indexOf("## 13. Akber's Multi-Stage Decision-Making Filter"),
        guideDoc.indexOf("## 14. How To Review A Trade Idea")
    );
    assert((akberGuideHtml.match(/class="guide-table"/g) || []).length === 1, "guide HTML Akber section must contain one merged table");
    assert((akberGuideHtml.match(/<div><strong>[1-6]\. /g) || []).length === 6, "guide HTML Akber table must contain six merged rows");
    assert((akberGuideDoc.match(/^[1-6]\. \*\*/gm) || []).length === 6, "guide markdown Akber section must contain six merged stages");
}

function assertPlanAndChecks() {
    includesAll(plan, [
        "D11N - Documentation And Guide Alignment",
        "docs/qadam-dashboard-d11n-documentation-guide-alignment-2026-05-26.md",
        "scripts/check_dashboard_d11n_documentation_guide_alignment.js",
        "D11O - Deployment Discipline",
        "D11P - Performance View Consolidation"
    ], "D11N master plan");
    includesAll(protectedGuideCheck, [
        "Qadam Team",
        "System Overview",
        "Data Sources",
        "Trading Universe",
        "Trading Strategies",
        "QSASE Dashboard Sections",
        "Portfolio",
        "Decision Room",
        "guide HTML still tells users to hunt old panel"
    ], "protected guide checker alignment");
    includesAll(d11mCheck, [
        "D11N - Documentation And Guide Alignment",
        "D11O - Deployment Discipline",
        "D11P - Performance View Consolidation"
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
