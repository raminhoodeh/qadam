#!/usr/bin/env node

const fs = require("node:fs");
const path = require("node:path");

const repoRoot = path.resolve(__dirname, "..");
const cssPath = path.join(repoRoot, "landing-page-repo", "auth.css");
const css = fs.readFileSync(cssPath, "utf8");

function assert(condition, message) {
    if (!condition) {
        throw new Error(message);
    }
}

function desktopRule(selector) {
    const desktopStart = css.indexOf("@media (min-width: 901px)");
    assert(desktopStart >= 0, "desktop dashboard media query is missing");

    const desktopCss = css.slice(desktopStart);
    const escaped = selector.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
    const match = desktopCss.match(new RegExp(`(?:^|\\n)\\s*${escaped}\\s*\\{([^}]*)\\}`));
    assert(match, `desktop rule missing for ${selector}`);
    return match[1];
}

function hasProperty(rule, property, value) {
    const escapedProperty = property.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
    const escapedValue = value.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
    return new RegExp(`(?:^|;)\\s*${escapedProperty}\\s*:\\s*${escapedValue}\\s*(?:;|$)`).test(rule);
}

const bodyRule = desktopRule("body:has(.dashboard-shell)");
assert(!bodyRule.includes("overflow: hidden"), "dashboard desktop body must not lock page scrolling");
assert(bodyRule.includes("overflow-y: auto"), "dashboard desktop body should allow vertical scrolling");

const shellRule = desktopRule(".dashboard-shell");
assert(!hasProperty(shellRule, "height", "100dvh"), "dashboard shell must not be fixed to one viewport");
assert(!shellRule.includes("overflow: hidden"), "dashboard shell must not clip the page");
assert(hasProperty(shellRule, "min-height", "100dvh"), "dashboard shell should use min-height instead of fixed height");

const workspaceRule = desktopRule(".dashboard-workspace");
assert(!workspaceRule.includes("overflow: hidden"), "dashboard workspace must not trap scrolling");
assert(!workspaceRule.includes("32vh"), "dashboard workspace must not squeeze the system map into a viewport fraction");
assert(workspaceRule.includes("overflow: visible"), "dashboard workspace should allow page-flow content");

const panelScrollRule = desktopRule(".panel-scroll");
assert(!panelScrollRule.includes("overflow: auto"), "dashboard panels should not all become nested scroll containers");
assert(panelScrollRule.includes("overflow: visible"), "dashboard panel bodies should expand into the page by default");

console.log("dashboard_page_architecture=ok");
