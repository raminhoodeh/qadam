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
const auditPath = path.join(repoRoot, "docs", "qadam-dashboard-overhaul-dx-10-operations-audit-2026-05-25.md");

const dashboardHtml = fs.readFileSync(htmlPath, "utf8");
const css = fs.readFileSync(cssPath, "utf8");
const renderer = fs.readFileSync(rendererPath, "utf8");
const plan = fs.readFileSync(planPath, "utf8");

function includesAll(text, needles, label) {
    needles.forEach((needle) => {
        assert(text.includes(needle), `${label} missing ${needle}`);
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
        "Operations workspace",
        "Operations readout and full system map",
        "data-operations-consolidated-readout",
        "data-operations-review-groups",
        "data-operations-review-group=\"runtime_safety\"",
        "data-operations-review-group=\"team_data_plumbing\"",
        "data-operations-review-group=\"system_map_event_trail\"",
        "data-operations-review-group=\"governance_comms_audit\"",
        "What is broken?",
        "Safety Status above",
        "Runtime, bridge, and safety",
        "Operating team and data plumbing",
        "Full system map and event trail",
        "Governance and communications audit",
        "Full system map",
        "Expand diagnostics",
        "Event Log references",
        "Authority boundary",
        "Edge state",
        "research only"
    ], "Operations workspace static shell");

    includesAll(css, [
        ".operations-workspace",
        ".operations-consolidated-readout",
        ".operations-consolidated-metrics",
        ".operations-review-groups",
        ".operations-review-group",
        ".operations-review-group-body",
        ".operations-workspace-head",
        ".operations-broken-card",
        ".operations-safety-reference",
        ".operations-role-grid",
        ".operations-diagnostics-grid",
        ".operations-feed-grid",
        ".operations-full-map",
        ".operations-edge-legend",
        ".operations-node-diagnostics",
        "html[data-dashboard-active-view=\"operations\"] .system-map-panel"
    ], "Operations workspace CSS");

    includesAll(renderer, [
        "const OPERATIONS_ROLE_SPINE",
        "function buildOperationsFeedClusters",
        "function buildOperationsRoleSpine",
        "function renderOperationsWorkspace",
        "function renderOperationsReviewGroup",
        "function renderOperationsNodeDetails",
        "function renderOperationsFeedCluster",
        "function renderOperationsEdge",
        "operations_review_groups",
        "operations-full-map",
        "What is broken?",
        "operations-safety-reference",
        "Safety Status above"
    ], "Operations workspace renderer");

    const window = loadRendererWindow();
    assert(typeof window.buildQadamDashboardOperationsModel === "function", "operations model builder not exported");
    const operations = window.buildQadamDashboardOperationsModel(status, { key: "static_snapshot" });
    const connectivity = operations.system_connectivity_model || {};
    const edgeStates = new Set((connectivity.edges || []).map((edge) => edge.state));
    const roleLabels = (operations.role_spine || []).map((role) => role.label);
    const feedLabels = (connectivity.feed_clusters || []).map((cluster) => cluster.label);

    assert(operations.id === "operations", "operations model id mismatch");
    assert(operations.operations_review_groups.length === 4, "operations model should expose four D11I review groups");
    assert(connectivity.id === "system_connectivity_model", "operations missing shared connectivity model");
    assert(connectivity.operations_scope?.placement === "operations-full-map", "operations full-map placement missing");
    assert(connectivity.overview_scope?.placement === "overview-mini-map", "overview mini-map placement missing");
    assert(connectivity.nodes.length >= 20, "operations full map should expose backend nodes");
    assert(connectivity.edges.length > 0, "operations full map should expose edges");
    ["active", "shadow/context-only", "locked", "blocked"].forEach((state) => {
        assert(edgeStates.has(state), `operations edge state missing ${state}`);
    });
    [
        "Fund Manager supervisor",
        "Live data feed clusters",
        "Qadam Orchestrator",
        "Local LLM Research Analyst",
        "Frontier LLM Strategy Lead",
        "Quantum/Classical Head of Quant",
        "Signal/Risk Gates",
        "Paper Lifecycle",
        "Learning Loop"
    ].forEach((label) => assert(roleLabels.includes(label), `missing operations role ${label}`));
    [
        "Conflict and geopolitics",
        "Physical world, energy, shipping, and weather",
        "Macro, rates, and policy",
        "Markets, broker, and prediction markets",
        "Narrative, filings, social, and news"
    ].forEach((label) => assert(feedLabels.includes(label), `missing feed cluster ${label}`));
    assert(connectivity.feed_clusters.length >= 5, "operations feed clusters missing");
    assert(operations.runtime.live_bridge_read_only === true, "live bridge must remain read-only");
    assert(operations.runtime.public_safe === true, "operations runtime must be public-safe");
    assert(operations.safety.live_capital_enabled === false, "operations reports live capital enabled");
    assert(operations.safety.authority_flags.length === 0, "operations authority flags present");
    assert(operations.diagnostics.exporter_state.static_fallback.includes("cockpit-status.json"), "exporter static fallback missing");
    assert(operations.diagnostics.kill_switch.blocking_count === 0, "kill-switch ledger should not be blocking");

    const rendered = await renderWithStatus(status);
    const operationsHtml = html(rendered, "[data-flow-map]");
    [
        "Operations workspace",
        "Operations readout and full system map",
        "Runtime, bridge, and safety",
        "Operating team and data plumbing",
        "Full system map and event trail",
        "Governance and communications audit",
        "What is broken?",
        "Safety Status above",
        "Fund Manager supervisor",
        "Live data feed clusters",
        "Qadam Orchestrator",
        "Local LLM Research Analyst",
        "Frontier LLM Strategy Lead",
        "Quantum/Classical Head of Quant",
        "Signal/Risk Gates",
        "Paper Lifecycle",
        "Learning Loop",
        "Bridge and snapshot",
        "Exporter and cache",
        "Module health",
        "Certification diagnostics",
        "Kill-switch ledger",
        "Full system map",
        "Q5-13 Functional System Map Dashboard",
        "Backend parity",
        "Unsafe controls",
        "canonical sources",
        "Yahoo Finance supplemental market confirmation only",
        "Preference/PREF MCP",
        "live capital disabled",
        "paper submit path 1",
        "dashboard does not say trading",
        "Edge state",
        "shadow/context-only",
        "Expand diagnostics",
        "Latest heartbeat",
        "Dependencies",
        "Degraded reasons",
        "Event Log references",
        "Authority boundary",
        "Related dashboard links",
        "Watched Sources",
        "Secure Live Bridge",
        "Research Analyst",
        "Strategy Lead",
        "Head of Quant",
        "Risk Agent",
        "Trade Layer",
        "Postmortem Loop"
    ].forEach((needle) => assert(operationsHtml.includes(needle), `rendered operations workspace missing ${needle}`));

    [
        "/Users/",
        "api_key",
        "PREFERENCE_API_KEY",
        "ALPACA_SECRET",
        "Q_CTRL",
        "raw_payload",
        "private_payload",
        "local_path",
        "request_body",
        "broker_identifier"
    ].forEach((needle) => {
        assert(!operationsHtml.includes(needle), `operations workspace leaked non-public-safe marker ${needle}`);
    });

    [
        "DX-10 - Operations Workspace",
        "Build the full expandable System Operating Map from `system_connectivity_model`",
        "Add expandable feed clusters for the five intelligence pipelines",
        "scripts/check_dashboard_overhaul_operations.js"
    ].forEach((needle) => {
        assert(plan.includes(needle), `master plan missing DX-10 marker: ${needle}`);
    });
    assert(fs.existsSync(auditPath), "DX-10 audit document missing");

    console.log("dashboard_overhaul_operations=ok");
    console.log("dashboard_operations_role_count=" + operations.role_spine.length);
    console.log("dashboard_operations_node_count=" + connectivity.nodes.length);
    console.log("dashboard_operations_feed_cluster_count=" + connectivity.feed_clusters.length);
    console.log("dashboard_operations_edge_state_count=" + edgeStates.size);
    console.log("dashboard_operations_authority_unchanged=True");
}

if (require.main === module) {
    main().catch((error) => {
        console.error(error.message);
        process.exitCode = 1;
    });
}
