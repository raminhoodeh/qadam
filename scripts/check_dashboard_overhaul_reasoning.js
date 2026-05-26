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
const auditPath = path.join(repoRoot, "docs", "qadam-dashboard-overhaul-dx-8-reasoning-audit-2026-05-25.md");

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
        "Reasoning workspace",
        "Priors, evidence, hypotheses, and blockers",
        "Prior, not evidence",
        "Hypothesis, not candidate",
        "No paper/order authority",
        "Merged into Reasoning workspace"
    ], "Reasoning static shell");

    includesAll(css, [
        ".reasoning-workspace",
        ".reasoning-workspace-head",
        ".reasoning-boundary-card",
        ".reasoning-lane-grid",
        ".reasoning-prior-grid",
        ".reasoning-hypothesis-card",
        ".reasoning-evidence-grid",
        ".reasoning-missing-grid",
        ".reasoning-review-grid",
        ".reasoning-quant-card",
        ".reasoning-merge-note"
    ], "Reasoning workspace CSS");

    includesAll(renderer, [
        "function renderReasoningWorkspace",
        "function renderWorldviewPriorSummary",
        "function renderReasoningHypothesisSummary",
        "function renderReasoningEvidenceSummary",
        "function renderMissingCorroborationCard",
        "function renderReasoningReviewCard",
        "function renderQuantAnnotationCard",
        "worldview_prior",
        "hypothesis_queue",
        "missing_corroboration",
        "quant_annotation"
    ], "Reasoning workspace renderer");

    const window = loadRendererWindow();
    assert(typeof window.buildQadamDashboardReasoningModel === "function", "reasoning model builder not exported");
    const model = window.buildQadamDashboardReasoningModel(status);

    assert(model.id === "reasoning", "reasoning model id mismatch");
    assert(Array.isArray(model.lanes) && model.lanes.length === 6, "reasoning model must expose six reasoning lanes");
    assert(model.worldview_prior?.is_evidence === false, "worldview prior must not be evidence");
    assert(model.worldview_prior?.evidence_role === "prior_not_evidence", "worldview prior role must be explicit");
    assert(model.worldview_prior.active_lenses.length > 0, "worldview priors are missing");
    model.worldview_prior.active_lenses.forEach((lens) => {
        assert(lens.is_evidence === false, `${lens.key} is incorrectly marked as evidence`);
        assert(lens.trade_authority === false, `${lens.key} exposes trade authority`);
        assert(/prior/i.test(lens.evidence_boundary), `${lens.key} boundary does not label it as a prior`);
    });

    assert(model.hypothesis_queue.length > 0, "hypothesis queue missing");
    model.hypothesis_queue.forEach((hypothesis) => {
        assert(hypothesis.is_trade_candidate === false, `${hypothesis.signal_id} became a candidate`);
        assert(hypothesis.paper_order_allowed === false, `${hypothesis.signal_id} allows paper orders`);
        assert(hypothesis.order_authority === false, `${hypothesis.signal_id} exposes order authority`);
        assert(/Hypothesis, not candidate/i.test(hypothesis.boundary), `${hypothesis.signal_id} boundary is weak`);
    });

    assert(model.evidence_packets.length > 0, "evidence packet index missing");
    model.evidence_packets.forEach((packet) => {
        assert(packet.source_count >= 1, `${packet.trail_id} has no sources`);
        assert(packet.items.length >= 1, `${packet.trail_id} has no evidence items`);
        assert(/cannot create a candidate or order/i.test(packet.boundary), `${packet.trail_id} boundary is weak`);
    });

    assert(model.missing_corroboration.length > 0, "missing corroboration blockers are missing");
    assert(
        model.missing_corroboration.some((item) => /source|risk|market|corroboration|challenge/i.test(item.label)),
        "missing corroboration records are not recognizable"
    );
    assert(model.review_chain.length === 4, "review chain should include Research Analyst, Strategy Lead, Signal Integrity, and Head of Quant");
    model.review_chain.forEach((review) => {
        assert(review.can_advance_trade === false, `${review.label} can advance trade`);
        assert(/authority|only|orders|write/i.test(review.boundary), `${review.label} boundary is weak`);
    });
    assert(model.quant_annotation.recommendation, "quant annotation recommendation missing");
    assert(model.quant_annotation.execution_allowed === false, "quant annotation allows execution");
    assert(model.quant_annotation.paper_order_allowed === false, "quant annotation allows paper orders");
    assert(model.quant_annotation.trade_candidate_created_count === 0, "quant annotation creates candidates");
    assert(/Priors are not evidence|Reasoning is research-only/i.test(model.boundary), "reasoning boundary is weak");

    const rendered = await renderWithStatus(status);
    const cognitionHtml = html(rendered, "[data-cognition]");
    const worldviewHtml = html(rendered, "[data-worldview]");

    [
        "Reasoning workspace",
        "Worldview prior",
        "Question generator, not proof",
        "Prior, not evidence",
        "Hypothesis queue",
        "Why ideas advanced, stalled, or were blocked",
        "Hypothesis, not candidate",
        "Factual evidence",
        "Evidence packets and source trail",
        "Missing corroboration",
        "Normal blockers before trade state",
        "Strategy Lead review",
        "Head of Quant annotation",
        "Quant/quantum annotation",
        "No paper/order authority",
        "Research Analyst review",
        "Signal Integrity review"
    ].forEach((needle) => assert(cognitionHtml.includes(needle), `rendered reasoning workspace missing ${needle}`));

    assert(worldviewHtml.includes("Merged into Reasoning workspace"), "worldview panel does not point back to Reasoning");
    assert(worldviewHtml.includes("Decision chain"), "worldview prior index lost the decision chain");

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
        assert(!cognitionHtml.includes(needle), `reasoning workspace leaked non-public-safe marker ${needle}`);
    });

    assertIncludes(rendered, "[data-cognition]", "Current focus");
    assertIncludes(rendered, "[data-cognition]", "Hypotheses and evidence");
    assertIncludes(rendered, "[data-cognition]", "Evidence packet index");

    [
        "DX-8 - Reasoning Workspace",
        "Separate worldview prior, hypothesis, evidence packet, missing",
        "scripts/check_dashboard_overhaul_reasoning.js"
    ].forEach((needle) => {
        assert(plan.includes(needle), `master plan missing DX-8 marker: ${needle}`);
    });
    assert(fs.existsSync(auditPath), "DX-8 audit document missing");

    console.log("dashboard_overhaul_reasoning=ok");
    console.log("dashboard_reasoning_lane_count=" + model.lanes.length);
    console.log("dashboard_reasoning_prior_count=" + model.worldview_prior.active_lenses.length);
    console.log("dashboard_reasoning_hypothesis_count=" + model.hypothesis_queue.length);
    console.log("dashboard_reasoning_missing_corroboration_count=" + model.missing_corroboration.length);
    console.log("dashboard_reasoning_review_chain_count=" + model.review_chain.length);
    console.log("dashboard_reasoning_authority_unchanged=True");
}

if (require.main === module) {
    main().catch((error) => {
        console.error(error.message);
        process.exitCode = 1;
    });
}
