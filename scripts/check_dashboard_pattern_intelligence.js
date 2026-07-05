#!/usr/bin/env node

const fs = require("node:fs");
const path = require("node:path");

const {
    assert,
    html,
    renderWithStatus,
    status
} = require("./check_dashboard_renderer.js");

const repoRoot = path.resolve(__dirname, "..");
const runtimeDir = path.join(repoRoot, "data", "runtime");

const artifactMap = {
    status: "qsase_dashboard_status.json",
    portfolio_value: "qsase_dashboard_portfolio_value_series.json",
    current_portfolio: "qsase_dashboard_current_portfolio.json",
    trading_history: "qsase_dashboard_trading_history.json",
    source_network: "qsase_dashboard_source_network.json",
    strategy_universe: "qsase_dashboard_strategy_universe.json",
    pattern_lab: "qsase_dashboard_pattern_lab.json",
    trade_intents: "qsase_dashboard_trade_intents.json",
    pattern_to_paper_workflow: "qsase_pattern_to_paper_workflow.json",
    pattern_intelligence: "qsase_pattern_intelligence.json",
    learning_ledger: "qsase_dashboard_learning_ledger.json",
    repair_queue: "qsase_dashboard_repair_queue.json",
    router: "qsase_strategy_router_decisions.json",
    paperops_gate: "qsase_paperops_gate_interface.json"
};

function readJson(filename) {
    const artifactPath = path.join(runtimeDir, filename);
    assert(fs.existsSync(artifactPath), `missing runtime artifact ${filename}`);
    return JSON.parse(fs.readFileSync(artifactPath, "utf8"));
}

function clone(value) {
    return JSON.parse(JSON.stringify(value));
}

function buildQsaseFixture() {
    const primary = readJson(artifactMap.status);
    const sections = Object.fromEntries(
        Object.entries(artifactMap)
            .filter(([key]) => key !== "status")
            .map(([key, filename]) => [key, readJson(filename)])
    );
    return {
        ...primary,
        schema_version: "qsase_public_dashboard.v1",
        status: primary.status || "qsase_dashboard_visibility_ready",
        public_safe: true,
        read_only: true,
        command_disabled: true,
        paper_only: true,
        sections,
        boundary: "Public dashboard visibility only. QSASE cannot create orders, approvals, broker writes, Telegram commands, live-capital authority, or paper proof ledger credit.",
        authority_flags: {
            creates_trade_candidates: false,
            creates_paper_orders: false,
            grants_proof_credit: false,
            enables_live_capital: false,
            sends_broker_writes: false,
            telegram_command_path_enabled: false
        }
    };
}

async function main() {
    const fixtureStatus = clone(status);
    fixtureStatus.qsase_dashboard = buildQsaseFixture();
    const rendered = await renderWithStatus(fixtureStatus);
    const stageHtml = html(rendered, "[data-stage7-dashboard-visibility]");

    [
        "Pattern Recognition Findings",
        "Qadam's current read",
        "Detected signal",
        "Market affected",
        "Evidence",
        "What Qadam thinks",
        "What would confirm it",
        "What blocks the trade",
        "Next action",
        "Technical evidence ledger",
        "These are pattern-recognition findings, not orders"
    ].forEach((needle) => {
        assert(stageHtml.includes(needle), `pattern intelligence UI missing ${needle}`);
    });

    [
        "Pattern &amp; Opportunity Lab",
        "Pattern-To-Paper Workflow",
        "PaperOps handoff candidate",
        "Telegram candidate"
    ].forEach((needle) => {
        assert(!stageHtml.includes(needle), `pattern intelligence UI still shows internal/legacy copy ${needle}`);
    });

    assert(
        !/\d+\s+linear\s+·\s+\d+\s+nonlinear/i.test(stageHtml),
        "pattern intelligence UI still leads with raw linear/nonlinear counts"
    );

    const intelligence = readJson(artifactMap.pattern_intelligence);
    assert(intelligence.artifact_type === "qsase_pattern_intelligence", "pattern intelligence artifact type invalid");
    assert(Number(intelligence.finding_count || 0) > 0, "pattern intelligence artifact has no findings");
    assert(intelligence.human_brief?.telegram_live_send_allowed === false, "human brief live send must be disabled");
    assert(intelligence.human_brief?.telegram_command_path_enabled === false, "human brief command path must be disabled");
    intelligence.findings.forEach((finding) => {
        [
            "detected_signal",
            "market_affected",
            "source_signal_summary",
            "evidence_summary",
            "what_qadam_thinks",
            "what_would_confirm",
            "what_blocks_trade",
            "next_action",
            "stage_label"
        ].forEach((field) => assert(finding[field], `finding ${finding.finding_id} missing ${field}`));
        assert(finding.paper_order_allowed === false, `finding ${finding.finding_id} can create paper orders`);
        assert(finding.broker_write_allowed === false, `finding ${finding.finding_id} can write to broker`);
        assert(finding.live_capital_enabled === false, `finding ${finding.finding_id} can enable live capital`);
    });

    console.log("dashboard_pattern_intelligence=ok");
}

if (require.main === module) {
    main().catch((error) => {
        console.error(error.message);
        process.exitCode = 1;
    });
}
