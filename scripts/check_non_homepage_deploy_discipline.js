#!/usr/bin/env node

const fs = require("node:fs");
const path = require("node:path");

const repoRoot = path.resolve(__dirname, "..");
const dashboardSiteRoot = path.resolve(
    process.env.QADAM_DASHBOARD_SITE_ROOT || path.join(repoRoot, "landing-page-repo")
);

function resolvePath(relativePath) {
    const prefix = "landing-page-repo/";
    return relativePath.startsWith(prefix)
        ? path.join(dashboardSiteRoot, relativePath.slice(prefix.length))
        : path.join(repoRoot, relativePath);
}

const paths = {
    deployScript: "landing-page-repo/scripts/deploy-vercel-production.sh",
    preflight: "scripts/preflight_dashboard_deployment.sh",
    regressionSuite: "scripts/check_non_homepage_regression_suite.js",
    deployDiscipline: "scripts/check_non_homepage_deploy_discipline.js",
    readiness: "scripts/check_dashboard_deployment_readiness.js",
    status: "landing-page-repo/status/cockpit-status.json",
    signature: "landing-page-repo/status/cockpit-status.signature.json",
    project: "landing-page-repo/.vercel/project.json",
    ignore: "landing-page-repo/.vercelignore",
    waveHBackend: "scripts/check_qadam_wave_h_crude_oil_certification.py",
    waveHFrontend: "scripts/check_dashboard_quantum_edge_wave_h.js",
    quantumPageBackend: "scripts/check_qadam_quantum_edge_page_view_model.py",
    quantumPageFrontend: "scripts/check_dashboard_quantum_edge_three_layer.js",
    quantumPageInteractions: "scripts/check_dashboard_quantum_edge_interactions.js"
};

const requiredNonHomepageChecks = [
    "scripts/check_non_homepage_design_tokens.js",
    "scripts/check_non_homepage_layout_components.js",
    "scripts/check_non_homepage_navigation_contract.js",
    "scripts/check_non_homepage_auth_pages.js",
    "scripts/check_non_homepage_whitepaper_redesign.js",
    "scripts/check_non_homepage_guide_redesign.js",
    "scripts/check_non_homepage_dashboard_redesign.js",
    "scripts/check_non_homepage_accessibility.js",
    "scripts/check_non_homepage_regression_suite.js",
    "scripts/check_non_homepage_deploy_discipline.js"
];

const requiredLandingFiles = [
    "landing-page-repo/login/index.html",
    "landing-page-repo/sign-up/index.html",
    "landing-page-repo/whitepaper/index.html",
    "landing-page-repo/guide/index.html",
    "landing-page-repo/dashboard/index.html",
    "landing-page-repo/auth.css",
    "landing-page-repo/whitepaper.css",
    "landing-page-repo/dashboard.js",
    "landing-page-repo/quantum-edge-page.js",
    "landing-page-repo/quantum-edge-page.css",
    "landing-page-repo/status/quantum-edge-page.json",
    "landing-page-repo/non-homepage-tokens.css",
    "landing-page-repo/non-homepage-layout.css"
];

function read(relativePath) {
    return fs.readFileSync(resolvePath(relativePath), "utf8");
}

function assert(condition, message) {
    if (!condition) {
        throw new Error(message);
    }
}

function assertFile(relativePath) {
    assert(fs.existsSync(resolvePath(relativePath)), `missing deploy discipline dependency ${relativePath}`);
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

[...Object.values(paths), ...requiredNonHomepageChecks, ...requiredLandingFiles].forEach(assertFile);

const deployScript = read(paths.deployScript);
const preflight = read(paths.preflight);
const regressionSuite = read(paths.regressionSuite);
const readiness = read(paths.readiness);
const project = JSON.parse(read(paths.project));
const ignore = read(paths.ignore);

includesAll(deployScript, [
    "bash \"${ROOT_DIR}/scripts/preflight_dashboard_deployment.sh\"",
    "QADAM_SKIP_DEPLOY_PREFLIGHT",
    "QADAM_DASHBOARD_SITE_ROOT",
    "git -C \"${SITE_DIR}\" worktree add --detach",
    "QADAM_DASHBOARD_SITE_ROOT=\"${PREFLIGHT_SITE_DIR}\"",
    "cleanup_preflight_site",
    "\"${vercel_cmd[@]}\" deploy",
    "--prod",
    "--yes",
    "--scope \"${VERCEL_TEAM_ID}\"",
    "--token \"${VERCEL_TOKEN}\"",
    "\"qadam.trade\"",
    "\"www.qadam.trade\"",
    "No production aliases were changed by this script and no deployment receipt was written.",
    "A Vercel deployment URL may exist, but this script did not complete all production aliases or write a receipt.",
    "dashboard-deployment-receipt.json",
    "preflight: \"passed\"",
    "quantum_edge_page: manifest.quantum_edge_page",
    "quantum_edge_wave_f: manifest.quantum_edge_wave_f",
    "Contains no Vercel token, session cookie, broker credential, or dashboard secret."
], "production deploy script");

const preflightIndex = indexOfOrThrow(deployScript, "bash \"${ROOT_DIR}/scripts/preflight_dashboard_deployment.sh\"", "deploy order");
const deployIndex = indexOfOrThrow(deployScript, "\"${vercel_cmd[@]}\" deploy", "deploy order");
const aliasIndex = indexOfOrThrow(deployScript, "\"${vercel_cmd[@]}\" alias set", "deploy order");
const receiptIndex = indexOfOrThrow(deployScript, "dashboard-deployment-receipt.json", "deploy order");
assert(preflightIndex < deployIndex, "local preflight must run before Vercel deploy");
assert(deployIndex < aliasIndex, "production aliases must run after Vercel deploy");
assert(aliasIndex < receiptIndex, "deployment receipt must be written after aliasing");

includesAll(preflight, [
    "node --check scripts/check_non_homepage_regression_suite.js",
    "node scripts/check_non_homepage_regression_suite.js",
    "node --check scripts/check_non_homepage_deploy_discipline.js",
    "node scripts/check_non_homepage_deploy_discipline.js",
    "node scripts/check_dashboard_quantum_edge_wave_f.js \"${DASHBOARD_SITE_ROOT}\"",
    "node scripts/check_dashboard_quantum_edge_wave_g.js \"${DASHBOARD_SITE_ROOT}\"",
    "node scripts/check_dashboard_quantum_edge_wave_h.js \"${DASHBOARD_SITE_ROOT}\"",
    "node scripts/check_dashboard_quantum_edge_three_layer.js \"${DASHBOARD_SITE_ROOT}\"",
    "run_with_retry 3 node scripts/check_dashboard_quantum_edge_interactions.js --site-root \"${DASHBOARD_SITE_ROOT}\""
], "deployment preflight non-homepage gate");

const regressionIndex = indexOfOrThrow(preflight, "node scripts/check_non_homepage_regression_suite.js", "preflight order");
const disciplineIndex = indexOfOrThrow(preflight, "node scripts/check_non_homepage_deploy_discipline.js", "preflight order");
assert(regressionIndex < disciplineIndex, "non-homepage regression suite must run before deploy discipline checker");

includesAll(regressionSuite, [
    "scripts/check_non_homepage_design_tokens.js",
    "scripts/check_non_homepage_layout_components.js",
    "scripts/check_non_homepage_navigation_contract.js",
    "scripts/check_non_homepage_auth_pages.js",
    "scripts/check_non_homepage_whitepaper_redesign.js",
    "scripts/check_non_homepage_guide_redesign.js",
    "scripts/check_non_homepage_dashboard_redesign.js",
    "scripts/check_non_homepage_accessibility.js",
    "scripts/check_dashboard_deployment_readiness.js",
    "assertHomepageIsolation",
    "assertPublicSafePages",
    "git\", [\"diff\", \"--check\"",
    "git\", [\"-C\", dashboardSiteRoot, \"diff\", \"--check\"",
    "non_homepage_regression_suite=ok"
], "non-homepage regression suite");

includesAll(readiness, [
    "scripts/check_non_homepage_regression_suite.js",
    "scripts/check_non_homepage_deploy_discipline.js",
    "landing-page-repo/non-homepage-tokens.css",
    "landing-page-repo/non-homepage-layout.css"
], "deployment readiness non-homepage dependencies");

assert(project.projectId === "prj_apm3Zfd9fpWq4wsJiSunkVmxdCVQ", "Vercel project id does not match qadam");
assert(project.orgId === "team_Qv7iJDGRobHFyiyUsMUbVxyy", "Vercel org id does not match qadam team");

[
    "login",
    "sign-up",
    "whitepaper",
    "guide",
    "dashboard",
    "auth.css",
    "whitepaper.css",
    "dashboard.js",
    "non-homepage-tokens.css",
    "non-homepage-layout.css",
    "status"
].forEach((needle) => {
    assert(!ignore.includes(`/${needle}`), `.vercelignore must not exclude ${needle}`);
});

[
    deployScript,
    preflight,
    regressionSuite,
    readiness,
    ...requiredLandingFiles.map(read)
].forEach((text, index) => assertNoSecretMaterial(text, `deploy discipline text ${index}`));

console.log("non_homepage_deploy_discipline=ok");
console.log("non_homepage_deploy_preflight_wired=True");
console.log("non_homepage_live_deploy_attempted=False");
