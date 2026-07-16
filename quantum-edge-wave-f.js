(() => {
    "use strict";

    const STATUS_URL = "/status/quantum-edge-wave-f.json?v=20260716-dashboard-ux-consistency-v1";
    const VIEW_SELECTORS = {
        pattern: '[data-qsase-module-panel="patterns"][data-qsase-view-panel="findings"]',
        strategies: '[data-qsase-module-panel="decide"][data-qsase-view-panel="strategies"]'
    };
    const NAVIGATION_LABELS = [
        ["patterns", "findings", "Pattern Recognition", ["Pattern Discovery", "Pattern Findings", "Pattern Recognition Findings"]],
        ["patterns", "nonlinear", "Quantum Edge", ["Nonlinear Review", "Quantum Review"]],
        ["decide", "strategies", "Trading Strategies", ["Core Strategies"]]
    ];
    const PATTERN_STATE_KEY = "qadam.patternRecognition.v2";
    const STRATEGY_STATE_KEY = "qadam.tradingStrategies.v2";
    const PATTERN_PAGE_SIZE = 7;
    let projection = null;
    let observer = null;
    let applyScheduled = false;
    let activeTooltipTrigger = null;
    let activeTooltipPinned = false;

    function readPatternState() {
        const fallback = { filter: "all", sort: "recommended", visible: PATTERN_PAGE_SIZE, openIds: [], explanationOpen: false };
        try {
            const stored = JSON.parse(window.sessionStorage.getItem(PATTERN_STATE_KEY) || "null");
            return {
                filter: String(stored?.filter || fallback.filter),
                sort: String(stored?.sort || fallback.sort),
                visible: Math.max(PATTERN_PAGE_SIZE, Number(stored?.visible) || PATTERN_PAGE_SIZE),
                openIds: list(stored?.openIds).map(String),
                explanationOpen: stored?.explanationOpen === true
            };
        } catch (_error) {
            return fallback;
        }
    }

    function writePatternState(next) {
        try {
            window.sessionStorage.setItem(PATTERN_STATE_KEY, JSON.stringify(next));
        } catch (_error) {
            // The dashboard remains usable when storage is unavailable.
        }
    }

    function updatePatternState(patch) {
        const next = { ...readPatternState(), ...patch };
        writePatternState(next);
        return next;
    }

    function readStrategyState() {
        try {
            const stored = JSON.parse(window.sessionStorage.getItem(STRATEGY_STATE_KEY) || "null");
            return { openIds: list(stored?.openIds).map(String) };
        } catch (_error) {
            return { openIds: [] };
        }
    }

    function writeStrategyState(next) {
        try {
            window.sessionStorage.setItem(STRATEGY_STATE_KEY, JSON.stringify(next));
        } catch (_error) {
            // The dashboard remains usable when storage is unavailable.
        }
    }

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

    function sentenceCase(value, fallback = "Not available") {
        const raw = String(value || "").trim();
        if (!raw) return fallback;
        return raw.replace(/[A-Za-z]/, (character) => character.toUpperCase());
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

    function tooltipTerm(label, help, className = "") {
        if (!help) return `<span class="${escapeHtml(className)}">${escapeHtml(label)}</span>`;
        return `<button type="button" class="qwf-tooltip-term ${escapeHtml(className)}" data-qwf-tooltip="${escapeHtml(help)}" aria-label="${escapeHtml(`${label}. ${help}`)}">${escapeHtml(label)}</button>`;
    }

    function renderStrategyLenses(candidate) {
        const lenses = list(candidate.strategy_lenses);
        if (!lenses.length) return "";
        return `
            <section class="qwf-strategy-fit" aria-labelledby="qwf-strategy-fit-${escapeHtml(candidate.candidate_id)}">
                <header>
                    <span>Potential strategy fit</span>
                    <h4 id="qwf-strategy-fit-${escapeHtml(candidate.candidate_id)}">How this research could be used later</h4>
                    <p>These are lenses for testing or using the relationship. They do not mean a strategy or trade has been approved.</p>
                </header>
                <dl>
                    ${lenses.map((lens) => `
                        <div>
                            <dt>${tooltipTerm(lens.label, lens.explanation)}</dt>
                            <dd>${escapeHtml(lens.role)}</dd>
                        </div>
                    `).join("")}
                </dl>
            </section>
        `;
    }

    function renderPatternMetadata(candidate, quantumLink) {
        const firstDate = new Date(candidate.first_observed_at || candidate.observed_at || "");
        const lastDate = new Date(candidate.last_observed_at || candidate.observed_at || "");
        const dateOptions = { day: "numeric", month: "short", year: "numeric" };
        const firstLabel = Number.isNaN(firstDate.getTime()) ? "Start not exported" : firstDate.toLocaleDateString([], dateOptions);
        const lastLabel = Number.isNaN(lastDate.getTime()) ? "Latest not exported" : lastDate.toLocaleDateString([], dateOptions);
        const sameObservation = firstLabel === lastLabel;
        const observationCount = Math.max(1, Number(candidate.observation_count) || 1);
        return `
            <div class="qwf-pattern-metadata">
                <div>
                    <span>Status</span>
                    ${tooltipTerm(candidate.lifecycle_label, candidate.lifecycle_help)}
                </div>
                <div>
                    <span>Found by</span>
                    ${tooltipTerm(candidate.computation_label, candidate.computation_help)}
                </div>
                <div>
                    <span>Observed</span>
                    <strong>${escapeHtml(sameObservation ? firstLabel : `${firstLabel} to ${lastLabel}`)}</strong>
                    <small>${escapeHtml(`${observationCount} ${observationCount === 1 ? "observation" : "observations"}`)}</small>
                </div>
                ${quantumLink ? `<div class="qwf-pattern-metadata-link">${quantumLink}</div>` : ""}
            </div>
        `;
    }

    function renderPatternPathParagraph(path = {}) {
        const paragraph = String(path.paragraph || "");
        const filterLabel = "Akber’s 6-Stage Filter";
        const filterHelp = "Akber’s 6-Stage Filter checks context, catalyst, confirmation, risk, execution suitability, and what Qadam should learn afterward. A pass means an idea looks practical enough for the Decision Room to continue reviewing; it is not permission to place an order.";
        const markerIndex = paragraph.indexOf(filterLabel);
        if (markerIndex < 0) return escapeHtml(paragraph);
        return `${escapeHtml(paragraph.slice(0, markerIndex))}${tooltipTerm(filterLabel, filterHelp)}${escapeHtml(paragraph.slice(markerIndex + filterLabel.length))}`;
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
        const score = candidate.research_score || {};
        const state = readPatternState();
        const isOpen = state.openIds.includes(String(candidate.candidate_id));
        const observed = Date.parse(candidate.last_observed_at || candidate.observed_at || "") || 0;
        const quantumLink = candidate.quantum_involved && candidate.quantum_edge_route
            ? `<a class="qwf-text-link" href="${routeHref(candidate.quantum_edge_route)}" data-qsase-route data-qsase-module-target="patterns" data-qsase-view-target="nonlinear">Open its Quantum Edge evidence</a>`
            : "";
        return `
            <details class="qwf-pattern-card ${originClass(origin)}" data-qwf-pattern-card data-qwf-pattern-id="${escapeHtml(candidate.candidate_id)}" data-qwf-origin="${escapeHtml(origin)}" data-qwf-score="${escapeHtml(score.value ?? 0)}" data-qwf-observed="${escapeHtml(observed)}" data-qwf-rank="${escapeHtml(candidate.recommended_rank || 999)}" data-qwf-validated="${candidate.validated_edge ? "true" : "false"}" data-qwf-fixture="${candidate.contract_fixture_only ? "true" : "false"}" data-qwf-title="${escapeHtml(String(candidate.title || "").toLowerCase())}" ${isOpen ? "open" : ""}>
                <summary>
                    <div class="qwf-pattern-heading">
                        <div class="qwf-badge-row">
                            ${tooltipTerm(sentenceCase(candidate.pattern_category), candidate.pattern_category_help, "qwf-category-badge")}
                            ${tooltipTerm(candidate.discovery_origin_label, candidate.computation_help, "qwf-origin-badge")}
                            ${tooltipTerm(candidate.validation_contribution_label, candidate.validation_contribution_help, `qwf-validation-badge ${validationClass(contribution)}`)}
                            ${candidate.contract_fixture_only ? tooltipTerm("System test only", candidate.evidence_help, "qwf-fixture-badge") : ""}
                        </div>
                        <h3>${escapeHtml(sentenceCase(candidate.title))}</h3>
                        <p>${escapeHtml(candidate.relationship)}</p>
                    </div>
                    <div class="qwf-pattern-summary">
                        ${tooltipTerm(score.display, score.explanation, "qwf-score")}
                        <span>${escapeHtml(sentenceCase(candidate.market))}</span>
                        ${tooltipTerm(candidate.evidence_label, candidate.evidence_help, "qwf-public-state")}
                        <span class="qsase-card-expand" aria-hidden="true"><b>Expand Details</b><i></i></span>
                    </div>
                </summary>
                <div class="qwf-pattern-body">
                    <section class="qwf-potential-pattern">
                        <span>What is the potential pattern?</span>
                        <p>${escapeHtml(candidate.potential_pattern_summary)}</p>
                    </section>
                    <div class="qwf-evidence-route" aria-label="Source to market evidence route">
                        <div><span>${tooltipTerm("Strongest contributing signals", "These are the signals that made this row stand out. Qadam still checked the complete source and market universe.")}</span><strong>${escapeHtml(candidate.source_chain_summary)}</strong></div>
                        <i aria-hidden="true">→</i>
                        <div><span>${tooltipTerm("Market affected", "The market sleeve and instruments whose price behavior is being compared with the evidence.")}</span><strong>${escapeHtml(sentenceCase(candidate.market))}</strong><small>${escapeHtml(instruments.join(", "), "No instrument exported")}</small></div>
                        <i aria-hidden="true">→</i>
                        <div><span>${tooltipTerm("Current meaning", "Qadam's present interpretation. It can change as new evidence arrives.")}</span><strong>${escapeHtml(candidate.interpretation)}</strong></div>
                    </div>
                    ${renderStrategyLenses(candidate)}
                    <dl class="qwf-pattern-evidence-grid">
                        <div><dt>${tooltipTerm("What would confirm it", "The independent evidence that must appear before Qadam can treat the relationship as more credible.")}</dt><dd>${escapeHtml(candidate.confirmation)}</dd></div>
                        <div><dt>${tooltipTerm("What would disprove it", "The result that would weaken or reject the proposed relationship.")}</dt><dd>${escapeHtml(candidate.falsifier)}</dd></div>
                        <div><dt>${tooltipTerm("What blocks it now", "The most important missing evidence or failed check preventing progress.")}</dt><dd>${escapeHtml(candidate.blocker)}</dd></div>
                        <div><dt>${tooltipTerm("Next action", "The next research step Qadam should take. This is not a trade instruction.")}</dt><dd>${escapeHtml(candidate.next_action)}</dd></div>
                    </dl>
                    ${renderPatternMetadata(candidate, quantumLink)}
                    ${methods.length ? `
                        <details class="qwf-technical-details">
                            <summary>Technical method evidence</summary>
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
        const sortOptions = list(section.sort_options);
        const state = readPatternState();
        const selectedFilter = filters.some((filter) => filter.key === state.filter) ? state.filter : "all";
        const selectedSort = sortOptions.some((option) => option.key === state.sort) ? state.sort : "recommended";
        const scope = section.comparison_scope || {};
        const path = section.strategy_path_explainer || {};
        const pathStages = list(path.stages);
        const explanationOpen = state.explanationOpen === true;
        return `
            <section class="qwf-view qwf-pattern-recognition" data-qwf-view="pattern-recognition">
                <header class="qwf-page-header">
                    <div>
                        <span>${escapeHtml(section.eyebrow || "Predictive Architecture")}</span>
                        <h2>Pattern Recognition</h2>
                        <p>${escapeHtml(section.headline)}</p>
                        <button type="button" class="qwf-pattern-path-toggle" data-qwf-strategy-path-toggle aria-expanded="${explanationOpen ? "true" : "false"}" aria-controls="qwf-pattern-strategy-path">${escapeHtml(path.label || "How a recognised pattern becomes a trading strategy")} ${explanationOpen ? "−" : "+"}</button>
                        <section id="qwf-pattern-strategy-path" class="qwf-pattern-path-guidance" data-qwf-strategy-path ${explanationOpen ? "" : "hidden"}>
                            <p>${renderPatternPathParagraph(path)}</p>
                            <span class="qwf-pattern-path-label">From recognised relationship to guarded paper review</span>
                            <ol aria-label="Path from recognised pattern to guarded paper trade">
                                ${pathStages.map((stage, index) => `<li><b>${String(index + 1).padStart(2, "0")}</b><span>${escapeHtml(stage)}</span></li>`).join("")}
                            </ol>
                        </section>
                    </div>
                    <aside><strong>${escapeHtml(section.candidate_count || candidates.length)}</strong><span>Research relationships</span></aside>
                </header>
                <section class="qwf-universe-scope" aria-labelledby="qwf-universe-scope-title">
                    <div>
                        <span>Whole-universe search</span>
                        <h3 id="qwf-universe-scope-title">${escapeHtml(scope.source_count || 0)} sources × ${escapeHtml(scope.instrument_count || 0)} watched instruments</h3>
                    </div>
                    <p>${escapeHtml(scope.plain_english_summary)}</p>
                    ${tooltipTerm(scope.matrix_summary, "This is the number of point-in-time source and price rows available to the search, not the number of validated patterns.", "qwf-scope-help")}
                </section>
                <div class="qwf-origin-key" aria-label="Pattern origin key">
                    <span class="is-classical"><i></i>${tooltipTerm("Classical recognition", "Statistical and machine-learning methods surfaced this relationship without quantum-assisted discovery.")}</span>
                    <span class="is-quantum"><i></i>${tooltipTerm("Quantum-assisted recognition", "A bounded quantum method surfaced the relationship. The label does not by itself prove an advantage over classical analysis.")}</span>
                    <span class="is-joint"><i></i>${tooltipTerm("Found by both", "Classical and quantum-assisted lanes independently pointed to the same candidate relationship.")}</span>
                </div>
                <div class="qwf-controls">
                    <div class="qwf-filter-bar" role="tablist" aria-label="Filter patterns by discovery origin">
                        ${filters.map((filter) => `
                            <button type="button" role="tab" data-qwf-origin-filter="${escapeHtml(filter.key)}" aria-selected="${filter.key === selectedFilter ? "true" : "false"}">
                                <span>${escapeHtml(filter.label)}</span><strong>${escapeHtml(filter.count)}</strong>
                            </button>
                        `).join("")}
                    </div>
                    <label class="qwf-sort-control">
                        <span class="qwf-sort-label">${tooltipTerm("Sort observations", "Recommended balances research evidence and validation readiness. You can instead sort by recency, score, validation proximity, or title.")}</span>
                        <span class="qwf-sort-select">
                            <select data-qwf-pattern-sort aria-label="Sort pattern observations">
                                ${sortOptions.map((option) => `<option value="${escapeHtml(option.key)}" ${option.key === selectedSort ? "selected" : ""}>${escapeHtml(option.label)}</option>`).join("")}
                            </select>
                            <i aria-hidden="true"></i>
                        </span>
                    </label>
                </div>
                <div class="qwf-pattern-list" data-qwf-pattern-list data-qsase-progressive-list="pattern-recognition" data-qsase-page-size="${PATTERN_PAGE_SIZE}">
                    ${candidates.map(renderPatternCard).join("")}
                    <article class="qwf-empty-state" data-qwf-filter-empty hidden>
                        <strong>No records in this lane</strong>
                        <p>Qadam has not exported a candidate with the selected discovery origin.</p>
                    </article>
                </div>
                <button type="button" class="qwf-view-more" data-qwf-view-more hidden>View More +</button>
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
                    <div><span>Quantum Benchmark Framework</span><h2>Quantum Edge</h2><p>Not every pattern needs quantum analysis. This framework tests whether a nonlinear or quantum-assisted method contributes information that the strongest conventional method missed.</p></div>
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
                        <p>${escapeHtml(authenticity.provider_status_summary || human(authenticity.provider_blocker, "Provider status was not exported"))}</p>
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

    function renderStrategyPattern(pattern) {
        const score = pattern.research_score || {};
        return `
            <article class="qwf-strategy-pattern ${originClass(pattern.discovery_origin)}">
                <div>
                    <span>${escapeHtml(pattern.discovery_origin_label || human(pattern.discovery_origin))}</span>
                    <strong>${escapeHtml(pattern.relationship || pattern.title)}</strong>
                    <small>${escapeHtml(pattern.lifecycle_label || "Lifecycle state unavailable")}</small>
                </div>
                <p class="qwf-strategy-pattern-score"><span>Research score</span><strong>${escapeHtml(score.display || Number(score.value || 0).toFixed(3))}</strong></p>
                <p>${escapeHtml(pattern.next_action || "The next research action has not been exported.")}</p>
            </article>
        `;
    }

    function renderInstrumentGroup(label, instruments, explanation) {
        const rows = list(instruments);
        return `
            <section class="qwf-strategy-instruments">
                <span>${escapeHtml(label)}</span>
                <p>${escapeHtml(explanation)}</p>
                <div>${rows.length ? rows.map((instrument) => `<strong>${escapeHtml(instrument)}</strong>`).join("") : "<em>None exported</em>"}</div>
            </section>
        `;
    }

    function renderStrategyCard(strategy, admitted) {
        const origins = list(strategy.discovery_origins);
        const contributions = list(strategy.validation_contributions);
        const patterns = list(strategy.pattern_lineage);
        const patternCount = Number(strategy.pattern_count) || patterns.length;
        const statusLabel = admitted ? "Validated strategy" : "Awaiting validated evidence";
        const strategyId = String(strategy.strategy_family_id || strategy.label || "strategy");
        const isOpen = readStrategyState().openIds.includes(strategyId);
        return `
            <details class="qwf-strategy-card ${admitted ? "is-admitted" : "is-research"}" data-qwf-strategy-card data-qwf-strategy-id="${escapeHtml(strategyId)}" ${isOpen ? "open" : ""}>
                <summary>
                    <div>
                        <span>${admitted ? "Admitted core strategy" : "Core research playbook"}</span>
                        <strong>${escapeHtml(strategy.label)}</strong>
                        <p>${escapeHtml(strategy.thesis)}</p>
                        <p class="qwf-strategy-pattern-preview"><b>${escapeHtml(patternCount)} recognised ${patternCount === 1 ? "relationship" : "relationships"}</b><i aria-hidden="true">·</i><b>Top research score ${escapeHtml(Number(strategy.top_research_score || 0).toFixed(3))}</b></p>
                    </div>
                    <aside>
                        <em class="${admitted ? "is-positive" : "is-waiting"}">${escapeHtml(statusLabel)}</em>
                        <span class="qsase-card-expand" aria-hidden="true"><b>Expand Strategy</b><i></i></span>
                    </aside>
                </summary>
                <div class="qwf-strategy-body">
                    <section class="qwf-strategy-pattern-lineage">
                        <header><span>Patterns feeding this strategy</span><h4>${escapeHtml(patternCount)} research ${patternCount === 1 ? "question is" : "questions are"} shaping this playbook</h4><p>A research score ranks which relationship Qadam should investigate first. The lifecycle label shows how far that relationship has actually progressed.</p></header>
                        <div>${patterns.length ? patterns.map(renderStrategyPattern).join("") : `<article class="qwf-empty-state"><strong>No pattern lineage is available</strong><p>This playbook cannot advance until a recognised relationship is attached.</p></article>`}</div>
                    </section>
                    <div class="qwf-strategy-explainer">
                        <section><span>How this strategy works</span><p>${escapeHtml(strategy.thesis)}</p></section>
                        <section><span>What Qadam watches</span><p>${escapeHtml(strategy.catalyst)}</p></section>
                    </div>
                    <div class="qwf-strategy-instrument-map">
                        ${renderInstrumentGroup("Core instruments", strategy.core_instruments, "The primary instruments Qadam could use to express this strategy if its edge is validated and the Decision Room passes the setup.")}
                        ${renderInstrumentGroup("Secondary instruments", strategy.secondary_instruments, "Related assets used for confirmation, comparison, or an alternative proxy. Some may remain research-only.")}
                    </div>
                    <dl class="qwf-strategy-rules">
                        <div><dt>What would confirm it</dt><dd>${escapeHtml(strategy.confirmation)}</dd></div>
                        <div><dt>What would disprove it</dt><dd>${escapeHtml(strategy.invalidation)}</dd></div>
                        <div><dt>How a later trade would be governed</dt><dd>${escapeHtml(strategy.entry)}</dd></div>
                        <div><dt>How a later position could end</dt><dd>${escapeHtml(strategy.exits)}</dd></div>
                        <div><dt>What blocks it now</dt><dd>${escapeHtml(strategy.present_blocker)}</dd></div>
                        <div><dt>Next research action</dt><dd>${escapeHtml(strategy.next_action)}</dd></div>
                    </dl>
                    <section class="qwf-strategy-lineage">
                        <span>Evidence route</span>
                        <p>Found through ${escapeHtml(origins.map(human).join(", "), "no exported discovery lane")}. Current validation contribution: ${escapeHtml(contributions.map(human).join(", "), "not tested")}.</p>
                        <p>Strongest source inputs: ${escapeHtml(list(strategy.source_inputs).map(human).join(", "), "not exported")}.</p>
                        <nav>
                            <a href="${routeHref(strategy.pattern_recognition_route)}" data-qsase-route data-qsase-module-target="patterns" data-qsase-view-target="findings">Open Pattern Recognition</a>
                            ${strategy.quantum_edge_route ? `<a href="${routeHref(strategy.quantum_edge_route)}" data-qsase-route data-qsase-module-target="patterns" data-qsase-view-target="nonlinear">Open Quantum Edge evidence</a>` : ""}
                            <a href="/dashboard/?module=decide&amp;view=decision" data-qsase-route data-qsase-module-target="decide" data-qsase-view-target="decision">Continue to Decision Room</a>
                        </nav>
                    </section>
                </div>
            </details>
        `;
    }

    function renderTradingStrategies(section) {
        const core = list(section.core_playbooks).length
            ? list(section.core_playbooks)
            : [...list(section.admitted_strategies), ...list(section.research_playbooks)];
        const emerging = list(section.emerging_strategy_candidates);
        const progression = list(section.strategy_progression);
        return `
            <section class="qwf-view qwf-trading-strategies" data-qwf-view="trading-strategies">
                <header class="qwf-page-header qwf-strategy-page-header">
                    <div><span>${escapeHtml(section.eyebrow || "Pattern-to-Strategy Architecture")}</span><h2>Trading Strategies</h2><p>${escapeHtml(section.headline)}. ${escapeHtml(section.plain_english_summary)}</p></div>
                </header>
                <section class="qwf-strategy-progression" aria-labelledby="qwf-strategy-progression-title">
                    <header><span>From pattern to strategy</span><h3 id="qwf-strategy-progression-title">How evidence advances into a trading playbook</h3><p>A pattern is a research question. A strategy is the bounded plan Qadam may use only after that question survives independent testing.</p></header>
                    <ol>${progression.map((stage) => `<li><span>${escapeHtml(stage.sequence)}</span><div><strong>${escapeHtml(stage.label)}</strong><p>${escapeHtml(stage.summary)}</p></div></li>`).join("")}</ol>
                </section>
                <section class="qwf-strategy-admission" aria-label="Current strategy admission state">
                    <article><span>Core families</span><strong>${escapeHtml(section.core_strategy_count || core.length)}</strong><p>Known playbooks Qadam can refine.</p></article>
                    <article class="is-waiting"><span>Validated strategies</span><strong>${escapeHtml(section.validated_strategy_count || 0)}</strong><p>Playbooks with a proven underlying edge.</p></article>
                    <article><span>Emerging families</span><strong>${escapeHtml(section.emerging_strategy_count || emerging.length)}</strong><p>New playbooks formed outside the core five.</p></article>
                </section>
                <section class="qwf-strategy-chapter qwf-core-strategies">
                    <header><span>Core strategy families</span><h3>Five ways Qadam knows how to investigate an edge</h3><p>These are durable research frameworks, not fixed trading rules. New pattern evidence can refine their instruments, confirmation rules, invalidation, and timing.</p></header>
                    <div class="qwf-strategy-list">${core.map((strategy) => renderStrategyCard(strategy, strategy.admission_state === "validated_strategy")).join("")}</div>
                </section>
                <section class="qwf-strategy-chapter qwf-emerging-strategies">
                    <header><span>Emerging strategy families</span><h3>Patterns that do not fit the existing five</h3><p>Qadam is not limited to its core playbooks. A genuinely supported relationship can propose a new family, but it must clear the same evidence and governance standards.</p></header>
                    ${emerging.length ? `<div class="qwf-emerging-list">${emerging.map((candidate) => `<article><span>${escapeHtml(candidate.lifecycle_label)}</span><strong>${escapeHtml(candidate.label)}</strong><p>${escapeHtml(candidate.relationship)}</p><small>${escapeHtml(candidate.next_action)}</small></article>`).join("")}</div>` : `<article class="qwf-empty-state"><strong>No new strategy family has earned admission yet</strong><p>Every current relationship maps to one of the five core playbooks. If a validated relationship falls outside them, it will appear here before governed review.</p><a href="${routeHref({module_id: "patterns", view_id: "findings"})}" data-qsase-route data-qsase-module-target="patterns" data-qsase-view-target="findings">Review the pattern library</a></article>`}
                </section>
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
        if (viewName === "pattern-recognition") capturePatternState(panel);
        panel.dataset.qadamWaveFHash = projection.content_hash;
        panel.dataset.qadamWaveFView = viewName;
        const lifecycle = Array.from(panel.children).find((child) => child.matches("[data-qadam-lifecycle]"));
        const handoff = Array.from(panel.children).find((child) => child.matches("[data-qsase-flow-handoff]"));
        Array.from(panel.children).forEach((child) => {
            if (child !== lifecycle && child !== handoff) child.remove();
        });
        if (handoff) handoff.insertAdjacentHTML("beforebegin", html);
        else panel.insertAdjacentHTML("beforeend", html);
        if (viewName === "pattern-recognition") {
            const root = panel.querySelector("[data-qwf-view='pattern-recognition']");
            if (root) initializePatternView(root);
        }
        if (viewName === "trading-strategies") {
            const root = panel.querySelector("[data-qwf-view='trading-strategies']");
            if (root) initializeStrategyView(root);
        }
    }

    function applyProjection() {
        applyScheduled = false;
        if (!projection) return;
        NAVIGATION_LABELS.forEach(([moduleId, viewId, label, previousLabels]) => updateNavigationLabel(moduleId, viewId, label, previousLabels));
        updateCurrentViewLabel();
        replacePanel(VIEW_SELECTORS.pattern, renderPatternRecognition(projection.pattern_recognition || {}), "pattern-recognition");
        replacePanel(VIEW_SELECTORS.strategies, renderTradingStrategies(projection.trading_strategies || {}), "trading-strategies");
        document.documentElement.dataset.qadamWaveF = "rendered";
    }

    function scheduleApply() {
        if (applyScheduled) return;
        applyScheduled = true;
        window.requestAnimationFrame(applyProjection);
    }

    function capturePatternState(container = document) {
        const root = container.matches?.("[data-qwf-view='pattern-recognition']")
            ? container
            : container.querySelector?.("[data-qwf-view='pattern-recognition']");
        if (!root) return readPatternState();
        const selectedFilter = root.querySelector("[data-qwf-origin-filter][aria-selected='true']")?.dataset.qwfOriginFilter;
        const selectedSort = root.querySelector("[data-qwf-pattern-sort]")?.value;
        const explanationOpen = root.querySelector("[data-qwf-strategy-path-toggle]")?.getAttribute("aria-expanded") === "true";
        const openIds = Array.from(root.querySelectorAll("[data-qwf-pattern-card][open]"))
            .map((card) => card.dataset.qwfPatternId)
            .filter(Boolean);
        return updatePatternState({
            filter: selectedFilter || readPatternState().filter,
            sort: selectedSort || readPatternState().sort,
            visible: Number(root.dataset.qwfVisible) || readPatternState().visible,
            openIds,
            explanationOpen
        });
    }

    function patternComparator(sort) {
        const number = (card, key) => Number(card.dataset[key] || 0);
        if (sort === "newest") return (a, b) => number(b, "qwfObserved") - number(a, "qwfObserved") || number(a, "qwfRank") - number(b, "qwfRank");
        if (sort === "highest_score") return (a, b) => number(b, "qwfScore") - number(a, "qwfScore") || number(a, "qwfRank") - number(b, "qwfRank");
        if (sort === "closest_to_validation") return (a, b) => {
            const tier = (card) => card.dataset.qwfFixture === "true" ? 2 : card.dataset.qwfValidated === "true" ? 0 : 1;
            return tier(a) - tier(b) || number(b, "qwfScore") - number(a, "qwfScore");
        };
        if (sort === "title") return (a, b) => String(a.dataset.qwfTitle || "").localeCompare(String(b.dataset.qwfTitle || ""));
        return (a, b) => number(a, "qwfRank") - number(b, "qwfRank");
    }

    function applyPatternView(root) {
        const state = readPatternState();
        const listRoot = root.querySelector("[data-qwf-pattern-list]");
        if (!listRoot) return;
        const cards = Array.from(listRoot.querySelectorAll("[data-qwf-pattern-card]"));
        const empty = root.querySelector("[data-qwf-filter-empty]");
        cards.sort(patternComparator(state.sort)).forEach((card) => listRoot.insertBefore(card, empty));
        const matching = cards.filter((card) => state.filter === "all" || card.dataset.qwfOrigin === state.filter);
        const visibleLimit = Math.max(PATTERN_PAGE_SIZE, Number(state.visible) || PATTERN_PAGE_SIZE);
        cards.forEach((card) => {
            const index = matching.indexOf(card);
            card.hidden = index < 0 || index >= visibleLimit;
        });
        root.dataset.qwfVisible = String(visibleLimit);
        root.querySelectorAll("[data-qwf-origin-filter]").forEach((control) => {
            control.setAttribute("aria-selected", control.dataset.qwfOriginFilter === state.filter ? "true" : "false");
        });
        const select = root.querySelector("[data-qwf-pattern-sort]");
        if (select && Array.from(select.options).some((option) => option.value === state.sort)) select.value = state.sort;
        if (empty) empty.hidden = matching.length > 0;
        const more = root.querySelector("[data-qwf-view-more]");
        if (more) {
            more.hidden = matching.length <= PATTERN_PAGE_SIZE;
            more.textContent = visibleLimit < matching.length ? "View More +" : "Show Less";
            more.dataset.qwfExpanded = visibleLimit < matching.length ? "false" : "true";
        }
    }

    function initializePatternView(root) {
        let state = readPatternState();
        const supportedFilters = Array.from(root.querySelectorAll("[data-qwf-origin-filter]"))
            .map((button) => button.dataset.qwfOriginFilter);
        const select = root.querySelector("[data-qwf-pattern-sort]");
        const supportedSorts = Array.from(select?.options || []).map((option) => option.value);
        if (!supportedFilters.includes(state.filter) || !supportedSorts.includes(state.sort)) {
            state = updatePatternState({
                filter: supportedFilters.includes(state.filter) ? state.filter : "all",
                sort: supportedSorts.includes(state.sort) ? state.sort : "recommended"
            });
        }
        const pathToggle = root.querySelector("[data-qwf-strategy-path-toggle]");
        const pathGuidance = root.querySelector("[data-qwf-strategy-path]");
        if (pathToggle && pathGuidance) {
            pathToggle.setAttribute("aria-expanded", state.explanationOpen ? "true" : "false");
            pathGuidance.hidden = !state.explanationOpen;
        }
        root.querySelectorAll("[data-qwf-pattern-card]").forEach((card) => {
            card.open = state.openIds.includes(String(card.dataset.qwfPatternId));
            if (card.dataset.qwfToggleReady === "true") return;
            card.dataset.qwfToggleReady = "true";
            card.addEventListener("toggle", () => {
                const openIds = Array.from(root.querySelectorAll("[data-qwf-pattern-card][open]"))
                    .map((row) => row.dataset.qwfPatternId)
                    .filter(Boolean);
                updatePatternState({ openIds });
            });
        });
        applyPatternView(root);
    }

    function initializeStrategyView(root) {
        const state = readStrategyState();
        root.querySelectorAll("[data-qwf-strategy-card]").forEach((card) => {
            card.open = state.openIds.includes(String(card.dataset.qwfStrategyId));
            if (card.dataset.qwfToggleReady === "true") return;
            card.dataset.qwfToggleReady = "true";
            card.addEventListener("toggle", () => {
                const openIds = Array.from(root.querySelectorAll("[data-qwf-strategy-card][open]"))
                    .map((row) => row.dataset.qwfStrategyId)
                    .filter(Boolean);
                writeStrategyState({ openIds });
            });
        });
    }

    function ensureTooltip() {
        let tooltip = document.querySelector("[data-qwf-floating-tooltip]");
        if (tooltip) return tooltip;
        tooltip = document.createElement("div");
        tooltip.className = "qwf-floating-tooltip";
        tooltip.dataset.qwfFloatingTooltip = "true";
        tooltip.id = "qwf-floating-tooltip";
        tooltip.setAttribute("role", "tooltip");
        tooltip.hidden = true;
        document.body.appendChild(tooltip);
        return tooltip;
    }

    function positionTooltip(trigger, tooltip) {
        const rect = trigger.getBoundingClientRect();
        const edge = 12;
        const gap = 10;
        tooltip.style.maxWidth = `${Math.min(360, window.innerWidth - edge * 2)}px`;
        const width = tooltip.offsetWidth;
        const height = tooltip.offsetHeight;
        let left = rect.left + rect.width / 2 - width / 2;
        left = Math.max(edge, Math.min(left, window.innerWidth - width - edge));
        let top = rect.bottom + gap;
        if (top + height > window.innerHeight - edge) top = Math.max(edge, rect.top - height - gap);
        tooltip.style.left = `${Math.round(left)}px`;
        tooltip.style.top = `${Math.round(top)}px`;
    }

    function showTooltip(trigger, pinned = false) {
        const copy = trigger?.dataset?.qwfTooltip;
        if (!copy) return;
        const tooltip = ensureTooltip();
        activeTooltipTrigger = trigger;
        activeTooltipPinned = pinned;
        tooltip.textContent = copy;
        tooltip.hidden = false;
        trigger.setAttribute("aria-describedby", tooltip.id);
        window.requestAnimationFrame(() => positionTooltip(trigger, tooltip));
    }

    function hideTooltip(trigger = activeTooltipTrigger) {
        const tooltip = document.querySelector("[data-qwf-floating-tooltip]");
        if (trigger) trigger.removeAttribute("aria-describedby");
        if (tooltip) tooltip.hidden = true;
        if (!trigger || trigger === activeTooltipTrigger) {
            activeTooltipTrigger = null;
            activeTooltipPinned = false;
        }
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
        const tooltipTrigger = event.target?.closest?.("[data-qwf-tooltip]");
        if (tooltipTrigger) {
            event.preventDefault();
            event.stopPropagation();
            if (activeTooltipTrigger === tooltipTrigger && activeTooltipPinned) hideTooltip(tooltipTrigger);
            else showTooltip(tooltipTrigger, true);
            return;
        }
        if (activeTooltipTrigger) hideTooltip();
        const pathToggle = event.target?.closest?.("[data-qwf-strategy-path-toggle]");
        if (pathToggle) {
            const root = pathToggle.closest("[data-qwf-view='pattern-recognition']");
            const guidance = root?.querySelector("[data-qwf-strategy-path]");
            const expanded = pathToggle.getAttribute("aria-expanded") === "true";
            const nextExpanded = !expanded;
            pathToggle.setAttribute("aria-expanded", nextExpanded ? "true" : "false");
            pathToggle.textContent = `${projection?.pattern_recognition?.strategy_path_explainer?.label || "How a recognised pattern becomes a trading strategy"} ${nextExpanded ? "−" : "+"}`;
            if (guidance) guidance.hidden = !nextExpanded;
            updatePatternState({ explanationOpen: nextExpanded });
            return;
        }
        const filter = event.target?.closest?.("[data-qwf-origin-filter]");
        if (filter) {
            const root = filter.closest("[data-qwf-view='pattern-recognition']");
            updatePatternState({ filter: filter.dataset.qwfOriginFilter, visible: PATTERN_PAGE_SIZE });
            applyPatternView(root);
            return;
        }
        const more = event.target?.closest?.("[data-qwf-view-more]");
        if (more) {
            const root = more.closest("[data-qwf-view='pattern-recognition']");
            const state = readPatternState();
            const nextVisible = more.dataset.qwfExpanded === "true"
                ? PATTERN_PAGE_SIZE
                : state.visible + PATTERN_PAGE_SIZE;
            updatePatternState({ visible: nextVisible });
            applyPatternView(root);
        }
    });
    document.addEventListener("change", (event) => {
        const select = event.target?.closest?.("[data-qwf-pattern-sort]");
        if (!select) return;
        const root = select.closest("[data-qwf-view='pattern-recognition']");
        updatePatternState({ sort: select.value, visible: PATTERN_PAGE_SIZE });
        applyPatternView(root);
    });
    document.addEventListener("mouseover", (event) => {
        const trigger = event.target?.closest?.("[data-qwf-tooltip]");
        if (trigger && (!activeTooltipPinned || trigger !== activeTooltipTrigger)) showTooltip(trigger);
    });
    document.addEventListener("mouseout", (event) => {
        const trigger = event.target?.closest?.("[data-qwf-tooltip]");
        if (!activeTooltipPinned && trigger && !trigger.contains(event.relatedTarget)) hideTooltip(trigger);
    });
    document.addEventListener("focusin", (event) => {
        const trigger = event.target?.closest?.("[data-qwf-tooltip]");
        if (trigger) showTooltip(trigger);
    });
    document.addEventListener("focusout", (event) => {
        const trigger = event.target?.closest?.("[data-qwf-tooltip]");
        if (!activeTooltipPinned && trigger) hideTooltip(trigger);
    });
    document.addEventListener("keydown", (event) => {
        if (event.key === "Escape") hideTooltip();
    });
    window.addEventListener("resize", () => hideTooltip());
    window.addEventListener("scroll", () => hideTooltip(), true);
    observer = new MutationObserver(scheduleApply);
    observer.observe(document.body, { childList: true, subtree: true });
    window.addEventListener("popstate", scheduleApply);
    window.QadamWaveF = {
        statusUrl: STATUS_URL,
        apply: scheduleApply,
        getProjection: () => projection,
        refreshPatternView: () => {
            const root = document.querySelector("[data-qwf-view='pattern-recognition']");
            if (root) initializePatternView(root);
        },
        disconnect: () => observer?.disconnect()
    };
    loadProjection();
})();
