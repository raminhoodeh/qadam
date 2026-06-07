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
const auditPath = path.join(repoRoot, "docs", "qadam-dashboard-d11i-operations-view-2026-05-26.md");

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

function countOccurrences(text, needle) {
    return text.split(needle).length - 1;
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
        "Operations diagnostics and event trail",
        "id=\"operations-readout\"",
        "data-operations-consolidated-readout",
        "data-operations-review-groups",
        "data-operations-review-group=\"runtime_safety\"",
        "data-operations-review-group=\"team_data_plumbing\"",
        "data-operations-review-group=\"system_map_event_trail\"",
        "data-operations-review-group=\"governance_comms_audit\"",
        "/auth.css?v=20260607-cc10-remove-view-card",
        "/dashboard.js?v=20260607-cc10-remove-view-card"
    ], "D11I Operations static shell");

    assert(countOccurrences(dashboardHtml, "legacy-operations-panel") === 0, "legacy Operations panels should be removed after CC2");

    includesAll(css, [
        ".operations-consolidated-readout",
        ".operations-consolidated-metrics",
        ".operations-review-groups",
        ".operations-review-group",
        ".operations-review-group-body",
        ".operations-event-trail",
        ".operations-governance-audit"
    ], "D11I Operations CSS");

    includesAll(renderer, [
        "function renderOperationsReviewGroup",
        "operations_review_groups",
        "runtime_safety",
        "team_data_plumbing",
        "system_map_event_trail",
        "governance_comms_audit",
        "operations-consolidated-readout",
        "Process console merged into Operations",
        "No Telegram command path"
    ], "D11I Operations renderer");

    const window = loadRendererWindow();
    assert(typeof window.buildQadamDashboardOperationsModel === "function", "operations model builder missing");
    const model = window.buildQadamDashboardOperationsModel(status, { key: "static_snapshot" });
    const groupIds = new Set(model.operations_review_groups.map((group) => group.id));

    assert(model.id === "operations", "operations model id mismatch");
    assert(model.operations_review_groups.length === 4, "Operations view must expose four consolidated review groups");
    ["runtime_safety", "team_data_plumbing", "system_map_event_trail", "governance_comms_audit"].forEach((id) => {
        assert(groupIds.has(id), `Operations review group missing ${id}`);
    });
    assert(model.runtime.live_bridge_read_only === true, "live bridge must remain read-only");
    assert(model.runtime.public_safe === true, "Operations runtime must stay public-safe");
    assert(model.safety.live_capital_enabled === false, "Operations reports live capital enabled");
    assert(model.safety.authority_flags.length === 0, "Operations authority flags present");
    assert(model.communications_audit.command_path_enabled === false, "Telegram command path became enabled");
    assert(model.communications_audit.live_send_allowed_count === 0, "Telegram live sends became enabled");
    assert(model.system_connectivity_model.operations_scope?.placement === "operations-diagnostics", "Operations diagnostics placement changed");

    const rendered = await renderWithStatus(status);
    const operationsHtml = html(rendered, "[data-flow-map]");

    includesAll(operationsHtml, [
        "Operations workspace",
        "Operations diagnostics and event trail",
        "Runtime, bridge, and safety",
        "Operating team and data plumbing",
        "System map diagnostics and event trail",
        "Governance, inbox, and communications audit",
        "Hard safety stops",
        "Operating team diagnostics",
        "Live data feed clusters",
        "System map diagnostics",
        "Recent runtime events",
        "Process console merged into Operations",
        "Governance and outbound communications",
        "Fund Manager review and Telegram state",
        "No Telegram command path",
        "No browser shell",
        "Open the Overview tab for the single canonical node-by-node system map",
        "Read-only bridge",
        "OK - live capital off"
    ], "rendered D11I Operations");

    assert(countOccurrences(operationsHtml, "data-operations-review-group=") === 4, "Operations should render exactly four review groups");
    excludesAll(operationsHtml, [
        "Panel readout",
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
    ], "rendered D11I Operations");

    assert(fs.existsSync(auditPath), "D11I audit document missing");
    includesAll(plan, [
        "D11I - Operations View",
        "scripts/check_dashboard_d11i_operations_view.js",
        "D11J - Tooltip Simplification"
    ], "D11I master plan");

    console.log("dashboard_d11i_operations_view=ok");
    console.log("dashboard_d11i_review_group_count=" + model.operations_review_groups.length);
    console.log("dashboard_d11i_legacy_operations_panel_count=0");
    console.log("dashboard_d11i_telegram_command_path_enabled=False");
    console.log("dashboard_authority_unchanged=True");
}

if (require.main === module) {
    main().catch((error) => {
        console.error(error.message);
        process.exitCode = 1;
    });
}
