(() => {
    "use strict";

    const STATUS_URL = "/status/quantum-edge-wave-g.json?v=20260712-wave-g-v1";
    const TARGET_SELECTOR = '[data-qwf-view="quantum-edge"]';
    let projection = null;
    let observer = null;
    let applyScheduled = false;

    function list(value) {
        return Array.isArray(value) ? value : [];
    }

    function escapeHtml(value, fallback = "") {
        return String(value ?? fallback)
            .replace(/&/g, "&amp;")
            .replace(/</g, "&lt;")
            .replace(/>/g, "&gt;")
            .replace(/"/g, "&quot;")
            .replace(/'/g, "&#039;");
    }

    function titleCase(value, fallback = "Not available") {
        const text = String(value || "").trim();
        if (!text) return fallback;
        return text
            .replace(/[_-]+/g, " ")
            .replace(/\s+/g, " ")
            .replace(/^./, (character) => character.toUpperCase());
    }

    function lastCompletedState(states) {
        const completed = list(states).filter((row) => row.status === "complete");
        return completed.length ? completed[completed.length - 1].state : "candidate noticed";
    }

    function renderLifecycle(states) {
        return `
            <ol class="qwg-lifecycle" aria-label="Hybrid evidence lifecycle">
                ${list(states).map((row, index) => `
                    <li class="${row.status === "complete" ? "is-complete" : "is-pending"}">
                        <span>${String(index + 1).padStart(2, "0")}</span>
                        <div>
                            <strong>${escapeHtml(titleCase(row.state))}</strong>
                            <p>${escapeHtml(row.explanation)}</p>
                        </div>
                        <em>${row.status === "complete" ? "Reached" : "Not reached"}</em>
                    </li>
                `).join("")}
            </ol>
        `;
    }

    function renderStageFacts(stages, automation) {
        const sources = stages.source_refresh || {};
        const classical = stages.classical_discovery || {};
        const quantum = stages.local_quantum_simulation || {};
        const hardware = stages.hardware_experiment_preparation || {};
        return `
            <dl class="qwg-facts">
                <div><dt>Source snapshot</dt><dd>${escapeHtml(sources.source_count || 0)} sources reviewed</dd></div>
                <div><dt>Classical control</dt><dd>${escapeHtml(classical.method_count || 0)} methods reproduced</dd></div>
                <div><dt>Local quantum control</dt><dd>${escapeHtml(quantum.circuit_evaluation_count || 0)} bounded circuit evaluations</dd></div>
                <div><dt>Hardware experiment</dt><dd>${hardware.prepared_experiment_count ? "Prepared, not submitted" : "Not prepared"}</dd></div>
                <div><dt>Provider calls this cycle</dt><dd>${escapeHtml(automation.provider_calls_this_cycle || 0)}</dd></div>
            </dl>
        `;
    }

    function renderRoute(integration) {
        const contract = integration.route_contract || {};
        return `
            <section class="qwg-route">
                <header>
                    <span>Guarded paper path</span>
                    <h3>What happens only after an edge is validated</h3>
                </header>
                <ol>
                    ${list(contract.stages).map((stage) => `<li>${escapeHtml(stage)}</li>`).join("")}
                </ol>
                <dl>
                    <div><dt>Validated edges admitted</dt><dd>${escapeHtml(projection.validated_edge_admissions?.length || 0)}</dd></div>
                    <div><dt>Strategies influenced</dt><dd>${escapeHtml(integration.strategy_count || 0)}</dd></div>
                    <div><dt>Risk reviews</dt><dd>${escapeHtml(integration.risk_review_count || 0)}</dd></div>
                    <div><dt>PaperOps review handoffs</dt><dd>${escapeHtml(integration.paperops_review_handoff_count || 0)}</dd></div>
                </dl>
                <p>Wave G can prepare a review record. It cannot size a position, approve execution, submit an order, or call Alpaca.</p>
            </section>
        `;
    }

    function renderProjection(payload) {
        const integration = payload.paper_integration || {};
        const automation = payload.automation || {};
        const stages = payload.daily_stages || {};
        const lifecycle = list(payload.public_lifecycle);
        const currentState = lastCompletedState(lifecycle);
        const brief = payload.telegram_brief || {};
        return `
            <section class="qwg-loop" data-qwg-loop data-qwg-content-hash="${escapeHtml(payload.content_hash)}">
                <header class="qwg-header">
                    <div>
                        <span>Recurring hybrid loop</span>
                        <h3>From research finding to paper outcome</h3>
                        <p>${escapeHtml(payload.plain_english_summary)}</p>
                    </div>
                    <aside>
                        <span>Furthest evidence state</span>
                        <strong>${escapeHtml(titleCase(currentState))}</strong>
                    </aside>
                </header>
                ${renderLifecycle(lifecycle)}
                <div class="qwg-operations-grid">
                    <section class="qwg-daily-cycle">
                        <header><span>Latest unattended cycle</span><h3>What ran safely</h3></header>
                        ${renderStageFacts(stages, automation)}
                        <p>Daily work is content-addressed and checkpointed. Unchanged evidence is reused; cadence cannot force hardware, validation, strategy promotion, or a trade.</p>
                    </section>
                    ${renderRoute(integration)}
                </div>
                <section class="qwg-brief">
                    <header><span>Human daily brief</span><h3>How this would be explained on Telegram</h3></header>
                    ${escapeHtml(brief.text).split("\n\n").map((paragraph) => `<p>${paragraph}</p>`).join("")}
                    <small>Read-only preview. Wave G does not send messages or accept commands.</small>
                </section>
            </section>
        `;
    }

    function applyProjection() {
        applyScheduled = false;
        if (!projection) return;
        const target = document.querySelector(TARGET_SELECTOR);
        if (!target) return;
        const existing = target.querySelector("[data-qwg-loop]");
        if (existing?.dataset.qwgContentHash === projection.content_hash) return;
        if (existing) existing.remove();
        const boundary = target.querySelector(":scope > .qwf-boundary");
        const wrapper = document.createElement("div");
        wrapper.innerHTML = renderProjection(projection).trim();
        const section = wrapper.firstElementChild;
        if (boundary) target.insertBefore(section, boundary);
        else target.appendChild(section);
        document.documentElement.dataset.qadamWaveG = "rendered";
    }

    function scheduleApply() {
        if (applyScheduled) return;
        applyScheduled = true;
        window.requestAnimationFrame(applyProjection);
    }

    async function loadProjection() {
        try {
            const response = await fetch(STATUS_URL, { cache: "no-store" });
            if (!response.ok) throw new Error(`Wave G status returned ${response.status}`);
            const payload = await response.json();
            if (payload?.schema_version !== "qadam.QuantumEdgeWaveGHybridLoop.v1") {
                throw new Error("Wave G status schema mismatch");
            }
            projection = payload;
            scheduleApply();
        } catch (error) {
            document.documentElement.dataset.qadamWaveG = "unavailable";
            console.error("Qadam Wave G projection unavailable", error);
        }
    }

    observer = new MutationObserver(scheduleApply);
    observer.observe(document.body, { childList: true, subtree: true });
    window.addEventListener("qadam-wave-f-ready", scheduleApply);
    window.addEventListener("popstate", scheduleApply);
    window.QadamWaveG = {
        statusUrl: STATUS_URL,
        apply: scheduleApply,
        getProjection: () => projection,
        disconnect: () => observer?.disconnect()
    };
    loadProjection();
})();
