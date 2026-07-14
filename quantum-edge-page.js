(() => {
    "use strict";

    const STATUS_URL = "/status/quantum-edge-page.json";
    const SCHEMA_VERSION = "qadam.QuantumEdgeThreeLayerPage.v1";
    const PANEL_SELECTOR = '[data-qsase-module-panel="patterns"][data-qsase-view-panel="nonlinear"]';
    const ROOT_SELECTOR = "[data-quantum-edge-page]";
    const PRIMARY_STATE_KEY = "qadam.quantumEdgeThreeLayer.open.v1";
    const PRIMARY_IDS = ["answer", "evidence", "consequence"];
    const PURPOSE_COPY = "Not every pattern needs quantum analysis. It is used when a relationship might involve complicated interactions, sequencing, regimes or path dependence that simpler analysis could miss. Quantum Edge is Qadam’s independent proof room for deciding whether a nonlinear or quantum-assisted method genuinely contributes something that the best conventional method missed.";
    const DEFAULT_BOUNDARY = "This is a read-only explanation of Qadam’s research evidence. It cannot submit a hardware job, change a pattern or strategy, approve risk or execution, create a paper order, write to a broker, award proof credit, or create live-capital authority.";

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
    const nestedOpenState = new Map();

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

    function tone(value) {
        const state = String(value || "").toLowerCase();
        if (/failed|decayed|conflict|error|rejected/.test(state)) return "negative";
        if (/blocked|waiting|pending|partial|prepared|incomplete|unproven|not[_ ]measurable|not[_ ]run|not[_ ]reached|unavailable|missing|provisional/.test(state)) return "waiting";
        if (/validated|complete|passed|reproduced|strengthened|available/.test(state)) return "positive";
        if (/quantum|simulation/.test(state)) return "quantum";
        return "neutral";
    }

    function stateLabel(block, fallback = "Not available") {
        return text(block?.label || block?.state_label || block?.proof_state_label || block?.scientific_verdict_label, human(block?.state || block?.status, fallback));
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
        const defaults = { answer: true, evidence: false, consequence: false };
        try {
            const stored = JSON.parse(sessionStorage.getItem(PRIMARY_STATE_KEY) || "null");
            if (!stored || typeof stored !== "object") return defaults;
            PRIMARY_IDS.forEach((id) => {
                if (typeof stored[id] === "boolean") defaults[id] = stored[id];
            });
        } catch (_error) {
            // Invalid session data must not hide the essential answer.
        }
        return defaults;
    }

    function storePrimaryState(root) {
        if (!root) return;
        const next = {};
        PRIMARY_IDS.forEach((id) => {
            next[id] = Boolean(root.querySelector(`[data-qep-primary="${id}"]`)?.open);
        });
        try {
            sessionStorage.setItem(PRIMARY_STATE_KEY, JSON.stringify(next));
        } catch (_error) {
            // The native disclosure remains usable when storage is unavailable.
        }
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
        const open = nestedOpenState.get(id) === true;
        return `
            <details class="qep-nested" data-qep-nested="${escapeHtml(id)}" ${open ? "open" : ""}>
                <summary data-qep-focus-key="nested-${escapeHtml(id)}"><span>${escapeHtml(label)}</span><i aria-hidden="true"></i></summary>
                <div class="qep-nested-body">${body}</div>
            </details>
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

    function renderAnswer() {
        const answer = projection.answer || {};
        const proofState = text(answer.proof_state_label, human(answer.proof_state || "unproven"));
        const verdict = text(answer.scientific_verdict_label, human(answer.scientific_verdict || "not_measurable"));
        const engineering = answer.engineering_checks || {};
        const market = answer.market_proof_prerequisites || {};
        return `
            <div class="qep-section-body qep-answer-body">
                <section class="qep-answer-card is-${tone(answer.proof_state)}">
                    <div>
                        <div class="qep-label-with-help"><span>Current proof state</span>${renderHelp("current-proof-state", `Explain current proof state: ${proofState}`, helpText("current_proof_state", "proof_state"))}</div>
                        <h3>${escapeHtml(proofState)}</h3>
                        <p>${escapeHtml(text(answer.plain_english_summary, "A market-level quantum edge has not been proven."))}</p>
                    </div>
                    <div class="qep-answer-verdict"><span>Scientific verdict</span><strong>${escapeHtml(verdict)}</strong></div>
                </section>
                ${renderScorePair(answer)}
                <section class="qep-content-block">
                    <header class="qep-subhead"><div><span>The proof ladder</span><h3>What Qadam must establish, in order</h3></div><small>${escapeHtml(text(answer.proof_ladder?.completed_count, 0))}/${escapeHtml(text(answer.proof_ladder?.step_count, proofSteps(answer).length))} stages reached</small></header>
                    ${renderProofLadder(answer)}
                </section>
                <div class="qep-two-column">
                    <section class="qep-content-block"><header class="qep-subhead"><div><span>Immediate blockers</span><h3>Why the claim cannot advance</h3></div></header>${renderList(answer.current_blockers, "No blocker was exported.")}</section>
                    <section class="qep-content-block"><header class="qep-subhead"><div><span>Next proof required</span><h3>What evidence would change the answer</h3></div></header>${renderList(answer.next_required_evidence, "No next evidence requirement was exported.")}</section>
                </div>
                <p class="qep-score-note">The two scores answer different questions: ${escapeHtml(scoreLabel(engineering))} describes the test rig; ${escapeHtml(scoreLabel(market))} describes the current market-proof prerequisites.</p>
            </div>
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
        return renderNested("experiment-details", "View experiment details", body);
    }

    function renderMatchedComparison(evidence) {
        const comparison = evidence.matched_classical_comparison || {};
        const state = comparison.verdict || comparison.state || "not_measurable";
        return `
            <section class="qep-content-block qep-comparison">
                <header class="qep-subhead"><div><span>Matched classical comparison</span><h3>Did the nonlinear method beat the strongest fair baseline?</h3></div>${renderHelp("matched-classical-comparison", "Explain the matched classical comparison", helpText("matched_classical_comparison", "matched_comparison"))}</header>
                <p>${escapeHtml(text(comparison.plain_english_summary || comparison.summary, "No winner exists because a fair comparison on untouched market evidence has not run."))}</p>
                <dl class="qep-fact-grid">
                    <div><dt>Current verdict</dt><dd>${escapeHtml(text(comparison.verdict_label || comparison.state_label, human(state)))}</dd></div>
                    <div><dt>Classical benchmark</dt><dd>${escapeHtml(human(comparison.classical_baseline || comparison.classical_method))}</dd></div>
                    <div><dt>Nonlinear or quantum method</dt><dd>${escapeHtml(human(comparison.quantum_method || comparison.nonlinear_method))}</dd></div>
                    <div><dt>What blocks a verdict</dt><dd>${escapeHtml(text(comparison.blocker, "Eligible untouched evidence is missing."))}</dd></div>
                </dl>
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

    function renderVerdictDefinitions(evidence) {
        const states = list(evidence.proof_state_definitions || evidence.proof_states || evidence.verdict_definitions);
        const defaults = [
            { label: "Unproven", meaning: "Required evidence is incomplete, so Qadam makes no market-edge claim." },
            { label: "Provisional", meaning: "Early evidence exists, but independent confirmation is still required." },
            { label: "Validated", meaning: "The contribution survived the defined independent market tests." },
            { label: "Classical preferred", meaning: HELP_FALLBACKS.classical_preferred },
            { label: "Decayed", meaning: "A previously useful result no longer survives current evidence." }
        ];
        const rows = states.length ? states : defaults;
        return renderNested("verdict-meanings", "What these verdicts mean", `<dl class="qep-definition-list">${rows.map((row) => `<div><dt>${escapeHtml(text(row.label, human(row.state || row.key)))}</dt><dd>${escapeHtml(text(row.meaning || row.explanation || row.summary))}</dd></div>`).join("")}</dl>`);
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
        return renderNested("certification-checks", "View certification checks", body);
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
        return renderNested("hardware-provenance", "View hardware and provenance", facts.length ? `<dl class="qep-provenance-list">${facts.map(([label, value]) => `<div><dt>${escapeHtml(label)}</dt><dd>${escapeHtml(value)}</dd></div>`).join("")}</dl>` : `<p class="qep-empty">No public hardware or provenance facts were exported.</p>`);
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
        return renderNested("operational-evidence", "View operational evidence", body);
    }

    function renderEvidence() {
        const evidence = projection.evidence || {};
        return `
            <div class="qep-section-body qep-evidence-body">
                ${renderStrongestEvidence(evidence)}
                ${renderExperiments(evidence)}
                ${renderMatchedComparison(evidence)}
                ${renderNegativeEvidence(evidence)}
                <div class="qep-two-column qep-evidence-pair">${renderHardware(evidence)}${renderPilotFacts(evidence)}</div>
                ${renderVerdictDefinitions(evidence)}
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
            <section class="qep-content-block">
                <header class="qep-subhead"><div><span>Guarded downstream route</span><h3>What could happen only after independent validation</h3></div></header>
                ${stages.length ? `<ol class="qep-route">${stages.map((stage, index) => `<li><span>${String(index + 1).padStart(2, "0")}</span><div><strong>${escapeHtml(text(stage.label || stage.title, human(typeof stage === "string" ? stage : stage.key)))}</strong>${typeof stage === "object" && (stage.explanation || stage.summary) ? `<p>${escapeHtml(stage.explanation || stage.summary)}</p>` : ""}</div></li>`).join("")}</ol>` : `<p class="qep-empty">No downstream route was exported.</p>`}
                ${route.summary || route.why_not?.reason ? `<p>${escapeHtml(text(route.summary || route.why_not.reason))}</p>` : ""}
            </section>
        `;
    }

    function renderLifecycle(consequence) {
        const lifecycle = list(consequence.hybrid_lifecycle);
        return renderNested("research-paper-lifecycle", "View the research-to-paper lifecycle", lifecycle.length ? `<ol class="qep-lifecycle">${lifecycle.map((row, index) => {
            const state = row.status || "waiting_for_evidence";
            const stageLabel = row.label || row.title || row.state || row.stage || row.key;
            return `<li class="is-${tone(state)}"><span>${String(row.number || index + 1).padStart(2, "0")}</span><div><strong>${escapeHtml(human(stageLabel))}</strong><p>${escapeHtml(text(row.explanation || row.summary))}</p></div>${renderStatusChip(text(row.status_label, human(state)), state)}</li>`;
        }).join("")}</ol>` : `<p class="qep-empty">No research-to-paper lifecycle was exported.</p>`);
    }

    function renderDailyPreview(consequence) {
        const preview = consequence.daily_explanation_preview || {};
        const raw = text(preview.text || preview.preview, "");
        const paragraphs = raw ? raw.split(/\n\s*\n/).filter(Boolean) : [];
        return renderNested("daily-explanation", "View daily explanation preview", paragraphs.length ? `${paragraphs.map((paragraph) => `<p>${escapeHtml(paragraph)}</p>`).join("")}<small>${escapeHtml(text(preview.boundary, "Read-only explanation preview. It cannot send a message or accept a command."))}</small>` : `<p class="qep-empty">No daily explanation preview was exported.</p>`);
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

    function primarySummary(id, numberLabel, title, question, status, countSummary, state) {
        return `
            <summary data-qep-primary-summary data-qep-focus-key="primary-${id}">
                <span class="qep-section-number">${numberLabel}</span>
                <div class="qep-summary-copy"><span>${escapeHtml(title)}</span><strong>${escapeHtml(question)}</strong></div>
                <div class="qep-summary-state">${renderStatusChip(status, state)}<small>${escapeHtml(countSummary)}</small></div>
                <span class="qep-summary-toggle" aria-hidden="true"><i></i></span>
            </summary>
        `;
    }

    function renderPrimarySections() {
        const answer = projection.answer || {};
        const evidence = projection.evidence || {};
        const consequence = projection.consequence || {};
        const open = primaryState();
        const hashId = window.location.hash.replace(/^#quantum-/, "");
        if (PRIMARY_IDS.includes(hashId)) open[hashId] = true;
        const proof = text(answer.proof_state_label, human(answer.proof_state || "unproven"));
        const evidenceCount = list(evidence.experiments).length || list(evidence.run_ledger).length;
        const engineeringScore = scoreLabel(answer.engineering_checks || {});
        const marketScore = scoreLabel(answer.market_proof_prerequisites || {});
        const { strategyCount, paperCount } = consequenceCounts(consequence);
        return `
            <div class="qep-primary-sections" data-qep-primary-sections>
                <details id="quantum-answer" class="qep-primary is-answer" data-qep-primary="answer" ${open.answer ? "open" : ""}>
                    ${primarySummary("answer", "01", "The answer", "Has a market-level quantum edge been proven?", proof, `${engineeringScore} engineering · ${marketScore} market prerequisites`, answer.proof_state)}
                    ${renderAnswer()}
                </details>
                <details id="quantum-evidence" class="qep-primary is-evidence" data-qep-primary="evidence" ${open.evidence ? "open" : ""}>
                    ${primarySummary("evidence", "02", "The evidence", "What was run, compared, and independently verified?", stateLabel(evidence, "Audit trail"), `${evidenceCount} experiment records · ${engineeringScore} engineering · ${marketScore} market prerequisites`, evidence.status || "neutral")}
                    ${renderEvidence()}
                </details>
                <details id="quantum-consequence" class="qep-primary is-consequence" data-qep-primary="consequence" ${open.consequence ? "open" : ""}>
                    ${primarySummary("consequence", "03", "The consequence", "Did this change a validated strategy or paper decision?", stateLabel(consequence, strategyCount || paperCount ? "Downstream impact recorded" : "No downstream change"), `${strategyCount} strategies · ${paperCount} paper decisions`, consequence.status || (strategyCount || paperCount ? "validated" : "waiting_for_evidence"))}
                    ${renderConsequence()}
                </details>
            </div>
        `;
    }

    function renderGuidance() {
        const guidance = projection.page_explainer?.guidance || {};
        const questions = list(guidance.questions).length ? list(guidance.questions) : [
            "Can Qadam access the required technology?",
            "Was an actual hardware experiment executed?",
            "Can the result be reproduced?",
            "Did it beat the strongest fair classical comparison?",
            "Did that advantage survive completely untouched market data?",
            "Did it ultimately improve a governed paper decision?"
        ];
        const outcomes = list(guidance.possible_outcomes).length ? list(guidance.possible_outcomes) : [
            "Strengthen the evidence.",
            "Agree with the classical result.",
            "Lose to the classical method.",
            "Weaken the original pattern.",
            "Remain unmeasurable because evidence is missing."
        ];
        return `
            <div id="qep-purpose-guidance" class="qep-guidance" data-qep-guidance ${introExpanded ? "" : "hidden"}>
                <p>${escapeHtml(text(guidance.introduction, "If you're wondering what this page is trying to establish... It asks six progressively harder questions:"))}</p>
                <ul>${questions.map((question) => `<li>${escapeHtml(question)}</li>`).join("")}</ul>
                <p>${escapeHtml(text(guidance.outcome_introduction, "A quantum method can therefore:"))}</p>
                <ul>${outcomes.map((outcome) => `<li>${escapeHtml(outcome)}</li>`).join("")}</ul>
                <p class="qep-guidance-note">${escapeHtml(text(guidance.note, "Note: “Classical preferred” is a perfectly successful scientific outcome: Qadam learns that the simpler method is sufficient."))}</p>
            </div>
        `;
    }

    function renderPage() {
        const answer = projection.answer || {};
        const pageExplainer = projection.page_explainer || {};
        const conclusion = text(pageExplainer.current_conclusion || answer.current_conclusion, `${text(answer.proof_state_label, human(answer.proof_state || "Unproven"))} — ${text(answer.scientific_verdict_label, human(answer.scientific_verdict || "market advantage not measurable yet"))}.`);
        const boundary = text(projection.boundary || projection.authority?.plain_english_boundary || projection.authority?.boundary || pageExplainer.authority_boundary, DEFAULT_BOUNDARY);
        const freshness = projection.generated_at ? `Evidence projection updated ${new Date(projection.generated_at).toLocaleString(undefined, { dateStyle: "medium", timeStyle: "short" })}` : "Evidence projection time unavailable";
        return `
            <section class="qep-page" data-quantum-edge-page data-qep-content-hash="${escapeHtml(projection.content_hash)}" aria-labelledby="qep-page-title">
                <header class="qep-header">
                    <span>${escapeHtml(text(pageExplainer.eyebrow, "Quantum Research"))}</span>
                    <h2 id="qep-page-title">${escapeHtml(text(pageExplainer.title, "Quantum Edge"))}</h2>
                    <p class="qep-purpose">${escapeHtml(text(pageExplainer.purpose_paragraph, PURPOSE_COPY))}</p>
                    <button type="button" class="qep-read-more" data-qep-read-more data-qep-focus-key="read-more" aria-expanded="${introExpanded ? "true" : "false"}" aria-controls="qep-purpose-guidance">${escapeHtml(introExpanded ? text(pageExplainer.read_less_label, "Read less −") : text(pageExplainer.read_more_label, "Read more +"))}</button>
                    ${renderGuidance()}
                </header>
                <p class="qep-current-conclusion is-${tone(answer.proof_state)}" data-qep-current-conclusion role="status" aria-live="polite"><span>Current conclusion</span><strong>${escapeHtml(conclusion)}</strong></p>
                ${renderPrimarySections()}
                <footer class="qep-boundary"><p>${escapeHtml(boundary)}</p><small>${escapeHtml(freshness)}</small></footer>
            </section>
        `;
    }

    function renderUnavailablePage() {
        return `
            <section class="qep-page qep-unavailable-page" data-quantum-edge-page data-qep-unavailable aria-labelledby="qep-page-title">
                <header class="qep-header">
                    <span>Quantum Research</span>
                    <h2 id="qep-page-title">Quantum Edge</h2>
                    <p class="qep-purpose">${escapeHtml(PURPOSE_COPY)}</p>
                </header>
                <p class="qep-current-conclusion is-waiting" role="status" aria-live="polite"><span>Current proof unavailable</span><strong>Qadam cannot verify the current Quantum Edge projection, so no proof state or score is being shown.</strong></p>
                <section class="qep-unavailable-card">
                    <div><span>Fail-closed evidence view</span><h3>The scientific record could not be loaded safely</h3><p>The page has not inferred a verdict, reused an old count, or treated a missing test as a failure. You can retry the same read-only status request.</p></div>
                    <button type="button" data-qep-retry data-qep-focus-key="retry">Retry</button>
                </section>
                <footer class="qep-boundary"><p>${escapeHtml(DEFAULT_BOUNDARY)}</p><small>No research, provider, strategy, risk, execution, order, broker, proof, or capital state was changed.</small></footer>
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
            readMore.textContent = introExpanded ? text(projection.page_explainer?.read_less_label, "Read less −") : text(projection.page_explainer?.read_more_label, "Read more +");
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
        root.querySelectorAll("[data-qep-nested]").forEach((details) => {
            details.addEventListener("toggle", () => {
                nestedOpenState.set(details.dataset.qepNested, details.open);
                if (!details.open && details.contains(document.activeElement) && document.activeElement !== details.querySelector(":scope > summary")) {
                    details.querySelector(":scope > summary")?.focus({ preventScroll: true });
                }
                if (!details.open && activeHelp?.trigger && details.contains(activeHelp.trigger)) closeHelp();
            });
        });
        bindHelp(root);
    }

    function deepLink({ force = false } = {}) {
        const hash = window.location.hash;
        if (!PRIMARY_IDS.some((id) => hash === `#quantum-${id}`)) return;
        if (!force && handledHash === hash) return;
        const root = document.querySelector(ROOT_SELECTOR);
        const details = root?.querySelector(hash);
        const summary = details?.querySelector(":scope > summary");
        if (!details || !summary) return;
        details.open = true;
        storePrimaryState(root);
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
        if (existing?.dataset.qepContentHash === projection.content_hash) {
            deepLink();
            return;
        }
        const focusKey = captureFocusKey(existing);
        if (activeHelp?.trigger && existing?.contains(activeHelp.trigger)) closeHelp({ restoreFocus: true });
        const lifecycle = Array.from(panel.children).find((child) => child.matches?.("[data-qadam-lifecycle]"));
        Array.from(panel.children).forEach((child) => {
            if (child !== lifecycle) child.remove();
        });
        const wrapper = document.createElement("div");
        wrapper.innerHTML = renderPage().trim();
        const root = wrapper.firstElementChild;
        panel.appendChild(root);
        bindPage(root);
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
        Array.from(panel.children).forEach((child) => {
            if (child !== lifecycle) child.remove();
        });
        const wrapper = document.createElement("div");
        wrapper.innerHTML = renderUnavailablePage().trim();
        const root = wrapper.firstElementChild;
        panel.appendChild(root);
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
                if (payload?.schema_version !== SCHEMA_VERSION) throw new Error("Quantum Edge page status schema mismatch");
                projection = payload;
                loadFailed = false;
                scheduleApply();
                return payload;
            } catch (error) {
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
            closeHelp();
            handledHash = "";
            return;
        }
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
        apply: scheduleApply,
        getProjection: () => projection,
        setProjection: (payload) => {
            if (payload?.schema_version !== SCHEMA_VERSION) throw new Error("Quantum Edge page status schema mismatch");
            projection = payload;
            scheduleApply();
        },
        disconnect: () => {
            closeHelp();
            observer?.disconnect();
        }
    };

    handleRouteChange();
})();
