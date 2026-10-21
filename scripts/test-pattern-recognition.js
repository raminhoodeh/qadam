"use strict";

const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const test = require("node:test");
const vm = require("node:vm");

const script = fs.readFileSync(path.join(__dirname, "..", "quantum-edge-wave-f.js"), "utf8");
const end = "    loadProjection();\n})();";
assert.ok(script.includes(end), "The test must disable the real network loader.");
const context = vm.createContext({
    console,
    Date,
    Intl,
    URLSearchParams,
    document: { addEventListener() {}, body: {} },
    window: { addEventListener() {}, sessionStorage: { getItem() { return null; } } },
    MutationObserver: class { observe() {} }
});
vm.runInContext(script.replace(end, `
    globalThis.patternTest = { buildCurrentPatternRecognition, renderPatternRecognition, renderPatternCard, readPatternState };
})();`), context);
const api = context.patternTest;
const now = Date.parse("2026-10-21T05:00:00Z");

function relationship(overrides = {}) {
    return {
        pattern_id: "silver", title: "Silver and liquidity", raw_pattern_score: 0.60724,
        plain_english_question: "Does liquidity precede silver repricing?",
        plain_english_analysis: "Liquidity is being compared with silver returns.",
        stage: "under_historical_test", stage_label: "Under historical test",
        historical_evidence: { validated_edge: false },
        fresh_source_count: 1, contributing_source_count: 5,
        observed_at: "2026-10-21T04:50:00Z", freshness: { is_current: true, stale_after_seconds: 1800 },
        target_instruments: ["SLV", "SIL"], source_chain: ["fred", "ecb"],
        instrument_results: [{ instrument: "SLV", raw_pattern_score: 0.60724, missing_context: [] }],
        ...overrides
    };
}

function canonical(rows = [relationship()], overrides = {}) {
    return {
        artifact_type: "qadam_pattern_discovery_dashboard",
        generated_at: "2026-10-21T04:58:00Z", relationships: rows,
        universe: { source_count: 41, instrument_count: 19, mapped_relationship_count: 779 },
        ...overrides
    };
}

test("rankings reflect current canonical scores, not legacy snapshot values", () => {
    const view = api.buildCurrentPatternRecognition(canonical([
        relationship(), relationship({ pattern_id: "oil", title: "Oil", raw_pattern_score: 0.68932 })
    ]), now);
    assert.equal(view.candidates[0].candidate_id, "oil");
    assert.equal(view.candidates[0].research_score.display, "0.689");
    assert.equal(view.candidates[1].research_score.display, "0.607");
    const revised = api.buildCurrentPatternRecognition(canonical([
        relationship(), relationship({ pattern_id: "oil", title: "Oil", raw_pattern_score: 0.2 })
    ]), now);
    assert.equal(revised.candidates[0].candidate_id, "silver");
    assert.equal(api.readPatternState().sort, "highest_score");
});

test("engineering fixtures and negative controls are not market discoveries", () => {
    const view = api.buildCurrentPatternRecognition(canonical([
        relationship(), relationship({ contract_fixture_only: true }), relationship({ negative_control: true })
    ]), now);
    assert.equal(view.candidate_count, 1);
    assert.equal(view.filters[0].count, 1);
});

test("missing canonical evidence never falls back to deployed recognition data", () => {
    const view = api.buildCurrentPatternRecognition({ candidates: [{ research_score: { value: 0.9 } }] }, now);
    assert.equal(view.available, false);
    assert.equal(view.candidates.length, 0);
    assert.match(api.renderPatternRecognition(view), /Older recognition snapshots and engineering controls are not substituted/);
});

test("fresh sources at scoring and present observation age remain separate", () => {
    const view = api.buildCurrentPatternRecognition(canonical([relationship({
        observed_at: "2026-10-20T20:00:00Z", freshness: { is_current: true }
    })]), now);
    const row = view.candidates[0];
    assert.equal(row.source_freshness_label, "1/5 sources fresh at scoring");
    assert.equal(row.observation_state, "Observation stale");
    assert.equal(row.source_freshness_limited, true);
});

test("missing and future times cannot become current observations", () => {
    for (const observed_at of [null, "invalid", "2026-10-21T06:00:00Z"]) {
        const row = api.buildCurrentPatternRecognition(canonical([relationship({ observed_at })]), now).candidates[0];
        assert.equal(row.observation_state, "Observation time unverified");
    }
});

test("missing source counts are unknown, not fabricated zero coverage", () => {
    const view = api.buildCurrentPatternRecognition(canonical([relationship({ fresh_source_count: null })]), now);
    assert.equal(view.candidates[0].source_freshness_label, "Source freshness not reported");
});

test("a new snapshot timestamp does not make old observations current", () => {
    const view = api.buildCurrentPatternRecognition(canonical([relationship({
        observed_at: "2026-10-20T00:00:00Z"
    })]), now);
    assert.equal(view.snapshot_current, true);
    assert.equal(view.candidates[0].observation_state, "Observation stale");
    const old = api.buildCurrentPatternRecognition(canonical(undefined, { generated_at: "2026-10-20T00:00:00Z" }), now);
    assert.equal(old.snapshot_current, false);
    assert.match(api.renderPatternRecognition(old), /Snapshot stale or unavailable/);
});

test("validation requires both a validated stage and historical evidence", () => {
    for (const overrides of [{ stage: "validated_edge" }, { historical_evidence: { validated_edge: true } }]) {
        const view = api.buildCurrentPatternRecognition(canonical([relationship(overrides)]), now);
        assert.equal(view.validated_count, 0);
        assert.equal(view.candidates[0].validation_contribution_label, "Unproven hypothesis");
    }
    const view = api.buildCurrentPatternRecognition(canonical([relationship({
        stage: "validated_edge", historical_evidence: { validated_edge: true }
    })]), now);
    assert.equal(view.validated_count, 1);
    assert.equal(view.candidates[0].validated_edge, true);
});

test("missing, malformed and out-of-range scores are not shown as real rankings", () => {
    for (const raw_pattern_score of [null, undefined, "0.9", NaN, Infinity, -1, 2]) {
        const row = api.buildCurrentPatternRecognition(canonical([relationship({ raw_pattern_score })]), now).candidates[0];
        assert.equal(row.research_score.value, null);
        assert.equal(row.research_score.display, "Not scored");
    }
});

test("public cards explain ranking, instruments, validation and missing empirical counts", () => {
    const view = api.buildCurrentPatternRecognition(canonical(), now);
    const html = api.renderPatternRecognition(view);
    for (const phrase of ["Research score", "Validated edges", "Unproven hypothesis", "1/5 sources fresh at scoring",
        "not a win probability", "SLV, SIL", "Independent occurrence count not established", "Instrument-level research scores"]) {
        assert.ok(html.includes(phrase), `Missing ${phrase}`);
    }
    assert.ok(!html.includes("Confidence score"));
    assert.equal(view.candidates[0].research_score.is_probability, false);
    assert.equal(view.candidates[0].quantum_involved, false);
});

test("untrusted pattern text is escaped", () => {
    const view = api.buildCurrentPatternRecognition(canonical([relationship({ title: "<script>bad()</script>" })]), now);
    const html = api.renderPatternRecognition(view);
    assert.ok(!html.includes("<script>bad()"));
    assert.match(html, /&lt;script&gt;/);
});

test("canonical panel replacement is keyed to changing evidence, not the legacy content hash", () => {
    assert.match(script, /buildCurrentPatternRecognition\(canonical\)/);
    assert.match(script, /"pattern-recognition", JSON\.stringify\(current\)/);
    assert.ok(!script.includes("renderPatternRecognition(projection.pattern_recognition"));
    assert.equal((script.match(/fetch\(/g) || []).length, 1);
});
