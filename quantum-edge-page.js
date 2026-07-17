(() => {
    "use strict";

    const STATUS_URL = "/status/quantum-edge-page.json?v=20260717-learn-improve-final-polish-v1";
    const SCHEMA_VERSION = "qadam.QuantumEdgeThreeLayerPage.v1";
    const CONTRACT_VERSION = "quantum-edge-elegant-v1";
    const PANEL_SELECTOR = '[data-qsase-module-panel="patterns"][data-qsase-view-panel="nonlinear"]';
    const ROOT_SELECTOR = "[data-quantum-edge-page]";
    const PRIMARY_IDS = ["evidence", "consequence", "answer"];
    const PAGE_EYEBROW = "Quantum Benchmark Framework";
    const PURPOSE_COPY = "Not every pattern needs quantum analysis. It is used when a relationship might involve complicated interactions, sequencing, regimes or path dependence that simpler analysis could miss. Quantum Edge is Qadam’s independent proof room for deciding whether a nonlinear or quantum-assisted method genuinely contributes something that the best conventional method missed. The framework presents the experiment record first, then any strategy and paper impact, and closes with the formal market-level verdict.";
    const GUIDANCE_WORKFLOW_STEPS = [
        { key: "evidence_assembly", label: "Evidence assembly", title: "Python prepares the evidence", description: "Qadam aligns prices, timestamps, source signals, instruments, and market regimes into a structured point-in-time dataset." },
        { key: "classical_discovery", label: "Classical discovery", title: "Classical models search for patterns", description: "They identify lead-lag relationships, divergences, correlations, breakouts, and regime changes." },
        { key: "quantum_exploration", label: "Quantum exploration", title: "The quantum lane examines selected problems", description: "Quantum-assisted methods test nonlinear, sequential, and path-dependent structure that classical analysis may have missed. This lane may originate a new candidate relationship; it does not merely review classical output." },
        { key: "matched_comparison", label: "Matched comparison", title: "Both lanes are compared fairly", description: "The same frozen evidence and decision rules are applied to the strongest classical and quantum-assisted methods to isolate any incremental signal." },
        { key: "ordinary_validation", label: "Standard validation", title: "Ordinary validation still applies", description: "Any quantum-originated pattern must survive historical testing, untouched data, trading costs, forward observation, and strategy validation before it can influence paper trading." }
    ];
    const GUIDANCE_OPERATING_MODEL = {
        label: "Operating model",
        title: "Hybrid by design—not a standalone quantum computer.",
        body: "Even when genuine IBM hardware is used, classical computing remains essential. It prepares the data, constructs circuits, submits jobs, decodes measurements, runs matched comparisons, and operates Qadam."
    };
    const GUIDANCE_CURRENT_CAPABILITY = {
        label: "Current capability",
        title: "Experimental pathway implemented; IBM hardware proof pending.",
        body: "Qadam has reproduced its quantum experiment through local simulation and can access the configured Q-CTRL/IBM provider path. No IBM hardware experiment has been authorized, submitted, or executed. The quantum lane is therefore an implemented experimental pathway—not yet a hardware-proven pattern-discovery engine."
    };
    const GUIDANCE_PROOF_STEPS = [
        { key: "technology_access", label: "Infrastructure readiness", question: "Can Qadam access the required technology?", meaning: "Confirms that the required tools and providers are available. This establishes access only; it does not show that an experiment ran." },
        { key: "hardware_execution", label: "Hardware execution", question: "Was an actual hardware experiment executed?", meaning: "Distinguishes a real quantum-hardware job from a local simulation or a prepared test." },
        { key: "reproducibility", label: "Result reproducibility", question: "Can the result be reproduced?", meaning: "Checks whether the same method produces the same result again, rather than a one-off outcome." },
        { key: "classical_comparison", label: "Matched classical benchmark", question: "Did it beat the strongest fair classical comparison?", meaning: "Compares the quantum-assisted method with Qadam’s strongest conventional method using the same evidence and rules." },
        { key: "untouched_market_data", label: "Untouched holdout validation", question: "Did that advantage survive completely untouched market data?", meaning: "Checks whether the advantage remains on market data that was never used to develop or tune the method." },
        { key: "governed_paper_impact", label: "Governed paper-decision impact", question: "Did it ultimately improve a governed paper decision?", meaning: "Asks whether the added evidence materially improved a paper decision while Qadam’s normal governance and risk controls remained in place." }
    ];
    const GUIDANCE_OUTCOME_STATES = [
        { key: "evidence_strengthened", label: "Incremental quantum evidence", description: "The quantum-assisted method finds useful information beyond the strongest conventional method." },
        { key: "joint_corroboration", label: "Corroborated classical signal", description: "Quantum supports the same conclusion as the conventional method, but does not show a unique advantage." },
        { key: "classical_preferred", label: "Classical method preferred", description: "The conventional method performs equally well or better." },
        { key: "pattern_weakened", label: "Original thesis weakened", description: "The more demanding test reduces confidence in the relationship Qadam originally found." },
        { key: "not_measurable", label: "Insufficient evidence", description: "Required evidence is missing, so the contribution cannot yet be measured." }
    ];
    const GUIDANCE_TAKEAWAY = {
        label: "Research reminder",
        title: "A classical-preferred result is a successful research outcome.",
        body: "It shows that the conventional method explains the evidence as well as or better than the more complex approach, allowing Qadam to avoid unsupported complexity."
    };
    const HELP_FALLBACKS = {
        proof_state: "A market-level quantum edge has not been proven. Qadam has shown that its testing process works, but it has not shown that a quantum-assisted method improves predictions on real untouched market evidence.",
        engineering_control: "This is a known-answer synthetic test. Qadam deliberately used data containing a relationship it already knew was there, then checked whether the classical and local quantum methods could recover it. Passing shows that the test machinery works; it does not prove a market edge.",
        local_quantum_simulation: "This ran on a simulator, not IBM quantum hardware. It demonstrates that the software path and circuit logic can be reproduced, but it does not establish quantum-hardware performance or market advantage.",
        engineering_mechanism: "These checks test the experimental machinery. They cover frozen inputs, reproducibility, lineage, safety, and authority isolation. A complete engineering score certifies the test rig, not predictive or investment performance.",
        paired_scores: "Read these scores together. The engineering score says whether the experimental test rig works. The market-proof score says whether the investment claim has evidence. It is like proving an engine works on a test bench without yet proving that it wins races.",
        provider_access: "Access is not execution. This confirms that Qadam can reach the configured provider path. It does not mean a quantum circuit was run or that a result exists.",
        hardware_execution: "The current record must separately show whether an IBM hardware experiment was authorized, submitted, completed, and verified. A prepared circuit manifest and a local simulation are not hardware execution.",
        untouched_holdout: "An untouched holdout is market history kept completely out of discovery and tuning, then opened only for the final test. Without eligible untouched evidence, Qadam cannot fairly measure whether either method generalizes to unseen markets.",
        matched_comparison: "No winner exists until both methods are tested on the same unseen evidence. If the fair comparison has not run, the result is not measurable; it is neither a quantum loss nor a classical win.",
        classical_preferred: "This is a useful scientific result. It means the simpler conventional method explains the evidence just as well as, or better than, the more complicated method. Qadam should prefer the simpler method.",
        classified_windows: "Classified windows have been inspected and categorized. Eligible holdout windows also satisfy the stricter point-in-time, completeness, and independence rules required for a fair final test. A large classified count does not imply usable holdout evidence.",
        provider_history: "Provider-history rows are raw time-stamped records received from a data provider. Completed partitions are validated, coherent groups that are ready for point-in-time testing. Raw rows in incomplete or failing partitions cannot create eligible holdout evidence by themselves.",
        strategy_influence: "No strategy may change because of quantum evidence until the contribution passes independent market validation. A simulator, synthetic fixture, provider connection, or prepared hardware manifest cannot influence a governed strategy.",
        paper_outcome: "This count changes only after validated evidence affects a governed paper decision and the resulting paper outcome is recorded. A zero means no paper decision or result can currently be traced to validated quantum evidence."
    };

    let projection = null;
    let loadPromise = null;
    let loadFailed = false;
    let observer = null;
    let applyScheduled = false;
    let introExpanded = false;
    let handledHash = "";
    let helpCloseTimer = 0;
    let activeHelp = null;
    let routeWasActive = false;
    let forceFreshRender = false;
    let primaryOpenState = { evidence: false, consequence: false, answer: false };
    let technicalOpen = false;

    function list(value) {
        return Array.isArray(value) ? value : [];
    }

    function records(value) {
        if (Array.isArray(value)) return value;
        if (!value || typeof value !== "object") return [];
        return Object.entries(value).map(([key, item]) => (
            item && typeof item === "object" ? { key, ...item } : { key, value: item }
        ));
    }

    function escapeHtml(value, fallback = "") {
        return String(value ?? fallback)
            .replace(/&/g, "&amp;")
            .replace(/</g, "&lt;")
            .replace(/>/g, "&gt;")
            .replace(/"/g, "&quot;")
            .replace(/'/g, "&#039;");
    }

    function text(value, fallback = "Not available") {
        if (value === 0 || value === false) return String(value);
        const result = String(value || "").trim();
        return result || fallback;
    }

    function guidanceText(value, fallback = "Not available") {
        return text(value, fallback)
            .replace(/[—–−]/g, " - ")
            .replace(/\s+-\s+/g, " - ");
    }

    function human(value, fallback = "Not available") {
        const raw = text(value, "");
        if (!raw) return fallback;
        const normalized = raw === "classically_dominated" ? "classical_preferred" : raw;
        const mapped = {
            not_measurable: "Not measurable yet",
            waiting_for_evidence: "Waiting for evidence",
            not_run: "Not run",
            source_truth_conflict: "Source truth conflict",
            classical_preferred: "Classical preferred",
            local_quantum_simulation: "Local quantum simulation"
        }[normalized];
        if (mapped) return mapped;
        return normalized
            .replace(/[_-]+/g, " ")
            .replace(/\s+/g, " ")
            .replace(/^./, (character) => character.toUpperCase());
    }

    function number(value, fallback = 0) {
        const parsed = Number(value);
        return Number.isFinite(parsed) ? parsed : fallback;
    }

    function routeIsActive() {
        const params = new URLSearchParams(window.location.search);
        return params.get("module") === "patterns" && params.get("view") === "nonlinear";
    }

    function validProjection(payload) {
        if (!payload || typeof payload !== "object") return false;
        if (payload.schema_version !== SCHEMA_VERSION || payload.contract_version !== CONTRACT_VERSION) return false;
        if (!/^[a-f0-9]{64}$/i.test(String(payload.content_hash || ""))) return false;
        if (!/^[a-f0-9]{64}$/i.test(String(payload.render_contract_hash || ""))) return false;
        if (payload.page_copy?.eyebrow !== PAGE_EYEBROW || payload.page_copy?.title !== "Quantum Edge" || payload.page_copy?.subtitle !== PURPOSE_COPY || payload.page_copy?.conclusion_label !== "Current conclusion") return false;
        const axes = payload.state_axes;
        const presentation = payload.presentation;
        if (!axes || !presentation || typeof axes !== "object" || typeof presentation !== "object") return false;
        if (!["proof", "comparison", "execution", "downstream", "freshness"].every((key) => axes[key] && typeof axes[key] === "object")) return false;
        if (JSON.stringify(presentation.section_order) !== JSON.stringify(PRIMARY_IDS)) return false;
        if (!["evidence", "consequence", "answer"].every((key) => presentation.rows?.[key]?.id === key && presentation.rows[key].collapsed_by_default === true)) return false;
        if (!presentation.evidence || !presentation.impact || !presentation.verdict || !presentation.technical_record) return false;
        if (!["shared_basis", "conventional_lane", "quantum_lane", "matched_outcome"].every((key) => presentation.evidence[key] && typeof presentation.evidence[key] === "object")) return false;
        if (!presentation.impact.headline || !presentation.verdict.next_evidence) return false;
        if (list(presentation.evidence.facts).length > 3) return false;
        if (presentation.technical_record.closed_by_default !== true) return false;
        const gates = list(presentation.impact.gates);
        if (gates.length !== 4) return false;
        if (JSON.stringify(gates.map((gate) => gate.key)) !== JSON.stringify(["experiment_works", "hardware_evidence_exists", "market_comparison_holds_up", "downstream_decision_improved"])) return false;
        if (list(presentation.verdict.metrics).length !== 3) return false;
        const comparison = axes.comparison;
        const execution = axes.execution;
        const downstream = axes.downstream;
        const proof = axes.proof;
        const freshness = axes.freshness;
        const matched = presentation.evidence.matched_outcome || {};
        const quantumLane = presentation.evidence.quantum_lane || {};
        const impact = presentation.impact.headline || {};
        const verdict = presentation.verdict || {};
        if (matched.key !== comparison.key || matched.label !== comparison.label || matched.summary !== comparison.summary || matched.eligible !== comparison.eligible) return false;
        if (quantumLane.state !== execution.key || quantumLane.state_label !== execution.label || quantumLane.summary !== execution.summary || quantumLane.execution_mode !== execution.execution_mode) return false;
        if (impact.key !== downstream.key || impact.label !== downstream.label || impact.summary !== downstream.summary || impact.strategy_count !== downstream.strategy_count || impact.paper_decision_count !== downstream.paper_decision_count) return false;
        if (verdict.proof_state !== proof.key || verdict.proof_state_label !== proof.label) return false;
        if (verdict.comparison_state !== comparison.key || verdict.comparison_label !== comparison.label) return false;
        if (verdict.scientific_verdict !== comparison.key || verdict.scientific_verdict_label !== comparison.label) return false;
        if (verdict.freshness_state !== freshness.key || verdict.freshness_label !== freshness.label) return false;
        return list(presentation.technical_record.index).length > 0;
    }

    function canonicalJson(value) {
        if (value === null || typeof value !== "object") {
            const encoded = JSON.stringify(value);
            return typeof encoded === "string"
                ? encoded.replace(/[\u007f-\uffff]/g, (character) => `\\u${character.charCodeAt(0).toString(16).padStart(4, "0")}`)
                : "null";
        }
        if (Array.isArray(value)) return `[${value.map(canonicalJson).join(",")}]`;
        return `{${Object.keys(value).sort().map((key) => `${canonicalJson(key)}:${canonicalJson(value[key])}`).join(",")}}`;
    }

    async function projectionHashMatches(payload) {
        if (!window.crypto?.subtle || typeof window.TextEncoder !== "function") return false;
        const sourceContentHashes = Object.fromEntries(list(payload.source_artifacts).filter((row) => row && typeof row === "object" && text(row.source_id, "")).map((row) => [text(row.source_id), text(row.content_hash, "")]));
        const material = {
            content_hash: payload.content_hash,
            schema_version: payload.schema_version,
            contract_version: payload.contract_version,
            projection_status: payload.projection_status,
            page_copy: payload.page_copy,
            state_axes: payload.state_axes,
            presentation: payload.presentation,
            source_content_hashes: sourceContentHashes
        };
        const digest = await window.crypto.subtle.digest("SHA-256", new window.TextEncoder().encode(canonicalJson(material)));
        const hash = Array.from(new Uint8Array(digest), (byte) => byte.toString(16).padStart(2, "0")).join("");
        return hash === String(payload.render_contract_hash || "").toLowerCase();
    }

    async function projectionAccepted(payload) {
        return validProjection(payload) && await projectionHashMatches(payload);
    }

    function tone(value) {
        const state = String(value || "").toLowerCase();
        if (/failed|decayed|conflict|error|rejected/.test(state)) return "negative";
        if (/blocked|waiting|pending|partial|prepared|incomplete|unproven|not[_ ]measurable|not[_ ]run|not[_ ]reached|unavailable|missing|provisional/.test(state)) return "waiting";
        if (/validated|verified|complete|passed|reproduced|strengthened|available/.test(state)) return "positive";
        if (/quantum|simulation/.test(state)) return "quantum";
        return "neutral";
    }

    function scoreLabel(block) {
        if (!block || block.available === false) return text(block?.score_label, "Unavailable");
        if (block.score_label) return text(block.score_label);
        const passed = block.pass_count ?? block.passed_count;
        const total = block.check_count ?? block.total_count;
        if (passed === null || passed === undefined || total === null || total === undefined) return "Unavailable";
        return `${passed}/${total}`;
    }

    function countOf(block, names, fallback = 0) {
        for (const name of names) {
            if (block && block[name] !== null && block[name] !== undefined) return number(block[name], fallback);
        }
        return fallback;
    }

    function helpText(key, fallback, dynamicFallback = "") {
        const help = projection?.plain_english_help || {};
        const candidate = help[key];
        if (typeof candidate === "string" && candidate.trim()) return candidate.trim();
        if (candidate && typeof candidate === "object") {
            const copy = candidate.text || candidate.summary || candidate.explanation || candidate.copy;
            if (typeof copy === "string" && copy.trim()) return copy.trim();
        }
        return dynamicFallback || HELP_FALLBACKS[fallback] || fallback;
    }

    function marketProofHelp(block) {
        const supplied = helpText("market_proof_prerequisites", "", "");
        if (supplied) return supplied;
        if (!block || block.available === false) {
            return "These checks test what is required before Qadam may claim market value. The current prerequisite score is unavailable because its source records conflict, so Qadam fails closed instead of displaying a misleading pass count.";
        }
        const checks = list(block.checks);
        const passed = checks.filter((row) => row.passed === true).map((row) => human(row.label || row.key));
        const missing = checks.filter((row) => row.passed !== true).map((row) => human(row.label || row.key));
        const passedCopy = passed.length ? `Currently passed: ${passed.join(", ")}.` : "No prerequisite currently passes.";
        const missingCopy = missing.length ? `Still required: ${missing.join(", ")}.` : "No prerequisite is currently missing.";
        return `These checks test what is still required before Qadam may claim market value. ${passedCopy} ${missingCopy} Provider access alone is not an IBM experiment or a market advantage.`;
    }

    function primaryState() {
        return { ...primaryOpenState };
    }

    function storePrimaryState(root) {
        if (!root) return;
        PRIMARY_IDS.forEach((id) => {
            primaryOpenState[id] = Boolean(root.querySelector(`[data-qep-primary="${id}"]`)?.open);
        });
    }

    function resetDisclosureState() {
        primaryOpenState = { evidence: false, consequence: false, answer: false };
        technicalOpen = false;
        introExpanded = false;
    }

    function renderHelp(instanceKey, accessibleLabel, copy) {
        const id = `qep-help-${instanceKey.replace(/[^a-z0-9-]+/gi, "-").toLowerCase()}`;
        return `
            <span class="qep-help" data-qep-help>
                <button type="button" class="qep-help-trigger" data-qep-help-trigger data-qep-focus-key="help-${escapeHtml(instanceKey)}" aria-label="${escapeHtml(accessibleLabel)}" aria-expanded="false" aria-controls="${id}" aria-describedby="${id}"><span aria-hidden="true">i</span></button>
                <span id="${id}" class="qep-help-popover" data-qep-help-popover role="tooltip" hidden>${escapeHtml(copy)}</span>
            </span>
        `;
    }

    function renderStatusChip(label, state) {
        return `<span class="qep-status is-${tone(state)}"><i aria-hidden="true"></i>${escapeHtml(label)}</span>`;
    }

    function renderMetric({ label, value, description = "", state = "", helpKey = "", helpLabel = "", help = "" }) {
        return `
            <article class="qep-metric is-${tone(state)}">
                <div class="qep-metric-heading">
                    <span>${escapeHtml(label)}</span>
                    ${help ? renderHelp(helpKey, helpLabel || `Explain ${label}`, help) : ""}
                </div>
                <strong>${escapeHtml(value)}</strong>
                ${description ? `<p>${escapeHtml(description)}</p>` : ""}
            </article>
        `;
    }

    function renderList(items, emptyCopy) {
        const rows = list(items).filter((item) => item !== null && item !== undefined && text(typeof item === "object" ? item.label || item.explanation || item.summary || item.action || item.key : item, ""));
        if (!rows.length) return `<p class="qep-empty">${escapeHtml(emptyCopy)}</p>`;
        return `<ul>${rows.map((item) => {
            const rawCopy = typeof item === "object" ? item.label || item.explanation || item.summary || item.action || human(item.key) : item;
            const copy = typeof rawCopy === "string" && /^[a-z0-9_:-]+$/.test(rawCopy) ? human(rawCopy) : rawCopy;
            return `<li>${escapeHtml(copy)}</li>`;
        }).join("")}</ul>`;
    }

    function renderNested(id, label, body) {
        return `
            <section class="qep-technical-group" data-qep-technical-group="${escapeHtml(id)}">
                <h4>${escapeHtml(label)}</h4>
                <div class="qep-technical-group-body">${body}</div>
            </section>
        `;
    }

    function proofSteps(answer) {
        const ladder = answer.proof_ladder || {};
        return list(ladder.steps).length ? list(ladder.steps) : list(ladder);
    }

    function renderProofLadder(answer) {
        const steps = proofSteps(answer);
        if (!steps.length) return `<p class="qep-empty">The proof ladder is not available in the current public projection.</p>`;
        return `
            <ol class="qep-proof-ladder" aria-label="Six-stage Quantum Edge proof ladder">
                ${steps.map((step, index) => {
                    const state = step.state || step.status || "waiting_for_evidence";
                    const key = String(step.key || "");
                    let helpName = "";
                    if (/provider_configured/.test(key)) helpName = "provider_access";
                    else if (/hardware/.test(key)) helpName = "ibm_hardware";
                    else if (/reproduced/.test(key)) helpName = "local_quantum_simulation";
                    else if (/classical_baseline/.test(key)) helpName = "matched_classical_comparison";
                    else if (/untouched/.test(key)) helpName = "untouched_holdout";
                    else if (/paper_decision/.test(key)) helpName = "paper_outcome_lineage";
                    return `
                        <li class="is-${tone(state)}">
                            <span>${String(step.number || index + 1).padStart(2, "0")}</span>
                            <div><div class="qep-step-title"><strong>${escapeHtml(step.label || step.title || human(step.key))}</strong>${helpName ? renderHelp(`proof-step-${index}`, `Explain ${text(step.label, human(step.key)).toLowerCase()}`, helpText(helpName, helpName === "ibm_hardware" ? "hardware_execution" : helpName)) : ""}</div><p>${escapeHtml(step.explanation || step.summary || "No public explanation was exported.")}</p></div>
                            ${renderStatusChip(text(step.state_label || step.status_label, human(state)), state)}
                        </li>
                    `;
                }).join("")}
            </ol>
        `;
    }

    function renderScorePair(answer) {
        const engineering = answer.engineering_checks || {};
        const market = answer.market_proof_prerequisites || {};
        return `
            <section class="qep-score-section" aria-labelledby="qep-score-heading">
                <header class="qep-subhead">
                    <div><span>Two different standards</span><h3 id="qep-score-heading">Engineering readiness is not market proof</h3></div>
                    ${renderHelp("score-pair", "Explain how to read the engineering and market-proof scores together", helpText("engineering_vs_market_proof", "paired_scores"))}
                </header>
                <div class="qep-metric-pair">
                    ${renderMetric({
                        label: "Engineering mechanism",
                        value: scoreLabel(engineering),
                        description: text(engineering.summary, "Does the experimental test rig work as designed?"),
                        state: engineering.status || (engineering.available === false ? "unavailable" : "neutral"),
                        helpKey: "engineering-mechanism",
                        helpLabel: "Explain the engineering mechanism score",
                        help: helpText("engineering_mechanism", "engineering_mechanism")
                    })}
                    ${renderMetric({
                        label: "Market-proof prerequisites",
                        value: scoreLabel(market),
                        description: text(market.summary, "Is there enough independent evidence to test the investment claim?"),
                        state: market.status || (market.available === false ? "unavailable" : "waiting_for_evidence"),
                        helpKey: "market-proof-prerequisites",
                        helpLabel: "Explain the market-proof prerequisites score",
                        help: marketProofHelp(market)
                    })}
                </div>
            </section>
        `;
    }

    function renderStrongestEvidence(evidence) {
        const strongest = evidence.strongest_evidence || {};
        const route = strongest.originating_pattern_route || strongest.pattern_route || { module_id: "patterns", view_id: "findings" };
        const href = `/dashboard/?module=${encodeURIComponent(route.module_id || "patterns")}&view=${encodeURIComponent(route.view_id || "findings")}`;
        const mode = strongest.execution_mode || strongest.mode || "engineering_control";
        const localSimulationHelp = /simulat/i.test(String(mode))
            ? renderHelp("local-quantum-simulation", "Explain local quantum simulation", helpText("local_quantum_simulation", "local_quantum_simulation"))
            : "";
        return `
            <section class="qep-strongest-evidence">
                <div>
                    <div class="qep-label-with-help"><span>Strongest evidence so far</span>${renderHelp("strongest-evidence", "Explain the strongest engineering evidence", helpText("strongest_evidence", "engineering_control"))}${localSimulationHelp}</div>
                    <h3>${escapeHtml(text(strongest.title, "Known-answer engineering control"))}</h3>
                    <p>${escapeHtml(text(strongest.summary, "Classical and local quantum methods reproduced a known synthetic relationship."))}</p>
                    ${renderStatusChip(text(strongest.state_label, human(strongest.state || mode)), strongest.state || mode)}
                </div>
                <a href="${escapeHtml(href)}" data-qsase-route data-qsase-module-target="patterns" data-qsase-view-target="findings">Open originating pattern <span aria-hidden="true">→</span></a>
            </section>
        `;
    }

    function renderExperiments(evidence) {
        const experiments = list(evidence.experiments);
        const ledger = list(evidence.run_ledger || evidence.pilot?.run_ledger);
        const all = experiments.length ? experiments : ledger;
        const body = all.length ? `
            <div class="qep-record-list">
                ${all.map((row, index) => {
                    const state = row.state || row.status || "not_run";
                    const mode = row.execution_mode || row.kind || row.type || "experiment";
                    const isSimulation = /simulat|statevector|finite[_ -]shot/i.test(`${mode} ${row.title || ""}`);
                    const isHardware = /hardware|ibm|fire[_ -]?opal/i.test(`${mode} ${row.title || row.run || ""}`);
                    return `
                        <article class="qep-record is-${tone(state)}">
                            <header><div><span>${escapeHtml(text(row.kind_label || row.run || row.type_label, human(mode)))}</span><strong>${escapeHtml(text(row.title || row.label, `Experiment ${index + 1}`))}</strong></div>${renderStatusChip(text(row.state_label || row.status_label, human(state)), state)}</header>
                            <p>${escapeHtml(text(row.result || row.summary || row.explanation, "No public result was exported."))}</p>
                            ${row.boundary ? `<small>${escapeHtml(row.boundary)}</small>` : ""}
                            <div class="qep-record-help">${isSimulation ? renderHelp(`experiment-simulation-${index}`, `Explain the simulation used in ${text(row.title, `experiment ${index + 1}`)}`, helpText("local_quantum_simulation", "local_quantum_simulation")) : ""}${isHardware ? renderHelp(`experiment-hardware-${index}`, `Explain the hardware state of ${text(row.title, `experiment ${index + 1}`)}`, helpText("ibm_hardware", "hardware_execution")) : ""}</div>
                        </article>
                    `;
                }).join("")}
            </div>
        ` : `<p class="qep-empty">No experiment details were exported.</p>`;
        return renderNested("experiment-details", "Experiment details", body);
    }

    function renderMatchedComparison(evidence) {
        const comparison = evidence.matched_classical_comparison || {};
        const state = comparison.verdict || comparison.state || "not_measurable";
        return `
            <section class="qep-content-block qep-comparison">
                <header class="qep-subhead"><div><span>Matched classical comparison</span><h3>Did the nonlinear method beat the strongest fair baseline?</h3></div>${renderHelp("matched-classical-comparison", "Explain the matched classical comparison", helpText("matched_classical_comparison", "matched_comparison"))}</header>
                <p>${escapeHtml(text(comparison.plain_english_summary || comparison.summary, "No winner exists because a fair comparison on untouched market evidence has not run."))}</p>
                <dl class="qep-fact-grid">
                    <div><dt>Current comparison outcome</dt><dd>${escapeHtml(text(comparison.verdict_label || comparison.state_label, human(state)))}</dd></div>
                    <div><dt>Classical benchmark</dt><dd>${escapeHtml(human(comparison.classical_baseline || comparison.classical_method))}</dd></div>
                    <div><dt>Nonlinear or quantum method</dt><dd>${escapeHtml(human(comparison.quantum_method || comparison.nonlinear_method))}</dd></div>
                    <div><dt>What blocks the comparison</dt><dd>${escapeHtml(text(comparison.blocker, "Eligible untouched evidence is missing."))}</dd></div>
                </dl>
            </section>
        `;
    }

    function renderFairComparisonProtocol() {
        const comparison = projection.state_axes?.comparison || {};
        const checks = list(comparison.eligibility_checks);
        return `
            <section class="qep-content-block qep-fair-protocol" data-qep-fair-comparison-protocol>
                <header class="qep-subhead"><div><span>Fair-comparison protocol</span><h3>Eight conditions required before either method can win</h3></div>${renderHelp("fair-comparison-protocol", "Explain the fair-comparison protocol", presentationHelp("market_comparison"))}</header>
                <p>${escapeHtml(text(comparison.summary, "The fair-comparison record is unavailable."))}</p>
                ${checks.length ? `<ol class="qep-check-list qep-fair-protocol-list">${checks.map((row) => {
                    const state = row.passed === true ? "passed" : row.passed === false ? "waiting" : "unavailable";
                    const label = row.passed === true ? "Satisfied" : row.passed === false ? "Still required" : "Unavailable";
                    return `<li><div><strong>${escapeHtml(text(row.label, human(row.key)))}</strong></div><p>${escapeHtml(text(row.summary, "No public explanation was exported."))}</p>${renderStatusChip(label, state)}</li>`;
                }).join("")}</ol>` : `<p class="qep-empty">No fair-comparison eligibility record was exported.</p>`}
            </section>
        `;
    }

    function renderNegativeEvidence(evidence) {
        const negative = list(evidence.negative_evidence);
        return `
            <section class="qep-content-block">
                <header class="qep-subhead"><div><span>Negative evidence</span><h3>What has not been established</h3></div></header>
                ${negative.length ? `<div class="qep-compact-records">${negative.map((row) => `<article><strong>${escapeHtml(text(row.title || row.label, human(row.key)))}</strong><p>${escapeHtml(text(row.explanation || row.summary || row.result))}</p>${renderStatusChip(text(row.status_label, human(row.status || "not_run")), row.status || "not_run")}</article>`).join("")}</div>` : `<p class="qep-empty">No negative-evidence records were exported.</p>`}
            </section>
        `;
    }

    function renderPilotFacts(evidence) {
        const pilot = evidence.pilot || {};
        const truth = pilot.evidence_truth || evidence.operational_evidence?.evidence_truth || pilot;
        const classified = truth.classified_window_count ?? truth.classified_windows;
        const eligible = truth.eligible_window_count ?? truth.eligible_holdout_windows;
        const providerRows = truth.provider_row_count ?? truth.provider_history_rows;
        const partitions = truth.completed_partition_count ?? truth.completed_provider_partitions;
        const features = list(pilot.point_in_time_features);
        return `
            <section class="qep-content-block">
                <header class="qep-subhead"><div><span>Untouched market evidence</span><h3>${escapeHtml(text(pilot.title || pilot.market_sleeve_label, `${human(pilot.market_sleeve, "Current")} pilot evidence`))}</h3></div>${renderHelp("untouched-evidence", "Explain untouched market evidence", helpText("untouched_holdout", "untouched_holdout"))}</header>
                ${pilot.research_question ? `<p>${escapeHtml(pilot.research_question)}</p>` : ""}
                <div class="qep-fact-metrics">
                    ${renderMetric({ label: "Classified windows", value: text(classified, 0), state: "neutral", helpKey: "classified-windows", helpLabel: "Explain classified and eligible holdout windows", help: helpText("classified_vs_eligible_windows", "classified_windows") })}
                    ${renderMetric({ label: "Eligible holdout windows", value: text(eligible, 0), state: number(eligible) > 0 ? "available" : "waiting_for_evidence", helpKey: "eligible-holdout-windows", helpLabel: "Explain eligible holdout windows", help: helpText("eligible_holdout_windows", "untouched_holdout") })}
                    ${renderMetric({ label: "Provider-history rows", value: text(providerRows, 0), state: number(providerRows) > 0 ? "available" : "waiting_for_evidence", helpKey: "provider-history-rows", helpLabel: "Explain provider-history rows", help: helpText("provider_history_rows", "provider_history") })}
                    ${renderMetric({ label: "Completed provider partitions", value: text(partitions, 0), state: number(partitions) > 0 ? "available" : "waiting_for_evidence", helpKey: "completed-provider-partitions", helpLabel: "Explain completed provider partitions", help: helpText("completed_provider_partitions", "provider_history") })}
                </div>
                <dl class="qep-fact-grid">
                    <div><dt>Paper targets</dt><dd>${escapeHtml(list(pilot.paper_targets).join(", ") || "Not exported")}</dd></div>
                    <div><dt>Market context</dt><dd>${escapeHtml(list(pilot.market_context).join(", ") || "Not exported")}</dd></div>
                    <div><dt>Point-in-time features</dt><dd>${features.length}</dd></div>
                    <div><dt>Defined outcomes</dt><dd>${list(pilot.outcomes).length}</dd></div>
                </dl>
                ${features.length ? `<div class="qep-feature-list" aria-label="Point-in-time pilot features">${features.map((feature) => `<article><strong>${escapeHtml(human(feature.key))}</strong><p>${escapeHtml(text(feature.meaning))}</p></article>`).join("")}</div>` : ""}
            </section>
        `;
    }

    function renderHardware(evidence) {
        const hardware = evidence.hardware_authenticity || {};
        const waveRecord = hardware.wave_f_record || hardware.provider_record || {};
        const checkpoint = hardware.current_hardware_checkpoint || hardware.hardware_checkpoint || {};
        const marketChecks = list(projection.answer?.market_proof_prerequisites?.checks);
        const providerCheck = marketChecks.find((row) => row.key === "ibm_provider_recovered" || row.key === "provider_configured");
        const metrics = [
            ["Provider configured", providerCheck?.passed ?? hardware.provider_configured ?? waveRecord.ibm_instance_accessible, "provider-access", "provider_access"],
            ["Hardware job authorized", checkpoint.authorized ?? hardware.hardware_job_authorized ?? hardware.authorized ?? waveRecord.hardware_execution_authorized, "hardware-authorized", "ibm_hardware"],
            ["Hardware job submitted", hardware.hardware_job_submitted ?? waveRecord.hardware_job_submitted, "hardware-submitted", "ibm_hardware"],
            ["Hardware result completed", hardware.hardware_result_completed ?? hardware.hardware_experiment_completed ?? waveRecord.hardware_experiment_completed, "hardware-completed", "ibm_hardware"],
            ["Verified hardware receipt", hardware.hardware_receipt_verified ?? waveRecord.hardware_receipt_verified, "hardware-receipt", "ibm_hardware"]
        ];
        return `
            <section class="qep-content-block">
                <header class="qep-subhead"><div><span>Hardware authenticity</span><h3>What the provider record actually proves</h3></div>${renderHelp("hardware-authenticity", "Explain hardware authenticity", helpText("ibm_hardware", "hardware_execution"))}</header>
                <dl class="qep-state-list">
                    ${metrics.map(([label, value, key, helpName]) => {
                        const available = value === true;
                        const state = value === null || value === undefined ? "unavailable" : available ? "complete" : "not_run";
                        return `<div><dt>${escapeHtml(label)}</dt><dd>${renderStatusChip(value === null || value === undefined ? "Not reported" : available ? "Yes" : "No", state)}${renderHelp(key, `Explain ${label.toLowerCase()}`, helpText(helpName, helpName))}</dd></div>`;
                    }).join("")}
                </dl>
                <p>${escapeHtml(text(hardware.summary || providerCheck?.explanation || checkpoint.provider_readiness_status || waveRecord.provider_blocker, "Provider readiness is reported separately from hardware execution."))}</p>
            </section>
        `;
    }

    function renderVerdictDefinitions() {
        const groups = [
            ["Proof status", [
                ["Unproven", "Required market evidence is incomplete, so Qadam makes no quantum-edge claim."],
                ["Provisional", "Positive untouched evidence exists, but the complete governed proof is unfinished."],
                ["Validated", "The contribution survived the defined hardware, market, and robustness requirements."]
            ]],
            ["Comparison outcome", [
                ["Not measurable", "The two methods have not yet completed one eligible fair comparison."],
                ["Classical preferred", HELP_FALLBACKS.classical_preferred],
                ["Quantum contribution", "The quantum-assisted method added information under the governed matched comparison."]
            ]],
            ["Evidence freshness", [
                ["Current", "The evidence records are within the governed freshness window."],
                ["Stale", "One or more required records are too old for a current claim."],
                ["Decayed", "A previously supported result no longer survives current evidence."]
            ]]
        ];
        return renderNested("state-definitions", "Independent state definitions", `<div class="qep-state-definition-groups">${groups.map(([label, rows]) => `<section><h5>${escapeHtml(label)}</h5><dl class="qep-definition-list">${rows.map(([term, meaning]) => `<div><dt>${escapeHtml(term)}</dt><dd>${escapeHtml(meaning)}</dd></div>`).join("")}</dl></section>`).join("")}</div>`);
    }

    function renderCertification(evidence) {
        const certification = evidence.certification || {};
        const groups = [
            ["Engineering mechanism", certification.engineering_checks?.checks || certification.engineering_checks || projection.answer?.engineering_checks?.checks],
            ["Market-proof prerequisites", certification.market_proof_prerequisites?.checks || certification.market_proof_prerequisites || certification.scientific_checks || projection.answer?.market_proof_prerequisites?.checks]
        ];
        const body = `<div class="qep-certification-groups">${groups.map(([label, value]) => {
            const checks = list(value);
            return `<section><h4>${escapeHtml(label)}</h4>${checks.length ? `<ul class="qep-check-list">${checks.map((row, index) => {
                const state = row.status || (row.passed === true ? "passed" : "not_run");
                const descriptor = `${row.key || ""} ${row.label || ""}`;
                let helpName = "";
                if (/simulat|control_reproduced|fixture|matched_lane/i.test(descriptor)) helpName = "strongest_evidence";
                else if (/provider|ibm_provider/i.test(descriptor)) helpName = "provider_access";
                else if (/hardware_result/i.test(descriptor)) helpName = "ibm_hardware";
                else if (/holdout|control_suite/i.test(descriptor)) helpName = "untouched_holdout";
                else if (/matched_quantum|classical/i.test(descriptor)) helpName = "matched_classical_comparison";
                const help = helpName ? renderHelp(`cert-${label}-${index}`, `Explain ${text(row.label, human(row.key))}`, helpText(helpName, helpName === "ibm_hardware" ? "hardware_execution" : helpName === "strongest_evidence" ? "engineering_control" : helpName)) : "";
                return `<li><div><strong>${escapeHtml(text(row.label, human(row.key)))}</strong>${help}</div><p>${escapeHtml(text(row.explanation || row.summary))}</p>${renderStatusChip(text(row.status_label, human(state)), state)}</li>`;
            }).join("")}</ul>` : `<p class="qep-empty">No checks were exported.</p>`}</section>`;
        }).join("")}</div>`;
        return renderNested("certification-checks", "Certification checks", body);
    }

    function flattenFacts(value, prefix = "") {
        if (!value || typeof value !== "object") return [];
        const rows = [];
        Object.entries(value).forEach(([key, item]) => {
            if (item === null || item === undefined || item === "") return;
            if (Array.isArray(item)) {
                rows.push([`${prefix}${human(key)}`, item.map((entry) => typeof entry === "object" ? text(entry.label || entry.key || entry.id, "record") : text(entry)).join(", ") || "None"]);
            } else if (typeof item === "object") {
                Object.entries(item).forEach(([nestedKey, nestedValue]) => {
                    if (["string", "number", "boolean"].includes(typeof nestedValue)) rows.push([`${prefix}${human(key)} · ${human(nestedKey)}`, text(nestedValue)]);
                });
            } else {
                rows.push([`${prefix}${human(key)}`, text(item)]);
            }
        });
        return rows;
    }

    function renderProvenance(evidence) {
        const facts = [
            ...flattenFacts(evidence.hardware_authenticity),
            ...flattenFacts(evidence.provenance)
        ];
        return renderNested("hardware-provenance", "Hardware and provenance", facts.length ? `<dl class="qep-provenance-list">${facts.map(([label, value]) => `<div><dt>${escapeHtml(label)}</dt><dd>${escapeHtml(value)}</dd></div>`).join("")}</dl>` : `<p class="qep-empty">No public hardware or provenance facts were exported.</p>`);
    }

    function renderOperationalEvidence(evidence) {
        const operational = evidence.operational_evidence || {};
        const stages = records(operational.daily_stages);
        const ledger = list(operational.run_ledger);
        const facts = flattenFacts({
            wave_g_cycle_id: operational.wave_g_cycle_id,
            wave_g_evidence_date: operational.wave_g_evidence_date,
            wave_g_status: operational.wave_g_status
        });
        const body = `
            ${operational.summary ? `<p>${escapeHtml(operational.summary)}</p>` : ""}
            ${stages.length ? `<div class="qep-operational-stages">${stages.map((stage) => `<article><strong>${escapeHtml(human(stage.key))}</strong><span>${escapeHtml(human(stage.state))}</span><p>${escapeHtml(text(stage.scope || stage.run_mode, "Current cycle record"))}</p></article>`).join("")}</div>` : ""}
            ${ledger.length ? `<div class="qep-record-list">${ledger.map((row, index) => `<article class="qep-record is-${tone(row.status)}"><header><div><span>${row.fixture_only ? "Engineering control" : "Market evidence"}</span><strong>${escapeHtml(text(row.run, `Run ${index + 1}`))}</strong></div>${renderStatusChip(human(row.status), row.status)}</header><p>${escapeHtml(text(row.result))}</p></article>`).join("")}</div>` : ""}
            ${facts.length ? `<dl class="qep-provenance-list">${facts.map(([label, value]) => `<div><dt>${escapeHtml(label)}</dt><dd>${escapeHtml(value)}</dd></div>`).join("")}</dl>` : ""}
            ${!stages.length && !ledger.length && !facts.length ? `<p class="qep-empty">No unattended-cycle facts were exported.</p>` : ""}
        `;
        return renderNested("operational-evidence", "Operational evidence", body);
    }

    function renderEvidence() {
        const evidence = projection.evidence || {};
        return `
            <div class="qep-section-body qep-evidence-body">
                ${renderStrongestEvidence(evidence)}
                ${renderExperiments(evidence)}
                ${renderMatchedComparison(evidence)}
                ${renderFairComparisonProtocol()}
                ${renderNegativeEvidence(evidence)}
                <div class="qep-two-column qep-evidence-pair">${renderHardware(evidence)}${renderPilotFacts(evidence)}</div>
                ${renderVerdictDefinitions()}
                ${renderCertification(evidence)}
                ${renderProvenance(evidence)}
                ${renderOperationalEvidence(evidence)}
            </div>
        `;
    }

    function consequenceCounts(consequence) {
        const strategy = consequence.strategy_influence || {};
        const paper = consequence.paper_outcome_lineage || {};
        return {
            strategy,
            paper,
            strategyCount: countOf(strategy, ["validated_strategy_count", "strategy_count", "count"]),
            paperCount: countOf(paper, ["attributed_paper_decision_count", "paper_decision_count", "count"])
        };
    }

    function renderGuardedRoute(consequence) {
        const route = consequence.guarded_route || {};
        const contract = route.route_contract || {};
        const stages = list(route.stages || route.route_stages || route.path || contract.stages);
        return `
            <section class="qep-content-block" data-qep-technical-route>
                <header class="qep-subhead"><div><span>Guarded downstream route</span><h3>${escapeHtml(stages.length ? `${stages.length}-stage route after independent validation` : "What could happen only after independent validation")}</h3></div></header>
                ${stages.length ? `<ol class="qep-route">${stages.map((stage, index) => `<li><span>${String(index + 1).padStart(2, "0")}</span><div><strong>${escapeHtml(text(stage.label || stage.title, human(typeof stage === "string" ? stage : stage.key)))}</strong>${typeof stage === "object" && (stage.explanation || stage.summary) ? `<p>${escapeHtml(stage.explanation || stage.summary)}</p>` : ""}</div></li>`).join("")}</ol>` : `<p class="qep-empty">No downstream route was exported.</p>`}
                ${route.summary || route.why_not?.reason ? `<p>${escapeHtml(text(route.summary || route.why_not.reason))}</p>` : ""}
            </section>
        `;
    }

    function renderLifecycle(consequence) {
        const lifecycle = list(consequence.hybrid_lifecycle);
        return renderNested("research-paper-lifecycle", "Research-to-paper lifecycle", lifecycle.length ? `<ol class="qep-lifecycle">${lifecycle.map((row, index) => {
            const state = row.status || "waiting_for_evidence";
            const stageLabel = row.label || row.title || row.state || row.stage || row.key;
            return `<li class="is-${tone(state)}"><span>${String(row.number || index + 1).padStart(2, "0")}</span><div><strong>${escapeHtml(human(stageLabel))}</strong><p>${escapeHtml(text(row.explanation || row.summary))}</p></div>${renderStatusChip(text(row.status_label, human(state)), state)}</li>`;
        }).join("")}</ol>` : `<p class="qep-empty">No research-to-paper lifecycle was exported.</p>`);
    }

    function renderDailyPreview(consequence) {
        const preview = consequence.daily_explanation_preview || {};
        const raw = text(preview.text || preview.preview, "");
        const paragraphs = raw ? raw.split(/\n\s*\n/).filter(Boolean) : [];
        return renderNested("daily-explanation", "Daily explanation preview", paragraphs.length ? `${paragraphs.map((paragraph) => `<p>${escapeHtml(paragraph)}</p>`).join("")}<small>${escapeHtml(text(preview.boundary, "Read-only explanation preview. It cannot send a message or accept a command."))}</small>` : `<p class="qep-empty">No daily explanation preview was exported.</p>`);
    }

    function renderConsequence() {
        const consequence = projection.consequence || {};
        const { strategy, paper, strategyCount, paperCount } = consequenceCounts(consequence);
        return `
            <div class="qep-section-body qep-consequence-body">
                <section class="qep-impact-intro"><span>Current downstream impact</span><h3>${escapeHtml(text(consequence.plain_english_summary, "No validated strategy or governed paper decision has changed because of quantum evidence."))}</h3></section>
                <div class="qep-metric-pair">
                    ${renderMetric({ label: "Strategy influence", value: `${strategyCount} ${strategyCount === 1 ? "strategy" : "strategies"}`, description: text(strategy.summary, "No validated strategy is attributable to quantum evidence."), state: strategyCount > 0 ? "validated" : "waiting_for_evidence", helpKey: "strategy-influence", helpLabel: "Explain strategy influence", help: helpText("strategy_influence", "strategy_influence") })}
                    ${renderMetric({ label: "Paper outcome lineage", value: `${paperCount} ${paperCount === 1 ? "paper decision" : "paper decisions"}`, description: text(paper.summary, "No governed paper decision or result is attributable to quantum evidence."), state: paperCount > 0 ? "validated" : "waiting_for_evidence", helpKey: "paper-outcome-lineage", helpLabel: "Explain paper outcome lineage", help: helpText("paper_outcome_lineage", "paper_outcome") })}
                </div>
                ${renderGuardedRoute(consequence)}
                ${renderLifecycle(consequence)}
                ${renderDailyPreview(consequence)}
                ${consequence.next_destination ? `<p class="qep-next-destination"><span>Next destination</span><strong>${escapeHtml(text(consequence.next_destination.label || consequence.next_destination, human(consequence.next_destination.state)))}</strong>${consequence.next_destination.summary ? `<small>${escapeHtml(consequence.next_destination.summary)}</small>` : ""}</p>` : ""}
            </div>
        `;
    }

    function presentationModel() {
        return projection?.presentation && typeof projection.presentation === "object" ? projection.presentation : {};
    }

    function displayValue(value) {
        if (value === 0 || value === false) return String(value);
        return text(value, "Unavailable");
    }

    function presentationHelp(key) {
        const copy = {
            shared_basis: "Both methods must receive the same frozen point-in-time evidence. This prevents either method from benefiting from different inputs or later information.",
            shared_evidence: "Both methods received the same frozen point-in-time evidence, so neither lane benefited from different inputs or later information.",
            conventional_lane: "This is Qadam’s strongest fair non-quantum comparison. It establishes what simpler methods can already explain.",
            quantum_lane: "This lane tests nonlinear, sequential, or path-dependent structure. Its purple treatment identifies the method; it does not imply that it won.",
            execution: "The software path reproduced locally. Provider readiness and hardware execution are separate, and no hardware result is implied by a simulator result.",
            engineering: "Engineering checks show whether the experimental test rig is reproducible and governed. They do not, by themselves, prove a market advantage.",
            experiment: "This reports whether the frozen experimental mechanism can be reproduced. It is separate from proof on untouched market evidence.",
            hardware: "Provider readiness and hardware execution are separate. Access to a provider does not mean that a hardware experiment ran.",
            market_comparison: "A fair comparison gives both methods the same untouched evidence, prediction target, horizon, evaluation rules, and leakage controls.",
            market_proof: "Market-proof prerequisites measure whether enough independent evidence exists to test predictive value fairly.",
            downstream: "Downstream impact records whether validated evidence changed a governed strategy or paper decision."
        };
        return copy[key] || "This status comes from Qadam’s current canonical public evidence projection.";
    }

    function renderPresentationFacts(items) {
        const facts = list(items);
        if (!facts.length) return "";
        return `
            <dl class="qep-simple-facts">
                ${facts.map((fact) => `
                    <div class="is-${tone(fact.status)}">
                        <dt><span>${escapeHtml(text(fact.label, human(fact.key)))}</span>${renderHelp(`evidence-fact-${fact.key}`, `Explain ${text(fact.label, "this evidence fact").toLowerCase()}`, presentationHelp(fact.key))}</dt>
                        <dd>${escapeHtml(displayValue(fact.value))}</dd>
                    </div>
                `).join("")}
            </dl>
        `;
    }

    function renderSharedBasis(shared) {
        return `
            <section class="qep-shared-basis" aria-labelledby="qep-shared-basis-title">
                <header>
                    <div>
                        <span class="qep-label-with-help">${escapeHtml(text(shared.label, "Shared frozen evidence"))}${renderHelp("shared-basis", "Explain shared frozen evidence", presentationHelp("shared_basis"))}</span>
                        <h3 id="qep-shared-basis-title">One evidence basis for both methods</h3>
                    </div>
                    ${renderStatusChip(text(shared.state_label, "Unavailable"), shared.state || "unavailable")}
                </header>
                <p>${escapeHtml(text(shared.summary, "The shared evidence basis is unavailable in the current public projection."))}</p>
            </section>
        `;
    }

    function methodDetails(lane, kind) {
        const isQuantum = kind === "quantum";
        return list(lane.details).length ? list(lane.details) : isQuantum ? [
            { label: "Run environment", value: lane.execution_mode },
            { label: "Current result", value: lane.reproducibility_label },
            { label: "Untouched market test", value: "Not yet eligible" },
            { label: "Main limitation", value: lane.hardware_label }
        ] : [
            { label: "Run environment", value: "Local Python research runtime" },
            { label: "Current result", value: lane.reproducibility_label },
            { label: "Untouched market test", value: lane.holdout_label },
            { label: "Main limitation", value: "No untouched market comparison yet" }
        ];
    }

    function renderMethodLane(lane, kind) {
        const isQuantum = kind === "quantum";
        return `
            <article class="qep-method-lane is-${isQuantum ? "quantum" : "classical"}">
                <header>
                    <span>${isQuantum ? "Quantum-assisted lane" : "Conventional lane"}</span>
                    ${renderStatusChip(text(lane.state_label, "Unavailable"), lane.state || "unavailable")}
                </header>
                <div class="qep-lane-title"><h3>${escapeHtml(text(lane.label, isQuantum ? "Quantum-assisted method" : "Classical benchmark"))}</h3>${renderHelp(`${kind}-lane`, `Explain the ${isQuantum ? "quantum-assisted" : "conventional"} lane`, presentationHelp(isQuantum ? "quantum_lane" : "conventional_lane"))}</div>
                <p>${escapeHtml(text(lane.summary, "This lane is unavailable in the current public projection."))}</p>
            </article>
        `;
    }

    function renderMatchedEvidenceRows(conventionalLane, quantumLane) {
        const conventional = methodDetails(conventionalLane, "classical");
        const quantum = methodDetails(quantumLane, "quantum");
        const labels = [...new Set([...conventional, ...quantum].map((row) => text(row.label, human(row.key))))];
        return `
            <section class="qep-matched-evidence" data-qep-matched-evidence aria-labelledby="qep-matched-evidence-title">
                <header>
                    <span>Matched evidence</span>
                    <h3 id="qep-matched-evidence-title">Distinct pairs used in the side-by-side comparison</h3>
                    <p>Each row compares the same evidence question across the conventional and quantum-assisted lanes.</p>
                </header>
                <ol>
                    ${labels.map((label, index) => {
                        const conventionalRow = conventional.find((row) => text(row.label, human(row.key)) === label) || {};
                        const quantumRow = quantum.find((row) => text(row.label, human(row.key)) === label) || {};
                        return `
                            <li>
                                <span>${String(index + 1).padStart(2, "0")}</span>
                                <strong>${escapeHtml(label)}</strong>
                                <div><small>Conventional lane</small><p>${escapeHtml(displayValue(conventionalRow.value))}</p></div>
                                <div><small>Quantum-assisted lane</small><p>${escapeHtml(displayValue(quantumRow.value))}</p></div>
                            </li>
                        `;
                    }).join("")}
                </ol>
            </section>
        `;
    }

    function renderSimplifiedEvidence() {
        const evidence = presentationModel().evidence || {};
        const matched = evidence.matched_outcome || {};
        const conventionalLane = evidence.conventional_lane || {};
        const quantumLane = evidence.quantum_lane || {};
        return `
            <div class="qep-section-body qep-simple-evidence">
                ${renderSharedBasis(evidence.shared_basis || {})}
                <div class="qep-method-lanes" aria-label="Fair method comparison">
                    ${renderMethodLane(conventionalLane, "classical")}
                    ${renderMethodLane(quantumLane, "quantum")}
                </div>
                ${renderMatchedEvidenceRows(conventionalLane, quantumLane)}
                <section class="qep-matched-outcome is-${tone(matched.key)}" aria-labelledby="qep-matched-outcome-title">
                    <span class="qep-label-with-help">Matched comparison${renderHelp("primary-matched-comparison", "Explain the matched comparison", presentationHelp("market_comparison"))}</span>
                    <h3 id="qep-matched-outcome-title">${escapeHtml(text(matched.label, "Comparison unavailable"))}</h3>
                    <p>${escapeHtml(text(matched.summary, "The matched comparison is unavailable in the current public projection."))}</p>
                </section>
            </div>
        `;
    }

    function renderSimplifiedImpact() {
        const impact = presentationModel().impact || {};
        const headline = impact.headline || {};
        const gates = list(impact.gates);
        const outcomes = list(impact.outcomes);
        const hasPositiveImpact = number(headline.strategy_count) > 0 || number(headline.paper_decision_count) > 0;
        return `
            <div class="qep-section-body qep-simple-impact">
                <section class="qep-impact-result is-${tone(headline.key)}">
                    <div><span>Current downstream impact</span><h3>${escapeHtml(text(headline.label, "Unavailable"))}</h3><p>${escapeHtml(text(headline.summary, "Downstream impact is unavailable in the current public projection."))}</p></div>
                    ${hasPositiveImpact ? `<p class="qep-impact-counts"><strong>${escapeHtml(displayValue(headline.strategy_count))}</strong><span>strategies changed</span><i aria-hidden="true"></i><strong>${escapeHtml(displayValue(headline.paper_decision_count))}</strong><span>paper decisions influenced</span></p>` : ""}
                </section>
                ${outcomes.length ? `<div class="qep-impact-decisions" aria-label="Current strategy and paper-decision impact">${outcomes.map((outcome) => `
                    <article class="is-${tone(outcome.state)}">
                        <span>${escapeHtml(text(outcome.label, human(outcome.key)))}</span>
                        <strong>${escapeHtml(displayValue(outcome.value))}</strong>
                    </article>
                `).join("")}</div>` : ""}
                <ol class="qep-four-gates" aria-label="Four evidence-to-decision gates">
                    ${gates.map((gate, index) => `
                        <li class="is-${tone(gate.state)}">
                            <span class="qep-gate-number" aria-hidden="true">${String(index + 1).padStart(2, "0")}</span>
                            <div><strong>${escapeHtml(text(gate.label, human(gate.key)))}</strong><p>${escapeHtml(text(gate.summary, "No public explanation was exported."))}</p></div>
                            ${renderStatusChip(text(gate.state_label, "Unavailable"), gate.state || "unavailable")}
                        </li>
                    `).join("")}
                </ol>
                <p class="qep-impact-boundary">${escapeHtml(text(impact.boundary, "Quantum findings remain research-only until every governed evidence and downstream gate is satisfied."))}</p>
            </div>
        `;
    }

    function renderSimplifiedVerdict() {
        const verdict = presentationModel().verdict || {};
        const statements = list(verdict.statements).slice(0, 3);
        const freshnessWarning = !["", "current"].includes(text(verdict.freshness_state, ""))
            ? `<small class="qep-verdict-freshness is-${tone(verdict.freshness_state)}">Evidence freshness: ${escapeHtml(text(verdict.freshness_label, "Unavailable"))}</small>`
            : "";
        return `
            <div class="qep-section-body qep-simple-verdict">
                <section class="qep-verdict-result is-${tone(verdict.proof_state)}">
                    <span class="qep-label-with-help">Formal market-level verdict${renderHelp("formal-market-verdict", "Explain the formal market-level verdict", presentationHelp("market_proof"))}</span>
                    <h3>${escapeHtml(text(verdict.proof_state_label, "Unavailable"))}</h3>
                    <strong>${escapeHtml(text(verdict.comparison_label, verdict.scientific_verdict_label || "Unavailable"))}</strong>
                    ${freshnessWarning}
                    <p>${escapeHtml(text(verdict.summary, "The current verdict is unavailable in the public projection."))}</p>
                </section>
                <div class="qep-verdict-statements" aria-label="Plain-English verdict explanation">
                    ${statements.map((statement, index) => `
                        <article class="is-${tone(statement.state)}">
                            <span>${String(index + 1).padStart(2, "0")}</span>
                            <div><strong>${escapeHtml(text(statement.label, human(statement.key)))}</strong><p>${escapeHtml(text(statement.summary, "No explanation was exported."))}</p></div>
                        </article>
                    `).join("")}
                </div>
            </div>
        `;
    }

    function renderTechnicalProofRecord() {
        const answer = projection.answer || {};
        const engineering = answer.engineering_checks || {};
        const market = answer.market_proof_prerequisites || {};
        return `
            <div class="qep-section-body qep-technical-proof-record">
                ${renderScorePair(answer)}
                <section class="qep-content-block">
                    <header class="qep-subhead"><div><span>Proof sequence</span><h3>What the evidence must establish, in order</h3></div><small>${escapeHtml(text(answer.proof_ladder?.completed_count, 0))}/${escapeHtml(text(answer.proof_ladder?.step_count, proofSteps(answer).length))} stages reached</small></header>
                    ${renderProofLadder(answer)}
                </section>
                <div class="qep-two-column">
                    <section class="qep-content-block"><header class="qep-subhead"><div><span>Current blockers</span><h3>Why proof cannot advance</h3></div></header>${renderList(answer.current_blockers, "No blocker was exported.")}</section>
                    <section class="qep-content-block"><header class="qep-subhead"><div><span>Required evidence</span><h3>What would change the record</h3></div></header>${renderList(answer.next_required_evidence, "No next evidence requirement was exported.")}</section>
                </div>
                <p class="qep-score-note">The engineering and market-proof scores remain separate: ${escapeHtml(scoreLabel(engineering))} describes the test rig; ${escapeHtml(scoreLabel(market))} describes the independent market-proof prerequisites.</p>
            </div>
        `;
    }

    function renderTechnicalMetadata() {
        const sources = list(projection.source_artifacts);
        const freshnessFacts = flattenFacts(projection.freshness);
        return `
            <div class="qep-two-column qep-technical-metadata">
                <section class="qep-content-block">
                    <header class="qep-subhead"><div><span>Source artifacts</span><h3>Canonical evidence inputs</h3></div></header>
                    ${sources.length ? `<div class="qep-record-list">${sources.map((source, index) => `<article class="qep-record is-${tone(source.content_hash_verified ? "verified" : "unavailable")}"><header><div><span>${escapeHtml(text(source.source_id, `Source ${index + 1}`))}</span><strong>${escapeHtml(text(source.artifact_name, "Artifact name unavailable"))}</strong></div>${renderStatusChip(source.content_hash_verified === true ? "Hash verified" : "Verification unavailable", source.content_hash_verified === true ? "verified" : "unavailable")}</header><p>${escapeHtml(text(source.responsibility, "Responsibility not exported."))}</p><dl class="qep-provenance-list"><div><dt>Schema</dt><dd>${escapeHtml(text(source.schema_version))}</dd></div><div><dt>Generated</dt><dd>${escapeHtml(text(source.generated_at))}</dd></div><div><dt>Content hash</dt><dd>${escapeHtml(text(source.content_hash))}</dd></div></dl></article>`).join("")}</div>` : `<p class="qep-empty">No public source-artifact references were exported.</p>`}
                </section>
                <section class="qep-content-block">
                    <header class="qep-subhead"><div><span>Freshness</span><h3>Current evidence timing</h3></div></header>
                    ${freshnessFacts.length ? `<dl class="qep-provenance-list">${freshnessFacts.map(([label, value]) => `<div><dt>${escapeHtml(label)}</dt><dd>${escapeHtml(value)}</dd></div>`).join("")}</dl>` : `<p class="qep-empty">No public freshness record was exported.</p>`}
                </section>
            </div>
        `;
    }

    function renderTechnicalIndex(items) {
        const rows = list(items);
        if (!rows.length) return "";
        return `<nav class="qep-technical-index" aria-label="Technical evidence record index"><span>Record index</span><ul>${rows.map((row) => `<li>${escapeHtml(text(row.label, human(row.key)))}</li>`).join("")}</ul></nav>`;
    }

    function renderTechnicalEvidence() {
        const technical = presentationModel().technical_record || {};
        return `
            <details id="quantum-technical-evidence" class="qep-technical" data-qep-technical ${technicalOpen ? "open" : ""}>
                <summary data-qep-focus-key="technical-summary">
                    <span><small>Complete research record</small><strong class="qep-technical-view-label">${escapeHtml(text(technical.label, "View technical evidence"))}</strong><strong class="qep-technical-hide-label">Hide technical evidence</strong></span>
                    <i aria-hidden="true"></i>
                </summary>
                <div class="qep-technical-body">
                    <header class="qep-technical-header">
                        <div><span>Audit trail</span><h3>Technical evidence and provenance</h3><p>The detail below preserves the complete public-safe experiment, validation, hardware, lineage, and consequence record behind the simplified page.</p></div>
                        <button type="button" data-qep-technical-close data-qep-focus-key="technical-close">Close technical evidence</button>
                    </header>
                    ${renderTechnicalIndex(technical.index)}
                    <section class="qep-technical-chapter" aria-labelledby="qep-technical-verdict"><h3 id="qep-technical-verdict">Proof record</h3>${renderTechnicalProofRecord()}</section>
                    <section class="qep-technical-chapter" aria-labelledby="qep-technical-experiments"><h3 id="qep-technical-experiments">Experiment and evidence record</h3>${renderEvidence()}</section>
                    <section class="qep-technical-chapter" aria-labelledby="qep-technical-impact"><h3 id="qep-technical-impact">Strategy and paper-impact record</h3>${renderConsequence()}</section>
                    <section class="qep-technical-chapter" aria-labelledby="qep-technical-metadata"><h3 id="qep-technical-metadata">Source and freshness record</h3>${renderTechnicalMetadata()}</section>
                    <button type="button" class="qep-technical-close-bottom" data-qep-technical-close data-qep-focus-key="technical-close-bottom">Close technical evidence</button>
                </div>
            </details>
        `;
    }

    function primarySummary(id, row, status, state) {
        return `
            <summary data-qep-primary-summary data-qep-focus-key="primary-${id}">
                <span class="qep-section-number">${escapeHtml(text(row.sequence, id === "evidence" ? "01" : id === "consequence" ? "02" : "03"))}</span>
                <div class="qep-summary-copy"><span>${escapeHtml(text(row.eyebrow, id === "evidence" ? "Experiment & Evidence" : id === "consequence" ? "Strategy & Paper Impact" : "Quantum Edge Verdict"))}</span><strong>${escapeHtml(text(row.title, id === "evidence" ? "What was run, what was compared, and what was verified?" : id === "consequence" ? "Did this change a validated strategy or paper decision?" : "Has a genuine market-level quantum advantage been proven?"))}</strong></div>
                <div class="qep-summary-state">${renderStatusChip(status, state)}<small>${escapeHtml(text(row.summary, "Current public status unavailable."))}</small></div>
                <span class="qep-summary-toggle" aria-hidden="true"><i></i></span>
            </summary>
        `;
    }

    function renderPrimarySections() {
        const presentation = presentationModel();
        const rows = presentation.rows || {};
        const evidence = presentation.evidence || {};
        const impact = presentation.impact || {};
        const verdict = presentation.verdict || {};
        const open = primaryState();
        const hashId = window.location.hash.replace(/^#quantum-/, "");
        if (PRIMARY_IDS.includes(hashId)) open[hashId] = true;
        return `
            <div class="qep-primary-sections" data-qep-primary-sections>
                <details id="quantum-evidence" class="qep-primary is-evidence" data-qep-primary="evidence" ${open.evidence ? "open" : ""}>
                    ${primarySummary("evidence", rows.evidence || {}, text(evidence.shared_basis?.state_label, "Unavailable"), evidence.shared_basis?.state || "unavailable")}
                    ${renderSimplifiedEvidence()}
                </details>
                <details id="quantum-consequence" class="qep-primary is-consequence" data-qep-primary="consequence" ${open.consequence ? "open" : ""}>
                    ${primarySummary("consequence", rows.consequence || {}, text(impact.headline?.label, "Unavailable"), impact.headline?.key || "unavailable")}
                    ${renderSimplifiedImpact()}
                </details>
                <details id="quantum-answer" class="qep-primary is-answer" data-qep-primary="answer" ${open.answer ? "open" : ""}>
                    ${primarySummary("answer", rows.answer || {}, text(verdict.proof_state_label, "Unavailable"), verdict.proof_state || "unavailable")}
                    ${renderSimplifiedVerdict()}
                </details>
            </div>
        `;
    }

    function renderGuidance() {
        const guidance = projection.page_explainer?.guidance || {};
        const workflowSteps = list(guidance.workflow_steps).length ? list(guidance.workflow_steps) : GUIDANCE_WORKFLOW_STEPS;
        const operatingModel = guidance.operating_model && typeof guidance.operating_model === "object" ? guidance.operating_model : GUIDANCE_OPERATING_MODEL;
        const currentCapability = guidance.current_capability && typeof guidance.current_capability === "object" ? guidance.current_capability : GUIDANCE_CURRENT_CAPABILITY;
        const proofSteps = list(guidance.proof_steps).length ? list(guidance.proof_steps) : GUIDANCE_PROOF_STEPS;
        const outcomeStates = list(guidance.outcome_states).length ? list(guidance.outcome_states) : GUIDANCE_OUTCOME_STATES;
        const takeaway = guidance.takeaway && typeof guidance.takeaway === "object" ? guidance.takeaway : GUIDANCE_TAKEAWAY;
        return `
            <div id="qep-purpose-guidance" class="qep-guidance" data-qep-guidance ${introExpanded ? "" : "hidden"}>
                <div class="qep-guidance-intro">
                    <span class="qep-guidance-eyebrow">${escapeHtml(guidanceText(guidance.eyebrow, "Quantum research mandate"))}</span>
                    <p>${escapeHtml(guidanceText(guidance.introduction, "Quantum analysis earns a role in Qadam’s research process only when it clears six increasingly demanding standards—from infrastructure access to measurable decision value under paper-trading governance."))}</p>
                </div>
                <section class="qep-guidance-workflow" aria-labelledby="qep-guidance-workflow-title">
                    <header class="qep-guidance-section-heading">
                        <h3 id="qep-guidance-workflow-title">${escapeHtml(guidanceText(guidance.workflow_heading, "How the hybrid research loop works"))}</h3>
                        <p>${escapeHtml(guidanceText(guidance.workflow_support, "Classical and quantum-assisted methods have distinct roles, then meet under one validation standard."))}</p>
                    </header>
                    <ol class="qep-guidance-workflow-steps" data-qep-guidance-workflow role="list">
                        ${workflowSteps.map((step, index) => `
                            <li data-qep-guidance-workflow-step="${escapeHtml(text(step.key, `workflow-${index + 1}`))}">
                                <span class="qep-guidance-workflow-number" aria-hidden="true">${String(index + 1).padStart(2, "0")}</span>
                                <div>
                                    <span class="qep-guidance-workflow-label">${escapeHtml(guidanceText(step.label, `Research stage ${index + 1}`))}</span>
                                    <strong>${escapeHtml(guidanceText(step.title, "Stage title unavailable"))}</strong>
                                    <p>${escapeHtml(guidanceText(step.description, "Stage explanation unavailable"))}</p>
                                </div>
                            </li>
                        `).join("")}
                    </ol>
                </section>
                <aside class="qep-guidance-boundaries" aria-label="Hybrid operating model and current capability">
                    <article class="qep-guidance-boundary is-model" data-qep-guidance-operating-model>
                        <span>${escapeHtml(guidanceText(operatingModel.label, "Operating model"))}</span>
                        <strong>${escapeHtml(guidanceText(operatingModel.title, "Hybrid by design - not a standalone quantum computer."))}</strong>
                        <p>${escapeHtml(guidanceText(operatingModel.body, GUIDANCE_OPERATING_MODEL.body))}</p>
                    </article>
                    <article class="qep-guidance-boundary is-current" data-qep-guidance-current-capability>
                        <span>${escapeHtml(guidanceText(currentCapability.label, "Current capability"))}</span>
                        <strong>${escapeHtml(guidanceText(currentCapability.title, GUIDANCE_CURRENT_CAPABILITY.title))}</strong>
                        <p>${escapeHtml(guidanceText(currentCapability.body, GUIDANCE_CURRENT_CAPABILITY.body))}</p>
                    </article>
                </aside>
                <section class="qep-guidance-proof" aria-labelledby="qep-guidance-proof-title">
                    <header class="qep-guidance-section-heading">
                        <h3 id="qep-guidance-proof-title">${escapeHtml(guidanceText(guidance.proof_heading, "Six standards of evidence"))}</h3>
                        <p>${escapeHtml(guidanceText(guidance.proof_support, "The standards are cumulative: passing an earlier stage does not satisfy the stages that follow."))}</p>
                    </header>
                    <ol class="qep-guidance-steps" data-qep-guidance-steps role="list">
                        ${proofSteps.map((step, index) => `
                            <li class="qep-guidance-step" data-qep-guidance-step="${escapeHtml(text(step.key, `step-${index + 1}`))}">
                                <span class="qep-guidance-step-number" aria-hidden="true">${String(index + 1).padStart(2, "0")}</span>
                                <div>
                                    <span class="qep-guidance-step-label">${escapeHtml(guidanceText(step.label, `Proof question ${index + 1}`))}</span>
                                    <strong>${escapeHtml(guidanceText(step.question, "Question unavailable"))}</strong>
                                    <p>${escapeHtml(guidanceText(step.meaning, "Explanation unavailable"))}</p>
                                </div>
                            </li>
                        `).join("")}
                    </ol>
                </section>
                <section class="qep-guidance-results" aria-labelledby="qep-guidance-results-title">
                    <header class="qep-guidance-section-heading">
                        <h3 id="qep-guidance-results-title">${escapeHtml(guidanceText(guidance.outcome_heading, "Permissible research conclusions"))}</h3>
                        <p>${escapeHtml(guidanceText(guidance.outcome_introduction, "The evidence can support one of five governed conclusions."))}</p>
                    </header>
                    <ul class="qep-guidance-outcomes" data-qep-guidance-outcomes role="list">
                        ${outcomeStates.map((outcome) => `
                            <li data-qep-guidance-outcome="${escapeHtml(text(outcome.key, "outcome"))}">
                                <strong>${escapeHtml(guidanceText(outcome.label, "Outcome"))}</strong>
                                <p>${escapeHtml(guidanceText(outcome.description, "Explanation unavailable"))}</p>
                            </li>
                        `).join("")}
                    </ul>
                </section>
                <aside class="qep-guidance-takeaway" data-qep-guidance-takeaway aria-label="${escapeHtml(guidanceText(takeaway.label, "Research reminder"))}">
                    <span>${escapeHtml(guidanceText(takeaway.label, "Research reminder"))}</span>
                    <strong>${escapeHtml(guidanceText(takeaway.title, "A classical-preferred result is a successful research outcome."))}</strong>
                    <p>${escapeHtml(guidanceText(takeaway.body, "It shows that the conventional method explains the evidence as well as or better than the more complex approach, allowing Qadam to avoid unsupported complexity."))}</p>
                </aside>
                <button type="button" class="qep-guidance-close" data-qep-guidance-close data-qep-focus-key="guidance-close">Minimize research mandate</button>
            </div>
        `;
    }

    function renderPage() {
        const pageCopy = projection.page_copy || {};
        const axes = projection.state_axes || {};
        const verdict = presentationModel().verdict || {};
        const pageExplainer = projection.page_explainer || {};
        const freshnessCurrent = ["", "current"].includes(text(verdict.freshness_state, ""));
        const conclusionState = freshnessCurrent ? verdict.comparison_label || verdict.scientific_verdict_label : verdict.freshness_label;
        const conclusionTone = freshnessCurrent ? axes.proof?.key : verdict.freshness_state;
        const conclusion = `${text(verdict.proof_state_label, "Unavailable")} - ${text(conclusionState, "Unavailable")}`;
        const readMoreLabel = `${text(pageExplainer.read_more_label, "How Qadam researches, finds evidence and makes a conclusion").replace(/\s*\+\s*$/, "")} +`;
        const readLessLabel = text(pageExplainer.read_less_label, "Minimize -");
        const freshness = projection.generated_at ? `Evidence projection updated ${new Date(projection.generated_at).toLocaleString(undefined, { dateStyle: "medium", timeStyle: "short" })}` : "Evidence projection time unavailable";
        return `
            <section class="qep-page" data-quantum-edge-page data-qep-content-hash="${escapeHtml(projection.content_hash)}" aria-labelledby="qep-page-title">
                <header class="qep-header">
                    <div class="qep-header-layout">
                        <div class="qep-header-copy">
                            <span>${escapeHtml(text(pageCopy.eyebrow, PAGE_EYEBROW))}</span>
                            <h2 id="qep-page-title">${escapeHtml(text(pageCopy.title, "Quantum Edge"))}</h2>
                            <p class="qep-purpose">${escapeHtml(text(pageCopy.subtitle, PURPOSE_COPY))}</p>
                            <button type="button" class="qep-read-more" data-qep-read-more data-qep-focus-key="read-more" aria-expanded="${introExpanded ? "true" : "false"}" aria-controls="qep-purpose-guidance">${escapeHtml(introExpanded ? readLessLabel : readMoreLabel)}</button>
                        </div>
                        <aside class="qep-header-side">
                            <p class="qep-current-conclusion is-${tone(conclusionTone)}" data-qep-current-conclusion role="status" aria-live="polite"><span>${escapeHtml(text(pageCopy.conclusion_label, "Current conclusion"))}</span><strong>${escapeHtml(conclusion)}</strong></p>
                            <img class="qep-quantum-hero-image" src="/assets/ibm-quantum-computer.jpg" alt="IBM quantum computer hardware" width="1280" height="720" loading="eager" decoding="async">
                        </aside>
                    </div>
                    ${renderGuidance()}
                </header>
                ${renderPrimarySections()}
                ${renderTechnicalEvidence()}
                <footer class="qep-freshness"><small>${escapeHtml(freshness)}</small></footer>
            </section>
        `;
    }

    function renderUnavailablePage() {
        return `
            <section class="qep-page qep-unavailable-page" data-quantum-edge-page data-qep-unavailable aria-labelledby="qep-page-title">
                <header class="qep-header">
                    <div class="qep-header-layout">
                        <div class="qep-header-copy">
                            <span>${escapeHtml(PAGE_EYEBROW)}</span>
                            <h2 id="qep-page-title">Quantum Edge</h2>
                            <p class="qep-purpose">${escapeHtml(PURPOSE_COPY)}</p>
                        </div>
                        <p class="qep-current-conclusion is-waiting" role="status" aria-live="polite"><span>Current proof unavailable</span><strong>Qadam cannot verify the current Quantum Edge projection, so no proof state or score is being shown.</strong></p>
                    </div>
                </header>
                <section class="qep-unavailable-card">
                    <div><span>Fail-closed evidence view</span><h3>The scientific record could not be loaded safely</h3><p>The page has not inferred a verdict, reused an old count, or treated a missing test as a failure. You can retry the same read-only status request.</p></div>
                    <button type="button" data-qep-retry data-qep-focus-key="retry">Retry</button>
                </section>
            </section>
        `;
    }

    function clearHelpCloseTimer() {
        if (helpCloseTimer) window.clearTimeout(helpCloseTimer);
        helpCloseTimer = 0;
    }

    function positionHelp(trigger, panel) {
        if (!trigger?.isConnected || !panel?.isConnected || panel.hidden) return;
        const margin = 16;
        const gap = 8;
        const triggerRect = trigger.getBoundingClientRect();
        panel.style.maxWidth = `${Math.max(180, Math.min(360, window.innerWidth - margin * 2))}px`;
        panel.style.left = `${margin}px`;
        panel.style.top = `${margin}px`;
        const panelRect = panel.getBoundingClientRect();
        let left = triggerRect.left + (triggerRect.width - panelRect.width) / 2;
        left = Math.max(margin, Math.min(left, window.innerWidth - panelRect.width - margin));
        let top = triggerRect.bottom + gap;
        if (top + panelRect.height > window.innerHeight - margin && triggerRect.top - panelRect.height - gap >= margin) {
            top = triggerRect.top - panelRect.height - gap;
            panel.dataset.qepPosition = "above";
        } else {
            top = Math.max(margin, Math.min(top, window.innerHeight - panelRect.height - margin));
            panel.dataset.qepPosition = "below";
        }
        panel.style.left = `${Math.round(left)}px`;
        panel.style.top = `${Math.round(top)}px`;
    }

    function closeHelp({ restoreFocus = false } = {}) {
        clearHelpCloseTimer();
        if (!activeHelp) return;
        const { trigger, panel } = activeHelp;
        panel.hidden = true;
        panel.removeAttribute("data-qep-position");
        panel.style.removeProperty("left");
        panel.style.removeProperty("top");
        panel.style.removeProperty("max-width");
        trigger.setAttribute("aria-expanded", "false");
        trigger.closest("[data-qep-help]")?.classList.remove("is-open", "is-pinned");
        activeHelp = null;
        if (restoreFocus && trigger.isConnected) trigger.focus({ preventScroll: true });
    }

    function openHelp(trigger, { pinned = false } = {}) {
        const wrapper = trigger.closest("[data-qep-help]");
        const panel = wrapper?.querySelector("[data-qep-help-popover]");
        if (!panel) return;
        clearHelpCloseTimer();
        if (activeHelp && activeHelp.trigger !== trigger) closeHelp();
        activeHelp = activeHelp?.trigger === trigger ? activeHelp : {
            trigger,
            panel,
            pinned: false,
            triggerHovered: false,
            panelHovered: false
        };
        activeHelp.pinned = Boolean(pinned || activeHelp.pinned);
        panel.hidden = false;
        trigger.setAttribute("aria-expanded", "true");
        wrapper.classList.add("is-open");
        wrapper.classList.toggle("is-pinned", activeHelp.pinned);
        window.requestAnimationFrame(() => positionHelp(trigger, panel));
    }

    function maybeScheduleHelpClose() {
        clearHelpCloseTimer();
        helpCloseTimer = window.setTimeout(() => {
            if (!activeHelp || activeHelp.pinned || activeHelp.triggerHovered || activeHelp.panelHovered || document.activeElement === activeHelp.trigger) return;
            closeHelp();
        }, 180);
    }

    function bindHelp(root) {
        root.querySelectorAll("[data-qep-help-trigger]").forEach((trigger) => {
            const panel = trigger.closest("[data-qep-help]")?.querySelector("[data-qep-help-popover]");
            trigger.addEventListener("pointerenter", () => {
                openHelp(trigger);
                if (activeHelp?.trigger === trigger) activeHelp.triggerHovered = true;
            });
            trigger.addEventListener("pointerleave", () => {
                if (activeHelp?.trigger === trigger) activeHelp.triggerHovered = false;
                maybeScheduleHelpClose();
            });
            trigger.addEventListener("focus", () => openHelp(trigger));
            trigger.addEventListener("blur", maybeScheduleHelpClose);
            trigger.addEventListener("click", (event) => {
                event.stopPropagation();
                if (activeHelp?.trigger === trigger && activeHelp.pinned) {
                    closeHelp();
                } else {
                    openHelp(trigger, { pinned: true });
                }
            });
            panel?.addEventListener("pointerenter", () => {
                if (activeHelp?.panel === panel) activeHelp.panelHovered = true;
                clearHelpCloseTimer();
            });
            panel?.addEventListener("pointerleave", () => {
                if (activeHelp?.panel === panel) activeHelp.panelHovered = false;
                maybeScheduleHelpClose();
            });
        });
    }

    function bindPage(root) {
        const readMore = root.querySelector("[data-qep-read-more]");
        const guidance = root.querySelector("[data-qep-guidance]");
        readMore?.addEventListener("click", () => {
            introExpanded = !introExpanded;
            if (!introExpanded && guidance?.contains(document.activeElement)) readMore.focus({ preventScroll: true });
            guidance.hidden = !introExpanded;
            readMore.setAttribute("aria-expanded", introExpanded ? "true" : "false");
            const collapsedLabel = `${text(projection.page_explainer?.read_more_label, "How Qadam researches, finds evidence and makes a conclusion").replace(/\s*\+\s*$/, "")} +`;
            readMore.textContent = introExpanded ? text(projection.page_explainer?.read_less_label, "Minimize -") : collapsedLabel;
        });
        root.querySelector("[data-qep-guidance-close]")?.addEventListener("click", () => {
            introExpanded = false;
            guidance.hidden = true;
            readMore?.setAttribute("aria-expanded", "false");
            if (readMore) {
                readMore.textContent = `${text(projection.page_explainer?.read_more_label, "How Qadam researches, finds evidence and makes a conclusion").replace(/\s*\+\s*$/, "")} +`;
                readMore.focus({ preventScroll: true });
            }
        });
        root.querySelectorAll("[data-qep-primary]").forEach((details) => {
            details.addEventListener("toggle", () => {
                if (!details.open && details.contains(document.activeElement) && document.activeElement !== details.querySelector(":scope > summary")) {
                    details.querySelector(":scope > summary")?.focus({ preventScroll: true });
                }
                storePrimaryState(root);
                if (!details.open && activeHelp?.trigger && details.contains(activeHelp.trigger)) closeHelp();
            });
        });
        const technical = root.querySelector("[data-qep-technical]");
        const technicalSummary = technical?.querySelector(":scope > summary");
        technical?.addEventListener("toggle", () => {
            technicalOpen = technical.open;
            if (!technical.open && technical.contains(document.activeElement) && document.activeElement !== technicalSummary) {
                technicalSummary?.focus({ preventScroll: true });
            }
            if (!technical.open && activeHelp?.trigger && technical.contains(activeHelp.trigger)) closeHelp();
        });
        root.querySelectorAll("[data-qep-technical-close]").forEach((button) => {
            button.addEventListener("click", () => {
                if (!technical) return;
                technical.open = false;
                technicalSummary?.focus({ preventScroll: true });
            });
        });
        root.addEventListener("keydown", (event) => {
            if (event.key !== "Escape" || !technical?.open || !technical.contains(document.activeElement)) return;
            event.preventDefault();
            technical.open = false;
            technicalSummary?.focus({ preventScroll: true });
        });
        bindHelp(root);
    }

    function deepLink({ force = false } = {}) {
        const hash = window.location.hash;
        const isPrimaryHash = PRIMARY_IDS.some((id) => hash === `#quantum-${id}`);
        const isTechnicalHash = hash === "#quantum-technical-evidence";
        if (!isPrimaryHash && !isTechnicalHash) return;
        if (!force && handledHash === hash) return;
        const root = document.querySelector(ROOT_SELECTOR);
        const details = root?.querySelector(hash);
        const summary = details?.querySelector(":scope > summary");
        if (!details || !summary) return;
        details.open = true;
        if (isPrimaryHash) storePrimaryState(root);
        if (isTechnicalHash) technicalOpen = true;
        handledHash = hash;
        window.requestAnimationFrame(() => {
            details.scrollIntoView({ behavior: window.matchMedia("(prefers-reduced-motion: reduce)").matches ? "auto" : "smooth", block: "start" });
            summary.focus({ preventScroll: true });
        });
    }

    function captureFocusKey(root) {
        const focused = document.activeElement;
        if (!focused || !root?.contains(focused)) return "";
        return focused.closest("[data-qep-focus-key]")?.dataset.qepFocusKey || "";
    }

    function applyProjection() {
        applyScheduled = false;
        if (!projection || !routeIsActive()) return;
        const panel = document.querySelector(PANEL_SELECTOR);
        if (!panel) return;
        const roots = Array.from(panel.querySelectorAll(ROOT_SELECTOR));
        const existing = roots[0] || null;
        roots.slice(1).forEach((root) => root.remove());
        if (existing?.dataset.qepContentHash === projection.content_hash && !forceFreshRender) {
            deepLink();
            return;
        }
        if (existing && !forceFreshRender) {
            storePrimaryState(existing);
            technicalOpen = Boolean(existing.querySelector("[data-qep-technical]")?.open);
        }
        const focusKey = captureFocusKey(existing);
        if (activeHelp?.trigger && existing?.contains(activeHelp.trigger)) closeHelp({ restoreFocus: true });
        const lifecycle = Array.from(panel.children).find((child) => child.matches?.("[data-qadam-lifecycle]"));
        const handoff = Array.from(panel.children).find((child) => child.matches?.("[data-qsase-flow-handoff]"));
        Array.from(panel.children).forEach((child) => {
            if (child !== lifecycle && child !== handoff) child.remove();
        });
        const wrapper = document.createElement("div");
        wrapper.innerHTML = renderPage().trim();
        const root = wrapper.firstElementChild;
        if (handoff) panel.insertBefore(root, handoff);
        else panel.appendChild(root);
        bindPage(root);
        forceFreshRender = false;
        if (focusKey) Array.from(root.querySelectorAll("[data-qep-focus-key]")).find((control) => control.dataset.qepFocusKey === focusKey)?.focus({ preventScroll: true });
        document.documentElement.dataset.qadamQuantumEdgePage = "rendered";
        window.dispatchEvent(new CustomEvent("qadam-quantum-edge-page-ready", { detail: { contentHash: projection.content_hash } }));
        deepLink({ force: true });
    }

    function showUnavailablePage() {
        if (!routeIsActive()) return;
        const panel = document.querySelector(PANEL_SELECTOR);
        if (!panel) return;
        closeHelp();
        const lifecycle = Array.from(panel.children).find((child) => child.matches?.("[data-qadam-lifecycle]"));
        const handoff = Array.from(panel.children).find((child) => child.matches?.("[data-qsase-flow-handoff]"));
        Array.from(panel.children).forEach((child) => {
            if (child !== lifecycle && child !== handoff) child.remove();
        });
        const wrapper = document.createElement("div");
        wrapper.innerHTML = renderUnavailablePage().trim();
        const root = wrapper.firstElementChild;
        if (handoff) panel.insertBefore(root, handoff);
        else panel.appendChild(root);
        const retry = root.querySelector("[data-qep-retry]");
        retry?.addEventListener("click", () => {
            retry.disabled = true;
            retry.textContent = "Retrying…";
            loadProjection({ retry: true });
        });
        document.documentElement.dataset.qadamQuantumEdgePage = "unavailable";
    }

    function scheduleApply() {
        if (applyScheduled) return;
        applyScheduled = true;
        window.requestAnimationFrame(applyProjection);
    }

    async function loadProjection({ retry = false } = {}) {
        if (!routeIsActive()) return null;
        if (loadFailed && !retry) return null;
        if (retry) {
            loadFailed = false;
            loadPromise = null;
        }
        if (loadPromise) return loadPromise;
        loadPromise = (async () => {
            try {
                const response = await fetch(STATUS_URL, { cache: "no-store", credentials: "same-origin" });
                if (!response.ok) throw new Error(`Quantum Edge page status returned ${response.status}`);
                const payload = await response.json();
                if (!await projectionAccepted(payload)) throw new Error("Quantum Edge page status contract or content hash mismatch");
                projection = payload;
                loadFailed = false;
                scheduleApply();
                return payload;
            } catch (error) {
                projection = null;
                loadFailed = true;
                loadPromise = null;
                document.documentElement.dataset.qadamQuantumEdgePage = "unavailable";
                console.error("Qadam Quantum Edge page projection unavailable", error);
                showUnavailablePage();
                return null;
            }
        })();
        return loadPromise;
    }

    function handleRouteChange() {
        if (!routeIsActive()) {
            if (routeWasActive) resetDisclosureState();
            routeWasActive = false;
            closeHelp();
            handledHash = "";
            return;
        }
        if (!routeWasActive) {
            resetDisclosureState();
            handledHash = "";
            forceFreshRender = true;
        }
        routeWasActive = true;
        loadProjection();
        scheduleApply();
    }

    document.addEventListener("click", (event) => {
        if (event.target?.closest?.("[data-qsase-route]")) window.setTimeout(handleRouteChange, 0);
    }, true);
    document.addEventListener("click", (event) => {
        if (!activeHelp) return;
        if (activeHelp.trigger.contains(event.target) || activeHelp.panel.contains(event.target)) return;
        closeHelp();
    });
    document.addEventListener("keydown", (event) => {
        if (event.key === "Escape" && activeHelp) closeHelp();
    });
    window.addEventListener("resize", () => activeHelp && positionHelp(activeHelp.trigger, activeHelp.panel));
    window.addEventListener("scroll", () => activeHelp && positionHelp(activeHelp.trigger, activeHelp.panel), { passive: true, capture: true });
    window.addEventListener("popstate", handleRouteChange);
    window.addEventListener("hashchange", () => {
        handledHash = "";
        deepLink({ force: true });
    });

    observer = new MutationObserver(() => {
        if (!routeIsActive()) return;
        if (!projection && !loadFailed) loadProjection();
        scheduleApply();
    });
    observer.observe(document.body, { childList: true, subtree: true });

    window.QadamQuantumEdgePage = {
        statusUrl: STATUS_URL,
        schemaVersion: SCHEMA_VERSION,
        contractVersion: CONTRACT_VERSION,
        apply: scheduleApply,
        getProjection: () => projection,
        setProjection: async (payload) => {
            if (!await projectionAccepted(payload)) {
                projection = null;
                loadFailed = true;
                showUnavailablePage();
                return false;
            }
            projection = payload;
            scheduleApply();
            return true;
        },
        disconnect: () => {
            closeHelp();
            observer?.disconnect();
        }
    };

    handleRouteChange();
})();
