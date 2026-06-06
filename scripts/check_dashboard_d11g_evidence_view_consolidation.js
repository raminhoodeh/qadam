#!/usr/bin/env node

const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");

const {
    assert,
    html,
    renderWithStatus,
    status
} = require("./check_dashboard_renderer.js");

const repoRoot = path.resolve(__dirname, "..");
const htmlPath = path.join(repoRoot, "landing-page-repo", "dashboard", "index.html");
const cssPath = path.join(repoRoot, "landing-page-repo", "auth.css");
const rendererPath = path.join(repoRoot, "landing-page-repo", "dashboard.js");
const planPath = path.join(repoRoot, "docs", "qadam-dashboard-overhaul-master-implementation-plan.md");
const auditPath = path.join(repoRoot, "docs", "qadam-dashboard-d11g-evidence-view-consolidation-2026-05-26.md");

const dashboardHtml = fs.readFileSync(htmlPath, "utf8");
const css = fs.readFileSync(cssPath, "utf8");
const renderer = fs.readFileSync(rendererPath, "utf8");
const plan = fs.readFileSync(planPath, "utf8");

function includesAll(text, needles, label) {
    needles.forEach((needle) => {
        assert(text.includes(needle), `${label} missing ${needle}`);
    });
}

function excludesAll(text, needles, label) {
    needles.forEach((needle) => {
        assert(!text.includes(needle), `${label} still includes ${needle}`);
    });
}

function loadRendererWindow() {
    const document = {
        documentElement: { dataset: {} },
        querySelector() {
            return null;
        },
        querySelectorAll() {
            return [];
        }
    };
    const window = { document };
    const context = {
        Array,
        Boolean,
        Date,
        Error,
        Intl,
        Map,
        Math,
        Number,
        Object,
        Promise,
        Set,
        String,
        console,
        document,
        fetch: async () => ({ ok: true, json: async () => status }),
        localStorage: {
            getItem() {
                return null;
            },
            setItem() {}
        },
        sessionStorage: {
            getItem() {
                return null;
            },
            setItem() {}
        },
        window
    };
    window.window = window;
    vm.createContext(context);
    vm.runInContext(renderer, context, { filename: rendererPath });
    return window;
}

async function main() {
    includesAll(dashboardHtml, [
        "Evidence",
        "Source reliability and corroboration",
        "data-evidence-consolidated-readout",
        "data-evidence-review-groups",
        "data-evidence-review-group=\"setup_evidence\"",
        "data-evidence-review-group=\"source_reliability\"",
        "data-evidence-review-group=\"supplemental_context\"",
        "data-evidence-review-group=\"factual_packets\"",
        "data-evidence-source-ledger",
        "/auth.css?v=20260605-cc2-cut",
        "/dashboard.js?v=20260605-cc2-cut"
    ], "D11G Evidence static shell");

    excludesAll(dashboardHtml, [
        "data-panel-brief=\"watching\"",
        "<div class=\"summary-strip\" data-source-summary>"
    ], "D11G Evidence static shell");

    includesAll(css, [
        ".evidence-consolidated-readout",
        ".evidence-consolidated-metrics",
        ".evidence-review-groups",
        ".evidence-review-group",
        ".evidence-source-ledger",
        ".evidence-packet-mini-grid",
        ".evidence-packet-mini-card"
    ], "D11G Evidence CSS");

    includesAll(renderer, [
        "function renderEvidencePacketMiniCard",
        "function renderEvidenceReviewGroup",
        "evidence_review_groups",
        "factual_packets",
        "Factual evidence can support review",
        "sources cannot create orders"
    ], "D11G Evidence renderer");

    const window = loadRendererWindow();
    assert(typeof window.buildQadamDashboardSourcesModel === "function", "sources model builder missing");
    const model = window.buildQadamDashboardSourcesModel(status);
    const groupIds = new Set(model.evidence_review_groups.map((group) => group.id));
    const supplementalByKey = new Map(model.supplemental.map((source) => [source.key, source]));

    assert(model.id === "sources", "sources model id changed unexpectedly");
    assert(model.label === "Evidence", "Evidence model label mismatch");
    assert(model.evidence_review_groups.length === 4, "Evidence view must expose four review groups");
    ["setup_evidence", "source_reliability", "supplemental_context", "factual_packets"].forEach((id) => {
        assert(groupIds.has(id), `Evidence review group missing ${id}`);
    });
    assert(model.evidence_packets.length > 0, "Factual evidence packets missing from Evidence view");
    assert(model.source_setup_links.length >= 3, "Setup evidence links missing from Evidence view");
    assert(supplementalByKey.get("yahoo_finance")?.proof_boundary.includes("not source quorum"), "Yahoo Finance boundary must stay supplemental");
    assert(supplementalByKey.get("preference_mcp")?.proof_boundary.includes("not source quorum"), "Preference boundary must stay supplemental");
    assert(/sources can inform research context and signal review/i.test(model.boundary), "Evidence model influence boundary is weak");
    assert(/no source can create trade ideas, approve risk, authorize orders, broker writes, or live-capital authority/i.test(model.boundary), "Evidence model authority boundary is weak");
    assert(model.source_setup_links.every((link) => !/order authority|broker write|live capital/i.test(link.proof_boundary)), "Setup evidence link implies execution authority");
    assert(model.evidence_packets.every((packet) => /cannot create trade ideas, orders, broker writes, or performance credit/i.test(packet.boundary)), "Evidence packet boundary is weak");

    const rendered = await renderWithStatus(status);
    const workspaceHtml = html(rendered, "[data-sources-workspace-slot]");
    const summaryHtml = html(rendered, "[data-source-summary]");
    const ledgerHtml = html(rendered, "[data-watching-list]");

    includesAll(workspaceHtml, [
        "Evidence readout",
        "Source reliability and corroboration",
        "Setup evidence",
        "Source reliability",
        "Supplemental context",
        "Factual evidence packets",
        "Source to setup links",
        "Reliability states",
        "Pipeline groups",
        "Yahoo Finance",
        "Preference MCP",
        "sources cannot create orders"
    ], "rendered D11G Evidence workspace");

    includesAll(summaryHtml, [
        "Sources",
        "Required not configured",
        "Research usable",
        "Signal review eligible",
        "Order authority",
        "Yahoo Finance",
        "Preference MCP"
    ], "rendered D11G Evidence summary");

    includesAll(ledgerHtml, [
        "Detailed source ledger",
        "pipeline-row",
        "ACLED API",
        "Supplemental market confirmation",
        "Preference MCP data plane",
        "evidence only"
    ], "rendered D11G Evidence ledger");

    excludesAll(`${workspaceHtml} ${summaryHtml} ${ledgerHtml}`, [
        "/Users/",
        "api_key",
        "PREFERENCE_API_KEY",
        "ALPACA_SECRET",
        "raw_payload",
        "private_payload",
        "local_path",
        "request_body",
        "broker_identifier"
    ], "rendered D11G Evidence");

    assert(fs.existsSync(auditPath), "D11G audit document missing");
    includesAll(plan, [
        "D11G - Evidence View Consolidation",
        "D11H - Reasoning View Consolidation",
        "scripts/check_dashboard_d11g_evidence_view_consolidation.js"
    ], "D11G master plan");

    console.log("dashboard_d11g_evidence_view_consolidation=ok");
    console.log("dashboard_d11g_review_group_count=" + model.evidence_review_groups.length);
    console.log("dashboard_d11g_evidence_packet_count=" + model.evidence_packets.length);
    console.log("dashboard_d11g_watching_panel_brief_removed=True");
    console.log("dashboard_authority_unchanged=True");
}

if (require.main === module) {
    main().catch((error) => {
        console.error(error.message);
        process.exitCode = 1;
    });
}
