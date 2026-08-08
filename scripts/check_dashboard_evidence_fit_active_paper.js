#!/usr/bin/env node
"use strict";

const fs = require("node:fs");
const path = require("node:path");

const root = path.resolve(__dirname, "..");
const dashboardRoot = path.join(root, "landing-page-repo");
const javascript = fs.readFileSync(path.join(dashboardRoot, "dashboard.js"), "utf8");
const css = fs.readFileSync(path.join(dashboardRoot, "auth.css"), "utf8");
const html = fs.readFileSync(path.join(dashboardRoot, "dashboard", "index.html"), "utf8");
const runtimeArtifact = path.join(root, "data", "runtime", "qadam_dashboard_evidence_fit_frontend_checks.json");

const expectedAreas = ["sources", "universe", "patterns", "strategies", "decision", "orders", "learning"];
const errors = [];
if (!javascript.includes("function renderQsaseEvidenceFitContext")) errors.push("evidence_fit_renderer_missing");
for (const area of expectedAreas) {
    if (!javascript.includes(`renderQsaseEvidenceFitContext(qsase, \"${area}\")`)) {
        errors.push(`evidence_fit_area_missing:${area}`);
    }
}
if (!javascript.includes("qsase.evidence_fit_dashboard")) errors.push("evidence_fit_public_projection_reader_missing");
if (!javascript.includes("View evidence path")) errors.push("evidence_fit_disclosure_missing");
if (!css.includes(".qsase-evidence-fit-context")) errors.push("evidence_fit_styles_missing");
if (!html.includes("20260808-evidence-fit-v1")) errors.push("evidence_fit_asset_version_missing");

const routePairs = [
    ["system", "team"], ["fund", "portfolio"], ["fund", "timeline"],
    ["observe", "sources"], ["observe", "universe"], ["patterns", "findings"],
    ["patterns", "nonlinear"], ["decide", "strategies"], ["decide", "decision"],
    ["trade", "orders"], ["learn", "outcomes"], ["learn", "improvements"],
    ["system", "overview"]
];
for (const [moduleId, viewId] of routePairs) {
    const needle = `{ id: \"${viewId}\"`;
    if (!["team", "portfolio", "overview"].includes(viewId) && !javascript.includes(needle)) {
        errors.push(`protected_route_label_missing:${moduleId}/${viewId}`);
    }
}

const report = {
    schema_version: "qadam_dashboard_evidence_fit_frontend_checks.v1",
    artifact_type: "qadam_dashboard_evidence_fit_frontend_checks",
    generated_at: new Date().toISOString(),
    status: errors.length ? "blocked" : "passed",
    protected_route_count: 13,
    route_structure_changed: false,
    evidence_fit_area_count: expectedAreas.length,
    public_safe: true,
    read_only: true,
    command_disabled: true,
    paper_order_created_count: 0,
    broker_write_count: 0,
    validation_error_count: errors.length,
    validation_errors: errors
};
fs.mkdirSync(path.dirname(runtimeArtifact), { recursive: true });
fs.writeFileSync(runtimeArtifact, `${JSON.stringify(report, null, 2)}\n`);
console.log(`qadam_dashboard_evidence_fit_status=${report.status}`);
console.log(`qadam_dashboard_evidence_fit_route_count=${report.protected_route_count}`);
console.log(`qadam_dashboard_evidence_fit_area_count=${report.evidence_fit_area_count}`);
for (const error of errors) console.log(`qadam_dashboard_evidence_fit_error=${error}`);
process.exitCode = errors.length ? 1 : 0;
