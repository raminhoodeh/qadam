#!/usr/bin/env node

const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");

const repoRoot = path.resolve(__dirname, "..");
const rendererPath = path.join(repoRoot, "landing-page-repo", "dashboard.js");
const htmlPath = path.join(repoRoot, "landing-page-repo", "dashboard", "index.html");
const statusPath = path.join(repoRoot, "landing-page-repo", "status", "cockpit-status.json");
const planPath = path.join(repoRoot, "docs", "qadam-dashboard-overhaul-master-implementation-plan.md");
const auditPath = path.join(repoRoot, "docs", "qadam-dashboard-d11k-view-model-refactor-2026-05-26.md");

const renderer = fs.readFileSync(rendererPath, "utf8");
const html = fs.readFileSync(htmlPath, "utf8");
const status = JSON.parse(fs.readFileSync(statusPath, "utf8"));
const plan = fs.readFileSync(planPath, "utf8");

function assert(condition, message) {
    if (!condition) throw new Error(message);
}

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
        fetch: async () => ({ ok: true, json: async () => ({}) }),
        localStorage: {
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

function main() {
    const window = loadRendererWindow();
    assert(typeof window.buildQadamDashboardViewModels === "function", "dashboard view-model builder missing");
    const models = window.buildQadamDashboardViewModels(status, { key: "live_bridge" });

    assert(models.schema_version === "dashboard_view_models.v1", "schema compatibility changed");
    assert(models.model_contract_version === "dashboard_view_models.cc5.founder_contract.v1", "D11K model contract missing");
    assert(models.model_graph?.contract === "single_shared_dashboard_view_model_bundle", "model graph contract missing");
    assert(models.model_graph?.renderer_entrypoint === "renderQadamDashboardStatus", "model graph renderer entrypoint missing");
    assert(models.model_graph?.renderer_uses_shared_bundle === true, "renderer shared-bundle flag missing");

    includesAll(JSON.stringify(models.model_graph), [
        "founder_contract_model",
        "sources_model",
        "trades_model",
        "reasoning_model",
        "performance_model",
        "governance_model",
        "system_connectivity_model",
        "operations_model",
        "overview_model",
        "safety_strip_model"
    ], "D11K model graph");

    assert(
        models.operations_model.system_connectivity_model === models.system_connectivity_model,
        "Operations must reuse the top-level System Connectivity model object"
    );
    assert(
        models.overview_model.model_dependencies.system_connectivity_model === "system_connectivity_model",
        "Overview must declare shared System Connectivity dependency"
    );
    assert(
        models.trades_model.model_dependencies.sources_model === "sources",
        "Trades must declare shared Sources dependency"
    );
    assert(
        models.operations_model.model_dependencies.governance_model === "governance",
        "Operations must declare shared Governance dependency"
    );

    includesAll(renderer, [
        "function buildTradesModel(status = {}, sharedModels = {})",
        "const sourceModel = sharedModels.sources_model || buildSourcesModel(status);",
        "function buildOperationsModel(status = {}, source = {}, sharedModels = {})",
        "const connectivity = sharedModels.system_connectivity_model || buildSystemConnectivityModel(status);",
        "const governance = sharedModels.governance_model || buildGovernanceModel(status);",
        "function buildOverviewModel(status = {}, source = {}, sharedOperations = null, sharedModels = {})",
        "model_contract_version: \"dashboard_view_models.cc5.founder_contract.v1\"",
        "model_graph: modelGraph",
        "function renderWatching(status, viewModels = {})",
        "function renderCognition(status, viewModels = {})",
        "function renderTrades(status, viewModels = {})",
        "function renderCapital(status, viewModels = {})",
        "function renderFundManagerNotes(status, viewModels = {})",
        "renderWatching(status, viewModels)",
        "renderCognition(status, viewModels)",
        "renderTrades(status, viewModels)",
        "renderCapital(status, viewModels)",
        "renderFundManagerNotes(status, viewModels)"
    ], "D11K renderer contract");

    [
        "renderWatching(status);",
        "renderCognition(status);",
        "renderTrades(status);",
        "renderCapital(status);",
        "renderFundManagerNotes(status);"
    ].forEach((needle) => {
        assert(!renderer.includes(needle), `canonical render path still omits shared view models: ${needle}`);
    });

    includesAll(html, [
        "/auth.css?v=20260607-cc8-prune-docs",
        "/dashboard.js?v=20260607-cc8-prune-docs"
    ], "D11K cache key");

    assert(fs.existsSync(auditPath), "D11K audit document missing");
    includesAll(plan, [
        "D11K - View Model Refactor",
        "scripts/check_dashboard_d11k_view_model_refactor.js",
        "D11L - Visual Simplification"
    ], "D11K master plan");

    const payload = JSON.stringify(models);
    [
        "/Users/",
        "ALPACA_SECRET",
        "Q_CTRL",
        "PREFERENCE_API_KEY",
        "private_payload",
        "local_path",
        "request_body",
        "broker_identifier"
    ].forEach((needle) => {
        assert(!payload.includes(needle), `D11K model bundle leaked non-public-safe marker ${needle}`);
    });

    console.log("dashboard_d11k_view_model_refactor=ok");
    console.log(`dashboard_d11k_model_build_order_count=${models.model_graph.build_order.length}`);
    console.log("dashboard_d11k_shared_bundle=True");
    console.log("dashboard_authority_unchanged=True");
}

main();
