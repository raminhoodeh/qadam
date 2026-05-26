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
const auditPath = path.join(repoRoot, "docs", "qadam-dashboard-overhaul-dx-9-performance-audit-2026-05-25.md");

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
        "Performance workspace",
        "30-day demo proof and paper account performance",
        "30-day run separate from 100-trade maturity",
        "No forced trades",
        "Phase 5 trades excluded",
        "No proof-credit inference"
    ], "Performance workspace static shell");

    includesAll(css, [
        ".performance-workspace",
        ".performance-workspace-head",
        ".performance-boundary-card",
        ".performance-status-grid",
        ".performance-status-card",
        ".performance-progress-card",
        ".performance-progress-bar",
        ".performance-section",
        ".performance-two-col",
        ".paper-account-live-board",
        ".paper-account-balance-card",
        ".paper-equity-chart-card",
        ".paper-equity-chart",
        ".paper-equity-chart-summary",
        "html[data-dashboard-active-view=\"performance\"] .capital-panel"
    ], "Performance workspace CSS");

    includesAll(renderer, [
        "function renderPerformanceWorkspace",
        "function renderPerformanceStatusCard",
        "function renderPerformanceProgress",
        "function renderPerformanceSourceRecord",
        "function renderPaperAccountEquityChart",
        "function paperAccountEquityPoints",
        "operational_vs_maturity",
        "risk_state",
        "proof_quality",
        "safety_boundary",
        "forced_trade_pressure_detected"
    ], "Performance workspace renderer");

    const window = loadRendererWindow();
    assert(typeof window.buildQadamDashboardPerformanceModel === "function", "performance model builder not exported");
    const model = window.buildQadamDashboardPerformanceModel(status);
    const demo = model.demo_proof || {};
    const risk = model.risk_state || {};
    const maturity = model.operational_vs_maturity || {};
    const quality = model.proof_quality || {};
    const safety = model.safety_boundary || {};

    assert(model.id === "performance", "performance model id mismatch");
    assert(demo.required_calendar_day_count === 30, "demo proof should use 30 calendar days");
    assert(demo.proof_week_count === 5, "demo proof should expose five proof weeks");
    assert(demo.weekly_proof_trade_target === 3, "weekly proof target should be three trades");
    assert(demo.weekly_target_formula === "min(3, qualified setup count)", "weekly target formula missing");
    assert(demo.candidate_setup_count >= 1, "candidate setup count should be visible");
    assert(demo.phase5_test_trades_count_for_phase7 === false, "Phase 5 test trades must not count for Phase 7");
    assert(demo.display_proof_credit_allowed === false, "dashboard must not infer proof credit");
    assert(demo.ui_inferred_readiness_count === 0, "performance dashboard inferred readiness from UI");
    assert(risk.drawdown_within_cap === true, "drawdown should be within cap for current snapshot");
    assert(risk.risk_halt_active === false, "risk halt should not be active for current snapshot");
    assert(risk.live_capital_enabled === false, "live capital is enabled in risk state");
    assert(maturity.maturity_benchmark === 100, "100-trade maturity benchmark missing");
    assert(maturity.closed_proof_trade_count === demo.closed_proof_trade_count, "maturity and demo proof counts disagree");
    assert(maturity.phase7_mature_benchmark_met === false, "maturity benchmark should not be met");
    assert(maturity.phase7_statistical_immaturity_hidden === false, "statistical immaturity must remain visible");
    assert(/separate/i.test(maturity.boundary), "operational-vs-maturity boundary is weak");
    assert(quality.source_status_records.length >= 10, "Phase 7 source records missing");
    assert(quality.source_status_records.every((record) => record.ui_inferred_readiness === false), "source records inferred readiness from UI");
    assert(safety.forced_trade_pressure_detected === false, "forced trade pressure detected");
    assert(safety.broker_post_called_count === 0, "broker POST count must be zero");
    assert(safety.unsafe_write_counter_total === 0, "unsafe write counter must be zero");
    assert(safety.live_capital_enabled_count === 0, "live capital grant count must be zero");
    assert(/no forced trades/i.test(model.boundary), "performance boundary must block forced trades");

    const rendered = await renderWithStatus(status);
    const performanceHtml = html(rendered, "[data-capital]");
    [
        "Performance workspace",
        "30-day demo proof and paper account performance",
        "30-day run separate from 100-trade maturity",
        "No forced trades",
        "Phase 5 trades excluded",
        "No proof-credit inference",
        "Demo day",
        "Proof week",
        "Qualified setups",
        "Drawdown and halt state",
        "Proof cadence",
        "Setup funnel",
        "Paper mirror",
        "Paper trading account",
        "Live paper equity graph",
        "Paper trading account equity over time",
        "Proof lifecycle",
        "Operational completion vs maturity",
        "100-trade maturity benchmark",
        "Statistical maturity is tracked separately",
        "No forced trade pressure",
        "Backend source records",
        "no UI inference",
        "live capital disabled",
        "Is the paper account proving or losing trust?"
    ].forEach((needle) => assert(performanceHtml.includes(needle), `rendered performance workspace missing ${needle}`));

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
        assert(!performanceHtml.includes(needle), `performance workspace leaked non-public-safe marker ${needle}`);
    });

    [
        "DX-9 - Performance Workspace",
        "Move Money into Performance",
        "Separate operational completion from statistical maturity",
        "scripts/check_dashboard_overhaul_performance.js"
    ].forEach((needle) => {
        assert(plan.includes(needle), `master plan missing DX-9 marker: ${needle}`);
    });
    assert(fs.existsSync(auditPath), "DX-9 audit document missing");

    console.log("dashboard_overhaul_performance=ok");
    console.log("dashboard_performance_demo_day_count=" + demo.required_calendar_day_count);
    console.log("dashboard_performance_weekly_target=" + demo.weekly_proof_trade_target);
    console.log("dashboard_performance_maturity_benchmark=" + maturity.maturity_benchmark);
    console.log("dashboard_performance_source_record_count=" + quality.source_status_records.length);
    console.log("dashboard_performance_forced_trade_pressure=False");
    console.log("dashboard_performance_authority_unchanged=True");
}

if (require.main === module) {
    main().catch((error) => {
        console.error(error.message);
        process.exitCode = 1;
    });
}
