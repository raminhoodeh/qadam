#!/usr/bin/env node

const fs = require("node:fs");
const path = require("node:path");

const repoRoot = path.resolve(__dirname, "..");
const siteRoot = path.resolve(
    process.env.QADAM_DASHBOARD_SITE_ROOT || path.join(repoRoot, "landing-page-repo")
);
const contract = JSON.parse(fs.readFileSync(path.join(repoRoot, "docs/qadam-documentation-contract.json"), "utf8"));
const guideHtmlPath = path.join(siteRoot, "guide", "index.html");
const guideDocPath = path.join(repoRoot, contract.canonical_sources.user_guide);
const dashboardHtmlPath = path.join(siteRoot, "dashboard", "index.html");
const authPath = path.join(siteRoot, "auth.js");

const guideHtml = fs.readFileSync(guideHtmlPath, "utf8");
const guideDoc = fs.readFileSync(guideDocPath, "utf8");
const dashboardHtml = fs.readFileSync(dashboardHtmlPath, "utf8");
const auth = fs.readFileSync(authPath, "utf8");

function assert(condition, message) {
    if (!condition) throw new Error(message);
}

function plainText(source) {
    return source
        .replace(/&amp;/g, "&")
        .replace(/&rarr;|&#8594;/g, "→")
        .replace(/&#39;|&apos;/g, "'")
        .replace(/<script\b[^>]*>[\s\S]*?<\/script>/gi, " ")
        .replace(/<style\b[^>]*>[\s\S]*?<\/style>/gi, " ")
        .replace(/<[^>]+>/g, " ")
        .replace(/[`*_#|>-]/g, " ")
        .replace(/\s+/g, " ")
        .trim();
}

function includesNormalized(source, needle) {
    return plainText(source).toLowerCase().includes(plainText(needle).toLowerCase());
}

function includesAll(source, needles, label) {
    for (const needle of needles) {
        assert(includesNormalized(source, needle), `${label} missing: ${needle}`);
    }
}

function assertNoUnsafePublicText(source, label) {
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
        /GEMINI_API_KEY=/,
    ].forEach((pattern) => assert(!pattern.test(source), `${label} contains unsafe public text: ${pattern}`));
}

[
    '<body class="qadam-guide-page">',
    "How To Use Qadam",
    "data-dashboard",
    "hidden",
    "/auth.js?v=20260517-guide",
    "/dashboard/",
].forEach((needle) => assert(guideHtml.includes(needle), `guide HTML shell missing: ${needle}`));
[
    "data-user-email",
    "data-signout",
    "Signed in as",
    "Document version:",
].forEach((needle) => assert(!guideHtml.includes(needle), `guide HTML retains removed account chrome: ${needle}`));
assert(dashboardHtml.includes('href="/guide/"'), "dashboard navigation is missing the User Guide link");

includesAll(auth, [
    "function dashboardIsPublicReadOnly()",
    'document.body?.classList.contains("qadam-dashboard-page")',
    'const dashboard = document.querySelector("[data-dashboard]")',
    'emailTarget.textContent = session?.user?.email || "public read-only visitor"',
    "emailIsAllowed(session.user.email)",
    "window.location.replace(`/login/?next=${encodeURIComponent(currentPath)}`)",
], "access-control implementation");

const routeLabels = contract.dashboard_routes.map((route) => route.label);
const lifecycleLabels = contract.lifecycle.map((stage) => stage.label);
const sharedGuideTerms = [
    ...routeLabels,
    ...lifecycleLabels,
    ...contract.decision_room_sequence,
    ...contract.quantum_edge_sequence,
    ...contract.system_overview_disclosures,
    ...Object.keys(contract.learn_improve_questions),
    ...Object.values(contract.learn_improve_questions),
    "public read-only",
    "protected member features",
    "Akber pass",
    "research eligibility",
    "not approval",
    "Alpaca Paper",
    "paper proof ledger",
    "no-trade rationale",
    "live capital",
    "outbound",
    "inbound",
    "read-only research intake",
];
includesAll(guideDoc, sharedGuideTerms, "canonical guide Markdown");
includesAll(guideHtml, sharedGuideTerms, "published guide");

includesAll(guideDoc, [
    "Canonical source",
    "Current counts",
    "Appendix A: Operator-Only Procedures",
    contract.operator_workflows.paperops_pass,
    "The retired `run_phase7_demo_proof_harness.py` routine is not the canonical",
], "canonical guide maintenance contract");

[
    ".venv/bin/python scripts/run_phase7_demo_proof_harness.py",
    "the paper-live control plane is certified",
    "IBM Quantum token/instance configuration before device probing",
    "Open Watching",
    "Open Cognition",
    "Open Worldview",
    "Open Trade Layer",
    "Open Money",
    "Open Forbidden",
    "Start with Mission Control",
].forEach((needle) => {
    assert(!guideDoc.includes(needle), `canonical guide retains stale instruction: ${needle}`);
    assert(!guideHtml.includes(needle), `published guide retains stale instruction: ${needle}`);
});

assertNoUnsafePublicText(guideDoc, "canonical guide Markdown");
assertNoUnsafePublicText(guideHtml, "published guide");

console.log("protected_user_guide=ok");
console.log(`guide_html=${guideHtmlPath}`);
console.log(`canonical_source=${guideDocPath}`);
console.log(`dashboard_route_count=${contract.dashboard_routes.length}`);
console.log(`lifecycle_stage_count=${contract.lifecycle.length}`);
