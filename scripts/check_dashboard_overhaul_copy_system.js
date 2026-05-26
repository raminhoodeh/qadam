#!/usr/bin/env node

const fs = require("node:fs");
const path = require("node:path");

const repoRoot = path.resolve(__dirname, "..");
const copyPath = path.join(repoRoot, "docs", "qadam-dashboard-overhaul-dx-2-copy-system.json");
const iaPath = path.join(repoRoot, "docs", "qadam-dashboard-overhaul-dx-1-ia-contract.json");
const planPath = path.join(repoRoot, "docs", "qadam-dashboard-overhaul-master-implementation-plan.md");
const htmlPath = path.join(repoRoot, "landing-page-repo", "dashboard", "index.html");

const copySystem = JSON.parse(fs.readFileSync(copyPath, "utf8"));
const iaContract = JSON.parse(fs.readFileSync(iaPath, "utf8"));
const plan = fs.readFileSync(planPath, "utf8");
const html = fs.readFileSync(htmlPath, "utf8");

function assert(condition, message) {
    if (!condition) throw new Error(message);
}

function unique(values) {
    return Array.from(new Set(values));
}

function includesAll(values, required, label) {
    const missing = required.filter((value) => !values.includes(value));
    assert(missing.length === 0, `${label} missing ${missing.join(",")}`);
}

function hasInternalTerm(text, terms) {
    const normalized = String(text || "").toLowerCase();
    return terms.some((term) => normalized.includes(term.toLowerCase()));
}

const expectedViews = (iaContract.primary_views || []).map((view) => view.id);
const copyViews = copySystem.primary_view_copy_policy?.view_order || [];

assert(copySystem.contract_id === "qadam_dashboard_overhaul_dx_2_copy_system", "wrong copy-system contract id");
assert(copySystem.route === "/dashboard/", "copy system route must be /dashboard/");
assert(copySystem.status === "active", "copy system must be active");
assert(JSON.stringify(copyViews) === JSON.stringify(expectedViews), "copy-system view order must match DX-1 IA");
assert(
    String(copySystem.authority_boundary || "").includes("Read-only copy and terminology contract only"),
    "copy-system authority boundary must remain read-only"
);

const viewRuleIds = Object.keys(copySystem.view_rules || {});
assert(JSON.stringify(viewRuleIds) === JSON.stringify(expectedViews), "copy-system view rules must match DX-1 IA");

const overviewRule = copySystem.view_rules.overview || {};
const operationsRule = copySystem.view_rules.operations || {};
const overviewDisallowed = overviewRule.disallowed_primary_terms || [];
const requiredOverviewBans = [
    "D0",
    "D1",
    "D5",
    "D7",
    "D9",
    "Q4",
    "Q5",
    "Q5E",
    "Q6",
    "Q7",
    "Phase 4",
    "Phase 5",
    "Phase 6",
    "Phase 7",
    "static snapshot",
    "secure bridge",
    "shadow toggles"
];
includesAll(overviewDisallowed, requiredOverviewBans, "Overview primary-copy bans");
includesAll(
    overviewRule.required_plain_topics || [],
    ["paper/demo only", "live capital disabled", "source health", "trade lifecycle", "safety state", "action needed"],
    "Overview required plain topics"
);
assert(operationsRule.diagnostic_codes_allowed === true, "Operations must allow labeled diagnostics");
assert(operationsRule.diagnostic_explanation_required === true, "Operations diagnostics must require explanation");

const terms = copySystem.terminology || [];
const termNames = terms.map((entry) => entry.term);
assert(unique(termNames).length === termNames.length, "copy-system terminology terms must be unique");
includesAll(
    termNames,
    [
        "D0",
        "D1",
        "D5",
        "D7",
        "D9",
        "Q4",
        "Q5",
        "Q5E",
        "Q6",
        "Q7",
        "Phase 4",
        "Phase 5",
        "Phase 6",
        "Phase 7",
        "static snapshot",
        "secure bridge",
        "shadow toggles",
        "live capital",
        "broker write",
        "candidate",
        "staged paper order",
        "submitted paper order",
        "paper order"
    ],
    "copy-system terminology"
);

terms.forEach((entry) => {
    assert(typeof entry.plain_label === "string" && entry.plain_label.length >= 4, `${entry.term} missing plain_label`);
    assert(typeof entry.primary_copy === "string" && entry.primary_copy.length >= 4, `${entry.term} missing primary_copy`);
    assert(
        typeof entry.user_explanation === "string" && entry.user_explanation.length >= 24,
        `${entry.term} missing user_explanation`
    );
    assert(typeof entry.category === "string" && entry.category.length >= 4, `${entry.term} missing category`);
    if (entry.category === "internal_code") {
        assert(entry.primary_allowed === false, `${entry.term} must not be allowed in primary copy`);
        assert(entry.operations_diagnostic_allowed === true, `${entry.term} must be allowed only as Operations diagnostic`);
    }
    if (entry.category === "phase_label") {
        assert(entry.primary_allowed === false, `${entry.term} phase label must not be primary copy`);
        assert(entry.secondary_diagnostic_allowed === true, `${entry.term} phase label must be secondary diagnostic`);
        assert(!entry.primary_copy.startsWith("Phase "), `${entry.term} replacement must not be phase-first`);
    }
    if (entry.category === "safety_term") {
        assert(entry.must_remain_explicit === true, `${entry.term} safety term must remain explicit`);
        assert(entry.primary_allowed === true, `${entry.term} safety term must be allowed in primary copy`);
    }
});

const emptyStates = copySystem.empty_states || {};
const requiredEmptyStates = [
    "normal_no_setup",
    "normal_no_trade",
    "normal_no_position",
    "normal_no_postmortem",
    "blocked",
    "stale",
    "degraded",
    "missing"
];
includesAll(Object.keys(emptyStates), requiredEmptyStates, "empty states");
Object.entries(emptyStates).forEach(([key, value]) => {
    assert(typeof value.title === "string" && value.title.length >= 8, `${key} empty state missing title`);
    assert(typeof value.body === "string" && value.body.length >= 40, `${key} empty state missing body`);
    assert(typeof value.tone === "string" && value.tone.length >= 5, `${key} empty state missing tone`);
    assert(!hasInternalTerm(value.title, requiredOverviewBans), `${key} empty state title uses internal term`);
    assert(!hasInternalTerm(value.body, ["D0", "D1", "D5", "D7", "D9", "Q4", "Q5", "Q5E", "Q6", "Q7"]), `${key} empty state body uses internal code`);
});
assert(
    emptyStates.blocked.body.includes("read-only") && emptyStates.blocked.body.includes("cannot bypass"),
    "blocked empty state must preserve safety boundary"
);
assert(
    emptyStates.missing.body.includes("does not create trading authority"),
    "missing empty state must preserve authority boundary"
);

includesAll(
    copySystem.required_safety_phrases || [],
    ["read-only", "paper/demo only", "live capital disabled", "broker writes blocked", "candidate is not an order"],
    "required safety phrases"
);
const safetyText = JSON.stringify(copySystem).toLowerCase();
[
    "read-only",
    "paper/demo only",
    "live capital disabled",
    "broker writes blocked",
    "candidate is not an order"
].forEach((phrase) => {
    assert(safetyText.includes(phrase), `copy system missing explicit safety phrase: ${phrase}`);
});

(copySystem.replacement_rules || []).forEach((rule) => {
    assert(typeof rule.rule === "string" && rule.rule.length > 4, "replacement rule missing id");
    assert(typeof rule.from === "string" && rule.from.length > 4, `${rule.rule} missing from`);
    assert(typeof rule.to === "string" && rule.to.length > 20, `${rule.rule} missing to`);
});
includesAll(
    (copySystem.replacement_rules || []).map((rule) => rule.rule),
    ["internal_code_primary_copy", "phase_first_copy", "runtime_jargon", "safety_terms"],
    "replacement rules"
);

if (html.includes('data-dashboard-view="overview"')) {
    const overviewMatch = html.match(/<[^>]+data-dashboard-view="overview"[^>]*>([\s\S]*?)<\/(?:section|div)>/);
    const overviewHtml = overviewMatch ? overviewMatch[1] : "";
    requiredOverviewBans.forEach((term) => {
        assert(!overviewHtml.includes(term), `Overview primary HTML contains disallowed term: ${term}`);
    });
}

[
    "DX-2 - Copy And Terminology System",
    "Define user-facing labels for internal terms",
    "Keep internal codes visible only in Operations diagnostics",
    "Define empty-state language"
].forEach((needle) => {
    assert(plan.includes(needle), `master plan missing DX-2 marker: ${needle}`);
});

console.log("dashboard_overhaul_copy_system=ok");
console.log(`dashboard_copy_primary_view_count=${copyViews.length}`);
console.log(`dashboard_copy_term_count=${terms.length}`);
console.log(`dashboard_copy_empty_state_count=${Object.keys(emptyStates).length}`);
console.log("dashboard_internal_codes_diagnostic_only=True");
console.log("dashboard_phase_labels_secondary_only=True");
console.log("dashboard_overview_primary_copy_bans_internal_codes=True");
console.log("dashboard_safety_boundaries_explicit=True");
console.log("dashboard_authority_unchanged=True");
