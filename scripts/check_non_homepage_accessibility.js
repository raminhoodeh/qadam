#!/usr/bin/env node

const fs = require("node:fs");
const path = require("node:path");

const repoRoot = path.resolve(__dirname, "..");
const dashboardSiteRoot = path.resolve(
    process.env.QADAM_DASHBOARD_SITE_ROOT || path.join(repoRoot, "landing-page-repo")
);

function read(relativePath) {
    const prefix = "landing-page-repo/";
    const filePath = relativePath.startsWith(prefix)
        ? path.join(dashboardSiteRoot, relativePath.slice(prefix.length))
        : path.join(repoRoot, relativePath);
    return fs.readFileSync(filePath, "utf8");
}

function assert(condition, message) {
    if (!condition) throw new Error(message);
}

function includesAll(text, needles, label) {
    needles.forEach((needle) => {
        assert(text.includes(needle), `${label} missing ${needle}`);
    });
}

function hexToRgb(hex) {
    const clean = hex.replace("#", "");
    return [0, 2, 4].map((index) => parseInt(clean.slice(index, index + 2), 16) / 255);
}

function linearise(value) {
    return value <= 0.03928 ? value / 12.92 : ((value + 0.055) / 1.055) ** 2.4;
}

function luminance(hex) {
    const [r, g, b] = hexToRgb(hex).map(linearise);
    return 0.2126 * r + 0.7152 * g + 0.0722 * b;
}

function contrastRatio(a, b) {
    const first = luminance(a);
    const second = luminance(b);
    const lighter = Math.max(first, second);
    const darker = Math.min(first, second);
    return (lighter + 0.05) / (darker + 0.05);
}

function assertContrast(foreground, background, minimum, label) {
    const ratio = contrastRatio(foreground, background);
    assert(ratio >= minimum, `${label} contrast ${ratio.toFixed(2)} below ${minimum}`);
}

function assertNoUnsafeTabindex(html, label) {
    const bad = html.match(/\btabindex="(?!-1"|0")[^"]+"/g) || [];
    assert(bad.length === 0, `${label} contains positive or unsafe tabindex: ${bad.join(", ")}`);
}

function assertUniqueIds(html, label) {
    const ids = Array.from(html.matchAll(/\bid="([^"]+)"/g)).map((match) => match[1]);
    const duplicates = ids.filter((id, index) => ids.indexOf(id) !== index);
    assert(duplicates.length === 0, `${label} contains duplicate ids: ${[...new Set(duplicates)].join(", ")}`);
}

function assertImagesHaveAlt(html, label) {
    const images = Array.from(html.matchAll(/<img\b([^>]*)>/g));
    images.forEach(([, attrs], index) => {
        const alt = attrs.match(/\balt="([^"]*)"/)?.[1];
        assert(alt !== undefined && alt.trim(), `${label} image ${index + 1} missing non-empty alt`);
    });
}

function assertNavsHaveLabels(html, label) {
    const navs = Array.from(html.matchAll(/<nav\b([^>]*)>/g));
    assert(navs.length > 0, `${label} must expose at least one nav landmark`);
    navs.forEach(([, attrs], index) => {
        assert(/\baria-label="[^"]+"/.test(attrs), `${label} nav ${index + 1} missing aria-label`);
    });
}

function assertButtonsHaveNames(html, label) {
    const buttons = Array.from(html.matchAll(/<button\b([^>]*)>([\s\S]*?)<\/button>/g));
    buttons.forEach(([, attrs, body], index) => {
        const hasAria = /\baria-label="[^"]+"/.test(attrs);
        const text = body.replace(/<[^>]+>/g, "").trim();
        assert(hasAria || text, `${label} button ${index + 1} missing accessible name`);
    });
}

function assertRoleImagesHaveLabels(html, label) {
    const roleImages = Array.from(html.matchAll(/<[^>]+\brole="img"[^>]*>/g));
    roleImages.forEach(([tag], index) => {
        assert(/\baria-label="[^"]+"/.test(tag), `${label} role=img ${index + 1} missing aria-label`);
    });
}

function assertSkipTarget(html, href, label) {
    const id = href.replace("#", "");
    assert(html.includes(`href="${href}"`), `${label} missing skip link ${href}`);
    const targetTag = html.match(new RegExp(`<[^>]+\\bid="${id}"[^>]*>`))?.[0] || "";
    assert(targetTag, `${label} missing skip target ${id}`);
    assert(targetTag.includes('tabindex="-1"'), `${label} skip target must be programmatically focusable`);
}

const pages = {
    login: read("landing-page-repo/login/index.html"),
    signup: read("landing-page-repo/sign-up/index.html"),
    whitepaper: read("landing-page-repo/whitepaper/index.html"),
    guide: read("landing-page-repo/guide/index.html"),
    dashboard: read("landing-page-repo/dashboard/index.html")
};
const layoutCss = read("landing-page-repo/non-homepage-layout.css");
const tokenCss = read("landing-page-repo/non-homepage-tokens.css");
const authCss = read("landing-page-repo/auth.css");
const whitepaperCss = read("landing-page-repo/whitepaper.css");
const authJs = read("landing-page-repo/auth.js");
const dashboardJs = read("landing-page-repo/dashboard.js");
const quantumEdgeJs = read("landing-page-repo/quantum-edge-page.js");
const quantumEdgeCss = read("landing-page-repo/quantum-edge-page.css");
const homeHtml = read("landing-page-repo/index.html");
const homeCss = read("landing-page-repo/style.css");

[
    ["login", "#login-main"],
    ["signup", "#signup-main"],
    ["whitepaper", "#whitepaper-main"],
    ["guide", "#guide-main"],
    ["dashboard", "#dashboard-main"]
].forEach(([name, target]) => assertSkipTarget(pages[name], target, name));

Object.entries(pages).forEach(([name, html]) => {
    assertImagesHaveAlt(html, name);
    assertNavsHaveLabels(html, name);
    assertButtonsHaveNames(html, name);
    assertRoleImagesHaveLabels(html, name);
    assertNoUnsafeTabindex(html, name);
    assertUniqueIds(html, name);
});

includesAll(pages.login, [
    'id="login-status"',
    'data-status aria-live="polite"',
    'data-login-form aria-describedby="login-status"',
    'autocomplete="email"',
    'autocomplete="current-password"'
], "login accessibility");

includesAll(pages.signup, [
    'id="signup-status"',
    'data-status aria-live="polite"',
    'data-signup-form aria-describedby="signup-status"',
    'autocomplete="email"',
    'autocomplete="new-password"'
], "sign-up accessibility");

includesAll(pages.guide, [
    'hidden" data-dashboard tabindex="-1"'
], "guide protected accessibility");
assert(!pages.guide.includes("data-signout"), "User Guide must not expose a sign-out control");
assert(!pages.guide.includes("data-user-email"), "User Guide must not expose the signed-in email");

includesAll(pages.dashboard, [
    'aria-live="polite"',
    'hidden" data-dashboard tabindex="-1"',
    'id="dashboard-main"',
    'href="#dashboard-main"',
    'data-stage7-dashboard-visibility',
    'data-qadam-nav-context="public-dashboard"'
], "dashboard accessibility");

assert(!pages.dashboard.includes("data-signout"), "public dashboard must not expose a sign-out control");
[
    'aria-controls="dashboard-advanced-links"',
    'id="dashboard-advanced-links"',
    'data-dashboard-debug-toggle',
    'data-dashboard-view-link',
    'Paper trading mode',
    'Paper-only monitoring'
].forEach((needle) => {
    assert(!pages.dashboard.includes(needle), `dashboard accessibility should not include removed control ${needle}`);
});

includesAll(authJs, [
    'document.querySelector("[data-status]")',
    'function dashboardIsPublicReadOnly()',
    'window.renderQadamDashboardStatus(session || null)',
    'dashboard.classList.remove("hidden");',
    'window.location.replace(`/login/?next=${encodeURIComponent(currentPath)}`);'
], "auth js accessibility contract");

includesAll(dashboardJs, [
    'data-qsase-dashboard-rendered',
    'role="list"',
    'role="listitem"',
    'aria-label="Read-only paper trading chronology"',
    'aria-label="Portfolio data status"',
    'aria-label="Asset allocation: Cash 100%"',
    'aria-label="Open paper positions"',
    'aria-label="Qadam paper portfolio performance ${literalHtmlText(periodLabel.toLowerCase())} with timestamped horizontal axis"',
    'aria-label="Watched markets for this strategy"'
], "dashboard js accessibility contract");
assert(!dashboardJs.includes('<main class="qsase-module-workspace" aria-live='), "dashboard workspace must not be a broad live region");

includesAll(quantumEdgeJs, [
    'role="status" aria-live="polite"',
    'aria-expanded="false"',
    'aria-controls="${id}"',
    'aria-describedby="${id}"',
    'role="tooltip"',
    'event.key === "Escape"',
    'focus({ preventScroll: true })'
], "Quantum Edge dynamic accessibility contract");

includesAll(quantumEdgeCss, [
    ":focus-visible",
    "@media (prefers-reduced-motion: reduce)",
    "@media (forced-colors: active)",
    "min-height: 44px"
], "Quantum Edge accessibility css");

includesAll(layoutCss, [
    ".skip-link",
    ".skip-link:focus",
    ".sr-only",
    "min-height: var(--qadam-touch-target)",
    ":where(a, button, input, select, textarea, summary, [tabindex]):focus-visible",
    "main[tabindex=\"-1\"]:focus-visible",
    "@media (prefers-reduced-motion: reduce)",
    "@media (forced-colors: active)"
], "shared accessibility css");

includesAll(`${authCss}\n${whitepaperCss}`, [
    "@import url(\"/non-homepage-layout.css?v=20260628-stage2\");"
], "non-homepage css imports");

[
    ["ink on canvas", "#3f4148", "#ffffff"],
    ["heading on canvas", "#575058", "#ffffff"],
    ["muted on canvas", "#666a70", "#ffffff"],
    ["brand on page", "#a90036", "#f3f1ee"],
    ["white on brand", "#ffffff", "#a90036"],
    ["white on section band", "#ffffff", "#466b81"],
    ["info on info soft", "#3f708b", "#e6eff3"]
].forEach(([label, foreground, background]) => assertContrast(foreground, background, 4.5, label));

includesAll(tokenCss, [
    "--qadam-color-section-band: #466b81",
    "--qadam-color-section-band-dark: #36566a",
    "--qadam-shadow-focus"
], "accessible tokens");

[
    /PVZ[0-9A-Za-z_-]{20,}/,
    /\d{6,}:[A-Za-z0-9_-]{20,}/,
    /OPENAI_API_KEY=/,
    /ANTHROPIC_API_KEY=/,
    /TELEGRAM_BOT_TOKEN=/
].forEach((pattern) => {
    Object.entries(pages).forEach(([name, html]) => {
        assert(!pattern.test(html), `${name} contains unsafe public text: ${pattern}`);
    });
});

assert(!homeHtml.includes("skip-link"), "homepage must remain outside Stage 8 skip-link changes");
assert(!homeHtml.includes("qadam-section-nav"), "homepage must remain outside Stage 8 section nav changes");
assert(!homeCss.includes("qadam-nonhomepage-layout"), "homepage css must not import non-homepage accessibility layer");

console.log("non_homepage_accessibility=ok");
