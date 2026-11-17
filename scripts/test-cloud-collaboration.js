#!/usr/bin/env node
"use strict";

const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const test = require("node:test");
const vm = require("node:vm");

const root = path.resolve(__dirname, "..");
const read = (file) => fs.readFileSync(path.join(root, file), "utf8");
const authSource = read("auth.js");
const allowedSession = { user: { id: "fixture-user", email: "raminhoodeh@gmail.com" } };

function element(attributes = "") {
    const classes = new Set((attributes.match(/class="([^"]*)"/)?.[1] || "").split(/\s+/));
    const node = {
        dataset: {}, hidden: /(?:^|\s)hidden(?=\s|>|$)/.test(attributes), disabled: false,
        textContent: "", children: [], listeners: {},
        classList: {
            contains: (name) => classes.has(name),
            add: (name) => classes.add(name), remove: (name) => classes.delete(name),
            toggle(name, enabled) { enabled ? classes.add(name) : classes.delete(name); }
        },
        addEventListener(type, callback) { this.listeners[type] = callback; },
        appendChild(child) { this.children.push(child); return child; },
        append(...children) { this.children.push(...children); },
        querySelector() { return null; }, querySelectorAll() { return []; },
        setAttribute() {}
    };
    for (const match of attributes.matchAll(/data-([a-z-]+)="([^"]*)"/g)) {
        const key = match[1].replace(/-([a-z])/g, (_, letter) => letter.toUpperCase());
        node.dataset[key] = match[2];
    }
    return node;
}

async function boot({ route = "dashboard", enabled = false, sdk, session = null,
    sessionError = false, sdkOutcome = "error", actualRenderer = false, stripPublicAttribute = false } = {}) {
    let html = read(`${route}/index.html`);
    if (stripPublicAttribute) html = html.replace(' data-public-read-only="true"', "");
    const calls = { create: 0, session: 0, render: [], signIn: 0, signUp: 0, signOut: 0,
        table: 0, requests: [], replacements: [], assignments: [], errors: [] };
    const dashboardTag = html.match(/<[^>]+\sdata-dashboard(?:\s[^>]*)?>/);
    const dashboard = dashboardTag ? element(dashboardTag[0]) : null;
    const body = element(html.match(/<body([^>]*)>/)[1]);
    const notice = element();
    const status = element();
    const commentForm = element();
    const controls = [element(), element(), element()];
    const authForm = element();
    const submit = controls[2];
    authForm.querySelectorAll = commentForm.querySelectorAll = () => controls;
    authForm.querySelector = () => submit;
    const commentList = element();
    const selectors = new Map([
        ["[data-dashboard]", dashboard], ["[data-cloud-status]", notice], ["[data-status]", status],
        ["[data-user-email]", element()], ["[data-comment-form]", commentForm],
        ["[data-comments-list]", commentList], ["[data-comments-summary]", element()],
        ["[data-comments-status]", element()], ["[data-signout]", element()]
    ]);
    if (html.includes("data-login-form")) selectors.set("[data-login-form]", authForm);
    if (html.includes("data-signup-form")) selectors.set("[data-signup-form]", authForm);
    const client = {
        auth: {
            async getSession() {
                calls.session++;
                if (sessionError) throw new Error("fixture_auth_unavailable");
                return { data: { session } };
            },
            async signInWithPassword() {
                calls.signIn++;
                return { data: { session, user: session?.user } };
            },
            async signUp() { calls.signUp++; return { data: { session } }; },
            async signOut() { calls.signOut++; return {}; }
        },
        from() {
            calls.table++;
            return { select() { return this; }, order() { return this; },
                async limit() { return { data: [] }; } };
        }
    };
    const goodSdk = { createClient() { calls.create++; return client; } };
    const timers = new Map();
    const document = {
        body, head: element(), documentElement: element(), visibilityState: "visible",
        querySelector: (selector) => selectors.get(selector) || null,
        querySelectorAll: () => [], createElement: () => element()
    };
    const window = {
        document, supabase: sdk === "available" ? goodSdk : sdk,
        location: { pathname: `/${route}/`, search: "", origin: "https://fixture.invalid",
            replace: (url) => calls.replacements.push(url), assign: (url) => calls.assignments.push(url) },
        addEventListener() {},
        setTimeout(callback) { const id = timers.size + 1; timers.set(id, callback); return id; },
        clearTimeout(id) { timers.delete(id); }, setInterval() {},
        renderQadamDashboardStatus: async (value) => calls.render.push(value)
    };
    document.head.appendChild = (script) => {
        document.head.children.push(script);
        if (sdkOutcome === "timeout") return script;
        if (sdkOutcome === "loaded") window.supabase = goodSdk;
        queueMicrotask(() => (sdkOutcome === "loaded" ? script.onload : script.onerror)?.());
        return script;
    };
    const context = vm.createContext({
        document, window, URLSearchParams, Intl,
        console: { error: (...args) => calls.errors.push(args) },
        localStorage: { getItem() { return null; }, setItem() {} },
        FormData: class { get(key) { return key === "email" ? session?.user.email : "fixture-password"; } },
        async fetch(url) {
            calls.requests.push(url);
            assert.equal(actualRenderer, true, "Unexpected network request");
            assert.equal(url, "/api/cockpit-status", "Only the stubbed same-origin status is allowed");
            return { ok: true, status: 200, headers: { get() { return null; } },
                async json() { return JSON.parse(read("status/cockpit-status.json")); } };
        }
    });
    if (actualRenderer) vm.runInContext(read("dashboard.js"), context);
    const source = enabled
        ? authSource.replace("const CLOUD_COLLABORATION_ENABLED = false;", "const CLOUD_COLLABORATION_ENABLED = true;")
        : authSource;
    // Capture the production bootstrap promise without invoking initialization twice.
    assert.ok(source.includes("initializeAuth();"));
    vm.runInContext(source.replace("initializeAuth();", "globalThis.authReady = initializeAuth();"), context);
    if (sdkOutcome === "timeout") for (const callback of timers.values()) callback();
    await context.authReady;
    return { calls, context, document, window, dashboard, notice, status, controls, authForm, commentForm, commentList };
}

test("actual HTML explicitly marks only the public dashboard and keeps the guide natively hidden", () => {
    const dashboard = read("dashboard/index.html");
    assert.match(dashboard, /<section\b[^>]*data-dashboard\s+data-public-read-only="true"[^>]*\shidden>/);
    const guide = read("guide/index.html");
    assert.match(guide, /<main\b[^>]*class="[^"]*\bhidden\b[^"]*"[^>]*data-dashboard[^>]*\shidden>/);
    assert.doesNotMatch(guide, /data-public-read-only/);
    for (const route of ["dashboard", "guide", "login", "sign-up"]) {
        const html = read(`${route}/index.html`);
        assert.doesNotMatch(html, /<script[^>]+src="[^"]*supabase/i);
        assert.doesNotMatch(html, /sb_secret_|service_role|(?:password|token|secret)\s*[:=]\s*["'][^"']+["']/i);
        assert.doesNotMatch(html, /<input[^>]*\bvalue=/i);
        assert.match(html, /\/auth\.js\?v=20261117-cloud-paused-v1/);
    }
    assert.match(authSource, /const CLOUD_COLLABORATION_ENABLED = false;/);
    assert.doesNotMatch(authSource, /sb_secret_|SUPABASE_SERVICE_ROLE|localStorage|sessionStorage/);
});

test("paused public dashboard renders without an SDK, session lookup or cloud network", async () => {
    const state = await boot();
    assert.equal(state.dashboard.hidden, false);
    assert.equal(state.dashboard.classList.contains("hidden"), false);
    assert.deepEqual(state.calls.render, [null]);
    assert.equal(state.calls.create + state.calls.session + state.calls.table, 0);
    assert.deepEqual(state.calls.requests, []);
    assert.deepEqual(state.document.head.children, []);
    assert.match(state.notice.textContent, /temporarily unavailable.*Telegram/);
    assert.ok(state.controls.every((control) => control.disabled));
    assert.match(state.commentList.textContent, /temporarily unavailable/);
    await assert.rejects(state.context.loadForumComments(), /temporarily unavailable/);
    await assert.rejects(state.context.updateForumCommentStatus("fixture", "accepted"), /temporarily unavailable/);
});

test("paused mode never touches even an installed SDK or stale signed-in session", async () => {
    const state = await boot({ sdk: { createClient() { assert.fail("Paused SDK must not instantiate"); } },
        session: allowedSession });
    assert.deepEqual(state.calls.render, [null]);
    assert.equal(state.calls.session, 0);
});

test("actual dashboard renderer completes on a stubbed public snapshot without Supabase", async () => {
    const state = await boot({ actualRenderer: true });
    assert.deepEqual(state.calls.errors, []);
    assert.equal(state.document.documentElement.dataset.dashboardStatus, "rendered");
    assert.equal(state.calls.create + state.calls.session + state.calls.table, 0);
    assert.deepEqual(state.calls.requests, ["/api/cockpit-status"]);
    // A later refresh cannot reveal private cloud comments from a mirrored snapshot.
    state.context.renderFundManagerNotes({ fund_manager_notes: { recent_comments: [{ body: "private-fixture" }] } });
    assert.doesNotMatch(state.commentList.textContent, /private-fixture/);
});

test("paused guide stays closed even with a pre-existing allowed session", async () => {
    const state = await boot({ route: "guide", sdk: "available", session: allowedSession });
    assert.equal(state.dashboard.hidden, true);
    assert.equal(state.dashboard.classList.contains("hidden"), true);
    assert.deepEqual(state.calls.render, []);
    assert.equal(state.calls.create + state.calls.session + state.calls.table, 0);
    assert.equal(state.notice.hidden, false);
    assert.match(state.notice.textContent, /protected guide.*paused.*Telegram/);
});

test("a dashboard class alone never opts a protected surface into public mode", async () => {
    const state = await boot({ stripPublicAttribute: true });
    assert.equal(state.dashboard.hidden, true);
    assert.deepEqual(state.calls.render, []);
});

for (const route of ["login", "sign-up"]) {
    test(`paused ${route} disables controls and blocks submission without credential calls`, async () => {
        const state = await boot({ route });
        assert.ok(state.controls.every((control) => control.disabled));
        let prevented = false;
        await state.authForm.listeners.submit({ preventDefault() { prevented = true; } });
        assert.equal(prevented, true);
        assert.equal(state.calls.create + state.calls.signIn + state.calls.signUp, 0);
        assert.match(state.status.textContent, /temporarily unavailable.*Telegram/);
    });
}

test("enabled mode preserves allowed protected access and forum reads", async () => {
    const state = await boot({ route: "guide", enabled: true, sdk: "available", session: allowedSession });
    assert.equal(state.calls.create, 1);
    assert.equal(state.calls.session, 1);
    assert.equal(state.calls.table, 1);
    assert.equal(state.dashboard.hidden, false);
    assert.deepEqual(state.calls.render, [allowedSession]);
});

test("enabled protected routes still redirect signed-out and reject non-allowlisted users", async () => {
    const signedOut = await boot({ route: "guide", enabled: true, sdk: "available" });
    assert.equal(signedOut.dashboard.hidden, true);
    assert.deepEqual(signedOut.calls.replacements, ["/login/?next=%2Fguide%2F"]);
    const denied = await boot({ route: "guide", enabled: true, sdk: "available",
        session: { user: { id: "fixture", email: "not-allowed@example.invalid" } } });
    assert.equal(denied.dashboard.hidden, true);
    assert.equal(denied.calls.signOut, 1);
    assert.deepEqual(denied.calls.replacements, ["/login/?error=not-allowlisted"]);
    assert.equal(denied.calls.table, 0);
});

test("enabled login and signup retain credential handlers", async () => {
    for (const route of ["login", "sign-up"]) {
        const state = await boot({ route, enabled: true, sdk: "available", session: allowedSession });
        assert.ok(state.controls.every((control) => !control.disabled));
        await state.authForm.listeners.submit({ preventDefault() {} });
        assert.equal(state.calls.signIn + state.calls.signUp, 1);
        assert.deepEqual(state.calls.assignments, ["/dashboard/"]);
    }
});

test("enabled mode loads a missing SDK only on demand", async () => {
    const state = await boot({ enabled: true, sdkOutcome: "loaded", session: allowedSession });
    assert.equal(state.document.head.children.length, 1);
    assert.equal(state.document.head.children[0].async, true);
    assert.equal(state.calls.create, 1);
    assert.deepEqual(state.calls.render, [allowedSession]);
});

for (const sdkOutcome of ["error", "timeout"]) {
    test(`enabled SDK ${sdkOutcome} fails closed for the guide and keeps public rendering`, async () => {
        const protectedState = await boot({ route: "guide", enabled: true, sdkOutcome });
        assert.equal(protectedState.dashboard.hidden, true);
        assert.equal(protectedState.calls.create, 0);
        assert.deepEqual(protectedState.calls.render, []);
        assert.match(protectedState.notice.textContent, /temporarily unavailable/);
        const publicState = await boot({ enabled: true, sdkOutcome });
        assert.equal(publicState.dashboard.hidden, false);
        assert.deepEqual(publicState.calls.render, [null]);
    });
}

test("enabled auth failures never reveal the guide or load its forum", async () => {
    const state = await boot({ route: "guide", enabled: true, sdk: "available", sessionError: true });
    assert.equal(state.dashboard.hidden, true);
    assert.equal(state.calls.table, 0);
    assert.deepEqual(state.calls.render, []);
    assert.match(state.notice.textContent, /temporarily unavailable/);
});

test("enabled public mode survives rejected sessions without querying cloud comments", async () => {
    const state = await boot({ enabled: true, sdk: "available", sessionError: true });
    assert.equal(state.dashboard.hidden, false);
    assert.equal(state.calls.table, 0);
    assert.deepEqual(state.calls.render, [null]);
    assert.match(state.commentList.textContent, /temporarily unavailable/);
});

test("an unusable SDK cannot unlock a protected guide", async () => {
    const state = await boot({ route: "guide", enabled: true,
        sdk: { createClient() { throw new Error("fixture_initialization_failure"); } } });
    assert.equal(state.dashboard.hidden, true);
    assert.deepEqual(state.calls.render, []);
    assert.match(state.notice.textContent, /temporarily unavailable/);
});
