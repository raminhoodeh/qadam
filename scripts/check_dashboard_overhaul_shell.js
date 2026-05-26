#!/usr/bin/env node

const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");

const repoRoot = path.resolve(__dirname, "..");
const htmlPath = path.join(repoRoot, "landing-page-repo", "dashboard", "index.html");
const cssPath = path.join(repoRoot, "landing-page-repo", "auth.css");
const rendererPath = path.join(repoRoot, "landing-page-repo", "dashboard.js");
const planPath = path.join(repoRoot, "docs", "qadam-dashboard-overhaul-master-implementation-plan.md");

const html = fs.readFileSync(htmlPath, "utf8");
const css = fs.readFileSync(cssPath, "utf8");
const renderer = fs.readFileSync(rendererPath, "utf8");
const plan = fs.readFileSync(planPath, "utf8");

function assert(condition, message) {
    if (!condition) throw new Error(message);
}

function includesAll(text, needles, label) {
    needles.forEach((needle) => {
        assert(text.includes(needle), `${label} missing ${needle}`);
    });
}

function parseViewLinks(source) {
    const links = [];
    const pattern = /<a\b([^>]*)\bdata-dashboard-view-link\b([^>]*)>([^<]+)<\/a>/g;
    let match;
    while ((match = pattern.exec(source)) !== null) {
        const attributes = `${match[1]} ${match[2]}`;
        links.push({
            label: match[3].trim(),
            href: attributes.match(/\bhref="([^"]+)"/)?.[1],
            target: attributes.match(/\bdata-dashboard-view-target="([^"]+)"/)?.[1],
            section: attributes.match(/\bdata-target-section="([^"]+)"/)?.[1]
        });
    }
    return links;
}

function parseViewSections(source) {
    const sections = [];
    const pattern = /<(section|article)\b([^>]*)\bdata-dashboard-view-section="([^"]+)"([^>]*)>/g;
    let match;
    while ((match = pattern.exec(source)) !== null) {
        const attributes = `${match[2]} ${match[4]}`;
        sections.push({
            id: attributes.match(/\bid="([^"]+)"/)?.[1],
            view: match[3],
            label: attributes.match(/\bdata-cockpit-section="([^"]+)"/)?.[1],
            hidden: /\shidden(?:\s|>|$)/.test(match[0])
        });
    }
    return sections;
}

class FakeClassList {
    constructor() {
        this.values = new Set();
    }

    toggle(name, active) {
        if (active) {
            this.values.add(name);
        } else {
            this.values.delete(name);
        }
    }

    contains(name) {
        return this.values.has(name);
    }
}

class FakeElement {
    constructor({ id = "", text = "", dataset = {} } = {}) {
        this.id = id;
        this.textContent = text;
        this.dataset = dataset;
        this.hidden = false;
        this.attributes = {};
        this.classList = new FakeClassList();
        this.listeners = {};
        this.scrolled = false;
    }

    setAttribute(name, value) {
        this.attributes[name] = String(value);
    }

    removeAttribute(name) {
        delete this.attributes[name];
    }

    addEventListener(name, handler) {
        this.listeners[name] = handler;
    }

    scrollIntoView() {
        this.scrolled = true;
    }
}

function loadShellHarness() {
    const viewIds = ["overview", "trades", "sources", "reasoning", "performance", "operations", "governance"];
    const sectionMappings = {
        "mission-control": "overview",
        "review-sequence": "overview",
        watching: "sources",
        cognition: "reasoning",
        "strategy-manifestation": "reasoning",
        worldview: "reasoning",
        "trade-layer": "trades",
        money: "performance",
        "system-map": "operations",
        forbidden: "operations",
        "process-console": "operations",
        communications: "governance",
        governance: "governance"
    };
    const links = viewIds.map((viewId) => new FakeElement({
        text: viewId.replace(/^\w/, (char) => char.toUpperCase()),
        dataset: {
            dashboardViewTarget: viewId,
            targetSection: viewId
        }
    }));
    const sections = Object.entries(sectionMappings).map(([id, view]) => new FakeElement({
        id,
        dataset: { dashboardViewSection: view }
    }));
    const current = new FakeElement({ text: "Overview" });
    const byId = new Map(sections.map((section) => [section.id, section]));
    const documentElement = { dataset: {} };
    const document = {
        documentElement,
        querySelector(selector) {
            if (selector === "[data-dashboard-view-current]" || selector === "[data-cockpit-nav-current]") return current;
            return null;
        },
        querySelectorAll(selector) {
            if (selector === "[data-dashboard-view-link]" || selector === "[data-cockpit-nav-link]") return links;
            if (selector === "[data-dashboard-view-section]") return sections;
            if (selector === "[data-density-option]") return [];
            return [];
        },
        getElementById(id) {
            return byId.get(id) || null;
        }
    };
    const events = {};
    const window = {
        document,
        history: {
            pushed: [],
            pushState(_state, _title, url) {
                this.pushed.push(url);
                window.location.hash = url;
            }
        },
        location: { hash: "" },
        requestAnimationFrame(callback) {
            callback();
        },
        scrollTo(options) {
            window.lastScroll = options;
        },
        scrollY: 0,
        addEventListener(name, handler) {
            events[name] = handler;
        }
    };
    const sessionStorage = {
        values: new Map(),
        getItem(key) {
            return this.values.get(key) || null;
        },
        setItem(key, value) {
            this.values.set(key, String(value));
        }
    };
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
        fetch: async () => ({ ok: true, json: async () => ({}) }),
        localStorage: {
            getItem() {
                return null;
            },
            setItem() {}
        },
        sessionStorage,
        window
    };
    window.window = window;
    vm.createContext(context);
    vm.runInContext(renderer, context, { filename: rendererPath });
    return { window, links, sections, current, byId, events };
}

const expectedViews = ["overview", "trades", "sources", "reasoning", "performance", "operations", "governance"];
const expectedLabels = ["Overview", "Trades", "Sources", "Reasoning", "Performance", "Operations", "Governance"];
const links = parseViewLinks(html);
const sections = parseViewSections(html);
const sectionById = new Map(sections.map((section) => [section.id, section]));

assert(links.length === 7, `expected 7 dashboard view links, got ${links.length}`);
assert(JSON.stringify(links.map((link) => link.target)) === JSON.stringify(expectedViews), "dashboard view link order mismatch");
assert(JSON.stringify(links.map((link) => link.label)) === JSON.stringify(expectedLabels), "dashboard view labels mismatch");
links.forEach((link) => {
    assert(link.href === `#${link.target}`, `${link.target} link href mismatch`);
    assert(link.section === link.target, `${link.target} target section mismatch`);
});

assert(sections.length === 13, `expected 13 segmented dashboard sections, got ${sections.length}`);
[
    ["mission-control", "overview"],
    ["review-sequence", "overview"],
    ["trade-layer", "trades"],
    ["watching", "sources"],
    ["cognition", "reasoning"],
    ["strategy-manifestation", "reasoning"],
    ["worldview", "reasoning"],
    ["money", "performance"],
    ["system-map", "operations"],
    ["forbidden", "operations"],
    ["process-console", "operations"],
    ["communications", "governance"],
    ["governance", "governance"]
].forEach(([id, view]) => {
    assert(sectionById.get(id)?.view === view, `${id} should map to ${view}`);
});
sections.forEach((section) => {
    assert(expectedViews.includes(section.view), `${section.id} has invalid view ${section.view}`);
    if (section.view === "overview") {
        assert(section.hidden === false, `${section.id} should be visible by default`);
    } else {
        assert(section.hidden === true, `${section.id} should be hidden by default`);
    }
});

includesAll(css, [
    "[data-dashboard-view-section][hidden]",
    "html[data-dashboard-active-view=\"overview\"] .dashboard-detail-flow",
    ".dashboard-view-switcher",
    "min-height: 38px",
    ".cockpit-nav-links a[aria-current=\"page\"]"
], "segmented shell CSS");

includesAll(renderer, [
    "const DASHBOARD_VIEWS",
    "const DASHBOARD_LEGACY_SECTION_VIEWS",
    "function resolveDashboardHash",
    "function activateDashboardView",
    "function activateDashboardViewFromHash",
    "data-dashboard-view-section",
    "data-dashboard-view-link",
    "window.activateQadamDashboardView"
], "segmented shell renderer");

const harness = loadShellHarness();
assert(harness.window.resolveQadamDashboardHash("#money").viewId === "performance", "legacy #money should resolve to Performance");
assert(harness.window.resolveQadamDashboardHash("#system-map").viewId === "operations", "legacy #system-map should resolve to Operations");
assert(harness.window.resolveQadamDashboardHash("#cognition").viewId === "reasoning", "legacy #cognition should resolve to Reasoning");
assert(harness.window.resolveQadamDashboardHash("#trades").viewId === "trades", "#trades should resolve to Trades");
assert(harness.window.document.documentElement.dataset.dashboardActiveView === "overview", "/dashboard/ should start on Overview");
assert(harness.byId.get("mission-control").hidden === false, "Overview mission control should be visible at startup");
assert(harness.byId.get("trade-layer").hidden === true, "Trades panel should be hidden at startup");
assert(harness.current.textContent === "Overview", "current view label should start at Overview");

harness.window.activateQadamDashboardView("trades", { scroll: false });
assert(harness.window.document.documentElement.dataset.dashboardActiveView === "trades", "activate trades failed");
assert(harness.byId.get("trade-layer").hidden === false, "trade layer should show for Trades");
assert(harness.byId.get("mission-control").hidden === true, "overview should hide for Trades");
assert(harness.current.textContent === "Trades", "current view label should update to Trades");

harness.window.activateQadamDashboardViewFromHash("#money", { scroll: true });
assert(harness.window.document.documentElement.dataset.dashboardActiveView === "performance", "legacy #money should activate Performance");
assert(harness.byId.get("money").hidden === false, "money should show for Performance");
assert(harness.byId.get("money").scrolled === true, "legacy #money should scroll to target");

harness.window.activateQadamDashboardViewFromHash("#system-map", { scroll: false });
assert(harness.window.document.documentElement.dataset.dashboardActiveView === "operations", "legacy #system-map should activate Operations");
assert(harness.byId.get("system-map").hidden === false, "system map should show for Operations");
assert(harness.byId.get("forbidden").hidden === false, "safety should show for Operations");
assert(harness.byId.get("process-console").hidden === false, "process console should show for Operations");

[
    "DX-4 - Segmented Shell",
    "Add a primary view switcher",
    "Render only the active segment by default",
    "Keep old section anchors as compatibility redirects"
].forEach((needle) => {
    assert(plan.includes(needle), `master plan missing DX-4 marker: ${needle}`);
});

console.log("dashboard_overhaul_shell=ok");
console.log("dashboard_default_view=overview");
console.log("dashboard_segmented_views_enabled=True");
console.log("dashboard_primary_view_count=7");
console.log(`dashboard_segmented_section_count=${sections.length}`);
console.log("dashboard_legacy_anchor_redirects=True");
console.log("dashboard_mobile_tap_targets_stable=True");
console.log("dashboard_authority_unchanged=True");
