#!/usr/bin/env node

const fs = require("node:fs");
const path = require("node:path");

const {
    assert,
    assertIncludes,
    html: renderedHtmlFor,
    renderWithStatus,
    status,
    statusPath
} = require("./check_dashboard_renderer.js");

const repoRoot = path.resolve(__dirname, "..");
const htmlPath = path.join(repoRoot, "landing-page-repo", "dashboard", "index.html");
const cssPath = path.join(repoRoot, "landing-page-repo", "auth.css");
const rendererPath = path.join(repoRoot, "landing-page-repo", "dashboard.js");

async function main() {
    const html = fs.readFileSync(htmlPath, "utf8");
    const css = fs.readFileSync(cssPath, "utf8");
    const renderer = fs.readFileSync(rendererPath, "utf8");

	    [
	        "system-flow-diagram",
	        "flow-lane",
	        "flow-connector",
        "lane-handoff",
        "flow-return-loop",
        "Closed-loop rule"
    ].forEach((needle) => assert(html.includes(needle), `static system map missing ${needle}`));

	    [
	        "function systemMapLane",
	        "function systemMapConnector",
	        "function renderOverviewCanonicalMap",
	        "function buildTeamHealthModel",
	        "system-flow-diagram",
        "flow-return-loop",
        "Observation",
        "System Memory",
        "Quant + Risk",
        "Paper Trial",
        "Members"
    ].forEach((needle) => assert(renderer.includes(needle), `system map renderer missing ${needle}`));

    [
        ".system-flow-diagram",
        ".flow-lane",
        ".flow-lane-header",
        ".flow-lane-track",
        ".flow-connector",
        ".lane-handoff",
        ".flow-return-loop"
    ].forEach((needle) => assert(css.includes(needle), `system map CSS missing ${needle}`));

    assert(!css.includes("grid-template-columns: repeat(11, minmax(176px, 1fr))"), "system map regressed to horizontal strip grid");
    assert(!css.includes("grid-auto-flow: column"), "system map regressed to forced column flow");

	    const rendered = await renderWithStatus(status);
	    const overviewMapHtml = renderedHtmlFor(rendered, "[data-overview-mini-map]");
	    const operationsHtml = renderedHtmlFor(rendered, "[data-flow-map]");
	    assert((overviewMapHtml.match(/class="system-flow-diagram/g) || []).length === 1, "Overview should render exactly one canonical system-flow-diagram");
	    assert(!operationsHtml.includes("operations-flow-diagram"), "Operations should not render a duplicate operations-flow-diagram");
	    [
        "Qadam operating team",
        "mission_control",
	        "How to read this node",
        "Intelligence Pipelines",
        "Chief Operating Officer",
	        "Research Analyst",
        "Strategy Lead",
        "Head of Quant",
        "Safety Policy",
        "Paper/Demo State",
        "Learning Review",
	        "Closed-loop rule",
		        "Boundary",
		        "Watch for",
		        "Next handoff"
	    ].forEach((needle) => assertIncludes(rendered, "[data-overview-mini-map]", needle));
	    [
	        "Operations diagnostics and event trail",
	        "System map diagnostics",
	        "Edge state",
	        "Open the Overview tab for the single canonical node-by-node system map",
		        "OK - live capital off"
	    ].forEach((needle) => assertIncludes(rendered, "[data-flow-map]", needle));
	    ["Chief Operating Officer", "Research Analyst", "Strategy Lead", "Head of Quant", "Safety Policy", "PaperOps"].forEach((needle) => {
	        assertIncludes(rendered, "[data-team-health-row]", needle);
	    });

    console.log("dashboard_system_map=ok");
    console.log(`Rendered snapshot: ${statusPath}`);
}

if (require.main === module) {
    main().catch((error) => {
        console.error(error);
        process.exit(1);
    });
}
