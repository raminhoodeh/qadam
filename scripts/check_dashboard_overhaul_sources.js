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
const auditPath = path.join(repoRoot, "docs", "qadam-dashboard-overhaul-dx-7-sources-audit-2026-05-25.md");

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
        "data-sources-workspace",
        "Source reliability and corroboration",
        "Source quorum",
        "data-evidence-consolidated-readout",
        "data-evidence-review-groups"
    ], "Sources workspace static shell");

    includesAll(css, [
        ".sources-workspace",
        ".sources-workspace-head",
        ".source-quorum-card",
        ".source-reliability-grid",
        ".source-reliability-card",
        ".source-supplemental-grid",
        ".source-supplemental-card",
        ".source-setup-grid",
        ".source-setup-link",
        ".source-pipeline-grid",
        ".source-pipeline-card",
        ".evidence-consolidated-readout",
        ".evidence-review-group",
        ".evidence-source-ledger",
        ".source-workspace-topline .node-status"
    ], "Sources workspace CSS");

    includesAll(renderer, [
        "function renderSourcesWorkspace",
        "function renderSourceReliabilityCard",
        "function renderSupplementalSourceCard",
        "function renderSourceSetupLink",
        "function renderSourcePipelineCard",
        "function renderEvidencePacketMiniCard",
        "function renderEvidenceReviewGroup",
        "source_setup_links",
        "evidence_review_groups",
        "optional_credentials",
        "pending_adapter",
        "stale_heartbeat"
    ], "Sources workspace renderer");

    const window = loadRendererWindow();
    assert(typeof window.buildQadamDashboardSourcesModel === "function", "sources model builder not exported");
    const model = window.buildQadamDashboardSourcesModel(status);
    const reliability = model.reliability || [];
    const reliabilityByKey = new Map(reliability.map((record) => [record.key, record]));
    const supplementalByKey = new Map((model.supplemental || []).map((record) => [record.key, record]));

    assert(model.id === "sources", "sources model id mismatch");
    assert(model.pipelines.length === 5, "sources model must expose five intelligence pipelines");
    assert(reliability.length >= 10, "sources model must expose research, signal-review, order-authority, and reliability states");
    [
        "core_ok",
        "research_usable",
        "signal_review_eligible",
        "order_authority",
        "needs_attention",
        "missing_credential",
        "stale_heartbeat",
        "optional",
        "optional_credentials",
        "pending_adapter"
    ].forEach((key) => assert(reliabilityByKey.has(key), `missing reliability state ${key}`));
    assert(reliabilityByKey.get("research_usable").count >= 1, "research-usable sources must be visible");
    assert(reliabilityByKey.get("signal_review_eligible").count >= 1, "signal-review eligible sources must be visible");
    assert(reliabilityByKey.get("order_authority").count === 0, "source order authority must remain zero");
    assert(reliabilityByKey.get("missing_credential").count === 0, "required missing credentials should be zero for the core paper sources");
    assert(reliabilityByKey.get("optional_credentials").count >= 1, "optional missing credentials must be visible");
    assert(reliabilityByKey.get("pending_adapter").count >= 1, "pending adapters must be visible");
    assert(reliabilityByKey.get("optional").count >= 1, "optional feed count must be visible");
    assert(["ok", "degraded"].includes(model.quorum.status), "source quorum status should be visible");
    assert(supplementalByKey.has("yahoo_finance"), "Yahoo Finance supplemental source missing");
    assert(supplementalByKey.has("preference_mcp"), "Preference MCP supplemental source missing");
    assert(supplementalByKey.get("yahoo_finance").proof_boundary.includes("not source quorum"), "Yahoo Finance boundary must prevent sole-proof use");
    assert(supplementalByKey.get("preference_mcp").proof_boundary.includes("not source quorum"), "Preference boundary must prevent sole-proof use");
    assert(model.source_setup_links.length >= 3, "source-to-setup links should include observed, trade idea, and setup pool state");
    assert(model.source_setup_links.some((link) => link.stage === "Trade idea"), "trade-idea source link missing");
    assert(model.source_setup_links.some((link) => link.stage === "Observed signal"), "observed-signal source link missing");
    assert(model.source_setup_links.every((link) => link.href === "#trade-layer" || link.href === "#trades"), "source setup links must route to trade review surfaces");
    assert(model.source_setup_links.every((link) => !/order authority|broker write|live capital/i.test(link.proof_boundary)), "source setup links must not imply execution authority");

    const rendered = await renderWithStatus(status);
    const workspaceHtml = html(rendered, "[data-sources-workspace-slot]");
    const sourcesHtml = `${workspaceHtml} ${html(rendered, "[data-watching-list]")}`;
    [
        "Source reliability and corroboration",
        "Source quorum",
        "Core OK",
        "Required not configured",
        "Stale heartbeat",
        "Adapter backlog",
        "Optional not configured",
        "Yahoo Finance",
        "Preference MCP",
        "Supplemental confirmation only",
        "Challenge-only supplemental data plane",
        "Source to setup links",
        "Observed signal",
        "Trade idea",
        "Paper growth setup pool",
        "Pipeline groups",
        "Reliability state by intelligence pipeline",
        "credential required",
        "pending adapter",
        "evidence only",
        "Evidence readout",
        "Setup evidence",
        "Source reliability",
        "Supplemental context",
        "Factual evidence packets"
    ].forEach((needle) => assert(sourcesHtml.includes(needle), `rendered sources workspace missing ${needle}`));

    [
        "/Users/",
        "api_key",
        "PREFERENCE_API_KEY",
        "ALPACA_SECRET",
        "raw_payload",
        "private_payload",
        "local_path",
        "request_body",
        "broker_identifier"
    ].forEach((needle) => {
        assert(!workspaceHtml.includes(needle), `sources workspace leaked non-public-safe marker ${needle}`);
    });

    [
        "DX-7 - Sources Workspace",
        "Group sources by pipeline and reliability state",
        "Surface Yahoo Finance and PREF/Preference as capability-aware supplemental",
        "scripts/check_dashboard_overhaul_sources.js"
    ].forEach((needle) => {
        assert(plan.includes(needle), `master plan missing DX-7 marker: ${needle}`);
    });
    assert(fs.existsSync(auditPath), "DX-7 audit document missing");

    console.log("dashboard_overhaul_sources=ok");
    console.log("dashboard_sources_pipeline_count=" + model.pipelines.length);
    console.log("dashboard_sources_reliability_state_count=" + reliability.length);
    console.log("dashboard_sources_supplemental_count=2");
    console.log("dashboard_sources_setup_link_count=" + model.source_setup_links.length);
    console.log("dashboard_sources_public_safe=True");
    console.log("dashboard_source_authority_unchanged=True");
}

if (require.main === module) {
    main().catch((error) => {
        console.error(error.message);
        process.exitCode = 1;
    });
}
