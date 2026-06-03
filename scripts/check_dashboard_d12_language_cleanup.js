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
        "/auth.css?v=20260603-rs3-market-context",
        "/dashboard.js?v=20260603-rs3-market-context",
        "Qadam paper trading dashboard",
        "Paper Trading Overview",
        "Safety status",
        "Dashboard cannot place orders",
        "AI cannot bypass risk checks",
        "60-day paper growth trial",
        "How data becomes paper trade decisions",
        "Loading trade ideas"
    ], "D12 dashboard shell");

    includesAll(renderer, [
        "Dashboard cannot place orders",
        "AI cannot bypass risk checks",
        "Paper growth maturity requires verified records",
        "Use Safety Status for order authority",
        "Current summary",
        "Potential setups",
        "Trade ideas",
        "Python records the system"
    ], "D12 renderer copy");

    includesAll(`${guideHtml}\n${guideDoc}`, [
        "Safety Status",
        "Dashboard cannot place orders",
        "AI cannot bypass risk checks"
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
        html(rendered, "[data-overview-status-rail]"),
        html(rendered, "[data-overview-hero]"),
        html(rendered, "[data-overview-system-status]"),
        html(rendered, "[data-overview-paper-capacity]"),
        html(rendered, "[data-overview-data-sources]"),
        html(rendered, "[data-overview-trading-strategies]"),
        html(rendered, "[data-overview-thought-feed]"),
        html(rendered, "[data-overview-trade-considerations]"),
        html(rendered, "[data-overview-boundary-rail]")
    ].map(textOnly).join(" ");

    includesAll(overviewText, [
        "Dashboard cannot place orders",
        "AI cannot bypass risk checks",
        "toward £200,000",
        "Potential setups",
        "Current summary",
        "Trade ideas",
        "A trade idea is not an order"
    ], "D12 rendered overview");
    assertNoSlop(overviewText, "D12 rendered overview");

    assertNoSecretMaterial(dashboardHtml, "D12 dashboard HTML");
    assertNoSecretMaterial(renderer, "D12 dashboard renderer");
    assertNoSecretMaterial(guideHtml, "D12 guide HTML");
    assertNoSecretMaterial(guideDoc, "D12 guide doc");

    console.log("dashboard_d12_language_cleanup=ok");
    console.log("dashboard_d12_cache_key=20260603-rs3-market-context");
    console.log("dashboard_d12_default_copy_plain=True");
    console.log("dashboard_authority_unchanged=True");
}

main().catch((error) => {
    console.error(error.message);
    process.exitCode = 1;
});
