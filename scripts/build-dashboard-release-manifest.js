#!/usr/bin/env node
"use strict";

const crypto = require("node:crypto");
const fs = require("node:fs");
const path = require("node:path");

const SITE_ROOT = path.resolve(__dirname, "..");
const INDEX_PATH = path.join(SITE_ROOT, "dashboard", "index.html");
const DASHBOARD_PATH = path.join(SITE_ROOT, "dashboard.js");
const CSS_PATH = path.join(SITE_ROOT, "auth.css");
const AUTH_PATH = path.join(SITE_ROOT, "auth.js");
const QUANTUM_EDGE_JAVASCRIPT_PATH = path.join(SITE_ROOT, "quantum-edge-page.js");
const QUANTUM_EDGE_CSS_PATH = path.join(SITE_ROOT, "quantum-edge-page.css");
const QUANTUM_EDGE_STATUS_PATH = path.join(SITE_ROOT, "status", "quantum-edge-page.json");
const WAVE_F_JAVASCRIPT_PATH = path.join(SITE_ROOT, "quantum-edge-wave-f.js");
const WAVE_F_CSS_PATH = path.join(SITE_ROOT, "quantum-edge-wave-f.css");
const WAVE_F_STATUS_PATH = path.join(SITE_ROOT, "status", "quantum-edge-wave-f.json");
const STATUS_PATH = path.join(SITE_ROOT, "status", "cockpit-status.json");
const MANIFEST_PATH = path.join(SITE_ROOT, "status", "dashboard-release.json");

function sha256(filePath) {
    return crypto.createHash("sha256").update(fs.readFileSync(filePath)).digest("hex");
}

function requireMatch(value, pattern, label) {
    const match = value.match(pattern);
    if (!match) throw new Error(`dashboard_release_missing_${label}`);
    return match[1];
}

function buildManifest() {
    const html = fs.readFileSync(INDEX_PATH, "utf8");
    const auth = fs.readFileSync(AUTH_PATH, "utf8");
    const status = JSON.parse(fs.readFileSync(STATUS_PATH, "utf8"));
    const quantumEdgeStatus = JSON.parse(fs.readFileSync(QUANTUM_EDGE_STATUS_PATH, "utf8"));
    const waveFStatus = JSON.parse(fs.readFileSync(WAVE_F_STATUS_PATH, "utf8"));
    const lifecycle = status?.qsase_dashboard?.sections?.end_to_end_lifecycle || {};
    const lifecycleChecks = status?.qsase_dashboard?.sections?.lifecycle_dashboard_checks || {};
    const routeCount = Number(lifecycle.route_count || lifecycleChecks.route_count || 0);
    const canonicalStageCount = Number(lifecycle.stage_count || lifecycleChecks.stage_count || 0);

    if (routeCount !== 13 || canonicalStageCount !== 10 || lifecycleChecks.status !== "passed") {
        throw new Error("dashboard_release_lifecycle_contract_absent");
    }

    const releaseId = requireMatch(html, /<meta name="qadam-dashboard-release" content="([^"]+)"/, "id");
    const cacheKey = releaseId.replace("qadam-dashboard-", "");
    // Fail before the long production preflight if any lazy-loaded surface is stale.
    for (const [source, assets] of [
        [html, ["/dashboard.js", "/auth.js", "/auth.css", "/dashboard-release.js"]],
        [auth, ["/quantum-edge-page.js", "/quantum-edge-page.css", "/quantum-edge-wave-f.js", "/quantum-edge-wave-f.css"]],
        [fs.readFileSync(QUANTUM_EDGE_JAVASCRIPT_PATH, "utf8"), ["/status/quantum-edge-page.json"]],
        [fs.readFileSync(WAVE_F_JAVASCRIPT_PATH, "utf8"), ["/status/quantum-edge-wave-f.json"]]
    ]) {
        for (const asset of assets) {
            if (!source.includes(`${asset}?v=${cacheKey}\"`)) {
                throw new Error(`dashboard_release_cache_key_mismatch:${asset}`);
            }
        }
    }

    return {
        schema_version: "qadam_dashboard_release.v1",
        release_id: releaseId,
        git_commit: "runtime_injected_from_deploy",
        route_count: routeCount,
        canonical_stage_count: canonicalStageCount,
        stage_count: routeCount * canonicalStageCount,
        javascript_asset: requireMatch(html, /<script src="(\/dashboard\.js\?v=[^"]+)"/, "javascript_asset"),
        javascript_sha256: sha256(DASHBOARD_PATH),
        css_asset: requireMatch(html, /<link rel="stylesheet" href="(\/auth\.css\?v=[^"]+)"/, "css_asset"),
        css_sha256: sha256(CSS_PATH),
        auth_asset: requireMatch(html, /<script src="(\/auth\.js\?v=[^"]+)"/, "auth_asset"),
        auth_sha256: sha256(AUTH_PATH),
        quantum_edge_page: {
            schema_version: quantumEdgeStatus.schema_version,
            projection_status: quantumEdgeStatus.projection_status,
            content_hash: quantumEdgeStatus.content_hash,
            javascript_asset: requireMatch(auth, /script\.src = "(\/quantum-edge-page\.js\?v=[^"]+)"/, "quantum_edge_javascript_asset"),
            javascript_sha256: sha256(QUANTUM_EDGE_JAVASCRIPT_PATH),
            css_asset: requireMatch(auth, /stylesheet\.href = "(\/quantum-edge-page\.css\?v=[^"]+)"/, "quantum_edge_css_asset"),
            css_sha256: sha256(QUANTUM_EDGE_CSS_PATH),
            projection_asset: "/status/quantum-edge-page.json",
            projection_sha256: sha256(QUANTUM_EDGE_STATUS_PATH)
        },
        quantum_edge_wave_f: {
            schema_version: waveFStatus.schema_version,
            content_hash: waveFStatus.content_hash,
            javascript_asset: requireMatch(auth, /script\.src = "(\/quantum-edge-wave-f\.js\?v=[^"]+)"/, "wave_f_javascript_asset"),
            javascript_sha256: sha256(WAVE_F_JAVASCRIPT_PATH),
            css_asset: requireMatch(auth, /stylesheet\.href = "(\/quantum-edge-wave-f\.css\?v=[^"]+)"/, "wave_f_css_asset"),
            css_sha256: sha256(WAVE_F_CSS_PATH),
            projection_asset: "/status/quantum-edge-wave-f.json",
            projection_sha256: sha256(WAVE_F_STATUS_PATH)
        },
        lifecycle_check_result: "passed",
        stale_shell_detector: {
            status: "enabled",
            manifest_endpoint: "/api/dashboard-release",
            check_interval_seconds: 300,
            message: "A newer dashboard is available",
            silent_reload_allowed: false
        },
        authority: {
            read_only: true,
            paper_only: true,
            command_disabled: true,
            approvals_allowed: false,
            trades_allowed: false,
            broker_writes_allowed: false,
            live_capital_enabled: false,
            proof_credit_allowed: false
        },
        boundary: "Public release metadata only. It cannot create commands, approvals, trades, broker writes, live capital, or proof credit."
    };
}

function stable(value) {
    return JSON.stringify(value, null, 2) + "\n";
}

const expected = buildManifest();
if (process.argv.includes("--write")) {
    fs.writeFileSync(MANIFEST_PATH, stable(expected));
    console.log(`dashboard_release_manifest_written=${MANIFEST_PATH}`);
} else {
    const actual = JSON.parse(fs.readFileSync(MANIFEST_PATH, "utf8"));
    if (stable(actual) !== stable(expected)) {
        throw new Error("dashboard_release_manifest_does_not_match_committed_assets");
    }
}

console.log(`release_id=${expected.release_id}`);
console.log(`route_count=${expected.route_count}`);
console.log(`canonical_stage_count=${expected.canonical_stage_count}`);
console.log(`stage_count=${expected.stage_count}`);
console.log(`javascript_sha256=${expected.javascript_sha256}`);
console.log(`css_sha256=${expected.css_sha256}`);
console.log("dashboard_release_manifest_check=ok");
