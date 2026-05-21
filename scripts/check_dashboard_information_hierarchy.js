#!/usr/bin/env node

const fs = require("node:fs");
const path = require("node:path");

const repoRoot = path.resolve(__dirname, "..");
const htmlPath = path.join(repoRoot, "landing-page-repo", "dashboard", "index.html");
const cssPath = path.join(repoRoot, "landing-page-repo", "auth.css");
const rendererPath = path.join(repoRoot, "landing-page-repo", "dashboard.js");

const html = fs.readFileSync(htmlPath, "utf8");
const css = fs.readFileSync(cssPath, "utf8");
const renderer = fs.readFileSync(rendererPath, "utf8");

function assert(condition, message) {
    if (!condition) throw new Error(message);
}

function indexOf(needle, label = needle) {
    const index = html.indexOf(needle);
    assert(index >= 0, `dashboard HTML missing ${label}`);
    return index;
}

const hero = indexOf("dashboard-hero");
const review = indexOf("operating-review-panel");
const map = indexOf("system-map-panel");
const detailIntro = indexOf("dashboard-section-intro");
const detailFlow = indexOf("dashboard-detail-flow");

assert(hero < review, "mission control must appear after the hero");
assert(review < map, "mission control must appear before the system map");
assert(map < detailIntro, "section intro must appear after the system map");
assert(detailIntro < detailFlow, "detail panels must appear after the section intro");

[
    "data-operating-summary",
    "Mission control",
    "What Qadam is watching, thinking, planning, holding, and forbidden from doing",
    "data-mission-primary",
    "data-mission-sources",
    "data-mission-trades",
    "Paper account",
    "Source quality",
    "Safety state",
    "Review sequence: sources, cognition, trade state, money, safety, governance, runtime"
].forEach((needle) => assert(html.includes(needle), `dashboard hierarchy HTML missing ${needle}`));

[
    ".operating-review-panel",
    ".mission-control-grid",
    ".mission-primary",
    ".mission-card",
    ".priority-grid",
    ".priority-card",
    ".dashboard-detail-flow",
    "grid-template-columns: repeat(12, minmax(0, 1fr))",
    "order: 9"
].forEach((needle) => assert(css.includes(needle), `dashboard hierarchy CSS missing ${needle}`));

const missionFunction = renderer.indexOf("function renderMissionControl");
const missionCall = renderer.lastIndexOf("renderMissionControl(status, source)");
const renderFunction = renderer.indexOf("function renderOperatingSummary");
const renderCall = renderer.lastIndexOf("renderOperatingSummary(status, source)");
const flowCall = renderer.lastIndexOf("renderFlowMap(status)");
assert(missionFunction >= 0, "renderer missing renderMissionControl");
assert(missionCall >= 0, "renderer does not call renderMissionControl");
assert(renderFunction >= 0, "renderer missing renderOperatingSummary");
assert(renderCall >= 0, "renderer does not call renderOperatingSummary");
assert(missionCall < renderCall, "mission control must render before operating summary cards");
assert(renderCall < flowCall, "operating summary must render before the system map");

[
    "Candidate is not order",
    "logged-in/configured",
    "Source quality",
    "Safety state",
    "Live capital disabled",
    "Static fallback",
    "Live bridge"
].forEach((needle) => assert(renderer.includes(needle), `operating summary renderer missing ${needle}`));

console.log("dashboard_information_hierarchy=ok");
