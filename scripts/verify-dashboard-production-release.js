#!/usr/bin/env node
"use strict";

const crypto = require("node:crypto");
const fs = require("node:fs");
const path = require("node:path");

const SITE_ROOT = path.resolve(__dirname, "..");
const LOCAL_MANIFEST = JSON.parse(
    fs.readFileSync(path.join(SITE_ROOT, "status", "dashboard-release.json"), "utf8")
);
const ROUTES = [
    ["system", "team"],
    ["fund", "portfolio"],
    ["fund", "timeline"],
    ["observe", "sources"],
    ["observe", "universe"],
    ["patterns", "findings"],
    ["patterns", "nonlinear"],
    ["decide", "strategies"],
    ["decide", "decision"],
    ["trade", "orders"],
    ["learn", "outcomes"],
    ["learn", "improvements"],
    ["system", "overview"]
];
const OBSOLETE_LABELS = [
    "Trade Intents",
    "Final Decision",
    "Position Lifecycle",
    "Outcomes & Postmortems",
    "Improvement Proposals",
    "Backtesting & Replay",
    "Learning Briefs"
];

function argument(name) {
    const index = process.argv.indexOf(name);
    return index >= 0 ? process.argv[index + 1] : "";
}

function assert(condition, message) {
    if (!condition) throw new Error(message);
}

function sha256(value) {
    return crypto.createHash("sha256").update(value).digest("hex");
}

async function fetchText(url) {
    const response = await fetch(url, {
        cache: "no-store",
        headers: { "cache-control": "no-cache", pragma: "no-cache" },
        redirect: "follow"
    });
    assert(response.ok, `production_fetch_failed:${response.status}:${url}`);
    return response.text();
}

async function main() {
    const baseUrl = argument("--base-url").replace(/\/$/, "");
    const expectedCommit = argument("--expected-commit");
    assert(/^https:\/\//.test(baseUrl), "production_base_url_required");
    assert(/^[0-9a-f]{40}$/.test(expectedCommit), "expected_commit_required");

    const nonce = `${Date.now()}-${Math.random().toString(16).slice(2)}`;
    const manifest = JSON.parse(await fetchText(`${baseUrl}/api/dashboard-release?probe=${nonce}`));
    assert(manifest.release_id === LOCAL_MANIFEST.release_id, "production_release_id_mismatch");
    assert(manifest.git_commit === expectedCommit, "production_git_commit_mismatch");
    assert(manifest.route_count === 13, "production_route_count_mismatch");
    assert(manifest.canonical_stage_count === 10, "production_canonical_stage_count_mismatch");
    assert(manifest.stage_count === 130, "production_stage_count_mismatch");
    assert(manifest.lifecycle_check_result === "passed", "production_lifecycle_check_missing");
    assert(manifest.javascript_sha256 === LOCAL_MANIFEST.javascript_sha256, "production_manifest_javascript_hash_mismatch");
    assert(manifest.css_sha256 === LOCAL_MANIFEST.css_sha256, "production_manifest_css_hash_mismatch");
    assert(manifest.auth_sha256 === LOCAL_MANIFEST.auth_sha256, "production_manifest_auth_hash_mismatch");
    assert(
        JSON.stringify(manifest.quantum_edge_page) === JSON.stringify(LOCAL_MANIFEST.quantum_edge_page),
        "production_manifest_quantum_edge_contract_mismatch"
    );
    assert(
        JSON.stringify(manifest.quantum_edge_wave_f) === JSON.stringify(LOCAL_MANIFEST.quantum_edge_wave_f),
        "production_manifest_wave_f_contract_mismatch"
    );

    for (const [moduleId, viewId] of ROUTES) {
        const html = await fetchText(
            `${baseUrl}/dashboard/?module=${encodeURIComponent(moduleId)}&view=${encodeURIComponent(viewId)}&release_probe=${nonce}`
        );
        assert(html.includes(`content="${LOCAL_MANIFEST.release_id}"`), `production_release_meta_missing:${moduleId}/${viewId}`);
        assert(html.includes(`src="${LOCAL_MANIFEST.javascript_asset}"`), `production_javascript_asset_missing:${moduleId}/${viewId}`);
        assert(html.includes(`href="${LOCAL_MANIFEST.css_asset}"`), `production_css_asset_missing:${moduleId}/${viewId}`);
        assert(html.includes(`src="${LOCAL_MANIFEST.auth_asset}"`), `production_auth_asset_missing:${moduleId}/${viewId}`);
    }

    const javascript = await fetchText(`${baseUrl}${LOCAL_MANIFEST.javascript_asset}&release_probe=${nonce}`);
    const css = await fetchText(`${baseUrl}${LOCAL_MANIFEST.css_asset}&release_probe=${nonce}`);
    const auth = await fetchText(`${baseUrl}${LOCAL_MANIFEST.auth_asset}&release_probe=${nonce}`);
    assert(sha256(javascript) === LOCAL_MANIFEST.javascript_sha256, "production_javascript_hash_mismatch");
    assert(sha256(css) === LOCAL_MANIFEST.css_sha256, "production_css_hash_mismatch");
    assert(sha256(auth) === LOCAL_MANIFEST.auth_sha256, "production_auth_hash_mismatch");

    const quantum = LOCAL_MANIFEST.quantum_edge_page;
    const quantumJavascript = await fetchText(`${baseUrl}${quantum.javascript_asset}&release_probe=${nonce}`);
    const quantumCss = await fetchText(`${baseUrl}${quantum.css_asset}&release_probe=${nonce}`);
    const quantumProjectionText = await fetchText(`${baseUrl}${quantum.projection_asset}?release_probe=${nonce}`);
    const quantumProjection = JSON.parse(quantumProjectionText);
    assert(sha256(quantumJavascript) === quantum.javascript_sha256, "production_quantum_edge_javascript_hash_mismatch");
    assert(sha256(quantumCss) === quantum.css_sha256, "production_quantum_edge_css_hash_mismatch");
    assert(sha256(quantumProjectionText) === quantum.projection_sha256, "production_quantum_edge_projection_hash_mismatch");
    assert(quantumProjection.schema_version === "qadam.QuantumEdgeThreeLayerPage.v1", "production_quantum_edge_schema_mismatch");
    assert(quantumProjection.projection_status === "ready", "production_quantum_edge_projection_not_ready");
    assert(quantumProjection.content_hash === quantum.content_hash, "production_quantum_edge_content_hash_mismatch");
    assert(quantumProjection.answer.proof_state === "unproven", "production_quantum_edge_proof_overstated");
    assert(quantumProjection.answer.engineering_checks.score_label === "11/11", "production_quantum_edge_engineering_score_mismatch");
    assert(quantumProjection.answer.market_proof_prerequisites.score_label === "1/6", "production_quantum_edge_market_score_mismatch");
    assert(Object.values(quantumProjection.authority).every((value) => value === false), "production_quantum_edge_authority_escalated");
    assert(auth.includes(quantum.javascript_asset), "production_quantum_edge_javascript_loader_missing");
    assert(auth.includes(quantum.css_asset), "production_quantum_edge_css_loader_missing");
    assert(auth.includes('moduleId === "patterns" && viewId === "nonlinear"'), "production_quantum_edge_route_loader_missing");

    const waveF = LOCAL_MANIFEST.quantum_edge_wave_f;
    const waveFJavascript = await fetchText(`${baseUrl}${waveF.javascript_asset}&release_probe=${nonce}`);
    const waveFCss = await fetchText(`${baseUrl}${waveF.css_asset}&release_probe=${nonce}`);
    const waveFProjectionText = await fetchText(`${baseUrl}${waveF.projection_asset}?release_probe=${nonce}`);
    const waveFProjection = JSON.parse(waveFProjectionText);
    assert(sha256(waveFJavascript) === waveF.javascript_sha256, "production_wave_f_javascript_hash_mismatch");
    assert(sha256(waveFCss) === waveF.css_sha256, "production_wave_f_css_hash_mismatch");
    assert(sha256(waveFProjectionText) === waveF.projection_sha256, "production_wave_f_projection_hash_mismatch");
    assert(waveFProjection.schema_version === "qadam.QuantumEdgeWaveFPublicView.v1", "production_wave_f_schema_mismatch");
    assert(waveFProjection.content_hash === waveF.content_hash, "production_wave_f_content_hash_mismatch");
    assert(Object.values(waveFProjection.authority).every((value) => value === false), "production_wave_f_authority_escalated");
    assert(auth.includes(waveF.javascript_asset), "production_wave_f_javascript_loader_missing");
    assert(auth.includes(waveF.css_asset), "production_wave_f_css_loader_missing");

    [
        "function renderQadamLifecycleTimeline",
        "data-qadam-lifecycle",
        'const QSASE_TEAM_ROUTE = { moduleId: "system", viewId: "team", label: "Qadam Team" };',
        '{ id: "decision", label: "Decision Room" }',
        '{ id: "orders", label: "Order Monitor" }',
        '{ id: "outcomes", label: "Results & Lessons" }',
        '{ id: "improvements", label: "Tests & Improvements" }',
        'const QSASE_DEFAULT_ROUTE = { moduleId: "fund", viewId: "portfolio" };'
    ].forEach((needle) => assert(javascript.includes(needle), `production_lifecycle_renderer_missing:${needle}`));
    OBSOLETE_LABELS.forEach((label) => {
        assert(!javascript.includes(label), `production_obsolete_navigation_label:${label}`);
    });

    console.log(JSON.stringify({
        status: "production_dashboard_release_verified",
        base_url: baseUrl,
        release_id: manifest.release_id,
        git_commit: manifest.git_commit,
        route_count: manifest.route_count,
        canonical_stage_count: manifest.canonical_stage_count,
        stage_count: manifest.stage_count,
        javascript_sha256: manifest.javascript_sha256,
        css_sha256: manifest.css_sha256,
        auth_sha256: manifest.auth_sha256,
        quantum_edge_content_hash: manifest.quantum_edge_page.content_hash,
        quantum_edge_wave_f_content_hash: manifest.quantum_edge_wave_f.content_hash,
        verified_routes: ROUTES.map(([moduleId, viewId]) => `${moduleId}/${viewId}`),
        obsolete_navigation_label_count: 0
    }, null, 2));
}

main().catch((error) => {
    console.error(error.message);
    process.exitCode = 1;
});
