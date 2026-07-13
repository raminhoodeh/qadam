#!/usr/bin/env node

const fs = require("node:fs");
const path = require("node:path");

const { assert } = require("./check_dashboard_renderer.js");

const repoRoot = path.resolve(__dirname, "..");
const deployScriptPath = path.join(repoRoot, "landing-page-repo", "scripts", "deploy-vercel-production.sh");
const preflightPath = path.join(repoRoot, "scripts", "preflight_dashboard_deployment.sh");
const readinessPath = path.join(repoRoot, "scripts", "check_dashboard_deployment_readiness.js");
const acceptancePath = path.join(repoRoot, "scripts", "check_dashboard_acceptance.js");
const planPath = path.join(repoRoot, "docs", "qadam-dashboard-overhaul-master-implementation-plan.md");
const auditPath = path.join(repoRoot, "docs", "qadam-dashboard-d11o-deployment-discipline-2026-05-26.md");

function readText(filePath) {
    return fs.readFileSync(filePath, "utf8");
}

function includesAll(text, needles, label) {
    needles.forEach((needle) => {
        assert(text.includes(needle), `${label} missing ${needle}`);
    });
}

function indexOfOrThrow(text, needle, label) {
    const index = text.indexOf(needle);
    assert(index >= 0, `${label} missing ${needle}`);
    return index;
}

function assertNoUnsafePublicText(text, label) {
    [
        /\b[A-Za-z0-9_-]{12,}\.[A-Za-z0-9_-]{20,}\.[A-Za-z0-9_-]{20,}\b/,
        /\d{6,}:[A-Za-z0-9_-]{20,}/,
        /sk-[A-Za-z0-9_-]{20,}/,
        /ghp_[A-Za-z0-9_]{20,}/,
        /PVZ[0-9A-Za-z_-]{20,}/,
        /VERCEL_TOKEN=[^\n]+/,
        /TELEGRAM_BOT_TOKEN=/,
        /SUPABASE_SECRET_KEY=/,
        /GEMINI_API_KEY=/,
        /ANTHROPIC_API_KEY=/,
        /OPENAI_API_KEY=/
    ].forEach((pattern) => {
        assert(!pattern.test(text), `${label} contains unsafe public text: ${pattern}`);
    });
}

function assertNoSecretMaterial(text, label) {
    [
        /\b[A-Za-z0-9_-]{12,}\.[A-Za-z0-9_-]{20,}\.[A-Za-z0-9_-]{20,}\b/,
        /\d{6,}:[A-Za-z0-9_-]{20,}/,
        /sk-[A-Za-z0-9_-]{20,}/,
        /ghp_[A-Za-z0-9_]{20,}/,
        /PVZ[0-9A-Za-z_-]{20,}/
    ].forEach((pattern) => {
        assert(!pattern.test(text), `${label} contains secret-like material: ${pattern}`);
    });
}

const deployScript = readText(deployScriptPath);
const preflight = readText(preflightPath);
const readiness = readText(readinessPath);
const acceptance = readText(acceptancePath);
const plan = readText(planPath);

includesAll(deployScript, [
    "bash \"${ROOT_DIR}/scripts/preflight_dashboard_deployment.sh\"",
    "QADAM_SKIP_DEPLOY_PREFLIGHT",
    "Deploying to Vercel production scope",
    "--prod",
    "--yes",
    "--scope \"${VERCEL_TEAM_ID}\"",
    "--token \"${VERCEL_TOKEN}\"",
    "\"qadam.trade\"",
    "\"www.qadam.trade\"",
    "deployment_url",
    "grep -Eo 'https://[^[:space:]]+\\.vercel\\.app'",
    "No production aliases were changed by this script and no deployment receipt was written.",
    "A Vercel deployment URL may exist, but this script did not complete all production aliases or write a receipt.",
    "dashboard-deployment-receipt.json",
    "preflight: \"passed\"",
    "Dashboard repository is dirty; production deployment is blocked.",
    "Production preflight cannot be skipped for a dashboard integration release.",
    "verify-dashboard-production-release.js",
    "Contains no Vercel token, session cookie, broker credential, or dashboard secret.",
    "send_codebase_upgrade_telegram_notification.py",
    "Codebase upgrade Telegram notification",
    "--live",
    "--source \"production_deploy\"",
    "--summary \"Qadam has been updated and the live dashboard is ready for review.\"",
    "Production deployment:",
    "Aliased domains:"
], "D11O deploy script");

[
    "--detail",
    "--benefit",
    "Fund Managers can see what changed and why it matters without checking Git",
    "The deploy hook now sends this group update after Vercel production aliases are updated"
].forEach((needle) => {
    assert(!deployScript.includes(needle), `D11O deploy script should not force verbose Telegram copy: ${needle}`);
});

const preflightIndex = indexOfOrThrow(deployScript, "bash \"${ROOT_DIR}/scripts/preflight_dashboard_deployment.sh\"", "D11O deploy order");
const deployIndex = indexOfOrThrow(deployScript, "\"${vercel_cmd[@]}\" deploy", "D11O deploy order");
const aliasIndex = indexOfOrThrow(deployScript, "\"${vercel_cmd[@]}\" alias set", "D11O deploy order");
const receiptIndex = indexOfOrThrow(deployScript, "dashboard-deployment-receipt.json", "D11O deploy order");
const successPrintIndex = indexOfOrThrow(deployScript, "Production deployment:", "D11O deploy order");
assert(preflightIndex < deployIndex, "preflight must run before Vercel deploy");
assert(deployIndex < aliasIndex, "aliases must happen after Vercel deploy");
assert(aliasIndex < receiptIndex, "receipt must be written after alias loop");
assert(receiptIndex < successPrintIndex, "success message must be printed after receipt path is defined");

includesAll(preflight, [
    "node scripts/check_dashboard_deployment_readiness.js",
    "scripts/check_codebase_upgrade_telegram_notification.py",
    "node --check scripts/check_dashboard_d11o_deployment_discipline.js",
    "node scripts/check_dashboard_d11o_deployment_discipline.js",
    "node scripts/check_protected_user_guide.js",
    "node scripts/check_dashboard_information_hierarchy.js",
    "node scripts/check_dashboard_overhaul_overview.js",
    "node scripts/check_dashboard_cc6_real_portfolio_timeline.js",
    "node scripts/check_dashboard_cc9_slop_repetition.js",
    "node scripts/check_dashboard_renderer.js",
    "node scripts/check_dashboard_live_bridge.js",
    "\"$PYTHON_BIN\" scripts/check_cockpit_status.py",
    "\"$PYTHON_BIN\" scripts/check_live_bridge.py",
    "docs/qadam-dashboard-d11o-deployment-discipline-2026-05-26.md",
    "scripts/check_dashboard_d11o_deployment_discipline.js"
], "D11O preflight wiring");

includesAll(readiness, [
    "landing-page-repo/scripts/deploy-vercel-production.sh",
    "scripts/preflight_dashboard_deployment.sh",
    "scripts/check_codebase_upgrade_telegram_notification.py",
    "scripts/check_dashboard_d11o_deployment_discipline.js",
    "docs/qadam-dashboard-d11o-deployment-discipline-2026-05-26.md",
    "Phase D10I - Deployment Discipline",
    "D11O - Deployment Discipline"
], "D11O deployment readiness");

assert(
    acceptance.includes("\"scripts/check_dashboard_d11o_deployment_discipline.js\""),
    "dashboard acceptance missing D11O dependency"
);

includesAll(plan, [
    "D11O - Deployment Discipline",
    "docs/qadam-dashboard-d11o-deployment-discipline-2026-05-26.md",
    "scripts/check_dashboard_d11o_deployment_discipline.js",
    "D12 - Dashboard Language And Meaning Cleanup"
], "D11O master plan");

assert(fs.existsSync(auditPath), "D11O audit document missing");
assertNoUnsafePublicText(deployScript, "D11O deploy script");
assertNoSecretMaterial(readiness, "D11O deployment readiness checker");
assertNoSecretMaterial(preflight, "D11O deployment preflight");

console.log("dashboard_d11o_deployment_discipline=ok");
console.log("dashboard_d11o_preflight_required=True");
console.log("dashboard_d11o_receipt_after_alias=True");
console.log("dashboard_d11o_live_deploy_attempted=False");
console.log("dashboard_authority_unchanged=True");
