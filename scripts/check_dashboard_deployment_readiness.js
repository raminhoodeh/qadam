#!/usr/bin/env node

const fs = require("node:fs");
const path = require("node:path");

const { assert } = require("./check_dashboard_renderer.js");

const repoRoot = path.resolve(__dirname, "..");
const landingRoot = path.join(repoRoot, "landing-page-repo");
const projectPath = path.join(landingRoot, ".vercel", "project.json");
const ignorePath = path.join(landingRoot, ".vercelignore");
const deployScriptPath = path.join(landingRoot, "scripts", "deploy-vercel-production.sh");
const planPath = path.join(repoRoot, "docs", "qadam-dashboard-implementation-plan.md");
const localVercelEnvPath = path.join(repoRoot, "data", "runtime", "vercel.env");

function readText(filePath) {
    return fs.readFileSync(filePath, "utf8");
}

function assertIncludes(text, needle, label) {
    assert(text.includes(needle), `${label} missing ${needle}`);
}

function assertFile(relativePath) {
    const filePath = path.join(repoRoot, relativePath);
    assert(fs.existsSync(filePath), `deployment readiness missing ${relativePath}`);
}

function assertJson(relativePath) {
    const filePath = path.join(repoRoot, relativePath);
    JSON.parse(readText(filePath));
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

[
    "landing-page-repo/index.html",
    "landing-page-repo/login/index.html",
    "landing-page-repo/sign-up/index.html",
    "landing-page-repo/dashboard/index.html",
    "landing-page-repo/guide/index.html",
    "landing-page-repo/whitepaper/index.html",
    "landing-page-repo/auth.css",
    "landing-page-repo/auth.js",
    "landing-page-repo/dashboard.js",
    "landing-page-repo/status/cockpit-status.json",
    "landing-page-repo/status/cockpit-status.signature.json",
    "landing-page-repo/.vercel/project.json",
    "landing-page-repo/.vercelignore",
    "landing-page-repo/scripts/deploy-vercel-production.sh",
    "scripts/preflight_dashboard_deployment.sh",
    "scripts/check_codebase_upgrade_telegram_notification.py",
    "scripts/check_dashboard_acceptance.js",
    "scripts/check_dashboard_deployment_readiness.js",
    "scripts/check_dashboard_d11o_deployment_discipline.js",
    "docs/qadam-dashboard-d11o-deployment-discipline-2026-05-26.md",
    "docs/qadam-dashboard-overhaul-master-implementation-plan.md"
].forEach(assertFile);

[
    "landing-page-repo/status/cockpit-status.json",
    "landing-page-repo/status/cockpit-status.signature.json"
].forEach(assertJson);

const project = JSON.parse(readText(projectPath));
assert(project.projectId === "prj_apm3Zfd9fpWq4wsJiSunkVmxdCVQ", "Vercel project id does not match qadam");
assert(project.orgId === "team_Qv7iJDGRobHFyiyUsMUbVxyy", "Vercel org id does not match qadam team");

const ignore = readText(ignorePath);
[".git", ".vercel", ".DS_Store", "node_modules"].forEach((needle) => {
    assertIncludes(ignore, needle, "landing .vercelignore");
});
["dashboard", "guide", "status", "auth.css", "dashboard.js"].forEach((needle) => {
    assert(!ignore.includes(needle), `landing .vercelignore must not exclude ${needle}`);
});

const deployScript = readText(deployScriptPath);
[
    "bash \"${ROOT_DIR}/scripts/preflight_dashboard_deployment.sh\"",
    "QADAM_SKIP_DEPLOY_PREFLIGHT",
    "vercel",
    "deploy",
    "--prod",
    "--yes",
    "--scope",
    "--token",
    "qadam.trade",
    "www.qadam.trade",
    "deployment_url",
    "dashboard-deployment-receipt.json",
    "send_codebase_upgrade_telegram_notification.py",
    "Codebase upgrade Telegram notification",
    "No production aliases were changed",
    "Production deployment:"
].forEach((needle) => assertIncludes(deployScript, needle, "production deploy script"));

const plan = readText(planPath);
[
    "Phase D10I - Deployment Discipline",
    "local deployment preflight",
    "production deploy script",
    "deployment receipt"
].forEach((needle) => assertIncludes(plan, needle, "dashboard implementation plan"));

const masterPlan = readText(path.join(repoRoot, "docs", "qadam-dashboard-overhaul-master-implementation-plan.md"));
[
    "D11O - Deployment Discipline",
    "scripts/check_dashboard_d11o_deployment_discipline.js",
    "docs/qadam-dashboard-d11o-deployment-discipline-2026-05-26.md",
    "D11P - Performance View Consolidation"
].forEach((needle) => assertIncludes(masterPlan, needle, "dashboard overhaul master plan"));

[
    "landing-page-repo/dashboard/index.html",
    "landing-page-repo/guide/index.html",
    "landing-page-repo/auth.css",
    "landing-page-repo/dashboard.js",
    "landing-page-repo/scripts/deploy-vercel-production.sh",
    "scripts/preflight_dashboard_deployment.sh",
    "docs/qadam-dashboard-implementation-plan.md"
].forEach((relativePath) => {
    assertNoUnsafePublicText(readText(path.join(repoRoot, relativePath)), relativePath);
});

if (fs.existsSync(localVercelEnvPath)) {
    const mode = fs.statSync(localVercelEnvPath).mode & 0o777;
    assert((mode & 0o077) === 0, "data/runtime/vercel.env must not be group/world readable");
}

console.log("dashboard_deployment_readiness=ok");
