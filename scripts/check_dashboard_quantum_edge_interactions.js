#!/usr/bin/env node

"use strict";

/**
 * Deterministic rendered-DOM acceptance check for Quantum Edge.
 *
 * The repository intentionally has no installed browser-DOM test dependency.
 * This harness therefore supplies the small standards-shaped DOM surface used
 * by quantum-edge-page.js, executes that production script in a VM, and drives
 * its real event handlers against the real public projection.
 */

const fs = require("fs");
const nodeCrypto = require("crypto");
const path = require("path");
const vm = require("vm");

function canonicalJson(value) {
    if (value === null || typeof value !== "object") {
        const encoded = JSON.stringify(value);
        return typeof encoded === "string"
            ? encoded.replace(/[\u007f-\uffff]/g, (character) => `\\u${character.charCodeAt(0).toString(16).padStart(4, "0")}`)
            : "null";
    }
    if (Array.isArray(value)) return `[${value.map(canonicalJson).join(",")}]`;
    return `{${Object.keys(value).sort().map((key) => `${canonicalJson(key)}:${canonicalJson(value[key])}`).join(",")}}`;
}

function projectionHash(payload) {
    const material = Object.fromEntries(Object.entries(payload).filter(([key]) => !["generated_at", "content_hash", "render_contract_hash"].includes(key)));
    return nodeCrypto.createHash("sha256").update(canonicalJson(material), "utf8").digest("hex");
}

function renderContractHash(payload) {
    const sourceContentHashes = Object.fromEntries((payload.source_artifacts || []).filter((row) => row && row.source_id).map((row) => [String(row.source_id), String(row.content_hash || "")]));
    const material = {
        content_hash: payload.content_hash,
        schema_version: payload.schema_version,
        contract_version: payload.contract_version,
        projection_status: payload.projection_status,
        page_copy: payload.page_copy,
        state_axes: payload.state_axes,
        presentation: payload.presentation,
        source_content_hashes: sourceContentHashes
    };
    return nodeCrypto.createHash("sha256").update(canonicalJson(material), "utf8").digest("hex");
}

function parseSiteRoot(argv) {
    const flagIndex = argv.indexOf("--site-root");
    if (flagIndex >= 0) {
        if (!argv[flagIndex + 1]) throw new Error("--site-root requires a path");
        return path.resolve(argv[flagIndex + 1]);
    }
    const positional = argv.find((value) => !value.startsWith("-"));
    if (!positional) throw new Error("Usage: check_dashboard_quantum_edge_interactions.js --site-root <site-root>");
    return path.resolve(positional);
}

const siteRoot = parseSiteRoot(process.argv.slice(2));

function readSite(relativePath) {
    return fs.readFileSync(path.join(siteRoot, relativePath), "utf8");
}

function decodeHtml(value) {
    return String(value)
        .replace(/&quot;/g, "\"")
        .replace(/&#0*39;/g, "'")
        .replace(/&lt;/g, "<")
        .replace(/&gt;/g, ">")
        .replace(/&amp;/g, "&");
}

function dataNameToProperty(name) {
    return name.slice(5).replace(/-([a-z0-9])/g, (_match, character) => character.toUpperCase());
}

function dataPropertyToName(property) {
    return `data-${String(property).replace(/[A-Z]/g, (character) => `-${character.toLowerCase()}`)}`;
}

class HarnessEvent {
    constructor(type, init = {}) {
        this.type = type;
        this.bubbles = Boolean(init.bubbles);
        this.cancelable = Boolean(init.cancelable);
        this.key = init.key || "";
        this.detail = init.detail;
        this.target = null;
        this.currentTarget = null;
        this.defaultPrevented = false;
        this.propagationStopped = false;
        this.immediatePropagationStopped = false;
    }

    preventDefault() {
        if (this.cancelable) this.defaultPrevented = true;
    }

    stopPropagation() {
        this.propagationStopped = true;
    }

    stopImmediatePropagation() {
        this.immediatePropagationStopped = true;
        this.propagationStopped = true;
    }
}

class HarnessCustomEvent extends HarnessEvent {}

class HarnessEventTarget {
    constructor() {
        this.listeners = new Map();
    }

    addEventListener(type, listener, options = false) {
        if (typeof listener !== "function") return;
        const capture = options === true || Boolean(options && options.capture);
        const rows = this.listeners.get(type) || [];
        rows.push({ listener, capture });
        this.listeners.set(type, rows);
    }

    removeEventListener(type, listener) {
        const rows = this.listeners.get(type) || [];
        this.listeners.set(type, rows.filter((row) => row.listener !== listener));
    }

    invokeListeners(event, capture) {
        const rows = [...(this.listeners.get(event.type) || [])];
        for (const row of rows) {
            if (row.capture !== capture) continue;
            event.currentTarget = this;
            row.listener.call(this, event);
            if (event.immediatePropagationStopped) break;
        }
    }

    dispatchEvent(event) {
        if (!(event instanceof HarnessEvent)) throw new TypeError("dispatchEvent expects an Event");
        if (!event.target) event.target = this;
        this.invokeListeners(event, true);
        if (!event.immediatePropagationStopped) this.invokeListeners(event, false);
        return !event.defaultPrevented;
    }
}

class HarnessNode extends HarnessEventTarget {
    constructor(ownerDocument = null) {
        super();
        this.ownerDocument = ownerDocument;
        this.parentNode = null;
        this.childNodes = [];
    }

    appendChild(child) {
        if (!child) return child;
        child.remove();
        child.parentNode = this;
        setOwnerDocument(child, this.nodeType === 9 ? this : this.ownerDocument);
        this.childNodes.push(child);
        return child;
    }

    removeChild(child) {
        const index = this.childNodes.indexOf(child);
        if (index >= 0) {
            this.childNodes.splice(index, 1);
            child.parentNode = null;
        }
        return child;
    }

    remove() {
        this.parentNode?.removeChild(this);
    }

    contains(candidate) {
        for (let node = candidate; node; node = node.parentNode) {
            if (node === this) return true;
        }
        return false;
    }

    get parentElement() {
        return this.parentNode?.nodeType === 1 ? this.parentNode : null;
    }

    get isConnected() {
        let node = this;
        while (node) {
            if (node.nodeType === 9) return true;
            node = node.parentNode;
        }
        return false;
    }

    get textContent() {
        return this.childNodes.map((child) => child.textContent).join("");
    }

    set textContent(value) {
        this.childNodes.forEach((child) => { child.parentNode = null; });
        this.childNodes = [];
        if (String(value ?? "")) this.appendChild(new HarnessText(String(value), this.ownerDocument));
    }
}

class HarnessText extends HarnessNode {
    constructor(value, ownerDocument) {
        super(ownerDocument);
        this.nodeType = 3;
        this.data = value;
    }

    get textContent() {
        return this.data;
    }

    set textContent(value) {
        this.data = String(value);
    }
}

class HarnessClassList {
    constructor(element) {
        this.element = element;
    }

    values() {
        return (this.element.getAttribute("class") || "").split(/\s+/).filter(Boolean);
    }

    write(values) {
        if (values.length) this.element.setAttribute("class", [...new Set(values)].join(" "));
        else this.element.removeAttribute("class");
    }

    contains(value) {
        return this.values().includes(value);
    }

    add(...values) {
        this.write([...this.values(), ...values]);
    }

    remove(...values) {
        this.write(this.values().filter((value) => !values.includes(value)));
    }

    toggle(value, force) {
        const present = this.contains(value);
        const next = force === undefined ? !present : Boolean(force);
        if (next) this.add(value);
        else this.remove(value);
        return next;
    }
}

function makeStyle() {
    const values = new Map();
    return new Proxy({
        removeProperty(name) {
            values.delete(name);
        },
        setProperty(name, value) {
            values.set(name, String(value));
        },
        getPropertyValue(name) {
            return values.get(name) || "";
        }
    }, {
        get(target, property) {
            if (property in target) return target[property];
            return values.get(String(property)) || "";
        },
        set(_target, property, value) {
            values.set(String(property), String(value));
            return true;
        }
    });
}

function matchesSimple(element, selector) {
    let remaining = selector.trim();
    if (!remaining || remaining === "*") return true;
    const tag = remaining.match(/^[a-z][a-z0-9-]*/i);
    if (tag) {
        if (element.tagName !== tag[0].toUpperCase()) return false;
        remaining = remaining.slice(tag[0].length);
    }
    for (const idMatch of remaining.matchAll(/#([a-z0-9_-]+)/gi)) {
        if (element.id !== idMatch[1]) return false;
    }
    for (const classMatch of remaining.matchAll(/\.([a-z0-9_-]+)/gi)) {
        if (!element.classList.contains(classMatch[1])) return false;
    }
    for (const attributeMatch of remaining.matchAll(/\[([^\]\s~|^$*!=]+)(?:\s*=\s*(?:"([^"]*)"|'([^']*)'|([^\]\s]+)))?\]/g)) {
        const name = attributeMatch[1];
        const expected = attributeMatch[2] ?? attributeMatch[3] ?? attributeMatch[4];
        if (!element.hasAttribute(name)) return false;
        if (expected !== undefined && element.getAttribute(name) !== expected) return false;
    }
    return true;
}

function descendants(root) {
    const rows = [];
    for (const child of root.children || []) {
        rows.push(child, ...descendants(child));
    }
    return rows;
}

class HarnessElement extends HarnessNode {
    constructor(tagName, ownerDocument) {
        super(ownerDocument);
        this.nodeType = 1;
        this.tagName = String(tagName).toUpperCase();
        this.attributes = new Map();
        this.classList = new HarnessClassList(this);
        this.style = makeStyle();
        this.scrollIntoViewCalls = [];
        this.dataset = new Proxy({}, {
            get: (_target, property) => this.getAttribute(dataPropertyToName(property)) ?? undefined,
            set: (_target, property, value) => {
                this.setAttribute(dataPropertyToName(property), value);
                return true;
            },
            ownKeys: () => [...this.attributes.keys()].filter((name) => name.startsWith("data-")).map(dataNameToProperty),
            getOwnPropertyDescriptor: () => ({ enumerable: true, configurable: true })
        });
    }

    get children() {
        return this.childNodes.filter((child) => child.nodeType === 1);
    }

    get firstElementChild() {
        return this.children[0] || null;
    }

    get id() {
        return this.getAttribute("id") || "";
    }

    set id(value) {
        this.setAttribute("id", value);
    }

    get className() {
        return this.getAttribute("class") || "";
    }

    set className(value) {
        this.setAttribute("class", value);
    }

    get hidden() {
        return this.hasAttribute("hidden");
    }

    set hidden(value) {
        if (value) this.setAttribute("hidden", "");
        else this.removeAttribute("hidden");
    }

    get disabled() {
        return this.hasAttribute("disabled");
    }

    set disabled(value) {
        if (value) this.setAttribute("disabled", "");
        else this.removeAttribute("disabled");
    }

    get open() {
        return this.hasAttribute("open");
    }

    set open(value) {
        const changed = Boolean(value) !== this.open;
        if (value) this.setAttribute("open", "");
        else this.removeAttribute("open");
        if (changed && this.tagName === "DETAILS") this.dispatchEvent(new HarnessEvent("toggle"));
    }

    setAttribute(name, value) {
        this.attributes.set(String(name).toLowerCase(), String(value ?? ""));
    }

    getAttribute(name) {
        return this.attributes.has(String(name).toLowerCase())
            ? this.attributes.get(String(name).toLowerCase())
            : null;
    }

    hasAttribute(name) {
        return this.attributes.has(String(name).toLowerCase());
    }

    removeAttribute(name) {
        this.attributes.delete(String(name).toLowerCase());
    }

    matches(selector) {
        return matchesSimple(this, selector);
    }

    closest(selector) {
        for (let element = this; element; element = element.parentElement) {
            if (element.matches(selector)) return element;
        }
        return null;
    }

    querySelectorAll(selector) {
        const trimmed = selector.trim();
        if (trimmed.startsWith(":scope > ")) {
            const childSelector = trimmed.slice(9).trim();
            return this.children.filter((child) => child.matches(childSelector));
        }
        return descendants(this).filter((element) => element.matches(trimmed));
    }

    querySelector(selector) {
        return this.querySelectorAll(selector)[0] || null;
    }

    get innerHTML() {
        return this.childNodes.map((child) => child.textContent).join("");
    }

    set innerHTML(markup) {
        this.childNodes.forEach((child) => { child.parentNode = null; });
        this.childNodes = [];
        parseHtmlFragment(String(markup), this.ownerDocument).forEach((child) => this.appendChild(child));
    }

    focus() {
        const document = this.ownerDocument;
        if (!document || document.activeElement === this) return;
        const previous = document.activeElement;
        document.activeElement = this;
        previous?.dispatchEvent(new HarnessEvent("blur"));
        this.dispatchEvent(new HarnessEvent("focus"));
    }

    click() {
        const event = new HarnessEvent("click", { bubbles: true, cancelable: true });
        this.dispatchEvent(event);
        if (!event.defaultPrevented && this.tagName === "SUMMARY" && this.parentElement?.tagName === "DETAILS") {
            this.parentElement.open = !this.parentElement.open;
        }
    }

    dispatchEvent(event) {
        if (!(event instanceof HarnessEvent)) throw new TypeError("dispatchEvent expects an Event");
        if (!event.target) event.target = this;
        const ancestors = [];
        for (let node = this.parentNode; node; node = node.parentNode) ancestors.push(node);
        const view = this.ownerDocument?.defaultView;
        if (view) ancestors.push(view);
        for (const target of [...ancestors].reverse()) {
            target.invokeListeners(event, true);
            if (event.propagationStopped) return !event.defaultPrevented;
        }
        this.invokeListeners(event, true);
        if (!event.immediatePropagationStopped) this.invokeListeners(event, false);
        if (event.bubbles && !event.propagationStopped) {
            for (const target of ancestors) {
                target.invokeListeners(event, false);
                if (event.propagationStopped) break;
            }
        }
        return !event.defaultPrevented;
    }

    getBoundingClientRect() {
        if (this.matches("[data-qep-help-trigger]")) return { left: 300, right: 324, top: 180, bottom: 204, width: 24, height: 24 };
        if (this.matches("[data-qep-help-popover]")) return { left: 0, right: 320, top: 0, bottom: 140, width: 320, height: 140 };
        return { left: 0, right: 800, top: 0, bottom: 600, width: 800, height: 600 };
    }

    scrollIntoView(options) {
        this.scrollIntoViewCalls.push(options || {});
    }
}

class HarnessDocument extends HarnessNode {
    constructor() {
        super(null);
        this.nodeType = 9;
        this.ownerDocument = this;
        this.documentElement = new HarnessElement("html", this);
        this.body = new HarnessElement("body", this);
        this.documentElement.appendChild(this.body);
        this.appendChild(this.documentElement);
        this.activeElement = this.body;
        this.defaultView = null;
    }

    get children() {
        return [this.documentElement];
    }

    createElement(tagName) {
        return new HarnessElement(tagName, this);
    }

    querySelectorAll(selector) {
        const rows = [];
        if (this.documentElement.matches(selector)) rows.push(this.documentElement);
        return rows.concat(this.documentElement.querySelectorAll(selector));
    }

    querySelector(selector) {
        return this.querySelectorAll(selector)[0] || null;
    }

    getElementById(id) {
        return this.querySelector(`#${id}`);
    }
}

class HarnessWindow extends HarnessEventTarget {
    constructor(document, { hash = "" } = {}) {
        super();
        this.document = document;
        this.location = {
            search: "?module=patterns&view=nonlinear",
            hash
        };
        this.innerWidth = 1280;
        this.innerHeight = 900;
        this.Event = HarnessEvent;
        this.CustomEvent = HarnessCustomEvent;
        this.URLSearchParams = URLSearchParams;
        this.requestAnimationFrame = (callback) => {
            callback(Date.now());
            return 1;
        };
        this.cancelAnimationFrame = () => {};
        this.setTimeout = setTimeout;
        this.clearTimeout = clearTimeout;
        this.matchMedia = () => ({ matches: false, addEventListener() {}, removeEventListener() {} });
    }
}

class HarnessMutationObserver {
    constructor(callback) {
        this.callback = callback;
    }

    observe() {}
    disconnect() {}
}

function setOwnerDocument(node, document) {
    if (!node || !document) return;
    node.ownerDocument = document;
    node.childNodes.forEach((child) => setOwnerDocument(child, document));
}

const voidElements = new Set(["AREA", "BASE", "BR", "COL", "EMBED", "HR", "IMG", "INPUT", "LINK", "META", "PARAM", "SOURCE", "TRACK", "WBR"]);

function parseAttributes(source, element) {
    const expression = /([^\s=/>]+)(?:\s*=\s*(?:"([^"]*)"|'([^']*)'|([^\s"'=<>`]+)))?/g;
    for (const match of source.matchAll(expression)) {
        element.setAttribute(match[1], decodeHtml(match[2] ?? match[3] ?? match[4] ?? ""));
    }
}

function parseHtmlFragment(markup, document) {
    const fragment = new HarnessElement("fragment", document);
    const stack = [fragment];
    const tokens = markup.match(/<!--[\s\S]*?-->|<\/?[a-z][^>]*>|[^<]+/gi) || [];
    for (const token of tokens) {
        if (token.startsWith("<!--")) continue;
        if (token.startsWith("</")) {
            if (stack.length > 1) stack.pop();
            continue;
        }
        if (token.startsWith("<")) {
            const open = token.match(/^<\s*([a-z][a-z0-9-]*)([\s\S]*?)\/?\s*>$/i);
            if (!open) continue;
            const element = new HarnessElement(open[1], document);
            parseAttributes(open[2], element);
            stack[stack.length - 1].appendChild(element);
            if (!token.endsWith("/>") && !voidElements.has(element.tagName)) stack.push(element);
            continue;
        }
        stack[stack.length - 1].appendChild(new HarnessText(decodeHtml(token), document));
    }
    return [...fragment.childNodes].map((child) => {
        child.parentNode = null;
        return child;
    });
}

function workspaceAttributes(dashboardSource) {
    const match = dashboardSource.match(/<main\s+class="qsase-module-workspace"([^>]*)>/);
    if (!match) throw new Error("Could not locate the dashboard workspace markup");
    const probe = new HarnessElement("main", null);
    probe.setAttribute("class", "qsase-module-workspace");
    parseAttributes(match[1], probe);
    return [...probe.attributes.entries()];
}

function makeSessionStorage(seed = {}) {
    const values = new Map(Object.entries(seed));
    return {
        getItem(key) { return values.has(key) ? values.get(key) : null; },
        setItem(key, value) { values.set(key, String(value)); },
        removeItem(key) { values.delete(key); },
        clear() { values.clear(); },
        snapshot() { return Object.fromEntries(values); }
    };
}

function makeTimerScheduler() {
    let now = 0;
    let nextId = 1;
    const pending = new Map();

    const setTimer = (callback, delay = 0, ...args) => {
        const id = nextId++;
        const numericDelay = Number(delay);
        pending.set(id, {
            callback,
            args,
            dueAt: now + (Number.isFinite(numericDelay) ? Math.max(0, numericDelay) : 0)
        });
        return id;
    };

    const clearTimer = (id) => pending.delete(id);

    const advanceBy = (milliseconds) => {
        const target = now + Math.max(0, Number(milliseconds) || 0);
        while (true) {
            const next = [...pending.entries()]
                .filter(([, timer]) => timer.dueAt <= target)
                .sort(([leftId, left], [rightId, right]) => left.dueAt - right.dueAt || leftId - rightId)[0];
            if (!next) break;
            const [id, timer] = next;
            pending.delete(id);
            now = timer.dueAt;
            timer.callback(...timer.args);
        }
        now = target;
    };

    return {
        setTimeout: setTimer,
        clearTimeout: clearTimer,
        advanceBy,
        pendingCount: () => pending.size
    };
}

async function settle() {
    await Promise.resolve();
    await Promise.resolve();
    await new Promise((resolve) => setImmediate(resolve));
}

async function boot({ projection, pageScript, dashboardSource, hash = "", sessionSeed = {} }) {
    const document = new HarnessDocument();
    const timers = makeTimerScheduler();
    const window = new HarnessWindow(document, { hash });
    window.setTimeout = timers.setTimeout;
    window.clearTimeout = timers.clearTimeout;
    document.defaultView = window;
    const storage = makeSessionStorage(sessionSeed);
    const workspace = document.createElement("main");
    workspaceAttributes(dashboardSource).forEach(([name, value]) => workspace.setAttribute(name, value));
    const panel = document.createElement("section");
    panel.setAttribute("data-qsase-module-panel", "patterns");
    panel.setAttribute("data-qsase-view-panel", "nonlinear");
    const lifecycle = document.createElement("aside");
    lifecycle.setAttribute("data-qadam-lifecycle", "");
    panel.appendChild(lifecycle);
    workspace.appendChild(panel);
    document.body.appendChild(workspace);

    const context = {
        window,
        document,
        sessionStorage: storage,
        MutationObserver: HarnessMutationObserver,
        CustomEvent: HarnessCustomEvent,
        Event: HarnessEvent,
        crypto: nodeCrypto.webcrypto,
        TextEncoder,
        URLSearchParams,
        fetch: async (url, options) => {
            if (!String(url).startsWith("/status/quantum-edge-page.json?v=")) throw new Error(`Unexpected fetch URL: ${url}`);
            if (options?.cache !== "no-store" || options?.credentials !== "same-origin") throw new Error("Projection fetch options changed");
            return { ok: true, status: 200, async json() { return JSON.parse(JSON.stringify(projection)); } };
        },
        console,
        setTimeout: timers.setTimeout,
        clearTimeout: timers.clearTimeout
    };
    window.window = window;
    window.self = window;
    Object.assign(window, context);
    vm.runInNewContext(pageScript, context, { filename: path.join(siteRoot, "quantum-edge-page.js") });
    await settle();
    // WebCrypto digest completion is deliberately asynchronous and can take
    // more than one microtask turn on a busy host. Wait for the production
    // renderer (or its fail-closed surface) instead of racing that digest.
    for (let attempt = 0; attempt < 50 && !document.querySelector("[data-quantum-edge-page]"); attempt += 1) {
        await new Promise((resolve) => setImmediate(resolve));
    }
    return { document, window, workspace, panel, storage, timers };
}

function pressSummaryKey(summary, key) {
    if (!summary) return;
    const keydown = new HarnessEvent("keydown", { bubbles: true, cancelable: true, key });
    const shouldActivate = summary.dispatchEvent(keydown);
    if (key === "Enter" && shouldActivate && summary.tagName === "SUMMARY") summary.click();
    const keyup = new HarnessEvent("keyup", { bubbles: true, cancelable: true, key });
    const shouldActivateOnKeyup = summary.dispatchEvent(keyup);
    if (key === " " && shouldActivate && shouldActivateOnKeyup && summary.tagName === "SUMMARY") summary.click();
}

function isInteractive(element) {
    if (["A", "BUTTON", "INPUT", "SELECT", "TEXTAREA", "SUMMARY"].includes(element.tagName)) return true;
    if (["button", "link", "checkbox", "radio", "switch", "tab"].includes(element.getAttribute("role"))) return true;
    return element.hasAttribute("tabindex") && element.getAttribute("tabindex") !== "-1";
}

function findNestedInteractive(root) {
    return descendants(root).filter(isInteractive).flatMap((element) => {
        for (let ancestor = element.parentElement; ancestor && ancestor !== root; ancestor = ancestor.parentElement) {
            if (isInteractive(ancestor)) return [[element, ancestor]];
        }
        return [];
    });
}

const checks = [];

function check(name, condition, detail = "") {
    checks.push({ name, passed: Boolean(condition), ...(detail ? { detail } : {}) });
}

async function main() {
    const projection = JSON.parse(readSite("status/quantum-edge-page.json"));
    const pageScript = readSite("quantum-edge-page.js");
    const dashboardSource = readSite("dashboard.js");

    const baseline = await boot({ projection, pageScript, dashboardSource });
    const root = baseline.document.querySelector("[data-quantum-edge-page]");
    check("renderer produced one Quantum Edge root", baseline.panel.querySelectorAll("[data-quantum-edge-page]").length === 1);
    check("lifecycle context remained mounted", baseline.panel.querySelectorAll("[data-qadam-lifecycle]").length === 1);

    const sections = root?.querySelectorAll("[data-qep-primary]") || [];
    check("exactly three primary sections rendered", sections.length === 3, `found ${sections.length}`);
    check("primary section order is evidence, consequence, answer", sections.map((section) => section.dataset.qepPrimary).join(",") === "evidence,consequence,answer");
    check("evidence is closed by default", sections[0]?.open === false);
    check("consequence is closed by default", sections[1]?.open === false);
    check("answer is closed by default", sections[2]?.open === false);
    const technical = root?.querySelector("[data-qep-technical]");
    check("exactly one inline technical evidence disclosure rendered", root?.querySelectorAll("[data-qep-technical]").length === 1);
    check("technical evidence is closed by default", technical?.open === false);
    check("technical evidence renders its projection-owned record index", technical?.querySelector(".qep-technical-index")?.querySelectorAll("li").length === projection.presentation.technical_record.index.length);
    check("technical evidence retains all eight fair-comparison conditions", technical?.querySelector(".qep-fair-protocol-list")?.querySelectorAll(":scope > li").length === 8);
    check("technical evidence retains the seven-stage governed downstream route", technical?.querySelector(".qep-route")?.querySelectorAll(":scope > li").length === 7);
    check("technical evidence retains the eight-step hybrid research lifecycle", technical?.querySelector(".qep-lifecycle")?.querySelectorAll(":scope > li").length === 8);
    check("the header owns the only current-conclusion surface", root?.querySelectorAll("[data-qep-current-conclusion]").length === 1);
    check("primary evidence uses one shared basis", root?.querySelectorAll(".qep-shared-basis").length === 1);
    check("primary evidence uses two method lanes", root?.querySelectorAll(".qep-method-lane").length === 2);
    const matchedEvidenceRows = root?.querySelector("[data-qep-matched-evidence]")?.querySelectorAll("li") || [];
    check("matched evidence exposes four distinct comparison rows", matchedEvidenceRows.length === 4);
    check("every matched evidence row compares both methods", Array.from(matchedEvidenceRows).every((row) => row.querySelectorAll("div").length === 2));
    check("primary evidence uses one joined comparison", root?.querySelectorAll(".qep-matched-outcome").length === 1);
    check("completed IBM result renders one historical validation record", root?.querySelectorAll("[data-qep-hardware-validation]").length === 1);
    check("hardware result shows the verified zero-dollar billed cost", root?.textContent.includes("US$0.00"));
    check("hardware result shows the verified 28 quantum seconds", root?.textContent.includes("28 seconds"));
    check("hardware result shows the measured submit-to-result turnaround", root?.textContent.includes("6m 51s"));
    check("hardware result shows that the classical baseline was preferred", root?.textContent.includes("Classical baseline preferred"));
    check("primary impact exposes exactly four gates", root?.querySelector(".qep-four-gates")?.querySelectorAll(":scope > li").length === 4);
    check("primary impact names strategy and paper-decision outcomes", root?.querySelector(".qep-impact-decisions")?.querySelectorAll(":scope > article").length === 2);
    check("primary verdict exposes exactly three plain-English statements", root?.querySelector(".qep-verdict-statements")?.querySelectorAll(":scope > article").length === 3);
    check("primary sections contain no nested details", sections.every((section) => section.querySelectorAll("details").length === 0));
    const primaryText = sections.map((section) => section.textContent).join(" ");
    check("primary page does not foreground technical ratios", !/11\/11|1\/6/.test(primaryText));

    const legacySession = await boot({
        projection,
        pageScript,
        dashboardSource,
        sessionSeed: {
            "qadam.quantumEdgeThreeLayer.open.v1": JSON.stringify({ evidence: true, consequence: true, answer: true })
        }
    });
    const legacySessionSections = legacySession.document.querySelectorAll("[data-qep-primary]");
    check(
        "a prior-session disclosure record cannot reopen the page",
        legacySessionSections.every((section) => section.open === false)
    );
    check("a prior-session record cannot reopen technical evidence", legacySession.document.querySelector("[data-qep-technical]")?.open === false);

    const keyboard = await boot({ projection, pageScript, dashboardSource });
    const keyboardSections = keyboard.document.querySelectorAll("[data-qep-primary]");
    const keyboardEvidenceSummary = keyboard.document.querySelector("[data-qep-primary='evidence']")?.querySelector(":scope > summary");
    const keyboardConsequenceSummary = keyboard.document.querySelector("[data-qep-primary='consequence']")?.querySelector(":scope > summary");
    pressSummaryKey(keyboardEvidenceSummary, "Enter");
    check("Enter activates a primary summary", keyboard.document.querySelector("[data-qep-primary='evidence']")?.open === true);
    pressSummaryKey(keyboardConsequenceSummary, " ");
    check("Space activates a primary summary", keyboard.document.querySelector("[data-qep-primary='consequence']")?.open === true);
    const keyboardTechnical = keyboard.document.querySelector("[data-qep-technical]");
    const keyboardTechnicalSummary = keyboardTechnical?.querySelector(":scope > summary");
    pressSummaryKey(keyboardTechnicalSummary, "Enter");
    check("Enter activates the technical evidence summary", keyboardTechnical?.open === true);

    const collapseFocus = await boot({ projection, pageScript, dashboardSource });
    const collapseSection = collapseFocus.document.querySelector("[data-qep-primary='answer']");
    const collapseSummary = collapseSection?.querySelector(":scope > summary");
    if (collapseSection) collapseSection.open = true;
    const collapseOwnedControl = collapseSection?.querySelector("[data-qep-help-trigger]");
    collapseOwnedControl?.focus();
    collapseSection.open = false;
    check(
        "collapsing a section returns owned focus to its summary",
        collapseFocus.document.activeElement === collapseSummary
    );

    const evidenceSection = root?.querySelector("[data-qep-primary='evidence']");
    const consequenceSection = root?.querySelector("[data-qep-primary='consequence']");
    const answerSection = root?.querySelector("[data-qep-primary='answer']");
    const evidenceSummary = evidenceSection?.querySelector(":scope > summary");
    const consequenceSummary = consequenceSection?.querySelector(":scope > summary");
    const answerSummary = answerSection?.querySelector(":scope > summary");
    evidenceSummary?.click();
    check("evidence can open by itself", evidenceSection?.open === true && consequenceSection?.open === false && answerSection?.open === false);
    consequenceSummary?.click();
    check("opening consequence leaves evidence open", evidenceSection?.open === true && consequenceSection?.open === true && answerSection?.open === false);
    answerSummary?.click();
    check("opening the answer leaves evidence and consequence open", sections.every((section) => section.open));
    answerSummary?.click();
    check("closing the answer leaves evidence and consequence open", evidenceSection?.open === true && consequenceSection?.open === true && answerSection?.open === false);

    const reentry = await boot({ projection, pageScript, dashboardSource });
    reentry.document.querySelector("[data-qep-primary='evidence']")?.querySelector(":scope > summary")?.click();
    reentry.window.location.search = "?module=patterns&view=findings";
    reentry.window.dispatchEvent(new HarnessEvent("popstate"));
    reentry.window.location.search = "?module=patterns&view=nonlinear";
    reentry.window.dispatchEvent(new HarnessEvent("popstate"));
    await settle();
    const reentrySections = reentry.document.querySelectorAll("[data-qep-primary]");
    check(
        "returning to Quantum Edge restores the collapsed overview",
        reentrySections.map((section) => section.open).join(",") === "false,false,false"
    );
    check("returning to Quantum Edge closes technical evidence", reentry.document.querySelector("[data-qep-technical]")?.open === false);

    const rerender = await boot({ projection, pageScript, dashboardSource });
    const rerenderRootBefore = rerender.document.querySelector("[data-quantum-edge-page]");
    const rerenderSectionsBefore = rerenderRootBefore?.querySelectorAll("[data-qep-primary]") || [];
    rerenderSectionsBefore[0].open = false;
    rerenderSectionsBefore[1].open = true;
    const rerenderFocusBefore = rerenderSectionsBefore[1]?.querySelector(":scope > summary");
    rerenderFocusBefore?.focus();
    const rerenderTechnicalBefore = rerenderRootBefore?.querySelector("[data-qep-technical]");
    if (rerenderTechnicalBefore) rerenderTechnicalBefore.open = true;
    const updatedProjection = JSON.parse(JSON.stringify(projection));
    updatedProjection.freshness.stale_after_seconds += 1;
    updatedProjection.content_hash = projectionHash(updatedProjection);
    updatedProjection.render_contract_hash = renderContractHash(updatedProjection);
    await rerender.window.QadamQuantumEdgePage.setProjection(updatedProjection);
    await settle();
    const rerenderRootAfter = rerender.document.querySelector("[data-quantum-edge-page]");
    const rerenderSectionsAfter = rerenderRootAfter?.querySelectorAll("[data-qep-primary]") || [];
    const rerenderFocusAfter = rerenderSectionsAfter[1]?.querySelector(":scope > summary");
    check(
        "a changed content hash replaces the rendered root",
        rerenderRootAfter !== rerenderRootBefore
            && rerenderRootBefore?.isConnected === false
            && rerenderRootAfter?.dataset.qepContentHash === updatedProjection.content_hash
    );
    check(
        "content-hash rerender preserves independent open state",
        rerenderSectionsAfter.map((section) => section.open).join(",") === "false,true,false"
    );
    check("content-hash rerender preserves technical evidence open state", rerenderRootAfter?.querySelector("[data-qep-technical]")?.open === true);
    check(
        "content-hash rerender restores focus to the matching control",
        rerender.document.activeElement === rerenderFocusAfter
            && rerenderFocusAfter?.dataset.qepFocusKey === rerenderFocusBefore?.dataset.qepFocusKey
    );

    const tampered = await boot({ projection, pageScript, dashboardSource });
    const tamperedProjection = JSON.parse(JSON.stringify(projection));
    tamperedProjection.content_hash = tamperedProjection.content_hash === "0".repeat(64) ? "1".repeat(64) : "0".repeat(64);
    const tamperedAccepted = await tampered.window.QadamQuantumEdgePage.setProjection(tamperedProjection);
    await settle();
    check("a malformed projection content hash fails closed", tamperedAccepted === false && tampered.document.querySelector("[data-qep-unavailable]") !== null);

    const drifted = await boot({ projection, pageScript, dashboardSource });
    const driftedProjection = JSON.parse(JSON.stringify(projection));
    driftedProjection.presentation.evidence.matched_outcome.label = "Unsupported winner";
    driftedProjection.content_hash = projectionHash(driftedProjection);
    driftedProjection.render_contract_hash = renderContractHash(driftedProjection);
    const driftedAccepted = await drifted.window.QadamQuantumEdgePage.setProjection(driftedProjection);
    await settle();
    check("a presentation and state-axis contradiction fails closed", driftedAccepted === false && drifted.document.querySelector("[data-qep-unavailable]") !== null);

    for (const sectionId of ["evidence", "consequence", "answer"]) {
        const linked = await boot({ projection, pageScript, dashboardSource, hash: `#quantum-${sectionId}` });
        const linkedSection = linked.document.querySelector(`#quantum-${sectionId}`);
        const linkedSummary = linkedSection?.querySelector(":scope > summary");
        check(`${sectionId} deep link opens the requested section`, linkedSection?.open === true);
        check(`${sectionId} deep link focuses the requested summary`, linked.document.activeElement === linkedSummary);
        check(`${sectionId} deep link scrolls the requested section into view`, linkedSection?.scrollIntoViewCalls.length === 1);
    }
    const technicalLinked = await boot({ projection, pageScript, dashboardSource, hash: "#quantum-technical-evidence" });
    const technicalLinkedSection = technicalLinked.document.querySelector("#quantum-technical-evidence");
    const technicalLinkedSummary = technicalLinkedSection?.querySelector(":scope > summary");
    check("technical deep link opens technical evidence", technicalLinkedSection?.open === true);
    check("technical deep link focuses its summary", technicalLinked.document.activeElement === technicalLinkedSummary);
    check("technical deep link scrolls into view", technicalLinkedSection?.scrollIntoViewCalls.length === 1);

    const readMore = root?.querySelector("[data-qep-read-more]");
    const guidance = root?.querySelector("[data-qep-guidance]");
    check("guidance starts collapsed", guidance?.hidden === true && readMore?.getAttribute("aria-expanded") === "false");
    check("collapsed guidance label ends with a plus", readMore?.textContent.trim().endsWith("+"));
    readMore?.click();
    check("Read more expands guidance and exposes state", guidance?.hidden === false && readMore?.getAttribute("aria-expanded") === "true");
    const guidanceSteps = guidance?.querySelector("[data-qep-guidance-steps]");
    const guidanceWorkflow = guidance?.querySelector("[data-qep-guidance-workflow]");
    const guidanceOutcomes = guidance?.querySelector("[data-qep-guidance-outcomes]");
    check("expanded guidance uses an ordered hybrid research flow", guidanceWorkflow?.tagName === "OL");
    check("expanded guidance renders five hybrid research stages", guidance?.querySelectorAll("[data-qep-guidance-workflow-step]").length === 5);
    check("expanded guidance separates operating model from current capability", guidance?.querySelectorAll("[data-qep-guidance-operating-model]").length === 1 && guidance?.querySelectorAll("[data-qep-guidance-current-capability]").length === 1);
    check("expanded guidance uses an ordered proof ladder", guidanceSteps?.tagName === "OL");
    check("expanded guidance renders six numbered proof standards", guidance?.querySelectorAll("[data-qep-guidance-step]").length === 6);
    check("expanded guidance renders five governed outcomes", guidanceOutcomes?.tagName === "UL" && guidance?.querySelectorAll("[data-qep-guidance-outcome]").length === 5);
    check("expanded guidance separates the research-reminder takeaway", guidance?.querySelectorAll("[data-qep-guidance-takeaway]").length === 1);
    const guidanceClose = guidance?.querySelector("[data-qep-guidance-close]");
    check("expanded guidance includes a bottom minimize control", Boolean(guidanceClose));
    guidanceClose?.click();
    check("bottom minimize control collapses guidance", guidance?.hidden === true && readMore?.getAttribute("aria-expanded") === "false");
    readMore?.click();
    readMore?.click();
    check("top control can still collapse guidance", guidance?.hidden === true && readMore?.getAttribute("aria-expanded") === "false");

    if (!answerSection?.open) answerSummary?.click();
    const helpTrigger = answerSection?.querySelector("[data-qep-help-trigger]");
    const helpId = helpTrigger?.getAttribute("aria-controls");
    const helpPanel = helpId ? root.querySelector(`#${helpId}`) : null;
    check("help trigger resolves aria-controls", Boolean(helpId && helpPanel));
    check("help trigger resolves aria-describedby to the same tooltip", helpTrigger?.getAttribute("aria-describedby") === helpId && helpPanel?.getAttribute("role") === "tooltip");
    helpTrigger?.click();
    check("click pins and opens a tooltip", helpTrigger?.getAttribute("aria-expanded") === "true" && helpPanel?.hidden === false && helpTrigger.closest("[data-qep-help]")?.classList.contains("is-pinned"));
    baseline.document.dispatchEvent(new HarnessEvent("keydown", { key: "Escape" }));
    check("Escape closes a pinned tooltip", helpTrigger?.getAttribute("aria-expanded") === "false" && helpPanel?.hidden === true);
    helpTrigger?.click();
    baseline.workspace.dispatchEvent(new HarnessEvent("click", { bubbles: true }));
    check("outside click closes a pinned tooltip", helpTrigger?.getAttribute("aria-expanded") === "false" && helpPanel?.hidden === true);
    helpTrigger?.focus();
    check("keyboard focus opens a tooltip without pinning", helpTrigger?.getAttribute("aria-expanded") === "true" && helpPanel?.hidden === false && !helpTrigger.closest("[data-qep-help]")?.classList.contains("is-pinned"));
    baseline.document.dispatchEvent(new HarnessEvent("keydown", { key: "Escape" }));

    const hovered = await boot({ projection, pageScript, dashboardSource });
    const hoveredRoot = hovered.document.querySelector("[data-quantum-edge-page]");
    const hoveredTrigger = hoveredRoot?.querySelector("[data-qep-help-trigger]");
    const hoveredPanelId = hoveredTrigger?.getAttribute("aria-controls");
    const hoveredPanel = hoveredPanelId ? hoveredRoot.querySelector(`#${hoveredPanelId}`) : null;
    hoveredTrigger?.dispatchEvent(new HarnessEvent("pointerenter"));
    check("pointer hover opens a tooltip", hoveredTrigger?.getAttribute("aria-expanded") === "true" && hoveredPanel?.hidden === false);
    hoveredTrigger?.dispatchEvent(new HarnessEvent("pointerleave"));
    hoveredPanel?.dispatchEvent(new HarnessEvent("pointerenter"));
    hovered.timers.advanceBy(181);
    check(
        "moving the pointer from trigger into its popover keeps it open",
        hoveredTrigger?.getAttribute("aria-expanded") === "true" && hoveredPanel?.hidden === false
    );
    hoveredPanel?.dispatchEvent(new HarnessEvent("pointerleave"));
    hovered.timers.advanceBy(181);
    check("pointer tooltip closes after leaving both trigger and popover", hoveredTrigger?.getAttribute("aria-expanded") === "false" && hoveredPanel?.hidden === true);

    let positionedTriggerRect = { left: 292, right: 316, top: 350, bottom: 374, width: 24, height: 24 };
    hovered.window.innerWidth = 320;
    hovered.window.innerHeight = 400;
    hoveredTrigger.getBoundingClientRect = () => positionedTriggerRect;
    hoveredPanel.getBoundingClientRect = () => ({ left: 0, right: 280, top: 0, bottom: 140, width: 280, height: 140 });
    hoveredTrigger?.dispatchEvent(new HarnessEvent("pointerenter"));
    check(
        "tooltip flips above a trigger near the viewport bottom",
        hoveredPanel?.dataset.qepPosition === "above" && hoveredPanel?.style.top === "202px"
    );
    check(
        "tooltip horizontal position and width are clamped to the viewport",
        hoveredPanel?.style.left === "24px" && hoveredPanel?.style.maxWidth === "288px"
    );
    positionedTriggerRect = { left: 292, right: 316, top: 20, bottom: 44, width: 24, height: 24 };
    hovered.window.dispatchEvent(new HarnessEvent("resize"));
    check(
        "open tooltip repositions below its trigger after viewport geometry changes",
        hoveredPanel?.dataset.qepPosition === "below" && hoveredPanel?.style.top === "52px" && hoveredPanel?.style.left === "24px"
    );

    const idElements = root?.querySelectorAll("[id]") || [];
    const ids = idElements.map((element) => element.id);
    const duplicateIds = [...new Set(ids.filter((id, index) => ids.indexOf(id) !== index))];
    check("rendered IDs are unique", duplicateIds.length === 0, duplicateIds.join(", "));

    const ariaReferenceElements = [...new Set([
        ...(root?.querySelectorAll("[aria-controls]") || []),
        ...(root?.querySelectorAll("[aria-describedby]") || [])
    ])];
    const ariaReferences = ariaReferenceElements.flatMap((element) => {
        const references = `${element.getAttribute("aria-controls") || ""} ${element.getAttribute("aria-describedby") || ""}`.trim().split(/\s+/).filter(Boolean);
        return references.filter((id) => !root.querySelector(`#${id}`)).map((id) => `${element.tagName.toLowerCase()} -> ${id}`);
    });
    check("aria-controls and aria-describedby references resolve", ariaReferences.length === 0, ariaReferences.join(", "));

    const nestedInteractive = findNestedInteractive(root);
    check("interactive controls are not nested", nestedInteractive.length === 0, nestedInteractive.map(([child, parent]) => `${child.tagName.toLowerCase()} in ${parent.tagName.toLowerCase()}`).join(", "));

    const liveAncestor = (() => {
        for (let ancestor = root?.parentElement; ancestor; ancestor = ancestor.parentElement) {
            if (ancestor.hasAttribute("aria-live")) return ancestor;
        }
        return null;
    })();
    check("Quantum Edge workspace has no live-region ancestor", !liveAncestor, liveAncestor ? `${liveAncestor.tagName.toLowerCase()}.${liveAncestor.className} aria-live=${liveAncestor.getAttribute("aria-live")}` : "");

    const failures = checks.filter((row) => !row.passed);
    const output = {
        status: failures.length ? "quantum_edge_interaction_acceptance_failed" : "quantum_edge_interaction_acceptance_passed",
        site_root: siteRoot,
        projection_content_hash: projection.content_hash,
        checks_passed: checks.length - failures.length,
        checks_total: checks.length,
        failures,
        checks
    };
    process.stdout.write(`${JSON.stringify(output, null, 2)}\n`);
    if (failures.length) process.exitCode = 1;
}

main().catch((error) => {
    process.stderr.write(`${error.stack || error.message}\n`);
    process.exitCode = 1;
});
