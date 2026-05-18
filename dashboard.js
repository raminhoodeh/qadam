const STATUS_SOURCES = [
    {
        key: "live_bridge",
        label: "D9 read-only live bridge",
        url: "/api/cockpit-status",
        requiresAuth: true
    },
    {
        key: "static_snapshot",
        label: "static snapshot fallback",
        url: "/status/cockpit-status.json",
        requiresAuth: false
    }
];

const DASHBOARD_DENSITY_KEY = "qadam.dashboard.density";
const DASHBOARD_DENSITIES = new Set(["executive", "terminal"]);

function dashboardQuery(selector) {
    return document.querySelector(selector);
}

function storedDashboardDensity() {
    try {
        if (typeof localStorage === "undefined") return "executive";
        return localStorage.getItem(DASHBOARD_DENSITY_KEY) || "executive";
    } catch (_error) {
        return "executive";
    }
}

function normalizeDashboardDensity(value) {
    return DASHBOARD_DENSITIES.has(value) ? value : "executive";
}

function setDashboardDensity(value, persist = true) {
    const density = normalizeDashboardDensity(value);
    if (document.documentElement) {
        document.documentElement.dataset.dashboardDensity = density;
    }
    if (persist) {
        try {
            if (typeof localStorage !== "undefined") {
                localStorage.setItem(DASHBOARD_DENSITY_KEY, density);
            }
        } catch (_error) {
            // localStorage can be blocked in private browsing; the DOM state still works.
        }
    }
    if (typeof document.querySelectorAll === "function") {
        document.querySelectorAll("[data-density-option]").forEach((button) => {
            const active = button.dataset.densityOption === density;
            button.setAttribute("aria-pressed", active ? "true" : "false");
        });
    }
    return density;
}

function initDashboardDensityToggle() {
    const density = setDashboardDensity(storedDashboardDensity(), false);
    if (typeof document.querySelectorAll !== "function") return density;
    document.querySelectorAll("[data-density-option]").forEach((button) => {
        button.addEventListener("click", () => {
            setDashboardDensity(button.dataset.densityOption);
        });
    });
    return density;
}

function dashboardText(value, fallback = "Not connected yet") {
    if (value === null || value === undefined || value === "") return fallback;
    return String(value).replaceAll("_", " ");
}

function htmlText(value, fallback = "Not connected yet") {
    return dashboardText(value, fallback).replace(/[&<>"']/g, (char) => ({
        "&": "&amp;",
        "<": "&lt;",
        ">": "&gt;",
        "\"": "&quot;",
        "'": "&#39;"
    })[char]);
}

function asArray(value) {
    return Array.isArray(value) ? value : [];
}

function statusClass(status) {
    return dashboardText(status, "pending")
        .toLowerCase()
        .replace(/[^a-z0-9]+/g, "-")
        .replace(/^-+|-+$/g, "") || "pending";
}

function formatMoney(value) {
    const amount = Number(value || 0);
    return new Intl.NumberFormat("en-GB", {
        style: "currency",
        currency: "GBP",
        maximumFractionDigits: 0
    }).format(amount);
}

function formatTime(value) {
    if (!value) return "Not connected";
    const date = new Date(value);
    if (Number.isNaN(date.getTime())) return "Unknown";
    return new Intl.DateTimeFormat("en-GB", {
        day: "2-digit",
        month: "short",
        hour: "2-digit",
        minute: "2-digit"
    }).format(date);
}

function formatLatency(value) {
    if (value === null || value === undefined || value === "") return "unknown";
    const latency = Number(value);
    if (Number.isNaN(latency)) return dashboardText(value, "unknown");
    return `${Math.round(latency)} ms`;
}

function countBy(items, key) {
    return asArray(items).reduce((acc, item) => {
        const value = item?.[key] || "unknown";
        acc[value] = (acc[value] || 0) + 1;
        return acc;
    }, {});
}

function setText(selector, value) {
    const target = dashboardQuery(selector);
    if (target) target.textContent = value;
}

function renderStatusPill(status) {
    return `<b class="node-status ${statusClass(status)}">${htmlText(status)}</b>`;
}

function renderMetric(label, value) {
    return `<div class="metric"><span>${htmlText(label)}</span><strong>${htmlText(value)}</strong></div>`;
}

function renderInlineBadge(value, status = "pending") {
    return `<span class="inline-badge ${statusClass(status)}">${htmlText(value)}</span>`;
}

function renderPanelBrief({ id, question, state, tone = "pending", primary, secondary, boundary }) {
    return `
        <section class="panel-brief ${statusClass(tone)}" data-panel-brief="${htmlText(id)}">
            <div class="panel-brief-main">
                <p class="label">Panel readout</p>
                <h3>${htmlText(question)}</h3>
                <p>${htmlText(primary)}</p>
            </div>
            <dl class="panel-brief-facts">
                <div>
                    <dt>State</dt>
                    <dd>${renderInlineBadge(state, tone)}</dd>
                </div>
                <div>
                    <dt>Watch</dt>
                    <dd>${htmlText(secondary)}</dd>
                </div>
                <div>
                    <dt>Boundary</dt>
                    <dd>${htmlText(boundary)}</dd>
                </div>
            </dl>
        </section>
    `;
}

function replacePanelBrief(id, config) {
    const target = dashboardQuery(`[data-panel-brief="${id}"]`);
    if (target) target.outerHTML = renderPanelBrief({ id, ...config });
}

function renderTagList(items, emptyText = "None recorded") {
    const list = Array.isArray(items) ? items.filter(Boolean) : [];
    if (!list.length) return `<span>${htmlText(emptyText)}</span>`;
    return list.map((item) => `<span>${htmlText(item)}</span>`).join("");
}

function sumNestedItems(items, key) {
    return asArray(items).reduce((total, item) => total + asArray(item?.[key]).length, 0);
}

function formatConfidence(value) {
    if (value === null || value === undefined || value === "") return "unknown";
    const score = Number(value);
    if (Number.isNaN(score)) return dashboardText(value, "unknown");
    return score <= 1 ? `${Math.round(score * 100)}%` : `${Math.round(score)}%`;
}

function formatProbability(value) {
    if (value === null || value === undefined || value === "") return "unknown";
    const score = Number(value);
    if (Number.isNaN(score)) return dashboardText(value, "unknown");
    return score <= 1 ? `${Math.round(score * 100)}%` : `${Math.round(score)}%`;
}

function formatPercent(value) {
    if (value === null || value === undefined || value === "") return "0%";
    const score = Number(value);
    if (Number.isNaN(score)) return dashboardText(value, "0%");
    return `${score}%`;
}

function findModule(status, key) {
    return asArray(status.modules).find((module) => module.key === key);
}

const FLOW_NODE_DETAILS = {
    watching: {
        role: "Source desks",
        input: "Feeds, alerts, charts",
        output: "Observed facts",
        authority: "Observation only"
    },
    event_log: {
        role: "COO memory",
        input: "Every material event",
        output: "Audit trail",
        authority: "Source of truth"
    },
    live_bridge: {
        role: "Read-only bridge",
        input: "Sanitized snapshot",
        output: "Dashboard status",
        authority: "No command route"
    },
    worldview: {
        role: "Private edge",
        input: "World-model priors",
        output: "Sharper questions",
        authority: "Context only"
    },
    research_analyst: {
        role: "Research desk",
        input: "Noisy observations",
        output: "Shadow analysis",
        authority: "No execution"
    },
    strategy_lead: {
        role: "Strategy desk",
        input: "Evidence packets",
        output: "Challenge notes",
        authority: "Escalation only"
    },
    head_of_quant: {
        role: "Quant desk",
        input: "Bounded scenarios",
        output: "Oracle check",
        authority: "Non-executable"
    },
    shadow_intelligence: {
        role: "Research queue",
        input: "Model packets",
        output: "Hypotheses",
        authority: "Shadow only"
    },
    execution_registry: {
        role: "Risk desk",
        input: "Trade intents",
        output: "Blocks or gates",
        authority: "Fail closed"
    },
    trade_layer: {
        role: "Paper desk",
        input: "Approved intents",
        output: "Paper states",
        authority: "Live blocked"
    },
    telegram_bot: {
        role: "Member comms",
        input: "Status events",
        output: "Notifications",
        authority: "Notify only"
    },
    paper_account: {
        role: "Money mirror",
        input: "Paper broker state",
        output: "Balances and positions",
        authority: "Read-only"
    },
    postmortem_loop: {
        role: "Learning loop",
        input: "Closed paper trades",
        output: "Lessons and weight updates",
        authority: "After-action review"
    },
    fund_manager_forum: {
        role: "Governance desk",
        input: "Member comments",
        output: "Improvement notes",
        authority: "Governance only"
    }
};

function flowNodeDetails(module) {
    const key = module?.key || "";
    return FLOW_NODE_DETAILS[key] || {
        role: dashboardText(module?.owner, "Qadam desk"),
        input: "Runtime state",
        output: "Dashboard state",
        authority: dashboardText(module?.authority, "read only")
    };
}

function statusFetchHeaders(source, session) {
    if (!source.requiresAuth || !session?.access_token) return {};
    return { Authorization: `Bearer ${session.access_token}` };
}

async function fetchDashboardStatus(session) {
    const failures = [];
    for (const source of STATUS_SOURCES) {
        try {
            const response = await fetch(`${source.url}?t=${Date.now()}`, {
                cache: "no-store",
                headers: statusFetchHeaders(source, session)
            });
            if (!response.ok) {
                failures.push(`${source.key}:${response.status}`);
                continue;
            }
            return {
                source,
                status: await response.json()
            };
        } catch (error) {
            failures.push(`${source.key}:${error.message || "fetch failed"}`);
        }
    }
    throw new Error(`all status sources failed: ${failures.join(", ")}`);
}

function sourceSummary(status) {
    const watching = asArray(status.watching);
    const pipelineSummary = asArray(status.source_pipeline_summary);
    const counts = countBy(watching, "status");
    const missingCredentialCount = pipelineSummary.reduce(
        (total, pipeline) => total + Number(pipeline.missing_credential_count || 0),
        0
    );
    return [
        renderMetric("Sources", watching.length),
        renderMetric("Online", counts.online || 0),
        renderMetric("Degraded", counts.degraded || 0),
        renderMetric("Pending", counts.pending || 0),
        renderMetric("Local-only", counts.local_only || counts["local-only"] || 0),
        renderMetric("Missing creds", missingCredentialCount),
        renderMetric("Signal influence", watching.filter((source) => source.can_influence_signals).length)
    ].join("");
}

function systemMapNode(module, index) {
    const details = flowNodeDetails(module);
    return `
        <article class="flow-node system-map-node">
            <div class="node-topline">
                ${renderStatusPill(module.status)}
                <span>${String(index + 1).padStart(2, "0")} · ${htmlText(details.role, module.owner || "Qadam desk")}</span>
            </div>
            <h3>${htmlText(module.label, module.key)}</h3>
            <p class="flow-summary">${htmlText(module.current_process)}</p>
            <dl class="node-facts">
                <div>
                    <dt>Input</dt>
                    <dd>${htmlText(details.input)}</dd>
                </div>
                <div>
                    <dt>Output</dt>
                    <dd>${htmlText(details.output)}</dd>
                </div>
            </dl>
            <span class="node-authority">${htmlText(details.authority || module.authority, "read only")}</span>
        </article>
    `;
}

function systemMapConnector(label) {
    return `<div class="flow-connector" aria-hidden="true"><span>${htmlText(label)}</span></div>`;
}

function systemMapLane(lane, laneIndex) {
    const nodeHtml = lane.nodes
        .map((node, nodeIndex) => {
            const globalIndex = lane.offset + nodeIndex;
            const connector = nodeIndex < lane.nodes.length - 1
                ? systemMapConnector(node.handoff || "passes state")
                : "";
            return `${systemMapNode(node, globalIndex)}${connector}`;
        })
        .join("");

    return `
        <section class="flow-lane ${statusClass(lane.tone || "neutral")}">
            <header class="flow-lane-header">
                <span>${String(laneIndex + 1).padStart(2, "0")}</span>
                <div>
                    <h3>${htmlText(lane.title)}</h3>
                    <p>${htmlText(lane.summary)}</p>
                </div>
            </header>
            <div class="flow-lane-track">${nodeHtml}</div>
            <div class="lane-handoff"><span>${htmlText(lane.handoff)}</span></div>
        </section>
    `;
}

function renderFundModel(status, source) {
    const target = dashboardQuery("[data-fund-model]");
    if (!target) return;
    const cognition = status.cognition || {};
    const tradeLayer = status.trade_layer || {};
    const capital = status.capital || {};
    const communications = status.communications?.telegram || {};
    const sourceMode = source?.key === "live_bridge" ? "live bridge" : "snapshot";
    const cards = [
        {
            kicker: "Fund Manager",
            title: "You supervise the fund",
            body: "Review the operating map, challenge ideas, add governance comments, and decide whether Qadam is mature enough to advance.",
            metric: `${status.mode || "paper"} mode · ${sourceMode}`
        },
        {
            kicker: "COO",
            title: "Python keeps the book",
            body: "The orchestrator converts source, model, and trade events into public-safe state. If it is not logged, it does not count.",
            metric: `${asArray(status.process_console).length} recent events`
        },
        {
            kicker: "Analysts",
            title: "Local and frontier models research",
            body: "The Research Analyst compresses noise locally. The Strategy Lead challenges only after evidence exists.",
            metric: `${asArray(cognition.hypotheses).length} hypotheses · ${asArray(cognition.evidence_packets).length} packets`
        },
        {
            kicker: "Quant + Risk",
            title: "Models inform, gates decide",
            body: "The Head of Quant is a bounded oracle. Risk controls block stale, weak, oversized, or unauthorized ideas.",
            metric: `${asArray(tradeLayer.blocked).length} blocked · live capital ${capital.live_capital_enabled ? "enabled" : "off"}`
        },
        {
            kicker: "Paper desk",
            title: "Ideas become paper states only",
            body: "Observed signals and candidates are not orders. The paper account shows proof trades, positions, exits, and postmortems.",
            metric: `${asArray(tradeLayer.candidates).length} candidates · ${communications.status || "comms pending"} comms`
        }
    ];
    target.innerHTML = cards.map((card) => `
        <article class="fund-model-card">
            <span>${htmlText(card.kicker)}</span>
            <h3>${htmlText(card.title)}</h3>
            <p>${htmlText(card.body)}</p>
            <small>${htmlText(card.metric)}</small>
        </article>
    `).join("");
}

function renderFlowMap(status) {
    const tradeLayer = status.trade_layer || {};
    const tradeSummary = tradeLayer.summary || {};
    const telegram = status.communications?.telegram || {};
    const liveBridge = status.live_bridge || {};
    const capital = status.capital || {};
    const notes = status.fund_manager_notes || {};
    const watching = asArray(status.watching);
    const candidates = asArray(tradeLayer.candidates);
    const blocked = asArray(tradeLayer.blocked);
    const tradeIntentCount = tradeSummary.intent_count || 0;
    const tradeCandidateCount = candidates.length;
    const blockedTradeCount = blocked.length;
    const observedSignals = asArray(tradeLayer.watching);
    const closedTrades = asArray(capital.closed_trades);
    const postmortemsDue = asArray(capital.postmortems_due);
    const postmortemsComplete = asArray(capital.postmortems_complete);
    const mapNodes = [
        {
            key: "watching",
            label: "Watched Sources",
            owner: "Source Registry",
            status: watching.length ? "online" : "pending",
            current_process: `${watching.length} sources in the public-safe snapshot`,
            authority: "read_only",
            handoff: "observed facts"
        },
        {
            ...(findModule(status, "event_log") || {
                key: "event_log",
                label: "Event Log",
                owner: "COO memory",
                status: "local_only",
                current_process: "Local append-only runtime state",
                authority: "source_of_truth"
            }),
            handoff: "logged state"
        },
        {
            key: "live_bridge",
            label: "Secure Live Bridge",
            owner: "qadam.trade API",
            status: liveBridge.status === "read_only_ready" ? "online" : (liveBridge.status || "pending"),
            current_process: `${asArray(liveBridge.allowed_methods).join("/")} status only · fallback ${liveBridge.static_fallback || "static snapshot"}`,
            authority: liveBridge.browser_authority || "read_only",
            handoff: "public-safe dashboard state"
        },
        {
            key: "worldview",
            label: "Worldview Lens",
            owner: "Private Edge Layer",
            status: status.decision_philosophy?.status === "ok" ? "online" : "pending",
            current_process: `${status.decision_philosophy?.foundational_prior_count || 0} foundational priors shaping questions, not evidence`,
            authority: "prior_only",
            handoff: "questions, not evidence"
        },
        {
            ...(findModule(status, "research_analyst") || {
                key: "research_analyst",
                label: "Research Analyst",
                owner: "Local LLM",
                status: "pending",
                current_process: "Waiting for local triage heartbeat",
                authority: "shadow_only"
            }),
            handoff: "shadow analysis"
        },
        {
            ...(findModule(status, "strategy_lead") || {
                key: "strategy_lead",
                label: "Strategy Lead",
                owner: "Frontier model",
                status: "pending",
                current_process: "Waiting for evidence packets",
                authority: "non_executable"
            }),
            handoff: "challenge notes"
        },
        {
            ...(findModule(status, "head_of_quant") || {
                key: "head_of_quant",
                label: "Head of Quant",
                owner: "Quantum / classical oracle",
                status: "deferred",
                current_process: "No real-time role",
                authority: "weekly_oracle"
            }),
            handoff: "bounded oracle check"
        },
        {
            ...(findModule(status, "shadow_intelligence") || {
                key: "shadow_intelligence",
                label: "Shadow Intelligence",
                owner: "Research queue",
                status: "pending",
                current_process: "Hypotheses remain non-executable",
                authority: "shadow_only"
            }),
            handoff: "hypothesis package"
        },
        {
            ...(findModule(status, "execution_registry") || {
                key: "execution_registry",
                label: "Risk Agent",
                owner: "Risk desk",
                status: "blocked",
                current_process: "Broker writes and live capital blocked",
                authority: "fail_closed"
            }),
            label: "Risk Agent",
            handoff: "risk decision"
        },
        {
            key: "trade_layer",
            label: "Trade Layer",
            owner: "Paper Trial",
            status: tradeLayer.store_status === "ok" ? "online" : "degraded",
            current_process: `${observedSignals.length} observed · ${tradeIntentCount} intents · ${tradeCandidateCount} candidates · ${blockedTradeCount} blocked`,
            authority: "write_blocked",
            handoff: "paper state"
        },
        {
            key: "paper_account",
            label: "Paper Account Mirror",
            owner: "Money",
            status: capital.mirror_status === "ok" ? "online" : (capital.mirror_status || "pending"),
            current_process: `${formatMoney(capital.current_balance_gbp)} current · ${capital.open_position_count || 0} open · ${capital.closed_trade_count || 0} closed`,
            authority: capital.write_authority ? "write_enabled" : "read_only",
            handoff: "closed paper outcomes"
        },
        {
            key: "postmortem_loop",
            label: "Postmortem Loop",
            owner: "Knowledge Graph",
            status: postmortemsDue.length ? "pending" : "waiting",
            current_process: `${postmortemsDue.length} due · ${postmortemsComplete.length} complete · ${closedTrades.length} closed trades`,
            authority: "after_action_review",
            handoff: "lessons return to memory"
        },
        {
            key: "telegram_bot",
            label: "Telegram Bot",
            owner: "Fund Manager Interface",
            status: telegram.status === "dry_run" ? "dry run" : (telegram.status || "disabled"),
            current_process: `${telegram.pending_queue_count || 0} queued · ${telegram.sent_count || 0} sent · ${formatTime(telegram.last_sent_time)}`,
            authority: "notify_only",
            handoff: "member visibility"
        },
        {
            key: "fund_manager_forum",
            label: "Fund Manager Forum",
            owner: "Governance",
            status: notes.status === "ok" ? "online" : (notes.status || "pending"),
            current_process: `${notes.comment_count || 0} governance notes · ${notes.implemented_count || 0} implemented`,
            authority: "governance_only",
            handoff: "improvement notes"
        }
    ].filter(Boolean);

    let offset = 0;
    const makeLane = (title, summary, handoff, tone, keys) => {
        const nodes = keys.map((key) => mapNodes.find((node) => node.key === key)).filter(Boolean);
        const lane = { title, summary, handoff, tone, nodes, offset };
        offset += nodes.length;
        return lane;
    };

    const lanes = [
        makeLane(
            "Observation",
            "World and market inputs enter as observations only.",
            "Observed facts must be logged before they count.",
            "online",
            ["watching"]
        ),
        makeLane(
            "COO Memory",
            "The orchestrator records state and exposes only a safe cockpit mirror.",
            "Logged state becomes dashboard state and research input.",
            "online",
            ["event_log", "live_bridge"]
        ),
        makeLane(
            "Research",
            "Private priors and models shape questions and hypotheses without execution authority.",
            "Research outputs become challenge notes and evidence packets.",
            "pending",
            ["worldview", "research_analyst", "strategy_lead", "shadow_intelligence"]
        ),
        makeLane(
            "Quant + Risk",
            "Bounded modelling can inform a gate; risk decides whether an idea may continue.",
            "Only passed gates can become paper-trial state.",
            "blocked",
            ["head_of_quant", "execution_registry"]
        ),
        makeLane(
            "Paper Trial",
            "Candidates become paper states only after gates; outcomes return to learning.",
            "Closed paper outcomes and lessons return to memory.",
            "online",
            ["trade_layer", "paper_account", "postmortem_loop"]
        ),
        makeLane(
            "Members",
            "Founding Fund Managers receive notifications and leave governance comments.",
            "Human notes improve the system without creating broker authority.",
            "pending",
            ["telegram_bot", "fund_manager_forum"]
        )
    ].filter((lane) => lane.nodes.length);

    const target = dashboardQuery("[data-flow-map]");
    if (target) {
        target.innerHTML = `
            <div class="system-flow-diagram">
                ${lanes.map(systemMapLane).join("")}
                <div class="flow-return-loop">
                    <strong>Closed-loop rule</strong>
                    <span>Every observation, hypothesis, risk decision, paper state, comment, and postmortem returns to the Event Log before it changes Qadam.</span>
                </div>
            </div>
        `;
    }
}

function renderSnapshotMeta(status, source) {
    const capital = status.capital || {};
    const d1Snapshot = status.d1_snapshot || {};
    const liveBridge = status.live_bridge || {};
    const generatedAt = formatTime(status.generated_at);
    const sourceLabel = source?.label || "static snapshot";
    const bridgeSourceLabel = source?.key === "live_bridge"
        ? "D9 live bridge connected"
        : "D9 static fallback loaded";
    setText("[data-mode-label]", `${dashboardText(status.mode).toUpperCase()} MODE`);
    setText("[data-capital-label]", `${formatMoney(capital.starting_balance_gbp)} first-month test`);
    setText(
        "[data-live-capital-label]",
        capital.live_capital_enabled ? "Live capital enabled" : "Live capital disabled"
    );
    setText("[data-snapshot-meta]", `Snapshot ${generatedAt} · schema ${status.schema_version} · ${sourceLabel}`);

    const banner = dashboardQuery("[data-status-banner]");
    if (banner) {
        banner.classList.remove("snapshot-error");
        banner.innerHTML = `
            <span>${status.d0_shell?.status === "frozen" ? "D0 shell frozen" : "D0 shell unknown"}</span>
            <span>${d1Snapshot.public_safe ? "D1 public-safe snapshot loaded" : "D1 snapshot metadata missing"}</span>
            <span>${liveBridge.status === "read_only_ready" ? bridgeSourceLabel : "D9 bridge contract pending"}</span>
            <span>${status.boundary || "Read-only dashboard snapshot."}</span>
        `;
    }
}

function renderPriorityCard(label, value, body, meta, tone = "neutral") {
    return `
        <article class="priority-card ${statusClass(tone)}">
            <span>${htmlText(label)}</span>
            <strong>${htmlText(value)}</strong>
            <p>${htmlText(body)}</p>
            <small>${htmlText(meta)}</small>
        </article>
    `;
}

function renderOperatingSummary(status, source) {
    const target = dashboardQuery("[data-operating-summary]");
    if (!target) return;

    const watching = asArray(status.watching);
    const sourceCounts = countBy(watching, "status");
    const pipelineSummary = asArray(status.source_pipeline_summary);
    const missingCredentialCount = pipelineSummary.reduce(
        (total, pipeline) => total + Number(pipeline.missing_credential_count || 0),
        0
    );
    const degradedSources = Number(sourceCounts.degraded || 0);
    const pendingSources = Number(sourceCounts.pending || 0);
    const localOnlySources = Number(sourceCounts.local_only || sourceCounts["local-only"] || 0);

    const cognition = status.cognition || {};
    const hypotheses = asArray(cognition.hypotheses);
    const shadowPackets = asArray(cognition.shadow_packets);
    const localResearch = asArray(cognition.local_research_assessments);
    const executableHypotheses = hypotheses.filter((hypothesis) => hypothesis.execution_allowed).length;

    const tradeLayer = status.trade_layer || {};
    const observedSignals = asArray(tradeLayer.watching);
    const candidates = asArray(tradeLayer.candidates);
    const blockedTrades = asArray(tradeLayer.blocked);
    const stagedOrders = asArray(tradeLayer.staged_orders);
    const submittedOrders = asArray(tradeLayer.submitted_orders);
    const paperOrders = stagedOrders.length + submittedOrders.length;

    const capital = status.capital || {};
    const maturityCount = Number(capital.maturity_closed_trade_count || 0);
    const maturityTarget = Number(capital.maturity_closed_trade_target || 100);
    const realized = Number(capital.realized_pnl_gbp || 0);
    const unrealized = Number(capital.unrealized_pnl_gbp || 0);
    const pnlTotal = realized + unrealized;

    const forbiddenActions = asArray(status.forbidden_actions);
    const liveCapital = Boolean(capital.live_capital_enabled);
    const brokerWriteBlocked = forbiddenActions.some((action) => /broker|write/i.test(`${action.action || ""} ${action.reason || ""}`));
    const liveBridge = status.live_bridge || {};
    const bridgeLabel = source?.key === "live_bridge" ? "Live bridge" : "Static fallback";
    const bridgeMeta = liveBridge.status === "read_only_ready" ? "read-only ready" : dashboardText(liveBridge.status, "bridge pending");

    target.innerHTML = [
        renderPriorityCard(
            "Paper account",
            formatMoney(capital.current_balance_gbp),
            `${formatMoney(pnlTotal)} total P&L · ${formatPercent(capital.drawdown_pct)} drawdown · ${maturityCount}/${maturityTarget} closed proof trades`,
            capital.live_capital_enabled ? "Live capital enabled" : "Live capital disabled",
            capital.live_capital_enabled ? "blocked" : "online"
        ),
        renderPriorityCard(
            "Source quality",
            `${sourceCounts.online || 0}/${watching.length} online`,
            `${degradedSources} degraded · ${pendingSources} pending · ${localOnlySources} local-only · ${missingCredentialCount} missing credentials`,
            "Evidence strength depends on source health",
            degradedSources || missingCredentialCount ? "degraded" : "online"
        ),
        renderPriorityCard(
            "Cognition",
            `${hypotheses.length} hypotheses`,
            `${shadowPackets.length} shadow packets · ${localResearch.length} local assessments · ${executableHypotheses} executable`,
            executableHypotheses ? "Unexpected execution permission" : "Research only",
            executableHypotheses ? "blocked" : "pending"
        ),
        renderPriorityCard(
            "Trade layer",
            `${candidates.length} candidates`,
            `${observedSignals.length} observed · ${blockedTrades.length} blocked · ${paperOrders} staged/submitted paper orders`,
            "Candidate is not order",
            paperOrders ? "pending" : "online"
        ),
        renderPriorityCard(
            "Safety state",
            liveCapital ? "Live capital enabled" : "Live capital disabled",
            `${forbiddenActions.length} hard blocks · broker writes ${brokerWriteBlocked ? "blocked" : "not recorded"} · browser read-only`,
            "Fail closed before paper execution",
            liveCapital ? "blocked" : "online"
        ),
        renderPriorityCard(
            "Bridge",
            bridgeLabel,
            `${bridgeMeta} · snapshot ${formatTime(status.generated_at)} · schema ${dashboardText(status.schema_version, "unknown")}`,
            source?.key === "live_bridge" ? "Serving protected status endpoint" : "Serving static safe snapshot",
            source?.key === "live_bridge" ? "online" : "pending"
        )
    ].join("");
}

function renderWatching(status) {
    const watching = asArray(status.watching);
    const pipelineSummary = asArray(status.source_pipeline_summary);
    const summaryByPipeline = new Map(pipelineSummary.map((pipeline) => [pipeline.pipeline, pipeline]));
    const sourceCounts = countBy(watching, "status");
    const degraded = Number(sourceCounts.degraded || 0);
    const pending = Number(sourceCounts.pending || 0);
    const missingCredentialCount = pipelineSummary.reduce(
        (total, pipeline) => total + Number(pipeline.missing_credential_count || 0),
        0
    );
    replacePanelBrief("watching", {
        question: "Are Qadam's inputs healthy enough to trust?",
        state: `${sourceCounts.online || 0}/${watching.length} online`,
        tone: degraded || pending || missingCredentialCount ? "degraded" : "online",
        primary: `${watching.length} watched sources across ${pipelineSummary.length} pipelines, with ${degraded} degraded, ${pending} pending, and ${missingCredentialCount} missing credentials.`,
        secondary: "Stale heartbeats, missing credentials, degraded feeds, local-only sources, and whether a source can influence signals.",
        boundary: "Sources create observations only. Weak or pending source state cannot become strong evidence or create orders."
    });
    const summary = dashboardQuery("[data-source-summary]");
    if (summary) {
        const history = asArray(status.source_heartbeat_history);
        const lastRun = history[history.length - 1];
        summary.innerHTML = [
            sourceSummary(status),
            renderMetric("Pipelines", pipelineSummary.length),
            renderMetric("Adapters", watching.filter((source) => source.promoted_adapter).length),
            renderMetric("Last heartbeat", formatTime(lastRun?.checked_at || status.generated_at))
        ].join("");
    }

    const grouped = watching.reduce((acc, source) => {
        const pipeline = source.pipeline || "unknown";
        acc[pipeline] = acc[pipeline] || [];
        acc[pipeline].push(source);
        return acc;
    }, {});

    const target = dashboardQuery("[data-watching-list]");
    if (!target) return;

    if (!watching.length) {
        target.innerHTML = `
            <article class="empty-state">
                <h3>Not connected yet</h3>
                <p>No watched-source records have been exported into this snapshot.</p>
            </article>
        `;
        return;
    }

    target.innerHTML = Object.entries(grouped)
        .sort(([a], [b]) => a.localeCompare(b))
        .map(([pipeline, sources], index) => {
            const counts = countBy(sources, "status");
            const pipelineCounts = summaryByPipeline.get(pipeline) || {};
            const missingCredentials = sources.filter((source) => source.credential_status === "missing").length;
            const adapterReady = sources.filter((source) => source.promoted_adapter).length;
            const signalReady = sources.filter((source) => source.can_influence_signals).length;
            const localOnly = pipelineCounts.local_only_count || counts.local_only || counts["local-only"] || 0;
            const rows = sources
                .sort((a, b) => String(a.source_name).localeCompare(String(b.source_name)))
                .map((source) => `
                    <li class="source-row">
                        <div class="source-main">
                            ${renderStatusPill(source.status)}
                            <div>
                                <strong>${htmlText(source.source_name, source.source_key)}</strong>
                                <span>${htmlText(source.readiness)} · tier ${htmlText(source.tier)} · ${htmlText(source.cadence, "cadence unknown")}</span>
                            </div>
                        </div>
                        <div class="source-meta">
                            ${renderInlineBadge(source.credential_status, source.credential_status === "missing" ? "degraded" : "online")}
                            ${renderInlineBadge(source.promoted_adapter ? "adapter" : "registry", source.promoted_adapter ? "online" : "pending")}
                            ${renderInlineBadge(source.auth_class, source.auth_class === "credential_required" ? "degraded" : "online")}
                            ${renderInlineBadge(source.registry_status, "pending")}
                            ${renderInlineBadge(`${dashboardText(source.endpoint_count, "0")} endpoints`, source.endpoint_count ? "online" : "pending")}
                            ${renderInlineBadge(`trust ${dashboardText(source.trust_score, "n/a")}`, source.trust_score ? "online" : "pending")}
                            ${renderInlineBadge(source.can_influence_signals ? "can influence signals" : "evidence blocked", source.can_influence_signals ? "online" : "blocked")}
                            ${renderInlineBadge(`payload ${formatTime(source.last_payload_time)}`, source.last_payload_time ? "online" : "pending")}
                            ${renderInlineBadge(`latency ${formatLatency(source.latency_ms)}`, source.latency_ms ? "online" : "pending")}
                            ${renderInlineBadge(formatTime(source.last_heartbeat), source.status)}
                        </div>
                        <p>${htmlText(source.degraded_reason || source.raw_status)} · ${htmlText(source.influence_boundary, "blocked until signal integrity gate")}</p>
                    </li>
                `)
                .join("");
            return `
                <details class="pipeline-row" ${index === 0 ? "open" : ""}>
                    <summary>
                        <h3>${htmlText(pipeline)}</h3>
                        <p>${sources.length} sources · ${counts.online || 0} online · ${counts.degraded || 0} degraded · ${counts.pending || 0} pending · ${localOnly} local-only · ${missingCredentials} credentials missing · ${adapterReady} adapters · ${signalReady} signal-influencing</p>
                    </summary>
                    <ul class="source-table">${rows}</ul>
                </details>
            `;
        })
        .join("");
}

function renderCognition(status) {
    const target = dashboardQuery("[data-cognition]");
    if (!target) return;

    const cognition = status.cognition || {};
    const hypotheses = asArray(cognition.hypotheses);
    const evidencePackets = asArray(cognition.evidence_packets);
    const shadowPackets = asArray(cognition.shadow_packets);
    const localResearch = asArray(cognition.local_research_assessments);
    const activity = asArray(cognition.model_activity);
    const focus = asArray(cognition.current_focus);
    const timeline = asArray(cognition.analysis_timeline);
    const blockedReasons = asArray(cognition.blocked_reasons);
    const philosophy = status.decision_philosophy || {};
    const evidenceBySignal = evidencePackets.reduce((acc, packet) => {
        if (packet.signal_id) acc[packet.signal_id] = packet;
        return acc;
    }, {});
    const evidenceItemCount = sumNestedItems(evidencePackets, "items");
    const executableHypotheses = hypotheses.filter((hypothesis) => hypothesis.execution_allowed);
    const latestAssessment = localResearch[localResearch.length - 1] || {};
    const timelineHtml = timeline.length
        ? timeline.map((step) => `<li>${htmlText(step)}</li>`).join("")
        : `<li>${htmlText("trade layer not reached")}</li>`;

    const hypothesisHtml = hypotheses.length
        ? hypotheses.slice(0, 5).map((hypothesis) => {
            const packet = evidenceBySignal[hypothesis.signal_id] || {};
            const evidenceItems = asArray(packet.items);
            const evidenceHtml = evidenceItems.length
                ? evidenceItems.slice(0, 3).map((item) => `
                    <li>
                        <strong>${htmlText(item.source, "evidence source")}</strong>
                        <span>${htmlText(item.summary, "No summary")} · trust ${htmlText(item.trust_score, "n/a")}</span>
                    </li>
                `).join("")
                : `<li><strong>No evidence packet</strong><span>Waiting for corroborated source observations.</span></li>`;
            return `
                <article class="cognition-card hypothesis-card">
                    <div class="cognition-card-head">
                        ${renderStatusPill(hypothesis.status || "blocked")}
                        <p class="label">${htmlText(hypothesis.instrument_focus, "instrument watchlist")}</p>
                    </div>
                    <h3>${htmlText(hypothesis.title, "Shadow hypothesis")}</h3>
                    <p>${htmlText(hypothesis.thesis, "No thesis yet.")}</p>
                    <div class="tag-row">
                        ${renderInlineBadge("Hypothesis, not trade", "blocked")}
                        ${renderInlineBadge("Execution blocked", "blocked")}
                        ${renderInlineBadge(`created ${formatTime(hypothesis.created_at)}`, "pending")}
                        ${renderInlineBadge(`packet ${dashboardText(hypothesis.evidence_packet_id, "not linked")}`, packet.signal_id ? "online" : "pending")}
                    </div>
                    <div class="summary-strip compact">
                        ${renderMetric("Confidence", formatConfidence(hypothesis.confidence))}
                        ${renderMetric("Evidence", htmlText(hypothesis.evidence_source_count, "0"))}
                        ${renderMetric("Execution", hypothesis.execution_allowed ? "Allowed" : "Blocked")}
                        ${renderMetric("Generated by", htmlText(hypothesis.generated_by, "unknown"))}
                    </div>
                    <dl class="cognition-facts">
                        <div>
                            <dt>Blocked because</dt>
                            <dd>${htmlText(hypothesis.blocked_reason, "blocked")}</dd>
                        </div>
                        <div>
                            <dt>Invalidation</dt>
                            <dd>${htmlText(hypothesis.invalidation, "No invalidation recorded.")}</dd>
                        </div>
                        <div>
                            <dt>Missing corroboration</dt>
                            <dd class="tag-row">${renderTagList(hypothesis.missing_correlations, "No missing correlations recorded")}</dd>
                        </div>
                        <div>
                            <dt>Boundary</dt>
                            <dd>Hypothesis only. It cannot enter the trade layer until the Signal Integrity Gate and Risk Agent exist.</dd>
                        </div>
                    </dl>
                    ${renderDecisionWorldviewBlock(philosophy)}
                    <ul class="evidence-list">${evidenceHtml}</ul>
                </article>
            `;
        }).join("")
        : `
            <article class="cognition-card hypothesis-card">
                <h3>No hypotheses yet</h3>
                <p>Qadam is waiting for shadow intelligence inputs before showing a live analysis queue.</p>
            </article>
        `;

    const activityHtml = activity.length
        ? activity.map((model) => `
            <article class="model-activity-card">
                <p class="label">${htmlText(model.role, "model role")}</p>
                <h3>${htmlText(model.status, "not called")}</h3>
                <p>${htmlText(model.current_task, "No current task.")}</p>
                <div class="tag-row">
                    ${renderInlineBadge(model.provider, model.status)}
                    ${renderInlineBadge(model.model, model.status)}
                    ${renderInlineBadge(model.authority, "blocked")}
                </div>
            </article>
        `).join("")
        : `<article class="model-activity-card"><h3>No model activity yet</h3><p>Provider checks have not run.</p></article>`;

    const shadowPacketHtml = shadowPackets.length
        ? shadowPackets.slice(0, 5).map((packet) => `
            <li>
                <strong>${htmlText(packet.agent_key, "research analyst")} · ${htmlText(packet.status, "queued")}</strong>
                <span>${htmlText(packet.summary, "No packet summary")} · ${htmlText(packet.uncertainty, "uncertainty unknown")} uncertainty</span>
                <small>${htmlText(asArray(packet.source_event_refs).join(", "), "No source refs")} · ${formatTime(packet.created_at)}</small>
                <small>${htmlText(packet.boundary, "Shadow triage only. No execution authority.")}</small>
            </li>
        `).join("")
        : `<li><strong>No shadow packets</strong><span>Research queue is empty.</span></li>`;

    const evidencePacketHtml = evidencePackets.length
        ? evidencePackets.slice(0, 5).map((packet) => {
            const packetItems = asArray(packet.items);
            const itemHtml = packetItems.length
                ? packetItems.slice(0, 3).map((item) => `
                    <li>
                        <strong>${htmlText(item.source, "evidence source")}</strong>
                        <span>${htmlText(item.event_type, "event")} · ${htmlText(item.summary, "No summary")}</span>
                    </li>
                `).join("")
                : `<li><strong>No evidence items</strong><span>Waiting for source observations.</span></li>`;
            return `
                <article class="evidence-packet-card">
                    <h3>${htmlText(packet.trail_id, "Evidence packet")}</h3>
                    <div class="tag-row">
                        ${renderInlineBadge(`${packet.source_count || 0} sources`, packet.source_count ? "online" : "pending")}
                        ${renderInlineBadge(`${packetItems.length} evidence items`, packetItems.length ? "online" : "pending")}
                        ${renderInlineBadge(`avg trust ${dashboardText(packet.average_trust_score, "n/a")}`, packet.average_trust_score ? "online" : "pending")}
                        ${renderInlineBadge(`min trust ${dashboardText(packet.min_trust_score, "n/a")}`, packet.min_trust_score ? "online" : "pending")}
                        ${renderInlineBadge(`created ${formatTime(packet.created_at)}`, "pending")}
                    </div>
                    <dl class="cognition-facts">
                        <div>
                            <dt>Sources</dt>
                            <dd>${htmlText(asArray(packet.sources).join(", "), "No sources recorded")}</dd>
                        </div>
                        <div>
                            <dt>Missing</dt>
                            <dd>${htmlText(asArray(packet.missing_correlations).join(", "), "none recorded")}</dd>
                        </div>
                    </dl>
                    <ul class="evidence-list">${itemHtml}</ul>
                </article>
            `;
        }).join("")
        : `<article class="evidence-packet-card"><h3>No evidence packets</h3><p class="mini">Evidence packets appear after shadow triage has source observations.</p></article>`;

    const localResearchHtml = localResearch.length
        ? localResearch.slice(-3).reverse().map((assessment) => `
            <article class="cognition-card research-assessment-card">
                <div class="cognition-card-head">
                    ${renderStatusPill(assessment.status || "shadow_only")}
                    <p class="label">${htmlText(assessment.mode, "local assessment")}</p>
                </div>
                <h3>${htmlText(assessment.watch_focus, "Research Analyst focus")}</h3>
                <p>${htmlText(assessment.summary, "No local assessment summary.")}</p>
                <div class="summary-strip compact">
                    ${renderMetric("Confidence", formatConfidence(assessment.confidence))}
                    ${renderMetric("Escalation", htmlText(assessment.escalation_recommendation, "hold shadow"))}
                    ${renderMetric("Execution", assessment.execution_allowed ? "Allowed" : "Blocked")}
                    ${renderMetric("Paper order", assessment.paper_order_allowed ? "Allowed" : "Blocked")}
                </div>
                <section class="trade-check-section">
                    <p class="label">Anomalies</p>
                    <div class="tag-row">${renderTagList(assessment.anomalies, "No anomalies recorded")}</div>
                </section>
                <section class="trade-check-section">
                    <p class="label">Missing corroboration</p>
                    <div class="tag-row">${renderTagList(assessment.missing_correlations, "No missing correlations recorded")}</div>
                </section>
                <section class="trade-check-section">
                    <p class="label">Next questions</p>
                    <div class="tag-row">${renderTagList(assessment.next_questions, "No questions recorded")}</div>
                </section>
                <p class="mini">${htmlText(assessment.provider, "local")} · ${htmlText(assessment.model, "model")} · ${formatTime(assessment.created_at)}</p>
            </article>
        `).join("")
        : `<article class="cognition-card research-assessment-card"><h3>No local assessment yet</h3><p>The Research Analyst has not compressed the shadow queue.</p></article>`;

    target.innerHTML = `
        ${renderPanelBrief({
            id: "cognition",
            question: "What is Qadam thinking about, and why is it blocked?",
            state: `${hypotheses.length} hypotheses`,
            tone: executableHypotheses.length ? "blocked" : "pending",
            primary: `${shadowPackets.length} shadow packets, ${evidencePackets.length} evidence packets, ${localResearch.length} local assessments, and ${activity.length} model activity records are in the current queue.`,
            secondary: "Model-only reasoning, missing corroboration, stale evidence, blocked reasons, and whether anything unexpectedly claims execution permission.",
            boundary: cognition.boundary || "Research notebook only. A hypothesis is not a trade and cannot bypass risk."
        })}
        <section class="cognition-section">
            <p class="label">Cognition state</p>
            <div class="summary-strip compact">
                ${renderMetric("State", cognition.status || "shadow ready")}
                ${renderMetric("Focus items", focus.length)}
                ${renderMetric("Hypotheses", hypotheses.length)}
                ${renderMetric("Evidence items", evidenceItemCount)}
                ${renderMetric("Shadow packets", shadowPackets.length)}
                ${renderMetric("Local assessments", localResearch.length)}
                ${renderMetric("Models", activity.length)}
                ${renderMetric("Execution", executableHypotheses.length ? "Unexpected allowed" : "Blocked")}
            </div>
            <div class="tag-row">
                ${renderInlineBadge("Hypothesis, not trade", "blocked")}
                ${renderInlineBadge("Trade layer not reached", "blocked")}
                ${renderInlineBadge(`latest local assessment ${formatTime(latestAssessment.created_at)}`, latestAssessment.created_at ? "online" : "pending")}
            </div>
        </section>
        <section class="cognition-section">
            <p class="label">Current focus</p>
            <div class="focus-box">${renderTagList(focus, "No active focus")}</div>
        </section>
        <section class="cognition-section">
            <p class="label">Model activity</p>
            <div class="model-activity-grid">${activityHtml}</div>
        </section>
        <section class="cognition-section">
            <p class="label">Shadow packets</p>
            <ul class="status-list packet-list">${shadowPacketHtml}</ul>
        </section>
        <section class="cognition-section">
            <p class="label">Local Research Analyst</p>
            <div class="hypothesis-stack">${localResearchHtml}</div>
        </section>
        <section class="cognition-section">
            <p class="label">Hypotheses and evidence</p>
            <div class="hypothesis-stack">${hypothesisHtml}</div>
        </section>
        <section class="cognition-section">
            <p class="label">Evidence packet index</p>
            <div class="evidence-packet-grid">${evidencePacketHtml}</div>
        </section>
        <section class="cognition-section cognition-two-col">
            <div>
                <p class="label">Analysis timeline</p>
                <ol class="timeline-list">${timelineHtml}</ol>
            </div>
            <div>
                <p class="label">Blocked reasons</p>
                <div class="tag-row">${renderTagList(blockedReasons, "No blocks recorded")}</div>
            </div>
        </section>
        <p class="mini">${htmlText(cognition.boundary, "Shadow-only cognition.")}</p>
    `;
}

function renderDecisionWorldviewBlock(philosophy) {
    const lenses = asArray(philosophy.active_lenses).slice(0, 3);
    const lensTags = lenses.map((lens) => `${lens.claim_type}: ${lens.corroboration_status}`);
    return `
        <section class="trade-check-section worldview-decision-context">
            <p class="label">Worldview lens</p>
            <div class="tag-row">${renderTagList(lensTags, "No worldview lens recorded")}</div>
            <p class="mini">${htmlText(philosophy.boundary, "World-model claims are private priors, not evidence or trade triggers.")}</p>
        </section>
    `;
}

function renderWorldview(status) {
    const target = dashboardQuery("[data-worldview]");
    if (!target) return;
    const philosophy = status.decision_philosophy || {};
    const lenses = asArray(philosophy.active_lenses);
    const lensCards = lenses.length
        ? lenses.slice(0, 5).map((lens) => `
            <article class="evidence-packet-card">
                <p class="label">${htmlText(lens.claim_type, "worldview lens")}</p>
                <h3>${htmlText(lens.key, "private prior")}</h3>
                <p>${htmlText(lens.claim, "No claim text.")}</p>
                <div class="tag-row">
                    ${renderInlineBadge(lens.corroboration_status, "pending")}
                    ${renderInlineBadge(`${asArray(lens.live_sources_to_check).length} live checks`, "pending")}
                    ${renderInlineBadge(`${asArray(lens.market_channels).length} channels`, "pending")}
                </div>
                <p class="mini">${htmlText(lens.mechanism, "No mechanism recorded.")}</p>
            </article>
        `).join("")
        : `<article class="evidence-packet-card"><h3>No worldview cards</h3><p class="mini">The world-model corpus has not been exported into the status contract.</p></article>`;
    target.innerHTML = `
        ${renderPanelBrief({
            id: "private_edge_layer",
            question: "Which private priors are shaping the questions?",
            state: `${philosophy.claim_count || 0} claim cards`,
            tone: philosophy.status === "ok" ? "online" : "pending",
            primary: `${philosophy.corpus_file_count || 0} corpus files and ${philosophy.foundational_prior_count || 0} foundational priors are available as context.`,
            secondary: "Priors being mistaken for evidence, market channels without live corroboration, or a missing observable to check.",
            boundary: philosophy.boundary || "Worldview is context only, not evidence, and cannot trigger trades."
        })}
        <div class="summary-strip">
            ${renderMetric("Corpus files", htmlText(philosophy.corpus_file_count, "0"))}
            ${renderMetric("Claim cards", htmlText(philosophy.claim_count, "0"))}
            ${renderMetric("Private priors", htmlText(philosophy.foundational_prior_count, "0"))}
            ${renderMetric("Authority", "Prior only")}
        </div>
        <p class="empty-state">${htmlText(philosophy.trading_philosophy, "Qadam's private worldview shapes questions, not direct execution.")}</p>
        <section class="cognition-section">
            <p class="label">Decision chain</p>
            <ol class="timeline-list">${asArray(philosophy.decision_chain).map((step) => `<li>${htmlText(step)}</li>`).join("")}</ol>
        </section>
        <section class="cognition-section">
            <p class="label">Active private lenses</p>
            <div class="evidence-packet-grid">${lensCards}</div>
        </section>
        <p class="mini">${htmlText(philosophy.boundary, "World-model claims are private priors, not factual evidence or trade triggers.")}</p>
    `;
}

function renderForbidden(status) {
    const target = dashboardQuery("[data-forbidden-actions]");
    if (!target) return;
    const actions = asArray(status.forbidden_actions);
    const brokerBlocked = actions.some((action) => /broker|write/i.test(`${action.key || ""} ${action.reason || ""}`));
    replacePanelBrief("forbidden_actions", {
        question: "Which paths are deliberately blocked?",
        state: `${actions.length} hard blocks`,
        tone: actions.length ? "blocked" : "pending",
        primary: actions.length
            ? `Qadam is carrying ${actions.length} explicit safety blocks in this snapshot. Broker writes are ${brokerBlocked ? "blocked" : "not separately recorded"}.`
            : "No forbidden-action records have been exported into this snapshot.",
        secondary: "Live-capital, broker-write, stale-data, missing-credential, risk, and kill-switch boundaries.",
        boundary: "This panel reports hard stops only. It cannot unlock blocked authority or create an exception."
    });
    target.innerHTML = actions.length
        ? actions.map((action) => `
            <li>
                <strong>${htmlText(action.key)}</strong>
                <span>${htmlText(action.reason)}</span>
            </li>
        `).join("")
        : `
            <li>
                <strong>Not connected yet</strong>
                <span>No forbidden-action records have been exported into this snapshot.</span>
            </li>
        `;
}

function renderCommunications(status) {
    const target = dashboardQuery("[data-communications]");
    if (!target) return;
    const telegram = status.communications?.telegram || {};
    const messages = asArray(telegram.recent_messages);
    const classes = asArray(telegram.active_message_classes);
    const messageRows = messages.length
        ? messages.map((message) => `
            <li>
                <strong>${htmlText(message.title, "Telegram message")}</strong>
                <span>${htmlText(message.message_class, "message")} · ${htmlText(message.target_ref, "qadam")}</span>
                <div class="comment-meta">
                    ${renderInlineBadge(message.status || "queued", message.status || "pending")}
                    ${renderInlineBadge(message.mode || "dry_run", message.mode === "live_send" ? "degraded" : "pending")}
                    ${renderInlineBadge(message.send_allowed ? "send allowed" : "send blocked", message.send_allowed ? "degraded" : "online")}
                </div>
                <small>${formatTime(message.created_at)}</small>
            </li>
        `).join("")
        : `
            <li>
                <strong>No Telegram messages</strong>
                <span>No dry-run member communications have been queued yet.</span>
            </li>
        `;
    target.innerHTML = `
        ${renderPanelBrief({
            id: "telegram_communications",
            question: "What has Qadam told founding members?",
            state: telegram.status || "dry_run",
            tone: telegram.failed_count ? "degraded" : (telegram.status === "dry_run" ? "pending" : "online"),
            primary: `${telegram.pending_queue_count || 0} queued, ${telegram.sent_count || 0} sent, ${telegram.failed_count || 0} failed, and ${telegram.suppressed_count || 0} suppressed notifications are visible in the outbox mirror.`,
            secondary: "Dry-run/live-send mode, failed sends, suppressed messages, queue growth, and whether the bot/chat configuration is only reported as configured.",
            boundary: telegram.boundary || status.communications?.boundary || "Telegram is outbound notify-only and cannot place, approve, reject, modify, close, or resize trades."
        })}
        <div class="summary-strip compact">
            ${renderMetric("Status", telegram.status || "disabled")}
            ${renderMetric("Mode", telegram.mode || "dry_run")}
            ${renderMetric("Verified", telegram.verified_member_count || 0)}
            ${renderMetric("Pending", telegram.pending_member_count || 0)}
            ${renderMetric("Queued", telegram.pending_queue_count || 0)}
            ${renderMetric("Failed", telegram.failed_count || 0)}
            ${renderMetric("Suppressed", telegram.suppressed_count || 0)}
            ${renderMetric("Last sent", formatTime(telegram.last_sent_time))}
        </div>
        <div class="tag-row">
            ${renderInlineBadge(`send gate ${telegram.send_gate || "disabled"}`, telegram.send_gate === "enabled" ? "degraded" : "online")}
            ${renderInlineBadge(telegram.bot_configured ? "bot configured" : "bot token missing", telegram.bot_configured ? "online" : "pending")}
            ${renderInlineBadge(telegram.default_chat_configured ? "chat configured" : "chat pending", telegram.default_chat_configured ? "online" : "pending")}
            ${renderInlineBadge(`${telegram.dry_run_message_count || 0} dry-run messages`, telegram.dry_run_message_count ? "online" : "pending")}
        </div>
        <section class="trade-intent-section">
            <p class="label">Message classes</p>
            <div class="tag-row">${renderTagList(classes, "No message classes queued")}</div>
        </section>
        <section class="trade-intent-section">
            <p class="label">Recent outbox</p>
            <ul class="status-list communications-list">${messageRows}</ul>
        </section>
        <p class="mini">${htmlText(telegram.boundary || status.communications?.boundary || "Telegram is outbound-only and notify-only.")}</p>
    `;
}

function tradeStateLabel(status) {
    const labels = {
        observed_signal: "Watching",
        hypothesis: "Thinking About",
        candidate: "Considering Trade",
        blocked: "Blocked",
        risk_review: "Risk Review",
        staged_paper_order: "Preparing Paper Trade",
        submitted_paper_order: "Submitted Paper Trade",
        open_position: "Open Paper Position",
        exit_planned: "Exit Planned",
        closed_trade: "Closed",
        postmortem_due: "Postmortem Due",
        postmortem_complete: "Postmortem Complete"
    };
    return labels[status] || dashboardText(status, "Trade state unknown");
}

function renderTrades(status) {
    const target = dashboardQuery("[data-trade-layer]");
    if (!target) return;
    const tradeLayer = status.trade_layer || {};
    const tradingView = status.tradingview_alerts || {};
    const summary = tradeLayer.summary || {};
    const philosophy = status.decision_philosophy || {};
    const worldviewBlock = renderDecisionWorldviewBlock(philosophy);
    const rows = [
        ["Observed signals", asArray(tradeLayer.watching)],
        ["Candidates", asArray(tradeLayer.candidates)],
        ["Blocked", asArray(tradeLayer.blocked)],
        ["Staged orders", asArray(tradeLayer.staged_orders)],
        ["Submitted", asArray(tradeLayer.submitted_orders)],
        ["Open", asArray(tradeLayer.open_positions)],
        ["Closed", asArray(tradeLayer.closed_trades)],
        ["Postmortems due", asArray(tradeLayer.postmortems_due)]
    ];

    const renderObservedSignalCard = (signal) => {
        const indicatorState = signal.indicator_state || {};
        const indicatorTags = Object.entries(indicatorState).map(([key, value]) => `${key}: ${value}`);
        return `
            <article class="trade-intent-card pending">
                <div class="cognition-card-head">
                    ${renderStatusPill(signal.status || "observed_signal")}
                    <p class="label">${htmlText(tradeStateLabel(signal.status || "observed_signal"))} · ${htmlText(signal.source_type, "observed source")}</p>
                </div>
                <h3>${htmlText(signal.instrument || signal.symbol, "Observed signal")}</h3>
                <p>${htmlText(signal.trigger || signal.chart_context, "No alert trigger recorded.")}</p>
                <div class="tag-row">
                    ${renderInlineBadge("Observed signal only", "pending")}
                    ${renderInlineBadge(signal.trade_candidate_created ? "candidate created" : "not a candidate", signal.trade_candidate_created ? "blocked" : "online")}
                    ${renderInlineBadge(signal.execution_allowed ? "execution allowed" : "execution blocked", signal.execution_allowed ? "blocked" : "online")}
                    ${renderInlineBadge(signal.paper_order_allowed ? "paper order allowed" : "no paper order", signal.paper_order_allowed ? "blocked" : "online")}
                </div>
                <div class="summary-strip compact">
                    ${renderMetric("Timeframe", htmlText(signal.timeframe, "unknown"))}
                    ${renderMetric("Setup", htmlText(signal.setup_type, "unknown"))}
                    ${renderMetric("Direction", htmlText(signal.direction, "watch"))}
                    ${renderMetric("Price", htmlText(signal.price, "not supplied"))}
                </div>
                <section class="trade-check-section">
                    <p class="label">Indicator state</p>
                    <div class="tag-row">${renderTagList(indicatorTags, "No indicator state recorded")}</div>
                </section>
                ${worldviewBlock}
                <dl class="trade-facts">
                    <div>
                        <dt>Chart context</dt>
                        <dd>${htmlText(signal.chart_context, "No chart context.")}</dd>
                    </div>
                    <div>
                        <dt>Observed</dt>
                        <dd>${formatTime(signal.observed_at)} · received ${formatTime(signal.received_at)}</dd>
                    </div>
                    <div>
                        <dt>Authority</dt>
                        <dd>${signal.execution_allowed ? "Execution allowed" : "Execution blocked"} · ${signal.paper_order_allowed ? "paper order allowed" : "no paper order"}</dd>
                    </div>
                    <div>
                        <dt>Source</dt>
                        <dd>${htmlText(signal.source, "unknown")} · ${htmlText(signal.alert_id, "no alert id")}</dd>
                    </div>
                </dl>
                <p class="mini">${htmlText(signal.boundary, "Observed signal only.")}</p>
            </article>
        `;
    };

    const renderTradeIntentCard = (intent, tone = "pending") => {
        const filterEntries = Object.entries(intent.akber_filter || {});
        const riskEntries = Object.entries(intent.risk_checks || {});
        const filterHtml = filterEntries.length
            ? filterEntries.map(([key, value]) => {
                const normalized = String(value);
                return renderInlineBadge(`${key}: ${normalized}`, normalized.includes("failed") || normalized.includes("missing") ? "blocked" : "pending");
            }).join("")
            : renderInlineBadge("filter not recorded", "pending");
        const riskHtml = riskEntries.length
            ? riskEntries.map(([key, value]) => {
                const normalized = String(value);
                return renderInlineBadge(`${key}: ${normalized}`, normalized.includes("blocked") ? "blocked" : "pending");
            }).join("")
            : renderInlineBadge("risk checks not recorded", "pending");
        return `
            <article class="trade-intent-card ${statusClass(tone)}">
                <div class="cognition-card-head">
                    ${renderStatusPill(intent.status || tone)}
                    <p class="label">${htmlText(tradeStateLabel(intent.status || tone))} · ${htmlText(intent.venue, "venue unknown")}</p>
                </div>
                <h3>${htmlText(intent.instrument, "Trade intent")}</h3>
                <p>${htmlText(intent.catalyst, "No catalyst recorded.")}</p>
                <div class="tag-row">
                    ${renderInlineBadge(intent.status === "blocked" ? "Blocked trade" : "Candidate, not order", intent.status === "blocked" ? "blocked" : "pending")}
                    ${renderInlineBadge(intent.execution_allowed ? "execution allowed" : "execution blocked", intent.execution_allowed ? "blocked" : "online")}
                    ${renderInlineBadge(intent.paper_order_allowed ? "paper order allowed" : "no paper order", intent.paper_order_allowed ? "blocked" : "online")}
                    ${renderInlineBadge(intent.source_type, "pending")}
                </div>
                <div class="summary-strip compact">
                    ${renderMetric("Direction", htmlText(intent.direction, "unknown"))}
                    ${renderMetric("Qadam prob.", formatProbability(intent.probability_estimate))}
                    ${renderMetric("Market prob.", formatProbability(intent.market_implied_probability))}
                    ${renderMetric("Risk", `${formatMoney(intent.risk_size_gbp)} / ${htmlText(intent.risk_size_pct, "0")}%`)}
                </div>
                <dl class="trade-facts">
                    <div>
                        <dt>Evidence</dt>
                        <dd>${htmlText(intent.evidence_summary, "No evidence summary.")}</dd>
                    </div>
                    <div>
                        <dt>Entry</dt>
                        <dd>${htmlText(intent.proposed_entry, "No entry recorded.")}</dd>
                    </div>
                    <div>
                        <dt>Invalidation</dt>
                        <dd>${htmlText(intent.invalidation, "No invalidation recorded.")}</dd>
                    </div>
                    <div>
                        <dt>Hold window</dt>
                        <dd>${htmlText(intent.holding_window, "Unknown")}</dd>
                    </div>
                    <div>
                        <dt>Blocked reason</dt>
                        <dd>${htmlText(intent.blocked_reason || intent.risk_state, "Not reviewed by Risk Agent")}</dd>
                    </div>
                    <div>
                        <dt>Strategy</dt>
                        <dd>${htmlText(intent.strategy, "No strategy recorded.")}</dd>
                    </div>
                    <div>
                        <dt>Price gap</dt>
                        <dd>${htmlText(intent.price_gap, "No price gap recorded.")}</dd>
                    </div>
                    <div>
                        <dt>Source signal</dt>
                        <dd>${htmlText(intent.source_signal_id, "No source signal id")} · updated ${formatTime(intent.updated_at)}</dd>
                    </div>
                </dl>
                <section class="trade-check-section">
                    <p class="label">Akber filter</p>
                    <div class="tag-row">${filterHtml}</div>
                </section>
                <section class="trade-check-section">
                    <p class="label">Risk checks</p>
                    <div class="tag-row">${riskHtml}</div>
                </section>
                ${worldviewBlock}
                <section class="trade-check-section">
                    <p class="label">Tags</p>
                    <div class="tag-row">${renderTagList(intent.tags, "No tags recorded")}</div>
                </section>
                <p class="mini">${htmlText(intent.boundary, "Trade intent only. No broker route exists.")}</p>
            </article>
            `;
    };

    const observedSignals = asArray(tradeLayer.watching);
    const candidates = asArray(tradeLayer.candidates);
    const blocked = asArray(tradeLayer.blocked);

    const observedHtml = observedSignals.length
        ? observedSignals.map(renderObservedSignalCard).join("")
        : `<article class="trade-intent-card"><h3>No observed signals</h3><p>No TradingView or source-derived observed signal is present in the local snapshot.</p></article>`;

    const candidatesHtml = candidates.length
        ? candidates.map((intent) => renderTradeIntentCard(intent, "pending")).join("")
        : `<article class="trade-intent-card"><h3>No candidates</h3><p>No structured candidate is present in the local Trade Intent Store.</p></article>`;

    const blockedHtml = blocked.length
        ? blocked.map((intent) => renderTradeIntentCard(intent, "blocked")).join("")
        : `<article class="trade-intent-card"><h3>No blocked trades</h3><p>No blocked trade record is present yet.</p></article>`;

    const orderStateHtml = rows.slice(3).map(([label, items]) => `
        <li>
            <strong>${htmlText(label)}</strong>
            <span>${items.length ? `${items.length} records` : "not connected yet"}</span>
        </li>
    `).join("");

    target.innerHTML = `
        ${renderPanelBrief({
            id: "trade_layer",
            question: "Where are ideas on the paper-trade ladder?",
            state: `${candidates.length} candidates`,
            tone: blocked.length ? "blocked" : (candidates.length ? "pending" : "online"),
            primary: `${observedSignals.length} observed signals, ${candidates.length} candidates, ${blocked.length} blocked trades, and ${(asArray(tradeLayer.staged_orders).length + asArray(tradeLayer.submitted_orders).length)} staged/submitted paper orders are in the current snapshot.`,
            secondary: "Candidates without risk checks, blocked reasons, staged/submitted paper orders, open positions, and postmortems due.",
            boundary: tradeLayer.boundary || "Candidate is not order. Live capital stays disabled; only explicit paper state counts."
        })}
        <div class="summary-strip">${rows.map(([label, items]) => renderMetric(label, items.length)).join("")}</div>
        <p class="empty-state">${htmlText(tradeLayer.boundary, "D5 trade intent is local and non-executing.")}</p>
        <div class="trade-board-meta">
            ${renderInlineBadge(`store ${summary.status || tradeLayer.store_status || "unknown"}`, tradeLayer.store_status === "ok" ? "online" : "degraded")}
            ${renderInlineBadge(`${summary.intent_count || 0} local records`, summary.intent_count ? "online" : "pending")}
            ${renderInlineBadge(`${summary.observed_signal_count || observedSignals.length || 0} observed signals`, observedSignals.length ? "online" : "pending")}
            ${renderInlineBadge(`${summary.candidate_count || candidates.length || 0} candidates`, candidates.length ? "pending" : "online")}
            ${renderInlineBadge(`${summary.blocked_count || blocked.length || 0} blocked`, blocked.length ? "blocked" : "online")}
            ${renderInlineBadge(`${summary.execution_allowed_count || 0} execution allowed`, summary.execution_allowed_count ? "blocked" : "online")}
            ${renderInlineBadge(`${summary.paper_order_allowed_count || 0} paper orders allowed`, summary.paper_order_allowed_count ? "blocked" : "online")}
        </div>
        <section class="trade-intent-section">
            <p class="label">TradingView alert source</p>
            <div class="summary-strip compact">
                ${renderMetric("Receiver", tradingView.receiver_status || "local contract only")}
                ${renderMetric("Dedupe", tradingView.duplicate_protection || "dedupe key")}
                ${renderMetric("Alerts", tradingView.alert_count || 0)}
                ${renderMetric("Latest", formatTime(tradingView.latest_observed_at))}
                ${renderMetric("Execution", `${tradingView.execution_allowed_count || 0} allowed`)}
                ${renderMetric("Paper orders", `${tradingView.paper_order_allowed_count || 0} allowed`)}
                ${renderMetric("Candidates", `${tradingView.trade_candidate_created_count || 0} created`)}
                ${renderMetric("Source state", tradingView.status || "not initialized")}
            </div>
            <p class="mini">${htmlText(tradingView.boundary, "TradingView alerts are observed signals only. D7 has no execution route.")}</p>
        </section>
        <section class="trade-intent-section">
            <p class="label">Trade state ladder</p>
            <ol class="timeline-list">
                <li>Watching · observed signal only</li>
                <li>Considering Trade · candidate, not order</li>
                <li>Blocked · failed evidence, risk, policy, latency, or credential checks</li>
                <li>Preparing Paper Trade · unavailable until Risk Agent and broker adapter exist</li>
                <li>Postmortem · unavailable until closed paper trades exist</li>
            </ol>
        </section>
        <section class="trade-intent-section">
            <p class="label">Observed signals</p>
            <div class="trade-intent-stack">${observedHtml}</div>
        </section>
        <section class="trade-intent-section">
            <p class="label">Candidates</p>
            <div class="trade-intent-stack">${candidatesHtml}</div>
        </section>
        <section class="trade-intent-section">
            <p class="label">Blocked trades</p>
            <div class="trade-intent-stack">${blockedHtml}</div>
        </section>
        <section class="trade-intent-section">
            <p class="label">Paper lifecycle states</p>
            <ul class="status-list trade-state-list">${orderStateHtml}</ul>
        </section>
    `;
}

function renderCapital(status) {
    const target = dashboardQuery("[data-capital]");
    if (!target) return;
    const capital = status.capital || {};
    const maturityTarget = Number(capital.maturity_closed_trade_target || 100);
    const maturityCount = Number(capital.maturity_closed_trade_count || 0);
    const maturityPct = maturityTarget ? Math.round((maturityCount / maturityTarget) * 100) : 0;
    const safeMaturityPct = Number.isFinite(maturityPct) ? Math.min(100, Math.max(0, maturityPct)) : 0;
    const openPositions = asArray(capital.open_positions);
    const closedTrades = asArray(capital.closed_trades);
    const postmortemsDue = asArray(capital.postmortems_due);
    const postmortemsComplete = asArray(capital.postmortems_complete);
    const equityCurve = asArray(capital.equity_curve);

    const positionRows = openPositions.length
        ? openPositions.map((position) => `
            <li>
                <strong>${htmlText(position.instrument, "Open paper position")}</strong>
                <span>${htmlText(position.direction, "unknown")} · ${formatMoney(position.unrealized_pnl_gbp)} unrealized · ${htmlText(position.status, "open")}</span>
                <small>${htmlText(position.quantity, "0")} units · risk ${formatMoney(position.risk_size_gbp)} · ${htmlText(position.boundary, "Read-only paper position.")}</small>
            </li>
        `).join("")
        : `<li><strong>No open positions</strong><span>The paper mirror has no open positions.</span></li>`;

    const closedRows = closedTrades.length
        ? closedTrades.map((trade) => `
            <li>
                <strong>${htmlText(trade.instrument, "Closed paper trade")}</strong>
                <span>${formatMoney(trade.realized_pnl_gbp)} realized · ${htmlText(trade.postmortem_status, "postmortem state unknown")}</span>
                <small>${htmlText(trade.close_reason, "No close reason")} · ${htmlText(trade.boundary, "Read-only closed trade.")}</small>
            </li>
        `).join("")
        : `<li><strong>No closed trades</strong><span>The mature benchmark remains ${maturityCount}/${maturityTarget} closed proof trades.</span></li>`;

    const curveRows = equityCurve.length
        ? equityCurve.slice(-5).map((point) => `
            <li>
                <strong>${formatTime(point.observed_at)}</strong>
                <span>${formatMoney(point.equity_gbp)} equity · ${htmlText(point.drawdown_pct, "0")}% drawdown</span>
            </li>
        `).join("")
        : `<li><strong>No equity snapshots</strong><span>The mirror has not written an account snapshot yet.</span></li>`;

    target.innerHTML = `
        ${renderPanelBrief({
            id: "money",
            question: "Is the paper account proving or losing trust?",
            state: formatMoney(capital.current_balance_gbp),
            tone: capital.live_capital_enabled ? "blocked" : (Number(capital.drawdown_pct || 0) > 0 ? "degraded" : "online"),
            primary: `${formatMoney(capital.realized_pnl_gbp)} realized, ${formatMoney(capital.unrealized_pnl_gbp)} unrealized, ${formatPercent(capital.drawdown_pct)} drawdown, and ${maturityCount}/${maturityTarget} closed proof trades.`,
            secondary: "Open exposure, drawdown, stale paper-mirror timestamps, closed trades without postmortems, and progress toward the 100-trade maturity benchmark.",
            boundary: capital.boundary || "Read-only paper account mirror. No funding authority and no live broker-write authority."
        })}
        <div class="summary-strip">
            ${renderMetric("Starting", formatMoney(capital.starting_balance_gbp))}
            ${renderMetric("Current", formatMoney(capital.current_balance_gbp))}
            ${renderMetric("Cash", formatMoney(capital.cash_gbp))}
            ${renderMetric("Equity", formatMoney(capital.equity_gbp))}
            ${renderMetric("Realized", formatMoney(capital.realized_pnl_gbp))}
            ${renderMetric("Unrealized", formatMoney(capital.unrealized_pnl_gbp))}
            ${renderMetric("Drawdown", formatPercent(capital.drawdown_pct))}
            ${renderMetric("Closed trades", `${maturityCount}/${maturityTarget}`)}
        </div>
        <p class="empty-state">${htmlText(capital.boundary, "Read-only paper account mirror.")}</p>
        <div class="paper-account-meta">
            ${renderInlineBadge(`mirror ${capital.mirror_status || "unknown"}`, capital.mirror_status === "ok" ? "online" : "degraded")}
            ${renderInlineBadge(capital.account_scope, "online")}
            ${renderInlineBadge(capital.broker, "pending")}
            ${renderInlineBadge(capital.connection_status, capital.mirror_status === "ok" ? "online" : "pending")}
            ${renderInlineBadge(`${capital.write_authority ? "write enabled" : "read only"}`, capital.write_authority ? "blocked" : "online")}
            ${renderInlineBadge(`${capital.live_capital_enabled ? "live capital" : "paper only"}`, capital.live_capital_enabled ? "blocked" : "online")}
        </div>
        <section class="paper-account-section">
            <p class="label">Paper mirror state</p>
            <div class="summary-strip compact">
                ${renderMetric("Timeline", capital.timeline_status || "not initialized")}
                ${renderMetric("Observed", formatTime(capital.observed_at))}
                ${renderMetric("Peak equity", formatMoney(capital.peak_equity_gbp))}
                ${renderMetric("Max drawdown", formatPercent(capital.max_drawdown_pct))}
                ${renderMetric("Open positions", capital.open_position_count || openPositions.length)}
                ${renderMetric("Closed trades", capital.closed_trade_count || closedTrades.length)}
                ${renderMetric("Postmortems due", capital.postmortem_due_count || postmortemsDue.length)}
                ${renderMetric("Postmortems complete", capital.postmortem_complete_count || postmortemsComplete.length)}
            </div>
        </section>
        <section class="paper-account-section">
            <p class="label">Maturity benchmark</p>
            <div class="maturity-bar" aria-label="Closed trade maturity progress">
                <span style="width: ${safeMaturityPct}%"></span>
            </div>
            <p class="mini">${maturityCount} of ${maturityTarget} closed proof trades · ${capital.postmortem_complete_count || 0} postmortems complete · ${postmortemsDue.length} due.</p>
        </section>
        <section class="paper-account-section paper-account-grid">
            <div>
                <p class="label">Open positions</p>
                <ul class="status-list paper-list">${positionRows}</ul>
            </div>
            <div>
                <p class="label">Closed trades</p>
                <ul class="status-list paper-list">${closedRows}</ul>
            </div>
        </section>
        <section class="paper-account-section">
            <p class="label">Equity timeline</p>
            <ul class="status-list paper-list">${curveRows}</ul>
        </section>
    `;
}

function renderFundManagerNotes(status) {
    const commentsTarget = dashboardQuery("[data-comments-list]");
    const notes = status.fund_manager_notes || {};
    const comments = asArray(notes.recent_comments);
    replacePanelBrief("fund_manager_comments", {
        question: "What should the founding Fund Managers improve?",
        state: `${notes.comment_count || comments.length || 0} notes`,
        tone: notes.implemented_count ? "online" : "pending",
        primary: `${notes.suggestion_count || 0} suggestions, ${notes.accepted_count || 0} accepted, and ${notes.implemented_count || 0} implemented notes are mirrored for governance review.`,
        secondary: "Unlinked comments, accepted/rejected status, implemented suggestions, and notes that should become concrete implementation work.",
        boundary: notes.boundary || "Governance notes only. No trade approval, order placement, or local secret access."
    });

    const summary = dashboardQuery("[data-comments-summary]");
    if (summary) {
        summary.innerHTML = [
            renderMetric("Local notes", notes.comment_count || comments.length || 0),
            renderMetric("Suggestions", notes.suggestion_count || 0),
            renderMetric("Accepted", notes.accepted_count || 0),
            renderMetric("Implemented", notes.implemented_count || 0)
        ].join("");
    }

    setText(
        "[data-comments-boundary]",
        notes.boundary || "Governance notes only. No trade approval, order placement, or local secret access."
    );

    if (!commentsTarget) return;

    commentsTarget.innerHTML = comments.length
        ? comments.map((comment) => `
            <li>
                <strong>${htmlText(comment.target_type, "module")} · ${htmlText(comment.target_key, "general")}</strong>
                <span>${htmlText(comment.body, "No comment body.")}</span>
                <div class="comment-meta">
                    ${renderInlineBadge(comment.status || "suggestion", comment.status || "pending")}
                    ${renderInlineBadge(comment.visibility || notes.visibility || "founding_fund_managers", "online")}
                    ${renderInlineBadge(formatTime(comment.created_at), "pending")}
                </div>
                <small>${htmlText(comment.author_label, "founding_fund_manager")} · ${htmlText(asArray(comment.tags).join(", "), "no tags")}</small>
            </li>
        `).join("")
        : `
            <li>
                <strong>No local comments</strong>
                <span>The local governance mirror has no comments yet.</span>
                <small>${htmlText(notes.browser_write_scope, "comments_only")} · ${htmlText(notes.local_event_log_export, "accepted_or_implemented_only")}</small>
            </li>
        `;
}

function renderConsole(status) {
    const target = dashboardQuery("[data-process-console]");
    if (!target) return;
    const events = asArray(status.process_console);
    const latest = events[events.length - 1] || {};
    replacePanelBrief("process_console", {
        question: "What did Qadam last report about itself?",
        state: `${events.length} events`,
        tone: events.length ? "online" : "pending",
        primary: events.length
            ? `Latest event: ${dashboardText(latest.message, "runtime event")} at ${formatTime(latest.timestamp)}.`
            : "No process events are present in this snapshot yet.",
        secondary: "Stale timestamps, failed exports, fallback-only state, repeated degraded checks, and bridge source changes.",
        boundary: "Read-only event stream. It is not shell access and cannot run commands."
    });
    target.innerHTML = events.length
        ? events.map((event) => `
            <li>
                <time>${formatTime(event.timestamp)}</time>
                <span>${htmlText(event.message)}</span>
            </li>
        `).join("")
        : `<li><time>Now</time><span>No process events in the snapshot yet.</span></li>`;
}

async function renderQadamDashboardStatus(session) {
    const banner = dashboardQuery("[data-status-banner]");
    try {
        const { status, source } = await fetchDashboardStatus(session);
        renderSnapshotMeta(status, source);
        renderOperatingSummary(status, source);
        renderFundModel(status, source);
        renderFlowMap(status);
        renderWatching(status);
        renderCognition(status);
        renderWorldview(status);
        renderForbidden(status);
        renderCommunications(status);
        renderTrades(status);
        renderCapital(status);
        renderFundManagerNotes(status);
        renderConsole(status);
        if (document.documentElement) {
            document.documentElement.dataset.dashboardStatus = "rendered";
            document.documentElement.dataset.dashboardStatusSource = source.key;
        }
    } catch (error) {
        if (banner) {
            banner.classList.add("snapshot-error");
            banner.innerHTML = `
                <span>Status contract unavailable</span>
                <span>The dashboard shell is loaded, but neither /api/cockpit-status nor /status/cockpit-status.json could be read.</span>
            `;
        }
        if (document.documentElement) {
            document.documentElement.dataset.dashboardStatus = "snapshot-error";
            document.documentElement.dataset.dashboardStatusSource = "unavailable";
        }
        console.error("Qadam dashboard status load failed", error);
    }
}

initDashboardDensityToggle();
window.setDashboardDensity = setDashboardDensity;
window.renderQadamDashboardStatus = renderQadamDashboardStatus;
