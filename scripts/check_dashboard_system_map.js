#!/usr/bin/env node

const fs = require("node:fs");
const path = require("node:path");

const {
    assert,
    assertIncludes,
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
        "system-flow-diagram",
        "flow-return-loop",
        "Observation",
        "COO Memory",
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
    [
        "Observation",
        "COO Memory",
        "Research",
        "Quant + Risk",
        "Paper Trial",
        "Members",
        "Event Log",
        "Secure Live Bridge",
        "Research Analyst",
        "Strategy Lead",
        "Signal Integrity Gate",
        "Risk Agent",
        "Execution Policy",
        "Staged Order Contract",
        "Trade Layer",
        "Paper Account Mirror",
        "Postmortem Loop",
        "Telegram Bot",
        "Fund Manager Forum",
        "Input",
        "Output",
        "Closed-loop rule",
        "lessons return to memory"
    ].forEach((needle) => assertIncludes(rendered, "[data-flow-map]", needle));

    console.log("dashboard_system_map=ok");
    console.log(`Rendered snapshot: ${statusPath}`);
}

if (require.main === module) {
    main().catch((error) => {
        console.error(error);
        process.exit(1);
    });
}
