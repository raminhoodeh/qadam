#!/usr/bin/env node

"use strict";

const fs = require("fs");
const path = require("path");

const repoRoot = path.resolve(__dirname, "..");
const siteRoot = path.resolve(process.argv[2] || path.join(repoRoot, "landing-page-repo"));

function read(relativePath) {
    return fs.readFileSync(path.join(siteRoot, relativePath), "utf8");
}

function assert(condition, message) {
    if (!condition) throw new Error(message);
}

const status = JSON.parse(read("status/quantum-edge-wave-h.json"));
const script = read("quantum-edge-wave-h.js");
const stylesheet = read("quantum-edge-wave-h.css");
const auth = read("auth.js");
const dashboardHtml = read("dashboard/index.html");
const guideHtml = read("guide/index.html");
const whitepaperHtml = read("whitepaper/index.html");

assert(status.schema_version === "qadam.QuantumEdgeWaveHCrudeOilCertification.v1", "Wave H schema mismatch");
assert(status.status === "mechanism_certified_result_unproven", "Wave H status is not honest");
assert(status.mechanism_certified === true, "Wave H mechanism is not certified");
assert(status.scientific_result_certified === false, "Wave H overstates scientific certification");
assert(status.public_proof_state === "unproven", "Wave H proof state is overstated");
assert(status.scientific_verdict === "not_measurable", "Wave H verdict is overstated");
assert(status.certification.engineering_pass_count === 11, "Wave H engineering checks are incomplete");
assert(status.certification.engineering_check_count === 11, "Wave H engineering check contract changed");
assert(status.certification.scientific_pass_count === 0, "Wave H scientific checks are overstated");
assert(status.certification.scientific_check_count === 6, "Wave H scientific check contract changed");
assert(
    status.evidence_truth.classified_window_count >= status.evidence_truth.eligible_window_count,
    "Wave H classified-window count is below its eligible-window count"
);
assert(status.evidence_truth.eligible_window_count === 0, "Wave H invents eligible holdout windows");
assert(status.evidence_truth.provider_row_count === 0, "Wave H invents provider history");
assert(status.evidence_truth.leakage_violation_count === 0, "Wave H leakage gate failed");
assert(status.engineering_fixture.classical_method_count === 8, "Wave H classical control count changed");
assert(status.engineering_fixture.contract_fixture_only === true, "Wave H hides fixture status");
assert(status.engineering_fixture.provider_call_count === 0, "Wave H made a provider call");
assert(status.engineering_fixture.hardware_job_submitted === false, "Wave H submitted hardware");
assert(status.engineering_fixture.hardware_experiment_completed === false, "Wave H claims hardware completion");
assert(status.hardware_authorization_checkpoint.authorized === false, "Wave H invents hardware authorization");
assert(
    ["ibm_token_instance_access_mismatch", "provider_readiness_not_exported"].includes(
        status.hardware_authorization_checkpoint.provider_blocker
    ),
    "Wave H hides IBM readiness state"
);
assert(Object.values(status.downstream_truth).every((value) => value === 0), "Wave H created downstream trading state");
assert(status.expansion.allowed === false, "Wave H expands before crude-oil proof");
assert(Object.values(status.authority).every((value) => value === false), "Wave H has authority");
assert(status.proof_state_key.length === 5, "Wave H proof-state key is incomplete");
assert(status.proof_state_key.filter((row) => row.current).length === 1, "Wave H current proof state is ambiguous");

[
    "Crude-oil pilot certification",
    "Can Qadam prove a quantum edge honestly?",
    "What the crude-oil test will compare",
    "What ran, and what did not",
    "Engineering mechanism",
    "Market proof",
    "Evidence first, hardware second",
    "Not authorized or submitted"
].forEach((phrase) => assert(script.includes(phrase), `Wave H renderer missing ${phrase}`));

assert((script.match(/fetch\(/g) || []).length === 1, "Wave H renderer must make one read-only fetch");
assert(script.includes("/status/quantum-edge-wave-h.json"), "Wave H renderer fetches the wrong resource");
assert(!/paper-api\.alpaca|\/v2\/orders|submitOrder|createOrder/i.test(script), "Wave H renderer contains broker/order code");
assert(auth.includes("/quantum-edge-wave-h.js?v=20260712-wave-h-v1"), "Wave H script loader missing");
assert(auth.includes("/quantum-edge-wave-h.css?v=20260712-wave-h-v1"), "Wave H stylesheet loader missing");
const authAssetMatch = dashboardHtml.match(/\/auth\.js\?v=([^"']+)/);
assert(authAssetMatch, "Dashboard auth.js cache key is missing");
assert(
    !["20260712-wave-f-v1", "20260712-wave-g-v1"].includes(authAssetMatch[1]),
    "Dashboard auth.js cache key predates Wave H"
);
assert(stylesheet.includes("body.qadam-dashboard-page .qwh-"), "Wave H CSS is not dashboard scoped");
assert(stylesheet.includes("@media (max-width: 720px)"), "Wave H mobile layout missing");
assert(stylesheet.includes("prefers-reduced-motion"), "Wave H reduced-motion support missing");
assert(guideHtml.includes('id="quantum-edge-certification"'), "User Guide Wave H explanation missing");
assert(guideHtml.includes("zero provider-backed windows are eligible for untouched forward scoring"), "User Guide evidence truth missing");
assert(whitepaperHtml.includes('id="quantum-edge-proof"'), "Whitepaper Wave H explanation missing");
assert(whitepaperHtml.includes("A prepared engineering manifest is not hardware authorization"), "Whitepaper hardware boundary missing");

process.stdout.write(`${JSON.stringify({
    status: "wave_h_dashboard_acceptance_passed",
    content_hash: status.content_hash,
    public_proof_state: status.public_proof_state,
    scientific_verdict: status.scientific_verdict,
    engineering_checks: `${status.certification.engineering_pass_count}/${status.certification.engineering_check_count}`,
    scientific_checks: `${status.certification.scientific_pass_count}/${status.certification.scientific_check_count}`,
    eligible_windows: status.evidence_truth.eligible_window_count,
    provider_rows: status.evidence_truth.provider_row_count,
    hardware_authorized: status.hardware_authorization_checkpoint.authorized,
    downstream_state_total: Object.values(status.downstream_truth).reduce((sum, value) => sum + value, 0),
    authority: "read_only"
}, null, 2)}\n`);
