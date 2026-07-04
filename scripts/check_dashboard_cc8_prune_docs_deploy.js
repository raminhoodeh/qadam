#!/usr/bin/env node

const fs = require("node:fs");
const path = require("node:path");

const repoRoot = path.resolve(__dirname, "..");
const statusPath = path.join(repoRoot, "landing-page-repo", "status", "cockpit-status.json");
const exporterPath = path.join(repoRoot, "orchestrator", "cockpit_status.py");
const checkerPath = path.join(repoRoot, "scripts", "check_cockpit_status.py");
const guideHtmlPath = path.join(repoRoot, "landing-page-repo", "guide", "index.html");
const guideDocPath = path.join(repoRoot, "docs", "qadam-user-guide.md");
const whitepaperPath = path.join(repoRoot, "landing-page-repo", "whitepaper", "index.html");
const dashboardHtmlPath = path.join(repoRoot, "landing-page-repo", "dashboard", "index.html");
const preflightPath = path.join(repoRoot, "scripts", "preflight_dashboard_deployment.sh");
const planPath = path.join(repoRoot, "docs", "qadam-dashboard-consolidation-cut-implementation-plan-2026-06-05.md");

const status = JSON.parse(fs.readFileSync(statusPath, "utf8"));
const exporter = fs.readFileSync(exporterPath, "utf8");
const checker = fs.readFileSync(checkerPath, "utf8");
const guideHtml = fs.readFileSync(guideHtmlPath, "utf8");
const guideDoc = fs.readFileSync(guideDocPath, "utf8");
const whitepaper = fs.readFileSync(whitepaperPath, "utf8");
const dashboardHtml = fs.readFileSync(dashboardHtmlPath, "utf8");
const preflight = fs.readFileSync(preflightPath, "utf8");
const plan = fs.readFileSync(planPath, "utf8");

function assert(condition, message) {
    if (!condition) throw new Error(message);
}

function includesAll(text, needles, label) {
    needles.forEach((needle) => assert(text.includes(needle), `${label} missing ${needle}`));
}

function assertPublicSafe(text, label) {
    [
        /\/Users\//,
        /\/private\//,
        /\d{6,}:[A-Za-z0-9_-]{20,}/,
        /ghp_[A-Za-z0-9_]{20,}/,
        /sk-[A-Za-z0-9_-]{20,}/,
        /GEMINI_API_KEY=/,
        /SUPABASE_SECRET_KEY=/,
        /TELEGRAM_BOT_TOKEN=/
    ].forEach((pattern) => assert(!pattern.test(text), `${label} contains unsafe text: ${pattern}`));
}

const pruneCandidates = status.diagnostics?.prune_candidates || [];
const pruneAudit = status.diagnostics?.prune_audit || {};
const retained = pruneAudit.retained_top_level_keys || [];

assert(status.diagnostics?.status === "diagnostics_available", "diagnostics status mismatch");
assert(Array.isArray(pruneCandidates) && pruneCandidates.length > 0, "prune candidates missing");
assert(pruneAudit.status === "retained_due_to_active_dependencies", "prune audit status mismatch");
assert(pruneAudit.safe_to_remove_count === 0, "safe-to-remove count must remain zero until migration proof exists");
assert(Array.isArray(pruneAudit.safe_to_remove_keys) && pruneAudit.safe_to_remove_keys.length === 0, "safe-to-remove keys must be empty");
assert(pruneAudit.candidate_count === pruneCandidates.length, "prune audit candidate count mismatch");
assert(pruneAudit.retained_count === retained.length, "prune audit retained count mismatch");
assert(
    JSON.stringify(retained.map((entry) => entry.key)) === JSON.stringify(pruneCandidates),
    "retained key list must match prune_candidates"
);
retained.forEach((entry) => {
    assert(entry.migration_status === "retained_for_checker_and_diagnostics_compatibility", `bad migration status for ${entry.key}`);
    assert(entry.retention_reason, `retention reason missing for ${entry.key}`);
    assert(Array.isArray(entry.dependent_surfaces) && entry.dependent_surfaces.length >= 3, `dependent surfaces missing for ${entry.key}`);
    assert(entry.namespace_shadow === `diagnostics.audit_sections.${entry.key}`, `namespace shadow mismatch for ${entry.key}`);
});

includesAll(exporter, [
    "def _diagnostic_dependent_surfaces",
    "\"prune_audit\"",
    "\"retained_due_to_active_dependencies\"",
    "retained_for_checker_and_diagnostics_compatibility"
], "cockpit status exporter");
includesAll(checker, [
    "\"prune_audit\"",
    "cockpit_status_diagnostics_prune_audit_status_mismatch",
    "cockpit_status_diagnostics_prune_audit_safe_remove_without_proof"
], "cockpit status checker");

includesAll(guideHtml, [
    "Founder Decision Blocks",
    "Portfolio",
    "History",
    "Sources",
    "Strategy",
    "Patterns",
    "Thinking",
    "Control",
    "Diagnostics are not a seventh operating block"
], "guide HTML");
includesAll(guideDoc, [
    "Founder Decision Blocks",
    "Portfolio",
    "History",
    "Sources",
    "Strategy",
    "Patterns",
    "Thinking",
    "Control",
    "Diagnostics are not a seventh operating block"
], "guide markdown");
assert(!guideHtml.includes("five primary views"), "guide HTML still mentions old five-primary-view IA");
assert(!guideDoc.includes("five primary views"), "guide markdown still mentions old five-primary-view IA");

includesAll(whitepaper, [
    "Portfolio value first",
    "Data source posture",
    "Strategy universe",
    "Pattern and opportunity lab",
    "Trade intents and PaperOps",
    "Research and reasoning",
    "Worldview as prior",
    "Audit drawer",
    "How Qadam Finds Edge Over Time",
    "edge is not one signal",
    "Evidence repeats before repricing",
    "quantum/classical review",
    "Alpaca Paper",
    "Postmortem"
], "whitepaper How To Use section");

includesAll(dashboardHtml, [
    "/auth.css?v=20260704-pattern-workflow-v1",
    "/dashboard.js?v=20260704-pattern-workflow-v1"
], "dashboard cache key");
includesAll(preflight, [
    "node scripts/check_dashboard_cc8_prune_docs_deploy.js",
    "scripts/check_dashboard_cc8_prune_docs_deploy.js"
], "preflight wiring");
includesAll(plan, [
    "CC8",
    "Prune payload, tests, docs, deploy",
    "prune_audit",
    "20260704-pattern-workflow-v1"
], "CC8 plan");

assertPublicSafe(guideHtml, "guide HTML");
assertPublicSafe(guideDoc, "guide markdown");
assertPublicSafe(whitepaper, "whitepaper");

console.log("dashboard_cc8_prune_docs_deploy=ok");
console.log(`dashboard_cc8_prune_candidate_count=${pruneCandidates.length}`);
console.log(`dashboard_cc8_retained_top_level_key_count=${retained.length}`);
