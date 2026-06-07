#!/usr/bin/env node

const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");

const {
    assert,
    assertIncludes,
    html,
    renderWithStatus,
    status
} = require("./check_dashboard_renderer.js");

const repoRoot = path.resolve(__dirname, "..");
const htmlPath = path.join(repoRoot, "landing-page-repo", "dashboard", "index.html");
const cssPath = path.join(repoRoot, "landing-page-repo", "auth.css");
const rendererPath = path.join(repoRoot, "landing-page-repo", "dashboard.js");
const planPath = path.join(repoRoot, "docs", "qadam-dashboard-overhaul-master-implementation-plan.md");
const auditPath = path.join(repoRoot, "docs", "qadam-dashboard-overhaul-dx-6-trades-audit-2026-05-25.md");

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
        "data-trades-workspace",
        "Trade lifecycle board",
        "Verified performance only"
    ], "Trades workspace static shell");

    includesAll(css, [
        ".trades-workspace",
        ".trades-workspace-head",
        ".trade-lifecycle-safety",
        ".trade-lifecycle-filters",
        ".trade-lifecycle-strip",
        ".trade-proof-partitions",
        ".trade-evidence-links",
        ".trade-lifecycle-grid",
        ".trade-lifecycle-card",
        ".trade-lifecycle-card[hidden]",
        ".trade-lifecycle-topline",
        ".trade-lifecycle-links"
    ], "Trades workspace CSS");

    includesAll(renderer, [
        "TRADE_WORKSPACE_FILTERS",
        "function tradeLifecycleRecord",
        "function renderTradeLifecycleWorkspace",
        "function initTradeLifecycleFilters",
        "data-trade-lifecycle-filter",
        "data-trade-lifecycle-card",
        "data-filter-states",
        "phase5_test_lifecycle",
        "phase7_demo_proof",
        "trade-risk-policy",
        "trade-broker-receipts"
    ], "Trades workspace renderer");

    const window = loadRendererWindow();
    assert(typeof window.buildQadamDashboardTradesModel === "function", "trades model builder not exported");
    const model = window.buildQadamDashboardTradesModel(status);
    const records = model.lifecycle_records || [];
    const filters = model.lifecycle_filters || [];
    const filterById = new Map(filters.map((filter) => [filter.id, filter]));
    const recordKinds = new Set(records.map((record) => record.kind));

    assert(model.id === "trades", "trades model id mismatch");
    assert(model.lifecycle.length >= 9, "trades model must expose the complete lifecycle ladder");
    assert(records.length >= 6, "trades model must expose concrete lifecycle records");
    assert(model.counts.submitted_paper_order >= 1, "capital paper orders must count as submitted lifecycle records");
    assert(model.counts.closed_paper_trade >= 1, "closed trades must be exposed");
    assert(model.counts.postmortem_due >= 1, "postmortem due state must be exposed");
    [
        "observed_signal",
        "candidate",
        "blocked",
        "submitted_paper_order",
        "closed_paper_trade",
        "postmortem_due"
    ].forEach((kind) => assert(recordKinds.has(kind), `missing lifecycle record kind ${kind}`));

    [
        "all",
        "active",
        "blocked",
        "open",
        "closed",
        "postmortem_due"
    ].forEach((filterId) => assert(filterById.has(filterId), `missing lifecycle filter ${filterId}`));
    assert(filterById.get("all").count === records.length, "all filter must count every lifecycle record");
    assert(filterById.get("postmortem_due").count >= 1, "postmortem due filter must expose due reviews");

    const candidate = records.find((record) => record.kind === "candidate");
    const submitted = records.find((record) => record.kind === "submitted_paper_order");
    assert(candidate.filters.includes("active"), "candidate record should be active");
    assert(!candidate.filters.includes("open"), "candidate record must not appear as an open order");
    assert(!candidate.filters.includes("closed"), "candidate record must not appear as a closed trade");
    assert(submitted.filters.includes("all"), "submitted paper order must remain visible in the full lifecycle");
    assert(submitted.stage_label === "Submitted paper order", "submitted paper order stage label mismatch");
    assert(records.every((record) => record.phase7_proof_credit_allowed === false), "record-level proof credit must never be granted by UI model");
    assert(model.proof_partitions.phase5_test_lifecycle.counts_for_phase7_proof === false, "Phase 5 test lifecycle must not count for Phase 7 proof");
    assert(model.proof_credit.display_allowed === false, "proof credit display must remain off for non-mature status");
    assert(model.evidence_links.source_quorum.href === "#evidence", "source quorum link must point to Evidence");
    assert(model.evidence_links.risk_decision.href === "#trade-risk-policy", "risk decision link must point to trade risk section");
    assert(model.evidence_links.broker_receipt.href === "#trade-broker-receipts", "broker receipt link must point to broker receipt section");

    const rendered = await renderWithStatus(status);
    const tradeHtml = html(rendered, "[data-trade-layer]");
    [
        "Trade lifecycle board",
        "Verified performance only",
        "Trade ideas stay candidates until gated paper-order records exist",
        "Observed signal",
        "Trade idea",
        "Blocked idea",
        "Submitted paper order",
        "Closed paper trade",
        "Postmortem due",
        "Phase 5 test lifecycle",
        "Verified paper trades",
        "Source quorum",
        "Risk decision",
        "Broker receipt",
        "data-trade-lifecycle-filter",
        "data-trade-lifecycle-filter=\"postmortem_due\"",
        "data-filter-states=\"all postmortem_due\"",
        "data-trade-lifecycle-grid"
    ].forEach((needle) => assert(tradeHtml.includes(needle), `rendered trade workspace missing ${needle}`));

    [
        "DX-6 - Trades Workspace",
        "Move observed signals, qualified setups, candidates, blocked candidates",
        "Keep Phase 5 test trades visually separate from Phase 7 proof trades",
        "scripts/check_dashboard_overhaul_trades.js"
    ].forEach((needle) => {
        assert(plan.includes(needle), `master plan missing DX-6 marker: ${needle}`);
    });
    assert(fs.existsSync(auditPath), "DX-6 audit document missing");

    console.log("dashboard_overhaul_trades=ok");
    console.log("dashboard_trades_lifecycle_records=" + records.length);
    console.log("dashboard_trades_filters=6");
    console.log("dashboard_candidates_not_orders=True");
    console.log("dashboard_phase5_phase7_trade_partition=True");
    console.log("dashboard_trade_workspace_authority_unchanged=True");
}

if (require.main === module) {
    main().catch((error) => {
        console.error(error.message);
        process.exitCode = 1;
    });
}
