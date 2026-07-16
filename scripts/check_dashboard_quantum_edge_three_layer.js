#!/usr/bin/env node

"use strict";

const fs = require("fs");
const path = require("path");

const repoRoot = path.resolve(__dirname, "..");
const siteRoot = path.resolve(process.argv[2] || path.join(repoRoot, "landing-page-repo"));

function readSite(relativePath) {
    return fs.readFileSync(path.join(siteRoot, relativePath), "utf8");
}

function assert(condition, message) {
    if (!condition) throw new Error(message);
}

function occurrences(source, pattern) {
    return (source.match(pattern) || []).length;
}

function functionBody(source, name) {
    const marker = `function ${name}(`;
    const start = source.indexOf(marker);
    assert(start >= 0, `Quantum Edge renderer is missing ${name}()`);
    const brace = source.indexOf("{", start);
    assert(brace >= 0, `Quantum Edge renderer has an invalid ${name}() declaration`);
    let depth = 0;
    let quote = "";
    let escaped = false;
    let templateExpressionDepth = 0;
    for (let index = brace; index < source.length; index += 1) {
        const character = source[index];
        const next = source[index + 1];
        if (escaped) {
            escaped = false;
            continue;
        }
        if (quote) {
            if (character === "\\") {
                escaped = true;
            } else if (quote === "`" && character === "$" && next === "{") {
                templateExpressionDepth += 1;
                index += 1;
            } else if (quote === "`" && character === "}" && templateExpressionDepth > 0) {
                templateExpressionDepth -= 1;
            } else if (character === quote && templateExpressionDepth === 0) {
                quote = "";
            }
            continue;
        }
        if (character === "\"" || character === "'" || character === "`") {
            quote = character;
            continue;
        }
        if (character === "/" && next === "/") {
            const newline = source.indexOf("\n", index + 2);
            index = newline < 0 ? source.length : newline;
            continue;
        }
        if (character === "/" && next === "*") {
            const close = source.indexOf("*/", index + 2);
            index = close < 0 ? source.length : close + 1;
            continue;
        }
        if (character === "{") depth += 1;
        if (character === "}") {
            depth -= 1;
            if (depth === 0) return source.slice(brace + 1, index);
        }
    }
    throw new Error(`Quantum Edge renderer has an unterminated ${name}() body`);
}

const purposeCopy = "Not every pattern needs quantum analysis. It is used when a relationship might involve complicated interactions, sequencing, regimes or path dependence that simpler analysis could miss. Quantum Edge is Qadam’s independent proof room for deciding whether a nonlinear or quantum-assisted method genuinely contributes something that the best conventional method missed. The framework presents the experiment record first, then any strategy and paper impact, and closes with the formal market-level verdict.";
const guidanceIntroduction = "Quantum analysis earns a role in Qadam’s research process only when it clears six increasingly demanding standards—from infrastructure access to measurable decision value under paper-trading governance.";
const guidanceWorkflowLabels = [
    "Evidence assembly",
    "Classical discovery",
    "Quantum exploration",
    "Matched comparison",
    "Standard validation"
];
const guidanceWorkflowTitles = [
    "Python prepares the evidence",
    "Classical models search for patterns",
    "The quantum lane examines selected problems",
    "Both lanes are compared fairly",
    "Ordinary validation still applies"
];
const guidanceOperatingModelTitle = "Hybrid by design—not a standalone quantum computer.";
const guidanceCurrentCapabilityTitle = "Experimental pathway implemented; IBM hardware proof pending.";
const guidanceQuestions = [
    "Can Qadam access the required technology?",
    "Was an actual hardware experiment executed?",
    "Can the result be reproduced?",
    "Did it beat the strongest fair classical comparison?",
    "Did that advantage survive completely untouched market data?",
    "Did it ultimately improve a governed paper decision?"
];
const guidanceProofLabels = [
    "Infrastructure readiness",
    "Hardware execution",
    "Result reproducibility",
    "Matched classical benchmark",
    "Untouched holdout validation",
    "Governed paper-decision impact"
];
const guidanceOutcomeIntroduction = "The evidence can support one of five governed conclusions.";
const guidanceOutcomes = [
    "Strengthen the evidence.",
    "Agree with the classical result.",
    "Lose to the classical method.",
    "Weaken the original pattern.",
    "Remain unmeasurable because evidence is missing."
];
const guidanceOutcomeLabels = [
    "Incremental quantum evidence",
    "Corroborated classical signal",
    "Classical method preferred",
    "Original thesis weakened",
    "Insufficient evidence"
];
const guidanceTakeawayTitle = "A classical-preferred result is a successful research outcome.";

const status = JSON.parse(readSite("status/quantum-edge-page.json"));
const sourceMirrors = {
    wave_f: JSON.parse(readSite("status/quantum-edge-wave-f.json")),
    wave_g: JSON.parse(readSite("status/quantum-edge-wave-g.json")),
    wave_h: JSON.parse(readSite("status/quantum-edge-wave-h.json"))
};
const script = readSite("quantum-edge-page.js");
const stylesheet = readSite("quantum-edge-page.css");
const auth = readSite("auth.js");
const dashboardHtml = readSite("dashboard/index.html");
const dashboardRenderer = readSite("dashboard.js");
const waveF = readSite("quantum-edge-wave-f.js");

// The public projection is the sole truth contract for this page.
assert(status.schema_version === "qadam.QuantumEdgeThreeLayerPage.v1", "Quantum Edge page schema mismatch");
assert(status.copy_version === "quantum-edge-elegant-simplification-v1", "Quantum Edge guidance copy version is stale");
assert(status.contract_version === "quantum-edge-elegant-v1", "Quantum Edge elegant presentation contract is missing");
assert(status.projection_status === "ready", "Quantum Edge page projection is not ready");
assert(status.source_lineage?.content_hashes_verified === true, "Quantum Edge source hashes are not verified");
assert(status.source_lineage?.semantic_coherence_passed === true, "Quantum Edge source semantics are incoherent");
assert((status.source_lineage?.integrity_errors || []).length === 0, "Quantum Edge projection has integrity errors");
assert((status.source_lineage?.semantic_errors || []).length === 0, "Quantum Edge projection has semantic errors");
assert(/^[0-9a-f]{64}$/.test(status.content_hash || ""), "Quantum Edge page content hash is malformed");
assert(/^[0-9a-f]{64}$/.test(status.render_contract_hash || ""), "Quantum Edge render-contract hash is malformed");
const projectedSourceHashes = Object.fromEntries(
    (status.source_artifacts || []).map((source) => [source.source_id, source.content_hash])
);
Object.entries(sourceMirrors).forEach(([sourceId, source]) => {
    assert(
        projectedSourceHashes[sourceId] === source.content_hash,
        `Quantum Edge ${sourceId} mirror does not match the canonical page projection`
    );
});

// The requested explainer copy is exact and lives in both the projection and renderer fallback.
assert(status.page_explainer?.purpose_paragraph === purposeCopy, "Quantum Edge purpose paragraph changed");
assert(status.page_explainer?.eyebrow === "Quantum Benchmark Framework", "Quantum Edge page eyebrow changed");
assert(status.page_copy?.eyebrow === "Quantum Benchmark Framework", "Quantum Edge locked page eyebrow changed");
assert(status.page_copy?.title === "Quantum Edge", "Quantum Edge locked page title changed");
assert(status.page_copy?.subtitle === purposeCopy, "Quantum Edge locked page subtitle changed");
assert(script.includes(`const PURPOSE_COPY = ${JSON.stringify(purposeCopy)}`), "Quantum Edge renderer purpose fallback changed");
assert(script.includes('const PAGE_EYEBROW = "Quantum Benchmark Framework"'), "Quantum Edge renderer eyebrow fallback changed");
assert(status.page_explainer?.read_more_label === "How Qadam researches, finds evidence and makes a conclusion", "Quantum Edge Read more label changed");
assert(status.page_explainer?.read_less_label === "Minimize -", "Quantum Edge Read less label changed");
assert(status.page_explainer?.guidance?.eyebrow === "Quantum research mandate", "Quantum Edge guidance eyebrow changed");
assert(status.page_explainer?.guidance?.introduction === guidanceIntroduction, "Quantum Edge guidance introduction changed");
assert(status.page_explainer?.guidance?.workflow_heading === "How the hybrid research loop works", "Quantum Edge hybrid workflow heading changed");
assert((status.page_explainer?.guidance?.workflow_steps || []).length === 5, "Quantum Edge must expose five hybrid workflow steps");
assert(
    JSON.stringify(status.page_explainer.guidance.workflow_steps.map((step) => step.label)) === JSON.stringify(guidanceWorkflowLabels),
    "Quantum Edge hybrid workflow labels changed"
);
assert(
    JSON.stringify(status.page_explainer.guidance.workflow_steps.map((step) => step.title)) === JSON.stringify(guidanceWorkflowTitles),
    "Quantum Edge hybrid workflow titles changed"
);
assert(status.page_explainer?.guidance?.operating_model?.title === guidanceOperatingModelTitle, "Quantum Edge hybrid operating-model caveat changed");
assert(status.page_explainer?.guidance?.current_capability?.title === guidanceCurrentCapabilityTitle, "Quantum Edge current capability caveat changed");
assert(status.page_explainer?.guidance?.current_capability?.local_simulation_reproduced === true, "Quantum Edge must state the reproduced local simulation truthfully");
assert(status.page_explainer?.guidance?.current_capability?.provider_accessible === true, "Quantum Edge must state the configured provider access truthfully");
assert(status.page_explainer?.guidance?.current_capability?.hardware_authorized === false, "Quantum Edge must not imply hardware authorization");
assert(status.page_explainer?.guidance?.current_capability?.hardware_submitted === false, "Quantum Edge must not imply hardware submission");
assert(status.page_explainer?.guidance?.current_capability?.hardware_completed === false, "Quantum Edge must not imply hardware completion");
assert(JSON.stringify(status.page_explainer?.guidance?.questions) === JSON.stringify(guidanceQuestions), "Quantum Edge six-question guidance changed");
assert(status.page_explainer?.guidance?.proof_heading === "Six standards of evidence", "Quantum Edge proof heading changed");
assert((status.page_explainer?.guidance?.proof_steps || []).length === 6, "Quantum Edge must expose six structured proof steps");
assert(
    JSON.stringify(status.page_explainer.guidance.proof_steps.map((step) => step.label)) === JSON.stringify(guidanceProofLabels),
    "Quantum Edge structured proof labels changed"
);
assert(
    JSON.stringify(status.page_explainer.guidance.proof_steps.map((step) => step.question)) === JSON.stringify(guidanceQuestions),
    "Quantum Edge structured proof questions do not match the canonical ladder"
);
assert(status.page_explainer?.guidance?.outcome_introduction === guidanceOutcomeIntroduction, "Quantum Edge outcome introduction changed");
assert(JSON.stringify(status.page_explainer?.guidance?.possible_outcomes) === JSON.stringify(guidanceOutcomes), "Quantum Edge possible outcomes changed");
assert(status.page_explainer?.guidance?.outcome_heading === "Permissible research conclusions", "Quantum Edge outcome heading changed");
assert((status.page_explainer?.guidance?.outcome_states || []).length === 5, "Quantum Edge must expose five structured outcome states");
assert(
    JSON.stringify(status.page_explainer.guidance.outcome_states.map((outcome) => outcome.label)) === JSON.stringify(guidanceOutcomeLabels),
    "Quantum Edge outcome labels changed"
);
assert(status.page_explainer?.guidance?.takeaway?.label === "Research reminder", "Quantum Edge takeaway label changed");
assert(status.page_explainer?.guidance?.takeaway?.title === guidanceTakeawayTitle, "Quantum Edge classical-preferred takeaway changed");
[guidanceIntroduction, guidanceOperatingModelTitle, guidanceCurrentCapabilityTitle, guidanceOutcomeIntroduction, guidanceTakeawayTitle, ...guidanceWorkflowLabels, ...guidanceWorkflowTitles, ...guidanceQuestions, ...guidanceProofLabels, ...guidanceOutcomeLabels]
    .forEach((copy) => assert(script.includes(copy), `Quantum Edge renderer fallback is missing: ${copy}`));
assert(script.includes('data-qep-read-more'), "Quantum Edge Read more control is missing");
assert(script.includes('data-qep-guidance-close'), "Quantum Edge bottom minimize control is missing");
assert(script.includes('data-qep-matched-evidence'), "Quantum Edge matched evidence rows are missing");
assert(script.includes('/assets/ibm-quantum-computer.jpg'), "Quantum Edge IBM hardware image is missing");
assert(script.includes('aria-controls="qep-purpose-guidance"'), "Quantum Edge Read more control does not identify its guidance panel");
assert(script.includes('aria-expanded="${introExpanded ? "true" : "false"}"'), "Quantum Edge Read more state is not exposed accessibly");
assert(script.includes('<ol class="qep-guidance-steps"'), "Quantum Edge proof ladder is not an ordered list");
assert(script.includes('<ol class="qep-guidance-workflow-steps"'), "Quantum Edge hybrid research flow is not an ordered list");
assert(script.includes('data-qep-guidance-workflow-step='), "Quantum Edge hybrid workflow markup is missing");
assert(script.includes('data-qep-guidance-operating-model'), "Quantum Edge hybrid operating-model caveat is missing");
assert(script.includes('data-qep-guidance-current-capability'), "Quantum Edge current capability caveat is missing");
assert(stylesheet.includes(".qep-primary[open]"), "Quantum Edge selected-section border state is missing");
assert(stylesheet.includes(".qep-matched-evidence"), "Quantum Edge matched evidence styling is missing");
assert(stylesheet.includes(".qep-quantum-hero-image"), "Quantum Edge IBM hardware image styling is missing");
assert(script.includes('data-qep-guidance-step='), "Quantum Edge structured proof-step markup is missing");
assert(script.includes('<ul class="qep-guidance-outcomes"'), "Quantum Edge outcome list is missing");
assert(script.includes('<aside class="qep-guidance-takeaway"'), "Quantum Edge research-discipline callout is missing");
[
    ".qep-guidance-steps",
    ".qep-guidance-workflow-steps",
    ".qep-guidance-boundaries",
    ".qep-guidance-step-number",
    ".qep-guidance-outcomes",
    ".qep-guidance-takeaway"
].forEach((selector) => assert(stylesheet.includes(selector), `Quantum Edge guidance styling is missing ${selector}`));

// There are exactly three ordered, independently operable primary disclosures.
const expectedOrder = ["evidence", "consequence", "answer"];
assert(JSON.stringify(status.presentation?.section_order) === JSON.stringify(expectedOrder), "Quantum Edge projection section order changed");
assert(Object.keys(status.presentation?.rows || {}).length === 3 && expectedOrder.every((id) => status.presentation.rows[id]), "Quantum Edge projection rows changed");
assert(expectedOrder.every((id) => status.presentation.rows[id]?.collapsed_by_default === true), "Quantum Edge rows are not default-collapsed in the projection");
assert(expectedOrder.every((id) => String(status.presentation.rows[id]?.summary || "").trim()), "Quantum Edge collapsed rows are missing qualitative summaries");
const primaryMarkup = Array.from(script.matchAll(/<details id="quantum-([a-z]+)" class="qep-primary[^\n]+data-qep-primary="([a-z]+)"/g));
assert(primaryMarkup.length === 3, `Quantum Edge must render exactly three primary sections, found ${primaryMarkup.length}`);
assert(
    JSON.stringify(primaryMarkup.map((match) => match[1])) === JSON.stringify(expectedOrder)
        && primaryMarkup.every((match) => match[1] === match[2]),
    "Quantum Edge primary sections are missing or out of order"
);
[
    ["Experiment & Evidence", "What was run, what was compared, and what was verified?"],
    ["Strategy & Paper Impact", "Did this change a validated strategy or paper decision?"],
    ["Quantum Edge Verdict", "Has a genuine market-level quantum advantage been proven?"]
].forEach(([title, question]) => {
    assert(script.includes(`"${title}"`), `Quantum Edge section title is missing: ${title}`);
    assert(script.includes(`"${question}"`), `Quantum Edge section question is missing: ${question}`);
});
assert(script.includes("let primaryOpenState = { evidence: false, consequence: false, answer: false }"), "Quantum Edge default-collapsed contract changed");
assert(script.includes("let technicalOpen = false"), "Quantum Edge technical evidence does not default closed");
assert(script.includes("function resetDisclosureState()"), "Quantum Edge cannot reset disclosures on fresh entry");
assert(script.includes("forceFreshRender = true"), "Quantum Edge route re-entry does not force a fresh collapsed render");
assert(!script.includes("PRIMARY_STATE_KEY"), "Quantum Edge must not restore old disclosure state");
assert(!script.includes("sessionStorage.getItem"), "Quantum Edge must not reopen rows from session storage");
assert(!script.includes("sessionStorage.setItem"), "Quantum Edge must keep primary disclosure state in memory only");
assert(script.includes('root.querySelectorAll("[data-qep-primary]").forEach'), "Quantum Edge primary disclosures are not bound independently");
assert(!/PRIMARY_IDS[^\n]+(?:exclusive|accordion|active)/i.test(script), "Quantum Edge primary disclosures appear to enforce a single-open accordion");
assert(status.presentation?.technical_record?.closed_by_default === true, "Quantum Edge technical record is not default closed");
assert(status.presentation?.technical_record?.label === "View technical evidence", "Quantum Edge technical record label changed");
assert(script.includes('data-qep-technical'), "Quantum Edge technical evidence disclosure is missing");
assert(occurrences(script, /data-qep-technical(?:\s|>)/g) >= 1, "Quantum Edge technical disclosure markup is missing");
assert(script.includes('data-qep-technical-close'), "Quantum Edge technical disclosure has no explicit collapse control");
assert(script.includes('data-qep-fair-comparison-protocol'), "Quantum Edge technical record omits the fair-comparison protocol");
assert(script.includes('data-qep-technical-route'), "Quantum Edge technical record omits the governed downstream route");
assert(script.includes('class="qep-technical-index"'), "Quantum Edge technical record omits its projection-owned index");
assert(script.includes("projectionHashMatches"), "Quantum Edge renderer does not verify the render-contract hash");
assert(script.includes("payload.render_contract_hash"), "Quantum Edge renderer does not bind the render-contract hash");
assert(!/qep-simple-(?:evidence|impact|verdict)[\s\S]{0,220}<details/i.test(script), "Quantum Edge primary content contains a nested disclosure");
assert(status.presentation?.evidence?.conventional_lane?.details?.length === 4, "Classical lane lacks the four-field comparison contract");
assert(status.presentation?.evidence?.quantum_lane?.details?.length === 4, "Quantum lane lacks the four-field comparison contract");
assert(
    JSON.stringify(status.presentation.evidence.conventional_lane.details.map((row) => row.key))
        === JSON.stringify(status.presentation.evidence.quantum_lane.details.map((row) => row.key)),
    "Classical and quantum lane fields are not symmetrical"
);
assert(status.presentation?.impact?.outcomes?.length === 2, "Quantum impact lacks explicit strategy and paper-decision outcomes");
assert(status.presentation?.verdict?.statements?.length === 3, "Quantum verdict lacks its three plain-English conclusion statements");
assert(
    JSON.stringify(status.presentation.verdict.statements.map((row) => row.key)) === JSON.stringify(["known", "cannot_claim", "next"]),
    "Quantum verdict conclusion order changed"
);

// Five independent axes own mutable truth; presentation is a derived renderer contract.
const axes = status.state_axes || {};
assert(Object.keys(axes).length === 5 && ["proof", "comparison", "execution", "downstream", "freshness"].every((key) => axes[key] && typeof axes[key] === "object"), "Quantum Edge state axes changed");
assert(axes.proof.key === "unproven" && axes.proof.label === "Unproven", "Quantum Edge proof axis overstates the result");
assert(!Object.prototype.hasOwnProperty.call(axes.proof, "scientific_verdict"), "Quantum Edge proof axis improperly owns the comparison outcome");
assert(axes.comparison.key === "not_measurable" && axes.comparison.eligible === false, "Quantum Edge comparison axis invents a fair winner");
assert(Array.isArray(axes.comparison.eligibility_checks) && axes.comparison.eligibility_checks.length === 8, "Quantum Edge fair-comparison contract must contain eight checks");
assert(script.includes("Eight conditions required before either method can win"), "Quantum Edge technical record does not explain the eight fair-comparison conditions");
assert(axes.execution.local_simulation_reproduced === true, "Quantum Edge execution axis hides local reproduction");
assert(axes.execution.provider_accessible === true, "Quantum Edge execution axis hides provider access");
assert(axes.execution.hardware_authorized === false && axes.execution.hardware_submitted === false && axes.execution.hardware_completed === false, "Quantum Edge execution axis invents hardware execution");
assert(axes.downstream.key === "no_downstream_change" && axes.downstream.strategy_count === 0 && axes.downstream.paper_decision_count === 0, "Quantum Edge downstream axis invents impact");
assert(axes.freshness.key === "current", "Quantum Edge freshness axis is not current");
const impactGates = status.presentation?.impact?.gates || [];
assert(impactGates.length === 4, "Quantum Edge primary consequence must expose exactly four gates");
assert(JSON.stringify(impactGates.map((gate) => gate.label)) === JSON.stringify([
    "Does the experiment work?",
    "Does hardware evidence exist?",
    "Does the market comparison hold up?",
    "Did it improve a strategy or paper decision?"
]), "Quantum Edge four gate questions changed");
const primaryMetricText = JSON.stringify({ evidence: status.presentation?.evidence, verdict: status.presentation?.verdict });
assert(!/11\/11|1\/6|source_count|pilot_instrument_count|method_count|eligible_window_count|0 strategies changed/i.test(primaryMetricText), "Quantum Edge primary projection leaked technical counts");
assert((status.presentation?.verdict?.metrics || []).length === 3, "Quantum Edge verdict must expose exactly three qualitative statuses");
assert(stylesheet.includes(".qep-verdict-statements"), "Quantum Edge verdict statement styling is missing");
assert(
    /\.qep-verdict-result\s*>\s*h3\s*\{[^}]*clamp\(1\.65rem,\s*3\.2vw,\s*2\.45rem\)/s.test(stylesheet),
    "Quantum Edge final verdict is not kept at the restrained display size"
);
assert(!/\.qep-verdict-result\s*>\s*h3\s*\{[^}]*text-transform:\s*uppercase/s.test(stylesheet), "Quantum Edge final verdict should not shout in uppercase");
assert(stylesheet.includes(".qep-primary.is-answer"), "Quantum Edge verdict chapter lacks its waiting-state accent");

// One canonical fetch owns one deduplicated render root; prior Wave owners are disabled.
assert(occurrences(script, /fetch\(/g) === 1, "Quantum Edge renderer must make exactly one canonical fetch");
const releaseIdMatch = dashboardHtml.match(/<meta name="qadam-dashboard-release" content="qadam-dashboard-([^"]+)"/);
assert(releaseIdMatch, "Dashboard release identity is missing");
const releaseCacheKey = releaseIdMatch[1];
assert(
    script.includes(`const STATUS_URL = "/status/quantum-edge-page.json?v=${releaseCacheKey}"`),
    "Quantum Edge renderer projection cache key does not match the dashboard release"
);
assert(script.includes('credentials: "same-origin"'), "Quantum Edge projection fetch is not same-origin");
assert(occurrences(script, /<section class="qep-page" data-quantum-edge-page/g) === 1, "Quantum Edge renderer must define one page root");
assert(script.includes("roots.slice(1).forEach((root) => root.remove())"), "Quantum Edge renderer does not remove duplicate roots");
assert(
    script.includes("if (child !== lifecycle && child !== handoff) child.remove()"),
    "Quantum Edge renderer does not atomically clear prior nonlinear owners while preserving the shared handoff"
);
assert(occurrences(auth, /\/quantum-edge-page\.js\?v=/g) === 1, "Dashboard must load the Quantum Edge page script exactly once");
assert(occurrences(auth, /\/quantum-edge-page\.css\?v=/g) === 1, "Dashboard must load the Quantum Edge page stylesheet exactly once");
assert(auth.includes(`/quantum-edge-page.js?v=${releaseCacheKey}`), "Quantum Edge script cache key does not match the dashboard release");
assert(auth.includes(`/quantum-edge-page.css?v=${releaseCacheKey}`), "Quantum Edge stylesheet cache key does not match the dashboard release");
assert(!/quantum-edge-wave-[gh]\.(?:js|css)/i.test(auth), "Wave G or Wave H still owns Quantum Edge through auth.js");
const routeLoader = functionBody(auth, "loadQuantumDashboardRouteAssets");
assert(routeLoader.includes('moduleId === "patterns" && viewId === "nonlinear"'), "Canonical Quantum Edge assets are not route-scoped");
assert(routeLoader.includes("loadQuantumEdgePageAssets()"), "Canonical Quantum Edge route does not load the page assets");
assert(!routeLoader.match(/nonlinear[\s\S]{0,180}loadQuantumEdgeWaveFAssets\(\)/), "Nonlinear route still loads the Wave F projection");
const waveFApply = functionBody(waveF, "applyProjection");
assert(waveFApply.includes("VIEW_SELECTORS.pattern"), "Wave F no longer owns Pattern Recognition");
assert(waveFApply.includes("VIEW_SELECTORS.strategies"), "Wave F no longer owns Trading Strategies");
assert(!/VIEW_SELECTORS\.(?:quantum|nonlinear)|renderQuantumEdge\(/.test(waveFApply), "Wave F still owns the nonlinear Quantum Edge panel");

// Deep links, focus continuity, keyboard/touch help, and live-region discipline are explicit.
expectedOrder.forEach((id) => assert(script.includes(`#quantum-${id}`) || script.includes("`#quantum-${id}`"), `Quantum Edge deep-link handling is missing ${id}`));
assert(script.includes('window.addEventListener("hashchange"'), "Quantum Edge hash changes are not handled");
assert(script.includes("details.scrollIntoView"), "Quantum Edge deep links do not reveal their destination");
assert(script.includes("captureFocusKey"), "Quantum Edge rerenders do not preserve focus identity");
assert(script.includes('data-qep-focus-key'), "Quantum Edge controls do not expose stable focus keys");
assert(script.includes("focus({ preventScroll: true })"), "Quantum Edge does not restore focus after disclosure changes");
const politeStatusMarkupCount = occurrences(script, /role="status" aria-live="polite"/g);
assert(politeStatusMarkupCount >= 1, "Quantum Edge conclusion is not a polite status region");
assert(occurrences(script, /aria-live=/g) === politeStatusMarkupCount, "Quantum Edge uses live announcements outside its mutually exclusive status states");
assert(script.includes('<button type="button" class="qep-help-trigger"'), "Quantum Edge help triggers are not semantic buttons");
["aria-label", "aria-expanded", "aria-controls", "aria-describedby"].forEach((attribute) => {
    assert(script.includes(`${attribute}=`), `Quantum Edge help controls are missing ${attribute}`);
});
assert(script.includes('role="tooltip"'), "Quantum Edge help popovers lack tooltip semantics");
assert(script.includes('trigger.addEventListener("pointerenter"'), "Quantum Edge help lacks pointer hover support");
assert(script.includes('trigger.addEventListener("focus"'), "Quantum Edge help lacks keyboard focus support");
assert(script.includes('trigger.addEventListener("click"'), "Quantum Edge help lacks touch/click pinning");
assert(script.includes('event.key === "Escape"'), "Quantum Edge help cannot be dismissed with Escape");
assert(script.includes("if (activeHelp.trigger.contains(event.target) || activeHelp.panel.contains(event.target)) return"), "Quantum Edge help lacks outside-click dismissal");
assert(script.includes("activeHelp.pinned"), "Quantum Edge help cannot remain pinned for touch users");
assert(script.includes('helpText("ibm_hardware", "hardware_execution")'), "Quantum Edge hardware experiment help is not stateful");
assert(!script.includes("${marketScore} market prerequisites"), "Collapsed Evidence summary still foregrounds a technical score");
assert(dashboardRenderer.includes('class="qsase-quantum-fallback-sections"'), "Quantum Edge fallback lacks the three-layer hierarchy");
["Experiment &amp; Evidence", "Strategy &amp; Paper Impact", "Quantum Edge Verdict"].forEach((label) => {
    assert(dashboardRenderer.includes(`<strong>${label}</strong>`), `Quantum Edge fallback is missing ${label}`);
});
assert(!/<details open>[\s\S]{0,180}<summary><span>0[1-3]<\/span><strong>(?:Experiment|Strategy|Quantum)/.test(dashboardRenderer), "Quantum Edge fallback must be collapsed by default");
assert(!dashboardRenderer.includes('<main class="qsase-module-workspace" aria-live='), "Dashboard workspace must not announce the entire Quantum Edge replacement");

// Every non-technical truth topic requested in the design has a visible help route.
[
    "engineering_control",
    "local_quantum_simulation",
    "paired_scores",
    "provider_access",
    "hardware_execution",
    "untouched_holdout",
    "matched_comparison",
    "classical_preferred",
    "classified_windows",
    "provider_history",
    "strategy_influence",
    "paper_outcome"
].forEach((key) => assert(new RegExp(`\\b${key}:`).test(script), `Quantum Edge help copy is missing ${key}`));
[
    "engineering_vs_market_proof",
    "ibm_hardware",
    "local_quantum_simulation",
    "matched_classical_comparison",
    "classified_vs_eligible_windows",
    "provider_history_rows",
    "completed_provider_partitions",
    "strategy_influence",
    "paper_outcome_lineage"
].forEach((key) => assert(script.includes(`helpText("${key}"`), `Quantum Edge does not render the ${key} help topic`));

// Responsive and operating-system accessibility modes are part of the acceptance contract.
assert(stylesheet.includes("body.qadam-dashboard-page"), "Quantum Edge CSS is not dashboard scoped");
assert(stylesheet.includes("@media (max-width: 720px)"), "Quantum Edge mobile layout is missing");
assert(stylesheet.includes("@media (max-width: 640px)"), "Quantum Edge title breakpoint does not match Pattern Recognition");
assert(stylesheet.includes("@media (max-width: 520px)"), "Quantum Edge compact mobile layout is missing");
assert(stylesheet.includes("@media (prefers-reduced-motion: reduce)"), "Quantum Edge reduced-motion support is missing");
assert(stylesheet.includes("@media (forced-colors: active)"), "Quantum Edge forced-colors support is missing");
assert(stylesheet.includes("@media print"), "Quantum Edge print expansion support is missing");
assert(stylesheet.includes(":focus-visible"), "Quantum Edge visible keyboard focus is missing");
assert(stylesheet.includes(".qep-help-trigger > span") && stylesheet.includes("background: var(--qep-grey-soft)"), "Quantum Edge help icon is not neutral grey");
assert(stylesheet.includes("font: 500 2.5rem/1.05"), "Quantum Edge desktop title does not match Pattern Recognition");
assert(stylesheet.includes("font-size: 1rem") && stylesheet.includes("line-height: 1.65"), "Quantum Edge subtitle does not match Pattern Recognition");
assert(stylesheet.includes(".qep-header-layout") && stylesheet.includes("grid-template-columns: minmax(0, 1fr) minmax(20rem, 26rem)"), "Quantum Edge conclusion is not aligned beside the page title");
assert(script.includes('<p class="qep-current-conclusion') && script.includes('<div class="qep-header-layout">'), "Quantum Edge current conclusion is missing from the header layout");
assert(!script.includes('class="qep-boundary"'), "Quantum Edge still renders the bottom authority paragraph");
assert(!script.includes("DEFAULT_BOUNDARY"), "Quantum Edge still carries the removed bottom authority fallback");
assert(script.includes('<footer class="qep-freshness">'), "Quantum Edge freshness footer is missing");

// The public truth is deliberately conservative: engineering works, market proof does not yet exist.
assert(status.answer?.proof_state === "unproven", "Quantum Edge overstates its proof state");
assert(status.answer?.scientific_verdict === "not_measurable", "Quantum Edge overstates its scientific verdict");
assert(status.answer?.engineering_checks?.pass_count === 11 && status.answer?.engineering_checks?.check_count === 11, "Quantum Edge engineering score is not 11/11");
assert(status.answer?.engineering_checks?.score_label === "11/11", "Quantum Edge engineering score label changed");
assert(status.answer?.market_proof_prerequisites?.pass_count === 1 && status.answer?.market_proof_prerequisites?.check_count === 6, "Quantum Edge market-proof score is not 1/6");
assert(status.answer?.market_proof_prerequisites?.score_label === "1/6", "Quantum Edge market-proof score label changed");
const marketChecks = status.answer.market_proof_prerequisites.checks;
const providerAccess = marketChecks.find((check) => check.key === "ibm_provider_recovered");
const hardwareRun = marketChecks.find((check) => check.key === "ibm_hardware_result");
assert(providerAccess?.passed === true && providerAccess?.status === "passed", "Quantum Edge hides current provider access");
assert(/provider readiness only/i.test(providerAccess?.explanation || ""), "Quantum Edge does not distinguish provider access from execution");
assert(/no hardware job was authorized or run/i.test(providerAccess?.explanation || ""), "Quantum Edge provider copy implies hardware execution");
assert(hardwareRun?.passed === false && hardwareRun?.status === "not_run", "Quantum Edge invents a hardware experiment");
assert(status.evidence?.hardware_authenticity?.current_hardware_checkpoint?.authorized === false, "Quantum Edge invents hardware authorization");
assert(status.evidence?.hardware_authenticity?.engineering_fixture?.provider_call_count === 0, "Quantum Edge performed a provider call");
assert(status.evidence?.hardware_authenticity?.engineering_fixture?.hardware_job_submitted === false, "Quantum Edge submitted a hardware job");
assert(status.evidence?.hardware_authenticity?.engineering_fixture?.hardware_experiment_completed === false, "Quantum Edge claims a completed hardware experiment");
const evidenceTruth = status.evidence?.operational_evidence?.evidence_truth || {};
assert(evidenceTruth.eligible_window_count === 0, "Quantum Edge invents eligible untouched evidence");
assert(evidenceTruth.provider_row_count === 0, "Quantum Edge invents provider-history rows");
assert(evidenceTruth.completed_partition_count === 0, "Quantum Edge invents completed provider partitions");
assert(evidenceTruth.provider_history_certified_complete === false, "Quantum Edge overstates provider-history completeness");
assert(evidenceTruth.leakage_violation_count === 0, "Quantum Edge evidence violates the no-lookahead gate");

// No downstream trading state or operational authority may be created by this explanation page.
const consequence = status.consequence || {};
assert((consequence.hybrid_lifecycle || []).length === 8, "Quantum Edge technical record must retain the eight-step hybrid research lifecycle");
assert((consequence.guarded_route?.route_contract?.stages || []).length === 7, "Quantum Edge technical record must retain the seven-stage governed downstream route");
assert(consequence.strategy_influence?.validated_strategy_count === 0, "Quantum Edge created strategy influence");
assert(consequence.paper_outcome_lineage?.attributed_paper_decision_count === 0, "Quantum Edge created paper-decision attribution");
assert(consequence.paper_outcome_lineage?.mature_postmortem_count === 0, "Quantum Edge created a mature paper postmortem");
assert(consequence.paper_outcome_lineage?.paper_order_count === 0, "Quantum Edge created a paper order");
["validated_edge_count", "strategy_count", "risk_review_count", "paperops_review_handoff_count", "paper_order_count", "broker_write_count"].forEach((key) => {
    assert(consequence.guarded_route?.[key] === 0, `Quantum Edge created downstream ${key}`);
});
assert(consequence.guarded_route?.route_contract?.wave_g_calls_broker === false, "Quantum Edge Wave G route calls a broker");
assert(consequence.guarded_route?.route_contract?.wave_g_submits_orders === false, "Quantum Edge Wave G route submits orders");
assert(Object.keys(status.authority || {}).length >= 20, "Quantum Edge authority contract is incomplete");
assert(Object.values(status.authority || {}).every((value) => value === false), "Quantum Edge has operational authority");
assert(/cannot run research, call a provider, submit hardware/i.test(status.boundary || ""), "Quantum Edge boundary omits research/provider authority");
assert(/create a PaperOps handoff or order, write to a broker/i.test(status.boundary || ""), "Quantum Edge boundary omits order/broker authority");
assert(!/paper-api\.alpaca|\/v2\/orders|submitOrder|createOrder|placeOrder|submitHardware|createHardwareJob|method\s*:\s*["'](?:POST|PUT|PATCH|DELETE)["']/i.test(script), "Quantum Edge renderer contains an operational command path");

process.stdout.write(`${JSON.stringify({
    status: "quantum_edge_three_layer_dashboard_acceptance_passed",
    content_hash: status.content_hash,
    section_order: status.presentation.section_order,
    default_open: "none",
    engineering_checks: status.answer.engineering_checks.score_label,
    market_proof_prerequisites: status.answer.market_proof_prerequisites.score_label,
    provider_access: providerAccess.status,
    hardware_execution: hardwareRun.status,
    strategy_influence_count: consequence.strategy_influence.validated_strategy_count,
    paper_order_count: consequence.guarded_route.paper_order_count,
    authority: "read_only"
}, null, 2)}\n`);
