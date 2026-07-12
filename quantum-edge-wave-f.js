(() => {
    "use strict";

    const STATUS_URL = "/status/quantum-edge-wave-f.json?v=20260712-wave-f-v1";
    const VIEW_SELECTORS = {
        pattern: '[data-qsase-module-panel="patterns"][data-qsase-view-panel="findings"]',
        quantum: '[data-qsase-module-panel="patterns"][data-qsase-view-panel="nonlinear"]',
        strategies: '[data-qsase-module-panel="decide"][data-qsase-view-panel="strategies"]'
    };
    const NAVIGATION_LABELS = [
        ["patterns", "findings", "Pattern Recognition", ["Pattern Discovery", "Pattern Findings", "Pattern Recognition Findings"]],
        ["patterns", "nonlinear", "Quantum Edge", ["Nonlinear Review", "Quantum Review"]],
        ["decide", "strategies", "Trading Strategies", ["Core Strategies"]]
    ];
    let projection = null;
    let observer = null;
    let applyScheduled = false;

    function list(value) {
        return Array.isArray(value) ? value : [];
    }

    function escapeHtml(value, fallback = "") {
        const text = String(value ?? fallback);
        return text
            .replace(/&/g, "&amp;")
            .replace(/</g, "&lt;")
            .replace(/>/g, "&gt;")
            .replace(/"/g, "&quot;")
            .replace(/'/g, "&#039;");
    }

    function human(value, fallback = "Not available") {
        const text = String(value || "").trim();
        if (!text) return fallback;
        return text
            .replace(/[_-]+/g, " ")
            .replace(/\s+/g, " ")
            .replace(/^./, (character) => character.toUpperCase());
    }

    function routeHref(route) {
        if (!route?.module_id || !route?.view_id) return "/dashboard/";
        return `/dashboard/?module=${encodeURIComponent(route.module_id)}&view=${encodeURIComponent(route.view_id)}`;
    }

    function originClass(origin) {
        if (origin === "quantum_assisted_discovery") return "is-quantum";
        if (origin === "joint_discovery") return "is-joint";
        return "is-classical";
    }

    function validationClass(value) {
        if (["quantum_strengthened", "joint_corroboration", "classical_preferred"].includes(value)) return "is-positive";
        if (["weakened", "failed_safely"].includes(value)) return "is-negative";
        return "is-pending";
    }

    function renderBoundary(copy) {
        return `<p class="qwf-boundary">${escapeHtml(copy)}</p>`;
    }

    function renderPatternCard(candidate) {
        const sources = list(candidate.source_chain);
        const instruments = list(candidate.instruments);
        const methods = list(candidate.method_evidence);
        const origin = candidate.discovery_origin || "classical_discovery";
        const contribution = candidate.validation_contribution || "not_tested";
        const quantumLink = candidate.quantum_involved && candidate.quantum_edge_route
            ? `<a class="qwf-text-link" href="${routeHref(candidate.quantum_edge_route)}" data-qsase-route data-qsase-module-target="patterns" data-qsase-view-target="nonlinear">Open its Quantum Edge evidence</a>`
            : "";
        return `
            <details class="qwf-pattern-card ${originClass(origin)}" data-qwf-pattern-card data-qwf-origin="${escapeHtml(origin)}">
                <summary>
                    <div class="qwf-pattern-heading">
                        <div class="qwf-badge-row">
                            <span class="qwf-origin-badge">${escapeHtml(candidate.discovery_origin_label)}</span>
                            <span class="qwf-validation-badge ${validationClass(contribution)}">${escapeHtml(candidate.validation_contribution_label)}</span>
                            ${candidate.contract_fixture_only ? '<span class="qwf-fixture-badge">Engineering control</span>' : ""}
                        </div>
                        <h3>${escapeHtml(candidate.title)}</h3>
                        <p>${escapeHtml(candidate.relationship)}</p>
                    </div>
                    <div class="qwf-pattern-summary">
                        <span>${escapeHtml(candidate.market)}</span>
                        <strong>${escapeHtml(candidate.evidence_state)}</strong>
                        <small>Expand evidence</small>
                    </div>
                </summary>
                <div class="qwf-pattern-body">
                    <div class="qwf-evidence-route" aria-label="Source to market evidence route">
                        <div><span>Detected signal</span><strong>${escapeHtml(candidate.source_chain_summary)}</strong></div>
                        <i aria-hidden="true">→</i>
                        <div><span>Market affected</span><strong>${escapeHtml(candidate.market)}</strong><small>${escapeHtml(instruments.join(", "), "No instrument exported")}</small></div>
                        <i aria-hidden="true">→</i>
                        <div><span>Current meaning</span><strong>${escapeHtml(candidate.interpretation)}</strong></div>
                    </div>
                    <dl class="qwf-pattern-evidence-grid">
                        <div><dt>What would confirm it</dt><dd>${escapeHtml(candidate.confirmation)}</dd></div>
                        <div><dt>What would disprove it</dt><dd>${escapeHtml(candidate.falsifier)}</dd></div>
                        <div><dt>What blocks it now</dt><dd>${escapeHtml(candidate.blocker)}</dd></div>
                        <div><dt>Next action</dt><dd>${escapeHtml(candidate.next_action)}</dd></div>
                    </dl>
                    <div class="qwf-pattern-footer">
                        <div><span>Lifecycle</span><strong>${escapeHtml(human(candidate.lifecycle_stage))}</strong></div>
                        <div><span>Computation</span><strong>${escapeHtml(candidate.execution_mode_label)}</strong></div>
                        ${quantumLink}
                    </div>
                    ${methods.length ? `
                        <details class="qwf-technical-details">
                            <summary>Method evidence</summary>
                            <div class="qwf-method-list">
                                ${methods.map((method) => `
                                    <article>
                                        <span>${escapeHtml(human(method.discovery_origin))}</span>
                                        <strong>${escapeHtml(human(method.method))}</strong>
                                        <p>${escapeHtml(human(method.execution_mode))}${method.structural_score === null || method.structural_score === undefined ? "" : ` · structural score ${escapeHtml(Number(method.structural_score).toFixed(3))}`}</p>
                                    </article>
                                `).join("")}
                            </div>
                        </details>
                    ` : ""}
                </div>
            </details>
        `;
    }

    function renderPatternRecognition(section) {
        const candidates = list(section.candidates);
        const filters = list(section.filters);
        return `
            <section class="qwf-view qwf-pattern-recognition" data-qwf-view="pattern-recognition">
                <header class="qwf-page-header">
                    <div><span>Find Patterns</span><h2>Pattern Recognition</h2><p>${escapeHtml(section.headline)}</p></div>
                    <aside><strong>${escapeHtml(section.candidate_count || candidates.length)}</strong><span>research relationships</span></aside>
                </header>
                <p class="qwf-page-intro">${escapeHtml(section.plain_english_summary)}</p>
                <div class="qwf-origin-key" aria-label="Pattern origin key">
                    <span class="is-classical"><i></i>Classical recognition</span>
                    <span class="is-quantum"><i></i>Quantum-assisted recognition</span>
                    <span class="is-joint"><i></i>Found by both</span>
                </div>
                <div class="qwf-filter-bar" role="tablist" aria-label="Filter patterns by discovery origin">
                    ${filters.map((filter, index) => `
                        <button type="button" role="tab" data-qwf-origin-filter="${escapeHtml(filter.key)}" aria-selected="${index === 0 ? "true" : "false"}">
                            <span>${escapeHtml(filter.label)}</span><strong>${escapeHtml(filter.count)}</strong>
                        </button>
                    `).join("")}
                </div>
                <div class="qwf-pattern-list" data-qwf-pattern-list>
                    ${candidates.map(renderPatternCard).join("")}
                    <article class="qwf-empty-state" data-qwf-filter-empty hidden>
                        <strong>No records in this lane</strong>
                        <p>Qadam has not exported a candidate with the selected discovery origin.</p>
                    </article>
                </div>
                ${renderBoundary(section.boundary)}
            </section>
        `;
    }

    function renderProofStep(step, index) {
        return `
            <li class="${escapeHtml(step.state)}">
                <span>${String(index + 1).padStart(2, "0")}</span>
                <div><strong>${escapeHtml(step.label)}</strong><p>${escapeHtml(step.explanation)}</p></div>
                <em>${escapeHtml(human(step.state))}</em>
            </li>
        `;
    }

    function renderExperiment(experiment) {
        return `
            <details class="qwf-experiment-card is-${escapeHtml(experiment.kind)}">
                <summary>
                    <div><span>${escapeHtml(human(experiment.kind))}</span><strong>${escapeHtml(experiment.title)}</strong></div>
                    <em>${escapeHtml(human(experiment.state))}</em>
                    <i aria-hidden="true"></i>
                </summary>
                <div><p>${escapeHtml(experiment.result)}</p><small>${escapeHtml(experiment.boundary)}</small></div>
            </details>
        `;
    }

    function renderClassicalComparison(comparison) {
        return `
            <section class="qwf-classical-comparison">
                <header><span>Classical comparison</span><h3>Did quantum beat the strongest fair baseline?</h3></header>
                <p>${escapeHtml(comparison.plain_english_summary)}</p>
                <dl>
                    <div><dt>Current verdict</dt><dd>${escapeHtml(comparison.verdict_label)}</dd></div>
                    <div><dt>Market evidence</dt><dd>${comparison.empirical_claim_allowed ? "Untouched comparison complete" : "Untouched comparison still missing"}</dd></div>
                    <div><dt>Classical benchmark</dt><dd>${escapeHtml(human(comparison.classical_baseline))}</dd></div>
                    <div><dt>Quantum method</dt><dd>${escapeHtml(human(comparison.quantum_method))}</dd></div>
                    <div><dt>What blocks a verdict</dt><dd>${escapeHtml(human(comparison.blocker))}</dd></div>
                </dl>
            </section>
        `;
    }

    function renderQuantumEdge(section) {
        const authenticity = section.hardware_authenticity || {};
        const strongest = section.strongest_evidence || {};
        const provenance = section.provenance || {};
        const comparison = section.comparison_summary || {};
        const strategyInfluence = section.strategy_influence || {};
        const paperLineage = section.paper_outcome_lineage || {};
        return `
            <section class="qwf-view qwf-quantum-edge" data-qwf-view="quantum-edge">
                <header class="qwf-page-header qwf-quantum-header">
                    <div><span>Quantum Research</span><h2>Quantum Edge</h2><p>Did quantum computation add useful information beyond Qadam's strongest matched classical method?</p></div>
                    <aside><strong>${escapeHtml(section.completed_proof_step_count || 0)} / 6</strong><span>proof steps complete</span></aside>
                </header>
                <section class="qwf-proof-state">
                    <span>Current proof state</span>
                    <h3>${escapeHtml(section.headline)}</h3>
                    <p>${escapeHtml(section.plain_english_summary)}</p>
                </section>
                <ol class="qwf-proof-ladder" aria-label="Quantum edge proof ladder">
                    ${list(section.proof_ladder).map(renderProofStep).join("")}
                </ol>
                <section class="qwf-strongest-evidence">
                    <div><span>Strongest evidence so far</span><h3>${escapeHtml(strongest.title)}</h3><p>${escapeHtml(strongest.summary)}</p></div>
                    <a href="${routeHref({module_id: "patterns", view_id: "findings"})}" data-qsase-route data-qsase-module-target="patterns" data-qsase-view-target="findings">Open originating pattern</a>
                </section>
                <section class="qwf-section-block">
                    <header><span>Experiment gallery</span><h3>What Qadam has actually run</h3></header>
                    <div class="qwf-experiment-list">${list(section.experiments).map(renderExperiment).join("")}</div>
                </section>
                ${renderClassicalComparison(comparison)}
                <div class="qwf-quantum-evidence-grid">
                    <section class="qwf-negative-results">
                        <header><span>Negative evidence</span><h3>What has not passed</h3></header>
                        ${list(section.negative_results).map((result) => `<article><strong>${escapeHtml(result.title)}</strong><p>${escapeHtml(result.explanation)}</p></article>`).join("")}
                    </section>
                    <section class="qwf-hardware-truth">
                        <header><span>Hardware authenticity</span><h3>What the provider record proves</h3></header>
                        <dl>
                            <div><dt>Q-CTRL product access</dt><dd>${authenticity.qctrl_product_entitled ? "Verified" : "Not verified"}</dd></div>
                            <div><dt>IBM instance accessible</dt><dd>${authenticity.ibm_instance_accessible ? "Yes" : "No"}</dd></div>
                            <div><dt>Provider calls</dt><dd>${escapeHtml(authenticity.provider_call_count || 0)}</dd></div>
                            <div><dt>Hardware job submitted</dt><dd>${authenticity.hardware_job_submitted ? "Yes" : "No"}</dd></div>
                            <div><dt>Hardware result completed</dt><dd>${authenticity.hardware_experiment_completed ? "Yes" : "No"}</dd></div>
                            <div><dt>Verified receipt</dt><dd>${authenticity.hardware_receipt_verified ? "Yes" : "No"}</dd></div>
                        </dl>
                        <p>${escapeHtml(human(authenticity.provider_blocker, "No provider blocker exported"))}</p>
                    </section>
                </div>
                <div class="qwf-quantum-impact-grid">
                    <section>
                        <span>Strategy influence</span>
                        <strong>${escapeHtml(strategyInfluence.validated_strategy_count || 0)} validated strategies changed</strong>
                        <p>${escapeHtml(strategyInfluence.summary)}</p>
                    </section>
                    <section>
                        <span>Paper outcome lineage</span>
                        <strong>${escapeHtml(paperLineage.attributed_paper_decision_count || 0)} paper decisions attributed</strong>
                        <p>${escapeHtml(paperLineage.summary)}</p>
                    </section>
                </div>
                <details class="qwf-technical-details qwf-provenance">
                    <summary>Dataset, circuit, and evaluation provenance</summary>
                    <dl>
                        <div><dt>Shared evidence manifest</dt><dd>${escapeHtml(provenance.shared_manifest_hash, "Not exported")}</dd></div>
                        <div><dt>Prepared hardware manifest</dt><dd>${escapeHtml(provenance.hardware_manifest_hash, "Not exported")}</dd></div>
                        <div><dt>Independent evaluator policy</dt><dd>${escapeHtml(provenance.evaluation_policy_hash, "Not exported")}</dd></div>
                    </dl>
                </details>
                ${renderBoundary(section.boundary)}
            </section>
        `;
    }

    function renderStrategyCard(strategy, admitted) {
        const origins = list(strategy.discovery_origins);
        const contributions = list(strategy.validation_contributions);
        return `
            <details class="qwf-strategy-card ${admitted ? "is-admitted" : "is-research"}">
                <summary>
                    <div><span>${admitted ? "Validated strategy" : "Research playbook"}</span><strong>${escapeHtml(strategy.label)}</strong><p>${escapeHtml(strategy.thesis)}</p></div>
                    <aside><em>${escapeHtml(strategy.validated_edge_count || 0)} validated edges</em><small>Expand playbook</small></aside>
                </summary>
                <div class="qwf-strategy-body">
                    <dl>
                        <div><dt>Market</dt><dd>${escapeHtml(human(strategy.market))}</dd></div>
                        <div><dt>Instruments</dt><dd>${escapeHtml(list(strategy.instruments).join(", "), "Not exported")}</dd></div>
                        <div><dt>Catalyst</dt><dd>${escapeHtml(strategy.catalyst)}</dd></div>
                        <div><dt>Confirmation</dt><dd>${escapeHtml(strategy.confirmation)}</dd></div>
                        <div><dt>Entry discipline</dt><dd>${escapeHtml(strategy.entry)}</dd></div>
                        <div><dt>Invalidation</dt><dd>${escapeHtml(strategy.invalidation)}</dd></div>
                        <div><dt>Exit discipline</dt><dd>${escapeHtml(strategy.exits)}</dd></div>
                        <div><dt>Present blocker</dt><dd>${escapeHtml(strategy.present_blocker)}</dd></div>
                    </dl>
                    <section class="qwf-strategy-lineage">
                        <span>Discovery lineage</span>
                        <p>${origins.length ? escapeHtml(origins.map(human).join(" · ")) : "No originating pattern is validated."}</p>
                        <p>${contributions.length ? escapeHtml(contributions.map(human).join(" · ")) : "No independent validation contribution exists."}</p>
                        <div>
                            <a href="${routeHref(strategy.pattern_recognition_route)}" data-qsase-route data-qsase-module-target="patterns" data-qsase-view-target="findings">Pattern Recognition</a>
                            ${strategy.quantum_edge_route ? `<a href="${routeHref(strategy.quantum_edge_route)}" data-qsase-route data-qsase-module-target="patterns" data-qsase-view-target="nonlinear">Quantum Edge</a>` : ""}
                        </div>
                    </section>
                </div>
            </details>
        `;
    }

    function renderTradingStrategies(section) {
        const admitted = list(section.admitted_strategies);
        const research = list(section.research_playbooks);
        return `
            <section class="qwf-view qwf-trading-strategies" data-qwf-view="trading-strategies">
                <header class="qwf-page-header">
                    <div><span>Test & Decide</span><h2>Trading Strategies</h2><p>${escapeHtml(section.headline)}</p></div>
                    <aside><strong>${escapeHtml(section.validated_strategy_count || 0)}</strong><span>validated strategies</span></aside>
                </header>
                <p class="qwf-page-intro">${escapeHtml(section.plain_english_summary)}</p>
                <section class="qwf-section-block">
                    <header><span>Approved playbooks</span><h3>Strategies backed by validated pattern evidence</h3></header>
                    ${admitted.length
                        ? `<div class="qwf-strategy-list">${admitted.map((strategy) => renderStrategyCard(strategy, true)).join("")}</div>`
                        : `<article class="qwf-empty-state qwf-strategy-empty"><strong>No strategy has passed admission yet</strong><p>Qadam has defined research playbooks, but none has an independently validated underlying edge. Hardware activity and provisional patterns cannot enter this list.</p><a href="${routeHref({module_id: "patterns", view_id: "findings"})}" data-qsase-route data-qsase-module-target="patterns" data-qsase-view-target="findings">Review Pattern Recognition</a></article>`}
                </section>
                <details class="qwf-research-playbooks">
                    <summary><div><span>Research queue</span><strong>${research.length} defined playbooks still awaiting validation</strong></div><i aria-hidden="true"></i></summary>
                    <div class="qwf-strategy-list">${research.map((strategy) => renderStrategyCard(strategy, false)).join("")}</div>
                </details>
                ${renderBoundary(section.boundary)}
            </section>
        `;
    }

    function updateNavigationLabel(moduleId, viewId, label, previousLabels) {
        document.querySelectorAll(`[data-qsase-module-target="${moduleId}"][data-qsase-view-target="${viewId}"]`).forEach((link) => {
            if (link.closest(".qwf-view")) return;
            if (link.childElementCount === 0 && previousLabels.includes(link.textContent.trim())) {
                link.textContent = label;
            }
            link.querySelectorAll("strong").forEach((strong) => {
                let copy = strong.textContent;
                previousLabels.forEach((previous) => {
                    copy = copy.replace(previous, label);
                });
                if (copy !== strong.textContent) strong.textContent = copy;
            });
            if (link.closest(".qsase-sidebar") && link.getAttribute("aria-label") !== label) {
                link.setAttribute("aria-label", label);
            }
        });
    }

    function updateCurrentViewLabel() {
        const params = new URLSearchParams(window.location.search);
        const moduleId = params.get("module");
        const viewId = params.get("view");
        const match = NAVIGATION_LABELS.find(([module, view]) => module === moduleId && view === viewId);
        if (!match) return;
        const current = document.querySelector("[data-qsase-current-view]");
        if (current && current.textContent !== match[2]) current.textContent = match[2];
        const title = `${match[2]} | Qadam Dashboard`;
        if (document.title !== title) document.title = title;
    }

    function replacePanel(selector, html, viewName) {
        const panel = document.querySelector(selector);
        if (!panel || !projection) return;
        if (panel.dataset.qadamWaveFHash === projection.content_hash) return;
        panel.dataset.qadamWaveFHash = projection.content_hash;
        panel.dataset.qadamWaveFView = viewName;
        panel.innerHTML = html;
    }

    function applyProjection() {
        applyScheduled = false;
        if (!projection) return;
        NAVIGATION_LABELS.forEach(([moduleId, viewId, label, previousLabels]) => updateNavigationLabel(moduleId, viewId, label, previousLabels));
        updateCurrentViewLabel();
        replacePanel(VIEW_SELECTORS.pattern, renderPatternRecognition(projection.pattern_recognition || {}), "pattern-recognition");
        replacePanel(VIEW_SELECTORS.quantum, renderQuantumEdge(projection.quantum_edge || {}), "quantum-edge");
        replacePanel(VIEW_SELECTORS.strategies, renderTradingStrategies(projection.trading_strategies || {}), "trading-strategies");
        document.documentElement.dataset.qadamWaveF = "rendered";
    }

    function scheduleApply() {
        if (applyScheduled) return;
        applyScheduled = true;
        window.requestAnimationFrame(applyProjection);
    }

    function handleFilter(button) {
        const root = button.closest("[data-qwf-view='pattern-recognition']");
        if (!root) return;
        const filter = button.dataset.qwfOriginFilter;
        const cards = Array.from(root.querySelectorAll("[data-qwf-pattern-card]"));
        let visible = 0;
        root.querySelectorAll("[data-qwf-origin-filter]").forEach((control) => {
            control.setAttribute("aria-selected", control === button ? "true" : "false");
        });
        cards.forEach((card) => {
            const show = filter === "all" || card.dataset.qwfOrigin === filter;
            card.hidden = !show;
            if (show) visible += 1;
        });
        const empty = root.querySelector("[data-qwf-filter-empty]");
        if (empty) empty.hidden = visible > 0;
    }

    async function loadProjection() {
        try {
            const response = await fetch(STATUS_URL, { cache: "no-store" });
            if (!response.ok) throw new Error(`Wave F status returned ${response.status}`);
            const payload = await response.json();
            if (payload?.schema_version !== "qadam.QuantumEdgeWaveFPublicView.v1") {
                throw new Error("Wave F status schema mismatch");
            }
            projection = payload;
            scheduleApply();
            window.dispatchEvent(new CustomEvent("qadam-wave-f-ready", { detail: { contentHash: payload.content_hash } }));
        } catch (error) {
            document.documentElement.dataset.qadamWaveF = "unavailable";
            console.error("Qadam Wave F projection unavailable", error);
        }
    }

    document.addEventListener("click", (event) => {
        const filter = event.target?.closest?.("[data-qwf-origin-filter]");
        if (filter) handleFilter(filter);
    });
    observer = new MutationObserver(scheduleApply);
    observer.observe(document.body, { childList: true, subtree: true });
    window.addEventListener("popstate", scheduleApply);
    window.QadamWaveF = {
        statusUrl: STATUS_URL,
        apply: scheduleApply,
        getProjection: () => projection,
        disconnect: () => observer?.disconnect()
    };
    loadProjection();
})();
