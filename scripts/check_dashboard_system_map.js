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
	        "data-overview-control-plane",
	        "Control Plane",
        "Loading operating map and oversight"
    ].forEach((needle) => assert(html.includes(needle), `static Control Plane shell missing ${needle}`));

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
        ".flow-return-loop",
        ".overview-operating-flow-head",
        ".overview-operating-node-grid"
    ].forEach((needle) => assert(css.includes(needle), `system map CSS missing ${needle}`));

    assert(!css.includes("grid-template-columns: repeat(11, minmax(176px, 1fr))"), "system map regressed to horizontal strip grid");
    assert(!css.includes("grid-auto-flow: column"), "system map regressed to forced column flow");
    assert(css.includes(".overview-operating-flow {\n    display: grid;\n    grid-template-columns: 1fr;"), "Qadam operating team must not inherit multi-column system-flow layout");
    assert(css.includes(".overview-operating-node-grid {\n    align-items: start;\n    grid-template-columns: repeat(2, minmax(0, 1fr));"), "Qadam operating team nodes must render as broad desktop cards");
    assert(css.includes(".overview-operating-flow .overview-mini-connector"), "Qadam operating team should hide connector spans that squeeze node cards");

	    const rendered = await renderWithStatus(status);
	    const controlPlaneHtml = renderedHtmlFor(rendered, "[data-overview-control-plane]");
	    const operationsHtml = renderedHtmlFor(rendered, "[data-flow-map]");
	    assert((controlPlaneHtml.match(/class="system-flow-diagram/g) || []).length === 1, "Control Plane should render exactly one canonical system-flow-diagram");
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
	    ].forEach((needle) => assertIncludes(rendered, "[data-overview-control-plane]", needle));
	    [
	        "Operations diagnostics and event trail",
	        "System map diagnostics",
	        "Edge state",
	        "Open the Overview tab for the single canonical node-by-node system map",
		        "OK - live capital off"
	    ].forEach((needle) => assertIncludes(rendered, "[data-flow-map]", needle));
	    ["Chief Operating Officer", "Research Analyst", "Strategy Lead", "Head of Quant", "Safety Policy", "PaperOps"].forEach((needle) => {
	        assertIncludes(rendered, "[data-overview-control-plane]", needle);
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
