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
const auditPath = path.join(repoRoot, "docs", "qadam-dashboard-d11h-reasoning-view-consolidation-2026-05-26.md");

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
        "Reasoning readout and review chain",
        "data-reasoning-consolidated-readout",
        "data-reasoning-review-groups",
        "data-reasoning-review-group=\"prior_evidence_basis\"",
        "data-reasoning-review-group=\"hypotheses_blockers\"",
        "data-reasoning-review-group=\"review_chain\"",
        "data-reasoning-review-group=\"advanced_diagnostics\"",
        "/auth.css?v=20260528-opportunity-scan",
        "/dashboard.js?v=20260528-opportunity-scan"
    ], "D11H Reasoning static shell");

    excludesAll(dashboardHtml, [
        "data-panel-brief=\"cognition\"",
        "Foundation cognition"
    ], "D11H Reasoning static shell");

    includesAll(css, [
        ".reasoning-consolidated-readout",
        ".reasoning-consolidated-metrics",
        ".reasoning-review-groups",
        ".reasoning-review-group",
        ".reasoning-review-group-body",
        ".reasoning-advanced-diagnostics"
    ], "D11H Reasoning CSS");

    includesAll(renderer, [
        "function renderReasoningReviewGroup",
        "reasoning_review_groups",
        "prior_evidence_basis",
        "hypotheses_blockers",
        "review_chain",
        "advanced_diagnostics",
        "Reasoning readout",
        "Model output cannot create orders"
    ], "D11H Reasoning renderer");

    const window = loadRendererWindow();
    assert(typeof window.buildQadamDashboardReasoningModel === "function", "reasoning model builder missing");
    const model = window.buildQadamDashboardReasoningModel(status);
    const groupIds = new Set(model.reasoning_review_groups.map((group) => group.id));

    assert(model.id === "reasoning", "reasoning model id mismatch");
    assert(model.reasoning_review_groups.length === 3, "Reasoning view must expose three primary review groups");
    ["prior_evidence_basis", "hypotheses_blockers", "review_chain"].forEach((id) => {
        assert(groupIds.has(id), `Reasoning review group missing ${id}`);
    });
    assert(model.worldview_prior?.is_evidence === false, "worldview prior became evidence");
    assert(model.worldview_prior?.evidence_role === "prior_not_evidence", "worldview prior role is weak");
    assert(model.hypothesis_queue.every((hypothesis) => hypothesis.is_trade_candidate === false), "hypothesis became trade idea");
    assert(model.hypothesis_queue.every((hypothesis) => hypothesis.paper_order_allowed === false), "hypothesis allows paper order");
    assert(model.evidence_packets.every((packet) => /cannot create a trade idea or order/i.test(packet.boundary)), "evidence packet boundary is weak");
    assert(model.review_chain.every((review) => review.can_advance_trade === false), "review chain can advance trade");
    assert(model.quant_annotation.execution_allowed === false, "quant annotation allows execution");
    assert(model.quant_annotation.paper_order_allowed === false, "quant annotation allows paper orders");
    assert(model.quant_annotation.trade_candidate_created_count === 0, "quant annotation creates candidates");
    assert(/Priors are not evidence|Reasoning is research-only/i.test(model.boundary), "reasoning boundary is weak");

    const rendered = await renderWithStatus(status);
    const cognitionHtml = html(rendered, "[data-cognition]");

    includesAll(cognitionHtml, [
        "Reasoning readout",
        "Can this idea move beyond research?",
        "Prior and evidence basis",
        "Hypotheses and blockers",
        "Review chain and quant annotation",
        "Advanced cognition diagnostics",
        "Question generator, not proof",
        "Factual evidence",
        "Hypothesis queue",
        "Missing corroboration",
        "Research Analyst review",
        "Strategy Lead review",
        "Signal Integrity review",
        "Head of Quant annotation",
        "Model output cannot create orders",
        "No paper/order authority"
    ], "rendered D11H Reasoning");

    excludesAll(cognitionHtml, [
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
    ], "rendered D11H Reasoning");

    assert(fs.existsSync(auditPath), "D11H audit document missing");
    includesAll(plan, [
        "D11H - Reasoning View Consolidation",
        "D11I - Operations View",
        "scripts/check_dashboard_d11h_reasoning_view_consolidation.js"
    ], "D11H master plan");

    console.log("dashboard_d11h_reasoning_view_consolidation=ok");
    console.log("dashboard_d11h_review_group_count=" + model.reasoning_review_groups.length);
    console.log("dashboard_d11h_hypothesis_count=" + model.hypothesis_queue.length);
    console.log("dashboard_d11h_cognition_panel_brief_removed=True");
    console.log("dashboard_authority_unchanged=True");
}

if (require.main === module) {
    main().catch((error) => {
        console.error(error.message);
        process.exitCode = 1;
    });
}
