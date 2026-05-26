#!/usr/bin/env node

const fs = require("node:fs");
const path = require("node:path");

const repoRoot = path.resolve(__dirname, "..");
const htmlPath = path.join(repoRoot, "landing-page-repo", "dashboard", "index.html");
const contractPath = path.join(repoRoot, "docs", "qadam-dashboard-overhaul-dx-1-ia-contract.json");
const planPath = path.join(repoRoot, "docs", "qadam-dashboard-overhaul-master-implementation-plan.md");

const html = fs.readFileSync(htmlPath, "utf8");
const contract = JSON.parse(fs.readFileSync(contractPath, "utf8"));
const plan = fs.readFileSync(planPath, "utf8");

function assert(condition, message) {
    if (!condition) throw new Error(message);
}

function ids(values) {
    return values.map((value) => value.id);
}

function unique(values) {
    return Array.from(new Set(values));
}

function parseCockpitSections(source) {
    const sections = [];
    const pattern = /<(section|article)\b([^>]*)\bdata-cockpit-section="([^"]+)"([^>]*)>/g;
    let match;

    while ((match = pattern.exec(source)) !== null) {
        const attributes = `${match[2]} ${match[4]}`;
        const idMatch = attributes.match(/\bid="([^"]+)"/);
        assert(idMatch, `dashboard cockpit section has no id: ${match[0]}`);
        sections.push({
            id: idMatch[1],
            label: match[3]
        });
    }

    return sections;
}

const expectedViews = [
    "overview",
    "trades",
    "sources",
    "reasoning",
    "performance",
    "operations",
    "governance"
];

assert(contract.contract_id === "qadam_dashboard_overhaul_dx_1_ia_contract", "wrong contract id");
assert(contract.route === "/dashboard/", "contract route must be /dashboard/");
assert(contract.status === "active", "IA contract must be active");
assert(contract.url_behavior?.first_release === "hash_tabs_within_dashboard", "first release must use dashboard hash tabs");
assert(contract.url_behavior?.default_view === "overview", "default view must be overview");
assert(contract.url_behavior?.legacy_anchor_redirects === true, "legacy anchor redirects must be planned");
assert(
    String(contract.authority_boundary || "").includes("Read-only presentation contract only"),
    "authority boundary must explicitly remain read-only"
);

const viewIds = ids(contract.primary_views || []);
assert(JSON.stringify(viewIds) === JSON.stringify(expectedViews), `primary view order mismatch: ${viewIds.join(",")}`);
assert(unique(viewIds).length === expectedViews.length, "primary view ids must be unique");
contract.primary_views.forEach((view, index) => {
    assert(view.order === index + 1, `view order mismatch for ${view.id}`);
    assert(typeof view.label === "string" && view.label.length > 2, `view ${view.id} missing label`);
    assert(
        typeof view.short_description === "string" && view.short_description.length > 20,
        `view ${view.id} missing short description`
    );
    assert(
        typeof view.entry_question === "string" && view.entry_question.endsWith("?"),
        `view ${view.id} missing entry question`
    );
    assert(view.url_hash === `#${view.id}`, `view ${view.id} hash mismatch`);
});
assert(contract.primary_views[0].default === true, "Overview must be the only default view");
assert(contract.primary_views.slice(1).every((view) => view.default === false), "Only Overview may be default");

const currentSections = parseCockpitSections(html);
const currentIds = currentSections.map((section) => section.id);
const destinationIds = (contract.section_destinations || []).map((section) => section.section_id);
const missingDestinations = currentIds.filter((id) => !destinationIds.includes(id));
const staleDestinations = destinationIds.filter((id) => !currentIds.includes(id));
assert(missingDestinations.length === 0, `sections missing IA destinations: ${missingDestinations.join(",")}`);
assert(staleDestinations.length === 0, `IA destinations point at missing dashboard sections: ${staleDestinations.join(",")}`);
assert(unique(destinationIds).length === destinationIds.length, "section destinations must be unique");

(contract.section_destinations || []).forEach((section) => {
    assert(expectedViews.includes(section.destination_view), `${section.section_id} maps to invalid view`);
    assert(typeof section.destination_role === "string" && section.destination_role.length > 3, `${section.section_id} missing role`);
    assert(typeof section.notes === "string" && section.notes.length > 20, `${section.section_id} missing notes`);
});

const requiredMappings = {
    "mission-control": "overview",
    "trade-layer": "trades",
    watching: "sources",
    cognition: "reasoning",
    money: "performance",
    "system-map": "operations",
    "process-console": "operations",
    governance: "governance",
    communications: "governance"
};

Object.entries(requiredMappings).forEach(([sectionId, expectedView]) => {
    const destination = contract.section_destinations.find((section) => section.section_id === sectionId);
    assert(destination, `required section destination missing: ${sectionId}`);
    assert(
        destination.destination_view === expectedView,
        `${sectionId} must map to ${expectedView}, got ${destination.destination_view}`
    );
});

const placements = contract.system_map_placements || [];
const overviewMap = placements.find((placement) => placement.view === "overview" && placement.scope === "compact");
const operationsMap = placements.find((placement) => placement.view === "operations" && placement.scope === "expanded");
assert(overviewMap, "Overview compact system map placement is missing");
assert(operationsMap, "Operations expanded system map placement is missing");
assert(overviewMap.source_model === "system_connectivity_model", "Overview mini-map must use shared connectivity model");
assert(operationsMap.source_model === "system_connectivity_model", "Operations full map must use shared connectivity model");

const demotedIds = (contract.demoted_from_first_level || []).map((section) => section.section_id);
assert(demotedIds.includes("system-map"), "full system map must be demoted from first-level visibility");
assert(demotedIds.includes("process-console"), "process console must be demoted from first-level visibility");
assert(demotedIds.every((id) => currentIds.includes(id)), "demoted section list includes unknown section");

const compatibilityTargets = (contract.legacy_anchor_compatibility || []).map((entry) => entry.target_section);
const missingCompatibility = currentIds.filter((id) => !compatibilityTargets.includes(id));
assert(missingCompatibility.length === 0, `legacy anchor compatibility missing: ${missingCompatibility.join(",")}`);
(contract.legacy_anchor_compatibility || []).forEach((entry) => {
    assert(expectedViews.includes(entry.view), `${entry.target_section} has invalid compatibility view`);
    assert(entry.legacy_hash === `#${entry.target_section}`, `${entry.target_section} legacy hash mismatch`);
});

const tourViews = (contract.first_time_tour || []).map((step) => step.view);
assert(JSON.stringify(tourViews) === JSON.stringify(expectedViews), "first-time tour must follow primary view order");
assert((contract.first_time_tour || []).every((step, index) => step.step === index + 1), "first-time tour steps must be ordered");

[
    "DX-1 - Information Architecture Contract",
    "Define the seven primary views",
    "Map every existing section to a new destination",
    "Define the two system map placements"
].forEach((needle) => {
    assert(plan.includes(needle), `master plan missing DX-1 marker: ${needle}`);
});

console.log("dashboard_overhaul_ia_contract=ok");
console.log(`dashboard_primary_view_count=${contract.primary_views.length}`);
console.log(`dashboard_current_section_count=${currentSections.length}`);
console.log("dashboard_all_sections_mapped=True");
console.log(`dashboard_orphan_panel_count=${missingDestinations.length}`);
console.log(`dashboard_system_map_compact_destination=${overviewMap.view}`);
console.log(`dashboard_system_map_expanded_destination=${operationsMap.view}`);
console.log("dashboard_first_time_tour_rewritable=True");
console.log("dashboard_authority_unchanged=True");
