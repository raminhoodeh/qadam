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
    staged_order_contract: {
        role: "Paper gate",
        input: "Execution-policy reviews",
        output: "Disabled staging checks",
        authority: "No orders"
    },
    broker_reconciliation: {
        role: "Broker gate",
        input: "Staged-order reviews",
        output: "Broker echo checks",
        authority: "Read-only; no submit"
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
            ...(findModule(status, "signal_integrity_gate") || {
                key: "signal_integrity_gate",
                label: "Signal Integrity Gate",
                owner: "Signal Auditor",
                status: "pending",
                current_process: "Auditing shadow signals without trade authority",
                authority: "non_executable"
            }),
            handoff: "block or hold"
        },
        {
            ...(findModule(status, "risk_agent") || {
                key: "risk_agent",
                label: "Risk Agent",
                owner: "Policy Router",
                status: "pending",
                current_process: "Reviewing policy without order authority",
                authority: "read_only_policy_router"
            }),
            handoff: "policy hold"
        },
        {
            ...(findModule(status, "execution_policy") || {
                key: "execution_policy",
                label: "Execution Policy",
                owner: "Kill Switches",
                status: "blocked",
                current_process: "Kill switches and staged orders are read-only",
                authority: "read_only_execution_policy"
            }),
            handoff: "kill-switch hold"
        },
        {
            ...(findModule(status, "staged_order_contract") || {
                key: "staged_order_contract",
                label: "Staged Order Contract",
                owner: "Paper Order Gate",
                status: "blocked",
                current_process: "Disabled paper-order staging checks",
                authority: "disabled_staged_order_contract"
            }),
            handoff: "staging blocked"
        },
        {
            ...(findModule(status, "broker_reconciliation") || {
                key: "broker_reconciliation",
                label: "Broker Reconciliation",
                owner: "Paper Order Gate",
                status: "blocked",
                current_process: "Read-only broker echo and reconciliation checks",
                authority: "read_only_broker_reconciliation"
            }),
            handoff: "submit blocked"
        },
        {
            ...(findModule(status, "paper_submit_receipt") || {
                key: "paper_submit_receipt",
                label: "Paper Submit Receipt",
                owner: "Paper Order Gate",
                status: "blocked",
                current_process: "Dry-run receipt checks without broker POST",
                authority: "dry_run_receipt_only"
            }),
            handoff: "dry-run receipt only"
        },
        {
            ...(findModule(status, "execution_registry") || {
                key: "execution_registry",
                label: "Execution Registry",
                owner: "Risk Agent",
                status: "blocked",
                current_process: "Broker writes and live capital blocked",
                authority: "fail_closed"
            }),
            handoff: "broker route blocked"
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
            ["worldview", "research_analyst", "strategy_lead", "shadow_intelligence", "signal_integrity_gate"]
        ),
        makeLane(
            "Quant + Risk",
            "Bounded modelling can inform a gate; risk decides whether an idea may continue.",
            "Only passed gates can become paper-trial state.",
            "blocked",
            ["head_of_quant", "risk_agent", "execution_policy", "staged_order_contract", "broker_reconciliation", "paper_submit_receipt", "execution_registry"]
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

function compactItems(items, limit = 5) {
    const list = asArray(items).filter(Boolean);
    const visible = list.slice(0, limit);
    const overflow = list.length - visible.length;
    return overflow > 0 ? [...visible, `+${overflow} more`] : visible;
}

function renderMissionTags(items, emptyText = "None recorded", limit = 5) {
    return renderTagList(compactItems(items, limit), emptyText);
}

function fallbackMissionControl(status, source) {
    const watching = asArray(status.watching);
    const sourceCounts = countBy(watching, "status");
    const pipelineSummary = asArray(status.source_pipeline_summary);
    const configuredSources = watching
        .filter((item) => item.credential_status === "configured")
        .map((item) => item.source_name || item.source_key);
    const connectedSources = Array.from(new Set([
        ...configuredSources,
        ...watching.filter((item) => item.status === "online").map((item) => item.source_name || item.source_key)
    ]));
    const missingCredentialCount = pipelineSummary.reduce(
        (total, pipeline) => total + Number(pipeline.missing_credential_count || 0),
        0
    );
    const cognition = status.cognition || {};
    const tradeLayer = status.trade_layer || {};
    const capital = status.capital || {};
    const philosophy = status.decision_philosophy || {};
    const candidates = asArray(tradeLayer.candidates);
    const observedSignals = asArray(tradeLayer.watching);
    const blockedTrades = asArray(tradeLayer.blocked);
    const openPositions = asArray(capital.open_positions);
    const totalPnl = Number(capital.realized_pnl_gbp || 0) + Number(capital.unrealized_pnl_gbp || 0);
    return {
        status: "read_only_mission_control",
        source: source?.key || "dashboard_fallback",
        headline: `${sourceCounts.online || 0}/${watching.length} sources online; ${asArray(cognition.hypotheses).length} hypotheses; ${candidates.length} candidates; ${openPositions.length} open positions; live capital ${capital.live_capital_enabled ? "enabled" : "disabled"}.`,
        data_sources: {
            total_count: watching.length,
            online_count: sourceCounts.online || 0,
            degraded_count: sourceCounts.degraded || 0,
            pending_count: sourceCounts.pending || 0,
            missing_credential_count: missingCredentialCount,
            logged_in_count: configuredSources.length,
            logged_in_sources: configuredSources,
            connected_sources: connectedSources,
            boundary: "Configured and connected sources are observation inputs only; they cannot create orders."
        },
        trading_philosophy: {
            status: philosophy.status || "pending",
            summary: philosophy.trading_philosophy || "Qadam generates hypotheses from private priors, but live evidence and gates decide what can advance.",
            decision_chain: philosophy.decision_chain || [],
            private_prior_count: philosophy.foundational_prior_count || 0,
            current_self_directive: [
                "Use worldview as private prior.",
                "Require live-source corroboration.",
                "Compress source noise locally.",
                "Challenge with Strategy Lead.",
                "Keep paper orders blocked until gates pass."
            ],
            boundary: philosophy.boundary || "Worldview is context only, not evidence."
        },
        system_stack: {
            coo: findModule(status, "event_log")?.status || "local_only",
            data_spine: watching.length ? "online" : "pending",
            local_llm: findModule(status, "research_analyst")?.status || "pending",
            frontier_llm: findModule(status, "strategy_lead")?.status || "pending",
            quant_oracle: findModule(status, "head_of_quant")?.status || "deferred",
            risk_gate: status.risk_agent?.status || "pending",
            paper_account: capital.mirror_status || "pending",
            telegram: status.communications?.telegram?.status || "pending",
            boundary: "APIs, models, and quantum checks can inform the chain; only gates can advance state."
        },
        thinking: {
            status: cognition.status || "pending",
            current_focus: cognition.current_focus || [],
            hypothesis_count: asArray(cognition.hypotheses).length,
            evidence_packet_count: asArray(cognition.evidence_packets).length,
            local_assessment_count: asArray(cognition.local_research_assessments).length,
            strategy_packet_count: asArray(cognition.strategy_lead_packets).length,
            signal_integrity_status: cognition.signal_integrity?.status || "pending",
            blocked_reasons: cognition.blocked_reasons || [],
            boundary: cognition.boundary || "Cognition is shadow-only and cannot execute trades."
        },
        trade_intent: {
            state: candidates.length ? "candidate_review" : (observedSignals.length ? "observed_signal_review" : "no_trade_candidate"),
            summary: candidates.length
                ? `${candidates.length} candidate ideas are waiting behind risk and execution gates.`
                : (observedSignals.length ? `${observedSignals.length} observed signals are being watched, but none are orders.` : "No executable trade candidate exists in the current public-safe snapshot."),
            observed_signal_count: observedSignals.length,
            candidate_count: candidates.length,
            blocked_count: blockedTrades.length,
            top_candidates: candidates.slice(0, 5),
            blocked_trades: blockedTrades.slice(0, 5),
            execution_allowed_count: 0,
            paper_order_submitted_count: status.paper_submit_receipt?.paper_order_submitted_count || 0,
            broker_post_called_count: status.paper_submit_receipt?.broker_post_called_count || 0,
            boundary: tradeLayer.boundary || "Candidate is not order; no broker route exists."
        },
        portfolio: {
            account_scope: capital.account_scope || "first_release_gbp_1000_trial",
            broker: capital.broker || "paper_broker",
            connection_status: capital.connection_status || "pending",
            current_balance_gbp: capital.current_balance_gbp || capital.starting_balance_gbp || 0,
            total_pnl_gbp: totalPnl,
            drawdown_pct: capital.drawdown_pct || 0,
            open_position_count: openPositions.length,
            order_count: asArray(capital.orders).length,
            closed_trade_count: asArray(capital.closed_trades).length,
            live_capital_enabled: Boolean(capital.live_capital_enabled),
            write_authority: Boolean(capital.write_authority),
            open_positions: openPositions,
            orders: asArray(capital.orders),
            boundary: capital.boundary || "Read-only paper account mirror."
        },
        safety: {
            live_capital_enabled: Boolean(capital.live_capital_enabled),
            broker_write_allowed: false,
            forbidden_action_count: asArray(status.forbidden_actions).length,
            hard_blocks: asArray(status.forbidden_actions).map((item) => item.action || item.key || "blocked action"),
            boundary: "Mission control is read-only. It cannot approve, place, modify, resize, close, or fund trades."
        }
    };
}

function renderMissionControl(status, source) {
    const mission = status.mission_control || fallbackMissionControl(status, source);
    const dataSources = mission.data_sources || {};
    const philosophy = mission.trading_philosophy || {};
    const stack = mission.system_stack || {};
    const thinking = mission.thinking || {};
    const tradeIntent = mission.trade_intent || {};
    const portfolio = mission.portfolio || {};
    const safety = mission.safety || {};

    const primary = dashboardQuery("[data-mission-primary]");
    if (primary) {
        primary.innerHTML = `
            <span>Operating thesis</span>
            <h3>${htmlText(mission.headline, "Mission state unavailable")}</h3>
            <p>${htmlText(philosophy.summary, "Qadam is waiting for its trading philosophy snapshot.")}</p>
            <div class="mission-mini-grid">
                ${renderMetric("Thinking", `${thinking.hypothesis_count || 0} hypotheses`)}
                ${renderMetric("Intent", `${tradeIntent.candidate_count || 0} candidates`)}
                ${renderMetric("Holdings", `${portfolio.open_position_count || 0} open`)}
                ${renderMetric("Safety", safety.live_capital_enabled ? "live enabled" : "live disabled")}
            </div>
            <p class="mini">${htmlText(safety.boundary, "Mission control is read-only.")}</p>
        `;
    }

    const sources = dashboardQuery("[data-mission-sources]");
    if (sources) {
        sources.innerHTML = `
            <span>Data sources</span>
            <h3>${htmlText(dataSources.logged_in_count || 0)} logged-in/configured · ${htmlText(dataSources.online_count || 0)}/${htmlText(dataSources.total_count || 0)} online</h3>
            <p>${htmlText(dataSources.degraded_count || 0)} degraded · ${htmlText(dataSources.pending_count || 0)} pending · ${htmlText(dataSources.missing_credential_count || 0)} missing credentials</p>
            <div class="mission-tag-row">${renderMissionTags(dataSources.logged_in_sources || dataSources.connected_sources, "No configured sources visible yet", 8)}</div>
            <small>${htmlText(dataSources.boundary, "Sources are observation only.")}</small>
        `;
    }

    const philosophyTarget = dashboardQuery("[data-mission-philosophy]");
    if (philosophyTarget) {
        philosophyTarget.innerHTML = `
            <span>Trading philosophy</span>
            <h3>${htmlText(philosophy.private_prior_count || 0)} private priors · ${htmlText(philosophy.status, "pending")}</h3>
            <p>${htmlText(asArray(philosophy.current_self_directive)[0], "Use worldview as a question generator, not proof.")}</p>
            <div class="mission-tag-row">${renderMissionTags(philosophy.decision_chain, "Decision chain not exported", 7)}</div>
            <small>${htmlText(philosophy.boundary, "Worldview is context only, not evidence.")}</small>
        `;
    }

    const stackTarget = dashboardQuery("[data-mission-stack]");
    if (stackTarget) {
        stackTarget.innerHTML = `
            <span>System stack</span>
            <h3>COO ${htmlText(stack.coo)} · Local LLM ${htmlText(stack.local_llm)}</h3>
            <p>Frontier LLM ${htmlText(stack.frontier_llm)} · quantum oracle ${htmlText(stack.quant_oracle)} · risk ${htmlText(stack.risk_gate)}</p>
            <div class="mission-tag-row">
                ${renderInlineBadge(`data ${dashboardText(stack.data_spine)}`, stack.data_spine)}
                ${renderInlineBadge(`paper ${dashboardText(stack.paper_account)}`, stack.paper_account)}
                ${renderInlineBadge(`telegram ${dashboardText(stack.telegram)}`, stack.telegram)}
            </div>
            <small>${htmlText(stack.boundary, "Only gates can advance state.")}</small>
        `;
    }

    const trades = dashboardQuery("[data-mission-trades]");
    if (trades) {
        const candidateNames = asArray(tradeIntent.top_candidates).map((item) => {
            const direction = item.direction ? ` ${item.direction}` : "";
            return `${item.instrument || "candidate"}${direction}`;
        });
        const blockedNames = asArray(tradeIntent.blocked_trades).map((item) => `${item.instrument || "blocked idea"}: ${item.blocked_reason || item.status || "blocked"}`);
        trades.innerHTML = `
            <span>Trade intent</span>
            <h3>${htmlText(tradeIntent.state, "no trade candidate")}</h3>
            <p>${htmlText(tradeIntent.summary, "No executable trade candidate exists.")}</p>
            <div class="mission-mini-grid compact">
                ${renderMetric("Observed", tradeIntent.observed_signal_count || 0)}
                ${renderMetric("Candidates", tradeIntent.candidate_count || 0)}
                ${renderMetric("Blocked", tradeIntent.blocked_count || 0)}
                ${renderMetric("Submitted", tradeIntent.paper_order_submitted_count || 0)}
            </div>
            <div class="mission-tag-row">${renderMissionTags(candidateNames.length ? candidateNames : blockedNames, "No candidate or blocked trade visible yet", 4)}</div>
            <small>${htmlText(tradeIntent.boundary, "Candidate is not order.")}</small>
        `;
    }

    const portfolioTarget = dashboardQuery("[data-mission-portfolio]");
    if (portfolioTarget) {
        const openPositionNames = asArray(portfolio.open_positions).map((position) => {
            const pnl = position.unrealized_pnl_gbp === undefined ? "" : ` ${formatMoney(position.unrealized_pnl_gbp)}`;
            return `${position.instrument || "position"}${pnl}`;
        });
        const orderNames = asArray(portfolio.orders).map((order) => `${order.instrument || "order"} ${order.status || "mirrored"}`);
        portfolioTarget.innerHTML = `
            <span>Paper account</span>
            <h3>${formatMoney(portfolio.current_balance_gbp)} · ${formatMoney(portfolio.total_pnl_gbp)} P&L</h3>
            <p>${htmlText(portfolio.connection_status, "pending")} · ${htmlText(portfolio.account_scope, "first release trial")} · drawdown ${formatPercent(portfolio.drawdown_pct)}</p>
            <div class="mission-mini-grid compact">
                ${renderMetric("Open", portfolio.open_position_count || 0)}
                ${renderMetric("Orders", portfolio.order_count || 0)}
                ${renderMetric("Closed", portfolio.closed_trade_count || 0)}
                ${renderMetric("Write", portfolio.write_authority ? "enabled" : "blocked")}
            </div>
            <div class="mission-tag-row">${renderMissionTags(openPositionNames.length ? openPositionNames : orderNames, "No open positions or mirrored orders", 4)}</div>
            <small>${htmlText(portfolio.boundary, "Read-only paper account mirror.")}</small>
        `;
    }
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
    const accountContext = cognition.paper_account_context || {};
    const signalIntegrity = cognition.signal_integrity || {};
    const signalReviews = asArray(cognition.signal_integrity_reviews);
    const philosophy = status.decision_philosophy || {};
    const evidenceBySignal = evidencePackets.reduce((acc, packet) => {
        if (packet.signal_id) acc[packet.signal_id] = packet;
        return acc;
    }, {});
    const evidenceItemCount = sumNestedItems(evidencePackets, "items");
    const executableHypotheses = hypotheses.filter((hypothesis) => hypothesis.execution_allowed);
    const latestAssessment = localResearch[localResearch.length - 1] || {};
    const accountPositions = asArray(accountContext.position_summaries);
    const accountOrders = asArray(accountContext.order_summaries);
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
                        ${renderMetric("Integrity", htmlText(hypothesis.integrity_review_status, "not reviewed"))}
                        ${renderMetric("Score", dashboardText(hypothesis.integrity_score, "n/a"))}
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

    const paperContextHtml = `
        <article class="cognition-card paper-context-card">
            <div class="cognition-card-head">
                ${renderStatusPill(accountContext.status || "pending")}
                <p class="label">${htmlText(accountContext.connection_status, "paper mirror")}</p>
            </div>
            <h3>Paper account context</h3>
            <p>${htmlText(accountContext.capital_policy, "The first-release policy allocation is GBP 1000; paper broker balance is context only.")}</p>
            <div class="summary-strip compact">
                ${renderMetric("Trial policy", formatMoney(accountContext.trial_allocation_gbp))}
                ${renderMetric("Broker mirror", formatMoney(accountContext.current_balance_gbp))}
                ${renderMetric("Open positions", accountContext.open_position_count || 0)}
                ${renderMetric("Orders", accountContext.order_count || 0)}
                ${renderMetric("Drawdown", formatPercent(accountContext.drawdown_pct))}
                ${renderMetric("Execution", accountContext.execution_allowed ? "Allowed" : "Blocked")}
            </div>
            <div class="tag-row">
                ${renderInlineBadge(accountContext.write_authority ? "write enabled" : "read only", accountContext.write_authority ? "blocked" : "online")}
                ${renderInlineBadge(accountContext.paper_order_allowed ? "paper order allowed" : "no paper order authority", accountContext.paper_order_allowed ? "blocked" : "online")}
                ${renderInlineBadge(accountContext.live_capital_enabled ? "live capital" : "live capital disabled", accountContext.live_capital_enabled ? "blocked" : "online")}
                ${renderInlineBadge(`${accountContext.maturity_closed_trade_count || 0}/${accountContext.maturity_closed_trade_target || 100} proof trades`, "pending")}
            </div>
            <dl class="cognition-facts">
                <div>
                    <dt>Exposure</dt>
                    <dd>${accountPositions.length ? accountPositions.map((position) => `${htmlText(position.instrument, "instrument")} ${htmlText(position.direction, "direction")} ${htmlText(position.quantity, "0")}`).join(", ") : "No open exposure mirrored."}</dd>
                </div>
                <div>
                    <dt>Orders</dt>
                    <dd>${accountOrders.length ? accountOrders.map((order) => `${htmlText(order.instrument, "instrument")} ${htmlText(order.direction, "direction")} ${htmlText(order.status, "status")}`).join(", ") : "No mirrored paper orders."}</dd>
                </div>
                <div>
                    <dt>Boundary</dt>
                    <dd>${htmlText(accountContext.boundary, "Read-only paper account context. No order authority.")}</dd>
                </div>
            </dl>
        </article>
    `;

    const signalIntegrityHtml = signalReviews.length
        ? signalReviews.slice(-5).reverse().map((review) => `
            <article class="cognition-card signal-integrity-card">
                <div class="cognition-card-head">
                    ${renderStatusPill(review.status || "hold_for_corroboration")}
                    <p class="label">${htmlText(review.instrument_focus, "signal focus")}</p>
                </div>
                <h3>Signal Integrity Review</h3>
                <p>${htmlText(review.boundary, "Signal Integrity Gate is non-executable.")}</p>
                <div class="summary-strip compact">
                    ${renderMetric("Score", dashboardText(review.integrity_score, "n/a"))}
                    ${renderMetric("Sources", review.source_count || 0)}
                    ${renderMetric("Evidence", review.evidence_item_count || 0)}
                    ${renderMetric("Avg trust", dashboardText(review.average_trust_score, "n/a"))}
                    ${renderMetric("Min trust", dashboardText(review.min_trust_score, "n/a"))}
                    ${renderMetric("Trade created", review.trade_candidate_created ? "Yes" : "No")}
                </div>
                <section class="trade-check-section">
                    <p class="label">Akber filter</p>
                    <div class="tag-row">${renderTagList(Object.entries(review.akber_filter || {}).map(([key, value]) => `${key}: ${value}`), "No Akber stage output")}</div>
                </section>
                <section class="trade-check-section">
                    <p class="label">Failure reasons</p>
                    <div class="tag-row">${renderTagList(review.failure_reasons, "No failure reasons recorded")}</div>
                </section>
                <section class="trade-check-section">
                    <p class="label">Required next steps</p>
                    <div class="tag-row">${renderTagList(review.required_next_steps, "No next steps recorded")}</div>
                </section>
                <p class="mini">${htmlText(review.worldview_prior_status, "private prior only")} · ${formatTime(review.reviewed_at)}</p>
            </article>
        `).join("")
        : `<article class="cognition-card signal-integrity-card"><h3>No Signal Integrity reviews yet</h3><p>Shadow signals have not been audited by the Signal Auditor.</p></article>`;

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
                ${renderMetric("Integrity reviews", signalReviews.length)}
                ${renderMetric("Models", activity.length)}
                ${renderMetric("Execution", executableHypotheses.length ? "Unexpected allowed" : "Blocked")}
            </div>
            <div class="tag-row">
                ${renderInlineBadge("Hypothesis, not trade", "blocked")}
                ${renderInlineBadge("Trade layer not reached", "blocked")}
                ${renderInlineBadge(`Signal Integrity ${signalIntegrity.status || "pending"}`, signalIntegrity.status === "ok" ? "online" : "pending")}
                ${renderInlineBadge(`latest local assessment ${formatTime(latestAssessment.created_at)}`, latestAssessment.created_at ? "online" : "pending")}
            </div>
        </section>
        <section class="cognition-section">
            <p class="label">Current focus</p>
            <div class="focus-box">${renderTagList(focus, "No active focus")}</div>
        </section>
        <section class="cognition-section">
            <p class="label">Paper account context</p>
            <div class="hypothesis-stack">${paperContextHtml}</div>
        </section>
        <section class="cognition-section">
            <p class="label">Signal Integrity Gate</p>
            <div class="summary-strip compact">
                ${renderMetric("Total reviews", signalIntegrity.review_count || 0)}
                ${renderMetric("Held", (signalIntegrity.by_status || {}).hold_for_corroboration || 0)}
                ${renderMetric("Blocked", (signalIntegrity.by_status || {}).blocked || 0)}
                ${renderMetric("Risk shadow", (signalIntegrity.by_status || {}).passed_to_risk_shadow || 0)}
                ${renderMetric("Candidates created", signalIntegrity.trade_candidate_created_count || 0)}
                ${renderMetric("Execution", signalIntegrity.execution_allowed_count ? "Unexpected allowed" : "Blocked")}
            </div>
            <div class="hypothesis-stack">${signalIntegrityHtml}</div>
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
    const riskAgent = tradeLayer.risk_agent || status.risk_agent || {};
    const riskReviews = asArray(riskAgent.reviews);
    const executionPolicy = tradeLayer.execution_policy || status.execution_policy || {};
    const executionPolicyReviews = asArray(executionPolicy.reviews);
    const stagedPaperOrder = tradeLayer.staged_paper_order || status.staged_paper_order || {};
    const stagedPaperOrderReviews = asArray(stagedPaperOrder.reviews);
    const brokerReconciliation = tradeLayer.broker_reconciliation || status.broker_reconciliation || {};
    const brokerReconciliationReviews = asArray(brokerReconciliation.reviews);
    const paperSubmitReceipt = tradeLayer.paper_submit_receipt || status.paper_submit_receipt || {};
    const paperSubmitReceiptReviews = asArray(paperSubmitReceipt.reviews);
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

    const renderRiskReviewCard = (review) => {
        const checkTags = Object.entries(review.checks || {}).map(([key, value]) => `${key}: ${value}`);
        return `
            <article class="trade-intent-card ${statusClass(review.status || "policy_hold")}">
                <div class="cognition-card-head">
                    ${renderStatusPill(review.status || "policy_hold")}
                    <p class="label">${htmlText(review.source_type, "risk review")} · ${htmlText(review.source_ref, "source pending")}</p>
                </div>
                <h3>${htmlText(review.instrument, "Risk policy review")}</h3>
                <p>${htmlText(review.boundary, "Risk Agent review is read-only.")}</p>
                <div class="tag-row">
                    ${renderInlineBadge(review.execution_allowed ? "execution allowed" : "execution blocked", review.execution_allowed ? "blocked" : "online")}
                    ${renderInlineBadge(review.paper_order_allowed ? "paper order allowed" : "no paper order", review.paper_order_allowed ? "blocked" : "online")}
                    ${renderInlineBadge(review.order_created ? "order created" : "no order created", review.order_created ? "blocked" : "online")}
                    ${renderInlineBadge(review.broker_write_allowed ? "broker write allowed" : "broker write blocked", review.broker_write_allowed ? "blocked" : "online")}
                </div>
                <div class="summary-strip compact">
                    ${renderMetric("Policy score", formatProbability(review.policy_score))}
                    ${renderMetric("Risk asked", `${formatMoney(review.proposed_risk_gbp)} / ${htmlText(review.proposed_risk_pct, "0")}%`)}
                    ${renderMetric("Max risk", `${formatMoney(review.max_risk_gbp)} / ${htmlText(review.max_risk_pct, "1")}%`)}
                    ${renderMetric("Signal", htmlText(review.signal_integrity_status, "not reviewed"))}
                    ${renderMetric("Account", htmlText(review.paper_account_status, "unknown"))}
                    ${renderMetric("Reviewed", formatTime(review.reviewed_at))}
                </div>
                <section class="trade-check-section">
                    <p class="label">Risk checks</p>
                    <div class="tag-row">${renderTagList(checkTags, "No risk checks recorded")}</div>
                </section>
                <section class="trade-check-section">
                    <p class="label">Blocked reasons</p>
                    <div class="tag-row">${renderTagList(review.blocked_reasons, "No blocking reason recorded")}</div>
                </section>
                <section class="trade-check-section">
                    <p class="label">Required next steps</p>
                    <ul class="status-list">${asArray(review.required_next_steps).length
                        ? asArray(review.required_next_steps).map((step) => `<li><strong>${htmlText(step)}</strong></li>`).join("")
                        : "<li><strong>No next steps recorded</strong></li>"
                    }</ul>
                </section>
            </article>
        `;
    };

    const renderExecutionPolicyCard = (review) => {
        const checkTags = Object.entries(review.checks || {}).map(([key, value]) => `${key}: ${value}`);
        const killSwitchTags = Object.entries(review.kill_switches || {}).map(([key, value]) => `${key}: ${value}`);
        return `
            <article class="trade-intent-card ${statusClass(review.status || "blocked_by_policy")}">
                <div class="cognition-card-head">
                    ${renderStatusPill(review.status || "blocked_by_policy")}
                    <p class="label">Execution Policy · ${htmlText(review.source_risk_review_id, "risk review pending")}</p>
                </div>
                <h3>${htmlText(review.instrument, "Execution policy review")}</h3>
                <p>${htmlText(review.boundary, "Execution policy is read-only.")}</p>
                <div class="tag-row">
                    ${renderInlineBadge(review.execution_allowed ? "execution allowed" : "execution blocked", review.execution_allowed ? "blocked" : "online")}
                    ${renderInlineBadge(review.staged_paper_order_allowed ? "staged order allowed" : "no staged paper order", review.staged_paper_order_allowed ? "blocked" : "online")}
                    ${renderInlineBadge(review.paper_order_created ? "paper order created" : "no paper order created", review.paper_order_created ? "blocked" : "online")}
                    ${renderInlineBadge(review.broker_write_allowed ? "broker write allowed" : "broker write blocked", review.broker_write_allowed ? "blocked" : "online")}
                    ${renderInlineBadge(review.live_capital_enabled ? "live capital enabled" : "live capital disabled", review.live_capital_enabled ? "blocked" : "online")}
                </div>
                <div class="summary-strip compact">
                    ${renderMetric("Policy score", formatProbability(review.policy_score))}
                    ${renderMetric("Venue", htmlText(review.selected_venue, "none"))}
                    ${renderMetric("Venue mode", htmlText(review.venue_mode, "disabled"))}
                    ${renderMetric("Reviewed", formatTime(review.reviewed_at))}
                </div>
                <section class="trade-check-section">
                    <p class="label">Kill switches</p>
                    <div class="tag-row">${renderTagList(killSwitchTags, "No kill switches recorded")}</div>
                </section>
                <section class="trade-check-section">
                    <p class="label">Execution checks</p>
                    <div class="tag-row">${renderTagList(checkTags, "No execution checks recorded")}</div>
                </section>
                <section class="trade-check-section">
                    <p class="label">Blocked reasons</p>
                    <div class="tag-row">${renderTagList(review.blocked_reasons, "No blocking reason recorded")}</div>
                </section>
                <section class="trade-check-section">
                    <p class="label">Required next steps</p>
                    <ul class="status-list">${asArray(review.required_next_steps).length
                        ? asArray(review.required_next_steps).map((step) => `<li><strong>${htmlText(step)}</strong></li>`).join("")
                        : "<li><strong>No next steps recorded</strong></li>"
                    }</ul>
                </section>
            </article>
        `;
    };

    const renderStagedPaperOrderCard = (review) => {
        const checkTags = Object.entries(review.reconciliation_checks || {}).map(([key, value]) => `${key}: ${value}`);
        const hypothetical = review.hypothetical_order || {};
        return `
            <article class="trade-intent-card ${statusClass(review.status || "blocked_before_staging")}">
                <div class="cognition-card-head">
                    ${renderStatusPill(review.status || "blocked_before_staging")}
                    <p class="label">Staged paper-order contract · ${htmlText(review.source_execution_policy_review_id, "execution review pending")}</p>
                </div>
                <h3>${htmlText(review.instrument, "Staged paper-order review")}</h3>
                <p>${htmlText(review.boundary, "Staged paper-order contract is disabled.")}</p>
                <div class="tag-row">
                    ${renderInlineBadge(review.execution_allowed ? "execution allowed" : "execution blocked", review.execution_allowed ? "blocked" : "online")}
                    ${renderInlineBadge(review.staged_paper_order_created ? "staged order created" : "no staged order created", review.staged_paper_order_created ? "blocked" : "online")}
                    ${renderInlineBadge(review.paper_order_submittable ? "paper order submittable" : "paper order not submittable", review.paper_order_submittable ? "blocked" : "online")}
                    ${renderInlineBadge(review.broker_write_allowed ? "broker write allowed" : "broker write blocked", review.broker_write_allowed ? "blocked" : "online")}
                    ${renderInlineBadge(review.live_capital_enabled ? "live capital enabled" : "live capital disabled", review.live_capital_enabled ? "blocked" : "online")}
                </div>
                <div class="summary-strip compact">
                    ${renderMetric("Venue", htmlText(review.selected_venue, "none"))}
                    ${renderMetric("Venue mode", htmlText(review.venue_mode, "disabled"))}
                    ${renderMetric("Account", htmlText(review.account_scope, "trial"))}
                    ${renderMetric("Hypothetical", htmlText(hypothetical.status, "not created"))}
                    ${renderMetric("Notional", formatMoney(hypothetical.notional_gbp))}
                    ${renderMetric("Reviewed", formatTime(review.reviewed_at))}
                </div>
                <section class="trade-check-section">
                    <p class="label">Hypothetical order</p>
                    <div class="tag-row">
                        ${renderInlineBadge(`direction: ${dashboardText(hypothetical.direction, "not determined")}`, "pending")}
                        ${renderInlineBadge(`type: ${dashboardText(hypothetical.order_type, "not applicable")}`, "pending")}
                        ${renderInlineBadge(`idempotency: ${dashboardText(hypothetical.idempotency_key, "not allocated")}`, "blocked")}
                        ${renderInlineBadge(`event log: ${dashboardText(hypothetical.event_log_ref, "not written")}`, "blocked")}
                    </div>
                </section>
                <section class="trade-check-section">
                    <p class="label">Reconciliation checks</p>
                    <div class="tag-row">${renderTagList(checkTags, "No reconciliation checks recorded")}</div>
                </section>
                <section class="trade-check-section">
                    <p class="label">Blocked reasons</p>
                    <div class="tag-row">${renderTagList(review.blocked_reasons, "No blocking reason recorded")}</div>
                </section>
                <section class="trade-check-section">
                    <p class="label">Required next steps</p>
                    <ul class="status-list">${asArray(review.required_next_steps).length
                        ? asArray(review.required_next_steps).map((step) => `<li><strong>${htmlText(step)}</strong></li>`).join("")
                        : "<li><strong>No next steps recorded</strong></li>"
                    }</ul>
                </section>
            </article>
        `;
    };

    const renderBrokerReconciliationCard = (review) => {
        const checkTags = Object.entries(review.reconciliation_checks || {}).map(([key, value]) => `${key}: ${value}`);
        const brokerEcho = review.broker_echo || {};
        const hypothetical = review.hypothetical_order || {};
        return `
            <article class="trade-intent-card ${statusClass(review.status || "blocked_before_broker_reconciliation")}">
                <div class="cognition-card-head">
                    ${renderStatusPill(review.status || "blocked_before_broker_reconciliation")}
                    <p class="label">Broker reconciliation contract · ${htmlText(review.source_staged_paper_order_review_id, "staged review pending")}</p>
                </div>
                <h3>${htmlText(review.instrument, "Broker reconciliation review")}</h3>
                <p>${htmlText(review.boundary, "Broker reconciliation is read-only and cannot submit paper orders.")}</p>
                <div class="tag-row">
                    ${renderInlineBadge(review.idempotency_key_allocated ? "idempotency allocated" : "idempotency not allocated", review.idempotency_key_allocated ? "blocked" : "online")}
                    ${renderInlineBadge(review.event_log_prewrite_created ? "Event Log prewrite created" : "Event Log prewrite not created", review.event_log_prewrite_created ? "blocked" : "online")}
                    ${renderInlineBadge(review.duplicate_order_guard_ready ? "duplicate guard ready" : "duplicate guard not ready", review.duplicate_order_guard_ready ? "blocked" : "online")}
                    ${renderInlineBadge(review.broker_echo_verified ? "broker echo verified" : "broker echo not verified", review.broker_echo_verified ? "blocked" : "online")}
                    ${renderInlineBadge(review.paper_order_submit_allowed ? "paper submit allowed" : "paper submit blocked", review.paper_order_submit_allowed ? "blocked" : "online")}
                    ${renderInlineBadge(review.broker_write_allowed ? "broker write allowed" : "broker write blocked", review.broker_write_allowed ? "blocked" : "online")}
                    ${renderInlineBadge(review.live_capital_enabled ? "live capital enabled" : "live capital disabled", review.live_capital_enabled ? "blocked" : "online")}
                </div>
                <div class="summary-strip compact">
                    ${renderMetric("Venue", htmlText(review.selected_venue, "none"))}
                    ${renderMetric("Mode", htmlText(review.venue_mode, "disabled"))}
                    ${renderMetric("Account", htmlText(review.account_scope, "trial"))}
                    ${renderMetric("Hypothetical", htmlText(hypothetical.status, "not created"))}
                    ${renderMetric("Broker echo", htmlText(brokerEcho.status, "not requested"))}
                    ${renderMetric("Reviewed", formatTime(review.reviewed_at))}
                </div>
                <section class="trade-check-section">
                    <p class="label">Broker echo</p>
                    <div class="tag-row">
                        ${renderInlineBadge(`adapter: ${dashboardText(brokerEcho.adapter, "not selected")}`, "pending")}
                        ${renderInlineBadge(`venue: ${dashboardText(brokerEcho.venue, "none")}`, "pending")}
                        ${renderInlineBadge(`client id: ${dashboardText(brokerEcho.client_order_id, "not allocated")}`, "blocked")}
                        ${renderInlineBadge(`external id: ${dashboardText(brokerEcho.external_order_id, "not created")}`, "blocked")}
                        ${renderInlineBadge(`ack: ${dashboardText(brokerEcho.ack_status, "not available")}`, "blocked")}
                        ${renderInlineBadge(`fill: ${dashboardText(brokerEcho.fill_status, "not available")}`, "blocked")}
                    </div>
                </section>
                <section class="trade-check-section">
                    <p class="label">Reconciliation checks</p>
                    <div class="tag-row">${renderTagList(checkTags, "No broker reconciliation checks recorded")}</div>
                </section>
                <section class="trade-check-section">
                    <p class="label">Blocked reasons</p>
                    <div class="tag-row">${renderTagList(review.blocked_reasons, "No blocking reason recorded")}</div>
                </section>
                <section class="trade-check-section">
                    <p class="label">Required next steps</p>
                    <ul class="status-list">${asArray(review.required_next_steps).length
                        ? asArray(review.required_next_steps).map((step) => `<li><strong>${htmlText(step)}</strong></li>`).join("")
                        : "<li><strong>No next steps recorded</strong></li>"
                    }</ul>
                </section>
            </article>
        `;
    };

    const renderPaperSubmitReceiptCard = (review) => {
        const checkTags = Object.entries(review.receipt_checks || {}).map(([key, value]) => `${key}: ${value}`);
        const receipt = review.simulated_receipt || {};
        const brokerEcho = review.broker_echo || {};
        return `
            <article class="trade-intent-card ${statusClass(review.status || "blocked_before_dry_run_submit")}">
                <div class="cognition-card-head">
                    ${renderStatusPill(review.status || "blocked_before_dry_run_submit")}
                    <p class="label">Dry-run paper-submit receipt · ${htmlText(review.source_broker_reconciliation_review_id, "broker review pending")}</p>
                </div>
                <h3>${htmlText(review.instrument, "Paper-submit receipt review")}</h3>
                <p>${htmlText(review.boundary, "Paper-submit receipt is dry-run only and cannot call brokers.")}</p>
                <div class="tag-row">
                    ${renderInlineBadge(review.dry_run_receipt_created ? "dry-run receipt created" : "dry-run receipt not created", review.dry_run_receipt_created ? "pending" : "online")}
                    ${renderInlineBadge(review.paper_order_submitted ? "paper order submitted" : "paper order not submitted", review.paper_order_submitted ? "blocked" : "online")}
                    ${renderInlineBadge(review.broker_post_called ? "broker POST called" : "broker POST not called", review.broker_post_called ? "blocked" : "online")}
                    ${renderInlineBadge(review.broker_write_allowed ? "broker write allowed" : "broker write blocked", review.broker_write_allowed ? "blocked" : "online")}
                    ${renderInlineBadge(review.live_capital_enabled ? "live capital enabled" : "live capital disabled", review.live_capital_enabled ? "blocked" : "online")}
                </div>
                <div class="summary-strip compact">
                    ${renderMetric("Venue", htmlText(review.selected_venue, "none"))}
                    ${renderMetric("Mode", htmlText(review.venue_mode, "disabled"))}
                    ${renderMetric("Account", htmlText(review.account_scope, "trial"))}
                    ${renderMetric("Receipt", htmlText(receipt.status, "not created"))}
                    ${renderMetric("Broker echo", htmlText(brokerEcho.status, "not requested"))}
                    ${renderMetric("Submitted", htmlText(review.submitted_at, "not submitted"))}
                    ${renderMetric("Reviewed", formatTime(review.reviewed_at))}
                </div>
                <section class="trade-check-section">
                    <p class="label">Simulated receipt</p>
                    <div class="tag-row">
                        ${renderInlineBadge(`mode: ${dashboardText(receipt.mode, "dry run only")}`, "pending")}
                        ${renderInlineBadge(`adapter: ${dashboardText(receipt.adapter, "not selected")}`, "pending")}
                        ${renderInlineBadge(`client id: ${dashboardText(receipt.client_order_id, "not allocated")}`, "blocked")}
                        ${renderInlineBadge(`external id: ${dashboardText(receipt.external_order_id, "not created")}`, "blocked")}
                        ${renderInlineBadge(receipt.broker_post_called ? "POST called" : "POST not called", receipt.broker_post_called ? "blocked" : "online")}
                    </div>
                </section>
                <section class="trade-check-section">
                    <p class="label">Receipt checks</p>
                    <div class="tag-row">${renderTagList(checkTags, "No paper-submit receipt checks recorded")}</div>
                </section>
                <section class="trade-check-section">
                    <p class="label">Blocked reasons</p>
                    <div class="tag-row">${renderTagList(review.blocked_reasons, "No blocking reason recorded")}</div>
                </section>
                <section class="trade-check-section">
                    <p class="label">Required next steps</p>
                    <ul class="status-list">${asArray(review.required_next_steps).length
                        ? asArray(review.required_next_steps).map((step) => `<li><strong>${htmlText(step)}</strong></li>`).join("")
                        : "<li><strong>No next steps recorded</strong></li>"
                    }</ul>
                </section>
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
            <p class="label">Risk Agent policy router</p>
            <div class="summary-strip compact">
                ${renderMetric("Status", riskAgent.status || "pending")}
                ${renderMetric("Reviews", riskAgent.review_count || 0)}
                ${renderMetric("Blocked", riskAgent.by_status?.blocked_before_risk || 0)}
                ${renderMetric("Policy hold", riskAgent.by_status?.policy_hold || 0)}
                ${renderMetric("Shadow ready", riskAgent.by_status?.risk_shadow_ready || 0)}
                ${renderMetric("Orders", riskAgent.order_created_count || 0)}
                ${renderMetric("Broker writes", riskAgent.broker_write_allowed_count || 0)}
                ${renderMetric("Max risk", `${htmlText(riskAgent.max_risk_pct_per_idea, "1")}%`)}
            </div>
            <p class="mini">${htmlText(riskAgent.boundary, "Risk Agent policy router is read-only and cannot approve risk or create orders.")}</p>
            <div class="trade-intent-stack">${riskReviews.length
                ? riskReviews.map(renderRiskReviewCard).join("")
                : `<article class="trade-intent-card"><h3>No Risk Agent reviews yet</h3><p>The policy router has not reviewed any signal or trade-intent records.</p></article>`
            }</div>
        </section>
        <section class="trade-intent-section">
            <p class="label">Execution Policy and kill switches</p>
            <div class="summary-strip compact">
                ${renderMetric("Status", executionPolicy.status || "pending")}
                ${renderMetric("Reviews", executionPolicy.review_count || 0)}
                ${renderMetric("Policy blocks", executionPolicy.by_status?.blocked_by_policy || 0)}
                ${renderMetric("Kill-switch holds", executionPolicy.by_status?.kill_switch_hold || 0)}
                ${renderMetric("Shadow ready", executionPolicy.by_status?.paper_order_shadow_ready || 0)}
                ${renderMetric("Staged orders", executionPolicy.staged_paper_order_allowed_count || 0)}
                ${renderMetric("Orders created", executionPolicy.paper_order_created_count || 0)}
                ${renderMetric("Broker writes", executionPolicy.broker_write_allowed_count || 0)}
                ${renderMetric("Live capital", executionPolicy.live_capital_enabled_count || 0)}
            </div>
            <p class="mini">${htmlText(executionPolicy.boundary, "Execution policy is read-only and cannot stage paper orders or write to brokers.")}</p>
            <div class="trade-intent-stack">${executionPolicyReviews.length
                ? executionPolicyReviews.map(renderExecutionPolicyCard).join("")
                : `<article class="trade-intent-card"><h3>No execution policy reviews yet</h3><p>The execution-policy layer has not reviewed any Risk Agent records.</p></article>`
            }</div>
        </section>
        <section class="trade-intent-section">
            <p class="label">Disabled staged paper-order contract</p>
            <div class="summary-strip compact">
                ${renderMetric("Status", stagedPaperOrder.status || "pending")}
                ${renderMetric("Reviews", stagedPaperOrder.review_count || 0)}
                ${renderMetric("Blocked", stagedPaperOrder.by_status?.blocked_before_staging || 0)}
                ${renderMetric("Reconciliation hold", stagedPaperOrder.by_status?.reconciliation_hold || 0)}
                ${renderMetric("Disabled hold", stagedPaperOrder.by_status?.disabled_contract_hold || 0)}
                ${renderMetric("Staged created", stagedPaperOrder.staged_paper_order_created_count || 0)}
                ${renderMetric("Submittable", stagedPaperOrder.paper_order_submittable_count || 0)}
                ${renderMetric("Broker writes", stagedPaperOrder.broker_write_allowed_count || 0)}
                ${renderMetric("Live capital", stagedPaperOrder.live_capital_enabled_count || 0)}
            </div>
            <p class="mini">${htmlText(stagedPaperOrder.boundary, "Staged paper-order contract is disabled and read-only.")}</p>
            <div class="trade-intent-stack">${stagedPaperOrderReviews.length
                ? stagedPaperOrderReviews.map(renderStagedPaperOrderCard).join("")
                : `<article class="trade-intent-card"><h3>No staged paper-order reviews yet</h3><p>The disabled staging contract has not reviewed any Execution Policy records.</p></article>`
            }</div>
        </section>
        <section class="trade-intent-section">
            <p class="label">Read-only broker reconciliation</p>
            <div class="summary-strip compact">
                ${renderMetric("Status", brokerReconciliation.status || "pending")}
                ${renderMetric("Reviews", brokerReconciliation.review_count || 0)}
                ${renderMetric("Blocked", brokerReconciliation.by_status?.blocked_before_broker_reconciliation || 0)}
                ${renderMetric("Route closed", brokerReconciliation.by_status?.broker_route_closed || 0)}
                ${renderMetric("Contract hold", brokerReconciliation.by_status?.reconciliation_contract_hold || 0)}
                ${renderMetric("Idempotency", brokerReconciliation.idempotency_key_allocated_count || 0)}
                ${renderMetric("Prewrite", brokerReconciliation.event_log_prewrite_created_count || 0)}
                ${renderMetric("Duplicate guard", brokerReconciliation.duplicate_order_guard_ready_count || 0)}
                ${renderMetric("Broker echo", brokerReconciliation.broker_echo_verified_count || 0)}
                ${renderMetric("Submit", brokerReconciliation.paper_order_submit_allowed_count || 0)}
                ${renderMetric("Broker writes", brokerReconciliation.broker_write_allowed_count || 0)}
                ${renderMetric("Live capital", brokerReconciliation.live_capital_enabled_count || 0)}
            </div>
            <p class="mini">${htmlText(brokerReconciliation.boundary, "Broker reconciliation is read-only and cannot submit paper orders.")}</p>
            <div class="trade-intent-stack">${brokerReconciliationReviews.length
                ? brokerReconciliationReviews.map(renderBrokerReconciliationCard).join("")
                : `<article class="trade-intent-card"><h3>No broker reconciliation reviews yet</h3><p>The broker gate has not reviewed any staged paper-order records.</p></article>`
            }</div>
        </section>
        <section class="trade-intent-section">
            <p class="label">Dry-run paper-submit receipt</p>
            <div class="summary-strip compact">
                ${renderMetric("Status", paperSubmitReceipt.status || "pending")}
                ${renderMetric("Reviews", paperSubmitReceipt.review_count || 0)}
                ${renderMetric("Blocked", paperSubmitReceipt.by_status?.blocked_before_dry_run_submit || 0)}
                ${renderMetric("Dry-run blocked", paperSubmitReceipt.by_status?.dry_run_receipt_blocked || 0)}
                ${renderMetric("Dry-run ready", paperSubmitReceipt.by_status?.dry_run_receipt_ready || 0)}
                ${renderMetric("Receipts", paperSubmitReceipt.dry_run_receipt_created_count || 0)}
                ${renderMetric("Submitted", paperSubmitReceipt.paper_order_submitted_count || 0)}
                ${renderMetric("Broker POST", paperSubmitReceipt.broker_post_called_count || 0)}
                ${renderMetric("Broker writes", paperSubmitReceipt.broker_write_allowed_count || 0)}
                ${renderMetric("Live capital", paperSubmitReceipt.live_capital_enabled_count || 0)}
            </div>
            <p class="mini">${htmlText(paperSubmitReceipt.boundary, "Paper-submit receipt is dry-run only and cannot call brokers.")}</p>
            <div class="trade-intent-stack">${paperSubmitReceiptReviews.length
                ? paperSubmitReceiptReviews.map(renderPaperSubmitReceiptCard).join("")
                : `<article class="trade-intent-card"><h3>No dry-run paper-submit reviews yet</h3><p>The dry-run receipt gate has not reviewed any broker reconciliation records.</p></article>`
            }</div>
        </section>
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
                <li>Preparing Paper Trade · disabled until dry-run receipt and broker contracts pass</li>
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
    const orders = asArray(capital.orders);
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

    const orderRows = orders.length
        ? orders.map((order) => `
            <li>
                <strong>${htmlText(order.instrument, "Mirrored paper order")}</strong>
                <span>${htmlText(order.status, "unknown")} · ${htmlText(order.direction, "unknown")} · ${htmlText(order.order_type, "order")}</span>
                <small>${htmlText(order.quantity, "0")} units · notional ${formatMoney(order.notional_gbp)} · ${htmlText(order.boundary, "Read-only mirrored order.")}</small>
            </li>
        `).join("")
        : `<li><strong>No mirrored paper orders</strong><span>Alpaca returned no recent paper orders on the read-only mirror.</span></li>`;

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
                ${renderMetric("Orders", capital.order_count || orders.length)}
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
            <p class="label">Mirrored paper orders</p>
            <ul class="status-list paper-list">${orderRows}</ul>
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
        renderMissionControl(status, source);
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
