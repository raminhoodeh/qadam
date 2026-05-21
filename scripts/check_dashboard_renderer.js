#!/usr/bin/env node

const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");

const repoRoot = path.resolve(__dirname, "..");
const rendererPath = path.join(repoRoot, "landing-page-repo", "dashboard.js");
const statusPath = path.join(repoRoot, "landing-page-repo", "status", "cockpit-status.json");

const rendererCode = fs.readFileSync(rendererPath, "utf8");
const status = JSON.parse(fs.readFileSync(statusPath, "utf8"));

const selectors = [
    "[data-mission-primary]",
    "[data-mission-sources]",
    "[data-mission-philosophy]",
    "[data-mission-stack]",
    "[data-mission-trades]",
    "[data-mission-portfolio]",
    "[data-operating-summary]",
    "[data-flow-map]",
    "[data-fund-model]",
    "[data-source-summary]",
    "[data-watching-list]",
    "[data-cognition]",
    "[data-worldview]",
    "[data-forbidden-actions]",
    "[data-communications]",
    "[data-trade-layer]",
    "[data-capital]",
    "[data-comments-summary]",
    "[data-comments-boundary]",
    "[data-comments-list]",
    "[data-process-console]",
    "[data-status-banner]",
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
    return { document, elements, errors, requests };
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
    assertIncludes(rendered, "[data-status-banner]", "D1 public-safe snapshot loaded");
    assertIncludes(rendered, "[data-status-banner]", "D9 live bridge connected");
    assertIncludes(rendered, "[data-mission-primary]", "Operating thesis");
    assertIncludes(rendered, "[data-mission-primary]", "hypotheses");
    assertIncludes(rendered, "[data-mission-sources]", "logged-in/configured");
    assertIncludes(rendered, "[data-mission-philosophy]", "Trading philosophy");
    assertIncludes(rendered, "[data-mission-stack]", "Local LLM");
    assertIncludes(rendered, "[data-mission-trades]", "Trade intent");
    assertIncludes(rendered, "[data-mission-portfolio]", "Paper account");
    assertIncludes(rendered, "[data-operating-summary]", "Paper account");
    assertIncludes(rendered, "[data-operating-summary]", "Source quality");
    assertIncludes(rendered, "[data-operating-summary]", "Safety state");
    assertIncludes(rendered, "[data-operating-summary]", "Candidate is not order");
    assertIncludes(rendered, "[data-fund-model]", "Fund Manager");
    assertIncludes(rendered, "[data-fund-model]", "Python keeps the book");
    assertIncludes(rendered, "[data-fund-model]", "Models inform, gates decide");
    assertIncludes(rendered, "[data-flow-map]", "Watched Sources");
    assertIncludes(rendered, "[data-flow-map]", "Secure Live Bridge");
    assertIncludes(rendered, "[data-flow-map]", "Trade Layer");
    assertIncludes(rendered, "[data-flow-map]", "Input");
    assertIncludes(rendered, "[data-flow-map]", "Output");
    assertIncludes(rendered, "[data-source-summary]", "Sources");
    assertIncludes(rendered, "[data-watching-list]", "pipeline-row");
    assertIncludes(rendered, "[data-cognition]", "Current focus");
    assertIncludes(rendered, "[data-cognition]", "Hypotheses and evidence");
    assertIncludes(rendered, "[data-worldview]", "Decision chain");
    assertIncludes(rendered, "[data-forbidden-actions]", "live capital");
    assertIncludes(rendered, "[data-communications]", "Telegram");
    assertIncludes(rendered, "[data-trade-layer]", "Observed signals");
    assertIncludes(rendered, "[data-trade-layer]", "Candidates");
    assertIncludes(rendered, "[data-capital]", "Starting");
    assertIncludes(rendered, "[data-capital]", "Closed trades");
    assertIncludes(rendered, "[data-comments-summary]", "Local notes");
    assertIncludes(rendered, "[data-comments-list]", "<li>");
    assertIncludes(rendered, "[data-process-console]", "<li>");

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
    unsafeStatus.modules = (unsafeStatus.modules || []).map((module) => (
        module.key === "research_analyst" ? {
            ...module,
            key: "research_analyst",
            label: "<script>alert(1)</script>",
            owner: "Renderer <Probe>",
            status: "\" onclick=\"bad",
            current_process: "escaping <must> hold",
            authority: "read_only"
        } : module
    ));
    const unsafe = await renderWithStatus(unsafeStatus);
    const flowHtml = html(unsafe, "[data-flow-map]");
    assert(!flowHtml.includes("<script>"), "renderer emitted raw script tag from status data");
    assert(flowHtml.includes("&lt;script&gt;alert(1)&lt;/script&gt;"), "renderer did not escape status HTML");

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
