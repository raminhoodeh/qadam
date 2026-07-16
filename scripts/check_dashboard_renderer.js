#!/usr/bin/env node

const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");

const repoRoot = path.resolve(__dirname, "..");
const dashboardSiteRoot = path.resolve(
    process.env.QADAM_DASHBOARD_SITE_ROOT || path.join(repoRoot, "landing-page-repo")
);
const rendererPath = path.join(dashboardSiteRoot, "dashboard.js");
const statusPath = path.join(dashboardSiteRoot, "status", "cockpit-status.json");

const rendererCode = fs.readFileSync(rendererPath, "utf8");
const status = JSON.parse(fs.readFileSync(statusPath, "utf8"));

const selectors = [
    "[data-mission-control]",
    "[data-mission-primary]",
    "[data-mission-sources]",
    "[data-mission-philosophy]",
    "[data-mission-stack]",
    "[data-mission-strategy]",
    "[data-mission-trades]",
    "[data-mission-portfolio]",
    "[data-operating-summary]",
    "[data-dashboard-safety-strip]",
    "[data-stage7-dashboard-visibility]",
    "[data-overview-mission-brief]",
    "[data-overview-strategy-narrative]",
    "[data-overview-paper-trade-state]",
    "[data-overview-control-plane]",
    "[data-overview-plain-grid]",
    "[data-overview-source-summary]",
    "[data-overview-edge-tracker]",
    "[data-phase4-summary]",
    "[data-phase4-strategy]",
    "[data-flow-map]",
    "[data-sources-workspace-slot]",
    "[data-source-summary]",
    "[data-watching-list]",
    "[data-cognition]",
    "[data-trade-layer]",
    "[data-capital]",
    "[data-operations-consolidated-readout]",
    "[data-status-banner]",
    "[data-overview-portfolio-hero]",
    "[data-balance-ticker]",
    "[data-trade-toast-rail]",
    "[data-mode-label]",
    "[data-capital-label]",
    "[data-live-capital-label]",
    "[data-snapshot-meta]"
];

class FakeClassList {
    constructor() {
        this.values = new Set();
    }

    add(...names) {
        names.forEach((name) => this.values.add(name));
    }

    remove(...names) {
        names.forEach((name) => this.values.delete(name));
    }

    contains(name) {
        return this.values.has(name);
    }
}

class FakeElement {
    constructor(selector) {
        this.selector = selector;
        this._innerHTML = "";
        this._textContent = "";
        this.dataset = {};
        this.attributes = {};
        this.classList = new FakeClassList();
    }

    set innerHTML(value) {
        this._innerHTML = String(value);
        this._textContent = String(value);
    }

    get innerHTML() {
        return this._innerHTML;
    }

    set textContent(value) {
        this._textContent = String(value);
        this._innerHTML = String(value);
    }

    get textContent() {
        return this._textContent;
    }

    setAttribute(name, value) {
        this.attributes[name] = String(value);
    }

    querySelector() {
        return null;
    }

    querySelectorAll() {
        return [];
    }

    addEventListener() {}

    removeEventListener() {}

    focus() {}
}

function clone(value) {
    return JSON.parse(JSON.stringify(value));
}

function createFakeDom() {
    const elements = new Map(selectors.map((selector) => [selector, new FakeElement(selector)]));
    const documentElement = { dataset: {} };

    return {
        elements,
        document: {
            documentElement,
            querySelector(selector) {
                return elements.get(selector) || null;
            }
        }
    };
}

async function renderWithStatus(snapshot, options = {}) {
    const { elements, document } = createFakeDom();
    const errors = [];
    const requests = [];
    const window = { document };
    const context = {
        Array,
        Date,
        Error,
        Intl,
        Math,
        Number,
        Object,
        Promise,
        String,
        console: {
            error(...args) {
                errors.push(args.map(String).join(" "));
            }
        },
        document,
        fetch: async (url, init = {}) => {
            requests.push({ url: String(url), init });
            const sequenceResult = Array.isArray(options.fetchSequence)
                ? options.fetchSequence[requests.length - 1]
                : null;
            const bridgeFailed = options.liveFetchOk === false && String(url).includes("/api/cockpit-status");
            if (options.fetchOk === false || bridgeFailed || sequenceResult?.ok === false) {
                return {
                    ok: false,
                    status: sequenceResult?.statusCode || options.statusCode || 500,
                    json: async () => snapshot
                };
            }
            return {
                ok: true,
                status: 200,
                json: async () => snapshot
            };
        },
        window
    };
    window.window = window;

    vm.createContext(context);
    vm.runInContext(rendererCode, context, { filename: rendererPath });

    if (typeof window.renderQadamDashboardStatus !== "function") {
        throw new Error("dashboard renderer did not expose window.renderQadamDashboardStatus");
    }

    const session = Object.prototype.hasOwnProperty.call(options, "session")
        ? options.session
        : { access_token: "test-session-token" };
    await window.renderQadamDashboardStatus(session);
    return { document, elements, errors, requests, window };
}

function html(rendered, selector) {
    const element = rendered.elements.get(selector);
    if (!element) throw new Error(`missing fake element for ${selector}`);
    return element.innerHTML;
}

function assert(condition, message) {
    if (!condition) throw new Error(message);
}

function assertIncludes(rendered, selector, expected) {
    assert(
        html(rendered, selector).includes(expected),
        `${selector} did not include expected text: ${expected}`
    );
}

async function main() {
    const rendered = await renderWithStatus(status);

    assert(
        rendered.document.documentElement.dataset.dashboardStatus === "rendered",
        "dashboard did not mark the snapshot as rendered"
    );
    assert(
        rendered.document.documentElement.dataset.dashboardStatusSource === "live_bridge",
        "dashboard did not prefer the live bridge source"
    );
    assert(
        rendered.requests[0]?.url.includes("/api/cockpit-status"),
        "dashboard did not request the live bridge before the static snapshot"
    );
    assertIncludes(rendered, "[data-status-banner]", "Dashboard status loaded");
    assertIncludes(rendered, "[data-status-banner]", "Live status connected");
    assertIncludes(rendered, "[data-overview-mission-brief]", "Mission Snapshot");
    assertIncludes(rendered, "[data-mission-sources]", "logged-in/configured");
    assertIncludes(rendered, "[data-mission-sources]", "Preference MCP");
    assertIncludes(rendered, "[data-mission-philosophy]", "Trading philosophy");
    assertIncludes(rendered, "[data-mission-stack]", "Local LLM");
    assertIncludes(rendered, "[data-mission-stack]", "Q5-6");
    assertIncludes(rendered, "[data-mission-stack]", "Q5-14");
    assertIncludes(rendered, "[data-mission-stack]", "Q5E-10");
    assertIncludes(rendered, "[data-mission-stack]", "Paper growth visible");
    assertIncludes(rendered, "[data-mission-strategy]", "Phase 4 strategy");
    assertIncludes(rendered, "[data-mission-strategy]", "approved");
    assertIncludes(rendered, "[data-mission-strategy]", "certification certified");
    assertIncludes(rendered, "[data-mission-trades]", "Trade intent");
    assertIncludes(rendered, "[data-mission-portfolio]", "Paper account");
    assertIncludes(rendered, "[data-operating-summary]", "Paper account");
    assertIncludes(rendered, "[data-operating-summary]", "Source quality");
    assertIncludes(rendered, "[data-operating-summary]", "Strategy");
    assertIncludes(rendered, "[data-operating-summary]", "Trade layer");
    assertIncludes(rendered, "[data-operating-summary]", "paper orders");
    assertIncludes(rendered, "[data-phase4-summary]", "Q4-12");
    assertIncludes(rendered, "[data-phase4-summary]", "Certified");
    assertIncludes(rendered, "[data-phase4-strategy]", "Is Phase 4 visible but non-executable?");
    assertIncludes(rendered, "[data-phase4-strategy]", "approved");
    assertIncludes(rendered, "[data-phase4-strategy]", "No certification blockers exported");
    assertIncludes(rendered, "[data-phase4-strategy]", "No execution");
    assertIncludes(rendered, "[data-phase4-strategy]", "Yahoo Finance supplemental");
    assertIncludes(rendered, "[data-overview-control-plane]", "Control Plane");
    assertIncludes(rendered, "[data-overview-control-plane]", "Human oversight");
    assertIncludes(rendered, "[data-overview-control-plane]", "Qadam operating team");
    assertIncludes(rendered, "[data-overview-control-plane]", "Chief Operating Officer");
    assertIncludes(rendered, "[data-overview-control-plane]", "Research Analyst");
    assertIncludes(rendered, "[data-overview-control-plane]", "PaperOps");
    assertIncludes(rendered, "[data-overview-control-plane]", "Paper/Demo State");
    assertIncludes(rendered, "[data-overview-control-plane]", "mission_control");
    assertIncludes(rendered, "[data-overview-control-plane]", "What it does");
    assertIncludes(rendered, "[data-overview-control-plane]", "Boundary");
    assertIncludes(rendered, "[data-overview-portfolio-hero]", "Real portfolio timeline");
    assertIncludes(rendered, "[data-overview-portfolio-hero]", "Paper account portfolio value line");
    assertIncludes(rendered, "[data-overview-portfolio-hero]", "Trade timeline");
    assertIncludes(rendered, "[data-overview-portfolio-hero]", "Bought and held");
    assertIncludes(rendered, "[data-overview-portfolio-hero]", "Sold and closed");
    assertIncludes(rendered, "[data-flow-map]", "Q5-13 Functional System Map Dashboard");
    assertIncludes(rendered, "[data-flow-map]", "Backend parity");
    assertIncludes(rendered, "[data-flow-map]", "Unsafe controls");
    assertIncludes(rendered, "[data-flow-map]", "Yahoo Finance supplemental market confirmation only");
    assertIncludes(rendered, "[data-flow-map]", "Preference/PREF MCP");
    assertIncludes(rendered, "[data-flow-map]", "live capital disabled");
    assertIncludes(rendered, "[data-flow-map]", "paper submit path 0");
    assertIncludes(rendered, "[data-flow-map]", "dashboard does not say trading");
    assertIncludes(rendered, "[data-flow-map]", "Approval Policy Router");
    assertIncludes(rendered, "[data-flow-map]", "Kill-Switch Ledger");
    assertIncludes(rendered, "[data-flow-map]", "Execution Adapter Status");
    assertIncludes(rendered, "[data-flow-map]", "Prediction-Market Adapter");
    assertIncludes(rendered, "[data-flow-map]", "Position Monitor");
    assertIncludes(rendered, "[data-flow-map]", "Signal Review");
    assertIncludes(rendered, "[data-trade-layer]", "Verified paper trades");
    assertIncludes(rendered, "[data-source-summary]", "Sources");
    assertIncludes(rendered, "[data-source-summary]", "Preference MCP");
    assertIncludes(rendered, "[data-watching-list]", "pipeline-row");
    assertIncludes(rendered, "[data-watching-list]", "Preference MCP data plane");
    assertIncludes(rendered, "[data-watching-list]", "Domain-pack coverage");
    assertIncludes(rendered, "[data-watching-list]", "Provenance health");
    assertIncludes(rendered, "[data-watching-list]", "Quota/credit health");
    assertIncludes(rendered, "[data-watching-list]", "Blocked paid tools");
    assertIncludes(rendered, "[data-watching-list]", "no source-quorum");
    assertIncludes(rendered, "[data-cognition]", "Current focus");
    assertIncludes(rendered, "[data-cognition]", "Hypotheses and evidence");
    assertIncludes(rendered, "[data-trade-layer]", "Observed signals");
    assertIncludes(rendered, "[data-trade-layer]", "Candidates");
    assertIncludes(rendered, "[data-trade-layer]", "Q5-14 End-To-End Paper Trade Drill");
    assertIncludes(
        rendered,
        "[data-trade-layer]",
        status.phase5_paper_trade_drill?.paper_submit_approval_present
            ? "paper-submit approval present"
            : "paper-submit approval missing"
    );
    assertIncludes(rendered, "[data-trade-layer]", "paper submit path available");
    assertIncludes(rendered, "[data-trade-layer]", "no broker POST");
    assertIncludes(rendered, "[data-trade-layer]", "no false growth maturity");
    assertIncludes(rendered, "[data-trade-layer]", "Q5-15 Phase 5 Certification");
    assertIncludes(rendered, "[data-trade-layer]", "Q5E-10 Phase 6 Handoff Closeout");
    assertIncludes(rendered, "[data-trade-layer]", "Phase 5 certified");
    assertIncludes(rendered, "[data-trade-layer]", "Q5-14 exit passed");
    assertIncludes(rendered, "[data-trade-layer]", "Phase 6 handoff allowed");
    assertIncludes(rendered, "[data-overview-control-plane]", "How to read this node");
    assertIncludes(rendered, "[data-overview-control-plane]", "Strategy Lead");
    assertIncludes(rendered, "[data-overview-control-plane]", "Currently");
    assertIncludes(rendered, "[data-overview-control-plane]", "Next handoff");
    assertIncludes(rendered, "[data-overview-mission-brief]", "Durable replay");
    assertIncludes(rendered, "[data-overview-mission-brief]", "Trade lifecycle");
    assert(!html(rendered, "[data-overview-mission-brief]").includes("data-overview-decision-records"), "Mission Snapshot must not render old decision-record chrome");
    assert(!html(rendered, "[data-overview-mission-brief]").includes("Default to Mission Snapshot"), "Mission Snapshot must not render old default decision copy");
    assertIncludes(rendered, "[data-overview-strategy-narrative]", "Strategy Universe");
    assertIncludes(rendered, "[data-overview-strategy-narrative]", "Asymmetric Catalyst Proxy Trading");
    assertIncludes(rendered, "[data-overview-strategy-narrative]", "Qualified now");
    assertIncludes(rendered, "[data-overview-strategy-narrative]", "Waiting");
    assertIncludes(rendered, "[data-overview-strategy-narrative]", "Second-order AI infrastructure beneficiary lens");
    assertIncludes(rendered, "[data-overview-strategy-narrative]", "Open the full universe");
    assertIncludes(rendered, "[data-overview-strategy-narrative]", "Qadam-native edge");
    assertIncludes(rendered, "[data-overview-strategy-narrative]", "Semiconductor Policy Options Asymmetry");
    assertIncludes(rendered, "[data-overview-strategy-narrative]", "Defence Repricing Geopolitical Watch");
    assertIncludes(rendered, "[data-overview-strategy-narrative]", "Silver Macro Liquidity Stress");
    assertIncludes(rendered, "[data-overview-strategy-narrative]", "Crude Oil Energy Security Disruption");
    assertIncludes(rendered, "[data-overview-strategy-narrative]", "Prediction Market Geopolitical Dislocation");
    assertIncludes(rendered, "[data-overview-strategy-narrative]", "Akber’s 6-Stage Filter");
    assertIncludes(rendered, "[data-overview-strategy-narrative]", "guarded Alpaca Paper");
    assertIncludes(rendered, "[data-overview-paper-trade-state]", "Paper Account &amp; Trade State");
    assertIncludes(rendered, "[data-overview-paper-trade-state]", "Balance");
    assertIncludes(rendered, "[data-overview-paper-trade-state]", "Current value");
    assertIncludes(rendered, "[data-overview-paper-trade-state]", "Trade state");
    assertIncludes(rendered, "[data-overview-paper-trade-state]", "Total P&amp;L");
    assert(!html(rendered, "[data-overview-paper-trade-state]").includes("USO options watch"), "Overview trade state must not render trade-row ledgers");
    assertIncludes(rendered, "[data-overview-source-summary]", "Data source tracker");
    assertIncludes(rendered, "[data-overview-source-summary]", "Source list");
    assertIncludes(rendered, "[data-overview-source-summary]", "signal-review eligible");
    assertIncludes(rendered, "[data-overview-source-summary]", "ACLED API");
    assertIncludes(rendered, "[data-trade-layer]", "Signal Review");
    assertIncludes(rendered, "[data-trade-layer]", "Decision chain");
    assertIncludes(rendered, "[data-trade-layer]", "Governance comment");
    assertIncludes(rendered, "[data-trade-layer]", "Kill-switch action");
    assertIncludes(rendered, "[data-trade-layer]", "event_log_only_no_mutation");
    assertIncludes(rendered, "[data-trade-layer]", "no approval control");
    assertIncludes(rendered, "[data-trade-layer]", "no order control");
    assertIncludes(rendered, "[data-trade-layer]", "no broker write");
    assertIncludes(rendered, "[data-trade-layer]", "live capital disabled");
    assertIncludes(rendered, "[data-capital]", "Starting");
    assertIncludes(rendered, "[data-capital]", "Closed trades");
    const changedStatus = clone(status);
    changedStatus.watching = [
        {
            source_key: "renderer_probe_feed",
            source_name: "Renderer Probe Feed",
            pipeline: "renderer_probe",
            status: "online",
            readiness: "probe_ready",
            tier: "test",
            cadence: "one_off",
            credential_status: "configured",
            promoted_adapter: true,
            trust_score: 1,
            last_heartbeat: changedStatus.generated_at,
            raw_status: "renderer probe payload"
        }
    ];
    changedStatus.trade_layer = {
        ...changedStatus.trade_layer,
        summary: {
            ...(changedStatus.trade_layer?.summary || {}),
            intent_count: 1,
            candidate_count: 1
        },
        candidates: [
            {
                instrument: "D2-PROBE",
                venue: "renderer",
                status: "candidate",
                catalyst: "Renderer contract probe",
                direction: "long",
                probability_estimate: 0.61,
                market_implied_probability: 0.5,
                proposed_entry: "probe only",
                invalidation: "probe removed",
                holding_window: "one check",
                risk_size_gbp: 1,
                risk_size_pct: 0.1,
                akber_filter: { contract_probe: "pending" },
                risk_checks: { execution: "blocked" },
                boundary: "Contract probe only. No broker route exists."
            }
        ]
    };

    const changed = await renderWithStatus(changedStatus);
    assertIncludes(changed, "[data-watching-list]", "Renderer Probe Feed");
    assertIncludes(changed, "[data-trade-layer]", "D2-PROBE");

    const unsafeStatus = clone(status);
    unsafeStatus.mission_control = {
        ...(unsafeStatus.mission_control || {}),
        team: (unsafeStatus.mission_control?.team || []).map((node) => (
            node.key === "coo" ? {
                ...node,
                label: "<script>alert(1)</script>",
                owner: "Renderer <Probe>",
                status: "\" onclick=\"bad",
                current_process: "escaping <must> hold",
                authority: "read_only"
            } : node
        ))
    };
    const unsafe = await renderWithStatus(unsafeStatus);
    const controlPlaneHtml = html(unsafe, "[data-overview-control-plane]");
    assert(!controlPlaneHtml.includes("<script>"), "renderer emitted raw script tag from status data");
    assert(controlPlaneHtml.includes("&lt;script&gt;alert(1)&lt;/script&gt;"), "renderer did not escape status HTML");

    const failed = await renderWithStatus(status, { fetchOk: false, statusCode: 404 });
    assert(
        failed.document.documentElement.dataset.dashboardStatus === "snapshot-error",
        "dashboard did not mark failed fetches as snapshot-error"
    );
    assertIncludes(failed, "[data-status-banner]", "Status contract unavailable");

    console.log("Dashboard renderer contract OK");
    console.log(`Rendered snapshot: ${statusPath}`);
}

if (require.main === module) {
    main().catch((error) => {
        console.error(error.message);
        process.exitCode = 1;
    });
}

module.exports = {
    assert,
    assertIncludes,
    html,
    renderWithStatus,
    status,
    statusPath
};
