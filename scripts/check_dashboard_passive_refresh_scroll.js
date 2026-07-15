#!/usr/bin/env node

const fs = require("node:fs");
const path = require("node:path");

const {
    assert,
    renderWithStatus,
    status
} = require("./check_dashboard_renderer.js");

const repoRoot = path.resolve(__dirname, "..");
const dashboardSiteRoot = path.resolve(
    process.env.QADAM_DASHBOARD_SITE_ROOT || path.join(repoRoot, "landing-page-repo")
);
const renderer = fs.readFileSync(path.join(dashboardSiteRoot, "dashboard.js"), "utf8");

async function main() {
    const rendered = await renderWithStatus(status);
    const { window } = rendered;
    const previousSidebar = { scrollTop: 287 };
    const replacementSidebar = { scrollTop: 0 };
    const previousRoot = {
        querySelector(selector) {
            return selector === "[data-qsase-sidebar]" ? previousSidebar : null;
        }
    };
    const replacementRoot = {
        querySelector(selector) {
            return selector === "[data-qsase-sidebar]" ? replacementSidebar : null;
        }
    };

    window.scrollX = 14;
    window.scrollY = 1840;
    const scrollCalls = [];
    window.scrollTo = (options) => scrollCalls.push(options);
    window.requestAnimationFrame = (callback) => {
        callback();
        return scrollCalls.length;
    };

    const state = window.captureQadamDashboardViewportState(previousRoot);
    assert(state.scrollX === 14, `captured horizontal page position mismatch: ${state.scrollX}`);
    assert(state.scrollY === 1840, `captured vertical page position mismatch: ${state.scrollY}`);
    assert(state.sidebarScrollTop === 287, `captured sidebar position mismatch: ${state.sidebarScrollTop}`);

    window.restoreQadamDashboardViewportState(replacementRoot, state);
    assert(replacementSidebar.scrollTop === 287, "passive refresh did not restore independent sidebar position");
    assert(scrollCalls.length === 3, `expected immediate and two frame-aligned page restores, found ${scrollCalls.length}`);
    scrollCalls.forEach((call) => {
        assert(call.left === 14 && call.top === 1840 && call.behavior === "auto", "passive refresh changed the restored page position");
    });

    [
        "const preserveViewport = Boolean(target.querySelector?.(\"[data-qsase-dashboard-rendered]\"))",
        "const viewportState = preserveViewport ? captureQsaseViewportState(target) : null",
        "if (viewportState) restoreQsaseViewportState(target, viewportState)"
    ].forEach((contract) => assert(renderer.includes(contract), `passive refresh renderer missing ${contract}`));

    console.log("dashboard_passive_refresh_scroll=ok");
    console.log("page_scroll_restores=3");
    console.log("sidebar_scroll_restored=true");
}

main().catch((error) => {
    console.error(error.message);
    process.exitCode = 1;
});
