#!/usr/bin/env node

const fs = require("node:fs");
const path = require("node:path");

const repoRoot = path.resolve(__dirname, "..");
const htmlPath = path.join(repoRoot, "landing-page-repo", "dashboard", "index.html");
const cssPath = path.join(repoRoot, "landing-page-repo", "auth.css");
const html = fs.readFileSync(htmlPath, "utf8");
const css = fs.readFileSync(cssPath, "utf8");

function assert(condition, message) {
    if (!condition) throw new Error(message);
}

function assertIncludes(haystack, needle, message) {
    assert(haystack.includes(needle), message || `missing ${needle}`);
}

function blockFor(selector) {
    const escapedSelector = selector.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
    const matcher = new RegExp(`(^|\\n)\\s*${escapedSelector}\\s*(?:,|\\{)`, "g");
    let match;
    let start = -1;
    while ((match = matcher.exec(css)) !== null) {
        const candidate = match.index + match[0].lastIndexOf(selector);
        let previous = candidate - 1;
        while (previous >= 0 && /\s/.test(css[previous])) previous -= 1;
        if (css[previous] === ",") continue;
        start = candidate;
        break;
    }
    assert(start >= 0, `missing selector ${selector}`);
    const open = css.indexOf("{", start);
    const close = css.indexOf("}", open);
    assert(open >= 0 && close >= 0, `selector ${selector} has no complete block`);
    return css.slice(open + 1, close);
}

[
    "--bg: #0a0a0c",
    "--panel:",
    "--line-strong:",
    "--cyan:",
    "--green:",
    "--amber:",
    "--coral:",
    "--font-sans:",
    "--font-mono:",
    "--shadow-panel:",
    "--glow-cyan:",
    "--glow-green:",
    "--glow-amber:",
    "--glow-coral:"
].forEach((needle) => assertIncludes(css, needle, `visual token missing ${needle}`));

assert(!css.includes("font-family: Arial"), "dashboard visual system regressed to Arial");
assert(!css.includes("#071012"), "dashboard visual system regressed to old green-black base");
assert(!/radial-gradient\s*\(/.test(css), "dashboard visual system should avoid decorative radial orb backgrounds");

[
    [".info-card", ["backdrop-filter: blur", "var(--shadow-panel)", "var(--glow-cyan)"]],
    [".metric strong", ["font-family: var(--font-mono)", "font-variant-numeric: tabular-nums"]],
    [".node-status", ["font-family: var(--font-mono)", "font-variant-numeric: tabular-nums"]],
    [".node-status.online", ["var(--glow-green)", "var(--green)"]],
    [".node-status.pending", ["var(--glow-amber)", "var(--amber)"]],
    [".node-status.blocked", ["var(--glow-coral)", "var(--coral)"]],
    [".inline-badge", ["font-family: var(--font-mono)", "font-variant-numeric: tabular-nums"]],
    [".priority-card.online", ["var(--glow-green)"]],
    [".priority-card.blocked", ["var(--glow-coral)"]],
    [".flow-lane.online", ["var(--glow-green)"]],
    [".flow-lane.blocked", ["var(--glow-coral)"]],
    [".flow-return-loop", ["var(--glow-cyan)"]],
    [".trade-intent-card.pending", ["var(--glow-amber)"]],
    [".trade-intent-card.blocked", ["var(--glow-coral)"]],
    [".console-feed time", ["font-family: var(--font-mono)", "font-variant-numeric: tabular-nums"]]
].forEach(([selector, needles]) => {
    const block = blockFor(selector);
    needles.forEach((needle) => assertIncludes(block, needle, `${selector} missing ${needle}`));
});

assertIncludes(css, "@media (prefers-reduced-motion: reduce)", "visual system missing reduced-motion guard");
assertIncludes(css, "transition:", "visual system missing tactile transitions");
assertIncludes(css, "body:has(.dashboard-shell)", "dashboard-specific visual background missing");
assertIncludes(html, "/auth.css?v=20260526-paper-equity-chart", "dashboard HTML missing current stylesheet cache key");

console.log("dashboard_visual_system=ok");
