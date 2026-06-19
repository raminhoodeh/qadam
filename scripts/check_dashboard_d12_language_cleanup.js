#!/usr/bin/env node

const fs = require("node:fs");
const path = require("node:path");

const {
    assert,
    html,
    renderWithStatus,
    status
} = require("./check_dashboard_renderer.js");

const repoRoot = path.resolve(__dirname, "..");
const dashboardHtmlPath = path.join(repoRoot, "landing-page-repo", "dashboard", "index.html");
const guideHtmlPath = path.join(repoRoot, "landing-page-repo", "guide", "index.html");
const guideDocPath = path.join(repoRoot, "docs", "qadam-user-guide.md");
const rendererPath = path.join(repoRoot, "landing-page-repo", "dashboard.js");
const planPath = path.join(repoRoot, "docs", "qadam-dashboard-overhaul-master-implementation-plan.md");
const auditPath = path.join(repoRoot, "docs", "qadam-dashboard-d12-language-cleanup-2026-05-26.md");

const dashboardHtml = fs.readFileSync(dashboardHtmlPath, "utf8");
const guideHtml = fs.readFileSync(guideHtmlPath, "utf8");
const guideDoc = fs.readFileSync(guideDocPath, "utf8");
const renderer = fs.readFileSync(rendererPath, "utf8");
const plan = fs.readFileSync(planPath, "utf8");
const audit = fs.readFileSync(auditPath, "utf8");

function includesAll(text, needles, label) {
    needles.forEach((needle) => {
        assert(text.includes(needle), `${label} missing ${needle}`);
    });
}

function textOnly(htmlText) {
    return String(htmlText)
        .replace(/<script[\s\S]*?<\/script>/g, " ")
        .replace(/<style[\s\S]*?<\/style>/g, " ")
        .replace(/<[^>]+>/g, " ")
        .replace(/&pound;/g, "£")
        .replace(/&amp;/g, "&")
        .replace(/\s+/g, " ")
        .trim();
}

function assertNoSlop(text, label) {
    [
        "Qadam cockpit - D9 secure bridge",
        "D9 operating cockpit",
        "System Operating Map",
        "hedge fund team inside a laptop",
        "sources feed the COO",
        "Fund manager operating view",
        "Single safety strip",
        "No UI-to-broker path",
        "No LLM-to-broker path",
        "No proof-credit inference",
        "The shortest answer before deeper review.",
        "Current answer, next focus, compact map.",
        "Reading rule",
        "Fund Manager read",
        "public-safe cockpit snapshot",
        "Loading candidate state",
        "Strategy manifestation",
        "Phase 4 status, approval gate, and shadow-only strategy toggles",
        "Approved-shadow toggles",
        "Ideas become paper states"
    ].forEach((needle) => {
        assert(!text.includes(needle), `${label} still includes slop term: ${needle}`);
    });
}

function assertNoSecretMaterial(text, label) {
    [
        /\b[A-Za-z0-9_-]{12,}\.[A-Za-z0-9_-]{20,}\.[A-Za-z0-9_-]{20,}\b/,
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
        assert(!pattern.test(text), `${label} contains secret-like material: ${pattern}`);
    });
}

async function main() {
    includesAll(dashboardHtml, [
        "<title>Qadam Dashboard</title>",
        "/auth.css?v=20260619-dashboard-polish",
        "/dashboard.js?v=20260619-dashboard-polish",
        "Qadam paper trading dashboard",
        "Mission Control",
        "Safety status",
        "Paper-only monitoring. Live capital is off; order authority stays behind runtime gates.",
        "60-day paper growth trial",
        "Control Plane",
        "Paper Account &amp; Trade State",
        "Loading account and trade lifecycle"
    ], "D12 dashboard shell");

    includesAll(renderer, [
        "Order authority remains behind runtime gates",
        "Paper growth maturity requires verified records",
        "This is read-only mission control",
        "What Qadam is choosing now",
        "buildFounderContractModel",
        "Trade ideas",
        "Python records the system"
    ], "D12 renderer copy");

    includesAll(`${guideHtml}\n${guideDoc}`, [
        "Safety Status",
        "paper-only monitoring",
        "live capital off"
    ], "D12 guide copy");

    includesAll(`${plan}\n${audit}`, [
        "D12 - Dashboard Language And Meaning Cleanup",
        "scripts/check_dashboard_d12_language_cleanup.js",
        "docs/qadam-dashboard-d12-language-cleanup-2026-05-26.md"
    ], "D12 plan and audit");

    const shellText = textOnly(dashboardHtml);
    assertNoSlop(shellText, "D12 dashboard text");

    const rendered = await renderWithStatus(status);
    const overviewText = [
        html(rendered, "[data-dashboard-safety-strip]"),
        html(rendered, "[data-overview-mission-brief]"),
        html(rendered, "[data-overview-strategy-narrative]"),
        html(rendered, "[data-overview-paper-trade-state]"),
        html(rendered, "[data-overview-source-summary]"),
        html(rendered, "[data-overview-control-plane]")
    ].map(textOnly).join(" ");

    includesAll(overviewText, [
        "Order authority remains behind runtime gates",
        "Paper Account & Trade State",
        "Realized",
        "Unrealized",
        "Mission Snapshot",
        "Durable replay",
        "authority stops",
        "only guarded paper checks",
        "Trade state",
        "Trade ideas stay candidates"
    ], "D12 rendered overview");
    assertNoSlop(overviewText, "D12 rendered overview");

    assertNoSecretMaterial(dashboardHtml, "D12 dashboard HTML");
    assertNoSecretMaterial(renderer, "D12 dashboard renderer");
    assertNoSecretMaterial(guideHtml, "D12 guide HTML");
    assertNoSecretMaterial(guideDoc, "D12 guide doc");

    console.log("dashboard_d12_language_cleanup=ok");
    console.log("dashboard_d12_cache_key=20260619-dashboard-polish");
    console.log("dashboard_d12_default_copy_plain=True");
    console.log("dashboard_authority_unchanged=True");
}

main().catch((error) => {
    console.error(error.message);
    process.exitCode = 1;
});
