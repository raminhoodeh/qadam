#!/usr/bin/env node

const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");

const {
    assert,
    assertIncludes,
    html,
    renderWithStatus,
    status
} = require("./check_dashboard_renderer.js");

const repoRoot = path.resolve(__dirname, "..");
const rendererPath = path.join(repoRoot, "landing-page-repo", "dashboard.js");
const htmlPath = path.join(repoRoot, "landing-page-repo", "dashboard", "index.html");
const cssPath = path.join(repoRoot, "landing-page-repo", "auth.css");

const renderer = fs.readFileSync(rendererPath, "utf8");
const dashboardHtml = fs.readFileSync(htmlPath, "utf8");
const css = fs.readFileSync(cssPath, "utf8");

function buildModels(snapshot = status) {
    const document = {
        documentElement: { dataset: {} },
        querySelector() {
            return null;
        },
        querySelectorAll() {
            return [];
        }
    };
    const window = { document };
    const context = {
        Array,
        Boolean,
        Date,
        Error,
        Intl,
        Map,
        Math,
        Number,
        Object,
        Promise,
        Set,
        String,
        console,
        document,
        fetch: async () => ({ ok: true, json: async () => snapshot }),
        localStorage: {
            getItem() {
                return null;
            },
            setItem() {}
        },
        sessionStorage: {
            getItem() {
                return null;
            },
            setItem() {}
        },
        window
    };
    window.window = window;
    vm.createContext(context);
    vm.runInContext(renderer, context, { filename: rendererPath });
    return window.buildQadamDashboardViewModels(snapshot, { key: "static_snapshot" });
}

async function main() {
    assert(dashboardHtml.includes("data-overview-mission-brief"), "dashboard shell missing RS-8 Mission Brief slot");
    [
        ".overview-mission-brief",
        ".overview-mission-question",
        ".overview-mission-question > summary::after",
        ".overview-mission-question[open] > summary::after",
        ".overview-mission-nav",
        ".overview-mission-metrics"
    ].forEach((needle) => {
        assert(css.includes(needle), `RS-8 CSS missing ${needle}`);
    });
    assert(css.includes('content: "+"'), "RS-8 CSS missing visible plus affordance");
    assert(css.includes('content: "-"'), "RS-8 CSS missing visible minus affordance");

    const models = buildModels();
    const brief = models.overview_model.mission_brief;
    assert(brief.status === "ok" || brief.status === "fallback", "Mission Brief status missing");
    assert(brief.question_count === 7, "Mission Brief question_count must be seven");
    assert(brief.questions.length === 7, "Mission Brief must have seven questions");
    const keys = brief.questions.map((item) => item.key).sort();
    assert(
        JSON.stringify(keys) === JSON.stringify(["blocked", "considering", "forbidden", "portfolio", "thinking", "traded", "watching"]),
        "Mission Brief question keys mismatch"
    );
    [
        "What is Qadam watching?",
        "What is Qadam thinking about next?",
        "What is Qadam forbidden from doing?",
        "Which trades are candidates or blocked?",
        "What has Qadam traded on paper?",
        "What is the portfolio worth?",
        "Why is Qadam blocked or waiting?"
    ].forEach((question) => {
        assert(brief.questions.some((item) => item.question === question), `Mission Brief missing question: ${question}`);
    });
    brief.questions.forEach((question) => {
        assert(question.answer, `Mission Brief ${question.key} missing answer`);
        assert(question.summary, `Mission Brief ${question.key} missing summary`);
        assert(question.href?.startsWith("#"), `Mission Brief ${question.key} missing dashboard href`);
        assert(Array.isArray(question.metrics) && question.metrics.length >= 2, `Mission Brief ${question.key} missing metrics`);
    });
    assert(brief.navigation.length >= 9, "Mission Brief navigation must expose the main dashboard sections");
    [
        "Mission",
        "Map",
        "Sources",
        "Reasoning",
        "Trades",
        "Portfolio",
        "Safety",
        "Inbox",
        "Runtime"
    ].forEach((label) => {
        assert(brief.navigation.some((item) => item.label === label), `Mission Brief navigation missing ${label}`);
    });
    assert(brief.authority.live_capital_enabled === false, "Mission Brief must keep live capital disabled");
    assert(brief.authority.broker_write_allowed === false, "Mission Brief must keep broker writes disabled");
    assert(brief.authority.dashboard_write_authority === false, "Mission Brief must keep dashboard writes disabled");
    assert(brief.authority.telegram_command_authority === false, "Mission Brief must keep Telegram command authority disabled");
    assert(brief.boundary.includes("read-only"), "Mission Brief boundary must be read-only");
    assert(brief.boundary.includes("cannot approve"), "Mission Brief boundary must deny approval authority");

    const rendered = await renderWithStatus(status);
    assertIncludes(rendered, "[data-overview-mission-brief]", "Mission Snapshot");
    assertIncludes(rendered, "[data-overview-mission-brief]", "Durable replay");
    assertIncludes(rendered, "[data-overview-mission-brief]", "Safety boundary");
    assertIncludes(rendered, "[data-overview-mission-brief]", "Paper-only, read-only");
    assertIncludes(rendered, "[data-overview-mission-brief]", "it cannot approve trades");
    assert(
        !html(rendered, "[data-overview-mission-brief]").includes("hover"),
        "RS-8 Mission Brief should not rely on hover instructions"
    );

    console.log("dashboard_rs8_mission_control=ok");
    console.log("dashboard_rs8_question_count=7");
    console.log("dashboard_rs8_visible_expand_controls=True");
    console.log("dashboard_rs8_authority_unchanged=True");
}

main().catch((error) => {
    console.error(error);
    process.exit(1);
});
